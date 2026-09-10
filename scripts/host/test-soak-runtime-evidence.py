"""Evidence-index and prerequisite binding tests; synthetic data is never a live result."""
import copy,hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
HERE=Path(__file__).resolve().parent
REPO=Path(os.environ.get('ROG5_TEST_REPO',str(HERE.parents[1])))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
E=load('soak_evidence_index',HERE/'soak-runtime-evidence.py')
REAL=load('soak_evidence_pins',REPO/'scripts/host/check-standalone-boot.py')
O=load('soak_evidence_timing',REPO/'scripts/host/soak-observation.py')
sha=REAL.sha
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.contract=REAL.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
  self.source=dict(clean=True,revision='a'*40,worktree_digest='b'*64)
  self.identity=dict(serial='fixture',bundle='fixture',release='fixture',boot_id='11111111-1111-4111-8111-111111111111')
  self.data={role:('fixture '+role).encode() for role in E.FIXED}
  self.hashes={key:'c'*64 for key in ('kernel','dtb','rootfs','boot_bundle')};self.hashes['initramfs']=sha(self.data['archive'])
  self.data['manifest']=('bundle=fixture\ntarget_release=fixture\n'+''.join(key+'_sha256='+self.hashes[key]+'\n' for key in ('kernel','dtb','initramfs'))).encode()
  self.canonical=dict(serial='fixture',boot_image_sha256=self.hashes['boot_bundle'],manifest_sha256=sha(self.data['manifest']))
  files={}
  for path in (*E.SOURCES,'initramfs/native-wifi/runtime'):
   p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(path.encode());files[path]=sha(p.read_bytes())
  self.proofs={kind:dict(status='PASS',**{kind.lower()+'_qualified':True},identity=self.identity) for kind in ('S02','S04','S05')}
  self.ci=dict(status='PASS',source=self.source['revision'],returncode=0,terminal_completion_marker=True,source_unchanged=True,
   command=['scripts/host/rog5-dev','test','ci'],log_sha256=sha(b'PASS repository Linux ci tier\n'))
  self.started=dict(source=self.source['revision'],umask='0022',cwd=str(self.root),command=self.ci['command'])
  remote=dict(status='completed',conclusion='success',headSha=self.source['revision'],jobs=[dict(name=name,conclusion='success') for name in ('head-exact','merge-compat','candidate-publication','qemu-system')])
  self.run=dict(source=self.source,identity=self.identity,artifact_hashes=self.hashes,runner_sha256=sha(self.data['coordinator_source']),
   sources={p:files[p] for p in E.SOURCES},private_sources={role:sha(self.data[role]) for role in ('preparation_source','network_source','wifi_source','observer_source','preflight_source')},
   ci=dict(local=self.ci,remote=remote),prerequisites=self.proofs,seconds=3700,observation_started=50,observation_finished=3650,
   stats=dict(storage=[{}],network=[{}]))
  self.data['events']=b'{}\n'
  self.runtime=NS(evaluate=Mock(side_effect=lambda args:copy.deepcopy(self.proofs[args.kind])),T=object())
  self.rules=NS(timeline=Mock(),command_pairs=Mock(return_value=([],[],set())),observations=Mock(),storage=Mock(return_value=set()),network=Mock(return_value=set()))
  self.B=NS(R=self.root,sha=sha,require=REAL.require,pinned=REAL.pinned,READ=REAL.READ,
   ROOT=NS(D=NS(CAPTURE=NS(CLAIMS=NS(expected_record=lambda candidate:''.join(k+'='+v+'\n' for k,v in self.canonical.items()).encode(),verify_entered=Mock()),
    ACCEPTANCE=NS(load_contract=lambda:self.contract)))))
  def module(name,path):
   return {'soak-observation.py':O,'check-server-runtime-evidence.py':self.runtime,'soak-evidence-rules.py':self.rules}[Path(path).name]
  self.B.load=module
 def materialize(self):
  for role,value in (('run',self.run),('ci',self.ci),('ci_started',self.started)):self.data[role]=json.dumps(value).encode()
  self.data['ci_log']=b'PASS repository Linux ci tier\n'
  paths={}
  for role,raw in self.data.items():
   path=self.root/role;path.write_bytes(raw);paths[role]=dict(path=str(path),sha256=sha(raw))
  spec=dict(format='rog5-soak-evidence-v1',files=paths);self.inputs=self.root/'inputs.json';self.inputs.write_text(json.dumps(spec))
  return NS(inputs=self.inputs,inputs_sha256=sha(self.inputs.read_bytes()),candidate='fixture',artifact_hashes=','.join(k+'='+v for k,v in self.hashes.items()))
 def check(self,args=None):
  args=args or self.materialize()
  def show(command,**unused):
   path=command[-1].split(':',1)[1]
   return json.dumps(self.contract).encode() if path=='configs/release-acceptance.json' else (self.root/path).read_bytes()
  with patch.object(E.subprocess,'check_output',side_effect=show),patch.object(E,'scripts_and_boundaries'):
   return E.evaluate(args,self.B)
 def test_index_routes_all_mandatory_prerequisites_and_pure_rules(self):
  result=self.check();self.assertTrue(result['s07_qualified'])
  self.assertEqual([call.args[0].kind for call in self.runtime.evaluate.call_args_list],['S02','S04','S05'])
  for name in ('timeline','command_pairs','observations','storage','network'):getattr(self.rules,name).assert_called_once()
 def test_source_producer_and_ci_mismatch_are_rejected(self):
  changes=(lambda:self.run['source'].update(clean=False),lambda:self.run.update(runner_sha256='f'*64),
   lambda:self.run['sources'].update({E.SOURCES[0]:'f'*64}),lambda:self.run['private_sources'].update(network_source='f'*64),
   lambda:self.ci.update(returncode=False),lambda:self.ci.update(terminal_completion_marker=False),lambda:self.started.update(umask='0077'),
   lambda:self.run['ci']['remote']['jobs'].pop())
  for change in changes:
   with self.subTest(change=change):
    self.setUp();change()
    with self.assertRaises(ValueError):self.check()
 def test_failed_or_different_prerequisite_cannot_be_relabelled(self):
  for kind in ('S02','S04','S05'):
   with self.subTest(kind=kind):
    self.setUp();self.runtime.evaluate.side_effect=lambda args:dict(self.proofs[args.kind],status='FAIL') if args.kind==kind else self.proofs[args.kind]
    with self.assertRaises(ValueError):self.check()
 def test_changed_prerequisite_details_or_last_boot_are_rejected(self):
  self.runtime.evaluate.side_effect=lambda args:dict(self.proofs[args.kind],extra='different')
  with self.assertRaises(ValueError):self.check()
 def test_combined_file_size_is_bounded_before_replay(self):
  with patch.object(E,'RAW_LIMIT',32),self.assertRaisesRegex(ValueError,'memory bound'):
   self.check()
  self.runtime.evaluate.assert_not_called()
 def test_changed_file_during_replay_is_rejected(self):
  args=self.materialize()
  self.rules.observations.side_effect=lambda *unused:(self.root/'network_source').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check(args)
 def test_extra_missing_truncated_and_unpinned_files_are_rejected(self):
  for mutation in ('extra','missing','truncated','pin'):
   with self.subTest(mutation=mutation):
    self.setUp();args=self.materialize();spec=json.loads(self.inputs.read_text())
    if mutation=='extra':spec['files']['unrequested']=spec['files']['events']
    elif mutation=='missing':del spec['files']['s05']
    elif mutation=='truncated':
     (self.root/'events').write_bytes(b'{}');spec['files']['events']['sha256']=sha(b'{}')
    else:spec['files']['run']['sha256']='f'*64
    self.inputs.write_text(json.dumps(spec));args.inputs_sha256=sha(self.inputs.read_bytes())
    with self.assertRaises(ValueError):self.check(args)
if __name__=='__main__':unittest.main()
