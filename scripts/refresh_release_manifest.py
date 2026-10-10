"""Refresh only the release inventory after approved edits; never rewrite upstream provenance."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[1]
entries=[]
for p in sorted(R.rglob('*')):
 if p.is_symlink():raise ValueError('Release symlinks are forbidden')
 if not p.is_file() or any(x in p.parts for x in ('.git','__pycache__','.pytest_cache')) or p.suffix=='.pyc' or p.name=='RELEASE-MANIFEST.json':continue
 entries.append({'path':p.relative_to(R).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(R/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema_version':'cloud-release-inventory.v1','excludes':['RELEASE-MANIFEST.json','.git/','__pycache__/','.pytest_cache/','*.pyc'],'files':entries},indent=2)+'\n')
print(json.dumps({'files':len(entries),'manifest_sha256':hashlib.sha256((R/'RELEASE-MANIFEST.json').read_bytes()).hexdigest()}))
