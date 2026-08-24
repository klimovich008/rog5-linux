#!/usr/bin/env python3
"""Run one guarded recovery-to-headless-to-fallback lifecycle."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import stat
import subprocess
import sys
import time
from typing import NoReturn

import generated_power_usb_active as POWER_USB


REPO = Path(__file__).resolve().parents[2]
CANDIDATE = "headless-ssh-network-root-v3"
BUNDLE = "headless-ssh-network-root-v3-r2"
RECOVERY_PROFILE = "headless-ssh-deployment-v3"
CORE_RECOVERY_PROFILE = "headless-core-deployment-v1-live-v1"
POWER_USB_RECOVERY_PROFILE = POWER_USB.RECOVERY_PROFILE
DIAGNOSTIC_RECOVERY_PROFILE = (
    "headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1"
)
DIAGNOSTIC_LIVE_STATUS = "admitted"
DIAGNOSTIC_CANDIDATE = "headless-netroot-early-diag-v2"
DIAGNOSTIC_BUNDLE = "headless-netroot-early-diag-v2"
DIAGNOSTIC_PROFILE = "diagnostic-initramfs-v1"
DIAGNOSTIC_ADMISSION_PROFILE = "early-target-diagnostic-v2"
DIAGNOSTIC_COLLECTOR_READY = (
    "READY receive-only early-target diagnostic collector"
)
FALLBACK_KERNEL = "5.4.134-qgki-perf-00001-g6c308144c23e"
FALLBACK_CONTROL_MARGIN_SECONDS = POWER_USB.FALLBACK_CONTROL_MARGIN_SECONDS
FALLBACK_CONTACT_START_BUDGET_SECONDS = POWER_USB.FALLBACK_CONTACT_BUDGET_SECONDS
FALLBACK_NETWORK_PROFILE = "rog5-fallback-usb-ssh"
BUNDLE_HOST_ADDRESS = "169.254.77.1"
TARGET_PRODUCT = "ROG5 network root"
DIAGNOSTIC_TARGET_PRODUCT = "ROG5 diagnostic network root"
ROG5_NCM_MODELS = frozenset(
    {
        "ROG5_recovery",
        "ROG5_network_root",
        "ROG5_diagnostic_network_root",
        "ROG5_persistent_root",
        "ROG_Phone_5_Linux_Server",
    }
)
BUNDLE_TIMEOUT_SECONDS = POWER_USB.PREPARE_TIMEOUT_SECONDS
CONTROL_TIMEOUT_SECONDS = POWER_USB.CONTROL_TIMEOUT_SECONDS
ZERO_SHA256 = "0" * 64
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ZERO_ID = "0" * 32
PROGRESS_PHASES = (
    "REQUEST_ACCEPTED",
    "FETCH_COMPLETE",
    "VERIFY_COMPLETE",
    "KEXEC_LOAD_COMPLETE",
    "PREPARED_PERSISTED",
)
CONSUMED_MANIFESTS = {
    "457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e",
    "9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630",
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SSH_FINGERPRINT = re.compile(r"SHA256:[A-Za-z0-9+/]{43}\Z")
HEX_ID = re.compile(r"[0-9a-f]{32}\Z")
POSTMORTEM_TAIL_HEX = re.compile(r"(?:[0-9a-f]{2}){1,512}\Z")
CONTROL_RESPONSE_FIELDS = frozenset(
    {
        "session",
        "request",
        "verb",
        "result",
        "state",
        "prepared_bundle",
        "manifest_sha256",
        "prepare_request",
        "commit_request",
        "commit_fingerprint",
        "execution_started",
        "watchdog",
        "last_error",
        "postmortem_state",
        "postmortem_records",
        "postmortem_bytes",
        "postmortem_sha256",
        "postmortem_tail_hex",
        "postmortem_lineage_state",
        "postmortem_lineage_matches",
        "postmortem_lineage_sha256",
    }
)
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
USB_LOCATION = re.compile(r"[A-Za-z0-9._:/+-]{1,512}\Z")
ANCHOR_PATH = re.compile(r"/[A-Za-z0-9._/+-]{1,399}\Z")
FULL_GUARDS = (
    "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE",
    "ALLOW_HEADLESS_SSH_KEY_ADMISSION",
    "ALLOW_TEMPORARY_BOOT",
    "ALLOW_HEADLESS_LIVE_GATE",
    "ALLOW_STABLE_RECOVERY_CONTROL",
    "ALLOW_ATTENDED_KEXEC",
    "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
    "ALLOW_HEADLESS_NETWORK_ROOT_SERVER",
    "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP",
    "ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE",
    "ALLOW_PHONE_CREDENTIAL_USE",
    "ALLOW_FALLBACK_SSH_CONTROL",
    "ALLOW_FALLBACK_SSH_ATIME_EFFECTS",
)
KEY_GUARDS = (
    "ALLOW_HEADLESS_SSH_KEY_ADMISSION",
    "ALLOW_PHONE_CREDENTIAL_USE",
)
PASSTHROUGH_ENVIRONMENT = (
    "HOME",
    "USER",
    "LOGNAME",
    "XDG_STATE_HOME",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "LIVE_BUILD_ROOT",
    "RECOVERY_COMPONENT_ROOT",
    "TRUST_KEY",
    "BUNDLE_ROOT",
    "BUNDLE",
    "RECOVERY_SHA256",
    "TRUST_KEY_SHA256",
    "MANIFEST_SHA256",
    "HOST_VERIFIER_SHA256",
    "ROG5_STABLE_RECOVERY_PROFILE",
    "FASTBOOT_SERIAL",
    "ACM_TIMEOUT",
    "ROG5_NFS_TIMEOUT",
    "ROG5_EXPECTED_USB_LOCATION",
    "ROG5_RETENTION_BOOT_RESULT",
    "ROG5_LIVE_CYCLE_OFFLINE_TEST",
    "ROG5_LIVE_CYCLE_TEST_ROOT",
    "ROG5_HOST_DOCTOR_RECEIPT",
    "ROG5_POWER_USB_DEPLOYMENT_RECEIPT",
)

CLAIM_CONSUMER_PATH = REPO / "scripts/host/consume-exact-boot-claim.py"
STOCK_FALLBACK_PATH = REPO / "scripts/host/wait-stock-android-fallback.py"
_CLAIM_SPEC = importlib.util.spec_from_file_location(
    "rog5_live_cycle_claim_consumer", CLAIM_CONSUMER_PATH
)
if _CLAIM_SPEC is None or _CLAIM_SPEC.loader is None:
    raise RuntimeError("exact boot-claim consumer is unavailable")
CLAIM_CONSUMER = importlib.util.module_from_spec(_CLAIM_SPEC)
sys.modules[_CLAIM_SPEC.name] = CLAIM_CONSUMER
_CLAIM_SPEC.loader.exec_module(CLAIM_CONSUMER)
OUTPUT_NAMES = (
    "stable-recovery-boot.log",
    "recovery-usb-anchor.log",
    "recovery-usb.anchor",
    "bundle-server.log",
    "recovery-control.log",
    "network-root-server.log",
    "target-host-key.log",
    "target-known-hosts",
    "runtime-acceptance.log",
    "power-usb-observation.log",
    "minimal-headless-runtime.record",
    "fallback-identity.record",
    "stock-fallback-preboot.log",
    "stock-fallback-preboot.record",
    "fallback-profile-restore.log",
    "fallback-postmortem.log",
    "fallback-postmortem.record",
    "fallback-preflight.log",
    "intent-resolution.log",
    "early-target-diagnostics.log",
    "early-target-diagnostics.json",
    "recovery-progress.capture",
    "recovery-progress.stop",
    "recovery-progress-assessment.record",
)
FALLBACK_POSTMORTEM_FIELDS = (
    "format",
    "expected_candidate",
    "expected_boot_id",
    "fallback_boot_id",
    "usb_location",
    "pstore_state",
    "pstore_records",
    "pstore_bytes",
    "pstore_sha256",
    "pmic_pon_state",
    "pmic_pon_records",
    "pmic_pon_sha256",
    "pmic_cycle_entries",
    "pmic_reset_trigger",
    "pmic_reset_type",
    "pmic_watchdog_signal",
    "lineage_matches",
    "lineage_records",
    "fatal_tokens_total",
    "fatal_after_lineage",
    "correlation",
    "fatal_state",
    "nonce",
    "record_sha256",
    "signature_sha256",
    "host_pin_sha256",
    "result",
)
ANCHOR_FIELDS = (
    "format",
    "host_boot_id",
    "created_unix",
    "usb_location",
    "recovery_vendor",
    "recovery_product_id",
    "recovery_product",
)
STOCK_FALLBACK_FIELDS = (
    "format",
    "serial",
    "usb_location",
    "product",
    "model",
    "device",
    "evidence_mode",
    "slot_suffix",
    "fingerprint",
    "vbmeta_digest",
    "verified_boot_state",
    "boot_id",
    "boot_completed",
    "usb_config",
    "result",
)
KEY_ADMISSION_FIELDS = (
    "format",
    "candidate",
    "bundle",
    "profile",
    "build_profile",
    "target_id",
    "authorized_key_fingerprint",
    "public_key_sha256",
    "package_sha256",
    "candidate_sha256",
    "manifest_sha256",
    "root_tree_sha256",
    "root_seal_sha256",
    "root_tree_entries",
    "authority",
)


class CycleError(RuntimeError):
    """A fail-closed lifecycle condition."""


class HostIdentityObservationError(CycleError):
    """A transient disagreement between USB identity and host address views."""


def fail(message: str) -> NoReturn:
    raise CycleError(message)


@dataclass(frozen=True)
class Dependencies:
    git: Path
    ss: Path
    ip: Path
    nmcli: Path
    udevadm: Path
    firewall: Path
    live_gate: Path
    bundle_server: Path
    network_root_server: Path
    recovery_control: Path
    host_key: Path
    runtime_acceptance: Path
    diagnostic_collector: Path
    fallback: Path
    stock_fallback: Path
    key_admission: Path
    host_doctor: Path
    deployment_receipt: Path
    handoff_marker: Path
    network_service_state: Path
    export_mount: Path
    nfs_exports: Path
    nfs_threads: Path
    ip_nonlocal_bind: Path
    host_boot_id: Path
    sys_class_net: Path
    offline: bool

    @classmethod
    def from_environment(cls) -> "Dependencies":
        if os.environ.get("ROG5_LIVE_CYCLE_OFFLINE_TEST") == "1":
            root_value = os.environ.get("ROG5_LIVE_CYCLE_TEST_ROOT", "")
            if not root_value:
                fail("offline lifecycle test root is absent")
            root = Path(root_value).resolve(strict=True)
            if not root.is_dir() or root.is_symlink() or os.geteuid() == 0:
                fail("offline lifecycle test root is unsafe")
            state = root / "state"
            return cls(
                git=root / "git",
                ss=root / "ss",
                ip=root / "ip",
                nmcli=root / "nmcli",
                udevadm=root / "udevadm",
                firewall=root / "firewall-cmd",
                live_gate=root / "run-stable-recovery-live-gate.sh",
                bundle_server=root / "run-recovery-bundle-server.sh",
                network_root_server=(
                    root / "run-headless-network-root-server.sh"
                ),
                recovery_control=root / "stable-recovery-control.py",
                host_key=root / "pin-minimal-headless-host-key.py",
                runtime_acceptance=(
                    root / "run-minimal-headless-runtime-acceptance.sh"
                ),
                diagnostic_collector=(
                    root / "collect-early-target-diagnostics.py"
                ),
                fallback=root / "fallback-acm-control.py",
                stock_fallback=root / "wait-stock-android-fallback.py",
                key_admission=(
                    root / "verify-headless-ssh-v2-key-admission.py"
                ),
                host_doctor=root / "rog5-host-doctor.py",
                deployment_receipt=root / "power-usb-deployment-receipt.py",
                handoff_marker=state / "nfs-ready",
                network_service_state=root / "nfs-state",
                export_mount=state / "export-mount",
                nfs_exports=state / "nfs-exports",
                nfs_threads=state / "nfs-threads",
                ip_nonlocal_bind=state / "ip-nonlocal-bind",
                host_boot_id=state / "host-boot-id",
                sys_class_net=state / "sys-class-net",
                offline=True,
            )
        return cls(
            git=Path("/usr/bin/git"),
            ss=Path("/usr/bin/ss"),
            ip=Path("/usr/bin/ip"),
            nmcli=Path("/usr/bin/nmcli"),
            udevadm=Path("/usr/bin/udevadm"),
            firewall=Path("/usr/bin/firewall-cmd"),
            live_gate=REPO / "scripts/host/run-stable-recovery-live-gate.sh",
            bundle_server=(
                REPO / "scripts/host/run-recovery-bundle-server.sh"
            ),
            network_root_server=(
                REPO / "scripts/host/run-headless-network-root-server.sh"
            ),
            recovery_control=(
                REPO / "scripts/host/stable-recovery-control.py"
            ),
            host_key=(
                REPO / "scripts/host/pin-minimal-headless-host-key.py"
            ),
            runtime_acceptance=(
                REPO
                / "scripts/host/run-minimal-headless-runtime-acceptance.sh"
            ),
            diagnostic_collector=(
                REPO / "scripts/host/collect-early-target-diagnostics.py"
            ),
            fallback=REPO / "scripts/host/fallback-acm-control.py",
            stock_fallback=STOCK_FALLBACK_PATH,
            key_admission=(
                REPO
                / "scripts/host/"
                "verify-headless-ssh-v2-key-admission.py"
            ),
            host_doctor=REPO / "scripts/host/rog5-host-doctor.py",
            deployment_receipt=(
                REPO / "scripts/host/power-usb-deployment-receipt.py"
            ),
            handoff_marker=Path("/run/rog5-network-root-nfs-ready"),
            network_service_state=Path(
                "/run/rog5-network-root-server.state"
            ),
            export_mount=Path("/run/rog5-network-root-export"),
            nfs_exports=Path("/var/lib/nfs/etab"),
            nfs_threads=Path("/proc/fs/nfsd/threads"),
            ip_nonlocal_bind=Path(
                "/proc/sys/net/ipv4/ip_nonlocal_bind"
            ),
            host_boot_id=Path("/proc/sys/kernel/random/boot_id"),
            sys_class_net=Path("/sys/class/net"),
            offline=False,
        )


@dataclass(frozen=True)
class AdmissionInputs:
    manifest_sha256: str
    ssh_key: Path
    root_package: Path
    candidate_record: Path
    bundle_manifest: Path


@dataclass(frozen=True)
class CycleProfile:
    candidate: str
    bundle: str
    bundle_profile: str
    target_id: str
    admission_profile: str
    recovery_profile: str
    runtime_profile: str
    build_profile: str
    diagnostic: bool
    early_probe: bool = False


STANDARD_CYCLE_PROFILE = CycleProfile(
    candidate=CANDIDATE,
    bundle=BUNDLE,
    bundle_profile="network-root-v1",
    target_id="headless-ssh-network-root",
    admission_profile="headless-ssh-r2",
    recovery_profile=RECOVERY_PROFILE,
    runtime_profile=RECOVERY_PROFILE,
    build_profile="headless-ssh-v2",
    diagnostic=False,
)
DIAGNOSTIC_CYCLE_PROFILE = CycleProfile(
    candidate=DIAGNOSTIC_CANDIDATE,
    bundle=DIAGNOSTIC_BUNDLE,
    bundle_profile=DIAGNOSTIC_PROFILE,
    target_id="headless-netroot-early-diag-v2",
    admission_profile=DIAGNOSTIC_ADMISSION_PROFILE,
    recovery_profile=DIAGNOSTIC_RECOVERY_PROFILE,
    runtime_profile=DIAGNOSTIC_PROFILE,
    build_profile="headless-ssh-v2",
    diagnostic=True,
)
LEGACY_DIAGNOSTIC_CYCLE_PROFILE = CycleProfile(
    candidate="headless-netroot-early-diag-v1",
    bundle="headless-netroot-early-diag-v1",
    bundle_profile=DIAGNOSTIC_PROFILE,
    target_id="headless-netroot-early-diag",
    admission_profile="early-target-diagnostic-v1",
    recovery_profile="headless-diagnostic-generation12-live-v1",
    runtime_profile=DIAGNOSTIC_PROFILE,
    build_profile="headless-ssh-v2",
    diagnostic=True,
)
CORE_CYCLE_PROFILE = CycleProfile(
    candidate="headless-core-network-root-v2",
    bundle="headless-core-network-root-v2-live-v1",
    bundle_profile="network-root-v1",
    target_id="headless-core-network-root",
    admission_profile="headless-core-live-v1",
    recovery_profile=CORE_RECOVERY_PROFILE,
    runtime_profile="headless-core-deployment-v1",
    build_profile="headless-core-v3",
    diagnostic=False,
)
POWER_USB_CYCLE_PROFILE = CycleProfile(
    candidate=POWER_USB.CANDIDATE,
    bundle=POWER_USB.BUNDLE,
    bundle_profile=POWER_USB.BUNDLE_PROFILE,
    target_id=POWER_USB.TARGET_ID,
    admission_profile=POWER_USB.ADMISSION_PROFILE,
    recovery_profile=POWER_USB_RECOVERY_PROFILE,
    runtime_profile=POWER_USB.RUNTIME_PROFILE,
    build_profile=POWER_USB.BUILD_PROFILE,
    diagnostic=POWER_USB.PROBE_PHASE == "early-initramfs",
    early_probe=POWER_USB.PROBE_PHASE == "early-initramfs",
)
STOCK_FALLBACK_RECOVERY_PROFILES = frozenset(
    {
        POWER_USB_RECOVERY_PROFILE,
        "persistent-root-power-usb-v8-generation84-live-v1",
        "persistent-root-local-image-any-prior-v13-generation106-live-v1",
        "persistent-root-local-image-any-prior-v14-generation107-live-v1",
        "persistent-root-local-image-restart2-v15-generation108-live-v1",
        "persistent-root-local-image-reboot-mode-v16-generation109-live-v1",
        "persistent-root-sparse-diagnostic-v17-generation110-live-v1",
        "local-image-stage-writer-v2-generation111-live-v1",
        "local-image-stage-hotplug-v3-generation112-live-v1",
        "local-image-stage-preusb-v4-generation113-live-v1",
        "local-image-stage-usbmode-v5-generation114-live-v1",
        "local-image-stage-configfs-v6-generation115-live-v1",
        "local-image-stage-udc-v7-generation116-live-v1",
        "local-image-stage-udc-stable-v8-generation117-live-v1",
        "local-image-stage-ncm-v9-generation118-live-v1",
        "local-image-stage-timing-v10-generation119-live-v1",
        "local-image-stage-address-v11-generation120-live-v1",
        "local-image-stage-prebind-v12-generation121-live-v1",
    }
)
POWER_USB_RECEIPT_RECOVERY_PROFILES = frozenset(
    {
        POWER_USB_RECOVERY_PROFILE,
        "persistent-root-power-usb-v8-generation84-live-v1",
    }
)


@dataclass(frozen=True)
class Inputs:
    manifest_sha256: str
    ssh_key: Path
    ssh_public_key_sha256: str
    root_package_sha256: str
    candidate_record: Path
    candidate_sha256: str
    fallback_known_hosts: Path
    evidence_dir: Path
    fallback_timeout: int
    host_doctor_receipt: Path | None = None
    host_doctor_receipt_sha256: str = ""
    deployment_receipt: Path | None = None
    deployment_receipt_sha256: str = ""


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[bytes]
    log: Path


@dataclass(frozen=True)
class Intent:
    session: str
    request: str
    outcome: str
    state: str


@dataclass(frozen=True)
class ProgressAssessment:
    capture_result: str
    correlation: str
    reason: str


@dataclass(frozen=True)
class HostSnapshot:
    firewall_forward: bool
    ip_nonlocal_bind: str


@dataclass(frozen=True)
class InterfaceSnapshot:
    name: str
    product: str
    addresses: tuple[str, ...]
    firewall_zone: str
    network_manager_managed: str


def fixed_executable(path: Path, *, offline: bool) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise CycleError(f"required executable is absent: {path}") from error
    if not stat.S_ISREG(metadata.st_mode) or not os.access(path, os.X_OK):
        fail(f"required executable is unsafe: {path}")
    try:
        in_repository = path.resolve(strict=True).is_relative_to(REPO)
    except OSError:
        in_repository = False
    if offline or in_repository:
        if metadata.st_uid != os.geteuid():
            fail(f"caller-controlled executable has the wrong owner: {path}")
        if stat.S_IMODE(metadata.st_mode) & 0o022:
            fail(f"caller-controlled executable is group/world writable: {path}")
    elif (
        metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o755
    ):
        fail(f"fixed host executable metadata is unsafe: {path}")


def caller_file(path_value: str, label: str) -> Path:
    if not path_value:
        fail(f"set {label}")
    supplied = Path(path_value)
    try:
        metadata = supplied.lstat()
        path = supplied.resolve(strict=True)
    except OSError as error:
        raise CycleError(f"{label} is unavailable") from error
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not path.is_file()
        or path.is_symlink()
        or path.stat().st_uid != os.geteuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o600
    ):
        fail(f"{label} must be a caller-owned mode-0600 regular file")
    return path


def caller_directory(path_value: str) -> Path:
    if not path_value:
        fail("set EVIDENCE_DIR")
    supplied = Path(path_value)
    try:
        metadata = supplied.lstat()
        path = supplied.resolve(strict=True)
    except OSError as error:
        raise CycleError("EVIDENCE_DIR is unavailable") from error
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not path.is_dir()
        or path.is_symlink()
        or path == Path("/")
        or path.stat().st_uid != os.geteuid()
        or stat.S_IMODE(path.stat().st_mode) != 0o700
    ):
        fail("EVIDENCE_DIR must be a caller-owned mode-0700 directory")
    return path


def caller_artifact(path_value: str, label: str) -> Path:
    if not path_value:
        fail(f"set {label}")
    supplied = Path(path_value)
    try:
        metadata = supplied.lstat()
        path = supplied.resolve(strict=True)
        resolved = path.lstat()
    except OSError as error:
        raise CycleError(f"{label} is unavailable") from error
    if (
        not supplied.is_absolute()
        or supplied != path
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISREG(resolved.st_mode)
        or resolved.st_uid != os.geteuid()
        or stat.S_IMODE(resolved.st_mode) not in {0o400, 0o444}
        or resolved.st_nlink != 1
    ):
        fail(f"{label} must be a canonical caller-owned read-only file")
    return path


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def caller_artifact_directory(path_value: str, label: str) -> Path:
    if not path_value:
        fail(f"set {label}")
    supplied = Path(path_value)
    try:
        metadata = supplied.lstat()
        path = supplied.resolve(strict=True)
        resolved = path.lstat()
    except OSError as error:
        raise CycleError(f"{label} is unavailable") from error
    if (
        not supplied.is_absolute()
        or supplied != path
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(resolved.st_mode)
        or resolved.st_uid != os.geteuid()
        or stat.S_IMODE(resolved.st_mode) != 0o700
    ):
        fail(f"{label} must be a canonical caller-owned mode-0700 directory")
    return path


def outside_repository(path: Path, label: str) -> None:
    try:
        path.relative_to(REPO)
    except ValueError:
        return
    fail(f"{label} must remain outside the repository")


def parse_admission_inputs(profile: CycleProfile) -> AdmissionInputs:
    manifest = os.environ.get("MANIFEST_SHA256", "")
    if not SHA256.fullmatch(manifest) or manifest == ZERO_SHA256:
        fail("MANIFEST_SHA256 must be one nonzero lowercase SHA-256")
    if manifest in CONSUMED_MANIFESTS:
        fail(
            "MANIFEST_SHA256 identifies a consumed live payload; build "
            "and pin a fresh successor instead of retrying it"
        )
    if os.environ.get("BUNDLE") != profile.bundle:
        fail(f"BUNDLE must be exactly {profile.bundle}")
    if (
        os.environ.get("ROG5_STABLE_RECOVERY_PROFILE")
        != profile.recovery_profile
    ):
        fail(
            "ROG5_STABLE_RECOVERY_PROFILE must select the exact lifecycle "
            "deployment profile"
        )
    ssh_key = caller_file(os.environ.get("SSH_KEY", ""), "SSH_KEY")
    root_package = caller_artifact(
        os.environ.get("HEADLESS_ROOT_PACKAGE", ""),
        "HEADLESS_ROOT_PACKAGE",
    )
    candidate_record = caller_artifact(
        os.environ.get("RECOVERY_CANDIDATE_RECORD", ""),
        "RECOVERY_CANDIDATE_RECORD",
    )
    bundle_root = caller_artifact_directory(
        os.environ.get("BUNDLE_ROOT", ""),
        "BUNDLE_ROOT",
    )
    bundle_manifest = caller_artifact(
        str(bundle_root / profile.bundle / "manifest"),
        "runtime bundle manifest",
    )
    outside_repository(ssh_key, "SSH_KEY")
    return AdmissionInputs(
        manifest_sha256=manifest,
        ssh_key=ssh_key,
        root_package=root_package,
        candidate_record=candidate_record,
        bundle_manifest=bundle_manifest,
    )


def parse_inputs(
    admission: AdmissionInputs,
    admitted: OrderedDict[str, str],
    profile: CycleProfile = STANDARD_CYCLE_PROFILE,
) -> Inputs:
    known_hosts = caller_file(
        os.environ.get("FALLBACK_KNOWN_HOSTS", ""),
        "FALLBACK_KNOWN_HOSTS",
    )
    evidence = caller_directory(os.environ.get("EVIDENCE_DIR", ""))
    for path, label in (
        (known_hosts, "FALLBACK_KNOWN_HOSTS"),
        (evidence, "EVIDENCE_DIR"),
    ):
        outside_repository(path, label)
    anchor_path = str(evidence / "recovery-usb.anchor")
    if (
        not ANCHOR_PATH.fullmatch(anchor_path)
        or anchor_path.endswith("/")
        or "//" in anchor_path
        or ".." in Path(anchor_path).parts
    ):
        fail("EVIDENCE_DIR cannot carry the privileged recovery anchor")
    timeout_value = os.environ.get(
        "ROG5_FALLBACK_TIMEOUT", str(POWER_USB.FALLBACK_TIMEOUT_SECONDS)
    )
    if (
        not timeout_value.isascii()
        or not timeout_value.isdecimal()
        or not 600 <= int(timeout_value) <= 900
    ):
        fail("ROG5_FALLBACK_TIMEOUT must be between 600 and 900 seconds")
    host_doctor_receipt = None
    deployment_receipt = None
    if profile == POWER_USB_CYCLE_PROFILE:
        host_doctor_receipt = caller_artifact(
            os.environ.get("ROG5_HOST_DOCTOR_RECEIPT", ""),
            "ROG5_HOST_DOCTOR_RECEIPT",
        )
        deployment_receipt = caller_artifact(
            os.environ.get("ROG5_POWER_USB_DEPLOYMENT_RECEIPT", ""),
            "ROG5_POWER_USB_DEPLOYMENT_RECEIPT",
        )
        outside_repository(host_doctor_receipt, "ROG5_HOST_DOCTOR_RECEIPT")
        outside_repository(
            deployment_receipt,
            "ROG5_POWER_USB_DEPLOYMENT_RECEIPT",
        )
    return Inputs(
        manifest_sha256=admission.manifest_sha256,
        ssh_key=admission.ssh_key,
        ssh_public_key_sha256=admitted["public_key_sha256"],
        root_package_sha256=admitted["package_sha256"],
        candidate_record=admission.candidate_record,
        candidate_sha256=admitted["candidate_sha256"],
        fallback_known_hosts=known_hosts,
        evidence_dir=evidence,
        fallback_timeout=int(timeout_value),
        host_doctor_receipt=host_doctor_receipt,
        host_doctor_receipt_sha256=(
            file_sha256(host_doctor_receipt) if host_doctor_receipt else ""
        ),
        deployment_receipt=deployment_receipt,
        deployment_receipt_sha256=(
            file_sha256(deployment_receipt) if deployment_receipt else ""
        ),
    )


def child_environment(**updates: str) -> dict[str, str]:
    environment = {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "LC_ALL": "C",
    }
    for name in PASSTHROUGH_ENVIRONMENT:
        if name in os.environ:
            environment[name] = os.environ[name]
    if os.environ.get("ROG5_LIVE_CYCLE_OFFLINE_TEST") == "1":
        for name, value in os.environ.items():
            if name.startswith("MOCK_"):
                environment[name] = value
    environment.update(updates)
    return environment


def run_capture(
    arguments: list[str],
    *,
    environment: dict[str, str] | None = None,
    timeout: float = 180,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    if environment is None:
        environment = child_environment()
    result = subprocess.run(
        arguments,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        final = next(
            (
                line
                for line in reversed(result.stdout.splitlines())
                if line.strip()
            ),
            "no diagnostic",
        )
        fail(f"command failed ({arguments[0]}): {final}")
    return result


def verify_repository_checkpoint(git: Path) -> None:
    status = run_capture(
        [
            str(git),
            "-C",
            str(REPO),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ]
    ).stdout
    if status:
        fail("repository must be clean before deployment-key admission")
    branch = run_capture(
        [
            str(git),
            "-C",
            str(REPO),
            "branch",
            "--show-current",
        ]
    ).stdout.strip()
    if not branch:
        fail("repository is not on a branch")
    upstream = run_capture(
        [
            str(git),
            "-C",
            str(REPO),
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{u}",
        ]
    ).stdout.strip()
    if upstream != f"origin/{branch}":
        fail("lifecycle branch does not track its exact origin peer")
    run_capture(
        [
            str(git),
            "-C",
            str(REPO),
            "fetch",
            "--no-tags",
            "--prune",
            "origin",
            f"refs/heads/{branch}:refs/remotes/origin/{branch}",
        ]
    )
    head = run_capture(
        [str(git), "-C", str(REPO), "rev-parse", "HEAD"]
    ).stdout.strip()
    remote = run_capture(
        [str(git), "-C", str(REPO), "rev-parse", upstream]
    ).stdout.strip()
    if not head or head != remote:
        fail("local and remote-tracking checkpoints differ")


def parse_key_admission_record(
    payload: str,
    expected_manifest_sha256: str,
    profile: CycleProfile = STANDARD_CYCLE_PROFILE,
) -> OrderedDict[str, str]:
    if not payload.endswith("\n"):
        fail("deployment-key admission output is not canonical")
    lines = payload.splitlines()
    if len(lines) != len(KEY_ADMISSION_FIELDS):
        fail("deployment-key admission field count changed")
    values: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(KEY_ADMISSION_FIELDS, lines, strict=True):
        name, separator, value = line.partition("=")
        if (
            separator != "="
            or name != expected
            or not value
            or name in values
        ):
            fail("deployment-key admission field changed")
        values[name] = value
    if (
        values["format"] != "rog5-headless-ssh-v2-key-admission-v1"
        or values["candidate"] != profile.candidate
        or values["bundle"] != profile.bundle
        or values["profile"] != profile.bundle_profile
        or values["build_profile"] != profile.build_profile
        or values["target_id"] != profile.target_id
        or values["manifest_sha256"] != expected_manifest_sha256
        or values["authority"] != "none"
        or not SSH_FINGERPRINT.fullmatch(
            values["authorized_key_fingerprint"]
        )
    ):
        fail("deployment-key admission identity changed")
    for name in (
        "public_key_sha256",
        "package_sha256",
        "candidate_sha256",
        "manifest_sha256",
        "root_tree_sha256",
        "root_seal_sha256",
    ):
        if not SHA256.fullmatch(values[name]) or values[name] == ZERO_SHA256:
            fail("deployment-key admission hash is invalid")
    entries = values["root_tree_entries"]
    if (
        not entries.isascii()
        or not entries.isdecimal()
        or entries.startswith("0")
    ):
        fail("deployment-key admission entry count is invalid")
    return values


def verify_key_admission(
    dependencies: Dependencies,
    inputs: AdmissionInputs,
    profile: CycleProfile = STANDARD_CYCLE_PROFILE,
) -> OrderedDict[str, str]:
    fixed_executable(
        dependencies.key_admission,
        offline=dependencies.offline,
    )
    result = run_capture(
        [
            str(dependencies.key_admission),
            "--private-key",
            str(inputs.ssh_key),
            "--package",
            str(inputs.root_package),
            "--candidate",
            str(inputs.candidate_record),
            "--manifest",
            str(inputs.bundle_manifest),
            "--manifest-sha256",
            inputs.manifest_sha256,
            "--admission-profile",
            profile.admission_profile,
        ],
        environment={
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "LC_ALL": "C",
        },
        timeout=30,
    )
    return parse_key_admission_record(
        result.stdout,
        inputs.manifest_sha256,
        profile,
    )


def open_exclusive(path: Path) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    os.fchmod(descriptor, 0o600)
    return descriptor


def run_logged(
    arguments: list[str],
    log: Path,
    *,
    environment: dict[str, str] | None = None,
    timeout: float = 180,
) -> None:
    if environment is None:
        environment = child_environment()
    descriptor = open_exclusive(log)
    try:
        result = subprocess.run(
            arguments,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=descriptor,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if result.returncode != 0:
        fail(f"{log.stem} failed; inspect private log {log}")


def start_logged(
    name: str,
    arguments: list[str],
    log: Path,
    *,
    environment: dict[str, str] | None = None,
) -> ManagedProcess:
    if environment is None:
        environment = child_environment()
    descriptor = open_exclusive(log)
    try:
        process = subprocess.Popen(
            arguments,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=descriptor,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        os.close(descriptor)
    return ManagedProcess(name=name, process=process, log=log)


def terminate(managed: ManagedProcess | None) -> None:
    if managed is None or managed.process.poll() is not None:
        return
    try:
        os.killpg(managed.process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        managed.process.terminate()
    try:
        managed.process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(managed.process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        managed.process.kill()
    managed.process.wait(timeout=10)


def cancel_network_process(
    managed: ManagedProcess | None,
    dependencies: Dependencies,
    handoff_token: str | None,
) -> str:
    if managed is None or managed.process.poll() is not None:
        return ""
    if (
        handoff_token is None
        or not SHA256.fullmatch(handoff_token)
        or handoff_token == ZERO_SHA256
    ):
        return "cannot authenticate network-root service cancellation"
    try:
        result = run_capture(
            [
                str(dependencies.network_root_server),
                "cancel",
                handoff_token,
            ],
            environment=child_environment(
                ALLOW_HEADLESS_NETWORK_ROOT_CANCEL="1"
            ),
            timeout=45,
            check=False,
        )
    # Cancellation runs inside rollback. Defer even an interrupt until the
    # fallback and durable-intent paths have had a chance to finish.
    except BaseException as error:
        return f"privileged network-root cancellation failed: {error}"
    if result.returncode != 0:
        if managed.process.poll() is not None:
            return ""
        final = next(
            (
                line
                for line in reversed(result.stdout.splitlines())
                if line.strip()
            ),
            "no diagnostic",
        )
        return f"privileged network-root cancellation failed: {final}"
    try:
        managed.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        return "cancelled network-root server did not exit"
    return ""


def wait_process(managed: ManagedProcess, timeout: float) -> int:
    try:
        return managed.process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        terminate(managed)
        raise CycleError(
            f"{managed.name} exceeded its bounded runtime; inspect "
            f"{managed.log}"
        ) from error


def wait_network_process(
    managed: ManagedProcess,
    dependencies: Dependencies,
    handoff_token: str,
    timeout: float,
) -> int:
    try:
        return managed.process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        cancellation = cancel_network_process(
            managed,
            dependencies,
            handoff_token,
        )
        if cancellation:
            cancellation = f"; {cancellation}"
        raise CycleError(
            f"{managed.name} exceeded its bounded runtime; inspect "
            f"{managed.log}{cancellation}"
        ) from error


def wait_log_marker(
    managed: ManagedProcess,
    marker: str,
    *,
    timeout: float,
    poll: float,
    exact_line: bool = False,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = managed.log.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            payload = ""
        if exact_line:
            marker_count = payload.splitlines(keepends=True).count(
                f"{marker}\n"
            )
            if marker_count > 1:
                fail(f"{managed.name} published duplicate ready markers")
            found = marker_count == 1
        else:
            found = marker in payload
        if found:
            return
        status = managed.process.poll()
        if status is not None:
            fail(
                f"{managed.name} exited with status {status} before its "
                f"ready marker; inspect {managed.log}"
            )
        time.sleep(poll)
    fail(f"{managed.name} did not publish its bounded ready marker")


def require_exact_log_line(path: Path, marker: str) -> None:
    try:
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CycleError(f"cannot read private process log: {path}") from error
    if payload.splitlines(keepends=True).count(f"{marker}\n") != 1:
        fail(f"{path.name} lacks one exact newline-terminated marker")


def require_log_markers(path: Path, markers: tuple[str, ...]) -> None:
    try:
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CycleError(f"cannot read private process log: {path}") from error
    for marker in markers:
        if payload.count(marker) != 1:
            fail(f"{path.name} lacks one exact lifecycle marker")


def canonical_json(line: str) -> dict[str, object]:
    def unique(pairs):
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                fail("recovery-control JSON has a duplicate field")
            result[key] = value
        return result

    value = json.loads(line, object_pairs_hook=unique)
    if not isinstance(value, dict):
        fail("recovery-control output is not a JSON object")
    return value


def validate_intent(
    value: dict[str, object],
    *,
    manifest_sha256: str,
    target: str = BUNDLE,
) -> Intent:
    session = value.get("session")
    request = value.get("request")
    if (
        not isinstance(session, str)
        or not HEX_ID.fullmatch(session)
        or not isinstance(request, str)
        or not HEX_ID.fullmatch(request)
        or value.get("manifest_sha256") != manifest_sha256
        or value.get("target") != target
        or value.get("state") != "TRANSMITTED"
        or value.get("outcome") != "UNKNOWN"
    ):
        fail("host intent record does not bind the exact committed target")
    return Intent(
        session=session,
        request=request,
        state="TRANSMITTED",
        outcome="UNKNOWN",
    )


def observe_prepared_identity(
    path: Path,
    manifest_sha256: str,
    target: str,
) -> tuple[str, str] | None:
    """Observe PREPARED only to stop the non-authoritative progress tail."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            payload = os.read(descriptor, 8193)
        finally:
            os.close(descriptor)
        first, separator, _remaining = payload.partition(b"\n")
        if not separator or len(first) > 8192:
            return None
        value = canonical_json(first.decode("ascii"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, CycleError):
        return None
    session = value.get("session")
    request = value.get("request")
    if (
        not valid_prepared_response(value, manifest_sha256, target)
        or not isinstance(session, str)
        or not isinstance(request, str)
    ):
        return None
    return session, request


def inspect_progress_capture(
    path: Path,
    *,
    bundle: str,
    manifest_sha256: str,
    session: str,
    prepare_request: str,
) -> ProgressAssessment:
    """Classify caller-owned progress evidence without granting authority."""
    invalid = ProgressAssessment("INVALID", "UNAVAILABLE", "INVALID_RECORD")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            payload = os.read(descriptor, 8193)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        named = path.lstat()
    except OSError:
        return ProgressAssessment("MISSING", "UNAVAILABLE", "MISSING")

    def identity(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_uid,
            value.st_gid,
            stat.S_IFMT(value.st_mode),
            stat.S_IMODE(value.st_mode),
            value.st_nlink,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )

    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.geteuid()
        or before.st_gid != os.getegid()
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
        or not 1 <= before.st_size <= 8192
        or len(payload) != before.st_size
        or identity(before) != identity(after)
        or identity(before) != identity(named)
        or not payload.endswith(b"\n")
        or b"\r" in payload
        or b"\0" in payload
    ):
        return invalid
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError:
        return invalid
    fields = (
        "format",
        "session",
        "request",
        "bundle",
        "manifest_sha256",
        "records",
        "phases",
        "wire_bytes",
        "wire_sha256",
        "result",
        "truncated",
        "reason",
        "authority",
    )
    if len(lines) != len(fields):
        return invalid
    values: dict[str, str] = {}
    for expected, line in zip(fields, lines, strict=True):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or not value:
            return invalid
        values[name] = value
    if (
        values["format"] != "rog5-recovery-progress-capture-v1"
        or not HEX_ID.fullmatch(values["session"])
        or not HEX_ID.fullmatch(values["request"])
        or not values["records"].isascii()
        or not values["records"].isdecimal()
        or len(values["records"]) > 1
        or not values["wire_bytes"].isascii()
        or not values["wire_bytes"].isdecimal()
        or len(values["wire_bytes"]) > 4
        or not 0 <= int(values["wire_bytes"]) <= 8192
        or not SHA256.fullmatch(values["wire_sha256"])
        or not SHA256.fullmatch(values["manifest_sha256"])
        or values["result"] not in {"COMPLETE", "PARTIAL"}
        or values["truncated"] not in {"YES", "NO"}
        or values["authority"] != "NONE"
        or not re.fullmatch(r"[A-Z_]{2,32}", values["reason"])
    ):
        return invalid
    phases = () if values["phases"] == "none" else tuple(
        values["phases"].split(">")
    )
    records = int(values["records"])
    wire_bytes = int(values["wire_bytes"])
    if (
        records != len(phases)
        or phases != PROGRESS_PHASES[:records]
        or records > len(PROGRESS_PHASES)
        or (wire_bytes == 0 and values["wire_sha256"] != EMPTY_SHA256)
        or (wire_bytes > 0 and values["wire_sha256"] == EMPTY_SHA256)
        or (records > 0 and wire_bytes == 0)
        or (
            records > 0
            and (
                values["session"] == ZERO_ID
                or values["request"] == ZERO_ID
            )
        )
        or (
            values["result"] == "COMPLETE"
            and (
                phases != PROGRESS_PHASES
                or values["truncated"] != "NO"
                or values["reason"] != "CLEAN_EOF"
            )
        )
        or (
            values["result"] == "PARTIAL"
            and values["truncated"] != "YES"
        )
    ):
        return invalid
    identity_matches = (
        values["bundle"] == bundle
        and values["manifest_sha256"] == manifest_sha256
        and values["session"] == session
        and values["request"] == prepare_request
    )
    identity_unavailable = (
        values["result"] == "PARTIAL"
        and values["session"] == ZERO_ID
        and values["request"] == ZERO_ID
        and values["bundle"] == bundle
        and values["manifest_sha256"] == manifest_sha256
    )
    correlation = (
        "MATCH"
        if identity_matches
        else "UNAVAILABLE"
        if identity_unavailable
        else "MISMATCH"
    )
    return ProgressAssessment(
        values["result"],
        correlation,
        values["reason"],
    )


def postmortem_tuple(value: dict[str, object]) -> tuple[object, ...]:
    return tuple(
        value.get(name)
        for name in (
            "postmortem_state",
            "postmortem_records",
            "postmortem_bytes",
            "postmortem_sha256",
            "postmortem_tail_hex",
            "postmortem_lineage_state",
            "postmortem_lineage_matches",
            "postmortem_lineage_sha256",
        )
    )


def valid_postmortem(value: dict[str, object]) -> bool:
    (
        state,
        records,
        byte_count,
        digest,
        tail,
        lineage_state,
        lineage_matches,
        lineage_digest,
    ) = postmortem_tuple(value)
    if (
        not isinstance(state, str)
        or not isinstance(records, str)
        or not isinstance(byte_count, str)
        or not isinstance(digest, str)
        or not isinstance(tail, str)
        or not isinstance(lineage_state, str)
        or not isinstance(lineage_matches, str)
        or not isinstance(lineage_digest, str)
        or state not in {"PRESENT", "EMPTY", "UNAVAILABLE"}
        or not records.isdecimal()
        or (len(records) > 1 and records.startswith("0"))
        or len(records) > 2
        or int(records) > 64
        or not byte_count.isdecimal()
        or (len(byte_count) > 1 and byte_count.startswith("0"))
        or len(byte_count) > 7
        or int(byte_count) > 4194304
        or not SHA256.fullmatch(digest)
        or (tail != "none" and not POSTMORTEM_TAIL_HEX.fullmatch(tail))
        or lineage_state not in {"NONE", "UNIQUE", "REPEATED", "AMBIGUOUS"}
        or not lineage_matches.isdecimal()
        or (len(lineage_matches) > 1 and lineage_matches.startswith("0"))
        or len(lineage_matches) > 5
        or int(lineage_matches) > 65535
        or not SHA256.fullmatch(lineage_digest)
    ):
        return False
    if lineage_state == "NONE" and (
        lineage_matches != "0" or lineage_digest != ZERO_SHA256
    ):
        return False
    if lineage_state == "UNIQUE" and (
        lineage_matches != "1" or lineage_digest == ZERO_SHA256
    ):
        return False
    if lineage_state == "REPEATED" and (
        int(lineage_matches) < 2 or lineage_digest == ZERO_SHA256
    ):
        return False
    if lineage_state == "AMBIGUOUS" and lineage_digest != ZERO_SHA256:
        return False
    if state == "PRESENT":
        return (
            records != "0"
            and byte_count != "0"
            and digest not in {ZERO_SHA256, EMPTY_SHA256}
            and tail != "none"
        )
    if state == "EMPTY":
        return (
            records == "0"
            and byte_count == "0"
            and digest == EMPTY_SHA256
            and tail == "none"
            and lineage_state == "NONE"
            and lineage_matches == "0"
            and lineage_digest == ZERO_SHA256
        )
    return (
        records == "0"
        and byte_count == "0"
        and digest == ZERO_SHA256
        and tail == "none"
        and lineage_state == "NONE"
        and lineage_matches == "0"
        and lineage_digest == ZERO_SHA256
    )


def valid_prepared_response(
    prepared: dict[str, object],
    manifest_sha256: str,
    target: str,
) -> bool:
    session = prepared.get("session")
    request = prepared.get("request")
    return (
        set(prepared) == CONTROL_RESPONSE_FIELDS
        and isinstance(session, str)
        and bool(HEX_ID.fullmatch(session))
        and session != ZERO_ID
        and isinstance(request, str)
        and bool(HEX_ID.fullmatch(request))
        and request != ZERO_ID
        and prepared.get("verb") == "PREPARE"
        and prepared.get("result") == "PREPARED"
        and prepared.get("state") == "PREPARED"
        and prepared.get("prepared_bundle") == target
        and prepared.get("manifest_sha256") == manifest_sha256
        and prepared.get("prepare_request") == request
        and prepared.get("commit_request") == ZERO_ID
        and prepared.get("commit_fingerprint") == ZERO_SHA256
        and prepared.get("execution_started") == "NO"
        and prepared.get("watchdog") == "ARMED"
        and prepared.get("last_error") == "NONE"
        and valid_postmortem(prepared)
    )


def valid_committed_response(
    committed: dict[str, object],
    manifest_sha256: str,
    target: str,
    prepare_request: str,
) -> bool:
    session = committed.get("session")
    request = committed.get("request")
    fingerprint = committed.get("commit_fingerprint")
    return (
        set(committed) == CONTROL_RESPONSE_FIELDS
        and isinstance(session, str)
        and bool(HEX_ID.fullmatch(session))
        and session != ZERO_ID
        and isinstance(request, str)
        and bool(HEX_ID.fullmatch(request))
        and request != ZERO_ID
        and request != prepare_request
        and committed.get("verb") == "COMMIT_EXEC"
        and committed.get("result") == "CLAIMED"
        and committed.get("state") == "CLAIMED"
        and committed.get("prepared_bundle") == target
        and committed.get("manifest_sha256") == manifest_sha256
        and committed.get("prepare_request") == prepare_request
        and committed.get("commit_request") == request
        and isinstance(fingerprint, str)
        and fingerprint
        == commit_request_fingerprint(
            session,
            request,
            prepare_request,
            manifest_sha256,
        )
        and committed.get("watchdog") == "ARMED"
        and committed.get("execution_started") == "NO"
        and committed.get("last_error") == "NONE"
        and valid_postmortem(committed)
    )


def commit_request_fingerprint(
    session: str,
    request: str,
    prepare_request: str,
    manifest_sha256: str,
) -> str:
    body = (
        f"prepare_request={prepare_request}\n"
        f"manifest_sha256={manifest_sha256}\n"
    ).encode("ascii")
    wire = (
        "version=1\n"
        "kind=request\n"
        f"session={session}\n"
        f"request={request}\n"
        "verb=COMMIT_EXEC\n"
        f"body_sha256={hashlib.sha256(body).hexdigest()}\n"
    ).encode("ascii") + body
    return hashlib.sha256(wire).hexdigest()


def parse_control_log(
    path: Path,
    manifest_sha256: str,
    target: str = BUNDLE,
) -> tuple[Intent, str]:
    try:
        lines = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeDecodeError) as error:
        raise CycleError("recovery-control log is unreadable") from error
    if len(lines) != 4 or lines[3] != (
        "PASS recovery accepted one commit; outcome remains UNKNOWN"
    ):
        fail("recovery-control output is not one complete transaction")
    prepared, committed, intent_value = map(canonical_json, lines[:3])
    prepared_request = prepared.get("request")
    if not valid_prepared_response(prepared, manifest_sha256, target):
        fail("recovery PREPARE evidence is inconsistent")
    if not isinstance(prepared_request, str):
        fail("recovery PREPARE evidence is inconsistent")
    if not valid_committed_response(
        committed,
        manifest_sha256,
        target,
        prepared_request,
    ):
        fail("recovery COMMIT evidence is inconsistent")
    # The native responder loads /run/rog5-postmortem.status exactly once
    # before its request loop. Same-session PREPARE replay is mandatory, so
    # both accepted responses must carry that immutable in-process snapshot.
    if postmortem_tuple(prepared) != postmortem_tuple(committed):
        fail("recovery COMMIT evidence is inconsistent")
    intent = validate_intent(
        intent_value,
        manifest_sha256=manifest_sha256,
        target=target,
    )
    if (
        prepared.get("session") != intent.session
        or committed.get("session") != intent.session
        or committed.get("request") != intent.request
        or committed.get("commit_request") != intent.request
    ):
        fail("recovery transaction and host intent do not correlate")
    return intent, prepared_request


def parse_any_intent(
    path: Path,
    manifest_sha256: str,
    target: str = BUNDLE,
) -> Intent | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in lines:
        try:
            value = canonical_json(line)
            if {
                "session",
                "request",
                "manifest_sha256",
                "target",
                "state",
                "outcome",
            }.issubset(value):
                return validate_intent(
                    value,
                    manifest_sha256=manifest_sha256,
                    target=target,
                )
        except (CycleError, json.JSONDecodeError):
            continue
    return None


def parse_record(path: Path) -> dict[str, str]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    values: dict[str, str] = {}
    try:
        descriptor = os.open(path, flags)
        try:
            before = os.fstat(descriptor)
            payload = bytearray()
            while len(payload) <= 65536:
                block = os.read(descriptor, 65537 - len(payload))
                if not block:
                    break
                payload.extend(block)
            after = os.fstat(descriptor)
            named = path.lstat()
        finally:
            os.close(descriptor)
    except OSError as error:
        raise CycleError(f"cannot read private record: {path}") from error
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_uid,
        item.st_gid,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.geteuid()
        or before.st_nlink != 1
        or not 1 <= len(payload) <= 65536
        or before.st_size != len(payload)
        or identity(after) != identity(before)
        or identity(named) != identity(before)
        or not payload.endswith(b"\n")
        or b"\r" in payload
        or b"\0" in payload
    ):
        fail(f"private record metadata or encoding is unsafe: {path}")
    try:
        lines = bytes(payload).decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise CycleError(f"cannot read private record: {path}") from error
    for line in lines:
        if "=" not in line:
            fail(f"private record is not canonical: {path}")
        name, value = line.split("=", 1)
        if (
            not re.fullmatch(r"[a-z0-9_]{1,64}", name)
            or not value
            or name in values
        ):
            fail(f"private record has a duplicate field: {path}")
        values[name] = value
    if bytes(payload) != "".join(
        f"{name}={value}\n" for name, value in values.items()
    ).encode("ascii"):
        fail(f"private record is not canonical: {path}")
    return values


def verify_fallback_postmortem_evidence(
    path: Path,
    anchor_path: Path,
    expected_candidate: str,
    expected_target_boot_id: str,
    dependencies: Dependencies,
) -> str:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise CycleError(
            "fallback postmortem evidence is unavailable"
        ) from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or not 1 <= metadata.st_size <= 8192
    ):
        fail("fallback postmortem evidence metadata is unsafe")
    values = parse_record(path)
    if tuple(values) != FALLBACK_POSTMORTEM_FIELDS:
        fail("fallback postmortem evidence fields changed")

    location = read_recovery_anchor_location(anchor_path, dependencies)
    fallback_boot_id = values["fallback_boot_id"]
    if fallback_boot_id == expected_target_boot_id:
        fail("fallback retained the minimal-headless boot identity")
    if (
        values["format"] != "rog5-fallback-postmortem-evidence-v2"
        or values["expected_candidate"] != expected_candidate
        or values["expected_boot_id"] != expected_target_boot_id
        or not BOOT_ID.fullmatch(expected_target_boot_id)
        or not BOOT_ID.fullmatch(fallback_boot_id)
        or values["usb_location"] != location
        or not HEX_ID.fullmatch(values["nonce"])
        or not SHA256.fullmatch(values["pmic_pon_sha256"])
        or any(
            not SHA256.fullmatch(values[name])
            or values[name] == ZERO_SHA256
            for name in (
                "record_sha256",
                "signature_sha256",
                "host_pin_sha256",
            )
        )
        or values["result"] != "PASS"
    ):
        fail("fallback postmortem evidence identity is not exact")

    numeric_limits = {
        "pstore_records": 64,
        "pstore_bytes": 4 * 1024 * 1024,
        "pmic_pon_records": 64,
        "pmic_cycle_entries": 29,
        "lineage_matches": 1_000_000,
        "lineage_records": 64,
        "fatal_tokens_total": 1_000_000,
        "fatal_after_lineage": 1_000_000,
    }
    numbers: dict[str, int] = {}
    for name, maximum in numeric_limits.items():
        value = values[name]
        if (
            not value.isascii()
            or not value.isdecimal()
            or len(value) > 1
            and value.startswith("0")
            or not 0 <= int(value) <= maximum
        ):
            fail("fallback postmortem evidence count is invalid")
        numbers[name] = int(value)

    state = values["pstore_state"]
    digest = values["pstore_sha256"]
    records = numbers["pstore_records"]
    byte_count = numbers["pstore_bytes"]
    matches = numbers["lineage_matches"]
    lineage_records = numbers["lineage_records"]
    fatal_total = numbers["fatal_tokens_total"]
    fatal = numbers["fatal_after_lineage"]
    if state == "UNAVAILABLE":
        consistent = records == byte_count == 0 and digest == ZERO_SHA256
        correlation = "UNAVAILABLE"
    elif state == "EMPTY":
        consistent = records == byte_count == 0 and digest == EMPTY_SHA256
        correlation = "NO_RECORDS"
    elif state == "PRESENT":
        consistent = (
            1 <= records <= 64
            and 0 <= byte_count <= 4 * 1024 * 1024
            and SHA256.fullmatch(digest) is not None
            and digest not in {ZERO_SHA256, EMPTY_SHA256}
        )
        if matches == 0:
            correlation = "NO_LINEAGE"
        elif matches == 1 and lineage_records == 1:
            correlation = "MATCH"
        elif matches == lineage_records and lineage_records > 1:
            correlation = "MATCH_MULTIPLE"
        else:
            correlation = "AMBIGUOUS"
    else:
        consistent = False
        correlation = "INVALID"
    if (
        not consistent
        or lineage_records > records
        or lineage_records > matches
        or (matches == 0 and (lineage_records != 0 or fatal != 0))
        or (matches > 0 and lineage_records == 0)
        or fatal > fatal_total
        or (state != "PRESENT" and fatal_total != 0)
        or values["correlation"] != correlation
    ):
        fail("fallback postmortem evidence state is inconsistent")
    fatal_state = (
        "FATAL_TOKEN_AFTER_LINEAGE"
        if correlation in {"MATCH", "MATCH_MULTIPLE"} and fatal > 0
        else "FATAL_TOKEN_PRESENT_ORDER_UNKNOWN"
        if correlation in {"MATCH", "MATCH_MULTIPLE"} and fatal_total > 0
        else "NO_FATAL_TOKEN_OBSERVED"
        if correlation in {"MATCH", "MATCH_MULTIPLE"}
        else "UNCORRELATED"
    )
    if values["fatal_state"] != fatal_state:
        fail("fallback postmortem fatal classification is inconsistent")
    pmic_state = values["pmic_pon_state"]
    pmic_records = numbers["pmic_pon_records"]
    pmic_digest = values["pmic_pon_sha256"]
    pmic_cycle_entries = numbers["pmic_cycle_entries"]
    pmic_trigger = values["pmic_reset_trigger"]
    pmic_type = values["pmic_reset_type"]
    pmic_watchdog = values["pmic_watchdog_signal"]
    reset_triggers = {
        "KPDPWR_N_S2",
        "RESIN_N_S2",
        "KPDPWR_N_AND_RESIN_N_S2",
        "PMIC_WATCHDOG_S2",
        "PS_HOLD",
        "SW_RESET",
        "RESIN_N_DEBOUNCE",
        "KPDPWR_N_DEBOUNCE",
        "PMIC_SID2_BCL_ALARM",
        "PMIC_SID3_BCL_ALARM",
        "PMIC_SID1_OCP",
        "PMIC_SID2_OCP",
        "PMIC_SID4_OCP",
        "PMIC_SID5_OCP",
    }
    if pmic_state == "UNAVAILABLE":
        pmic_consistent = (
            pmic_records == pmic_cycle_entries == 0
            and pmic_digest == ZERO_SHA256
            and pmic_trigger == pmic_type == "NONE"
            and pmic_watchdog == "INCONCLUSIVE"
        )
    elif pmic_state == "INCONCLUSIVE":
        pmic_consistent = (
            pmic_cycle_entries == 0
            and (
                pmic_records == 0
                and pmic_digest == EMPTY_SHA256
                or 1 <= pmic_records <= 64
                and pmic_digest not in {ZERO_SHA256, EMPTY_SHA256}
            )
            and pmic_trigger == pmic_type == "NONE"
            and pmic_watchdog == "INCONCLUSIVE"
        )
    elif pmic_state == "EXACT":
        pmic_consistent = (
            3 <= pmic_cycle_entries <= pmic_records <= 29
            and pmic_digest not in {ZERO_SHA256, EMPTY_SHA256}
            and pmic_trigger in reset_triggers
            and pmic_type in {"WARM_RESET", "SHUTDOWN", "HARD_RESET"}
            and pmic_watchdog in {"PRESENT", "ABSENT"}
            and not (
                pmic_trigger == "PMIC_WATCHDOG_S2"
                and pmic_watchdog != "PRESENT"
            )
        )
    else:
        pmic_consistent = False
    if not pmic_consistent:
        fail("fallback PMIC PON evidence is inconsistent")
    return fallback_boot_id


def verify_stock_fallback_evidence(
    path: Path,
    location: str,
    target_boot_id: str | None,
) -> str:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        fail("stock fallback identity record metadata is unsafe")
    values = parse_record(path)
    if tuple(values) != STOCK_FALLBACK_FIELDS:
        fail("stock fallback identity record fields changed")
    common_invalid = (
        values["format"] != "rog5-stock-android-fallback-v1"
        or values["serial"] != "M5AIKN00F0353YH"
        or values["usb_location"] != location
        or values["result"] != "PASS"
    )
    authorized_invalid = (
        values["evidence_mode"] != "adb-authorized"
        or values["product"] != "WW_I005D"
        or values["model"] != "ASUS_I005DA"
        or values["device"] != "ASUS_I005_1"
        or values["slot_suffix"] != "_a"
        or values["fingerprint"]
        != (
            "asus/WW_I005D/ASUS_I005_1:13/TKQ1.220807.001/"
            "33.0210.0210.200-0:user/release-keys"
        )
        or values["vbmeta_digest"]
        != "48cc851a31e80492d60b3d1895e6be8605f4ef5d9d7c940c8582215fd80ac005"
        or values["verified_boot_state"] != "orange"
        or not BOOT_ID.fullmatch(values["boot_id"])
        or values["boot_completed"] != "1"
        or values["usb_config"] != "adb"
    )
    unavailable = (
        values["product"],
        values["model"],
        values["device"],
        values["fingerprint"],
        values["vbmeta_digest"],
        values["verified_boot_state"],
        values["boot_id"],
        values["boot_completed"],
    )
    unauthorized_invalid = (
        values["evidence_mode"] != "usb-unauthorized-slot-a"
        or unavailable != ("unavailable",) * len(unavailable)
        or values["slot_suffix"] != "_a"
        or values["usb_config"] != "adb-unauthorized"
    )
    fastboot_invalid = (
        values["evidence_mode"] != "fastboot-slot-a"
        or unavailable != ("unavailable",) * len(unavailable)
        or values["slot_suffix"] != "_a"
        or values["usb_config"] != "fastboot"
    )
    if common_invalid or (
        authorized_invalid
        if values["evidence_mode"] == "adb-authorized"
        else fastboot_invalid
        if values["evidence_mode"] == "fastboot-slot-a"
        else unauthorized_invalid
    ):
        fail("stock fallback identity record is not exact")
    if (
        target_boot_id is not None
        and values["boot_id"] != "unavailable"
        and values["boot_id"] == target_boot_id
    ):
        fail("stock fallback retained the minimal-headless boot identity")
    return values["boot_id"]


def read_recovery_anchor_location(
    path: Path,
    dependencies: Dependencies,
) -> str:
    try:
        parent = path.parent.lstat()
    except OSError as error:
        raise CycleError("recovery USB anchor parent is unavailable") from error
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.geteuid()
        or stat.S_IMODE(parent.st_mode) != 0o700
    ):
        fail("recovery USB anchor parent is unsafe")
    try:
        path.resolve(strict=False).relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("recovery USB anchor must remain outside the repository")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CycleError("recovery USB anchor is unavailable") from error
    try:
        opened = os.fstat(descriptor)
        payload = os.read(descriptor, 4097)
        after = os.fstat(descriptor)
        named = path.lstat()
    except OSError as error:
        raise CycleError("cannot inspect recovery USB anchor") from error
    finally:
        os.close(descriptor)
    stat_identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_uid,
        value.st_gid,
        stat.S_IFMT(value.st_mode),
    )
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.geteuid()
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
        or not 1 <= len(payload) <= 4096
        or stat_identity(after) != stat_identity(opened)
        or stat_identity(named) != stat_identity(opened)
    ):
        fail("recovery USB anchor metadata or identity is unsafe")
    if not payload.endswith(b"\n") or b"\r" in payload or b"\0" in payload:
        fail("recovery USB anchor encoding is not canonical")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise CycleError("recovery USB anchor is not ASCII") from error
    if len(lines) != len(ANCHOR_FIELDS):
        fail("recovery USB anchor field count changed")
    values: dict[str, str] = {}
    for expected, line in zip(ANCHOR_FIELDS, lines, strict=True):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or not value:
            fail("recovery USB anchor is not canonical")
        values[name] = value
    try:
        host_boot_id = dependencies.host_boot_id.read_text(
            encoding="ascii"
        ).strip()
    except (OSError, UnicodeDecodeError) as error:
        raise CycleError("cannot read the host boot identity") from error
    created = values["created_unix"]
    now = int(time.time())
    location = values["usb_location"]
    if (
        not BOOT_ID.fullmatch(host_boot_id)
        or values["format"] != "rog5-minimal-headless-usb-anchor-v1"
        or values["host_boot_id"] != host_boot_id
        or values["recovery_vendor"] != "1d6b"
        or values["recovery_product_id"] != "0104"
        or values["recovery_product"] != "ROG5 recovery"
        or not created.isascii()
        or not created.isdecimal()
        or created.startswith("0")
        or int(created) > now + 5
        or now - int(created) > FALLBACK_CONTACT_START_BUDGET_SECONDS
        or not USB_LOCATION.fullmatch(location)
        or location.startswith("/")
        or location.endswith("/")
        or "//" in location
        or ".." in Path(location).parts
    ):
        fail("recovery USB anchor identity or freshness is invalid")
    return location


def verify_diagnostic_evidence(
    path: Path,
    anchor_path: Path,
    expected_candidate: str,
    *,
    require_ssh: bool = True,
    require_power: bool = False,
) -> str:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or not 1 <= before.st_size <= 2 * 1024 * 1024
        ):
            fail("diagnostic evidence metadata is unsafe")
        payload = bytearray()
        while len(payload) <= 2 * 1024 * 1024:
            block = os.read(
                descriptor,
                min(65536, 2 * 1024 * 1024 + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        named = path.lstat()
        identity = lambda value: (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_uid,
            value.st_gid,
            value.st_nlink,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        if (
            len(payload) != before.st_size
            or identity(before) != identity(after)
            or identity(before) != identity(named)
        ):
            fail("diagnostic evidence changed while being read")
    finally:
        os.close(descriptor)
    if (
        not payload.endswith(b"\n")
        or payload.count(b"\n") != 1
        or b"\r" in payload
        or b"\0" in payload
    ):
        fail("diagnostic evidence encoding is not canonical")
    try:
        line = payload[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise CycleError("diagnostic evidence is not ASCII") from error
    value = canonical_json(line)
    canonical = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        + b"\n"
    )
    if canonical != payload:
        fail("diagnostic evidence JSON is not canonical")
    expected_keys = {
        "candidate",
        "capture_status",
        "dropped_transport_snapshots",
        "dropped_usb_events",
        "ended_unix_ns",
        "end_reason",
        "format",
        "frame_count",
        "frames",
        "host_boot_id",
        "power_evidence",
        "power_evidence_count",
        "started_unix_ns",
        "target_boot_id",
        "target_product",
        "transport_snapshot_count",
        "transport_snapshots",
        "usb_events",
        "usb_location",
    }
    anchor = parse_record(anchor_path)
    if set(anchor) != {
        "format",
        "host_boot_id",
        "created_unix",
        "usb_location",
        "recovery_vendor",
        "recovery_product_id",
        "recovery_product",
    }:
        fail("recovery USB anchor schema changed")
    target_boot_id = value.get("target_boot_id")
    frames = value.get("frames")
    transport_snapshots = value.get("transport_snapshots")
    usb_events = value.get("usb_events")
    power_evidence = value.get("power_evidence")
    if (
        set(value) != expected_keys
        or value.get("format") != "rog5-early-target-evidence-v2"
        or value.get("candidate") != expected_candidate
        or value.get("capture_status") != "valid"
        or value.get("target_product") != "ROG5 diagnostic network root"
        or value.get("host_boot_id") != anchor["host_boot_id"]
        or value.get("usb_location") != anchor["usb_location"]
        or not isinstance(target_boot_id, str)
        or not BOOT_ID.fullmatch(target_boot_id)
        or value.get("end_reason") not in {"disconnected", "timeout"}
        or type(value.get("started_unix_ns")) is not int
        or type(value.get("ended_unix_ns")) is not int
        or value["started_unix_ns"] <= 0
        or value["ended_unix_ns"] < value["started_unix_ns"]
        or type(value.get("dropped_usb_events")) is not int
        or value["dropped_usb_events"] < 0
        or type(value.get("dropped_transport_snapshots")) is not int
        or value["dropped_transport_snapshots"] != 0
        or not isinstance(frames, list)
        or not isinstance(transport_snapshots, list)
        or not isinstance(usb_events, list)
        or not isinstance(power_evidence, list)
        or len(usb_events) > 64
        or type(value.get("frame_count")) is not int
        or not 1 <= value["frame_count"] <= 4096
        or value["frame_count"] != len(frames)
        or type(value.get("power_evidence_count")) is not int
        or not 0 <= value["power_evidence_count"] <= 1024
        or value["power_evidence_count"] != len(power_evidence)
        or type(value.get("transport_snapshot_count")) is not int
        or not 1 <= value["transport_snapshot_count"] <= 768
        or value["transport_snapshot_count"] != len(transport_snapshots)
    ):
        fail("diagnostic evidence identity or status is invalid")
    frame_keys = {"host_monotonic_ns", "host_unix_ns", "record"}
    record_keys = {
        "boot_id",
        "boottime_ms",
        "candidate",
        "dropped_updates",
        "fault",
        "last_good_code",
        "sequence",
        "stage",
        "stage_code",
        "watchdog_deadline_ms",
    }
    for frame in frames:
        if (
            not isinstance(frame, dict)
            or set(frame) != frame_keys
            or type(frame.get("host_monotonic_ns")) is not int
            or type(frame.get("host_unix_ns")) is not int
            or frame["host_monotonic_ns"] < 0
            or frame["host_unix_ns"] <= 0
        ):
            fail("diagnostic evidence frame is invalid")
        record = frame.get("record")
        if (
            not isinstance(record, dict)
            or set(record) != record_keys
            or record.get("candidate") != expected_candidate
            or record.get("boot_id") != target_boot_id
        ):
            fail("diagnostic evidence frame identity is invalid")
        for name in (
            "boottime_ms",
            "dropped_updates",
            "last_good_code",
            "sequence",
            "stage_code",
            "watchdog_deadline_ms",
        ):
            if type(record.get(name)) is not int or record[name] < 0:
                fail("diagnostic evidence record value is invalid")
        if (
            not isinstance(record.get("stage"), str)
            or not record["stage"]
            or not isinstance(record.get("fault"), str)
            or not record["fault"]
        ):
            fail("diagnostic evidence record text is invalid")
    if require_ssh and not any(
        frame["record"].get("stage_code") == 150
        and frame["record"].get("stage") == "ssh-key-accepted"
        and frame["record"].get("last_good_code") == 150
        and frame["record"].get("fault") == "none"
        for frame in frames
    ):
        fail("diagnostic evidence lacks strict SSH acceptance milestone")
    power_frame_keys = {"host_monotonic_ns", "host_unix_ns", "record"}
    power_record_keys = {
        "boot_id",
        "boottime_ms",
        "candidate",
        "category",
        "encoding",
        "name",
        "sequence",
        "status",
        "value",
    }
    power_sequence = 0
    power_boottime = 0
    for item in power_evidence:
        if (
            not isinstance(item, dict)
            or set(item) != power_frame_keys
            or type(item.get("host_monotonic_ns")) is not int
            or type(item.get("host_unix_ns")) is not int
            or item["host_monotonic_ns"] < 0
            or item["host_unix_ns"] <= 0
        ):
            fail("power evidence frame is invalid")
        record = item.get("record")
        if (
            not isinstance(record, dict)
            or set(record) != power_record_keys
            or record.get("candidate") != expected_candidate
            or record.get("boot_id") != target_boot_id
            or record.get("encoding") != "hex"
            or record.get("status") not in {"present", "absent", "error"}
            or type(record.get("sequence")) is not int
            or record["sequence"] < 1
            or type(record.get("boottime_ms")) is not int
            or record["boottime_ms"] < 0
            or not isinstance(record.get("category"), str)
            or re.fullmatch(
                r"[a-z0-9][a-z0-9_.:-]{0,95}", record["category"]
            )
            is None
            or not isinstance(record.get("name"), str)
            or re.fullmatch(
                r"[a-z0-9][a-z0-9_.:-]{0,95}", record["name"]
            )
            is None
            or not isinstance(record.get("value"), str)
            or len(record["value"]) > 512
            or len(record["value"]) % 2
            or re.fullmatch(r"[0-9a-f]*", record["value"]) is None
            or record["status"] == "present" and not record["value"]
            or record["sequence"] <= power_sequence
            or record["boottime_ms"] < power_boottime
        ):
            fail("power evidence record is invalid")
        power_sequence = record["sequence"]
        power_boottime = record["boottime_ms"]
    if require_power:
        completed = [
            item["record"]
            for item in power_evidence
            if item["record"].get("category") == "summary"
            and item["record"].get("name") == "result"
            and item["record"].get("status") == "present"
            and item["record"].get("value") == "636f6d706c657465"
        ]
        if len(completed) != 1:
            fail("power evidence lacks one complete summary")
    for event in usb_events:
        if (
            not isinstance(event, dict)
            or set(event) != {"host_unix_ns", "message"}
            or type(event.get("host_unix_ns")) is not int
            or event["host_unix_ns"] <= 0
            or not isinstance(event.get("message"), str)
            or not event["message"].isascii()
            or not 1 <= len(event["message"].encode("ascii")) <= 256
        ):
            fail("diagnostic evidence USB event is invalid")
    transport_keys = {
        "carrier",
        "host_monotonic_ns",
        "host_unix_ns",
        "interface",
        "nfs_rpc_badauth",
        "nfs_rpc_badcalls",
        "nfs_rpc_badclnt",
        "nfs_rpc_calls",
        "nfs_rpc_xdrcall",
        "nfs_tcp_accept_backlog",
        "nfs_tcp_connections",
        "nfs_tcp_listener",
        "nfs_tcp_unrecovered_retransmits",
        "nfs_tcp_rx_queue",
        "nfs_tcp_states",
        "nfs_tcp_tx_queue",
        "operstate",
        "rx_bytes",
        "rx_dropped",
        "rx_errors",
        "rx_packets",
        "state",
        "tx_bytes",
        "tx_dropped",
        "tx_errors",
        "tx_packets",
        "usb_location",
    }
    network_counters = {
        "rx_bytes",
        "rx_dropped",
        "rx_errors",
        "rx_packets",
        "tx_bytes",
        "tx_dropped",
        "tx_errors",
        "tx_packets",
    }
    nfs_counters = {
        "nfs_rpc_badauth",
        "nfs_rpc_badcalls",
        "nfs_rpc_badclnt",
        "nfs_rpc_calls",
        "nfs_rpc_xdrcall",
    }
    operstates = {
        "unknown",
        "notpresent",
        "down",
        "lowerlayerdown",
        "testing",
        "dormant",
        "up",
    }
    tcp_states = (
        "established",
        "syn-sent",
        "syn-recv",
        "fin-wait-1",
        "fin-wait-2",
        "time-wait",
        "close",
        "close-wait",
        "last-ack",
        "closing",
        "new-syn-recv",
    )
    last_transport_monotonic = -1
    last_transport_unix = 0
    for snapshot in transport_snapshots:
        if (
            not isinstance(snapshot, dict)
            or set(snapshot) != transport_keys
            or type(snapshot.get("host_monotonic_ns")) is not int
            or snapshot["host_monotonic_ns"] < last_transport_monotonic
            or type(snapshot.get("host_unix_ns")) is not int
            or snapshot["host_unix_ns"] < last_transport_unix
            or not value["started_unix_ns"]
            <= snapshot["host_unix_ns"]
            <= value["ended_unix_ns"]
            or snapshot.get("usb_location") != anchor["usb_location"]
            or snapshot.get("state") not in {"present", "absent"}
        ):
            fail("diagnostic transport snapshot is invalid")
        last_transport_monotonic = snapshot["host_monotonic_ns"]
        last_transport_unix = snapshot["host_unix_ns"]
        nfs_values = [snapshot.get(name) for name in nfs_counters]
        if not (
            all(item is None for item in nfs_values)
            or all(
                type(item) is int and 0 <= item <= (1 << 64) - 1
                for item in nfs_values
            )
        ):
            fail("diagnostic NFS RPC snapshot is invalid")
        listener = snapshot.get("nfs_tcp_listener")
        accept_backlog = snapshot.get("nfs_tcp_accept_backlog")
        connections = snapshot.get("nfs_tcp_connections")
        observed_tcp_states = snapshot.get("nfs_tcp_states")
        tcp_counters = (
            snapshot.get("nfs_tcp_tx_queue"),
            snapshot.get("nfs_tcp_rx_queue"),
            snapshot.get("nfs_tcp_unrecovered_retransmits"),
        )
        if (
            type(listener) is not int
            or listener not in {0, 1}
            or type(accept_backlog) is not int
            or not 0 <= accept_backlog <= (1 << 32) - 1
            or listener == 0
            and accept_backlog != 0
            or type(connections) is not int
            or not 0 <= connections <= 64
            or not isinstance(observed_tcp_states, str)
            or any(
                type(item) is not int or not 0 <= item <= (1 << 64) - 1
                for item in tcp_counters
            )
        ):
            fail("diagnostic NFS TCP snapshot is invalid")
        if connections == 0:
            if observed_tcp_states != "absent" or any(tcp_counters):
                fail("absent diagnostic NFS TCP snapshot is inconsistent")
        else:
            selected_tcp_states = observed_tcp_states.split(",")
            if (
                any(item not in tcp_states for item in selected_tcp_states)
                or len(selected_tcp_states) > connections
                or selected_tcp_states
                != [item for item in tcp_states if item in selected_tcp_states]
            ):
                fail("diagnostic NFS TCP states are not canonical")
        if snapshot["state"] == "absent":
            if (
                snapshot.get("interface") is not None
                or snapshot.get("carrier") is not None
                or snapshot.get("operstate") is not None
                or any(snapshot.get(name) is not None for name in network_counters)
            ):
                fail("absent diagnostic NCM snapshot carries link state")
        elif (
            not isinstance(snapshot.get("interface"), str)
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", snapshot["interface"])
            or type(snapshot.get("carrier")) is not int
            or snapshot["carrier"] not in {0, 1}
            or snapshot.get("operstate") not in operstates
            or any(
                type(snapshot.get(name)) is not int
                or not 0 <= snapshot[name] <= (1 << 64) - 1
                for name in network_counters
            )
        ):
            fail("present diagnostic NCM snapshot is invalid")
    return target_boot_id


def write_record(path: Path, values: tuple[tuple[str, str], ...]) -> None:
    payload = "".join(f"{name}={value}\n" for name, value in values).encode(
        "ascii"
    )
    descriptor = open_exclusive(path)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written < 1:
                fail("cannot write private lifecycle record")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


class LiveCycle:
    def __init__(
        self,
        dependencies: Dependencies,
        inputs: Inputs,
        profile: CycleProfile = STANDARD_CYCLE_PROFILE,
    ):
        self.dependencies = dependencies
        self.inputs = inputs
        self.profile = profile
        self.poll = 0.02 if dependencies.offline else 0.25
        self.short_timeout = 4 if dependencies.offline else 120
        self.target_key_timeout = 4 if dependencies.offline else 450
        self.bundle_timeout = (
            5 if dependencies.offline else BUNDLE_TIMEOUT_SECONDS
        )
        self.control_timeout = (
            5 if dependencies.offline else CONTROL_TIMEOUT_SECONDS
        )
        self.network_timeout = (
            8
            if dependencies.offline
            else POWER_USB.NETWORK_SERVER_TIMEOUT_SECONDS + 15
        )
        self.diagnostic_capture_timeout = (
            POWER_USB.SAMPLER_TIMEOUT_SECONDS
            if profile.early_probe
            else 660
        )
        self.diagnostic_timeout = (
            8
            if dependencies.offline
            else self.diagnostic_capture_timeout + 75
        )
        self.cleanup_stabilize_timeout = (
            0.5 if dependencies.offline else 10
        )
        self.cleanup_stabilize_dwell = (
            0.08 if dependencies.offline else 1
        )
        if (
            self.cleanup_stabilize_dwell + 2 * self.poll
            > self.cleanup_stabilize_timeout
        ):
            fail("invalid host cleanup stabilization timing")
        self.fallback_timeout = (
            5 if dependencies.offline else inputs.fallback_timeout
        )
        self.host_snapshot: HostSnapshot | None = None

    def output(self, name: str) -> Path:
        return self.inputs.evidence_dir / name

    def verify_repository(self) -> None:
        verify_repository_checkpoint(self.dependencies.git)

    def verify_power_usb_receipts(self) -> None:
        if self.profile != POWER_USB_CYCLE_PROFILE:
            return
        doctor_receipt = self.inputs.host_doctor_receipt
        deployment_receipt = self.inputs.deployment_receipt
        if doctor_receipt is None or deployment_receipt is None:
            fail("power USB lifecycle lacks its immutable host/deployment receipts")
        for executable in (
            self.dependencies.host_doctor,
            self.dependencies.deployment_receipt,
        ):
            fixed_executable(executable, offline=self.dependencies.offline)
        for path, expected, label in (
            (
                doctor_receipt,
                self.inputs.host_doctor_receipt_sha256,
                "host-doctor",
            ),
            (
                deployment_receipt,
                self.inputs.deployment_receipt_sha256,
                "deployment",
            ),
        ):
            if file_sha256(path) != expected:
                fail(f"immutable {label} receipt changed after admission")
        deployment = json.loads(deployment_receipt.read_text(encoding="ascii"))
        if (
            deployment.get("format")
            != "rog5-power-usb-deployment-receipt-v1"
            or deployment.get("state") != "admitted"
            or deployment.get("candidate") != POWER_USB.CANDIDATE
            or deployment.get("output_root") != POWER_USB.OUTPUT_ROOT
        ):
            fail("power USB deployment receipt is not the exact admitted state")
        run_capture(
            [
                str(self.dependencies.host_doctor),
                "verify",
                str(doctor_receipt),
                "--deployment-receipt",
                str(deployment_receipt),
            ],
            environment=child_environment(),
            timeout=self.short_timeout,
        )
        run_capture(
            [
                str(self.dependencies.deployment_receipt),
                "verify",
                str(deployment_receipt),
                "--build-root",
                str(REPO / POWER_USB.OUTPUT_ROOT),
            ],
            environment=child_environment(),
            timeout=self.short_timeout,
        )

    def ledger_root(self) -> Path:
        state_home = os.environ.get("XDG_STATE_HOME")
        if state_home:
            base = Path(state_home)
            if not base.is_absolute():
                fail("XDG_STATE_HOME must be absolute for lifecycle intents")
        else:
            base = Path.home() / ".local" / "state"
        return base / "rog5-recovery-intents"

    def temporary_boot_consumption_root(self) -> Path:
        if self.dependencies.offline:
            state_home = os.environ.get("XDG_STATE_HOME")
            if state_home:
                base = Path(state_home)
                if not base.is_absolute():
                    fail(
                        "XDG_STATE_HOME must be absolute for lifecycle state"
                    )
            else:
                base = Path.home() / ".local" / "state"
        else:
            account_home = Path(pwd.getpwuid(os.geteuid()).pw_dir)
            if not account_home.is_absolute():
                fail("lifecycle account home must be absolute")
            try:
                account_home = account_home.resolve(strict=True)
            except OSError as error:
                raise CycleError(
                    "lifecycle account home is unsafe or absent"
                ) from error
            base = account_home / ".local" / "state"
        return base / "rog5-temporary-boot-consumption"

    def temporary_boot_consumption_path(self) -> Path:
        profile = self.profile.recovery_profile
        if not re.fullmatch(r"[a-z0-9-]{1,96}", profile):
            fail("recovery profile cannot identify temporary-boot state")
        return self.temporary_boot_consumption_root() / f"{profile}.record"

    def temporary_boot_entered_path(self) -> Path:
        return Path(f"{self.temporary_boot_consumption_path()}.entered")

    def validate_temporary_boot_consumption_root(
        self,
        *,
        create: bool,
    ) -> Path:
        root = self.temporary_boot_consumption_root()
        if create:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not root.exists() and not root.is_symlink():
            return root
        try:
            metadata = root.lstat()
        except OSError as error:
            raise CycleError(
                "cannot inspect temporary-boot consumption root"
            ) from error
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            fail("temporary-boot consumption root metadata is unsafe")
        return root

    def assert_temporary_boot_unconsumed(self) -> None:
        self.validate_temporary_boot_consumption_root(create=False)
        path = self.temporary_boot_consumption_path()
        entered = self.temporary_boot_entered_path()
        if (
            path.exists()
            or path.is_symlink()
            or entered.exists()
            or entered.is_symlink()
        ):
            fail(
                "temporary recovery lifecycle is already consumed on this "
                "host"
            )

    @staticmethod
    def _exact_claim_file(path: Path, expected: bytes) -> None:
        def metadata_identity(value: os.stat_result) -> tuple[int, ...]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_uid,
                value.st_gid,
                value.st_nlink,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )

        try:
            before = path.lstat()
            payload = path.read_bytes()
            after = path.lstat()
        except OSError as error:
            raise CycleError(
                "externally consumed temporary-boot claim is absent"
            ) from error
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or metadata_identity(before) != metadata_identity(after)
            or payload != expected
        ):
            fail("externally consumed temporary-boot claim is not exact")

    def assert_temporary_boot_claim_entered(self) -> None:
        self.validate_temporary_boot_consumption_root(create=False)
        expected = CLAIM_CONSUMER.expected_record(
            self.profile.recovery_profile
        )
        source = self.temporary_boot_consumption_path()
        if source.exists() or source.is_symlink():
            fail("external temporary-boot claim source still exists")
        self._exact_claim_file(self.temporary_boot_entered_path(), expected)
        try:
            guard_anchor = CLAIM_CONSUMER.canonical_claim_anchor()
        except CLAIM_CONSUMER.ClaimError as error:
            raise CycleError(
                "external temporary-boot claim anchor is unsafe or absent"
            ) from error
        guard = guard_anchor / (
            ".rog5-temporary-boot-consumption."
            f"{self.profile.recovery_profile}.entered"
        )
        self._exact_claim_file(guard, expected)

    def claim_temporary_boot(self) -> None:
        external = os.environ.get("ROG5_EXTERNAL_BOOT_CLAIM", "0")
        if external not in {"0", "1"}:
            fail("ROG5_EXTERNAL_BOOT_CLAIM must be exactly 0 or 1")
        if external == "1":
            self.assert_temporary_boot_claim_entered()
            return
        self.validate_temporary_boot_consumption_root(create=True)
        path = self.temporary_boot_consumption_path()
        entered = self.temporary_boot_entered_path()
        if entered.exists() or entered.is_symlink():
            fail(
                "temporary recovery lifecycle is already consumed on this "
                "host"
            )
        try:
            write_record(
                path,
                (
                    ("format", "rog5-temporary-boot-consumption-v1"),
                    ("recovery_profile", self.profile.recovery_profile),
                    ("candidate", self.profile.candidate),
                    ("manifest_sha256", self.inputs.manifest_sha256),
                    ("state", "BOOT_CLAIMED"),
                ),
            )
        except FileExistsError:
            fail(
                "temporary recovery lifecycle is already consumed on this "
                "host"
            )

    def ledger_inventory(self) -> set[str]:
        root = self.ledger_root()
        if not root.exists() and not root.is_symlink():
            return set()
        try:
            metadata = root.lstat()
        except OSError as error:
            raise CycleError("cannot inspect durable intent root") from error
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            fail("durable intent root metadata is unsafe")
        names: set[str] = set()
        for path in root.iterdir():
            if path.name == ".lock":
                continue
            if (
                not path.name.endswith(".json")
                or not HEX_ID.fullmatch(path.name[:-5])
            ):
                fail("durable intent root contains an unknown entry")
            metadata = path.lstat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_nlink != 1
            ):
                fail("durable intent record metadata is unsafe")
            names.add(path.name)
        return names

    def new_ledger_intent(self, before: set[str]) -> Intent | None:
        after = self.ledger_inventory()
        added = after - before
        if not added:
            return None
        if len(added) != 1:
            fail("multiple durable intents appeared during one transaction")
        path = self.ledger_root() / next(iter(added))
        try:
            lines = [
                line
                for line in path.read_text(encoding="ascii").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeDecodeError) as error:
            raise CycleError("new durable intent is unreadable") from error
        if len(lines) != 1:
            fail("new durable intent is not one canonical JSON record")
        value = canonical_json(lines[0])
        intent = validate_intent(
            value,
            manifest_sha256=self.inputs.manifest_sha256,
            target=self.profile.bundle,
        )
        if path.name != f"{intent.session}.json":
            fail("new durable intent path does not match its session")
        return intent

    def remaining_timeout(self, deadline: float | None) -> float:
        if deadline is None:
            return 180
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("host cleanup stabilization deadline expired")
        return remaining

    def firewall_empty(self, *, deadline: float | None = None) -> bool:
        drop_lines = run_capture(
            [
                str(self.dependencies.firewall),
                "--zone=drop",
                "--list-all",
            ],
            timeout=self.remaining_timeout(deadline),
        ).stdout.splitlines()
        if (
            not drop_lines
            or drop_lines[0].strip().split(maxsplit=1)[0] != "drop"
        ):
            fail("drop firewall zone output is not canonical")
        drop_fields: dict[str, str] = {}
        rich_rules_seen = False
        for line in drop_lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if rich_rules_seen:
                fail("drop firewall zone retains lifecycle state")
            name, separator, value = stripped.partition(":")
            if not separator or not name or name in drop_fields:
                fail("drop firewall zone output is not canonical")
            drop_fields[name] = value.strip()
            if name == "rich rules":
                rich_rules_seen = True
        required = {
            "target",
            "icmp-block-inversion",
            "interfaces",
            "sources",
            "services",
            "ports",
            "protocols",
            "forward",
            "masquerade",
            "forward-ports",
            "source-ports",
            "icmp-blocks",
            "rich rules",
        }
        if not required.issubset(drop_fields):
            fail("drop firewall zone output is incomplete")
        if drop_fields["target"] != "DROP":
            fail("drop firewall zone is not drop-by-default")
        if drop_fields["icmp-block-inversion"] != "no":
            fail("drop firewall zone has ICMP block inversion enabled")
        for name in (
            "interfaces",
            "sources",
            "services",
            "ports",
            "protocols",
            "forward-ports",
            "source-ports",
            "icmp-blocks",
            "rich rules",
        ):
            if drop_fields[name]:
                fail("drop firewall zone retains lifecycle state")
        if drop_fields["masquerade"] == "yes":
            fail("drop firewall zone has masquerading enabled")
        if drop_fields["masquerade"] != "no":
            fail("cannot inspect drop-zone masquerading state")
        if drop_fields["forward"] not in {"yes", "no"}:
            fail("cannot inspect drop-zone forwarding state")
        zones_result = run_capture(
            [str(self.dependencies.firewall), "--get-zones"],
            timeout=self.remaining_timeout(deadline),
        )
        zones = zones_result.stdout.split()
        if "drop" not in zones or len(set(zones)) != len(zones):
            fail("cannot enumerate canonical firewall zones")
        forbidden_rules = {
            'rule family="ipv4" priority="-300" destination '
            'address="169.254.77.1/32" port port="8080" '
            'protocol="tcp" drop',
            'rule family="ipv4" priority="-300" destination '
            'address="169.254.77.1/32" port port="2049" '
            'protocol="tcp" drop',
            'rule family="ipv4" priority="-300" port port="32767" '
            'protocol="tcp" drop',
            'rule family="ipv4" priority="-300" port port="32767" '
            'protocol="udp" drop',
        }
        all_zones = run_capture(
            [str(self.dependencies.firewall), "--list-all-zones"],
            timeout=self.remaining_timeout(deadline),
        ).stdout.splitlines()
        observed_zones: list[str] = []
        current_zone = ""
        for line in all_zones:
            stripped = line.strip()
            if not stripped:
                continue
            if not line[0].isspace():
                current_zone = stripped.split(maxsplit=1)[0]
                if current_zone not in zones:
                    fail("firewall returned an unknown zone snapshot")
                observed_zones.append(current_zone)
            elif stripped in forbidden_rules:
                if not current_zone:
                    fail("firewall rich rule lacks a zone identity")
                fail(
                    f"firewall zone {current_zone} retains a lifecycle "
                    "drop rule"
                )
        if len(observed_zones) != len(zones) or set(observed_zones) != set(
            zones
        ):
            fail("firewall all-zone snapshot is not canonical")
        return drop_fields["forward"] == "yes"

    def capture_host_snapshot(
        self, *, deadline: float | None = None
    ) -> HostSnapshot:
        try:
            ip_nonlocal = self.dependencies.ip_nonlocal_bind.read_text(
                encoding="ascii"
            ).strip()
        except (OSError, UnicodeDecodeError) as error:
            raise CycleError("cannot inspect ip_nonlocal_bind") from error
        if ip_nonlocal not in {"0", "1"}:
            fail("ip_nonlocal_bind is not canonical")
        return HostSnapshot(
            firewall_forward=self.firewall_empty(deadline=deadline),
            ip_nonlocal_bind=ip_nonlocal,
        )

    def rog5_ncm_interfaces(
        self, *, deadline: float | None = None
    ) -> tuple[InterfaceSnapshot, ...]:
        snapshots: list[InterfaceSnapshot] = []
        try:
            paths = sorted(self.dependencies.sys_class_net.iterdir())
        except OSError as error:
            raise CycleError("cannot inspect host network interfaces") from error
        for path in paths:
            name = path.name
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", name):
                continue
            properties_result = run_capture(
                [
                    str(self.dependencies.udevadm),
                    "info",
                    "--query=property",
                    f"--path={path}",
                ],
                timeout=self.remaining_timeout(deadline),
                check=False,
            )
            if properties_result.returncode != 0:
                continue
            properties: dict[str, str] = {}
            malformed = False
            for line in properties_result.stdout.splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in properties:
                    malformed = True
                    break
                properties[key] = value
            if malformed:
                fail("udev returned duplicate interface properties")
            if (
                properties.get("ID_VENDOR_ID") != "1d6b"
                or properties.get("ID_MODEL_ID") != "0104"
                or properties.get("ID_NET_DRIVER") != "cdc_ncm"
                or properties.get("ID_MODEL", "") not in ROG5_NCM_MODELS
            ):
                continue
            address_result = run_capture(
                [
                    str(self.dependencies.ip),
                    "-4",
                    "-o",
                    "address",
                    "show",
                    "dev",
                    name,
                ],
                timeout=self.remaining_timeout(deadline),
            )
            addresses = []
            for line in address_result.stdout.splitlines():
                fields = line.split()
                if len(fields) < 4 or fields[2] != "inet":
                    fail("ip returned a malformed ROG5 address record")
                addresses.append(fields[3])
            zone_lines = [
                line.strip()
                for line in run_capture(
                    [
                        str(self.dependencies.firewall),
                        f"--get-zone-of-interface={name}",
                    ],
                    timeout=self.remaining_timeout(deadline),
                    check=False,
                ).stdout.splitlines()
                if line.strip()
            ]
            if zone_lines == ["no zone"]:
                zone_lines = []
            if len(zone_lines) > 1 or (
                zone_lines
                and not re.fullmatch(r"[A-Za-z0-9_-]+", zone_lines[0])
            ):
                fail("ROG5 interface has an invalid firewall zone")
            managed_result = run_capture(
                [
                    str(self.dependencies.nmcli),
                    "-g",
                    "GENERAL.NM-MANAGED",
                    "device",
                    "show",
                    name,
                ],
                timeout=self.remaining_timeout(deadline),
                check=False,
            )
            managed = managed_result.stdout.strip()
            if managed_result.returncode != 0 or managed not in {"yes", "no"}:
                managed_result = run_capture(
                    [
                        str(self.dependencies.nmcli),
                        "-g",
                        "GENERAL.MANAGED",
                        "device",
                        "show",
                        name,
                    ],
                    timeout=self.remaining_timeout(deadline),
                    check=False,
                )
                managed = managed_result.stdout.strip()
            if managed_result.returncode != 0 or managed not in {"yes", "no"}:
                raise HostIdentityObservationError(
                    "cannot inspect NetworkManager ownership of ROG5 link"
                )
            snapshots.append(
                InterfaceSnapshot(
                    name=name,
                    product=properties["ID_MODEL"],
                    addresses=tuple(sorted(addresses)),
                    firewall_zone=zone_lines[0] if zone_lines else "",
                    network_manager_managed=managed,
                )
            )
        return tuple(snapshots)

    def wait_recovery_ncm(self) -> tuple[InterfaceSnapshot, ...]:
        deadline = time.monotonic() + self.short_timeout
        previous: tuple[InterfaceSnapshot, ...] | None = None
        stable_since = 0.0
        profile_activated = False
        while time.monotonic() < deadline:
            observed = tuple(
                item
                for item in self.rog5_ncm_interfaces()
                if (
                    item.product == "ROG5_recovery"
                    and item.network_manager_managed == "yes"
                    and item.firewall_zone != "drop"
                )
            )
            if (
                not profile_activated
                and len(observed) == 1
                and observed[0].addresses == ()
            ):
                profile = run_capture(
                    [
                        str(self.dependencies.nmcli),
                        "-g",
                        "connection.uuid,connection.id,"
                        "connection.interface-name,connection.autoconnect",
                        "connection",
                        "show",
                        FALLBACK_NETWORK_PROFILE,
                    ],
                    timeout=self.remaining_timeout(deadline),
                ).stdout.splitlines()
                if (
                    len(profile) != 4
                    or not re.fullmatch(
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                        r"[0-9a-f]{4}-[0-9a-f]{12}",
                        profile[0],
                    )
                    or profile[1] != FALLBACK_NETWORK_PROFILE
                    or profile[2] != observed[0].name
                    or profile[3] != "no"
                ):
                    fail("recovery NetworkManager profile is not exactly deferred")
                run_capture(
                    [
                        str(self.dependencies.nmcli),
                        "connection",
                        "up",
                        "uuid",
                        profile[0],
                        "ifname",
                        observed[0].name,
                    ],
                    timeout=self.remaining_timeout(deadline),
                )
                profile_activated = True
                previous = None
                stable_since = 0.0
                continue
            current = tuple(
                item
                for item in observed
                if item.addresses == ("169.254.77.1/30",)
            )
            if len(current) != 1:
                previous = None
                stable_since = 0.0
            elif current != previous:
                previous = current
                stable_since = time.monotonic()
            elif time.monotonic() - stable_since >= (
                0.04 if self.dependencies.offline else 1.0
            ):
                return current
            time.sleep(self.poll)
        fail("exact recovery NCM host state did not become stable")

    def verify_recovery_profile_deferred(
        self,
        original: tuple[InterfaceSnapshot, ...],
        *,
        deadline: float | None = None,
    ) -> None:
        if len(original) != 1:
            fail("recovery NCM anchor snapshot is ambiguous")
        expected = original[0]
        current = self.rog5_ncm_interfaces(deadline=deadline)
        if (
            len(current) != 1
            or current[0].name != expected.name
            or current[0].product != expected.product
            or current[0].firewall_zone != expected.firewall_zone
            or current[0].addresses
            or current[0].network_manager_managed != "no"
        ):
            raise HostIdentityObservationError(
                "bundle cleanup did not leave the exact recovery NCM "
                "profile deferred"
            )
        profile = run_capture(
            [
                str(self.dependencies.nmcli),
                "-g",
                "connection.uuid,connection.id,"
                "connection.interface-name,connection.autoconnect",
                "connection",
                "show",
                FALLBACK_NETWORK_PROFILE,
            ],
            timeout=self.remaining_timeout(deadline),
        ).stdout.splitlines()
        if (
            len(profile) != 4
            or not re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                r"[0-9a-f]{4}-[0-9a-f]{12}",
                profile[0],
            )
            or profile[1] != FALLBACK_NETWORK_PROFILE
            or profile[2] != expected.name
            or profile[3] != "no"
        ):
            raise HostIdentityObservationError(
                "fallback profile is not exactly inactive and deferred"
            )
        # NetworkManager can retain the exact last profile UUID after the
        # device is deactivated and explicitly made unmanaged.  With
        # `nmcli -g`, NetworkManager 1.52.1 renders a NULL CON-UUID as one
        # empty output field, so splitlines() returns [""]; a zero-byte
        # compatible implementation or test double returns [].  Treat those
        # two shapes as no association, and the exact UUID as historical only
        # after the address-free, unmanaged, exact-profile, autoconnect-off
        # checks above.  wait_host_clean() repeats this entire observation
        # through one continuous clean dwell.
        associated = run_capture(
            [
                str(self.dependencies.nmcli),
                "-g",
                "GENERAL.CON-UUID",
                "device",
                "show",
                expected.name,
            ],
            timeout=self.remaining_timeout(deadline),
        ).stdout.splitlines()
        if associated not in ([], [""], [profile[0]]):
            if associated == ["--"]:
                association_class = "placeholder"
            elif associated and all(value == "" for value in associated):
                association_class = "duplicate-empty"
            elif associated and all(
                value == profile[0] for value in associated
            ):
                association_class = "duplicate-exact"
            elif "" in associated:
                association_class = "mixed-empty"
            elif profile[0] in associated:
                association_class = "mixed"
            else:
                association_class = "foreign"
            raise HostIdentityObservationError(
                "deferred recovery interface retains an unexpected profile "
                f"association (class={association_class} "
                f"count={len(associated)})"
            )

    def verify_host_clean(
        self,
        *,
        final: bool = False,
        deadline: float | None = None,
    ) -> None:
        for path in (
            self.dependencies.handoff_marker,
            self.dependencies.network_service_state,
            self.dependencies.export_mount,
        ):
            if path.exists() or path.is_symlink():
                fail(f"host lifecycle residue remains: {path}")
        listener_checks = (
            (
                "8080",
                "-lnt4",
                "sport = :8080 and ( src = 0.0.0.0/32 or "
                f"src = {BUNDLE_HOST_ADDRESS}/32 )",
            ),
            (
                "8080",
                "-lnt6",
                "sport = :8080 and ( src = ::/128 or "
                "src = ::ffff:0.0.0.0/128 or "
                f"src = ::ffff:{BUNDLE_HOST_ADDRESS}/128 )",
            ),
            (
                "8081",
                "-lnt4",
                "sport = :8081 and ( src = 0.0.0.0/32 or "
                f"src = {BUNDLE_HOST_ADDRESS}/32 )",
            ),
            (
                "8081",
                "-lnt6",
                "sport = :8081 and ( src = ::/128 or "
                "src = ::ffff:0.0.0.0/128 or "
                f"src = ::ffff:{BUNDLE_HOST_ADDRESS}/128 )",
            ),
            ("2049", "-lntu4", "sport = :2049"),
            ("32767", "-lntu4", "sport = :32767"),
        )
        for port, socket_selection, listener_filter in listener_checks:
            result = run_capture(
                [
                    str(self.dependencies.ss),
                    "-H",
                    socket_selection,
                    listener_filter,
                ],
                timeout=self.remaining_timeout(deadline),
            )
            if result.stdout.strip():
                fail(f"host listener remains on TCP port {port}")
        if self.dependencies.offline:
            export_descriptor = -1
            try:
                export_descriptor = os.open(
                    self.dependencies.nfs_exports,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                )
                export_metadata = os.fstat(export_descriptor)
                export_payload = os.read(
                    export_descriptor,
                    1024 * 1024 + 1,
                )
                current_metadata = self.dependencies.nfs_exports.lstat()
            except OSError as error:
                raise CycleError(
                    "cannot inspect host NFS exports"
                ) from error
            finally:
                if export_descriptor >= 0:
                    os.close(export_descriptor)
            if (
                not stat.S_ISREG(export_metadata.st_mode)
                or export_metadata.st_uid != os.geteuid()
                or export_metadata.st_gid != os.getegid()
                or stat.S_IMODE(export_metadata.st_mode)
                not in {0o600, 0o644}
                or current_metadata.st_dev != export_metadata.st_dev
                or current_metadata.st_ino != export_metadata.st_ino
                or len(export_payload) > 1024 * 1024
            ):
                fail("host NFS export table metadata is unsafe")
            if export_payload.strip():
                fail("host retains an NFS export")
        else:
            export_state = run_capture(
                [str(self.dependencies.network_root_server), "inspect"],
                timeout=self.remaining_timeout(deadline),
            )
            if export_state.stdout != (
                "PASS host NFS export table is empty\n"
            ):
                fail("host NFS export proof is not canonical")
        rog5_interfaces = self.rog5_ncm_interfaces(deadline=deadline)
        allowed_shared_addresses = {
            item.name
            for item in rog5_interfaces
            if (
                item.addresses == ("169.254.77.1/30",)
                and item.network_manager_managed == "yes"
                and item.firewall_zone != "drop"
            )
        }
        address_lines = run_capture(
            [
                str(self.dependencies.ip),
                "-4",
                "-o",
                "address",
                "show",
            ],
            timeout=self.remaining_timeout(deadline),
        ).stdout.splitlines()
        for line in address_lines:
            fields = line.split()
            if len(fields) >= 4 and fields[2] == "inet":
                if fields[3] == "169.254.77.1/30":
                    if len(fields) < 2 or fields[1] not in (
                        allowed_shared_addresses
                    ):
                        raise HostIdentityObservationError(
                            "shared ROG5 /30 escaped the exact managed "
                            "USB profile"
                        )
        if self.dependencies.nfs_threads.exists():
            try:
                threads = self.dependencies.nfs_threads.read_text(
                    encoding="ascii"
                ).strip()
            except (OSError, UnicodeDecodeError) as error:
                raise CycleError("cannot inspect host NFS threads") from error
            if threads != "0":
                fail("host retains active kernel NFS threads")
        if final:
            for interface in rog5_interfaces:
                if (
                    interface.network_manager_managed != "yes"
                    or interface.firewall_zone == "drop"
                ):
                    fail(
                        "fallback ROG5 interface retains lifecycle "
                        "ownership"
                    )
        current = self.capture_host_snapshot(deadline=deadline)
        if self.host_snapshot is None:
            self.host_snapshot = current
        elif current != self.host_snapshot:
            fail("host firewall or nonlocal-bind state was not restored")

    def wait_host_clean(
        self,
        *,
        final: bool = False,
        recovery_ncm: tuple[InterfaceSnapshot, ...] | None = None,
    ) -> None:
        deadline = time.monotonic() + self.cleanup_stabilize_timeout
        clean_since: float | None = None
        last_error: HostIdentityObservationError | None = None
        observed_clean = False
        while time.monotonic() < deadline:
            try:
                self.verify_host_clean(final=final, deadline=deadline)
                if recovery_ncm is not None:
                    self.verify_recovery_profile_deferred(
                        recovery_ncm,
                        deadline=deadline,
                    )
            except HostIdentityObservationError as error:
                clean_since = None
                last_error = error
            except CycleError as error:
                if (
                    str(error)
                    == "host cleanup stabilization deadline expired"
                ):
                    break
                raise
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    break
                raise
            else:
                now = time.monotonic()
                observed_clean = True
                last_error = None
                if clean_since is None:
                    clean_since = now
                elif now - clean_since >= self.cleanup_stabilize_dwell:
                    return
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(self.poll, remaining))
        if last_error is None:
            if observed_clean:
                fail(
                    "host cleanup deadline expired before the continuous "
                    "clean dwell was proved"
                )
            fail("host cleanup was never observed clean before its deadline")
        raise CycleError(
            f"host cleanup did not stabilize: {last_error}"
        ) from last_error

    def preflight(self) -> None:
        for path in (
            self.dependencies.git,
            self.dependencies.ss,
            self.dependencies.ip,
            self.dependencies.nmcli,
            self.dependencies.udevadm,
            self.dependencies.firewall,
            self.dependencies.live_gate,
            self.dependencies.bundle_server,
            self.dependencies.network_root_server,
            self.dependencies.recovery_control,
            self.dependencies.host_key,
            self.dependencies.runtime_acceptance,
            self.dependencies.fallback,
        ):
            fixed_executable(path, offline=self.dependencies.offline)
        if self.profile.recovery_profile in STOCK_FALLBACK_RECOVERY_PROFILES:
            fixed_executable(
                self.dependencies.stock_fallback,
                offline=self.dependencies.offline,
            )
        if self.profile.recovery_profile in POWER_USB_RECEIPT_RECOVERY_PROFILES:
            self.verify_power_usb_receipts()
        if self.profile.diagnostic:
            fixed_executable(
                self.dependencies.diagnostic_collector,
                offline=self.dependencies.offline,
            )
        for name in OUTPUT_NAMES:
            path = self.output(name)
            if path.exists() or path.is_symlink():
                fail(f"refusing existing private lifecycle output: {path}")
        self.verify_host_clean()
        run_capture(
            [
                str(self.dependencies.bundle_server),
                "preflight",
                self.profile.bundle,
                self.inputs.manifest_sha256,
            ],
            environment=child_environment(),
        )
        run_capture(
            [
                str(self.dependencies.network_root_server),
                "preflight",
                RECOVERY_PROFILE,
                self.inputs.root_package_sha256,
            ],
            environment=child_environment(),
        )
        run_capture(
            [str(self.dependencies.live_gate), "preflight"],
            environment=child_environment(
                ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE="1"
            ),
            timeout=300,
        )
        if self.profile.recovery_profile in STOCK_FALLBACK_RECOVERY_PROFILES:
            run_capture([str(self.dependencies.stock_fallback), "host-preflight"])
        else:
            run_capture(
                [
                    str(self.dependencies.fallback),
                    "ssh-host-preflight",
                    str(self.inputs.fallback_known_hosts),
                    str(self.inputs.ssh_key),
                    self.inputs.ssh_public_key_sha256,
                    str(self.inputs.fallback_timeout),
                    str(FALLBACK_CONTACT_START_BUDGET_SECONDS),
                ],
                environment=child_environment(
                    ALLOW_FALLBACK_SSH_CONTROL="1",
                    ALLOW_PHONE_CREDENTIAL_USE="1",
                ),
            )

    def wait_bundle(
        self,
        bundle: ManagedProcess,
        control: ManagedProcess,
        observer: ManagedProcess | None = None,
    ) -> None:
        deadline = time.monotonic() + self.bundle_timeout
        control_success_deadline: float | None = None
        progress_stop = self.output("recovery-progress.stop")
        progress_stop_created = False
        while time.monotonic() < deadline:
            if not progress_stop_created:
                prepared = observe_prepared_identity(
                    control.log,
                    self.inputs.manifest_sha256,
                    self.profile.bundle,
                )
                if prepared is not None:
                    write_record(
                        progress_stop,
                        (("format", "rog5-recovery-progress-stop-v1"),),
                    )
                    progress_stop_created = True
            if observer is not None:
                observer_status = observer.process.poll()
                if observer_status is not None:
                    fail(
                        f"{observer.name} exited with status "
                        f"{observer_status} before the commit handoff; "
                        f"inspect {observer.log}"
                    )
            status = bundle.process.poll()
            if status is not None:
                if status != 0:
                    fail(
                        f"bundle server failed with status {status}; inspect "
                        f"{bundle.log}"
                    )
                require_log_markers(
                    bundle.log,
                    (
                        "PASS one recovery bundle transfer completed",
                        "INFO recovery bundle host network state removed",
                        "INFO fallback NetworkManager profile restoration "
                        "deferred",
                    ),
                )
                if observer is not None and observer.process.poll() is not None:
                    fail(
                        f"{observer.name} exited before the commit handoff; "
                        f"inspect {observer.log}"
                    )
                return
            control_status = control.process.poll()
            if control_status is not None:
                if control_status != 0:
                    fail(
                        "recovery control exited before the one-transfer "
                        f"bundle server cleaned up; inspect {control.log}"
                    )
                if control_success_deadline is None:
                    control_success_deadline = min(
                        deadline,
                        time.monotonic() + 5.0,
                    )
                elif time.monotonic() >= control_success_deadline:
                    fail(
                        "one-transfer bundle server did not finish cleanup "
                        "within 5 seconds of successful recovery control; "
                        f"inspect {bundle.log}"
                    )
            time.sleep(self.poll)
        terminate(bundle)
        if control_success_deadline is not None:
            fail(
                "one-transfer bundle server did not finish cleanup within "
                "5 seconds of successful recovery control; inspect "
                f"{bundle.log}"
            )
        fail("one-transfer bundle server exceeded its bounded window")

    def require_fallback_contact_budget(
        self,
        deadline: float | None,
    ) -> None:
        if deadline is None or time.monotonic() >= deadline:
            fail(
                "recovery anchor contact-start budget expired before "
                "fallback strict-SSH access"
            )

    def capture_stock_fallback_preboot(self) -> None:
        record = self.output("stock-fallback-preboot.record")
        log = self.output("stock-fallback-preboot.log")
        run_logged(
            [str(self.dependencies.stock_fallback), "capture-preboot", str(record)],
            log,
            environment=child_environment(
                ALLOW_STOCK_ANDROID_FALLBACK_PROOF="1"
            ),
            timeout=self.short_timeout,
        )
        require_log_markers(
            log,
            ("PASS exact slot-A fastboot fallback precondition captured",),
        )

    def wait_fallback(self, target_boot_id: str | None) -> str:
        anchor = self.output("recovery-usb.anchor")
        location = read_recovery_anchor_location(
            anchor,
            self.dependencies,
        )
        fallback_deadline = time.monotonic() + self.fallback_timeout
        if self.profile.recovery_profile in STOCK_FALLBACK_RECOVERY_PROFILES:
            fallback_location = Path(location).name
            if fallback_location != "1-1.2":
                fail("stock fallback anchor does not end at the exact USB port")
            timeout = max(
                1,
                min(900, int(fallback_deadline - time.monotonic() + 0.999)),
            )
            identity = self.output("fallback-identity.record")
            run_logged(
                [
                    str(self.dependencies.stock_fallback),
                    "wait",
                    fallback_location,
                    str(timeout),
                    str(self.output("stock-fallback-preboot.record")),
                    str(identity),
                ],
                self.output("fallback-preflight.log"),
                environment=child_environment(
                    ALLOW_STOCK_ANDROID_FALLBACK_PROOF="1"
                ),
                timeout=timeout + FALLBACK_CONTROL_MARGIN_SECONDS,
            )
            require_log_markers(
                self.output("fallback-preflight.log"),
                ("PASS exact stock WW33 slot-A fallback ",),
            )
            return verify_stock_fallback_evidence(
                identity,
                fallback_location,
                target_boot_id,
            )
        restore_timeout = max(
            1,
            min(
                900,
                int(fallback_deadline - time.monotonic() + 0.999),
            ),
        )
        run_logged(
            [
                str(self.dependencies.bundle_server),
                "restore-fallback",
                str(anchor),
                str(restore_timeout),
            ],
            self.output("fallback-profile-restore.log"),
            environment=child_environment(),
            timeout=(
                restore_timeout + FALLBACK_CONTROL_MARGIN_SECONDS
            ),
        )
        require_log_markers(
            self.output("fallback-profile-restore.log"),
            ("PASS exact Alpine fallback profile ",),
        )
        postmortem_boot_id: str | None = None
        if target_boot_id is not None:
            remaining = fallback_deadline - time.monotonic()
            if remaining < 1:
                fail(
                    "fallback profile restoration consumed the bounded "
                    "postmortem window"
                )
            postmortem_timeout = max(1, min(900, int(remaining)))
            postmortem = self.output("fallback-postmortem.record")
            run_logged(
                [
                    str(self.dependencies.fallback),
                    "capture-ssh-postmortem",
                    str(self.inputs.fallback_known_hosts),
                    str(self.inputs.ssh_key),
                    self.inputs.ssh_public_key_sha256,
                    str(anchor),
                    str(postmortem_timeout),
                    self.profile.candidate,
                    target_boot_id,
                    str(postmortem),
                ],
                self.output("fallback-postmortem.log"),
                environment=child_environment(
                    ALLOW_FALLBACK_SSH_CONTROL="1",
                    ALLOW_FALLBACK_SSH_ATIME_EFFECTS="1",
                    ALLOW_PHONE_CREDENTIAL_USE="1",
                ),
                timeout=(
                    postmortem_timeout
                    + FALLBACK_CONTROL_MARGIN_SECONDS
                ),
            )
            require_log_markers(
                self.output("fallback-postmortem.log"),
                ("PASS bounded fallback pstore evidence captured ",),
            )
            postmortem_boot_id = verify_fallback_postmortem_evidence(
                postmortem,
                anchor,
                self.profile.candidate,
                target_boot_id,
                self.dependencies,
            )
        remaining = fallback_deadline - time.monotonic()
        if remaining < 1:
            if target_boot_id is None:
                fail(
                    "fallback profile restoration consumed the bounded "
                    "fallback window"
                )
            fail(
                "fallback postmortem capture consumed the bounded "
                "fallback window"
            )
        ssh_timeout = max(1, min(900, int(remaining)))
        identity = self.output("fallback-identity.record")
        run_logged(
            [
                str(self.dependencies.fallback),
                "wait-ssh-preflight",
                str(self.inputs.fallback_known_hosts),
                str(self.inputs.ssh_key),
                self.inputs.ssh_public_key_sha256,
                str(self.output("recovery-usb.anchor")),
                str(ssh_timeout),
                str(identity),
            ],
            self.output("fallback-preflight.log"),
            environment=child_environment(
                ALLOW_FALLBACK_SSH_CONTROL="1",
                ALLOW_FALLBACK_SSH_ATIME_EFFECTS="1",
                ALLOW_PHONE_CREDENTIAL_USE="1",
            ),
            timeout=(
                ssh_timeout + FALLBACK_CONTROL_MARGIN_SECONDS
            ),
        )
        metadata = identity.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            fail("fallback identity record metadata is unsafe")
        values = parse_record(identity)
        if tuple(values) != (
            "format",
            "kernel_release",
            "boot_id",
            "usb_location",
            "nonce",
            "thermal_max",
            "record_sha256",
            "signature_sha256",
            "host_pin_sha256",
            "result",
        ):
            fail("fallback identity record fields changed")
        if (
            values["format"] != "rog5-fallback-identity-v2"
            or values["kernel_release"] != FALLBACK_KERNEL
            or not BOOT_ID.fullmatch(values["boot_id"])
            or not USB_LOCATION.fullmatch(values["usb_location"])
            or values["usb_location"].startswith("/")
            or ".." in Path(values["usb_location"]).parts
            or not HEX_ID.fullmatch(values["nonce"])
            or not values["thermal_max"].isascii()
            or not values["thermal_max"].isdecimal()
            or not 0 <= int(values["thermal_max"]) <= 80000
            or any(
                not SHA256.fullmatch(values[name])
                or values[name] == ZERO_SHA256
                for name in (
                    "record_sha256",
                    "signature_sha256",
                    "host_pin_sha256",
                )
            )
            or values["result"] != "PASS"
        ):
            fail("fallback identity record is not exact")
        fallback_boot_id = values["boot_id"]
        if target_boot_id is not None and fallback_boot_id == target_boot_id:
            fail("fallback retained the minimal-headless boot identity")
        if (
            postmortem_boot_id is not None
            and fallback_boot_id != postmortem_boot_id
        ):
            fail("fallback boot identity changed after postmortem capture")
        return fallback_boot_id

    def discover_unknown_intent(
        self,
        path: Path,
        ledger_before: set[str],
    ) -> Intent | None:
        ledger_intent = self.new_ledger_intent(ledger_before)
        intent = parse_any_intent(
            path,
            self.inputs.manifest_sha256,
            self.profile.bundle,
        )
        if intent is not None:
            if ledger_intent is None or ledger_intent != intent:
                fail("control output and durable intent ledger disagree")
            return ledger_intent
        if ledger_intent is not None:
            return ledger_intent
        try:
            payload = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        matches = re.findall(
            r"commit intent remains UNKNOWN "
            r"session=([0-9a-f]{32}) request=([0-9a-f]{32})(?:\s|$)",
            payload,
        )
        if len(matches) != 1:
            return None
        session, request = matches[0]
        result = run_capture(
            [
                str(self.dependencies.recovery_control),
                "show",
                session,
            ],
            environment=child_environment(),
            timeout=self.short_timeout,
            check=False,
        )
        lines = [
            line for line in result.stdout.splitlines() if line.strip()
        ]
        if result.returncode != 0 or len(lines) != 1:
            return None
        try:
            value = canonical_json(lines[0])
            intent = validate_intent(
                value,
                manifest_sha256=self.inputs.manifest_sha256,
                target=self.profile.bundle,
            )
        except (CycleError, json.JSONDecodeError):
            return None
        if intent.session != session or intent.request != request:
            return None
        return intent

    def resolve_intent(self, intent: Intent, outcome: str) -> None:
        if outcome not in {"TARGET_ACCEPTED", "FALLBACK_RETURNED"}:
            fail("invalid lifecycle outcome")
        log = self.output("intent-resolution.log")
        run_logged(
            [
                str(self.dependencies.recovery_control),
                "resolve",
                intent.session,
                intent.request,
                outcome,
            ],
            log,
            environment=child_environment(
                ALLOW_RECOVERY_INTENT_RESOLVE="1"
            ),
            timeout=self.short_timeout,
        )
        try:
            lines = [
                line
                for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeDecodeError) as error:
            raise CycleError("intent resolution log is unreadable") from error
        if len(lines) != 1:
            fail("intent resolution did not return one canonical record")
        record = canonical_json(lines[0])
        if (
            record.get("session") != intent.session
            or record.get("request") != intent.request
            or record.get("state") != "RESOLVED"
            or record.get("outcome") != outcome
            or record.get("manifest_sha256")
            != self.inputs.manifest_sha256
            or record.get("target") != self.profile.bundle
        ):
            fail("resolved intent record is inconsistent")

    def run(self) -> None:
        boot_log = self.output("stable-recovery-boot.log")
        anchor_log = self.output("recovery-usb-anchor.log")
        anchor = self.output("recovery-usb.anchor")
        target_known_hosts = self.output("target-known-hosts")
        bundle_log = self.output("bundle-server.log")
        control_log = self.output("recovery-control.log")
        network_log = self.output("network-root-server.log")
        target_key_log = self.output("target-host-key.log")
        runtime_record = self.output("minimal-headless-runtime.record")
        diagnostic_log = self.output("early-target-diagnostics.log")
        diagnostic_record = self.output("early-target-diagnostics.json")

        bundle_process: ManagedProcess | None = None
        control_process: ManagedProcess | None = None
        network_process: ManagedProcess | None = None
        collector_process: ManagedProcess | None = None
        intent: Intent | None = None
        control_attempted = False
        target_boot_id: str | None = None
        target_accepted = False
        fallback_attempted = False
        fallback_proved = False
        resolved = False
        final_cleanup_attempted = False
        final_cleanup_completed = False
        fallback_contact_deadline: float | None = None
        handoff_token: str | None = None
        ledger_before: set[str] = set()
        recovery_ncm: tuple[InterfaceSnapshot, ...] = ()
        self.verify_power_usb_receipts()
        self.claim_temporary_boot()
        try:
            run_logged(
                [str(self.dependencies.live_gate), "boot"],
                boot_log,
                environment=child_environment(
                    ALLOW_TEMPORARY_BOOT="1",
                    ALLOW_HEADLESS_LIVE_GATE="1",
                    ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE="1",
                ),
                timeout=300,
            )
            run_logged(
                [
                    str(self.dependencies.host_key),
                    "capture-recovery",
                    str(anchor),
                ],
                anchor_log,
                environment=child_environment(
                    ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP="1"
                ),
                timeout=self.short_timeout,
            )
            fallback_contact_deadline = (
                time.monotonic()
                + FALLBACK_CONTACT_START_BUDGET_SECONDS
            )
            if self.profile.diagnostic:
                collector_process = start_logged(
                    "early-target diagnostic collector",
                    [
                        str(self.dependencies.diagnostic_collector),
                        str(anchor),
                        str(diagnostic_record),
                        "120",
                        str(self.diagnostic_capture_timeout),
                        self.profile.candidate,
                    ],
                    diagnostic_log,
                    environment=child_environment(),
                )
                wait_log_marker(
                    collector_process,
                    DIAGNOSTIC_COLLECTOR_READY,
                    timeout=self.short_timeout,
                    poll=self.poll,
                    exact_line=True,
                )
            recovery_ncm = self.wait_recovery_ncm()
            bundle_process = start_logged(
                "recovery bundle server",
                [
                    str(self.dependencies.bundle_server),
                    "serve-progress-deferred",
                    self.profile.bundle,
                    self.inputs.manifest_sha256,
                    str(self.inputs.evidence_dir),
                ],
                bundle_log,
                environment=child_environment(),
            )
            wait_log_marker(
                bundle_process,
                "PASS recovery bundle server ready on "
                "169.254.77.1:8080",
                timeout=self.short_timeout,
                poll=self.poll,
            )
            handoff_token = secrets.token_hex(32)
            ledger_before = self.ledger_inventory()
            control_attempted = True
            control_process = start_logged(
                "stable recovery control",
                [
                    str(self.dependencies.recovery_control),
                    "prepare-commit",
                    self.profile.bundle,
                    self.inputs.manifest_sha256,
                ],
                control_log,
                environment=child_environment(
                    ALLOW_STABLE_RECOVERY_CONTROL="1",
                    ALLOW_ATTENDED_KEXEC="1",
                    ALLOW_NETWORK_ROOT_NFS_HANDOFF="1",
                    ROG5_NFS_HANDOFF_TOKEN=handoff_token,
                    ROG5_NFS_PROFILE=RECOVERY_PROFILE,
                    ROG5_NFS_PACKAGE_SHA256=(
                        self.inputs.root_package_sha256
                    ),
                ),
            )
            self.wait_bundle(
                bundle_process,
                control_process,
                collector_process,
            )
            bundle_process = None
            self.wait_host_clean(recovery_ncm=recovery_ncm)
            if (
                collector_process is not None
                and collector_process.process.poll() is not None
            ):
                fail(
                    "early-target diagnostic collector exited before the "
                    "commit handoff"
                )
            if collector_process is not None:
                require_exact_log_line(
                    diagnostic_log,
                    DIAGNOSTIC_COLLECTOR_READY,
                )

            network_process = start_logged(
                "headless network-root server",
                [
                    str(self.dependencies.network_root_server),
                    "serve",
                    RECOVERY_PROFILE,
                    self.inputs.root_package_sha256,
                    handoff_token,
                ],
                network_log,
                environment=child_environment(
                    ALLOW_HEADLESS_NETWORK_ROOT_SERVER="1"
                ),
            )
            control_status = wait_process(
                control_process,
                self.control_timeout,
            )
            control_process = None
            if control_status != 0:
                intent = self.discover_unknown_intent(
                    control_log,
                    ledger_before,
                )
                fail(
                    "stable recovery control failed after one non-retryable "
                    f"attempt; inspect {control_log}"
                )
            intent, prepare_request = parse_control_log(
                control_log,
                self.inputs.manifest_sha256,
                self.profile.bundle,
            )
            ledger_intent = self.new_ledger_intent(ledger_before)
            if ledger_intent != intent:
                fail("successful control output lacks its durable intent")
            progress = inspect_progress_capture(
                self.output("recovery-progress.capture"),
                bundle=self.profile.bundle,
                manifest_sha256=self.inputs.manifest_sha256,
                session=intent.session,
                prepare_request=prepare_request,
            )
            write_record(
                self.output("recovery-progress-assessment.record"),
                (
                    ("format", "rog5-recovery-progress-assessment-v1"),
                    ("capture_result", progress.capture_result),
                    ("correlation", progress.correlation),
                    ("reason", progress.reason),
                    ("authority", "NONE"),
                ),
            )
            print(
                "INFO recovery progress evidence "
                f"capture={progress.capture_result} "
                f"correlation={progress.correlation} authority=NONE"
            )

            if self.profile.early_probe:
                if collector_process is None:
                    fail("diagnostic collector was not started")
                collector_status = wait_process(
                    collector_process,
                    self.diagnostic_timeout,
                )
                collector_process = None
                if collector_status != 0:
                    fail(
                        "early-target diagnostic collector rejected the "
                        f"target stream; inspect {diagnostic_log}"
                    )
                require_log_markers(
                    diagnostic_log,
                    ("PASS receive-only early-target diagnostic capture ",),
                )
                diagnostic_boot_id = verify_diagnostic_evidence(
                    diagnostic_record,
                    anchor,
                    self.profile.candidate,
                    require_ssh=False,
                    require_power=True,
                )
                target_boot_id = diagnostic_boot_id
            else:
                run_logged(
                    [
                        str(self.dependencies.host_key),
                        "pin-target",
                        str(anchor),
                        str(target_known_hosts),
                        (
                            DIAGNOSTIC_TARGET_PRODUCT
                            if self.profile.diagnostic
                            else TARGET_PRODUCT
                        ),
                    ],
                    target_key_log,
                    environment=child_environment(
                        ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP="1"
                    ),
                    timeout=self.target_key_timeout,
                )
                runtime_profile = self.profile.runtime_profile
                run_logged(
                    [
                        str(self.dependencies.runtime_acceptance),
                        runtime_profile,
                        str(self.inputs.candidate_record),
                        self.inputs.candidate_sha256,
                    ],
                    self.output("runtime-acceptance.log"),
                    environment=child_environment(
                        ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE="1",
                        SSH_KEY=str(self.inputs.ssh_key),
                        TARGET_KNOWN_HOSTS=str(target_known_hosts),
                        EVIDENCE_DIR=str(self.inputs.evidence_dir),
                    ),
                    timeout=self.short_timeout,
                )
                runtime_values = parse_record(runtime_record)
                target_boot_id = runtime_values.get("boot_id")
                if (
                    runtime_values.get("result") != "PASS"
                    or target_boot_id is None
                    or not BOOT_ID.fullmatch(target_boot_id)
                ):
                    fail("minimal-headless runtime record is not accepted")
                target_accepted = True

                if self.profile.diagnostic:
                    if collector_process is None:
                        fail("diagnostic collector was not started")
                    collector_status = wait_process(
                        collector_process,
                        self.diagnostic_timeout,
                    )
                    collector_process = None
                    if collector_status != 0:
                        fail(
                            "early-target diagnostic collector rejected the "
                            f"target stream; inspect {diagnostic_log}"
                        )
                    require_log_markers(
                        diagnostic_log,
                        ("PASS receive-only early-target diagnostic capture ",),
                    )
                    diagnostic_boot_id = verify_diagnostic_evidence(
                        diagnostic_record,
                        anchor,
                        self.profile.candidate,
                    )
                    if diagnostic_boot_id != target_boot_id:
                        fail(
                            "strict SSH and diagnostic stream boot identities differ"
                        )

            network_status = wait_network_process(
                network_process,
                self.dependencies,
                handoff_token,
                self.network_timeout,
            )
            network_process = None
            if network_status != 0:
                fail(
                    "network-root server did not end after target departure; "
                    f"inspect {network_log}"
                )
            require_log_markers(
                network_log,
                (
                    "PASS network-root gadget departed; ending attended "
                    "export",
                    "INFO network-root NFS and runtime firewall state removed",
                ),
            )
            self.require_fallback_contact_budget(fallback_contact_deadline)
            fallback_attempted = True
            self.wait_fallback(target_boot_id)
            fallback_proved = True
            final_cleanup_attempted = True
            self.wait_host_clean(final=True)
            final_cleanup_completed = True
            outcome = (
                "FALLBACK_RETURNED"
                if self.profile.diagnostic
                else "TARGET_ACCEPTED"
            )
            self.resolve_intent(intent, outcome)
            resolved = True
            if self.profile.diagnostic:
                print(
                    "PASS one early-target diagnostic lifecycle captured "
                    "bounded evidence, returned to exact fallback, cleaned "
                    "host state, and resolved its durable intent"
                )
            else:
                print(
                    "PASS one minimal-headless lifecycle was accepted, "
                    "returned to exact fallback, cleaned host state, and "
                    "resolved its durable intent"
                )
        except BaseException as original:
            control_was_started = control_attempted
            if control_process is not None:
                status = control_process.process.poll()
                if status is not None and intent is None:
                    intent = self.discover_unknown_intent(
                        control_log,
                        ledger_before,
                    )
            terminate(control_process)
            control_process = None
            if control_was_started and intent is None:
                intent = self.discover_unknown_intent(
                    control_log,
                    ledger_before,
                )
            terminate(bundle_process)
            bundle_process = None
            cancellation = cancel_network_process(
                network_process,
                self.dependencies,
                handoff_token,
            )
            cleanup_note = ""
            if cancellation:
                cleanup_note = f"; {cancellation}"
            else:
                network_process = None
            recovery_note = ""
            if intent is None:
                if fallback_contact_deadline is None:
                    terminate(collector_process)
                    collector_process = None
                    try:
                        self.wait_host_clean()
                    except Exception as cleanup_error:
                        cleanup_note += (
                            "; host cleanup proof failed: "
                            f"{cleanup_error}"
                        )
                else:
                    fallback_error: BaseException | None = None
                    cleanup_base_error: BaseException | None = None
                    try:
                        if fallback_attempted:
                            fail(
                                "fallback proof was already attempted and "
                                "was not retried"
                            )
                        self.require_fallback_contact_budget(
                            fallback_contact_deadline
                        )
                        fallback_attempted = True
                        self.wait_fallback(None)
                        fallback_proved = True
                    except BaseException as recovery_error:
                        fallback_error = recovery_error
                    terminate(collector_process)
                    collector_process = None
                    try:
                        final_cleanup_attempted = True
                        self.wait_host_clean(final=fallback_proved)
                        final_cleanup_completed = True
                    except BaseException as cleanup_error:
                        cleanup_note += (
                            "; host cleanup proof failed: "
                            f"{cleanup_error}"
                        )
                        if not isinstance(cleanup_error, Exception):
                            cleanup_base_error = cleanup_error
                    if fallback_error is None:
                        recovery_note = (
                            "; exact fallback returned after the pre-commit "
                            "failure; no commit intent existed"
                        )
                        if final_cleanup_completed:
                            recovery_note += "; host cleanup proof passed"
                    else:
                        recovery_note = (
                            "; pre-commit fallback proof failed: "
                            f"{fallback_error}"
                        )
                        if final_cleanup_completed:
                            recovery_note += "; host cleanup proof passed"
                    if cleanup_base_error is not None:
                        raise cleanup_base_error
                    if fallback_error is not None:
                        if not isinstance(fallback_error, Exception):
                            raise fallback_error
            if intent is not None and not resolved:
                try:
                    if not fallback_proved:
                        if fallback_attempted:
                            fail(
                                "fallback proof was already attempted and "
                                "was not retried"
                            )
                        self.require_fallback_contact_budget(
                            fallback_contact_deadline
                        )
                        fallback_attempted = True
                        self.wait_fallback(target_boot_id)
                        fallback_proved = True
                    if network_process is not None:
                        network_status = wait_network_process(
                            network_process,
                            self.dependencies,
                            handoff_token,
                            self.short_timeout,
                        )
                        network_process = None
                        if network_status not in (0, 130):
                            fail(
                                "network-root server did not exit cleanly "
                                f"after fallback: {network_status}"
                            )
                    if not final_cleanup_completed:
                        if final_cleanup_attempted:
                            fail(
                                "final host cleanup proof was already "
                                "attempted and was not retried"
                            )
                        final_cleanup_attempted = True
                        self.wait_host_clean(final=True)
                        final_cleanup_completed = True
                    outcome = (
                        "TARGET_ACCEPTED"
                        if target_accepted
                        else "FALLBACK_RETURNED"
                    )
                    self.resolve_intent(intent, outcome)
                    resolved = True
                    recovery_note = (
                        f"; exact fallback returned and intent resolved as "
                        f"{outcome}"
                    )
                except BaseException as recovery_error:
                    recovery_note = (
                        "; commit intent remains UNKNOWN because fallback or "
                        f"cleanup proof failed: {recovery_error}"
                    )
            if isinstance(original, KeyboardInterrupt):
                raise
            raise CycleError(
                f"{original}{recovery_note}{cleanup_note}"
            ) from original
        finally:
            terminate(collector_process)
            terminate(control_process)
            terminate(bundle_process)
            self.output("recovery-progress.stop").unlink(missing_ok=True)
            cancel_network_process(
                network_process,
                self.dependencies,
                handoff_token,
            )


def require_guards() -> None:
    missing = [
        name for name in FULL_GUARDS if os.environ.get(name) != "1"
    ]
    if missing:
        fail(
            "one-shot lifecycle requires exact fresh guards: "
            + ", ".join(missing)
        )


def require_key_guards() -> None:
    missing = [
        name for name in KEY_GUARDS if os.environ.get(name) != "1"
    ]
    if missing:
        fail(
            "deployment-key admission requires exact fresh guards: "
            + ", ".join(missing)
        )


def main(arguments: list[str]) -> int:
    requested = arguments[0] if len(arguments) == 1 else ""
    actions = {
        "key-preflight": ("key-preflight", STANDARD_CYCLE_PROFILE),
        "preflight": ("preflight", STANDARD_CYCLE_PROFILE),
        "run": ("run", STANDARD_CYCLE_PROFILE),
        "diagnostic-key-preflight": (
            "key-preflight",
            DIAGNOSTIC_CYCLE_PROFILE,
        ),
        "diagnostic-preflight": ("preflight", DIAGNOSTIC_CYCLE_PROFILE),
        "diagnostic-run": ("run", DIAGNOSTIC_CYCLE_PROFILE),
        "core-key-preflight": ("key-preflight", CORE_CYCLE_PROFILE),
        "core-preflight": ("preflight", CORE_CYCLE_PROFILE),
        "core-run": ("run", CORE_CYCLE_PROFILE),
        "power-usb-key-preflight": (
            "key-preflight",
            POWER_USB_CYCLE_PROFILE,
        ),
        "power-usb-preflight": ("preflight", POWER_USB_CYCLE_PROFILE),
        "power-usb-run": ("run", POWER_USB_CYCLE_PROFILE),
    }
    if requested not in actions:
        fail(
            "usage: run-minimal-headless-live-cycle.py "
            "key-preflight | preflight | run | diagnostic-key-preflight | "
            "diagnostic-preflight | diagnostic-run | power-usb-key-preflight | "
            "power-usb-preflight | power-usb-run"
        )
    offline_test_root = os.environ.get("ROG5_LIVE_CYCLE_TEST_ROOT")
    offline_harness_requested = (
        os.environ.get("ROG5_LIVE_CYCLE_OFFLINE_TEST") == "1"
        and isinstance(offline_test_root, str)
        and bool(offline_test_root)
        and Path(offline_test_root).is_absolute()
    )
    # Dependencies.from_environment() subsequently resolves this root
    # strictly, rejects root execution, and routes every executable and
    # mutable host path into the fixture. These markers only select that
    # fail-closed harness; they do not themselves claim isolation.
    if (
        requested.startswith("diagnostic-")
        and not offline_harness_requested
        and DIAGNOSTIC_LIVE_STATUS != "admitted"
    ):
        fail(
            "no diagnostic recovery lifecycle is admitted; Generation-12 "
            f"is {DIAGNOSTIC_LIVE_STATUS} and must not be retried"
        )
    action, profile = actions[requested]
    if requested.startswith("diagnostic-") and offline_harness_requested:
        profile = LEGACY_DIAGNOSTIC_CYCLE_PROFILE
    if action == "run":
        require_guards()
    else:
        require_key_guards()
    dependencies = Dependencies.from_environment()
    fixed_executable(dependencies.git, offline=dependencies.offline)
    verify_repository_checkpoint(dependencies.git)
    admission = parse_admission_inputs(profile)
    admitted = verify_key_admission(dependencies, admission, profile)
    if action == "key-preflight":
        print(
            "PASS deployment SSH key matches one non-fixture v3 "
            f"package/{profile.candidate}/runtime-manifest chain; no phone or "
            "privileged host action occurred"
        )
        return 0
    inputs = parse_inputs(admission, admitted, profile)
    cycle = LiveCycle(dependencies, inputs, profile)
    if action == "run":
        if os.environ.get("ROG5_EXTERNAL_BOOT_CLAIM", "0") == "1":
            cycle.assert_temporary_boot_claim_entered()
        else:
            cycle.assert_temporary_boot_unconsumed()
    cycle.preflight()
    if action == "preflight":
        print(
            f"PASS {profile.candidate} lifecycle preflight is clean; the "
            "deployment key was admitted locally, and no phone boot, "
            "payload transfer, SSH connection, or privileged server was "
            "started"
        )
        return 0
    if profile == POWER_USB_CYCLE_PROFILE:
        cycle.capture_stock_fallback_preboot()
    cycle.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        CycleError,
        json.JSONDecodeError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
