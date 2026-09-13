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
        (self.home/'denial.log').write_text('fixture compositor diagnostic\n')
        self.runtime = self.root / 'runtime'; self.runtime.mkdir(mode=0o700)
        self.command_log = self.root / 'external-commands.log'
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
        # timeout execs programs; shell functions do not intercept these calls.
        bus_guard = '''[[ $DBUS_SESSION_BUS_ADDRESS == "unix:path=$XDG_RUNTIME_DIR/unavailable-session-bus" ]]
[[ $DBUS_SYSTEM_BUS_ADDRESS == "unix:path=$XDG_RUNTIME_DIR/unavailable-system-bus" ]]
[[ -d $XDG_RUNTIME_DIR && ! -e $XDG_RUNTIME_DIR/unavailable-session-bus ]]
'''
        self.command('dbus-update-activation-environment', bus_guard + '''
[[ $# == 2 && $1 == --systemd && $2 == XDG_DATA_HOME ]]
printf 'dbus-update-activation-environment %s\\n' "$*" >> "$TEST_COMMAND_LOG"
''')
        self.command('systemctl', bus_guard + '''
[[ $# == 2 && $1 == --user && $2 == show-environment ]]
printf 'systemctl %s\\n' "$*" >> "$TEST_COMMAND_LOG"
printf 'XDG_DATA_HOME=%s\\n' "$XDG_DATA_HOME"
''')
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
        # Do not inherit the desktop bus, manager, shell startup or exported
        # functions. A missed CLI fixture must fail against absent private buses.
        self.env = {'HOME': str(self.home), 'TEST_BIN': str(self.bin),
                    'TEST_COMMAND_LOG': str(self.command_log),
                    'PATH': str(self.bin) + ':/usr/bin:/bin', 'LANG': 'C.UTF-8',
                    'XDG_RUNTIME_DIR': str(self.runtime),
                    'XDG_DATA_HOME': str(self.home / '.local/share'),
                    'XDG_CONFIG_HOME': str(self.home / '.config'),
                    'XDG_CACHE_HOME': str(self.home / '.cache'),
                    'DBUS_SESSION_BUS_ADDRESS': 'unix:path=' + str(self.runtime / 'unavailable-session-bus'),
                    'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=' + str(self.runtime / 'unavailable-system-bus'),
                    'WAYLAND_DISPLAY': 'wayland-fixture'}
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

    def controller(self, prepare_only=False, post_prepare="", profile=None):
        code = self.prefix + r'''
readers=(); launcher=''; logind_apps_evidence_owned=0
cleanup_fixture(){
 rc=$?; trap - EXIT
 cleanup_authenticated_apps "$rc" || { [[ $rc != 0 ]] || rc=1; }
 stop_owned_group cleanup launcher || { [[ $rc != 0 ]] || rc=1; }
 for pid in "${readers[@]}"; do kill "$pid" 2>/dev/null || :; wait "$pid" 2>/dev/null || :; done
 readers=()
 old_port=${logind_apps_port:-}
 finish_authenticated_apps || { [[ $rc != 0 ]] || rc=1; }
 [[ -z $old_port || ! -e /proc/$$/fd/$old_port ]] || rc=92
 exit "$rc"
}
trap cleanup_fixture EXIT
trap 'exit 130' INT
prepare_authenticated_apps "$1" "$2" "$3" "$4" "$5" "$6" "$7"
'''
        if profile is not None:
            code = code.replace('prepare_authenticated_apps "$1" "$2" "$3" "$4" "$5" "$6" "$7"',
                                'prepare_authenticated_apps "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8"')
        code += post_prepare + "\n"
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
                           str(self.root / 'token'), *([] if profile is None else [profile])])

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

    def test_inherited_evidence_descriptor_does_not_reopen_removed_sink(self):
        alias = self.root / 'sink'
        alias.symlink_to(self.sink)
        code = self.prefix + r'''
exec {port}<> "$1"
rm -- "$1"
launcher_evidence_prepare "$2" "$1" "$3" "$port"
"$3" record inherited-port > "$2/events"
launcher_evidence_finish
exec {port}>&-
'''
        child = self.spawn(['bash', '-c', code, 'fixture', str(alias),
                            str(self.root / 'evidence'), str(self.writer)])
        out, err = child.communicate(timeout=3)
        self.assertEqual(child.returncode, 0, err.decode())
        self.until(lambda: b'inherited-port\n' in self.events)
        self.assertFalse(alias.exists())

    def test_controller_reads_open_descriptor_after_sink_path_removed(self):
        alias = self.root / 'sink'
        alias.symlink_to(self.sink)
        self.sink = str(alias)
        controller = self.controller(post_prepare='rm -- "$6"')
        self.until(lambda: b'OBSERVE authenticated launcher flow-ready\n' in self.events)
        editor = self.launch_tile('org.xfce.mousepad.desktop')
        foot = self.launch_tile('foot.desktop')
        self.until(lambda: b'EDITOR_WAYLAND fixture Mousepad protocol' in self.events
                   and b'FOOT_WAYLAND ROG5 controlled terminal:' in self.events)
        os.write(self.master, (self.token + '\n').encode())
        out, err = controller.communicate(timeout=8)
        self.assertEqual(controller.returncode, 0, out.decode() + err.decode())
        self.assertEqual(editor.wait(timeout=2), 0)
        self.assertEqual(foot.wait(timeout=2), 0)
        self.assertFalse(alias.exists())

    def test_finish_closes_port_after_partial_setup_or_failed_drain(self):
        for owned, status in [(0, 0), (1, 42)]:
            with self.subTest(owned=owned):
                code = self.prefix + r'''
exec {logind_apps_port}<> "$1"
old=$logind_apps_port
logind_apps_evidence_owned=$2
launcher_evidence_finish() { return 42; }
rc=0; finish_authenticated_apps || rc=$?
[[ $rc == "$3" && ! -v logind_apps_port && ! -e /proc/$$/fd/$old ]]
finish_authenticated_apps
'''
                child = self.spawn(['bash', '-c', code, 'fixture', self.sink,
                                    str(owned), str(status)])
                out, err = child.communicate(timeout=3)
                self.assertEqual(child.returncode, 0, err.decode())

    def test_invalid_inherited_descriptor_refuses_before_state_creation(self):
        code = self.prefix + '\nlauncher_evidence_prepare "$1" "$2" "$3" 9999'
        child = self.spawn(['bash', '-c', code, 'fixture', str(self.root / 'evidence'),
                            self.sink, str(self.writer)])
        child.communicate(timeout=3)
        self.assertNotEqual(child.returncode, 0)
        self.assertFalse((self.root / 'evidence').exists())

    def test_completion_published_between_wait_and_owner_check(self):
        for result in (0, 42):
            with self.subTest(result=result):
                state = self.root / ('race-' + str(result))
                code = self.prefix + r'''
state=$1; completed=$2
mkdir -p "$state/foot" "$state/mousepad"
start=$(launcher_identity "$$")
for app in foot mousepad; do
 printf '%s %s\n' "$$" "$start" > "$state/$app/owner"
 mkfifo "$state/$app/command"
done
exec {foot_fd}<> "$state/foot/command"
exec {editor_fd}<> "$state/mousepad/command"
eval "$(declare -f logind_apps_owner | sed '1s/logind_apps_owner/original_apps_owner/')"
printf '0\n' > "$state/calls"
logind_apps_owner() {
 local calls
 read -r calls < "$1/calls"
 ((calls+=1)); printf '%s\n' "$calls" > "$1/calls"
 # Initial calls are command dispatch. Publish only after the wait loop has
 # observed !finished, immediately before the real owner's !finished check.
 if ((calls>=3)); then printf '%s\n' "$completed" > "$1/$2/finished"; fi
 original_apps_owner "$@"
}
rc=0; logind_apps_close "$state" || rc=$?
[[ ($completed == 0 && $rc == 0) || ($completed != 0 && $rc != 0) ]]
IFS= read -r -t 1 -u "$foot_fd" token; [[ $token == ROG5_APP_CLOSE_0 ]]
IFS= read -r -t 1 -u "$editor_fd" token; [[ $token == ROG5_APP_CLOSE_0 ]]
exec {foot_fd}>&-; exec {editor_fd}>&-
'''
                child = self.spawn(['bash', '-c', code, 'fixture', str(state), str(result)])
                out, err = child.communicate(timeout=3)
                self.assertEqual(child.returncode, 0, out.decode() + err.decode())

    def test_cleanup_completion_race_does_not_signal_finished_owner(self):
        code = self.prefix + r'''
logind_apps_state=$1
mkdir -p "$1/mousepad"
start=$(launcher_identity "$$")
printf '%s %s\n' "$$" "$start" > "$1/mousepad/owner"
trap 'exit 91' TERM
eval "$(declare -f logind_apps_owner | sed '1s/logind_apps_owner/original_apps_owner/')"
logind_apps_owner() {
 printf '0\n' > "$1/$2/finished"
 original_apps_owner "$@"
}
cleanup_authenticated_apps
'''
        child = self.spawn(['bash', '-c', code, 'fixture', str(self.state)])
        out, err = child.communicate(timeout=3)
        self.assertEqual(child.returncode, 0, out.decode() + err.decode())

    def test_timeout_executes_external_bus_fixtures_with_private_environment(self):
        child = self.controller(prepare_only=True)
        out, err = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, out.decode() + err.decode())
        self.assertEqual(self.command_log.read_text().splitlines(), [
            'dbus-update-activation-environment --systemd XDG_DATA_HOME',
            'systemctl --user show-environment'])
        self.assertEqual(self.runtime.stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.runtime / 'unavailable-session-bus').exists())
        self.assertFalse((self.runtime / 'unavailable-system-bus').exists())
        self.assertNotIn('BASH_ENV', self.env)
        self.assertNotIn('DBUS_STARTER_ADDRESS', self.env)

    def test_external_bus_fixture_rejects_nonprivate_environment(self):
        self.env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/must-not-be-contacted'
        child = self.controller(prepare_only=True)
        out, err = child.communicate(timeout=5)
        self.assertNotEqual(child.returncode, 0, out.decode() + err.decode())
        self.assertFalse(self.command_log.exists())
        self.assertNotIn(b'authenticated launcher overrides prepared', out)

    def test_source_defines_functions_only(self):
        result = subprocess.run(['bash', '-c', 'source "$1"', 'fixture', str(TOOLS / 'logind-apps.sh')],
                                env=self.env, capture_output=True, timeout=2)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.state.exists())
        self.assertEqual(result.stdout + result.stderr, b'')

    def test_prepare_restores_exec_only_and_never_autostarts_clients(self):
        child = self.controller(prepare_only=True)
        out, err = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, err.decode())
        self.assertIn(b'apps NOT STARTED', out)
        self.assertEqual(self.text.read_bytes(), b'')
        self.assertFalse((self.state / 'foot').exists())
        self.assertFalse((self.state / 'mousepad').exists())
        self.assertIn('Exec=retained', (self.state / 'data/applications/foot.desktop').read_text())
        self.assertEqual((self.state / 'lifecycle.sh').stat().st_mode & 0o777, 0o600)

    def test_bottom_caret_prepares_exact_long_document_without_starting_apps(self):
        child = self.controller(prepare_only=True, profile='bottom-caret')
        out, err = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, out.decode()+err.decode())
        self.assertEqual(self.text.read_bytes(), ''.join(f'line-{line:02d}\n' for line in range(1, 65)).encode())
        self.assertFalse((self.state/'mousepad').exists())
        self.assertFalse((self.state/'foot').exists())
        self.assertIn(b'apps NOT STARTED', out)
        self.assertEqual((self.state/'text-path').read_text(), str(self.text)+'\n')

    def test_explicit_normal_profile_retains_empty_document(self):
        child = self.controller(prepare_only=True, profile='normal')
        out, err = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0, out.decode()+err.decode())
        self.assertEqual(self.text.read_bytes(), b'')

    def test_invalid_document_profile_fails_before_file_or_bus_effects(self):
        child = self.controller(prepare_only=True, profile='bottom-caret-wrong')
        out, err = child.communicate(timeout=5)
        self.assertNotEqual(child.returncode, 0, out.decode()+err.decode())
        self.assertFalse(self.text.exists())
        self.assertFalse(self.state.exists())
        self.assertFalse(self.command_log.exists())
        self.assertNotIn(b'PASS authenticated launcher overrides prepared', out)

    def test_bottom_caret_never_overwrites_existing_text(self):
        self.text.write_bytes(b'retained user data')
        child = self.controller(prepare_only=True, profile='bottom-caret')
        out, err = child.communicate(timeout=5)
        self.assertNotEqual(child.returncode, 0, out.decode()+err.decode())
        self.assertEqual(self.text.read_bytes(), b'retained user data')
        self.assertFalse(self.state.exists())
        self.assertFalse(self.command_log.exists())

    def test_guest_dispatch_requires_apps_marker_and_forwards_exact_profile(self):
        block = MAIN.split('publish_cache_environment\n', 1)[1].split('/usr/bin/denial-mobile-session --check', 1)[0]
        for apps, bottom in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(apps=apps, bottom=bottom):
                apps_marker, bottom_marker = self.root/'apps-probe', self.root/'bottom-caret-probe'
                for marker, present in ((apps_marker, apps), (bottom_marker, bottom)):
                    marker.unlink(missing_ok=True)
                    if present:
                        marker.touch()
                code = 'set -euo pipefail\nprepare_authenticated_apps(){ printf "CALL %s\\n" "$#"; printf "ARG %s\\n" "$@"; }\n'
                code += block.replace('/run/apps-probe', shlex.quote(str(apps_marker))).replace('/run/bottom-caret-probe', shlex.quote(str(bottom_marker)))
                result = subprocess.run(['bash', '-c', code], env=self.env, capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 0, result.stderr)
                if not apps:
                    self.assertEqual(result.stdout, '')
                elif not bottom:
                    self.assertEqual(result.stdout, 'CALL 0\nARG \n')
                else:
                    self.assertEqual(result.stdout.splitlines(), ['CALL 8',
                        'ARG '+str(self.home/'launcher-apps'), 'ARG /usr/share/applications',
                        'ARG /run/logind-apps.sh', 'ARG /tmp/rog5-text-probe.txt',
                        'ARG /run/evidence-writer', 'ARG /dev/vport0p1',
                        'ARG /run/apps-observe-token', 'ARG bottom-caret'])

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
        for app in ('foot', 'mousepad'):
            self.assertIn(f'OBSERVE launcher-lifecycle app={app} phase=normal-close status=0 child_status=0\n'.encode(), self.events)

    def test_wrong_ack_refused_and_cleanup_reaps_both_supervisors(self):
        controller, editor, foot = self.ready_apps()
        os.write(self.master, b'wrong\n')
        out, err = controller.communicate(timeout=8)
        self.assertNotEqual(controller.returncode, 0, out.decode() + err.decode())
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)
        self.assertNotEqual(editor.wait(timeout=2), 0)
        self.assertNotEqual(foot.wait(timeout=2), 0)
        self.assertIn(b'phase=signal-TERM status=143', self.events)
        self.assertFalse((self.home / 'foot-close.pipe').exists())

    def check_snapshot_failure_reason(self, status, periodic):
        controller = self.controller(post_prepare=f'''
snapshot_calls=0
logind_apps_snapshot() {{
 ((snapshot_calls+=1))
 if ((snapshot_calls == {2 if periodic else 1})); then return {status}; fi
}}
''')
        editor = None
        if periodic:
            self.until(lambda: b'OBSERVE authenticated launcher flow-ready\n' in self.events)
            editor = self.launch_tile('org.xfce.mousepad.desktop')
            self.until(lambda: b'EDITOR_WAYLAND fixture Mousepad protocol' in self.events)
        out, err = controller.communicate(timeout=10)
        self.assertEqual(controller.returncode, status, out.decode()+err.decode())
        phase = 'snapshot-periodic' if periodic else 'snapshot-initial'
        record = f'DENIAL_DIAGNOSTIC controller-exit phase={phase} status={status}\n'.encode()
        self.assertIn(record, self.events)
        self.assertNotIn(b'OBSERVE authenticated launcher teardown', self.events)
        if editor:
            self.assertEqual(editor.wait(timeout=2), 143)
            self.assertLess(self.events.index(record), self.events.index(b'phase=signal-TERM'))

    def test_initial_snapshot_failure_reason_survives_cleanup(self):
        self.check_snapshot_failure_reason(42, False)

    def test_periodic_snapshot_failure_reason_precedes_cleanup_term(self):
        self.check_snapshot_failure_reason(42, True)

    def test_periodic_snapshot_timeout_remains_failure_with_reason(self):
        self.check_snapshot_failure_reason(124, True)

    def check_optional_snapshot_close(self, periodic):
        # Exercise the actual snapshot and controller, including both owned apps.
        # Only local log preparation is injected; required evidence still flows.
        if periodic:
            self.command('head', '''
[[ $1 == -c && $2 == 1048576 ]] || exec /usr/bin/head "$@"
count=0
[[ ! -f $HOME/head-count ]] || read -r count < "$HOME/head-count"
((count+=1)); printf '%s\n' "$count" > "$HOME/head-count"
[[ $count != 3 ]] || exit 124
exec /usr/bin/head "$@"
''')
        else:
            self.command('head', '[[ $1 == -c && $2 == 1048576 ]] || exec /usr/bin/head "$@"\nexit 124\n')
        controller, editor, foot = self.ready_apps()
        self.until(lambda: b'DENIAL_DIAGNOSTIC snapshot-prepare status=124 optional=NOT_RUN\n'
                   in self.events, timeout=8)
        self.assertIsNone(controller.poll())
        self.assertIsNone(editor.poll()); self.assertIsNone(foot.poll())
        os.write(self.master, (self.token+'\n').encode())
        out, err = controller.communicate(timeout=8)
        self.assertEqual(controller.returncode, 0, out.decode()+err.decode())
        self.assertEqual(editor.wait(timeout=2), 0)
        self.assertEqual(foot.wait(timeout=2), 0)
        self.assertIn(b'OBSERVE authenticated launcher teardown\n', self.events)
        for app in ('mousepad', 'foot'):
            self.assertEqual((self.state/app/'finished').read_text(), '0\n')

    def test_optional_snapshot_preparation_timeout_keeps_authenticated_close(self):
        self.check_optional_snapshot_close(False)

    def test_optional_periodic_preparation_timeout_keeps_authenticated_close(self):
        self.check_optional_snapshot_close(True)

    def test_real_session_finish_passes_original_status_before_cleanup(self):
        finish = re.search(r'^finish\(\) \{.*?^\}', MAIN, re.M | re.S).group()
        marker = self.root/'apps-probe'; marker.touch()
        finish = finish.replace('/run/apps-probe', str(marker))
        code = r'''
readers=()
cleanup_authenticated_apps(){ printf 'cleanup-status=%s\n' "$1"; return 55; }
stop_all_owned(){ :; }
remove_foot_close(){ :; }
finish_authenticated_apps(){ :; }
''' + finish + '\ntrap finish EXIT\nexit 42\n'
        child = self.spawn(['bash', '-c', code])
        out, err = child.communicate(timeout=3)
        self.assertEqual(child.returncode, 42, err.decode())
        self.assertTrue(out.startswith(b'cleanup-status=42\n'))

    def test_failed_reason_delivery_does_not_replace_status_or_block_partial_cleanup(self):
        code = self.prefix + r'''
logind_apps_state=$1
logind_apps_phase=snapshot-periodic
logind_apps_record(){ return 55; }
logind_apps_evidence_owned=1
# Closed/absent keeper: no attempt to open the FIFO during partial setup.
cleanup_authenticated_apps 42
exec {launcher_evidence_keep}<> /dev/null
cleanup_authenticated_apps 42
exec {launcher_evidence_keep}>&-
exit 42
'''
        child = self.spawn(['bash', '-c', code, 'fixture', str(self.state)])
        out, err = child.communicate(timeout=3)
        self.assertEqual(child.returncode, 42)
        self.assertEqual(out, b'')
        self.assertEqual(err, b'DENIAL_DIAGNOSTIC controller-exit phase=snapshot-periodic status=42 delivery=failed\n')

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
        self.assertIn(b'OBSERVE launcher-lifecycle app=mousepad phase=normal-close status=42 child_status=42\n', self.events)

    def check_close_diagnostics(self, delay, expected):
        self.command('mousepad', f'''trap 'echo CLOSE_TERM_BEGIN; sleep {delay}; echo CLOSE_TERM_FINISHED; exit 0' TERM
echo 'fixture Mousepad protocol'
while :; do sleep .1; done
''')
        controller, editor, foot = self.ready_apps()
        os.write(self.master, (self.token + '\n').encode())
        controller.communicate(timeout=9)
        self.assertEqual(editor.wait(timeout=2), expected)
        self.assertEqual(foot.wait(timeout=2), 0)
        self.assertEqual(controller.returncode == 0, expected == 0)
        events = bytes(self.events)
        self.assertIn(b'DENIAL_DIAGNOSTIC timeout: sending signal TERM to command', events)
        self.assertEqual(b'DENIAL_DIAGNOSTIC timeout: sending signal KILL to command' in events,
                         expected == 137)
        records = re.findall(rb'DENIAL_DIAGNOSTIC app-close app=mousepad phase=(begin|close-returned) '
                             rb'pid=([0-9]+) clock=CLOCK_BOOTTIME seconds=([0-9]+\.[0-9]+)', events)
        self.assertEqual([r[0] for r in records], [b'begin', b'close-returned'])
        self.assertEqual(records[0][1], records[1][1])
        self.assertGreaterEqual(float(records[1][2]), float(records[0][2]))
        self.assertIn(f'phase=normal-close status={expected} child_status={expected}'.encode(), events)

    def test_fast_close_reports_term_and_clock_without_kill(self):
        self.check_close_diagnostics(.1, 0)

    def test_slow_close_reports_timeout_escalation_and_preserves_failure(self):
        self.check_close_diagnostics(2.5, 137)

    def test_timeout_signal_is_not_blocked_by_full_client_pipe(self):
        # Execute the production launch command with a full, unread client FIFO.
        # A verbose timeout sharing that FIFO blocks before forwarding TERM.
        launch = re.search(r'^        GDK_BACKEND=.*?^        editor=\$!',
                           (TOOLS / 'logind-apps.sh').read_text(), re.M | re.S).group()
        (self.state / 'mousepad').mkdir(parents=True)
        self.command('mousepad', 'exec sleep 60\n')
        fd = os.open(self.home / 'mousepad.pipe', os.O_RDWR | os.O_NONBLOCK)
        self.addCleanup(os.close, fd)
        while True:
            try: os.write(fd, b'x' * 4096)
            except BlockingIOError: break
        code = ('set -eu\nstate=$1; app=mousepad; bindir=$TEST_BIN; text=$2\n'
                + launch + '\nsleep .2\nkill -TERM "$editor"\n'
                + 'status=0; wait "$editor" || status=$?\n[[ $status == 143 ]]\n')
        child = self.spawn(['bash', '-c', code, 'fixture', str(self.state), str(self.text)])
        out, err = child.communicate(timeout=3)
        self.assertEqual(child.returncode, 0, out.decode() + err.decode())
        self.assertIn('sending signal TERM', (self.state / 'mousepad/timeout.log').read_text())


if __name__ == '__main__':
    unittest.main()
