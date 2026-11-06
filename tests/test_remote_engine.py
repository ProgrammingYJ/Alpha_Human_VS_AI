"""Remote protocol, actual-pixel boundary and two-lane scheduling fakes; no GUI/network/GPU."""

from contextlib import redirect_stdout, redirect_stderr
from io import BytesIO, StringIO
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from PIL import Image

from alpha_captcha import remote_engine as remote
from alpha_captcha.tasks import TilePrediction


ROUND = "11111111-1111-4111-8111-111111111111"
ROOM = "22222222-2222-4222-8222-222222222222"
TOKEN = "z" * 43
CODE = "ABCDEFGH"
CONDITION = {"task_type": "building_present"}


def state(phase="playing", lane="A", *, selected=(), sequence=0):
    return {"phase": phase, "roundId": ROUND if phase != "lobby" else None, "roundNumber": 0 if phase == "lobby" else 1,
            "startRequest": None, "startAt": None, "lastStartCancellationReason": None,
            "topic": {"condition": dict(CONDITION)} if phase in {"playing", "result"} else None,
            "tiles": [{"id": f"private-{index}", "url": f"/api/photos/00000000-0000-4000-8000-{index:012d}"}
                      for index in range(9)] if phase in {"playing", "result"} else [],
            "remote": {"mode": "remote", "lane": lane, "selectedIndices": list(selected), "sequence": sequence,
                       "gpuReservationSupported": True},
            "answerTileIds": ["THIS MUST NEVER REACH MODEL"], "originalFilename": "person3.jpg",
            "code": CODE, "roomId": ROOM}


def snapshot(phase="playing", lane="A"):
    return remote.PublicSnapshot.from_state(state(phase, lane), lane)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeResponse:
    def __init__(self, data, *, headers=None):
        self.data, self.headers = data, headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, count):
        return self.data[:count]


class FakeTransport:
    def __init__(self, lane="A"):
        self.lane, self.calls, self.errors = lane, [], []

    def json(self, path, *, token=None, body=None):
        self.calls.append((path, token, json.loads(json.dumps(body))))
        if path.endswith("join"):
            return {"roomId": ROOM, "token": TOKEN, "state": state("lobby", self.lane)}
        if self.errors:
            raise self.errors.pop(0)
        if body and body.get("action") == "select":
            return {"state": state(lane=self.lane, selected=[body["tileIndex"]], sequence=body["sequence"])}
        return {"state": state(lane=self.lane)}


class FakePump:
    def __init__(self, room):
        self.room, self.stage, self.failed = room, "ready", threading.Event()
        self.closed = False

    def start(self):
        self.room.heartbeat(self.stage)

    def bind(self, current):
        self.stage = "ready" if current.phase == "lobby" else "inferencing"

    def set_stage(self, stage, *, snapshot=None):
        self.stage = stage
        self.room.heartbeat(stage)

    def close(self):
        self.closed = True


class FakeRoom:
    def __init__(self, clock, lane="A", *, phases=("playing",), correct=True):
        self.lane, self.clock, self.phases, self.correct = lane, clock, list(phases), correct
        self.events, self.submits, self.heartbeats, self.submitted = [], 0, [], False
        self.views = 0

    def view(self):
        self.views += 1
        if self.submitted:
            return snapshot("result", self.lane)
        phase = self.phases.pop(0) if len(self.phases) > 1 else self.phases[0]
        return snapshot(phase, self.lane)

    def heartbeat(self, stage, **kwargs):
        if self.submitted and self.correct:
            raise remote.RemoteEngineError("round_ended", status=409)
        if stage == "ready" and self.views > 0 and self.phases[0] == "countdown":
            raise remote.RemoteEngineError("round_in_progress", status=409)
        self.heartbeats.append(stage)

    def pixels(self, current):
        self.clock.sleep(0.2)
        return [Image.new("RGB", (4, 4), (index, 0, 0)) for index in range(9)]

    def select(self, round_id, sequence, tile_index):
        self.events.append((sequence, tile_index, self.clock()))
        self.clock.sleep(0.125)  # ACK includes real network/server latency.

    def submit(self, round_id):
        self.submits += 1
        self.submitted = True
        return {"state": state("result" if self.correct else "playing", self.lane),
                "correct": self.correct, "elapsedMs": 2345}


class FakeModels:
    def __init__(self, selected=(0, 4, 8)):
        self.selected, self.calls = list(selected), 0

    def infer(self, images, condition, *, active, timings, clock):
        self.calls += 1
        assert len(images) == 9 and all(image.mode == "RGB" and not image.info for image in images)
        assert condition == CONDITION and active()
        timings.update(gpu_queue_seconds=0.0, inference_seconds=0.0)
        return self.selected, [{"person_count": 0}] * 9


class NoThreadPump(remote.HeartbeatPump):
    def start(self):
        self.beat()


class PersistentTransport:
    """A fake human starts/reset rounds independently of the PC capability."""
    def __init__(self):
        self.phase, self.number, self.round_id = "lobby", 0, None
        self.selected, self.sequence, self.result_polls = [], 0, 0
        self.joins, self.select_events, self.heartbeats, self.authenticated = 0, [], [], []

    def public(self):
        current = state(self.phase, selected=self.selected, sequence=self.sequence)
        current.update(roundId=self.round_id, roundNumber=self.number)
        return current

    def json(self, path, *, token=None, body=None):
        if path.endswith("join"):
            self.joins += 1
            return {"roomId": ROOM, "token": TOKEN, "state": self.public()}
        self.authenticated.append(token)
        if body is None:
            if self.phase == "result":
                self.result_polls += 1
                if self.result_polls >= 2:
                    # This is the fake human /next action: room/token and
                    # round number persist, while current-round state resets.
                    self.phase, self.round_id, self.selected, self.sequence = "lobby", None, [], 0
            return self.public()
        action = body["action"]
        if action == "heartbeat":
            self.heartbeats.append((body["stage"], body["roundId"], body["roundNumber"]))
            if (body["roundId"], body["roundNumber"]) != (self.round_id, self.number):
                raise remote.RemoteEngineError("round_changed", status=409)
            if body["stage"] == "ready":
                if self.phase != "lobby":
                    raise remote.RemoteEngineError("round_in_progress", status=409)
                self.number += 1
                self.round_id = f"{self.number:08x}-1111-4111-8111-111111111111"
                self.phase = "playing"  # Fake human start after this ready ACK.
        elif action == "select":
            self.assert_current(body)
            if body["sequence"] != self.sequence + 1:
                raise AssertionError("sequence did not reset at next participant")
            self.sequence = body["sequence"]
            self.selected.append(body["tileIndex"])
            self.select_events.append((self.number, self.sequence, body["tileIndex"]))
        elif action == "submit":
            self.assert_current(body)
            self.phase, self.result_polls = "result", 0
            return {"state": self.public(), "correct": True, "elapsedMs": 1234}
        return {"state": self.public()}

    def assert_current(self, body):
        if self.phase != "playing" or body["roundId"] != self.round_id:
            raise remote.RemoteEngineError("round_changed", status=409)

    def pixels(self, path):
        return Image.new("RGB", (4, 4))


class RemoteProtocolTests(unittest.TestCase):
    def test_controlled_origin_and_endpoint_boundary_excludes_redirects_metadata_and_auth(self):
        for allowed in ("http://127.0.0.1:5186", "http://localhost:5111/", "http://[::1]:5111", "https://bot.marulee.dev"):
            self.assertTrue(remote.controlled_origin(allowed))
        for denied in ("https://evil.example", "http://bot.marulee.dev", "https://bot.marulee.dev:444", "https://bot.marulee.dev/anything",
                       "https://bot.marulee.dev?token=x", "https://user:secret@bot.marulee.dev", "https://bot.marulee.dev.evil.example"):
            with self.subTest(denied=denied), self.assertRaises(ValueError):
                remote.controlled_origin(denied)
        transport = remote.ControlledTransport("http://localhost:5111", opener_factory=lambda: self.fail("must not request"))
        for path in ("https://evil.example/api/photos/" + ROUND, "//evil.example/", "/api/photos/" + ROUND + "?label=person",
                     "/api/photos/../admin", "/api/photos/known-answer.jpg", "/api/rooms/" + ROOM):
            with self.subTest(path=path), self.assertRaises(ValueError):
                transport.pixels(path)
        with self.assertRaises(ValueError):
            transport._read("/api/photos/" + ROUND, image=True, token=TOKEN)
        self.assertIsNone(remote.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example"))

    def test_download_has_no_bearer_and_only_decoded_rgb_pixels_without_source_metadata(self):
        png = BytesIO()
        image = Image.new("RGBA", (4, 4), (4, 5, 6, 255))
        image.save(png, format="PNG")
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                return FakeResponse(png.getvalue())
        result = remote.ControlledTransport("http://localhost", opener_factory=Opener).pixels("/api/photos/" + ROUND)
        self.assertEqual(result.mode, "RGB")
        self.assertEqual(result.info, {})
        self.assertFalse(hasattr(result, "filename"))
        self.assertIsNone(calls[0].get_header("Authorization"))
        self.assertEqual(calls[0].get_header("User-agent"), remote.USER_AGENT)

    def test_size_limits_error_bodies_and_retry_header_never_expose_credentials(self):
        class TooLarge:
            def open(self, request, timeout):
                return FakeResponse(b"", headers={"Content-Length": str(remote.MAX_IMAGE_BYTES + 1)})
        with self.assertRaises(remote.RemoteEngineError) as caught:
            remote.ControlledTransport("http://localhost", opener_factory=TooLarge).pixels("/api/photos/" + ROUND)
        self.assertEqual(caught.exception.code, "response_too_large")
        class ErrorOpener:
            def open(self, request, timeout):
                raise HTTPError("https://SECRET", 429, TOKEN, {"Retry-After": "NaN"}, BytesIO(json.dumps({"code": TOKEN, "token": TOKEN, "message": CODE}).encode()))
        with self.assertRaises(remote.RemoteEngineError) as caught:
            remote.ControlledTransport("http://localhost", opener_factory=ErrorOpener).json("/api/rooms/join", body={"code": CODE})
        self.assertEqual(caught.exception.code, "request_failed")
        self.assertEqual(caught.exception.retry_after, 0)
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertNotIn(CODE, str(caught.exception))

    def test_session_reset_HTTP_errors_preserve_bounded_code_status_without_echoing_server_credentials(self):
        raw_message = "untrusted server text with " + TOKEN + " and " + CODE
        for expected_code, status in (("room_reset", 410), ("session_reset_unavailable", 503),
                                      ("lane_disabled", 410), ("operation_mode_unavailable", 503)):
            with self.subTest(code=expected_code):
                class ErrorOpener:
                    def open(self, request, timeout):
                        raise HTTPError("https://PRIVATE-ERROR-URL", status, raw_message, {}, BytesIO(
                            json.dumps({"code": expected_code, "error": raw_message, "token": TOKEN}).encode()))
                transport = remote.ControlledTransport("http://localhost", opener_factory=ErrorOpener)
                with self.assertRaises(remote.RemoteEngineError) as caught:
                    transport.json("/api/rooms/" + ROOM, token=TOKEN)
                failure = caught.exception
                self.assertEqual((failure.code, failure.status), (expected_code, status))
                self.assertEqual(str(failure), expected_code)
                diagnostic = remote.safe_diagnostic(failure.code)
                self.assertLess(len(diagnostic), 200)
                self.assertNotEqual(diagnostic, remote.safe_diagnostic("unknown_fixture"))
                public_report = json.dumps({"code": failure.code, "status": failure.status,
                                            "error": str(failure), "diagnostic": diagnostic}, ensure_ascii=False)
                for private in (TOKEN, CODE, raw_message, "PRIVATE-ERROR-URL"):
                    self.assertNotIn(private, public_report)
                    self.assertNotIn(private, repr(failure))

    def test_projection_refuses_wrong_lane_and_truth_bearing_condition_and_only_retains_public_model_inputs(self):
        current = snapshot()
        self.assertEqual(set(vars(current)), {"phase", "round_id", "condition", "photo_paths", "lane", "round_number", "start_request", "start_at", "cancellation_reason", "gpu_reservation_supported", "selection_plan_supported", "bot_attempted", "image_barrier_supported", "image_load_id"})
        self.assertEqual(current.condition, CONDITION)
        self.assertNotIn("THIS MUST", repr(current))
        self.assertNotIn(CODE, repr(current))
        wrong = state()
        wrong["topic"]["condition"]["answer_count"] = 4
        with self.assertRaises(remote.RemoteEngineError):
            remote.PublicSnapshot.from_state(wrong, "A")
        with self.assertRaises(remote.RemoteEngineError):
            remote.PublicSnapshot.from_state(state(lane="B"), "A")
        missing = state(); missing["roundId"] = None
        with self.assertRaises(remote.RemoteEngineError):
            remote.PublicSnapshot.from_state(missing, "A")
        repeated = state(); repeated["tiles"][1]["url"] = repeated["tiles"][0]["url"]
        with self.assertRaises(remote.RemoteEngineError):
            remote.PublicSnapshot.from_state(repeated, "A")

    def test_engine_capability_join_and_same_sequence_retry_after_network_and_429(self):
        transport, waits = FakeTransport(), []
        room = remote.EngineRoom(transport, "A", CODE, sleep=waits.append)
        self.assertEqual(transport.calls[0][2], {"role": "engine", "lane": "A", "code": CODE})
        transport.errors = [remote.RemoteEngineError("connection_failed"), remote.RemoteEngineError("selection_too_fast", status=429, retry_after=2)]
        room.select(ROUND, 1, 7)
        requests = [call for call in transport.calls if call[2] and call[2].get("action") == "select"]
        self.assertEqual(len(requests), 3)
        self.assertEqual([call[2] for call in requests], [requests[0][2]] * 3)
        self.assertTrue(all(call[1] == TOKEN for call in requests))
        self.assertEqual(waits, [1, 2])
        with self.assertRaises(remote.RemoteEngineError):
            remote.EngineRoom(FakeTransport("B"), "A", CODE)
        with self.assertRaises(ValueError):
            room.select(ROUND, True, 3)


class RemoteRuntimeTests(unittest.TestCase):
    def test_continuous_result_idle_does_not_expire_after_one_round_wait_limit(self):
        clock, cancel, models, reports = FakeClock(), threading.Event(), FakeModels(), []
        room = FakeRoom(clock)
        room.view = lambda: snapshot("result")
        def idle_sleep(seconds):
            clock.sleep(seconds)
            if clock() >= 3:
                cancel.set()
        completed = remote.run_room_session(room, models, report_sink=reports.append, cancel=cancel,
                                            clock=clock, sleep=idle_sleep, wait_seconds=1, heartbeat_factory=NoThreadPump)
        self.assertEqual(completed, 0); self.assertEqual(reports, [])
        self.assertGreater(clock(), 1); self.assertEqual(models.calls, 0)
        self.assertEqual(room.heartbeats[-1], "error")

    def test_persistent_two_rounds_reuse_one_room_capability_models_and_reset_selection_sequence(self):
        clock, models, transport, cancel = FakeClock(), FakeModels(), PersistentTransport(), threading.Event()
        room = remote.EngineRoom(transport, "A", CODE, sleep=clock.sleep)
        reports = []
        def save(report):
            reports.append(report)
            if len(reports) == 2:
                cancel.set()
        completed = remote.run_room_session(room, models, report_sink=save, cancel=cancel,
                                            clock=clock, sleep=clock.sleep, heartbeat_factory=NoThreadPump)
        self.assertEqual(completed, 2)
        self.assertEqual(transport.joins, 1)
        self.assertTrue(all(token == TOKEN for token in transport.authenticated))
        self.assertEqual(models.calls, 2)
        self.assertEqual([report["model_predictions_per_game"] for report in reports], [1, 1])
        self.assertEqual(transport.select_events, [(n, seq, tile) for n in (1, 2) for seq, tile in enumerate((0, 4, 8), 1)])
        self.assertTrue(any(stage == "submitted" and number == 1 for stage, _, number in transport.heartbeats))
        self.assertIn(("ready", None, 1), transport.heartbeats)
        self.assertNotIn(TOKEN, json.dumps(reports)); self.assertNotIn(CODE, json.dumps(reports))

    def test_finish_heartbeat_race_rebinds_result_and_same_capability_completes_next_round(self):
        class FinishRace(PersistentTransport):
            raced = False
            def json(self, path, *, token=None, body=None):
                if (body and body.get("action") == "heartbeat" and body.get("stage") == "selecting"
                        and self.number == 1 and not self.raced):
                    self.raced = True
                    self.phase, self.result_polls = "result", 0  # Human finishes during this heartbeat.
                    raise remote.RemoteEngineError("round_ended", status=409)
                return super().json(path, token=token, body=body)
        transport, clock, models, cancel, reports = FinishRace(), FakeClock(), FakeModels(), threading.Event(), []
        room = remote.EngineRoom(transport, "A", CODE, sleep=clock.sleep)
        def save(report):
            reports.append(report)
            if len(reports) == 2:
                cancel.set()
        remote.run_room_session(room, models, report_sink=save, cancel=cancel, clock=clock,
                                sleep=clock.sleep, heartbeat_factory=NoThreadPump)
        self.assertTrue(transport.raced); self.assertEqual(transport.joins, 1)
        self.assertEqual([report["status"] for report in reports], ["game_ended", "game_ended"])
        self.assertFalse(reports[0]["submit_sent"]); self.assertTrue(reports[1]["submit_sent"])
        self.assertEqual(models.calls, 2)
        self.assertEqual(transport.select_events, [(2, seq, tile) for seq, tile in enumerate((0, 4, 8), 1)])

    def test_old_lobby_heartbeat_epoch_is_refreshed_before_new_lobby_ready(self):
        requests = []
        class Room:
            def heartbeat(self, stage, *, round_id, round_number, request_id=None):
                requests.append((stage, round_id, round_number))
                if round_number == 0:
                    raise remote.RemoteEngineError("round_changed", status=409)
            def view(self):
                value = state("lobby"); value["roundNumber"] = 1
                return remote.PublicSnapshot.from_state(value, "A")
        pump = remote.HeartbeatPump(Room())
        pump.beat()
        self.assertEqual(requests, [("ready", None, 0), ("ready", None, 1)])
        self.assertFalse(pump.failed.is_set())

    def test_abort_heartbeat_racing_next_preserves_error_and_never_arms_new_lobby(self):
        requests = []
        class Room:
            def heartbeat(self, stage, *, round_id, round_number, request_id=None):
                requests.append((stage, round_id, round_number))
                if round_id == ROUND:
                    raise remote.RemoteEngineError("round_changed", status=409)
            def view(self):
                current = state("lobby"); current["roundNumber"] = 1
                return remote.PublicSnapshot.from_state(current, "A")
        pump = remote.HeartbeatPump(Room())
        pump.bind(snapshot())
        pump.stage = "error"
        pump.beat()
        self.assertEqual(requests, [("error", ROUND, 1), ("error", None, 1)])
        self.assertEqual(pump.stage, "error")
        self.assertFalse(any(stage == "ready" for stage, _, _ in requests))

    def test_old_submitted_heartbeat_is_inferencing_in_new_active_round(self):
        requests = []
        new_round = "99999999-1111-4111-8111-111111111111"
        class Room:
            def heartbeat(self, stage, *, round_id, round_number, request_id=None):
                requests.append((stage, round_id, round_number))
                if round_id == ROUND:
                    raise remote.RemoteEngineError("round_changed", status=409)
            def view(self):
                current = state(); current.update(roundId=new_round, roundNumber=2)
                return remote.PublicSnapshot.from_state(current, "A")
        pump = remote.HeartbeatPump(Room())
        pump.bind(snapshot()); pump.stage = "submitted"
        pump.beat()
        self.assertEqual(requests, [("submitted", ROUND, 1), ("inferencing", new_round, 2)])
        self.assertEqual(pump.stage, "inferencing")

    def test_late_old_round_frame_cannot_download_or_infer_after_next_round_started(self):
        clock, models = FakeClock(), FakeModels()
        room = FakeRoom(clock)
        latest = state(); latest.update(roundId="99999999-1111-4111-8111-111111111111", roundNumber=2)
        room.view = lambda: remote.PublicSnapshot.from_state(latest, "A")
        room.pixels = lambda _: self.fail("stale round must not download model inputs")
        attempted = set()
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, pump=FakePump(room),
                                     starting_snapshot=snapshot(), attempted_rounds=attempted)
        self.assertEqual(report["status"], "game_ended")
        self.assertEqual(models.calls, 0); self.assertEqual(room.events, []); self.assertEqual(room.submits, 0)
        self.assertIn(ROUND, attempted)

    def test_old_round_request_rejected_after_next_is_recorded_as_finished_not_fatal_session_error(self):
        clock, models = FakeClock(), FakeModels()
        room = FakeRoom(clock)
        def crossed_next(*args):
            room.phases = ["lobby"]
            raise remote.RemoteEngineError("round_changed", status=409)
        room.select = crossed_next
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=FakePump)
        self.assertEqual(report["status"], "game_ended")
        self.assertEqual(report["error_code"], "round_changed")
        self.assertEqual(room.submits, 0)

    def test_stop_one_lane_cancels_only_that_worker_without_reloading_shared_models(self):
        a_started, b_started, finish_b = threading.Event(), threading.Event(), threading.Event()
        shared_model = object()
        def runner(room, models, *, cancel, **kwargs):
            self.assertIs(models, shared_model)
            (a_started if room.lane == "A" else b_started).set()
            until = time.monotonic() + 2
            while time.monotonic() < until:
                if cancel.is_set():
                    return {"status": "aborted", "error_code": "cancelled", "lane": room.lane}
                if room.lane == "B" and finish_b.is_set():
                    return {"status": "game_ended", "lane": "B"}
                time.sleep(0.005)
            raise AssertionError("fixture timed out")
        with tempfile.TemporaryDirectory() as directory:
            controller = remote.EngineController(shared_model, lambda lane, code: type("Room", (), {"lane": lane})(), directory, runner=runner)
            controller.add("A", CODE); controller.add("B", CODE)
            self.assertTrue(a_started.wait(1)); self.assertTrue(b_started.wait(1))
            controller.stop("A")
            self.assertFalse(controller.cancel.is_set())
            self.assertFalse(controller._lane_cancel["B"].is_set())
            finish_b.set(); controller.wait(); controller.close()
            self.assertEqual(sorted((report["lane"], report["status"]) for report in controller.reports), [("A", "aborted"), ("B", "game_ended")])

    def test_ack_based_spacing_actual_model_selection_and_correct_submit_ends_without_ended_heartbeat(self):
        clock, models = FakeClock(), FakeModels()
        room = FakeRoom(clock, phases=("lobby", "countdown", "playing"))
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=FakePump)
        self.assertEqual(report["status"], "game_ended")
        self.assertEqual(report["model_predictions_per_game"], 1)
        self.assertEqual(models.calls, 1)
        self.assertEqual([event[1] for event in room.events], [0, 4, 8])
        self.assertEqual(room.submits, 1)
        self.assertNotIn("submitted", room.heartbeats)  # terminal submit ACK must not POST heartbeat.
        self.assertIn("inferencing", room.heartbeats)
        for previous, current in zip(report["selection_events"], report["selection_events"][1:]):
            gap = current["sent_seconds"] - previous["ack_seconds"]
            self.assertGreaterEqual(gap, 0.25)
            self.assertLess(gap, 0.251)  # no leftover one-second pacing in the fake-clock path.
        serialized = json.dumps(report)
        self.assertNotIn(ROUND, serialized); self.assertNotIn(ROOM, serialized)
        self.assertNotIn(TOKEN, serialized); self.assertNotIn(CODE, serialized)
        self.assertNotIn("originalFilename", serialized)
        self.assertIn("gpu_queue_seconds", report); self.assertIn("inference_seconds", report)

    def test_wrong_or_empty_fixed_attempt_is_not_repredicted_or_forced_to_answer_count(self):
        clock, models = FakeClock(), FakeModels(selected=())
        room = FakeRoom(clock, correct=False)
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=FakePump)
        self.assertEqual(report["status"], "game_ended")
        self.assertEqual(report["selected_indices"], [])
        self.assertEqual(room.events, [])
        self.assertEqual(models.calls, 1); self.assertEqual(room.submits, 1)
        self.assertIn("submitted", room.heartbeats)
        self.assertFalse(report["submission_correct"])

    def test_cancel_or_opponent_end_prevents_all_remaining_selection_events(self):
        clock, models = FakeClock(), FakeModels()
        room = FakeRoom(clock)
        original = room.select
        def first_then_ended(*args):
            original(*args)
            room.phases = ["result"]
        room.select = first_then_ended
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=FakePump)
        self.assertEqual(report["status"], "game_ended")
        self.assertEqual(len(room.events), 1); self.assertEqual(room.submits, 0)
        cancel = threading.Event(); cancel.set()
        another = FakeRoom(clock)
        stopped = remote.run_one_room(another, models, cancel=cancel, clock=clock, sleep=clock.sleep, heartbeat_factory=FakePump)
        self.assertEqual(stopped["error_code"], "cancelled")
        self.assertFalse(another.events)

    def test_background_ready_start_race_switches_stage_without_clearing_ready(self):
        stages = []
        class Room:
            def heartbeat(self, stage, **kwargs):
                stages.append(stage)
                if stage == "ready":
                    raise remote.RemoteEngineError("round_in_progress", status=409)
            def view(self):
                return snapshot("countdown")
        pump = remote.HeartbeatPump(Room())
        pump.beat()
        self.assertEqual(stages, ["ready", "inferencing"])
        self.assertEqual(pump.stage, "inferencing")
        self.assertFalse(pump.failed.is_set())

    def test_single_gpu_queue_remains_heartbeat_live_and_ended_waiter_never_runs_model(self):
        entered, release, beat_seen = threading.Event(), threading.Event(), threading.Event()
        class Predictor:
            presence_metadata = {"profile": {"threshold": 0.5}}
            def __init__(self):
                self.calls = 0
            def predict_tiles(self, images):
                self.calls += 1
                entered.set()
                if not release.wait(2):
                    raise RuntimeError("fixture timed out")
                return [TilePrediction({"building": 0.9}, 0)] * 9
        predictor = Predictor()
        shared = remote.SharedModels(predictor, None, execution_mode="serial")
        class Room:
            def heartbeat(self, stage, **kwargs):
                beat_seen.set()
        pump = remote.HeartbeatPump(Room(), interval=0.02)
        pump.start(); beat_seen.clear()
        pixels = [Image.new("RGB", (4, 4)) for _ in range(9)]
        results, errors, timings = [], [], {}
        def first():
            results.append(shared.infer(pixels, CONDITION, timings=timings))
        def ended_waiter():
            try:
                shared.infer(pixels, CONDITION, active=lambda: False)
            except remote.RemoteEngineError as error:
                errors.append(error.code)
        a = threading.Thread(target=first); a.start()
        self.assertTrue(entered.wait(1))
        b = threading.Thread(target=ended_waiter); b.start()
        self.assertTrue(beat_seen.wait(1))  # background lease is independent of GPU queue/inference.
        b.join(1); release.set(); a.join(1); pump.close()
        self.assertEqual(errors, ["round_ended"])
        self.assertEqual(predictor.calls, 1)
        self.assertEqual(results[0][0], list(range(9)))  # no forced top-k.
        self.assertGreaterEqual(timings["gpu_queue_seconds"], 0)
        self.assertGreater(timings["inference_seconds"], 0)

    def test_two_lanes_finish_independently_active_lane_is_preserved_and_new_participant_reuses_finished_lane(self):
        started_a, release_a, finished_b = threading.Event(), threading.Event(), threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            def factory(lane, code):
                return type("Room", (), {"lane": lane})()
            def runner(room, models, **kwargs):
                if room.lane == "A":
                    started_a.set()
                    if not release_a.wait(2):
                        raise RuntimeError("fixture timed out")
                else:
                    finished_b.set()
                return {"mode": "remote", "lane": room.lane, "status": "game_ended"}
            controller = remote.EngineController(None, factory, directory, runner=runner)
            controller.add("A", CODE); self.assertTrue(started_a.wait(1))
            with self.assertRaises(remote.RemoteEngineError) as caught:
                controller.add("A", "HGFEDCBA")
            self.assertEqual(caught.exception.code, "lane_busy")
            controller.add("B", CODE); self.assertTrue(finished_b.wait(1))
            release_a.set(); controller.wait()
            controller.add("B", "HGFEDCBA"); controller.wait(); controller.close()
            reports = sorted(Path(directory).glob("*.json"))
            self.assertEqual([path.name for path in reports], ["lane-A-game-1.json", "lane-B-game-1.json", "lane-B-game-2.json"])
            self.assertNotIn(CODE, "".join(path.read_text() for path in reports))

    def test_cli_dry_run_performs_no_join_model_load_stdin_read_or_output_creation(self):
        path = Path(__file__).resolve().parents[1] / "scripts/run_remote_engine.py"
        spec = importlib.util.spec_from_file_location("remote_cli_fixture", path)
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-created"
            with patch("sys.argv", [str(path), "--output", str(output), "--rooms-stdin"]), patch.object(cli, "load_models", side_effect=AssertionError("no load")), patch.object(cli, "ControlledTransport", side_effect=AssertionError("no join")), patch("sys.stdin", None), redirect_stdout(StringIO()):
                self.assertEqual(cli.main(), 0)
            self.assertFalse(output.exists())

    def test_cli_stdin_codes_stay_only_in_memory_and_reports_contain_no_codes(self):
        path = Path(__file__).resolve().parents[1] / "scripts/run_remote_engine.py"
        spec = importlib.util.spec_from_file_location("remote_cli_stdin_fixture", path)
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        received = []
        modes = []
        class Controller:
            def __init__(self, *args, **kwargs):
                self.reports = [{"status": "game_ended"}]
                modes.append(kwargs["continuous"])
            def add(self, lane, code):
                received.append((lane, code))
            def wait(self): pass
            def close(self): pass
        with tempfile.TemporaryDirectory() as directory:
            output, printed = Path(directory) / "new", StringIO()
            with patch("sys.argv", [str(path), "--execute", "--once", "--inference-mode", "parallel", "--gpu-duty-cycle", "1", "--rooms-stdin", "--output", str(output)]), patch("sys.stdin", StringIO(json.dumps({"A": CODE, "B": "HGFEDCBA"}) + "\n")), patch.object(cli, "load_models", return_value=object()), patch.object(cli, "EngineController", Controller), redirect_stdout(printed), redirect_stderr(printed):
                self.assertEqual(cli.main(), 0)
            self.assertEqual(received, [("A", CODE), ("B", "HGFEDCBA")])
            self.assertEqual(modes, [False])
            combined = printed.getvalue() + (output / "startup.json").read_text()
            self.assertNotIn(CODE, combined); self.assertNotIn("HGFEDCBA", combined)

    def test_interactive_cli_keeps_room_connections_and_only_stops_explicit_lane(self):
        path = Path(__file__).resolve().parents[1] / "scripts/run_remote_engine.py"
        spec = importlib.util.spec_from_file_location("remote_cli_persistent_fixture", path)
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        calls = []
        class Controller:
            def __init__(self, *args, **kwargs):
                calls.append(("continuous", kwargs["continuous"]))
            def add(self, lane, code): calls.append(("add", lane))
            def stop(self, lane): calls.append(("stop", lane))
            def close(self): calls.append(("close",))
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv", [str(path), "--execute", "--output", str(Path(directory) / "new")]), patch.object(cli, "load_models", return_value=object()) as loader, patch.object(cli, "EngineController", Controller), patch.object(cli.getpass, "getpass", side_effect=["A " + CODE, "stop A", "quit"]), redirect_stdout(StringIO()):
                self.assertEqual(cli.main(), 0)
            self.assertEqual(loader.call_count, 1)
        self.assertEqual(calls, [("continuous", True), ("add", "A"), ("stop", "A"), ("close",)])


if __name__ == "__main__":
    unittest.main()
