"""Independent read-only audit of authored run source; never print matched values."""
from pathlib import Path
import ast
import hashlib
import json
import os
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).with_name('independent-run-source-audit.json')
EXT={'.py','.mjs','.ps1','.cmd','.sh'}
SKIP={'.git','.venv','venv','node_modules','__pycache__','vendor','downloads','external','third_party','site-packages'}
patterns={
 'github_token':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b'),
 'provider_api_key':re.compile(r'\b(?:sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}|hf_[A-Za-z0-9]{25,}|AKIA[A-Z0-9]{16})\b'),
 'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
 'credential_url':re.compile(r'https?://[^\s/:]+:[^\s/@]{6,}@'),
 'literal_sensitive_assignment':re.compile(r'''(?i)(?:admin[_-]?key|access[_-]?token|api[_-]?key|authorization|bearer|bot[_-]?token|human[_-]?token)\s*[:=]\s*["'][A-Za-z0-9_-]{24,}["']'''),
 'literal_room_code':re.compile(r'''(?i)(?:room[_-]?(?:id|code)|human[_-]?code|bot[_-]?code)\s*[:=]\s*["'](?:[A-Za-z0-9_-]{8}|[0-9a-fA-F-]{36})["']'''),
}
files=[];findings=[]
for directory,folders,names in os.walk(ROOT/'runs'):
 folders[:]=[n for n in folders if n not in SKIP]
 for name in names:
  p=Path(directory)/name
  if p.suffix.lower() not in EXT:continue
  rel=p.relative_to(ROOT).as_posix()
  if p.is_symlink():
   findings.append({'path':rel,'category':'symlink_requires_exclusion'});continue
  data=p.read_bytes();s=data.decode('utf-8-sig')
  files.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  for category,pattern in patterns.items():
   for m in pattern.finditer(s):findings.append({'path':rel,'category':category,'line':s.count('\n',0,m.start())+1})
  if p.suffix.lower()=='.py':
   try:tree=ast.parse(s)
   except SyntaxError:
    findings.append({'path':rel,'category':'syntax_error_cannot_analyze'});continue
   for node in ast.walk(tree):
    if not isinstance(node,(ast.Assign,ast.AnnAssign)):continue
    value=node.value
    if not isinstance(value,ast.Constant) or not isinstance(value.value,str):continue
    targets=node.targets if isinstance(node,ast.Assign) else [node.target]
    target=' '.join(ast.unparse(t) for t in targets)
    if re.search(r'(?i)(?:key|token|secret|password|room_id|room_code)',target) and re.fullmatch(r'[A-Za-z0-9_-]{16,}',value.value):
     findings.append({'path':rel,'category':'python_sensitive_named_literal','line':node.lineno,'targetName':target})

r={'scope':'Authored runs source only, never result/catalog/image/model files','extensions':sorted(EXT),'files':files,
   'sourceCount':len(files),'totalBytes':sum(x['bytes'] for x in files),'findings':findings,
   'credentialValuesPrintedOrStored':False,'classificationComplete':False,
   'limits':'Regex/AST findings require manual classification; source is not executed by this audit.'}
OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'sourceCount':len(files),'totalBytes':r['totalBytes'],'findings':findings},ensure_ascii=False))
