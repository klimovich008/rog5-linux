#!/usr/bin/env python3
"""Replay retained real host observations through the active parsers/lifecycle."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (REPO / "test-fixtures/power-usb-real-outputs-v1.json").read_text(
        encoding="ascii"
    )
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LIFECYCLE_TEST = load(
    "power_usb_lifecycle_replay",
    REPO / "scripts/host/test-run-minimal-headless-live-cycle.py",
)
FALLBACK = load(
    "power_usb_fallback_replay",
    REPO / "scripts/host/wait-stock-android-fallback.py",
)


class RealOutputReplayTest(unittest.TestCase):
    def test_power_receipts_fail_before_live_preflight(self) -> None:
        fixture = LIFECYCLE_TEST.Fixture()
        try:
            result = fixture.run(
                "power-usb-preflight",
                ROG5_HOST_DOCTOR_RECEIPT="",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("set ROG5_HOST_DOCTOR_RECEIPT", result.stderr)
            self.assertFalse(
                any(line.startswith("live:") for line in fixture.call_lines())
            )
        finally:
            fixture.close()

    def test_nonadmitted_deployment_receipt_fails_before_live_preflight(self) -> None:
        fixture = LIFECYCLE_TEST.Fixture()
        try:
            fixture.deployment_receipt.chmod(0o600)
            value = json.loads(fixture.deployment_receipt.read_text(encoding="ascii"))
            value["state"] = "built"
            fixture.deployment_receipt.write_text(
                json.dumps(value, sort_keys=True) + "\n",
                encoding="ascii",
            )
            fixture.deployment_receipt.chmod(0o400)
            result = fixture.run("power-usb-preflight")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not the exact admitted state", result.stderr)
            self.assertFalse(
                any(line.startswith("live:") for line in fixture.call_lines())
            )
        finally:
            fixture.close()

    def test_complete_lifecycle_replays_real_zone_nm_and_delays(self) -> None:
        delays = FIXTURE["delays_seconds"]
        for nm_mode in ("MOCK_DEFERRED_EMPTY_LINE_UUID", "MOCK_DEFERRED_STALE_UUID"):
            fixture = LIFECYCLE_TEST.Fixture()
            try:
                result = fixture.run(
                    "power-usb-run",
                    MOCK_FIREWALL_NO_ZONE="1",
                    MOCK_RECOVERY_USB_DELAY=delays["recovery_usb"],
                    MOCK_NFS_ENUMERATION_DELAY=delays["nfs"],
                    MOCK_SSH_ENUMERATION_DELAY=delays["ssh"],
                    MOCK_RUNTIME_ACCEPTANCE_DELAY=delays["runtime"],
                    MOCK_REQUIRE_PROFILE_PRIMER="1",
                    MOCK_UDEV_MISSING_AFTER_FALLBACK="1",
                    **{nm_mode: "1"},
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = fixture.call_lines()
                required = FIXTURE["required_lifecycle_order"]
                if LIFECYCLE_TEST.CYCLE.POWER_USB.PROBE_PHASE == "post-ssh":
                    required = [
                        "live:preflight",
                        "live:boot",
                        "host-key:capture",
                        "nmcli:connection up uuid "
                        "244dd128-e3b1-458e-9639-5e4ab4d8854f ifname usbmock0",
                        "bundle:start",
                        "control:prepare-commit",
                        "bundle:transfer",
                        "nfs:start",
                        "runtime:start",
                        "fallback:stock-android",
                        "control:resolve:TARGET_ACCEPTED",
                    ]
                positions = [calls.index(item) for item in required]
                self.assertEqual(positions, sorted(positions))
            finally:
                fixture.close()

    def test_fastboot_adb_path_and_unauthorized_stock_usb_replay(self) -> None:
        fastboot = FIXTURE["fastboot"]
        self.assertEqual(
            FALLBACK.parse_fastboot_devices(fastboot["devices"]),
            (FALLBACK.SERIAL, FIXTURE["adb"]["short_usb_location"]),
        )
        self.assertEqual(FALLBACK.parse_fastboot_value(fastboot["product"], "product"), "lahaina")
        self.assertEqual(FALLBACK.parse_fastboot_value(fastboot["slot"], "current-slot"), "a")
        self.assertEqual(
            Path(FIXTURE["adb"]["canonical_usb_location"]).name,
            FIXTURE["adb"]["short_usb_location"],
        )
        original_root, original_adb = FALLBACK.USB_ROOT, FALLBACK.adb
        with tempfile.TemporaryDirectory(prefix="rog5-real-usb-replay-") as raw:
            root = Path(raw)
            root.chmod(0o700)
            FALLBACK.USB_ROOT = root
            usb = FIXTURE["stock_fallback_usb"]
            device = root / "1-1.2"
            interface = root / "1-1.2:1.0"
            device.mkdir()
            interface.mkdir()
            for name in (
                "idVendor",
                "idProduct",
                "manufacturer",
                "product",
                "serial",
                "bDeviceClass",
                "bDeviceSubClass",
                "bDeviceProtocol",
            ):
                (device / name).write_text(usb[name] + "\n", encoding="ascii")
            for name in ("bInterfaceClass", "bInterfaceSubClass", "bInterfaceProtocol"):
                (interface / name).write_text(usb[name] + "\n", encoding="ascii")
            preboot = root / "preboot.record"
            preboot.write_text(
                "format=rog5-stock-fallback-preboot-v1\n"
                "serial=M5AIKN00F0353YH\nusb_location=1-1.2\n"
                "product=lahaina\nslot=a\nbattery_soc_ok=yes\nresult=PASS\n",
                encoding="ascii",
            )
            preboot.chmod(0o600)
            FALLBACK.adb = lambda *args, **kwargs: FIXTURE["adb"]["devices_unauthorized"]
            values = FALLBACK.verify_unauthorized_usb("1-1.2", preboot)
            self.assertEqual(values["result"], "PASS")
        FALLBACK.USB_ROOT, FALLBACK.adb = original_root, original_adb

    def test_profile_specific_root_markers_remain_accepted(self) -> None:
        markers = FIXTURE["accepted_root_markers"]
        self.assertIn(
            markers[0],
            (REPO / "scripts/host/run-persistent-root-p2-live-gate.sh").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn(
            markers[1],
            (REPO / "initramfs/persistent-root-attest").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
