#!/usr/bin/env python3
"""Select the cheapest repository tier that covers a changed-path set."""

from __future__ import annotations

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
QEMU_RELEVANT_PREFIXES = (
    "configs/kernel",
    "dts/",
    "initramfs/",
    "patches/",
    "scripts/device/build-network-root-initramfs.sh",
    "scripts/device/verify-network-root-initramfs.sh",
    "scripts/host/build-qemu",
    "scripts/host/test-qemu",
    "tools/early_target_diag/",
    "tools/qemu",
)


def classify(paths: list[str]) -> tuple[str, str]:
    normalized = sorted({path for path in paths if path})
    if not normalized:
        return "ci", "yes"
    if all(path.startswith("docs/") or path.endswith(".md") for path in normalized):
        return "active", "no"
    tier = "probe" if all(path in PROBE_ONLY for path in normalized) else "ci"
    qemu = (
        "yes"
        if any(
            path.startswith(prefix)
            for path in normalized
            for prefix in QEMU_RELEVANT_PREFIXES
        )
        else "no"
    )
    return tier, qemu


def changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(REPO), "diff", "--name-only", "-z", base, head],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        raise SystemExit("usage: select-repository-test-tier.py BASE HEAD")
    tier, qemu = classify(changed_paths(arguments[0], arguments[1]))
    print(f"tier={tier}")
    print(f"qemu={qemu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
