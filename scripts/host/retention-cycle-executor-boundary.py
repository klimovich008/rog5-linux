"""Pure descriptor and output boundary for a future retention runner."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


REPO = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name(
    "retention-cycle-executor-contract.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_cycle_executor_contract_for_boundary",
    CONTRACT_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("retention executor contract is unavailable")
CONTRACT = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = CONTRACT
_SPEC.loader.exec_module(CONTRACT)
ADAPTER = CONTRACT.ADAPTER

BUILTIN_EXECUTOR = "none"
LIVE_ENTRYPOINT = "none"
CONNECTED_ADMISSION = "none"
CREDENTIAL_USE = "none"

OPEN_FLAGS = ("O_CLOEXEC", "O_NOFOLLOW", "O_RDONLY")
DIRECTORY_OPEN_FLAGS = (
    "O_CLOEXEC",
    "O_DIRECTORY",
    "O_NOFOLLOW",
    "O_RDONLY",
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REQUEST_ID = re.compile(r"[0-9a-f]{32}\Z")
ZERO_SHA256 = "0" * 64
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
SSH_PREFIX = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
HOST_ALIAS = "rog5-fallback"

BOOT_RESULT_PREFIX = b"ROG5_RETENTION_BOOT_RESULT_V1 "
BOOT_ACTIONS = ("execution-boot", "fallback-reboot", "observer-boot")
LIVE_PRODUCER_STATE = {
    "execution-boot": "hold-gate-no-current-success",
    "fallback-reboot": "guarded-producer-defined",
    "observer-boot": "hold-gate-no-current-success",
}


class BoundaryError(RuntimeError):
    """One proposed process result or descriptor is not reviewable."""


@dataclass(frozen=True)
class InterpreterIdentity:
    logical_path: str
    resolved_path: str
    link_target: str
    size: int
    sha256: str


INTERPRETERS = {
    "/usr/bin/python3": InterpreterIdentity(
        logical_path="/usr/bin/python3",
        resolved_path="/usr/bin/python3.13",
        link_target="python3.13",
        size=14352,
        sha256=(
            "62cf34d8c76bbde1cceea478800c3b9125a90746dd73f1281614823bdcf1b718"
        ),
    ),
    "/usr/bin/bash": InterpreterIdentity(
        logical_path="/usr/bin/bash",
        resolved_path="/usr/bin/bash",
        link_target="none",
        size=1162328,
        sha256=(
            "66bb45cd80c82ea4c352c774c0f1577ad51707f55749e90dd6b787a9fb3022d1"
        ),
    ),
}


@dataclass(frozen=True)
class FileDescriptorEvidence:
    """Facts a future runtime must collect from one held descriptor."""

    logical_path: str
    resolved_path: str
    link_target: str
    revalidated_link_target: str
    file_type: str
    uid: int
    gid: int
    mode: str
    nlink: int
    size: int
    sha256: str
    opened_device: int
    opened_inode: int
    path_device: int
    path_inode: int
    open_flags: tuple[str, ...]


@dataclass(frozen=True)
class DirectoryDescriptorEvidence:
    """Facts for one held, revalidated private parent directory."""

    logical_path: str
    resolved_path: str
    uid: int
    gid: int
    mode: str
    opened_device: int
    opened_inode: int
    path_device: int
    path_inode: int
    open_flags: tuple[str, ...]


@dataclass(frozen=True)
class HostPinEvidence:
    """One public host-key pin snapshot; this module never reads a path."""

    file: FileDescriptorEvidence
    parent: DirectoryDescriptorEvidence
    payload: bytes


@dataclass(frozen=True)
class DescriptorAttestation:
    name: str
    program_sha256: str
    interpreter_sha256: str
    host_pin_sha256: str


@dataclass(frozen=True)
class ProcessOutcome:
    """Already-bounded child result supplied to the pure decoder."""

    name: str
    exit_code: int
    term_signal: int | None
    timed_out: bool
    output_overflow: bool
    stdout: bytes
    stderr: bytes


def _fail(message: str) -> None:
    raise BoundaryError(message)


def _exact_int(value: object, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} is not an exact integer")
    return value


def _canonical_absolute(value: object, label: str) -> str:
    if type(value) is not str:
        _fail(f"{label} is not an exact string")
    path = Path(value)
    if (
        not path.is_absolute()
        or value == "/"
        or str(path) != value
        or ".." in path.parts
        or value.endswith("/")
        or "//" in value
        or "\x00" in value
        or "\n" in value
    ):
        _fail(f"{label} is not canonical")
    return value


def _validate_sha256(value: object, label: str) -> str:
    if type(value) is not str or SHA256.fullmatch(value) is None:
        _fail(f"{label} is not one SHA-256")
    return value


def _validate_file(
    evidence: FileDescriptorEvidence,
    *,
    logical_path: str,
    resolved_path: str,
    link_target: str,
    uid: int,
    gid: int,
    mode: str,
    size: int,
    sha256: str,
) -> None:
    if type(evidence) is not FileDescriptorEvidence:
        _fail("file descriptor evidence has the wrong type")
    _canonical_absolute(evidence.logical_path, "logical file path")
    _canonical_absolute(evidence.resolved_path, "resolved file path")
    for value, label in (
        (evidence.uid, "file uid"),
        (evidence.gid, "file gid"),
        (evidence.nlink, "file link count"),
        (evidence.size, "file size"),
        (evidence.opened_device, "opened file device"),
        (evidence.opened_inode, "opened file inode"),
        (evidence.path_device, "revalidated file device"),
        (evidence.path_inode, "revalidated file inode"),
    ):
        _exact_int(value, label, 0)
    if (
        evidence.logical_path != logical_path
        or evidence.resolved_path != resolved_path
        or type(evidence.link_target) is not str
        or evidence.link_target != link_target
        or type(evidence.revalidated_link_target) is not str
        or evidence.revalidated_link_target != link_target
        or evidence.file_type != "regular"
        or evidence.uid != uid
        or evidence.gid != gid
        or evidence.mode != mode
        or evidence.nlink != 1
        or evidence.size != size
        or evidence.sha256 != sha256
        or evidence.opened_device <= 0
        or evidence.opened_inode <= 0
        or evidence.path_device != evidence.opened_device
        or evidence.path_inode != evidence.opened_inode
        or type(evidence.open_flags) is not tuple
        or evidence.open_flags != OPEN_FLAGS
    ):
        _fail("file descriptor identity is not exact")
    _validate_sha256(evidence.sha256, "file descriptor SHA-256")


def _validate_directory(
    evidence: DirectoryDescriptorEvidence,
    *,
    path: str,
    uid: int,
    gid: int,
) -> None:
    if type(evidence) is not DirectoryDescriptorEvidence:
        _fail("directory descriptor evidence has the wrong type")
    _canonical_absolute(evidence.logical_path, "logical directory path")
    _canonical_absolute(evidence.resolved_path, "resolved directory path")
    for value, label in (
        (evidence.uid, "directory uid"),
        (evidence.gid, "directory gid"),
        (evidence.opened_device, "opened directory device"),
        (evidence.opened_inode, "opened directory inode"),
        (evidence.path_device, "revalidated directory device"),
        (evidence.path_inode, "revalidated directory inode"),
    ):
        _exact_int(value, label, 0)
    if (
        evidence.logical_path != path
        or evidence.resolved_path != path
        or evidence.uid != uid
        or evidence.gid != gid
        or evidence.mode != "0700"
        or evidence.opened_device <= 0
        or evidence.opened_inode <= 0
        or evidence.path_device != evidence.opened_device
        or evidence.path_inode != evidence.opened_inode
        or type(evidence.open_flags) is not tuple
        or evidence.open_flags != DIRECTORY_OPEN_FLAGS
    ):
        _fail("directory descriptor identity is not exact")


def _validate_host_pin(
    inputs: CONTRACT.ExecutorInputs,
    evidence: HostPinEvidence,
    expected_sha256: str,
    uid: int,
    gid: int,
) -> str:
    if type(evidence) is not HostPinEvidence:
        _fail("fallback host pin evidence is absent")
    expected_sha256 = _validate_sha256(
        expected_sha256, "expected fallback host pin SHA-256"
    )
    if expected_sha256 == ZERO_SHA256:
        _fail("expected fallback host pin SHA-256 is zero")
    if type(evidence.payload) is not bytes:
        _fail("fallback host pin payload is not exact bytes")
    if not 1 <= len(evidence.payload) <= 4096:
        _fail("fallback host pin payload is outside its bound")
    digest = hashlib.sha256(evidence.payload).hexdigest()
    _validate_file(
        evidence.file,
        logical_path=inputs.fallback_known_hosts,
        resolved_path=inputs.fallback_known_hosts,
        link_target="none",
        uid=uid,
        gid=gid,
        mode="0600",
        size=len(evidence.payload),
        sha256=expected_sha256,
    )
    parent = str(Path(inputs.fallback_known_hosts).parent)
    _validate_directory(
        evidence.parent,
        path=parent,
        uid=uid,
        gid=gid,
    )
    if (
        digest != expected_sha256
        or evidence.file.sha256 != digest
        or Path(inputs.fallback_known_hosts).is_relative_to(REPO)
    ):
        _fail("fallback host pin snapshot identity is not exact")
    try:
        line = evidence.payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise BoundaryError("fallback host pin is not ASCII") from error
    if not line.endswith("\n") or line.count("\n") != 1:
        _fail("fallback host pin is not one canonical line")
    fields = line[:-1].split(" ")
    if (
        len(fields) != 3
        or any(not field for field in fields)
        or fields[0] != HOST_ALIAS
        or fields[1] != "ssh-ed25519"
    ):
        _fail("fallback host pin fields are not exact")
    try:
        key = base64.b64decode(fields[2], validate=True)
    except (binascii.Error, ValueError) as error:
        raise BoundaryError("fallback host pin key is not base64") from error
    if (
        len(key) != len(SSH_PREFIX) + 32
        or not key.startswith(SSH_PREFIX)
        or key[-32:] == b"\x00" * 32
        or base64.b64encode(key).decode("ascii") != fields[2]
    ):
        _fail("fallback host pin is not one nonzero Ed25519 key")
    return digest


def attest_descriptors(
    *,
    spec: CONTRACT.ProcessSpec,
    inputs: CONTRACT.ExecutorInputs,
    program: FileDescriptorEvidence,
    interpreter: FileDescriptorEvidence,
    repository_uid: int,
    repository_gid: int,
    host_pin: HostPinEvidence | None,
    expected_host_pin_sha256: str,
) -> DescriptorAttestation:
    """Validate supplied descriptor facts without opening any object."""

    if type(inputs) is not CONTRACT.ExecutorInputs:
        _fail("executor inputs have the wrong type")
    exact_specs = CONTRACT.process_specs(inputs)
    if type(spec) is not CONTRACT.ProcessSpec or spec not in exact_specs:
        _fail("process specification is not the reviewed contract")
    repository_uid = _exact_int(repository_uid, "repository uid", 0)
    repository_gid = _exact_int(repository_gid, "repository gid", 0)
    program_path = str(REPO / spec.program)
    _validate_file(
        program,
        logical_path=program_path,
        resolved_path=program_path,
        link_target="none",
        uid=repository_uid,
        gid=repository_gid,
        mode=spec.program_mode,
        size=spec.program_size,
        sha256=spec.program_sha256,
    )
    try:
        interpreter_identity = INTERPRETERS[spec.argv[0]]
    except KeyError as error:
        raise BoundaryError("process interpreter is not pinned") from error
    _validate_file(
        interpreter,
        logical_path=interpreter_identity.logical_path,
        resolved_path=interpreter_identity.resolved_path,
        link_target=interpreter_identity.link_target,
        uid=0,
        gid=0,
        mode="0755",
        size=interpreter_identity.size,
        sha256=interpreter_identity.sha256,
    )
    if spec.name == "fallback-reboot":
        if host_pin is None:
            _fail("fallback host pin evidence is absent")
        pin_sha256 = _validate_host_pin(
            inputs,
            host_pin,
            expected_host_pin_sha256,
            repository_uid,
            repository_gid,
        )
    else:
        if host_pin is not None or expected_host_pin_sha256 != "none":
            _fail("an unrelated action received fallback host pin evidence")
        pin_sha256 = "none"
    return DescriptorAttestation(
        name=spec.name,
        program_sha256=spec.program_sha256,
        interpreter_sha256=interpreter_identity.sha256,
        host_pin_sha256=pin_sha256,
    )


def _validate_process_outcome(
    spec: CONTRACT.ProcessSpec,
    outcome: ProcessOutcome,
) -> bytes:
    if type(outcome) is not ProcessOutcome or outcome.name != spec.name:
        _fail("process outcome does not name the reviewed action")
    if (
        type(outcome.exit_code) is not int
        or outcome.exit_code != 0
        or (
            outcome.term_signal is not None
            and (
                type(outcome.term_signal) is not int
                or outcome.term_signal <= 0
            )
        )
        or outcome.term_signal is not None
        or type(outcome.timed_out) is not bool
        or outcome.timed_out
        or type(outcome.output_overflow) is not bool
        or outcome.output_overflow
        or type(outcome.stdout) is not bytes
        or type(outcome.stderr) is not bytes
        or len(outcome.stdout) > spec.output_limit_bytes
        or len(outcome.stderr) > spec.output_limit_bytes
        or not outcome.stdout
        or not outcome.stdout.endswith(b"\n")
        or b"\x00" in outcome.stdout
        or b"\r" in outcome.stdout
    ):
        _fail("process result is not one clean bounded success")
    if spec.name not in BOOT_ACTIONS and outcome.stderr:
        _fail("non-boot process wrote unexpected stderr")
    try:
        outcome.stdout.decode("ascii")
        outcome.stderr.decode("ascii")
    except UnicodeDecodeError as error:
        raise BoundaryError("process output is not ASCII") from error
    if b"\x00" in outcome.stderr or b"\r" in outcome.stderr:
        _fail("process stderr is not canonical diagnostics")
    return outcome.stdout


def _boot_result(
    spec: CONTRACT.ProcessSpec,
    inputs: CONTRACT.ExecutorInputs,
    stdout: bytes,
    stderr: bytes,
    attestation: DescriptorAttestation | None,
) -> dict[str, object]:
    if (
        type(attestation) is not DescriptorAttestation
        or attestation.name != spec.name
        or attestation.program_sha256 != spec.program_sha256
        or attestation.interpreter_sha256
        != INTERPRETERS[spec.argv[0]].sha256
    ):
        _fail("boot output lacks its exact descriptor attestation")
    if spec.name == "fallback-reboot":
        if (
            SHA256.fullmatch(attestation.host_pin_sha256) is None
            or attestation.host_pin_sha256 == ZERO_SHA256
        ):
            _fail("fallback output lacks its public host-pin attestation")
    elif attestation.host_pin_sha256 != "none":
        _fail("non-fallback output unexpectedly carries a host pin")

    lines = stdout.splitlines(keepends=True)
    records = [line for line in lines if line.startswith(BOOT_RESULT_PREFIX)]
    if (
        stdout.count(BOOT_RESULT_PREFIX) != 1
        or BOOT_RESULT_PREFIX in stderr
        or len(records) != 1
        or not lines
        or lines[-1] != records[0]
    ):
        _fail("boot output lacks one terminal canonical result")
    expected_lines = {
        "execution-boot": (
            "ROG5_RETENTION_BOOT_RESULT_V1 action=execution-boot "
            f"recovery_sha256={ADAPTER.JOURNAL.EXECUTION_RECOVERY_SHA256} "
            f"rollback_armed=1 usb_location={inputs.usb_location}\n"
        ),
        "fallback-reboot": (
            "ROG5_RETENTION_BOOT_RESULT_V1 action=fallback-reboot "
            f"fastboot_serial={inputs.fastboot_serial} "
            f"host_pin_sha256={attestation.host_pin_sha256} "
            "product=0b05:4daf "
            f"usb_location={inputs.usb_location}\n"
        ),
        "observer-boot": (
            "ROG5_RETENTION_BOOT_RESULT_V1 action=observer-boot "
            f"fastboot_serial={inputs.fastboot_serial} "
            f"recovery_sha256={ADAPTER.JOURNAL.OBSERVER_RECOVERY_SHA256} "
            f"rollback_armed=1 usb_location={inputs.usb_location}\n"
        ),
    }
    if records[0] != expected_lines[spec.name].encode("ascii"):
        _fail("boot result is not the exact reviewed record")
    results: dict[str, dict[str, object]] = {
        "execution-boot": {
            "recovery_sha256": ADAPTER.JOURNAL.EXECUTION_RECOVERY_SHA256,
            "rollback_armed": True,
            "usb_location": inputs.usb_location,
        },
        "fallback-reboot": {
            "fastboot_serial": inputs.fastboot_serial,
            "product": "0b05:4daf",
            "usb_location": inputs.usb_location,
        },
        "observer-boot": {
            "fastboot_serial": inputs.fastboot_serial,
            "recovery_sha256": ADAPTER.JOURNAL.OBSERVER_RECOVERY_SHA256,
            "rollback_armed": True,
            "usb_location": inputs.usb_location,
        },
    }
    return results[spec.name]


def _decimal(value: object, label: str, maximum: int) -> int:
    if (
        type(value) is not str
        or not value.isascii()
        or not value.isdecimal()
        or (len(value) > 1 and value.startswith("0"))
        or len(value) > len(str(maximum))
        or int(value) > maximum
    ):
        _fail(f"{label} is not canonical")
    return int(value)


def _postmortem_result(
    inputs: CONTRACT.ExecutorInputs,
    stdout: bytes,
) -> dict[str, object]:
    pairs_seen: list[tuple[str, object]] = []

    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            _fail("postmortem JSON has duplicate fields")
        pairs_seen.extend(pairs)
        return dict(pairs)

    try:
        record = json.loads(
            stdout.decode("ascii"), object_pairs_hook=no_duplicates
        )
    except (BoundaryError, json.JSONDecodeError) as error:
        if isinstance(error, BoundaryError):
            raise
        raise BoundaryError("postmortem output is not JSON") from error
    expected_fields = {
        "classification",
        "expected_boot_id",
        "expected_candidate",
        "expected_lineage_sha256",
        "observed_lineage_matches",
        "observed_lineage_sha256",
        "postmortem_bytes",
        "postmortem_records",
        "postmortem_sha256",
        "postmortem_state",
        "recovery_session",
        "status_request",
    }
    if (
        type(record) is not dict
        or set(record) != expected_fields
        or len(pairs_seen) != len(expected_fields)
        or any(type(value) is not str for value in record.values())
        or (
            json.dumps(record, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
        != stdout
    ):
        _fail("postmortem JSON is not one canonical exact record")
    candidate = ADAPTER.JOURNAL.CANDIDATE
    expected_lineage = hashlib.sha256(
        (
            "rog5-network-root: lineage "
            f"format=rog5-target-lineage-v1 candidate={candidate} "
            f"boot_id={inputs.target_boot_id}"
        ).encode("ascii")
    ).hexdigest()
    classification = record["classification"]
    state = record["postmortem_state"]
    records = _decimal(record["postmortem_records"], "record count", 64)
    size = _decimal(record["postmortem_bytes"], "postmortem size", 4194304)
    matches = _decimal(
        record["observed_lineage_matches"], "lineage match count", 65535
    )
    postmortem_sha256 = _validate_sha256(
        record["postmortem_sha256"], "postmortem SHA-256"
    )
    observed_sha256 = _validate_sha256(
        record["observed_lineage_sha256"], "observed lineage SHA-256"
    )
    if (
        record["expected_candidate"] != candidate
        or record["expected_boot_id"] != inputs.target_boot_id
        or record["expected_lineage_sha256"] != expected_lineage
        or REQUEST_ID.fullmatch(record["recovery_session"]) is None
        or REQUEST_ID.fullmatch(record["status_request"]) is None
        or classification not in ADAPTER.JOURNAL.POSTMORTEM_CLASSIFICATIONS
        or state not in {"UNAVAILABLE", "EMPTY", "PRESENT"}
    ):
        _fail("postmortem lineage identity is not exact")
    if state == "UNAVAILABLE" and (
        records != 0
        or size != 0
        or postmortem_sha256 != ZERO_SHA256
        or matches != 0
        or observed_sha256 != ZERO_SHA256
        or classification != "UNAVAILABLE"
    ):
        _fail("unavailable postmortem result is inconsistent")
    if state == "EMPTY" and (
        records != 0
        or size != 0
        or postmortem_sha256 != EMPTY_SHA256
        or matches != 0
        or observed_sha256 != ZERO_SHA256
        or classification != "NO_RECORDS"
    ):
        _fail("empty postmortem result is inconsistent")
    if state == "PRESENT" and (
        records == 0 or size == 0 or postmortem_sha256 == ZERO_SHA256
    ):
        _fail("present postmortem result is inconsistent")
    if classification == "NO_MARKER" and (
        state != "PRESENT" or matches != 0 or observed_sha256 != ZERO_SHA256
    ):
        _fail("no-marker classification is inconsistent")
    if classification == "AMBIGUOUS" and (
        state != "PRESENT" or matches < 2 or observed_sha256 != ZERO_SHA256
    ):
        _fail("ambiguous classification is inconsistent")
    if classification == "DIFFERENT_MARKER" and (
        state != "PRESENT"
        or matches < 1
        or observed_sha256 in {ZERO_SHA256, expected_lineage}
    ):
        _fail("different-marker classification is inconsistent")
    if classification == "MATCH" and (
        state != "PRESENT"
        or matches != 1
        or observed_sha256 != expected_lineage
    ):
        _fail("match classification is inconsistent")
    if classification == "MATCH_REPEATED" and (
        state != "PRESENT"
        or matches < 2
        or observed_sha256 != expected_lineage
    ):
        _fail("repeated-match classification is inconsistent")
    return {
        "candidate": candidate,
        "classification": classification,
        "reads": 1,
        "target_boot_id": inputs.target_boot_id,
    }


def decode_process_outcome(
    spec: CONTRACT.ProcessSpec,
    inputs: CONTRACT.ExecutorInputs,
    outcome: ProcessOutcome,
    *,
    attestation: DescriptorAttestation | None = None,
) -> dict[str, object]:
    """Decode only outputs that prove the adapter's complete result."""

    if type(inputs) is not CONTRACT.ExecutorInputs:
        _fail("executor inputs have the wrong type")
    exact_specs = CONTRACT.process_specs(inputs)
    if type(spec) is not CONTRACT.ProcessSpec or spec not in exact_specs:
        _fail("process specification is not the reviewed contract")
    stdout = _validate_process_outcome(spec, outcome)
    if spec.name in BOOT_ACTIONS:
        return _boot_result(
            spec, inputs, stdout, outcome.stderr, attestation
        )
    if attestation is not None:
        _fail("non-boot decoder received unexpected descriptor state")
    if spec.name in {"execution-claim", "observer-claim"}:
        identifier = (
            ADAPTER.JOURNAL.EXECUTION_CLAIM_IDENTIFIER
            if spec.name == "execution-claim"
            else ADAPTER.JOURNAL.OBSERVER_CLAIM_IDENTIFIER
        )
        digest = (
            ADAPTER.JOURNAL.EXECUTION_CLAIM_SHA256
            if spec.name == "execution-claim"
            else ADAPTER.JOURNAL.OBSERVER_CLAIM_SHA256
        )
        expected = (
            f"PASS exact durable BOOT_CLAIMED record entered: {identifier}\n"
        ).encode("ascii")
        if stdout != expected:
            _fail("claim output is not one exact consumed-record marker")
        return {
            "identifier": identifier,
            "record_sha256": digest,
            "state": "consumed",
        }
    if spec.name == "postmortem-read":
        return _postmortem_result(inputs, stdout)
    _fail("process action has no reviewed output decoder")
