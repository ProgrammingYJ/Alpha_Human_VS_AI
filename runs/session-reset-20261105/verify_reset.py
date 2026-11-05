"""Keep QA capabilities only in RAM across a production session reset."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from alpha_captcha.remote_engine import ControlledTransport, EngineRoom, NoRedirect

ORIGINS = {"human": "https://human.marulee.dev", "bot": "https://bot.marulee.dev"}

def request(role, path, *, token=None, body=None):
    headers = {"User-Agent": "AlphaSessionResetQA/1.0"}
    if token: headers["Authorization"] = "Bearer " + token
    if body is not None: headers["Content-Type"] = "application/json"
    req = Request(ORIGINS[role] + path, headers=headers,
                  data=None if body is None else json.dumps(body).encode())
    try:
        with build_opener(NoRedirect()).open(req, timeout=15) as response:
            return response.status, json.loads(response.read(262145))
    except HTTPError as error:
        try: code = json.loads(error.read(8192)).get("code")
        except (ValueError, AttributeError): code = None
        return error.code, {"error_code": code}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        print("Dry-run: no rooms, credentials, HTTP or process changes.")
        return 0
    if args.output.exists(): parser.error("Preserve existing report; choose a new path")
    if not sys.stdin.isatty(): parser.error("Use a retained interactive PTY to preserve RAM-only QA capabilities")
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
              "credentials_logged": False, "answer_or_admin_access": False,
              "models_loaded": False, "rounds_started": 0, "browser_or_OS_input": False}
    old, transports = {}, []
    try:
        before = {}
        for lane in "AB":
            status, created = request("human", "/api/rooms", body={"mode": "remote", "lane": lane})
            if status != 201: raise RuntimeError("QA_create_failed")
            body = {"role": "bot", "lane": lane, "code": created["code"]}
            viewer_status, viewer = request("bot", "/api/rooms/join", body=body)
            transport = ControlledTransport(ORIGINS["bot"]); transports.append(transport)
            engine = EngineRoom(transport, lane, created["code"])
            engine.heartbeat("ready")
            path = "/api/rooms/" + created["roomId"]
            old[lane] = (created, viewer, engine, path)
            duplicate_status, _ = request("bot", "/api/rooms/join", body=body)
            before[lane] = {"created": status, "viewer_joined": viewer_status,
                            "duplicate_viewer_rejected": duplicate_status == 409}
        report["before"] = before
        print("READY_FOR_RESET: two private QA rooms connected; credentials remain in RAM.", flush=True)
        if sys.stdin.readline().strip() != "verify": raise RuntimeError("QA_verification_command_missing")
        after, fresh = {}, {}
        for lane, (created, viewer, engine, path) in old.items():
            statuses = {}
            for role, token in (("human", created["token"]), ("bot", viewer["token"]), ("engine", engine._token)):
                status, result = request("human" if role == "human" else "bot", path, token=token)
                statuses[role] = {"status": status, "error_code": result.get("error_code")}
            join_status, result = request("bot", "/api/rooms/join", body={"role": "bot", "lane": lane, "code": created["code"]})
            statuses["old_code_rejoin"] = {"status": join_status, "error_code": result.get("error_code")}
            after[lane] = statuses
            status, new = request("human", "/api/rooms", body={"mode": "remote", "lane": lane})
            if status != 201: raise RuntimeError("fresh_room_create_failed")
            joined_status, joined = request("bot", "/api/rooms/join", body={"role": "bot", "lane": lane, "code": new["code"]})
            transport = ControlledTransport(ORIGINS["bot"]); transports.append(transport)
            connected = EngineRoom(transport, lane, new["code"])
            connected.heartbeat("ready")
            state_status, state = request("human", "/api/rooms/" + new["roomId"], token=new["token"])
            fresh[lane] = {"created": status == 201, "viewer_joined_once": joined_status == 200,
                           "engine_ready": state_status == 200 and state["bot"]["ready"] is True,
                           "lobby_without_challenge": state_status == 200 and state["phase"] == "lobby" and not state["tiles"]}
            connected.heartbeat("error")
        report.update(after=after, fresh=fresh)
        report["passed"] = all(all(row.values()) for row in fresh.values()) and all(
            value["status"] == 410 and value["error_code"] == "room_reset"
            for statuses in after.values() for value in statuses.values())
    except Exception as error:
        report["error_type"] = type(error).__name__
    finally:
        for transport in transports: transport.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)
    return 0 if report["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
