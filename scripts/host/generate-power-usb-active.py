#!/usr/bin/env python3
"""Generate the active power/USB candidate record, locks, and boot policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "configs/recovery-candidates/power-usb-active.json"
PYTHON_LOCK = REPO / "scripts/host/generated_power_usb_active.py"
SHELL_LOCK = REPO / "scripts/host/generated-power-usb-active.sh"
LOCK = REPO / "manifests/power-usb-active.lock.json"
POLICY = REPO / "manifests/temporary-boot-images.tsv"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class GenerationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, value in items:
            if name in result:
                raise GenerationError(f"duplicate JSON field: {name}")
            result[name] = value
        return result

    return json.loads(path.read_text(encoding="ascii"), object_pairs_hook=pairs)


def encoded_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate(source: dict[str, object]) -> tuple[dict[str, object], dict[str, str]]:
    if source.get("format") != "rog5-power-usb-candidate-source-v1":
        raise GenerationError("unsupported canonical candidate source")
    record = source.get("record")
    integration = source.get("integration")
    if not isinstance(record, dict) or not isinstance(integration, dict):
        raise GenerationError("candidate source lacks record or integration")
    strings = {name: value for name, value in integration.items() if isinstance(value, str)}
    required = {
        "admission_profile",
        "recovery_profile",
        "runtime_profile",
        "build_profile",
        "expected_dtb_sha256",
        "expected_manifest_sha256",
        "output_root",
        "marker_predecessor",
        "marker_purpose",
        "boot_policy_status",
        "boot_policy_basis",
        "artifact_role",
    }
    if set(strings) != required or set(integration) != required:
        raise GenerationError("candidate integration schema changed")
    candidate = record.get("candidate")
    if (
        not isinstance(candidate, str)
        or not re.fullmatch(r"headless-power-usb-observer-v[1-9][0-9]*", candidate)
        or record.get("bundle") != candidate
        or record.get("target_id") != candidate
        or record.get("authority") != "none"
        or strings["boot_policy_status"] != "none"
        or not SHA256.fullmatch(strings["expected_dtb_sha256"])
        or not SHA256.fullmatch(strings["expected_manifest_sha256"])
    ):
        raise GenerationError("candidate identity is invalid")
    return record, strings


def validate_timing(
    source: dict[str, object], record: dict[str, object]
) -> dict[str, int]:
    timing = source.get("timing")
    expected = {
        "prepare_timeout_seconds",
        "host_readiness_seconds",
        "control_timeout_seconds",
        "recovery_timeout_seconds",
        "target_timeout_seconds",
        "rollback_timeout_seconds",
        "fallback_timeout_seconds",
        "cleanup_margin_seconds",
        "network_server_timeout_seconds",
        "sampler_timeout_seconds",
        "fallback_control_margin_seconds",
        "fallback_contact_budget_seconds",
    }
    if (
        not isinstance(timing, dict)
        or set(timing) != expected
        or any(type(value) is not int or value <= 0 for value in timing.values())
    ):
        raise GenerationError("timing lattice schema changed")
    values = {name: int(value) for name, value in timing.items()}
    if (
        str(values["target_timeout_seconds"]) != record["target_timeout"]
        or str(values["rollback_timeout_seconds"]) != record["rollback_timeout"]
        or values["recovery_timeout_seconds"]
        < values["prepare_timeout_seconds"] + 40
        or values["control_timeout_seconds"]
        < values["prepare_timeout_seconds"]
        + values["host_readiness_seconds"]
        + 10
        or values["rollback_timeout_seconds"]
        < values["target_timeout_seconds"] + values["cleanup_margin_seconds"]
        or values["network_server_timeout_seconds"]
        < values["rollback_timeout_seconds"] + values["cleanup_margin_seconds"]
        or values["sampler_timeout_seconds"]
        < values["rollback_timeout_seconds"] + 60
        or values["fallback_contact_budget_seconds"]
        < values["recovery_timeout_seconds"]
        + values["rollback_timeout_seconds"]
        + values["fallback_timeout_seconds"]
    ):
        raise GenerationError("timing lattice is inconsistent")
    return values


def validate_host(source: dict[str, object]) -> dict[str, object]:
    host = source.get("host")
    expected = {
        "measured_peak_build_bytes",
        "minimum_free_bytes",
        "minimum_free_inodes",
        "project_tcp_ports",
        "networkmanager_profile",
        "networkmanager_autoconnect",
        "usb_location",
        "fastboot_serial",
        "fastboot_product",
    }
    if not isinstance(host, dict) or set(host) != expected:
        raise GenerationError("host requirement schema changed")
    if (
        type(host["measured_peak_build_bytes"]) is not int
        or type(host["minimum_free_bytes"]) is not int
        or type(host["minimum_free_inodes"]) is not int
        or host["minimum_free_bytes"] < host["measured_peak_build_bytes"] * 5
        or host["minimum_free_inodes"] < 100000
        or host["project_tcp_ports"] != [2049, 8080, 8081]
        or host["networkmanager_autoconnect"] != "no"
        or host["usb_location"] != "1-1.2"
        or not re.fullmatch(r"[A-Za-z0-9]+", str(host["fastboot_serial"]))
        or host["fastboot_product"] != "lahaina"
    ):
        raise GenerationError("host requirements are invalid")
    return host


def validate_capability(source: dict[str, object]) -> dict[str, object]:
    capability = source.get("capability")
    expected = {
        "recovery_contract": "exact-a600000-v1",
        "recovery_verifier": "scripts/device/verify-stable-recovery-initramfs.sh",
        "fallback_verifier": "scripts/host/wait-stock-android-fallback.py",
        "target_verifier": "scripts/device/verify-network-root-initramfs.sh",
        "recovery_commands": [
            "busybox", "ip", "kexec", "mount", "rog5-bundle-fetch",
            "rog5-bundle-verify", "rog5-recovery-control",
        ],
        "target_commands": ["ip", "mount", "sshd", "systemd", "watchdog"],
        "host_commands": [
            "fastboot", "firewall-cmd", "ip", "nmcli", "ss", "systemctl",
        ],
    }
    if capability != expected:
        raise GenerationError("capability closure changed")
    return capability


def python_payload(
    record: dict[str, object],
    values: dict[str, str],
    timing: dict[str, int],
    host: dict[str, object],
    capability: dict[str, object],
    candidate_sha256: str,
) -> bytes:
    artifacts = json.dumps(record["artifacts"], sort_keys=True)
    lines = ["# Generated by generate-power-usb-active.py; do not edit."]
    for name, value in (
        ("CANDIDATE", record["candidate"]),
        ("BUNDLE", record["bundle"]),
        ("TARGET_ID", record["target_id"]),
        ("BUNDLE_PROFILE", record["profile"]),
        ("TARGET_RELEASE", record["target_release"]),
        ("ROLLBACK_TIMEOUT", record["rollback_timeout"]),
        ("TARGET_TIMEOUT", record["target_timeout"]),
        ("ADMISSION_PROFILE", values["admission_profile"]),
        ("RECOVERY_PROFILE", values["recovery_profile"]),
        ("RUNTIME_PROFILE", values["runtime_profile"]),
        ("BUILD_PROFILE", values["build_profile"]),
        ("EXPECTED_DTB_SHA256", values["expected_dtb_sha256"]),
        ("EXPECTED_MANIFEST_SHA256", values["expected_manifest_sha256"]),
        ("OUTPUT_ROOT", values["output_root"]),
        ("BOOT_POLICY_BASIS", values["boot_policy_basis"]),
        ("ARTIFACT_ROLE", values["artifact_role"]),
        ("CANDIDATE_SHA256", candidate_sha256),
    ):
        lines.append(f"{name} = {value!r}")
    lines.append(f"ARTIFACTS = {artifacts}")
    for name, value in sorted(timing.items()):
        lines.append(f"{name.upper()} = {value}")
    lines.append(f"HOST = {json.dumps(host, sort_keys=True)}")
    lines.append(f"CAPABILITY = {json.dumps(capability, sort_keys=True)}")
    return ("\n".join(lines) + "\n").encode("ascii")


def shell_payload(
    record: dict[str, object],
    values: dict[str, str],
    timing: dict[str, int],
    host: dict[str, object],
    candidate_sha256: str,
) -> bytes:
    pairs = (
        ("POWER_USB_CANDIDATE", record["candidate"]),
        ("POWER_USB_BUNDLE", record["bundle"]),
        ("POWER_USB_TARGET_ID", record["target_id"]),
        ("POWER_USB_BUNDLE_PROFILE", record["profile"]),
        ("POWER_USB_ADMISSION_PROFILE", values["admission_profile"]),
        ("POWER_USB_RECOVERY_PROFILE", values["recovery_profile"]),
        ("POWER_USB_RUNTIME_PROFILE", values["runtime_profile"]),
        ("POWER_USB_BUILD_PROFILE", values["build_profile"]),
        ("POWER_USB_EXPECTED_DTB_SHA256", values["expected_dtb_sha256"]),
        ("POWER_USB_EXPECTED_MANIFEST_SHA256", values["expected_manifest_sha256"]),
        ("POWER_USB_OUTPUT_ROOT", values["output_root"]),
        ("POWER_USB_BOOT_POLICY_BASIS", values["boot_policy_basis"]),
        ("POWER_USB_ARTIFACT_ROLE", values["artifact_role"]),
        ("POWER_USB_CANDIDATE_SHA256", candidate_sha256),
    )
    lines = ["# Generated by generate-power-usb-active.py; do not edit."]
    lines.extend(f"readonly {name}={shlex.quote(str(value))}" for name, value in pairs)
    lines.extend(
        f"readonly POWER_USB_{name.upper()}={value}"
        for name, value in sorted(timing.items())
    )
    lines.extend(
        (
            f"readonly POWER_USB_MINIMUM_FREE_BYTES={host['minimum_free_bytes']}",
            f"readonly POWER_USB_MINIMUM_FREE_INODES={host['minimum_free_inodes']}",
            "readonly POWER_USB_PROJECT_TCP_PORTS='2049 8080 8081'",
            f"readonly POWER_USB_NM_PROFILE={shlex.quote(str(host['networkmanager_profile']))}",
            f"readonly POWER_USB_NM_AUTOCONNECT={host['networkmanager_autoconnect']}",
            f"readonly POWER_USB_USB_LOCATION={host['usb_location']}",
            f"readonly POWER_USB_FASTBOOT_SERIAL={host['fastboot_serial']}",
            f"readonly POWER_USB_FASTBOOT_PRODUCT={host['fastboot_product']}",
        )
    )
    return ("\n".join(lines) + "\n").encode("ascii")


def marker_payload(record: dict[str, object], values: dict[str, str]) -> bytes:
    return (
        "format=rog5-recovery-candidate-marker-v1\n"
        f"candidate={record['candidate']}\n"
        f"predecessor={values['marker_predecessor']}\n"
        f"purpose={values['marker_purpose']}\n"
    ).encode("ascii")


def policy_payload(record: dict[str, object], values: dict[str, str]) -> bytes:
    lines = POLICY.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "name\tstatus\tbasis":
        raise GenerationError("temporary-boot policy header changed")
    lines = [
        line
        for line in lines
        if not (
            line.startswith("build/power-usb-observer-")
            and "\tallow\t" in line
        )
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def outputs() -> dict[Path, bytes]:
    source = load_json(SOURCE)
    record, values = validate(source)
    timing = validate_timing(source, record)
    host = validate_host(source)
    capability = validate_capability(source)
    candidate_payload = encoded_json(record)
    marker = marker_payload(record, values)
    candidate_sha256 = digest(candidate_payload)
    python_lock = python_payload(
        record, values, timing, host, capability, candidate_sha256
    )
    shell_lock = shell_payload(record, values, timing, host, candidate_sha256)
    candidate_path = REPO / f"configs/recovery-candidates/{record['candidate']}.json"
    marker_path = REPO / f"configs/recovery-candidates/markers/{record['candidate']}"
    lock = {
        "format": "rog5-power-usb-generated-lock-v1",
        "source_sha256": digest(SOURCE.read_bytes()),
        "candidate": record["candidate"],
        "candidate_path": candidate_path.relative_to(REPO).as_posix(),
        "candidate_sha256": candidate_sha256,
        "marker_sha256": digest(marker),
        "python_lock_sha256": digest(python_lock),
        "shell_lock_sha256": digest(shell_lock),
        "expected_manifest_sha256": values["expected_manifest_sha256"],
        "output_root": values["output_root"],
        "boot_policy_basis": values["boot_policy_basis"],
        "artifact_role": values["artifact_role"],
        "boot_policy_status": values["boot_policy_status"],
        "timing": timing,
        "host": host,
        "capability": capability,
    }
    return {
        candidate_path: candidate_payload,
        marker_path: marker,
        PYTHON_LOCK: python_lock,
        SHELL_LOCK: shell_lock,
        LOCK: encoded_json(lock),
        POLICY: policy_payload(record, values),
    }


def verify_consumer_closure(source: dict[str, object]) -> None:
    record, values = validate(source)
    candidate = str(record["candidate"])
    allowed = {
        SOURCE.relative_to(REPO).as_posix(),
        f"configs/recovery-candidates/{candidate}.json",
        f"configs/recovery-candidates/markers/{candidate}",
        PYTHON_LOCK.relative_to(REPO).as_posix(),
        SHELL_LOCK.relative_to(REPO).as_posix(),
        LOCK.relative_to(REPO).as_posix(),
    }
    names = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-co", "--exclude-standard"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.splitlines()
    leaks = []
    for name in names:
        path = REPO / name
        if name in allowed or not path.is_file() or path.is_symlink():
            continue
        try:
            payload = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if candidate in payload or values["runtime_profile"] in payload:
            leaks.append(name)
    if leaks:
        raise GenerationError(
            "active candidate identity leaked outside generated closure: "
            + ", ".join(sorted(leaks))
        )
    required = {
        "scripts/host/verify-headless-ssh-v2-key-admission.py": (
            "import generated_power_usb_active as POWER_USB",
        ),
        "scripts/host/verify-minimal-headless-runtime.py": (
            "import generated_power_usb_active as POWER_USB",
        ),
        "scripts/host/run-minimal-headless-live-cycle.py": (
            "import generated_power_usb_active as POWER_USB",
        ),
        "scripts/host/stable-recovery-control.py": (
            "import generated_power_usb_active as POWER_USB",
        ),
        "scripts/host/run-minimal-headless-runtime-acceptance.sh": (
            "source \"$script_dir/generated-power-usb-active.sh\"",
        ),
        "scripts/host/build-corrected-headless-candidate-offline-impl.sh": (
            "source \"$repo/scripts/host/generated-power-usb-active.sh\"",
        ),
        "scripts/host/run-stable-recovery-live-gate.sh": (
            "source \"$repo/scripts/host/generated-power-usb-active.sh\"",
            "$POWER_USB_RECOVERY_PROFILE)",
        ),
        "scripts/device/collect-minimal-headless-runtime.sh": (
            "ROG5_RUNTIME_ALLOWED_CANDIDATE",
        ),
    }
    for name, markers in required.items():
        payload = (REPO / name).read_text(encoding="utf-8")
        if any(marker not in payload for marker in markers):
            raise GenerationError(f"active candidate consumer is not generated: {name}")
        if "headless-power-usb-observer-v3" in payload and name != (
            "scripts/host/build-corrected-headless-candidate-offline-impl.sh"
        ):
            raise GenerationError(f"active candidate consumer still selects v3: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    generated = outputs()
    changed: list[str] = []
    for path, payload in generated.items():
        current = path.read_bytes() if path.exists() else None
        if current == payload:
            continue
        changed.append(path.relative_to(REPO).as_posix())
    if changed and args.write:
        with tempfile.TemporaryDirectory(prefix="rog5-power-usb-generate-") as raw:
            stage = Path(raw)
            for index, (path, payload) in enumerate(generated.items()):
                staged = stage / str(index)
                staged.write_bytes(payload)
                if staged.read_bytes() != payload:
                    raise GenerationError("staged generated output changed")
                if path.suffix == ".json":
                    load_json(staged)
            for path, payload in generated.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{path.name}.", dir=path.parent
                )
                temporary = Path(temporary_name)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(payload)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, 0o644)
                    os.replace(temporary, path)
                finally:
                    temporary.unlink(missing_ok=True)
    if changed and not args.write:
        raise GenerationError("generated outputs differ: " + ", ".join(changed))
    verify_consumer_closure(load_json(SOURCE))
    print("PASS power/USB candidate generated outputs are current")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GenerationError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
