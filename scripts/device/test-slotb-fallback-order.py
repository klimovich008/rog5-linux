#!/usr/bin/env python3
"""Replay the loader's actual copy/unmount/verify/select ordering, offline."""
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO / 'initramfs/persistent-slotb-loader-init').read_text()
MAIN = SOURCE[SOURCE.index('\nresolve_storage || fail storage_identity'):]
FLOW = MAIN[MAIN.index('case $selector_format in'):MAIN.index('command_line=')]
COPY = re.search(r'^copy_bundle\(\) \{\n.*?^}', SOURCE, re.M | re.S).group()
SHELL = shlex.split(os.environ.get('ROG5_LOADER_TEST_SHELL', 'sh'))


class FallbackOrder(unittest.TestCase):
    def run_case(self, mutation='', decision='primary'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            bundles = root / 'bundles'; bundles.mkdir()
            for name in ('primary', 'fallback'):
                directory = source / name; directory.mkdir()
                (directory / 'payload').write_text('verified-' + name)
            if mutation in ('missing-primary', 'missing-fallback'):
                (source / mutation.removeprefix('missing-')).rename(root / 'missing')
            elif mutation == 'linked-primary':
                (source / 'primary').rename(root / 'linked')
                (source / 'primary').symlink_to(root / 'linked')
            elif mutation in ('corrupt-primary', 'corrupt-fallback'):
                (source / mutation.removeprefix('corrupt-') / 'payload').write_text('bad')
            elif mutation == 'relock-fail':
                (source / 'primary' / 'payload').write_text('bad')
            script = '''set -eu
mutation=$2; decision=$3
selector_format=format=rog5-slotb-selector-v2
primary_bundle=primary; fallback_bundle=fallback
primary_manifest_hash=primary-pin; fallback_manifest_hash=fallback-pin
selection_report_delay=0.30
source_root=$1/source; bundle_root=$1/bundles; plan=$1/plan
target_mount=$1/mount
fail() { printf 'FAIL %s\n' "$1"; exit 1; }
log() { :; }
set_stage() { printf 'stage %s %s %s\n' "$1" "$2" "$3"; }
sync() { :; }
umount() { printf 'unmount\n'; [ "$mutation" != unmount-fail ]; }
relock_all_storage() { printf 'relock\n'; [ "$mutation" != relock-fail ]; }
sleep() { [ "$1" = 0.30 ]; }
cp() {
    if [ "$mutation" = partial-primary ] && [ "$2" = "$source_root/primary" ]; then
        mkdir "$bundle_root/primary"
        printf partial >"$bundle_root/primary/payload"
        return 1
    fi
    command cp "$@"
}
verify_bundle() {
    printf 'verify %s\n' "$1"
    # Crypto is the fixed verifier boundary; exercise exact argument routing
    # and rejection here, not a substitute signature implementation.
    [ "$2" = "$1-pin" ] || return 1
    [ "$(cat "$bundle_root/$1/payload")" = "verified-$1" ] || return 1
    printf 'cmdline=verified-%s\n' "$1" >"$3"
}
select_trial_bundle() {
    printf 'select-once\n'
    bundle=$decision
    manifest_hash=$decision-pin
    trial_selection_detail=trial-$decision
}
''' + COPY + '\n' + FLOW + '\nprintf "selected=%s hash=%s\\n" "$bundle" "$manifest_hash"\ncat "$plan"\n'
            result = subprocess.run(
                [*SHELL, '-c', script, 'fixture', str(root), mutation, decision],
                capture_output=True, text=True, timeout=5,
            )
            return result

    def test_primary_only_damage_uses_verified_fallback_without_trial_write(self):
        for mutation in ('missing-primary', 'linked-primary', 'corrupt-primary',
                         'partial-primary'):
            with self.subTest(mutation=mutation):
                result = self.run_case(mutation)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('selected=fallback hash=fallback-pin', result.stdout)
                self.assertTrue(result.stdout.endswith('cmdline=verified-fallback\n'))
                self.assertNotIn('select-once', result.stdout)
                self.assertEqual(result.stdout.count('relock\n'), 1)
                self.assertLess(result.stdout.index('unmount'), result.stdout.index('verify fallback'))

    def test_invalid_fallback_or_failed_unmount_never_selects(self):
        for mutation in ('missing-fallback', 'corrupt-fallback', 'unmount-fail',
                         'relock-fail'):
            with self.subTest(mutation=mutation):
                result = self.run_case(mutation)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('selected=', result.stdout)
                self.assertNotIn('select-once', result.stdout)

    def test_invalid_trial_decision_never_publishes_a_plan(self):
        result = self.run_case(decision='unreviewed')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('selected=', result.stdout)

    def test_two_valid_bundles_keep_one_use_selection_and_plan_identity(self):
        for decision in ('primary', 'fallback'):
            with self.subTest(decision=decision):
                result = self.run_case(decision=decision)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stdout.count('select-once'), 1)
                self.assertIn(f'selected={decision} hash={decision}-pin', result.stdout)
                self.assertTrue(result.stdout.endswith(f'cmdline=verified-{decision}\n'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
