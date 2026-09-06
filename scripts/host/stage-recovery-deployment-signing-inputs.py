#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Verify and privately snapshot one deployment signing input pair."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, NoReturn


SOURCE_REPO = Path(__file__).resolve().parents[2]
CANDIDATE_PATH = SOURCE_REPO / "scripts/host/prepare-recovery-candidate.py"
DEFAULT_CANDIDATE_ID = "headless-ssh-network-root-v3"
CORE_CANDIDATE_ID = "headless-core-network-root-v2"
DIAGNOSTIC_CANDIDATE_ID = "headless-netroot-early-diag-v2"
POWER_USB_LOCK = json.loads(
    (SOURCE_REPO / "manifests/power-usb-active.lock.json").read_text(
        encoding="ascii"
    )
)
POWER_CANDIDATE_ID = POWER_USB_LOCK["candidate"]
ALLOWED_CANDIDATE_IDS = (
    DEFAULT_CANDIDATE_ID,
    CORE_CANDIDATE_ID,
    DIAGNOSTIC_CANDIDATE_ID,
    POWER_CANDIDATE_ID,
)
EXACT_CANDIDATE_SHA256 = {
    DIAGNOSTIC_CANDIDATE_ID: (
        "f23626d6ad0b15a660835bd8419cde40a8f8c3c79f83b6feca5cb57952f7b1ab"
    ),
    POWER_CANDIDATE_ID: POWER_USB_LOCK["candidate_sha256"],
}
GIT = Path("/usr/bin/git")
OPENSSL = Path("/usr/bin/openssl")
ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
MAXIMUM_INPUT = 64 * 1024
SUBPROCESS_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
}
OPENSSL_ENV = {
    **SUBPROCESS_ENV,
    "OPENSSL_CONF": "/dev/null",
}


class SigningInputError(RuntimeError):
    """A stable refusal that does not expose credential bytes."""


def fail(message: str) -> NoReturn:
    raise SigningInputError(message)


def load_candidate_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_deployment_signing_candidate",
        CANDIDATE_PATH,
    )
    if specification is None or specification.loader is None:
        fail("cannot load the fixed candidate verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


CANDIDATE = load_candidate_module()


def identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def outside_repository(path: Path, repository: Path, label: str) -> None:
    try:
        path.relative_to(repository)
    except ValueError:
        return
    fail(f"{label} must remain outside the repository")


def canonical_repository(path: Path) -> Path:
    if not path.is_absolute():
        fail("repository path must be absolute")
    lexical = Path(os.path.abspath(path))
    try:
        resolved = lexical.resolve(strict=True)
        metadata = lexical.lstat()
    except OSError as error:
        raise SigningInputError("repository is unavailable") from error
    if (
        lexical != resolved
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
    ):
        fail("repository metadata is unsafe")
    return resolved


def git_output(repository: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        [str(GIT), "-C", str(repository), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=SUBPROCESS_ENV,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        fail("cannot verify the repository checkpoint")
    return result.stdout.strip()


def verify_repository_checkpoint(repository: Path) -> str:
    if git_output(
        repository,
        ["status", "--porcelain", "--untracked-files=all"],
    ):
        fail("repository must be clean before deployment signing")
    branch = git_output(repository, ["branch", "--show-current"])
    if not branch:
        fail("repository is not on a branch")
    upstream = git_output(
        repository,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
    )
    if upstream != f"origin/{branch}":
        fail("deployment-signing branch does not track its origin peer")
    git_output(
        repository,
        [
            "fetch",
            "--no-tags",
            "--prune",
            "origin",
            f"refs/heads/{branch}:refs/remotes/origin/{branch}",
        ],
    )
    checkpoint = git_output(repository, ["rev-parse", "HEAD"])
    if checkpoint != git_output(repository, ["rev-parse", upstream]):
        fail("deployment-signing checkpoint differs from its origin peer")
    if len(checkpoint) != 40:
        fail("deployment-signing checkpoint is malformed")
    return checkpoint


def private_parent(
    path: Path,
    repository: Path,
    label: str,
) -> Path:
    if not path.is_absolute():
        fail(f"{label} path must be absolute")
    lexical = Path(os.path.abspath(path))
    parent = lexical.parent
    try:
        named = parent.lstat()
        resolved = parent.resolve(strict=True)
        resolved_metadata = resolved.lstat()
    except OSError as error:
        raise SigningInputError(f"{label} parent is unavailable") from error
    if (
        parent != resolved
        or stat.S_ISLNK(named.st_mode)
        or identity(named) != identity(resolved_metadata)
        or not stat.S_ISDIR(named.st_mode)
        or named.st_uid != os.geteuid()
        or named.st_gid != os.getegid()
        or stat.S_IMODE(named.st_mode) != 0o700
    ):
        fail(f"{label} parent metadata is unsafe")
    outside_repository(resolved, repository, f"{label} parent")
    return lexical


def read_private_input(
    path: Path,
    repository: Path,
    label: str,
    mode: int,
) -> bytes:
    lexical = private_parent(path, repository, label)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lexical, flags)
    except OSError as error:
        raise SigningInputError(f"{label} is unavailable") from error
    try:
        before = os.fstat(descriptor)
        try:
            named = lexical.lstat()
        except OSError as error:
            raise SigningInputError(f"{label} is unavailable") from error
        if (
            identity(before) != identity(named)
            or not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_size < 1
            or before.st_size > MAXIMUM_INPUT
        ):
            fail(f"{label} metadata is unsafe")
        payload = bytearray()
        while len(payload) <= MAXIMUM_INPUT:
            block = os.read(
                descriptor,
                min(65536, MAXIMUM_INPUT + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        try:
            named_after = lexical.lstat()
        except OSError as error:
            raise SigningInputError(
                f"{label} disappeared while being read"
            ) from error
        if (
            len(payload) != before.st_size
            or identity(before) != identity(after)
            or identity(before) != identity(named_after)
        ):
            fail(f"{label} changed while being read")
        return bytes(payload)
    finally:
        os.close(descriptor)


@dataclass
class OutputReservation:
    path: Path
    descriptor: int
    created: os.stat_result
    mode: int
    label: str


def reserve_output(
    path: Path,
    repository: Path,
    mode: int,
    label: str,
) -> OutputReservation:
    output = private_parent(path, repository, label)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    created: os.stat_result | None = None
    try:
        descriptor = os.open(output, flags, mode)
        created = os.fstat(descriptor)
        os.fchmod(descriptor, mode)
        configured = os.fstat(descriptor)
        if (
            created.st_dev != configured.st_dev
            or created.st_ino != configured.st_ino
            or not stat.S_ISREG(configured.st_mode)
            or configured.st_uid != os.geteuid()
            or configured.st_gid != os.getegid()
            or configured.st_nlink != 1
            or stat.S_IMODE(configured.st_mode) != mode
            or configured.st_size != 0
        ):
            fail(f"{label} reservation metadata is unsafe")
        return OutputReservation(
            path=output,
            descriptor=descriptor,
            created=created,
            mode=mode,
            label=label,
        )
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        if created is not None:
            try:
                named = output.lstat()
                if (
                    named.st_dev == created.st_dev
                    and named.st_ino == created.st_ino
                    and named.st_uid == created.st_uid
                    and named.st_gid == created.st_gid
                    and stat.S_ISREG(named.st_mode)
                ):
                    output.unlink()
            except FileNotFoundError:
                pass
        raise


def reservation_is_owned(reservation: OutputReservation) -> bool:
    try:
        named = reservation.path.lstat()
    except FileNotFoundError:
        return False
    return (
        named.st_dev == reservation.created.st_dev
        and named.st_ino == reservation.created.st_ino
        and named.st_uid == reservation.created.st_uid
        and named.st_gid == reservation.created.st_gid
        and stat.S_ISREG(named.st_mode)
    )


def discard_reservation(reservation: OutputReservation) -> None:
    if reservation.descriptor >= 0:
        os.close(reservation.descriptor)
        reservation.descriptor = -1
    if reservation_is_owned(reservation):
        reservation.path.unlink()


def commit_reservation(
    reservation: OutputReservation,
    payload: bytes,
) -> Path:
    if reservation.descriptor < 0:
        fail(f"{reservation.label} reservation is closed")
    view = memoryview(payload)
    while view:
        written = os.write(reservation.descriptor, view)
        if written <= 0:
            fail(f"{reservation.label} write made no progress")
        view = view[written:]
    os.fchmod(reservation.descriptor, reservation.mode)
    os.fsync(reservation.descriptor)
    metadata = os.fstat(reservation.descriptor)
    if (
        not reservation_is_owned(reservation)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_gid != os.getegid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != reservation.mode
        or metadata.st_size != len(payload)
    ):
        fail(f"{reservation.label} output metadata is unsafe")
    os.close(reservation.descriptor)
    reservation.descriptor = -1
    return reservation.path


def sync_directory(path: Path) -> None:
    directory_descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def validate_candidate(payload: bytes, candidate_id: str) -> None:
    if candidate_id not in ALLOWED_CANDIDATE_IDS:
        fail("deployment candidate identity is not one fixed policy")
    try:
        record: dict[str, Any] = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=CANDIDATE.unique_object,
        )
    except (
        CANDIDATE.CandidateError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise SigningInputError("deployment candidate record is invalid") from error
    CANDIDATE.validate_external_candidate_record(record, candidate_id)
    expected_sha256 = EXACT_CANDIDATE_SHA256.get(candidate_id)
    if (
        expected_sha256 is not None
        and hashlib.sha256(payload).hexdigest() != expected_sha256
    ):
        fail("deployment diagnostic candidate identity changed")


def derive_ed25519_public(private_key: Path) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(private_key, flags)
    try:
        metadata = os.fstat(descriptor)
        payload = bytearray()
        while len(payload) <= MAXIMUM_INPUT:
            block = os.read(
                descriptor,
                min(65536, MAXIMUM_INPUT + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        if len(payload) != metadata.st_size:
            fail("staged deployment signing key changed")
        lines = bytes(payload).splitlines()
        if (
            len(lines) < 3
            or lines[0] != b"-----BEGIN PRIVATE KEY-----"
            or lines[-1] != b"-----END PRIVATE KEY-----"
        ):
            fail("deployment signing key is not unencrypted PKCS#8")
        os.lseek(descriptor, 0, os.SEEK_SET)
        parse = subprocess.run(
            [
                str(OPENSSL),
                "pkcs8",
                "-in",
                f"/proc/self/fd/{descriptor}",
                "-passin",
                "pass:",
                "-nocrypt",
                "-outform",
                "DER",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=OPENSSL_ENV,
            pass_fds=(descriptor,),
            timeout=15,
            check=False,
        )
        if parse.returncode != 0:
            fail("deployment signing key is not unencrypted PKCS#8")
        os.lseek(descriptor, 0, os.SEEK_SET)
        result = subprocess.run(
            [
                str(OPENSSL),
                "pkey",
                "-in",
                f"/proc/self/fd/{descriptor}",
                "-passin",
                "pass:",
                "-pubout",
                "-outform",
                "DER",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=OPENSSL_ENV,
            pass_fds=(descriptor,),
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise SigningInputError(
            "deployment signing key validation timed out"
        ) from error
    finally:
        os.close(descriptor)
    expected_size = len(ED25519_SPKI_PREFIX) + 32
    if (
        result.returncode != 0
        or len(result.stdout) != expected_size
        or not result.stdout.startswith(ED25519_SPKI_PREFIX)
    ):
        fail("deployment signing key is not Ed25519")
    public = result.stdout[len(ED25519_SPKI_PREFIX) :]
    if not any(public):
        fail("deployment signing public key is all zero")
    return public


def stage_inputs(
    repository_path: Path,
    signing_key: Path,
    candidate_record: Path,
    staged_key: Path,
    staged_candidate: Path,
    raw_public_key: Path,
    candidate_id: str = DEFAULT_CANDIDATE_ID,
    expected_checkpoint: str | None = None,
) -> tuple[str, str, str]:
    repository = canonical_repository(repository_path)
    checkpoint = verify_repository_checkpoint(repository)
    if expected_checkpoint is not None and checkpoint != expected_checkpoint:
        fail("repository checkpoint does not match the launcher snapshot")
    candidate_payload = read_private_input(
        candidate_record,
        repository,
        "deployment candidate record",
        0o444,
    )
    validate_candidate(candidate_payload, candidate_id)
    try:
        current_checkpoint = verify_repository_checkpoint(repository)
    except SigningInputError as error:
        raise SigningInputError(
            "repository checkpoint changed before credential read"
        ) from error
    if current_checkpoint != checkpoint:
        fail("repository checkpoint changed before credential read")
    reservations: list[OutputReservation] = []
    try:
        reservations.append(
            reserve_output(
                staged_key,
                repository,
                0o600,
                "staged deployment signing key",
            )
        )
        reservations.append(
            reserve_output(
                staged_candidate,
                repository,
                0o444,
                "staged deployment candidate",
            )
        )
        reservations.append(
            reserve_output(
                raw_public_key,
                repository,
                0o400,
                "staged deployment public key",
            )
        )
        key_payload = read_private_input(
            signing_key,
            repository,
            "deployment signing key",
            0o600,
        )
        commit_reservation(reservations[0], key_payload)
        public = derive_ed25519_public(staged_key)
        commit_reservation(reservations[1], candidate_payload)
        commit_reservation(reservations[2], public)
        for parent in {
            staged_key.parent,
            staged_candidate.parent,
            raw_public_key.parent,
        }:
            sync_directory(parent)
    except Exception:
        for reservation in reversed(reservations):
            discard_reservation(reservation)
        raise
    return (
        checkpoint,
        hashlib.sha256(candidate_payload).hexdigest(),
        hashlib.sha256(public).hexdigest(),
    )


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--signing-key", required=True, type=Path)
    parser.add_argument("--candidate-record", required=True, type=Path)
    parser.add_argument("--staged-key", required=True, type=Path)
    parser.add_argument("--staged-candidate", required=True, type=Path)
    parser.add_argument("--raw-public-key", required=True, type=Path)
    parser.add_argument(
        "--candidate-id",
        choices=ALLOWED_CANDIDATE_IDS,
        default=DEFAULT_CANDIDATE_ID,
    )
    parser.add_argument("--expected-repository-commit")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    options = parse_arguments(
        sys.argv[1:] if arguments is None else arguments
    )
    try:
        checkpoint, candidate_sha256, public_sha256 = stage_inputs(
            options.repository,
            options.signing_key,
            options.candidate_record,
            options.staged_key,
            options.staged_candidate,
            options.raw_public_key,
            options.candidate_id,
            options.expected_repository_commit,
        )
    except (CANDIDATE.CandidateError, SigningInputError) as error:
        print(
            f"FAIL deployment signing input staging refused: {error}",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError):
        print("FAIL deployment signing input staging refused", file=sys.stderr)
        return 1
    print("format=rog5-recovery-deployment-signing-inputs-v2")
    print(f"candidate={options.candidate_id}")
    print(f"repository_commit={checkpoint}")
    print(f"candidate_record_sha256={candidate_sha256}")
    print(f"raw_public_key_sha256={public_sha256}")
    print("authority=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
