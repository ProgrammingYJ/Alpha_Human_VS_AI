"""Pixel-only inference and guarded OS clicks for the controlled ALPHA booth.

This module reads no website answers, tile URLs, image identities or demo bank.
Public question conditions may be supplied by an operator or room synchronizer.
"""

from dataclasses import asdict, dataclass
import hashlib
import time
from urllib.parse import urlsplit

from PIL import Image

from .geometry import GridLayout
from .tasks import TaskCondition, select_tiles
from .timing import MIN_TILE_INTERVAL_SECONDS, ClickDispatchError, ClickTimingConfig, TileClickScheduler, plan_click_offsets


class UnsupportedBoothTask(ValueError):
    pass


class BoothScreenChanged(RuntimeError):
    pass


class BoothRunError(RuntimeError):
    def __init__(self, report, cause):
        self.report = report
        super().__init__(str(cause))


def public_condition(value):
    """Accept only the visible question's general condition, never answer data."""
    if not isinstance(value, dict) or set(value) - {"task_type", "operator", "n"}:
        raise ValueError("only public task_type/operator/n fields are accepted")
    if value.get("task_type") == "tree_count":
        if value.get("operator") != "gte" or type(value.get("n")) is not int or value["n"] != 3:
            raise UnsupportedBoothTask("tree counting currently supports only an explicit >=3 adapter")
        return dict(value)
    return TaskCondition.from_dict(value)


def _rect(value, name):
    if not isinstance(value, dict) or set(value) != {"left", "top", "width", "height"}:
        raise ValueError(f"{name} requires left/top/width/height")
    if any(type(number) is not int or number < 0 for number in value.values()):
        raise ValueError(f"{name} must contain non-negative integer pixels")
    if not value["width"] or not value["height"]:
        raise ValueError(f"{name} must have positive dimensions")
    return dict(value)


@dataclass(frozen=True)
class BoothLayout:
    url: str
    expected_window_title: str
    calibrated: bool
    grid: GridLayout
    submit: tuple[int, int]
    question_guard: dict
    min_interval_seconds: float = MIN_TILE_INTERVAL_SECONDS
    first_click_delay_seconds: float = 0.0

    @classmethod
    def from_dict(cls, value):
        allowed = {"url", "expected_window_title", "calibrated", "grid", "submit",
                   "question_guard", "min_interval_seconds", "first_click_delay_seconds"}
        if not isinstance(value, dict) or set(value) - allowed:
            raise ValueError("unsupported booth layout field")
        url = value.get("url", "")
        parsed = urlsplit(url)
        # The owned deployed host is explicit; arbitrary third-party CAPTCHAs
        # are outside this controlled integration runner.
        if (parsed.scheme not in {"http", "https"} or parsed.hostname not in
                {"localhost", "127.0.0.1", "::1", "bot.marulee.dev"}
                or parsed.username or parsed.password or parsed.fragment):
            raise ValueError("url must identify the controlled local or bot.marulee.dev booth")
        title = value.get("expected_window_title")
        if not isinstance(title, str) or not title.strip() or "ALPHA" not in title.upper():
            raise ValueError("an explicit ALPHA bot window title is required")
        if type(value.get("calibrated")) is not bool:
            raise ValueError("calibrated must be a bool")
        grid = GridLayout(**value["grid"])
        if grid.rows != 3 or grid.columns != 3:
            raise ValueError("booth grid must be exactly 3x3")
        submit = value.get("submit")
        if not isinstance(submit, dict) or set(submit) != {"x", "y"} or any(
                type(number) is not int or number < 0 for number in submit.values()):
            raise ValueError("submit must contain non-negative integer x/y")
        timing = ClickTimingConfig(value.get("min_interval_seconds", MIN_TILE_INTERVAL_SECONDS),
                                   value.get("first_click_delay_seconds", 0.0))
        return cls(url, title, value["calibrated"], grid, (submit["x"], submit["y"]),
                   _rect(value["question_guard"], "question_guard"),
                   timing.min_interval_seconds, timing.first_click_delay_seconds)


def crop_rect(image, rect):
    left, top, width, height = (rect[key] for key in ("left", "top", "width", "height"))
    if left + width > image.width or top + height > image.height:
        raise ValueError("configured rectangle lies outside the captured physical screen")
    return image.crop((left, top, left + width, top + height)).convert("RGB")


def crop_screen_tiles(image, grid):
    """Remove CSS gaps rather than mixing neighbouring photos into model input."""
    if not isinstance(image, Image.Image):
        raise TypeError("screen capture must be PIL pixels")
    if grid.left + grid.width > image.width or grid.top + grid.height > image.height:
        raise ValueError("grid lies outside the captured physical screen")
    tile_width = (grid.width - 2 * grid.gap_x) / 3
    tile_height = (grid.height - 2 * grid.gap_y) / 3
    return [image.crop((
        int(grid.left + column * (tile_width + grid.gap_x)),
        int(grid.top + row * (tile_height + grid.gap_y)),
        int(grid.left + column * (tile_width + grid.gap_x) + tile_width),
        int(grid.top + row * (tile_height + grid.gap_y) + tile_height),
    )).convert("RGB") for row in range(3) for column in range(3)]


def pixel_sha256(image):
    rgb = image.convert("RGB")
    return hashlib.sha256(str(rgb.size).encode("ascii") + rgb.tobytes()).hexdigest()


class PyAutoGuiScreen:
    """Lazy native adapter. Importing the module never captures or clicks."""

    def __init__(self):
        import sys
        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except (AttributeError, OSError):
                ctypes.windll.user32.SetProcessDPIAware()
        import pyautogui
        self.api = pyautogui
        self.api.FAILSAFE = True

    def title(self):
        getter = getattr(self.api, "getActiveWindowTitle", None)
        if getter is None:
            raise RuntimeError("active GUI window verification is unavailable in this session")
        return getter() or ""

    def capture(self):
        return self.api.screenshot().convert("RGB")

    def click(self, x, y):
        self.api.click(x=x, y=y)


class BoothBotRunner:
    def __init__(self, predictor, screen, layout, *, tree_predictor=None,
                 clock=time.monotonic, sleep=time.sleep):
        if not isinstance(layout, BoothLayout):
            raise ValueError("layout must be a BoothLayout")
        self.predictor, self.screen, self.layout = predictor, screen, layout
        self.tree_predictor, self.clock = tree_predictor, clock
        self._attempted_questions = set()
        self.scheduler = TileClickScheduler(ClickTimingConfig(
            layout.min_interval_seconds, layout.first_click_delay_seconds), clock=clock, sleep=sleep)

    def _verify_window(self):
        title = self.screen.title()
        if self.layout.expected_window_title not in title:
            raise BoothScreenChanged("the controlled ALPHA bot window is not foreground")
        return title

    def check_ready_surface(self):
        """Check the calibrated foreground surface and capture bounds only."""
        if self.layout.calibrated is not True:
            raise ValueError("readiness requires an explicitly calibrated layout")
        title = self._verify_window()
        capture = self.screen.capture()
        crop_screen_tiles(capture, self.layout.grid)
        crop_rect(capture, self.layout.question_guard)
        if self.layout.submit[0] >= capture.width or self.layout.submit[1] >= capture.height:
            raise ValueError("submit lies outside the captured physical screen")
        return title

    def run_once(self, condition, *, execute=False, question_id="manual", public_guard=None):
        if type(execute) is not bool:
            raise ValueError("execute must be a bool")
        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError("a non-empty public question identity is required")
        if execute and question_id in self._attempted_questions:
            raise ValueError("this question already had an OS attempt; use a new participant and room, never toggle the same predictions again")
        parsed = public_condition(condition)
        if isinstance(parsed, dict) and self.tree_predictor is None:
            raise UnsupportedBoothTask("tree_count>=3 needs a real tree ML adapter; presence scores cannot count trees")
        if execute and self.layout.calibrated is not True:
            raise ValueError("physical clicks require an explicitly calibrated layout")
        started = self.clock()
        title = self._verify_window()
        if public_guard is not None and not public_guard():
            raise BoothScreenChanged("public round is not active")
        capture = self.screen.capture()
        tiles = crop_screen_tiles(capture, self.layout.grid)
        anchor = pixel_sha256(crop_rect(capture, self.layout.question_guard))
        if self.layout.submit[0] >= capture.width or self.layout.submit[1] >= capture.height:
            raise ValueError("submit lies outside the captured physical screen")
        inference_started = self.clock()
        if isinstance(parsed, dict):
            predictions = self.tree_predictor.predict_at_least_three(tiles)
            if len(predictions) != 9 or any(type(item) is not bool for item in predictions):
                raise ValueError("tree adapter must return nine explicit ML decisions")
            selected = [index for index, item in enumerate(predictions) if item]
            output_predictions = [{"at_least_three": item} for item in predictions]
        else:
            predictions = self.predictor.predict_tiles(tiles)
            threshold = self.predictor.presence_metadata["profile"]["threshold"]
            selected = select_tiles(predictions, parsed, {name: threshold for name in ("tree", "building", "pond")})
            output_predictions = [{"presence_scores": dict(item.presence_scores),
                                   "person_count": item.person_count} for item in predictions]
        inference_seconds = self.clock() - inference_started
        clicks = self.layout.grid.plan(selected)
        result = {"schema_version": 1, "mode": "execute" if execute else "dry-run",
                  "condition": dict(condition), "question_id": question_id,
                  "source": "actual_model_rgb_predictions", "selected_tiles": selected,
                  "predictions": output_predictions, "click_plan": clicks,
                  "capture_performed": True, "mouse_control_performed": False,
                  "mouse_control_attempted": False, "tile_click_count": 0,
                  "submit_performed": False, "inference_wall_seconds": inference_seconds,
                  "window_title": title, "origin": urlsplit(self.layout.url).netloc,
                  "question_guard_sha256": anchor, "click_events": [],
                  "first_click_delay_seconds": self.layout.first_click_delay_seconds,
                  "submit_interval_policy": "submit is outside the tile interval rule",
                  "new_accuracy_measurement": False}
        if isinstance(parsed, dict):
            result["tree_model_provenance"] = getattr(self.tree_predictor, "provenance", None)
            result["tree_detections"] = getattr(self.tree_predictor, "last_detections", [])
        grid_rect = {key: getattr(self.layout.grid, key) for key in ("left", "top", "width", "height")}
        if not execute:
            result["planned_click_offsets_seconds"] = plan_click_offsets(
                len(selected), self.layout.min_interval_seconds, self.layout.first_click_delay_seconds)
            result["elapsed_seconds"] = self.clock() - started
            return result, crop_rect(capture, grid_rect), None

        def guard():
            self._verify_window()
            if public_guard is not None and not public_guard():
                raise BoothScreenChanged("public round changed or ended")
            if pixel_sha256(crop_rect(self.screen.capture(), self.layout.question_guard)) != anchor:
                raise BoothScreenChanged("visible question changed; remaining clicks were cancelled")

        def click_tile(index):
            guard()
            x, y = self.layout.grid.center(index)
            actual = self.clock()
            result["mouse_control_attempted"] = True
            self.screen.click(x, y)
            result["mouse_control_performed"] = True
            result["click_events"].append({"tile_index": index, "x": x, "y": y,
                                           "os_call_at_monotonic": actual,
                                           "os_call_finished_at_monotonic": self.clock()})
            result["tile_click_count"] = len(result["click_events"])

        # Once any native attempt is scheduled, retrying this same question
        # could toggle already selected tiles. Dry-runs do not consume it.
        self._attempted_questions.add(question_id)
        token = self.scheduler.begin_question(question_id)
        try:
            click_report = self.scheduler.run_tiles(token, selected, click_tile)
        except ClickDispatchError as error:
            result.update(scheduler=asdict(error.report), mouse_control_performed=bool(result["click_events"]),
                          status="aborted", error_type=type(error.__cause__).__name__,
                          error=str(error.__cause__), elapsed_seconds=self.clock() - started)
            raise BoothRunError(result, error.__cause__) from error
        result["scheduler"] = asdict(click_report)
        result["mouse_control_performed"] = bool(result["click_events"])
        intervals = [right["os_call_at_monotonic"] - left["os_call_at_monotonic"]
                     for left, right in zip(result["click_events"], result["click_events"][1:])]
        result["observed_os_call_intervals_seconds"] = intervals
        if any(interval < self.layout.min_interval_seconds for interval in intervals):
            raise RuntimeError("actual OS click call interval violated the configured tile interval")
        try:
            guard()
            result["submit_os_call_at_monotonic"] = self.clock()
            result["mouse_control_attempted"] = True
            self.screen.click(*self.layout.submit)
        except Exception as error:
            result.update(status="aborted", error_type=type(error).__name__,
                          error=str(error), elapsed_seconds=self.clock() - started)
            raise BoothRunError(result, error) from error
        result["submit_performed"] = True
        result["mouse_control_performed"] = True
        result["elapsed_seconds"] = self.clock() - started
        # After submission the page may change; save only the grid's pixels.
        return result, crop_rect(capture, grid_rect), crop_rect(self.screen.capture(), grid_rect)
