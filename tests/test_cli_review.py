"""CLI/review integration uses temporary synthetic images, never network/input."""

from copy import deepcopy
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

from alpha_captcha.dataset import load_jsonl, save_jsonl, sha256_file, validate_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCRIPT = PROJECT_ROOT / "scripts" / "review_labels.py"
REVIEW_FIELDS = [
    "dataset_ref", "image_id", "sha256", "image_path", "tree", "building", "pond",
    "person_present", "person_count", "reviewer", "review_note",
]


class CliAndReviewTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.records = []
        for index in range(4):
            image = self.root / f"data/raw/kaggle/synthetic/photo-{index}.png"
            image.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (20, 16), (20 + index * 30, index, 100)).save(image)
            self.records.append({
                "schema_version": 1,
                "source": "kaggle",
                "dataset_ref": "fixture/scenes",
                "dataset_version": 1,
                "image_id": f"photo-{index}",
                "image_path": image.relative_to(self.root).as_posix(),
                "sha256": sha256_file(image),
                "group_id": f"group-{index}",
                "labels": {"tree": None, "building": None, "pond": None},
                "person": {
                    "present": None, "count": None, "count_status": "unknown",
                    "boxes": None, "iscrowd": False,
                },
                "original_split": None,
                "split": None,
                "usage_note": "Synthetic test fixture; not a dataset licence.",
            })
        self.records[1]["person"].update(
            present=True, boxes=[[1, 1, 8, 9], [10, 2, 15, 12]],
        )
        self.manifest = self.root / "data/manifests/input.jsonl"
        save_jsonl(self.records, self.manifest)
        self.reviews = self.root / "reviews.csv"
        self.original_manifest = self.manifest.read_bytes()
        self.original_images = {
            row["image_path"]: (self.root / row["image_path"]).read_bytes()
            for row in self.records
        }

    def assert_originals_preserved(self):
        self.assertEqual(self.manifest.read_bytes(), self.original_manifest)
        for path, contents in self.original_images.items():
            self.assertEqual((self.root / path).read_bytes(), contents)

    def review(self, action, *, output=None, manifest=None):
        command = [
            sys.executable, str(REVIEW_SCRIPT), action,
            "--manifest", str(manifest or self.manifest),
            "--reviews", str(self.reviews), "--root", str(self.root),
        ]
        if output is not None:
            command.extend(["--output", str(output)])
        return subprocess.run(
            command, cwd=PROJECT_ROOT, capture_output=True, text=True,
            encoding="utf-8", timeout=15,
        )

    def cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "alpha_captcha", *map(str, arguments)],
            cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=15,
        )

    def export(self):
        result = self.review("export")
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.reviews.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, REVIEW_FIELDS)
            return list(reader)

    def write_reviews(self, rows):
        with self.reviews.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_export_and_blank_apply_never_turn_unknown_into_negative_or_zero(self):
        rows = self.export()
        self.assertEqual(len(rows), 4)
        for row, original in zip(rows, self.records):
            for field in REVIEW_FIELDS[:4]:
                self.assertEqual(row[field], original[field])
            for field in REVIEW_FIELDS[4:]:
                self.assertEqual(row[field], "")
        output = self.root / "blank-reviewed.jsonl"
        result = self.review("apply", output=output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(load_jsonl(output), self.records)
        self.assert_originals_preserved()

    def test_explicit_absence_and_blank_ambiguity_remain_distinct(self):
        rows = self.export()
        rows[0].update(
            tree="0", building="1", pond="  ", person_present="0",
            reviewer="fixture reviewer", review_note="pond ambiguous; leave unknown",
        )
        self.write_reviews(rows)
        output = self.root / "presence-reviewed.jsonl"
        result = self.review("apply", output=output)
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = load_jsonl(output)
        self.assertEqual(changed[0]["labels"], {"tree": False, "building": True, "pond": None})
        self.assertIs(changed[0]["person"]["present"], False)
        self.assertIsNone(changed[0]["person"]["count"])
        self.assertEqual(changed[0]["person"]["count_status"], "unknown")
        self.assertEqual(changed[1:], self.records[1:])
        self.assert_originals_preserved()

    def test_nonblank_ambiguous_label_is_rejected_without_output(self):
        rows = self.export()
        for index, invalid in enumerate(("?", "unknown", "false")):
            with self.subTest(value=invalid):
                edited = deepcopy(rows)
                edited[0].update(tree=invalid, reviewer="fixture", review_note="ambiguous")
                self.write_reviews(edited)
                output = self.root / f"invalid-{index}.jsonl"
                result = self.review("apply", output=output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("review flags must be 0, 1 or blank", result.stderr)
                self.assertFalse(output.exists())
                self.assert_originals_preserved()

    def test_review_identity_hash_and_path_mismatch_reject_atomically(self):
        rows = self.export()
        for field, wrong in (
            ("sha256", "0" * 64),
            ("image_id", "unknown-image"),
            ("dataset_ref", "wrong/source"),
            ("image_path", "data/raw/kaggle/wrong.png"),
        ):
            with self.subTest(field=field):
                edited = deepcopy(rows)
                # A valid first row must not be saved when a later row is invalid.
                edited[0].update(tree="1", reviewer="fixture", review_note="valid first row")
                edited[1].update({field: wrong})
                self.write_reviews(edited)
                output = self.root / f"mismatch-{field}.jsonl"
                result = self.review("apply", output=output)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
                self.assert_originals_preserved()

    def test_exact_count_review_preserves_uncertified_original_boxes_separately(self):
        rows = self.export()
        rows[1].update(person_count="3", reviewer="fixture", review_note="three visible people")
        self.write_reviews(rows)
        output = self.root / "count-reviewed.jsonl"
        result = self.review("apply", output=output)
        self.assertEqual(result.returncode, 0, result.stderr)
        reviewed = load_jsonl(output)
        self.assertEqual(reviewed[1]["annotation_boxes"], self.records[1]["person"]["boxes"])
        self.assertIsNone(reviewed[1]["person"]["boxes"])
        self.assertEqual(reviewed[1]["person"]["count"], 3)
        self.assertEqual(reviewed[1]["person"]["count_status"], "verified")
        self.assertIs(reviewed[1]["person"]["present"], True)
        validate_manifest(reviewed, self.root)
        self.assert_originals_preserved()

    def test_count_rereview_keeps_original_annotation_provenance(self):
        rows = self.export()
        rows[1].update(person_count="3", reviewer="fixture", review_note="first review")
        self.write_reviews(rows)
        first_output = self.root / "first-count-review.jsonl"
        first = self.review("apply", output=first_output)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_bytes = first_output.read_bytes()
        rows[1].update(person_count="4", review_note="corrected independent review")
        self.write_reviews(rows)
        second_output = self.root / "second-count-review.jsonl"
        second = self.review("apply", manifest=first_output, output=second_output)
        self.assertEqual(second.returncode, 0, second.stderr)
        reviewed = load_jsonl(second_output)
        self.assertEqual(reviewed[1]["annotation_boxes"], self.records[1]["person"]["boxes"])
        self.assertIsNone(reviewed[1]["person"]["boxes"])
        self.assertEqual(reviewed[1]["person"]["count"], 4)
        self.assertEqual(first_output.read_bytes(), first_bytes)
        self.assert_originals_preserved()

    def config_file(self, **changes):
        config = {
            "dry_run": True,
            "screen": {"calibrated": False, "coordinate_system": "primary-monitor-physical-pixels"},
            "grid": {"left": 100, "top": 100, "width": 600, "height": 600, "rows": 3, "columns": 3},
            "click_policy": {"min_interval_seconds": 0.25, "first_click_delay_seconds": 0.0},
        }
        for key, value in changes.items():
            config[key].update(value)
        path = self.root / "dry-run.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_cli_dry_run_has_3x3_coordinates_and_planned_offsets_only(self):
        result = self.cli("dry-run", "--config", self.config_file(), "--tiles", "0,4,8")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["source"], "manual_tile_indices_no_model")
        self.assertIs(output["calibrated"], False)
        self.assertEqual([(item["x"], item["y"]) for item in output["clicks"]], [(200, 200), (400, 400), (600, 600)])
        self.assertEqual([item["earliest_offset_seconds"] for item in output["clicks"]], [0.0, 0.25, 0.5])
        self.assertIs(output["timing"]["submission_included"], False)
        self.assertIn("provisional", output["timing"]["first_click_delay_status"])

    def test_cli_rejects_wrong_grid_and_interval_below_quarter_second(self):
        for changes, message in (
            ({"grid": {"rows": 2}}, "fixed at 3x3"),
            ({"click_policy": {"min_interval_seconds": 0.249}}, "at least 0.25"),
        ):
            with self.subTest(changes=changes):
                result = self.cli("dry-run", "--config", self.config_file(**changes), "--tiles", "0,4")
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)

    def test_cli_data_check_relation_leakage_exits_two_without_changing_files(self):
        records = deepcopy(self.records)
        records[0]["split"] = "train"
        records[1]["split"] = "test"
        records[1]["parent_id"] = records[0]["image_id"]
        path = self.root / "leakage.jsonl"
        save_jsonl(records, path)
        before = path.read_bytes()
        result = self.cli("data-check", "--manifest", path, "--root", self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("cross-split leakage", result.stderr)
        self.assertEqual(path.read_bytes(), before)
        self.assert_originals_preserved()

    def test_cli_group_split_preserves_relations_unknowns_and_existing_output(self):
        records = deepcopy(self.records)
        records[1]["parent_id"] = records[0]["image_id"]
        path = self.root / "related.jsonl"
        save_jsonl(records, path)
        before = path.read_bytes()
        output = self.root / "split.jsonl"
        arguments = ("data-split", "--manifest", path, "--root", self.root, "--output", output)
        result = self.cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        reviewed = load_jsonl(output)
        self.assertEqual(reviewed[0]["split"], reviewed[1]["split"])
        self.assertTrue(all(row["split"] in {"train", "val", "test"} for row in reviewed))
        self.assertTrue(all(row["labels"] == self.records[0]["labels"] for row in reviewed))
        self.assertTrue(all(row["person"]["count"] is None for row in reviewed))
        self.assertEqual(path.read_bytes(), before)
        output_before = output.read_bytes()
        repeated = self.cli(*arguments)
        self.assertEqual(repeated.returncode, 2)
        self.assertEqual(output.read_bytes(), output_before)
        self.assert_originals_preserved()


if __name__ == "__main__":
    unittest.main()
