#!/usr/bin/env python3
"""Verify the P2 Android boot-v3 wrapper command-line safety contract."""

from __future__ import annotations

import gzip
from pathlib import Path
import struct
import sys


BOOT_MAGIC = b"ANDROID!"
BOOT_V3_CMDLINE_OFFSET = 44
BOOT_V3_CMDLINE_SIZE = 1536
BOOT_V3_MIN_HEADER_SIZE = BOOT_V3_CMDLINE_OFFSET + BOOT_V3_CMDLINE_SIZE
EXPECTED_TARGET_RELEASE = b"Linux version 7.1.4-gcfd385a1c754 "
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


def read_embedded_config(image: Path) -> bytes:
    image_data = image.read_bytes()
    if EXPECTED_TARGET_RELEASE not in image_data:
        fail("target Image does not contain the exact running-kernel release")
    start_marker = b"IKCFG_ST"
    end_marker = b"IKCFG_ED"
    if image_data.count(start_marker) != 1:
        fail("target Image does not contain exactly one IKCONFIG start marker")
    if image_data.count(end_marker) != 1:
        fail("target Image does not contain exactly one IKCONFIG end marker")
    start = image_data.index(start_marker) + len(start_marker)
    end = image_data.index(end_marker, start)
    return gzip.decompress(image_data[start:end])


def main(arguments: list[str]) -> int:
    if len(arguments) > 4:
        fail(
            "usage: test-persistent-root-boot-contract.py "
            "[BOOT_IMAGE [WRAPPER_CONFIG [TARGET_IMAGE [TARGET_CONFIG]]]]"
        )
    repo = Path(__file__).resolve().parents[2]
    artifact_dir = repo / "artifacts" / "persistent-root-p2"
    boot_image = (
        Path(arguments[0])
        if arguments
        else artifact_dir / "boot-5.4.210-persistent-root.raw.img"
    )
    wrapper_config = (
        Path(arguments[1])
        if len(arguments) >= 2
        else artifact_dir / "config-5.4.210-persistent-root-wrapper"
    )
    target_image = (
        Path(arguments[2])
        if len(arguments) >= 3
        else artifact_dir / "Image-7.1.4-persistent-root"
    )
    target_config = (
        Path(arguments[3])
        if len(arguments) == 4
        else artifact_dir / "config-7.1.4-persistent-root"
    )
    for label, path in (
        ("boot image", boot_image),
        ("wrapper config", wrapper_config),
        ("target Image", target_image),
        ("target config", target_config),
    ):
        if not path.is_file() or path.is_symlink():
            fail(f"missing regular P2 {label}: {path}")

    tokens = read_boot_v3_cmdline(boot_image).split()
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
    wrapper_config_text = wrapper_config.read_text(encoding="utf-8")
    if "CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y" in wrapper_config_text:
        fail("ASUS wrapper unexpectedly claims the target-only UFS policy")
    embedded_config = read_embedded_config(target_image)
    if embedded_config != target_config.read_bytes():
        fail("target Image IKCONFIG differs from the pinned target config")
    target_config_lines = set(
        target_config.read_text(encoding="utf-8").splitlines()
    )
    for setting in (
        "CONFIG_IKCONFIG=y",
        "CONFIG_IKCONFIG_PROC=y",
        "CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y",
        "CONFIG_EXT4_FS=y",
        "CONFIG_OVERLAY_FS=y",
    ):
        if setting not in target_config_lines:
            fail(f"target config omits {setting}")
    print(
        "PASS P2 boot-v3 wrapper omits target-only UFS discovery and "
        "the exact-release target Image embeds the pinned read-only config"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
