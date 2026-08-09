#!/usr/bin/env python3
"""Hostile fixture tests for the read-only ROG5 dual-cell snapshot."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
COLLECTOR = REPO / "scripts/device/collect-dual-cell-readonly-snapshot.sh"
BOOT_ID = "7d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8"


class DualCellReadonlySnapshotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-dual-cell-snapshot-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.power_root = self.root / "sys/class/power_supply"
        self.device_root = self.root / "sys/devices"
        self.power_root.mkdir(parents=True)
        self.device_root.mkdir(parents=True)
        boot_id = self.root / "proc/sys/kernel/random/boot_id"
        boot_id.parent.mkdir(parents=True)
        boot_id.write_text(f"{BOOT_ID}\n", encoding="ascii")

        for name in (
            "qcom-battmgr-bat",
            "qcom-battmgr-usb",
            "qcom-battmgr-wls",
        ):
            target = self.device_root / "platform/pmic-glink" / name
            target.mkdir(parents=True)
            relative = os.path.relpath(target, self.power_root)
            (self.power_root / name).symlink_to(relative)

        self.battery = (
            self.device_root / "platform/pmic-glink/qcom-battmgr-bat"
        )
        self.write_property("voltage_now", "8255000\n")
        self.write_property(
            "cell_voltages",
            "cell1_voltage_mv=4120 cell2_voltage_mv=4135\n",
        )

    def write_property(self, name: str, value: str, mode: int = 0o444) -> Path:
        path = self.battery / name
        if path.exists() and not path.is_symlink():
            path.chmod(0o644)
        path.write_text(value, encoding="ascii")
        path.chmod(mode)
        return path

    def run_collector(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "ALLOW_DUAL_CELL_READONLY_SNAPSHOT": "1",
                "ROG5_DUAL_CELL_TEST_MODE": "1",
                "ROG5_DUAL_CELL_RUNTIME_ROOT": str(self.root),
                "ROG5_DUAL_CELL_TEST_KERNEL_RELEASE": (
                    "7.1.4-g7a5cef0db479"
                ),
            }
        )
        return subprocess.run(
            [str(COLLECTOR)],
            cwd=REPO,
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def assert_refused(self, message: str) -> None:
        result = self.run_collector()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)

    def test_canonical_snapshot_passes_and_is_observational(self) -> None:
        result = self.run_collector()
        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(
            line.split("=", 1)
            for line in result.stdout.splitlines()
            if "=" in line
        )
        self.assertEqual(values["format"], "rog5-dual-cell-snapshot-v1")
        self.assertEqual(values["profile"], "battery-dual-cell-readonly-v1")
        self.assertEqual(values["aggregate_voltage_uv"], "8255000")
        self.assertEqual(values["cell1_voltage_mv"], "4120")
        self.assertEqual(values["cell2_voltage_mv"], "4135")
        self.assertEqual(values["cell_sum_uv"], "8255000")
        self.assertEqual(values["aggregate_delta_uv"], "0")
        self.assertEqual(values["cell_imbalance_mv"], "15")
        self.assertEqual(values["charge_control_surface_count"], "0")
        self.assertEqual(values["result"], "OBSERVED_NOT_HEALTH_ASSESSMENT")
        self.assertRegex(values["collector_sha256"], r"^[0-9a-f]{64}$")

    def test_exact_cell_response_framing_is_required(self) -> None:
        hostile = (
            "cell1_voltage_mv=4120 cell2_voltage_mv=4135 extra=1\n",
            "cell2_voltage_mv=4135 cell1_voltage_mv=4120\n",
            "cell1_voltage_mv=04120 cell2_voltage_mv=4135\n",
            "cell1_voltage_mv=-4120 cell2_voltage_mv=4135\n",
        )
        for value in hostile:
            with self.subTest(value=value):
                self.write_property("cell_voltages", value)
                self.assert_refused("cell-voltage response is not canonical")

    def test_property_identity_and_mode_fail_closed(self) -> None:
        self.write_property("cell_voltages", "x\n", mode=0o644)
        self.assert_refused("property is not read-only: battery/cell_voltages")

        path = self.battery / "cell_voltages"
        path.unlink()
        path.symlink_to("voltage_now")
        self.assert_refused("property is absent or linked: battery/cell_voltages")

    def test_supply_inventory_and_control_surfaces_fail_closed(self) -> None:
        extra = self.device_root / "platform/pmic-glink/hostile"
        extra.mkdir()
        (self.power_root / "hostile").symlink_to(
            os.path.relpath(extra, self.power_root)
        )
        self.assert_refused("supply inventory changed")
        (self.power_root / "hostile").unlink()

        self.write_property("charge_control_end_threshold", "80\n")
        self.assert_refused("charge-control surface appeared")

    def test_ranges_and_aggregate_consistency_fail_closed(self) -> None:
        cases = (
            ("2499", "4135", "cell voltage is outside"),
            ("5001", "4135", "cell voltage is outside"),
            ("3500", "3500", "aggregate does not match cell sum"),
        )
        for cell1, cell2, message in cases:
            with self.subTest(cell1=cell1, cell2=cell2):
                self.write_property(
                    "cell_voltages",
                    f"cell1_voltage_mv={cell1} cell2_voltage_mv={cell2}\n",
                )
                self.assert_refused(message)

    def test_source_contains_no_write_or_phone_transport(self) -> None:
        source = COLLECTOR.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(
                r"(?<![\w-])(adb|fastboot|reboot|poweroff|"
                r"flash|erase|mount|tee)(?![\w-])",
                source,
            )
        )
        self.assertNotIn("> /sys", source)


if __name__ == "__main__":
    unittest.main()
