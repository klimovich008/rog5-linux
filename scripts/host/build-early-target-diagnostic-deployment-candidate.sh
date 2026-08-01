#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Launch one exact diagnostic deployment build across a clean boundary."""

from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import stat
import subprocess


GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_OPTIONAL_LOCKS": "0",
}
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
REQUIRED_SEALS = (
    getattr(fcntl, "F_SEAL_SEAL", 0x0001)
    | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
    | getattr(fcntl, "F_SEAL_GROW", 0x0004)
    | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
)
IMPLEMENTATION_REPOSITORY_PATH = (
    "scripts/host/build-corrected-headless-candidate-offline-impl.sh"
)


def git_output(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(repository),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=GIT_ENV,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("FAIL cannot verify the deployment-launcher checkpoint")
    return result.stdout.strip()


def git_bytes(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        [
            "/usr/bin/git",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(repository),
            *arguments,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=GIT_ENV,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("FAIL cannot read the deployment implementation blob")
    return result.stdout


def sealed_implementation(repository: Path, implementation: Path) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    source = os.open(implementation, flags)
    sealed = -1
    try:
        before = os.fstat(source)
        expected = git_bytes(
            repository,
            "show",
            f"HEAD:{IMPLEMENTATION_REPOSITORY_PATH}",
        )
        payload = bytearray()
        while True:
            block = os.read(source, 1024 * 1024)
            if not block:
                break
            payload.extend(block)
        after = os.fstat(source)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or bytes(payload) != expected
        ):
            raise SystemExit("FAIL deployment implementation differs from HEAD")
        sealed = os.memfd_create(
            "rog5-deployment-builder",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        view = memoryview(payload)
        while view:
            written = os.write(sealed, view)
            if written <= 0:
                raise SystemExit("FAIL deployment implementation snapshot stalled")
            view = view[written:]
        os.fchmod(sealed, 0o555)
        fcntl.fcntl(sealed, F_ADD_SEALS, REQUIRED_SEALS)
        if fcntl.fcntl(sealed, F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS:
            raise SystemExit("FAIL deployment implementation snapshot is unsealed")
        os.set_inheritable(sealed, True)
        return sealed
    except BaseException:
        if sealed >= 0:
            os.close(sealed)
        raise
    finally:
        os.close(source)


def verified_implementation() -> tuple[Path, int]:
    lexical = Path(os.path.abspath(__file__))
    resolved = lexical.resolve(strict=True)
    repository = resolved.parents[2]
    implementation = resolved.with_name(
        "build-corrected-headless-candidate-offline-impl.sh"
    )
    for path, expected_type in (
        (repository, stat.S_ISDIR),
        (repository / "scripts", stat.S_ISDIR),
        (resolved.parent, stat.S_ISDIR),
        (resolved, stat.S_ISREG),
        (implementation, stat.S_ISREG),
    ):
        metadata = path.lstat()
        if (
            path.resolve(strict=True) != path
            or stat.S_ISLNK(metadata.st_mode)
            or not expected_type(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_gid != os.getegid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise SystemExit("FAIL deployment-launcher filesystem metadata is unsafe")
    if git_output(repository, "status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("FAIL repository must be clean before deployment signing")
    branch = git_output(repository, "branch", "--show-current")
    upstream = git_output(
        repository,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    if not branch or upstream != f"origin/{branch}":
        raise SystemExit("FAIL deployment-signing branch has no exact origin peer")
    if git_output(repository, "rev-parse", "HEAD") != git_output(
        repository, "rev-parse", upstream
    ):
        raise SystemExit("FAIL deployment-signing checkpoint differs from origin")
    return repository, sealed_implementation(repository, implementation)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorize-recovery-deployment-build", action="store_true")
    parser.add_argument("--authorize-phone-credential-use", action="store_true")
    parser.add_argument("--candidate-record", required=True)
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--signing-input-preflight", action="store_true")
    parser.add_argument("output_root")
    arguments = parser.parse_args()
    if not arguments.authorize_recovery_deployment_build:
        parser.error(
            "set --authorize-recovery-deployment-build for one signed recovery build"
        )
    if not arguments.authorize_phone_credential_use:
        parser.error("set --authorize-phone-credential-use before using the signing key")
    return arguments


def main() -> None:
    arguments = parse_arguments()
    repository, implementation_fd = verified_implementation()
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "ROG5_INTERNAL_REPOSITORY_ROOT": str(repository),
        "ROG5_INTERNAL_IMPLEMENTATION_SEALED": "1",
        "ALLOW_RECOVERY_DEPLOYMENT_BUILD": "1",
        "ALLOW_PHONE_CREDENTIAL_USE": "1",
        "ROG5_DEPLOYMENT_CANDIDATE_RECORD": arguments.candidate_record,
        "ROG5_DEPLOYMENT_SIGNING_KEY": arguments.signing_key,
        "ROG5_DEPLOYMENT_BUILD": "1",
        "ROG5_DEPLOYMENT_SIGNING_INPUT_PREFLIGHT": (
            "1" if arguments.signing_input_preflight else "0"
        ),
        "ROG5_OFFLINE_CANDIDATE": "headless-netroot-early-diag-v1",
        "ROG5_OFFLINE_EXPECTED_DTB": (
            "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
        ),
        "ROG5_OFFLINE_EXPECTED_TARGET": "headless-netroot-early-diag",
    }
    os.execve(
        "/usr/bin/bash",
        [
            "/usr/bin/bash",
            "--noprofile",
            "--norc",
            f"/proc/self/fd/{implementation_fd}",
            arguments.output_root,
        ],
        environment,
    )


if __name__ == "__main__":
    main()
