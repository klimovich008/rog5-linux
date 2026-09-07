"""Synthetic S04 evidence fixtures; no private logs or phone execution."""
import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
R=Path(__file__).resolve().parents[2]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
E=load('durability_evidence',Path(__file__).with_name('storage-durability-evidence.py'))
P=load('durability_phase_fixture',R/'scripts/host/run-durability-phase.py');B=P.B
OPS=load('durability_payload_fixture',R/'scripts/device/durability-file-ops.py')
SOURCES=P.sources();HASHES=P.hashes(SOURCES)
NONCE='1'*64
HASH=hashlib.sha256(b''.join(OPS.chunks(NONCE,64*1024**2))).hexdigest()
def encoded(value):return json.dumps(value).encode()
def fixture():
 root=B.load('durability_root_fixture',R/'scripts/host/test-check-standalone-root.py').Tests();root.setUp()
 origin=root.identity;identity=dict(origin,boot_id='22222222-2222-4222-8222-222222222222')
 source=dict(clean=True,revision='a'*40,worktree_digest='b'*64)
 plan=dict(nonce=NONCE)
 scope=dict(status='PASS',mutation='none',identity=origin,scope=dict(path='/persist',uid=0,gid=0,
  mode=0o755,dev=1793,inode=2,test_directory_exists=False))
 file=dict(name='s04-'+NONCE[:32],nonce=NONCE,sha256=HASH,parent_inode=12,directory_inode=13,
  file=dict(inode=14,size=64*1024**2,mode=0o400,uid=0,gid=0,nlink=1))
 prepared=dict(file=file,namespace_inode=12)
 d=dict(plan=plan,scope=scope);raw={k:encoded(v) for k,v in d.items()};previous=None
 for phase in E.PHASES:
  boot=origin['boot_id'] if phase=='prepare' else identity['boot_id']
  request=P.phase_request(plan,origin,scope,phase,boot,previous,HASHES,B.sha(raw['plan']))
  target=dict(status='PASS',phase=phase,identity=request['identity'],origin_boot_id=origin['boot_id'],
   nonce=NONCE,size=64*1024**2,prepared=copy.deepcopy(prepared),seconds=.1,ops_sha256=HASHES[P.SOURCES[0]])
  d[phase+'.stdout']=target;raw[phase+'.stdout']=encoded(target)
  script='REQUEST='+repr(request)+'\nOPS_SOURCE='+repr(SOURCES[P.SOURCES[0]].decode())+'\n'+SOURCES[P.SOURCES[1]].decode()
  report=dict(status='PASS',phase=phase,source=source,target_started=True,s04_qualified=False,
   release_qualified=False,script_hashes=HASHES,inputs_sha256=B.sha(raw['plan']),target=target,
   stdout_sha256=B.sha(raw[phase+'.stdout']),identity=request['identity'],script_sha256=B.sha(script.encode()),
   seconds=1,previous_sha256=None if previous is None else B.sha(raw[E.PHASES[E.PHASES.index(phase)-1]]))
  d[phase]=report;raw[phase]=encoded(report);previous=report
  d[phase+'.root']=copy.deepcopy(root.value);d[phase+'.root']['identity']=request['identity']
  raw[phase+'.root']=encoded(d[phase+'.root'])
 d['entry']=dict(source_boot_id=origin['boot_id'],monotonic=120);raw['entry']=encoded(d['entry'])
 d['started']=dict(monotonic=100,deadline_seconds=660,result_sha256=B.sha(raw['prepare']))
 d['cycle']=dict(status='PASS',source=source,origin_boot_id=origin['boot_id'],identity=identity,seconds=100,
  prepared_sha256=B.sha(raw['prepare']),verified_sha256=B.sha(raw['verify']),cleanup_sha256=B.sha(raw['cleanup']))
 before=dict(identity=origin)
 after=dict(identity=identity,original_source=source,boot_to_ssh_seconds=85,evidence_sha256=dict(entry=B.sha(raw['entry'])))
 return d,raw,before,after
class Tests(unittest.TestCase):
 def check(self,values):return E.check_phases(*values,HASHES,SOURCES,B,P,OPS)
 def reject(self,change):
  values=fixture();change(*values)
  with self.assertRaises((ValueError,KeyError,TypeError)):self.check(values)
 def test_complete_component(self):
  self.assertTrue(self.check(fixture())['s04_qualified'])
 def test_requires_distinct_boot_and_same_release(self):
  self.reject(lambda d,r,b,a:a.update(identity=b['identity']))
  self.reject(lambda d,r,b,a:a['identity'].update(bundle='another'))
 def test_missing_or_failed_phase(self):
  self.reject(lambda d,*unused:d.pop('cleanup'))
  self.reject(lambda d,*unused:d['verify'].update(status='FAIL'))
 def test_wrong_phase_or_source(self):
  self.reject(lambda d,*unused:d['verify'].update(phase='prepare'))
  self.reject(lambda d,*unused:d['verify'].update(source={}))
 def test_wrong_previous_pin(self):
  self.reject(lambda d,*unused:d['cleanup'].update(previous_sha256='0'*64))
 def test_altered_output_or_command(self):
  self.reject(lambda d,*unused:d['prepare'].update(stdout_sha256='0'*64))
  self.reject(lambda d,*unused:d['verify'].update(script_sha256='0'*64))
 def test_raw_root_rechecked(self):
  self.reject(lambda d,*unused:d['verify.root']['blocks'].update(sda24='0'))
  self.reject(lambda d,*unused:d['verify.root'].update(usb_online='0'))
 def test_deadline_and_phase_order(self):
  self.reject(lambda d,*unused:d['cycle'].update(seconds=661))
  self.reject(lambda d,*unused:d['cycle'].update(seconds=True))
  self.reject(lambda d,*unused:d['cycle'].update(seconds=1))
  self.reject(lambda d,*unused:d['started'].update(deadline_seconds=999))
  self.reject(lambda d,*unused:d['started'].update(monotonic=121))
 def test_entry_and_final_phase_records_bound(self):
  self.reject(lambda d,r,b,a:a['evidence_sha256'].update(entry='0'*64))
  self.reject(lambda d,*unused:d['cycle'].update(cleanup_sha256='0'*64))
 def test_release_flags_cannot_be_promoted(self):
  self.reject(lambda d,*unused:d['prepare'].update(release_qualified=True))
  self.reject(lambda d,*unused:d['prepare'].update(s04_qualified=True))

class OuterGateTests(unittest.TestCase):
 def outer(self,root):
  files={}
  for role in E.ROLES:
   path=root/role;path.write_bytes(b'{}')
   files[role]=dict(path=str(path),sha256=B.sha(path.read_bytes()))
  plan=dict(format='rog5-s04-file-plan-v1',candidate='fixture',artifact_hashes={'kernel':'a'*64},
   s01=dict(files['s01-before']),scope=dict(files['scope']))
  p=Path(files['plan']['path']);p.write_bytes(encoded(plan));files['plan']['sha256']=B.sha(p.read_bytes())
  p=root/'inputs.json';p.write_bytes(encoded(dict(format='rog5-storage-durability-evidence-v1',files=files)))
  return SimpleNamespace(inputs=p,inputs_sha256=B.sha(p.read_bytes()),candidate='fixture',artifact_hashes='kernel='+'a'*64),files
 def test_incomplete_capture_cannot_reach_file_component(self):
  for failed in (0,1):
   with self.subTest(failed=failed),tempfile.TemporaryDirectory() as tmp:
    args,files=self.outer(Path(tmp))
    replies=[dict(status='PASS',s01_qualified=True),dict(status='PASS',s01_qualified=True)]
    replies[failed]=dict(status='FAIL',s01_qualified=False)
    with patch.object(B,'evaluate',side_effect=replies),patch.object(E,'check_phases') as inner:
     with self.assertRaisesRegex(ValueError,'complete compatible'):E.evaluate(args,B)
     inner.assert_not_called()
 def test_missing_capture_roles_rejected_before_prerequisites(self):
  with tempfile.TemporaryDirectory() as tmp:
   args,files=self.outer(Path(tmp));files.pop('s01-after')
   args.inputs.write_bytes(encoded(dict(format='rog5-storage-durability-evidence-v1',files=files)))
   args.inputs_sha256=B.sha(args.inputs.read_bytes())
   with patch.object(B,'evaluate') as qualify:
    with self.assertRaisesRegex(ValueError,'roles'):E.evaluate(args,B)
    qualify.assert_not_called()
 def test_changed_nested_evidence_rejected_before_prerequisites(self):
  with tempfile.TemporaryDirectory() as tmp:
   args,files=self.outer(Path(tmp));Path(files['s01-after']['path']).write_bytes(b'{"changed":true}')
   with patch.object(B,'evaluate') as qualify:
    with self.assertRaisesRegex(ValueError,'hash mismatch'):E.evaluate(args,B)
    qualify.assert_not_called()
 def test_changed_outer_receipt_rejected_before_prerequisites(self):
  with tempfile.TemporaryDirectory() as tmp:
   args,files=self.outer(Path(tmp));args.inputs_sha256='0'*64
   with patch.object(B,'evaluate') as qualify:
    with self.assertRaisesRegex(ValueError,'hash mismatch'):E.evaluate(args,B)
    qualify.assert_not_called()
if __name__=='__main__':unittest.main()
