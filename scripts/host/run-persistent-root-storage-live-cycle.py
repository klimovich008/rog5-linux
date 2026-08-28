#!/usr/bin/env python3
"""Run one RAM-only local-image-root critical-path lifecycle."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time
from typing import NamedTuple


REPO = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CYCLE = load_module(
    "rog5_shared_live_cycle",
    REPO / "scripts/host/run-minimal-headless-live-cycle.py",
)
PIN = load_module(
    "rog5_shared_host_key_pin",
    REPO / "scripts/host/pin-minimal-headless-host-key.py",
)
STOCK = load_module(
    "rog5_stock_fallback",
    REPO / "scripts/host/wait-stock-android-fallback.py",
)

PROFILE_ID = "persistent-native-root-v5-generation230-live-v1"
BUNDLE = "persistent-native-root-v5"
MANIFEST_SHA256 = (
    "2454db0ff2a558d8764c824f0a6c4d82f0212e39714d540163a9f7a865c5d9da"
)
RECOVERY_SHA256 = (
    "a87d564c9249a611bdc38a52cb28cc25bde6743ca0d2e98529c12c2ba7361c9c"
)
TRUST_KEY_SHA256 = (
    "cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054"
)
HOST_VERIFIER_SHA256 = (
    "04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29"
)
CLAIM_RECORD = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile="
    b"persistent-native-root-v5-generation230-live-v1\n"
    b"candidate=persistent-native-root-v5\n"
    b"manifest_sha256="
    b"2454db0ff2a558d8764c824f0a6c4d82f0212e39714d540163a9f7a865c5d9da\n"
    b"state=BOOT_CLAIMED\n"
)
CYCLE.CLAIM_CONSUMER.CLAIMS[PROFILE_ID] = CLAIM_RECORD
CLAIM_ENTRYPOINT = (
    REPO
    / "scripts/host/consume-exact-boot-claim.py"
)
TARGET_RELEASE = "7.1.4-g359318de534f"
TARGET_PRODUCT = "ROG5 persistent root"
TARGET_UDEV_MODEL = "ROG5_persistent_root"
HOST_PROFILE = "rog5-fallback-usb-ssh"
LIVE_ROOT = (
    REPO
    / "build/persistent-native-root-v5-generation230-20260828-r1"
)
COMPONENT_ROOT = (
    REPO
    / "build/storage-layout-stage2-mainline-readonly-v2-recovery-components-20260826-r1"
)
TRUST_KEY = COMPONENT_ROOT / "ephemeral-public.raw"
BUNDLE_ROOT = Path("/var/lib/rog5-recovery-bundles")
TARGET_WAIT_SECONDS = 450
FALLBACK_TIMEOUT_SECONDS = 930
AUTHENTICATED_SSH_ATTEMPT_SECONDS = 20
AUTHENTICATED_SSH_READY_MARKER = "ROG5_AUTHENTICATED_SSH_READY_V1"
AUTHENTICATED_SSH_COMMAND = (
    f"printf '%s\\n' '{AUTHENTICATED_SSH_READY_MARKER}'"
)
SSH_DIAGNOSTIC_PORT = 8078
SSH_DIAGNOSTIC_MAX_BYTES = 16384
SSH_CLIENT_MAX_BYTES = 32768
SSH_CLIENT_RECORD_MAX_BYTES = 131072
SSH_DIAGNOSTIC_FIELDS = (
    "format",
    "target_release",
    "boot_id",
    "auth_event",
    "shadow_class",
    "shadow_metadata",
    "lower_shadow_class",
    "lower_shadow_metadata",
    "root_metadata",
    "root_ssh_metadata",
    "authorized_keys_metadata",
    "run_nologin",
    "etc_nologin",
    "system_state",
    "early_sshd",
    "sshd_usepam",
    "sshd_permitrootlogin",
    "sshd_pubkeyauthentication",
    "sshd_passwordauthentication",
    "sshd_kbdinteractiveauthentication",
    "sshd_persourcepenalties_sha256",
    "log_bytes",
    "log_sha256",
    "log_tail_hex",
    "result",
)
UFS_LINK_SNAPSHOT_COMMAND = r"""
set -eu
printf '%s\n' 'format=rog5-ufs-link-snapshot-v1'
printf '%s\n' '=== udc ==='
for path in /sys/class/udc/*/current_speed /sys/class/udc/*/state; do
    [ ! -r "$path" ] || { printf '%s=' "$path"; cat "$path"; }
done
printf '%s\n' '=== scsi ==='
for path in /sys/class/scsi_device/*/device/queue_depth; do
    [ ! -r "$path" ] || { printf '%s=' "$path"; cat "$path"; }
done
printf '%s\n' '=== block ==='
for path in /sys/class/block/sd*/queue/logical_block_size \
    /sys/class/block/sd*/queue/max_sectors_kb \
    /sys/class/block/sd*/queue/nr_requests \
    /sys/class/block/sd*/queue/write_cache; do
    [ ! -r "$path" ] || { printf '%s=' "$path"; cat "$path"; }
done
printf '%s\n' '=== ufs-dmesg ==='
dmesg | grep -Ei 'ufs|gear|lane|pwr' | tail -80 || true
printf '%s\n' 'result=PASS'
""".strip()
STAGE_PORT = 8079
STAGE_RECORD_MAX_BYTES = 512
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TREE_RECORD = re.compile(
    r"ROG5_NATIVE_TREE_V1 item=([a-z-]+) status=(PASS|MISMATCH) "
    r"metadata=([^ ]+) sha256=([0-9a-f]{64}|none|error)\Z"
)
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)

PROFILE = CYCLE.CycleProfile(
    candidate=BUNDLE,
    bundle=BUNDLE,
    bundle_profile="persistent-root-ro-v1",
    target_id=BUNDLE,
    admission_profile="persistent-native-root-v5",
    recovery_profile=PROFILE_ID,
    runtime_profile="persistent-native-root-v5",
    build_profile="persistent-native-root-v5",
    diagnostic=False,
)

RUNTIME_COMMAND = r"""
set -eu
ready=/run/rog5-p2-ready
[ -f "$ready" ]
printf '%s\n' 'format=rog5-native-root-runtime-v1'
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='; awk '{ print $1 }' /proc/uptime
cat "$ready"
[ "$(cat /proc/1/comm)" = systemd ]
[ "$(systemctl is-system-running)" = running ]
systemctl is-active --quiet rog5-early-sshd.service
systemctl is-active --quiet rog5-p2-ready.service
failed=$(systemctl --failed --no-legend --plain | awk 'NF { count++ } END { print count + 0 }')
printf 'failed_units=%s\n' "$failed"
[ "$failed" -eq 0 ]
printf '%s\n' 'result=PASS'
""".strip()

class PersistentCycleError(RuntimeError):
    """One bounded local-root lifecycle failed."""


def fail(message: str) -> None:
    raise PersistentCycleError(message)


class StageRecord(NamedTuple):
    boot_id: str
    sequence: int
    stage: str
    state: str
    detail: str
    payload: bytes


class TreeEvidence(NamedTuple):
    disposition: str
    mismatches: tuple[str, ...]


STAGES = {
    "kernel-verified",
    "power-usb",
    "ufs-ready",
    "userdata-resolved",
    "storage-locked",
    "userdata-mount",
    "image-resolved",
    "image-mount",
    "root-verify",
    "ufs-health",
    "overlay",
    "runtime",
    "final-storage",
    "switch-root",
}
STAGE_STATES = {"ENTER", "PASS", "FAIL"}
WATCHDOG_OBSERVER_DETAIL = re.compile(
    r"wdt-r[0-9]{1,12}-e[0-9a-f]{8}-s[0-9a-f]{8}-"
    r"b[0-9a-f]{8}-i[0-9a-f]{8}\Z"
)
SOFTDOG_PROBE_DETAIL = "softdog-armed-20"


def parse_stage_record(payload: bytes) -> StageRecord:
    if len(payload) > STAGE_RECORD_MAX_BYTES:
        fail("target stage record exceeds its fixed bound")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise PersistentCycleError("target stage record is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        fail("target stage record framing is not exact")
    lines = text.splitlines()
    if len(lines) != 7:
        fail("target stage record has the wrong field count")
    if lines[0] != "format=rog5-persistent-root-stage-v2":
        fail("target stage record format changed")
    if lines[1] != f"target_release={TARGET_RELEASE}":
        fail("target stage record release changed")
    boot_id = lines[2].removeprefix("boot_id=")
    if lines[2] != f"boot_id={boot_id}" or not BOOT_ID.fullmatch(boot_id):
        fail("target stage record boot identity is invalid")
    sequence_text = lines[3].removeprefix("sequence=")
    if not re.fullmatch(r"[1-9][0-9]{0,2}", sequence_text):
        fail("target stage record sequence is invalid")
    stage = lines[4].removeprefix("stage=")
    state = lines[5].removeprefix("state=")
    detail = lines[6].removeprefix("detail=")
    if lines[4] != f"stage={stage}" or stage not in STAGES:
        fail("target stage record stage is invalid")
    if lines[5] != f"state={state}" or state not in STAGE_STATES:
        fail("target stage record state is invalid")
    if (
        lines[6] != f"detail={detail}"
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?", detail)
    ):
        fail("target stage record detail is invalid")
    return StageRecord(
        boot_id=boot_id,
        sequence=int(sequence_text),
        stage=stage,
        state=state,
        detail=detail,
        payload=payload,
    )


def require_stage_successor(previous: StageRecord, current: StageRecord) -> None:
    if current.boot_id != previous.boot_id:
        fail("target stage record boot identity changed")
    if current.sequence == previous.sequence:
        if current != previous:
            fail("target stage record changed within one sequence")
        return
    if current.sequence < previous.sequence:
        fail("target stage record sequence regressed")


def exact_environment() -> dict[str, str]:
    required = {
        "FASTBOOT_SERIAL": os.environ.get("FASTBOOT_SERIAL", ""),
        "ROG5_EXPECTED_USB_LOCATION": os.environ.get(
            "ROG5_EXPECTED_USB_LOCATION", ""
        ),
    }
    for name, value in required.items():
        if not value:
            fail(f"set {name} for the exact connected phone")
    return CYCLE.child_environment(
        LIVE_BUILD_ROOT=str(LIVE_ROOT),
        RECOVERY_COMPONENT_ROOT=str(COMPONENT_ROOT),
        TRUST_KEY=str(TRUST_KEY),
        BUNDLE_ROOT=str(BUNDLE_ROOT),
        BUNDLE=BUNDLE,
        RECOVERY_SHA256=RECOVERY_SHA256,
        TRUST_KEY_SHA256=TRUST_KEY_SHA256,
        MANIFEST_SHA256=MANIFEST_SHA256,
        HOST_VERIFIER_SHA256=HOST_VERIFIER_SHA256,
        ROG5_STABLE_RECOVERY_PROFILE=PROFILE_ID,
        FASTBOOT_SERIAL=required["FASTBOOT_SERIAL"],
        ROG5_EXPECTED_USB_LOCATION=required["ROG5_EXPECTED_USB_LOCATION"],
    )


def exact_inputs() -> CYCLE.Inputs:
    ssh_key = CYCLE.caller_file(os.environ.get("SSH_KEY", ""), "SSH_KEY")
    known_hosts = CYCLE.caller_file(
        os.environ.get("FALLBACK_KNOWN_HOSTS", ""),
        "FALLBACK_KNOWN_HOSTS",
    )
    evidence = CYCLE.caller_directory(os.environ.get("EVIDENCE_DIR", ""))
    public_hash = os.environ.get("SSH_PUBLIC_KEY_SHA256", "")
    if not SHA256.fullmatch(public_hash) or public_hash == "0" * 64:
        fail("SSH_PUBLIC_KEY_SHA256 must be one nonzero lowercase SHA-256")
    CYCLE.outside_repository(ssh_key, "SSH_KEY")
    CYCLE.outside_repository(known_hosts, "FALLBACK_KNOWN_HOSTS")
    CYCLE.outside_repository(evidence, "EVIDENCE_DIR")
    if any(evidence.iterdir()):
        fail("EVIDENCE_DIR must be empty for one exact lifecycle")
    return CYCLE.Inputs(
        manifest_sha256=MANIFEST_SHA256,
        ssh_key=ssh_key,
        ssh_public_key_sha256=public_hash,
        root_package_sha256=MANIFEST_SHA256,
        candidate_record=BUNDLE_ROOT / BUNDLE / "manifest",
        candidate_sha256=RECOVERY_SHA256,
        fallback_known_hosts=known_hosts,
        evidence_dir=evidence,
        fallback_timeout=FALLBACK_TIMEOUT_SECONDS,
    )


def require_file(path: Path, *, owner: int, modes: set[int]) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise PersistentCycleError(f"required artifact is absent: {path}") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != owner
        or stat.S_IMODE(metadata.st_mode) not in modes
        or metadata.st_nlink != 1
    ):
        fail(f"required artifact metadata is unsafe: {path}")


def verify_static_artifacts(inputs: CYCLE.Inputs) -> None:
    for path in (LIVE_ROOT, COMPONENT_ROOT):
        if not path.is_dir() or path.is_symlink():
            fail(f"required ignored build root is absent: {path}")
    require_file(TRUST_KEY, owner=os.geteuid(), modes={0o400, 0o444})
    if hashlib.sha256(TRUST_KEY.read_bytes()).hexdigest() != TRUST_KEY_SHA256:
        fail("recovery trust key identity changed")
    require_file(
        inputs.candidate_record,
        owner=os.geteuid(),
        modes={0o400},
    )
    if hashlib.sha256(inputs.candidate_record.read_bytes()).hexdigest() != (
        MANIFEST_SHA256
    ):
        fail("installed persistent-root manifest identity changed")


def ssh_arguments(inputs: CYCLE.Inputs, known_hosts: Path) -> list[str]:
    return [
        "/usr/bin/ssh",
        "-F",
        "/dev/null",
        "-vvv",
        "-i",
        str(inputs.ssh_key),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        f"HostKeyAlias={PIN.HOST_ALIAS}",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ConnectionAttempts=1",
        f"root@{PIN.TARGET_ADDRESS}",
    ]


def write_private_payload(path: Path, payload: bytes, maximum: int) -> None:
    if not payload or len(payload) > maximum:
        fail("private diagnostic payload is outside its fixed bound")
    descriptor = CYCLE.open_exclusive(path)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_one_authenticated_ssh_diagnostic(
    target_ssh: list[str], log_path: Path
) -> tuple[int, float]:
    """Run one key-auth attempt and retain its complete bounded transcript."""
    started = time.monotonic()
    try:
        result = CYCLE.run_capture(
            [*target_ssh, AUTHENTICATED_SSH_COMMAND],
            timeout=AUTHENTICATED_SSH_ATTEMPT_SECONDS,
            check=False,
        )
        output = result.stdout.encode("utf-8")
        status = result.returncode
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or ""
        output = partial if isinstance(partial, bytes) else partial.encode("utf-8")
        status = 124
    if len(output) > SSH_CLIENT_MAX_BYTES or b"\x00" in output:
        fail("one SSH client transcript exceeded its fixed bound")
    if status == 0 and result.stdout.splitlines().count(
        AUTHENTICATED_SSH_READY_MARKER
    ) != 1:
        fail("successful SSH diagnostic lacks its exact readiness marker")
    elapsed = time.monotonic() - started
    payload = (
        "format=rog5-native-ssh-client-diagnostic-v1\n"
        f"status={status}\n"
        f"elapsed_seconds={elapsed:.3f}\n"
        f"output_bytes={len(output)}\n"
        f"output_sha256={hashlib.sha256(output).hexdigest()}\n"
        f"output_hex={output.hex() or 'none'}\n"
        "result=PASS\n"
    ).encode("ascii")
    write_private_payload(log_path, payload, SSH_CLIENT_RECORD_MAX_BYTES)
    return status, elapsed


def open_ssh_diagnostic_listener() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.settimeout(60.0)
    listener.bind(("169.254.77.1", SSH_DIAGNOSTIC_PORT))
    listener.listen(1)
    return listener


def receive_ssh_diagnostic(
    listener: socket.socket, expected_boot_id: str, output: Path
) -> dict[str, str]:
    connection, peer = listener.accept()
    with connection:
        connection.settimeout(5.0)
        payload = bytearray()
        while len(payload) <= SSH_DIAGNOSTIC_MAX_BYTES:
            block = connection.recv(SSH_DIAGNOSTIC_MAX_BYTES + 1 - len(payload))
            if not block:
                break
            payload.extend(block)
        local = connection.getsockname()
    if peer[0] != "169.254.77.2" or local[0] != "169.254.77.1":
        fail("SSH diagnostic used the wrong source or host address")
    raw = bytes(payload)
    if not raw or len(raw) > SSH_DIAGNOSTIC_MAX_BYTES:
        fail("SSH diagnostic exceeded its fixed bound")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise PersistentCycleError("SSH diagnostic is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        fail("SSH diagnostic framing is invalid")
    lines = text.splitlines()
    if len(lines) != len(SSH_DIAGNOSTIC_FIELDS):
        fail("SSH diagnostic field count changed")
    values: dict[str, str] = {}
    for expected, line in zip(SSH_DIAGNOSTIC_FIELDS, lines, strict=True):
        prefix = f"{expected}="
        if not line.startswith(prefix):
            fail("SSH diagnostic field order changed")
        value = line[len(prefix):]
        if not value:
            fail("SSH diagnostic contains an empty field")
        values[expected] = value
    metadata = re.compile(r"(?:absent|symlink|error|[0-9]+:[0-9]+:[0-7]+:[0-9]+:[0-9]+)\Z")
    path_state = re.compile(r"(?:absent|symlink|other|regular-(?:error|[0-9]+))\Z")
    if (
        values["format"] != "rog5-native-ssh-diagnostic-v1"
        or values["target_release"] != TARGET_RELEASE
        or values["boot_id"] != expected_boot_id
        or values["auth_event"] not in {"present", "absent"}
        or values["shadow_class"] not in {"x", "locked", "empty", "other", "unavailable", "error"}
        or values["lower_shadow_class"] not in {"x", "locked", "empty", "other", "unavailable", "error"}
        or any(
            not metadata.fullmatch(values[name])
            for name in (
                "shadow_metadata",
                "lower_shadow_metadata",
                "root_metadata",
                "root_ssh_metadata",
                "authorized_keys_metadata",
            )
        )
        or not path_state.fullmatch(values["run_nologin"])
        or not path_state.fullmatch(values["etc_nologin"])
        or values["system_state"] not in {"starting", "running", "degraded", "maintenance", "stopping", "offline", "error"}
        or values["early_sshd"] not in {"active", "inactive"}
        or values["sshd_usepam"] not in {"yes", "no", "error"}
        or values["sshd_permitrootlogin"] not in {"prohibit-password", "without-password", "no", "yes", "error"}
        or values["sshd_pubkeyauthentication"] not in {"yes", "no", "error"}
        or values["sshd_passwordauthentication"] not in {"yes", "no", "error"}
        or values["sshd_kbdinteractiveauthentication"] not in {"yes", "no", "error"}
        or not SHA256.fullmatch(values["sshd_persourcepenalties_sha256"])
        or not values["log_bytes"].isascii()
        or not values["log_bytes"].isdecimal()
        or not 0 <= int(values["log_bytes"]) <= 10_000_000
        or not SHA256.fullmatch(values["log_sha256"])
        or (
            values["log_tail_hex"] != "none"
            and (
                len(values["log_tail_hex"]) > 8192
                or len(values["log_tail_hex"]) % 2 != 0
                or re.fullmatch(r"[0-9a-f]+", values["log_tail_hex"]) is None
            )
        )
        or values["result"] != "PASS"
    ):
        fail("SSH diagnostic content is invalid")
    write_private_payload(output, raw, SSH_DIAGNOSTIC_MAX_BYTES)
    return values


def privileged_nmcli(arguments: list[str]) -> None:
    attempts = (["/usr/bin/nmcli", *arguments], ["/usr/bin/sudo", "-n", "/usr/bin/nmcli", *arguments])
    diagnostics: list[str] = []
    for command in attempts:
        result = CYCLE.run_capture(command, timeout=30, check=False)
        if result.returncode == 0:
            return
        final = next(
            (line for line in reversed(result.stdout.splitlines()) if line.strip()),
            f"status {result.returncode}",
        )
        diagnostics.append(final[:200])
    fail("cannot activate the exact persistent-root host profile: " + " | ".join(diagnostics))


def alpine_fallback_is_present(expected_location: str) -> bool:
    return PIN.fallback_returned(expected_location)


def stock_fastboot_returned(expected_location: str) -> bool:
    if expected_location != (
        "pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2"
    ):
        fail("unexpected canonical USB path during fastboot return check")
    if not STOCK.exact_fastboot("1-1.2"):
        return False
    if (
        STOCK.fastboot_value("product") != "lahaina"
        or STOCK.fastboot_value("current-slot") != "a"
    ):
        fail("unexpected fastboot identity returned during target wait")
    return True


def exact_fastboot_fallback_record(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return False
    return (
        "format=rog5-stock-android-fallback-v1" in lines
        and "serial=M5AIKN00F0353YH" in lines
        and "usb_location=1-1.2" in lines
        and "evidence_mode=fastboot-slot-a" in lines
        and "slot_suffix=_a" in lines
        and "usb_config=fastboot" in lines
        and lines.count("result=PASS") == 1
    )


def activate_target_network(cycle: CYCLE.LiveCycle, anchor: Path) -> str:
    expected_location = CYCLE.read_recovery_anchor_location(
        anchor, cycle.dependencies
    )
    deadline = time.monotonic() + TARGET_WAIT_SECONDS
    last_error = "target gadget absent"
    interface = ""
    while time.monotonic() < deadline:
        try:
            observed_interface, location = PIN.target_observation(TARGET_PRODUCT)
        except PIN.BootstrapError as error:
            if stock_fastboot_returned(expected_location):
                fail("exact slot-A fastboot returned before target USB appeared")
            if alpine_fallback_is_present(expected_location):
                fail(
                    "Alpine fallback returned before persistent-root "
                    "target USB appeared"
                )
            last_error = str(error)
            time.sleep(cycle.poll)
            continue
        if location != expected_location:
            fail("persistent-root target appeared on a different physical USB port")
        interface = observed_interface
        break
    if not interface:
        fail(f"persistent-root target NCM did not appear: {last_error}")

    privileged_nmcli(["device", "set", interface, "managed", "yes"])
    privileged_nmcli(
        ["connection", "up", "id", HOST_PROFILE, "ifname", interface]
    )

    stable_since: float | None = None
    while time.monotonic() < deadline:
        if PIN.target_observation(TARGET_PRODUCT) != (
            interface,
            expected_location,
        ):
            fail("persistent-root USB identity changed after profile activation")
        try:
            PIN.exact_route(interface)
        except PIN.BootstrapError as error:
            last_error = str(error)
            stable_since = None
            time.sleep(cycle.poll)
            continue
        snapshots = [
            value
            for value in cycle.rog5_ncm_interfaces()
            if value.name == interface and value.product == TARGET_UDEV_MODEL
        ]
        if (
            len(snapshots) == 1
            and snapshots[0].addresses == ("169.254.77.1/30",)
            and snapshots[0].network_manager_managed == "yes"
            and snapshots[0].firewall_zone != "drop"
        ):
            now = time.monotonic()
            if stable_since is None:
                stable_since = now
            elif now - stable_since >= 1.0:
                return interface
        else:
            stable_since = None
        time.sleep(cycle.poll)
    fail(f"persistent-root host network did not stabilize: {last_error}")


def receive_stage_record(listener: socket.socket) -> StageRecord:
    connection, peer = listener.accept()
    with connection:
        connection.settimeout(2.0)
        payload = bytearray()
        while len(payload) <= STAGE_RECORD_MAX_BYTES:
            part = connection.recv(STAGE_RECORD_MAX_BYTES + 1 - len(payload))
            if not part:
                break
            payload.extend(part)
        local = connection.getsockname()
    if peer[0] != "169.254.77.2" or local[0] != "169.254.77.1":
        fail("target stage record used the wrong source or host address")
    return parse_stage_record(bytes(payload))


def wait_for_target_host_key(
    cycle: CYCLE.LiveCycle,
    anchor: Path,
    target_known_hosts: Path,
) -> StageRecord:
    expected_location = CYCLE.read_recovery_anchor_location(
        anchor, cycle.dependencies
    )
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.settimeout(0.5)
    listener.bind(("169.254.77.1", STAGE_PORT))
    listener.listen(4)
    stage_log = CYCLE.open_exclusive(cycle.output("persistent-root-stages.log"))
    process = CYCLE.start_logged(
        "persistent-root target host-key pin",
        [
            str(cycle.dependencies.host_key),
            "pin-target",
            str(anchor),
            str(target_known_hosts),
            TARGET_PRODUCT,
        ],
        cycle.output("target-host-key.log"),
        environment=CYCLE.child_environment(
            ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP="1"
        ),
    )
    previous: StageRecord | None = None
    deadline = time.monotonic() + TARGET_WAIT_SECONDS + 30
    try:
        while process.process.poll() is None:
            if time.monotonic() >= deadline:
                fail("target host-key pin escaped its fixed deadline")
            try:
                current = receive_stage_record(listener)
            except (TimeoutError, socket.timeout):
                if stock_fastboot_returned(expected_location):
                    fail("exact slot-A fastboot returned before target host-key readiness")
                continue
            if previous is not None:
                require_stage_successor(previous, current)
                if current == previous:
                    continue
            os.write(
                stage_log,
                f"received_monotonic={time.monotonic():.6f}\n".encode("ascii")
                + current.payload,
            )
            os.fsync(stage_log)
            previous = current
            if (
                WATCHDOG_OBSERVER_DETAIL.fullmatch(current.detail)
                or current.detail == SOFTDOG_PROBE_DETAIL
            ):
                CYCLE.terminate(process)
                process = None
                return current
            if current.state == "FAIL":
                fail(
                    "target emitted terminal local-root failure "
                    f"sequence={current.sequence} stage={current.stage} "
                    f"detail={current.detail}"
                )
        status = CYCLE.wait_process(process, 5)
        process = None
    finally:
        CYCLE.terminate(process)
        os.close(stage_log)
        listener.close()
    if previous is None:
        fail("target emitted no exact local-root stage record")
    if status != 0:
        fail(
            "target host key was not ready; last exact stage "
            f"sequence={previous.sequence} stage={previous.stage} "
            f"state={previous.state} detail={previous.detail}"
        )
    return previous


def wait_for_stage_host_key(
    cycle: CYCLE.LiveCycle,
    anchor: Path,
    target_known_hosts: Path,
) -> None:
    CYCLE.run_logged(
        [
            str(cycle.dependencies.host_key),
            "pin-target",
            str(anchor),
            str(target_known_hosts),
            TARGET_PRODUCT,
        ],
        cycle.output("target-host-key.log"),
        environment=CYCLE.child_environment(
            ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP="1"
        ),
        timeout=TARGET_WAIT_SECONDS + 30,
    )


def parse_runtime_evidence(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise PersistentCycleError("runtime evidence is unreadable") from error
    required = {
        "format=rog5-native-root-runtime-v1",
        "status=PASS",
        "kernel=7.1.4-g359318de534f",
        "physical_blocks=117",
        "block_backed_mounts=1",
        "root_mount=native-root-ro-noload",
        "root=native-ext4-overlay-tmpfs",
        "blocked_device_queries=0",
        "blocked_scsi_commands=0",
        "journal_recovery_events=0",
        "ufs_error_events=0",
        "ssh=strict-key-only",
        "failed_units=0",
        "result=PASS",
    }
    for marker in required:
        if lines.count(marker) != 1:
            fail(f"runtime evidence lacks one exact marker: {marker}")
    boot_ids = [line.removeprefix("boot_id=") for line in lines if line.startswith("boot_id=")]
    if len(boot_ids) != 1 or not BOOT_ID.fullmatch(boot_ids[0]):
        fail("runtime evidence has no unique target boot identity")
    return boot_ids[0]


def parse_verify_evidence(path: Path) -> TreeEvidence:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise PersistentCycleError("native verification evidence is unreadable") from error
    lines = [
        line
        for line in lines
        if line.startswith(("ROG5_NATIVE_POSTMORTEM_V1 ", "ROG5_NATIVE_TREE_V1 "))
    ]
    if not lines or lines[0] != (
        "ROG5_NATIVE_POSTMORTEM_V1 stage=inspect status=READ"
    ):
        fail("native verification evidence lacks its exact inspect record")
    expected = (
        (
            "seal",
            "0:0:444:430:1",
            "02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876",
        ),
        (
            "init",
            "symlink",
            "a8da8f10c8ab68bf1cc2234032b9ba3fd66d16ea84872acca9461c985224dc94",
        ),
        (
            "systemd",
            "0:0:755:198968:1",
            "dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0",
        ),
        (
            "sshd",
            "0:0:755:527008:1",
            "6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932",
        ),
        (
            "ssh-keygen",
            "0:0:755:526688:1",
            "e238ce08e1a4fa0d9d8fe5022e47bf9a841de23370b043c457e13f45e9d90d4e",
        ),
        (
            "authorized-keys",
            "0:0:600:81:1",
            "04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61",
        ),
        (
            "ssh-policy",
            "0:0:644:201:1",
            "c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693",
        ),
    )
    if len(lines) != len(expected) + 2:
        fail("native verification evidence has the wrong record count")
    mismatches = []
    for line, (item, metadata, digest) in zip(lines[1:-1], expected, strict=True):
        match = TREE_RECORD.fullmatch(line)
        if match is None or match.group(1) != item:
            fail("native tree evidence is malformed or out of order")
        observed = (match.group(3), match.group(4))
        exact = observed == (metadata, digest)
        if (match.group(2) == "PASS") != exact:
            fail("native tree status contradicts its bounded observation")
        if not exact:
            mismatches.append(item)
    tree = "BOOT_CRITICAL_MISMATCH" if mismatches else "BOOT_CRITICAL_PASS"
    terminal = (
        "ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS "
        "disposition=grown-target "
        "uuid=8b03827a-cc2d-4408-8558-e9b61195f96b blocks=8388603 "
        f"state=clean label=ROG5_ARCH_A tree={tree} "
        "prefix_sha256=4624159a5ad652036ad1facfc3e1dcf0c38024d1a3d7aeda9e7c9d92a13a0647"
    )
    if lines[-1] != terminal:
        fail("native verification evidence lacks its exact terminal record")
    return TreeEvidence(tree, tuple(mismatches))


def parse_repair_evidence(path: Path) -> None:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise PersistentCycleError("native repair evidence is unreadable") from error
    lines = [line for line in lines if line.startswith("ROG5_NATIVE_REPAIR_V1 ")]
    expected = [
        "ROG5_NATIVE_REPAIR_V1 stage=repair status=BEGIN",
        "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=ARMED",
        "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=DISARMED",
        "ROG5_NATIVE_REPAIR_V1 stage=terminal status=PASS "
        "files=sshd,ssh-keygen bytes=1053696 storage=RELOCKED",
    ]
    if lines != expected:
        fail("native repair evidence is not the exact successful sequence")


def parse_fsck_evidence(path: Path) -> int:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise PersistentCycleError("native fsck evidence is unreadable") from error
    lines = [line for line in lines if line.startswith("ROG5_NATIVE_REPAIR_V1 ")]
    prefix = [
        "ROG5_NATIVE_REPAIR_V1 stage=fsck status=BEGIN",
        "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=ARMED",
        "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=DISARMED",
    ]
    if len(lines) != 4 or lines[:3] != prefix:
        fail("native fsck evidence lacks its exact prefix")
    match = re.fullmatch(
        r"ROG5_NATIVE_REPAIR_V1 stage=terminal status=PASS operation=fsck "
        r"status_code=([012]) storage=RELOCKED tree=PASS",
        lines[3],
    )
    if match is None:
        fail("native fsck evidence lacks its exact terminal record")
    return int(match.group(1))


def run_optional_logged(arguments: list[str], path: Path, timeout: float) -> int:
    descriptor = CYCLE.open_exclusive(path)
    try:
        result = subprocess.run(
            arguments,
            env=CYCLE.child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=descriptor,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return result.returncode


def preflight(
    cycle: CYCLE.LiveCycle,
    inputs: CYCLE.Inputs,
    gate_environment: dict[str, str],
) -> None:
    CYCLE.verify_repository_checkpoint(cycle.dependencies.git)
    for path in (
        cycle.dependencies.git,
        cycle.dependencies.ss,
        cycle.dependencies.ip,
        cycle.dependencies.nmcli,
        cycle.dependencies.udevadm,
        cycle.dependencies.firewall,
        cycle.dependencies.live_gate,
        cycle.dependencies.bundle_server,
        cycle.dependencies.recovery_control,
        cycle.dependencies.host_key,
        cycle.dependencies.stock_fallback,
        CLAIM_ENTRYPOINT,
        Path("/usr/bin/ssh"),
    ):
        CYCLE.fixed_executable(path, offline=False)
    verify_static_artifacts(inputs)
    cycle.verify_host_clean()
    CYCLE.run_capture(
        [str(cycle.dependencies.bundle_server), "preflight", BUNDLE, MANIFEST_SHA256],
        timeout=60,
    )
    CYCLE.run_capture(
        [str(cycle.dependencies.live_gate), "preflight"],
        environment=gate_environment,
        timeout=300,
    )
    CYCLE.run_capture(
        [str(cycle.dependencies.stock_fallback), "host-preflight"],
        timeout=60,
    )


def stop_recovery_host(
    cycle: CYCLE.LiveCycle,
    control_process: CYCLE.ManagedProcess | None,
    bundle_process: CYCLE.ManagedProcess | None,
    recovery_ncm: tuple[CYCLE.InterfaceSnapshot, ...] | None,
    *,
    target_network_active: bool = False,
) -> None:
    CYCLE.terminate(control_process)
    CYCLE.terminate(bundle_process)
    if target_network_active:
        return
    if recovery_ncm is None:
        cycle.wait_host_clean()
    else:
        cycle.wait_host_clean(recovery_ncm=recovery_ncm)


def run(
    cycle: CYCLE.LiveCycle,
    inputs: CYCLE.Inputs,
    gate_environment: dict[str, str],
) -> None:
    anchor = cycle.output("recovery-usb.anchor")
    target_known_hosts = cycle.output("target-known-hosts")
    bundle_process = None
    control_process = None
    intent = None
    ledger_before: set[str] = set()
    target_boot_id: str | None = None
    target_accepted = False
    fallback_attempted = False
    fallback_proven = False
    resolved = False
    control_attempted = False
    recovery_ncm = None
    target_network_active = False
    boot_started = time.monotonic()

    cycle.capture_stock_fallback_preboot()
    cycle.claim_temporary_boot()
    CYCLE.run_logged(
        [str(CLAIM_ENTRYPOINT), PROFILE_ID],
        cycle.output("boot-claim.log"),
        timeout=30,
    )
    cycle.assert_temporary_boot_claim_entered()
    try:
        CYCLE.run_logged(
            [str(cycle.dependencies.live_gate), "boot"],
            cycle.output("stable-recovery-boot.log"),
            environment={
                **gate_environment,
                "ALLOW_TEMPORARY_BOOT": "1",
                "ALLOW_HEADLESS_LIVE_GATE": "1",
                "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE": "1",
            },
            timeout=300,
        )
        CYCLE.run_logged(
            [str(cycle.dependencies.host_key), "capture-recovery", str(anchor)],
            cycle.output("recovery-usb-anchor.log"),
            environment=CYCLE.child_environment(
                ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP="1"
            ),
            timeout=120,
        )
        recovery_ncm = cycle.wait_recovery_ncm()

        bundle_process = CYCLE.start_logged(
            "persistent-root recovery bundle server",
            [
                str(cycle.dependencies.bundle_server),
                "serve-progress-deferred",
                BUNDLE,
                MANIFEST_SHA256,
                str(inputs.evidence_dir),
            ],
            cycle.output("bundle-server.log"),
        )
        CYCLE.wait_log_marker(
            bundle_process,
            "PASS recovery bundle server ready on 169.254.77.1:8080",
            timeout=120,
            poll=cycle.poll,
        )
        ledger_before = cycle.ledger_inventory()
        control_attempted = True
        control_process = CYCLE.start_logged(
            "persistent-root recovery control",
            [
                str(cycle.dependencies.recovery_control),
                "prepare-commit",
                BUNDLE,
                MANIFEST_SHA256,
            ],
            cycle.output("recovery-control.log"),
            environment=CYCLE.child_environment(
                ALLOW_STABLE_RECOVERY_CONTROL="1",
                ALLOW_ATTENDED_KEXEC="1",
            ),
        )
        cycle.wait_bundle(bundle_process, control_process)
        bundle_process = None
        recovery_ncm = None
        status = CYCLE.wait_process(control_process, cycle.control_timeout)
        control_process = None
        if status != 0:
            intent = cycle.discover_unknown_intent(
                cycle.output("recovery-control.log"), ledger_before
            )
            fail("stable recovery control rejected the persistent-root commit")
        intent, _prepare_request = CYCLE.parse_control_log(
            cycle.output("recovery-control.log"), MANIFEST_SHA256, BUNDLE
        )
        if cycle.new_ledger_intent(ledger_before) != intent:
            fail("persistent-root control output lacks its durable intent")

        interface = activate_target_network(cycle, anchor)
        target_network_active = True
        accepted_stage = wait_for_target_host_key(cycle, anchor, target_known_hosts)
        if (
            WATCHDOG_OBSERVER_DETAIL.fullmatch(accepted_stage.detail)
            or accepted_stage.detail == SOFTDOG_PROBE_DETAIL
        ):
            target_accepted = True
            elapsed = time.monotonic() - boot_started
            CYCLE.write_record(
                cycle.output("watchdog-observer-timing.record"),
                (
                    ("format", "rog5-watchdog-observer-timing-v1"),
                    ("target_release", TARGET_RELEASE),
                    ("interface", interface),
                    ("target_boot_id", accepted_stage.boot_id),
                    ("observer_detail", accepted_stage.detail),
                    ("seconds_to_observer_evidence", f"{elapsed:.3f}"),
                    ("result", "PASS"),
                ),
            )
            fallback_attempted = True
            cycle.wait_fallback(None)
            cycle.wait_host_clean(final=True)
            fallback_proven = True
            cycle.resolve_intent(intent, "TARGET_ACCEPTED")
            resolved = True
            print(
                "PASS one RAM-only cycle captured watchdog probe evidence "
                f"in {elapsed:.3f}s"
            )
            return
        target_ssh = ssh_arguments(inputs, target_known_hosts)
        ssh_status, ssh_elapsed = run_one_authenticated_ssh_diagnostic(
            target_ssh,
            cycle.output("native-root-ssh-client.log"),
        )
        if ssh_status != 0:
            fail(f"first authenticated SSH attempt returned {ssh_status}")
        if run_optional_logged(
            [*target_ssh, UFS_LINK_SNAPSHOT_COMMAND],
            cycle.output("ufs-link-snapshot.log"),
            30,
        ) != 0:
            fail("UFS link snapshot failed")
        runtime_log = cycle.output("persistent-root-runtime.log")
        runtime_status = run_optional_logged(
            [*target_ssh, RUNTIME_COMMAND], runtime_log, 180
        )
        if runtime_status != 0:
            fail(f"local-root runtime acceptance returned {runtime_status}")
        target_boot_id = parse_runtime_evidence(runtime_log)
        target_accepted = True
        elapsed = time.monotonic() - boot_started
        CYCLE.write_record(
            cycle.output("native-root-boot-timing.record"),
            (
                ("format", "rog5-native-root-boot-timing-v1"),
                ("target_release", TARGET_RELEASE),
                ("interface", interface),
                ("authenticated_ssh_attempts", "1"),
                ("authenticated_ssh_rendezvous_seconds", f"{ssh_elapsed:.3f}"),
                ("target_boot_id", target_boot_id),
                ("disposition", "systemd-ssh-ready"),
                ("root", "native-ext4-overlay-tmpfs"),
                ("storage", "read-only"),
                ("seconds_to_native_ready", f"{elapsed:.3f}"),
                ("result", "PASS"),
            ),
        )
        reboot_status = run_optional_logged(
            [*target_ssh, "/run/initramfs/usr/libexec/rog5-reboot-bootloader"],
            cycle.output("native-root-reboot.log"),
            30,
        )
        if reboot_status not in {0, 255}:
            fail(f"native-root restart2 returned unexpected status {reboot_status}")
        fallback_attempted = True
        cycle.wait_fallback(None)
        cycle.wait_host_clean(final=True)
        fallback_proven = True
        if not exact_fastboot_fallback_record(cycle.output("fallback-identity.record")):
            fail("diagnostic target did not return through exact slot-A fastboot")
        cycle.resolve_intent(intent, "TARGET_ACCEPTED")
        resolved = True
        print(
            "PASS one RAM-only native-root cycle reached systemd and key-only SSH "
            f"in {elapsed:.3f}s and returned to exact fastboot"
        )
    except BaseException as original:
        if control_process is not None and control_process.process.poll() is not None and intent is None:
            intent = cycle.discover_unknown_intent(
                cycle.output("recovery-control.log"), ledger_before
            )
        recovery_note = ""
        cleanup_note = ""
        cleanup_base_error: BaseException | None = None
        try:
            stop_recovery_host(
                cycle,
                control_process,
                bundle_process,
                recovery_ncm,
                target_network_active=target_network_active,
            )
        except BaseException as cleanup_error:
            cleanup_note = f"; pre-fallback host cleanup failed: {cleanup_error}"
            if not isinstance(cleanup_error, Exception):
                cleanup_base_error = cleanup_error
        control_process = None
        bundle_process = None
        if anchor.exists() and not fallback_attempted:
            try:
                fallback_attempted = True
                cycle.wait_fallback(None)
                cycle.wait_host_clean(final=True)
                fallback_proven = True
                recovery_note = "; exact stock slot-A fallback and host cleanup passed"
            except BaseException as recovery_error:
                recovery_note = f"; fallback proof failed: {recovery_error}"
        if intent is None and control_attempted:
            intent = cycle.discover_unknown_intent(
                cycle.output("recovery-control.log"), ledger_before
            )
        if intent is not None and not resolved and fallback_proven:
            try:
                cycle.resolve_intent(
                    intent,
                    "TARGET_ACCEPTED" if target_accepted else "FALLBACK_RETURNED",
                )
                resolved = True
            except BaseException as resolve_error:
                recovery_note += f"; intent resolution failed: {resolve_error}"
        if isinstance(original, KeyboardInterrupt):
            raise
        if cleanup_base_error is not None:
            raise cleanup_base_error
        raise PersistentCycleError(
            f"{original}{recovery_note}{cleanup_note}"
        ) from original
    finally:
        CYCLE.terminate(control_process)
        CYCLE.terminate(bundle_process)
        cycle.output("recovery-progress.stop").unlink(missing_ok=True)


def main(arguments: list[str]) -> int:
    if arguments not in (["preflight"], ["run"]):
        fail("usage: run-persistent-root-storage-live-cycle.py preflight | run")
    if arguments == ["run"] and os.environ.get(
        "ALLOW_PERSISTENT_ROOT_STORAGE_LIVE_CYCLE"
    ) != "1":
        fail("set ALLOW_PERSISTENT_ROOT_STORAGE_LIVE_CYCLE=1 for one RAM-only cycle")
    if arguments == ["run"] and os.environ.get(
        "ALLOW_NATIVE_ROOT_BOOT"
    ) != "1":
        fail(
            "set ALLOW_NATIVE_ROOT_BOOT=1 for one exact RAM-only "
            "native-root boot"
        )
    dependencies = CYCLE.Dependencies.from_environment()
    inputs = exact_inputs()
    gate_environment = exact_environment()
    cycle = CYCLE.LiveCycle(dependencies, inputs, PROFILE)
    preflight(cycle, inputs, gate_environment)
    if arguments == ["preflight"]:
        print(
            "PASS persistent-root storage lifecycle preflight; no claim was "
            "created and no phone boot occurred"
        )
        return 0
    run(cycle, inputs, gate_environment)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        CYCLE.CycleError,
        PIN.BootstrapError,
        PersistentCycleError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
