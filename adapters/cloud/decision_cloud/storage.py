"""Explicit private destination, immutable research revisions, atomic current pointer.

This stores report artifacts only, never an authorized decision or approval.
The selected storage provider still controls persistence, access and retention.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from capital_decision_lab.privacy.containment import validate_contained_path


def private_root(path, bundle_root):
 raw=Path(path)
 if not raw.is_absolute(): raise ValueError('DATA_DIR_MUST_BE_EXPLICIT_ABSOLUTE')
 if any(p.is_symlink() for p in (raw,*raw.parents)): raise ValueError('DATA_DIR_LINK_FORBIDDEN')
 root=raw.resolve(strict=True); bundle=Path(bundle_root).resolve(strict=True)
 if not root.is_dir(): raise ValueError('DATA_DIR_NOT_DIRECTORY')
 if any((p/'.git').is_file() or (p/'.git'/'HEAD').exists() for p in (root,*root.parents)): raise ValueError('DATA_DIR_IN_REPOSITORY_FORBIDDEN')
 if root.is_relative_to(bundle) or bundle.is_relative_to(root): raise ValueError('DATA_DIR_BUNDLE_OVERLAP')
 return root


def contained_file(root, relative):
 if not isinstance(relative,str) or not relative or '\\' in relative:
  raise ValueError('RELATIVE_PATH_REQUIRED')
 candidate=Path(relative)
 if candidate.is_absolute() or PureWindowsPath(relative).drive or '..' in candidate.parts:
  raise ValueError('RELATIVE_PATH_REQUIRED')
 check=validate_contained_path(Path(root),candidate)
 if not check['allowed']: raise ValueError(check['issues'][0]['code'])
 return Path(check['resolved_path'])


def write_report(root, report_id, html, payload, *, bundle_root):
 root=private_root(root,bundle_root)
 if not isinstance(report_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',report_id):
  raise ValueError('REPORT_ID_INVALID')
 # Validate all serialization before filesystem changes.
 encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False).encode('utf-8')+b'\n'
 content=html.encode('utf-8')
 reports=contained_file(root,'reports');reports.mkdir(mode=0o700,exist_ok=True)
 base=contained_file(root,'reports/'+report_id);base.mkdir(mode=0o700,exist_ok=True)
 lock=base/'.write-lock'
 try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 except FileExistsError: raise ValueError('REPORT_WRITE_BUSY_OR_INTERRUPTED')
 os.close(fd)
 temporary=None
 try:
  revisions=contained_file(root,'reports/'+report_id+'/versions');revisions.mkdir(mode=0o700,exist_ok=True)
  existing=[int(p.name[1:]) for p in revisions.iterdir() if re.fullmatch(r'v\d{6}',p.name)]
  revision='v'+str(max(existing,default=0)+1).zfill(6)
  if len(revision)!=7: raise ValueError('REVISION_LIMIT_REACHED')
  target=contained_file(root,f'reports/{report_id}/versions/{revision}')
  temporary=Path(tempfile.mkdtemp(prefix='.pending-',dir=base))
  files={'report.html':content,'input.json':encoded}
  for name,data in files.items():
   with (temporary/name).open('xb') as handle:
    os.chmod(temporary/name,0o600);handle.write(data);handle.flush();os.fsync(handle.fileno())
  receipt={'schema_version':'report-revision.v1','report_id':report_id,'revision':revision,
   'created_at':datetime.now(timezone.utc).isoformat(),
   'kind':'educational_research_report_not_decision_record',
   'bundle_manifest_sha256':hashlib.sha256((Path(bundle_root)/'portable-manifest.json').read_bytes()).hexdigest() if (Path(bundle_root)/'portable-manifest.json').is_file() else None,
   'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
  (temporary/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
  os.chmod(temporary/'receipt.json',0o600)
  temporary.rename(target);temporary=None
  # Stable identity is a small atomic pointer to an immutable pair, avoiding
  # a split update of current HTML and audit JSON after interruption.
  pointer=base/('.current-'+uuid.uuid4().hex)
  with pointer.open('x',encoding='utf-8') as handle:
   os.chmod(pointer,0o600);json.dump({'revision':revision,'report':'versions/'+revision+'/report.html','receipt':'versions/'+revision+'/receipt.json'},handle);handle.flush();os.fsync(handle.fileno())
  os.replace(pointer,base/'current.json')
  return receipt
 finally:
  if temporary is not None: shutil.rmtree(temporary)
  lock.unlink()
