"""Audit both public banks' byte/original identities and simple dHash flags."""
import hashlib
import itertools
import json
from pathlib import Path

from PIL import Image


def dhash(path):
    with Image.open(path) as image:
        gray = image.convert('L').resize((9,8), Image.Resampling.LANCZOS)
        values = list(gray.get_flattened_data())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | (values[y*9+x] > values[y*9+x+1])
    return value


def main():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for version in ('v1','v2'):
        folder = root/'data/booth'/('public-web-'+version)
        bank = json.loads((folder/'bank.json').read_text(encoding='utf-8'))
        for row in bank['images']:
            path = folder/row['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row['provenance']['sha256']
            rows.append((version,row,dhash(path)))
    same_original, same_bytes, possible_similar = [], [], []
    for (av,a,ah),(bv,b,bh) in itertools.combinations(rows,2):
        pair = [a['id'],b['id']]
        if a['provenance']['originalId'] == b['provenance']['originalId'] or a['provenance']['originalSha1'] == b['provenance']['originalSha1']:
            same_original.append(pair)
        if a['provenance']['sha256'] == b['provenance']['sha256']:
            same_bytes.append(pair)
        if (ah^bh).bit_count() <= 4:
            possible_similar.append({'ids':pair,'dhashDistance':(ah^bh).bit_count()})
    report = {'imagesAcrossBothBanks':len(rows),'sameOriginalPairs':same_original,
        'sameTransferredBytesPairs':same_bytes,'dhashDistanceAtMostFourPairs':possible_similar,
        'potentialRelatedSessionExcluded':'v2 Gullmar60336752 omitted because v1 Holma59873545 has same photographer/date and nearby locality.',
        'passedIdentityChecks':not same_original and not same_bytes,
        'limits':'Simple dHash only flags some visually similar photographs. It is not a complete duplicate/crop/session genealogy detector or independent human review.'}
    path = root/'data/booth/public-web-v2/group-and-duplicate-review.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['passedIdentityChecks'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
