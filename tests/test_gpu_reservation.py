"""Controlled reservations, protocol and timing fakes; never GUI, HTTP or GPU."""

import json
import threading
import time
import unittest

from PIL import Image

from alpha_captcha import remote_engine as remote
from alpha_captcha.tasks import TilePrediction


REQUEST = "11111111-1111-4111-8111-111111111111"
ROUND = "22222222-2222-4222-8222-222222222222"
ROOM = "33333333-3333-4333-8333-333333333333"
CONDITION = {"task_type": "building_present"}


class Clock:
    def __init__(self):
        self.value, self.lock = 0.0, threading.Lock()
    def __call__(self):
        with self.lock: return self.value
    def sleep(self, seconds):
        with self.lock: self.value += seconds


def public(phase="queued", *, lane="A", request_id=REQUEST, number=None):
    active = phase in {"countdown", "playing", "result"}
    return {"phase": phase, "roundId": ROUND if active else None, "roundNumber": (1 if active else 0) if number is None else number,
            "startRequest": {"id": request_id, "requestedAt": 0, "expiresAt": 120000} if request_id else None,
            "startAt": 2000 if active else None, "lastStartCancellationReason": None,
            "topic": {"condition": dict(CONDITION)} if phase in {"playing", "result"} else None,
            "tiles": [{"url": f"/api/photos/00000000-0000-4000-8000-{index:012d}"} for index in range(9)] if phase in {"playing", "result"} else [],
            "remote": {"mode": "remote", "lane": lane, "gpuReservationSupported": True, "sequence": 0, "selectedIndices": []}}


class Pump(remote.HeartbeatPump):
    def start(self): self.beat()


class Predictor:
    presence_metadata = {"profile": {"threshold": 0.5}}
    def __init__(self, clock=None):
        self.clock, self.calls = clock, 0
    def predict_tiles(self, images):
        self.calls += 1
        if self.clock: self.clock.sleep(2)
        return [TilePrediction({"building": 0.9 if index in (0, 4) else 0.1}, 0) for index in range(9)]


class Room:
    def __init__(self, models, clock, *, lane="A", first_select=None, began=None):
        self.models, self.clock, self.lane = models, clock, lane
        self.phase, self.events, self.begin_count, self.submits = "queued", [], 0, 0
        self.first_select, self.began = first_select, began
        self.public_downloads = 0
    def view(self):
        return remote.PublicSnapshot.from_state(public(self.phase, lane=self.lane), self.lane)
    def heartbeat(self, stage, **kwargs): pass
    def begin(self, request_id, round_number):
        if not self.models.reservations.busy or not self.models.lock.locked():
            raise AssertionError("begin without acquired GPU reservation")
        self.begin_count += 1
        self.phase = "playing"
        if self.began: self.began.set()
        return self.view()
    def pixels(self, current):
        if current.phase != "playing": raise AssertionError("pixels before common start")
        self.public_downloads += 1
        return [Image.new("RGB", (4, 4), (index, 0, 0)) for index in range(9)]
    def select(self, round_id, sequence, tile_index):
        if self.models.reservations.busy and self.models.lock.locked() and self.lane == "A":
            # B may legitimately own the reservation now, so only test that
            # this thread's completed reservation has been released via trace.
            pass
        if sequence == 1 and self.first_select:
            self.first_select()
        self.events.append((sequence, tile_index, self.clock()))
    def submit(self, round_id):
        self.submits += 1
        self.phase = "result"
        return {"correct": True, "elapsedMs": 3000, "state": public("result", lane=self.lane)}


class ReservationTests(unittest.TestCase):
    def test_join_and_preheartbeat_lobby_bootstrap_upgrade_before_queued_begin(self):
        calls = []
        class Transport:
            upgraded = False
            def json(self, path, *, token=None, body=None):
                calls.append(body)
                current = public("lobby", request_id=None)
                current["remote"]["gpuReservationSupported"] = self.upgraded
                if path.endswith("join"):
                    return {"roomId": ROOM, "token": "z" * 43, "state": current}
                if body is None:
                    return public() if self.upgraded else current
                if body["action"] == "heartbeat":
                    self.upgraded = True
                    return {"state": public()}
                if body["action"] == "begin":
                    return {"state": public("countdown")}
                raise AssertionError("unexpected request")
        room = remote.EngineRoom(Transport(), "A", "ABCDEFGH")
        self.assertFalse(room.view().gpu_reservation_supported)
        room.heartbeat("ready")
        self.assertTrue(room.view().gpu_reservation_supported)
        self.assertEqual(room.begin(REQUEST, 0).phase, "countdown")
        self.assertEqual(calls[2]["protocolVersion"], 2)
        active_false = public("playing"); active_false["remote"]["gpuReservationSupported"] = False
        with self.assertRaises(remote.RemoteEngineError):
            remote.PublicSnapshot.from_state(active_false, "A", allow_protocol_bootstrap=True)

    def test_old_server_and_queued_truth_or_clock_are_refused(self):
        old = public(); del old["remote"]["gpuReservationSupported"]
        with self.assertRaises(remote.RemoteEngineError) as caught:
            remote.PublicSnapshot.from_state(old, "A")
        self.assertEqual(caught.exception.code, "protocol_upgrade_required")
        for field, value in (("startAt", 1), ("roundId", ROUND), ("topic", {"condition": CONDITION}), ("tiles", [{"url": "answer.jpg"}])):
            value_state = public(); value_state[field] = value
            with self.subTest(field=field), self.assertRaises(remote.RemoteEngineError):
                remote.PublicSnapshot.from_state(value_state, "A")

    def test_protocol_two_context_and_begin_retry_preserve_same_request(self):
        bodies, waits = [], []
        class Transport:
            failed = False
            def json(self, path, *, token=None, body=None):
                bodies.append(body)
                if path.endswith("join"):
                    return {"roomId": ROOM, "token": "z" * 43, "state": public("lobby", request_id=None)}
                if body["action"] == "begin":
                    if not self.failed:
                        self.failed = True
                        raise remote.RemoteEngineError("connection_failed")
                    return {"state": public("countdown")}
                return {"state": public()}
        room = remote.EngineRoom(Transport(), "A", "ABCDEFGH", sleep=waits.append)
        room.heartbeat("waiting_gpu", round_id=None, round_number=0, request_id=REQUEST)
        current = room.begin(REQUEST, 0)
        self.assertEqual(current.phase, "countdown")
        self.assertEqual(bodies[1], {"action": "heartbeat", "stage": "waiting_gpu", "protocolVersion": 2,
                                    "requestId": REQUEST, "roundId": None, "roundNumber": 0})
        self.assertEqual(bodies[2], bodies[3]); self.assertEqual(waits, [1])

    def test_fifo_cancelled_waiter_is_removed_and_later_reservation_is_released(self):
        pool = remote.FifoGpuReservations(threading.Lock())
        owner = pool.acquire()
        order, cancelled, errors = [], threading.Event(), []
        def waiter(name, valid):
            try:
                claim = pool.acquire(active=valid)
                order.append(name)
                claim.release()
            except remote.RemoteEngineError as error: errors.append(error.code)
        b = threading.Thread(target=waiter, args=("B", lambda: not cancelled.is_set())); b.start()
        until = time.monotonic() + 1
        while len(pool.pending) < 1 and time.monotonic() < until: time.sleep(0.001)
        c = threading.Thread(target=waiter, args=("C", lambda: True)); c.start()
        cancelled.set(); b.join(1); owner.release(); c.join(1)
        self.assertEqual(errors, ["start_cancelled"]); self.assertEqual(order, ["C"])
        self.assertFalse(pool.busy); self.assertFalse(pool.lock.locked()); self.assertEqual(pool.pending, [])

    def test_precise_model_call_excludes_slow_http_guards_and_queue_context_checks(self):
        clock, predictor = Clock(), Predictor()
        def predict(images):
            clock.sleep(2)
            return [TilePrediction({"building": 0.1}, 0)] * 9
        predictor.predict_tiles = predict
        models, timings = remote.SharedModels(predictor, None), {}
        def guard(): clock.sleep(5); return True
        selected, _ = models.infer([Image.new("RGB", (4, 4)) for _ in range(9)], CONDITION,
                                  active=guard, timings=timings, clock=clock)
        self.assertEqual(selected, [])
        self.assertEqual(timings["gpu_queue_seconds"], 5)  # Standalone legacy acquisition includes its context check.
        self.assertEqual(timings["model_inference_seconds"], 2)
        self.assertEqual(timings["model_call_returned_monotonic_seconds"] - timings["model_call_started_monotonic_seconds"], 2)
        self.assertFalse(models.lock.locked())

    def test_cancel_before_begin_and_decode_failure_release_reservation_without_inference(self):
        for failing in ("cancel", "decode", "begin"):
            with self.subTest(failing=failing):
                clock, predictor = Clock(), Predictor()
                models = remote.SharedModels(predictor, None)
                room = Room(models, clock)
                if failing == "cancel":
                    views = [0]
                    original = room.view
                    def changed():
                        views[0] += 1
                        if views[0] >= 4:
                            return remote.PublicSnapshot.from_state(public("lobby", request_id=None), "A")
                        return original()
                    room.view = changed
                elif failing == "decode":
                    def pixels(_): raise remote.RemoteEngineError("invalid_public_image")
                    room.pixels = pixels
                else:
                    def begin(*_): raise remote.RemoteEngineError("start_request_changed", status=409)
                    room.begin = begin
                report = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=Pump)
                self.assertEqual(predictor.calls, 0)
                self.assertFalse(models.lock.locked()); self.assertFalse(models.reservations.busy)
                self.assertFalse(room.events); self.assertEqual(room.submits, 0)
                self.assertNotIn(REQUEST, json.dumps(report))

    def test_two_lanes_block_begin_before_gpu_then_overlap_selection_after_release(self):
        clock, entered_a, release_a, b_began, b_waiting = Clock(), threading.Event(), threading.Event(), threading.Event(), threading.Event()
        predictor = Predictor()
        def predict(images):
            predictor.calls += 1
            if predictor.calls == 1:
                entered_a.set()
                if not release_a.wait(2): raise AssertionError("fixture timed out")
            return [TilePrediction({"building": 0.9 if index in (0, 4) else 0.1}, 0) for index in range(9)]
        predictor.predict_tiles = predict
        models = remote.SharedModels(predictor, None)
        def first_select():
            if not b_began.wait(1): raise AssertionError("A selection held B's GPU reservation")
        a, b = Room(models, clock, first_select=first_select), Room(models, clock, lane="B", began=b_began)
        reports = {}
        def run(room):
            reports[room.lane] = remote.run_one_room(room, models, clock=clock, sleep=clock.sleep, heartbeat_factory=Pump,
                progress=lambda stage: b_waiting.set() if room.lane == "B" and stage == "waiting_gpu" else None)
        worker_a = threading.Thread(target=run, args=(a,)); worker_a.start(); self.assertTrue(entered_a.wait(1))
        worker_b = threading.Thread(target=run, args=(b,)); worker_b.start(); self.assertTrue(b_waiting.wait(1))
        self.assertFalse(b_began.is_set()); self.assertEqual(b.begin_count, 0); self.assertEqual(b.public_downloads, 0)
        release_a.set(); worker_a.join(2); worker_b.join(2)
        self.assertFalse(worker_a.is_alive()); self.assertFalse(worker_b.is_alive())
        self.assertEqual([reports[lane]["status"] for lane in ("A", "B")], ["game_ended", "game_ended"])
        self.assertEqual(predictor.calls, 2)
        for report in reports.values():
            self.assertTrue(report["gpu_reserved_before_start"])
            self.assertLessEqual(report["gpu_reserved_monotonic_seconds"], report["begin_sent_monotonic_seconds"])
            self.assertEqual(report["gpu_queue_seconds"], 0)
            self.assertLessEqual(report["gpu_reservation_released_seconds"], report["selection_events"][0]["sent_seconds"])
        self.assertEqual(len(a.events), 2); self.assertEqual(len(b.events), 2)
        self.assertFalse(models.lock.locked())


if __name__ == "__main__":
    unittest.main()
