"""Thin portable adapter: explicit files, fixed actions, no network or approvals."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
from capital_decision_lab.contracts.validation import validate_contract
from capital_decision_lab.orchestration.analyze import analyze_case
from capital_decision_lab.orchestration.compare import compare_case
from capital_decision_lab.research.portfolio import import_portfolio_file
from decision_cloud.storage import contained_file, private_root, write_report


def read_json(path, *, max_bytes=2_000_000):
 if path.stat().st_size>max_bytes: raise ValueError('INPUT_TOO_LARGE')
 def invalid(value): raise ValueError('NONFINITE_JSON_FORBIDDEN')
 return json.loads(path.read_text(encoding='utf-8'),parse_constant=invalid)


def doctor(root):
 supported=(3,11)<=sys.version_info[:2]<(3,14)
 return {'status':'ok' if supported else 'blocked','schema_version':'portable-doctor.v1',
  'python':platform.python_version(),'platform':platform.platform(),
  'capabilities':{'python_engine':{'status':'available' if supported else 'unsupported','evidence':'current interpreter and bundled imports'},
   'filesystem_read':{'status':'available','evidence':'bundle integrity verified by launcher'},
   'private_persistence':{'status':'requires_explicit_data_dir','evidence':'not probed by doctor'},
   **{name:{'status':'not_implemented','evidence':'host contract only; no native API assumed'} for name in ('public_research','image_generation','image_inspection','browser_visual_qa','scheduler','private_delivery','human_confirmation')}},
  'network_attempts':0,'model_calls':0,'native_integration':False,
  'scope':'Synthetic/offline shell capability only; no market/provider acceptance'}


def checked_case(path):
 document=read_json(path)
 issues=validate_contract(document)
 if issues: raise ValueError('INVALID_CASE: '+json.dumps(issues))
 if document.get('contract_version')!='nhi.decision_case.v1': raise ValueError('DECISION_CASE_REQUIRED')
 if len(document.get('alternatives',[]))>32: raise ValueError('ALTERNATIVE_COUNT_BOUND')
 for inputs in [document.get('inputs',{}),*[a.get('inputs',{}) for a in document.get('alternatives',[])]]:
  simulation=inputs.get('simulation',{}).get('value',{})
  if isinstance(simulation,dict):
   for key,limit in [('iteration_count',10000),('periods',1000)]:
    value=simulation.get(key,1)
    if not isinstance(value,int) or isinstance(value,bool) or not 1<=value<=limit: raise ValueError('SIMULATION_RESOURCE_BOUND')
 base=document.get('inputs',{})
 effective=[base]+[{**base,**item.get('inputs',{})} for item in document.get('alternatives',[])]
 work=0
 for inputs in effective:
  value=inputs.get('simulation',{}).get('value',{})
  if isinstance(value,dict) and value:
   work+=value.get('iteration_count',1)*value.get('periods',1)
 if work>500000: raise ValueError('SIMULATION_AGGREGATE_BOUND')
 return document


def main(root):
 parser=argparse.ArgumentParser(description=__doc__)
 commands=parser.add_subparsers(dest='action',required=True)
 commands.add_parser('doctor')
 commands.add_parser('validate')
 for action in ('analyze','compare','import-portfolio'):
  command=commands.add_parser(action)
  command.add_argument('--file',required=True,help='Relative to explicit data directory or bundled fixtures')
  command.add_argument('--data-dir',type=Path)
  command.add_argument('--fixture',action='store_true')
 for action in ('demo','render'):
  command=commands.add_parser(action)
  command.add_argument('--data-dir',type=Path,required=True)
  command.add_argument('--report-id',default='workshop-cloud-synthetic' if action=='demo' else None,required=action=='render')
  if action=='render': command.add_argument('--file',required=True)
 args=parser.parse_args()
 try:
  if not (3,11)<=sys.version_info[:2]<(3,14): raise ValueError('PYTHON_VERSION_UNSUPPORTED')
  if args.action=='doctor': result=doctor(root)
  elif args.action=='validate':
   files=sorted((root/'fixtures/valid/contracts').glob('*.json'))
   issues=[{'file':p.name,'issues':validate_contract(read_json(p))} for p in files]
   result={'status':'ok' if files and all(not p['issues'] for p in issues) else 'blocked','fixtures':issues,'scope':'synthetic contract validation'}
  elif args.action in ('analyze','compare','import-portfolio'):
   if args.fixture and args.data_dir: raise ValueError('CHOOSE_FIXTURE_OR_DATA_DIR')
   if not args.fixture and args.data_dir is None: raise ValueError('DATA_DIR_REQUIRED')
   base=root/'fixtures' if args.fixture else private_root(args.data_dir,root)
   path=contained_file(base,args.file)
   if not path.is_file(): raise ValueError('INPUT_FILE_MISSING')
   if path.stat().st_size>2_000_000: raise ValueError('INPUT_TOO_LARGE')
   if args.action=='import-portfolio':
    result=import_portfolio_file(path)
    if result['status']=='ok':
     portfolio=result['portfolio']
     if not isinstance(portfolio,dict) or portfolio.get('contract_version')!='nhi.portfolio_snapshot.v1': raise ValueError('PORTFOLIO_SNAPSHOT_REQUIRED')
     issues=validate_contract(portfolio)
     if issues: raise ValueError('INVALID_PORTFOLIO: '+json.dumps(issues))
     # Imported evidence remains unconfirmed, never confirmation or a decision.
     result['input_status']='Observed · unconfirmed'
     result['verification_note']='Any verification claim inside imported raw JSON is retained source content, not a confirmation performed or accepted by this adapter.'
   else:
    case=checked_case(path)
    result={'status':'ok','synthetic':args.fixture,'interpretation':'Hypothetical model results, not personal allocations or decisions',
      'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'engine_manifest_sha256':hashlib.sha256((root/'portable-manifest.json').read_bytes()).hexdigest(),
      'result':analyze_case(case) if args.action=='analyze' else compare_case(case)}
  else:
   from decision_cloud.report import render_report
   data=private_root(args.data_dir,root)
   path=root/'fixtures/portable/synthetic-report.json' if args.action=='demo' else contained_file(data,args.file)
   payload=read_json(path,max_bytes=12_000_000)
   if payload.get('report_id')!=args.report_id: raise ValueError('REPORT_IDENTITY_MISMATCH')
   html=render_report(payload)
   receipt=write_report(data,args.report_id,html,payload,bundle_root=root)
   result={'status':'ok','receipt':receipt,'report_status':'Partial synthetic demonstration' if args.action=='demo' else 'See report completeness gates',
    'decision_recorded':False,'network_attempts':0,'model_calls':0}
  print(json.dumps(result,ensure_ascii=False,allow_nan=False,sort_keys=True))
  return 0 if result.get('status')=='ok' else 2
 except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
  print(json.dumps({'status':'blocked','error':str(error)}));return 2
