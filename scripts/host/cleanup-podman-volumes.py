#!/usr/bin/env python3
"""Preflight or execute an exact, plan-bound ROG5 Podman volume cleanup."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, NoReturn


PLAN_FORMAT = "rog5-host-storage-cleanup-plan-v1"
MAX_PLAN_SIZE = 4 * 1024 * 1024
MAX_PLAN_AGE = timedelta(minutes=15)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
SHA256 = re.compile(r"[0-9a-f]{64}")
REMOTE_ENVIRONMENT = (
    "CONTAINER_CONNECTION",
    "CONTAINER_HOST",
    "CONTAINER_SSHKEY",
)


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def run(*arguments: str) -> bytes:
    return subprocess.run(
        list(arguments),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def git(repo: Path, *arguments: str) -> bytes:
    return run("git", "-C", str(repo), *arguments)


def podman_store_identity(graph_root: Path, volume_root: Path) -> str:
    encoded = (
        f"graph-root\0{graph_root.as_posix()}\0"
        f"volume-root\0{volume_root.as_posix()}\0"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def load_plan(path: Path, expected_sha256: str) -> dict[str, Any]:
    absolute = Path(os.path.abspath(path.expanduser()))
    descriptor = os.open(
        absolute,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
            or metadata.st_size <= 0
            or metadata.st_size > MAX_PLAN_SIZE
        ):
            fail(
                "plan must be an owned, bounded ordinary file that is not "
                "group/other-writable"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            encoded = stream.read(MAX_PLAN_SIZE + 1)
    finally:
        os.close(descriptor)
    if len(encoded) != metadata.st_size:
        fail("plan size changed while it was read")
    actual_sha256 = hashlib.sha256(encoded).hexdigest()
    if actual_sha256 != expected_sha256:
        fail("plan SHA-256 does not match the explicit expected identity")
    plan = json.loads(encoded, object_pairs_hook=unique_object)
    if not isinstance(plan, dict):
        fail("plan root is not a JSON object")
    return plan


def require_bool(value: Any, expected: bool, label: str) -> None:
    if value is not expected:
        fail(f"plan policy mismatch: {label}")


def require_zero_count(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value != 0:
        fail(f"{label} is not the integer zero")


def validate_plan(
    plan: dict[str, Any],
    *,
    repo: Path,
    expected_candidates: int,
) -> tuple[
    list[str],
    list[str],
    int,
    str,
    dict[str, dict[str, Any]],
    str,
]:
    if plan.get("format") != PLAN_FORMAT:
        fail("unsupported host-storage plan format")
    if plan.get("scope") != ["rog5-dev", "rog5-cache", "podman-volume"]:
        fail("plan scope is not canonical")
    policy = plan.get("policy")
    if not isinstance(policy, dict):
        fail("plan policy is absent")
    require_bool(policy.get("read_only"), True, "read_only")
    require_bool(policy.get("deletion_supported"), False, "deletion_supported")
    require_bool(
        policy.get("prune_candidate_is_authority"),
        False,
        "prune_candidate_is_authority",
    )
    require_bool(
        policy.get("absolute_paths_published"),
        False,
        "absolute_paths_published",
    )
    require_bool(
        policy.get("unrelated_host_state_in_scope"),
        False,
        "unrelated_host_state_in_scope",
    )
    runtime = plan.get("runtime")
    if not isinstance(runtime, dict):
        fail("plan runtime is absent")
    require_zero_count(
        runtime.get("podman_container_count"),
        "plan Podman container count",
    )
    store_identity = runtime.get("podman_store_identity_sha256")
    if not isinstance(store_identity, str) or not SHA256.fullmatch(store_identity):
        fail("plan Podman store identity is invalid")

    generated_raw = plan.get("generated_at")
    if not isinstance(generated_raw, str):
        fail("plan generation time is absent")
    try:
        generated_at = datetime.fromisoformat(generated_raw)
    except ValueError:
        fail("plan generation time is invalid")
    if generated_at.tzinfo is None:
        fail("plan generation time has no timezone")
    now = datetime.now(timezone.utc)
    generated_at = generated_at.astimezone(timezone.utc)
    if generated_at > now + timedelta(minutes=1):
        fail("plan generation time is in the future")
    if now - generated_at > MAX_PLAN_AGE:
        fail("plan is older than the 15-minute execution window")

    commit = plan.get("repository_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        fail("plan repository commit is invalid")
    current_commit = git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    if current_commit != commit:
        fail("plan repository commit is not the current exact HEAD")
    if git(repo, "status", "--porcelain"):
        fail("repository must be clean before volume cleanup")

    raw_entries = plan.get("entries")
    if not isinstance(raw_entries, list):
        fail("plan entries are absent")
    candidates: list[str] = []
    candidate_details: dict[str, dict[str, Any]] = {}
    retained: list[str] = []
    allocated = 0
    seen: set[str] = set()
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            fail("plan entry is not an object")
        if raw_entry.get("scope") != "podman-volume":
            continue
        name = raw_entry.get("unit")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            fail("plan contains an invalid Podman volume name")
        if name in seen or raw_entry.get("id") != f"podman-volume:{name}":
            fail("plan contains a duplicate or noncanonical Podman volume")
        seen.add(name)
        decision = raw_entry.get("decision")
        if decision not in {"retain", "review", "prune_candidate"}:
            fail(f"plan contains an invalid decision for volume: {name}")
        entry_runtime = raw_entry.get("runtime")
        if not isinstance(entry_runtime, dict):
            fail(f"volume runtime is absent: {name}")
        require_zero_count(
            entry_runtime.get("container_count"),
            f"volume container count for {name}",
        )
        if decision == "prune_candidate":
            if not name.startswith("rog5-"):
                fail(f"candidate is outside the ROG5 project prefix: {name}")
            require_zero_count(
                entry_runtime.get("mount_count"),
                f"candidate mount count for {name}",
            )
            if (
                entry_runtime.get("driver") != "local"
                or entry_runtime.get("scope") != "local"
            ):
                fail(f"candidate volume is not local project storage: {name}")
            created_at = entry_runtime.get("created_at")
            if not isinstance(created_at, str) or not created_at:
                fail(f"candidate volume creation time is invalid: {name}")
            try:
                created_time = datetime.fromisoformat(created_at)
            except ValueError:
                fail(f"candidate volume creation time is invalid: {name}")
            if created_time.tzinfo is None:
                fail(f"candidate volume creation time has no timezone: {name}")
            if created_time.astimezone(timezone.utc) > generated_at:
                fail(f"candidate volume was created after the plan began: {name}")
            if entry_runtime.get("options") != {}:
                fail(f"candidate volume has nonempty storage options: {name}")
            if raw_entry.get("tracked_references") != []:
                fail(f"candidate volume has tracked references: {name}")
            if raw_entry.get("embedded_git") != []:
                fail(f"candidate volume has unexpected Git state: {name}")
            size = raw_entry.get("allocated_size_bytes")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                fail(f"candidate volume has an invalid size: {name}")
            allocated += size
            candidates.append(name)
            apparent = raw_entry.get("apparent_size_bytes")
            if (
                not isinstance(apparent, int)
                or isinstance(apparent, bool)
                or apparent < 0
            ):
                fail(f"candidate volume has an invalid apparent size: {name}")
            candidate_details[name] = {
                "allocated_size_bytes": size,
                "apparent_size_bytes": apparent,
                "created_at": created_at,
            }
        else:
            retained.append(name)
    candidates.sort()
    retained.sort()
    if len(candidates) != expected_candidates:
        fail("candidate count does not match the explicit expected count")
    if not candidates:
        fail("plan has no Podman prune candidates")
    return (
        candidates,
        retained,
        allocated,
        commit,
        candidate_details,
        store_identity,
    )


def podman_json(command: str, *arguments: str) -> Any:
    return json.loads(run(command, *arguments).decode("utf-8"))


def volume_rows(command: str, arguments: tuple[str, ...]) -> list[dict[str, Any]]:
    rows = podman_json(command, *arguments)
    if not isinstance(rows, list):
        fail("Podman returned a non-list volume inventory")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            fail("Podman returned a non-object volume entry")
        normalized.append(row)
    return normalized


def ensure_empty_containers(command: str) -> None:
    containers = podman_json(command, "ps", "-a", "--format", "json")
    if not isinstance(containers, list) or containers:
        fail("Podman container closure is no longer empty")


def exact_store_root(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        fail(f"Podman {label} path is unavailable")
    absolute = Path(os.path.abspath(value))
    resolved = absolute.resolve(strict=True)
    if absolute != resolved or not resolved.is_dir() or resolved.is_symlink():
        fail(f"Podman {label} path is linked or not an ordinary directory")
    return resolved


def disk_sizes(
    command: str,
    paths: list[Path],
    *,
    apparent: bool,
) -> dict[Path, int]:
    arguments = [command, "unshare", "du"]
    if apparent:
        arguments.append("--apparent-size")
    arguments.extend(["--block-size=1", "--summarize", "--"])
    arguments.extend(str(path) for path in paths)
    output = run(*arguments).decode("utf-8")
    result: dict[Path, int] = {}
    by_name: dict[str, int] = {}
    for line in output.splitlines():
        raw_size, raw_path = line.split("\t", 1)
        by_name[raw_path] = int(raw_size)
    for path in paths:
        if str(path) not in by_name:
            fail(f"Podman du omitted candidate: {path.name}")
        result[path] = by_name[str(path)]
    return result


def validate_live_candidate(
    row: dict[str, Any],
    *,
    name: str,
    volume_root: Path,
    details: dict[str, Any],
    phase: str,
) -> Path:
    require_zero_count(
        row.get("MountCount"),
        f"{phase} candidate mount count for {name}",
    )
    if row.get("Driver") != "local" or row.get("Scope") != "local":
        fail(f"{phase} candidate is not local storage: {name}")
    if row.get("Options") != {}:
        fail(f"{phase} candidate has nonempty storage options: {name}")
    if row.get("CreatedAt") != details["created_at"]:
        fail(f"{phase} candidate creation identity changed: {name}")
    path = volume_root / name
    expected_mountpoint = path / "_data"
    mountpoint = row.get("Mountpoint")
    if (
        not isinstance(mountpoint, str)
        or Path(os.path.abspath(mountpoint)) != expected_mountpoint
        or not path.is_dir()
        or path.is_symlink()
        or not expected_mountpoint.is_dir()
        or expected_mountpoint.is_symlink()
    ):
        fail(f"{phase} candidate mountpoint escaped the local volume root: {name}")
    return path


def live_preflight(
    command: str,
    *,
    candidates: list[str],
    retained: list[str],
    candidate_details: dict[str, dict[str, Any]],
    expected_store_identity: str,
) -> Path:
    redirected = [name for name in REMOTE_ENVIRONMENT if os.environ.get(name)]
    if redirected:
        fail(
            "refusing inherited Podman connection selectors: "
            + ",".join(redirected)
        )
    info = podman_json(command, "info", "--format", "json")
    try:
        rootless = info["host"]["security"]["rootless"]
        service_is_remote = info["host"]["serviceIsRemote"]
        graph_root_raw = info["store"]["graphRoot"]
        volume_root_raw = info["store"]["volumePath"]
    except (KeyError, TypeError):
        fail("Podman local-store identity is unavailable")
    if rootless is not True or service_is_remote is not False:
        fail("cleanup requires a local rootless Podman engine")
    graph_root = exact_store_root(graph_root_raw, "graph root")
    volume_root = exact_store_root(volume_root_raw, "volume root")
    if podman_store_identity(graph_root, volume_root) != expected_store_identity:
        fail("live Podman store identity differs from the plan")
    ensure_empty_containers(command)

    rows = volume_rows(command, ("volume", "ls", "--format", "json"))
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row.get("Name")
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in by_name:
            fail("live Podman volume inventory is invalid or duplicated")
        by_name[name] = row
    expected = set(candidates) | set(retained)
    if set(by_name) != expected:
        fail("live Podman volume set differs from the exact plan")
    paths: list[Path] = []
    for name in candidates:
        paths.append(
            validate_live_candidate(
                by_name[name],
                name=name,
                volume_root=volume_root,
                details=candidate_details[name],
                phase="live",
            )
        )

    inspected = volume_rows(
        command, ("volume", "inspect", "--format", "json", *candidates)
    )
    inspected_by_name: dict[str, dict[str, Any]] = {}
    for row in inspected:
        name = row.get("Name")
        if (
            not isinstance(name, str)
            or name not in candidates
            or name in inspected_by_name
        ):
            fail("Podman inspect returned an unexpected candidate")
        inspected_by_name[name] = row
    if set(inspected_by_name) != set(candidates):
        fail("Podman inspect omitted a candidate")
    for name in candidates:
        validate_live_candidate(
            inspected_by_name[name],
            name=name,
            volume_root=volume_root,
            details=candidate_details[name],
            phase="inspected",
        )
    allocated = disk_sizes(command, paths, apparent=False)
    apparent = disk_sizes(command, paths, apparent=True)
    for name, path in zip(candidates, paths, strict=True):
        details = candidate_details[name]
        if allocated[path] != details["allocated_size_bytes"]:
            fail(f"candidate allocated size changed: {name}")
        if apparent[path] != details["apparent_size_bytes"]:
            fail(f"candidate apparent size changed: {name}")
    ensure_empty_containers(command)
    return volume_root


def candidate_set_sha256(candidates: list[str]) -> str:
    encoded = "".join(f"{name}\n" for name in candidates).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def delete_candidates(
    command: str,
    *,
    candidates: list[str],
    retained: list[str],
    candidate_details: dict[str, dict[str, Any]],
    volume_root: Path,
    plan_sha256: str,
) -> None:
    if os.environ.get("ALLOW_ROG5_PODMAN_VOLUME_DELETE") != plan_sha256:
        fail(
            "delete action requires ALLOW_ROG5_PODMAN_VOLUME_DELETE "
            "to equal the exact plan SHA-256"
        )
    ensure_empty_containers(command)
    deleted: list[str] = []

    def report_stop(error: Exception, name: str) -> None:
        stale = bool(deleted)
        label = "PARTIAL" if stale else "STOPPED"
        print(
            f"{label} cleanup stopped at={name}; "
            f"deleted_count={len(deleted)} "
            f"remaining_count={len(candidates) - len(deleted)} "
            f"plan_is_stale={'true' if stale else 'false'}",
            file=sys.stderr,
        )
        if isinstance(error, subprocess.CalledProcessError):
            diagnostic = (error.stderr or b"").decode(
                "utf-8", errors="replace"
            ).strip()
            if diagnostic:
                print(f"podman_error={diagnostic}", file=sys.stderr)

    for name in candidates:
        try:
            ensure_empty_containers(command)
            inspected = volume_rows(
                command, ("volume", "inspect", "--format", "json", name)
            )
            if len(inspected) != 1 or inspected[0].get("Name") != name:
                fail(f"candidate changed before deletion: {name}")
            validate_live_candidate(
                inspected[0],
                name=name,
                volume_root=volume_root,
                details=candidate_details[name],
                phase="pre-delete",
            )
            run(command, "volume", "rm", "--", name)
        except Exception as error:
            report_stop(error, name)
            raise
        deleted.append(name)
        print(f"deleted={name}")
    try:
        ensure_empty_containers(command)
        remaining = volume_rows(command, ("volume", "ls", "--format", "json"))
        remaining_names = sorted(str(row.get("Name", "")) for row in remaining)
        if remaining_names != retained:
            fail("post-delete volume closure does not equal the retained set")
    except Exception as error:
        report_stop(error, "post-delete-closure")
        raise


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "delete"))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--expected-candidate-set-sha256")
    parser.add_argument("--expected-candidate-count", type=int, required=True)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--podman-command", default="podman")
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    if not SHA256.fullmatch(options.plan_sha256):
        fail("--plan-sha256 must be exactly 64 lowercase hexadecimal digits")
    if options.expected_candidate_count <= 0:
        fail("--expected-candidate-count must be positive")
    if options.expected_candidate_set_sha256 is not None and not SHA256.fullmatch(
        options.expected_candidate_set_sha256
    ):
        fail(
            "--expected-candidate-set-sha256 must be exactly 64 lowercase "
            "hexadecimal digits"
        )
    if options.action == "delete" and options.expected_candidate_set_sha256 is None:
        fail("delete action requires --expected-candidate-set-sha256")
    repo = options.repo.resolve(strict=True)
    if not (repo / ".git").exists():
        fail("repository is not a Git worktree")
    plan = load_plan(options.plan, options.plan_sha256)
    (
        candidates,
        retained,
        allocated,
        commit,
        candidate_details,
        store_identity,
    ) = validate_plan(
        plan,
        repo=repo,
        expected_candidates=options.expected_candidate_count,
    )
    volume_root = live_preflight(
        options.podman_command,
        candidates=candidates,
        retained=retained,
        candidate_details=candidate_details,
        expected_store_identity=store_identity,
    )
    set_sha256 = candidate_set_sha256(candidates)
    if (
        options.expected_candidate_set_sha256 is not None
        and options.expected_candidate_set_sha256 != set_sha256
    ):
        fail("candidate-set SHA-256 does not match explicit approval identity")
    print(f"plan_sha256={options.plan_sha256}")
    print(f"repository_commit={commit}")
    print(f"candidate_count={len(candidates)}")
    print(f"candidate_set_sha256={set_sha256}")
    print(f"candidate_allocated_size_bytes={allocated}")
    if options.action == "preflight":
        print("action=preflight")
        print("status=ready")
        return 0
    delete_candidates(
        options.podman_command,
        candidates=candidates,
        retained=retained,
        candidate_details=candidate_details,
        volume_root=volume_root,
        plan_sha256=options.plan_sha256,
    )
    print("action=delete")
    print("status=complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
