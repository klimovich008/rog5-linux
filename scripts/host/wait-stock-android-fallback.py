#!/usr/bin/env python3
"""Prove the exact stock WW33 slot-A rescue after a RAM-only Linux boot."""

from __future__ import annotations

from collections import OrderedDict
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from typing import NoReturn


ADB = Path("/usr/bin/adb")
FASTBOOT = Path("/usr/bin/fastboot")
USB_ROOT = Path("/sys/bus/usb/devices")
SERIAL = "M5AIKN00F0353YH"
PRODUCT = "WW_I005D"
MODEL = "ASUS_I005DA"
DEVICE = "ASUS_I005_1"
FINGERPRINT = (
    "asus/WW_I005D/ASUS_I005_1:13/TKQ1.220807.001/"
    "33.0210.0210.200-0:user/release-keys"
)
VBMETA_DIGEST = (
    "48cc851a31e80492d60b3d1895e6be8605f4ef5d9d7c940c8582215fd80ac005"
)
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
USB_LOCATION = re.compile(r"[A-Za-z0-9._:+/-]{1,512}\Z")


class FallbackError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise FallbackError(message)


def fixed_tools() -> None:
    for path in (ADB, FASTBOOT):
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o755
            or metadata.st_nlink != 1
        ):
            fail("fixed Android platform tool is unsafe")


def adb(*arguments: str, timeout: int = 10) -> str:
    result = subprocess.run(
        [str(ADB), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=timeout,
        check=False,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0:
        fail("fixed adb command failed")
    return result.stdout


def device_state(location: str) -> str:
    lines = [line for line in adb("devices", "-l").splitlines()[1:] if line]
    if len(lines) != 1:
        return "absent"
    fields = lines[0].split()
    authorized = fields == [
        SERIAL,
        "device",
        f"usb:{location}",
        f"product:{PRODUCT}",
        f"model:{MODEL}",
        f"device:{DEVICE}",
        fields[-1],
    ] and fields[-1].startswith("transport_id:") and fields[-1][13:].isdigit()
    unauthorized = fields == [
        SERIAL,
        "unauthorized",
        f"usb:{location}",
        fields[-1],
    ] and fields[-1].startswith("transport_id:") and fields[-1][13:].isdigit()
    if authorized:
        return "authorized"
    if unauthorized:
        return "unauthorized"
    return "wrong"


def exact_device(location: str) -> bool:
    return device_state(location) == "authorized"


def property_value(name: str) -> str:
    value = adb("-s", SERIAL, "shell", "getprop", name).strip()
    if "\n" in value or "\r" in value:
        fail("stock Android property is not scalar")
    return value


def wait_device(location: str, deadline: float) -> str:
    while time.monotonic() < deadline:
        try:
            state = device_state(location)
            if state in {"authorized", "unauthorized"}:
                return state
        except (FallbackError, subprocess.TimeoutExpired):
            pass
        time.sleep(1)
    fail("exact stock Android USB identity did not appear")


def verify_stock(location: str) -> OrderedDict[str, str]:
    values = OrderedDict(
        (
            ("format", "rog5-stock-android-fallback-v1"),
            ("serial", SERIAL),
            ("usb_location", location),
            ("product", PRODUCT),
            ("model", MODEL),
            ("device", DEVICE),
            ("evidence_mode", "adb-authorized"),
            ("slot_suffix", property_value("ro.boot.slot_suffix")),
            ("fingerprint", property_value("ro.build.fingerprint")),
            ("vbmeta_digest", property_value("ro.boot.vbmeta.digest")),
            (
                "verified_boot_state",
                property_value("ro.boot.verifiedbootstate"),
            ),
            ("boot_id", adb("-s", SERIAL, "shell", "cat", "/proc/sys/kernel/random/boot_id").strip()),
            ("boot_completed", property_value("sys.boot_completed")),
            ("usb_config", property_value("sys.usb.config")),
            ("result", "PASS"),
        )
    )
    if (
        values["slot_suffix"] != "_a"
        or values["fingerprint"] != FINGERPRINT
        or values["vbmeta_digest"] != VBMETA_DIGEST
        or values["verified_boot_state"] != "orange"
        or not BOOT_ID.fullmatch(values["boot_id"])
        or values["boot_completed"] != "1"
    ):
        fail("stock Android fallback identity is not exact")
    return values


def fastboot_value(name: str) -> str:
    result = subprocess.run(
        [str(FASTBOOT), "-s", SERIAL, "getvar", name],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=10,
        check=False,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0:
        fail("exact fastboot property is unavailable")
    return parse_fastboot_value(result.stdout, name)


def parse_fastboot_value(payload: str, name: str) -> str:
    lines = [line for line in payload.splitlines() if line.startswith(f"{name}: ")]
    if len(lines) != 1:
        fail("exact fastboot property is unavailable")
    return lines[0].split(": ", 1)[1]


def parse_fastboot_devices(payload: str) -> tuple[str, str]:
    lines = [line.split() for line in payload.splitlines() if line]
    if lines != [[SERIAL, "fastboot", "usb:1-1.2"]]:
        fail("exact slot-A fastboot identity is unavailable")
    return SERIAL, "1-1.2"


def capture_preboot(path: Path) -> None:
    payload = subprocess.run(
        [str(FASTBOOT), "devices", "-l"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
        check=False,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    ).stdout
    parse_fastboot_devices(payload)
    values = OrderedDict(
        (
            ("format", "rog5-stock-fallback-preboot-v1"),
            ("serial", SERIAL),
            ("usb_location", "1-1.2"),
            ("product", fastboot_value("product")),
            ("slot", fastboot_value("current-slot")),
            ("battery_soc_ok", fastboot_value("battery-soc-ok")),
            ("result", "PASS"),
        )
    )
    if (
        values["product"] != "lahaina"
        or values["slot"] != "a"
        or values["battery_soc_ok"] != "yes"
    ):
        fail("slot-A fastboot fallback precondition is not exact")
    publish(path, values)


def read_preboot(path: Path, location: str) -> None:
    payload = path.read_text(encoding="ascii")
    lines = payload.splitlines()
    expected = [
        "format=rog5-stock-fallback-preboot-v1",
        f"serial={SERIAL}",
        f"usb_location={location}",
        "product=lahaina",
        "slot=a",
        "battery_soc_ok=yes",
        "result=PASS",
    ]
    metadata = path.lstat()
    if (
        lines != expected
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        fail("stock fallback preboot record is not exact")


def verify_unauthorized_usb(location: str, preboot: Path) -> OrderedDict[str, str]:
    read_preboot(preboot, location)
    device = USB_ROOT / location
    expected = {
        "idVendor": "0b05",
        "idProduct": "7770",
        "manufacturer": "asus",
        "product": "ROG Phone 5",
        "serial": SERIAL,
        "bDeviceClass": "00",
        "bDeviceSubClass": "00",
        "bDeviceProtocol": "00",
    }
    if any((device / name).read_text(encoding="ascii").strip() != value for name, value in expected.items()):
        fail("unauthorized stock Android USB descriptors are not exact")
    interfaces = sorted(USB_ROOT.glob(f"{location}:*"))
    if len(interfaces) != 1:
        fail("unauthorized stock Android interface inventory is not exact")
    interface = interfaces[0]
    for name, value in (
        ("bInterfaceClass", "ff"),
        ("bInterfaceSubClass", "42"),
        ("bInterfaceProtocol", "01"),
    ):
        if (interface / name).read_text(encoding="ascii").strip() != value:
            fail("unauthorized stock Android ADB interface is not exact")
    if (interface / "net").exists():
        fail("unauthorized stock Android unexpectedly exposes USB networking")
    return OrderedDict(
        (
            ("format", "rog5-stock-android-fallback-v1"),
            ("serial", SERIAL),
            ("usb_location", location),
            ("product", "unavailable"),
            ("model", "unavailable"),
            ("device", "unavailable"),
            ("evidence_mode", "usb-unauthorized-slot-a"),
            ("slot_suffix", "_a"),
            ("fingerprint", "unavailable"),
            ("vbmeta_digest", "unavailable"),
            ("verified_boot_state", "unavailable"),
            ("boot_id", "unavailable"),
            ("boot_completed", "unavailable"),
            ("usb_config", "adb-unauthorized"),
            ("result", "PASS"),
        )
    )


def publish(path: Path, values: OrderedDict[str, str]) -> None:
    requested = Path(os.path.abspath(path.expanduser()))
    parent = requested.parent
    metadata = parent.lstat()
    if (
        requested != path
        or parent.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or os.path.lexists(requested)
    ):
        fail("stock fallback output path is unsafe")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(requested, flags, 0o600)
    try:
        payload = "".join(f"{name}={value}\n" for name, value in values.items())
        os.write(descriptor, payload.encode("ascii"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main(arguments: list[str]) -> int:
    fixed_tools()
    if arguments == ["host-preflight"]:
        print("PASS exact stock WW33 fallback verifier is available; no phone contact occurred")
        return 0
    if len(arguments) == 2 and arguments[0] == "capture-preboot":
        if os.environ.get("ALLOW_STOCK_ANDROID_FALLBACK_PROOF") != "1":
            fail("set ALLOW_STOCK_ANDROID_FALLBACK_PROOF=1")
        capture_preboot(Path(arguments[1]))
        print("PASS exact slot-A fastboot fallback precondition captured")
        return 0
    if len(arguments) != 5 or arguments[0] != "wait":
        fail("usage: wait-stock-android-fallback.py host-preflight | capture-preboot OUTPUT | wait USB_LOCATION TIMEOUT PREBOOT OUTPUT")
    if os.environ.get("ALLOW_STOCK_ANDROID_FALLBACK_PROOF") != "1":
        fail("set ALLOW_STOCK_ANDROID_FALLBACK_PROOF=1")
    location, timeout_text, preboot_text, output_text = arguments[1:]
    if (
        not USB_LOCATION.fullmatch(location)
        or location.startswith("/")
        or ".." in Path(location).parts
        or not timeout_text.isascii()
        or not timeout_text.isdecimal()
        or not 60 <= int(timeout_text) <= 900
    ):
        fail("stock fallback wait inputs are invalid")
    deadline = time.monotonic() + int(timeout_text)
    state = wait_device(location, deadline)
    if state == "unauthorized":
        values = verify_unauthorized_usb(location, Path(preboot_text))
    else:
        values = verify_stock(location)
    if state == "authorized" and values["usb_config"] != "adb":
        adb("-s", SERIAL, "shell", "svc", "usb", "setFunctions", "adb")
        state = wait_device(location, deadline)
        if state != "authorized":
            fail("authorized stock Android did not return after USB cleanup")
        values = verify_stock(location)
    if values["usb_config"] not in {"adb", "adb-unauthorized"}:
        fail("stock Android fallback retained a USB network function")
    publish(Path(output_text), values)
    print("PASS exact stock WW33 slot-A fallback reached ADB with network USB disabled")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (FallbackError, OSError, subprocess.SubprocessError, UnicodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
