#!/usr/bin/env python3
"""Fault-injection tests for the native recovery bundle verifier."""

from __future__ import annotations

import array
import fcntl
import gzip
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import socket
import struct
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "tools/recovery_control/rog5-bundle-verify.c"
ACCEPTED_TARGET_DTB = (
    REPO / "artifacts/network-root-v3/"
    "sm8350-asus-rog-phone5-recovery.dtb"
)
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
FILES = (
    "manifest",
    "manifest.sig",
    "Image",
    "board.dtb",
    "initramfs.cpio.gz",
)
COMMAND_MANIFEST_SHA256 = "a" * 64
ROOT_TREE_SHA256 = "b" * 64
ROOT_SEAL_SHA256 = "c" * 64
ROOT_TREE_ENTRIES = "7"
ZERO_HASH = "0" * 64
STOCK_CHARGING_COMMAND_LINE = (
    "log_buf_len=256K earlycon=msm_geni_serial,0x98c000 "
    "rcupdate.rcu_expedited=1 rcu_nocbs=0-7 kpti=off "
    "console=ttyMSM0,115200n8 androidboot.hardware=qcom "
    "androidboot.console=ttyMSM0 androidboot.memcg=1 "
    "lpm_levels.sleep_disabled=1 video=vfb:640x400,bpp=32,memsize=3072000 "
    "msm_rtb.filter=0x237 service_locator.enable=1 "
    "androidboot.usbcontroller=a600000.dwc3 swiotlb=0 loop.max_part=7 "
    "cgroup.memory=nokmem,nosocket pcie_ports=compat loop.max_part=7 "
    "iptable_raw.raw_before_defrag=1 ip6table_raw.raw_before_defrag=1 "
    "buildvariant=user androidboot.mode=charger androidboot.force_normal_boot=0 "
    "rdinit=/init panic=10 oops=panic loglevel=8 ignore_loglevel "
    "printk.always_kmsg_dump=Y ramoops.mem_address=0x9b800000 "
    "ramoops.mem_size=0x400000 ramoops.record_size=0x100000 "
    "ramoops.console_size=0x300000 ramoops.pmsg_size=0 "
    "ramoops.ftrace_size=0 ramoops.dump_oops=1"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def newc_header(
    name: str,
    size: int,
    *,
    mode: int = 0o100644,
    inode: int = 1,
    magic: bytes = b"070701",
    checksum: int = 0,
) -> bytes:
    encoded_name = name.encode("ascii") + b"\0"
    fields = (
        inode,
        mode,
        0,
        0,
        1,
        0,
        size,
        0,
        0,
        0,
        0,
        len(encoded_name),
        checksum,
    )
    header = magic + "".join(f"{value:08x}" for value in fields).encode(
        "ascii"
    )
    record = header + encoded_name
    return record + bytes((-len(record)) % 4)


def newc_entry(
    name: str,
    data: bytes,
    *,
    mode: int = 0o100644,
    inode: int = 1,
    crc: bool = False,
) -> bytes:
    return (
        newc_header(
            name,
            len(data),
            mode=mode,
            inode=inode,
            magic=b"070702" if crc else b"070701",
            checksum=sum(data) & 0xFFFFFFFF if crc else 0,
        )
        + data
        + bytes((-len(data)) % 4)
    )


def newc_archive(
    entries: list[tuple[str, bytes, int]],
    *,
    crc: bool = False,
) -> bytes:
    archive = bytearray()
    for inode, (name, data, mode) in enumerate(entries, 1):
        archive.extend(
            newc_entry(
                name,
                data,
                mode=mode,
                inode=inode,
                crc=crc,
            )
        )
    archive.extend(
        newc_header(
            "TRAILER!!!",
            0,
            mode=0,
            inode=len(entries) + 1,
            magic=b"070702" if crc else b"070701",
        )
    )
    archive.extend(bytes((-len(archive)) % 512))
    return bytes(archive)


def minimal_initramfs(*, diagnostic: bool = False) -> bytes:
    entries = [
        ("init", b"#!/bin/sh\nexec /bin/sh\n", 0o100755),
        (
            "sbin/persistent-root-verify",
            b"\x7fELFfixture",
            0o100755,
        ),
    ]
    if diagnostic:
        entries.append(
            (
                "sbin/rog5-early-target-diag",
                b"\x7fELFdiagnostic-fixture",
                0o100755,
            )
        )
    return newc_archive(entries)


def rewrite_dtb_property_name(
    blob: bytes,
    old_name: str,
    new_name: str,
    occurrence: int,
) -> bytes:
    result = bytearray(blob)
    struct_offset = struct.unpack_from(">I", result, 8)[0]
    strings_offset = struct.unpack_from(">I", result, 12)[0]
    struct_size = struct.unpack_from(">I", result, 36)[0]
    strings_size = struct.unpack_from(">I", result, 32)[0]
    strings = result[strings_offset : strings_offset + strings_size]
    new_offset = strings.find(new_name.encode("ascii") + b"\0")
    if new_offset < 0:
        raise AssertionError(f"missing DTB string {new_name}")
    cursor = 0
    depth = 0
    matches = 0
    while cursor + 4 <= struct_size:
        token = struct.unpack_from(">I", result, struct_offset + cursor)[0]
        cursor += 4
        if token == 1:
            end = result.index(0, struct_offset + cursor)
            cursor = (end - struct_offset + 4) & ~3
            depth += 1
        elif token == 2:
            depth -= 1
        elif token == 3:
            length, name_offset = struct.unpack_from(
                ">II", result, struct_offset + cursor
            )
            name_end = strings.index(0, name_offset)
            name = strings[name_offset:name_end].decode("ascii")
            if name == old_name:
                if matches == occurrence:
                    struct.pack_into(
                        ">I",
                        result,
                        struct_offset + cursor + 4,
                        new_offset,
                    )
                    return bytes(result)
                matches += 1
            cursor += 8 + ((length + 3) & ~3)
        elif token == 4:
            continue
        elif token == 9:
            break
        else:
            raise AssertionError(f"unknown fixture FDT token {token}")
    raise AssertionError(
        f"missing DTB property occurrence {old_name}[{occurrence}]"
    )


class BundleFixture:
    def __init__(
        self,
        test: "NativeBundleVerifierTest",
        name: str = "signed-test",
        *,
        profile: str = "network-root-v1",
    ):
        self.test = test
        self.name = name
        self.root = test.root / f"{name}-root"
        self.root.mkdir(mode=0o700)
        self.bundle = self.root / name
        self.bundle.mkdir(mode=0o700)
        self.key = test.root / f"{name}.pub"
        self.key.write_bytes(test.public_key)
        self.key.chmod(0o600)
        self.profile = profile
        self.write_kernel()
        self.write_dtb(test.valid_dts())
        (self.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                minimal_initramfs(
                    diagnostic=profile == "diagnostic-initramfs-v1"
                ),
                mtime=0,
            )
        )
        self.refresh_manifest()

    def write_kernel(
        self,
        *,
        magic: bytes = b"ARM\x64",
        image_size: int = 4096,
        flags: int = 0xA,
        reserved: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        image = bytearray(4096)
        struct.pack_into("<Q", image, 16, image_size)
        struct.pack_into("<Q", image, 24, flags)
        struct.pack_into("<QQQ", image, 32, *reserved)
        image[56:60] = magic
        image[64:] = bytes((index * 17 + 3) & 0xFF for index in range(4032))
        (self.bundle / "Image").write_bytes(image)

    def write_dtb(self, source: str) -> None:
        dts = self.test.root / f"{self.name}.dts"
        dts.write_text(source, encoding="ascii")
        subprocess.run(
            [
                "dtc",
                "-q",
                "-I",
                "dts",
                "-O",
                "dtb",
                "-o",
                str(self.bundle / "board.dtb"),
                str(dts),
            ],
            check=True,
            cwd=REPO,
        )

    def fields(self, **overrides: str) -> list[tuple[str, str]]:
        kernel = (self.bundle / "Image").read_bytes()
        dtb = (self.bundle / "board.dtb").read_bytes()
        initramfs = (self.bundle / "initramfs.cpio.gz").read_bytes()
        binds_root = self.profile in {
            "diagnostic-initramfs-v1",
            "network-root-v1",
        }
        values = {
            "format": "rog5-recovery-bundle-v2",
            "bundle": self.name,
            "profile": self.profile,
            "kernel_size": str(len(kernel)),
            "kernel_sha256": sha256(kernel),
            "dtb_size": str(len(dtb)),
            "dtb_sha256": sha256(dtb),
            "initramfs_size": str(len(initramfs)),
            "initramfs_sha256": sha256(initramfs),
            "target_id": "rog5-test",
            "target_release": "test-1",
            "rollback_timeout": (
                "900"
                if self.profile == "stock-charging-recovery-v1"
                else "300"
                if self.profile == "persistent-root-ro-v1"
                else "180"
            ),
            "target_timeout": "90",
            "a660_command_manifest_sha256": (
                COMMAND_MANIFEST_SHA256
                if binds_root
                else ZERO_HASH
            ),
            "root_generation": (
                "arch-a"
                if binds_root
                else "none"
            ),
            "root_tree_sha256": (
                ROOT_TREE_SHA256
                if binds_root
                else ZERO_HASH
            ),
            "root_seal_sha256": (
                ROOT_SEAL_SHA256
                if binds_root
                else ZERO_HASH
            ),
            "root_tree_entries": (
                ROOT_TREE_ENTRIES
                if binds_root
                else "0"
            ),
            "root_subtree": (
                "/" if binds_root else "none"
            ),
        }
        values.update(overrides)
        order = (
            "format",
            "bundle",
            "profile",
            "kernel_size",
            "kernel_sha256",
            "dtb_size",
            "dtb_sha256",
            "initramfs_size",
            "initramfs_sha256",
            "target_id",
            "target_release",
            "rollback_timeout",
            "target_timeout",
            "a660_command_manifest_sha256",
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_tree_entries",
            "root_subtree",
        )
        return [(name, values[name]) for name in order]

    def write_manifest(
        self,
        fields: list[tuple[str, str]] | None = None,
        *,
        raw: bytes | None = None,
        sign: bool = True,
    ) -> None:
        if raw is None:
            if fields is None:
                fields = self.fields()
            raw = "".join(f"{name}={value}\n" for name, value in fields).encode(
                "ascii"
            )
        manifest = self.bundle / "manifest"
        manifest.write_bytes(raw)
        if sign:
            subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-sign",
                    "-rawin",
                    "-inkey",
                    str(self.test.private_key),
                    "-in",
                    str(manifest),
                    "-out",
                    str(self.bundle / "manifest.sig"),
                ],
                check=True,
                cwd=REPO,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

    def refresh_manifest(self, **overrides: str) -> None:
        self.write_manifest(self.fields(**overrides))

    def manifest_hash(self) -> str:
        return sha256((self.bundle / "manifest").read_bytes())

    def invoke(
        self,
        *,
        expected_hash: str | None = None,
        key: Path | None = None,
        requested_name: str | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        if expected_hash is None:
            expected_hash = self.manifest_hash()
        if key is None:
            key = self.key
        if requested_name is None:
            requested_name = self.name
        return subprocess.run(
            [
                *self.test.runner,
                str(self.test.binary),
                "--bundle-root",
                str(self.root),
                "--trust-key",
                str(key),
                requested_name,
                expected_hash,
            ],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )

    def invoke_handoff(
        self,
        *,
        socket_type: int = socket.SOCK_SEQPACKET,
    ) -> tuple[
        subprocess.CompletedProcess[bytes],
        bytes,
        list[int],
        int,
    ]:
        saved_fd3: int | None = None
        saved_fd3_flags = 0
        try:
            saved_fd3_flags = fcntl.fcntl(3, fcntl.F_GETFD)
            saved_fd3 = os.dup(3)
        except OSError:
            pass
        reservation = os.open("/dev/null", os.O_RDONLY)
        if reservation != 3:
            os.dup2(reservation, 3)
        parent, child = socket.socketpair(socket.AF_UNIX, socket_type)
        child_fd = child.fileno()

        command = [
            *self.test.runner,
            str(self.test.binary),
            "--bundle-root",
            str(self.root),
            "--trust-key",
            str(self.key),
            "--handoff-fd3",
            self.name,
            self.manifest_hash(),
        ]
        os.dup2(child_fd, 3, inheritable=True)
        try:
            process = subprocess.Popen(
                command,
                cwd=REPO,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=(3,),
            )
        finally:
            if saved_fd3 is None:
                os.close(3)
            else:
                os.dup2(saved_fd3, 3)
                fcntl.fcntl(3, fcntl.F_SETFD, saved_fd3_flags)
                os.close(saved_fd3)
            if reservation != 3:
                os.close(reservation)
        child.close()
        parent.settimeout(10)
        try:
            packet, ancillary, flags, _ = parent.recvmsg(
                4096,
                socket.CMSG_SPACE(3 * array.array("i").itemsize),
                socket.MSG_CMSG_CLOEXEC,
            )
            stdout, stderr = process.communicate(timeout=10)
        except BaseException:
            process.kill()
            process.wait(timeout=2)
            raise
        finally:
            parent.close()
        descriptors: list[int] = []
        for level, kind, payload in ancillary:
            if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
                continue
            values = array.array("i")
            usable = len(payload) - len(payload) % values.itemsize
            values.frombytes(payload[:usable])
            descriptors.extend(values)
        result = subprocess.CompletedProcess(
            command,
            process.returncode,
            stdout,
            stderr,
        )
        return result, packet, descriptors, flags

    def assert_rejected(self, message: str | None = None, **kwargs) -> None:
        result = self.invoke(**kwargs)
        self.test.assertNotEqual(
            result.returncode,
            0,
            result.stdout.decode(errors="replace"),
        )
        if message is not None:
            self.test.assertIn(
                message,
                result.stderr.decode(errors="replace"),
            )


class NativeBundleVerifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("gcc", "dtc", "openssl", "strings"):
            if shutil.which(command) is None:
                raise RuntimeError(f"{command} is required")
        cls.build = tempfile.TemporaryDirectory()
        cls.build_path = Path(cls.build.name)
        cls.runner = shlex.split(
            os.environ.get("ROG5_BUNDLE_TEST_RUNNER", "")
        )
        override = os.environ.get("ROG5_BUNDLE_TEST_BINARY")
        cls.binary = (
            Path(override)
            if override is not None
            else cls.build_path / "rog5-bundle-verify-test"
        )
        cls.production = cls.build_path / "rog5-bundle-verify"
        common = [
            "gcc",
            "-std=c11",
            "-O2",
            "-fPIE",
            "-pie",
            "-fstack-protector-strong",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none",
        ]
        if override is None:
            subprocess.run(
                [
                    *common,
                    "-DROG5_BUNDLE_TESTING=1",
                    str(SOURCE),
                    "-o",
                    str(cls.binary),
                    "-lcrypto",
                    "-lz",
                ],
                check=True,
                cwd=REPO,
            )
        elif not cls.binary.is_file():
            raise RuntimeError("ROG5_BUNDLE_TEST_BINARY is not a file")
        subprocess.run(
            [
                *common,
                str(SOURCE),
                "-o",
                str(cls.production),
                "-lcrypto",
                "-lz",
            ],
            check=True,
            cwd=REPO,
        )
        cls.private_key = cls.build_path / "test-ed25519-private.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(cls.private_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        public_der = subprocess.check_output(
            [
                "openssl",
                "pkey",
                "-in",
                str(cls.private_key),
                "-pubout",
                "-outform",
                "DER",
            ],
            stderr=subprocess.PIPE,
        )
        if not public_der.startswith(SPKI_PREFIX) or len(public_der) != 44:
            raise RuntimeError("unexpected Ed25519 SubjectPublicKeyInfo")
        cls.public_key = public_der[len(SPKI_PREFIX) :]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.build.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def valid_dts(
        *,
        model: str = "ASUS ROG Phone 5",
        compatible: str = '"asus,rog-phone5", "qcom,sm8350"',
        root_address_cells: str = "<2>",
        root_size_cells: str = "<2>",
        chosen: str = 'stdout-path = "serial0:115200n8";',
        serial_alias: str = "serial0 = &uart2;",
        soc_status: str = "",
        soc_address_cells: str = "<2>",
        soc_size_cells: str = "<2>",
        soc_ranges: str = "<0 0 0 0 0x10 0>",
        qup_compatible: str = "qcom,geni-se-qup",
        qup_reg: str = "<0 0x9c0000 0 0x6000>",
        qup_address_cells: str = "<2>",
        qup_size_cells: str = "<2>",
        qup_ranges: str = "",
        qup_status: str = "okay",
        uart_compatible: str = "qcom,geni-debug-uart",
        uart_reg: str = "<0 0x98c000 0 0x4000>",
        uart_status: str = "okay",
        uart_pinctrl: str = "<&uart2_default>",
        rx_pin: str = "gpio18",
        rx_function: str = "qup3",
        tx_pin: str = "gpio19",
        tx_function: str = "qup3",
        ramoops_start: str = "0x9b800000",
        ramoops_size: str = "0x400000",
        second_start: str = "0x9bc00000",
        second_size: str = "0x100000",
        ranges: str = "ranges;",
        memory_reg: str = (
            "<0 0x80000000 0 0x37100000 "
            "2 0 1 0x80000000 "
            "0 0xc0000000 1 0x40000000 "
            "0 0xb9500000 0 0>"
        ),
    ) -> str:
        return f"""/dts-v1/;

/ {{
\tmodel = "{model}";
\tcompatible = {compatible};
\t#address-cells = {root_address_cells};
\t#size-cells = {root_size_cells};

\taliases {{
\t\t{serial_alias}
\t}};

\tchosen {{
\t\t{chosen}
\t}};

\tmemory@80000000 {{
\t\tdevice_type = "memory";
\t\treg = {memory_reg};
\t}};

\tsoc@0 {{
\t\tcompatible = "simple-bus";
\t\t#address-cells = {soc_address_cells};
\t\t#size-cells = {soc_size_cells};
\t\tranges = {soc_ranges};
\t\t{soc_status}

\t\tgeniqup@9c0000 {{
\t\t\tcompatible = "{qup_compatible}";
\t\t\treg = {qup_reg};
\t\t\t#address-cells = {qup_address_cells};
\t\t\t#size-cells = {qup_size_cells};
\t\t\tranges{qup_ranges};
\t\t\tstatus = "{qup_status}";

\t\t\tuart2: serial@98c000 {{
\t\t\t\tcompatible = "{uart_compatible}";
\t\t\t\treg = {uart_reg};
\t\t\t\tpinctrl-names = "default";
\t\t\t\tpinctrl-0 = {uart_pinctrl};
\t\t\t\tstatus = "{uart_status}";
\t\t\t}};
\t\t}};

\t\tpinctrl@f100000 {{
\t\t\tcompatible = "qcom,sm8350-tlmm";
\t\t\treg = <0 0xf100000 0 0x300000>;

\t\t\tuart2_default: qup-uart3-default-state {{
\t\t\t\trx-pins {{
\t\t\t\t\tpins = "{rx_pin}";
\t\t\t\t\tfunction = "{rx_function}";
\t\t\t\t}};

\t\t\t\ttx-pins {{
\t\t\t\t\tpins = "{tx_pin}";
\t\t\t\t\tfunction = "{tx_function}";
\t\t\t\t}};
\t\t\t}};
\t\t}};
\t}};

\treserved-memory {{
\t\t#address-cells = <2>;
\t\t#size-cells = <2>;
\t\t{ranges}

\t\tmemory@9b800000 {{
\t\t\tno-map;
\t\t\treg = <0 {ramoops_start} 0 {ramoops_size}>;
\t\t}};

\t\tmemory@9bc00000 {{
\t\t\tno-map;
\t\t\treg = <0 {second_start} 0 {second_size}>;
\t\t}};
\t}};
}};
"""

    def fixture(
        self,
        name: str = "signed-test",
        *,
        profile: str = "network-root-v1",
    ) -> BundleFixture:
        return BundleFixture(self, name, profile=profile)

    def test_accepts_each_fixed_profile_and_emits_exact_plan(self) -> None:
        profile_tokens = {
            "diagnostic-initramfs-v1": (
                "rog5.netroot=1 rog5.diagnostic=1"
            ),
            "network-root-v1": "rog5.netroot=1",
            "persistent-root-ro-v1": (
                "rog5.ufs_discovery=1 rog5.persistent_ro=1"
            ),
            "stock-charging-recovery-v1": STOCK_CHARGING_COMMAND_LINE,
        }
        for index, (profile, token) in enumerate(profile_tokens.items()):
            with self.subTest(profile=profile):
                fixture = self.fixture(f"accepted-{index}", profile=profile)
                result = fixture.invoke()
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stderr.decode(errors="replace"),
                )
                output = result.stdout.decode("ascii")
                ramoops = (
                    " ramoops.mem_address=0x9b800000"
                    " ramoops.mem_size=0x400000"
                    " ramoops.record_size=0x100000"
                    " ramoops.console_size=0x300000"
                    " ramoops.pmsg_size=0 ramoops.ftrace_size=0"
                    " ramoops.dump_oops=1"
                    if profile != "persistent-root-ro-v1"
                    and profile != "stock-charging-recovery-v1"
                    else ""
                )
                if profile == "stock-charging-recovery-v1":
                    command_line = STOCK_CHARGING_COMMAND_LINE
                else:
                    command_line = (
                        "console=ttyMSM0,115200n8 rdinit=/init panic=10 "
                        "oops=panic loglevel=8 ignore_loglevel "
                        "printk.always_kmsg_dump=Y "
                        f"{token}{ramoops} "
                        f"rog5.bundle=accepted-{index} "
                        "rog5.target_timeout=90 "
                        f"rog5.recovery_timeout="
                        f"{300 if profile == 'persistent-root-ro-v1' else 180}"
                    )
                if profile in {
                    "diagnostic-initramfs-v1",
                    "network-root-v1",
                }:
                    command_line += (
                        " rog5.a660_command_manifest_sha256="
                        f"{COMMAND_MANIFEST_SHA256}"
                        " rog5.root_generation=arch-a"
                        f" rog5.root_tree_sha256={ROOT_TREE_SHA256}"
                        f" rog5.root_seal_sha256={ROOT_SEAL_SHA256}"
                        f" rog5.root_tree_entries={ROOT_TREE_ENTRIES}"
                        " rog5.root_subtree=/"
                    )
                expected = (
                    "format=rog5-verified-plan-v1\n"
                    f"bundle=accepted-{index}\n"
                    f"manifest_sha256={fixture.manifest_hash()}\n"
                    f"profile={profile}\n"
                    "kernel_file=Image\n"
                    "dtb_file=board.dtb\n"
                    "initramfs_file=initramfs.cpio.gz\n"
                    "target_id=rog5-test\n"
                    "target_release=test-1\n"
                    "target_timeout=90\n"
                    f"cmdline_sha256={sha256(command_line.encode('ascii'))}\n"
                    f"cmdline={command_line}\n"
                )
                self.assertEqual(output, expected)
                self.assertNotIn(str(fixture.root), output)

        self.assertEqual(
            sha256(STOCK_CHARGING_COMMAND_LINE.encode("ascii")),
            "a6d4b68d1eda751632f1b656a037b0bf232a184a5026f08e98292885d9e04a4a",
        )
        self.assertEqual(
            sha256((STOCK_CHARGING_COMMAND_LINE + "\n").encode("ascii")),
            "4721d4e80662df64e809d00a2fcecbd6d6450567663d7791db2a1015bc3526c6",
        )
        source = SOURCE.read_text(encoding="ascii")
        self.assertIn("manifest->initramfs_size != 11125036", source)
        self.assertIn("manifest->dtb_size != 839846", source)
        for identity in (
            "54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33",
            "4a62a4b83ff8948667732e55d8f2e57e575e05e9d3a3aa64b3da1dc58fd78065",
            "cb895b26239fdb29d32ea771e2b52e56a75a1543c62aafc6f6debbb83e992017",
        ):
            self.assertIn(identity, source)

    def test_handoff_preserves_exact_verified_open_files(self) -> None:
        required_seals = (
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE
        )

        def read_snapshot(descriptor: int) -> bytes:
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)

        fixture = self.fixture("handoff")
        expected = fixture.invoke()
        self.assertEqual(
            expected.returncode,
            0,
            expected.stderr.decode(errors="replace"),
        )
        original = [
            (fixture.bundle / name).read_bytes()
            for name in ("Image", "board.dtb", "initramfs.cpio.gz")
        ]
        result, packet, descriptors, flags = fixture.invoke_handoff()
        try:
            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode(errors="replace"),
            )
            self.assertEqual(result.stdout, b"")
            self.assertEqual(packet, expected.stdout)
            self.assertEqual(flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC), 0)
            self.assertEqual(len(descriptors), 3)
            for descriptor in descriptors:
                metadata = os.fstat(descriptor)

                self.assertEqual(os.lseek(descriptor, 0, os.SEEK_CUR), 0)
                self.assertEqual(metadata.st_nlink, 0)
                self.assertEqual(metadata.st_mode & 0o222, 0)
                self.assertEqual(
                    fcntl.fcntl(descriptor, fcntl.F_GET_SEALS),
                    required_seals,
                )
                self.assertNotEqual(
                    fcntl.fcntl(descriptor, fcntl.F_GETFD)
                    & fcntl.FD_CLOEXEC,
                    0,
                )
                with self.assertRaises(PermissionError):
                    os.pwrite(descriptor, b"X", 0)

            for index, name in enumerate(
                ("Image", "board.dtb", "initramfs.cpio.gz")
            ):
                path = fixture.bundle / name
                path.write_bytes(b"W" * len(original[index]))
                self.assertNotEqual(path.read_bytes(), original[index])

            for descriptor, expected_bytes in zip(
                descriptors,
                original,
                strict=True,
            ):
                self.assertEqual(read_snapshot(descriptor), expected_bytes)

            for index, name in enumerate(
                ("Image", "board.dtb", "initramfs.cpio.gz")
            ):
                path = fixture.bundle / name
                replacement = fixture.bundle / f".{name}.replacement"
                replacement.write_bytes(f"replaced-{name}".encode("ascii"))
                replacement.chmod(0o600)
                os.replace(replacement, path)
                self.assertNotEqual(path.read_bytes(), original[index])

            for descriptor, expected_bytes in zip(
                descriptors,
                original,
                strict=True,
            ):
                self.assertEqual(read_snapshot(descriptor), expected_bytes)
        finally:
            for descriptor in descriptors:
                os.close(descriptor)

    def test_handoff_rejects_non_seqpacket_descriptor(self) -> None:
        fixture = self.fixture("handoff-stream")
        result, packet, descriptors, _ = fixture.invoke_handoff(
            socket_type=socket.SOCK_STREAM
        )
        try:
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(packet, b"")
            self.assertEqual(descriptors, [])
            self.assertIn(
                b"handoff descriptor is not a SEQPACKET socket",
                result.stderr,
            )
        finally:
            for descriptor in descriptors:
                os.close(descriptor)

    def test_handoff_rejects_missing_fixed_descriptor(self) -> None:
        fixture = self.fixture("handoff-missing")
        result = subprocess.run(
            [
                *self.runner,
                str(self.binary),
                "--bundle-root",
                str(fixture.root),
                "--trust-key",
                str(fixture.key),
                "--handoff-fd3",
                fixture.name,
                fixture.manifest_hash(),
            ],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"handoff descriptor is not a socket", result.stderr)

    def test_production_build_has_no_path_override_interface(self) -> None:
        strings = subprocess.check_output(["strings", str(self.production)])
        self.assertNotIn(b"--bundle-root", strings)
        self.assertNotIn(b"--trust-key", strings)
        self.assertIn(b"--handoff-fd3", strings)
        result = subprocess.run(
            [
                str(self.production),
                "--bundle-root",
                str(self.root),
                "signed-test",
                "a" * 64,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_manifest_hash_signature_and_trust_root_are_bound(self) -> None:
        fixture = self.fixture()
        fixture.assert_rejected(
            "requested manifest SHA-256 mismatch",
            expected_hash="a" * 64,
        )
        signature = fixture.bundle / "manifest.sig"
        damaged = bytearray(signature.read_bytes())
        damaged[0] ^= 0x80
        signature.write_bytes(damaged)
        fixture.assert_rejected("manifest signature is invalid")
        fixture.write_manifest()

        other_private = self.root / "other-private.pem"
        other_public = self.root / "other.pub"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(other_private),
            ],
            check=True,
            stderr=subprocess.PIPE,
        )
        der = subprocess.check_output(
            [
                "openssl",
                "pkey",
                "-in",
                str(other_private),
                "-pubout",
                "-outform",
                "DER",
            ],
            stderr=subprocess.PIPE,
        )
        other_public.write_bytes(der[len(SPKI_PREFIX) :])
        other_public.chmod(0o600)
        fixture.assert_rejected("manifest signature is invalid", key=other_public)

        fixture = self.fixture("changed-after-signing")
        manifest = fixture.bundle / "manifest"
        changed = manifest.read_bytes().replace(b"test-1", b"test-2")
        self.assertEqual(len(changed), manifest.stat().st_size)
        manifest.write_bytes(changed)
        fixture.assert_rejected("manifest signature is invalid")

    def test_manifest_requires_exact_ascii_order_and_fields(self) -> None:
        cases = {
            "no-newline": lambda fields: "".join(
                f"{key}={value}\n" for key, value in fields
            ).rstrip("\n").encode("ascii"),
            "carriage-return": lambda fields: "".join(
                f"{key}={value}\r\n" for key, value in fields
            ).encode("ascii"),
            "embedded-nul": lambda fields: (
                "".join(f"{key}={value}\n" for key, value in fields)
                .replace("target_id=rog5-test", "target_id=rog5\\0test")
                .encode("ascii")
                .replace(b"\\0", b"\0")
            ),
            "non-ascii": lambda fields: "".join(
                f"{key}={value}\n" for key, value in fields
            ).encode("ascii")[:-2]
            + b"\x80\n",
        }
        for index, (case, make_raw) in enumerate(cases.items()):
            with self.subTest(case=case):
                fixture = self.fixture(f"manifest-byte-{index}")
                fixture.write_manifest(raw=make_raw(fixture.fields()))
                fixture.assert_rejected()

        fixture = self.fixture("manifest-order")
        fields = fixture.fields()
        fields[3], fields[4] = fields[4], fields[3]
        fixture.write_manifest(fields)
        fixture.assert_rejected("manifest is not the canonical v2 record")

        fixture = self.fixture("manifest-extra")
        fields = fixture.fields()
        fields.append(("unexpected", "value"))
        fixture.write_manifest(fields)
        fixture.assert_rejected("manifest is not the canonical v2 record")

        fixture = self.fixture("manifest-duplicate")
        fields = fixture.fields()
        fields.insert(2, fields[1])
        fixture.write_manifest(fields)
        fixture.assert_rejected("manifest is not the canonical v2 record")

    def test_manifest_identity_size_and_timeout_policy(self) -> None:
        cases = (
            ("bundle-none", {"bundle": "none"}),
            ("bad-profile", {"profile": "arbitrary-command-line"}),
            ("leading-zero", {"kernel_size": "04096"}),
            ("zero-timeout", {"rollback_timeout": "0"}),
            ("no-margin", {"rollback_timeout": "60", "target_timeout": "60"}),
            ("bad-target", {"target_id": "../root"}),
            ("zero-hash", {"kernel_sha256": "0" * 64}),
            ("zero-root-hash", {"root_tree_sha256": ZERO_HASH}),
            ("wrong-root-generation", {"root_generation": "arch-b"}),
            ("zero-root-entries", {"root_tree_entries": "0"}),
        )
        for name, overrides in cases:
            with self.subTest(case=name):
                fixture = self.fixture(name)
                fixture.refresh_manifest(**overrides)
                fixture.assert_rejected()
        fixture = self.fixture(
            "diagnostic-without-root-identity",
            profile="diagnostic-initramfs-v1",
        )
        fixture.refresh_manifest(
            a660_command_manifest_sha256=ZERO_HASH,
            root_generation="none",
            root_tree_sha256=ZERO_HASH,
            root_seal_sha256=ZERO_HASH,
            root_tree_entries="0",
            root_subtree="none",
        )
        fixture.assert_rejected(
            "network-root trust identity is invalid"
        )
        fixture = self.fixture(
            "persistent-short",
            profile="persistent-root-ro-v1",
        )
        fixture.refresh_manifest(rollback_timeout="299")
        fixture.assert_rejected("profile rollback timeout is too short")
        fixture = self.fixture(
            "stock-charging-short",
            profile="stock-charging-recovery-v1",
        )
        fixture.refresh_manifest(rollback_timeout="899")
        fixture.assert_rejected("profile rollback timeout is too short")

    def test_artifact_size_and_hash_binding(self) -> None:
        for index, artifact in enumerate(
            ("Image", "board.dtb", "initramfs.cpio.gz")
        ):
            with self.subTest(artifact=artifact):
                fixture = self.fixture(f"artifact-{index}")
                path = fixture.bundle / artifact
                data = bytearray(path.read_bytes())
                data[-1] ^= 1
                path.write_bytes(data)
                fixture.assert_rejected("SHA-256 mismatch")

        fixture = self.fixture("artifact-size")
        with (fixture.bundle / "Image").open("ab") as stream:
            stream.write(b"x")
        fixture.assert_rejected("unsafe bundle file: Image")

        limits = {
            "Image": 128 * 1024 * 1024,
            "board.dtb": 2 * 1024 * 1024,
            "initramfs.cpio.gz": 256 * 1024 * 1024,
        }
        for index, (artifact, maximum) in enumerate(limits.items()):
            with self.subTest(oversized=artifact):
                fixture = self.fixture(f"oversized-{index}")
                with (fixture.bundle / artifact).open("r+b") as stream:
                    stream.truncate(maximum + 1)
                fixture.assert_rejected(
                    f"unsafe bundle file: {artifact}"
                )

    def test_stock_profile_rejects_bootloader_placeholder_memory(self) -> None:
        fixture = self.fixture(
            "stock-zero-memory",
            profile="stock-charging-recovery-v1",
        )
        fixture.write_dtb(self.valid_dts(memory_reg="<0 0 0 0>"))
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "stock DTB lacks exact bootable memory geometry"
        )

    def test_bundle_inventory_rejects_every_missing_file(self) -> None:
        for index, name in enumerate(FILES):
            with self.subTest(missing=name):
                fixture = self.fixture(f"missing-{index}")
                expected_hash = fixture.manifest_hash()
                (fixture.bundle / name).unlink()
                fixture.assert_rejected(
                    "bundle directory is incomplete",
                    expected_hash=expected_hash,
                )

    def test_bundle_filesystem_policy_rejects_aliases_and_writers(self) -> None:
        fixture = self.fixture("extra-entry")
        (fixture.bundle / "extra").write_text("no", encoding="ascii")
        fixture.assert_rejected("unexpected bundle directory entry")

        fixture = self.fixture("symlink")
        image = fixture.bundle / "Image"
        outside = self.root / "outside-image"
        image.replace(outside)
        image.symlink_to(outside)
        fixture.assert_rejected("cannot open bundle file Image")

        fixture = self.fixture("hardlink")
        image = fixture.bundle / "Image"
        os.link(image, self.root / "second-image-link")
        fixture.assert_rejected("unsafe bundle file: Image")

        fixture = self.fixture("writable")
        (fixture.bundle / "board.dtb").chmod(0o666)
        fixture.assert_rejected("unsafe bundle file: board.dtb")

        fixture = self.fixture("writable-directory")
        fixture.bundle.chmod(0o770)
        fixture.assert_rejected("unsafe bundle directory")

        fixture = self.fixture("writable-root")
        fixture.root.chmod(0o770)
        fixture.assert_rejected("unsafe directory")

    def test_trust_key_filesystem_policy(self) -> None:
        fixture = self.fixture()
        fixture.key.chmod(0o660)
        fixture.assert_rejected("unsafe trust key")
        fixture.key.chmod(0o600)
        os.link(fixture.key, self.root / "second-key-link")
        fixture.assert_rejected("unsafe trust key")

        fixture = self.fixture("symlink-key")
        real_key = self.root / "real-key"
        fixture.key.replace(real_key)
        fixture.key.symlink_to(real_key)
        fixture.assert_rejected("cannot open trust key")

    def test_arm64_image_header_policy(self) -> None:
        cases = (
            ("bad-magic", {"magic": b"NOPE"}),
            ("small-memory", {"image_size": 4095}),
            ("large-memory", {"image_size": 256 * 1024 * 1024 + 1}),
            ("unknown-flags", {"flags": 0x10}),
            ("reserved", {"reserved": (1, 0, 0)}),
        )
        for name, values in cases:
            with self.subTest(case=name):
                fixture = self.fixture(name)
                fixture.write_kernel(**values)
                fixture.refresh_manifest()
                fixture.assert_rejected("invalid ARM64 Image header")

    def test_initramfs_must_be_gzip(self) -> None:
        fixture = self.fixture()
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(b"not-gzip")
        fixture.refresh_manifest()
        fixture.assert_rejected("invalid initramfs gzip stream")

        fixture = self.fixture("trailing-gzip")
        path = fixture.bundle / "initramfs.cpio.gz"
        path.write_bytes(path.read_bytes() + b"trailing")
        fixture.refresh_manifest()
        fixture.assert_rejected("initramfs gzip stream has trailing data")

        fixture = self.fixture("not-cpio")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(b"not-a-cpio-archive".ljust(110, b"x"), mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected("initramfs is not a newc CPIO archive")

        fixture = self.fixture("missing-trailer")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_entry(
                    "init",
                    b"#!/bin/sh\n",
                    mode=0o100755,
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "truncated or incomplete initramfs newc archive"
        )

        fixture = self.fixture("missing-init")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_archive(
                    [("bin", b"", 0o040755)]
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected("invalid initramfs newc trailer")

    def test_diagnostic_initramfs_requires_reporter(self) -> None:
        fixture = self.fixture(
            "diagnostic-without-reporter",
            profile="diagnostic-initramfs-v1",
        )
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(minimal_initramfs(), mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "diagnostic initramfs lacks early-target reporter"
        )

    def test_normal_initramfs_rejects_reporter(self) -> None:
        fixture = self.fixture("normal-with-reporter")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(minimal_initramfs(diagnostic=True), mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "non-diagnostic initramfs carries early-target reporter"
        )

    def test_initramfs_archive_content_policy(self) -> None:
        fixture = self.fixture(
            "diagnostic-non-executable-reporter",
            profile="diagnostic-initramfs-v1",
        )
        archive = newc_archive(
            [
                ("init", b"#!/bin/sh\n", 0o100755),
                (
                    "sbin/persistent-root-verify",
                    b"\x7fELFfixture",
                    0o100755,
                ),
                (
                    "sbin/rog5-early-target-diag",
                    b"\x7fELFdiagnostic-fixture",
                    0o100644,
                ),
            ]
        )
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(archive, mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "initramfs has no executable early-target reporter"
        )

        fixture = self.fixture("missing-root-verifier")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_archive(
                    [("init", b"#!/bin/sh\n", 0o100755)]
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "network-root initramfs lacks persistent-root verifier"
        )

        fixture = self.fixture(
            "diagnostic-without-root-verifier",
            profile="diagnostic-initramfs-v1",
        )
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_archive(
                    [("init", b"#!/bin/sh\n", 0o100755)]
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "network-root initramfs lacks persistent-root verifier"
        )

        fixture = self.fixture("duplicate-entry")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_archive(
                    [
                        ("init", b"#!/bin/sh\n", 0o100755),
                        ("init", b"replacement", 0o100755),
                    ]
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "initramfs newc entries are not unique and sorted"
        )

        fixture = self.fixture("traversal-entry")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_archive(
                    [("../init", b"#!/bin/sh\n", 0o100755)]
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected("initramfs has an unsafe newc pathname")

        fixture = self.fixture("non-executable-init")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(
                newc_archive(
                    [("init", b"contents", 0o100644)]
                ),
                mtime=0,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "initramfs has no executable regular /init"
        )

        fixture = self.fixture("non-hex-cpio")
        archive = bytearray(minimal_initramfs())
        archive[6] = ord("g")
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(archive, mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "initramfs has a non-hex newc field"
        )

        fixture = self.fixture("nonzero-cpio-padding")
        archive = bytearray(minimal_initramfs())
        archive[115] = 1
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(archive, mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected("nonzero initramfs newc padding")

        fixture = self.fixture("crc-trailer-checksum")
        archive = bytearray(minimal_initramfs())
        trailer = archive.rfind(b"070701")
        self.assertNotEqual(trailer, -1)
        archive[trailer : trailer + 6] = b"070702"
        archive[trailer + 102 : trailer + 110] = b"00000001"
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(archive, mtime=0)
        )
        fixture.refresh_manifest()
        fixture.assert_rejected("invalid initramfs newc trailer")

    def test_initramfs_accepts_maximum_pathname(self) -> None:
        fixture = self.fixture("maximum-cpio-name")
        archive = newc_archive(
            [
                ("a" * 4096, b"", 0o100644),
                ("init", b"#!/bin/sh\n", 0o100755),
                (
                    "sbin/persistent-root-verify",
                    b"\x7fELFfixture",
                    0o100755,
                ),
            ]
        )
        (fixture.bundle / "initramfs.cpio.gz").write_bytes(
            gzip.compress(archive, mtime=0)
        )
        fixture.refresh_manifest()
        result = fixture.invoke()
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )

    def test_initramfs_crc_archive_is_checked(self) -> None:
        fixture = self.fixture("crc-cpio")
        archive = newc_archive(
            [
                ("init", b"#!/bin/sh\n", 0o100755),
                (
                    "sbin/persistent-root-verify",
                    b"\x7fELFfixture",
                    0o100755,
                ),
            ],
            crc=True,
        )
        path = fixture.bundle / "initramfs.cpio.gz"
        path.write_bytes(gzip.compress(archive, mtime=0))
        fixture.refresh_manifest()
        result = fixture.invoke()
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )

        damaged = bytearray(archive)
        position = damaged.index(b"#!/bin/sh")
        damaged[position] ^= 1
        path.write_bytes(gzip.compress(damaged, mtime=0))
        fixture.refresh_manifest()
        fixture.assert_rejected("initramfs newc data checksum mismatch")

    def test_initramfs_expansion_is_bounded(self) -> None:
        fixture = self.fixture("gzip-bomb")
        with (fixture.bundle / "initramfs.cpio.gz").open("wb") as raw:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                fileobj=raw,
                mtime=0,
            ) as compressor:
                compressor.write(
                    newc_header(
                        "huge",
                        129 * 1024 * 1024,
                        mode=0o100644,
                    )
                )
                block = bytes(1024 * 1024)
                for _ in range(129):
                    compressor.write(block)
        fixture.refresh_manifest()
        fixture.assert_rejected("initramfs expands beyond policy")

    def test_dtb_identity_bootargs_ramoops_and_overlap_policy(self) -> None:
        cases = (
            (
                "model",
                self.valid_dts(model="Different Phone"),
                "DTB lacks the fixed ROG Phone 5 contract",
            ),
            (
                "compatible",
                self.valid_dts(compatible='"qcom,sm8350"'),
                "DTB lacks the fixed ROG Phone 5 contract",
            ),
            (
                "bootargs",
                self.valid_dts(chosen='bootargs = "init=/bin/sh";'),
                "DTB contains forbidden bootargs",
            ),
            (
                "ramoops",
                self.valid_dts(ramoops_start="0x9b700000"),
                "DTB lacks the fixed ROG Phone 5 contract",
            ),
            (
                "overlap",
                self.valid_dts(
                    second_start="0x9bb00000",
                    second_size="0x200000",
                ),
                "overlapping DTB reserved-memory ranges",
            ),
            (
                "translated-ranges",
                self.valid_dts(ranges="ranges = <0 0 0 0 0 0x1000>;"),
                "reserved-memory ranges is not empty",
            ),
            (
                "memreserve",
                self.valid_dts().replace(
                    "/dts-v1/;\n",
                    "/dts-v1/;\n/memreserve/ 0x80000000 0x1000;\n",
                ),
                "unsafe FDT layout",
            ),
        )
        for name, source, error in cases:
            with self.subTest(case=name):
                fixture = self.fixture(f"dtb-{name}")
                fixture.write_dtb(source)
                fixture.refresh_manifest()
                fixture.assert_rejected(error)

    def test_dtb_latent_serial_observability_contract(self) -> None:
        cases = (
            (
                "stdout-path",
                self.valid_dts(chosen='stdout-path = "serial1:115200n8";'),
            ),
            (
                "serial-alias",
                self.valid_dts(serial_alias='serial0 = "/wrong";'),
            ),
            (
                "root-address-cells",
                self.valid_dts(root_address_cells="<1>"),
            ),
            ("root-size-cells", self.valid_dts(root_size_cells="<1>")),
            ("soc-disabled", self.valid_dts(soc_status='status = "disabled";')),
            (
                "soc-address-cells",
                self.valid_dts(soc_address_cells="<1>"),
            ),
            ("soc-size-cells", self.valid_dts(soc_size_cells="<1>")),
            ("soc-ranges", self.valid_dts(soc_ranges="<0 0 0 0 1 0>")),
            (
                "qup-compatible",
                self.valid_dts(qup_compatible="qcom,geni-se"),
            ),
            (
                "qup-register",
                self.valid_dts(qup_reg="<0 0x9d0000 0 0x6000>"),
            ),
            (
                "qup-address-cells",
                self.valid_dts(qup_address_cells="<1>"),
            ),
            ("qup-size-cells", self.valid_dts(qup_size_cells="<1>")),
            (
                "qup-ranges",
                self.valid_dts(qup_ranges=" = <0 0 0 0 0x10 0>"),
            ),
            ("qup-disabled", self.valid_dts(qup_status="disabled")),
            (
                "uart-compatible",
                self.valid_dts(uart_compatible="qcom,geni-uart"),
            ),
            (
                "uart-register",
                self.valid_dts(uart_reg="<0 0x998000 0 0x4000>"),
            ),
            ("uart-disabled", self.valid_dts(uart_status="disabled")),
            (
                "wrong-pinctrl-phandle",
                self.valid_dts(uart_pinctrl="<0xdeadbeef>"),
            ),
            ("rx-pin", self.valid_dts(rx_pin="gpio19")),
            ("rx-function", self.valid_dts(rx_function="gpio")),
            ("tx-pin", self.valid_dts(tx_pin="gpio18")),
            ("tx-function", self.valid_dts(tx_function="gpio")),
        )
        for name, source in cases:
            with self.subTest(case=name):
                fixture = self.fixture(f"dtb-serial-{name}")
                fixture.write_dtb(source)
                fixture.refresh_manifest()
                fixture.assert_rejected(
                    "DTB lacks the latent serial observability contract"
                )

    def test_repository_accepted_dtb_has_serial_observability_contract(
        self,
    ) -> None:
        fixture = self.fixture("accepted-serial-dtb")
        shutil.copyfile(
            ACCEPTED_TARGET_DTB,
            fixture.bundle / "board.dtb",
        )
        fixture.refresh_manifest()
        result = fixture.invoke()
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )

    def test_dtb_rejects_truncated_header_and_string_list(self) -> None:
        fixture = self.fixture("dtb-header")
        dtb = bytearray((fixture.bundle / "board.dtb").read_bytes())
        dtb[0:4] = b"BAD!"
        (fixture.bundle / "board.dtb").write_bytes(dtb)
        fixture.refresh_manifest()
        fixture.assert_rejected("invalid FDT header")

        fixture = self.fixture("dtb-string")
        path = fixture.bundle / "board.dtb"
        dtb = bytearray(path.read_bytes())
        needle = b"asus,rog-phone5\x00qcom,sm8350\x00"
        position = dtb.find(needle)
        self.assertNotEqual(position, -1)
        dtb[position + len(needle) - 1] = ord("X")
        path.write_bytes(dtb)
        fixture.refresh_manifest()
        fixture.assert_rejected("unterminated FDT string list")

        fixture = self.fixture("dtb-duplicate-cells")
        path = fixture.bundle / "board.dtb"
        path.write_bytes(
            rewrite_dtb_property_name(
                path.read_bytes(),
                "#size-cells",
                "#address-cells",
                3,
            )
        )
        fixture.refresh_manifest()
        fixture.assert_rejected(
            "invalid reserved-memory address cells"
        )

    def test_dtb_requires_explicit_reserved_memory_geometry(self) -> None:
        cases = (
            ("missing-address", "#address-cells = <2>;\n", ""),
            ("missing-size", "#size-cells = <2>;\n", ""),
            ("missing-ranges", "ranges;\n", ""),
        )
        for name, before, after in cases:
            with self.subTest(case=name):
                fixture = self.fixture(name)
                source = self.valid_dts()
                reserved = source.index("\treserved-memory {")
                position = source.find(before, reserved)
                self.assertNotEqual(position, -1)
                source = (
                    source[:position]
                    + after
                    + source[position + len(before) :]
                )
                fixture.write_dtb(source)
                fixture.refresh_manifest()
                fixture.assert_rejected(
                    "incomplete reserved-memory policy"
                )

    def test_bundle_name_and_requested_name_must_match(self) -> None:
        fixture = self.fixture()
        fixture.assert_rejected(requested_name="other")
        fixture.assert_rejected(
            "invalid requested bundle identity",
            requested_name="../signed-test",
        )
        fixture.refresh_manifest(bundle="other")
        fixture.assert_rejected()


if __name__ == "__main__":
    unittest.main(verbosity=2)
