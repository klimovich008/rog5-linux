#!/usr/bin/env python3
"""Hostile tests for the stable-recovery wrapper cache."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


CACHE = Path(__file__).with_name("stable-recovery-wrapper-cache.py")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StableRecoveryWrapperCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.cache = self.root / "cache"
        self.cache.mkdir(mode=0o700)
        self.output_parent = self.root / "output"
        self.output_parent.mkdir()

        self.data = {
            "reference_config": b"CONFIG_TEST=y\n",
            "build_script": b"#!/bin/sh\nexit 0\n",
            "repack_script": b"#!/bin/sh\nexit 0\n",
            "boot_template": b"boot-template\n",
            "mkbootimg": b"mkbootimg\n",
            "unpack_bootimg": b"unpack-bootimg\n",
            "avbtool": b"avbtool\n",
            "source_tree_tool": b"source-tree-tool\n",
            "initramfs": b"stable-recovery-initramfs\n",
        }
        for name, data in self.data.items():
            (self.inputs / name).write_bytes(data)

        self.image = b"arm64-image-prefix" + self.data["initramfs"] + b"suffix"
        self.raw = b"raw-wrapper-image"
        self.avb = b"avb-wrapper-image"
        self.profile = {
            "format": "rog5-stable-recovery-wrapper-cache-profile-v1",
            "source_archive_sha256": digest(b"source-archive"),
            "source_marker_sha256": digest(b"source-marker"),
            "source_tree_format": "rog5-kernel-source-tree-v1",
            "source_tree_entries": 4,
            "source_tree_regular_files": 2,
            "source_tree_directories": 1,
            "source_tree_symlinks": 1,
            "source_tree_bytes": 99,
            "source_tree_sha256": digest(b"source-tree"),
            "source_seal_tool_sha256": digest(
                self.data["source_tree_tool"]
            ),
            "reference_config_sha256": digest(self.data["reference_config"]),
            "wrapper_config_sha256": digest(self.data["reference_config"]),
            "builder_image": "localhost/test-builder:pinned",
            "builder_id": digest(b"builder-id"),
            "builder_digest": f"sha256:{digest(b'builder-digest')}",
            "compiler": "test clang 1.0",
            "build_script_sha256": digest(self.data["build_script"]),
            "repack_script_sha256": digest(self.data["repack_script"]),
            "boot_template_sha256": digest(self.data["boot_template"]),
            "mkbootimg_sha256": digest(self.data["mkbootimg"]),
            "unpack_bootimg_sha256": digest(self.data["unpack_bootimg"]),
            "avbtool_sha256": digest(self.data["avbtool"]),
            "partition_size": len(self.avb),
            "cmdline_overrides": "",
            "cmdline_remove_keys": "rog5.recovery_cidr",
        }
        self.profile_path = self.inputs / "profile.json"
        self.profile_path.write_text(
            json.dumps(self.profile, indent=2) + "\n",
            encoding="ascii",
        )
        self.source_seal = self.inputs / "source.seal"
        self.source_seal.write_text(
            "\n".join(
                (
                    "tree_format=rog5-kernel-source-tree-v1",
                    "tree_entries=4",
                    "tree_regular_files=2",
                    "tree_directories=1",
                    "tree_symlinks=1",
                    "tree_bytes=99",
                    f"tree_sha256={self.profile['source_tree_sha256']}",
                    "",
                )
            ),
            encoding="ascii",
        )
        self.build_a = self.make_build("a")
        self.build_b = self.make_build("b")
        self.raw_a = self.inputs / "raw-a.img"
        self.raw_b = self.inputs / "raw-b.img"
        self.avb_a = self.inputs / "avb-a.img"
        self.avb_b = self.inputs / "avb-b.img"
        self.raw_a.write_bytes(self.raw)
        self.raw_b.write_bytes(self.raw)
        self.avb_a.write_bytes(self.avb)
        self.avb_b.write_bytes(self.avb)

    def tearDown(self) -> None:
        for path in self.root.rglob("*"):
            try:
                if path.is_dir() and not path.is_symlink():
                    path.chmod(0o700)
                elif path.is_file():
                    path.chmod(0o600)
            except FileNotFoundError:
                pass
        self.temporary.cleanup()

    def make_build(self, suffix: str) -> Path:
        root = self.root / f"build-{suffix}"
        output = root / "asus-kexec-stage"
        (output / "arch/arm64/boot").mkdir(parents=True)
        (root / "rog5-kexec-stage-initramfs.cpio.gz").write_bytes(
            self.data["initramfs"]
        )
        (output / ".config").write_bytes(self.data["reference_config"])
        (output / "arch/arm64/boot/Image").write_bytes(self.image)
        metadata = (
            f"source_sha256={self.profile['source_archive_sha256']}\n"
            "kexec_file=0\n"
            f"initramfs_sha256={digest(self.data['initramfs'])}\n"
            f"compiler={self.profile['compiler']}\n"
            f"{digest(self.data['reference_config'])}  "
            "/root/build/asus-kexec-stage/.config\n"
            f"{digest(self.image)}  "
            "/root/build/asus-kexec-stage/arch/arm64/boot/Image\n"
        )
        (output / "build-meta.txt").write_text(metadata, encoding="ascii")
        return root

    def common(self) -> list[str]:
        return [
            "--profile",
            str(self.profile_path),
            "--source-seal",
            str(self.source_seal),
            "--source-tree-tool",
            str(self.inputs / "source_tree_tool"),
            "--reference-config",
            str(self.inputs / "reference_config"),
            "--initramfs",
            str(self.inputs / "initramfs"),
            "--build-script",
            str(self.inputs / "build_script"),
            "--repack-script",
            str(self.inputs / "repack_script"),
            "--boot-template",
            str(self.inputs / "boot_template"),
            "--mkbootimg",
            str(self.inputs / "mkbootimg"),
            "--unpack-bootimg",
            str(self.inputs / "unpack_bootimg"),
            "--avbtool",
            str(self.inputs / "avbtool"),
            "--cache-root",
            str(self.cache),
        ]

    def publish(self, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(CACHE),
                "publish",
                *self.common(),
                "--source-seal-after",
                str(self.source_seal),
                "--build-a",
                str(self.build_a),
                "--build-b",
                str(self.build_b),
                "--raw-a",
                str(self.raw_a),
                "--raw-b",
                str(self.raw_b),
                "--avb-a",
                str(self.avb_a),
                "--avb-b",
                str(self.avb_b),
            ],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def entry_id(self) -> str:
        result = self.publish()
        return next(
            line.split("=", 1)[1]
            for line in result.stdout.splitlines()
            if line.startswith("cache_entry_id=")
        )

    def materialize(
        self,
        entry_id: str,
        output: Path,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(CACHE),
                "materialize",
                *self.common(),
                "--expected-entry-id",
                entry_id,
                "--output-root",
                str(output),
            ],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_publish_is_idempotent_and_materialization_is_exact(self) -> None:
        first = self.publish()
        second = self.publish()
        self.assertIn("cache_publication=new", first.stdout)
        self.assertIn("cache_publication=existing", second.stdout)
        entry_id = self.entry_id()
        output = self.output_parent / "materialized"
        self.materialize(entry_id, output)
        entry = self.cache / "entries" / entry_id
        self.assertEqual(
            sorted(path.name for path in output.iterdir()),
            sorted(path.name for path in entry.iterdir()),
        )
        for path in entry.iterdir():
            self.assertEqual(path.read_bytes(), (output / path.name).read_bytes())

    def test_twin_mismatch_is_rejected_without_publication(self) -> None:
        image = self.build_b / "asus-kexec-stage/arch/arm64/boot/Image"
        image.write_bytes(self.image + b"changed")
        result = self.publish(check=False)
        self.assertNotEqual(result.returncode, 0)
        entries = self.cache / "entries"
        self.assertTrue(not entries.exists() or not any(entries.iterdir()))

    def test_source_seal_and_dependency_mutations_are_rejected(self) -> None:
        original = self.source_seal.read_text(encoding="ascii")
        self.source_seal.write_text(
            original.replace("tree_entries=4", "tree_entries=5"),
            encoding="ascii",
        )
        self.assertNotEqual(self.publish(check=False).returncode, 0)
        self.source_seal.write_text(original, encoding="ascii")
        (self.inputs / "build_script").write_bytes(b"changed\n")
        self.assertNotEqual(self.publish(check=False).returncode, 0)

    def test_noncanonical_or_duplicate_profile_is_rejected(self) -> None:
        profile = self.profile_path.read_text(encoding="ascii")
        self.profile_path.write_text(profile.rstrip() + " \n", encoding="ascii")
        self.assertNotEqual(self.publish(check=False).returncode, 0)
        self.profile_path.write_text(
            profile.replace(
                '  "format":',
                '  "format": "duplicate",\n  "format":',
                1,
            ),
            encoding="ascii",
        )
        self.assertNotEqual(self.publish(check=False).returncode, 0)

    def test_wrong_expected_entry_and_input_drift_cannot_materialize(self) -> None:
        entry_id = self.entry_id()
        wrong = "0" * 64
        result = self.materialize(
            wrong, self.output_parent / "wrong", check=False
        )
        self.assertNotEqual(result.returncode, 0)
        (self.inputs / "initramfs").write_bytes(b"different-initramfs\n")
        result = self.materialize(
            entry_id, self.output_parent / "drift", check=False
        )
        self.assertNotEqual(result.returncode, 0)

    def test_same_inputs_cannot_bind_two_different_outputs(self) -> None:
        first_entry = self.entry_id()
        changed_image = (
            b"changed-prefix" + self.data["initramfs"] + b"changed-suffix"
        )
        for root in (self.build_a, self.build_b):
            image = root / "asus-kexec-stage/arch/arm64/boot/Image"
            image.write_bytes(changed_image)
            metadata = root / "asus-kexec-stage/build-meta.txt"
            metadata.write_text(
                (
                    f"source_sha256={self.profile['source_archive_sha256']}\n"
                    "kexec_file=0\n"
                    f"initramfs_sha256={digest(self.data['initramfs'])}\n"
                    f"compiler={self.profile['compiler']}\n"
                    f"{digest(self.data['reference_config'])}  "
                    "/root/build/asus-kexec-stage/.config\n"
                    f"{digest(changed_image)}  "
                    "/root/build/asus-kexec-stage/arch/arm64/boot/Image\n"
                ),
                encoding="ascii",
            )
        result = self.publish(check=False)
        self.assertNotEqual(result.returncode, 0)
        entries = self.cache / "entries"
        self.assertEqual(
            [path.name for path in entries.iterdir()],
            [first_entry],
        )

    def test_cache_content_and_inventory_tampering_are_rejected(self) -> None:
        entry_id = self.entry_id()
        entry = self.cache / "entries" / entry_id
        image = entry / "wrapper.Image"
        image.chmod(0o600)
        image.write_bytes(image.read_bytes() + b"tamper")
        image.chmod(0o400)
        result = self.materialize(
            entry_id, self.output_parent / "tampered", check=False
        )
        self.assertNotEqual(result.returncode, 0)
        image.chmod(0o600)
        image.write_bytes(self.image)
        image.chmod(0o400)
        entry.chmod(0o700)
        (entry / "extra").write_bytes(b"extra")
        entry.chmod(0o500)
        result = self.materialize(
            entry_id, self.output_parent / "extra", check=False
        )
        self.assertNotEqual(result.returncode, 0)

    def test_links_and_unsafe_cache_metadata_are_rejected(self) -> None:
        entry_id = self.entry_id()
        entry = self.cache / "entries" / entry_id
        image = entry / "wrapper.Image"
        entry.chmod(0o700)
        image.chmod(0o600)
        image.unlink()
        image.symlink_to(self.inputs / "initramfs")
        entry.chmod(0o500)
        result = self.materialize(
            entry_id, self.output_parent / "linked", check=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.cache.chmod(0o755)
        result = self.materialize(
            entry_id, self.output_parent / "public-cache", check=False
        )
        self.assertNotEqual(result.returncode, 0)

    def test_existing_output_is_never_replaced(self) -> None:
        entry_id = self.entry_id()
        output = self.output_parent / "existing"
        output.mkdir()
        sentinel = output / "sentinel"
        sentinel.write_bytes(b"keep")
        result = self.materialize(entry_id, output, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_build_metadata_and_embedded_initramfs_are_enforced(self) -> None:
        metadata = self.build_b / "asus-kexec-stage/build-meta.txt"
        metadata.write_text("not canonical\n", encoding="ascii")
        self.assertNotEqual(self.publish(check=False).returncode, 0)
        metadata.write_bytes(
            (
                self.build_a / "asus-kexec-stage/build-meta.txt"
            ).read_bytes()
        )
        image = self.build_a / "asus-kexec-stage/arch/arm64/boot/Image"
        other = self.build_b / "asus-kexec-stage/arch/arm64/boot/Image"
        image.write_bytes(b"no embedded initramfs")
        other.write_bytes(b"no embedded initramfs")
        self.assertNotEqual(self.publish(check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
