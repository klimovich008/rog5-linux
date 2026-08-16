#!/usr/bin/env python3
"""Offline tests for the atomic stable-recovery bundle packager."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
PACKAGER_PATH = REPO / "scripts/host/prepare-recovery-runtime-bundle.py"
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
VERIFIER_SOURCE = REPO / "tools/recovery_control/rog5-bundle-verify.c"
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
FILES = (
    "manifest",
    "manifest.sig",
    "Image",
    "board.dtb",
    "initramfs.cpio.gz",
)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


PACKAGER = load_module("rog5_bundle_packager", PACKAGER_PATH)
SERVER = load_module(
    "rog5_host_bundle_server",
    REPO / "tools/recovery_control/host_bundle_server.py",
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def newc_header(
    name: str,
    size: int,
    *,
    mode: int = 0o100644,
    inode: int = 1,
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
        0,
    )
    header = b"070701" + "".join(
        f"{value:08x}" for value in fields
    ).encode("ascii")
    record = header + encoded_name
    return record + bytes((-len(record)) % 4)


def newc_entry(
    name: str,
    payload: bytes,
    *,
    mode: int,
    inode: int,
) -> bytes:
    return (
        newc_header(name, len(payload), mode=mode, inode=inode)
        + payload
        + bytes((-len(payload)) % 4)
    )


def minimal_initramfs(*, diagnostic: bool = False) -> bytes:
    archive = bytearray()
    archive.extend(
        newc_entry(
            "init",
            b"#!/bin/sh\nexec /bin/sh\n",
            mode=0o100755,
            inode=1,
        )
    )
    archive.extend(
        newc_entry(
            "sbin/persistent-root-verify",
            b"\x7fELFfixture",
            mode=0o100755,
            inode=2,
        )
    )
    next_inode = 3
    if diagnostic:
        archive.extend(
            newc_entry(
                "sbin/rog5-early-target-diag",
                b"\x7fELFdiagnostic-fixture",
                mode=0o100755,
                inode=next_inode,
            )
        )
        next_inode += 1
    archive.extend(
        newc_header("TRAILER!!!", 0, mode=0, inode=next_inode)
    )
    archive.extend(bytes((-len(archive)) % 512))
    return gzip.compress(bytes(archive), mtime=0)


def valid_dts() -> str:
    return """/dts-v1/;

/ {
\tmodel = "ASUS ROG Phone 5";
\tcompatible = "asus,rog-phone5", "qcom,sm8350";
\t#address-cells = <2>;
\t#size-cells = <2>;

\taliases {
\t\tserial0 = &uart2;
\t};

\tchosen {
\t\tstdout-path = "serial0:115200n8";
\t};

\tmemory@80000000 {
\t\tdevice_type = "memory";
\t\treg = <0 0x80000000 0 0x37100000
\t\t       2 0 1 0x80000000
\t\t       0 0xc0000000 1 0x40000000
\t\t       0 0xb9500000 0 0>;
\t};

\tsoc@0 {
\t\tcompatible = "simple-bus";
\t\t#address-cells = <2>;
\t\t#size-cells = <2>;
\t\tranges = <0 0 0 0 0x10 0>;

\t\tgeniqup@9c0000 {
\t\t\tcompatible = "qcom,geni-se-qup";
\t\t\treg = <0 0x9c0000 0 0x6000>;
\t\t\t#address-cells = <2>;
\t\t\t#size-cells = <2>;
\t\t\tranges;
\t\t\tstatus = "okay";

\t\t\tuart2: serial@98c000 {
\t\t\t\tcompatible = "qcom,geni-debug-uart";
\t\t\t\treg = <0 0x98c000 0 0x4000>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tpinctrl-0 = <&uart2_default>;
\t\t\t\tstatus = "okay";
\t\t\t};
\t\t};

\t\tpinctrl@f100000 {
\t\t\tcompatible = "qcom,sm8350-tlmm";
\t\t\treg = <0 0xf100000 0 0x300000>;

\t\t\tuart2_default: qup-uart3-default-state {
\t\t\t\trx-pins {
\t\t\t\t\tpins = "gpio18";
\t\t\t\t\tfunction = "qup3";
\t\t\t\t};

\t\t\t\ttx-pins {
\t\t\t\t\tpins = "gpio19";
\t\t\t\t\tfunction = "qup3";
\t\t\t\t};
\t\t\t};
\t\t};
\t};

\treserved-memory {
\t\t#address-cells = <2>;
\t\t#size-cells = <2>;
\t\tranges;

\t\tmemory@9b800000 {
\t\t\tno-map;
\t\t\treg = <0 0x9b800000 0 0x400000>;
\t\t};

\t\tmemory@9bc00000 {
\t\t\tno-map;
\t\t\treg = <0 0x9bc00000 0 0x100000>;
\t\t};
\t};
};
"""


class BundlePackagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("dtc", "gcc", "openssl"):
            if shutil.which(command) is None:
                raise RuntimeError(f"{command} is required")
        cls.build = tempfile.TemporaryDirectory()
        cls.build_path = Path(cls.build.name)
        cls.verifier = cls.build_path / "rog5-bundle-verify-test"
        subprocess.run(
            [
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
                "-DROG5_BUNDLE_TESTING=1",
                str(VERIFIER_SOURCE),
                "-o",
                str(cls.verifier),
                "-lcrypto",
                "-lz",
            ],
            check=True,
            cwd=REPO,
        )
        cls.private_key = cls.build_path / "ephemeral-ed25519.pem"
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
        cls.private_key.chmod(0o600)
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
        if (
            len(public_der) != len(SPKI_PREFIX) + 32
            or not public_der.startswith(SPKI_PREFIX)
        ):
            raise RuntimeError("unexpected ephemeral Ed25519 public key")
        cls.public_key = public_der[len(SPKI_PREFIX) :]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.build.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.index = 0

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def workspace(self, label: str) -> tuple[PACKAGER.Configuration, Path]:
        self.index += 1
        workspace = self.base / f"{self.index}-{label}"
        workspace.mkdir()
        sources = workspace / "sources"
        sources.mkdir()

        image = bytearray(4096)
        struct.pack_into("<Q", image, 16, len(image))
        struct.pack_into("<Q", image, 24, 0xA)
        image[56:60] = b"ARM\x64"
        image[64:] = bytes(
            (position * 17 + 3) & 0xFF for position in range(4032)
        )
        image_path = sources / "Image"
        image_path.write_bytes(image)

        dts_path = sources / "board.dts"
        dtb_path = sources / "board.dtb"
        dts_path.write_text(valid_dts(), encoding="ascii")
        subprocess.run(
            [
                "dtc",
                "-q",
                "-I",
                "dts",
                "-O",
                "dtb",
                "-o",
                str(dtb_path),
                str(dts_path),
            ],
            check=True,
            cwd=REPO,
        )

        initramfs_path = sources / "initramfs.cpio.gz"
        initramfs_path.write_bytes(
            minimal_initramfs(diagnostic=label == "diagnostic-initramfs-v1")
        )
        bundle_root = workspace / "bundles"
        bundle_root.mkdir(mode=0o700)
        bundle_root.chmod(0o700)
        config = PACKAGER.Configuration(
            bundle="test-bundle",
            profile="network-root-v1",
            image=image_path,
            dtb=dtb_path,
            initramfs=initramfs_path,
            target_id="rog5-a660",
            target_release="accepted-v9",
            rollback_timeout="180",
            target_timeout="90",
            a660_command_manifest_sha256=COMMAND_MANIFEST_SHA256,
            root_generation="arch-a",
            root_tree_sha256=ROOT_TREE_SHA256,
            root_seal_sha256=ROOT_SEAL_SHA256,
            root_tree_entries=ROOT_TREE_ENTRIES,
            root_subtree="/",
            private_key=self.private_key,
            bundle_root=bundle_root,
        )
        return config, workspace

    @staticmethod
    def replace(
        config: PACKAGER.Configuration,
        **updates,
    ) -> PACKAGER.Configuration:
        values = {
            field: getattr(config, field)
            for field in config.__dataclass_fields__
        }
        values.update(updates)
        return PACKAGER.Configuration(**values)

    @staticmethod
    def arguments(config: PACKAGER.Configuration) -> list[str]:
        return [
            "--bundle",
            config.bundle,
            "--profile",
            config.profile,
            "--image",
            str(config.image),
            "--dtb",
            str(config.dtb),
            "--initramfs",
            str(config.initramfs),
            "--target-id",
            config.target_id,
            "--target-release",
            config.target_release,
            "--rollback-timeout",
            config.rollback_timeout,
            "--target-timeout",
            config.target_timeout,
            "--a660-command-manifest-sha256",
            config.a660_command_manifest_sha256,
            "--root-generation",
            config.root_generation,
            "--root-tree-sha256",
            config.root_tree_sha256,
            "--root-seal-sha256",
            config.root_seal_sha256,
            "--root-tree-entries",
            config.root_tree_entries,
            "--root-subtree",
            config.root_subtree,
            "--private-key",
            str(config.private_key),
            "--bundle-root",
            str(config.bundle_root),
        ]

    def invoke(
        self,
        config: PACKAGER.Configuration,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(PACKAGER_PATH), *self.arguments(config)],
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )

    def assert_packaged(
        self,
        config: PACKAGER.Configuration,
    ) -> tuple[Path, str]:
        result = self.invoke(config)
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )
        bundle = config.bundle_root / config.bundle
        manifest_hash = sha256((bundle / "manifest").read_bytes())
        expected = (
            "format=rog5-prepared-bundle-v1\n"
            f"bundle={config.bundle}\n"
            f"profile={config.profile}\n"
            f"manifest_sha256={manifest_hash}\n"
            f"trust_key_sha256={sha256(self.public_key)}\n"
        ).encode("ascii")
        self.assertEqual(result.stdout, expected)
        self.assertEqual(result.stderr, b"")
        return bundle, manifest_hash

    def public_key_file(self, workspace: Path) -> Path:
        path = workspace / "ephemeral-ed25519.pub"
        path.write_bytes(self.public_key)
        path.chmod(0o600)
        return path

    def test_each_fixed_profile_passes_native_and_host_verifiers(self) -> None:
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
        for profile_index, (profile, token) in enumerate(
            profile_tokens.items()
        ):
            with self.subTest(profile=profile):
                config, workspace = self.workspace(profile)
                rollback = (
                    "900"
                    if profile == "stock-charging-recovery-v1"
                    else "300"
                    if profile == "persistent-root-ro-v1"
                    else "180"
                )
                config = self.replace(
                    config,
                    bundle=f"profile-{profile_index}",
                    profile=profile,
                    rollback_timeout=rollback,
                    **(
                        {}
                        if profile in {
                            "diagnostic-initramfs-v1",
                            "network-root-v1",
                        }
                        else {
                            "a660_command_manifest_sha256": ZERO_HASH,
                            "root_generation": "none",
                            "root_tree_sha256": ZERO_HASH,
                            "root_seal_sha256": ZERO_HASH,
                            "root_tree_entries": "0",
                            "root_subtree": "none",
                        }
                    ),
                )
                _bundle, manifest_hash = self.assert_packaged(config)
                public_key = self.public_key_file(workspace)
                result = subprocess.run(
                    [
                        str(self.verifier),
                        "--bundle-root",
                        str(config.bundle_root),
                        "--trust-key",
                        str(public_key),
                        config.bundle,
                        manifest_hash,
                    ],
                    cwd=REPO,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stderr.decode(errors="replace"),
                )
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
                        f"rog5.bundle={config.bundle} "
                        f"rog5.target_timeout={config.target_timeout} "
                        f"rog5.recovery_timeout={rollback}"
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
                expected_plan = (
                    "format=rog5-verified-plan-v1\n"
                    f"bundle={config.bundle}\n"
                    f"manifest_sha256={manifest_hash}\n"
                    f"profile={profile}\n"
                    "kernel_file=Image\n"
                    "dtb_file=board.dtb\n"
                    "initramfs_file=initramfs.cpio.gz\n"
                    f"target_id={config.target_id}\n"
                    f"target_release={config.target_release}\n"
                    f"target_timeout={config.target_timeout}\n"
                    f"cmdline_sha256={sha256(command_line.encode('ascii'))}\n"
                    f"cmdline={command_line}\n"
                ).encode("ascii")
                self.assertEqual(result.stdout, expected_plan)

                root_descriptor = os.open(
                    config.bundle_root,
                    os.O_RDONLY | os.O_DIRECTORY,
                )
                try:
                    with SERVER.prepare_bundle(
                        root_descriptor,
                        config.bundle,
                        manifest_hash,
                        os.geteuid(),
                    ) as prepared:
                        self.assertEqual(prepared.bundle, config.bundle)
                        self.assertEqual(
                            prepared.manifest_hash,
                            manifest_hash,
                        )
                finally:
                    os.close(root_descriptor)

    def test_output_is_deterministic_and_has_exact_private_metadata(self) -> None:
        first, workspace = self.workspace("deterministic-first")
        second_root = workspace / "second-root"
        second_root.mkdir(mode=0o700)
        second_root.chmod(0o700)
        second = self.replace(first, bundle_root=second_root)
        first_bundle, _first_hash = self.assert_packaged(first)
        second_bundle, _second_hash = self.assert_packaged(second)

        self.assertEqual(
            {path.name for path in first.bundle_root.iterdir()},
            {first.bundle},
        )
        for bundle in (first_bundle, second_bundle):
            metadata = bundle.stat()
            self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o500)
            self.assertEqual(metadata.st_uid, os.geteuid())
            self.assertEqual({path.name for path in bundle.iterdir()}, set(FILES))
            aggregate = bytearray()
            for name in FILES:
                path = bundle / name
                metadata = path.stat()
                self.assertTrue(stat.S_ISREG(metadata.st_mode))
                self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o400)
                self.assertEqual(metadata.st_uid, os.geteuid())
                self.assertEqual(metadata.st_nlink, 1)
                aggregate.extend(path.read_bytes())
            self.assertNotIn(self.private_key.read_bytes(), bytes(aggregate))
            self.assertNotIn(b"BEGIN PRIVATE KEY", bytes(aggregate))

        for name in FILES:
            self.assertEqual(
                (first_bundle / name).read_bytes(),
                (second_bundle / name).read_bytes(),
                name,
            )

    def test_refusal_matrix_never_leaves_a_partial_bundle(self) -> None:
        cases = (
            ("bad-bundle-case", {"bundle": "Bad"}),
            ("reserved-bundle", {"bundle": "none"}),
            ("dot-dot-bundle", {"bundle": "a..b"}),
            ("unknown-profile", {"profile": "a660-freeform"}),
            ("unsafe-target", {"target_id": ".hidden"}),
            ("unsafe-release", {"target_release": "v1..v2"}),
            ("leading-zero-timeout", {"rollback_timeout": "0180"}),
            (
                "timeout-margin",
                {"rollback_timeout": "180", "target_timeout": "151"},
            ),
            (
                "zero-network-root-hash",
                {"root_tree_sha256": ZERO_HASH},
            ),
            (
                "diagnostic-without-root-identity",
                {
                    "profile": "diagnostic-initramfs-v1",
                    "a660_command_manifest_sha256": ZERO_HASH,
                    "root_generation": "none",
                    "root_tree_sha256": ZERO_HASH,
                    "root_seal_sha256": ZERO_HASH,
                    "root_tree_entries": "0",
                    "root_subtree": "none",
                },
            ),
            (
                "short-persistent",
                {
                    "profile": "persistent-root-ro-v1",
                    "rollback_timeout": "299",
                },
            ),
        )
        for label, updates in cases:
            with self.subTest(case=label):
                config, _workspace = self.workspace(label)
                config = self.replace(config, **updates)
                result = self.invoke(config)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("source-symlink")
        image_link = workspace / "Image.link"
        image_link.symlink_to(config.image)
        result = self.invoke(self.replace(config, image=image_link))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, _workspace = self.workspace("key-artifact-alias")
        result = self.invoke(
            self.replace(config, image=self.private_key)
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"bundle artifact aliases the private key",
            result.stderr,
        )
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("key-symlink")
        key_link = workspace / "key.link"
        key_link.symlink_to(self.private_key)
        result = self.invoke(self.replace(config, private_key=key_link))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("weak-key-mode")
        weak_key = workspace / "weak-key.pem"
        weak_key.write_bytes(self.private_key.read_bytes())
        weak_key.chmod(0o644)
        result = self.invoke(self.replace(config, private_key=weak_key))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("hard-linked-key")
        key_copy = workspace / "key-copy.pem"
        hard_key = workspace / "hard-key.pem"
        key_copy.write_bytes(self.private_key.read_bytes())
        key_copy.chmod(0o600)
        os.link(key_copy, hard_key)
        result = self.invoke(self.replace(config, private_key=hard_key))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("encrypted-empty-passphrase")
        encrypted_key = workspace / "encrypted.pem"
        subprocess.run(
            [
                "openssl",
                "pkcs8",
                "-topk8",
                "-in",
                str(self.private_key),
                "-out",
                str(encrypted_key),
                "-passout",
                "pass:",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        encrypted_key.chmod(0o600)
        result = self.invoke(
            self.replace(config, private_key=encrypted_key)
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("rsa-key")
        rsa_key = workspace / "rsa.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(rsa_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        rsa_key.chmod(0o600)
        result = self.invoke(self.replace(config, private_key=rsa_key))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, _workspace = self.workspace("root-mode")
        config.bundle_root.chmod(0o755)
        result = self.invoke(config)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        config, workspace = self.workspace("root-symlink")
        root_link = workspace / "bundles.link"
        root_link.symlink_to(config.bundle_root, target_is_directory=True)
        result = self.invoke(self.replace(config, bundle_root=root_link))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

        for label, entry_kind in (
            ("nonempty-root", "file"),
            ("existing-bundle", "directory"),
        ):
            with self.subTest(case=label):
                config, _workspace = self.workspace(label)
                entry = config.bundle_root / (
                    "unrelated" if entry_kind == "file" else config.bundle
                )
                if entry_kind == "file":
                    entry.write_bytes(b"preserve")
                else:
                    entry.mkdir()
                inventory = {path.name for path in config.bundle_root.iterdir()}
                result = self.invoke(config)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(
                    {path.name for path in config.bundle_root.iterdir()},
                    inventory,
                )

    def test_signing_failure_cleans_exact_staging_directory(self) -> None:
        config, _workspace = self.workspace("signing-failure")

        def fail_signing(
            _manifest: bytes,
            _private_key: int,
            _openssl: str,
        ) -> bytes:
            raise PACKAGER.BundleError("injected signing failure")

        with self.assertRaisesRegex(
            PACKAGER.BundleError,
            "injected signing failure",
        ):
            PACKAGER.prepare_bundle(config, signer=fail_signing)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

    def test_concurrent_final_directory_is_never_replaced(self) -> None:
        config, _workspace = self.workspace("no-replace-race")
        competing_identity: list[tuple[int, int]] = []

        def create_competing_final(
            manifest: bytes,
            private_key: int,
            openssl: str,
        ) -> bytes:
            competing = config.bundle_root / config.bundle
            competing.mkdir(mode=0o700)
            metadata = competing.stat()
            competing_identity.append(
                (metadata.st_dev, metadata.st_ino)
            )
            return PACKAGER.sign_manifest(
                manifest,
                private_key,
                openssl,
            )

        with self.assertRaisesRegex(
            PACKAGER.BundleError,
            "atomic no-replace publication failed",
        ):
            PACKAGER.prepare_bundle(config, signer=create_competing_final)
        self.assertEqual(
            {path.name for path in config.bundle_root.iterdir()},
            {config.bundle},
        )
        competing = config.bundle_root / config.bundle
        metadata = competing.stat()
        self.assertEqual(
            (metadata.st_dev, metadata.st_ino),
            competing_identity[0],
        )
        self.assertEqual(list(competing.iterdir()), [])

    def test_private_key_change_during_signing_is_rejected(self) -> None:
        config, _workspace = self.workspace("changing-key")

        def change_key_metadata(
            manifest: bytes,
            private_key: int,
            openssl: str,
        ) -> bytes:
            signature = PACKAGER.sign_manifest(
                manifest,
                private_key,
                openssl,
            )
            os.utime(config.private_key, None)
            return signature

        with self.assertRaisesRegex(
            PACKAGER.BundleError,
            "private key changed while signing",
        ):
            PACKAGER.prepare_bundle(config, signer=change_key_metadata)
        self.assertEqual(list(config.bundle_root.iterdir()), [])

    def test_wrong_private_key_owner_is_rejected(self) -> None:
        descriptor = os.open(self.private_key, os.O_RDONLY)
        try:
            with mock.patch.object(
                PACKAGER.os,
                "geteuid",
                return_value=os.geteuid() + 1,
            ):
                with self.assertRaisesRegex(
                    PACKAGER.BundleError,
                    "private key metadata is unsafe",
                ):
                    PACKAGER.validate_private_key(
                        descriptor,
                        shutil.which("openssl"),
                    )
        finally:
            os.close(descriptor)

    def test_failed_staging_open_removes_created_directory(self) -> None:
        config, _workspace = self.workspace("staging-open-failure")
        root = os.open(
            config.bundle_root,
            os.O_RDONLY | os.O_DIRECTORY,
        )
        real_open = os.open

        def fail_staging_open(path, flags, mode=0o777, *, dir_fd=None):
            if (
                isinstance(path, str)
                and path.startswith(f".{config.bundle}.staging-")
                and dir_fd == root
            ):
                raise PermissionError("injected staging open failure")
            return real_open(path, flags, mode, dir_fd=dir_fd)

        try:
            with mock.patch.object(
                PACKAGER.os,
                "open",
                side_effect=fail_staging_open,
            ):
                with self.assertRaisesRegex(
                    PACKAGER.BundleError,
                    "cannot open private staging directory",
                ):
                    PACKAGER.create_staging_directory(
                        root,
                        config.bundle,
                    )
        finally:
            os.close(root)
        self.assertEqual(list(config.bundle_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
