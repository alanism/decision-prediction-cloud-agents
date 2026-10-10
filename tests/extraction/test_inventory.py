"""Cloud-only distribution acceptance: source inventory, asset coverage, isolation."""
from pathlib import Path
import hashlib, importlib.util, json, re, unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('cloud_bootstrap',ROOT/'scripts/bootstrap_portable.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)
class InventoryTests(unittest.TestCase):
 def test_all_assets_are_installed(self):
  selected=set(bootstrap.selected_files(ROOT))
  for directory in ('skills','templates','design','schemas','docs','adapters/cloud/decision_cloud','vendor/capital-decision-lab/capital_decision_lab'):
   for p in (ROOT/directory).rglob('*'):
    if p.is_file() and '__pycache__' not in p.parts:
     self.assertIn(p.relative_to(ROOT).as_posix(),selected)
 def test_all_original_frameworks_pinned(self):
  data=json.loads((ROOT/'UPSTREAM.json').read_text());entries={x['path']:x for x in data['files']}
  for name in ('dlc','dlc-Galloway','dlc-Gerstner','dlc-camillo','dlc-laffont','dlc-mauboussin','dlc-munger-buffett','dlc-shkreli','dlc-thorp','dlc-page.md','LICENSE'):
   self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),entries[name]['source_working_sha256'],name)
 def test_math_and_contracts_preserved(self):
  data=json.loads((ROOT/'UPSTREAM.json').read_text())
  for row in data['files']:
   if row['path'].startswith('schemas/') or any('/'+x+'/' in row['path'] for x in ('formulas','contracts','simulation','model_thinking')):
    if row['path'].startswith('tests/'):continue
    self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['source_working_sha256'],row['path'])
 def test_no_desktop_setup_or_private_payload(self):
  for name in ('config.yaml','distribution.yaml','.env.EXAMPLE','local','plugins','scripts/build_profile_staging.py'):
   self.assertFalse((ROOT/name).exists(),name)
  for d in ('skills','design','templates','docs/platforms','docs/reports'):
   for p in (ROOT/d).rglob('*'):
    if p.is_file():
     t=p.read_text()
     for marker in ('/Users/','~/.hermes','notebooklm.google.com/notebook/','alanism_','libfile_'):
      self.assertNotIn(marker,t,str(p))
 def test_engine_adapter_separation(self):
  self.assertFalse((ROOT/'vendor/capital-decision-lab/capital_decision_lab/portable').exists())
  self.assertTrue((ROOT/'adapters/cloud/decision_cloud/cli.py').is_file())
  for p in (ROOT/'vendor/capital-decision-lab/capital_decision_lab').rglob('*.py'):
   self.assertNotIn('from decision_cloud',p.read_text(),str(p))
 def test_legacy_cli_cannot_discover_host_or_default_private_root(self):
  from capital_decision_lab.plugin import commands
  status, diagnostic=commands.doctor()
  self.assertEqual(status,0)
  self.assertFalse(diagnostic['native_integration'])
  self.assertFalse(hasattr(commands,'handle_cli'))
  status,result=commands.run_cli(['analyze','--case','anything.json'])
  self.assertEqual(status,2)
  self.assertEqual(result['issues'],[{'code':'EXPLICIT_DATA_ROOT_REQUIRED'}])
 def test_fixed_extraction_denominator(self):
  board=json.loads((ROOT/'docs/extraction/tasks.json').read_text())
  self.assertEqual(board['denominator'],10)
  self.assertEqual(len(board['tasks']),10)
  self.assertEqual(len({x['id'] for x in board['tasks']}),10)
  for row in board['tasks']:
   if row['status']=='done':self.assertTrue(row['evidence'])
 def test_current_policy_and_complete_design_set(self):
  for name in ('DESIGN-Monocle.md','DESIGN-Creative Giants.md','DESIGN-Ease Health.md','DESIGN-Stock-Report-Web.md','DESIGN-Stock-Report.md','hero-cards/andy-allen.md','hero-cards/satori-grid-layout-rubric.md'):
   self.assertTrue((ROOT/'design'/name).is_file(),name)
  for name in ('Stock-Report-Web-Template.html','Stock-Report-Template.html'):
   self.assertTrue((ROOT/'templates/stock-report'/name).is_file(),name)
 def test_pinned_source_hashes_and_patch_declarations(self):
  data=json.loads((ROOT/'UPSTREAM.json').read_text());patches={x['path'] for x in data['local_patches']}
  for row in data['files']:
   self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['extracted_sha256'],row['path'])
   if row['source_working_sha256']!=row['extracted_sha256']:self.assertIn(row['path'],patches)
if __name__=='__main__':unittest.main()
