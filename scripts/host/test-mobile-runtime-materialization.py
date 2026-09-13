#!/usr/bin/env python3
"""Real confined extraction fixtures; no package install scripts or hardware."""
import hashlib
import importlib.util
import io
import json
import os
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

    def package(self, name, files, links=(), hardlinks=(), mode=0o755):
        path = self.home / (name + '.pkg.tar.xz')
        with tarfile.open(path, 'w:xz') as archive:
            for filename, data in files.items():
                member = tarfile.TarInfo(filename)
                member.size = len(data)
                member.mode = mode
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

    def test_execute_only_payload_is_readable_for_manifest(self):
        package = self.package('execute-only', {'usr/lib/helper': b'payload'}, mode=0o110)
        root = self.home / 'root'
        M.materialize([package], self.home, root, M.inventory([package], self.home))
        self.assertEqual((root / 'usr/lib/helper').read_bytes(), b'payload')
        self.assertTrue(M.tree_manifest(root))

    def materialize_policy(self, package, policy):
        root = self.home / ('root-' + policy)
        old_umask = os.umask(0o077)
        try:
            M.materialize([package], self.home, root, M.inventory([package], self.home),
                          permission_policy=policy)
        finally:
            os.umask(old_umask)
        self.assertEqual(os.umask(old_umask), old_umask)
        return root

    def test_package_read_preserves_public_access_under_private_caller_umask(self):
        p = self.package('app', {'usr/bin/app': b'payload'}, mode=0o755,
                         links=[('usr/bin/link', 'app')],
                         hardlinks=[('usr/bin/hard', 'usr/bin/app')])
        root = self.materialize_policy(p, 'package-read')
        for path in (root, root/'usr', root/'usr/bin', root/'usr/bin/app'):
            self.assertEqual(path.stat().st_mode & 0o7777, 0o755, str(path))
        self.assertEqual((root/'usr/bin/link').readlink(), Path('app'))
        self.assertEqual((root/'usr/bin/app').stat().st_ino, (root/'usr/bin/hard').stat().st_ino)

    def test_package_read_keeps_private_files_and_strips_privileges_and_writes(self):
        for mode, expected in ((0o600, 0o600), (0o640, 0o640), (0o644, 0o644),
                               (0o7777, 0o755), (0o666, 0o644), (0o111, 0o511)):
            with self.subTest(mode=oct(mode)):
                p = self.package('permissions', {'payload': b'data'}, mode=mode)
                root = self.home / ('mode-' + str(mode))
                M.materialize([p], self.home, root, M.inventory([p], self.home),
                              permission_policy='package-read')
                self.assertEqual((root/'payload').stat().st_mode & 0o7777, expected)

    def test_package_read_does_not_open_packaged_private_directory(self):
        p = self.package('private', {'private/file': b'data'}, mode=0o600)
        path = self.home / p['archive']
        with tarfile.open(path, 'w:xz') as archive:
            directory = tarfile.TarInfo('private')
            directory.type, directory.mode = tarfile.DIRTYPE, 0o700
            archive.addfile(directory)
        p['sha256'] = M.digest(path)
        root = self.materialize_policy(p, 'package-read')
        self.assertEqual((root/'private').stat().st_mode & 0o7777, 0o700)

    def test_owner_only_profile_retains_existing_modes(self):
        p = self.package('public', {'usr/bin/app': b'payload'}, mode=0o7777)
        root = self.materialize_policy(p, 'owner-only')
        for path in (root, root/'usr', root/'usr/bin', root/'usr/bin/app'):
            self.assertEqual(path.stat().st_mode & 0o7777, 0o700)

    def test_unknown_permission_profile_refuses_before_creation(self):
        with self.assertRaisesRegex(ValueError, 'unknown permission'):
            M.materialize([], self.home, self.home/'absent', [], permission_policy='wrong')
        self.assertFalse((self.home/'absent').exists())

    def test_package_read_does_not_rewrite_retained_owner_only_tree(self):
        p = self.package('public', {'usr/bin/app': b'payload'}, mode=0o755)
        old = self.materialize_policy(p, 'owner-only')
        before = M.tree_manifest(old)
        M.materialize([p], self.home, self.home/'new', M.inventory([p], self.home),
                      permission_policy='package-read')
        self.assertEqual(M.tree_manifest(old), before)

    def test_umask_restored_after_extraction_failure(self):
        p = self.package('one', {'file': b'payload'})
        original = os.umask(0o077)
        try:
            with mock.patch.object(M, 'extract_archive', side_effect=ValueError('extract failed')):
                with self.assertRaisesRegex(ValueError, 'extract failed'):
                    M.materialize([p], self.home, self.home/'root', M.inventory([p], self.home),
                                  permission_policy='package-read')
            self.assertEqual(os.umask(0o077), 0o077)
        finally:
            os.umask(original)

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
        self.assertEqual(output.stat().st_mode & 0o7777, 0o700)

    def test_requested_permission_policy_recorded_on_authentication_failure(self):
        output = self.home/'failed-package-read'
        result = subprocess.run(self.command(output) + ['--permission-policy', 'package-read'],
                                capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((output/'result.json').read_text())
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['permission_profile'], 'package-read')
        self.assertFalse((output/'root').exists())

    def test_existing_output_receipt_is_untouched(self):
        output = self.home / 'output'
        output.mkdir()
        (output / 'result.json').write_text('preserved')
        result = subprocess.run(self.command(output), capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((output / 'result.json').read_text(), 'preserved')


if __name__ == '__main__':
    unittest.main(verbosity=2)
