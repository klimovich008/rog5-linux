"""Offline fixtures only: synthetic closing events never count as live evidence."""
import copy,hashlib,importlib.util,json,unittest,tempfile,os,subprocess,sys
from unittest import mock
from pathlib import Path
W=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('ordinary_evidence_fixture',W/'check-standalone-boot.py')
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
def fixture():
 # Sanitized fixtures reuse the real root/readiness validators; no private logs.
 root_test=M.load('root_fixture',M.R/'scripts/host/test-check-standalone-root.py').Tests()
 root_test.setUp()
 ready_test=M.load('ready_fixture',M.R/'scripts/host/test-check-deployed-server.py').ReadinessTests()
 ready_test.setUp()
 identity=dict(ready_test.identity,serial='fixture')
 root_test.value['identity']=identity.copy()
 old='22222222-2222-4222-8222-222222222222';boot=identity['boot_id']
 source=dict(clean=True,revision='a'*40,worktree_digest='b'*64)
 record=dict(serial=identity['serial'],target_bundle=identity['bundle'],candidate='fixture',
  manifest_sha256='c'*64,boot_image_sha256='d'*64,execution='fastboot-boot-selector-trial')
 hashes=dict(preflight='e'*64,receipt='f'*64,root_raw='1'*64,manifest='c'*64)
 producers=dict(supervisor='2'*64,preflight='3'*64,receiver='4'*64,deployed='5'*64)
 receipt=dict(format='rog5-headless-capture-v1',source=source,canonical_record=record,profile='fixture',
  source_boot_id=old,required_seconds=1320,started_monotonic=90,deadline_monotonic=1470,
  receiver_sha256=producers['receiver'])
 begin=100;end=1471
 entry=dict(source=source,source_boot_id=old,artifact=record['boot_image_sha256'],
  preflight_sha256=hashes['preflight'],receiver_receipt_sha256=hashes['receipt'],
  operation='ordinary installed release reboot; no RAM claim retry',
  supervisor_sha256=producers['supervisor'],monotonic=begin)
 root=dict(source=source,identity=identity,status='PASS',manifest_sha256=hashes['manifest'],stdout_sha256=hashes['root_raw'])
 startup=dict(source=source,identity=identity,status='LOCAL_ROOT_PASS_CAPTURE_PENDING',
  boot_requested=True,reboot_returncode=0,boot_to_ssh_seconds=85)
 stage=dict(boot_id=boot,sequence=1,stage='switch-root',state='PASS',detail='none')
 events=[dict(event=name,monotonic=begin-5+i) for i,name in enumerate(M.READ.PREPARED)]
 events += [dict(event='source-disconnected',source_boot_id=old,monotonic=101),
  dict(event='transport',mode='target',monotonic=120),
  dict(event='stage',stage=stage,monotonic=140)]
 finish=dict(status='NOT RUN',duration_seconds=end-90,source_disconnected=True,source_boot_id=old,last_stage=stage)
 events += [dict(event='capture-ended',monotonic=end,**finish)]
 events += [dict(event='host-cleanup',item=name,status='PASS',monotonic=end+1+i)
  for i,name in enumerate(('route','firewall','profile','address'))]
 hosts=[dict(monotonic=t,nfs_listening=False,
  listeners='LISTEN 0 10 127.0.0.1:8080 *:* users:(("steamwebhelper",pid=10,fd=1))',
  cef_socket='FragmentPath=/usr/lib/systemd/system/steam-web-debug-portforward.socket\nDropInPaths=')
  for t in (85,99,180,1480)]
 ready=dict(status='PASS',source=source,identity=identity,canonical_record=record,
  runner_sha256=producers['deployed'],actual=dict(ready_test.value,
   marker=ready_test.value['marker']+'\nattested_boot_id='+boot))
 d=dict(receipt=receipt,entry=entry,root=root,root_raw=root_test.value,startup=startup,
  supervision=dict(startup,receiver_returncode=0),events=events,capture_result=finish,hosts=hosts,
  readiness=ready,manifest=dict(bundle=identity['bundle'],target_release=identity['release']),
  receiver_check=dict(status='PASS',test='H01-receiver',profile='fixture',receipt_sha256=hashes['receipt'],remaining_seconds=1380),
  preflight=dict(source=source,status='PASS',source_boot_id=old,identity=dict(identity,boot_id=old),
   installed_boot_b_sha256=record['boot_image_sha256'],manifest_sha256=hashes['manifest'],observer_sha256=producers['preflight']))
 return d,record,hashes,producers
class Tests(unittest.TestCase):
 def setUp(self):self.d,self.record,self.hashes,self.producers=fixture()
 def run_case(self):return M.qualify(self.d,self.record,self.hashes,self.producers)
 def reject(self):
  with self.assertRaises((ValueError,KeyError,TypeError)):self.run_case()
 def test_valid_fixture_is_one_boot_not_release(self):
  r=self.run_case();self.assertTrue(r['s01_qualified']);self.assertFalse(r['release_qualified'])
 def test_missing_closure(self):del self.d['supervision']['receiver_returncode'];self.reject()
 def test_shortened_window(self):self.d['capture_result']['duration_seconds']=1;self.reject()
 def test_ambiguous_request(self):self.d['supervision']['reboot_returncode']=255;self.reject()
 def test_old_boot(self):self.d['entry']['source_boot_id']=self.d['root']['identity']['boot_id'];self.reject()
 def test_mixed_revision(self):self.d['entry']['source']={};self.reject()
 def test_changed_receipt(self):self.hashes['receipt']='0'*64;self.reject()
 def test_changed_producer(self):self.producers['supervisor']='0'*64;self.reject()
 def test_wrong_signed_kernel(self):self.d['manifest']['target_release']='wrong-kernel';self.reject()
 def test_host_nfs_even_with_false_summary(self):
  self.d['hosts'][0]['listeners']+='\nLISTEN 0 10 0.0.0.0:2049 *:*';self.reject()
 def test_wrong_bundle_listener(self):
  self.d['hosts'][0]['listeners']=self.d['hosts'][0]['listeners'].replace('steamwebhelper','server');self.reject()
 def test_failed_cleanup(self):self.d['events'][-1]['status']='FAIL';self.reject()
 def test_failed_capture(self):self.d['capture_result']['status']='FAIL';self.reject()
 def test_missing_disconnect(self):self.d['events']=[e for e in self.d['events'] if e['event']!='source-disconnected'];self.reject()
 def test_post_target_transport_loss(self):
  self.d['events'].insert(7,dict(event='transport',mode='absent',monotonic=self.d['entry']['monotonic']+50));self.reject()
 def test_no_early_handover(self):self.d['events']=[e for e in self.d['events'] if e['event']!='stage'];self.reject()
 def test_bad_timing_types_and_deadline(self):
  for value in (True,float('nan'),float('inf'),301):
   with self.subTest(value=value):self.d['startup']['boot_to_ssh_seconds']=value;self.reject()
 def test_root_network_dependency(self):
  self.d['root_raw']['mountinfo']+='90 37 0:90 / /other rw - nfs host:/root rw\n';self.reject()
 def test_unsafe_power(self):self.d['root_raw']['power']['temp']='401';self.reject()
 def test_legacy_unbound_readiness(self):
  self.d['readiness']['actual']['marker']=self.d['readiness']['actual']['marker'].split('\nattested_boot_id=')[0];self.reject()
 def test_receipt_window_cannot_be_invented(self):
  self.d['receipt']['deadline_monotonic']=200;self.reject()
 def test_no_reboot_option_or_credential_use_in_entry_point(self):
  p=subprocess.run([str(M.R/'scripts/host/rog5-dev'),'check-standalone-boot','--help'],capture_output=True,text=True,timeout=5)
  self.assertEqual(p.returncode,0,p.stderr);self.assertIn('--inputs-sha256',p.stdout)
  self.assertNotIn('--reboot',p.stdout);self.assertNotIn('--identity-file',p.stdout)

class PinnedReplayTests(unittest.TestCase):
 def prepare(self,path):
  d,record,_,_=fixture()
  hashes={k:'a'*64 for k in ('kernel','dtb','initramfs','rootfs','boot_bundle')}
  hashes['boot_bundle']=record['boot_image_sha256']
  d['manifest'].update({k+'_sha256':hashes[k] for k in ('kernel','dtb','initramfs')})
  manifest=''.join(k+'='+v+'\n' for k,v in d['manifest'].items()).encode()
  record['manifest_sha256']=M.sha(manifest)
  d['preflight']['manifest_sha256']=d['root']['manifest_sha256']=M.sha(manifest)
  d['entry']['supervisor_sha256']=d['preflight']['observer_sha256']=M.sha(b'reviewed fixture source')
  d['receipt']['receiver_sha256']=M.sha((M.R/'scripts/host/headless-stage-receiver.py').read_bytes())
  d['readiness']['runner_sha256']=M.sha((M.R/'scripts/host/check-deployed-server.py').read_bytes())
  payload={k:json.dumps(v).encode() for k,v in d.items() if k not in ('events','hosts','manifest')}
  d['root']['stdout_sha256']=M.sha(payload['root_raw'])
  payload['root']=json.dumps(d['root']).encode()
  d['entry']['preflight_sha256']=M.sha(payload['preflight'])
  d['entry']['receiver_receipt_sha256']=d['receiver_check']['receipt_sha256']=M.sha(payload['receipt'])
  payload['entry']=json.dumps(d['entry']).encode();payload['receiver_check']=json.dumps(d['receiver_check']).encode()
  payload.update(manifest=manifest,events=b''.join(json.dumps(e).encode()+b'\n' for e in d['events']),
   supervisor_source=b'reviewed fixture source',preflight_source=b'reviewed fixture source',
   composition=json.dumps(dict(status='PASS',a01_qualified=True,candidate='fixture',artifact_hashes=hashes)).encode())
  payload.update({'host-'+str(i):json.dumps(h).encode() for i,h in enumerate(d['hosts'])})
  entries={}
  for name,raw in payload.items():
   target=path/name;target.write_bytes(raw);target.chmod(0o600)
   entries[name]=dict(path=str(target),sha256=M.sha(raw))
  inputs=path/'inputs.json';inputs.write_text(json.dumps(dict(format='rog5-standalone-boot-evidence-v1',files=entries)));inputs.chmod(0o600)
  return inputs,M.sha(inputs.read_bytes()),record,hashes
 def test_real_file_reader_valid_and_hostile_inputs(self):
  for mutation in ('none','altered','symlink','missing','wrong-composition','duplicate'):
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);inputs,pin,record,hashes=self.prepare(root)
    if mutation=='altered':(root/'root_raw').write_text('{}')
    if mutation=='symlink':
     (root/'root_raw').rename(root/'original');(root/'root_raw').symlink_to(root/'original')
    if mutation=='missing':(root/'supervision').unlink()
    if mutation=='wrong-composition':hashes['rootfs']='f'*64
    if mutation=='duplicate':
     inputs.write_text('{"files":{},"files":{}}');pin=M.sha(inputs.read_bytes())
    canonical=''.join(k+'='+v+'\n' for k,v in record.items()).encode()
    with mock.patch.object(M.ROOT.D.CAPTURE.CLAIMS,'expected_record',return_value=canonical), \
         mock.patch.object(M.ROOT.D.CAPTURE.CLAIMS,'verify_entered') as claim, \
         mock.patch.object(M.subprocess,'check_output',side_effect=lambda args,**kw:(M.R/args[-1].split(':',1)[1]).read_bytes()):
     if mutation=='none':
      result=M.evaluate(inputs,pin,'fixture',hashes);self.assertTrue(result['s01_qualified']);claim.assert_called_once_with('fixture')
     else:
      with self.assertRaises((ValueError,OSError)):M.evaluate(inputs,pin,'fixture',hashes)
 def test_cli_missing_completed_evidence_is_blocked_under_both_interpreters(self):
  for optimized in ([],['-O']):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    p=subprocess.run([sys.executable,*optimized,str(M.R/'scripts/host/check-standalone-boot.py'),
     '--inputs',str(root/'missing'),'--inputs-sha256','a'*64,'--candidate','fixture',
     '--artifact-hashes','kernel='+'b'*64,'--output',str(root/'output')],capture_output=True,text=True,timeout=5)
    self.assertEqual(p.returncode,3,p.stderr)
    result=json.loads((root/'output/result.json').read_text())
    self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['s01_qualified'])
if __name__=='__main__':unittest.main()
