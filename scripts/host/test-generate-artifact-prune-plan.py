#!/usr/bin/env python3
"""Tests for the read-only artifact retention planner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


PLANNER = Path(__file__).with_name("generate-artifact-prune-plan.py")


class ArtifactPrunePlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.name", "Test"],
            check=True,
        )
        (self.repo / "artifacts/referenced").mkdir(parents=True)
        (self.repo / "artifacts/referenced/input.bin").write_bytes(b"input")
        (self.repo / "artifacts/failed-build").mkdir()
        (self.repo / "artifacts/failed-build/object.o").write_bytes(b"failed")
        leaked = (
            self.repo
            / "artifacts/recovery-stage-v12/extract-test.ABC123"
        )
        leaked.mkdir(parents=True)
        (leaked / "temporary").write_bytes(b"temporary")
        (self.repo / "build/qemu-smoke-kernel").mkdir(parents=True)
        (self.repo / "build/qemu-smoke-kernel/Image").write_bytes(b"kernel")
        (self.repo / "build/other-cache").mkdir()
        (self.repo / "build/other-cache/object.o").write_bytes(b"cache")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/usage.md").write_text(
            "Use artifacts/referenced/input.bin.\n", encoding="utf-8"
        )
        (self.repo / "test-results").mkdir()
        (self.repo / "test-results/old-artifact-prune-plan.json").write_text(
            '{"path":"artifacts/failed-build"}\n', encoding="ascii"
        )
        (self.repo / "manifests").mkdir()
        digest = hashlib.sha256(b"input").hexdigest()
        (self.repo / "manifests/artifacts.tsv").write_text(
            "name\tsize\tsha256\trole\ttracked\n"
            f"artifacts/referenced/input.bin\t5\t{digest}\tinput\tno\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "git",
                "-C",
                self.repo,
                "add",
                "docs/usage.md",
                "manifests/artifacts.tsv",
                "test-results/old-artifact-prune-plan.json",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", self.repo, "commit", "-qm", "fixture"],
            check=True,
        )
        self.output = self.repo / "plan.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_planner(self, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                PLANNER,
                "--repo",
                self.repo,
                "--output",
                self.output,
            ],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_plan_is_conservative_machine_readable_and_non_destructive(self) -> None:
        self.run_planner()
        plan = json.loads(self.output.read_text(encoding="ascii"))
        self.assertEqual(plan["format"], "rog5-artifact-prune-plan-v1")
        self.assertTrue(plan["policy"]["read_only"])
        self.assertFalse(plan["policy"]["deletion_supported"])
        entries = {entry["path"]: entry for entry in plan["entries"]}

        referenced = entries["artifacts/referenced"]
        self.assertEqual(referenced["decision"], "retain")
        self.assertEqual(
            referenced["manifest"]["status"],
            "listed-size-match-hash-unverified",
        )
        self.assertIn("docs/usage.md:1", referenced["tracked_references"])

        self.assertEqual(
            entries["artifacts/failed-build"]["decision"],
            "prune_candidate",
        )
        self.assertEqual(
            entries[
                "artifacts/recovery-stage-v12/extract-test.ABC123"
            ]["decision"],
            "prune_candidate",
        )
        self.assertEqual(
            entries["build/qemu-smoke-kernel"]["reproduction"]["command"],
            "scripts/host/build-qemu-smoke-kernel.sh "
            "build/qemu-linux-source build/qemu-smoke-kernel",
        )
        self.assertEqual(entries["build/other-cache"]["decision"], "review")
        for path in (
            self.repo / "artifacts/referenced/input.bin",
            self.repo / "artifacts/failed-build/object.o",
            self.repo / "build/other-cache/object.o",
        ):
            self.assertTrue(path.exists())

    def test_existing_output_is_never_replaced(self) -> None:
        self.output.write_text("sentinel\n", encoding="ascii")
        result = self.run_planner(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(encoding="ascii"), "sentinel\n")

    def test_sensitive_ignored_unit_is_not_published(self) -> None:
        sensitive = self.repo / "artifacts/private-ssh-key"
        sensitive.mkdir()
        (sensitive / "fixture").write_text("not-a-key\n", encoding="ascii")
        result = self.run_planner(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive-looking inventory unit", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
