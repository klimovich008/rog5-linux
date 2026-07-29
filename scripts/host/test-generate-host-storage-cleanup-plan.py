#!/usr/bin/env python3
"""Tests for the read-only host-storage cleanup planner."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


PLANNER = Path(__file__).with_name(
    "generate-host-storage-cleanup-plan.py"
)


class HostStorageCleanupPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.data = root / "data"
        self.cache = root / "cache"
        self.volume_root = root / "volumes"
        self.repo.mkdir()
        (self.data / "dev").mkdir(parents=True)
        self.cache.mkdir()
        self.volume_root.mkdir()

        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.name", "Test"],
            check=True,
        )
        (self.repo / "docs").mkdir()
        (self.repo / "docs/refs.md").write_text(
            "Keep active-source and rog5-active-volume and retained-cache.\n",
            encoding="utf-8",
        )
        (self.repo / "test-results").mkdir()
        (
            self.repo
            / "test-results/old-host-storage-cleanup-plan.json"
        ).write_text(
            '{"unit":"old-volume"}\n',
            encoding="ascii",
        )
        subprocess.run(
            ["git", "-C", self.repo, "add", "docs", "test-results"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", self.repo, "commit", "-qm", "fixture"],
            check=True,
        )

        dev = self.data / "dev"
        (dev / "old-build.ABC123").mkdir()
        (dev / "old-build.ABC123/object.o").write_bytes(b"generated")
        (dev / "unique-debug").mkdir()
        (dev / "unique-debug/trace.log").write_bytes(b"evidence")
        (dev / "active-source").mkdir()
        (dev / "active-source/source.c").write_bytes(b"active")
        dirty = dev / "dirty-tree"
        dirty.mkdir()
        subprocess.run(["git", "init", "-q", dirty], check=True)
        subprocess.run(
            ["git", "-C", dirty, "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", dirty, "config", "user.name", "Test"],
            check=True,
        )
        (dirty / "driver.c").write_text("base\n", encoding="ascii")
        subprocess.run(["git", "-C", dirty, "add", "driver.c"], check=True)
        subprocess.run(
            ["git", "-C", dirty, "commit", "-qm", "base"],
            check=True,
        )
        (dirty / "driver.c").write_text("changed\n", encoding="ascii")

        (self.cache / "rebuild-cache").mkdir()
        (self.cache / "rebuild-cache/value").write_bytes(b"cache")
        (self.cache / "retained-cache").mkdir()
        (self.cache / "retained-cache/value").write_bytes(b"retained")

        self.volumes: list[dict[str, object]] = []
        for name, driver, scope in (
            ("rog5-active-volume", "local", "local"),
            ("rog5-old-volume", "local", "local"),
            ("foreign-volume", "local", "local"),
            ("rog5-remote-volume", "remote", "global"),
        ):
            path = self.volume_root / name
            (path / "_data").mkdir(parents=True)
            (path / "_data/value").write_bytes(name.encode("ascii"))
            self.volumes.append(
                {
                    "Name": name,
                    "Mountpoint": str(path / "_data"),
                    "MountCount": 0,
                    "Driver": driver,
                    "Scope": scope,
                    "CreatedAt": "2026-07-29T00:00:00+00:00",
                    "Options": {},
                }
            )
        self.volumes_json = root / "volumes.json"
        self.volumes_json.write_text(
            json.dumps(self.volumes), encoding="ascii"
        )
        self.output = root / "plan.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_planner(
        self,
        *,
        cache: Path | None = None,
        containers: int = 0,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                PLANNER,
                "--repo",
                self.repo,
                "--rog5-data-root",
                self.data,
                "--rog5-cache-root",
                cache or self.cache,
                "--podman-volumes-json",
                self.volumes_json,
                "--podman-container-count",
                str(containers),
                "--podman-volume-root",
                self.volume_root,
                "--output",
                self.output,
            ],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_plan_is_conservative_scoped_and_non_destructive(self) -> None:
        self.run_planner()
        encoded = self.output.read_text(encoding="ascii")
        plan = json.loads(encoded)
        self.assertEqual(
            plan["format"], "rog5-host-storage-cleanup-plan-v1"
        )
        self.assertTrue(plan["policy"]["read_only"])
        self.assertFalse(plan["policy"]["deletion_supported"])
        self.assertNotIn(str(self.temporary.name), encoded)
        entries = {entry["id"]: entry for entry in plan["entries"]}

        self.assertEqual(
            entries["rog5-dev:old-build.ABC123"]["decision"],
            "prune_candidate",
        )
        self.assertEqual(
            entries["rog5-dev:unique-debug"]["decision"], "review"
        )
        self.assertEqual(
            entries["rog5-dev:active-source"]["decision"], "retain"
        )
        dirty = entries["rog5-dev:dirty-tree"]
        self.assertEqual(dirty["decision"], "retain")
        self.assertTrue(dirty["embedded_git"][0]["dirty"])
        self.assertRegex(
            dirty["embedded_git"][0]["head_diff_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertEqual(
            entries["rog5-cache:rebuild-cache"]["decision"],
            "prune_candidate",
        )
        self.assertEqual(
            entries["rog5-cache:retained-cache"]["decision"], "retain"
        )
        self.assertEqual(
            entries["podman-volume:rog5-active-volume"]["decision"], "retain"
        )
        self.assertEqual(
            entries["podman-volume:rog5-old-volume"]["decision"],
            "prune_candidate",
        )
        self.assertEqual(
            entries["podman-volume:foreign-volume"]["decision"], "retain"
        )
        self.assertEqual(
            entries["podman-volume:rog5-remote-volume"]["decision"], "retain"
        )
        self.assertEqual(plan["runtime"]["podman_container_count"], 0)
        self.assertGreater(
            plan["summary"]["decisions"]["prune_candidate"][
                "allocated_size_bytes"
            ],
            0,
        )

        for path in (
            self.data / "dev/old-build.ABC123/object.o",
            self.cache / "rebuild-cache/value",
            self.volume_root / "rog5-old-volume/_data/value",
        ):
            self.assertTrue(path.exists())

    def test_any_container_retains_all_volumes(self) -> None:
        self.run_planner(containers=1)
        plan = json.loads(self.output.read_text(encoding="ascii"))
        entries = {entry["id"]: entry for entry in plan["entries"]}
        self.assertEqual(
            entries["podman-volume:rog5-old-volume"]["decision"], "retain"
        )

    def test_existing_output_is_never_replaced(self) -> None:
        self.output.write_text("sentinel\n", encoding="ascii")
        result = self.run_planner(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(encoding="ascii"), "sentinel\n")

    def test_dangling_output_link_is_never_followed(self) -> None:
        target = self.output.with_name("link-target.json")
        self.output.symlink_to(target)
        result = self.run_planner(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse(target.exists())

    def test_linked_inventory_root_is_rejected(self) -> None:
        linked_cache = self.cache.parent / "linked-cache"
        linked_cache.symlink_to(self.cache, target_is_directory=True)
        result = self.run_planner(cache=linked_cache, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inventory path contains a symlink", result.stderr)
        self.assertFalse(self.output.exists())

    def test_linked_git_marker_is_retained_without_following_it(self) -> None:
        linked = self.data / "dev/generated-build-linked-git"
        linked.mkdir()
        (linked / ".git").symlink_to(
            self.data / "dev/dirty-tree/.git", target_is_directory=True
        )
        self.run_planner()
        plan = json.loads(self.output.read_text(encoding="ascii"))
        entries = {entry["id"]: entry for entry in plan["entries"]}
        entry = entries["rog5-dev:generated-build-linked-git"]
        self.assertEqual(entry["decision"], "retain")
        self.assertIn("could not be safely audited", entry["reason"])
        self.assertIsNotNone(entry["embedded_git"][0]["audit_error"])
        self.assertIsNone(entry["embedded_git"][0]["head"])

    def test_sensitive_unit_is_not_published(self) -> None:
        sensitive = self.cache / "private-key"
        sensitive.mkdir()
        result = self.run_planner(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive-looking inventory unit", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
