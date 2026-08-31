#!/usr/bin/env python3
"""Execute the persistent Wi-Fi health gate against bounded fake endpoints."""

from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO/'initramfs/native-wifi-persistent/healthy').read_text()
TRIAL = '1' * 64
PRIMARY = 'persistent-native-root-wifi'


class PersistentWifiHealthy(unittest.TestCase):
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
        helper = root/'trial-helper'
        helper.write_text(
            '#!/bin/sh\n[ "$1" = healthy ] && [ "$2" = "' + TRIAL +
            '" ] && [ "$3" = "' + PRIMARY + '" ] || exit 2\n'
            + ('exit 1\n' if mutation == 'helper-fail' else 'echo healthy\n'))
        helper.chmod(0o700)
        if mutation == 'usb-offline':
            (usb/'online').write_text('0\n')
        elif mutation == 'wrong-write-scope':
            (blocks/'sda42/ro').write_text('0\n')
        source = SOURCE.replace('/run/rog5-native-wifi', str(runtime))
        source = source.replace('/usr/libexec/rog5-persistent-trial-state', str(helper))
        source = source.replace('/proc/', str(proc) + '/')
        source = source.replace('/sys/', str(root/'sys') + '/')
        harness = root/'harness.sh'
        harness.write_text(
            '#!/bin/sh\nset -eu\nselector=' + str(descriptor) + '\n'
            'id() { echo 0; }\n'
            'stat() { if [ "$3" = "$selector" ]; then echo 0:0:444:1; '
            'else command stat "$@"; fi; }\n'
            'timer_active=1\n'
            'systemctl() {\n'
            ' if [ "$1" = stop ]; then timer_active=0; return 0; fi\n'
            ' if [ "$1:$2" = is-active:--quiet ]; then\n'
            '  [ "$3:$timer_active" != rog5-wifi-boot-rollback.timer:0 ]; return\n'
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
        result = subprocess.run(['sh', str(harness)], text=True,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS native Wi-Fi persistent trial healthy', result.stdout)
        self.assertTrue((root/'run/rog5-native-wifi/healthy').read_text().endswith('result=PASS\n'))

    def test_unsafe_or_uncommittable_state_keeps_rollback_armed(self):
        for mutation in ('usb-offline', 'wrong-write-scope', 'helper-fail'):
            with self.subTest(mutation=mutation):
                root, harness = self.fixture(mutation)
                result = subprocess.run(['sh', str(harness)], text=True,
                                        capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root/'run/rog5-native-wifi/healthy').exists())


if __name__ == '__main__':
    unittest.main()
