"""CPU-only synthetic tests; official weights are never downloaded here."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import torch
from torch import nn

from alpha_captcha.dataset import ManifestError, save_jsonl, sha256_file
from alpha_captcha.presence_model import (
    FILL, PresenceDataset, PresenceNet, PresenceTrainingProfile, letterbox_image,
    evaluate_presence, load_presence_checkpoint, masked_bce_with_logits, predict_presence,
    preprocess_image, presence_metrics, state_sha256, train_presence,
)


def tiny_model():
    return PresenceNet(
        nn.Sequential(nn.AdaptiveAvgPool2d((2, 2)), nn.Conv2d(3, 4, 1), nn.BatchNorm2d(4), nn.ReLU()),
        nn.AdaptiveAvgPool2d((1, 1)), nn.Sequential(nn.Linear(4, 3)),
    )


class PresenceModelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.addCleanup(torch.hub.set_dir, torch.hub.get_dir())

    def record(self, name, split, labels=None):
        path = self.root / f"data/raw/kaggle/fixture/{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (20, 10), (len(name) * 10, len(list(path.parent.glob('*.png'))), 90)).save(path)
        return {
            "schema_version": 1, "source": "kaggle", "dataset_ref": "fixture/presence", "dataset_version": 1,
            "image_id": name, "image_path": path.relative_to(self.root).as_posix(), "group_id": name,
            "sha256": sha256_file(path), "split": split, "original_split": None,
            "labels": labels or {"tree": True, "building": False, "pond": True},
            "person": {"present": None, "count": None, "count_status": "unknown", "boxes": None, "iscrowd": False},
            "usage_note": "Synthetic fixture; not a dataset licence.",
        }

    def test_letterbox_preserves_full_width_edges_and_normalizes_rgb(self):
        image = Image.new("RGB", (400, 100), "red")
        image.paste("blue", (200, 0, 400, 100))
        letterboxed = letterbox_image(image)
        self.assertEqual(letterboxed.size, (224, 224))
        self.assertEqual(letterboxed.getpixel((0, 0)), FILL)
        self.assertEqual(letterboxed.getpixel((0, 100)), (255, 0, 0))
        self.assertEqual(letterboxed.getpixel((223, 100)), (0, 0, 255))
        tensor = preprocess_image(image)
        self.assertEqual(tuple(tensor.shape), (3, 224, 224))
        self.assertEqual(tensor.dtype, torch.float32)
        self.assertTrue(bool(torch.isfinite(tensor).all()))
        self.assertEqual(letterbox_image(Image.new("L", (10, 40))).mode, "RGB")

    def test_unknown_loss_and_gradient_do_not_depend_on_unknown_targets(self):
        logits = torch.zeros((2, 3), requires_grad=True)
        known = torch.tensor([[True, False, True], [False, True, False]])
        targets = torch.tensor([[1.0, float("nan"), 0.0], [float("nan"), 1.0, float("nan")]])
        loss = masked_bce_with_logits(logits, targets, known)
        self.assertAlmostEqual(loss.item(), 0.69314718, places=6)
        loss.backward()
        self.assertTrue(torch.equal(logits.grad[~known], torch.zeros(3)))
        self.assertTrue(bool((logits.grad[known] != 0).all()))
        empty_logits = torch.full((1, 3), 3e38, requires_grad=True)
        empty_loss = masked_bce_with_logits(empty_logits, torch.full((1, 3), float("nan")), torch.zeros((1, 3), dtype=torch.bool))
        empty_loss.backward()
        self.assertEqual(empty_loss.item(), 0.0)
        self.assertTrue(torch.equal(empty_logits.grad, torch.zeros_like(empty_logits)))
        with self.assertRaises(ValueError):
            masked_bce_with_logits(logits, targets, torch.ones_like(known))

    def test_train_mode_keeps_feature_bn_state_and_gradients_frozen(self):
        torch.manual_seed(42)
        model = tiny_model()
        before = state_sha256(model.features)
        head_before = state_sha256(model.classifier)
        model.train()
        self.assertFalse(model.features.training)
        self.assertFalse(model.features[2].training)
        self.assertTrue(model.classifier.training)
        optimizer = torch.optim.AdamW(model.classifier.parameters(), lr=0.01)
        logits = model(torch.randn(3, 3, 12, 12))
        masked_bce_with_logits(logits, torch.ones(3, 3), torch.ones((3, 3), dtype=torch.bool)).backward()
        optimizer.step()
        self.assertEqual(state_sha256(model.features), before)
        self.assertNotEqual(state_sha256(model.classifier), head_before)
        self.assertTrue(all(parameter.grad is None for parameter in model.features.parameters()))

    def test_dataset_refuses_school_anywhere_and_excludes_other_splits(self):
        records = [self.record("train-one", "train"), self.record("val-one", "val")]
        dataset = PresenceDataset(records, self.root, "train")
        self.assertEqual([row["image_id"] for row in dataset.records], ["train-one"])
        records[1]["source"] = "school"
        with self.assertRaisesRegex(ManifestError, "school"):
            PresenceDataset(records, self.root, "train")
        records[1]["source"] = "kaggle"
        records[1]["image_path"] = "data/raw/school/held-out.png"
        with self.assertRaisesRegex(ManifestError, "school"):
            PresenceDataset(records, self.root, "train")

    def test_metrics_use_class_specific_known_denominators(self):
        scores = torch.tensor([[0.9, 0.8, 0.2], [0.1, 0.1, 0.9]])
        targets = torch.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 1.0]])
        known = torch.tensor([[True, True, False], [True, False, False]])
        metrics = presence_metrics(scores, targets, known)["classes"]
        self.assertEqual(metrics["tree"]["known"], 2)
        self.assertEqual(metrics["tree"]["accuracy"], 1.0)
        self.assertEqual(metrics["tree"]["f1"], 1.0)
        self.assertEqual(metrics["building"]["known"], 1)
        self.assertEqual(metrics["building"]["fp"], 1)
        self.assertEqual(metrics["building"]["accuracy"], 0.0)
        self.assertIsNone(metrics["pond"]["accuracy"])
        self.assertIsNone(metrics["pond"]["f1"])

    def test_pixel_prediction_ignores_filename_and_rejects_answer_records(self):
        model = tiny_model().eval()
        image = Image.new("RGB", (20, 30), "green")
        image.filename = "answer_tree_true.png"
        first = predict_presence(model, [image])
        image.filename = "answer_tree_false.png"
        self.assertEqual(first, predict_presence(model, [image]))
        self.assertEqual(set(first[0]), {"tree", "building", "pond"})
        with self.assertRaises(TypeError):
            predict_presence(model, [{"answer": True}])

    def test_cpu_pipeline_only_fits_train_and_saves_reloadable_checked_artifacts(self):
        records = [
            self.record("train-alpha", "train"), self.record("train-beta", "train"),
            self.record("val-alpha", "val", {"tree": False, "building": True, "pond": None}),
            self.record("test-alpha", "test", {"tree": None, "building": True, "pond": False}),
        ]
        manifest = self.root / "manifest.jsonl"
        save_jsonl(records, manifest)
        original = manifest.read_bytes()
        output = self.root / "new-run"

        def builder(**kwargs):
            self.assertEqual(Path(torch.hub.get_dir()).resolve(), (self.root / "models/pretrained").resolve())
            return tiny_model(), {"name": "synthetic_test_only", "sha256": "not_official"}

        optimizer_class = torch.optim.AdamW
        frozen_before_optimizer = []

        def checked_optimizer(parameters, **kwargs):
            profiles = list((self.root / "runs/frozen-profiles").glob("*.json"))
            self.assertEqual(len(profiles), 1)
            frozen = json.loads(profiles[0].read_text(encoding="utf-8"))
            self.assertTrue(frozen["recorded_before_optimizer_creation"])
            self.assertEqual(frozen["manifest_sha256"], sha256_file(manifest))
            self.assertEqual(frozen["profile"]["epochs"], 1)
            frozen_before_optimizer.append(frozen)
            return optimizer_class(parameters, **kwargs)

        with patch("alpha_captcha.presence_model.build_presence_model", side_effect=builder), \
                patch("alpha_captcha.presence_model.torch.optim.AdamW", side_effect=checked_optimizer):
            report = train_presence(manifest, self.root, output, device="cpu")
            self.assertEqual(len(frozen_before_optimizer), 1)
            self.assertEqual(sha256_file(report["frozen_profile_path"]), report["frozen_profile_sha256"])
            self.assertEqual(report["profile"]["epochs"], 1)
            self.assertEqual({row["image_id"] for row in report["train_used"]}, {"train-alpha", "train-beta"})
            self.assertEqual(report["evaluations"]["train"]["images"], 2)
            self.assertEqual(report["evaluations"]["val"]["images"], 1)
            self.assertEqual(report["evaluations"]["test"]["images"], 1)
            self.assertTrue(report["features_and_bn_unchanged"])
            self.assertNotEqual(report["classifier_sha256_before"], report["classifier_sha256_after"])
            self.assertEqual(report["manifest_sha256"], sha256_file(manifest))
            self.assertTrue(all(name.startswith("classifier.") for name in report["trainable_parameter_names"]))
            loaded, metadata = load_presence_checkpoint(output / "presence.pt")
            self.assertEqual(metadata["model_state_sha256"], state_sha256(loaded))
            self.assertEqual(len(predict_presence(loaded, [Image.new("RGB", (10, 10))])), 1)
            for split in ("train", "val", "test"):
                self.assertTrue((output / f"predictions-{split}.json").is_file())
            with self.assertRaises(FileExistsError):
                train_presence(manifest, self.root, output, device="cpu")
        self.assertEqual(manifest.read_bytes(), original)

    def test_profile_and_eval_cap_validation(self):
        for changes in ({"epochs": True}, {"threshold": float("nan")}, {"batch_size": 0}, {"seed": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                PresenceTrainingProfile(**changes)
        records = [self.record("validation", "val")]
        with self.assertRaisesRegex(ValueError, "cannot be capped"):
            PresenceDataset(records, self.root, "val", max_images=1)

    def test_selection_run_never_evaluates_or_publishes_test_predictions(self):
        manifest = self.root / "selection.jsonl"
        save_jsonl([
            self.record("train-selection", "train"),
            self.record("val-selection", "val"),
            self.record("test-selection", "test"),
        ], manifest)
        original = manifest.read_bytes()
        output = self.root / "selection-run"

        def selection_evaluation(model, dataset, *args, **kwargs):
            self.assertNotEqual(dataset.split, "test", "selection must not run test inference")
            return evaluate_presence(model, dataset, *args, **kwargs)

        with patch("alpha_captcha.presence_model.build_presence_model",
                   return_value=(tiny_model(), {"name": "synthetic_test_only"})), \
                patch("alpha_captcha.presence_model.evaluate_presence",
                      side_effect=selection_evaluation) as evaluate:
            report = train_presence(manifest, self.root, output, device="cpu", evaluate_test=False)

        self.assertEqual([call.args[1].split for call in evaluate.call_args_list], ["train", "val"])
        self.assertEqual(set(report["evaluations"]), {"train", "val"})
        self.assertIs(report["test_evaluated"], False)
        self.assertFalse((output / "predictions-test.json").exists())
        self.assertTrue((output / "predictions-val.json").is_file())
        persisted = json.loads((output / "report.json").read_text(encoding="utf-8"))
        self.assertIs(persisted["test_evaluated"], False)
        self.assertNotIn("test", persisted["evaluations"])
        saved = torch.load(output / "presence.pt", map_location="cpu", weights_only=True)
        self.assertIs(saved["metadata"]["test_evaluated"], False)
        self.assertEqual(manifest.read_bytes(), original)

    def test_test_evaluation_switch_requires_a_real_boolean_before_any_io(self):
        for value in (None, 0, 1, "false", []):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "evaluate_test"):
                train_presence(self.root / "absent.jsonl", self.root, self.root / "unused",
                               device="cpu", evaluate_test=value)
        self.assertFalse((self.root / "unused").exists())

    def test_manifest_change_mid_run_refuses_artifact_with_wrong_provenance(self):
        manifest = self.root / "changing.jsonl"
        save_jsonl([self.record("train-changing", "train")], manifest)
        output = self.root / "must-not-publish"

        def changing_builder(**kwargs):
            with manifest.open("a", encoding="utf-8") as stream:
                stream.write("\n")
            return tiny_model(), {"name": "synthetic_test_only"}

        with patch("alpha_captcha.presence_model.build_presence_model", side_effect=changing_builder):
            with self.assertRaisesRegex(ValueError, "manifest changed during training"):
                train_presence(manifest, self.root, output, device="cpu")
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
