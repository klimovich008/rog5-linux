#!/usr/bin/env python3
"""Actual enclosing cohort and successor imports; private admission is a fixture.

No phone, SSH, root operation, module/helper execution, signing or real admission.
The input-lock producer is a synthetic authority boundary, not proof of the
missing private decoder or live command policy. No cohort/load/bind function is
substituted. Real temporary files exercise their production metadata/hash code.

All source patches apply strictly; no packet-recount compatibility mode.
"""
import ast
import copy
import hashlib
import importlib.util
import marshal
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('display-component.py','display-endpoint.py','display-firmware.py',
         'display-providers.py','load-production-display.py')
BOOT = '11111111-2222-3333-4444-555555555555'
OWNER = 'a'*32

HISTORICAL = {
    'backend-before.py':'840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d',
    'transport-before.py':'3d6f76bb421bf8f40967ac354d49e152248636b2272a1cf2653f8702e2a1a573',
    'session-before.py':'2a2316564977a2839a31f11fb0435859857b6567f38fc5f0752ca27b5f63fa8c',
    'kernel-log-before.py':'b690ae15bfced9c5cc3c9ab905209dc12dccb909678c31975fe6a32282a18d14',
    # This is the explicitly normalized fixture, not the private historical seal.
    'health-before.py':'5d8aa3e5e61ebcffdabd3f5b32d90c3c5c5b378866de1df69bff92d7ce5f5940',
}


def digest(data):return hashlib.sha256(data).hexdigest()


def module(path, name):
    # Execute source bytes, never a path loader or pyc. Successor module bodies
    # are inert; retained historical session/health/transport are NOT imported.
    result = types.ModuleType(name); result.__file__ = str(path)
    result.__source__ = path.read_bytes()
    exec(compile(result.__source__,str(path),'exec'),result.__dict__)
    return result


def literals(path, names):
    tree=ast.parse(path.read_bytes()); result={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in names:
                    if target.id in result:raise ValueError('duplicate fixture constant')
                    result[target.id]=ast.literal_eval(node.value)
    if set(result)!=set(names):raise ValueError('missing fixture constant')
    return result


def assemble(destination):
    for name, old, patches in (
        ('backend.py','backend-before.py',('0002-production-supervisor.patch','0007-production-context.patch')),
        ('transport.py','transport-before.py',('0003-production-transport.patch','0008-production-staging.patch')),
        ('session.py','session-before.py',('0004-production-session.patch',)),
        ('kernel-log.py','kernel-log-before.py',('0005-production-kernel-log.patch',)),
        ('health.py','health-before.py',('0006-production-health.patch',)),
    ):
        raw=(ROOT/'scripts/device/fixtures/display-loader'/old).read_bytes()
        if digest(raw)!=HISTORICAL[old]:raise ValueError('retained historical fixture changed: '+old)
        (destination/name).write_bytes(raw)
        for name in patches:
            subprocess.run(['git','apply',str(ROOT/'patches/display-controller'/name)],
                           cwd=destination,check=True,capture_output=True,timeout=10)
    for name in NAMES:shutil.copyfile(ROOT/'scripts/device'/name,destination/name)
    # Preserve the actual preceding cohort for the negative control, without
    # importing its historical dependency-loading statements.
    previous={p.name:p.read_bytes() for p in destination.glob('*.py')}
    subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0009-production-session-source-binding.patch')],
                   cwd=destination,check=True,capture_output=True,timeout=10)
    return previous


class Cohort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getuid()!=1000 or os.geteuid()!=1000:
            raise ValueError('run this source-metadata test as the ordinary UID1000 host user, not root')
        cls.temp=tempfile.TemporaryDirectory(prefix='production-cohort-',dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temp.cleanup);cls.base=Path(cls.temp.name)
        cls.assembled=cls.base/'assembled';cls.assembled.mkdir()
        cls.previous_sources=assemble(cls.assembled);cls.previous=cls.previous_sources['session.py']
        cls.payload=module(ROOT/'scripts/device/stage-production-display-payload.py','actual_payload')

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=self.base))
        for name in ('gpu-iommu-session-r1','gpu-iommu-display-r1','gpu-iommu-health-r1'):
            (self.root/name).mkdir(mode=0o700)
        for file in self.assembled.glob('*.py'):
            if file.name in ('session.py','kernel-log.py'):key='gpu-iommu-session-r1/'+file.name
            elif file.name=='health.py':key='gpu-iommu-health-r1/successor-health.py'
            else:key='gpu-iommu-display-r1/'+file.name
            target=self.root/key;target.write_bytes(file.read_bytes());target.chmod(0o644)
        self.s=module(self.root/'gpu-iommu-session-r1/session.py','actual_source_session')
        self.value={'files':{},'production_display_sources':list(self.s.PATHS)}
        for name in self.s.PATHS:
            p=self.root/name;st=p.stat()
            self.value['files'][name]=dict(size=st.st_size,uid=st.st_uid,mode=stat.S_IMODE(st.st_mode),sha256=digest(p.read_bytes()))
        self.checked=[]
        # Only the missing private admission provider/decoder is a fixture.
        # It deliberately does not hide failures by checking bytes for cohort().
        self.ad=types.SimpleNamespace(__file__=str(self.root/'gpu-iommu-live-driver-r1/live-admission.py'),
            inputs=lambda:copy.deepcopy(self.value),digest_file=lambda *args:self.checked.append(args))
        self.identity=dict(boot_id=BOOT,owner=OWNER,release='7.1.4-rog5-production',bundle='fixture-production',
            descriptor_sha256=digest(b'inert fixture descriptor\n'),
            board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57')

    def reject(self, call=None):
        before=set(os.listdir('/proc/self/fd'))
        with self.assertRaises((ValueError,OSError)):(call or (lambda:self.s.cohort(self.ad)))()
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))
        self.assertFalse(self.s.OUTPUT.exists())

    def test_actual_preceding_cohort_reproduces_query_failure(self):
        tree=ast.parse(self.previous)
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cohort']
        self.s.bind_sources(self.ad)
        ns=dict(self.s.__dict__)
        ns['PINS']=self.s.source_literal(self.previous,'PINS')
        # Use the actual bound new transport/backend, with no QUERY/QUERY_SHA.
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-previous-cohort>','exec'),ns)
        with self.assertRaisesRegex(AttributeError,'QUERY'):ns['cohort'](self.ad)

    def test_import_of_full_successors_does_not_open_private_sources(self):
        self.assertIsNone(self.s.T);self.assertIsNone(self.s.H);self.assertIsNone(self.s.C)
        for path in ('gpu-iommu-display-r1/transport.py','gpu-iommu-health-r1/successor-health.py','gpu-iommu-session-r1/kernel-log.py'):
            m=module(self.root/path,'inert_successor')
            self.assertEqual(m.__source__,(self.root/path).read_bytes())
        self.assertEqual(self.checked,[])
        self.assertFalse((self.root/'oled-startup-live-driver-r1').exists())

    def test_cohort_is_exact_and_import_free(self):
        result=self.s.cohort(self.ad)
        self.assertEqual(result,{n:self.value['files'][n]['sha256'] for n in self.s.PATHS})
        self.assertEqual(len(result),10);self.assertIsNone(self.s.T);self.assertEqual(self.s._SOURCE_MODULES,{})
        self.assertEqual([str(a[0].relative_to(self.root)) for a in self.checked],list(self.s.PATHS))

    def test_actual_successor_source_binding_has_all_six_and_no_query(self):
        c=self.s.bind_sources(self.ad);t=self.s.T
        self.assertFalse(hasattr(t,'QUERY'));self.assertFalse(hasattr(t.B,'QUERY_SHA'));self.assertFalse(hasattr(self.s,'P'))
        self.assertEqual(set(t.SOURCE_PINS),{'backend.py',*NAMES})
        self.assertEqual(t.SOURCE_PINS,{n:digest((self.root/'gpu-iommu-display-r1'/n).read_bytes()) for n in t.SOURCE_PINS})
        self.assertEqual(c.SOURCE_PINS,{k:v for k,v in t.B.PINS.items() if k!='display-component.py'})
        self.assertIsNone(t.W);self.assertIsNone(self.s.H.A)
        self.assertEqual(c.__source__,(self.root/'gpu-iommu-display-r1/display-component.py').read_bytes())

    def test_load_is_forbidden_before_cohort(self):
        name='gpu-iommu-display-r1/transport.py'
        self.reject(lambda:self.s.load('premature',self.root/name,self.s.PINS[name]))
        self.assertEqual(self.s._SOURCE_MODULES,{})

    def test_missing_each_lock_row_refuses_before_loading(self):
        for name in self.s.PATHS:
            row=self.value['files'].pop(name)
            with self.subTest(name=name):self.reject()
            self.value['files'][name]=row
        self.assertEqual(self.s._SOURCE_MODULES,{})

    def test_missing_each_actual_source_refuses(self):
        for name in self.s.PATHS:
            p=self.root/name;raw=p.read_bytes();p.unlink()
            with self.subTest(name=name):self.reject()
            p.write_bytes(raw);p.chmod(0o644)

    def test_changed_each_actual_source_refuses(self):
        for name in self.s.PATHS:
            p=self.root/name;raw=p.read_bytes();p.write_bytes(b'!'+raw[1:])
            with self.subTest(name=name):self.reject()
            p.write_bytes(raw)

    def test_external_lock_cannot_repin_foreign_nonself_source(self):
        name='gpu-iommu-display-r1/display-firmware.py';p=self.root/name
        p.write_bytes(b'raise RuntimeError("must not execute")\n')
        self.value['files'][name].update(size=p.stat().st_size,sha256=digest(p.read_bytes()))
        self.reject(lambda:self.s.bind_sources(self.ad));self.assertEqual(self.s._SOURCE_MODULES,{})

    def test_unscoped_historical_input_lock_refuses(self):
        del self.value['production_display_sources'];self.reject()

    def test_duplicate_and_unknown_scoped_paths_refuse(self):
        original=list(self.value['production_display_sources'])
        for bad in (original+[original[0]],original[:-1]+[original[0]],original+['gpu-iommu-display-r1/extra.py'],
                    original[:-1]+['gpu-iommu-display-r1/../gpu-iommu-display-r1/backend.py']):
            self.value['production_display_sources']=bad
            with self.subTest(bad=bad[-1]):self.reject()

    def test_historical_provider_query_and_initializer_closure_refuses(self):
        original=list(self.s.PATHS)
        for name in ('gpu-iommu-provider-r1/transport.py','gpu-query-arm64-r1/a/rog5-gpu-query.deploy',
                     'gpu-iommu-display-r1/initialize.py','gpu-iommu-display-r1/provider-proof.py'):
            self.value['production_display_sources']=original[:-1]+[name]
            with self.subTest(name=name):self.reject()

    def test_other_boot_inputs_are_not_mistaken_for_display_source_inputs(self):
        self.value['files']['boot-only/retained-receipt.json']={'opaque':'private boundary'}
        self.s.cohort(self.ad)
        self.assertEqual(len(self.checked),10)
        self.assertFalse(any('boot-only' in str(row[0]) for row in self.checked))

    def test_unknown_disk_file_cannot_be_loaded_and_is_not_deleted(self):
        path=self.root/'gpu-iommu-display-r1/foreign.py';path.write_text('raise RuntimeError("NEVER")\n')
        self.s.cohort(self.ad)
        self.reject(lambda:self.s.load('foreign',path,digest(path.read_bytes())))
        self.assertTrue(path.is_file())

    def test_source_scope_order_is_not_activation_order(self):
        self.s.cohort(self.ad);self.value['production_display_sources'].reverse()
        self.s.cohort(self.ad)
        contract=self.s.host_contract(self.ad,self.identity)
        self.assertEqual([r['filename'] for r in contract.entry_intent(BOOT,OWNER)['modules']],list(self.s.bind_sources(self.ad).ORDER))

    def test_changed_lock_after_first_validation_is_not_recaptured(self):
        self.s.cohort(self.ad)
        self.value['files'][self.s.SESSION_PATH]['mode']=0o600
        (self.root/self.s.SESSION_PATH).chmod(0o600)
        self.reject();self.assertEqual(self.s._SOURCE_MODULES,{})

    def test_same_byte_replacement_after_first_validation_refuses(self):
        self.s.cohort(self.ad)
        path=self.root/'gpu-iommu-display-r1/display-endpoint.py'
        other=path.with_suffix('.replacement');other.write_bytes(path.read_bytes());other.chmod(0o644);os.replace(other,path)
        self.reject(lambda:self.s.bind_sources(self.ad))

    def test_cached_module_still_revalidates_the_whole_cohort(self):
        self.s.bind_sources(self.ad)
        key='gpu-iommu-display-r1/transport.py'
        self.assertIs(self.s._SOURCE_MODULES[key],self.s.T)
        changed=self.root/'gpu-iommu-display-r1/display-firmware.py'
        changed.write_bytes(b'!'+changed.read_bytes()[1:])
        self.reject(lambda:self.s.load('cached_transport',self.root/key,self.s.PINS[key]))

    def test_replacement_between_external_check_and_source_read_refuses(self):
        name=self.s.PATHS[0];path=self.root/name
        def check(p,*args):
            if p==path:
                new=path.with_suffix('.replacement');new.write_bytes(path.read_bytes());new.chmod(0o644);os.replace(new,path)
        self.ad.digest_file=check
        self.reject();self.assertIsNone(self.s._SOURCE_BINDING)

    def test_late_replacement_of_earlier_source_refuses_before_any_import(self):
        original=self.s.source_read;first=self.root/self.s.PATHS[0]
        def read(name,row):
            result=original(name,row)
            if name==self.s.PATHS[-1]:
                new=first.with_suffix('.replacement');new.write_bytes(first.read_bytes());new.chmod(0o644);os.replace(new,first)
            return result
        with patch.object(self.s,'source_read',side_effect=read):self.reject(lambda:self.s.bind_sources(self.ad))
        self.assertIsNone(self.s._SOURCE_BINDING);self.assertEqual(self.s._SOURCE_MODULES,{})

    def test_external_lock_mutation_during_validation_refuses(self):
        original=self.s.source_read
        def read(name,row):
            result=original(name,row)
            if name==self.s.PATHS[-1]:self.value['production_display_sources'].pop()
            return result
        with patch.object(self.s,'source_read',side_effect=read):self.reject()

    def test_symlink_hardlink_nonregular_and_mode_refuse(self):
        path=self.root/'gpu-iommu-display-r1/display-firmware.py';raw=path.read_bytes()
        link=path.with_suffix('.link');os.link(path,link);self.reject();link.unlink()
        path.chmod(0o666);self.reject();path.chmod(0o644)
        other=path.with_suffix('.real');path.rename(other);path.symlink_to(other);self.reject();path.unlink();other.rename(path)
        path.unlink();os.mkfifo(path,0o644);self.reject();path.unlink();path.write_bytes(raw);path.chmod(0o644)
        self.s.cohort(self.ad)

    def test_bool_numeric_fields_and_excessive_sizes_refuse(self):
        row=self.value['files'][self.s.PATHS[0]];original=copy.deepcopy(row)
        for field,value in (('size',True),('uid',True),('mode',True),('size',131073),('uid',0),('sha256','not a pin')):
            row[field]=value
            with self.subTest(field=field,value=value):self.reject()
            row.clear();row.update(original)

    def test_valid_stale_pyc_is_never_executed(self):
        source=self.root/'gpu-iommu-display-r1/transport.py'
        cached=Path(importlib.util.cache_from_source(str(source)))
        cached.parent.mkdir()
        info=source.stat()
        # Valid timestamp/size cache metadata makes the former path loader
        # execute these different bytes despite the source hash still matching.
        sentinel=compile('raise RuntimeError("stale-bytecode sentinel")',str(source),'exec')
        cached.write_bytes(importlib.util.MAGIC_NUMBER+struct.pack('<III',0,
            int(info.st_mtime)&0xffffffff,info.st_size&0xffffffff)+marshal.dumps(sentinel))
        spec=importlib.util.spec_from_file_location('old_path_loader',source)
        with self.assertRaisesRegex(RuntimeError,'stale-bytecode sentinel'):
            spec.loader.exec_module(importlib.util.module_from_spec(spec))
        self.s.bind_sources(self.ad)
        self.assertEqual(self.s.T.__source__,source.read_bytes())
        self.assertTrue(cached.exists())

    def test_private_binding_refuses_before_session_output_or_entry(self):
        consumed=self.root/'retained-consumed.json';consumed.write_bytes(b'consumed; preserve\n')
        contract=self.s.host_contract(self.ad,self.identity)
        with self.assertRaisesRegex(ValueError,'unresolved source dependency: oled-startup-live-driver-r1/ssh-worker.py'):
            self.s.run(self.ad,None,None,None,contract)
        self.assertFalse(self.s.OUTPUT.exists());self.assertEqual(consumed.read_bytes(),b'consumed; preserve\n')
        self.assertIsNone(self.s.T.W);self.assertIsNone(self.s.H.A)

    def test_actual_identity_six_and_source_only_stage_plan(self):
        contract=self.s.host_contract(self.ad,self.identity)
        self.assertEqual(contract.expected(BOOT,OWNER),self.identity)
        owner=types.SimpleNamespace(admission=dict(boot_id=BOOT,owner=OWNER),receipt_sha='2'*64)
        plan=self.s.T.stage_plan(owner,contract)
        self.assertEqual(plan['artifact_identity'],self.identity)
        data=literals_from_text(plan['script'],'DATA')
        self.assertEqual(set(data['files']),{'backend.py',*NAMES})
        self.assertNotIn('query',data);self.assertFalse(self.s.OUTPUT.exists())

    def test_graph_rejects_parent_child_pin_disagreement(self):
        self.s.cohort(self.ad);sources=dict(self.s._SOURCE_BINDING['sources'])
        key='gpu-iommu-display-r1/backend.py'
        sources[key]=sources[key].replace(b"'display-firmware.py': 'd3bfd",b"'display-firmware.py': 'a3bfd",1)
        with self.assertRaisesRegex(ValueError,'backend source closure'):self.s.source_graph(sources)

    def test_duplicate_literal_keys_refuse(self):
        with self.assertRaisesRegex(ValueError,'duplicate source constant key'):
            self.s.source_literal("PINS={'same':'a','same':'b'}",'PINS')

    def test_real_payload_plan_keeps_archive_and_activation_orders_independent(self):
        # Explicit synthetic archive metadata. It uses the actual fourteen module
        # identities, not the real qualified archive, which this test never opens.
        p=self.payload;constants,_=p.source_contracts()
        rows=[dict(name=n,path=path,bytes=size,sha256=pin,dependencies=[],vermagic=constants['RELEASE']+' SMP preempt mod_unload aarch64')
              for n,path,size,pin in constants['MODULES']]
        rows=sorted(rows,key=lambda r:r['path'])
        for index,row in enumerate(rows):row['dependencies']=[] if index==0 else [rows[index-1]['path']]
        expected=dict(bytes=10240,sha256='a'*64,manifest=dict(format='rog5-production-display-modules-v1',
            release=constants['RELEASE'],authority='none',physical='NOT RUN',roots=sorted(p.S.ROOTS),modules=rows))
        self.assertNotEqual([r['name'] for r in rows],[r[0] for r in constants['MODULES']])
        p.plan(expected,constants)
        contract=self.s.host_contract(self.ad,self.identity)
        self.assertEqual([r['module'] for r in contract.entry_intent(BOOT,OWNER)['modules']],
                         [row[0] for row in constants['MODULES']])
        bad=copy.deepcopy(expected);bad['manifest']['modules'].reverse()
        with self.assertRaisesRegex(ValueError,'dependency absent or after consumer'):p.plan(bad,constants)
        bad=copy.deepcopy(expected);bad['manifest']['modules'][-1]=copy.deepcopy(bad['manifest']['modules'][0])
        with self.assertRaises(ValueError):p.plan(bad,constants)

    def test_actual_session_admission_calls_actual_cohort_before_authority(self):
        contract=self.s.host_contract(self.ad,self.identity)
        output=self.root/'gpu-iommu-controller-r1/execution';output.mkdir(parents=True)
        records=dict(close_capture=dict(status='PASS',capture_status='PASS',full_lifetime=True,cleanup_complete=True),
                     post_capture_health=dict(status='PASS',identity=copy.deepcopy(self.identity),
                                              current_boot_healthy=True,physical_guards_passed=True))
        controller=types.SimpleNamespace(output=output,context=dict(owner=OWNER),entered=list(records),
                                        results=records,target_identity=copy.deepcopy(self.identity))
        boot=dict(status='COMPONENT_PASS',successor_running=True,errors=[],entered=list(records),
                  phases=list(records),target_identity=copy.deepcopy(self.identity))
        (output/'result.json').write_text(json.dumps(boot))
        calls=[];self.ad.OUTPUT=output
        self.ad.common=lambda _: (calls.append('common') or dict(expires_monotonic=self.s.time.monotonic()+4000))
        self.ad.receipt=lambda p,_:json.loads(p.read_bytes())
        self.ad.A=types.SimpleNamespace(exact_json=lambda a,b:json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True))
        credentials=types.SimpleNamespace(check=lambda:calls.append('credentials'))
        self.assertEqual(self.s.admission(self.ad,controller,credentials,boot,contract)[1],self.identity)
        self.assertEqual(calls,['common','credentials']);calls.clear()
        path=self.root/'gpu-iommu-display-r1/display-providers.py';path.write_bytes(b'!'+path.read_bytes()[1:])
        self.reject(lambda:self.s.admission(self.ad,controller,credentials,boot,contract))
        self.assertEqual(calls,[])

    def test_current_logger_and_health_semantics_stay_unchanged(self):
        for filename,names in (
            ('health.py',('inputs','physical_guard','configuration','script','validate','rollback_units','latch')),
            ('kernel-log.py',('KernelLog','REMOTE')),
            ('transport.py',('exchange','terminal','stage','stage_plan','ssh_argv','STAGE','SOURCE','SOURCE_PINS')),
        ):
            old=ast.parse(self.previous_sources[filename]);new=ast.parse((self.assembled/filename).read_bytes())
            def node(tree,name):
                return next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name
                            or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
            for name in names:
                with self.subTest(file=filename,name=name):self.assertEqual(ast.dump(node(old,name)),ast.dump(node(new,name)))

    def test_worker_or_health_files_cannot_gain_scope_by_lock_edit(self):
        name='oled-startup-live-driver-r1/ssh-worker.py'
        path=self.root/name;path.parent.mkdir();path.write_text('raise RuntimeError("must not execute")\n')
        self.value['production_display_sources'].append(name)
        self.value['files'][name]=dict(size=path.stat().st_size,uid=1000,mode=0o644,sha256=digest(path.read_bytes()))
        self.reject(lambda:self.s.initialize(self.ad));self.assertEqual(self.s._SOURCE_MODULES,{})

    def test_supervision_and_existing_authority_functions_are_not_redesigned(self):
        # The retained fixture/0002+0007 backend is byte-for-byte unchanged.
        backend=self.assembled/'backend.py'
        self.assertEqual(digest(backend.read_bytes()),'e8354b4591d5110224ed5bd4579a82995071d7c98c846567dd387396e2a1a098')
        old=ast.parse(self.previous);new=ast.parse(self.s.__source__)
        for name in ('Owner','admission','recovery','collect_health','display_result','contract_target'):
            def node(tree):return next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
            self.assertEqual(ast.dump(node(old)),ast.dump(node(new)),name)


def literals_from_text(text,name):
    tree=ast.parse(text)
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))


if __name__=='__main__':unittest.main(verbosity=2)
