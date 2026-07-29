#!/usr/bin/env python3
"""Generate a read-only retention plan for ignored build and artifact state."""

from __future__ import annotations

import argparse
import csv
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


FORMAT = "rog5-artifact-prune-plan-v1"
TEMPORARY_RECOVERY = re.compile(
    r"(?:extract-test|stage-extract-test|template-inspect|template-args|"
    r"v6-template-args|v6-template-rog5)\.[A-Za-z0-9]+"
)
SENSITIVE_UNIT = re.compile(
    r"(?:^|[-_.])(?:credential|key|private|secret|token)(?:[-_.]|$)",
    re.IGNORECASE,
)


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def git(repo: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def disk_size(path: Path, *, apparent: bool) -> int:
    arguments = ["du"]
    if apparent:
        arguments.append("--apparent-size")
    arguments.extend(["--block-size=1", "--summarize", "--", str(path)])
    result = subprocess.run(
        arguments,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return int(result.stdout.split(maxsplit=1)[0])


def load_manifest(repo: Path) -> list[dict[str, str]]:
    manifest = repo / "manifests/artifacts.tsv"
    with manifest.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        expected = ["name", "size", "sha256", "role", "tracked"]
        if reader.fieldnames != expected:
            fail("artifact manifest header is not canonical")
        rows = list(reader)
    for row in rows:
        if (
            not row["name"]
            or not row["size"].isdigit()
            or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        ):
            fail(f"invalid artifact manifest row: {row['name']!r}")
    return rows


def tracked_lines(repo: Path) -> list[tuple[str, int, str]]:
    lines: list[tuple[str, int, str]] = []
    for raw_name in git(repo, "ls-files", "-z").split(b"\0"):
        if not raw_name:
            continue
        relative = raw_name.decode("utf-8")
        if (
            relative.startswith("test-results/")
            and relative.endswith("-artifact-prune-plan.json")
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


def collect_units(repo: Path) -> list[tuple[Path, bool]]:
    units: list[tuple[Path, bool]] = []
    for name in ("artifacts", "build"):
        root = repo / name
        metadata = root.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            fail(f"inventory root is not a directory: {name}")
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if SENSITIVE_UNIT.search(child.name):
                fail(
                    "refusing to publish a sensitive-looking inventory unit: "
                    f"{name}/{child.name}"
                )
            units.append((child, False))

    recovery = repo / "artifacts/recovery-stage-v12"
    if recovery.is_dir() and not recovery.is_symlink():
        for child in sorted(recovery.iterdir(), key=lambda item: item.name):
            if TEMPORARY_RECOVERY.fullmatch(child.name):
                units.append((child, True))
    return units


def manifest_for_unit(
    relative: str, rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    prefix = f"{relative}/"
    return [
        row
        for row in rows
        if row["name"] == relative or row["name"].startswith(prefix)
    ]


def manifest_status(
    repo: Path, rows: list[dict[str, str]]
) -> tuple[str, int, int]:
    if not rows:
        return "unlisted", 0, 0
    missing = 0
    size_mismatch = 0
    for row in rows:
        path = repo / row["name"]
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            missing += 1
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != int(
            row["size"]
        ):
            size_mismatch += 1
    if missing:
        return "listed-missing", missing, size_mismatch
    if size_mismatch:
        return "listed-size-mismatch", missing, size_mismatch
    return "listed-size-match-hash-unverified", 0, 0


def classify(
    relative: str,
    *,
    nested: bool,
    references: list[str],
    manifest_rows: list[dict[str, str]],
) -> tuple[str, str, dict[str, str | None]]:
    name = Path(relative).name.lower()
    if (
        nested
        and TEMPORARY_RECOVERY.fullmatch(Path(relative).name)
        and not references
        and not manifest_rows
    ):
        return (
            "prune_candidate",
            "leaked_temporary",
            {
                "command": None,
                "reason_irreplaceable": None,
                "note": "temporary extraction tree; reproduction is not required",
            },
        )
    if "failed" in name and not references and not manifest_rows:
        return (
            "prune_candidate",
            "failed_build",
            {
                "command": None,
                "reason_irreplaceable": None,
                "note": "failed intermediate with no manifest or tracked reference",
            },
        )
    if relative == "build/qemu-smoke-kernel":
        return (
            "review",
            "build_cache",
            {
                "command": (
                    "scripts/host/build-qemu-smoke-kernel.sh "
                    "build/qemu-linux-source build/qemu-smoke-kernel"
                ),
                "reason_irreplaceable": None,
                "note": "content-keyed CI cache; keep while it shortens local tests",
            },
        )
    if manifest_rows or references:
        reason = (
            "manifest-backed or used by tracked source/evidence; retain until "
            "an exact reproducer and reference closure are both proven"
        )
        return (
            "retain",
            "manifest_or_reference",
            {
                "command": None,
                "reason_irreplaceable": reason,
                "note": "no deletion authority",
            },
        )
    if relative.startswith("build/"):
        reason = (
            "incremental build state with no machine-resolved reproducer; "
            "review before sacrificing build speed"
        )
        return (
            "review",
            "build_cache",
            {
                "command": None,
                "reason_irreplaceable": reason,
                "note": "no deletion authority",
            },
        )
    reason = (
        "unclassified ignored artifact with no machine-resolved reproducer; "
        "retain until reviewed"
    )
    return (
        "review",
        "unclassified",
        {
            "command": None,
            "reason_irreplaceable": reason,
            "note": "no deletion authority",
        },
    )


def build_plan(repo: Path) -> dict[str, object]:
    commit = git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    manifest = load_manifest(repo)
    source_lines = tracked_lines(repo)
    entries: list[dict[str, object]] = []

    for path, nested in collect_units(repo):
        relative = path.relative_to(repo).as_posix()
        metadata = path.lstat()
        references = sorted(
            {
                f"{name}:{number}"
                for name, number, line in source_lines
                if relative in line
            }
        )
        rows = manifest_for_unit(relative, manifest)
        status, missing, size_mismatch = manifest_status(repo, rows)
        decision, role, reproduction = classify(
            relative,
            nested=nested,
            references=references,
            manifest_rows=rows,
        )
        canonical_rows = json.dumps(
            rows, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        entries.append(
            {
                "path": relative,
                "nested": nested,
                "kind": (
                    "directory"
                    if stat.S_ISDIR(metadata.st_mode)
                    else "symlink"
                    if stat.S_ISLNK(metadata.st_mode)
                    else "file"
                ),
                "apparent_size_bytes": disk_size(path, apparent=True),
                "allocated_size_bytes": disk_size(path, apparent=False),
                "sha256": (
                    sha256_file(path)
                    if stat.S_ISREG(metadata.st_mode)
                    else None
                ),
                "manifest": {
                    "status": status,
                    "rows": rows,
                    "rows_sha256": (
                        hashlib.sha256(canonical_rows).hexdigest()
                        if rows
                        else None
                    ),
                    "missing": missing,
                    "size_mismatch": size_mismatch,
                },
                "tracked_references": references,
                "role": role,
                "decision": decision,
                "reproduction": reproduction,
            }
        )

    top_level = [entry for entry in entries if not entry["nested"]]
    decisions = {
        decision: sum(entry["decision"] == decision for entry in entries)
        for decision in ("retain", "review", "prune_candidate")
    }
    return {
        "format": FORMAT,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "repository_commit": commit,
        "scope": ["artifacts", "build"],
        "policy": {
            "read_only": True,
            "deletion_supported": False,
            "prune_candidate_is_authority": False,
            "generated_plans_are_references": False,
            "directory_sha256": (
                "not computed; manifest row identities are recorded and "
                "unresolved directories cannot be pruned"
            ),
        },
        "summary": {
            "top_level_units": len(top_level),
            "nested_units": len(entries) - len(top_level),
            "top_level_apparent_size_bytes": sum(
                int(entry["apparent_size_bytes"]) for entry in top_level
            ),
            "top_level_allocated_size_bytes": sum(
                int(entry["allocated_size_bytes"]) for entry in top_level
            ),
            "decisions": decisions,
        },
        "entries": entries,
    }


def write_plan(plan: dict[str, object], output: Path | None) -> None:
    encoded = (
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("ascii")
    if output is None:
        sys.stdout.buffer.write(encoded)
        return
    output = output.resolve(strict=False)
    parent = output.parent
    if not parent.is_dir() or parent.is_symlink():
        fail("output parent is absent or linked")
    if output.exists() or output.is_symlink():
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


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--output", type=Path)
    options = parser.parse_args(arguments)
    repo = options.repo.resolve(strict=True)
    if not (repo / ".git").exists():
        fail("repository is not a Git worktree")
    write_plan(build_plan(repo), options.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
