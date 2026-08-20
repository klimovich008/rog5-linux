#!/usr/bin/env python3
"""Verify one private SSH key against an exact non-fixture v3 candidate."""

from __future__ import annotations

from collections import OrderedDict
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
from types import MappingProxyType
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
HEADLESS_TOOL_PATH = REPO / "scripts/host/headless-network-root.py"
CANDIDATE_TOOL_PATH = REPO / "scripts/host/prepare-recovery-candidate.py"
FIXTURE_KEY_PATH = REPO / "configs/ssh/rog5-headless-build-fixture.pub"
SSH_KEYGEN = Path("/usr/bin/ssh-keygen")
ZERO_SHA256 = "0" * 64
FIXTURE_FINGERPRINT = (
    "SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0"
)
FIXTURE_SOURCE_SHA256 = (
    "2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a"
)
FIXTURE_SEALED_SHA256 = (
    "60fed48c8714a3f3b2082f95a04e913f32dfc74ed4c262e5b3d6e924a39a9c3b"
)
FIXTURE_TREE_SHA256 = (
    "6f8a8f11bfb581bb52ca7d590141ce465b8d48d8f9f4577a076b7a37604a2fd5"
)
FIXTURE_SEAL_SHA256 = (
    "f443a47c456b33d670e6efd4a2e20cff2bc72061e7661472694acfbba45c8d5a"
)
FIXTURE_MANIFEST_SHA256 = (
    "a409f0ebad410edf8fb36e31d322029bf69d4c6621ddab84a660ff471da48e11"
)
CANDIDATE_ID = "headless-ssh-network-root-v3"
BUNDLE_ID = "headless-ssh-network-root-v3-r2"
PROFILE = "network-root-v1"
BUILD_PROFILE = "headless-ssh-v2"
TARGET_ID = "headless-ssh-network-root"
TARGET_RELEASE = "7.1.4-g7a5cef0db479"
EXPECTED_ARTIFACTS = {
    "Image": {
        "path": "artifacts/network-root-v1/Image-7.1.4-network-root",
        "size": 40049152,
        "sha256": (
            "349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf"
        ),
    },
    "board.dtb": {
        "path": (
            "artifacts/network-root-v3/"
            "sm8350-asus-rog-phone5-recovery.dtb"
        ),
        "size": 102870,
        "sha256": (
            "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
        ),
    },
    "initramfs.cpio.gz": {
        "path": (
            "artifacts/headless-network-root-v1/"
            "rog5-headless-network-root-initramfs.cpio.gz"
        ),
        "size": 5978369,
        "sha256": (
            "819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5"
        ),
    },
}
LEGACY_DIAGNOSTIC_EXPECTED_ARTIFACTS = {
    "Image": {
        "path": "artifacts/network-root-v1/Image-7.1.4-network-root",
        "size": 40049152,
        "sha256": (
            "349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf"
        ),
    },
    "board.dtb": {
        "path": (
            "artifacts/network-root-v3/"
            "sm8350-asus-rog-phone5-recovery.dtb"
        ),
        "size": 102870,
        "sha256": (
            "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
        ),
    },
    "initramfs.cpio.gz": {
        "path": (
            "artifacts/early-target-diagnostic-v1/"
            "rog5-early-target-diagnostic-initramfs.cpio.gz"
        ),
        "size": 6010870,
        "sha256": (
            "10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c"
        ),
    },
}
DIAGNOSTIC_EXPECTED_ARTIFACTS = {
    "Image": {
        "path": "artifacts/network-root-v1/Image-7.1.4-network-root",
        "size": 40049152,
        "sha256": (
            "349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf"
        ),
    },
    "board.dtb": {
        "path": (
            "artifacts/network-root-v3/"
            "sm8350-asus-rog-phone5-recovery.dtb"
        ),
        "size": 102870,
        "sha256": (
            "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
        ),
    },
    "initramfs.cpio.gz": {
        "path": (
            "artifacts/early-target-diagnostic-v7/"
            "rog5-early-target-diagnostic-initramfs.cpio.gz"
        ),
        "size": 6014751,
        "sha256": (
            "635e641c62f894d4bc150cd3fec9ae965f0f9a769ff7b856ad5ca2432530ed2b"
        ),
    },
}
CORE_EXPECTED_ARTIFACTS = {
    "Image": EXPECTED_ARTIFACTS["Image"],
    "board.dtb": {
        "path": (
            "artifacts/buttons-indicator-v1/"
            "sm8350-asus-rog-phone5-buttons-indicator.dtb"
        ),
        "size": 103554,
        "sha256": (
            "57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d"
        ),
    },
    "initramfs.cpio.gz": EXPECTED_ARTIFACTS["initramfs.cpio.gz"],
}
POWER_USB_EXPECTED_ARTIFACTS = {
    "Image": {
        "path": "artifacts/network-root-power-usb-observer-v1/Image",
        "size": 40049152,
        "sha256": (
            "6b5697ee1c2bf289bc6f94323bba7cc01db70a657770395fdc588eb93d1b36ef"
        ),
    },
    "board.dtb": {
        "path": "artifacts/network-root-power-usb-observer-v1/board.dtb",
        "size": 102938,
        "sha256": (
            "3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11"
        ),
    },
    "initramfs.cpio.gz": {
        "path": (
            "artifacts/network-root-power-usb-observer-v1/"
            "initramfs.cpio.gz"
        ),
        "size": 5995915,
        "sha256": (
            "f3df0e5865a55a2d5260270db628b61358e2c1287491e35f79b73c38e9ade4d9"
        ),
    },
}
CORE_FIXTURE_IDENTITIES = {
    "source_archive_sha256": (
        "86e2b3bfdd057e9b7bb98963eb419c839641b63d8d21ec8d3bd84c5c1b8d18f1"
    ),
    "sealed_archive_sha256": (
        "f8ec3bd739ab96b8559f20da4e971e4c01fadaec86f8610036c084cd78019f64"
    ),
    "root_tree_sha256": (
        "c00fbf419f64b41690aa66c9c5b627e78990b367be320f13b04ff1cf5e7af17d"
    ),
    "root_seal_sha256": (
        "96c9ff3584d65e21c0307cd065ca28babf8f9c3ad708034965c85e3788de1e22"
    ),
}
MANIFEST_KEYS = (
    "format",
    "bundle",
    "profile",
    "kernel_size",
    "kernel_sha256",
    "dtb_size",
    "dtb_sha256",
    "initramfs_size",
    "initramfs_sha256",
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
)
ROOT_FIELDS = (
    "a660_command_manifest_sha256",
    "root_generation",
    "root_tree_sha256",
    "root_seal_sha256",
    "root_tree_entries",
    "root_subtree",
)


@dataclass(frozen=True)
class ArtifactPin:
    name: str
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class AdmissionProfile:
    name: str
    candidate_id: str
    bundle_id: str
    bundle_profile: str
    package_profile: str
    build_profile: str
    target_id: str
    target_release: str
    expected_artifacts: tuple[ArtifactPin, ...]


def immutable_artifacts(
    values: dict[str, dict[str, str | int]],
) -> tuple[ArtifactPin, ...]:
    return tuple(
        ArtifactPin(
            name=name,
            path=str(values[name]["path"]),
            size=int(values[name]["size"]),
            sha256=str(values[name]["sha256"]),
        )
        for name in ("Image", "board.dtb", "initramfs.cpio.gz")
    )


def artifact_map(profile: AdmissionProfile) -> dict[str, dict[str, str | int]]:
    return {
        artifact.name: {
            "path": artifact.path,
            "size": artifact.size,
            "sha256": artifact.sha256,
        }
        for artifact in profile.expected_artifacts
    }


DEPLOYMENT_ADMISSION_PROFILE = AdmissionProfile(
    name="headless-ssh-r2",
    candidate_id=CANDIDATE_ID,
    bundle_id=BUNDLE_ID,
    bundle_profile=PROFILE,
    package_profile=PROFILE,
    build_profile=BUILD_PROFILE,
    target_id=TARGET_ID,
    target_release=TARGET_RELEASE,
    expected_artifacts=immutable_artifacts(EXPECTED_ARTIFACTS),
)
LEGACY_DIAGNOSTIC_ADMISSION_PROFILE = AdmissionProfile(
    # Read-side verification only for immutable consumed v1 evidence. Current
    # credentialed builders accept only DIAGNOSTIC_ADMISSION_PROFILE below.
    name="early-target-diagnostic-v1",
    candidate_id="headless-netroot-early-diag-v1",
    bundle_id="headless-netroot-early-diag-v1",
    bundle_profile="diagnostic-initramfs-v1",
    package_profile=PROFILE,
    build_profile=BUILD_PROFILE,
    target_id="headless-netroot-early-diag",
    target_release=TARGET_RELEASE,
    expected_artifacts=immutable_artifacts(
        LEGACY_DIAGNOSTIC_EXPECTED_ARTIFACTS
    ),
)
DIAGNOSTIC_ADMISSION_PROFILE = AdmissionProfile(
    name="early-target-diagnostic-v2",
    candidate_id="headless-netroot-early-diag-v2",
    bundle_id="headless-netroot-early-diag-v2",
    bundle_profile="diagnostic-initramfs-v1",
    package_profile=PROFILE,
    build_profile=BUILD_PROFILE,
    target_id="headless-netroot-early-diag-v2",
    target_release=TARGET_RELEASE,
    expected_artifacts=immutable_artifacts(DIAGNOSTIC_EXPECTED_ARTIFACTS),
)
CORE_ADMISSION_PROFILE = AdmissionProfile(
    name="headless-core-live-v1",
    candidate_id="headless-core-network-root-v2",
    bundle_id="headless-core-network-root-v2-live-v1",
    bundle_profile=PROFILE,
    package_profile=PROFILE,
    build_profile="headless-core-v3",
    target_id="headless-core-network-root",
    target_release=TARGET_RELEASE,
    expected_artifacts=immutable_artifacts(CORE_EXPECTED_ARTIFACTS),
)
POWER_USB_ADMISSION_PROFILE = AdmissionProfile(
    name="power-usb-observer-live-v1",
    candidate_id="headless-power-usb-observer-v3",
    bundle_id="headless-power-usb-observer-v3",
    bundle_profile=PROFILE,
    package_profile=PROFILE,
    build_profile=BUILD_PROFILE,
    target_id="headless-power-usb-observer-v3",
    target_release=TARGET_RELEASE,
    expected_artifacts=immutable_artifacts(POWER_USB_EXPECTED_ARTIFACTS),
)
ADMISSION_PROFILES = MappingProxyType(
    {
        profile.name: profile
        for profile in (
            DEPLOYMENT_ADMISSION_PROFILE,
            LEGACY_DIAGNOSTIC_ADMISSION_PROFILE,
            DIAGNOSTIC_ADMISSION_PROFILE,
            CORE_ADMISSION_PROFILE,
            POWER_USB_ADMISSION_PROFILE,
        )
    }
)


class AdmissionError(RuntimeError):
    """A stable error that never includes private key material."""


def fail(message: str) -> NoReturn:
    raise AdmissionError(message)


def resolve_admission_profile(name: str) -> AdmissionProfile:
    if not isinstance(name, str) or name not in ADMISSION_PROFILES:
        fail("admission profile is not one fixed policy")
    return ADMISSION_PROFILES[name]


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        fail("cannot load a fixed admission verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


HEADLESS = load_module("rog5_headless_key_admission_root", HEADLESS_TOOL_PATH)
CANDIDATE = load_module(
    "rog5_headless_key_admission_candidate",
    CANDIDATE_TOOL_PATH,
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


def canonical_path(path: Path, label: str) -> Path:
    if not path.is_absolute():
        fail(f"{label} path must be absolute")
    try:
        named = path.lstat()
        resolved = path.resolve(strict=True)
        resolved_metadata = resolved.lstat()
    except OSError as error:
        raise AdmissionError(f"{label} path is unavailable") from error
    if (
        path != resolved
        or stat.S_ISLNK(named.st_mode)
        or identity(named) != identity(resolved_metadata)
    ):
        fail(f"{label} path is not canonical")
    return resolved


def outside_repository(path: Path, label: str) -> None:
    try:
        path.relative_to(REPO)
    except ValueError:
        return
    fail(f"{label} must remain outside the repository")


def open_private_key(path: Path) -> tuple[int, os.stat_result]:
    path = canonical_path(path, "private key")
    outside_repository(path, "private key")
    parent = path.parent.lstat()
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.geteuid()
        or stat.S_IMODE(parent.st_mode) & 0o077
    ):
        fail("private key parent metadata is unsafe")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise AdmissionError("private key cannot be opened") from error
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
        or metadata.st_nlink != 1
        or metadata.st_size < 1
        or metadata.st_size > 64 * 1024
    ):
        os.close(descriptor)
        fail("private key metadata is unsafe")
    return descriptor, metadata


def fixed_ssh_keygen() -> str:
    try:
        metadata = SSH_KEYGEN.lstat()
    except OSError as error:
        raise AdmissionError("fixed ssh-keygen is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o755
    ):
        fail("fixed ssh-keygen metadata is unsafe")
    return str(SSH_KEYGEN)


def derive_public_key(path: Path) -> tuple[bytes, str]:
    descriptor, before = open_private_key(path)
    try:
        result = subprocess.run(
            [
                fixed_ssh_keygen(),
                "-y",
                "-f",
                f"/proc/self/fd/{descriptor}",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"LC_ALL": "C"},
            pass_fds=(descriptor,),
            check=False,
            timeout=15,
        )
        after = os.fstat(descriptor)
        try:
            named = path.lstat()
        except OSError as error:
            raise AdmissionError(
                "private key disappeared during derivation"
            ) from error
        if identity(before) != identity(after) or identity(before) != identity(
            named
        ):
            fail("private key changed during derivation")
        if (
            result.returncode != 0
            or not result.stdout.endswith(b"\n")
            or result.stdout.count(b"\n") != 1
            or b"\r" in result.stdout
        ):
            fail("private key is not one unencrypted Ed25519 key")
        fields = result.stdout[:-1].split(b" ")
        if (
            len(fields) < 2
            or fields[0] != b"ssh-ed25519"
            or not fields[1]
        ):
            fail("private key is not one unencrypted Ed25519 key")
        canonical = b" ".join(fields[:2]) + b"\n"
        fingerprint = HEADLESS.authorized_key_fingerprint(canonical)
        return canonical, fingerprint
    except subprocess.TimeoutExpired as error:
        raise AdmissionError("private key derivation timed out") from error
    finally:
        os.close(descriptor)


def read_record(path: Path, label: str, modes: set[int]) -> bytes:
    path = canonical_path(path, label)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise AdmissionError(f"{label} cannot be opened") from error
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) not in modes
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > 64 * 1024
        ):
            fail(f"{label} metadata is unsafe")
        payload = bytearray()
        while len(payload) <= 64 * 1024:
            block = os.read(
                descriptor,
                min(65536, 64 * 1024 + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            len(payload) != before.st_size
            or identity(before) != identity(after)
            or identity(before) != identity(named)
        ):
            fail(f"{label} changed while being read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def parse_package(path: Path) -> tuple[OrderedDict[str, str], bytes]:
    payload = read_record(path, "root package", {0o400, 0o444})
    values = HEADLESS.parse_canonical_payload(
        payload,
        HEADLESS.PACKAGE_KEYS_V3,
    )
    HEADLESS.validate_package(values)
    return values, payload


def parse_candidate(
    path: Path,
    admission_profile: str = DEPLOYMENT_ADMISSION_PROFILE.name,
) -> tuple[dict[str, Any], bytes]:
    profile = resolve_admission_profile(admission_profile)
    payload = read_record(path, "candidate record", {0o400, 0o444})
    try:
        values = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=CANDIDATE.unique_object,
        )
    except (
        CANDIDATE.CandidateError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise AdmissionError("candidate record is invalid") from error
    temporary = canonical_path(path, "candidate record")
    try:
        validated = CANDIDATE.load_candidate_path(
            temporary,
            profile.candidate_id,
        )
    except CANDIDATE.CandidateError as error:
        raise AdmissionError("candidate record is invalid") from error
    if values != validated:
        fail("candidate record changed during validation")
    return validated, payload


def parse_manifest(
    path: Path,
    expected_sha256: str,
) -> tuple[OrderedDict[str, str], bytes]:
    if (
        not HEADLESS.SHA256.fullmatch(expected_sha256)
        or expected_sha256 == ZERO_SHA256
    ):
        fail("expected manifest identity is invalid")
    payload = read_record(path, "runtime manifest", {0o400, 0o444})
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        fail("runtime manifest identity changed")
    values = HEADLESS.parse_canonical_payload(payload, MANIFEST_KEYS)
    return values, payload


def verify(
    private_key: Path,
    package_path: Path,
    candidate_path: Path,
    manifest_path: Path,
    expected_manifest_sha256: str,
    admission_profile: str = DEPLOYMENT_ADMISSION_PROFILE.name,
) -> OrderedDict[str, str]:
    profile = resolve_admission_profile(admission_profile)
    public_key, fingerprint = derive_public_key(private_key)
    fixture_payload = b" ".join(
        FIXTURE_KEY_PATH.read_bytes().strip().split()[:2]
    ) + b"\n"
    if (
        HEADLESS.authorized_key_fingerprint(fixture_payload)
        != FIXTURE_FINGERPRINT
    ):
        fail("tracked fixture key identity changed")
    if fingerprint == FIXTURE_FINGERPRINT:
        fail("tracked fixture key is not a deployment credential")

    package, package_payload = parse_package(package_path)
    candidate, candidate_payload = parse_candidate(
        candidate_path,
        profile.name,
    )
    manifest, manifest_payload = parse_manifest(
        manifest_path,
        expected_manifest_sha256,
    )

    if (
        package["format"]
        != (
            "rog5-headless-network-root-package-v4"
            if profile is CORE_ADMISSION_PROFILE
            else "rog5-headless-network-root-package-v3"
        )
        or package["profile"] != profile.package_profile
        or package["build_profile"] != profile.build_profile
        or package["authorized_key_fingerprint"] != fingerprint
    ):
        fail("private key and v3 root package do not match")
    if (
        package["source_archive_sha256"] == FIXTURE_SOURCE_SHA256
        or package["sealed_archive_sha256"] == FIXTURE_SEALED_SHA256
        or package["root_tree_sha256"] == FIXTURE_TREE_SHA256
        or package["root_seal_sha256"] == FIXTURE_SEAL_SHA256
        or any(
            package[name] == value
            for name, value in CORE_FIXTURE_IDENTITIES.items()
        )
    ):
        fail("root package still carries a tracked fixture identity")

    if any(name not in candidate for name in ROOT_FIELDS):
        fail("candidate is missing a v3 root identity")
    if (
        candidate["candidate"] != profile.candidate_id
        or candidate["bundle"] != profile.bundle_id
        or candidate["status"] != "offline"
        or candidate["authority"] != "none"
        or candidate["profile"] != profile.bundle_profile
        or candidate["target_id"] != profile.target_id
        or candidate["target_release"] != profile.target_release
        or candidate["rollback_timeout"] != "600"
        or candidate["target_timeout"] != "480"
        or candidate["artifacts"] != artifact_map(profile)
    ):
        fail("candidate identity is not the exact deployment tuple")
    for name in ROOT_FIELDS:
        if str(candidate[name]) != package[name]:
            fail("candidate and v3 root package do not match")

    expected_manifest = {
        "format": "rog5-recovery-bundle-v2",
        "bundle": profile.bundle_id,
        "profile": profile.bundle_profile,
        "kernel_size": str(
            artifact_map(profile)["Image"]["size"]
        ),
        "kernel_sha256": artifact_map(profile)["Image"][
            "sha256"
        ],
        "dtb_size": str(
            artifact_map(profile)["board.dtb"]["size"]
        ),
        "dtb_sha256": artifact_map(profile)["board.dtb"][
            "sha256"
        ],
        "initramfs_size": str(
            artifact_map(profile)["initramfs.cpio.gz"]["size"]
        ),
        "initramfs_sha256": artifact_map(profile)[
            "initramfs.cpio.gz"
        ]["sha256"],
        "target_id": profile.target_id,
        "target_release": profile.target_release,
        "rollback_timeout": "600",
        "target_timeout": "480",
        **{name: package[name] for name in ROOT_FIELDS},
    }
    if dict(manifest) != expected_manifest:
        fail("runtime manifest and admitted candidate do not match")
    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    if manifest_sha256 == FIXTURE_MANIFEST_SHA256:
        fail("runtime manifest still carries the tracked fixture identity")

    result: OrderedDict[str, str] = OrderedDict(
        (
            ("format", "rog5-headless-ssh-v2-key-admission-v1"),
            ("candidate", profile.candidate_id),
            ("bundle", profile.bundle_id),
            ("profile", profile.bundle_profile),
            ("build_profile", profile.build_profile),
            ("target_id", profile.target_id),
            ("authorized_key_fingerprint", fingerprint),
            ("public_key_sha256", hashlib.sha256(public_key).hexdigest()),
            (
                "package_sha256",
                hashlib.sha256(package_payload).hexdigest(),
            ),
            (
                "candidate_sha256",
                hashlib.sha256(candidate_payload).hexdigest(),
            ),
            ("manifest_sha256", manifest_sha256),
            ("root_tree_sha256", package["root_tree_sha256"]),
            ("root_seal_sha256", package["root_seal_sha256"]),
            ("root_tree_entries", package["root_tree_entries"]),
            ("authority", "none"),
        )
    )
    return result


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument(
        "--admission-profile",
        choices=tuple(ADMISSION_PROFILES),
        default=DEPLOYMENT_ADMISSION_PROFILE.name,
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    values = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        result = verify(
            values.private_key,
            values.package,
            values.candidate,
            values.manifest,
            values.manifest_sha256,
            values.admission_profile,
        )
    except (
        AdmissionError,
        HEADLESS.HeadlessRootError,
        CANDIDATE.CandidateError,
        OSError,
        subprocess.SubprocessError,
    ):
        print(
            "FAIL headless SSH deployment-key admission refused",
            file=sys.stderr,
        )
        return 1
    sys.stdout.buffer.write(HEADLESS.canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
