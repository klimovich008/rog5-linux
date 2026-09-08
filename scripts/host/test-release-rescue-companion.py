"""Explicit profile pairing and real dispatcher subprocess routing in fixtures."""
import copy,importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
S=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('staged_paired_release',S/'release-acceptance.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
class Tests(unittest.TestCase):
 def receipt(self,root):
  item=root/'artifact';item.write_bytes(b'exact artifact')
  artifact=dict(path=str(item),size=item.stat().st_size,sha256=M.sha_file(item))
  primary=dict(format='rog5-release-inputs-v1',candidate_id='server',source_revision='a'*40,
               artifacts={role:dict(artifact) for role in M.ARTIFACT_ROLES})
  companion=copy.deepcopy(primary);companion['candidate_id']='rescue'
  primary['rescue_companion']=companion
  return primary
 def test_explicit_pair_and_shared_inputs_checked_once(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);record=self.receipt(root);receipt=root/'receipt.json';receipt.write_text(json.dumps(record))
   result=M.verify_release(receipt)
   self.assertEqual(result['rescue_companion']['candidate_id'],'rescue')
   self.assertEqual(result['rescue_companion']['artifact_paths']['rootfs'],result['artifact_paths']['rootfs'])
   self.assertNotIn('root_upper',result['rescue_companion'])
 def test_pair_rejects_cross_kernel_root_source_or_overlay(self):
  for mutation in ('kernel','rootfs','path','source','same','upper','nested','missing','bad-hash'):
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);record=self.receipt(root);child=record['rescue_companion']
    if mutation in ('kernel','rootfs'):child['artifacts'][mutation]['sha256']='b'*64
    if mutation=='path':child['artifacts']['rootfs']['path']=str(root/'other')
    if mutation=='source':child['source_revision']='b'*40
    if mutation=='same':child['candidate_id']='server'
    if mutation=='upper':child['root_upper']=record['artifacts']['rootfs']
    if mutation=='nested':child['rescue_companion']={}
    if mutation=='missing':child['artifacts'].pop('dtb')
    if mutation=='bad-hash':child['artifacts']['initramfs']['sha256']='b'*64
    receipt=root/'receipt.json';receipt.write_text(json.dumps(record))
    with self.assertRaises(ValueError):M.verify_release(receipt)
 def test_companion_without_completed_evidence_cannot_contact_phone(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);record=self.receipt(root);p=root/'release.json';p.write_text(json.dumps(record));release=M.verify_release(p)
   for kind in ('H01','H02','H03'):
    test=next(t for t in M.load_contract()['tests'] if t['id']==kind)
    with patch.object(M.subprocess,'Popen') as process:
     row=M.run_one(test,root,release,rescue_inputs=root/'live-inputs')
     self.assertEqual(row['status'],'BLOCKED');process.assert_not_called()
 def test_each_rescue_row_uses_child_and_requires_full_bound_proof(self):
  for kind in ('H01','H02','H03'):
   for mutation in (None,'candidate','artifacts','source','flag','pin','runner'):
    with self.subTest(kind=kind,mutation=mutation),tempfile.TemporaryDirectory() as tmp:
     root=Path(tmp);record=self.receipt(root);receipt=root/'release.json';receipt.write_text(json.dumps(record));release=M.verify_release(receipt)
     folder=root/kind;folder.mkdir();inputs=root/'inputs';inputs.write_text('{}');pin=M.sha_file(inputs)
     runner=root/'scripts/host/rescue-runtime-evidence.py';runner.parent.mkdir(parents=True)
     runner.write_text('import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
     source=M.source_identity();proof=dict(status='PASS',source=source,candidate='rescue',
      artifact_hashes=M.qualification_hashes(release['rescue_companion']),inputs_sha256=pin,
      runner_sha256=M.sha_file(runner),original_source=dict(revision='b'*40),**{kind.lower()+'_qualified':True})
     if mutation=='candidate':proof['candidate']='server'
     if mutation=='artifacts':proof['artifact_hashes']={}
     if mutation=='source':proof['source']={}
     if mutation=='flag':proof[kind.lower()+'_qualified']=False
     if mutation=='pin':proof['inputs_sha256']='c'*64
     if mutation=='runner':proof['runner_sha256']='c'*64
     (folder/'result.json').write_text(json.dumps(proof))
     test=next(t for t in M.load_contract()['tests'] if t['id']==kind)
     with patch.object(M,'REPO',root):row=M.run_one(test,root,release,rescue_runtime_inputs=(inputs,pin))
     self.assertEqual(row['status'],'FAIL' if mutation else 'PASS',row)
     self.assertEqual(row['release_role'],'rescue_companion')
     command=row['commands'][0];self.assertEqual(command[command.index('--candidate')+1],'rescue')
     self.assertEqual(release['candidate_id'],'server')
 def test_live_and_completed_rescue_cli_arguments_cannot_mix(self):
  for tail in (['--rescue-runtime-inputs','/unused'],['--rescue-runtime-inputs','/unused','--rescue-runtime-inputs-sha256','a'*64,'--rescue-inputs','/live']):
   p=subprocess.run([sys.executable,str(S/'release-acceptance.py'),'release','--list',*tail],capture_output=True,timeout=5)
   self.assertEqual(p.returncode,2)
if __name__=='__main__':unittest.main()
