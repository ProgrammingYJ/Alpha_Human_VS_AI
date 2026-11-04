"""Synthetic fixture tests: no downloaded or school photos are used."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from alpha_captcha.dataset import (
    ManifestError,
    grouped_split,
    load_jsonl,
    manifest_stats,
    save_jsonl,
    sha256_file,
    validate_manifest,
)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def record(self, name="one", **changes):
        path = self.root / "data/raw/kaggle/fixture" / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Distinct fixture bytes prevent accidental hash grouping by default.
        Image.new("RGB", (20, 15), (sum(name.encode()) % 256, len(name), len(list(path.parent.glob('*.png'))))).save(path)
        row = {
            "schema_version": 1,
            "image_path": path.relative_to(self.root).as_posix(),
            "source": "kaggle",
            "dataset_ref": "fixture/scenes",
            "dataset_version": "1",
            "image_id": name,
            "group_id": f"group-{name}",
            "sha256": sha256_file(path),
            "labels": {"tree": None, "building": False, "pond": True},
            "person": {"present": None, "count": None, "count_status": "unknown", "boxes": None, "iscrowd": False},
            "original_split": None,
            "usage_note": "Synthetic test fixture; not a real dataset licence.",
        }
        row.update(changes)
        return row

    def assert_invalid(self, row, message, **kwargs):
        with self.assertRaisesRegex(ManifestError, message):
            validate_manifest([row], self.root, **kwargs)

    def test_jsonl_roundtrip_exclusive_write_and_no_original_changes(self):
        row = self.record()
        output = self.root / "data/manifests/new.jsonl"
        image = self.root / row["image_path"]
        original = image.read_bytes()
        save_jsonl([row], output)
        self.assertEqual([row], load_jsonl(output))
        with self.assertRaises(FileExistsError):
            save_jsonl([], output)
        with self.assertRaises(ManifestError):
            save_jsonl([row], image)
        self.assertEqual(original, image.read_bytes())

    def test_load_rejects_duplicate_keys_and_non_objects_with_line(self):
        path = self.root / "bad.jsonl"
        for body, message in [('\n{"schema_version":1,"schema_version":2}', "2: duplicate JSON key"), ('[]', "1: expected a JSON object")]:
            path.write_text(body, encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, message):
                load_jsonl(path)

    def test_unknown_labels_and_binary_person_presence_remain_unknown_count(self):
        row = self.record()
        row["person"]["present"] = True
        before = deepcopy(row)
        report = validate_manifest([row], self.root)
        self.assertEqual(row, before)
        self.assertEqual(report["labels"]["tree"], {"positive": 0, "negative": 0, "unknown": 1})
        self.assertEqual(report["person_count_status"], {"verified": 0, "unknown": 1, "crowd": 0})
        self.assertTrue(report["verification"]["file_hashes_and_pixels"])
        self.assertFalse(report["verification"]["label_truth_verified"])
        self.assertFalse(report["verification"]["near_duplicate_search_performed"])
        self.assert_invalid(self.record("invalidlabel", labels={"tree": 0, "building": None, "pond": None}), "bool or null")

    def test_positive_integer_dataset_version_extra_provenance_and_partial_boxes(self):
        row = self.record(dataset_version=2, parent_id=None, width=20, height=15,
                          annotation_source="synthetic", annotation_exhaustive=False)
        row["person"].update(present=True, boxes=[[1, 1, 4, 5]])
        report = validate_manifest([row], self.root)
        self.assertEqual(report["datasets"], {"fixture/scenes@2": 1})
        self.assertEqual(report["person_count_status"]["unknown"], 1)
        for version in (True, 0, -1, None):
            bad = deepcopy(row)
            bad["dataset_version"] = version
            self.assert_invalid(bad, "dataset_version")

    def test_school_source_and_paths_and_traversal_are_rejected(self):
        self.assert_invalid(self.record(source="school"), "school data is forbidden")
        for path in ("data/raw/school/a.png", "data/raw/kaggle/../school/a.png", "../outside.png", "C:/school/a.png", "data/raw/kaggle/school/a.png", "data\\raw\\kaggle\\a.png"):
            with self.subTest(path=path):
                self.assert_invalid(self.record(image_path=path), "(school|traversal|POSIX)", verify_files=False)

    def test_symlink_escape_and_kaggle_root_symlink_are_rejected(self):
        row = self.record()
        school = self.root / "data/raw/school"
        school.mkdir(parents=True)
        target = school / "synthetic.png"
        Image.new("RGB", (20, 15)).save(target)
        link = self.root / "data/raw/kaggle/school-link.png"
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest(f"OS does not permit creating a symlink: {error}")
        row.update(image_path=link.relative_to(self.root).as_posix(), sha256=sha256_file(target))
        self.assert_invalid(row, "symlink/junction")
        processed = self.root / "data/processed"
        processed.mkdir()
        (processed / "kaggle").symlink_to(school, target_is_directory=True)
        row["image_path"] = "data/processed/kaggle/synthetic.png"
        self.assert_invalid(row, "symlink/junction")

    def test_hash_corruption_missing_and_non_image_are_rejected(self):
        self.assert_invalid(self.record(sha256="0" * 64), "sha256 mismatch")
        row = self.record("deleted")
        (self.root / row["image_path"]).unlink()
        self.assert_invalid(row, "does not exist")
        schema_report = validate_manifest([row], self.root, verify_files=False)
        self.assertFalse(schema_report["verification"]["file_hashes_and_pixels"])
        row = self.record("invalidpixels")
        image = self.root / row["image_path"]
        image.write_text("this is not an image", encoding="utf-8")
        row["sha256"] = sha256_file(image)
        self.assert_invalid(row, "unreadable image")

    def test_person_count_and_boxes_are_checked(self):
        row = self.record()
        row["person"] = {"present": True, "count": 1, "count_status": "verified", "boxes": [[1, 2, 10, 12]], "iscrowd": False}
        validate_manifest([row], self.root)
        for count in (-1, True, 1.5):
            bad = deepcopy(row)
            bad["person"]["count"] = count
            self.assert_invalid(bad, "nonnegative integer")
        bad = deepcopy(row)
        bad["person"]["count"] = 2
        self.assert_invalid(bad, "disagrees")
        for box in ([1, 2, 25, 12], [2, 2, 1, 12], [1, 2, float("nan"), 12], [True, 2, 10, 12]):
            bad = deepcopy(row)
            bad["person"]["boxes"] = [box]
            self.assert_invalid(bad, "(beyond|positive area|finite)")

    def test_crowd_never_becomes_one_person(self):
        row = self.record()
        row["person"] = {"present": True, "count": None, "count_status": "crowd", "boxes": [[1, 1, 5, 5]], "iscrowd": True}
        report = validate_manifest([row], self.root)
        self.assertEqual(report["person_count_status"]["crowd"], 1)
        self.assertEqual(report["verified_count_histogram"], {})
        row["person"]["count"] = 1
        self.assert_invalid(row, "must be null")
        row["person"]["count_status"] = "verified"
        self.assert_invalid(row, "cannot have a verified exact count")

    def test_split_leakage_for_groups_hashes_parents_and_source_versions(self):
        for relation in ("group", "hash", "parent", "siblings", "source"):
            with self.subTest(relation=relation):
                first, second = self.record("first"), self.record("second")
                first["split"], second["split"] = "train", "test"
                if relation == "group":
                    second["group_id"] = first["group_id"]
                elif relation == "hash":
                    (self.root / second["image_path"]).write_bytes((self.root / first["image_path"]).read_bytes())
                    second["sha256"] = first["sha256"]
                elif relation == "parent":
                    second["parent_id"] = first["image_id"]
                elif relation == "siblings":
                    first["parent_id"] = second["parent_id"] = "parent-not-in-manifest"
                else:
                    second["image_id"] = first["image_id"]
                    second["dataset_version"] = "2"
                with self.assertRaisesRegex(ManifestError, "cross-split leakage"):
                    validate_manifest([first, second], self.root)

    def test_split_is_deterministic_order_independent_and_grouped(self):
        records = [self.record(f"img-{number:03d}") for number in range(40)]
        records[1]["parent_id"] = records[0]["image_id"]
        records[3]["group_id"] = records[2]["group_id"]
        originals = deepcopy(records)
        first = grouped_split(records, self.root)
        second = grouped_split(list(reversed(records)), self.root)
        assignment = lambda rows: {row["image_id"]: row["split"] for row in rows}
        self.assertEqual(assignment(first), assignment(second))
        self.assertEqual(records, originals)
        self.assertEqual(first[0]["split"], first[1]["split"])
        self.assertEqual(first[2]["split"], first[3]["split"])
        report = validate_manifest(first, self.root, require_split=True)
        self.assertEqual(report["groups"], 38)
        self.assertEqual({name: report["splits"][name]["images"] for name in ("train", "val", "test")}, {"train": 28, "val": 6, "test": 6})
        self.assertNotEqual(assignment(first), assignment(grouped_split(records, self.root, seed=7)))

    def test_official_splits_pin_entire_lineage_and_conflicts_fail(self):
        first, second = self.record("official"), self.record("child")
        first["original_split"] = "test"
        second["parent_id"] = first["image_id"]
        rows = grouped_split([first, second], self.root)
        self.assertEqual([row["split"] for row in rows], ["test", "test"])
        second["original_split"] = "train"
        with self.assertRaisesRegex(ManifestError, "contradictory official splits"):
            grouped_split([first, second], self.root)
        rows = grouped_split([first, second], self.root, respect_original_split=False, ratios=(1, 0, 0))
        self.assertEqual([row["split"] for row in rows], ["train", "train"])

    def test_small_group_does_not_promise_coverage(self):
        row = self.record()
        rows = grouped_split([row], self.root)
        report = manifest_stats(rows)
        self.assertTrue(report["warnings"])
        self.assertEqual(report["splits"]["test"]["images"], 0)
        self.assertEqual(row["labels"]["tree"], None)
        with self.assertRaisesRegex(ManifestError, "assigned split"):
            validate_manifest([row], self.root, require_split=True)
        with self.assertRaisesRegex(ManifestError, "sum to 1"):
            grouped_split([row], self.root, ratios=(.5, .5, .5))
        with self.assertRaisesRegex(ManifestError, "no images"):
            validate_manifest([], self.root)


if __name__ == "__main__":
    unittest.main()
