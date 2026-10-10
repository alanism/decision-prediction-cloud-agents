"""Offline, stdlib-only fresh bundle installer. No native host registration."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('LICENSE', 'README.md', 'START_HERE.md', 'SOUL.md', 'UPSTREAM.json', 'dlc', 'dlc-thorp',
 'dlc-mauboussin', 'dlc-munger-buffett', 'dlc-laffont', 'dlc-Galloway',
 'dlc-Gerstner', 'dlc-shkreli', 'dlc-camillo', 'dlc-page.md',
 'portable.py', 'scripts/bootstrap_portable.py', 'scripts/update_extraction_board.py')
DIRECTORIES = ('vendor/capital-decision-lab/capital_decision_lab', 'adapters/cloud/decision_cloud',
 'schemas', 'skills', 'fixtures/valid', 'fixtures/portable', 'templates', 'design', 'docs')
EXTRA_FILES = ()

def sha(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()

def selected_files(root):
 selected = list(FILES + EXTRA_FILES)
 for directory in DIRECTORIES:
  base = root / directory
  if not base.is_dir() or base.is_symlink():
   raise ValueError('REQUIRED_ASSET_MISSING_OR_LINK: ' + directory)
  for path in base.rglob('*'):
   if path.is_symlink(): raise ValueError('SYMLINK_ASSET_FORBIDDEN')
   if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
    selected.append(path.relative_to(root).as_posix())
 for name in selected:
  path = root / name
  if not path.is_file() or path.is_symlink(): raise ValueError('REQUIRED_ASSET_MISSING_OR_LINK: ' + name)
  if any(p.is_symlink() for p in path.parents): raise ValueError('SYMLINK_ASSET_FORBIDDEN')
 return sorted(set(selected))

def install(source, destination):
 source=Path(source).resolve(strict=True)
 destination=Path(destination).absolute()
 if destination.exists() or destination.is_symlink(): raise ValueError('DESTINATION_MUST_BE_NEW')
 if any(p.is_symlink() for p in destination.parents): raise ValueError('SYMLINK_DESTINATION_FORBIDDEN')
 if destination.is_relative_to(source) or source.is_relative_to(destination): raise ValueError('SOURCE_DESTINATION_OVERLAP')
 if not destination.parent.is_dir(): raise ValueError('DESTINATION_PARENT_MISSING')
 selected=selected_files(source)
 for name in selected:
  if any(part.casefold() in {'local','private','outputs','logs'} for part in Path(name).parts): raise ValueError('PRIVATE_ASSET_PATH_FORBIDDEN')
  try: text=(source/name).read_text(encoding='utf-8')
  except UnicodeDecodeError: continue
  if ('private_'+'sentinel') in text: raise ValueError('PRIVATE_ASSET_SENTINEL_FORBIDDEN')
 # Retain upstream safety scanners; this separate portable allowlist never
 # weakens the existing Hermes staging allowlist.
 sys.path.insert(0,str(source/'vendor/capital-decision-lab'))
 from capital_decision_lab.privacy.scanner import scan_repository
 issues=scan_repository(source,policy='domain')+scan_repository(source,policy='advice')
 if issues: raise ValueError('SOURCE_POLICY_SCAN_FAILED: '+json.dumps(issues))
 try:
  commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
 except (OSError,subprocess.CalledProcessError): commit=None
 staging=Path(tempfile.mkdtemp(prefix='.decision-install-',dir=destination.parent))
 try:
  inventory=[]
  for name in selected:
   target=staging/name;target.parent.mkdir(parents=True,exist_ok=True)
   shutil.copyfile(source/name,target)
   inventory.append({'path':name,'sha256':sha(target)})
  manifest={'schema_version':'portable-install.v1','product':'Decision ≥ Prediction',
   'bundle_version':'0.1.0-cloud','source_base_commit':commit,
   'identity_note':'Hashes identify installed bytes, including uncommitted implementation changes; source_base_commit is not proof of a published release. See UPSTREAM.json for content provenance.',
   'python':'>=3.11,<3.14','files':inventory,
   'scope':'offline portable shell workflow; no native host integration or live-provider acceptance'}
  (staging/'portable-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
  staging.rename(destination)
 except Exception:
  shutil.rmtree(staging)
  raise
 return {'status':'installed','destination':str(destination),'files':len(inventory),'manifest_sha256':sha(destination/'portable-manifest.json')}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--destination',type=Path,required=True)
 args=parser.parse_args()
 try: result=install(ROOT,args.destination)
 except (OSError,ValueError) as error:
  print(json.dumps({'status':'blocked','error':str(error)}));return 2
 print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__': raise SystemExit(main())
