#!/usr/bin/env python3
"""Execute real timeout/disconnect groups; no hardware or repository suites."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('repository-test-report.py')
spec = importlib.util.spec_from_file_location('report', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Report(unittest.TestCase):
    def test_repeated_interrupt_cannot_abort_process_group_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile=Path(tmp)/'child.pid'
            code='''
import importlib.util, json, os, pathlib, signal, sys, tempfile, threading, time
s=importlib.util.spec_from_file_location('report',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
pidfile=pathlib.Path(sys.argv[2])
def interrupt_twice():
    until=time.monotonic()+2
    while not pidfile.exists():
        if time.monotonic()>until: raise RuntimeError('test child never started')
        time.sleep(.001)
    os.kill(os.getpid(),signal.SIGTERM)
    time.sleep(.01)
    os.kill(os.getpid(),signal.SIGTERM)
t=threading.Thread(target=interrupt_twice,daemon=True);t.start()
child='import os,pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path('+repr(str(pidfile))+').write_text(str(os.getpid())); time.sleep(60)'
with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
    print(json.dumps(m.execute([sys.executable,'-c',child],3,out,err)),flush=True)
t.join(timeout=1)
'''
            result=subprocess.run([sys.executable,'-c',code,str(SOURCE),str(pidfile)],
                                  capture_output=True,text=True,timeout=5)
            pid=int(pidfile.read_text())
            alive=False
            try:
                stat=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
                alive=stat[0]!='Z'
                if alive:os.killpg(pid,signal.SIGKILL)
            except FileNotFoundError:
                pass
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(alive,'owned child survived interrupted cleanup')
            self.assertEqual(json.loads(result.stdout)[0],'FAIL')

    def result_fixture(self, body, mandatory=True, interpreter='python3', optional=None, prerequisites=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);(root/'configs').mkdir();result=root/'result';result.mkdir()
        row=dict(path='one.py',interpreter=interpreter,tiers=['ci'],mandatory=mandatory,
                 deadline_seconds=1,prerequisites=prerequisites or [],resource_class='shared-state',
                 exclusivity_group='repository',python_optimized=False,exact_source=False,required_inputs=[])
        if optional is not None:row['optional_subchecks']=optional
        (root/'configs/repository-tests.json').write_text(json.dumps(dict(tests=[row])))
        (root/'one.py').write_text(body)
        self.last_result_directory=result
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code=m.run(root,result,'one.py')
        return code,json.loads(next(result.glob('*.json')).read_text())

    def test_rust_prerequisite_uses_the_compiler_selected_by_the_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / 'rustc'
            selected = root / 'custom compiler'
            for path in (default, selected):
                path.write_text('#!' + sys.executable + '\nprint("fixture compiler")\n')
                path.chmod(0o700)
            body = ('import os, subprocess\n'
                    'assert subprocess.check_output([os.environ.get("RUSTC", "rustc"), '
                    '"--version"], text=True).strip() == "fixture compiler"\n')
            for name, compiler, search, expected in (
                ('explicit', str(selected), '', 'PASS'),
                ('missing explicit', str(root / 'missing'), str(root), 'BLOCKED'),
                ('empty explicit', '', str(root), 'BLOCKED'),
                ('default', None, str(root), 'PASS'),
            ):
                with self.subTest(name=name), patch.dict(os.environ, {'PATH': search}):
                    if compiler is None:
                        os.environ.pop('RUSTC', None)
                    else:
                        os.environ['RUSTC'] = compiler
                    code, result = self.result_fixture(body, interpreter=sys.executable,
                                                       prerequisites=['rustc'])
                    self.assertEqual(result['status'], expected)
                    self.assertEqual(code, 0 if expected == 'PASS' else 1)

    def declaration(self, message='SKIP retained fixture', kind='line', scope='subcheck'):
        return dict(id='retained-fixture',kind=kind,message=message,scope=scope,
                    reason='Retained historical artifact is not part of source contract.',
                    inputs=['build/retained-fixture'],test_ids=['Fixture.test_old'] if kind=='unittest' else [])

    def test_declared_optional_subcheck_preserves_executed_contract_pass(self):
        code,result=self.result_fixture('print("PASS source contract"); print("SKIP retained fixture")',
                                        optional=[self.declaration()])
        self.assertEqual((code,result['status']),(0,'PASS'))
        self.assertEqual(result['subchecks'][0]['status'],'SKIPPED')
        self.assertTrue(result['subchecks'][0]['declared_optional'])

    def test_unknown_skip_stays_fatal_even_for_optional_suite(self):
        code,result=self.result_fixture('print("SKIP unknown component")',mandatory=False,
                                        optional=[self.declaration()])
        self.assertEqual(code,1)
        self.assertEqual(result['status'],'SKIPPED')

    def test_declared_whole_historical_suite_is_skipped_not_passed(self):
        code,result=self.result_fixture('print("SKIP retained fixture")',mandatory=False,
                                        optional=[self.declaration(scope='whole_test')])
        self.assertEqual((code,result['status']),(0,'SKIPPED'))

    def test_unittest_skip_needs_exact_reason_and_case(self):
        body=('import unittest\nclass Fixture(unittest.TestCase):\n'
              ' def test_old(self): self.skipTest("retained old artifact")\n'
              ' def test_current(self): self.assertEqual(1,1)\n'
              'if __name__=="__main__": unittest.main()\n')
        declaration=self.declaration('retained old artifact',kind='unittest')
        code,result=self.result_fixture(body,optional=[declaration])
        self.assertEqual((code,result['status']),(0,'PASS'))
        self.assertEqual(result['subchecks'][0]['test_id'],'Fixture.test_old')
        declaration['test_ids']=['Fixture.test_different']
        code,result=self.result_fixture(body,optional=[declaration])
        self.assertEqual((code,result['status']),(1,'SKIPPED'))

    def test_quiet_unittest_skip_summary_never_passes_unnoticed(self):
        code,result=self.result_fixture('print("OK (skipped=1)")')
        self.assertEqual((code,result['status']),(1,'SKIPPED'))

    def test_optional_declaration_does_not_hide_process_failure(self):
        code,result=self.result_fixture('print("SKIP retained fixture"); raise SystemExit(42)',mandatory=False,
                                        optional=[self.declaration()])
        self.assertEqual((code,result['status']),(1,'FAIL'))

    def test_all_unittest_cases_skipped_cannot_claim_contract_pass(self):
        body=('import unittest\nclass Fixture(unittest.TestCase):\n'
              ' def test_old(self): self.skipTest("retained old artifact")\n'
              'if __name__=="__main__": unittest.main()\n')
        declaration=self.declaration('retained old artifact',kind='unittest')
        code,result=self.result_fixture(body,optional=[declaration])
        self.assertEqual((code,result['status']),(1,'SKIPPED'))

    def test_summary_retains_skipped_subsection_beside_passed_contract(self):
        code,result=self.result_fixture('print("PASS source contract"); print("SKIP retained fixture")',
                                        optional=[self.declaration()])
        directory=self.last_result_directory
        (directory/'selection.json').write_text(json.dumps(dict(tier='ci',selected=['one.py'])))
        with contextlib.redirect_stdout(io.StringIO()):m.summarize(directory.parent,directory)
        summary=json.loads((directory/'summary.json').read_text())
        self.assertEqual(summary['counts']['PASS'],1)
        self.assertEqual(summary['subcheck_counts']['SKIPPED'],1)
        xml=(directory/'summary.xml').read_text()
        self.assertIn('tests="2"',xml)
        self.assertIn('skipped="1"',xml)
        self.assertIn('SKIP retained fixture',xml)

    def test_failure_cannot_be_hidden_by_optional_skip_output(self):
        code,result=self.result_fixture('print("SKIP optional component"); raise SystemExit(42)', mandatory=False)
        self.assertEqual(code,1)
        self.assertEqual(result['status'],'FAIL')

    def test_mandatory_skip_cannot_pass(self):
        code,result=self.result_fixture('print("SKIP unavailable component")')
        self.assertEqual((code,result['status']),(1,'SKIPPED'))

    def test_missing_interpreter_gets_blocked_receipt(self):
        code,result=self.result_fixture('pass', interpreter='rog5-missing-fixture-interpreter')
        self.assertEqual((code,result['status']),(1,'BLOCKED'))

    def execute(self, code, limit=2):
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            return m.execute([sys.executable, '-c', code], limit, out, err)

    def test_success_and_failure(self):
        self.assertEqual(self.execute('pass')[0], 'PASS')
        self.assertEqual(self.execute('raise SystemExit(42)')[0], 'FAIL')

    def test_deadline_kills_process_group(self):
        started = time.monotonic()
        status, reason, duration = self.execute('import subprocess,time; subprocess.Popen(["sleep","60"]); time.sleep(60)', .1)
        self.assertEqual((status, reason), ('FAIL', 'deadline exceeded'))
        self.assertLess(time.monotonic()-started, 2)

    def test_completed_parent_cannot_leave_background_child(self):
        status, reason, _ = self.execute('import subprocess; subprocess.Popen(["sleep","60"])')
        self.assertEqual((status, reason), ('FAIL', 'background descendants'))

    def test_report_lists_selected_not_reached_and_not_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'configs').mkdir(); result=root/'result'; result.mkdir()
            row=dict(path='one.py',interpreter='python3',tiers=['ci'],mandatory=True,
                     deadline_seconds=1,prerequisites=[],resource_class='shared-state',
                     exclusivity_group='repository',python_optimized=False,exact_source=False,required_inputs=[])
            second=dict(row,path='two.py')
            (root/'configs/repository-tests.json').write_text(json.dumps(dict(tests=[row,second])))
            (result/'selection.json').write_text(json.dumps(dict(tier='ci',selected=['one.py'])))
            self.assertEqual(m.summarize(root,result),1)
            summary=json.loads((result/'summary.json').read_text())
            self.assertEqual(summary['counts']['BLOCKED'],1)
            self.assertEqual(summary['counts']['NOT_SELECTED'],1)
            self.assertIn('<error', (result/'summary.xml').read_text())
            process=subprocess.run([sys.executable,str(SOURCE),'summary',str(root),str(result)],capture_output=True,text=True)
            self.assertEqual(process.returncode,1)

    def test_actual_shell_cleanup_preserves_summary_failure(self):
        runner=SOURCE.with_name('test-repository-linux.sh').read_text()
        begin=runner.index('cleanup_parallel_tests() {\n')
        body=runner[begin:runner.index('\n}\n',begin)+3]
        with tempfile.TemporaryDirectory() as tmp:
            code='set -u\nrepo=$1\nparallel_root=$1/scratch\nmkdir "$parallel_root"\nreport_root=$1/report\ntest_tmp_root=\nparallel_pids=()\npython3() { return 1; }\n'+body+'\ncleanup_parallel_tests\n'
            process=subprocess.run(['bash','-c',code,'fixture',tmp],capture_output=True,text=True)
            self.assertEqual(process.returncode,1,process.stderr)
            self.assertFalse((Path(tmp)/'scratch').exists())

    def test_missing_prerequisite_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'configs').mkdir(); result=root/'result'; result.mkdir()
            row=dict(path='one.py',interpreter='python3',tiers=['ci'],mandatory=True,
                     deadline_seconds=1,prerequisites=['rog5-missing-fixture-tool'],resource_class='shared-state',
                     exclusivity_group='repository',python_optimized=False,exact_source=False,required_inputs=[])
            (root/'configs/repository-tests.json').write_text(json.dumps(dict(tests=[row])))
            self.assertEqual(m.run(root,result,'one.py'),1)
            self.assertEqual(json.loads(next(result.glob('*.json')).read_text())['status'],'BLOCKED')

if __name__=='__main__': unittest.main(verbosity=2)
