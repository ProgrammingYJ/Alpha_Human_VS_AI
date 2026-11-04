"""Finalize only explicitly pixel/licence-reviewed public expansion photos."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import shutil

from PIL import Image
from prepare_public_expansion import OUTPUT, ROOT, sheet


def main():
    candidates = json.loads((OUTPUT/'candidate-provenance.json').read_text(encoding='utf-8'))
    selected = json.loads((OUTPUT/'reviewed-labels.json').read_text(encoding='utf-8'))
    evidence = json.loads((OUTPUT/'file-description-evidence.json').read_text(encoding='utf-8'))
    by_id = {str(row['pageid']):row for row in candidates}
    descriptions = {str(row['pageid']):row for row in evidence['pages']}
    old = json.loads((ROOT/'data/booth/public-web-v1/bank.json').read_text(encoding='utf-8'))
    old_ids = {row['provenance']['originalId'] for row in old['images']}
    old_hashes = {row['provenance']['originalSha1'] for row in old['images']}
    old_transferred = {row['provenance']['sha256'] for row in old['images']}
    secondary_path = OUTPUT/'secondary-ai-review.json'
    secondary = json.loads(secondary_path.read_text(encoding='utf-8')) if secondary_path.exists() else None
    secondary_complete = bool(secondary and secondary.get('secondaryAiVisualReviewCompleted') is True
        and secondary.get('approvedPageIds') == sorted(int(x) for x in selected))
    approvals = []
    rows, selected_candidates = [], []
    new_sha1, new_transferred = set(), set()
    (OUTPUT/'images').mkdir(exist_ok=True)
    for identity, label in selected.items():
        row = by_id[identity]
        revision = descriptions[identity]['revisions'][0]
        wikitext = revision['slots']['main']['*']
        meta = row['info']['extmetadata']
        license_name = meta['LicenseShortName']['value']
        # These explicit file IDs were inspected as photographs and their file
        # descriptions reviewed. Templates are an additional consistency check.
        if license_name == 'CC0':
            assert re.search(r'\{\{self\|cc-zero\}\}', wikitext, re.I), identity
            license_url = 'https://creativecommons.org/publicdomain/zero/1.0/'
            license_basis = 'Photographer own-work file declaration and self|cc-zero licence template reviewed'
        elif identity in {'107866069','19966065','22987018','20532882','12063659','14491424'}:
            assert '{{PD-USGov-NASA}}' in wikitext
            license_url = 'https://commons.wikimedia.org/wiki/Template:PD-USGov-NASA'
            license_basis = 'NASA photographic source plus PD-USGov-NASA file template reviewed; no endorsement implied'
        elif identity == '255822':
            assert '{{PD-self}}' in wikitext and 'Photographed by contributor' in wikitext
            license_url = 'https://commons.wikimedia.org/wiki/Template:PD-self'
            license_basis = 'Photographer PD-self public-domain release on original file page reviewed'
        else:
            raise ValueError('File has no explicitly reviewed licence basis')
        data = (OUTPUT/row['file']).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        original_sha1 = row['info']['sha1']
        assert sha == row['sha256'] and sha not in new_transferred | old_transferred
        assert original_sha1 not in new_sha1 | old_hashes and 'commons:'+identity not in old_ids
        with Image.open(OUTPUT/row['file']) as image:
            image.verify()
        author = unescape(re.sub('<[^>]+>', '', meta.get('Artist',{}).get('value','')))
        author = ' '.join(author.split())[:250]
        if not author and identity == '25265833':
            author = 'Wilfredor (The Photographer)'
        filename = sha[:32]+'.jpg'
        shutil.copyfile(OUTPUT/row['file'], OUTPUT/'images'/filename)
        note = label['note']
        provenance = {'sha256':sha,'sourceUrl':row['info']['descriptionurl'],
            'license':license_name,'licenseUrl':license_url,'author':author,
            'originalId':'commons:'+identity,'title':row['title'],
            'originalUrl':row['info']['url'].split('?',1)[0], 'originalSha1':original_sha1,
            'licenseReview':license_basis,'fileDescriptionRevision':revision['revid'],
            'fileDescriptionTimestamp':revision['timestamp'],
            'transformation':'Wikimedia full-frame thumbnail; RGB JPEG re-encode strips metadata; no local crop',
            'reviewedBy':('Codex primary pixel review and parent AI cross-review; no independent human annotation'
                          if secondary_complete else 'Codex pixel review; parent AI cross-review pending; no independent human annotation'),
            'visualReviewNote':note}
        if identity == '61967456':
            provenance['sourceRetouchDisclosure']='Original Commons source declares a small car fragment cloned out.'
        rows.append({'id':'commons-'+identity,'file':'images/'+filename,
            'groupId':'commons-original-'+identity,'source':'other',
            'labels':{key:value for key,value in label.items() if key!='note'},
            'usageNote':'Public booth question photo, excluded from model training/tuning and independent accuracy claims. '+note,
            'provenance':provenance})
        approvals.append({'pageid':int(identity),'title':row['title'],'license':license_name,
            'revisionId':revision['revid'],'checkedBy':'Codex file-page review',
            'basis':license_basis,'photographNotObjectCopyrightOnly':True})
        selected_candidates.append(row)
        new_sha1.add(original_sha1)
        new_transferred.add(sha)
    totals = {}
    for theme in ('person_ge3','tree_ge3','building_present','pond_present'):
        values = []
        for row in rows:
            label = row['labels']
            if theme == 'person_ge3':
                value = label['personCount'] >= 3 if type(label['personCount']) is int else None
            else:
                value = label['treeAtLeast3' if theme=='tree_ge3' else 'building' if theme=='building_present' else 'pond']
            values.append(value)
        totals[theme]={'positiveGroups':sum(value is True for value in values),
            'negativeGroups':sum(value is False for value in values),'unknown':sum(value is None for value in values)}
        totals[theme]['ready']=totals[theme]['positiveGroups']>=4 and totals[theme]['negativeGroups']>=(6 if theme=='tree_ge3' else 7)
    assert all(row['ready'] for row in totals.values()), totals
    exclusion = {'150026314':'File source calls it a pond but wide-water pixels can resemble a lake/river; excluded on parent clarity review, no prediction used.',
        '141320357':'File source calls it a pond but the snowy circular water resembles a puddle; excluded on parent clarity review, no prediction used.',
        '60336752':'Same photographer/date and nearby locality as v1 Holma forest59873545; conservatively omitted as potentially related shooting session.',
        '61782087':'Pre-2017 Unsplash candidate has review-needed category and no reviewed licence confirmation; omitted.',
        '147090135':'Spiral composite rather than ordinary straight photograph; omitted.',
        '148546573':'Same Hampden Pond session/place as public-v1 image; omitted.',
        '151923192':'Same Gun Pond session/place as public-v1 image; omitted.',
        '149042915':'Same Lords Bridge session as selected149042914; omitted.',
        '190219780':'Same Kiyosumi Garden session as selected190219779; omitted.',
        '87777112':'Same botanical lily-pond session as candidate87777181; neither selected.',
        '201088858':'Photo of a school/attack context unnecessary for current non-school public selection; omitted.',
        'otherUnselected':'Paintings, museum objects/models, unclear/inconvenient views or alternatives not needed for selected independent groups; not relabelled as real objects.'}
    bank = {'schemaVersion':1,'publicDeploymentCleared':True,'schoolPhotosUsed':False,
        'purpose':'Public booth question expansion only; excluded from model training/tuning and independent accuracy claims',
        'independentHumanReviewCompleted':False,'secondaryAiVisualReviewCompleted':secondary_complete,
        'modelPredictionsUsedToSelectPhotos':False,'images':rows,'readiness':totals,
        'imageCount':len(rows),'totalBytes':sum((OUTPUT/row['file']).stat().st_size for row in rows),
        'groupReview':'One image per source/session; repeated alternative views removed; no v1 source ID/SHA1 or byte duplicates. Complete photographic genealogy is not guaranteed.',
        'excludedCandidates':exclusion}
    (OUTPUT/'bank.json').write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUTPUT/'license-review-summary.json').write_text(json.dumps({'checkedAtUtc':datetime.now(timezone.utc).isoformat(),
        'approvedPageIds':sorted(int(x) for x in selected),'files':approvals,
        'limits':'File declarations reviewed; not an independent legal or all-third-party-rights guarantee.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUTPUT/'provenance.json').write_text(json.dumps({'sources':selected_candidates,
        'descriptionEvidence':'file-description-evidence.json','reviewedLabels':'reviewed-labels.json',
        'licenceEvidence':'license-review-summary.json','licenses':dict(Counter(x['provenance']['license'] for x in rows)),
        'excluded':exclusion},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet(selected_candidates,'selected-sheet')
    print(json.dumps({'imageCount':len(rows),'totalBytes':bank['totalBytes'],'readiness':totals,
        'licenses':dict(Counter(x['provenance']['license'] for x in rows)),
        'additionalToV1':True,'schoolPhotosUsed':False,'trainingOrTuning':False},ensure_ascii=False))


if __name__ == '__main__':
    main()
