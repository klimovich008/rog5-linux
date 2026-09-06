#!/usr/bin/env python3
"""Run bounded staging or promoted-system A660 acceptance gates."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import pwd
import re
import select
import signal
import stat
import subprocess
import sys
import threading
import time


KERNEL_FAILURE = re.compile(
    rb"(BUG:|Oops:|Kernel panic|Call trace:|Unable to handle kernel|"
    rb"Synchronous External Abort|watchdog[^\n]*bite|"
    rb"Unhandled context fault|"
    rb"arm-smmu[^\n]*(fault|error)|IOMMU[^\n]*fault|"
    rb"\bGMU\b[^\n]*(error|timeout|fault|hang)|"
    rb"\bHFI\b[^\n]*(error|timeout|fault)|"
    rb"adreno[^\n]*(fault|hang|timeout)|"
    rb"msm[^\n]*gpu[^\n]*(fault|hang|timeout)|"
    rb"(msm_)?drm[^\n]*(\*ERROR\*|error|failed|fault|timeout|hang))",
    re.IGNORECASE,
)
A660_RENDERER = re.compile(r"(Adreno(?: \(TM\))? 660|FD660)", re.IGNORECASE)
SOFTWARE_RENDERER = re.compile(
    r"(llvmpipe|lavapipe|softpipe|software rasterizer)",
    re.IGNORECASE,
)
SAFE_TOKEN = re.compile(r"[A-Za-z0-9_./:=,@%+-]+\Z")
BUNDLE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
DPMS_LINE = re.compile(r"dpms mode for screen DSI-1: (on|off)\Z")
STAGING_DEADLINE_SECONDS = 540
WATCHDOG_MARGIN_SECONDS = 60
COMMAND_OUTPUT_MAX = 4 * 1024 * 1024
MAX_INTEGER = (1 << 63) - 1
BATTERY_STATUSES = {
    "Charging",
    "Discharging",
    "Not charging",
    "Full",
    "Unknown",
}
ROOT_ENVIRONMENT = {
    "HOME": "/root",
    "USER": "root",
    "LOGNAME": "root",
    "PATH": "/usr/local/bin:/usr/bin",
    "LANG": "C",
    "LC_ALL": "C",
    "TZ": "UTC",
}
COMMAND_MANIFEST = Path("/etc/rog5/a660-command-manifest")
COMMAND_PATHS = {
    "runner": Path("/usr/local/libexec/rog5-cgroup-exec"),
    "systemctl": Path("/usr/bin/systemctl"),
    "dmesg": Path("/usr/bin/dmesg"),
    "baseline": Path("/usr/local/bin/rog5-collect-baseline.sh"),
    "vulkaninfo": Path("/usr/bin/vulkaninfo"),
    "eglinfo": Path("/usr/bin/eglinfo"),
    "submit": Path("/usr/local/libexec/rog5-vulkan-submit"),
    "gdbus": Path("/usr/bin/gdbus"),
    "vkcube": Path("/usr/bin/vkcube"),
    "screen": Path("/usr/local/bin/rog5-screen-toggle.sh"),
    "kscreen": Path("/usr/bin/kscreen-doctor"),
    "root_verify": Path("/usr/local/sbin/persistent-root-verify"),
}
COMMAND_ORDER = tuple(COMMAND_PATHS)
PROMOTED_VERIFICATION_MOUNT = "/.rog5/userdata-ro"
PROMOTED_ROOT_PREFIX = "/rog5/roots/"
CGROUP_ROOT = Path("/sys/fs/cgroup")
CGROUP_COUNTER = 0
CGROUP_LOCK = threading.Lock()


class AcceptanceError(RuntimeError):
    """A stable, non-sensitive A660 gate refusal."""


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    uid: int
    start_time_ticks: int
    pidfd: int | None


@dataclass(frozen=True)
class TrustedCommand:
    name: str
    path: Path
    descriptor: int
    sha256: str


@dataclass(frozen=True)
class Session:
    identity: ProcessIdentity
    user: str
    group: int
    supplementary_groups: tuple[int, ...]
    home: str
    environment: dict[str, str]

    @property
    def pid(self) -> int:
        return self.identity.pid


@dataclass(frozen=True)
class Watchdog:
    identity: ProcessIdentity
    timer_identity: ProcessIdentity
    deadline_boottime_seconds: int
    required_until_boottime_seconds: int

    @property
    def pid(self) -> int:
        return self.identity.pid


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    bundle: str
    root_generation: str = ""
    root_tree_sha256: str = ""
    root_seal_sha256: str = ""
    root_tree_entries: int = 0
    root_subtree: str = ""
    root_device: str = ""


@dataclass(frozen=True)
class Configuration:
    mode: str
    fixture: bool
    root: Path
    report: Path
    expected_kernel: str
    render_cycles: int
    vulkan_cycles: int
    submit_cycles: int
    screen_cycles: int
    screen_pause_seconds: float
    workload_seconds: float
    soak_seconds: int
    soak_interval_seconds: int
    thermal_limit_mc: int
    memory_floor_kib: int
    staging_deadline_seconds: int
    command_manifest_sha256: str
    commands: dict[str, TrustedCommand]


def task_path(config: Configuration, absolute: str) -> Path:
    if not absolute.startswith("/"):
        raise AcceptanceError("internal target path is not absolute")
    if config.root == Path("/"):
        return Path(absolute)
    return config.root / absolute.removeprefix("/")


def fixed_command(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise AcceptanceError("fixed command path is not absolute")
    for ancestor in path.parents:
        try:
            ancestor_metadata = ancestor.lstat()
        except OSError as error:
            raise AcceptanceError(
                "fixed command ancestor is unavailable"
            ) from error
        if (
            not stat.S_ISDIR(ancestor_metadata.st_mode)
            or ancestor_metadata.st_uid != 0
            or stat.S_IMODE(ancestor_metadata.st_mode) & 0o022
        ):
            raise AcceptanceError("fixed command ancestor is unsafe")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise AcceptanceError("fixed command is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) & 0o022
        or not os.access(path, os.X_OK)
    ):
        raise AcceptanceError("fixed command metadata is unsafe")
    return path


def command_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_fixed_ascii(
    path: Path,
    label: str,
    maximum: int = 4096,
) -> str:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise AcceptanceError(f"cannot read {label}") from error
    if len(payload) > maximum or b"\0" in payload:
        raise AcceptanceError(f"{label} is not canonical")
    try:
        return payload.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise AcceptanceError(f"{label} is not ASCII") from error


def read_pinned_control_ascii(
    config: Configuration,
    absolute: str,
    label: str,
    maximum: int = 4096,
) -> str:
    path = task_path(config, absolute)
    parent = path.parent
    expected_owner = task_path(config, "/proc/1").stat().st_uid
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        parent_before = parent.lstat()
        parent_fd = os.open(parent, flags)
    except OSError as error:
        raise AcceptanceError(f"cannot pin {label} parent") from error
    descriptor = -1
    try:
        parent_observed = os.fstat(parent_fd)
        if (
            command_identity(parent_before)
            != command_identity(parent_observed)
            or not stat.S_ISDIR(parent_observed.st_mode)
            or parent_observed.st_uid != expected_owner
            or stat.S_IMODE(parent_observed.st_mode) & 0o022
        ):
            raise AcceptanceError(f"{label} parent is unsafe")
        file_flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            file_flags |= os.O_NOFOLLOW
        descriptor = os.open(
            path.name,
            file_flags,
            dir_fd=parent_fd,
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != expected_owner
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) != 0o400
        ):
            raise AcceptanceError(f"{label} metadata is unsafe")
        payload = bytearray()
        while len(payload) <= maximum:
            chunk = os.read(descriptor, maximum + 1 - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(descriptor)
        named = os.stat(
            path.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (
            command_identity(before) != command_identity(after)
            or command_identity(before) != command_identity(named)
        ):
            raise AcceptanceError(f"{label} identity changed")
    except OSError as error:
        raise AcceptanceError(f"cannot read {label}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_fd)
    if len(payload) > maximum or b"\0" in payload:
        raise AcceptanceError(f"{label} is not canonical")
    try:
        return payload.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise AcceptanceError(f"{label} is not ASCII") from error


def host_cmdline_value(name: str) -> str:
    payload = read_fixed_ascii(
        Path("/proc/cmdline"),
        "kernel command line",
        1024 * 1024,
    )
    tokens = payload.split()
    if not tokens or any(not SAFE_TOKEN.fullmatch(token) for token in tokens):
        raise AcceptanceError("kernel command line is not canonical")
    return unique_cmdline_value(tokens, name)


def parse_command_manifest(
    expected_sha256: str,
) -> dict[str, str]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        before = COMMAND_MANIFEST.lstat()
        descriptor = os.open(COMMAND_MANIFEST, flags)
    except OSError as error:
        raise AcceptanceError("command manifest is unavailable") from error
    try:
        metadata = os.fstat(descriptor)
        if command_identity(before) != command_identity(metadata):
            raise AcceptanceError("command manifest identity changed")
        payload = bytearray()
        while len(payload) <= 4096:
            chunk = os.read(descriptor, 4097 - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        after = COMMAND_MANIFEST.lstat()
        if command_identity(before) != command_identity(after):
            raise AcceptanceError("command manifest identity changed")
    except OSError as error:
        raise AcceptanceError("cannot read command manifest") from error
    finally:
        os.close(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or len(payload) > 4096
        or b"\0" in payload
        or hashlib.sha256(payload).hexdigest() != expected_sha256
    ):
        raise AcceptanceError("command manifest is unsafe")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise AcceptanceError("command manifest is not ASCII") from error
    expected_names = (
        "format",
        *(f"{name}_sha256" for name in COMMAND_ORDER),
    )
    if len(lines) != len(expected_names):
        raise AcceptanceError("command manifest is not canonical")
    values: dict[str, str] = {}
    for expected_name, line in zip(expected_names, lines, strict=True):
        name, separator, value = line.partition("=")
        if (
            separator != "="
            or name != expected_name
            or not value
            or name in values
        ):
            raise AcceptanceError("command manifest is not canonical")
        values[name] = value
    if values["format"] != "rog5-a660-command-manifest-v1":
        raise AcceptanceError("command manifest format changed")
    for name in COMMAND_ORDER:
        if not SHA256.fullmatch(values[f"{name}_sha256"]):
            raise AcceptanceError("command manifest hash is invalid")
    return values


def trusted_command(
    name: str,
    path: Path,
    expected_sha256: str,
) -> TrustedCommand:
    fixed_command(str(path))
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        source = os.open(path, flags)
    except OSError as error:
        raise AcceptanceError("cannot open fixed command") from error
    descriptor = -1
    try:
        before = path.lstat()
        observed = os.fstat(source)
        if command_identity(before) != command_identity(observed):
            raise AcceptanceError("fixed command identity changed")
        descriptor = os.memfd_create(
            f"rog5-a660-{name}",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        digest = hashlib.sha256()
        while True:
            payload = os.read(source, 1024 * 1024)
            if not payload:
                break
            digest.update(payload)
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise AcceptanceError(
                        "trusted command copy made no progress"
                    )
                offset += written
        after = path.lstat()
        if command_identity(before) != command_identity(after):
            raise AcceptanceError("fixed command identity changed")
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise AcceptanceError("fixed command hash is not trusted")
        os.fchmod(descriptor, 0o555)
        os.lseek(descriptor, 0, os.SEEK_SET)
        required_seals = (
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE
        )
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, required_seals)
        if fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) != required_seals:
            raise AcceptanceError("trusted command sealing failed")
        return TrustedCommand(
            name=name,
            path=path,
            descriptor=descriptor,
            sha256=actual_sha256,
        )
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    finally:
        os.close(source)


def configuration(mode: str) -> Configuration:
    if mode not in {"preflight", "staging", "soak"}:
        raise AcceptanceError(
            "usage: a660-acceptance.py [preflight|staging|soak]"
        )
    expected_kernel = os.environ.get("EXPECTED_KERNEL_RELEASE", "")
    if (
        not expected_kernel
        or not expected_kernel.isascii()
        or not SAFE_TOKEN.fullmatch(expected_kernel)
    ):
        raise AcceptanceError("EXPECTED_KERNEL_RELEASE is invalid")
    command_manifest_sha256 = host_cmdline_value(
        "rog5.a660_command_manifest_sha256"
    )
    if not SHA256.fullmatch(command_manifest_sha256):
        raise AcceptanceError(
            "signed command manifest identity is invalid"
        )
    manifest = parse_command_manifest(command_manifest_sha256)
    commands: dict[str, TrustedCommand] = {}
    try:
        for name in COMMAND_ORDER:
            commands[name] = trusted_command(
                name,
                COMMAND_PATHS[name],
                manifest[f"{name}_sha256"],
            )
    except BaseException:
        for command in commands.values():
            os.close(command.descriptor)
        raise
    return Configuration(
        mode=mode,
        fixture=False,
        root=Path("/"),
        report=Path("/run/rog5-a660-acceptance"),
        expected_kernel=expected_kernel,
        render_cycles=100,
        vulkan_cycles=10,
        submit_cycles=10,
        screen_cycles=5,
        screen_pause_seconds=2.0,
        workload_seconds=30.0,
        soak_seconds=1800,
        soak_interval_seconds=60,
        thermal_limit_mc=85000,
        memory_floor_kib=524288,
        staging_deadline_seconds=STAGING_DEADLINE_SECONDS,
        command_manifest_sha256=command_manifest_sha256,
        commands=commands,
    )


def validate_configured_command(
    config: Configuration,
    name: str,
) -> TrustedCommand:
    command = config.commands.get(name)
    if command is None or command.name != name:
        raise AcceptanceError("command is outside the fixed surface")
    try:
        metadata = os.fstat(command.descriptor)
        seals = fcntl.fcntl(command.descriptor, fcntl.F_GET_SEALS)
    except OSError as error:
        raise AcceptanceError("trusted command descriptor changed") from error
    required_seals = (
        fcntl.F_SEAL_SEAL
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_WRITE
    )
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size <= 0
        or stat.S_IMODE(metadata.st_mode) != 0o555
        or seals != required_seals
    ):
        raise AcceptanceError("trusted command descriptor changed")
    return command


def current_command_cgroup() -> Path:
    payload = read_fixed_ascii(
        Path("/proc/self/cgroup"),
        "acceptance cgroup identity",
        4096,
    )
    lines = payload.splitlines()
    if len(lines) != 1 or not lines[0].startswith("0::/"):
        raise AcceptanceError("unified cgroup v2 is unavailable")
    relative = lines[0].removeprefix("0::/")
    if (
        not relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise AcceptanceError("acceptance cgroup identity is unsafe")
    root = CGROUP_ROOT.resolve(strict=True)
    parent = (root / relative).resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as error:
        raise AcceptanceError("acceptance cgroup escaped its root") from error
    if (
        not parent.is_dir()
        or parent.is_symlink()
        or not os.access(parent, os.W_OK)
        or not (parent / "cgroup.procs").is_file()
        or not (parent / "cgroup.events").is_file()
        or not (parent / "cgroup.kill").is_file()
    ):
        raise AcceptanceError("acceptance cgroup is not delegated")
    return parent


def create_command_cgroup() -> Path:
    global CGROUP_COUNTER

    parent = current_command_cgroup()
    with CGROUP_LOCK:
        CGROUP_COUNTER += 1
        counter = CGROUP_COUNTER
    path = parent / f"rog5-a660-{os.getpid()}-{counter}"
    try:
        os.mkdir(path, 0o755)
    except OSError as error:
        raise AcceptanceError("cannot create command cgroup") from error
    if (
        not path.is_dir()
        or path.is_symlink()
        or not (path / "cgroup.procs").is_file()
        or not (path / "cgroup.events").is_file()
        or not (path / "cgroup.kill").is_file()
    ):
        try:
            os.rmdir(path)
        except OSError:
            pass
        raise AcceptanceError("command cgroup is unsafe")
    return path


def open_cgroup_procs(cgroup: Path) -> int:
    flags = os.O_WRONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(cgroup / "cgroup.procs", flags)
    except OSError as error:
        raise AcceptanceError("cannot open command cgroup") from error


def cgroup_populated(cgroup: Path) -> bool:
    payload = read_fixed_ascii(
        cgroup / "cgroup.events",
        "command cgroup state",
        4096,
    )
    values: dict[str, str] = {}
    for line in payload.splitlines():
        name, separator, value = line.partition(" ")
        if separator != " " or not name or value not in {"0", "1"}:
            raise AcceptanceError("command cgroup state is malformed")
        values[name] = value
    if "populated" not in values:
        raise AcceptanceError("command cgroup state omits population")
    return values["populated"] == "1"


def terminate_process_cgroup(
    process: subprocess.Popen[bytes],
    cgroup: Path,
) -> None:
    flags = os.O_WRONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(cgroup / "cgroup.kill", flags)
        try:
            if os.write(descriptor, b"1\n") != 2:
                raise AcceptanceError("command cgroup kill made no progress")
        finally:
            os.close(descriptor)
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while cgroup_populated(cgroup):
            if time.monotonic() >= deadline:
                raise AcceptanceError(
                    "acceptance process tree did not exit"
                )
            time.sleep(0.01)
        os.rmdir(cgroup)
    except subprocess.TimeoutExpired as error:
        raise AcceptanceError("acceptance process tree did not exit") from error
    except OSError as error:
        raise AcceptanceError("cannot clean command cgroup") from error


def run_command(
    config: Configuration,
    name: str,
    arguments: list[str] | tuple[str, ...] = (),
    *,
    timeout: float,
    environment: dict[str, str] | None = None,
    session: Session | None = None,
) -> bytes:
    command = validate_configured_command(config, name)
    if name == "runner":
        raise AcceptanceError("cgroup runner cannot be invoked as a target")
    runner = validate_configured_command(config, "runner")
    if environment is None:
        environment = (
            os.environ.copy()
            if config.fixture
            else dict(ROOT_ENVIRONMENT)
        )
    if session is not None:
        uid = session.identity.uid
        gid = session.group
        groups = session.supplementary_groups
    elif config.fixture:
        uid = os.geteuid()
        gid = os.getegid()
        groups = tuple(sorted(set(os.getgroups())))
    else:
        uid = 0
        gid = 0
        groups = ()
    group_text = (
        ",".join(str(group) for group in groups)
        if groups
        else "-"
    )
    cgroup = create_command_cgroup()
    try:
        cgroup_descriptor = open_cgroup_procs(cgroup)
    except BaseException:
        try:
            os.rmdir(cgroup)
        except OSError:
            pass
        raise
    try:
        process = subprocess.Popen(
            [
                str(runner.path),
                "--target-fd",
                str(command.descriptor),
                "--cgroup-fd",
                str(cgroup_descriptor),
                "--uid",
                str(uid),
                "--gid",
                str(gid),
                "--groups",
                group_text,
                "--",
                str(command.path),
                *arguments,
            ],
            executable=f"/proc/self/fd/{runner.descriptor}",
            pass_fds=(
                runner.descriptor,
                command.descriptor,
                cgroup_descriptor,
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment,
            start_new_session=True,
        )
    except BaseException:
        os.close(cgroup_descriptor)
        try:
            os.rmdir(cgroup)
        except OSError:
            pass
        raise
    os.close(cgroup_descriptor)
    if process.stdout is None:
        terminate_process_cgroup(process, cgroup)
        raise AcceptanceError("acceptance command has no output pipe")
    output = bytearray()
    output_fd = process.stdout.fileno()
    os.set_blocking(output_fd, False)
    deadline = time.monotonic() + timeout
    eof = False
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AcceptanceError("fixed acceptance command timed out")
            ready, _writable, _exceptional = select.select(
                [output_fd],
                [],
                [],
                min(remaining, 0.1),
            )
            if ready:
                payload = os.read(output_fd, 65536)
                if payload:
                    output.extend(payload)
                    if len(output) > COMMAND_OUTPUT_MAX:
                        raise AcceptanceError(
                            "command output exceeds policy"
                        )
                else:
                    eof = True
            return_code = process.poll()
            if return_code is not None and eof:
                break
        if return_code != 0:
            raise AcceptanceError("fixed acceptance command failed")
        return bytes(output)
    finally:
        process.stdout.close()
        terminate_process_cgroup(process, cgroup)


def system_is_running(config: Configuration) -> None:
    output = run_command(
        config,
        "systemctl",
        ["is-system-running"],
        timeout=5,
    ).decode("ascii", errors="strict").strip()
    if output != "running":
        raise AcceptanceError("systemd is not running")


def read_ascii(path: Path, label: str, maximum: int = 4096) -> str:
    return read_fixed_ascii(path, label, maximum)


def read_process_fields(
    config: Configuration,
    pid: int,
) -> tuple[str, int, int]:
    process = task_path(config, f"/proc/{pid}")
    payload = read_ascii(process / "stat", "process identity")
    _prefix, separator, tail = payload.rpartition(") ")
    fields = tail.split()
    if separator != ") " or len(fields) < 20:
        raise AcceptanceError("process identity is malformed")
    state = fields[0]
    ppid_text = fields[1]
    start_text = fields[19]
    if (
        len(state) != 1
        or not ppid_text.isdecimal()
        or not start_text.isdecimal()
    ):
        raise AcceptanceError("process identity is malformed")
    return state, int(ppid_text), int(start_text)


def pidfd_is_alive(identity: ProcessIdentity) -> None:
    if identity.pidfd is None:
        return
    poller = select.poll()
    poller.register(identity.pidfd, select.POLLIN)
    if poller.poll(0):
        raise AcceptanceError("pinned process exited")


def pin_process(
    config: Configuration,
    pid: int,
    *,
    expected_name: str,
    expected_uid: int | None = None,
    expected_ppid: int | None = None,
) -> ProcessIdentity:
    if pid <= 1:
        raise AcceptanceError("process PID is outside policy")
    process = task_path(config, f"/proc/{pid}")
    if not process.is_dir():
        raise AcceptanceError("process is absent")
    if read_ascii(process / "comm", "process name") != expected_name:
        raise AcceptanceError("process name changed")
    uid = process.stat().st_uid
    if expected_uid is not None and uid != expected_uid:
        raise AcceptanceError("process owner changed")
    state, ppid, start_time = read_process_fields(config, pid)
    if state in {"T", "t", "X", "x", "Z"}:
        raise AcceptanceError("process is not runnable")
    if expected_ppid is not None and ppid != expected_ppid:
        raise AcceptanceError("process parent changed")
    pidfd: int | None = None
    if not config.fixture:
        pidfd = os.pidfd_open(pid, 0)
    identity = ProcessIdentity(
        pid=pid,
        uid=uid,
        start_time_ticks=start_time,
        pidfd=pidfd,
    )
    try:
        revalidate_process(
            config,
            identity,
            expected_name=expected_name,
            expected_ppid=expected_ppid,
        )
    except BaseException:
        if pidfd is not None:
            os.close(pidfd)
        raise
    return identity


def revalidate_process(
    config: Configuration,
    identity: ProcessIdentity,
    *,
    expected_name: str,
    expected_ppid: int | None = None,
) -> None:
    pidfd_is_alive(identity)
    process = task_path(config, f"/proc/{identity.pid}")
    if (
        not process.is_dir()
        or read_ascii(process / "comm", "process name") != expected_name
        or process.stat().st_uid != identity.uid
    ):
        raise AcceptanceError("pinned process identity changed")
    state, ppid, start_time = read_process_fields(config, identity.pid)
    if (
        state in {"T", "t", "X", "x", "Z"}
        or start_time != identity.start_time_ticks
        or (expected_ppid is not None and ppid != expected_ppid)
    ):
        raise AcceptanceError("pinned process identity changed")
    pidfd_is_alive(identity)


def find_kwin_session(config: Configuration) -> Session:
    process_root = task_path(config, "/proc")
    matches: list[Path] = []
    for candidate in process_root.iterdir():
        if not candidate.name.isdecimal() or not candidate.is_dir():
            continue
        try:
            name = (candidate / "comm").read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError):
            continue
        if name == "kwin_wayland":
            matches.append(candidate)
    if len(matches) != 1:
        raise AcceptanceError("expected exactly one KWin Wayland process")
    process = matches[0]
    pid = int(process.name)
    uid = process.stat().st_uid
    identity = pin_process(
        config,
        pid,
        expected_name="kwin_wayland",
        expected_uid=uid,
    )
    account = pwd.getpwuid(uid)
    user = account.pw_name
    home = account.pw_dir
    groups = tuple(sorted(set(os.getgrouplist(user, account.pw_gid))))
    payload = (process / "environ").read_bytes()
    if len(payload) > 1024 * 1024:
        raise AcceptanceError("KWin environment exceeds policy")
    values: dict[str, str] = {}
    for record in payload.split(b"\0"):
        if not record or b"=" not in record:
            continue
        name, value = record.split(b"=", 1)
        if name not in {
            b"XDG_RUNTIME_DIR",
            b"WAYLAND_DISPLAY",
            b"DBUS_SESSION_BUS_ADDRESS",
        }:
            continue
        try:
            decoded = value.decode("ascii")
        except UnicodeDecodeError as error:
            raise AcceptanceError("KWin session value is not ASCII") from error
        if not SAFE_TOKEN.fullmatch(decoded):
            raise AcceptanceError("KWin session value is unsafe")
        values[name.decode("ascii")] = decoded
    runtime = values.get("XDG_RUNTIME_DIR", "")
    wayland = values.get("WAYLAND_DISPLAY", "wayland-0")
    bus = values.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not runtime.startswith("/") or not wayland or not bus.startswith(
        "unix:path="
    ):
        raise AcceptanceError("KWin session environment is incomplete")
    return Session(
        identity=identity,
        user=user,
        group=account.pw_gid,
        supplementary_groups=groups,
        home=home,
        environment={
            "HOME": home,
            "USER": user,
            "LOGNAME": user,
            "PATH": "/usr/local/bin:/usr/bin",
            "XDG_RUNTIME_DIR": runtime,
            "WAYLAND_DISPLAY": wayland,
            "DBUS_SESSION_BUS_ADDRESS": bus,
        },
    )


def run_session(
    config: Configuration,
    session: Session,
    name: str,
    arguments: list[str] | tuple[str, ...] = (),
    *,
    timeout: float = 30,
) -> bytes:
    environment = (
        os.environ.copy()
        if config.fixture
        else {}
    )
    environment.update(session.environment)
    return run_command(
        config,
        name,
        arguments,
        timeout=timeout,
        environment=environment,
        session=session,
    )


def kwin_is_alive(config: Configuration, session: Session) -> None:
    revalidate_process(
        config,
        session.identity,
        expected_name="kwin_wayland",
    )


def read_cmdline(config: Configuration) -> list[str]:
    payload = read_ascii(
        task_path(config, "/proc/cmdline"),
        "kernel command line",
        1024 * 1024,
    )
    tokens = payload.split()
    if not tokens or any(not SAFE_TOKEN.fullmatch(token) for token in tokens):
        raise AcceptanceError("kernel command line is not canonical")
    return tokens


def unique_cmdline_value(tokens: list[str], name: str) -> str:
    prefix = f"{name}="
    matches = [
        token
        for token in tokens
        if token == name or token.startswith(prefix)
    ]
    if (
        len(matches) != 1
        or matches[0] == name
        or not matches[0].removeprefix(prefix)
    ):
        raise AcceptanceError(f"kernel command line does not bind {name}")
    return matches[0].removeprefix(prefix)


def require_absent_cmdline_family(tokens: list[str], name: str) -> None:
    prefix = f"{name}="
    if any(token == name or token.startswith(prefix) for token in tokens):
        raise AcceptanceError(f"kernel command line unexpectedly has {name}")


def signed_root_identity(
    tokens: list[str],
    *,
    allowed_subtrees: set[str],
    require_device: bool,
) -> tuple[str, str, int, str, str, str]:
    generation = unique_cmdline_value(tokens, "rog5.root_generation")
    tree_sha256 = unique_cmdline_value(tokens, "rog5.root_tree_sha256")
    seal_sha256 = unique_cmdline_value(tokens, "rog5.root_seal_sha256")
    entries_text = unique_cmdline_value(tokens, "rog5.root_tree_entries")
    subtree = unique_cmdline_value(tokens, "rog5.root_subtree")
    device = (
        unique_cmdline_value(tokens, "rog5.root_device")
        if require_device
        else ""
    )
    if (
        generation != "arch-a"
        or not SHA256.fullmatch(tree_sha256)
        or not SHA256.fullmatch(seal_sha256)
        or not entries_text.isdecimal()
        or entries_text.startswith("0")
        or int(entries_text) > MAX_INTEGER
        or subtree not in allowed_subtrees
        or (require_device and device != "8:23")
    ):
        raise AcceptanceError("signed runtime-root identity is invalid")
    return (
        generation,
        tree_sha256,
        int(entries_text),
        seal_sha256,
        subtree,
        device,
    )


def staging_mount_attestation(
    config: Configuration,
) -> dict[str, str]:
    expected_names = (
        "format",
        "overlay_mount_id",
        "overlay_lower_mount_id",
        "state_mount_id",
        "overlay_lower_path",
        "command_manifest_sha256",
        "root_generation",
        "root_tree_sha256",
        "root_seal_sha256",
        "root_tree_entries",
        "root_subtree",
    )
    lines = read_pinned_control_ascii(
        config,
        "/run/rog5-network-root-identity",
        "network-root mount identity",
        4096,
    ).splitlines()
    if len(lines) != len(expected_names):
        raise AcceptanceError(
            "network-root mount identity is not canonical"
        )
    values: dict[str, str] = {}
    for expected_name, line in zip(expected_names, lines, strict=True):
        name, separator, value = line.partition("=")
        if (
            name != expected_name
            or separator != "="
            or not value
            or not value.isascii()
        ):
            raise AcceptanceError(
                "network-root mount identity is not canonical"
            )
        values[name] = value
    if values["format"] != "rog5-network-root-identity-v1":
        raise AcceptanceError("network-root mount identity changed")
    for name in (
        "overlay_mount_id",
        "overlay_lower_mount_id",
        "state_mount_id",
    ):
        canonical_positive_integer(
            values[name],
            f"network-root {name}",
        )
    return values


def staging_root_provenance(
    config: Configuration,
    *,
    command_manifest_sha256: str,
    root_generation: str,
    root_tree_sha256: str,
    root_seal_sha256: str,
    root_tree_entries: int,
    root_subtree: str,
) -> None:
    mountinfo = read_ascii(
        task_path(config, "/proc/self/mountinfo"),
        "mount inventory",
        1024 * 1024,
    )
    expected = {
        "/": ("overlay", "overlay", False),
        "/.rog5/root-ro": ("nfs", "169.254.77.1:/", True),
        "/.rog5/state": ("tmpfs", "tmpfs", False),
    }
    observed: dict[str, tuple[str, str, bool]] = {}
    mount_ids: dict[str, str] = {}
    overlay_paths: dict[str, str] = {}
    for line in mountinfo.splitlines():
        left, separator, right = line.partition(" - ")
        left_fields = left.split()
        right_fields = right.split()
        if (
            separator != " - "
            or len(left_fields) < 6
            or len(right_fields) < 2
        ):
            raise AcceptanceError("mount inventory is malformed")
        mountpoint = left_fields[4]
        if mountpoint not in expected:
            continue
        if mountpoint in observed:
            raise AcceptanceError("staging root mount inventory changed")
        canonical_positive_integer(
            left_fields[0],
            "staging mount ID",
        )
        mount_ids[mountpoint] = left_fields[0]
        options = left_fields[5].split(",")
        fstype = right_fields[0]
        if fstype.startswith("nfs"):
            fstype = "nfs"
        if mountpoint == "/":
            if len(right_fields) < 3:
                raise AcceptanceError(
                    "staging overlay mount options are incomplete"
                )
            for option in right_fields[2].split(","):
                name, separator, value = option.partition("=")
                if name not in {"lowerdir", "upperdir", "workdir"}:
                    continue
                if separator != "=" or not value or name in overlay_paths:
                    raise AcceptanceError(
                        "staging overlay mount options changed"
                    )
                overlay_paths[name] = value
        if mountpoint == "/.rog5/state":
            if (
                "nodev" not in options
                or "nosuid" not in options
                or len(right_fields) < 3
                or "size=2097152k" not in right_fields[2].split(",")
            ):
                raise AcceptanceError(
                    "staging volatile state mount changed"
                )
        observed[mountpoint] = (
            fstype,
            right_fields[1],
            "ro" in options,
        )
    if observed != expected:
        raise AcceptanceError("staging root mount inventory changed")
    if overlay_paths != {
        "lowerdir": "/mnt/root-ro",
        "upperdir": "/mnt/state/upper",
        "workdir": "/mnt/state/work",
    }:
        raise AcceptanceError("staging overlay mount options changed")
    attestation = staging_mount_attestation(config)
    if (
        attestation["overlay_mount_id"] != mount_ids["/"]
        or attestation["overlay_lower_mount_id"]
        != mount_ids["/.rog5/root-ro"]
        or attestation["state_mount_id"] != mount_ids["/.rog5/state"]
        or attestation["overlay_lower_path"] != "/mnt/root-ro"
        or attestation["command_manifest_sha256"]
        != command_manifest_sha256
        or attestation["root_generation"] != root_generation
        or attestation["root_tree_sha256"] != root_tree_sha256
        or attestation["root_seal_sha256"] != root_seal_sha256
        or attestation["root_tree_entries"] != str(root_tree_entries)
        or attestation["root_subtree"] != root_subtree
    ):
        raise AcceptanceError(
            "network-root mount identity does not match runtime"
        )
    reject_critical_upper(config)


def reject_critical_upper(config: Configuration) -> None:
    upper = task_path(config, "/.rog5/state/upper")
    if not upper.is_dir() or upper.is_symlink():
        raise AcceptanceError("staging overlay upper is unavailable")
    if os.path.lexists(upper / ".wh..wh..opq"):
        raise AcceptanceError(
            "volatile overlay can override the trusted runtime"
        )
    for relative in ("bin", "sbin", "lib", "lib64", "usr", "etc"):
        if (
            os.path.lexists(upper / relative)
            or os.path.lexists(upper / f".wh.{relative}")
        ):
            raise AcceptanceError(
                "volatile overlay can override the trusted runtime"
            )


def staging_runtime_profile(config: Configuration) -> RuntimeProfile:
    tokens = read_cmdline(config)
    if unique_cmdline_value(tokens, "rog5.netroot") != "1":
        raise AcceptanceError("staging is not a network-root profile")
    if unique_cmdline_value(tokens, "rog5.target_timeout") != "600":
        raise AcceptanceError("staging target timeout is not 600 seconds")
    if unique_cmdline_value(tokens, "rog5.recovery_timeout") != "900":
        raise AcceptanceError("staging rollback timeout is not 900 seconds")
    command_manifest_sha256 = unique_cmdline_value(
        tokens,
        "rog5.a660_command_manifest_sha256",
    )
    if command_manifest_sha256 != config.command_manifest_sha256:
        raise AcceptanceError("staging command manifest identity changed")
    bundle = unique_cmdline_value(tokens, "rog5.bundle")
    if not BUNDLE_ID.fullmatch(bundle):
        raise AcceptanceError("staging bundle identity is invalid")
    (
        root_generation,
        root_tree_sha256,
        root_tree_entries,
        root_seal_sha256,
        root_subtree,
        root_device,
    ) = signed_root_identity(
        tokens,
        allowed_subtrees={"/"},
        require_device=False,
    )
    for family in (
        "rog5.persistent_ro",
        "rog5.persistent_promoted",
        "rog5.ufs_discovery",
    ):
        require_absent_cmdline_family(tokens, family)
    if not task_path(config, "/run/rog5-network-root-mounted").is_file():
        raise AcceptanceError("network-root runtime marker is absent")
    if read_ascii(
        task_path(config, "/run/rog5-network-root-source"),
        "network-root source",
    ) != "169.254.77.1:/":
        raise AcceptanceError("network-root source is unexpected")
    if read_ascii(
        task_path(config, "/run/rog5-physical-block-count"),
        "physical block count",
    ) != "0":
        raise AcceptanceError("network-root storage attestation changed")
    staging_root_provenance(
        config,
        command_manifest_sha256=command_manifest_sha256,
        root_generation=root_generation,
        root_tree_sha256=root_tree_sha256,
        root_seal_sha256=root_seal_sha256,
        root_tree_entries=root_tree_entries,
        root_subtree=root_subtree,
    )
    return RuntimeProfile(
        name="network-root-v1",
        bundle=bundle,
        root_generation=root_generation,
        root_tree_sha256=root_tree_sha256,
        root_seal_sha256=root_seal_sha256,
        root_tree_entries=root_tree_entries,
        root_subtree=root_subtree,
        root_device=root_device,
    )


def parse_promotion_attestation(
    config: Configuration,
) -> dict[str, str]:
    expected_names = (
        "format",
        "profile",
        "bundle",
        "kernel",
        "command_manifest_sha256",
        "root_mount_fstype",
        "root_mount_source",
        "root_mount_device",
        "overlay_mount_id",
        "overlay_lower_mount_id",
        "state_mount_id",
        "overlay_lower_path",
        "root_generation",
        "root_subtree",
        "root_tree_entries",
        "root_tree_sha256",
        "root_seal_sha256",
        "verification_mount",
        "verification_root",
    )
    lines = read_pinned_control_ascii(
        config,
        "/run/rog5-persistent-promotion.attestation",
        "promotion attestation",
        4096,
    ).splitlines()
    if len(lines) != len(expected_names):
        raise AcceptanceError("promotion attestation is not canonical")
    values: dict[str, str] = {}
    for expected, line in zip(expected_names, lines, strict=True):
        name, separator, value = line.partition("=")
        if (
            name != expected
            or separator != "="
            or not value
            or not value.isascii()
        ):
            raise AcceptanceError("promotion attestation is not canonical")
        values[name] = value
    for name in (
        "overlay_mount_id",
        "overlay_lower_mount_id",
        "state_mount_id",
    ):
        canonical_positive_integer(
            values[name],
            f"promotion {name}",
        )
    return values


def promoted_mount_inventory(
    config: Configuration,
) -> tuple[str, str, str, str, str, str, str, str]:
    mountinfo = read_ascii(
        task_path(config, "/proc/self/mountinfo"),
        "mount inventory",
        1024 * 1024,
    )
    overlay_roots = 0
    overlay_mount_id = ""
    overlay_paths: dict[str, str] = {}
    verification_mounts = 0
    verification_device = ""
    verification_mount_id = ""
    state_mounts = 0
    state_mount_id = ""
    for line in mountinfo.splitlines():
        left, separator, right = line.partition(" - ")
        left_fields = left.split()
        right_fields = right.split()
        if (
            separator != " - "
            or len(left_fields) < 6
            or len(right_fields) < 2
        ):
            raise AcceptanceError("mount inventory is malformed")
        device_path = task_path(
            config,
            f"/sys/dev/block/{left_fields[2]}",
        )
        block_backed = device_path.is_symlink()
        if block_backed:
            try:
                block_name = device_path.resolve(strict=True).name
            except OSError as error:
                raise AcceptanceError(
                    "block-device identity is unavailable"
                ) from error
            if block_name != "sda23":
                raise AcceptanceError(
                    "promoted block-device identity changed"
                )
        mountpoint = left_fields[4]
        mount_options = left_fields[5].split(",")
        canonical_positive_integer(
            left_fields[0],
            "promoted mount ID",
        )
        if mountpoint == "/":
            if (
                block_backed
                or right_fields[0] != "overlay"
                or right_fields[1] != "overlay"
                or "rw" not in mount_options
                or len(right_fields) < 3
            ):
                raise AcceptanceError(
                    "promoted root overlay provenance changed"
                )
            overlay_roots += 1
            overlay_mount_id = left_fields[0]
            for option in right_fields[2].split(","):
                name, separator, value = option.partition("=")
                if name not in {"lowerdir", "upperdir", "workdir"}:
                    continue
                if separator != "=" or not value or name in overlay_paths:
                    raise AcceptanceError(
                        "promoted root overlay provenance changed"
                    )
                overlay_paths[name] = value
        if right_fields[0].startswith("nfs"):
            raise AcceptanceError("promoted root still has an NFS mount")
        if mountpoint == PROMOTED_VERIFICATION_MOUNT:
            if (
                not block_backed
                or right_fields[0] != "ext4"
                or right_fields[1] != "/dev/sda23"
                or left_fields[3] != "/"
                or "ro" not in mount_options
            ):
                raise AcceptanceError(
                    "promoted verification mount is unsafe"
                )
            verification_mounts += 1
            verification_device = left_fields[2]
            verification_mount_id = left_fields[0]
        elif mountpoint == "/.rog5/state":
            if (
                block_backed
                or right_fields[0] != "tmpfs"
                or right_fields[1] != "tmpfs"
                or "rw" not in mount_options
                or "nodev" not in mount_options
                or "nosuid" not in mount_options
                or len(right_fields) < 3
                or "size=2097152k" not in right_fields[2].split(",")
            ):
                raise AcceptanceError(
                    "promoted volatile state mount changed"
                )
            state_mounts += 1
            state_mount_id = left_fields[0]
        elif mountpoint != "/" and block_backed:
            raise AcceptanceError(
                "promoted root has an unexpected block-backed mount"
            )
    if (
        overlay_roots != 1
        or overlay_paths != {
            "lowerdir": "/mnt/userdata/rog5/roots/arch-a",
            "upperdir": "/mnt/state/upper",
            "workdir": "/mnt/state/work",
        }
        or verification_mounts != 1
        or verification_device != "8:23"
        or state_mounts != 1
    ):
        raise AcceptanceError("root mount inventory is not exact")
    reject_critical_upper(config)
    return (
        "ext4",
        "/dev/sda23",
        "/rog5/roots/arch-a",
        verification_device,
        overlay_mount_id,
        verification_mount_id,
        state_mount_id,
        "/mnt/userdata/rog5/roots/arch-a",
    )


def soak_runtime_profile(config: Configuration) -> RuntimeProfile:
    tokens = read_cmdline(config)
    if unique_cmdline_value(
        tokens,
        "rog5.persistent_promoted",
    ) != "1":
        raise AcceptanceError("soak is not a promoted persistent root")
    if unique_cmdline_value(tokens, "rog5.ufs_discovery") != "1":
        raise AcceptanceError("soak lacks persistent storage provenance")
    bundle = unique_cmdline_value(tokens, "rog5.bundle")
    if not BUNDLE_ID.fullmatch(bundle):
        raise AcceptanceError("promoted bundle identity is invalid")
    command_manifest_sha256 = unique_cmdline_value(
        tokens,
        "rog5.a660_command_manifest_sha256",
    )
    if command_manifest_sha256 != config.command_manifest_sha256:
        raise AcceptanceError("promoted command manifest identity changed")
    (
        root_generation,
        root_tree_sha256,
        root_tree_entries,
        root_seal_sha256,
        root_subtree,
        root_device,
    ) = signed_root_identity(
        tokens,
        allowed_subtrees={"/rog5/roots/arch-a"},
        require_device=True,
    )
    root_entries_text = str(root_tree_entries)
    for family in ("rog5.netroot", "rog5.persistent_ro"):
        require_absent_cmdline_family(tokens, family)
    for path in (
        "/run/rog5-network-root-watchdog.pid",
        "/run/rog5-network-root-watchdog.lease",
        "/run/rog5-network-root-watchdog.disarmed.pid",
        "/run/rog5-p2-watchdog.pid",
        "/run/rog5-p2-entry-watchdog.pid",
        "/run/rog5-network-root-mounted",
        "/run/rog5-network-root-source",
        "/run/rog5-network-root-identity",
        "/run/rog5-physical-block-count",
        "/run/rog5-p2-root-mounted",
        "/run/rog5-p2-entry-root-mounted",
        "/run/rog5-p2-ready",
    ):
        if task_path(config, path).exists():
            raise AcceptanceError("soak still has rollback-root state")
    attestation = parse_promotion_attestation(config)
    if (
        attestation["format"] != "rog5-persistent-promotion-v2"
        or attestation["profile"] != "persistent-root-promoted-v1"
        or attestation["bundle"] != bundle
        or attestation["kernel"] != config.expected_kernel
        or attestation["command_manifest_sha256"]
        != command_manifest_sha256
        or attestation["root_mount_fstype"] != "ext4"
        or attestation["root_mount_source"] != "/dev/sda23"
        or attestation["root_mount_device"] != root_device
        or attestation["overlay_lower_path"]
        != "/mnt/userdata/rog5/roots/arch-a"
        or attestation["root_generation"] != root_generation
        or attestation["root_subtree"] != root_subtree
        or attestation["root_tree_entries"] != root_entries_text
        or attestation["root_tree_sha256"] != root_tree_sha256
        or attestation["root_seal_sha256"] != root_seal_sha256
        or attestation["verification_mount"]
        != PROMOTED_VERIFICATION_MOUNT
        or attestation["verification_root"]
        != f"{PROMOTED_VERIFICATION_MOUNT}{root_subtree}"
    ):
        raise AcceptanceError("promotion attestation does not match runtime")
    if promoted_mount_inventory(config) != (
        attestation["root_mount_fstype"],
        attestation["root_mount_source"],
        attestation["root_subtree"],
        attestation["root_mount_device"],
        attestation["overlay_mount_id"],
        attestation["overlay_lower_mount_id"],
        attestation["state_mount_id"],
        attestation["overlay_lower_path"],
    ):
        raise AcceptanceError("promoted root mount provenance changed")
    return RuntimeProfile(
        name="persistent-root-promoted-v1",
        bundle=bundle,
        root_generation=root_generation,
        root_tree_sha256=root_tree_sha256,
        root_seal_sha256=root_seal_sha256,
        root_tree_entries=root_tree_entries,
        root_subtree=root_subtree,
        root_device=root_device,
    )


def canonical_positive_integer(value: str, label: str) -> int:
    if (
        not value.isdecimal()
        or value.startswith("0")
        or int(value) > MAX_INTEGER
    ):
        raise AcceptanceError(f"{label} is not canonical")
    return int(value)


def canonical_nonnegative_integer(value: str, label: str) -> int:
    if (
        not value.isdecimal()
        or (value.startswith("0") and value != "0")
        or int(value) > MAX_INTEGER
    ):
        raise AcceptanceError(f"{label} is not canonical")
    return int(value)


def parse_watchdog_lease(config: Configuration) -> dict[str, str]:
    expected_names = (
        "format",
        "pid",
        "start_time_ticks",
        "timer_pid",
        "timer_start_time_ticks",
        "armed_boottime_seconds",
        "deadline_boottime_seconds",
        "timeout_seconds",
    )
    lines = read_pinned_control_ascii(
        config,
        "/run/rog5-network-root-watchdog.lease",
        "rollback watchdog lease",
        2048,
    ).splitlines()
    if len(lines) != len(expected_names):
        raise AcceptanceError("rollback watchdog lease is not canonical")
    values: dict[str, str] = {}
    for expected_name, line in zip(expected_names, lines, strict=True):
        name, separator, value = line.partition("=")
        if (
            separator != "="
            or name != expected_name
            or not value
            or name in values
        ):
            raise AcceptanceError(
                "rollback watchdog lease is not canonical"
            )
        values[name] = value
    if values["format"] != "rog5-network-root-watchdog-v1":
        raise AcceptanceError("rollback watchdog lease format changed")
    for name in expected_names[1:]:
        label = f"rollback watchdog {name}"
        if name == "armed_boottime_seconds":
            canonical_nonnegative_integer(values[name], label)
        else:
            canonical_positive_integer(values[name], label)
    return values


def boottime_seconds(config: Configuration) -> int:
    value = read_ascii(
        task_path(config, "/proc/uptime"),
        "system uptime",
    ).split()
    if (
        len(value) != 2
        or not re.fullmatch(r"[0-9]+\.[0-9]+", value[0])
    ):
        raise AcceptanceError("system uptime is not canonical")
    return int(value[0].partition(".")[0])


def watchdog_executable(config: Configuration, pid: int) -> None:
    try:
        executable = os.readlink(
            task_path(config, f"/proc/{pid}/exe")
        )
    except OSError as error:
        raise AcceptanceError(
            "rollback watchdog executable changed"
        ) from error
    if executable not in {
        "/bin/busybox",
        "/bin/busybox (deleted)",
    }:
        raise AcceptanceError("rollback watchdog executable changed")


def writable_descriptor(config: Configuration, pid: int, fd: int) -> None:
    lines = read_ascii(
        task_path(config, f"/proc/{pid}/fdinfo/{fd}"),
        "rollback watchdog descriptor flags",
    ).splitlines()
    flag_values = [
        line.partition(":")[2].strip()
        for line in lines
        if line.partition(":")[0] == "flags"
    ]
    if len(flag_values) != 1:
        raise AcceptanceError("rollback watchdog descriptors changed")
    try:
        flags = int(flag_values[0], 8)
    except ValueError as error:
        raise AcceptanceError(
            "rollback watchdog descriptors changed"
        ) from error
    if (flags & os.O_ACCMODE) not in {os.O_WRONLY, os.O_RDWR}:
        raise AcceptanceError("rollback watchdog descriptors changed")


def staging_watchdog(
    config: Configuration,
    expected: Watchdog | None = None,
) -> Watchdog:
    marker = task_path(
        config, "/run/rog5-network-root-watchdog.disarmed.pid"
    )
    watchdog = read_pinned_control_ascii(
        config,
        "/run/rog5-network-root-watchdog.pid",
        "rollback watchdog PID",
    )
    if (
        not watchdog.isdecimal()
        or (watchdog.startswith("0") and watchdog != "0")
        or marker.exists()
    ):
        raise AcceptanceError("rollback watchdog is not armed")
    pid = int(watchdog)
    lease = parse_watchdog_lease(config)
    lease_pid = canonical_positive_integer(
        lease["pid"],
        "rollback watchdog PID",
    )
    timer_pid = canonical_positive_integer(
        lease["timer_pid"],
        "rollback watchdog timer PID",
    )
    start_time = canonical_positive_integer(
        lease["start_time_ticks"],
        "rollback watchdog start time",
    )
    timer_start_time = canonical_positive_integer(
        lease["timer_start_time_ticks"],
        "rollback watchdog timer start time",
    )
    armed = canonical_nonnegative_integer(
        lease["armed_boottime_seconds"],
        "rollback watchdog arm time",
    )
    deadline = canonical_positive_integer(
        lease["deadline_boottime_seconds"],
        "rollback watchdog deadline",
    )
    timeout_seconds = canonical_positive_integer(
        lease["timeout_seconds"],
        "rollback watchdog timeout",
    )
    now = boottime_seconds(config)
    if (
        pid != lease_pid
        or timeout_seconds != 900
        or deadline - armed != timeout_seconds
        or now < armed
        or now >= deadline
    ):
        raise AcceptanceError("rollback watchdog lease changed")
    expected_uid = task_path(config, "/proc/1").stat().st_uid
    if expected is None:
        identity = pin_process(
            config,
            pid,
            expected_name="init",
            expected_uid=expected_uid,
            expected_ppid=1,
        )
        try:
            timer_identity = pin_process(
                config,
                timer_pid,
                expected_name="sleep",
                expected_uid=expected_uid,
                expected_ppid=pid,
            )
        except BaseException:
            close_identity(identity)
            raise
        required_until = (
            now
            + config.staging_deadline_seconds
            + WATCHDOG_MARGIN_SECONDS
        )
        if deadline < required_until:
            close_identity(identity)
            close_identity(timer_identity)
            raise AcceptanceError(
                "rollback watchdog has insufficient time remaining"
            )
        watchdog_identity = Watchdog(
            identity=identity,
            timer_identity=timer_identity,
            deadline_boottime_seconds=deadline,
            required_until_boottime_seconds=required_until,
        )
    else:
        watchdog_identity = expected
        if (
            pid != expected.pid
            or timer_pid != expected.timer_identity.pid
            or deadline != expected.deadline_boottime_seconds
            or deadline < expected.required_until_boottime_seconds
        ):
            raise AcceptanceError("rollback watchdog PID changed")
        revalidate_process(
            config,
            expected.identity,
            expected_name="init",
            expected_ppid=1,
        )
        revalidate_process(
            config,
            expected.timer_identity,
            expected_name="sleep",
            expected_ppid=pid,
        )
    if (
        watchdog_identity.identity.start_time_ticks != start_time
        or watchdog_identity.timer_identity.start_time_ticks
        != timer_start_time
    ):
        raise AcceptanceError("rollback watchdog lease changed")
    process = task_path(config, f"/proc/{pid}")
    try:
        log_target = os.readlink(process / "fd/8")
        reset_target = os.readlink(process / "fd/9")
    except OSError as error:
        raise AcceptanceError("rollback watchdog descriptors changed") from error
    if log_target != "/dev/kmsg" or reset_target != "/proc/sysrq-trigger":
        raise AcceptanceError("rollback watchdog descriptors changed")
    writable_descriptor(config, pid, 8)
    writable_descriptor(config, pid, 9)
    watchdog_executable(config, pid)
    watchdog_executable(config, timer_pid)
    return watchdog_identity


def staging_storage_isolation(config: Configuration) -> None:
    for candidate in task_path(config, "/sys/class/block").glob("*"):
        if (candidate / "device").exists():
            raise AcceptanceError("physical block device is present")
    mountinfo = read_ascii(
        task_path(config, "/proc/self/mountinfo"),
        "mount inventory",
        1024 * 1024,
    )
    for line in mountinfo.splitlines():
        left, separator, right = line.partition(" - ")
        left_fields = left.split()
        right_fields = right.split()
        if (
            separator != " - "
            or len(left_fields) < 6
            or len(right_fields) < 2
        ):
            raise AcceptanceError("mount inventory is malformed")
        if task_path(
            config,
            f"/sys/dev/block/{left_fields[2]}",
        ).exists():
            raise AcceptanceError("block-backed mount is present")


def staging_guard(
    config: Configuration,
    watchdog: Watchdog | None,
) -> None:
    if watchdog is None:
        return
    staging_runtime_profile(config)
    staging_watchdog(config, watchdog)
    staging_storage_isolation(config)


def preflight(
    config: Configuration,
) -> tuple[Session, Watchdog | None, RuntimeProfile | None]:
    if not config.fixture and os.geteuid() != 0:
        raise AcceptanceError("A660 acceptance requires root")
    if os.uname().release != config.expected_kernel:
        raise AcceptanceError("kernel release does not match")
    if read_ascii(task_path(config, "/proc/1/comm"), "PID 1 name") != "systemd":
        raise AcceptanceError("PID 1 is not systemd")

    watchdog: Watchdog | None = None
    runtime: RuntimeProfile | None = None
    if config.mode == "staging":
        runtime = staging_runtime_profile(config)
        watchdog = staging_watchdog(config)
        staging_storage_isolation(config)
    elif config.mode == "soak":
        for path in (
            "/run/rog5-network-root-watchdog.pid",
            "/run/rog5-network-root-watchdog.lease",
            "/run/rog5-p2-watchdog.pid",
            "/run/rog5-p2-entry-watchdog.pid",
        ):
            if task_path(config, path).exists():
                raise AcceptanceError(
                    "soak cannot consume a rollback window"
                )
        runtime = soak_runtime_profile(config)

    system_is_running(config)
    render_root = task_path(config, "/dev/dri")
    render_nodes = sorted(render_root.glob("renderD*"))
    expected_render = task_path(config, "/dev/dri/renderD128")
    if render_nodes != [expected_render]:
        raise AcceptanceError("render-node inventory is not exact")
    metadata = expected_render.stat()
    if not config.fixture and not stat.S_ISCHR(metadata.st_mode):
        raise AcceptanceError("renderD128 is not a character device")
    if task_path(config, "/dev/kgsl-3d0").exists():
        raise AcceptanceError("vendor KGSL node is present")
    driver = task_path(
        config, "/sys/class/drm/renderD128/device/driver"
    )
    if not driver.is_symlink() or driver.resolve().name != "msm":
        raise AcceptanceError("renderD128 is not bound to msm")
    return find_kwin_session(config), watchdog, runtime


def create_report_directory(config: Configuration) -> None:
    if config.report.exists() or config.report.is_symlink():
        raise AcceptanceError("report directory already exists")
    parent = config.report.parent
    if not parent.is_dir() or parent.is_symlink():
        raise AcceptanceError("report parent is unsafe")
    parent_metadata = parent.stat()
    if (
        parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) & 0o022
    ):
        raise AcceptanceError("report parent metadata is unsafe")
    os.mkdir(config.report, mode=0o700)
    metadata = config.report.stat()
    if (
        metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise AcceptanceError("report directory metadata is unsafe")


def write_private(config: Configuration, name: str, payload: bytes) -> None:
    path = config.report / name
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AcceptanceError("report write made no progress")
            offset += written
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_metrics(payload: bytes) -> dict[str, str]:
    if len(payload) > 1024 * 1024 or b"\0" in payload:
        raise AcceptanceError("baseline metrics exceed policy")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise AcceptanceError("baseline metrics are not ASCII") from error
    metrics: dict[str, str] = {}
    for line in text.splitlines():
        name, separator, value = line.partition("=")
        if (
            separator != "="
            or not name
            or not value
            or name in metrics
            or not SAFE_TOKEN.fullmatch(name)
        ):
            raise AcceptanceError("baseline metrics are not canonical")
        metrics[name] = value
    return metrics


def canonical_metric_integer(
    metrics: dict[str, str],
    name: str,
    minimum: int,
    maximum: int,
) -> int:
    value = metrics[name]
    negative = value.startswith("-")
    digits = value[1:] if negative else value
    if (
        not digits
        or not digits.isascii()
        or not digits.isdecimal()
        or (digits.startswith("0") and digits != "0")
        or (negative and digits == "0")
    ):
        raise AcceptanceError(f"{name} is not a canonical integer")
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise AcceptanceError(f"{name} is outside policy")
    return parsed


def plasma_inventory(config: Configuration) -> tuple[int, int]:
    selected_names = {
        "kwin_wayland",
        "plasmashell",
        "krdpserver",
        "Xwayland",
        "kded6",
        "kglobalacceld",
    }
    count = 0
    total_pss = 0
    for status_path in sorted(
        task_path(config, "/proc").glob("[0-9]*/status")
    ):
        status = read_ascii(
            status_path,
            "Plasma process status",
            1024 * 1024,
        )
        names = [
            line.split()[1]
            for line in status.splitlines()
            if line.startswith("Name:") and len(line.split()) == 2
        ]
        if len(names) != 1 or names[0] not in selected_names:
            continue
        count += 1
        rollup = read_ascii(
            status_path.parent / "smaps_rollup",
            "Plasma process PSS",
            1024 * 1024,
        )
        values = [
            line.split()[1]
            for line in rollup.splitlines()
            if line.startswith("Pss:") and len(line.split()) >= 2
        ]
        if (
            len(values) != 1
            or not values[0].isdecimal()
            or values[0].startswith("0")
        ):
            raise AcceptanceError("Plasma process PSS is incomplete")
        total_pss += int(values[0])
    if count == 0 or total_pss <= 0:
        raise AcceptanceError("Plasma process inventory is incomplete")
    return count, total_pss


def collect_metrics(config: Configuration) -> tuple[bytes, dict[str, str]]:
    payload = run_command(
        config,
        "baseline",
        timeout=15,
    )
    metrics = parse_metrics(payload)
    for name in (
        "thermal_max_millidegree_c",
        "memory_available_kib",
        "plasma_process_count",
        "plasma_pss_kib",
        "battery_status",
        "battery_capacity_percent",
        "battery_current_ua",
        "screen_state",
        "drm_render_node_count",
    ):
        if name not in metrics:
            raise AcceptanceError("baseline metrics omit required field")
    thermal = canonical_metric_integer(
        metrics,
        "thermal_max_millidegree_c",
        0,
        config.thermal_limit_mc,
    )
    memory = canonical_metric_integer(
        metrics,
        "memory_available_kib",
        config.memory_floor_kib,
        MAX_INTEGER,
    )
    reported_plasma_count = canonical_metric_integer(
        metrics,
        "plasma_process_count",
        1,
        MAX_INTEGER,
    )
    reported_plasma_pss = canonical_metric_integer(
        metrics,
        "plasma_pss_kib",
        1,
        MAX_INTEGER,
    )
    observed_plasma_count, observed_plasma_pss = plasma_inventory(config)
    if (
        reported_plasma_count != observed_plasma_count
        or reported_plasma_pss != observed_plasma_pss
    ):
        raise AcceptanceError("Plasma PSS evidence is incomplete")
    canonical_metric_integer(
        metrics,
        "battery_capacity_percent",
        0,
        100,
    )
    canonical_metric_integer(
        metrics,
        "battery_current_ua",
        -MAX_INTEGER,
        MAX_INTEGER,
    )
    render_count = canonical_metric_integer(
        metrics,
        "drm_render_node_count",
        1,
        1,
    )
    if metrics["battery_status"] not in BATTERY_STATUSES:
        raise AcceptanceError("battery status is not canonical")
    if metrics["screen_state"] not in {"on", "off"}:
        raise AcceptanceError("screen metric is not canonical")
    if thermal > config.thermal_limit_mc:
        raise AcceptanceError("thermal limit exceeded")
    if memory < config.memory_floor_kib:
        raise AcceptanceError("available memory is below policy")
    if render_count != 1:
        raise AcceptanceError("baseline render-node count changed")
    return payload, metrics


def render_open_cycles(config: Configuration) -> None:
    path = task_path(config, "/dev/dri/renderD128")
    expected = path.stat()
    for _attempt in range(config.render_cycles):
        descriptor = os.open(path, os.O_RDWR | os.O_CLOEXEC)
        try:
            observed = os.fstat(descriptor)
            if (
                observed.st_dev,
                observed.st_ino,
                observed.st_rdev,
            ) != (
                expected.st_dev,
                expected.st_ino,
                expected.st_rdev,
            ):
                raise AcceptanceError("render node identity changed")
        finally:
            os.close(descriptor)


def require_hardware_renderer(payload: bytes, label: str) -> str:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise AcceptanceError(f"{label} output is not UTF-8") from error
    if not A660_RENDERER.search(text) or SOFTWARE_RENDERER.search(text):
        raise AcceptanceError(f"{label} did not select hardware A660")
    return text


def run_mesa_gates(
    config: Configuration,
    session: Session,
    watchdog: Watchdog | None,
) -> tuple[str, str, str]:
    first_vulkan = ""
    for attempt in range(config.vulkan_cycles):
        staging_guard(config, watchdog)
        payload = run_session(
            config,
            session,
            "vulkaninfo",
            ["--summary"],
            timeout=30,
        )
        text = require_hardware_renderer(payload, "vulkaninfo")
        if "turnip" not in text.lower():
            raise AcceptanceError("vulkaninfo did not select Turnip")
        if attempt == 0:
            first_vulkan = text
    staging_guard(config, watchdog)
    egl = require_hardware_renderer(
        run_session(
            config,
            session,
            "eglinfo",
            ["-B"],
            timeout=30,
        ),
        "eglinfo",
    )
    support = require_hardware_renderer(
        run_session(
            config,
            session,
            "gdbus",
            [
                "call",
                "--session",
                "--dest",
                "org.kde.KWin",
                "--object-path",
                "/KWin",
                "--method",
                "org.kde.KWin.supportInformation",
            ],
            timeout=30,
        ),
        "KWin support information",
    )
    for _attempt in range(config.submit_cycles):
        staging_guard(config, watchdog)
        payload = run_session(
            config,
            session,
            "submit",
            ["--require-a660"],
            timeout=15,
        )
        text = require_hardware_renderer(payload, "Vulkan submit helper")
        if "submit=pass" not in text:
            raise AcceptanceError("Vulkan submit helper did not pass")
    staging_guard(config, watchdog)
    return first_vulkan, egl, support


def run_wayland_frame_workload(
    config: Configuration,
    session: Session,
    watchdog: Watchdog | None,
) -> None:
    staging_guard(config, watchdog)
    run_session(
        config,
        session,
        "vkcube",
        ["--wsi", "wayland", "--c", "120"],
        timeout=config.workload_seconds,
    )
    staging_guard(config, watchdog)


def screen_state(
    config: Configuration,
    session: Session,
    expected: str,
) -> None:
    state = read_ascii(
        task_path(config, "/run/rog5-screen-state"),
        "screen state",
    )
    brightness = read_ascii(
        task_path(
            config,
            "/sys/class/backlight/panel0-backlight/brightness",
        ),
        "backlight brightness",
    )
    if not brightness.isdecimal():
        raise AcceptanceError("backlight brightness is not numeric")
    if expected == "off" and (state != "off" or brightness != "0"):
        raise AcceptanceError("screen did not enter off state")
    if expected == "on" and (state != "on" or int(brightness) <= 0):
        raise AcceptanceError("screen did not enter on state")
    dpms = run_session(
        config,
        session,
        "kscreen",
        ["--dpms", "show"],
        timeout=15,
    ).decode("utf-8", errors="strict").strip()
    match = DPMS_LINE.fullmatch(dpms)
    if match is None or match.group(1) != expected:
        raise AcceptanceError("screen DPMS state does not match")


def physical_screen_off(config: Configuration) -> None:
    state = read_ascii(
        task_path(config, "/run/rog5-screen-state"),
        "screen state",
    )
    brightness = read_ascii(
        task_path(
            config,
            "/sys/class/backlight/panel0-backlight/brightness",
        ),
        "backlight brightness",
    )
    if (
        not brightness.isdecimal()
        or state != "off"
        or brightness != "0"
    ):
        raise AcceptanceError("screen did not remain physically off")


def set_screen(
    config: Configuration,
    session: Session,
    action: str,
) -> None:
    run_command(
        config,
        "screen",
        [action],
        timeout=15,
    )
    screen_state(config, session, action)


class ScreenOffMonitor:
    """Continuously sample physical darkness in a worker thread."""

    def __init__(self, config: Configuration, session: Session):
        self.config = config
        self.session = session
        self.stop_event = threading.Event()
        self.failure_lock = threading.Lock()
        self.failure: AcceptanceError | None = None
        self.interval = 0.02 if config.fixture else 0.1
        self.thread = threading.Thread(
            target=self._run,
            name="rog5-screen-off-monitor",
            daemon=True,
        )

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                physical_screen_off(self.config)
            except (
                AcceptanceError,
                OSError,
                subprocess.SubprocessError,
                UnicodeError,
            ) as error:
                with self.failure_lock:
                    if self.failure is None:
                        self.failure = AcceptanceError(str(error))
                self.stop_event.set()
                return
            self.stop_event.wait(self.interval)

    def start(self) -> ScreenOffMonitor:
        self.thread.start()
        return self

    def check(self) -> None:
        with self.failure_lock:
            failure = self.failure
        if failure is not None:
            raise failure

    def wait(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while True:
            self.check()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            self.stop_event.wait(min(self.interval, remaining))

    def close(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise AcceptanceError("screen-off monitor did not stop")
        self.check()


def run_screen_cycles(
    config: Configuration,
    session: Session,
    watchdog: Watchdog,
) -> int:
    maximum_thermal = -1
    for _cycle in range(config.screen_cycles):
        staging_guard(config, watchdog)
        set_screen(config, session, "off")
        monitor = ScreenOffMonitor(config, session).start()
        try:
            kwin_is_alive(config, session)
            payload = run_session(
                config,
                session,
                "submit",
                ["--require-a660"],
                timeout=15,
            )
            monitor.check()
            require_hardware_renderer(payload, "screen-off Vulkan submit")
            if b"submit=pass" not in payload:
                raise AcceptanceError("screen-off submit did not pass")
            screen_state(config, session, "off")
            _raw, metrics = collect_metrics(config)
            monitor.check()
            screen_state(config, session, "off")
            maximum_thermal = max(
                maximum_thermal,
                int(metrics["thermal_max_millidegree_c"]),
            )
            monitor.wait(config.screen_pause_seconds)
        finally:
            monitor.close()
        set_screen(config, session, "on")
        kwin_is_alive(config, session)
        time.sleep(config.screen_pause_seconds)
        screen_state(config, session, "on")
        staging_guard(config, watchdog)
    set_screen(config, session, "off")
    staging_guard(config, watchdog)
    return maximum_thermal


def run_soak(
    config: Configuration,
    session: Session,
    monitor: ScreenOffMonitor,
) -> int:
    deadline = time.monotonic() + config.soak_seconds
    maximum_thermal = -1
    while True:
        monitor.check()
        soak_runtime_profile(config)
        kwin_is_alive(config, session)
        payload = run_session(
            config,
            session,
            "submit",
            ["--require-a660"],
            timeout=15,
        )
        require_hardware_renderer(payload, "soak Vulkan submit")
        if b"submit=pass" not in payload:
            raise AcceptanceError("soak submit did not pass")
        monitor.check()
        screen_state(config, session, "off")
        _raw, metrics = collect_metrics(config)
        monitor.check()
        screen_state(config, session, "off")
        maximum_thermal = max(
            maximum_thermal,
            int(metrics["thermal_max_millidegree_c"]),
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        monitor.wait(min(config.soak_interval_seconds, remaining))
    return maximum_thermal


def capture_dmesg(config: Configuration) -> bytes:
    return run_command(
        config,
        "dmesg",
        ["--color=never"],
        timeout=15,
    )


def verify_kernel_delta(before: bytes, after: bytes) -> bytes:
    if len(after) < len(before) or not after.startswith(before):
        raise AcceptanceError("kernel log rotated or changed before baseline")
    delta = after[len(before) :]
    if KERNEL_FAILURE.search(delta):
        raise AcceptanceError("kernel log contains a new GPU failure")
    return delta


def verify_runtime_root_tree(
    config: Configuration,
    runtime: RuntimeProfile,
) -> bytes:
    if runtime.name == "network-root-v1":
        verification_root = "/.rog5/root-ro"
    elif runtime.name == "persistent-root-promoted-v1":
        verification_root = (
            f"{PROMOTED_VERIFICATION_MOUNT}{runtime.root_subtree}"
        )
    else:
        raise AcceptanceError("runtime root profile is unsupported")
    output = run_command(
        config,
        "root_verify",
        [
            verification_root,
            f"{verification_root}/.rog5-persistent-seal",
            runtime.root_seal_sha256,
        ],
        timeout=(
            120
            if runtime.name == "network-root-v1"
            else 300
        ),
    )
    expected = (
        "PASS persistent root matches anchored seal "
        f"entries={runtime.root_tree_entries} "
        f"tree_sha256={runtime.root_tree_sha256}\n"
    ).encode("ascii")
    if output != expected:
        raise AcceptanceError(
            "runtime root tree verification did not match signed identity"
        )
    return output


def result_record(
    config: Configuration,
    runtime: RuntimeProfile,
    before_metrics: dict[str, str],
    after_metrics: dict[str, str],
    maximum_thermal: int,
    kernel_delta: bytes,
) -> bytes:
    fields = (
        (
            "format",
            (
                "rog5-a660-acceptance-fixture-v1"
                if config.fixture
                else "rog5-a660-acceptance-v1"
            ),
        ),
        ("mode", config.mode),
        ("kernel", config.expected_kernel),
        ("runtime_profile", runtime.name),
        ("bundle", runtime.bundle),
        (
            "command_manifest_sha256",
            config.command_manifest_sha256,
        ),
        (
            "root_generation",
            runtime.root_generation or "none",
        ),
        ("root_subtree", runtime.root_subtree or "none"),
        (
            "root_tree_entries",
            str(runtime.root_tree_entries),
        ),
        (
            "root_tree_sha256",
            runtime.root_tree_sha256 or "none",
        ),
        (
            "root_seal_sha256",
            runtime.root_seal_sha256 or "none",
        ),
        ("root_device", runtime.root_device or "none"),
        ("render_open_cycles", str(config.render_cycles)),
        ("vulkaninfo_cycles", str(config.vulkan_cycles)),
        ("submit_cycles", str(config.submit_cycles)),
        (
            "screen_cycles",
            str(config.screen_cycles if config.mode == "staging" else 0),
        ),
        (
            "soak_seconds",
            str(config.soak_seconds if config.mode == "soak" else 0),
        ),
        (
            "thermal_before_mc",
            before_metrics["thermal_max_millidegree_c"],
        ),
        (
            "thermal_after_mc",
            after_metrics["thermal_max_millidegree_c"],
        ),
        ("thermal_observed_max_mc", str(maximum_thermal)),
        (
            "memory_available_before_kib",
            before_metrics["memory_available_kib"],
        ),
        (
            "memory_available_after_kib",
            after_metrics["memory_available_kib"],
        ),
        (
            "plasma_processes_before",
            before_metrics["plasma_process_count"],
        ),
        (
            "plasma_processes_after",
            after_metrics["plasma_process_count"],
        ),
        ("plasma_pss_before_kib", before_metrics["plasma_pss_kib"]),
        ("plasma_pss_after_kib", after_metrics["plasma_pss_kib"]),
        (
            "battery_status_before",
            before_metrics["battery_status"],
        ),
        (
            "battery_status_after",
            after_metrics["battery_status"],
        ),
        (
            "battery_capacity_before_percent",
            before_metrics["battery_capacity_percent"],
        ),
        (
            "battery_capacity_after_percent",
            after_metrics["battery_capacity_percent"],
        ),
        (
            "battery_current_before_ua",
            before_metrics["battery_current_ua"],
        ),
        (
            "battery_current_after_ua",
            after_metrics["battery_current_ua"],
        ),
        ("kernel_delta_sha256", hashlib.sha256(kernel_delta).hexdigest()),
        ("screen_final", "off"),
        ("status", "pass"),
    )
    return "".join(f"{name}={value}\n" for name, value in fields).encode(
        "ascii"
    )


def staging_deadline_expired(
    _signal_number: int,
    _frame: object,
) -> None:
    raise AcceptanceError("staging deadline expired")


def execute(
    config: Configuration,
    session: Session,
    watchdog: Watchdog | None,
    runtime: RuntimeProfile,
) -> bytes:
    final_screen_monitor: ScreenOffMonitor | None = None
    result_published = False
    create_report_directory(config)
    try:
        staging_guard(config, watchdog)
        root_verification = verify_runtime_root_tree(config, runtime)
        write_private(
            config,
            "runtime-root-verification-before.txt",
            root_verification,
        )
        before_dmesg = capture_dmesg(config)
        if KERNEL_FAILURE.search(before_dmesg):
            raise AcceptanceError(
                "kernel log baseline contains a GPU failure"
            )
        before_raw, before_metrics = collect_metrics(config)
        write_private(config, "dmesg-before.log", before_dmesg)
        write_private(config, "metrics-before.txt", before_raw)

        render_open_cycles(config)
        staging_guard(config, watchdog)
        first_vulkan, egl, support = run_mesa_gates(
            config,
            session,
            watchdog,
        )
        write_private(config, "vulkan-summary.txt", first_vulkan.encode())
        write_private(config, "egl-info.txt", egl.encode())
        write_private(config, "kwin-support.txt", support.encode())
        run_wayland_frame_workload(config, session, watchdog)
        if config.mode == "staging":
            if watchdog is None:
                raise AcceptanceError("staging watchdog was not pinned")
            maximum_thermal = run_screen_cycles(
                config,
                session,
                watchdog,
            )
        else:
            set_screen(config, session, "off")
        final_screen_monitor = ScreenOffMonitor(
            config,
            session,
        ).start()
        if config.mode == "soak":
            maximum_thermal = run_soak(
                config,
                session,
                final_screen_monitor,
            )

        final_screen_monitor.check()
        after_raw, after_metrics = collect_metrics(config)
        final_screen_monitor.check()
        after_dmesg = capture_dmesg(config)
        kernel_delta = verify_kernel_delta(before_dmesg, after_dmesg)
        kwin_is_alive(config, session)
        system_is_running(config)
        staging_guard(config, watchdog)
        observed_runtime = (
            staging_runtime_profile(config)
            if config.mode == "staging"
            else soak_runtime_profile(config)
        )
        if observed_runtime != runtime:
            raise AcceptanceError("runtime profile changed during acceptance")
        final_root_verification = verify_runtime_root_tree(config, runtime)
        final_screen_monitor.check()
        if final_root_verification != root_verification:
            raise AcceptanceError(
                "runtime root verification changed during acceptance"
            )
        write_private(
            config,
            "runtime-root-verification-after.txt",
            final_root_verification,
        )
        final_screen_monitor.check()
        maximum_thermal = max(
            maximum_thermal,
            int(before_metrics["thermal_max_millidegree_c"]),
            int(after_metrics["thermal_max_millidegree_c"]),
        )
        write_private(config, "metrics-after.txt", after_raw)
        write_private(config, "dmesg-delta.log", kernel_delta)
        result = result_record(
            config,
            runtime,
            before_metrics,
            after_metrics,
            maximum_thermal,
            kernel_delta,
        )
        write_private(config, ".result.pending", result)
        final_screen_monitor.check()
        final_screen_monitor.close()
        final_screen_monitor = None
        screen_state(config, session, "off")
        os.link(
            config.report / ".result.pending",
            config.report / "result",
            follow_symlinks=False,
        )
        os.unlink(config.report / ".result.pending")
        fsync_directory(config.report)
        result_published = True
        return result
    finally:
        try:
            if final_screen_monitor is not None:
                final_screen_monitor.close()
        finally:
            if not result_published:
                cleanup_error: OSError | None = None
                try:
                    os.unlink(config.report / "result")
                except FileNotFoundError:
                    pass
                except OSError as error:
                    cleanup_error = error
                try:
                    os.unlink(config.report / ".result.pending")
                except FileNotFoundError:
                    pass
                except OSError as error:
                    if cleanup_error is None:
                        cleanup_error = error
                try:
                    fsync_directory(config.report)
                except OSError as error:
                    if cleanup_error is None:
                        cleanup_error = error
                try:
                    run_command(
                        config,
                        "screen",
                        ["off"],
                        timeout=15,
                    )
                except (
                    AcceptanceError,
                    subprocess.TimeoutExpired,
                    OSError,
                ):
                    pass
                if cleanup_error is not None:
                    raise AcceptanceError(
                        "incomplete result retraction failed"
                    ) from cleanup_error


def close_identity(identity: ProcessIdentity | None) -> None:
    if identity is not None and identity.pidfd is not None:
        os.close(identity.pidfd)


def close_commands(config: Configuration | None) -> None:
    if config is None:
        return
    for command in config.commands.values():
        try:
            os.close(command.descriptor)
        except OSError:
            pass


def run_configuration(config: Configuration) -> bytes:
    if config.fixture:
        raise AcceptanceError(
            "production runner rejects fixture configurations"
        )
    if (
        config.mode == "staging"
        and os.environ.get("ALLOW_A660_STAGING_ACCEPTANCE") != "1"
    ):
        raise AcceptanceError("set ALLOW_A660_STAGING_ACCEPTANCE=1")
    if (
        config.mode == "soak"
        and os.environ.get("ALLOW_A660_PROMOTED_SOAK") != "1"
    ):
        raise AcceptanceError("set ALLOW_A660_PROMOTED_SOAK=1")
    session: Session | None = None
    watchdog: Watchdog | None = None
    previous_handler: signal.Handlers | None = None
    if config.mode == "staging":
        previous_handler = signal.signal(
            signal.SIGALRM,
            staging_deadline_expired,
        )
        signal.alarm(config.staging_deadline_seconds)
    try:
        session, watchdog, runtime = preflight(config)
        if config.mode == "preflight":
            return (
                "PASS A660 preflight "
                f"kernel={config.expected_kernel} "
                "render=/dev/dri/renderD128 driver=msm kgsl=absent "
                f"kwin_pid={session.pid}\n"
            ).encode("ascii")
        if runtime is None:
            raise AcceptanceError("runtime profile was not established")
        return execute(config, session, watchdog, runtime)
    finally:
        if config.mode == "staging":
            signal.alarm(0)
            if previous_handler is not None:
                signal.signal(signal.SIGALRM, previous_handler)
        close_identity(session.identity if session is not None else None)
        close_identity(
            watchdog.identity if watchdog is not None else None
        )
        close_identity(
            (
                watchdog.timer_identity
                if watchdog is not None
                else None
            )
        )


def main(arguments: list[str] | None = None) -> int:
    values = sys.argv[1:] if arguments is None else arguments
    mode = values[0] if len(values) == 1 else ""
    config: Configuration | None = None
    try:
        config = configuration(mode)
        result = run_configuration(config)
    except (
        AcceptanceError,
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
        ValueError,
    ) as error:
        if isinstance(error, AcceptanceError):
            message = str(error)
        else:
            message = "host operation failed"
        print(f"FAIL {message}", file=sys.stderr)
        return 1
    finally:
        close_commands(config)
    sys.stdout.buffer.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
