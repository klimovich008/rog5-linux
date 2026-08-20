#!/usr/bin/env python3
"""Capture or verify the exact installed power/USB byte composition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import NoReturn

import generated_power_usb_active as POWER_USB


REPO = Path(__file__).resolve().parents[2]
MOUNT_TARGET = Path("/var/lib/rog5-recovery-bundles")
POLICY = REPO / "manifests/temporary-boot-images.tsv"
LOCK = REPO / "manifests/power-usb-active.lock.json"
COMPONENTS = (
    REPO / "scripts/host/stable-recovery-control.py",
    Path("/usr/libexec/rog5-recovery-bundle-controller"),
    Path("/usr/libexec/rog5-recovery-host/host_bundle_server.py"),
    Path("/usr/libexec/rog5-recovery-host/rog5-recovery-host-client.py"),
    Path("/usr/libexec/rog5-recovery-host/serve-network-root.sh"),
)
BUILD_FILES = (
    "wrapper/repack/stable-recovery-a.avb.img",
    "wrapper/repack/stable-recovery-b.avb.img",
    "wrapper/repack/stable-recovery-a.raw.img",
    "wrapper/repack/stable-recovery-b.raw.img",
    "wrapper/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
    "wrapper/wrapper-b/asus-kexec-stage/arch/arm64/boot/Image",
    "wrapper/wrapper-a/asus-kexec-stage/.config",
    "wrapper/wrapper-b/asus-kexec-stage/.config",
    "recovery/initramfs-a/rog5-stable-recovery.cpio.gz",
    "recovery/initramfs-b/rog5-stable-recovery.cpio.gz",
    "recovery/components/rog5-recovery-control",
    "recovery/components/rog5-bundle-fetch",
    "recovery/components/rog5-bundle-verify",
    "recovery/components/rog5-bundle-verify-host-test",
    "recovery/ephemeral-public.raw",
)


class ReceiptError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise ReceiptError(message)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def identity(path: Path) -> dict[str, object]:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        fail(f"deployment input is unsafe: {path}")
    return {"size": metadata.st_size, "sha256": sha256(path)}


def mount() -> dict[str, str]:
    for line in Path("/proc/self/mountinfo").read_text(encoding="ascii").splitlines():
        left, separator, right = line.partition(" - ")
        if separator:
            fields = left.split()
            if len(fields) >= 6 and fields[4] == str(MOUNT_TARGET):
                return {
                    "root": fields[3],
                    "options": fields[5],
                    "source": right.split()[1],
                }
    fail("deployment bundle mount is absent")


def served() -> dict[str, object]:
    names = sorted(path.name for path in MOUNT_TARGET.iterdir())
    if len(names) != 1:
        fail("served bundle inventory is not singular")
    root = MOUNT_TARGET / names[0]
    files = {}
    for name in ("Image", "board.dtb", "initramfs.cpio.gz", "manifest", "manifest.sig"):
        files[name] = identity(root / name)
    return {"bundle": names[0], "files": files}


def active_policy_rows() -> list[str]:
    return [
        line
        for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
        if line.startswith(f"{POWER_USB.OUTPUT_ROOT}/") and "\tallow\t" in line
    ]


def build_files(build_root: Path) -> dict[str, dict[str, object]]:
    return {name: identity(build_root / name) for name in BUILD_FILES}


def snapshot(state: str, build_root: Path | None) -> dict[str, object]:
    if state not in {"planned", "built", "admitted"}:
        fail("deployment receipt state is invalid")
    if state == "planned":
        build = {}
    else:
        expected = REPO / POWER_USB.OUTPUT_ROOT
        if build_root is None or build_root.resolve(strict=True) != expected:
            fail("deployment build root is not canonical")
        build = build_files(build_root)
    return {
        "format": "rog5-power-usb-deployment-receipt-v1",
        "state": state,
        "git_head": subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip(),
        "active_lock": identity(LOCK),
        "candidate": POWER_USB.CANDIDATE,
        "candidate_record": identity(
            REPO / f"configs/recovery-candidates/{POWER_USB.CANDIDATE}.json"
        ),
        "expected_manifest_sha256": POWER_USB.EXPECTED_MANIFEST_SHA256,
        "output_root": POWER_USB.OUTPUT_ROOT,
        "mount": mount(),
        "served": served(),
        "components": {str(path): identity(path) if path.is_file() else {"size": 0, "sha256": "absent"} for path in COMPONENTS},
        "build": build,
        "policy_sha256": sha256(POLICY),
        "active_policy_rows": active_policy_rows(),
    }


def validate(value: dict[str, object]) -> None:
    state = value.get("state")
    served_value = value.get("served")
    rows = value.get("active_policy_rows")
    build = value.get("build")
    if (
        value.get("format") != "rog5-power-usb-deployment-receipt-v1"
        or state not in {"planned", "built", "admitted"}
        or value.get("candidate") != POWER_USB.CANDIDATE
        or value.get("expected_manifest_sha256") != POWER_USB.EXPECTED_MANIFEST_SHA256
        or value.get("output_root") != POWER_USB.OUTPUT_ROOT
        or not isinstance(served_value, dict)
        or not isinstance(rows, list)
        or not isinstance(build, dict)
        or "ro" not in str(value["mount"]["options"]).split(",")
    ):
        fail("deployment receipt schema or identity is invalid")
    if state == "planned":
        if build or rows or served_value.get("bundle") == POWER_USB.BUNDLE:
            fail("planned receipt accidentally carries active deployment authority")
        return
    manifest = served_value.get("files", {}).get("manifest", {})
    if (
        len(build) != len(BUILD_FILES)
        or served_value.get("bundle") != POWER_USB.BUNDLE
        or manifest.get("sha256") != POWER_USB.EXPECTED_MANIFEST_SHA256
    ):
        fail("built deployment receipt does not match served active bytes")
    image_a = build["wrapper/repack/stable-recovery-a.avb.img"]
    image_b = build["wrapper/repack/stable-recovery-b.avb.img"]
    raw_a = build["wrapper/repack/stable-recovery-a.raw.img"]
    raw_b = build["wrapper/repack/stable-recovery-b.raw.img"]
    if image_a != image_b or raw_a != raw_b:
        fail("deployment clean twins differ")
    for first, second in (
        (
            "wrapper/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
            "wrapper/wrapper-b/asus-kexec-stage/arch/arm64/boot/Image",
        ),
        (
            "wrapper/wrapper-a/asus-kexec-stage/.config",
            "wrapper/wrapper-b/asus-kexec-stage/.config",
        ),
        (
            "recovery/initramfs-a/rog5-stable-recovery.cpio.gz",
            "recovery/initramfs-b/rog5-stable-recovery.cpio.gz",
        ),
    ):
        if build[first] != build[second]:
            fail("deployment clean twins differ")
    if state == "built" and rows:
        fail("built receipt unexpectedly carries boot authority")
    if state == "admitted" and len(rows) != 1:
        fail("admitted receipt lacks one exact policy row")


def publish(path: Path, value: dict[str, object]) -> None:
    path = Path(os.path.abspath(path))
    parent = path.parent
    metadata = parent.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or os.path.lexists(path)
    ):
        fail("deployment receipt output path is unsafe")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read(path: Path) -> dict[str, object]:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
        or metadata.st_nlink != 1
    ):
        fail("deployment receipt metadata is unsafe")
    return json.loads(path.read_text(encoding="ascii"))


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--state", choices=("planned", "built", "admitted"), required=True)
    capture.add_argument("--build-root", type=Path)
    capture.add_argument("output", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("receipt", type=Path)
    verify.add_argument("--build-root", type=Path)
    values = parser.parse_args(arguments)
    if values.action == "capture":
        result = snapshot(values.state, values.build_root)
        validate(result)
        publish(values.output, result)
        print(f"PASS exact {values.state} deployment receipt captured")
        return 0
    expected = read(values.receipt)
    current = snapshot(str(expected["state"]), values.build_root)
    validate(expected)
    if current != expected:
        fail("deployed composition drifted from its immutable receipt")
    print(f"PASS exact {expected['state']} deployment receipt verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ReceiptError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
