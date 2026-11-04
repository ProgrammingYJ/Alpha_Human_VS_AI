"""Actual PC ML audit: reuse lane A twice while lane B remains independent.

No private answer/admin access. HTTP viewers stand in for browser displays;
physical booth stations are not tested. --execute creates QA rooms and submits.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.remote_engine import ControlledTransport, EngineController, EngineRoom, NoRedirect, SharedModels
from alpha_captcha.tree_model import TreeCountPredictor
from alpha_captcha.timing import MIN_TILE_INTERVAL_SECONDS
from alpha_captcha.tasks import TaskCondition, select_tiles
from PIL import Image


def verify_target_routing(predictor, image_directory):
    """Compare actual model outputs on fixed local public RGB, never answers."""
    paths = sorted(path for path in Path(image_directory).glob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})[:9]
    if len(paths) != 9:
        raise RuntimeError("routing_requires_nine_local_public_images")
    images, hashes = [], []
    try:
        for path in paths:
            hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as source:
                source.load()
                image = Image.new("RGB", source.size)
                image.paste(source.convert("RGB"))
                images.append(image)
        started = time.monotonic(); full = predictor.predict_tiles(images)
        full_seconds = time.monotonic() - started
        rows = []
        threshold = predictor.presence_metadata["profile"]["threshold"]
        for condition in (TaskCondition("building_present"), TaskCondition("pond_present"), TaskCondition("person_count", "gte", 3)):
            started = time.monotonic(); targeted = predictor.predict_condition_tiles(images, condition)
            seconds = time.monotonic() - started
            thresholds = {label: threshold for label in ("tree", "building", "pond")}
            same_selection = select_tiles(full, condition, thresholds) == select_tiles(targeted, condition, thresholds)
            if condition.task_type == "person_count":
                same_outputs = all(a.person_count == b.person_count for a, b in zip(full, targeted))
                maximum_score_difference = None
            else:
                maximum_score_difference = max(abs(a.presence_scores[label] - b.presence_scores[label])
                    for a, b in zip(full, targeted) for label in ("tree", "building", "pond"))
                same_outputs = maximum_score_difference == 0
            rows.append({"task_type": condition.task_type, "same_selection": same_selection,
                         "same_relevant_outputs": same_outputs, "maximum_score_difference": maximum_score_difference,
                         "targeted_seconds": seconds})
        return {"passed": all(row["same_selection"] and row["same_relevant_outputs"] for row in rows),
                "image_sha256": hashes, "full_prediction_seconds": full_seconds, "conditions": rows,
                "private_labels_or_answers_read": False, "training_or_threshold_changes": False,
                "note": "One fixed nine-image output-equivalence check; timings are not a distribution or accuracy estimate."}
    finally:
        for image in images: image.close()


class ReadinessDisplays:
    """HTTP/PIL stand-ins, not a browser rendering measurement.

    Decode every public image before the role's ACK, retain the successful
    decode across epoch changes, and deliberately hold one human role ready.
    """
    def __init__(self, request, transport, *, slow_human_seconds=3.0):
        self.request, self.transport = request, transport
        self.slow_human_seconds = slow_human_seconds
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="alpha-qa-display")
        self.roles, self.completed, self.held_samples = {}, [], []
        self.checks = {"slow_human_kept_timer_stopped": True, "slow_human_gate_observed": False,
                       "both_roles_decode_nine_before_ready": True, "all_ready_before_countdown": True}

    def _decode(self, paths):
        started = time.monotonic()
        futures = [self.transport._image_pool.submit(self.transport.pixels, path) for path in paths]
        decoded = 0
        try:
            for future in futures:
                image = future.result()
                try:
                    if image.mode != "RGB" or min(image.size) < 3: raise RuntimeError("invalid_decoded_qa_image")
                    decoded += 1
                finally: image.close()
        finally:
            for future in futures:
                try: future.result().close()
                except Exception: pass
        return {"decoded": decoded, "download_decode_seconds": time.monotonic() - started,
                "completed_at": time.monotonic()}

    def observe(self, lane, pair, state):
        if not state.get("remote", {}).get("imageBarrierSupported"):
            return
        if state["phase"] in {"countdown", "playing"}:
            ready = state.get("imageLoad", {})
            self.checks["all_ready_before_countdown"] &= all(ready.get(name + "Ready") for name in ("human", "bot", "engine"))
        if state["phase"] not in {"loading", "countdown"}:
            return
        paths = tuple(tile["url"] for tile in state["preloadTiles"])
        for role, token_name in (("human", "human"), ("bot", "viewer")):
            key = (lane, role, state["roundId"])
            item = self.roles.get(key)
            if item is None:
                item = {"registered": False, "future": self.pool.submit(self._decode, paths), "paths": paths, "acked_epoch": None}
                self.roles[key] = item
            if item["paths"] != paths:
                raise RuntimeError("qa_display_round_pixels_changed")
            body = {"roundId": state["roundId"], "requestId": state["startRequest"]["id"],
                    "imageLoadId": state["imageLoad"]["id"]}
            if not item["registered"]:
                try:
                    self.request(pair["path"] + "/images-ready", token=pair[token_name], body={**body, "ready": False})
                except HTTPError as error:
                    if error.code != 409: raise
                item["registered"] = True
                continue
            if not item["future"].done():
                continue
            if "decode" not in item:
                item["decode"] = item["future"].result()
            decoded = item["decode"]
            slow = lane == "A" and role == "human" and state["roundNumber"] == 1
            if slow and item.get("hold_until") is None and state["imageLoad"]["engineReady"] and state["imageLoad"]["botReady"]:
                # Start the hold only after the other two roles are ready.
                # Starting at this role's decode completion can miss the
                # intended gate when another role prepares more slowly.
                item["hold_until"] = time.monotonic() + self.slow_human_seconds
            if slow and (item.get("hold_until") is None or time.monotonic() < item["hold_until"]):
                stopped = state["phase"] == "loading" and state["startAt"] is None and state["deadlineAt"] is None and state["topic"] is None
                self.checks["slow_human_kept_timer_stopped"] &= stopped
                self.checks["slow_human_gate_observed"] |= stopped and state["imageLoad"]["engineReady"] and state["imageLoad"]["botReady"]
                self.held_samples.append({"lane": lane, "roundNumber": state["roundNumber"], "phase": state["phase"],
                    "timer_stopped": stopped, "engine_ready": state["imageLoad"]["engineReady"], "bot_ready": state["imageLoad"]["botReady"]})
                continue
            if item["acked_epoch"] == state["imageLoad"]["id"]:
                continue
            self.checks["both_roles_decode_nine_before_ready"] &= decoded["decoded"] == 9
            try:
                self.request(pair["path"] + "/images-ready", token=pair[token_name], body={**body, "ready": True})
            except HTTPError as error:
                if error.code != 409: raise
                continue
            item["acked_epoch"] = state["imageLoad"]["id"]
            if not item.get("recorded"):
                self.completed.append({"lane": lane, "role": role, "roundNumber": state["roundNumber"],
                    "decoded": decoded["decoded"], "download_decode_seconds": decoded["download_decode_seconds"],
                    "artificial_ready_hold_seconds": self.slow_human_seconds if slow else 0})
                item["recorded"] = True

    def close(self):
        self.pool.shutdown(wait=True)


class LivenessRecorder:
    """Record only public status/timing, never capabilities or room identities."""

    def __init__(self, *, clock=time.monotonic):
        self.clock, self.started = clock, clock()
        self.samples, self.ready_lanes = [], set()
        self.checks = {"no_disconnect_after_ready": True, "liveness_flag_received": True}

    def observe(self, lane, state):
        remote = state["remote"]
        connected, first = remote.get("engineConnected"), remote.get("engineHeartbeatReceived")
        if type(connected) is not bool or type(first) is not bool:
            self.checks["liveness_flag_received"] = False
        if state["bot"]["ready"]:
            self.ready_lanes.add(lane)
        if lane in self.ready_lanes and (connected is not True or first is not True):
            self.checks["no_disconnect_after_ready"] = False
        self.samples.append({"relative_seconds": self.clock() - self.started, "lane": lane,
                             "roundNumber": state["roundNumber"], "phase": state["phase"],
                             "stage": remote["engineStage"], "connected": connected if type(connected) is bool else None,
                             "firstHeartbeat": first if type(first) is bool else None})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5186")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--routing-image-directory", type=Path, default=Path("data/booth/public-web-v2/images"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output directory")
    if not args.execute:
        print("Dry-run: no rooms, model loading, selection or submission.")
        return 0
    transport = ControlledTransport(args.base_url)
    request_events, audit_started = [], time.monotonic()
    def request(path, *, token=None, body=None):
        headers = {"User-Agent": "AlphaCaptchaContinuousQA/1.0"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(transport.origin + path, headers=headers,
                      data=None if body is None else json.dumps(body).encode("utf-8"))
        sent, status = time.monotonic(), None
        route = next((name for name in ("join", "images-ready", "start", "next") if path.endswith("/" + name)),
                     "create" if path == "/api/rooms" else "state")
        try:
            with build_opener(NoRedirect()).open(req, timeout=15) as response:
                status = response.status
                return json.loads(response.read(262145))
        except HTTPError as error:
            status = error.code
            raise
        finally:
            # Future runs can separate a slow API operation from the serial
            # controller's observation/registration delays. No paths or tokens.
            request_events.append({"route": route, "method": "GET" if body is None else "POST", "status": status,
                                   "sent_relative_seconds": sent - audit_started, "duration_seconds": time.monotonic() - sent})
    args.output.mkdir(parents=True)
    loaded_at = time.monotonic()
    models = SharedModels(TorchTilePredictor.from_checkpoints(
        "models/checkpoints/presence-limited-v1/presence.pt",
        "models/checkpoints/person-limited-v1/person.pt", device=args.device),
        TreeCountPredictor(Path("models/pretrained/grounding-dino-tiny"), device=args.device))
    loading_seconds = time.monotonic() - loaded_at
    warmup = models.warm_up()
    routing = verify_target_routing(models.predictor, args.routing_image_directory)
    controller = EngineController(models, lambda lane, code: EngineRoom(transport, lane, code), args.output,
                                  continuous=True, wait_seconds=150,
                                  progress=lambda lane, stage: print(f"{lane}: {stage}", flush=True))
    pairs = {}
    observations = {}
    # Start before either controller.add(): these are observation times, not
    # lane-specific pairing latency measurements (lane B is polled later).
    liveness = LivenessRecorder()
    displays = ReadinessDisplays(request, transport)
    checks = {"same_room_and_code": True, "same_viewer_capability": True,
              "targeted_inference_matches_full_outputs_and_selection": routing["passed"],
              "selection_reset_before_second_round": False, "engine_rearmed_without_pairing": False}
    try:
        for lane in ("A", "B"):
            created = request("/api/rooms", body={"mode": "remote", "lane": lane})
            viewer = request("/api/rooms/join", body={"role": "bot", "lane": lane, "code": created["code"]})
            pairs[lane] = {"path": "/api/rooms/" + created["roomId"], "human": created["token"],
                           "viewer": viewer["token"], "code": created["code"], "id": created["roomId"]}
            controller.add(lane, created["code"])
        def view(lane):
            pair = pairs[lane]
            state = request(pair["path"], token=pair["viewer"])
            displays.observe(lane, pair, state)
            liveness.observe(lane, state)
            checks["same_room_and_code"] &= state["roomId"] == pair["id"] and state["code"] == pair["code"]
            checks["same_viewer_capability"] &= state["remote"]["viewerConnected"]
            key = lane + str(state["roundNumber"])
            item = {"phase": state["phase"], "stage": state["remote"]["engineStage"],
                    "indices": state["remote"]["selectedIndices"], "sequence": state["remote"]["sequence"]}
            if state.get("imageLoad"):
                item["images_ready"] = {name: state["imageLoad"][name + "Ready"] for name in ("human", "bot", "engine")}
                item["timer_stopped"] = state["startAt"] is None
            rows = observations.setdefault(key, [])
            if not rows or rows[-1] != item:
                rows.append(item)
            return state
        def ready(lane):
            limit = time.monotonic() + 30
            while time.monotonic() < limit:
                state = view(lane)
                if state["bot"]["ready"]:
                    return state
                time.sleep(0.25)
            raise RuntimeError("engine_not_ready")
        prepared_states = {lane: ready(lane) for lane in pairs}
        with ThreadPoolExecutor(max_workers=2) as pool:
            starts = list(pool.map(lambda lane: request(pairs[lane]["path"] + "/start", token=pairs[lane]["human"],
                                                       body={"expectedRevision": prepared_states[lane]["revision"]}), pairs))
        checks["start_requests_queued_without_timer_or_photos"] = all(
            reply["state"]["phase"] == "queued" and reply["state"]["roundId"] is None
            and reply["state"]["startAt"] is None and reply["state"]["topic"] is None
            and reply["state"]["tiles"] == [] and reply["state"]["remote"]["gpuReservationSupported"] is True
            for reply in starts)
        finals = {}
        next_used = False
        limit = time.monotonic() + 240
        while time.monotonic() < limit:
            for lane in pairs:
                state = view(lane)
                if state["phase"] != "result":
                    continue
                number = state["roundNumber"]
                finals[lane + str(number)] = {"winner": state["result"]["winner"], "reason": state["result"]["reason"]}
                if lane == "A" and number == 1 and not next_used:
                    reset = request(pairs[lane]["path"] + "/next", token=pairs[lane]["human"], body={"roundId": state["roundId"]})["state"]
                    checks["selection_reset_before_second_round"] = reset["phase"] == "lobby" and reset["roundId"] is None and reset["roundNumber"] == 1
                    prepared = ready("A")
                    checks["engine_rearmed_without_pairing"] = prepared["remote"]["sequence"] == 0 and prepared["remote"]["selectedIndices"] == []
                    request(pairs[lane]["path"] + "/start", token=pairs[lane]["human"],
                            body={"expectedRevision": prepared["revision"]})
                    next_used = True
            if all(key in finals for key in ("A1", "A2", "B1")):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("continuous_round_timeout")
        wait_until = time.monotonic() + 8
        while len(controller.reports) < 3 and time.monotonic() < wait_until:
            time.sleep(0.1)
        reports = [report for report in controller.reports if report.get("model_predictions_per_game") == 1]
        checks["two_predictions_for_two_A_participants"] = sum(row["lane"] == "A" for row in reports) == 2
        checks["one_B_prediction"] = sum(row["lane"] == "B" for row in reports) == 1
        checks["exactly_one_logical_submit_per_round"] = len(reports) == 3 and all(row["logical_submission_count"] == 1 for row in reports)
        checks["all_rounds_ended_normally"] = len(reports) == 3 and all(row["status"] == "game_ended" for row in reports)
        model_groups = {lane: [row for row in reports if row["lane"] == lane] for lane in ("A", "B")}
        def viewer_matches(lane, number):
            observed = [item for item in observations[lane + str(number)] if item["phase"] == "result"][-1]["indices"]
            report = model_groups[lane][number - 1]
            expected = report["selected_indices"]
            # A human who finishes first cancels future planned selections.
            return observed == expected if report["server_submission_observed"] else observed == expected[:len(observed)]
        checks["viewer_matches_model_each_round"] = all(viewer_matches(lane, number)
            for lane, number in (("A", 1), ("A", 2), ("B", 1)))
        checks["actual_http_intervals_at_least_quarter_second"] = all(
            events[i]["sent_seconds"] - events[i-1]["ack_seconds"] >= MIN_TILE_INTERVAL_SECONDS
            for report in reports for events in [report["selection_events"]] for i in range(1, len(events)))
        checks["scheduled_intervals_are_250ms"] = all(
            events[i]["server_scheduled_at_ms"] - events[i-1]["server_scheduled_at_ms"] == 250
            for report in reports for events in [report["planned_selection_events"]] for i in range(1, len(events)))
        checks["all_gpu_reservations_before_start"] = len(reports) == 3 and all(
            row.get("gpu_reserved_before_start") is True and row["gpu_reserved_monotonic_seconds"]
            <= row["begin_sent_monotonic_seconds"] <= row["begin_ack_monotonic_seconds"]
            <= row["model_call_started_monotonic_seconds"] <= row["model_call_returned_monotonic_seconds"]
            <= row["gpu_released_monotonic_seconds"] for row in reports)
        checks["no_gpu_queue_during_game"] = len(reports) == 3 and all(row.get("gpu_queue_seconds") == 0 for row in reports)
        checks["gpu_released_before_plan_or_selection_and_submit"] = len(reports) == 3 and all(
            row["gpu_reservation_released_seconds"] <= row["plan_upload_sent_seconds" if row["selection_transport"] == "scheduled_plan" else "submit_sent_seconds"]
            and all(row["gpu_reservation_released_seconds"] <= event["sent_seconds"] for event in row["selection_events"])
            for row in reports)
        checks["model_and_state_http_timing_separated"] = len(reports) == 3 and all(
            row.get("timing_schema_version") == 2 and row["model_inference_seconds"] >= 0
            and row["round_state_http_seconds"] >= 0 and row["prestart_gpu_queue_seconds"] >= 0 for row in reports)
        checks.update(liveness.checks)
        checks.update(displays.checks)
        checks["six_display_rounds_decoded_nine_images"] = len(displays.completed) == 6 and all(item["decoded"] == 9 for item in displays.completed)
        checks["all_rounds_used_image_barrier"] = len(reports) == 3 and all(row["image_barrier_used"] for row in reports)
        checks["no_image_download_or_inference_before_readiness_during_game"] = len(reports) == 3 and all(
            row["public_image_download_during_game_seconds"] == 0 and row["prestart_inference_count"] == 0
            and row["image_cache_reused"] and row["image_download_completed_monotonic_seconds"]
            <= row["image_ready_ack_monotonic_seconds"] <= row["playing_observed_monotonic_seconds"]
            <= row["model_call_started_monotonic_seconds"] for row in reports)
        summary = {"passed": all(checks.values()), "checks": checks, "device": args.device,
                   "models_loaded_once_seconds": loading_seconds, "finals": finals,
                   "synthetic_warmup": warmup, "readiness_displays": displays.completed,
                   "targeted_inference_equivalence": routing,
                   "held_human_samples": displays.held_samples,
                   "qa_control_request_events": request_events,
                   "observations": observations, "liveness_samples": liveness.samples,
                   "liveness_sample_count": len(liveness.samples), "physical_tablets_used": 0,
                   "private_answer_or_admin_access": False, "os_input_used": False,
                   "training_or_tuning": False, "accuracy_estimate": None,
                   "selection_timing": {
                       "transports": [row["selection_transport"] for row in reports],
                       "actual_http_interval_samples": sum(max(0, len(row["selection_events"]) - 1) for row in reports),
                       "scheduled_interval_samples": sum(max(0, len(row["planned_selection_events"]) - 1) for row in reports),
                       "server_submissions_observed": sum(row["server_submission_observed"] for row in reports),
                       "note": "Scheduled timestamps are not actual per-tile dispatch or browser rendering measurements."},
                   "limits": "Actual PC models and HTTP viewers; scheduled plan timing is distinct from actual HTTP/visual timing; physical booth stations and event network unverified"}
        (args.output / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in summary.items() if key not in {"observations", "liveness_samples"}}, ensure_ascii=False), flush=True)
        return 0 if summary["passed"] else 1
    finally:
        controller.close()
        displays.close()
        transport.close()


if __name__ == "__main__":
    raise SystemExit(main())
