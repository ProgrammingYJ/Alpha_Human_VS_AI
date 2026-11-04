"""Export reviewed source without local data, credentials or nested Git history.

The default is an inventory audit. --copy creates a separate source checkout;
--refresh updates only files still matching this export's previous inventory.
Excluded local artifact links become plain paths in exported Markdown only.
This command never authenticates, creates a remote repository, or pushes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache',
             '.mypy_cache', '.ruff_cache', 'build', 'dist', '.next', '.vinext',
             '.wrangler', '.sites-runtime', '.codex', '.agents', 'coverage',
             'outputs', 'work', 'out'}
PRIVATE_ROOTS = {'data', 'datasets', 'models', 'logs'}
HELPER_SUFFIXES = {'.py', '.mjs', '.ps1', '.cmd', '.sh'}
PRIVATE_HELPERS = {'runs/photo-clarity-20261102/build_review_v1.py',
                   'runs/photo-clarity-20261102/finalize_bank.py'}
SKIP_SUFFIXES = {'.pyc', '.pyo', '.pt', '.pth', '.onnx', '.ckpt', '.safetensors',
                 '.tflite', '.h5', '.jpg', '.jpeg', '.png', '.webp', '.mp4',
                 '.zip', '.gz', '.tgz', '.tar', '.log', '.sqlite', '.sqlite3',
                 '.db', '.pem', '.key', '.pfx', '.p12', '.tmp', '.pending'}
PATTERNS = {
    'github_token': re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{20,}\b|github_pat_[A-Za-z0-9_]{30,}'),
    'provider_secret': re.compile(rb'\b(?:sk-proj-|sk-ant-)[A-Za-z0-9_-]{20,}|\bAKIA[A-Z0-9]{16}\b'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
}

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def source_files():
    selected = []
    for folder, dirs, files in os.walk(ROOT, followlinks=False):
        path = Path(folder)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith('.egg-info')
                   and not (path/d).is_symlink() and not (path/d).is_junction()
                   and not (path == ROOT and d in PRIVATE_ROOTS)]
        for name in files:
            item = path/name
            relative = item.relative_to(ROOT)
            if relative.as_posix() in PRIVATE_HELPERS:
                continue
            if item.is_symlink() or not item.resolve().is_relative_to(ROOT):
                raise ValueError('linked_source_path_not_allowed')
            if relative.parts[0] == 'runs' and item.suffix.lower() not in HELPER_SUFFIXES:
                continue
            if ((name.startswith('.env') and name != '.env.example') or name.startswith('.dev.vars')
                    or name in {'.npmrc', 'kaggle.json', 'access_token', 'next-env.d.ts'}
                    or name.endswith(('.local.json', '.tsbuildinfo'))
                    or ('credentials' in name.lower() and name.endswith('.json'))
                    or item.suffix.lower() in SKIP_SUFFIXES):
                continue
            if item.stat().st_size > 5*1024*1024:
                raise ValueError('unexpected_large_source_file:'+relative.as_posix())
            selected.append(relative)
    # Preserve empty documented layout without traversing private datasets.
    for name in ['data/interim/.gitkeep','data/manifests/.gitkeep','data/processed/.gitkeep',
                 'data/raw/kaggle/.gitkeep','data/raw/school/.gitkeep',
                 'models/checkpoints/.gitkeep','models/exports/.gitkeep','logs/.gitkeep']:
        if (ROOT/name).is_file():selected.append(Path(name))
    return sorted(set(selected))

def export_markdown(relative, blob, selected):
    body = blob.decode('utf-8-sig')
    changed = 0
    def replace(match):
        nonlocal changed
        label,target=match.group(1),match.group(2)
        raw=unquote(target.split('#',1)[0].strip('<>'))
        if not raw or '://' in raw or raw.startswith(('mailto:','data:')):return match.group(0)
        resolved=(ROOT/relative.parent/raw).resolve()
        if resolved.is_relative_to(ROOT):
            rel=resolved.relative_to(ROOT)
            if rel in selected or resolved.is_dir():return match.group(0)
            display=rel.as_posix()
        else:
            display=raw
        changed+=1
        return f'{label} (로컬 산출물: `{display}`)'
    body=re.sub(r'!?\[([^\]]*)\]\(([^)]+)\)',replace,body)
    return (body.encode('utf-8') if changed else blob),changed

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copy',action='store_true')
    parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--destination',type=Path,default=ROOT.parent/'Alpha_Human_VS_AI')
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    destination=args.destination.resolve()
    if destination.is_relative_to(ROOT) or destination==ROOT.parent or destination.name!='Alpha_Human_VS_AI':
        raise ValueError('destination_must_be_separate_named_checkout')
    previous={}
    if args.copy and destination.exists():
        if not args.refresh or not args.report.is_file():raise ValueError('destination_exists')
        prior=json.loads(args.report.read_text(encoding='utf8'))
        if prior['destination']!=str(destination):raise ValueError('different_previous_export')
        previous={r['path']:r['exportSha256'] for r in prior['files']}
    selected=source_files();selected_set=set(selected)
    report={'source':str(ROOT),'destination':str(destination),'copied':args.copy,
            'files':[],'findings':[],'nestedGitHistoryIncluded':False,'dataOrModelFilesIncluded':False,
            'authoredRunHelpersIncluded':True,'markdownArtifactLinksChanged':0}
    prepared=[]
    for relative in selected:
        blob=(ROOT/relative).read_bytes()
        for category,pattern in PATTERNS.items():
            if pattern.search(blob):report['findings'].append({'path':relative.as_posix(),'category':category})
        exported,count=export_markdown(relative,blob,selected_set) if relative.suffix.lower()=='.md' else (blob,0)
        report['markdownArtifactLinksChanged']+=count
        record={'path':relative.as_posix(),'bytes':len(exported),'sourceSha256':sha(blob),
                'exportSha256':sha(exported),'artifactLinksChanged':count}
        report['files'].append(record);prepared.append((relative,exported))
        target=destination/relative
        if args.copy and target.exists() and (record['path'] not in previous or sha(target.read_bytes())!=previous[record['path']]):
            raise ValueError('destination_file_modified:'+record['path'])
    report['fileCount']=len(selected);report['totalBytes']=sum(r['bytes'] for r in report['files'])
    report['passed']=not report['findings']
    if args.copy and report['passed']:
        for relative,blob in prepared:
            target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ['passed','copied','fileCount','totalBytes','markdownArtifactLinksChanged','findings']},ensure_ascii=False))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
