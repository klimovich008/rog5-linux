#!/usr/bin/env python3
"""Offline preservation and hostile-input checks for the inert indicator trial."""
import copy
import gzip
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'buttons_trial', REPO/'scripts/device/build-buttons-indicator-trial-initramfs.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
A = M.ARCHIVE
PRODUCTION_PAYLOAD = dict(M.PAYLOAD)


def descriptor(trial='1', bundle='fixture-primary'):
    return ('format=rog5-persistent-wifi-health-v1\ntrial_id='+trial*64+
            '\nprimary_bundle='+bundle+'\nmode=try-once\n').encode()


class Composition(unittest.TestCase):
    def test_historical_tracked_lpg_cannot_enter_active_payload(self):
        old = (REPO/'artifacts/buttons-indicator-v1/leds-qcom-lpg.ko').read_bytes()
        self.assertEqual(M.sha(old),
                         '5885a9db2a8821f7c0ee9b16d92092d6d44f5c5092561e8e312f6047bb1a246c')
        expected = PRODUCTION_PAYLOAD['leds-qcom-lpg.ko']
        self.assertNotEqual(M.sha(old), expected[1])
        # Keep unrelated payloads small; retain the actual production LPG pin.
        # Validation is of bytes, so renaming the old directory cannot help.
        specs = dict(M.PAYLOAD, **{'leds-qcom-lpg.ko': expected})
        payload = dict(self.payload, **{'leds-qcom-lpg.ko': old})
        with mock.patch.object(M, 'PAYLOAD', specs):
            with self.assertRaisesRegex(ValueError, 'payload identity mismatch: leds-qcom-lpg'):
                M.validate_payload(payload)

    def setUp(self):
        self.members = {}
        A.add(self.members, 'init', b'unchanged startup and storage policy', 0o100755)
        A.add(self.members, 'shutdown', b'accepted shutdown fixture', 0o100755)
        shutdown_patch = mock.patch.object(M, 'OLD_SHUTDOWN_SHA256', M.sha(b'accepted shutdown fixture'))
        shutdown_patch.start()
        self.addCleanup(shutdown_patch.stop)
        A.add(self.members, 'rog5-ufs-modules/ufs-qcom.ko', b'unchanged UFS module', 0o100644)
        outer = dict(line.split('=', 1) for line in
                     (REPO/'initramfs/native-wifi/timing').read_text().splitlines()
                     if line and not line.startswith('#'))['outer_seconds'].encode()
        for directory in ('native-wifi', 'native-wifi-persistent'):
            root = REPO/'initramfs'/directory
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    name = M.PREFIX+str(path.relative_to(root))
                    data = path.read_bytes().replace(b'@OUTER_SECONDS@', outer)
                    if name in self.members:
                        A.replace(self.members, name, data)
                    else:
                        A.add(self.members, name, data, stat.S_IFREG |
                              (0o755 if os.access(path, os.X_OK) else 0o644))
        for name, data, mode in (
            ('kernel-release', (M.RELEASE+'\n').encode(), 0o444),
            ('automatic', b'rog5-native-wifi-boot-v1\n', 0o444),
            ('trial-descriptor', descriptor(), 0o444),
            ('trial-state', A.TRIAL_HELPER.read_bytes(), 0o755),
            ('probe-native-wifi.sh', (REPO/'scripts/device/probe-native-wifi.sh').read_bytes(), 0o755),
            ('boot-files.sha256', b'', 0o444),
        ):
            A.add(self.members, M.PREFIX+name, data, stat.S_IFREG | mode)
        A.install_wifi_iw(self.members)
        A.replace(self.members, M.CATALOG, M.catalog(self.members))
        self.payload = {name: ('fixture '+name).encode() for name in M.PAYLOAD}
        specs = {name: (len(data), M.sha(data), M.PAYLOAD[name][2])
                 for name, data in self.payload.items()}
        patcher = mock.patch.object(M, 'PAYLOAD', specs)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.new_descriptor = descriptor('2', 'fixture-successor')

    def run_compose(self, members=None, payload=None, new_descriptor=None, recatalog=True):
        members = copy.deepcopy(self.members if members is None else members)
        if recatalog:
            A.replace(members, M.CATALOG, M.catalog(members))
        base = gzip.compress(A.encode(members), mtime=0)
        return M.compose(base, M.sha(base), self.new_descriptor if new_descriptor is None else new_descriptor,
                         self.payload if payload is None else payload)

    def test_twins_preserve_storage_radio_and_startup_without_activation(self):
        first, report = self.run_compose()
        second, _ = self.run_compose()
        self.assertEqual(first, second)
        output = A.entries(gzip.decompress(first))
        for name, entry in self.members.items():
            if name not in (M.CATALOG, M.PREFIX+'trial-descriptor', 'shutdown'):
                self.assertEqual(output[name], entry, name)
        self.assertEqual(output['shutdown'][1], M.SHUTDOWN.read_bytes())
        self.assertEqual(set(output)-set(self.members),
                         {M.PAYLOAD_PREFIX[:-1]} | {M.PAYLOAD_PREFIX+n for n in self.payload})
        self.assertEqual(output[M.CATALOG][1], M.catalog(output))
        self.assertEqual(report['activation'], 'none; deferred to a separately guarded runtime test')

    def test_current_payload_requires_parent_and_corrected_daemon(self):
        # Regression: the old LED-only payload passed composition while neither
        # PMIC input child could bind on the real phone.
        self.assertEqual(set(PRODUCTION_PAYLOAD), {
            'led-class-multicolor.ko', 'qcom-pbs.ko', 'leds-qcom-lpg.ko',
            'qcom-pon.ko', 'rog5-key-indicatord'})
        self.assertEqual(PRODUCTION_PAYLOAD['qcom-pon.ko'],
                         (273336, '5e0b893338592d3d4a87b3d36459de6405313d1522f552e772f5bcda78b5aab3', 0o644))
        self.assertEqual(PRODUCTION_PAYLOAD['rog5-key-indicatord'],
                         (67520, '410e8936872b5fb80ef94adc6b66e7a9b0a76e7357158f6102772d235e1111c3', 0o755))
        led_only = dict(self.payload)
        del led_only['qcom-pon.ko']
        with self.assertRaisesRegex(ValueError, 'payload inventory mismatch'):
            self.run_compose(payload=led_only)
        packed, report = self.run_compose()
        output = A.entries(gzip.decompress(packed))
        self.assertEqual(output[M.PAYLOAD_PREFIX+'qcom-pon.ko'][1], self.payload['qcom-pon.ko'])
        self.assertEqual(report['authority'], 'unsigned offline composition only')
        self.assertFalse(report['kernel_rebuilt'])
        self.assertFalse(report['arch_root_rebuilt'])

    def test_wrong_outer_hash(self):
        with self.assertRaisesRegex(ValueError, 'base hash mismatch'):
            M.compose(b'not an archive', '0'*64, self.new_descriptor, self.payload)

    def test_shutdown_pairing_rejects_unknown_retained_or_corrected_helper(self):
        for mutation in ('bytes', 'owner', 'mode', 'missing'):
            altered = copy.deepcopy(self.members)
            if mutation == 'bytes':
                A.replace(altered, 'shutdown', b'unknown teardown')
            elif mutation == 'owner':
                altered['shutdown'][0][2] = 1000
            elif mutation == 'mode':
                altered['shutdown'][0][1] = 0o100644
            else:
                del altered['shutdown']
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'retained shutdown'):
                self.run_compose(members=altered)
        with mock.patch.object(M, 'SHUTDOWN_SHA256', '0'*64):
            with self.assertRaisesRegex(ValueError, 'corrected shutdown'):
                self.run_compose()

    def test_changed_missing_and_extra_payload(self):
        for name in self.payload:
            with self.subTest(name=name):
                changed = dict(self.payload); changed[name] += b'corrupt'
                with self.assertRaisesRegex(ValueError, 'payload identity'):
                    self.run_compose(payload=changed)
                missing = dict(self.payload); del missing[name]
                with self.assertRaisesRegex(ValueError, 'inventory'):
                    self.run_compose(payload=missing)
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.run_compose(payload={**self.payload, 'unexpected.service': b'enable'})

    def test_kernel_catalog_and_trial_identity(self):
        for name, data, error in (
            ('kernel-release', b'7.1.4-g7a5cef0db479\n', 'kernel release'),
            ('trial-state', b'wrong helper', 'trial helper'),
            ('probe-native-wifi.sh', b'old probe', 'unexpected successor'),
        ):
            with self.subTest(name=name):
                altered = copy.deepcopy(self.members)
                A.replace(altered, M.PREFIX+name, data)
                with self.assertRaisesRegex(ValueError, error):
                    self.run_compose(members=altered)
        altered = copy.deepcopy(self.members)
        A.replace(altered, M.CATALOG, b'wrong catalog\n')
        with self.assertRaisesRegex(ValueError, 'integrity catalog'):
            self.run_compose(members=altered, recatalog=False)
        for trial in (descriptor(), descriptor('2')):
            with self.assertRaisesRegex(ValueError, 'reuses'):
                self.run_compose(new_descriptor=trial)

    def test_existing_payload_and_unsafe_metadata(self):
        for mode in (stat.S_IFDIR | 0o755, stat.S_IFLNK | 0o777):
            altered = copy.deepcopy(self.members)
            A.add(altered, M.PAYLOAD_PREFIX[:-1], b'' if stat.S_ISDIR(mode) else b'/tmp', mode)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                self.run_compose(members=altered)
        for index, value in ((1, stat.S_IFLNK | 0o777), (2, 1000), (4, 2)):
            altered = copy.deepcopy(self.members)
            altered[M.PREFIX+'kernel-release'][0][index] = value
            with self.assertRaisesRegex(ValueError, 'metadata'):
                self.run_compose(members=altered)

    def test_input_files_reject_links_fifo_and_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            regular = root/'regular'; regular.write_bytes(b'payload')
            self.assertEqual(M.read_regular(regular, 7), b'payload')
            with self.assertRaises(ValueError):
                M.read_regular(regular, 6)
            linked = root/'linked'; linked.symlink_to(regular)
            with self.assertRaises(OSError):
                M.read_regular(linked, 7)
            os.link(regular, root/'hardlink')
            with self.assertRaises(ValueError):
                M.read_regular(regular, 7)
            fifo = root/'fifo'; os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                M.read_regular(fifo, 7)


if __name__ == '__main__':
    unittest.main()
