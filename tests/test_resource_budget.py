"""Deterministic pacing tests; no model, CUDA, network or process changes."""

import math
import unittest

from alpha_captcha.resource_budget import CooperativePacer


class Clock:
    def __init__(self, *, oversleep=0.0):
        self.now = 0.0
        self.sleeps = []
        self.oversleep = oversleep

    def __call__(self):
        return self.now

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.now += duration + self.oversleep


class ResourceBudgetTests(unittest.TestCase):
    def test_invalid_duty_cycles_are_rejected(self):
        for value in (True, False, 0, -0.1, 1.1, math.inf, -math.inf, math.nan, None, "0.3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CooperativePacer(value)

    def test_thirty_percent_budget_synchronizes_and_rests_even_after_final_chunk(self):
        clock = Clock()
        events = []
        pacer = CooperativePacer(0.3, clock=clock, sleep=clock.sleep)

        def synchronize():
            events.append("synchronize")
            if events.count("synchronize") == 2:
                clock.now += 0.02  # queued GPU work must complete before rest

        def model():
            events.append("model")
            clock.now += 0.1
            return [1, 4, 7]

        result = pacer.run(model, synchronize=synchronize)
        metrics = pacer.metrics()
        self.assertEqual(result, [1, 4, 7])
        self.assertEqual(events, ["synchronize", "model", "synchronize"])
        self.assertAlmostEqual(metrics["inference_work_seconds"], 0.12)
        self.assertAlmostEqual(metrics["resource_throttle_planned_seconds"], 0.28)
        self.assertAlmostEqual(metrics["resource_throttle_seconds"], 0.28)
        self.assertAlmostEqual(metrics["resource_work_fraction_observed"], 0.3)
        self.assertEqual(metrics["inference_chunk_count"], 1)
        self.assertTrue(clock.sleeps)
        self.assertTrue(all(0 < seconds <= 0.05 for seconds in clock.sleeps))
        self.assertEqual(metrics["quota_kind"], "cooperative_model_call_time")
        self.assertIs(metrics["hardware_gpu_quota_enforced"], False)
        self.assertIsNone(metrics["memory_allocator_limit_fraction"])

    def test_earlier_idle_time_never_accumulates_burst_credit(self):
        clock = Clock()
        pacer = CooperativePacer(0.3, clock=clock, sleep=clock.sleep)

        def model():
            clock.now += 0.09
            return "unchanged"

        pacer.run(model)
        before = pacer.metrics()["resource_throttle_seconds"]
        clock.now += 600  # lobby time must not pay for the next participant
        self.assertEqual(pacer.run(model), "unchanged")
        metrics = pacer.metrics()
        self.assertAlmostEqual(metrics["resource_throttle_seconds"] - before, 0.21)
        self.assertAlmostEqual(metrics["resource_work_fraction_observed"], 0.3)
        self.assertEqual(metrics["inference_chunk_count"], 2)

    def test_oversleep_is_measured_separately_from_the_planned_rest(self):
        clock = Clock(oversleep=0.01)
        pacer = CooperativePacer(0.3, clock=clock, sleep=clock.sleep)

        def model():
            clock.now += 0.1

        pacer.run(model)
        metrics = pacer.metrics()
        self.assertAlmostEqual(metrics["resource_throttle_planned_seconds"], 0.1 * (1 / 0.3 - 1))
        self.assertGreater(metrics["resource_throttle_seconds"], metrics["resource_throttle_planned_seconds"])
        self.assertLess(metrics["resource_work_fraction_observed"], 0.3)

    def test_cancelled_rest_stops_after_one_slice_without_repeating_the_model(self):
        clock = Clock()
        calls = []
        pacer = CooperativePacer(0.3, clock=clock, sleep=clock.sleep)

        def check():
            if clock.sleeps:
                raise RuntimeError("cancelled")

        def model():
            calls.append("model")
            clock.now += 0.1

        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            pacer.run(model, check_running=check)
        self.assertEqual(calls, ["model"])
        self.assertEqual(clock.sleeps, [0.05])
        self.assertEqual(pacer.metrics()["inference_chunk_count"], 1)
        self.assertAlmostEqual(pacer.metrics()["resource_throttle_seconds"], 0.05)

    def test_failed_model_is_synchronized_and_measured_without_rest_or_retry(self):
        clock = Clock()
        events = []
        pacer = CooperativePacer(0.3, clock=clock, sleep=clock.sleep)

        def model():
            events.append("model")
            clock.now += 0.03
            raise ValueError("model_failed")

        def synchronize():
            events.append("synchronize")

        with self.assertRaisesRegex(ValueError, "model_failed"):
            pacer.run(model, synchronize=synchronize)
        self.assertEqual(events, ["synchronize", "model", "synchronize"])
        self.assertEqual(clock.sleeps, [])
        self.assertAlmostEqual(pacer.metrics()["inference_work_seconds"], 0.03)
        self.assertEqual(pacer.metrics()["resource_throttle_planned_seconds"], 0)

    def test_failed_cleanup_cannot_hide_the_original_model_error(self):
        clock = Clock()
        sync_count = 0
        pacer = CooperativePacer(0.3, clock=clock, sleep=clock.sleep)

        def synchronize():
            nonlocal sync_count
            sync_count += 1
            if sync_count == 2:
                raise RuntimeError("cleanup_failed")

        def model():
            raise ValueError("original_model_failure")

        with self.assertRaisesRegex(ValueError, "original_model_failure"):
            pacer.run(model, synchronize=synchronize)
        self.assertEqual(sync_count, 2)
        self.assertEqual(clock.sleeps, [])

    def test_unlimited_mode_does_not_sleep_and_empty_metrics_do_not_invent_a_measurement(self):
        clock = Clock()
        pacer = CooperativePacer(1, clock=clock, sleep=clock.sleep)
        self.assertIsNone(pacer.metrics()["resource_work_fraction_observed"])

        def model():
            clock.now += 0.02
            return 42

        self.assertEqual(pacer.run(model), 42)
        self.assertEqual(clock.sleeps, [])
        self.assertEqual(pacer.metrics()["resource_work_fraction_observed"], 1)


if __name__ == "__main__":
    unittest.main()
