#!/usr/bin/env python3
"""Real persistent-state/health/runtime integration; only hardware endpoints fake."""
import importlib.util
import os
from pathlib import Path
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('healthy_fixture', REPO/'scripts/device/test-native-wifi-healthy.py')
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

class Finalization(unittest.TestCase):
    def fixture(self):
        root, harness = F.PersistentWifiHealthy.fixture(self)
        state = root/'state'; state.mkdir(mode=0o755)
        (state/'rog5').mkdir(mode=0o700)
        helper = root/'run/rog5-native-wifi/trial-state'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1',
                        f'-DROG5_DECIDE_ROOT="{state}"', f'-DROG5_HEALTHY_ROOT="{state}"',
                        str(REPO/'tools/persistent_trial_state/rog5-persistent-trial-state.c'),
                        '-o', str(helper)], check=True, capture_output=True)
        self.args = [str(helper), 'decide', F.TRIAL, F.PRIMARY, '2'*64, 'fallback', '3'*64]
        self.assertEqual(self.decide(), F.PRIMARY)
        return root, harness

    def decide(self):
        p = subprocess.run(self.args, capture_output=True, text=True, timeout=5)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def run_health(self, harness):
        return subprocess.run(['sh', str(harness)], capture_output=True, text=True, timeout=5)

    def timer(self, root):
        return F.PersistentWifiHealthy.fire_boot_timer(self, root)

    def command(self, root, action):
        return subprocess.run([str(root/'run/rog5-native-wifi/trial-state'), action,
                               F.TRIAL, F.PRIMARY], capture_output=True, text=True, timeout=5)

    def inject(self, harness, code):
        source = harness.read_text()
        harness.write_text(code + '\n' + source)

    def assert_failed_fallback(self, root, harness):
        result = self.run_health(harness)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.timer(root), 'reboot\n')
        self.assertEqual(self.decide(), 'fallback')

    def test_probe_timer_routes_automatic_acceptance_but_preserves_manual_reboot(self):
        source = (REPO/'scripts/device/probe-native-wifi.sh').read_text()
        start = source.index('# Automatic boot compositions')
        end = source.index('systemctl is-active --quiet rog5-wifi-probe-rollback.timer', start)
        actual = source[start:end]
        for automatic in (False, True):
            with self.subTest(automatic=automatic):
                root, harness = self.fixture()
                runtime = root/'run/rog5-native-wifi'
                if automatic:
                    (runtime/'automatic').write_text('rog5-native-wifi-boot-v1\n')
                    (runtime/'runtime').write_text('#!/bin/sh\n'); (runtime/'runtime').chmod(0o755)
                result = subprocess.run(['sh', '-c', 'set -eu\nroot='+str(runtime)+
                    '\nfail() { exit 1; }\nsystemd-run() { printf "%s\n" "$@"; }\n'+actual],
                    capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines()[-2:],
                    [str(runtime/'runtime'), 'rollback'] if automatic else ['/usr/bin/systemctl', 'reboot'])
                if automatic:
                    self.assertEqual(self.run_health(harness).returncode, 0)
                    self.assertEqual(self.timer(root), '')
                    self.assertEqual(self.decide(), F.PRIMARY)

    def test_timer_stop_failure_cannot_accept_failed_finalization(self):
        for timer in ('probe', 'boot'):
            with self.subTest(timer=timer):
                root, harness = self.fixture()
                source = harness.read_text().replace(timer+'_timer_active=0 ;;', 'return 42 ;;')
                harness.write_text(source)
                result = self.run_health(harness)
                # Old protocol fails after committing healthy; fixed does not cancel.
                if result.returncode:
                    self.assertEqual(self.decide(), 'fallback', result.stderr)
                else:
                    self.assertEqual(self.decide(), F.PRIMARY)

    def test_timer_stop_and_inactivity_operations_are_absent(self):
        root, harness = self.fixture()
        s = harness.read_text().replace('systemctl() {',
            'systemctl() { case "$*" in *rollback.timer*) echo forbidden >>"'+str(root/'timer-ops')+'"; return 42 ;; esac;')
        harness.write_text(s)
        self.assertEqual(self.run_health(harness).returncode, 0)
        self.assertFalse((root/'timer-ops').exists())
        self.assertEqual(self.timer(root), '')
        self.assertEqual(self.timer(root), '')
        self.assertEqual(self.decide(), F.PRIMARY)
        # Every ordinary boot still needs a fresh health acknowledgment.
        self.assertEqual(self.decide(), 'fallback')

    def test_record_creation_mode_and_publication_failures(self):
        for phase in ('creation', 'mode', 'publication'):
            with self.subTest(phase=phase):
                root, harness = self.fixture()
                if phase == 'creation':
                    (root/'run/rog5-native-wifi/healthy.record.next').mkdir()
                else:
                    command = 'chmod' if phase == 'mode' else 'mv'
                    self.inject(harness, command+'() { return 42; }')
                self.assert_failed_fallback(root, harness)

    def test_interruption_before_commit_is_fenced_but_completed_commit_survives(self):
        points = [('state=$("$helper" state', False),
                  ('	chmod 0444 "$record.next"', False),
                  ('	mv -T "$record.next"', False),
                  ('result=$("$helper" healthy', False),
                  ('echo "PASS native Wi-Fi', True)]
        for marker, accepted in points:
            with self.subTest(marker=marker):
                root, harness = self.fixture()
                source = harness.read_text()
                at = source.index(marker)
                harness.write_text(source[:at]+'kill -KILL "$$"\n'+source[at:])
                self.assertNotEqual(self.run_health(harness).returncode, 0)
                self.assertEqual(self.timer(root), '' if accepted else 'reboot\n')
                self.assertEqual(self.decide(), F.PRIMARY if accepted else 'fallback')

    def test_real_commit_write_fsync_and_rename_failures(self):
        # Compile the actual translation unit with only syscall boundaries
        # intercepted. No duplicate state-machine model or fake healthy reply.
        for phase in ('write', 'file-fsync', 'rename', 'directory-fsync'):
            with self.subTest(phase=phase):
                root, harness = self.fixture()
                state = root/'state'
                injection = root/'injection.c'
                injection.write_text(r'''#define _GNU_SOURCE
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
static int active, sync_calls;
static ssize_t injected_write(int fd, const void *data, size_t size);
static int injected_fsync(int fd);
static int injected_renameat(int from, const char *a, int to, const char *b);
#define main production_main
#define write injected_write
#define fsync injected_fsync
#define renameat injected_renameat
#include "''' + str(REPO/'tools/persistent_trial_state/rog5-persistent-trial-state.c') + r'''"
#undef main
#undef write
#undef fsync
#undef renameat
static ssize_t injected_write(int fd, const void *data, size_t size) {
    if (active && strcmp("PHASE", "write") == 0) { errno=EIO; return -1; }
    return write(fd, data, size);
}
static int injected_fsync(int fd) {
    if (active && ((++sync_calls == 1 && strcmp("PHASE", "file-fsync") == 0) ||
                   (sync_calls == 2 && strcmp("PHASE", "directory-fsync") == 0))) {
        errno=EIO; return -1;
    }
    return fsync(fd);
}
static int injected_renameat(int from, const char *a, int to, const char *b) {
    if (active && strcmp("PHASE", "rename") == 0) { errno=EIO; return -1; }
    return renameat(from, a, to, b);
}
int main(int argc, char **argv) {
    active = argc > 1 && strcmp(argv[1], "healthy") == 0;
    return production_main(argc, argv);
}
'''.replace('PHASE', phase))
                subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    f'-DROG5_DECIDE_ROOT="{state}"', f'-DROG5_HEALTHY_ROOT="{state}"',
                    str(injection), '-o', str(root/'run/rog5-native-wifi/trial-state')],
                    check=True, capture_output=True)
                self.assert_failed_fallback(root, harness)

    def test_reported_failure_after_durable_commit_is_rejected(self):
        root, harness = self.fixture()
        helper = root/'run/rog5-native-wifi/trial-state'
        actual = helper.with_name('trial-state-real'); helper.rename(actual)
        helper.write_text('#!/bin/sh\n'+str(actual)+' "$@"\nresult=$?\n[ "$1" != healthy ] || exit 42\nexit "$result"\n')
        helper.chmod(0o755)
        self.assert_failed_fallback(root, harness)

    def test_timer_winning_before_commit_prevents_late_acceptance(self):
        root, harness = self.fixture()
        source = harness.read_text()
        at = source.index('result=$("$helper" healthy')
        harness.write_text(source[:at]+'"$helper" rollback "$trial_id" "$primary"\n'+source[at:])
        self.assert_failed_fallback(root, harness)
        self.assertNotEqual(self.command(root, 'healthy').returncode, 0)

    def test_receipt_alone_cannot_suppress_rollback(self):
        root, harness = self.fixture()
        source = harness.read_text(); at = source.index('result=$("$helper" healthy')
        harness.write_text(source[:at]+'kill -KILL "$$"\n'+source[at:])
        self.run_health(harness)
        self.assertTrue((root/'run/rog5-native-wifi/healthy.record').exists())
        self.assertEqual(self.command(root, 'state').stdout, 'pending\n')
        self.assertEqual(self.timer(root), 'reboot\n')
        self.assertEqual(self.command(root, 'state').stdout, 'failed\n')
        self.assertEqual(self.decide(), 'fallback')

    def test_success_already_healthy_and_stale_receipts(self):
        for mutation in ('none', 'boot', 'trial', 'missing'):
            with self.subTest(mutation=mutation):
                root, harness = self.fixture()
                self.assertEqual(self.run_health(harness).returncode, 0)
                self.assertEqual(self.run_health(harness).returncode, 0)
                receipt = root/'run/rog5-native-wifi/healthy.record'
                if mutation == 'missing': receipt.unlink()
                elif mutation != 'none':
                    text = receipt.read_text().replace('000000000001', '000000000002') if mutation == 'boot' else receipt.read_text().replace(F.TRIAL, '4'*64)
                    receipt.chmod(0o644); receipt.write_text(text); receipt.chmod(0o444)
                result = self.run_health(harness)
                self.assertEqual(result.returncode == 0, mutation == 'none')
                self.assertEqual(self.timer(root), '' if mutation == 'none' else 'reboot\n')
                self.assertEqual(self.decide(), F.PRIMARY if mutation == 'none' else 'fallback')

    def test_existing_receipt_mode_and_link_count_are_real(self):
        for mutation in ('mode', 'hardlink'):
            with self.subTest(mutation=mutation):
                root, harness = self.fixture()
                self.assertEqual(self.run_health(harness).returncode, 0)
                receipt = root/'run/rog5-native-wifi/healthy.record'
                if mutation == 'mode': receipt.chmod(0o644)
                else: os.link(receipt, root/'second-link')
                self.assert_failed_fallback(root, harness)

    def test_mismatched_trial_and_duplicate_bundle_tokens_never_commit(self):
        for mutation in ('trial', 'duplicate', 'duplicate-identical'):
            with self.subTest(mutation=mutation):
                root, harness = self.fixture()
                if mutation == 'trial':
                    descriptor = root/'run/rog5-native-wifi/trial-descriptor'
                    descriptor.chmod(0o644); descriptor.write_text(descriptor.read_text().replace(F.TRIAL, '4'*64)); descriptor.chmod(0o444)
                else:
                    (root/'proc/cmdline').write_text('rog5.bundle='+ ('other' if mutation == 'duplicate' else F.PRIMARY)+' rog5.bundle='+F.PRIMARY+'\n')
                self.assert_failed_fallback(root, harness)

if __name__ == '__main__': unittest.main()
