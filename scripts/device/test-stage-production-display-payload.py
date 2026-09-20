#!/usr/bin/env python3
"""Exercise actual archive-to-loader layout with inert ARM64 ELF fixtures."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


P = load('display_payload', 'stage-production-display-payload.py')
F = load('module_fixture', 'test-production-display-modules.py')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class Payload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        F.Modules.setUpClass(); cls.addClassCleanup(F.Modules.doClassCleanups)

    def setUp(self):
        self.fixture = F.Modules(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        manifest = self.fixture.build(); self.archive = self.fixture.output
        self.root = self.fixture.root; self.output = self.root/'payload'
        self.expected = dict(sha256=sha(self.archive), bytes=self.archive.stat().st_size,
                             manifest=manifest, qualification_sha256='a'*64)
        self.helper = self.root/'inert-helper'
        self.helper.write_bytes(b'not executable; host input fixture\n')
        self.firmware = self.root/'firmware-inputs'; self.firmware.mkdir()
        fw = []
        for name in ('qcom/a660_sqe.fw', 'qcom/a660_gmu.bin', 'qcom/sm8350/a660_zap.mbn'):
            path = self.firmware/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('inert '+name).encode()); fw.append((name, path.stat().st_size, sha(path)))
        self.constants = dict(RELEASE=P.S.RELEASE,
            HELPER=('module-once', self.helper.stat().st_size, sha(self.helper), 0o755),
            MODULES=tuple((r['name'], r['path'], r['bytes'], r['sha256']) for r in manifest['modules']),
            FIRMWARE=tuple(fw))
        docs = []
        for name, _, _ in P.DOCUMENTATION:
            path = self.firmware/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('inert documentation '+name).encode())
            docs.append((name, path.stat().st_size, sha(path)))
        p = patch.object(P, 'DOCUMENTATION', tuple(docs)); p.start(); self.addCleanup(p.stop)
        self.sources = {'fixture': 'b'*64}
        self.reader = patch.object(P, 'source_contracts', lambda: (copy.deepcopy(self.constants), dict(self.sources)))
        self.reader.start(); self.addCleanup(self.reader.stop)

    def assemble(self):
        return P.assemble(self.archive, self.expected, self.helper, self.firmware, self.output)

    def rejected(self, message=None, exception=(ValueError, OSError)):
        before = set(os.listdir('/proc/self/fd'))
        with self.assertRaises(exception) as error: self.assemble()
        if message: self.assertIn(message, str(error.exception))
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.payload.*')))
        self.assertEqual(before, set(os.listdir('/proc/self/fd')))

    def test_complete_exact_layout_and_no_live_authority(self):
        before = set(os.listdir('/proc/self/fd')); result = self.assemble()
        self.assertEqual(result['modules'], 5); self.assertEqual(result['firmware_files'], 3)
        for key in ('physical', 'activation', 'firmware_root_transition'):
            self.assertEqual(result[key], 'NOT RUN')
        self.assertEqual(result['authority'], 'none')
        manifest = json.loads((self.output/'payload-manifest.json').read_text())
        self.assertEqual(manifest, result['manifest'])
        self.assertEqual(sha(self.output/'payload-manifest.json'), result['manifest_sha256'])
        expected = {'payload-manifest.json'}
        for row in manifest['files']:
            path = self.output/row['path']; expected.add(row['path'])
            self.assertEqual(sha(path), row['sha256'])
            self.assertEqual(path.stat().st_size, row['bytes'])
            self.assertEqual(path.stat().st_mode&0o777, row['mode'])
        self.assertEqual({str(p.relative_to(self.output)) for p in self.output.rglob('*') if p.is_file()}, expected)
        self.assertEqual(before, set(os.listdir('/proc/self/fd')))

    def test_old_module_only_intake_does_not_supply_loader_payload(self):
        # Source-level counterexample: the existing intake correctly validates
        # an archive, but neither binds it to a loader nor includes helper/fw.
        old = self.root/'module-only'
        P.S.materialize(self.archive, self.expected, old)
        self.assertFalse((old/'module-once').exists())
        self.assertFalse((old/'firmware/qcom/a660_sqe.fw').exists())
        self.reader.stop()
        self.rejected('loader cohort')  # Actual production consumer needs14.

    def test_consumer_literals_are_actual_source_constants(self):
        self.reader.stop(); constants, sources = P.source_contracts()
        loader = load('actual_loader', 'load-production-display.py')
        firmware = load('actual_firmware', 'display-firmware.py')
        self.assertEqual(constants['MODULES'], loader.MODULES)
        self.assertEqual(constants['HELPER'], loader.HELPER)
        self.assertEqual(constants['FIRMWARE'], firmware.FIRMWARE)
        self.assertEqual(constants['RELEASE'], loader.RELEASE)
        self.assertEqual(sources, {name: sha(HERE/name) for name in sources})

    def test_activation_order_can_differ_from_archive_order(self):
        self.constants['MODULES'] = tuple(reversed(self.constants['MODULES']))
        self.assemble()

    def test_valid_archive_with_wrong_loader_hash_refuses(self):
        rows = list(self.constants['MODULES']); row = list(rows[0]); row[3] = 'f'*64
        rows[0] = tuple(row); self.constants['MODULES'] = tuple(rows)
        self.rejected('loader cohort')

    def test_duplicate_loader_module_refuses(self):
        rows = list(self.constants['MODULES']); rows[1] = rows[0]
        self.constants['MODULES'] = tuple(rows); self.rejected('loader cohort')

    def test_release_mismatch_refuses(self):
        self.constants['RELEASE'] = 'historical'; self.rejected('loader release')

    def test_missing_helper_refuses_before_staging(self):
        self.helper.unlink(); self.rejected()

    def test_wrong_helper_bytes_refuse_before_staging(self):
        self.helper.write_bytes(b'x'*self.helper.stat().st_size); self.rejected('digest')

    def test_wrong_firmware_bytes_refuse_before_staging(self):
        path = self.firmware/self.constants['FIRMWARE'][2][0]
        path.write_bytes(b'x'*path.stat().st_size); self.rejected('digest')

    def test_missing_firmware_refuses_before_staging(self):
        (self.firmware/self.constants['FIRMWARE'][1][0]).unlink(); self.rejected()

    def test_missing_license_refuses_before_staging(self):
        (self.firmware/'LICENSES/LICENSE.qcom').unlink(); self.rejected()

    def test_wrong_notice_refuses_before_staging(self):
        path = self.firmware/'LICENSES/NOTICE.qcom'
        path.write_bytes(b'x'*path.stat().st_size); self.rejected('digest')

    def test_symlink_helper_refuses(self):
        original = self.helper.with_suffix('.real'); self.helper.rename(original)
        self.helper.symlink_to(original); self.rejected('symlink')

    def test_symlink_firmware_parent_refuses(self):
        original = self.root/'real-fw'; self.firmware.rename(original)
        self.firmware.symlink_to(original); self.rejected('symlink')

    def test_hardlink_helper_refuses(self):
        os.link(self.helper, self.root/'hardlink'); self.rejected('links')

    def test_unsafe_firmware_contract_refuses(self):
        rows = list(self.constants['FIRMWARE']); rows[0] = ('../../escape', 1, 'a'*64)
        self.constants['FIRMWARE'] = tuple(rows); self.rejected('path')

    def test_corrupt_module_archive_refuses_without_partial_payload(self):
        with self.archive.open('r+b') as stream: stream.write(b'broken')
        self.rejected('archive digest')

    def test_copy_interruption_closes_inputs_and_removes_only_scratch(self):
        original = P.copy_input
        def interrupted(*args):
            original(*args)
            raise KeyboardInterrupt('copy interrupted')
        with patch.object(P, 'copy_input', interrupted):
            self.rejected('interrupted', KeyboardInterrupt)
        self.assertTrue(self.helper.exists()); self.assertTrue(self.archive.exists())

    def test_input_mutation_during_copy_refuses(self):
        original = P.copy_input
        def mutate(*args):
            original(*args)
            self.helper.write_bytes(b'x'*self.helper.stat().st_size)
        with patch.object(P, 'copy_input', mutate): self.rejected('ingredient changed')

    def test_consumer_mutation_before_publication_refuses(self):
        original = P.copy_input
        def mutate(*args):
            original(*args); self.sources['fixture'] = 'c'*64
        with patch.object(P, 'copy_input', mutate): self.rejected('consumer sources changed')

    def test_existing_output_is_never_replaced(self):
        self.output.mkdir(); sentinel = self.output/'keep'; sentinel.write_text('retained')
        with self.assertRaisesRegex(ValueError, 'new absolute output'): self.assemble()
        self.assertEqual(sentinel.read_text(), 'retained')

    def test_atomic_publish_race_preserves_winner(self):
        original = P.S.publish
        def race(stage, output):
            if output == self.output:
                output.mkdir(); (output/'winner').write_text('retain')
            original(stage, output)
        with patch.object(P.S, 'publish', race):
            with self.assertRaises(OSError): self.assemble()
        self.assertEqual((self.output/'winner').read_text(), 'retain')
        self.assertEqual(list(self.output.iterdir()), [self.output/'winner'])
        self.assertFalse(list(self.root.glob('.payload.*')))

    def test_fsync_failure_after_final_rename_retains_published_bytes(self):
        original = P.S.publish
        def fail_after_rename(stage, output):
            original(stage, output)
            if output == self.output: raise OSError('parent fsync failed')
        with patch.object(P.S, 'publish', fail_after_rename):
            with self.assertRaisesRegex(OSError, 'parent fsync'): self.assemble()
        # An exception is not proof of absence after the atomic rename. Never
        # remove the final directory or retry over it; no success receipt issued.
        self.assertTrue((self.output/'payload-manifest.json').is_file())
        self.assertFalse(list(self.root.glob('.payload.*')))
        with self.assertRaisesRegex(ValueError, 'new absolute output'): self.assemble()

    def test_fsync_failure_after_inner_rename_cleans_private_tree(self):
        original = P.S.publish
        def fail_after_rename(stage, output):
            original(stage, output)
            raise OSError('inner parent fsync failed')
        with patch.object(P.S, 'publish', fail_after_rename): self.rejected('inner parent fsync')

    def test_umask_and_source_modes_do_not_change_output(self):
        self.helper.chmod(0o400)
        prior = os.umask(0o007)
        try: self.assemble()
        finally: os.umask(prior)
        self.assertEqual((self.output/'module-once').stat().st_mode&0o777, 0o755)
        for path in self.output.rglob('*'):
            self.assertFalse(path.stat().st_mode&0o022)

    def test_twins_have_identical_manifest_and_member_bytes(self):
        first = self.assemble(); self.output = self.root/'twin'
        second = self.assemble(); self.assertEqual(first, second)


if __name__ == '__main__': unittest.main()
