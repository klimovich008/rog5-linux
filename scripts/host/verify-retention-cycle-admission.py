#!/usr/bin/env python3
"""Verify an authority-free target/observer retention-cycle review."""

from __future__ import annotations

import ast
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from typing import Any, Iterator, NamedTuple


REPO = Path(__file__).resolve().parents[2]
PROFILE = (
    REPO
    / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
)
ARTIFACTS = REPO / "manifests/artifacts.tsv"
EXPECTED_SEQUENCE = (
    "diagnostic-target",
    "exact-alpine-fallback",
    "bootloader",
    "observation-recovery",
    "postmortem-status",
)
SHA256_ZERO = "0" * 64
MAX_INITRAMFS_BYTES = 32 * 1024 * 1024
BOOT_V3_PAGE_SIZE = 4096
BOOT_V3_HEADER_SIZE = 1580
EXPECTED_RECOVERY_CMDLINE = (
    "init=/init selinux=0 printk.devkmsg=on rog5linux.test=1 "
    "ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 "
    "ramoops.record_size=0x100000 ramoops.console_size=0x300000 "
    "ramoops.pmsg_size=0 ramoops.ftrace_size=0 ramoops.dump_oops=1 "
    "rog5.recovery_timeout=180"
)


class AdmissionError(RuntimeError):
    """The offline pair is not an exact, authority-free review."""


class NewcEntry(NamedTuple):
    mode: int
    uid: int
    gid: int
    nlink: int
    payload: bytes


def fail(message: str) -> None:
    raise AdmissionError(message)


def require_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"{label} fields are not exact")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label} is not a nonempty string")
    return value


def require_sha256(value: Any, label: str) -> str:
    digest = require_string(value, label)
    if (
        len(digest) != 64
        or digest == SHA256_ZERO
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        fail(f"{label} is not one nonzero lowercase SHA-256")
    return digest


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def read_json(
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    expected_digest: str | None = None,
) -> dict[str, Any]:
    payload = read_verified_bytes(
        path,
        label,
        expected_size=expected_size,
        expected_digest=expected_digest,
    )
    try:
        value = json.loads(
            payload,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AdmissionError(f"{label} is not canonical JSON") from error
    if not isinstance(value, dict):
        fail(f"{label} is not a JSON object")
    return value


def hash_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while block := os.read(descriptor, 1024 * 1024):
        digest.update(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return digest.hexdigest()


def stable_metadata(metadata: os.stat_result) -> tuple[int, ...]:
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


def exact_regular(metadata: os.stat_result) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and metadata.st_nlink == 1
        and not stat.S_IMODE(metadata.st_mode) & 0o022
    )


@contextmanager
def verified_descriptor(
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    expected_digest: str | None = None,
) -> Iterator[int]:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise AdmissionError(f"unsafe or missing {label}") from error
    try:
        opened = os.fstat(descriptor)
        named = os.stat(path, follow_symlinks=False)
        if (
            not exact_regular(opened)
            or stable_metadata(opened) != stable_metadata(named)
        ):
            fail(f"unsafe or missing {label}")
        if expected_size is not None and opened.st_size != expected_size:
            fail(f"{label} size changed")
        first_digest = hash_descriptor(descriptor)
        if expected_digest is not None and first_digest != expected_digest:
            fail(f"{label} identity changed")
        after_hash = os.fstat(descriptor)
        if stable_metadata(after_hash) != stable_metadata(opened):
            fail(f"{label} changed during verification")
        yield descriptor
        final_digest = hash_descriptor(descriptor)
        final = os.fstat(descriptor)
        current = os.stat(path, follow_symlinks=False)
        if (
            final_digest != first_digest
            or stable_metadata(final) != stable_metadata(opened)
            or stable_metadata(current) != stable_metadata(opened)
        ):
            fail(f"{label} changed during verification")
    except OSError as error:
        raise AdmissionError(f"{label} changed during verification") from error
    finally:
        os.close(descriptor)


def read_descriptor(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    blocks: list[bytes] = []
    while block := os.read(descriptor, 1024 * 1024):
        blocks.append(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return b"".join(blocks)


def read_verified_bytes(
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    expected_digest: str | None = None,
) -> bytes:
    with verified_descriptor(
        path,
        label,
        expected_size=expected_size,
        expected_digest=expected_digest,
    ) as descriptor:
        return read_descriptor(descriptor)


def safe_file_metadata(path: Path, label: str) -> os.stat_result:
    with verified_descriptor(path, label) as descriptor:
        return os.fstat(descriptor)


def read_safe_file(path: Path, label: str) -> bytes:
    return read_verified_bytes(path, label)


def safe_root(path: Path, label: str) -> Path:
    if not path.is_absolute():
        fail(f"{label} must be absolute")
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise AdmissionError(f"unsafe or missing {label}") from error
    if (
        resolved != path
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        fail(f"unsafe or missing {label}")
    return resolved


def relative_path(value: Any, label: str) -> PurePosixPath:
    raw = require_string(value, label)
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(
        part in ("", ".", "..") for part in path.parts
    ):
        fail(f"{label} is not a safe relative path")
    return path


def safe_child(root: Path, value: Any, label: str) -> Path:
    relative = relative_path(value, label)
    current = root
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise AdmissionError(f"unsafe or missing {label}") from error
        if not stat.S_ISDIR(metadata.st_mode):
            fail(f"unsafe or missing {label}")
    path = root.joinpath(*relative.parts)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise AdmissionError(f"unsafe or missing {label}") from error
    if resolved != path:
        fail(f"unsafe or missing {label}")
    return path


def require_absent_child(root: Path, value: Any, label: str) -> None:
    relative = relative_path(value, label)
    current = root
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return
        except OSError as error:
            raise AdmissionError(f"unsafe {label} ancestry") from error
        if not stat.S_ISDIR(metadata.st_mode):
            fail(f"unsafe {label} ancestry")
    path = root.joinpath(*relative.parts)
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as error:
        raise AdmissionError(f"unsafe {label}") from error
    fail(f"{label} must be absent")


def verify_file(path: Path, size: Any, digest: Any, label: str) -> None:
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        fail(f"{label} size is invalid")
    expected = require_sha256(digest, f"{label} SHA-256")
    with verified_descriptor(
        path,
        label,
        expected_size=size,
        expected_digest=expected,
    ):
        pass


def verify_pair(
    root: Path,
    value: Any,
    label: str,
) -> tuple[Path, Path, str]:
    record = require_keys(
        value,
        {"path_a", "path_b", "size", "sha256"},
        label,
    )
    first = safe_child(root, record["path_a"], f"{label} A")
    second = safe_child(root, record["path_b"], f"{label} B")
    if first == second:
        fail(f"{label} twins use one pathname")
    verify_file(first, record["size"], record["sha256"], f"{label} A")
    verify_file(second, record["size"], record["sha256"], f"{label} B")
    return first, second, require_sha256(record["sha256"], f"{label} SHA-256")


def verify_single(root: Path, value: Any, label: str) -> tuple[Path, str]:
    record = require_keys(value, {"path", "size", "sha256"}, label)
    path = safe_child(root, record["path"], label)
    verify_file(path, record["size"], record["sha256"], label)
    return path, require_sha256(record["sha256"], f"{label} SHA-256")


def expected_identity(value: Any, label: str, *, pair: bool) -> tuple[int, str]:
    keys = {"path_a", "path_b", "size", "sha256"} if pair else {
        "path",
        "size",
        "sha256",
    }
    record = require_keys(value, keys, label)
    size = record["size"]
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        fail(f"{label} size is invalid")
    return size, require_sha256(record["sha256"], f"{label} SHA-256")


def parse_key_values(payload: bytes, label: str) -> dict[str, str]:
    try:
        text = payload.decode("ascii")
    except UnicodeError as error:
        raise AdmissionError(f"{label} is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        fail(f"{label} is not canonical text")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            fail(f"{label} is not canonical key-value text")
        key, value = line.split("=", 1)
        if not key or not value or key in values:
            fail(f"{label} has an invalid or duplicate field")
        values[key] = value
    return values


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(archive: bytes) -> dict[str, NewcEntry]:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
            payload = stream.read(MAX_INITRAMFS_BYTES + 1)
    except (OSError, EOFError) as error:
        raise AdmissionError("recovery initramfs is not valid gzip") from error
    if len(payload) > MAX_INITRAMFS_BYTES:
        fail("recovery initramfs exceeds the decompression bound")
    entries: dict[str, NewcEntry] = {}
    offset = 0
    trailer = False
    while offset < len(payload):
        if payload[offset : offset + 6] not in (b"070701", b"070702"):
            if not any(memoryview(payload)[offset:]):
                break
            fail("recovery initramfs is not newc")
        if offset + 110 > len(payload):
            fail("recovery initramfs has a truncated newc header")
        header = payload[offset : offset + 110]
        try:
            fields = [
                int(header[6 + index * 8 : 14 + index * 8], 16)
                for index in range(13)
            ]
        except ValueError as error:
            raise AdmissionError("recovery initramfs has an invalid header") from error
        mode, uid, gid, nlink = fields[1:5]
        file_size = fields[6]
        name_size = fields[11]
        if name_size < 2:
            fail("recovery initramfs has an invalid entry name")
        name_start = offset + 110
        name_end = name_start + name_size
        if name_end > len(payload) or payload[name_end - 1] != 0:
            fail("recovery initramfs has a truncated entry name")
        try:
            name = payload[name_start : name_end - 1].decode("utf-8")
        except UnicodeError as error:
            raise AdmissionError("recovery initramfs has a non-UTF-8 path") from error
        data_start = align4(name_end)
        data_end = data_start + file_size
        if data_end > len(payload):
            fail("recovery initramfs has truncated entry data")
        offset = align4(data_end)
        if name == "TRAILER!!!":
            trailer = True
            break
        pure = PurePosixPath(name)
        if (
            not name
            or pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != name
            or name in entries
        ):
            fail("recovery initramfs has an unsafe or duplicate path")
        entries[name] = NewcEntry(
            mode,
            uid,
            gid,
            nlink,
            payload[data_start:data_end],
        )
    if not trailer:
        fail("recovery initramfs lacks its newc trailer")
    if any(memoryview(payload)[offset:]):
        fail("recovery initramfs contains a trailing archive member")
    return entries


def verify_recovery_role(
    path: Path,
    mode: str,
    expected_size: int,
    expected_digest: str,
) -> dict[str, NewcEntry]:
    entries = parse_newc(
        read_verified_bytes(
            path,
            "recovery initramfs",
            expected_size=expected_size,
            expected_digest=expected_digest,
        )
    )
    marker = entries.get("etc/rog5/recovery-mode")
    expected_marker = f"{mode}\n".encode("ascii")
    if (
        marker is None
        or not stat.S_ISREG(marker.mode)
        or stat.S_IMODE(marker.mode) != 0o444
        or marker.uid != 0
        or marker.gid != 0
        or marker.nlink != 1
        or marker.payload != expected_marker
    ):
        fail("recovery initramfs mode is not exact")
    control = entries.get("usr/libexec/rog5-recovery-control")
    if (
        control is None
        or not stat.S_ISREG(control.mode)
        or stat.S_IMODE(control.mode) != 0o755
        or control.uid != 0
        or control.gid != 0
        or control.nlink != 1
    ):
        fail("recovery initramfs lacks its control responder")
    mutating = {
        "usr/libexec/rog5-bundle-fetch",
        "usr/libexec/rog5-bundle-verify",
        "etc/rog5/recovery-bundle-ed25519.pub",
        "usr/sbin/kexec",
    }
    if mode == "full-v1":
        if not mutating.issubset(entries):
            fail("execution recovery lacks its exact payload path")
    elif mode == "observation-only-v1":
        if mutating.intersection(entries) or any(
            PurePosixPath(name).name == "kexec" for name in entries
        ):
            fail("observation recovery retains a payload execution path")
        if any(
            name == "run/rog5-bundles" or name.startswith("run/rog5-bundles/")
            for name in entries
        ):
            fail("observation recovery retains bundle state")
    else:
        fail("unknown recovery role")
    if any(
        stat.S_IFMT(entry.mode)
        not in {stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}
        or entry.uid != 0
        or entry.gid != 0
        or entry.nlink < 1
        or stat.S_IMODE(entry.mode) & 0o6000
        for entry in entries.values()
    ):
        fail("recovery initramfs contains an unsafe object")
    return entries


def verify_recovery_derivation(
    execution: dict[str, NewcEntry],
    observer: dict[str, NewcEntry],
) -> None:
    removed = {
        "usr/libexec/rog5-bundle-fetch",
        "usr/libexec/rog5-bundle-verify",
        "etc/rog5/recovery-bundle-ed25519.pub",
        "usr/sbin/kexec",
    }
    if set(observer) != set(execution) - removed:
        fail("observation recovery is not the exact execution-free derivation")
    marker = "etc/rog5/recovery-mode"
    for name, entry in observer.items():
        if name != marker and entry != execution[name]:
            fail("observation recovery changed a shared base entry")


def compare_prefix(raw_fd: int, avb_fd: int, size: int) -> None:
    offset = 0
    while offset < size:
        length = min(1024 * 1024, size - offset)
        if os.pread(raw_fd, length, offset) != os.pread(avb_fd, length, offset):
            fail("AVB payload differs from its raw boot image")
        offset += length


def zero_region(descriptor: int, start: int, end: int, label: str) -> None:
    if start > end:
        fail(f"{label} geometry is invalid")
    offset = start
    while offset < end:
        length = min(1024 * 1024, end - offset)
        block = os.pread(descriptor, length, offset)
        if len(block) != length or any(block):
            fail(f"{label} padding is not zero")
        offset += length


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def verify_boot_v3(
    raw: Path,
    kernel: Path,
    ramdisk: Path,
    raw_identity: tuple[int, str],
    kernel_identity: tuple[int, str],
    ramdisk_identity: tuple[int, str],
    expected_cmdline: str,
) -> None:
    raw_size, raw_digest = raw_identity
    kernel_size_expected, kernel_digest = kernel_identity
    ramdisk_size_expected, ramdisk_digest = ramdisk_identity
    with (
        verified_descriptor(
            raw,
            "raw boot image",
            expected_size=raw_size,
            expected_digest=raw_digest,
        ) as raw_fd,
        verified_descriptor(
            kernel,
            "wrapper Image",
            expected_size=kernel_size_expected,
            expected_digest=kernel_digest,
        ) as kernel_fd,
        verified_descriptor(
            ramdisk,
            "recovery initramfs",
            expected_size=ramdisk_size_expected,
            expected_digest=ramdisk_digest,
        ) as ramdisk_fd,
    ):
        header = os.pread(raw_fd, BOOT_V3_PAGE_SIZE, 0)
        if len(header) != BOOT_V3_PAGE_SIZE or header[:8] != b"ANDROID!":
            fail("raw wrapper is not Android boot-v3")
        kernel_size, ramdisk_size, _os_version, header_size = struct.unpack_from(
            "<4I", header, 8
        )
        header_version = struct.unpack_from("<I", header, 40)[0]
        if (
            header_version != 3
            or header_size != BOOT_V3_HEADER_SIZE
            or any(header[24:40])
            or any(header[BOOT_V3_HEADER_SIZE:BOOT_V3_PAGE_SIZE])
            or kernel_size != kernel_size_expected
            or ramdisk_size != ramdisk_size_expected
        ):
            fail("raw wrapper boot-v3 header is not exact")
        command_line_field = header[44:BOOT_V3_HEADER_SIZE]
        command_line_bytes, separator, trailing = command_line_field.partition(b"\0")
        try:
            command_line = command_line_bytes.decode("ascii")
        except UnicodeError as error:
            raise AdmissionError("raw wrapper command line is not ASCII") from error
        if (
            not separator
            or any(trailing)
            or command_line != expected_cmdline
        ):
            fail("raw wrapper command line is not exact")
        kernel_offset = BOOT_V3_PAGE_SIZE
        ramdisk_offset = kernel_offset + align(kernel_size, BOOT_V3_PAGE_SIZE)
        expected_size = ramdisk_offset + align(ramdisk_size, BOOT_V3_PAGE_SIZE)
        if raw_size != expected_size:
            fail("raw wrapper boot-v3 geometry is not exact")

        def compare_region(
            source_fd: int,
            source_size: int,
            offset: int,
            label: str,
        ) -> None:
            source_offset = 0
            while source_offset < source_size:
                length = min(1024 * 1024, source_size - source_offset)
                if os.pread(source_fd, length, source_offset) != os.pread(
                    raw_fd,
                    length,
                    offset + source_offset,
                ):
                    fail(f"raw wrapper does not embed the exact {label}")
                source_offset += length

        compare_region(kernel_fd, kernel_size, kernel_offset, "wrapper Image")
        compare_region(
            ramdisk_fd,
            ramdisk_size,
            ramdisk_offset,
            "recovery initramfs",
        )
        zero_region(
            raw_fd,
            kernel_offset + kernel_size,
            ramdisk_offset,
            "boot-v3 kernel",
        )
        zero_region(
            raw_fd,
            ramdisk_offset + ramdisk_size,
            expected_size,
            "boot-v3 ramdisk",
        )


def verify_wrapper_config(
    path: Path,
    identity: tuple[int, str],
) -> None:
    payload = read_verified_bytes(
        path,
        "wrapper config",
        expected_size=identity[0],
        expected_digest=identity[1],
    )
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeError as error:
        raise AdmissionError("wrapper config is not ASCII") from error
    for required in (
        "CONFIG_PSTORE=y",
        "CONFIG_PSTORE_CONSOLE=y",
        "CONFIG_PSTORE_PMSG=y",
        "CONFIG_PSTORE_RAM=y",
    ):
        if lines.count(required) != 1:
            fail(f"wrapper config lacks exact {required}")


def verify_unsigned_avb(
    avb: Path,
    raw: Path,
    algorithm: str,
    avb_identity: tuple[int, str],
    raw_identity: tuple[int, str],
) -> None:
    if algorithm != "NONE":
        fail("offline wrapper AVB algorithm is not NONE")
    avb_size, avb_digest = avb_identity
    raw_size, raw_digest = raw_identity
    try:
        with (
            verified_descriptor(
                avb,
                "unsigned AVB wrapper",
                expected_size=avb_size,
                expected_digest=avb_digest,
            ) as avb_fd,
            verified_descriptor(
                raw,
                "raw boot image",
                expected_size=raw_size,
                expected_digest=raw_digest,
            ) as raw_fd,
        ):
            footer = os.pread(avb_fd, 64, avb_size - 64)
            magic, major, minor, original_size, offset, size = struct.unpack(
                "!4s2I3Q28x", footer
            )
            if (
                magic != b"AVBf"
                or (major, minor) != (1, 0)
                or original_size != raw_size
                or offset != original_size
                or size < 256
                or offset + size > avb_size - 64
            ):
                fail("AVB footer is not exact")
            header = os.pread(avb_fd, 256, offset)
            if len(header) != 256 or header[:4] != b"AVB0":
                fail("AVB metadata header is not exact")
            required_major, required_minor = struct.unpack_from("!2I", header, 4)
            authentication_size, auxiliary_size = struct.unpack_from("!2Q", header, 12)
            hash_offset, hash_size = struct.unpack_from("!2Q", header, 32)
            signature_offset, signature_size = struct.unpack_from("!2Q", header, 48)
            public_key_offset, public_key_size = struct.unpack_from("!2Q", header, 64)
            metadata_offset, metadata_size = struct.unpack_from("!2Q", header, 80)
            descriptors_offset, descriptors_size = struct.unpack_from("!2Q", header, 96)
            rollback_index = struct.unpack_from("!Q", header, 112)[0]
            flags, rollback_location = struct.unpack_from("!2I", header, 120)
            release = header[128:175].split(b"\0", 1)[0]
            if (
                (required_major, required_minor) != (1, 0)
                or authentication_size != 0
                or struct.unpack_from("!I", header, 28)[0] != 0
                or size != 256 + authentication_size + auxiliary_size
                or (hash_offset, hash_size) != (0, 0)
                or (signature_offset, signature_size) != (0, 0)
                or public_key_size != 0
                or metadata_size != 0
                or descriptors_offset != 0
                or descriptors_size != public_key_offset
                or descriptors_size != metadata_offset
                or rollback_index != 0
                or flags != 0
                or rollback_location != 0
                or release != b"avbtool 1.4.0"
                or any(header[175:])
            ):
                fail("offline wrapper AVB algorithm is not NONE")
            auxiliary = os.pread(avb_fd, auxiliary_size, offset + 256)
            if len(auxiliary) != auxiliary_size or descriptors_size != 200:
                fail("AVB hash descriptor geometry is not exact")
            descriptor = auxiliary[:descriptors_size]
            try:
                (
                    tag,
                    following,
                    image_size,
                    hash_algorithm,
                    partition_length,
                    salt_length,
                    digest_length,
                    descriptor_flags,
                    reserved,
                ) = struct.unpack("!QQQ32sLLLL60s", descriptor[:132])
            except struct.error as error:
                raise AdmissionError("AVB hash descriptor is malformed") from error
            variable = descriptor[132:]
            partition = variable[:partition_length]
            salt_start = partition_length
            digest_start = salt_start + salt_length
            salt = variable[salt_start:digest_start]
            recorded_digest = variable[digest_start : digest_start + digest_length]
            expected_following = align(
                116 + partition_length + salt_length + digest_length,
                8,
            )
            if (
                tag != 2
                or following != expected_following
                or 16 + following != descriptors_size
                or image_size != raw_size
                or hash_algorithm.rstrip(b"\0") != b"sha256"
                or any(hash_algorithm[len(b"sha256") :])
                or partition != b"boot"
                or partition_length != 4
                or salt_length != 32
                or digest_length != 32
                or descriptor_flags != 0
                or any(reserved)
                or digest_start + digest_length != len(variable)
                or salt != bytes.fromhex(raw_digest)
                or any(auxiliary[descriptors_size:])
            ):
                fail("AVB hash descriptor is not exact")
            calculated = hashlib.sha256(salt)
            raw_offset = 0
            while raw_offset < raw_size:
                block = os.pread(
                    raw_fd,
                    min(1024 * 1024, raw_size - raw_offset),
                    raw_offset,
                )
                if not block:
                    fail("AVB raw payload is truncated")
                calculated.update(block)
                raw_offset += len(block)
            if calculated.digest() != recorded_digest:
                fail("AVB hash descriptor digest is invalid")
            compare_prefix(raw_fd, avb_fd, raw_size)
            zero_region(
                avb_fd,
                offset + size,
                avb_size - 64,
                "AVB partition",
            )
    except (OSError, struct.error) as error:
        raise AdmissionError("AVB footer is not exact") from error


def verify_signature(
    manifest: Path,
    signature: Path,
    key: Path,
    manifest_identity: tuple[int, str],
    signature_identity: tuple[int, str],
    key_identity: tuple[int, str],
) -> None:
    openssl = Path("/usr/bin/openssl")
    try:
        metadata = openssl.lstat()
    except OSError as error:
        raise AdmissionError("fixed OpenSSL verifier is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o022
        or not os.access(openssl, os.X_OK)
    ):
        fail("fixed OpenSSL verifier is unavailable")
    manifest_size, manifest_digest = manifest_identity
    signature_size, signature_digest = signature_identity
    key_size, key_digest = key_identity
    with (
        verified_descriptor(
            manifest,
            "execution runtime manifest",
            expected_size=manifest_size,
            expected_digest=manifest_digest,
        ) as manifest_fd,
        verified_descriptor(
            signature,
            "execution runtime signature",
            expected_size=signature_size,
            expected_digest=signature_digest,
        ) as signature_fd,
        verified_descriptor(
            key,
            "execution recovery trust key",
            expected_size=key_size,
            expected_digest=key_digest,
        ) as key_fd,
    ):
        raw_key = read_descriptor(key_fd)
        if len(raw_key) != 32:
            fail("execution recovery trust key is not raw Ed25519")
        with tempfile.NamedTemporaryFile(prefix="rog5-retention-key-") as der:
            der.write(bytes.fromhex("302a300506032b6570032100") + raw_key)
            der.flush()
            result = subprocess.run(
                [
                    str(openssl),
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-keyform",
                    "DER",
                    "-inkey",
                    der.name,
                    "-rawin",
                    "-in",
                    f"/proc/self/fd/{manifest_fd}",
                    "-sigfile",
                    f"/proc/self/fd/{signature_fd}",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(manifest_fd, signature_fd),
            )
    if result.returncode != 0:
        fail("execution runtime signature is invalid")


def verify_candidate_and_bundle(
    repo: Path,
    root: Path,
    execution: dict[str, Any],
    artifacts_path: Path,
) -> tuple[str, str]:
    candidate_path = safe_child(
        repo,
        execution["candidate_path"],
        "tracked execution candidate",
    )
    candidate_sha256 = require_sha256(
        execution["candidate_sha256"],
        "tracked execution candidate SHA-256",
    )
    candidate_size = execution["candidate_size"]
    if (
        not isinstance(candidate_size, int)
        or isinstance(candidate_size, bool)
        or candidate_size <= 0
    ):
        fail("tracked execution candidate size is invalid")
    candidate = read_json(
        candidate_path,
        "tracked execution candidate",
        expected_size=candidate_size,
        expected_digest=candidate_sha256,
    )
    candidate_id = require_string(execution["candidate"], "candidate identity")
    require_keys(
        candidate,
        {
            "format",
            "candidate",
            "status",
            "authority",
            "bundle",
            "profile",
            "target_id",
            "target_release",
            "rollback_timeout",
            "target_timeout",
            "a660_command_manifest_sha256",
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_tree_entries",
            "root_subtree",
            "artifacts",
        },
        "tracked execution candidate",
    )
    if (
        candidate.get("format") != "rog5-recovery-candidate-v1"
        or candidate.get("candidate") != candidate_id
        or candidate.get("status") != "offline"
        or candidate.get("authority") != "none"
        or candidate.get("bundle") != candidate_id
        or candidate.get("target_id") != candidate_id
        or candidate.get("profile") != "diagnostic-initramfs-v1"
    ):
        fail("tracked execution candidate is not authority-free and exact")

    inventory = read_safe_file(artifacts_path, "artifact inventory").decode(
        "utf-8", errors="strict"
    )
    rows = [line.split("\t") for line in inventory.splitlines()]
    if not rows or rows[0] != ["name", "size", "sha256", "role", "tracked"]:
        fail("artifact inventory header is not exact")
    matches = [row for row in rows[1:] if row and row[0] == execution["candidate_path"]]
    if len(matches) != 1 or len(matches[0]) != 5:
        fail("tracked execution candidate inventory is not unique")
    row = matches[0]
    if (
        row[1] != str(candidate_size)
        or row[2] != candidate_sha256
        or not row[3].startswith("tracked ")
        or "consumed" in row[3]
        or row[4] != "yes"
    ):
        fail("tracked execution candidate inventory is not current")

    record_a, _record_b, _record_digest = verify_pair(
        root,
        execution["candidate_record"],
        "execution candidate record",
    )
    manifest_a, manifest_b, manifest_sha256 = verify_pair(
        root,
        execution["runtime_manifest"],
        "execution runtime manifest",
    )
    signature_a, signature_b, _signature_digest = verify_pair(
        root,
        execution["runtime_signature"],
        "execution runtime signature",
    )
    trust_key, trust_sha256 = verify_single(
        root,
        execution["trust_key"],
        "execution recovery trust key",
    )
    require_absent_child(root, execution["private_key_path"], "private signing key")

    record_identity = expected_identity(
        execution["candidate_record"],
        "execution candidate record",
        pair=True,
    )
    manifest_identity = expected_identity(
        execution["runtime_manifest"],
        "execution runtime manifest",
        pair=True,
    )
    signature_identity = expected_identity(
        execution["runtime_signature"],
        "execution runtime signature",
        pair=True,
    )
    trust_identity = expected_identity(
        execution["trust_key"],
        "execution recovery trust key",
        pair=False,
    )
    record = parse_key_values(
        read_verified_bytes(
            record_a,
            "execution candidate record",
            expected_size=record_identity[0],
            expected_digest=record_identity[1],
        ),
        "execution candidate record",
    )
    if set(record) != {
        "format",
        "candidate",
        "status",
        "authority",
        "bundle",
        "manifest_sha256",
        "trust_key_sha256",
    } or record != {
        "format": "rog5-prepared-candidate-v1",
        "candidate": candidate_id,
        "status": "offline",
        "authority": "none",
        "bundle": candidate_id,
        "manifest_sha256": manifest_sha256,
        "trust_key_sha256": trust_sha256,
    }:
        fail("execution candidate record is not exact and authority-free")

    manifest = parse_key_values(
        read_verified_bytes(
            manifest_a,
            "execution runtime manifest",
            expected_size=manifest_identity[0],
            expected_digest=manifest_identity[1],
        ),
        "execution runtime manifest",
    )
    if set(manifest) != {
        "format",
        "bundle",
        "profile",
        "kernel_size",
        "kernel_sha256",
        "dtb_size",
        "dtb_sha256",
        "initramfs_size",
        "initramfs_sha256",
        "target_id",
        "target_release",
        "rollback_timeout",
        "target_timeout",
        "a660_command_manifest_sha256",
        "root_generation",
        "root_tree_sha256",
        "root_seal_sha256",
        "root_tree_entries",
        "root_subtree",
    }:
        fail("execution runtime manifest fields are not exact")
    bound_fields = (
        "profile",
        "target_id",
        "target_release",
        "rollback_timeout",
        "target_timeout",
        "a660_command_manifest_sha256",
        "root_generation",
        "root_tree_sha256",
        "root_seal_sha256",
        "root_tree_entries",
        "root_subtree",
    )
    if any(
        not isinstance(candidate.get(field), str) or not candidate[field]
        for field in bound_fields
    ):
        fail("execution candidate binding fields are incomplete")
    if (
        manifest.get("format") != "rog5-recovery-bundle-v2"
        or manifest.get("bundle") != candidate_id
        or any(manifest.get(field) != candidate[field] for field in bound_fields)
    ):
        fail("execution runtime manifest no longer binds the candidate")

    bundle_roots = tuple(
        safe_root(
            safe_child(root, execution[key], label),
            label,
        )
        for key, label in (
            ("bundle_a", "execution bundle A"),
            ("bundle_b", "execution bundle B"),
        )
    )
    if bundle_roots[0] == bundle_roots[1]:
        fail("execution bundle roots are not distinct")
    expected_bundle_names = {
        "Image",
        "board.dtb",
        "initramfs.cpio.gz",
        "manifest",
        "manifest.sig",
    }
    for bundle_root, label in zip(
        bundle_roots,
        ("execution bundle A", "execution bundle B"),
        strict=True,
    ):
        try:
            names = {entry.name for entry in os.scandir(bundle_root)}
        except OSError as error:
            raise AdmissionError(f"{label} inventory is unavailable") from error
        if names != expected_bundle_names:
            fail(f"{label} inventory is not exact")
    artifacts = candidate.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
        "Image",
        "board.dtb",
        "initramfs.cpio.gz",
    }:
        fail("execution candidate artifact set changed")
    manifest_names = {
        "Image": ("kernel_size", "kernel_sha256"),
        "board.dtb": ("dtb_size", "dtb_sha256"),
        "initramfs.cpio.gz": ("initramfs_size", "initramfs_sha256"),
    }
    for name, fields in manifest_names.items():
        artifact = require_keys(
            artifacts[name],
            {"path", "size", "sha256"},
            f"candidate {name}",
        )
        if (
            manifest.get(fields[0]) != str(artifact["size"])
            or manifest.get(fields[1]) != artifact["sha256"]
        ):
            fail(f"execution manifest does not bind {name}")
        first = safe_child(bundle_roots[0], name, f"bundle A {name}")
        second = safe_child(bundle_roots[1], name, f"bundle B {name}")
        verify_file(first, artifact["size"], artifact["sha256"], f"bundle A {name}")
        verify_file(second, artifact["size"], artifact["sha256"], f"bundle B {name}")

    verify_signature(
        manifest_a,
        signature_a,
        trust_key,
        manifest_identity,
        signature_identity,
        trust_identity,
    )
    verify_signature(
        manifest_b,
        signature_b,
        trust_key,
        manifest_identity,
        signature_identity,
        trust_identity,
    )
    return candidate_sha256, manifest_sha256


def verify_policy(policy_path: Path, required_allow_rows: Any) -> int:
    if required_allow_rows != 0:
        fail("offline review must require zero temporary-boot admissions")
    try:
        text = read_safe_file(policy_path, "temporary-boot policy").decode("utf-8")
    except UnicodeError as error:
        raise AdmissionError("temporary-boot policy is not UTF-8") from error
    rows = [line.split("\t") for line in text.splitlines()]
    if not rows or rows[0] != ["name", "status", "basis"]:
        fail("temporary-boot policy header is not exact")
    allow_rows = 0
    for row in rows[1:]:
        if len(row) != 3 or not all(row):
            fail("temporary-boot policy row is malformed")
        if row[1] == "allow":
            allow_rows += 1
        elif row[1] not in {"deny", "revoked"}:
            fail("temporary-boot policy status is unknown")
    if allow_rows != required_allow_rows:
        fail("temporary-boot policy grants authority during HOLD")
    return allow_rows


def verify_observer_evidence(
    path: Path,
    evidence_identity: tuple[int, str],
    initramfs_identity: tuple[int, str],
    config_identity: tuple[int, str],
    image_identity: tuple[int, str],
    raw_identity: tuple[int, str],
    avb_identity: tuple[int, str],
) -> None:
    payload = read_verified_bytes(
        path,
        "observer wrapper evidence",
        expected_size=evidence_identity[0],
        expected_digest=evidence_identity[1],
    )
    try:
        text = payload.decode("ascii")
    except UnicodeError as error:
        raise AdmissionError("observer wrapper evidence is not ASCII") from error
    lines = text.splitlines()
    if not lines or lines[-1] != (
        "PASS observation-only clean-twin wrapper evidence is exact and offline-only"
    ):
        fail("observer wrapper evidence result is not exact")
    values = parse_key_values(
        ("\n".join(lines[:-1]) + "\n").encode("ascii"),
        "observer wrapper evidence",
    )
    required = {
        "format": "rog5-observation-recovery-wrapper-evidence-v1",
        "observer_initramfs_size": str(initramfs_identity[0]),
        "observer_initramfs_sha256": initramfs_identity[1],
        "wrapper_config_size": str(config_identity[0]),
        "wrapper_config_sha256": config_identity[1],
        "wrapper_image_size": str(image_identity[0]),
        "wrapper_image_sha256": image_identity[1],
        "raw_boot_size": str(raw_identity[0]),
        "raw_boot_sha256": raw_identity[1],
        "unsigned_avb_size": str(avb_identity[0]),
        "unsigned_avb_sha256": avb_identity[1],
        "ramoops_mem_address": "0x9b800000",
        "ramoops_mem_size": "0x400000",
        "authority": "none",
        "candidate": "none",
        "boot_authority": "none",
        "retention": "unproven",
    }
    if values != required:
        fail("observer wrapper evidence does not bind the offline role")


def verify(
    profile_path: Path,
    repo: Path,
    execution_root: Path,
    observer_root: Path,
    artifacts_path: Path,
    policy_path: Path,
    *,
    enforce_repository_layout: bool,
) -> str:
    repo = safe_root(repo, "repository root")
    execution_root = safe_root(execution_root, "execution evidence root")
    observer_root = safe_root(observer_root, "observer evidence root")
    if execution_root == observer_root:
        fail("execution and observer evidence roots are not distinct")
    for child, parent in (
        (execution_root, observer_root),
        (observer_root, execution_root),
    ):
        try:
            child.relative_to(parent)
        except ValueError:
            continue
        fail("execution and observer evidence roots overlap")
    if enforce_repository_layout:
        build_root = repo / "build"
        git = Path("/usr/bin/git")
        try:
            git_metadata = git.lstat()
        except OSError as error:
            raise AdmissionError("fixed Git verifier is unavailable") from error
        if (
            not stat.S_ISREG(git_metadata.st_mode)
            or git_metadata.st_uid != 0
            or stat.S_IMODE(git_metadata.st_mode) & 0o022
            or not os.access(git, os.X_OK)
        ):
            fail("fixed Git verifier is unavailable")
        for root, label in (
            (execution_root, "execution evidence root"),
            (observer_root, "observer evidence root"),
        ):
            try:
                root.relative_to(build_root)
            except ValueError:
                fail(f"{label} must remain below the ignored build directory")
            result = subprocess.run(
                [str(git), "-C", str(repo), "check-ignore", "-q", str(root)],
                check=False,
            )
            if result.returncode != 0:
                fail(f"{label} is not ignored by Git")

    profile = read_json(profile_path, "retention-cycle profile")
    require_keys(
        profile,
        {
            "format",
            "profile",
            "state",
            "authority",
            "boot_authority",
            "retention",
            "missing_pstore",
            "recovery_cmdline",
            "sequence",
            "execution",
            "observer",
            "claims",
            "policy",
        },
        "retention-cycle profile",
    )
    if (
        profile["format"] != "rog5-retention-cycle-admission-review-v1"
        or profile["profile"] != "host-rendezvous-v3-observer-v1"
        or profile["state"] != "hold"
        or profile["authority"] != "none"
        or profile["boot_authority"] != "none"
        or profile["retention"] != "unproven"
        or profile["missing_pstore"] != "inconclusive"
        or profile["recovery_cmdline"] != EXPECTED_RECOVERY_CMDLINE
        or tuple(profile["sequence"]) != EXPECTED_SEQUENCE
    ):
        fail("retention-cycle profile weakens the HOLD boundary")

    execution = require_keys(
        profile["execution"],
        {
            "role",
            "candidate_path",
            "candidate_size",
            "candidate_sha256",
            "candidate",
            "candidate_record",
            "bundle_a",
            "bundle_b",
            "runtime_manifest",
            "runtime_signature",
            "trust_key",
            "private_key_path",
            "trust_class",
            "recovery_mode",
            "avb_algorithm",
            "recovery_initramfs",
            "wrapper_config",
            "wrapper_image",
            "raw_boot",
            "unsigned_avb",
            "claim",
        },
        "execution role",
    )
    observer = require_keys(
        profile["observer"],
        {
            "role",
            "host_action",
            "recovery_mode",
            "avb_algorithm",
            "wrapper_evidence",
            "recovery_initramfs",
            "wrapper_config",
            "wrapper_image",
            "raw_boot",
            "unsigned_avb",
            "claim",
        },
        "observer role",
    )
    if (
        execution["role"] != "target-execution-v1"
        or execution["trust_class"] != "disposable-offline"
        or execution["recovery_mode"] != "full-v1"
        or execution["avb_algorithm"] != "NONE"
        or execution["claim"] != "unissued"
        or observer["role"] != "observation-only-v1"
        or observer["host_action"] != "postmortem-status"
        or observer["recovery_mode"] != "observation-only-v1"
        or observer["avb_algorithm"] != "NONE"
        or observer["claim"] != "unissued"
    ):
        fail("execution and observation roles are not fail-closed")

    candidate_sha256, manifest_sha256 = verify_candidate_and_bundle(
        repo,
        execution_root,
        execution,
        artifacts_path,
    )
    execution_initramfs_a, _execution_initramfs_b, execution_initramfs = verify_pair(
        execution_root,
        execution["recovery_initramfs"],
        "execution recovery initramfs",
    )
    _execution_config_a, _execution_config_b, execution_config = verify_pair(
        execution_root,
        execution["wrapper_config"],
        "execution wrapper config",
    )
    execution_image_a, _execution_image_b, execution_image = verify_pair(
        execution_root,
        execution["wrapper_image"],
        "execution wrapper Image",
    )
    execution_raw_a, _execution_raw_b, execution_raw = verify_pair(
        execution_root,
        execution["raw_boot"],
        "execution raw boot",
    )
    execution_avb_a, _execution_avb_b, execution_avb = verify_pair(
        execution_root,
        execution["unsigned_avb"],
        "execution unsigned AVB",
    )
    execution_initramfs_identity = expected_identity(
        execution["recovery_initramfs"],
        "execution recovery initramfs",
        pair=True,
    )
    execution_image_identity = expected_identity(
        execution["wrapper_image"],
        "execution wrapper Image",
        pair=True,
    )
    execution_raw_identity = expected_identity(
        execution["raw_boot"],
        "execution raw boot",
        pair=True,
    )
    execution_avb_identity = expected_identity(
        execution["unsigned_avb"],
        "execution unsigned AVB",
        pair=True,
    )
    execution_config_identity = expected_identity(
        execution["wrapper_config"],
        "execution wrapper config",
        pair=True,
    )
    verify_wrapper_config(_execution_config_a, execution_config_identity)
    execution_entries = verify_recovery_role(
        execution_initramfs_a,
        "full-v1",
        *execution_initramfs_identity,
    )
    verify_boot_v3(
        execution_raw_a,
        execution_image_a,
        execution_initramfs_a,
        execution_raw_identity,
        execution_image_identity,
        execution_initramfs_identity,
        profile["recovery_cmdline"],
    )
    verify_unsigned_avb(
        execution_avb_a,
        execution_raw_a,
        execution["avb_algorithm"],
        execution_avb_identity,
        execution_raw_identity,
    )

    evidence_path, _evidence_sha256 = verify_single(
        observer_root,
        observer["wrapper_evidence"],
        "observer wrapper evidence",
    )
    observer_initramfs_a, _observer_initramfs_b, observer_initramfs = verify_pair(
        observer_root,
        observer["recovery_initramfs"],
        "observer recovery initramfs",
    )
    _observer_config_a, _observer_config_b, observer_config = verify_pair(
        observer_root,
        observer["wrapper_config"],
        "observer wrapper config",
    )
    observer_image_a, _observer_image_b, observer_image = verify_pair(
        observer_root,
        observer["wrapper_image"],
        "observer wrapper Image",
    )
    observer_raw_a, _observer_raw_b, observer_raw = verify_pair(
        observer_root,
        observer["raw_boot"],
        "observer raw boot",
    )
    observer_avb_a, _observer_avb_b, observer_avb = verify_pair(
        observer_root,
        observer["unsigned_avb"],
        "observer unsigned AVB",
    )
    evidence_identity = expected_identity(
        observer["wrapper_evidence"],
        "observer wrapper evidence",
        pair=False,
    )
    observer_initramfs_identity = expected_identity(
        observer["recovery_initramfs"],
        "observer recovery initramfs",
        pair=True,
    )
    observer_config_identity = expected_identity(
        observer["wrapper_config"],
        "observer wrapper config",
        pair=True,
    )
    observer_image_identity = expected_identity(
        observer["wrapper_image"],
        "observer wrapper Image",
        pair=True,
    )
    observer_raw_identity = expected_identity(
        observer["raw_boot"],
        "observer raw boot",
        pair=True,
    )
    observer_avb_identity = expected_identity(
        observer["unsigned_avb"],
        "observer unsigned AVB",
        pair=True,
    )
    observer_entries = verify_recovery_role(
        observer_initramfs_a,
        "observation-only-v1",
        *observer_initramfs_identity,
    )
    verify_boot_v3(
        observer_raw_a,
        observer_image_a,
        observer_initramfs_a,
        observer_raw_identity,
        observer_image_identity,
        observer_initramfs_identity,
        profile["recovery_cmdline"],
    )
    verify_unsigned_avb(
        observer_avb_a,
        observer_raw_a,
        observer["avb_algorithm"],
        observer_avb_identity,
        observer_raw_identity,
    )
    verify_observer_evidence(
        evidence_path,
        evidence_identity,
        observer_initramfs_identity,
        observer_config_identity,
        observer_image_identity,
        observer_raw_identity,
        observer_avb_identity,
    )
    verify_recovery_derivation(execution_entries, observer_entries)

    for label, first, second in (
        ("recovery initramfs", execution_initramfs, observer_initramfs),
        ("wrapper Image", execution_image, observer_image),
        ("raw boot", execution_raw, observer_raw),
        ("AVB wrapper", execution_avb, observer_avb),
    ):
        if first == second:
            fail(f"execution and observer {label} identities are not distinct")
    if execution_config != observer_config:
        fail("execution and observer wrappers do not share the reviewed config")

    claims = require_keys(
        profile["claims"],
        {
            "consumer",
            "consumer_size",
            "consumer_sha256",
            "execution",
            "observer",
            "issuance_requirement",
            "reuse",
        },
        "claim policy",
    )
    if (
        claims["consumer"] != "scripts/host/consume-exact-boot-claim.py"
        or claims["execution"] != "not-defined"
        or claims["observer"] != "not-defined"
        or claims["issuance_requirement"] != "distinct-exact-records"
        or claims["reuse"] != "forbidden"
    ):
        fail("one-use claim policy is not exact")
    consumer = safe_child(repo, claims["consumer"], "generic claim consumer")
    consumer_size = claims["consumer_size"]
    if (
        not isinstance(consumer_size, int)
        or isinstance(consumer_size, bool)
        or consumer_size <= 0
    ):
        fail("generic claim consumer size is invalid")
    consumer_digest = require_sha256(
        claims["consumer_sha256"],
        "generic claim consumer SHA-256",
    )
    consumer_source = read_verified_bytes(
        consumer,
        "generic claim consumer",
        expected_size=consumer_size,
        expected_digest=consumer_digest,
    )
    try:
        consumer_tree = ast.parse(consumer_source, filename=str(consumer))
    except (SyntaxError, UnicodeError) as error:
        raise AdmissionError("generic claim consumer cannot be inspected") from error
    profile_assignments = [
        node
        for node in consumer_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CLAIM_PROFILES"
            for target in node.targets
        )
    ]
    claims_assignments = [
        node
        for node in consumer_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CLAIMS"
            for target in node.targets
        )
    ]
    if len(profile_assignments) != 1 or len(claims_assignments) != 1:
        fail("generic claim consumer registry is not exact")
    try:
        registered_profiles = ast.literal_eval(profile_assignments[0].value)
    except (ValueError, TypeError) as error:
        raise AdmissionError("generic claim consumer registry is not exact") from error
    claims_expression = claims_assignments[0].value
    if (
        not isinstance(registered_profiles, tuple)
        or not registered_profiles
        or len(set(registered_profiles)) != len(registered_profiles)
        or any(not isinstance(item, str) or not item for item in registered_profiles)
        or not isinstance(claims_expression, ast.DictComp)
        or not isinstance(claims_expression.key, ast.Name)
        or claims_expression.key.id != "profile"
        or not isinstance(claims_expression.value, ast.Call)
        or not isinstance(claims_expression.value.func, ast.Name)
        or claims_expression.value.func.id != "exact_record"
        or len(claims_expression.value.args) != 1
        or not isinstance(claims_expression.value.args[0], ast.Name)
        or claims_expression.value.args[0].id != "profile"
        or len(claims_expression.generators) != 1
        or not isinstance(claims_expression.generators[0].target, ast.Name)
        or claims_expression.generators[0].target.id != "profile"
        or not isinstance(claims_expression.generators[0].iter, ast.Name)
        or claims_expression.generators[0].iter.id != "CLAIM_PROFILES"
        or claims_expression.generators[0].ifs
        or claims_expression.generators[0].is_async
    ):
        fail("generic claim consumer registry is not exact")
    for node in ast.walk(consumer_tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "CLAIMS"
        ):
            fail("generic claim consumer registry is mutated after definition")
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = list(node.targets)
        for target in targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "CLAIMS"
            ):
                fail("generic claim consumer registry is mutated after definition")
    if profile["profile"] in registered_profiles:
        fail("HOLD profile already has a consumable boot claim")

    policy = require_keys(
        profile["policy"],
        {"path", "required_allow_rows"},
        "temporary-boot policy contract",
    )
    expected_policy = safe_child(repo, policy["path"], "profile policy path")
    if expected_policy != policy_path:
        fail("temporary-boot policy path is not repository-owned")
    allow_rows = verify_policy(policy_path, policy["required_allow_rows"])

    return "\n".join(
        (
            "format=rog5-retention-cycle-admission-review-v1",
            f"profile={profile['profile']}",
            f"execution_candidate_sha256={candidate_sha256}",
            f"execution_runtime_manifest_sha256={manifest_sha256}",
            f"execution_recovery_avb_sha256={execution_avb}",
            f"observer_recovery_avb_sha256={observer_avb}",
            f"temporary_boot_allow_rows={allow_rows}",
            "execution_claim=not-defined",
            "observer_claim=not-defined",
            "authority=none",
            "boot_authority=none",
            "retention=unproven",
            "missing_pstore=inconclusive",
            "recommendation=HOLD",
            "PASS exact target/observer retention-cycle review remains authority-free",
        )
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: verify-retention-cycle-admission.py "
            "EXECUTION_EVIDENCE_ROOT OBSERVER_EVIDENCE_ROOT",
            file=sys.stderr,
        )
        return 2
    try:
        report = verify(
            PROFILE,
            REPO,
            Path(argv[1]).resolve(strict=True),
            Path(argv[2]).resolve(strict=True),
            ARTIFACTS,
            REPO / "manifests/temporary-boot-images.tsv",
            enforce_repository_layout=True,
        )
    except (AdmissionError, OSError, UnicodeError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
