#!/usr/bin/env python3
"""Prepare and verify a sealed, no-workload headless network root."""

from __future__ import annotations

import argparse
import base64
import binascii
from collections import OrderedDict
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys
from typing import NoReturn


SOURCE_PATH = Path(__file__).resolve()
INSTALLED_ROOT = Path("/usr/libexec/rog5-recovery-host")
if SOURCE_PATH.parent == INSTALLED_ROOT:
    ROOT_TOOL_PATH = INSTALLED_ROOT / "persistent-root-tool.py"
    for installed_path in (SOURCE_PATH, ROOT_TOOL_PATH):
        installed_metadata = installed_path.lstat()
        if (
            not stat.S_ISREG(installed_metadata.st_mode)
            or installed_metadata.st_uid != 0
            or installed_metadata.st_gid != 0
            or stat.S_IMODE(installed_metadata.st_mode) != 0o555
        ):
            raise SystemExit(
                "FAIL installed headless verifier metadata is unsafe"
            )
else:
    REPO = SOURCE_PATH.parents[2]
    ROOT_TOOL_PATH = REPO / "scripts/device/persistent-root-tool.py"
DEPLOYMENT_EXPORT_STORAGE_ROOT = Path("/home/rog5-linux")
DEPLOYMENT_EXPORT = (
    DEPLOYMENT_EXPORT_STORAGE_ROOT
    / "exports"
    / "headless-ssh-network-root-v3"
)
SEAL_NAME = ".rog5-persistent-seal"
COMMAND_PATH = Path("etc/rog5/a660-command-manifest")
AUTHORIZED_KEYS_PATH = Path("root/.ssh/authorized_keys")
EPOCH = 1681862400
ZERO_HASH = "0" * 64
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SSH_SHA256 = re.compile(r"SHA256:[A-Za-z0-9+/]{43}\Z")
IDENTITY_KEYS_V1 = (
    "format",
    "profile",
    "root_generation",
    "root_subtree",
    "source_archive_size",
    "source_archive_sha256",
    "a660_command_manifest_sha256",
    "root_tree_entries",
    "root_tree_sha256",
    "root_seal_sha256",
)
IDENTITY_KEYS_V2 = (
    "format",
    "profile",
    "build_profile",
    *IDENTITY_KEYS_V1[2:],
)
IDENTITY_KEYS_V3 = (
    "format",
    "profile",
    "build_profile",
    "authorized_key_fingerprint",
    *IDENTITY_KEYS_V1[2:],
)
PACKAGE_KEYS_V1 = (
    "format",
    "profile",
    "root_generation",
    "root_subtree",
    "source_archive_size",
    "source_archive_sha256",
    "sealed_archive_size",
    "sealed_archive_sha256",
    "a660_command_manifest_sha256",
    "root_tree_entries",
    "root_tree_sha256",
    "root_seal_sha256",
)
PACKAGE_KEYS_V2 = (
    "format",
    "profile",
    "build_profile",
    *PACKAGE_KEYS_V1[2:],
)
PACKAGE_KEYS_V3 = (
    "format",
    "profile",
    "build_profile",
    "authorized_key_fingerprint",
    *PACKAGE_KEYS_V1[2:],
)
IDENTITY_FORMATS = {
    "rog5-headless-network-root-identity-v1": IDENTITY_KEYS_V1,
    "rog5-headless-network-root-identity-v2": IDENTITY_KEYS_V2,
    "rog5-headless-network-root-identity-v3": IDENTITY_KEYS_V3,
}
PACKAGE_FORMATS = {
    "rog5-headless-network-root-package-v1": PACKAGE_KEYS_V1,
    "rog5-headless-network-root-package-v2": PACKAGE_KEYS_V2,
    "rog5-headless-network-root-package-v3": PACKAGE_KEYS_V3,
}
BUILD_FIELDS = {
    "headless-ssh-v1": (
        "profile",
        "project_commit",
        "rootfs_sha256",
        "modules_sha256",
        "kernel_release",
    ),
    "headless-core-v2": (
        "profile",
        "project_commit",
        "rootfs_sha256",
        "modules_sha256",
        "kernel_release",
        "indicator_sha256",
        "indicator_policy",
    ),
    "headless-ssh-v2": (
        "profile",
        "project_commit",
        "rootfs_sha256",
        "modules_sha256",
        "kernel_release",
        "authorized_key_fingerprint",
    ),
}
COMMAND_FIELDS = OrderedDict(
    (
        ("format", "rog5-headless-command-manifest-v1"),
        ("workload", "none"),
    )
)


class HeadlessRootError(RuntimeError):
    """A stable, non-sensitive headless-root refusal."""


def fail(message: str) -> NoReturn:
    raise HeadlessRootError(message)


def load_root_tool():
    specification = importlib.util.spec_from_file_location(
        "rog5_headless_persistent_root_tool",
        ROOT_TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        fail("cannot load the persistent-root tool")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


ROOT_TOOL = load_root_tool()


def canonical_bytes(values: OrderedDict[str, str]) -> bytes:
    return "".join(
        f"{name}={value}\n" for name, value in values.items()
    ).encode("ascii")


def parse_decimal(value: str, label: str) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdecimal()
        or value.startswith("0")
    ):
        fail(f"{label} is not a positive canonical decimal")
    return int(value)


def validate_hash(value: str, label: str) -> None:
    if not SHA256.fullmatch(value) or value == ZERO_HASH:
        fail(f"{label} is not a nonzero SHA-256")


def file_identity(metadata: os.stat_result) -> tuple[int, ...]:
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


def trusted_deployment_export_parent(
    destination: Path,
    *,
    storage_root: Path = DEPLOYMENT_EXPORT_STORAGE_ROOT,
    owner: int = 0,
    group: int = 0,
    require_destination: bool = False,
) -> Path:
    parent = storage_root / "exports"
    expected = parent / "headless-ssh-network-root-v3"
    if (
        not storage_root.is_absolute()
        or storage_root == Path("/")
        or destination != expected
    ):
        fail("deployment destination is not the fixed export store")
    paths: list[tuple[Path, int | None]] = [
        (storage_root.parent, None),
        (storage_root, 0o700),
        (parent, 0o700),
    ]
    if require_destination:
        paths.append((destination, 0o700))
    for path, required_mode in paths:
        try:
            named = path.lstat()
            resolved = path.resolve(strict=True)
            resolved_metadata = resolved.lstat()
        except OSError as error:
            raise HeadlessRootError(
                "deployment destination ancestor is unavailable"
            ) from error
        mode = stat.S_IMODE(named.st_mode)
        if (
            path != resolved
            or file_identity(named) != file_identity(resolved_metadata)
            or not stat.S_ISDIR(named.st_mode)
            or named.st_uid != owner
            or named.st_gid != group
            or mode & 0o022
            or (required_mode is not None and mode != required_mode)
        ):
            fail("deployment destination ancestor is unsafe")
    return parent


def safe_root(path: Path) -> tuple[Path, int]:
    if not path.is_absolute():
        fail("root path must be absolute")
    try:
        before = path.lstat()
        root = path.resolve(strict=True)
        after = root.lstat()
    except OSError as error:
        raise HeadlessRootError("root path is unavailable") from error
    if (
        root == Path("/")
        or path != root
        or file_identity(before) != file_identity(after)
        or not stat.S_ISDIR(after.st_mode)
        or stat.S_IMODE(after.st_mode) & 0o022
    ):
        fail("root path metadata is unsafe")
    return root, after.st_uid


def read_regular(
    path: Path,
    *,
    owner: int,
    group: int | None = None,
    mode: int | None = None,
    maximum: int = 64 * 1024,
) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise HeadlessRootError("cannot open fixed regular file") from error
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != owner
            or (group is not None and before.st_gid != group)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > maximum
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
            or (mode is None and stat.S_IMODE(before.st_mode) & 0o022)
        ):
            fail("fixed regular-file metadata is unsafe")
        payload = bytearray()
        while len(payload) <= maximum:
            block = os.read(
                descriptor,
                min(65536, maximum + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        try:
            named = path.lstat()
        except OSError as error:
            raise HeadlessRootError(
                "fixed regular file disappeared"
            ) from error
        if (
            len(payload) != before.st_size
            or file_identity(before) != file_identity(after)
            or file_identity(before) != file_identity(named)
        ):
            fail("fixed regular file changed while being read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def validate_directory(
    path: Path,
    *,
    owner: int,
    group: int,
    mode: int | None,
) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise HeadlessRootError("fixed directory is unavailable") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != owner
        or metadata.st_gid != group
        or (
            mode is not None
            and stat.S_IMODE(metadata.st_mode) != mode
        )
        or (
            mode is None
            and stat.S_IMODE(metadata.st_mode) & 0o022
        )
    ):
        fail("fixed directory metadata is unsafe")


def parse_ssh_string(
    blob: bytes,
    offset: int,
    label: str,
) -> tuple[bytes, int]:
    if len(blob) - offset < 4:
        fail(f"{label} is truncated")
    length = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4
    end = offset + length
    if end > len(blob):
        fail(f"{label} is truncated")
    return blob[offset:end], end


def authorized_key_fingerprint(payload: bytes) -> str:
    if (
        not payload.endswith(b"\n")
        or payload.count(b"\n") != 1
        or b"\r" in payload
    ):
        fail("authorized key is not one canonical line")
    line = payload[:-1]
    fields = line.split(b" ")
    if len(fields) != 2 or any(not field for field in fields):
        fail("authorized key is not a canonical two-field record")
    key_type, encoded = fields
    if key_type != b"ssh-ed25519":
        fail("authorized key algorithm is unsupported")
    try:
        blob = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HeadlessRootError(
            "authorized key Base64 is invalid"
        ) from error
    if base64.b64encode(blob) != encoded:
        fail("authorized key Base64 is not canonical")
    algorithm, offset = parse_ssh_string(blob, 0, "authorized key algorithm")
    public_key, offset = parse_ssh_string(
        blob,
        offset,
        "authorized key payload",
    )
    if (
        algorithm != key_type
        or len(public_key) != 32
        or offset != len(blob)
    ):
        fail("authorized key blob changed")
    fingerprint = (
        "SHA256:"
        + base64.b64encode(hashlib.sha256(blob).digest())
        .decode("ascii")
        .rstrip("=")
    )
    if not SSH_SHA256.fullmatch(fingerprint):
        fail("authorized key fingerprint is not canonical")
    return fingerprint


def validate_authorized_key(root: Path, owner: int) -> str:
    root_metadata = root.lstat()
    validate_directory(
        root / AUTHORIZED_KEYS_PATH.parents[1],
        owner=owner,
        group=root_metadata.st_gid,
        mode=None,
    )
    ssh_directory = root / AUTHORIZED_KEYS_PATH.parent
    validate_directory(
        ssh_directory,
        owner=owner,
        group=root_metadata.st_gid,
        mode=0o700,
    )
    payload = read_regular(
        root / AUTHORIZED_KEYS_PATH,
        owner=owner,
        group=root_metadata.st_gid,
        mode=0o600,
        maximum=16 * 1024,
    )
    return authorized_key_fingerprint(payload)


def parse_canonical_payload(
    payload: bytes,
    keys: tuple[str, ...],
) -> OrderedDict[str, str]:
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise HeadlessRootError("canonical record is not ASCII") from error
    lines = text.splitlines()
    if len(lines) != len(keys) or not payload.endswith(b"\n"):
        fail("canonical record field count changed")
    values: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(keys, lines, strict=True):
        name, separator, value = line.partition("=")
        if (
            separator != "="
            or name != expected
            or not value
            or name in values
        ):
            fail("canonical record field changed")
        values[name] = value
    if canonical_bytes(values) != payload:
        fail("canonical record encoding changed")
    return values


def parse_canonical(
    path: Path,
    keys: tuple[str, ...],
    *,
    owner: int,
    mode: int,
) -> OrderedDict[str, str]:
    return parse_canonical_payload(
        read_regular(path, owner=owner, mode=mode),
        keys,
    )


def parse_canonical_variant(
    path: Path,
    formats: dict[str, tuple[str, ...]],
    *,
    owner: int,
    mode: int,
) -> OrderedDict[str, str]:
    payload = read_regular(path, owner=owner, mode=mode)
    first = payload.split(b"\n", 1)[0]
    prefix = b"format="
    if not first.startswith(prefix):
        fail("canonical record format is missing")
    try:
        format_name = first[len(prefix) :].decode("ascii")
    except UnicodeDecodeError as error:
        raise HeadlessRootError(
            "canonical record format is not ASCII"
        ) from error
    keys = formats.get(format_name)
    if keys is None:
        fail("canonical record format is unsupported")
    return parse_canonical_payload(payload, keys)


def parse_command(payload: bytes) -> OrderedDict[str, str]:
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise HeadlessRootError(
            "headless command manifest is not ASCII"
        ) from error
    lines = text.splitlines()
    values: OrderedDict[str, str] = OrderedDict()
    if len(lines) != len(COMMAND_FIELDS) or not payload.endswith(b"\n"):
        fail("headless command manifest is not canonical")
    for (expected, expected_value), line in zip(
        COMMAND_FIELDS.items(),
        lines,
        strict=True,
    ):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or value != expected_value:
            fail("headless command manifest changed")
        values[name] = value
    if canonical_bytes(values) != payload:
        fail("headless command manifest encoding changed")
    return values


def validate_build(
    root: Path,
    owner: int,
    expected_profile: str,
) -> dict[str, str]:
    payload = read_regular(
        root / "etc/rog5/build",
        owner=owner,
        maximum=4096,
    )
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise HeadlessRootError(
            "headless build record is not ASCII"
        ) from error
    fields: dict[str, str] = {}
    expected = BUILD_FIELDS.get(expected_profile)
    if expected is None:
        fail("headless build profile is unsupported")
    if len(lines) != len(expected) or not payload.endswith(b"\n"):
        fail("headless build record field count changed")
    for name, line in zip(expected, lines, strict=True):
        observed, separator, value = line.partition("=")
        if separator != "=" or observed != name or not value:
            fail("headless build record changed")
        fields[name] = value
    canonical = "".join(
        f"{name}={fields[name]}\n" for name in expected
    ).encode("ascii")
    if payload != canonical:
        fail("headless build record encoding changed")
    if (
        fields["profile"] != expected_profile
        or fields["kernel_release"] != "7.1.4-g7a5cef0db479"
        or not re.fullmatch(r"[0-9a-f]{40}", fields["project_commit"])
    ):
        fail("headless build identity changed")
    validate_hash(fields["rootfs_sha256"], "base rootfs hash")
    validate_hash(fields["modules_sha256"], "module archive hash")
    if expected_profile == "headless-core-v2":
        validate_hash(fields["indicator_sha256"], "indicator hash")
        if fields["indicator_policy"] != "power-key-green-status-pulse-v1":
            fail("headless indicator policy changed")
    elif expected_profile == "headless-ssh-v2":
        fingerprint = fields["authorized_key_fingerprint"]
        if (
            not SSH_SHA256.fullmatch(fingerprint)
            or validate_authorized_key(root, owner) != fingerprint
        ):
            fail("authorized key identity changed")
    return fields


def remove_posix_acls(root: Path) -> None:
    acl_names = (
        "system.posix_acl_access",
        "system.posix_acl_default",
    )
    for _, path, _ in ROOT_TOOL.walk_tree(os.fsencode(root)):
        for name in acl_names:
            try:
                os.removexattr(path, name, follow_symlinks=False)
            except OSError as error:
                if error.errno not in (errno.ENODATA, errno.ENOTSUP):
                    raise


def normalize_mtimes(root: Path) -> None:
    for _, path, metadata in ROOT_TOOL.walk_tree(os.fsencode(root)):
        mtime_ns = metadata.st_mtime_ns // 1_000_000_000 * 1_000_000_000
        os.utime(
            path,
            ns=(metadata.st_atime_ns, mtime_ns),
            follow_symlinks=False,
        )


def create_exclusive(path: Path, payload: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, mode)
    except OSError as error:
        raise HeadlessRootError("cannot create fixed output") from error
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("fixed output write made no progress")
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_identity(values: OrderedDict[str, str]) -> None:
    format_name = values.get("format")
    if format_name == "rog5-headless-network-root-identity-v1":
        expected_keys = IDENTITY_KEYS_V1
        expected_build_profile = "headless-ssh-v1"
    elif format_name == "rog5-headless-network-root-identity-v2":
        expected_keys = IDENTITY_KEYS_V2
        expected_build_profile = "headless-core-v2"
    elif format_name == "rog5-headless-network-root-identity-v3":
        expected_keys = IDENTITY_KEYS_V3
        expected_build_profile = "headless-ssh-v2"
    else:
        fail("headless network-root identity format changed")
    if (
        tuple(values) != expected_keys
        or values["profile"] != "network-root-v1"
        or values["root_generation"] != "arch-a"
        or values["root_subtree"] != "/"
        or (
            format_name
            in (
                "rog5-headless-network-root-identity-v2",
                "rog5-headless-network-root-identity-v3",
            )
            and values["build_profile"] != expected_build_profile
        )
    ):
        fail("headless network-root identity changed")
    parse_decimal(values["source_archive_size"], "source archive size")
    parse_decimal(values["root_tree_entries"], "root tree entries")
    for name in (
        "source_archive_sha256",
        "a660_command_manifest_sha256",
        "root_tree_sha256",
        "root_seal_sha256",
    ):
        validate_hash(values[name], name)
    if format_name == "rog5-headless-network-root-identity-v3":
        if not SSH_SHA256.fullmatch(values["authorized_key_fingerprint"]):
            fail("authorized key fingerprint changed")


def prepare(
    root_path: Path,
    source_size: str,
    source_sha256: str,
    command_path: Path,
    identity_path: Path,
    build_profile: str = "headless-ssh-v1",
) -> OrderedDict[str, str]:
    root, owner = safe_root(root_path)
    if build_profile not in BUILD_FIELDS:
        fail("headless build profile is unsupported")
    build = validate_build(root, owner, build_profile)
    parse_decimal(source_size, "source archive size")
    validate_hash(source_sha256, "source archive hash")
    command_payload = read_regular(
        command_path,
        owner=owner,
        maximum=4096,
    )
    parse_command(command_payload)
    remove_posix_acls(root)
    installed_command = root / COMMAND_PATH
    seal = root / SEAL_NAME
    if installed_command.exists() or installed_command.is_symlink():
        fail("headless command-manifest target already exists")
    if seal.exists() or seal.is_symlink():
        fail("persistent-seal target already exists")
    command_parent = installed_command.parent
    command_parent_metadata = command_parent.lstat()
    create_exclusive(installed_command, command_payload, 0o400)
    create_exclusive(seal, b"", 0o600)
    fixed_time = EPOCH * 1_000_000_000
    os.utime(
        installed_command,
        ns=(fixed_time, fixed_time),
        follow_symlinks=False,
    )
    os.utime(
        command_parent,
        ns=(
            command_parent_metadata.st_atime_ns,
            command_parent_metadata.st_mtime_ns,
        ),
        follow_symlinks=False,
    )
    os.utime(
        root,
        ns=(fixed_time, fixed_time),
        follow_symlinks=False,
    )
    normalize_mtimes(root)
    tree = OrderedDict(ROOT_TOOL.seal_tree(root))
    seal_values: OrderedDict[str, str] = OrderedDict(
        (
            ("seal_format", "rog5-persistent-root-v1"),
            ("generation", "arch-a"),
            ("source_archive_size", source_size),
            ("source_archive_sha256", source_sha256),
            ("promotion_state", "UNBOOTED"),
            *((name, tree[name]) for name in ROOT_TOOL.TREE_KEYS),
        )
    )
    descriptor = os.open(
        seal,
        os.O_WRONLY | os.O_TRUNC | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        payload = canonical_bytes(seal_values)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("persistent-seal write made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.utime(seal, ns=(fixed_time, fixed_time), follow_symlinks=False)
    ROOT_TOOL.verify_tree(root, seal)
    values: OrderedDict[str, str] = OrderedDict()
    formats = {
        "headless-ssh-v1": "rog5-headless-network-root-identity-v1",
        "headless-core-v2": "rog5-headless-network-root-identity-v2",
        "headless-ssh-v2": "rog5-headless-network-root-identity-v3",
    }
    values["format"] = formats[build_profile]
    values["profile"] = "network-root-v1"
    if build_profile in ("headless-core-v2", "headless-ssh-v2"):
        values["build_profile"] = build_profile
    if build_profile == "headless-ssh-v2":
        values["authorized_key_fingerprint"] = build[
            "authorized_key_fingerprint"
        ]
    values.update(
        (
            ("root_generation", "arch-a"),
            ("root_subtree", "/"),
            ("source_archive_size", source_size),
            ("source_archive_sha256", source_sha256),
            (
                "a660_command_manifest_sha256",
                hashlib.sha256(command_payload).hexdigest(),
            ),
            ("root_tree_entries", tree["tree_entries"]),
            ("root_tree_sha256", tree["tree_sha256"]),
            (
                "root_seal_sha256",
                hashlib.sha256(payload).hexdigest(),
            ),
        )
    )
    validate_identity(values)
    create_exclusive(identity_path, canonical_bytes(values), 0o444)
    return values


def regular_identity(path: Path) -> tuple[int, int, str]:
    if not path.is_absolute():
        fail("archive path must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise HeadlessRootError("cannot open sealed archive") from error
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) & 0o022
            or metadata.st_size < 1
        ):
            fail("sealed archive metadata is unsafe")
        digest = hashlib.sha256()
        observed = 0
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
            observed += len(block)
        after = os.fstat(descriptor)
        if (
            observed != metadata.st_size
            or file_identity(metadata) != file_identity(after)
        ):
            fail("sealed archive changed while being read")
        return metadata.st_uid, observed, digest.hexdigest()
    finally:
        os.close(descriptor)


def package(
    identity_path: Path,
    sealed_archive: Path,
    package_path: Path,
) -> OrderedDict[str, str]:
    owner, sealed_size, sealed_sha256 = regular_identity(sealed_archive)
    identity = parse_canonical_variant(
        identity_path,
        IDENTITY_FORMATS,
        owner=owner,
        mode=0o444,
    )
    validate_identity(identity)
    version = identity["format"].rsplit("-", 1)[1]
    identity_keys = IDENTITY_FORMATS[identity["format"]]
    split_at = identity_keys.index("a660_command_manifest_sha256")
    values: OrderedDict[str, str] = OrderedDict()
    values["format"] = f"rog5-headless-network-root-package-{version}"
    for name in identity_keys[1:split_at]:
        values[name] = identity[name]
    values["sealed_archive_size"] = str(sealed_size)
    values["sealed_archive_sha256"] = sealed_sha256
    for name in identity_keys[split_at:]:
        values[name] = identity[name]
    validate_package(values)
    create_exclusive(package_path, canonical_bytes(values), 0o444)
    return values


def validate_package(values: OrderedDict[str, str]) -> None:
    format_name = values.get("format")
    if format_name == "rog5-headless-network-root-package-v1":
        expected_keys = PACKAGE_KEYS_V1
        expected_build_profile = "headless-ssh-v1"
    elif format_name == "rog5-headless-network-root-package-v2":
        expected_keys = PACKAGE_KEYS_V2
        expected_build_profile = "headless-core-v2"
    elif format_name == "rog5-headless-network-root-package-v3":
        expected_keys = PACKAGE_KEYS_V3
        expected_build_profile = "headless-ssh-v2"
    else:
        fail("headless network-root package format changed")
    if (
        tuple(values) != expected_keys
        or values["profile"] != "network-root-v1"
        or values["root_generation"] != "arch-a"
        or values["root_subtree"] != "/"
        or (
            format_name
            in (
                "rog5-headless-network-root-package-v2",
                "rog5-headless-network-root-package-v3",
            )
            and values["build_profile"] != expected_build_profile
        )
    ):
        fail("headless network-root package identity changed")
    for name in (
        "source_archive_size",
        "sealed_archive_size",
        "root_tree_entries",
    ):
        parse_decimal(values[name], name)
    for name in (
        "source_archive_sha256",
        "sealed_archive_sha256",
        "a660_command_manifest_sha256",
        "root_tree_sha256",
        "root_seal_sha256",
    ):
        validate_hash(values[name], name)
    if format_name == "rog5-headless-network-root-package-v3":
        if not SSH_SHA256.fullmatch(values["authorized_key_fingerprint"]):
            fail("authorized key fingerprint changed")


def verify(
    root_path: Path,
    sealed_archive: Path,
    package_path: Path,
    command_path: Path,
) -> OrderedDict[str, str]:
    root, owner = safe_root(root_path)
    archive_owner, sealed_size, sealed_sha256 = regular_identity(
        sealed_archive
    )
    if archive_owner != owner:
        fail("root and sealed archive owners differ")
    values = verify_root(root_path, package_path, command_path)
    if (
        values["sealed_archive_size"] != str(sealed_size)
        or values["sealed_archive_sha256"] != sealed_sha256
    ):
        fail("sealed archive identity changed")
    return values


def verify_root(
    root_path: Path,
    package_path: Path,
    command_path: Path | None = None,
) -> OrderedDict[str, str]:
    root, owner = safe_root(root_path)
    values = parse_canonical_variant(
        package_path,
        PACKAGE_FORMATS,
        owner=owner,
        mode=0o444,
    )
    validate_package(values)
    build_profile = values.get("build_profile", "headless-ssh-v1")
    build = validate_build(root, owner, build_profile)
    if (
        build_profile == "headless-ssh-v2"
        and values["authorized_key_fingerprint"]
        != build["authorized_key_fingerprint"]
    ):
        fail("authorized key package binding changed")
    installed_command = read_regular(
        root / COMMAND_PATH,
        owner=owner,
        mode=0o400,
        maximum=4096,
    )
    parse_command(installed_command)
    if command_path is not None:
        expected_command = read_regular(
            command_path,
            owner=owner,
            maximum=4096,
        )
        parse_command(expected_command)
        if installed_command != expected_command:
            fail("installed no-workload command manifest changed")
    if (
        hashlib.sha256(installed_command).hexdigest()
        != values["a660_command_manifest_sha256"]
    ):
        fail("installed no-workload command manifest changed")
    seal = root / SEAL_NAME
    seal_payload = read_regular(seal, owner=owner, mode=0o444)
    if hashlib.sha256(seal_payload).hexdigest() != values["root_seal_sha256"]:
        fail("persistent-seal identity changed")
    seal_values = ROOT_TOOL.read_seal(seal)
    if (
        seal_values["source_archive_size"]
        != values["source_archive_size"]
        or seal_values["source_archive_sha256"]
        != values["source_archive_sha256"]
        or seal_values["tree_entries"] != values["root_tree_entries"]
        or seal_values["tree_sha256"] != values["root_tree_sha256"]
    ):
        fail("persistent-seal binding changed")
    ROOT_TOOL.verify_tree(root, seal)
    return values


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("root", type=Path)
    prepare_parser.add_argument("source_size")
    prepare_parser.add_argument("source_sha256")
    prepare_parser.add_argument("command_manifest", type=Path)
    prepare_parser.add_argument("identity", type=Path)
    prepare_parser.add_argument(
        "--build-profile",
        choices=tuple(BUILD_FIELDS),
        default="headless-ssh-v1",
    )
    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("identity", type=Path)
    package_parser.add_argument("sealed_archive", type=Path)
    package_parser.add_argument("package_manifest", type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("root", type=Path)
    verify_parser.add_argument("sealed_archive", type=Path)
    verify_parser.add_argument("package_manifest", type=Path)
    verify_parser.add_argument("command_manifest", type=Path)
    verify_root_parser = subparsers.add_parser("verify-root")
    verify_root_parser.add_argument("root", type=Path)
    verify_root_parser.add_argument("package_manifest", type=Path)
    verify_export_parser = subparsers.add_parser(
        "verify-export-ancestry"
    )
    verify_export_parser.add_argument("export", type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    values = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        if values.command == "prepare":
            identity = prepare(
                values.root,
                values.source_size,
                values.source_sha256,
                values.command_manifest,
                values.identity,
                values.build_profile,
            )
            print("PASS prepared sealed headless network root")
            print(f"root_tree_entries={identity['root_tree_entries']}")
            print(f"root_tree_sha256={identity['root_tree_sha256']}")
            print(f"root_seal_sha256={identity['root_seal_sha256']}")
        elif values.command == "package":
            package_values = package(
                values.identity,
                values.sealed_archive,
                values.package_manifest,
            )
            print("PASS packaged sealed headless network root")
            print(
                "sealed_archive_sha256="
                f"{package_values['sealed_archive_sha256']}"
            )
        elif values.command == "verify":
            package_values = verify(
                values.root,
                values.sealed_archive,
                values.package_manifest,
                values.command_manifest,
            )
            print(
                "PASS verified sealed headless network root "
                f"entries={package_values['root_tree_entries']} "
                f"tree_sha256={package_values['root_tree_sha256']}"
            )
        elif values.command == "verify-root":
            package_values = verify_root(
                values.root,
                values.package_manifest,
            )
            print(
                "PASS verified installed headless network root "
                f"entries={package_values['root_tree_entries']} "
                f"tree_sha256={package_values['root_tree_sha256']}"
            )
        else:
            trusted_deployment_export_parent(
                values.export,
                require_destination=True,
            )
            print("PASS verified deployment export ancestry")
    except (HeadlessRootError, ROOT_TOOL.ContractError):
        print("FAIL headless network-root operation refused", file=sys.stderr)
        return 1
    except OSError:
        print(
            "FAIL headless network-root filesystem operation failed",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
