#!/usr/bin/env python3
"""Install one admitted non-fixture headless SSH v3 export without replace."""

from __future__ import annotations

from collections import OrderedDict
import ctypes
import errno
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import stat
import subprocess
import sys
import tarfile
from typing import NoReturn


SOURCE_PATH = Path(__file__).resolve()
INSTALLED_ROOT = Path("/usr/libexec/rog5-recovery-host")
INSTALLED_PATH = INSTALLED_ROOT / SOURCE_PATH.name
HEADLESS_TOOL_PATH = (
    INSTALLED_ROOT / "headless-network-root.py"
    if SOURCE_PATH.parent == INSTALLED_ROOT
    else SOURCE_PATH.with_name("headless-network-root.py")
)
EXPORT_STORAGE_ROOT = Path("/home/rog5-linux")
DESTINATION = (
    EXPORT_STORAGE_ROOT
    / "exports"
    / "headless-ssh-network-root-v3"
)
LOCK_PATH = Path("/run/rog5-headless-ssh-export-install.lock")
BSDTAR = Path("/usr/bin/bsdtar")
ZERO_SHA256 = "0" * 64
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FIXTURE_FINGERPRINT = (
    "SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0"
)
FIXTURE_IDENTITIES = {
    "source_archive_sha256": (
        "2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a"
    ),
    "sealed_archive_sha256": (
        "60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b"
    ),
    "root_tree_sha256": (
        "6f8a8f11bfb581bb52ca7d590141ce465b8d48d8f9f4577a076b7a37604a2fd5"
    ),
    "root_seal_sha256": (
        "f443a47c456b33d670e6efd4a2e20cff2bc72061e7661472694acfbba45c8d5a"
    ),
}
AT_FDCWD = -100
RENAME_NOREPLACE = 1


class ExportInstallError(RuntimeError):
    """A stable deployment-export installation refusal."""


def fail(message: str) -> NoReturn:
    raise ExportInstallError(message)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        fail("cannot load the installed headless-root verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


HEADLESS = load_module("rog5_deployment_export_headless", HEADLESS_TOOL_PATH)


def identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def require_sha256(value: str, label: str) -> str:
    if not SHA256.fullmatch(value) or value == ZERO_SHA256:
        fail(f"{label} is not one nonzero SHA-256")
    return value


def fixed_installed_metadata() -> None:
    if SOURCE_PATH != INSTALLED_PATH:
        fail("installer is not running from its fixed installed path")
    for path in (SOURCE_PATH, HEADLESS_TOOL_PATH, HEADLESS.ROOT_TOOL_PATH):
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ExportInstallError(
                "installed export component is unavailable"
            ) from error
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o555
            or metadata.st_nlink != 1
        ):
            fail("installed export component metadata is unsafe")


def canonical_input(
    path: Path,
    *,
    owner: int,
    group: int,
    label: str,
) -> Path:
    if not path.is_absolute():
        fail(f"{label} path must be absolute")
    lexical = Path(os.path.abspath(path))
    try:
        named = lexical.lstat()
        resolved = lexical.resolve(strict=True)
        resolved_metadata = resolved.lstat()
        parent = resolved.parent.lstat()
    except OSError as error:
        raise ExportInstallError(f"{label} path is unavailable") from error
    if (
        lexical != resolved
        or stat.S_ISLNK(named.st_mode)
        or identity(named) != identity(resolved_metadata)
        or not stat.S_ISREG(named.st_mode)
        or named.st_uid != owner
        or named.st_gid != group
        or stat.S_IMODE(named.st_mode) not in {0o400, 0o444}
        or named.st_nlink != 1
        or named.st_size < 1
        or not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != owner
        or parent.st_gid != group
        or stat.S_IMODE(parent.st_mode) != 0o700
    ):
        fail(f"{label} metadata is unsafe")
    return resolved


def open_input(path: Path, maximum: int | None = None) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ExportInstallError("cannot open deployment export input") from error
    metadata = os.fstat(descriptor)
    if maximum is not None and metadata.st_size > maximum:
        os.close(descriptor)
        fail("deployment export input is too large")
    return descriptor


def hash_descriptor(
    descriptor: int,
    path: Path,
) -> tuple[int, str]:
    before = os.fstat(descriptor)
    digest = hashlib.sha256()
    observed = 0
    os.lseek(descriptor, 0, os.SEEK_SET)
    while block := os.read(descriptor, 1024 * 1024):
        digest.update(block)
        observed += len(block)
    after = os.fstat(descriptor)
    try:
        named = path.lstat()
    except OSError as error:
        raise ExportInstallError(
            "deployment export input disappeared"
        ) from error
    if (
        observed != before.st_size
        or identity(before) != identity(after)
        or identity(before) != identity(named)
    ):
        fail("deployment export input changed while being read")
    os.lseek(descriptor, 0, os.SEEK_SET)
    return observed, digest.hexdigest()


def snapshot_archive(
    descriptor: int,
    *,
    expected_size: int,
    expected_sha256: str,
    private_parent: Path,
) -> int:
    temporary_flag = getattr(os, "O_TMPFILE", 0)
    if not temporary_flag:
        fail("host lacks anonymous deployment archive snapshots")
    try:
        private = os.open(
            private_parent,
            temporary_flag | os.O_RDWR | os.O_CLOEXEC,
            0o600,
        )
    except OSError as error:
        raise ExportInstallError(
            "cannot create a private deployment archive snapshot"
        ) from error
    try:
        digest = hashlib.sha256()
        observed = 0
        os.lseek(descriptor, 0, os.SEEK_SET)
        while observed < expected_size:
            block = os.read(
                descriptor,
                min(1024 * 1024, expected_size - observed),
            )
            if not block:
                break
            digest.update(block)
            observed += len(block)
            view = memoryview(block)
            while view:
                written = os.write(private, view)
                if written <= 0:
                    fail("deployment archive snapshot made no progress")
                view = view[written:]
        trailing = os.read(descriptor, 1)
        if (
            observed != expected_size
            or trailing
            or digest.hexdigest() != expected_sha256
        ):
            fail("deployment archive does not match the admitted package")
        metadata = os.fstat(private)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 0
            or metadata.st_size != expected_size
        ):
            fail("private deployment archive snapshot is unsafe")
        os.lseek(private, 0, os.SEEK_SET)
        return private
    except BaseException:
        os.close(private)
        raise


def read_descriptor(
    descriptor: int,
    path: Path,
    maximum: int,
) -> bytes:
    size, _digest = hash_descriptor(descriptor, path)
    if size > maximum:
        fail("deployment package record is too large")
    payload = bytearray()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while len(payload) < size:
        block = os.read(descriptor, size - len(payload))
        if not block:
            break
        payload.extend(block)
    if len(payload) != size:
        fail("deployment package record changed while being read")
    os.lseek(descriptor, 0, os.SEEK_SET)
    return bytes(payload)


def parse_package(payload: bytes) -> OrderedDict[str, str]:
    values = HEADLESS.parse_canonical_payload(
        payload,
        HEADLESS.PACKAGE_KEYS_V3,
    )
    HEADLESS.validate_package(values)
    if (
        values["format"] != "rog5-headless-network-root-package-v3"
        or values["profile"] != "network-root-v1"
        or values["build_profile"] != "headless-ssh-v2"
    ):
        fail("deployment package tuple is unsupported")
    if values["authorized_key_fingerprint"] == FIXTURE_FINGERPRINT:
        fail("deployment package still carries the fixture SSH identity")
    for field, fixture in FIXTURE_IDENTITIES.items():
        if values[field] == fixture:
            fail("deployment package still carries a fixture root identity")
    return values


def inspect_archive(descriptor: int) -> None:
    names: set[str] = set()
    symlinks: set[str] = set()
    hardlinks: list[tuple[str, str]] = []
    root_is_directory = False
    duplicate = os.dup(descriptor)
    try:
        os.lseek(duplicate, 0, os.SEEK_SET)
        with os.fdopen(duplicate, "rb", closefd=True) as stream:
            duplicate = -1
            with tarfile.open(fileobj=stream, mode="r:*") as archive:
                for member in archive:
                    name = HEADLESS.ROOT_TOOL.clean_archive_path(member.name)
                    if name in names:
                        fail("deployment archive contains a duplicate path")
                    names.add(name)
                    if name != "root" and not name.startswith("root/"):
                        fail("deployment archive escapes its fixed root")
                    relative = name.removeprefix("root/")
                    if HEADLESS.ROOT_TOOL.has_embedded_credential(relative):
                        fail("deployment archive embeds a forbidden credential")
                    if member.sparse:
                        fail("deployment archive contains a sparse member")
                    if member.isdir():
                        if name == "root":
                            root_is_directory = True
                        continue
                    if member.isfile():
                        continue
                    if member.issym():
                        symlinks.add(name)
                        if not member.linkname:
                            fail("deployment archive has an empty symlink")
                        if not member.linkname.startswith("/"):
                            resolved = PurePosixPath(name).parent.joinpath(
                                member.linkname
                            )
                            normalized = os.path.normpath(str(resolved))
                            if normalized == ".." or normalized.startswith("../"):
                                fail("deployment archive symlink escapes root")
                        continue
                    if member.islnk():
                        target = HEADLESS.ROOT_TOOL.clean_archive_path(
                            member.linkname
                        )
                        if (
                            target == "."
                            or (
                                target != "root"
                                and not target.startswith("root/")
                            )
                        ):
                            fail("deployment archive has an invalid hard link")
                        hardlinks.append((name, target))
                        continue
                    if member.isdev():
                        fail("deployment archive contains a device or FIFO")
                    fail("deployment archive contains an unsupported member")
    except HEADLESS.ROOT_TOOL.ContractError as error:
        raise ExportInstallError(
            "deployment archive contains an unsafe path"
        ) from error
    except (OSError, tarfile.TarError) as error:
        raise ExportInstallError(
            "cannot inspect deployment archive"
        ) from error
    finally:
        if duplicate >= 0:
            os.close(duplicate)
        os.lseek(descriptor, 0, os.SEEK_SET)
    if not names or not root_is_directory:
        fail("deployment archive lacks its fixed root directory")
    for name in names:
        parts = PurePosixPath(name).parts
        for end in range(1, len(parts)):
            if PurePosixPath(*parts[:end]).as_posix() in symlinks:
                fail("deployment archive writes through a symlink")
    for _name, target in hardlinks:
        if target not in names or target in symlinks:
            fail("deployment archive hard link target is unsafe")


def write_manifest(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o444)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("deployment manifest write made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def extract_archive(descriptor: int, stage: Path) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    result = subprocess.run(
        [
            str(BSDTAR),
            "--numeric-owner",
            "--same-permissions",
            "--acls",
            "--xattrs",
            "--fflags",
            "-xpf",
            f"/proc/self/fd/{descriptor}",
            "-C",
            str(stage),
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
        },
        pass_fds=(descriptor,),
        text=True,
    )
    if result.returncode != 0:
        fail("deployment archive extraction failed")


def rename_noreplace(source: Path, destination: Path) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, "renameat2", None)
    if function is None:
        fail("host libc lacks renameat2 no-replace publication")
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    result = function(
        AT_FDCWD,
        os.fsencode(source),
        AT_FDCWD,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            fail("refusing an existing deployment export")
        raise OSError(error, os.strerror(error), destination)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_tree(root: Path) -> None:
    for directory, subdirectories, filenames in os.walk(
        root,
        topdown=False,
        followlinks=False,
    ):
        current = Path(directory)
        for name in filenames:
            path = current / name
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                continue
            if not stat.S_ISREG(metadata.st_mode):
                fail("deployment tree contains an unsafe fsync target")
            flags = os.O_RDONLY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(path, flags)
            try:
                if identity(metadata) != identity(os.fstat(descriptor)):
                    fail("deployment tree changed while being synced")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        for name in subdirectories:
            path = current / name
            metadata = path.lstat()
            if not (
                stat.S_ISDIR(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
            ):
                fail("deployment tree contains an unsafe directory entry")
        fsync_directory(current)


def install_export(
    archive_path: Path,
    package_path: Path,
    expected_package_sha256: str,
    *,
    owner: int,
    group: int,
) -> OrderedDict[str, str]:
    require_sha256(expected_package_sha256, "admitted package identity")
    archive = canonical_input(
        archive_path,
        owner=owner,
        group=group,
        label="deployment archive",
    )
    package = canonical_input(
        package_path,
        owner=owner,
        group=group,
        label="deployment package",
    )
    destination = DESTINATION
    lock_path = LOCK_PATH
    try:
        parent = HEADLESS.trusted_deployment_export_parent(
            destination,
            storage_root=EXPORT_STORAGE_ROOT,
            owner=os.geteuid(),
            group=os.getegid(),
        )
    except HEADLESS.HeadlessRootError as error:
        raise ExportInstallError(
            "deployment destination ancestry is unsafe"
        ) from error
    if destination.exists() or destination.is_symlink():
        fail("refusing an existing deployment export")
    package_descriptor = open_input(package, 64 * 1024)
    archive_descriptor = -1
    private_archive_descriptor = -1
    lock_descriptor = -1
    try:
        package_payload = read_descriptor(
            package_descriptor,
            package,
            64 * 1024,
        )
        package_sha256 = hashlib.sha256(package_payload).hexdigest()
        if package_sha256 != expected_package_sha256:
            fail("deployment package identity changed")
        values = parse_package(package_payload)
        archive_descriptor = open_input(archive)
        private_archive_descriptor = snapshot_archive(
            archive_descriptor,
            expected_size=int(values["sealed_archive_size"]),
            expected_sha256=values["sealed_archive_sha256"],
            private_parent=parent,
        )
        os.close(archive_descriptor)
        archive_descriptor = -1
        inspect_archive(private_archive_descriptor)
        lock_descriptor = os.open(
            lock_path,
            os.O_WRONLY | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        lock_metadata = os.fstat(lock_descriptor)
        if (
            not stat.S_ISREG(lock_metadata.st_mode)
            or lock_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(lock_metadata.st_mode) != 0o600
            or lock_metadata.st_nlink != 1
        ):
            fail("deployment export lock metadata is unsafe")
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ExportInstallError(
                "another deployment export install is active"
            ) from error
        stage = parent / (
            f".{destination.name}.partial-{expected_package_sha256[:16]}"
        )
        if stage.exists() or stage.is_symlink():
            fail("refusing an existing deployment export stage")
        os.mkdir(stage, 0o700)
        os.chmod(stage, 0o700)
        extract_archive(private_archive_descriptor, stage)
        root = stage / "root"
        if not root.is_dir() or root.is_symlink():
            fail("deployment archive lacks its fixed root directory")
        write_manifest(stage / "manifest", package_payload)
        verified = HEADLESS.verify_root(root, stage / "manifest")
        if dict(verified) != dict(values):
            fail("deployment root verification changed package meaning")
        if destination.exists() or destination.is_symlink():
            fail("refusing an existing deployment export")
        fsync_tree(stage)
        rename_noreplace(stage, destination)
        fsync_directory(parent)
        return values
    finally:
        os.close(package_descriptor)
        if archive_descriptor >= 0:
            os.close(archive_descriptor)
        if private_archive_descriptor >= 0:
            os.close(private_archive_descriptor)
        if lock_descriptor >= 0:
            os.close(lock_descriptor)


def parse_arguments(arguments: list[str]) -> tuple[Path, Path, str]:
    if len(arguments) != 3:
        fail(
            "usage: install-headless-ssh-deployment-export.py "
            "ARCHIVE PACKAGE PACKAGE_SHA256"
        )
    return Path(arguments[0]), Path(arguments[1]), arguments[2]


def main(arguments: list[str] | None = None) -> int:
    try:
        archive, package, package_sha256 = parse_arguments(
            sys.argv[1:] if arguments is None else arguments
        )
        if os.geteuid() != 0:
            fail("run the fixed installer through PolicyKit")
        caller = os.environ.get("PKEXEC_UID", "")
        if not caller.isascii() or not caller.isdecimal() or caller == "0":
            fail("missing non-root PolicyKit caller identity")
        caller_uid = int(caller)
        caller_record = pwd.getpwuid(caller_uid)
        fixed_installed_metadata()
        values = install_export(
            archive,
            package,
            package_sha256,
            owner=caller_uid,
            group=caller_record.pw_gid,
        )
    except (
        ExportInstallError,
        HEADLESS.HeadlessRootError,
        HEADLESS.ROOT_TOOL.ContractError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
    ):
        print(
            "FAIL headless SSH deployment export installation refused",
            file=sys.stderr,
        )
        return 1
    print(
        "PASS installed admitted headless SSH deployment export "
        f"entries={values['root_tree_entries']} "
        f"tree_sha256={values['root_tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
