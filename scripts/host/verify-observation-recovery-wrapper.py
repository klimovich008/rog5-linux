#!/usr/bin/env python3
"""Verify offline observation-only ASUS recovery wrapper evidence."""

from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tempfile
from typing import NamedTuple


REPO = Path(__file__).resolve().parents[2]
UNPACK_BOOTIMG = REPO / "artifacts/android-boot-tools-v1/unpack_bootimg.py"
AVBTOOL = REPO / "artifacts/android-boot-tools-v1/avbtool.py"
EXPECTED_UNPACK_SHA256 = (
    "7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef"
)
EXPECTED_AVBTOOL_SHA256 = (
    "6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff"
)
EXPECTED_CONFIG_SHA256 = (
    "df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f"
)
EXPECTED_SOURCE_SHA256 = (
    "3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8"
)
HISTORICAL_FULL_IMAGE_SHA256 = (
    "4b30cfff3aedb6ac04bb57d981df920314d830adcbcbed9a3da033db7cec9495"
)
HISTORICAL_FULL_RAW_SHA256 = (
    "5141f0d037f8ca8dc5a2367a476b2730d4cdac8cd61d6d29a95bbf3ca477deab"
)
HISTORICAL_FULL_AVB_SHA256 = (
    "b004e500a7e77840568ec6e8aee8092e16a9e6a4089f954d140d68c8c2b0c218"
)
EXPECTED_CMDLINE = (
    "init=/init selinux=0 printk.devkmsg=on rog5linux.test=1 "
    "ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 "
    "ramoops.record_size=0x100000 ramoops.console_size=0x300000 "
    "ramoops.pmsg_size=0 ramoops.ftrace_size=0 "
    "ramoops.dump_oops=1 rog5.recovery_timeout=300"
)
EXPECTED_PARTITION_SIZE = 100_663_296
REQUIRED_CONFIG = (
    "CONFIG_PSTORE=y",
    "CONFIG_PSTORE_CONSOLE=y",
    "CONFIG_PSTORE_PMSG=y",
    "CONFIG_PSTORE_RAM=y",
)


class VerificationError(Exception):
    pass


class NewcEntry(NamedTuple):
    mode: int
    uid: int
    gid: int
    nlink: int
    payload: bytes


def fail(message: str) -> None:
    raise VerificationError(message)


def safe_file(path: Path, role: str) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        fail(role)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.geteuid()
        or metadata.st_mode & 0o022
    ):
        fail(role)


def read_safe(path: Path, role: str) -> bytes:
    safe_file(path, role)
    try:
        return path.read_bytes()
    except OSError:
        fail(role)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(archive: bytes) -> dict[str, NewcEntry]:
    try:
        payload = gzip.decompress(archive)
    except (OSError, EOFError):
        fail("observation initramfs is not a valid gzip archive")
    result: dict[str, NewcEntry] = {}
    offset = 0
    found_trailer = False
    while offset < len(payload):
        if payload[offset:] and not payload[offset:].strip(b"\0"):
            break
        if offset + 110 > len(payload):
            fail("observation initramfs has a truncated newc header")
        header = payload[offset : offset + 110]
        if header[:6] not in (b"070701", b"070702"):
            fail("observation initramfs is not a newc archive")
        try:
            fields = [
                int(header[6 + index * 8 : 14 + index * 8], 16)
                for index in range(13)
            ]
        except ValueError:
            fail("observation initramfs has an invalid newc header")
        mode, uid, gid, nlink = fields[1:5]
        file_size = fields[6]
        name_size = fields[11]
        if name_size < 2:
            fail("observation initramfs has an invalid entry name")
        name_start = offset + 110
        name_end = name_start + name_size
        if name_end > len(payload) or payload[name_end - 1] != 0:
            fail("observation initramfs has a truncated entry name")
        try:
            name = payload[name_start : name_end - 1].decode("utf-8")
        except UnicodeDecodeError:
            fail("observation initramfs has a non-UTF-8 entry name")
        data_start = align4(name_end)
        data_end = data_start + file_size
        if data_end > len(payload):
            fail("observation initramfs has truncated entry data")
        offset = align4(data_end)
        if name == "TRAILER!!!":
            found_trailer = True
            break
        while name.startswith("./"):
            name = name[2:]
        pure_name = PurePosixPath(name)
        if (
            not name
            or pure_name.is_absolute()
            or ".." in pure_name.parts
            or name in result
        ):
            fail("observation initramfs has an unsafe or duplicate path")
        result[name] = NewcEntry(
            mode, uid, gid, nlink, payload[data_start:data_end]
        )
    if not found_trailer:
        fail("observation initramfs lacks its newc trailer")
    return result


def require_archive_entry(
    entries: dict[str, NewcEntry],
    name: str,
    permissions: int,
    expected_payload: bytes | None = None,
) -> None:
    entry = entries.get(name)
    if entry is None:
        fail(f"observation archive lacks {name}")
    if (
        not stat.S_ISREG(entry.mode)
        or stat.S_IMODE(entry.mode) != permissions
        or entry.uid != 0
        or entry.gid != 0
        or entry.nlink != 1
    ):
        fail(f"observation archive metadata changed for {name}")
    if expected_payload is not None and entry.payload != expected_payload:
        fail("recovery archive mode is not observation-only")


def verify_archive(archive: bytes) -> None:
    entries = parse_newc(archive)
    require_archive_entry(entries, "init", 0o755)
    require_archive_entry(entries, "usr/libexec/rog5-recovery-control", 0o755)
    require_archive_entry(
        entries,
        "etc/rog5/recovery-mode",
        0o444,
        b"observation-only-v1\n",
    )
    forbidden = {
        "usr/libexec/rog5-bundle-fetch",
        "usr/libexec/rog5-bundle-verify",
        "etc/rog5/recovery-bundle-ed25519.pub",
        "usr/sbin/kexec",
    }
    if forbidden.intersection(entries) or any(
        PurePosixPath(name).name == "kexec" for name in entries
    ):
        fail("observation archive retains kexec")
    if any(name == "run/rog5-bundles" or name.startswith("run/rog5-bundles/") for name in entries):
        fail("observation archive retains bundle state")


def require_equal(left: bytes, right: bytes, message: str) -> None:
    if left != right:
        fail(message)


def exact_line(text: str, line: str, message: str) -> None:
    if text.splitlines().count(line) != 1:
        fail(message)


def extract_cmdline(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line == "--cmdline":
            if lines.count("--cmdline") != 1:
                break
            return lines[index + 1]
    fail("boot command line is not the exact observer contract")


def run_tool(arguments: list[str], message: str) -> bytes:
    try:
        result = subprocess.run(
            arguments,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        fail(message)
    return result.stdout


def avb_algorithm_and_original_size(avb: bytes) -> tuple[int, int]:
    if len(avb) < 64:
        fail("AVB footer is missing or malformed")
    try:
        (
            magic,
            version_major,
            version_minor,
            original_size,
            vbmeta_offset,
            vbmeta_size,
        ) = struct.unpack("!4s2I3Q28x", avb[-64:])
    except struct.error:
        fail("AVB footer is missing or malformed")
    if (
        magic != b"AVBf"
        or (version_major, version_minor) != (1, 0)
        or vbmeta_size < 256
        or vbmeta_offset + vbmeta_size > len(avb) - 64
        or avb[vbmeta_offset : vbmeta_offset + 4] != b"AVB0"
    ):
        fail("AVB footer is missing or malformed")
    algorithm_type = struct.unpack_from("!I", avb, vbmeta_offset + 28)[0]
    return algorithm_type, original_size


def inspect_boot_and_avb(
    raw_path: Path,
    avb_path: Path,
    products: dict[str, bytes],
) -> tuple[str, str]:
    unpack_payload = read_safe(UNPACK_BOOTIMG, "unsafe pinned boot tool")
    avbtool_payload = read_safe(AVBTOOL, "unsafe pinned AVB tool")
    if digest(unpack_payload) != EXPECTED_UNPACK_SHA256:
        fail("pinned boot unpacker identity changed")
    if digest(avbtool_payload) != EXPECTED_AVBTOOL_SHA256:
        fail("pinned AVB tool identity changed")

    with tempfile.TemporaryDirectory(prefix="rog5-observer-wrapper-") as stage:
        stage_path = Path(stage)
        unpacked = stage_path / "unpacked"
        boot_info = run_tool(
            [
                sys.executable,
                str(UNPACK_BOOTIMG),
                "--boot_img",
                str(raw_path),
                "--out",
                str(unpacked),
            ],
            "raw boot-v3 inspection failed",
        ).decode("utf-8", errors="strict")
        exact_line(
            boot_info,
            "boot image header version: 3",
            "raw boot image is not header version 3",
        )
        try:
            fresh_kernel = (unpacked / "kernel").read_bytes()
            fresh_ramdisk = (unpacked / "ramdisk").read_bytes()
        except OSError:
            fail("raw boot-v3 inspection failed")
        require_equal(
            fresh_kernel,
            products["image_a"],
            "raw boot kernel differs from wrapper Image",
        )
        require_equal(
            fresh_ramdisk,
            products["embedded_a"],
            "raw boot ramdisk differs from observer input",
        )
        require_equal(
            fresh_kernel,
            products["unpacked_kernel"],
            "retained unpacked kernel differs from raw boot image",
        )
        require_equal(
            fresh_ramdisk,
            products["unpacked_ramdisk"],
            "retained unpacked ramdisk differs from raw boot image",
        )

        raw_arguments = run_tool(
            [
                sys.executable,
                str(UNPACK_BOOTIMG),
                "--boot_img",
                str(raw_path),
                "--out",
                str(stage_path / "arguments"),
                "--format=mkbootimg",
                "--null",
            ],
            "raw boot-v3 argument inspection failed",
        )
        try:
            arguments = [
                item.decode("utf-8")
                for item in raw_arguments.rstrip(b"\0").split(b"\0")
            ]
        except UnicodeDecodeError:
            fail("raw boot-v3 argument inspection failed")
        if arguments.count("--cmdline") != 1:
            fail("boot command line is not the exact observer contract")
        index = arguments.index("--cmdline")
        if index + 1 >= len(arguments):
            fail("boot command line is not the exact observer contract")
        command_line = arguments[index + 1]
        retained_command_line = extract_cmdline(
            products["boot_args"].decode("ascii", errors="strict")
        )
        if retained_command_line != command_line:
            fail("retained boot arguments differ from raw boot image")

        fresh_avb_info = run_tool(
            [
                sys.executable,
                str(AVBTOOL),
                "info_image",
                "--image",
                str(avb_path),
            ],
            "AVB metadata inspection failed",
        ).decode("ascii", errors="strict")
        if fresh_avb_info.encode("ascii") != products["avb_info"]:
            fail("retained AVB information differs from the AVB image")
        boot_link = stage_path / "boot.img"
        boot_link.symlink_to(avb_path.resolve(strict=True))
        run_tool(
            [
                sys.executable,
                str(AVBTOOL),
                "verify_image",
                "--image",
                str(boot_link),
            ],
            "AVB verification failed",
        )
    return command_line, fresh_avb_info


def verify(initramfs_a_path: Path, initramfs_b_path: Path, output: Path) -> str:
    initramfs_a = read_safe(
        initramfs_a_path, "unsafe observation initramfs path"
    )
    initramfs_b = read_safe(
        initramfs_b_path, "unsafe observation initramfs path"
    )
    if initramfs_a != initramfs_b:
        fail("observation initramfs twins differ")
    verify_archive(initramfs_a)

    names = {
        "config_a": "wrapper-a/asus-kexec-stage/.config",
        "config_b": "wrapper-b/asus-kexec-stage/.config",
        "image_a": "wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
        "image_b": "wrapper-b/asus-kexec-stage/arch/arm64/boot/Image",
        "meta_a": "wrapper-a/asus-kexec-stage/build-meta.txt",
        "meta_b": "wrapper-b/asus-kexec-stage/build-meta.txt",
        "embedded_a": "wrapper-a/rog5-kexec-stage-initramfs.cpio.gz",
        "embedded_b": "wrapper-b/rog5-kexec-stage-initramfs.cpio.gz",
        "raw_a": "repack/stable-recovery-a.raw.img",
        "raw_b": "repack/stable-recovery-b.raw.img",
        "avb_a": "repack/stable-recovery-a.avb.img",
        "avb_b": "repack/stable-recovery-b.avb.img",
        "unpacked_kernel": "inspection/unpacked/kernel",
        "unpacked_ramdisk": "inspection/unpacked/ramdisk",
        "boot_args": "inspection/boot-args.lines",
        "avb_info": "inspection/avb-info.txt",
        "seal_before": "source-seal-before.txt",
        "seal_after": "source-seal-after.txt",
        "profile": "builder-profile.txt",
        "qualification": "builder-qualification.txt",
        "cache": "cache-publication.txt",
    }
    products = {
        name: read_safe(output / relative, "unsafe wrapper product path")
        for name, relative in names.items()
    }

    config_sha256 = digest(products["config_a"])
    if config_sha256 != EXPECTED_CONFIG_SHA256:
        fail("wrapper configuration identity changed")
    require_equal(products["config_a"], products["config_b"], "wrapper config twins differ")
    require_equal(products["image_a"], products["image_b"], "wrapper Image twins differ")
    require_equal(products["meta_a"], products["meta_b"], "wrapper metadata twins differ")
    require_equal(products["raw_a"], products["raw_b"], "raw boot twins differ")
    require_equal(products["avb_a"], products["avb_b"], "AVB wrapper twins differ")
    require_equal(products["embedded_a"], initramfs_a, "wrapper A initramfs differs from observer input")
    require_equal(products["embedded_b"], initramfs_b, "wrapper B initramfs differs from observer input")
    require_equal(products["unpacked_ramdisk"], initramfs_a, "unpacked ramdisk differs from observer input")
    require_equal(products["unpacked_kernel"], products["image_a"], "unpacked kernel differs from wrapper Image")

    config_text = products["config_a"].decode("utf-8", errors="strict")
    for line in REQUIRED_CONFIG:
        exact_line(config_text, line, f"wrapper lacks exact {line}")

    initramfs_sha256 = digest(initramfs_a)
    image_sha256 = digest(products["image_a"])
    raw_sha256 = digest(products["raw_a"])
    avb_sha256 = digest(products["avb_a"])
    if image_sha256 == HISTORICAL_FULL_IMAGE_SHA256:
        fail("observer wrapper reused the full-recovery Image")
    if raw_sha256 == HISTORICAL_FULL_RAW_SHA256:
        fail("observer wrapper reused the full-recovery raw image")
    if avb_sha256 == HISTORICAL_FULL_AVB_SHA256:
        fail("observer wrapper reused the full-recovery AVB image")

    expected_meta = (
        f"source_sha256={EXPECTED_SOURCE_SHA256}\n"
        "reference_config_profile=accepted-wrapper-v18-v1\n"
        "kexec_file=0\n"
        f"initramfs_sha256={initramfs_sha256}\n"
        "compiler=Ubuntu clang version 18.1.3 (1ubuntu1)\n"
        f"{config_sha256}  /root/build/asus-kexec-stage/.config\n"
        f"{image_sha256}  /root/build/asus-kexec-stage/arch/arm64/boot/Image\n"
    ).encode("ascii")
    require_equal(products["meta_a"], expected_meta, "wrapper build metadata changed")

    require_equal(products["seal_before"], products["seal_after"], "ASUS source seal changed across twin builds")
    profile = products["profile"].decode("ascii", errors="strict")
    exact_line(profile, "builder_profile=steam-deck-asus-5.4-v1", "wrong wrapper builder profile")
    exact_line(profile, "reference_config_profile=accepted-wrapper-v18-v1", "wrong wrapper config profile")
    qualification = products["qualification"].decode("ascii", errors="strict")
    exact_line(qualification, "PASS qualified Steam Deck ASUS 5.4 kernel builder", "builder qualification missing")
    cache = products["cache"].decode("ascii", errors="strict")
    exact_line(cache, "cache_publication=disabled-for-qualified-steam-deck-twin-build", "wrapper cache was not disabled")

    raw_size = len(products["raw_a"])
    if len(products["avb_a"]) != EXPECTED_PARTITION_SIZE:
        fail("AVB wrapper size is not the exact boot partition size")
    algorithm_type, original_size = avb_algorithm_and_original_size(
        products["avb_a"]
    )
    if algorithm_type != 0:
        fail("AVB algorithm is not NONE")
    if original_size != raw_size:
        fail("AVB original image size changed")
    if products["avb_a"][:raw_size] != products["raw_a"]:
        fail("AVB payload differs from raw boot image")

    command_line, avb_info = inspect_boot_and_avb(
        output / names["raw_a"], output / names["avb_a"], products
    )
    if command_line != EXPECTED_CMDLINE:
        fail("boot command line is not the exact observer contract")

    required_avb_patterns = (
        (rf"^Image size:\s+{EXPECTED_PARTITION_SIZE} bytes$", "AVB image size changed"),
        (rf"^Original image size:\s+{raw_size} bytes$", "AVB original image size changed"),
        (r"^Algorithm:\s+NONE$", "AVB algorithm is not NONE"),
        (r"^Rollback Index:\s+0$", "AVB rollback index is not zero"),
        (rf"^\s+Image Size:\s+{raw_size} bytes$", "AVB descriptor size changed"),
        (r"^\s+Partition Name:\s+boot$", "AVB partition name is not boot"),
    )
    for pattern, message in required_avb_patterns:
        if len(re.findall(pattern, avb_info, flags=re.MULTILINE)) != 1:
            fail(message)

    return "\n".join(
        (
            "format=rog5-observation-recovery-wrapper-evidence-v1",
            f"observer_initramfs_size={len(initramfs_a)}",
            f"observer_initramfs_sha256={initramfs_sha256}",
            f"wrapper_config_size={len(products['config_a'])}",
            f"wrapper_config_sha256={config_sha256}",
            f"wrapper_image_size={len(products['image_a'])}",
            f"wrapper_image_sha256={image_sha256}",
            f"raw_boot_size={raw_size}",
            f"raw_boot_sha256={raw_sha256}",
            f"unsigned_avb_size={len(products['avb_a'])}",
            f"unsigned_avb_sha256={avb_sha256}",
            "ramoops_mem_address=0x9b800000",
            "ramoops_mem_size=0x400000",
            "authority=none",
            "candidate=none",
            "boot_authority=none",
            "retention=unproven",
            "PASS observation-only clean-twin wrapper evidence is exact and offline-only",
        )
    )


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: verify-observation-recovery-wrapper.py "
            "INITRAMFS_A INITRAMFS_B OUTPUT_ROOT",
            file=sys.stderr,
        )
        return 2
    try:
        report = verify(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    except (VerificationError, UnicodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
