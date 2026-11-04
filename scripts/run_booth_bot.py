"""Capture the controlled ALPHA bot window, infer RGB tiles and optionally click.

Dry-run is the default. --execute is required for real OS input. No answer bank,
website image IDs/URLs or submission API are used by the solver.
"""

import argparse
import json
import math
from pathlib import Path
import time
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import webbrowser

from alpha_captcha.booth_bot import (
    BoothBotRunner, BoothLayout, BoothRunError, BoothScreenChanged, PyAutoGuiScreen, public_condition,
)
from alpha_captcha.inference import TorchTilePredictor


BOOTH_USER_AGENT = "AlphaCaptchaBoothBot/1.0"


class LazyTreePredictor:
    """Load the pinned local tree model only when a tree question is inferred."""
    def __init__(self, *, device="cpu", model_dir=None):
        self.device, self.model_dir, self.model = device, model_dir, None
        self.last_loading_seconds = 0.0

    @property
    def provenance(self):
        return self.model.provenance if self.model is not None else None

    @property
    def last_detections(self):
        return self.model.last_detections if self.model is not None else []

    def prepare(self):
        """Validate/load the pinned tree model before announcing readiness."""
        self.last_loading_seconds = 0.0
        if self.model is None:
            from alpha_captcha.tree_model import TreeCountPredictor
            started = time.monotonic()
            self.model = TreeCountPredictor(self.model_dir, device=self.device)
            self.last_loading_seconds = time.monotonic() - started
        return self.last_loading_seconds

    def predict_at_least_three(self, images):
        self.prepare()
        return self.model.predict_at_least_three(images)


class BoothConnectionError(RuntimeError):
    """A bounded public error code, never a response body or role capability."""
    def __init__(self, status, code=None):
        self.status, self.code = status, code
        messages = {
            "bot_already_connected": "이미 봇 화면이 먼저 참가했습니다. 인간 화면에서 새 대결방을 만든 뒤 실행기에 새 코드를 입력하세요. 웹 봇 참가 버튼을 먼저 누르지 마세요.",
            "not_found": "대기실을 찾을 수 없습니다. 인간 화면의 새 대결방 코드를 확인하세요.",
            "invalid_code": "인간 화면에 표시된 8자리 연결 코드를 입력하세요.",
            "room_expired": "대기실이 만료됐습니다. 새 대결방에서 실행하세요.",
            "round_in_progress": "이미 시작한 대결방입니다. 다음 참가자의 새 방을 사용하세요.",
            "unauthorized": "봇 역할 연결이 유효하지 않습니다. 새 대결방에서 실행하세요.",
        }
        super().__init__(messages.get(code, f"서버 연결에 실패했습니다 (HTTP {status}). 인터넷과 공개 사이트 상태를 확인하세요."))


def startup_message(stage, error):
    if isinstance(error, BoothConnectionError):
        return str(error)
    messages = {
        "model_loading": "모델을 불러오지 못했습니다. 체크포인트·나무 가중치 경로와 CUDA 환경을 확인하세요.",
        "gui_initialization": "이 PC의 화면 캡처·마우스 환경을 초기화하지 못했습니다.",
        "room_join": "공개 서버 대기실에 연결하지 못했습니다. 연결 코드와 인터넷 상태를 확인하세요.",
        "browser_open": "봇 브라우저를 열지 못했습니다. 기본 브라우저 설정을 확인하세요.",
        "ready_surface": "보정된 봇 창을 확인하지 못했습니다. ALPHA BOT 창을 전면에 두고 해상도·배율·좌표 설정을 확인하세요.",
        "waiting_for_start": "시작할 수 있는 새 문제가 없습니다. 봇 창을 전면에 둔 채 인간 화면에서 새 대결을 시작하세요.",
    }
    return messages.get(stage, "봇 실행을 중단했습니다. 실행 보고서의 단계와 오류 종류를 확인하세요.")


def wait_for_ready_surface(runner, *, timeout=20.0, clock=time.monotonic, sleep=time.sleep):
    """Check foreground identity and calibrated capture bounds, without clicks.

    Before start the grid contains a placeholder. This does not claim that nine
    challenge photos have loaded; the render wait after start remains separate.
    """
    deadline = clock() + timeout
    while True:
        try:
            runner.check_ready_surface()
            return
        except BoothScreenChanged:
            if clock() >= deadline:
                raise
            sleep(min(0.2, max(0.0, deadline - clock())))


class PublicRoomSession:
    """Keep only publicly visible phase/round/start time/general condition.

    Responses are projected immediately. Tile identities and answers are not
    retained, logged or forwarded to model inference. Role tokens stay in RAM.
    """
    def __init__(self, base_url, code):
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
                "localhost", "127.0.0.1", "::1", "bot.marulee.dev"} or parsed.username or parsed.password \
                or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("room synchronization is restricted to the controlled booth origin")
        self.base_url = base_url.rstrip("/")
        self.token = None
        joined = self._request("/api/rooms/join", {"code": code, "role": "bot"})
        self.room_id = joined["roomId"]
        self.token = joined["token"]
        if (not isinstance(self.room_id, str) or not self.room_id or not isinstance(self.token, str)
                or not self.token or any(ord(char) < 33 or ord(char) == 127 for char in self.token)):
            raise ValueError("invalid role session response")

    def _request(self, path, body=None):
        headers = {"Accept": "application/json", "User-Agent": BOOTH_USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = Request(self.base_url + path, data=data, headers=headers)
        # urllib error text does not include headers. Do not print response
        # bodies, join results or the token-bearing browser fragment.
        try:
            with urlopen(request, timeout=5) as response:
                raw = response.read(2_000_001)
        except HTTPError as error:
            code = None
            raw_error = error.read(65537)
            if len(raw_error) <= 65536:
                try:
                    public_code = json.loads(raw_error).get("code")
                    if public_code in {"bot_already_connected", "not_found", "invalid_code", "room_expired",
                                       "round_in_progress", "unauthorized"}:
                        code = public_code
                except (ValueError, AttributeError, TypeError):
                    pass
            raise BoothConnectionError(error.code, code) from None
        if len(raw) > 2_000_000:
            raise ValueError("room response exceeds the bounded public synchronization size")
        return json.loads(raw)

    def view(self):
        value = self._request(f"/api/rooms/{quote(self.room_id, safe='')}")
        if isinstance(value.get("state"), dict):
            value = value["state"]
        result = {name: value.get(name) for name in ("phase", "roundId", "startAt")}
        topic = value.get("topic")
        if isinstance(topic, dict) and isinstance(topic.get("condition"), dict):
            public_condition(topic["condition"])
            result["condition"] = dict(topic["condition"])
        return result

    def set_ready(self, ready):
        if type(ready) is not bool:
            raise ValueError("ready must be an explicit boolean")
        self._request(f"/api/rooms/{quote(self.room_id, safe='')}/ready", {"ready": ready})

    def open_browser(self, bot_path="/?role=bot"):
        if not bot_path.startswith("/") or "#" in bot_path or "://" in bot_path:
            raise ValueError("bot path must be a relative public route")
        url = self.base_url + bot_path + "#" + urlencode({"room": self.room_id, "token": self.token})
        webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="calibrated physical screen layout")
    parser.add_argument("--task", choices=["tree_present", "building_present", "pond_present",
                                           "person_present", "person_count", "tree_count"])
    parser.add_argument("--operator", choices=["gte", "eq"])
    parser.add_argument("--n", type=int)
    parser.add_argument("--execute", action="store_true", help="perform real OS tile clicks and submit")
    parser.add_argument("--ready", action="store_true",
                        help="announce ready only after all models and the calibrated foreground bot surface are checked")
    parser.add_argument("--presence", type=Path, default=Path("models/checkpoints/presence-limited-v1/presence.pt"))
    parser.add_argument("--person", type=Path, default=Path("models/checkpoints/person-limited-v1/person.pt"))
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--tree-model", choices=["grounding-dino"],
                        help="pinned local tree adapter; loaded before --ready, otherwise on the first tree_count question")
    parser.add_argument("--tree-model-dir", type=Path, help="optional already downloaded local tree model directory")
    parser.add_argument("--output", type=Path, required=True, help="new run directory, never overwrite")
    parser.add_argument("--room", help="optional room code; only public timing and question condition are read")
    parser.add_argument("--base-url", help="controlled room API origin")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--bot-path", default="/?role=bot")
    parser.add_argument("--rounds", type=int, choices=[1], default=1,
                        help="one participant plays one game; a new participant needs a new room")
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--render-wait-seconds", type=float, default=0.25,
                        help="explicit UI render wait after public round activation; logged separately")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory already exists; use a new name")
    if args.ready and (not args.execute or not args.room or not args.tree_model):
        parser.error("--ready requires --execute, --room and --tree-model grounding-dino")
    if (not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0
            or not math.isfinite(args.render_wait_seconds) or args.render_wait_seconds < 0):
        parser.error("invalid round/time limits")
    try:
        layout = BoothLayout.from_dict(json.loads(args.config.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError, TypeError, KeyError):
        parser.error("유효한 화면 보정 설정을 읽지 못했습니다. scripts/start_booth_bot.ps1 -Calibrate로 직접 보정하세요.")
    if args.execute and layout.calibrated is not True:
        parser.error("실제 클릭에는 보정된 calibrated=true 설정이 필요합니다. 예시 좌표로 실행하지 않습니다.")
    condition = None
    if args.task:
        condition = {"task_type": args.task}
        if args.operator is not None:
            condition["operator"] = args.operator
        if args.n is not None:
            condition["n"] = args.n
        public_condition(condition)
    if not args.room and condition is None:
        parser.error("supply an explicit public --task or --room")
    if args.room and (not args.base_url or args.task):
        parser.error("room mode requires --base-url and gets its condition from the public question")
    # Check unsupported tree count before loading weights or touching the GUI.
    if condition and condition["task_type"] == "tree_count" and not args.tree_model:
        parser.error("tree_count>=3 needs a real tree ML adapter; presence cannot count trees")
    args.output.mkdir(parents=True)
    completed, seen = [], set()
    session, announced_ready = None, False
    stage = "model_loading"
    try:
        print(json.dumps({"status": stage, "message": "로컬 ML 모델을 불러오는 중입니다. 아직 인간 대결을 시작하지 마세요."}, ensure_ascii=False), flush=True)
        loading_started = time.monotonic()
        predictor = TorchTilePredictor.from_checkpoints(args.presence, args.person, device=args.device)
        tree = LazyTreePredictor(device=args.device, model_dir=args.tree_model_dir) if args.tree_model else None
        if args.ready and tree is not None:
            tree.prepare()
        loading_seconds = time.monotonic() - loading_started
        stage = "gui_initialization"
        runner = BoothBotRunner(predictor, PyAutoGuiScreen(), layout, tree_predictor=tree)
        stage = "room_join"
        session = PublicRoomSession(args.base_url, args.room) if args.room else None
        if session and args.open_browser:
            stage = "browser_open"
            session.open_browser(args.bot_path)
        if session and args.ready:
            stage = "ready_surface"
            wait_for_ready_surface(runner)
            session.set_ready(True)
            announced_ready = True
        stage = "waiting_for_start"
        print(json.dumps({"status": stage, "ready_announced": announced_ready,
                          "message": "로컬 봇 실행 중입니다. 봇 창을 전면에 유지하세요. 인간 화면은 패드 등 다른 기기에서 시작하거나, 같은 PC라면 시작 후 봇 창으로 돌아오세요."}, ensure_ascii=False), flush=True)
        deadline = time.monotonic() + args.timeout_seconds
        while len(completed) < args.rounds:
            public_guard = None
            round_id = "manual"
            render_wait = 0.0
            if session:
                state = session.view()
                if state["phase"] == "result":
                    raise RuntimeError("the participant's game has already ended; create a new room")
                if state["phase"] != "playing" or not state["roundId"] or state["roundId"] in seen:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("no new public active round before the timeout")
                    time.sleep(0.15)
                    continue
                if not state.get("condition"):
                    raise ValueError("public active round has no general question condition")
                condition, round_id = state["condition"], state["roundId"]
                seen.add(round_id)
                if state.get("startAt") is not None and time.time() * 1000 < state["startAt"]:
                    time.sleep(min(0.15, (state["startAt"] - time.time() * 1000) / 1000))
                    seen.remove(round_id)
                    continue

                def public_guard():
                    current = session.view()
                    return (current["phase"] == "playing" and current["roundId"] == round_id
                            and current.get("condition") == condition)

                time.sleep(args.render_wait_seconds)
                render_wait = args.render_wait_seconds
            stage = "round_execution"
            result, before, after = runner.run_once(condition, execute=args.execute,
                                                      question_id=round_id, public_guard=public_guard)
            result.update(model_loading_seconds=loading_seconds, device=args.device,
                          explicit_ui_render_wait_seconds=render_wait,
                          public_condition_source="public_room_state" if session else "operator_cli")
            if condition["task_type"] == "tree_count" and tree is not None:
                result["tree_model_loading_seconds_included_in_inference"] = tree.last_loading_seconds
            number = len(completed) + 1
            before.save(args.output / f"round-{number}-captured-grid.png")
            if after is not None:
                after.save(args.output / f"round-{number}-after-grid.png")
            with (args.output / f"round-{number}.json").open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            completed.append(result)
            print(json.dumps({"round": number, "selected_tiles": result["selected_tiles"],
                              "execute": args.execute, "submitted": result["submit_performed"]}), flush=True)
    except Exception as error:
        failure = error.report if isinstance(error, BoothRunError) else {
            "status": "aborted", "error_type": type(error).__name__, "stage": stage,
            "error": startup_message(stage, error),
            "completed_rounds": len(completed), "role_token_logged": False}
        with (args.output / "aborted.json").open("x", encoding="utf-8") as stream:
            json.dump(failure, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps({"status": "aborted", "error_type": type(error).__name__,
                          "stage": stage, "message": startup_message(stage, error),
                          "report": str(args.output / "aborted.json")}), flush=True)
        return 1
    finally:
        # A waiting process that exits must not leave a lobby advertising a
        # prepared local engine. This is best-effort, without logging tokens.
        if announced_ready and session and not completed:
            try:
                if session.view()["phase"] == "lobby":
                    session.set_ready(False)
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
