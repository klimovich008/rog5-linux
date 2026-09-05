#!/usr/bin/env python3
"""Real loader RAM selection and shared execute tail with fake hardware endpoints."""
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO/'initramfs/persistent-slotb-loader-init').read_text()
SHELL = shlex.split(os.environ.get('ROG5_LOADER_TEST_SHELL', 'sh'))


def function(name):
    match = re.search(r'^'+name+r'\(\) \{\n.*?^}', SOURCE, re.M | re.S)
    if not match:
        raise AssertionError('RAM rescue production function missing: '+name)
    return match.group()


class RamBundleTest(unittest.TestCase):
    def test_exact_argument_parser(self):
        prefix = SOURCE[:SOURCE.index('\nlog()')]
        for args, accepted in ((['existing-recovery-ram', 'rescue', 'a'*64], True),
                               (['existing-recovery-ram', '../rescue', 'a'*64], False),
                               (['existing-recovery-ram', 'x\ny', 'a'*64], False),
                               (['existing-recovery-ram', 'rescue', 'a'*64+'\n'], False),
                               (['existing-recovery-ram', 'rescue', '0'*64], False),
                               (['existing-recovery-ram', 'rescue'], False)):
            with self.subTest(args=args):
                result = subprocess.run([*SHELL, '-c', prefix+
                    '\nprintf "%s %s %s\\n" "$loader_mode" "$ram_bundle" "$ram_manifest_hash"',
                    'fixture', *args], capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode == 0, accepted, result.stdout+result.stderr)
                if accepted:
                    self.assertEqual(result.stdout.strip(), 'existing-recovery rescue '+'a'*64)

    def run_case(self, mutation=''):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            embedded = root/'embedded'; embedded.mkdir(mode=0o700)
            bundle = embedded/'rescue'; bundle.mkdir(mode=0o700)
            destination = root/'destination'; destination.mkdir(mode=0o700)
            for name in ('Image', 'board.dtb', 'initramfs.cpio.gz', 'manifest', 'manifest.sig'):
                (bundle/name).write_bytes(b'verified-'+name.encode())
                (bundle/name).chmod(0o600)
            digest = hashlib.sha256((bundle/'manifest').read_bytes()).hexdigest()
            if mutation == 'missing': (bundle/'Image').unlink()
            if mutation == 'linked':
                (bundle/'Image').unlink(); (bundle/'Image').symlink_to('/not-allowed')
            if mutation == 'extra': (bundle/'unexpected').write_text('extra')
            if mutation == 'dirty-root': (destination/'.stale').write_text('stale')
            if mutation == 'wrong-manifest': (bundle/'manifest').write_bytes(b'changed')
            script = '''set -eu
embedded_root=$1/embedded; bundle_root=$1/destination; plan=$1/plan
ram_bundle=rescue; ram_manifest_hash=$3; mutation=$2
loader_mode=existing-recovery
fail() { printf 'FAIL %s\n' "$1"; exit 1; }
log() { :; }
set_stage() { printf 'stage %s %s %s\n' "$1" "$2" "$3"; }
relock_all_storage() { echo relock; [ "$mutation" != relock ]; }
stat() {
    # Fixture owns files as the test user; production requires root ownership.
    if [ "$1" = -c ] && [ "$2" = '%u:%g:%a:%h' ]; then
        printf '0:0:%s\n' "$(command stat -c '%a:%h' "$3")"
    else command stat "$@"; fi
}
verify_bundle() {
    echo verify
    [ "$mutation" != signature ] && [ "$1" = rescue ] && [ "$2" = "$ram_manifest_hash" ] || return 1
    [ "$(sha256sum "$bundle_root/$1/manifest" | cut -d ' ' -f 1)" = "$2" ] || return 1
    printf 'cmdline=verified-only\n' >"$3"
}
fixture_kexec() {
    case $1 in
        -c) echo load; [ "$mutation" != load ] ;;
        -e) echo execute; exit 0 ;;
        *) exit 98 ;;
    esac
}
disable_haven_watchdog() { echo haven; [ "$mutation" != haven ]; }
sleep() { :; }
mount() { echo FORBIDDEN-mount; exit 99; }
umount() { echo FORBIDDEN-umount; exit 99; }
select_trial_bundle() { echo FORBIDDEN-trial; exit 99; }
read_selector() { echo FORBIDDEN-selector; exit 99; }
'''
            script += function('valid_bundle_name')+'\n'+function('valid_hash')+'\n'
            script += function('prepare_embedded_bundle')+'\nprepare_embedded_bundle || fail ram_bundle\n'
            tail = SOURCE[SOURCE.index('\ncommand_line=$(sed -n'):]
            script += tail.replace('/usr/sbin/kexec', 'fixture_kexec')
            return subprocess.run([*SHELL, '-c', script, 'fixture', str(root), mutation, digest],
                                  capture_output=True, text=True, timeout=5)

    def test_one_verified_execute_without_storage_mount_or_trial(self):
        result = self.run_case()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertNotIn('FORBIDDEN', result.stdout)
        events = [line for line in result.stdout.splitlines() if line in ('relock', 'verify', 'load', 'haven', 'execute')]
        self.assertEqual(events, ['relock', 'verify', 'load', 'haven', 'execute'])

    def test_any_preparation_or_tail_failure_prevents_execute(self):
        for mutation in ('missing', 'linked', 'extra', 'dirty-root', 'wrong-manifest',
                         'relock', 'signature', 'load', 'haven'):
            with self.subTest(mutation=mutation):
                result = self.run_case(mutation)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('\nexecute\n', '\n'+result.stdout)
                self.assertNotIn('FORBIDDEN', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
