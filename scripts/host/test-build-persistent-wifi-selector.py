#!/usr/bin/env python3

import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/build-persistent-wifi-selector.py'
SPEC = importlib.util.spec_from_file_location('selector', SOURCE)
SELECTOR = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(SELECTOR)


class SelectorGeneration(unittest.TestCase):
    def manifest(self, bundle):
        return (
            'format=rog5-recovery-bundle-v2\n'
            f'bundle={bundle}\nprofile=persistent-root-ro-v1\n'
            'kernel_size=1\nkernel_sha256=' + '1'*64 + '\n'
            'dtb_size=1\ndtb_sha256=' + '2'*64 + '\n'
            'initramfs_size=1\ninitramfs_sha256=' + '3'*64 + '\n'
            f'target_id={bundle}\ntarget_release=7.1.4-test\n'
            'rollback_timeout=900\ntarget_timeout=600\n'
            'a660_command_manifest_sha256=' + '0'*64 + '\n'
            'root_generation=none\nroot_tree_sha256=' + '0'*64 + '\n'
            'root_seal_sha256=' + '0'*64 + '\nroot_tree_entries=0\n'
            'root_subtree=none\n').encode()

    def descriptor(self, primary='persistent-native-root-wifi'):
        return (
            'format=rog5-persistent-wifi-health-v1\n'
            'trial_id=' + '1'*64 + '\n'
            f'primary_bundle={primary}\nmode=try-once\n').encode()

    def test_hashes_are_derived_after_manifest_creation(self):
        primary = self.manifest('persistent-native-root-wifi')
        fallback = self.manifest('persistent-native-root-v11')
        original = SELECTOR.FALLBACK_MANIFEST_SHA256
        SELECTOR.FALLBACK_MANIFEST_SHA256 = hashlib.sha256(fallback).hexdigest()
        self.addCleanup(setattr, SELECTOR, 'FALLBACK_MANIFEST_SHA256', original)
        selector, record = SELECTOR.generate(self.descriptor(), primary, fallback)
        text = selector.decode()
        self.assertIn('primary_manifest_sha256=', text)
        self.assertIn('fallback_manifest_sha256=' +
                      SELECTOR.FALLBACK_MANIFEST_SHA256, text)
        self.assertNotIn(record['primary_manifest_sha256'].encode(), self.descriptor())
        self.assertEqual(record['authority'],
                         'none; selector generation does not stage or select it')

    def test_cross_bundle_and_wrong_fallback_fail(self):
        fallback = self.manifest('persistent-native-root-v11')
        original = SELECTOR.FALLBACK_MANIFEST_SHA256
        SELECTOR.FALLBACK_MANIFEST_SHA256 = hashlib.sha256(fallback).hexdigest()
        self.addCleanup(setattr, SELECTOR, 'FALLBACK_MANIFEST_SHA256', original)
        with self.assertRaises(AssertionError):
            SELECTOR.generate(self.descriptor('other'),
                              self.manifest('persistent-native-root-wifi'),
                              fallback)
        with self.assertRaises(AssertionError):
            SELECTOR.generate(self.descriptor(),
                              self.manifest('persistent-native-root-wifi'),
                              self.manifest('not-v11'))

    def test_explicit_accepted_primary_can_be_the_next_fallback(self):
        primary_name = 'persistent-native-root-wifi-overlay-v1'
        fallback_name = 'persistent-native-root-wifi-v3'
        fallback = self.manifest(fallback_name)
        fallback_hash = hashlib.sha256(fallback).hexdigest()
        selector, record = SELECTOR.generate(
            self.descriptor(primary_name),
            self.manifest(primary_name),
            fallback,
            fallback_name,
            fallback_hash,
        )
        self.assertIn(
            f'fallback_bundle={fallback_name}\n'.encode(), selector
        )
        self.assertEqual(record['fallback_manifest_sha256'], fallback_hash)


if __name__ == '__main__':
    unittest.main()
