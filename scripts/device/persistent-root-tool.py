#!/usr/bin/env python3
"""Validate and seal a persistent ROG Phone 5 root tree."""

from __future__ import annotations

import argparse
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile
from typing import NoReturn


SEAL_NAME = ".rog5-persistent-seal"
TREE_KEYS = (
    "tree_format",
    "tree_entries",
    "tree_regular_files",
    "tree_directories",
    "tree_symlinks",
    "tree_bytes",
    "tree_xattrs",
    "tree_sha256",
)
SEAL_KEYS = (
    "seal_format",
    "generation",
    "source_archive_size",
    "source_archive_sha256",
    "promotion_state",
    *TREE_KEYS,
)


class ContractError(Exception):
    """A persistent-root contract was not met."""


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def clean_archive_path(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    if name in ("", "."):
        return "."
    if "\0" in name or name.startswith("/"):
        fail(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if any(part in ("", ".", "..") for part in path.parts):
        fail(f"unsafe archive path: {name!r}")
    return path.as_posix()


def has_embedded_credential(path: str) -> bool:
    return (
        path.startswith("etc/ssh/ssh_host_")
        or path == "etc/wireguard/wg0.conf"
        or path.startswith("etc/NetworkManager/system-connections/")
        or path == "home/rog5/.config/krdpserverrc"
        or path.startswith("home/rog5/.local/share/kwalletd/")
        or path.startswith("var/lib/rog5-agent/private/")
    )


def inspect_archive(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        fail("archive is not a regular, non-linked file")

    counts = {
        "archive_entries": 0,
        "archive_regular_files": 0,
        "archive_directories": 0,
        "archive_symlinks": 0,
        "archive_hardlinks": 0,
    }
    names: set[str] = set()
    try:
        with tarfile.open(path, mode="r:*") as archive:
            for member in archive:
                name = clean_archive_path(member.name)
                if name in names:
                    fail(f"duplicate archive path: {name}")
                names.add(name)
                if name == SEAL_NAME:
                    fail("archive contains the reserved persistent seal path")
                if has_embedded_credential(name):
                    fail(f"archive embeds a deployment credential: {name}")
                if member.sparse:
                    fail(f"sparse archive member is unsupported: {name}")

                counts["archive_entries"] += 1
                if member.isfile():
                    counts["archive_regular_files"] += 1
                elif member.isdir():
                    counts["archive_directories"] += 1
                elif member.issym():
                    counts["archive_symlinks"] += 1
                    if not member.linkname:
                        fail(f"empty symbolic-link target: {name}")
                    if not member.linkname.startswith("/"):
                        resolved = PurePosixPath(name).parent.joinpath(
                            member.linkname
                        )
                        if ".." in resolved.parts:
                            normalized = os.path.normpath(str(resolved))
                            if normalized == ".." or normalized.startswith("../"):
                                fail(f"symbolic link escapes the root: {name}")
                elif member.islnk():
                    counts["archive_hardlinks"] += 1
                    target = clean_archive_path(member.linkname)
                    if target == ".":
                        fail(f"invalid hard-link target: {name}")
                elif member.isdev():
                    fail(f"archive contains a device or FIFO: {name}")
                else:
                    fail(f"archive contains an unsupported entry: {name}")
    except (OSError, tarfile.TarError) as error:
        fail(f"cannot inspect archive: {error}")

    if counts["archive_entries"] == 0:
        fail("archive is empty")
    return {key: str(value) for key, value in counts.items()}


def put_field(digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def file_digest(path: bytes, expected: os.stat_result) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        actual = os.fstat(descriptor)
        if (actual.st_dev, actual.st_ino, actual.st_mode, actual.st_size) != (
            expected.st_dev,
            expected.st_ino,
            expected.st_mode,
            expected.st_size,
        ):
            fail("tree entry changed while it was being sealed")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return digest.digest()
    finally:
        os.close(descriptor)


def entry_xattrs(path: bytes) -> list[tuple[bytes, bytes]]:
    try:
        names = os.listxattr(path, follow_symlinks=False)
    except OSError as error:
        if error.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):
            fail("the staging filesystem does not support xattrs")
        raise
    result: list[tuple[bytes, bytes]] = []
    for name in names:
        encoded = os.fsencode(name)
        value = os.getxattr(path, name, follow_symlinks=False)
        result.append((encoded, value))
    return sorted(result)


def walk_tree(root: bytes) -> list[tuple[bytes, bytes, os.stat_result]]:
    result: list[tuple[bytes, bytes, os.stat_result]] = []

    def visit(path: bytes, relative: bytes) -> None:
        metadata = os.lstat(path)
        result.append((relative, path, metadata))
        if not stat.S_ISDIR(metadata.st_mode):
            return
        with os.scandir(path) as entries:
            children = sorted(entries, key=lambda entry: os.fsencode(entry.name))
        for entry in children:
            name = os.fsencode(entry.name)
            child_relative = name if relative == b"." else relative + b"/" + name
            if child_relative == os.fsencode(SEAL_NAME):
                continue
            visit(os.path.join(path, name), child_relative)

    visit(root, b".")
    return result


def seal_tree(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_dir():
        fail("tree root is not a real directory")
    root = os.fsencode(os.path.abspath(path))
    root_metadata = os.lstat(root)
    root_device = root_metadata.st_dev
    digest = hashlib.sha256()
    digest.update(b"rog5-persistent-tree-v1\0")
    counters = {
        "tree_entries": 0,
        "tree_regular_files": 0,
        "tree_directories": 0,
        "tree_symlinks": 0,
        "tree_bytes": 0,
        "tree_xattrs": 0,
    }

    for relative, entry_path, metadata in walk_tree(root):
        if metadata.st_dev != root_device:
            fail(f"tree crosses a filesystem boundary: {os.fsdecode(relative)}")
        if stat.S_ISREG(metadata.st_mode):
            kind = b"file"
            counters["tree_regular_files"] += 1
            counters["tree_bytes"] += metadata.st_size
            content_hash = file_digest(entry_path, metadata)
            link_target = b""
        elif stat.S_ISDIR(metadata.st_mode):
            kind = b"directory"
            counters["tree_directories"] += 1
            content_hash = b""
            link_target = b""
        elif stat.S_ISLNK(metadata.st_mode):
            kind = b"symlink"
            counters["tree_symlinks"] += 1
            content_hash = b""
            link_target = os.fsencode(os.readlink(entry_path))
        else:
            fail(f"tree contains an unsupported entry: {os.fsdecode(relative)}")

        xattrs = entry_xattrs(entry_path)
        counters["tree_xattrs"] += len(xattrs)
        counters["tree_entries"] += 1
        put_field(digest, relative)
        put_field(digest, kind)
        for number in (
            stat.S_IMODE(metadata.st_mode),
            metadata.st_uid,
            metadata.st_gid,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_nlink,
        ):
            put_field(digest, str(number).encode("ascii"))
        put_field(digest, content_hash)
        put_field(digest, link_target)
        put_field(digest, str(len(xattrs)).encode("ascii"))
        for name, value in xattrs:
            put_field(digest, name)
            put_field(digest, value)

    return {
        "tree_format": "rog5-persistent-tree-v1",
        **{key: str(value) for key, value in counters.items()},
        "tree_sha256": digest.hexdigest(),
    }


def print_fields(fields: dict[str, str]) -> None:
    for key, value in fields.items():
        print(f"{key}={value}")


def read_seal(path: Path) -> dict[str, str]:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        fail("seal is not a regular, non-linked file")
    if stat.S_IMODE(metadata.st_mode) != 0o444:
        fail("seal mode changed")
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        fail(f"cannot read seal: {error}")
    for line in lines:
        if "=" not in line:
            fail("seal contains a malformed record")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            fail("seal contains an empty or duplicate record")
        fields[key] = value
    if tuple(fields) != SEAL_KEYS:
        fail("seal fields or ordering changed")
    if fields["seal_format"] != "rog5-persistent-root-v1":
        fail("seal format changed")
    if fields["generation"] != "arch-a":
        fail("seal generation changed")
    if fields["promotion_state"] != "UNBOOTED":
        fail("staged root is not explicitly unbooted")
    if (
        not fields["source_archive_size"].isdigit()
        or int(fields["source_archive_size"]) == 0
        or len(fields["source_archive_sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in fields["source_archive_sha256"]
        )
    ):
        fail("seal archive identity is malformed")
    return fields


def verify_tree(root: Path, seal: Path) -> None:
    expected = read_seal(seal)
    actual = seal_tree(root)
    for key in TREE_KEYS:
        if actual[key] != expected[key]:
            fail(f"sealed tree changed: {key}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)
    archive = subparsers.add_parser("archive")
    archive.add_argument("path", type=Path)
    seal = subparsers.add_parser("seal")
    seal.add_argument("root", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("root", type=Path)
    verify.add_argument("seal", type=Path)
    return result


def main() -> int:
    arguments = parser().parse_args()
    if arguments.command == "archive":
        print_fields(inspect_archive(arguments.path))
    elif arguments.command == "seal":
        print_fields(seal_tree(arguments.root))
    else:
        verify_tree(arguments.root, arguments.seal)
        print("PASS persistent root tree matches its complete seal")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
