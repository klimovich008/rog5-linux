#!/usr/bin/env python3
"""Publish and materialize hash-pinned stable-recovery wrapper cache entries."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import NoReturn


PROFILE_FORMAT = "rog5-stable-recovery-wrapper-cache-profile-v1"
ENTRY_FORMAT = "rog5-stable-recovery-wrapper-cache-entry-v1"
BINDING_FORMAT = "rog5-stable-recovery-wrapper-cache-binding-v1"
RENAME_NOREPLACE = 1
HEX = frozenset("0123456789abcdef")
PROFILE_KEYS = (
    "format",
    "source_archive_sha256",
    "source_marker_sha256",
    "source_tree_format",
    "source_tree_entries",
    "source_tree_regular_files",
    "source_tree_directories",
    "source_tree_symlinks",
    "source_tree_bytes",
    "source_tree_sha256",
    "source_seal_tool_sha256",
    "reference_config_sha256",
    "wrapper_config_sha256",
    "builder_image",
    "builder_id",
    "builder_digest",
    "compiler",
    "build_script_sha256",
    "repack_script_sha256",
    "boot_template_sha256",
    "mkbootimg_sha256",
    "unpack_bootimg_sha256",
    "avbtool_sha256",
    "partition_size",
    "cmdline_overrides",
    "cmdline_remove_keys",
)
SOURCE_SEAL_KEYS = (
    "tree_format",
    "tree_entries",
    "tree_regular_files",
    "tree_directories",
    "tree_symlinks",
    "tree_bytes",
    "tree_sha256",
)
INPUT_FILE_FIELDS = (
    ("source_tree_tool", "source_seal_tool_sha256"),
    ("reference_config", "reference_config_sha256"),
    ("build_script", "build_script_sha256"),
    ("repack_script", "repack_script_sha256"),
    ("boot_template", "boot_template_sha256"),
    ("mkbootimg", "mkbootimg_sha256"),
    ("unpack_bootimg", "unpack_bootimg_sha256"),
    ("avbtool", "avbtool_sha256"),
)
CACHE_FILES = (
    "wrapper.config",
    "wrapper.Image",
    "wrapper.build-meta",
    "recovery.cpio.gz",
    "stable-recovery.raw.img",
    "stable-recovery.avb.img",
)
ENTRY_KEYS = (
    "format",
    "input_key",
    "profile_sha256",
    *PROFILE_KEYS[1:],
    "initramfs_size",
    "initramfs_sha256",
    "wrapper_config_size",
    "wrapper_config_output_sha256",
    "wrapper_image_size",
    "wrapper_image_sha256",
    "build_meta_size",
    "build_meta_sha256",
    "raw_image_size",
    "raw_image_sha256",
    "avb_image_size",
    "avb_image_sha256",
)
BINDING_KEYS = ("format", "input_key", "entry_id")


class CacheError(RuntimeError):
    """The cache contract was not met."""


def fail(message: str) -> NoReturn:
    raise CacheError(message)


def duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate profile field: {key}")
        result[key] = value
    return result


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in HEX for character in value)
    )


def read_regular(path: Path) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise CacheError(f"cannot inspect input: {path}") from error
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
    ):
        fail(f"input is not a single-link regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CacheError(f"cannot open input: {path}") from error
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
        ) != (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_size,
            metadata.st_mtime_ns,
        ):
            fail(f"input changed while opening: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        ) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
        ):
            fail(f"input changed while reading: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def file_identity(path: Path) -> tuple[int, str]:
    data = read_regular(path)
    return len(data), hashlib.sha256(data).hexdigest()


def load_profile(path: Path) -> tuple[dict[str, object], str]:
    raw = read_regular(path)
    try:
        profile = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=duplicate_object,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CacheError("cache profile is not canonical ASCII JSON") from error
    if not isinstance(profile, dict) or tuple(profile) != PROFILE_KEYS:
        fail("cache profile fields or ordering changed")
    canonical = (
        json.dumps(profile, indent=2, ensure_ascii=True) + "\n"
    ).encode("ascii")
    if raw != canonical:
        fail("cache profile JSON is not canonical")
    if profile["format"] != PROFILE_FORMAT:
        fail("cache profile format changed")
    for key in (
        "source_archive_sha256",
        "source_marker_sha256",
        "source_tree_sha256",
        "source_seal_tool_sha256",
        "reference_config_sha256",
        "wrapper_config_sha256",
        "builder_id",
        "build_script_sha256",
        "repack_script_sha256",
        "boot_template_sha256",
        "mkbootimg_sha256",
        "unpack_bootimg_sha256",
        "avbtool_sha256",
    ):
        if not is_sha256(profile[key]):
            fail(f"cache profile has invalid SHA-256: {key}")
    if profile["source_tree_format"] != "rog5-kernel-source-tree-v1":
        fail("cache profile source-tree format changed")
    for key in (
        "source_tree_entries",
        "source_tree_regular_files",
        "source_tree_directories",
        "source_tree_symlinks",
        "source_tree_bytes",
        "partition_size",
    ):
        if not isinstance(profile[key], int) or profile[key] < 0:
            fail(f"cache profile has invalid integer: {key}")
    if int(profile["source_tree_entries"]) == 0:
        fail("cache profile source tree is empty")
    if int(profile["partition_size"]) == 0:
        fail("cache profile partition size is zero")
    for key in (
        "builder_image",
        "builder_digest",
        "compiler",
        "cmdline_overrides",
        "cmdline_remove_keys",
    ):
        value = profile[key]
        if not isinstance(value, str) or "\n" in value or "\0" in value:
            fail(f"cache profile has invalid string: {key}")
    if not str(profile["builder_image"]) or not str(profile["builder_digest"]):
        fail("cache profile builder identity is empty")
    if not str(profile["builder_digest"]).startswith("sha256:"):
        fail("cache profile builder digest is not SHA-256")
    return profile, hashlib.sha256(raw).hexdigest()


def parse_records(
    data: bytes,
    keys: tuple[str, ...],
    label: str,
    *,
    allow_empty: frozenset[str] = frozenset(),
) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeError as error:
        raise CacheError(f"{label} is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\0" in text:
        fail(f"{label} is not canonical LF text")
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            fail(f"{label} contains a malformed record")
        key, value = line.split("=", 1)
        if (
            not key
            or (not value and key not in allow_empty)
            or key in result
        ):
            fail(f"{label} contains an empty or duplicate record")
        result[key] = value
    if tuple(result) != keys:
        fail(f"{label} fields or ordering changed")
    return result


def read_source_seal(path: str) -> bytes:
    if path == "-":
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(0, min(65536, 1024 * 1024 + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > 1024 * 1024:
                fail("source seal exceeds its bound")
        return b"".join(chunks)
    return read_regular(Path(path))


def validate_source_seal(
    profile: dict[str, object], seal_data: bytes
) -> dict[str, str]:
    seal = parse_records(seal_data, SOURCE_SEAL_KEYS, "source seal")
    expected = {
        "tree_format": str(profile["source_tree_format"]),
        "tree_entries": str(profile["source_tree_entries"]),
        "tree_regular_files": str(profile["source_tree_regular_files"]),
        "tree_directories": str(profile["source_tree_directories"]),
        "tree_symlinks": str(profile["source_tree_symlinks"]),
        "tree_bytes": str(profile["source_tree_bytes"]),
        "tree_sha256": str(profile["source_tree_sha256"]),
    }
    if seal != expected:
        fail("ASUS source tree seal changed")
    return seal


def validate_inputs(
    values: argparse.Namespace,
    profile: dict[str, object],
    profile_sha256: str,
) -> tuple[dict[str, str], bytes]:
    validate_source_seal(profile, read_source_seal(values.source_seal))
    for argument, profile_key in INPUT_FILE_FIELDS:
        path = Path(getattr(values, argument))
        _, actual = file_identity(path)
        if actual != profile[profile_key]:
            fail(f"cache input hash changed: {argument}")
    initramfs = read_regular(Path(values.initramfs))
    if not initramfs:
        fail("stable-recovery initramfs is empty")
    records: dict[str, str] = {
        "format": ENTRY_FORMAT,
        "profile_sha256": profile_sha256,
    }
    for key in PROFILE_KEYS[1:]:
        records[key] = str(profile[key])
    records["initramfs_size"] = str(len(initramfs))
    records["initramfs_sha256"] = hashlib.sha256(initramfs).hexdigest()
    input_bytes = "".join(
        f"{key}={value}\n" for key, value in records.items()
    ).encode("ascii")
    records["input_key"] = hashlib.sha256(input_bytes).hexdigest()
    return records, initramfs


def build_paths(root: Path) -> dict[str, Path]:
    return {
        "wrapper.config": root / "asus-kexec-stage/.config",
        "wrapper.Image": root / "asus-kexec-stage/arch/arm64/boot/Image",
        "wrapper.build-meta": root / "asus-kexec-stage/build-meta.txt",
        "recovery.cpio.gz": root / "rog5-kexec-stage-initramfs.cpio.gz",
    }


def exact_equal(first: Path, second: Path) -> None:
    first_data = read_regular(first)
    second_data = read_regular(second)
    if first_data != second_data:
        fail(f"twin output mismatch: {first.name}")


def validate_build_meta(
    data: bytes,
    profile: dict[str, object],
    initramfs_sha256: str,
    config_sha256: str,
    image_sha256: str,
) -> None:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as error:
        raise CacheError("wrapper build metadata is not ASCII") from error
    expected = [
        f"source_sha256={profile['source_archive_sha256']}",
        "kexec_file=0",
        f"initramfs_sha256={initramfs_sha256}",
        f"compiler={profile['compiler']}",
        f"{config_sha256}  /root/build/asus-kexec-stage/.config",
        (
            f"{image_sha256}  "
            "/root/build/asus-kexec-stage/arch/arm64/boot/Image"
        ),
    ]
    if lines != expected or not data.endswith(b"\n"):
        fail("wrapper build metadata changed")


def collect_outputs(
    values: argparse.Namespace,
    profile: dict[str, object],
    records: dict[str, str],
    initramfs: bytes,
) -> tuple[dict[str, Path], dict[str, str]]:
    build_a = Path(values.build_a)
    build_b = Path(values.build_b)
    try:
        if os.path.samefile(build_a, build_b):
            fail("wrapper twin roots are not distinct")
    except OSError as error:
        raise CacheError("cannot inspect wrapper twin roots") from error
    paths_a = build_paths(build_a)
    paths_b = build_paths(build_b)
    for name in paths_a:
        exact_equal(paths_a[name], paths_b[name])
    exact_equal(Path(values.raw_a), Path(values.raw_b))
    exact_equal(Path(values.avb_a), Path(values.avb_b))

    cached = {
        **paths_a,
        "stable-recovery.raw.img": Path(values.raw_a),
        "stable-recovery.avb.img": Path(values.avb_a),
    }
    identities = {name: file_identity(path) for name, path in cached.items()}
    config_size, config_hash = identities["wrapper.config"]
    image_size, image_hash = identities["wrapper.Image"]
    meta_size, meta_hash = identities["wrapper.build-meta"]
    ramdisk_size, ramdisk_hash = identities["recovery.cpio.gz"]
    raw_size, raw_hash = identities["stable-recovery.raw.img"]
    avb_size, avb_hash = identities["stable-recovery.avb.img"]

    if ramdisk_size != len(initramfs) or ramdisk_hash != records["initramfs_sha256"]:
        fail("wrapper staged initramfs changed")
    if read_regular(paths_a["recovery.cpio.gz"]) != initramfs:
        fail("wrapper staged initramfs is not the requested input")
    if config_hash != profile["wrapper_config_sha256"]:
        fail("wrapper output config identity changed")
    image = read_regular(paths_a["wrapper.Image"])
    if image.count(initramfs) != 1:
        fail("wrapper Image does not embed the initramfs exactly once")
    validate_build_meta(
        read_regular(paths_a["wrapper.build-meta"]),
        profile,
        records["initramfs_sha256"],
        config_hash,
        image_hash,
    )
    if avb_size != profile["partition_size"]:
        fail("wrapper AVB partition size changed")

    output_records = {
        "wrapper_config_size": str(config_size),
        "wrapper_config_output_sha256": config_hash,
        "wrapper_image_size": str(image_size),
        "wrapper_image_sha256": image_hash,
        "build_meta_size": str(meta_size),
        "build_meta_sha256": meta_hash,
        "raw_image_size": str(raw_size),
        "raw_image_sha256": raw_hash,
        "avb_image_size": str(avb_size),
        "avb_image_sha256": avb_hash,
    }
    return cached, output_records


def canonical_manifest(
    records: dict[str, str], output_records: dict[str, str]
) -> bytes:
    combined = {
        "format": records["format"],
        "input_key": records["input_key"],
        "profile_sha256": records["profile_sha256"],
    }
    for key in PROFILE_KEYS[1:]:
        combined[key] = records[key]
    combined["initramfs_size"] = records["initramfs_size"]
    combined["initramfs_sha256"] = records["initramfs_sha256"]
    combined.update(output_records)
    if tuple(combined) != ENTRY_KEYS:
        fail("internal cache manifest ordering error")
    return "".join(
        f"{key}={value}\n" for key, value in combined.items()
    ).encode("ascii")


def secure_directory(path: Path, *, create: bool) -> None:
    if create:
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
    try:
        metadata = path.lstat()
    except OSError as error:
        raise CacheError(f"cannot inspect cache directory: {path}") from error
    if (
        path.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail(f"cache directory is not private and owned: {path}")


def copy_file(source: Path, destination: Path, mode: int = 0o400) -> None:
    source_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    destination_flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    source_fd = os.open(source, source_flags)
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            fail(f"copy source is not a single-link regular file: {source}")
        destination_fd = os.open(destination, destination_flags, mode)
        try:
            while chunk := os.read(source_fd, 1024 * 1024):
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_fd, view)
                    view = view[written:]
            os.fsync(destination_fd)
        finally:
            os.close(destination_fd)
        after = os.fstat(source_fd)
        if (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
        ):
            fail(f"copy source changed during publication: {source}")
    finally:
        os.close(source_fd)


def write_file(path: Path, data: bytes, mode: int = 0o400) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags, mode)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def rename_noreplace(source: Path, destination: Path) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = library.renameat2
    except AttributeError as error:
        raise CacheError("atomic no-replace rename is unavailable") from error
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100,
        os.fsencode(source),
        -100,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        number = ctypes.get_errno()
        if number == errno.EEXIST:
            raise FileExistsError(destination)
        raise CacheError("atomic no-replace publication failed") from OSError(
            number, os.strerror(number)
        )


def parse_manifest(data: bytes) -> dict[str, str]:
    manifest = parse_records(
        data,
        ENTRY_KEYS,
        "cache manifest",
        allow_empty=frozenset(("cmdline_overrides",)),
    )
    if manifest["format"] != ENTRY_FORMAT:
        fail("cache entry format changed")
    for key, value in manifest.items():
        if key.endswith("_sha256") or key in ("input_key", "profile_sha256"):
            if key == "builder_digest":
                continue
            if not is_sha256(value):
                fail(f"cache manifest has invalid SHA-256: {key}")
    for key in (
        "source_tree_entries",
        "source_tree_regular_files",
        "source_tree_directories",
        "source_tree_symlinks",
        "source_tree_bytes",
        "partition_size",
        "initramfs_size",
        "wrapper_config_size",
        "wrapper_image_size",
        "build_meta_size",
        "raw_image_size",
        "avb_image_size",
    ):
        if not manifest[key].isdigit():
            fail(f"cache manifest has invalid integer: {key}")
    return manifest


def verify_entry(
    entries: Path,
    expected_entry_id: str,
    records: dict[str, str],
) -> tuple[Path, dict[str, str]]:
    if not is_sha256(expected_entry_id):
        fail("expected cache entry ID is not SHA-256")
    entry = entries / expected_entry_id
    try:
        metadata = entry.lstat()
    except OSError as error:
        raise CacheError("expected cache entry is absent") from error
    if (
        entry.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o500
    ):
        fail("cache entry directory metadata changed")
    inventory = sorted(path.name for path in entry.iterdir())
    expected_inventory = sorted(("manifest", *CACHE_FILES))
    if inventory != expected_inventory:
        fail("cache entry inventory changed")
    manifest_data = read_regular(entry / "manifest")
    actual_entry_id = hashlib.sha256(manifest_data).hexdigest()
    if actual_entry_id != expected_entry_id:
        fail("cache entry manifest identity changed")
    manifest = parse_manifest(manifest_data)
    if manifest["input_key"] != records["input_key"]:
        fail("cache entry input key changed")
    if manifest["profile_sha256"] != records["profile_sha256"]:
        fail("cache entry profile identity changed")
    for key in PROFILE_KEYS[1:]:
        if manifest[key] != records[key]:
            fail(f"cache entry input changed: {key}")
    for key in ("initramfs_size", "initramfs_sha256"):
        if manifest[key] != records[key]:
            fail(f"cache entry input changed: {key}")
    file_fields = {
        "wrapper.config": (
            "wrapper_config_size",
            "wrapper_config_output_sha256",
        ),
        "wrapper.Image": ("wrapper_image_size", "wrapper_image_sha256"),
        "wrapper.build-meta": ("build_meta_size", "build_meta_sha256"),
        "recovery.cpio.gz": ("initramfs_size", "initramfs_sha256"),
        "stable-recovery.raw.img": ("raw_image_size", "raw_image_sha256"),
        "stable-recovery.avb.img": ("avb_image_size", "avb_image_sha256"),
    }
    for name, (size_key, hash_key) in file_fields.items():
        path = entry / name
        metadata = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
        ):
            fail(f"cache entry file metadata changed: {name}")
        size, digest = file_identity(path)
        if str(size) != manifest[size_key] or digest != manifest[hash_key]:
            fail(f"cache entry file identity changed: {name}")
    image = read_regular(entry / "wrapper.Image")
    initramfs = read_regular(entry / "recovery.cpio.gz")
    if image.count(initramfs) != 1:
        fail("cached wrapper does not embed its initramfs exactly once")
    return entry, manifest


def binding_bytes(input_key: str, entry_id: str) -> bytes:
    return (
        f"format={BINDING_FORMAT}\n"
        f"input_key={input_key}\n"
        f"entry_id={entry_id}\n"
    ).encode("ascii")


def verify_binding(inputs: Path, input_key: str, entry_id: str) -> None:
    if not is_sha256(input_key) or not is_sha256(entry_id):
        fail("cache binding identity is malformed")
    path = inputs / input_key
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o400
    ):
        fail("cache input binding metadata changed")
    fields = parse_records(read_regular(path), BINDING_KEYS, "cache input binding")
    if fields != {
        "format": BINDING_FORMAT,
        "input_key": input_key,
        "entry_id": entry_id,
    }:
        fail("cache input binding changed")


def publish_binding(inputs: Path, input_key: str, entry_id: str) -> bool:
    stage = inputs / f".binding-{os.getpid()}-{entry_id[:16]}"
    if stage.exists() or stage.is_symlink():
        fail("cache binding staging path already exists")
    write_file(stage, binding_bytes(input_key, entry_id))
    try:
        try:
            rename_noreplace(stage, inputs / input_key)
            fsync_directory(inputs)
            return True
        except FileExistsError:
            verify_binding(inputs, input_key, entry_id)
            return False
    finally:
        if stage.exists():
            stage.unlink()


def publish(values: argparse.Namespace) -> None:
    profile, profile_sha256 = load_profile(Path(values.profile))
    records, initramfs = validate_inputs(values, profile, profile_sha256)
    if values.source_seal_after is None:
        fail("publish requires a post-build source seal")
    after = read_source_seal(values.source_seal_after)
    validate_source_seal(profile, after)
    if after != read_source_seal(values.source_seal):
        fail("ASUS source tree changed across the twin build")
    cached, output_records = collect_outputs(
        values, profile, records, initramfs
    )
    manifest = canonical_manifest(records, output_records)
    entry_id = hashlib.sha256(manifest).hexdigest()

    cache_root = Path(values.cache_root).absolute()
    secure_directory(cache_root, create=True)
    entries = cache_root / "entries"
    secure_directory(entries, create=True)
    inputs = cache_root / "inputs"
    secure_directory(inputs, create=True)
    stage = Path(tempfile.mkdtemp(prefix=".entry-", dir=entries))
    published = False
    bound = False
    final = entries / entry_id
    try:
        for name in CACHE_FILES:
            copy_file(cached[name], stage / name)
        write_file(stage / "manifest", manifest)
        fsync_directory(stage)
        os.chmod(stage, 0o500)
        try:
            rename_noreplace(stage, final)
            published = True
            fsync_directory(entries)
        except FileExistsError:
            os.chmod(stage, 0o700)
            shutil.rmtree(stage)
        verify_entry(entries, entry_id, records)
        try:
            bound = publish_binding(
                inputs, records["input_key"], entry_id
            )
        except CacheError:
            if published and final.exists() and not final.is_symlink():
                os.chmod(final, 0o700)
                shutil.rmtree(final)
                fsync_directory(entries)
            raise
    finally:
        if stage.exists():
            os.chmod(stage, 0o700)
            shutil.rmtree(stage)
    print(f"cache_input_key={records['input_key']}")
    print(f"cache_entry_id={entry_id}")
    print(f"cache_publication={'new' if published else 'existing'}")
    print(f"cache_binding={'new' if bound else 'existing'}")
    print("PASS verified stable-recovery wrapper cache entry")


def materialize(values: argparse.Namespace) -> None:
    profile, profile_sha256 = load_profile(Path(values.profile))
    records, _ = validate_inputs(values, profile, profile_sha256)
    cache_root = Path(values.cache_root).absolute()
    secure_directory(cache_root, create=False)
    entries = cache_root / "entries"
    secure_directory(entries, create=False)
    inputs = cache_root / "inputs"
    secure_directory(inputs, create=False)
    verify_binding(inputs, records["input_key"], values.expected_entry_id)
    entry, _ = verify_entry(entries, values.expected_entry_id, records)

    output = Path(values.output_root).absolute()
    parent = output.parent
    try:
        parent_metadata = parent.lstat()
    except OSError as error:
        raise CacheError("materialization parent is absent") from error
    if parent.is_symlink() or not stat.S_ISDIR(parent_metadata.st_mode):
        fail("materialization parent is not a real directory")
    if output.exists() or output.is_symlink():
        fail("refusing an existing materialization output")
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=parent))
    try:
        for name in ("manifest", *CACHE_FILES):
            copy_file(entry / name, stage / name)
        fsync_directory(stage)
        os.chmod(stage, 0o500)
        rename_noreplace(stage, output)
        fsync_directory(parent)
        verify_materialized(output, values.expected_entry_id, records)
    finally:
        if stage.exists():
            os.chmod(stage, 0o700)
            shutil.rmtree(stage)
    print(f"cache_input_key={records['input_key']}")
    print(f"cache_entry_id={values.expected_entry_id}")
    print(f"materialized={output}")
    print("PASS materialized exact stable-recovery wrapper cache entry")


def print_input_key(values: argparse.Namespace) -> None:
    profile, profile_sha256 = load_profile(Path(values.profile))
    records, _ = validate_inputs(values, profile, profile_sha256)
    print(f"cache_input_key={records['input_key']}")
    print("PASS stable-recovery wrapper cache inputs")


def verify_materialized(
    output: Path,
    expected_entry_id: str,
    records: dict[str, str],
) -> None:
    metadata = output.lstat()
    if (
        output.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o500
    ):
        fail("materialized directory metadata changed")
    inventory = sorted(path.name for path in output.iterdir())
    if inventory != sorted(("manifest", *CACHE_FILES)):
        fail("materialized cache inventory changed")
    manifest_data = read_regular(output / "manifest")
    if hashlib.sha256(manifest_data).hexdigest() != expected_entry_id:
        fail("materialized manifest identity changed")
    manifest = parse_manifest(manifest_data)
    if manifest["input_key"] != records["input_key"]:
        fail("materialized input key changed")
    for name, size_key, hash_key in (
        (
            "wrapper.config",
            "wrapper_config_size",
            "wrapper_config_output_sha256",
        ),
        ("wrapper.Image", "wrapper_image_size", "wrapper_image_sha256"),
        ("wrapper.build-meta", "build_meta_size", "build_meta_sha256"),
        ("recovery.cpio.gz", "initramfs_size", "initramfs_sha256"),
        ("stable-recovery.raw.img", "raw_image_size", "raw_image_sha256"),
        ("stable-recovery.avb.img", "avb_image_size", "avb_image_sha256"),
    ):
        path = output / name
        size, digest = file_identity(path)
        if str(size) != manifest[size_key] or digest != manifest[hash_key]:
            fail(f"materialized cache file changed: {name}")


def add_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", required=True)
    parser.add_argument("--source-seal", required=True)
    parser.add_argument("--source-tree-tool", required=True)
    parser.add_argument("--reference-config", required=True)
    parser.add_argument("--initramfs", required=True)
    parser.add_argument("--build-script", required=True)
    parser.add_argument("--repack-script", required=True)
    parser.add_argument("--boot-template", required=True)
    parser.add_argument("--mkbootimg", required=True)
    parser.add_argument("--unpack-bootimg", required=True)
    parser.add_argument("--avbtool", required=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)
    input_parser = subparsers.add_parser("input-key")
    add_inputs(input_parser)
    publish_parser = subparsers.add_parser("publish")
    add_inputs(publish_parser)
    publish_parser.add_argument("--cache-root", required=True)
    publish_parser.add_argument("--source-seal-after", required=True)
    publish_parser.add_argument("--build-a", required=True)
    publish_parser.add_argument("--build-b", required=True)
    publish_parser.add_argument("--raw-a", required=True)
    publish_parser.add_argument("--raw-b", required=True)
    publish_parser.add_argument("--avb-a", required=True)
    publish_parser.add_argument("--avb-b", required=True)
    materialize_parser = subparsers.add_parser("materialize")
    add_inputs(materialize_parser)
    materialize_parser.add_argument("--cache-root", required=True)
    materialize_parser.add_argument("--expected-entry-id", required=True)
    materialize_parser.add_argument("--output-root", required=True)
    return result


def main() -> int:
    values = parser().parse_args()
    if values.command == "publish":
        publish(values)
    elif values.command == "materialize":
        materialize(values)
    else:
        print_input_key(values)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CacheError, OSError) as error:
        print(f"FAIL {error}", file=os.sys.stderr)
        raise SystemExit(1)
