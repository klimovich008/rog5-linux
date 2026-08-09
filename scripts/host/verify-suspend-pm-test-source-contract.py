#!/usr/bin/env python3
"""Verify that devices-level pm_test returns before the PSCI suspend boundary."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys


class ContractError(RuntimeError):
    pass


FILES = {
    "kconfig": "kernel/power/Kconfig",
    "power_main": "kernel/power/main.c",
    "suspend": "kernel/power/suspend.c",
    "dpm": "drivers/base/power/main.c",
    "psci": "drivers/firmware/psci/psci.c",
}


def fail(message: str) -> None:
    raise ContractError(message)


def read_source(root: Path, relative: str) -> str:
    path = root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        fail(f"missing source file: {relative}")
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        fail(f"unsafe source file: {relative}")
    if metadata.st_size <= 0 or metadata.st_size > 4 * 1024 * 1024:
        fail(f"invalid source file size: {relative}")
    return path.read_text(encoding="utf-8")


def function_body(text: str, signature: str, label: str) -> str:
    start = text.find(signature)
    if start < 0:
        fail(f"missing {label}")
    opening = text.find("{", start)
    if opening < 0:
        fail(f"malformed {label}")
    depth = 0
    for index in range(opening, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    fail(f"unterminated {label}")


def kconfig_block(text: str, symbol: str) -> str:
    marker = f"config {symbol}\n"
    start = text.find(marker)
    if start < 0:
        fail(f"missing {symbol} Kconfig block")
    end = text.find("\nconfig ", start + len(marker))
    return text[start:] if end < 0 else text[start:end]


def require(text: str, token: str, message: str) -> None:
    if token not in text:
        fail(message)


def require_order(text: str, tokens: tuple[str, ...], message: str) -> None:
    position = -1
    for token in tokens:
        current = text.find(token, position + 1)
        if current < 0:
            fail(message)
        position = current


def verify(root: Path) -> None:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        fail("kernel source root must be an absolute non-linked directory")
    source = {name: read_source(root, relative) for name, relative in FILES.items()}

    pm_sleep_debug = kconfig_block(source["kconfig"], "PM_SLEEP_DEBUG")
    require(pm_sleep_debug, "def_bool y", "PM_SLEEP_DEBUG is not derived")
    require(
        pm_sleep_debug,
        "depends on PM_DEBUG && PM_SLEEP",
        "PM_SLEEP_DEBUG dependency changed",
    )
    require(source["kconfig"], "config DPM_WATCHDOG", "DPM watchdog Kconfig is absent")
    require(
        source["kconfig"],
        "depends on PM_DEBUG && PSTORE && EXPERT",
        "DPM watchdog dependency changed",
    )

    require(
        source["power_main"],
        '[TEST_DEVICES] = "devices",',
        "pm_test devices level is absent",
    )
    require(source["power_main"], "power_attr(pm_test);", "pm_test sysfs attribute is absent")
    pm_test_store = function_body(
        source["power_main"], "static ssize_t pm_test_store", "pm_test store function"
    )
    require(
        pm_test_store,
        "pm_test_level = level;",
        "pm_test store does not select the requested level",
    )

    suspend_test = function_body(
        source["suspend"], "static int suspend_test", "suspend test function"
    )
    require_order(
        suspend_test,
        ("if (pm_test_level == level)", "return 1;"),
        "suspend test no longer returns before deeper entry",
    )
    devices_enter = function_body(
        source["suspend"],
        "int suspend_devices_and_enter",
        "suspend devices-and-enter function",
    )
    require(
        devices_enter,
        "if (suspend_test(TEST_DEVICES))\n\t\tgoto Recover_platform;",
        "devices-level suspend intercept changed",
    )
    require_order(
        devices_enter,
        (
            "dpm_suspend_start(PMSG_SUSPEND)",
            "suspend_test(TEST_DEVICES)",
            "suspend_enter(state, &wakeup)",
            "dpm_resume_end(PMSG_RESUME)",
        ),
        "devices-level test no longer returns before platform/CPU entry",
    )

    watchdog = function_body(
        source["dpm"], "static void dpm_watchdog_handler", "DPM watchdog handler"
    )
    require(watchdog, "**** DPM device timeout ****", "DPM watchdog diagnostic changed")
    require(
        watchdog,
        'panic("%s %s: unrecoverable failure\\n",',
        "DPM watchdog panic changed",
    )

    require(
        source["psci"],
        "ret = psci_features(PSCI_FN_NATIVE(1_0, SYSTEM_SUSPEND));",
        "PSCI SYSTEM_SUSPEND feature probe changed",
    )
    require(
        source["psci"],
        "suspend_set_ops(&psci_suspend_ops);",
        "PSCI system-suspend registration changed",
    )
    psci_enter = function_body(
        source["psci"],
        "static int psci_system_suspend_enter",
        "PSCI system-suspend entry",
    )
    require(
        psci_enter,
        "return cpu_suspend(0, psci_system_suspend);",
        "PSCI system-suspend entry changed",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} KERNEL_SOURCE", file=sys.stderr)
        return 2
    try:
        root = Path(os.path.abspath(sys.argv[1]))
        verify(root)
    except (ContractError, OSError, UnicodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print("status=devices-level-return-before-psci")
    print("dpm_watchdog=panic-after-30-seconds-when-configured")
    print("real_suspend=forbidden")
    print("PASS pinned Linux source preserves the devices-level pm_test boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
