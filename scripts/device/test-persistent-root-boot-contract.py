#!/usr/bin/env python3
"""Verify the P2 Android boot-v3 wrapper command-line safety contract."""

from __future__ import annotations

from pathlib import Path
import struct
import sys


BOOT_MAGIC = b"ANDROID!"
BOOT_V3_CMDLINE_OFFSET = 44
BOOT_V3_CMDLINE_SIZE = 1536
BOOT_V3_MIN_HEADER_SIZE = BOOT_V3_CMDLINE_OFFSET + BOOT_V3_CMDLINE_SIZE
REQUIRED_TOKENS = (
    "init=/init",
    "rog5linux.test=1",
    "rog5.recovery_timeout=180",
)
FORBIDDEN_KEYS = ("rog5.ufs_discovery",)


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_boot_v3_cmdline(image: Path) -> str:
    with image.open("rb") as stream:
        header = stream.read(BOOT_V3_MIN_HEADER_SIZE)
    if len(header) != BOOT_V3_MIN_HEADER_SIZE:
        fail("boot image is shorter than the Android boot-v3 header")
    if header[: len(BOOT_MAGIC)] != BOOT_MAGIC:
        fail("Android boot magic is absent")
    header_size = struct.unpack_from("<I", header, 20)[0]
    header_version = struct.unpack_from("<I", header, 40)[0]
    if header_version != 3:
        fail(f"expected boot header v3, found v{header_version}")
    if header_size < BOOT_V3_MIN_HEADER_SIZE:
        fail(f"boot-v3 header is unexpectedly short: {header_size}")
    raw_cmdline = header[
        BOOT_V3_CMDLINE_OFFSET:
        BOOT_V3_CMDLINE_OFFSET + BOOT_V3_CMDLINE_SIZE
    ].split(b"\0", 1)[0]
    try:
        return raw_cmdline.decode("ascii")
    except UnicodeDecodeError as error:
        fail(f"boot command line is not ASCII: {error}")


def main(arguments: list[str]) -> int:
    if len(arguments) > 2:
        fail(
            "usage: test-persistent-root-boot-contract.py "
            "[BOOT_IMAGE [WRAPPER_CONFIG]]"
        )
    repo = Path(__file__).resolve().parents[2]
    image = (
        Path(arguments[0])
        if arguments
        else repo
        / "artifacts"
        / "persistent-root-p2"
        / "boot-5.4.210-persistent-root.raw.img"
    )
    config = (
        Path(arguments[1])
        if len(arguments) == 2
        else repo
        / "artifacts"
        / "persistent-root-p2"
        / "config-5.4.210-persistent-root-wrapper"
    )
    if not image.is_file() or image.is_symlink():
        fail(f"missing regular P2 boot image: {image}")
    if not config.is_file() or config.is_symlink():
        fail(f"missing regular P2 wrapper config: {config}")

    tokens = read_boot_v3_cmdline(image).split()
    for token in REQUIRED_TOKENS:
        key = token.partition("=")[0]
        key_tokens = [
            candidate
            for candidate in tokens
            if candidate.partition("=")[0] == key
        ]
        if key_tokens != [token]:
            fail(f"expected only {token}, found {key_tokens}")
    for key in FORBIDDEN_KEYS:
        key_tokens = [
            candidate
            for candidate in tokens
            if candidate.partition("=")[0] == key
        ]
        if key_tokens:
            fail(f"wrapper must not enable unsupported {key}, found {key_tokens}")
    config_text = config.read_text(encoding="utf-8")
    if "CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y" in config_text:
        fail("ASUS wrapper unexpectedly claims the target-only UFS policy")
    print(
        "PASS P2 boot-v3 wrapper omits target-only UFS discovery and "
        "keeps the exact staging contract"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
