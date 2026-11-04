"""Pure geometry/file/hotkey fixtures only: no native desktop, screenshots or input."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/calibrate_booth_bot.py"
    spec = importlib.util.spec_from_file_location("booth_calibration_fixture", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.cli = module()
        self.points = {"grid_top_left": (660, 268), "grid_bottom_right": (1260, 868),
                       "submit": (1185, 906), "guard_top_left": (660, 170),
                       "guard_bottom_right": (1130, 252)}

    def test_valid_manual_geometry_matches_runtime_schema_and_tile_centers(self):
        layout = self.cli.build_layout(self.points, (1920, 1080))
        parsed = self.cli.BoothLayout.from_dict(layout)
        self.assertTrue(parsed.calibrated)
        self.assertEqual(parsed.grid.center(0), (757, 365))
        self.assertEqual(parsed.grid.center(8), (1162, 770))
        self.assertEqual(layout["question_guard"], {"left": 660, "top": 170, "width": 470, "height": 82})

    def test_mismeasurements_offscreen_small_grid_and_changing_regions_rejected(self):
        changes = [
            {"submit": (0, 0)}, {"submit": (1185, 1080)}, {"grid_top_left": (-1, 268)},
            {"grid_bottom_right": (1400, 868)}, {"grid_bottom_right": (760, 368)},
            {"guard_bottom_right": (1130, 300)}, {"guard_bottom_right": (700, 180)},
            {"grid_top_left": (True, 268)}, {"submit": (1921, 906)},
        ]
        for replacement in changes:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                self.cli.build_layout({**self.points, **replacement}, (1920, 1080))
        with self.assertRaises(ValueError):
            self.cli.build_layout(self.points, (1920, 1080), gap_x=101)

    def test_existing_file_is_preserved_unless_replacement_is_explicit_and_backed_up(self):
        layout = self.cli.build_layout(self.points, (1920, 1080))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "booth-bot.local.json"
            original = b'{"calibrated": false, "operator_note": "retain this"}\n'
            output.write_bytes(original)
            with self.assertRaises(FileExistsError):
                self.cli.write_layout(output, layout)
            self.assertEqual(output.read_bytes(), original)
            backup = self.cli.write_layout(output, layout, replace=True)
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), layout)
            self.assertFalse(output.with_name(output.name + ".pending").exists())

    def test_escape_cancels_before_any_cursor_or_title_query(self):
        class EscRecorder:
            def down(self, key):
                return key == "ESC"
            def position(self):
                raise AssertionError("cancellation must not query cursor")
            def title(self):
                raise AssertionError("cancellation must not query title")
        with self.assertRaises(KeyboardInterrupt):
            self.cli.collect_points(EscRecorder(), notify=lambda _: None)

    def test_cancelled_user_session_does_not_replace_existing_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "booth-bot.local.json"
            original = b'{"calibrated": false}\n'
            output.write_bytes(original)
            class FakeRecorder:
                def screen_size(self):
                    return 1920, 1080
            with patch("sys.argv", ["calibrate", "--output", str(output), "--replace"]), \
                    patch.object(self.cli, "WindowsPointerRecorder", return_value=FakeRecorder()), \
                    patch.object(self.cli, "collect_points", side_effect=KeyboardInterrupt), \
                    patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(self.cli.main(), 130)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(list(Path(temporary).iterdir()), [output])

    def test_existing_output_is_rejected_before_any_native_adapter_initialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "booth-bot.local.json"
            output.write_text("{}", encoding="utf-8")
            with patch("sys.argv", ["calibrate", "--output", str(output)]), \
                    patch.object(self.cli, "WindowsPointerRecorder") as native, \
                    patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit):
                    self.cli.main()
            self.assertEqual(native.call_count, 0)


if __name__ == "__main__":
    unittest.main()
