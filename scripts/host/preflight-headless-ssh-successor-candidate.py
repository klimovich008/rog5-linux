#!/usr/bin/env python3
"""Verify the real r2 deployment candidate before any credential access."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
DEPLOYMENT_PATH = (
    REPO / "scripts/host/prepare-headless-ssh-deployment-candidate.py"
)
STAGER_PATH = (
    REPO / "scripts/host/stage-headless-ssh-deployment-signing-inputs.py"
)
EXPECTED_MANIFEST_SHA256 = (
    "9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630"
)
EXPECTED_BASE_CANDIDATE_SHA256 = (
    "cda35b12db73966fd231ea6889978da5fbf9ab62375177a21084c2ec822f6bcd"
)
EXPECTED_SUCCESSOR_CANDIDATE_SHA256 = (
    "b26bc73ec6cd0053900044776270ed2c3a7f7bf6424140a59bb74d513b5dd51e"
)
FAILURE = "FAIL successor candidate preflight refused"


class SuccessorPreflightError(RuntimeError):
    """A stable refusal that does not expose private input data."""


def fail(message: str) -> NoReturn:
    raise SuccessorPreflightError(message)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        fail("cannot load a fixed successor verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    try:
        specification.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(specification.name, None)
        raise
    return module


try:
    DEPLOYMENT = load_module(
        "rog5_successor_preflight_deployment",
        DEPLOYMENT_PATH,
    )
    STAGER = load_module(
        "rog5_successor_preflight_stager",
        STAGER_PATH,
    )
except Exception:
    if __name__ == "__main__":
        print(FAILURE, file=sys.stderr)
        raise SystemExit(1) from None
    raise
CANDIDATE = DEPLOYMENT.CANDIDATE
PACKAGER = CANDIDATE.PACKAGER


def parse_candidate(
    payload: bytes,
    expected_bundle: str,
) -> dict[str, Any]:
    try:
        record = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=CANDIDATE.unique_object,
        )
    except (
        CANDIDATE.CandidateError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise SuccessorPreflightError(
            "successor candidate JSON is invalid"
        ) from error
    validated = CANDIDATE.validate_external_candidate_record(
        record,
        DEPLOYMENT.CANDIDATE_ID,
    )
    if validated["bundle"] != expected_bundle:
        fail("candidate bundle identity is unexpected")
    return validated


def snapshot_artifacts(
    record: dict[str, Any],
) -> dict[str, tuple[int, str]]:
    observed: dict[str, tuple[int, str]] = {}
    with tempfile.TemporaryDirectory(
        prefix="rog5-successor-preflight-"
    ) as temporary:
        root = Path(temporary)
        for name in CANDIDATE.ARTIFACT_NAMES:
            destination = root / name
            CANDIDATE.snapshot_artifact(
                record["artifacts"][name],
                destination,
                name,
            )
            descriptor = os.open(
                destination,
                os.O_RDONLY
                | os.O_CLOEXEC
                | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                before = os.fstat(descriptor)
                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                    payload = stream.read()
                after = os.fstat(descriptor)
                identity = lambda value: (
                    value.st_dev,
                    value.st_ino,
                    value.st_mode,
                    value.st_nlink,
                    value.st_size,
                )
                if (
                    not stat.S_ISREG(after.st_mode)
                    or after.st_nlink != 1
                    or after.st_size != len(payload)
                    or identity(before) != identity(after)
                ):
                    fail("candidate artifact snapshot metadata is unsafe")
            finally:
                os.close(descriptor)
            observed[name] = (
                len(payload),
                hashlib.sha256(payload).hexdigest(),
            )
    return observed


def manifest_identity(
    record: dict[str, Any],
    observed: dict[str, tuple[int, str]],
) -> str:
    config = CANDIDATE.bundle_configuration(
        record,
        {
            "Image": Path("/not-opened/Image"),
            "board.dtb": Path("/not-opened/board.dtb"),
            "initramfs.cpio.gz": Path(
                "/not-opened/initramfs.cpio.gz"
            ),
        },
        Path("/not-opened/signing-key"),
        Path("/not-opened/bundles"),
    )
    PACKAGER.validate_configuration(config)
    return hashlib.sha256(
        PACKAGER.manifest_bytes(config, observed)
    ).hexdigest()


def verify(
    package_path: Path,
    base_candidate_path: Path,
    candidate_path: Path,
) -> tuple[str, str, str, str]:
    checkpoint = STAGER.verify_repository_checkpoint(REPO)
    package = DEPLOYMENT.parse_package(package_path)
    base_payload = STAGER.read_private_input(
        base_candidate_path,
        REPO,
        "base candidate record",
        0o444,
    )
    baseline = parse_candidate(
        base_payload,
        DEPLOYMENT.BASE_BUNDLE_ID,
    )
    candidate_payload = STAGER.read_private_input(
        candidate_path,
        REPO,
        "successor candidate record",
        0o444,
    )
    record = parse_candidate(
        candidate_payload,
        DEPLOYMENT.SUCCESSOR_BUNDLE_ID,
    )
    expected_baseline = DEPLOYMENT.candidate_record(
        package,
        DEPLOYMENT.BASE_BUNDLE_ID,
    )
    if (
        baseline != expected_baseline
        or base_payload != DEPLOYMENT.canonical_payload(expected_baseline)
    ):
        fail("base candidate does not match its retained package reconstruction")
    expected = DEPLOYMENT.candidate_record(
        package,
        DEPLOYMENT.SUCCESSOR_BUNDLE_ID,
    )
    if (
        record != expected
        or candidate_payload != DEPLOYMENT.canonical_payload(expected)
    ):
        fail(
            "successor candidate does not match its retained package reconstruction"
        )

    base_candidate_sha256 = hashlib.sha256(base_payload).hexdigest()
    candidate_sha256 = hashlib.sha256(candidate_payload).hexdigest()
    if base_candidate_sha256 != EXPECTED_BASE_CANDIDATE_SHA256:
        fail("base candidate does not match the pinned identity")
    if candidate_sha256 != EXPECTED_SUCCESSOR_CANDIDATE_SHA256:
        fail("successor candidate does not match the pinned identity")

    if {
        key: value for key, value in record.items() if key != "bundle"
    } != {
        key: value for key, value in baseline.items() if key != "bundle"
    }:
        fail("successor changes more than the bundle identity")

    observed = snapshot_artifacts(record)
    manifest_sha256 = manifest_identity(record, observed)
    if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        fail("successor manifest does not match the pinned prediction")
    if STAGER.verify_repository_checkpoint(REPO) != checkpoint:
        fail("repository checkpoint changed during successor preflight")
    return (
        checkpoint,
        base_candidate_sha256,
        candidate_sha256,
        manifest_sha256,
    )


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--base-candidate-record", required=True, type=Path)
    parser.add_argument("--candidate-record", required=True, type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    options = parse_arguments(
        sys.argv[1:] if arguments is None else arguments
    )
    try:
        (
            checkpoint,
            base_candidate_sha256,
            candidate_sha256,
            manifest_sha256,
        ) = verify(
            options.package,
            options.base_candidate_record,
            options.candidate_record,
        )
    except Exception:
        print(FAILURE, file=sys.stderr)
        return 1
    print("format=rog5-headless-ssh-successor-preflight-v1")
    print(f"checkpoint={checkpoint}")
    print(f"candidate={DEPLOYMENT.CANDIDATE_ID}")
    print(f"bundle={DEPLOYMENT.SUCCESSOR_BUNDLE_ID}")
    print(f"base_candidate_sha256={base_candidate_sha256}")
    print(f"candidate_sha256={candidate_sha256}")
    print(f"manifest_sha256={manifest_sha256}")
    print("authority=none")
    print("credential_access=none")
    print("phone_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
