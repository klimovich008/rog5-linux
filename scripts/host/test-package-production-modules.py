#!/usr/bin/env python3
"""Offline checks for package-production-modules.py: deterministic packing,
member identity and refusal of an incomplete kernel build. The real
reproduction against build-r2 is recorded in test-results, not repeated here."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/package-production-modules.py'
spec = importlib.util.spec_from_file_location('package_production_modules', SOURCE)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class Packager(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def tree(self):
        tree = self.root/'tree'
        for name, data in (('lib/modules/r/kernel/b.ko', b'b'), ('lib/modules/r/kernel/a/a.ko', b'a'),
                           ('lib/modules/r/modules.dep', b'dep\n')):
            (tree/name).parent.mkdir(parents=True, exist_ok=True)
            (tree/name).write_bytes(data)
        (tree/'lib/modules/r/kernel/a/a.ko').chmod(0o600)
        return tree

    def test_pack_is_deterministic_sorted_and_normalized(self):
        tree = self.tree()
        first, second = self.root/'one.tar.gz', self.root/'two.tar.gz'
        entries, total = P.pack(tree, first)
        P.pack(tree, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(total, 6)
        with tarfile.open(first, 'r:gz') as archive:
            members = archive.getmembers()
        self.assertEqual([m.name for m in members], sorted(entries))
        self.assertTrue(all(m.isfile() and m.mode == 0o644 and m.uid == m.gid == m.mtime == 0 for m in members))
        self.assertEqual(entries['lib/modules/r/kernel/b.ko'], hashlib.sha256(b'b').hexdigest())

    def test_pack_refuses_an_existing_output(self):
        tree = self.tree()
        (self.root/'exists.tar.gz').write_bytes(b'')
        with self.assertRaises(FileExistsError):
            P.pack(tree, self.root/'exists.tar.gz')

    def test_incomplete_kernel_build_is_refused(self):
        build = self.root/'build'
        build.mkdir()
        (build/'result.json').write_text(json.dumps(dict(status='FAIL', stages={'kernel-build': dict(status='FAIL')})))
        argv = ['package', '--build', str(build), '--output', str(self.root/'out')]
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'did not pass'):
                P.main()

    def test_selection_is_the_booted_77_module_set(self):
        selection = json.loads(P.SELECTION.read_text())
        self.assertEqual(len(selection['board_modules']), 72)
        self.assertEqual(len(selection['board_modules']), len(set(selection['board_modules'])))
        self.assertEqual([m['name'] for m in selection['external_modules']],
                         ['rog5-bt-activate', 'rog5-pmic-pon-readonly', 'rog5-s12-ufs-vote', 'rog5-wifi-activate', 'rog5_fts3658u'])
        for item in selection['external_modules']:
            self.assertTrue((REPO/item['source']/'Makefile').is_file(), item)


if __name__ == '__main__':
    unittest.main(verbosity=2)
