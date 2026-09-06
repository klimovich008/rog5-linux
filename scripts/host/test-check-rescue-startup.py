#!/usr/bin/env python3
"""Offline replay of the real rescue supervisor boundary; no phone endpoints."""
import importlib.util
import gzip
import json
from pathlib import Path
import tempfile
import subprocess
import sys
from unittest import mock
import unittest

spec = importlib.util.spec_from_file_location('startup', Path(__file__).with_name('check-rescue-startup.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class Tests(unittest.TestCase):
    def setUp(self):
        self.record = dict(candidate='fixture', target_bundle='fixture', serial='fixture-serial',
                           execution='fastboot-boot-ram-bundle', product='lahaina', expected_slot='b')
        self.identity = dict(serial='fixture-serial', bundle='fixture', release='fixture-kernel',
                             boot_id='11111111-1111-4111-8111-111111111111')
        source = dict(revision='a'*40, worktree_digest='b'*64, clean=True)
        self.receipt = dict(format='rog5-headless-capture-v1', profile='fixture',
                            canonical_record=self.record, source=source, required_seconds=1320,
                            started_monotonic=100, deadline_monotonic=1480,
                            receiver_sha256=M.digest(M.D.CAPTURE.__file__))
        self.execution = dict(preflight='PASS', canonical_record=self.record,
                              source_revision=source['revision'], unix=1003, flash=False,
                              capture=dict(status='PASS', test='H01-receiver', profile='fixture',
                                           remaining_seconds=1376, receipt_sha256='c'*64))
        self.readiness = dict(status='PASS', source=source, identity=self.identity,
                              canonical_record=self.record, runner_sha256=M.digest(M.D.__file__),
                              actual=dict(boot_before=self.identity['boot_id'], boot_after=self.identity['boot_id'],
                                          kernel='fixture-kernel', bundle='fixture', run_fstype='tmpfs',
                                          marker_metadata='0:0:444:regular file:1', ssh_identity_service='active',
                                          marker='status=PASS\nkernel=fixture-kernel\nssh=strict-key-only\nattested_boot_id='+self.identity['boot_id']+'\n'))
        self.events = [dict(event=name, unix=1000+i*.1, monotonic=100+i*.1)
                       for i,name in enumerate(M.PREPARED)]
        self.events.append(dict(event='stage', unix=1045, monotonic=145,
                                stage=dict(boot_id=self.identity['boot_id'], stage='switch-root', state='PASS')))
        self.attempts = [dict(unix=1040, elapsed=39, code=1), dict(unix=1060, elapsed=59, code=0)]
        self.smoke = dict(status='PASS', elapsed_seconds=59.1, execution_return=0)

    def check(self):
        return M.validate(self.record, self.identity, self.execution, self.receipt, 'c'*64,
                          self.events, self.attempts, self.smoke, self.readiness, 300)

    def test_replays_raw_readiness_not_only_stored_pass(self):
        result = self.check()
        self.assertEqual(result['startup_seconds'], 59)
        self.assertTrue(result['evidence_reused'])
        self.assertFalse(result['release_qualified'])
        self.assertFalse(result['h02_qualified'])
        self.readiness['actual']['marker'] = 'status=PASS\n'
        with self.assertRaises(ValueError): self.check()

    def test_deadline_is_original_not_a_new_ssh_clock(self):
        self.attempts[-1].update(unix=1302, elapsed=301)
        self.smoke['elapsed_seconds'] = 301.1
        with self.assertRaisesRegex(ValueError, 'deadline'): self.check()

    def test_ambiguous_execution_is_never_accepted(self):
        for code in (1, 124, False):
            self.smoke['execution_return'] = code
            with self.subTest(code=code), self.assertRaises(ValueError): self.check()

    def test_missing_preboot_receiver_is_rejected(self):
        self.events.pop(0)
        with self.assertRaisesRegex(ValueError, 'preboot'): self.check()

    def test_receiver_after_execution_is_rejected(self):
        self.events[3]['unix'] = 1004
        with self.assertRaisesRegex(ValueError, 'preboot'): self.check()

    def test_wrong_receipt_hash_or_short_capture(self):
        self.execution['capture']['receipt_sha256'] = 'd'*64
        with self.assertRaises(ValueError): self.check()
        self.execution['capture']['receipt_sha256'] = 'c'*64
        self.execution['capture']['remaining_seconds'] = 1319
        with self.assertRaises(ValueError): self.check()

    def test_different_boot_or_candidate_is_rejected(self):
        self.readiness['identity'] = dict(self.identity, boot_id='wrong')
        with self.assertRaises(ValueError): self.check()
        self.readiness['identity'] = self.identity
        self.receipt['canonical_record'] = dict(self.record, candidate='other')
        with self.assertRaises(ValueError): self.check()

    def test_unbound_or_wrong_boot_stage_is_not_startup_proof(self):
        self.events[-1]['stage']['boot_id'] = 'other'
        with self.assertRaises(ValueError): self.check()

    def test_changed_producer_or_dirty_source_cannot_reuse_evidence(self):
        for target, key, bad in ((self.receipt, 'receiver_sha256', '0'*64),
                                 (self.readiness, 'runner_sha256', '0'*64),
                                 (self.receipt['source'], 'clean', False)):
            old = target[key]; target[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()
            target[key] = old

    def test_nan_boolean_and_nonmonotonic_timings_rejected(self):
        for bad in (float('nan'), float('inf'), True, -1):
            self.attempts[-1]['elapsed'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError): self.check()
        self.attempts[-1]['elapsed'] = 38
        with self.assertRaises(ValueError): self.check()

    def test_multiple_successes_or_lost_transport_not_silently_accepted(self):
        self.attempts.insert(0, dict(unix=1020, elapsed=19, code=0))
        with self.assertRaises(ValueError): self.check()
        self.attempts.pop(0)
        self.events.insert(-1, dict(event='transport-check-failed', unix=1044, monotonic=144))
        with self.assertRaises(ValueError): self.check()

    def test_evidence_reader_rejects_symlinks_duplicates_and_large_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root/'receipt.json'
            path.write_text('{"status":"FAIL","status":"PASS"}')
            with self.assertRaises(ValueError): M.read_json(path)
            path.write_text('{}')
            (root/'link').symlink_to(path)
            with self.assertRaises(OSError): M.read_json(root/'link')
            path.write_bytes(b' '*(M.LIMIT+1))
            with self.assertRaises(ValueError): M.read_json(path)

    def test_discoverable_and_retained_in_normal_optimized_and_broader_tiers(self):
        help_result = subprocess.run([str(M.D.REPO/'scripts/host/rog5-dev'),
                                     'check-rescue-startup', '--help'],
                                    capture_output=True, text=True, timeout=5)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('--execution-record', help_result.stdout)
        contract = M.D.CAPTURE.ACCEPTANCE.load_contract()
        for tier in ('quick', 'offline', 'release'):
            row = next(t for t in M.D.CAPTURE.ACCEPTANCE.select(contract, tier) if t['id'] == 'A02')
            for command in (['python3', 'scripts/host/test-check-rescue-startup.py'],
                            ['python3', '-O', 'scripts/host/test-check-rescue-startup.py']):
                self.assertIn(command, row['commands'])
        script = (M.D.REPO/'scripts/host/test-repository-linux.sh').read_text()
        self.assertIn('scripts/host/test-check-rescue-startup.py', script.split('active_tests=(',1)[1].split(')',1)[0])


class CurrentBootTests(unittest.TestCase):
    def setUp(self):
        self.identity = dict(boot_id='11111111-1111-4111-8111-111111111111',
                             bundle='fixture', release='fixture-kernel')
        self.observed = dict(boot_before=self.identity['boot_id'], boot_after=self.identity['boot_id'],
                             cmdline='rog5.bundle=fixture rog5.recovery_timeout=900',
                             kernel='fixture-kernel', wifi='inactive', files='PASS',
                             health='Good', temperature='298', voltage='8619000', online='1',
                             status='Full', current='0', capacity='100', uptime='1000.0',
                             watchdog='[ 2.5] rog5-persistent-root: emergency-reset watchdog armed for 900 seconds\n'
                                      '[ 902.6] rog5-persistent-root: watchdog acknowledged by current-boot P2 and SSH identity readiness')

    def test_exact_same_boot_full_battery_is_safe_not_h03_charging_proof(self):
        result = M.validate_current(self.observed, self.identity, 900)
        self.assertEqual(result['watchdog'], 'acknowledged')
        self.assertFalse(result['h03_qualified'])

    def test_wrong_boot_unsafe_power_and_radio_activation_fail(self):
        for key, bad in [('boot_after','other'), ('kernel','other'), ('wifi','active'),
                         ('files','FAIL'), ('health','Overheat'), ('temperature','400'),
                         ('voltage','7000000'), ('online','0'), ('capacity','101')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                M.validate_current(dict(self.observed, **{key:bad}), self.identity, 900)

    def test_watchdog_wrong_timeout_duplicate_missing_or_early_ack_fail(self):
        for bad in ('', self.observed['watchdog']*2,
                    self.observed['watchdog'].replace('900 seconds','600 seconds'),
                    self.observed['watchdog'].replace('902.6','12.6')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                M.validate_current(dict(self.observed, watchdog=bad), self.identity, 900)

    def test_duplicate_cmdline_timeout_or_bundle_fail(self):
        for extra in (' rog5.recovery_timeout=600', ' rog5.bundle=other'):
            with self.assertRaises(ValueError):
                M.validate_current(dict(self.observed, cmdline=self.observed['cmdline']+extra), self.identity, 900)

    def test_identity_gate_precedes_credential_and_remote_command(self):
        with mock.patch.object(M.D, 'host_gate', side_effect=ValueError('wrong USB')), \
             mock.patch.object(M.D, 'credential') as credential, \
             mock.patch.object(M.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'wrong USB'):
                M.collect_current(self.identity, None, None, 'not executed')
            credential.assert_not_called(); run.assert_not_called()


def sealed_probe(archive, manifest_path):
    """Exact sealed BusyBox commands in disposable target paths, never hardware."""
    manifest = dict(line.split('=',1) for line in manifest_path.read_text().splitlines())
    expected, blob = M.sealed_runtime(archive, manifest)
    composition = M.D.CAPTURE.load('startup_fixture_composition', 'scripts/host/check-rescue-root-composition.py')
    members = composition.SEALED.ARCHIVE.entries(gzip.decompress(blob))
    fixture = CurrentBootTests(); fixture.setUp()
    identity = dict(fixture.identity, release=manifest['target_release'], bundle=manifest['bundle'])
    with tempfile.TemporaryDirectory(prefix='rog5-startup-sealed-') as tmp:
        root = Path(tmp)
        composition.SEALED.extract(members, root)
        for source, target in M.RUNTIME_FILES.items():
            path = root/target.lstrip('/'); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(members[source][1]); path.chmod(int(expected[target]['mode'],8))
        values = {'proc/sys/kernel/random/boot_id': identity['boot_id'],
                  'proc/cmdline': 'rog5.bundle='+identity['bundle']+' rog5.recovery_timeout=900',
                  'proc/uptime': '1000.0 2000.0',
                  'sys/class/power_supply/qcom-battmgr-bat/health': 'Good',
                  'sys/class/power_supply/qcom-battmgr-bat/temp': '298',
                  'sys/class/power_supply/qcom-battmgr-bat/voltage_now': '8619000',
                  'sys/class/power_supply/qcom-battmgr-bat/status': 'Full',
                  'sys/class/power_supply/qcom-battmgr-bat/current_now': '0',
                  'sys/class/power_supply/qcom-battmgr-bat/capacity': '100',
                  'sys/class/power_supply/qcom-battmgr-usb/online': '1'}
        for name, value in values.items():
            path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value+'\n')
        # Only hardware/mount observations are fixtures. Shell, stat, cat, grep,
        # hash, cut, test and NUL framing run with the exact sealed BusyBox.
        for applet, body in [('findmnt', 'test "$*" = "-n -o FSTYPE --target /run/initramfs"\nprintf "tmpfs\\n"\n'),
                             ('dmesg', 'cat /fixture-dmesg\n')]:
            path = root/'bin'/applet
            if path.is_symlink(): path.unlink()
            path.write_text('#!/bin/sh\nset -eu\n'+body); path.chmod(0o755)
        (root/'fixture-dmesg').write_text(fixture.observed['watchdog']+'\n')
        (root/'probe').write_text(M.current_script(identity, expected))
        (root/'rog5-qemu').touch()
        command = ['bwrap','--unshare-all','--die-with-parent','--uid','0','--gid','0',
                   '--ro-bind',str(root),'/', '--ro-bind','/usr/bin/qemu-aarch64-static','/rog5-qemu',
                   '--clearenv','--setenv','PATH','/bin:/sbin:/usr/bin:/usr/sbin',
                   '--setenv','QEMU_UNAME',identity['release'],
                   '/rog5-qemu','/bin/busybox','sh','/probe']
        result = subprocess.run(command, capture_output=True, timeout=15)
        if result.returncode: raise ValueError(result.stderr.decode())
        fields = result.stdout.decode('ascii').split('\0')
        if len(fields) != len(M.CURRENT_KEYS)+1 or fields[-1]: raise ValueError('sealed framing failed')
        M.validate_current(dict(zip(M.CURRENT_KEYS,fields[:-1])),identity,900)
        # An actual fixture radio device must fail the same complete script.
        (root/'sys/class/ieee80211/phy0').mkdir(parents=True)
        rejected = subprocess.run(command,capture_output=True,timeout=15)
        if rejected.returncode == 0: raise ValueError('sealed radio isolation failed')
    print('PASS exact sealed BusyBox runtime probe and active-radio refusal; mount/dmesg are fixtures')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--sealed':
        sealed_probe(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        unittest.main(verbosity=2)
