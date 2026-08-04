#!/usr/bin/env python3
"""Offline lifecycle tests for the privileged recovery-host controller."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import time
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
        self.sys_devices = self.root / "sys/devices"
        self.usb_device = (
            self.sys_devices / "pci/usb1/1-1/1-1.2"
        )
        self.sys_net = self.usb_device / "net"
        self.sys_net.mkdir(parents=True)
        interface = self.sys_net / "usbtest0"
        (interface / "device").mkdir(parents=True)
        self.driver = self.root / "sys/drivers/cdc_ncm"
        self.driver.mkdir(parents=True)
        (interface / "device/driver").symlink_to(self.driver)
        for name, value in (
            ("idVendor", "1d6b\n"),
            ("idProduct", "0104\n"),
            ("product", "ROG5 recovery\n"),
        ):
            (self.usb_device / name).write_text(value, encoding="ascii")
        self.sys_bus_usb = self.root / "sys/bus/usb/devices"
        self.sys_bus_usb.mkdir(parents=True)
        (self.sys_bus_usb / "1-1.2").symlink_to(self.usb_device)
        self.bundle_root = self.root / "bundles"
        self.bundle_root.mkdir(mode=0o700)
        self.bundle_root.chmod(0o700)
        self.lock = self.root / "controller.lock"
        self.calls = self.root / "calls"
        self.connection_state = self.root / "connection-down"
        self.autoconnect_state = self.root / "profile-autoconnect"
        self.autoconnect_state.write_text("yes\n", encoding="ascii")
        self.managed_state = self.root / "device-managed"
        self.managed_state.write_text("yes\n", encoding="ascii")
        self.pid = self.root / "server.pid"
        self.progress_pid = self.root / "progress.pid"
        self.progress_ss_count = self.root / "progress-ss.count"
        self.progress_eof = self.root / "progress.eof"
        self.progress_output = self.root / "progress-output"
        self.progress_output.mkdir(mode=0o700)
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
        self.progress_collector = self.root / "progress_collector.py"
        self.progress_collector.write_text(
            textwrap.dedent(
                """\
                import hashlib
                import os
                from pathlib import Path
                import sys
                import time

                Path(os.environ["MOCK_PROGRESS_PID"]).write_text(
                    f"{os.getpid()}\\n", encoding="ascii"
                )
                if os.environ.get("MOCK_PROGRESS_EXIT") == "1":
                    raise SystemExit(1)
                eof = Path(sys.argv[8])
                if eof != Path(os.environ["ROG5_TEST_PROGRESS_EOF_MARKER"]):
                    raise SystemExit(2)
                if int(sys.argv[9]) != os.getppid():
                    raise SystemExit(3)
                if os.environ.get("MOCK_PROGRESS_PRECREATE_EOF") == "1":
                    eof.touch()
                    time.sleep(10)
                stop = Path(sys.argv[4]) / "recovery-progress.stop"
                while not eof.exists() and not stop.exists():
                    time.sleep(0.01)
                if os.environ.get("MOCK_PROGRESS_HANG") == "1":
                    time.sleep(10)
                if os.environ.get("MOCK_PROGRESS_EXIT_AFTER_EOF") == "1":
                    raise SystemExit(1)
                if os.environ.get("MOCK_PROGRESS_NO_CAPTURE") == "1":
                    raise SystemExit(0)
                empty = hashlib.sha256(b"").hexdigest()
                payload = (
                    "format=rog5-recovery-progress-capture-v1\\n"
                    + "session=" + "0" * 32 + "\\n"
                    + "request=" + "0" * 32 + "\\n"
                    + f"bundle={sys.argv[2]}\\n"
                    + f"manifest_sha256={sys.argv[3]}\\n"
                    + "records=0\\nphases=none\\nwire_bytes=0\\n"
                    + f"wire_sha256={empty}\\n"
                    + "result=PARTIAL\\ntruncated=YES\\n"
                    + "reason=NO_ADMISSION\\nauthority=NONE\\n"
                )
                output = Path(sys.argv[4]) / "recovery-progress.capture"
                output.write_text(payload, encoding="ascii")
                output.chmod(0o600)
                """
            ),
            encoding="utf-8",
        )
        self.progress_collector.chmod(0o555)
        self._write_mocks()

    def close(self) -> None:
        self.temporary.cleanup()

    def set_usb_product(self, product: str) -> None:
        (self.usb_device / "product").write_text(
            product + "\n", encoding="utf-8"
        )

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
	if [ "${MOCK_UDEV_SLEEP:-0}" != 0 ]; then
	  sleep "$MOCK_UDEV_SLEEP"
	fi
	[ "${MOCK_UDEV_MATCH:-1}" = 1 ] || exit 0
	printf '%s\n' \
	  'ID_VENDOR_ID=1d6b' \
	  'ID_MODEL_ID=0104' \
	  "ID_MODEL=${MOCK_USB_MODEL:-ROG5_recovery}" \
	  'ID_NET_DRIVER=cdc_ncm' \
	  'ID_USB_DRIVER=cdc_ncm' \
	  'ID_USB_INTERFACE_NUM=00'
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
if [ "${MOCK_NMCLI_SLEEP:-0}" != 0 ]; then
  sleep "$MOCK_NMCLI_SLEEP"
fi
case $* in
  *"${MOCK_FAIL_CONTAINS:-__never_match__}"*) exit 1 ;;
esac
	if [ "$1 $2 $3" = "-g GENERAL.NM-MANAGED device" ]; then
	  [ "${MOCK_LEGACY_MANAGED_FIELD:-0}" = 0 ] || exit 2
	  cat "$MOCK_MANAGED_STATE"
	elif [ "$1 $2 $3" = "-g GENERAL.MANAGED device" ]; then
	  cat "$MOCK_MANAGED_STATE"
	elif [ "$1 $2 $3" = "-g GENERAL.CON-UUID device" ]; then
	  [ ! -e "$MOCK_CONNECTION_STATE" ] &&
	    printf '%s\n' '244dd128-e3b1-458e-9639-5e4ab4d8854f'
	elif [ "$1 $2" = "-g connection.uuid" ] &&
	     [ "$3 $4" = "connection show" ]; then
	  printf '%s\n' '244dd128-e3b1-458e-9639-5e4ab4d8854f'
	elif [ "$1" = -g ] && [ "$3 $4 $5" = "connection show uuid" ]; then
	  printf '%s\n' \
	    "${MOCK_PROFILE_ID:-rog5-fallback-usb-ssh}" \
	    '802-3-ethernet' \
	    'usbtest0' \
	    "$(cat "$MOCK_AUTOCONNECT_STATE")" \
    '100' \
    'manual' \
    '169.254.77.1/30' \
    '' \
    '' \
    'yes' \
    'disabled'
	elif [ "$1 $2 $3" = "connection down uuid" ]; then
	  : >"$MOCK_CONNECTION_STATE"
	elif [ "$1 $2 $3" = "connection up uuid" ]; then
	  rm -f "$MOCK_CONNECTION_STATE"
	  if [ "${MOCK_DETACH_AFTER_UP:-0}" = 1 ]; then
	    rm -f "$MOCK_USB_DEVICE/product"
	  fi
	elif [ "$1 $2 $3" = "connection modify uuid" ] &&
	     [ "$5" = connection.autoconnect ]; then
	  printf '%s\n' "$6" >"$MOCK_AUTOCONNECT_STATE"
	elif [ "$1 $2 $4" = "device set managed" ]; then
	  printf '%s\n' "$5" >"$MOCK_MANAGED_STATE"
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
        '15: usbtest0 inet 169.254.77.1/30 scope link usbtest0'
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
  case ${MOCK_LISTENER_ADDRESS:-0.0.0.0}:$* in
    127.0.0.1:*"sport = :8080 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*) ;;
    127.0.0.1:*"-lnt4"*"sport = :8080"*|127.0.0.1:*"-lntp4"*"sport = :8080"*|127.0.0.1:*"-lntu4"*"sport = :8080"*)
      printf '%s\n' \
        'LISTEN 0 1 127.0.0.1:8080 0.0.0.0:* users:(("other",pid=999,fd=3))'
      ;;
    0.0.0.0:*"-lnt4"*"sport = :8080 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*|169.254.77.1:*"-lnt4"*"sport = :8080 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
      printf '%s\n' \
        "LISTEN 0 1 ${MOCK_LISTENER_ADDRESS:-0.0.0.0}:8080 0.0.0.0:* users:((\"other\",pid=999,fd=3))"
      ;;
    :::*"-lnt6"*"sport = :8080 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*|::ffff:0.0.0.0:*"-lnt6"*"sport = :8080 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*|::ffff:169.254.77.1:*"-lnt6"*"sport = :8080 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*)
      printf '%s\n' \
        "LISTEN 0 1 [${MOCK_LISTENER_ADDRESS}]:8080 [::]:* users:((\"other\",pid=999,fd=3))"
      ;;
  esac
fi
if [ "${MOCK_PROGRESS_LISTENER_EXISTING:-0}" = 1 ]; then
  case $* in
    *"-lnt4"*"sport = :8081"*)
      printf '%s\n' \
        'LISTEN 0 1 169.254.77.1:8081 0.0.0.0:* users:(("other",pid=998,fd=3))'
      ;;
  esac
fi
if [ "${MOCK_PROGRESS_IPV6_EXISTING:-0}" = 1 ]; then
  case $* in
    *"-lnt6"*"sport = :8081 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*)
      printf '%s\\n' \\
        'LISTEN 0 4096 [::]:8081 [::]:* users:(("systemd",pid=1,fd=205))'
      ;;
  esac
fi
if [ -s "$MOCK_SERVER_PID" ]; then
  case $* in
    *"-lntp4"*"sport = :8080 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
      pid=$(sed -n '1p' "$MOCK_SERVER_PID")
      printf '%s\n' \
        "LISTEN 0 1 169.254.77.1:8080 0.0.0.0:* users:((\\"python3\\",pid=$pid,fd=3))"
      ;;
  esac
  case ${MOCK_LISTENER_AFTER_SERVER_ADDRESS:-}:$* in
    :::*"-lntp6"*"sport = :8080 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*)
      printf '%s\n' \
        'LISTEN 0 1 [::]:8080 [::]:* users:(("other",pid=999,fd=3))'
      ;;
  esac
fi
case $* in
  *"-lntp4"*"sport = :8081"*)
    if [ -n "${MOCK_PROGRESS_LISTENER_DELAY_CALLS:-}" ]; then
      count=0
      if [ -f "$MOCK_PROGRESS_SS_COUNT" ]; then
        count=$(sed -n '1p' "$MOCK_PROGRESS_SS_COUNT")
      fi
      count=$((count + 1))
      printf '%s\n' "$count" >"$MOCK_PROGRESS_SS_COUNT"
      if [ "$count" -le "$MOCK_PROGRESS_LISTENER_DELAY_CALLS" ]; then
        exit 0
      fi
    fi
    ;;
esac
if [ "${MOCK_PROGRESS_LISTENER_AFTER_SERVER:-0}" = 1 ] &&
   [ -s "$MOCK_SERVER_PID" ]; then
  case $* in
    *"-lntp4"*"sport = :8081 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
      printf '%s\n' \
        'LISTEN 0 1 169.254.77.1%usbtest0:8081 0.0.0.0:* users:(("other",pid=997,fd=3))'
      ;;
  esac
elif [ "${MOCK_PROGRESS_NO_LISTENER:-0}" != 1 ] &&
     [ -s "$MOCK_PROGRESS_PID" ]; then
  case $* in
    *"-lntp4"*"sport = :8081 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
      pid=$(sed -n '1p' "$MOCK_PROGRESS_PID")
      if [ "${MOCK_PROGRESS_LISTENER_UNSCOPED:-0}" = 1 ]; then
        local_address=169.254.77.1:8081
      elif [ "${MOCK_PROGRESS_LISTENER_WRONG_INTERFACE:-0}" = 1 ]; then
        local_address=169.254.77.1%xusbtest0:8081
      elif [ "${MOCK_PROGRESS_LISTENER_WRONG_ADDRESS:-0}" = 1 ]; then
        local_address=169.254.77.10%usbtest0:8081
      else
        local_address=169.254.77.1%usbtest0:8081
      fi
      if [ "${MOCK_PROGRESS_LISTENER_SHARED_OWNER:-0}" = 1 ]; then
        owner_field="users:((\\\"python3\\\",pid=$pid,fd=3),(\\\"other\\\",pid=996,fd=4))"
      else
        owner_field="users:((\\\"python3\\\",pid=$pid,fd=3))"
      fi
      printf '%s\n' \
        "LISTEN 0 1 $local_address 0.0.0.0:* $owner_field"
      if [ "${MOCK_PROGRESS_LISTENER_DUPLICATE:-0}" = 1 ]; then
        printf '%s\n' \
          "LISTEN 0 1 $local_address 0.0.0.0:* $owner_field"
      fi
      ;;
  esac
fi
if [ "${MOCK_PROGRESS_IPV6_AFTER_SERVER:-0}" = 1 ] &&
  [ -s "$MOCK_SERVER_PID" ]; then
  case $* in
    *"-lntp6"*"sport = :8081 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*)
      printf '%s\n' \
        'LISTEN 0 4096 [::]:8081 [::]:* users:(("systemd",pid=1,fd=205))'
      ;;
  esac
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
for argument in "$@"; do
  if [ "$argument" = "$ROG5_TEST_SERVER_PATH" ]; then
    printf '%s\n' "$$" >"$MOCK_SERVER_PID"
  fi
done
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
                "ROG5_TEST_SYS_DEVICES": str(self.sys_devices),
                "ROG5_TEST_SYS_BUS_USB": str(self.sys_bus_usb),
                "ROG5_TEST_SERVER_PATH": str(self.server),
                "ROG5_TEST_PROGRESS_COLLECTOR_PATH": str(
                    self.progress_collector
                ),
                "ROG5_TEST_PROGRESS_EOF_MARKER": str(self.progress_eof),
                "ROG5_TEST_BUNDLE_ROOT": str(self.bundle_root),
                "ROG5_TEST_LOCK_PATH": str(self.lock),
                "MOCK_CALLS": str(self.calls),
                "MOCK_SERVER_PID": str(self.pid),
                "MOCK_PROGRESS_PID": str(self.progress_pid),
                "MOCK_PROGRESS_SS_COUNT": str(self.progress_ss_count),
                "MOCK_CONNECTION_STATE": str(self.connection_state),
                "MOCK_AUTOCONNECT_STATE": str(self.autoconnect_state),
                "MOCK_MANAGED_STATE": str(self.managed_state),
                "MOCK_USB_DEVICE": str(self.usb_device),
                "MOCK_FALLBACK_ADDRESS": "1",
                "ROG5_TEST_WATCHDOG_PID_FILE": str(self.watchdog_pid),
            }
        )
        environment.update(overrides)
        return environment

    def run(
        self,
        *arguments: str,
        controller: Path = CONTROLLER,
        **overrides: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(controller), *arguments],
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

    def test_progress_mode_owns_both_listeners_until_capture_then_defers(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("progress listener ready on 169.254.77.1:8081", result.stdout)
        self.assertIn("bounded recovery progress capture completed", result.stdout)
        self.assertIn(
            "bounded recovery progress collection concluded authority=NONE",
            result.stdout,
        )
        self.assertIn("profile restoration deferred", result.stdout)
        capture = self.fixture.progress_output / "recovery-progress.capture"
        self.assertTrue(capture.is_file())
        self.assertEqual(capture.stat().st_mode & 0o777, 0o600)
        self.assertIn("authority=NONE\n", capture.read_text(encoding="ascii"))
        self.assertFalse(self.fixture.progress_eof.exists())
        calls = self.fixture.call_log()
        for port in ("8080", "8081"):
            self.assertIn(f'port port="{port}" protocol="tcp" accept', calls)
            self.assertIn(f'port port="{port}" protocol="tcp" drop', calls)
        self.assertIn("sport = :8081", calls)
        self.assertIn("--timeout=360s", calls)
        self.assertIn(
            "valid_lft 360 preferred_lft 360",
            calls,
        )
        self.assertIn(
            "setpriv --pdeathsig TERM -- /usr/bin/python3 -I -S -B "
            + str(self.fixture.progress_collector),
            calls,
        )

    def test_progress_port_conflict_refuses_before_network_mutation(self):
        for override in (
            "MOCK_PROGRESS_LISTENER_EXISTING",
            "MOCK_PROGRESS_IPV6_EXISTING",
        ):
            with self.subTest(override=override):
                self.fixture.close()
                self.fixture = ControllerFixture()
                result = self.fixture.run(
                    "serve-progress-deferred",
                    BUNDLE,
                    MANIFEST_HASH,
                    str(self.fixture.progress_output),
                    **{override: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "TCP port 8081 already has a listener",
                    result.stderr,
                )
                calls = self.fixture.call_log()
                self.assertNotIn("--add-rich-rule=", calls)
                self.assertNotIn("connection down uuid", calls)

    def test_progress_listener_absence_is_advisory_and_deferred(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_NO_LISTENER="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("progress listener unavailable", result.stdout)
        self.assertIn("authority=NONE", result.stdout)
        self.assertIn("profile restoration deferred", result.stdout)
        calls = self.fixture.call_log()
        self.assertIn(
            "ip address del 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertNotIn("nmcli device set usbtest0 managed yes", calls)
        self.assertFalse(self.fixture.progress_eof.exists())

    def test_delayed_healthy_progress_listener_is_admitted(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_LISTENER_DELAY_CALLS="3",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("progress listener ready", result.stdout)
        self.assertEqual(
            self.fixture.progress_ss_count.read_text(encoding="ascii"),
            "4\n",
        )

    def test_progress_listener_requires_exact_interface_scope(self):
        for override in (
            "MOCK_PROGRESS_LISTENER_UNSCOPED",
            "MOCK_PROGRESS_LISTENER_WRONG_INTERFACE",
            "MOCK_PROGRESS_LISTENER_WRONG_ADDRESS",
        ):
            with self.subTest(override=override):
                self.fixture.close()
                self.fixture = ControllerFixture()
                result = self.fixture.run(
                    "serve-progress-deferred",
                    BUNDLE,
                    MANIFEST_HASH,
                    str(self.fixture.progress_output),
                    **{override: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "progress listener is not uniquely confined",
                    result.stderr,
                )

    def test_steam_style_ipv6_progress_race_fails_closed(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_IPV6_AFTER_SERVER="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "progress listener is not uniquely confined",
            result.stderr,
        )
        calls = self.fixture.call_log()
        self.assertIn(
            "ss -H -lntp6 sport = :8081 and ( src = ::/128 or ",
            calls,
        )

    def test_progress_listener_rejects_shared_owner_record(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_LISTENER_SHARED_OWNER="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "progress listener is not uniquely confined",
            result.stderr,
        )

    def test_progress_listener_rejects_duplicate_records(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_LISTENER_DUPLICATE="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "progress listener is not uniquely confined",
            result.stderr,
        )

    def test_progress_listener_conflict_after_start_fails_closed(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_LISTENER_AFTER_SERVER="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "progress listener is not uniquely confined",
            result.stderr,
        )
        calls = self.fixture.call_log()
        self.assertIn(
            "ip address del 169.254.77.1/30 dev usbtest0",
            calls,
        )
        self.assertIn("nmcli device set usbtest0 managed yes", calls)

    def test_progress_conflict_after_collector_exit_fails_closed(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_EXIT="1",
            MOCK_PROGRESS_LISTENER_AFTER_SERVER="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "progress listener is not uniquely confined",
            result.stderr,
        )

    def test_post_transfer_progress_failure_is_advisory_and_deferred(self):
        for override in (
            "MOCK_PROGRESS_NO_CAPTURE",
            "MOCK_PROGRESS_EXIT_AFTER_EOF",
        ):
            with self.subTest(override=override):
                self.fixture.close()
                self.fixture = ControllerFixture()
                result = self.fixture.run(
                    "serve-progress-deferred",
                    BUNDLE,
                    MANIFEST_HASH,
                    str(self.fixture.progress_output),
                    **{override: "1"},
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("authority=NONE", result.stdout + result.stderr)
                self.assertIn("profile restoration deferred", result.stdout)
                calls = self.fixture.call_log()
                self.assertIn(
                    "ip address del 169.254.77.1/30 dev usbtest0",
                    calls,
                )
                self.assertNotIn("nmcli device set usbtest0 managed yes", calls)
                self.assertFalse(self.fixture.progress_eof.exists())

    def test_progress_eof_marker_failure_is_advisory_and_deferred(self):
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_PRECREATE_EOF="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("bundle-EOF marker is unavailable", result.stderr)
        self.assertIn("authority=NONE", result.stderr)
        self.assertIn("one recovery bundle transfer completed", result.stdout)
        self.assertIn("profile restoration deferred", result.stdout)
        calls = self.fixture.call_log()
        self.assertNotIn("nmcli device set usbtest0 managed yes", calls)
        self.assertFalse(self.fixture.progress_eof.exists())

    def test_progress_stall_is_advisory_after_bounded_grace(self):
        started = time.monotonic()
        result = self.fixture.run(
            "serve-progress-deferred",
            BUNDLE,
            MANIFEST_HASH,
            str(self.fixture.progress_output),
            MOCK_PROGRESS_HANG="1",
            ROG5_TEST_HARD_SERVER_TIMEOUT="3",
            ROG5_TEST_PROGRESS_POST_TRANSFER_GRACE="1",
        )
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(elapsed, 2.5)
        self.assertIn("exceeded post-transfer grace", result.stderr)
        self.assertIn("authority=NONE", result.stderr)
        self.assertIn("one recovery bundle transfer completed", result.stdout)
        self.assertIn("profile restoration deferred", result.stdout)
        self.assertFalse(self.fixture.progress_eof.exists())
        calls = self.fixture.call_log()
        self.assertIn("--remove-rich-rule=", calls)
        self.assertNotIn("nmcli device set usbtest0 managed yes", calls)

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

    def test_loopback_listener_does_not_conflict_with_fixed_bundle_bind(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_LISTENER_EXISTING="1",
            MOCK_LISTENER_ADDRESS="127.0.0.1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fixture.call_log()
        self.assertIn(
            "ss -H -lnt4 sport = :8080 and ( src = 0.0.0.0/32 or "
            "src = 169.254.77.1/32 )",
            calls,
        )
        self.assertIn(
            "ss -H -lnt6 sport = :8080 and ( src = ::/128 or "
            "src = ::ffff:0.0.0.0/128 or "
            "src = ::ffff:169.254.77.1/128 )",
            calls,
        )

        mutated = self.fixture.root / "broad-listener-controller"
        source = CONTROLLER.read_text(encoding="utf-8")
        old = (
            'bundle_ipv4_filter="sport = :$host_port and ( '
            'src = 0.0.0.0/32 or src = $host_ip/32 )"'
        )
        self.assertEqual(source.count(old), 1)
        mutated.write_text(
            source.replace(old, 'bundle_ipv4_filter="sport = :$host_port"'),
            encoding="utf-8",
        )
        mutated.chmod(0o755)
        rejected = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            controller=mutated,
            MOCK_LISTENER_EXISTING="1",
            MOCK_LISTENER_ADDRESS="127.0.0.1",
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("already has a listener", rejected.stderr)

    def test_each_conflicting_bundle_listener_is_rejected(self):
        for address in (
            "0.0.0.0",
            "169.254.77.1",
            "::",
            "::ffff:0.0.0.0",
            "::ffff:169.254.77.1",
        ):
            with self.subTest(address=address):
                result = self.fixture.run(
                    BUNDLE,
                    MANIFEST_HASH,
                    MOCK_LISTENER_EXISTING="1",
                    MOCK_LISTENER_ADDRESS=address,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("already has a listener", result.stderr)

    def test_readiness_rejects_conflict_appearing_after_server_start(self):
        result = self.fixture.run(
            BUNDLE,
            MANIFEST_HASH,
            MOCK_LISTENER_AFTER_SERVER_ADDRESS="::",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "recovery server listener is not uniquely confined",
            result.stderr,
        )

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

    def test_exact_shared_profile_is_deactivated_and_restored(self):
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
        self.assertIn("nmcli device set usbtest0 managed no", calls)
        self.assertIn("nmcli device set usbtest0 managed yes", calls)
        self.assertFalse(self.fixture.connection_state.exists())

    def test_lifecycle_deferred_mode_suppresses_profile_until_fallback(self):
        result = self.fixture.run(
            "serve-deferred",
            BUNDLE,
            MANIFEST_HASH,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "fallback NetworkManager profile restoration deferred",
            result.stdout,
        )
        calls = self.fixture.call_log()
        uuid = "244dd128-e3b1-458e-9639-5e4ab4d8854f"
        self.assertIn(
            f"nmcli connection modify uuid {uuid} "
            "connection.autoconnect no",
            calls,
        )
        self.assertNotIn(f"nmcli connection up uuid {uuid}", calls)
        self.assertNotIn("device set usbtest0 managed yes", calls)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertEqual(
            self.fixture.managed_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertTrue(self.fixture.connection_state.exists())

    def defer_then_restore(self, **overrides: str) -> subprocess.CompletedProcess[str]:
        deferred = self.fixture.run(
            "serve-deferred",
            BUNDLE,
            MANIFEST_HASH,
        )
        self.assertEqual(deferred.returncode, 0, deferred.stderr)
        self.fixture.set_usb_product("ROG Phone 5 Linux Server")
        return self.fixture.run(
            "restore-fallback",
            "pci/usb1/1-1/1-1.2",
            "3",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
            **overrides,
        )

    def test_deferred_profile_restores_only_on_exact_anchored_fallback(self):
        result = self.defer_then_restore()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("exact Alpine fallback profile restored", result.stdout)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "yes\n",
        )
        self.assertEqual(
            self.fixture.managed_state.read_text(encoding="ascii"),
            "yes\n",
        )
        self.assertFalse(self.fixture.connection_state.exists())

        calls_before = self.fixture.call_log()
        repeated = self.fixture.run(
            "restore-fallback",
            "pci/usb1/1-1/1-1.2",
            "3",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertIn("already restored", repeated.stdout)
        calls_after = self.fixture.call_log()[len(calls_before):]
        self.assertNotIn("connection down uuid", calls_after)
        self.assertNotIn("connection modify uuid", calls_after)

    def test_restore_rejects_wrong_location_and_duplicate_raw_product(self):
        deferred = self.fixture.run(
            "serve-deferred",
            BUNDLE,
            MANIFEST_HASH,
        )
        self.assertEqual(deferred.returncode, 0, deferred.stderr)
        self.fixture.set_usb_product("ROG Phone 5 Linux Server")
        wrong = self.fixture.run(
            "restore-fallback",
            "pci/usb9/9-9",
            "1",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
        )
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("different physical USB port", wrong.stderr)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "no\n",
        )

        duplicate = self.fixture.sys_devices / "pci/usb2/2-1"
        duplicate_interface = duplicate / "net/usbtest1"
        (duplicate_interface / "device").mkdir(parents=True)
        (duplicate_interface / "device/driver").symlink_to(
            self.fixture.driver
        )
        for name, value in (
            ("idVendor", "1d6b\n"),
            ("idProduct", "0104\n"),
            ("product", "ROG Phone 5 Linux Server\n"),
        ):
            (duplicate / name).write_text(value, encoding="ascii")
        (self.fixture.sys_bus_usb / "2-1").symlink_to(duplicate)
        duplicated = self.fixture.run(
            "restore-fallback",
            "pci/usb1/1-1/1-1.2",
            "1",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
        )
        self.assertNotEqual(duplicated.returncode, 0)
        self.assertIn("exact Alpine USB product", duplicated.stderr)

    def test_every_partial_restore_failure_rolls_back_to_deferred_state(self):
        for failure in (
            "device set usbtest0 managed yes",
            "connection up uuid",
            "connection.autoconnect yes",
        ):
            with self.subTest(failure=failure):
                self.fixture.close()
                self.fixture = ControllerFixture()
                result = self.defer_then_restore(
                    MOCK_FAIL_CONTAINS=failure,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(
                    self.fixture.autoconnect_state.read_text(
                        encoding="ascii"
                    ),
                    "no\n",
                )
                self.assertEqual(
                    self.fixture.managed_state.read_text(encoding="ascii"),
                    "no\n",
                )
                self.assertTrue(self.fixture.connection_state.exists())

    def test_usb_detach_during_activation_rolls_profile_back(self):
        result = self.defer_then_restore(MOCK_DETACH_AFTER_UP="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("USB identity changed", result.stderr)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertTrue(self.fixture.connection_state.exists())

    def test_restore_rejects_a_claimed_cdc_ncm_interface_on_wrong_driver(self):
        deferred = self.fixture.run(
            "serve-deferred",
            BUNDLE,
            MANIFEST_HASH,
        )
        self.assertEqual(deferred.returncode, 0, deferred.stderr)
        self.fixture.set_usb_product("ROG Phone 5 Linux Server")
        driver_link = self.fixture.sys_net / "usbtest0/device/driver"
        driver_link.unlink()
        wrong_driver = self.fixture.root / "sys/drivers/rndis_host"
        wrong_driver.mkdir()
        driver_link.symlink_to(wrong_driver)

        result = self.fixture.run(
            "restore-fallback",
            "pci/usb1/1-1/1-1.2",
            "1",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not become stable", result.stderr)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertEqual(
            self.fixture.managed_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertTrue(self.fixture.connection_state.exists())

    def test_bundle_and_restore_operations_share_one_nonblocking_lock(self):
        server = subprocess.Popen(
            [
                str(CONTROLLER),
                "serve-deferred",
                BUNDLE,
                MANIFEST_HASH,
            ],
            env=self.fixture.environment(MOCK_SERVER_SLEEP="2"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            for _attempt in range(100):
                if "setpriv " in self.fixture.call_log():
                    break
                if server.poll() is not None:
                    self.fail("bundle controller exited before lock test")
                time.sleep(0.02)
            else:
                self.fail("bundle controller did not enter its serve phase")
            collision = self.fixture.run(
                "restore-fallback",
                "pci/usb1/1-1/1-1.2",
                "1",
                MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
            )
            self.assertNotEqual(collision.returncode, 0)
            self.assertIn(
                "another recovery bundle controller is active",
                collision.stderr,
            )
        finally:
            server.terminate()
            server.communicate(timeout=5)

    def test_hung_udev_cannot_escape_the_restore_deadline(self):
        deferred = self.fixture.run(
            "serve-deferred",
            BUNDLE,
            MANIFEST_HASH,
        )
        self.assertEqual(deferred.returncode, 0, deferred.stderr)
        self.fixture.set_usb_product("ROG Phone 5 Linux Server")
        started = time.monotonic()
        result = self.fixture.run(
            "restore-fallback",
            "pci/usb1/1-1/1-1.2",
            "1",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
            MOCK_UDEV_SLEEP="2",
        )
        elapsed = time.monotonic() - started
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not become stable", result.stderr)
        self.assertLess(elapsed, 2.0)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "no\n",
        )

    def test_post_enumeration_work_cannot_escape_the_restore_deadline(self):
        deferred = self.fixture.run(
            "serve-deferred",
            BUNDLE,
            MANIFEST_HASH,
        )
        self.assertEqual(deferred.returncode, 0, deferred.stderr)
        self.fixture.set_usb_product("ROG Phone 5 Linux Server")
        started = time.monotonic()
        result = self.fixture.run(
            "restore-fallback",
            "pci/usb1/1-1/1-1.2",
            "1",
            MOCK_USB_MODEL="ROG_Phone_5_Linux_Server",
            MOCK_NMCLI_SLEEP="2",
        )
        elapsed = time.monotonic() - started
        self.assertNotEqual(result.returncode, 0)
        self.assertLess(elapsed, 2.0)
        self.assertEqual(
            self.fixture.autoconnect_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertEqual(
            self.fixture.managed_state.read_text(encoding="ascii"),
            "no\n",
        )
        self.assertTrue(self.fixture.connection_state.exists())

    def test_missing_or_wrong_shared_profile_fails_before_mutation(self):
        for mutation, overrides in (
            ("missing", {"MOCK_FALLBACK_ADDRESS": "0"}),
            ("wrong-id", {"MOCK_PROFILE_ID": "unexpected-profile"}),
        ):
            with self.subTest(mutation=mutation):
                self.fixture.close()
                self.fixture = ControllerFixture()
                result = self.fixture.run(
                    BUNDLE,
                    MANIFEST_HASH,
                    **overrides,
                )
                self.assertNotEqual(result.returncode, 0)
                calls = self.fixture.call_log()
                self.assertNotIn("connection down uuid", calls)
                self.assertNotIn("--add-rich-rule=", calls)

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
            'address_lifetime=360',
        ):
            self.assertIn(contract, controller)
        self.assertIn(
            'exec python3 -B "$client" bundle "$bundle" "$manifest_hash"',
            launcher,
        )
        self.assertIn(
            'exec python3 -B "$server" --preflight "$bundle" "$manifest_hash"',
            launcher,
        )
        self.assertNotIn("exec pkexec", launcher)

        progress_metadata = launcher.index(
            "[[ -f $progress_collector && ! -L $progress_collector"
        )
        progress_hashes = launcher.index(
            '"$progress_collector:$progress_collector_source"'
        )
        for protected_offset in (progress_metadata, progress_hashes):
            guard_offset = launcher.rfind(
                "if [[ $action == serve-progress-deferred ]]; then",
                0,
                protected_offset,
            )
            dispatch_offset = launcher.find("\nfi\n", protected_offset)
            self.assertGreaterEqual(guard_offset, 0)
            self.assertGreater(dispatch_offset, protected_offset)
        self.assertIn("install -o root -g root -m 0555", installer)
        self.assertIn(
            "install-headless-ssh-deployment-export.py",
            installer,
        )
        self.assertIn(
            "export_storage_root=/home/rog5-linux",
            installer,
        )
        self.assertIn(
            "export_parent=$export_storage_root/exports",
            installer,
        )
        self.assertIn(
            "install -d -o root -g root -m 0700",
            installer,
        )
        server_hash = hashlib.sha256(
            (
                REPO / "tools/recovery_control/host_bundle_server.py"
            ).read_bytes()
        ).hexdigest()
        self.assertIn(f"server_sha256={server_hash}", controller)
        progress_sources = {
            "progress_collector_sha256": (
                REPO / "packaging/host/rog5-recovery-progress-collector.py"
            ),
            "progress_package_init_sha256": (
                REPO / "tools/recovery_control/__init__.py"
            ),
            "progress_reference_sha256": (
                REPO / "tools/recovery_control/reference.py"
            ),
            "progress_module_sha256": (
                REPO
                / "tools/recovery_control/host_progress_collector.py"
            ),
        }
        for pin, source in progress_sources.items():
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertIn(f"{pin}={digest}", controller)
            self.assertIn(f'"{pin}:$', installer)
        for contract in (
            "rog5-recovery-progress-collector.py",
            "progress_package_root=$progress_tools_root/recovery_control",
            'install -o root -g root -m 0444',
            '"$progress_package_root/host_progress_collector.py"',
            "installed progress collector module set does not match "
            "controller pins",
        ):
            self.assertIn(contract, controller + installer)
        self.assertIn(
            "controller source does not pin this bundle-server source",
            installer,
        )
        for contract in (
            "steamos_readonly=/usr/bin/steamos-readonly",
            "restore_steamos_readonly=1",
            "run_steamos_readonly disable",
            "run_steamos_readonly enable",
            "1:disabled) printf '%s\\n' disabled",
            "for trusted_directory in / /usr /usr/bin",
            "steamos_readonly_fd_path=/proc/self/fd/",
            "readonly_fd_identity",
            "trap 'cleanup_signal_received=1' HUP INT TERM",
            "FAIL could not restore SteamOS read-only mode",
        ):
            self.assertIn(contract, installer)
        self.assertLess(
            installer.index("restore_steamos_readonly=1"),
            installer.index("run_steamos_readonly disable"),
        )
        self.assertLess(
            installer.index("trap cleanup_and_restore_readonly EXIT"),
            installer.index("run_steamos_readonly disable"),
        )
        self.assertLess(
            installer.index(
                "trap 'cleanup_signal_received=1' HUP INT TERM"
            ),
            installer.index("trap - EXIT"),
        )
        self.assertLess(
            installer.index("run_steamos_readonly disable"),
            installer.index('install -d -o root -g root -m 0755'),
        )
        self.assertLess(
            installer.rindex("restore_original_steamos_readonly"),
            installer.index('echo "PASS installed fixed recovery host controller"'),
        )
        self.assertEqual(installer.count("restore_steamos_readonly=1"), 1)
        self.assertEqual(installer.count("run_steamos_readonly enable"), 1)
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
