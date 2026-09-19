#!/usr/bin/env python3
"""Exercise the real manual runner's process ownership without containers/VMs."""
import os
import ast
from types import SimpleNamespace
from unittest.mock import patch
import re
import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path
import signal
import shutil
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


class CleanupGrace(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('cleanup_runner', RUNNER)
        self.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.runner)
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-cleanup-grace-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runner.APPS_CLEANUP_GRACE = .4
        self.steps = []

    def test_approved_teardown_can_finish_after_progress_deadline(self):
        self.runner.execute([sys.executable, '-c', 'import time;time.sleep(.45)'],
                            self.root/'child.log', .3, self.steps,
                            poll=lambda: None, cleanup_ready=lambda: True)
        self.assertEqual(self.steps[0]['status'], 'PASS')
        self.assertEqual(self.steps[0]['effective_deadline_seconds'], .7)
        self.assertLess(self.steps[0]['cleanup_eligible_seconds'], .3)

    def virtual_failure(self, mode):
        clock = SimpleNamespace(value=0.)
        def sleep(seconds): clock.value += seconds
        clock.monotonic = lambda: clock.value
        clock.sleep = sleep
        self.runner.time = clock
        self.runner.APPS_CLEANUP_GRACE = .2
        def poll():
            if mode == 'late-tick': clock.value += .4
            if mode == 'error-during-grace' and clock.value >= .3:
                raise ValueError('late protocol error')
        def ready():
            if mode == 'late-predicate': clock.value += .4
            if mode == 'predicate-error': raise ValueError('eligibility unavailable')
            return mode != 'unapproved'
        with self.assertRaises((RuntimeError, ValueError)):
            self.runner.execute([sys.executable, '-c', 'import time;time.sleep(30)'],
                                self.root/'child.log', .3, self.steps, poll=poll, cleanup_ready=ready)
        row = self.steps[0]
        self.assertNotEqual(row['exit_status'], 0)
        if mode in ('unapproved', 'late-tick', 'late-predicate', 'predicate-error'):
            self.assertNotIn('effective_deadline_seconds', row)
        else:
            self.assertEqual(row['effective_deadline_seconds'], .5)
            self.assertLess(row['duration_seconds'], .53)
        return row

    def test_unapproved_cleanup_keeps_original_deadline(self):
        self.assertEqual(self.virtual_failure('unapproved')['status'], 'FAIL_TIMEOUT')

    def test_tick_crossing_deadline_cannot_enable_grace(self):
        self.virtual_failure('late-tick')

    def test_predicate_crossing_deadline_cannot_enable_grace(self):
        self.virtual_failure('late-predicate')

    def test_repeated_eligibility_cannot_reset_hard_deadline(self):
        self.assertEqual(self.virtual_failure('repeated')['status'], 'FAIL_TIMEOUT')

    def test_protocol_error_during_grace_still_fails(self):
        self.assertEqual(self.virtual_failure('error-during-grace')['status'], 'FAIL')

    def test_predicate_exception_fails_with_cleanup(self):
        self.virtual_failure('predicate-error')

    def test_allowance_requires_live_observer_before_starting_process(self):
        with self.assertRaisesRegex(ValueError, 'requires live observation'):
            self.runner.execute(['must-not-execute'], self.root/'no.log', .3, self.steps,
                                cleanup_ready=lambda: True)
        self.assertEqual(self.steps, [])
        self.assertFalse((self.root/'no.log').exists())

    def test_actual_apps_predicate_requires_all_handshake_conditions(self):
        self.assertFalse(self.runner.apps_cleanup_ready(None))
        valid = dict(complete=True, ack_sent=True, teardown=True, error=None)
        self.assertTrue(self.runner.apps_cleanup_ready(SimpleNamespace(**valid)))
        for field in valid:
            changed = dict(valid); changed[field] = 'failure' if field == 'error' else False
            self.assertFalse(self.runner.apps_cleanup_ready(SimpleNamespace(**changed)), field)

    def terminal_cutoff(self, grace, final_only=False):
        clock = SimpleNamespace(value=0.)
        clock.monotonic = lambda: clock.value
        def sleep(seconds): clock.value += seconds
        clock.sleep = sleep; self.runner.time = clock
        self.runner.APPS_CLEANUP_GRACE = .2
        class Child:
            pid = 123456789  # killpg is intercepted below; never signal this PID.
            returncode = None
            calls = 0
            def poll(self):
                self.calls += 1
                if final_only or self.calls > (2 if grace else 1): self.returncode = 0
                return self.returncode
            def wait(self, timeout): return self.returncode
        child = Child()
        ticks = 0
        def tick():
            nonlocal ticks
            ticks += 1
            clock.value = .1 if grace and ticks == 1 else .6 if grace else .4
        with patch.object(self.runner.subprocess, 'Popen', return_value=child), \
             patch.object(self.runner.os, 'killpg'):
            with self.assertRaisesRegex(RuntimeError, 'command exceeded'):
                self.runner.execute(['inert-child'], self.root/'terminal.log', .3, self.steps,
                                    poll=tick, cleanup_ready=lambda: grace)
        self.assertEqual(self.steps[0]['status'], 'FAIL_TIMEOUT')

    def test_terminal_child_cannot_bypass_original_cutoff(self):
        self.terminal_cutoff(False)

    def test_terminal_child_cannot_bypass_hard_grace_cutoff(self):
        self.terminal_cutoff(True)

    def test_final_observer_call_cannot_bypass_cutoff(self):
        self.terminal_cutoff(False, final_only=True)

    def test_real_vm_call_attaches_allowance_only_for_apps(self):
        tree = ast.parse(RUNNER.read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == 'container'
                 and len(node.args) > 2 and 'serial.log' in ast.unparse(node.args[2])]
        self.assertEqual(len(calls), 1)
        for apps in (False, True):
            kwargs = {}
            observer = SimpleNamespace(tick=lambda: None, complete=True, ack_sent=True,
                                       teardown=True, error=None)
            def capture(*args, **options): kwargs.update(options)
            namespace = dict(container=capture, command=['inert'], name='owned',
                             output=self.root, combined=True, result={'steps':[]}, observer=observer,
                             finish_observer=lambda error: None, args=SimpleNamespace(observe_apps=apps),
                             apps_cleanup_ready=self.runner.apps_cleanup_ready)
            exec(compile(ast.Expression(calls[0]), str(RUNNER), 'eval'), namespace)
            if apps:
                self.assertTrue(kwargs['cleanup_ready']())
                observer.teardown=False
                self.assertFalse(kwargs['cleanup_ready']())
            else:
                self.assertIsNone(kwargs['cleanup_ready'])


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

    def test_live_observer_failure_reaps_owned_process(self):
        spec = importlib.util.spec_from_file_location('runner_live', RUNNER)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); pidfile = root/'pid'
            command = [sys.executable, '-c',
                       'import os,time;from pathlib import Path;'
                       f'Path({str(pidfile)!r}).write_text(str(os.getpid()));time.sleep(30)']
            called = []
            def observe():
                if pidfile.exists():
                    called.append(int(pidfile.read_text()))
                    self.assertTrue(live(called[-1]))
                    raise ValueError('deliberate observation failure')
            with self.assertRaisesRegex(ValueError, 'deliberate observation failure'):
                module.execute(command, root/'child.log', 3, [], poll=observe)
            self.assertEqual(len(called), 1)
            self.assertFalse(live(called[0]))

    def test_observer_finalizes_before_container_removal_even_on_failure(self):
        spec=importlib.util.spec_from_file_location('runner_finalize',RUNNER)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        events=[]; steps=[]
        def execute(command, log, deadline, rows, **kwargs):
            events.append(command[0] if command[0] != 'podman' else command[1])
            rows.append({})
            if command[0] == 'fixture': raise ValueError('original failure')
        module.execute=execute
        def finalize(error):
            self.assertIn('original failure',str(error));events.append('finalize')
            raise ValueError('release failed')
        with self.assertRaisesRegex(RuntimeError,'original failure'):
            module.container(['fixture'],'owned',Path('/unused.log'),1,steps,finalize=finalize)
        self.assertEqual(events,['fixture','finalize','rm','container'])

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


class ExecutableView(unittest.TestCase):
    def restore(self, first=0, second=0, original=None, abort=None):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-session.sh'
        source = script.read_text()
        restore_state = re.search(r'\|\| restore_needed=(\d+)', source).group(1)
        exit_trap = re.search(r'^trap .* EXIT$', source, re.M).group()
        success = source.split('# Restore canonical executable paths', 1)[1]
        success = success.split("echo 'PASS authenticated", 1)[0]
        # Remove the remainder of the first comment line after splitting.
        success = success.split('\n', 1)[1]
        body = success if original is None else f'exit {original}\n'
        code = r'''
set -euo pipefail
source "$1"
FIRST=$2; SECOND=$3; ABORT=$4
/run/original-bin/umount(){
    printf 'CALL original %s\n' "$*"
    [[ ${1:-} != --lazy ]] || return "$ABORT"
    return "$FIRST"
}
/usr/bin/umount(){ printf 'CALL canonical %s\n' "$*"; return "$SECOND"; }
''' + f'restore_needed={restore_state}\n' + exit_trap + '\n' + body
        return subprocess.run(['bash', '-c', code, 'fixture', str(script), str(first), str(second),
                               str(first if abort is None else abort)],
                              capture_output=True, text=True, timeout=3)

    def test_aborted_session_detaches_busy_owned_overlay_and_preserves_timeout(self):
        result = self.restore(first=32, abort=0, original=124)
        self.assertEqual(result.returncode, 124, result.stdout+result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['CALL original --lazy /usr/bin', 'CALL canonical --lazy /run/original-bin'])

    def test_normal_restore_failure_stays_failure_after_abort_detach(self):
        result = self.restore(first=32, abort=0)
        self.assertEqual(result.returncode, 32, result.stdout+result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['CALL original /usr/bin', 'CALL original --lazy /usr/bin',
                          'CALL canonical --lazy /run/original-bin'])

    def test_lazy_alias_release_follows_canonical_restore_and_has_no_force(self):
        result = self.restore()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['CALL original /usr/bin', 'CALL canonical --lazy /run/original-bin'])

    def test_first_failure_never_releases_alias_or_claims_success(self):
        result = self.restore(first=42)
        self.assertEqual(result.returncode, 42, result.stdout+result.stderr)
        self.assertNotIn('CALL canonical', result.stdout)

    def test_second_failure_never_repeats_successful_canonical_restore(self):
        result = self.restore(second=43)
        self.assertEqual(result.returncode, 43, result.stdout+result.stderr)
        self.assertEqual(result.stdout.count('CALL original /usr/bin'), 1)
        self.assertIn('CALL canonical --lazy /run/original-bin', result.stdout)

    def test_exit_cleanup_keeps_original_failure_and_releases_both_mounts(self):
        for first, second in [(0, 0), (42, 0), (0, 43)]:
            with self.subTest(first=first, second=second):
                result = self.restore(first, second, original=37)
                self.assertEqual(result.returncode, 37, result.stdout+result.stderr)
                self.assertIn('CALL original --lazy /usr/bin', result.stdout)
                if not first:
                    self.assertIn('CALL canonical --lazy /run/original-bin', result.stdout)
                else:
                    self.assertNotIn('CALL canonical', result.stdout)
                if first or second:
                    self.assertIn(f'stage={2 if first else 1} status={first or second}', result.stderr)


class CacheEnvironment(unittest.TestCase):
    def publish(self, mode='success'):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh'
        source = script.read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        # Real production boundary: cache publication must precede even the
        # mobile entry preflight. Old code executes it without any publication.
        prelaunch = source.split("trap 'exit 130' INT\n", 1)[1]
        prelaunch = prelaunch.split('/usr/bin/denial-mobile-session >', 1)[0]
        cache_exports = '\n'.join(line for line in source.splitlines()
                                 if re.match(r'^export (GSETTINGS_SCHEMA_DIR|XDG_DATA_DIRS|GTK_IM_MODULE_FILE)=', line))
        cache_exports = cache_exports.replace('/run/gtk-runtime', '${1}')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'schemas').mkdir(); (root/'mime').mkdir()
            if mode != 'missing_schema': (root/'schemas/gschemas.compiled').write_bytes(b'fixture')
            if mode != 'missing_mime': (root/'mime/mime.cache').write_bytes(b'fixture')
            if mode not in ('missing_im', 'unset_im'):
                (root/'immodules.cache').write_bytes(b'' if mode == 'empty_im' else b'fixture')
            private_bin = root/'bin'; private_bin.mkdir()
            runtime = root/'runtime'; runtime.mkdir(mode=0o700)
            stubs = {
                'timeout': r'''#!/bin/bash
set -euo pipefail
[[ ${1:-} == -k && ${2:-} == 1 && ${3:-} == 3 ]] || exit 97
printf 'TIMEOUT %s\n' "$*" >&2
exec /usr/bin/timeout "$@"
''',
                'dbus-update-activation-environment': r'''#!/bin/bash
set -euo pipefail
[[ $* == '--systemd GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS GTK_IM_MODULE_FILE' ||
   $* == '--systemd GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS' ]] || exit 98
[[ $DBUS_SESSION_BUS_ADDRESS == "unix:path=$XDG_RUNTIME_DIR/unavailable-session-bus" ]] || exit 99
printf 'IMPORT %s\n' "$*"
case $MODE in unavailable) exit 127;; update_fail) exit 69;; deadline) exit 124;; esac
''',
                'systemctl': r'''#!/bin/bash
set -euo pipefail
[[ $* == '--user show-environment' ]] || exit 98
[[ $DBUS_SESSION_BUS_ADDRESS == "unix:path=$XDG_RUNTIME_DIR/unavailable-session-bus" ]] || exit 99
printf 'MANAGER %s\n' "$*" >&2
[[ $MODE != query_fail ]] || exit 42
[[ $MODE != missing_value ]] || exit 0
printf 'GSETTINGS_SCHEMA_DIR=%s\n' "$GSETTINGS_SCHEMA_DIR"
if [[ $MODE == mismatch ]]; then printf 'XDG_DATA_DIRS=/wrong\n'
else printf 'XDG_DATA_DIRS=%s\n' "$XDG_DATA_DIRS"; fi
[[ $MODE != duplicate ]] || printf 'GSETTINGS_SCHEMA_DIR=%s\n' "$GSETTINGS_SCHEMA_DIR"
if [[ $MODE == mismatch_im ]]; then printf 'GTK_IM_MODULE_FILE=/wrong\n'
elif [[ $MODE != missing_im_value ]]; then printf 'GTK_IM_MODULE_FILE=%s\n' "${GTK_IM_MODULE_FILE:-}"; fi
[[ $MODE != duplicate_im ]] || printf 'GTK_IM_MODULE_FILE=%s\n' "${GTK_IM_MODULE_FILE:-}"
exit 0
''',
            }
            for name, body in stubs.items():
                target = private_bin/name; target.write_text(body); target.chmod(0o700)
            code = 'set -euo pipefail\n' + functions + '\n' + cache_exports + r'''
export MODE=$2
[[ $MODE != unset_im ]] || unset GTK_IM_MODULE_FILE
# FUSE access is checked separately; this fixture isolates cache publication.
require_fuse_device(){ :; }
# Real timeout execs only private executable transport stubs. No inherited
# shell functions or real host bus/user-manager endpoint enters this fixture.
/usr/bin/denial-mobile-session(){ printf 'MOBILE %s\n' "$*"; }
''' + prelaunch
            environment = {
                'PATH': f'{private_bin}:/usr/bin:/bin', 'HOME': directory,
                'XDG_RUNTIME_DIR': str(runtime), 'LC_ALL': 'C',
                'XDG_DATA_HOME': str(root/'data'), 'XDG_CONFIG_HOME': str(root/'config'),
                'XDG_CACHE_HOME': str(root/'cache'),
                'DBUS_SESSION_BUS_ADDRESS': f'unix:path={runtime}/unavailable-session-bus',
                'DBUS_SYSTEM_BUS_ADDRESS': f'unix:path={runtime}/unavailable-system-bus',
            }
            return subprocess.run(['bash', '-c', code, 'fixture', directory, mode],
                                  env=environment, capture_output=True, text=True, timeout=3)

    def test_actual_prelaunch_publishes_only_cache_keys_and_verifies_manager(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('IMPORT --systemd GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS GTK_IM_MODULE_FILE\n', result.stdout)
        self.assertEqual(result.stderr.count('MANAGER --user show-environment\n'), 1)
        self.assertIn('TIMEOUT -k 1 3 dbus-update-activation-environment --systemd GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS GTK_IM_MODULE_FILE\n', result.stderr)
        self.assertIn('TIMEOUT -k 1 3 systemctl --user show-environment', result.stderr)
        self.assertLess(result.stdout.index('IMPORT '), result.stdout.index('MOBILE --check'))

    def test_missing_caches_prevent_publication_and_launch(self):
        for mode in ['missing_schema', 'missing_mime', 'missing_im', 'empty_im', 'unset_im']:
            with self.subTest(mode=mode):
                result = self.publish(mode)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('IMPORT ', result.stdout)
                self.assertNotIn('MOBILE ', result.stdout)

    def test_failed_transfer_or_query_prevents_launch_and_preserves_status(self):
        for mode, status in [('unavailable', 127), ('update_fail', 69), ('deadline', 124), ('query_fail', 42)]:
            with self.subTest(mode=mode):
                result = self.publish(mode)
                self.assertEqual(result.returncode, status, result.stdout+result.stderr)
                self.assertNotIn('MOBILE ', result.stdout)

    def test_missing_duplicate_or_mismatched_manager_values_prevent_launch(self):
        for mode in ['missing_value', 'duplicate', 'mismatch', 'missing_im_value', 'duplicate_im', 'mismatch_im']:
            with self.subTest(mode=mode):
                result = self.publish(mode)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('MOBILE ', result.stdout)


class ActivatedServices(unittest.TestCase):
    def qualify(self, mode='success'):
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh').read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        boundary = re.search(r"^printf 'OBSERVE activated local Denial.*?\n(.*?)^if \[\[ -f /run/apps-probe \]\]", source, re.M | re.S).group(1)
        code = 'set -euo pipefail\n' + functions + r'''
export XDG_RUNTIME_DIR=/run/user/1000
MODE=$1; CLOCK_COUNT=$2
lsclocks(){
    [[ $* == '--time CLOCK_MONOTONIC --no-discover-dynamic' ]] || return 98
    if [[ $MODE == *post_clock ]]; then
        [[ ! -f $CLOCK_COUNT ]] || return 43
        : > "$CLOCK_COUNT"
    fi
    case $MODE in clock_fail) return 43;; clock_bad) echo not-a-clock;; *) echo 100.123456789;; esac
}
timeout(){ printf 'BOUNDED %s\n' "$*" >&2; shift 3; "$@"; }
stdbuf(){
    [[ $1 == -oL && $2 == -e0 ]] || return 98
    [[ $MODE != start_fail_buffer_tool ]] || return 127
    shift 2; "$@"
}
systemctl(){
    printf 'SERVICE %s\n' "$*" >&2
    if [[ $2 == start ]]; then [[ $MODE != start_fail* ]] || return 124; return 0; fi
    if [[ $2 == show ]]; then
        [[ $MODE != start_fail_snapshot ]] || return 42
        [[ $MODE != start_fail_overflow ]] || { head -c 70000 /dev/zero | tr '\0' x; echo; return; }
        printf 'Id=xdg-desktop-portal-gtk.service\nActiveState=active\nActiveEnterTimestampMonotonic=99123456\n'
        return 0
    fi
    [[ $MODE != query_fail ]] || return 42
    [[ $MODE != query_deadline ]] || return 124
    case $MODE in
        empty_states) return 0;;
        partial_states) printf 'active\nactive\nactive\n';;
        inactive) printf 'active\nactive\ninactive\nactive\n';;
        *) printf 'active\nactive\nactive\nactive\n';;
    esac
}
findmnt(){
    printf 'MOUNT %s\n' "$*" >&2
    case $MODE in
        mount_fail) return 1;;
        mount_deadline) return 124;;
        empty_mount) return 0;;
        ancestor) printf '/run/user/1000 tmpfs rw\n';;
        wrong_type) printf '/run/user/1000/doc tmpfs rw\n';;
        duplicate_mount) printf '/run/user/1000/doc fuse.portal rw\n/run/user/1000/doc fuse.portal rw\n';;
        fuse_plain) printf '/run/user/1000/doc fuse rw,nosuid,nodev\n';;
        *) printf '/run/user/1000/doc fuse.portal rw,nosuid,nodev\n';;
    esac
}
''' + boundary + "echo CLIENTS-MAY-START\n"
        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(['bash', '-c', code, 'fixture', mode, str(Path(directory)/'clock')],
                                  capture_output=True, text=True, timeout=3)

    def fuse_guard(self, device, helper, uid='0', gid='0'):
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh').read_text()
        function = re.search(r'^require_fuse_device\(\) \{.*?^\}', source, re.M | re.S).group()
        code = function + r'''
# Preserve real stat's mode/type, replacing only ownership facts unavailable to
# an unprivileged host fixture. No mount helper or device operation is executed.
stat(){ local owner group rest; read -r owner group rest <<< "$(command stat "$@")"; printf '%s %s %s\n' "$UID_FACT" "$GID_FACT" "$rest"; }
UID_FACT=$3; GID_FACT=$4
require_fuse_device "$1" "$2"
'''
        return subprocess.run(['bash', '-c', code, 'fixture', str(device), str(helper), uid, gid],
                              capture_output=True, text=True, timeout=3)

    def test_actual_fuse_guard_rejects_missing_and_regular_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); regular = root/'regular'; regular.write_bytes(b'not a device')
            helper = root/'helper'; helper.write_bytes(b'helper'); helper.chmod(0o4755)
            for path, expected in [(regular, 1), (regular.with_name('missing'), 1), (Path('/dev/null'), 0)]:
                with self.subTest(path=str(path)):
                    result = self.fuse_guard(path, helper)
                    self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
            # /dev/null exercises only the predicate, not actual FUSE support.

    def test_actual_fuse_guard_rejects_wrong_helper_metadata_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); helper = root/'helper'; helper.write_bytes(b'helper')
            link = root/'link'; link.symlink_to(helper)
            for path, mode, uid, gid, expected in [
                    (helper, 0o4755, '0', '0', 0), (helper, 0o755, '0', '0', 1),
                    (helper, 0o4755, '1000', '0', 1), (helper, 0o4755, '0', '1000', 1),
                    (link, 0o4755, '0', '0', 1), (helper, 0o6755, '0', '0', 1)]:
                with self.subTest(path=str(path), mode=oct(mode), uid=uid, gid=gid):
                    helper.chmod(mode)
                    result = self.fuse_guard('/dev/null', path, uid, gid)
                    self.assertEqual(result.returncode, expected, result.stdout+result.stderr)

    def test_actual_boundary_starts_all_services_and_requires_exact_fuse_mount(self):
        for mode in ['success', 'fuse_plain']:
            with self.subTest(mode=mode):
                result = self.qualify(mode)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                names = 'at-spi-dbus-bus.service xdg-document-portal.service xdg-desktop-portal-gtk.service xdg-desktop-portal.service'
                self.assertIn('BOUNDED -k 1 25 systemctl --user start '+names, result.stderr)
                self.assertIn('BOUNDED -k 1 3 systemctl --user is-active '+names, result.stderr)
                self.assertIn('MOUNT --kernel --noheadings --raw --mountpoint /run/user/1000/doc --output TARGET,FSTYPE,OPTIONS', result.stderr)
                self.assertIn('OBSERVE document portal mount=/run/user/1000/doc fuse', result.stdout)
                self.assertIn('CLIENTS-MAY-START', result.stdout)

    def test_each_boundary_reports_its_exact_status_on_stderr(self):
        stages = ['service-start', 'service-state', 'document-mount']
        for mode, stage, status in [('success', 'document-mount', 0),
                                   ('start_fail', 'service-start', 124),
                                   ('query_fail', 'service-state', 42),
                                   ('query_deadline', 'service-state', 124),
                                   ('mount_fail', 'document-mount', 1),
                                   ('mount_deadline', 'document-mount', 124)]:
            with self.subTest(mode=mode):
                result = self.qualify(mode)
                self.assertEqual(result.returncode, status, result.stdout+result.stderr)
                self.assertRegex(result.stderr, rf'OBSERVE stage={stage} phase=begin deadline_seconds=\d+')
                self.assertRegex(result.stderr, rf'OBSERVE stage={stage} phase=end status={status} elapsed_seconds=\d+')
                self.assertNotIn('OBSERVE stage=', result.stdout)
                for later in stages[stages.index(stage)+1:]:
                    self.assertNotIn(f'OBSERVE stage={later}', result.stderr)

    def test_monotonic_clock_and_snapshot_precede_failure_return(self):
        for mode in ['success', 'start_fail', 'start_fail_snapshot', 'start_fail_overflow',
                     'start_fail_buffer_tool']:
            with self.subTest(mode=mode):
                r = self.qualify(mode)
                self.assertEqual(r.returncode, 0 if mode == 'success' else 124, r.stderr)
                self.assertIn('clock=CLOCK_MONOTONIC seconds=100.123456789', r.stderr)
                self.assertIn('OBSERVE service-snapshot phase=begin', r.stderr)
                status = (127 if mode == 'start_fail_buffer_tool' else
                          42 if mode in ['start_fail_snapshot', 'start_fail_overflow'] else 0)
                self.assertIn(f'OBSERVE service-snapshot phase=end status={status}', r.stderr)
                self.assertIn('--property=ActiveEnterTimestampMonotonic', r.stderr)
                self.assertLess(len(r.stderr), 68000)
                if mode != 'success': self.assertNotIn('CLIENTS-MAY-START', r.stdout)

    def test_post_clock_failure_keeps_primary_start_failure(self):
        for mode, status in [('success_post_clock',43), ('start_fail_post_clock',124)]:
            with self.subTest(mode=mode):
                r=self.qualify(mode)
                self.assertEqual(r.returncode,status,r.stderr)
                self.assertIn('OBSERVE service-clock phase=after-start status=43',r.stderr)
                self.assertIn('OBSERVE service-snapshot phase=end status=0',r.stderr)
                self.assertNotIn('CLIENTS-MAY-START',r.stdout)

    def test_bad_clock_refuses_before_service_start(self):
        for mode, status in [('clock_fail',43), ('clock_bad',1)]:
            with self.subTest(mode=mode):
                r=self.qualify(mode)
                self.assertEqual(r.returncode,status,r.stderr)
                self.assertNotIn('SERVICE --user start',r.stderr)
                self.assertNotIn('CLIENTS-MAY-START',r.stdout)

    def test_service_and_mount_failures_never_admit_clients(self):
        for mode in ['start_fail', 'query_fail', 'empty_states', 'partial_states', 'inactive',
                     'mount_fail', 'empty_mount', 'ancestor', 'wrong_type', 'duplicate_mount']:
            with self.subTest(mode=mode):
                result = self.qualify(mode)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('CLIENTS-MAY-START', result.stdout)


class DeviceReadiness(unittest.TestCase):
    BASE = ['/dev/dri/card0', '/dev/input/event0', '/dev/tty1']

    def run_boundary(self, flags=(), missing='', uninitialized='', failure=0):
        source = (RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh').read_text()
        # Execute the real supervisor call site; extraction also supports the
        # old global barrier so its unrelated-queue counterexample is retained.
        boundary = source.split("echo 'OBSERVE packaged Permit User Sessions removed startup nologin'\n", 1)[1].split('\n# A diagnostic failure', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for flag in flags:
                (root/flag).touch()
            tool = root/'udevadm'
            tool.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args=sys.argv[1:]
Path(os.environ['ARGUMENTS']).write_text(json.dumps(args))
if args == ['settle','--timeout=8']:
    sys.exit(124)  # unrelated queued event; all requested devices may be ready
if args[:3] != ['wait','--timeout=8','--initialized=yes']:
    sys.exit(98)
if os.environ['MISSING'] in args[3:] or os.environ['UNINITIALIZED'] in args[3:]:
    sys.exit(42)
sys.exit(int(os.environ['FAILURE']))
''')
            tool.chmod(0o755)
            # Source-only mode executes functions, never the root supervisor.
            # Redirect the default /run argument at the call seam, keeping the
            # function body and fixed /dev consumers unchanged.
            code = 'set -euo pipefail\nsource "$1"\n' + boundary.replace('logind_wait_devices', 'logind_wait_devices "$2"') + '\necho ADMITTED\n'
            result = subprocess.run(['bash', '-c', code, 'fixture',
                                     str(RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh'), str(root)],
                                    env={**os.environ, 'PATH': str(root)+':'+os.environ['PATH'],
                                         'ARGUMENTS': str(root/'args'), 'MISSING': missing,
                                         'UNINITIALIZED': uninitialized, 'FAILURE': str(failure)},
                                    capture_output=True, text=True, timeout=3)
            arguments = json.loads((root/'args').read_text()) if (root/'args').exists() else None
            return result, arguments

    def test_ready_consumers_do_not_wait_for_unrelated_queue(self):
        for flags, extra in [((), []), (('session-sha256',), ['/dev/fuse']),
                             (('session-sha256','startup-only'), ['/dev/fuse']),
                             (('session-sha256','editor-probe'), ['/dev/fuse','/dev/input/event1','/dev/vport0p1']),
                             (('session-sha256','apps-probe'), ['/dev/fuse','/dev/input/event1','/dev/vport0p1'])]:
            with self.subTest(flags=flags):
                result, arguments = self.run_boundary(flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(arguments, ['wait','--timeout=8','--initialized=yes', *self.BASE, *extra])
                self.assertIn('ADMITTED', result.stdout)

    def test_every_consumed_device_must_exist_and_be_initialized(self):
        flags = ('session-sha256','apps-probe')
        for device in [*self.BASE, '/dev/fuse','/dev/input/event1','/dev/vport0p1']:
            for kind in ['missing','uninitialized']:
                with self.subTest(device=device, kind=kind):
                    result, _ = self.run_boundary(flags, **{kind:device})
                    self.assertEqual(result.returncode, 42, result.stderr)
                    self.assertNotIn('ADMITTED', result.stdout)

    def test_query_failures_remain_fatal(self):
        for code in [1, 42, 124, 127]:
            with self.subTest(code=code):
                result, _ = self.run_boundary(failure=code)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertNotIn('ADMITTED', result.stdout)

    def test_inconsistent_observation_modes_refuse_before_query(self):
        for flags in [('editor-probe',), ('apps-probe',),
                      ('session-sha256','editor-probe','apps-probe')]:
            with self.subTest(flags=flags):
                result, arguments = self.run_boundary(flags)
                self.assertNotEqual(result.returncode, 0)
                self.assertIsNone(arguments)
                self.assertNotIn('ADMITTED', result.stdout)


class ServiceSnapshot(unittest.TestCase):
    def test_completed_unit_output_survives_a_later_query_timeout(self):
        # A libc-buffered producer writes a complete small reply then stalls.
        # Run the actual snapshot function and timeout, not a duplicate model.
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh').read_text()
        function = re.search(r'^service_snapshot\(\) \{.*?^\}', source, re.M | re.S).group()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            producer = root/'producer.c'
            producer.write_text('''#include <stdio.h>
#include <unistd.h>
int main(void) {
    puts("Id=at-spi-dbus-bus.service");
    puts("ActiveState=active");
    puts("Job=0");
    fputs("diagnostic-without-newline", stderr);
    for (;;) pause();
}
''')
            subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', str(producer),
                            '-o', str(root/'systemctl')], check=True, timeout=15,
                           capture_output=True)
            # Preserve the actual timeout/group cleanup but shorten fixture time.
            # Reject any change to the production deadline arguments.
            timer = root/'timeout'
            timer.write_text('#!/bin/bash\n[[ $1 == -k && $2 == 1 && $3 == 3 ]] || exit 98\n'
                             'exec /usr/bin/timeout -k .1 .2 "${@:4}"\n')
            timer.chmod(0o755)
            code = 'set -euo pipefail\n' + function + '\nservice_snapshot at-spi-dbus-bus.service xdg-desktop-portal.service\n'
            result = subprocess.run(['bash', '-c', code],
                                    env={**os.environ, 'PATH': str(root)+':'+os.environ['PATH']},
                                    capture_output=True, text=True, timeout=6)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertIn('Id=at-spi-dbus-bus.service\nActiveState=active\nJob=0\n', result.stderr)
            self.assertIn('diagnostic-without-newline', result.stderr)
            self.assertIn('OBSERVE service-snapshot phase=end status=124', result.stderr)


class FuseHelperStaging(unittest.TestCase):
    def run_stage(self, source_path, target, *, repeat=False, ownership_status=0, hash_fault=None):
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial-prepare.sh').read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        block = source.split('chmod 6755 /run/session-bin/unix_chkpwd\n', 1)[1]
        block = block.split('mount --bind /run/session-bin /usr/bin', 1)[0]
        block = block.replace('/run/original-bin/fusermount3', '"$1"').replace('/run/session-bin/fusermount3', '"$2"')
        code = 'set -euo pipefail\n' + functions + r'''
# Ownership alone is a host fact fixture; copying, link checks and chmod are real.
chown(){ [[ $1 == 0:0 ]] || return 99; return "$3"; }
'''.replace('return "$3"', f'return {ownership_status}') + block
        if hash_fault:
            fault = {
                'source': 'sha256sum(){ [[ $2 != "$SOURCE_PATH" ]] || return 42; command sha256sum "$@"; }\n',
                'copy': 'sha256sum(){ [[ $2 != "$TARGET_PATH" ]] || return 43; command sha256sum "$@"; }\n',
                'corrupt': 'cp(){ command cp "$@" || return $?; printf corrupted >> "${@: -1}"; }\n',
            }[hash_fault]
            code = code[:-len(block)] + 'SOURCE_PATH=$1; TARGET_PATH=$2\n' + fault + block
        if repeat: code += block
        # Constrain every staging test to real utilities already supplied by the
        # retained runtime. In particular, cmp/diffutils must not leak from host.
        with tempfile.TemporaryDirectory() as directory:
            commands = Path(directory)
            for name in ['bash', 'readlink', 'rm', 'cp', 'chmod', 'sha256sum']:
                executable = shutil.which(name)
                self.assertIsNotNone(executable, f'required host utility missing: {name}')
                (commands/name).symlink_to(executable)
            self.assertIsNone(shutil.which('cmp', path=str(commands)))
            return subprocess.run([str(commands/'bash'), '-c', code, 'fixture', str(source_path), str(target)],
                                  env={**os.environ, 'PATH': str(commands)},
                                  capture_output=True, text=True, timeout=3)

    def test_staging_replaces_link_with_exact_4755_copy_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source'; target = root/'target'
            source.write_bytes(b'authenticated helper fixture'); source.chmod(0o755); target.symlink_to(source)
            result = self.run_stage(source, target)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.stat().st_mode & 0o7777, 0o4755)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertEqual(source.stat().st_mode & 0o7777, 0o755)
            self.assertNotEqual(source.stat().st_ino, target.stat().st_ino)

    def test_actual_symlink_farm_construction_preserves_semantic_source_identity(self):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial-prepare.sh'
        # Exercise the exact construction that failed in the VM. cp -as retains
        # the source /./ spelling in its links; a hand-created link missed this.
        construction = next(line for line in script.read_text().splitlines() if line.startswith('cp -as '))
        construction = construction.replace('/run/original-bin/.', '"$1/."').replace('/run/session-bin/', '"$2/"')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = root/'original'; staged = root/'staged'
            original.mkdir(); staged.mkdir()
            source = original/'fusermount3'; source.write_bytes(b'helper'); source.chmod(0o755)
            subprocess.run(['bash', '-c', construction, 'fixture', str(original), str(staged)],
                           capture_output=True, text=True, check=True, timeout=3)
            target = staged/'fusermount3'
            self.assertEqual(target.resolve(), source)
            self.assertIn('/./', os.readlink(target))
            result = self.run_stage(source, target)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(), b'helper')
            self.assertEqual(target.stat().st_mode & 0o7777, 0o4755)
            self.assertEqual(source.stat().st_mode & 0o7777, 0o755)

    def test_wrong_destination_is_refused_even_with_same_bytes_or_inode(self):
        for hardlink in [False, True]:
            with self.subTest(hardlink=hardlink), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); source = root/'source'; target = root/'target'; other = root/'other'
                source.write_bytes(b'helper'); source.chmod(0o755)
                if hardlink: os.link(source, other)
                else: other.write_bytes(b'helper'); other.chmod(0o755)
                target.symlink_to(other)
                result = self.run_stage(source, target)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertTrue(target.is_symlink())
                self.assertEqual(target.resolve(), other)
                self.assertEqual(source.stat().st_mode & 0o7777, 0o755)
                self.assertEqual(other.stat().st_mode & 0o7777, 0o755)

    def test_repeated_staging_refuses_to_overwrite_existing_regular_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source'; target = root/'target'
            source.write_bytes(b'helper'); source.chmod(0o755); target.symlink_to(source)
            result = self.run_stage(source, target, repeat=True)
            self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(), b'helper')
            self.assertEqual(target.stat().st_mode & 0o7777, 0o4755)

    def test_invalid_source_leaves_original_link_untouched(self):
        for mode in ['missing', 'directory', 'symlink', 'empty']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); source = root/'source'; target = root/'target'
                if mode == 'directory': source.mkdir()
                elif mode == 'symlink': source.symlink_to('/bin/true')
                elif mode == 'empty': source.touch(); source.chmod(0o755)
                target.symlink_to(source)
                result = self.run_stage(source, target)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertTrue(target.is_symlink())

    def test_streamed_identity_rejects_hash_failures_and_corrupt_copy(self):
        for fault, expected in [('source', 42), ('copy', 43), ('corrupt', 1)]:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); source = root/'source'; target = root/'target'
                source.write_bytes(b'helper'); source.chmod(0o755); target.symlink_to(source)
                result = self.run_stage(source, target, hash_fault=fault)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                self.assertEqual(source.read_bytes(), b'helper')
                self.assertEqual(source.stat().st_mode & 0o7777, 0o755)

    def test_ownership_failure_does_not_apply_setuid_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source'; target = root/'target'
            source.write_bytes(b'helper'); source.chmod(0o755); target.symlink_to(source)
            result = self.run_stage(source, target, ownership_status=42)
            self.assertEqual(result.returncode, 42, result.stdout+result.stderr)
            self.assertFalse(target.stat().st_mode & 0o4000)


class ClientLog(unittest.TestCase):
    def test_actual_drainer_bounds_storage_without_killing_writer(self):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh'
        function = re.search(r'^start_log\(\) \{.*?^\}', script.read_text(), re.M | re.S).group()
        with tempfile.TemporaryDirectory() as directory:
            code = function + r'''
HOME=$1; readers=()
start_log client
python3 -c 'import sys;sys.stdout.write(("fixture"*100+"\n")*5000)' > "$HOME/client.pipe"
producer=$?
wait "${readers[0]}"
exit "$producer"
'''
            result = subprocess.run(['bash', '-c', code, 'fixture', directory],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((Path(directory)/'client.log').stat().st_size, 1048576)

    def drain_denial(self, payload):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh'
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', script.read_text(), re.M | re.S))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'input').write_bytes(payload)
            code = functions + r"""
HOME=$1; readers=()
start_log denial
cat "$HOME/input" > "$HOME/denial.pipe"
producer=$?
wait "${readers[0]}"; reader=$?
[[ $producer == 0 ]] || exit 99
exit "$reader"
"""
            result = subprocess.run(['bash', '-c', code, 'fixture', directory],
                                    capture_output=True, timeout=5)
            return result.returncode, (root/'denial.log').read_text()

    @staticmethod
    def session_parser():
        spec = importlib.util.spec_from_file_location('drm_log_fixture', RUNNER.with_name('test-qemu-virtio-drm.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module.session_result

    def test_terminal_counters_survive_verbose_head_cap(self):
        payload = b'diagnostic trace\n'*70000
        payload += b'independently clocked Flutter KMS session complete raster_frames=80 output_page_flips=79\n'
        rc, log = self.drain_denial(payload)
        self.assertEqual(rc, 0)
        self.assertLessEqual(len(log.encode()), 1048576 + 65536 + 256)
        self.assertEqual(self.session_parser()(log)['status'], 'PASS')

    def test_every_parser_render_error_survives_head_cap(self):
        parser = self.session_parser()
        errors = next(c for c in parser.__code__.co_consts if isinstance(c, tuple)
                      and 'required Flutter native fence export failed' in c)
        for error in errors:
            with self.subTest(error=error):
                rc, log = self.drain_denial(b'diagnostic trace\n'*70000 + error.encode() + b'\n'
                    + b'independently clocked Flutter KMS session complete raster_frames=80 output_page_flips=79\n')
                self.assertEqual(rc, 0)
                self.assertIn(error, parser(log)['render_errors'])
                self.assertEqual(parser(log)['status'], 'FAIL')

    def test_ansi_normalization_matches_actual_session_parser_after_cap(self):
        parser = self.session_parser()
        errors = next(c for c in parser.__code__.co_consts if isinstance(c, tuple)
                      and 'required Flutter native fence export failed' in c)
        summary = 'independently clocked Flutter KMS session complete raster_frames=80 output_page_flips=79'
        for error in [*errors, None]:
            with self.subTest(error=error):
                # The real parser strips ANSI at arbitrary boundaries, not just
                # around whole tracing fields. Exercise that same contract.
                tail = ''.join(c+'\x1b[0m' for c in (error or summary))+'\n'
                if error: tail += summary+'\n'
                payload = b'diagnostic trace\n'*70000 + tail.encode()
                rc, log = self.drain_denial(payload)
                self.assertEqual(rc, 0)
                self.assertEqual(parser(log), parser(payload.decode()))

    def test_diagnostic_overflow_fails_after_draining_writer(self):
        rc, log = self.drain_denial(b'diagnostic trace\n'*70000 + b'ERROR repeated failure\n'*10000)
        self.assertEqual(rc, 42)
        self.assertLessEqual(len(log.encode()), 1048576 + 65536 + 256)
        self.assertIn('FAIL Denial diagnostic log overflow', log)

    def test_duplicate_terminal_counters_remain_a_failure(self):
        line = b'independently clocked Flutter KMS session complete raster_frames=80 output_page_flips=79\n'
        rc, log = self.drain_denial(line + b'diagnostic trace\n'*70000 + line)
        self.assertEqual(rc, 0)
        self.assertEqual(self.session_parser()(log)['status'], 'FAIL')


class ClientExit(unittest.TestCase):
    def run_stop(self, first_exit, phase="stop"):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh'
        source = script.read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        # Exercise generic production signal cleanup with real children/waits.
        # FootClose executes the normal production launch and stop blocks.
        stop = 'stop_all_owned stop\n'
        if phase == 'readiness':
            stop = 'require_running foot\n'
        elif phase == 'cleanup':
            stop = 'exit 37\n'
        elif phase == 'interrupt':
            stop = "trap 'exit 143' TERM\nkill -TERM $$\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['denial', 'foot', 'mousepad']:
                (root/f'{name}.log').touch()
            child = 'sleep 30' if first_exit is None else f'exit {first_exit}'
            code = 'set -euo pipefail\n' + functions + r'''
HOME=$1; readers=(); launcher=''; foot=''; editor=''
trap finish EXIT
bash -c "$2" & foot=$!
sleep 30 & editor=$!
sleep 30 & launcher=$!
printf '%s\n' "$foot" "$editor" "$launcher" > "$HOME/pids"
# Ensure the deliberately early child has exited before the stop request.
if [[ $3 == early ]]; then wait "$foot" || :; fi
''' + stop
            result = subprocess.run(['bash', '-c', code, 'fixture', directory, child,
                                     'live' if first_exit is None else 'early'],
                                    capture_output=True, text=True, timeout=5)
            for pid in map(int, (root/'pids').read_text().split()):
                self.assertFalse(live(pid), f'owned process {pid} left running')
            return result

    def test_early_exit_records_status_and_reaps_other_clients(self):
        for status in [0, 42, 124]:
            with self.subTest(status=status):
                result = self.run_stop(status)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertRegex(result.stdout, rf'process=foot phase=stop .*status={status}(?: |$)')
                self.assertIn('process=editor phase=stop', result.stdout)
                self.assertIn('process=launcher phase=stop', result.stdout)

    def test_requested_stop_records_all_client_statuses(self):
        result = self.run_stop(None)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        for name in ['foot', 'editor', 'launcher']:
            self.assertRegex(result.stdout, rf'process={name} phase=stop .*status=143(?: |$)')


    def test_readiness_retains_early_deadline_and_cleans_remaining_children(self):
        result = self.run_stop(124, 'readiness')
        self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
        self.assertRegex(result.stdout, r'process=foot phase=readiness .*status=124 ')
        for name in ['editor', 'launcher']:
            self.assertRegex(result.stdout, rf'process={name} phase=cleanup .*status=143 ')

    def test_failure_cleanup_preserves_original_failure_and_child_status(self):
        result = self.run_stop(42, 'cleanup')
        self.assertEqual(result.returncode, 37, result.stdout+result.stderr)
        self.assertRegex(result.stdout, r'process=foot phase=cleanup .*status=42 ')
        for name in ['editor', 'launcher']:
            self.assertRegex(result.stdout, rf'process={name} phase=cleanup .*status=143 ')

    def test_interruption_captures_every_child_and_retains_signal_status(self):
        result = self.run_stop(None, 'interrupt')
        self.assertEqual(result.returncode, 143, result.stdout+result.stderr)
        for name in ['foot', 'editor', 'launcher']:
            self.assertRegex(result.stdout, rf'process={name} phase=cleanup .*status=143 ')


class FootClose(unittest.TestCase):
    def run_close(self, mode='success'):
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh').read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        launch = source.split('editor=$!\n', 1)[1].split('for ((i=0;i<160;i++)); do', 1)[0]
        stop = source.split('sleep 3\n', 1)[1].split('# Require successful enumeration', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); commands = root/'bin'; commands.mkdir()
            # Thin external-program seam: execute the actual supplied child
            # command, without a compositor. Do not model its FIFO protocol.
            wrapper = {
                'dead_reader': 'exec sleep 30',
                'early0': 'exit 0', 'early124': 'exit 124', 'early230': 'exit 230',
                'nonzero': '"$@"; exit 42',
                'exit_timeout': '"$@"; exec sleep 30',
            }.get(mode, 'exec "$@"')
            (commands/'foot').write_text('#!/usr/bin/bash\n(($#)) || exit 230\n'+wrapper+'\n')
            (commands/'foot').chmod(0o755)
            (root/'foot.pipe').touch()
            for name in ['denial', 'foot', 'mousepad']:
                (root/f'{name}.log').touch()
            code = 'set -euo pipefail\n' + functions + r'''
HOME=$1; MODE=$2; export HOME; export PATH=$HOME/bin:$PATH
readers=(); launcher=''; foot=''; editor=''; foot_close_owned=0
foot_close_fifo=$HOME/foot-close.pipe
trap finish EXIT
trap 'exit 143' TERM
sleep 30 & editor=$!
sleep 30 & launcher=$!
''' + launch + r'''
printf '%s\n' "$foot" "$editor" "$launcher" > "$HOME/pids"
if [[ $MODE == early* ]]; then wait "$foot" || :; fi
'''
            if mode == 'wrong_token':
                stop = r'''
timeout -k 1 3 /usr/bin/bash -c 'printf "WRONG\n" > "$1"' fixture "$foot_close_fifo"
wait "$foot"
'''
            elif mode == 'interrupt':
                stop = 'kill -TERM $$\n'
            code += stop
            result = subprocess.run(['bash', '-c', code, 'fixture', directory, mode],
                                    capture_output=True, text=True, timeout=12)
            for pid in map(int, (root/'pids').read_text().split()):
                self.assertFalse(live(pid), f'owned process {pid} left running')
            self.assertFalse((root/'foot-close.pipe').exists())
            return result, (root/'foot.pipe').read_text()

    def test_actual_launch_and_stop_use_normal_child_exit_without_term(self):
        result, child_output = self.run_close()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertRegex(result.stdout, r'process=foot phase=normal-close .*status=0 term_sent=no')
        self.assertNotRegex(result.stdout, r'process=foot .*term_sent=yes')
        self.assertIn('PASS controlled terminal child exit requested', child_output)
        self.assertIn('process=editor phase=stop', result.stdout)
        self.assertIn('process=launcher phase=stop', result.stdout)


    def test_wrong_token_is_rejected_by_actual_child_and_all_processes_cleaned(self):
        result, child_output = self.run_close('wrong_token')
        self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
        self.assertNotIn('PASS controlled terminal child exit requested', child_output)
        self.assertIn('process=editor phase=cleanup', result.stdout)
        self.assertIn('process=launcher phase=cleanup', result.stdout)

    def test_dead_reader_and_nonterminating_terminal_have_real_bounded_timeouts(self):
        for mode in ['dead_reader', 'exit_timeout']:
            with self.subTest(mode=mode):
                result, _ = self.run_close(mode)
                self.assertEqual(result.returncode, 124, result.stdout+result.stderr)
                self.assertIn('process=editor phase=cleanup', result.stdout)
                self.assertIn('process=launcher phase=cleanup', result.stdout)

    def test_early_exit_and_nonzero_normal_close_remain_failures(self):
        for mode, expected in [('early0', 1), ('early124', 1), ('early230', 1), ('nonzero', 42)]:
            with self.subTest(mode=mode):
                result, _ = self.run_close(mode)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                self.assertIn('process=editor phase=cleanup', result.stdout)
                self.assertIn('process=launcher phase=cleanup', result.stdout)
                self.assertNotIn('PASS Foot exited normally', result.stdout)

    def test_interruption_cleans_processes_and_owned_fifo(self):
        result, _ = self.run_close('interrupt')
        self.assertEqual(result.returncode, 143, result.stdout+result.stderr)
        self.assertIn('process=editor phase=cleanup', result.stdout)
        self.assertIn('process=launcher phase=cleanup', result.stdout)

    def test_fresh_fifo_mode_and_preexisting_path_refusal(self):
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh').read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        for existing in [False, True]:
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as directory:
                fifo = Path(directory)/'close'
                if existing: os.mkfifo(fifo, 0o600)
                code = functions + r'''
foot_close_fifo=$1; foot_close_owned=0
prepare_foot_close || exit $?
[[ -p $foot_close_fifo && $(stat -c %a "$foot_close_fifo") == 600 ]] || exit 2
remove_foot_close
'''
                result = subprocess.run(['bash', '-c', code, 'fixture', str(fifo)],
                                        capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 1 if existing else 0, result.stdout+result.stderr)
                self.assertEqual(fifo.exists(), existing)


class EditorTransport(unittest.TestCase):
    script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-editor.sh'

    def test_actual_awk_preserves_attribution_and_caps_both_outputs(self):
        for data in [b'one\ntwo\n', b'x'*1024+b'\n' + (b'bounded line\n'*100000)]:
            with self.subTest(size=len(data)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); fifo = root/'wire'; os.mkfifo(fifo)
                with (root/'wire.log').open('wb') as wire:
                    reader = subprocess.Popen(['cat', str(fifo)], stdout=wire)
                    try:
                        result = subprocess.run(['bash', '-c', 'source "$1"; drain_editor_protocol "$2"',
                                                 'fixture', str(self.script), str(fifo)],
                                                input=data, capture_output=True, timeout=3)
                        reader.wait(timeout=3)
                    finally:
                        if reader.poll() is None: reader.kill(); reader.wait()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, data[:1048576])
                expected = b''.join(b'EDITOR_WAYLAND '+line+b'\n' for line in data.splitlines())[:1048576]
                self.assertEqual((root/'wire.log').read_bytes(), expected)

    def test_failed_foot_close_never_launches_editor(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'foot.log').write_text('xdg_toplevel.configure\n')
            code = r'''source "$1"
HOME=$2; launcher=fixture; foot=fixture
prepare_foot_close(){ :; }; launch_foot(){ :; }
require_running(){ :; }; close_foot_normally(){ return 42; }
run_authenticated_editor
'''
            result=subprocess.run(['bash','-c',code,'fixture',str(self.script),str(root)],
                                  capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,42,result.stdout+result.stderr)
            self.assertFalse((root/'rog5-text-probe.txt').exists())


class AppsPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('apps_runner_fixture', RUNNER)
        cls.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.runner)

    def test_settings_probe_staging_checks_architecture_and_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work); source = root/'probe.so'; stage = root/'stage'; stage.mkdir()
            header = bytearray(64); header[:7] = b'\x7fELF\x02\x01\x01'
            header[16:20] = b'\x03\x00\xb7\x00'
            source.write_bytes(header + b'fixture shared object')
            target = self.runner.stage_settings_sync_diagnostic(source, stage)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)
            with self.assertRaises(FileExistsError):
                self.runner.stage_settings_sync_diagnostic(source, stage)
            target.unlink()
            for invalid in [b'not ELF', bytes(header[:16])+b'\x02\x00'+bytes(header[18:]),
                            bytes(header[:18])+b'\x3e\x00'+bytes(header[20:])]:
                source.write_bytes(invalid)
                with self.assertRaisesRegex(ValueError, 'ARM64 shared ELF'):
                    self.runner.stage_settings_sync_diagnostic(source, stage)
                self.assertFalse(target.exists())
            alias = root/'alias.so'; alias.symlink_to(source)
            with self.assertRaises(ValueError):
                self.runner.stage_settings_sync_diagnostic(alias, stage)

    def test_channel_is_duplex_with_single_log_writer_and_fixed_port(self):
        channel = self.runner.observation_channel(True)
        self.assertEqual(channel, ['-chardev', 'socket,id=apps,path=/observe/apps.sock,server=on,wait=off',
                                  '-device', 'virtserialport,chardev=apps,name=rog5.apps,nr=1'])
        self.assertIn('file,id=editor,path=/observe/editor.log', self.runner.observation_channel(False))

    def test_cli_refuses_incomplete_or_conflicting_observation_before_effects(self):
        required = [value for name in ['runtime-view', 'runtime-receipt', 'kernel', 'qemu-image',
                    'toolchain-image', 'libc', 'libloading', 'output'] for value in ['--'+name, '/unused']]
        combined = ['--session-archive', '/unused', '--session-receipt', '/unused', '--host-render-node', '/unused']
        for extra in [['--observe-apps'], combined+['--observe-apps'],
                      combined+['--observe-apps', '--launcher-reference', '/unused'],
                      combined+['--observe-editor', '--observe-apps'],
                      ['--launcher-reference', '/unused'], ['--evidence-writer', '/unused'],
                      ['--settings-sync-diagnostic', '/unused']]:
            with self.subTest(extra=extra):
                result = subprocess.run([sys.executable, str(RUNNER), *required, *extra],
                                        capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 2)
                self.assertRegex(result.stderr, 'observation requires|not allowed with argument|settings-sync-diagnostic requires observe-apps')

    def test_close_only_cli_and_factory_preserve_explicit_scope(self):
        required = [v for n in ['runtime-view', 'runtime-receipt', 'kernel', 'qemu-image',
                    'toolchain-image', 'libc', 'libloading', 'output'] for v in ['--'+n, '/unused']]
        combined = ['--session-archive','/unused','--session-receipt','/unused','--host-render-node','/unused']
        apps = ['--observe-apps','--launcher-reference','/unused','--evidence-writer','/unused']
        for extra in ([],combined,combined+['--observe-editor'],combined+apps+['--automatic-caret'],
                      combined+apps+['--automatic-caret','--bottom-caret'],combined+apps+['--startup-only']):
            with self.subTest(extra=extra), patch.object(sys, 'argv',[str(RUNNER),*required,*extra,'--close-only']), \
                    patch.object(self.runner, 'install_handlers') as effects, patch('sys.stderr',new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as status:self.runner.main()
                self.assertEqual(status.exception.code,2);effects.assert_not_called()
        with patch.object(sys,'argv',[str(RUNNER),*required,*combined,*apps,'--close-only']), \
                patch.object(self.runner,'install_handlers',side_effect=RuntimeError('accepted close mode')):
            with self.assertRaisesRegex(RuntimeError,'accepted close mode'):self.runner.main()
        calls=[]
        self.runner.session_observer(SimpleNamespace(LiveApps=lambda *a,**kw:calls.append(kw)),
            SimpleNamespace(observe_apps=True,automatic_caret=False,close_only=True,launcher_reference='reference'),
            'directory','owned','token')
        self.assertEqual(calls,[{'automatic_caret':False,'close_only':True}])

    def test_automatic_caret_requires_apps_before_any_effects(self):
        required = [value for name in ['runtime-view', 'runtime-receipt', 'kernel', 'qemu-image',
                    'toolchain-image', 'libc', 'libloading', 'output'] for value in ['--'+name, '/unused']]
        for extra in [[], ['--observe-editor', '--session-archive', '/unused',
                          '--session-receipt', '/unused', '--host-render-node', '/unused']]:
            with self.subTest(extra=extra):
                result = subprocess.run([sys.executable, str(RUNNER), *required, *extra,
                                         '--automatic-caret'], capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 2)
                self.assertIn('automatic-caret requires observe-apps', result.stderr)

    def test_production_observer_factory_forwards_explicit_policy(self):
        from types import SimpleNamespace
        calls = []
        module = SimpleNamespace(LiveApps=lambda *a, **kw: calls.append((a, kw)),
                                 LiveEditor=lambda *a, **kw: calls.append((a, kw)))
        for automatic in (False, True):
            args = SimpleNamespace(observe_apps=True, launcher_reference='reference', automatic_caret=automatic)
            self.runner.session_observer(module, args, 'directory', 'owned', 'token')
            self.assertEqual(calls[-1], (('directory', 'owned', 'token', 'reference'),
                                        {'automatic_caret': automatic}))
        self.runner.session_observer(module, SimpleNamespace(observe_apps=False),
                                     'directory', 'owned', 'token')
        self.assertEqual(calls[-1], (('directory', 'owned'), {}))

    def test_bottom_caret_cli_requires_both_optins_before_effects(self):
        required = [value for name in ['runtime-view', 'runtime-receipt', 'kernel', 'qemu-image',
                    'toolchain-image', 'libc', 'libloading', 'output'] for value in ['--'+name, '/unused']]
        combined = ['--session-archive', '/unused', '--session-receipt', '/unused', '--host-render-node', '/unused']
        apps = ['--observe-apps', '--launcher-reference', '/unused', '--evidence-writer', '/unused']
        for extra in ([], combined+['--observe-editor'], combined+apps):
            with self.subTest(extra=extra), patch.object(sys, 'argv', [str(RUNNER), *required, *extra, '--bottom-caret']), \
                    patch.object(self.runner, 'install_handlers') as effects, patch('sys.stderr', new_callable=io.StringIO) as stderr:
                with self.assertRaises(SystemExit) as exit_status:
                    self.runner.main()
                self.assertEqual(exit_status.exception.code, 2)
                self.assertIn('bottom-caret requires observe-apps and automatic-caret', stderr.getvalue())
                effects.assert_not_called()
        with patch.object(sys, 'argv', [str(RUNNER), *required, *combined, *apps, '--automatic-caret', '--bottom-caret']), \
                patch.object(self.runner, 'install_handlers', side_effect=RuntimeError('accepted CLI fixture')):
            with self.assertRaisesRegex(RuntimeError, 'accepted CLI fixture'):
                self.runner.main()

    def test_observer_factory_forwards_bottom_caret_only_when_selected(self):
        calls = []
        module = SimpleNamespace(LiveApps=lambda *a, **kw: calls.append((a, kw)))
        for bottom in (False, True):
            args = SimpleNamespace(observe_apps=True, launcher_reference='reference', automatic_caret=True, bottom_caret=bottom)
            self.runner.session_observer(module, args, 'directory', 'owned', 'token')
            expected = {'automatic_caret': True}
            if bottom:
                expected['bottom_caret'] = True
            self.assertEqual(calls[-1], (('directory', 'owned', 'token', 'reference'), expected))

    @staticmethod
    def actual_apps_block(marker):
        # Execute complete production branches, replacing expensive build/VM
        # surroundings, not the policy or staged-file implementation.
        tree = ast.parse(RUNNER.read_text())
        candidates = [node for node in ast.walk(tree) if isinstance(node, ast.If)
                      and ast.unparse(node.test) == 'args.observe_apps'
                      and marker in ast.unparse(node)]
        if len(candidates) != 1:
            raise AssertionError('production apps branch is absent or ambiguous')
        return compile(ast.Module(body=candidates, type_ignores=[]), str(RUNNER), 'exec')

    def test_bottom_caret_input_lock_is_explicit_optin(self):
        block = self.actual_apps_block('source_names_extra')
        for observe, bottom in ((False, False), (True, False), (True, True)):
            with self.subTest(observe=observe, bottom=bottom):
                inputs = []
                scope = dict(args=SimpleNamespace(observe_apps=observe, bottom_caret=bottom,
                    launcher_reference=Path('/fixture/reference'), evidence_writer=Path('/fixture/writer')),
                    input_files=inputs, SOURCES=self.runner.SOURCES, REPO=self.runner.REPO,
                    regular=lambda path: path)
                exec(block, scope)
                caret = self.runner.REPO/'scripts/host/qemu-caret-protocol.py'
                self.assertEqual(inputs.count(caret), int(observe and bottom))
                if observe:
                    self.assertIn(self.runner.REPO/'scripts/host/qemu-launcher-protocol.py', inputs)
                else:
                    self.assertEqual(inputs, [])

    def test_bottom_caret_marker_is_staged_and_hashed_only_optin(self):
        import uuid
        block = self.actual_apps_block('bottom-caret-probe')
        for bottom in (False, True):
            with self.subTest(bottom=bottom), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                stage = root/'initramfs'
                (stage/'stage').mkdir(parents=True)
                writer = root/'writer'
                writer.write_bytes(b'fixture executable')
                result = {'outputs': {}}
                scope = dict(args=SimpleNamespace(observe_apps=True, bottom_caret=bottom, evidence_writer=writer),
                             scripts={}, stage=stage, uuid=uuid, shutil=shutil, result=result,
                             identity=self.runner.identity)
                exec(block, scope)
                marker = stage/'stage/bottom-caret-probe'
                self.assertEqual(marker.exists(), bottom)
                self.assertEqual('stage/bottom-caret-probe' in result['outputs'], bottom)
                if bottom:
                    self.assertEqual(marker.read_bytes(), b'1\n')
                    self.assertEqual(result['outputs']['stage/bottom-caret-probe'], self.runner.identity(marker))
                self.assertEqual((stage/'stage/apps-probe').read_bytes(), b'1\n')
                self.assertRegex((stage/'stage/apps-observe-token').read_text(), r'^ROG5_APPS_DONE_[0-9a-f]{32}\n$')

    def test_reference_semantics_and_guest_architecture_checked(self):
        spec = importlib.util.spec_from_file_location('editor_png_fixture', RUNNER.with_name('test-qemu-logind-editor.py'))
        fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); png = root/'reference.png'; writer = root/'writer'
            png.write_bytes(fixture.PNG)
            elf = b'\x7fELF\x02\x01\x01'+b'\0'*11+b'\xb7\0'
            writer.write_bytes(elf)
            self.runner.validate_apps_inputs(png, writer)
            for data in [b'', elf[:18]+b'\x3e\0', b'#!/bin/sh\nexit 0\n', elf.replace(b'ELF', b'BAD')]:
                writer.write_bytes(data)
                with self.assertRaisesRegex(ValueError, 'ARM64 ELF'):
                    self.runner.validate_apps_inputs(png, writer)
            writer.write_bytes(elf); png.write_bytes(b'not a PNG')
            with self.assertRaises(ValueError): self.runner.validate_apps_inputs(png, writer)


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


class StartupOnly(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('startup_runner_fixture', RUNNER)
        self.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.runner)

    def test_cli_requires_combined_inputs_and_excludes_ui_observers(self):
        required = [v for n in ['runtime-view', 'runtime-receipt', 'kernel', 'qemu-image',
                    'toolchain-image', 'libc', 'libloading', 'output'] for v in ['--'+n, '/unused']]
        combined = ['--session-archive', '/unused', '--session-receipt', '/unused', '--host-render-node', '/unused']
        for extra in ([], combined+['--observe-editor'], combined+['--observe-apps']):
            with self.subTest(extra=extra), patch.object(sys, 'argv', [str(RUNNER), *required, *extra, '--startup-only']), \
                    patch.object(self.runner, 'install_handlers') as effects, patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as status: self.runner.main()
                self.assertEqual(status.exception.code, 2); effects.assert_not_called()
        with patch.object(sys, 'argv', [str(RUNNER), *required, *combined, '--startup-only']), \
                patch.object(self.runner, 'install_handlers', side_effect=RuntimeError('accepted startup CLI')):
            with self.assertRaisesRegex(RuntimeError, 'accepted startup CLI'): self.runner.main()

    def serial(self):
        units = self.runner.STARTUP_UNITS
        records = ['Id='+unit+'\nLoadState=loaded\nActiveState=active\n'
                   'ActiveEnterTimestampMonotonic=1000000\nInactiveExitTimestampMonotonic=800000\n'
                   'ConditionResult=yes\nExecMainStartTimestampMonotonic=800000\n'
                   'ExecMainExitTimestampMonotonic=950000' for unit in units]
        data = '\n\n'.join(records).encode()
        return ('OBSERVE pid1-handoff boottime=12.34\n'
                'DIAGNOSTIC_UNIT_TIMINGS status=read bytes='+str(len(data))+' hex='+data.hex()+'\n'
                'PASS startup-only authenticated readiness; Denial NOT RUN\n')

    def test_actual_shell_collects_fixed_properties_and_encodes_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); tool = root/'systemctl'
            data = 'Id=ldconfig.service\n' + self.runner.SUCCESS + '\n'
            tool.write_text('#!/bin/bash\nprintf \'%s\\n\' "$@" > "$ARGUMENTS"\ncat "$DATA"\n')
            tool.chmod(0o755); (root/'data').write_text(data)
            env = {'PATH':str(root)+':/usr/bin:/bin', 'LANG':'C',
                   'ARGUMENTS':str(root/'arguments'), 'DATA':str(root/'data'), 'TMPDIR':str(root)}
            result = subprocess.run(['bash','-c', 'set -euo pipefail; source "$1"; logind_startup_timings',
                                     'fixture', str(RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh')],
                                    env=env, capture_output=True, text=True, timeout=12)
            self.assertEqual(result.returncode, 0, result.stderr)
            packet = re.search(r'bytes=(\d+) hex=([0-9a-f]+)', result.stdout)
            self.assertEqual(bytes.fromhex(packet[2]).decode(), data)
            self.assertNotIn(self.runner.SUCCESS, result.stdout)
            arguments = (root/'arguments').read_text().splitlines()
            self.assertEqual(arguments[:2], ['show','--no-pager'])
            self.assertEqual(arguments[-9:], list(self.runner.STARTUP_UNITS))
            self.assertIn('ExecMainExitTimestampMonotonic', arguments)
            for code in (42, 124):
                tool.write_text('#!/bin/bash\ncat \"$DATA\"\nexit '+str(code)+'\n')
                failed = subprocess.run(['bash','-c', 'set -euo pipefail; source "$1"; logind_startup_timings',
                                          'fixture', str(RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh')],
                                         env=env, capture_output=True, text=True, timeout=12)
                self.assertEqual(failed.returncode, code)
                self.assertNotIn('status=read', failed.stdout)
                packet = re.search(r'bytes=(\d+) hex=([0-9a-f]+)', failed.stdout)
                self.assertIsNotNone(packet, 'partial timing bytes discarded')
                self.assertEqual(bytes.fromhex(packet[2]).decode(), data)

    def test_buffered_partial_stdout_survives_real_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'buffered.c'
            source.write_text('#include <stdio.h>\n#include <unistd.h>\nint main(void){printf("Id=ldconfig.service\\n");while(1)pause();}\n')
            subprocess.run(['cc',str(source),'-o',str(root/'systemctl')],check=True,capture_output=True,timeout=10)
            timeout=root/'timeout'
            timeout.write_text('#!/bin/bash\nexec /usr/bin/timeout -k .1 .2 "${@:4}"\n');timeout.chmod(0o755)
            env=dict(os.environ,PATH=str(root)+':/usr/bin:/bin',TMPDIR=str(root))
            result=subprocess.run(['bash','-c','source "$1"; logind_startup_timings','fixture',
                str(RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh')],env=env,capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,124,result.stdout+result.stderr)
            packet=re.search(r'DIAGNOSTIC_UNIT_TIMINGS status=failed code=124 bytes=(\d+) hex=([0-9a-f]+)',result.stdout)
            self.assertIsNotNone(packet,'buffered partial properties disappeared when the writer was killed')
            self.assertEqual(bytes.fromhex(packet[2]).decode(),'Id=ldconfig.service\n')

    def test_query_stderr_is_bounded_encoded_and_never_session_proof(self):
        for overflow in (False,True):
            with self.subTest(overflow=overflow),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);tool=root/'systemctl'
                if overflow:
                    tool.write_text('#!/bin/bash\nhead -c 2097152 /dev/zero >&2\n')
                else:
                    tool.write_text('#!/bin/bash\nprintf "Id=ldconfig.service\\n"\nprintf "'+self.runner.SUCCESS+'\\n" >&2\nexit 42\n')
                tool.chmod(0o755)
                env=dict(os.environ,PATH=str(root)+':/usr/bin:/bin',TMPDIR=str(root))
                result=subprocess.run(['bash','-c','source "$1"; logind_startup_timings','fixture',
                    str(RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh')],env=env,capture_output=True,text=True,timeout=4)
                self.assertNotEqual(result.returncode,0)
                self.assertLess(len(result.stdout)+len(result.stderr),70000)
                self.assertNotIn(self.runner.SUCCESS,result.stdout+result.stderr)
                packet=re.search(r'DIAGNOSTIC_UNIT_QUERY code=(\d+) bytes=(\d+) hex=([0-9a-f]*)',result.stdout)
                self.assertIsNotNone(packet)
                self.assertLessEqual(int(packet[2]),16384)
                if not overflow:
                    self.assertEqual(result.returncode,42)
                    self.assertEqual(bytes.fromhex(packet[3]).decode(),self.runner.SUCCESS+'\n')
                self.assertEqual(list(root.glob('rog5-unit-query.*')),[])

    def test_encoder_failure_is_propagated_and_scratch_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,body in [('systemctl','printf "Id=ldconfig.service\\n"'),('od','exit 41')]:
                p=root/name;p.write_text('#!/bin/bash\n'+body+'\n');p.chmod(0o755)
            result=subprocess.run(['bash','-c','source "$1"; if logind_startup_timings; then exit 0; else exit $?; fi','fixture',
                str(RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh')],
                env=dict(os.environ,PATH=str(root)+':/usr/bin:/bin',TMPDIR=str(root)),capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,41,result.stdout+result.stderr)
            self.assertNotIn('status=read',result.stdout)
            self.assertEqual(list(root.glob('rog5-unit-query.*')),[])

    def test_actual_user_dispatch_skips_denial_only_for_explicit_marker(self):
        source = (RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-user.sh').read_text()
        branch = source[source.index('if [[ -f /run/startup-only ]]; then'):]
        branch = branch.replace('/usr/bin/bash /run/logind-denial.sh', 'denial_fixture')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            branch = branch.replace('/run/startup-only', str(root/'startup-only'))
            branch = branch.replace('/run/session-sha256', str(root/'session-sha256'))
            code = 'set -euo pipefail; denial_fixture(){ echo DENIAL_CALLED; };\n'+branch
            def run(): return subprocess.run(['bash','-c',code],capture_output=True,text=True,timeout=3)
            (root/'session-sha256').touch()
            self.assertEqual(run().stdout, 'DENIAL_CALLED\n')
            (root/'startup-only').touch()
            result = run(); self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Denial NOT RUN',result.stdout); self.assertNotIn('DENIAL_CALLED',result.stdout)
            (root/'session-sha256').unlink()
            self.assertNotEqual(run().returncode,0)

    def test_actual_timing_parser_retains_all_unit_clocks(self):
        result = self.runner.startup_result(self.serial())
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['pid1_handoff_boottime_seconds'], 12.34)
        self.assertEqual(set(result['units']), set(self.runner.STARTUP_UNITS))
        self.assertEqual(result['units']['ldconfig.service']['ExecMainExitTimestampMonotonic'], 950000)
        self.assertIn('microseconds', result['unit_clock'])

    def test_actual_failed_collector_branch_continues_to_pam(self):
        source = (RUNNER.parents[2]/'tools/qemu-virtio-drm/logind-session.sh').read_text()
        branch = next(line for line in source.splitlines() if line.startswith('if [[ -f /run/startup-only ]'))
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'startup-only'; marker.touch()
            branch = branch.replace('/run/startup-only', str(marker))
            code = 'set -euo pipefail; logind_startup_timings(){ echo QUERY_FAILED; return 124; };\n'+branch+'\necho PAM_CONTINUES'
            result = subprocess.run(['bash','-c',code],capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'QUERY_FAILED\nPAM_CONTINUES\n')

    def test_real_systemd_console_prefix_is_accepted(self):
        framed = '\n'.join(line if line.startswith('OBSERVE pid1-') else 'bash[412]: '+line
                            for line in self.serial().splitlines())+'\n'
        self.assertEqual(self.runner.startup_result(framed)['status'], 'PASS')

    def test_failed_partial_timing_data_never_qualifies(self):
        serial = self.serial().replace('status=read bytes=', 'status=failed code=124 bytes=')
        with self.assertRaises(ValueError): self.runner.startup_result(serial)

    def test_missing_or_duplicate_timing_proof_fails(self):
        serial = self.serial()
        for invalid in ('', serial.split('DIAGNOSTIC_UNIT_TIMINGS')[0], serial+serial,
                        serial.replace('PASS startup-only', 'FAIL startup-only')):
            with self.subTest(invalid=invalid[:40]), self.assertRaises(ValueError):
                self.runner.startup_result(invalid)

    def test_invalid_decoded_unit_state_or_time_fails(self):
        serial = self.serial()
        match = re.search(r'bytes=(\d+) hex=([0-9a-f]+)', serial)
        data = bytes.fromhex(match[2]).decode()
        for changed in (data.replace('LoadState=loaded', 'LoadState=not-found', 1),
                        data.replace('Monotonic=1000000', 'Monotonic=bad', 1),
                        data.replace('Id=ldconfig.service', 'Id=unexpected.service'),
                        data.replace('LoadState=loaded', 'LoadState=loaded\nLoadState=loaded', 1)):
            packet = 'bytes='+str(len(changed.encode()))+' hex='+changed.encode().hex()
            with self.subTest(changed=changed[:40]), self.assertRaises(ValueError):
                self.runner.startup_result(serial[:match.start()]+packet+serial[match.end():])


class TcgMode(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('tcg_runner_fixture', RUNNER)
        self.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.runner)
        self.required = [v for n in ['runtime-view', 'runtime-receipt', 'kernel', 'qemu-image',
                         'toolchain-image', 'libc', 'libloading', 'output'] for v in ['--'+n, '/unused']]

    def parsed(self, options):
        observed = []
        original = self.runner.argparse.ArgumentParser.parse_args
        def capture(parser, *args, **kwargs):
            result = original(parser, *args, **kwargs); observed.append(result); return result
        with patch.object(sys, 'argv', [str(RUNNER), *self.required, *options]), \
                patch.object(self.runner.argparse.ArgumentParser, 'parse_args', capture), \
                patch.object(self.runner, 'install_handlers', side_effect=RuntimeError('CLI accepted')):
            with self.assertRaisesRegex(RuntimeError, 'CLI accepted'): self.runner.main()
        return observed[0]

    def test_default_and_explicit_modes_reach_real_argument_parser(self):
        for options, expected in [([], 'multi'), (['--tcg-thread', 'multi'], 'multi'),
                                  (['--tcg-thread', 'single'], 'single')]:
            with self.subTest(options=options):
                self.assertEqual(self.parsed(options).tcg_thread, expected)

    def test_invalid_mode_rejected_before_effects(self):
        for value in ['invalid', 'single,thread=multi', '']:
            with self.subTest(value=value), patch.object(sys, 'argv',
                    [str(RUNNER), *self.required, '--tcg-thread', value]), \
                    patch.object(self.runner, 'install_handlers') as effects, \
                    patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as status: self.runner.main()
                self.assertEqual(status.exception.code, 2); effects.assert_not_called()

    def command(self, mode, combined):
        # Execute the actual command-construction statements. No rewritten QEMU
        # command model or container/VM execution belongs in this host regression.
        tree = ast.parse(RUNNER.read_text())
        command = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'command' for t in n.targets)
                       and isinstance(n.value, ast.List) and isinstance(n.value.elts[0], ast.Constant)
                       and n.value.elts[0].value == 'podman')
        combined_block = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                              and isinstance(n.test, ast.Name) and n.test.id == 'combined'
                              and n.lineno > command.lineno)
        args = self.parsed(['--tcg-thread', mode]); args.qemu_image = 'pinned-image'
        args.host_render_node = Path('/dev/dri/renderD128')
        env = dict(args=args, combined=combined, name='owned-fixture', runtime=Path('/fixture/runtime'),
                   kernel=Path('/fixture/Image'), output=Path('/fixture/output'), payload=Path('/fixture/payload'))
        exec(compile(ast.Module(body=[command, combined_block], type_ignores=[]), str(RUNNER), 'exec'), env)
        return env['command']

    def test_mode_changes_only_accelerator_not_guest_smp_or_containment(self):
        for combined in (False, True):
            with self.subTest(combined=combined):
                multi = self.command('multi', combined); single = self.command('single', combined)
                changed = [i for i, pair in enumerate(zip(multi, single)) if pair[0] != pair[1]]
                self.assertEqual(len(multi), len(single))
                self.assertEqual(changed, [multi.index('-accel')+1])
                self.assertEqual(single[changed[0]], 'tcg,thread=single')
                self.assertEqual(multi[changed[0]], 'tcg,thread=multi')
                self.assertEqual(single[single.index('-smp')+1], '2' if combined else '1')
                self.assertIn('--network=none', single); self.assertIn('--read-only', single)
                self.assertIn('--cpus=2', single); self.assertIn('--pids-limit=64', single)
                self.assertIn('--memory-swap=2048m' if combined else '--memory-swap=1024m', single)
                self.assertIn('/fixture/runtime:/runtime:ro', single)


if __name__ == '__main__':
    unittest.main()
