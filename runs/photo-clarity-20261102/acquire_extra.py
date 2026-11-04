import json
from pathlib import Path
import sys
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from prepare_public_booth_bank import fetch, download

out = Path('data/booth/public-web-v3')
titles = [
    'File:Garden pond with waterfalls and bridge and fish.jpg',
    'File:Lonely tree.jpg',
    'File:Building 655 at Fort Douglas, Utah - Front and south side view.jpg',
]
rows = []
for title in titles:
    query = {'action':'query','format':'json','titles':title,'redirects':1,
             'prop':'imageinfo|revisions','iiprop':'url|extmetadata|sha1|size',
             'iiurlwidth':800,'rvprop':'content','rvslots':'main'}
    reply = json.loads(fetch('https://commons.wikimedia.org/w/api.php?' + urlencode(query)))
    page = next(iter(reply['query']['pages'].values()))
    info = page['imageinfo'][0]
    license_name = info['extmetadata']['LicenseShortName']['value']
    if license_name not in {'Public domain','CC0'}:
        raise RuntimeError('unsupported_license')
    row = {'pageid':page['pageid'],'title':page['title'],'info':info,
           'candidateType':'extra','fileDescription':page['revisions'][0]['slots']['main']['*']}
    rows.append(download(row,out))
    print(json.dumps({'pageid':row['pageid'],'downloaded':True}),flush=True)
(out/'extra-candidate-provenance.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
