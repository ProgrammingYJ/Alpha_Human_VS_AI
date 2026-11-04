"""Disposable localhost plan fixture; no ML, GUI, images, answers or SQL writes.

The parent created this time-bounded B-room in the browser. The readonly DB
lookup finds only that room's normal pairing code, never answer/round data.
All capabilities stay in memory. Stdout deliberately contains stage/flags only.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
CREATED_FROM = 1793090817689
CREATED_TO = 1793090820174 + 2000
LIFETIME_SECONDS = 300


class FixtureFailure(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def log(stage, accepted=False):
    print(json.dumps({'stage':stage,'planAccepted':accepted,'actualMl':False}), flush=True)


def find_target(created_from, created_to):
    base = ROOT/'web/alpha-arena/.wrangler/state/v3/d1'
    databases = [path for path in base.rglob('*.sqlite') if path.name != 'metadata.sqlite']
    matches = []
    for path in databases:
        # mode=ro enforces read-only access. No migration, update or pragma write.
        uri = path.resolve().as_uri()+'?mode=ro'
        try:
            with sqlite3.connect(uri, uri=True, timeout=2) as connection:
                rows = connection.execute('''SELECT room.id, room.code FROM arena_rooms AS room
                    JOIN arena_remote_rooms AS remote ON remote.room_id = room.id
                    WHERE room.created_at >= ? AND room.created_at <= ?
                    AND remote.lane = 'B' AND remote.engine_token_hash IS NULL
                    AND room.phase = 'lobby' LIMIT 2''', (created_from, created_to)).fetchall()
        except sqlite3.OperationalError:
            continue
        matches.extend(rows)
    if len(matches) != 1:
        raise FixtureFailure('qa_target_not_unique')
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--created-from',type=int,default=CREATED_FROM)
    parser.add_argument('--created-to',type=int,default=CREATED_TO)
    args = parser.parse_args()
    if not 0 < args.created_to-args.created_from <= 10000:
        raise FixtureFailure('invalid_qa_window')
    target, code = find_target(args.created_from,args.created_to)
    origin = 'http://127.0.0.1:5186'
    opener = build_opener(NoRedirect())

    def request(path, *, body=None, token=None):
        headers = {'User-Agent':'AlphaCaptchaLocalPlanUiFixture/1.0'}
        if token:
            headers['Authorization'] = 'Bearer '+token
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = Request(origin+path, headers=headers,
            data=None if body is None else json.dumps(body).encode('utf-8'))
        try:
            with opener.open(req, timeout=8) as response:
                data = response.read(262145)
                if len(data) > 262144:
                    raise FixtureFailure('response_too_large')
                return json.loads(data)
        except HTTPError as error:
            # Never print request URLs, response messages or capability headers.
            reason = 'http_'+str(error.code)
            try:
                server_code = json.loads(error.read(4096)).get('code')
                if isinstance(server_code,str) and re.fullmatch('[a-z_]{1,50}',server_code):
                    reason += '_'+server_code
            except Exception:
                pass
            raise FixtureFailure(reason) from None

    def heartbeat(snapshot, stage):
        try:
            request(path+'/engine', token=token, body={'action':'heartbeat','protocolVersion':2,
                'requestId':snapshot['startRequest']['id'] if snapshot.get('startRequest') else None,
                'roundId':snapshot.get('roundId'),'roundNumber':snapshot['roundNumber'],'stage':stage})
            return True
        except FixtureFailure as error:
            if str(error) in {'http_409_start_request_changed','http_409_round_changed','http_409_round_ended'}:
                # A human can start/cancel/finish after our state GET. The server
                # correctly rejects that old heartbeat; refresh rather than exit.
                log('context_refresh', accepted)
                return False
            raise

    joined = request('/api/rooms/join', body={'role':'engine','lane':'B','code':code})
    code = None
    token = joined['token']
    path = '/api/rooms/'+target
    accepted = False
    began = set()
    due = None
    previous = None
    last_heartbeat = -float('inf')
    started = time.monotonic()
    log('engine_joined')
    while time.monotonic()-started < LIFETIME_SECONDS:
        state = request(path, token=token)
        phase = state.get('phase')
        request_id = state['startRequest']['id'] if state.get('startRequest') else None
        stage = 'submitted' if accepted else 'reserved' if phase=='queued' else 'inferencing' if phase in {'countdown','playing'} else 'ready'
        if time.monotonic()-last_heartbeat >= 3:
            if not heartbeat(state,stage):
                time.sleep(0.1)
                continue
            last_heartbeat = time.monotonic()
        if phase != previous:
            log(phase, accepted)
            previous = phase
        if phase == 'queued' and request_id not in began:
            if not heartbeat(state,'reserved'):
                time.sleep(0.1)
                continue
            request(path+'/engine', token=token, body={'action':'begin','requestId':request_id,
                'roundNumber':state['roundNumber']})
            began.add(request_id)
        if phase == 'playing' and not accepted:
            if due is None:
                due = time.monotonic()+3
            if time.monotonic() >= due:
                if not heartbeat(state,'selecting'):
                    time.sleep(0.1)
                    continue
                reply = request(path+'/engine', token=token, body={'action':'plan',
                    'roundId':state['roundId'],'selectedIndices':[0,2,4,6]})
                accepted = bool(isinstance(reply.get('plan'),dict)
                    and reply['plan'].get('selectedIndices') == [0,2,4,6])
                if not accepted:
                    raise FixtureFailure('plan_not_acknowledged')
                log('plan_accepted', True)
        if phase == 'result':
            log('finished', accepted)
            return 0
        time.sleep(0.2)
    log('fixture_stopped', accepted)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except FixtureFailure as error:
        log(str(error))
        raise SystemExit(1)
    except KeyboardInterrupt:
        log('fixture_interrupted')
        raise SystemExit(0)
    except Exception:
        log('unexpected_fixture_failure')
        raise SystemExit(1)
