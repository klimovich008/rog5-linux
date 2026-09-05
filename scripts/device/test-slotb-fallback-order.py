#!/usr/bin/env python3
"""Replay the loader's actual copy/unmount/verify/select ordering, offline."""
import os
import hashlib
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO / 'initramfs/persistent-slotb-loader-init').read_text()
MAIN = SOURCE[SOURCE.index('\nresolve_storage || fail storage_identity'):]
FLOW = MAIN[MAIN.index('case $selector_format in'):MAIN.index('fi # storage-selector path;')]
SELECTOR_FLOW = MAIN[MAIN.index('read_selector ||'):MAIN.index('\nif [ "$loader_mode"')]
COPY = re.search(r'^copy_bundle\(\) \{\n.*?^}', SOURCE, re.M | re.S).group()
SHELL = shlex.split(os.environ.get('ROG5_LOADER_TEST_SHELL', 'sh'))
HASHES = {'primary': 'a' * 64, 'fallback': 'b' * 64}


class FallbackOrder(unittest.TestCase):
    def run_case(self, mutation='', decision='primary', rescue=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            bundles = root / 'bundles'; bundles.mkdir()
            for name in ('primary', 'fallback'):
                directory = source / name; directory.mkdir()
                (directory / 'payload').write_text('verified-' + name)
            selector = root / 'selector'
            selector.write_text('format=rog5-slotb-selector-v2\ntrial_id=' + 'c' * 64 +
                '\nprimary_bundle=primary\nprimary_manifest_sha256=' + HASHES['primary'] +
                '\nfallback_bundle=fallback\nfallback_manifest_sha256=' + HASHES['fallback'] +
                '\nmode=try-once\n')
            selector.chmod(0o600)
            selector_hash = hashlib.sha256(selector.read_bytes()).hexdigest()
            if mutation == 'changed-selector':
                selector.write_text(selector.read_text().replace('c' * 64, 'd' * 64))
            elif mutation == 'wrong-selector-format':
                selector.write_text('format=rog5-slotb-selector-v1\nbundle=primary\nmanifest_sha256=' + HASHES['primary'] + '\n')
            elif mutation == 'selector-mode':
                selector.chmod(0o644)
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
export PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/libexec
mutation=$2; decision=$3
selector_format=format=rog5-slotb-selector-v2
primary_bundle=primary; fallback_bundle=fallback
primary_manifest_hash=primary-pin; fallback_manifest_hash=fallback-pin
selection_report_delay=0.30
source_root=$1/source; bundle_root=$1/bundles; plan=$1/plan
target_mount=$1/mount
fallback_selector_hash=
fail() { printf 'FAIL %s\n' "$1"; exit 1; }
log() { :; }
set_stage() { printf 'stage %s %s %s\n' "$1" "$2" "$3"; }
sync() { :; }
umount() { printf 'unmount\n'; [ "$mutation" != unmount-fail ]; }
relock_all_storage() {
    printf 'relock\n'
    [ "$mutation" != relock-fail ] && [ "$mutation" != rescue-relock-fail ]
}
sleep() { [ "$1" = 0.30 ]; }
cp() {
    if [ "$1" = -a ]; then printf 'copy %s\n' "${2##*/}"; fi
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
    case $1 in primary) expected=primary-pin ;; fallback) expected=fallback-pin ;; *) return 1 ;; esac
    [ "$2" = "$expected" ] || return 1
    [ "$(cat "$bundle_root/$1/payload")" = "verified-$1" ] || return 1
    printf 'cmdline=verified-%s\n' "$1" >"$3"
}
select_trial_bundle() {
    printf 'select-once\n'
    bundle=$decision
    case $decision in primary) manifest_hash=$primary_manifest_hash ;;
        fallback) manifest_hash=$fallback_manifest_hash ;; *) manifest_hash=invalid ;; esac
    trial_selection_detail=trial-$decision
}
'''
            script = script.replace('primary-pin', HASHES['primary']).replace('fallback-pin', HASHES['fallback'])
            if rescue:
                for name in ('valid_bundle_name', 'valid_hash', 'read_selector', 'apply_fallback_request'):
                    function = re.search(r'^' + name + r'\(\) \{\n.*?^}', SOURCE, re.M | re.S)
                    self.assertIsNotNone(function, 'missing selector function: ' + name)
                    script += function.group() + '\n'
                script += f'fallback_selector_hash={selector_hash}\nselector=$1/selector\n'
                # UID/GID are explicitly fixture-modeled; real mode/link count
                # and the production parser/hash/copy integration are exercised.
                script += '''stat() {
    if [ "$1" = -c ] && [ "$2" = '%u:%g:%a:%h' ] && [ "$3" = "$selector" ]; then
        metadata=$(command stat -c '%a:%h' "$selector") || return 1
        printf '0:0:%s\n' "$metadata"
    else command stat "$@"; fi
}
''' + SELECTOR_FLOW + '\n'
            script += COPY + '\n' + FLOW + '\nprintf "selected=%s hash=%s\\n" "$bundle" "$manifest_hash"\ncat "$plan"\n'
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
                self.assertIn('selected=fallback hash=' + HASHES['fallback'], result.stdout)
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
                self.assertIn(f'selected={decision} hash={HASHES[decision]}', result.stdout)
                self.assertTrue(result.stdout.endswith(f'cmdline=verified-{decision}\n'))

    def test_explicit_rescue_never_copies_primary_or_opens_trial_write(self):
        for mutation in ('', 'missing-primary', 'corrupt-primary'):
            with self.subTest(mutation=mutation):
                result = self.run_case(mutation, rescue=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('verify primary', result.stdout)
                self.assertNotIn('copy primary', result.stdout)
                self.assertNotIn('select-once', result.stdout)
                self.assertEqual(result.stdout.count('relock\n'), 1)
                self.assertTrue(result.stdout.endswith('cmdline=verified-fallback\n'))

    def test_rescue_refuses_changed_selector_and_failed_cleanup_or_signature(self):
        for mutation in ('changed-selector', 'wrong-selector-format', 'selector-mode', 'missing-fallback',
                         'corrupt-fallback', 'unmount-fail', 'rescue-relock-fail'):
            with self.subTest(mutation=mutation):
                result = self.run_case(mutation, rescue=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('selected=', result.stdout)
                self.assertNotIn('select-once', result.stdout)

    def test_rescue_argument_parser_is_exact_and_does_not_start_recovery(self):
        prefix = SOURCE[:SOURCE.index('\nlog()')]
        cases = ((['existing-recovery-fallback', 'a' * 64], True),
                 (['existing-recovery-fallback'], False),
                 (['existing-recovery-fallback', 'a' * 63], False),
                 (['existing-recovery-fallback', 'A' * 64], False),
                 (['existing-recovery-fallback', 'a' * 64 + '\n' + 'b' * 64], False),
                 (['existing-recovery', 'a' * 64], False),
                 (['existing-recovery-fallback', 'a' * 64, 'extra'], False))
        for args, accepted in cases:
            with self.subTest(args=args):
                result = subprocess.run([*SHELL, '-c', prefix +
                    '\nprintf "mode=%s hash=%s\\n" "$loader_mode" "$fallback_selector_hash"',
                    'fixture', *args], capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
                if accepted:
                    self.assertIn('mode=existing-recovery hash=' + 'a' * 64, result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
