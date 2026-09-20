#!/usr/bin/env python3
"""Execute the enclosing session with real duplex/process code and inert I/O.

No historical dependency imports or SSH constructors execute. Admission source
locks, health transport, staging and kernel logger effects are explicit fixtures.
The logger owns a real inert child; its 300-second lifetime uses a virtual clock.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT/'scripts/device/fixtures/display-loader/session-before.py'
PATCH = ROOT/'patches/display-controller/0004-production-session.patch'
BEFORE = '--before' in sys.argv
if BEFORE: sys.argv.remove('--before')


def load(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


D = load(ROOT/'scripts/device/test-production-display-transport.py', 'duplex_fixture')
WHO = D.WHO


def session(path):
    tree = ast.parse(path.read_text())
    constants = {'LOGGER_SECONDS', 'RECOVERY_RESERVE', 'SESSION_SECONDS',
                 'FALLBACK_SECONDS', 'DISPLAY_SECONDS', 'HEALTH_SECONDS', 'LOGGER_CLOSE_SECONDS'}
    nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))
             or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets)]
    module = types.ModuleType('actual_session')
    module.__file__ = str(path)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), module.__dict__)
    return module


class Session(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        D.Duplex.setUpClass()
        cls.addClassCleanup(D.Duplex.doClassCleanups)
        cls.base = D.Duplex.base
        cls.source = cls.base/'session.py'
        if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != '2a2316564977a2839a31f11fb0435859857b6567f38fc5f0752ca27b5f63fa8c':
            raise ValueError('historical session fixture changed')
        cls.source.write_bytes(FIXTURE.read_bytes())
        if not BEFORE:
            subprocess.run(['git', 'apply', str(PATCH)], cwd=cls.base, check=True, capture_output=True)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(dir=self.base))
        self.s = session(self.source)
        self.s.STATE = self.root
        self.s.HERE = self.root/'session-source'; self.s.HERE.mkdir()
        self.s.OUTPUT = self.s.HERE/'session-r1'
        self.b = D.load(D.Duplex.backend, 'actual_backend')
        self.t = D.transport(D.Duplex.source, self.b)
        # Execute the original bounded metadata reader, excluding staging code.
        tree = ast.parse(D.Duplex.source.read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'raw')
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(D.Duplex.source), 'exec'), self.t.__dict__)
        self.s.T = self.t
        def save(path,value):
            self.b.save(path,value)
            return hashlib.sha256(path.read_bytes()).hexdigest()
        self.s.save = save
        self.real_collect_health = self.s.collect_health
        self.c = D.load(ROOT/'scripts/device/display-component.py', 'contract')
        self.contract = self.c.HostContract(WHO)
        self.offset = 0
        self.s.time = types.SimpleNamespace(monotonic=lambda: time.monotonic()+self.offset)
        self.expires = self.s.time.monotonic()+4000
        self.calls = []; self.logs = []; self.health_fail = set(); self.scenario = 'pass'
        self.log_fault = None; self.stage_seconds = 0; self.stage_fault = None
        self.restore_fault = None
        output = self.root/'gpu-iommu-controller-r1/execution'; output.mkdir(parents=True)
        results = dict(close_capture=dict(status='PASS', capture_status='PASS', full_lifetime=True, cleanup_complete=True),
                       post_capture_health=dict(status='PASS', identity=copy.deepcopy(WHO), current_boot_healthy=True,
                                                physical_guards_passed=True))
        self.controller = types.SimpleNamespace(context=dict(owner=D.OWNER, admission_sha256='a'*64),
            output=output, entered=list(results), results=results, target_identity=copy.deepcopy(WHO), selection_restored=False)
        def restore():
            self.calls.append('recovery'); self.controller.entered.append('locate_fallback')
            if self.restore_fault: raise self.restore_fault
            self.controller.selection_restored = True
        self.controller.restore_fallback = restore
        self.boot = dict(status='COMPONENT_PASS', successor_running=True, errors=[],
            target_identity=copy.deepcopy(WHO), entered=list(results), phases=list(results))
        self.credentials = types.SimpleNamespace(check=lambda: self.calls.append('credentials'))
        self.ad = types.SimpleNamespace(OUTPUT=output, common=lambda _: dict(expires_monotonic=self.expires),
            receipt=lambda p, _: json.loads(p.read_bytes()),
            A=types.SimpleNamespace(exact_json=lambda a,b: json.dumps(a, sort_keys=True)==json.dumps(b, sort_keys=True)))
        self.original_cohort = self.s.cohort
        self.s.cohort = lambda _: dict(fixture_source_lock='not an admission')
        self.t.target = lambda boot: copy.deepcopy(WHO)  # historical admission comparison only
        self.write_boot()
        def provider_stage(*_): self.calls.append('provider-stage'); return {}
        def provider_exchange(*_): raise ValueError('fixture refuses duplicate provider')
        self.s.P = types.SimpleNamespace(stage=provider_stage, ssh_argv=lambda *_: [], exchange=provider_exchange)
        def stage(*_):
            self.calls.append('display-stage'); self.offset += self.stage_seconds
            if self.stage_fault: raise self.stage_fault
            return {}
        self.t.stage = stage
        self.t.ssh_argv = lambda *_: self.peer_argv()
        def health(owner, label):
            owner.base(35); self.calls.append(label)
            if label in self.health_fail: raise ValueError('fixture health lost: '+label)
            owner.health_at = self.s.time.monotonic()
            return dict(status='PASS', identity=copy.deepcopy(WHO), current_boot_healthy=True,
                        physical_guards_passed=True, observed_at=owner.health_at)
        self.s.collect_health = health
        case = self
        class Logger:
            def __init__(self, directory, boot, duration):
                self.closed=False; self.started=None; self.p=None; self.duration=duration
                case.logs.append(self)
            def start(self):
                self.started=case.s.time.monotonic(); case.calls.append('logger-start')
                self.p=subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time; time.sleep(30)'],
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                case.addCleanup(self.dispose)
                if case.log_fault == 'start': raise ValueError('fixture logger start')
                return dict(status='READY')
            def live(self, remaining=5):
                if case.log_fault == 'interrupt':
                    case.log_fault=None; raise KeyboardInterrupt('fixture interruption')
                if case.log_fault == 'live': raise ValueError('fixture logger live')
                case.s.need(self.p.poll() is None and case.s.time.monotonic()+remaining < self.started+self.duration,
                            'fixture logger lifetime')
                return True
            def dispose(self):
                if self.p is not None and self.p.poll() is None: self.p.kill()
                if self.p is not None: self.p.wait(timeout=2)
            def close(self, cancel=False):
                case.calls.append('logger-cancel' if cancel else 'logger-close')
                if not cancel: case.offset += max(0, self.started+self.duration-case.s.time.monotonic())
                self.dispose(); self.closed=True
                if case.log_fault == 'close': raise ValueError('fixture logger close')
                return dict(status='FAIL' if case.log_fault == 'terminal' else 'PASS', child_reaped=True)
        self.s.K = types.SimpleNamespace(KernelLog=Logger)

    def write_boot(self):
        (self.ad.OUTPUT/'result.json').write_text(json.dumps(self.boot))

    def peer_argv(self):
        self.calls.append('display-argv')
        directory=self.root/'peer'; directory.mkdir()
        (directory/'peer.json').write_text(json.dumps(dict(identity=WHO,
            monitor_receipt_sha256=hashlib.sha256((self.s.OUTPUT/'entered.json').read_bytes()).hexdigest())))
        return [sys.executable, '-I', '-B', str(ROOT/'scripts/device/test-production-display-transport.py'),
                '--peer', str(directory), self.scenario, str(D.Duplex.backend)]

    def run_session(self):
        args=(self.ad, self.controller, self.credentials, self.boot)
        if not BEFORE: args += (self.contract,)
        return self.s.run(*args)

    def admit(self):
        args=(self.ad, self.controller, self.credentials, self.boot)
        if not BEFORE: args += (self.contract,)
        return self.s.admission(*args)

    def owner(self):
        self.s.OUTPUT.mkdir(); pin=self.s.save(self.s.OUTPUT/'entered.json', {'fixture': True})
        return self.s.Owner(self.ad, self.controller, self.credentials, copy.deepcopy(WHO), pin)

    def test_recovery_reserve_on_every_owner_check(self):
        owner=self.owner(); self.expires=self.s.time.monotonic()+1850
        with self.assertRaisesRegex(ValueError, 'session lifetime'): owner.base(100)

    def test_no_duplicate_provider_dispatch(self):
        self.run_session()
        self.assertNotIn('provider-stage', self.calls)
        self.assertEqual(self.calls.count('display-stage'), 1)

    def test_interruption_is_failed_terminal_and_logger_reaped(self):
        self.log_fault='interrupt'
        try: result=self.run_session()
        except KeyboardInterrupt: self.fail('session interruption escaped without failed terminal')
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['error']['type'], 'KeyboardInterrupt')
        self.assertTrue(self.logs[0].closed); self.assertIsNotNone(self.logs[0].p.returncode)
        self.assertIn('health-recovery', self.calls)

    def test_success_final_health_follows_logger_close(self):
        result=self.run_session()
        self.assertEqual(result['status'], 'PASS_PRODUCTION_DISPLAY_SESSION', result['error'])
        self.assertTrue(result['healthy_target_with_cleanup'])
        self.assertLess(self.s.time.monotonic()-result['health_after']['observed_at'], 2)
        self.assertIn('health-final', self.calls)
        self.assertGreater(self.calls.index('health-final'), self.calls.index('logger-close'))
        self.assertGreaterEqual(self.offset, 299)
        for key in ('hardware_acceleration_verified', 'physical_scanout_verified', 'physical_darkness_verified',
                    'release_qualified', 'retry_allowed'): self.assertIs(result[key], False)
        entry=json.loads((self.s.OUTPUT/'entered.json').read_bytes())
        self.assertEqual(entry['maximum_module_insertions'], 14)
        self.assertEqual(entry['maximum_driver_probes'], 0)
        self.assertEqual(entry['maximum_query_opens'], 0)
        self.assertEqual(entry['expected_intent'], self.contract.entry_intent(D.BOOT,D.OWNER))

    def test_complete_session_transport_loader_endpoint(self):
        self.scenario='assembled'
        self.contract.modules.MODULES=tuple((n,p,1,'fixture') for n,p,_,_ in self.contract.modules.MODULES)
        self.contract.modules.HELPER=('helper',1,'fixture',0o644); self.contract.modules.INSERT_SECONDS=2
        result=self.run_session()
        self.assertEqual(result['status'], 'PASS_PRODUCTION_DISPLAY_SESSION', result['error'])
        self.assertEqual(len(result['component']['target']['component']['insertions']),14)
        self.assertTrue(result['component']['ssh_group_absent'])

    def test_failed_action_preserves_cleanup_without_pass(self):
        self.scenario='action-fail'; result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['healthy_target_with_cleanup'])
        self.assertIn('fixture action failure',result['component']['target']['error']['reason'])

    def test_unknown_transport_cannot_borrow_healthy_cleanup(self):
        self.t.ssh_argv=lambda *_: ['/nonexistent/local-fixture']
        result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertFalse(result['healthy_target_with_cleanup'])
        self.assertIsNotNone(result['health_after'])

    def test_logger_failures_close_children(self):
        for fault in ('start','live','close','terminal'):
            with self.subTest(fault=fault):
                if fault != 'start': self.setUp()
                self.log_fault=fault; result=self.run_session()
                self.assertEqual(result['status'],'FAIL'); self.assertTrue(self.logs[0].closed)
                self.assertIsNotNone(self.logs[0].p.returncode)

    def test_logger_closure_failure_cannot_claim_session_cleanup(self):
        self.log_fault='close'; result=self.run_session()
        self.assertEqual(result['status'],'FAIL')
        self.assertIsNotNone(result['component']['blank'])
        self.assertFalse(result['healthy_target_with_cleanup'])

    def test_failed_final_health_uses_recovery(self):
        self.health_fail={'health-final','health-recovery'}
        result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertEqual(result['recovery']['status'],'PASS_FALLBACK_RESTORED')
        self.assertFalse(result['healthy_target_with_cleanup']); self.assertIsNone(result['health_after'])

    def test_recovery_failure_stays_unproven(self):
        self.health_fail={'health-before','health-recovery'}; self.restore_fault=ValueError('fixture fallback failure')
        result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertEqual(result['recovery']['status'],'FAIL_RECOVERY_UNPROVEN')

    def test_error_record_failure_does_not_prevent_recovery(self):
        self.health_fail={'health-before','health-recovery'}
        save=self.s.save
        def failing_save(path,value):
            if path.name=='health-recovery-error.json': raise OSError(28,'fixture disk full')
            return save(path,value)
        self.s.save=failing_save
        try: result=self.run_session()
        except OSError: self.fail('diagnostic publication prevented recovery')
        self.assertIn('recovery',self.calls); self.assertEqual(result['status'],'FAIL')
        self.assertIn('health-before',result['error']['reason'])
        self.assertIn('disk full', result['health_recovery_errors'][-1]['error'])

    def test_slow_staging_refuses_logger_start(self):
        self.stage_seconds=150
        result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertFalse(self.logs)
        self.assertNotIn('display-argv',self.calls)

    def test_entry_cannot_be_retried_or_changed(self):
        result=self.run_session(); self.assertEqual(result['status'],'PASS_PRODUCTION_DISPLAY_SESSION')
        before=(self.s.OUTPUT/'entered.json').read_bytes()
        with self.assertRaises(FileExistsError): self.run_session()
        self.assertEqual((self.s.OUTPUT/'entered.json').read_bytes(),before)

    def test_entry_tamper_and_stale_health_refused(self):
        owner=self.owner(); owner.health_at=self.s.time.monotonic()-151
        with self.assertRaisesRegex(ValueError,'full health expired'): owner.check()
        owner.health_at=None; (self.s.OUTPUT/'entered.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'entry changed'): owner.base()

    def test_contract_changes_before_dispatch_refused(self):
        argv=self.t.ssh_argv
        def mutate(*args):
            result=argv(*args); self.contract.modules.MODULES=self.contract.modules.MODULES[:-1]
            return result
        self.t.ssh_argv=mutate
        result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertFalse(result['display_dispatched'])
        self.assertFalse((self.root/'peer/target-entered.json').exists())

    def test_missing_local_closure_rejects_positive_terminal(self):
        exchange=self.t.exchange
        def uncertain(*args): return dict(exchange(*args),ssh_group_absent=False)
        self.t.exchange=uncertain; result=self.run_session()
        self.assertEqual(result['status'],'FAIL'); self.assertFalse(result['healthy_target_with_cleanup'])

    def test_admission_requires_completed_exact_boot(self):
        for key,value in (('status','FAIL'),('successor_running',False),('errors',['failure'])):
            with self.subTest(key=key):
                original=self.boot[key]; self.boot[key]=value; self.write_boot()
                with self.assertRaises(ValueError): self.admit()
                self.boot[key]=original
        self.write_boot(); self.admit()
        self.assertFalse(self.s.OUTPUT.exists())

    def test_admission_requires_full_capture_and_physical_guards(self):
        for section,key in (('close_capture','cleanup_complete'),('close_capture','full_lifetime'),
                            ('post_capture_health','physical_guards_passed'),('post_capture_health','current_boot_healthy')):
            with self.subTest(section=section,key=key):
                row=self.controller.results[section]; row[key]=False
                with self.assertRaises(ValueError): self.admit()
                row[key]=True
        self.assertFalse(self.s.OUTPUT.exists())

    def test_admission_requires_reserve_and_unconsumed_recovery(self):
        self.expires=self.s.time.monotonic()+2299
        with self.assertRaisesRegex(ValueError,'reserve'): self.admit()
        self.expires=self.s.time.monotonic()+4000
        self.controller.entered.append('locate_fallback'); self.boot['entered']=list(self.controller.entered); self.write_boot()
        with self.assertRaisesRegex(ValueError,'already entered recovery'): self.admit()

    def test_admission_rejects_identity_mismatch(self):
        for key,value in (('owner','b'*32),('descriptor_sha256','b'*64),('board_dtb_sha256','b'*64)):
            with self.subTest(key=key):
                self.boot['target_identity'][key]=value; self.controller.target_identity=copy.deepcopy(self.boot['target_identity'])
                self.write_boot()
                with self.assertRaises(ValueError): self.admit()
                self.boot['target_identity']=copy.deepcopy(WHO); self.controller.target_identity=copy.deepcopy(WHO)
        self.assertFalse(self.s.OUTPUT.exists())

    def test_historical_authority_functions_unchanged(self):
        old=ast.parse(FIXTURE.read_text()); new=ast.parse(self.source.read_text())
        for name in ('load','cohort','collect_health','recovery'):
            def node(tree): return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(node(old)),ast.dump(node(new)),name)

    def test_original_source_admission_guard_retained(self):
        self.ad.__file__=str(self.root/'wrong-admission.py')
        with self.assertRaisesRegex(ValueError,'admission provider'): self.original_cohort(self.ad)


if __name__=='__main__': unittest.main()
