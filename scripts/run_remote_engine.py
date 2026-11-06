"""Run one A-lane PC bot by default, with an explicit A/B recovery mode."""

import argparse
import getpass
import json
import math
import os
from pathlib import Path
import re
import sys
import time

from alpha_captcha.remote_engine import (
    ControlledTransport, EngineController, EngineRoom, RemoteEngineError, SharedModels,
    controlled_origin, safe_diagnostic,
)


def configure_runtime(args):
    """Limit only this process's CPU pools; leave other programs untouched."""
    os.environ["OMP_NUM_THREADS"] = str(args.cpu_threads)
    os.environ["MKL_NUM_THREADS"] = str(args.cpu_threads)
    priority = {"requested": "below_normal", "applied": False}
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            kernel.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.SetPriorityClass.restype = wintypes.BOOL
            kernel.GetPriorityClass.argtypes = [wintypes.HANDLE]
            kernel.GetPriorityClass.restype = wintypes.DWORD
            process = kernel.GetCurrentProcess()
            priority["applied"] = bool(kernel.SetPriorityClass(process, 0x4000))
            priority["actual_windows_priority_class"] = int(kernel.GetPriorityClass(process))
        except (OSError, AttributeError):
            priority["applied"] = False
    import torch
    torch.set_num_threads(args.cpu_threads)
    torch.set_num_interop_threads(1)
    args.runtime_cpu_settings = {"intraop_threads": torch.get_num_threads(),
                                 "interop_threads": torch.get_num_interop_threads(),
                                 "process_priority": priority,
                                 "other_processes_modified": False}


def load_models(args):
    configure_runtime(args)
    from alpha_captcha.inference import TorchTilePredictor
    from alpha_captcha.tree_model import TreeCountPredictor
    predictor = TorchTilePredictor.from_checkpoints(args.presence, args.person, device=args.device)
    tree = TreeCountPredictor(args.tree_model_dir, device=args.device)
    return SharedModels(predictor, tree, execution_mode=args.inference_mode,
                        gpu_duty_cycle=args.gpu_duty_cycle)


def interactive_command(line, *, single):
    """Parse hidden input without returning unvalidated lanes to the controller."""
    parts = line.split()
    if single and len(parts) == 1:
        if parts[0].lower() == "stop":
            return "stop", "A", None
        if re.fullmatch(r"[A-Z2-9]{8}", parts[0].upper()):
            return "add", "A", parts[0].upper()
    if len(parts) != 2:
        raise ValueError("invalid_operator_command")
    action = "stop" if parts[0].lower() == "stop" else "add"
    lane = parts[1].upper() if action == "stop" else parts[0].upper()
    if lane not in {"A", "B"} or single and lane != "A":
        raise ValueError("disabled_operator_lane")
    code = None if action == "stop" else parts[1].upper()
    if code is not None and not re.fullmatch(r"[A-Z2-9]{8}", code):
        raise ValueError("invalid_pairing_code")
    return action, lane, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://bot.marulee.dev")
    parser.add_argument("--room-a", help="pairing code for lane A; prefer hidden interactive input")
    parser.add_argument("--room-b", help="pairing code for lane B; prefer hidden interactive input")
    parser.add_argument("--rooms-stdin", action="store_true", help="read one JSON line with A/B pairing codes from stdin; never echo/store it")
    parser.add_argument("--execute", action="store_true", help="join/heartbeat/select/submit actual remote rooms")
    parser.add_argument("--once", action="store_true", help="finish one round in each supplied room, then exit; default keeps room connections")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--inference-mode", choices=["single", "parallel", "serial"], default="single",
                        help="single (default): lane A only, one worker; parallel: two A/B workers; serial: A/B FIFO")
    parser.add_argument("--gpu-duty-cycle", type=float, default=0.30,
                        help="cooperative GPU execution-time budget in (0,1], default 0.30; not an instantaneous utilization, SM or VRAM quota")
    parser.add_argument("--cpu-threads", type=int, default=4,
                        help="this process's PyTorch/OMP/MKL thread count, 1..64 (default 4); inter-op uses one thread")
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
    if not math.isfinite(args.gpu_duty_cycle) or not 0 < args.gpu_duty_cycle <= 1:
        parser.error("GPU 시간 예산은 0보다 크고 1 이하인 유한한 비율이어야 합니다.")
    if args.inference_mode == "parallel" and args.gpu_duty_cycle < 1:
        parser.error("A/B 병렬 복구에는 --gpu-duty-cycle 1을 명시하세요. 30% 시간 예산은 단일 작업에서 사용합니다.")
    if not 1 <= args.cpu_threads <= 64:
        parser.error("CPU 스레드 수는 1~64 사이의 정수여야 합니다.")
    single = args.inference_mode == "single"
    enabled_lanes = {"A"} if single else {"A", "B"}
    if single and args.room_b is not None:
        parser.error("A 단일 운영에서는 --room-b를 사용할 수 없습니다. A의 새 연결 코드만 입력하세요.")
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
    if set(initial_rooms) - enabled_lanes:
        parser.error("A 단일 운영에서는 B를 연결할 수 없습니다. A의 새 연결 코드만 입력하세요.")
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
        "requested_inference_mode": args.inference_mode,
        "enabled_lanes": sorted(enabled_lanes),
        "resource_budget": {"gpu_duty_cycle_requested": args.gpu_duty_cycle,
                            "gpu_limit_kind": "cooperative_execution_time_budget",
                            "instantaneous_gpu_quota_claimed": False,
                            "vram_quota_claimed": False,
                            "cpu_threads_requested": args.cpu_threads,
                            "cpu_runtime": getattr(args, "runtime_cpu_settings", None)},
        **(models.execution_metadata() if isinstance(models, SharedModels) else {}),
        "model_loading_seconds": model_loading_seconds, "synthetic_warmup": warmup,
        "startup_total_seconds": time.monotonic() - started, "gui_used": False,
        "credentials_logged": False, "model_or_threshold_tuning_performed": False,
        "selection_plan_preferred": True, "minimum_tile_interval_seconds": 0.25,
        "public_image_download_workers": 3, "image_readiness_barrier_supported": True,
        "server_protocol_negotiation": "2_for_v11_missing_capability_3_for_barrier_server"}, indent=2) + "\n", encoding="utf-8")
    print("모델 로드와 합성 이미지 예열을 마쳤습니다. 실제 문제는 공통 출발 후에만 판별합니다.", flush=True)
    print(f"운영: {'A 단일 구역' if single else 'A/B 구역'} · GPU 협력적 실행시간 예산 {args.gpu_duty_cycle:.0%} · "
          "순간 사용률/SM/VRAM 고정 할당이 아닙니다.", flush=True)
    if isinstance(models, SharedModels):
        execution = models.execution_metadata()
        print(f"추론 모드: {execution['inference_mode']} · 동시 작업 {execution['max_concurrent_inferences']}개 · "
              f"CUDA 스트림 {execution['cuda_stream_count']}개 · 모델 가중치 한 세트 공유", flush=True)
    transport = ControlledTransport(args.base_url)
    messages = {"ready": "모델 준비 완료 · AI 표시 화면 연결 후 인간 화면에서 시작하세요.",
                "waiting_gpu": "시작 요청을 받았습니다. 경기 타이머 밖에서 추론 작업 슬롯을 준비합니다.",
                "reserved": "이 레인의 추론 슬롯을 예약했습니다. 사진 준비와 서버 공통 출발을 기다립니다.",
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
            print("최초 한 번 새8자리코드만 입력하세요. A CODE8도 사용할 수 있습니다. B 연결은 비활성화했습니다." if single else
                  "최초 한 번 A CODE8 또는 B CODE8을 입력하세요.", flush=True)
            print("이후 같은 방에서 다음 참가자 준비를 누르면 자동 대기/진행합니다. 코드는 화면/로그에 출력하지 않습니다.", flush=True)
            print("연결을 바꿀 때만 stop을 사용하세요. 이미 수락한 서버 선택 계획은 완료됩니다. 전체 종료는 quit입니다." if single else
                  "연결을 바꿀 때만 stop A 또는 stop B를 사용하세요. 이미 서버가 수락한 선택 계획은 완료됩니다. 전체 종료는 quit입니다.", flush=True)
            while True:
                line = getpass.getpass("새 연결 코드 (입력 숨김)> " if single else "레인과 새 연결 코드 (입력 숨김)> ").strip()
                if line.lower() in {"quit", "exit", "q"}:
                    break
                try:
                    action, lane, code = interactive_command(line, single=single)
                    if action == "stop":
                        controller.stop(lane)
                    else:
                        controller.add(lane, code)
                except RemoteEngineError as error:
                    print(safe_diagnostic(error.code), flush=True)
                except ValueError:
                    print("A 단일 운영입니다. 새8자리코드 또는 A CODE8을 입력하세요. B는 연결할 수 없습니다." if single else
                          "레인과8자리코드 형식을 확인하세요.", flush=True)
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
