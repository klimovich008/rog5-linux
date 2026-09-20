#!/usr/bin/env python3
"""Actual health predicates and collector with explicit offline I/O fixtures.

Private seals, physical shell execution and device reads are never imported or
executed. No fixture result is phone evidence or health admission.
"""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
BEFORE='--before' in sys.argv
if BEFORE:sys.argv.remove('--before')
BOOT='11111111-2222-3333-4444-555555555555';OWNER='a'*32;TRIAL='1'*64


def selected(path,constants=(),functions=None,classes=()):
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))
           or isinstance(n,ast.FunctionDef) and (functions is None or n.name in functions)
           or isinstance(n,ast.ClassDef) and n.name in classes
           or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
    m=types.ModuleType(path.stem);m.__file__=str(path)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),m.__dict__)
    return m


def load(path):
    m=types.ModuleType(path.stem);m.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m


def marker(text,mode=0o444):
    return dict(status='present',uid=0,gid=0,mode=mode,nlink=1,dev=23,text=text)


class Health(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='production-health-',dir=os.environ.get('TMPDIR',str(Path.home()/'.local/state')))
        cls.addClassCleanup(cls.temp.cleanup);cls.base=Path(cls.temp.name)
        cls.source=cls.base/'health.py'
        raw=(ROOT/'scripts/device/fixtures/display-loader/health-before.py').read_bytes()
        if hashlib.sha256(raw).hexdigest()!='5d8aa3e5e61ebcffdabd3f5b32d90c3c5c5b378866de1df69bff92d7ce5f5940':raise ValueError('normalized health fixture changed')
        cls.source.write_bytes(raw)
        if not BEFORE:subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0006-production-health.patch')],cwd=cls.base,check=True,capture_output=True)
        cls.root_module=selected(ROOT/'scripts/host/check-standalone-root.py',{'PROBE'})
        cls.root_module.D=types.SimpleNamespace(REPO=ROOT)
        cls.root_fixture=selected(ROOT/'scripts/host/test-check-standalone-root.py',{'MOUNTS'},functions=(),classes={'Tests'})
        cls.obs=selected(ROOT/'scripts/host/isolated-recovery-observation.py',{'PROBE'},functions={'need','unique','record'})
        cls.readiness=selected(ROOT/'scripts/host/check-deployed-server.py',{'READINESS_FAMILIES'},functions={'validate_readiness'})

    def setUp(self):
        self.m=selected(self.source,{'FINGERPRINT','IDENTITY_SHA','STARTUP_SECONDS','MARKERS','PROPERTIES','TIMER_PROPERTIES','ROLLBACK_PROPERTIES','SEALED_READER','COLLECT'})
        self.ident=dict(boot_id=BOOT,owner=OWNER,release='7.1.4-rog5-production',bundle='fixture-production',
            board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57')
        descriptor=f'format=rog5-persistent-wifi-health-v1\ntrial_id={TRIAL}\nprimary_bundle=fixture-production\nmode=try-once\n'
        self.ident['descriptor_sha256']=hashlib.sha256(descriptor.encode()).hexdigest()
        self.c=load(ROOT/'scripts/device/display-component.py');self.contract=self.c.HostContract(self.ident)
        self.legacy={k:self.ident[k] for k in ('boot_id','bundle','release')}
        self.state=(f'format=rog5-persistent-wifi-trial-v1\ntrial_id={TRIAL}\nprimary_bundle=fixture-production\n'
                    'primary_manifest_sha256='+('2'*64)+'\nfallback_bundle=fixture-fallback\nfallback_manifest_sha256='+('3'*64)+'\nstate=healthy\n')
        self.m.SEAL=dict(source_boot_id='00000000-0000-0000-0000-000000000001',
            target=self.legacy.copy() if BEFORE else {k:v for k,v in self.ident.items() if k not in ('owner','boot_id')},
            owner=OWNER,ssh_fingerprint='SHA256:'+'f'*43,trial_id=TRIAL,
            healthy_state_sha256=hashlib.sha256(self.state.encode()).hexdigest(),files={})
        if BEFORE:self.m.SEAL['target'].pop('boot_id')
        for name in ('runtime','healthy','trial','gpu_sqe','gpu_gmu','gpu_zap'):
            self.m.SEAL['files'][name]=dict(path='/fixture/'+name,size=12,uid=0,gid=0,mode=0o644,nlink=1,sha256='4'*64)
        self.m.inputs=lambda:self.m.SEAL
        self.m.ROOT=self.root_module;self.m.OBS=self.obs;self.m.D=self.readiness
        self.guard='expected_bundle=fixture-fallback\nexpected_release=fallback-release\nguard() { :; }\nrun_helper() { NEVER_EXECUTE; }\n'
        self.m.RECEIPT_SHA='5'*64
        self.m.A=types.SimpleNamespace(SOURCE_BOOT='00000000-0000-0000-0000-000000000002',OWNER=OWNER,
            exact_json=lambda a,b:json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True),pinned_sources=lambda:None,
            C=types.SimpleNamespace(boot_id=lambda b:None,FALLBACK=dict(bundle='fixture-fallback',release='fallback-release')),
            G=types.SimpleNamespace(build=lambda *args:self.guard))
        f=self.root_fixture.Tests();f.setUp();root=f.value;root['identity']=self.legacy.copy()
        cfg=self.cfg()
        files=dict(descriptor=marker(descriptor),healthy=marker(f'format=rog5-native-wifi-healthy-v1\nboot_id={BOOT}\ntrial_id={TRIAL}\nresult=PASS\n'),
            ssh=marker('format=rog5-persistent-ssh-identity-v1\nmode=load\nfingerprint=SHA256:'+('f'*43)+f'\nidentity_boot_id={BOOT}\n'),
            ready=marker(f'status=PASS\nkernel={self.ident["release"]}\nssh=strict-key-only\nattested_boot_id={BOOT}\n'),selection=marker(self.state,0o600))
        self.value=dict(identity=self.legacy.copy(),boot_after=self.legacy.copy(),root=root,files=files,
            sealed={n:dict(status='present',dev=23,**{k:r[k] for k in ('uid','gid','mode','nlink','sha256')}) for n,r in cfg['files'].items()},
            unit=dict(ActiveState='active',SubState='exited',Result='success',ExecMainStatus='0',ExecMainStartTimestampMonotonic='48000000',ExecMainExitTimestampMonotonic='58000000'),
            timers={},services=dict.fromkeys(('rog5-wifi-radio.service','rog5-wifi-wpa.service','rog5-wifi-dhcp.service','rog5-tailscaled.service'),'active\n'),
            marker_fstype='tmpfs\n',uptime='1400.25',physical_guard_passed=True)
        names=('rog5-wifi-boot-rollback','rog5-wifi-probe-rollback')
        if BEFORE:self.value['timers']={n+'.timer':'inactive\n' for n in names}
        else:
            self.value.update(artifact_identity=self.ident.copy(),artifact_identity_after=self.ident.copy(),rollback_services={},rollback_exec={})
            for n in names:
                self.value['timers'][n+'.timer']=dict(LoadState='loaded',ActiveState='active',SubState='waiting',Result='success',Unit=n+'.service')
                self.value['rollback_services'][n+'.service']=dict(LoadState='loaded',ActiveState='inactive',SubState='dead',Result='success',ExecMainStatus='0',**dict.fromkeys(self.m.ROLLBACK_PROPERTIES[5:],''))
                self.value['rollback_exec'][n+'.service']=dict(type='a(sasbttttuii)',data=[['/run/rog5-native-wifi/runtime',['/run/rog5-native-wifi/runtime','rollback'],False,0,0,0,0,0,0,0]])

    def cfg(self):
        return self.m.configuration('target',BOOT,*(() if BEFORE else (self.contract,OWNER)))

    def check(self):
        return self.m.validate(self.value,'target',BOOT,*(() if BEFORE else (self.contract,OWNER)))

    def test_armed_timer_protocol(self):
        if BEFORE:self.value['timers']=dict.fromkeys(self.value['timers'],'active\n')
        self.assertEqual(self.check()['status'],'PASS')

    def test_healthy_line_order_rejected(self):
        row=self.value['files']['healthy'];row['text']='\n'.join(reversed(row['text'].splitlines()))+'\n'
        with self.assertRaises(ValueError):self.m.latch(self.value,self.cfg())

    def test_descriptor_exact_bytes_rejected(self):
        row=self.value['files']['descriptor'];row['text']='\n'.join(reversed(row['text'].splitlines()))+'\n'
        with self.assertRaises(ValueError):self.m.latch(self.value,self.cfg())

    def test_pending_selection_even_when_hash_pinned(self):
        self.value['files']['selection']['text']=self.state.replace('state=healthy','state=pending')
        self.m.SEAL['healthy_state_sha256']=hashlib.sha256(self.value['files']['selection']['text'].encode()).hexdigest()
        with self.assertRaises(ValueError):self.check()

    def test_positive_reports_exact_artifact_and_late_observation(self):
        result=self.check();self.assertEqual(result['identity'],self.ident)
        self.assertEqual(result['commit_uptime_seconds'],58);self.assertEqual(result['observed_uptime_seconds'],1400.25)
        self.assertFalse(result['release_qualified']);self.assertTrue(result['current_boot_healthy'])

    def test_waiting_and_elapsed_are_accepted(self):
        for row in self.value['timers'].values():row['SubState']='elapsed'
        self.assertEqual(self.check()['status'],'PASS')

    def test_seal_identity_and_private_fingerprint_required(self):
        for key,bad in (('owner','b'*32),('ssh_fingerprint','invalid'),('target',self.legacy)):
            original=self.m.SEAL[key];self.m.SEAL[key]=bad
            with self.subTest(key=key),self.assertRaises((ValueError,KeyError)):self.cfg()
            self.m.SEAL[key]=original

    def test_guard_owner_cannot_differ_from_admitted_owner(self):
        self.m.A.OWNER='b'*32
        with self.assertRaisesRegex(ValueError,'seal differs'):self.cfg()

    def test_artifact_before_after_binding(self):
        for field in ('artifact_identity','artifact_identity_after'):
            for key,bad in (('owner','b'*32),('descriptor_sha256','0'*64),('board_dtb_sha256','0'*64)):
                original=self.value[field][key];self.value[field][key]=bad
                with self.subTest(field=field,key=key),self.assertRaises(ValueError):self.check()
                self.value[field][key]=original

    def test_descriptor_hash_cannot_follow_valid_parsed_fields(self):
        self.ident['descriptor_sha256']='0'*64;self.contract=self.c.HostContract(self.ident)
        self.m.SEAL['target']['descriptor_sha256']='0'*64
        for field in ('artifact_identity','artifact_identity_after'):self.value[field]=self.ident.copy()
        with self.assertRaisesRegex(ValueError,'descriptor bytes/hash'):self.check()

    def test_wrong_trial_even_when_state_hash_pinned(self):
        raw=self.state.replace(TRIAL,'9'*64);self.value['files']['selection']['text']=raw
        self.m.SEAL['healthy_state_sha256']=hashlib.sha256(raw.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'trial identity'):self.check()

    def test_timer_and_service_failures_hooks(self):
        timer=next(iter(self.value['timers'].values()));service=next(iter(self.value['rollback_services'].values()))
        for row,key,bad in ((timer,'LoadState','not-found'),(timer,'ActiveState','inactive'),(timer,'SubState','dead'),(timer,'Unit','other.service'),
                            (service,'ActiveState','active'),(service,'ExecMainStatus','1'),(service,'ExecStartPre','/bin/reboot'),(service,'ExecCondition','/bin/false')):
            original=row[key];row[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):self.check()
            row[key]=original

    def test_loaded_action_must_be_single_typed_guarded_runtime(self):
        item=next(iter(self.value['rollback_exec'].values()));original=copy.deepcopy(item)
        variants=[dict(type='wrong',data=original['data']),dict(original,data=[]),dict(original,data=original['data']*2)]
        for index,bad in ((0,'/usr/bin/systemctl'),(1,['/usr/bin/systemctl','reboot']),(2,True),(3,False),(8,2),(9,1)):
            changed=copy.deepcopy(original);changed['data'][0][index]=bad;variants.append(changed)
        for bad in variants:
            item.clear();item.update(bad)
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.check()
        item.clear();item.update(original)

    def test_physical_root_and_firmware_guards_stay_required(self):
        for path,bad in ((('physical_guard_passed',),False),(('root','usb_online'),'0'),(('root','power','temp'),'400'),
                         (('root','power','voltage_now'),'8000000'),(('root','blocks','sda23'),'1'),(('services','rog5-wifi-radio.service'),'inactive\n')):
            row=self.value
            for key in path[:-1]:row=row[key]
            key=path[-1];old=row[key];row[key]=bad
            with self.subTest(path=path),self.assertRaises(ValueError):self.check()
            row[key]=old
        for row in self.value['sealed'].values():
            old=row['sha256'];row['sha256']='0'*64
            with self.assertRaises(ValueError):self.check()
            row['sha256']=old

    def test_health_unit_boot_trial_readiness_and_ssh_failures(self):
        for name in ('healthy','descriptor','ready','ssh'):
            old=self.value['files'][name]['text']
            if name=='descriptor':bad=old.replace(TRIAL,'8'*64)
            elif name=='ssh':bad=old.replace('f'*43,'e'*43)
            else:bad=old.replace(BOOT,'00000000-0000-0000-0000-000000000000')
            self.value['files'][name]['text']=bad
            with self.subTest(name=name),self.assertRaises(ValueError):self.check()
            self.value['files'][name]['text']=old
        self.value['unit']['ExecMainExitTimestampMonotonic']='301000000'
        with self.assertRaises(ValueError):self.check()

    def test_guard_prefix_preserved_without_helper_execution(self):
        actual=self.m.physical_guard(self.cfg())
        expected=self.guard.split('run_helper() {')[0].replace('expected_bundle=fixture-fallback','expected_bundle=fixture-production').replace('expected_release=fallback-release','expected_release=7.1.4-rog5-production')+"guard\nprintf 'PASS-physical-guard\\n'\n"
        self.assertEqual(actual,expected)
        self.assertNotIn('NEVER_EXECUTE',actual)
        self.guard+='run_helper() { duplicate; }'
        with self.assertRaises(ValueError):self.m.physical_guard(self.cfg())

    def test_generated_script_checks_identity_and_keeps_legacy_inner_readers(self):
        script=self.m.script('target',BOOT,self.contract,OWNER);compile(script,'health-fixture','exec')
        tree=ast.parse(script);env={}
        head=[]
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='artifact_before' for t in node.targets):break
            head.append(node)
        exec(compile(ast.Module(body=head,type_ignores=[]),'health-prefix','exec'),env)
        endpoint=load(ROOT/'scripts/device/test-display-endpoint.py').EndpointFixture();endpoint.setUp();self.addCleanup(endpoint.doCleanups)
        endpoint.write(endpoint.descriptor,self.value['files']['descriptor']['text'])
        ns=env['endpoint_space'];ns['PROC']=endpoint.proc;ns['DESCRIPTOR']=endpoint.descriptor
        self.assertEqual(env['artifact_identity'](),self.ident)
        self.assertEqual(env['CFG']['identity'],self.legacy)
        reader={ 'request':{'identity':self.legacy} }
        exec(env['READERS'],reader)
        with patch.object(reader['os'],'getuid',return_value=0),patch.object(reader['os'],'getgid',return_value=0),patch.object(reader['os'],'uname',return_value=types.SimpleNamespace(release=self.ident['release'])):
            reader['small']=lambda p,*_: BOOT if str(p).endswith('boot_id') else 'rog5.bundle=fixture-production'
            self.assertEqual(reader['identity'](),self.legacy)
        endpoint.write(endpoint.proc/'cmdline','rog5.bundle=fixture-production rog5.bundle=fixture-production\n')
        with self.assertRaises(ValueError):env['artifact_identity']()

    def test_sealed_authority_functions_and_reader_are_unchanged(self):
        before=ast.parse((ROOT/'scripts/device/fixtures/display-loader/health-before.py').read_text())
        after=ast.parse(self.source.read_text())
        for name in ('inputs','physical_guard','SEALED_READER'):
            def find(tree):
                return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name
                    or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
            with self.subTest(name=name):self.assertEqual(ast.dump(find(before)),ast.dump(find(after)))

    def test_collector_rejects_descriptor_changed_after_collection(self):
        self.mutate_after_collection=True
        with self.assertRaisesRegex(ValueError,'descriptor changed'):
            self.test_generated_collector_executes_command_and_identity_boundaries()

    def test_generated_collector_executes_command_and_identity_boundaries(self):
        script=self.m.script('target',BOOT,self.contract,OWNER)
        tree=ast.parse(script);split=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='artifact_before' for t in n.targets))
        env={};exec(compile(ast.Module(body=tree.body[:split],type_ignores=[]),'health-prefix','exec'),env)
        endpoint=load(ROOT/'scripts/device/test-display-endpoint.py').EndpointFixture();endpoint.setUp();self.addCleanup(endpoint.doCleanups)
        endpoint.write(endpoint.descriptor,self.value['files']['descriptor']['text']);ns=env['endpoint_space'];ns['PROC']=endpoint.proc;ns['DESCRIPTOR']=endpoint.descriptor
        # The collector itself executes. Root/metadata observations are explicit
        # fixtures validated separately above; no absolute target path is read.
        env['ROOT_PROBE']='value='+repr(self.value['root'])
        observed={self.m.MARKERS[k]:v for k,v in self.value['files'].items()}
        env['READERS']='''identity=lambda: request['identity'].copy()
observed=lambda p,text: OBSERVED[p]
observed_sealed=lambda row: SEALED[row['path']]
small=lambda *args: '1400.25 0'
'''
        actual_exec=exec
        def execute(source,space):
            if source==env['READERS']:
                space['OBSERVED']=observed;space['SEALED']={row['path']:self.value['sealed'][n] for n,row in self.cfg()['files'].items()}
            return actual_exec(source,space)
        env['exec']=execute;calls=[]
        def command(argv,data=None):
            calls.append(argv)
            if argv[0].endswith('ld-musl-aarch64.so.1'):
                if getattr(self,'mutate_after_collection',False) and sum(c[0].endswith('ld-musl-aarch64.so.1') for c in calls)==2:
                    endpoint.write(endpoint.descriptor,b'changed after metadata collection\n')
                return b'PASS-physical-guard\n'
            if argv[0]=='busctl':
                name=argv[4].rsplit('/',1)[1].replace('_2d','-').replace('_2e','.')
                return json.dumps(self.value['rollback_exec'][name]).encode()
            if argv[0]=='findmnt':return b'tmpfs\n'
            self.assertEqual(argv[:2],['systemctl','show']);name=argv[2]
            if name in self.value['services']:return self.value['services'][name].encode()
            row=self.value['unit'] if name=='rog5-wifi-healthy.service' else self.value['timers'].get(name,self.value['rollback_services'].get(name))
            return ''.join(k+'='+v+'\n' for k,v in row.items()).encode()
        env['command']=command
        out=io.StringIO()
        with contextlib.redirect_stdout(out):exec(compile(ast.Module(body=tree.body[split:],type_ignores=[]),'health-collect','exec'),env)
        self.value=json.loads(out.getvalue());self.assertEqual(self.check()['status'],'PASS')
        self.assertEqual(sum(c[0]=='busctl' for c in calls),2)
        self.assertEqual(sum(c[0].endswith('ld-musl-aarch64.so.1') for c in calls),2)
        self.assertEqual(self.value['artifact_identity_after'],self.ident)


if __name__=='__main__':
    controls=['Health.test_armed_timer_protocol','Health.test_healthy_line_order_rejected',
              'Health.test_descriptor_exact_bytes_rejected','Health.test_pending_selection_even_when_hash_pinned']
    unittest.main(defaultTest=controls if BEFORE else None)
