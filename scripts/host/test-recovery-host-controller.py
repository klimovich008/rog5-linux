#!/usr/bin/env python3
"""Offline lifecycle tests for the privileged recovery-host controller."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPO = Path(__file__).resolve().parents[2]
CONTROLLER = (
    REPO / "packaging/host/rog5-recovery-bundle-controller"
)
INSTALLER = REPO / "scripts/host/install-recovery-host-controller.sh"
LAUNCHER = REPO / "scripts/host/run-recovery-bundle-server.sh"
BUNDLE = "arch-test-v1"
MANIFEST_HASH = "a" * 64


class ControllerFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-controller-test-"
        )
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.sys_net = self.root / "sys/class/net"
        self.sys_net.mkdir(parents=True)
        (self.sys_net / "usbtest0").mkdir()
        self.bundle_root = self.root / "bundles"
        self.bundle_root.mkdir(mode=0o700)
        self.bundle_root.chmod(0o700)
        self.lock = self.root / "controller.lock"
        self.calls = self.root / "calls"
        self.connection_state = self.root / "connection-down"
        self.pid = self.root / "server.pid"
        self.watchdog_pid = self.root / "watchdog.pid"
        self.server = self.root / "host_bundle_server.py"
        self.server.write_text(
            textwrap.dedent(
                """\
                import os
                import time

                if os.environ.get("MOCK_SERVER_EXIT") == "1":
                    raise SystemExit(1)
                time.sleep(float(os.environ.get("MOCK_SERVER_SLEEP", "0.2")))
                """
            ),
            encoding="utf-8",
        )
        self.server.chmod(0o555)
        self._write_mocks()

    def close(self) -> None:
        self.temporary.cleanup()

    def write_executable(self, name: str, payload: str) -> None:
        path = self.bin / name
        path.write_text(payload, encoding="utf-8")
        path.chmod(0o755)

    def _write_mocks(self) -> None:
        self.write_executable(
            "systemctl",
            """#!/bin/sh
printf 'systemctl %s\n' "$*" >>"$MOCK_CALLS"
[ "$1 $2" = "is-active --quiet" ]
""",
        )
        self.write_executable(
            "udevadm",
            """#!/bin/sh
printf 'udevadm %s\n' "$*" >>"$MOCK_CALLS"
[ "${MOCK_UDEV_MATCH:-1}" = 1 ] || exit 0
printf '%s\n' \
  'ID_VENDOR_ID=1d6b' \
  'ID_MODEL_ID=0104' \
  'ID_MODEL=ROG5_recovery' \
  'ID_NET_DRIVER=cdc_ncm'
""",
        )
        self.write_executable(
            "firewall-cmd",
            """#!/bin/sh
printf 'firewall-cmd %s\n' "$*" >>"$MOCK_CALLS"
case $* in
  *"${MOCK_FAIL_CONTAINS:-__never_match__}"*) exit 1 ;;
esac
case " $* " in
  *" --zone=drop --list-all "*)
    printf '%s\n' 'drop' '  target: DROP'
    ;;
  *" --get-zones "*) printf '%s\n' 'drop public trusted' ;;
  *" --get-zone-of-interface=usbtest0 "*) printf '%s\n' 'public' ;;
  *" --query-forward "*)
    [ "${MOCK_FORWARD_ENABLED:-1}" = 1 ]
    ;;
  *" --query-masquerade "*|*" --query-rich-rule="*)
    exit 1
    ;;
  *" --list-"*) ;;
  *) ;;
esac
""",
        )
        self.write_executable(
            "nmcli",
            """#!/bin/sh
printf 'nmcli %s\n' "$*" >>"$MOCK_CALLS"
case $* in
  *"${MOCK_FAIL_CONTAINS:-__never_match__}"*) exit 1 ;;
esac
if [ "$1 $2 $3" = "-g GENERAL.NM-MANAGED device" ]; then
  [ "${MOCK_LEGACY_MANAGED_FIELD:-0}" = 0 ] || exit 2
  printf '%s\n' yes
elif [ "$1 $2 $3" = "-g GENERAL.MANAGED device" ]; then
  printf '%s\n' yes
elif [ "$1 $2 $3" = "-g GENERAL.CON-UUID device" ]; then
  [ "${MOCK_FALLBACK_ADDRESS:-0}" = 1 ] &&
    printf '%s\n' '244dd128-e3b1-458e-9639-5e4ab4d8854f'
elif [ "$1 $2 $3" = "connection down uuid" ]; then
  : >"$MOCK_CONNECTION_STATE"
elif [ "$1 $2 $3" = "connection up uuid" ]; then
  rm -f "$MOCK_CONNECTION_STATE"
fi
""",
        )
        self.write_executable(
            "ip",
            """#!/bin/sh
printf 'ip %s\n' "$*" >>"$MOCK_CALLS"
case $* in
  *"${MOCK_FAIL_CONTAINS:-__never_match__}"*) exit 1 ;;
esac
case " $* " in
  *" -4 -o address show "*)
    if [ "${MOCK_FALLBACK_ADDRESS:-0}" = 1 ] &&
       [ ! -e "$MOCK_CONNECTION_STATE" ]; then
      printf '%s\n' \
        '15: usbtest0 inet 169.254.77.1/16 scope link usbtest0'
    fi
    ;;
  *) ;;
esac
""",
        )
        self.write_executable(
            "ss",
            """#!/bin/sh
printf 'ss %s\n' "$*" >>"$MOCK_CALLS"
if [ "${MOCK_LISTENER_EXISTING:-0}" = 1 ]; then
  printf '%s\n' \
    'LISTEN 0 1 0.0.0.0:8080 0.0.0.0:* users:(("other",pid=999,fd=3))'
elif [ -s "$MOCK_SERVER_PID" ]; then
  pid=$(sed -n '1p' "$MOCK_SERVER_PID")
  printf '%s\n' \
    "LISTEN 0 1 169.254.77.1:8080 0.0.0.0:* users:((\\"python3\\",pid=$pid,fd=3))"
fi
""",
        )
        self.write_executable(
            "setpriv",
            """#!/bin/sh
printf 'setpriv %s\n' "$*" >>"$MOCK_CALLS"
while [ "$#" -gt 0 ]; do
  case $1 in
    --) shift; break ;;
    --reuid|--regid|--pdeathsig) shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\n' "$$" >"$MOCK_SERVER_PID"
exec "$@"
""",
        )

    def environment(self, **overrides: str) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_CONTROLLER_OFFLINE_TEST": "1",
                "ROG5_TEST_PATH": (
                    f"{self.bin}:/usr/sbin:/usr/bin:/sbin:/bin"
                ),
                "ROG5_TEST_SYS_CLASS_NET": str(self.sys_net),
                "ROG5_TEST_SERVER_PATH": str(self.server),
                "ROG5_TEST_BUNDLE_ROOT": str(self.bundle_root),
                "ROG5_TEST_LOCK_PATH": str(self.lock),
                "MOCK_CALLS": str(self.calls),
                "MOCK_SERVER_PID": str(self.pid),
                "MOCK_CONNECTION_STATE": str(self.connection_state),
                "ROG5_TEST_WATCHDOG_PID_FILE": str(self.watchdog_pid),
            }
        )
        environment.update(overrides)
        return environment

    def run(
        self,
        *arguments: str,
        **overrides: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTROLLER), *arguments],
            env=self.environment(**overrides),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )

    def call_log(self) -> str:
        if not self.calls.exists():
            return ""
        return self.calls.read_text(encoding="utf-8")


class RecoveryHostControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ControllerFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_success_is_fixed_privilege_separated_and_fully_cleaned(self):
        result = self.fixture.run(BUNDLE, MANIFEST_HASH)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("server ready on 169.254.77.1:8080", result.stdout)
        self.assertIn("one recovery bundle transfer completed", result.stdout)
        self.assertIn("host network state removed", result.stdout)
        calls = self.fixture.call_log()
        self.assertIn(
            "firewall-cmd --zone=public --add-rich-rule=rule "
            'family="ipv4"',
            calls,
        )
        self.assertIn(
            "firewall-cmd --zone=trusted --add-rich-rule=rule "
            'family="ipv4"',
            calls,
        )
        self.assertIn(
            "firewall-cmd --zone=drop --change-interface=usbtest0",
            calls,
        )
        self.assertIn(
            "firewall-cmd --zone=drop --remove-forward",
            calls,
        )
        self.assertIn(
            "firewall-cmd --zone=drop --add-forward",
            calls,
        )
        self.assertIn(
            "firewall-cmd --zone=drop --add-rich-rule=rule "
            'family="ipv4"',
            calls,
        )
        self.assertIn("nmcli device set usbtest0 managed no", calls)
        self.assertIn("nmcli device set usbtest0 managed yes", calls)
        self.assertIn(
            "ip address add 169.254.77.1/30 dev usbtest0 "
            "valid_lft 180 preferred_lft 180",
            calls,
        )
        self.assertIn(
            "ip address del 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertIn(
            "firewall-cmd --zone=public --change-interface=usbtest0",
            calls,
        )
        self.assertIn("--remove-rich-rule=", calls)
        setpriv = next(
            line for line in calls.splitlines()
            if line.startswith("setpriv ")
        )
        for policy in (
            "--clear-groups",
            "--bounding-set=-all",
            "--inh-caps=-all",
            "--ambient-caps=-all",
            "--no-new-privs",
            "--pdeathsig TERM",
            "--reset-env",
        ):
            self.assertIn(policy, setpriv)

    def test_missing_or_duplicate_gadget_fails_before_mutation(self):
        missing = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_UDEV_MATCH="0",
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("found 0", missing.stderr)
        self.assertNotIn("--add-rich-rule=", self.fixture.call_log())

        self.fixture.close()
        self.fixture = ControllerFixture()
        (self.fixture.sys_net / "usbtest1").mkdir()
        duplicate = self.fixture.run(BUNDLE, MANIFEST_HASH)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("found 2", duplicate.stderr)
        self.assertNotIn("--add-rich-rule=", self.fixture.call_log())

    def test_existing_listener_fails_before_network_mutation(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_LISTENER_EXISTING="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already has a listener", result.stderr)
        calls = self.fixture.call_log()
        self.assertNotIn("--add-rich-rule=", calls)
        self.assertNotIn("ip address add", calls)

    def test_server_start_failure_rolls_back_every_created_state(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_SERVER_EXIT="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            "did not create its fixed listener" in result.stderr
            or "server failed with status 1" in result.stderr
        )
        calls = self.fixture.call_log()
        self.assertIn(
            "ip address add 169.254.77.1/30 dev usbtest0 "
            "valid_lft 180 preferred_lft 180",
            calls,
        )
        self.assertIn(
            "ip address del 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertIn("--remove-rich-rule=", calls)
        self.assertIn("nmcli device set usbtest0 managed yes", calls)

    def test_hard_watchdog_cleans_server_hung_after_listener(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_SERVER_SLEEP="10",
            ROG5_TEST_HARD_SERVER_TIMEOUT="1",
        )
        self.assertEqual(result.returncode, 130, result.stderr)
        calls = self.fixture.call_log()
        self.assertIn("setpriv ", calls)
        self.assertIn(
            "ip address del 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertIn("--remove-rich-rule=", calls)
        self.assertIn("nmcli device set usbtest0 managed yes", calls)

    def test_watchdog_exits_after_immediate_parent_death(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_SERVER_SLEEP="2",
            ROG5_TEST_HARD_SERVER_TIMEOUT="1",
            ROG5_TEST_DIE_AFTER_WATCHDOG="1",
        )
        self.assertEqual(result.returncode, -9, result.stderr)
        watchdog_pid = int(
            self.fixture.watchdog_pid.read_text(encoding="ascii")
        )
        for _attempt in range(40):
            try:
                os.kill(watchdog_pid, 0)
            except ProcessLookupError:
                break
            __import__("time").sleep(0.05)
        else:
            self.fail("watchdog survived immediate controller death")
        controller = CONTROLLER.read_text(encoding="utf-8")
        self.assertGreaterEqual(controller.count("os.getppid()==expected"), 2)

    def test_every_partial_setup_failure_enters_scoped_cleanup(self):
        cases = (
            (
                "--zone=drop --remove-forward",
                "--zone=drop --add-forward",
            ),
            (
                "--zone=trusted --add-rich-rule=",
                "--zone=public --remove-rich-rule=",
            ),
            (
                "device set usbtest0 managed no",
                "--zone=public --remove-rich-rule=",
            ),
            (
                "--zone=drop --change-interface=usbtest0",
                "--zone=public --change-interface=usbtest0",
            ),
            (
                "--zone=drop --add-rich-rule=",
                "--zone=drop --remove-rich-rule=",
            ),
            (
                "address add 169.254.77.1/30",
                "address del 169.254.77.1/30",
            ),
        )
        for failure, rollback in cases:
            with self.subTest(failure=failure):
                self.fixture.close()
                self.fixture = ControllerFixture()
                result = self.fixture.run(
                    BUNDLE,
                    MANIFEST_HASH,
                    MOCK_FAIL_CONTAINS=failure,
                )
                self.assertNotEqual(result.returncode, 0)
                calls = self.fixture.call_log()
                self.assertIn(rollback, calls)
                self.assertNotIn("setpriv ", calls)
                self.assertIn("host network state removed", result.stdout)

    def test_pre_disabled_forwarding_is_left_unchanged(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_FORWARD_ENABLED="0",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fixture.call_log()
        self.assertNotIn("--zone=drop --remove-forward", calls)
        self.assertNotIn("--zone=drop --add-forward", calls)

    def test_legacy_networkmanager_managed_field_is_supported(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_LEGACY_MANAGED_FIELD="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fixture.call_log()
        self.assertIn("-g GENERAL.NM-MANAGED device show usbtest0", calls)
        self.assertIn("-g GENERAL.MANAGED device show usbtest0", calls)

    def test_fallback_profile_is_scoped_to_recovery_and_restored(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_FALLBACK_ADDRESS="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fixture.call_log()
        uuid = "244dd128-e3b1-458e-9639-5e4ab4d8854f"
        self.assertIn(f"nmcli connection down uuid {uuid}", calls)
        self.assertIn(
            f"nmcli connection up uuid {uuid} ifname usbtest0",
            calls,
        )
        self.assertIn(
            "ip address add 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertIn(
            "ip address del 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertFalse(self.fixture.connection_state.exists())

    def test_invalid_identity_is_rejected_before_host_inspection(self):
        for bundle, digest in (
            ("../escape", MANIFEST_HASH),
            ("none", MANIFEST_HASH),
            (BUNDLE, "A" * 64),
            (BUNDLE, "0" * 64),
        ):
            with self.subTest(bundle=bundle, digest=digest[:1]):
                result = self.fixture.run(bundle, digest)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.fixture.call_log(), "")

    def test_installed_surface_is_fixed_and_runtime_only(self):
        controller = CONTROLLER.read_text(encoding="utf-8")
        installer = INSTALLER.read_text(encoding="utf-8")
        launcher = LAUNCHER.read_text(encoding="utf-8")
        for contract in (
            "/usr/libexec/rog5-recovery-bundle-controller",
            "/usr/libexec/rog5-recovery-host/host_bundle_server.py",
            "/var/lib/rog5-recovery-bundles",
            "169.254.77.1",
            "169.254.77.2",
            "ID_VENDOR_ID=1d6b",
            "ID_MODEL_ID=0104",
            "ID_MODEL=ROG5_recovery",
            "ID_NET_DRIVER=cdc_ncm",
            "--bounding-set=-all",
            "--no-new-privs",
            "--pdeathsig TERM",
            "--reset-env",
            "--timeout=",
            "valid_lft 180",
        ):
            self.assertIn(contract, controller)
        self.assertIn('exec pkexec "$controller"', launcher)
        self.assertIn("install -o root -g root -m 0555", installer)
        self.assertIn(
            "install-headless-ssh-deployment-export.py",
            installer,
        )
        server_hash = hashlib.sha256(
            (
                REPO / "tools/recovery_control/host_bundle_server.py"
            ).read_bytes()
        ).hexdigest()
        self.assertIn(f"server_sha256={server_hash}", controller)
        self.assertIn(
            "controller source does not pin this bundle-server source",
            installer,
        )
        invalid_launcher = subprocess.run(
            [str(LAUNCHER), "../escape", MANIFEST_HASH],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(invalid_launcher.returncode, 0)
        self.assertIn("invalid bundle identity", invalid_launcher.stderr)
        self.assertNotIn("not safely installed", invalid_launcher.stderr)
        unprivileged_installer = subprocess.run(
            [str(INSTALLER)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(unprivileged_installer.returncode, 0)
        self.assertIn("through PolicyKit", unprivileged_installer.stderr)
        for forbidden in (
            "--permanent",
            "--add-masquerade",
            "sudo ",
            "fastboot flash",
            "dd if=",
            "shell=True",
        ):
            self.assertNotIn(forbidden, controller)
            self.assertNotIn(forbidden, launcher)


if __name__ == "__main__":
    unittest.main(verbosity=2)
