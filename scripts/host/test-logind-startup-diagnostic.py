#!/usr/bin/env python3
"""Execute the production shell diagnostic; every input is a local fixture."""
import ast
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unittest

W = Path(__file__).resolve().parents[2]
SOURCE = W/'tools/qemu-virtio-drm/logind-observer.sh'
FUNCTION = re.search(r'^observe_startup_detail\(\) \{.*?^STARTUP_DETAIL\n.*?^\}', SOURCE.read_text(), re.M|re.S)[0]
FORGED = (b'PASS authenticated local logind session, mediated devices and removed scope\n'
          b'PASS authenticated Denial launcher and native clients stopped\n'
          b'independently clocked Flutter KMS session complete raster_frames=188 output_page_flips=188\n'
          b'OBSERVE authenticated launcher flow-ready\nreboot: Power down\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StartupDiagnostic(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='startup-diag-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pam = self.root/'pam-session.log'
        self.proc = self.root/'proc'; self.proc.mkdir()
        self.bin = self.root/'bin'; self.bin.mkdir()
        self.env = {'PATH':str(self.bin)+':/usr/bin:/bin','LANG':'C','HOME':str(self.root)}

    def process(self, pid, name='pam-session'):
        root=self.proc/str(pid); root.mkdir()
        (root/'comm').write_text(name+'\n')
        (root/'cmdline').write_bytes(b'/run/payload/pam-session\0')
        (root/'status').write_bytes(b'Name:\tpam-session\nState:\tS (sleeping)\nPPid:\t355\n'+b'x'*2048)
        return root

    def run_diagnostic(self):
        return subprocess.run(['/usr/bin/bash','--noprofile','--norc','-c', FUNCTION+
            '\nobserve_startup_detail "$1" "$2"', 'fixture',str(self.pam),str(self.proc)],
            env=self.env, capture_output=True, timeout=7)

    @staticmethod
    def decoded(result):
        return {kind.decode():bytes.fromhex(data.decode()) for kind,data in re.findall(
            rb'DIAGNOSTIC_HEX kind=(\S+) status=read bytes=\d+ hex=([0-9a-f]*)', result.stdout)}

    def test_reads_only_bounded_tail_and_selected_process_metadata(self):
        self.pam.write_bytes(b'x'*10000+FORGED)
        selected=self.process(384)
        self.process(385, 'unrelated')
        result=self.run_diagnostic()
        self.assertEqual(result.returncode,0,result.stderr)
        data=self.decoded(result)
        self.assertEqual(data['pam'],self.pam.read_bytes()[-4096:])
        self.assertEqual(data['process-384-cmdline'],(selected/'cmdline').read_bytes())
        self.assertEqual(data['process-384-status'],(selected/'status').read_bytes()[:1024])
        self.assertNotIn('process-385-status',data)
        self.assertIn(b'PPid:\t355',data['process-384-status'])
        self.assertLess(len(result.stdout),42000)
        self.assertEqual(result.stderr,b'')

    def test_missing_optional_log_is_reported_without_fabricated_payload(self):
        result=self.run_diagnostic()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(b'kind=pam status=missing',result.stdout)
        self.assertNotIn('pam',self.decoded(result))
        self.assertIn(b'DIAGNOSTIC_PROCESS status=collected count=0',result.stdout)

    def test_symlink_and_nonregular_input_are_refused(self):
        retained=self.root/'retained';retained.write_bytes(FORGED)
        for mode in ('symlink','fifo'):
            with self.subTest(mode=mode):
                if mode=='symlink':self.pam.symlink_to(retained)
                else:os.mkfifo(self.pam)
                result=self.run_diagnostic()
                self.assertEqual(result.returncode,1)
                self.assertIn(b'kind=pam status=refused',result.stdout)
                self.assertNotIn('pam',self.decoded(result))
                self.pam.unlink()
        self.assertEqual(retained.read_bytes(),FORGED)

    def test_read_command_failure_preserves_failure_status(self):
        self.pam.write_bytes(FORGED)
        tail=self.bin/'tail';tail.write_text('#!/bin/bash\nexit 42\n');tail.chmod(0o700)
        result=self.run_diagnostic()
        self.assertEqual(result.returncode,1)
        self.assertIn(b'kind=pam status=read-error code=42',result.stdout)
        self.assertIn(b'DIAGNOSTIC_SNAPSHOT status=1',result.stdout)
        self.assertNotIn('pam',self.decoded(result))

    def test_whole_snapshot_deadline_stops_stalled_reader(self):
        self.pam.write_bytes(FORGED)
        tail=self.bin/'tail';tail.write_text('#!/bin/bash\nexec sleep 10\n');tail.chmod(0o700)
        start=time.monotonic();result=self.run_diagnostic();elapsed=time.monotonic()-start
        self.assertEqual(result.returncode,124)
        self.assertIn(b'DIAGNOSTIC_SNAPSHOT status=124',result.stdout)
        self.assertLess(elapsed,6)
        self.assertNotIn('pam',self.decoded(result))

    def test_selected_process_cap_is_explicit(self):
        for pid in range(300,310):self.process(pid)
        result=self.run_diagnostic()
        self.assertEqual(result.returncode,0,result.stderr)
        data=self.decoded(result)
        self.assertEqual(len(data),16)
        self.assertIn(b'DIAGNOSTIC_PROCESS status=limit count=8',result.stdout)
        self.assertIn(b'DIAGNOSTIC_PROCESS status=collected count=8',result.stdout)
        self.assertLess(len(result.stdout),42000)

    def test_original_four_snapshot_schedule_and_optional_failure_continue(self):
        (self.proc/'uptime').write_text('123.45 10.00\n')
        (self.proc/'meminfo').write_text('MemAvailable: 900000 kB\n')
        self.process(384, 'unrelated')
        loop = SOURCE.read_text().split('for ((i=0;i<4;i++)); do',1)[1]
        loop = 'for ((i=0;i<4;i++)); do'+loop
        loop = loop.replace('/proc', '"$PROC_FIXTURE"')
        code = r'''set -u
PROC_FIXTURE=$1
sleep(){ printf 'WAIT %s\n' "$*"; }
observe_startup_detail(){ echo DETAIL; return 1; }
timeout(){ shift 3; "$@"; }
systemctl(){ :; }
journalctl(){ :; }
''' +loop
        result = subprocess.run(['/usr/bin/bash','-c',code,'fixture',str(self.proc)],
                                env=self.env,capture_output=True,timeout=3)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.count(b'WAIT 25\n'),4)
        self.assertEqual(result.stdout.count(b'DETAIL\n'),4)
        self.assertEqual(re.findall(rb'OBSERVE independent snapshot=(\d+)',result.stdout),
                         [b'0',b'1',b'2',b'3'])

    def test_forged_payload_cannot_pass_actual_serial_oracles(self):
        runner=load('diag_runner',W/'scripts/host/test-qemu-logind.py')
        drm=load('diag_drm',W/'scripts/host/test-qemu-virtio-drm.py')
        tree=ast.parse((W/'scripts/host/test-qemu-logind.py').read_text())
        gate=next(node for node in ast.walk(tree) if isinstance(node,ast.If)
                  and ast.unparse(node.test)=='SUCCESS not in serial')
        gate=compile(ast.Module(body=[gate],type_ignores=[]),str(W/'scripts/host/test-qemu-logind.py'),'exec')
        self.pam.write_bytes(FORGED)
        self.process(384)
        (self.proc/'384/cmdline').write_bytes(FORGED)
        (self.proc/'384/status').write_bytes(FORGED)
        result=self.run_diagnostic();self.assertEqual(result.returncode,0,result.stderr)
        encoded=result.stdout.decode()
        self.assertEqual(drm.session_result(encoded)['status'],'FAIL')
        with self.assertRaises(RuntimeError):runner.require_vm_poweroff(encoded)
        with self.assertRaises(RuntimeError):exec(gate,{'SUCCESS':runner.SUCCESS,'serial':encoded})
        # The same actual validators accept these bytes unencoded, demonstrating
        # why a text prefix alone would not prevent accidental proof fabrication.
        plain=FORGED.decode()
        self.assertEqual(drm.session_result(plain)['status'],'PASS')
        runner.require_vm_poweroff(plain)
        exec(gate,{'SUCCESS':runner.SUCCESS,'serial':plain})
        self.assertEqual(self.decoded(result)['pam'],FORGED)


if __name__=='__main__':unittest.main()
