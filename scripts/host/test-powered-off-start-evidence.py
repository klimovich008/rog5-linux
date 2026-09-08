"""Synthetic S06 evidence: never contacts, powers off or starts a phone."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
HERE=Path(__file__).resolve().parent
P=load('powered_off_evidence_tests',HERE/'powered-off-start-evidence.py')
F=load('powered_off_fixture',HERE/'test-repeated-boot-evidence.py')
B=P.B

def fixture():
    boot,d,raw,base,record,producers,probe=F.fixture();c=boot['context'];end=boot['closure']
    host='33333333-3333-4333-8333-333333333333';nonce='a'*64
    operator=[]
    for event,text,when in [('ready','READY',99),('off-confirmed','OFF',104),
        ('start-requested','PRESS POWER ONCE',116),('started','STARTED',117)]:
        operator.append(dict(event=event,text=text+' '+nonce,monotonic=when,nonce=nonce,
            host_boot_id=host,origin='coordinator' if event=='start-requested' else 'operator'))
    samples=[dict(sequence=n,monotonic=when,host_boot_id=host,serial=c['identity']['serial'],
        usb_anchor=B.ROOT.D.CAPTURE.ANCHOR,mode='absent',interface=None) for n,when in enumerate(range(102,118,2),1)]
    c['physical']=dict(format='rog5-powered-off-conditions-v1',nonce=nonce,host_boot_id=host,
        source_boot_id=c['source_boot_id'],serial=c['identity']['serial'],usb_anchor=B.ROOT.D.CAPTURE.ANCHOR,
        conditions=dict(side_usb='connected throughout',external_power='host USB throughout',
            other_cables='none',start_method='one physical power-button press'),operator=operator,samples=samples)
    end.update(operation='powered-off-start-smoke',poweroff_returncode=end.pop('reboot_returncode'))
    def add(key,value):d[key]=value;raw[key]=json.dumps(value).encode()
    add('operator',operator);add('off_samples',samples)
    add('receiver',dict(d['receiver'],host_boot_id=host,deadline_monotonic=d['receiver']['deadline_monotonic']+90))
    add('receiver_check',dict(d['receiver_check'],receipt_sha256=B.sha(raw['receiver']),
        remaining_seconds=d['receiver_check']['remaining_seconds']+90))
    add('entry',dict(d['entry'],operation='installed release power-off and one operator start; no reboot substitution',
        receiver_receipt_sha256=B.sha(raw['receiver'])))
    add('close_intent',dict(d['close_intent'],context=c,decision=P.eligibility(base,c),
        receiver_receipt_sha256=B.sha(raw['receiver'])))
    d.pop('reboot');raw.pop('reboot')
    command='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+c['source_boot_id']+'; test "$(sha256sum /run/initramfs/shutdown | cut -d " " -f 1)" = '+producers['shutdown']+'; systemctl poweroff --no-block'
    add('poweroff',dict(returncode=0,script_sha256=B.sha(command.encode())))
    boot['component']=P.closed(base,c,end)
    return boot,d,raw,base,record,producers,probe

class PhysicalTests(unittest.TestCase):
    def check(self,v):
        return P.E.bind_boot(*v,B,P,kind='S06')
    def reject(self,change):
        values=copy.deepcopy(fixture());change(*values)
        with self.assertRaises((ValueError,KeyError,TypeError)):self.check(values)
    def test_complete_pinned_boot_component(self):
        v=fixture();self.check(v);result=P.closed(v[3],v[0]['context'],v[0]['closure'])
        self.assertEqual(result['boot_to_health_seconds'],74)
        self.assertFalse(result['s06_qualified']);self.assertFalse(result['release_qualified'])
    def test_reboot_does_not_qualify_as_poweroff(self):
        self.reject(lambda b,d,*rest:d['entry'].update(operation='ordinary installed release reboot; no RAM claim retry'))
        self.reject(lambda b,d,*rest:d['poweroff'].update(script_sha256='0'*64))
        self.reject(lambda b,d,*rest:b['closure'].update(operation='ordinary-boot-smoke'))
    def test_poweroff_acknowledgement_is_required(self):
        for value in (255,False,None):
            self.reject(lambda b,d,*rest:d['poweroff'].update(returncode=value))
    def test_operator_missing_stale_or_inferred(self):
        for event in range(4):
            for change in ({'text':'yes'},{'nonce':'b'*64},{'origin':'observer'},{'host_boot_id':'old'}):
                self.reject(lambda b,*rest:b['context']['physical']['operator'][event].update(change))
        self.reject(lambda b,*rest:b['context']['physical']['operator'].pop(1))
    def test_off_interval_and_timing_lattice(self):
        self.reject(lambda b,*rest:b['context']['physical']['operator'][1].update(monotonic=110))
        self.reject(lambda b,*rest:b['context']['physical']['operator'][2].update(monotonic=float('nan')))
        self.reject(lambda b,*rest:b['context']['physical']['operator'][3].update(monotonic=191))
        self.reject(lambda b,*rest:b['context'].update(observed_monotonic=417))
        self.reject(lambda b,*rest:b['closure'].update(finished_monotonic=521))
    def test_off_samples_have_no_gaps_ambiguity_or_other_device(self):
        for change in ({'mode':'enumerating'},{'mode':'target'},{'interface':'usb0'},
            {'serial':'other'},{'usb_anchor':'1-1.3'},{'host_boot_id':'old'},{'sequence':False}):
            self.reject(lambda b,*rest:b['context']['physical']['samples'][2].update(change))
        self.reject(lambda b,*rest:b['context']['physical']['samples'].pop(2))
        self.reject(lambda b,*rest:b['context']['physical']['samples'].pop())
    def test_changed_cables_and_power_are_not_off_proof(self):
        for key in ('side_usb','external_power','other_cables','start_method'):
            self.reject(lambda b,*rest:b['context']['physical']['conditions'].update({key:'unknown'}))
    def test_automatic_return_before_operator_start(self):
        self.reject(lambda b,*rest:b['context']['events'].insert(5,dict(event='transport',monotonic=110,mode='target')))
        self.reject(lambda b,*rest:b['context']['events'].insert(5,dict(event='transport',monotonic=110,mode='fastboot')))
        self.reject(lambda b,*rest:b['context']['events'][-1].update(monotonic=115))
    def test_failed_boot_and_stale_health_remain_failures(self):
        self.reject(lambda b,*rest:b['context']['events'][-1]['stage'].update(state='FAIL'))
        self.reject(lambda b,*rest:b['context']['health']['unit'].update(Result='exit-code'))
        self.reject(lambda b,*rest:b['context']['root']['blocks'].update(sda24='0'))
    def test_delayed_usb_cannot_hide_a_boot_before_the_start_request(self):
        v=fixture();c=v[0]['context'];c['health']['uptime']='75.0'
        with self.assertRaisesRegex(ValueError,'kernel boot predates'):
            P.eligibility(v[3],c)
    def test_failed_and_incomplete_capture_cleanup(self):
        self.reject(lambda b,*rest:b['closure']['events'][-1].update(status='FAIL'))
        self.reject(lambda b,*rest:b['closure']['events'].pop())
        self.reject(lambda b,*rest:b['closure'].update(receiver_returncode=1))
    def test_invalid_limits(self):
        original=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
        for update in ({'minimum_off_seconds':True},{'maximum_sample_gap_seconds':10},
            {'minimum_off_seconds':91},{'maximum_sample_gap_seconds':0}):
            changed=copy.deepcopy(original);changed['defaults']['powered_off_start'].update(update)
            with patch.object(B.ROOT.D.CAPTURE.ACCEPTANCE,'load_contract',return_value=changed):
                with self.assertRaises(ValueError):P.timing()

class EnvelopeTests(unittest.TestCase):
    def test_missing_or_tampered_evidence_stops_before_prerequisites(self):
        for mutation in ('roles','outer','nested'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);files={}
                for role in P.ROLES:
                    p=root/role;p.write_bytes(b'{}');files[role]=dict(path=str(p),sha256=B.sha(b'{}'))
                if mutation=='roles':files.pop('operator')
                p=root/'inputs';p.write_text(json.dumps(dict(format='rog5-powered-off-start-evidence-v1',files=files)))
                args=SimpleNamespace(inputs=p,inputs_sha256=B.sha(p.read_bytes()))
                if mutation=='outer':args.inputs_sha256='0'*64
                if mutation=='nested':(root/'off_samples').write_bytes(b'changed')
                with patch.object(B,'evaluate') as baseline:
                    with self.assertRaises(ValueError):P.evaluate(args,B)
                    baseline.assert_not_called()
    def test_complete_envelope_replays_all_raw_bindings(self):
        v=fixture();boot,d,raw,baseline,record,producers,probe=v
        boot['context']['source']['worktree_digest']=B.sha(boot['context']['source']['revision'].encode())
        manifest=b'kernel_sha256='+b'a'*64+b'\ndtb_sha256='+b'b'*64+b'\ninitramfs_sha256='+b'e'*64+b'\n'
        record['manifest_sha256']=B.sha(manifest)
        d['preflight']['manifest_sha256']=d['root']['manifest_sha256']=record['manifest_sha256']
        sources={key:(b'PROBE = "literal probe"\n' if key=='health' else b'# reviewed synthetic producer\n')
            for key in ('coordinator','preflight','health')}
        producers.update({key:B.sha(value) for key,value in sources.items()})
        producers.update(receiver=B.sha((HERE/'headless-stage-receiver.py').read_bytes()),
            deployed=B.sha((HERE/'check-deployed-server.py').read_bytes()),
            shutdown=B.sha((B.R/'initramfs/persistent-root-shutdown-standalone').read_bytes()))
        d['preflight'].update(observer_sha256=producers['preflight'],shutdown_sha256=producers['shutdown'])
        d['receiver']['receiver_sha256']=producers['receiver'];d['readiness']['runner_sha256']=producers['deployed']
        d['health']['runner_sha256']=producers['health'];d['entry']['supervisor_sha256']=producers['coordinator']
        hashes=dict(kernel='a'*64,dtb='b'*64,initramfs='e'*64,boot_bundle=record['boot_image_sha256'])
        baseline.update(artifact_hashes=hashes,original_source=boot['context']['source'],evidence_sha256={})
        boot['context']['artifact_hashes']=hashes
        raw.update(manifest=manifest,baseline=b'{}',s05=b'{}')
        raw.update({key+'_source':value for key,value in sources.items()})
        proof=dict(baseline,source=boot['context']['source'],inputs_sha256=B.sha(raw['baseline']),
            runner_sha256=B.sha(Path(B.__file__).read_bytes()))
        raw['baseline_proof']=json.dumps(proof).encode();d['entry']['baseline_sha256']=B.sha(raw['baseline_proof'])
        def encode(key):raw[key]=json.dumps(d[key]).encode()
        for key in ('preflight','receiver','root','readiness','health'):encode(key)
        d['entry'].update(preflight_sha256=B.sha(raw['preflight']),receiver_receipt_sha256=B.sha(raw['receiver']))
        d['receiver_check']['receipt_sha256']=B.sha(raw['receiver'])
        d['health']['root_sha256']=B.sha(raw['root']);encode('health')
        d['close_intent'].update(health_report_sha256=B.sha(raw['health']),receiver_receipt_sha256=B.sha(raw['receiver']),
            decision=P.eligibility(baseline,boot['context']))
        boot['component']=P.closed(baseline,boot['context'],boot['closure'])
        command='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot['context']['source_boot_id']+'; test "$(sha256sum /run/initramfs/shutdown | cut -d " " -f 1)" = '+producers['shutdown']+'; systemctl poweroff --no-block'
        d['poweroff']['script_sha256']=B.sha(command.encode())
        for key in d:encode(key)
        s05=dict(status='PASS',s05_qualified=True,identity=baseline['identity'])
        raw['run']=json.dumps(dict(source=boot['context']['source'],status='POWERED_OFF_COMPONENT_PASS',
            s06_qualified=False,release_qualified=False,s05=s05,boot=boot,started_monotonic=80,finished_monotonic=198)).encode()
        def original(command,**kwargs):return (B.R/command[-1].split(':',1)[1]).read_bytes()
        canonical=''.join(k+'='+value+'\n' for k,value in record.items()).encode()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);files={}
            for key,value in raw.items():
                path=root/key;path.write_bytes(value);files[key]=dict(path=str(path),sha256=B.sha(value))
            self.assertEqual(set(files),P.ROLES)
            inputs=root/'inputs';inputs.write_text(json.dumps(dict(format='rog5-powered-off-start-evidence-v1',files=files)))
            args=SimpleNamespace(inputs=inputs,inputs_sha256=B.sha(inputs.read_bytes()),candidate='fixture',
                artifact_hashes=','.join(k+'='+value for k,value in hashes.items()))
            with patch.object(B,'evaluate',return_value=baseline), patch.object(B,'load',return_value=SimpleNamespace(evaluate=lambda a:s05)), \
                 patch.object(P.subprocess,'check_output',side_effect=original), \
                 patch.object(B.ROOT.D.CAPTURE.CLAIMS,'expected_record',return_value=canonical):
                result=P.evaluate(args,B)
                self.assertTrue(result['s06_qualified']);self.assertFalse(result['release_qualified'])
                self.assertEqual(result['observed_seconds'],118)
                self.assertEqual(result['physical']['off_seconds'],12)
                self.assertEqual(set(result['evidence_sha256']),P.ROLES)
    def test_runtime_dispatch_uses_off_validator(self):
        runtime=load('cold_runtime_dispatch',HERE/'check-server-runtime-evidence.py')
        with patch.object(runtime,'load',return_value=SimpleNamespace(evaluate=lambda a,b:'off replay')) as loader:
            self.assertEqual(runtime.evaluate(SimpleNamespace(kind='S06')),'off replay')
            self.assertEqual(loader.call_args.args[1].name,'powered-off-start-evidence.py')

if __name__=='__main__':unittest.main()
