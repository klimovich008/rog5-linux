#!/usr/bin/env python3
"""Verify and reboot the configuration-unchanged Alpine fallback over ACM."""

from __future__ import annotations

from collections import OrderedDict
import base64
import binascii
import errno
import fcntl
import glob
import hashlib
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
from typing import NoReturn
import zlib


REPO = Path(__file__).resolve().parents[2]
FORMAT = "rog5-fallback-acm-v1"
IDENTITY_FORMAT = "rog5-fallback-identity-v2"
HOST_ALIAS = "rog5-fallback"
SIGN_NAMESPACE = "rog5-fallback-acm-v1"
FALLBACK_KERNEL = "5.4.134-qgki-perf-00001-g6c308144c23e"
USB_VENDOR = "1d6b"
USB_PRODUCT = "0104"
USB_MODEL = "ROG_Phone_5_Linux_Server"
USB_PRODUCT_NAME = "ROG Phone 5 Linux Server"
RECOVERY_PRODUCT_NAME = "ROG5 recovery"
USB_INTERFACE = "02"
USB_DRIVER = "cdc_acm"
USB_NCM_INTERFACE = "00"
USB_NCM_DRIVER = "cdc_ncm"
FALLBACK_ADDRESS = "169.254.77.2"
HOST_ADDRESS = "169.254.77.1"
HOST_CIDR = f"{HOST_ADDRESS}/30"
FALLBACK_NETWORK_PROFILE = "rog5-fallback-usb-ssh"
FASTBOOT_VENDOR = "0b05"
FASTBOOT_PRODUCT = "4daf"
MAX_SERIAL_OUTPUT = 128 * 1024
# Alpine 3.24 sets CONFIG_FEATURE_EDITING_MAX_LEN=2048. Keep the complete
# interactive launcher, including its newline, below a stricter local bound.
BUSYBOX_EDITING_MAX_LEN = 2048
MAX_LAUNCHER_LINE_BYTES = 2000
SOURCE_CHUNK_BYTES = 1800
MAX_SOURCE_CHUNKS = 4
SHELL_READY_TIMEOUT_SECONDS = 5
LOADER_READY_TIMEOUT_SECONDS = 10
LOADER_RECEIVE_TIMEOUT_SECONDS = 20
PREPARED_FRAME_TIMEOUT_SECONDS = 45
MAX_PREFLIGHT_THERMAL = 60000
MAX_RETURN_THERMAL = 80000
REBOOT_COMMIT_TIMEOUT_SECONDS = 30
MIN_THERMAL_ZONES = 70
MAX_THERMAL_ZONES = 128
MIN_VALID_THERMAL_READINGS = 29
REQUIRED_THERMAL_TYPES = frozenset(
    {
        "aoss-0-usr",
        "cpu-0-0-usr",
        "cpu-1-0-usr",
        "gpuss-0-usr",
        "mdmss-0-usr",
        "nspss-0-usr",
    }
)
INACTIVE_THERMAL_VALUES = frozenset({0, -274000})
UNAVAILABLE_THERMAL_TYPES = frozenset(
    {
        "camera-therm-usr",
        "modem-ambient-usr",
        "modem-lte-sub6-pa1",
        "modem-lte-sub6-pa2",
        "modem-mmw-pa1-usr",
        "modem-mmw-pa2-usr",
        "modem-mmw-pa3-usr",
        "modem-mmw0-mod-usr",
        "modem-mmw0-usr",
        "modem-mmw1-mod-usr",
        "modem-mmw1-usr",
        "modem-mmw2-mod-usr",
        "modem-mmw2-usr",
        "modem-mmw3-mod-usr",
        "modem-mmw3-usr",
        "modem-sdr-mmw-usr",
        "modem-skin-usr",
        "modem-streamer-usr",
        "modem-wifi-usr",
        "pmr735b_tz",
        "rear-cam-therm-usr",
        "tof-therm-usr",
        "wlc-therm-usr",
    }
)
ANCHOR_MAX_AGE_SECONDS = 7200
ZERO_ID = "0" * 32
NONCE = re.compile(r"[0-9a-f]{32}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
LOCATION = re.compile(r"[A-Za-z0-9._:/+-]{1,512}\Z")
CSI = re.compile(rb"\x1b\[[0-9;?]*[ -/]*[@-~]")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
UDEVADM = Path("/usr/bin/udevadm")
SSH_KEYGEN = Path("/usr/bin/ssh-keygen")
SSH = Path("/usr/bin/ssh")
IP = Path("/usr/bin/ip")
NMCLI = Path("/usr/bin/nmcli")
FASTBOOT = Path("/usr/bin/fastboot")
SYSTEMCTL = Path("/usr/bin/systemctl")
FUSER = Path("/usr/bin/fuser")
SYS_DEVICES = Path("/sys/devices")
SYS_BUS_USB = Path("/sys/bus/usb/devices")
SYS_CLASS_TTY = Path("/sys/class/tty")
SYS_CLASS_NET = Path("/sys/class/net")
HOST_BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
ANCHOR_FIELDS = (
    "format",
    "host_boot_id",
    "created_unix",
    "usb_location",
    "recovery_vendor",
    "recovery_product_id",
    "recovery_product",
)
REMOTE_ERROR_CODES = frozenset(
    {
        "ack",
        "ack-timeout",
        "boot-id-changed",
        "health",
        "host-key-sign",
        "post-ack-timeout",
        "probe",
    }
)
RESULT_FIELDS = (
    "format",
    "nonce",
    "action",
    "kernel_release",
    "init",
    "compatible",
    "root_fstype",
    "modules_checked",
    "project_modules",
    "pstore_checked",
    "pstore_records",
    "dmesg_checked",
    "fatal_lines",
    "thermal_samples",
    "thermal_zones",
    "thermal_max",
    "python_major",
    "boot_id",
    "result",
)


LOADER_SOURCE = f'''
import base64
import hashlib
import os
import select
import sys
import time
import zlib

SOURCE_CHUNK_BYTES = {SOURCE_CHUNK_BYTES}
MAX_RECEIVE_TIMEOUT_SECONDS = {LOADER_RECEIVE_TIMEOUT_SECONDS}

if len(sys.argv) != 7:
    raise SystemExit(80)
count = int(sys.argv[1])
size = int(sys.argv[2])
expected_sha256 = sys.argv[3]
nonce = sys.argv[4]
action = sys.argv[5]
receive_timeout = int(sys.argv[6])
if (
    count < 1
    or size < 1
    or not 1 <= receive_timeout <= MAX_RECEIVE_TIMEOUT_SECONDS
):
    raise SystemExit(81)
print("ROG5_FALLBACK_LOADER_READY", nonce, flush=True)
deadline = time.monotonic() + receive_timeout
wire = bytearray()
wire_size = size + count
while wire.count(b"\\n") < count:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SystemExit(90)
    ready, _, _ = select.select([sys.stdin], [], [], remaining)
    if not ready:
        raise SystemExit(90)
    chunk = os.read(sys.stdin.fileno(), wire_size - len(wire) + 1)
    if not chunk:
        raise SystemExit(90)
    wire.extend(chunk)
    if len(wire) > wire_size:
        raise SystemExit(91)
parts = bytes(wire).splitlines(keepends=True)
if (
    len(parts) != count
    or any(
        not part.endswith(b"\\n")
        or len(part) > SOURCE_CHUNK_BYTES + 1
        for part in parts
    )
):
    raise SystemExit(91)
encoded = b"".join(part[:-1] for part in parts)
if (
    len(encoded) != size
    or hashlib.sha256(encoded).hexdigest() != expected_sha256
):
    raise SystemExit(91)
sys.argv = [sys.argv[0], nonce, action]
exec(zlib.decompress(base64.b64decode(encoded, validate=True)))
'''


REMOTE_SOURCE = r'''
import base64
import ctypes
import os
from pathlib import Path
import platform
import re
import select
import stat
import subprocess
import sys
import time

FORMAT = "rog5-fallback-acm-v1"
NAMESPACE = "rog5-fallback-acm-v1"
KERNEL = "5.4.134-qgki-perf-00001-g6c308144c23e"
MAX_PREFLIGHT_THERMAL = 60000
MAX_RETURN_THERMAL = 80000
MIN_THERMAL_ZONES = 70
MAX_THERMAL_ZONES = 128
MIN_VALID_THERMAL_READINGS = 29
REQUIRED_THERMAL_TYPES = {
    "aoss-0-usr",
    "cpu-0-0-usr",
    "cpu-1-0-usr",
    "gpuss-0-usr",
    "mdmss-0-usr",
    "nspss-0-usr",
}
INACTIVE_THERMAL_VALUES = {0, -274000}
UNAVAILABLE_THERMAL_TYPES = {
    "camera-therm-usr",
    "modem-ambient-usr",
    "modem-lte-sub6-pa1",
    "modem-lte-sub6-pa2",
    "modem-mmw-pa1-usr",
    "modem-mmw-pa2-usr",
    "modem-mmw-pa3-usr",
    "modem-mmw0-mod-usr",
    "modem-mmw0-usr",
    "modem-mmw1-mod-usr",
    "modem-mmw1-usr",
    "modem-mmw2-mod-usr",
    "modem-mmw2-usr",
    "modem-mmw3-mod-usr",
    "modem-mmw3-usr",
    "modem-sdr-mmw-usr",
    "modem-skin-usr",
    "modem-streamer-usr",
    "modem-wifi-usr",
    "pmr735b_tz",
    "rear-cam-therm-usr",
    "tof-therm-usr",
    "wlc-therm-usr",
}
REBOOT_ACK_TIMEOUT_SECONDS = 30
POST_ACK_DEADLINE_SECONDS = 25
HOST_KEY = Path("/etc/ssh/ssh_host_ed25519_key")
FATAL = re.compile(
    rb"(^|[^A-Za-z0-9_])(Kernel panic|Oops:|BUG:|"
    rb"watchdog[ _-]+bite|Kernel fault|Unable to handle kernel|"
    rb"Synchronous External Abort)([^A-Za-z0-9_]|$)",
    re.IGNORECASE | re.MULTILINE,
)


def stop(nonce, code):
    print("ROG5_FALLBACK_ACM_ERROR", nonce, code, flush=True)
    raise SystemExit(1)


def mount_type():
    for line in Path("/proc/mounts").read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[1] == "/":
            return fields[2]
    return ""


def pstore_count():
    available = 0
    paths = set()
    for name in ("/sys/fs/pstore", "/mnt/pstore"):
        root = Path(name)
        if not root.is_dir():
            continue
        available += 1
        try:
            entries = list(root.iterdir())
        except OSError:
            return 0, 0
        for entry in entries:
            try:
                if entry.is_file():
                    paths.add(str(entry.resolve()))
            except OSError:
                return 0, 0
    return available, len(paths)


def temperatures():
    try:
        observed = {
            str(path)
            for path in Path("/sys/class/thermal").glob(
                "thermal_zone*/temp"
            )
        }
    except OSError:
        return 0, 0, 0
    zone_count = len(observed)
    expected = {
        f"/sys/class/thermal/thermal_zone{index}/temp"
        for index in range(zone_count)
    }
    if (
        not MIN_THERMAL_ZONES <= zone_count <= MAX_THERMAL_ZONES
        or observed != expected
    ):
        return 0, 0, 0
    maxima = []
    counts = []
    for sample in range(3):
        values = []
        required = set()
        for index in range(zone_count):
            root = f"/sys/class/thermal/thermal_zone{index}"
            try:
                thermal_type = Path(f"{root}/type").read_text().strip()
            except OSError:
                return 0, 0, 0
            try:
                raw_value = Path(f"{root}/temp").read_text().strip()
            except OSError:
                if thermal_type in UNAVAILABLE_THERMAL_TYPES:
                    continue
                return 0, 0, 0
            try:
                value = int(raw_value)
            except ValueError:
                return 0, 0, 0
            if value in INACTIVE_THERMAL_VALUES:
                continue
            if not 0 < value <= 200000:
                return 0, 0, 0
            values.append(value)
            if thermal_type in REQUIRED_THERMAL_TYPES:
                required.add(thermal_type)
        if (
            len(values) < MIN_VALID_THERMAL_READINGS
            or required != REQUIRED_THERMAL_TYPES
        ):
            return 0, 0, 0
        counts.append(len(values))
        maxima.append(max(values))
        if sample != 2:
            time.sleep(0.5)
    if len(set(counts)) != 1:
        return 0, 0, 0
    return 3, zone_count, max(maxima)


def collect(nonce, action):
    compatible = Path("/proc/device-tree/compatible").read_bytes().split(b"\0")
    modules_path = Path("/proc/modules")
    modules = modules_path.read_text().splitlines()
    project_modules = sum(
        1 for line in modules if line.split() and line.split()[0].startswith("rog5_")
    )
    pstore_checked, pstore_records = pstore_count()
    dmesg = subprocess.run(
        ["/bin/dmesg"],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    thermal_samples, thermal_zones, thermal_max = temperatures()
    values = [
        ("format", FORMAT),
        ("nonce", nonce),
        ("action", action),
        ("kernel_release", platform.release()),
        ("init", os.readlink("/proc/1/exe")),
        (
            "compatible",
            "qcom,lahaina-mtp"
            if b"qcom,lahaina-mtp" in compatible
            else "unexpected",
        ),
        ("root_fstype", mount_type()),
        ("modules_checked", "1" if modules_path.is_file() else "0"),
        ("project_modules", str(project_modules)),
        ("pstore_checked", "1" if pstore_checked else "0"),
        ("pstore_records", str(pstore_records)),
        ("dmesg_checked", "1" if dmesg.returncode == 0 else "0"),
        (
            "fatal_lines",
            str(len(FATAL.findall(dmesg.stdout))) if dmesg.returncode == 0 else "-1",
        ),
        ("thermal_samples", str(thermal_samples)),
        ("thermal_zones", str(thermal_zones)),
        ("thermal_max", str(thermal_max)),
        ("python_major", str(sys.version_info.major)),
        (
            "boot_id",
            Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        ),
        ("result", "PASS"),
    ]
    result = dict(values)
    thermal_limit = (
        MAX_RETURN_THERMAL
        if action == "classify"
        else MAX_PREFLIGHT_THERMAL
    )
    if (
        result["kernel_release"] != KERNEL
        or result["init"] != "/bin/busybox"
        or result["compatible"] != "qcom,lahaina-mtp"
        or result["root_fstype"] != "ext4"
        or result["modules_checked"] != "1"
        or result["project_modules"] != "0"
        or result["pstore_checked"] != "1"
        or result["pstore_records"] != "0"
        or result["dmesg_checked"] != "1"
        or result["fatal_lines"] != "0"
        or result["thermal_samples"] != "3"
        or not MIN_THERMAL_ZONES
        <= int(result["thermal_zones"])
        <= MAX_THERMAL_ZONES
        or not 0 <= int(result["thermal_max"]) <= thermal_limit
        or result["python_major"] != "3"
        or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{12}",
            result["boot_id"],
        )
    ):
        stop(nonce, "health")
    return values


def sign(payload):
    metadata = HOST_KEY.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        raise RuntimeError("host-key-metadata")
    result = subprocess.run(
        [
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(HOST_KEY),
            "-n",
            NAMESPACE,
            "-",
        ],
        input=payload,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError("host-key-sign")
    return result.stdout


def encode(values):
    return ("".join(f"{key}={value}\n" for key, value in values)).encode()


def main():
    if len(sys.argv) != 3:
        raise RuntimeError("arguments")
    nonce, action = sys.argv[1:]
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise RuntimeError("nonce")
    if action not in {"classify", "preflight", "reboot"}:
        raise RuntimeError("action")
    values = collect(nonce, action)
    payload = encode(values)
    try:
        signature = sign(payload)
    except Exception:
        stop(nonce, "host-key-sign")
    print("ROG5_FALLBACK_ACM_BEGIN", nonce)
    print(base64.b64encode(payload).decode())
    print(base64.b64encode(signature).decode())
    print("ROG5_FALLBACK_ACM_END", nonce, "PREPARED", flush=True)
    if action != "reboot":
        return
    expected_boot_id = dict(values)["boot_id"]
    ready, _, _ = select.select(
        [sys.stdin],
        [],
        [],
        REBOOT_ACK_TIMEOUT_SECONDS,
    )
    if not ready:
        stop(nonce, "ack-timeout")
    reply = sys.stdin.readline().strip()
    expected = f"ROG5_FALLBACK_REBOOT_ACK {nonce} {expected_boot_id}"
    if reply != expected:
        stop(nonce, "ack")
    post_ack_deadline = time.monotonic() + POST_ACK_DEADLINE_SECONDS
    current = collect(nonce, action)
    if dict(current)["boot_id"] != expected_boot_id:
        stop(nonce, "boot-id-changed")
    if time.monotonic() >= post_ack_deadline:
        stop(nonce, "post-ack-timeout")
    print(
        "ROG5_FALLBACK_ACM_COMMIT",
        nonce,
        expected_boot_id,
        flush=True,
    )
    if time.monotonic() >= post_ack_deadline:
        stop(nonce, "post-ack-timeout")
    restart_bootloader()


def restart_bootloader():
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(
        ctypes.c_long(142),
        ctypes.c_uint(0xFEE1DEAD),
        ctypes.c_uint(672274793),
        ctypes.c_uint(0xA1B2C3D4),
        ctypes.c_char_p(b"bootloader"),
    )
    raise RuntimeError(f"reboot-returned-{result}-{ctypes.get_errno()}")


try:
    main()
except SystemExit:
    raise
except Exception:
    nonce = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    stop(nonce, "probe")
'''


class FallbackError(RuntimeError):
    """A fail-closed fallback control condition."""


def fail(message: str) -> NoReturn:
    raise FallbackError(message)


def fixed_binary(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise FallbackError("fixed host command is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_gid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o755
    ):
        fail("fixed host command metadata is unsafe")


def canonical_private_file(path: Path, label: str) -> Path:
    if not path.is_absolute():
        fail(f"{label} must be absolute")
    try:
        named = path.lstat()
        resolved = path.resolve(strict=True)
        metadata = resolved.lstat()
        parent = path.parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as error:
        raise FallbackError(f"{label} is unavailable") from error
    if (
        path != resolved
        or path.parent != parent
        or stat.S_ISLNK(named.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(parent_metadata.st_mode) != 0o700
    ):
        fail(
            f"{label} must be a canonical mode-0600 file below a "
            "caller-owned mode-0700 directory"
        )
    return resolved


def decode_ed25519(value: str) -> None:
    try:
        blob = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise FallbackError("fallback host key is not canonical base64") from error
    prefix = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
    if (
        len(blob) != len(prefix) + 32
        or not blob.startswith(prefix)
        or blob[-32:] == b"\x00" * 32
    ):
        fail("fallback host key is not one nonzero Ed25519 key")


def verify_known_hosts(path: Path) -> bytes:
    known_hosts = canonical_private_file(path, "fallback host pin")
    if (
        any(character.isspace() for character in str(known_hosts))
        or "%" in str(known_hosts)
    ):
        fail(
            "fallback host pin path must not contain whitespace or "
            "OpenSSH percent tokens"
        )
    try:
        known_hosts.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("fallback host pin must remain outside the repository")
    descriptor = os.open(
        known_hosts,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or not 1 <= metadata.st_size <= 4096
        ):
            fail("fallback host pin changed during inspection")
        payload = os.read(descriptor, 4097)
    finally:
        os.close(descriptor)
    if len(payload) != metadata.st_size:
        fail("fallback host pin changed during inspection")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise FallbackError("fallback host pin is not ASCII") from error
    if len(lines) != 1 or not payload.endswith(b"\n"):
        fail(
            "fallback host pin uses allowed-signers format and must contain "
            "exactly one canonical key"
        )
    fields = lines[0].split()
    if (
        len(fields) != 3
        or fields[0] != HOST_ALIAS
        or fields[1] != "ssh-ed25519"
    ):
        fail(
            "fallback host pin uses allowed-signers format and must be one "
            "exact literal Ed25519 key"
        )
    decode_ed25519(fields[2])
    return payload


def file_identity(path: Path) -> tuple[int, ...]:
    metadata = path.lstat()
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


def verify_ssh_key(path: Path, expected_public_sha256: str) -> Path:
    if (
        not SHA256.fullmatch(expected_public_sha256)
        or expected_public_sha256 == "0" * 64
    ):
        fail("admitted fallback SSH public-key identity is invalid")
    key = canonical_private_file(path, "fallback SSH client key")
    if "%" in str(key):
        fail(
            "fallback SSH client key path must not contain OpenSSH "
            "percent tokens"
        )
    try:
        key.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("fallback SSH client key must remain outside the repository")
    metadata = key.lstat()
    if not 64 <= metadata.st_size <= 4096:
        fail("fallback SSH client key size is outside policy")
    before = file_identity(key)
    descriptor = os.open(
        key,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        result = subprocess.run(
            [
                str(SSH_KEYGEN),
                "-y",
                "-f",
                f"/proc/self/fd/{descriptor}",
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
            env={"LC_ALL": "C"},
            pass_fds=(descriptor,),
        )
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = result.stdout.rstrip(b"\n").split(b" ")
    if (
        result.returncode != 0
        or not result.stdout.endswith(b"\n")
        or result.stdout.count(b"\n") != 1
        or b"\r" in result.stdout
        or len(fields) < 2
        or fields[0] != b"ssh-ed25519"
        or not fields[1]
        or before != file_identity(key)
        or before
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
        fail("fallback SSH client key changed or is not Ed25519")
    canonical_public = b" ".join(fields[:2]) + b"\n"
    if hashlib.sha256(canonical_public).hexdigest() != expected_public_sha256:
        fail("fallback SSH client key no longer matches admission")
    return key


def host_boot_id() -> str:
    try:
        value = HOST_BOOT_ID.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise FallbackError("cannot read the host boot identity") from error
    if not BOOT_ID.fullmatch(value):
        fail("host boot identity is malformed")
    return value


def validate_location(value: str) -> None:
    if (
        not LOCATION.fullmatch(value)
        or value.startswith("/")
        or ".." in Path(value).parts
    ):
        fail("USB physical location is invalid")


def read_anchor(path: Path) -> str:
    anchor = canonical_private_file(path, "recovery USB anchor")
    parent = anchor.parent
    metadata = parent.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail("recovery USB anchor parent is unsafe")
    try:
        anchor.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("recovery USB anchor must remain outside the repository")
    payload = anchor.read_bytes()
    if len(payload) > 4096:
        fail("recovery USB anchor exceeds its bound")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise FallbackError("recovery USB anchor is not ASCII") from error
    if len(lines) != len(ANCHOR_FIELDS) or not payload.endswith(b"\n"):
        fail("recovery USB anchor field count changed")
    values: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(ANCHOR_FIELDS, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected or not value:
            fail("recovery USB anchor is not canonical")
        values[key] = value
    if (
        values["format"] != "rog5-minimal-headless-usb-anchor-v1"
        or values["host_boot_id"] != host_boot_id()
        or values["recovery_vendor"] != USB_VENDOR
        or values["recovery_product_id"] != USB_PRODUCT
        or values["recovery_product"] != RECOVERY_PRODUCT_NAME
    ):
        fail("recovery USB anchor identity changed")
    created = values["created_unix"]
    if (
        not created.isascii()
        or not created.isdecimal()
        or created.startswith("0")
    ):
        fail("recovery USB anchor time is not canonical")
    now = int(time.time())
    if int(created) > now + 5 or now - int(created) > ANCHOR_MAX_AGE_SECONDS:
        fail("recovery USB anchor is stale")
    validate_location(values["usb_location"])
    return values["usb_location"]


def read_small(path: Path, maximum: int) -> str:
    try:
        metadata = path.lstat()
        payload = path.read_bytes()
    except OSError as error:
        raise FallbackError("USB identity file is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or len(payload) < 1
        or len(payload) > maximum
    ):
        fail("USB identity file is unsafe")
    try:
        return payload.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise FallbackError("USB identity file is not text") from error


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
        markers = (
            candidate / "idVendor",
            candidate / "idProduct",
            candidate / "product",
        )
        if not all(marker.exists() for marker in markers):
            continue
        try:
            vendor = read_small(markers[0], 16)
            product_id = read_small(markers[1], 16)
            product = read_small(markers[2], 128)
            location = candidate.relative_to(SYS_DEVICES).as_posix()
        except (FallbackError, ValueError):
            continue
        validate_location(location)
        return candidate, vendor, product_id, product
    return None


def udev_properties(device: str) -> dict[str, str]:
    result = subprocess.run(
        [str(UDEVADM), "info", "--query=property", f"--name={device}"],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
        env={"LC_ALL": "C"},
    )
    if result.returncode != 0:
        fail("cannot inspect fallback ACM identity")
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator == "=" and key:
            properties[key] = value
    return properties


def fallback_raw_locations() -> set[str]:
    raw_locations: set[str] = set()
    for entry in sorted(SYS_BUS_USB.iterdir()):
        observed = usb_ancestor(entry)
        if observed is None:
            continue
        device, vendor, product_id, product = observed
        if (
            vendor == USB_VENDOR
            and product_id == USB_PRODUCT
            and product == USB_PRODUCT_NAME
        ):
            raw_locations.add(device.relative_to(SYS_DEVICES).as_posix())
    return raw_locations


def fallback_acm_identity(device: str) -> tuple[str, str, int] | None:
    try:
        metadata = os.stat(device, follow_symlinks=False)
        properties = udev_properties(device)
        observed = usb_ancestor(SYS_CLASS_TTY / Path(device).name)
    except (OSError, FallbackError, subprocess.SubprocessError):
        return None
    if observed is None or not stat.S_ISCHR(metadata.st_mode):
        return None
    raw, vendor, product_id, product = observed
    location = raw.relative_to(SYS_DEVICES).as_posix()
    if (
        vendor != USB_VENDOR
        or product_id != USB_PRODUCT
        or product != USB_PRODUCT_NAME
        or properties.get("ID_VENDOR_ID") != USB_VENDOR
        or properties.get("ID_MODEL_ID") != USB_PRODUCT
        or properties.get("ID_MODEL") != USB_MODEL
        or properties.get("ID_USB_DRIVER") != USB_DRIVER
        or properties.get("ID_USB_INTERFACE_NUM") != USB_INTERFACE
        or not os.access(device, os.R_OK | os.W_OK)
    ):
        return None
    return device, location, metadata.st_rdev


def find_fallback_acm(
    expected_location: str | None = None,
) -> tuple[str, str, int]:
    raw_locations = fallback_raw_locations()
    matches: list[tuple[str, str, int]] = []
    for device in sorted(glob.glob("/dev/ttyACM*")):
        identity = fallback_acm_identity(device)
        if identity is not None:
            matches.append(identity)
    if len(raw_locations) != 1 or len(matches) != 1:
        fail(
            "expected exactly one Alpine fallback USB product and ACM "
            f"interface, found products={len(raw_locations)} acm={len(matches)}"
        )
    if matches[0][1] not in raw_locations:
        fail("fallback ACM escaped the exact USB product")
    if expected_location is not None and matches[0][1] != expected_location:
        fail("fallback returned on a different physical USB port")
    return matches[0]


def revalidate_fallback_acm(
    path: str,
    location: str,
    device_number: int,
) -> None:
    if (
        fallback_raw_locations() != {location}
        or fallback_acm_identity(path) != (path, location, device_number)
    ):
        fail("fallback USB identity changed after signed preflight")


def wait_fallback_acm(
    expected_location: str | None,
    timeout_seconds: int,
) -> tuple[str, str, int]:
    deadline = time.monotonic() + timeout_seconds
    candidate: tuple[str, str, int] | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        try:
            identity = find_fallback_acm(expected_location)
        except (OSError, FallbackError):
            candidate = None
            stable_since = 0.0
        else:
            now = time.monotonic()
            if identity != candidate:
                candidate = identity
                stable_since = now
            elif now - stable_since >= 0.5:
                return identity
        time.sleep(0.1)
    fail("exact Alpine fallback ACM did not become stable")


def fallback_ncm_identity() -> tuple[str, str] | None:
    matches: list[tuple[str, str]] = []
    try:
        entries = sorted(SYS_CLASS_NET.iterdir())
    except OSError:
        return None
    for entry in entries:
        observed = usb_ancestor(entry)
        if observed is None:
            continue
        raw, vendor, product_id, product = observed
        if (
            vendor != USB_VENDOR
            or product_id != USB_PRODUCT
            or product != USB_PRODUCT_NAME
        ):
            continue
        result = subprocess.run(
            [
                str(UDEVADM),
                "info",
                "--query=property",
                f"--path={entry}",
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            env={"LC_ALL": "C"},
        )
        properties: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            if separator == "=" and key and key not in properties:
                properties[key] = value
        try:
            driver = (entry / "device" / "driver").resolve(strict=True).name
        except OSError:
            continue
        if (
            result.returncode != 0
            or properties.get("ID_VENDOR_ID") != USB_VENDOR
            or properties.get("ID_MODEL_ID") != USB_PRODUCT
            or properties.get("ID_MODEL") != USB_MODEL
            or properties.get("ID_USB_DRIVER") != USB_NCM_DRIVER
            or properties.get("ID_USB_INTERFACE_NUM")
            != USB_NCM_INTERFACE
            or driver != USB_NCM_DRIVER
        ):
            continue
        matches.append(
            (entry.name, raw.relative_to(SYS_DEVICES).as_posix())
        )
    raw_locations = fallback_raw_locations()
    if len(raw_locations) != 1 or len(matches) != 1:
        return None
    if matches[0][1] not in raw_locations:
        fail("fallback NCM escaped the exact USB product")
    return matches[0]


def wait_fallback_ncm(
    expected_location: str,
    timeout_seconds: int,
) -> tuple[str, str]:
    deadline = time.monotonic() + timeout_seconds
    candidate: tuple[str, str] | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        current = fallback_ncm_identity()
        if current is None:
            candidate = None
            stable_since = 0.0
        elif current[1] != expected_location:
            fail("fallback returned on a different physical USB port")
        else:
            now = time.monotonic()
            if current != candidate:
                candidate = current
                stable_since = now
            elif now - stable_since >= 0.5:
                return current
        time.sleep(0.1)
    fail("exact Alpine fallback NCM did not become stable")


def exact_fallback_route(interface: str) -> None:
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
    cidrs = [
        fields[3]
        for line in address.stdout.splitlines()
        if (fields := line.split()) and len(fields) >= 4
        and fields[2] == "inet"
    ]
    if address.returncode != 0 or cidrs != [HOST_CIDR]:
        fail("fallback NCM lacks the exact host /16 address")
    route = subprocess.run(
        [str(IP), "-4", "route", "get", FALLBACK_ADDRESS],
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
        fail("fallback route is unavailable")
    fields = raw_lines[0].split()
    if (
        not fields
        or fields[0] != FALLBACK_ADDRESS
        or fields.count("dev") != 1
        or fields.count("src") != 1
        or "via" in fields
        or "table" in fields
    ):
        fail("fallback route is not exact and direct")
    try:
        device = fields[fields.index("dev") + 1]
        source = fields[fields.index("src") + 1]
    except IndexError as error:
        raise FallbackError("fallback route is incomplete") from error
    if device != interface or source != HOST_ADDRESS:
        fail("fallback route escaped the exact NCM interface")
    default_route = subprocess.run(
        [str(IP), "-4", "route", "show", "default", "dev", interface],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
        env={"LC_ALL": "C"},
    )
    if default_route.returncode != 0 or default_route.stdout.splitlines():
        fail("fallback NCM interface must not carry a default route")


def verify_network_profile(expected_interface: str | None = None) -> str:
    result = subprocess.run(
        [
            str(NMCLI),
            "-g",
            "connection.id,connection.type,connection.interface-name,"
            "connection.autoconnect,connection.autoconnect-priority,"
            "ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns,"
            "ipv4.never-default,ipv6.method",
            "connection",
            "show",
            FALLBACK_NETWORK_PROFILE,
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=8,
        env={"LC_ALL": "C"},
    )
    values = result.stdout.splitlines()
    if result.returncode != 0 or len(values) != 11:
        fail("fallback NetworkManager profile is unavailable or malformed")
    interface = values[2]
    if (
        values
        != [
            FALLBACK_NETWORK_PROFILE,
            "802-3-ethernet",
            interface,
            "yes",
            "100",
            "manual",
            HOST_CIDR,
            "",
            "",
            "yes",
            "disabled",
        ]
        or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", interface)
        or (
            expected_interface is not None
            and interface != expected_interface
        )
    ):
        fail("fallback NetworkManager profile is not exact and no-gateway")
    return interface


def remote_transport(nonce: str, action: str) -> tuple[bytes, tuple[bytes, ...]]:
    if not NONCE.fullmatch(nonce) or action not in {
        "classify",
        "preflight",
        "reboot",
    }:
        fail("invalid fallback loader request")
    compressed = zlib.compress(REMOTE_SOURCE.encode("utf-8"), level=9)
    encoded = base64.b64encode(compressed)
    chunks = tuple(
        encoded[offset : offset + SOURCE_CHUNK_BYTES] + b"\n"
        for offset in range(0, len(encoded), SOURCE_CHUNK_BYTES)
    )
    encoded_sha256 = hashlib.sha256(encoded).hexdigest()
    loader = base64.b64encode(
        zlib.compress(LOADER_SOURCE.encode("utf-8"), level=9)
    ).decode("ascii")
    launcher = (
        " /bin/busybox env -i "
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "
        "HOME=/root PYTHONDONTWRITEBYTECODE=1 "
        "/usr/bin/python3 -I -S -B -c 'import base64,zlib;"
        f"exec(zlib.decompress(base64.b64decode(\"{loader}\")))' "
        f"{len(chunks)} {len(encoded)} {encoded_sha256} {nonce} {action} "
        f"{LOADER_RECEIVE_TIMEOUT_SECONDS}\n"
    )
    command = launcher.encode("ascii")
    if (
        len(command) > MAX_LAUNCHER_LINE_BYTES
        or MAX_LAUNCHER_LINE_BYTES >= BUSYBOX_EDITING_MAX_LEN
        or not chunks
        or len(chunks) > MAX_SOURCE_CHUNKS
        or any(
            len(chunk) > SOURCE_CHUNK_BYTES + 1
            or not chunk.endswith(b"\n")
            for chunk in chunks
        )
    ):
        fail("fixed fallback loader transport exceeds its bound")
    return command, chunks


def shell_sync_transport(nonce: str) -> tuple[bytes, bytes, str]:
    if not NONCE.fullmatch(nonce):
        fail("invalid fallback shell synchronization request")
    marker = f"ROG5_FALLBACK_SHELL_READY {nonce}"
    reset = b"\x03\n"
    command = (
        " /bin/busybox printf 'ROG5_FALLBACK_SHELL_%s %s\\n' "
        f"READY {nonce}\n"
    ).encode("ascii")
    if (
        len(command) > 256
        or marker.encode("ascii") in reset + command
    ):
        fail("fallback shell synchronization transport exceeds its bound")
    return reset, command, marker


def sanitize(data: bytes) -> list[str]:
    clean = CSI.sub(b"", data).replace(b"\x1b", b"")
    try:
        return clean.decode("ascii").replace("\r", "").splitlines()
    except UnicodeDecodeError as error:
        raise FallbackError("fallback ACM output is not ASCII") from error


def remote_error(output: bytes, nonce: str) -> str | None:
    lines = sanitize(output)
    prefix = "ROG5_FALLBACK_ACM_ERROR "
    errors = [line for line in lines if line.startswith(prefix)]
    if not errors:
        return None
    expected_prefix = f"{prefix}{nonce} "
    if (
        len(errors) != 1
        or not errors[0].startswith(expected_prefix)
        or errors[0][len(expected_prefix) :] not in REMOTE_ERROR_CODES
    ):
        fail("fallback ACM remote error frame is malformed or ambiguous")
    return errors[0][len(expected_prefix) :]


class FallbackSerial:
    def __init__(self, path: str, location: str, device_number: int):
        self.path = path
        self.location = location
        self.device_number = device_number
        self.fd = -1
        self.output = bytearray()

    def __enter__(self) -> "FallbackSerial":
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC
        self.fd = os.open(self.path, flags)
        try:
            metadata = os.fstat(self.fd)
            if (
                not stat.S_ISCHR(metadata.st_mode)
                or metadata.st_rdev != self.device_number
            ):
                fail("opened fallback ACM identity changed")
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.ioctl(self.fd, termios.TIOCEXCL)
            tty.setraw(self.fd, termios.TCSANOW)
            attributes = termios.tcgetattr(self.fd)
            attributes[0] &= ~(
                termios.IXON | termios.IXOFF | termios.ICRNL | termios.INLCR
            )
            attributes[1] &= ~termios.OPOST
            attributes[2] |= termios.CLOCAL | termios.CREAD
            attributes[4] = termios.B115200
            attributes[5] = termios.B115200
            attributes[6][termios.VMIN] = 0
            attributes[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
            termios.tcflush(self.fd, termios.TCIFLUSH)
            result = subprocess.run(
                [str(FUSER), self.path],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
                env={"LC_ALL": "C"},
            )
            holders = {
                int(value)
                for value in result.stdout.split()
                if value.isascii() and value.isdecimal()
            }
            if result.returncode != 0 or holders != {os.getpid()}:
                fail("fallback ACM already has another open holder")
        except BaseException:
            os.close(self.fd)
            self.fd = -1
            raise
        return self

    def __exit__(self, *_: object) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def write(
        self,
        payload: bytes,
        timeout_seconds: float = 5.0,
        stage: str = "payload",
    ) -> None:
        if not stage.isascii() or not re.fullmatch(r"[a-z0-9-]{1,32}", stage):
            fail("fallback ACM write stage is invalid")
        total = len(payload)
        view = memoryview(payload)
        deadline = time.monotonic() + timeout_seconds
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                fail(
                    f"fallback ACM {stage} write timed out "
                    f"after {total - len(view)}/{total} bytes"
                )
            readable, writable, _ = select.select(
                [self.fd],
                [self.fd],
                [],
                remaining,
            )
            if not readable and not writable:
                fail(
                    f"fallback ACM {stage} write timed out "
                    f"after {total - len(view)}/{total} bytes"
                )
            if readable:
                try:
                    chunk = os.read(self.fd, 4096)
                except OSError as error:
                    if error.errno not in {
                        errno.EAGAIN,
                        errno.EWOULDBLOCK,
                        errno.EINTR,
                    }:
                        if error.errno == errno.EIO:
                            fail(
                                "fallback ACM disconnected during write"
                            )
                        raise
                else:
                    if not chunk:
                        fail("fallback ACM closed during write")
                    self.output.extend(chunk)
                    if len(self.output) > MAX_SERIAL_OUTPUT:
                        fail("fallback ACM output exceeds its bound")
            if not writable:
                continue
            try:
                written = os.write(self.fd, view[:256])
            except OSError as error:
                if error.errno in {
                    errno.EAGAIN,
                    errno.EWOULDBLOCK,
                    errno.EINTR,
                }:
                    continue
                raise
            if written <= 0:
                fail("fallback ACM write made no progress")
            view = view[written:]

    def read_until(
        self,
        expected_line: str,
        timeout_seconds: float,
        remote_nonce: str | None = None,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if remote_nonce is not None:
                code = remote_error(bytes(self.output), remote_nonce)
                if code is not None:
                    fail(f"fallback remote probe failed: {code}")
            if expected_line in sanitize(bytes(self.output)):
                return
            ready, _, _ = select.select([self.fd], [], [], 0.25)
            if not ready:
                continue
            try:
                chunk = os.read(self.fd, 4096)
            except OSError as error:
                if error.errno == errno.EIO:
                    fail("fallback ACM disconnected before the signed result")
                raise
            if not chunk:
                fail("fallback ACM closed before the signed result")
            self.output.extend(chunk)
            if len(self.output) > MAX_SERIAL_OUTPUT:
                fail("fallback ACM output exceeds its bound")
        if remote_nonce is not None:
            code = remote_error(bytes(self.output), remote_nonce)
            if code is not None:
                fail(f"fallback remote probe failed: {code}")
        fail("fallback ACM signed result timed out")

    def wait_disconnect(
        self,
        timeout_seconds: float,
        remote_nonce: str | None = None,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if remote_nonce is not None:
                code = remote_error(bytes(self.output), remote_nonce)
                if code is not None:
                    fail(f"fallback remote probe failed: {code}")
            ready, _, _ = select.select([self.fd], [], [], 0.25)
            if not ready:
                continue
            try:
                chunk = os.read(self.fd, 4096)
            except OSError as error:
                if error.errno == errno.EIO:
                    return
                raise
            if not chunk:
                return
            self.output.extend(chunk)
            if len(self.output) > MAX_SERIAL_OUTPUT:
                fail("fallback ACM output exceeds its bound")
        if remote_nonce is not None:
            code = remote_error(bytes(self.output), remote_nonce)
            if code is not None:
                fail(f"fallback remote probe failed: {code}")
        fail("fallback ACM remained present after the reboot commit")


def parse_record(payload: bytes, nonce: str, action: str) -> OrderedDict[str, str]:
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise FallbackError("fallback signed record is not ASCII") from error
    if len(lines) != len(RESULT_FIELDS) or not payload.endswith(b"\n"):
        fail("fallback signed record field count changed")
    values: OrderedDict[str, str] = OrderedDict()
    for expected, line in zip(RESULT_FIELDS, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected or not value:
            fail("fallback signed record is not canonical")
        values[key] = value
    if payload != "".join(
        f"{key}={value}\n" for key, value in values.items()
    ).encode("ascii"):
        fail("fallback signed record encoding changed")
    exact = {
        "format": FORMAT,
        "nonce": nonce,
        "action": action,
        "kernel_release": FALLBACK_KERNEL,
        "init": "/bin/busybox",
        "compatible": "qcom,lahaina-mtp",
        "root_fstype": "ext4",
        "modules_checked": "1",
        "project_modules": "0",
        "pstore_checked": "1",
        "pstore_records": "0",
        "dmesg_checked": "1",
        "fatal_lines": "0",
        "thermal_samples": "3",
        "python_major": "3",
        "result": "PASS",
    }
    if any(values[key] != value for key, value in exact.items()):
        fail("fallback signed health result changed")
    for field in ("thermal_zones", "thermal_max"):
        if not values[field].isascii() or not values[field].isdecimal():
            fail("fallback thermal result is malformed")
    thermal_limit = (
        MAX_RETURN_THERMAL
        if action == "classify"
        else MAX_PREFLIGHT_THERMAL
    )
    if (
        not MIN_THERMAL_ZONES
        <= int(values["thermal_zones"])
        <= MAX_THERMAL_ZONES
        or not 0 <= int(values["thermal_max"]) <= thermal_limit
        or not BOOT_ID.fullmatch(values["boot_id"])
    ):
        fail("fallback signed runtime result is unsafe")
    return values


def parse_frame(
    output: bytes,
    nonce: str,
    action: str,
) -> tuple[OrderedDict[str, str], bytes, bytes]:
    lines = sanitize(output)
    begin = f"ROG5_FALLBACK_ACM_BEGIN {nonce}"
    end = f"ROG5_FALLBACK_ACM_END {nonce} PREPARED"
    if lines.count(begin) != 1 or lines.count(end) != 1:
        fail("fallback ACM did not return exactly one correlated frame")
    first = lines.index(begin)
    last = lines.index(end)
    if last != first + 3:
        fail("fallback ACM frame structure changed")
    try:
        payload = base64.b64decode(lines[first + 1], validate=True)
        signature = base64.b64decode(lines[first + 2], validate=True)
    except (binascii.Error, ValueError) as error:
        raise FallbackError("fallback ACM frame is not canonical base64") from error
    values = parse_record(payload, nonce, action)
    return values, payload, signature


def verify_signature(
    allowed_signers: bytes,
    payload: bytes,
    signature: bytes,
) -> None:
    fixed_binary(SSH_KEYGEN)
    if not signature or len(signature) > 4096:
        fail("fallback host signature is outside its bound")
    pin_descriptor = os.memfd_create(
        "rog5-fallback-allowed-signers",
        os.MFD_CLOEXEC,
    )
    signature_descriptor = os.memfd_create(
        "rog5-fallback-signature",
        os.MFD_CLOEXEC,
    )
    try:
        for descriptor, source in (
            (pin_descriptor, allowed_signers),
            (signature_descriptor, signature),
        ):
            view = memoryview(source)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    fail("fallback verifier input write made no progress")
                view = view[written:]
            os.lseek(descriptor, 0, os.SEEK_SET)
        result = subprocess.run(
            [
                str(SSH_KEYGEN),
                "-Y",
                "verify",
                "-f",
                f"/proc/self/fd/{pin_descriptor}",
                "-I",
                HOST_ALIAS,
                "-n",
                SIGN_NAMESPACE,
                "-s",
                f"/proc/self/fd/{signature_descriptor}",
            ],
            input=payload,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            pass_fds=(pin_descriptor, signature_descriptor),
        )
    finally:
        os.close(pin_descriptor)
        os.close(signature_descriptor)
    if result.returncode != 0:
        fail("fallback ACM result lacks the pinned host-key signature")


def probe(
    allowed_signers: bytes,
    *,
    action: str,
    expected_location: str | None = None,
    anchor_path: Path | None = None,
    timeout_seconds: int = 12,
) -> tuple[OrderedDict[str, str], str, OrderedDict[str, str]]:
    nonce = os.urandom(16).hex()
    if not NONCE.fullmatch(nonce) or nonce == ZERO_ID:
        fail("cannot mint one fallback challenge")
    path, location, device_number = wait_fallback_acm(
        expected_location,
        timeout_seconds,
    )
    if anchor_path is not None:
        refreshed_location = read_anchor(anchor_path)
        if refreshed_location != location:
            fail("recovery USB anchor changed after fallback discovery")
    with FallbackSerial(path, location, device_number) as serial:
        reset, sync_command, shell_ready = shell_sync_transport(nonce)
        serial.write(reset + sync_command, stage="shell-sync")
        serial.read_until(shell_ready, SHELL_READY_TIMEOUT_SECONDS)
        if sanitize(bytes(serial.output)).count(shell_ready) != 1:
            fail("fallback shell readiness marker is absent or ambiguous")
        launcher, source_chunks = remote_transport(nonce, action)
        serial.write(launcher, stage="loader-launcher")
        loader_ready = f"ROG5_FALLBACK_LOADER_READY {nonce}"
        serial.read_until(loader_ready, LOADER_READY_TIMEOUT_SECONDS)
        if sanitize(bytes(serial.output)).count(loader_ready) != 1:
            fail("fallback loader readiness marker is absent or ambiguous")
        for index, source_chunk in enumerate(source_chunks, start=1):
            serial.write(source_chunk, stage=f"source-{index}")
        end = f"ROG5_FALLBACK_ACM_END {nonce} PREPARED"
        serial.read_until(
            end,
            PREPARED_FRAME_TIMEOUT_SECONDS,
            remote_nonce=nonce,
        )
        if sanitize(bytes(serial.output)).count(shell_ready) != 1:
            fail("fallback shell readiness marker is absent or ambiguous")
        values, payload, signature = parse_frame(
            bytes(serial.output),
            nonce,
            action,
        )
        verify_signature(allowed_signers, payload, signature)
        proof = OrderedDict(
            (
                ("nonce", values["nonce"]),
                ("usb_location", location),
                ("thermal_max", values["thermal_max"]),
                ("record_sha256", hashlib.sha256(payload).hexdigest()),
                (
                    "signature_sha256",
                    hashlib.sha256(signature).hexdigest(),
                ),
                (
                    "host_pin_sha256",
                    hashlib.sha256(allowed_signers).hexdigest(),
                ),
            )
        )
        revalidate_fallback_acm(path, location, device_number)
        if action == "reboot":
            boot_id = values["boot_id"]
            serial.write(
                (
                    f"ROG5_FALLBACK_REBOOT_ACK {nonce} {boot_id}\n"
                ).encode("ascii"),
                stage="reboot-ack",
            )
            commit = f"ROG5_FALLBACK_ACM_COMMIT {nonce} {boot_id}"
            serial.read_until(
                commit,
                REBOOT_COMMIT_TIMEOUT_SECONDS,
                remote_nonce=nonce,
            )
            if sanitize(bytes(serial.output)).count(commit) != 1:
                fail("fallback reboot commit marker is absent or ambiguous")
            serial.wait_disconnect(20, remote_nonce=nonce)
        return values, location, proof


def ssh_probe(
    known_hosts: Path,
    allowed_signers: bytes,
    ssh_key: Path,
    expected_public_sha256: str,
    anchor_path: Path,
    timeout_seconds: int,
) -> tuple[OrderedDict[str, str], OrderedDict[str, str]]:
    expected_location = read_anchor(anchor_path)
    interface, location = wait_fallback_ncm(
        expected_location,
        timeout_seconds,
    )
    verify_network_profile(interface)
    exact_fallback_route(interface)
    nonce = os.urandom(16).hex()
    if not NONCE.fullmatch(nonce) or nonce == ZERO_ID:
        fail("cannot mint one fallback SSH challenge")
    host_pin_identity = file_identity(known_hosts)
    key_identity = file_identity(ssh_key)
    command = [
        str(SSH),
        "-F",
        "/dev/null",
        "-i",
        str(ssh_key),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        f"HostKeyAlias={HOST_ALIAS}",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=2",
        "-o",
        "LogLevel=ERROR",
        f"root@{FALLBACK_ADDRESS}",
        "/usr/bin/python3",
        "-I",
        "-S",
        "-B",
        "-",
        nonce,
        "classify",
    ]
    result = subprocess.run(
        command,
        input=REMOTE_SOURCE.encode("utf-8"),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    if (
        file_identity(known_hosts) != host_pin_identity
        or verify_known_hosts(known_hosts) != allowed_signers
        or file_identity(ssh_key) != key_identity
        or verify_ssh_key(ssh_key, expected_public_sha256) != ssh_key
    ):
        fail("fallback SSH credentials changed during the health probe")
    if (
        result.returncode != 0
        or result.stderr
        or len(result.stdout) > MAX_SERIAL_OUTPUT
    ):
        diagnostic = ascii(
            result.stderr.decode("utf-8", errors="replace").strip()[:512]
        )
        fail(
            "fallback strict SSH health probe failed "
            f"status={result.returncode} stderr={diagnostic}"
        )
    values, payload, signature = parse_frame(
        result.stdout,
        nonce,
        "classify",
    )
    verify_signature(allowed_signers, payload, signature)
    if fallback_ncm_identity() != (interface, location):
        fail("fallback NCM identity changed after strict SSH proof")
    exact_fallback_route(interface)
    if read_anchor(anchor_path) != location:
        fail("recovery USB anchor changed after strict SSH proof")
    proof = OrderedDict(
        (
            ("nonce", values["nonce"]),
            ("usb_location", location),
            ("thermal_max", values["thermal_max"]),
            ("record_sha256", hashlib.sha256(payload).hexdigest()),
            (
                "signature_sha256",
                hashlib.sha256(signature).hexdigest(),
            ),
            (
                "host_pin_sha256",
                hashlib.sha256(allowed_signers).hexdigest(),
            ),
        )
    )
    return values, proof


def safe_new_output(path: Path) -> Path:
    if not path.is_absolute():
        fail("fallback evidence output must be absolute")
    try:
        parent = path.parent.resolve(strict=True)
        metadata = parent.lstat()
    except OSError as error:
        raise FallbackError("fallback evidence parent is unavailable") from error
    if (
        path.parent != parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or path.exists()
        or path.is_symlink()
    ):
        fail("fallback evidence output is unsafe or already exists")
    try:
        path.relative_to(REPO)
    except ValueError:
        return path
    fail("fallback evidence must remain outside the repository")


def write_identity(
    path: Path,
    values: OrderedDict[str, str],
    proof: OrderedDict[str, str],
) -> None:
    destination = safe_new_output(path)
    payload = (
        f"format={IDENTITY_FORMAT}\n"
        f"kernel_release={FALLBACK_KERNEL}\n"
        f"boot_id={values['boot_id']}\n"
        f"usb_location={proof['usb_location']}\n"
        f"nonce={proof['nonce']}\n"
        f"thermal_max={proof['thermal_max']}\n"
        f"record_sha256={proof['record_sha256']}\n"
        f"signature_sha256={proof['signature_sha256']}\n"
        f"host_pin_sha256={proof['host_pin_sha256']}\n"
        "result=PASS\n"
    ).encode("ascii")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    descriptor = os.open(destination, flags, 0o600)
    succeeded = False
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                fail("fallback identity write made no progress")
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
            fail("fallback identity output metadata is unsafe")
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


def require_fastboot_usb(location: str, serial: str) -> None:
    raw = SYS_DEVICES / location
    if (
        not raw.is_dir()
        or read_small(raw / "idVendor", 16) != FASTBOOT_VENDOR
        or read_small(raw / "idProduct", 16) != FASTBOOT_PRODUCT
        or read_small(raw / "serial", 128) != serial
    ):
        fail("fastboot escaped the exact fallback USB device")
    locations: set[str] = set()
    for entry in sorted(SYS_BUS_USB.iterdir()):
        observed = usb_ancestor(entry)
        if observed is None:
            continue
        device, vendor, product_id, _ = observed
        if vendor != FASTBOOT_VENDOR or product_id != FASTBOOT_PRODUCT:
            continue
        try:
            candidate_serial = read_small(device / "serial", 128)
            candidate_location = device.relative_to(SYS_DEVICES).as_posix()
        except (FallbackError, ValueError):
            continue
        if candidate_serial == serial:
            locations.add(candidate_location)
    if locations != {location}:
        fail("fastboot serial is not unique at the expected physical port")


def anchored_usb_identity(location: str) -> tuple[str, str] | None:
    """Best-effort VID:PID observation at the pinned physical port."""
    validate_location(location)
    raw = SYS_DEVICES / location
    try:
        vendor = read_small(raw / "idVendor", 16).lower()
        product_id = read_small(raw / "idProduct", 16).lower()
    except (FallbackError, OSError):
        # Hotplug may remove or replace this node between either read. This
        # observation only improves a fatal timeout diagnostic; exact
        # fastboot admission remains in require_fastboot_usb().
        return None
    if not re.fullmatch(r"[0-9a-f]{4}", vendor) or not re.fullmatch(
        r"[0-9a-f]{4}", product_id
    ):
        return None
    return vendor, product_id


def fail_fastboot_timeout(
    location: str,
    saw_disconnect: bool,
    reenumerated: set[tuple[str, str]],
) -> NoReturn:
    current = anchored_usb_identity(location)
    if not saw_disconnect:
        fail(
            "fallback USB never disconnected after the acknowledged "
            "bootloader reboot"
        )
    if current is None and not reenumerated:
        fail(
            "fallback USB disconnected but no anchored-port USB "
            "re-enumeration was observed"
        )
    fastboot_identity = (FASTBOOT_VENDOR, FASTBOOT_PRODUCT)
    if current == fastboot_identity or fastboot_identity in reenumerated:
        fail(
            "exact fastboot USB re-enumerated but fastboot userspace "
            "discovery did not succeed"
        )
    fail("a non-fastboot USB mode was observed at the anchored port")


def wait_fastboot(location: str, timeout_seconds: int = 45) -> None:
    fixed_binary(FASTBOOT)
    deadline = time.monotonic() + timeout_seconds
    initial_identity = anchored_usb_identity(location)
    fallback_identity = (USB_VENDOR, USB_PRODUCT)
    saw_disconnect = initial_identity != fallback_identity
    reenumerated: set[tuple[str, str]] = set()
    if saw_disconnect and initial_identity is not None:
        reenumerated.add(initial_identity)
    while time.monotonic() < deadline:
        identity = anchored_usb_identity(location)
        if identity is None:
            saw_disconnect = True
        elif saw_disconnect:
            reenumerated.add(identity)
        result = subprocess.run(
            [str(FASTBOOT), "devices"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            env={"LC_ALL": "C"},
        )
        devices = [
            line.split()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        if any(len(fields) != 2 for fields in devices):
            fail("fastboot returned a malformed device inventory")
        if len(devices) > 1:
            fail("more than one fastboot device appeared")
        if result.returncode == 0 and len(devices) == 1:
            serial, state = devices[0]
            if state != "fastboot":
                fail("USB device reached an unexpected fastboot state")
            require_fastboot_usb(location, serial)
            product = subprocess.run(
                [str(FASTBOOT), "-s", serial, "getvar", "product"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=8,
                env={"LC_ALL": "C"},
            )
            values = re.findall(
                r"(?:^|\n)(?:\(bootloader\)\s*)?product:\s*(\S+)",
                product.stdout,
            )
            if product.returncode != 0 or values != ["lahaina"]:
                fail("fastboot product is not exactly lahaina")
            require_fastboot_usb(location, serial)
            return
        time.sleep(0.25)
    fail_fastboot_timeout(location, saw_disconnect, reenumerated)


def require_guards(action: str) -> None:
    ssh_action = action in {"ssh-host-preflight", "wait-ssh-preflight"}
    guard = (
        "ALLOW_FALLBACK_SSH_CONTROL"
        if ssh_action
        else "ALLOW_FALLBACK_ACM_CONTROL"
    )
    if os.environ.get(guard) != "1":
        fail(f"set {guard}=1 for one fixed fallback action")
    if os.environ.get("ALLOW_PHONE_CREDENTIAL_USE") != "1":
        fail(
            "set ALLOW_PHONE_CREDENTIAL_USE=1 for one host-key-signed "
            "fallback action"
        )
    if (
        not ssh_action
        and action != "host-preflight"
        and os.environ.get("ALLOW_FALLBACK_ACM_STORAGE_WRITE") != "1"
    ):
        fail(
            "set ALLOW_FALLBACK_ACM_STORAGE_WRITE=1 to authorize one "
            "fallback ACM action's shell-history and possible atime writes"
        )
    if (
        ssh_action
        and action != "ssh-host-preflight"
        and os.environ.get("ALLOW_FALLBACK_SSH_ATIME_EFFECTS") != "1"
    ):
        fail(
            "set ALLOW_FALLBACK_SSH_ATIME_EFFECTS=1 for one strict-SSH "
            "probe's possible read-induced atime effects"
        )
    if (
        action == "reboot"
        and os.environ.get("ALLOW_FALLBACK_BOOTLOADER_REBOOT") != "1"
    ):
        fail(
            "set ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 for one guarded reboot"
        )


def require_modem_manager_inactive() -> None:
    result = subprocess.run(
        [
            str(SYSTEMCTL),
            "show",
            "ModemManager.service",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
        ],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
        env={"LC_ALL": "C"},
    )
    if result.returncode != 0 or result.stdout.splitlines() not in (
        [
            "LoadState=loaded",
            "ActiveState=inactive",
            "SubState=dead",
        ],
        [
            "LoadState=not-found",
            "ActiveState=inactive",
            "SubState=dead",
        ],
    ):
        fail("ModemManager state is not exactly inactive")


def require_fastboot_absent() -> None:
    fixed_binary(FASTBOOT)
    result = subprocess.run(
        [str(FASTBOOT), "devices"],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=5,
        env={"LC_ALL": "C"},
    )
    if result.returncode != 0 or result.stdout.split():
        fail("reboot requires a canonical empty initial fastboot inventory")


def parse_wait_timeout(value: str, minimum: int = 600) -> int:
    if minimum not in {1, 600}:
        fail("internal fallback wait-timeout policy is invalid")
    if (
        not value.isascii()
        or not value.isdecimal()
        or not minimum <= int(value) <= 900
    ):
        fail(
            "fallback wait timeout must be between "
            f"{minimum} and 900 seconds"
        )
    return int(value)


def require_anchor_budget(value: str, wait_timeout: int) -> None:
    if (
        not value.isascii()
        or not value.isdecimal()
        or int(value) < 1
        or int(value) + wait_timeout >= ANCHOR_MAX_AGE_SECONDS
    ):
        fail(
            "fallback contact-start budget plus wait timeout must remain "
            "below the recovery anchor age bound"
        )


def main(arguments: list[str]) -> int:
    action = arguments[0] if arguments else ""
    if action not in {
        "host-preflight",
        "ssh-host-preflight",
        "preflight",
        "wait-preflight",
        "wait-ssh-preflight",
        "reboot",
    }:
        fail(
            "usage: fallback-acm-control.py "
            "host-preflight KNOWN_HOSTS TIMEOUT CONTACT_START_BUDGET | "
            "ssh-host-preflight KNOWN_HOSTS SSH_KEY PUBLIC_KEY_SHA256 TIMEOUT "
            "CONTACT_START_BUDGET | "
            "preflight KNOWN_HOSTS OUTPUT | "
            "wait-preflight KNOWN_HOSTS ANCHOR TIMEOUT OUTPUT | "
            "wait-ssh-preflight KNOWN_HOSTS SSH_KEY PUBLIC_KEY_SHA256 "
            "ANCHOR TIMEOUT "
            "OUTPUT | "
            "reboot KNOWN_HOSTS"
        )
    require_guards(action)
    expected_arguments = {
        "host-preflight": 4,
        "ssh-host-preflight": 6,
        "preflight": 3,
        "wait-preflight": 5,
        "wait-ssh-preflight": 7,
        "reboot": 2,
    }
    if len(arguments) != expected_arguments[action]:
        fail(f"invalid arguments for fallback {action}")
    fixed_binary(UDEVADM)
    fixed_binary(SSH_KEYGEN)
    if action in {"ssh-host-preflight", "wait-ssh-preflight"}:
        fixed_binary(SSH)
        fixed_binary(IP)
        fixed_binary(NMCLI)
    else:
        fixed_binary(SYSTEMCTL)
        fixed_binary(FUSER)
        require_modem_manager_inactive()
    output: Path | None = None
    if action == "preflight":
        output = safe_new_output(Path(arguments[2]))
    elif action == "wait-preflight":
        output = safe_new_output(Path(arguments[4]))
    elif action == "wait-ssh-preflight":
        output = safe_new_output(Path(arguments[6]))
    known_hosts_path = canonical_private_file(
        Path(arguments[1]),
        "fallback host pin",
    )
    known_hosts = verify_known_hosts(known_hosts_path)
    if action == "host-preflight":
        wait_timeout = parse_wait_timeout(arguments[2])
        require_anchor_budget(arguments[3], wait_timeout)
        remote_transport("1" * 32, "classify")
        print(
            "PASS fallback ACM host prerequisites and allowed-signers pin "
            "are exact; no phone contact occurred"
        )
        return 0
    if action == "ssh-host-preflight":
        verify_ssh_key(Path(arguments[2]), arguments[3])
        verify_network_profile()
        wait_timeout = parse_wait_timeout(arguments[4])
        require_anchor_budget(arguments[5], wait_timeout)
        compile(REMOTE_SOURCE, "fallback-ssh-remote.py", "exec")
        print(
            "PASS fallback strict-SSH host prerequisites, client key, "
            "and pinned host key are exact; no phone contact occurred"
        )
        return 0
    if action == "preflight":
        if output is None:
            fail("preflight evidence output is unavailable")
        values, _, proof = probe(known_hosts, action="preflight")
        write_identity(output, values, proof)
        print(
            "PASS pinned exact Alpine fallback verified through fixed USB ACM"
        )
        return 0
    if action == "reboot":
        require_fastboot_absent()
        _, location, _ = probe(known_hosts, action="reboot")
        wait_fastboot(location)
        print("PASS pinned Alpine fallback reached exact fastboot device")
        return 0
    if action == "wait-ssh-preflight":
        if output is None:
            fail("strict-SSH preflight evidence output is unavailable")
        expected_public_sha256 = arguments[3]
        ssh_key = verify_ssh_key(Path(arguments[2]), expected_public_sha256)
        anchor = Path(arguments[4])
        # Profile restoration and this SSH wait share one lifecycle deadline.
        # The restore step may legitimately leave less than the standalone
        # 600-second host-preflight minimum.
        timeout = parse_wait_timeout(arguments[5], minimum=1)
        values, proof = ssh_probe(
            known_hosts_path,
            known_hosts,
            ssh_key,
            expected_public_sha256,
            anchor,
            timeout,
        )
        write_identity(output, values, proof)
        print(
            "PASS pinned exact Alpine fallback returned over strict SSH "
            "on the recovery USB port"
        )
        return 0
    timeout = parse_wait_timeout(arguments[3])
    anchor_path = Path(arguments[2])
    expected_location = read_anchor(anchor_path)
    values, _, proof = probe(
        known_hosts,
        action="classify",
        expected_location=expected_location,
        anchor_path=anchor_path,
        timeout_seconds=timeout,
    )
    if output is None:
        fail("fallback identity output is unavailable")
    write_identity(output, values, proof)
    print(
        "PASS pinned exact Alpine fallback returned on the recovery USB port"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        FallbackError,
        OSError,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
