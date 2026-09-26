#!/usr/bin/env python3
"""Tests for install-default-kernel.py and its target script.

The target script runs under `unshare -r` against a temporary p24/p23 tree;
findmnt, blkid, blockdev, mount, systemd-run and systemctl are stubs that
keep the mount and block read-only state in files, so the write window,
relock and cleanup are observable.
"""
import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('installer', REPO/'scripts/host/install-default-kernel.py')
I = importlib.util.module_from_spec(spec)
spec.loader.exec_module(I)
TRIAL = 'ab'*32
BUNDLE = 'production-7.2.7-r9'
DESCRIPTOR = f'format=rog5-persistent-wifi-health-v1\ntrial_id={TRIAL}\nprimary_bundle={BUNDLE}\nmode=try-once\n'.encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def newc(members):
    out = b''
    for index, (name, data, mode) in enumerate(members+[('TRAILER!!!', b'', 0)]):
        encoded = name.encode()+b'\0'
        header = b'070701'+b''.join(b'%08x' % value for value in (
            index+1, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(encoded), 0))
        out += header+encoded
        out += b'\0'*(-len(out) % 4)+data
        out += b'\0'*(-len(out) % 4)
    return gzip.compress(out)


class Host(unittest.TestCase):
    def test_descriptor_fields(self):
        self.assertEqual(I.descriptor_fields(DESCRIPTOR), (TRIAL, BUNDLE))
        for bad in (DESCRIPTOR.replace(b'try-once', b'always'), DESCRIPTOR+b'x=1\n',
                    DESCRIPTOR.replace(BUNDLE.encode(), b'../v11'), DESCRIPTOR.replace(TRIAL.encode(), b'AB'*32)):
            with self.subTest(bad), self.assertRaises(ValueError):
                I.descriptor_fields(bad)

    def test_newc_member_finds_the_descriptor_only_as_a_regular_file(self):
        archive = newc([('init', b'#!/bin/sh\n', 0o100755), ('rog5-production-trial', b'', 0o040700),
                        ('rog5-production-trial/trial-descriptor', DESCRIPTOR, 0o100444)])
        self.assertEqual(I.newc_member(archive, 'rog5-production-trial/trial-descriptor'), DESCRIPTOR)
        self.assertIsNone(I.newc_member(archive, 'rog5-production-trial/commit'))
        with self.assertRaises(ValueError):
            I.newc_member(archive, 'rog5-production-trial')

    def test_render_prepends_only_safe_values(self):
        script = I.render(dict(bundle=BUNDLE, trial_id=TRIAL)).decode()
        self.assertTrue(script.startswith(f"#!/bin/sh\nbundle='{BUNDLE}'\ntrial_id='{TRIAL}'\n"))
        for bad in ("x'; reboot; '", 'a b', '$(id)', '', 'a\nb'):
            with self.subTest(bad), self.assertRaises(ValueError):
                I.render(dict(bundle=bad))

    def test_selector_fallback_is_read_from_the_selector(self):
        good = (b'format=rog5-slotb-selector-v2\ntrial_id='+b'a'*64+b'\nprimary_bundle=p\nprimary_manifest_sha256='
                + b'b'*64+b'\nfallback_bundle=persistent-native-root-v11\nfallback_manifest_sha256='+b'c'*64+b'\nmode=try-once\n')
        self.assertEqual(I.selector_fallback(good), ('persistent-native-root-v11', 'c'*64))
        for bad in (good.replace(b'selector-v2', b'selector-v1'), good.replace(b'root-v11', b'../v11'),
                    good.replace(b'c'*64, b'c'*63)):
            with self.assertRaises(ValueError):
                I.selector_fallback(bad)

    def test_archive_name_is_unique_per_bundle_and_record(self):
        self.assertEqual(I.archive_name(BUNDLE, 'f'*64), f'wifi-trial-state.archived-before-{BUNDLE}-'+'f'*64)


STUBS = {
    'findmnt': '''case "$4" in
	*/p24) [ "$3" = SOURCE ] && echo /dev/sda24 || echo "$(cat $S/p24-mount),relatime" ;;
	*/p23) [ "$3" = SOURCE ] && echo /dev/sda23 || echo rw ;;
	/run) echo tmpfs ;;
esac''',
    'blkid': '''case $1 in /dev/sda24) echo '/dev/sda24: UUID="8b03827a-cc2d-4408-8558-e9b61195f96b"' ;;
	/dev/sda23) echo '/dev/sda23: UUID="0892bacf-3e02-41b0-84a4-5f05c2df7ce5"' ;; esac''',
    'blockdev': '''echo "blockdev $*" >>$S/calls
case $1 in --getsize64) echo 34359717888 ;; --setrw) echo 0 >$S/block/sda24/ro ;; --setro) echo 1 >$S/block/sda24/ro ;; esac''',
    'mount': '''echo "mount $*" >>$S/calls
[ -e $S/fail-remount-rw ] && [ "$2" = remount,rw ] && exit 1
case $2 in remount,ro) echo ro >$S/p24-mount ;; remount,rw) echo rw >$S/p24-mount ;; esac''',
    'systemd-run': 'echo "systemd-run $*" >>$S/calls; touch $S/timer',
    'systemctl': '''echo "systemctl $*" >>$S/calls
case $1 in show) echo not-found ;; is-active) [ -e $S/timer ] ;; *) rm -f $S/timer ;; esac''',
}


def unshare_ok():
    return subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Target(unittest.TestCase):
    def setUp(self):
        self.dir = d = Path(tempfile.mkdtemp(prefix='rog5-install-'))
        self.stub = d/'stub'
        (self.stub/'bin').mkdir(parents=True)
        for name, body in STUBS.items():
            (self.stub/'bin'/name).write_text(f'#!/bin/sh\nS={self.stub}\n{body}\n')
            (self.stub/'bin'/name).chmod(0o755)
        (self.stub/'p24-mount').write_text('ro\n')
        for disk, ro in (('sda', 0), ('sda23', 0), ('sda24', 1), ('sdb', 1)):
            (self.stub/'block'/disk).mkdir(parents=True)
            (self.stub/'block'/disk/'ro').write_text(f'{ro}\n')
        power = d/'power'
        for name, value in (('qcom-battmgr-bat/health', 'Good'), ('qcom-battmgr-bat/temp', '300'),
                            ('qcom-battmgr-bat/voltage_now', '8405000'), ('qcom-battmgr-bat/capacity', '100'),
                            ('qcom-battmgr-usb/online', '1')):
            (power/name).parent.mkdir(parents=True, exist_ok=True)
            (power/name).write_text(value+'\n')
        self.p24, self.p23, self.source = d/'p24', d/'p23', d/'source'
        linux = self.p24/'boot/rog5-linux'
        (linux/'bundles').mkdir(parents=True)
        self.fallback = {}
        (linux/'bundles'/I.FALLBACK).mkdir()
        for name in I.FILES:
            data = b'v11 '+name.encode()
            (linux/'bundles'/I.FALLBACK/name).write_bytes(data)
            self.fallback[name] = sha(data)
        self.selector_old = b'format=rog5-slotb-selector-v2\nold\n'
        (linux/'selector').write_bytes(self.selector_old)
        (linux/'selector').chmod(0o600)
        (self.p23/'rog5/boot').mkdir(parents=True)
        self.record_old = b'format=rog5-persistent-wifi-trial-v1\nforeign\nstate=healthy\n'
        (self.p23/'rog5/boot/wifi-trial-state').write_bytes(self.record_old)
        (self.p23/'rog5/boot/wifi-trial-state').chmod(0o600)
        self.source.mkdir()
        self.payload = {}
        for name in I.FILES+('selector',):
            data = b'new '+name.encode()
            (self.source/name).write_bytes(data)
            self.payload[name] = sha(data)
        self.values = dict(
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), bundle=BUNDLE, trial_id=TRIAL,
            payload_image=self.payload['Image'], payload_dtb=self.payload['board.dtb'],
            payload_initramfs=self.payload['initramfs.cpio.gz'], payload_manifest=self.payload['manifest'],
            payload_signature=self.payload['manifest.sig'],
            selector_old_sha256=sha(self.selector_old), selector_old_size=len(self.selector_old),
            selector_new_sha256=self.payload['selector'],
            record_old_sha256=sha(self.record_old), record_archive=I.archive_name(BUNDLE, sha(self.record_old)),
            fallback_bundle=I.FALLBACK, fallback_install=0,
            fallback_image=self.fallback['Image'], fallback_dtb=self.fallback['board.dtb'],
            fallback_initramfs=self.fallback['initramfs.cpio.gz'], fallback_manifest=self.fallback['manifest'],
            fallback_signature=self.fallback['manifest.sig'],
            p24_uuid=I.P24_UUID, p23_uuid=I.P23_UUID, p24_size=I.P24_SIZE,
            root_mount=str(self.p24), userdata_mount=str(self.p23), source_root=str(self.source),
            sys_block=str(self.stub/'block'), sys_power=str(power),
            install_path=f'{self.stub}/bin:/usr/bin:/bin')

    def tearDown(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.dir)])
        shutil.rmtree(self.dir)

    def run_target(self, mode, **changes):
        script = I.render(dict(self.values, **changes))
        result = subprocess.run(['unshare', '-r', 'sh', '-s', '--', mode], input=script,
                                capture_output=True, timeout=60)
        return result.returncode, (result.stdout+result.stderr).decode()

    def calls(self):
        path = self.stub/'calls'
        return path.read_text().splitlines() if path.exists() else []

    def linux(self):
        return self.p24/'boot/rog5-linux'

    def assert_untouched(self):
        self.assertEqual((self.linux()/'selector').read_bytes(), self.selector_old)
        self.assertEqual((self.p23/'rog5/boot/wifi-trial-state').read_bytes(), self.record_old)
        self.assertEqual((self.stub/'block/sda24/ro').read_text(), '1\n')
        self.assertEqual((self.stub/'p24-mount').read_text().strip(), 'ro')

    def test_usb_disks_are_outside_the_write_scope(self):
        # A writable USB disk (a hub's card reader) is not on the UFS.
        usb = self.dir/'devices/xhci-hcd.1.auto/usb1/1-1/1-1.1/host1/block/sdh'
        usb.mkdir(parents=True)
        (usb/'ro').write_text('0\n')
        (self.stub/'block/sdh').symlink_to(usb)
        self.assertEqual(self.run_target('--inspect'), (0, 'PASS default kernel inspection scope= sda sda23\n'))

    def test_inspect_and_preflight_are_read_only(self):
        self.assertEqual(self.run_target('--inspect'), (0, 'PASS default kernel inspection scope= sda sda23\n'))
        self.assertEqual(self.run_target('--preflight'), (0, 'PASS default kernel payload preflight\n'))
        self.assertEqual(self.calls(), ['blockdev --getsize64 /dev/sda24', 'systemctl show -p LoadState --value '
                                        'rog5-default-kernel-guard-abababababababab.timer']*2)
        self.assert_untouched()

    def test_stage_installs_swaps_relocks_and_archives(self):
        code, out = self.run_target('--stage')
        self.assertEqual(code, 0, out)
        self.assertTrue(out.endswith(I.STAGED.format(bundle=BUNDLE, fallback=I.FALLBACK, state='preserved')))
        target = self.linux()/'bundles'/BUNDLE
        self.assertEqual(sorted(p.name for p in target.iterdir()), sorted(I.FILES))
        for name in I.FILES:
            self.assertEqual(oct((target/name).stat().st_mode & 0o777), '0o400')
            self.assertEqual(sha((target/name).read_bytes()), self.payload[name])
        self.assertEqual(oct(target.stat().st_mode & 0o777), '0o700')
        self.assertEqual(sha((self.linux()/'selector').read_bytes()), self.payload['selector'])
        self.assertEqual((self.linux()/f'selector.rollback-{BUNDLE}').read_bytes(), self.selector_old)
        self.assertFalse((self.p23/'rog5/boot/wifi-trial-state').exists())
        self.assertEqual((self.p23/'rog5/boot'/self.values['record_archive']).read_bytes(), self.record_old)
        for name in I.FILES:
            self.assertEqual(sha((self.linux()/'bundles'/I.FALLBACK/name).read_bytes()), self.fallback[name])
        self.assertEqual((self.stub/'block/sda24/ro').read_text(), '1\n')
        self.assertEqual((self.stub/'p24-mount').read_text().strip(), 'ro')
        self.assertFalse((self.stub/'timer').exists())
        calls = self.calls()
        self.assertLess(calls.index('blockdev --setrw /dev/sda24'), calls.index(f'mount -o remount,rw {self.p24}'))
        self.assertTrue(any(c.startswith('systemd-run --quiet --unit=rog5-default-kernel-guard-') for c in calls))
        # The same values can never stage twice.
        code, out = self.run_target('--stage')
        self.assertEqual(code, 1)
        self.assertIn('FAIL default kernel install: selector metadata changed', out)

    def test_stage_can_install_a_new_fallback(self):
        (self.source/'fallback').mkdir()
        new = {}
        for name in I.FILES:
            data = b'safe '+name.encode()
            (self.source/'fallback'/name).write_bytes(data)
            new[name] = sha(data)
        changes = dict(fallback_bundle='production-7.2.7-safe-r1', fallback_install=1,
                       fallback_image=new['Image'], fallback_dtb=new['board.dtb'],
                       fallback_initramfs=new['initramfs.cpio.gz'], fallback_manifest=new['manifest'],
                       fallback_signature=new['manifest.sig'])
        self.assertEqual(self.run_target('--preflight', **changes), (0, 'PASS default kernel payload preflight\n'))
        code, out = self.run_target('--stage', **changes)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.endswith(I.STAGED.format(bundle=BUNDLE, fallback='production-7.2.7-safe-r1',
                                                     state='installed')))
        target = self.linux()/'bundles/production-7.2.7-safe-r1'
        self.assertEqual({n: sha((target/n).read_bytes()) for n in I.FILES}, new)
        self.assertEqual(oct(target.stat().st_mode & 0o777), '0o700')
        # The old fallback stays as it was, for a manual rollback.
        for name in I.FILES:
            self.assertEqual(sha((self.linux()/'bundles'/I.FALLBACK/name).read_bytes()), self.fallback[name])
        self.assertEqual((self.stub/'block/sda24/ro').read_text(), '1\n')

    def test_new_fallback_refusals(self):
        cases = [
            ('path exists', dict(fallback_install=1), None),
            ('transferred fallback Image changed', dict(fallback_bundle='production-7.2.7-safe-r1', fallback_install=1),
             lambda: (self.source/'fallback').mkdir()),
            ('primary and fallback are the same bundle', dict(fallback_bundle=BUNDLE), None),
            ('fallback_install must be 0 or 1', dict(fallback_install=2), None),
        ]
        for why, changes, setup in cases:
            with self.subTest(why):
                self.tearDown()
                self.setUp()
                if setup:
                    setup()
                code, out = self.run_target('--stage', **changes)
                self.assertEqual(code, 1, out)
                self.assertIn(why, out)
                self.assertNotIn('blockdev --setrw /dev/sda24', self.calls())

    def test_absent_record_stages_without_archive(self):
        (self.p23/'rog5/boot/wifi-trial-state').unlink()
        code, out = self.run_target('--stage', record_old_sha256='absent')
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(p.name for p in (self.p23/'rog5/boot').iterdir()), [])

    def test_failure_inside_the_window_relocks(self):
        (self.stub/'fail-remount-rw').touch()
        code, out = self.run_target('--stage')
        self.assertEqual(code, 1, out)
        self.assertIn('p24 remount failed', out)
        self.assert_untouched()
        self.assertFalse((self.linux()/'bundles'/BUNDLE).exists())
        self.assertIn('blockdev --setro /dev/sda24', self.calls())
        self.assertFalse((self.stub/'timer').exists())

    def test_refusals_before_any_write(self):
        cases = [
            ('boot identity changed', dict(boot_id='0'*8+'-0000-0000-0000-'+'0'*12), None),
            ('previous selector changed', dict(selector_old_sha256='0'*64), None),
            ('previous record changed', dict(record_old_sha256='0'*64), None),
            ('fallback Image changed', dict(fallback_image='0'*64), None),
            ('transferred selector changed', dict(selector_new_sha256='0'*64), None),
            ('path exists', {}, lambda: (self.linux()/'bundles'/BUNDLE).mkdir()),
            ('path exists', {}, lambda: (self.linux()/f'selector.rollback-{BUNDLE}').write_text('x')),
            ('write scope is sda sda23 sdb', {}, lambda: (self.stub/'block/sdb/ro').write_text('0\n')),
            ('battery temperature unsafe', {}, lambda: (self.dir/'power/qcom-battmgr-bat/temp').write_text('401\n')),
            ('USB power offline', {}, lambda: (self.dir/'power/qcom-battmgr-usb/online').write_text('0\n')),
            ('battery voltage unsafe', {}, lambda: (self.dir/'power/qcom-battmgr-bat/voltage_now').write_text('7300000\n')),
            ('battery capacity below 30 %', {}, lambda: (self.dir/'power/qcom-battmgr-bat/capacity').write_text('29\n')),
            ('p24 is not read-only', {}, lambda: (self.stub/'p24-mount').write_text('rw\n')),
            ('unexpected userdata boot state', {}, lambda: (self.p23/'rog5/state/good').mkdir(parents=True)),
        ]
        for why, changes, setup in cases:
            with self.subTest(why):
                self.tearDown()
                self.setUp()
                if setup:
                    setup()
                code, out = self.run_target('--stage', **changes)
                self.assertEqual(code, 1, out)
                self.assertIn(why, out)
                self.assertNotIn('blockdev --setrw /dev/sda24', self.calls())
                self.assertEqual((self.linux()/'selector').read_bytes(), self.selector_old)


if __name__ == '__main__':
    unittest.main(verbosity=2)
