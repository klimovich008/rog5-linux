#!/usr/bin/env python3
"""Bind one private v3 root package to an authority-free candidate record."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
HEADLESS_PATH = REPO / "scripts/host/headless-network-root.py"
CANDIDATE_PATH = REPO / "scripts/host/prepare-recovery-candidate.py"
FIXTURE_PACKAGE_PATH = (
    REPO / "configs/network-roots/headless-ssh-network-root-v3.package"
)
CANDIDATE_ID = "headless-ssh-network-root-v3"
BASE_BUNDLE_ID = "headless-ssh-network-root-v3"
SUCCESSOR_BUNDLE_ID = "headless-ssh-network-root-v3-r2"
ALLOWED_BUNDLES = {BASE_BUNDLE_ID, SUCCESSOR_BUNDLE_ID}
ROOT_FIELDS = (
    "a660_command_manifest_sha256",
    "root_generation",
    "root_tree_sha256",
    "root_seal_sha256",
    "root_tree_entries",
    "root_subtree",
)
FIXTURE_FIELDS = (
    "authorized_key_fingerprint",
    "source_archive_sha256",
    "sealed_archive_sha256",
    "root_tree_sha256",
    "root_seal_sha256",
)
MAX_PACKAGE_SIZE = 16 * 1024


class DeploymentCandidateError(RuntimeError):
    """A stable refusal that does not expose credential material."""


def fail(message: str) -> NoReturn:
    raise DeploymentCandidateError(message)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        fail("cannot load a fixed deployment-candidate verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


HEADLESS = load_module("rog5_deployment_candidate_headless", HEADLESS_PATH)
CANDIDATE = load_module(
    "rog5_deployment_candidate_template",
    CANDIDATE_PATH,
)


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


def outside_repository(path: Path, label: str) -> None:
    try:
        path.relative_to(REPO)
    except ValueError:
        return
    fail(f"{label} must remain outside the repository")


def private_parent(path: Path, label: str) -> Path:
    if not path.is_absolute():
        fail(f"{label} path must be absolute")
    lexical = Path(os.path.abspath(path))
    parent = lexical.parent
    try:
        named = parent.lstat()
        resolved = parent.resolve(strict=True)
        resolved_metadata = resolved.lstat()
    except OSError as error:
        raise DeploymentCandidateError(
            f"{label} parent is unavailable"
        ) from error
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
    outside_repository(resolved, f"{label} parent")
    return lexical


def readonly_input(path: Path, label: str) -> Path:
    lexical = private_parent(path, label)
    try:
        named = lexical.lstat()
        resolved = lexical.resolve(strict=True)
        resolved_metadata = resolved.lstat()
    except OSError as error:
        raise DeploymentCandidateError(f"{label} is unavailable") from error
    if (
        lexical != resolved
        or stat.S_ISLNK(named.st_mode)
        or identity(named) != identity(resolved_metadata)
        or not stat.S_ISREG(named.st_mode)
        or named.st_uid != os.geteuid()
        or named.st_gid != os.getegid()
        or stat.S_IMODE(named.st_mode) not in {0o400, 0o444}
        or named.st_nlink != 1
        or named.st_size < 1
        or named.st_size > MAX_PACKAGE_SIZE
    ):
        fail(f"{label} metadata is unsafe")
    return resolved


def parse_package(path: Path) -> dict[str, str]:
    package_path = readonly_input(path, "deployment package")
    values = HEADLESS.parse_canonical_variant(
        package_path,
        HEADLESS.PACKAGE_FORMATS,
        owner=os.geteuid(),
        mode=stat.S_IMODE(package_path.stat().st_mode),
    )
    HEADLESS.validate_package(values)
    if (
        values["format"] != "rog5-headless-network-root-package-v3"
        or values["profile"] != "network-root-v1"
        or values["build_profile"] != "headless-ssh-v2"
    ):
        fail("deployment package tuple is unsupported")
    fixture = HEADLESS.parse_canonical_variant(
        FIXTURE_PACKAGE_PATH,
        HEADLESS.PACKAGE_FORMATS,
        owner=FIXTURE_PACKAGE_PATH.stat().st_uid,
        mode=stat.S_IMODE(FIXTURE_PACKAGE_PATH.stat().st_mode),
    )
    for field in FIXTURE_FIELDS:
        if values[field] == fixture[field]:
            fail("deployment package still carries a fixture identity")
    return dict(values)


def candidate_record(
    package: dict[str, str],
    bundle: str = BASE_BUNDLE_ID,
) -> dict[str, Any]:
    if bundle not in ALLOWED_BUNDLES:
        fail("deployment bundle identity is unsupported")
    template = CANDIDATE.load_candidate(CANDIDATE_ID)
    record = copy.deepcopy(template)
    record["bundle"] = bundle
    for field in ROOT_FIELDS:
        record[field] = package[field]
    validated = CANDIDATE.validate_candidate_record(
        record,
        CANDIDATE_ID,
    )
    return CANDIDATE.validate_external_candidate_record(
        validated,
        CANDIDATE_ID,
    )


def canonical_payload(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, indent=2) + "\n").encode("ascii")


def write_candidate(path: Path, payload: bytes) -> Path:
    output = private_parent(path, "deployment candidate")
    if output.exists() or output.is_symlink():
        fail("deployment candidate output already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output, flags, 0o444)
    created = os.fstat(descriptor)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("deployment candidate write made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_gid != os.getegid()
            or stat.S_IMODE(metadata.st_mode) != 0o444
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            fail("deployment candidate output metadata is unsafe")
    except Exception:
        os.close(descriptor)
        descriptor = -1
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
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    parent_descriptor = os.open(
        output.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        os.fsync(parent_descriptor)
    finally:
        os.close(parent_descriptor)
    return output


def prepare(
    package_path: Path,
    output_path: Path,
    bundle: str = BASE_BUNDLE_ID,
) -> tuple[dict[str, Any], Path]:
    package = parse_package(package_path)
    record = candidate_record(package, bundle)
    output = write_candidate(output_path, canonical_payload(record))
    return record, output


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--bundle",
        choices=sorted(ALLOWED_BUNDLES),
        required=True,
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    options = parse_arguments(
        sys.argv[1:] if arguments is None else arguments
    )
    try:
        record, output = prepare(
            options.package,
            options.output,
            options.bundle,
        )
    except (
        DeploymentCandidateError,
        HEADLESS.HeadlessRootError,
        CANDIDATE.CandidateError,
        OSError,
        ValueError,
    ):
        print(
            "FAIL deployment candidate preparation refused",
            file=sys.stderr,
        )
        return 1
    print("format=rog5-headless-ssh-deployment-candidate-v1")
    print(f"candidate={record['candidate']}")
    print(f"bundle={record['bundle']}")
    print(f"root_tree_sha256={record['root_tree_sha256']}")
    print(f"root_seal_sha256={record['root_seal_sha256']}")
    print(f"root_tree_entries={record['root_tree_entries']}")
    print(f"output={output}")
    print("authority=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
