#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Hostile tests for immutable ignored inputs in deployment worktrees."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
LAUNCHERS = (
    REPO / "scripts/host/build-headless-ssh-deployment-candidate.sh",
    REPO / "scripts/host/build-early-target-diagnostic-deployment-candidate.sh",
)


def load_launcher(path: Path):
    name = f"rog5_checkpoint_input_{path.stem.replace('-', '_')}"
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    specification = importlib.util.spec_from_loader(name, loader)
    if specification is None:
        raise RuntimeError("cannot load deployment launcher")
    module = importlib.util.module_from_spec(specification)
    loader.exec_module(module)
    return module


class CheckpointInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.snapshot = self.root / "snapshot"
        self.repository.mkdir(mode=0o700)
        self.snapshot.mkdir(mode=0o700)
        (self.snapshot / ".gitignore").write_text("artifacts/*\n", encoding="ascii")
        subprocess.run(
            ["/usr/bin/git", "init", "-q", str(self.snapshot)], check=True
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(self.snapshot),
                "-c",
                "user.name=ROG5 Test",
                "-c",
                "user.email=rog5-test@example.invalid",
                "add",
                ".gitignore",
            ],
            check=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(self.snapshot),
                "-c",
                "user.name=ROG5 Test",
                "-c",
                "user.email=rog5-test@example.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            check=True,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def contract(self, relative: str, payload: bytes, mode: int = 0o644):
        return (
            relative,
            len(payload),
            mode,
            hashlib.sha256(payload).hexdigest(),
        )

    def source(self, relative: str, payload: bytes, mode: int = 0o644) -> Path:
        path = self.repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(mode)
        return path

    def test_exact_regular_input_is_copied_without_aliasing(self) -> None:
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher.name):
                module = load_launcher(launcher)
                payload = b"reviewed ignored release input\n"
                relative = "artifacts/fixture/release.bin"
                source = self.source(relative, payload)
                module.stage_checkpoint_inputs(
                    self.repository,
                    self.snapshot,
                    (self.contract(relative, payload),),
                )
                destination = self.snapshot / relative
                self.assertEqual(destination.read_bytes(), payload)
                self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o644)
                self.assertNotEqual(source.stat().st_ino, destination.stat().st_ino)
                destination.unlink()

    def test_missing_symlink_wrong_mode_hash_and_occupied_output_fail(self) -> None:
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher.name):
                module = load_launcher(launcher)
                payload = b"exact\n"
                relative = "artifacts/fixture/input.bin"
                contract = (self.contract(relative, payload),)
                source_path = self.repository / relative
                destination_path = self.snapshot / relative
                for path in (source_path, destination_path):
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass

                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, contract
                    )

                source = self.source(relative, payload, 0o600)
                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, contract
                    )
                source.chmod(0o644)

                wrong_hash = (
                    relative,
                    len(payload),
                    0o644,
                    "0" * 64,
                )
                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, (wrong_hash,)
                    )

                source.unlink()
                source.symlink_to("missing-target")
                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, contract
                    )
                source.unlink()
                self.source(relative, payload)

                destination = self.snapshot / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"occupied")
                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, contract
                    )
                self.assertEqual(destination.read_bytes(), b"occupied")
                destination.unlink()

    def test_absolute_parent_alias_and_duplicate_contracts_fail(self) -> None:
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher.name):
                module = load_launcher(launcher)
                payload = b"exact\n"
                relative = "artifacts/fixture/input.bin"
                contract = self.contract(relative, payload)
                self.source(relative, payload)
                for hostile in (
                    ((str(self.repository / relative), *contract[1:]),),
                    (("artifacts/../fixture/input.bin", *contract[1:]),),
                    (contract, contract),
                ):
                    with self.assertRaises(SystemExit):
                        module.stage_checkpoint_inputs(
                            self.repository, self.snapshot, hostile
                        )

    def test_source_and_destination_parent_symlinks_fail(self) -> None:
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher.name):
                module = load_launcher(launcher)
                payload = b"exact\n"
                relative = "artifacts/aliased/input.bin"
                contract = (self.contract(relative, payload),)
                outside = self.root / f"outside-{launcher.stem}"
                outside.mkdir()

                source_parent = self.repository / "artifacts/aliased"
                if source_parent.is_symlink():
                    source_parent.unlink()
                elif source_parent.is_dir():
                    source_parent.rmdir()
                source_parent.parent.mkdir(parents=True, exist_ok=True)
                source_parent.symlink_to(outside, target_is_directory=True)
                (outside / "input.bin").write_bytes(payload)
                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, contract
                    )
                source_parent.unlink()
                (outside / "input.bin").unlink()

                self.source(relative, payload)
                destination_parent = self.snapshot / "artifacts/aliased"
                destination_parent.parent.mkdir(parents=True, exist_ok=True)
                destination_parent.symlink_to(outside, target_is_directory=True)
                with self.assertRaises(SystemExit):
                    module.stage_checkpoint_inputs(
                        self.repository, self.snapshot, contract
                    )
                self.assertFalse((outside / "input.bin").exists())
                destination_parent.unlink()
                (self.repository / relative).unlink()
                source_parent.rmdir()

    def test_source_change_during_copy_fails_and_removes_output(self) -> None:
        for launcher in LAUNCHERS:
            with self.subTest(launcher=launcher.name):
                module = load_launcher(launcher)
                relative = "artifacts/fixture/changing.bin"
                payload = b"A" * (1024 * 1024 + 1)
                source = self.source(relative, payload)
                contract = (self.contract(relative, payload),)
                original_read = module.os.read
                changed = False

                def hostile_read(descriptor: int, count: int) -> bytes:
                    nonlocal changed
                    block = original_read(descriptor, count)
                    if block and not changed:
                        changed = True
                        with source.open("r+b") as stream:
                            stream.seek(-1, os.SEEK_END)
                            stream.write(b"B")
                            stream.flush()
                            os.fsync(stream.fileno())
                    return block

                module.os.read = hostile_read
                try:
                    with self.assertRaises(SystemExit):
                        module.stage_checkpoint_inputs(
                            self.repository, self.snapshot, contract
                        )
                finally:
                    module.os.read = original_read
                self.assertTrue(changed)
                self.assertFalse((self.snapshot / relative).exists())
                source.unlink()


if __name__ == "__main__":
    unittest.main()
