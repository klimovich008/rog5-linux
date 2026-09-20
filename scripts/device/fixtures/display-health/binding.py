#!/usr/bin/env python3
"""Actual fixed health binding, with explicit synthetic authority/data values.

The existing checked-worker test's authenticated-provider/custody seam is reused.
All new sources execute captured bytes; real ROOT/OBS/readiness/health validators
run. No private top-level import, command, device, credential or claim operation.
"""
import argparse,ast,base64,builtins,copy,hashlib,json,os
from pathlib import Path
import re,runpy,shutil,subprocess,sys,tempfile,types,unittest
from unittest.mock import patch
P=argparse.ArgumentParser();P.add_argument('--packet',type=Path,required=True);P.add_argument('--patch',type=Path,required=True)
P.add_argument('--case',action='append',default=[]);ARGS=P.parse_args()
SOURCE='00000000-1111-2222-3333-444444444444';BOOT='11111111-2222-3333-4444-555555555555';OWNER='a'*32;TRIAL='1'*64
ROOT='health-private/oled-startup-controller-worktree-r1__scripts__host__check-standalone-root.py.txt'
OBS='health-private/oled-startup-controller-worktree-r1__scripts__host__isolated-recovery-observation.py.txt'
COMMON='health-private/gpu-capture-r1__capture-common.py.txt';CORE='health-private/gpu-controller-r1__controller.py.txt'
GUARD='health-private/gpu-state-guards-r1__guarded-state.py.txt';LEGACY='health-private/gpu-state-guards-r1__legacy-restore.py.txt'
ACTION='health-private/oled-startup-live-driver-r1__action-callbacks.py.txt'
HELPER='repo/scripts/device/fixtures/display-worker/checked-loader.py'
PREFIX='oled-startup-controller-worktree-r1/'
MODULES={ROOT:PREFIX+'scripts/host/check-standalone-root.py',OBS:PREFIX+'scripts/host/isolated-recovery-observation.py',
 COMMON:'gpu-capture-r1/capture-common.py',CORE:'gpu-controller-r1/controller.py',GUARD:'gpu-state-guards-r1/guarded-state.py'}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def packet(path):
    out={}
    for m in re.finditer(rb'^===== FILE (.+?) SHA256 ([0-9a-f]{64}) =====\n(.*?)^===== END FILE =====',path.read_bytes(),re.M|re.S):
        name,pin,raw=m.groups();name=name.decode();raw=raw[:-1]
        if name in out or sha(raw)!=pin.decode():raise ValueError('packet source digest: '+name)
        out[name]=raw
    return out

CONTENTS=packet(ARGS.packet)
if sha(CONTENTS[HELPER])!='45754db264fb325868534655d1dc0e5e25a881f5ef1a443ef74afd2ae2aef297':raise ValueError('existing authority fixture changed')
# Load definitions only from the TEST, not an actual private admission module.
ns=dict(__name__='fixture_loader',__file__=str(ARGS.packet),sys=sys)
argv=sys.argv;sys.argv=['checked-loader.py','--packet',str(ARGS.packet),'--patch',str(ARGS.patch),'--sources','/unused-fixture-path']
try:exec(compile(CONTENTS[HELPER],HELPER,'exec'),ns)
finally:sys.argv=argv
Base=ns['Loader'];source_module=ns['source_module']

def constants(raw,changes):
    """Fixture-only replacement of explicitly omitted identity values, before lock capture."""
    text=raw.decode();lines=text.splitlines(True);edits=[]
    for n in ast.parse(text).body:
        if isinstance(n,ast.Assign):
            names=[x.id for x in n.targets if isinstance(x,ast.Name)]
            if len(names)==1 and names[0] in changes:
                edits.append((n.lineno-1,n.end_lineno,names[0]+'='+changes[names[0]]+'\n'))
    if len(edits)!=len(changes):raise ValueError('fixture constant missing')
    for first,last,value in reversed(edits):lines[first:last]=[value]
    return ''.join(lines).encode()


def marker(text,mode=0o444):return dict(status='present',uid=0,gid=0,mode=mode,nlink=1,dev=23,text=text)


class HealthSources(Base):
    @classmethod
    def setUpClass(cls):
        if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError('ordinary UID1000 required')
        tmp=tempfile.TemporaryDirectory(prefix='checked-health-',dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(tmp.cleanup);cls.base=Path(tmp.name);cls.after=cls.base/'after';cls.after.mkdir()
        for name,raw in CONTENTS.items():
            p=cls.after/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        for flags in (['--check'],[]):subprocess.run(['git','apply',*flags,str(ARGS.patch.resolve())],cwd=cls.after,check=True,capture_output=True,timeout=10)
        cls.contents=dict(CONTENTS)
        for name in ('ssh-worker.py','check-deployed-server.py','headless-stage-receiver.py','rescue-capture-network.py','release-acceptance.py'):
            cls.contents[name+'.txt']=CONTENTS['worker-closure/'+name+'.txt']
        session=ast.parse((cls.after/'production-cohort/session.py').read_bytes())
        cls.pins=next(ast.literal_eval(n.value) for n in session.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='PINS' for x in n.targets))
        cls.public={}
        for key,pin in cls.pins.items():
            filename='health.py' if key.endswith('successor-health.py') else Path(key).name
            raw=(cls.after/'production-cohort'/filename).read_bytes()
            if sha(raw)!=pin:raise ValueError('composed public pin differs: '+filename)
            cls.public[key]=raw
        cls.public['gpu-iommu-session-r1/session.py']=(cls.after/'production-cohort/session.py').read_bytes()

    def setUp(self):
        super().setUp()
        self.profile_path=self.root/'fixture-profile.json'
        profile=json.dumps(dict(bundle='fixture-production',release='7.1.4-rog5-production',scope='INERT TEST ONLY')).encode()
        self.selection=(f'format=rog5-persistent-wifi-trial-v1\ntrial_id={TRIAL}\nprimary_bundle=fixture-production\n'
            'primary_manifest_sha256='+'2'*64+'\nfallback_bundle=persistent-native-root-v11\nfallback_manifest_sha256='+'3'*64+'\nstate=healthy\n')
        self.states=dict(old=sha(b'inert old'),pending=sha(b'inert pending'),healthy=sha(self.selection.encode()))
        self.fallback=dict(bundle='persistent-native-root-v11',release='7.1.4-g359318de534f')
        descriptor=f'format=rog5-persistent-wifi-health-v1\ntrial_id={TRIAL}\nprimary_bundle=fixture-production\nmode=try-once\n'
        self.identity=dict(boot_id=BOOT,owner=OWNER,bundle='fixture-production',release='7.1.4-rog5-production',
            descriptor_sha256=sha(descriptor.encode()),board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57')
        self.descriptor=descriptor
        self.seal=dict(source_boot_id=SOURCE,owner=OWNER,target={k:v for k,v in self.identity.items() if k not in ('boot_id','owner')},
            trial_id=TRIAL,healthy_state_sha256=self.states['healthy'],ssh_fingerprint='SHA256:'+'f'*43,files={},producers={})
        for name in ('runtime','healthy','trial','gpu_sqe','gpu_gmu','gpu_zap'):
            self.seal['files'][name]=dict(path='/inert/'+name,size=12,uid=0,gid=0,mode=0o644,nlink=1,sha256='4'*64)
        for filename,key in MODULES.items():
            raw=(self.after/filename).read_bytes()
            if filename==COMMON:raw=constants(raw,dict(PROFILE='Path('+repr(str(self.profile_path))+')',PROFILE_SHA=repr(sha(profile)),OWNER=repr(OWNER),SOURCE_BOOT=repr(SOURCE)))
            if filename==CORE:raw=constants(raw,dict(TARGET=repr({k:self.identity[k] for k in ('bundle','release')}),FALLBACK=repr(self.fallback),
                OLD=repr(self.states['old']),PENDING=repr(self.states['pending']),HEALTHY=repr(self.states['healthy'])))
            if filename==GUARD:raw=constants(raw,dict(LEGACY_SHA=repr(sha(CONTENTS[LEGACY])),OLD_SHA=repr(self.states['old']),
                PENDING_SHA=repr(self.states['pending']),HEALTHY_SHA=repr(self.states['healthy']),TRIAL=repr(TRIAL),BUNDLE=repr('fixture-production')))
            self.install(key,raw)
        self.install('gpu-state-guards-r1/legacy-restore.py',CONTENTS[LEGACY])
        self.install('fixture-profile.json',profile,0o600)
        self.layout=dict(proposal=dict(arch_root_a=dict(number=24,first_lba=100,size_lba=200,name='arch_root_a')))
        self.layout_key=PREFIX+'configs/storage/rog5-dedicated-linux-v1.json'
        self.install(self.layout_key,json.dumps(self.layout).encode())
        for key in (MODULES[ROOT],MODULES[OBS],PREFIX+'scripts/host/check-deployed-server.py'):
            self.seal['producers'][key.removeprefix(PREFIX)]=self.value['files'][key]['sha256']
        self.install_seal()
        # Nothing has bound/captured a source yet. Test-only replacement anchors
        # are computed BEFORE invoking the real checked worker/health readers.
        self.exec_patch.stop()
        self.s=source_module(self.root/'gpu-iommu-session-r1/session.py','actual_test_session')
        original=builtins.exec
        def execute(code,namespace,*args):
            self.executions.append(namespace.get('__file__'));return original(code,namespace,*args)
        self.exec_patch=patch.object(self.s,'exec',execute,create=True);self.exec_patch.start();self.addCleanup(self.exec_patch.stop)
        self.reseal_fixture();self.health_handle=None
        self.block=patch.object(subprocess,'Popen',side_effect=AssertionError('command/device effect forbidden'))
        self.block.start();self.addCleanup(self.block.stop)

    def install(self,key,raw,mode=0o644):
        p=self.root/key;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(mode)
        self.value['files'][key]=dict(size=len(raw),uid=1000,mode=mode,sha256=sha(raw))

    def install_seal(self):
        raw=json.dumps(self.seal).encode();self.install('gpu-iommu-health-r1/health-inputs.json',raw,0o600)
        hkey='gpu-iommu-health-r1/successor-health.py'
        before=(self.root/hkey).read_bytes()
        updated=constants(before,dict(INPUT_SHA=repr(sha(raw))))
        self.install(hkey,updated)
        skey='gpu-iommu-session-r1/session.py'
        text=(self.root/skey).read_text().replace(sha(before),sha(updated));self.install(skey,text.encode())

    def prepare_health(self):
        if self.handle is None:self.prepare()
        self.health_handle=self.s.bind_health_sources(self.ad,authenticated_inputs=self.ad.inputs,profile=self.profile_path)
        return self.health_handle

    def bound(self):
        h=self.prepare_health();self.s.initialize(self.ad);return h

    def health_execs(self):
        return [p for p in self.executions if p in {str(self.root/key) for key in MODULES.values()}]

    def clean_failure(self):
        if self.s.H is not None:
            self.assertTrue(all(getattr(self.s.H,key) is None for key in ('SEAL','ROOT','OBS','A','D')))
        self.assertIsNone(self.s.C);self.assertIsNone(self.s.save)
        self.assertFalse(self.s.OUTPUT.exists());self.assertEqual(self.effects,[])

    def observation(self):
        ident={k:self.identity[k] for k in ('boot_id','bundle','release')}
        root=dict(identity=ident,mountinfo='''1 0 8:24 / /.rog5/root-ro ro - ext4 /dev/sda24 ro,norecovery
2 0 8:23 / /.rog5/userdata-rw rw - ext4 /dev/sda23 rw
3 0 7:0 / /.rog5/state rw - ext4 /dev/loop0 rw
4 0 0:1 / / rw - overlay overlay rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/state/work
''',loops=dict(loop0='/.rog5/userdata-rw/rog5/root/root-overlay-v1.ext4'),root_device='/dev/sda24',
            geometry=dict(partition='24',start='800',size='1600',ro='1',uevent='PARTNAME=arch_root_a\n'),
            blocks={**dict.fromkeys(['sda','sda23'],'0'),**dict.fromkeys(['fixture'+str(i) for i in range(115)],'1')},
            units=dict.fromkeys(('rog5-persistent-state.service','rog5-persistent-ssh-identity.service','rog5-early-sshd.service','rog5-healthd.service'),'active'),
            power=dict(health='Good',temp='300',voltage_now='8500000'),usb_online='1')
        files=dict(descriptor=marker(self.descriptor),healthy=marker(f'format=rog5-native-wifi-healthy-v1\nboot_id={BOOT}\ntrial_id={TRIAL}\nresult=PASS\n'),
            ssh=marker(f'format=rog5-persistent-ssh-identity-v1\nmode=load\nfingerprint=SHA256:{"f"*43}\nidentity_boot_id={BOOT}\n'),
            ready=marker(f'status=PASS\nkernel={ident["release"]}\nssh=strict-key-only\nattested_boot_id={BOOT}\n'),selection=marker(self.selection,0o600))
        h=self.s.H
        value=dict(identity=ident,boot_after=dict(ident),artifact_identity=dict(self.identity),artifact_identity_after=dict(self.identity),root=root,files=files,
            sealed={n:dict(status='present',dev=23,**{k:v[k] for k in ('uid','gid','mode','nlink','sha256')}) for n,v in self.seal['files'].items()},
            unit=dict(zip(h.PROPERTIES,('active','exited','success','0','48000000','58000000'))),timers={},rollback_services={},rollback_exec={},
            services=dict.fromkeys(('rog5-wifi-radio.service','rog5-wifi-wpa.service','rog5-wifi-dhcp.service','rog5-tailscaled.service'),'active\n'),
            marker_fstype='tmpfs\n',uptime='1400.25',physical_guard_passed=True)
        for n in ('rog5-wifi-boot-rollback','rog5-wifi-probe-rollback'):
            value['timers'][n+'.timer']=dict(zip(h.TIMER_PROPERTIES,('loaded','active','waiting','success',n+'.service')))
            value['rollback_services'][n+'.service']=dict(zip(h.ROLLBACK_PROPERTIES,('loaded','inactive','dead','success','0','','','','','')))
            value['rollback_exec'][n+'.service']=dict(type='a(sasbttttuii)',data=[['/run/rog5-native-wifi/runtime',['/run/rog5-native-wifi/runtime','rollback'],False,0,0,0,0,0,0,0]])
        return value

    def contract(self):return self.s.host_contract(self.ad,self.identity)

    def test_default_worker_and_default_health_refusals_remain(self):
        self.reject(lambda:self.s.initialize(self.ad),'unresolved source dependency');self.clean_failure()
        self.prepare();self.s.initialize_worker(self.ad)
        self.reject(lambda:self.s.initialize(self.ad),'unresolved source dependency: '+MODULES[ROOT]);self.clean_failure()

    def test_preflight_executes_no_new_health_source_and_shared_binding(self):
        h=self.prepare_health();self.assertEqual(self.health_execs(),[]);self.assertEqual(h._modules,{})
        self.s.initialize(self.ad)
        self.assertEqual(set(self.health_execs()),{str(self.root/key) for key in MODULES.values()})
        self.assertIs(self.s.T.W,self.s.K.W);self.assertIs(self.s.H.D,self.s.T.W.load_deployed())
        self.assertIs(self.s.H.D,self.s.H.ROOT.D);self.assertIs(self.s.H.D,self.s.H.OBS.D)
        self.assertIs(self.s.H.A.W,self.s.T.W);self.assertIs(self.s.C,self.s.H.A.C);self.assertIs(self.s.save,self.s.C.save)
        self.assertEqual(self.s.C.__file__,str(self.root/MODULES[CORE]));self.assertIsNot(self.s.C,getattr(self.ad,'C',None))
        self.s.initialize(self.ad);self.assertEqual(len(self.health_execs()),5)
        self.assertFalse((self.root/'gpu-capture-r1').joinpath('action-callbacks.py').exists())
        self.assertEqual(self.effects,[])

    def test_old_observer_imports_are_eager_new_imports_are_inert(self):
        for name in (ROOT,OBS):
            module=types.ModuleType('old');module.__file__=str(self.root/MODULES[name])
            with patch('importlib.util.spec_from_file_location',side_effect=ValueError('old eager deployed import')):
                with self.assertRaisesRegex(ValueError,'old eager'):exec(compile(CONTENTS[name],name,'exec'),module.__dict__)
        for name in (ROOT,OBS,COMMON):
            path=self.after/name
            with patch('importlib.util.spec_from_file_location',side_effect=AssertionError('implicit import')):
                module=source_module(path,'inert_after')
            self.assertIsNone(getattr(module,'D',None));self.assertIsNone(getattr(module,'W',None))

    def test_actual_capture_negative_control_has_eager_private_load(self):
        tree=ast.parse(CONTENTS[COMMON]);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OLD' for t in n.targets))
        def no_import(*args):raise ValueError('old eager capture action load')
        with self.assertRaisesRegex(ValueError,'old eager'):exec(compile(ast.Module(body=[node],type_ignores=[]),'old-capture','exec'),dict(load=no_import,LEGACY=self.root))
        with self.assertRaisesRegex(ValueError,'sources absent'):source_module(self.after/COMMON,'inert_common').pinned_sources()

    def test_missing_source_or_data_refuses_before_new_execution(self):
        for key in MODULES.values():
            case=HealthSources();case.setUp()
            try:
                case.prepare();(case.root/key).unlink()
                case.reject(case.prepare_health)
                case.assertEqual(case.health_execs(),[]);case.clean_failure()
            finally:case.doCleanups()

    def test_missing_layout_and_profile_rows_refuse(self):
        for key in (self.layout_key,'fixture-profile.json'):
            case=HealthSources();case.setUp()
            try:
                del case.value['files'][key];case.reseal_fixture()
                case.reject(case.prepare_health);case.assertEqual(case.health_execs(),[]);case.clean_failure()
            finally:case.doCleanups()

    def test_missing_seal_and_legacy_data_are_not_opened_as_modules(self):
        for key in ('gpu-iommu-health-r1/health-inputs.json','gpu-state-guards-r1/legacy-restore.py'):
            case=HealthSources();case.setUp()
            try:
                (case.root/key).unlink();case.reject(case.prepare_health);case.assertEqual(case.health_execs(),[])
            finally:case.doCleanups()

    def test_unauthenticated_or_changed_provider_refuses(self):
        self.reject(lambda:self.s.bind_health_sources(self.ad,authenticated_inputs=self.ad.inputs,profile=self.profile_path),'checked worker authority')
        self.prepare();self.reject(lambda:self.s.bind_health_sources(self.ad,authenticated_inputs=lambda:self.value,profile=self.profile_path),'authority')
        self.raw+=b' ';self.reject(self.prepare_health);self.assertEqual(self.health_execs(),[])

    def test_seal_digest_and_producer_mismatch_precede_new_execution(self):
        self.seal['producers']['scripts/host/check-standalone-root.py']='f'*64
        self.install_seal();self.reseal_fixture()
        # Refresh this not-yet-bound synthetic session after the test-only pin update.
        self.s=source_module(self.root/'gpu-iommu-session-r1/session.py','fixture_reload')
        self.reject(self.prepare_health,'producer/admission pins differ');self.clean_failure()

    def test_historical_and_owner_boot_seal_refusals(self):
        for field,value in (('target',dict(bundle='historical',release='7.1.4-g136f75ae869a')),('owner','b'*32),('source_boot_id',BOOT)):
            case=HealthSources();case.setUp()
            try:
                case.seal[field]=value;case.install_seal();case.reseal_fixture()
                case.s=source_module(case.root/'gpu-iommu-session-r1/session.py','fixture_reload')
                case.reject(case.prepare_health,'incompatible health seal identity');case.clean_failure()
            finally:case.doCleanups()

    def test_missing_or_changed_capture_profile_semantics(self):
        for field,value in (('bundle','different'),('release','different')):
            case=HealthSources();case.setUp()
            try:
                raw=json.loads(case.profile_path.read_bytes());raw[field]=value;raw=json.dumps(raw).encode()
                case.install('fixture-profile.json',raw,0o600)
                key=MODULES[COMMON];case.install(key,constants((case.root/key).read_bytes(),dict(PROFILE_SHA=repr(sha(raw)))))
                case.reseal_fixture();case.prepare_health()
                case.reject(lambda:case.s.initialize(case.ad),'controller/profile/health target');case.clean_failure()
            finally:case.doCleanups()

    def test_profile_hash_or_capture_owner_mismatch(self):
        for field,value in (('PROFILE_SHA',repr('f'*64)),('OWNER',repr('b'*32)),('SOURCE_BOOT',repr(BOOT))):
            case=HealthSources();case.setUp()
            try:
                key=MODULES[COMMON];case.install(key,constants((case.root/key).read_bytes(),{field:value}));case.reseal_fixture();case.prepare_health()
                case.reject(lambda:case.s.initialize(case.ad));case.clean_failure()
            finally:case.doCleanups()

    def test_guard_state_trial_and_fallback_mismatch(self):
        for file,field,value in ((GUARD,'HEALTHY_SHA',repr('f'*64)),(GUARD,'TRIAL',repr('f'*64)),(CORE,'FALLBACK',repr(dict(bundle='other',release='other')))):
            case=HealthSources();case.setUp()
            try:
                key=MODULES[file];case.install(key,constants((case.root/key).read_bytes(),{field:value}));case.reseal_fixture();case.prepare_health()
                case.reject(lambda:case.s.initialize(case.ad));case.clean_failure()
            finally:case.doCleanups()

    def test_retained_guard_digest_still_required(self):
        key=MODULES[GUARD];self.install(key,constants((self.root/key).read_bytes(),dict(LEGACY_SHA=repr('f'*64))));self.reseal_fixture()
        self.prepare_health();self.reject(lambda:self.s.initialize(self.ad),'retained guard source binding');self.clean_failure()

    def test_same_byte_replacement_and_metadata_change_refuse(self):
        h=self.bound();path=self.root/MODULES[OBS];new=path.with_suffix('.replacement');new.write_bytes(path.read_bytes());new.chmod(0o644);os.replace(new,path)
        self.reject(h.check,'retained health input replaced')
        self.reject(lambda:self.s.H.inputs(),'failed')

    def test_changed_seal_after_binding_refuses_without_repin(self):
        self.bound();path=self.root/'gpu-iommu-health-r1/health-inputs.json';path.write_bytes(path.read_bytes()+b' ')
        self.reject(lambda:self.s.H.inputs());self.assertFalse(self.s.OUTPUT.exists())

    def test_late_replacement_during_final_preflight_refuses(self):
        self.prepare();original=self.handle.check;count=0
        def check():
            nonlocal count
            answer=original();count+=1
            if count==2:
                path=self.root/MODULES[ROOT];new=path.with_suffix('.replacement');new.write_bytes(path.read_bytes());new.chmod(0o644);os.replace(new,path)
            return answer
        with patch.object(self.handle,'check',check):self.reject(self.prepare_health)
        self.assertEqual(self.health_execs(),[]);self.clean_failure()

    def test_missing_import_and_syntax_fail_entire_preflight(self):
        key=MODULES[COMMON];self.install(key,(self.root/key).read_bytes()+b'\nimport unreviewed_health_dependency\n');self.reseal_fixture()
        self.reject(self.prepare_health,'health project import forbidden');self.assertEqual(self.health_execs(),[])

    def test_worker_mismatch_and_observer_deployed_change_refuse(self):
        self.bound();worker=self.s.K.W;self.s.K.W=types.SimpleNamespace()
        self.reject(lambda:self.s.H.inputs());self.s.K.W=worker
        self.reject(lambda:self.s.H.inputs(),'failed')

    def test_observer_or_guard_links_cannot_be_rebound(self):
        self.bound();h=self.s.H
        for function,args in ((h.ROOT.bind_deployed,(types.SimpleNamespace(),lambda:b'{}',lambda:None)),
                              (h.OBS.bind_deployed,(types.SimpleNamespace(),lambda:None)),
                              (h.A.G.bind_retained_source,((self.root/'gpu-state-guards-r1/legacy-restore.py').read_bytes(),lambda:None))):
            with self.assertRaises(ValueError):function(*args)
        h.ROOT.D=types.SimpleNamespace()
        self.reject(h.inputs,'dependency binding changed')

    def test_publication_interruptions_clear_every_runtime_alias(self):
        for kind in (KeyboardInterrupt,SystemExit):
            for target in ('SEAL,ROOT,OBS,A,D=runtime[:5]','_RUNTIME=runtime',"_RUNTIME_STATE='bound'",'checked.check()'):
                case=HealthSources();case.setUp()
                try:
                    case.prepare_health();raw=(case.root/'gpu-iommu-health-r1/successor-health.py').read_text().splitlines()
                    line=next(i for i,s in enumerate(raw,1) if s.strip()==target)
                    code=case.s.H.bind_runtime.__code__;raised=kind('publication interruption');fired=[];prior=sys.gettrace()
                    def trace(frame,event,arg):
                        if frame.f_code is not code:return None
                        if event=='line' and frame.f_lineno==line and not fired:fired.append(True);raise raised
                        return trace
                    original_runtime=case.health_handle.runtime
                    def runtime():
                        value=original_runtime()
                        # Enable tracing only after the real dependency binding.
                        # The existing caller frame is the actual H.bind_runtime.
                        caller=sys._getframe(1);caller.f_trace=trace;sys.settrace(trace)
                        return value
                    with patch.object(case.health_handle,'runtime',runtime):
                        try:
                            with case.assertRaises(kind) as caught:case.s.initialize(case.ad)
                        finally:sys.settrace(prior)
                    case.assertIs(caught.exception,raised);case.assertTrue(fired);case.clean_failure()
                    case.reject(lambda:case.s.initialize(case.ad));case.assertIs(case.s.T.W,case.s.K.W)
                finally:case.doCleanups()

    def test_failed_partial_dependency_binding_is_not_retried(self):
        handle=self.prepare_health();original=handle._load;raised=KeyboardInterrupt('after common bind')
        def load(role):
            module=original(role)
            if role=='common':
                normal=module.bind_health
                # Raise after the actual common binder returns; no code or
                # validation function is substituted in a cached source module.
                def hook(frame,event,arg):
                    if frame.f_code is normal.__code__ and event=='return':raise raised
                    return hook
                sys.setprofile(hook)
            return module
        prior=sys.getprofile()
        with patch.object(handle,'_load',load):
            try:
                with self.assertRaises(KeyboardInterrupt) as caught:self.s.initialize(self.ad)
            finally:sys.setprofile(prior)
        self.assertIs(caught.exception,raised);self.clean_failure();self.reject(lambda:self.s.initialize(self.ad))

    def test_actual_validation_and_guard_generation_unchanged(self):
        self.bound();contract=self.contract();value=self.observation();h=self.s.H
        result=h.validate(value,'target',BOOT,contract,OWNER)
        self.assertEqual(result['identity'],self.identity);self.assertFalse(result['release_qualified'])
        script=h.script('target',BOOT,contract,OWNER);compile(script,'<GENERATED NOT EXECUTED>','exec')
        guard=h.physical_guard(h.configuration('target',BOOT,contract,OWNER))
        self.assertNotIn('run_helper() {',guard);self.assertIn("printf 'PASS-physical-guard",guard)
        for text in ('storage write scope','power threshold','thermal threshold','prior startup transaction inventory'):
            self.assertIn(text,guard)
        self.assertIs(self.s.save,h.A.C.save);self.assertFalse(self.s.OUTPUT.exists())

    def test_real_predicates_reject_storage_power_markers_and_artifact_drift(self):
        self.bound();h=self.s.H;contract=self.contract();base=self.observation()
        cases=(lambda v:v['root']['blocks'].update(sda23='1'),lambda v:v['root']['power'].update(temp='500'),
            lambda v:v['artifact_identity_after'].update(owner='b'*32),lambda v:v['files']['ready'].update(text='status=PASS\n'),
            lambda v:v['files']['healthy'].update(mode=0o644),lambda v:v['files']['selection'].update(text=self.selection.replace('state=healthy','state=pending')),
            lambda v:v['unit'].update(ExecMainExitTimestampMonotonic='400000000'),
            lambda v:next(iter(v['rollback_services'].values())).update(ExecStartPre='unexpected'),
            lambda v:next(iter(v['timers'].values())).update(ActiveState='inactive'),lambda v:v['sealed']['gpu_sqe'].update(sha256='0'*64))
        for mutate in cases:
            value=copy.deepcopy(base);mutate(value)
            with self.assertRaises(ValueError):h.validate(value,'target',BOOT,contract,OWNER)
        self.assertEqual(h.validate(base,'target',BOOT,contract,OWNER)['status'],'PASS')

    def test_layout_path_reopen_negative_control_and_checked_refusal(self):
        self.bound();value=self.observation()['root'];old=types.ModuleType('old_root')
        tree=ast.parse(CONTENTS[ROOT]);nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual_old_root','exec'),old.__dict__)
        old.D=self.s.H.D
        changed=copy.deepcopy(self.layout);changed['proposal']['arch_root_a']['first_lba']=101
        (self.root/self.layout_key).write_text(json.dumps(changed));value['geometry']['start']='808'
        old.validate(value,value['identity'])  # Old validator reopens the changed data.
        self.reject(lambda:self.s.H.ROOT.validate(value,value['identity']))

    def test_each_retained_health_source_change_refuses(self):
        for key in MODULES.values():
            case=HealthSources();case.setUp()
            try:
                case.bound();path=case.root/key;path.write_bytes(b'!'+path.read_bytes()[1:])
                case.reject(case.s.H.inputs);case.assertFalse(case.s.OUTPUT.exists())
            finally:case.doCleanups()

    def test_syntax_failure_is_found_before_any_new_source_execution(self):
        key=MODULES[COMMON];self.install(key,(self.root/key).read_bytes()+b'\ninvalid python !!!\n');self.reseal_fixture()
        self.reject(self.prepare_health,exception=SyntaxError);self.assertEqual(self.health_execs(),[]);self.clean_failure()

    def test_cache_probe_profile_and_data_metadata_mutations_refuse(self):
        self.bound();self.s.H.ROOT.PROBE+='\n# altered\n'
        self.reject(self.s.H.inputs,'source/module identity changed')
        for target,change in (('profile',lambda p:p.chmod(0o644)),('layout',lambda p:p.chmod(0o600))):
            case=HealthSources();case.setUp()
            try:
                case.bound();change(case.profile_path if target=='profile' else case.root/case.layout_key)
                case.reject(case.s.H.inputs)
            finally:case.doCleanups()

    def test_interruption_after_session_alias_publication_clears_both_stages(self):
        for kind in (KeyboardInterrupt,SystemExit):
            case=HealthSources();case.setUp()
            try:
                h=case.prepare_health();original=h.check;raised=kind('after session health aliases');calls=[]
                def check():
                    result=original()
                    if sys._getframe(1).f_code is case.s.initialize.__code__:
                        calls.append(1);raise raised
                    return result
                with patch.object(h,'check',check):
                    with case.assertRaises(kind) as caught:case.s.initialize(case.ad)
                case.assertIs(caught.exception,raised);case.assertEqual(calls,[1]);case.clean_failure()
                case.reject(lambda:case.s.initialize(case.ad))
            finally:case.doCleanups()

    def test_complete_seal_artifact_drift_fails_actual_configuration(self):
        for field in ('descriptor_sha256','board_dtb_sha256'):
            case=HealthSources();case.setUp()
            try:
                case.seal['target'][field]='f'*64
                case.install_seal();case.reseal_fixture()
                case.s=source_module(case.root/'gpu-iommu-session-r1/session.py','fixture_reload')
                case.bound()
                case.reject(lambda:case.s.H.configuration('target',BOOT,case.contract(),OWNER),
                            'health seal differs from production contract')
                case.reject(lambda:case.s.H.validate(case.observation(),'target',BOOT,case.contract(),OWNER))
                case.assertFalse(case.s.OUTPUT.exists());case.assertEqual(case.effects,[])
            finally:case.doCleanups()

    def test_deep_shared_dependency_replacement_poisoning(self):
        for name in ('NETWORK','ACCEPTANCE','_TRANSPORT','_SOURCE_READER'):
            case=HealthSources();case.setUp()
            try:
                case.bound();capture=case.s.H.D.CAPTURE
                module=capture.ACCEPTANCE if name=='_SOURCE_READER' else capture
                original=getattr(module,name);setattr(module,name,object())
                case.reject(case.s.H.inputs)
                setattr(module,name,original)
                case.reject(case.s.H.inputs,'failed')
                case.assertFalse(case.s.OUTPUT.exists());case.assertEqual(case.effects,[])
            finally:case.doCleanups()

    def test_probes_validators_helpers_and_worker_are_preserved(self):
        def defs(raw):return {n.name:ast.dump(n) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        before=defs(CONTENTS['production-cohort/health.py']);after=defs((self.after/'production-cohort/health.py').read_bytes())
        for name in ('configuration','physical_guard','script','record','latch','rollback_units','validate'):self.assertEqual(before[name],after[name])
        for file,names in ((ROOT,('mounts',)),(OBS,('record','environment','pending','negative','script','collect')),
                           (GUARD,('custody','predecessor_guard','inherited_guard','build'))):
            a=defs(CONTENTS[file]);b=defs((self.after/file).read_bytes())
            for name in names:self.assertEqual(a[name],b[name],(file,name))
        a=defs(CONTENTS[ACTION]);b=defs((self.after/COMMON).read_bytes())
        for name in ('need','sha','unique','decode','exact_json'):self.assertEqual(a[name],b[name])
        for file,names in ((ROOT,('PROBE',)),(OBS,('PROBE',)),('production-cohort/health.py',('COLLECT','SEALED_READER','INPUT_SHA','RECEIPT_SHA','IDENTITY_SHA'))):
            for name in names:self.assertEqual(self.s.source_literal(CONTENTS[file],name),self.s.source_literal((self.after/file).read_bytes(),name))
        a=defs(CONTENTS['production-cohort/session.py']);b=defs((self.after/'production-cohort/session.py').read_bytes())
        for name in ('_WorkerSources','bind_worker_sources','initialize_worker','load','source_read','cohort','admission','run','recovery'):
            self.assertEqual(a[name],b[name],name)
        self.assertEqual(sha(CONTENTS['worker-closure/ssh-worker.py.txt']),'faedbbc0c1010bc88f5837c31c8b2714b76c8305abf826cb67ee43958c55b851')
        self.assertEqual(CONTENTS[CORE],(self.after/CORE).read_bytes())


if __name__=='__main__':
    names=ARGS.case or sorted(n for n in HealthSources.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(HealthSources(n) for n in names))
    raise SystemExit(not result.wasSuccessful())
