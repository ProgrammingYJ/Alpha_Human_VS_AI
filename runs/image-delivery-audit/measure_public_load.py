"""Bounded disposable legacy-room photo delivery audit. No model or answers."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'runs/image-delivery-audit/public-load-v11.json'
if OUTPUT.exists(): raise SystemExit('Preserve prior report; choose a new path.')
origin='https://human.marulee.dev'
def request(path,body=None,token=None):
    headers={'User-Agent':'AlphaCaptchaImageDeliveryAudit/1.0'}
    if token: headers['Authorization']='Bearer '+token
    if body is not None: headers['Content-Type']='application/json'
    data=None if body is None else json.dumps(body).encode()
    with urlopen(Request(origin+path,data=data,headers=headers),timeout=20) as response:
        result=response.read(262145)
    if len(result)>262144: raise ValueError('Oversized response')
    return json.loads(result)

def photo(path):
    before=time.monotonic()
    with urlopen(Request(origin+path,headers={'User-Agent':'AlphaCaptchaImageDeliveryAudit/1.0'}),timeout=20) as response:
        headers_at=time.monotonic()
        data=response.read(8*1024*1024+1)
        headers={name:response.headers.get(name) for name in ('Cache-Control','Content-Type','Content-Length','ETag','CF-Cache-Status')}
    received=time.monotonic()
    if len(data)>8*1024*1024: raise ValueError('Oversized photo')
    with Image.open(BytesIO(data)) as image:
        image.load(); size=list(image.size)
    return {'ttfb_seconds':headers_at-before,'body_seconds':received-headers_at,
            'network_seconds':received-before,'decode_seconds':time.monotonic()-received,
            'bytes':len(data),'dimensions':size,'headers':headers}

report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'server_version_basis':'deployed version11 before readiness fix',
        'passed':False,'models_loaded':False,'answer_or_admin_access':False,'selection_or_submission':False,
        'capabilities_codes_room_ids_or_photo_urls_logged':False,'browser_measurement':False,
        'scope':'One disposable legacy QA room; public nine-photo decode twice with max3 parallel Python HTTP calls'}
try:
    human=request('/api/rooms',{})
    viewer=request('/api/rooms/join',{'role':'bot','code':human['code']})
    path='/api/rooms/'+human['roomId']
    request(path+'/ready',{'ready':True},viewer['token'])
    state=request(path+'/start',{},human['token'])['state']
    assert state['tiles']==[]
    time.sleep(max(0,(state['startAt']-state['serverNow'])/1000)+.05)
    state=request(path,token=human['token'])
    assert state['phase']=='playing' and len(state['tiles'])==9
    paths=[tile['url'] for tile in state['tiles']]
    report['trials']=[]
    for number in (1,2):
        started=time.monotonic()
        with ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(photo,paths))
        report['trials'].append({'trial':number,'wall_seconds':time.monotonic()-started,
            'total_bytes':sum(row['bytes'] for row in rows),'photos':rows})
    assert [r['bytes'] for r in report['trials'][0]['photos']]==[r['bytes'] for r in report['trials'][1]['photos']]
    report['passed']=True
except Exception as error:
    report['failure_type']=type(error).__name__
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='trials'}|{'trials':[
    {'trial':r['trial'],'wall_seconds':r['wall_seconds'],'bytes':r['total_bytes'],
     'ttfb_min':min(x['ttfb_seconds'] for x in r['photos']),'ttfb_max':max(x['ttfb_seconds'] for x in r['photos']),
     'cache_controls':sorted({x['headers']['Cache-Control'] for x in r['photos']})}
    for r in report.get('trials',[])]}))
raise SystemExit(0 if report['passed'] else 1)
