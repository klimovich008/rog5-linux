"""Pinned S05 replay regressions; synthetic data only, no device or credentials."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
HERE=Path(__file__).resolve().parent
E=load('repeated_evidence',HERE/'repeated-boot-evidence.py')
F=load('repeated_fixture',HERE/'test-ordinary-boot-smoke.py');M=F.M;B=M.B
def encoded(value):return json.dumps(value).encode()
def fixture():
 baseline,c,end=F.closed_fixture();source=c['source'];identity=c['identity'];record=c['record'];probe='literal probe'
 boot=dict(context=c,closure=end,preflight_monotonic=80,component=M.closed(baseline,c,end))
 producers={k:'a'*64 for k in ('preflight','coordinator','receiver','deployed','health','shutdown','baseline_proof')}
 d={};raw={}
 def add(key,value):d[key]=value;raw[key]=encoded(value)
 add('preflight',dict(source=source,status='PASS',source_boot_id=c['source_boot_id'],
  identity=dict(identity,boot_id=c['source_boot_id']),installed_boot_b_sha256=record['boot_image_sha256'],
  manifest_sha256=record['manifest_sha256'],observer_sha256=producers['preflight'],shutdown_sha256=producers['shutdown']))
 t=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()['defaults']['rescue_capture']
 required=t['recovery_seconds']+t['target_rollback_seconds']+t['cleanup_seconds']
 add('receiver',dict(source=source,format='rog5-headless-capture-v1',canonical_record=record,profile=record['candidate'],
  source_boot_id=c['source_boot_id'],receiver_sha256=producers['receiver'],required_seconds=required,
  started_monotonic=85,deadline_monotonic=85+required+t['preflight_seconds']))
 add('receiver_check',dict(status='PASS',test='H01-receiver',profile=record['candidate'],
  receipt_sha256=B.sha(raw['receiver']),remaining_seconds=required+10))
 add('entry',dict(source=source,operation='ordinary installed release reboot; no RAM claim retry',
  source_boot_id=c['source_boot_id'],monotonic=c['entry_monotonic'],artifact=record['boot_image_sha256'],
  preflight_sha256=B.sha(raw['preflight']),receiver_receipt_sha256=B.sha(raw['receiver']),
  baseline_sha256=producers['baseline_proof'],supervisor_sha256=producers['coordinator']))
 add('root_raw',c['root'])
 add('root',dict(source=source,status='PASS',identity=identity,manifest_sha256=record['manifest_sha256'],
  stdout_sha256=B.sha(raw['root_raw'])))
 add('readiness',dict(source=source,status='PASS',identity=identity,canonical_record=record,
  runner_sha256=producers['deployed'],actual=c['readiness']))
 paths=dict(descriptor='/run/rog5-native-wifi/trial-descriptor',healthy='/run/rog5-native-wifi/healthy.record',
  ssh='/run/rog5-persistent-ssh-identity.record');h=c['health']
 add('health_raw',dict(identity=identity,uptime=h['uptime'],files={paths[k]:v for k,v in h['files'].items()},
  unit=dict(returncode=0,stderr='',stdout=''.join(k+'='+v+'\n' for k,v in h['unit'].items()))))
 raw['health_stderr']=b''
 add('health',dict(source=source,status='PASS',identity=identity,returncode=0,root_sha256=B.sha(raw['root']),
  stdout_sha256=B.sha(raw['health_raw']),runner_sha256=producers['health'],actual=h,
  observed_monotonic=c['observed_monotonic'],healthy=M.health(h,identity),
  script_sha256=B.sha(('expected='+repr(identity)+'\n'+probe).encode())))
 add('close_intent',dict(monotonic=end['close_requested_monotonic'],context=c,health_report_sha256=B.sha(raw['health']),
  receiver_receipt_sha256=B.sha(raw['receiver']),decision=M.eligibility(baseline,c)))
 raw['events']=b''.join(encoded(e)+b'\n' for e in end['events'])
 add('capture_result',next(e for e in end['events'] if e['event']=='capture-ended'))
 command='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+c['source_boot_id']+'; test "$(sha256sum /run/initramfs/shutdown | cut -d " " -f 1)" = '+producers['shutdown']+'; systemctl reboot --no-block'
 add('reboot',dict(returncode=0,script_sha256=B.sha(command.encode())))
 for key,monotonic in zip(('host-before','host-at-entry','host-after-startup','host-after-capture'),(81,99,189,196.5)):
  add(key,dict(monotonic=monotonic,nfs_listening=False,listeners='',
   cef_socket='FragmentPath=/usr/lib/systemd/system/steam-web-debug-portforward.socket\nDropInPaths=\n'))
 return boot,d,raw,baseline,record,producers,probe
class Tests(unittest.TestCase):
 def check(self,values):return E.bind_boot(*values,B,M)
 def reject(self,change):
  values=copy.deepcopy(fixture());change(*values)
  with self.assertRaises((ValueError,KeyError,TypeError)):self.check(values)
 def test_complete_raw_component(self):self.check(fixture())
 def test_mixed_source_and_old_boot(self):
  self.reject(lambda b,d,*u:d['health'].update(source={}))
  self.reject(lambda b,d,*u:d['preflight'].update(source_boot_id=b['context']['identity']['boot_id']))
 def test_entry_and_producer_pins(self):
  for key in ('preflight_sha256','receiver_receipt_sha256','supervisor_sha256','baseline_sha256'):
   self.reject(lambda b,d,*u:d['entry'].update({key:'0'*64}))
 def test_full_failure_observation_still_required(self):
  self.reject(lambda b,d,*u:d['receiver'].update(deadline_monotonic=300))
  self.reject(lambda b,d,*u:d['receiver_check'].update(remaining_seconds=60))
 def test_raw_proofs_replayed(self):
  self.reject(lambda b,d,*u:d['root_raw']['power'].update(temp='401'))
  self.reject(lambda b,d,*u:d['readiness']['actual'].update(marker_metadata='0:0:644:regular file:1'))
  self.reject(lambda b,d,*u:d['health_raw']['unit'].update(returncode=1))
  self.reject(lambda b,d,*u:d['health'].update(script_sha256='0'*64))
 def test_ambiguous_command_and_changed_shutdown(self):
  self.reject(lambda b,d,*u:d['reboot'].update(returncode=None))
  self.reject(lambda b,d,*u:d['reboot'].update(returncode=False))
  self.reject(lambda b,d,*u:d['health_raw']['unit'].update(returncode=False))
  self.reject(lambda b,d,*u:d['preflight'].update(shutdown_sha256='0'*64))
 def test_truncated_changed_or_failed_capture(self):
  self.reject(lambda b,d,r,*u:r.update(events=r['events'][:-1]))
  self.reject(lambda b,d,*u:d['capture_result'].update(status='PASS'))
  self.reject(lambda b,d,*u:b['closure']['events'][-1].update(status='FAIL'))
 def test_host_services_and_ordering(self):
  self.reject(lambda b,d,*u:d['host-before'].update(nfs_listening=True))
  self.reject(lambda b,d,*u:d['host-after-capture'].update(monotonic=191))
 def test_missing_outer_roles_or_changed_pin_before_baseline(self):
  for mutation in ('roles','outer','nested'):
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);files={}
    for role in E.ROLES:
     p=root/role;p.write_bytes(b'{}');files[role]=dict(path=str(p),sha256=B.sha(b'{}'))
    if mutation=='roles':files.pop('3.events')
    p=root/'inputs';p.write_bytes(encoded(dict(format='rog5-repeated-boot-evidence-v1',files=files)))
    args=SimpleNamespace(inputs=p,inputs_sha256=B.sha(p.read_bytes()))
    if mutation=='outer':args.inputs_sha256='0'*64
    if mutation=='nested':(root/'run').write_bytes(b'changed')
    with patch.object(B,'evaluate') as baseline:
     with self.assertRaises(ValueError):E.evaluate(args,B)
     baseline.assert_not_called()
class SourceBindingTests(unittest.TestCase):
 def replay(self,changed_observer=False):
  # Exercise envelope/source selection independently of the boot predicates
  # already covered above. Historical shutdown source differs from both HEAD
  # and canonical installed bytes; only the canonical hash reaches bind_boot.
  source=dict(clean=True,revision='1'*40,worktree_digest=B.sha(('1'*40).encode()))
  installed=B.sha(b'canonical release shutdown')
  manifest=b'kernel_sha256='+b'a'*64+b'\ndtb_sha256='+b'b'*64+b'\ninitramfs_sha256='+b'c'*64+b'\n'
  canonical=dict(candidate='fixture',manifest_sha256=B.sha(manifest))
  baseline=dict(status='PASS',s01_qualified=True,identity={},candidate='fixture',
   artifact_hashes={},original_source=source,evidence_sha256={})
  proof=dict(baseline,source=source,inputs_sha256=B.sha(b'{}'),runner_sha256='a'*64)
  sequence=dict(identity={},observed_seconds=300,boot_ids=[])
  run=dict(source=source,status='SEQUENCE_COMPONENT_PASS',s05_qualified=False,release_qualified=False,
   boots=[{} for _ in range(3)],sequence=sequence,supervision_seconds=300)
  raw={role:b'{}' for role in E.ROLES}
  raw.update(run=encoded(run),baseline_proof=encoded(proof),manifest=manifest,health_source=b'PROBE = "fixture"\n')
  for n in range(1,4):raw[str(n)+'.receiver']=encoded(dict(host_boot_id='33333333-3333-4333-8333-333333333333'))
  def original(_source,path,pin=None):
   self.assertEqual(_source,source)
   if path=='initramfs/persistent-root-shutdown-standalone':return b'historical development shutdown'
   if changed_observer and path=='scripts/host/check-deployed-server.py':return b'changed observer'
   return (B.R/path).read_bytes()
  def binding(boot,data,payload,base,record,producers,*rest):
   self.assertEqual(producers['shutdown'],installed)
   self.assertNotEqual(producers['shutdown'],B.sha((B.R/'initramfs/persistent-root-shutdown-standalone').read_bytes()))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);files={}
   for role,value in raw.items():
    p=root/role;p.write_bytes(value);files[role]=dict(path=str(p),sha256=B.sha(value))
   inputs=root/'inputs';inputs.write_bytes(encoded(dict(format='rog5-repeated-boot-evidence-v1',files=files)))
   args=SimpleNamespace(inputs=inputs,inputs_sha256=B.sha(inputs.read_bytes()),candidate='fixture',artifact_hashes='kernel='+'a'*64+',dtb='+'b'*64+',initramfs='+'c'*64)
   with patch.object(B,'evaluate',return_value=baseline),patch.object(B,'original_bytes',side_effect=original), \
    patch.object(E.subprocess,'check_output',return_value=(B.R/'configs/release-acceptance.json').read_bytes()), \
    patch.object(B.ROOT.D.CAPTURE.CLAIMS,'expected_record',return_value=''.join(k+'='+v+'\n' for k,v in canonical.items()).encode()), \
    patch.object(B.ROOT.D,'expected_files',return_value={'shutdown':{'sha256':installed}}) as deployed, \
    patch.object(B,'load',return_value=SimpleNamespace(sequence=lambda *args:sequence)), \
    patch.object(E,'bind_boot',side_effect=binding) as bound:
     result=E.evaluate(args,B)
     self.assertTrue(result['s05_qualified']);self.assertEqual(bound.call_count,3)
     deployed.assert_called_once_with('fixture')
 def test_old_shutdown_source_keeps_canonical_installed_binding(self):self.replay()
 def test_changed_observer_still_refused(self):
  with self.assertRaisesRegex(ValueError,'changed observed dependency: scripts/host/check-deployed-server.py'):
   self.replay(changed_observer=True)

if __name__=='__main__':unittest.main()
