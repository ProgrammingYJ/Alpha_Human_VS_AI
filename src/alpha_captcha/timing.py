"""Rate-limit synchronous tile callbacks without implementing mouse control.

The callback must perform at most one tile click synchronously, including a
selection toggle. A dispatch record describes that callback, not proof that an
OS mouse event succeeded. Submission is deliberately outside this API. The
default first-click delay of zero is provisional, pending the booth rules.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import math
from numbers import Real
import threading
import time
from typing import Literal


MIN_TILE_INTERVAL_SECONDS = 0.25


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number, not a boolean")
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real number") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _after(base: float, delay: float) -> float:
    """Round a deadline upward if float addition would shorten the interval."""
    deadline = base + delay
    if not math.isfinite(deadline):
        raise ValueError("scheduled time exceeds the finite clock range")
    if deadline - base < delay:
        deadline = math.nextafter(deadline, math.inf)
    if not math.isfinite(deadline):
        raise ValueError("scheduled time exceeds the finite clock range")
    return deadline


@dataclass(frozen=True)
class ClickTimingConfig:
    min_interval_seconds: float = MIN_TILE_INTERVAL_SECONDS
    first_click_delay_seconds: float = 0.0
    poll_interval_seconds: float = 0.05

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _finite_number(getattr(self, name), name))
        if self.min_interval_seconds < MIN_TILE_INTERVAL_SECONDS:
            raise ValueError(f"min_interval_seconds must be at least {MIN_TILE_INTERVAL_SECONDS}")
        if self.first_click_delay_seconds < 0:
            raise ValueError("first_click_delay_seconds must be non-negative")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")


def plan_click_offsets(
    count: int,
    min_interval_seconds: float = MIN_TILE_INTERVAL_SECONDS,
    first_click_delay_seconds: float = 0.0,
) -> list[float]:
    """Plan relative dry-run offsets; no sleep, callback or scheduler mutation.

    These assume no processing delay or prior click. The first delay defaults
    provisionally to zero. Submission is not included, nor is this a prediction
    of real elapsed time. A live scheduler also preserves prior-question timing.
    """
    if type(count) is not int or count < 0:
        raise ValueError("count must be a non-negative integer, not a boolean")
    config = ClickTimingConfig(min_interval_seconds, first_click_delay_seconds)
    offsets = []
    for index in range(count):
        offset = (
            config.first_click_delay_seconds if index == 0
            else _after(offsets[-1], config.min_interval_seconds)
        )
        offsets.append(offset)
    return offsets


@dataclass(frozen=True)
class QuestionToken:
    question_id: str
    generation: int


@dataclass(frozen=True)
class ClickEvent:
    tile_index: int
    requested_at: float
    scheduled_at: float
    dispatched_at: float
    finished_at: float
    succeeded: bool
    error_type: str | None = None

    @property
    def required_wait_seconds(self) -> float:
        return self.scheduled_at - self.requested_at

    @property
    def wait_seconds(self) -> float:
        return self.dispatched_at - self.requested_at

    @property
    def dispatch_seconds(self) -> float:
        return self.finished_at - self.dispatched_at


StopReason = Literal["completed", "cancelled", "question_changed", "callback_failed"]


@dataclass(frozen=True)
class ClickRunReport:
    token: QuestionToken
    events: tuple[ClickEvent, ...]
    started_at: float
    finished_at: float
    wait_seconds: float
    stop_reason: StopReason

    @property
    def dispatch_seconds(self) -> float:
        return sum(event.dispatch_seconds for event in self.events)

    @property
    def elapsed_seconds(self) -> float:
        return self.finished_at - self.started_at


class ClockError(RuntimeError):
    """A clock/sleep fault latched the scheduler closed; no more dispatches."""


class ClickDispatchError(RuntimeError):
    """A callback failed; inspect report and the chained original exception."""

    def __init__(self, report: ClickRunReport) -> None:
        super().__init__("tile callback failed; remaining tile queue was stopped")
        self.report = report


class TileClickScheduler:
    """Serialize tile callbacks and preserve cooldown across problem changes.

    A callback completion is the conservative next-click reference, because an
    adapter can spend time before it sends its one synchronous click. Failed
    callbacks also consume this cooldown: they might have clicked before raising.
    No catch-up schedule is accumulated. begin_question/cancel may be called by
    another thread or the callback; an already-running callback cannot be undone.
    The same scheduler must be retained for all questions on one input device.
    """

    def __init__(
        self,
        config: ClickTimingConfig | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if config is not None and not isinstance(config, ClickTimingConfig):
            raise ValueError("config must be a ClickTimingConfig")
        if not callable(clock) or not callable(sleep):
            raise ValueError("clock and sleep must be callable")
        self.config = config or ClickTimingConfig()
        self._clock = clock
        self._sleep = sleep
        self._state_lock = threading.RLock()
        self._run_lock = threading.Lock()
        self._active: QuestionToken | None = None
        self._question_started_at = 0.0
        self._generation = 0
        self._last_observed: float | None = None
        self._last_dispatch_at: float | None = None
        self._last_finished_at: float | None = None
        self._clock_fault: str | None = None

    def _fault(self, message: str) -> None:
        self._clock_fault = message
        self._active = None
        raise ClockError(message)

    def _now(self) -> float:
        with self._state_lock:
            if self._clock_fault is not None:
                raise ClockError(f"scheduler stopped after a clock fault: {self._clock_fault}")
            try:
                value = _finite_number(self._clock(), "clock result")
            except Exception as error:
                self._fault(f"invalid monotonic clock: {type(error).__name__}")
            if self._last_observed is not None and value < self._last_observed:
                self._fault("monotonic clock moved backwards")
            self._last_observed = value
            return value

    @property
    def last_dispatch_at(self) -> float | None:
        with self._state_lock:
            return self._last_dispatch_at

    @property
    def last_click_finished_at(self) -> float | None:
        with self._state_lock:
            return self._last_finished_at

    def begin_question(self, question_id: str) -> QuestionToken:
        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError("question_id must be a non-empty string")
        with self._state_lock:
            now = self._now()
            self._generation += 1
            token = QuestionToken(question_id, self._generation)
            self._active = token
            self._question_started_at = now
            return token

    def cancel(self, token: QuestionToken | None = None) -> None:
        if token is not None and not isinstance(token, QuestionToken):
            raise ValueError("token must be a QuestionToken")
        with self._state_lock:
            if token is None or token is self._active:
                self._active = None

    def _stop_reason(self, token: QuestionToken) -> StopReason | None:
        if self._active is None:
            return "cancelled"
        if token is not self._active:
            return "question_changed"
        return None

    def run_tiles(
        self,
        token: QuestionToken,
        tile_indices: Iterable[int],
        callback: Callable[[int], None],
    ) -> ClickRunReport:
        """Run a finite queue; repeated indices are separately limited toggles.

        Validate the entire queue before dispatch. Return partial records after
        cancellation/replacement; callback failures stop and raise with records.
        Tokens are accepted by identity, so an old/recreated token cannot resume
        an earlier queue even when its textual question ID matches a new one.
        """
        if not isinstance(token, QuestionToken):
            raise ValueError("token must be a QuestionToken")
        if not callable(callback):
            raise ValueError("callback must be callable")
        tiles = tuple(tile_indices)
        if any(type(index) is not int or not 0 <= index < 9 for index in tiles):
            raise ValueError("tile indices must be integers in [0, 8], booleans excluded")
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("only one run_tiles call may dispatch at a time")
        try:
            started = self._now()
            events: list[ClickEvent] = []
            waited = 0.0

            def report(reason: StopReason, finished: float) -> ClickRunReport:
                return ClickRunReport(token, tuple(events), started, finished, waited, reason)

            for tile in tiles:
                with self._state_lock:
                    requested = self._now()
                    stopped = self._stop_reason(token)
                    if stopped is not None:
                        return report(stopped, requested)
                    scheduled = max(requested, _after(
                        self._question_started_at, self.config.first_click_delay_seconds,
                    ))
                    if self._last_finished_at is not None:
                        scheduled = max(scheduled, _after(
                            self._last_finished_at, self.config.min_interval_seconds,
                        ))
                no_progress = 0
                while True:
                    with self._state_lock:
                        now = self._now()
                        stopped = self._stop_reason(token)
                        if stopped is not None:
                            waited += now - requested
                            return report(stopped, now)
                        remaining = scheduled - now
                        if remaining <= 0:
                            # Keep token validation and callback entry atomic with
                            # respect to another thread's begin_question/cancel.
                            waited += now - requested
                            self._last_dispatch_at = now
                            self._last_finished_at = now
                            failure: BaseException | None = None
                            try:
                                callback(tile)
                            except BaseException as error:
                                failure = error
                            finished = self._now()
                            self._last_finished_at = finished
                            events.append(ClickEvent(
                                tile, requested, scheduled, now, finished,
                                failure is None,
                                type(failure).__name__ if failure is not None else None,
                            ))
                            if failure is not None:
                                failed_report = report("callback_failed", finished)
                                if isinstance(failure, Exception):
                                    raise ClickDispatchError(failed_report) from failure
                                raise failure
                            break
                    self._sleep(min(remaining, self.config.poll_interval_seconds))
                    with self._state_lock:
                        after = self._now()
                        no_progress = no_progress + 1 if after == now else 0
                        if no_progress >= 3 and self._stop_reason(token) is None:
                            self._fault("sleep returned repeatedly without clock progress")
            return report("completed", self._now())
        finally:
            self._run_lock.release()
