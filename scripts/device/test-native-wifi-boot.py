#!/usr/bin/env python3
"""Production-only USB independence; no real device, mount or network operations."""
import os
import importlib.util
import json
import gzip
from pathlib import Path
import subprocess
import tempfile
import unittest

R = Path(__file__).resolve().parents[2]


def function(source, name):
    start = source.index(name + '() {')
    return source[start:source.index('\n}', start) + 2]


class AutomaticWifi(unittest.TestCase):
    def test_watchdog_can_fire_before_basic_or_failed_p2(self):
        fixture = json.loads((R/'tests/fixtures/native-wifi/timer-default-dependencies.json').read_text())
        self.assertIn('basic.target', fixture['original_service_after'])
        self.assertNotIn('basic.target', fixture['fixed_service_after'])
        self.assertEqual(fixture['fixed_timer_after'], [])
        units = R/'initramfs/native-wifi/units'
        for name in ('rog5-wifi-boot-rollback.service', 'rog5-wifi-boot-rollback.timer',
                     'rog5-wifi-radio.service', 'rog5-wifi-wpa.service'):
            source = (units/name).read_text()
            self.assertIn('DefaultDependencies=no', source)
            self.assertIn('Conflicts=shutdown.target', source)
            self.assertIn('Before=shutdown.target', source)
        early = (units/'before-ssh.conf').read_text()
        self.assertIn('Requires=rog5-wifi-boot-rollback.timer', early)
        self.assertIn('After=rog5-wifi-boot-rollback.timer', early)
        rollback = (units/'rog5-wifi-boot-rollback.timer').read_text()
        self.assertNotIn('After=rog5-p2', rollback)
        self.assertIn('OnBootSec=@OUTER_SECONDS@s', rollback)
        probe = (R/'scripts/device/probe-native-wifi.sh').read_text()
        self.assertIn('--property=DefaultDependencies=no', probe)
        self.assertIn('--timer-property=DefaultDependencies=no', probe)

    def test_power_loader_never_turns_carrier_into_a_charging_requirement(self):
        source = (R/'scripts/device/load-persistent-root-power-usb.sh').read_text()
        body = function(source, 'require_ncm_carrier')
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'automatic'
            script = body.replace('/run/rog5-native-wifi/automatic', str(marker))
            for content, expected in [(None, 1), ('bad\n', 1), ('rog5-native-wifi-boot-v1\n', 0)]:
                if content is not None:
                    marker.write_text(content)
                result = subprocess.run(['sh', '-c', 'set -eu\n'
                    + 'stat() { echo 0:0:444:25:1; }; fail() { exit 1; };\n'
                    + script + '\nrequire_ncm_carrier'], capture_output=True)
                self.assertEqual(result.returncode, expected)
        # Missing carrier is bypassed, never power/route/role/storage checks.
        for check in ('wait_for_usb_online\n', 'power_role_is_sink "$power_role"',
                      "fail ncm-route 'NCM route changed'", "fail storage-before-ufs"):
            self.assertIn(check, source)

    def test_foreground_network_commands_do_not_reintroduce_fatal_optional_flags(self):
        source = (R/'initramfs/native-wifi/runtime').read_text()
        for function_name, expected in [('run_wpa', '-Dnl80211 -i wlp1s0 -c'),
                                        ('run_dhcp', '-4 -B -L -m 100')]:
            body = function(source, function_name).replace('\n\texec ', '\n\tprintf \'%s\\n\' ')
            result = subprocess.run(['sh', '-c', 'set -eu\nroot=/payload; state=/private; '
                + 'interface_identity() { interface=wlp1s0; }; fail() { exit 1; };\n'
                + body + '\n' + function_name], capture_output=True, text=True, check=True)
            command = result.stdout.splitlines()
            self.assertIn(expected, ' '.join(command))
            if function_name == 'run_wpa':
                for forbidden in ('-f', '-B', '-P', '-K'):
                    self.assertNotIn(forbidden, command)
                self.assertNotIn('password', result.stdout)
            else:
                self.assertEqual(command[-1], 'wlp1s0')
                self.assertNotIn('-1', command)  # must maintain/reacquire lease

    def test_radio_precedes_writable_state_and_cannot_restart(self):
        units = R/'initramfs/native-wifi/units'
        radio = (units/'rog5-wifi-radio.service').read_text()
        self.assertIn('Before=rog5-persistent-state.service basic.target', radio)
        self.assertIn('OnFailure=reboot.target', radio)
        self.assertIn('Restart=no', radio)
        self.assertIn('Requires=rog5-wifi-radio.service', (units/'before-state.conf').read_text())
        runtime = (R/'initramfs/native-wifi/runtime').read_text()
        self.assertIn('rog5-wifi-dhcp) target=multi-user.target', runtime)
        self.assertNotIn('Before=basic.target', (units/'rog5-wifi-dhcp.service').read_text())
        self.assertIn('systemd-resolved.service', (units/'rog5-wifi-dhcp.service').read_text())
        script = (R/'initramfs/native-wifi/radio').read_text()
        self.assertLess(script.index('rollback.timer'), script.index('for action in query mode held-oem'))
        self.assertIn('mkdir "$root/radio-entered"', script)
        self.assertIn('no', radio)
        self.assertIn('guard\n', script)
        self.assertIn('timeout -k "$kill_seconds" "$limit" "$root/module-once"', script)
        self.assertNotIn('insmod', script)
        self.assertIn('$((outer_seconds - radio_seconds - cleanup_seconds))', script)
        timing = (R/'initramfs/native-wifi/timing').read_text()
        result = subprocess.run(['sh', '-c', 'set -eu\n'+timing+
            '\n[ "$outer_seconds" -gt "$((radio_seconds + cleanup_seconds))" ]\n'
            '[ "$((query_seconds + mode_seconds + hold_seconds + 3*kill_seconds))" -lt "$outer_seconds" ]'], check=True)

    def test_newc_preserves_existing_entries_and_rejects_unsafe_input(self):
        spec = importlib.util.spec_from_file_location('wifi_archive', R/'scripts/device/build-native-wifi-boot-initramfs.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        members = {}
        module.add(members, 'lib/module.ko', b'ELF-unchanged', 0o100644)
        module.add(members, 'init', b'#!/bin/sh\n', 0o100755)
        module.add(members, 'bin/sh', b'busybox', 0o120777)
        old_module = members['lib/module.ko']
        module.replace(members, 'init', b'#!/bin/sh\necho test\n')
        module.add(members, 'new/regular', b'local-data', 0o100444)
        self.assertEqual(module.entries(module.encode(members)), members)
        self.assertEqual(list(module.entries(module.encode(members))), sorted(members))
        self.assertEqual(members['lib/module.ko'], old_module)
        for name in ('init', '../escape', '/absolute', 'bin/sh/child'):
            with self.assertRaises(AssertionError):
                module.add(members, name, b'bad', 0o100644)
        with self.assertRaises(AssertionError):
            module.compose(b'bad', b'bad', {'files': {'initramfs.cpio.gz': '0'*64}})
        # Execute the real release verifier's newc parser, not just our encoder.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); harness = root/'parser.c'; verifier = root/'parser'
            harness.write_text('#define main full_verifier_main\n#include "'+str(R/'tools/recovery_control/rog5-bundle-verify.c')+'"\n'
                '#undef main\nint main(int argc, char **argv) { if (argc != 2) return 2; '
                'int fd = open(argv[1], O_RDONLY | O_NOFOLLOW); if (fd < 0) return 2; '
                'verify_initramfs_gzip(fd, false, false, false); close(fd); return 0; }\n')
            subprocess.run(['gcc','-O2','-Wall','-Wextra','-Werror',str(harness),'-lcrypto','-lz','-o',str(verifier)], check=True)
            raw = module.encode(members)
            good = root/'good.gz'; good.write_bytes(gzip.compress(raw, mtime=0))
            subprocess.run([str(verifier),str(good)],check=True)
            bad = root/'bad.gz'; bad.write_bytes(gzip.compress(raw.replace(b'bin\0', b'zzz\0', 1), mtime=0))
            rejected = subprocess.run([str(verifier),str(bad)],capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b'not unique and sorted', rejected.stderr)

    def test_rendezvous_never_waits_for_usb_in_sealed_native_mode(self):
        source = (R / 'initramfs/persistent-root-init').read_text()
        body = function(source, 'wait_for_deferred_ufs_rendezvous')
        for native, expected in [('1', 0), ('0', 1)]:
            result = subprocess.run(['sh', '-c', 'set -eu\nnative_wifi_boot=' + native + '\n'
                + 'cat() { echo 0; }; sleep() { :; };\n' + body
                + '\nwait_for_deferred_ufs_rendezvous'], capture_output=True)
            self.assertEqual(result.returncode, expected)

    def test_only_sealed_readonly_native_mode_can_enable_usb_independence(self):
        source = (R / 'initramfs/persistent-root-init').read_text()
        body = function(source, 'prepare_native_wifi_boot')
        for native, storage, diag, content, expected in [
            ('1', 'read-only', '0', 'rog5-native-wifi-boot-v1\n', 0),
            ('0', 'read-only', '0', 'rog5-native-wifi-boot-v1\n', 1),
            ('1', 'local-write', '0', 'rog5-native-wifi-boot-v1\n', 1),
            ('1', 'read-only', '1', 'rog5-native-wifi-boot-v1\n', 1),
            ('1', 'read-only', '0', 'bad\n', 1),
        ]:
            with self.subTest(native=native, storage=storage, diag=diag, content=content):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp); payload = root/'payload'; payload.mkdir()
                    (payload/'automatic').write_text(content); (payload/'automatic').chmod(0o444)
                    script = body.replace('/rog5-native-wifi', str(payload)).replace(
                        '/run' + str(payload), str(root/'run'))
                    result = subprocess.run(['sh', '-c', 'set -eu\n'
                        + f'expected_native_root_mode={native}\nexpected_ufs_storage_mode={storage}\n'
                        + f'expected_ssh_diagnostic_mode={diag}\nnative_wifi_boot=0\n'
                        + 'stat() { echo 0:0:444:25:1; };\n' + script
                        + '\nprepare_native_wifi_boot'], capture_output=True)
                    self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == '__main__':
    unittest.main()
