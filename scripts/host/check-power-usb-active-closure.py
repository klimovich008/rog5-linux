#!/usr/bin/env python3
"""Fail fast unless the active power/USB track is one coherent identity."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import generated_power_usb_active as POWER_USB


REPO = Path(__file__).resolve().parents[2]
POLICY = REPO / "manifests/temporary-boot-images.tsv"
ARTIFACTS = REPO / "manifests/artifacts.tsv"
LOCK = REPO / "manifests/power-usb-active.lock.json"


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def exact_rows(path: Path, prefix: str) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()[1:]
        if line.startswith(prefix)
    ]


def receipt_verify_command(receipt: Path, state: object) -> list[str]:
    command = [
        sys.executable,
        str(REPO / "scripts/host/power-usb-deployment-receipt.py"),
        "verify",
        str(receipt),
    ]
    if state in {"built", "admitted"}:
        command.extend(("--build-root", str(REPO / POWER_USB.OUTPUT_ROOT)))
    return command


def validate(stage: str, receipt: Path | None) -> str:
    subprocess.run(
        [sys.executable, str(REPO / "scripts/host/generate-power-usb-active.py")],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    lock = json.loads(LOCK.read_text(encoding="ascii"))
    candidate_path = REPO / str(lock["candidate_path"])
    candidate = json.loads(candidate_path.read_text(encoding="ascii"))
    if (
        lock.get("candidate") != POWER_USB.CANDIDATE
        or lock.get("candidate_sha256") != sha256(candidate_path)
        or candidate.get("candidate") != POWER_USB.CANDIDATE
        or candidate.get("bundle") != POWER_USB.BUNDLE
        or candidate.get("target_id") != POWER_USB.TARGET_ID
        or candidate.get("profile") != POWER_USB.BUNDLE_PROFILE
        or candidate.get("target_release") != POWER_USB.TARGET_RELEASE
        or candidate.get("authority") != "none"
        or candidate.get("artifacts") != POWER_USB.ARTIFACTS
        or lock.get("expected_manifest_sha256")
        != POWER_USB.EXPECTED_MANIFEST_SHA256
        or lock.get("output_root") != POWER_USB.OUTPUT_ROOT
        or lock.get("timing", {}).get("target_timeout_seconds")
        != int(candidate["target_timeout"])
        or lock.get("timing", {}).get("rollback_timeout_seconds")
        != int(candidate["rollback_timeout"])
        or lock.get("capability") != POWER_USB.CAPABILITY
    ):
        fail("candidate, bundle, target, profile, timing, or artifact closure differs")

    prefix = f"{POWER_USB.OUTPUT_ROOT}/wrapper/repack/stable-recovery-a.avb.img\t"
    policy_rows = exact_rows(POLICY, prefix)
    artifact_rows = exact_rows(ARTIFACTS, prefix)
    if stage == "auto":
        if policy_rows and "\trevoked\t" in policy_rows[0]:
            stage = "revoked"
        else:
            stage = "admitted" if policy_rows or artifact_rows else "planned"
    expected_policy_rows = 1 if stage in {"admitted", "revoked"} else 0
    expected_artifact_rows = 1 if stage in {"admitted", "revoked"} else 0
    if len(policy_rows) != expected_policy_rows or len(artifact_rows) != expected_artifact_rows:
        fail("active live-policy/artifact row count differs from the requested stage")
    if stage == "admitted":
        if policy_rows[0] != f"{prefix}allow\t{POWER_USB.BOOT_POLICY_BASIS}":
            fail("active live-policy row is not canonical")
        fields = artifact_rows[0].split("\t")
        if len(fields) != 5 or fields[3] != POWER_USB.ARTIFACT_ROLE or fields[4] != "no":
            fail("active artifact row is not canonical")
    elif stage == "revoked":
        if "\trevoked\t" not in policy_rows[0]:
            fail("revoked active policy row is not canonical")
        fields = artifact_rows[0].split("\t")
        if (
            len(fields) != 5
            or fields[1] != "100663296"
            or len(fields[2]) != 64
            or fields[4] != "no"
        ):
            fail("revoked active artifact row is malformed")

    capability = POWER_USB.CAPABILITY
    for key in ("recovery_verifier", "fallback_verifier", "target_verifier"):
        path = REPO / str(capability[key])
        if not path.is_file() or path.is_symlink():
            fail(f"capability verifier is absent: {key}")
    recovery = (REPO / str(capability["recovery_verifier"])).read_text(
        encoding="utf-8"
    )
    for token in (
        "exact-a600000-v1",
        "rog5-recovery-control",
        "rog5-bundle-fetch",
        "rog5-bundle-verify",
        "usr/sbin/kexec",
        "ip address add 169.254.77.2/30 dev usb0",
    ):
        if token not in recovery:
            fail(f"recovery capability verifier lacks {token}")
    fallback = (REPO / str(capability["fallback_verifier"])).read_text(
        encoding="utf-8"
    )
    for token in (
        'SERIAL = "M5AIKN00F0353YH"',
        'values["product"] != "lahaina"',
        'values["slot"] != "a"',
    ):
        if token not in fallback:
            fail(f"fallback capability verifier lacks {token}")

    if receipt is not None:
        receipt_value = json.loads(receipt.read_text(encoding="ascii"))
        result = subprocess.run(
            receipt_verify_command(receipt, receipt_value.get("state")),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode != 0:
            fail(result.stdout.strip() or "deployment receipt verification failed")
        receipt_states = (
            {"planned", "built"}
            if stage == "planned"
            else {"admitted"}
            if stage == "admitted"
            else {"revoked"}
        )
        if (
            receipt_value.get("state") not in receipt_states
            or receipt_value.get("candidate") != POWER_USB.CANDIDATE
            or receipt_value.get("output_root") != POWER_USB.OUTPUT_ROOT
        ):
            fail("deployment receipt does not represent the requested active stage")
    return stage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", choices=("auto", "planned", "admitted", "revoked"), default="auto"
    )
    parser.add_argument("--deployment-receipt", type=Path)
    arguments = parser.parse_args()
    stage = validate(arguments.stage, arguments.deployment_receipt)
    print(f"PASS active power/USB {stage} dependency closure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
