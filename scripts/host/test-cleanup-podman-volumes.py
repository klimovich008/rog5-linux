#!/usr/bin/env python3
"""Tests for exact, plan-bound Podman volume cleanup."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone


CLEANUP = Path(__file__).with_name("cleanup-podman-volumes.py")


class PodmanVolumeCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.name", "Test"],
            check=True,
        )
        (self.repo / "tracked").write_text("fixture\n", encoding="ascii")
        subprocess.run(["git", "-C", self.repo, "add", "tracked"], check=True)
        subprocess.run(
            ["git", "-C", self.repo, "commit", "-qm", "fixture"],
            check=True,
        )
        self.commit = subprocess.run(
            ["git", "-C", self.repo, "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

        self.graph_root = root / "container-storage"
        self.volume_root = self.graph_root / "volumes"
        self.volume_root.mkdir(parents=True)
        self.state = root / "podman-state.json"
        self.write_state()
        self.fake_podman = root / "podman"
        self.fake_podman.write_text(
            """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys

state_path = Path(os.environ["FAKE_PODMAN_STATE"])
state = json.loads(state_path.read_text())
args = sys.argv[1:]
if args == ["info", "--format", "json"]:
    print(json.dumps({
        "host": {
            "security": {"rootless": state.get("rootless", True)},
            "serviceIsRemote": state.get("remote", False),
        },
        "store": {
            "graphRoot": state["graph_root"],
            "volumePath": state["volume_root"],
        },
    }))
elif args == ["ps", "-a", "--format", "json"]:
    print(json.dumps(state["containers"]))
elif args == ["volume", "ls", "--format", "json"]:
    print(json.dumps(state["volumes"]))
elif args[:4] == ["volume", "inspect", "--format", "json"]:
    names = args[4:]
    rows = [row for row in state["volumes"] if row["Name"] in names]
    if len(rows) != len(names):
        raise SystemExit(1)
    print(json.dumps(rows))
elif args[:2] == ["unshare", "du"]:
    raise SystemExit(subprocess.run(args[1:]).returncode)
elif len(args) == 4 and args[:3] == ["volume", "rm", "--"]:
    name = args[3]
    rows = [row for row in state["volumes"] if row["Name"] == name]
    if len(rows) != 1 or rows[0].get("MountCount", 0):
        raise SystemExit(1)
    if state.get("fail_rm") == name:
        print("synthetic volume refusal", file=sys.stderr)
        raise SystemExit(1)
    state["volumes"] = [
        row for row in state["volumes"] if row["Name"] != name
    ]
    state.setdefault("removed", []).append(name)
    state_path.write_text(json.dumps(state))
    print(name)
else:
    raise SystemExit(2)
""",
            encoding="utf-8",
        )
        self.fake_podman.chmod(0o755)
        self.plan = root / "plan.json"
        self.write_plan()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_state(
        self,
        *,
        containers: list[dict[str, object]] | None = None,
        candidate_mount_count: int = 0,
        extra_volume: bool = False,
        candidate_created_at: str = "2026-07-29T00:00:00+00:00",
        candidate_options: dict[str, str] | None = None,
        fail_rm: str | None = None,
        rootless: bool = True,
        remote: bool = False,
    ) -> None:
        def row(
            name: str,
            *,
            mount_count: int = 0,
            created_at: str = "2026-07-29T00:00:00+00:00",
            options: dict[str, str] | None = None,
        ) -> dict[str, object]:
            data = self.volume_root / name / "_data"
            data.mkdir(parents=True, exist_ok=True)
            payload = data / "payload"
            if not payload.exists():
                payload.write_bytes(name.encode("ascii"))
            return {
                "Name": name,
                "MountCount": mount_count,
                "Driver": "local",
                "Scope": "local",
                "CreatedAt": created_at,
                "Options": options or {},
                "Mountpoint": str(data),
            }

        volumes: list[dict[str, object]] = [
            row(
                "rog5-candidate-a",
                mount_count=candidate_mount_count,
                created_at=candidate_created_at,
                options=candidate_options,
            ),
            row("rog5-candidate-b"),
            row("rog5-retained"),
            row("foreign-volume"),
        ]
        if extra_volume:
            volumes.append(row("new-volume"))
        self.state.write_text(
            json.dumps(
                {
                    "containers": containers or [],
                    "volumes": volumes,
                    "graph_root": str(self.graph_root),
                    "volume_root": str(self.volume_root),
                    "fail_rm": fail_rm,
                    "removed": [],
                    "rootless": rootless,
                    "remote": remote,
                }
            ),
            encoding="ascii",
        )

    def write_plan(
        self,
        *,
        candidate_references: list[str] | None = None,
        commit: str | None = None,
    ) -> None:
        state = json.loads(self.state.read_text(encoding="ascii"))
        state_by_name = {row["Name"]: row for row in state["volumes"]}

        def size(name: str, apparent: bool) -> int:
            arguments = ["du"]
            if apparent:
                arguments.append("--apparent-size")
            arguments.extend(
                [
                    "--block-size=1",
                    "--summarize",
                    str(self.volume_root / name),
                ]
            )
            return int(
                subprocess.run(
                    arguments,
                    check=True,
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout.split(maxsplit=1)[0]
            )

        entries = []
        for name, decision in (
            ("rog5-candidate-a", "prune_candidate"),
            ("rog5-candidate-b", "prune_candidate"),
            ("rog5-retained", "retain"),
            ("foreign-volume", "retain"),
        ):
            row = state_by_name[name]
            entries.append(
                {
                    "id": f"podman-volume:{name}",
                    "scope": "podman-volume",
                    "unit": name,
                    "kind": "directory",
                    "allocated_size_bytes": size(name, False),
                    "apparent_size_bytes": size(name, True),
                    "tracked_references": (
                        candidate_references
                        if decision == "prune_candidate"
                        and name == "rog5-candidate-a"
                        and candidate_references is not None
                        else []
                    ),
                    "embedded_git": [],
                    "runtime": {
                        "container_count": 0,
                        "mount_count": 0,
                        "driver": "local",
                        "scope": "local",
                        "created_at": row["CreatedAt"],
                        "options": row["Options"],
                    },
                    "decision": decision,
                    "reason": "fixture",
                }
            )
        plan = {
            "format": "rog5-host-storage-cleanup-plan-v1",
            "generated_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "repository_commit": commit or self.commit,
            "scope": ["rog5-dev", "rog5-cache", "podman-volume"],
            "policy": {
                "read_only": True,
                "deletion_supported": False,
                "prune_candidate_is_authority": False,
                "absolute_paths_published": False,
                "unrelated_host_state_in_scope": False,
            },
            "runtime": {
                "podman_container_count": 0,
                "podman_store_identity_sha256": self.store_identity(),
            },
            "summary": {},
            "entries": entries,
        }
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )

    def plan_sha256(self) -> str:
        return hashlib.sha256(self.plan.read_bytes()).hexdigest()

    def store_identity(self) -> str:
        encoded = (
            f"graph-root\0{self.graph_root.as_posix()}\0"
            f"volume-root\0{self.volume_root.as_posix()}\0"
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def candidate_set_sha256() -> str:
        return hashlib.sha256(
            b"rog5-candidate-a\nrog5-candidate-b\n"
        ).hexdigest()

    def run_cleanup(
        self,
        action: str = "preflight",
        *,
        allow: bool = False,
        check: bool = False,
        expected_count: int = 2,
        expected_set_sha256: str | None = None,
        plan_sha256: str | None = None,
        redirected: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["FAKE_PODMAN_STATE"] = str(self.state)
        for name in (
            "CONTAINER_CONNECTION",
            "CONTAINER_HOST",
            "CONTAINER_SSHKEY",
        ):
            environment.pop(name, None)
        if redirected:
            environment["CONTAINER_HOST"] = "ssh://wrong-host/run/podman.sock"
        actual_plan_sha256 = plan_sha256 or self.plan_sha256()
        if allow:
            environment["ALLOW_ROG5_PODMAN_VOLUME_DELETE"] = (
                actual_plan_sha256
            )
        else:
            environment.pop("ALLOW_ROG5_PODMAN_VOLUME_DELETE", None)
        return subprocess.run(
            [
                "python3",
                CLEANUP,
                action,
                "--plan",
                self.plan,
                "--plan-sha256",
                actual_plan_sha256,
                "--expected-candidate-count",
                str(expected_count),
                "--repo",
                self.repo,
                "--podman-command",
                self.fake_podman,
                *(
                    [
                        "--expected-candidate-set-sha256",
                        expected_set_sha256 or self.candidate_set_sha256(),
                    ]
                    if action == "delete"
                    else []
                ),
            ],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )

    def test_preflight_is_exact_and_non_destructive(self) -> None:
        before = self.state.read_bytes()
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        allocated = sum(
            entry["allocated_size_bytes"]
            for entry in plan["entries"]
            if entry["decision"] == "prune_candidate"
        )
        result = self.run_cleanup(check=True)
        self.assertIn("candidate_count=2\n", result.stdout)
        self.assertIn(
            f"candidate_allocated_size_bytes={allocated}\n", result.stdout
        )
        self.assertIn("action=preflight\nstatus=ready\n", result.stdout)
        self.assertEqual(self.state.read_bytes(), before)

    def test_delete_requires_guard_and_then_removes_only_candidates(self) -> None:
        denied = self.run_cleanup("delete")
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn(
            "ALLOW_ROG5_PODMAN_VOLUME_DELETE to equal", denied.stderr
        )
        self.assertEqual(
            [row["Name"] for row in json.loads(self.state.read_text())["volumes"]],
            [
                "rog5-candidate-a",
                "rog5-candidate-b",
                "rog5-retained",
                "foreign-volume",
            ],
        )
        allowed = self.run_cleanup("delete", allow=True, check=True)
        self.assertIn("deleted=rog5-candidate-a\n", allowed.stdout)
        self.assertIn("deleted=rog5-candidate-b\n", allowed.stdout)
        self.assertIn("action=delete\nstatus=complete\n", allowed.stdout)
        self.assertEqual(
            [row["Name"] for row in json.loads(self.state.read_text())["volumes"]],
            ["rog5-retained", "foreign-volume"],
        )
        self.assertEqual(
            json.loads(self.state.read_text())["removed"],
            ["rog5-candidate-a", "rog5-candidate-b"],
        )

    def test_hash_count_reference_and_commit_mismatches_fail_closed(self) -> None:
        result = self.run_cleanup(plan_sha256="0" * 64)
        self.assertIn("plan SHA-256 does not match", result.stderr)
        result = self.run_cleanup(expected_count=3)
        self.assertIn("candidate count does not match", result.stderr)
        self.write_plan(candidate_references=["docs/active.md:1"])
        result = self.run_cleanup()
        self.assertIn("candidate volume has tracked references", result.stderr)
        self.write_plan(commit="0" * 40)
        result = self.run_cleanup()
        self.assertIn("commit is not the current exact HEAD", result.stderr)

    def test_live_container_mount_and_volume_drift_fail_closed(self) -> None:
        self.write_state(containers=[{"Id": "running"}])
        result = self.run_cleanup()
        self.assertIn("container closure is no longer empty", result.stderr)
        self.write_state(candidate_mount_count=1)
        result = self.run_cleanup()
        self.assertIn("live candidate mount count", result.stderr)
        self.write_state(extra_volume=True)
        result = self.run_cleanup()
        self.assertIn("volume set differs from the exact plan", result.stderr)

    def test_foreign_prefix_and_driver_can_never_be_candidates(self) -> None:
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        candidate = next(
            entry
            for entry in plan["entries"]
            if entry["unit"] == "rog5-candidate-a"
        )
        candidate["unit"] = "foreign-candidate"
        candidate["id"] = "podman-volume:foreign-candidate"
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        result = self.run_cleanup()
        self.assertIn("outside the ROG5 project prefix", result.stderr)

        self.write_plan()
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        candidate = next(
            entry
            for entry in plan["entries"]
            if entry["unit"] == "rog5-candidate-a"
        )
        candidate["runtime"]["driver"] = "remote"
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        result = self.run_cleanup()
        self.assertIn("not local project storage", result.stderr)

    def test_live_identity_options_size_store_and_connection_are_bound(
        self,
    ) -> None:
        self.write_state(
            candidate_created_at="2026-07-29T00:00:01+00:00"
        )
        result = self.run_cleanup()
        self.assertIn("creation identity changed", result.stderr)

        self.write_state(candidate_options={"device": "/other/data"})
        result = self.run_cleanup()
        self.assertIn("nonempty storage options", result.stderr)

        self.write_state()
        payload = self.volume_root / "rog5-candidate-a/_data/payload"
        payload.write_bytes(b"changed-content-with-a-different-size")
        result = self.run_cleanup()
        self.assertRegex(
            result.stderr,
            r"candidate (allocated|apparent) size changed",
        )

        self.write_state()
        result = self.run_cleanup(redirected=True)
        self.assertIn("inherited Podman connection selectors", result.stderr)

        self.write_state(rootless=False)
        result = self.run_cleanup()
        self.assertIn("local rootless Podman engine", result.stderr)

    def test_candidate_set_hash_and_plan_mutation_are_independently_bound(
        self,
    ) -> None:
        result = self.run_cleanup(
            "delete",
            allow=True,
            expected_set_sha256="0" * 64,
        )
        self.assertIn("candidate-set SHA-256 does not match", result.stderr)

        recorded = self.plan_sha256()
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        plan["policy"]["read_only"] = False
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        result = self.run_cleanup(plan_sha256=recorded)
        self.assertIn("plan SHA-256 does not match", result.stderr)

    def test_partial_delete_is_explicit_and_makes_plan_stale(self) -> None:
        self.write_state(fail_rm="rog5-candidate-b")
        result = self.run_cleanup("delete", allow=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PARTIAL cleanup stopped", result.stderr)
        self.assertIn("deleted_count=1", result.stderr)
        self.assertIn("plan_is_stale=true", result.stderr)
        self.assertIn("synthetic volume refusal", result.stderr)
        self.assertEqual(
            [row["Name"] for row in json.loads(self.state.read_text())["volumes"]],
            ["rog5-candidate-b", "rog5-retained", "foreign-volume"],
        )

    def test_policy_runtime_age_permissions_and_duplicate_json_fail_closed(
        self,
    ) -> None:
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        plan["policy"]["read_only"] = False
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        result = self.run_cleanup()
        self.assertIn("plan policy mismatch: read_only", result.stderr)

        self.write_plan()
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        plan["runtime"]["podman_container_count"] = 1
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        result = self.run_cleanup()
        self.assertIn("plan Podman container count", result.stderr)

        self.write_plan()
        plan = json.loads(self.plan.read_text(encoding="ascii"))
        plan["generated_at"] = "2000-01-01T00:00:00+00:00"
        self.plan.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        result = self.run_cleanup()
        self.assertIn("older than the 15-minute", result.stderr)

        self.write_plan()
        self.plan.chmod(0o666)
        result = self.run_cleanup()
        self.assertIn("group/other-writable", result.stderr)
        self.plan.chmod(0o644)

        encoded = self.plan.read_text(encoding="ascii")
        encoded = encoded.replace(
            '"format": "rog5-host-storage-cleanup-plan-v1",',
            '"format": "rog5-host-storage-cleanup-plan-v1",\n'
            '  "format": "rog5-host-storage-cleanup-plan-v1",',
            1,
        )
        self.plan.write_text(encoded, encoding="ascii")
        result = self.run_cleanup()
        self.assertIn("duplicate JSON field: format", result.stderr)

    def test_linked_plan_is_rejected(self) -> None:
        target = self.plan.with_name("target.json")
        self.plan.replace(target)
        self.plan.symlink_to(target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        result = self.run_cleanup(plan_sha256=digest)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Too many levels of symbolic links", result.stderr)


if __name__ == "__main__":
    unittest.main()
