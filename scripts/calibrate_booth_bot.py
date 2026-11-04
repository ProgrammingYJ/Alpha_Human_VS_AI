"""User-operated Windows calibration. Importing this file never touches the GUI.

Run this yourself with the owned ALPHA bot page visible. The utility reads five
mouse positions when YOU press F8; it never captures a screen, clicks or types.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

from alpha_captcha.booth_bot import BoothLayout
from alpha_captcha.timing import MIN_TILE_INTERVAL_SECONDS


EXPECTED_TITLE = "ALPHA BOT | CAPTCHA"
POINT_NAMES = (
    "grid_top_left", "grid_bottom_right", "submit", "guard_top_left", "guard_bottom_right",
)
POINT_INSTRUCTIONS = (
    "격자 전체의 왼쪽 위 바깥 모서리",
    "격자 전체의 오른쪽 아래 바깥 모서리",
    "'정답 제출' 버튼의 중앙",
    "변하지 않는 질문 제목/설명 영역의 왼쪽 위",
    "같은 질문 영역의 오른쪽 아래 (타이머/선택 수/진행 표시 제외)",
)


def _pair(value, name):
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(type(number) is not int for number in value)):
        raise ValueError(f"{name}: 두 개의 정수 물리 좌표가 필요합니다.")
    return tuple(value)


def build_layout(points, screen_size, *, gap_x=8, gap_y=8):
    """Validate manually measured physical geometry; performs no GUI access."""
    width, height = _pair(screen_size, "screen_size")
    if min(width, height) <= 0:
        raise ValueError("주 모니터의 실제 화면 크기를 확인하세요.")
    if not isinstance(points, dict) or set(points) != set(POINT_NAMES):
        raise ValueError("F8로 측정한 다섯 점이 모두 필요합니다.")
    if any(type(gap) is not int or not 0 <= gap <= 100 for gap in (gap_x, gap_y)):
        raise ValueError("타일 간격은 0~100 범위의 정수 물리 픽셀이어야 합니다.")
    measured = {name: _pair(points[name], name) for name in POINT_NAMES}
    for name, (x, y) in measured.items():
        right_or_bottom = name.endswith("bottom_right")
        if x < 0 or y < 0 or x > width or y > height:
            raise ValueError(f"{name}: 주 모니터 밖의 좌표는 지원하지 않습니다.")
        if not right_or_bottom and (x == width or y == height):
            raise ValueError(f"{name}: 화면 경계 바깥 점입니다.")
    left, top = measured["grid_top_left"]
    right, bottom = measured["grid_bottom_right"]
    grid_width, grid_height = right - left, bottom - top
    if min(grid_width, grid_height) < 240:
        raise ValueError("3×3 전체 격자가 너무 작거나 모서리 순서가 잘못됐습니다.")
    if abs(grid_width - grid_height) > max(grid_width, grid_height) * 0.03:
        raise ValueError("봇 격자는 정사각형입니다. 전체 격자 두 모서리를 다시 측정하세요.")
    if min((grid_width - 2 * gap_x) / 3, (grid_height - 2 * gap_y) / 3) < 64:
        raise ValueError("타일 간격을 제외한 사진이 너무 작습니다.")
    submit_x, submit_y = measured["submit"]
    if not left <= submit_x < right or not bottom <= submit_y < height:
        raise ValueError("제출 버튼 중앙은 격자 아래쪽의 보이는 화면 안에 있어야 합니다.")
    guard_left, guard_top = measured["guard_top_left"]
    guard_right, guard_bottom = measured["guard_bottom_right"]
    if guard_right - guard_left < 120 or guard_bottom - guard_top < 24:
        raise ValueError("질문 보호 영역이 너무 작거나 모서리 순서가 잘못됐습니다.")
    if not (left <= guard_left < guard_right <= right and guard_bottom <= top):
        raise ValueError("질문 보호 영역은 격자 위쪽에 있어야 하며 타이머를 포함하면 안 됩니다.")
    result = {
        "url": "https://bot.marulee.dev/", "expected_window_title": EXPECTED_TITLE,
        "calibrated": True,
        "grid": {"left": left, "top": top, "width": grid_width, "height": grid_height,
                 "rows": 3, "columns": 3, "gap_x": gap_x, "gap_y": gap_y},
        "submit": {"x": submit_x, "y": submit_y},
        "question_guard": {"left": guard_left, "top": guard_top,
                           "width": guard_right - guard_left, "height": guard_bottom - guard_top},
        "min_interval_seconds": MIN_TILE_INTERVAL_SECONDS, "first_click_delay_seconds": 0.0,
    }
    BoothLayout.from_dict(result)
    return result


def write_layout(output, layout, *, replace=False):
    """Write only a fully validated layout; preserve the previous file on replacement."""
    output = Path(output)
    if not isinstance(layout, dict) or layout.get("calibrated") is not True:
        raise ValueError("완료되지 않은 보정은 저장할 수 없습니다.")
    BoothLayout.from_dict(layout)
    if output.exists() and not replace:
        raise FileExistsError("기존 보정 파일이 있습니다. 새 --output 또는 명시적 --replace를 사용하세요.")
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_name(output.name + ".pending")
    backup = None
    created = False
    try:
        with pending.open("x", encoding="utf-8") as stream:
            created = True
            json.dump(layout, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if output.exists():
            if not replace:
                raise FileExistsError("측정 중 파일이 생성되어 저장을 중단했습니다.")
            backup = output.with_name(f"{output.stem}.backup-{time.time_ns()}.local.json")
            shutil.copy2(output, backup)
        pending.replace(output)
    finally:
        if created and pending.exists():
            pending.unlink()
    return backup


class WindowsPointerRecorder:
    """Created only by a human-invoked main(); provides observation, never input."""

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("이 보정 도구는 Windows PC 전용입니다. Pi 보정은 별도 검증이 필요합니다.")
        import ctypes
        self.user32 = ctypes.windll.user32
        try:
            set_awareness = self.user32.SetProcessDpiAwarenessContext
            set_awareness.argtypes = [ctypes.c_void_p]
            set_awareness.restype = ctypes.c_bool
            changed = set_awareness(ctypes.c_void_p(-4))
            get_context = self.user32.GetThreadDpiAwarenessContext
            get_context.restype = ctypes.c_void_p
            get_awareness = self.user32.GetAwarenessFromDpiAwarenessContext
            get_awareness.argtypes = [ctypes.c_void_p]
            get_awareness.restype = ctypes.c_int
            if not changed and get_awareness(get_context()) != 2:
                raise RuntimeError("물리 픽셀 측정을 위한 모니터별 DPI 인식을 설정하지 못했습니다.")
        except (AttributeError, OSError) as error:
            raise RuntimeError("이 Windows 환경에서 물리 픽셀 보정을 확인할 수 없습니다.") from error
        # Lazy import avoids even position/title queries during module import/help/tests.
        import pyautogui
        self.gui = pyautogui

    def down(self, key):
        return bool(self.user32.GetAsyncKeyState({"F8": 0x77, "ESC": 0x1B}[key]) & 0x8000)

    def position(self):
        return tuple(self.gui.position())

    def screen_size(self):
        return tuple(self.gui.size())

    def title(self):
        return self.gui.getActiveWindowTitle() or ""


def collect_points(recorder, *, clock=time.monotonic, sleep=time.sleep, notify=print, timeout_seconds=300):
    """Observe user F8 presses. Esc/timeout leaves writing to the caller unstarted."""
    points = {}
    for index, (name, instruction) in enumerate(zip(POINT_NAMES, POINT_INSTRUCTIONS), 1):
        notify(f"{index}/5: {instruction}에 마우스를 대고 F8을 한 번 누르세요.")
        deadline = clock() + timeout_seconds
        while recorder.down("F8"):
            if recorder.down("ESC"):
                raise KeyboardInterrupt
            if clock() >= deadline:
                raise TimeoutError("F8 키 해제를 기다리다가 보정을 중단했습니다.")
            sleep(0.03)
        while True:
            if recorder.down("ESC"):
                raise KeyboardInterrupt
            if clock() >= deadline:
                raise TimeoutError("5분 동안 F8 입력이 없어 보정을 중단했습니다.")
            if recorder.down("F8"):
                if EXPECTED_TITLE not in recorder.title():
                    notify("봇 페이지가 전면이 아닙니다. bot.marulee.dev 화면을 앞으로 옮기고 다시 F8을 누르세요.")
                    while recorder.down("F8"):
                        if recorder.down("ESC"):
                            raise KeyboardInterrupt
                        if clock() >= deadline:
                            raise TimeoutError("봇 창 확인을 기다리다가 보정을 중단했습니다.")
                        sleep(0.03)
                    continue
                points[name] = _pair(recorder.position(), name)
                notify(f"기록: {index}/5")
                break
            sleep(0.03)
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("configs/booth-bot.local.json"))
    parser.add_argument("--replace", action="store_true", help="back up an existing layout before replacement")
    parser.add_argument("--gap-x", type=int, default=8, help="measured horizontal gap in physical pixels")
    parser.add_argument("--gap-y", type=int, default=8, help="measured vertical gap in physical pixels")
    args = parser.parse_args()
    if args.output.exists() and not args.replace:
        parser.error("기존 보정 파일은 보존합니다. 새 --output 또는 --replace를 명시하세요.")
    if args.output.with_name(args.output.name + ".pending").exists():
        parser.error("이전 pending 파일이 있어 중단합니다. 원인을 확인하고 새 출력 경로를 쓰세요.")
    print("사용자가 직접 진행하는 화면 좌표 보정입니다. 자동 클릭·키 입력·화면 캡처는 하지 않습니다.")
    print("주 모니터의 bot.marulee.dev를 열고 F11 전체화면을 직접 켜세요. 제출 버튼까지 모두 보여야 합니다.")
    print("기본 타일 간격 8은 물리 픽셀입니다. OS 배율/Chrome 줌100% 기준이며 다르면 실제 --gap-x/--gap-y를 지정하세요.")
    print("질문 보호 영역에는 질문 제목/설명만 넣고, 타이머·라운드 진행·선택 개수·반짝이는 커서는 제외하세요.")
    print("아래 순서대로 봇 화면에 마우스를 대고 F8을 누르세요. 언제든 Esc로 취소하며 기존 파일은 보존됩니다.")
    for index, instruction in enumerate(POINT_INSTRUCTIONS, 1):
        print(f"  {index}. {instruction}")
    try:
        recorder = WindowsPointerRecorder()
        initial_size = recorder.screen_size()
        points = collect_points(recorder)
        if recorder.screen_size() != initial_size or EXPECTED_TITLE not in recorder.title():
            raise ValueError("보정 중 화면 크기나 전면 창이 바뀌었습니다. 파일을 저장하지 않습니다.")
        layout = build_layout(points, initial_size, gap_x=args.gap_x, gap_y=args.gap_y)
        backup = write_layout(args.output, layout, replace=args.replace)
    except KeyboardInterrupt:
        print("보정을 취소했습니다. 기존 설정은 변경하지 않았습니다.")
        return 130
    except Exception as error:
        print(f"보정 실패: {error}", file=sys.stderr)
        return 1
    print(f"보정 저장: {args.output}")
    if backup:
        print(f"기존 설정 백업: {backup}")
    print("이 결과는 사용자 위치 측정이며 실제 ML 클릭 성공 검증은 아닙니다. 창/배율/스크롤이 바뀌면 다시 보정하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
