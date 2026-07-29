#!/usr/bin/env python3
"""Inventory ROG5 host state and emit a conservative, read-only cleanup plan."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import NoReturn


FORMAT = "rog5-host-storage-cleanup-plan-v1"
SENSITIVE_UNIT = re.compile(
    r"(?:^|[-_.])(?:auth|credentials?|id[-_.]?(?:ed25519|rsa)|keys?|"
    r"password|passwd|private|secrets?|tokens?)(?:[-_.]|$)",
    re.IGNORECASE,
)
GENERATED_DEV_UNIT = re.compile(
    r"(?:^|[-_.])(?:build|package|prepare|repack|smoke|source|stage|"
    r"sysroot|template|wrapper|work)(?:[-_.]|$)",
    re.IGNORECASE,
)
EVIDENCE_DEV_UNIT = re.compile(
    r"(?:^|[-_.])(?:audit|debug|log|metric|trace)(?:[-_.]|$)",
    re.IGNORECASE,
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


def resolve_inventory_root(path: Path, label: str) -> Path:
    absolute = Path(os.path.abspath(path.expanduser()))
    cursor = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        cursor /= component
        if stat.S_ISLNK(cursor.lstat().st_mode):
            fail(f"{label} inventory path contains a symlink")
    resolved = absolute.resolve(strict=True)
    metadata = resolved.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or resolved.is_symlink():
        fail(f"{label} inventory root is not an ordinary directory")
    return resolved


def tracked_lines(repo: Path) -> list[tuple[str, int, str]]:
    lines: list[tuple[str, int, str]] = []
    for raw_name in git(repo, "ls-files", "-z").split(b"\0"):
        if not raw_name:
            continue
        relative = raw_name.decode("utf-8")
        if (
            relative.startswith("test-results/")
            and relative.endswith("-host-storage-cleanup-plan.json")
        ):
            continue
        path = repo / relative
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        for number, line in enumerate(
            data.decode("utf-8", errors="replace").splitlines(), 1
        ):
            lines.append((relative, number, line))
    return lines


def references_for(
    unit: str, source_lines: list[tuple[str, int, str]]
) -> list[str]:
    return sorted(
        {
            f"{name}:{number}"
            for name, number, line in source_lines
            if unit in line
        }
    )


def collect_units(root: Path) -> list[Path]:
    units = sorted(root.iterdir(), key=lambda path: path.name)
    for unit in units:
        if SENSITIVE_UNIT.search(unit.name):
            fail(
                "refusing to publish a sensitive-looking inventory unit: "
                f"{unit.name}"
            )
    return units


def disk_sizes(
    paths: list[Path],
    *,
    apparent: bool,
    command_prefix: tuple[str, ...] = (),
) -> dict[Path, int]:
    if not paths:
        return {}
    arguments = [*command_prefix, "du"]
    if apparent:
        arguments.append("--apparent-size")
    arguments.extend(["--block-size=1", "--summarize", "--"])
    arguments.extend(str(path) for path in paths)
    output = run(*arguments).decode("utf-8", errors="strict")
    by_name: dict[str, int] = {}
    for line in output.splitlines():
        raw_size, raw_path = line.split("\t", 1)
        by_name[raw_path] = int(raw_size)
    result: dict[Path, int] = {}
    for path in paths:
        try:
            result[path] = by_name[str(path)]
        except KeyError:
            fail(f"du omitted inventory unit: {path.name}")
    return result


def path_kind(path: Path) -> str:
    mode = path.lstat().st_mode
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def embedded_worktrees(unit: Path) -> list[dict[str, object]]:
    if not unit.is_dir() or unit.is_symlink():
        return []
    output = run(
        "find",
        str(unit),
        "-xdev",
        "-name",
        ".git",
        "-print0",
        "-prune",
    )
    results: list[dict[str, object]] = []
    for raw_marker in output.split(b"\0"):
        if not raw_marker:
            continue
        marker = Path(raw_marker.decode("utf-8"))
        worktree = marker.parent
        relative = worktree.relative_to(unit).as_posix()
        if marker.is_symlink() or not marker.is_dir():
            results.append(
                {
                    "worktree": relative if relative != "." else ".",
                    "head": None,
                    "dirty": None,
                    "dirty_paths": [],
                    "head_diff_sha256": None,
                    "audit_error": (
                        ".git marker is not an ordinary in-unit directory"
                    ),
                }
            )
            continue
        head = git(worktree, "rev-parse", "HEAD").decode("ascii").strip()
        status = git(
            worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all"
        )
        dirty_paths = sorted(
            {
                record[3:].decode("utf-8", errors="replace")
                for record in status.split(b"\0")
                if len(record) >= 4
            }
        )
        diff = git(worktree, "diff", "--binary", "HEAD", "--")
        results.append(
            {
                "worktree": relative if relative != "." else ".",
                "head": head,
                "dirty": bool(status),
                "dirty_paths": dirty_paths,
                "head_diff_sha256": (
                    hashlib.sha256(diff).hexdigest() if status else None
                ),
                "audit_error": None,
            }
        )
    return sorted(results, key=lambda item: str(item["worktree"]))


def make_entry(
    *,
    identifier: str,
    scope: str,
    unit: Path,
    allocated: int,
    apparent: int,
    references: list[str],
    worktrees: list[dict[str, object]],
    decision: str,
    reason: str,
    runtime: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": identifier,
        "scope": scope,
        "unit": unit.name,
        "kind": path_kind(unit),
        "allocated_size_bytes": allocated,
        "apparent_size_bytes": apparent,
        "tracked_references": references,
        "embedded_git": worktrees,
        "runtime": runtime,
        "decision": decision,
        "reason": reason,
    }


def data_entries(
    *,
    root: Path,
    scope: str,
    prefix: str,
    source_lines: list[tuple[str, int, str]],
    cache: bool,
) -> list[dict[str, object]]:
    units = collect_units(root)
    allocated = disk_sizes(units, apparent=False)
    apparent = disk_sizes(units, apparent=True)
    entries: list[dict[str, object]] = []
    for unit in units:
        references = references_for(unit.name, source_lines)
        worktrees = embedded_worktrees(unit)
        audit_error = any(tree.get("audit_error") for tree in worktrees)
        dirty = any(bool(tree["dirty"]) for tree in worktrees)
        kind = path_kind(unit)
        if references:
            decision = "retain"
            reason = "unit is named by tracked project source or evidence"
        elif audit_error:
            decision = "retain"
            reason = "embedded Git metadata could not be safely audited"
        elif dirty:
            decision = "retain"
            reason = "embedded Git worktree has uncommitted state"
        elif kind in {"symlink", "other"}:
            decision = "retain"
            reason = "non-ordinary unit requires manual resolution"
        elif cache:
            decision = "prune_candidate"
            reason = "unreferenced project cache unit"
        elif kind == "file" or EVIDENCE_DEV_UNIT.search(unit.name):
            decision = "review"
            reason = "unreferenced unit may contain compact diagnostic evidence"
        elif GENERATED_DEV_UNIT.search(unit.name):
            decision = "prune_candidate"
            reason = "unreferenced generated unit with no dirty Git worktree"
        else:
            decision = "review"
            reason = "unreferenced external unit is not proven generated"
        entries.append(
            make_entry(
                identifier=f"{prefix}:{unit.name}",
                scope=scope,
                unit=unit,
                allocated=allocated[unit],
                apparent=apparent[unit],
                references=references,
                worktrees=worktrees,
                decision=decision,
                reason=reason,
            )
        )
    return entries


def load_podman_state(
    options: argparse.Namespace,
) -> tuple[list[dict[str, object]], int, Path, tuple[str, ...]]:
    if options.podman_volumes_json is not None:
        volumes = json.loads(
            options.podman_volumes_json.read_text(encoding="utf-8")
        )
        if options.podman_container_count is None:
            fail("--podman-container-count is required with fixture state")
        if options.podman_volume_root is None:
            fail("--podman-volume-root is required with fixture state")
        container_count = options.podman_container_count
        volume_root = options.podman_volume_root
        size_command_prefix: tuple[str, ...] = ()
    else:
        command = options.podman_command
        volumes = json.loads(
            run(command, "volume", "ls", "--format", "json").decode("utf-8")
        )
        containers = json.loads(
            run(command, "ps", "-a", "--format", "json").decode("utf-8")
        )
        info = json.loads(
            run(command, "info", "--format", "json").decode("utf-8")
        )
        container_count = len(containers)
        volume_root = Path(str(info["store"]["volumePath"]))
        size_command_prefix = (command, "unshare")
    if not isinstance(volumes, list):
        fail("Podman volume inventory is not a JSON list")
    if container_count < 0:
        fail("Podman container count cannot be negative")
    return (
        volumes,
        container_count,
        resolve_inventory_root(Path(volume_root), "Podman volume"),
        size_command_prefix,
    )


def podman_entries(
    *,
    volumes: list[dict[str, object]],
    container_count: int,
    volume_root: Path,
    source_lines: list[tuple[str, int, str]],
    size_command_prefix: tuple[str, ...],
) -> list[dict[str, object]]:
    paths: list[Path] = []
    normalized: list[tuple[dict[str, object], str, Path, list[str], int]] = []
    for volume in volumes:
        name = str(volume.get("Name", ""))
        if not name or "/" in name or name in {".", ".."}:
            fail(f"invalid Podman volume name: {name!r}")
        if SENSITIVE_UNIT.search(name):
            fail(
                "refusing to publish a sensitive-looking Podman volume: "
                f"{name}"
            )
        path = volume_root / name
        if not path.is_dir() or path.is_symlink():
            fail(f"Podman volume unit is absent or linked: {name}")
        expected_mountpoint = path / "_data"
        if (
            not expected_mountpoint.is_dir()
            or expected_mountpoint.is_symlink()
        ):
            fail(f"Podman data directory is absent or linked: {name}")
        mountpoint = Path(str(volume.get("Mountpoint", ""))).resolve(
            strict=False
        )
        if mountpoint != expected_mountpoint:
            fail(f"Podman mountpoint does not match volume root: {name}")
        mount_count = int(volume.get("MountCount", 0))
        references = references_for(name, source_lines)
        normalized.append((volume, name, path, references, mount_count))
        paths.append(path)
    allocated = disk_sizes(
        paths, apparent=False, command_prefix=size_command_prefix
    )
    apparent = disk_sizes(
        paths, apparent=True, command_prefix=size_command_prefix
    )
    entries: list[dict[str, object]] = []
    for _volume, name, path, references, mount_count in normalized:
        if container_count:
            decision = "retain"
            reason = "Podman has containers; attachment closure is not empty"
        elif mount_count:
            decision = "retain"
            reason = "volume reports a nonzero mount count"
        elif references:
            decision = "retain"
            reason = "volume is named by tracked project source or evidence"
        else:
            decision = "prune_candidate"
            reason = "detached volume has no tracked project reference"
        entries.append(
            make_entry(
                identifier=f"podman-volume:{name}",
                scope="podman-volume",
                unit=path,
                allocated=allocated[path],
                apparent=apparent[path],
                references=references,
                worktrees=[],
                decision=decision,
                reason=reason,
                runtime={
                    "container_count": container_count,
                    "mount_count": mount_count,
                },
            )
        )
    return entries


def summarize(entries: list[dict[str, object]]) -> dict[str, object]:
    decisions = ("retain", "review", "prune_candidate")
    scopes = sorted({str(entry["scope"]) for entry in entries})
    return {
        "units": len(entries),
        "allocated_size_bytes": sum(
            int(entry["allocated_size_bytes"]) for entry in entries
        ),
        "apparent_size_bytes": sum(
            int(entry["apparent_size_bytes"]) for entry in entries
        ),
        "decisions": {
            decision: {
                "units": sum(
                    entry["decision"] == decision for entry in entries
                ),
                "allocated_size_bytes": sum(
                    int(entry["allocated_size_bytes"])
                    for entry in entries
                    if entry["decision"] == decision
                ),
            }
            for decision in decisions
        },
        "scopes": {
            scope: {
                "units": sum(entry["scope"] == scope for entry in entries),
                "allocated_size_bytes": sum(
                    int(entry["allocated_size_bytes"])
                    for entry in entries
                    if entry["scope"] == scope
                ),
                "decisions": {
                    decision: {
                        "units": sum(
                            entry["scope"] == scope
                            and entry["decision"] == decision
                            for entry in entries
                        ),
                        "allocated_size_bytes": sum(
                            int(entry["allocated_size_bytes"])
                            for entry in entries
                            if entry["scope"] == scope
                            and entry["decision"] == decision
                        ),
                    }
                    for decision in decisions
                },
            }
            for scope in scopes
        },
    }


def build_plan(options: argparse.Namespace) -> dict[str, object]:
    repo = options.repo.resolve(strict=True)
    if not (repo / ".git").exists():
        fail("repository is not a Git worktree")
    data_root = resolve_inventory_root(options.rog5_data_root, "ROG5 data")
    dev_root = resolve_inventory_root(data_root / "dev", "ROG5 dev")
    cache_root = resolve_inventory_root(options.rog5_cache_root, "ROG5 cache")
    source_lines = tracked_lines(repo)
    (
        volumes,
        container_count,
        volume_root,
        size_command_prefix,
    ) = load_podman_state(options)

    entries = data_entries(
        root=dev_root,
        scope="rog5-dev",
        prefix="rog5-dev",
        source_lines=source_lines,
        cache=False,
    )
    entries.extend(
        data_entries(
            root=cache_root,
            scope="rog5-cache",
            prefix="rog5-cache",
            source_lines=source_lines,
            cache=True,
        )
    )
    entries.extend(
        podman_entries(
            volumes=volumes,
            container_count=container_count,
            volume_root=volume_root,
            source_lines=source_lines,
            size_command_prefix=size_command_prefix,
        )
    )
    entries.sort(key=lambda entry: str(entry["id"]))
    return {
        "format": FORMAT,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "repository_commit": git(repo, "rev-parse", "HEAD")
        .decode("ascii")
        .strip(),
        "scope": ["rog5-dev", "rog5-cache", "podman-volume"],
        "policy": {
            "read_only": True,
            "deletion_supported": False,
            "prune_candidate_is_authority": False,
            "absolute_paths_published": False,
            "unrelated_host_state_in_scope": False,
            "dirty_git_worktree_retained": True,
            "nonzero_container_closure_retains_all_volumes": True,
        },
        "runtime": {
            "podman_container_count": container_count,
        },
        "summary": summarize(entries),
        "entries": entries,
    }


def write_plan(plan: dict[str, object], output: Path | None) -> None:
    encoded = (
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("ascii")
    if output is None:
        sys.stdout.buffer.write(encoded)
        return
    requested = Path(os.path.abspath(output.expanduser()))
    parent = resolve_inventory_root(requested.parent, "output parent")
    output = parent / requested.name
    if os.path.lexists(output):
        fail("refusing to replace an existing plan")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def default_data_root() -> Path:
    root = os.environ.get("XDG_DATA_HOME")
    return (
        Path(root) / "rog5-linux"
        if root
        else Path.home() / ".local/share/rog5-linux"
    )


def default_cache_root() -> Path:
    root = os.environ.get("XDG_CACHE_HOME")
    return (
        Path(root) / "rog5-linux"
        if root
        else Path.home() / ".cache/rog5-linux"
    )


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument(
        "--rog5-data-root", type=Path, default=default_data_root()
    )
    parser.add_argument(
        "--rog5-cache-root", type=Path, default=default_cache_root()
    )
    parser.add_argument("--podman-command", default="podman")
    parser.add_argument("--podman-volumes-json", type=Path)
    parser.add_argument("--podman-container-count", type=int)
    parser.add_argument("--podman-volume-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    write_plan(build_plan(options), options.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
