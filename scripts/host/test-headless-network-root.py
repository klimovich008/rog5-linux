#!/usr/bin/env python3
"""Offline tests for the sealed headless network-root package."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO / "scripts/host/headless-network-root.py"
COMMAND = REPO / "packaging/arch/rog5-headless-command-manifest"
INSTALLER = REPO / "scripts/host/install-headless-network-root-export.sh"
EXPORT_VERIFIER = (
    REPO / "scripts/host/verify-headless-network-root-export.sh"
)
SERVER = REPO / "scripts/host/serve-network-root.sh"
FIXTURE = REPO / "configs/ssh/rog5-headless-build-fixture.pub"


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_headless_network_root_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load headless network-root tool")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()
FIXTURE_KEY = b" ".join(FIXTURE.read_bytes().strip().split()[:2]) + b"\n"
FIXTURE_FINGERPRINT = TOOL.authorized_key_fingerprint(FIXTURE_KEY)


def ed25519_key(byte: int) -> bytes:
    algorithm = b"ssh-ed25519"
    blob = (
        len(algorithm).to_bytes(4, "big")
        + algorithm
        + (32).to_bytes(4, "big")
        + bytes((byte,)) * 32
    )
    return algorithm + b" " + base64.b64encode(blob) + b"\n"


class HeadlessNetworkRootTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("bsdtar") is None:
            raise RuntimeError("bsdtar is required")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "root"
        (self.root / "etc/rog5").mkdir(parents=True)
        (self.root / "usr/lib/rog5").mkdir(parents=True)
        (self.root / "etc/rog5/build").write_text(
            "profile=headless-ssh-v1\n"
            "project_commit=eb61a45938c851b1b02a2f3151db5265ab9213e7\n"
            f"rootfs_sha256={'a' * 64}\n"
            f"modules_sha256={'b' * 64}\n"
            "kernel_release=7.1.4-g7a5cef0db479\n",
            encoding="ascii",
        )
        (self.root / "usr/lib/rog5/payload").write_text(
            "fixture\n",
            encoding="ascii",
        )
        self.identity = Path(self.temporary.name) / "identity"
        self.archive = Path(self.temporary.name) / "sealed.tar"
        self.package = Path(self.temporary.name) / "manifest"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_core_build(self) -> None:
        (self.root / "etc/rog5/build").write_text(
            "profile=headless-core-v2\n"
            "project_commit=6a8090e936bfbc2a8e93b430671a216593d11ca9\n"
            f"rootfs_sha256={'a' * 64}\n"
            f"modules_sha256={'b' * 64}\n"
            "kernel_release=7.1.4-g7a5cef0db479\n"
            f"indicator_sha256={'d' * 64}\n"
            "indicator_policy=power-key-green-status-pulse-v1\n",
            encoding="ascii",
        )

    def write_ssh_v2_build(
        self,
        key: bytes = FIXTURE_KEY,
        fingerprint: str = FIXTURE_FINGERPRINT,
    ) -> None:
        ssh_directory = self.root / "root/.ssh"
        ssh_directory.mkdir(parents=True, exist_ok=True)
        ssh_directory.chmod(0o700)
        authorized_keys = ssh_directory / "authorized_keys"
        authorized_keys.write_bytes(key)
        authorized_keys.chmod(0o600)
        (self.root / "etc/rog5/build").write_text(
            "profile=headless-ssh-v2\n"
            "project_commit=000acc638ec851b1b02a2f3151db5265ab9213e7\n"
            f"rootfs_sha256={'a' * 64}\n"
            f"modules_sha256={'b' * 64}\n"
            "kernel_release=7.1.4-g7a5cef0db479\n"
            f"authorized_key_fingerprint={fingerprint}\n",
            encoding="ascii",
        )

    @staticmethod
    def write_fixed(path: Path, payload: bytes) -> None:
        if path.exists():
            path.chmod(0o600)
        path.write_bytes(payload)
        path.chmod(0o444)

    def prepare_package(
        self,
        build_profile: str = "headless-ssh-v1",
    ) -> None:
        TOOL.prepare(
            self.root,
            "123",
            "c" * 64,
            COMMAND,
            self.identity,
            build_profile,
        )
        subprocess.run(
            [
                "bsdtar",
                "--acls",
                "--xattrs",
                "--fflags",
                "-cpf",
                str(self.archive),
                "-C",
                str(self.root),
                ".",
            ],
            check=True,
        )
        TOOL.package(self.identity, self.archive, self.package)

    def test_no_workload_root_is_fully_bound(self) -> None:
        self.prepare_package()
        values = TOOL.verify(
            self.root,
            self.archive,
            self.package,
            COMMAND,
        )
        self.assertEqual(values["profile"], "network-root-v1")
        self.assertEqual(values["root_generation"], "arch-a")
        self.assertEqual(values["root_subtree"], "/")
        self.assertGreater(int(values["root_tree_entries"]), 1)
        self.assertRegex(values["root_tree_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(values["root_seal_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            (self.root / "etc/rog5/a660-command-manifest").read_text(
                encoding="ascii"
            ),
            COMMAND.read_text(encoding="ascii"),
        )
        runtime_values = TOOL.verify_root(self.root, self.package)
        self.assertEqual(runtime_values, values)

    def test_headless_core_successor_is_explicitly_bound(self) -> None:
        self.write_core_build()
        self.prepare_package("headless-core-v2")
        values = TOOL.verify(
            self.root,
            self.archive,
            self.package,
            COMMAND,
        )
        self.assertEqual(
            values["format"],
            "rog5-headless-network-root-package-v2",
        )
        self.assertEqual(values["profile"], "network-root-v1")
        self.assertEqual(values["build_profile"], "headless-core-v2")
        package_payload = self.package.read_text(encoding="ascii")
        self.assertIn("build_profile=headless-core-v2\n", package_payload)

        self.package.chmod(0o600)
        self.package.write_text(
            package_payload.replace(
                "build_profile=headless-core-v2",
                "build_profile=headless-ssh-v1",
            ),
            encoding="ascii",
        )
        self.package.chmod(0o444)
        with self.assertRaises(TOOL.HeadlessRootError):
            TOOL.verify_root(self.root, self.package)

    def test_ssh_v2_key_is_canonically_bound(self) -> None:
        self.write_ssh_v2_build()
        self.prepare_package("headless-ssh-v2")
        values = TOOL.verify(
            self.root,
            self.archive,
            self.package,
            COMMAND,
        )
        self.assertEqual(
            values["format"],
            "rog5-headless-network-root-package-v3",
        )
        self.assertEqual(values["build_profile"], "headless-ssh-v2")
        self.assertEqual(
            values["authorized_key_fingerprint"],
            FIXTURE_FINGERPRINT,
        )
        self.assertEqual(
            (self.root / TOOL.AUTHORIZED_KEYS_PATH).read_bytes(),
            FIXTURE_KEY,
        )

    def test_ssh_v2_rejects_key_build_and_package_mismatches(self) -> None:
        other_key = ed25519_key(0x5A)
        other_fingerprint = TOOL.authorized_key_fingerprint(other_key)
        cases = ("key", "build", "package")
        for case in cases:
            with self.subTest(case=case):
                self.tearDown()
                self.setUp()
                if case == "key":
                    self.write_ssh_v2_build(key=other_key)
                    with self.assertRaises(TOOL.HeadlessRootError):
                        TOOL.validate_build(
                            self.root,
                            self.root.stat().st_uid,
                            "headless-ssh-v2",
                        )
                    continue
                self.write_ssh_v2_build(
                    fingerprint=(
                        other_fingerprint
                        if case == "build"
                        else FIXTURE_FINGERPRINT
                    )
                )
                if case == "build":
                    with self.assertRaises(TOOL.HeadlessRootError):
                        TOOL.validate_build(
                            self.root,
                            self.root.stat().st_uid,
                            "headless-ssh-v2",
                        )
                    continue
                self.prepare_package("headless-ssh-v2")
                payload = self.package.read_text(encoding="ascii")
                self.write_fixed(
                    self.package,
                    payload.replace(
                        FIXTURE_FINGERPRINT,
                        other_fingerprint,
                    ).encode("ascii"),
                )
                with self.assertRaises(TOOL.HeadlessRootError):
                    TOOL.verify_root(self.root, self.package)

    def test_ssh_v2_rejects_noncanonical_or_malformed_keys(self) -> None:
        key_type, encoded = FIXTURE_KEY.rstrip(b"\n").split(b" ")
        rsa_algorithm = b"ssh-rsa"
        mismatched_blob = (
            len(rsa_algorithm).to_bytes(4, "big")
            + rsa_algorithm
            + (32).to_bytes(4, "big")
            + b"\x11" * 32
        )
        cases = (
            FIXTURE_KEY.rstrip(b"\n"),
            FIXTURE_KEY.replace(b"\n", b"\r\n"),
            b"restrict " + FIXTURE_KEY,
            FIXTURE_KEY.rstrip(b"\n") + b" comment\n",
            key_type + b" " + encoded + b"=\n",
            key_type + b" " + base64.b64encode(mismatched_blob) + b"\n",
            b"ssh-rsa " + encoded + b"\n",
        )
        for payload in cases:
            with self.subTest(payload=payload[:80]):
                with self.assertRaises(TOOL.HeadlessRootError):
                    TOOL.authorized_key_fingerprint(payload)

    def test_ssh_v2_rejects_unsafe_key_metadata(self) -> None:
        cases = (
            "parent-mode",
            "parent-symlink",
            "directory-mode",
            "file-mode",
            "hard-link",
        )
        for case in cases:
            with self.subTest(case=case):
                self.tearDown()
                self.setUp()
                self.write_ssh_v2_build()
                authorized_keys = self.root / TOOL.AUTHORIZED_KEYS_PATH
                ssh_parent = authorized_keys.parent.parent
                if case == "parent-mode":
                    ssh_parent.chmod(0o777)
                elif case == "parent-symlink":
                    real_parent = ssh_parent.with_name("root.real")
                    ssh_parent.rename(real_parent)
                    ssh_parent.symlink_to(real_parent.name)
                elif case == "directory-mode":
                    authorized_keys.parent.chmod(0o755)
                elif case == "file-mode":
                    authorized_keys.chmod(0o644)
                else:
                    authorized_keys.with_name(
                        "authorized_keys.copy"
                    ).hardlink_to(authorized_keys)
                with self.assertRaises(TOOL.HeadlessRootError):
                    TOOL.validate_build(
                        self.root,
                        self.root.stat().st_uid,
                        "headless-ssh-v2",
                    )

    def test_ssh_v2_identity_cannot_be_downgraded_to_v2(self) -> None:
        self.write_ssh_v2_build()
        self.prepare_package("headless-ssh-v2")
        payload = self.package.read_bytes()
        malformed_downgrade = payload.replace(
            b"format=rog5-headless-network-root-package-v3\n",
            b"format=rog5-headless-network-root-package-v2\n",
        )
        self.write_fixed(self.package, malformed_downgrade)
        with self.assertRaises(TOOL.HeadlessRootError):
            TOOL.parse_canonical_variant(
                self.package,
                TOOL.PACKAGE_FORMATS,
                owner=self.package.stat().st_uid,
                mode=0o444,
            )

        structural_downgrade = (
            payload.replace(
                b"format=rog5-headless-network-root-package-v3\n",
                b"format=rog5-headless-network-root-package-v2\n",
            )
            .replace(
                b"build_profile=headless-ssh-v2\n",
                b"build_profile=headless-core-v2\n",
            )
            .replace(
                (
                    b"authorized_key_fingerprint="
                    + FIXTURE_FINGERPRINT.encode("ascii")
                    + b"\n"
                ),
                b"",
            )
        )
        self.write_fixed(self.package, structural_downgrade)
        with self.assertRaises(TOOL.HeadlessRootError):
            TOOL.verify_root(self.root, self.package)

    def test_variant_dispatch_rejects_malformed_and_cross_version_records(
        self,
    ) -> None:
        self.prepare_package()
        v1 = self.package.read_bytes()
        v2 = v1.replace(
            b"format=rog5-headless-network-root-package-v1\n",
            b"format=rog5-headless-network-root-package-v2\n",
        ).replace(
            b"profile=network-root-v1\n",
            b"profile=network-root-v1\nbuild_profile=headless-core-v2\n",
        )
        cases = (
            b"profile=network-root-v1\n",
            b"format=\xff\n",
            b"format=rog5-headless-network-root-package-v9\n",
            v1.replace(
                b"format=rog5-headless-network-root-package-v1\n",
                b"format=rog5-headless-network-root-package-v2\n",
            ),
            v2.replace(
                b"format=rog5-headless-network-root-package-v2\n",
                b"format=rog5-headless-network-root-package-v1\n",
            ),
        )
        for payload in cases:
            with self.subTest(payload=payload[:80]):
                self.write_fixed(self.package, payload)
                with self.assertRaises(TOOL.HeadlessRootError):
                    TOOL.parse_canonical_variant(
                        self.package,
                        TOOL.PACKAGE_FORMATS,
                        owner=self.package.stat().st_uid,
                        mode=0o444,
                    )

    def test_v1_package_cannot_verify_a_headless_core_root(self) -> None:
        self.prepare_package()
        self.write_core_build()
        with self.assertRaises(TOOL.HeadlessRootError):
            TOOL.verify_root(self.root, self.package)

    def test_v1_package_cannot_verify_an_ssh_v2_root(self) -> None:
        self.prepare_package()
        self.write_ssh_v2_build()
        with self.assertRaises(TOOL.HeadlessRootError):
            TOOL.verify_root(self.root, self.package)

    def test_tree_archive_and_command_mutations_refuse(self) -> None:
        cases = ("tree", "archive", "command")
        for case in cases:
            with self.subTest(case=case):
                self.tearDown()
                self.setUp()
                self.prepare_package()
                if case == "tree":
                    (self.root / "usr/lib/rog5/payload").write_text(
                        "changed\n",
                        encoding="ascii",
                    )
                elif case == "archive":
                    with self.archive.open("ab") as stream:
                        stream.write(b"x")
                else:
                    installed = self.root / "etc/rog5/a660-command-manifest"
                    installed.chmod(0o600)
                    installed.write_text(
                        "format=rog5-headless-command-manifest-v1\n"
                        "workload=gpu\n",
                        encoding="ascii",
                    )
                    installed.chmod(0o400)
                with self.assertRaises(
                    (TOOL.HeadlessRootError, TOOL.ROOT_TOOL.ContractError)
                ):
                    TOOL.verify(
                        self.root,
                        self.archive,
                        self.package,
                        COMMAND,
                    )

    def test_host_export_surface_is_fixed_and_non_destructive(self) -> None:
        for script in (INSTALLER, EXPORT_VERIFIER, SERVER):
            source = script.read_text(encoding="utf-8")
            self.assertNotRegex(
                source,
                r"\b(fastboot|adb|flash|mkfs|wipefs|blkdiscard)\b",
            )
        installer = INSTALLER.read_text(encoding="utf-8")
        self.assertIn(
            "destination=/var/lib/rog5-headless-network-root-v1",
            installer,
        )
        self.assertIn("refusing existing headless export", installer)
        self.assertIn('verify-root "$stage/root" "$stage/manifest"', installer)
        self.assertIn(
            "/var/lib/rog5-headless-network-root-v1/root)",
            SERVER.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
