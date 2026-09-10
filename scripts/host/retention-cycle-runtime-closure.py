"""Disconnected fresh-intent/fresh-pipe fixture for retention-cycle review."""

from __future__ import annotations

from dataclasses import dataclass, replace as dataclass_replace
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import stat
import sys
import time
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
BOUNDARY_PATH = Path(__file__).with_name(
    "retention-cycle-executor-boundary.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_executor_boundary_for_runtime_closure",
    BOUNDARY_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("retention executor boundary is unavailable")
BOUNDARY = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = BOUNDARY
_SPEC.loader.exec_module(BOUNDARY)
CONTRACT = BOUNDARY.CONTRACT
ADAPTER = CONTRACT.ADAPTER
JOURNAL = ADAPTER.JOURNAL

LIVE_ENTRYPOINT = "none"
ADAPTER_WIRING = "none"
PRODUCTION_EXECUTION = "none"
CONNECTED_ADMISSION = "none"
CREDENTIAL_USE = "none"
RESULT_AUTHORITY = "none"

RESULT_EVENT_BY_ACTION = {
    "execution-claim": "execution-claim-entered",
    "execution-boot": "execution-recovery-observed",
    "fallback-reboot": "bootloader-observed",
    "observer-claim": "observer-claim-entered",
    "observer-boot": "observer-recovery-observed",
    "postmortem-read": "postmortem-result",
}

SHA256 = BOUNDARY.SHA256
ZERO_SHA256 = BOUNDARY.ZERO_SHA256
MAX_INTENT_BYTES = 4096
MAX_FIXTURE_DEADLINE_MILLISECONDS = 5000
PIPE_FLAGS = os.O_CLOEXEC | os.O_NONBLOCK
FILE_OPEN_FLAGS = os.O_RDONLY | os.O_CLOEXEC | getattr(
    os, "O_NOFOLLOW", 0
)
DIRECTORY_OPEN_FLAGS = (
    os.O_RDONLY
    | os.O_CLOEXEC
    | os.O_DIRECTORY
    | getattr(os, "O_NOFOLLOW", 0)
)
EVIDENCE_OPEN_FLAGS = ("O_CLOEXEC", "O_NOFOLLOW", "O_RDONLY")
EVIDENCE_DIRECTORY_OPEN_FLAGS = (
    "O_CLOEXEC",
    "O_DIRECTORY",
    "O_NOFOLLOW",
    "O_RDONLY",
)
JOURNAL_MARKER = "_rog5_runtime_closure_prepared"


class RuntimeClosureError(RuntimeError):
    """The offline runtime fixture cannot prove one exact action."""


def _fail(message: str) -> NoReturn:
    raise RuntimeClosureError(message)


@dataclass(frozen=True)
class IntentAttestation:
    action: str
    required_intent: str
    cycle_sha256: str
    event_index: int
    event_sha256: str
    opened_device: int
    opened_inode: int
    path_device: int
    path_inode: int
    path: Path
    checked_ns: int


@dataclass(frozen=True)
class OfflineChildPlan:
    """Fixed child behavior for hardware-free process-control tests only."""

    stdout: bytes
    stderr: bytes
    exit_code: int
    delay_milliseconds: int
    descendant_holds_pipes: bool


@dataclass(frozen=True)
class RuntimeProof:
    action: str
    intent: IntentAttestation
    runtime_nonce: str
    stdout_pipe_device: int
    stdout_pipe_inode: int
    stderr_pipe_device: int
    stderr_pipe_inode: int
    pipe_created_ns: int
    spawned_ns: int
    finished_ns: int
    stdout_eof: bool
    stderr_eof: bool
    outcome: BOUNDARY.ProcessOutcome


@dataclass(frozen=True)
class OfflineDecodedProof:
    action: str
    intent_sha256: str
    runtime_nonce: str
    result: dict[str, object]
    authority: str
    adapter_eligible: bool


@dataclass(frozen=True)
class StatIdentity:
    device: int
    inode: int
    mode: int
    uid: int
    gid: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class _HeldObject:
    descriptor: int
    path: Path
    opened: StatIdentity
    digest: str | None
    symlink_path: Path | None = None
    symlink_target: str = "none"


def _metadata(metadata: os.stat_result) -> StatIdentity:
    return StatIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        uid=metadata.st_uid,
        gid=metadata.st_gid,
        links=metadata.st_nlink,
        size=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
        changed_ns=metadata.st_ctime_ns,
    )


def _same_object(first: os.stat_result, second: os.stat_result) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


def _read_regular(
    descriptor: int, expected_size: int, label: str
) -> bytes:
    before = os.fstat(descriptor)
    if expected_size < 0 or before.st_size != expected_size:
        _fail(f"{label} size changed")
    os.lseek(descriptor, 0, os.SEEK_SET)
    payload = bytearray()
    while len(payload) <= expected_size:
        block = os.read(
            descriptor,
            min(65536, expected_size + 1 - len(payload)),
        )
        if not block:
            break
        payload.extend(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    after = os.fstat(descriptor)
    if len(payload) != expected_size or _metadata(before) != _metadata(after):
        _fail(f"{label} changed while being read")
    return bytes(payload)


def _open_exact_regular(
    *,
    logical_path: Path,
    resolved_path: Path,
    link_target: str,
    uid: int,
    gid: int,
    mode: int,
    size: int,
    digest: str,
    label: str,
) -> tuple[int, BOUNDARY.FileDescriptorEvidence, _HeldObject]:
    if not logical_path.is_absolute() or not resolved_path.is_absolute():
        _fail(f"{label} path is not absolute")
    if link_target == "none":
        logical = logical_path.lstat()
        if not stat.S_ISREG(logical.st_mode) or logical_path != resolved_path:
            _fail(f"{label} path is not one regular file")
    else:
        logical = logical_path.lstat()
        if (
            not stat.S_ISLNK(logical.st_mode)
            or logical.st_uid != 0
            or logical.st_gid != 0
            or os.readlink(logical_path) != link_target
        ):
            _fail(f"{label} logical symlink changed")
    descriptor = -1
    try:
        descriptor = os.open(resolved_path, FILE_OPEN_FLAGS)
        opened = os.fstat(descriptor)
        named = resolved_path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not _same_object(opened, named)
            or opened.st_uid != uid
            or opened.st_gid != gid
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != mode
            or opened.st_size != size
        ):
            _fail(f"{label} metadata is not exact")
        payload = _read_regular(descriptor, size, label)
        observed_digest = hashlib.sha256(payload).hexdigest()
        if observed_digest != digest:
            _fail(f"{label} digest is not exact")
        if link_target != "none" and os.readlink(logical_path) != link_target:
            _fail(f"{label} logical symlink changed")
        evidence = BOUNDARY.FileDescriptorEvidence(
            logical_path=str(logical_path),
            resolved_path=str(resolved_path),
            link_target=link_target,
            revalidated_link_target=link_target,
            file_type="regular",
            uid=opened.st_uid,
            gid=opened.st_gid,
            mode=f"{stat.S_IMODE(opened.st_mode):04o}",
            nlink=opened.st_nlink,
            size=opened.st_size,
            sha256=observed_digest,
            opened_device=opened.st_dev,
            opened_inode=opened.st_ino,
            path_device=named.st_dev,
            path_inode=named.st_ino,
            open_flags=EVIDENCE_OPEN_FLAGS,
        )
        held = _HeldObject(
            descriptor=descriptor,
            path=resolved_path,
            opened=_metadata(opened),
            digest=observed_digest,
            symlink_path=logical_path if link_target != "none" else None,
            symlink_target=link_target,
        )
        return descriptor, evidence, held
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _open_host_pin(
    inputs: CONTRACT.ExecutorInputs,
    expected_digest: str,
    repository_uid: int,
    repository_gid: int,
) -> tuple[
    tuple[int, int],
    BOUNDARY.HostPinEvidence,
    tuple[_HeldObject, _HeldObject],
]:
    path = Path(inputs.fallback_known_hosts)
    parent = path.parent
    parent_descriptor = -1
    pin_descriptor = -1
    try:
        if parent.resolve(strict=True) != parent:
            _fail("fallback host pin parent is not canonical")
        parent_descriptor = os.open(parent, DIRECTORY_OPEN_FLAGS)
        parent_opened = os.fstat(parent_descriptor)
        parent_named = parent.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(parent_opened.st_mode)
            or not _same_object(parent_opened, parent_named)
            or parent_opened.st_uid != repository_uid
            or parent_opened.st_gid != repository_gid
            or stat.S_IMODE(parent_opened.st_mode) != 0o700
        ):
            _fail("fallback host pin parent metadata is not exact")
        pin_descriptor = os.open(
            path.name, FILE_OPEN_FLAGS, dir_fd=parent_descriptor
        )
        pin_opened = os.fstat(pin_descriptor)
        pin_named = os.stat(
            path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(pin_opened.st_mode)
            or not _same_object(pin_opened, pin_named)
            or pin_opened.st_uid != repository_uid
            or pin_opened.st_gid != repository_gid
            or pin_opened.st_nlink != 1
            or stat.S_IMODE(pin_opened.st_mode) != 0o600
            or not 1 <= pin_opened.st_size <= 4096
        ):
            _fail("fallback host pin metadata is not exact")
        payload = _read_regular(
            pin_descriptor, pin_opened.st_size, "fallback host pin"
        )
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected_digest:
            _fail("fallback host pin digest is not exact")
        file_evidence = BOUNDARY.FileDescriptorEvidence(
            logical_path=str(path),
            resolved_path=str(path),
            link_target="none",
            revalidated_link_target="none",
            file_type="regular",
            uid=pin_opened.st_uid,
            gid=pin_opened.st_gid,
            mode="0600",
            nlink=pin_opened.st_nlink,
            size=pin_opened.st_size,
            sha256=digest,
            opened_device=pin_opened.st_dev,
            opened_inode=pin_opened.st_ino,
            path_device=pin_named.st_dev,
            path_inode=pin_named.st_ino,
            open_flags=EVIDENCE_OPEN_FLAGS,
        )
        parent_evidence = BOUNDARY.DirectoryDescriptorEvidence(
            logical_path=str(parent),
            resolved_path=str(parent),
            uid=parent_opened.st_uid,
            gid=parent_opened.st_gid,
            mode="0700",
            opened_device=parent_opened.st_dev,
            opened_inode=parent_opened.st_ino,
            path_device=parent_named.st_dev,
            path_inode=parent_named.st_ino,
            open_flags=EVIDENCE_DIRECTORY_OPEN_FLAGS,
        )
        return (
            (pin_descriptor, parent_descriptor),
            BOUNDARY.HostPinEvidence(
                file=file_evidence,
                parent=parent_evidence,
                payload=payload,
            ),
            (
                _HeldObject(
                    pin_descriptor,
                    path,
                    _metadata(pin_opened),
                    digest,
                ),
                _HeldObject(
                    parent_descriptor,
                    parent,
                    _metadata(parent_opened),
                    None,
                ),
            ),
        )
    except BaseException:
        if pin_descriptor >= 0:
            os.close(pin_descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)
        raise


def _open_journal_event(
    journal: JOURNAL.CycleJournal,
    path: Path,
    expected_index: int,
    expected_name: str,
    label: str,
) -> tuple[int, dict[str, Any], bytes, _HeldObject]:
    descriptor = -1
    try:
        descriptor = os.open(
            path.name, FILE_OPEN_FLAGS, dir_fd=journal.cycle_descriptor
        )
        opened = os.fstat(descriptor)
        named = os.stat(
            path.name,
            dir_fd=journal.cycle_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or not _same_object(opened, named)
            or opened.st_uid != os.geteuid()
            or opened.st_gid != os.getegid()
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
            or not 1 <= opened.st_size <= MAX_INTENT_BYTES
        ):
            _fail(f"{label} metadata is not exact")
        payload = _read_regular(descriptor, opened.st_size, label)
        try:
            value = json.loads(
                payload,
                object_pairs_hook=JOURNAL.reject_duplicate_keys,
            )
        except (UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeClosureError(
                f"{label} is not canonical JSON"
            ) from error
        expected_keys = {
            "cycle_sha256",
            "data",
            "format",
            "index",
            "name",
            "previous_sha256",
        }
        if (
            type(value) is not dict
            or set(value) != expected_keys
            or JOURNAL.canonical_json(value) != payload
            or value["format"] != "rog5-retention-cycle-event-v1"
            or value["cycle_sha256"] != JOURNAL.CYCLE_SHA256
            or value["index"] != expected_index
            or value["name"] != expected_name
            or type(value["data"]) is not dict
            or SHA256.fullmatch(value["previous_sha256"]) is None
        ):
            _fail(f"{label} identity is not exact")
        digest = hashlib.sha256(payload).hexdigest()
        held = _HeldObject(
            descriptor,
            path,
            _metadata(opened),
            digest,
        )
        return descriptor, value, payload, held
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _open_intent(
    journal: JOURNAL.CycleJournal,
    action: str,
    required_intent: str,
) -> tuple[int, IntentAttestation, _HeldObject]:
    paths = journal.event_paths()
    if not paths:
        _fail("action has no durable intent record")
    path = paths[-1]
    index = len(paths) - 1
    descriptor, _, payload, held = _open_journal_event(
        journal,
        path,
        index,
        required_intent,
        "intent record",
    )
    try:
        opened = os.fstat(descriptor)
        intent = IntentAttestation(
            action=action,
            required_intent=required_intent,
            cycle_sha256=JOURNAL.CYCLE_SHA256,
            event_index=index,
            event_sha256=hashlib.sha256(payload).hexdigest(),
            opened_device=opened.st_dev,
            opened_inode=opened.st_ino,
            path_device=opened.st_dev,
            path_inode=opened.st_ino,
            path=path,
            checked_ns=time.monotonic_ns(),
        )
        return descriptor, intent, held
    except BaseException:
        os.close(descriptor)
        raise


class PreparedAction:
    """Held descriptors and one unexecuted action-intent binding."""

    def __init__(
        self,
        *,
        journal: JOURNAL.CycleJournal,
        spec: CONTRACT.ProcessSpec,
        inputs: CONTRACT.ExecutorInputs,
        intent: IntentAttestation,
        descriptors: BOUNDARY.DescriptorAttestation,
        held: tuple[_HeldObject, ...],
        host_pin_payload: bytes,
        snapshot: dict[str, Any],
        marker: str,
    ) -> None:
        self.journal = journal
        self.spec = spec
        self.inputs = inputs
        self.intent = intent
        self.descriptors = descriptors
        self._held = held
        self.host_pin_payload = host_pin_payload
        self._snapshot = snapshot
        self._marker = marker
        self._closed = False
        self._attempted = False
        self._decoded = False
        self._decode_succeeded = False
        self._decoded_result: dict[str, object] | None = None
        self._finalized = False
        self._proof: RuntimeProof | None = None

    @property
    def action(self) -> str:
        return self.spec.name

    @property
    def held_descriptors(self) -> tuple[int, ...]:
        return tuple(item.descriptor for item in self._held)

    @property
    def attempted(self) -> bool:
        return self._attempted

    def __enter__(self) -> "PreparedAction":
        if self._closed:
            _fail("prepared action is closed")
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for held in self._held:
            try:
                os.close(held.descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
        if (
            not self._attempted
            and getattr(self.journal, JOURNAL_MARKER, None) == self._marker
        ):
            delattr(self.journal, JOURNAL_MARKER)


def _revalidate_held(held: _HeldObject, label: str) -> None:
    try:
        opened = os.fstat(held.descriptor)
        named = held.path.stat(follow_symlinks=False)
    except OSError as error:
        raise RuntimeClosureError(f"{label} changed") from error
    if _metadata(opened) != held.opened or _metadata(named) != held.opened:
        _fail(f"{label} changed")
    if held.digest is not None:
        payload = _read_regular(held.descriptor, opened.st_size, label)
        if hashlib.sha256(payload).hexdigest() != held.digest:
            _fail(f"{label} changed")
    if held.symlink_path is not None:
        try:
            target = os.readlink(held.symlink_path)
        except OSError as error:
            raise RuntimeClosureError(f"{label} symlink changed") from error
        if target != held.symlink_target:
            _fail(f"{label} symlink changed")


def _revalidate_journal_event(
    journal: JOURNAL.CycleJournal,
    held: _HeldObject,
    label: str,
) -> None:
    try:
        opened = os.fstat(held.descriptor)
        named = os.stat(
            held.path.name,
            dir_fd=journal.cycle_descriptor,
            follow_symlinks=False,
        )
    except OSError as error:
        raise RuntimeClosureError(f"{label} changed") from error
    if _metadata(opened) != held.opened or _metadata(named) != held.opened:
        _fail(f"{label} changed")
    if held.digest is None:
        _fail(f"{label} digest is unavailable")
    payload = _read_regular(held.descriptor, opened.st_size, label)
    if hashlib.sha256(payload).hexdigest() != held.digest:
        _fail(f"{label} changed")


def _revalidate_prepared(prepared: PreparedAction) -> None:
    if type(prepared) is not PreparedAction or prepared._closed:
        _fail("prepared action is unavailable")
    if getattr(prepared.journal, JOURNAL_MARKER, None) != prepared._marker:
        _fail("prepared action ownership changed")
    try:
        snapshot = prepared.journal.snapshot()
    except Exception as error:
        raise RuntimeClosureError("journal changed during action") from error
    if snapshot != prepared._snapshot:
        _fail("journal changed during action")

    _revalidate_descriptors(prepared)


def _revalidate_descriptors(prepared: PreparedAction) -> None:
    labels = [
        "intent record",
        "program descriptor",
        "interpreter descriptor",
    ]
    if len(prepared._held) == 5:
        labels.extend(("fallback host pin", "fallback host pin parent"))
    for held, label in zip(prepared._held, labels, strict=True):
        try:
            _revalidate_held(held, label)
        except RuntimeClosureError as error:
            if label == "intent record":
                raise RuntimeClosureError("intent record changed") from error
            raise


def prepare_action(
    *,
    journal: JOURNAL.CycleJournal,
    spec: CONTRACT.ProcessSpec,
    inputs: CONTRACT.ExecutorInputs,
    expected_host_pin_sha256: str,
) -> PreparedAction:
    """Hold exact descriptors after one freshly appended durable intent."""

    if type(journal) is not JOURNAL.CycleJournal:
        _fail("journal has the wrong type")
    if getattr(journal, "_reopened", True) is not False:
        _fail("reopened action intent is terminal and cannot be prepared")
    if hasattr(journal, JOURNAL_MARKER):
        _fail("action intent is already prepared")
    if type(inputs) is not CONTRACT.ExecutorInputs:
        _fail("executor inputs have the wrong type")
    exact_specs = CONTRACT.process_specs(inputs)
    if type(spec) is not CONTRACT.ProcessSpec or spec not in exact_specs:
        _fail("process specification is not the reviewed contract")
    invocation = next(
        (item for item in ADAPTER.INVOCATIONS if item.name == spec.name), None
    )
    if invocation is None:
        _fail("process action is not adapter-owned")
    snapshot = journal.snapshot()
    if snapshot["phase"] != invocation.required_intent:
        _fail("process action lacks its fresh durable intent")
    if spec.name == "fallback-reboot":
        if (
            type(expected_host_pin_sha256) is not str
            or SHA256.fullmatch(expected_host_pin_sha256) is None
            or expected_host_pin_sha256 == ZERO_SHA256
        ):
            _fail("fallback host pin digest is not exact")
    elif expected_host_pin_sha256 != "none":
        _fail("unrelated action received a host pin digest")

    marker = os.getrandom(32).hex()
    setattr(journal, JOURNAL_MARKER, marker)
    opened: list[_HeldObject] = []
    try:
        _, intent, intent_held = _open_intent(
            journal, spec.name, invocation.required_intent
        )
        opened.append(intent_held)
        repository_uid = os.geteuid()
        repository_gid = os.getegid()
        program_path = REPO / spec.program
        _, program, program_held = _open_exact_regular(
            logical_path=program_path,
            resolved_path=program_path,
            link_target="none",
            uid=repository_uid,
            gid=repository_gid,
            mode=int(spec.program_mode, 8),
            size=spec.program_size,
            digest=spec.program_sha256,
            label="program descriptor",
        )
        opened.append(program_held)
        interpreter_identity = BOUNDARY.INTERPRETERS.get(spec.argv[0])
        if interpreter_identity is None:
            _fail("process interpreter is not pinned")
        _, interpreter, interpreter_held = _open_exact_regular(
            logical_path=Path(interpreter_identity.logical_path),
            resolved_path=Path(interpreter_identity.resolved_path),
            link_target=interpreter_identity.link_target,
            uid=0,
            gid=0,
            mode=0o755,
            size=interpreter_identity.size,
            digest=interpreter_identity.sha256,
            label="interpreter descriptor",
        )
        opened.append(interpreter_held)
        host_pin = None
        host_pin_payload = b""
        if spec.name == "fallback-reboot":
            _, host_pin, pin_held = _open_host_pin(
                inputs,
                expected_host_pin_sha256,
                repository_uid,
                repository_gid,
            )
            opened.extend(pin_held)
            host_pin_payload = host_pin.payload
        descriptors = BOUNDARY.attest_descriptors(
            spec=spec,
            inputs=inputs,
            program=program,
            interpreter=interpreter,
            repository_uid=repository_uid,
            repository_gid=repository_gid,
            host_pin=host_pin,
            expected_host_pin_sha256=expected_host_pin_sha256,
        )
        prepared = PreparedAction(
            journal=journal,
            spec=spec,
            inputs=inputs,
            intent=intent,
            descriptors=descriptors,
            held=tuple(opened),
            host_pin_payload=host_pin_payload,
            snapshot=snapshot,
            marker=marker,
        )
        _revalidate_prepared(prepared)
        return prepared
    except BaseException:
        for held in opened:
            try:
                os.close(held.descriptor)
            except OSError:
                pass
        if getattr(journal, JOURNAL_MARKER, None) == marker:
            delattr(journal, JOURNAL_MARKER)
        raise


def _new_pipe() -> tuple[int, int]:
    return os.pipe2(PIPE_FLAGS)


def _require_empty_pipe(descriptor: int) -> None:
    try:
        payload = os.read(descriptor, 1)
    except BlockingIOError:
        return
    if payload or payload == b"":
        _fail("fresh pipe was not empty")


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written < 1:
            os._exit(125)
        view = view[written:]


def _signal_group(pid: int, selected: signal.Signals) -> None:
    try:
        os.killpg(pid, selected)
    except ProcessLookupError:
        try:
            os.kill(pid, selected)
        except ProcessLookupError:
            pass


def _wait_nonblocking(pid: int) -> int | None:
    try:
        observed, status_value = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return None
    return status_value if observed == pid else None


def _reap_after_stop(pid: int, current_status: int | None) -> int:
    _signal_group(pid, signal.SIGTERM)
    deadline = time.monotonic() + 0.1
    status_value = current_status
    while status_value is None and time.monotonic() < deadline:
        status_value = _wait_nonblocking(pid)
        if status_value is None:
            time.sleep(0.005)
    _signal_group(pid, signal.SIGKILL)
    if status_value is None:
        try:
            _, status_value = os.waitpid(pid, 0)
        except ChildProcessError:
            status_value = 0
    return status_value


def _child_main(
    plan: OfflineChildPlan,
    devnull: int,
    stdout_read: int,
    stdout_write: int,
    stderr_read: int,
    stderr_write: int,
) -> NoReturn:
    try:
        os.setsid()
        os.dup2(devnull, 0)
        os.dup2(stdout_write, 1)
        os.dup2(stderr_write, 2)
        descriptor_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        if descriptor_limit == resource.RLIM_INFINITY:
            descriptor_limit = 1048576
        os.closerange(3, int(descriptor_limit))
        os.set_blocking(1, True)
        os.set_blocking(2, True)
        if plan.descendant_holds_pipes:
            descendant = os.fork()
            if descendant == 0:
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                time.sleep(10)
                os._exit(0)
        if plan.delay_milliseconds:
            time.sleep(plan.delay_milliseconds / 1000)
        _write_all(1, plan.stdout)
        _write_all(2, plan.stderr)
        os.close(1)
        os.close(2)
        os._exit(plan.exit_code)
    except BaseException:
        os._exit(125)


def _validate_plan(
    plan: OfflineChildPlan,
    output_limit: int,
    deadline_milliseconds: int,
) -> None:
    if (
        type(plan) is not OfflineChildPlan
        or type(plan.stdout) is not bytes
        or type(plan.stderr) is not bytes
        or len(plan.stdout) > output_limit + 1
        or len(plan.stderr) > output_limit + 1
        or type(plan.exit_code) is not int
        or not 0 <= plan.exit_code <= 125
        or type(plan.delay_milliseconds) is not int
        or not 0 <= plan.delay_milliseconds <= 5000
        or type(plan.descendant_holds_pipes) is not bool
        or type(deadline_milliseconds) is not int
        or not 1
        <= deadline_milliseconds
        <= MAX_FIXTURE_DEADLINE_MILLISECONDS
    ):
        _fail("offline child plan is not bounded and exact")


def _read_ready(
    descriptor: int,
    buffer: bytearray,
    limit: int,
) -> tuple[bool, bool]:
    remaining = limit + 1 - len(buffer)
    if remaining <= 0:
        return False, True
    try:
        block = os.read(descriptor, min(65536, remaining))
    except BlockingIOError:
        return False, False
    if not block:
        return True, False
    buffer.extend(block)
    return False, len(buffer) > limit


def run_offline_fixture(
    prepared: PreparedAction,
    plan: OfflineChildPlan,
    *,
    deadline_milliseconds: int,
) -> RuntimeProof:
    """Fork only the fixed offline writer; never invoke a process spec."""

    if type(prepared) is not PreparedAction or prepared._closed:
        _fail("prepared action is unavailable")
    if prepared._attempted:
        _fail("prepared action was already attempted")
    prepared._attempted = True
    _validate_plan(
        plan, prepared.spec.output_limit_bytes, deadline_milliseconds
    )
    _revalidate_prepared(prepared)

    stdout_read = stdout_write = stderr_read = stderr_write = devnull = -1
    pid = -1
    child_status: int | None = None
    try:
        stdout_read, stdout_write = _new_pipe()
        stderr_read, stderr_write = _new_pipe()
        devnull = os.open(os.devnull, os.O_RDONLY | os.O_CLOEXEC)
        _require_empty_pipe(stdout_read)
        _require_empty_pipe(stderr_read)
        stdout_metadata = os.fstat(stdout_read)
        stderr_metadata = os.fstat(stderr_read)
        if (
            not stat.S_ISFIFO(stdout_metadata.st_mode)
            or not stat.S_ISFIFO(stderr_metadata.st_mode)
            or stdout_metadata.st_ino <= 0
            or stderr_metadata.st_ino <= 0
            or (
                stdout_metadata.st_dev == stderr_metadata.st_dev
                and stdout_metadata.st_ino == stderr_metadata.st_ino
            )
        ):
            _fail("fresh pipe identity is not exact")
        runtime_nonce = os.getrandom(32).hex()
        pipe_created_ns = time.monotonic_ns()
        pid = os.fork()
        if pid == 0:
            _child_main(
                plan,
                devnull,
                stdout_read,
                stdout_write,
                stderr_read,
                stderr_write,
            )
        spawned_ns = time.monotonic_ns()
        os.close(devnull)
        devnull = -1
        os.close(stdout_write)
        stdout_write = -1
        os.close(stderr_write)
        stderr_write = -1

        output = {
            stdout_read: bytearray(),
            stderr_read: bytearray(),
        }
        eof = {stdout_read: False, stderr_read: False}
        overflow = False
        timed_out = False
        selector = selectors.DefaultSelector()
        selector.register(stdout_read, selectors.EVENT_READ)
        selector.register(stderr_read, selectors.EVENT_READ)
        deadline = time.monotonic() + deadline_milliseconds / 1000
        while True:
            if child_status is None:
                child_status = _wait_nonblocking(pid)
            if child_status is not None and all(eof.values()):
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                child_status = _reap_after_stop(pid, child_status)
                break
            for key, _ in selector.select(min(remaining, 0.05)):
                descriptor = key.fd
                reached_eof, reached_limit = _read_ready(
                    descriptor,
                    output[descriptor],
                    prepared.spec.output_limit_bytes,
                )
                if reached_eof:
                    eof[descriptor] = True
                    selector.unregister(descriptor)
                if reached_limit:
                    overflow = True
                    child_status = _reap_after_stop(pid, child_status)
                    break
            if overflow:
                break
        selector.close()
        if child_status is None:
            _, child_status = os.waitpid(pid, 0)
        if timed_out or overflow:
            for descriptor in (stdout_read, stderr_read):
                try:
                    for _ in range(4):
                        before = len(output[descriptor])
                        reached_eof, reached_limit = _read_ready(
                            descriptor,
                            output[descriptor],
                            prepared.spec.output_limit_bytes,
                        )
                        if reached_eof:
                            eof[descriptor] = True
                            break
                        if reached_limit:
                            break
                        if len(output[descriptor]) == before:
                            break
                except OSError:
                    pass
        finished_ns = time.monotonic_ns()
        _revalidate_prepared(prepared)
        if os.WIFEXITED(child_status):
            exit_code = os.WEXITSTATUS(child_status)
            term_signal = None
        elif os.WIFSIGNALED(child_status):
            term_signal = os.WTERMSIG(child_status)
            exit_code = 128 + term_signal
        else:
            exit_code = 125
            term_signal = None
        proof = RuntimeProof(
            action=prepared.action,
            intent=prepared.intent,
            runtime_nonce=runtime_nonce,
            stdout_pipe_device=stdout_metadata.st_dev,
            stdout_pipe_inode=stdout_metadata.st_ino,
            stderr_pipe_device=stderr_metadata.st_dev,
            stderr_pipe_inode=stderr_metadata.st_ino,
            pipe_created_ns=pipe_created_ns,
            spawned_ns=spawned_ns,
            finished_ns=finished_ns,
            stdout_eof=eof[stdout_read],
            stderr_eof=eof[stderr_read],
            outcome=BOUNDARY.ProcessOutcome(
                name=prepared.action,
                exit_code=exit_code,
                term_signal=term_signal,
                timed_out=timed_out,
                output_overflow=overflow,
                stdout=bytes(output[stdout_read]),
                stderr=bytes(output[stderr_read]),
            ),
        )
        prepared._proof = proof
        return proof
    except BaseException:
        if pid > 0:
            child_status = _reap_after_stop(pid, child_status)
        raise
    finally:
        for descriptor in (
            stdout_read,
            stdout_write,
            stderr_read,
            stderr_write,
            devnull,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError as error:
                    if error.errno != errno.EBADF:
                        raise


def decode_offline_fixture(
    prepared: PreparedAction, proof: RuntimeProof
) -> OfflineDecodedProof:
    """Decode one internally issued proof without making it adapter-eligible."""

    if type(prepared) is not PreparedAction or prepared._closed:
        _fail("prepared action is unavailable")
    if prepared._decoded:
        _fail("prepared action was already decoded")
    if type(proof) is not RuntimeProof or prepared._proof is not proof:
        _fail("runtime proof belongs to a different prepared action")
    if (
        proof.action != prepared.action
        or proof.intent != prepared.intent
        or SHA256.fullmatch(proof.runtime_nonce) is None
        or proof.runtime_nonce == ZERO_SHA256
        or proof.stdout_pipe_inode <= 0
        or proof.stderr_pipe_inode <= 0
        or (
            proof.stdout_pipe_device == proof.stderr_pipe_device
            and proof.stdout_pipe_inode == proof.stderr_pipe_inode
        )
        or not (
            proof.intent.checked_ns
            < proof.pipe_created_ns
            < proof.spawned_ns
            <= proof.finished_ns
        )
    ):
        _fail("runtime proof identity is not exact")
    _revalidate_prepared(prepared)
    prepared._decoded = True
    attestation = (
        prepared.descriptors
        if prepared.action in BOUNDARY.BOOT_ACTIONS
        else None
    )
    result = BOUNDARY.decode_process_outcome(
        prepared.spec,
        prepared.inputs,
        proof.outcome,
        attestation=attestation,
    )
    prepared._decode_succeeded = True
    prepared._decoded_result = dict(result)
    return OfflineDecodedProof(
        action=prepared.action,
        intent_sha256=prepared.intent.event_sha256,
        runtime_nonce=proof.runtime_nonce,
        result=result,
        authority="none",
        adapter_eligible=False,
    )


def finalize_offline_fixture(prepared: PreparedAction) -> None:
    """Release one action only after its exact result event is durable."""

    if type(prepared) is not PreparedAction or prepared._closed:
        _fail("prepared action is unavailable")
    if (
        not prepared._decode_succeeded
        or prepared._decoded_result is None
        or prepared._finalized
    ):
        _fail("offline action has no new decoded result to finalize")
    if getattr(prepared.journal, JOURNAL_MARKER, None) != prepared._marker:
        _fail("prepared action ownership changed")
    expected_phase = RESULT_EVENT_BY_ACTION.get(prepared.action)
    snapshot = prepared.journal.snapshot()
    paths = prepared.journal.event_paths()
    if (
        snapshot["phase"] != expected_phase
        or len(paths) != prepared.intent.event_index + 2
        or paths[prepared.intent.event_index] != prepared.intent.path
    ):
        _fail("journal did not advance by one exact action result")
    result_descriptor = -1
    try:
        result_descriptor, event, _, result_held = _open_journal_event(
            prepared.journal,
            paths[-1],
            prepared.intent.event_index + 1,
            str(expected_phase),
            "action result event",
        )
        if event["data"] != prepared._decoded_result:
            _fail("journal action result differs from decoded child result")
        _revalidate_descriptors(prepared)
        _revalidate_journal_event(
            prepared.journal,
            result_held,
            "action result event",
        )
        prepared._finalized = True
        delattr(prepared.journal, JOURNAL_MARKER)
    finally:
        if result_descriptor >= 0:
            os.close(result_descriptor)
    prepared.close()
