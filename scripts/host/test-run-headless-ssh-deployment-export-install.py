#!/usr/bin/env python3
"""Offline tests for deployment admission-to-PolicyKit export launch."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
LAUNCHER_PATH = (
    REPO / "scripts/host/run-headless-ssh-deployment-export-install.py"
)
TOOL_PATH = REPO / "scripts/host/headless-network-root.py"
COMMAND = REPO / "packaging/arch/rog5-headless-command-manifest"
INSTALL_CONTROLLER = REPO / "scripts/host/install-recovery-host-controller.sh"


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module("rog5_export_launch_test_headless", TOOL_PATH)
LAUNCHER = load_module("rog5_export_launch_test", LAUNCHER_PATH)


def ed25519_key(byte: int) -> bytes:
    algorithm = b"ssh-ed25519"
    blob = (
        len(algorithm).to_bytes(4, "big")
        + algorithm
        + (32).to_bytes(4, "big")
        + bytes((byte,)) * 32
    )
    return algorithm + b" " + base64.b64encode(blob) + b"\n"


class DeploymentExportLaunchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-export-launch-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "root"
        self.archive = self.directory / "root.tar.gz"
        self.identity = self.directory / "root.identity"
        self.package = self.directory / "root.package"
        self.installed = self.directory / "installed"
        self.installed.mkdir()
        self.installed.chmod(0o700)
        self.prepare_package()
        self.install_components()
        self.private_key = self.directory / "deployment-key"
        self.candidate = self.directory / "candidate.json"
        self.manifest = self.directory / "manifest"
        self.pkexec = self.directory / "pkexec"

    def prepare_package(self) -> None:
        key = ed25519_key(0x5A)
        (self.root / "etc/rog5").mkdir(parents=True)
        (self.root / "usr/lib/rog5").mkdir(parents=True)
        (self.root / "usr/lib/rog5/payload").write_text(
            "deployment launch fixture\n",
            encoding="ascii",
        )
        ssh_directory = self.root / "root/.ssh"
        ssh_directory.mkdir(parents=True)
        ssh_directory.chmod(0o700)
        authorized_keys = ssh_directory / "authorized_keys"
        authorized_keys.write_bytes(key)
        authorized_keys.chmod(0o600)
        fingerprint = TOOL.authorized_key_fingerprint(key)
        (self.root / "etc/rog5/build").write_text(
            "profile=headless-ssh-v2\n"
            "project_commit=000acc638ec851b1b02a2f3151db5265ab9213e7\n"
            f"rootfs_sha256={'a' * 64}\n"
            f"modules_sha256={'b' * 64}\n"
            "kernel_release=7.1.4-g7a5cef0db479\n"
            f"authorized_key_fingerprint={fingerprint}\n",
            encoding="ascii",
        )
        TOOL.prepare(
            self.root,
            "123",
            "c" * 64,
            COMMAND,
            self.identity,
            "headless-ssh-v2",
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

    def install_components(self) -> None:
        for source in (
            LAUNCHER.INSTALLER_SOURCE,
            LAUNCHER.HEADLESS_SOURCE,
            LAUNCHER.ROOT_TOOL_SOURCE,
        ):
            destination = self.installed / source.name
            shutil.copyfile(source, destination)
            destination.chmod(0o555)

    def command(self) -> list[str]:
        return LAUNCHER.admitted_install_command(
            self.private_key,
            self.archive,
            self.package,
            self.candidate,
            self.manifest,
            "7" * 64,
            installed_root=self.installed,
            installed_owner=os.geteuid(),
            pkexec=self.pkexec,
        )

    def test_exact_admission_result_enters_only_fixed_installer(self) -> None:
        with mock.patch.object(
            LAUNCHER.ADMISSION,
            "verify",
            return_value={"package_sha256": self.package_sha256},
        ) as admission:
            command = self.command()
        admission.assert_called_once_with(
            self.private_key,
            self.package,
            self.candidate,
            self.manifest,
            "7" * 64,
        )
        self.assertEqual(
            command,
            [
                str(self.pkexec),
                str(
                    self.installed
                    / "install-headless-ssh-deployment-export.py"
                ),
                str(self.archive),
                str(self.package),
                self.package_sha256,
            ],
        )
        self.assertNotIn(str(self.private_key), command)
        self.assertNotIn(str(self.candidate), command)
        self.assertNotIn(str(self.manifest), command)

    def test_stale_installed_component_fails_before_key_admission(self) -> None:
        installer = (
            self.installed / "install-headless-ssh-deployment-export.py"
        )
        installer.chmod(0o755)
        with (
            mock.patch.object(LAUNCHER.ADMISSION, "verify") as admission,
            self.assertRaisesRegex(
                LAUNCHER.ExportLaunchError,
                "stale or unsafe",
            ),
        ):
            self.command()
        admission.assert_not_called()

    def test_admission_package_hash_mismatch_is_rejected(self) -> None:
        with (
            mock.patch.object(
                LAUNCHER.ADMISSION,
                "verify",
                return_value={"package_sha256": "8" * 64},
            ),
            self.assertRaisesRegex(
                LAUNCHER.ExportLaunchError,
                "identities diverged",
            ),
        ):
            self.command()

    def test_archive_mismatch_is_rejected_after_admission(self) -> None:
        self.archive.chmod(0o600)
        with self.archive.open("ab") as stream:
            stream.write(b"changed")
        self.archive.chmod(0o400)
        with (
            mock.patch.object(
                LAUNCHER.ADMISSION,
                "verify",
                return_value={"package_sha256": self.package_sha256},
            ),
            self.assertRaisesRegex(
                LAUNCHER.ExportLaunchError,
                "archive does not match",
            ),
        ):
            self.command()

    def test_guards_fail_before_argument_or_credential_inspection(self) -> None:
        result = subprocess.run(
            [sys.executable, str(LAUNCHER_PATH)],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                "PATH": "/usr/bin:/bin",
                "LC_ALL": "C",
            },
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "FAIL headless SSH deployment export launch refused",
            result.stderr,
        )

    def test_repository_checkpoint_requires_clean_exact_origin_peer(
        self,
    ) -> None:
        passing = [
            "",
            "agent/linux-recovery-host",
            "origin/agent/linux-recovery-host",
            "",
            "checkpoint",
            "checkpoint",
        ]
        with mock.patch.object(
            LAUNCHER,
            "git_output",
            side_effect=passing,
        ):
            LAUNCHER.verify_repository_checkpoint()
        dirty = passing.copy()
        dirty[0] = " M changed"
        with (
            mock.patch.object(
                LAUNCHER,
                "git_output",
                side_effect=dirty,
            ),
            self.assertRaisesRegex(
                LAUNCHER.ExportLaunchError,
                "repository must be clean",
            ),
        ):
            LAUNCHER.verify_repository_checkpoint()
        wrong_upstream = passing.copy()
        wrong_upstream[2] = "origin/other"
        with (
            mock.patch.object(
                LAUNCHER,
                "git_output",
                side_effect=wrong_upstream,
            ),
            self.assertRaisesRegex(
                LAUNCHER.ExportLaunchError,
                "origin peer",
            ),
        ):
            LAUNCHER.verify_repository_checkpoint()

    def test_repository_checkpoint_refreshes_stale_origin_before_comparison(
        self,
    ) -> None:
        fetched = False
        commands: list[tuple[str, ...]] = []

        def git_output(arguments: list[str]) -> str:
            nonlocal fetched
            command = tuple(arguments)
            commands.append(command)
            if command == ("status", "--porcelain", "--untracked-files=all"):
                return ""
            if command == ("branch", "--show-current"):
                return "agent/linux-recovery-host"
            if command == (
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ):
                return "origin/agent/linux-recovery-host"
            if command == (
                "fetch",
                "--no-tags",
                "--prune",
                "origin",
                "refs/heads/agent/linux-recovery-host:"
                "refs/remotes/origin/agent/linux-recovery-host",
            ):
                fetched = True
                return ""
            if command == ("rev-parse", "HEAD"):
                return "stale-checkpoint"
            if command == (
                "rev-parse",
                "origin/agent/linux-recovery-host",
            ):
                return (
                    "fresh-remote-checkpoint"
                    if fetched
                    else "stale-checkpoint"
                )
            self.fail(f"unexpected git command: {command}")

        with (
            mock.patch.object(
                LAUNCHER,
                "git_output",
                side_effect=git_output,
            ),
            self.assertRaisesRegex(
                LAUNCHER.ExportLaunchError,
                "local and remote-tracking checkpoints differ",
            ),
        ):
            LAUNCHER.verify_repository_checkpoint()

        self.assertTrue(fetched)
        fetch_index = next(
            index
            for index, command in enumerate(commands)
            if command and command[0] == "fetch"
        )
        remote_index = commands.index(
            ("rev-parse", "origin/agent/linux-recovery-host")
        )
        self.assertLess(fetch_index, remote_index)

    def test_installer_is_part_of_fixed_host_controller_install(self) -> None:
        source = INSTALL_CONTROLLER.read_text(encoding="utf-8")
        self.assertIn(
            "install-headless-ssh-deployment-export.py",
            source,
        )
        self.assertIn(
            '"$deployment_export_installer_source"',
            source,
        )
        self.assertIn(
            '"$deployment_export_installer_temporary"',
            source,
        )

    def test_source_excludes_phone_and_root_credential_surfaces(self) -> None:
        source = LAUNCHER_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "fastboot",
            "adb",
            "flash",
            "sudo",
            "SSH_ASKPASS",
            "password",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("ALLOW_HEADLESS_SSH_EXPORT_INSTALL", source)
        self.assertIn("ALLOW_HEADLESS_SSH_KEY_ADMISSION", source)
        self.assertIn("ALLOW_PHONE_CREDENTIAL_USE", source)
        self.assertIn("os.execv(command[0], command)", source)


if __name__ == "__main__":
    unittest.main()
