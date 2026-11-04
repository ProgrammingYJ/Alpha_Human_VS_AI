"""Audit owned Markdown without excluding data/models/runs/logs wholesale."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--date')
parser.add_argument('--output', type=Path, default=root / 'runs/site-publish/document-audit.json')
args = parser.parse_args()
external = {'.venv', 'venv', '.git', 'node_modules', 'vendor', '__pycache__',
            '.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'build',
            '.wrangler', '.vinext', '.sites-runtime', '.next'}
documents = []
for directory, folders, files in os.walk(root):
    folders[:] = [name for name in folders if name not in external and not name.endswith('.egg-info')]
    documents += [Path(directory) / name for name in files if name.lower().endswith('.md')]
documents.sort()
errors = []
for path in documents:
    text = path.read_text(encoding='utf-8-sig', errors='strict')
    if '\ufffd' in text:
        errors.append(f'{path.relative_to(root)}: Unicode replacement character')
    marker = re.search(r'최종 검토:\s*(\d{4}-\d{2}-\d{2})', text)
    if not marker or (args.date and marker.group(1) != args.date) or '이번 작업 검토:' not in text:
        errors.append(f'{path.relative_to(root)}: review markers')
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        target = unquote(target.split('#', 1)[0].strip('<>'))
        if not target or '://' in target or target.startswith(('mailto:', 'data:')):
            continue
        # Local source documentation uses project-relative targets only.
        if not (path.parent / target).exists():
            errors.append(f'{path.relative_to(root)}: missing link {target}')
latest = (root / 'docs/CHANGELOG.md').read_text(encoding='utf-8').split('## 2026-10-22', 1)[0]
for path in documents:
    if path.relative_to(root).as_posix() not in latest:
        errors.append(f'Latest CHANGELOG list missing {path.relative_to(root)}')
configs = sorted((root / 'configs').glob('*.json'))
for path in configs:
    json.loads(path.read_text(encoding='utf-8-sig'))
if len(documents) != 13:
    errors.append(f'Owned Markdown count was {len(documents)}, expected 13')
report = {'managed_markdown': [path.relative_to(root).as_posix() for path in documents],
          'count': len(documents), 'config_json_count': len(configs), 'errors': errors,
          'passed': not errors,
          'limits': 'Mechanical inventory/link/UTF-8/marker checks; content reviewed separately'}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(1 if errors else 0)
