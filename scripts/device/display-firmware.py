#!/usr/bin/env python3
"""Read-only A660 firmware prerequisite; no activation or future-root guarantee.

The pinned Linux firmware loader uses kernel_read_file_from_path_initns(),
which opens relative to init_task.fs's root. Require the caller's current root
and mount namespace to match PID 1, and retain/revalidate the entire pathname.
PID1 initially shares init_task.fs (init/main.c CLONE_FS), but userspace can
unshare it. Matching PID1 is a prerequisite, not proof of the kernel task root
after arbitrary root changes. This cannot certify switch_root, firmware
authentication, or a later kernel request.
"""
import hashlib
import os
from pathlib import Path
import stat
import re

PROC = Path('/proc')
SYS = Path('/sys')
PAYLOAD = Path('/run/rog5-native-wifi')
FIRMWARE = (
    ('qcom/a660_sqe.fw', 43292, 'd222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76'),
    ('qcom/a660_gmu.bin', 55252, '8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7'),
    ('qcom/sm8350/a660_zap.mbn', 1054648, '5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d'),
)
FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK


def need(ok, why):
    if not ok:
        raise ValueError(why)


def identity(st):
    return st.st_dev, st.st_ino


def mount_id(fd):
    info = os.open(PROC / 'self/fdinfo' / str(fd), FLAGS)
    try:
        raw = os.read(info, 4097)
        ids = re.findall(rb'^mnt_id:\s*([0-9]+)$', raw, re.MULTILINE)
        need(len(raw) <= 4096 and len(ids) == 1, 'root mount identity unavailable')
        return int(ids[0])
    finally:
        os.close(info)


def root_identity(fd):
    return identity(os.fstat(fd)) + (mount_id(fd),)


def protected(st, directory=False):
    need((stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode))
         and st.st_uid == 0 and st.st_gid == 0 and not st.st_mode & 0o022,
         'firmware path type/owner/permissions')


def stamp(st, directory=False):
    base = identity(st) + (st.st_mode, st.st_uid, st.st_gid)
    return base if directory else base + (st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


class Inputs:
    def __init__(self):
        self.handles = []
        self.paths = []
        self.context = []
        self.closed = False
        try:
            need(os.geteuid() == 0, 'firmware verification requires root')
            # These four intentional procfs magic links are not firmware paths.
            for process in ('self', '1'):
                for leaf in ('ns/mnt', 'root'):
                    path = PROC / process / leaf
                    fd = self.keep(os.open(path, os.O_RDONLY | os.O_CLOEXEC |
                                           (os.O_DIRECTORY if leaf == 'root' else 0)))
                    self.context.append((path, fd, root_identity(fd) if leaf == 'root'
                                         else identity(os.fstat(fd)), leaf == 'root'))
            self.root = self.keep(os.open('/', FLAGS | os.O_DIRECTORY))
            self.root_stamp = stamp(os.fstat(self.root), True)
            protected(os.fstat(self.root), True)
            self.check_context()
            self.parameter = self.open_path(SYS / 'module/firmware_class/parameters/path')
            self.check_parameter()
            for name, size, digest in FIRMWARE:
                fd = self.open_path(PAYLOAD / 'firmware' / name)
                before = os.fstat(fd)
                need(before.st_size == size and stat.S_IMODE(before.st_mode) == 0o644
                     and before.st_nlink == 1, 'firmware file size/mode/links')
                hashed = hashlib.sha256()
                remaining = size
                while remaining:
                    block = os.read(fd, min(65536, remaining))
                    need(bool(block), 'firmware truncated')
                    hashed.update(block)
                    remaining -= len(block)
                need(not os.read(fd, 1), 'firmware grew')
                need(hashed.hexdigest() == digest, 'firmware digest mismatch')
            self.check()
        except BaseException:
            try:
                self.close()
            except OSError:
                pass  # Preserve the setup failure after attempting every close.
            raise

    def keep(self, fd):
        self.handles.append(fd)
        return fd

    def open_path(self, path):
        need(path.is_absolute() and '..' not in path.parts, 'absolute firmware path required')
        parent = self.root
        for index, name in enumerate(path.parts[1:]):
            directory = index != len(path.parts) - 2
            fd = self.keep(os.open(name, FLAGS | (os.O_DIRECTORY if directory else 0), dir_fd=parent))
            current = os.fstat(fd)
            protected(current, directory)
            self.paths.append((parent, name, fd, stamp(current, directory), directory))
            parent = fd
        return parent

    def check_context(self):
        need(os.geteuid() == 0, 'firmware verification requires root')
        for path, fd, initial, is_root in self.context:
            current = os.open(path, os.O_RDONLY | os.O_CLOEXEC |
                              (os.O_DIRECTORY if is_root else 0))
            try:
                measure = root_identity if is_root else lambda value: identity(os.fstat(value))
                need(measure(fd) == initial == measure(current),
                     'firmware root/mount namespace changed')
            finally:
                os.close(current)
        need(self.context[0][2] == self.context[2][2], 'caller differs from PID1 mount namespace')
        current_root = os.open('/', FLAGS | os.O_DIRECTORY)
        try:
            need(root_identity(current_root) == root_identity(self.root), 'caller root changed')
        finally:
            os.close(current_root)
        need(self.context[1][2] == self.context[3][2] == root_identity(self.root)
             and identity(os.stat('/')) == identity(os.fstat(self.root)), 'caller differs from PID1 filesystem root')
        need(stamp(os.fstat(self.root), True) == self.root_stamp, 'firmware root changed')

    def check_parameter(self):
        os.lseek(self.parameter, 0, os.SEEK_SET)
        raw = os.read(self.parameter, 257)
        expected = str(PAYLOAD / 'firmware').encode()
        need(raw in (expected, expected + b'\n'), 'firmware search path changed')

    def check(self):
        """Revalidate current context, every path edge and parameter; raises on loss."""
        need(not self.closed, 'firmware inputs closed')
        self.check_context()
        for parent, name, fd, initial, directory in self.paths:
            need(stamp(os.fstat(fd), directory) == initial ==
                 stamp(os.stat(name, dir_fd=parent, follow_symlinks=False), directory),
                 'firmware pathname/input changed')
        self.check_parameter()
        # Catch a context transition during the pathname walk as well.
        self.check_context()
        return True

    def close(self):
        """Idempotently release all owned descriptors, including failed setup."""
        if self.closed:
            return
        self.closed = True
        first = None
        for fd in reversed(self.handles):
            try:
                os.close(fd)
            except OSError as error:
                first = first or error
        self.handles.clear()
        if first is not None:
            raise first


def open_inputs():
    return Inputs()
