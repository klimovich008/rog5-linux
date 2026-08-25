#!/usr/bin/env python3
"""Stream the reviewed sparse Arch image through fixed direct-write commands."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
MAP = REPO / "configs/storage/local-image-direct-extents.tsv"
MAP_SHA256 = "e21b9453662d5f24536144e322ed0ef6bde7038efb44fdf1afcb80ee823ccd94"
IMAGE_SIZE = 17_179_869_184
IMAGE_SHA256 = "533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153"
BLOCK_SIZE = 4096
BUFFER_SIZE = 1_048_576


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"FAIL {message}")


def parse_map() -> list[tuple[int, int, int]]:
    data = MAP.read_bytes()
    if hashlib.sha256(data).hexdigest() != MAP_SHA256:
        fail("direct extent map changed")
    lines = data.decode("ascii").splitlines()
    expected = [
        "format=rog5-local-image-direct-extents-v1",
        f"image_size={IMAGE_SIZE}",
        f"image_sha256={IMAGE_SHA256}",
        f"block_size={BLOCK_SIZE}",
        "merge_gap_max=1048576",
        "extent_count=37",
        "data_bytes=1850654720",
        "index\toffset_blocks\tblock_count",
    ]
    if lines[:8] != expected or len(lines) != 45:
        fail("direct extent map shape changed")
    extents: list[tuple[int, int, int]] = []
    previous_end = 0
    for expected_index, line in enumerate(lines[8:], 1):
        fields = line.split("\t")
        if len(fields) != 3 or any(not field.isdecimal() for field in fields):
            fail("direct extent map record is invalid")
        index, offset, count = map(int, fields)
        if (
            index != expected_index
            or count <= 0
            or offset < previous_end
            or offset + count > IMAGE_SIZE // BLOCK_SIZE
        ):
            fail("direct extent map ordering changed")
        extents.append((index, offset, count))
        previous_end = offset + count
    return extents


def verify_image(path: Path) -> None:
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


def run(
    command: list[str],
    expected: bytes,
    *,
    accepted: set[int] = {0},
    allow_disconnect: bool = False,
) -> None:
    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout
    disconnect = b"Timeout, server 169.254.77.2 not responding.\n"
    if allow_disconnect and output == expected + disconnect:
        output = expected
    if result.returncode not in accepted or output != expected:
        if len(output) <= 4096 and b"\0" not in output:
            sys.stdout.buffer.write(output)
        fail(f"target command failed: {command[-2:]}")
    sys.stdout.buffer.write(output)


def stream_extent(
    image, command: list[str], index: int, offset: int, count: int
) -> None:
    process = subprocess.Popen(
        [*command, "write", str(index)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.stdin is None:
        fail("target command has no input pipe")
    remaining = count * BLOCK_SIZE
    image.seek(offset * BLOCK_SIZE)
    try:
        while remaining:
            chunk = image.read(min(BUFFER_SIZE, remaining))
            if not chunk:
                fail("reviewed Arch image ended during extent streaming")
            process.stdin.write(chunk)
            remaining -= len(chunk)
        process.stdin.close()
        output = process.stdout.read() if process.stdout is not None else b""
        returncode = process.wait()
    except BrokenPipeError:
        process.kill()
        process.wait()
        fail(f"target closed direct extent {index}")
    expected = (
        "format=rog5-local-image-direct-extent-v1\n"
        f"index={index}\nblocks={count}\nresult=PASS\n"
    ).encode("ascii")
    if returncode != 0 or output != expected:
        if len(output) <= 4096 and b"\0" not in output:
            sys.stdout.buffer.write(output)
        fail(f"target rejected direct extent {index}")
    sys.stdout.buffer.write(output)


def main(arguments: list[str]) -> int:
    if len(arguments) == 2 and arguments[1] == "--verify-only":
        verify_image(Path(arguments[0]))
        parse_map()
        print("PASS reviewed sparse Arch image and direct extent map")
        return 0
    if len(arguments) < 3 or arguments[1] != "--":
        fail(
            "usage: stream-local-image-direct.py IMAGE --verify-only | "
            "IMAGE -- TARGET_COMMAND..."
        )
    image_path = Path(arguments[0])
    command = arguments[2:]
    verify_image(image_path)
    extents = parse_map()
    run(
        [*command, "prepare"],
        b"format=rog5-local-image-direct-stage-v1\nstate=READY\nextents=37\n",
    )
    with image_path.open("rb", buffering=0) as image:
        for index, offset, count in extents:
            stream_extent(image, command, index, offset, count)
    run(
        [*command, "finalize"],
        (
            b"format=rog5-local-image-direct-final-v1\n"
            b"image_size=17179869184\nextents=37\nresult=PASS\n"
        ),
        accepted={0, 255},
        allow_disconnect=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
