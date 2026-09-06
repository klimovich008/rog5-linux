#!/usr/bin/env python3
"""E02 runtime composition, with fake hardware and real file metadata checks.

Optional --sealed-archive replays the same cases with that archive's BusyBox
in a private root. This is not a systemd transaction or physical safety proof.
"""
import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

R = Path(__file__).resolve().parents[2]
SEALED_ARCHIVE = None


class OptionalDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive_root = None
        if SEALED_ARCHIVE:
            spec = importlib.util.spec_from_file_location(
                'sealed', R/'scripts/host/run-sealed-busybox.py')
            sealed = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sealed)
            cls.extraction = tempfile.TemporaryDirectory(prefix='rog5-e02-sealed-')
            cls.addClassCleanup(cls.extraction.cleanup)
            cls.archive_root = Path(cls.extraction.name)
            data = SEALED_ARCHIVE.read_bytes()
            sealed.extract(sealed.ARCHIVE.entries(gzip.decompress(data)), cls.archive_root)
            (cls.archive_root/'rog5-qemu').touch()
            print('sealed_archive_sha256=' + hashlib.sha256(data).hexdigest(), flush=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-e02-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root/'run/rog5-native-wifi'
        self.units = self.root/'run/systemd/system'
        self.panel = self.root/'backlight/panel0-backlight'
        self.tty = self.root/'tty1'
        for path in (self.payload/'units', self.units/'sysinit.target.wants',
                     self.root/'run/NetworkManager/conf.d', self.root/'lib', self.panel):
            path.mkdir(parents=True)
        (self.units/'rog5-p2-ready.service').write_text('[Service]\nExecStart=/run/rog5-p2-attest\n')
        (self.units/'rog5-p2-ready.service').chmod(0o644)
        for source in (R/'initramfs/native-wifi/units').iterdir():
            if source.is_file():
                (self.payload/'units'/source.name).write_bytes(source.read_bytes())
                (self.payload/'units'/source.name).chmod(0o644)
        for name in ('rog5-power-button.service', 'rog5-status-screen.service'):
            (self.payload/'units'/name).write_bytes((R/'packaging/arch'/name).read_bytes())
            (self.payload/'units'/name).chmod(0o644)
        for name in ('screen-toggle.sh', 'status-screen.sh', 'power-buttond.py'):
            (self.payload/name).write_bytes((R/'scripts/device'/name).read_bytes())
            (self.payload/name).chmod(0o755)
        (self.payload/'kernel-release').write_text('7.1.4-test\n')
        (self.payload/'qcom-pon.ko').write_text('fixture module; loader endpoint is mocked\n')
        (self.payload/'qcom-pon.ko').chmod(0o644)
        (self.panel/'brightness').write_text('0\n')
        (self.panel/'max_brightness').write_text('1023\n')
        self.tty.touch()
        self.loader()

    def loader(self, outcome='pwrkey-pass', status=0, mode='0444'):
        # Deliberate module/hardware endpoint, never insmod or contact an input.
        (self.payload/'load-pwrkey').write_text(
            '#!/bin/sh\nset -eu\n'
            f'printf "called\\n" >{shlex.quote(str(self.root/"loader-called"))}\n'
            f'printf "%s\\n" {shlex.quote(outcome)} >"$ROG5_PWRKEY_RESULT"\n'
            f'chmod {mode} "$ROG5_PWRKEY_RESULT"\nexit {status}\n')
        (self.payload/'load-pwrkey').chmod(0o755)

    def shell(self, script, *args):
        if self.archive_root:
            command = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
                       '--uid', '0', '--gid', '0', '--ro-bind', str(self.archive_root), '/',
                       '--dev', '/dev', '--tmpfs', '/tmp',
                       '--bind', str(self.root), str(self.root),
                       '--ro-bind', '/usr/bin/qemu-aarch64-static', '/rog5-qemu',
                       '--clearenv', '--setenv', 'PATH', '/bin:/sbin:/usr/bin:/usr/sbin',
                       '--setenv', 'LC_ALL', 'C', '/rog5-qemu', '/bin/busybox', 'sh']
        else:
            command = ['sh']
        return subprocess.run([*command, '-c', script, 'e02-fixture', *args],
                              capture_output=True, text=True, timeout=10)

    def install(self):
        source = (R/'initramfs/native-wifi/runtime').read_text()
        # Only absolute fixture roots and the fake tty's type are substituted.
        source = source.replace('[ ! -c /dev/tty1 ]', '[ ! -f /dev/tty1 ]')
        for old, new in (('/run/', str(self.root/'run')+'/'),
                         ('/newroot', str(self.root/'newroot')),
                         ('/lib/modules', str(self.root/'lib/modules')),
                         ('/sys/class/backlight', str(self.root/'backlight')),
                         ('/dev/tty1', str(self.tty))):
            source = source.replace(old, new)
        prelude = (
            'id() { echo 0; }\nuname() { echo 7.1.4-test; }\n'
            # Real modes, sizes, nlinks and contents; only fixture ownership is mapped.
            'stat() { command stat "$@" | sed ' + shlex.quote(
                f's/^{os.getuid()}:{os.getgid()}:/0:0:/') + '; }\n'
        )
        return self.shell(prelude + source, 'install')

    def assert_core(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.units/'rog5-p2-ready.service').read_text(),
                         '[Service]\nExecStart=/run/rog5-p2-attest\n')
        for name in ('rog5-wifi-radio.service', 'rog5-wifi-boot-rollback.timer'):
            self.assertTrue((self.units/'sysinit.target.wants'/name).is_symlink())
        self.assertTrue((self.units/'rog5-persistent-state.service.d/10-wifi-radio.conf').is_file())
        self.assertEqual((self.units/'rog5-wifi-failure.service').read_bytes(),
                         (R/'initramfs/native-wifi/units/rog5-wifi-failure.service').read_bytes())

    def enabled(self, name):
        return (self.units/'multi-user.target.wants'/f'rog5-{name}.service').is_symlink()

    def test_missing_input_does_not_block_core_or_status(self):
        self.loader('pwrkey-input-zero', 1)
        result = self.install()
        self.assert_core(result)
        self.assertIn('OBS absent power-button', result.stdout)
        self.assertFalse(self.enabled('power-button'))
        self.assertTrue(self.enabled('status-screen'))

    def test_fixture_uses_deployed_modes_under_private_log_umask(self):
        previous = os.umask(0o077)
        try:
            self.setUp()
            self.assert_core(self.install())
        finally:
            os.umask(previous)

    def test_absent_optional_payload_preserves_core_without_loading(self):
        for name in ('load-pwrkey', 'qcom-pon.ko', 'screen-toggle.sh',
                     'status-screen.sh', 'power-buttond.py',
                     'units/rog5-status-screen.service', 'units/rog5-power-button.service'):
            (self.payload/name).unlink()
        self.assert_core(self.install())
        self.assertFalse((self.root/'loader-called').exists())
        self.assertFalse(self.enabled('status-screen'))
        self.assertFalse(self.enabled('power-button'))

    def test_missing_display_or_tty_skips_both_optional_units(self):
        for missing in ('backlight', 'tty'):
            with self.subTest(missing=missing):
                self.setUp()
                if missing == 'backlight':
                    (self.panel/'brightness').unlink()
                else:
                    self.tty.unlink()
                result = self.install()
                self.assert_core(result)
                self.assertIn('OBS absent status-screen', result.stdout)
                self.assertFalse(self.enabled('status-screen'))
                self.assertFalse(self.enabled('power-button'))

    def test_p2_display_attempt_is_optional_but_backlight_safety_is_not(self):
        self.assert_core(self.install())
        self.assertTrue(self.enabled('status-screen'))
        self.assertTrue(self.enabled('power-button'))
        dropin = self.units/'rog5-p2-ready.service.d/10-screen-off.conf'
        self.assertIn('ExecStartPre=-/usr/local/bin/rog5-screen-toggle.sh off', dropin.read_text())
        # Execute the actual toggle with absent backlight: it really fails, so
        # the ignore-failure prefix matters. Do not pretend this runs systemd.
        command = f'BACKLIGHT_DIR={shlex.quote(str(self.root/"absent"))} sh {shlex.quote(str(self.payload/"screen-toggle.sh"))} off'
        self.assertNotEqual(self.shell(command).returncode, 0)
        attest = (R/'initramfs/persistent-root-attest').read_text()
        block = attest[attest.index('backlight_count=0\n'):attest.index('temporary=/run/.rog5-p2-ready.')]
        block = block.replace('/sys/class/backlight', str(self.root/'backlight'))
        for value, expected in (('0\n', 0), ('1\n', 1), ('absent', 0)):
            if value == 'absent':
                (self.panel/'brightness').unlink()
            else:
                (self.panel/'brightness').write_text(value)
            checked = self.shell('set -eu\nfail() { exit 1; }\n' + block)
            self.assertEqual(checked.returncode, expected)

    def test_artifact_and_unclassified_failures_stay_fatal(self):
        for outcome, status in (('pwrkey-module-load', 1), ('pwrkey-module-absent', 1),
                                ('pwrkey-module-vermagic', 1), ('pwrkey-module-name', 1),
                                ('pwrkey-platform-identity', 1), ('pwrkey-input-multiple', 1),
                                ('unsafe-power', 1), ('boot-chain', 1),
                                ('pwrkey-input-zero', 0), ('pwrkey-pass', 1),
                                ('pwrkey-input-zero', 137), ('pwrkey-input-zero\n', 1)):
            with self.subTest(outcome=outcome, status=status):
                self.setUp()
                self.loader(outcome, status)
                self.assertNotEqual(self.install().returncode, 0)
        for mutation in ('partial', 'mode', 'symlink', 'hardlink', 'installed-content',
                         'unit-collision', 'result-mode'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.loader('pwrkey-input-zero', 1)
                path = self.payload/'status-screen.sh'
                if mutation == 'partial': path.unlink()
                elif mutation == 'mode': path.chmod(0o777)
                elif mutation == 'symlink':
                    path.rename(self.payload/'saved'); path.symlink_to('saved')
                elif mutation == 'hardlink': os.link(path, self.payload/'alias')
                elif mutation == 'installed-content':
                    dest = self.root/'newroot/usr/local/libexec/rog5-status-screen'
                    dest.parent.mkdir(parents=True); dest.write_text('mismatch'); dest.chmod(0o755)
                elif mutation == 'unit-collision':
                    (self.units/'rog5-power-button.service').write_text('untrusted')
                else: self.loader('pwrkey-input-zero', 1, '0644')
                self.assertNotEqual(self.install().returncode, 0)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--sealed-archive':
        SEALED_ARCHIVE = Path(sys.argv[2]).resolve(strict=True)
        del sys.argv[1:3]
    unittest.main(verbosity=2)
