#!/usr/bin/env python3
"""Run one at-most-once devices-level suspend callback test, never real suspend."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Any


GUARD = "rog5-suspend-pm-test-devices-v1"
EXPECTED_KERNEL = "7.1.4-g7a5cef0db479"
EXPECTED_UDC = "a600000.usb"
EXPECTED_ADDRESS = "169.254.77.2/30"
HOST_ADDRESS = "169.254.77.1"
PM_MARKER = "suspend debug: Waiting for 5 second(s)."
FATAL = re.compile(
    r"Kernel panic|Oops:|BUG:|Unable to handle kernel|"
    r"Synchronous External Abort|watchdog.*bite"
)


class GateError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise GateError(message)


def selected_pm_test(value: str) -> str:
    selected = re.findall(r"\[([^][\s]+)\]", value)
    if len(selected) != 1:
        fail("pm_test selection is malformed")
    return selected[0]


def tokens(value: str) -> list[str]:
    return value.replace("[", "").replace("]", "").split()


class Backend:
    fixture = False
    phase = "pre"

    def get(self, name: str) -> Any:
        raise NotImplementedError

    def write_power(self, name: str, value: str) -> None:
        raise NotImplementedError

    @property
    def run_root(self) -> Path:
        return Path("/run")


class FixtureBackend(Backend):
    fixture = True

    def __init__(self, root: Path) -> None:
        root = Path(os.path.abspath(root))
        if root == Path("/") or root.is_symlink() or not root.is_dir():
            fail("fixture root must be an absolute non-linked directory other than /")
        metadata = root.stat()
        if stat.S_IMODE(metadata.st_mode) != 0o700 or metadata.st_uid != os.getuid():
            fail("fixture root must be owned by the caller with mode 0700")
        fixture_path = root / "fixture.json"
        if fixture_path.is_symlink() or not fixture_path.is_file():
            fail("fixture JSON is absent or linked")
        if fixture_path.stat().st_size > 1024 * 1024:
            fail("fixture JSON is too large")
        self.data = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(self.data, dict):
            fail("fixture JSON must contain an object")
        self.root = root
        self.phase = "pre"

    @property
    def run_root(self) -> Path:
        return self.root / "run"

    def get(self, name: str) -> Any:
        if self.phase == "post":
            post = self.data.get("post", {})
            if isinstance(post, dict) and name in post:
                return post[name]
        if name not in self.data:
            fail(f"fixture omits {name}")
        return self.data[name]

    def record(self, name: str, value: str) -> None:
        with (self.root / "writes.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{name}={value}\n")
            stream.flush()
            os.fsync(stream.fileno())

    def write_power(self, name: str, value: str) -> None:
        self.record(name, value)
        if name == "pm_test":
            current = str(self.data["pm_test"])
            available = tokens(current)
            if value not in available:
                fail(f"fixture cannot select unavailable pm_test level: {value}")
            self.data["pm_test"] = " ".join(
                f"[{item}]" if item == value else item for item in available
            )
            return
        if name != "state" or value != "mem":
            fail("fixture received an unexpected power write")
        if self.data.get("fail_state_write") is True:
            fail("simulated state write failure")
        self.phase = "post"
        if self.data.get("omit_pm_marker") is not True:
            self.data["dmesg"] = f"{self.data['dmesg']}\n{PM_MARKER}"


class RealBackend(Backend):
    def run(self, arguments: list[str], *, allow_failure: bool = False) -> str:
        environment = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/bin", "LC_ALL": "C"}
        result = subprocess.run(
            arguments,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            env=environment,
        )
        if result.returncode != 0 and not allow_failure:
            fail(f"command failed: {' '.join(arguments)}: {result.stderr.strip()}")
        return result.stdout.strip()

    @staticmethod
    def read(path: str, maximum: int = 1024 * 1024) -> str:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            data = os.read(descriptor, maximum + 1)
        finally:
            os.close(descriptor)
        if len(data) > maximum:
            fail(f"oversized runtime input: {path}")
        return data.decode("utf-8").strip()

    def get(self, name: str) -> Any:
        if name == "kernel_release":
            return self.read("/proc/sys/kernel/osrelease", 256)
        if name == "pid1":
            return self.read("/proc/1/comm", 256)
        if name == "cmdline":
            return self.read("/proc/cmdline", 65536)
        if name == "system_state":
            return self.run(["systemctl", "is-system-running"], allow_failure=True)
        if name == "server_inhibitor":
            return self.run(
                ["systemctl", "is-active", "rog5-server-inhibit.service"],
                allow_failure=True,
            )
        if name == "failed_units":
            output = self.run(
                ["systemctl", "--failed", "--no-legend", "--plain"],
                allow_failure=True,
            )
            return len([line for line in output.splitlines() if line.split()])
        if name == "root_fstype":
            return self.run(["findmnt", "-n", "-o", "FSTYPE", "/"])
        if name == "nfs_source":
            return self.run(["findmnt", "-n", "-o", "SOURCE", "/.rog5/root-ro"])
        if name == "nfs_options":
            return self.run(["findmnt", "-n", "-o", "OPTIONS", "/.rog5/root-ro"])
        if name == "physical_blocks":
            block_root = Path("/sys/class/block")
            return sum(1 for entry in block_root.iterdir() if (entry / "device").exists())
        if name == "block_mounts":
            output = self.run(["findmnt", "-rn", "-o", "SOURCE"])
            return sum(1 for line in output.splitlines() if line.startswith("/dev/"))
        if name == "watchdog_pid":
            return Path("/run/rog5-network-root-watchdog.pid").exists()
        if name == "watchdog_disarmed":
            marker = Path("/run/rog5-network-root-watchdog.disarmed.pid")
            return marker.is_file() and marker.stat().st_size > 0
        if name == "udcs":
            return sorted(entry.name for entry in Path("/sys/class/udc").iterdir())
        if name == "bound_udc":
            return self.read("/sys/kernel/config/usb_gadget/rog5-network-root/UDC", 256)
        if name == "usb0_present":
            return Path("/sys/class/net/usb0").exists()
        if name == "carrier":
            return self.read("/sys/class/net/usb0/carrier", 32)
        if name == "addresses":
            output = self.run(["ip", "-4", "-o", "address", "show", "dev", "usb0"])
            return [fields[3] for line in output.splitlines() if len(fields := line.split()) >= 4]
        if name == "route":
            return self.run(["ip", "-4", "route", "get", HOST_ADDRESS])
        if name == "pm_test":
            return self.read("/sys/power/pm_test", 4096)
        if name == "power_state":
            return self.read("/sys/power/state", 4096)
        if name == "sync_on_suspend":
            return self.read("/sys/power/sync_on_suspend", 32)
        if name == "wakeup_count":
            return self.read("/sys/power/wakeup_count", 64)
        if name == "kernel_config":
            with gzip.open("/proc/config.gz", "rt", encoding="utf-8") as stream:
                return stream.read(2 * 1024 * 1024).splitlines()
        if name == "dmesg":
            return self.run(["dmesg"])
        fail(f"unsupported runtime field: {name}")

    def write_power(self, name: str, value: str) -> None:
        paths = {"pm_test": "/sys/power/pm_test", "state": "/sys/power/state"}
        if name not in paths or value not in {"none", "devices", "mem"}:
            fail("refusing unexpected power write")
        descriptor = os.open(paths[name], os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            payload = f"{value}\n".encode("ascii")
            written = os.write(descriptor, payload)
            if written != len(payload):
                fail(f"short power write: {name}")
        finally:
            os.close(descriptor)


def check_config(config: Any) -> None:
    if not isinstance(config, list) or not all(isinstance(line, str) for line in config):
        fail("kernel config inventory is malformed")
    required = {
        "CONFIG_EXPERT=y",
        "CONFIG_PM_DEBUG=y",
        "CONFIG_PM_SLEEP_DEBUG=y",
        "CONFIG_DPM_WATCHDOG=y",
        "CONFIG_DPM_WATCHDOG_TIMEOUT=30",
        "CONFIG_DPM_WATCHDOG_WARNING_TIMEOUT=15",
        "# CONFIG_PM_ADVANCED_DEBUG is not set",
        "# CONFIG_PM_TEST_SUSPEND is not set",
        "# CONFIG_RESET_SIMPLE is not set",
    }
    missing = sorted(required.difference(config))
    if missing:
        fail(f"kernel lacks exact suspend pm_test config: {', '.join(missing)}")


def check_link(backend: Backend, phase: str) -> None:
    prefix = "post-return " if phase == "post" else ""
    udcs = backend.get("udcs")
    if udcs != [EXPECTED_UDC]:
        if phase == "post":
            fail("post-return UDC loss")
        fail("expected exactly one expected UDC")
    if backend.get("bound_udc") != EXPECTED_UDC:
        if phase == "post":
            fail("post-return UDC binding loss")
        fail("network-root gadget is not bound to the expected UDC")
    if backend.get("usb0_present") is not True:
        fail(f"{prefix}interface loss" if phase == "post" else "usb0 is absent")
    if backend.get("carrier") != "1":
        fail(f"{prefix}carrier loss" if phase == "post" else "USB network carrier is down")
    if backend.get("addresses") != [EXPECTED_ADDRESS]:
        fail(f"{prefix}address loss" if phase == "post" else "USB network address is not exact")
    route = str(backend.get("route")).split()
    direct = (
        len(route) >= 5
        and route[0] == HOST_ADDRESS
        and "via" not in route
        and "dev" in route
        and route[route.index("dev") + 1 : route.index("dev") + 2] == ["usb0"]
        and "src" in route
        and route[route.index("src") + 1 : route.index("src") + 2] == ["169.254.77.2"]
    )
    if not direct:
        fail(f"{prefix}route loss" if phase == "post" else "direct USB route is not exact")


def check_runtime(backend: Backend) -> None:
    if backend.get("kernel_release") != EXPECTED_KERNEL:
        fail("unexpected kernel")
    if backend.get("pid1") != "systemd":
        fail("PID 1 is not systemd")
    if "systemd.mask=" in str(backend.get("cmdline")):
        fail("pm_test requires normal unmasked mode")
    if backend.get("system_state") != "running":
        fail("systemd is not running")
    if backend.get("server_inhibitor") != "active":
        fail("server inhibitor is not active")
    if backend.get("failed_units") != 0:
        fail("systemd has failed units")
    if backend.get("root_fstype") != "overlay":
        fail("root is not OverlayFS")
    if backend.get("nfs_source") != "169.254.77.1:/":
        fail("unexpected NFS lower source")
    if "ro" not in str(backend.get("nfs_options")).split(","):
        fail("NFS lower is not read-only")
    if backend.get("physical_blocks") != 0:
        fail("physical block device is present")
    if backend.get("block_mounts") != 0:
        fail("block-backed mount is present")
    if backend.get("watchdog_pid") is not False:
        fail("rollback watchdog is still armed")
    if backend.get("watchdog_disarmed") is not True:
        fail("rollback watchdog has no disarm marker")
    check_link(backend, "pre")
    if FATAL.search(str(backend.get("dmesg"))):
        fail("fatal kernel signature is present before pm_test")


def create_consumed_marker(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    try:
        payload = b"consumed-before-pm-test\n"
        if os.write(descriptor, payload) != len(payload):
            fail("short consumed-marker write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def execute(backend: Backend) -> None:
    check_runtime(backend)
    check_config(backend.get("kernel_config"))
    pm_test = str(backend.get("pm_test"))
    if "devices" not in tokens(pm_test):
        fail("pm_test devices level is unavailable")
    if selected_pm_test(pm_test) != "none":
        fail("pm_test is not disarmed")
    if "mem" not in str(backend.get("power_state")).split():
        fail("mem state is unavailable")
    if backend.get("sync_on_suspend") != "1":
        fail("sync_on_suspend is not enabled")
    try:
        int(str(backend.get("wakeup_count")))
    except ValueError:
        fail("wakeup_count is malformed")

    backend.run_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = backend.run_root / "rog5-pm-test-devices-v1.lock"
    consumed = backend.run_root / "rog5-pm-test-devices-v1.consumed"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        fail("another suspend pm_test gate owns the runtime lock")
    try:
        if consumed.exists():
            fail("devices-level suspend pm_test is already consumed this boot")
        create_consumed_marker(consumed)
        before_dmesg = str(backend.get("dmesg"))
        armed = False
        active_error: BaseException | None = None
        try:
            backend.write_power("pm_test", "devices")
            armed = True
            if selected_pm_test(str(backend.get("pm_test"))) != "devices":
                fail("kernel did not arm the devices pm_test level")
            backend.write_power("state", "mem")
            if selected_pm_test(str(backend.get("pm_test"))) != "devices":
                fail("pm_test selection changed while state write returned")
        except BaseException as error:
            active_error = error
            raise
        finally:
            if armed:
                try:
                    backend.write_power("pm_test", "none")
                    if selected_pm_test(str(backend.get("pm_test"))) != "none":
                        fail("kernel did not disarm pm_test after return")
                except BaseException as restore_error:
                    if active_error is None:
                        raise
                    print(f"FAIL additionally could not disarm pm_test: {restore_error}", file=sys.stderr)

        after_dmesg = str(backend.get("dmesg"))
        if after_dmesg.count(PM_MARKER) != before_dmesg.count(PM_MARKER) + 1:
            fail("exactly one devices-level return marker was not observed")
        check_link(backend, "post")
        if backend.get("system_state") != "running":
            fail("systemd did not return to running state")
        if backend.get("server_inhibitor") != "active":
            fail("server inhibitor did not remain active")
        if backend.get("failed_units") != 0:
            fail("systemd gained a failed unit after pm_test")
        if FATAL.search(after_dmesg):
            fail("fatal kernel signature appeared after pm_test")
    finally:
        shutil.rmtree(lock, ignore_errors=True)

    print(
        "PASS suspend pm_test devices callbacks returned "
        "attempts=1 consumed=1 dpm_watchdog=30s real_suspend=0 "
        f"backend={'fixture' if backend.fixture else 'target'}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if os.environ.get("ALLOW_ROG5_SUSPEND_PM_TEST_DEVICES") != GUARD:
        print("FAIL set the exact execution guard for one devices-level pm_test", file=sys.stderr)
        return 1
    try:
        if arguments.fixture_root is not None:
            if os.environ.get("ROG5_PM_TEST_TESTING") != "1":
                fail("fixture backend requires ROG5_PM_TEST_TESTING=1")
            backend: Backend = FixtureBackend(arguments.fixture_root)
        else:
            if os.environ.get("ROG5_PM_TEST_TESTING") is not None:
                fail("testing marker is forbidden for target execution")
            if os.geteuid() != 0:
                fail("target suspend pm_test requires root")
            backend = RealBackend()
        execute(backend)
    except (GateError, OSError, UnicodeError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
