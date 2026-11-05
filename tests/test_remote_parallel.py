"""Two-lane admission and real host-call overlap; no network, GUI or CUDA."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import threading
import time
import unittest

from PIL import Image

from alpha_captcha import remote_engine as remote
from alpha_captcha.tasks import TilePrediction
from test_gpu_reservation import Clock, CONDITION, Pump, public
from test_image_readiness import BarrierRoom, EPOCH, barrier_state


def pixels(marker=0):
    return [Image.new("RGB", (4, 4), (marker, index, 0)) for index in range(9)]


def rows(images):
    parity = images[0].getpixel((0, 0))[0] % 2
    return [TilePrediction({"building": .9 if index % 2 == parity else .1}, 0)
            for index in range(9)]


class Predictor:
    presence_metadata = {"profile": {"threshold": .5}}

    def predict_tiles(self, images):
        return rows(images)


class ParallelTests(unittest.TestCase):
    def test_default_has_two_slots_cancelled_third_waiter_leaves_both_owners_intact(self):
        models = remote.SharedModels(Predictor(), None)
        metadata = models.execution_metadata()
        self.assertEqual(metadata["inference_mode"], "parallel")
        self.assertEqual(metadata["max_concurrent_inferences"], 2)
        claims = [models.reserve(), models.reserve()]
        self.assertEqual({claim.worker_index for claim in claims}, {0, 1})
        checked, cancelled, failures = threading.Event(), threading.Event(), []

        def guard():
            checked.set()
            return not cancelled.is_set()

        def waiter():
            try:
                models.reserve(active=guard)
                failures.append("unexpected_acquisition")
            except remote.RemoteEngineError as error:
                failures.append(error.code)

        worker = threading.Thread(target=waiter)
        try:
            worker.start()
            self.assertTrue(checked.wait(1))
            cancelled.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(failures, ["start_cancelled"])
            for claim in claims:
                claim.validate(models.reservations)
        finally:
            cancelled.set()
            for claim in claims:
                claim.release()
        first, second = models.reserve(), models.reserve()
        self.assertEqual({first.worker_index, second.worker_index}, {0, 1})
        first.release(); first.release(); second.release()
        self.assertFalse(models.reservations.busy)

    def test_default_two_model_calls_reach_barrier_before_either_returns(self):
        gate = threading.Barrier(2)
        intervals = []
        lock = threading.Lock()

        class BlockingPredictor(Predictor):
            def predict_tiles(self, images):
                started = time.perf_counter()
                gate.wait(timeout=2)  # A serialized executor cannot pass this gate.
                result = rows(images)
                with lock:
                    intervals.append((started, time.perf_counter()))
                return result

        models = remote.SharedModels(BlockingPredictor(), None)
        image_sets = [pixels(1), pixels(2)]
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(models.infer, images, CONDITION) for images in image_sets]
                outputs = [job.result(timeout=4)[0] for job in jobs]
            self.assertEqual(outputs, [[1, 3, 5, 7], [0, 2, 4, 6, 8]])
            self.assertLess(max(start for start, _ in intervals), min(end for _, end in intervals))
            self.assertFalse(models.reservations.busy)
        finally:
            for images in image_sets:
                for image in images: image.close()

    def test_tree_and_presence_use_separate_slots_and_preserve_actual_predictions(self):
        gate = threading.Barrier(2)

        class BlockingPredictor(Predictor):
            def predict_tiles(self, images):
                gate.wait(timeout=2)
                return rows(images)

        class Tree:
            def predict_at_least_three(self, images):
                gate.wait(timeout=2)
                return [index in (2, 5, 8) for index in range(9)]

        models = remote.SharedModels(BlockingPredictor(), Tree())
        images_a, images_b = pixels(1), pixels(2)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(models.infer, images_a, CONDITION)
                second = pool.submit(models.infer, images_b, {"task_type": "tree_count", "operator": "gte", "n": 3})
                self.assertEqual(first.result(timeout=4)[0], [1, 3, 5, 7])
                self.assertEqual(second.result(timeout=4)[0], [2, 5, 8])
        finally:
            for image in images_a + images_b: image.close()

    def test_one_model_failure_does_not_cancel_other_lane_or_leak_slot(self):
        gate = threading.Barrier(2)
        call_lock, calls = threading.Lock(), []

        class Fallible(Predictor):
            def predict_tiles(self, images):
                with call_lock:
                    calls.append(images[0].getpixel((0, 0))[0])
                    ordinal = len(calls)
                if ordinal <= 2: gate.wait(timeout=2)
                if images[0].getpixel((0, 0))[0] == 1:
                    raise ValueError("controlled_lane_failure")
                return rows(images)

        models = remote.SharedModels(Fallible(), None)
        image_sets = [pixels(marker) for marker in (1, 2, 3)]
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                failed = pool.submit(models.infer, image_sets[0], CONDITION)
                healthy = pool.submit(models.infer, image_sets[1], CONDITION)
                with self.assertRaisesRegex(ValueError, "controlled_lane_failure"):
                    failed.result(timeout=4)
                self.assertEqual(healthy.result(timeout=4)[0], [0, 2, 4, 6, 8])
            self.assertEqual(models.infer(image_sets[2], CONDITION)[0], [1, 3, 5, 7])
            self.assertFalse(models.reservations.busy)
        finally:
            for images in image_sets:
                for image in images: image.close()

    def test_explicit_serial_fallback_never_enters_second_call_until_first_finishes(self):
        entered, second_checked, release = threading.Event(), threading.Event(), threading.Event()
        call_lock, calls, errors = threading.Lock(), [], []

        class SerialPredictor(Predictor):
            def predict_tiles(self, images):
                with call_lock:
                    calls.append(images[0].getpixel((0, 0))[0])
                    ordinal = len(calls)
                entered.set()
                if ordinal == 1 and not release.wait(2): raise RuntimeError("fixture_timeout")
                return rows(images)

        models = remote.SharedModels(SerialPredictor(), None, execution_mode="serial")
        image_sets = [pixels(1), pixels(2)]

        def second_guard(): second_checked.set(); return True
        def infer(images, **kwargs):
            try: return models.infer(images, CONDITION, **kwargs)
            except Exception as error: errors.append(error); raise

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(infer, image_sets[0])
                self.assertTrue(entered.wait(1))
                second = pool.submit(infer, image_sets[1], active=second_guard)
                self.assertTrue(second_checked.wait(1))
                with call_lock: self.assertEqual(calls, [1])
                release.set()
                first.result(timeout=3); second.result(timeout=3)
            self.assertEqual(calls, [1, 2])
            self.assertEqual(models.execution_metadata()["max_concurrent_inferences"], 1)
            self.assertFalse(errors)
        finally:
            release.set()
            for images in image_sets:
                for image in images: image.close()

    def test_claim_from_other_thread_or_released_claim_cannot_run_model(self):
        models = remote.SharedModels(Predictor(), None)
        claim = models.reserve()
        images = pixels()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(models.infer, images, CONDITION, reservation=claim)
                with self.assertRaises(remote.RemoteEngineError) as caught:
                    future.result(timeout=2)
                self.assertEqual(caught.exception.code, "reservation_required")
            claim.release()
            with self.assertRaises(remote.RemoteEngineError) as caught:
                models.infer(images, CONDITION, reservation=claim)
            self.assertEqual(caught.exception.code, "reservation_required")
        finally:
            claim.release()
            for image in images: image.close()

    def test_cancelled_owner_never_calls_model_and_does_not_release_healthy_lane(self):
        entered, release = threading.Event(), threading.Event()
        calls = []

        class Blocking(Predictor):
            def predict_tiles(self, images):
                calls.append(images[0].getpixel((0, 0))[0])
                entered.set()
                if not release.wait(2): raise RuntimeError("fixture_timeout")
                return rows(images)

        models = remote.SharedModels(Blocking(), None)
        cancelled_owner = models.reserve()
        healthy_images, cancelled_images = pixels(2), pixels(1)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                healthy = pool.submit(models.infer, healthy_images, CONDITION)
                self.assertTrue(entered.wait(1))
                with self.assertRaises(remote.RemoteEngineError) as error:
                    models.infer(cancelled_images, CONDITION, active=lambda: False,
                                 reservation=cancelled_owner)
                self.assertEqual(error.exception.code, "round_ended")
                cancelled_owner.release()
                self.assertTrue(models.reservations.busy)
                self.assertFalse(healthy.done())
                release.set()
                self.assertEqual(healthy.result(timeout=3)[0], [0, 2, 4, 6, 8])
            self.assertEqual(calls, [2])
            self.assertFalse(models.reservations.busy)
        finally:
            release.set(); cancelled_owner.release()
            for image in healthy_images + cancelled_images: image.close()


class LifecycleTests(unittest.TestCase):
    def test_replaced_round_cache_never_reaches_model_while_other_lane_keeps_running(self):
        entered, release = threading.Event(), threading.Event()
        model_inputs = []

        class Blocking(Predictor):
            def predict_tiles(self, images):
                model_inputs.append(images[0].getpixel((0, 0))[0])
                entered.set()
                if not release.wait(3): raise RuntimeError("fixture_timeout")
                return rows(images)

        models = remote.SharedModels(Blocking(), None)

        class LaneRoom(BarrierRoom):
            def __init__(self, lane, *, replace_round=False):
                super().__init__(models, Clock())
                self.lane, self.replace_round = lane, replace_round

            def view(self):
                current = replace(super().view(), lane=self.lane)
                if self.replace_round and self.acks:
                    current = replace(current, round_id="99999999-9999-4999-8999-999999999999",
                                      round_number=current.round_number + 1)
                return current

            def pixels(self, snapshot):
                result = super().pixels(snapshot)
                for image in result: image.paste((2 if self.lane == "B" else 1, 0, 0), (0, 0, 4, 4))
                return result

            def submit(self, round_id):
                result = super().submit(round_id)
                result["state"]["remote"]["lane"] = self.lane
                return result

        healthy, stale = LaneRoom("B"), LaneRoom("A", replace_round=True)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                running = pool.submit(remote.run_one_room, healthy, models, clock=healthy.clock,
                                      sleep=healthy.clock.sleep, heartbeat_factory=Pump, wait_seconds=10)
                self.assertTrue(entered.wait(1))
                rejected = remote.run_one_room(stale, models, clock=stale.clock,
                                               sleep=stale.clock.sleep, heartbeat_factory=Pump, wait_seconds=10)
                self.assertEqual(rejected["status"], "start_cancelled", rejected)
                self.assertEqual(stale.selects, [])
                self.assertEqual(stale.downloads, 1)
                self.assertEqual(model_inputs, [2])
                self.assertTrue(models.reservations.busy)
                self.assertFalse(running.done())
                release.set()
                self.assertEqual(running.result(timeout=4)["status"], "game_ended")
            self.assertFalse(models.reservations.busy)
        finally: release.set()

    def test_both_lanes_begin_preload_countdown_then_infer_with_no_fifo_and_keep_click_interval(self):
        begin_gate, decode_gate, ready_gate, infer_gate = [threading.Barrier(2) for _ in range(4)]
        room_by_marker, predicted = {}, []
        predicted_lock = threading.Lock()

        class ConcurrentPredictor(Predictor):
            def predict_tiles(self, images):
                marker = images[0].getpixel((0, 0))[0]
                room = room_by_marker[marker]
                if room.phase != "playing": raise AssertionError("actual_question_inferred_before_common_start")
                if images is not room.saved_images: raise AssertionError("preloaded_pixels_not_reused")
                infer_gate.wait(timeout=3)
                with predicted_lock: predicted.append(marker)
                return [TilePrediction({"building": .9 if index in (0, 4) else .1}, 0) for index in range(9)]

        models = remote.SharedModels(ConcurrentPredictor(), None)

        class Room:
            def __init__(self, lane, marker):
                self.lane, self.marker, self.clock, self.phase = lane, marker, Clock(), "queued"
                self.downloads, self.acks, self.events, self.saved_images = 0, 0, [], []
                room_by_marker[marker] = self

            def view(self):
                if self.phase == "countdown" and self.clock() >= 1:
                    self.phase = "playing"
                value = public(lane=self.lane) if self.phase == "queued" else barrier_state(self.phase, ready=self.phase != "loading")
                value["remote"]["lane"] = self.lane
                value["remote"]["imageBarrierSupported"] = True
                return remote.PublicSnapshot.from_state(value, self.lane)

            def heartbeat(self, *args, **kwargs): pass

            def begin(self, *_):
                self.phase = "loading"
                begin_gate.wait(timeout=3)  # Both lanes reserve before either model runs.
                return self.view()

            def pixels(self, snapshot):
                if self.phase != "loading" or snapshot.phase != "loading": raise AssertionError("wrong_download_phase")
                decode_gate.wait(timeout=3)
                self.downloads += 1
                self.saved_images = pixels(self.marker)
                return self.saved_images

            def images_ready(self, snapshot):
                if snapshot.image_load_id != EPOCH: raise AssertionError("wrong_image_epoch")
                self.acks += 1
                ready_gate.wait(timeout=3)
                self.phase = "countdown"
                return self.view()

            def select(self, _, sequence, index): self.events.append((sequence, index, self.clock()))

            def submit(self, _):
                self.phase = "result"
                value = barrier_state("result"); value["remote"]["lane"] = self.lane
                return {"correct": True, "elapsedMs": 1000, "state": value}

        rooms = [Room("A", 1), Room("B", 2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(remote.run_one_room, room, models, clock=room.clock,
                                   sleep=room.clock.sleep, heartbeat_factory=Pump, wait_seconds=10) for room in rooms]
            reports = [future.result(timeout=6) for future in futures]
        self.assertCountEqual(predicted, [1, 2])
        for room, report in zip(rooms, reports):
            self.assertEqual(report["status"], "game_ended", report)
            self.assertEqual(room.downloads, 1)
            self.assertEqual(room.acks, 1)
            self.assertTrue(report["image_cache_reused"])
            self.assertEqual(report["model_predictions_per_game"], 1)
            self.assertEqual(report["gpu_queue_seconds"], 0)
            self.assertGreaterEqual(room.events[1][2] - room.events[0][2], .25)
            self.assertLessEqual(report["gpu_reservation_released_seconds"], report["selection_events"][0]["sent_seconds"])
            with self.assertRaises(ValueError): room.saved_images[0].getpixel((0, 0))
        self.assertFalse(models.reservations.busy)


if __name__ == "__main__": unittest.main()
