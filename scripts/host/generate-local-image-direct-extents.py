#!/usr/bin/env python3
"""Generate the fixed direct-I/O extent plan for the reviewed Arch image."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys


IMAGE_SIZE = 17_179_869_184
IMAGE_SHA256 = "533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153"
BLOCK_SIZE = 4096
MERGE_GAP_MAX = 1_048_576


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"FAIL {message}")


def image_extents(path: Path) -> list[tuple[int, int]]:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 2
        or metadata.st_size != IMAGE_SIZE
    ):
        fail("reviewed Arch image metadata changed")
    with path.open("rb", buffering=0) as image:
        if hashlib.file_digest(image, "sha256").hexdigest() != IMAGE_SHA256:
            fail("reviewed Arch image hash changed")
        descriptor = image.fileno()
        position = 0
        source: list[tuple[int, int]] = []
        while position < IMAGE_SIZE:
            try:
                start = os.lseek(descriptor, position, os.SEEK_DATA)
            except OSError:
                break
            end = os.lseek(descriptor, start, os.SEEK_HOLE)
            if (
                start % BLOCK_SIZE
                or end % BLOCK_SIZE
                or not start < end <= IMAGE_SIZE
            ):
                fail("reviewed Arch image extent is invalid")
            source.append((start, end))
            position = end
    merged: list[tuple[int, int]] = []
    for start, end in source:
        if merged and start - merged[-1][1] <= MERGE_GAP_MAX:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def render(path: Path) -> bytes:
    extents = image_extents(path)
    data_bytes = sum(end - start for start, end in extents)
    lines = [
        "format=rog5-local-image-direct-extents-v1",
        f"image_size={IMAGE_SIZE}",
        f"image_sha256={IMAGE_SHA256}",
        f"block_size={BLOCK_SIZE}",
        f"merge_gap_max={MERGE_GAP_MAX}",
        f"extent_count={len(extents)}",
        f"data_bytes={data_bytes}",
        "index\toffset_blocks\tblock_count",
    ]
    lines.extend(
        f"{index}\t{start // BLOCK_SIZE}\t{(end - start) // BLOCK_SIZE}"
        for index, (start, end) in enumerate(extents, 1)
    )
    return ("\n".join(lines) + "\n").encode("ascii")


def main(arguments: list[str]) -> int:
    if len(arguments) not in {1, 3} or (
        len(arguments) == 3 and arguments[1] != "--check"
    ):
        fail("usage: generate-local-image-direct-extents.py IMAGE [--check MAP]")
    generated = render(Path(arguments[0]))
    if len(arguments) == 3:
        if Path(arguments[2]).read_bytes() != generated:
            fail("direct extent map is stale")
        print("PASS direct extent map is current")
    else:
        sys.stdout.buffer.write(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
