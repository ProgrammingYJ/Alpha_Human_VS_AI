"""Timing tests use fake clocks and recording callbacks, never mouse input."""

import unittest

from alpha_captcha.timing import (
    ClickDispatchError,
    ClickTimingConfig,
    ClockError,
    QuestionToken,
    TileClickScheduler,
    plan_click_offsets,
)


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start
        self.sleeps = []
        self.sleep_hook = None

    def clock(self):
        return self.now

    def sleep(self, duration):
        self.sleeps.append(duration)
        if self.sleep_hook is not None:
            self.sleep_hook(duration)
        else:
            self.now += duration


class TileClickSchedulerTests(unittest.TestCase):
    def scheduler(self, fake, **config):
        return TileClickScheduler(
            ClickTimingConfig(**config), clock=fake.clock, sleep=fake.sleep,
        )

    def test_consecutive_callbacks_and_toggle_share_minimum_interval(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        calls = []
        token = scheduler.begin_question("one")
        result = scheduler.run_tiles(token, [0, 4, 4, 8], lambda tile: calls.append((tile, fake.now)))
        self.assertEqual([tile for tile, _ in calls], [0, 4, 4, 8])
        self.assertEqual(calls[0][1], 0.0)
        for previous, current in zip(calls, calls[1:]):
            self.assertGreaterEqual(current[1] - previous[1], 0.25)
        self.assertEqual(result.stop_reason, "completed")
        self.assertAlmostEqual(result.wait_seconds, 0.75)
        self.assertTrue(all(event.succeeded for event in result.events))

    def test_slow_callback_and_oversleep_do_not_catch_up(self):
        fake = FakeClock(10.0)
        scheduler = self.scheduler(fake)
        calls = []

        def callback(tile):
            calls.append(fake.now)
            fake.now += 2.5

        def oversleep(duration):
            fake.now += duration + 4.0

        fake.sleep_hook = oversleep
        result = scheduler.run_tiles(scheduler.begin_question("slow"), [0, 1, 2], callback)
        for left, right in zip(result.events, result.events[1:]):
            self.assertGreaterEqual(right.dispatched_at - left.finished_at, 0.25)
        self.assertEqual(result.dispatch_seconds, 7.5)
        self.assertGreater(result.wait_seconds, 8.0)
        self.assertAlmostEqual(result.elapsed_seconds, result.wait_seconds + result.dispatch_seconds)
        self.assertEqual(len(calls), 3)

    def test_prior_processing_delay_does_not_add_unneeded_extra_cooldown(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("processing")
        scheduler.run_tiles(token, [0], lambda tile: None)
        fake.now += 8.0
        result = scheduler.run_tiles(token, [1], lambda tile: None)
        self.assertEqual(result.events[0].dispatched_at, 8.0)
        self.assertEqual(result.wait_seconds, 0.0)

    def test_early_wakeup_rechecks_clock_and_records_elapsed_wait(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake, poll_interval_seconds=0.5)
        wakeups = 0

        def early_sleep(duration):
            nonlocal wakeups
            wakeups += 1
            fake.now += duration / 2 if wakeups <= 4 else duration

        fake.sleep_hook = early_sleep
        result = scheduler.run_tiles(scheduler.begin_question("early"), [0, 1], lambda tile: None)
        self.assertGreater(len(fake.sleeps), 2)
        self.assertGreaterEqual(result.events[1].dispatched_at - result.events[0].finished_at, 0.25)
        self.assertAlmostEqual(result.events[1].required_wait_seconds, 0.25)
        self.assertAlmostEqual(result.events[1].wait_seconds, 0.25)
        self.assertAlmostEqual(result.wait_seconds, 0.25)

    def test_cancel_during_wait_stops_remainder_and_preserves_global_cooldown(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("cancel")
        calls = []

        def cancel_during_sleep(duration):
            fake.now += duration
            scheduler.cancel(token)

        fake.sleep_hook = cancel_during_sleep
        result = scheduler.run_tiles(token, [0, 1, 2], calls.append)
        self.assertEqual(calls, [0])
        self.assertEqual(result.stop_reason, "cancelled")
        self.assertAlmostEqual(result.wait_seconds, 0.05)
        fake.sleep_hook = None
        next_result = scheduler.run_tiles(scheduler.begin_question("next"), [3], calls.append)
        self.assertGreaterEqual(next_result.events[0].dispatched_at, 0.25)

    def test_question_change_mid_wait_invalidates_old_token_even_same_id(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("same-id")
        new_token = None
        calls = []

        def replace(duration):
            nonlocal new_token
            fake.now += duration
            new_token = scheduler.begin_question("same-id")

        fake.sleep_hook = replace
        result = scheduler.run_tiles(token, [0, 1], calls.append)
        self.assertEqual(result.stop_reason, "question_changed")
        self.assertEqual(calls, [0])
        fake.sleep_hook = None
        scheduler.cancel(token)  # A stale cancellation must not cancel the new question.
        next_result = scheduler.run_tiles(new_token, [2], calls.append)
        self.assertEqual(next_result.stop_reason, "completed")
        self.assertGreaterEqual(next_result.events[0].dispatched_at, 0.25)

    def test_recreated_or_old_token_cannot_dispatch(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("original")
        copied = QuestionToken(token.question_id, token.generation)
        calls = []
        result = scheduler.run_tiles(copied, [0], calls.append)
        self.assertEqual(result.stop_reason, "question_changed")
        scheduler.begin_question("replacement")
        result = scheduler.run_tiles(token, [1], calls.append)
        self.assertEqual(result.stop_reason, "question_changed")
        self.assertEqual(calls, [])

    def test_first_delay_is_per_question_and_explicit_not_per_run(self):
        fake = FakeClock(5.0)
        scheduler = self.scheduler(fake, first_click_delay_seconds=2.0)
        token = scheduler.begin_question("delay")
        first = scheduler.run_tiles(token, [0], lambda tile: None)
        self.assertEqual(first.events[0].dispatched_at, 7.0)
        second = scheduler.run_tiles(token, [1], lambda tile: None)
        self.assertEqual(second.events[0].dispatched_at, 7.25)
        replacement = scheduler.begin_question("new-delay")
        third = scheduler.run_tiles(replacement, [2], lambda tile: None)
        self.assertEqual(third.events[0].dispatched_at, 9.25)

    def test_failed_callback_records_attempt_stops_queue_and_consumes_cooldown(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        calls = []

        def fail_after_possible_click(tile):
            calls.append(tile)
            fake.now += 0.25
            raise OSError("input adapter failed after a possible click")

        with self.assertRaises(ClickDispatchError) as raised:
            scheduler.run_tiles(scheduler.begin_question("failure"), [0, 1], fail_after_possible_click)
        report = raised.exception.report
        self.assertIsInstance(raised.exception.__cause__, OSError)
        self.assertEqual(calls, [0])
        self.assertEqual(report.stop_reason, "callback_failed")
        self.assertFalse(report.events[0].succeeded)
        self.assertEqual(report.events[0].error_type, "OSError")
        self.assertEqual(report.dispatch_seconds, 0.25)
        self.assertEqual(scheduler.last_dispatch_at, 0.0)
        self.assertEqual(scheduler.last_click_finished_at, 0.25)
        result = scheduler.run_tiles(scheduler.begin_question("after-failure"), [2], calls.append)
        self.assertGreaterEqual(result.events[0].dispatched_at, 0.5)

    def test_invalid_queue_is_rejected_before_any_callback(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("validation")
        calls = []
        for invalid in (True, -1, 9, 1.0, float("nan")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                scheduler.run_tiles(token, [0, invalid], calls.append)
        self.assertEqual(calls, [])

    def test_rollback_latches_closed_before_next_dispatch(self):
        fake = FakeClock(10.0)
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("rollback")
        calls = []
        scheduler.run_tiles(token, [0], calls.append)
        fake.now = 9.0
        with self.assertRaises(ClockError):
            scheduler.run_tiles(token, [1], calls.append)
        fake.now = 20.0
        with self.assertRaises(ClockError):
            scheduler.begin_question("still-closed")
        self.assertEqual(calls, [0])

    def test_invalid_clock_values_and_nonadvancing_sleep_fail_closed(self):
        for invalid in (True, float("nan"), float("inf"), "1"):
            with self.subTest(clock=invalid):
                scheduler = TileClickScheduler(clock=lambda: invalid)
                with self.assertRaises(ClockError):
                    scheduler.begin_question("bad-clock")
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        fake.sleep_hook = lambda duration: None
        calls = []
        with self.assertRaises(ClockError):
            scheduler.run_tiles(scheduler.begin_question("no-progress"), [0, 1], calls.append)
        self.assertEqual(calls, [0])
        self.assertEqual(len(fake.sleeps), 3)

    def test_callback_cancellation_prevents_remaining_queue(self):
        fake = FakeClock()
        scheduler = self.scheduler(fake)
        token = scheduler.begin_question("inside-callback")
        calls = []

        def cancel(tile):
            calls.append(tile)
            scheduler.cancel(token)

        result = scheduler.run_tiles(token, [0, 1], cancel)
        self.assertEqual(calls, [0])
        self.assertEqual(result.stop_reason, "cancelled")


class TimingConfigAndPlanTests(unittest.TestCase):
    def test_dry_run_plan_never_dispatches_and_has_explicit_provisional_first_delay(self):
        self.assertEqual(plan_click_offsets(0), [])
        self.assertEqual(plan_click_offsets(3), [0.0, 0.25, 0.5])
        self.assertEqual(plan_click_offsets(3, 1.5, 0.25), [0.25, 1.75, 3.25])

    def test_config_and_plan_reject_booleans_nonfinite_and_short_intervals(self):
        for field in ("min_interval_seconds", "first_click_delay_seconds", "poll_interval_seconds"):
            for invalid in (True, False, float("nan"), float("inf"), "1"):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    ClickTimingConfig(**{field: invalid})
        for config in (
            {"min_interval_seconds": 0.249},
            {"first_click_delay_seconds": -0.1},
            {"poll_interval_seconds": 0},
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                ClickTimingConfig(**config)
        for invalid_count in (True, -1, 1.0, float("nan")):
            with self.subTest(count=invalid_count), self.assertRaises(ValueError):
                plan_click_offsets(invalid_count)
        with self.assertRaises(ValueError):
            plan_click_offsets(2, first_click_delay_seconds=1.79e308, min_interval_seconds=1.79e308)

    def test_quarter_second_boundary_and_explicit_slower_policy(self):
        self.assertEqual(ClickTimingConfig(min_interval_seconds=0.25).min_interval_seconds, 0.25)
        self.assertEqual(plan_click_offsets(3, 0.25), [0.0, 0.25, 0.5])
        self.assertEqual(plan_click_offsets(3, 1.0), [0.0, 1.0, 2.0])
        with self.assertRaisesRegex(ValueError, "at least 0.25"):
            plan_click_offsets(2, 0.249)


if __name__ == "__main__":
    unittest.main()
