import tempfile
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from PIL import Image
import torch
from torch import nn

from alpha_captcha.dataset import save_jsonl, sha256_file
from alpha_captcha.person_model import (
    PersonDataset, PersonTrainingProfile, decode_person_output, letterbox_person,
    set_person_training_mode, train_person, SSDLite320_MobileNet_V3_Large_Weights,
)


class TinyPersonDetector(nn.Module):
    """A CPU loss fixture, never an actual detector or official weight download."""

    def __init__(self):
        super().__init__()
        self.backbone = nn.Linear(1, 1)
        self.head = nn.Linear(1, 1)
        for parameter in self.backbone.parameters():
            parameter.requires_grad_(False)

    def forward(self, images, targets=None):
        if not self.training or targets is None:
            raise AssertionError("this training fixture must not perform detector inference")
        summary = torch.stack([image.mean() for image in images]).mean().reshape(1, 1)
        return {"loss_classifier": self.head(summary).square().mean()}


class PersonModelTests(unittest.TestCase):
    def test_letterbox_preserves_full_image_and_boxes_roundtrip(self):
        picture = Image.new("RGB", (640, 200), (255, 0, 0))
        boxes = [[0, 0, 100, 200], [600, 0, 640, 200]]
        tensor, transformed, geometry = letterbox_person(picture, boxes)
        self.assertEqual(tuple(tensor.shape), (3, 320, 320))
        output = {"boxes": transformed, "labels": torch.ones(2, dtype=torch.int64), "scores": torch.tensor([.9, .8])}
        decoded = decode_person_output(output, geometry, PersonTrainingProfile())
        self.assertEqual(decoded["person_count"], 2)
        torch.testing.assert_close(torch.tensor(decoded["boxes"]), torch.tensor(boxes, dtype=torch.float32))
        self.assertTrue(torch.all(tensor[:, 0, 0] == 114 / 255))
        self.assertEqual(float(tensor[0, 160, 0]), 1.0)

    def test_only_valid_person_boxes_above_frozen_threshold_count(self):
        output = {"boxes": torch.tensor([[0, 0, 20, 20], [0, 0, 20, 20], [0, 0, 20, 20], [0, 0, 3, 3]], dtype=torch.float32),
                  "labels": torch.tensor([1, 2, 1, 1]), "scores": torch.tensor([.5, .99, .49, .99])}
        geometry = dict(width=320, height=320, left=0, top=0, scale_x=1, scale_y=1)
        self.assertEqual(decode_person_output(output, geometry, PersonTrainingProfile())["person_count"], 1)
        output["scores"][0] = float("nan")
        with self.assertRaises(ValueError):
            decode_person_output(output, geometry, PersonTrainingProfile())

    def test_count_without_complete_verified_boxes_cannot_fit_detector(self):
        for person in [dict(count_status="unknown", iscrowd=False, boxes=[]),
                       dict(count_status="verified", iscrowd=False, boxes=None),
                       dict(count_status="crowd", iscrowd=True, boxes=[])]:
            dataset = PersonDataset([{"person": person}], Path("."), PersonTrainingProfile())
            with self.assertRaisesRegex(ValueError, "complete"):
                dataset[0]

    def test_training_mode_freezes_backbone_and_all_bn_statistics(self):
        model = nn.Module()
        model.backbone = nn.Sequential(nn.Linear(2, 2), nn.BatchNorm1d(2))
        model.head = nn.Sequential(nn.BatchNorm1d(2), nn.Linear(2, 1))
        set_person_training_mode(model)
        self.assertFalse(model.backbone.training)
        self.assertTrue(model.head.training)
        self.assertFalse(model.head[0].training)

    def test_profile_rejects_invalid_limits(self):
        for kwargs in [dict(epochs=True), dict(batch_size=0), dict(input_size=224),
                       dict(score_threshold=float("nan")), dict(nms_iou_threshold=0)]:
            with self.assertRaises(ValueError):
                PersonTrainingProfile(**kwargs)

    def test_selection_run_evaluates_only_val_and_marks_test_unseen_in_all_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.addCleanup(torch.hub.set_dir, torch.hub.get_dir())
            records = []
            for index, split in enumerate(("train", "val", "test")):
                image_path = root / f"data/raw/kaggle/fixture/{split}.png"
                image_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (20, 10), (index * 60, 40, 90)).save(image_path)
                records.append({
                    "schema_version": 1, "source": "kaggle", "dataset_ref": "fixture/person",
                    "dataset_version": 1, "image_id": split, "group_id": split,
                    "image_path": image_path.relative_to(root).as_posix(),
                    "sha256": sha256_file(image_path), "split": split, "original_split": None,
                    "labels": {"tree": None, "building": None, "pond": None},
                    "person": {"present": True, "count": 1, "count_status": "verified",
                               "boxes": [[2, 1, 14, 9]], "iscrowd": False},
                    "person_review": {"detection_eligible": True},
                    "usage_note": "Synthetic fixture; not a dataset licence.",
                })
            manifest = root / "selection.jsonl"
            save_jsonl(records, manifest)
            original = manifest.read_bytes()
            output = root / "selection-run"

            def builder(profile):
                # train_person records the cached file hash. This is a local
                # synthetic placeholder inside the temporary test directory.
                cached = (root / "models/pretrained/checkpoints"
                          / Path(SSDLite320_MobileNet_V3_Large_Weights.COCO_V1.url).name)
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(b"synthetic unit-test weight provenance only")
                return TinyPersonDetector()

            def selection_evaluation(model, rows, *args, **kwargs):
                self.assertEqual([row["image_id"] for row in rows], ["val"],
                                 "selection must not run test inference")
                return {"images": len(rows), "predictions": []}

            with patch("alpha_captcha.person_model.build_person_model", side_effect=builder), \
                    patch("alpha_captcha.person_model.evaluate_person",
                          side_effect=selection_evaluation) as evaluate:
                report = train_person(manifest, root, output, device="cpu", evaluate_test=False)

            self.assertEqual(evaluate.call_count, 1)
            self.assertEqual(set(report["evaluation"]), {"val"})
            self.assertIs(report["metadata"]["test_evaluated"], False)
            persisted = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertIs(persisted["metadata"]["test_evaluated"], False)
            self.assertNotIn("test", persisted["evaluation"])
            frozen = json.loads((output / "frozen-profile.json").read_text(encoding="utf-8"))
            self.assertIs(frozen["test_evaluated"], False)
            saved = torch.load(output / "person.pt", map_location="cpu", weights_only=True)
            self.assertIs(saved["metadata"]["test_evaluated"], False)
            self.assertFalse((output / "predictions-test.json").exists())
            self.assertEqual(manifest.read_bytes(), original)

    def test_test_evaluation_switch_requires_a_real_boolean_before_any_io(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for value in (None, 0, 1, "false", []):
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, "evaluate_test"):
                    train_person(root / "absent.jsonl", root, root / "unused",
                                 device="cpu", evaluate_test=value)
            self.assertFalse((root / "unused").exists())


if __name__ == "__main__":
    unittest.main()
