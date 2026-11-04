"""Read-only public-source audit. Never prints matched credential material."""
from pathlib import Path
import hashlib
import json
import os
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name('independent-source-audit.json')
EXCLUDED={'.git','.venv','venv','node_modules','data','datasets','models','runs','logs',
          '__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','build','dist','out',
          '.next','.vinext','.wrangler','.sites-runtime','.agents','.codex','outputs','work',
          '.idea','.vscode','coverage','.yarn'}
ARTIFACT_EXT={'.pyc','.pyo','.pt','.pth','.onnx','.ckpt','.tflite','.h5','.hdf5','.safetensors',
              '.tar','.gz','.zip','.7z','.jpg','.jpeg','.png','.webp','.mp4','.exe','.dll','.pyd',
              '.so','.db','.sqlite','.sqlite3','.tsbuildinfo','.pem','.key','.pfx','.p12'}
patterns={
 'github_token':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b'),
 'provider_api_key':re.compile(r'\b(?:sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}|hf_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16})\b'),
 'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
 'credential_in_url':re.compile(r'https?://[^\s/:]+:[^\s/@]{6,}@'),
 'literal_admin_or_bearer':re.compile(r'''(?i)(?:ADMIN_KEY|access_token|api_key|Authorization|Bearer|bot_token|human_token)\s*[:=]\s*["'][A-Za-z0-9_-]{24,}["']'''),
}
files=[]; findings=[]; excluded_files=[]; symlinks=[]
for directory,folders,names in os.walk(ROOT,followlinks=False):
 d=Path(directory)
 folders[:]=[n for n in folders if n not in EXCLUDED and not n.endswith('.egg-info')]
 for name in names:
  p=d/name; rel=p.relative_to(ROOT).as_posix()
  if p.is_symlink():symlinks.append(rel);continue
  n=name.lower()
  excluded=(p.suffix.lower() in ARTIFACT_EXT or n in {'kaggle.json','access_token','.npmrc','.netrc','id_rsa','id_ed25519','desktop.ini','thumbs.db','next-env.d.ts'}
       or n.endswith('.local.json') or 'credentials' in n or (n.startswith('.env') and n!='.env.example')
       or n.startswith('.dev.vars') or n.startswith('npm-debug.log') or n.startswith('yarn-error.log'))
  if excluded:excluded_files.append(rel);continue
  data=p.read_bytes();files.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  try:text=data.decode('utf-8-sig')
  except UnicodeDecodeError:
   findings.append({'path':rel,'category':'binary_or_non_utf8_requires_review','bytes':len(data)});continue
  if len(data)>5_000_000:findings.append({'path':rel,'category':'source_over_5MB','bytes':len(data)})
  for category,pattern in patterns.items():
   for match in pattern.finditer(text):findings.append({'path':rel,'category':category,'line':text.count('\n',0,match.start())+1})
report={'scope':'Independent read-only candidate-source inventory; parent decides final export set',
        'sourceRootGitPresent':(ROOT/'.git').exists(),'nestedSitesGitPresent':(ROOT/'web/alpha-arena/.git').exists(),
        'fileCount':len(files),'totalBytes':sum(r['bytes'] for r in files),'files':files,
        'excludedFileCandidates':excluded_files,'excludedDirectories':sorted(EXCLUDED),'symlinks':symlinks,
        'findings':findings,'credentialValuesPrintedOrStored':False,
        'limits':'Pattern scan cannot prove absence of all secrets. Generic literals require manual classification.'}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'fileCount':len(files),'totalBytes':report['totalBytes'],'findings':findings,
                  'symlinks':symlinks,'excludedFileCount':len(excluded_files)},ensure_ascii=False))
