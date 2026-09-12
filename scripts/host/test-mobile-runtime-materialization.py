#!/usr/bin/env python3
"""Real confined extraction fixtures; no package install scripts or hardware."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/host/materialize-mobile-runtime.py'
SPEC = importlib.util.spec_from_file_location('materializer', SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class Materialization(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def package(self, name, files, links=(), hardlinks=()):
        path = self.home / (name + '.pkg.tar.xz')
        with tarfile.open(path, 'w:xz') as archive:
            for filename, data in files.items():
                member = tarfile.TarInfo(filename)
                member.size = len(data)
                member.mode = 0o755
                archive.addfile(member, io.BytesIO(data))
            for pairs, kind in ((links, tarfile.SYMTYPE), (hardlinks, tarfile.LNKTYPE)):
                for filename, target in pairs:
                    member = tarfile.TarInfo(filename)
                    member.type, member.linkname = kind, target
                    archive.addfile(member)
        return {'name': name, 'archive': path.name,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_payload_links_and_metadata_exclusion(self):
        package = self.package('one', {'usr/bin/app': b'payload',
                                     '.INSTALL': b'touch /out/executed\n', '.PKGINFO': b'metadata'},
                               links=[('usr/bin/link', 'app')],
                               hardlinks=[('usr/bin/hard', 'usr/bin/app')])
        inventory = M.inventory([package], self.home)
        output = self.home / 'root'
        M.materialize([package], self.home, output, inventory)
        self.assertEqual((output / 'usr/bin/link').read_bytes(), b'payload')
        self.assertEqual((output / 'usr/bin/app').stat().st_ino, (output / 'usr/bin/hard').stat().st_ino)
        self.assertFalse((output / '.INSTALL').exists())
        self.assertFalse((output / '.PKGINFO').exists())
        self.assertFalse((output / 'executed').exists())
        self.assertEqual(len(M.tree_manifest(output)), 5)

    def test_conflicting_files_refused_before_extraction(self):
        a = self.package('a', {'usr/bin/app': b'a'})
        b = self.package('b', {'usr/bin/app': b'b'})
        with self.assertRaisesRegex(ValueError, 'conflicting package'):
            M.inventory([a, b], self.home)

    def test_changed_archive_refused(self):
        p = self.package('one', {'usr/bin/app': b'payload'})
        rows = M.inventory([p], self.home)
        (self.home / p['archive']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'archive changed'):
            M.materialize([p], self.home, self.home / 'root', rows)

    def test_traversal_and_special_members_refused(self):
        for name in ('../../outside', '/outside'):
            with self.subTest(name=name):
                p = self.package('bad', {name: b'not allowed'})
                with self.assertRaisesRegex(ValueError, 'unsafe archive'):
                    M.inventory([p], self.home)
        path = self.home / 'fifo.pkg.tar.xz'
        with tarfile.open(path, 'w:xz') as archive:
            member = tarfile.TarInfo('fifo')
            member.type = tarfile.FIFOTYPE
            archive.addfile(member)
        with self.assertRaisesRegex(ValueError, 'special archive'):
            M.inventory([{'name': 'fifo', 'archive': path.name, 'sha256': M.digest(path)}], self.home)

    def test_extractor_refuses_symlink_traversal_and_preserves_host(self):
        sentinel = self.home / 'outside'
        sentinel.write_bytes(b'unchanged')
        path = self.home / 'attack.tar'
        with tarfile.open(path, 'w') as archive:
            link = tarfile.TarInfo('escape')
            link.type, link.linkname = tarfile.SYMTYPE, str(self.home)
            archive.addfile(link)
            member = tarfile.TarInfo('escape/outside')
            member.size = 7
            archive.addfile(member, io.BytesIO(b'changed'))
        output = self.home / 'root'
        output.mkdir()
        with self.assertRaises(ValueError):
            M.extract_archive(path, output)
        self.assertEqual(sentinel.read_bytes(), b'unchanged')

    def test_extractor_does_not_overwrite_existing_payload(self):
        p = self.package('one', {'file': b'changed'})
        output = self.home / 'root'
        output.mkdir()
        (output / 'file').write_bytes(b'original')
        M.extract_archive(self.home / p['archive'], output)
        self.assertEqual((output / 'file').read_bytes(), b'original')

    def test_symlink_alias_cannot_hide_conflicting_payload(self):
        a = self.package('a', {'real/file': b'first'}, links=[('alias', 'real')])
        b = self.package('b', {'alias/file': b'second'})
        rows = M.inventory([a, b], self.home)
        with self.assertRaises(ValueError):
            M.materialize([a, b], self.home, self.home / 'root', rows)

    def test_disk_floor_refuses_before_root_creation(self):
        p = self.package('one', {'file': b'payload'})
        rows = M.inventory([p], self.home)
        with mock.patch.object(M.shutil, 'disk_usage', return_value=mock.Mock(free=M.RESERVE)):
            with self.assertRaisesRegex(ValueError, 'insufficient disk'):
                M.materialize([p], self.home, self.home / 'root', rows)
        self.assertFalse((self.home / 'root').exists())

    def command(self, output):
        return [sys.executable, '-O', str(SCRIPT), '--graph',
                str(ROOT / 'packaging/arch/mobile-package-snapshot-20260912.json'),
                '--cache', str(self.home), '--keyring', str(self.home / 'missing-keyring'),
                '--trusted', str(self.home / 'missing-trust'), '--revoked', str(self.home / 'missing-revocations'),
                '--output', str(output)]

    def test_missing_authentication_creates_no_payload_tree(self):
        output = self.home / 'output'
        result = subprocess.run(self.command(output), capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads((output / 'result.json').read_text())['status'], 'FAIL')
        self.assertFalse((output / 'root').exists())

    def test_existing_output_receipt_is_untouched(self):
        output = self.home / 'output'
        output.mkdir()
        (output / 'result.json').write_text('preserved')
        result = subprocess.run(self.command(output), capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((output / 'result.json').read_text(), 'preserved')


if __name__ == '__main__':
    unittest.main(verbosity=2)
