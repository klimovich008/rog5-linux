#!/usr/bin/env python3
"""Hostile offline tests for the fixed v3 deployment-export installer."""

from __future__ import annotations

import base64
from collections import OrderedDict
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
INSTALLER_PATH = (
    REPO / "scripts/host/install-headless-ssh-deployment-export.py"
)
TOOL_PATH = REPO / "scripts/host/headless-network-root.py"
COMMAND = REPO / "packaging/arch/rog5-headless-command-manifest"
FIXTURE = REPO / "configs/ssh/rog5-headless-build-fixture.pub"


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module("rog5_export_install_test_headless", TOOL_PATH)
INSTALLER = load_module("rog5_export_install_test", INSTALLER_PATH)
FIXTURE_KEY = b" ".join(FIXTURE.read_bytes().strip().split()[:2]) + b"\n"


def ed25519_key(byte: int) -> bytes:
    algorithm = b"ssh-ed25519"
    blob = (
        len(algorithm).to_bytes(4, "big")
        + algorithm
        + (32).to_bytes(4, "big")
        + bytes((byte,)) * 32
    )
    return algorithm + b" " + base64.b64encode(blob) + b"\n"


class DeploymentExportInstallerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-deployment-export-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "root"
        self.archive = self.directory / "root.tar.gz"
        self.identity = self.directory / "root.identity"
        self.package = self.directory / "root.package"
        self.destination = self.directory / "installed-v3"
        self.lock = self.directory / "install.lock"
        self.key = ed25519_key(0x5A)
        self.prepare_package()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def prepare_package(
        self,
        *,
        key: bytes | None = None,
        build_profile: str = "headless-ssh-v2",
    ) -> None:
        selected_key = self.key if key is None else key
        (self.root / "etc/rog5").mkdir(parents=True)
        (self.root / "usr/lib/rog5").mkdir(parents=True)
        (self.root / "usr/lib/rog5/payload").write_text(
            "deployment fixture\n",
            encoding="ascii",
        )
        if build_profile == "headless-ssh-v2":
            ssh_directory = self.root / "root/.ssh"
            ssh_directory.mkdir(parents=True)
            ssh_directory.chmod(0o700)
            authorized_keys = ssh_directory / "authorized_keys"
            authorized_keys.write_bytes(selected_key)
            authorized_keys.chmod(0o600)
            fingerprint = TOOL.authorized_key_fingerprint(selected_key)
            build = (
                "profile=headless-ssh-v2\n"
                "project_commit=000acc638ec851b1b02a2f3151db5265ab9213e7\n"
                f"rootfs_sha256={'a' * 64}\n"
                f"modules_sha256={'b' * 64}\n"
                "kernel_release=7.1.4-g7a5cef0db479\n"
                f"authorized_key_fingerprint={fingerprint}\n"
            )
        else:
            build = (
                "profile=headless-ssh-v1\n"
                "project_commit=eb61a45938c851b1b02a2f3151db5265ab9213e7\n"
                f"rootfs_sha256={'a' * 64}\n"
                f"modules_sha256={'b' * 64}\n"
                "kernel_release=7.1.4-g7a5cef0db479\n"
            )
        (self.root / "etc/rog5/build").write_text(
            build,
            encoding="ascii",
        )
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
                "/usr/bin/bsdtar",
                "--acls",
                "--xattrs",
                "--fflags",
                "-czpf",
                str(self.archive),
                "-C",
                str(self.directory),
                "root",
            ],
            check=True,
        )
        TOOL.package(self.identity, self.archive, self.package)
        self.archive.chmod(0o400)
        self.package.chmod(0o444)
        self.package_sha256 = hashlib.sha256(
            self.package.read_bytes()
        ).hexdigest()

    def install(self):
        return INSTALLER.install_export(
            self.archive,
            self.package,
            self.package_sha256,
            owner=os.geteuid(),
            group=os.getegid(),
            destination=self.destination,
            lock_path=self.lock,
        )

    def replace_package(self, values: OrderedDict[str, str]) -> None:
        self.package.chmod(0o600)
        self.package.write_bytes(TOOL.canonical_bytes(values))
        self.package.chmod(0o444)
        self.package_sha256 = hashlib.sha256(
            self.package.read_bytes()
        ).hexdigest()

    def bind_archive(self, archive: Path) -> None:
        values = TOOL.parse_canonical_variant(
            self.package,
            TOOL.PACKAGE_FORMATS,
            owner=os.geteuid(),
            mode=0o444,
        )
        values["sealed_archive_size"] = str(archive.stat().st_size)
        values["sealed_archive_sha256"] = hashlib.sha256(
            archive.read_bytes()
        ).hexdigest()
        self.replace_package(values)

    def test_nonfixture_export_installs_once_and_verifies(self) -> None:
        values = self.install()
        self.assertEqual(values["build_profile"], "headless-ssh-v2")
        self.assertTrue(self.destination.is_dir())
        self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o700)
        manifest = self.destination / "manifest"
        self.assertEqual(stat.S_IMODE(manifest.stat().st_mode), 0o444)
        verified = TOOL.verify_root(self.destination / "root", manifest)
        self.assertEqual(dict(verified), dict(values))
        with self.assertRaisesRegex(
            INSTALLER.ExportInstallError,
            "existing deployment export",
        ):
            self.install()

    def test_fixture_fingerprint_is_rejected(self) -> None:
        self.tearDown()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-deployment-export-fixture-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "root"
        self.archive = self.directory / "root.tar.gz"
        self.identity = self.directory / "root.identity"
        self.package = self.directory / "root.package"
        self.destination = self.directory / "installed-v3"
        self.lock = self.directory / "install.lock"
        self.key = FIXTURE_KEY
        self.prepare_package(key=FIXTURE_KEY)
        with self.assertRaisesRegex(
            INSTALLER.ExportInstallError,
            "fixture SSH identity",
        ):
            self.install()

    def test_historical_package_is_rejected(self) -> None:
        self.tearDown()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-deployment-export-v1-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "root"
        self.archive = self.directory / "root.tar.gz"
        self.identity = self.directory / "root.identity"
        self.package = self.directory / "root.package"
        self.destination = self.directory / "installed-v3"
        self.lock = self.directory / "install.lock"
        self.key = ed25519_key(0x5A)
        self.prepare_package(build_profile="headless-ssh-v1")
        with self.assertRaises(INSTALLER.HEADLESS.HeadlessRootError):
            self.install()

    def test_package_hash_and_archive_binding_are_exact(self) -> None:
        with self.assertRaisesRegex(
            INSTALLER.ExportInstallError,
            "package identity changed",
        ):
            INSTALLER.install_export(
                self.archive,
                self.package,
                "6" * 64,
                owner=os.geteuid(),
                group=os.getegid(),
                destination=self.destination,
                lock_path=self.lock,
            )
        self.archive.chmod(0o600)
        with self.archive.open("ab") as stream:
            stream.write(b"changed")
        self.archive.chmod(0o400)
        with self.assertRaisesRegex(
            INSTALLER.ExportInstallError,
            "does not match the admitted package",
        ):
            self.install()

    def test_unsafe_input_metadata_is_rejected(self) -> None:
        cases = ("relative", "symlink", "hardlink", "mode", "parent")
        for case in cases:
            with self.subTest(case=case):
                path = self.archive
                linked = self.directory / "linked.tar.gz"
                if linked.exists() or linked.is_symlink():
                    linked.unlink()
                if case == "relative":
                    path = Path("root.tar.gz")
                elif case == "symlink":
                    linked.symlink_to(self.archive.name)
                    path = linked
                elif case == "hardlink":
                    linked.hardlink_to(self.archive)
                elif case == "mode":
                    self.archive.chmod(0o600)
                else:
                    self.directory.chmod(0o755)
                with self.assertRaisesRegex(
                    INSTALLER.ExportInstallError,
                    "deployment archive",
                ):
                    INSTALLER.install_export(
                        path,
                        self.package,
                        self.package_sha256,
                        owner=os.geteuid(),
                        group=os.getegid(),
                        destination=self.destination,
                        lock_path=self.lock,
                    )
                if linked.exists() or linked.is_symlink():
                    linked.unlink()
                self.archive.chmod(0o400)
                self.directory.chmod(0o700)

    def malicious_archive(self, kind: str) -> None:
        self.archive.chmod(0o600)
        with tarfile.open(self.archive, "w:gz") as archive:
            root = tarfile.TarInfo("root")
            if kind == "root-symlink":
                root.type = tarfile.SYMTYPE
                root.linkname = "/"
            else:
                root.type = tarfile.DIRTYPE
                root.mode = 0o700
            archive.addfile(root)
            if kind == "escape":
                member = tarfile.TarInfo("../escape")
                payload = b"escape\n"
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
            elif kind == "credential":
                member = tarfile.TarInfo(
                    "root/etc/ssh/ssh_host_ed25519_key"
                )
                payload = b"not-a-key\n"
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
            elif kind == "nested-symlink":
                member = tarfile.TarInfo("root/etc")
                member.type = tarfile.SYMTYPE
                member.linkname = "/etc"
                archive.addfile(member)
                child = tarfile.TarInfo("root/etc/unsafe")
                payload = b"unsafe\n"
                child.size = len(payload)
                archive.addfile(child, io.BytesIO(payload))
            elif kind == "root-symlink":
                child = tarfile.TarInfo("root/unsafe")
                payload = b"unsafe\n"
                child.size = len(payload)
                archive.addfile(child, io.BytesIO(payload))
            else:
                member = tarfile.TarInfo("root/dev/unsafe")
                member.type = tarfile.CHRTYPE
                member.devmajor = 1
                member.devminor = 3
                archive.addfile(member)
        self.archive.chmod(0o400)
        self.bind_archive(self.archive)

    def test_archive_preinspection_rejects_unsafe_members(self) -> None:
        for kind, message in (
            ("escape", "unsafe path"),
            ("credential", "forbidden credential"),
            ("nested-symlink", "writes through a symlink"),
            ("root-symlink", "fixed root directory"),
            ("device", "device or FIFO"),
        ):
            with self.subTest(kind=kind):
                self.tearDown()
                self.setUp()
                self.malicious_archive(kind)
                with self.assertRaisesRegex(
                    INSTALLER.ExportInstallError,
                    message,
                ):
                    self.install()
                self.assertFalse(self.destination.exists())

    def test_path_replacement_cannot_change_open_archive(self) -> None:
        real_run = subprocess.run
        original = self.directory / "opened-archive.tar.gz"

        def replace_then_extract(*arguments, **keywords):
            self.archive.rename(original)
            self.archive.write_bytes(b"replacement")
            self.archive.chmod(0o400)
            return real_run(*arguments, **keywords)

        with mock.patch.object(
            INSTALLER.subprocess,
            "run",
            side_effect=replace_then_extract,
        ):
            self.install()
        self.assertTrue((self.destination / "root").is_dir())
        self.assertEqual(self.archive.read_bytes(), b"replacement")

    def test_in_place_rewrite_cannot_change_private_archive_snapshot(
        self,
    ) -> None:
        real_extract = INSTALLER.extract_archive

        def rewrite_then_extract(descriptor: int, stage: Path) -> None:
            self.archive.chmod(0o600)
            self.archive.write_bytes(b"replacement")
            self.archive.chmod(0o400)
            real_extract(descriptor, stage)

        with mock.patch.object(
            INSTALLER,
            "extract_archive",
            side_effect=rewrite_then_extract,
        ):
            self.install()
        self.assertTrue((self.destination / "root").is_dir())
        self.assertEqual(self.archive.read_bytes(), b"replacement")

    def test_atomic_publication_never_replaces_a_racing_destination(
        self,
    ) -> None:
        real_rename = INSTALLER.rename_noreplace

        def race(source: Path, destination: Path) -> None:
            destination.mkdir()
            (destination / "owner").write_text("other\n", encoding="ascii")
            real_rename(source, destination)

        with (
            mock.patch.object(
                INSTALLER,
                "rename_noreplace",
                side_effect=race,
            ),
            self.assertRaisesRegex(
                INSTALLER.ExportInstallError,
                "existing deployment export",
            ),
        ):
            self.install()
        self.assertEqual(
            (self.destination / "owner").read_text(encoding="ascii"),
            "other\n",
        )

    def test_tree_is_synced_before_no_replace_publication(self) -> None:
        events: list[str] = []
        real_sync = INSTALLER.fsync_tree
        real_rename = INSTALLER.rename_noreplace

        def sync(root: Path) -> None:
            events.append("sync")
            real_sync(root)

        def rename(source: Path, destination: Path) -> None:
            events.append("rename")
            real_rename(source, destination)

        with (
            mock.patch.object(INSTALLER, "fsync_tree", side_effect=sync),
            mock.patch.object(
                INSTALLER,
                "rename_noreplace",
                side_effect=rename,
            ),
        ):
            self.install()
        self.assertEqual(events, ["sync", "rename"])

    def test_source_has_no_test_override_or_phone_mutation_surface(self) -> None:
        source = INSTALLER_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "ROG5_TEST",
            "fastboot",
            "adb",
            "flash",
            "mkfs",
            "wipefs",
            "blkdiscard",
            "dd ",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("renameat2", source)
        self.assertIn("RENAME_NOREPLACE", source)
        self.assertIn("/proc/self/fd/", source)
        self.assertIn("O_TMPFILE", source)
        self.assertIn("fsync_tree(stage)", source)
        self.assertIn("FIXTURE_IDENTITIES", source)


if __name__ == "__main__":
    unittest.main()
