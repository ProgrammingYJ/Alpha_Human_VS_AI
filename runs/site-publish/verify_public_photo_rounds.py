"""Privileged SERVER audit of public photo rendering, never an ML solver."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler
from PIL import Image

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

key = sys.stdin.readline(4097).strip()
root = Path(__file__).resolve().parents[2]
out = root / 'runs/site-publish/public-photo-rounds-verification.json'
if out.exists():
    raise SystemExit('choose a new audit output; existing reports are preserved')
origin = 'https://human.marulee.dev'
bot_origin = 'https://bot.marulee.dev'
ua = 'AlphaCaptchaPublicPhotoAudit/1.0'
def request(path, *, token=None, admin=False, body=None, host=origin, raw=False):
    headers = {'User-Agent': ua, 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if admin:
        headers['x-admin-key'] = key
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    with build_opener(NoRedirect()).open(Request(host + path, data=data, headers=headers), timeout=20) as response:
        blob = response.read(9_000_001)
        assert len(blob) <= 9_000_000
        return blob if raw else json.loads(blob)

readiness = request('/api/admin/status', admin=True)
assert readiness['ready'] is True
bank = json.loads((root / 'data/booth/public-web-v1/bank.json').read_text(encoding='utf-8'))
by_hash = {row['provenance']['sha256']: row for row in bank['images']}
def truth(row, theme):
    labels = row['labels']
    if theme == 'person_ge3':
        count = labels.get('personCount')
        return None if count is None else count >= 3
    if theme == 'tree_ge3':
        if type(labels.get('treeAtLeast3')) is bool:
            return labels['treeAtLeast3']
        count = labels.get('treeCount')
        return None if count is None else count >= 3
    return labels['building' if theme == 'building_present' else 'pond']

private_fields = {'answer_json', 'answers', 'answerTileIds', 'answerCount', 'personCount',
                  'treeCount', 'treeAtLeast3', 'groupId', 'metadata', 'provenance', 'objectKey', 'photoId'}
def no_leak(value):
    if isinstance(value, list):
        for child in value:
            no_leak(child)
    elif isinstance(value, dict):
        for name, child in value.items():
            assert name not in private_fields, name
            no_leak(child)

report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'scope': 'Privileged server photo/round audit; no answer submitted and no model/OS input',
          'photo_count': readiness['photoCount'], 'ready': readiness['ready'],
          'topics_readiness': readiness['topics'], 'verified_topics': {},
          'role_tokens_room_ids_and_codes_stored': False,
          'model_inference_performed': False, 'mouse_control_performed': False,
          'answer_submission_performed': False, 'all_passed': False}

for attempt in range(24):
    human = request('/api/rooms', body={})
    room = '/api/rooms/' + human['roomId']
    bot = request('/api/rooms/join', body={'code': human['code'], 'role': 'bot'}, host=bot_origin)
    request(room + '/ready', token=bot['token'], body={'ready': True}, host=bot_origin)
    countdown = request(room + '/start', token=human['token'], body={})['state']
    assert countdown['phase'] == 'countdown' and not countdown['tiles'] and countdown['topic'] is None
    time.sleep(max(0, countdown['startAt'] / 1000 - time.time() + 0.05))
    state = request(room, token=human['token'])
    no_leak(state)
    theme = state['topic']['id']
    if theme in report['verified_topics']:
        continue
    bot_state = request(room, token=bot['token'], host=bot_origin)
    no_leak(bot_state)
    assert bot_state['startAt'] == state['startAt'] and bot_state['tiles'] == state['tiles']
    assert state['phase'] == 'playing' and len(state['tiles']) == 9
    def check_tile(tile):
        blob = request(tile['url'], raw=True)
        sha = hashlib.sha256(blob).hexdigest()
        assert sha in by_hash
        with Image.open(BytesIO(blob)) as image:
            image.load()
            dimensions = image.size
        return sha, by_hash[sha], dimensions
    with ThreadPoolExecutor(max_workers=4) as pool:
        checked = list(pool.map(check_tile, state['tiles']))
    assert len({item[0] for item in checked}) == 9
    assert len({item[1]['groupId'] for item in checked}) == 9
    values = [truth(item[1], theme) for item in checked]
    assert all(type(value) is bool for value in values)
    count = sum(values)
    assert (3 if theme == 'tree_ge3' else 2) <= count <= 4
    report['verified_topics'][theme] = {'tiles': 9, 'images_decoded': 9,
        'distinct_hashes': 9, 'distinct_original_groups': 9,
        'evaluator_positive_count': count, 'same_start_and_tiles_on_both_hosts': True,
        'private_answer_fields_absent': True}
    print(json.dumps({'verified_topic': theme, 'images_decoded': 9, 'distinct_groups': 9}))
    if len(report['verified_topics']) == 4:
        break
report['rooms_requested'] = attempt + 1
report['all_passed'] = len(report['verified_topics']) == 4
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'all_passed': report['all_passed'], 'topics': list(report['verified_topics']),
                  'photo_count': report['photo_count'], 'rooms_requested': report['rooms_requested']}))
raise SystemExit(0 if report['all_passed'] else 1)
