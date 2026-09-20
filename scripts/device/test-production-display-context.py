#!/usr/bin/env python3
"""Actual production staging context on temporary files; no target execution.

Only root ownership, fixed RAM paths and mountinfo are fixtures. Manifest/source
bytes, modes, hashes, dependency execution and identity logic are actual code.
No module insertion, backlight command, SSH or admission is invoked.
"""
import ast
import base64
import contextlib
import copy
import builtins
import json
import hashlib
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
BOOT='11111111-2222-3333-4444-555555555555';OWNER='a'*32
SOURCES=('display-component.py','display-endpoint.py','display-firmware.py','display-providers.py','load-production-display.py')


def load(path,name):
    m=types.ModuleType(name);m.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m


class Context(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='production-context-',dir=os.environ.get('TMPDIR',str(Path.home()/'.local/state')))
        cls.addClassCleanup(cls.temp.cleanup);cls.base=Path(cls.temp.name)
        cls.source=cls.base/'backend.py'
        old=ROOT/'scripts/device/fixtures/display-loader/backend-before.py'
        raw=old.read_bytes()
        if hashlib.sha256(raw).hexdigest()!='840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d':raise ValueError('historical backend changed')
        cls.source.write_bytes(raw)
        subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0002-production-supervisor.patch')],cwd=cls.base,check=True,capture_output=True)
        if not BEFORE:subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0007-production-context.patch')],cwd=cls.base,check=True,capture_output=True)

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=self.base));self.ram=self.root/'run';self.ram.mkdir(mode=0o755)
        self.parent=self.ram/'initramfs';self.parent.mkdir(mode=0o755)
        self.directory=self.parent/('rog5-gpu-iommu-display-'+OWNER);self.directory.mkdir(mode=0o700)
        self.b=load(self.source,'actual_context')
        self.b.ENTRY=self.parent/'entered.json';self.b.INITIALIZER_ENTRY=self.parent/'old-entered.json'
        descriptor=b'inert fixture descriptor\n'
        self.identity=dict(boot_id=BOOT,owner=OWNER,release='7.1.4-rog5-production',bundle='fixture-production',
            descriptor_sha256=hashlib.sha256(descriptor).hexdigest(),board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57')
        files={n:(ROOT/'scripts/device'/n).read_bytes() for n in SOURCES};files['backend.py']=self.source.read_bytes()
        self.value=dict(format='rog5-gpu-iommu-display-backend-v1',phase='gpu-iommu-display',boot_id=BOOT,owner=OWNER,
            monitor_receipt_sha256='2'*64,artifact_identity=self.identity.copy(),files={n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()})
        for n,raw in files.items():self.write(self.directory/n,raw)
        self.pin=self.manifest()
        self.mountinfo=self.root/'mountinfo';device=self.ram.stat().st_dev
        self.mountinfo.write_text(f'10 9 {os.major(device)}:{os.minor(device)} / /run rw - tmpfs tmpfs rw\n')
        original_fstat=os.fstat;original_lstat=Path.lstat
        class Owned:
            def __init__(self,st):self.st=st;self.st_uid=self.st_gid=0
            def __getattr__(self,k):return getattr(self.st,k)
            def __dir__(self):return dir(self.st)
        def mapped(path):return {'/run':self.ram,'/run/initramfs':self.parent,'/proc/self/mountinfo':self.mountinfo}.get(str(path),Path(path))
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(self.b,'Path',mapped))
        self.stack.enter_context(patch.object(os,'geteuid',return_value=0))
        self.stack.enter_context(patch.object(os,'fstat',side_effect=lambda fd:Owned(original_fstat(fd))))
        self.stack.enter_context(patch.object(Path,'lstat',lambda p,*a,**kw:Owned(original_lstat(p,*a,**kw))))

    def write(self,p,raw):
        p.write_bytes(raw);p.chmod(0o600)

    def manifest(self):
        raw=self.b.encoded(self.value);self.write(self.directory/'manifest.json',raw)
        return hashlib.sha256(raw).hexdigest()

    def admit(self):return self.b.context(self.directory,self.pin)

    def test_complete_production_context_has_no_query_requirement(self):
        self.assertEqual(self.admit(),self.value)
        self.assertFalse((self.directory/'rog5-gpu-query').exists())

    def test_actual_component_is_constructed_from_validated_sources(self):
        value=self.admit();component=self.b.load_component(self.directory,value)
        self.assertEqual(component.__class__.__name__,'Component')
        self.assertEqual(len(component.modules.MODULES),14)
        intent=component.modules.entry_intent(self.identity)
        self.assertEqual(intent['maximum_insertions'],14)
        self.assertEqual(intent['drm_opens'],0)

    def test_consumed_entry_blocks_new_context_but_not_cleanup_binding(self):
        value=self.admit()
        for path in (self.b.ENTRY,self.b.INITIALIZER_ENTRY,self.directory/'run-entered.json'):
            self.write(path,b'{"consumed":true}\n')
            with self.assertRaisesRegex(ValueError,'already entered'):self.admit()
            component=self.b.load_component(self.directory,value)
            self.assertEqual(component.__class__.__name__,'Component')
            self.assertEqual(path.read_bytes(),b'{"consumed":true}\n')
            path.unlink()  # Owned inert fixture only; no actual claim exists.

    def test_manifest_pin_and_retained_binding_cannot_change(self):
        value=self.admit();self.value['monitor_receipt_sha256']='3'*64;self.manifest()
        with self.assertRaisesRegex(ValueError,'manifest'):self.admit()
        with self.assertRaisesRegex(ValueError,'manifest'):self.b.load_component(self.directory,value)

    def test_noncanonical_or_duplicate_manifest_is_refused_even_if_pinned(self):
        raw=self.b.encoded(self.value)
        for bad in (b' '+raw,raw.replace(b'{',b'{"phase":"duplicate",',1)):
            self.write(self.directory/'manifest.json',bad);self.pin=hashlib.sha256(bad).hexdigest()
            with self.assertRaises(ValueError):self.admit()

    def test_all_source_bytes_are_rechecked_after_entry(self):
        value=self.admit();self.write(self.b.ENTRY,b'fixture consumed\n')
        for name in value['files']:
            p=self.directory/name;raw=p.read_bytes();self.write(p,raw+b'\n# changed\n')
            with self.subTest(name=name),self.assertRaises(ValueError):self.b.load_component(self.directory,value)
            self.write(p,raw)

    def test_manifest_cannot_repin_foreign_component(self):
        name='display-component.py';p=self.directory/name;self.write(p,b'raise RuntimeError("must not execute")\n')
        self.value['files'][name]=hashlib.sha256(p.read_bytes()).hexdigest();self.pin=self.manifest()
        with self.assertRaises(ValueError):self.admit()

    def test_inventory_rejects_missing_extra_and_historical_sources(self):
        for name in ('initialize.py','provider.py','rog5-gpu-query'):
            self.value['files'][name]='0'*64;self.pin=self.manifest()
            with self.subTest(name=name),self.assertRaises(ValueError):self.admit()
            del self.value['files'][name]
        del self.value['files']['display-component.py'];self.pin=self.manifest()
        with self.assertRaises(ValueError):self.admit()

    def test_artifact_identity_must_match_outer_boot_owner_and_board(self):
        for key,bad in (('boot_id','00000000-0000-0000-0000-000000000000'),('owner','b'*32),('release','old'),('board_dtb_sha256','0'*64),('descriptor_sha256','x'),('bundle','../bad')):
            old=self.value['artifact_identity'][key];self.value['artifact_identity'][key]=bad;self.pin=self.manifest()
            with self.subTest(key=key),self.assertRaises(ValueError):self.admit()
            self.value['artifact_identity'][key]=old

    def test_manifest_and_sources_reject_bad_modes_links_and_symlinks(self):
        for name in ('manifest.json','display-component.py'):
            p=self.directory/name;raw=p.read_bytes();p.chmod(0o666)
            with self.assertRaises(ValueError):self.admit()
            p.chmod(0o600);link=self.root/'hardlink';os.link(p,link)
            with self.assertRaises(ValueError):self.admit()
            link.unlink();p.unlink();target=self.root/'source-target';self.write(target,raw);p.symlink_to(target)
            with self.assertRaises((ValueError,OSError)):self.admit()
            p.unlink();self.write(p,raw);target.unlink()

    def test_ram_parent_namespace_and_mount_guards(self):
        self.mountinfo.write_text(self.mountinfo.read_text().replace('tmpfs','ext4'))
        with self.assertRaisesRegex(ValueError,'filesystem'):self.admit()
        self.mountinfo.write_text(self.mountinfo.read_text().replace('ext4','tmpfs'))
        self.directory.chmod(0o755)
        with self.assertRaisesRegex(ValueError,'namespace'):self.admit()
        self.directory.chmod(0o700);self.parent.chmod(0o777)
        with self.assertRaisesRegex(ValueError,'parent'):self.admit()

    def test_loader_identity_is_not_fabricated_from_manifest(self):
        component=self.b.load_component(self.directory,self.admit())
        fixture=load(ROOT/'scripts/device/test-display-endpoint.py','endpoint_fixture').EndpointFixture()
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        ns=component.endpoint.identity.__func__.__globals__;ns['PROC']=fixture.proc;ns['DESCRIPTOR']=fixture.descriptor
        self.assertEqual(component.identity(BOOT),self.identity)
        fixture.write(fixture.proc/'cmdline','rog5.bundle=wrong\n')
        with self.assertRaises(ValueError):component.identity(BOOT)

    def transport(self):
        path=self.base/'transport.py'
        if not path.exists():
            path.write_bytes((ROOT/'scripts/device/fixtures/display-loader/transport-before.py').read_bytes())
            for patch_name in ('0003-production-transport.patch','0008-production-staging.patch'):
                subprocess.run(['git','apply',str(ROOT/'patches/display-controller'/patch_name)],cwd=self.base,check=True,capture_output=True)
        tree=ast.parse(path.read_text())
        functions={'need','sources','identity','stage_plan','stage','ssh_argv'}
        constants={'SOURCE_PINS','STAGE'}
        nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or
               isinstance(n,ast.FunctionDef) and n.name in functions or
               isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
        t=types.ModuleType('staging_transport');t.__file__=str(path)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),t.__dict__)
        t.HERE=self.directory;t.B=self.b
        # The unchanged host raw() ownership reader has separate coverage. All
        # exact source digest comparisons still execute on real fixture bytes.
        t.raw=lambda path,*_:path.read_bytes()
        contract=load(ROOT/'scripts/device/display-component.py','host_contract').HostContract(self.identity)
        owner=types.SimpleNamespace(admission=dict(boot_id=BOOT,owner=OWNER),receipt_sha='2'*64)
        return t,contract,owner

    def execute_stage(self,script):
        # Remap only fixed RAM/proc paths into this inert filesystem. The exact
        # generated program and checked backend/component/endpoint code execute.
        proc=self.root/'proc'
        for name,raw in [('sys/kernel/random/boot_id',BOOT+'\n'),('sys/kernel/osrelease',self.identity['release']+'\n'),
                         ('cmdline','rog5.bundle=fixture-production\n')]:
            p=proc/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(raw)
        descriptor=self.ram/'rog5-native-wifi/trial-descriptor';descriptor.parent.mkdir(exist_ok=True)
        if descriptor.exists():descriptor.chmod(0o600)
        descriptor.write_bytes(b'inert fixture descriptor\n');descriptor.chmod(0o444)
        (proc/'self').mkdir(exist_ok=True);(proc/'self/mountinfo').write_bytes(self.mountinfo.read_bytes())
        real_import=builtins.__import__
        def mapped(path):
            text=str(path)
            if text=='/run' or text.startswith('/run/'):return self.ram/text.removeprefix('/run').lstrip('/')
            if text=='/proc' or text.startswith('/proc/'):return proc/text.removeprefix('/proc').lstrip('/')
            return Path(path)
        def imported(name,*args,**kwargs):
            if name=='pathlib':return types.SimpleNamespace(Path=mapped)
            return real_import(name,*args,**kwargs)
        env={'__name__':'fixture_stage','__builtins__':dict(vars(builtins),__import__=imported)}
        import io
        output=io.StringIO()
        with contextlib.redirect_stdout(output):exec(compile(script,'<actual-stage>','exec'),env)
        return json.loads(output.getvalue())

    def test_stage_plan_binds_current_sources_without_module_or_query_transfer(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        self.assertLess(len(plan['script'].encode()),3*1024*1024)
        self.assertEqual(plan['identity']['boot_id'],BOOT)
        self.assertEqual(set(t.SOURCE_PINS),{'backend.py',*SOURCES})
        self.assertEqual(t.SOURCE_PINS,{n:hashlib.sha256((self.directory/n).read_bytes()).hexdigest() for n in t.SOURCE_PINS})
        self.assertFalse((self.directory/'run-entered.json').exists())

    def test_actual_stage_exclusive_publication_and_post_entry_binding(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        # Move only the owned input fixture; target output must be new.
        backup=self.root/'input-sources';self.directory.rename(backup)
        result=self.execute_stage(plan['script'])
        self.assertEqual(result['status'],'PASS_RAM_STAGE')
        self.assertEqual(result['identity'],self.identity)
        self.assertEqual(self.b.context(self.directory,plan['manifest_sha256'])['artifact_identity'],self.identity)
        with self.assertRaises((ValueError,FileExistsError)):self.execute_stage(plan['script'])
        self.assertTrue((self.directory/'manifest.json').is_file())
        self.assertEqual(set(p.name for p in self.directory.iterdir()),{'manifest.json',*SOURCES,'backend.py'})

    def test_stage_refuses_nonram_parent_before_writing(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        self.directory.rename(self.root/'input-sources');self.mountinfo.write_text(self.mountinfo.read_text().replace('tmpfs','ext4'))
        with self.assertRaisesRegex(ValueError,'filesystem'):self.execute_stage(plan['script'])
        self.assertFalse(self.directory.exists())

    def test_stage_refuses_consumed_global_entry_before_writing(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        self.directory.rename(self.root/'input-sources')
        entered=self.parent/'rog5-gpu-iommu-display-entered.json';self.write(entered,b'prior fixture entry\n')
        with self.assertRaises(ValueError):self.execute_stage(plan['script'])
        self.assertFalse(self.directory.exists());self.assertEqual(entered.read_bytes(),b'prior fixture entry\n')

    def test_stage_interruption_closes_partial_file_and_owned_directory(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        self.directory.rename(self.root/'input-sources');real_open=os.open;real_fstat=os.fstat
        opened=[];trigger=[]
        def opening(path,flags,*args,**kwargs):
            fd=real_open(path,flags,*args,**kwargs)
            if flags & os.O_CREAT and kwargs.get('dir_fd') is not None:opened.append(fd);trigger.append(fd)
            return fd
        def observed(fd):
            if trigger and fd==trigger[-1]:
                trigger.clear();raise KeyboardInterrupt('fixture after file creation')
            return real_fstat(fd)
        with patch.object(os,'open',side_effect=opening),patch.object(os,'fstat',side_effect=observed):
            with self.assertRaisesRegex(KeyboardInterrupt,'fixture after file creation'):self.execute_stage(plan['script'])
        try:
            for fd in opened:
                with self.assertRaises(OSError):real_fstat(fd)
            self.assertFalse(self.directory.exists())
        finally:
            for fd in opened:
                try:os.close(fd)
                except OSError:pass

    def test_stage_failure_after_mkdir_removes_only_owned_empty_directory(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        self.directory.rename(self.root/'input-sources');real_open=os.open
        def opening(path,flags,*args,**kwargs):
            if str(path)==str(self.directory) and flags & os.O_DIRECTORY:raise OSError('fixture directory open')
            return real_open(path,flags,*args,**kwargs)
        with patch.object(os,'open',side_effect=opening):
            with self.assertRaisesRegex(OSError,'fixture directory open'):self.execute_stage(plan['script'])
        self.assertFalse(self.directory.exists())

    def test_failed_stage_never_deletes_replaced_file(self):
        t,contract,owner=self.transport();plan=t.stage_plan(owner,contract)
        self.directory.rename(self.root/'input-sources');real_write=os.write;replaced=[]
        def writing(fd,data):
            count=real_write(fd,data)
            if not replaced:
                path=self.directory/'backend.py';path.unlink();self.write(path,b'foreign replacement\n')
                replaced.append(path)
                raise KeyboardInterrupt('fixture after replacement')
            return count
        with patch.object(os,'write',side_effect=writing):
            with self.assertRaisesRegex(KeyboardInterrupt,'fixture after replacement'):self.execute_stage(plan['script'])
        self.assertEqual(replaced[0].read_bytes(),b'foreign replacement\n')
        self.assertEqual(list(self.directory.iterdir()),replaced)

    def host_stage(self,invalid_scope=False):
        t,contract,owner=self.transport();backup=self.root/'input-sources'
        self.directory.rename(backup);t.HERE=backup;t.save=self.b.save;t.SOURCE={'fixture':True}
        checks=[];owner.check=lambda seconds=5:checks.append(seconds)
        def perform(request,_):
            self.assertEqual(request['timeout'],35)
            value=self.execute_stage(request['script'])
            # Translate only the path remapping used by the filesystem fixture.
            value['namespace']='/run/initramfs/'+self.directory.name
            if invalid_scope:value['module_payload_staged']=0
            raw=self.b.encoded(value)
            return dict(status='PASS_TRANSPORT_COMPLETED',mode='normal',source=t.SOURCE,command_invoked=True,
                command=dict(returncode=0,timed_out=False,reaped=True,stdout_base64=base64.b64encode(raw).decode(),
                    stderr_base64='',stdout_sha256=hashlib.sha256(raw).hexdigest(),stderr_sha256=hashlib.sha256(b'').hexdigest()))
        t.W=types.SimpleNamespace(request=json.loads,load_deployed=lambda:None,perform=perform)
        output=self.root/'stage-records'
        output.mkdir(mode=0o700)  # The actual enclosing session owns this directory.
        if invalid_scope:
            with self.assertRaises(ValueError):t.stage(owner,output,contract)
            self.assertFalse((output/'stage-result.json').exists())
        else:
            plan=t.stage(owner,output,contract)
            result=json.loads((output/'stage-result.json').read_bytes())
            self.assertEqual(result['identity'],self.identity);self.assertIs(result['module_payload_staged'],False)
            self.assertEqual(checks,[40,40,5]);self.assertEqual(plan['namespace'],result['namespace'])

    def test_host_stage_collects_actual_target_receipt(self):self.host_stage()

    def test_host_stage_rejects_integer_instead_of_false(self):self.host_stage(invalid_scope=True)

    def test_pyc_cannot_enter_verified_namespace(self):
        self.write(self.directory/'display-component.pyc',b'invalid stale pyc')
        with self.assertRaises(ValueError):self.admit()


if __name__=='__main__':unittest.main(defaultTest='Context.test_complete_production_context_has_no_query_requirement' if BEFORE else None)
