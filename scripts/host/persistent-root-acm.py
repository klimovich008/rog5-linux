#!/usr/bin/env python3
"""Load or execute the fixed P2 persistent-root payload over recovery ACM."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import NoReturn


sys.dont_write_bytecode = True
TRANSPORT_PATH = Path(__file__).with_name("network-root-acm.py")
SPEC = importlib.util.spec_from_file_location("rog5_network_root_acm", TRANSPORT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the accepted recovery ACM transport")
TRANSPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRANSPORT)

LOAD_COMMAND = (
    "ROG5_RECOVERY_TIMEOUT=600 "
    "/usr/local/sbin/rog5-load-mainline-recovery"
)
LOAD_MARKER = b"PASS mainline read-only persistent-root payload loaded"
PREFLIGHT_COMMAND = (
    "set -eu; "
    '[ -e /run/rog5-recovery-armed ]; '
    "physical_count=0; "
    "writable_physical=0; "
    "for sys_disk in /sys/class/block/*; do "
    '[ -e "$sys_disk/device" ] || continue; '
    '[ ! -e "$sys_disk/partition" ] || continue; '
    'disk=${sys_disk##*/}; '
    'for sys_block in "$sys_disk" "$sys_disk"/"$disk"*; do '
    '[ -e "$sys_block/dev" ] || continue; '
    '[ "$sys_block" = "$sys_disk" ] || '
    '[ -e "$sys_block/partition" ] || continue; '
    "physical_count=$((physical_count + 1)); "
    '[ "$(cat "$sys_block/ro")" = 1 ] || '
    "writable_physical=$((writable_physical + 1)); "
    "done; "
    "done; "
    '[ "$physical_count" = 116 ]; '
    '[ "$writable_physical" = 0 ]; '
    '[ "$(cat /run/rog5-physical-block-count)" = "$physical_count" ]; '
    "[ ! -e /run/rog5-ufs-blocked-query-count ]; "
    "[ ! -e /run/rog5-ufs-blocked-scsi-count ]; "
    '[ "$(cat /sys/kernel/kexec_loaded)" = 1 ]; '
    "(cd /opt/rog5-recovery && sha256sum -c SHA256SUMS); "
    "block_mounts=0; "
    "while read -r _ _ device _ mountpoint _ rest; do "
    '[ ! -e "/sys/dev/block/$device" ] || '
    "block_mounts=$((block_mounts + 1)); "
    "done </proc/self/mountinfo; "
    '[ "$block_mounts" = 0 ]; '
    "printf 'PASS P2 staging preflight storage=ro kexec_loaded=%s\\n' 1"
)
PREFLIGHT_MARKER = b"PASS P2 staging preflight storage=ro kexec_loaded=1"


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def run_marked_action(command: str, marker: bytes, label: str) -> str:
    for attempt in range(2):
        path = TRANSPORT.wait_for_stable_recovery_acm()
        try:
            return TRANSPORT.run_serial(
                path,
                command,
                marker,
                False,
                60,
            )
        except TRANSPORT.MissingLoadMarkerError:
            if attempt:
                raise
            print(
                f"INFO {label} marker missing; rediscovering ACM and "
                "retrying the identical read-safe action once",
                file=sys.stderr,
            )
    raise AssertionError("bounded marked-action loop fell through")


def load_persistent_root() -> str:
    return run_marked_action(LOAD_COMMAND, LOAD_MARKER, "P2 load")


def preflight_persistent_root() -> str:
    return run_marked_action(
        PREFLIGHT_COMMAND,
        PREFLIGHT_MARKER,
        "P2 preflight",
    )


def execute_persistent_root() -> str:
    path = TRANSPORT.wait_for_stable_recovery_acm()
    return TRANSPORT.run_serial(path, "kexec -e", None, True, 20)


def main(arguments: list[str]) -> int:
    if os.environ.get("ALLOW_PERSISTENT_ROOT_ACM") != "1":
        fail("set ALLOW_PERSISTENT_ROOT_ACM=1 for one fixed P2 staging action")
    if (
        len(arguments) != 1
        or arguments[0] not in {"load", "preflight", "execute"}
    ):
        fail("usage: persistent-root-acm.py load|preflight|execute")
    action = arguments[0]
    if action == "execute" and os.environ.get("ALLOW_ATTENDED_KEXEC") != "1":
        fail("set ALLOW_ATTENDED_KEXEC=1 for the attended P2 execute action")
    if os.uname().sysname != "Linux":
        fail("this host workflow requires Linux")
    for command in ("systemctl", "udevadm"):
        if shutil.which(command) is None:
            fail(f"missing host command: {command}")
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "ModemManager.service"],
        check=False,
    ).returncode == 0:
        fail("stop ModemManager before using the recovery ACM")

    if action == "load":
        output = load_persistent_root()
    elif action == "preflight":
        output = preflight_persistent_root()
    else:
        output = execute_persistent_root()
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    print(f"PASS control-safe persistent-root ACM action={action}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
