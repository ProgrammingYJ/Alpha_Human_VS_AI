"""Isolated API pacing audit, without ML, image download, answers or submission.

Creates its own disposable remote room. Capabilities and room identities remain
in memory, never arguments or output. A run does not measure browser rendering.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class AuditFailure(Exception):
    """Only a fixed, non-sensitive failure code may leave the audit."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def require(condition, code):
    if not condition:
        raise AuditFailure(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://bot.marulee.dev")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("quarter-interval-api.json"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    origin = urlsplit(args.base_url)
    require(not origin.username and not origin.password and not origin.query
            and not origin.fragment and origin.path in {"", "/"}, "invalid_origin")
    allowed = (origin.scheme == "https" and origin.hostname in {"bot.marulee.dev", "human.marulee.dev"}
               and origin.port in {None, 443}) or (origin.scheme == "http"
               and origin.hostname in {"127.0.0.1", "localhost", "::1"})
    require(allowed, "unsupported_origin")
    if not args.execute:
        print("Dry-run: no room creation, model, images, selection or submission.")
        return 0

    opener = build_opener(NoRedirect())
    base = args.base_url.rstrip("/")
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "audit": "isolated_fixed_tile_api_interval_without_ml",
              "passed": False, "configured_minimum_seconds": 0.25,
              "selection_events": [], "server_intervals_ms": [],
              "duplicate_ack_preserved": False,
              "images_downloaded": 0, "private_answers_read": False,
              "actual_ml": False, "submission_performed": False,
              "browser_rendering_verified": False, "credentials_logged": False,
              "limits": "Fixed indices 0,1,2 test transport pacing only. No accuracy, inference speed or visual timing measurement. Disposable room is left unsubmitted to expire normally."}
    def request(path, *, token=None, body=None):
        headers = {"User-Agent": "AlphaCaptchaQuarterIntervalQA/1.0"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(base + path, headers=headers,
                      data=None if body is None else json.dumps(body).encode("utf-8"))
        before = time.monotonic()
        try:
            with opener.open(req, timeout=15) as response:
                payload = response.read(262145)
                require(len(payload) <= 262144, "response_too_large")
                result = json.loads(payload)
        except HTTPError as failure:
            # Do not expose request URLs, tokens, response messages or headers.
            code = "http_" + str(failure.code)
            try:
                server_code = json.loads(failure.read(4096)).get("code")
                if isinstance(server_code, str) and re.fullmatch(r"[a-z_]{1,50}", server_code):
                    code += "_" + server_code
            except Exception:
                pass
            raise AuditFailure(code) from None
        return result, time.monotonic() - before

    try:
        created, _ = request("/api/rooms", body={"mode": "remote", "lane": "A"})
        path, human, code = "/api/rooms/" + created["roomId"], created["token"], created["code"]
        viewer, _ = request("/api/rooms/join", body={"role": "bot", "lane": "A", "code": code})
        engine, _ = request("/api/rooms/join", body={"role": "engine", "lane": "A", "code": code})
        del code, created
        token = engine["token"]
        ready, _ = request(path + "/engine", token=token, body={"action": "heartbeat", "stage": "ready",
            "roundId": None, "roundNumber": 0, "protocolVersion": 2, "requestId": None})
        queued, _ = request(path + "/start", token=human,
                            body={"expectedRevision": ready["state"]["revision"]})
        state = queued["state"]
        require(state["phase"] == "queued" and state["roundId"] is None and state["startAt"] is None
                and state["topic"] is None and state["tiles"] == [], "queue_privacy_failed")
        report["queue_hidden_and_timer_zero"] = True
        request_id = state["startRequest"]["id"]
        request(path + "/engine", token=token, body={"action": "heartbeat", "stage": "reserved",
            "roundId": None, "roundNumber": 0, "protocolVersion": 2, "requestId": request_id})
        begun, _ = request(path + "/engine", token=token,
                            body={"action": "begin", "requestId": request_id, "roundNumber": 0})
        state = begun["state"]
        require(state["phase"] in {"countdown", "playing"}, "begin_failed")
        time.sleep(max(0, (state["startAt"] - state["serverNow"]) / 1000) + 0.05)
        state, _ = request(path, token=token)
        require(state["phase"] == "playing", "round_not_playing")
        round_id, start_at = state["roundId"], state["startAt"]
        request(path + "/engine", token=token, body={"action": "heartbeat", "stage": "selecting",
            "roundId": round_id, "roundNumber": 1, "protocolVersion": 2, "requestId": request_id})
        previous_ack = None
        first_at = None
        for sequence, tile in enumerate((0, 1, 2), 1):
            if previous_ack is not None:
                time.sleep(max(0, previous_ack + 0.25 - time.monotonic()))
            body = {"action": "select", "roundId": round_id, "sequence": sequence, "tileIndex": tile}
            selected, elapsed = request(path + "/engine", token=token, body=body)
            previous_ack = time.monotonic()
            remote = selected["state"]["remote"]
            require(remote["sequence"] == sequence and remote["selectedIndices"] == list(range(sequence)), "selection_mismatch")
            selected_at = remote["lastSelectionAt"]
            require(type(selected_at) is int, "invalid_selection_time")
            if first_at is None:
                first_at = selected_at
            report["selection_events"].append({"sequence": sequence, "tile_index": tile,
                "server_selection_at_ms": selected_at, "server_round_elapsed_ms": selected_at - start_at,
                "relative_to_first_selection_ms": selected_at - first_at,
                "request_elapsed_seconds": elapsed})
            if sequence == 1:
                repeated, _ = request(path + "/engine", token=token, body=body)
                repeat = repeated["state"]["remote"]
                require(repeat["lastSelectionAt"] == selected_at and repeat["sequence"] == sequence
                        and repeat["selectedIndices"] == [0], "duplicate_ack_changed")
                report["duplicate_ack_preserved"] = True
        events = report["selection_events"]
        intervals = [right["server_selection_at_ms"] - left["server_selection_at_ms"]
                     for left, right in zip(events, events[1:])]
        report["server_intervals_ms"] = intervals
        report["interval_samples"] = len(intervals)
        report["minimum_server_interval_ms"] = min(intervals)
        report["maximum_server_interval_ms"] = max(intervals)
        report["all_server_intervals_at_least_250ms"] = all(value >= 250 for value in intervals)
        final, _ = request(path, token=viewer["token"])
        report["viewer_selection_matches"] = final["remote"]["selectedIndices"] == [0, 1, 2]
        report["passed"] = report["all_server_intervals_at_least_250ms"] and report["viewer_selection_matches"]
    except AuditFailure as failure:
        report["error_code"] = str(failure)
    except Exception:
        # Generic failures must not include a capability-bearing traceback.
        report["error_code"] = "unexpected_audit_failure"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditFailure as failure:
        print(json.dumps({"passed": False, "error_code": str(failure)}))
        raise SystemExit(1)
