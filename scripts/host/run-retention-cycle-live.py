#!/usr/bin/env python3
"""Run one journaled RAM-only ROG5 diagnostic and observation cycle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
MODULES = {
    "journal": "retention-cycle-transaction.py",
    "adapter": "retention-cycle-adapter.py",
    "claims": "consume-exact-boot-claim.py",
}


def load_module(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(
        f"rog5_retention_live_{name}", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


JOURNAL = load_module("journal", MODULES["journal"])
ADAPTER = load_module("adapter", MODULES["adapter"])
CLAIMS = load_module("claims", MODULES["claims"])

EXECUTION_ID = JOURNAL.EXECUTION_CLAIM_IDENTIFIER
OBSERVER_ID = JOURNAL.OBSERVER_CLAIM_IDENTIFIER
EXECUTION_SHA256 = JOURNAL.EXECUTION_RECOVERY_SHA256
OBSERVER_SHA256 = JOURNAL.OBSERVER_RECOVERY_SHA256
MANIFEST_SHA256 = (
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc"
)
USB_LOCATION = re.compile(r"[A-Za-z0-9._:/-]{1,512}\Z")
SERIAL = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
BOOT_ID = JOURNAL.BOOT_ID
MAX_OUTPUT = 256 * 1024
SYS_BUS_USB = Path("/sys/bus/usb/devices")
SYS_DEVICES = Path("/sys/devices")


class LiveCycleError(RuntimeError):
    """The bounded physical cycle cannot preserve its exact state."""


def fail(message: str) -> NoReturn:
    raise LiveCycleError(message)


def exact_file(path: Path, modes: set[int], label: str) -> bytes:
    try:
        before = path.lstat()
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as error:
        raise LiveCycleError(f"{label} is unavailable") from error
    if (
        not path.is_absolute()
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.geteuid()
        or stat.S_IMODE(before.st_mode) not in modes
        or before.st_nlink != 1
        or (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_uid,
            before.st_gid,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_uid,
            after.st_gid,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
    ):
        fail(f"{label} metadata is unsafe")
    return payload


def exact_directory(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise LiveCycleError(f"{label} is unavailable") from error
    if (
        not path.is_absolute()
        or path != resolved
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail(f"{label} metadata is unsafe")


def require_inputs() -> dict[str, str]:
    required = (
        "FASTBOOT_SERIAL",
        "ROG5_EXPECTED_USB_LOCATION",
        "SSH_KEY",
        "HEADLESS_ROOT_PACKAGE",
        "RECOVERY_CANDIDATE_RECORD",
        "FALLBACK_KNOWN_HOSTS",
        "EVIDENCE_DIR",
        "ROG5_RETENTION_JOURNAL_ROOT",
    )
    values = {name: os.environ.get(name, "") for name in required}
    missing = [name for name, value in values.items() if not value]
    if missing:
        fail("missing live-cycle inputs: " + ", ".join(missing))
    if (
        SERIAL.fullmatch(values["FASTBOOT_SERIAL"]) is None
        or USB_LOCATION.fullmatch(values["ROG5_EXPECTED_USB_LOCATION"])
        is None
        or values["ROG5_EXPECTED_USB_LOCATION"].startswith("/")
        or ".." in Path(values["ROG5_EXPECTED_USB_LOCATION"]).parts
    ):
        fail("fastboot or USB identity is not canonical")
    modes = {
        "SSH_KEY": {0o600},
        "HEADLESS_ROOT_PACKAGE": {0o444},
        "RECOVERY_CANDIDATE_RECORD": {0o444},
        "FALLBACK_KNOWN_HOSTS": {0o600},
    }
    for name, allowed_modes in modes.items():
        path = Path(values[name])
        exact_file(path, allowed_modes, name)
        try:
            path.relative_to(REPO)
        except ValueError:
            pass
        else:
            fail(f"{name} must remain outside the repository")
    exact_directory(Path(values["EVIDENCE_DIR"]), "EVIDENCE_DIR")
    exact_directory(
        Path(values["ROG5_RETENTION_JOURNAL_ROOT"]),
        "ROG5_RETENTION_JOURNAL_ROOT",
    )
    return values


def closed_live_environment(values: dict[str, str]) -> dict[str, str]:
    build = REPO / "build/host-rendezvous-v3-haven-production-20260810-r2"
    environment = {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "LC_ALL": "C",
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", ""),
        "LOGNAME": os.environ.get("LOGNAME", ""),
        "ALLOW_HEADLESS_LIVE_GATE": "1",
        "ALLOW_HEADLESS_NETWORK_ROOT_SERVER": "1",
        "ALLOW_HEADLESS_SSH_KEY_ADMISSION": "1",
        "ALLOW_HEADLESS_NETWORK_ROOT_CANCEL": "1",
        "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP": "1",
        "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE": "1",
        "ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE": "1",
        "ALLOW_NETWORK_ROOT_NFS_HANDOFF": "1",
        "ALLOW_PHONE_CREDENTIAL_USE": "1",
        "ALLOW_FALLBACK_SSH_CONTROL": "1",
        "ALLOW_FALLBACK_SSH_ATIME_EFFECTS": "1",
        "ALLOW_STABLE_RECOVERY_CONTROL": "1",
        "ALLOW_ATTENDED_KEXEC": "1",
        "ALLOW_TEMPORARY_BOOT": "1",
        "ROG5_EXTERNAL_BOOT_CLAIM": "1",
        "ROG5_RETENTION_BOOT_RESULT": "1",
        "ROG5_STABLE_RECOVERY_PROFILE": EXECUTION_ID,
        "LIVE_BUILD_ROOT": str(build / "wrapper"),
        "RECOVERY_COMPONENT_ROOT": str(build / "recovery"),
        "TRUST_KEY": str(build / "recovery/ephemeral-public.raw"),
        "BUNDLE_ROOT": "/var/lib/rog5-recovery-bundles",
        "BUNDLE": JOURNAL.CANDIDATE,
        "RECOVERY_SHA256": EXECUTION_SHA256,
        "TRUST_KEY_SHA256": (
            "f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b"
        ),
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "HOST_VERIFIER_SHA256": (
            "03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0"
        ),
        "ROG5_FALLBACK_TIMEOUT": "750",
    }
    environment.update(values)
    for name in (
        "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS",
        "XDG_STATE_HOME",
    ):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def run_process(
    argv: list[str],
    *,
    environment: dict[str, str],
    timeout: int,
    label: str,
) -> str:
    process = subprocess.Popen(
        argv,
        cwd=REPO,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        start_new_session=True,
        close_fds=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate(timeout=10)
        raise LiveCycleError(f"{label} exceeded its deadline") from error
    if len(output) > MAX_OUTPUT:
        fail(f"{label} output exceeded the bound")
    text = output.decode("utf-8", errors="replace")
    if process.returncode != 0:
        final = next(
            (line for line in reversed(text.splitlines()) if line.strip()),
            "no diagnostic",
        )
        fail(f"{label} failed: {final}")
    return text


def write_claim_source(identifier: str) -> None:
    expected = CLAIMS.expected_record(identifier)
    root = CLAIMS.canonical_claim_root()
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
        os.chmod(root, 0o700)
        parent_fd = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    exact_directory(root, "temporary-boot claim root")
    source = root / f"{identifier}.record"
    entered = Path(f"{source}.entered")
    guard = root.parent / (
        f".rog5-temporary-boot-consumption.{identifier}.entered"
    )
    if any(path.exists() or path.is_symlink() for path in (source, entered, guard)):
        fail(f"claim state already exists: {identifier}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(expected)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("cannot write exact claim source")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if exact_file(source, {0o600}, "claim source") != expected:
        fail("published claim source is not exact")


def prepare_claims() -> None:
    expected = {
        EXECUTION_ID: JOURNAL.EXECUTION_CLAIM_SHA256,
        OBSERVER_ID: JOURNAL.OBSERVER_CLAIM_SHA256,
    }
    records: dict[str, bytes] = {}
    root = CLAIMS.canonical_claim_root()
    for identifier, digest in expected.items():
        record = CLAIMS.expected_record(identifier)
        if hashlib.sha256(record).hexdigest() != digest:
            fail(f"claim record diverges from the journal: {identifier}")
        records[identifier] = record
        source = root / f"{identifier}.record"
        entered = Path(f"{source}.entered")
        guard = root.parent / (
            f".rog5-temporary-boot-consumption.{identifier}.entered"
        )
        if any(
            path.exists() or path.is_symlink()
            for path in (source, entered, guard)
        ):
            fail(f"claim state already exists: {identifier}")
    for identifier in records:
        write_claim_source(identifier)
    print("PASS exact execution and observer claim sources prepared")


def consume_claim(
    identifier: str,
    expected_sha256: str,
    environment: dict[str, str],
) -> None:
    invocation = next(
        item for item in ADAPTER.INVOCATIONS if item.name.endswith("claim")
        and item.arguments == (identifier,)
    )
    output = run_process(
        [
            "/usr/bin/python3",
            "-B",
            str(REPO / invocation.program),
            identifier,
        ],
        environment=environment,
        timeout=15,
        label=identifier,
    )
    expected = f"PASS exact durable BOOT_CLAIMED record entered: {identifier}\n"
    if output != expected:
        fail("claim consumer output is not exact")
    record = CLAIMS.expected_record(identifier)
    if hashlib.sha256(record).hexdigest() != expected_sha256:
        fail("consumed claim identity changed")


def parse_record(path: Path) -> dict[str, str]:
    payload = exact_file(path, {0o600}, path.name)
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise LiveCycleError(f"{path.name} is not ASCII") from error
    if not text.endswith("\n"):
        fail(f"{path.name} is not canonical")
    values: dict[str, str] = {}
    for line in text.splitlines():
        name, separator, value = line.partition("=")
        if not separator or not name or not value or name in values:
            fail(f"{path.name} fields are not canonical")
        values[name] = value
    return values


def parse_execution_evidence(
    values: dict[str, str],
) -> tuple[str, str, bool]:
    evidence = Path(values["EVIDENCE_DIR"])
    diagnostic_path = evidence / "early-target-diagnostics.json"
    payload = exact_file(diagnostic_path, {0o600}, diagnostic_path.name)
    try:
        diagnostic = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LiveCycleError("diagnostic evidence is invalid") from error
    target_boot_id = diagnostic.get("target_boot_id")
    if (
        diagnostic.get("capture_status") != "valid"
        or diagnostic.get("candidate") != JOURNAL.CANDIDATE
        or not isinstance(target_boot_id, str)
        or BOOT_ID.fullmatch(target_boot_id) is None
        or diagnostic.get("usb_location")
        != values["ROG5_EXPECTED_USB_LOCATION"]
    ):
        fail("diagnostic execution evidence is not exact")
    fallback = parse_record(evidence / "fallback-identity.record")
    fallback_boot_id = fallback.get("boot_id", "")
    if (
        BOOT_ID.fullmatch(fallback_boot_id) is None
        or fallback_boot_id == target_boot_id
        or fallback.get("usb_location")
        != values["ROG5_EXPECTED_USB_LOCATION"]
        or fallback.get("result") != "PASS"
    ):
        fail("fallback evidence is not exact")
    postmortem = parse_record(evidence / "fallback-postmortem.record")
    if (
        postmortem.get("expected_candidate") != JOURNAL.CANDIDATE
        or postmortem.get("expected_boot_id") != target_boot_id
        or postmortem.get("fallback_boot_id") != fallback_boot_id
    ):
        fail("fallback postmortem lineage is not exact")
    resolution_path = evidence / "intent-resolution.log"
    resolution_payload = exact_file(
        resolution_path, {0o600}, resolution_path.name
    )
    try:
        resolution = json.loads(resolution_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LiveCycleError("intent resolution is invalid") from error
    if (
        resolution.get("state") != "RESOLVED"
        or resolution.get("outcome") != "FALLBACK_RETURNED"
        or resolution.get("target") != JOURNAL.CANDIDATE
        or resolution.get("manifest_sha256") != MANIFEST_SHA256
    ):
        fail("execution intent was not resolved to exact fallback")
    return (
        target_boot_id,
        fallback_boot_id,
        postmortem.get("pstore_state") == "EMPTY",
    )


def parse_single_result(output: str, action: str) -> dict[str, str]:
    prefix = f"ROG5_RETENTION_BOOT_RESULT_V1 action={action} "
    records = [
        line.removeprefix(prefix)
        for line in output.splitlines()
        if line.startswith(prefix)
    ]
    if len(records) != 1:
        fail(f"{action} produced no unique result")
    result: dict[str, str] = {}
    for field in records[0].split():
        name, separator, value = field.partition("=")
        if not separator or not name or not value or name in result:
            fail(f"{action} result is malformed")
        result[name] = value
    return result


def fastboot_id_path(serial: str, expected_raw_location: str) -> str:
    """Map one exact fastboot device's raw sysfs ancestry to udev ID_PATH."""

    matches: list[Path] = []
    try:
        candidates = tuple(SYS_BUS_USB.iterdir())
    except OSError as error:
        raise LiveCycleError("USB sysfs inventory is unavailable") from error
    for candidate in candidates:
        try:
            vendor = (candidate / "idVendor").read_text(encoding="ascii").strip()
            product = (candidate / "idProduct").read_text(encoding="ascii").strip()
            observed_serial = (candidate / "serial").read_text(
                encoding="ascii"
            ).strip()
        except (OSError, UnicodeDecodeError):
            continue
        if (vendor, product, observed_serial) == ("0b05", "4daf", serial):
            matches.append(candidate)
    if len(matches) != 1:
        fail("expected one exact fastboot USB sysfs device")
    try:
        resolved = matches[0].resolve(strict=True)
        raw_location = resolved.relative_to(SYS_DEVICES.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise LiveCycleError("fastboot USB ancestry is unavailable") from error
    if raw_location.as_posix() != expected_raw_location:
        fail("fastboot moved from the exact raw physical USB location")
    output = run_process(
        [
            "/usr/bin/udevadm",
            "info",
            "--query=property",
            f"--path={matches[0]}",
        ],
        environment={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        timeout=5,
        label="fastboot udev identity",
    )
    values = [
        line.removeprefix("ID_PATH=")
        for line in output.splitlines()
        if line.startswith("ID_PATH=")
    ]
    if (
        len(values) != 1
        or USB_LOCATION.fullmatch(values[0]) is None
        or values[0].startswith("/")
        or ".." in Path(values[0]).parts
    ):
        fail("fastboot udev ID_PATH is not unique and canonical")
    return values[0]


def public_key_sha256(private_key: Path) -> str:
    output = run_process(
        ["/usr/bin/ssh-keygen", "-y", "-f", str(private_key)],
        environment={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        timeout=15,
        label="public-key derivation",
    )
    fields = output.strip().split()
    if len(fields) < 2 or fields[0] != "ssh-ed25519":
        fail("deployment key is not Ed25519")
    canonical = f"{fields[0]} {fields[1]}\n".encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def run_live_cycle(values: dict[str, str]) -> None:
    names = tuple(item.name for item in ADAPTER.INVOCATIONS)
    if names != (
        "execution-claim",
        "execution-boot",
        "fallback-reboot",
        "observer-claim",
        "observer-boot",
        "postmortem-read",
    ):
        fail("adapter action ordering changed")
    environment = closed_live_environment(values)
    host_boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(
        encoding="ascii"
    ).strip()
    if BOOT_ID.fullmatch(host_boot_id) is None:
        fail("host boot identity is invalid")
    journal_root = Path(values["ROG5_RETENTION_JOURNAL_ROOT"])
    journal = JOURNAL.CycleJournal.create(
        journal_root,
        host_boot_id,
        values["ROG5_EXPECTED_USB_LOCATION"],
    )
    try:
        journal.execution_claim_intent()
        consume_claim(
            EXECUTION_ID,
            JOURNAL.EXECUTION_CLAIM_SHA256,
            environment,
        )
        journal.execution_claim_entered(
            EXECUTION_ID, JOURNAL.EXECUTION_CLAIM_SHA256
        )
        journal.execution_boot_intent(
            EXECUTION_SHA256,
            values["ROG5_EXPECTED_USB_LOCATION"],
            True,
        )
        run_process(
            [
                "/usr/bin/python3",
                "-B",
                str(REPO / "scripts/host/run-minimal-headless-live-cycle.py"),
                "diagnostic-run",
            ],
            environment=environment,
            timeout=1200,
            label="diagnostic lifecycle",
        )
        target_boot_id, fallback_boot_id, pstore_empty = (
            parse_execution_evidence(values)
        )
        journal.execution_recovery_observed(
            EXECUTION_SHA256,
            values["ROG5_EXPECTED_USB_LOCATION"],
            True,
        )
        journal.target_observed(
            JOURNAL.CANDIDATE,
            target_boot_id,
            values["ROG5_EXPECTED_USB_LOCATION"],
        )
        journal.fallback_observed(
            JOURNAL.CANDIDATE,
            target_boot_id,
            fallback_boot_id,
            values["ROG5_EXPECTED_USB_LOCATION"],
            "1d6b:0104",
            "ROG5LINUX",
            True,
            True,
        )
        observer_environment = dict(environment)
        observer_environment.update(
            {
                "ROG5_OBSERVATION_RECOVERY_PROFILE": OBSERVER_ID,
                "OBSERVER_BUILD_ROOT": str(
                    REPO
                    / "build/observation-recovery-haven-live-20260810-r1"
                ),
                "OBSERVER_RECOVERY_SHA256": OBSERVER_SHA256,
            }
        )
        run_process(
            [
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                str(REPO / "scripts/host/run-observation-recovery-live-gate.sh"),
                "artifact-preflight",
            ],
            environment=observer_environment,
            timeout=300,
            label="observer artifact preflight",
        )
        if not pstore_empty:
            journal.terminate("fallback-pstore-not-empty")
            fail(
                "fallback retained pstore evidence; observer boot withheld "
                "to preserve the independent record"
            )
        retention_environment = dict(environment)
        retention_environment.update(
            {
                "SSH_KEY": values["SSH_KEY"],
                "KNOWN_HOSTS": values["FALLBACK_KNOWN_HOSTS"],
            }
        )
        run_process(
            [
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                str(REPO / "scripts/host/reboot-fallback-to-fastboot.sh"),
                "retention-preflight",
            ],
            environment=retention_environment,
            timeout=90,
            label="fallback retention preflight",
        )
        journal.retention_preflight(
            fallback_boot_id,
            values["ROG5_EXPECTED_USB_LOCATION"],
            True,
            True,
        )

        journal.bootloader_transition_intent(
            fallback_boot_id,
            values["ROG5_EXPECTED_USB_LOCATION"],
        )
        fallback_environment = dict(environment)
        fallback_environment.update(
            {
                "ALLOW_FALLBACK_ACM_CONTROL": "1",
                "ALLOW_FALLBACK_ACM_STORAGE_WRITE": "1",
                "ALLOW_FALLBACK_BOOTLOADER_REBOOT": "1",
                "ROG5_EXPECTED_FASTBOOT_SERIAL": values["FASTBOOT_SERIAL"],
            }
        )
        reboot_output = run_process(
            [
                "/usr/bin/python3",
                "-B",
                str(REPO / "scripts/host/fallback-acm-control.py"),
                "reboot",
                values["FALLBACK_KNOWN_HOSTS"],
            ],
            environment=fallback_environment,
            timeout=240,
            label="fallback-to-fastboot transition",
        )
        reboot = parse_single_result(reboot_output, "fallback-reboot")
        if (
            reboot.get("fastboot_serial") != values["FASTBOOT_SERIAL"]
            or reboot.get("product") != "0b05:4daf"
            or reboot.get("usb_location")
            != values["ROG5_EXPECTED_USB_LOCATION"]
        ):
            fail("fallback reboot result changed identity")
        journal.bootloader_observed(
            values["ROG5_EXPECTED_USB_LOCATION"],
            "0b05:4daf",
            values["FASTBOOT_SERIAL"],
        )

        observer_id_path = fastboot_id_path(
            values["FASTBOOT_SERIAL"],
            values["ROG5_EXPECTED_USB_LOCATION"],
        )
        observer_environment["ROG5_EXPECTED_USB_LOCATION"] = observer_id_path

        journal.observer_claim_intent()
        consume_claim(
            OBSERVER_ID,
            JOURNAL.OBSERVER_CLAIM_SHA256,
            observer_environment,
        )
        journal.observer_claim_entered(
            OBSERVER_ID, JOURNAL.OBSERVER_CLAIM_SHA256
        )
        journal.observer_boot_intent(
            OBSERVER_SHA256,
            values["ROG5_EXPECTED_USB_LOCATION"],
            values["FASTBOOT_SERIAL"],
            True,
        )
        observer_output = run_process(
            [
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                str(REPO / "scripts/host/run-observation-recovery-live-gate.sh"),
                "boot",
            ],
            environment=observer_environment,
            timeout=300,
            label="observation recovery boot",
        )
        observer = parse_single_result(observer_output, "observer-boot")
        if (
            observer.get("fastboot_serial") != values["FASTBOOT_SERIAL"]
            or observer.get("recovery_sha256") != OBSERVER_SHA256
            or observer.get("rollback_armed") != "1"
            or observer.get("usb_location") != observer_id_path
        ):
            fail("observer boot result changed identity")
        journal.observer_recovery_observed(
            OBSERVER_SHA256,
            values["ROG5_EXPECTED_USB_LOCATION"],
            values["FASTBOOT_SERIAL"],
            True,
        )

        journal.postmortem_read_intent(JOURNAL.CANDIDATE, target_boot_id)
        postmortem_output = run_process(
            [
                "/usr/bin/python3",
                "-B",
                str(REPO / "scripts/host/stable-recovery-control.py"),
                "postmortem-status",
                JOURNAL.CANDIDATE,
                target_boot_id,
            ],
            environment=observer_environment,
            timeout=90,
            label="observation postmortem read",
        )
        try:
            postmortem = json.loads(postmortem_output)
        except json.JSONDecodeError as error:
            raise LiveCycleError(
                "observation postmortem output is invalid"
            ) from error
        classification = postmortem.get("classification")
        if (
            postmortem.get("expected_candidate") != JOURNAL.CANDIDATE
            or postmortem.get("expected_boot_id") != target_boot_id
            or classification not in JOURNAL.POSTMORTEM_CLASSIFICATIONS
        ):
            fail("observation postmortem result is not exact")
        journal.postmortem_result(
            JOURNAL.CANDIDATE,
            target_boot_id,
            str(classification),
            1,
        )

        fallback_output = (
            Path(values["EVIDENCE_DIR"])
            / "observer-fallback-identity.record"
        )
        run_process(
            [
                "/usr/bin/python3",
                "-B",
                str(REPO / "scripts/host/fallback-acm-control.py"),
                "wait-ssh-preflight",
                values["FALLBACK_KNOWN_HOSTS"],
                values["SSH_KEY"],
                public_key_sha256(Path(values["SSH_KEY"])),
                str(Path(values["EVIDENCE_DIR"]) / "recovery-usb.anchor"),
                "750",
                str(fallback_output),
            ],
            environment=fallback_environment,
            timeout=870,
            label="observer fallback proof",
        )
        final_fallback = parse_record(fallback_output)
        if (
            final_fallback.get("result") != "PASS"
            or final_fallback.get("usb_location")
            != values["ROG5_EXPECTED_USB_LOCATION"]
        ):
            fail("observer fallback identity is not exact")
        result = journal.finish()
        print(
            "PASS retention live cycle complete "
            f"target_boot_id={target_boot_id} "
            f"postmortem={classification} "
            f"lineage={result['lineage_result']}"
        )
    except BaseException:
        try:
            snapshot = journal.snapshot()
            if snapshot["phase"] not in {"complete", "terminated"}:
                journal.terminate("live-cycle-failed")
        except BaseException:
            pass
        raise
    finally:
        journal.close()


def main(arguments: list[str]) -> int:
    if arguments == ["prepare"]:
        prepare_claims()
        return 0
    if arguments == ["run"]:
        run_live_cycle(require_inputs())
        return 0
    fail("usage: run-retention-cycle-live.py {prepare|run}")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        LiveCycleError,
        JOURNAL.TransactionError,
        CLAIMS.ClaimError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
