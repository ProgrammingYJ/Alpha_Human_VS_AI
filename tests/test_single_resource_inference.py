"""One-worker pacing is distinct from the unchanged server click interval."""
import unittest
from PIL import Image

from alpha_captcha.remote_engine import SharedModels, RemoteEngineError
from alpha_captcha.tasks import TilePrediction


class Clock:
    def __init__(self): self.now = 0.0
    def __call__(self): return self.now
    def sleep(self, duration): self.now += duration


class Predictor:
    presence_metadata = {"profile": {"threshold": .5}}
    def __init__(self, clock): self.clock, self.inputs, self.batch_sizes = clock, [], []
    def predict_condition_batch(self, images, condition):
        self.inputs.extend(images)
        self.batch_sizes.append(len(images))
        self.clock.now += .012
        return [TilePrediction(presence_scores={"building": .9 if image.getpixel((0, 0))[0] % 2 else .1})
                for image in images]


class SingleInferenceTests(unittest.TestCase):
    def setUp(self):
        self.images = [Image.new("RGB", (4, 4), (index, 0, 0)) for index in range(9)]
        self.addCleanup(lambda: [image.close() for image in self.images])

    def test_one_slot_yields_after_original_batches_and_preserves_pixel_order_without_more_HTTP(self):
        clock = Clock(); predictor = Predictor(clock)
        models = SharedModels(predictor, None, execution_mode="single", gpu_duty_cycle=.3)
        timings, active_calls = {}, []
        claim = models.reserve()
        try:
            selected, _ = models.infer(self.images, {"task_type": "building_present"},
                reservation=claim, active=lambda: active_calls.append(True) or True,
                timings=timings, clock=clock, budget_clock=clock, budget_sleep=clock.sleep)
        finally: claim.release()
        self.assertEqual(selected, [1, 3, 5, 7])
        self.assertEqual(predictor.inputs, self.images)
        self.assertEqual(len(active_calls), 1)
        self.assertEqual(models.execution_metadata()["max_concurrent_inferences"], 1)
        self.assertEqual(predictor.batch_sizes, [8, 1])
        self.assertEqual(timings["inference_chunk_count"], 2)
        self.assertAlmostEqual(timings["inference_work_seconds"], .024)
        self.assertAlmostEqual(timings["resource_throttle_seconds"], .056)
        self.assertAlmostEqual(timings["resource_work_fraction_observed"], .3)
        self.assertAlmostEqual(clock(), .08)  # Includes the final batch's yield.
        self.assertFalse(timings["hardware_gpu_quota_enforced"])
        self.assertFalse(models.reservations.busy)

    def test_local_cancellation_during_resource_sleep_stops_without_later_model_calls_and_releases_slot(self):
        clock = Clock(); predictor = Predictor(clock)
        models = SharedModels(predictor, None, execution_mode="single", gpu_duty_cycle=.3)
        def check():
            if clock.now >= .02: raise RemoteEngineError("cancelled")
        with self.assertRaisesRegex(RemoteEngineError, "cancelled"):
            models.infer(self.images, {"task_type": "building_present"},
                check_running=check, budget_clock=clock, budget_sleep=clock.sleep)
        self.assertEqual(len(predictor.inputs), 8)
        self.assertFalse(models.reservations.busy)

    def test_parallel_cannot_claim_a_process_wide_thirty_percent_with_independent_workers(self):
        with self.assertRaisesRegex(ValueError, "parallel workers"):
            SharedModels(None, None, execution_mode="parallel", gpu_duty_cycle=.3)
