import json
import re
from pathlib import Path
import sys
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from prepare_public_booth_bank import fetch
folder=Path('data/booth/public-web-v3')
selected={61646091,201510322,148520940,94910189,142133935,181762,6454929,881860,20837694}
query={'action':'query','format':'json','pageids':'|'.join(map(str,sorted(selected))),
       'prop':'revisions|imageinfo','rvprop':'content','rvslots':'main','iiprop':'extmetadata|sha1|url|size'}
reply=json.loads(fetch('https://commons.wikimedia.org/w/api.php?'+urlencode(query)))
evidence=[]
for page in reply['query']['pages'].values():
    body=page['revisions'][0]['slots']['main']['*']
    info=page['imageinfo'][0]
    tags=re.findall(r'\{\{\s*([^{}|\n]+)',body)
    row={'pageid':page['pageid'],'title':page['title'],'descriptionWikitext':body,
         'imageinfo':info,'templates':tags}
    evidence.append(row)
    e=info['extmetadata']
    print(json.dumps({'pageid':page['pageid'],'title':page['title'],'templates':tags,
          'license':e.get('LicenseShortName',{}).get('value'),
          'date':e.get('DateTimeOriginal',{}).get('value'),
          'artist':e.get('Artist',{}).get('value')},ensure_ascii=True))
(folder/'selected-file-license-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
