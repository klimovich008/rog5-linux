#!/usr/bin/env python3
"""Actual worker graph and acceptance over inert Git; external authority is a fixture.

The checked-loader fixture uses the supplied session.source_read. The acceptance
module is actual source, exercised in a disposable local Git repository. This
does not qualify the private input authentication or an admitted host identity.
No private imports, credentials, root, network command or phone execution.
"""
import argparse
import ast
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

P=argparse.ArgumentParser()
P.add_argument('--packet',type=Path,required=True)
P.add_argument('--patch',type=Path,required=True)
P.add_argument('--sources',type=Path,required=True)
P.add_argument('--acceptance',type=Path,required=True)
P.add_argument('--case',action='append',default=[])
ARGS=P.parse_args()
PREFIX='oled-startup-controller-worktree-r1/scripts/host/'
WORKER='oled-startup-live-driver-r1/ssh-worker.py'
NS=types.SimpleNamespace

def sha(data):return hashlib.sha256(data).hexdigest()

def source_module(path,name):
    result=types.ModuleType(name);result.__file__=str(path);result.__source__=path.read_bytes()
    exec(compile(result.__source__,str(path),'exec'),result.__dict__)
    return result


def packet(path):
    values={}
    pattern=rb'^===== FILE (.+?) SHA256 ([0-9a-f]{64}) ORIGINAL_SHA256 (.*?) =====\n(.*?)^===== END FILE ====='
    for match in re.finditer(pattern,path.read_bytes(),re.M|re.S):
        name,pin,_,body=match.groups();name=name.decode();raw=body[:-1]
        if sha(raw)!=pin.decode() or name in values:raise ValueError('packet hash/duplicate: '+name)
        values[name]=raw
    return values


class CheckedLoaderFixture:
    """Synthetic external lock, complete preflight, captured bytes, path cache.

    The real source loader is NOT supplied for this private closure. Reuse the
    production bounded reader; do not treat this fixture as an admission issuer.
    """
    def __init__(self,session,rows):
        self.session=session;self.rows=rows;self.stamps=None;self.modules={};self.calls=[]
    def __call__(self,name,path,pin):
        key=str(path.relative_to(self.session.STATE))
        if key not in self.rows or self.rows[key]['sha256']!=pin:raise ValueError('fixture unqualified source: '+key)
        blobs={};stamps={}
        for relative,row in self.rows.items():
            blobs[relative],stamps[relative]=self.session.source_read(relative,row)
        if self.stamps is not None and stamps!=self.stamps:raise ValueError('fixture retained source replacement')
        self.stamps=stamps
        self.calls.append(key)
        if key not in self.modules:
            module=types.ModuleType(name);module.__file__=str(path);module.__source__=blobs[key]
            exec(compile(module.__source__,str(path),'exec'),module.__dict__)
            self.modules[key]=module
        return self.modules[key]


class Binding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError('ordinary UID1000 required')
        cls.contents=packet(ARGS.packet)
        acceptance=ARGS.acceptance.read_bytes()
        if sha(acceptance)!='7eab4bb7cabfc618771e60d1d7a8b64d3ed43a5e92d375fbc7aafd4e227992d2':
            raise ValueError('exact original acceptance source required')
        cls.contents['release-acceptance.py.txt']=acceptance
        cls.temp=tempfile.TemporaryDirectory(prefix='worker-source-',dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temp.cleanup);cls.base=Path(cls.temp.name)
        cls.before=cls.base/'before';cls.after=cls.base/'after';cls.assembled=cls.base/'assembled'
        for directory in (cls.before,cls.after,cls.assembled):directory.mkdir()
        for name,raw in cls.contents.items():
            for directory in (cls.before,cls.after):
                path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        for options in (['--check'],[]):
            subprocess.run(['git','apply',*options,str(ARGS.patch.resolve())],cwd=cls.after,
                           capture_output=True,check=True,timeout=10)
        cls.cohort=source_module(cls.before/'test-production-display-cohort.py','actual_cohort_fixture')
        # Reuse existing exact assembly inputs, not a whole repository rebuild.
        old=source_module(ARGS.sources/'session.py','exact_session')
        for name,pin in old.PINS.items():
            filename='health.py' if name.endswith('successor-health.py') else Path(name).name
            if sha((ARGS.sources/filename).read_bytes())!=pin:raise ValueError('exact public source required: '+filename)
        if sha((ARGS.sources/'session.py').read_bytes())!=sha(cls.contents['production-cohort/session.py']):
            raise ValueError('wrong baseline session')
        for path in ARGS.sources.glob('*.py'):shutil.copyfile(path,cls.assembled/path.name)
        shutil.copyfile(cls.after/'production-cohort/session.py',cls.assembled/'session.py')

    def setUp(self):
        self.h=self.cohort.Cohort();self.h.base=self.base;self.h.assembled=self.assembled
        self.h.setUp();self.addCleanup(self.h.doCleanups)
        self.s=self.h.s;self.root=self.h.root
        self.s.bind_sources(self.h.ad);self.t=self.s.T;self.k=self.s.K
        self.events=[];self.rows={}
        source_policy=(self.after/'release-acceptance.py.txt').read_bytes()
        inputs={WORKER:(self.after/'ssh-worker.py.txt').read_bytes(),
                PREFIX+'check-deployed-server.py':(self.after/'check-deployed-server.py.txt').read_bytes(),
                PREFIX+'headless-stage-receiver.py':(self.after/'headless-stage-receiver.py.txt').read_bytes(),
                PREFIX+'rescue-capture-network.py':self.contents['rescue-capture-network.py.txt'],
                PREFIX+'release-acceptance.py':source_policy}
        for name,raw in inputs.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o644)
            self.rows[name]=dict(size=len(raw),uid=1000,mode=0o644,sha256=sha(raw))
        self.repo=self.root/'oled-startup-controller-worktree-r1'
        self.git_env={'PATH':'/usr/bin:/bin','HOME':str(self.root),'LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1',
                      'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null'}
        def git(*args):
            return subprocess.check_output(['/usr/bin/git','-C',str(self.repo),*args],env=self.git_env,stderr=subprocess.DEVNULL,timeout=5)
        self.git=git
        git('init','--quiet','--template=','--initial-branch=fixture')
        git('add','.')
        git('-c','user.name=Fixture','-c','user.email=fixture.invalid','commit','--quiet','--no-gpg-sign','-m','Inert sources')
        self.original_acceptance=source_module(self.before/'release-acceptance.py.txt','original_acceptance')
        self.observed=self.original_acceptance.source_identity(self.repo)
        self.t.SOURCE=dict(self.observed)  # Inert request expectation, never the historical production pin.
        self.loader=CheckedLoaderFixture(self.s,self.rows)
        self.w=self.load(WORKER);self.d=self.load(PREFIX+'check-deployed-server.py')
        self.c=self.load(PREFIX+'headless-stage-receiver.py');self.n=self.load(PREFIX+'rescue-capture-network.py')
        self.a=self.load(PREFIX+'release-acceptance.py')
        # Explicit replacement-artifact fixture only: the real consumer pin still
        # names the historical worker and is tested separately as incompatible.
        self.t.W=self.k.W=self.w
        # Inert local credential files, never private keys or hosts files.
        self.w.KEY=self.root/'inert-key';self.w.KEY.write_bytes(b'NOT A KEY\n');self.w.KEY.chmod(0o600)
        self.w.HOSTS=self.root/'inert-hosts';self.w.HOSTS.write_bytes(b'NOT HOSTS\n');self.w.HOSTS.chmod(0o600)
        self.w.HOSTS_SHA=sha(self.w.HOSTS.read_bytes());self.w.SERIAL='inert-serial'
        # Actual usb_mode runs against an explicit local topology fixture.
        self.c.USB=self.root/'usb';self.c.USB.mkdir();self.c.ANCHOR=str(self.c.USB)
        for name,value in [('idVendor','1d6b'),('idProduct','0104'),('product','ROG5 persistent root')]:
            (self.c.USB/name).write_text(value+'\n')
        port=self.c.USB/'interface';port.mkdir();driver=self.root/'cdc_ncm';driver.mkdir()
        (port/'driver').symlink_to(driver,target_is_directory=True)
        net=self.root/'net';(net/self.n.INTERFACE).mkdir(parents=True)
        (net/self.n.INTERFACE/'device').symlink_to(port,target_is_directory=True)
        self.c.Path=lambda name:net if str(name)=='/sys/class/net' else Path(name)
        self.c.subprocess=NS(PIPE=subprocess.PIPE,check_output=lambda *a,**kw:json.dumps([
            dict(dev=self.n.INTERFACE,prefsrc='192.0.2.142')]))
        # Packet normalizations use different placeholder alphabets. Preserve
        # production source bytes; align ONLY the returned destination in this
        # test's nonexecuted argv fixture, retaining the actual SSH options.
        ssh=self.d.ssh_command
        def argv(*args):
            result=ssh(*args);result[-1]='root@<IPV4_2>';return result
        self.d.ssh_command=argv
        real=source_module(self.root/WORKER,'actual_command_executor')
        self.command_effect=lambda *args:(self.events.append('inert-command') or dict(reaped=True))
        self.git_observer=lambda argv,result:None
        def execute(argv,script,timeout):
            if argv[0]=='/usr/bin/env':
                result=real.execute(argv,script,timeout);self.git_observer(argv,result);return result
            return self.command_effect(argv,script,timeout)
        self.w.execute=execute

    def load(self,key):return self.loader('fixture',self.root/key,self.rows[key]['sha256'])
    def bind(self):return self.w.bind_deployed(self.loader,self.rows,self.t,self.k)
    def request(self,mode='normal'):
        return self.w.request(json.dumps(dict(format='rog5-one-usb-command-v1',mode=mode,remote='sh -s',
            script='INERT; NEVER EXECUTED',source=dict(self.t.SOURCE),timeout=1)).encode())

    def test_actual_cohort_still_refuses_worker_before_health_or_entries(self):
        # Fresh actual Cohort fixture and actual patched session.run/initialize.
        h=self.cohort.Cohort();h.base=self.base;h.assembled=self.assembled
        h.setUp()
        try:h.test_private_binding_refuses_before_session_output_or_entry()
        finally:h.doCleanups()
        self.assertEqual(self.events,[])

    def test_imports_are_inert_and_no_implicit_filesystem_loader_remains(self):
        before=list(sys.path)
        for key in self.rows:
            m=source_module(self.root/key,'fresh_inert_source')
            if key==WORKER:self.assertRaisesRegex(ValueError,'not bound',m.load_deployed)
        self.assertEqual(before,sys.path);self.assertEqual(self.events,[])
        self.assertIsNone(self.c.STAGES);self.assertIsNone(self.c.CLAIMS);self.assertIsNone(self.c.TEARDOWN)
        self.assertFalse(hasattr(self.w,'load'));self.assertFalse(hasattr(self.c,'load'))

    def test_bound_worker_deployed_and_existing_logger_use_shared_identity(self):
        d=self.bind();self.assertIs(d,self.d);self.assertIs(self.d.CAPTURE,self.c)
        self.assertIs(self.c.NETWORK,self.n);self.assertIs(self.c.ACCEPTANCE,self.a)
        self.assertIs(self.w.load_deployed(),d);self.assertIs(self.bind(),d)
        self.assertEqual(self.a.source_identity(),self.observed)
        # A temporary repo is not the logger's historical admitted source.
        self.assertRaisesRegex(ValueError,'logger source identity',self.k.command)
        argv=self.d.ssh_command(self.w.KEY,self.w.HOSTS)
        self.assertIn('StrictHostKeyChecking=yes',argv);self.assertIn('IdentityAgent=none',argv)
        self.assertEqual(self.events,[])

    def test_missing_transitive_acceptance_refuses_before_binding(self):
        self.rows.pop(PREFIX+'release-acceptance.py')
        self.assertRaisesRegex(ValueError,'source input missing',self.bind)
        self.assertIsNone(self.w._BINDING);self.assertIsNone(self.d.CAPTURE)
        self.assertEqual(self.events,[])

    def test_missing_network_file_refuses_without_binding_or_credentials(self):
        (self.root/(PREFIX+'rescue-capture-network.py')).unlink()
        self.assertRaises(FileNotFoundError,self.bind)
        self.assertIsNone(self.w._BINDING);self.assertEqual(self.events,[])

    def test_each_source_change_after_binding_refuses(self):
        for key in self.rows:
            case=Binding();case.setUp()
            try:
                case.bind();p=case.root/key;raw=p.read_bytes();p.write_bytes(b'!'+raw[1:])
                with self.subTest(key=key):
                    self.assertRaisesRegex(ValueError,re.escape(key),case.w.load_deployed)
                    self.assertEqual(case.events,[])
            finally:case.doCleanups()

    def test_same_byte_replacement_refuses(self):
        self.bind();p=self.root/(PREFIX+'check-deployed-server.py');other=p.with_suffix('.new')
        other.write_bytes(p.read_bytes());other.chmod(0o644);os.replace(other,p)
        self.assertRaises(ValueError,self.w.load_deployed);self.assertEqual(self.events,[])

    def test_foreign_deployed_and_mismatched_shared_worker_refuse(self):
        self.k.W=NS()
        self.assertRaisesRegex(ValueError,'worker identity differs',self.bind)
        self.k.W=self.w;self.bind()
        self.assertRaisesRegex(ValueError,'deployed identity differs',self.w.perform,self.request(),NS())
        self.k.W=NS();self.assertRaisesRegex(ValueError,'shared worker changed',self.w.load_deployed)
        self.assertEqual(self.events,[])

    def test_late_dependency_function_alias_and_input_mutations_refuse(self):
        self.bind()
        with patch.object(self.a,'source_identity',lambda:dict(self.t.SOURCE)):
            self.assertRaises(ValueError,self.w.load_deployed)
        with patch.object(self.d,'CAPTURE',NS()):self.assertRaises(ValueError,self.w.load_deployed)
        with patch.object(self.c,'NETWORK',NS()):self.assertRaises(ValueError,self.w.load_deployed)
        with patch.object(self.n,'INTERFACE','another'):self.assertRaises(ValueError,self.w.load_deployed)
        self.rows[WORKER]['sha256']='f'*64
        self.assertRaises(ValueError,self.w.load_deployed);self.assertEqual(self.events,[])

    def test_failed_binding_is_not_retried_and_loader_cannot_be_switched(self):
        self.bind()
        other=lambda *args:self.loader(*args)
        self.assertRaisesRegex(ValueError,'cannot be replaced',self.w.bind_deployed,other,self.rows,self.t,self.k)
        fresh=source_module(self.root/WORKER,'other_worker');self.t.W=self.k.W=fresh
        self.assertRaisesRegex(ValueError,'another worker',fresh.bind_deployed,self.loader,self.rows,self.t,self.k)
        self.assertRaisesRegex(ValueError,'previous worker binding failed',fresh.bind_deployed,self.loader,self.rows,self.t,self.k)

    def test_cached_module_source_and_file_identity_changes_refuse(self):
        self.bind();key=PREFIX+'check-deployed-server.py'
        with patch.object(self.d,'__file__',str(self.root/'foreign.py')):
            self.assertRaises(ValueError,self.w.load_deployed)
        with patch.object(self.d,'__source__',self.d.__source__+b'\n'):
            self.assertRaises(ValueError,self.w.load_deployed)
        original=self.loader.modules[key];self.loader.modules[key]=NS()
        self.assertRaises(ValueError,self.w.load_deployed);self.loader.modules[key]=original
        with patch.object(self.w,'KEY',self.root/'foreign-key'):
            self.assertRaises(ValueError,self.w.load_deployed)
        self.assertEqual(self.events,[])

    def test_normal_command_uses_same_bound_deployed_and_retains_policy(self):
        self.bind();result=self.w.perform(self.request(),self.d)
        self.assertEqual(result['status'],'PASS_TRANSPORT_COMPLETED')
        self.assertTrue(result['command_invoked']);self.assertFalse(result['network_owned'])
        self.assertEqual(self.events,['inert-command']);self.assertEqual(result['events'],[])

    def test_historical_consumer_pin_does_not_authenticate_changed_worker(self):
        self.t.W=self.k.W=None
        self.assertRaisesRegex(ValueError,'unqualified source',self.t.bind_worker,self.loader)
        self.assertRaisesRegex(ValueError,'unqualified source',self.k.bind_worker,self.loader)
        self.assertIsNone(self.t.W);self.assertIsNone(self.k.W)

    def test_full_capture_and_claim_entrypoints_remain_refused(self):
        self.bind()
        for call in (lambda:self.c.Receiver('inert',self.events.append),lambda:self.c.check_receiver(self.root,'inert'),
                     self.c.main,lambda:self.d.expected_files('inert'),self.d.main):
            with self.assertRaisesRegex(ValueError,'full receiver dependencies'):call()
        self.assertEqual(self.events,[])
        self.assertRaises(FileNotFoundError,self.s.H.bind_runtime,self.s.load)
        self.assertIsNone(self.s.H.A)

    def test_credentials_keep_actual_metadata_and_hash_refusal(self):
        self.bind();self.w.KEY.chmod(0o666)
        result=self.w.perform(self.request(),self.d)
        self.assertEqual(result['status'],'FAIL');self.assertIn('credential metadata',result['reason'])
        self.w.KEY.chmod(0o600);self.w.HOSTS.write_bytes(b'CHANGED\n')
        result=self.w.perform(self.request(),self.d)
        self.assertEqual(result['status'],'FAIL');self.assertIn('host key pin changed',result['reason'])
        self.assertEqual(self.events,[])

    def test_actual_usb_topology_source_and_request_policy_refuse(self):
        self.bind();(self.c.USB/'product').write_text('another phone\n')
        result=self.w.perform(self.request(),self.d)
        self.assertEqual(result['status'],'FAIL');self.assertIn('USB identity/topology',result['reason'])
        (self.c.USB/'product').write_text('ROG5 persistent root\n')
        request=self.request();request['source']['clean']=False
        result=self.w.perform(request,self.d);self.assertEqual(result['status'],'FAIL')
        self.assertEqual(self.events,[])
        request=self.request('linklocal');request['remote']='python3 -I -B -'
        self.assertRaisesRegex(ValueError,'V11 has no Python',self.w.request,json.dumps(request).encode())

    def network_fixture(self):
        state=dict(profile=list(self.n.ORIGINAL),addresses=[],firewall=False,route=[])
        def run(args,**kwargs):
            code=0;out=''
            if args[:2]==['nmcli','-g']:
                out=('\n'.join(state['profile'])+'\n' if args[2]==self.n.FIELDS else self.n.PROFILE)
            elif args[:3]==['nmcli','connection','modify']:state['profile'][-1]=args[-1]
            elif args[:2]==['nmcli','device']:pass
            elif args[:4]==['ip','-j','address','show']:out=json.dumps(state['addresses'])
            elif args[0]=='ss':pass
            elif args[:2]==['firewall-cmd','--state']:out='running'
            elif args[0]=='firewall-cmd':
                if '--query-rich-rule=' in ' '.join(args):code=0 if state['firewall'] else 1
                elif '--add-rich-rule=' in ' '.join(args):state['firewall']=True
                elif '--remove-rich-rule=' in ' '.join(args):state['firewall']=False
                elif '--get-zone-of-interface=' in ' '.join(args):out='nm-shared'
                else:raise AssertionError(args)
            elif args[:4]==['ip','-j','route','show']:out=json.dumps(state['route'])
            elif args[:4]==['ip','-j','route','get']:
                code=0 if state['route'] else 2
                out=json.dumps([dict(dev=self.n.INTERFACE,prefsrc='<IPV4_4>')]) if code==0 else ''
            elif args[:4]==['ip','-j','link','show']:
                out=json.dumps([dict(ifname=self.n.INTERFACE,ifindex=17,flags=['UP'])])
            elif args[:2]==['sysctl','-n']:out='0\n'*4
            elif args[:3]==['ip','route','add']:
                state['route']=[dict(dst=self.n.PEER+'/32',dev=self.n.INTERFACE,prefsrc=self.n.ADDRESS,protocol='static',metric=8079,scope='link')]
            elif args[:3]==['ip','route','del']:state['route']=[]
            elif args[:3]==['ip','address','add']:
                state['addresses']=[dict(ifname='lo',addr_info=[dict(local=self.n.ADDRESS,prefixlen=32,label=args[-1])])]
            elif args[:3]==['ip','address','del']:state['addresses']=[]
            else:raise AssertionError('unmodeled inert network command: '+repr(args))
            return NS(returncode=code,stdout=out)
        self.n.subprocess=NS(run=run)
        return state

    def test_actual_network_cleanup_survives_command_and_source_failure(self):
        state=self.network_fixture()
        # Explicit root-role fixture only; the real test process remains UID1000.
        self.w.os=NS(geteuid=lambda:0)
        def failed(*args):
            self.events.append('inert-command')
            p=self.root/(PREFIX+'release-acceptance.py');p.write_bytes(b'!'+p.read_bytes()[1:])
            return dict(reaped=True)
        self.command_effect=failed;self.bind()
        result=self.w.perform(self.request('linklocal'),self.d)
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['network_owned'])
        cleanup=[(e['item'],e['status']) for e in result['events'] if e.get('event')=='host-cleanup']
        self.assertEqual(cleanup,[(x,'PASS') for x in ('route','firewall','profile','address')])
        self.assertEqual(state,dict(profile=list(self.n.ORIGINAL),addresses=[],firewall=False,route=[]))
        self.assertEqual(self.events,['inert-command'])

    def test_actual_network_cleanup_exception_stays_failure(self):
        state=self.network_fixture();self.w.os=NS(geteuid=lambda:0)
        def changed_profile(*args):state['profile'][-1]='foreign';return dict(reaped=True)
        self.command_effect=changed_profile;self.bind()
        result=self.w.perform(self.request('linklocal'),self.d)
        self.assertEqual(result['status'],'FAIL');self.assertIn('cleanup incomplete',result['reason'])
        self.assertEqual(state['profile'][-1],'foreign')
        self.assertEqual(state['route'],[]);self.assertFalse(state['firewall']);self.assertEqual(state['addresses'],[])

    def test_unprivileged_new_route_still_refuses_before_command(self):
        self.network_fixture();self.bind()
        result=self.w.perform(self.request('linklocal'),self.d)
        self.assertEqual(result['status'],'FAIL');self.assertIn('requires scoped host network privileges',result['reason'])
        self.assertEqual(self.events,[]);self.assertFalse(result['network_owned'])

    def test_unprivileged_borrowed_route_is_not_prepared_or_owned(self):
        state=self.network_fixture();state['route']=[dict(inert_borrowed_route=True)]
        before=copy.deepcopy(state);self.bind()
        result=self.w.perform(self.request('linklocal'),self.d)
        self.assertEqual(result['status'],'PASS_TRANSPORT_COMPLETED')
        self.assertFalse(result['network_owned']);self.assertEqual(result['events'],[])
        self.assertEqual(state,before);self.assertEqual(self.events,['inert-command'])

    def test_actual_execute_timeout_reaps_inert_local_child(self):
        fresh=source_module(self.root/WORKER,'actual_execute')
        before=set(os.listdir('/proc/self/fd'))
        result=fresh.execute([sys.executable,'-I','-B','-c','import time; time.sleep(5)'],'',1)
        self.assertTrue(result['timed_out']);self.assertTrue(result['reaped'])
        self.assertLess(result['returncode'],0)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_unchanged_policy_and_cleanup_bodies(self):
        groups={'ssh-worker.py.txt':('request','credentials','main'),
                'rescue-capture-network.py.txt':('command','profile','addresses','prepared'),
                'headless-stage-receiver.py.txt':('usb_mode','run','update_transport'),
                'check-deployed-server.py.txt':('credential','validate_readiness','validate_snapshot')}
        for file,names in groups.items():
            old=ast.parse(self.contents[file]);new=ast.parse((self.after/file).read_bytes())
            for name in names:
                def node(tree):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
                self.assertEqual(ast.dump(node(old)),ast.dump(node(new)),(file,name))
        self.assertEqual(self.s.PINS,ast.literal_eval(next(n.value for n in ast.parse(self.contents['production-cohort/session.py']).body
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINS' for t in n.targets))))
        self.assertEqual(len(self.s.PATHS),10)
        old=ast.parse(self.contents['ssh-worker.py.txt']);new=ast.parse((self.after/'ssh-worker.py.txt').read_bytes())
        before=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='perform')
        after=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='perform')
        after.body.pop(0)
        next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='source').body.pop(0)
        self.assertEqual(ast.dump(before),ast.dump(after),'perform changed beyond source-binding guards')

if __name__=='__main__':
    names=ARGS.case or sorted(n for n in Binding.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Binding(n) for n in names))
    raise SystemExit(not result.wasSuccessful())
