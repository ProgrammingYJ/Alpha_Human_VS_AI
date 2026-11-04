"""Local UI-only readiness fixture; no usable capabilities or private answers."""
import argparse
import json
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--after-ms", type=int, required=True)
parser.add_argument("--before-ms", type=int, required=True)
args = parser.parse_args()
assert 0 < args.after_ms <= args.before_ms and args.before_ms - args.after_ms < 5000
root = Path(__file__).resolve().parents[2]
site = root / "web/alpha-arena"
def execute(sql):
    completed = subprocess.run(["node", "--import", "./scripts/sites-env.mjs", "./node_modules/wrangler/bin/wrangler.js",
        "d1", "execute", "DB", "--local", "--config", "dist/server/wrangler.json", "--persist-to", ".wrangler/state",
        "--command", sql, "--json"], cwd=site, capture_output=True, text=True)
    if completed.returncode:
        print(json.dumps({"operation":sql.split()[0],"stdout":completed.stdout[-1500:],"stderr":completed.stderr[-1500:]}))
        raise SystemExit(completed.returncode)
    return json.loads(completed.stdout)
rows = execute(f"SELECT room.id,room.code FROM arena_rooms AS room JOIN arena_remote_rooms AS remote ON remote.room_id=room.id WHERE remote.lane='B' AND room.phase='lobby' AND room.created_at BETWEEN {args.after_ms} AND {args.before_ms}")[0]["results"]
assert len(rows) == 1, "Refuse ambiguous browser QA target"
target = rows[0]["id"]
assert len(target) == 36 and all(ch in "0123456789abcdef-" for ch in target)
def request(path, body, token=None):
    headers={"Content-Type":"application/json","User-Agent":"AlphaCaptchaLocalUiFixture/1.0"}
    if token: headers["Authorization"]="Bearer "+token
    with urlopen(Request("http://127.0.0.1:5186"+path,headers=headers,data=json.dumps(body).encode()),timeout=10) as response:
        return json.loads(response.read())
# Pair only this timestamp-bounded disposable QA room. Codes and capabilities
# stay in this process's memory and HTTP bodies, never files/argv/output.
request("/api/rooms/join",{"role":"bot","lane":"B","code":rows[0]["code"]})
engine=request("/api/rooms/join",{"role":"engine","lane":"B","code":rows[0]["code"]})
request("/api/rooms/"+target+"/engine",{"action":"heartbeat","protocolVersion":2,"stage":"ready","requestId":None,"roundId":None,"roundNumber":0},engine["token"])
print(json.dumps({"fixture": "local browser readiness only", "matched_rooms":1, "actual_ml_engine":False,
    "disposable_qa_pairing":True,"credentials_logged":False,"private_answer_access":False}))
