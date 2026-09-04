#!/usr/bin/env python3
"""Select the cheapest repository tier that covers a changed-path set."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
PROBE_ONLY = frozenset(
    {
        "scripts/device/observe-early-mainline-power.sh",
        "scripts/device/probe-network-root-battery-telemetry.sh",
        "scripts/device/test-observe-early-mainline-power.sh",
        "scripts/device/test-probe-network-root-battery-telemetry.sh",
        "scripts/host/collect-early-target-diagnostics.py",
        "scripts/host/early-target-diagnostics.py",
        "scripts/host/test-collect-early-target-diagnostics.py",
        "scripts/host/test-early-target-diagnostics.py",
        "tools/early_target_diag/rog5-early-target-diag.c",
    }
)
PROBE_QEMU = "tools/early_target_diag/rog5-early-target-diag.c"


def documentation(path: str) -> bool:
    # Markdown elsewhere can be a sealed artifact/runtime input, not prose.
    # In particular, test-results includes hash-pinned runtime-builder evidence
    # and compatibility-oracle inputs: do not exempt that whole namespace.
    return path in {"README.md", "ROADMAP.md", "AGENTS.md"} or (
        path.startswith(("docs/", ".agents/skills/")) and path.endswith(".md")
    )


def classify(paths: list[str]) -> tuple[str, str]:
    normalized = sorted({path for path in paths if path})
    if not normalized:
        return "ci", "yes"
    runtime = [path for path in normalized if not documentation(path)]
    if not runtime:
        return "active", "no"
    if all(path in PROBE_ONLY for path in runtime):
        return "probe", "yes" if PROBE_QEMU in runtime else "no"
    # Only demonstrated narrow coverage may opt out of full CI and QEMU.
    return "ci", "yes"


def git(*arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def changed_paths(base: str, head: str, *, merge_base: bool = False) -> list[str]:
    revisions = []
    for revision in (base, head):
        if not revision or not revision.strip("0"):
            raise ValueError("missing or zero revision")
        revisions.append(git("rev-parse", "--verify", "--end-of-options",
                             f"{revision}^{{commit}}").decode().strip())
    base, head = revisions
    if merge_base:
        bases = git("merge-base", "--all", base, head).decode().splitlines()
        if len(bases) != 1:
            raise ValueError("no unique merge base")
        base = bases[0]
    # Disable rename detection so a runtime -> docs rename includes BOTH paths.
    result = git("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                 "--name-only", "-z", base, head, "--")
    return [
        item.decode("utf-8", errors="surrogateescape")
        for item in result.split(b"\0")
        if item
    ]


def select(base: str, head: str, event: str) -> tuple[str, str]:
    if event in {"schedule", "workflow_dispatch"}:
        return "nightly", "yes"
    if event not in {"push", "pull_request", "merge"}:
        return "ci", "yes"
    try:
        # PR head: branch contribution, excluding unrelated base advancement.
        # Push: before -> head, including force pushes. Merge: base -> actual merge.
        return classify(changed_paths(base, head, merge_base=event == "pull_request"))
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f"selection unavailable; using full CI/QEMU: {error}", file=sys.stderr)
        return "ci", "yes"


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default="push")
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args(arguments)
    tier, qemu = select(args.base, args.head, args.event)
    print(f"tier={tier}")
    print(f"qemu={qemu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
