"""Cooperative model-call pacing, not a hardware GPU utilization quota.

One pacer belongs to one inference worker/run. It neither changes a device's
power/clock settings nor partitions its SMs or memory. Each completed chunk is
followed by its own rest period; earlier idle time never earns burst credit.
"""

import math
from numbers import Real
import time


class CooperativePacer:
    """Limit model-call time relative to completed cooperative rest periods.

    The call interval includes CPU preprocessing/postprocessing and completion
    of that worker's CUDA stream. It is deliberately a conservative wall-clock
    budget, not a measurement of GPU kernel occupancy or device utilization.

    ``synchronize`` must synchronize only this worker's work. ``check_running``
    must be a cheap, local cancellation/heartbeat check, never an HTTP request.
    The object is worker-local and is not safe for concurrent calls.
    """

    _SLEEP_SLICE_SECONDS = 0.05

    def __init__(self, duty_cycle, *, clock=time.perf_counter, sleep=time.sleep):
        if (isinstance(duty_cycle, bool) or not isinstance(duty_cycle, Real)
                or not math.isfinite(duty_cycle) or not 0 < duty_cycle <= 1):
            raise ValueError("duty_cycle must be a finite number greater than zero and at most one")
        if not callable(clock) or not callable(sleep):
            raise TypeError("clock and sleep must be callable")
        self.duty_cycle = float(duty_cycle)
        self._clock, self._sleep = clock, sleep
        self._work_seconds = 0.0
        self._throttle_seconds = 0.0
        self._throttle_planned_seconds = 0.0
        self._chunk_count = 0

    def run(self, call, *, synchronize=lambda: None, check_running=lambda: None):
        """Run one chunk and rest after it, including the last chunk of a run.

        A failed call is still synchronized and measured, then propagated
        immediately without a forced cooldown or retry. Cancellation behaves
        the same way. Sleep is requested in slices of at most 50 ms; scheduling
        delays may make the actual wait longer on a busy computer.
        """
        check_running()
        synchronize()
        started = self._clock()
        call_error = None
        try:
            try:
                result = call()
            except BaseException as error:
                call_error = error
                raise
            finally:
                try:
                    synchronize()
                except BaseException:
                    # Cleanup is best-effort if the model already failed: do
                    # not hide its original exception with a second failure.
                    if call_error is None:
                        raise
        finally:
            work_seconds = max(0.0, self._clock() - started)
            self._work_seconds += work_seconds
            self._chunk_count += 1

        check_running()
        planned = work_seconds * (1.0 / self.duty_cycle - 1.0)
        self._throttle_planned_seconds += planned
        rested = 0.0
        while rested < planned:
            check_running()
            before = self._clock()
            # Large monotonic timestamps can round a tiny final remainder to
            # zero. Request a representable step instead of spinning on it.
            minimum_step = 2.0 * math.ulp(before)
            requested = min(self._SLEEP_SLICE_SECONDS, max(planned - rested, minimum_step))
            try:
                self._sleep(requested)
            finally:
                elapsed = max(0.0, self._clock() - before)
                self._throttle_seconds += elapsed
                rested += elapsed
            if elapsed <= 0:
                # Injected clocks/sleepers must progress; avoid a spin loop
                # if a caller supplies an invalid timing pair.
                raise RuntimeError("pacer sleep did not advance the monotonic clock")
        check_running()
        return result

    def metrics(self):
        total = self._work_seconds + self._throttle_seconds
        return {
            "inference_work_seconds": self._work_seconds,
            "resource_throttle_seconds": self._throttle_seconds,
            "resource_throttle_planned_seconds": self._throttle_planned_seconds,
            "resource_work_fraction_observed": self._work_seconds / total if total else None,
            "inference_chunk_count": self._chunk_count,
            "target_gpu_duty_cycle": self.duty_cycle,
            "quota_kind": "cooperative_model_call_time",
            "hardware_gpu_quota_enforced": False,
            "memory_allocator_limit_fraction": None,
        }
