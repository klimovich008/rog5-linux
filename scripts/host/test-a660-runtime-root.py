#!/usr/bin/env python3
"""Fault-test the versioned A660 runtime-root transaction."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/host/a660-runtime-root.py"
PUBLISH_MODULE_PATH = REPO / "scripts/host/a660-runtime-publish.py"


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_a660_runtime_root",
        MODULE_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load A660 runtime-root module")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


RUNTIME = load_module()


def load_publisher():
    specification = importlib.util.spec_from_file_location(
        "rog5_a660_runtime_publish",
        PUBLISH_MODULE_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load A660 runtime publisher")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


PUBLISHER = load_publisher()


class Fixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.parent = Path(self.temporary.name)
        self.parent.chmod(0o700)
        self.root = self.parent / "root"
        self.base = self.parent / "base"
        self.tools = self.parent / "tools"
        self.identity = self.parent / "identity"
        self.base_seal = b"fixture successor-v3 seal\n"
        self.base_seal_sha256 = hashlib.sha256(self.base_seal).hexdigest()
        self.base_verifier_sha256 = RUNTIME.sha256_file(
            RUNTIME.BASE_VERIFIERS["arch-successor-v3"]
        )
        self.base_archive_sha256 = "a" * 64
        self._make_root()
        shutil.copytree(
            self.root,
            self.base,
            copy_function=shutil.copy2,
            symlinks=True,
        )
        self.root.chmod(0o555)
        self.base.chmod(0o555)
        self._make_tools()

    def cleanup(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write(path: Path, payload: bytes, mode: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(mode)

    @staticmethod
    def _normalize(root: Path) -> None:
        for path in sorted(root.rglob("*"), reverse=True):
            if not path.is_symlink():
                os.utime(
                    path,
                    ns=(RUNTIME.EPOCH * 1_000_000_000,) * 2,
                )
        os.utime(
            root,
            ns=(RUNTIME.EPOCH * 1_000_000_000,) * 2,
        )

    def _make_root(self) -> None:
        self.root.mkdir(mode=0o755)
        self._write(
            self.root / "etc/rog5/arch-successor-v3-export",
            self.base_seal,
            0o444,
        )
        for _name, relative in RUNTIME.COMMAND_PATHS.items():
            if relative in {
                Path("usr/local/libexec/rog5-cgroup-exec"),
                Path("usr/local/libexec/rog5-vulkan-submit"),
                Path("usr/local/sbin/persistent-root-verify"),
            }:
                continue
            if relative == Path(
                "usr/local/bin/rog5-collect-baseline.sh"
            ):
                payload = RUNTIME.BASELINE_SOURCE.read_bytes()
            else:
                payload = (
                    f"#!/bin/sh\n# {relative}\nexit 0\n".encode()
                )
            self._write(
                self.root / relative,
                payload,
                0o755,
            )
        (self.root / "usr/local/libexec").mkdir(
            parents=True,
            exist_ok=True,
        )
        (self.root / "usr/local/sbin").mkdir(
            parents=True,
            exist_ok=True,
        )
        self._normalize(self.root)

    def _make_tools(self) -> None:
        self.tools.mkdir(mode=0o700)
        hashes: dict[str, tuple[int, str]] = {}
        for name in RUNTIME.TOOL_NAMES:
            payload = f"#!/bin/sh\n# fixture {name}\nexit 0\n".encode()
            self._write(self.tools / name, payload, 0o755)
            hashes[name] = (len(payload), hashlib.sha256(payload).hexdigest())
        values = OrderedDict(
            (
                ("format", "rog5-a660-runtime-tools-v1"),
                ("source_date_epoch", str(RUNTIME.EPOCH)),
                ("static_builder_image_id", "b" * 64),
                ("vulkan_builder_image_id", "c" * 64),
                ("builder_packages_sha256", "d" * 64),
            )
        )
        for name in RUNTIME.TOOL_NAMES:
            prefix = name.replace("-", "_")
            values[f"{prefix}_size"] = str(hashes[name][0])
            values[f"{prefix}_sha256"] = hashes[name][1]
        self._write(
            self.tools / "manifest",
            RUNTIME.canonical_bytes(values),
            0o400,
        )
        self._normalize(self.tools)
        self.tools_manifest_sha256 = hashlib.sha256(
            (self.tools / "manifest").read_bytes()
        ).hexdigest()

    def prepare(
        self,
        *,
        base_verifier_sha256: str | None = None,
        approved_tools_manifest_sha256: str | None = None,
    ):
        return RUNTIME.prepare_runtime_root(
            self.root,
            self.base,
            self.tools,
            self.identity,
            base_generation="arch-successor-v3",
            base_seal_sha256=self.base_seal_sha256,
            base_verifier_sha256=(
                base_verifier_sha256 or self.base_verifier_sha256
            ),
            base_archive_size="123456",
            base_archive_sha256=self.base_archive_sha256,
            kernel_release="7.1.4-fixture",
            approved_tools_manifest_sha256=(
                approved_tools_manifest_sha256
                or self.tools_manifest_sha256
            ),
        )

    def verify(self):
        return RUNTIME.verify_runtime_root(
            self.root,
            self.identity,
            inspect_elf_files=False,
            independent_verification=False,
        )


class RuntimeRootTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Fixture()

    def tearDown(self) -> None:
        self.fixture.cleanup()

    def test_preparation_and_verification_bind_every_runtime_input(self) -> None:
        prepared = self.fixture.prepare()
        verified = self.fixture.verify()
        self.assertEqual(prepared, verified)
        self.assertEqual(prepared["profile"], "network-root-v1")
        self.assertEqual(prepared["root_generation"], "arch-a")
        self.assertEqual(prepared["root_subtree"], "/")
        self.assertEqual(prepared["base_generation"], "arch-successor-v3")
        self.assertEqual(
            prepared["base_export_verifier_sha256"],
            self.fixture.base_verifier_sha256,
        )
        self.assertGreater(int(prepared["root_tree_entries"]), 0)
        self.assertEqual(
            (self.fixture.root / ".rog5-persistent-seal").stat().st_mode
            & 0o777,
            0o444,
        )
        self.assertEqual(self.fixture.root.stat().st_mode & 0o777, 0o555)
        self.assertEqual(self.fixture.identity.stat().st_mode & 0o777, 0o444)

    def test_two_equal_inputs_produce_equal_runtime_root_identity(self) -> None:
        first = self.fixture.prepare()
        second_fixture = Fixture()
        self.addCleanup(second_fixture.cleanup)
        second = second_fixture.prepare()
        for key in (
            "runtime_provenance_sha256",
            "a660_acceptance_sha256",
            "command_manifest_sha256",
            "persistent_root_verify_sha256",
            "rog5_cgroup_exec_sha256",
            "rog5_vulkan_submit_sha256",
            "root_tree_entries",
            "root_tree_sha256",
            "root_seal_sha256",
        ):
            self.assertEqual(first[key], second[key], key)

    def test_command_mutation_retracts_complete_root_acceptance(self) -> None:
        self.fixture.prepare()
        command = self.fixture.root / "usr/bin/vulkaninfo"
        command.write_bytes(command.read_bytes() + b"# mutation\n")
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.verify()

    def test_tool_mutation_retracts_complete_root_acceptance(self) -> None:
        self.fixture.prepare()
        helper = (
            self.fixture.root
            / "usr/local/libexec/rog5-vulkan-submit"
        )
        helper.write_bytes(helper.read_bytes() + b"# mutation\n")
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.verify()

    def test_identity_mutation_is_rejected(self) -> None:
        self.fixture.prepare()
        payload = self.fixture.identity.read_text(encoding="ascii")
        self.fixture.identity.chmod(0o600)
        self.fixture.identity.write_text(
            payload.replace(
                "root_tree_sha256=",
                "root_tree_sha256=0",
                1,
            ),
            encoding="ascii",
        )
        self.fixture.identity.chmod(0o444)
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.verify()

    def test_existing_identity_refuses_before_root_mutation(self) -> None:
        self.fixture.identity.write_text("occupied\n", encoding="ascii")
        before = sorted(
            path.relative_to(self.fixture.root)
            for path in self.fixture.root.rglob("*")
        )
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.prepare()
        after = sorted(
            path.relative_to(self.fixture.root)
            for path in self.fixture.root.rglob("*")
        )
        self.assertEqual(before, after)
        self.assertFalse(
            (self.fixture.root / ".rog5-persistent-seal").exists()
        )

    def test_tool_manifest_hash_substitution_is_rejected(self) -> None:
        manifest = self.fixture.tools / "manifest"
        payload = manifest.read_text(encoding="ascii")
        manifest.chmod(0o600)
        manifest.write_text(
            payload.replace(
                "rog5_vulkan_submit_sha256=",
                f"rog5_vulkan_submit_sha256={'e' * 64}\n#",
                1,
            ),
            encoding="ascii",
        )
        manifest.chmod(0o400)
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.prepare()

    def test_unapproved_tool_manifest_is_rejected(self) -> None:
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.prepare(
                approved_tools_manifest_sha256="e" * 64,
            )
        self.assertFalse(
            (self.fixture.root / ".rog5-persistent-seal").exists()
        )

    def test_base_verifier_hash_substitution_is_rejected(self) -> None:
        with self.assertRaises(RUNTIME.RuntimeRootError):
            self.fixture.prepare(base_verifier_sha256="f" * 64)
        self.assertFalse(
            (self.fixture.root / ".rog5-persistent-seal").exists()
        )

    def test_preexisting_base_mutation_fails_delta_verification(self) -> None:
        self.fixture.prepare()
        RUNTIME.verify_base_preservation(
            self.fixture.base,
            self.fixture.root,
            owner=os.geteuid(),
        )
        command = self.fixture.root / "usr/bin/vulkaninfo"
        command.write_bytes(command.read_bytes() + b"# base mutation\n")
        with self.assertRaises(RUNTIME.RuntimeRootError):
            RUNTIME.verify_base_preservation(
                self.fixture.base,
                self.fixture.root,
                owner=os.geteuid(),
            )

    def test_unapproved_addition_fails_delta_verification(self) -> None:
        self.fixture.prepare()
        self.fixture._write(
            self.fixture.root / "usr/local/bin/not-approved",
            b"unexpected\n",
            0o755,
        )
        with self.assertRaises(RUNTIME.RuntimeRootError):
            RUNTIME.verify_base_preservation(
                self.fixture.base,
                self.fixture.root,
                owner=os.geteuid(),
            )


class AtomicPublisherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.parent = Path(self.temporary.name)
        self.parent.chmod(0o700)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_atomic_publication_preserves_directory_identity(self) -> None:
        stage = self.parent / "artifact.partial"
        output = self.parent / "artifact"
        stage.mkdir(mode=0o700)
        (stage / "marker").write_text("prepared\n", encoding="ascii")
        identity = stage.stat().st_dev, stage.stat().st_ino
        PUBLISHER.atomic_publish(stage, output)
        self.assertFalse(stage.exists())
        self.assertEqual(
            identity,
            (output.stat().st_dev, output.stat().st_ino),
        )
        self.assertEqual(
            (output / "marker").read_text(encoding="ascii"),
            "prepared\n",
        )

    def test_renameat2_collision_never_replaces_competitor(self) -> None:
        stage = self.parent / "artifact.partial"
        output = self.parent / "artifact"
        stage.mkdir(mode=0o700)
        (stage / "marker").write_text("ours\n", encoding="ascii")

        def inject_competitor() -> None:
            output.mkdir(mode=0o700)
            (output / "marker").write_text("theirs\n", encoding="ascii")

        with self.assertRaises(PUBLISHER.PublicationError):
            PUBLISHER.atomic_publish(
                stage,
                output,
                before_rename=inject_competitor,
            )
        self.assertEqual(
            (stage / "marker").read_text(encoding="ascii"),
            "ours\n",
        )
        self.assertEqual(
            (output / "marker").read_text(encoding="ascii"),
            "theirs\n",
        )

    def test_post_rename_replacement_is_never_followed_or_cleaned(self) -> None:
        stage = self.parent / "artifact.partial"
        output = self.parent / "artifact"
        displaced = self.parent / "published-original"
        target = self.parent / "unrelated"
        stage.mkdir(mode=0o700)
        target.mkdir(mode=0o700)
        (stage / "marker").write_text("ours\n", encoding="ascii")
        (target / "marker").write_text("untouched\n", encoding="ascii")

        def replace_published_name() -> None:
            output.rename(displaced)
            output.symlink_to(target, target_is_directory=True)

        with self.assertRaises(PUBLISHER.PublicationError):
            PUBLISHER.atomic_publish(
                stage,
                output,
                after_rename=replace_published_name,
            )
        self.assertTrue(output.is_symlink())
        self.assertEqual(
            (displaced / "marker").read_text(encoding="ascii"),
            "ours\n",
        )
        self.assertEqual(
            (target / "marker").read_text(encoding="ascii"),
            "untouched\n",
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
