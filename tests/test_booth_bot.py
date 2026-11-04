"""Synthetic screen/clock tests: no weights, native capture, network or clicks."""

import json
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from alpha_captcha.booth_bot import (
    BoothBotRunner, BoothLayout, BoothRunError, BoothScreenChanged,
    UnsupportedBoothTask, crop_screen_tiles, public_condition,
)
from alpha_captcha.tasks import TilePrediction


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class FakeScreen:
    def __init__(self, layout):
        self.window = "ALPHA BOT | CAPTCHA - Synthetic test"
        self.image = Image.new("RGB", (110, 110), "white")
        draw = ImageDraw.Draw(self.image)
        draw.rectangle((10, 10, 69, 69), fill="red")
        for index in range(9):
            row, column = divmod(index, 3)
            left, top = 10 + column * 21, 10 + row * 21
            draw.rectangle((left, top, left + 17, top + 17), fill=(index * 20, 90, 70))
        self.clicks, self.captures = [], 0
        self.change_after_click = False

    def title(self):
        return self.window

    def capture(self):
        self.captures += 1
        return self.image.copy()

    def click(self, x, y):
        self.clicks.append((x, y))
        if self.change_after_click:
            self.image.putpixel((10, 0), (1, 2, 3))


class FakePredictor:
    presence_metadata = {"profile": {"threshold": 0.5}}

    def __init__(self):
        self.inputs = []

    def predict_tiles(self, images):
        self.inputs.append(images)
        return [TilePrediction({"tree": 0.1, "building": 0.8 if i % 3 == 0 else 0.2,
                                "pond": 0.1}, 3 if i % 3 == 0 else 0) for i in range(9)]


class BoothBotTests(unittest.TestCase):
    def config(self, **changes):
        return {"url": "http://127.0.0.1:3000/bot", "expected_window_title": "ALPHA BOT | CAPTCHA",
                "calibrated": True, "grid": {"left": 10, "top": 10, "width": 60, "height": 60,
                                              "rows": 3, "columns": 3, "gap_x": 3, "gap_y": 3},
                "submit": {"x": 95, "y": 95},
                "question_guard": {"left": 10, "top": 0, "width": 30, "height": 8}, **changes}

    def runner(self, **kwargs):
        layout = BoothLayout.from_dict(self.config())
        screen, predictor, clock = FakeScreen(layout), FakePredictor(), FakeClock()
        return BoothBotRunner(predictor, screen, layout, clock=clock, sleep=clock.sleep, **kwargs), screen, predictor, clock

    def test_dry_run_captures_nine_pixel_tiles_without_native_input(self):
        runner, screen, predictor, clock = self.runner()
        report, before, after = runner.run_once({"task_type": "person_count", "operator": "gte", "n": 3})
        self.assertEqual(report["selected_tiles"], [0, 3, 6])
        self.assertEqual(screen.clicks, [])
        self.assertFalse(report["mouse_control_performed"])
        self.assertFalse(report["submit_performed"])
        self.assertEqual(report["planned_click_offsets_seconds"], [0.0, 0.25, 0.5])
        self.assertEqual(before.size, (60, 60))
        self.assertIsNone(after)
        self.assertEqual(clock.now, 0.0)
        for index, image in enumerate(predictor.inputs[0]):
            self.assertIsInstance(image, Image.Image)
            self.assertEqual(image.size, (18, 18))
            self.assertEqual(image.getpixel((0, 0)), (index * 20, 90, 70))
        json.dumps(report, allow_nan=False)

    def test_execute_uses_real_callback_intervals_and_submit_without_top_four(self):
        runner, screen, predictor, clock = self.runner()
        report, _, after = runner.run_once({"task_type": "building_present"}, execute=True)
        self.assertEqual(screen.clicks, [(19, 19), (19, 40), (19, 61), (95, 95)])
        self.assertEqual(report["selected_tiles"], [0, 3, 6])
        self.assertTrue(report["submit_performed"])
        self.assertTrue(all(interval >= 0.25 for interval in report["observed_os_call_intervals_seconds"]))
        self.assertEqual(after.size, (60, 60))
        last = report["click_events"][-1]["os_call_at_monotonic"]
        again, _, _ = runner.run_once({"task_type": "person_present"}, execute=True, question_id="next")
        self.assertGreaterEqual(again["click_events"][0]["os_call_at_monotonic"] - last, 0.25)

    def test_zero_selected_tiles_still_reports_the_submit_mouse_call(self):
        runner, screen, predictor, _ = self.runner()
        predictor.predict_tiles = lambda images: [TilePrediction({"pond": 0.1}, 0) for _ in images]
        report, _, _ = runner.run_once({"task_type": "pond_present"}, execute=True)
        self.assertEqual(report["selected_tiles"], [])
        self.assertEqual(report["tile_click_count"], 0)
        self.assertEqual(screen.clicks, [(95, 95)])
        self.assertTrue(report["mouse_control_attempted"])
        self.assertTrue(report["mouse_control_performed"])
        self.assertTrue(report["submit_performed"])

    def test_changed_visible_question_stops_remaining_clicks_and_submit(self):
        runner, screen, _, _ = self.runner()
        screen.change_after_click = True
        with self.assertRaises(BoothRunError) as caught:
            runner.run_once({"task_type": "person_present"}, execute=True)
        self.assertEqual(screen.clicks, [(19, 19)])
        self.assertEqual(len(caught.exception.report["click_events"]), 1)
        self.assertFalse(caught.exception.report["submit_performed"])
        self.assertEqual(caught.exception.report["error_type"], "BoothScreenChanged")

    def test_foreground_or_uncalibrated_rejection_precedes_capture_and_click(self):
        runner, screen, _, _ = self.runner()
        screen.window = "An unrelated page"
        with self.assertRaises(BoothScreenChanged):
            runner.run_once({"task_type": "person_present"}, execute=True)
        self.assertEqual(screen.captures, 0)
        self.assertEqual(screen.clicks, [])
        runner.layout = BoothLayout.from_dict(self.config(calibrated=False))
        with self.assertRaisesRegex(ValueError, "calibrated"):
            runner.run_once({"task_type": "person_present"}, execute=True)

    def test_tree_count_fails_closed_without_actual_ml_adapter(self):
        runner, screen, predictor, _ = self.runner()
        with self.assertRaises(UnsupportedBoothTask):
            runner.run_once({"task_type": "tree_count", "operator": "gte", "n": 3}, execute=True)
        self.assertEqual(screen.captures, 0)
        self.assertEqual(predictor.inputs, [])

    def test_explicit_tree_ml_adapter_supplies_decisions_without_fabricated_counts(self):
        class TreeAdapter:
            def predict_at_least_three(self, images):
                self.images = images
                return [True, False, True, False, False, False, False, False, False]
        tree = TreeAdapter()
        runner, screen, predictor, _ = self.runner(tree_predictor=tree)
        report, _, _ = runner.run_once({"task_type": "tree_count", "operator": "gte", "n": 3})
        self.assertEqual(report["selected_tiles"], [0, 2])
        self.assertEqual(predictor.inputs, [])
        self.assertTrue(all("person_count" not in item for item in report["predictions"]))
        self.assertEqual(len(tree.images), 9)

    def test_public_phase_guard_stops_clicks_without_reading_answers(self):
        runner, screen, _, _ = self.runner()
        calls = []
        def public_guard():
            calls.append(True)
            return len(calls) == 1
        with self.assertRaises(BoothRunError):
            runner.run_once({"task_type": "person_present"}, execute=True, public_guard=public_guard)
        self.assertEqual(screen.clicks, [])

    def test_opponent_winning_mid_queue_cancels_clicks_and_submission(self):
        runner, screen, _, _ = self.runner()
        state = {"phase": "playing"}
        original_click = screen.click
        def first_click_then_opponent_wins(x, y):
            original_click(x, y)
            state["phase"] = "result"
        screen.click = first_click_then_opponent_wins
        with self.assertRaises(BoothRunError) as caught:
            runner.run_once({"task_type": "person_present"}, execute=True,
                            question_id="public-round", public_guard=lambda: state["phase"] == "playing")
        self.assertEqual(screen.clicks, [(19, 19)])
        self.assertFalse(caught.exception.report["submit_performed"])
        self.assertEqual(caught.exception.report["error_type"], "BoothScreenChanged")

    def test_same_question_cannot_reclick_predictions_but_dry_run_is_not_an_attempt(self):
        runner, screen, predictor, _ = self.runner()
        runner.run_once({"task_type": "person_present"}, question_id="one-public-round")
        runner.run_once({"task_type": "person_present"}, execute=True, question_id="one-public-round")
        count, captures, predictions = len(screen.clicks), screen.captures, len(predictor.inputs)
        with self.assertRaisesRegex(ValueError, "already had an OS attempt"):
            runner.run_once({"task_type": "person_present"}, execute=True, question_id="one-public-round")
        self.assertEqual(len(screen.clicks), count)
        self.assertEqual(screen.captures, captures)
        self.assertEqual(len(predictor.inputs), predictions)

    def test_rejects_answer_fields_uncontrolled_hosts_and_invalid_geometry(self):
        with self.assertRaises(ValueError):
            public_condition({"task_type": "person_present", "answer_tiles": [0]})
        for changes in ({"url": "https://third-party.example/captcha"}, {"min_interval_seconds": 0.249},
                        {"calibrated": 1}, {"expected_window_title": "Browser"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                BoothLayout.from_dict(self.config(**changes))
        runner, screen, _, _ = self.runner()
        with self.assertRaises(ValueError):
            crop_screen_tiles(Image.new("RGB", (20, 20)), runner.layout.grid)

    def cli_module(self):
        spec = importlib.util.spec_from_file_location(
            "booth_cli_fixture", Path(__file__).resolve().parents[1] / "scripts/run_booth_bot.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_room_projection_retains_only_public_timing_and_general_condition(self):
        cli = self.cli_module()
        state = {"phase": "playing", "roundId": "opaque-round", "startAt": 123000,
                 "topic": {"condition": {"task_type": "person_count", "operator": "gte", "n": 3},
                           "answer_tiles": [0, 4]},
                 "tiles": [{"id": "hidden-identity", "url": "/do-not-use.jpg", "answer": True}]}
        with patch.object(cli.PublicRoomSession, "_request", side_effect=[
                {"roomId": "opaque-room", "token": "private-role-token", "state": state}, state]):
            session = cli.PublicRoomSession("http://127.0.0.1:3000", "TEST01")
            public = session.view()
        self.assertEqual(set(public), {"phase", "roundId", "startAt", "condition"})
        self.assertEqual(public["condition"], {"task_type": "person_count", "operator": "gte", "n": 3})
        self.assertNotIn("private-role-token", json.dumps(public))
        self.assertNotIn("hidden-identity", json.dumps(public))
        self.assertNotIn("answer", json.dumps(public))

    def test_room_http_requests_identify_the_bot_and_scope_the_bearer_token(self):
        cli = self.cli_module()
        responses = iter([
            {"roomId": "synthetic-room-only", "token": "synthetic-role-token"},
            {"phase": "lobby", "roundId": None, "startAt": None, "topic": None, "tiles": []},
        ])
        requests = []
        class Response:
            def __init__(self, value):
                self.raw = json.dumps(value).encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                self.limit = limit
                return self.raw
        def open_fixture(request, *, timeout):
            self.assertEqual(timeout, 5)
            requests.append(request)
            return Response(next(responses))
        with patch.object(cli, "urlopen", side_effect=open_fixture):
            session = cli.PublicRoomSession("https://bot.marulee.dev", "TESTONLY")
            state = session.view()
        self.assertEqual(state, {"phase": "lobby", "roundId": None, "startAt": None})
        self.assertEqual([request.get_method() for request in requests], ["POST", "GET"])
        self.assertEqual(requests[0].full_url, "https://bot.marulee.dev/api/rooms/join")
        self.assertEqual(json.loads(requests[0].data), {"code": "TESTONLY", "role": "bot"})
        self.assertIsNone(requests[1].data)
        for request in requests:
            headers = {key.lower(): value for key, value in request.header_items()}
            self.assertEqual(headers["user-agent"], "AlphaCaptchaBoothBot/1.0")
            self.assertEqual(headers["accept"], "application/json")
        first = {key.lower(): value for key, value in requests[0].header_items()}
        second = {key.lower(): value for key, value in requests[1].header_items()}
        self.assertNotIn("authorization", first)
        self.assertEqual(second["authorization"], "Bearer synthetic-role-token")

    def test_tree_checkpoint_is_lazy_and_reused_without_runtime_download(self):
        cli = self.cli_module()
        class TreeFixture:
            provenance = {"weights_sha256": "synthetic"}
            last_detections = [{"tree_count": 3}]
            def __init__(self, model_dir, *, device):
                self.model_dir, self.device = model_dir, device
            def predict_at_least_three(self, images):
                return [True] * len(images)
        with patch("alpha_captcha.tree_model.TreeCountPredictor", side_effect=TreeFixture) as builder:
            lazy = cli.LazyTreePredictor(device="cpu", model_dir=Path("fixture-local-model"))
            self.assertIsNone(lazy.provenance)
            self.assertEqual(builder.call_count, 0)
            self.assertEqual(lazy.predict_at_least_three([Image.new("RGB", (10, 10))]), [True])
            lazy.predict_at_least_three([Image.new("RGB", (10, 10))])
            self.assertEqual(builder.call_count, 1)
            self.assertEqual(lazy.last_loading_seconds, 0.0)
            self.assertEqual(lazy.provenance, TreeFixture.provenance)

    def test_multiple_games_cli_rejected_before_layout_models_or_native_gui(self):
        cli = self.cli_module()
        with tempfile.TemporaryDirectory() as temporary:
            args = ["run_booth_bot.py", "--config", str(Path(temporary) / "absent-layout.json"),
                    "--output", str(Path(temporary) / "unused-output"), "--rounds", "2", "--execute"]
            with patch("sys.argv", args), patch("sys.stderr", new_callable=io.StringIO) as error, \
                    patch.object(cli.TorchTilePredictor, "from_checkpoints") as load, \
                    patch.object(cli, "PyAutoGuiScreen") as native:
                with self.assertRaises(SystemExit) as caught:
                    cli.main()
            self.assertEqual(caught.exception.code, 2)
            self.assertIn("--rounds", error.getvalue())
            self.assertEqual(load.call_count, 0)
            self.assertEqual(native.call_count, 0)
            self.assertFalse((Path(temporary) / "unused-output").exists())


if __name__ == "__main__":
    unittest.main()
