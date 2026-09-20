#!/usr/bin/env python3
"""Actual source-loader and admission functions, no external/runtime authority.

The input bytes/anchor, omitted preloaded admission graph, decoder and historical
custody are explicit fixtures. ad.inputs/input_schema/digest_file execute actual
source definitions; only the historical custody rows delegate to an inert seam.
All five private sources and public cohort execute their actual inert definitions.
No Git/SSH command, credentials, claim, root or health runtime import is performed.
"""
import argparse
import ast
import builtins
import copy
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

P=argparse.ArgumentParser()
P.add_argument('--packet',type=Path,required=True)
P.add_argument('--patch',type=Path,required=True)
P.add_argument('--sources',type=Path,required=True)
P.add_argument('--case',action='append',default=[])
ARGS=P.parse_args()
WORKER='oled-startup-live-driver-r1/ssh-worker.py'
PREFIX='oled-startup-controller-worktree-r1/scripts/host/'
ADMISSION='current-callers/live-admission.py.txt'
OWNER='a'*32
SOURCE_BOOT='00000000-1111-2222-3333-444444444444'
NS=types.SimpleNamespace


def sha(raw):return hashlib.sha256(raw).hexdigest()
def noop(*args,**kwargs):return None

def packet(path):
    result={}
    for m in re.finditer(rb'^===== FILE (.+?) SHA256 ([0-9a-f]{64}) =====\n(.*?)^===== END FILE =====',path.read_bytes(),re.M|re.S):
        name,pin,body=m.groups();name=name.decode();raw=body[:-1]
        if name in result or sha(raw)!=pin.decode():raise ValueError('packet identity: '+name)
        result[name]=raw
    return result

def source_module(path,name):
    m=types.ModuleType(name);m.__file__=str(path);m.__source__=path.read_bytes()
    exec(compile(m.__source__,str(path),'exec'),m.__dict__)
    return m

def unique(rows):
    out={}
    for k,v in rows:
        if k in out:raise ValueError('fixture duplicate JSON key')
        out[k]=v
    return out

def decode(raw):
    def constant(value):raise ValueError('fixture nonfinite JSON')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=constant)


class Loader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError('ordinary UID1000 required; no root test')
        cls.contents=packet(ARGS.packet)
        tmp=tempfile.TemporaryDirectory(prefix='checked-worker-',dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(tmp.cleanup);cls.base=Path(tmp.name)
        cls.after=cls.base/'after';(cls.after/'production-cohort').mkdir(parents=True)
        before=cls.contents['production-cohort/session.py']
        (cls.after/'production-cohort/session.py').write_bytes(before)
        for options in (['--check'],[]):
            subprocess.run(['git','apply',*options,str(ARGS.patch.resolve())],cwd=cls.after,
                           check=True,capture_output=True,timeout=10)
        tree=ast.parse(before)
        cls.pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                      and any(isinstance(t,ast.Name) and t.id=='PINS' for t in n.targets))
        if (ARGS.sources/'session.py').read_bytes()!=before:raise ValueError('exact current session assembly required')
        cls.public={}
        for key,pin in cls.pins.items():
            name='health.py' if key.endswith('successor-health.py') else Path(key).name
            raw=(ARGS.sources/name).read_bytes()
            if sha(raw)!=pin:raise ValueError('exact public source: '+name)
            cls.public[key]=raw
        cls.public['gpu-iommu-session-r1/session.py']=(cls.after/'production-cohort/session.py').read_bytes()

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=self.base));self.executions=[];self.effects=[];self.auth_calls=[]
        self.inputs={**self.public,
            WORKER:self.contents['ssh-worker.py.txt'],
            **{PREFIX+n:self.contents[n+'.txt'] for n in (
                'check-deployed-server.py','headless-stage-receiver.py','rescue-capture-network.py','release-acceptance.py')}}
        self.value=dict(format='rog5-live-admission-inputs-v1',files={},
                        production_display_sources=sorted(self.public))
        for key,raw in self.inputs.items():
            path=self.root/key;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(0o644)
            self.value['files'][key]=dict(size=len(raw),uid=1000,mode=0o644,sha256=sha(raw))
        self.s=source_module(self.root/'gpu-iommu-session-r1/session.py','actual_session')
        path=self.root/'gpu-iommu-live-driver-r1/live-admission.py';path.parent.mkdir();path.write_bytes(self.contents[ADMISSION])
        self.ad=types.ModuleType('actual_admission_definitions');self.ad.__file__=str(path)
        self.ad.__dict__.update(ast=ast,base64=__import__('base64'),hashlib=hashlib,json=json,math=__import__('math'),
                               os=os,Path=Path,re=re,stat=__import__('stat'),time=__import__('time'),
                               STATE=self.root,HERE=path.parent,INPUTS=path.parent/'admission-inputs-r2.json',_CACHE={})
        tree=ast.parse(self.contents[ADMISSION]);names=('need','stamp','digest_file','input_schema','inputs','cold_schema','cold_input_document')
        for name in ('PRODUCTION_PATHS','COLD_FORMAT','HEALTH_INPUT'):
            node,=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),self.ad.__dict__)
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),self.ad.__dict__)
        custody=self.root/'custody-fixture';custody.mkdir()
        for name in ('preparation.json','stage-receipt.json'):
            (custody/name).write_bytes(b'inert custody only\n');(custody/name).chmod(0o600)
        self.ad.A=NS(OWNER=OWNER,SOURCE_BOOT=SOURCE_BOOT,sha=sha,decode=decode,STAGING=custody,
            RECEIPT_SHA='0'*64,CUSTODY_SHA=sha(b'inert custody'),G=NS(custody=lambda *a:b'inert custody'),pinned_sources=noop)
        self.ad.D=NS(BOOT=NS(expected_kernel_relay=lambda:self.auth_calls.append('relay-fixture'),pins=noop),pins=noop)
        self.ad.W=NS(pins=noop);self.ad.H=NS(pins=noop)
        self.ad.R=NS(receipt=lambda p,limit:self.raw if p==self.ad.INPUTS else p.read_bytes())
        self.ad._actual_digest=self.ad.digest_file;self.ad._custody_dir=custody
        # The omitted historical custody seal is not reproducible here. Only its
        # two known rows are an effect seam, not the private/public source rows.
        exec('def digest_file(path,*args):\n'
             '    if path.parent == _custody_dir:\n'
             '        need(path.is_file(), "inert custody fixture absent")\n'
             '        return\n'
             '    return _actual_digest(path,*args)\n',self.ad.__dict__)
        self.reseal_fixture()
        original=builtins.exec
        def execute(code,namespace,*args):
            self.executions.append(namespace.get('__file__'))
            return original(code,namespace,*args)
        self.exec_patch=patch.object(self.s,'exec',execute,create=True);self.exec_patch.start();self.addCleanup(self.exec_patch.stop)
        self.handle=None

    def reseal_fixture(self):
        # In-memory external-authentication fixture. Never output an input lock.
        self.raw=json.dumps(self.value,sort_keys=True,allow_nan=False).encode();self.ad.INPUTS_SHA=sha(self.raw)

    def prepare(self):
        self.handle=self.s.bind_worker_sources(self.ad,authenticated_inputs=self.ad.inputs)
        return self.handle

    def load(self,key=WORKER,name='first_label'):
        return self.handle(name,self.root/key,self.value['files'][key]['sha256'])

    def reject(self,call,text=None,exception=Exception):
        before=set(os.listdir('/proc/self/fd'))
        with self.assertRaises(exception) as caught:call()
        if text:self.assertIn(text,str(caught.exception))
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))
        self.assertFalse(self.s.OUTPUT.exists());self.assertEqual(self.effects,[])
        return caught.exception

    def modify_source(self,key,suffix):
        path=self.root/key;path.write_bytes(path.read_bytes()+suffix)
        self.value['files'][key].update(size=path.stat().st_size,sha256=sha(path.read_bytes()))
        self.reseal_fixture()

    def test_default_actual_public_refusal_unchanged(self):
        self.reject(lambda:self.s.initialize(self.ad),'unresolved source dependency: '+WORKER)
        self.assertIsNone(self.s.T.W);self.assertIsNone(self.s.K.W);self.assertIsNone(self.s.H.A)
        self.assertFalse(any(str(self.root/WORKER)==p for p in self.executions))

    def test_actual_preflight_executes_nothing_then_real_shared_binding(self):
        h=self.prepare();self.assertEqual(self.executions,[]);self.assertEqual(self.s._SOURCE_MODULES,{})
        self.assertEqual(h._modules,{})
        with patch.object(subprocess,'Popen',side_effect=AssertionError('no commands during source binding')):
            deployed=self.s.initialize_worker(self.ad)
        w=self.s.T.W;self.assertIs(w,self.s.K.W);self.assertIs(deployed,w.load_deployed())
        self.assertIs(deployed.CAPTURE.ACCEPTANCE,h._modules[PREFIX+'release-acceptance.py'])
        self.assertIs(deployed.CAPTURE.NETWORK,h._modules[PREFIX+'rescue-capture-network.py'])
        self.assertEqual(set(h._modules),{key for _,key in self.s.WORKER_PATHS})
        self.assertIs(deployed,self.s.initialize_worker(self.ad))
        self.assertIsNone(self.s.H.A);self.assertIsNone(self.s.C);self.assertIsNone(self.s.save)
        self.assertFalse((self.root/WORKER).parent.joinpath('inert-key').exists())

    def test_actual_initialize_stops_at_unchanged_health_boundary(self):
        self.prepare()
        self.reject(lambda:self.s.initialize(self.ad),'health-inputs.json',FileNotFoundError)
        self.assertIs(self.s.T.W,self.s.K.W);self.assertIsNotNone(self.s.T.W.load_deployed())
        self.assertIsNone(self.s.H.A);self.assertIsNone(self.s.C)
        # This stage failure does not pretend the already-source-bound worker was
        # health-qualified or consumed. Its exact binding can be checked again.
        self.assertTrue(self.handle.check())

    def test_arbitrary_dict_missing_reader_or_other_callable_is_not_authority(self):
        self.reject(lambda:self.s.bind_worker_sources(self.value,authenticated_inputs=lambda:self.value),
                    'already-authenticated')
        self.assertEqual(self.executions,[])
        self.reject(lambda:self.s.bind_worker_sources(self.ad,authenticated_inputs=self.ad.inputs),'previous private')
        self.reject(lambda:self.s.bind_worker_sources(self.ad),exception=TypeError)

    def test_input_hash_failure_and_legacy_schema_precede_any_execution(self):
        self.raw+=b' '
        self.reject(self.prepare,'input lock changed');self.assertEqual(self.executions,[])
        # Exercise actual admission schema independently; no failed handle reuse.
        self.value.pop('production_display_sources');self.reseal_fixture()
        self.reject(self.ad.inputs,'input lock schema')

    def test_decoder_failure_is_not_replaced_or_reauthenticated(self):
        self.raw=b'{"format":"x","files":{},"files":{}}';self.ad.INPUTS_SHA=sha(self.raw)
        self.reject(self.prepare,'duplicate');self.assertEqual(self.executions,[])

    def test_each_missing_private_input_fails_whole_preflight(self):
        for _,key in self.s.WORKER_PATHS:
            case=Loader();case.setUp()
            try:
                case.value['files'].pop(key);case.reseal_fixture()
                with self.subTest(key=key):case.reject(case.prepare,'private source row missing')
                self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_missing_transitive_disk_source_precedes_worker_execution(self):
        (self.root/PREFIX/'release-acceptance.py').unlink()
        self.reject(self.prepare,exception=FileNotFoundError);self.assertEqual(self.executions,[])

    def test_each_changed_source_is_rejected_before_any_module(self):
        for _,key in self.s.WORKER_PATHS:
            case=Loader();case.setUp()
            try:
                path=case.root/key;path.write_bytes(b'!'+path.read_bytes()[1:])
                with self.subTest(key=key):case.reject(case.prepare,'digest')
                self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_exact_fixed_scope_and_no_optional_transitive_fallback(self):
        key=PREFIX+'foreign.py';p=self.root/key;p.write_bytes(b'raise AssertionError("never")\n')
        self.value['files'][key]=dict(size=p.stat().st_size,uid=1000,mode=0o644,sha256=sha(p.read_bytes()))
        self.reseal_fixture();self.prepare()
        self.reject(lambda:self.load(key),'unqualified private source')
        self.assertEqual(self.executions,[])

    def test_worker_literal_projection_and_project_import_refuse_preexec(self):
        self.modify_source(WORKER,b'\nSOURCE_PATHS = SOURCE_PATHS + (("extra", "extra.py"),)\n')
        self.reject(self.prepare,'unique source constant');self.assertEqual(self.executions,[])

    def test_unknown_import_and_syntax_error_refuse_before_any_module(self):
        for suffix in (b'\nimport foreign_project_dependency\n',b'\nTHIS IS NOT VALID PYTHON !!!\n'):
            case=Loader();case.setUp()
            try:
                case.modify_source(PREFIX+'release-acceptance.py',suffix)
                case.reject(case.prepare);self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_dynamic_import_has_no_fallback_and_partial_import_poisoned(self):
        key=PREFIX+'release-acceptance.py'
        self.modify_source(key,b'\n__import__("foreign_project_dependency")\n')
        self.prepare();self.load()
        self.reject(lambda:self.load(key),'outside checked worker stdlib')
        self.assertNotIn(key,self.handle._modules)
        self.reject(self.load,'handle failed')

    def test_metadata_symlink_hardlink_fifo_and_alias_refuse(self):
        key=PREFIX+'rescue-capture-network.py'
        for mode in ('mode','symlink','hardlink','fifo'):
            case=Loader();case.setUp()
            try:
                p=case.root/key
                if mode=='mode':p.chmod(0o666)
                elif mode=='symlink':p.rename(p.with_suffix('.real'));p.symlink_to(p.with_suffix('.real'))
                elif mode=='hardlink':os.link(p,p.with_suffix('.link'))
                else:p.unlink();os.mkfifo(p,0o644)
                with self.subTest(mode=mode):case.reject(case.prepare)
                self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_bad_metadata_rows_are_not_accepted_as_typed_inputs(self):
        for field,value in (('size',True),('uid',True),('mode',True),('size',131073),('mode',0o666),('sha256','bad')):
            case=Loader();case.setUp()
            try:
                case.value['files'][WORKER][field]=value;case.reseal_fixture()
                with self.subTest(field=field,value=value):case.reject(case.prepare)
                self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_same_bytes_replacement_and_reversion_poison_handle(self):
        self.prepare();self.load()
        path=self.root/PREFIX/'check-deployed-server.py';other=path.with_suffix('.new')
        other.write_bytes(path.read_bytes());other.chmod(0o644);os.replace(other,path)
        self.reject(self.load,'retained private source replaced')
        self.reject(self.load,'handle failed')
        self.reject(self.prepare,'handle failed')

    def test_source_replaced_across_authentication_is_detected(self):
        fired=False
        def replace():
            nonlocal fired
            self.auth_calls.append('relay-fixture')
            if not fired:
                fired=True;path=self.root/WORKER;other=path.with_suffix('.new')
                other.write_bytes(path.read_bytes());other.chmod(0o644);os.replace(other,path)
        self.ad.D.BOOT.expected_kernel_relay=replace
        self.reject(self.prepare,'during private preflight');self.assertEqual(self.executions,[])

    def test_late_source_mutation_at_last_authority_check_is_detected(self):
        self.prepare();calls=[]
        original=self.ad.R.receipt
        def read(path,limit):
            if path==self.ad.INPUTS:
                calls.append(1)
                # check: first input read, cohort twice, final input read.
                if len(calls)==4:
                    p=self.root/WORKER;p.write_bytes(b'!'+p.read_bytes()[1:])
            return original(path,limit)
        self.ad.R.receipt=read
        self.reject(self.load);self.assertEqual(self.executions,[])

    def test_changed_lock_implementation_anchor_owner_and_process_refuse(self):
        variants=('bytes','pin','reader','digest','owner','source_boot','process','handle_provider','retained_rows')
        for mode in variants:
            case=Loader();case.setUp()
            try:
                case.prepare()
                if mode=='bytes':case.raw+=b' '
                elif mode=='pin':case.ad.INPUTS_SHA='f'*64
                elif mode=='reader':case.ad.inputs=lambda:case.value
                elif mode=='digest':case.ad.digest_file=lambda *a:None
                elif mode=='owner':case.ad.A.OWNER='b'*32
                elif mode=='source_boot':case.ad.A.SOURCE_BOOT='changed'
                elif mode=='handle_provider':
                    other=types.ModuleType('copied_provider');other.__dict__.update(case.ad.__dict__)
                    case.handle.ad=other
                elif mode=='retained_rows':
                    rows={k:dict(v) for k,v in case.handle._rows.items()};rows[WORKER]['sha256']='f'*64
                    case.handle._rows=rows
                else:case.handle._process=(-1,1000,1000)
                with self.subTest(mode=mode):case.reject(case.load)
                self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_name_alias_returns_one_canonical_module_and_no_pyc(self):
        key=WORKER;path=self.root/key
        code=compile('raise AssertionError("valid stale pyc must not execute")',str(path),'exec')
        cache=Path(importlib.util.cache_from_source(str(path)));cache.parent.mkdir()
        cache.write_bytes(importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(path.stat().st_mtime),path.stat().st_size)+marshal.dumps(code))
        self.prepare();first=self.load(name='alias_one');second=self.load(name='alias_two')
        self.assertIs(first,second);self.assertEqual(first.__name__,'rog5_private_worker')
        self.assertEqual(self.executions.count(str(path)),1)
        self.assertNotIn('alias_one',sys.modules);self.assertTrue(cache.exists())
        self.assertIs(first.__source__,self.handle._sources[key])

    def test_path_alias_wrong_pin_and_main_name_refuse(self):
        for mode in ('alias','pin','main','outside'):
            case=Loader();case.setUp()
            try:
                h=case.prepare();path=case.root/WORKER;pin=case.value['files'][WORKER]['sha256'];name='worker_alias'
                if mode=='alias':path=path.parent/'..'/path.parent.name/path.name
                elif mode=='pin':pin='f'*64
                elif mode=='main':name='__main__'
                else:path=case.root.parent/'outside.py'
                with self.subTest(mode=mode):case.reject(lambda:h(name,path,pin))
                self.assertEqual(case.executions,[])
            finally:case.doCleanups()

    def test_cached_module_path_source_function_and_cache_replacement_refuse(self):
        for mode in ('path','source','function','cache'):
            case=Loader();case.setUp()
            try:
                case.prepare();module=case.load()
                if mode=='path':module.__file__=str(case.root/'foreign.py')
                elif mode=='source':module.__source__=module.__source__+b'\n'
                elif mode=='function':module.execute=lambda *args:None
                else:case.handle._modules[WORKER]=types.ModuleType('foreign')
                with self.subTest(mode=mode):case.reject(case.load,'private module')
            finally:case.doCleanups()

    def test_concurrent_alias_loads_share_one_module(self):
        self.prepare()
        with ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(lambda name:self.load(name=name),('thread_one','thread_two')))
        self.assertIs(values[0],values[1]);self.assertEqual(self.executions.count(str(self.root/WORKER)),1)

    def test_partial_source_execution_failure_is_sticky_and_not_cached(self):
        self.prepare();key=PREFIX+'release-acceptance.py';original=self.s.exec
        failure=KeyboardInterrupt('inert failure after source definition execution')
        def interrupted(code,ns,*args):
            original(code,ns,*args)
            if ns['__file__']==str(self.root/key):raise failure
        with patch.object(self.s,'exec',interrupted):
            self.assertIs(self.reject(lambda:self.load(key),exception=KeyboardInterrupt),failure)
        self.assertNotIn(key,self.handle._modules);self.reject(self.load,'handle failed')
        self.reject(lambda:self.s.initialize_worker(self.ad),'handle failed')

    def test_failure_after_acceptance_bind_detaches_only_our_worker(self):
        self.prepare();key=PREFIX+'headless-stage-receiver.py'
        # A trace failure in the ACTUAL bind_transport after acceptance binding;
        # do not replace the loader or any production binding function.
        tree=ast.parse(self.contents['headless-stage-receiver.py.txt'])
        line=next(n.body[0].lineno for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bind_transport')
        failure=SystemExit('inert partial binding interruption');previous=sys.gettrace()
        def trace(frame,event,arg):
            if frame.f_code.co_filename==str(self.root/key) and frame.f_code.co_name=='bind_transport' and event=='line':
                raise failure
            return trace
        sys.settrace(trace)
        try:self.assertIs(self.reject(lambda:self.s.initialize_worker(self.ad),exception=SystemExit),failure)
        finally:sys.settrace(previous)
        acceptance=self.handle._modules[PREFIX+'release-acceptance.py']
        self.assertIsNotNone(acceptance._SOURCE_READER)
        self.assertIsNone(self.s.T.W);self.assertIsNone(self.s.K.W)
        self.reject(lambda:self.s.initialize_worker(self.ad),'handle failed')
        self.reject(lambda:acceptance._SOURCE_READER[1](),'shared worker changed')

    def test_mixed_worker_before_attach_is_not_overwritten(self):
        self.prepare();self.s.bind_sources(self.ad);foreign=object();self.s.K.W=foreign
        self.reject(lambda:self.s.initialize_worker(self.ad),'already bound')
        self.assertIs(self.s.K.W,foreign);self.assertIsNone(self.s.T.W)
        self.assertEqual(self.handle._modules,{})

    def test_shared_worker_and_deployed_alias_mutation_refuse_reuse(self):
        self.prepare();d=self.s.initialize_worker(self.ad);w=self.s.T.W
        self.s.K.W=object()
        self.reject(w.load_deployed,'shared worker changed')
        self.reject(lambda:self.s.initialize_worker(self.ad),'shared private worker changed')
        self.reject(lambda:self.s.initialize_worker(self.ad),'handle failed')

    def test_provider_revocation_on_reuse_refuses_before_returning_cached_module(self):
        self.prepare();self.load()
        def deny():raise ValueError('inert external authentication revoked')
        self.ad.D.pins=deny
        self.reject(self.load,'authentication revoked')
        self.ad.D.pins=noop
        self.reject(self.load,'handle failed')

    def test_mutation_during_source_execution_is_not_published_or_retried(self):
        self.prepare();original=self.s.exec
        def mutate(code,ns,*args):
            original(code,ns,*args)
            if ns['__file__']==str(self.root/WORKER):
                path=self.root/PREFIX/'rescue-capture-network.py';other=path.with_suffix('.new')
                other.write_bytes(path.read_bytes());other.chmod(0o644);os.replace(other,path)
        with patch.object(self.s,'exec',mutate):self.reject(self.load,'retained private source replaced')
        self.assertEqual(self.handle._modules,{})
        self.reject(self.load,'handle failed')

    def test_authenticated_private_rows_do_not_repin_public_sources(self):
        self.modify_source('gpu-iommu-display-r1/transport.py',b'\n# inert unreviewed public change\n')
        self.reject(self.prepare,'reviewed source pin')
        self.assertEqual(self.executions,[])

    def test_binding_cannot_move_to_another_provider_or_reader(self):
        self.prepare()
        self.reject(lambda:self.s.bind_worker_sources(self.ad,authenticated_inputs=lambda:self.value),
                    'authority cannot be replaced')
        foreign=types.ModuleType('foreign_admission');foreign.__dict__.update(self.ad.__dict__)
        self.reject(lambda:self.s.initialize_worker(foreign),'admission differs')
        self.assertEqual(self.executions,[])
        self.assertIs(self.prepare(),self.handle)

    def test_authority_cannot_reenter_the_loader_it_authenticates(self):
        self.prepare()
        self.ad.D.pins=lambda:self.handle.check()
        self.reject(self.load,'authority/preflight recursion')
        self.assertEqual(self.executions,[])
        self.ad.D.pins=noop
        self.reject(self.load,'handle failed')

    def test_public_reader_and_historical_binders_remain_unchanged(self):
        before=ast.parse(self.contents['production-cohort/session.py']);after=ast.parse(self.public['gpu-iommu-session-r1/session.py'])
        def function(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        for name in ('source_lock','source_stamp','source_read','source_graph','cohort','load','bind_sources','run','admission','recovery'):
            self.assertEqual(ast.dump(function(before,name)),ast.dump(function(after,name)),name)
        self.assertEqual(self.s.PINS,self.pins);self.assertEqual(set(self.s.PATHS),set(self.public))
        self.prepare();self.s.initialize_worker(self.ad)
        self.reject(lambda:self.s.load('legacy',self.root/WORKER,self.value['files'][WORKER]['sha256']),
                    'unresolved source dependency')
        # No changed pin is accepted on behalf of the legacy caller.
        self.reject(lambda:self.s.T.bind_worker(self.handle),'unqualified private source')
        self.assertEqual(sha(self.inputs[WORKER]),'faedbbc0c1010bc88f5837c31c8b2714b76c8305abf826cb67ee43958c55b851')


if __name__=='__main__':
    names=ARGS.case or unittest.defaultTestLoader.getTestCaseNames(Loader)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Loader(name) for name in names))
    raise SystemExit(not result.wasSuccessful())
