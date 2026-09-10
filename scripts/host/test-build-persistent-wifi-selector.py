#!/usr/bin/env python3

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/build-persistent-wifi-selector.py'
SPEC = importlib.util.spec_from_file_location('selector', SOURCE)
SELECTOR = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(SELECTOR)


class SelectorGeneration(unittest.TestCase):
    def run_cli(self, root, optimized=False, mutation=''):
        descriptor = self.descriptor()
        primary = self.manifest('persistent-native-root-wifi')
        fallback = self.manifest('persistent-native-root-v11')
        fallback_hash = hashlib.sha256(fallback).hexdigest()
        if mutation == 'fallback-hash': fallback_hash = '0'*64
        if mutation == 'cross-bundle': descriptor = self.descriptor('other')
        if mutation == 'header': primary = primary.replace(b'rog5-recovery-bundle-v2', b'wrong-bundle-v2')
        if mutation == 'profile': primary = primary.replace(b'profile=persistent-root-ro-v1', b'profile=wrong')
        if mutation == 'duplicate': primary += b'bundle=persistent-native-root-wifi\n'
        if mutation == 'missing': primary = primary.replace(b'kernel_size=1\n', b'')
        if mutation == 'crlf': primary = primary.replace(b'\n', b'\r\n')
        if mutation == 'timeout': primary = primary.replace(b'rollback_timeout=900', b'rollback_timeout=1')
        if mutation == 'target': primary = primary.replace(b'target_id=persistent-native-root-wifi', b'target_id=other')
        if mutation == 'hash-shape': primary = primary.replace(b'kernel_sha256='+b'1'*64, b'kernel_sha256=invalid')
        if mutation == 'size-shape': primary = primary.replace(b'kernel_size=1', b'kernel_size=-1')
        if mutation == 'oversize': primary = primary.replace(b'root_generation=none', b'root_generation='+b'x'*4096)
        for name, data in (('descriptor', descriptor), ('primary', primary), ('fallback', fallback)):
            (root/name).write_bytes(data)
        if mutation == 'symlink':
            (root/'primary').rename(root/'source')
            (root/'primary').symlink_to(root/'source')
        if mutation == 'hardlink': os.link(root/'primary', root/'alias')
        if mutation == 'existing-record': (root/'selector.json').write_bytes(b'preserved')
        command = [sys.executable, *(['-O'] if optimized else []), '-B', str(SOURCE),
                   '--trial-descriptor', str(root/'descriptor'), '--primary-manifest', str(root/'primary'),
                   '--fallback-manifest', str(root/'fallback'), '--expected-fallback-manifest-sha256',
                   fallback_hash, '--output', str(root/'selector')]
        return subprocess.run(command, capture_output=True, timeout=5)

    def test_cli_invalid_inputs_fail_before_output_in_normal_and_optimized_python(self):
        for mutation in ('fallback-hash', 'cross-bundle', 'header', 'profile', 'duplicate',
                         'missing', 'crlf', 'timeout', 'target', 'hash-shape', 'size-shape',
                         'oversize', 'symlink', 'hardlink', 'existing-record'):
            for optimized in (False, True):
                with self.subTest(mutation=mutation, optimized=optimized), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    result = self.run_cli(root, optimized, mutation)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(os.path.lexists(root/'selector'))
                    if mutation == 'existing-record':
                        self.assertEqual((root/'selector.json').read_bytes(), b'preserved')
                    else:
                        self.assertFalse(os.path.lexists(root/'selector.json'))

    def test_cli_valid_output_and_authority_unchanged_under_optimization(self):
        outputs = []
        for optimized in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = self.run_cli(root, optimized)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                record = json.loads((root/'selector.json').read_text())
                self.assertTrue(record['authority'].startswith('none;'))
                outputs.append(((root/'selector').read_bytes(), record))
        self.assertEqual(outputs[0], outputs[1])

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
        with self.assertRaises(ValueError):
            SELECTOR.generate(self.descriptor('other'),
                              self.manifest('persistent-native-root-wifi'),
                              fallback)
        with self.assertRaises(ValueError):
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
