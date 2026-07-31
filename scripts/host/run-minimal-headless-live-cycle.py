#!/usr/bin/env python3
"""Run one guarded recovery-to-headless-to-fallback lifecycle."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import subprocess
import sys
import time
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
CANDIDATE = "headless-ssh-network-root-v3"
BUNDLE = "headless-ssh-network-root-v3-r2"
RECOVERY_PROFILE = "headless-ssh-deployment-v3"
FALLBACK_KERNEL = "5.4.134-qgki-perf-00001-g6c308144c23e"
FALLBACK_CONTROL_MARGIN_SECONDS = 120
FALLBACK_CONTACT_START_BUDGET_SECONDS = 3600
ZERO_SHA256 = "0" * 64
CONSUMED_MANIFESTS = {
    "457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e",
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SSH_FINGERPRINT = re.compile(r"SHA256:[A-Za-z0-9+/]{43}\Z")
HEX_ID = re.compile(r"[0-9a-f]{32}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
USB_LOCATION = re.compile(r"[A-Za-z0-9._:/+-]{1,512}\Z")
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
    "ROG5_LIVE_CYCLE_OFFLINE_TEST",
    "ROG5_LIVE_CYCLE_TEST_ROOT",
)
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
    "minimal-headless-runtime.record",
    "fallback-identity.record",
    "fallback-preflight.log",
    "intent-resolution.log",
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
    fallback: Path
    key_admission: Path
    handoff_marker: Path
    network_service_state: Path
    export_mount: Path
    nfs_exports: Path
    nfs_threads: Path
    ip_nonlocal_bind: Path
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
                fallback=root / "fallback-acm-control.py",
                key_admission=(
                    root / "verify-headless-ssh-v2-key-admission.py"
                ),
                handoff_marker=state / "nfs-ready",
                network_service_state=root / "nfs-state",
                export_mount=state / "export-mount",
                nfs_exports=state / "nfs-exports",
                nfs_threads=state / "nfs-threads",
                ip_nonlocal_bind=state / "ip-nonlocal-bind",
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
            fallback=REPO / "scripts/host/fallback-acm-control.py",
            key_admission=(
                REPO
                / "scripts/host/"
                "verify-headless-ssh-v2-key-admission.py"
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


def parse_admission_inputs() -> AdmissionInputs:
    manifest = os.environ.get("MANIFEST_SHA256", "")
    if not SHA256.fullmatch(manifest) or manifest == ZERO_SHA256:
        fail("MANIFEST_SHA256 must be one nonzero lowercase SHA-256")
    if manifest in CONSUMED_MANIFESTS:
        fail(
            "MANIFEST_SHA256 identifies a consumed live payload; build "
            "and pin a fresh successor instead of retrying it"
        )
    if os.environ.get("BUNDLE") != BUNDLE:
        fail(f"BUNDLE must be exactly {BUNDLE}")
    if (
        os.environ.get("ROG5_STABLE_RECOVERY_PROFILE")
        != RECOVERY_PROFILE
    ):
        fail(
            "ROG5_STABLE_RECOVERY_PROFILE must select the headless SSH "
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
        str(bundle_root / BUNDLE / "manifest"),
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
    timeout_value = os.environ.get("ROG5_FALLBACK_TIMEOUT", "750")
    if (
        not timeout_value.isascii()
        or not timeout_value.isdecimal()
        or not 600 <= int(timeout_value) <= 900
    ):
        fail("ROG5_FALLBACK_TIMEOUT must be between 600 and 900 seconds")
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
        or values["candidate"] != CANDIDATE
        or values["bundle"] != BUNDLE
        or values["profile"] != "network-root-v1"
        or values["build_profile"] != "headless-ssh-v2"
        or values["target_id"] != "headless-ssh-network-root"
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
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = managed.log.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            payload = ""
        if marker in payload:
            return
        status = managed.process.poll()
        if status is not None:
            fail(
                f"{managed.name} exited with status {status} before its "
                f"ready marker; inspect {managed.log}"
            )
        time.sleep(poll)
    fail(f"{managed.name} did not publish its bounded ready marker")


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
) -> Intent:
    session = value.get("session")
    request = value.get("request")
    if (
        not isinstance(session, str)
        or not HEX_ID.fullmatch(session)
        or not isinstance(request, str)
        or not HEX_ID.fullmatch(request)
        or value.get("manifest_sha256") != manifest_sha256
        or value.get("target") != BUNDLE
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


def parse_control_log(path: Path, manifest_sha256: str) -> Intent:
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
    if (
        prepared.get("result") != "PREPARED"
        or prepared.get("state") != "PREPARED"
        or prepared.get("prepared_bundle") != BUNDLE
        or prepared.get("manifest_sha256") != manifest_sha256
        or prepared.get("watchdog") != "ARMED"
    ):
        fail("recovery PREPARE evidence is inconsistent")
    if (
        committed.get("result") != "CLAIMED"
        or committed.get("state") != "CLAIMED"
        or committed.get("manifest_sha256") != manifest_sha256
        or committed.get("watchdog") != "ARMED"
        or committed.get("execution_started") != "NO"
    ):
        fail("recovery COMMIT evidence is inconsistent")
    intent = validate_intent(
        intent_value,
        manifest_sha256=manifest_sha256,
    )
    if (
        prepared.get("session") != intent.session
        or committed.get("session") != intent.session
        or committed.get("request") != intent.request
        or committed.get("commit_request") != intent.request
    ):
        fail("recovery transaction and host intent do not correlate")
    return intent


def parse_any_intent(path: Path, manifest_sha256: str) -> Intent | None:
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
                )
        except (CycleError, json.JSONDecodeError):
            continue
    return None


def parse_record(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise CycleError(f"cannot read private record: {path}") from error
    for line in lines:
        if "=" not in line:
            fail(f"private record is not canonical: {path}")
        name, value = line.split("=", 1)
        if not name or name in values:
            fail(f"private record has a duplicate field: {path}")
        values[name] = value
    return values


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
    def __init__(self, dependencies: Dependencies, inputs: Inputs):
        self.dependencies = dependencies
        self.inputs = inputs
        self.poll = 0.02 if dependencies.offline else 0.25
        self.short_timeout = 4 if dependencies.offline else 120
        self.bundle_timeout = 5 if dependencies.offline else 95
        self.control_timeout = 5 if dependencies.offline else 320
        self.network_timeout = 8 if dependencies.offline else 735
        self.fallback_timeout = (
            5 if dependencies.offline else inputs.fallback_timeout
        )
        self.host_snapshot: HostSnapshot | None = None

    def output(self, name: str) -> Path:
        return self.inputs.evidence_dir / name

    def verify_repository(self) -> None:
        verify_repository_checkpoint(self.dependencies.git)

    def ledger_root(self) -> Path:
        state_home = os.environ.get("XDG_STATE_HOME")
        if state_home:
            base = Path(state_home)
            if not base.is_absolute():
                fail("XDG_STATE_HOME must be absolute for lifecycle intents")
        else:
            base = Path.home() / ".local" / "state"
        return base / "rog5-recovery-intents"

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
        )
        if path.name != f"{intent.session}.json":
            fail("new durable intent path does not match its session")
        return intent

    def firewall_empty(self) -> bool:
        target = run_capture(
            [
                str(self.dependencies.firewall),
                "--zone=drop",
                "--list-all",
            ]
        ).stdout.splitlines()
        targets = [
            line.split(":", 1)[1].strip()
            for line in target
            if line.strip().startswith("target:")
        ]
        if targets != ["DROP"]:
            fail("drop firewall zone is not drop-by-default")
        queries = (
            "--list-interfaces",
            "--list-sources",
            "--list-services",
            "--list-ports",
            "--list-protocols",
            "--list-source-ports",
            "--list-forward-ports",
            "--list-icmp-blocks",
            "--list-rich-rules",
        )
        for query in queries:
            result = run_capture(
                [
                    str(self.dependencies.firewall),
                    "--zone=drop",
                    query,
                ]
            )
            if result.stdout.strip():
                fail("drop firewall zone retains lifecycle state")
        masquerade = run_capture(
            [
                str(self.dependencies.firewall),
                "--zone=drop",
                "--query-masquerade",
            ],
            check=False,
        )
        if masquerade.returncode == 0:
            fail("drop firewall zone has masquerading enabled")
        if masquerade.returncode not in (1,):
            fail("cannot inspect drop-zone masquerading state")
        forward = run_capture(
            [
                str(self.dependencies.firewall),
                "--zone=drop",
                "--query-forward",
            ],
            check=False,
        )
        if forward.returncode not in (0, 1):
            fail("cannot inspect drop-zone forwarding state")
        zones_result = run_capture(
            [str(self.dependencies.firewall), "--get-zones"]
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
        for zone in zones:
            rules = [
                line.strip()
                for line in run_capture(
                [
                    str(self.dependencies.firewall),
                    f"--zone={zone}",
                    "--list-rich-rules",
                ]
                ).stdout.splitlines()
                if line.strip()
            ]
            if forbidden_rules.intersection(rules):
                fail(f"firewall zone {zone} retains a lifecycle drop rule")
        return forward.returncode == 0

    def capture_host_snapshot(self) -> HostSnapshot:
        try:
            ip_nonlocal = self.dependencies.ip_nonlocal_bind.read_text(
                encoding="ascii"
            ).strip()
        except (OSError, UnicodeDecodeError) as error:
            raise CycleError("cannot inspect ip_nonlocal_bind") from error
        if ip_nonlocal not in {"0", "1"}:
            fail("ip_nonlocal_bind is not canonical")
        return HostSnapshot(
            firewall_forward=self.firewall_empty(),
            ip_nonlocal_bind=ip_nonlocal,
        )

    def rog5_ncm_interfaces(self) -> tuple[InterfaceSnapshot, ...]:
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
                or not properties.get("ID_MODEL", "").startswith("ROG5_")
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
                ]
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
                    check=False,
                ).stdout.splitlines()
                if line.strip()
            ]
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
                    check=False,
                )
                managed = managed_result.stdout.strip()
            if managed_result.returncode != 0 or managed not in {"yes", "no"}:
                fail("cannot inspect NetworkManager ownership of ROG5 link")
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
        while time.monotonic() < deadline:
            current = tuple(
                item
                for item in self.rog5_ncm_interfaces()
                if (
                    item.product == "ROG5_recovery"
                    and item.addresses == ("169.254.77.1/30",)
                    and item.network_manager_managed == "yes"
                    and item.firewall_zone != "drop"
                )
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

    def verify_host_clean(self, *, final: bool = False) -> None:
        for path in (
            self.dependencies.handoff_marker,
            self.dependencies.network_service_state,
            self.dependencies.export_mount,
        ):
            if path.exists() or path.is_symlink():
                fail(f"host lifecycle residue remains: {path}")
        for port in ("8080", "2049", "32767"):
            result = run_capture(
                [
                    str(self.dependencies.ss),
                    "-H",
                    "-lntu4",
                    f"sport = :{port}",
                ]
            )
            if result.stdout.strip():
                fail(f"host listener remains on TCP port {port}")
        export_descriptor = -1
        try:
            export_descriptor = os.open(
                self.dependencies.nfs_exports,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            )
            export_metadata = os.fstat(export_descriptor)
            export_payload = os.read(export_descriptor, 1024 * 1024 + 1)
            current_metadata = self.dependencies.nfs_exports.lstat()
        except OSError as error:
            raise CycleError("cannot inspect host NFS exports") from error
        finally:
            if export_descriptor >= 0:
                os.close(export_descriptor)
        expected_owner = os.geteuid() if self.dependencies.offline else 0
        expected_group = os.getegid() if self.dependencies.offline else 0
        if (
            not stat.S_ISREG(export_metadata.st_mode)
            or export_metadata.st_uid != expected_owner
            or export_metadata.st_gid != expected_group
            or stat.S_IMODE(export_metadata.st_mode) not in {0o600, 0o644}
            or current_metadata.st_dev != export_metadata.st_dev
            or current_metadata.st_ino != export_metadata.st_ino
            or len(export_payload) > 1024 * 1024
        ):
            fail("host NFS export table metadata is unsafe")
        if export_payload.strip():
            fail("host retains an NFS export")
        rog5_interfaces = self.rog5_ncm_interfaces()
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
            ]
        ).stdout.splitlines()
        for line in address_lines:
            fields = line.split()
            if len(fields) >= 4 and fields[2] == "inet":
                if fields[3] == "169.254.77.1/30":
                    if len(fields) < 2 or fields[1] not in (
                        allowed_shared_addresses
                    ):
                        fail(
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
        current = self.capture_host_snapshot()
        if self.host_snapshot is None:
            self.host_snapshot = current
        elif current != self.host_snapshot:
            fail("host firewall or nonlocal-bind state was not restored")

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
        for name in OUTPUT_NAMES:
            path = self.output(name)
            if path.exists() or path.is_symlink():
                fail(f"refusing existing private lifecycle output: {path}")
        self.verify_host_clean()
        run_capture(
            [
                str(self.dependencies.bundle_server),
                "preflight",
                BUNDLE,
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
            environment=child_environment(),
            timeout=300,
        )
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
    ) -> None:
        deadline = time.monotonic() + self.bundle_timeout
        while time.monotonic() < deadline:
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
                    ),
                )
                return
            control_status = control.process.poll()
            if control_status is not None:
                fail(
                    "recovery control exited before the one-transfer bundle "
                    f"server cleaned up; inspect {control.log}"
                )
            time.sleep(self.poll)
        terminate(bundle)
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

    def wait_fallback(self, target_boot_id: str | None) -> str:
        identity = self.output("fallback-identity.record")
        run_logged(
            [
                str(self.dependencies.fallback),
                "wait-ssh-preflight",
                str(self.inputs.fallback_known_hosts),
                str(self.inputs.ssh_key),
                self.inputs.ssh_public_key_sha256,
                str(self.output("recovery-usb.anchor")),
                str(self.inputs.fallback_timeout),
                str(identity),
            ],
            self.output("fallback-preflight.log"),
            environment=child_environment(
                ALLOW_FALLBACK_SSH_CONTROL="1",
                ALLOW_FALLBACK_SSH_ATIME_EFFECTS="1",
                ALLOW_PHONE_CREDENTIAL_USE="1",
            ),
            timeout=(
                self.fallback_timeout + FALLBACK_CONTROL_MARGIN_SECONDS
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
        return fallback_boot_id

    def discover_unknown_intent(
        self,
        path: Path,
        ledger_before: set[str],
    ) -> Intent | None:
        ledger_intent = self.new_ledger_intent(ledger_before)
        intent = parse_any_intent(path, self.inputs.manifest_sha256)
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
            or record.get("target") != BUNDLE
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

        bundle_process: ManagedProcess | None = None
        control_process: ManagedProcess | None = None
        network_process: ManagedProcess | None = None
        intent: Intent | None = None
        control_attempted = False
        target_boot_id: str | None = None
        target_accepted = False
        fallback_attempted = False
        fallback_proved = False
        resolved = False
        fallback_contact_deadline: float | None = None
        handoff_token: str | None = None
        ledger_before: set[str] = set()
        recovery_ncm: tuple[InterfaceSnapshot, ...] = ()
        try:
            run_logged(
                [str(self.dependencies.live_gate), "boot"],
                boot_log,
                environment=child_environment(
                    ALLOW_TEMPORARY_BOOT="1",
                    ALLOW_HEADLESS_LIVE_GATE="1",
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
            recovery_ncm = self.wait_recovery_ncm()

            bundle_process = start_logged(
                "recovery bundle server",
                [
                    str(self.dependencies.bundle_server),
                    BUNDLE,
                    self.inputs.manifest_sha256,
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
                    BUNDLE,
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
            self.wait_bundle(bundle_process, control_process)
            bundle_process = None
            self.verify_host_clean()
            if self.rog5_ncm_interfaces() != recovery_ncm:
                fail("bundle server did not restore exact recovery NCM state")

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
            intent = parse_control_log(
                control_log,
                self.inputs.manifest_sha256,
            )
            ledger_intent = self.new_ledger_intent(ledger_before)
            if ledger_intent != intent:
                fail("successful control output lacks its durable intent")

            run_logged(
                [
                    str(self.dependencies.host_key),
                    "pin-target",
                    str(anchor),
                    str(target_known_hosts),
                ],
                target_key_log,
                environment=child_environment(
                    ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP="1"
                ),
                timeout=self.short_timeout,
            )
            run_logged(
                [
                    str(self.dependencies.runtime_acceptance),
                    RECOVERY_PROFILE,
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
            self.verify_host_clean(final=True)
            self.resolve_intent(intent, "TARGET_ACCEPTED")
            resolved = True
            print(
                "PASS one minimal-headless lifecycle was accepted, returned "
                "to exact fallback, cleaned host state, and resolved its "
                "durable intent"
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
            if intent is None:
                try:
                    self.verify_host_clean()
                except Exception as cleanup_error:
                    cleanup_note += (
                        "; host cleanup proof failed: "
                        f"{cleanup_error}"
                    )
            recovery_note = ""
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
                    self.verify_host_clean(final=True)
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
            terminate(control_process)
            terminate(bundle_process)
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
    action = arguments[0] if len(arguments) == 1 else ""
    if action not in {"key-preflight", "preflight", "run"}:
        fail(
            "usage: run-minimal-headless-live-cycle.py "
            "key-preflight | preflight | run"
        )
    if action == "run":
        require_guards()
    else:
        require_key_guards()
    dependencies = Dependencies.from_environment()
    fixed_executable(dependencies.git, offline=dependencies.offline)
    verify_repository_checkpoint(dependencies.git)
    admission = parse_admission_inputs()
    admitted = verify_key_admission(dependencies, admission)
    if action == "key-preflight":
        print(
            "PASS deployment SSH key matches one non-fixture v3 "
            "package/candidate/runtime-manifest chain; no phone or "
            "privileged host action occurred"
        )
        return 0
    inputs = parse_inputs(admission, admitted)
    cycle = LiveCycle(dependencies, inputs)
    cycle.preflight()
    if action == "preflight":
        print(
            "PASS minimal-headless lifecycle preflight is clean; the "
            "deployment key was admitted locally, and no phone boot, "
            "payload transfer, SSH connection, or privileged server was "
            "started"
        )
        return 0
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
