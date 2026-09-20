#!/usr/bin/env python3
"""Source integration only. No private imports or target commands are executed.

The actual caller/wrapper/Driver/Fastboot/Controller definitions run with the
actual public cohort, HostContract and health validator. Authentication, health
seal storage, omitted custody/root/route/capture/boot producers, and all device
transports are explicit inert fixtures. They are not evidence of live authority.
Supply the exact original ten sources: two packet attachments are normalized.
"""
import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import shlex
import stat
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch

P=argparse.ArgumentParser()
P.add_argument('--packet',type=Path,required=True)
P.add_argument('--patch',type=Path,required=True)
P.add_argument('--sources',type=Path,required=True)
ARGS,REST=P.parse_known_args()
AD='current-callers/live-admission.py.txt'
L='current-callers/trial-launcher.py.txt'
PREFIX='downstream/gpu-iommu-live-driver-r1__'
WR=PREFIX+'health-read-callbacks.py.txt';FB=PREFIX+'fastboot-callbacks.py.txt'
DR=PREFIX+'live-driver.py.txt';AC=PREFIX+'action-callbacks.py.txt'
F=PREFIX+'fallback-observation.py.txt';C='downstream/gpu-iommu-controller-r1__controller.py.txt'
BOOT='11111111-2222-3333-4444-555555555555'
SOURCE_BOOT='00000000-1111-2222-3333-444444444444'
FALLBACK_BOOT='22222222-3333-4444-5555-666666666666'
OWNER='a'*32
NS=types.SimpleNamespace

def sha(raw):return hashlib.sha256(raw).hexdigest()
def noop(*args,**kwargs):return None

def packet(path):
    result={};originals={}
    for header,body in re.findall(rb'^===== FILE ([^\n]+) =====\n(.*?)^===== END FILE =====(?:\n|$)',path.read_bytes(),re.M|re.S):
        name,digests=header.decode().split(' SHA256 ',1);raw=body[:-1]
        digest=digests.split('SANITIZED_ATTACHMENT_SHA256 ')[-1].strip()
        if sha(raw)!=digest or name in result:raise ValueError('packet digest/duplicate: '+name)
        result[name]=raw;originals[name]=digests[:64]
    return result,originals

def definitions(raw,name,namespace=None,constants=()):
    """No module-level imports, private loads, producers, or embedded commands."""
    m=types.ModuleType(name)
    m.__dict__.update(dict(base64=base64,hashlib=hashlib,json=json,math=math,os=os,
                          Path=Path,re=re,stat=stat,time=time,shlex=shlex),**(namespace or {}))
    tree=ast.parse(raw)
    for key in constants:
        node,=[n for n in tree.body if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id==key for t in n.targets)]
        exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'),m.__dict__)
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),m.__dict__)
    return m

def source_module(path):
    m=types.ModuleType('inert_public_source');m.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__)
    return m

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError('ordinary UID1000 required; no root test')
        cls.sections,cls.originals=packet(ARGS.packet)
        temp=tempfile.TemporaryDirectory(prefix='cold-boot-source-',dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(temp.cleanup);cls.base=Path(temp.name)
        for name in (AD,L,WR,FB,DR,AC,F,C):
            p=cls.base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(cls.sections[name])
        for option in (['--check'],[]):
            subprocess.run(['git','apply',*option,str(ARGS.patch.resolve())],cwd=cls.base,
                           check=True,capture_output=True,timeout=10)
        for name in [n for n in cls.sections if n.startswith('production-cohort/')]:
            raw=(ARGS.sources/Path(name).name).read_bytes()
            if sha(raw)!=cls.originals[name]:raise ValueError('exact original cohort required: '+name)

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=self.base));self.events=[]
        cp=self.root/'gpu-iommu-controller-r1';cp.mkdir()
        self.c=definitions((self.base/C).read_bytes(),'controller',dict(ROOT=cp,OUTPUT=cp/'execution'),
                           ('SOURCE','TARGET','FALLBACK','OLD','PENDING','HEALTHY','PHASES','MUTATIONS'))
        self.a=definitions((self.base/AC).read_bytes(),'actions',dict(C=self.c),('PHASES','SHELL','RECEIPT_SHA','CUSTODY_SHA'))
        self.a.OWNER=OWNER;self.a.SOURCE_BOOT=SOURCE_BOOT;self.a.OUTPUT=self.c.OUTPUT
        self.a.pinned_sources=noop
        self.source=dict(clean=True,revision='inert-test',worktree_digest='f'*64)
        self.cap=NS(INTERFACE='inert-interface',ACCEPTANCE=NS(source_identity=lambda:dict(self.source)),
                    usb_mode=lambda _:('target','inert-interface'),UsbReadDisappeared=type('NoDevice', (Exception,), {}))
        self.deployed=NS(CAPTURE=self.cap)
        self.w=NS(request=self.a.decode,load_deployed=lambda:self.deployed,perform=self.forbidden,
                  SERIAL='INERT-NO-DEVICE',source_identity=lambda:dict(self.source),pins=noop)
        self.a.W=self.w
        self.r=definitions(self.sections[PREFIX+'source-read-callbacks.py.txt'],'receipts',dict(A=self.a,need=self.a.need))
        self.r.pins=noop
        raw_receipt=self.r.receipt
        self.r.receipt=lambda p,limit:self.lock_raw if p==self.ad.INPUTS else raw_receipt(p,limit)
        self.f=definitions((self.base/F).read_bytes(),'fallback',constants=('BOOT_SHA','BODY'))
        self.f.SOURCE_BOOT=SOURCE_BOOT;self.f.OWNER=OWNER;self.f.RECEIPT_SHA='c'*64
        self.f.inventory=lambda:{}  # Missing private installed inventory/custody.
        self.wrapper=definitions((self.base/WR).read_bytes(),'health_wrapper',dict(A=self.a,R=self.r,F=self.f,need=self.a.need),('PHASES','DISCOVERY'))
        self.wrapper.OUTPUT=self.c.OUTPUT;self.wrapper.pins=noop
        self.fb=definitions((self.base/FB).read_bytes(),'fastboot',dict(A=self.a,R=self.r,HEALTH=self.wrapper,need=self.a.need),('PHASES',))
        self.fb.OUTPUT=self.c.OUTPUT;self.fb.pins=noop
        self.driver=definitions((self.base/DR).read_bytes(),'driver',dict(C=self.c,A=self.a,R=self.r,HEALTH=self.wrapper,
            FASTBOOT=self.fb,need=self.a.need))
        self.driver.OUTPUT=self.c.OUTPUT;self.driver.pins=noop
        ad_path=self.root/'gpu-iommu-live-driver-r1/live-admission.py';ad_path.parent.mkdir()
        ad_path.write_bytes((self.base/AD).read_bytes())
        self.ad=definitions((self.base/AD).read_bytes(),'admission',dict(__file__=str(ad_path),A=self.a,C=self.c,R=self.r,
            H=self.wrapper,W=self.w,D=self.driver,STATE=self.root,HERE=ad_path.parent,OUTPUT=self.c.OUTPUT,_CACHE={}),
            ('PRODUCTION_PATHS','DISCOVERY_FIELDS','ARTIFACT_FIELDS','COLD_FORMAT','HEALTH_INPUT','MAX_LIFETIME'))
        self.ad.INPUTS=ad_path.parent/'inert-input-path'
        self.driver.BOOT=NS(expected_kernel_relay=noop,pins=noop,IMAGE_SHA='d'*64)
        self.a.STAGING=self.root/'inert-custody';self.a.STAGING.mkdir()
        for name in ('preparation.json','stage-receipt.json'):(self.a.STAGING/name).write_bytes(b'inert\n')
        original_digest=self.ad.digest_file
        def digest(p,*args):
            # Only unavailable private seal/custody is synthetic; all ten source
            # metadata/digest checks execute the actual admission implementation.
            if p.parent==self.a.STAGING or p==self.root/self.ad.HEALTH_INPUT:return
            original_digest(p,*args)
        self.ad.digest_file=digest
        self.lock=dict(format=self.ad.COLD_FORMAT,files={},production_display_sources=list(self.ad.PRODUCTION_PATHS))
        for p in ARGS.sources.glob('*.py'):
            if p.name in ('session.py','kernel-log.py'):name='gpu-iommu-session-r1/'+p.name
            elif p.name=='health.py':name='gpu-iommu-health-r1/successor-health.py'
            else:name='gpu-iommu-display-r1/'+p.name
            if name not in self.ad.PRODUCTION_PATHS:continue
            dest=self.root/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(p.read_bytes());dest.chmod(0o644)
            st=dest.stat();self.lock['files'][name]=dict(size=st.st_size,uid=1000,mode=0o644,sha256=sha(dest.read_bytes()))
        self.g=source_module(self.root/'gpu-iommu-session-r1/session.py')
        trial='2'*64;bundle='fixture-production'
        descriptor=f'format=rog5-persistent-wifi-health-v1\ntrial_id={trial}\nprimary_bundle={bundle}\nmode=try-once\n'
        self.selection=('format=rog5-persistent-wifi-trial-v1\ntrial_id='+trial+'\nprimary_bundle='+bundle+
            '\nprimary_manifest_sha256='+'4'*64+'\nfallback_bundle='+self.c.FALLBACK['bundle']+
            '\nfallback_manifest_sha256='+'5'*64+'\nstate=healthy\n')
        self.spec=dict(source_boot_id=SOURCE_BOOT,owner=OWNER,trial_id=trial,ssh_fingerprint='SHA256:'+'f'*43,
            target=dict(bundle=bundle,release='7.1.4-rog5-production',descriptor_sha256=sha(descriptor.encode()),
                        board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57'),
            boot_image_sha256='d'*64,health_inputs_sha256='02e007b553ba4a5e3d5bf5d1545ea3a5ee62860cc09ffb748135e7bc9d8b3425',
            states=dict(old=self.c.OLD,pending=sha(b'inert-pending'),healthy=sha(self.selection.encode())))
        self.lock['production_cold_boot']=copy.deepcopy(self.spec)
        self.lock['files'][self.ad.HEALTH_INPUT]=dict(size=1,uid=1000,mode=0o600,sha256=self.spec['health_inputs_sha256'])
        self.guard=NS(OLD_SHA=self.spec['states']['old'],PENDING_SHA=self.spec['states']['pending'],
            HEALTHY_SHA=self.spec['states']['healthy'],custody=lambda *a:b'inert',
            OPERATIONS={'restore-target':(*[self.spec['target'][k] for k in ('bundle','release')],'inert'),
                        'restore-v11':(self.c.FALLBACK['bundle'],self.c.FALLBACK['release'],'inert')},
            boot_id=self.c.boot_id,build=lambda *a:
                'expected_bundle='+self.c.FALLBACK['bundle']+'\nexpected_release='+self.c.FALLBACK['release']+'\nrun_helper() {\n')
        self.a.G=self.f.G=self.guard;self.a.CUSTODY_SHA=sha(b'inert')
        self.reseal_fixture()
        self.binding=self.ad.ColdBoot(self.ad,self.g,OWNER)
        self.h=self.g.H
        self.h.A=self.a;self.h.SEAL=dict(target=self.spec['target'],owner=OWNER,source_boot_id=SOURCE_BOOT,
            trial_id=trial,ssh_fingerprint=self.spec['ssh_fingerprint'],healthy_state_sha256=self.spec['states']['healthy'],files={})
        self.h.inputs=lambda:copy.deepcopy(self.h.SEAL)
        self.h.ROOT=NS(PROBE='print(json.dumps(value))',validate=noop)
        self.h.OBS=NS(PROBE='actual=dict(identity=identity(),files={},sealed={},units={})',
                      record=lambda item,mode:self.a.fields(item['text'].encode()))
        self.h.D=NS(validate_readiness=lambda *a:dict(marker_boot_bound=True))
        self.l=definitions((self.base/L).read_bytes(),'launcher',dict(AD=self.ad,A=self.a,C=self.c,B=NS(),G=self.g,
                          __file__=str(self.base/L),LAUNCH=self.root/'launch',AUTH_ROOT=self.root/'auth',LOCK=self.root/'lock',need=self.ad.need))
        self.l.P=NS(authenticate=self.forbidden);self.l.K=NS(Credentials=self.forbidden)
        self.env=patch.dict(os.environ,ALLOW_TEMPORARY_BOOT='1',ALLOW_HEADLESS_LIVE_GATE='1')
        self.env.start();self.addCleanup(self.env.stop)

    def forbidden(self,*args,**kwargs):
        self.events.append('FORBIDDEN EFFECT');raise AssertionError('effect was reached')

    def reseal_fixture(self):
        # In-memory authority fixture only; never emit a replacement lock/seal.
        self.lock_raw=json.dumps(self.lock,allow_nan=False).encode();self.ad.INPUTS_SHA=sha(self.lock_raw)

    def ready(self):
        # ONLY the unavailable private initialization is a fixture for downstream
        # API tests. A separate case executes the real refusal before credentials.
        with patch.object(self.g,'initialize',noop):self.binding.runtime_ready()

    def health_value(self,boot=BOOT):
        s=self.spec;identity=dict(s['target'],boot_id=boot,owner=OWNER)
        ident3={k:identity[k] for k in ('boot_id','bundle','release')}
        marker=lambda text:dict(text=text)
        value=dict(identity=ident3,boot_after=dict(ident3),artifact_identity=dict(identity),artifact_identity_after=dict(identity),
            root=dict(units={'rog5-persistent-ssh-identity.service':'active'}),files={},sealed={},unit={},timers={},
            rollback_services={},rollback_exec={},services={},marker_fstype='tmpfs\n',uptime='100',physical_guard_passed=True)
        value['files']=dict(descriptor=marker(f'format=rog5-persistent-wifi-health-v1\ntrial_id={s["trial_id"]}\nprimary_bundle={s["target"]["bundle"]}\nmode=try-once\n'),
            healthy=marker(f'format=rog5-native-wifi-healthy-v1\nboot_id={boot}\ntrial_id={s["trial_id"]}\nresult=PASS\n'),
            ssh=marker(f'format=rog5-persistent-ssh-identity-v1\nmode=seed\nfingerprint={s["ssh_fingerprint"]}\nidentity_boot_id={boot}\n'),
            selection=marker(self.selection),ready=marker('inert-readiness\n'))
        # Readiness parser is an explicit omitted dependency; use a framed marker.
        value['files']['ready']['text']='status=PASS\n'
        value['unit']=dict(zip(self.h.PROPERTIES,('active','exited','success','0','1000000','2000000')))
        for name in ('rog5-wifi-boot-rollback','rog5-wifi-probe-rollback'):
            value['timers'][name+'.timer']=dict(zip(self.h.TIMER_PROPERTIES,('loaded','active','waiting','success',name+'.service')))
            value['rollback_services'][name+'.service']=dict(zip(self.h.ROLLBACK_PROPERTIES,('loaded','inactive','dead','success','0','','','','','')))
            value['rollback_exec'][name+'.service']=dict(type='a(sasbttttuii)',data=[['/run/rog5-native-wifi/runtime',['/run/rog5-native-wifi/runtime','rollback'],False,0,0,0,0,0,0,0]])
        value['services']={n:'active\n' for n in ('rog5-wifi-radio.service','rog5-wifi-wpa.service','rog5-wifi-dhcp.service','rog5-tailscaled.service')}
        return value

    def restoration_raw(self,boot,role,purpose='verify-restored'):
        bundle,release,_=self.guard.OPERATIONS['restore-target' if role=='target' else 'restore-v11']
        ready=f'status=PASS\nkernel={release}\nssh=strict-key-only\nattested_boot_id={boot}\n'.encode()
        value=dict(format='rog5-target-selection-restoration-v1' if role=='target' else 'rog5-v11-selection-observation-v1',
            purpose=purpose,boot_id=boot,state_sha256=self.spec['states']['old' if purpose=='verify-restored' else 'pending'],readiness_sha256=sha(ready),
            readiness_base64=base64.b64encode(ready).decode(),installed_inventory_sha256=sha(json.dumps(
                {'/dev/sde35':dict(sha256=self.f.BOOT_SHA)},sort_keys=True,separators=(',',':')).encode()),
            physical_guards_passed='true',restoration_verified='true' if purpose=='verify-restored' else 'false',read_only='true')
        raw=''.join(k+'='+v+'\n' for k,v in value.items()).encode()
        if role=='fallback':return raw
        expected=self.binding.expected(boot,OWNER)
        return json.dumps(dict(artifact_before=expected,artifact_after=expected,
                              restoration_base64=base64.b64encode(raw).decode())).encode()

    def transport(self,phase,context,results,pin,request,deployed):
        self.assertIs(deployed,self.deployed)
        self.ad.command_policy(phase,context,results,pin,request,self.source,contract=self.binding,owner=OWNER)
        self.events.append((phase,'inert transport'))
        code=0
        if request['script'] in (self.wrapper.discovery('target'),self.wrapper.discovery('fallback')):
            role='target' if request['script']==self.wrapper.discovery('target') else 'fallback'
            identity=dict(boot_id=BOOT,**self.binding.target) if role=='target' else dict(boot_id=FALLBACK_BOOT,**self.c.FALLBACK)
            data=dict(identity,ready='ready');data.update(getattr(self,'discovery_change',{}))
            out=''.join(k+'='+v+'\n' for k,v in data.items()).encode()
            if role=='target' and getattr(self,'only_fallback',False):code=255;out=b''
        elif phase=='verify_target_restoration':out=self.restoration_raw(BOOT,'target')
        elif request['mode']=='linklocal':
            out=self.restoration_raw(FALLBACK_BOOT,'fallback','verify-restored' if phase=='verify_fallback_restoration' else 'observe')
        else:
            value=self.health_value();value.update(getattr(self,'health_change',{}));out=json.dumps(value).encode()
        return dict(status='PASS_TRANSPORT_COMPLETED',mode=request['mode'],source=self.source,command_invoked=True,
            command=dict(returncode=code,timed_out=False,reaped=True,stdout_base64=base64.b64encode(out).decode(),
                         stderr_base64='',stdout_sha256=sha(out),stderr_sha256=sha(b'')))

    def build_driver(self,create_controller=True):
        self.ready();a=self.a;c=self.c;api=self
        class Route:
            def __init__(self,*args):pass
            def check(self,*args):return {}
            def prepare(self,context,results,pin):return dict(status='PASS',identity=context['source'],ram_staging_verified=True)
        class SourceReads:
            def __init__(self,*args):pass
            def inspect_source_abort(self,*args):raise AssertionError('source recovery fixture not installed')
            def verify_source_abort(self,*args):raise AssertionError('source recovery fixture not installed')
        class Captures:
            def __init__(self,*args):self.workers={}
            def ready(self,*args):return dict(status='PASS',live=True,remaining_lifetime_valid=True)
            capture_start=recovery_capture_start=ready
            def close_capture(self,*args):return dict(status='PASS',cleanup_complete=True,capture_started=True,full_lifetime=True,capture_status='PASS')
            close_recovery_capture=close_capture
        class Boot:
            def __init__(self,*args):pass
            def boot_once(self,*args):return dict(status='PASS',transfer_completed=True,attempt_count=1)
        self.r.SourceReads=SourceReads;self.r.OUTPUT=c.OUTPUT
        self.driver.ROUTE=NS(Route=Route,W=self.w,OUTPUT=c.OUTPUT)
        self.driver.CAPTURE=NS(Captures=Captures,PHASES=('capture_start','close_capture','recovery_capture_start','close_recovery_capture'),A=a,OUTPUT=c.OUTPUT)
        self.driver.BOOT.Boot=Boot;self.driver.BOOT.PHASES=('boot_once',);self.driver.BOOT.OUTPUT=c.OUTPUT;self.driver.BOOT.A=a
        self.fb.A=a
        # Actual Actions constructor and target_recovery_proof; physical source
        # mutation/custody bodies and unknown guarded generators are not run.
        def prep(obj,phase,context,results,pin):
            api.ad.authorize(phase,context,results,pin,contract=api.binding,owner=OWNER)
            return dict(context['source'])
        def arm(obj,context,results,pin):
            prep(obj,'arm_state',context,results,pin)
            return dict(status='PASS',identity=context['source'],before_sha256=api.binding.states['old'],after_sha256=api.binding.states['pending'],completed=True)
        def install(obj,context,results,pin):
            prep(obj,'install_exitrd',context,results,pin)
            return dict(status='PASS',identity=context['source'],installed=True,reboot_requested=False)
        def reboot(obj,context,results,pin):
            prep(obj,'request_source_reboot',context,results,pin);return dict(status='PASS')
        for method,fn in [('arm_state',arm),('install_exitrd',install),('request_source_reboot',reboot)]:
            p=patch.object(a.Actions,method,fn);p.start();self.addCleanup(p.stop)
        p=patch.object(self.fb.Fastboot,'await_fastboot',lambda *args:dict(status='PASS'))
        p.start();self.addCleanup(p.stop)
        bridge=NS(command=noop,launch=noop,stop=noop)
        inner=self.driver.Driver(self.source,
            lambda *a:self.ad.before_phase(*a,contract=self.binding,owner=OWNER),
            lambda *a:self.ad.authorize(*a,contract=self.binding,owner=OWNER),bridge,
            transport=self.transport,production=self.binding)
        # Full actual history/policy runs; only external authenticated admission,
        # process custody and claim/qualification storage are inert here.
        self.ad.common=lambda *a,**kw:dict(host_source=self.source,expires_monotonic=time.monotonic()+4000)
        self.inner=inner
        if not create_controller:return inner
        context=dict(source=dict(c.SOURCE,boot_id=SOURCE_BOOT),owner=OWNER,admission_sha256='e'*64)
        controller=c.Controller(inner,context,production=self.binding)
        c.save(c.OUTPUT/'admission.json',dict(host_source=self.source))
        self.inner=inner;self.controller=controller
        return controller

    def run_success(self):
        controller=self.build_driver();result=controller.run()
        self.assertEqual(result['status'],'COMPONENT_PASS',result)
        return controller,result

    def test_static_document_has_no_boot_and_no_authority(self):
        self.assertNotIn('boot_id',self.binding.static)
        self.assertIsNone(self.binding.selected_boot);self.assertIsNone(self.binding._contract)
        document=self.ad.cold_input_document(self.lock['files'],self.spec)
        self.assertEqual(document,self.lock)
        self.assertFalse(self.c.OUTPUT.exists())
        self.binding.static['target']['bundle']='changed'
        self.assertEqual(self.binding.static,self.spec)
        changed=self.binding.static;changed['states']['pending']='f'*64
        self.binding._spec=json.dumps(changed,sort_keys=True,separators=(',',':'))
        self.assertRaisesRegex(ValueError,'retained static binding changed',self.binding.check)

    def test_static_schema_scope_and_owner_mismatches(self):
        for mutation in (lambda d:d.update(boot_id=BOOT),lambda d:d['target'].update(owner=OWNER),
            lambda d:d.update(owner=True),lambda d:d['target'].update(descriptor_sha256='b'*64),
            lambda d:d['states'].update(healthy=d['states']['old'])):
            s=copy.deepcopy(self.spec);mutation(s)
            with self.assertRaises(ValueError):self.ad.cold_schema(s)
        for key,value in [('owner','b'*32),('source_boot_id',BOOT)]:
            self.lock['production_cold_boot'][key]=value;self.reseal_fixture()
            with self.assertRaises(ValueError):self.ad.ColdBoot(self.ad,self.g,OWNER)
            self.lock['production_cold_boot']=copy.deepcopy(self.spec)
        for names in (list(self.ad.PRODUCTION_PATHS)+['foreign.py'],list(self.ad.PRODUCTION_PATHS[:-1])+[self.ad.PRODUCTION_PATHS[0]]):
            self.lock['production_display_sources']=names;self.reseal_fixture()
            with self.assertRaises(ValueError):self.ad.inputs()

    def test_authentication_and_decoder_refuse_before_structure_acceptance(self):
        self.lock_raw+=b' ';self.assertRaises(ValueError,self.ad.inputs)
        for raw in (b'{"files":{},"files":{}}',b'{"nested":{"a":1,"a":2}}',b'{"x":NaN}'):
            self.assertRaises(ValueError,self.a.decode,raw)

    def test_actual_missing_static_or_private_dependency_precedes_credentials(self):
        for function in (self.l.run,self.l._run_once):
            with self.assertRaisesRegex(ValueError,'unresolved source dependency'):
                function(authenticate=True,contract=self.binding,owner=OWNER)
            self.assertFalse(self.l.LAUNCH.exists());self.assertFalse(self.l.LOCK.exists())
        self.lock.pop('production_cold_boot');self.lock['format']='rog5-live-admission-inputs-v1';self.reseal_fixture()
        with self.assertRaisesRegex(ValueError,'cold-boot inputs absent'):self.l.run(authenticate=True,owner=OWNER)
        self.assertEqual(self.events,[])

    def test_wrong_health_seal_and_recovery_generator_stay_refused(self):
        self.ready()
        old=self.h.SEAL;self.h.SEAL=dict(target=self.c.TARGET)
        with self.assertRaisesRegex(ValueError,'historical or incompatible'):self.binding.check()
        self.h.SEAL=old
        self.guard.OPERATIONS['restore-target']=(self.c.TARGET['bundle'],self.c.TARGET['release'],'inert')
        with patch.object(self.g,'initialize',noop):
            with self.assertRaisesRegex(ValueError,'unqualified target recovery'):self.binding.runtime_ready()

    def test_module_identity_disagreement_is_not_silently_rebound(self):
        original=self.g.H;self.g.H=NS()
        self.assertRaises(ValueError,self.binding.check);self.g.H=original
        self.wrapper.F=NS();self.assertRaises(ValueError,self.binding.check)

    def test_coordinated_controller_and_both_readers_and_session_admission(self):
        controller,result=self.run_success()
        self.assertIs(self.inner.health.production,self.inner.fastboot.health.production)
        self.assertIs(self.inner.health.health,self.g.H)
        self.assertIs(self.inner.fastboot.health.health,self.g.H)
        self.assertNotEqual(self.binding.target,self.c.TARGET)
        expected=self.binding.expected(BOOT,OWNER)
        self.assertEqual(result['target_identity'],expected);self.assertEqual(len(expected),6)
        self.assertEqual(self.g.admission(self.ad,controller,NS(check=noop),result,self.binding.session_contract())[1],expected)
        self.assertEqual(self.ad.selected_boot(),BOOT)
        with self.assertRaisesRegex(ValueError,'repeated phase'):controller.action('observe_target')
        self.assertEqual(self.binding._contract.expected(BOOT,OWNER),expected)

    def test_discovery_wrong_boot_release_bundle_and_source_refuse(self):
        for field,value in [('boot_id',SOURCE_BOOT),('boot_id','00000000-0000-0000-0000-000000000000'),
                            ('bundle','wrong'),('release','wrong')]:
            identity=dict(boot_id=BOOT,**self.binding.target);identity[field]=value
            with self.subTest(field=field,value=value):self.assertRaises(ValueError,self.binding.discovery,identity)

    def test_bound_boot_conflict_and_mutated_contract_refuse(self):
        controller,result=self.run_success();original=self.binding._contract
        with self.assertRaisesRegex(ValueError,'selection changed'):
            self.binding.discovery(dict(boot_id=FALLBACK_BOOT,**self.binding.target))
        self.assertIs(self.binding._contract,original)
        original._binding['descriptor_sha256']='d'*64
        self.assertRaises(ValueError,self.binding.session_contract)

    def test_unproved_binding_cannot_enter_session_after_health_failure(self):
        controller=self.build_driver();self.health_change=dict(artifact_identity_after=dict(self.spec['target'],owner=OWNER,boot_id=FALLBACK_BOOT))
        # Leave the controller's actual first-discovery and full health path intact;
        # stop at its mandatory recovery dependency boundary without device work.
        with patch.object(controller,'restore_fallback',side_effect=ValueError('inert recovery unavailable')):
            result=controller.run()
        self.assertEqual(result['status'],'FAIL');self.assertEqual(self.binding.selected_boot,BOOT)
        self.assertFalse(self.binding._proved);self.assertRaises(ValueError,self.binding.session_contract)
        self.assertEqual(self.ad.selected_boot(),BOOT)

    def test_descriptor_board_owner_drift_fail_actual_health_validator(self):
        self.run_success()
        for field in ('descriptor_sha256','board_dtb_sha256','owner'):
            raw=self.health_value();raw['artifact_identity_after'][field]='x'
            with self.subTest(field=field):self.assertRaises(ValueError,self.binding.validate,json.dumps(raw).encode(),BOOT)

    def test_retained_binding_receipt_replacement_is_not_adopted(self):
        self.run_success();path=self.c.OUTPUT/'production-boot-binding.json'
        value=json.loads(path.read_bytes());value['identity']['descriptor_sha256']='f'*64
        path.write_text(json.dumps(value))
        self.assertRaises(ValueError,self.binding.check)

    def test_construct_failure_cannot_rebind_a_new_or_same_uuid(self):
        controller=self.build_driver()
        with patch.object(self.g,'host_contract',side_effect=ValueError('injected source construction failure')), \
             patch.object(controller,'restore_fallback',side_effect=ValueError('inert recovery unavailable')):
            result=controller.run()
        self.assertEqual(result['status'],'FAIL');self.assertEqual(self.binding.selected_boot,BOOT)
        self.assertIsNone(self.binding._contract)
        self.assertRaises(ValueError,self.binding.session_contract)
        self.assertRaises(ValueError,self.binding.discovery,dict(boot_id=FALLBACK_BOOT,**self.binding.target))

    def test_actual_target_recovery_and_restored_identity6(self):
        controller,result=self.run_success()
        def stage(obj,context,results,pin):
            proof=obj.target_recovery_proof(results)
            return dict(status='PASS',identity=proof['identity'],ram_files_verified=True)
        def restore(obj,context,results,pin):
            proof=obj.target_recovery_proof(results)
            return dict(status='PASS',identity=proof['identity'],before_sha256=self.binding.states['healthy'],
                        after_sha256=self.binding.states['old'],completed=True)
        # The missing privileged generators, not the target identity validators,
        # are inert. All controller/action/health recovery validators are real.
        self.inner.bindings['stage_target_recovery']=lambda *a:stage(self.inner.actions,*a)
        self.inner.bindings['restore_target_state']=lambda *a:restore(self.inner.actions,*a)
        controller.restore_fallback()
        self.assertTrue(controller.selection_restored)
        proof=controller.results['verify_target_restoration']
        self.assertEqual(proof['identity'],result['target_identity'])
        self.assertEqual(proof['state_sha256'],self.binding.states['old'])
        self.assertTrue(proof['selection_eligibility_restored'])

    def test_restoration_combiner_requires_real_endpoint_and_legacy_proofs(self):
        self.run_success();raw=self.restoration_raw(BOOT,'target');contract=self.binding.session_contract()
        self.assertEqual(self.f.parse_production(raw,BOOT,contract,OWNER)['identity'],self.binding.expected(BOOT,OWNER))
        script=self.f.build_production(BOOT,contract,OWNER);compile(script,'<NOT EXECUTED>','exec')
        for change in (dict(artifact_after={}),dict(restoration_base64=base64.b64encode(b'broken\n').decode())):
            value=json.loads(raw);value.update(change)
            self.assertRaises(ValueError,self.f.parse_production,json.dumps(value).encode(),BOOT,contract,OWNER)

    def test_fallback_remains_exact_identity3(self):
        proof=self.f.parse(self.restoration_raw(FALLBACK_BOOT,'fallback'),'verify-restored',FALLBACK_BOOT,'fallback')
        self.c.same_identity(proof['identity'],self.c.FALLBACK,excluded=(SOURCE_BOOT,))
        self.assertEqual(set(proof['identity']),set(self.ad.DISCOVERY_FIELDS))
        self.assertRaises(ValueError,self.c.same_identity,dict(proof['identity'],owner=OWNER),self.c.FALLBACK)

    def test_history_and_target_phase_gates_are_not_waived(self):
        self.run_success();results=self.controller.results;entered=set(self.controller.entered)
        for phase in ('restore_target_state','verify_target_restoration','stage_fallback'):
            self.assertRaises(ValueError,self.ad.policy,phase,results,entered,contract=self.binding,owner=OWNER)
        bad=dict(results);bad['close_capture']=dict(results['close_capture'],full_lifetime=False)
        self.assertRaises(ValueError,self.ad.policy,'locate_fallback',bad,entered,contract=self.binding,owner=OWNER)
        bad_context=dict(self.controller.context,owner='b'*32)
        self.assertRaises(ValueError,self.ad.phase,'locate_fallback',bad_context,results,contract=self.binding,owner=OWNER)

    def test_actual_session_entry_call_uses_bound_hostcontract(self):
        controller,trial=self.run_success()
        tree=ast.parse((self.base/L).read_bytes())
        call,=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and ast.unparse(n.func)=='G.run']
        ns=dict(G=self.g,AD=self.ad,controller=controller,credentials=NS(check=noop),trial=trial,contract=self.binding)
        with self.assertRaisesRegex(ValueError,'unresolved source dependency'):
            eval(compile(ast.Expression(call),'<actual launcher session call>','eval'),ns)
        self.assertFalse(self.g.OUTPUT.exists())

    def test_failed_capture_remains_failed_even_with_target_recovery(self):
        controller=self.build_driver()
        self.inner.bindings['close_capture']=lambda *a:dict(status='PASS',capture_started=True,full_lifetime=True,cleanup_complete=True,capture_status='FAIL')
        # A failed capture cannot be promoted by a successful selection restore.
        with patch.object(controller,'restore_fallback',lambda:setattr(controller,'selection_restored',True)):
            result=controller.run()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['selection_eligibility_restored'])
        self.assertNotIn('post_capture_health',result['phases'])

    def test_old_source_counterexamples_are_still_real(self):
        old=definitions(self.sections[C],'old_controller',constants=('TARGET','HEALTHY'))
        identity=dict(self.spec['target'],owner=OWNER,boot_id=BOOT)
        self.assertRaisesRegex(ValueError,'identity fields',old.same_identity,identity,old.TARGET)
        holder=NS(context=dict(source=dict(boot_id=SOURCE_BOOT)),target_identity=None)
        proof=dict(identity=identity,state_sha256=old.HEALTHY,current_boot_healthy=True,readiness_boot_bound=True,physical_guards_passed=True)
        self.assertRaises(ValueError,old.Controller.target_health,holder,proof)
        tree=ast.parse(self.sections[WR])
        for name in ('script','validate'):
            call,=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                   and ast.unparse(n.func)=='H.'+name]
            with self.assertRaisesRegex(TypeError,'contract'):
                eval(compile(ast.Expression(call),'<old actual wrapper call>','eval'),dict(H=self.h,A=self.a,out=b'{}',boot=BOOT))

    def test_other_three_executed_old_wrapper_identity_counterexamples(self):
        oldc=definitions(self.sections[C],'old_identity_core',constants=('TARGET',))
        oldc.save=noop
        olda=NS(C=oldc,SOURCE_BOOT=SOURCE_BOOT,exact_json=self.a.exact_json,
                fields=self.a.fields,decode=self.a.decode,SHELL='inert-shell',W=self.w)
        old=definitions(self.sections[WR],'old_wrapper',dict(A=olda,need=self.a.need,OUTPUT=self.root,
            H=NS(script=lambda *a:'inert',validate=lambda *a:dict(identity=identity6))),('DISCOVERY',))
        old.pins=noop
        identity3=dict(boot_id=BOOT,**oldc.TARGET)
        identity6=dict(identity3,owner=OWNER,descriptor_sha256='a'*64,board_dtb_sha256='b'*64)
        reader=old.HealthReads.__new__(old.HealthReads)
        reader.gate=lambda *a:dict(monotonic=time.monotonic())
        reader.deployed=self.deployed
        data=''.join(k+'='+v+'\n' for k,v in dict(identity3,ready='ready').items()).encode()
        reader.command=lambda phase,label,*args:(0,data if label.startswith('discovery') else b'{}',b'')
        with self.assertRaisesRegex(ValueError,'target recovery boot changed'):
            reader.location_role(dict(identity3,ready='ready'),dict(observe_target=dict(identity=identity6)))
        with self.assertRaisesRegex(ValueError,'health proof identity changed'):
            reader.observe('observe_target',{}, {},'inert')
        previous=dict(observe_target=dict(identity=identity6),close_capture=dict(cleanup_complete=True,full_lifetime=True,capture_status='PASS'))
        with self.assertRaisesRegex(ValueError,'identity fields'):
            reader.observe('post_capture_health',{},previous,'inert')

    def test_static_board_health_digest_and_boot_image_mismatch(self):
        self.lock['production_cold_boot']['target']['board_dtb_sha256']='0'*64
        self.reseal_fixture()
        self.assertRaisesRegex(ValueError,'endpoint artifact',self.ad.ColdBoot,self.ad,self.g,OWNER)
        self.lock['production_cold_boot']=copy.deepcopy(self.spec)
        self.lock['production_cold_boot']['health_inputs_sha256']='0'*64
        self.reseal_fixture();self.assertRaisesRegex(ValueError,'authenticated file inventory',self.ad.inputs)
        self.lock['production_cold_boot']=copy.deepcopy(self.spec);self.reseal_fixture()
        self.ad.D.BOOT.IMAGE_SHA='0'*64
        with patch.object(self.g,'initialize',noop):
            self.assertRaisesRegex(ValueError,'cold boot image differs',self.binding.runtime_ready)
        self.assertEqual(self.events,[])

    def test_early_fallback_without_any_target_uuid_preserves_legacy_route(self):
        controller=self.build_driver();self.only_fallback=True
        def fail_boot(*args):raise ValueError('inert ambiguous boot failure')
        self.inner.bindings['boot_once']=fail_boot
        def stage(context,results,pin):
            proof=results['locate_fallback']
            self.c.same_identity(proof['identity'],self.c.FALLBACK,excluded=(SOURCE_BOOT,))
            return dict(status='PASS',identity=proof['identity'],ram_files_verified=True)
        def restore(context,results,pin):
            return dict(status='PASS',identity=results['locate_fallback']['identity'],
                before_sha256=self.binding.states['pending'],after_sha256=self.binding.states['old'],completed=True)
        self.inner.bindings['stage_fallback']=stage
        self.inner.bindings['restore_fallback_state']=restore
        result=controller.run()
        self.assertEqual(result['status'],'FAIL',result)
        self.assertTrue(result['selection_eligibility_restored'],result)
        self.assertIsNone(self.binding.selected_boot)
        self.assertEqual(set(controller.results['verify_fallback_restoration']['identity']),set(self.ad.DISCOVERY_FIELDS))
        self.assertEqual(self.ad.policy_states(),self.binding.states)

    def test_launcher_to_controller_to_session_uses_one_late_contract(self):
        api=self;display_calls=[];claims=[]
        class Credentials:
            def __init__(self,path):self.started=time.monotonic()
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def check(self):pass
        self.l.K=NS(Credentials=Credentials)
        self.l.ADMISSION_SHA='e'*64
        self.l.B=NS(PROFILE_ID='inert-fixture-not-a-claim',SERIAL='inert',
            CLAIMS=NS(consume=lambda *args:claims.append('inert-consume-call')),canonical=noop)
        self.ad.D.BOOT.IMAGE_SHA='d'*64
        self.ad.PREP=NS(prior_and_staging=noop,observe_fresh=lambda *args:'a'*64,verify_ready=noop)
        self.ad.S=NS(process_identity=lambda pid:dict(uids=[1000]*4,start='inert-start'))
        def assemble(source,*,contract,owner):
            self.assertIs(contract,self.binding);self.assertIsNone(contract.selected_boot)
            inner=self.build_driver(create_controller=False)
            return inner,NS(close=noop)
        def session(ad,controller,credentials,trial,contract):
            display_calls.append(contract)
            self.assertIs(contract,self.binding._contract)
            self.g.admission(ad,controller,credentials,trial,contract)
            return dict(status='PASS_PRODUCTION_DISPLAY_SESSION',scope='inert display effect fixture')
        with patch.object(self.g,'initialize',noop),patch.object(self.g,'run',session), \
             patch.object(self.ad,'assemble',assemble),patch.object(self.ad,'qualification',lambda *args:'q'*64), \
             patch.object(self.l,'registered_claim',lambda:dict(inert=True)),patch.object(self.l,'pending_claim',noop):
            result=self.l._run_once(contract=self.binding,owner=OWNER)
        self.assertEqual(result['status'],'COMPONENT_PASS',result)
        self.assertEqual(claims,['inert-consume-call']);self.assertEqual(len(display_calls),1)
        self.assertEqual(result['trial']['target_identity'],self.binding.expected(BOOT,OWNER))

    def test_binding_is_constructed_once_and_both_readers_refuse_replacement(self):
        original=self.g.host_contract;calls=[]
        def construct(*args):calls.append(args);return original(*args)
        with patch.object(self.g,'host_contract',construct):self.run_success()
        self.assertEqual(len(calls),1)  # post_capture_health reused the object.
        self.inner.fastboot.health.health=NS()
        with self.assertRaisesRegex(ValueError,'health module changed'):
            self.inner.fastboot.health.gate('locate_fallback',self.controller.context,self.controller.results,'inert')

    def test_policy_wrong_owner_contract_and_source_fail_before_transport(self):
        self.run_success();controller=self.controller
        request=dict(format='rog5-one-usb-command-v1',mode='normal',remote='python3 -I -B -',
                     script=self.binding.script(BOOT),source=self.source,timeout=35)
        for contract,owner in ((None,OWNER),(self.binding,'b'*32),(self.binding,None)):
            self.assertRaises(ValueError,self.ad.command_policy,'post_capture_health',controller.context,
                controller.results,'inert',request,self.source,contract=contract,owner=owner)
        changed=dict(request,source=dict(self.source,revision='changed'))
        self.assertRaises(ValueError,self.ad.command_policy,'post_capture_health',controller.context,
            controller.results,'inert',changed,self.source,contract=self.binding,owner=OWNER)
        for owner in (None,'b'*32):
            self.assertRaises(ValueError,self.l.production_preflight,self.binding,owner)

    def test_changed_static_during_credentials_refuses_before_claim(self):
        api=self
        class Credentials:
            def __init__(self,path):self.started=time.monotonic()
            def __enter__(self):
                api.lock['production_cold_boot']['ssh_fingerprint']='SHA256:'+'b'*43
                api.reseal_fixture();return self
            def __exit__(self,*args):return False
        self.l.K=NS(Credentials=Credentials)
        self.l.B=NS(CLAIMS=NS(consume=self.forbidden))
        self.ad.PREP=NS(prior_and_staging=noop,observe_fresh=self.forbidden)
        with patch.object(self.g,'initialize',noop),patch.object(self.ad,'qualification',lambda *args:'q'*64), \
             patch.object(self.l,'registered_claim',lambda:dict(inert=True)),patch.object(self.l,'pending_claim',noop):
            result=self.l._run_once(contract=self.binding,owner=OWNER)
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('authenticated cold input changed',result['error']['reason'])
        self.assertFalse(result['claim_consumption_entered']);self.assertEqual(self.events,[])
        self.assertFalse((self.l.LAUNCH/'claim-consumption-entered.json').exists())

    def test_source_and_lifecycle_guards_remain_unchanged(self):
        groups={C:('same_identity','save'),AC:('need','unique','decode','exact_json','state_reply','save_transport'),
                F:('operation','build','parse'),AD:('common','claim','qualification','digest_file','authorize_transport','capture_launch_authorize'),
                L:('registered_claim','pending_claim','record','close_owned','closed_authentication_attempts')}
        for file,names in groups.items():
            old=ast.parse(self.sections[file]);new=ast.parse((self.base/file).read_bytes())
            for name in names:
                def fn(tree):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
                self.assertEqual(ast.dump(fn(old)),ast.dump(fn(new)),(file,name))
        for file in (AD,L,WR,FB,DR,AC,F,C):
            old=ast.parse(self.sections[file]);new=ast.parse((self.base/file).read_bytes())
            def pins(tree):
                return {t.id:ast.dump(n.value) for n in tree.body if isinstance(n,ast.Assign) for t in n.targets
                        if isinstance(t,ast.Name) and (t.id.endswith('_SHA') or t.id in ('SOURCE','TARGET','FALLBACK'))}
            self.assertEqual(pins(old),pins(new),file)
        self.assertNotIn("H = load('health_read_target'",(self.base/WR).read_text())
        self.assertEqual(set(self.g.PATHS),set(self.ad.PRODUCTION_PATHS))

if __name__=='__main__':unittest.main(argv=[__file__,*REST],verbosity=2)
