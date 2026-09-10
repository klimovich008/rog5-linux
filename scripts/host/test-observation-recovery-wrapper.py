#!/usr/bin/env python3
"""Hostile offline tests for the observation-only recovery wrapper."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-observation-recovery-wrapper.py"
BUILDER = REPO / "scripts/host/build-observation-recovery-wrapper-offline.sh"
RUNNER = REPO / "scripts/host/test-repository-linux.sh"
REPACK = REPO / "scripts/device/repack-android-boot-v3.sh"
BOOT_TEMPLATE = (
    REPO
    / "artifacts/recovery-wrapper-inputs-v1/"
    "rog5-canonical-boot-v3-template.raw.img"
)
BOOT_TOOLS = REPO / "artifacts/android-boot-tools-v1"
UNPACK_BOOTIMG = BOOT_TOOLS / "unpack_bootimg.py"
AVBTOOL = BOOT_TOOLS / "avbtool.py"
CONFIG = (
    REPO
    / "artifacts/recovery-stage-v18/"
    "config-5.4.210-kexec-stage-builtin-recovery"
)
EXPECTED_CMDLINE = (
    "init=/init selinux=0 printk.devkmsg=on rog5linux.test=1 "
    "ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 "
    "ramoops.record_size=0x100000 ramoops.console_size=0x300000 "
    "ramoops.pmsg_size=0 ramoops.ftrace_size=0 "
    "ramoops.dump_oops=1 rog5.recovery_timeout=180"
)


def align4(value: int) -> int:
    return (value + 3) & ~3


def newc(entries: list[tuple[str, int, bytes]]) -> bytes:
    output = bytearray()
    inode = 1
    for name, mode, payload in [
        *entries,
        ("TRAILER!!!", stat.S_IFREG, b""),
    ]:
        encoded_name = name.encode("ascii") + b"\0"
        fields = (
            inode,
            mode,
            0,
            0,
            1,
            0,
            len(payload),
            0,
            0,
            0,
            0,
            len(encoded_name),
            0,
        )
        header = b"070701" + b"".join(
            f"{value:08x}".encode("ascii") for value in fields
        )
        output.extend(header)
        output.extend(encoded_name)
        output.extend(b"\0" * (align4(len(output)) - len(output)))
        output.extend(payload)
        output.extend(b"\0" * (align4(len(output)) - len(output)))
        inode += 1
    return bytes(output)


def write_archive(
    path: Path,
    *,
    mode: bytes = b"observation-only-v1\n",
    include_kexec: bool = False,
) -> None:
    entries = [
        ("init", stat.S_IFREG | 0o755, b"#!/bin/sh\n"),
        (
            "usr/libexec/rog5-recovery-control",
            stat.S_IFREG | 0o755,
            b"observer-control",
        ),
        ("etc/rog5/recovery-mode", stat.S_IFREG | 0o444, mode),
    ]
    if include_kexec:
        entries.append(("usr/sbin/kexec", stat.S_IFREG | 0o755, b"x"))
    path.write_bytes(gzip.compress(newc(entries), mtime=0))
    path.chmod(0o600)


class Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.archive_a = root / "observer-a.cpio.gz"
        self.archive_b = root / "observer-b.cpio.gz"
        write_archive(self.archive_a)
        shutil.copyfile(self.archive_a, self.archive_b)
        self.output = root / "wrapper"
        self._populate()

    def path(self, relative: str) -> Path:
        return self.output / relative

    def _write(self, relative: str, payload: bytes) -> Path:
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o600)
        return path

    def _populate(self) -> None:
        config = CONFIG.read_bytes()
        image = b"observation-only-kernel-image\n"
        initramfs = self.archive_a.read_bytes()
        initramfs_hash = hashlib.sha256(initramfs).hexdigest()
        config_hash = hashlib.sha256(config).hexdigest()
        image_hash = hashlib.sha256(image).hexdigest()
        metadata = (
            "source_sha256="
            "3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8\n"
            "reference_config_profile=accepted-wrapper-v18-v1\n"
            "kexec_file=0\n"
            f"initramfs_sha256={initramfs_hash}\n"
            "compiler=Ubuntu clang version 18.1.3 (1ubuntu1)\n"
            f"{config_hash}  /root/build/asus-kexec-stage/.config\n"
            f"{image_hash}  /root/build/asus-kexec-stage/arch/arm64/boot/Image\n"
        ).encode("ascii")
        for suffix in ("a", "b"):
            prefix = f"wrapper-{suffix}"
            self._write(f"{prefix}/asus-kexec-stage/.config", config)
            self._write(
                f"{prefix}/asus-kexec-stage/arch/arm64/boot/Image",
                image,
            )
            self._write(
                f"{prefix}/asus-kexec-stage/build-meta.txt",
                metadata,
            )
            self._write(
                f"{prefix}/rog5-kexec-stage-initramfs.cpio.gz",
                initramfs,
            )
        self.repack()
        self._write("source-seal-before.txt", b"source-seal\n")
        self._write("source-seal-after.txt", b"source-seal\n")
        self._write(
            "builder-profile.txt",
            b"builder_profile=steam-deck-asus-5.4-v1\n"
            b"reference_config_profile=accepted-wrapper-v18-v1\n",
        )
        self._write(
            "builder-qualification.txt",
            b"PASS qualified Steam Deck ASUS 5.4 kernel builder\n",
        )
        self._write(
            "cache-publication.txt",
            b"cache_publication=disabled-for-qualified-steam-deck-twin-build\n",
        )

    def repack(self, command_line_override: str = "") -> None:
        # Observation wrappers are a frozen historical 180-second contract;
        # the shared recovery template now defaults to 300 seconds.
        if not command_line_override:
            command_line_override = "rog5.recovery_timeout=180"
        raw_a = self.path("repack/stable-recovery-a.raw.img")
        avb_a = self.path("repack/stable-recovery-a.avb.img")
        raw_a.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                str(REPACK),
                str(BOOT_TEMPLATE),
                str(self.path("wrapper-a/asus-kexec-stage/arch/arm64/boot/Image")),
                str(self.archive_a),
                str(BOOT_TOOLS),
                str(AVBTOOL),
                str(raw_a),
                str(avb_a),
                "100663296",
                command_line_override,
                "rog5.recovery_cidr",
            ],
            cwd=REPO,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        raw_b = self.path("repack/stable-recovery-b.raw.img")
        avb_b = self.path("repack/stable-recovery-b.avb.img")
        shutil.copyfile(raw_a, raw_b)
        shutil.copyfile(avb_a, avb_b)
        for path in (raw_a, raw_b, avb_a, avb_b):
            path.chmod(0o600)
        self._refresh_inspection(raw_a, avb_a)

    def _refresh_inspection(self, raw: Path, avb: Path) -> None:
        unpacked = self.path("inspection/unpacked")
        subprocess.run(
            [
                "python3",
                str(UNPACK_BOOTIMG),
                "--boot_img",
                str(raw),
                "--out",
                str(unpacked),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        arguments = subprocess.run(
            [
                "python3",
                str(UNPACK_BOOTIMG),
                "--boot_img",
                str(raw),
                "--out",
                str(self.path("inspection/arguments")),
                "--format=mkbootimg",
                "--null",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        self._write("inspection/boot-args.lines", arguments.replace(b"\0", b"\n"))
        avb_info = subprocess.run(
            ["python3", str(AVBTOOL), "info_image", "--image", str(avb)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        self._write("inspection/avb-info.txt", avb_info)

    def set_avb_algorithm(self, algorithm_type: int) -> None:
        for suffix in ("a", "b"):
            path = self.path(f"repack/stable-recovery-{suffix}.avb.img")
            with path.open("r+b") as descriptor:
                descriptor.seek(-64, 2)
                footer = descriptor.read(64)
                _, _, _, _, vbmeta_offset, _ = struct.unpack(
                    "!4s2I3Q28x", footer
                )
                descriptor.seek(vbmeta_offset + 28)
                descriptor.write(struct.pack("!I", algorithm_type))


class ObservationWrapperTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        if not VERIFIER.is_file():
            raise RuntimeError("observation-wrapper verifier is missing")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = Fixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def verify(self, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(VERIFIER),
                str(self.fixture.archive_a),
                str(self.fixture.archive_b),
                str(self.fixture.output),
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=check,
        )

    def assert_rejected(self, message: str) -> None:
        result = self.verify(check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"FAIL {message}", result.stderr)

    def test_exact_observation_wrapper_passes(self) -> None:
        result = self.verify()
        self.assertIn(
            "format=rog5-observation-recovery-wrapper-evidence-v1",
            result.stdout,
        )
        self.assertIn("authority=none", result.stdout)
        self.assertIn("boot_authority=none", result.stdout)
        self.assertIn("candidate=none", result.stdout)

    def test_full_mode_and_kexec_archives_fail(self) -> None:
        write_archive(self.fixture.archive_a, mode=b"full-v1\n")
        shutil.copyfile(self.fixture.archive_a, self.fixture.archive_b)
        self.assert_rejected("recovery archive mode is not observation-only")

        write_archive(self.fixture.archive_a, include_kexec=True)
        shutil.copyfile(self.fixture.archive_a, self.fixture.archive_b)
        self.assert_rejected("observation archive retains kexec")

    def test_twin_and_embedded_initramfs_mismatches_fail(self) -> None:
        self.fixture.archive_b.write_bytes(b"wrong")
        self.assert_rejected("observation initramfs twins differ")

        shutil.copyfile(self.fixture.archive_a, self.fixture.archive_b)
        self.fixture.path(
            "wrapper-a/rog5-kexec-stage-initramfs.cpio.gz"
        ).write_bytes(b"wrong")
        self.assert_rejected("wrapper A initramfs differs from observer input")

    def test_ramoops_cmdline_and_pstore_config_are_exact(self) -> None:
        self.fixture.repack("ramoops.mem_size=0x300000")
        self.assert_rejected("boot command line is not the exact observer contract")

        self.fixture.repack()
        config = self.fixture.path("wrapper-a/asus-kexec-stage/.config")
        config.write_text(
            config.read_text(encoding="ascii").replace(
                "CONFIG_PSTORE_RAM=y", "# CONFIG_PSTORE_RAM is not set"
            ),
            encoding="ascii",
        )
        self.assert_rejected("wrapper configuration identity changed")

    def test_avb_must_be_unsigned_boot_only_with_zero_rollback(self) -> None:
        self.fixture.set_avb_algorithm(2)
        self.assert_rejected("AVB algorithm is not NONE")

    def test_detached_sidecars_cannot_certify_changed_avb_payload(self) -> None:
        for suffix in ("a", "b"):
            path = self.fixture.path(
                f"repack/stable-recovery-{suffix}.avb.img"
            )
            with path.open("r+b") as descriptor:
                descriptor.write(b"X")
        self.assert_rejected("AVB payload differs from raw boot image")

    def test_source_seal_and_safe_paths_fail_closed(self) -> None:
        self.fixture.path("source-seal-after.txt").write_text(
            "changed\n", encoding="ascii"
        )
        self.assert_rejected("ASUS source seal changed across twin builds")

        self.fixture.path("source-seal-after.txt").write_text(
            "source-seal\n", encoding="ascii"
        )
        config = self.fixture.path("wrapper-a/asus-kexec-stage/.config")
        config.unlink()
        config.symlink_to(CONFIG)
        self.assert_rejected("unsafe wrapper product path")

    def test_offline_orchestrator_is_exact_and_registered(self) -> None:
        source = BUILDER.read_text(encoding="utf-8")
        for token in (
            "observation-only-a600000-v1",
            "test-stable-recovery-wrapper-offline.sh",
            "verify-observation-recovery-wrapper.py",
            "steam-deck-asus-5.4-v1",
            "ROG5_OBSERVATION_WRAPPER_JOBS:-8",
        ):
            self.assertIn(token, source)
        verifier_source = VERIFIER.read_text(encoding="utf-8")
        for token in ("authority=none", "candidate=none", "boot_authority=none"):
            self.assertIn(token, verifier_source)
        self.assertNotRegex(
            source,
            r"\b(?:fastboot|adb|ssh|scp|sudo|pkexec)\b|/dev/(?:sd|nvme|ufs)",
        )
        self.assertIn(
            "scripts/host/test-observation-recovery-wrapper.py",
            RUNNER.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
