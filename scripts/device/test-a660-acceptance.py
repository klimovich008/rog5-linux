#!/usr/bin/env python3
"""Offline contract and fault tests for the unified A660 acceptance suite."""

from __future__ import annotations

from dataclasses import replace
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "scripts/device/a660-acceptance.py"
SUBMIT_SOURCE = REPO / "tools/a660/rog5-vulkan-submit.c"
RUNNER_SOURCE = REPO / "tools/a660/rog5-cgroup-exec.c"
PERSISTENT_VERIFIER_SOURCE = REPO / "tools/persistent-root-verify.c"
PERSISTENT_ROOT_TOOL = REPO / "scripts/device/persistent-root-tool.py"
SUBMIT_BUILD = REPO / "scripts/device/build-a660-vulkan-submit.sh"
FAKE_VULKAN = REPO / "tools/a660/test-fake-vulkan.c"
FIXTURE_MANIFEST_SHA256 = "b" * 64
FIXTURE_TREE_SHA256 = "c" * 64
FIXTURE_SEAL_SHA256 = "d" * 64
FIXTURE_TREE_ENTRIES = 7
FIXTURE_RUNNER: Path | None = None

SPEC = importlib.util.spec_from_file_location("rog5_a660_acceptance", TARGET)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load A660 acceptance module")
ACCEPTANCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ACCEPTANCE
SPEC.loader.exec_module(ACCEPTANCE)


class AcceptanceFixture:
    def __init__(self, test: unittest.TestCase):
        self.test = test
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.root = self.base / "root"
        self.report = self.base / "report"
        self.bin = self.base / "bin"
        self.dmesg = self.base / "dmesg"
        self.invocations = self.base / "invocations"
        self.root.mkdir()
        self.bin.mkdir()
        self.dmesg.write_text("[    0.0] Linux booted\n", encoding="ascii")
        self.invocations.write_text("", encoding="ascii")
        self._filesystem()
        self.commands = self._commands()

    def cleanup(self) -> None:
        self.temporary.cleanup()

    def _filesystem(self) -> None:
        directories = (
            ".rog5/root-ro",
            ".rog5/state/upper",
            "dev/dri",
            "drivers/msm",
            "proc/1",
            "proc/100",
            "proc/999/fd",
            "proc/999/fdinfo",
            "proc/1000",
            "proc/self",
            "run",
            "sys/dev/block",
            "sys/devices/mock/block/sda/sda23",
            "sys/devices/mock/block/sda/sda24",
            "sys/class/backlight/panel0-backlight",
            "sys/class/block",
            "sys/class/drm/renderD128/device",
        )
        for relative in directories:
            (self.root / relative).mkdir(parents=True, exist_ok=True)
        (self.root / "dev/dri/renderD128").write_bytes(b"render-fixture")
        (self.root / "proc/1/comm").write_text(
            "systemd\n", encoding="ascii"
        )
        (self.root / "proc/100/comm").write_text(
            "kwin_wayland\n", encoding="ascii"
        )
        (self.root / "proc/100/stat").write_text(
            self.process_stat(100, "kwin_wayland", 1, 1000),
            encoding="ascii",
        )
        (self.root / "proc/100/status").write_text(
            "Name:\tkwin_wayland\n", encoding="ascii"
        )
        (self.root / "proc/100/smaps_rollup").write_text(
            "Pss:\t300000 kB\n", encoding="ascii"
        )
        (self.root / "proc/999/comm").write_text(
            "init\n", encoding="ascii"
        )
        (self.root / "proc/999/stat").write_text(
            self.process_stat(999, "init", 1, 900),
            encoding="ascii",
        )
        (self.root / "proc/999/exe").symlink_to("/bin/busybox")
        (self.root / "proc/999/fd/8").symlink_to("/dev/kmsg")
        (self.root / "proc/999/fd/9").symlink_to(
            "/proc/sysrq-trigger"
        )
        for descriptor in (8, 9):
            (
                self.root / f"proc/999/fdinfo/{descriptor}"
            ).write_text(
                "pos:\t0\nflags:\t0100001\n",
                encoding="ascii",
            )
        (self.root / "proc/1000/comm").write_text(
            "sleep\n", encoding="ascii"
        )
        (self.root / "proc/1000/stat").write_text(
            self.process_stat(1000, "sleep", 999, 905),
            encoding="ascii",
        )
        (self.root / "proc/1000/exe").symlink_to("/bin/busybox")
        (self.root / "proc/uptime").write_text(
            "100.00 90.00\n", encoding="ascii"
        )
        (self.root / "proc/100/environ").write_bytes(
            b"XDG_RUNTIME_DIR=/run/user/1000\0"
            b"WAYLAND_DISPLAY=wayland-0\0"
            b"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus\0"
        )
        (self.root / "proc/self/mountinfo").write_text(
            "20 1 0:20 / / rw - overlay overlay "
            "rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,"
            "workdir=/mnt/state/work\n"
            "21 20 0:21 / /.rog5/root-ro ro,relatime "
            "- nfs 169.254.77.1:/ ro\n"
            "22 20 0:22 / /.rog5/state rw,nosuid,nodev,relatime "
            "- tmpfs tmpfs rw,size=2097152k\n",
            encoding="ascii",
        )
        (self.root / "proc/cmdline").write_text(
            "console=ttyMSM0,115200n8 "
            "rog5.netroot=1 "
            "rog5.bundle=a660-acceptance-test "
            "rog5.target_timeout=600 "
            "rog5.recovery_timeout=900 "
            "rog5.a660_command_manifest_sha256="
            f"{FIXTURE_MANIFEST_SHA256} "
            "rog5.root_generation=arch-a "
            f"rog5.root_tree_sha256={FIXTURE_TREE_SHA256} "
            f"rog5.root_seal_sha256={FIXTURE_SEAL_SHA256} "
            f"rog5.root_tree_entries={FIXTURE_TREE_ENTRIES} "
            "rog5.root_subtree=/\n",
            encoding="ascii",
        )
        identity = self.root / "run/rog5-network-root-identity"
        identity.write_text(
            "format=rog5-network-root-identity-v1\n"
            "overlay_mount_id=20\n"
            "overlay_lower_mount_id=21\n"
            "state_mount_id=22\n"
            "overlay_lower_path=/mnt/root-ro\n"
            "command_manifest_sha256="
            f"{FIXTURE_MANIFEST_SHA256}\n"
            "root_generation=arch-a\n"
            f"root_tree_sha256={FIXTURE_TREE_SHA256}\n"
            f"root_seal_sha256={FIXTURE_SEAL_SHA256}\n"
            f"root_tree_entries={FIXTURE_TREE_ENTRIES}\n"
            "root_subtree=/\n",
            encoding="ascii",
        )
        identity.chmod(0o400)
        driver = self.root / "sys/class/drm/renderD128/device/driver"
        driver.symlink_to(self.root / "drivers/msm", target_is_directory=True)
        (self.root / "run/rog5-network-root-watchdog.pid").write_text(
            "999\n", encoding="ascii"
        )
        (
            self.root / "run/rog5-network-root-watchdog.pid"
        ).chmod(0o400)
        lease = self.root / "run/rog5-network-root-watchdog.lease"
        lease.write_text(
            "format=rog5-network-root-watchdog-v1\n"
            "pid=999\n"
            "start_time_ticks=900\n"
            "timer_pid=1000\n"
            "timer_start_time_ticks=905\n"
            "armed_boottime_seconds=90\n"
            "deadline_boottime_seconds=990\n"
            "timeout_seconds=900\n",
            encoding="ascii",
        )
        lease.chmod(0o400)
        (self.root / "run/rog5-network-root-mounted").touch()
        (self.root / "run/rog5-network-root-source").write_text(
            "169.254.77.1:/\n", encoding="ascii"
        )
        (self.root / "run/rog5-physical-block-count").write_text(
            "0\n", encoding="ascii"
        )
        (self.root / "run/rog5-screen-state").write_text(
            "on\n", encoding="ascii"
        )
        (self.root / "run/rog5-dpms-state").write_text(
            "on\n", encoding="ascii"
        )
        (
            self.root
            / "sys/class/backlight/panel0-backlight/brightness"
        ).write_text("100\n", encoding="ascii")

    @staticmethod
    def process_stat(
        pid: int,
        name: str,
        ppid: int,
        start_time: int,
        state: str = "S",
    ) -> str:
        fields = [state, str(ppid), *(["0"] * 17), str(start_time)]
        return f"{pid} ({name}) {' '.join(fields)}\n"

    def script(self, name: str, body: str) -> Path:
        path = self.bin / name
        path.write_text(
            "#!/bin/sh\nset -eu\n"
            f"printf '%s\\n' {shlex.quote(name)} "
            f">> {shlex.quote(str(self.invocations))}\n"
            f"{body}\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def _commands(self) -> dict[str, Path]:
        if FIXTURE_RUNNER is None:
            raise RuntimeError("cgroup runner fixture is unavailable")
        root = shlex.quote(str(self.root))
        dmesg = shlex.quote(str(self.dmesg))
        watchdog_stat = shlex.quote(
            self.process_stat(999, "init", 1, 901)
        )
        kwin_stat = shlex.quote(
            self.process_stat(100, "kwin_wayland", 1, 1001)
        )
        root_verify_count = shlex.quote(
            str(self.base / "root-verify-count")
        )
        return {
            "runner": FIXTURE_RUNNER,
            "systemctl": self.script("systemctl", "echo running"),
            "dmesg": self.script("dmesg", f"cat {dmesg}"),
            "baseline": self.script(
                "baseline",
                f"""screen=$(cat {root}/run/rog5-screen-state)
cat <<EOF
thermal_max_millidegree_c=${{ROG5_FIXTURE_THERMAL:-42000}}
memory_available_kib=${{ROG5_FIXTURE_MEMORY:-2000000}}
plasma_process_count=${{ROG5_FIXTURE_PLASMA_COUNT:-1}}
plasma_pss_kib=${{ROG5_FIXTURE_PLASMA_PSS:-300000}}
battery_status=${{ROG5_FIXTURE_BATTERY_STATUS:-Discharging}}
battery_capacity_percent=${{ROG5_FIXTURE_BATTERY_CAPACITY:-77}}
battery_current_ua=${{ROG5_FIXTURE_BATTERY_CURRENT:--450000}}
screen_state=$screen
drm_render_node_count=${{ROG5_FIXTURE_RENDER_COUNT:-1}}
EOF""",
            ),
            "vulkaninfo": self.script(
                "vulkaninfo",
                """cat <<'EOF'
driverName = turnip
deviceName = Turnip Adreno (TM) 660
EOF""",
            ),
            "eglinfo": self.script(
                "eglinfo",
                "echo 'OpenGL renderer string: FD660'",
            ),
            "submit": self.script(
                "submit",
                f"""watchdog_stat={watchdog_stat}
kwin_stat={kwin_stat}
if [ "${{ROG5_TEST_INJECT_FAULT:-0}}" = 1 ] &&
   [ ! -e {dmesg}.fault ]; then
    fault=${{ROG5_FIXTURE_FAULT_LINE:-[  10.0] arm-smmu IOMMU fault}}
    printf '%s\\n' "$fault" >> {dmesg}
    : > {dmesg}.fault
fi
if [ "${{ROG5_FIXTURE_REUSE_WATCHDOG:-0}}" = 1 ]; then
    printf '%s\\n' "$watchdog_stat" > {root}/proc/999/stat
fi
if [ "${{ROG5_FIXTURE_REUSE_KWIN:-0}}" = 1 ]; then
    printf '%s\\n' "$kwin_stat" > {root}/proc/100/stat
fi
if [ "${{ROG5_FIXTURE_BREAK_DPMS:-0}}" = 1 ] &&
   [ "$(cat {root}/run/rog5-screen-state)" = off ]; then
    echo on > {root}/run/rog5-dpms-state
fi
if [ "${{ROG5_FIXTURE_TRANSIENT_DPMS:-0}}" = 1 ] &&
   [ "$(cat {root}/run/rog5-screen-state)" = off ]; then
    echo on > {root}/run/rog5-dpms-state
    echo 100 > {root}/sys/class/backlight/panel0-backlight/brightness
    sleep 0.5
    echo 0 > {root}/sys/class/backlight/panel0-backlight/brightness
    echo off > {root}/run/rog5-dpms-state
fi
cat <<'EOF'
format=rog5-vulkan-submit-v1
device_name=Turnip Adreno (TM) 660
api_version=1.4.0
queue_family=0
submit=pass
EOF""",
            ),
            "gdbus": self.script(
                "gdbus",
                "echo \"('OpenGL renderer string: FD660',)\"",
            ),
            "vkcube": self.script(
                "vkcube",
                """[ "$#" -eq 4 ]
[ "$1" = --wsi ]
[ "$2" = wayland ]
[ "$3" = --c ]
[ "$4" = 120 ]
if [ "${ROG5_FIXTURE_VKCUBE_HANG:-0}" = 1 ]; then
    sleep 30
fi""",
            ),
            "screen": self.script(
                "screen",
                f"""case $1 in
off)
    echo off > {root}/run/rog5-screen-state
    echo off > {root}/run/rog5-dpms-state
    echo 0 > {root}/sys/class/backlight/panel0-backlight/brightness
    ;;
on)
    echo on > {root}/run/rog5-screen-state
    echo on > {root}/run/rog5-dpms-state
    echo 100 > {root}/sys/class/backlight/panel0-backlight/brightness
    ;;
*) exit 2 ;;
esac""",
            ),
            "kscreen": self.script(
                "kscreen",
                f"""[ "$#" -eq 2 ]
[ "$1" = --dpms ]
[ "$2" = show ]
state=$(cat {root}/run/rog5-dpms-state)
printf 'dpms mode for screen DSI-1: %s\\n' "$state" """,
            ),
            "root_verify": self.script(
                "root-verify",
                f"""[ "$#" -eq 3 ]
case "$1" in
/.rog5/root-ro|/.rog5/userdata-ro/rog5/roots/arch-a) ;;
*) exit 2 ;;
esac
[ "$2" = "$1/.rog5-persistent-seal" ]
[ "$3" = {FIXTURE_SEAL_SHA256} ]
tree=${{ROG5_FIXTURE_ROOT_TREE:-{FIXTURE_TREE_SHA256}}}
count=0
[ ! -f {root_verify_count} ] || read -r count < {root_verify_count}
count=$((count + 1))
printf '%s\\n' "$count" > {root_verify_count}
if [ "${{ROG5_FIXTURE_ROOT_TREE_AFTER_FIRST:-0}}" = 1 ] &&
   [ "$count" -gt 1 ]; then
    tree={'e' * 64}
fi
printf '%s\\n' \
  "PASS persistent root matches anchored seal entries={FIXTURE_TREE_ENTRIES} tree_sha256=$tree" """,
            ),
        }

    def environment(self, mode: str) -> dict[str, str]:
        environment = {
            "HOME": str(self.base),
            "USER": "test",
            "LOGNAME": "test",
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
        if mode == "staging":
            environment["ALLOW_A660_STAGING_ACCEPTANCE"] = "1"
        elif mode == "soak":
            environment["ALLOW_A660_PROMOTED_SOAK"] = "1"
        return environment

    @staticmethod
    def trusted_fixture_command(
        name: str,
        path: Path,
    ) -> ACCEPTANCE.TrustedCommand:
        descriptor = os.memfd_create(
            f"rog5-a660-fixture-{name}",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        try:
            payload = path.read_bytes()
            offset = 0
            while offset < len(payload):
                offset += os.write(descriptor, payload[offset:])
            os.fchmod(descriptor, 0o555)
            os.lseek(descriptor, 0, os.SEEK_SET)
            seals = (
                fcntl.F_SEAL_SEAL
                | fcntl.F_SEAL_SHRINK
                | fcntl.F_SEAL_GROW
                | fcntl.F_SEAL_WRITE
            )
            fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals)
            return ACCEPTANCE.TrustedCommand(
                name=name,
                path=path,
                descriptor=descriptor,
                sha256=hashlib.sha256(payload).hexdigest(),
            )
        except BaseException:
            os.close(descriptor)
            raise

    def configuration(self, mode: str) -> ACCEPTANCE.Configuration:
        return ACCEPTANCE.Configuration(
            mode=mode,
            fixture=True,
            root=self.root,
            report=self.report,
            expected_kernel=os.uname().release,
            render_cycles=100,
            vulkan_cycles=10,
            submit_cycles=1,
            screen_cycles=1,
            screen_pause_seconds=0,
            workload_seconds=0.05,
            soak_seconds=1,
            soak_interval_seconds=1,
            thermal_limit_mc=60000,
            memory_floor_kib=131072,
            staging_deadline_seconds=10,
            command_manifest_sha256=FIXTURE_MANIFEST_SHA256,
            commands={
                name: self.trusted_fixture_command(name, path)
                for name, path in self.commands.items()
            },
        )

    @staticmethod
    def run_fixture_configuration(
        config: ACCEPTANCE.Configuration,
    ) -> bytes:
        session = None
        watchdog = None
        previous_handler = None
        if config.mode == "staging":
            previous_handler = ACCEPTANCE.signal.signal(
                ACCEPTANCE.signal.SIGALRM,
                ACCEPTANCE.staging_deadline_expired,
            )
            ACCEPTANCE.signal.alarm(config.staging_deadline_seconds)
        try:
            session, watchdog, runtime = ACCEPTANCE.preflight(config)
            if config.mode == "preflight":
                return (
                    "PASS A660 fixture preflight "
                    f"kernel={config.expected_kernel} "
                    f"kwin_pid={session.pid}\n"
                ).encode("ascii")
            if runtime is None:
                raise ACCEPTANCE.AcceptanceError(
                    "runtime profile was not established"
                )
            return ACCEPTANCE.execute(
                config,
                session,
                watchdog,
                runtime,
            )
        finally:
            if config.mode == "staging":
                ACCEPTANCE.signal.alarm(0)
                if previous_handler is not None:
                    ACCEPTANCE.signal.signal(
                        ACCEPTANCE.signal.SIGALRM,
                        previous_handler,
                    )
            ACCEPTANCE.close_identity(
                session.identity if session is not None else None
            )
            ACCEPTANCE.close_identity(
                watchdog.identity if watchdog is not None else None
            )
            ACCEPTANCE.close_identity(
                (
                    watchdog.timer_identity
                    if watchdog is not None
                    else None
                )
            )

    def invoke(
        self,
        mode: str,
        *,
        environment: dict[str, str] | None = None,
    ) -> SimpleNamespace:
        selected = (
            self.environment(mode)
            if environment is None
            else environment
        )
        config = self.configuration(mode)
        with mock.patch.dict(os.environ, selected, clear=True):
            try:
                if (
                    mode == "staging"
                    and selected.get(
                        "ALLOW_A660_STAGING_ACCEPTANCE"
                    )
                    != "1"
                ):
                    raise ACCEPTANCE.AcceptanceError(
                        "set ALLOW_A660_STAGING_ACCEPTANCE=1"
                    )
                if (
                    mode == "soak"
                    and selected.get("ALLOW_A660_PROMOTED_SOAK")
                    != "1"
                ):
                    raise ACCEPTANCE.AcceptanceError(
                        "set ALLOW_A660_PROMOTED_SOAK=1"
                    )
                output = self.run_fixture_configuration(config)
            except (
                ACCEPTANCE.AcceptanceError,
                OSError,
                subprocess.SubprocessError,
                UnicodeError,
                ValueError,
            ) as error:
                message = (
                    str(error)
                    if isinstance(error, ACCEPTANCE.AcceptanceError)
                    else "host operation failed"
                )
                return SimpleNamespace(
                    returncode=1,
                    stdout=b"",
                    stderr=f"FAIL {message}\n".encode("ascii"),
                )
            finally:
                ACCEPTANCE.close_commands(config)
        return SimpleNamespace(returncode=0, stdout=output, stderr=b"")

    def promote(self) -> None:
        for relative in (
            "run/rog5-network-root-watchdog.pid",
            "run/rog5-network-root-watchdog.lease",
            "run/rog5-network-root-mounted",
            "run/rog5-network-root-source",
            "run/rog5-network-root-identity",
            "run/rog5-physical-block-count",
        ):
            (self.root / relative).unlink(missing_ok=True)
        (self.root / "proc/cmdline").write_text(
            "console=ttyMSM0,115200n8 "
            "rog5.persistent_promoted=1 "
            "rog5.ufs_discovery=1 "
            "rog5.bundle=a660-promoted-test "
            "rog5.a660_command_manifest_sha256="
            f"{FIXTURE_MANIFEST_SHA256} "
            f"rog5.root_tree_sha256={FIXTURE_TREE_SHA256} "
            f"rog5.root_seal_sha256={FIXTURE_SEAL_SHA256} "
            f"rog5.root_tree_entries={FIXTURE_TREE_ENTRIES} "
            "rog5.root_generation=arch-a "
            "rog5.root_subtree=/rog5/roots/arch-a "
            "rog5.root_device=8:23\n",
            encoding="ascii",
        )
        (
            self.root / "sys/dev/block/8:23"
        ).symlink_to(
            self.root / "sys/devices/mock/block/sda/sda23",
            target_is_directory=True,
        )
        (self.root / "proc/self/mountinfo").write_text(
            "20 1 0:20 / / rw,relatime - overlay overlay "
            "rw,lowerdir=/mnt/userdata/rog5/roots/arch-a,"
            "upperdir=/mnt/state/upper,workdir=/mnt/state/work\n"
            "21 20 8:23 / /.rog5/userdata-ro ro,relatime "
            "- ext4 /dev/sda23 ro,noload\n"
            "22 20 0:22 / /.rog5/state rw,nosuid,nodev,relatime "
            "- tmpfs tmpfs rw,size=2097152k\n",
            encoding="ascii",
        )
        attestation = (
            "format=rog5-persistent-promotion-v2\n"
            "profile=persistent-root-promoted-v1\n"
            "bundle=a660-promoted-test\n"
            f"kernel={os.uname().release}\n"
            "command_manifest_sha256="
            f"{FIXTURE_MANIFEST_SHA256}\n"
            "root_mount_fstype=ext4\n"
            "root_mount_source=/dev/sda23\n"
            "root_mount_device=8:23\n"
            "overlay_mount_id=20\n"
            "overlay_lower_mount_id=21\n"
            "state_mount_id=22\n"
            "overlay_lower_path=/mnt/userdata/rog5/roots/arch-a\n"
            "root_generation=arch-a\n"
            "root_subtree=/rog5/roots/arch-a\n"
            f"root_tree_entries={FIXTURE_TREE_ENTRIES}\n"
            f"root_tree_sha256={FIXTURE_TREE_SHA256}\n"
            f"root_seal_sha256={FIXTURE_SEAL_SHA256}\n"
            "verification_mount=/.rog5/userdata-ro\n"
            "verification_root="
            "/.rog5/userdata-ro/rog5/roots/arch-a\n"
        )
        path = (
            self.root
            / "run/rog5-persistent-promotion.attestation"
        )
        path.write_text(attestation, encoding="ascii")
        path.chmod(0o400)


class A660AcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        global FIXTURE_RUNNER

        if shutil.which("gcc") is None:
            raise RuntimeError("gcc is required")
        cls.runner_temporary = tempfile.TemporaryDirectory()
        FIXTURE_RUNNER = (
            Path(cls.runner_temporary.name) / "rog5-cgroup-exec"
        )
        cls.persistent_verifier = (
            Path(cls.runner_temporary.name) / "persistent-root-verify"
        )
        subprocess.run(
            [
                "gcc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(RUNNER_SOURCE),
                "-o",
                str(FIXTURE_RUNNER),
            ],
            cwd=REPO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        subprocess.run(
            [
                "gcc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(PERSISTENT_VERIFIER_SOURCE),
                "-o",
                str(cls.persistent_verifier),
            ],
            cwd=REPO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        global FIXTURE_RUNNER

        FIXTURE_RUNNER = None
        cls.runner_temporary.cleanup()

    def setUp(self) -> None:
        self.fixture = AcceptanceFixture(self)

    def tearDown(self) -> None:
        self.fixture.cleanup()

    def test_staging_gate_is_bounded_and_leaves_screen_off(self) -> None:
        result = self.fixture.invoke("staging")
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )
        expected_fields = {
            "format": "rog5-a660-acceptance-fixture-v1",
            "mode": "staging",
            "kernel": os.uname().release,
            "runtime_profile": "network-root-v1",
            "bundle": "a660-acceptance-test",
            "command_manifest_sha256": FIXTURE_MANIFEST_SHA256,
            "root_generation": "arch-a",
            "root_subtree": "/",
            "root_tree_entries": str(FIXTURE_TREE_ENTRIES),
            "root_tree_sha256": FIXTURE_TREE_SHA256,
            "root_seal_sha256": FIXTURE_SEAL_SHA256,
            "root_device": "none",
            "render_open_cycles": "100",
            "vulkaninfo_cycles": "10",
            "submit_cycles": "1",
            "screen_cycles": "1",
            "soak_seconds": "0",
            "thermal_before_mc": "42000",
            "thermal_after_mc": "42000",
            "thermal_observed_max_mc": "42000",
            "memory_available_before_kib": "2000000",
            "memory_available_after_kib": "2000000",
            "plasma_processes_before": "1",
            "plasma_processes_after": "1",
            "plasma_pss_before_kib": "300000",
            "plasma_pss_after_kib": "300000",
            "battery_status_before": "Discharging",
            "battery_status_after": "Discharging",
            "battery_capacity_before_percent": "77",
            "battery_capacity_after_percent": "77",
            "battery_current_before_ua": "-450000",
            "battery_current_after_ua": "-450000",
            "kernel_delta_sha256": hashlib.sha256(b"").hexdigest(),
            "screen_final": "off",
            "status": "pass",
        }
        expected = "".join(
            f"{name}={value}\n" for name, value in expected_fields.items()
        ).encode("ascii")
        self.assertEqual(result.stdout, expected)
        self.assertEqual(
            (
                self.fixture.root
                / "run/rog5-screen-state"
            ).read_text(encoding="ascii"),
            "off\n",
        )
        self.assertEqual(
            {path.name for path in self.fixture.report.iterdir()},
            {
                "dmesg-before.log",
                "dmesg-delta.log",
                "egl-info.txt",
                "kwin-support.txt",
                "metrics-after.txt",
                "metrics-before.txt",
                "result",
                "runtime-root-verification-after.txt",
                "runtime-root-verification-before.txt",
                "vulkan-summary.txt",
            },
        )
        self.assertEqual(
            stat.S_IMODE(self.fixture.report.stat().st_mode),
            0o700,
        )
        for path in self.fixture.report.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_promoted_soak_refuses_an_armed_rollback_watchdog(self) -> None:
        result = self.fixture.invoke("soak")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"soak cannot consume a rollback window",
            result.stderr,
        )
        self.assertFalse(self.fixture.report.exists())

        self.fixture.promote()
        result = self.fixture.invoke("soak")
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )
        self.assertIn(b"mode=soak\n", result.stdout)
        self.assertIn(b"soak_seconds=1\n", result.stdout)
        self.assertIn(
            b"runtime_profile=persistent-root-promoted-v1\n",
            result.stdout,
        )
        self.assertIn(
            b"root_subtree=/rog5/roots/arch-a\n",
            result.stdout,
        )
        self.assertIn(b"screen_final=off\n", result.stdout)

    def test_promoted_soak_refuses_a_stale_watchdog_lease(self) -> None:
        self.fixture.promote()
        lease = (
            self.fixture.root
            / "run/rog5-network-root-watchdog.lease"
        )
        lease.write_text(
            "format=rog5-network-root-watchdog-v1\n",
            encoding="ascii",
        )
        lease.chmod(0o400)
        result = self.fixture.invoke("soak")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"soak cannot consume a rollback window",
            result.stderr,
        )
        self.assertFalse(self.fixture.report.exists())

    def test_soak_refuses_watchdog_removal_without_promotion(self) -> None:
        for name in (
            "rog5-network-root-watchdog.pid",
            "rog5-network-root-watchdog.lease",
        ):
            (self.fixture.root / "run" / name).unlink()
        result = self.fixture.invoke("soak")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"kernel command line does not bind "
            b"rog5.persistent_promoted",
            result.stderr,
        )
        self.assertFalse(self.fixture.report.exists())

    def test_staging_profile_and_timeout_contract_is_exact(self) -> None:
        cases = (
            (
                "rog5.netroot=1",
                "rog5.netroot=0",
                b"staging is not a network-root profile",
            ),
            (
                "rog5.target_timeout=600",
                "rog5.target_timeout=599",
                b"staging target timeout is not 600 seconds",
            ),
            (
                "rog5.recovery_timeout=900",
                "rog5.recovery_timeout=899",
                b"staging rollback timeout is not 900 seconds",
            ),
        )
        for original, replacement, expected in cases:
            with self.subTest(replacement=replacement):
                fixture = AcceptanceFixture(self)
                try:
                    cmdline = fixture.root / "proc/cmdline"
                    cmdline.write_text(
                        cmdline.read_text(encoding="ascii").replace(
                            original,
                            replacement,
                        ),
                        encoding="ascii",
                    )
                    result = fixture.invoke("staging")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(fixture.report.exists())
                    self.assertEqual(
                        fixture.invocations.read_text(
                            encoding="ascii"
                        ),
                        "",
                    )
                finally:
                    fixture.cleanup()

    def test_staging_root_mount_and_upper_are_fail_closed(self) -> None:
        def wrong_source(fixture: AcceptanceFixture) -> None:
            mountinfo = fixture.root / "proc/self/mountinfo"
            mountinfo.write_text(
                mountinfo.read_text(encoding="ascii").replace(
                    "169.254.77.1:/",
                    "169.254.77.1:/other",
                ),
                encoding="ascii",
            )

        def critical_upper(fixture: AcceptanceFixture) -> None:
            (
                fixture.root / ".rog5/state/upper/usr"
            ).mkdir()

        def detached_overlay_lower(fixture: AcceptanceFixture) -> None:
            mountinfo = fixture.root / "proc/self/mountinfo"
            mountinfo.write_text(
                mountinfo.read_text(encoding="ascii").replace(
                    "lowerdir=/mnt/root-ro",
                    "lowerdir=/mnt/untrusted-root",
                ),
                encoding="ascii",
            )

        def replaced_visible_lower_mount(
            fixture: AcceptanceFixture,
        ) -> None:
            mountinfo = fixture.root / "proc/self/mountinfo"
            mountinfo.write_text(
                mountinfo.read_text(encoding="ascii").replace(
                    "21 20 0:21 / /.rog5/root-ro",
                    "31 20 0:21 / /.rog5/root-ro",
                ),
                encoding="ascii",
            )

        def trusted_tree_whiteout(fixture: AcceptanceFixture) -> None:
            (
                fixture.root / ".rog5/state/upper/.wh.etc"
            ).touch()

        cases = (
            (
                "wrong lower source",
                wrong_source,
                b"staging root mount inventory changed",
            ),
            (
                "critical upper override",
                critical_upper,
                b"volatile overlay can override the trusted runtime",
            ),
            (
                "detached overlay lower",
                detached_overlay_lower,
                b"staging overlay mount options changed",
            ),
            (
                "replaced visible lower mount",
                replaced_visible_lower_mount,
                b"network-root mount identity does not match runtime",
            ),
            (
                "critical upper whiteout",
                trusted_tree_whiteout,
                b"volatile overlay can override the trusted runtime",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                fixture = AcceptanceFixture(self)
                try:
                    mutate(fixture)
                    result = fixture.invoke("staging")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(fixture.report.exists())
                finally:
                    fixture.cleanup()

    def test_promoted_soak_provenance_mutations_fail_closed(self) -> None:
        def detached_overlay_lower(
            fixture: AcceptanceFixture,
        ) -> None:
            mountinfo = fixture.root / "proc/self/mountinfo"
            mountinfo.write_text(
                mountinfo.read_text(encoding="ascii").replace(
                    "lowerdir=/mnt/userdata/rog5/roots/arch-a",
                    "lowerdir=/mnt/userdata/rog5/roots/other",
                ),
                encoding="ascii",
            )

        def critical_upper(fixture: AcceptanceFixture) -> None:
            (fixture.root / ".rog5/state/upper/etc").mkdir()

        def replaced_visible_lower_mount(
            fixture: AcceptanceFixture,
        ) -> None:
            mountinfo = fixture.root / "proc/self/mountinfo"
            mountinfo.write_text(
                mountinfo.read_text(encoding="ascii").replace(
                    "21 20 8:23 / /.rog5/userdata-ro",
                    "31 20 8:23 / /.rog5/userdata-ro",
                ),
                encoding="ascii",
            )

        cases = (
            (
                "weak attestation mode",
                self._weaken_promotion_attestation,
                b"promotion attestation metadata is unsafe",
            ),
            (
                "wrong root source",
                self._change_promoted_root_source,
                b"promoted verification mount is unsafe",
            ),
            (
                "detached overlay lower",
                detached_overlay_lower,
                b"root mount inventory is not exact",
            ),
            (
                "replaced visible lower mount",
                replaced_visible_lower_mount,
                b"promoted root mount provenance changed",
            ),
            (
                "critical volatile override",
                critical_upper,
                b"volatile overlay can override the trusted runtime",
            ),
            (
                "NFS still mounted",
                self._append_promoted_nfs_mount,
                b"promoted root still has an NFS mount",
            ),
            (
                "extra block mount",
                self._append_promoted_block_mount,
                b"promoted block-device identity changed",
            ),
            (
                "network-root residue",
                self._restore_network_root_marker,
                b"soak still has rollback-root state",
            ),
            (
                "wrong attested bundle",
                self._change_attested_bundle,
                b"promotion attestation does not match runtime",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                fixture = AcceptanceFixture(self)
                try:
                    fixture.promote()
                    mutate(fixture)
                    result = fixture.invoke("soak")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(fixture.report.exists())
                    self.assertEqual(
                        fixture.invocations.read_text(
                            encoding="ascii"
                        ),
                        "",
                    )
                finally:
                    fixture.cleanup()

    def test_promoted_root_requires_matching_block_identity(self) -> None:
        cases = (
            (
                "verification major-minor mismatch",
                self._change_verification_device,
                b"root mount inventory is not exact",
            ),
            (
                "resolved block name mismatch",
                self._change_resolved_block_name,
                b"promoted block-device identity changed",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                fixture = AcceptanceFixture(self)
                try:
                    fixture.promote()
                    mutate(fixture)
                    result = fixture.invoke("soak")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(fixture.report.exists())
                finally:
                    fixture.cleanup()

    @staticmethod
    def _promotion_path(fixture: AcceptanceFixture) -> Path:
        return (
            fixture.root
            / "run/rog5-persistent-promotion.attestation"
        )

    @classmethod
    def _weaken_promotion_attestation(
        cls,
        fixture: AcceptanceFixture,
    ) -> None:
        cls._promotion_path(fixture).chmod(0o444)

    @staticmethod
    def _change_promoted_root_source(
        fixture: AcceptanceFixture,
    ) -> None:
        mountinfo = fixture.root / "proc/self/mountinfo"
        mountinfo.write_text(
            mountinfo.read_text(encoding="ascii").replace(
                "/dev/sda23",
                "/dev/sda24",
                1,
            ),
            encoding="ascii",
        )

    @staticmethod
    def _append_promoted_nfs_mount(
        fixture: AcceptanceFixture,
    ) -> None:
        mountinfo = fixture.root / "proc/self/mountinfo"
        with mountinfo.open("a", encoding="ascii") as stream:
            stream.write(
                "21 20 0:21 / /lower ro "
                "- nfs 169.254.77.1:/ ro\n"
            )

    @staticmethod
    def _append_promoted_block_mount(
        fixture: AcceptanceFixture,
    ) -> None:
        (
            fixture.root / "sys/dev/block/8:24"
        ).symlink_to(
            fixture.root / "sys/devices/mock/block/sda/sda24",
            target_is_directory=True,
        )
        mountinfo = fixture.root / "proc/self/mountinfo"
        with mountinfo.open("a", encoding="ascii") as stream:
            stream.write(
                "22 20 8:24 / /mnt/other ro "
                "- ext4 /dev/sda24 ro\n"
            )

    @staticmethod
    def _change_verification_device(
        fixture: AcceptanceFixture,
    ) -> None:
        (
            fixture.root / "sys/dev/block/8:24"
        ).symlink_to(
            fixture.root / "sys/devices/mock/block/sda/sda23",
            target_is_directory=True,
        )
        mountinfo = fixture.root / "proc/self/mountinfo"
        mountinfo.write_text(
            mountinfo.read_text(encoding="ascii").replace(
                "21 20 8:23",
                "21 20 8:24",
            ),
            encoding="ascii",
        )

    @staticmethod
    def _change_resolved_block_name(
        fixture: AcceptanceFixture,
    ) -> None:
        identity = fixture.root / "sys/dev/block/8:23"
        identity.unlink()
        identity.symlink_to(
            fixture.root / "sys/devices/mock/block/sda/sda24",
            target_is_directory=True,
        )

    @staticmethod
    def _restore_network_root_marker(
        fixture: AcceptanceFixture,
    ) -> None:
        (
            fixture.root / "run/rog5-network-root-source"
        ).write_text("169.254.77.1:/\n", encoding="ascii")

    @classmethod
    def _change_attested_bundle(
        cls,
        fixture: AcceptanceFixture,
    ) -> None:
        path = cls._promotion_path(fixture)
        path.chmod(0o600)
        path.write_text(
            path.read_text(encoding="ascii").replace(
                "bundle=a660-promoted-test",
                "bundle=other-promoted-test",
            ),
            encoding="ascii",
        )
        path.chmod(0o400)

    def test_guard_refuses_before_any_acceptance_command(self) -> None:
        environment = self.fixture.environment("staging")
        environment.pop("ALLOW_A660_STAGING_ACCEPTANCE")
        result = self.fixture.invoke("staging", environment=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"set ALLOW_A660_STAGING_ACCEPTANCE=1",
            result.stderr,
        )
        self.assertEqual(
            self.fixture.invocations.read_text(encoding="ascii"),
            "",
        )
        self.assertFalse(self.fixture.report.exists())

    def test_software_renderer_and_new_iommu_fault_fail_closed(self) -> None:
        self.fixture.commands["vulkaninfo"].write_text(
            "#!/bin/sh\n"
            "echo 'driverName = lavapipe'\n"
            "echo 'deviceName = llvmpipe'\n",
            encoding="ascii",
        )
        self.fixture.commands["vulkaninfo"].chmod(0o755)
        result = self.fixture.invoke("staging")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"vulkaninfo did not select hardware A660",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

        self.fixture.cleanup()
        self.fixture = AcceptanceFixture(self)
        environment = self.fixture.environment("staging")
        environment["ROG5_TEST_INJECT_FAULT"] = "1"
        result = self.fixture.invoke("staging", environment=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"kernel log contains a new GPU failure",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())
        self.assertEqual(
            (
                self.fixture.root
                / "run/rog5-screen-state"
            ).read_text(encoding="ascii"),
            "off\n",
        )

    def test_preflight_rejects_kgsl_and_wrong_render_driver(self) -> None:
        kgsl = self.fixture.root / "dev/kgsl-3d0"
        kgsl.write_bytes(b"vendor")
        result = self.fixture.invoke("preflight")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"vendor KGSL node is present", result.stderr)
        kgsl.unlink()

        driver = (
            self.fixture.root
            / "sys/class/drm/renderD128/device/driver"
        )
        driver.unlink()
        (self.fixture.root / "drivers/kgsl").mkdir()
        driver.symlink_to(
            self.fixture.root / "drivers/kgsl",
            target_is_directory=True,
        )
        result = self.fixture.invoke("preflight")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"renderD128 is not bound to msm", result.stderr)

    def test_cli_source_has_no_runtime_test_override_surface(self) -> None:
        source = TARGET.read_bytes()
        self.assertNotIn(b"ROG5_A660_TEST_", source)
        self.assertNotIn(b"ROG5_A660_TESTING", source)
        self.assertNotIn(b"os.killpg", source)
        self.assertIn(b"fixture=False", source)
        self.assertIn(b'root=Path("/")', source)
        with (
            mock.patch.dict(
                os.environ,
                {
                    "EXPECTED_KERNEL_RELEASE": os.uname().release,
                    "ROG5_A660_TEST_ROOT": str(self.fixture.root),
                    "ROG5_A660_TEST_SCREEN": "/tmp/malicious",
                },
                clear=True,
            ),
            mock.patch.object(
                ACCEPTANCE,
                "host_cmdline_value",
                return_value="a" * 64,
            ),
            mock.patch.object(
                ACCEPTANCE,
                "parse_command_manifest",
                return_value={
                    "format": "rog5-a660-command-manifest-v1",
                    **{
                        f"{name}_sha256": "a" * 64
                        for name in ACCEPTANCE.COMMAND_ORDER
                    },
                },
            ),
            mock.patch.object(
                ACCEPTANCE,
                "trusted_command",
                side_effect=lambda name, path, digest: (
                    ACCEPTANCE.TrustedCommand(
                        name=name,
                        path=path,
                        descriptor=-1,
                        sha256=digest,
                    )
                ),
            ),
        ):
            config = ACCEPTANCE.configuration("staging")
        self.assertFalse(config.fixture)
        self.assertEqual(config.root, Path("/"))
        self.assertEqual(
            config.commands["screen"].path,
            Path("/usr/local/bin/rog5-screen-toggle.sh"),
        )
        self.assertEqual(config.staging_deadline_seconds, 540)
        fixture_config = self.fixture.configuration("preflight")
        try:
            with self.assertRaisesRegex(
                ACCEPTANCE.AcceptanceError,
                "production runner rejects fixture",
            ):
                ACCEPTANCE.run_configuration(fixture_config)
        finally:
            ACCEPTANCE.close_commands(fixture_config)

    def test_production_command_environment_is_sanitized(self) -> None:
        path = Path("/usr/bin/env")
        command = ACCEPTANCE.trusted_command(
            "env",
            path,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        base_config = self.fixture.configuration("preflight")
        runner = base_config.commands["runner"]
        base_config.commands.pop("runner")
        try:
            config = replace(
                base_config,
                fixture=False,
                root=Path("/"),
                command_manifest_sha256="e" * 64,
                commands={"env": command, "runner": runner},
            )
        finally:
            ACCEPTANCE.close_commands(base_config)
        caller_environment = {
            "PATH": "/malicious",
            "LD_PRELOAD": "/malicious/library.so",
            "ROG5_METRICS_ROOT": "/malicious",
        }
        session = ACCEPTANCE.Session(
            identity=ACCEPTANCE.ProcessIdentity(
                pid=os.getpid(),
                uid=os.geteuid(),
                start_time_ticks=1,
                pidfd=None,
            ),
            user="fixture",
            group=os.getegid(),
            supplementary_groups=tuple(sorted(set(os.getgroups()))),
            home=str(self.fixture.base),
            environment={},
        )
        try:
            with mock.patch.dict(
                os.environ,
                caller_environment,
                clear=True,
            ):
                output = ACCEPTANCE.run_command(
                    config,
                    "env",
                    timeout=5,
                    session=session,
                )
        finally:
            ACCEPTANCE.close_commands(config)
        observed = {
            line.partition(b"=")[0]: line.partition(b"=")[2]
            for line in output.splitlines()
        }
        self.assertEqual(
            observed,
            {
                name.encode("ascii"): value.encode("ascii")
                for name, value in ACCEPTANCE.ROOT_ENVIRONMENT.items()
            },
        )

    def test_watchdog_identity_and_descriptors_are_pinned(self) -> None:
        cases = (
            (
                "zero PID",
                self._zero_watchdog_pid,
                b"rollback watchdog pid is not canonical",
            ),
            (
                "wrong executable",
                lambda fixture: (
                    fixture.root / "proc/999/comm"
                ).write_text("sleep\n", encoding="ascii"),
                b"process name changed",
            ),
            (
                "stopped process",
                lambda fixture: (
                    fixture.root / "proc/999/stat"
                ).write_text(
                    fixture.process_stat(
                        999, "init", 1, 900, state="T"
                    ),
                    encoding="ascii",
                ),
                b"process is not runnable",
            ),
            (
                "wrong descriptor",
                self._replace_watchdog_log_descriptor,
                b"rollback watchdog descriptors changed",
            ),
            (
                "read-only descriptor",
                self._make_watchdog_descriptor_read_only,
                b"rollback watchdog descriptors changed",
            ),
            (
                "wrong watchdog executable",
                self._replace_watchdog_executable,
                b"rollback watchdog executable changed",
            ),
            (
                "stopped timer",
                lambda fixture: (
                    fixture.root / "proc/1000/stat"
                ).write_text(
                    fixture.process_stat(
                        1000,
                        "sleep",
                        999,
                        905,
                        state="T",
                    ),
                    encoding="ascii",
                ),
                b"process is not runnable",
            ),
            (
                "timer parent changed",
                lambda fixture: (
                    fixture.root / "proc/1000/stat"
                ).write_text(
                    fixture.process_stat(1000, "sleep", 1, 905),
                    encoding="ascii",
                ),
                b"process parent changed",
            ),
            (
                "insufficient remaining time",
                lambda fixture: (
                    fixture.root / "proc/uptime"
                ).write_text("951.00 900.00\n", encoding="ascii"),
                b"rollback watchdog has insufficient time remaining",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                fixture = AcceptanceFixture(self)
                try:
                    mutate(fixture)
                    result = fixture.invoke("staging")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(fixture.report.exists())
                    self.assertEqual(
                        fixture.invocations.read_text(
                            encoding="ascii"
                        ),
                        "",
                    )
                finally:
                    fixture.cleanup()

    def test_watchdog_control_files_are_pinned_and_private(self) -> None:
        cases = (
            (
                "writable lease",
                lambda fixture: (
                    fixture.root
                    / "run/rog5-network-root-watchdog.lease"
                ).chmod(0o600),
                b"rollback watchdog lease metadata is unsafe",
            ),
            (
                "linked pid",
                self._link_watchdog_pid,
                b"cannot read rollback watchdog PID",
            ),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                fixture = AcceptanceFixture(self)
                try:
                    mutate(fixture)
                    result = fixture.invoke("staging")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(fixture.report.exists())
                finally:
                    fixture.cleanup()

    @staticmethod
    def _link_watchdog_pid(fixture: AcceptanceFixture) -> None:
        pid_path = (
            fixture.root / "run/rog5-network-root-watchdog.pid"
        )
        pid_path.unlink()
        pid_path.symlink_to("rog5-network-root-watchdog.lease")

    @staticmethod
    def _zero_watchdog_pid(
        fixture: AcceptanceFixture,
    ) -> None:
        pid_path = (
            fixture.root
            / "run/rog5-network-root-watchdog.pid"
        )
        pid_path.chmod(0o600)
        pid_path.write_text("0\n", encoding="ascii")
        pid_path.chmod(0o400)
        lease = fixture.root / "run/rog5-network-root-watchdog.lease"
        lease.chmod(0o600)
        lease.write_text(
            lease.read_text(encoding="ascii").replace(
                "pid=999\n",
                "pid=0\n",
                1,
            ),
            encoding="ascii",
        )
        lease.chmod(0o400)

    @staticmethod
    def _replace_watchdog_log_descriptor(
        fixture: AcceptanceFixture,
    ) -> None:
        descriptor = fixture.root / "proc/999/fd/8"
        descriptor.unlink()
        descriptor.symlink_to("/dev/null")

    @staticmethod
    def _make_watchdog_descriptor_read_only(
        fixture: AcceptanceFixture,
    ) -> None:
        (
            fixture.root / "proc/999/fdinfo/8"
        ).write_text(
            "pos:\t0\nflags:\t0100000\n",
            encoding="ascii",
        )

    @staticmethod
    def _replace_watchdog_executable(
        fixture: AcceptanceFixture,
    ) -> None:
        executable = fixture.root / "proc/999/exe"
        executable.unlink()
        executable.symlink_to("/usr/bin/python3")

    def test_watchdog_and_kwin_pid_reuse_fail_closed(self) -> None:
        for variable in (
            "ROG5_FIXTURE_REUSE_WATCHDOG",
            "ROG5_FIXTURE_REUSE_KWIN",
        ):
            with self.subTest(variable=variable):
                fixture = AcceptanceFixture(self)
                try:
                    environment = fixture.environment("staging")
                    environment[variable] = "1"
                    result = fixture.invoke(
                        "staging",
                        environment=environment,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        b"pinned process identity changed",
                        result.stderr,
                    )
                    self.assertFalse(
                        (fixture.report / "result").exists()
                    )
                finally:
                    fixture.cleanup()

    def test_kernel_failure_signatures_fail_closed(self) -> None:
        signatures = (
            "[ 10.0] msm_drm: error atomic commit",
            "[ 10.0] Unable to handle kernel paging request",
            "[ 10.0] Synchronous External Abort",
            "[ 10.0] apps watchdog bite",
        )
        for signature in signatures:
            with self.subTest(signature=signature):
                fixture = AcceptanceFixture(self)
                try:
                    environment = fixture.environment("staging")
                    environment.update(
                        {
                            "ROG5_TEST_INJECT_FAULT": "1",
                            "ROG5_FIXTURE_FAULT_LINE": signature,
                        }
                    )
                    result = fixture.invoke(
                        "staging",
                        environment=environment,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        b"kernel log contains a new GPU failure",
                        result.stderr,
                    )
                    self.assertFalse(
                        (fixture.report / "result").exists()
                    )
                finally:
                    fixture.cleanup()

    def test_boot_time_kernel_failure_fails_closed(self) -> None:
        self.fixture.dmesg.write_text(
            "[    0.0] Linux booted\n"
            "[    1.0] adreno GPU timeout during boot\n",
            encoding="ascii",
        )
        result = self.fixture.invoke("staging")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"kernel log baseline contains a GPU failure",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

    def test_bare_forbidden_cmdline_tokens_fail_closed(self) -> None:
        for token in (
            "rog5.persistent_ro",
            "rog5.persistent_promoted",
            "rog5.ufs_discovery",
        ):
            with self.subTest(token=token):
                fixture = AcceptanceFixture(self)
                try:
                    cmdline = fixture.root / "proc/cmdline"
                    payload = cmdline.read_text(encoding="ascii").strip()
                    cmdline.write_text(
                        f"{payload} {token}\n",
                        encoding="ascii",
                    )
                    result = fixture.invoke("staging")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        (
                            "kernel command line unexpectedly has "
                            f"{token}"
                        ).encode("ascii"),
                        result.stderr,
                    )
                finally:
                    fixture.cleanup()

    def test_required_signed_cmdline_families_reject_bare_or_duplicate(
        self,
    ) -> None:
        families = (
            "rog5.a660_command_manifest_sha256",
            "rog5.root_generation",
            "rog5.root_tree_sha256",
            "rog5.root_seal_sha256",
            "rog5.root_tree_entries",
            "rog5.root_subtree",
        )
        for family in families:
            for mutation in ("bare", "duplicate"):
                with self.subTest(family=family, mutation=mutation):
                    fixture = AcceptanceFixture(self)
                    try:
                        cmdline = fixture.root / "proc/cmdline"
                        payload = cmdline.read_text(
                            encoding="ascii"
                        ).strip()
                        original = next(
                            token
                            for token in payload.split()
                            if token.startswith(f"{family}=")
                        )
                        added = family if mutation == "bare" else original
                        cmdline.write_text(
                            f"{payload} {added}\n",
                            encoding="ascii",
                        )
                        result = fixture.invoke("staging")
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(
                            (
                                "kernel command line does not bind "
                                f"{family}"
                            ).encode("ascii"),
                            result.stderr,
                        )
                    finally:
                        fixture.cleanup()

    def test_promoted_required_cmdline_families_reject_bare_duplicate(
        self,
    ) -> None:
        for family in (
            "rog5.persistent_promoted",
            "rog5.ufs_discovery",
            "rog5.root_device",
        ):
            with self.subTest(family=family):
                fixture = AcceptanceFixture(self)
                try:
                    fixture.promote()
                    cmdline = fixture.root / "proc/cmdline"
                    payload = cmdline.read_text(encoding="ascii").strip()
                    cmdline.write_text(
                        f"{payload} {family}\n",
                        encoding="ascii",
                    )
                    result = fixture.invoke("soak")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        (
                            "kernel command line does not bind "
                            f"{family}"
                        ).encode("ascii"),
                        result.stderr,
                    )
                finally:
                    fixture.cleanup()

    def test_wayland_workload_requires_finite_frames(self) -> None:
        environment = self.fixture.environment("staging")
        environment["ROG5_FIXTURE_VKCUBE_HANG"] = "1"
        result = self.fixture.invoke(
            "staging",
            environment=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"fixed acceptance command timed out",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

    def test_screen_off_dpms_is_rechecked_during_workload(self) -> None:
        environment = self.fixture.environment("staging")
        environment["ROG5_FIXTURE_BREAK_DPMS"] = "1"
        result = self.fixture.invoke(
            "staging",
            environment=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"screen DPMS state does not match",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

    def test_transient_screen_wake_is_caught_by_continuous_monitor(
        self,
    ) -> None:
        environment = self.fixture.environment("staging")
        environment["ROG5_FIXTURE_TRANSIENT_DPMS"] = "1"
        result = self.fixture.invoke(
            "staging",
            environment=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"screen did not remain physically off",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

    def test_late_screen_wake_cannot_publish_passing_result(self) -> None:
        original_write = ACCEPTANCE.write_private

        def wake_after_pending(
            config: ACCEPTANCE.Configuration,
            name: str,
            payload: bytes,
        ) -> None:
            original_write(config, name, payload)
            if name == ".result.pending":
                (
                    self.fixture.root
                    / "sys/class/backlight/panel0-backlight/brightness"
                ).write_text("100\n", encoding="ascii")

        with mock.patch.object(
            ACCEPTANCE,
            "write_private",
            side_effect=wake_after_pending,
        ):
            result = self.fixture.invoke("staging")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            b"screen did not remain physically off" in result.stderr
            or b"screen did not enter off state" in result.stderr,
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())
        self.assertFalse(
            (self.fixture.report / ".result.pending").exists()
        )

    def test_post_link_failures_retract_passing_result(self) -> None:
        for boundary in ("pending-unlink", "directory-open", "directory-fsync"):
            with self.subTest(boundary=boundary):
                fixture = AcceptanceFixture(self)
                real_unlink = ACCEPTANCE.os.unlink
                real_open = ACCEPTANCE.os.open
                real_fsync = ACCEPTANCE.os.fsync
                failed = False

                def unlink_once(path: os.PathLike[str] | str) -> None:
                    nonlocal failed
                    if (
                        boundary == "pending-unlink"
                        and not failed
                        and Path(path).name == ".result.pending"
                    ):
                        failed = True
                        raise OSError("injected pending unlink failure")
                    real_unlink(path)

                def open_once(
                    path: os.PathLike[str] | str,
                    flags: int,
                    mode: int = 0o777,
                    *,
                    dir_fd: int | None = None,
                ) -> int:
                    nonlocal failed
                    if (
                        boundary == "directory-open"
                        and not failed
                        and Path(path) == fixture.report
                        and flags & os.O_DIRECTORY
                    ):
                        failed = True
                        raise OSError("injected directory open failure")
                    if dir_fd is None:
                        return real_open(path, flags, mode)
                    return real_open(path, flags, mode, dir_fd=dir_fd)

                def fsync_once(descriptor: int) -> None:
                    nonlocal failed
                    if (
                        boundary == "directory-fsync"
                        and not failed
                        and stat.S_ISDIR(os.fstat(descriptor).st_mode)
                    ):
                        failed = True
                        raise OSError("injected directory fsync failure")
                    real_fsync(descriptor)

                try:
                    with (
                        mock.patch.object(
                            ACCEPTANCE.os,
                            "unlink",
                            side_effect=unlink_once,
                        ),
                        mock.patch.object(
                            ACCEPTANCE.os,
                            "open",
                            side_effect=open_once,
                        ),
                        mock.patch.object(
                            ACCEPTANCE.os,
                            "fsync",
                            side_effect=fsync_once,
                        ),
                    ):
                        result = fixture.invoke("staging")
                    self.assertTrue(failed)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(
                        (fixture.report / "result").exists()
                    )
                    self.assertFalse(
                        (fixture.report / ".result.pending").exists()
                    )
                finally:
                    fixture.cleanup()

    def test_promoted_root_tree_is_recomputed(self) -> None:
        self.fixture.promote()
        environment = self.fixture.environment("soak")
        environment["ROG5_FIXTURE_ROOT_TREE"] = "e" * 64
        result = self.fixture.invoke("soak", environment=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"runtime root tree verification did not match signed identity",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

    def test_runtime_root_is_recomputed_after_workload(self) -> None:
        environment = self.fixture.environment("staging")
        environment["ROG5_FIXTURE_ROOT_TREE_AFTER_FIRST"] = "1"
        result = self.fixture.invoke(
            "staging",
            environment=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"runtime root tree verification did not match signed identity",
            result.stderr,
        )
        self.assertFalse((self.fixture.report / "result").exists())

    def test_plasma_inventory_must_match_collector(self) -> None:
        environment = self.fixture.environment("staging")
        environment["ROG5_FIXTURE_PLASMA_COUNT"] = "2"
        result = self.fixture.invoke(
            "staging",
            environment=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            b"Plasma PSS evidence is incomplete",
            result.stderr,
        )

        fixture = AcceptanceFixture(self)
        try:
            process = fixture.root / "proc/101"
            process.mkdir()
            (process / "status").write_text(
                "Name:\tplasmashell\n",
                encoding="ascii",
            )
            result = fixture.invoke("staging")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                b"cannot read Plasma process PSS",
                result.stderr,
            )
        finally:
            fixture.cleanup()

    def test_command_output_and_process_tree_are_bounded(self) -> None:
        config = self.fixture.configuration("preflight")
        old = config.commands["systemctl"]
        os.close(old.descriptor)
        burst = self.fixture.script(
            "bounded-output",
            "dd if=/dev/zero bs=1048576 count=5 2>/dev/null",
        )
        config.commands["systemctl"] = (
            self.fixture.trusted_fixture_command("systemctl", burst)
        )
        try:
            with self.assertRaisesRegex(
                ACCEPTANCE.AcceptanceError,
                "command output exceeds policy",
            ):
                ACCEPTANCE.run_command(
                    config,
                    "systemctl",
                    timeout=5,
                )
        finally:
            ACCEPTANCE.close_commands(config)

        child_pid = self.fixture.base / "child-pid"
        config = self.fixture.configuration("preflight")
        old = config.commands["systemctl"]
        os.close(old.descriptor)
        sleeper = self.fixture.script(
            "bounded-time",
            "setsid sh -c "
            + shlex.quote(
                "printf '%s\\n' \"$$\" > "
                f"{shlex.quote(str(child_pid))}; exec sleep 30"
            )
            + " &\nwait",
        )
        config.commands["systemctl"] = (
            self.fixture.trusted_fixture_command("systemctl", sleeper)
        )
        try:
            with self.assertRaisesRegex(
                ACCEPTANCE.AcceptanceError,
                "fixed acceptance command timed out",
            ):
                ACCEPTANCE.run_command(
                    config,
                    "systemctl",
                    timeout=0.1,
                )
        finally:
            ACCEPTANCE.close_commands(config)
        pid = int(child_pid.read_text(encoding="ascii"))
        for _attempt in range(100):
            if not Path(f"/proc/{pid}").exists():
                break
            time.sleep(0.01)
        else:
            self.fail("timed-out command left a setsid descendant")
        parent = ACCEPTANCE.current_command_cgroup()
        self.assertEqual(
            list(parent.glob(f"rog5-a660-{os.getpid()}-*")),
            [],
        )

    def test_noncanonical_telemetry_fails_closed(self) -> None:
        cases = (
            (
                "ROG5_FIXTURE_PLASMA_PSS",
                "unavailable",
                b"plasma_pss_kib is not a canonical integer",
            ),
            (
                "ROG5_FIXTURE_PLASMA_PSS",
                "--1",
                b"plasma_pss_kib is not a canonical integer",
            ),
            (
                "ROG5_FIXTURE_BATTERY_CAPACITY",
                "101",
                b"battery_capacity_percent is outside policy",
            ),
            (
                "ROG5_FIXTURE_BATTERY_STATUS",
                "Broken",
                b"battery status is not canonical",
            ),
        )
        for variable, value, expected in cases:
            with self.subTest(variable=variable, value=value):
                fixture = AcceptanceFixture(self)
                try:
                    environment = fixture.environment("staging")
                    environment[variable] = value
                    result = fixture.invoke(
                        "staging",
                        environment=environment,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)
                    self.assertFalse(
                        (fixture.report / "result").exists()
                    )
                finally:
                    fixture.cleanup()


    def test_cgroup_runner_is_descriptor_only_and_shell_free(self) -> None:
        source = RUNNER_SOURCE.read_bytes()
        for required in (
            b"F_GET_SEALS",
            b"cgroup descriptor",
            b"setresgid",
            b"setresuid",
            b"fexecve",
        ):
            self.assertIn(required, source)
        for forbidden in (
            b"system(",
            b"execvp",
            b"execvpe",
            b"/bin/sh",
            b"/usr/bin/env",
            b"killpg",
        ):
            self.assertNotIn(forbidden, source)

    def test_actual_persistent_verifier_runs_as_sealed_command(
        self,
    ) -> None:
        root = self.fixture.base / "actual-root"
        (root / "etc/rog5").mkdir(parents=True)
        (root / "usr/lib/rog5").mkdir(parents=True)
        (root / "etc/rog5/build").write_bytes(b"fixture\n")
        (root / "usr/lib/rog5/payload").write_bytes(b"payload\n")
        seal = root / ".rog5-persistent-seal"
        seal.touch()
        tree_report = subprocess.check_output(
            [str(PERSISTENT_ROOT_TOOL), "seal", str(root)],
            cwd=REPO,
            text=True,
        ).strip()
        seal.write_text(
            "seal_format=rog5-persistent-root-v1\n"
            "generation=arch-a\n"
            "source_archive_size=1\n"
            f"source_archive_sha256={'0' * 64}\n"
            "promotion_state=UNBOOTED\n"
            f"{tree_report}\n",
            encoding="ascii",
        )
        seal.chmod(0o444)
        seal_hash = hashlib.sha256(seal.read_bytes()).hexdigest()
        config = self.fixture.configuration("preflight")
        old = config.commands["root_verify"]
        os.close(old.descriptor)
        config.commands["root_verify"] = (
            self.fixture.trusted_fixture_command(
                "root_verify",
                self.persistent_verifier,
            )
        )
        try:
            output = ACCEPTANCE.run_command(
                config,
                "root_verify",
                [str(root), str(seal), seal_hash],
                timeout=10,
            )
            self.assertRegex(
                output,
                rb"^PASS persistent root matches anchored seal "
                rb"entries=[1-9][0-9]* tree_sha256=[0-9a-f]{64}\n$",
            )
            (root / "usr/lib/rog5/payload").write_bytes(b"mutated\n")
            with self.assertRaisesRegex(
                ACCEPTANCE.AcceptanceError,
                "fixed acceptance command failed",
            ):
                ACCEPTANCE.run_command(
                    config,
                    "root_verify",
                    [str(root), str(seal), seal_hash],
                    timeout=10,
                )
        finally:
            ACCEPTANCE.close_commands(config)


class VulkanSubmitSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("gcc", "pkg-config", "strings"):
            if shutil.which(command) is None:
                raise RuntimeError(f"{command} is required")
        if subprocess.run(
            ["pkg-config", "--exists", "vulkan"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode != 0:
            raise RuntimeError("Vulkan development package is required")
        vulkan_cflags = shlex.split(
            subprocess.check_output(
                ["pkg-config", "--cflags", "vulkan"],
                text=True,
            )
        )
        cls.temporary = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temporary.name) / "rog5-vulkan-submit"
        cls.fake_binary = (
            Path(cls.temporary.name) / "rog5-vulkan-submit-fake"
        )
        subprocess.run(
            [
                "gcc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                *vulkan_cflags,
                str(SUBMIT_SOURCE),
                str(FAKE_VULKAN),
                "-o",
                str(cls.fake_binary),
            ],
            cwd=REPO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        result = subprocess.run(
            [str(SUBMIT_BUILD), str(cls.binary)],
            cwd=REPO,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        if (
            b"format=rog5-vulkan-submit-build-v1\n" not in result.stdout
            or b"sha256=" not in result.stdout
        ):
            raise RuntimeError("unexpected helper build record")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_helper_source_is_fixed_a660_only(self) -> None:
        self.assertTrue(os.access(SUBMIT_BUILD, os.X_OK))
        source = SUBMIT_SOURCE.read_bytes()
        for required in (
            b"Adreno (TM) 660",
            b"Adreno 660",
            b"FD660",
            b"vkQueueSubmit",
            b"vkWaitForFences",
            b"submit=pass",
            b"FENCE_TIMEOUT_NS",
        ):
            self.assertIn(required, source)
        for forbidden in (
            b"/dev/kgsl-3d0",
            b"fastboot",
            b"/dev/sda",
            b"http://",
            b"https://",
        ):
            self.assertNotIn(forbidden, source)

    def test_helper_compiles_and_requires_explicit_mode(self) -> None:
        result = subprocess.run(
            [str(self.binary)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"--require-a660", result.stderr)
        strings = subprocess.check_output(
            ["strings", "-a", str(self.binary)],
            cwd=REPO,
        )
        for required in (
            b"Adreno (TM) 660",
            b"Adreno 660",
            b"FD660",
            b"vkQueueSubmit",
            b"vkWaitForFences",
            b"submit=pass",
        ):
            self.assertIn(required, strings)
        for forbidden in (
            b"/dev/kgsl-3d0",
            b"fastboot",
            b"/dev/sda",
            b"http://",
            b"https://",
        ):
            self.assertNotIn(forbidden, strings)

    def test_helper_core_fault_matrix_with_fake_vulkan(self) -> None:
        cases = (
            (
                "success",
                0,
                b"device_name=Turnip Adreno (TM) 660\n",
            ),
            (
                "none",
                1,
                b"expected exactly one A660 physical device count=0",
            ),
            (
                "duplicate",
                1,
                b"expected exactly one A660 physical device count=2",
            ),
            (
                "no_queue",
                1,
                b"A660 has no graphics or compute queue",
            ),
            (
                "submit_fail",
                1,
                b"FAIL vkQueueSubmit result=",
            ),
            (
                "wait_timeout",
                1,
                b"FAIL vkWaitForFences result=",
            ),
        )
        for mode, expected_status, expected in cases:
            with self.subTest(mode=mode):
                environment = {
                    **os.environ,
                    "ROG5_FAKE_VULKAN_MODE": mode,
                }
                result = subprocess.run(
                    [str(self.fake_binary), "--require-a660"],
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    check=False,
                )
                self.assertEqual(result.returncode, expected_status)
                self.assertIn(
                    expected,
                    result.stdout + result.stderr,
                )
                if mode == "success":
                    self.assertIn(b"submit=pass\n", result.stdout)

    def test_builder_publication_is_atomic_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "contended-output"
            counter = root / "compiler-count"
            wrapper = root / "compiler"
            real_compiler = shutil.which("gcc")
            self.assertIsNotNone(real_compiler)
            wrapper.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                f"{shlex.quote(str(real_compiler))} \"$@\"\n"
                "count=0\n"
                f"[ ! -f {shlex.quote(str(counter))} ] || "
                f"read -r count < {shlex.quote(str(counter))}\n"
                "count=$((count + 1))\n"
                f"printf '%s\\n' \"$count\" > "
                f"{shlex.quote(str(counter))}\n"
                "if [ \"$count\" -eq 2 ]; then\n"
                "    printf 'competitor\\n' > \"$RACE_OUTPUT\"\n"
                "fi\n",
                encoding="ascii",
            )
            wrapper.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "CC": str(wrapper),
                    "RACE_OUTPUT": str(output),
                }
            )
            result = subprocess.run(
                [str(SUBMIT_BUILD), str(output)],
                cwd=REPO,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                b"output appeared during build",
                result.stderr,
            )
            self.assertEqual(output.read_bytes(), b"competitor\n")
            self.assertEqual(
                list(root.glob(".rog5-vulkan-submit.*")),
                [],
            )

    def test_builder_rejects_unsafe_output_parents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            writable = root / "writable"
            real = root / "real"
            linked = root / "linked"
            writable.mkdir(mode=0o700)
            writable.chmod(0o777)
            real.mkdir(mode=0o700)
            linked.symlink_to(real, target_is_directory=True)
            cases = (
                (
                    writable / "helper",
                    b"output parent is group- or world-writable",
                ),
                (
                    linked / "helper",
                    b"output parent is absent or linked",
                ),
            )
            for output, expected in cases:
                with self.subTest(output=output):
                    result = subprocess.run(
                        [str(SUBMIT_BUILD), str(output)],
                        cwd=REPO,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
