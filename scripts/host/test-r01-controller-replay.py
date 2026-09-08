#!/usr/bin/env python3
"""Whole retained-controller replay with synthetic commands; no live authority.

Only the canonical candidate, frozen source and signed-return lookup are
fixtures. Raw command, negative state, root, readiness, journal, capture and
ordinary closure validators execute normally. No producer script is executed.
"""
import copy
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


M=load('whole_r01_consumer','check-isolated-recovery.py')
F=load('whole_r01_frames','test-check-isolated-recovery.py')
N=load('whole_r01_negative','test-isolated-recovery-observation.py')
O=load('whole_r01_ordinary','test-ordinary-boot-smoke.py')
T=load('whole_r01_root','test-check-standalone-root.py')
SOURCE=dict(clean=True,revision='a'*40,worktree_digest='b'*64)
PRIMARY=dict(candidate=M.PRIMARY,target_bundle=M.PRIMARY,serial='fixture',
             execution='fastboot-boot-selector-trial',manifest_sha256='c'*64,boot_image_sha256='d'*64,
             trial_id='e'*64,fallback_bundle=M.FALLBACK,fallback_manifest_sha256='f'*64)
NEG=dict(F.NEG,bundle='fixture-negative',release='7.1.4-negative')
BACK=dict(F.BACK,bundle=M.FALLBACK,release='7.1.4-g359318de534f')
RETURN=dict(bundle=BACK['bundle'],release=BACK['release'],manifest_sha256=PRIMARY['fallback_manifest_sha256'])
BEFORE=dict(boot_id='33333333-3333-4333-8333-333333333333',bundle=M.PRIMARY,release=NEG['release'])
AFTER=dict(boot_id='44444444-4444-4444-8444-444444444444',bundle=M.PRIMARY,release=NEG['release'])
CANONICAL=dict(candidate=NEG['bundle'],target_bundle=NEG['bundle'],qualification='isolated-failure-r01',
               execution='fastboot-boot-ram-bundle',fallback_bundle=M.FALLBACK,
               fallback_manifest_sha256=PRIMARY['fallback_manifest_sha256'])
DEPLOYED=dict(runtime=dict(status='present',path='/run/rog5-native-wifi/runtime',size=10,
                           sha256='a'*64,mode=0o755,uid=0,gid=0,nlink=1))


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    return dict(path=str(path),sha256=M.digest(path.read_bytes()))


def save_command(directory,name,stdout=b'',*,stamp=1000,returncode=0,stderr=b''):
    source=b'# synthetic command; never executed\n'
    for suffix,payload in (('stdout',stdout),('stderr',stderr),('script',source)):
        (directory/(name+'.'+suffix)).write_bytes(payload)
    return dump(directory/(name+'-command.json'),dict(returncode=returncode,timeout=False,
        stdout_sha256=M.digest(stdout),stderr_sha256=M.digest(stderr),script_sha256=M.digest(source),retained_monotonic=stamp))


def ready(identity):
    return dict(boot_before=identity['boot_id'],boot_after=identity['boot_id'],kernel=identity['release'],
                bundle=identity['bundle'],run_fstype='tmpfs',marker_metadata='0:0:444:regular file:1',
                ssh_identity_service='active',marker='status=PASS\nkernel='+identity['release']+
                '\nssh=strict-key-only\nattested_boot_id='+identity['boot_id']+'\n')


def ready_raw(value):return b'\0'.join(value[key].encode() for key in M.ROOT.D.READINESS_KEYS)+b'\0'


def root(identity):
    test=T.Tests();test.setUp();value=test.value;value['identity']=identity.copy();return value


def fixture(directory):
    directory.mkdir();work=directory.parent
    trial=dict(trial_id=PRIMARY['trial_id'],primary_bundle=M.PRIMARY,primary_manifest_sha256=PRIMARY['manifest_sha256'],
               fallback_bundle=M.FALLBACK,fallback_manifest_sha256=PRIMARY['fallback_manifest_sha256'])
    def state(state):return M.digest(''.join(key+'='+value+'\n' for key,value in
        dict(format='rog5-persistent-wifi-trial-v1',**trial,state=state).items()).encode())
    context=dict(source=BEFORE,rescue={key:BACK[key] for key in ('bundle','release')},
                 pending_sha256=state('pending'),healthy_sha256=state('healthy'))
    dump(directory/'context.json',dict(context=context,started_monotonic=890))
    private_sources={}
    for name in M.PRIVATE_SOURCES:
        private=work/name;private.write_text('# synthetic producer fixture, never executed\n')
        private_sources[name]=M.digest(private.read_bytes())
    checks=dump(work/'controller-checks.json',dict(status='PASS',complete_driver_bindings=True,private_sources=private_sources))
    external=work/'fixture-fastboot-identity.py';external.write_text('# synthetic read-only identity producer\n')
    c=dict(format='rog5-r01-live-admission-v1',candidate=NEG['bundle'],source=SOURCE,source_identity=BEFORE,lifecycle_uid=1000,
           private_sources=private_sources,public_sources=M.source_closure(),controller_checks=checks,
           external_sources=dict(fastboot_identity=dict(path=str(external),sha256=M.digest(external.read_bytes()))),
           checker=dict(path=str(HERE/'check-isolated-recovery.py'),sha256=M.digest((HERE/'check-isolated-recovery.py').read_bytes())),
           negative_trial_id=N.TRIAL,negative_sealed=N.SEALED,fallback_manifest=str(work/'fixture-manifest'))
    with patch.object(F,'NEG',NEG),patch.object(F,'BACK',BACK),patch.object(F,'RETURN',RETURN):
        cycle=F.fixture();journal=F.raw(F.stream())
    receipt=cycle['receipt'];receipt.update(canonical_record=CANONICAL,source=SOURCE,
        receiver_sha256=M.digest((HERE/'capture-isolated-recovery.py').read_bytes()),
        framework_sha256=M.digest((HERE/'headless-stage-receiver.py').read_bytes()))
    dump(directory/'capture/receipt.json',receipt)
    capture_raw=F.raw(cycle['events']);(directory/'capture/events.jsonl').write_bytes(capture_raw)
    results={name:dict(status='PASS') for name in M.PHASES}
    results['execute'].update(canonical_record=CANONICAL,entry_monotonic=cycle['entry'])
    results['close_capture'].update(events_sha256=M.digest(capture_raw),receiver_returncode=0,full_lifetime=True)
    results['ordinary_verify'].update(identity=AFTER)
    observe=results['observe'];observe.update(negative_identity=NEG,identity=BACK,
        physical_return_monotonic=cycle['returned'],samples=[])
    (directory/'rollback-stream.stdout').write_bytes(journal)
    (directory/'rollback-stream.stderr').write_bytes(b'Connection closed\n')
    (directory/'rollback-stream.script').write_bytes(b'# synthetic stream\n')
    dump(directory/'rollback-stream-started.json',dict(identity=NEG,monotonic=1113,
        script_sha256=M.digest((directory/'rollback-stream.script').read_bytes())))
    dump(directory/'rollback-stream-result.json',dict(returncode=255,stdout_sha256=M.digest(journal),
        stderr_sha256=M.digest((directory/'rollback-stream.stderr').read_bytes())))
    for name,identity in (('source-root',BEFORE),('negative-root',NEG)):
        save_command(directory,name,json.dumps(root(identity)).encode())
    save_command(directory,'source-deployed',json.dumps(dict(BEFORE,files=DEPLOYED)).encode())
    save_command(directory,'source-ready',ready_raw(ready(BEFORE)))
    save_command(directory,'source-state',json.dumps(dict(status='PASS',identity=BEFORE,healthy_sha256=state('healthy'))).encode())
    save_command(directory,'source-installed',b'PASS-installed\n')
    for label,identity in (('source-reset',BEFORE),('rescue-reset',BACK)):
        observation='format|rog5-r01-reset-observation-v1\nidentity|'+identity['boot_id']+'|'+identity['release']+'|'+identity['bundle']+'\n'
        observation+='cmdline|'+('rog5.bundle='+identity['bundle']).encode().hex()+'\n'
        observation+='directory|/sys/fs/pstore|unsupported\ndirectory|/mnt/pstore|absent\nboot_after|'+identity['boot_id']+'\n'
        save_command(directory,label,observation.encode())
    save_command(directory,'arm-state',json.dumps(dict(identity=BEFORE,before_sha256=state('healthy'),after_sha256=state('pending'))).encode())
    save_command(directory,'source-fastboot',F.raw([dict(event='transition-ready',pending_sha256=state('pending')),
                                                  dict(event='reboot-request-returned',returncode=0)]))
    save_command(directory,'execute',b'CLAIM_CONSUMED\nFASTBOOT_ACCEPTED\n')
    for key,prefix,identity,stamp in (('negative_ready','negative-ready',NEG,1111),('return_ready','return-ready',BACK,2010)):
        actual=ready(identity);observe[key]=dict(command=prefix+'-1',actual=actual,monotonic=stamp)
        save_command(directory,prefix+'-1',ready_raw(actual),stamp=stamp)
    with patch.object(N,'IDENTITY',NEG),patch.object(N,'INSTALLED',trial):negative=N.fixture()
    save_command(directory,'negative-health-wait-1',json.dumps(negative).encode(),stamp=1112)
    for index,sample in enumerate(cycle['samples'],1):
        actual=copy.deepcopy(negative);actual['uptime']=sample['uptime'];name='negative-sample-'+str(index)
        save_command(directory,name,json.dumps(actual).encode(),stamp=sample['finished_monotonic'])
        proof=M.OBS.negative(actual,NEG,N.TRIAL,trial,N.SEALED)
        observe['samples'].append(dict(command=name,proof=proof,**{k:sample[k] for k in ('started_monotonic','finished_monotonic')}))
    for name in ('return-guard','rescue-fresh-guard','restore-fresh-guard','ordinary-source-guard'):
        save_command(directory,name,b'PASS-V11-guard\n',stamp=2012 if name=='return-guard' else 2401)
    save_command(directory,'rescue-fresh-ready',ready_raw(ready(BACK)),stamp=2391)
    save_command(directory,'restore-directory',b'PASS-owned-directory\n')
    save_command(directory,'restore-helper',b'PASS-helper-staged\n')
    restored=dict(format='rog5-r01-selection-restoration-v1',entered='true',boot_id=BACK['boot_id'],
        before_sha256=state('pending'),completed='true',after_sha256=state('healthy'),
        selection_eligibility_restored='true',release_qualified='false')
    save_command(directory,'restore-state',''.join(k+'='+v+'\n' for k,v in restored.items()).encode())
    save_command(directory,'restore-cleanup',b'PASS-helper-cleaned\n')
    save_command(directory,'ordinary-state',b'PASS-ordinary-state\n')
    save_command(directory,'ordinary-installed',b'PASS-installed\n')
    save_command(directory,'ordinary-reboot')
    baseline,smoke,closure=O.closed_fixture();old=smoke['identity'];old_source=smoke['source_boot_id']
    changes={old['boot_id']:AFTER['boot_id'],old_source:BACK['boot_id'],old['bundle']:AFTER['bundle'],
             old['release']:AFTER['release'],'1'*64:PRIMARY['trial_id']}
    clocks={'monotonic','entry_monotonic','observed_monotonic','close_requested_monotonic','finished_monotonic'}
    def adapt(value):
        if isinstance(value,dict):return {key:(item+2400 if key in clocks else adapt(item)) for key,item in value.items()}
        if isinstance(value,list):return [adapt(item) for item in value]
        if isinstance(value,str):
            for old,new in changes.items():value=value.replace(old,new)
        return value
    baseline,smoke,closure=adapt(baseline),adapt(smoke),adapt(closure)
    identity=dict(AFTER,serial=PRIMARY['serial']);baseline.update(candidate=M.PRIMARY,identity=dict(identity,boot_id=BACK['boot_id']),
        artifact_hashes=dict(boot_bundle=PRIMARY['boot_image_sha256'],kernel='a'*64,dtb='1'*64,
                             initramfs='2'*64,rootfs='3'*64,root_upper='4'*64))
    smoke.update(identity=identity,source=SOURCE,record=PRIMARY,artifact_hashes=baseline['artifact_hashes'])
    smoke['root']['identity']=identity;smoke['health']['identity']=identity
    smoke['readiness']=ready(identity);closure.update(identity=identity,source=SOURCE)
    c['ordinary_baseline']=dump(work/'baseline.json',baseline)
    c['ordinary_baseline_inputs']=dump(work/'fixture-ordinary-inputs.json',dict(fixture=True))
    save_command(directory,'ordinary-root',json.dumps(smoke['root']).encode(),stamp=2585)
    save_command(directory,'ordinary-ready-1',ready_raw(smoke['readiness']),stamp=2580)
    healthy=smoke['health'];raw_health=dict(identity=identity,uptime=healthy['uptime'],
        files={M.OBS.MARKERS[key]:item for key,item in healthy['files'].items()},
        unit=dict(returncode=0,stderr='',stdout=''.join(k+'='+v+'\n' for k,v in healthy['unit'].items())))
    save_command(directory,'ordinary-health-1',json.dumps(raw_health).encode(),stamp=2589)
    proof=M.SMOKE.closed(baseline,smoke,closure)
    dump(directory/'ordinary-smoke.json',dict(context=smoke,closure=closure,proof=proof))
    (directory/'ordinary-capture').mkdir();(directory/'ordinary-capture/events.jsonl').write_bytes(F.raw(closure['events']))
    stamps=[900,910,920,1000,1010,1100,2013,2390,2400,2410]
    for index,phase in enumerate(M.PHASES):
        dump(directory/(phase+'-entered.json'),dict(phase=phase,prior=list(M.PHASES[:index]),monotonic=stamps[index]))
        dump(directory/(phase+'-result.json'),results[phase])
    admission=dump(work/'admission.json',c)
    return admission


class ControllerReplayTests(unittest.TestCase):
    @contextlib.contextmanager
    def gates(self):
        with patch.object(M,'canonical',side_effect=lambda profile:PRIMARY if profile==M.PRIMARY else CANONICAL),\
             patch.object(M,'verify_claim'),\
             patch.object(M.CAP.ACCEPTANCE,'source_identity',return_value=SOURCE),\
             patch.object(M.CAP,'return_manifest',return_value=RETURN),\
             patch.object(M.ROOT.D,'expected_files',return_value=DEPLOYED):
            yield

    def evaluate(self,admission,directory):
        with self.gates():return M.check_controller(admission['path'],admission['sha256'],directory)

    def completed(self,directory):
        admission=fixture(directory);proof=self.evaluate(admission,directory)
        dump(directory/'result.json',dict(status='COMPONENT_PASS',phases=[*M.PHASES,'qualify'],errors=[],
             retry_permitted=False,selection_restored=True,release_qualified=False,qualification=proof))
        c=M.read(admission['path']);baseline=M.read(c['ordinary_baseline']['path'])
        inputs=M.make_inputs(admission['path'],admission['sha256'],directory,baseline['artifact_hashes'])
        envelope=dump(directory.parent/'inputs.json',inputs)
        return envelope,c,baseline

    def test_complete_synthetic_controller_replays_actual_validators(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'cycle';admission=fixture(directory)
            result=self.evaluate(admission,directory)
            self.assertTrue(result['r01_qualified']);self.assertFalse(result['release_qualified'])
            self.assertEqual(result['identity'],AFTER)

    def test_cli_replays_completed_envelope_and_separate_full_baseline(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'cycle';envelope,c,baseline=self.completed(directory)
            output=Path(temporary)/'assessment'
            args=['r01','--inputs',envelope['path'],'--inputs-sha256',envelope['sha256'],
                  '--candidate',M.PRIMARY,'--artifact-hashes',','.join(k+'='+v for k,v in baseline['artifact_hashes'].items()),
                  '--output',str(output)]
            with self.gates(),patch.object(M.SMOKE.B,'evaluate',return_value=baseline) as prior,\
                 patch.object(M.sys,'argv',args),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(M.main(),0)
            prior.assert_called_once_with(Path(c['ordinary_baseline_inputs']['path']),c['ordinary_baseline_inputs']['sha256'],
                                          M.PRIMARY,baseline['artifact_hashes'])
            result=M.read(output/'result.json')
            self.assertEqual(result['status'],'PASS');self.assertTrue(result['r01_qualified'])
            self.assertFalse(result['release_qualified']);self.assertEqual(result['inputs_sha256'],envelope['sha256'])

    def test_envelope_detects_extra_changed_or_mismatched_release_evidence(self):
        for change in ('extra','changed','different-release','failed-baseline'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)/'cycle';envelope,c,baseline=self.completed(directory)
                hashes=dict(baseline['artifact_hashes']);replayed=copy.deepcopy(baseline)
                if change=='extra':(directory/'unexpected').write_text('extra')
                if change=='changed':(directory/'ordinary-installed.stdout').write_text('changed')
                if change=='different-release':hashes['root_upper']='9'*64
                if change=='failed-baseline':replayed['status']='FAIL'
                with self.gates(),patch.object(M.SMOKE.B,'evaluate',return_value=replayed):
                    with self.assertRaises(ValueError):M.evaluate(Path(envelope['path']),envelope['sha256'],M.PRIMARY,hashes)

    def test_raw_evidence_contradictions_and_failure_cannot_be_hidden(self):
        for change in ('extra-command','source-storage','ordinary-summary','fake-return-time','phase-failure',
                       'component-only','changed-producer','missing-sample','ordinary-capture','wrong-primary-trial'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)/'cycle';admission=fixture(directory)
                if change=='extra-command':save_command(directory,'unexpected-reboot')
                if change=='source-storage':
                    actual=M.OBS.decode((directory/'source-root.stdout').read_bytes());actual['blocks']['sda24']='0'
                    save_command(directory,'source-root',json.dumps(actual).encode())
                if change=='ordinary-summary':
                    file=directory/'ordinary-smoke.json';value=M.read(file);value['context']['root']['power']['temp']='401';dump(file,value)
                if change=='fake-return-time':
                    file=directory/'observe-result.json';value=M.read(file);value['physical_return_monotonic']=2011;dump(file,value)
                if change=='phase-failure':dump(directory/'observe-failure.json',dict(status='FAIL'))
                if change=='component-only':
                    file=Path(admission['path']);c=M.read(file);checks=M.read(c['controller_checks']['path'])
                    checks['complete_driver_bindings']=False;c['controller_checks']=dump(Path(c['controller_checks']['path']),checks);admission=dump(file,c)
                if change=='changed-producer':(Path(temporary)/'r01-live-driver-r1.py').write_text('# changed\n')
                if change=='missing-sample':(directory/'negative-sample-3-command.json').unlink()
                if change=='ordinary-capture':(directory/'ordinary-capture/events.jsonl').write_bytes(b'{}\n')
                if change=='wrong-primary-trial':
                    file=directory/'ordinary-smoke.json';value=M.read(file)
                    for key in ('descriptor','healthy'):
                        item=value['context']['health']['files'][key];item['text']=item['text'].replace(PRIMARY['trial_id'],'9'*64)
                    dump(file,value)
                    actual=M.OBS.decode((directory/'ordinary-health-1.stdout').read_bytes())
                    for key in ('descriptor','healthy'):
                        item=actual['files'][M.OBS.MARKERS[key]];item['text']=item['text'].replace(PRIMARY['trial_id'],'9'*64)
                    save_command(directory,'ordinary-health-1',json.dumps(actual).encode(),stamp=2589)
                with self.assertRaises((ValueError,OSError,KeyError,TypeError)):self.evaluate(admission,directory)


if __name__=='__main__':unittest.main()
