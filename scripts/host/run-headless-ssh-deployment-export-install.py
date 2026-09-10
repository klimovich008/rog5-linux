#!/usr/bin/env python3
"""Admit one deployment key chain, then enter the fixed export installer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
ADMISSION_PATH = REPO / "scripts/host/verify-headless-ssh-v2-key-admission.py"
INSTALLER_SOURCE = (
    REPO / "scripts/host/install-headless-ssh-deployment-export.py"
)
HEADLESS_SOURCE = REPO / "scripts/host/headless-network-root.py"
ROOT_TOOL_SOURCE = REPO / "scripts/device/persistent-root-tool.py"
INSTALLED_ROOT = Path("/usr/libexec/rog5-recovery-host")
INSTALLED_INSTALLER = INSTALLED_ROOT / INSTALLER_SOURCE.name
GIT = Path("/usr/bin/git")
PKEXEC = Path("/usr/bin/pkexec")


class ExportLaunchError(RuntimeError):
    """A stable refusal before privileged export installation."""


def fail(message: str) -> NoReturn:
    raise ExportLaunchError(message)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        fail("cannot load a fixed export-install verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


ADMISSION = load_module("rog5_export_install_admission", ADMISSION_PATH)
INSTALLER = load_module("rog5_export_install_contract", INSTALLER_SOURCE)


def executable(path: Path, label: str, mode: int) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ExportLaunchError(f"{label} is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_nlink != 1
    ):
        fail(f"{label} metadata is unsafe")


def git_output(arguments: list[str]) -> str:
    result = subprocess.run(
        [str(GIT), "-C", str(REPO), *arguments],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env={
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
        },
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        fail("cannot verify the repository checkpoint")
    return result.stdout.strip()


def verify_repository_checkpoint() -> None:
    if git_output(["status", "--porcelain", "--untracked-files=all"]):
        fail("repository must be clean before export installation")
    branch = git_output(["branch", "--show-current"])
    if not branch:
        fail("repository is not on a branch")
    upstream = git_output(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
    )
    if upstream != f"origin/{branch}":
        fail("export-install branch does not track its origin peer")
    git_output(
        [
            "fetch",
            "--no-tags",
            "--prune",
            "origin",
            f"refs/heads/{branch}:refs/remotes/origin/{branch}",
        ]
    )
    if git_output(["rev-parse", "HEAD"]) != git_output(
        ["rev-parse", upstream]
    ):
        fail("local and remote-tracking checkpoints differ")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def installed_components(
    installed_root: Path = INSTALLED_ROOT,
    *,
    owner: int = 0,
) -> Path:
    expected_group = os.getegid() if owner != 0 else 0
    expected = (
        (
            installed_root / INSTALLER_SOURCE.name,
            INSTALLER_SOURCE,
        ),
        (
            installed_root / HEADLESS_SOURCE.name,
            HEADLESS_SOURCE,
        ),
        (
            installed_root / ROOT_TOOL_SOURCE.name,
            ROOT_TOOL_SOURCE,
        ),
    )
    for installed, source in expected:
        try:
            metadata = installed.lstat()
        except OSError as error:
            raise ExportLaunchError(
                "fixed export-install component is unavailable"
            ) from error
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != owner
            or metadata.st_gid != expected_group
            or stat.S_IMODE(metadata.st_mode) != 0o555
            or metadata.st_nlink != 1
            or file_sha256(installed) != file_sha256(source)
        ):
            fail("fixed export-install component is stale or unsafe")
    return expected[0][0]


def admitted_install_command(
    private_key: Path,
    archive_path: Path,
    package_path: Path,
    candidate_path: Path,
    manifest_path: Path,
    manifest_sha256: str,
    *,
    installed_root: Path = INSTALLED_ROOT,
    installed_owner: int = 0,
    pkexec: Path = PKEXEC,
) -> list[str]:
    installed = installed_components(
        installed_root,
        owner=installed_owner,
    )
    archive = INSTALLER.canonical_input(
        archive_path,
        owner=os.geteuid(),
        group=os.getegid(),
        label="deployment archive",
    )
    package = INSTALLER.canonical_input(
        package_path,
        owner=os.geteuid(),
        group=os.getegid(),
        label="deployment package",
    )
    admitted = ADMISSION.verify(
        private_key,
        package,
        candidate_path,
        manifest_path,
        manifest_sha256,
    )
    package_values, package_payload = ADMISSION.parse_package(package)
    if (
        hashlib.sha256(package_payload).hexdigest()
        != admitted["package_sha256"]
    ):
        fail("admission and package identities diverged")
    archive_descriptor = INSTALLER.open_input(archive)
    try:
        archive_size, archive_sha256 = INSTALLER.hash_descriptor(
            archive_descriptor,
            archive,
        )
    finally:
        os.close(archive_descriptor)
    if (
        str(archive_size) != package_values["sealed_archive_size"]
        or archive_sha256 != package_values["sealed_archive_sha256"]
    ):
        fail("deployment archive does not match the admitted package")
    return [
        str(pkexec),
        str(installed),
        str(archive),
        str(package),
        admitted["package_sha256"],
    ]


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    try:
        if os.environ.get("ALLOW_HEADLESS_SSH_EXPORT_INSTALL") != "1":
            fail("set ALLOW_HEADLESS_SSH_EXPORT_INSTALL=1 for one host install")
        if os.environ.get("ALLOW_HEADLESS_SSH_KEY_ADMISSION") != "1":
            fail("set ALLOW_HEADLESS_SSH_KEY_ADMISSION=1 for key admission")
        if os.environ.get("ALLOW_PHONE_CREDENTIAL_USE") != "1":
            fail("set ALLOW_PHONE_CREDENTIAL_USE=1 before using the key")
        options = parse_arguments(
            sys.argv[1:] if arguments is None else arguments
        )
        executable(GIT, "fixed Git", 0o755)
        executable(PKEXEC, "fixed PolicyKit launcher", 0o4755)
        verify_repository_checkpoint()
        command = admitted_install_command(
            options.private_key,
            options.archive,
            options.package,
            options.candidate,
            options.manifest,
            options.manifest_sha256,
        )
    except (
        ExportLaunchError,
        ADMISSION.AdmissionError,
        ADMISSION.HEADLESS.HeadlessRootError,
        ADMISSION.CANDIDATE.CandidateError,
        INSTALLER.ExportInstallError,
        OSError,
        subprocess.SubprocessError,
    ):
        print(
            "FAIL headless SSH deployment export launch refused",
            file=sys.stderr,
        )
        return 1
    os.execv(command[0], command)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
