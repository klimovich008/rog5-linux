#!/usr/bin/env python3
"""Hostile fixture tests for the at-most-once devices-level pm_test gate."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts/device/run-network-root-suspend-pm-test-devices.py"
GUARD = "rog5-suspend-pm-test-devices-v1"


def baseline() -> dict[str, object]:
    return {
        "kernel_release": "7.1.4-g7a5cef0db479",
        "pid1": "systemd",
        "cmdline": "root=/dev/nfs ro",
        "system_state": "running",
        "server_inhibitor": "active",
        "failed_units": 0,
        "root_fstype": "overlay",
        "nfs_source": "169.254.77.1:/",
        "nfs_options": "ro,vers=4.2,proto=tcp",
        "physical_blocks": 0,
        "block_mounts": 0,
        "watchdog_pid": False,
        "watchdog_disarmed": True,
        "udcs": ["a600000.dwc3"],
        "bound_udc": "a600000.dwc3",
        "usb0_present": True,
        "carrier": "1",
        "addresses": ["169.254.77.2/30"],
        "route": "169.254.77.1 dev usb0 src 169.254.77.2",
        "pm_test": "[none] core processors platform devices freezer",
        "power_state": "freeze mem",
        "sync_on_suspend": "1",
        "wakeup_count": "7",
        "kernel_config": [
            "CONFIG_EXPERT=y",
            "CONFIG_PM_DEBUG=y",
            "CONFIG_PM_SLEEP_DEBUG=y",
            "CONFIG_DPM_WATCHDOG=y",
            "CONFIG_DPM_WATCHDOG_TIMEOUT=30",
            "CONFIG_DPM_WATCHDOG_WARNING_TIMEOUT=15",
            "# CONFIG_PM_ADVANCED_DEBUG is not set",
            "# CONFIG_PM_TEST_SUSPEND is not set",
            "# CONFIG_RESET_SIMPLE is not set",
        ],
        "dmesg": "Linux version fixture",
        "post": {},
    }


class SuspendPmTestDevicesGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "fixture"
        self.root.mkdir(mode=0o700)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_gate(
        self,
        fixture: dict[str, object],
        *,
        armed: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        (self.root / "fixture.json").write_text(
            json.dumps(fixture), encoding="utf-8"
        )
        environment = os.environ.copy()
        environment["ROG5_PM_TEST_TESTING"] = "1"
        if armed:
            environment["ALLOW_ROG5_SUSPEND_PM_TEST_DEVICES"] = GUARD
        else:
            environment.pop("ALLOW_ROG5_SUSPEND_PM_TEST_DEVICES", None)
        return subprocess.run(
            [str(GATE), "--fixture-root", str(self.root)],
            cwd=REPO,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def writes(self) -> list[str]:
        path = self.root / "writes.log"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def test_one_devices_attempt_returns_and_is_consumed(self) -> None:
        result = self.run_gate(baseline())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.writes(), ["pm_test=devices", "state=mem", "pm_test=none"])
        consumed = self.root / "run/rog5-pm-test-devices-v1.consumed"
        self.assertTrue(consumed.is_file())
        self.assertEqual(consumed.read_text(encoding="utf-8"), "consumed-before-pm-test\n")
        self.assertIn("attempts=1", result.stdout)
        self.assertIn("real_suspend=0", result.stdout)

        second = self.run_gate(baseline())
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("already consumed", second.stderr)
        self.assertEqual(self.writes(), ["pm_test=devices", "state=mem", "pm_test=none"])

    def test_missing_guard_fails_before_claim_or_write(self) -> None:
        result = self.run_gate(baseline(), armed=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact execution guard", result.stderr)
        self.assertEqual(self.writes(), [])
        self.assertFalse((self.root / "run/rog5-pm-test-devices-v1.consumed").exists())

    def hostile_before_claim(self, field: str, value: object, expected: str) -> None:
        fixture = baseline()
        fixture[field] = value
        result = self.run_gate(fixture)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)
        self.assertEqual(self.writes(), [])
        self.assertFalse((self.root / "run/rog5-pm-test-devices-v1.consumed").exists())

    def test_hostile_preconditions_fail_closed(self) -> None:
        cases = (
            ("kernel_release", "7.1.4-hostile", "unexpected kernel"),
            ("server_inhibitor", "inactive", "server inhibitor is not active"),
            ("physical_blocks", 1, "physical block device"),
            ("watchdog_pid", True, "rollback watchdog is still armed"),
            ("udcs", [], "exactly one expected UDC"),
            ("udcs", ["a600000.dwc3", "hostile"], "exactly one expected UDC"),
            ("udcs", ["renamed.dwc3"], "exactly one expected UDC"),
            ("bound_udc", "hostile.dwc3", "gadget is not bound"),
            ("carrier", "0", "USB network carrier"),
            ("addresses", ["169.254.77.2/24"], "USB network address"),
            ("route", "169.254.77.1 via 1.2.3.4 dev usb0", "direct USB route"),
            ("pm_test", "[none] core platform freezer", "devices level is unavailable"),
            ("pm_test", "none core platform [devices] freezer", "pm_test is not disarmed"),
            ("sync_on_suspend", "0", "sync_on_suspend is not enabled"),
            (
                "kernel_config",
                [line for line in baseline()["kernel_config"] if line != "CONFIG_EXPERT=y"],
                "kernel lacks exact suspend pm_test config",
            ),
        )
        for field, value, expected in cases:
            with self.subTest(field=field, value=value):
                self.hostile_before_claim(field, value, expected)
                for child in self.root.iterdir():
                    if child.is_dir():
                        import shutil

                        shutil.rmtree(child)
                    else:
                        child.unlink()

    def test_state_write_failure_is_consumed_and_disarmed(self) -> None:
        fixture = baseline()
        fixture["fail_state_write"] = True
        result = self.run_gate(fixture)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("simulated state write failure", result.stderr)
        self.assertEqual(self.writes(), ["pm_test=devices", "state=mem", "pm_test=none"])
        self.assertTrue((self.root / "run/rog5-pm-test-devices-v1.consumed").is_file())

    def test_post_return_losses_have_exact_terminal_classifications(self) -> None:
        cases = (
            ("udcs", [], "post-return UDC loss"),
            ("bound_udc", "", "post-return UDC binding loss"),
            ("usb0_present", False, "post-return interface loss"),
            ("carrier", "0", "post-return carrier loss"),
            ("addresses", [], "post-return address loss"),
            ("route", "unreachable 169.254.77.1", "post-return route loss"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                fixture = baseline()
                fixture["post"] = {field: value}
                result = self.run_gate(fixture)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertEqual(
                    self.writes(), ["pm_test=devices", "state=mem", "pm_test=none"]
                )
                for child in self.root.iterdir():
                    if child.is_dir():
                        import shutil

                        shutil.rmtree(child)
                    else:
                        child.unlink()

    def test_missing_debug_return_marker_is_consumed(self) -> None:
        fixture = baseline()
        fixture["omit_pm_marker"] = True
        result = self.run_gate(fixture)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("devices-level return marker", result.stderr)
        self.assertTrue((self.root / "run/rog5-pm-test-devices-v1.consumed").is_file())


if __name__ == "__main__":
    unittest.main()
