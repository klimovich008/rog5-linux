#!/usr/bin/env python3
"""Create one atomic, signed ROG5 stable-recovery runtime bundle."""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys


BUNDLE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9_+.-]+\Z")
PROFILES = {
    "diagnostic-initramfs-v1",
    "network-root-v1",
    "persistent-root-ro-v1",
}
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
ARTIFACTS = (
    ("Image", 64, 128 * 1024 * 1024),
    ("board.dtb", 40, 2 * 1024 * 1024),
    ("initramfs.cpio.gz", 2, 256 * 1024 * 1024),
)
FINAL_INVENTORY = {
    "manifest",
    "manifest.sig",
    *(name for name, _minimum, _maximum in ARTIFACTS),
}
RENAME_NOREPLACE = 1


class BundleError(RuntimeError):
    """A stable, non-sensitive packager refusal."""


@dataclass(frozen=True)
class Configuration:
    bundle: str
    profile: str
    image: Path
    dtb: Path
    initramfs: Path
    target_id: str
    target_release: str
    rollback_timeout: str
    target_timeout: str
    private_key: Path
    bundle_root: Path


def valid_bundle(value: str) -> bool:
    return (
        bool(BUNDLE_ID.fullmatch(value))
        and ".." not in value
        and value != "none"
    )


def valid_identity(value: str, maximum: int) -> bool:
    return (
        len(value) <= maximum
        and value.isascii()
        and bool(IDENTITY.fullmatch(value))
        and not value.startswith(".")
        and ".." not in value
    )


def parse_decimal(value: str, minimum: int, maximum: int) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdecimal()
        or (value.startswith("0") and value != "0")
    ):
        raise BundleError("timeout is not a canonical decimal")
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise BundleError("timeout is outside policy")
    return parsed


def open_regular(path: Path, label: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BundleError(f"cannot open {label}") from error
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        raise BundleError(f"{label} is not a regular file")
    return descriptor


def validate_private_key(descriptor: int, openssl: str) -> bytes:
    metadata = os.fstat(descriptor)
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
        or metadata.st_nlink != 1
        or metadata.st_size < 1
        or metadata.st_size > 64 * 1024
    ):
        raise BundleError("private key metadata is unsafe")
    os.lseek(descriptor, 0, os.SEEK_SET)
    unencrypted = subprocess.run(
        [
            openssl,
            "pkcs8",
            "-in",
            f"/proc/self/fd/{descriptor}",
            "-nocrypt",
            "-outform",
            "DER",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        pass_fds=(descriptor,),
        check=False,
    )
    if unencrypted.returncode != 0:
        raise BundleError(
            "private key is not unencrypted PKCS#8"
        )
    os.lseek(descriptor, 0, os.SEEK_SET)
    result = subprocess.run(
        [
            openssl,
            "pkey",
            "-in",
            f"/proc/self/fd/{descriptor}",
            "-pubout",
            "-outform",
            "DER",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        pass_fds=(descriptor,),
        check=False,
    )
    if (
        result.returncode != 0
        or len(result.stdout) != len(SPKI_PREFIX) + 32
        or not result.stdout.startswith(SPKI_PREFIX)
    ):
        raise BundleError("private key is not Ed25519")
    return result.stdout[len(SPKI_PREFIX) :]


def open_bundle_root(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BundleError("cannot open bundle root") from error
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        os.close(descriptor)
        raise BundleError("bundle root metadata is unsafe")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        os.close(descriptor)
        raise BundleError("bundle root is busy") from error
    if directory_inventory(descriptor):
        os.close(descriptor)
        raise BundleError("bundle root is not empty")
    return descriptor


def directory_inventory(descriptor: int) -> list[str]:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    snapshot = os.open(".", flags, dir_fd=descriptor)
    try:
        return os.listdir(snapshot)
    finally:
        os.close(snapshot)


def source_snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise BundleError("bundle artifact write made no progress")
        offset += written


def copy_artifact(
    source: int,
    directory: int,
    name: str,
    minimum: int,
    maximum: int,
    created: list[str],
) -> tuple[int, str]:
    before = os.fstat(source)
    if before.st_size < minimum or before.st_size > maximum:
        raise BundleError(f"{name} size is outside policy")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    destination = os.open(name, flags, 0o400, dir_fd=directory)
    created.append(name)
    observed = 0
    try:
        while True:
            block = os.read(source, 1024 * 1024)
            if not block:
                break
            observed += len(block)
            if observed > maximum:
                raise BundleError(f"{name} changed beyond size policy")
            write_all(destination, block)
        os.fchmod(destination, 0o400)
        os.fsync(destination)
        output = os.fstat(destination)
        after = os.fstat(source)
        if (
            source_snapshot(before) != source_snapshot(after)
            or observed != before.st_size
        ):
            raise BundleError(f"{name} changed while being copied")
        if (
            output.st_uid != os.geteuid()
            or stat.S_IMODE(output.st_mode) != 0o400
            or output.st_nlink != 1
            or output.st_size != observed
        ):
            raise BundleError(f"{name} output metadata is unsafe")
        os.lseek(destination, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        hashed = 0
        while True:
            block = os.read(destination, 1024 * 1024)
            if not block:
                break
            hashed += len(block)
            digest.update(block)
        if hashed != observed:
            raise BundleError(f"{name} staged snapshot changed")
    finally:
        os.close(destination)
    return observed, digest.hexdigest()


def create_file(
    directory: int,
    name: str,
    payload: bytes,
    created: list[str],
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o400, dir_fd=directory)
    created.append(name)
    try:
        write_all(descriptor, payload)
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            raise BundleError(f"{name} output metadata is unsafe")
    finally:
        os.close(descriptor)


def sign_manifest(
    manifest: bytes, private_key: int, openssl: str
) -> bytes:
    try:
        message = os.memfd_create(
            "rog5-recovery-manifest",
            flags=os.MFD_CLOEXEC,
        )
    except (AttributeError, OSError) as error:
        raise BundleError("cannot create private signing input") from error
    try:
        write_all(message, manifest)
        os.lseek(message, 0, os.SEEK_SET)
        os.lseek(private_key, 0, os.SEEK_SET)
        result = subprocess.run(
            [
                openssl,
                "pkeyutl",
                "-sign",
                "-rawin",
                "-inkey",
                f"/proc/self/fd/{private_key}",
                "-in",
                f"/proc/self/fd/{message}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            pass_fds=(private_key, message),
            check=False,
        )
    finally:
        os.close(message)
    if result.returncode != 0 or len(result.stdout) != 64:
        raise BundleError("Ed25519 manifest signing failed")
    return result.stdout


def create_staging_directory(root: int, bundle: str) -> tuple[str, int]:
    for _attempt in range(32):
        name = f".{bundle}.staging-{secrets.token_hex(8)}"
        try:
            os.mkdir(name, 0o700, dir_fd=root)
        except FileExistsError:
            continue
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(name, flags, dir_fd=root)
        except OSError as error:
            try:
                os.rmdir(name, dir_fd=root)
            except OSError as cleanup_error:
                raise BundleError(
                    "cannot clean failed staging directory"
                ) from cleanup_error
            raise BundleError(
                "cannot open private staging directory"
            ) from error
        return name, descriptor
    raise BundleError("cannot allocate a private staging directory")


def rename_noreplace(
    root: int,
    source: str,
    destination: str,
) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = library.renameat2
    except AttributeError as error:
        raise BundleError("atomic no-replace rename is unavailable") from error
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        root,
        os.fsencode(source),
        root,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise BundleError("atomic no-replace publication failed") from OSError(
            error_number,
            os.strerror(error_number),
        )


def cleanup_staging(
    root: int,
    staging_name: str,
    staging: int,
    created: list[str],
) -> None:
    try:
        os.fchmod(staging, 0o700)
    except OSError:
        pass
    for name in reversed(created):
        try:
            os.unlink(name, dir_fd=staging)
        except FileNotFoundError:
            pass
    try:
        os.rmdir(staging_name, dir_fd=root)
    except FileNotFoundError:
        pass


def manifest_bytes(
    config: Configuration,
    observed: dict[str, tuple[int, str]],
) -> bytes:
    fields = (
        ("format", "rog5-recovery-bundle-v1"),
        ("bundle", config.bundle),
        ("profile", config.profile),
        ("kernel_size", str(observed["Image"][0])),
        ("kernel_sha256", observed["Image"][1]),
        ("dtb_size", str(observed["board.dtb"][0])),
        ("dtb_sha256", observed["board.dtb"][1]),
        (
            "initramfs_size",
            str(observed["initramfs.cpio.gz"][0]),
        ),
        ("initramfs_sha256", observed["initramfs.cpio.gz"][1]),
        ("target_id", config.target_id),
        ("target_release", config.target_release),
        ("rollback_timeout", config.rollback_timeout),
        ("target_timeout", config.target_timeout),
    )
    payload = "".join(f"{name}={value}\n" for name, value in fields).encode(
        "ascii"
    )
    if len(payload) > 4096:
        raise BundleError("manifest exceeds size policy")
    return payload


def validate_configuration(config: Configuration) -> None:
    if not valid_bundle(config.bundle):
        raise BundleError("bundle identifier is invalid")
    if config.profile not in PROFILES:
        raise BundleError("bundle profile is invalid")
    if not valid_identity(config.target_id, 64):
        raise BundleError("target identifier is invalid")
    if not valid_identity(config.target_release, 96):
        raise BundleError("target release is invalid")
    rollback = parse_decimal(config.rollback_timeout, 60, 900)
    target = parse_decimal(config.target_timeout, 30, 600)
    if target > rollback - 30:
        raise BundleError("timeout rollback margin is unsafe")
    if config.profile == "persistent-root-ro-v1" and rollback < 300:
        raise BundleError("persistent profile rollback is too short")


def prepare_bundle(
    config: Configuration,
    *,
    signer=sign_manifest,
) -> tuple[str, str]:
    validate_configuration(config)
    openssl = shutil.which("openssl")
    if openssl is None:
        raise BundleError("openssl is unavailable")

    private_key = open_regular(config.private_key, "private key")
    sources: list[int] = []
    root = -1
    staging = -1
    staging_name: str | None = None
    created: list[str] = []
    try:
        key_snapshot = source_snapshot(os.fstat(private_key))
        public_key = validate_private_key(private_key, openssl)
        private_key_metadata = os.fstat(private_key)
        private_key_identity = (
            private_key_metadata.st_dev,
            private_key_metadata.st_ino,
        )
        paths = (config.image, config.dtb, config.initramfs)
        for (name, _minimum, _maximum), path in zip(
            ARTIFACTS, paths, strict=True
        ):
            source = open_regular(path, name)
            metadata = os.fstat(source)
            if (
                metadata.st_dev,
                metadata.st_ino,
            ) == private_key_identity:
                os.close(source)
                raise BundleError(
                    "bundle artifact aliases the private key"
                )
            sources.append(source)
        root = open_bundle_root(config.bundle_root)
        staging_name, staging = create_staging_directory(
            root, config.bundle
        )
        observed: dict[str, tuple[int, str]] = {}
        for source, (name, minimum, maximum) in zip(
            sources, ARTIFACTS, strict=True
        ):
            observed[name] = copy_artifact(
                source,
                staging,
                name,
                minimum,
                maximum,
                created,
            )
        manifest = manifest_bytes(config, observed)
        create_file(staging, "manifest", manifest, created)
        signature = signer(manifest, private_key, openssl)
        if source_snapshot(os.fstat(private_key)) != key_snapshot:
            raise BundleError("private key changed while signing")
        if len(signature) != 64:
            raise BundleError("Ed25519 manifest signature has wrong size")
        create_file(staging, "manifest.sig", signature, created)
        if set(directory_inventory(staging)) != FINAL_INVENTORY:
            raise BundleError("staging inventory is incomplete")
        os.fsync(staging)
        os.fchmod(staging, 0o500)
        rename_noreplace(root, staging_name, config.bundle)
        staging_name = None
        os.fsync(root)
        return (
            hashlib.sha256(manifest).hexdigest(),
            hashlib.sha256(public_key).hexdigest(),
        )
    finally:
        if staging_name is not None and root >= 0 and staging >= 0:
            cleanup_staging(root, staging_name, staging, created)
        if staging >= 0:
            os.close(staging)
        if root >= 0:
            os.close(root)
        for descriptor in sources:
            os.close(descriptor)
        os.close(private_key)


def parse_arguments(arguments: list[str]) -> Configuration:
    parser = argparse.ArgumentParser(
        description=__doc__,
        allow_abbrev=False,
    )
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--dtb", required=True, type=Path)
    parser.add_argument("--initramfs", required=True, type=Path)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--target-release", required=True)
    parser.add_argument("--rollback-timeout", required=True)
    parser.add_argument("--target-timeout", required=True)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--bundle-root", required=True, type=Path)
    values = parser.parse_args(arguments)
    return Configuration(**vars(values))


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    try:
        config = parse_arguments(
            sys.argv[1:] if arguments is None else arguments
        )
        manifest_hash, trust_key_hash = prepare_bundle(config)
    except BundleError as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    except OSError:
        print("FAIL host filesystem operation failed", file=sys.stderr)
        return 1
    print("format=rog5-prepared-bundle-v1")
    print(f"bundle={config.bundle}")
    print(f"profile={config.profile}")
    print(f"manifest_sha256={manifest_hash}")
    print(f"trust_key_sha256={trust_key_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
