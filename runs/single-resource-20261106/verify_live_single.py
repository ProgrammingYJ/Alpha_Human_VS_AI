"""One public single-mode room with production ML and a 30% cooperative budget.

--execute creates only a fresh QA room and one fixed ML selection plan. Human
and AI displays are HTTP/PIL stand-ins. No answer, admin, GUI or OS input.
Room codes, tokens, IDs and image URLs stay in RAM and are never reported.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
ORIGINS = {"human": "https://human.marulee.dev", "bot": "https://bot.marulee.dev"}
PHOTO_PATH = re.compile(r"/api/photos/[a-fA-F0-9-]{36}\Z")
FORBIDDEN = {"answer", "answers", "answer_json", "answerTileIds", "answerCount", "metadata", "photoId",
             "personCount", "treeCount", "treeAtLeast3", "groupId", "objectKey", "engine_token_hash",
             "human_token_hash", "bot_token_hash"}

class QAFailure(RuntimeError):
    """Only bounded local messages, never transport bodies or credentials."""

    def __init__(self, code, *, status=None):
        self.status = status
        super().__init__(code)

def operator_count():
    query = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*Alpha-Captcha-AI*run_remote_engine.py*' }).Count"
    return int(subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", query], text=True).strip())

def no_truth(value):
    if isinstance(value, list):
        for item in value: no_truth(item)
    elif isinstance(value, dict):
        if FORBIDDEN.intersection(value): raise QAFailure("private_field_in_public_response")
        for item in value.values(): no_truth(item)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.execute:
        print("Dry-run: no CUDA, models, HTTP, rooms, selection, submission or process changes.")
        return 0
    if Path.cwd().resolve() != ROOT: parser.error("run from the original project root")
    if args.output.exists(): parser.error("preserve existing reports; choose a new output directory")
    if operator_count(): parser.error("operator engine active; no live QA performed")

    from PIL import Image
    from alpha_captcha.inference import TorchTilePredictor
    from alpha_captcha.tree_model import TreeCountPredictor
    from alpha_captcha.remote_engine import ControlledTransport, EngineController, EngineRoom, NoRedirect, SharedModels

    args.output.mkdir(parents=True)
    started = time.perf_counter()
    summary = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
               "operator_engine_process_count_before": 0, "qa_rounds_requested": 1,
               "operator_rooms_accessed": False, "display_roles_are_HTTP_PIL_standins": True,
               "physical_browsers_used": 0, "OS_input_used": False, "answer_or_admin_access": False,
               "training_or_threshold_changes": False, "credentials_recorded": False,
               "accuracy_estimate": None, "hardware_GPU_quota_claim": False,
               "limits": "One random QA round; cooperative model-call work fraction is not GPU SM utilization, memory quota, external-PC rendering or CTF co-load validation."}
    events, event_lock = [], threading.Lock()
    controller, transport = None, None

    def request(role, path, *, token=None, body=None, pixels=False, expected_status=200):
        if pixels and not PHOTO_PATH.fullmatch(path): raise QAFailure("unsafe_public_image_path")
        headers = {"User-Agent": "AlphaCaptchaSingleResourceQA/1.0"}
        if token: headers["Authorization"] = "Bearer " + token
        if body is not None: headers["Content-Type"] = "application/json"
        route = "photo" if pixels else next((name for name in ("health", "join", "images-ready", "start") if path.endswith("/" + name)),
                                              "create" if path == "/api/rooms" else "state")
        sent, status = time.perf_counter(), None
        try:
            req = Request(ORIGINS[role] + path, headers=headers,
                          data=None if body is None else json.dumps(body).encode("utf-8"))
            try:
                response = build_opener(NoRedirect()).open(req, timeout=15)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                limit = 8 * 1024 * 1024 if pixels else 262144
                raw = response.read(limit + 1)
                if len(raw) > limit: raise QAFailure("oversized_QA_response")
                allowed = expected_status if isinstance(expected_status, tuple) else (expected_status,)
                if status not in allowed: raise QAFailure("unexpected_QA_HTTP_status", status=status)
                if pixels:
                    with Image.open(BytesIO(raw)) as source:
                        source.load()
                        if min(source.size) < 3: raise QAFailure("invalid_QA_pixels")
                        rgb = Image.new("RGB", source.size); rgb.paste(source.convert("RGB")); return rgb
                value = json.loads(raw)
                no_truth(value)
                return value
        finally:
            with event_lock:
                events.append({"role": role, "route": route, "method": "GET" if body is None else "POST",
                               "status": status, "sent_relative_seconds": sent - started,
                               "duration_seconds": time.perf_counter() - sent})

    def read(role, pair):
        for attempt in range(3):
            try: return request(role, pair["path"], token=pair[role])
            except (URLError, TimeoutError):
                if attempt == 2: raise
                time.sleep(.2 * (attempt + 1))
            except QAFailure as failure:
                if attempt == 2 or failure.status not in {429, 500, 502, 503, 504}: raise
                time.sleep(.2 * (attempt + 1))

    def decode(role, pair, state, pool):
        paths = tuple(tile["url"] for tile in state["preloadTiles"])
        if len(paths) != 9 or len(set(paths)) != 9: raise QAFailure("not_nine_independent_public_images")
        futures = [pool.submit(request, role, path, pixels=True) for path in paths]
        decoded, began = 0, time.perf_counter()
        try:
            for future in futures:
                image = future.result(timeout=45)
                try:
                    if image.mode != "RGB" or image.info: raise QAFailure("non_RGB_QA_pixels")
                    decoded += 1
                finally: image.close()
        finally:
            for future in futures:
                try: future.result(timeout=45).close()
                except Exception: pass
        return {"decoded": decoded, "download_decode_seconds": time.perf_counter() - began}

    try:
        health = {role: request(role, "/api/health") for role in ("human", "bot")}
        summary["single_health_on_both_hosts"] = all(h.get("ok") is True and h.get("operationMode") == "single"
            and h.get("protocolVersion") == 3 and h.get("imageReadinessBarrier") is True and h.get("minimumTileIntervalMs") == 250
            for h in health.values())
        if not summary["single_health_on_both_hosts"]: raise QAFailure("production_not_single_protocol3")
        rejected = request("human", "/api/rooms", body={"mode": "remote", "lane": "B"}, expected_status=409)
        summary["B_creation_rejected"] = rejected.get("code") == "lane_disabled"
        if not summary["B_creation_rejected"]: raise QAFailure("B_create_not_disabled")

        spec = importlib.util.spec_from_file_location("alpha_single_qa_operator", ROOT / "scripts/run_remote_engine.py")
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        runtime = SimpleNamespace(cpu_threads=4)
        cli.configure_runtime(runtime)
        summary["runtime_cpu_settings"] = runtime.runtime_cpu_settings
        loaded = time.perf_counter()
        models = SharedModels(TorchTilePredictor.from_checkpoints(
            ROOT / "models/checkpoints/presence-limited-v1/presence.pt",
            ROOT / "models/checkpoints/person-limited-v1/person.pt", device="cuda"),
            TreeCountPredictor(ROOT / "models/pretrained/grounding-dino-tiny", device="cuda"),
            execution_mode="single", gpu_duty_cycle=.3)
        summary.update(model_load_seconds=time.perf_counter() - loaded,
                       execution_metadata=models.execution_metadata(), synthetic_warmup=models.warm_up())
        transport = ControlledTransport(ORIGINS["bot"])
        controller = EngineController(models, lambda lane, code: EngineRoom(transport, lane, code), args.output,
                                      wait_seconds=170, continuous=False,
                                      progress=lambda lane, stage: print("QA: " + stage, flush=True))
        created = request("human", "/api/rooms", body={"mode": "remote"}, expected_status=201)
        if created["state"].get("operationMode") != "single" or created["state"]["remote"]["lane"] != "A":
            raise QAFailure("single_room_did_not_default_to_internal_A")
        for role in ("bot", "engine"):
            denied = request("bot", "/api/rooms/join", body={"role": role, "lane": "B", "code": created["code"]}, expected_status=409)
            if denied.get("code") != "lane_disabled": raise QAFailure("B_join_not_disabled")
        summary["B_viewer_and_engine_join_rejected"] = True
        viewer = request("bot", "/api/rooms/join", body={"role": "bot", "code": created["code"]})
        pair = {"path": "/api/rooms/" + created["roomId"], "human": created["token"], "bot": viewer["token"]}
        controller.add("A", created["code"])
        limit = time.perf_counter() + 35
        while True:
            current = read("human", pair)
            if current["bot"]["ready"] and current["remote"].get("imageBarrierSupported"): break
            if time.perf_counter() >= limit: raise QAFailure("engine_not_ready")
            time.sleep(.15)
        for _ in range(3):
            result = request("human", pair["path"] + "/start", token=pair["human"],
                             body={"expectedRevision": current["revision"]}, expected_status=(200, 409))
            if "state" in result:
                start = result["state"]
                break
            current = read("human", pair)
            if current["phase"] in {"queued", "loading"}:
                start = current
                break
            if current["phase"] != "lobby": raise QAFailure("start_race_unrecoverable")
        else: raise QAFailure("start_revision_race")
        summary["start_without_timer_or_question"] = start["phase"] == "queued" and start["startAt"] is None and start["topic"] is None and start["tiles"] == []
        limit = time.perf_counter() + 35
        while True:
            human = read("human", pair)
            if human["phase"] == "loading": break
            if time.perf_counter() >= limit: raise QAFailure("loading_not_observed")
            time.sleep(.1)
        viewer_state = read("bot", pair)
        loading_hidden = all(s["phase"] == "loading" and s["startAt"] is None and s["deadlineAt"] is None
                             and s["topic"] is None and s["tiles"] == [] for s in (human, viewer_state))
        if human["roundId"] != viewer_state["roundId"] or human["preloadTiles"] != viewer_state["preloadTiles"]:
            raise QAFailure("role_preload_mismatch")
        with ThreadPoolExecutor(max_workers=3) as pool:
            decoded = {role: decode(role, pair, human if role == "human" else viewer_state, pool) for role in ("human", "bot")}
        expected_round, paths = human["roundId"], tuple(tile["url"] for tile in human["preloadTiles"])
        for role in ("human", "bot"):
            state = read("human", pair)
            if state["roundId"] != expected_round or tuple(tile["url"] for tile in state["preloadTiles"]) != paths:
                raise QAFailure("round_or_preload_changed")
            request(role, pair["path"] + "/images-ready", token=pair[role], body={"ready": True,
                    "roundId": expected_round, "requestId": state["startRequest"]["id"], "imageLoadId": state["imageLoad"]["id"]})
        observations, final, readiness = [], None, True
        limit = time.perf_counter() + 115
        while final is None:
            state = read("bot", pair)
            if state["roundId"] != expected_round: raise QAFailure("round_changed")
            if state["phase"] in {"countdown", "playing"}:
                readiness &= all(state["imageLoad"].get(role + "Ready") is True for role in ("human", "bot", "engine"))
            item = {"phase": state["phase"], "indices": state["remote"]["selectedIndices"],
                    "sequence": state["remote"]["sequence"], "engine_connected": state["remote"]["engineConnected"]}
            if not observations or item != observations[-1]: observations.append(item)
            if state["phase"] == "result":
                human_final = read("human", pair)
                final = {"winner": state["result"]["winner"], "reason": state["result"]["reason"],
                         "same_role_start_at": human_final["startAt"] == state["startAt"],
                         "selected_indices": list(state["remote"]["selectedIndices"])}
                break
            if time.perf_counter() >= limit: raise QAFailure("round_timeout")
            time.sleep(.2)
        controller.wait()
        if len(controller.reports) != 1: raise QAFailure("not_one_QA_round")
        report = controller.reports[0]
        planned = report.get("planned_selection_events", [])
        fraction = report.get("resource_work_fraction_observed")
        checks = {
            "ended_normally": report.get("status") == "game_ended", "internal_A_only": report.get("lane") == "A",
            "single_slot": report.get("max_concurrent_inferences") == 1 and report.get("inference_mode") == "single",
            "one_model_prediction": report.get("model_predictions_per_game") == 1,
            "one_logical_submission": report.get("logical_submission_count") == 1,
            "server_submission_observed": report.get("server_submission_observed") is True,
            "scheduled_plan_used": report.get("selection_transport") == "scheduled_plan",
            "250ms_schedule": report.get("plan_interval_ms") == 250 and all(b["server_scheduled_at_ms"] - a["server_scheduled_at_ms"] == 250 for a, b in zip(planned, planned[1:])),
            "loading_hidden": loading_hidden, "all_three_ready_before_start": readiness,
            "each_display_decoded_nine": all(row["decoded"] == 9 for row in decoded.values()),
            "cached_RGB_reused": report.get("image_cache_reused") is True,
            "no_in_game_image_download": report.get("public_image_download_during_game_seconds") == 0,
            "no_prestart_inference": report.get("prestart_inference_count") == 0 and report.get("model_call_started_monotonic_seconds", -1) >= report.get("playing_observed_monotonic_seconds", 1e300),
            "released_before_plan": report.get("gpu_reservation_released_seconds", 1e300) <= report.get("plan_upload_sent_seconds", -1),
            "viewer_matches_model": final["selected_indices"] == report.get("selected_indices"),
            "same_role_start": final["same_role_start_at"],
            "cooperative_target_30_percent": report.get("target_gpu_duty_cycle") == .3,
            "observed_work_fraction_at_most_30_percent": isinstance(fraction, (int, float)) and math.isfinite(fraction) and 0 <= fraction <= .300001,
            "measured_throttle": report.get("resource_throttle_seconds", 0) > 0 and report.get("inference_chunk_count", 0) >= 1,
            "hardware_quota_not_claimed": report.get("hardware_gpu_quota_enforced") is False,
        }
        summary.update(checks=checks, decoded_displays=decoded, observations=observations, final=final,
                       model_budget_metrics={key: report.get(key) for key in ("inference_work_seconds", "resource_throttle_seconds", "resource_work_fraction_observed", "inference_chunk_count", "target_gpu_duty_cycle")})
        summary["passed"] = all(checks.values()) and summary["start_without_timer_or_question"]
    except Exception as error:
        summary.update(passed=False, error_type=type(error).__name__)
        if isinstance(error, QAFailure):
            summary["error_code"] = str(error)
            if error.status is not None: summary["HTTP_status"] = error.status
    finally:
        if controller is not None: controller.close()
        if transport is not None: transport.close()
        summary.update(total_seconds=time.perf_counter() - started, requests=events)
        (args.output / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key not in {"requests", "observations"}}, ensure_ascii=False), flush=True)
    return 0 if summary["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
