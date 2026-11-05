"""Two fresh public protocol3 rooms, actual CUDA ML, HTTP/PIL display stand-ins.

Creates QA rooms and submits fixed model plans only with --execute. No browser,
OS input, admin data, answer labels or pairing credentials are written to disk.
The two display lanes must both reach loading before either downloads images;
the old single-slot FIFO cannot pass that gate.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import argparse
import json
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from verify_cuda import ROOT, operator_count


ORIGINS = {"human": "https://human.marulee.dev", "bot": "https://bot.marulee.dev"}
PHOTO_PATH = re.compile(r"/api/photos/[a-fA-F0-9-]{36}\Z")


class QAFailure(RuntimeError):
    """Only bounded local messages, never a URL or role capability."""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        print("Dry-run: no CUDA, model loading, HTTP, rooms, plans or process changes.")
        return 0
    if Path.cwd().resolve() != ROOT: parser.error("run from the original project root")
    if args.output.exists(): parser.error("preserve existing results; use a new output directory")
    if operator_count(): parser.error("operator engine is active; no QA was performed")

    from PIL import Image
    from alpha_captcha.inference import TorchTilePredictor
    from alpha_captcha.tree_model import TreeCountPredictor
    from alpha_captcha.remote_engine import ControlledTransport, EngineController, EngineRoom, NoRedirect, SharedModels

    args.output.mkdir(parents=True)
    started = time.perf_counter()
    summary = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
               "operator_engine_process_count_before": 0, "cuda_device_requested": True,
               "physical_browsers_used": 0, "human_and_viewer_are_HTTP_PIL_standins": True,
               "OS_input_used": False, "answer_or_admin_access": False,
               "training_or_threshold_changes": False, "credentials_recorded": False,
               "accuracy_estimate": None, "gpu_kernel_concurrency_claim_from_live_HTTP": False,
               "limits": "One random round per lane; HTTP/PIL decode does not measure browser rendering, external PCs, Wi-Fi or long-run stability."}
    request_events, event_lock = [], threading.Lock()
    controller, transport = None, None
    loading_gate = threading.Barrier(2)

    def request(role, path, *, token=None, body=None, pixels=False):
        headers = {"User-Agent": "AlphaCaptchaParallelQA/1.0"}
        if token is not None: headers["Authorization"] = "Bearer " + token
        if body is not None: headers["Content-Type"] = "application/json"
        if pixels and not PHOTO_PATH.fullmatch(path): raise QAFailure("unsafe_public_image_path")
        route = "photo" if pixels else next((name for name in ("join", "images-ready", "start") if path.endswith("/" + name)),
                                              "create" if path == "/api/rooms" else "state")
        sent, status = time.perf_counter(), None
        try:
            req = Request(ORIGINS[role] + path, headers=headers,
                          data=None if body is None else json.dumps(body).encode("utf-8"))
            with build_opener(NoRedirect()).open(req, timeout=15) as response:
                status = response.status
                raw = response.read(8 * 1024 * 1024 + 1 if pixels else 262145)
                if len(raw) > (8 * 1024 * 1024 if pixels else 262144): raise QAFailure("oversized_QA_response")
                if not pixels: return json.loads(raw)
                with Image.open(BytesIO(raw)) as source:
                    source.load()
                    if min(source.size) < 3: raise QAFailure("invalid_QA_pixels")
                    rgb = Image.new("RGB", source.size); rgb.paste(source.convert("RGB")); return rgb
        except HTTPError as error:
            status = error.code
            raise
        finally:
            with event_lock:
                request_events.append({"role": role, "route": route, "method": "GET" if body is None else "POST",
                                       "status": status, "sent_relative_seconds": sent - started,
                                       "duration_seconds": time.perf_counter() - sent})

    def get(role, pair):
        for attempt in range(3):
            try: return request(role, pair["path"], token=pair[role])
            except (HTTPError, URLError, TimeoutError) as error:
                if isinstance(error, HTTPError) and error.code < 500: raise
                if attempt == 2: raise
                time.sleep(.2 * (attempt + 1))

    def decode(role, pair, state, pool):
        paths = tuple(tile["url"] for tile in state["preloadTiles"])
        if len(paths) != 9 or len(set(paths)) != 9: raise QAFailure("not_nine_public_images")
        futures = [pool.submit(request, role, path, pixels=True) for path in paths]
        count, download_started = 0, time.perf_counter()
        try:
            for future in futures:
                image = future.result(timeout=45)
                try:
                    if image.mode != "RGB" or image.info: raise QAFailure("non_RGB_QA_input")
                    count += 1
                finally: image.close()
        finally:
            for future in futures:
                try: future.result(timeout=45).close()
                except Exception: pass
        return {"decoded": count, "download_decode_seconds": time.perf_counter() - download_started}

    def display_pair(lane, pair):
        limit = time.perf_counter() + 35
        while True:
            human = get("human", pair)
            if human["phase"] == "loading": break
            if human["phase"] in {"result", "expired"} or time.perf_counter() >= limit:
                raise QAFailure("both_lanes_did_not_reach_loading")
            time.sleep(.1)
        viewer = get("bot", pair)
        stopped = all(state["phase"] == "loading" and state["startAt"] is None
                      and state.get("deadlineAt") is None and state["topic"] is None and state["tiles"] == []
                      for state in (human, viewer))
        if not stopped: raise QAFailure("loading_exposed_timer_or_question")
        if human["roundId"] != viewer["roundId"] or human["preloadTiles"] != viewer["preloadTiles"]:
            raise QAFailure("roles_have_different_preload_images")
        entered = time.perf_counter()
        print(f"{lane}: loading gate", flush=True)
        loading_gate.wait(timeout=35)
        gate_passed = time.perf_counter()
        # Neither human/viewer role downloaded any photo before both lanes
        # passed loading. Engine RGB preloading is independently production code.
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="alpha-live-display-photo") as image_pool:
            decode_results = {role: decode(role, pair, human if role == "human" else viewer, image_pool)
                              for role in ("human", "bot")}
        paths = tuple(tile["url"] for tile in human["preloadTiles"])
        expected_round = human["roundId"]
        acked = set()
        limit = time.perf_counter() + 45
        while len(acked) < 2:
            current = get("human", pair)
            if current["roundId"] != expected_round: raise QAFailure("QA_round_changed_during_decode")
            if current["phase"] not in {"loading", "countdown"}: raise QAFailure("QA_departed_before_both_display_ACKs")
            if tuple(tile["url"] for tile in current["preloadTiles"]) != paths: raise QAFailure("QA_preloaded_order_changed")
            for role in ("human", "bot"):
                if role in acked: continue
                body = {"roundId": current["roundId"], "requestId": current["startRequest"]["id"],
                        "imageLoadId": current["imageLoad"]["id"], "ready": True}
                try:
                    request(role, pair["path"] + "/images-ready", token=pair[role], body=body)
                    acked.add(role)
                except HTTPError as error:
                    if error.code != 409: raise
                    break
            if time.perf_counter() >= limit: raise QAFailure("display_ACK_timeout")
        observations, final, common_start, ready_boundary = [], None, None, True
        limit = time.perf_counter() + 115
        while final is None:
            current = get("bot", pair)
            if current["roundId"] != expected_round: raise QAFailure("QA_round_changed")
            phase, remote = current["phase"], current["remote"]
            if phase in {"countdown", "playing"}:
                ready_boundary &= all(current["imageLoad"].get(name + "Ready") is True for name in ("human", "bot", "engine"))
                common_start = current["startAt"]
            item = {"relative_seconds": time.perf_counter() - started, "phase": phase,
                    "indices": list(remote["selectedIndices"]), "sequence": remote["sequence"],
                    "engine_stage": remote["engineStage"], "engine_connected": remote["engineConnected"]}
            if not observations or any(item[key] != observations[-1][key] for key in item if key != "relative_seconds"):
                observations.append(item)
            if phase == "result":
                final = {"reason": current["result"]["reason"], "winner": current["result"]["winner"],
                         "selected_indices": list(remote["selectedIndices"]),
                         "bot_attempted": current["bot"].get("submitted") is True
                         or type(current["bot"].get("elapsedMs")) is int}
                human_final = get("human", pair)
                if human_final["startAt"] != current["startAt"]: raise QAFailure("role_start_times_differ")
                common_start = current["startAt"]
                break
            if time.perf_counter() >= limit: raise QAFailure("public_QA_round_timeout")
            time.sleep(.15)
        return {"both_roles_loading_before_download": stopped, "both_lanes_loading_gate_passed": True,
                "loading_gate_entered_seconds": entered - started, "loading_gate_passed_seconds": gate_passed - started,
                "decoded_roles": decode_results, "all_three_ready_before_countdown": ready_boundary,
                "common_start_at_ms": common_start, "observations": observations, "final": final}

    try:
        loaded = time.perf_counter()
        models = SharedModels(TorchTilePredictor.from_checkpoints(
            ROOT / "models/checkpoints/presence-limited-v1/presence.pt",
            ROOT / "models/checkpoints/person-limited-v1/person.pt", device="cuda"),
            TreeCountPredictor(ROOT / "models/pretrained/grounding-dino-tiny", device="cuda"))
        summary.update(models_loaded_once_seconds=time.perf_counter() - loaded,
                       execution_metadata=models.execution_metadata(), synthetic_warmup=models.warm_up())
        transport = ControlledTransport(ORIGINS["bot"])
        controller = EngineController(models, lambda lane, code: EngineRoom(transport, lane, code), args.output,
                                      wait_seconds=155, continuous=False,
                                      progress=lambda lane, stage: print(f"{lane}: {stage}", flush=True))
        pairs, prepared = {}, {}
        for lane in ("A", "B"):
            created = request("human", "/api/rooms", body={"mode": "remote", "lane": lane})
            joined = request("bot", "/api/rooms/join", body={"role": "bot", "lane": lane, "code": created["code"]})
            pairs[lane] = {"path": "/api/rooms/" + created["roomId"], "human": created["token"], "bot": joined["token"]}
            controller.add(lane, created["code"])
        ready_limit = time.perf_counter() + 30
        while True:
            prepared = {lane: get("human", pair) for lane, pair in pairs.items()}
            if all(state["bot"]["ready"] and state["remote"].get("imageBarrierSupported") for state in prepared.values()): break
            if time.perf_counter() >= ready_limit: raise QAFailure("engine_protocol3_not_ready")
            time.sleep(.15)

        def start(lane):
            pair, current = pairs[lane], prepared[lane]
            for _ in range(3):
                try:
                    return request("human", pair["path"] + "/start", token=pair["human"], body={"expectedRevision": current["revision"]})["state"]
                except HTTPError as error:
                    if error.code != 409: raise
                    current = get("human", pair)
                    if current["phase"] in {"queued", "loading"}: return current
                    if current["phase"] != "lobby": raise QAFailure("start_race_unrecoverable")
            raise QAFailure("start_revision_race")

        with ThreadPoolExecutor(max_workers=2) as pool:
            starts = list(pool.map(start, ("A", "B")))
            summary["start_requests_without_question_or_timer"] = all(
                state["phase"] == "queued" and state["startAt"] is None and state["topic"] is None and state["tiles"] == [] for state in starts)
            jobs = {lane: pool.submit(display_pair, lane, pair) for lane, pair in pairs.items()}
            display_results = {lane: future.result(timeout=180) for lane, future in jobs.items()}
        controller.wait()
        reports = {report["lane"]: report for report in controller.reports}
        checks = {}
        for lane in ("A", "B"):
            report, display = reports[lane], display_results[lane]
            events = report.get("planned_selection_events", [])
            intervals = [b["server_scheduled_at_ms"] - a["server_scheduled_at_ms"] for a, b in zip(events, events[1:])]
            checks[lane] = {
                "ended_normally": report.get("status") == "game_ended",
                "one_model_prediction": report.get("model_predictions_per_game") == 1,
                "one_logical_submission": report.get("logical_submission_count") == 1,
                "server_submission_observed": report.get("server_submission_observed") is True,
                "selection_plan_used": report.get("selection_transport") == "scheduled_plan",
                "all_scheduled_intervals_250ms": report.get("plan_interval_ms") == 250 and all(value == 250 for value in intervals),
                "image_cache_reused": report.get("image_cache_reused") is True,
                "no_in_game_image_download": report.get("public_image_download_during_game_seconds") == 0,
                "model_starts_after_playing_observed": report.get("model_call_started_monotonic_seconds", -1) >= report.get("playing_observed_monotonic_seconds", 1e300),
                "GPU_released_before_plan": report.get("gpu_reservation_released_seconds", 1e300) <= report.get("plan_upload_sent_seconds", -1),
                "viewer_matches_model": display["final"]["selected_indices"] == report.get("selected_indices"),
                "two_concurrent_inference_slots": report.get("max_concurrent_inferences") == 2,
                "both_lanes_loading_gate_passed": display["both_lanes_loading_gate_passed"],
                "all_three_ready_before_countdown": display["all_three_ready_before_countdown"],
                "each_display_decoded_nine_before_ACK": all(row["decoded"] == 9 for row in display["decoded_roles"].values()),
            }
        calls = [(report.get("model_call_started_monotonic_seconds", 0), report.get("model_call_returned_monotonic_seconds", 0)) for report in reports.values()]
        summary.update(lane_checks=checks, displays=display_results,
                       actual_model_host_call_overlap_seconds=max(0., min(end for _, end in calls) - max(start for start, _ in calls)),
                       passed=summary["start_requests_without_question_or_timer"] and all(all(row.values()) for row in checks.values()))
    except Exception as error:
        summary.update(passed=False, error_type=type(error).__name__)
        if isinstance(error, QAFailure): summary["error_code"] = str(error)
        if isinstance(error, HTTPError): summary["HTTP_status"] = error.code
        loading_gate.abort()
    finally:
        if controller is not None: controller.close()
        if transport is not None: transport.close()
        summary.update(total_seconds=time.perf_counter() - started, requests=request_events)
        (args.output / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key not in {"requests", "displays"}}, ensure_ascii=False), flush=True)
    return 0 if summary["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
