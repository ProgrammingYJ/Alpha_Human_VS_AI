import json
from pathlib import Path
import sys
from urllib.request import build_opener, Request
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from import_public_booth_bank import NoRedirect
key=sys.stdin.readline(4097).strip()
if not 16<=len(key)<=1024: raise SystemExit('Missing administrator capability')
out=Path('runs/photo-clarity-20261102/catalog-before.json')
if out.exists():raise SystemExit('preserve_existing_report')
def get(path):
 req=Request('https://human.marulee.dev'+path,headers={'x-admin-key':key,'User-Agent':'AlphaCaptchaClarityReview/1.0'})
 with build_opener(NoRedirect()).open(req,timeout=25) as response:
  raw=response.read(2_000_001)
 if len(raw)>2_000_000:raise RuntimeError('bounded_response')
 return json.loads(raw)
catalog=get('/api/admin/photos');status=get('/api/admin/status')
out.write_text(json.dumps({'status':status,'catalog':catalog,'administratorKeyStoredOrLogged':False},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'photoCount':status['photoCount'],'ready':status['ready'],'savedNoCredentials':True}))
