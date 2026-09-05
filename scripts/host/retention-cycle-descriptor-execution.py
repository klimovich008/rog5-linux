"""Execute one harmless probe through exact held file descriptors."""

from __future__ import annotations

from dataclasses import dataclass, replace as dataclass_replace
import errno
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import time
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
PROGRAM_RELATIVE = "scripts/host/retention-cycle-descriptor-probe.py"
PROGRAM_PATH = REPO / PROGRAM_RELATIVE
PROGRAM_SIZE = 5288
PROGRAM_SHA256 = "afba8ae9c2bff325eadcae781895aafd7934897b238edcdc72bf73f7f38e20f5"
PROGRAM_MODE = 0o644
INTERPRETER_LOGICAL = Path("/usr/bin/python3")
INTERPRETER_RESOLVED = Path("/usr/bin/python3.13")
INTERPRETER_LINK_TARGET = "python3.13"
INTERPRETER_SIZE = 14352
INTERPRETER_SHA256 = "62cf34d8c76bbde1cceea478800c3b9125a90746dd73f1281614823bdcf1b718"
INTERPRETER_MODE = 0o755
FORMAT = "rog5-retention-descriptor-exec-v1"
PROGRAM_EXEC_FD = 198
INTERPRETER_EXEC_FD = 199
OUTPUT_LIMIT_BYTES = 4096
PIPE_FLAGS = os.O_CLOEXEC | os.O_NONBLOCK
FILE_FLAGS = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
DIRECTORY_FLAGS = (
    os.O_RDONLY
    | os.O_CLOEXEC
    | os.O_DIRECTORY
    | getattr(os, "O_NOFOLLOW", 0)
)
MODES = ("success", "timeout", "descendant", "overflow", "exit")
DEADLINES = {
    "success": 1000,
    "timeout": 60,
    "descendant": 60,
    "overflow": 1000,
    "exit": 1000,
}
BASE_ENVIRONMENT = {
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
    "TZ": "UTC",
}

LIVE_ENTRYPOINT = "none"
ADAPTER_WIRING = "none"
PRODUCTION_EXECUTION = "none"
CONNECTED_ADMISSION = "none"
CREDENTIAL_USE = "none"
RESULT_AUTHORITY = "none"
PRODUCTION_DESCRIPTOR_EXECUTION = "unproven"


class DescriptorExecutionError(RuntimeError):
    """The disconnected descriptor-execution proof is not exact."""


class _ChildState(Enum):
    REAPED_WITHOUT_STATUS = "reaped-without-status"


def _fail(message: str) -> NoReturn:
    raise DescriptorExecutionError(message)


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
class DescriptorFixtureSpec:
    mode: str
    argv: tuple[str, ...]
    cwd: str
    environment: tuple[tuple[str, str], ...]
    stdin: str
    stdout: str
    stderr: str
    output_limit_bytes: int
    deadline_milliseconds: int
    start_new_session: bool
    kill_process_group_on_timeout: bool
    close_fds: bool
    umask: str
    program_fd: int
    interpreter_fd: int
    accepted_exit_codes: tuple[int, ...]


@dataclass(frozen=True)
class ProcessOutcome:
    exit_code: int
    term_signal: int | None
    timed_out: bool
    output_overflow: bool
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class DescriptorExecutionProof:
    preparation_id: str
    nonce: str
    mode: str
    child_pid: int
    stdout_pipe_device: int
    stdout_pipe_inode: int
    stderr_pipe_device: int
    stderr_pipe_inode: int
    pipe_created_ns: int
    spawned_ns: int
    finished_ns: int
    stdout_eof: bool
    stderr_eof: bool
    outcome: ProcessOutcome


@dataclass(frozen=True)
class DescriptorDecodedProof:
    preparation_id: str
    nonce: str
    evidence: dict[str, object]
    authority: str
    adapter_eligible: bool


def _metadata(value: os.stat_result) -> StatIdentity:
    return StatIdentity(
        device=value.st_dev,
        inode=value.st_ino,
        mode=value.st_mode,
        uid=value.st_uid,
        gid=value.st_gid,
        links=value.st_nlink,
        size=value.st_size,
        modified_ns=value.st_mtime_ns,
        changed_ns=value.st_ctime_ns,
    )


def _read_exact(descriptor: int, expected_size: int, label: str) -> bytes:
    before = os.fstat(descriptor)
    if before.st_size != expected_size:
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


def _stat_named(
    which: str,
    repository_descriptor: int = -1,
) -> StatIdentity:
    try:
        if which == "repository":
            value = os.stat(REPO, follow_symlinks=False)
        elif which == "program":
            if repository_descriptor < 0:
                _fail("repository descriptor is unavailable")
            value = os.stat(
                PROGRAM_RELATIVE,
                dir_fd=repository_descriptor,
                follow_symlinks=False,
            )
        elif which == "interpreter":
            value = os.stat(INTERPRETER_RESOLVED, follow_symlinks=False)
        else:
            _fail("unknown descriptor identity")
    except OSError as error:
        raise DescriptorExecutionError(f"{which} descriptor changed") from error
    return _metadata(value)


def _environment(nonce: str, mode: str) -> tuple[tuple[str, str], ...]:
    values = dict(BASE_ENVIRONMENT)
    values.update(
        {
            "ROG5_DESCRIPTOR_FIXTURE_FORMAT": FORMAT,
            "ROG5_DESCRIPTOR_FIXTURE_MODE": mode,
            "ROG5_DESCRIPTOR_FIXTURE_NONCE": nonce,
            "ROG5_DESCRIPTOR_FIXTURE_REPO": str(REPO),
        }
    )
    return tuple(sorted(values.items()))


def _exact_spec(nonce: str, mode: str) -> DescriptorFixtureSpec:
    if mode not in MODES:
        _fail("descriptor fixture mode is not reviewed")
    return DescriptorFixtureSpec(
        mode=mode,
        argv=(
            str(INTERPRETER_LOGICAL),
            "-B",
            f"/proc/self/fd/{PROGRAM_EXEC_FD}",
            "probe",
            mode,
            nonce,
        ),
        cwd=str(REPO),
        environment=_environment(nonce, mode),
        stdin="devnull",
        stdout="bounded-pipe",
        stderr="bounded-pipe",
        output_limit_bytes=OUTPUT_LIMIT_BYTES,
        deadline_milliseconds=DEADLINES[mode],
        start_new_session=True,
        kill_process_group_on_timeout=True,
        close_fds=True,
        umask="0077",
        program_fd=PROGRAM_EXEC_FD,
        interpreter_fd=INTERPRETER_EXEC_FD,
        accepted_exit_codes=(0,),
    )


class PreparedDescriptorFixture:
    """Held repository, program, and interpreter descriptors for one run."""

    def __init__(
        self,
        *,
        nonce: str,
        spec: DescriptorFixtureSpec,
        repository_descriptor: int,
        program_descriptor: int,
        interpreter_descriptor: int,
        repository_identity: StatIdentity,
        program_identity: StatIdentity,
        interpreter_identity: StatIdentity,
        preparation_id: str,
    ) -> None:
        self.nonce = nonce
        self.spec = spec
        self.repository_descriptor = repository_descriptor
        self.program_descriptor = program_descriptor
        self.interpreter_descriptor = interpreter_descriptor
        self.repository_identity = repository_identity
        self.program_identity = program_identity
        self.interpreter_identity = interpreter_identity
        self.preparation_id = preparation_id
        self._attempted = False
        self._decoded = False
        self._closed = False
        self._proof: DescriptorExecutionProof | None = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for descriptor in (
            self.repository_descriptor,
            self.program_descriptor,
            self.interpreter_descriptor,
        ):
            try:
                os.close(descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise


def _revalidate_prepared(prepared: PreparedDescriptorFixture) -> None:
    if type(prepared) is not PreparedDescriptorFixture or prepared._closed:
        _fail("descriptor preparation is unavailable")
    if prepared.spec != _exact_spec(prepared.nonce, prepared.spec.mode):
        _fail("fixture process specification changed")
    try:
        repository_opened = _metadata(os.fstat(prepared.repository_descriptor))
        program_opened = _metadata(os.fstat(prepared.program_descriptor))
        interpreter_opened = _metadata(os.fstat(prepared.interpreter_descriptor))
    except OSError as error:
        raise DescriptorExecutionError("held descriptor changed") from error
    checks = (
        (
            "repository directory",
            repository_opened,
            prepared.repository_identity,
            _stat_named("repository"),
        ),
        (
            "program descriptor",
            program_opened,
            prepared.program_identity,
            _stat_named("program", prepared.repository_descriptor),
        ),
        (
            "interpreter descriptor",
            interpreter_opened,
            prepared.interpreter_identity,
            _stat_named("interpreter"),
        ),
    )
    for label, opened, expected, named in checks:
        if opened != expected or named != expected:
            _fail(f"{label} changed")
    if os.readlink(INTERPRETER_LOGICAL) != INTERPRETER_LINK_TARGET:
        _fail("interpreter descriptor changed")
    if hashlib.sha256(
        _read_exact(
            prepared.program_descriptor,
            PROGRAM_SIZE,
            "program descriptor",
        )
    ).hexdigest() != PROGRAM_SHA256:
        _fail("program descriptor changed")
    if hashlib.sha256(
        _read_exact(
            prepared.interpreter_descriptor,
            INTERPRETER_SIZE,
            "interpreter descriptor",
        )
    ).hexdigest() != INTERPRETER_SHA256:
        _fail("interpreter descriptor changed")


def prepare_fixture(mode: str) -> PreparedDescriptorFixture:
    """Open the one repository-owned harmless probe and pinned interpreter."""

    if type(mode) is not str or mode not in MODES:
        _fail("descriptor fixture mode is not reviewed")
    nonce = os.getrandom(32).hex()
    spec = _exact_spec(nonce, mode)
    repository_descriptor = program_descriptor = interpreter_descriptor = -1
    try:
        repository_descriptor = os.open(REPO, DIRECTORY_FLAGS)
        repository_opened = os.fstat(repository_descriptor)
        repository_named = _stat_named("repository")
        repository_identity = _metadata(repository_opened)
        if (
            not stat.S_ISDIR(repository_opened.st_mode)
            or repository_identity != repository_named
            or repository_opened.st_uid != os.geteuid()
            or repository_opened.st_gid != os.getegid()
            or stat.S_IMODE(repository_opened.st_mode) != 0o755
        ):
            _fail("repository directory metadata is not exact")

        program_descriptor = os.open(
            PROGRAM_RELATIVE,
            FILE_FLAGS,
            dir_fd=repository_descriptor,
        )
        program_opened = os.fstat(program_descriptor)
        program_identity = _metadata(program_opened)
        if (
            not stat.S_ISREG(program_opened.st_mode)
            or program_identity
            != _stat_named("program", repository_descriptor)
            or program_opened.st_uid != os.geteuid()
            or program_opened.st_gid != os.getegid()
            or program_opened.st_nlink != 1
            or stat.S_IMODE(program_opened.st_mode) != PROGRAM_MODE
            or program_opened.st_size != PROGRAM_SIZE
            or hashlib.sha256(
                _read_exact(program_descriptor, PROGRAM_SIZE, "program descriptor")
            ).hexdigest()
            != PROGRAM_SHA256
        ):
            _fail("program descriptor metadata is not exact")

        logical = INTERPRETER_LOGICAL.lstat()
        if (
            not stat.S_ISLNK(logical.st_mode)
            or logical.st_uid != 0
            or logical.st_gid != 0
            or os.readlink(INTERPRETER_LOGICAL) != INTERPRETER_LINK_TARGET
        ):
            _fail("interpreter logical path is not exact")
        interpreter_descriptor = os.open(INTERPRETER_RESOLVED, FILE_FLAGS)
        interpreter_opened = os.fstat(interpreter_descriptor)
        interpreter_identity = _metadata(interpreter_opened)
        if (
            not stat.S_ISREG(interpreter_opened.st_mode)
            or interpreter_identity != _stat_named("interpreter")
            or interpreter_opened.st_uid != 0
            or interpreter_opened.st_gid != 0
            or interpreter_opened.st_nlink != 1
            or stat.S_IMODE(interpreter_opened.st_mode) != INTERPRETER_MODE
            or interpreter_opened.st_size != INTERPRETER_SIZE
            or hashlib.sha256(
                _read_exact(
                    interpreter_descriptor,
                    INTERPRETER_SIZE,
                    "interpreter descriptor",
                )
            ).hexdigest()
            != INTERPRETER_SHA256
        ):
            _fail("interpreter descriptor metadata is not exact")

        identity_payload = json.dumps(
            {
                "interpreter": INTERPRETER_SHA256,
                "mode": mode,
                "nonce": nonce,
                "program": PROGRAM_SHA256,
                "repository_device": repository_identity.device,
                "repository_inode": repository_identity.inode,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        prepared = PreparedDescriptorFixture(
            nonce=nonce,
            spec=spec,
            repository_descriptor=repository_descriptor,
            program_descriptor=program_descriptor,
            interpreter_descriptor=interpreter_descriptor,
            repository_identity=repository_identity,
            program_identity=program_identity,
            interpreter_identity=interpreter_identity,
            preparation_id=hashlib.sha256(identity_payload).hexdigest(),
        )
        _revalidate_prepared(prepared)
        return prepared
    except BaseException:
        for descriptor in (
            repository_descriptor,
            program_descriptor,
            interpreter_descriptor,
        ):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        raise


def _close_unrelated_descriptors(keep: tuple[int, ...]) -> None:
    allowed = frozenset(keep)
    try:
        names = os.listdir("/proc/self/fd")
    except OSError:
        os._exit(125)
    for name in names:
        if not name.isdigit():
            os._exit(125)
        descriptor = int(name)
        if descriptor in allowed:
            continue
        try:
            os.close(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                os._exit(125)


def _child_exec(
    prepared: PreparedDescriptorFixture,
    devnull: int,
    stdout_read: int,
    stdout_write: int,
    stderr_read: int,
    stderr_write: int,
) -> NoReturn:
    try:
        os.setsid()
        os.fchdir(prepared.repository_descriptor)
        os.umask(0o077)
        os.dup2(devnull, 0, inheritable=True)
        os.dup2(stdout_write, 1, inheritable=True)
        os.dup2(stderr_write, 2, inheritable=True)
        os.dup2(
            prepared.program_descriptor,
            PROGRAM_EXEC_FD,
            inheritable=True,
        )
        os.dup2(
            prepared.interpreter_descriptor,
            INTERPRETER_EXEC_FD,
            inheritable=False,
        )
        _close_unrelated_descriptors(
            (0, 1, 2, PROGRAM_EXEC_FD, INTERPRETER_EXEC_FD)
        )
        os.set_blocking(1, True)
        os.set_blocking(2, True)
        os.execve(
            INTERPRETER_EXEC_FD,
            prepared.spec.argv,
            dict(prepared.spec.environment),
        )
    except BaseException:
        try:
            os.write(2, b"descriptor-exec-failure\n")
        except OSError:
            pass
        os._exit(125)


def _new_pipe() -> tuple[int, int]:
    return os.pipe2(PIPE_FLAGS)


def _require_empty_pipe(descriptor: int) -> None:
    try:
        payload = os.read(descriptor, 1)
    except BlockingIOError:
        return
    if payload or payload == b"":
        _fail("fresh descriptor-execution pipe was not empty")


def _wait_nonblocking(pid: int) -> int | _ChildState | None:
    try:
        observed, status_value = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return _ChildState.REAPED_WITHOUT_STATUS
    return status_value if observed == pid else None


def _signal_group(
    pid: int,
    selected: signal.Signals,
    *,
    allow_direct_child: bool,
) -> None:
    try:
        os.killpg(pid, selected)
    except ProcessLookupError:
        if not allow_direct_child:
            return
        try:
            os.kill(pid, selected)
        except ProcessLookupError:
            pass


def _stop_group(
    pid: int,
    current_status: int | _ChildState | None,
) -> int | _ChildState:
    _signal_group(
        pid,
        signal.SIGTERM,
        allow_direct_child=current_status is None,
    )
    deadline = time.monotonic() + 0.1
    status_value = current_status
    while status_value is None and time.monotonic() < deadline:
        status_value = _wait_nonblocking(pid)
        if status_value is None:
            time.sleep(0.005)
    _signal_group(
        pid,
        signal.SIGKILL,
        allow_direct_child=status_value is None,
    )
    if status_value is None:
        try:
            _, status_value = os.waitpid(pid, 0)
        except ChildProcessError:
            status_value = _ChildState.REAPED_WITHOUT_STATUS
    return status_value


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


def run_fixture(
    prepared: PreparedDescriptorFixture,
) -> DescriptorExecutionProof:
    """Execute only the pinned harmless probe through held descriptors."""

    if type(prepared) is not PreparedDescriptorFixture or prepared._closed:
        _fail("descriptor preparation is unavailable")
    if prepared._attempted:
        _fail("descriptor preparation was already attempted")
    prepared._attempted = True
    _revalidate_prepared(prepared)

    stdout_read = stdout_write = stderr_read = stderr_write = devnull = -1
    pid = -1
    child_status: int | _ChildState | None = None
    selector: selectors.BaseSelector | None = None
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
            _fail("fresh descriptor-execution pipe identity is not exact")
        pipe_created_ns = time.monotonic_ns()
        pid = os.fork()
        if pid == 0:
            _child_exec(
                prepared,
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
        deadline = (
            time.monotonic() + prepared.spec.deadline_milliseconds / 1000
        )
        while True:
            if child_status is None:
                child_status = _wait_nonblocking(pid)
            if child_status is not None and all(eof.values()):
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                child_status = _stop_group(pid, child_status)
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
                    child_status = _stop_group(pid, child_status)
                    break
            if overflow:
                break
        selector.close()
        selector = None
        if child_status is None:
            try:
                _, child_status = os.waitpid(pid, 0)
            except ChildProcessError:
                child_status = _ChildState.REAPED_WITHOUT_STATUS
        if timed_out or overflow:
            drain_deadline = time.monotonic() + 0.1
            while time.monotonic() < drain_deadline:
                progressed = False
                pending = False
                for descriptor in (stdout_read, stderr_read):
                    if eof[descriptor]:
                        continue
                    if (
                        len(output[descriptor])
                        > prepared.spec.output_limit_bytes
                    ):
                        continue
                    pending = True
                    try:
                        before = len(output[descriptor])
                        reached_eof, reached_limit = _read_ready(
                            descriptor,
                            output[descriptor],
                            prepared.spec.output_limit_bytes,
                        )
                    except OSError:
                        continue
                    if reached_eof:
                        eof[descriptor] = True
                        progressed = True
                    elif reached_limit:
                        overflow = True
                    elif len(output[descriptor]) != before:
                        progressed = True
                if not pending or all(eof.values()):
                    break
                if not progressed:
                    time.sleep(0.005)
        finished_ns = time.monotonic_ns()
        _revalidate_prepared(prepared)
        if child_status is _ChildState.REAPED_WITHOUT_STATUS:
            exit_code = 125
            term_signal = None
        elif os.WIFEXITED(child_status):
            exit_code = os.WEXITSTATUS(child_status)
            term_signal = None
        elif os.WIFSIGNALED(child_status):
            term_signal = os.WTERMSIG(child_status)
            exit_code = 128 + term_signal
        else:
            exit_code = 125
            term_signal = None
        proof = DescriptorExecutionProof(
            preparation_id=prepared.preparation_id,
            nonce=prepared.nonce,
            mode=prepared.spec.mode,
            child_pid=pid,
            stdout_pipe_device=stdout_metadata.st_dev,
            stdout_pipe_inode=stdout_metadata.st_ino,
            stderr_pipe_device=stderr_metadata.st_dev,
            stderr_pipe_inode=stderr_metadata.st_ino,
            pipe_created_ns=pipe_created_ns,
            spawned_ns=spawned_ns,
            finished_ns=finished_ns,
            stdout_eof=eof[stdout_read],
            stderr_eof=eof[stderr_read],
            outcome=ProcessOutcome(
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
            child_status = _stop_group(pid, child_status)
        raise
    finally:
        if selector is not None:
            selector.close()
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


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            _fail("descriptor fixture output has duplicate fields")
        value[key] = item
    return value


def _expected_evidence(prepared: PreparedDescriptorFixture) -> dict[str, object]:
    exec_argv_payload = b"\0".join(
        value.encode("ascii") for value in prepared.spec.argv
    ) + b"\0"
    argv_payload = json.dumps(
        list(prepared.spec.argv[2:]),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    environment_payload = json.dumps(
        list(prepared.spec.environment),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return {
        "argv_sha256": hashlib.sha256(argv_payload).hexdigest(),
        "cwd": str(REPO),
        "environment_sha256": hashlib.sha256(environment_payload).hexdigest(),
        "exec_argv_sha256": hashlib.sha256(exec_argv_payload).hexdigest(),
        "format": FORMAT,
        "interpreter_device": prepared.interpreter_identity.device,
        "interpreter_inode": prepared.interpreter_identity.inode,
        "interpreter_path": str(INTERPRETER_RESOLVED),
        "interpreter_sha256": INTERPRETER_SHA256,
        "mode": prepared.spec.mode,
        "nonce": prepared.nonce,
        "open_fds": f"0,1,2,{PROGRAM_EXEC_FD}",
        "process_group_leader": True,
        "program_device": prepared.program_identity.device,
        "program_fd": PROGRAM_EXEC_FD,
        "program_inode": prepared.program_identity.inode,
        "program_sha256": PROGRAM_SHA256,
        "session_leader": True,
        "stderr_pipe": True,
        "stdin_devnull": True,
        "stdout_pipe": True,
        "umask": "0077",
    }


def decode_fixture(
    prepared: PreparedDescriptorFixture,
    proof: DescriptorExecutionProof,
) -> DescriptorDecodedProof:
    """Validate one exact success record from the internally issued proof."""

    if type(prepared) is not PreparedDescriptorFixture or prepared._closed:
        _fail("descriptor preparation is unavailable")
    if prepared._decoded:
        _fail("descriptor preparation was already decoded")
    if type(proof) is not DescriptorExecutionProof or prepared._proof is not proof:
        _fail("descriptor proof belongs to a different preparation")
    prepared._decoded = True
    if (
        proof.preparation_id != prepared.preparation_id
        or proof.nonce != prepared.nonce
        or proof.mode != prepared.spec.mode
        or proof.child_pid <= 0
        or proof.stdout_pipe_inode <= 0
        or proof.stderr_pipe_inode <= 0
        or (
            proof.stdout_pipe_device == proof.stderr_pipe_device
            and proof.stdout_pipe_inode == proof.stderr_pipe_inode
        )
        or not (
            proof.pipe_created_ns < proof.spawned_ns <= proof.finished_ns
        )
    ):
        _fail("descriptor proof identity is not exact")
    if (
        proof.mode != "success"
        or proof.outcome.exit_code not in prepared.spec.accepted_exit_codes
        or proof.outcome.term_signal is not None
        or proof.outcome.timed_out
        or proof.outcome.output_overflow
        or proof.outcome.stderr != b""
        or not proof.stdout_eof
        or not proof.stderr_eof
    ):
        _fail("descriptor proof is not a successful descriptor fixture")
    _revalidate_prepared(prepared)
    try:
        evidence = json.loads(
            proof.outcome.stdout,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise DescriptorExecutionError(
            "descriptor fixture output is not canonical JSON"
        ) from error
    if (
        type(evidence) is not dict
        or evidence != _expected_evidence(prepared)
        or (
            json.dumps(evidence, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
        != proof.outcome.stdout
    ):
        _fail("descriptor fixture output is not exact")
    return DescriptorDecodedProof(
        preparation_id=prepared.preparation_id,
        nonce=prepared.nonce,
        evidence=evidence,
        authority="none",
        adapter_eligible=False,
    )
