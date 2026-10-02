#!/usr/bin/env python3
"""The state stager's root-mount gate (verify_existing_root_mount) on mount
fixtures: exactly one /dev/sd mount, the exact p24 at /.rog5/root-ro, ext4,
ro and norecovery. No devices are touched."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
STAGER = REPO/'scripts/device/stage-persistent-service-state.sh'
GOOD = '/dev/sda24 /.rog5/root-ro ext4 ro,nosuid,nodev,noatime,norecovery 0 0\n'


def gate():
    text = STAGER.read_text()
    body = re.search(r'^verify_existing_root_mount\(\) \{\n.*?^\}\n', text, re.M | re.S).group(0)
    assert body.count('/proc/mounts') == 1
    return body.replace('/proc/mounts', '"$MOUNTS"').replace('[ -b "$root_device" ] || return 1', ':')


class RootMountGate(unittest.TestCase):
    def check(self, mounts):
        with tempfile.NamedTemporaryFile('w') as fixture:
            fixture.write(mounts)
            fixture.flush()
            script = 'userdata_disk=/dev/sda\n' + gate() + 'verify_existing_root_mount\n'
            return subprocess.run(['sh', '-c', script], env={'MOUNTS': fixture.name, 'PATH': '/usr/bin:/bin'},
                                  capture_output=True, text=True).returncode

    def test_the_exact_mount_passes(self):
        self.assertEqual(self.check('proc /proc proc rw 0 0\n' + GOOD), 0)

    def test_one_wrong_mount_fails(self):
        # Before 2026-10-02 the END block overwrote the rule's exit 1, so a
        # single wrong /dev/sd mount passed.
        for wrong in (GOOD.replace('sda24', 'sda23'), GOOD.replace('/.rog5/root-ro', '/mnt'),
                      GOOD.replace('ro,', 'rw,'), GOOD.replace(',norecovery', ''),
                      GOOD.replace('ext4', 'f2fs')):
            with self.subTest(wrong=wrong):
                self.assertEqual(self.check(wrong), 1)

    def test_zero_or_two_mounts_fail(self):
        self.assertEqual(self.check('proc /proc proc rw 0 0\n'), 1)
        self.assertEqual(self.check(GOOD + GOOD), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
