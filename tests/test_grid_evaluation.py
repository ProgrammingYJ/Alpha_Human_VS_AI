"""Synthetic cache/manifest tests: no model execution, network or mouse input."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from alpha_captcha.dataset import save_jsonl, sha256_file
from alpha_captcha import grid_evaluation as grids
from alpha_captcha.tasks import TaskCondition, TilePrediction


class GridEvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = self.root / "data/manifests/fixture.jsonl"
        self.folder = self.root / "models/checkpoints/fixture"
        self.folder.mkdir(parents=True)
        self.condition = TaskCondition("tree_present")

    def rows(self, positives=4, negatives=5, *, split="val", start=0):
        result = []
        for number in range(start, start + positives + negatives):
            positive = number < start + positives
            path = self.root / f"data/raw/kaggle/fixture/{number}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (12, 8), (number % 256, number // 256, 123)).save(path)
            result.append({
                "schema_version": 1, "source": "kaggle", "dataset_ref": "fixture/grids",
                "dataset_version": 1, "image_id": str(number), "image_path": path.relative_to(self.root).as_posix(),
                "group_id": f"group-{number}", "sha256": sha256_file(path), "split": split,
                "original_split": None, "labels": {"tree": positive, "building": positive, "pond": None},
                "person": {"present": positive, "count": 5 if positive else 0,
                           "count_status": "verified", "boxes": None, "iscrowd": False},
                "usage_note": "Synthetic fixture, not a dataset licence.",
            })
        return result

    def save(self, value, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
        return path

    def presence(self, rows):
        save_jsonl(rows, self.manifest)
        checkpoint = self.folder / "presence.pt"
        checkpoint.write_bytes(b"synthetic checkpoint; never loaded")
        report = self.save({
            "manifest_sha256": sha256_file(self.manifest), "school_data_used": False,
            "profile": {"threshold": .5}, "checkpoint": checkpoint.relative_to(self.root).as_posix(),
            "checkpoint_sha256": sha256_file(checkpoint),
        }, self.folder / "report.json")
        raw = self.save([{
            "image_id": row["image_id"], "image_path": row["image_path"], "split": row["split"],
            "scores": {"tree": .9 if row["labels"]["tree"] else .1,
                       "building": .9 if row["labels"]["building"] else .1, "pond": .2},
            "targets_for_evaluator_only": {"tree": not row["labels"]["tree"]},
            "decisions": {"tree": not row["labels"]["tree"]},
        } for row in rows if row["split"] == "val"], self.folder / "predictions-val.json")
        cache = grids.adapt_presence_predictions(self.manifest, raw, report, self.root)
        cache_path = self.save(cache, self.root / "cache.json")
        return cache, cache_path

    def evaluate(self, path, **kwargs):
        return grids.evaluate_cached_grids(self.manifest, path, self.root, self.condition, seed=20261022, **kwargs)

    def test_disjoint_seeded_grids_and_exact_set_do_not_claim_target(self):
        rows = self.rows(8, 10)
        _, cache = self.presence(rows)
        report = self.evaluate(cache, grids=2)
        self.assertEqual(report["status"], "evaluated")
        self.assertEqual(report["exact_set"], {"successes": 2, "total": 2, "rate": 1.0})
        self.assertEqual(report["reuse"]["unique_images"], 18)
        self.assertEqual(report["reuse"]["unique_groups"], 18)
        self.assertEqual(report["reuse"]["reused_image_occurrences"], 0)
        self.assertIsNone(report["target_achieved"])
        self.assertIsNone(report["confidence_interval"])
        self.assertFalse(report["independent_population_trials_claimed"])
        self.assertEqual(report, self.evaluate(cache, grids=2))
        for grid in report["grids"]:
            self.assertEqual(len(grid["tiles"]), 9)
            self.assertEqual(len(grid["answer_tiles"]), 4)
            self.assertEqual(len({tile["component"] for tile in grid["tiles"]}), 9)

    def test_insufficient_val_never_falls_back_to_train_or_test(self):
        rows = self.rows(3, 5) + self.rows(8, 10, split="train", start=20) + self.rows(8, 10, split="test", start=50)
        _, cache = self.presence(rows)
        report = self.evaluate(cache)
        self.assertEqual(report["status"], "insufficient_data")
        self.assertEqual(report["coverage"]["available_disjoint_grids"], 0)
        self.assertEqual(report["exact_set"]["total"], 0)
        self.assertTrue(report["no_split_fallback"])
        with self.assertRaisesRegex(ValueError, "val only"):
            grids.plan_validation_grids(rows, self.condition, split="test")

    def test_shared_lineage_cannot_fill_two_tiles_and_mixed_groups_work(self):
        rows = self.rows()
        rows[0]["parent_id"] = "shared-origin"
        rows[1]["parent_id"] = "shared-origin"
        plan = grids.plan_validation_grids(rows, self.condition)
        self.assertEqual(plan["available_disjoint_grids"], 0)
        rows = self.rows(6, 7, start=40)
        # Four mixed groups, two positive-only, three negative-only = 9 groups.
        for number in range(4):
            rows[6 + number]["group_id"] = rows[number]["group_id"]
        plan = grids.plan_validation_grids(rows, self.condition)
        self.assertEqual(plan["available_disjoint_grids"], 1)
        self.assertEqual(len({tile["component"] for tile in plan["grids"][0]["tiles"]}), 9)

    def test_reused_hundred_grids_report_dependence(self):
        _, cache = self.presence(self.rows())
        report = self.evaluate(cache, grids=100, mode="reuse")
        self.assertEqual(report["exact_set"]["successes"], 100)
        self.assertEqual(report["reuse"]["unique_grid_compositions"], 1)
        self.assertEqual(report["reuse"]["reused_image_occurrences"], 891)
        self.assertIsNone(report["target_achieved"])
        self.assertIsNone(report["confidence_interval"])

    def test_cache_identity_payload_and_source_hash_guards(self):
        rows = self.rows()
        original, path = self.presence(rows)
        for field, value in (("source", "school"), ("group_id", "other"), ("split", "test"), ("sha256", "0" * 64)):
            with self.subTest(field=field):
                cache = deepcopy(original)
                cache["predictions"][0][field] = value
                cache["predictions_sha256"] = grids._digest(cache["predictions"])
                self.save(cache, path)
                with self.assertRaisesRegex(ValueError, "differs from manifest"):
                    self.evaluate(path)
        cache = deepcopy(original)
        cache["predictions"][0]["presence_scores"]["tree"] = .6
        self.save(cache, path)
        with self.assertRaisesRegex(ValueError, "payload hash"):
            self.evaluate(path)
        self.save(original, path)
        (self.folder / "presence.pt").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "file hash changed"):
            self.evaluate(path)

    def test_missing_predictions_do_not_select_easier_subset(self):
        cache, path = self.presence(self.rows(8, 10))
        cache["predictions"].pop()
        cache["predictions_sha256"] = grids._digest(cache["predictions"])
        self.save(cache, path)
        report = self.evaluate(path)
        self.assertEqual(report["missing_prediction_images"], 1)
        self.assertEqual(report["status"], "insufficient_data")
        self.assertEqual(report["exact_set"]["total"], 0)

    def test_selection_never_receives_truth_or_k_and_all_positive_fails(self):
        cache, path = self.presence(self.rows())
        for prediction in cache["predictions"]:
            prediction["presence_scores"]["tree"] = .9
        cache["predictions_sha256"] = grids._digest(cache["predictions"])
        self.save(cache, path)
        with patch.object(grids, "select_tiles", wraps=grids.select_tiles) as selection:
            report = self.evaluate(path)
        args = selection.call_args.args
        self.assertEqual(len(args), 3)
        self.assertTrue(all(isinstance(item, TilePrediction) for item in args[0]))
        self.assertEqual(args[1], self.condition)
        self.assertFalse(selection.call_args.kwargs)
        self.assertEqual(report["exact_set"]["successes"], 0)
        self.assertEqual(len(report["grids"][0]["selected_tiles"]), 9)

    def test_person_adapter_ignores_actual_count_and_supports_all_n(self):
        rows = self.rows()
        save_jsonl(rows, self.manifest)
        checkpoint = self.folder / "person.pt"
        checkpoint.write_bytes(b"synthetic person checkpoint")
        report = self.save({
            "metadata": {"manifest_sha256": sha256_file(self.manifest), "school_data_used": False,
                         "checkpoint_sha256": sha256_file(checkpoint)},
            "evaluation": {"val": {"predictions": [{
                "image_id": row["image_id"], "sha256": row["sha256"],
                "person_count": row["person"]["count"], "actual_count": 999,
            } for row in rows]}},
        }, self.folder / "report.json")
        cache = grids.adapt_person_report(self.manifest, report, self.root)
        self.assertEqual({row["person_count"] for row in cache["predictions"]}, {0, 5})
        path = self.save(cache, self.root / "cache.json")
        for condition in [TaskCondition("person_present"), *(TaskCondition("person_count", "gte", n) for n in range(2, 6))]:
            with self.subTest(condition=condition):
                result = grids.evaluate_cached_grids(self.manifest, path, self.root, condition)
                self.assertEqual(result["exact_set"]["successes"], 1)
        rows[0]["person"].update(count=None, count_status="crowd", iscrowd=True)
        self.assertEqual(grids.plan_validation_grids(rows, TaskCondition("person_present"))["unknown_images_excluded"], 1)
        self.assertEqual(grids.plan_validation_grids(rows, TaskCondition("person_count", "gte", 2))["available_disjoint_grids"], 0)

    def test_school_and_cross_split_lineage_are_rejected(self):
        rows = self.rows()
        rows[0]["source"] = "school"
        with self.assertRaises(ValueError):
            self.presence(rows)
        self.manifest.unlink()
        rows = self.rows() + self.rows(1, 0, split="test", start=40)
        rows[-1]["group_id"] = rows[0]["group_id"]
        with self.assertRaisesRegex(ValueError, "split"):
            self.presence(rows)

    def test_cli_evaluates_cache_without_overwriting_result(self):
        _, cache = self.presence(self.rows())
        condition = self.save({"task_type": "tree_present"}, self.root / "condition.json")
        output = self.root / "grid-report.json"
        script = Path(__file__).resolve().parents[1] / "scripts/evaluate_grids.py"
        command = [sys.executable, str(script), "evaluate", "--manifest", str(self.manifest),
                   "--root", str(self.root), "--cache", str(cache), "--condition", str(condition),
                   "--output", str(output), "--seed", "20261022"]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        previous = output.read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(output.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
