#!/usr/bin/env python3
"""Self-contained syscall/path fixtures for the production read-only verifier."""
import importlib.util
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('firmware', Path(__file__).with_name('display-firmware.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
REAL_FSTAT = os.fstat
REAL_STAT = os.stat
MOUNT_ID = M.mount_id


class RootOwned:
    def __init__(self, st):
        self.st = st
        self.st_uid = self.st_gid = 0

    def __getattr__(self, key):
        return getattr(self.st, key)


class Firmware(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.proc = self.base / 'proc'
        self.sys = self.base / 'sys'
        self.payload = self.base / 'payload'
        self.parameter = self.sys / 'module/firmware_class/parameters/path'
        self.parameter.parent.mkdir(parents=True)
        self.parameter.write_text(str(self.payload / 'firmware')+'\n')
        self.parameter.chmod(0o644)
        self.namespace = self.base / 'namespace'
        self.namespace.write_bytes(b'namespace fixture')
        for process in ('self', '1'):
            (self.proc / process / 'ns').mkdir(parents=True)
            (self.proc / process / 'root').symlink_to('/')
            (self.proc / process / 'ns/mnt').symlink_to(self.namespace)
        rows = []
        for index, (name, size, _) in enumerate(M.FIRMWARE):
            path = self.payload / 'firmware' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = bytes([index+1])*size
            path.write_bytes(data)
            path.chmod(0o644)
            rows.append((name, size, hashlib.sha256(data).hexdigest()))
        self.patch('PROC', self.proc)
        self.patch('SYS', self.sys)
        self.patch('PAYLOAD', self.payload)
        self.patch('FIRMWARE', tuple(rows))  # Fixture bytes only; no production hash option.
        self.mock(M.os, 'geteuid', return_value=0)
        self.mock(M.os, 'fstat', side_effect=lambda fd: self.owned(REAL_FSTAT(fd)))
        self.mock(M.os, 'stat', side_effect=lambda *a, **kw: self.owned(REAL_STAT(*a, **kw)))
        self.mount_mock = self.mock(M, 'mount_id', return_value=1)
        self.inputs = None
        self.addCleanup(self.close)

    def patch(self, name, value):
        p = patch.object(M, name, value)
        p.start()
        self.addCleanup(p.stop)

    def mock(self, obj, name, **kwargs):
        p = patch.object(obj, name, **kwargs)
        result = p.start()
        self.addCleanup(p.stop)
        return result

    def owned(self, st):
        # Fixtures need neither root nor chown. /tmp's sticky world-write mode
        # is mapped only for the common ancestor, not any tested fixture path.
        wrapped = RootOwned(st)
        if (st.st_dev, st.st_ino) == (REAL_STAT('/tmp').st_dev, REAL_STAT('/tmp').st_ino):
            wrapped.st_mode = stat.S_IFDIR | 0o755
        return wrapped

    def close(self):
        if self.inputs:
            self.inputs.close()

    def open(self):
        self.inputs = M.open_inputs()
        return self.inputs

    def file(self):
        return self.payload / 'firmware' / M.FIRMWARE[0][0]

    def test_valid_and_idempotent_close(self):
        self.assertTrue(self.open().check())
        handles = self.inputs.handles[:]
        self.inputs.close()
        self.inputs.close()
        for fd in handles:
            with self.assertRaises(OSError):
                REAL_FSTAT(fd)
        with self.assertRaisesRegex(ValueError, 'closed'):
            self.inputs.check()

    def test_wrong_namespace_despite_valid_path(self):
        # Historical path/hash check accepts these bytes; kernel view differs.
        self.assertEqual(hashlib.sha256(self.file().read_bytes()).hexdigest(), M.FIRMWARE[0][2])
        other = self.base / 'other-ns'
        other.write_bytes(b'other namespace')
        path = self.proc / '1/ns/mnt'
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'mount namespace'):
            self.open()

    def test_wrong_pid1_root_despite_valid_path(self):
        path = self.proc / '1/root'
        path.unlink()
        path.symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, 'filesystem root'):
            self.open()

    def test_caller_root_mismatch(self):
        for process in ('self', '1'):
            path = self.proc / process / 'root'
            path.unlink()
            path.symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, 'filesystem root'):
            self.open()

    def test_context_changes_after_open(self):
        self.open()
        path = self.proc / '1/root'
        path.unlink()
        path.symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, 'namespace changed'):
            self.inputs.check()

    def test_same_inode_root_on_different_mount(self):
        self.mount_mock.side_effect = [1, 2] + [1]*20
        with self.assertRaisesRegex(ValueError, 'namespace changed|filesystem root'):
            self.open()

    def test_wrong_owner(self):
        target = self.file().stat().st_ino
        original = self.owned
        def ownership(st):
            result = original(st)
            if st.st_ino == target:
                result.st_uid = 1000
            return result
        with patch.object(self, 'owned', side_effect=ownership):
            with self.assertRaisesRegex(ValueError, 'owner'):
                self.open()

    def test_fdinfo_mount_identity(self):
        path = self.proc / 'self/fdinfo/123'
        path.parent.mkdir()
        path.write_bytes(b'pos:\t0\nflags:\t02300000\nmnt_id:\t99\nino:\t2\n')
        self.assertEqual(MOUNT_ID(123), 99)
        for raw in (b'mnt_id: 1\nmnt_id: 2\n', b'ino: 1\n', b'mnt_id: 2\n'+b'x'*4096):
            with self.subTest(raw=raw[:30]):
                path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, 'mount identity'):
                    MOUNT_ID(123)

    def test_namespace_changes_after_open(self):
        self.open()
        path = self.proc / 'self/ns/mnt'
        other = self.base / 'other'
        other.write_bytes(b'different')
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'namespace changed'):
            self.inputs.check()

    def test_parameter_mismatch(self):
        self.parameter.write_text('/other/path\n')
        with self.assertRaisesRegex(ValueError, 'search path'):
            self.open()

    def test_parameter_mutation_after_open(self):
        self.open()
        self.parameter.write_text('/other/path\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.inputs.check()

    def test_wrong_digest(self):
        self.file().write_bytes(b'x' * M.FIRMWARE[0][1])
        with self.assertRaisesRegex(ValueError, 'digest'):
            self.open()

    def test_wrong_size(self):
        self.file().write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'size'):
            self.open()

    def test_wrong_file_permissions(self):
        self.file().chmod(0o666)
        with self.assertRaisesRegex(ValueError, 'permissions'):
            self.open()

    def test_unprotected_directory(self):
        self.file().parent.chmod(0o777)
        with self.assertRaisesRegex(ValueError, 'permissions'):
            self.open()

    def test_symlink_file(self):
        path = self.file()
        target = path.with_suffix('.copy')
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises(OSError):
            self.open()

    def test_symlink_directory(self):
        path = self.file().parent
        target = path.with_name('other')
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises(OSError):
            self.open()

    def test_hardlink_file(self):
        os.link(self.file(), self.base / 'link')
        with self.assertRaisesRegex(ValueError, 'links'):
            self.open()

    def test_file_replacement(self):
        self.open()
        path = self.file()
        replacement = path.with_suffix('.copy')
        shutil.copyfile(path, replacement)
        replacement.replace(path)
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.inputs.check()

    def test_file_mutation(self):
        self.open()
        with self.file().open('r+b') as stream:
            stream.write(b'x')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.inputs.check()

    def test_intermediate_directory_rename(self):
        self.open()
        path = self.payload / 'firmware'
        saved = self.payload / 'saved'
        path.rename(saved)
        shutil.copytree(saved, path)
        # Retained file and leaf-parent descriptors still refer to valid bytes.
        # The full chain must reject replacement of their ancestor.
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.inputs.check()

    def test_failed_construction_closes_every_fd(self):
        handles = []
        real_open = os.open
        def opening(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            handles.append(fd)
            return fd
        self.file().write_bytes(b'x')
        with patch.object(M.os, 'open', side_effect=opening):
            with self.assertRaises(ValueError):
                self.open()
        self.assertTrue(handles)
        for fd in handles:
            with self.assertRaises(OSError):
                REAL_FSTAT(fd)

    def test_interruption_closes_every_fd(self):
        handles = []
        real_open = os.open
        def opening(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            handles.append(fd)
            return fd
        with patch.object(M.os, 'open', side_effect=opening), patch.object(M.hashlib, 'sha256', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.open()
        for fd in handles:
            with self.assertRaises(OSError):
                REAL_FSTAT(fd)

    def test_growth_read_is_bounded(self):
        real_read = os.read
        target = self.file().stat().st_ino
        count = 0
        def reading(fd, size):
            nonlocal count
            if REAL_FSTAT(fd).st_ino == target:
                count += size
                return b'x' * size
            return real_read(fd, size)
        with patch.object(M.os, 'read', side_effect=reading):
            with self.assertRaisesRegex(ValueError, 'grew'):
                self.open()
        self.assertEqual(count, M.FIRMWARE[0][1]+1)

    def test_nonroot(self):
        with patch.object(M.os, 'geteuid', return_value=1000):
            with self.assertRaisesRegex(ValueError, 'requires root'):
                self.open()


if __name__ == '__main__':
    unittest.main()
