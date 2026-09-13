#!/usr/bin/env python3
"""Exercise the real manual runner's process ownership without containers/VMs."""
import os
import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

RUNNER = Path(__file__).with_name('test-qemu-logind.py')


def live(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1][0] not in 'ZX'
    except FileNotFoundError:
        return False


class Ownership(unittest.TestCase):
    def scenario(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'pid'
            inner = ('import os,time;from pathlib import Path;'
                     f'Path({str(marker)!r}).write_text(str(os.getpid()));time.sleep(30)')
            if mode == 'completed':
                inner = ('import subprocess,sys,time;from pathlib import Path;'
                         f'subprocess.Popen([sys.executable,"-c",{inner!r}]);'
                         f'\nwhile not Path({str(marker)!r}).exists():time.sleep(0.01)')
            driver = f'''
import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('runner',{str(RUNNER)!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if hasattr(m,'install_handlers'):m.install_handlers()
m.execute([sys.executable,'-c',{inner!r}],Path({str(root/'child.log')!r}),{0.3 if mode == 'timeout' else 5},[])
'''
            child_pid = None
            with (root/'driver.log').open('wb') as log:
                process = subprocess.Popen([sys.executable, '-c', driver], stdout=log, stderr=log)
                try:
                    deadline = time.monotonic()+3
                    while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
                        time.sleep(0.01)
                    self.assertTrue(marker.exists(), (root/'driver.log').read_text())
                    child_pid = int(marker.read_text())
                    if mode == 'signal':
                        process.send_signal(signal.SIGTERM)
                    process.wait(timeout=5)
                    if mode == 'completed':
                        self.assertEqual(process.returncode, 0)
                    else:
                        self.assertNotEqual(process.returncode, 0)
                    deadline = time.monotonic()+0.5
                    while live(child_pid) and time.monotonic()<deadline:
                        time.sleep(0.01)
                    self.assertFalse(live(child_pid), 'runner left its command running')
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                    if child_pid is not None:
                        try: os.killpg(child_pid, signal.SIGKILL)
                        except ProcessLookupError: pass

    def test_sigterm_reaps_command(self):
        self.scenario('signal')

    def test_deadline_reaps_command(self):
        self.scenario('timeout')

    def test_completed_command_reaps_background_descendant(self):
        self.scenario('completed')


class Cleanup(unittest.TestCase):
    def test_actual_cleanup_distinguishes_absence_presence_and_query_error(self):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-session.sh'
        harness = '''
source "$1"
SESSION_ROWS=$2; SCOPE_ROWS=$3; SESSION_RC=$4; SCOPE_RC=$5
timeout(){ shift 3; "$@"; }
loginctl(){ [[ $1 == list-sessions ]] || return 99; printf '%s\n' "$SESSION_ROWS"; return "$SESSION_RC"; }
systemctl(){ [[ $1 == list-units ]] || return 99; printf '%s\n' "$SCOPE_ROWS"; return "$SCOPE_RC"; }
logind_cleanup_state "$6"
'''
        cases = [
            ('', '', 0, 0, 'c1', 0),
            ('c2 1000 mobile seat0 tty2', 'session-c2.scope loaded active running', 0, 0, 'c1', 0),
            ('c1 1000 mobile seat0 tty1 closing', '', 0, 0, 'c1', 1),
            ('', 'session-c1.scope loaded active running', 0, 0, 'c1', 1),
            ('', 'session-c1.scope loaded inactive dead', 0, 0, 'c1', 1),
            ('', '', 1, 0, 'c1', 2),
            ('', '', 0, 1, 'c1', 2),
            ('', '', 124, 0, 'c1', 2),
            ('', '', 0, 124, 'c1', 2),
            ('', '', 0, 0, '../scope', 2),
        ]
        for sessions, scopes, session_rc, scope_rc, sid, expected in cases:
            with self.subTest(sessions=sessions, scopes=scopes, session_rc=session_rc, scope_rc=scope_rc, sid=sid):
                result = subprocess.run(['bash', '-c', harness, 'fixture', str(script), sessions, scopes,
                                         str(session_rc), str(scope_rc), sid], capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                if session_rc:
                    self.assertIn(f'query=loginctl status={session_rc}', result.stderr)
                elif scope_rc:
                    self.assertIn(f'query=systemctl status={scope_rc}', result.stderr)


    def test_early_parser_check_uses_actual_cleanup_query_arguments(self):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-session.sh'
        harness = r'''source "$1"
timeout(){ shift 3; "$@"; }
loginctl(){ printf '%s\n' "$*"; }
systemctl(){ printf '%s\n' "$*"; }
logind_query_sessions
logind_query_sessions --help
logind_query_scopes
logind_query_scopes --help
'''
        result = subprocess.run(['bash', '-c', harness, 'fixture', str(script)],
                                capture_output=True, text=True, timeout=3, check=True)
        session, session_help, scope, scope_help = result.stdout.splitlines()
        self.assertEqual(session_help, session+' --help')
        self.assertEqual(scope_help, scope+' --help')
        # Exact packaged ARM64 parser was exercised separately, not modeled here.
        self.assertNotIn('--no-footer', session.split())

    def test_tty_ownership_requires_successful_enumeration(self):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-session.sh'
        harness = r'''source "$1"
ROWS=$2; RC=$3
timeout(){ shift 3; "$@"; }
ps(){ [[ "$*" == '-eo tty=,pid=' ]] || return 99; printf '%s\n' "$ROWS"; return "$RC"; }
logind_tty_unowned
'''
        for rows, rc, expected in [('', 0, 0), ('? 1\ntty2 32', 0, 0), ('tty1 33', 0, 1), ('', 42, 2), ('', 124, 2)]:
            with self.subTest(rows=rows, rc=rc):
                result = subprocess.run(['bash', '-c', harness, 'fixture', str(script), rows, str(rc)],
                                        capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)


class Archive(unittest.TestCase):
    def test_vm_panic_cannot_be_promoted_by_earlier_success(self):
        spec = importlib.util.spec_from_file_location('logind_runner', RUNNER)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.require_vm_poweroff('PASS session\nreboot: Power down\n')
        for serial in ['PASS session', 'PASS session\nKernel panic\n', 'Kernel panic\nreboot: Power down']:
            with self.subTest(serial=serial), self.assertRaises(RuntimeError):
                module.require_vm_poweroff(serial)

    def test_actual_inventory_and_unsafe_member_boundaries(self):
        spec = importlib.util.spec_from_file_location('logind_runner', RUNNER)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        names = ['usr/bin/deniald', 'usr/bin/denialctl', 'usr/bin/denial-session',
                 'usr/bin/denial-mobile-session', 'usr/lib/systemd/user/denial-session.target',
                 'usr/lib/denial/flutter/lib/libapp.so', 'usr/lib/denial/flutter/lib/libflutter_engine.so']
        for mode in ['valid', 'wrong_hash', 'wrong_member', 'symlink', 'traversal', 'missing']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); archive = root/'session.tar.gz'; receipt = root/'receipt.json'
                rows = [{'name': name, 'size': 2, 'mode': 0o644, 'sha256': hashlib.sha256(b'ok').hexdigest()} for name in names]
                with tarfile.open(archive, 'w:gz') as stream:
                    directory_member = tarfile.TarInfo('usr'); directory_member.type = tarfile.DIRTYPE; directory_member.mode = 0o755
                    stream.addfile(directory_member)
                    for i, name in enumerate(names + ['usr/share/rog5-denial/payload.json']):
                        if mode == 'missing' and i == 0: continue
                        member = tarfile.TarInfo('../escape' if mode == 'traversal' and i == 0 else name)
                        member.size = 2; member.mode = 0o644
                        if mode == 'symlink' and i == 0:
                            member.type = tarfile.SYMTYPE; member.linkname = '/etc/shadow'; member.size = 0
                            stream.addfile(member)
                        else:
                            stream.addfile(member, io.BytesIO(b'no' if mode == 'wrong_member' and i == 0 else b'ok'))
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                receipt.write_text(json.dumps({'status': 'PREPARED_NOT_INSTALLED', 'authority': 'none',
                    'sha256': '0'*64 if mode == 'wrong_hash' else digest, 'size': archive.stat().st_size,
                    'metadata': {'files': rows}}))
                if mode == 'valid': module.validate_session_archive(archive, receipt)
                else:
                    with self.assertRaises(ValueError): module.validate_session_archive(archive, receipt)


if __name__ == '__main__':
    unittest.main()
