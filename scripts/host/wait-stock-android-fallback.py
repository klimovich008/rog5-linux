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


def fixed_adb() -> None:
    metadata = ADB.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) != 0o755
        or metadata.st_nlink != 1
    ):
        fail("fixed adb executable is unsafe")


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


def exact_device(location: str) -> bool:
    lines = [line for line in adb("devices", "-l").splitlines()[1:] if line]
    if len(lines) != 1:
        return False
    fields = lines[0].split()
    return fields == [
        SERIAL,
        "device",
        f"usb:{location}",
        f"product:{PRODUCT}",
        f"model:{MODEL}",
        f"device:{DEVICE}",
        fields[-1],
    ] and fields[-1].startswith("transport_id:") and fields[-1][13:].isdigit()


def property_value(name: str) -> str:
    value = adb("-s", SERIAL, "shell", "getprop", name).strip()
    if "\n" in value or "\r" in value:
        fail("stock Android property is not scalar")
    return value


def wait_exact_device(location: str, deadline: float) -> None:
    while time.monotonic() < deadline:
        try:
            if exact_device(location):
                return
        except (FallbackError, subprocess.TimeoutExpired):
            pass
        time.sleep(1)
    fail("exact stock Android ADB identity did not appear")


def verify_stock(location: str) -> OrderedDict[str, str]:
    values = OrderedDict(
        (
            ("format", "rog5-stock-android-fallback-v1"),
            ("serial", SERIAL),
            ("usb_location", location),
            ("product", PRODUCT),
            ("model", MODEL),
            ("device", DEVICE),
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
    fixed_adb()
    if arguments == ["host-preflight"]:
        print("PASS exact stock WW33 fallback verifier is available; no phone contact occurred")
        return 0
    if len(arguments) != 4 or arguments[0] != "wait":
        fail("usage: wait-stock-android-fallback.py host-preflight | wait USB_LOCATION TIMEOUT OUTPUT")
    if os.environ.get("ALLOW_STOCK_ANDROID_FALLBACK_PROOF") != "1":
        fail("set ALLOW_STOCK_ANDROID_FALLBACK_PROOF=1")
    location, timeout_text, output_text = arguments[1:]
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
    wait_exact_device(location, deadline)
    values = verify_stock(location)
    if values["usb_config"] != "adb":
        adb("-s", SERIAL, "shell", "svc", "usb", "setFunctions", "adb")
        wait_exact_device(location, deadline)
        values = verify_stock(location)
    if values["usb_config"] != "adb":
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
