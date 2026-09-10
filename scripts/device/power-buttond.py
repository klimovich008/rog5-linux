#!/usr/bin/python3
"""Toggle the ROG5 display on PMK8350 power-button presses."""

import argparse
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

SYS_INPUT = Path("/sys/class/input")
DEV_INPUT = Path("/dev/input")
INPUT_NAME = "pmic_pwrkey"
SCREEN_TOGGLE = Path("/usr/local/bin/rog5-screen-toggle.sh")
INPUT_EVENT = struct.Struct("@llHHi")
EVENT_TYPE_KEY = 1
KEY_POWER = 116
VALUE_PRESS = 1


def discover_input() -> Path:
    matches = []
    for event in sorted(SYS_INPUT.glob("event*")):
        try:
            name = (event / "device/name").read_text(encoding="ascii").strip()
            candidate = DEV_INPUT / event.name
            mode = candidate.stat().st_mode
        except OSError:
            continue
        if name == INPUT_NAME and stat.S_ISCHR(mode):
            matches.append(candidate)
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one {INPUT_NAME} input, found {len(matches)}"
        )
    return matches[0]


def toggle_screen(toggle: Path) -> None:
    try:
        result = subprocess.run(
            [toggle, "toggle"], check=False, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"screen toggle failed: {error}") from error
    if result.returncode:
        raise RuntimeError(
            f"screen toggle failed with status {result.returncode}"
        )


def monitor(input_path: Path, toggle: Path, once: bool) -> None:
    with input_path.open("rb", buffering=0) as source:
        while True:
            record = source.read(INPUT_EVENT.size)
            if len(record) != INPUT_EVENT.size:
                raise RuntimeError(
                    f"short input_event: expected {INPUT_EVENT.size}, "
                    f"got {len(record)}"
                )
            _, _, event_type, code, value = INPUT_EVENT.unpack(record)
            if (
                event_type == EVENT_TYPE_KEY
                and code == KEY_POWER
                and value == VALUE_PRESS
            ):
                toggle_screen(toggle)
                print("PASS KEY_POWER screen toggle", flush=True)
                if once:
                    return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--toggle", type=Path, default=SCREEN_TOGGLE)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if INPUT_EVENT.size != 24:
        print(
            f"ERROR unexpected AArch64 input_event size: {INPUT_EVENT.size}",
            file=sys.stderr,
        )
        return 1

    if args.input:
        try:
            monitor(args.input, args.toggle, args.once)
        except (OSError, RuntimeError) as error:
            print(f"ERROR {error}", file=sys.stderr)
            return 1
        return 0

    while True:
        try:
            monitor(discover_input(), args.toggle, False)
        except (OSError, RuntimeError) as error:
            print(f"WARN {error}; retrying", file=sys.stderr, flush=True)
            time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
