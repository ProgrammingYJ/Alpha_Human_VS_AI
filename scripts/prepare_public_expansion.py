"""Download bounded CC0/PD candidates for explicit review, never auto-label.

Public API source selection is followed by pixel and file-page licence review.
No model is loaded, and the reviewed bank is not automatically published.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode

from PIL import Image, ImageDraw, ImageOps
from prepare_public_booth_bank import download, fetch, search


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/booth/public-web-v2'
QUERIES = {
    'people_space': 'ISS crew portrait',
    'people_general': 'three people "CC0"',
    'trees': 'forest "CC0"',
    'tree_avenue': 'tree avenue "public domain"',
    'ponds': 'pond "CC0"',
    'buildings': 'house "CC0"',
    'negative_desert': 'desert "CC0"',
}


def sheet(rows, name):
    for offset in range(0, len(rows), 12):
        part = rows[offset:offset+12]
        canvas = Image.new('RGB', (1600, 1200), 'white')
        draw = ImageDraw.Draw(canvas)
        for index, row in enumerate(part):
            x, y = index % 4 * 400, index // 4 * 400
            with Image.open(OUTPUT / row['file']) as original:
                im = ImageOps.contain(original.convert('RGB'), (396, 345))
            canvas.paste(im, (x+(396-im.width)//2, y))
            draw.text((x+4, y+350), f"{row['pageid']} {row['candidateType']}", fill='black')
            draw.text((x+4, y+367), row['title'][:58].encode('ascii','replace').decode(), fill='black')
        canvas.save(OUTPUT / f'{name}-{offset//12+1}.jpg', quality=93)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queries', nargs='*', help='Additional label=query searches; existing candidates are retained')
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'candidates').mkdir(exist_ok=True)
    previous = json.loads((ROOT/'data/booth/public-web-v1/bank.json').read_text(encoding='utf-8'))
    previous_ids = {x['id'] for x in previous['images']}
    previous_original_hashes = {x['provenance']['originalSha1'] for x in previous['images']}
    candidate_path = OUTPUT/'candidate-provenance.json'
    existing = json.loads(candidate_path.read_text(encoding='utf-8')) if candidate_path.exists() else []
    candidates = []
    seen = {row['pageid'] for row in existing}
    queries = dict(item.split('=', 1) for item in args.queries) if args.queries else QUERIES
    for kind, query in queries.items():
        found = search(query)
        chosen = 0
        for row in found:
            if row['pageid'] in seen or 'commons-'+str(row['pageid']) in previous_ids or row['info']['sha1'] in previous_original_hashes:
                continue
            seen.add(row['pageid'])
            row.update(candidateType=kind, searchQuery=query)
            candidates.append(row)
            chosen += 1
            if chosen >= 8:
                break
        print(json.dumps({'queryType':kind,'eligible':len(found),'selectedForReview':chosen}), flush=True)
    successful = list(existing)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [(row,pool.submit(download,row,OUTPUT)) for row in candidates]
        for row,future in futures:
            try:
                successful.append(future.result())
            except Exception as error:
                print(json.dumps({'pageid':row['pageid'],'error':type(error).__name__}), flush=True)
    (OUTPUT/'candidate-provenance.json').write_text(json.dumps(successful,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    descriptions = []
    for offset in range(0,len(successful),20):
        params = {'action':'query','format':'json','pageids':'|'.join(str(x['pageid']) for x in successful[offset:offset+20]),
                  'prop':'revisions','rvprop':'ids|timestamp|content','rvslots':'main'}
        reply = json.loads(fetch('https://commons.wikimedia.org/w/api.php?'+urlencode(params)))
        descriptions.extend(reply.get('query',{}).get('pages',{}).values())
    (OUTPUT/'file-description-evidence.json').write_text(json.dumps({'checkedAtUtc':datetime.now(timezone.utc).isoformat(),'pages':descriptions},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet(successful, 'candidate-sheet')
    print(json.dumps({'downloaded':len(successful),'pixelAndLicenceReviewRequired':True}), flush=True)


if __name__ == '__main__':
    main()
