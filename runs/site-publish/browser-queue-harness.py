"""Local UI harness: normal disposable pairing, stub heartbeat, no ML or begin.

Read pairing data for the timestamp-bounded browser-created QA room ONLY while
preview is stopped, keep it in memory, then restart our own local preview.
"""
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen

root=Path(__file__).resolve().parents[2]
site=root/"web/alpha-arena"
print("Ready for UI harness JSON on stdin (input hidden).",flush=True)
if sys.stdin.isatty():
    import getpass
    config=json.loads(getpass.getpass(""))
else:
    config=json.loads(sys.stdin.readline())
assert isinstance(config["adminKey"],str) and len(config["adminKey"])>=24
after,before=config["after"],config["before"]
assert type(after) is int and type(before) is int and 0<=before-after<5000
sql=f"SELECT room.id,room.code,room.bot_token_hash IS NOT NULL AS bot_joined,remote.engine_token_hash IS NOT NULL AS engine_joined,remote.engine_token_hash='local-ui-fixture-not-a-capability' AS simulated_engine FROM arena_rooms AS room JOIN arena_remote_rooms AS remote ON remote.room_id=room.id WHERE remote.lane='B' AND room.phase='lobby' AND room.created_at BETWEEN {after} AND {before}"
result=subprocess.run(["node","--import","./scripts/sites-env.mjs","./node_modules/wrangler/bin/wrangler.js","d1","execute","DB","--local","--config","dist/server/wrangler.json","--persist-to",".wrangler/state","--command",sql,"--json"],cwd=site,capture_output=True,text=True,check=True)
rows=json.loads(result.stdout)[0]["results"]
assert len(rows)==1,"Refuse ambiguous QA target"
target,code=rows[0]["id"],rows[0]["code"]
if rows[0]["engine_joined"]:
    assert rows[0]["simulated_engine"]==1,"Refuse to reset a usable engine capability"
    reset=f"UPDATE arena_remote_rooms SET engine_token_hash=NULL,engine_protocol=1,engine_seen_at=NULL,engine_ready=0,engine_stage='disconnected' WHERE room_id='{target}' AND engine_token_hash='local-ui-fixture-not-a-capability'"
    subprocess.run(["node","--import","./scripts/sites-env.mjs","./node_modules/wrangler/bin/wrangler.js","d1","execute","DB","--local","--config","dist/server/wrangler.json","--persist-to",".wrangler/state","--command",reset,"--json"],cwd=site,capture_output=True,text=True,check=True)
def request(path,body=None,token=None):
    headers={"User-Agent":"AlphaCaptchaLocalUiHarness/1.0"}
    if token:headers["Authorization"]="Bearer "+token
    if body is not None:headers["Content-Type"]="application/json"
    with urlopen(Request("http://127.0.0.1:5186"+path,headers=headers,data=None if body is None else json.dumps(body).encode()),timeout=10) as response:
        return json.loads(response.read())
preview=None
try:
    preview=subprocess.Popen(["node","scripts/preview-with-secret.mjs"],cwd=site,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
    preview.stdin.write(json.dumps({"adminKey":config["adminKey"]})+"\n");preview.stdin.flush()
    config.clear()
    limit=time.monotonic()+40
    while True:
        try:
            with urlopen("http://127.0.0.1:5186/",timeout=2) as response:assert response.status==200
            break
        except Exception:
            if time.monotonic()>=limit:raise RuntimeError("preview_not_ready") from None
            time.sleep(.5)
    if not rows[0]["bot_joined"]:request("/api/rooms/join",{"role":"bot","lane":"B","code":code})
    engine=request("/api/rooms/join",{"role":"engine","lane":"B","code":code})
    code=None
    last=None
    limit=time.monotonic()+180
    while time.monotonic()<limit:
        state=request("/api/rooms/"+target,token=engine["token"])
        stage="waiting_gpu" if state["phase"]=="queued" else "ready"
        assert state["phase"] in {"lobby","queued"}
        request("/api/rooms/"+target+"/engine",{"action":"heartbeat","protocolVersion":2,"stage":stage,"requestId":state["startRequest"]["id"] if state["startRequest"] else None,"roundId":None,"roundNumber":state["roundNumber"]},engine["token"])
        if state["phase"]!=last:
            print(json.dumps({"fixture_phase":state["phase"],"timer_started":False,"actual_ml":False,"private_answers":False,"credentials_logged":False}),flush=True)
            last=state["phase"]
        time.sleep(1)
except KeyboardInterrupt:
    print("UI harness stopped.",flush=True)
finally:
    if preview:
        # Terminate only this harness's own preview descendants, never the PC engine.
        subprocess.run(["taskkill","/PID",str(preview.pid),"/T","/F"],capture_output=True)
