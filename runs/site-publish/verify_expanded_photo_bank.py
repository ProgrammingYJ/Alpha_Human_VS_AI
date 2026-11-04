"""Privileged bank/rendering audit; never a model, solver, or answer submitter."""
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

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'runs/site-publish/expanded-photo-bank-verification.json'
if OUTPUT.exists():
    raise SystemExit('Use a new output file; preserve prior audit.')
key = sys.stdin.readline(4097).strip()
if not 24 <= len(key) <= 4096:
    raise SystemExit('Missing bounded stdin administrator capability.')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def request(path, *, token=None, admin=False, body=None, bot=False, raw=False):
    origin = 'https://bot.marulee.dev' if bot else 'https://human.marulee.dev'
    headers = {'User-Agent':'AlphaCaptchaExpandedBankAudit/1.0'}
    if token: headers['Authorization'] = 'Bearer '+token
    if admin: headers['x-admin-key'] = key
    if body is not None: headers['Content-Type'] = 'application/json'
    req = Request(origin+path,headers=headers,data=None if body is None else json.dumps(body).encode())
    with build_opener(NoRedirect()).open(req,timeout=20) as response:
        blob = response.read(9_000_001)
        assert len(blob) <= 9_000_000
    return blob if raw else json.loads(blob)

expected = {}
new_hashes = set()
for version in (1,2):
    bank = json.loads((ROOT/f'data/booth/public-web-v{version}/bank.json').read_text(encoding='utf-8'))
    for row in bank['images']:
        digest = row['provenance']['sha256']
        assert digest not in expected
        expected[digest] = row
        if version == 2: new_hashes.add(digest)

forbidden = {'answer','answers','answer_json','answerTileIds','answerCount','metadata','provenance',
             'personCount','treeCount','treeAtLeast3','groupId','objectKey','photoId','bot_plan_correct'}
def no_truth(value):
    if isinstance(value,list):
        for row in value: no_truth(row)
    elif isinstance(value,dict):
        for name,child in value.items():
            assert name not in forbidden
            no_truth(child)

def label(row, theme):
    values = row['labels']
    if theme == 'person_ge3':
        n = values.get('personCount'); return None if n is None else n >= 3
    if theme == 'tree_ge3':
        flag = values.get('treeAtLeast3')
        if type(flag) is bool: return flag
        n = values.get('treeCount'); return None if n is None else n >= 3
    return values.get('building' if theme == 'building_present' else 'pond')

def decoded_hash(blob):
    with Image.open(BytesIO(blob)) as image:
        image.verify()
    with Image.open(BytesIO(blob)) as image:
        image.load(); assert image.width >= 3 and image.height >= 3
    return hashlib.sha256(blob).hexdigest()

report = {'checked_at_utc':datetime.now(timezone.utc).isoformat(), 'passed':False,
          'scope':'Privileged SERVER bank/photo audit; no model, selection or answer submission',
          'expected_photo_count':len(expected),'expected_new_photo_count':len(new_hashes),
          'school_photos_used':False,'training_or_tuning':False,'physical_browser_verified':False,
          'capabilities_codes_room_ids_logged':False,'verified_topics':{}}
try:
    status = request('/api/admin/status',admin=True)
    assert status['ready'] is True and status['photoCount'] == len(expected)
    catalog = request('/api/admin/photos',admin=True)['photos']
    assert len(catalog) == len(expected)
    def admin_photo(photo):
        return decoded_hash(request(photo['url'],admin=True,raw=True))
    with ThreadPoolExecutor(max_workers=3) as pool:
        actual_hashes = list(pool.map(admin_photo,catalog))
    assert set(actual_hashes) == set(expected) and len(set(actual_hashes)) == len(expected)
    report.update(photo_count=status['photoCount'],all_admin_images_decoded=True,
                  all_expected_hashes_present=True,topics_readiness=status['topics'])
    public_new = set()
    for attempt in range(24):
        human = request('/api/rooms',body={})
        path = '/api/rooms/'+human['roomId']
        bot = request('/api/rooms/join',body={'role':'bot','code':human['code']},bot=True)
        request(path+'/ready',token=bot['token'],body={'ready':True},bot=True)
        initial = request(path+'/start',token=human['token'],body={})['state']
        assert initial['phase'] == 'countdown' and initial['tiles'] == [] and initial['topic'] is None
        time.sleep(max(0,(initial['startAt']-initial['serverNow'])/1000)+0.05)
        state = request(path,token=human['token']); no_truth(state)
        theme = state['topic']['id']
        if theme in report['verified_topics']: continue
        display = request(path,token=bot['token'],bot=True); no_truth(display)
        assert state['tiles'] == display['tiles'] and state['startAt'] == display['startAt']
        def public_photo(tile):
            digest = decoded_hash(request(tile['url'],raw=True))
            assert digest in expected
            return digest
        with ThreadPoolExecutor(max_workers=3) as pool:
            hashes = list(pool.map(public_photo,state['tiles']))
        assert len(hashes) == 9 and len(set(hashes)) == 9
        groups = [expected[digest]['groupId'] for digest in hashes]
        assert len(set(groups)) == 9
        values = [label(expected[digest],theme) for digest in hashes]
        assert all(type(value) is bool for value in values)
        positives = sum(values)
        assert (3 if theme == 'tree_ge3' else 2) <= positives <= 4
        fresh = set(hashes) & new_hashes; public_new.update(fresh)
        report['verified_topics'][theme] = {'images_decoded':9,'independent_groups':9,
            'correct_count_within_required_bounds':True,'new_bank_images':len(fresh),
            'same_human_bot_photos_and_start':True,'public_state_truth_free':True}
        if len(report['verified_topics']) == 4: break
    assert len(report['verified_topics']) == 4 and public_new
    report.update(public_new_photos_observed=len(public_new),passed=True)
except Exception as error:
    # No traceback, URL, server message, or capability can leave this process.
    report.update(failure_type=type(error).__name__)
OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
