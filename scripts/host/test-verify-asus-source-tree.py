#!/usr/bin/env python3
"""Behavioral tests for the accepted ASUS source-tree verifier."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile


SCRIPT = Path(__file__).with_name("verify-asus-source-tree.py")
SEAL_TOOL = Path(__file__).with_name("kernel-source-seal.py")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_script():
    spec = importlib.util.spec_from_file_location("verify_asus_source_tree", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load ASUS source verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module, source: Path, repo: Path, profile_sha256: str) -> None:
    try:
        with redirect_stdout(io.StringIO()):
            module.verify(
                source,
                repo=repo,
                expected_profile_sha256=profile_sha256,
            )
    except module.VerificationError:
        return
    raise AssertionError("mutated ASUS source fixture was accepted")


def main() -> int:
    module = load_script()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        repo = root / "repo"
        source = root / "source"
        patch_directory = repo / module.PATCH_DIRECTORY_RELATIVE
        profile_path = repo / module.PROFILE_RELATIVE
        seal_path = repo / module.SEAL_TOOL_RELATIVE
        patch_directory.mkdir(parents=True)
        profile_path.parent.mkdir(parents=True)
        seal_path.parent.mkdir(parents=True, exist_ok=True)
        source.mkdir()
        shutil.copyfile(SEAL_TOOL, seal_path)

        patches = {
            "0001-first.patch": b"first patch\n",
            "0002-second.patch": b"second patch\n",
        }
        for name, data in patches.items():
            (patch_directory / name).write_bytes(data)
        source_payload = source / "payload.c"
        source_payload.write_bytes(b"accepted source\n")
        source_payload.chmod(0o644)

        archive_sha256 = digest(b"source archive")
        marker_lines = [f"source_sha256={archive_sha256}"]
        for name in sorted(patches):
            marker_lines.append(
                f"{digest(patches[name])}  {module.MARKER_PATCH_PREFIX}/{name}"
            )
        marker = source / ".rog5-kexec-source"
        marker.write_text("\n".join(marker_lines) + "\n", encoding="ascii")
        marker.chmod(0o644)

        seal_module_spec = importlib.util.spec_from_file_location(
            "fixture_kernel_source_seal", seal_path
        )
        assert seal_module_spec is not None and seal_module_spec.loader is not None
        seal_module = importlib.util.module_from_spec(seal_module_spec)
        seal_module_spec.loader.exec_module(seal_module)
        source_seal = seal_module.seal_tree(source)
        profile = {
            "format": "rog5-stable-recovery-wrapper-cache-profile-v1",
            "source_archive_sha256": archive_sha256,
            "source_marker_sha256": digest(marker.read_bytes()),
            "source_tree_format": source_seal["tree_format"],
            "source_tree_entries": int(source_seal["tree_entries"]),
            "source_tree_regular_files": int(source_seal["tree_regular_files"]),
            "source_tree_directories": int(source_seal["tree_directories"]),
            "source_tree_symlinks": int(source_seal["tree_symlinks"]),
            "source_tree_bytes": int(source_seal["tree_bytes"]),
            "source_tree_sha256": source_seal["tree_sha256"],
            "source_seal_tool_sha256": digest(seal_path.read_bytes()),
        }
        profile_raw = (
            json.dumps(profile, indent=2, sort_keys=True) + "\n"
        ).encode("ascii")
        profile_path.write_bytes(profile_raw)
        profile_sha256 = digest(profile_raw)

        with redirect_stdout(io.StringIO()):
            verified = module.verify(
                source,
                repo=repo,
                expected_profile_sha256=profile_sha256,
            )
        assert verified == source_seal

        source_payload.write_bytes(b"mutated source\n")
        expect_rejected(module, source, repo, profile_sha256)
        source_payload.write_bytes(b"accepted source\n")

        source_payload.chmod(0o600)
        expect_rejected(module, source, repo, profile_sha256)
        source_payload.chmod(0o644)

        first_patch = patch_directory / "0001-first.patch"
        first_patch.write_bytes(b"mutated patch\n")
        expect_rejected(module, source, repo, profile_sha256)
        first_patch.write_bytes(patches[first_patch.name])

        extra_patch = patch_directory / "0003-extra.patch"
        extra_patch.write_bytes(b"unrecorded patch\n")
        expect_rejected(module, source, repo, profile_sha256)
        extra_patch.unlink()

        marker_backup = source / "marker.backup"
        marker.rename(marker_backup)
        marker.symlink_to(marker_backup.name)
        expect_rejected(module, source, repo, profile_sha256)
        marker.unlink()
        marker_backup.rename(marker)

        profile_path.write_bytes(profile_raw + b"\n")
        expect_rejected(module, source, repo, profile_sha256)

    print("PASS accepted ASUS source-tree verifier rejects identity mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
