"""Run actual PC ML for two remote pad lanes; no browser/OS automation."""

import argparse
import getpass
import json
import math
from pathlib import Path
import re
import sys
import time

from alpha_captcha.remote_engine import (
    ControlledTransport, EngineController, EngineRoom, RemoteEngineError, SharedModels,
    controlled_origin, safe_diagnostic,
)


def load_models(args):
    from alpha_captcha.inference import TorchTilePredictor
    from alpha_captcha.tree_model import TreeCountPredictor
    predictor = TorchTilePredictor.from_checkpoints(args.presence, args.person, device=args.device)
    tree = TreeCountPredictor(args.tree_model_dir, device=args.device)
    return SharedModels(predictor, tree)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://bot.marulee.dev")
    parser.add_argument("--room-a", help="pairing code for lane A; prefer hidden interactive input")
    parser.add_argument("--room-b", help="pairing code for lane B; prefer hidden interactive input")
    parser.add_argument("--rooms-stdin", action="store_true", help="read one JSON line with A/B pairing codes from stdin; never echo/store it")
    parser.add_argument("--execute", action="store_true", help="join/heartbeat/select/submit actual remote rooms")
    parser.add_argument("--once", action="store_true", help="finish one round in each supplied room, then exit; default keeps room connections")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--presence", type=Path, default=Path("models/checkpoints/presence-limited-v1/presence.pt"))
    parser.add_argument("--person", type=Path, default=Path("models/checkpoints/person-limited-v1/person.pt"))
    parser.add_argument("--tree-model-dir", type=Path, default=Path("models/pretrained/grounding-dino-tiny"))
    parser.add_argument("--wait-seconds", type=float, default=1800, help="one-round safety limit; continuous lobby/result idle wait stays connected")
    parser.add_argument("--output", type=Path, required=True, help="new output directory; never stores pairing codes/tokens")
    args = parser.parse_args()
    try:
        controlled_origin(args.base_url)
    except ValueError:
        parser.error("bot.marulee.dev HTTPS 또는 localhost만 사용할 수 있습니다.")
    if not math.isfinite(args.wait_seconds) or args.wait_seconds <= 0:
        parser.error("대기 제한은 양의 유한한 초 단위 값이어야 합니다.")
    if args.output.exists():
        parser.error("기존 결과를 보존합니다. 새 --output 경로를 지정하세요.")
    if not args.execute:
        print("Dry-run: 원격 방 참가·준비·선택·제출 및 모델/GUI 실행을 하지 않았습니다. 실제 운영에는 --execute를 명시하세요.")
        return 0
    initial_rooms = {lane: code for lane, code in (("A", args.room_a), ("B", args.room_b)) if code}
    if args.rooms_stdin:
        if initial_rooms:
            parser.error("--rooms-stdin과 --room-a/--room-b를 함께 사용하지 마세요.")
        try:
            supplied = sys.stdin.readline(512)
            initial_rooms = json.loads(supplied)
            if not isinstance(initial_rooms, dict) or set(initial_rooms) - {"A", "B"}:
                raise ValueError
        except (ValueError, OSError):
            parser.error("stdin에는 A/B 연결 코드만 담긴 JSON 한 줄이 필요합니다.")
    if any(not isinstance(code, str) or not re.fullmatch(r"[A-Z2-9]{8}", code) for code in initial_rooms.values()):
        parser.error("초기 레인의 연결 코드 형식을 확인하세요.")
    if args.once and not initial_rooms:
        parser.error("--once에는 초기 A/B 방 연결 코드가 필요합니다.")
    args.output.mkdir(parents=True)
    print("PC에서 존재·사람·나무 모델을 한 번 불러옵니다. 인간 화면은 직접 입력하고 AI 표시 화면은 모델 선택을 보여 줍니다.", flush=True)
    started = time.monotonic()
    startup_stage = "model_loading"
    try:
        models = load_models(args)
        model_loading_seconds = time.monotonic() - started
        startup_stage = "synthetic_warmup"
        warmup = models.warm_up() if isinstance(models, SharedModels) else None
    except Exception as error:
        report = {"status": "aborted", "stage": startup_stage, "error_type": type(error).__name__,
                  "model_loading_seconds": time.monotonic() - started, "credentials_logged": False}
        (args.output / "startup.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("모델 로드 또는 예열을 완료하지 못했습니다. 체크포인트·고정 나무 가중치·CUDA 환경을 확인하세요.", flush=True)
        return 1
    (args.output / "startup.json").write_text(json.dumps({
        "mode": "remote", "device": args.device, "models_loaded_once": True,
        "model_loading_seconds": model_loading_seconds, "synthetic_warmup": warmup,
        "startup_total_seconds": time.monotonic() - started, "gui_used": False,
        "credentials_logged": False, "model_or_threshold_tuning_performed": False,
        "selection_plan_preferred": True, "minimum_tile_interval_seconds": 0.25,
        "public_image_download_workers": 3, "image_readiness_barrier_supported": True,
        "server_protocol_negotiation": "2_for_v11_missing_capability_3_for_barrier_server"}, indent=2) + "\n", encoding="utf-8")
    print("모델 로드와 합성 이미지 예열을 마쳤습니다. 실제 문제는 공통 출발 후에만 판별합니다.", flush=True)
    transport = ControlledTransport(args.base_url)
    messages = {"ready": "모델 준비 완료 · AI 표시 화면 연결 후 인간 화면에서 시작하세요.",
                "waiting_gpu": "시작 요청을 받았습니다. 경기 타이머 밖에서 GPU 순서를 기다립니다.",
                "reserved": "GPU를 예약했습니다. 사진 준비와 서버 공통 출발을 기다립니다.",
                "loading_images": "경기 시작 전에 사진 9장을 내려받아 준비합니다. 타이머는 아직 시작하지 않습니다.",
                "images_ready": "PC 사진 준비 완료 · 인간/AI 표시 화면의 사진 준비와 공통 출발을 기다립니다.",
                "start_cancelled": "시작 대기가 취소 또는 만료됐습니다. 같은 인간 화면에서 다시 시작할 수 있습니다.",
                "inferencing": "공개 사진을 실제 모델로 판별합니다.",
                "selecting": "모델 선택을 서버에 전달합니다.",
                "scheduled": "서버가 모델 선택을0.25초 간격으로 표시하고 한 번 제출합니다.",
                "submitted": "고정 예측을 제출했습니다. 재추론 없이 경기 종료를 기다립니다.",
                "countdown": "같은 방의 새 경기가 시작됩니다. 공통 시작 시각을 기다립니다.",
                "ended": "경기 기록을 저장했습니다. 연결을 유지합니다. 인간 화면에서 다음 참가자 준비를 누르세요.",
                "waiting_next": "같은 방 연결 유지 중 · 인간 화면의 다음 참가자 준비를 기다립니다.",
                "stopping": "이 레인의 새 추론/입력을 중단합니다. 서버가 이미 수락한 선택 계획은 완료되며 인간은 계속할 수 있습니다. 같은 토큰 재참가는 지원하지 않아 다른 방 연결용으로만 사용하세요.",
                "aborted": "실행을 마쳤거나 중단했습니다. 해당 레인의 보고서를 확인하세요."}
    controller = EngineController(models, lambda lane, code: EngineRoom(transport, lane, code), args.output,
                                  wait_seconds=args.wait_seconds,
                                  continuous=not args.once,
                                  progress=lambda lane, stage: print(f"[{lane}] {messages.get(stage, '상태 변경')}", flush=True),
                                  diagnostic=lambda lane, code: print(f"[{lane}] {safe_diagnostic(code)}", flush=True))
    result = 0
    try:
        for lane, code in initial_rooms.items():
            if code:
                controller.add(lane, code.strip().upper())
        if args.once:
            controller.wait()
            result = 0 if all(report.get("status") == "game_ended" for report in controller.reports) else 1
        else:
            print("최초 한 번 A CODE8 또는 B CODE8을 입력하세요. 이후 같은 방에서 다음 참가자 준비를 누르면 자동 대기/진행합니다. 코드는 화면/로그에 출력하지 않습니다.", flush=True)
            print("연결을 바꿀 때만 stop A 또는 stop B를 사용하세요. 이미 서버가 수락한 선택 계획은 완료됩니다. 전체 종료는 quit입니다.", flush=True)
            while True:
                line = getpass.getpass("레인과 새 연결 코드 (입력 숨김)> ").strip()
                if line.lower() in {"quit", "exit", "q"}:
                    break
                parts = line.split()
                if len(parts) != 2:
                    print("A 또는 B, 공백, 새8자리코드 형식으로 입력하세요.", flush=True)
                    continue
                try:
                    if parts[0].lower() == "stop":
                        controller.stop(parts[1].upper())
                    else:
                        controller.add(parts[0].upper(), parts[1].upper())
                except RemoteEngineError as error:
                    print(safe_diagnostic(error.code), flush=True)
                except ValueError:
                    print("레인과8자리코드 형식을 확인하세요.", flush=True)
    except KeyboardInterrupt:
        print("엔진 종료를 요청했습니다. 남은 원격 입력을 취소합니다.", flush=True)
    except Exception as error:
        print(safe_diagnostic(error.code if isinstance(error, RemoteEngineError) else "request_failed"), flush=True)
        result = 1
    finally:
        controller.close()
        close_transport = getattr(transport, "close", None)
        if close_transport is not None:
            close_transport()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
