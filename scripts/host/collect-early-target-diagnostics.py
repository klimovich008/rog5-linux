#!/usr/bin/env python3
"""Capture one receive-only ROG5 early-target diagnostic stream."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import errno
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import termios
import time
import tty
from typing import Callable, NoReturn, Protocol


REPO = Path(__file__).resolve().parents[2]
PARSER_SOURCE = Path(__file__).with_name("early-target-diagnostics.py")
PARSER_SPEC = importlib.util.spec_from_file_location(
    "rog5_early_target_diagnostics", PARSER_SOURCE
)
if PARSER_SPEC is None or PARSER_SPEC.loader is None:
    raise RuntimeError("cannot load the early-target diagnostic parser")
PARSER = importlib.util.module_from_spec(PARSER_SPEC)
sys.modules[PARSER_SPEC.name] = PARSER
PARSER_SPEC.loader.exec_module(PARSER)

EVIDENCE_FORMAT = "rog5-early-target-evidence-v1"
CANDIDATE = "headless-netroot-early-diag-v1"
ANCHOR_FORMAT = "rog5-minimal-headless-usb-anchor-v1"
RECOVERY_PRODUCT = "ROG5 recovery"
TARGET_PRODUCT = "ROG5 diagnostic network root"
USB_VENDOR = "1d6b"
USB_PRODUCT = "0104"
USB_DRIVER = "cdc_acm"
USB_INTERFACE = "02"
ANCHOR_MAX_AGE_SECONDS = 7200
ENUMERATION_TIMEOUT_SECONDS = 60
CAPTURE_TIMEOUT_SECONDS = 900
MAX_FRAMES = 4096
MAX_USB_EVENTS = 64
MAX_EVENT_BYTES = 256
MAX_JOURNAL_BUFFER = 8192
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
READ_INTERVAL_SECONDS = 0.25
STABLE_ENUMERATION_SECONDS = 0.5
FINAL_EVENT_POLLS = 10
FINAL_EVENT_INTERVAL_SECONDS = 0.05
JOURNAL_STARTUP_SETTLE_SECONDS = 0.05
COLLECTOR_READY = "READY receive-only early-target diagnostic collector"

SYS_DEVICES = Path("/sys/devices")
SYS_BUS_USB = Path("/sys/bus/usb/devices")
SYS_CLASS_TTY = Path("/sys/class/tty")
DEV_ROOT = Path("/dev")
HOST_BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
JOURNALCTL = Path("/usr/bin/journalctl")
FUSER = Path("/usr/bin/fuser")

BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
LOCATION = re.compile(r"[A-Za-z0-9._:+/-]{1,512}\Z")
ANCHOR_FIELDS = (
    "format",
    "host_boot_id",
    "created_unix",
    "usb_location",
    "recovery_vendor",
    "recovery_product_id",
    "recovery_product",
)


class CollectorError(RuntimeError):
    """The collector cannot produce trusted target evidence."""


class CaptureRejected(CollectorError):
    """A stream was observed but failed the capture contract."""

    def __init__(self, code: str, message: str, partial: "CaptureResult"):
        super().__init__(message)
        self.code = code
        self.partial = partial


def fail(message: str) -> NoReturn:
    raise CollectorError(message)


@dataclass(frozen=True)
class AcmIdentity:
    path: str
    location: str
    device_number: int


@dataclass(frozen=True)
class TimestampedRecord:
    host_unix_ns: int
    host_monotonic_ns: int
    record: PARSER.DiagnosticRecord


@dataclass(frozen=True)
class UsbEvent:
    host_unix_ns: int
    message: str


@dataclass(frozen=True)
class CaptureResult:
    frames: tuple[TimestampedRecord, ...]
    usb_events: tuple[UsbEvent, ...]
    dropped_usb_events: int
    end_reason: str


class Clock(Protocol):
    def time_ns(self) -> int: ...

    def monotonic_ns(self) -> int: ...

    def monotonic(self) -> float: ...


class Reader(Protocol):
    def read(self, timeout_seconds: float) -> bytes | None: ...


def file_identity(metadata: os.stat_result) -> tuple[int, ...]:
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


def validate_location(value: str) -> None:
    if (
        not LOCATION.fullmatch(value)
        or value.startswith("/")
        or ".." in Path(value).parts
    ):
        fail("USB physical location is invalid")


def read_small_regular(path: Path, maximum: int = 512) -> str:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            fail("fixed system record metadata is unsafe")
        payload = os.read(descriptor, maximum + 1)
        after = os.fstat(descriptor)
        if (
            not 1 <= len(payload) <= maximum
            or (before.st_dev, before.st_ino, before.st_mode)
            != (after.st_dev, after.st_ino, after.st_mode)
        ):
            fail("fixed system record changed while being read")
    except OSError as error:
        raise CollectorError("cannot read fixed system record") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        value = payload.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise CollectorError("fixed system record is not ASCII") from error
    if not value or "\n" in value or "\r" in value:
        fail("fixed system record is not one canonical line")
    return value


def host_boot_id() -> str:
    value = read_small_regular(HOST_BOOT_ID)
    if not BOOT_ID.fullmatch(value):
        fail("host boot ID is invalid")
    return value


def read_anchor(path: Path) -> OrderedDict[str, str]:
    if not path.is_absolute():
        fail("recovery anchor path must be absolute")
    try:
        resolved = path.resolve(strict=True)
        parent = path.parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as error:
        raise CollectorError("recovery anchor is unavailable") from error
    try:
        resolved.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("recovery anchor must remain outside the repository")
    if (
        resolved != path
        or parent != path.parent
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        fail("recovery anchor parent must be caller-owned mode 0700")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or not 1 <= before.st_size <= 4096
        ):
            fail("recovery anchor metadata is unsafe")
        payload = os.read(descriptor, 4097)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            len(payload) != before.st_size
            or file_identity(before) != file_identity(after)
            or file_identity(before) != file_identity(named)
        ):
            fail("recovery anchor changed while being read")
    except OSError as error:
        raise CollectorError("cannot read recovery anchor") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise CollectorError("recovery anchor is not ASCII") from error
    if len(lines) != len(ANCHOR_FIELDS) or not payload.endswith(b"\n"):
        fail("recovery anchor field count changed")
    values: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(ANCHOR_FIELDS, lines, strict=True):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or not value:
            fail("recovery anchor is not canonical")
        values[name] = value
    canonical = "".join(
        f"{name}={value}\n" for name, value in values.items()
    ).encode("ascii")
    if canonical != payload:
        fail("recovery anchor encoding changed")
    if (
        values["format"] != ANCHOR_FORMAT
        or values["host_boot_id"] != host_boot_id()
        or values["recovery_vendor"] != USB_VENDOR
        or values["recovery_product_id"] != USB_PRODUCT
        or values["recovery_product"] != RECOVERY_PRODUCT
    ):
        fail("recovery anchor identity changed")
    created = values["created_unix"]
    if (
        not created.isascii()
        or not created.isdecimal()
        or created.startswith("0")
    ):
        fail("recovery anchor time is not canonical")
    now = int(time.time())
    if int(created) > now + 5 or now - int(created) > ANCHOR_MAX_AGE_SECONDS:
        fail("recovery anchor is stale")
    validate_location(values["usb_location"])
    return values


def safe_new_output(path: Path) -> Path:
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        fail("evidence output must be one absolute file")
    try:
        parent = path.parent.resolve(strict=True)
        metadata = parent.lstat()
    except OSError as error:
        raise CollectorError("evidence output parent is unavailable") from error
    try:
        path.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("diagnostic evidence must remain outside the repository")
    if (
        parent != path.parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or path.exists()
        or path.is_symlink()
    ):
        fail("evidence output is unsafe or already exists")
    return path


def require_fixed_executable(path: Path, label: str) -> None:
    try:
        metadata = path.stat()
    except OSError as error:
        raise CollectorError(f"{label} is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or not os.access(path, os.X_OK)
    ):
        fail(f"{label} identity is unsafe")


def require_exclusive_holder(path: str) -> None:
    require_fixed_executable(FUSER, "fuser")
    try:
        result = subprocess.run(
            [str(FUSER), path],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            env={"LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CollectorError("cannot inspect diagnostic ACM holders") from error
    holders = {
        int(value)
        for value in result.stdout.split()
        if value.isascii() and value.isdecimal()
    }
    if result.returncode != 0 or holders != {os.getpid()}:
        fail("diagnostic ACM already has another open holder")


def usb_ancestor(path: Path) -> tuple[Path, str, str, str] | None:
    try:
        resolved = path.resolve(strict=True)
        relative = resolved.relative_to(SYS_DEVICES)
    except (OSError, ValueError):
        return None
    candidates = (SYS_DEVICES / relative, *(SYS_DEVICES / relative).parents)
    for candidate in candidates:
        if candidate in {SYS_DEVICES, SYS_DEVICES.parent}:
            continue
        markers = (
            candidate / "idVendor",
            candidate / "idProduct",
            candidate / "product",
        )
        if not all(marker.exists() for marker in markers):
            continue
        try:
            vendor = read_small_regular(markers[0], 16)
            product_id = read_small_regular(markers[1], 16)
            product = read_small_regular(markers[2], 128)
            validate_location(candidate.relative_to(SYS_DEVICES).as_posix())
        except (CollectorError, ValueError):
            continue
        return candidate, vendor, product_id, product
    return None


def diagnostic_product_locations() -> set[str]:
    locations: set[str] = set()
    try:
        entries = sorted(SYS_BUS_USB.iterdir())
    except OSError as error:
        raise CollectorError("cannot inspect USB product inventory") from error
    for entry in entries:
        observed = usb_ancestor(entry)
        if observed is None:
            continue
        device, vendor, product_id, product = observed
        if (
            vendor == USB_VENDOR
            and product_id == USB_PRODUCT
            and product == TARGET_PRODUCT
        ):
            locations.add(device.relative_to(SYS_DEVICES).as_posix())
    return locations


def usb_interface_identity(path: Path, raw: Path) -> tuple[str, str] | None:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return None
    for candidate in (resolved, *resolved.parents):
        if candidate == raw:
            break
        interface = candidate / "bInterfaceNumber"
        driver = candidate / "driver"
        if not interface.exists() or not driver.exists():
            continue
        try:
            number = read_small_regular(interface, 8)
            driver_name = driver.resolve(strict=True).name
        except (CollectorError, OSError):
            return None
        return number, driver_name
    return None


def diagnostic_acm_identities() -> list[AcmIdentity]:
    matches: list[AcmIdentity] = []
    for device in sorted(DEV_ROOT.glob("ttyACM*")):
        try:
            metadata = os.stat(device, follow_symlinks=False)
        except OSError:
            continue
        observed = usb_ancestor(SYS_CLASS_TTY / device.name)
        if observed is None or not stat.S_ISCHR(metadata.st_mode):
            continue
        raw, vendor, product_id, product = observed
        interface = usb_interface_identity(
            SYS_CLASS_TTY / device.name, raw
        )
        if (
            vendor != USB_VENDOR
            or product_id != USB_PRODUCT
            or product != TARGET_PRODUCT
            or interface != (USB_INTERFACE, USB_DRIVER)
            or not os.access(device, os.R_OK)
        ):
            continue
        location = raw.relative_to(SYS_DEVICES).as_posix()
        validate_location(location)
        matches.append(AcmIdentity(str(device), location, metadata.st_rdev))
    return matches


def find_diagnostic_acm(expected_location: str) -> AcmIdentity:
    validate_location(expected_location)
    products = diagnostic_product_locations()
    matches = diagnostic_acm_identities()
    if len(products) != 1 or len(matches) != 1:
        fail(
            "expected exactly one diagnostic USB product and ACM interface, "
            f"found products={len(products)} acm={len(matches)}"
        )
    identity = matches[0]
    if products != {identity.location}:
        fail("diagnostic ACM escaped the exact USB product")
    if identity.location != expected_location:
        fail("diagnostic target enumerated on another physical USB port")
    return identity


def revalidate_diagnostic_acm(identity: AcmIdentity) -> None:
    if find_diagnostic_acm(identity.location) != identity:
        fail("diagnostic ACM identity changed during capture")


def wait_diagnostic_acm(
    expected_location: str,
    timeout_seconds: float,
    poll_events: Callable[[], list[UsbEvent]],
) -> AcmIdentity:
    deadline = time.monotonic() + timeout_seconds
    candidate: AcmIdentity | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        poll_events()
        try:
            observed = find_diagnostic_acm(expected_location)
        except (CollectorError, OSError):
            candidate = None
            stable_since = 0.0
        else:
            now = time.monotonic()
            if observed != candidate:
                candidate = observed
                stable_since = now
            elif now - stable_since >= STABLE_ENUMERATION_SECONDS:
                return observed
        time.sleep(0.1)
    fail("exact diagnostic ACM did not become stable before its deadline")


class ReceiveOnlySerial:
    """An exclusive descriptor with no writable phone-facing surface."""

    def __init__(self, identity: AcmIdentity):
        self.identity = identity
        self._descriptor = -1

    def __enter__(self) -> "ReceiveOnlySerial":
        flags = os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC
        try:
            self._descriptor = os.open(self.identity.path, flags)
        except OSError as error:
            raise CollectorError(
                "cannot open the exact diagnostic ACM"
            ) from error
        try:
            metadata = os.fstat(self._descriptor)
            if (
                not stat.S_ISCHR(metadata.st_mode)
                or metadata.st_rdev != self.identity.device_number
            ):
                fail("opened diagnostic ACM identity changed")
            fcntl.flock(
                self._descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB
            )
            fcntl.ioctl(self._descriptor, termios.TIOCEXCL)
            tty.setraw(self._descriptor, termios.TCSANOW)
            attributes = termios.tcgetattr(self._descriptor)
            attributes[0] &= ~(
                termios.IXON
                | termios.IXOFF
                | termios.ICRNL
                | termios.INLCR
            )
            attributes[1] &= ~termios.OPOST
            attributes[2] &= ~termios.HUPCL
            attributes[2] |= termios.CLOCAL | termios.CREAD
            attributes[3] &= ~(
                termios.ECHO
                | termios.ECHOE
                | termios.ECHOK
                | termios.ECHONL
                | termios.ICANON
            )
            attributes[4] = termios.B115200
            attributes[5] = termios.B115200
            attributes[6][termios.VMIN] = 0
            attributes[6][termios.VTIME] = 0
            termios.tcsetattr(
                self._descriptor, termios.TCSANOW, attributes
            )
            require_exclusive_holder(self.identity.path)
        except CollectorError:
            os.close(self._descriptor)
            self._descriptor = -1
            raise
        except OSError as error:
            os.close(self._descriptor)
            self._descriptor = -1
            raise CollectorError(
                "cannot secure the diagnostic ACM reader"
            ) from error
        except BaseException:
            os.close(self._descriptor)
            self._descriptor = -1
            raise
        return self

    def __exit__(self, *_: object) -> None:
        if self._descriptor >= 0:
            os.close(self._descriptor)
            self._descriptor = -1

    def fileno(self) -> int:
        return self._descriptor

    def read(self, timeout_seconds: float) -> bytes | None:
        if self._descriptor < 0:
            fail("diagnostic ACM reader is not open")
        try:
            readable, _, _ = select.select(
                [self._descriptor], [], [], timeout_seconds
            )
        except OSError as error:
            if error.errno == errno.EINTR:
                return None
            raise CollectorError("diagnostic ACM wait failed") from error
        if not readable:
            return None
        try:
            chunk = os.read(self._descriptor, 4096)
        except OSError as error:
            if error.errno in {errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR}:
                return None
            if error.errno == errno.EIO:
                return b""
            raise CollectorError("diagnostic ACM read failed") from error
        return chunk


class KernelEventFilter:
    def __init__(self, port: str):
        if not re.fullmatch(r"[0-9]+-[0-9]+(?:\.[0-9]+)*", port):
            fail("USB kernel port token is invalid")
        self.port = port
        self.pattern = re.compile(
            rf"(?:usb|cdc_acm|cdc_ncm)\s+{re.escape(port)}(?:[: ])",
            re.IGNORECASE,
        )
        self.events: list[UsbEvent] = []
        self.dropped = 0

    def accept(self, line: bytes, host_unix_ns: int) -> list[UsbEvent]:
        text = line.decode("utf-8", errors="replace").strip()
        if (
            not self.pattern.search(text)
            or "serialnumber" in text.lower()
        ):
            return []
        sanitized = "".join(
            character if 32 <= ord(character) < 127 else "?"
            for character in text
        )
        encoded = sanitized.encode("ascii")[:MAX_EVENT_BYTES]
        message = encoded.decode("ascii")
        if len(self.events) >= MAX_USB_EVENTS:
            self.dropped += 1
            return []
        event = UsbEvent(host_unix_ns, message)
        self.events.append(event)
        return [event]


class KernelJournal:
    """A bounded reader for matching kernel USB journal lines."""

    def __init__(self, location: str):
        validate_location(location)
        self.filter = KernelEventFilter(Path(location).name)
        self.process: subprocess.Popen[bytes] | None = None
        self.buffer = bytearray()

    def __enter__(self) -> "KernelJournal":
        require_fixed_executable(JOURNALCTL, "journalctl")
        try:
            self.process = subprocess.Popen(
                [
                    str(JOURNALCTL),
                    "--dmesg",
                    "--follow",
                    "--lines=0",
                    "--output=short-monotonic",
                    "--no-pager",
                    "--quiet",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                env={"LC_ALL": "C"},
            )
        except OSError as error:
            raise CollectorError("cannot start bounded kernel event reader") from error
        assert self.process.stdout is not None
        os.set_blocking(self.process.stdout.fileno(), False)
        try:
            time.sleep(JOURNAL_STARTUP_SETTLE_SECONDS)
            running = self.process.poll() is None
        except BaseException:
            self.__exit__()
            raise
        if not running:
            self.__exit__()
            fail("kernel event reader exited during startup")
        return self

    def __exit__(self, *_: object) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        if self.process.stdout is not None:
            self.process.stdout.close()
        self.process = None

    def poll(self) -> list[UsbEvent]:
        if self.process is None or self.process.stdout is None:
            fail("kernel event reader is not running")
        descriptor = self.process.stdout.fileno()
        events: list[UsbEvent] = []
        while True:
            ready, _, _ = select.select([descriptor], [], [], 0)
            if not ready:
                break
            try:
                chunk = os.read(descriptor, 4096)
            except OSError as error:
                if error.errno in {
                    errno.EAGAIN,
                    errno.EWOULDBLOCK,
                    errno.EINTR,
                }:
                    break
                raise CollectorError("kernel event read failed") from error
            if not chunk:
                if self.process.poll() is not None:
                    fail("kernel event reader exited during capture")
                break
            events.extend(self.consume(chunk))
        return events

    def consume(self, chunk: bytes) -> list[UsbEvent]:
        self.buffer.extend(chunk)
        events: list[UsbEvent] = []
        while b"\n" in self.buffer:
            line, _, remainder = self.buffer.partition(b"\n")
            self.buffer = bytearray(remainder)
            if len(line) > MAX_JOURNAL_BUFFER:
                fail("kernel event line exceeds its memory bound")
            events.extend(self.filter.accept(line, time.time_ns()))
        if len(self.buffer) > MAX_JOURNAL_BUFFER:
            fail("kernel event line exceeds its memory bound")
        return events


def settle_kernel_events(
    poll_events: Callable[[], list[UsbEvent]],
) -> None:
    for attempt in range(FINAL_EVENT_POLLS):
        poll_events()
        if attempt + 1 != FINAL_EVENT_POLLS:
            time.sleep(FINAL_EVENT_INTERVAL_SECONDS)


def rejected(
    code: str,
    message: str,
    frames: list[TimestampedRecord],
    events: list[UsbEvent],
    dropped_events: int,
) -> NoReturn:
    partial = CaptureResult(
        tuple(frames), tuple(events), dropped_events, "rejected"
    )
    raise CaptureRejected(code, message, partial)


def capture_stream(
    reader: Reader,
    expected_candidate: str,
    *,
    deadline_monotonic: float,
    clock: Clock = time,
    revalidate: Callable[[], None],
    poll_events: Callable[[], list[UsbEvent]],
    initial_events: tuple[UsbEvent, ...] = (),
    initial_dropped_events: int = 0,
) -> CaptureResult:
    stream = PARSER.DiagnosticStream(expected_candidate)
    frames: list[TimestampedRecord] = []
    events = list(initial_events)
    dropped_events = initial_dropped_events

    def retain(records: list[PARSER.DiagnosticRecord]) -> None:
        for record in records:
            if len(frames) >= MAX_FRAMES:
                rejected(
                    "frame-limit",
                    "diagnostic stream exceeded its frame bound",
                    frames,
                    events,
                    dropped_events,
                )
            frames.append(
                TimestampedRecord(
                    clock.time_ns(), clock.monotonic_ns(), record
                )
            )

    try:
        revalidate()
    except CollectorError as error:
        rejected("identity-changed", str(error), frames, events, dropped_events)
    while True:
        try:
            events.extend(poll_events())
        except CollectorError as error:
            rejected("kernel-events", str(error), frames, events, dropped_events)
        remaining = deadline_monotonic - clock.monotonic()
        if remaining <= 0:
            try:
                stream.finalize()
            except PARSER.DiagnosticError:
                rejected(
                    "truncated-stream",
                    "diagnostic stream ended with a partial frame",
                    frames,
                    events,
                    dropped_events,
                )
            if not frames:
                rejected(
                    "no-records",
                    "diagnostic capture deadline passed without a record",
                    frames,
                    events,
                    dropped_events,
                )
            return CaptureResult(
                tuple(frames), tuple(events), dropped_events, "timeout"
            )
        try:
            chunk = reader.read(min(READ_INTERVAL_SECONDS, remaining))
        except CollectorError as error:
            rejected("read-failed", str(error), frames, events, dropped_events)
        if chunk is None:
            continue
        if chunk == b"":
            try:
                stream.finalize()
            except PARSER.DiagnosticError:
                rejected(
                    "truncated-stream",
                    "diagnostic stream disconnected with a partial frame",
                    frames,
                    events,
                    dropped_events,
                )
            if not frames:
                rejected(
                    "no-records",
                    "diagnostic ACM disconnected without a valid record",
                    frames,
                    events,
                    dropped_events,
                )
            return CaptureResult(
                tuple(frames), tuple(events), dropped_events, "disconnected"
            )
        for byte in chunk:
            try:
                accepted = stream.feed(bytes((byte,)))
            except PARSER.DiagnosticError as error:
                rejected(
                    "invalid-stream",
                    f"diagnostic stream violated policy: {error}",
                    frames,
                    events,
                    dropped_events,
                )
            retain(accepted)


def evidence_document(
    *,
    anchor: OrderedDict[str, str],
    started_unix_ns: int,
    ended_unix_ns: int,
    result: CaptureResult,
    rejection_code: str | None = None,
    rejection_message: str | None = None,
) -> dict[str, object]:
    records = []
    for frame in result.frames:
        records.append(
            {
                "host_monotonic_ns": frame.host_monotonic_ns,
                "host_unix_ns": frame.host_unix_ns,
                "record": asdict(frame.record),
            }
        )
    events = [asdict(event) for event in result.usb_events]
    boot_ids = {frame.record.boot_id for frame in result.frames}
    document: dict[str, object] = {
        "candidate": CANDIDATE,
        "capture_status": "rejected" if rejection_code else "valid",
        "dropped_usb_events": result.dropped_usb_events,
        "ended_unix_ns": ended_unix_ns,
        "end_reason": result.end_reason,
        "format": EVIDENCE_FORMAT,
        "frame_count": len(records),
        "frames": records,
        "host_boot_id": anchor["host_boot_id"],
        "started_unix_ns": started_unix_ns,
        "target_boot_id": next(iter(boot_ids)) if len(boot_ids) == 1 else None,
        "target_product": TARGET_PRODUCT,
        "usb_events": events,
        "usb_location": anchor["usb_location"],
    }
    if rejection_code is not None:
        document["rejection_code"] = rejection_code
        document["rejection_message"] = rejection_message
    return document


def encode_evidence(document: dict[str, object]) -> bytes:
    try:
        payload = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError) as error:
        raise CollectorError("diagnostic evidence is not serializable") from error
    if not 1 <= len(payload) <= MAX_EVIDENCE_BYTES:
        fail("diagnostic evidence exceeds its size bound")
    return payload


def write_evidence(path: Path, payload: bytes) -> None:
    destination = safe_new_output(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    descriptor = os.open(destination, flags, 0o600)
    succeeded = False
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("diagnostic evidence write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            fail("diagnostic evidence metadata is unsafe")
        succeeded = True
    finally:
        os.close(descriptor)
        if not succeeded:
            try:
                destination.unlink()
            except OSError:
                pass
    directory = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def parse_timeout(value: str, label: str, maximum: int) -> int:
    if (
        not value.isascii()
        or not value.isdecimal()
        or value.startswith("0")
    ):
        fail(f"{label} must be a positive canonical decimal")
    parsed = int(value)
    if not 1 <= parsed <= maximum:
        fail(f"{label} is outside policy")
    return parsed


def usage() -> NoReturn:
    fail(
        "usage: collect-early-target-diagnostics.py ANCHOR OUTPUT "
        "[ENUMERATION_TIMEOUT] [CAPTURE_TIMEOUT]"
    )


def main(arguments: list[str]) -> int:
    if not 2 <= len(arguments) <= 4:
        usage()
    anchor_path = Path(arguments[0])
    output_path = Path(arguments[1])
    enumeration_timeout = (
        parse_timeout(arguments[2], "enumeration timeout", 120)
        if len(arguments) >= 3
        else ENUMERATION_TIMEOUT_SECONDS
    )
    capture_timeout = (
        parse_timeout(arguments[3], "capture timeout", 900)
        if len(arguments) == 4
        else CAPTURE_TIMEOUT_SECONDS
    )
    anchor = read_anchor(anchor_path)
    safe_new_output(output_path)
    started_unix_ns = time.time_ns()
    result: CaptureResult
    pre_capture_events: tuple[UsbEvent, ...] = ()
    pre_capture_dropped = 0
    observed: CaptureResult | None = None
    rejection_code: str | None = None
    rejection_message: str | None = None
    try:
        with KernelJournal(anchor["usb_location"]) as journal:
            print(COLLECTOR_READY, flush=True)
            primary_error: BaseException | None = None
            try:
                identity = wait_diagnostic_acm(
                    anchor["usb_location"], enumeration_timeout, journal.poll
                )
                initial_events = tuple(journal.filter.events)
                initial_dropped = journal.filter.dropped
                with ReceiveOnlySerial(identity) as serial:
                    observed = capture_stream(
                        serial,
                        CANDIDATE,
                        deadline_monotonic=time.monotonic() + capture_timeout,
                        revalidate=lambda: revalidate_diagnostic_acm(identity),
                        poll_events=journal.poll,
                        initial_events=initial_events,
                        initial_dropped_events=initial_dropped,
                    )
            except BaseException as error:
                primary_error = error
            finally:
                try:
                    settle_kernel_events(journal.poll)
                except CollectorError as error:
                    if primary_error is None:
                        primary_error = error
                finally:
                    pre_capture_events = tuple(journal.filter.events)
                    pre_capture_dropped = journal.filter.dropped
            if primary_error is not None:
                raise primary_error
        if observed is None:
            fail("diagnostic capture returned without a result")
        result = CaptureResult(
            observed.frames,
            pre_capture_events,
            pre_capture_dropped,
            observed.end_reason,
        )
    except CaptureRejected as error:
        result = CaptureResult(
            error.partial.frames,
            pre_capture_events,
            pre_capture_dropped,
            error.partial.end_reason,
        )
        rejection_code = error.code
        rejection_message = str(error)
    except CollectorError as error:
        result = CaptureResult(
            observed.frames if observed is not None else (),
            pre_capture_events,
            pre_capture_dropped,
            "rejected",
        )
        rejection_code = (
            "collector-finalization"
            if observed is not None
            else "collector-preflight"
        )
        rejection_message = str(error)
    document = evidence_document(
        anchor=anchor,
        started_unix_ns=started_unix_ns,
        ended_unix_ns=time.time_ns(),
        result=result,
        rejection_code=rejection_code,
        rejection_message=rejection_message,
    )
    write_evidence(output_path, encode_evidence(document))
    if rejection_code is not None:
        print(
            f"FAIL early-target diagnostic capture: {rejection_code}",
            file=sys.stderr,
        )
        return 1
    last = result.frames[-1].record
    print(
        "PASS receive-only early-target diagnostic capture "
        f"frames={len(result.frames)} last={last.stage_code}:{last.stage} "
        f"end={result.end_reason}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except CollectorError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from None
