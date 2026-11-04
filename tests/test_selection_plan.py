"""One immutable ML plan and honest scheduled timing; no HTTP, GPU or GUI."""

import copy
import json
import threading
import time
import unittest

from PIL import Image

from alpha_captcha import remote_engine as remote


ROUND = "11111111-1111-4111-8111-111111111111"
ROOM = "22222222-2222-4222-8222-222222222222"
TOKEN = "z" * 43
CODE = "ABCDEFGH"
CONDITION = {"task_type": "building_present"}


def state(phase="playing", *, attempted=False):
    return {"phase": phase, "roundId": ROUND if phase != "lobby" else None,
            "roundNumber": 0 if phase == "lobby" else 1, "startRequest": None, "startAt": None,
            "lastStartCancellationReason": None,
            "bot": {"submitted": attempted, "elapsedMs": 1000 if attempted else None},
            "remote": {"mode": "remote", "lane": "A", "gpuReservationSupported": True,
                       "selectionPlanSupported": True, "selectedIndices": [], "sequence": 0},
            "topic": {"condition": CONDITION} if phase == "playing" else None,
            "tiles": [{"url": f"/api/photos/00000000-0000-4000-8000-{index:012d}"}
                      for index in range(9)] if phase == "playing" else []}


class Clock:
    value = 0.0
    def __call__(self): return self.value
    def sleep(self, seconds): self.value += seconds


class Pump:
    def __init__(self, room): self.room, self.stage, self.failed = room, "ready", threading.Event()
    def start(self): pass
    def bind(self, current): pass
    def set_stage(self, stage, *, snapshot=None): self.stage = stage
    def close(self): pass


class RoomFake:
    lane = "A"
    def __init__(self, clock, *, human_finishes_at=None):
        self.clock, self.human_finishes_at = clock, human_finishes_at
        self.plans, self.views, self.schedule = [], 0, None
    def view(self):
        self.views += 1
        attempted = self.schedule is not None and self.clock() * 1000 >= self.schedule["submitAt"]
        human_finished = self.human_finishes_at is not None and self.clock() >= self.human_finishes_at
        return remote.PublicSnapshot.from_state(state("result" if attempted or human_finished else "playing",
                                                     attempted=attempted and not human_finished), "A")
    def heartbeat(self, *args, **kwargs): pass
    def pixels(self, current): return [Image.new("RGB", (4, 4)) for _ in range(9)]
    def plan(self, round_id, indices):
        self.plans.append((round_id, list(indices)))
        start = round(self.clock() * 1000) + 500
        self.schedule = {"startAt": start, "intervalMs": 250,
                         "submitAt": start + max(0, len(indices) - 1) * 250,
                         "selectedIndices": list(indices), "serverNow": round(self.clock() * 1000)}
        return dict(self.schedule)
    def select(self, *args): raise AssertionError("plan path must not send per-tile HTTP")
    def submit(self, *args): raise AssertionError("plan includes one server-owned submission")


class Models:
    def __init__(self, selected=(0, 4, 8)): self.selected, self.calls = list(selected), 0
    def infer(self, images, condition, *, active, timings, clock):
        self.calls += 1
        assert active() and condition == CONDITION and len(images) == 9
        return list(self.selected), [{} for _ in range(9)]


class PlanTransport:
    def __init__(self): self.calls, self.failures, self.ack_mutator = [], [], lambda value: value
    def json(self, path, *, token=None, body=None):
        self.calls.append(copy.deepcopy(body))
        if path.endswith("join"):
            return {"roomId": ROOM, "token": TOKEN, "state": state("lobby")}
        if self.failures: raise self.failures.pop(0)
        indices = body["selectedIndices"]
        return self.ack_mutator({"plan": {"roundId": ROUND, "selectedIndices": indices,
                                         "startAt": 1000, "intervalMs": 250,
                                         "submitAt": 1000 + max(0, len(indices) - 1) * 250},
                                 "serverNow": 5000})  # A replay after completion is valid.


class SelectionPlanTests(unittest.TestCase):
    def test_public_rgb_downloads_overlap_at_most_three_and_preserve_tile_order(self):
        lock, all_three, active, maximum, completions = threading.Lock(), threading.Event(), 0, 0, []
        class Transport(PlanTransport):
            def pixels(self, path):
                nonlocal active, maximum
                index = int(path[-12:])
                with lock:
                    active += 1; maximum = max(maximum, active)
                    if active == 3: all_three.set()
                try:
                    if not all_three.wait(1): raise AssertionError("downloads did not overlap")
                    # Complete the first three in the opposite order.
                    if index < 3: time.sleep((3 - index) * 0.01)
                    with lock: completions.append(index)
                    return Image.new("RGB", (3, 3), (index, 0, 0))
                finally:
                    with lock: active -= 1
        room = remote.EngineRoom(Transport(), "A", CODE)
        images = room.pixels(remote.PublicSnapshot.from_state(state(), "A"))
        self.assertEqual(maximum, 3); self.assertEqual(active, 0)
        self.assertEqual([image.getpixel((0, 0))[0] for image in images], list(range(9)))
        self.assertNotEqual(completions, list(range(9)))
        self.assertTrue(all(image.mode == "RGB" and image.info == {} for image in images))

    def test_failed_rgb_download_propagates_after_workers_are_joined_without_model_input(self):
        lock, active, maximum, finished = threading.Lock(), 0, 0, []
        class Transport(PlanTransport):
            def pixels(self, path):
                nonlocal active, maximum
                index = int(path[-12:])
                with lock: active += 1; maximum = max(maximum, active)
                try:
                    if index == 1: raise remote.RemoteEngineError("invalid_public_image")
                    time.sleep(0.01)
                    return Image.new("RGB", (3, 3))
                finally:
                    with lock: active -= 1; finished.append(index)
        room = remote.EngineRoom(Transport(), "A", CODE)
        with self.assertRaises(remote.RemoteEngineError) as caught:
            room.pixels(remote.PublicSnapshot.from_state(state(), "A"))
        self.assertEqual(caught.exception.code, "invalid_public_image")
        self.assertEqual(active, 0); self.assertLessEqual(maximum, 3)
        self.assertIn(1, finished)

    def test_plan_retry_uses_one_immutable_body_and_accepts_terminal_replay_ack(self):
        transport, waits = PlanTransport(), []
        room = remote.EngineRoom(transport, "A", CODE, sleep=waits.append)
        transport.failures = [remote.RemoteEngineError("connection_failed"),
                              remote.RemoteEngineError("request_failed", status=503)]
        schedule = room.plan(ROUND, [8, 2, 4])
        self.assertEqual(transport.calls[1:], [transport.calls[1]] * 3)
        self.assertEqual(transport.calls[1], {"action": "plan", "roundId": ROUND,
                                             "selectedIndices": [8, 2, 4]})
        self.assertEqual(waits, [1, 1]); self.assertEqual(schedule["submitAt"], 1500)
        self.assertNotIn(ROUND, json.dumps(schedule)); self.assertNotIn(TOKEN, json.dumps(schedule))

    def test_conflicting_plan_is_not_retried(self):
        transport = PlanTransport(); room = remote.EngineRoom(transport, "A", CODE)
        transport.failures = [remote.RemoteEngineError("plan_changed", status=409)]
        with self.assertRaises(remote.RemoteEngineError) as caught: room.plan(ROUND, [1])
        self.assertEqual(caught.exception.code, "plan_changed"); self.assertEqual(len(transport.calls), 2)

    def test_plan_refuses_duplicate_bool_out_of_range_and_nonlist_indices_before_http(self):
        transport = PlanTransport(); room = remote.EngineRoom(transport, "A", CODE)
        for invalid in ([1, 1], [True], [-1], [9], [0.0], (0, 1), list(range(10))):
            with self.subTest(indices=invalid), self.assertRaises(ValueError): room.plan(ROUND, invalid)
        self.assertEqual(len(transport.calls), 1)

    def test_ack_must_preserve_model_order_interval_and_exact_submission_schedule(self):
        transport = PlanTransport(); room = remote.EngineRoom(transport, "A", CODE)
        for key, invalid in (("roundId", ROOM), ("selectedIndices", [1, 0]), ("selectedIndices", [False, 1]),
                             ("intervalMs", 249), ("intervalMs", True),
                             ("startAt", -1), ("startAt", True), ("submitAt", 1251)):
            def mutate(value, key=key, invalid=invalid):
                value["plan"][key] = invalid
                return value
            transport.ack_mutator = mutate
            with self.subTest(key=key, invalid=invalid), self.assertRaises(remote.RemoteEngineError):
                room.plan(ROUND, [0, 1])

    def test_supported_runtime_uploads_one_plan_and_does_not_forge_actual_click_timestamps(self):
        clock, models = Clock(), Models(); room = RoomFake(clock)
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=Pump)
        self.assertEqual(report["status"], "game_ended"); self.assertEqual(models.calls, 1)
        self.assertEqual(room.plans, [(ROUND, [0, 4, 8])])
        self.assertEqual(report["selection_transport"], "scheduled_plan")
        self.assertEqual(report["selection_timing_schema_version"], 3)
        self.assertEqual(report["selection_events"], []); self.assertFalse(report["submit_sent"])
        self.assertTrue(report["logical_submit_scheduled"]); self.assertEqual(report["logical_submission_count"], 1)
        self.assertTrue(report["server_submission_observed"])
        self.assertEqual([row["server_scheduled_at_ms"] for row in report["planned_selection_events"]], [500, 750, 1000])
        self.assertEqual([row["tile_index"] for row in report["planned_selection_events"]], [0, 4, 8])
        self.assertTrue(all("sent_seconds" not in row for row in report["planned_selection_events"]))
        self.assertNotIn(ROUND, json.dumps(report)); self.assertNotIn(TOKEN, json.dumps(report))

    def test_empty_prediction_schedules_one_empty_submission_without_forced_tiles(self):
        clock, models = Clock(), Models(()); room = RoomFake(clock)
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=Pump)
        self.assertEqual(report["status"], "game_ended"); self.assertEqual(room.plans, [(ROUND, [])])
        self.assertEqual(report["selected_indices"], []); self.assertEqual(report["planned_selection_events"], [])
        self.assertEqual(report["planned_submit_at_ms"], report["plan_start_at_ms"])
        self.assertTrue(report["server_submission_observed"]); self.assertEqual(models.calls, 1)

    def test_opponent_finish_does_not_trigger_reinference_or_force_remaining_plan(self):
        clock, models = Clock(), Models(); room = RoomFake(clock, human_finishes_at=0.6)
        report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=Pump)
        self.assertEqual(report["status"], "game_ended"); self.assertEqual(models.calls, 1)
        self.assertEqual(len(room.plans), 1); self.assertFalse(report["server_submission_observed"])
        self.assertEqual(report["selection_events"], [])

    def test_feature_flag_is_transport_only_and_wrong_submit_observation_is_preserved(self):
        raw = state(); raw["remote"]["selectionPlan"] = {"selectedIndices": [8]}
        snap = remote.PublicSnapshot.from_state(raw, "A")
        self.assertEqual(snap.condition, CONDITION); self.assertTrue(snap.selection_plan_supported)
        self.assertNotIn("selectedIndices", snap.condition)
        raw["bot"] = {"submitted": False, "elapsedMs": 1000, "correct": False}
        self.assertTrue(remote.PublicSnapshot.from_state(raw, "A").bot_attempted)
        raw["remote"]["selectionPlanSupported"] = "true"
        with self.assertRaises(remote.RemoteEngineError): remote.PublicSnapshot.from_state(raw, "A")


if __name__ == "__main__": unittest.main()
