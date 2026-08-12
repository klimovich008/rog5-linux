#!/usr/bin/env python3
"""Pin one volatile target SSH host key through recovery USB continuity."""

from __future__ import annotations

from collections import OrderedDict
import base64
import binascii
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
SYS_DEVICES = Path("/sys/devices")
SYS_BUS_USB = Path("/sys/bus/usb/devices")
SYS_CLASS_TTY = Path("/sys/class/tty")
SYS_CLASS_NET = Path("/sys/class/net")
HOST_BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
IP = Path("/usr/bin/ip")
SSH_KEYSCAN = Path("/usr/bin/ssh-keyscan")

FORMAT = "rog5-minimal-headless-usb-anchor-v1"
RECOVERY_PRODUCT = "ROG5 recovery"
TARGET_PRODUCT = "ROG5 network root"
DIAGNOSTIC_TARGET_PRODUCT = "ROG5 diagnostic network root"
PERSISTENT_TARGET_PRODUCT = "ROG5 persistent root"
FALLBACK_PRODUCT = "ROG Phone 5 Linux Server"
TARGET_PRODUCTS = frozenset(
    (TARGET_PRODUCT, DIAGNOSTIC_TARGET_PRODUCT, PERSISTENT_TARGET_PRODUCT)
)
USB_VENDOR = "1d6b"
USB_PRODUCT = "0104"
TARGET_ADDRESS = "169.254.77.2"
HOST_ADDRESS = "169.254.77.1"
HOST_CIDR = f"{HOST_ADDRESS}/30"
HOST_ALIAS = "rog5-minimal-headless-v1"
ANCHOR_MAX_AGE_SECONDS = 600
# A cold NFS-root handoff on the physical phone took 368.5 seconds to reach
# sshd.  Start this bounded wait immediately after COMMIT and keep it below
# the 600-second recovery-anchor lifetime.
TARGET_WAIT_SECONDS = 420
LOCATION = re.compile(r"[A-Za-z0-9._:+/-]{1,512}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
ANCHOR_KEYS = (
    "format",
    "host_boot_id",
    "created_unix",
    "usb_location",
    "recovery_vendor",
    "recovery_product_id",
    "recovery_product",
)


class BootstrapError(RuntimeError):
    """A bounded, non-sensitive host-key bootstrap refusal."""


class HostKeyNotReady(BootstrapError):
    """The exact target exists but SSH has not exposed its host key yet."""


class HostNetworkNotReady(BootstrapError):
    """The exact target exists before its host-side address is installed."""


def fail(message: str) -> NoReturn:
    raise BootstrapError(message)


def canonical_bytes(values: OrderedDict[str, str]) -> bytes:
    return "".join(
        f"{name}={value}\n" for name, value in values.items()
    ).encode("ascii")


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
            len(payload) < 1
            or len(payload) > maximum
            or (before.st_dev, before.st_ino, before.st_mode)
            != (after.st_dev, after.st_ino, after.st_mode)
        ):
            fail("fixed system record changed while being read")
    except OSError as error:
        raise BootstrapError("cannot read fixed system record") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        value = payload.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise BootstrapError("fixed system record is not ASCII") from error
    if not value or "\n" in value or "\r" in value:
        fail("fixed system record is not one canonical line")
    return value


def host_boot_id() -> str:
    value = read_small_regular(HOST_BOOT_ID)
    if not BOOT_ID.fullmatch(value):
        fail("host boot ID is invalid")
    return value


def safe_new_output(path: Path) -> Path:
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        fail("output path must be one absolute file")
    try:
        parent = path.parent.resolve(strict=True)
        metadata = parent.lstat()
    except OSError as error:
        raise BootstrapError("output parent is unavailable") from error
    resolved_output = parent / path.name
    try:
        resolved_output.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("host-key bootstrap output must remain outside the repository")
    if (
        path.parent != parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail("output parent must be caller-owned mode 0700")
    if path.exists() or path.is_symlink():
        fail("refusing an existing bootstrap output")
    return path


def write_exclusive(path: Path, payload: bytes) -> None:
    if len(payload) < 1 or len(payload) > 4096:
        fail("bootstrap output size is outside policy")
    temporary_descriptor = -1
    temporary_name = ""
    published = False
    succeeded = False
    try:
        temporary_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".rog5-host-key.",
            dir=path.parent,
        )
        os.fchmod(temporary_descriptor, 0o600)
        view = memoryview(payload)
        while view:
            written = os.write(temporary_descriptor, view)
            if written <= 0:
                fail("bootstrap output write made no progress")
            view = view[written:]
        os.fsync(temporary_descriptor)
        metadata = os.fstat(temporary_descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            fail("bootstrap output metadata is unsafe")
        os.close(temporary_descriptor)
        temporary_descriptor = -1
        os.link(temporary_name, path, follow_symlinks=False)
        published = True
        os.unlink(temporary_name)
        temporary_name = ""
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        final = path.lstat()
        if (
            not stat.S_ISREG(final.st_mode)
            or final.st_uid != os.geteuid()
            or stat.S_IMODE(final.st_mode) != 0o600
            or final.st_nlink != 1
            or final.st_size != len(payload)
        ):
            fail("published bootstrap output metadata is unsafe")
        succeeded = True
    except OSError as error:
        raise BootstrapError("cannot publish bootstrap output") from error
    finally:
        if temporary_descriptor >= 0:
            os.close(temporary_descriptor)
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        if published and not succeeded:
            try:
                os.unlink(path)
            except OSError:
                pass


def read_anchor(path: Path) -> OrderedDict[str, str]:
    if not path.is_absolute():
        fail("anchor path must be absolute")
    try:
        resolved = path.resolve(strict=True)
        parent = path.parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as error:
        raise BootstrapError("USB anchor path is unavailable") from error
    try:
        resolved.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("USB anchor must remain outside the repository")
    if (
        resolved != path
        or parent != path.parent
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        fail("USB anchor parent must be caller-owned mode 0700")
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
            or before.st_size < 1
            or before.st_size > 4096
        ):
            fail("anchor metadata is unsafe")
        payload = os.read(descriptor, 4097)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            len(payload) != before.st_size
            or file_identity(before) != file_identity(after)
            or file_identity(before) != file_identity(named)
        ):
            fail("anchor changed while being read")
    except OSError as error:
        raise BootstrapError("cannot read USB anchor") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise BootstrapError("USB anchor is not ASCII") from error
    if len(lines) != len(ANCHOR_KEYS) or not payload.endswith(b"\n"):
        fail("USB anchor field count changed")
    values: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(ANCHOR_KEYS, lines, strict=True):
        name, separator, value = line.partition("=")
        if separator != "=" or name != expected or not value:
            fail("USB anchor is not canonical")
        values[name] = value
    if canonical_bytes(values) != payload:
        fail("USB anchor encoding changed")
    if (
        values["format"] != FORMAT
        or not BOOT_ID.fullmatch(values["host_boot_id"])
        or values["recovery_vendor"] != USB_VENDOR
        or values["recovery_product_id"] != USB_PRODUCT
        or values["recovery_product"] != RECOVERY_PRODUCT
    ):
        fail("USB anchor identity changed")
    validate_location(values["usb_location"])
    require_fresh_anchor(values)
    return values


def require_fresh_anchor(values: OrderedDict[str, str]) -> None:
    created = parse_unix_time(values["created_unix"])
    now = int(time.time())
    if created > now + 5 or now - created > ANCHOR_MAX_AGE_SECONDS:
        fail("USB anchor is stale")
    if values["host_boot_id"] != host_boot_id():
        fail("USB anchor belongs to another host boot")


def parse_unix_time(value: str) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdecimal()
        or value.startswith("0")
    ):
        fail("anchor time is not a positive canonical decimal")
    return int(value)


def validate_location(value: str) -> None:
    if (
        not LOCATION.fullmatch(value)
        or value.startswith("/")
        or ".." in Path(value).parts
    ):
        fail("USB physical location is invalid")


def usb_ancestor(path: Path) -> tuple[Path, str, str, str] | None:
    try:
        resolved = path.resolve(strict=True)
        relative = resolved.relative_to(SYS_DEVICES)
    except (OSError, ValueError):
        return None
    candidates = (SYS_DEVICES / relative, *(SYS_DEVICES / relative).parents)
    for candidate in candidates:
        if candidate == SYS_DEVICES.parent:
            break
        if candidate == SYS_DEVICES:
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
            location = candidate.relative_to(SYS_DEVICES).as_posix()
        except (BootstrapError, ValueError):
            continue
        validate_location(location)
        return candidate, vendor, product_id, product
    return None


def exact_product_location(expected_product: str) -> str:
    locations: set[str] = set()
    try:
        entries = sorted(SYS_BUS_USB.iterdir())
    except OSError as error:
        raise BootstrapError("cannot inspect the USB device inventory") from error
    for entry in entries:
        try:
            device = entry.resolve(strict=True)
            relative = device.relative_to(SYS_DEVICES)
        except (OSError, ValueError):
            continue
        markers = (
            device / "idVendor",
            device / "idProduct",
            device / "product",
        )
        try:
            vendor = read_small_regular(markers[0], 16)
            product_id = read_small_regular(markers[1], 16)
            product = read_small_regular(markers[2], 128)
        except BootstrapError:
            continue
        if (
            vendor != USB_VENDOR
            or product_id != USB_PRODUCT
            or product != expected_product
        ):
            continue
        location = relative.as_posix()
        validate_location(location)
        locations.add(location)
    if len(locations) != 1:
        fail(
            f"expected exactly one raw {expected_product} USB product, "
            f"found {len(locations)}"
        )
    return locations.pop()


def recovery_observation() -> str:
    product_location = exact_product_location(RECOVERY_PRODUCT)
    locations: list[str] = []
    for entry in sorted(SYS_CLASS_TTY.glob("ttyACM*")):
        observed = usb_ancestor(entry)
        if observed is None:
            continue
        device, vendor, product_id, product = observed
        if (
            vendor == USB_VENDOR
            and product_id == USB_PRODUCT
            and product == RECOVERY_PRODUCT
        ):
            locations.append(device.relative_to(SYS_DEVICES).as_posix())
    if len(locations) != 1:
        fail(
            "expected exactly one stable-recovery ACM interface, "
            f"found {len(locations)}"
        )
    if locations[0] != product_location:
        fail("stable-recovery ACM interface escaped the exact USB product")
    return locations[0]


def target_observation(
    expected_product: str = TARGET_PRODUCT,
) -> tuple[str, str]:
    if expected_product not in TARGET_PRODUCTS:
        fail("target USB product is not reviewed")
    product_location = exact_product_location(expected_product)
    matches: list[tuple[str, str]] = []
    for entry in sorted(SYS_CLASS_NET.iterdir()):
        observed = usb_ancestor(entry)
        if observed is None:
            continue
        device, vendor, product_id, product = observed
        if (
            vendor != USB_VENDOR
            or product_id != USB_PRODUCT
            or product != expected_product
        ):
            continue
        driver = entry / "device" / "driver"
        try:
            driver_name = driver.resolve(strict=True).name
        except OSError:
            continue
        if driver_name != "cdc_ncm":
            continue
        matches.append(
            (entry.name, device.relative_to(SYS_DEVICES).as_posix())
        )
    if len(matches) != 1:
        fail(
            "expected exactly one minimal-headless NCM device, "
            f"found {len(matches)}"
        )
    if matches[0][1] != product_location:
        fail("minimal-headless NCM interface escaped the exact USB product")
    return matches[0]


def fallback_returned(expected_location: str) -> bool:
    try:
        location = exact_product_location(FALLBACK_PRODUCT)
    except BootstrapError:
        return False
    if location != expected_location:
        fail("Alpine fallback appeared on a different physical USB port")
    return True


def wait_for_recovery() -> str:
    deadline = time.monotonic() + 5
    previous: str | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        try:
            current = recovery_observation()
        except BootstrapError:
            previous = None
            stable_since = 0.0
        else:
            now = time.monotonic()
            if current != previous:
                previous = current
                stable_since = now
            elif now - stable_since >= 0.5:
                return current
        time.sleep(0.1)
    fail("stable-recovery USB location did not remain stable")


def wait_for_target(
    expected_location: str,
    expected_product: str = TARGET_PRODUCT,
) -> tuple[str, str]:
    deadline = time.monotonic() + TARGET_WAIT_SECONDS
    previous: tuple[str, str] | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        try:
            current = target_observation(expected_product)
        except BootstrapError:
            if fallback_returned(expected_location):
                fail("Alpine fallback returned before target SSH was ready")
            previous = None
            stable_since = 0.0
        else:
            if current[1] != expected_location:
                fail("target re-enumerated on a different physical USB port")
            now = time.monotonic()
            if current != previous:
                previous = current
                stable_since = now
            elif now - stable_since >= 0.5:
                return current
        time.sleep(0.1)
    fail("minimal-headless USB identity did not remain stable")


def require_fixed_binary(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BootstrapError("fixed host command is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o755
    ):
        fail("fixed host command metadata is unsafe")


def exact_route(interface: str) -> None:
    require_fixed_binary(IP)
    address = subprocess.run(
        [str(IP), "-4", "-o", "address", "show", "dev", interface],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
        env={"LC_ALL": "C"},
    )
    address_lines = [
        line.split() for line in address.stdout.splitlines() if line.strip()
    ]
    cidrs = [
        fields[3]
        for fields in address_lines
        if len(fields) > 3 and fields[2] == "inet"
    ]
    if address.returncode != 0:
        fail("cannot inspect the exact target interface address")
    if not cidrs:
        raise HostNetworkNotReady(
            "target interface does not yet have the host /30 address"
        )
    if cidrs != [HOST_CIDR]:
        fail("target interface does not have the exact host /30 address")
    route = subprocess.run(
        [str(IP), "-4", "route", "get", TARGET_ADDRESS],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
        env={"LC_ALL": "C"},
    )
    raw_lines = [line for line in route.stdout.splitlines() if line]
    if (
        route.returncode != 0
        or not raw_lines
        or raw_lines[0][0].isspace()
        or any(not line[0].isspace() for line in raw_lines[1:])
        or [line.strip() for line in raw_lines[1:]]
        not in ([], ["cache"])
    ):
        fail("cannot resolve one exact target route")
    fields = raw_lines[0].split()
    if (
        not fields
        or fields[0] != TARGET_ADDRESS
        or fields.count("dev") != 1
        or fields.count("src") != 1
        or "via" in fields
        or "table" in fields
    ):
        fail("target route is not direct")
    try:
        route_interface = fields[fields.index("dev") + 1]
        source = fields[fields.index("src") + 1]
    except IndexError as error:
        raise BootstrapError("target route is incomplete") from error
    if route_interface != interface or source != HOST_ADDRESS:
        fail("target route escaped the exact USB interface")


def decode_ed25519_blob(value: str) -> bytes:
    try:
        blob = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise BootstrapError("SSH host key is not canonical base64") from error
    expected_prefix = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
    if (
        len(blob) != len(expected_prefix) + 32
        or not blob.startswith(expected_prefix)
        or blob[-32:] == b"\x00" * 32
    ):
        fail("SSH host key is not one nonzero Ed25519 key")
    return blob


def scan_target_key() -> tuple[str, str]:
    require_fixed_binary(SSH_KEYSCAN)
    result = subprocess.run(
        [
            str(SSH_KEYSCAN),
            "-4",
            "-T",
            "5",
            "-t",
            "ed25519",
            TARGET_ADDRESS,
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=8,
        env={"LC_ALL": "C"},
    )
    lines = [
        line for line in result.stdout.splitlines()
        if line and not line.startswith("#")
    ]
    if result.returncode != 0 or not lines:
        raise HostKeyNotReady("target SSH host key is not ready")
    if len(lines) != 1:
        fail("target returned multiple SSH host keys")
    fields = lines[0].split()
    if (
        len(fields) != 3
        or fields[0] != TARGET_ADDRESS
        or fields[1] != "ssh-ed25519"
    ):
        fail("target SSH host-key record is not exact")
    blob = decode_ed25519_blob(fields[2])
    fingerprint = base64.b64encode(hashlib.sha256(blob).digest()).decode(
        "ascii"
    ).rstrip("=")
    return (
        f"{HOST_ALIAS} ssh-ed25519 {fields[2]}\n",
        f"SHA256:{fingerprint}",
    )


def capture_recovery(output: Path) -> str:
    destination = safe_new_output(output)
    location = wait_for_recovery()
    values = OrderedDict(
        (
            ("format", FORMAT),
            ("host_boot_id", host_boot_id()),
            ("created_unix", str(int(time.time()))),
            ("usb_location", location),
            ("recovery_vendor", USB_VENDOR),
            ("recovery_product_id", USB_PRODUCT),
            ("recovery_product", RECOVERY_PRODUCT),
        )
    )
    write_exclusive(destination, canonical_bytes(values))
    return location


def pin_target(
    anchor_path: Path,
    output: Path,
    expected_product: str = TARGET_PRODUCT,
) -> str:
    if expected_product not in TARGET_PRODUCTS:
        fail("target USB product is not reviewed")
    destination = safe_new_output(output)
    anchor = read_anchor(anchor_path)
    expected_location = anchor["usb_location"]
    deadline = time.monotonic() + TARGET_WAIT_SECONDS
    last_not_ready: HostKeyNotReady | None = None
    while time.monotonic() < deadline:
        interface, location = wait_for_target(
            expected_location,
            expected_product,
        )
        try:
            exact_route(interface)
        except HostNetworkNotReady:
            time.sleep(0.25)
            continue
        try:
            record, fingerprint = scan_target_key()
        except HostKeyNotReady as error:
            last_not_ready = error
            time.sleep(0.25)
            continue
        if target_observation(expected_product) != (interface, location):
            fail("target USB identity changed during host-key scan")
        exact_route(interface)
        require_fresh_anchor(anchor)
        write_exclusive(destination, record.encode("ascii"))
        return fingerprint
    if last_not_ready is not None:
        raise last_not_ready
    fail("target SSH host key did not appear")


def main(arguments: list[str]) -> int:
    if os.environ.get(
        "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP"
    ) != "1":
        fail(
            "set ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP=1 "
            "for one public host-key bootstrap"
        )
    if len(arguments) == 2 and arguments[0] == "capture-recovery":
        location = capture_recovery(Path(arguments[1]))
        print(
            "PASS captured one recovery USB continuity anchor "
            f"location={location}"
        )
        return 0
    if len(arguments) == 4 and arguments[0] == "pin-target":
        fingerprint = pin_target(
            Path(arguments[1]),
            Path(arguments[2]),
            arguments[3],
        )
        print(
            "PASS pinned one volatile minimal-headless Ed25519 host key "
            f"fingerprint={fingerprint}"
        )
        return 0
    fail(
        "usage: pin-minimal-headless-host-key.py "
        "capture-recovery OUTPUT | "
        "pin-target ANCHOR KNOWN_HOSTS EXPECTED_PRODUCT"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        BootstrapError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
