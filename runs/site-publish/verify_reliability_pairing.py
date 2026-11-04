"""Verify normal human-host -> bot-host pairing without ML or private answers."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

from alpha_captcha.remote_engine import ControlledTransport, EngineRoom

def request(origin, path, *, body=None, token=None):
    headers={'User-Agent':'AlphaCrossHostPairingQA/1.0'}
    if body is not None: headers['Content-Type']='application/json'
    if token: headers['Authorization']='Bearer '+token
    with urlopen(Request(origin+path, data=None if body is None else json.dumps(body).encode(), headers=headers),timeout=15) as response:
        return json.loads(response.read(262145))

def main():
    output=Path('runs/site-publish/reliability-cross-host-pairing-20261101.json')
    if output.exists(): raise RuntimeError('Use a new report path')
    human_origin, bot_origin='https://human.marulee.dev','https://bot.marulee.dev'
    created=request(human_origin,'/api/rooms',body={'mode':'remote','lane':'B'})
    viewer=request(bot_origin,'/api/rooms/join',body={'role':'bot','lane':'B','code':created['code']})
    transport=ControlledTransport(bot_origin)
    room=EngineRoom(transport,'B',created['code'])
    try:
        room.heartbeat('ready')
        h=request(human_origin,'/api/rooms/'+created['roomId'],token=created['token'])
        b=request(bot_origin,'/api/rooms/'+created['roomId'],token=viewer['token'])
        checks={'human_create_bot_join_same_room':h['roomId']==b['roomId']==created['roomId'],
                'same_code':h['code']==b['code']==created['code'],
                'same_lane':h['remote']['lane']==b['remote']['lane']=='B',
                'both_observe_fresh_engine':all(s['remote']['engineConnected'] and s['remote']['engineHeartbeatReceived'] and s['bot']['ready'] for s in (h,b)),
                'both_observe_protocol3':all(s['remote']['imageBarrierSupported'] and s['remote']['gpuReservationSupported'] for s in (h,b)),
                'no_round_or_pixels':all(s['phase']=='lobby' and s['roundId'] is None and s['tiles']==[] for s in (h,b))}
        report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'passed':all(checks.values()),
                'models_loaded':False,'round_started':False,'operator_rooms_accessed':False,'credentials_or_ids_logged':False,
                'limits':'Cross-host API pairing/heartbeat only, not browser DOM or a model race.'}
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
        return 0 if report['passed'] else 1
    finally:
        room.heartbeat('error');transport.close()

if __name__=='__main__':raise SystemExit(main())
