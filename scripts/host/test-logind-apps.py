#!/usr/bin/env python3
"""Guest launcher supervision with real FIFOs/processes and an inert CLI seam."""
import os
from pathlib import Path
import pty
import re
import select
import shlex
import signal
import subprocess
import tempfile
import threading
import time
import tty
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools/qemu-virtio-drm'
NAMES = ('prepare_foot_close', 'launch_foot', 'close_foot_normally', 'remove_foot_close',
         'reap_owned', 'require_running', 'stop_owned_group')
MAIN = (TOOLS / 'logind-denial.sh').read_text()
LIFECYCLE = '\n'.join(re.search(r'^' + name + r'\(\) \{.*?^\}', MAIN, re.M | re.S).group()
                      for name in NAMES)


class AuthenticatedApps(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-apps-test-')
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'; self.home.mkdir()
        self.state = self.home / 'launcher-apps'
        self.bin = self.root / 'bin'; self.bin.mkdir()
        self.desktops = self.root / 'desktops'; self.desktops.mkdir()
        self.text = self.root / 'rog5-text-probe.txt'
        self.token = 'ROG5_APPS_DONE_' + 'a' * 32
        (self.root / 'token').write_text(self.token + '\n')
        for app, filename in [('foot', 'foot.desktop'), ('mousepad', 'org.xfce.mousepad.desktop')]:
            (self.desktops / filename).write_text(
                f'[Desktop Entry]\nName={app}\nExec={app}\n[Desktop Action other]\nExec=retained\n')
            os.mkfifo(self.home / (app + '.pipe'), 0o600)
        self.command('foot', 'exec "$@"\n')
        self.command('mousepad', '''[[ $GDK_BACKEND == wayland && $WAYLAND_DEBUG == client ]] || exit 42
trap 'exit 0' TERM
echo 'fixture Mousepad protocol'
while :; do sleep .1; done
''')
        self.writer = self.bin / 'writer'
        self.writer.write_text('''#!/usr/bin/env python3
import os,sys
if sys.argv[1] == 'record': os.write(1,(sys.argv[2]+'\\n').encode())
else:
 for line in sys.stdin.buffer:
  record=sys.argv[2].encode()+b' '+line
  if len(record)>4096: sys.exit(42)
  os.write(1,record)
''')
        self.writer.chmod(0o700)
        self.prefix = ('set -euo pipefail\n' + '\n'.join('source ' + shlex.quote(str(TOOLS / file))
                       for file in ('launcher-apps.sh', 'launcher-evidence.sh', 'logind-apps.sh'))
                       + '\n' + LIFECYCLE + '\nlauncher_guest_guard() { :; }\n')
        self.wrapper = self.root / 'tile-wrapper'
        self.wrapper.write_text('#!/bin/bash\n' + self.prefix
            + '[[ $1 == launch ]]; logind_apps_supervise "$2" "$HOME/launcher-apps" "$TEST_BIN"\n')
        self.wrapper.chmod(0o700)
        self.master, self.slave = pty.openpty()
        tty.setraw(self.slave)
        self.sink = os.ttyname(self.slave)
        self.env = {**os.environ, 'HOME': str(self.home), 'TEST_BIN': str(self.bin),
                    'PATH': str(self.bin) + ':' + os.environ['PATH'], 'WAYLAND_DISPLAY': 'wayland-fixture'}
        self.processes = []
        self.events = bytearray()
        self.stop = threading.Event()
        self.reader = threading.Thread(target=self.drain, daemon=True)
        self.reader.start()
        self.addCleanup(self.cleanup)

    def command(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/bash\nset -eu\n' + body)
        path.chmod(0o700)

    def drain(self):
        while not self.stop.is_set():
            if select.select([self.master], [], [], .1)[0]:
                try: self.events.extend(os.read(self.master, 8192))
                except OSError: break

    def cleanup(self):
        for process in self.processes:
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
        for process in self.processes:
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=2)
            if process.stdout: process.stdout.close()
            if process.stderr: process.stderr.close()
        self.stop.set(); self.reader.join(timeout=1)
        os.close(self.master); os.close(self.slave)
        self.temp.cleanup()

    def spawn(self, command):
        child = subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        self.processes.append(child)
        return child

    def controller(self, prepare_only=False):
        code = self.prefix + r'''
readers=(); launcher=''; logind_apps_evidence_owned=0
dbus-update-activation-environment(){ [[ $* == '--systemd XDG_DATA_HOME' ]]; }
systemctl(){ [[ $* == '--user show-environment' ]]; printf 'XDG_DATA_HOME=%s\n' "$XDG_DATA_HOME"; }
cleanup_fixture(){
 rc=$?; trap - EXIT
 cleanup_authenticated_apps || { [[ $rc != 0 ]] || rc=1; }
 stop_owned_group cleanup launcher || { [[ $rc != 0 ]] || rc=1; }
 for pid in "${readers[@]}"; do kill "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; done
 readers=()
 finish_authenticated_apps || { [[ $rc != 0 ]] || rc=1; }
 exit "$rc"
}
trap cleanup_fixture EXIT
trap 'exit 130' INT
prepare_authenticated_apps "$1" "$2" "$3" "$4" "$5" "$6" "$7"
'''
        if not prepare_only:
            code += r'''
sleep 60 & launcher=$!
run_authenticated_apps
stop_owned_group stop launcher
for pid in "${readers[@]}"; do wait "$pid"; done
readers=()
finish_authenticated_apps
'''
        return self.spawn(['bash', '-c', code, 'fixture', str(self.state), str(self.desktops),
                           str(self.wrapper), str(self.text), str(self.writer), self.sink,
                           str(self.root / 'token')])

    def until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(.01)
        self.fail('fixture event deadline; stream=' + self.events.decode(errors='replace'))

    def launch_tile(self, filename):
        data = (self.state / 'data/applications' / filename).read_text()
        command = next(line[5:] for line in data.splitlines() if line.startswith('Exec='))
        return self.spawn(shlex.split(command))

    def ready_apps(self):
        controller = self.controller()
        self.until(lambda: b'OBSERVE authenticated launcher flow-ready\n' in self.events)
        self.assertFalse((self.state / 'mousepad').exists())
        self.assertFalse((self.state / 'foot').exists())
        editor = self.launch_tile('org.xfce.mousepad.desktop')
        foot = self.launch_tile('foot.desktop')
        self.until(lambda: b'EDITOR_WAYLAND fixture Mousepad protocol' in self.events
                   and b'FOOT_WAYLAND ROG5 controlled terminal:' in self.events)
        return controller, editor, foot

    def test_source_defines_functions_only(self):
        result = subprocess.run(['bash', '-c', 'source "$1"', 'fixture', str(TOOLS / 'logind-apps.sh')],
                                capture_output=True, timeout=2)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.state.exists())
        self.assertEqual(result.stdout + result.stderr, b'')

    def test_prepare_restores_exec_only_and_never_autostarts_clients(self):
        child = self.controller(prepare_only=True)
        out, err = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, err.decode())
        self.assertIn(b'apps NOT STARTED', out)
        self.assertFalse((self.state / 'foot').exists())
        self.assertFalse((self.state / 'mousepad').exists())
        self.assertIn('Exec=retained', (self.state / 'data/applications/foot.desktop').read_text())
        self.assertEqual((self.state / 'lifecycle.sh').stat().st_mode & 0o777, 0o600)

    def test_real_tile_commands_controlled_close_both_zero_and_remove_foot_fifo(self):
        controller, editor, foot = self.ready_apps()
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)
        os.write(self.master, (self.token + '\n').encode())
        out, err = controller.communicate(timeout=8)
        self.assertEqual(controller.returncode, 0, out.decode() + err.decode())
        self.assertEqual(editor.wait(timeout=2), 0)
        self.assertEqual(foot.wait(timeout=2), 0)
        foot_out, foot_err = foot.communicate(timeout=2)
        self.assertIn(b'phase=normal-close', foot_out)
        self.assertIn(b'status=0 term_sent=no', foot_out)
        for app in ('mousepad', 'foot'):
            self.assertEqual((self.state / app / 'finished').read_text(), '0\n')
        self.assertFalse((self.home / 'foot-close.pipe').exists())
        self.assertIn(b'OBSERVE authenticated launcher teardown\n', self.events)
        self.assertIn(b'OBSERVE launcher app=foot exit=0\n', self.events)
        self.assertIn(b'OBSERVE launcher app=mousepad exit=0\n', self.events)

    def test_wrong_ack_refused_and_cleanup_reaps_both_supervisors(self):
        controller, editor, foot = self.ready_apps()
        os.write(self.master, b'wrong\n')
        out, err = controller.communicate(timeout=8)
        self.assertNotEqual(controller.returncode, 0, out.decode() + err.decode())
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)
        self.assertNotEqual(editor.wait(timeout=2), 0)
        self.assertNotEqual(foot.wait(timeout=2), 0)
        self.assertFalse((self.home / 'foot-close.pipe').exists())

    def test_fragmented_host_ack_is_accumulated_without_accepting_prefix(self):
        controller, editor, foot = self.ready_apps()
        os.write(self.master, self.token[:8].encode()); time.sleep(.3)
        self.assertIsNone(controller.poll())
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)
        os.write(self.master, (self.token[8:] + '\n').encode())
        out, err = controller.communicate(timeout=8)
        self.assertEqual(controller.returncode, 0, out.decode() + err.decode())

    def test_early_client_failure_keeps_real_exit_status(self):
        self.command('mousepad', 'echo fixture-failure; exit 42\n')
        controller = self.controller()
        self.until(lambda: b'OBSERVE authenticated launcher flow-ready\n' in self.events)
        editor = self.launch_tile('org.xfce.mousepad.desktop')
        self.assertEqual(editor.wait(timeout=3), 42)
        out, err = controller.communicate(timeout=5)
        self.assertNotEqual(controller.returncode, 0)
        self.assertEqual((self.state / 'mousepad/exit-status').read_text(), '42\n')
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)

    def test_early_zero_is_not_accepted_as_controlled_completion(self):
        self.command('mousepad', 'exit 0\n')
        controller = self.controller()
        self.until(lambda: b'OBSERVE authenticated launcher flow-ready\n' in self.events)
        editor = self.launch_tile('org.xfce.mousepad.desktop')
        self.assertEqual(editor.wait(timeout=3), 1)
        controller.communicate(timeout=5)
        self.assertNotEqual(controller.returncode, 0)

    def test_missing_writer_refuses_before_creating_state(self):
        self.writer.unlink()
        controller = self.controller(prepare_only=True)
        controller.communicate(timeout=3)
        self.assertNotEqual(controller.returncode, 0)
        self.assertFalse(self.state.exists())

    def test_token_must_match_exact_host_contract(self):
        (self.root / 'token').write_text('ROG5_APPS_DONE_fixture\n')
        controller = self.controller(prepare_only=True)
        controller.communicate(timeout=3)
        self.assertNotEqual(controller.returncode, 0)
        self.assertFalse(self.state.exists())

    def test_existing_text_is_not_overwritten(self):
        self.text.write_text('retained unique contents')
        controller = self.controller(prepare_only=True)
        controller.communicate(timeout=3)
        self.assertNotEqual(controller.returncode, 0)
        self.assertEqual(self.text.read_text(), 'retained unique contents')
        self.assertFalse(self.state.exists())

    def test_missing_second_client_pipe_cleans_partial_evidence_setup(self):
        (self.home / 'foot.pipe').unlink()
        controller = self.controller(prepare_only=True)
        out, err = controller.communicate(timeout=4)
        self.assertNotEqual(controller.returncode, 0)
        self.assertNotIn(b'authenticated launcher overrides prepared', out)
        self.assertFalse((self.state / 'mousepad').exists())

    def test_duplicate_tile_launch_cannot_replace_original_owner(self):
        controller, editor, foot = self.ready_apps()
        owner = (self.state / 'mousepad/owner').read_bytes()
        duplicate = self.launch_tile('org.xfce.mousepad.desktop')
        self.assertNotEqual(duplicate.wait(timeout=2), 0)
        self.assertEqual((self.state / 'mousepad/owner').read_bytes(), owner)
        self.assertIsNone(editor.poll())
        os.write(self.master, (self.token + '\n').encode())
        out, err = controller.communicate(timeout=8)
        self.assertEqual(controller.returncode, 0, out.decode() + err.decode())

    def test_ack_before_any_tile_launch_is_refused(self):
        controller = self.controller()
        self.until(lambda: b'OBSERVE authenticated launcher flow-ready\n' in self.events)
        os.write(self.master, (self.token + '\n').encode())
        controller.communicate(timeout=4)
        self.assertNotEqual(controller.returncode, 0)
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)

    def test_stale_owner_identity_refused_without_signalling_unowned_process(self):
        (self.state / 'foot').mkdir(parents=True)
        sleeper = self.spawn(['sleep', '20'])
        (self.state / 'foot/owner').write_text(f'{sleeper.pid} 1\n')
        result = subprocess.run(['bash', '-c', self.prefix + '\nlogind_apps_owner "$1" foot',
                                 'fixture', str(self.state)], env=self.env, capture_output=True, timeout=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(sleeper.poll())

    def test_cli_refuses_outside_guarded_guest(self):
        result = subprocess.run(['bash', str(TOOLS / 'logind-apps.sh'), 'launch', 'foot'],
                                env=self.env, capture_output=True, timeout=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.state.exists())

    def test_editor_close_failure_preserves_actual_child_status(self):
        self.command('mousepad', '''trap 'exit 42' TERM
echo 'fixture Mousepad protocol'
while :; do sleep .1; done
''')
        controller, editor, foot = self.ready_apps()
        os.write(self.master, (self.token + '\n').encode())
        controller.communicate(timeout=8)
        self.assertNotEqual(controller.returncode, 0)
        self.assertEqual(editor.wait(timeout=2), 42)
        self.assertEqual((self.state / 'mousepad/exit-status').read_text(), '42\n')
        self.assertEqual(foot.wait(timeout=2), 0)


if __name__ == '__main__':
    unittest.main()
