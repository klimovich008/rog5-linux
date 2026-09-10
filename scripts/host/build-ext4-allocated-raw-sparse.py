#!/usr/bin/env python3
"""Build Android sparse data with RAW ext4 allocations and skipped free blocks."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import tempfile


BLOCK_SIZE = 4096
SPARSE_MAGIC = 0xED26FF3A
RAW_CHUNK = 0xCAC1
DONT_CARE_CHUNK = 0xCAC3
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SparseBuildError(RuntimeError):
    """The exact ext4 allocation map cannot be represented safely."""


def fail(message: str) -> None:
    raise SparseBuildError(message)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def parse_header(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("Group "):
            break
        if ":" in line:
            name, value = line.split(":", 1)
            values[name.strip()] = value.strip()
    return values


def parse_free_ranges(output: str, block_count: int, expected_free: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    in_group = False
    for line in output.splitlines():
        if line.startswith("Group "):
            in_group = True
            continue
        if not in_group or not line.startswith("  Free blocks:"):
            continue
        for token in line.split(":", 1)[1].strip().split(", "):
            if not token:
                continue
            fields = token.split("-", 1)
            try:
                first = int(fields[0])
                last = int(fields[-1])
            except ValueError as error:
                raise SparseBuildError("dumpe2fs free-block range is invalid") from error
            if first < 0 or last < first or last >= block_count:
                fail("dumpe2fs free-block range escaped the filesystem")
            ranges.append((first, last + 1))
    ranges.sort()
    merged: list[tuple[int, int]] = []
    for first, end in ranges:
        if merged and first < merged[-1][1]:
            fail("dumpe2fs free-block ranges overlap")
        if merged and first == merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((first, end))
    if sum(end - first for first, end in merged) != expected_free:
        fail("dumpe2fs free-block count disagrees with its ranges")
    return merged


def allocation_chunks(
    free_ranges: list[tuple[int, int]], block_count: int
) -> list[tuple[int, int, int]]:
    chunks: list[tuple[int, int, int]] = []
    cursor = 0
    for first, end in free_ranges:
        if cursor < first:
            chunks.append((RAW_CHUNK, cursor, first - cursor))
        chunks.append((DONT_CARE_CHUNK, first, end - first))
        cursor = end
    if cursor < block_count:
        chunks.append((RAW_CHUNK, cursor, block_count - cursor))
    if not chunks or sum(count for _kind, _first, count in chunks) != block_count:
        fail("allocation chunks do not cover the filesystem exactly")
    return chunks


def copy_blocks(source, target, count: int) -> None:
    remaining = count * BLOCK_SIZE
    while remaining:
        block = source.read(min(remaining, 8 * 1024 * 1024))
        if not block:
            fail("source image truncated during RAW chunk copy")
        target.write(block)
        remaining -= len(block)


def build_sparse(source_path: Path, output_path: Path, chunks: list[tuple[int, int, int]]) -> None:
    parent = output_path.parent.resolve(strict=True)
    if output_path.parent != parent or output_path.exists() or output_path.is_symlink():
        fail("output path is not one new canonical file")
    parent_metadata = parent.stat()
    if (
        parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        fail("output parent must be caller-owned mode 0700")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".rog5-ext4-sparse.", dir=parent)
    published = False
    try:
        with os.fdopen(descriptor, "wb", buffering=0) as target, source_path.open(
            "rb", buffering=0
        ) as source:
            target.write(
                struct.pack(
                    "<IHHHHIIII",
                    SPARSE_MAGIC,
                    1,
                    0,
                    28,
                    12,
                    BLOCK_SIZE,
                    source_path.stat().st_size // BLOCK_SIZE,
                    len(chunks),
                    0,
                )
            )
            for kind, first, count in chunks:
                if kind == RAW_CHUNK:
                    target.write(struct.pack("<HHII", kind, 0, count, 12 + count * BLOCK_SIZE))
                    source.seek(first * BLOCK_SIZE)
                    copy_blocks(source, target, count)
                else:
                    target.write(struct.pack("<HHII", kind, 0, count, 12))
            target.flush()
            os.fsync(target.fileno())
            os.fchmod(target.fileno(), 0o400)
        os.link(temporary_name, output_path, follow_symlinks=False)
        published = True
        os.unlink(temporary_name)
        temporary_name = ""
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary_name:
            os.unlink(temporary_name)
        if published and not output_path.exists():
            fail("sparse output publication disappeared")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-blocks", required=True, type=int)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--expected-label", required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    values = parser.parse_args()
    if os.geteuid() == 0:
        fail("run as the desktop user")
    source = values.source.resolve(strict=True)
    metadata = source.stat()
    if (
        values.source != source
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_nlink != 1
        or metadata.st_size != values.expected_blocks * BLOCK_SIZE
        or not SHA256.fullmatch(values.expected_source_sha256)
    ):
        fail("source image metadata or expected identity is invalid")
    if file_sha256(source) != values.expected_source_sha256:
        fail("source image SHA-256 changed")
    result = subprocess.run(
        ["/usr/bin/dumpe2fs", str(source)],
        env={"LC_ALL": "C"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        fail("dumpe2fs rejected the source image")
    header = parse_header(result.stdout)
    expected = {
        "Filesystem volume name": values.expected_label,
        "Filesystem UUID": values.expected_uuid,
        "Filesystem state": "clean",
        "Block count": str(values.expected_blocks),
        "First block": "0",
        "Block size": str(BLOCK_SIZE),
    }
    if any(header.get(name) != value for name, value in expected.items()):
        fail("source ext4 identity or clean state changed")
    try:
        free_blocks = int(header["Free blocks"])
    except (KeyError, ValueError) as error:
        raise SparseBuildError("source free-block count is invalid") from error
    free_ranges = parse_free_ranges(result.stdout, values.expected_blocks, free_blocks)
    chunks = allocation_chunks(free_ranges, values.expected_blocks)
    build_sparse(source, values.output, chunks)
    raw_blocks = sum(count for kind, _first, count in chunks if kind == RAW_CHUNK)
    print("format=rog5-ext4-allocated-raw-sparse-v1")
    print(f"blocks={values.expected_blocks}")
    print(f"allocated_raw_blocks={raw_blocks}")
    print(f"free_dont_care_blocks={free_blocks}")
    print(f"chunks={len(chunks)}")
    print(f"output_size={values.output.stat().st_size}")
    print(f"output_sha256={file_sha256(values.output)}")
    print("result=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SparseBuildError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=os.sys.stderr)
        raise SystemExit(1)
