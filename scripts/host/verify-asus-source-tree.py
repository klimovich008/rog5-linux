#!/usr/bin/env python3
"""Verify the complete accepted ASUS 5.4 stable-wrapper source tree."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
from types import ModuleType
from typing import NoReturn


PROFILE_RELATIVE = Path(
    "configs/recovery-wrapper-cache/asus-5.4-stable-recovery-v1.json"
)
SEAL_TOOL_RELATIVE = Path("scripts/host/kernel-source-seal.py")
PATCH_DIRECTORY_RELATIVE = Path("patches/asus-5.4.210")
EXPECTED_PROFILE_SHA256 = (
    "c6b06b44561506d3adfd7c3d49ef5d3476356d8aa0061fc3dec11bbf8496a4c7"
)
MARKER_PATCH_PREFIX = "/workspace/repo/patches/asus-5.4.210"
REQUIRED_PROFILE_KEYS = (
    "format",
    "source_archive_sha256",
    "source_marker_sha256",
    "source_tree_format",
    "source_tree_entries",
    "source_tree_regular_files",
    "source_tree_directories",
    "source_tree_symlinks",
    "source_tree_bytes",
    "source_tree_sha256",
    "source_seal_tool_sha256",
)


class VerificationError(RuntimeError):
    """The source tree or one of its tracked identities is not accepted."""


def fail(message: str) -> NoReturn:
    raise VerificationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: Path) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise VerificationError(f"cannot inspect {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        fail(f"not a regular file: {path}")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise VerificationError(f"cannot read {path}") from error
    after = path.lstat()
    if (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        fail(f"file changed while reading: {path}")
    return data


def load_profile(
    repo: Path, expected_profile_sha256: str
) -> dict[str, object]:
    profile_path = repo / PROFILE_RELATIVE
    raw = read_regular(profile_path)
    if sha256_bytes(raw) != expected_profile_sha256:
        fail("stable-recovery source profile identity changed")
    try:
        profile = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("source profile is not valid JSON") from error
    if not isinstance(profile, dict):
        fail("source profile is not a JSON object")
    if any(key not in profile for key in REQUIRED_PROFILE_KEYS):
        fail("source profile is missing a required identity")
    if profile["format"] != "rog5-stable-recovery-wrapper-cache-profile-v1":
        fail("source profile format changed")
    return profile


def load_seal_tool(repo: Path, profile: dict[str, object]) -> ModuleType:
    tool_path = repo / SEAL_TOOL_RELATIVE
    if sha256_bytes(read_regular(tool_path)) != profile["source_seal_tool_sha256"]:
        fail("kernel source seal implementation changed")
    spec = importlib.util.spec_from_file_location("rog5_kernel_source_seal", tool_path)
    if spec is None or spec.loader is None:
        fail("cannot load kernel source seal implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "seal_tree"):
        fail("kernel source seal implementation has no seal_tree")
    return module


def expected_marker(repo: Path, profile: dict[str, object]) -> bytes:
    patch_directory = repo / PATCH_DIRECTORY_RELATIVE
    try:
        patches = sorted(patch_directory.glob("*.patch"))
    except OSError as error:
        raise VerificationError("cannot enumerate ASUS source patches") from error
    if not patches:
        fail("ASUS source patch set is empty")
    lines = [f"source_sha256={profile['source_archive_sha256']}"]
    for patch in patches:
        digest = sha256_bytes(read_regular(patch))
        lines.append(f"{digest}  {MARKER_PATCH_PREFIX}/{patch.name}")
    return ("\n".join(lines) + "\n").encode("ascii")


def verify(
    source: Path,
    *,
    repo: Path,
    expected_profile_sha256: str = EXPECTED_PROFILE_SHA256,
) -> dict[str, str]:
    repo = repo.resolve(strict=True)
    if source.is_symlink():
        fail("ASUS source root is a symlink")
    source = source.resolve(strict=True)
    profile = load_profile(repo, expected_profile_sha256)

    marker_path = source / ".rog5-kexec-source"
    marker = read_regular(marker_path)
    if sha256_bytes(marker) != profile["source_marker_sha256"]:
        fail("ASUS source marker identity changed")
    if marker != expected_marker(repo, profile):
        fail("ASUS source marker does not bind the tracked patch set")

    seal_tool = load_seal_tool(repo, profile)
    try:
        seal = seal_tool.seal_tree(source)
    except Exception as error:
        raise VerificationError(f"cannot seal ASUS source tree: {error}") from error
    expected = {
        "tree_format": str(profile["source_tree_format"]),
        "tree_entries": str(profile["source_tree_entries"]),
        "tree_regular_files": str(profile["source_tree_regular_files"]),
        "tree_directories": str(profile["source_tree_directories"]),
        "tree_symlinks": str(profile["source_tree_symlinks"]),
        "tree_bytes": str(profile["source_tree_bytes"]),
        "tree_sha256": str(profile["source_tree_sha256"]),
    }
    if seal != expected:
        fail("ASUS source tree seal changed")
    return seal


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the complete path/type/mode/content/symlink seal of the "
            "accepted ASUS 5.4 stable-wrapper source."
        )
    )
    parser.add_argument("source", type=Path)
    values = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    seal = verify(values.source, repo=repo)
    for key, value in seal.items():
        print(f"{key}={value}")
    print("PASS accepted ASUS 5.4 source tree")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, VerificationError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
