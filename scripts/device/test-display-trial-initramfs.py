#!/usr/bin/env python3
"""Inert display composition over the qualified corrected-buttons fixture."""
import copy
import gzip
import importlib.util
from pathlib import Path
import stat
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

B = load('display_composer', 'build-display-trial-initramfs.py')
F = load('buttons_fixture', 'test-buttons-indicator-trial-initramfs.py')


class DisplayComposition(unittest.TestCase):
    def setUp(self):
        fixture = F.Composition()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.base, _ = fixture.run_compose()
        self.original = B.ARCHIVE.entries(gzip.decompress(self.base))
        patcher = mock.patch.dict(B.BUTTONS.PAYLOAD, F.M.PAYLOAD, clear=True)
        patcher.start(); self.addCleanup(patcher.stop)
        self.payload = {n: ('display fixture '+n).encode() for n in B.PAYLOAD}
        pins = {n: (len(data), B.sha(data), 0o644) for n, data in self.payload.items()}
        patcher = mock.patch.dict(B.PAYLOAD, pins, clear=True)
        patcher.start(); self.addCleanup(patcher.stop)
        self.descriptor = F.descriptor('3', 'fixture-display-successor')

    def compose(self, members=None, payload=None, descriptor=None, recatalog=True):
        if members is None:
            base = self.base
        else:
            members = copy.deepcopy(members)
            if recatalog:
                B.ARCHIVE.replace(members, B.CATALOG, B.BUTTONS.catalog(members))
            base = gzip.compress(B.ARCHIVE.encode(members), mtime=0)
        return B.compose(base, B.sha(base), self.descriptor if descriptor is None else descriptor,
                         self.payload if payload is None else payload)

    def test_twins_preserve_all_runtime_storage_radio_and_buttons_bytes(self):
        first, result = self.compose()
        second, _ = self.compose()
        self.assertEqual(first, second)
        output = B.ARCHIVE.entries(gzip.decompress(first))
        allowed = {B.CATALOG, B.PREFIX+'trial-descriptor'}
        self.assertEqual(result['changed_existing_members'], sorted(allowed))
        for name, entry in self.original.items():
            if name not in allowed:
                self.assertEqual(output[name], entry, name)
        self.assertEqual(set(output)-set(self.original),
                         {B.PAYLOAD_PREFIX[:-1]} | {B.PAYLOAD_PREFIX+n for n in self.payload})
        self.assertEqual(output[B.CATALOG][1], B.BUTTONS.catalog(output))
        self.assertTrue(result['activation'].startswith('none added;'))
        self.assertEqual(result['corrected_buttons_payload'], 'preserved unchanged')
        self.assertFalse(result['kernel_rebuilt'])
        self.assertFalse(result['arch_root_rebuilt'])

    def test_missing_extra_and_changed_display_payload_refused(self):
        for name in self.payload:
            absent = dict(self.payload); del absent[name]
            changed = dict(self.payload); changed[name] += b'x'
            for payload in (absent, changed):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.compose(payload=payload)
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.compose(payload={**self.payload, 'startup.service': b'enable'})

    def test_historical_or_corrupt_buttons_payload_is_not_reclassified(self):
        prefix = B.BUTTONS.PAYLOAD_PREFIX
        for mutation in ('missing-parent', 'old-daemon', 'extra-module', 'owner'):
            members = copy.deepcopy(self.original)
            if mutation == 'missing-parent': del members[prefix+'qcom-pon.ko']
            elif mutation == 'old-daemon': B.ARCHIVE.replace(members, prefix+'rog5-key-indicatord', b'old')
            elif mutation == 'extra-module': B.ARCHIVE.add(members, prefix+'extra.ko', b'extra', 0o100644)
            else: members[prefix+'qcom-pon.ko'][0][2] = 1000
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.compose(members=members)

    def test_wrong_base_kernel_catalog_and_source_refused(self):
        with self.assertRaisesRegex(ValueError, 'base hash'):
            B.compose(self.base, '0'*64, self.descriptor, self.payload)
        for name, data in ((B.PREFIX+'kernel-release', b'7.1.4-rog5-display60-v1\n'),
                           (B.CATALOG, b'wrong'),
                           (B.PREFIX+'radio', b'old radio'),
                           (B.PREFIX+'probe-native-wifi.sh', b'old probe'),
                           ('shutdown', b'old shutdown'),
                           (B.PREFIX+'runtime', b'old runtime'),
                           (B.PREFIX+'trial-state', b'old helper')):
            members = copy.deepcopy(self.original)
            B.ARCHIVE.replace(members, name, data)
            with self.subTest(path=name), self.assertRaises(ValueError):
                self.compose(members=members, recatalog=name != B.CATALOG)

    def test_base_display_opt_in_refused(self):
        for name in B.DISPLAY_OPT_IN:
            members = copy.deepcopy(self.original)
            B.ARCHIVE.add(members, B.PREFIX+name, b'opt in', stat.S_IFREG | 0o644)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'activation opt-in'):
                self.compose(members=members)

    def test_existing_namespace_and_reused_identity_refused(self):
        for mode, data in ((stat.S_IFDIR | 0o755, b''), (stat.S_IFLNK | 0o777, b'/tmp')):
            members = copy.deepcopy(self.original)
            B.ARCHIVE.add(members, B.PAYLOAD_PREFIX[:-1], data, mode)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                self.compose(members=members)
        for descriptor in (F.descriptor('2', 'different-bundle'), F.descriptor('3', 'fixture-successor')):
            with self.assertRaisesRegex(ValueError, 'reuses'):
                self.compose(descriptor=descriptor)


if __name__ == '__main__':
    unittest.main()
