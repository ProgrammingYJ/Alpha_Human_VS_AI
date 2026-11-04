"""Bounded Wikimedia Commons public-domain/CC0 candidate download.

Search results are candidates only. Explicit RGB review and a separate labels
file are required before bank.json can be approved for publication.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html import unescape
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from PIL import Image, ImageOps, ImageDraw

UA = 'AlphaCaptchaEducationalBooth/1.0 (Wikimedia public-domain photo review)'
MAX_BYTES = 2_000_000
QUERIES = {
    'people': 'Apollo crew portrait',
    'trees': 'forest "public domain"',
    'ponds': 'pond "public domain"',
    'buildings': 'building "public domain"',
    'negatives': 'desert "public domain"',
}

def fetch(url, maximum=MAX_BYTES):
    with urlopen(Request(url, headers={'User-Agent': UA}), timeout=30) as response:
        content = response.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError('Response exceeded bounded size')
    return content

def search(query):
    params = {'action':'query','format':'json','generator':'search','gsrsearch':query,
              'gsrnamespace':6,'gsrlimit':30,'prop':'imageinfo',
              'iiprop':'url|extmetadata|sha1|size','iiurlwidth':800}
    value = json.loads(fetch('https://commons.wikimedia.org/w/api.php?' + urlencode(params)))
    found = []
    for page in sorted(value.get('query', {}).get('pages', {}).values(), key=lambda x: x.get('index', 1000)):
        info = page.get('imageinfo', [{}])[0]
        metadata = info.get('extmetadata', {})
        license_name = metadata.get('LicenseShortName', {}).get('value', '')
        if license_name not in {'Public domain', 'CC0'}:
            continue
        if not re.search(r'\.(jpe?g|png)$', page['title'], re.I):
            continue
        found.append({'title':page['title'],'pageid':page['pageid'],'info':info})
    return found

def download(row, output):
    info = row['info']
    content = fetch(info.get('thumburl', info['url']))
    im = Image.open(BytesIO(content)); im.verify()
    im = Image.open(BytesIO(content)).convert('RGB')
    name = str(row['pageid']) + '.jpg'
    # Strip metadata and re-encode a full-frame thumbnail; no semantic crops.
    path = output / 'candidates' / name
    im.save(path, quality=90, optimize=True)
    row.update({'file':'candidates/' + name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'downloadSha256':hashlib.sha256(content).hexdigest(), 'size':[im.width, im.height]})
    return row

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('data/booth/public-web-v1'))
    parser.add_argument('--queries',nargs='*',help='label=query overrides')
    parser.add_argument('--finalize',action='store_true',help='use reviewed-labels and explicit license approval; no search/download')
    args = parser.parse_args()
    if args.finalize:
        return finalize(args.output)
    queries = dict(item.split('=',1) for item in args.queries) if args.queries else QUERIES
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'candidates').mkdir(exist_ok=True)
    rows=[]
    for label,query in queries.items():
        found=search(query)
        for row in found[:10]:
            row['candidateType']=label
            if row['pageid'] not in {x['pageid'] for x in rows}: rows.append(row)
        print(json.dumps({'queryType':label,'eligibleFound':len(found)},ensure_ascii=True),flush=True)
    successful=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[(row,pool.submit(download,row,args.output)) for row in rows]
        for row,future in futures:
            try: successful.append(future.result())
            except Exception as error: print(json.dumps({'pageid':row['pageid'],'error':type(error).__name__}),flush=True)
    (args.output/'candidate-provenance.json').write_text(json.dumps(successful,ensure_ascii=False,indent=2),encoding='utf-8')
    for start in range(0,len(successful),12):
        part=successful[start:start+12]
        sheet=Image.new('RGB',(1200,960),'white'); draw=ImageDraw.Draw(sheet)
        for n,row in enumerate(part):
            x=(n%4)*300; y=(n//4)*320
            im=Image.open(args.output/row['file']); im=ImageOps.contain(im,(296,275))
            sheet.paste(im,(x+(296-im.width)//2,y))
            draw.text((x+5,y+280),f"{row['pageid']} {row['candidateType']}",fill='black')
            draw.text((x+5,y+296),row['title'][:38].encode('ascii','replace').decode(),fill='black')
        sheet.save(args.output/f'candidate-sheet-{start//12+1}.jpg')
    print(json.dumps({'downloaded':len(successful),'requiresExplicitVisualReview':True}),flush=True)

def finalize(output):
    review=json.loads((output/'reviewed-labels.json').read_text(encoding='utf-8'))
    approvals=json.loads((output/'license-review-summary.json').read_text(encoding='utf-8'))
    if approvals.get('approvedPageIds') != sorted(map(int,review)):
        raise ValueError('Every selected page needs explicit file-license review')
    candidates=json.loads((output/'candidate-provenance.json').read_text(encoding='utf-8'))
    by_id={str(row['pageid']):row for row in candidates}
    (output/'images').mkdir(exist_ok=True)
    rows=[]; hashes=set()
    for pageid,labels in review.items():
        source=by_id[pageid]; path=output/source['file']; data=path.read_bytes()
        sha=hashlib.sha256(data).hexdigest()
        if sha != source['sha256'] or sha in hashes:
            raise ValueError('Changed or duplicate photo bytes')
        hashes.add(sha)
        with Image.open(path) as im:
            im.verify()
        e=source['info']['extmetadata']
        license_name=e['LicenseShortName']['value']
        if license_name not in {'CC0','Public domain'}:
            raise ValueError('Unsupported license for this fixture')
        author=unescape(re.sub('<[^>]*>','',e.get('Artist',{}).get('value','')))
        if pageid=='27424290':
            author='NASA (original photograph); Adam Cuerden (restoration)'
        source_url=source['info']['descriptionurl']
        license_url=e.get('LicenseUrl',{}).get('value') or (
            'https://commons.wikimedia.org/wiki/Template:PD-USGov-NASA' if 'NASA' in e.get('Categories',{}).get('value','')
            else source_url)
        license_url=license_url.replace('http://','https://',1)
        filename=sha[:32]+'.jpg'; shutil.copyfile(path,output/'images'/filename)
        note=labels['note']
        row={'id':'commons-'+pageid,'file':'images/'+filename,'groupId':'commons-original-'+pageid,
             'source':'other','labels':{k:v for k,v in labels.items() if k!='note'},
             'usageNote':'Public test fixture only; Codex RGB review; not training or independent accuracy evaluation. '+note,
             'provenance':{'sha256':sha,'sourceUrl':source_url,'license':license_name,'licenseUrl':license_url,
                           'author':author[:250],'originalId':'commons:'+pageid,'title':source['title'],
                           'originalUrl':source['info']['url'],'originalSha1':source['info']['sha1'],
                           'licenseReview':'Commons original file description wikitext and imageinfo extmetadata',
                           'transformation':'Wikimedia full-frame thumbnail; RGB JPEG re-encode strips metadata; no crop',
                           'reviewedBy':'Codex single visual review; no independent human annotation',
                           'visualReviewNote':note}}
        rows.append(row)
    totals={}
    for theme in ('person_ge3','tree_ge3','building_present','pond_present'):
        values=[]
        for row in rows:
            label=row['labels']
            if theme=='person_ge3':value=label['personCount']>=3 if type(label['personCount']) is int else None
            elif theme=='tree_ge3':value=label['treeAtLeast3']
            else:value=label['building' if theme=='building_present' else 'pond']
            values.append(value)
        totals[theme]={'positiveGroups':sum(v is True for v in values),'negativeGroups':sum(v is False for v in values),
                       'unknown':sum(v is None for v in values)}
        totals[theme]['ready']=totals[theme]['positiveGroups']>=4 and totals[theme]['negativeGroups']>=(6 if theme=='tree_ge3' else 7)
    if not all(value['ready'] for value in totals.values()):raise ValueError('Not every theme is ready')
    bank={'schemaVersion':1,'publicDeploymentCleared':True,'schoolPhotosUsed':False,
          'purpose':'Public website test fixtures only; never train/tune or claim independent accuracy',
          'independentHumanReviewCompleted':False,'modelPredictionsUsedToSelectPhotos':False,
          'images':rows,'readiness':totals,'imageCount':len(rows),
          'totalBytes':sum((output/row['file']).stat().st_size for row in rows),
          'excludedCandidates':{'114587405':'Photo CC BY-SA despite object Public domain metadata',
              '109486171':'Photo CC BY-SA despite object Public domain metadata',
              '52081005':'Jurisdiction-specific/dual licensed photo omitted from simple PD/CC0 fixture',
              '36409963':'Same photographer/date/locality as selected Paulista session; omitted to retain one photo per group',
              '155066939':'Related Apollo 11 portrait session already represented',
              '6449879':'Duplicate Apollo 11 original already represented',
              '23614544':'Artwork, not a photograph','38344996':'Artwork, not a photograph','60873842':'Artwork, not a photograph'}}
    (output/'bank.json').write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'provenance.json').write_text(json.dumps({'sources':[{k:v for k,v in by_id[str(row['provenance']['originalId'].split(':')[1])].items()} for row in rows],
        'licenseApproval':approvals,'visualReviewFile':'reviewed-labels.json'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'imageCount':len(rows),'totalBytes':bank['totalBytes'],'readiness':totals,'publicDeploymentCleared':True}),flush=True)
    return 0

if __name__=='__main__':main()
