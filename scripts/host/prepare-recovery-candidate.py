#!/usr/bin/env python3
"""Prepare one pinned, authority-free stable-recovery candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CANDIDATE_ROOT = REPO / "configs" / "recovery-candidates"
PACKAGER_PATH = REPO / "scripts" / "host" / (
    "prepare-recovery-runtime-bundle.py"
)
CANDIDATE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TOP_LEVEL_KEYS = {
    "format",
    "candidate",
    "status",
    "authority",
    "bundle",
    "profile",
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
    "artifacts",
}
ARTIFACT_NAMES = ("Image", "board.dtb", "initramfs.cpio.gz")
ARTIFACT_KEYS = {"path", "size", "sha256"}
EXTERNAL_MUTABLE_FIELDS = {
    "a660_command_manifest_sha256",
    "root_generation",
    "root_tree_sha256",
    "root_seal_sha256",
    "root_tree_entries",
    "root_subtree",
}
EXTERNAL_BUNDLE_SUCCESSORS = {
    "headless-ssh-network-root-v3": {
        "headless-ssh-network-root-v3",
        "headless-ssh-network-root-v3-r2",
    },
}
EXTERNAL_SUCCESSOR_ROOT_FIELDS = {
    "headless-ssh-network-root-v3-r2": {
        "a660_command_manifest_sha256": (
            "99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2"
        ),
        "root_generation": "arch-a",
        "root_tree_sha256": (
            "f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087"
        ),
        "root_seal_sha256": (
            "42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a"
        ),
        "root_tree_entries": "37735",
        "root_subtree": "/",
    },
}


class CandidateError(RuntimeError):
    """A stable, non-sensitive candidate refusal."""


def load_packager():
    specification = importlib.util.spec_from_file_location(
        "rog5_recovery_runtime_packager",
        PACKAGER_PATH,
    )
    if specification is None or specification.loader is None:
        raise CandidateError("cannot load stable bundle packager")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


PACKAGER = load_packager()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise CandidateError("candidate JSON has a duplicate key")
        output[key] = value
    return output


def regular_bytes(path: Path, label: str, maximum: int) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CandidateError(f"cannot open {label}") from error
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) & 0o022
            or metadata.st_size < 1
            or metadata.st_size > maximum
        ):
            raise CandidateError(f"{label} metadata is unsafe")
        payload = bytearray()
        while len(payload) <= maximum:
            block = os.read(descriptor, min(65536, maximum + 1 - len(payload)))
            if not block:
                break
            payload.extend(block)
        if len(payload) != metadata.st_size:
            raise CandidateError(f"{label} changed while being read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def require_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str):
        raise CandidateError(f"candidate field {key} is not a string")
    return value


def validate_candidate_identifier(candidate: str) -> None:
    if (
        not CANDIDATE_ID.fullmatch(candidate)
        or ".." in candidate
        or candidate == "none"
    ):
        raise CandidateError("candidate identifier is invalid")


def validate_candidate_record(
    record: dict[str, Any],
    candidate: str,
) -> dict[str, Any]:
    validate_candidate_identifier(candidate)
    if not isinstance(record, dict) or set(record) != TOP_LEVEL_KEYS:
        raise CandidateError("candidate fields are incomplete or unknown")
    if require_string(record, "format") != "rog5-recovery-candidate-v1":
        raise CandidateError("candidate format is unsupported")
    if require_string(record, "candidate") != candidate:
        raise CandidateError("candidate identity does not match its filename")
    status = require_string(record, "status")
    profile = require_string(record, "profile")
    if status not in {"consumed", "offline"}:
        raise CandidateError("candidate status is not authority-free")
    if status == "offline" and profile not in {
        "diagnostic-initramfs-v1",
        "network-root-v1",
    }:
        raise CandidateError("offline candidate is not a network-root profile")
    if require_string(record, "authority") != "none":
        raise CandidateError("candidate unexpectedly carries live authority")

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict) or tuple(artifacts) != ARTIFACT_NAMES:
        raise CandidateError("candidate artifact inventory is not canonical")
    for name in ARTIFACT_NAMES:
        artifact = artifacts[name]
        if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_KEYS:
            raise CandidateError(f"{name} fields are incomplete or unknown")
        relative = artifact.get("path")
        size = artifact.get("size")
        digest = artifact.get("sha256")
        if (
            not isinstance(relative, str)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 1
            or not isinstance(digest, str)
            or not SHA256.fullmatch(digest)
        ):
            raise CandidateError(f"{name} identity is invalid")
        path = PurePosixPath(relative)
        if (
            path.is_absolute()
            or not path.parts
            or path.parts[0] != "artifacts"
            or ".." in path.parts
        ):
            raise CandidateError(f"{name} path is outside artifact policy")
    return record


def load_candidate_path(path: Path, candidate: str) -> dict[str, Any]:
    validate_candidate_identifier(candidate)
    payload = regular_bytes(
        path,
        "candidate record",
        64 * 1024,
    )
    try:
        record = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=unique_object,
        )
    except (CandidateError, UnicodeDecodeError, json.JSONDecodeError) as error:
        if isinstance(error, CandidateError):
            raise
        raise CandidateError("candidate JSON is invalid") from error
    return validate_candidate_record(record, candidate)


def load_candidate(candidate: str) -> dict[str, Any]:
    return load_candidate_path(
        CANDIDATE_ROOT / f"{candidate}.json",
        candidate,
    )


def validate_external_candidate_record(
    record: dict[str, Any],
    candidate: str,
) -> dict[str, Any]:
    validated = validate_candidate_record(record, candidate)
    template = load_candidate(candidate)
    allowed_bundles = EXTERNAL_BUNDLE_SUCCESSORS.get(
        candidate,
        {require_string(template, "bundle")},
    )
    bundle = require_string(validated, "bundle")
    if bundle not in allowed_bundles:
        raise CandidateError("external candidate bundle is unsupported")
    for field in TOP_LEVEL_KEYS - EXTERNAL_MUTABLE_FIELDS - {"bundle"}:
        if validated[field] != template[field]:
            raise CandidateError(
                "external candidate changed a fixed template field"
            )
    successor_root = EXTERNAL_SUCCESSOR_ROOT_FIELDS.get(bundle)
    if successor_root is not None:
        for field, expected in successor_root.items():
            if validated[field] != expected:
                raise CandidateError(
                    "external successor changed the accepted predecessor root"
                )
    return validated


def load_external_candidate_path(
    path: Path,
    candidate: str,
    expected_sha256: str,
) -> dict[str, Any]:
    validate_candidate_identifier(candidate)
    if not SHA256.fullmatch(expected_sha256):
        raise CandidateError("external candidate hash is invalid")
    payload = regular_bytes(path, "external candidate record", 64 * 1024)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise CandidateError("external candidate hash changed")
    try:
        record = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=unique_object,
        )
    except (CandidateError, UnicodeDecodeError, json.JSONDecodeError) as error:
        if isinstance(error, CandidateError):
            raise
        raise CandidateError("candidate JSON is invalid") from error
    return validate_external_candidate_record(record, candidate)


def source_snapshot(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise CandidateError("candidate snapshot write made no progress")
        offset += written


def snapshot_artifact(
    artifact: dict[str, Any],
    destination: Path,
    label: str,
) -> None:
    source_path = REPO / artifact["path"]
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        source = os.open(source_path, flags)
    except OSError as error:
        raise CandidateError(f"cannot open pinned {label}") from error
    output = -1
    try:
        before = os.fstat(source)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != artifact["size"]
        ):
            raise CandidateError(f"pinned {label} metadata changed")
        output = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o400,
        )
        digest = hashlib.sha256()
        observed = 0
        while True:
            block = os.read(source, 1024 * 1024)
            if not block:
                break
            observed += len(block)
            digest.update(block)
            write_all(output, block)
        os.fchmod(output, 0o400)
        os.fsync(output)
        after = os.fstat(source)
        if source_snapshot(before) != source_snapshot(after):
            raise CandidateError(f"pinned {label} changed during snapshot")
        if (
            observed != artifact["size"]
            or digest.hexdigest() != artifact["sha256"]
        ):
            raise CandidateError(f"pinned {label} identity changed")
    finally:
        if output >= 0:
            os.close(output)
        os.close(source)


def bundle_configuration(
    record: dict[str, Any],
    artifacts: dict[str, Path],
    private_key: Path,
    bundle_root: Path,
) -> Any:
    return PACKAGER.Configuration(
        bundle=require_string(record, "bundle"),
        profile=require_string(record, "profile"),
        image=artifacts["Image"],
        dtb=artifacts["board.dtb"],
        initramfs=artifacts["initramfs.cpio.gz"],
        target_id=require_string(record, "target_id"),
        target_release=require_string(record, "target_release"),
        rollback_timeout=require_string(record, "rollback_timeout"),
        target_timeout=require_string(record, "target_timeout"),
        a660_command_manifest_sha256=require_string(
            record,
            "a660_command_manifest_sha256",
        ),
        root_generation=require_string(record, "root_generation"),
        root_tree_sha256=require_string(record, "root_tree_sha256"),
        root_seal_sha256=require_string(record, "root_seal_sha256"),
        root_tree_entries=require_string(record, "root_tree_entries"),
        root_subtree=require_string(record, "root_subtree"),
        private_key=private_key,
        bundle_root=bundle_root,
    )


def prepare(
    candidate: str,
    private_key: Path,
    bundle_root: Path,
    candidate_path: Path | None = None,
    candidate_sha256: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    if (candidate_path is None) != (candidate_sha256 is None):
        raise CandidateError(
            "external candidate path and hash must be provided together"
        )
    if candidate_path is None:
        record = load_candidate(candidate)
    else:
        assert candidate_sha256 is not None
        record = load_external_candidate_path(
            candidate_path,
            candidate,
            candidate_sha256,
        )
    with tempfile.TemporaryDirectory(
        prefix=f"rog5-{candidate}-",
    ) as temporary:
        snapshot_root = Path(temporary)
        snapshots: dict[str, Path] = {}
        for name in ARTIFACT_NAMES:
            destination = snapshot_root / name
            snapshot_artifact(record["artifacts"][name], destination, name)
            snapshots[name] = destination
        config = bundle_configuration(
            record,
            snapshots,
            private_key,
            bundle_root,
        )
        manifest_hash, trust_key_hash = PACKAGER.prepare_bundle(config)
    return record, manifest_hash, trust_key_hash


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("candidate")
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--bundle-root", required=True, type=Path)
    parser.add_argument("--candidate-record", type=Path)
    parser.add_argument("--candidate-record-sha256")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    os.umask(0o077)
    values = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        record, manifest_hash, trust_key_hash = prepare(
            values.candidate,
            values.private_key,
            values.bundle_root,
            values.candidate_record,
            values.candidate_record_sha256,
        )
    except (CandidateError, PACKAGER.BundleError):
        print("FAIL offline candidate preparation refused", file=sys.stderr)
        return 1
    except OSError:
        print("FAIL offline candidate filesystem operation failed", file=sys.stderr)
        return 1
    print("format=rog5-prepared-candidate-v1")
    print(f"candidate={record['candidate']}")
    print(f"status={record['status']}")
    print(f"authority={record['authority']}")
    print(f"bundle={record['bundle']}")
    print(f"manifest_sha256={manifest_hash}")
    print(f"trust_key_sha256={trust_key_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
