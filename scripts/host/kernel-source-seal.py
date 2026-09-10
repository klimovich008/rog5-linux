#!/usr/bin/env python3
"""Create a host-metadata-independent seal for a kernel source tree."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn


TREE_FORMAT = "rog5-kernel-source-tree-v1"


class SourceSealError(RuntimeError):
    """The kernel source tree cannot be sealed safely."""


def fail(message: str) -> NoReturn:
    raise SourceSealError(message)


def put_field(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def file_digest(path: bytes, expected: os.stat_result) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != (
            expected.st_dev,
            expected.st_ino,
            expected.st_mode,
            expected.st_size,
            expected.st_mtime_ns,
            expected.st_ctime_ns,
        ):
            fail("kernel source file changed while opening")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ):
            fail("kernel source file changed while hashing")
        return digest.digest()
    finally:
        os.close(descriptor)


def seal_tree(path: Path) -> dict[str, str]:
    try:
        root_metadata = path.lstat()
    except OSError as error:
        raise SourceSealError("cannot inspect kernel source root") from error
    if path.is_symlink() or not stat.S_ISDIR(root_metadata.st_mode):
        fail("kernel source root is not a real directory")

    root = os.fsencode(os.path.abspath(path))
    root_device = root_metadata.st_dev
    digest = hashlib.sha256()
    digest.update(TREE_FORMAT.encode("ascii") + b"\0")
    counters = {
        "tree_entries": 0,
        "tree_regular_files": 0,
        "tree_directories": 0,
        "tree_symlinks": 0,
        "tree_bytes": 0,
    }

    def visit(entry_path: bytes, relative: bytes) -> None:
        metadata = os.lstat(entry_path)
        if metadata.st_dev != root_device:
            fail(
                "kernel source crosses a filesystem boundary: "
                f"{os.fsdecode(relative)}"
            )
        counters["tree_entries"] += 1
        put_field(digest, relative)
        put_field(digest, str(stat.S_IMODE(metadata.st_mode)).encode("ascii"))

        if stat.S_ISREG(metadata.st_mode):
            counters["tree_regular_files"] += 1
            counters["tree_bytes"] += metadata.st_size
            put_field(digest, b"file")
            put_field(digest, str(metadata.st_size).encode("ascii"))
            put_field(digest, file_digest(entry_path, metadata))
            return
        if stat.S_ISLNK(metadata.st_mode):
            counters["tree_symlinks"] += 1
            put_field(digest, b"symlink")
            put_field(digest, os.fsencode(os.readlink(entry_path)))
            after = os.lstat(entry_path)
            if (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) != (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_mode,
                metadata.st_size,
                metadata.st_mtime_ns,
                metadata.st_ctime_ns,
            ):
                fail("kernel source symlink changed while sealing")
            return
        if not stat.S_ISDIR(metadata.st_mode):
            fail(
                "kernel source contains an unsupported entry: "
                f"{os.fsdecode(relative)}"
            )

        counters["tree_directories"] += 1
        put_field(digest, b"directory")
        before = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        with os.scandir(entry_path) as entries:
            children = sorted(entries, key=lambda entry: os.fsencode(entry.name))
        for child in children:
            name = os.fsencode(child.name)
            child_relative = name if relative == b"." else relative + b"/" + name
            visit(os.path.join(entry_path, name), child_relative)
        after = os.lstat(entry_path)
        if (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) != before:
            fail("kernel source directory changed while sealing")

    visit(root, b".")
    return {
        "tree_format": TREE_FORMAT,
        **{key: str(value) for key, value in counters.items()},
        "tree_sha256": digest.hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    values = parser.parse_args()
    for key, value in seal_tree(values.source).items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SourceSealError) as error:
        print(f"FAIL {error}", file=os.sys.stderr)
        raise SystemExit(1)
