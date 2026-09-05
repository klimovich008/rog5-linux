#!/usr/bin/env python3
"""Execute the persistent Wi-Fi health gate against bounded fake endpoints."""

from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO/'initramfs/native-wifi-persistent/healthy').read_text()
TRIAL = '1' * 64
PRIMARY = 'persistent-native-root-wifi'
# Optional isolated-shell runner for exact sealed BusyBox replay. The runner
# must expose fixture paths unchanged and supply its own rootfs/applets; merely
# prefixing QEMU while using host /usr/bin does not prove target composition.
SHELL = shlex.split(os.environ.get('ROG5_WIFI_TEST_SHELL', 'sh'))


class PersistentWifiHealthy(unittest.TestCase):
    def fire_boot_timer(self, root, owner='0:0'):
        """Model a late timer event, NOT an actual systemd restart/transaction.

        Execute the shipped ExecStart/runtime with fixture /proc and a reboot
        recorder. Only ownership is simulated; mode/type/link checks are real.
        """
        (root/'proc/uptime').write_text('901.00 0.00\n')
        service = (REPO/'initramfs/native-wifi/units/'
                   'rog5-wifi-boot-rollback.service').read_text()
        command, = [line.removeprefix('ExecStart=')
                    for line in service.splitlines()
                    if line.startswith('ExecStart=')]
        argv = shlex.split(command)
        prelude = (
            'id() { echo 0; }\n'
            'stat() { if [ "$2" != "%u:%g:%a:%h" ]; then '
            'command stat "$@"; return; fi; printf "%s:%s\\n" ' + shlex.quote(owner) +
            ' "$(command stat -c \'%a:%h\' \"$3\")"; }\n'
            'sed() { printf "read\\n" >>' + shlex.quote(str(root/'content-reads')) +
            '; command sed "$@"; }\n'
            'systemctl() { [ "$*" = "--no-block reboot" ] || exit 2; '
            'printf "reboot\\n" >>' + shlex.quote(str(root/'reboots')) + '; }\n'
        )
        if argv[0] == '/run/rog5-native-wifi/runtime':
            source = (REPO/'initramfs/native-wifi/runtime').read_text()
            source = source.replace('/run/rog5-native-wifi',
                                    str(root/'run/rog5-native-wifi'))
            source = source.replace('/proc/', str(root/'proc') + '/')
            script = prelude + source
        else:
            # Safely reproduce the old unconditional service before the fix.
            self.assertEqual(argv, ['/usr/bin/systemctl', '--no-block', 'reboot'])
            script = prelude + 'systemctl --no-block reboot\n'
        result = subprocess.run([*SHELL, '-c', script, 'rollback-fixture', *argv[1:]],
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return (root/'reboots').read_text() if (root/'reboots').exists() else ''

    def test_healthy_boot_survives_reactivated_elapsed_timer(self):
        root, harness = self.fixture()
        accepted = subprocess.run([*SHELL, str(harness)], text=True,
                                  capture_output=True, timeout=5)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        # Model SSH Requires reactivating OnBootSec after health stopped it.
        self.assertEqual(self.fire_boot_timer(root), '')
        self.assertEqual(self.fire_boot_timer(root), '')

    def test_pending_boot_still_reboots_after_deadline(self):
        root, _ = self.fixture()
        self.assertFalse((root/'run/rog5-native-wifi/healthy.record').exists())
        self.assertEqual(self.fire_boot_timer(root), 'reboot\n')

    def test_invalid_healthy_evidence_never_suppresses_reboot(self):
        record = 'run/rog5-native-wifi/healthy.record'
        descriptor = 'run/rog5-native-wifi/trial-descriptor'
        boot = 'proc/sys/kernel/random/boot_id'
        cmdline = 'proc/cmdline'
        cases = [
            (record, 'missing', None),
            (record, 'empty', b''),
            (record, 'malformed', b'healthy\n'),
            (record, 'stale-boot', ('000000000001', '000000000002')),
            (record, 'missing-boot', ('boot_id=', 'missing=')),
            (record, 'stale-trial', (TRIAL, '2' * 64)),
            (record, 'missing-trial', ('trial_id=', 'missing=')),
            (record, 'not-pass', ('result=PASS', 'result=pending')),
            (record, 'unterminated-extra', b'junk'),
            (record, 'nul-suffix', b'\0'),
            (record, 'blank-extra', b'\n'),
            (record, 'oversized', b'x' * 257),
            (record, 'partial-publication', ('result=PASS\n', 'result=PA')),
            (descriptor, 'missing', None),
            (descriptor, 'empty', b''),
            (descriptor, 'bad-format', ('health-v1', 'health-v2')),
            (descriptor, 'wrong-mode', ('mode=try-once', 'mode=always')),
            (descriptor, 'stale-trial', (TRIAL, '2' * 64)),
            (descriptor, 'missing-trial', ('trial_id=', 'missing=')),
            (descriptor, 'wrong-primary', (PRIMARY, PRIMARY + '-other')),
            (descriptor, 'unterminated-extra', b'junk'),
            (descriptor, 'nul-suffix', b'\0'),
            (descriptor, 'oversized', b'x' * 257),
            (boot, 'missing', None),
            (boot, 'empty', b''),
            (boot, 'stale', ('000000000001', '000000000002')),
            (cmdline, 'missing', None),
            (cmdline, 'empty', b''),
            (cmdline, 'wrong-primary', (PRIMARY, PRIMARY + '-other')),
            (cmdline, 'prefixed-token', ('rog5.bundle=', 'xrog5.bundle=')),
            (cmdline, 'duplicate', ('rog5.bundle=',
                                      'rog5.bundle=other rog5.bundle=')),
        ]
        for path, label, value in cases:
            with self.subTest(path=path, mutation=label):
                root, _ = self.fixture('already-healthy-missing-timers')
                target = root/path
                if value is None:
                    target.unlink()
                elif isinstance(value, tuple):
                    target.chmod(0o644)
                    target.write_text(target.read_text().replace(*value))
                    target.chmod(0o444)
                else:
                    target.chmod(0o644)
                    target.write_bytes(target.read_bytes() + value if value else value)
                    target.chmod(0o444)
                self.assertEqual(self.fire_boot_timer(root), 'reboot\n')
                if label == 'oversized':
                    self.assertFalse((root/'content-reads').exists())

        for path in (record, descriptor):
            for mutation in ('mode', 'symlink', 'hardlink', 'directory', 'fifo'):
                with self.subTest(path=path, mutation=mutation):
                    root, _ = self.fixture('already-healthy-missing-timers')
                    target = root/path
                    if mutation == 'mode':
                        target.chmod(0o644)
                    elif mutation == 'hardlink':
                        os.link(target, root/'other-link')
                    else:
                        target.rename(root/'saved')
                        if mutation == 'symlink':
                            target.symlink_to(root/'saved')
                        elif mutation == 'directory':
                            target.mkdir()
                        else:
                            os.mkfifo(target)
                    self.assertEqual(self.fire_boot_timer(root), 'reboot\n')
        for owner in ('1000:0', '0:1000'):
            root, _ = self.fixture('already-healthy-missing-timers')
            self.assertEqual(self.fire_boot_timer(root, owner), 'reboot\n')

    def test_matching_but_malformed_identities_still_reboot(self):
        for field, invalid in [('boot_id', ''), ('boot_id', 'not-a-uuid'),
                               ('trial_id', ''), ('trial_id', 'A' * 64),
                               ('trial_id', '1' * 63),
                               ('primary_bundle', '../bad')]:
            with self.subTest(field=field, invalid=invalid):
                root, _ = self.fixture('already-healthy-missing-timers')
                runtime = root/'run/rog5-native-wifi'
                if field == 'boot_id':
                    paths = [root/'proc/sys/kernel/random/boot_id',
                             runtime/'healthy.record']
                    old = '00000000-0000-4000-8000-000000000001'
                elif field == 'trial_id':
                    paths = [runtime/'trial-descriptor', runtime/'healthy.record']
                    old = TRIAL
                else:
                    paths = [runtime/'trial-descriptor', root/'proc/cmdline']
                    old = PRIMARY
                for path in paths:
                    path.chmod(0o644)
                    path.write_text(path.read_text().replace(old, invalid))
                    path.chmod(0o444)
                self.assertEqual(self.fire_boot_timer(root), 'reboot\n')

    def test_timer_disarm_ignores_required_unit_stop_propagation(self):
        self.assertIn('rog5-wifi-probe-rollback.timer', SOURCE)
        self.assertIn('rog5-wifi-boot-rollback.timer', SOURCE)
        self.assertIn(
            'systemctl --job-mode=ignore-dependencies stop "$rollback_timer"',
            SOURCE,
        )

    def fixture(self, mutation=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        runtime = root/'run/rog5-native-wifi'; runtime.mkdir(parents=True)
        descriptor = runtime/'trial-descriptor'
        descriptor.write_text(
            'format=rog5-persistent-wifi-health-v1\n'
            f'trial_id={TRIAL}\nprimary_bundle={PRIMARY}\nmode=try-once\n')
        descriptor.chmod(0o444)
        (runtime/'interface').write_text('wlan0\n')
        proc = root/'proc'; (proc/'sys/kernel/random').mkdir(parents=True)
        (proc/'cmdline').write_text(f'rog5.bundle={PRIMARY}\n')
        (proc/'uptime').write_text('100.00 0.00\n')
        (proc/'sys/kernel/random/boot_id').write_text('00000000-0000-4000-8000-000000000001\n')
        pci = root/'sys/bus/pci/devices/0000:01:00.0'; pci.mkdir(parents=True)
        net = root/'sys/class/net/wlan0'; net.mkdir(parents=True)
        (net/'device').symlink_to(pci)
        (net/'carrier').write_text('1\n')
        power = root/'sys/class/power_supply'
        battery = power/'qcom-battmgr-bat'; battery.mkdir(parents=True)
        usb = power/'qcom-battmgr-usb'; usb.mkdir(parents=True)
        (battery/'health').write_text('Good\n'); (battery/'temp').write_text('300\n')
        (usb/'online').write_text('1\n')
        blocks = root/'sys/class/block'; blocks.mkdir(parents=True)
        for index in range(117):
            name = 'sda' if index == 0 else f'sda{index}'
            node = blocks/name; node.mkdir()
            (node/'ro').write_text('0\n' if name in ('sda', 'sda23') else '1\n')
        (blocks/'sda/sda24').mkdir()
        (blocks/'sda/sda24/ro').write_text('1\n')
        helper = runtime/'trial-state'
        already_healthy = bool(
            mutation and mutation.startswith('already-healthy')
        )
        helper.write_text(
            '#!/bin/sh\n[ "$1" = healthy ] && [ "$2" = "' + TRIAL +
            '" ] && [ "$3" = "' + PRIMARY + '" ] || exit 2\n'
            + ('exit 1\n' if mutation == 'helper-fail' else
               'echo already-healthy\n' if already_healthy else
               'echo healthy\n'))
        helper.chmod(0o700)
        record = runtime/'healthy.record'
        if mutation in (
            'already-healthy-missing-timers',
            'already-healthy-bad-record',
        ):
            record.write_text(
                'format=rog5-native-wifi-healthy-v1\n'
                'boot_id=00000000-0000-4000-8000-000000000001\n'
                f'trial_id={TRIAL}\n'
                + ('result=FAIL\n' if mutation == 'already-healthy-bad-record'
                   else 'result=PASS\n')
            )
            record.chmod(0o444)
        if mutation == 'usb-offline':
            (usb/'online').write_text('0\n')
        elif mutation == 'wrong-write-scope':
            (blocks/'sda42/ro').write_text('0\n')
        source = SOURCE.replace('/run/rog5-native-wifi', str(runtime))
        source = source.replace('/proc/', '@@ROG5_PROC_SLASH@@')
        source = source.replace('/sys/', '@@ROG5_SYS_SLASH@@')
        source = source.replace('@@ROG5_PROC_SLASH@@', str(proc) + '/')
        source = source.replace('@@ROG5_SYS_SLASH@@', str(root/'sys') + '/')
        harness = root/'harness.sh'
        harness.write_text(
            '#!/bin/sh\nset -eu\nselector=' + str(descriptor) + '\n'
            'record_fixture=' + str(record) + '\n'
            'id() { echo 0; }\n'
            'stat() { if [ "$3" = "$selector" ] || '
            '[ "$3" = "$record_fixture" ]; then echo 0:0:444:1; '
            'else command stat "$@"; fi; }\n'
            'probe_timer_active=' +
            ('missing\n' if mutation in (
                'already-healthy-missing-timers',
                'already-healthy-missing-timers-no-record',
                'healthy-missing-timers')
             else '1\n') +
            'boot_timer_active=' +
            ('missing\n' if mutation in (
                'already-healthy-missing-timers',
                'already-healthy-missing-timers-no-record',
                'healthy-missing-timers')
             else '1\n') +
            'systemctl() {\n'
            ' if [ "$1:$2" = --job-mode=ignore-dependencies:stop ]; then '
            '  case "$3" in\n'
            '   rog5-wifi-probe-rollback.timer) '
            '    [ "$probe_timer_active" != missing ] || return 5; '
            '    probe_timer_active=0 ;;\n'
            '   rog5-wifi-boot-rollback.timer) '
            '    [ "$boot_timer_active" != missing ] || return 5; '
            '    boot_timer_active=0 ;;\n'
            '   *) return 2 ;;\n'
            '  esac\n'
            '  return 0\n'
            ' fi\n'
            ' if [ "$1:$2" = is-active:--quiet ]; then\n'
            '  case "$3" in\n'
            '   rog5-wifi-probe-rollback.timer) [ "$probe_timer_active" = 1 ] ;;\n'
            '   rog5-wifi-boot-rollback.timer) [ "$boot_timer_active" = 1 ] ;;\n'
            '   *) return 0 ;;\n'
            '  esac\n'
            '  return\n'
            ' fi\n return 2\n}\n'
            'ip() { case "$*" in\n'
            ' "-4 -o address show dev wlan0 scope global") '
            'echo "3: wlan0 inet 192.0.2.2/24 scope global wlan0" ;;\n'
            ' "-4 route show default dev wlan0") '
            'echo "default via 192.0.2.1 dev wlan0" ;;\n'
            ' *) return 2 ;; esac; }\n'
            'sleep() { echo "300.00 0.00" >"' + str(proc/'uptime') + '"; }\n'
            + source)
        harness.chmod(0o700)
        return root, harness

    def test_healthy_trial_commits_then_disarms(self):
        root, harness = self.fixture()
        result = subprocess.run([*SHELL, str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS native Wi-Fi persistent trial healthy', result.stdout)
        self.assertTrue(
            (root/'run/rog5-native-wifi/healthy.record')
            .read_text().endswith('result=PASS\n')
        )

    def test_unsafe_or_uncommittable_state_keeps_rollback_armed(self):
        for mutation in ('usb-offline', 'wrong-write-scope', 'helper-fail'):
            with self.subTest(mutation=mutation):
                root, harness = self.fixture(mutation)
                result = subprocess.run([*SHELL, str(harness)], text=True,
                                        capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(
                    (root/'run/rog5-native-wifi/healthy.record').exists()
                )

    def test_already_healthy_rerun_accepts_absent_timers_and_exact_record(self):
        root, harness = self.fixture('already-healthy-missing-timers')
        result = subprocess.run([*SHELL, str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS native Wi-Fi persistent trial healthy', result.stdout)
        self.assertTrue(
            (root/'run/rog5-native-wifi/healthy.record')
            .read_text().endswith('result=PASS\n')
        )

    def test_already_healthy_rerun_rejects_changed_record(self):
        _, harness = self.fixture('already-healthy-bad-record')
        result = subprocess.run([*SHELL, str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)

    def test_already_healthy_fresh_boot_creates_record_after_timer_stop(self):
        root, harness = self.fixture('already-healthy-fresh-boot')
        result = subprocess.run([*SHELL, str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (root/'run/rog5-native-wifi/healthy.record')
            .read_text().endswith('result=PASS\n')
        )

    def test_already_healthy_without_record_still_requires_timers(self):
        root, harness = self.fixture(
            'already-healthy-missing-timers-no-record'
        )
        result = subprocess.run([*SHELL, str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            (root/'run/rog5-native-wifi/healthy.record').exists()
        )

    def test_first_commit_still_rejects_absent_timer(self):
        root, harness = self.fixture('healthy-missing-timers')
        result = subprocess.run([*SHELL, str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            (root/'run/rog5-native-wifi/healthy.record').exists()
        )


if __name__ == '__main__':
    unittest.main()
