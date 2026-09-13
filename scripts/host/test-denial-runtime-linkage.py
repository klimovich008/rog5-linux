#!/usr/bin/env python3
"""Real host dynamic-loader regressions for the confined linkage probe."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]


class Linkage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.probe = cls.root / 'probe'
        subprocess.run([os.environ.get('RUSTC', 'rustc'), '--edition=2024', '-Dwarnings',
                        os.environ.get('PROBE_SOURCE', str(ROOT / 'tools/denial-runtime-linkage/probe.rs')), '-o', str(cls.probe)],
                       check=True, capture_output=True, timeout=60)
        cls.build('helper', 'int helper(void){return 1;}')
        cls.build('good', '#include <stdlib.h>\nint entry(void){abort();}\n')
        cls.build('dependent', 'extern int helper(void); int entry(void){return helper();}',
                  ['-L'+str(cls.root), '-lhelper', '-Wl,-rpath,$ORIGIN'])
        cls.build('unresolved', 'extern int absent(void);int entry(void){return absent();}')
        cls.build('cleanup', '#include <unistd.h>\nint entry(void){return 1;}\n'
                  '__attribute__((destructor)) void done(void){write(1,"FIXTURE_CLOSED\\n",15);}')

    @classmethod
    def build(cls, name, source, flags=()):
        path = cls.root / (name + '.c')
        path.write_text(source)
        subprocess.run([os.environ.get('CC', 'cc'), '-shared', '-fPIC', str(path),
                        '-o', str(cls.root / ('lib'+name+'.so')), *flags],
                       check=True, capture_output=True, timeout=30)

    def run_probe(self, name='good', symbol='entry'):
        return subprocess.run([str(self.probe), str(self.root / ('lib'+name+'.so')), symbol],
                              capture_output=True, text=True, timeout=10,
                              env={k:v for k,v in os.environ.items() if not k.startswith('LD_')})

    def test_symbol_is_resolved_but_never_called(self):
        r = self.run_probe()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('RESULT PASS_LINKAGE_ONLY', r.stdout)

    def test_missing_library_refuses(self):
        r = self.run_probe('absent')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('RESULT PASS', r.stdout)

    def test_missing_symbol_refuses(self):
        r = self.run_probe(symbol='absent')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('undefined symbol', r.stderr)

    def test_lazy_unresolved_relocation_is_refused_now(self):
        r = self.run_probe('unresolved')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('undefined symbol', r.stderr)

    def test_dependency_is_in_actual_loader_inventory(self):
        r = self.run_probe('dependent')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('OBJECT '+str(self.root / 'libhelper.so'), r.stdout)

    def test_missing_needed_dependency_refuses(self):
        helper = self.root / 'libhelper.so'
        saved = self.root / 'libhelper.saved'
        helper.rename(saved)
        try:
            r = self.run_probe('dependent')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('libhelper.so', r.stderr)
        finally:
            saved.rename(helper)

    def test_library_cleanup_precedes_success(self):
        r = self.run_probe('cleanup')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(r.stdout.index('FIXTURE_CLOSED'), r.stdout.index('RESULT PASS_LINKAGE_ONLY'))

    def test_error_path_closes_library_before_failure_receipt(self):
        r = subprocess.run([str(self.probe), str(self.root/'libcleanup.so'), 'absent'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)
        self.assertLess(r.stdout.index('FIXTURE_CLOSED'), r.stdout.index('FAIL_LINKAGE:'))

    def test_invalid_arguments_refuse_without_success(self):
        for args in [[], ['relative.so','entry'], ['/missing','bad\nsymbol'],
                     ['/missing']+['entry']*17]:
            with self.subTest(args=args):
                r = subprocess.run([str(self.probe), *args], capture_output=True, text=True, timeout=10)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('usage:', r.stderr)


class ReceiptAndRoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('linkage_checker', ROOT/'scripts/host/check-denial-runtime-linkage.py')
        cls.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)

    def test_complete_receipt_is_required(self):
        good = 'LIBRARY /a\nSYMBOL entry\nOBJECT /usr/lib/liba.so\nRESULT PASS_LINKAGE_ONLY\n'
        self.assertEqual(self.module.parse_receipt(good, '/a', ['entry']), ['/usr/lib/liba.so'])
        for value in ['RESULT PASS_LINKAGE_ONLY\n',good+'EXTRA\n',good.replace('SYMBOL entry','SYMBOL other'),
                      good.replace('OBJECT /usr/lib/liba.so','OBJECT /usr/lib/liba.so\nOBJECT /usr/lib/liba.so')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.parse_receipt(value, '/a', ['entry'])

    def test_absolute_symlink_is_resolved_inside_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'usr').mkdir();(root/'usr/lib').mkdir()
            (root/'usr/lib/object').write_bytes(b'exact');(root/'alias').symlink_to('/usr/lib/object')
            rows = [{'path':n,'type':'directory'} for n in ['usr','usr/lib']]
            rows += [{'path':'alias','type':'symlink','target':'/usr/lib/object'},
                     {'path':'usr/lib/object','type':'file','size':5,'sha256':hashlib.sha256(b'exact').hexdigest()}]
            runtime = self.module.Runtime(root,rows)
            self.assertEqual(runtime.resolve('/alias'), root/'usr/lib/object')
            (root/'usr/lib/object').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'bytes changed'):
                runtime.resolve('/alias')

    def test_changed_link_and_traversal_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);(root/'alias').symlink_to('../../outside')
            runtime = self.module.Runtime(root,[{'path':'alias','type':'symlink','target':'../../outside'}])
            with self.assertRaisesRegex(ValueError,'escapes root'):
                runtime.resolve('/alias')
            (root/'alias').unlink();(root/'alias').symlink_to('/different')
            with self.assertRaisesRegex(ValueError,'link changed'):
                runtime.resolve('/alias')

    def test_duplicate_manifest_paths_refuse(self):
        with self.assertRaisesRegex(ValueError,'duplicate runtime'):
            self.module.Runtime(Path('/not-accessed'),[{'path':'a'},{'path':'a'}])


class BoundedCommand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('bounded_checker', ROOT/'scripts/host/check-denial-runtime-linkage.py')
        cls.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)

    def exercise(self, interruption=None, stop_fails=False, exit_status=0, wait_fails=False, deadline=False):
        # Model only the service-manager boundary. Client and service are real,
        # separate process groups: killing the client cannot kill the service.
        popen = subprocess.Popen
        service = client = None
        stop_calls = []
        clock = self.module.time.monotonic
        launched = [False]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            def launch(command, **kwargs):
                nonlocal service, client
                service = popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
                client = popen([sys.executable, '-c', f'print("partial probe evidence", flush=True); raise SystemExit({exit_status})'], **kwargs)
                if interruption is not None:
                    poll = client.poll
                    pending = [True]
                    def interrupted_poll():
                        if pending:
                            pending.clear()
                            raise interruption
                        return poll()
                    client.poll = interrupted_poll
                if wait_fails:
                    wait = client.wait
                    pending_wait = [True]
                    def failed_wait(*args, **kwargs):
                        if pending_wait:
                            pending_wait.clear()
                            raise subprocess.TimeoutExpired('fixture client', 10) if wait_fails is True else wait_fails
                        return wait(*args, **kwargs)
                    client.wait = failed_wait
                launched[0] = True
                return client
            def control(command, **kwargs):
                if command[:3] == ['systemctl', '--user', 'stop']:
                    stop_calls.append(command[3])
                    if not stop_fails:
                        os.killpg(service.pid, signal.SIGKILL); service.wait(timeout=3)
                    return subprocess.CompletedProcess(command, 1 if stop_fails else 0, b'', b'')
                self.assertEqual(command[:3], ['systemctl', '--user', 'is-active'])
                state = 'active' if service.poll() is None else 'inactive'
                return subprocess.CompletedProcess(command, 0 if state=='active' else 3, state+'\n', '')
            try:
                with mock.patch.object(self.module.subprocess, 'Popen', side_effect=launch), mock.patch.object(self.module.subprocess, 'run', side_effect=control), mock.patch.object(self.module.time, 'monotonic', side_effect=lambda: clock()+(46 if deadline and launched[0] else 0)):
                    expected_error = interruption or (wait_fails if isinstance(wait_fails, BaseException) else None)
                    if expected_error is not None:
                        with self.assertRaises(type(expected_error)) as caught:
                            self.module.bounded(['systemd-run','fixture'], output, 'test')
                        self.assertIs(caught.exception, expected_error)
                        self.assertEqual(len(stop_calls), 1)
                        if stop_fails:
                            self.assertIn('service shutdown', '\n'.join(caught.exception.__notes__))
                        else:
                            self.assertIsNotNone(service.poll(), 'service survived client interruption')
                        return
                    result = self.module.bounded(['systemd-run','fixture'], output, 'test')
                self.assertEqual(len(stop_calls), 1)
                if not deadline:
                    self.assertEqual(result['exit_status'], exit_status)
                    self.assertIn('partial probe evidence', (output/'test.log').read_text())
                else:
                    self.assertIn('log limit or deadline', result['failure'])
                    self.assertIn('service shutdown', result['failure'])
                if stop_fails or wait_fails:
                    self.assertIn('failure', result)
                else:
                    self.assertIsNotNone(service.poll())
                    self.assertNotIn('failure', result)
            finally:
                for process in (client, service):
                    if process is not None:
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        process.wait(timeout=3)

    def test_interruption_stops_service_and_preserves_exception(self):
        for error in (KeyboardInterrupt(), OSError('observation failed')):
            with self.subTest(error=type(error).__name__):
                self.exercise(interruption=error)

    def test_success_confirms_service_cleanup(self):
        self.exercise()

    def test_nonzero_exit_retains_evidence_and_cleans_service(self):
        self.exercise(exit_status=42)

    def test_failed_service_cleanup_cannot_pass(self):
        self.exercise(stop_fails=True)

    def test_deadline_and_cleanup_failure_are_both_retained(self):
        self.exercise(stop_fails=True, deadline=True)

    def test_client_wait_failure_still_stops_service(self):
        self.exercise(wait_fails=True)

    def test_cleanup_error_is_attached_to_original_interruption(self):
        self.exercise(interruption=KeyboardInterrupt(), stop_fails=True)

    def test_interruption_during_client_wait_still_stops_service(self):
        self.exercise(wait_fails=KeyboardInterrupt())

    def test_main_retains_original_error_and_cleanup_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for kind in (OSError, KeyboardInterrupt):
                with self.subTest(kind=kind.__name__):
                    output = base/kind.__name__
                    args = ['checker', '--output', str(output), '--tree-sha256', '0'*64]
                    for name in ('root','tree','bundle','native','probe'):
                        args += ['--'+name, str(base)]
                    error = kind('original observation failure')
                    error.add_note('Probe cleanup: service shutdown could not be confirmed')
                    with mock.patch.object(sys, 'argv', args), mock.patch.object(self.module.shutil, 'which', return_value='/fixture/tool'), mock.patch.object(self.module, 'identity', side_effect=error):
                        code = self.module.main()
                    report = json.loads((output/'result.json').read_text())
                    self.assertEqual(code, 130 if kind is KeyboardInterrupt else 1)
                    self.assertEqual(report['error'], 'original observation failure')
                    self.assertEqual(report['error_notes'], error.__notes__)
                    self.assertEqual(report['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
