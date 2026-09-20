#!/usr/bin/env python3
"""Actual patched Supervisor with real pipes/workers and inert target callbacks.

--before runs the two defect regressions against exact retained historical bytes.
No phone, module, root authority, signing, admission or live transport is used.
"""
import hashlib
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BEFORE = '--before' in sys.argv
if BEFORE:
    sys.argv.remove('--before')
OLD = ROOT/'scripts/device/fixtures/display-loader/backend-before.py'
PATCH = ROOT/'patches/display-controller/0002-production-supervisor.patch'
OLD_SHA = '840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d'
BOOT = '00000000-0000-4000-8000-000000000001'
OWNER = '1'*32
WHO = dict(boot_id=BOOT, owner=OWNER, release='7.1.4-rog5-production', bundle='fixture-production')
VALUE = dict(phase='gpu-iommu-display', boot_id=BOOT, owner=OWNER, monitor_receipt_sha256='2'*64)


def load(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def blank():
    endpoint = dict(identity=WHO, path='/fixture/brightness', brightness=0)
    return dict(status='PASS_ZERO_BRIGHTNESS_COMMAND', before=endpoint.copy(), after=endpoint.copy(),
                write_bytes=2, brightness_readback=0, physical_darkness_verified=False,
                full_health_verified=False, framebuffer_qualified=False)


def good_result(loader):
    return dict(status='PASS_MODULES_AND_BLANK', seconds=.01, entered=True, panel_attempted=True,
        insertions=[dict(status='PASS_INSERTION', filename=Path(path).name, seconds=.001, pid=123,
                        returncode=0, reaped=True, stdout='', stderr='', error=None, retry_allowed=False)
                    for _, path, *_ in loader.MODULES],
        checkpoints=['refgen','gpucc','msm'], preconsumer_checks=['msm','panel_asus_rog5_ams678'],
        registration=dict(identity=WHO, brightness=0), blank=blank(), cleanup_blank=None,
        endpoint=dict(status='PASS_FRAMEBUFFER_SYSFS', identity=WHO, path='/fixture/fb0',
                      name='msmdrmfb', virtual_size=[1080,2448], mode='U:1080x2448p-60', bits_per_pixel=32,
                      physical_scanout_verified=False, pixel_layout_verified=False, device_opened=False),
        error=None, cleanup_errors=[], retry_allowed=False, driver_reprobes=0, drm_opens=0,
        physical_scanout_verified=False, physical_darkness_verified=False, full_health_verified=False,
        admission_granted=False)


class Run:
    """One owned supervisor process; action and cleanup are its actual children."""
    def __init__(self, case, scenario='pass', lifetime=2.0, lease=.4):
        self.case = case
        self.directory = Path(tempfile.mkdtemp(dir=case.base))
        (self.directory/'boot').write_text(BOOT)
        if scenario=='prior-entry':
            (self.directory/'global-entered.json').write_text('{"prior":"preserve"}\n')
        self.value = VALUE.copy()
        self.seq = 0
        incoming, self.write = os.pipe()
        self.read, outgoing = os.pipe()
        self.pid = os.fork()
        if self.pid == 0:
            os.close(self.write); os.close(self.read)
            b = case.b
            b.ENTRY = self.directory/'global-entered.json'
            b.INITIALIZER_ENTRY = self.directory/'legacy-entered.json'
            b.LOCK = self.directory/'global.lock'
            b.LEASE, b.LIFETIME, b.CLEANUP, b.REAP = lease, lifetime, .2, .5
            original_fstat = os.fstat
            class Owned:
                def __init__(self, st): self.st = st; self.st_uid = self.st_gid = 0
                def __getattr__(self, key): return getattr(self.st, key)
            # Only lock ownership is mocked; no actual root authority is granted.
            b.os.fstat = lambda fd: Owned(original_fstat(fd))
            b.load_component = lambda _: case.component(self.directory, scenario)
            if scenario == 'entry-interrupt':
                original_emit = b.Supervisor.emit
                def emit(supervisor, kind, payload=None):
                    if kind == 'enter-request': raise KeyboardInterrupt('fixture entry interruption')
                    return original_emit(supervisor, kind, payload)
                b.Supervisor.emit = emit
            try:
                result = b.Supervisor(self.directory, self.value, incoming, outgoing).run()
                os._exit(0 if result['status'] == 'PASS_PRODUCTION_DISPLAY_AND_CLEANUP' else 1)
            except BaseException:
                os._exit(2)
        os.close(incoming); os.close(outgoing)
        self.reader = case.b.Records(self.read)
        self.pending = []
        case.addCleanup(self.close)

    def event(self, timeout=3):
        deadline = time.monotonic()+timeout
        while not self.pending:
            with selectors.DefaultSelector() as selector:
                selector.register(self.read, selectors.EVENT_READ)
                self.case.assertTrue(selector.select(max(0,deadline-time.monotonic())), 'event deadline')
                self.pending += self.reader.read()
        return self.pending.pop(0)

    def send(self, command, intent=None, **changes):
        self.seq += 1
        row = dict(self.value, sequence=self.seq, command=command, intent_sha256=intent)
        row.update(changes)
        self.case.b.send(self.write, row)

    def arm(self):
        self.case.assertEqual(self.event()['event'],'transport-ready')
        self.send('start')
        row = self.event()
        self.case.assertEqual(row['event'],'enter-request')
        return row['payload']['intent_sha256']

    def entered(self):
        self.send('enter-ack', self.arm())
        until = time.monotonic()+1
        while not (self.directory/'action-started').exists():
            self.case.assertLess(time.monotonic(), until)
            time.sleep(.005)

    def terminal(self):
        row = self.event()
        self.case.assertEqual(row['event'],'terminal')
        return row['payload']

    def close(self):
        if self.pid is not None:
            until=time.monotonic()+3
            while time.monotonic()<until:
                got, _ = os.waitpid(self.pid,os.WNOHANG)
                if got:
                    self.pid=None
                    break
                time.sleep(.01)
            if self.pid is not None:
                os.kill(self.pid,signal.SIGKILL);os.waitpid(self.pid,0);self.pid=None
                self.case.fail('supervisor did not exit')
        for fd in (self.write,self.read):
            if fd is not None: os.close(fd)


class Supervisor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='display-supervisor-',
            dir=os.environ.get('TMPDIR', str(Path.home()/'.local/state')))
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base=Path(cls.temp.name)
        if hashlib.sha256(OLD.read_bytes()).hexdigest()!=OLD_SHA:
            raise ValueError('historical backend fixture identity differs')
        cls.source=cls.base/'backend.py';cls.source.write_bytes(OLD.read_bytes())
        if not BEFORE:
            subprocess.run(['git','apply',str(PATCH)],cwd=cls.base,check=True,capture_output=True)

    def setUp(self):
        self.b=load(self.source,'bounded_supervisor')

    def component(self, directory, scenario):
        loader=load(ROOT/'scripts/device/load-production-display.py','actual_loader')
        validator=load(ROOT/'scripts/device/display-component.py','actual_validator')
        def identity(boot):
            self.b.need((directory/'boot').read_text()==boot==BOOT,'fixture boot changed')
            return WHO.copy()
        def zero(boot, authorize):
            self.b.need(authorize() is True,'fixture cleanup ownership')
            if scenario=='cleanup-fail':raise PermissionError('fixture exact brightness EPERM')
            if scenario=='cleanup-hang':time.sleep(30)
            (directory/'zero').write_text('0')
            result=blank()
            if scenario=='bad-zero':result['write_bytes']=0
            return result
        def entry(boot,owner):
            self.b.need(owner==OWNER,'fixture owner')
            return loader.entry_intent(identity(boot))
        def action(boot, authorize, enter, ownership):
            self.b.need(authorize() is True and ownership() is True,'fixture initial ownership')
            intent=entry(boot,OWNER)
            if scenario=='wrong-scope':intent['maximum_insertions']=2
            self.b.need(enter(intent) is True,'fixture entry not acknowledged')
            (directory/'action-started').write_text('yes')
            if scenario in ('hang','stop','eof','cleanup-hang','lifetime'):time.sleep(30)
            if scenario=='boot-change':
                (directory/'boot').write_text('other-boot');raise ValueError('fixture boot changed')
            if scenario=='action-fail':raise ValueError('fixture action failure')
            result=good_result(loader)
            if scenario=='bad-result':result['insertions'][-1]['returncode']=42
            if scenario=='validator-false':result['fixture_false']=True
            return result
        def validate_result(result,boot,owner):
            if scenario=='validator-false':return False
            self.b.need(owner==OWNER,'fixture owner')
            return validator.validate_result(result,identity(boot))
        return types.SimpleNamespace(identity=identity, endpoint=types.SimpleNamespace(blank=zero),
            loader=types.SimpleNamespace(load_once=action), entry_intent=entry,
            validate_result=validate_result,
            validate_blank=lambda value,boot,owner:validator.validate_blank(value,identity(boot)))

    def test_entry_interruption_never_publishes_pass(self):
        # No private files/root/fork needed: exercise actual Supervisor.run at
        # the point after durable entry and before host acknowledgement.
        b=self.b;sup=b.Supervisor(Path('/unused'),VALUE,10,11)
        class Select:
            def __init__(self):self.events=iter(('host','worker'))
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def register(self,*args):pass
            def fileno(self):return 20
            def select(self,*args):return [(types.SimpleNamespace(data=next(self.events)),None)]
        channel=types.SimpleNamespace(fileno=lambda:30,close=lambda:None)
        payload={'scope':'fixture'}
        readers=[types.SimpleNamespace(read=lambda:[dict(VALUE,sequence=1,command='start',intent_sha256=None)]),
                 types.SimpleNamespace(read=lambda:[dict(kind='enter',payload=payload)])]
        meta=types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_uid=0,st_gid=0,st_nlink=1)
        output=[]; saved=[]
        def emit(kind, value=None):
            output.append((kind,value))
            if kind=='enter-request':raise KeyboardInterrupt('entry interruption')
        proc=dict(pid=123,reaped=True,group_absent=True,exitcode=-9,killed=True)
        component=types.SimpleNamespace(entry_intent=lambda *_:payload)
        with patch.object(b,'Records',side_effect=readers),patch.object(b.os,'open',return_value=999), \
             patch.object(b.os,'fstat',return_value=meta),patch.object(b.os,'close'), \
             patch.object(b.os.path,'lexists',return_value=False),patch.object(b.fcntl,'flock'), \
             patch.object(b,'save',side_effect=lambda path,value:saved.append((path,value))), \
             patch.object(b.selectors,'DefaultSelector',return_value=Select()), \
             patch.object(b,'spawn',return_value=(123,channel)),patch.object(b,'stop',return_value=proc), \
             patch.object(b,'load_component',return_value=component),patch.object(sup,'emit',side_effect=emit), \
             patch.object(sup,'cleanup',return_value=(blank(),dict(proc,exitcode=0))):
            try:sup.run()
            except KeyboardInterrupt:pass
        self.assertEqual(output[-1][0],'terminal')
        result=output[-1][1]
        self.assertTrue(result['entered']);self.assertFalse(result['acknowledged'])
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['error']['type'],'KeyboardInterrupt')
        self.assertEqual(saved[-1][1],result)

    def cleanup_error(self, detail):
        b=self.b;sup=b.Supervisor(Path('/unused'),VALUE)
        channel=types.SimpleNamespace(fileno=lambda:99,close=lambda:None)
        reader=types.SimpleNamespace(read=lambda:[dict(kind='error',payload=detail)])
        class Select:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def register(self,*args):pass
            def select(self,*args):return [True]
        proc=dict(pid=123,reaped=True,group_absent=True,exitcode=1,killed=True)
        with patch.object(b,'spawn',return_value=(123,channel)),patch.object(b,'Records',return_value=reader), \
             patch.object(b.selectors,'DefaultSelector',return_value=Select()),patch.object(b,'stop',return_value=proc):
            with self.assertRaises(ValueError) as error:sup.cleanup()
        self.assertEqual(error.exception.process,proc)
        return error.exception

    def test_cleanup_preserves_worker_diagnostic(self):
        detail=dict(type='PermissionError',reason='fixture exact brightness EPERM',component={'status':'FAIL_ZERO'})
        self.assertEqual(getattr(self.cleanup_error(detail),'worker_error',None),detail)

    def test_large_cleanup_diagnostic_keeps_reason_and_hash(self):
        detail=dict(type='ValueError',reason='fixture detailed failure',component={'log':'x'*20000})
        error=self.cleanup_error(detail)
        self.assertEqual(error.worker_error['reason'],detail['reason'])
        self.assertTrue(error.worker_error['component_omitted'])
        self.assertEqual(error.worker_error['payload_sha256'],hashlib.sha256(self.b.encoded(detail)).hexdigest())
        self.assertLess(len(self.b.encoded(error.worker_error)),8192)

    def test_complete_real_workers_and_durable_ack(self):
        run=Run(self);pin=run.arm()
        record=self.b.decode((run.directory/'global-entered.json').read_bytes())
        self.assertEqual(record['intent_sha256'],pin)
        self.assertFalse((run.directory/'action-started').exists())
        run.send('enter-ack',pin)
        result=run.terminal()
        self.assertEqual(result['status'],'PASS_PRODUCTION_DISPLAY_AND_CLEANUP')
        self.assertTrue(result['remote_reaped']);self.assertTrue(result['acknowledged'])
        self.assertEqual(len(result['component']['insertions']),14)
        self.assertEqual(self.b.decode((run.directory/'result.json').read_bytes()),result)
        for key in ('action_process','cleanup_process'):
            with self.assertRaises(ProcessLookupError):os.kill(result[key]['pid'],0)

    def test_changed_scope_is_rejected_before_durable_entry(self):
        run=Run(self,'wrong-scope');self.assertEqual(run.event()['event'],'transport-ready');run.send('start')
        result=run.terminal();self.assertEqual(result['status'],'FAIL')
        self.assertFalse(result['entered']);self.assertFalse((run.directory/'global-entered.json').exists())
        self.assertFalse((run.directory/'action-started').exists())

    def test_existing_entry_remains_consumed(self):
        run=Run(self,'prior-entry');result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertFalse(result['entered'])
        self.assertEqual((run.directory/'global-entered.json').read_text(),'{"prior":"preserve"}\n')
        self.assertFalse((run.directory/'run-entered.json').exists())
        self.assertFalse((run.directory/'result.json').exists())

    def test_missing_ack_expires_without_action(self):
        run=Run(self);run.arm();result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['entered'])
        self.assertFalse(result['acknowledged']);self.assertFalse((run.directory/'action-started').exists())
        self.assertTrue(result['remote_reaped'])

    def test_wrong_ack_never_starts_action(self):
        run=Run(self);run.arm();run.send('enter-ack','0'*64)
        result=run.terminal();self.assertEqual(result['status'],'FAIL')
        self.assertFalse((run.directory/'action-started').exists())
        self.assertTrue((run.directory/'global-entered.json').exists())

    def test_expired_lease_stops_action_and_independently_cleans(self):
        run=Run(self,'hang');run.entered();result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertTrue(result['action_process']['killed']);self.assertTrue((run.directory/'zero').exists())

    def test_eof_still_cleans(self):
        run=Run(self,'eof');run.entered();os.close(run.write);run.write=None
        result=run.terminal();self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertTrue((run.directory/'zero').exists())

    def test_explicit_stop_still_cleans(self):
        run=Run(self,'stop');run.entered();run.send('stop')
        result=run.terminal();self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])

    def test_action_failure_retains_failure(self):
        run=Run(self,'action-fail');run.send('enter-ack',run.arm());result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertIn('fixture action failure',result['error']['reason'])
        self.assertTrue(result['remote_reaped'])

    def test_cleanup_error_retains_actual_child_payload(self):
        run=Run(self,'cleanup-fail');run.send('enter-ack',run.arm());result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertEqual(result['cleanup_errors'][0]['worker_error']['reason'],'fixture exact brightness EPERM')

    def test_bad_zero_receipt_fails(self):
        run=Run(self,'bad-zero');run.send('enter-ack',run.arm());result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertTrue(result['cleanup_errors'])

    def test_bad_action_receipt_fails(self):
        run=Run(self,'bad-result');run.send('enter-ack',run.arm());result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertIsNotNone(result['error'])

    def test_validator_must_explicitly_accept(self):
        run=Run(self,'validator-false');run.send('enter-ack',run.arm());result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])

    def test_boot_change_refuses_zero_on_other_boot(self):
        run=Run(self,'boot-change');run.send('enter-ack',run.arm());result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertFalse((run.directory/'zero').exists())
        self.assertTrue(result['remote_reaped'])

    def test_hung_cleanup_is_killed_and_reaped(self):
        run=Run(self,'cleanup-hang');run.entered();result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertTrue(result['cleanup_process']['killed']);self.assertLess(result['seconds'],2)

    def test_worker_lifetime_is_bounded_with_live_lease(self):
        run=Run(self,'lifetime',lifetime=.25,lease=1);run.entered();result=run.terminal()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['remote_reaped'])
        self.assertLess(result['seconds'],1)

    def test_constants_fit_loader_and_preserve_legacy_barriers(self):
        loader=load(ROOT/'scripts/device/load-production-display.py','actual_loader')
        old=load(OLD,'old_backend')
        self.assertEqual(self.b.LIFETIME,100)
        self.assertGreaterEqual(self.b.LIFETIME-loader.TOTAL_SECONDS,15)
        for name in ('PINS','ENTRY','INITIALIZER_ENTRY','LOCK','LEASE','CLEANUP','REAP'):
            self.assertEqual(getattr(self.b,name),getattr(old,name))
        import ast
        def definition(source,name):
            return ast.dump(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name))
        for name in ('context','load_component'):
            self.assertEqual(definition(self.source.read_text(),name),definition(OLD.read_text(),name))


if __name__=='__main__':
    if BEFORE:
        suite=unittest.TestSuite(Supervisor(name) for name in (
            'test_entry_interruption_never_publishes_pass','test_cleanup_preserves_worker_diagnostic'))
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    unittest.main(verbosity=2)
