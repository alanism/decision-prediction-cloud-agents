#!/usr/bin/env python3
"""Relocatable launcher. Integrity is checked before importing bundled code.

For authenticity pin the installer-returned manifest digest out of band using
DECISION_MANIFEST_SHA256. A self-contained unsigned manifest alone detects
accidental changes, not an attacker able to replace both code and manifest.
"""
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent

def verify():
 path=ROOT/'portable-manifest.json'
 if not path.is_file() or path.is_symlink(): raise ValueError('INSTALLED_MANIFEST_REQUIRED')
 raw=path.read_bytes()
 expected=os.environ.get('DECISION_MANIFEST_SHA256')
 if expected and hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('MANIFEST_IDENTITY_MISMATCH')
 manifest=json.loads(raw)
 if manifest.get('schema_version')!='portable-install.v1': raise ValueError('MANIFEST_VERSION_UNSUPPORTED')
 listed=set()
 for item in manifest['files']:
  name=item['path'];relative=Path(name)
  if not name or relative.is_absolute() or PureWindowsPath(name).drive or '\\' in name or '..' in relative.parts: raise ValueError('MANIFEST_PATH_INVALID')
  if name in listed: raise ValueError('MANIFEST_DUPLICATE_PATH')
  listed.add(name);file=ROOT/relative
  if any(p.is_symlink() for p in (file,*file.parents)): raise ValueError('BUNDLE_LINK_FORBIDDEN')
  if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']: raise ValueError('BUNDLE_INTEGRITY_FAILED: '+name)
 actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='portable-manifest.json'}
 if actual!=listed: raise ValueError('BUNDLE_INVENTORY_MISMATCH')
 if 'portable.py' not in listed: raise ValueError('LAUNCHER_IDENTITY_MISSING')
 return manifest

if __name__=='__main__':
 try: verify()
 except (OSError,ValueError,KeyError,TypeError) as error:
  print(json.dumps({'status':'blocked','error':str(error)}));raise SystemExit(2)
 sys.path.insert(0,str(ROOT/'vendor/capital-decision-lab'))
 sys.path.insert(0,str(ROOT/'adapters/cloud'))
 from decision_cloud.cli import main
 raise SystemExit(main(ROOT))
