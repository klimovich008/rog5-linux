#!/usr/bin/env python3
"""Exercise the real manual runner's process ownership without containers/VMs."""
import os
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


class ExecutableView(unittest.TestCase):
    def restore(self, first=0, second=0, original=None):
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
FIRST=$2; SECOND=$3
/run/original-bin/umount(){ printf 'CALL original %s\n' "$*"; return "$FIRST"; }
/usr/bin/umount(){ printf 'CALL canonical %s\n' "$*"; return "$SECOND"; }
''' + f'restore_needed={restore_state}\n' + exit_trap + '\n' + body
        return subprocess.run(['bash', '-c', code, 'fixture', str(script), str(first), str(second)],
                              capture_output=True, text=True, timeout=3)

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
                self.assertIn('CALL original /usr/bin', result.stdout)
                if not first:
                    self.assertIn('CALL canonical --lazy /run/original-bin', result.stdout)
                else:
                    self.assertNotIn('CALL canonical', result.stdout)


class CacheEnvironment(unittest.TestCase):
    def publish(self, mode='success'):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh'
        source = script.read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        # Real production boundary: cache publication must precede even the
        # mobile entry preflight. Old code executes it without any publication.
        prelaunch = source.split("trap 'exit 130' INT\n", 1)[1]
        prelaunch = prelaunch.split('/usr/bin/denial-mobile-session >', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'schemas').mkdir(); (root/'mime').mkdir()
            if mode != 'missing_schema': (root/'schemas/gschemas.compiled').write_bytes(b'fixture')
            if mode != 'missing_mime': (root/'mime/mime.cache').write_bytes(b'fixture')
            code = 'set -euo pipefail\n' + functions + r'''
export GSETTINGS_SCHEMA_DIR=$1/schemas XDG_DATA_DIRS=$1:/usr/local/share:/usr/share
MODE=$2
# FUSE access is checked separately; this fixture isolates cache publication.
require_fuse_device(){ :; }
# Only external transport is stubbed; production file validation and result
# parsing execute unchanged. No host session bus or manager is contacted.
timeout(){ printf 'TIMEOUT %s\n' "$*" >&2; shift 3; "$@"; }
dbus-update-activation-environment(){
    printf 'IMPORT %s\n' "$*"
    case $MODE in unavailable) return 127;; update_fail) return 69;; deadline) return 124;; esac
}
systemctl(){
    printf 'MANAGER %s\n' "$*" >&2
    [[ $MODE != query_fail ]] || return 42
    [[ $MODE != missing_value ]] || return 0
    printf 'GSETTINGS_SCHEMA_DIR=%s\n' "$GSETTINGS_SCHEMA_DIR"
    if [[ $MODE == mismatch ]]; then printf 'XDG_DATA_DIRS=/wrong\n'
    else printf 'XDG_DATA_DIRS=%s\n' "$XDG_DATA_DIRS"; fi
    [[ $MODE != duplicate ]] || printf 'GSETTINGS_SCHEMA_DIR=%s\n' "$GSETTINGS_SCHEMA_DIR"
    return 0
}
/usr/bin/denial-mobile-session(){ printf 'MOBILE %s\n' "$*"; }
''' + prelaunch
            return subprocess.run(['bash', '-c', code, 'fixture', directory, mode],
                                  capture_output=True, text=True, timeout=3)

    def test_actual_prelaunch_publishes_only_cache_keys_and_verifies_manager(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('IMPORT --systemd GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS', result.stdout)
        self.assertIn('MANAGER --user show-environment', result.stderr)
        self.assertIn('TIMEOUT -k 1 3 dbus-update-activation-environment --systemd GSETTINGS_SCHEMA_DIR XDG_DATA_DIRS', result.stderr)
        self.assertIn('TIMEOUT -k 1 3 systemctl --user show-environment', result.stderr)
        self.assertLess(result.stdout.index('IMPORT '), result.stdout.index('MOBILE --check'))

    def test_missing_caches_prevent_publication_and_launch(self):
        for mode in ['missing_schema', 'missing_mime']:
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
        for mode in ['missing_value', 'duplicate', 'mismatch']:
            with self.subTest(mode=mode):
                result = self.publish(mode)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('MOBILE ', result.stdout)


class ActivatedServices(unittest.TestCase):
    def qualify(self, mode='success'):
        source = (RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh').read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        boundary = re.search(r"^printf 'OBSERVE activated local Denial.*?\n(.*?)^: >", source, re.M | re.S).group(1)
        code = 'set -euo pipefail\n' + functions + r'''
export XDG_RUNTIME_DIR=/run/user/1000
MODE=$1
timeout(){ printf 'BOUNDED %s\n' "$*" >&2; shift 3; "$@"; }
systemctl(){
    printf 'SERVICE %s\n' "$*" >&2
    if [[ $2 == start ]]; then [[ $MODE != start_fail ]] || return 124; return 0; fi
    [[ $MODE != query_fail ]] || return 42
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
        empty_mount) return 0;;
        ancestor) printf '/run/user/1000 tmpfs rw\n';;
        wrong_type) printf '/run/user/1000/doc tmpfs rw\n';;
        duplicate_mount) printf '/run/user/1000/doc fuse.portal rw\n/run/user/1000/doc fuse.portal rw\n';;
        fuse_plain) printf '/run/user/1000/doc fuse rw,nosuid,nodev\n';;
        *) printf '/run/user/1000/doc fuse.portal rw,nosuid,nodev\n';;
    esac
}
''' + boundary + "echo CLIENTS-MAY-START\n"
        return subprocess.run(['bash', '-c', code, 'fixture', mode],
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
                self.assertIn('BOUNDED -k 1 20 systemctl --user start '+names, result.stderr)
                self.assertIn('BOUNDED -k 1 3 systemctl --user is-active '+names, result.stderr)
                self.assertIn('MOUNT --kernel --noheadings --raw --mountpoint /run/user/1000/doc --output TARGET,FSTYPE,OPTIONS', result.stderr)
                self.assertIn('OBSERVE document portal mount=/run/user/1000/doc fuse', result.stdout)
                self.assertIn('CLIENTS-MAY-START', result.stdout)

    def test_service_and_mount_failures_never_admit_clients(self):
        for mode in ['start_fail', 'query_fail', 'empty_states', 'partial_states', 'inactive',
                     'mount_fail', 'empty_mount', 'ancestor', 'wrong_type', 'duplicate_mount']:
            with self.subTest(mode=mode):
                result = self.qualify(mode)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('CLIENTS-MAY-START', result.stdout)


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


class ClientExit(unittest.TestCase):
    def run_stop(self, first_exit, phase="stop"):
        script = RUNNER.parents[1].parent/'tools/qemu-virtio-drm/logind-denial.sh'
        source = script.read_text()
        functions = '\n'.join(re.findall(r'^\w+\(\) \{.*?^\}', source, re.M | re.S))
        # Execute the production terminal-stop block, including the old defective
        # block before the correction. The children and Bash waits are real.
        stop = source.split("sleep 3\n", 1)[1].split('# Require successful enumeration', 1)[0]
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
