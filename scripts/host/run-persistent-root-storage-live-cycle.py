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

PROFILE_ID = "local-image-stage-prebind-v12-generation121-live-v1"
BUNDLE = "local-image-stage-prebind-v12"
MANIFEST_SHA256 = (
    "60d264a02ba91ad0839f27a8d8054092dd435414d247a9bc50495ca470d5ac70"
)
RECOVERY_SHA256 = (
    "08c78710259a8eb6da4545249ba86aaae2fed5e59d4eb6d6a1548c1050df80b5"
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
    b"local-image-stage-prebind-v12-generation121-live-v1\n"
    b"candidate=local-image-stage-prebind-v12\n"
    b"manifest_sha256="
    b"60d264a02ba91ad0839f27a8d8054092dd435414d247a9bc50495ca470d5ac70\n"
    b"state=BOOT_CLAIMED\n"
)
CYCLE.CLAIM_CONSUMER.CLAIMS[PROFILE_ID] = CLAIM_RECORD
CLAIM_ENTRYPOINT = (
    REPO
    / "scripts/host/consume-local-image-stage-prebind-v12-claim.py"
)
TARGET_RELEASE = "7.1.4-g359318de534f"
TARGET_PRODUCT = "ROG5 local image stage"
TARGET_UDEV_MODEL = "ROG5_local_image_stage"
HOST_PROFILE = "rog5-fallback-usb-ssh"
LIVE_ROOT = (
    REPO
    / "build/local-image-stage-prebind-v12-generation121-20260824-r1"
)
COMPONENT_ROOT = REPO / "build/persistent-root-v13-recovery-components-20260823-r1"
TRUST_KEY = COMPONENT_ROOT / "ephemeral-public.raw"
BUNDLE_ROOT = Path("/var/lib/rog5-recovery-bundles")
TARGET_WAIT_SECONDS = 450
FALLBACK_TIMEOUT_SECONDS = 900
AUTHENTICATED_SSH_WAIT_SECONDS = 150
AUTHENTICATED_SSH_ATTEMPT_SECONDS = 20
AUTHENTICATED_SSH_READY_MARKER = "ROG5_AUTHENTICATED_SSH_READY_V1"
AUTHENTICATED_SSH_OUTPUT_MAX_BYTES = 4096
AUTHENTICATED_SSH_COMMAND = (
    f"printf '%s\\n' '{AUTHENTICATED_SSH_READY_MARKER}'"
)
STAGE_PORT = 8079
STAGE_RECORD_MAX_BYTES = 512
ARCH_IMAGE_SIZE = 649960943
ARCH_IMAGE_SHA256 = "41f75ab6c9c74e3f511fcac4a85b1c4da93695bc56bf85ab954a42f70d83ba88"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)

PROFILE = CYCLE.CycleProfile(
    candidate=BUNDLE,
    bundle=BUNDLE,
    bundle_profile="persistent-root-ro-v1",
    target_id=BUNDLE,
    admission_profile="local-image-stage-prebind-v12",
    recovery_profile=PROFILE_ID,
    runtime_profile="local-image-stage-prebind-v12",
    build_profile="local-image-stage-prebind-v12",
    diagnostic=False,
)

RUNTIME_COMMAND = r"""
set -eu
i=0
while [ ! -f /run/rog5-p2-ready ] && [ "$i" -lt 300 ]; do
    i=$((i + 1))
    sleep 0.5
done
[ -f /run/rog5-p2-ready ]
[ -f /run/rog5-power-usb-ready ]
printf '%s\n' 'format=rog5-persistent-root-live-evidence-v1'
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='; awk '{ print $1 }' /proc/uptime
cat /run/rog5-p2-ready
printf 'userdata_device='; cat /run/rog5-p2-userdata-device
printf '%s\n' 'result=PASS'
""".strip()

DIAGNOSTIC_COMMAND = r"""
set -eu
printf '%s\n' '=== ready ==='
cat /run/rog5-p2-ready
printf '%s\n' '=== userdata ==='
cat /run/rog5-p2-userdata-device
printf '%s\n' '=== side-port power/USB ==='
cat /run/rog5-power-usb-ready
printf '%s\n' '=== mounts ==='
cat /proc/mounts
printf '%s\n' '=== UFS inventory ==='
cat /run/rog5-p2-ufs-inventory.tsv
printf '%s\n' '=== initramfs verification ==='
cat /run/rog5-p2-root-verification.txt
printf '%s\n' '=== systemd time ==='
systemd-analyze time
printf '%s\n' '=== systemd blame ==='
systemd-analyze blame --no-pager | sed -n '1,80p'
printf '%s\n' '=== systemd critical chain ==='
systemd-analyze critical-chain --no-pager
printf '%s\n' '=== sshd critical chain ==='
systemd-analyze critical-chain --no-pager rog5-early-sshd.service
printf '%s\n' '=== Ed25519 key critical chain ==='
systemd-analyze critical-chain --no-pager rog5-sshd-ed25519-key.service
printf '%s\n' '=== ssh host-key services ==='
systemctl show --no-pager -p LoadState -p ActiveState -p SubState \
	sshdgenkeys.service rog5-sshd-ed25519-key.service \
	rog5-early-sshd.service sshd.service
printf '%s\n' '=== ssh host-key inventory ==='
find /etc/ssh -maxdepth 1 -type f -name 'ssh_host_*_key*' \
    -printf '%f %m\n' | sort
printf '%s\n' '=== dmesg ==='
dmesg
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


STAGES = {
    "kernel-verified",
    "ufs-ready",
    "storage-locked",
    "userdata-resolved",
    "userdata-mount",
    "image-resolved",
    "image-write",
    "image-write-window",
    "userdata-unmount",
    "write-window-precheck",
    "userdata-partition-rw",
    "userdata-disk-rw",
    "write-window-selected-disk-blockdev",
    "write-window-selected-disk-sysfs",
    "write-window-selected-part-blockdev",
    "write-window-selected-part-sysfs",
    "write-window-other-disk-blockdev",
    "write-window-other-disk-sysfs",
    "write-window-other-part-blockdev",
    "write-window-other-part-sysfs",
    "write-window-count",
    "userdata-rw",
    "image-loop-rw",
    "image-fs-rw",
    "image-probe",
    "storage-relock",
    "image-mount",
    "root-verify",
    "ufs-health",
    "overlay",
    "runtime",
    "final-storage",
    "switch-root",
}
STAGE_STATES = {"ENTER", "PASS", "FAIL"}


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


def exact_arch_image() -> Path:
    image = CYCLE.caller_file(os.environ.get("ARCH_IMAGE_GZ", ""), "ARCH_IMAGE_GZ")
    CYCLE.outside_repository(image, "ARCH_IMAGE_GZ")
    metadata = image.stat()
    if metadata.st_size != ARCH_IMAGE_SIZE:
        fail("ARCH_IMAGE_GZ size changed")
    with image.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != ARCH_IMAGE_SHA256:
        fail("ARCH_IMAGE_GZ identity changed")
    return image


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
        f"root@{PIN.TARGET_ADDRESS}",
    ]


def wait_for_authenticated_ssh(
    target_ssh: list[str],
    log_path: Path,
) -> tuple[int, float]:
    """Wait for one complete key-authenticated session, not only TCP/22."""
    started = time.monotonic()
    deadline = started + AUTHENTICATED_SSH_WAIT_SECONDS
    attempts = 0
    descriptor = CYCLE.open_exclusive(log_path)
    try:
        os.write(
            descriptor,
            b"format=rog5-authenticated-ssh-rendezvous-v1\n",
        )
        while True:
            now = time.monotonic()
            if now >= deadline:
                os.write(descriptor, b"result=FAIL\n")
                os.fsync(descriptor)
                fail(
                    "authenticated SSH did not become ready within "
                    f"{AUTHENTICATED_SSH_WAIT_SECONDS} seconds"
                )
            attempts += 1
            timeout = min(
                AUTHENTICATED_SSH_ATTEMPT_SECONDS,
                max(1.0, deadline - now),
            )
            try:
                result = CYCLE.run_capture(
                    [*target_ssh, AUTHENTICATED_SSH_COMMAND],
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                status = "timeout"
            else:
                if result.returncode == 0:
                    output = result.stdout.encode("utf-8")
                    output_sha256 = hashlib.sha256(output).hexdigest()
                    marker_count = result.stdout.splitlines().count(
                        AUTHENTICATED_SSH_READY_MARKER
                    )
                    if (
                        len(output) > AUTHENTICATED_SSH_OUTPUT_MAX_BYTES
                        or "\x00" in result.stdout
                        or marker_count != 1
                    ):
                        os.write(
                            descriptor,
                            (
                                f"attempt={attempts} status=unexpected-output "
                                f"output_bytes={len(output)} "
                                f"output_sha256={output_sha256}\n"
                                "result=FAIL\n"
                            ).encode("ascii"),
                        )
                        os.fsync(descriptor)
                        fail("unexpected authenticated SSH readiness output")
                    elapsed = time.monotonic() - started
                    os.write(
                        descriptor,
                        (
                            f"attempt={attempts} status=ready "
                            f"output_bytes={len(output)} "
                            f"output_sha256={output_sha256}\n"
                            f"attempts={attempts}\n"
                            f"elapsed_seconds={elapsed:.3f}\n"
                            "result=PASS\n"
                        ).encode("ascii"),
                    )
                    os.fsync(descriptor)
                    return attempts, elapsed
                status = f"exit-{result.returncode}"
            os.write(
                descriptor,
                f"attempt={attempts} status={status}\n".encode("ascii"),
            )
            os.fsync(descriptor)
            time.sleep(1.0)
    finally:
        os.close(descriptor)


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


def wait_post_commit_host_cleanup(cycle: CYCLE.LiveCycle) -> None:
    # COMMIT_EXEC is allowed to replace recovery USB immediately.  The host
    # cleanup contract must therefore prove listener, firewall, address, NFS,
    # and snapshot restoration without requiring the old USB product to
    # survive the transition.
    cycle.wait_host_clean()


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


def transfer_arch_image(
    cycle: CYCLE.LiveCycle,
    target_ssh: list[str],
    image: Path,
) -> None:
    log = cycle.output("local-image-transfer.log")
    descriptor = CYCLE.open_exclusive(log)
    command = (
        "umask 077; cat > /run/arch-local-a.ext4.gz; "
        "stat -c 'size=%s mode=%a links=%h uid=%u gid=%g' "
        "/run/arch-local-a.ext4.gz; "
        "printf 'sha256='; sha256sum /run/arch-local-a.ext4.gz | cut -d ' ' -f 1; "
        "printf 'result=PASS\\n'"
    )
    try:
        with image.open("rb") as source:
            result = subprocess.run(
                [*target_ssh, command],
                env=CYCLE.child_environment(),
                stdin=source,
                stdout=descriptor,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=600,
            )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if result.returncode != 0:
        fail("local Arch image transfer failed")
    CYCLE.require_log_markers(
        log,
        (
            f"size={ARCH_IMAGE_SIZE} mode=600 links=1 uid=0 gid=0",
            f"sha256={ARCH_IMAGE_SHA256}",
            "result=PASS",
        ),
    )


def run_stage_installer(cycle: CYCLE.LiveCycle, target_ssh: list[str]) -> None:
    log = cycle.output("local-image-installer.log")
    status = run_optional_logged(
        [*target_ssh, "/usr/local/sbin/rog5-install-local-arch-image"],
        log,
        900,
    )
    if status not in {0, 255}:
        fail(f"local-image installer returned unexpected status {status}")
    CYCLE.require_log_markers(
        log,
        (
            "state=PASS",
            "image_sha256=533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153",
            "image_size=17179869184",
            "filesystem_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4",
            "filesystem_label=ROG5_ARCH_A",
        ),
    )


def parse_runtime_evidence(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise PersistentCycleError("runtime evidence is unreadable") from error
    required = {
        "format=rog5-persistent-root-live-evidence-v1",
        f"kernel={TARGET_RELEASE}",
        "status=PASS",
        "physical_blocks=116",
        "block_backed_mounts=2",
        "userdata_mount=ro-noload",
        "local_image_mount=ro-noload",
        "local_image_write_probe=PASS",
        "root=local-ext4-overlay-tmpfs",
        "blocked_device_queries=0",
        "blocked_scsi_commands=0",
        "journal_recovery_events=0",
        "ufs_error_events=0",
        "ssh=strict-key-only",
        "result=PASS",
    }
    for marker in required:
        if lines.count(marker) != 1:
            fail(f"runtime evidence lacks one exact marker: {marker}")
    boot_ids = [line.removeprefix("boot_id=") for line in lines if line.startswith("boot_id=")]
    if len(boot_ids) != 1 or not BOOT_ID.fullmatch(boot_ids[0]):
        fail("runtime evidence has no unique target boot identity")
    userdata = [
        line.removeprefix("userdata_device=")
        for line in lines
        if line.startswith("userdata_device=")
    ]
    if len(userdata) != 1 or not re.fullmatch(r"/dev/sd[a-z]23", userdata[0]):
        fail("runtime evidence has no exact dynamic userdata identity")
    return boot_ids[0]


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
    exact_arch_image()
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


def run(cycle: CYCLE.LiveCycle, inputs: CYCLE.Inputs, gate_environment: dict[str, str]) -> None:
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
        [str(CLAIM_ENTRYPOINT)],
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
        wait_post_commit_host_cleanup(cycle)
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
        wait_for_stage_host_key(cycle, anchor, target_known_hosts)
        target_ssh = ssh_arguments(inputs, target_known_hosts)
        ssh_attempts, ssh_ready_elapsed = wait_for_authenticated_ssh(
            target_ssh,
            cycle.output("persistent-root-ssh-readiness.log"),
        )
        transfer_arch_image(cycle, target_ssh, exact_arch_image())
        run_stage_installer(cycle, target_ssh)
        target_accepted = True
        elapsed = time.monotonic() - boot_started
        CYCLE.write_record(
            cycle.output("persistent-root-timing.record"),
            (
                ("format", "rog5-local-image-stage-timing-v1"),
                ("target_release", TARGET_RELEASE),
                ("interface", interface),
                ("authenticated_ssh_attempts", str(ssh_attempts)),
                (
                    "authenticated_ssh_rendezvous_seconds",
                    f"{ssh_ready_elapsed:.3f}",
                ),
                ("seconds_to_staged_image", f"{elapsed:.3f}"),
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
            "PASS one RAM-only writer cycle staged the exact 16-GiB Arch image "
            f"through strict SSH in {elapsed:.3f}s, relocked storage, and returned to fastboot"
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
