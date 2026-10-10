"""Offline installation/storage acceptance, runnable without test dependencies."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'vendor/capital-decision-lab'))
sys.path.insert(0,str(ROOT/'adapters/cloud'))
spec=importlib.util.spec_from_file_location('bootstrap',ROOT/'scripts/bootstrap_portable.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)
from decision_cloud.storage import private_root, contained_file, write_report

class StorageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.data=self.root/'private';self.data.mkdir()
 def tearDown(self): self.temp.cleanup()
 def test_no_implicit_data_directory(self):
  for p in [Path('relative'),self.root/'missing',ROOT,ROOT/'fixtures']:
   with self.assertRaises((ValueError,OSError)): private_root(p,ROOT)
 def test_reject_foreign_and_traversal_paths(self):
  for p in ['../escape','/etc/passwd',r'C:\Windows\file','C:relative',r'\\server\share','a/../../b']:
   with self.subTest(path=p),self.assertRaises(ValueError): contained_file(self.data,p)
 def test_repo_data_destination_refused(self):
  (self.data/".git").mkdir();(self.data/".git/HEAD").touch()
  with self.assertRaises(ValueError): private_root(self.data,ROOT)
 def test_reject_symlink(self):
  (self.data/'link').symlink_to(self.root,target_is_directory=True)
  with self.assertRaises(ValueError): contained_file(self.data,'link/file')
 def test_versions_and_stable_current(self):
  first=write_report(self.data,'demo','<html>one</html>',{'synthetic':True},bundle_root=ROOT)
  before=(self.data/'reports/demo/versions/v000001/report.html').read_bytes()
  second=write_report(self.data,'demo','<html>two</html>',{'synthetic':True},bundle_root=ROOT)
  self.assertEqual(first['revision'],'v000001');self.assertEqual(second['revision'],'v000002')
  self.assertEqual(before,(self.data/'reports/demo/versions/v000001/report.html').read_bytes())
  self.assertEqual(json.loads((self.data/'reports/demo/current.json').read_text())['revision'],'v000002')
  self.assertEqual(hashlib.sha256(before).hexdigest(),first['files']['report.html'])
  self.assertEqual(first['kind'],'educational_research_report_not_decision_record')
 def test_invalid_identity_no_write(self):
  for name in ['../escape','/absolute','C:bad','bad/name','']:
   with self.assertRaises(ValueError): write_report(self.data,name,'html',{},bundle_root=ROOT)
  self.assertEqual(list(self.data.iterdir()),[])
 def test_busy_writer_no_overwrite(self):
  write_report(self.data,'demo','one',{},bundle_root=ROOT)
  (self.data/'reports/demo/.write-lock').touch()
  with self.assertRaises(ValueError): write_report(self.data,'demo','two',{},bundle_root=ROOT)
  self.assertEqual(len(list((self.data/'reports/demo/versions').iterdir())),1)
 def test_invalid_nan_no_write(self):
  with self.assertRaises(ValueError): write_report(self.data,'demo','one',{'number':float('nan')},bundle_root=ROOT)
  self.assertEqual(list(self.data.iterdir()),[])

class InstallationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self): self.temp.cleanup()
 def install(self):
  target=self.root/'fresh';self.receipt=bootstrap.install(ROOT,target);return target
 def run_cli(self,bundle,*args):
  env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('DECISION_MANIFEST_SHA256',None)
  return subprocess.run([sys.executable,'-I',str(bundle/'portable.py'),*args],cwd=self.root,text=True,capture_output=True,env=env,timeout=30)
 def test_fresh_complete_relocated_install(self):
  old=self.install();bundle=self.root/'relocated';old.rename(bundle)
  manifest=json.loads((bundle/'portable-manifest.json').read_text());paths={p['path'] for p in manifest['files']}
  for name in ['dlc-Galloway','dlc-Gerstner','dlc-camillo','dlc-laffont','dlc-mauboussin','dlc-munger-buffett','dlc-shkreli','dlc-thorp','dlc-page.md','skills/decision-prediction/SKILL.md','skills/decision-prediction/references/monocle-report-anatomy.md','docs/cloud-portability/REPORT-POLICY.md']:
   self.assertIn(name,paths)
  self.assertFalse(any(p.split('/')[0] in {'.git','local','tests','outputs'} for p in paths))
  for args in [('doctor',),('validate',),('analyze','--fixture','--file','valid/mvp-case.json'),('compare','--fixture','--file','valid/mvp-case.json')]:
   result=self.run_cli(bundle,*args)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  first=self.run_cli(bundle,'analyze','--fixture','--file','valid/mvp-case.json')
  second=self.run_cli(bundle,'analyze','--fixture','--file','valid/mvp-case.json')
  self.assertEqual(first.stdout,second.stdout)
  output=json.loads(first.stdout)['result'];self.assertAlmostEqual(output['data']['roi']['value'],.08)
 def test_tamper_fails_before_import(self):
  bundle=self.install();(bundle/'vendor/capital-decision-lab/capital_decision_lab/__init__.py').write_text('raise RuntimeError("must not execute")')
  result=self.run_cli(bundle,'doctor');self.assertEqual(result.returncode,2);self.assertIn('BUNDLE_INTEGRITY_FAILED',result.stdout);self.assertNotIn('RuntimeError',result.stderr)
 def test_extra_file_fails(self):
  bundle=self.install();(bundle/'injected.py').write_text('pass')
  result=self.run_cli(bundle,'doctor');self.assertEqual(result.returncode,2);self.assertIn('INVENTORY',result.stdout)
 def test_reinstall_does_not_overwrite(self):
  bundle=self.install()
  with self.assertRaises(ValueError): bootstrap.install(ROOT,bundle)
 def test_explicit_data_and_bad_action(self):
  bundle=self.install()
  for args in [('trade',),('analyze','--fixture','--file','../portable.py'),('analyze','--file','valid/mvp-case.json')]:
   result=self.run_cli(bundle,*args);self.assertNotEqual(result.returncode,0,result.stdout)
 def test_aggregate_work_rejected(self):
  from decision_cloud.cli import checked_case
  case=json.loads((ROOT/'fixtures/valid/mvp-case.json').read_text())
  case['alternatives']=[{'alternative_id':'alt_'+str(i),'label':'Synthetic alternative'} for i in range(33)]
  path=self.root/'many.json';path.write_text(json.dumps(case))
  with self.assertRaisesRegex(ValueError,'ALTERNATIVE_COUNT_BOUND'): checked_case(path)
  case['alternatives']=case['alternatives'][:10]
  case['inputs']['simulation']['value'].update(iteration_count=10000,periods=100)
  path.write_text(json.dumps(case))
  with self.assertRaisesRegex(ValueError,'SIMULATION_AGGREGATE_BOUND'): checked_case(path)
 def test_wrong_portfolio_contract_refused(self):
  bundle=self.install()
  result=self.run_cli(bundle,"import-portfolio","--fixture","--file","valid/mvp-case.json")
  self.assertEqual(result.returncode,2,result.stdout)
 def test_missing_asset_refused(self):
  source=self.root/'source';shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('.git','__pycache__'))
  (source/'dlc-thorp').unlink()
  with self.assertRaises(ValueError): bootstrap.install(source,self.root/'output')
  self.assertFalse((self.root/'output').exists())
 def test_private_fixture_sentinel_refused(self):
  source=self.root/'source';shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('.git','__pycache__'))
  (source/'fixtures/portable/accidental.json').write_text('{"note":"private_sentinel"}')
  with self.assertRaises(ValueError): bootstrap.install(source,self.root/'output')
  self.assertFalse((self.root/'output').exists())
 def test_json_csv_import_and_malformed_input(self):
  bundle=self.install();data=self.root/'private';data.mkdir()
  csv='ticker,shares,current_price,user_intent,cash,borrowed_amount,maintenance_margin_requirement,initial_margin_requirement\nSYNTH,10,20,watch,100,0,0.25,0.5\n'
  (data/'synthetic.csv').write_text(csv)
  first=self.run_cli(bundle,'import-portfolio','--data-dir',str(data),'--file','synthetic.csv')
  second=self.run_cli(bundle,'import-portfolio','--data-dir',str(data),'--file','synthetic.csv')
  self.assertEqual(first.returncode,0,first.stdout+first.stderr)
  a=json.loads(first.stdout)['portfolio'];b=json.loads(second.stdout)['portfolio']
  a.pop('capture_timestamp');b.pop('capture_timestamp');self.assertEqual(a,b)
  self.assertEqual(a['total_equity'],300);self.assertEqual(a['verification_status'],'unverified_extraction')
  result=self.run_cli(bundle,'import-portfolio','--fixture','--file','valid/guided-research/portfolio-basic-hold.json')
  self.assertEqual(result.returncode,0,result.stdout)
  (data/'broken.json').write_text('{"bad": NaN}')
  result=self.run_cli(bundle,'analyze','--data-dir',str(data),'--file','broken.json')
  self.assertEqual(result.returncode,2,result.stdout)
 def test_symlink_source_refused(self):
  source=self.root/'source';shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('.git','__pycache__'))
  (source/'schemas/link.json').symlink_to(ROOT/'schemas/decision-case.v1.schema.json')
  with self.assertRaises(ValueError): bootstrap.install(source,self.root/'output')
 def test_render_identity_mismatch_refused(self):
  bundle=self.install();data=self.root/"private";data.mkdir()
  result=self.run_cli(bundle,"demo","--data-dir",str(data),"--report-id","other-company")
  self.assertEqual(result.returncode,2,result.stdout)
  self.assertEqual(list(data.iterdir()),[])
 def test_demo_two_revisions(self):
  bundle=self.install();data=self.root/'private';data.mkdir()
  for _ in range(2):
   result=self.run_cli(bundle,'demo','--data-dir',str(data));self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertTrue((data/'reports/workshop-cloud-synthetic/versions/v000002/report.html').is_file())
  html=(data/'reports/workshop-cloud-synthetic/versions/v000001/report.html').read_text()
  self.assertIn('synthetic',html.lower());self.assertIn('sketchnote',html.lower())
if __name__=='__main__': unittest.main()
