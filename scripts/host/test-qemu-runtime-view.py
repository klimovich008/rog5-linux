#!/usr/bin/env python3
"""Real extraction/view fixtures; QEMU interpretation is qualified separately."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
V = load('view', HERE/'prepare-qemu-runtime-view.py')
T = load('materialization_tests', HERE/'test-mobile-runtime-materialization.py')


class View(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        maker = T.Materialization(); maker.home = self.home
        self.package = maker.package('fixture', {'usr/bin/app': b'executable'},
            links=[('bin', 'usr/bin')], hardlinks=[('usr/bin/alias', 'usr/bin/app')], mode=0o755)
        self.package['status'] = 'PASS'
        self.runtime = self.home/'runtime'
        T.M.materialize([self.package], self.home, self.runtime, T.M.inventory([self.package], self.home))
        self.tree = self.home/'tree.json'
        self.tree.write_text(json.dumps(T.M.tree_manifest(self.runtime)))
        self.receipt = self.home/'receipt.json'
        self.receipt.write_text(json.dumps({'status':'PASS', 'installation_scripts_executed':False,
            'archive_audit':{'status':'PASS', 'packages':[self.package]},
            'tree_manifest_sha256':V.digest(self.tree)}))
        self.output = self.home/'view'

    def run_view(self):
        return V.prepare(self.runtime, self.tree, self.receipt, self.home, self.output)

    def test_regular_bytes_shared_and_permissions_separate(self):
        before = T.M.tree_manifest(self.runtime)
        result = self.run_view(); root = self.output/'root'
        self.assertEqual(result['status'], 'PASS_VIEW_PREPARED')
        self.assertEqual((root/'usr/bin/app').stat().st_ino, (self.runtime/'usr/bin/app').stat().st_ino)
        self.assertEqual((root/'usr/bin/app').stat().st_mode & 0o7777, 0o700)
        metadata = (root/'usr/bin/.virtfs_metadata/app').read_text()
        self.assertIn('virtfs.mode='+str(stat.S_IFREG|0o755)+'\n', metadata)
        self.assertIn('virtfs.uid=0\n', metadata)
        self.assertEqual((root/'usr/bin/.virtfs_metadata/app').stat().st_ino,
                         (root/'usr/bin/.virtfs_metadata/alias').stat().st_ino)
        self.assertFalse((root/'bin').is_symlink())
        self.assertEqual((root/'bin').read_text(), 'usr/bin')
        self.assertIn('virtfs.mode='+str(stat.S_IFLNK|0o777)+'\n',
                      (root/'.virtfs_metadata/bin').read_text())
        self.assertEqual(T.M.tree_manifest(self.runtime), before)

    def test_private_and_privileged_archive_modes(self):
        for mode, expected in ((0o600, 0o600), (0o7777, 0o755), (0o111, 0o511)):
            with self.subTest(mode=mode):
                maker = T.Materialization(); maker.home = self.home
                p=maker.package('modes', {'file':b'data'}, mode=mode);p['status']='PASS'
                self.assertEqual(V.package_modes([p], self.home)['file'], (stat.S_IFREG,expected))

    def test_archive_change_refused_before_view_creation(self):
        (self.home/self.package['archive']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'authentication'): self.run_view()
        self.assertFalse(self.output.exists())

    def test_tree_receipt_mismatch_refused(self):
        self.tree.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'receipt'): self.run_view()
        self.assertFalse(self.output.exists())

    def test_payload_change_refused_without_source_rewrite(self):
        file=self.runtime/'usr/bin/app';file.write_bytes(b'bad-content')
        with self.assertRaisesRegex(ValueError, 'retained file'): self.run_view()
        self.assertEqual(file.read_bytes(),b'bad-content')
        self.assertFalse((self.output/'result.json').exists())

    def test_mode_change_refused(self):
        (self.runtime/'usr/bin/app').chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'source mode'): self.run_view()

    def test_existing_output_untouched(self):
        self.output.mkdir();p=self.output/'result.json';p.write_text('preserved')
        with self.assertRaisesRegex(ValueError, 'already exists'): self.run_view()
        self.assertEqual(p.read_text(),'preserved')

    def test_reserved_and_unsafe_names(self):
        for value in ('../escape','/escape','.virtfs_metadata/a','a/.virtfs_metadata_root','.'):
            with self.subTest(value=value), self.assertRaises(ValueError): V.safe_name(value)

    def test_disk_reserve_before_creation(self):
        with mock.patch.object(V.shutil,'disk_usage',return_value=mock.Mock(free=V.RESERVE)):
            with self.assertRaisesRegex(ValueError,'insufficient disk'): self.run_view()
        self.assertFalse(self.output.exists())

    def test_manifest_cannot_use_symlink_parent(self):
        rows=json.loads(self.tree.read_text());rows.append({'path':'bin/hidden','type':'file'})
        self.tree.write_text(json.dumps(rows));receipt=json.loads(self.receipt.read_text())
        receipt['tree_manifest_sha256']=V.digest(self.tree);self.receipt.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'parent is not a directory'): self.run_view()
        self.assertFalse(self.output.exists())


if __name__ == '__main__': unittest.main(verbosity=2)
