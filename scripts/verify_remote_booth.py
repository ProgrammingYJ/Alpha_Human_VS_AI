"""Exercise two fresh remote rooms with actual frozen PC models, never answers.

Creates isolated QA rooms only with --execute. The two viewer sessions below are
HTTP clients, not physical pads; this does not verify tablet rendering or Wi-Fi.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from urllib.request import Request, build_opener

from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.remote_engine import ControlledTransport, EngineController, EngineRoom, NoRedirect, SharedModels
from alpha_captcha.tree_model import TreeCountPredictor
from alpha_captcha.timing import MIN_TILE_INTERVAL_SECONDS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5186")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output directory")
    if not args.execute:
        print("Dry-run: no room, model, selection or submission was executed.")
        return 0
    transport = ControlledTransport(args.base_url)
    # Human/viewer QA control is separate from the restricted ML transport.
    # The solver transport deliberately cannot create/start rooms or read admin data.
    def qa_request(path, *, token=None, body=None):
        headers = {"User-Agent": "AlphaCaptchaRemoteQA/1.0"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(transport.origin + path, headers=headers,
                          data=None if body is None else json.dumps(body).encode("utf-8"))
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            return json.loads(response.read(262145))
    args.output.mkdir(parents=True)
    load_started = time.monotonic()
    models = SharedModels(TorchTilePredictor.from_checkpoints(
        "models/checkpoints/presence-limited-v1/presence.pt",
        "models/checkpoints/person-limited-v1/person.pt", device=args.device),
        TreeCountPredictor(Path("models/pretrained/grounding-dino-tiny"), device=args.device))
    loading_seconds = time.monotonic() - load_started
    controller = EngineController(models, lambda lane, code: EngineRoom(transport, lane, code),
                                  args.output, wait_seconds=150,
                                  progress=lambda lane, stage: print(f"{lane}: {stage}", flush=True))
    humans, viewers = {}, {}
    observations = {lane: [] for lane in ("A", "B")}
    try:
        for lane in ("A", "B"):
            created = qa_request("/api/rooms", body={"mode": "remote", "lane": lane})
            path = "/api/rooms/" + created["roomId"]
            humans[lane] = (path, created["token"])
            viewer = qa_request("/api/rooms/join", body={"role": "bot", "lane": lane, "code": created["code"]})
            viewers[lane] = (path, viewer["token"])
            controller.add(lane, created["code"])
        end = time.monotonic() + 30
        while True:
            prepared = {lane: qa_request(path, token=token) for lane, (path, token) in humans.items()}
            if all(value["bot"]["ready"] for value in prepared.values()):
                break
            if time.monotonic() >= end:
                raise RuntimeError("remote_engine_not_ready")
            time.sleep(0.2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            starts = list(pool.map(lambda lane: qa_request(humans[lane][0] + "/start", token=humans[lane][1],
                                                          body={"expectedRevision": prepared[lane]["revision"]}), humans))
        requests_queued = all(row["state"]["phase"] == "queued" and row["state"]["startAt"] is None
                              and row["state"]["tiles"] == [] and row["state"]["topic"] is None for row in starts)
        limit = time.monotonic() + 130
        finals = {}
        while len(finals) < 2:
            for lane, (path, token) in viewers.items():
                state = qa_request(path, token=token)
                remote = state["remote"]
                item = {"phase": state["phase"], "stage": remote["engineStage"],
                        "sequence": remote["sequence"], "indices": remote["selectedIndices"],
                        "server_last_selection_at": remote["lastSelectionAt"]}
                if not observations[lane] or item != observations[lane][-1]:
                    observations[lane].append(item)
                if state["phase"] == "result":
                    finals[lane] = {"winner": state["result"]["winner"], "reason": state["result"]["reason"]}
            if time.monotonic() >= limit:
                raise RuntimeError("qa_round_timeout")
            time.sleep(0.2)
        controller.wait()
        by_lane = {report["lane"]: report for report in controller.reports}
        checks = {}
        for lane in ("A", "B"):
            report = by_lane[lane]
            events = report.get("selection_events", [])
            deltas = [events[i]["sent_seconds"] - events[i - 1]["ack_seconds"] for i in range(1, len(events))]
            planned = report["planned_selection_events"]
            planned_deltas = [planned[i]["server_scheduled_at_ms"] - planned[i - 1]["server_scheduled_at_ms"] for i in range(1, len(planned))]
            observed = observations[lane][-1]["indices"]
            expected = report["selected_indices"]
            checks[lane] = {"one_model_prediction": report.get("model_predictions_per_game") == 1,
                            "one_logical_submit": report.get("logical_submission_count") == 1,
                            "ended_normally": report.get("status") == "game_ended",
                            "viewer_matches_model": observed == expected if report["server_submission_observed"] else observed == expected[:len(observed)],
                            "actual_http_intervals_at_least_quarter_second": all(delta >= MIN_TILE_INTERVAL_SECONDS for delta in deltas),
                            "scheduled_intervals_are_250ms": all(delta == 250 for delta in planned_deltas),
                            "selection_transport": report["selection_transport"],
                            "selected_count": len(report.get("selected_indices", [])),
                            "observed_viewer_transitions": len(observations[lane]),
                            "actual_http_interval_samples": len(deltas), "event_intervals_seconds": deltas,
                            "scheduled_interval_samples": len(planned_deltas), "scheduled_intervals_ms": planned_deltas,
                            "server_submission_observed": report["server_submission_observed"],
                            "final": finals[lane]}
        passed = requests_queued and all(all(value for key, value in row.items()
                                            if isinstance(value, bool) and key != "server_submission_observed")
                                         for row in checks.values())
        summary = {"passed": passed, "device": args.device, "models_loaded_once_seconds": loading_seconds,
                   "start_requests_queued_without_timer_or_photos": requests_queued, "lanes": checks,
                   "viewer_state_transitions": observations,
                   "physical_tablets_used": 0, "os_input_used": False,
                   "answer_or_admin_access": False, "training_or_tuning": False,
                   "accuracy_estimate": None,
                   "limits": "Two actual PC ML sessions and HTTP viewers; scheduled times are not actual dispatch times; no physical tablet/browser rendering or Wi-Fi benchmark"}
        (args.output / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in summary.items() if key != "viewer_state_transitions"}, ensure_ascii=False), flush=True)
        return 0 if passed else 1
    finally:
        controller.close()


if __name__ == "__main__":
    raise SystemExit(main())
