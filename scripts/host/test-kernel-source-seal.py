#!/usr/bin/env python3
"""Tests for the canonical kernel source tree seal."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest


SEAL_PATH = Path(__file__).with_name("kernel-source-seal.py")
SPEC = importlib.util.spec_from_file_location("kernel_source_seal", SEAL_PATH)
assert SPEC is not None and SPEC.loader is not None
SEAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEAL)


class KernelSourceSealTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "source"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "Makefile").write_bytes(b"obj-y += core.o\n")
        script = self.root / "scripts/build.sh"
        script.write_bytes(b"#!/bin/sh\nexit 0\n")
        script.chmod(0o755)
        (self.root / "link").symlink_to("Makefile")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def seal(self) -> dict[str, str]:
        return SEAL.seal_tree(self.root)

    def test_seal_is_canonical_and_cli_matches(self) -> None:
        first = self.seal()
        second = self.seal()
        self.assertEqual(first, second)
        result = subprocess.run(
            ["python3", str(SEAL_PATH), str(self.root)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        expected = "".join(f"{key}={value}\n" for key, value in first.items())
        self.assertEqual(result.stdout, expected)
        self.assertEqual(first["tree_format"], "rog5-kernel-source-tree-v1")
        self.assertEqual(first["tree_entries"], "5")

    def test_host_timestamps_do_not_change_identity(self) -> None:
        before = self.seal()
        future = time.time() + 3600
        for path in (self.root, self.root / "Makefile", self.root / "scripts"):
            os.utime(path, (future, future), follow_symlinks=False)
        self.assertEqual(before, self.seal())

    def test_file_content_and_mode_changes_are_detected(self) -> None:
        before = self.seal()
        makefile = self.root / "Makefile"
        makefile.write_bytes(b"obj-y += changed.o\n")
        self.assertNotEqual(before, self.seal())
        content_changed = self.seal()
        makefile.chmod(0o600)
        self.assertNotEqual(content_changed, self.seal())

    def test_symlink_target_and_added_path_are_detected(self) -> None:
        before = self.seal()
        link = self.root / "link"
        link.unlink()
        link.symlink_to("scripts/build.sh")
        self.assertNotEqual(before, self.seal())
        changed = self.seal()
        (self.root / "extra").write_bytes(b"extra")
        self.assertNotEqual(changed, self.seal())

    def test_unsupported_entry_and_linked_root_fail_closed(self) -> None:
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        with self.assertRaises(SEAL.SourceSealError):
            self.seal()
        fifo.unlink()
        linked = self.root.parent / "linked"
        linked.symlink_to(self.root)
        with self.assertRaises(SEAL.SourceSealError):
            SEAL.seal_tree(linked)


if __name__ == "__main__":
    unittest.main()
