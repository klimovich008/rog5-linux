#!/usr/bin/env python3
"""Fast pure checks for host-doctor receipt validation."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("rog5-host-doctor.py")
SPEC = importlib.util.spec_from_file_location("rog5_host_doctor", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load host doctor")
DOCTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DOCTOR
SPEC.loader.exec_module(DOCTOR)


def clean_receipt() -> dict[str, object]:
    return {
        "format": "rog5-host-doctor-receipt-v1",
        "mode": "build",
        "host_boot_id": "11111111-2222-3333-4444-555555555555",
        "captured_unix": 1,
        "git_head": "a" * 40,
        "active_lock_sha256": "b" * 64,
        "deployment_receipt_sha256": "none",
        "disk": {"available_bytes": 100_000_000_000, "available_inodes": 2_000_000},
        "build_processes": [],
        "mount": {"target": DOCTOR.MOUNT_TARGET, "root": "/source", "mount_options": "ro", "source": "/dev/test"},
        "served_bundle": {"inventory": ["historical"], "manifest_sha256": "c" * 64},
        "installed": {"/installed": "d" * 64},
        "listeners": ["tcp:0100007F:8080"],
        "binfmt": {"entries": {}, "sha256": "e" * 64},
        "network": {
            "networkmanager": [
                str(DOCTOR.POWER_USB.HOST["networkmanager_profile"]),
                "enp4s0f3u1u2",
                "no",
                "manual",
                "169.254.77.1/30",
                "yes",
            ],
            "firewalld_active_zones": ["public"],
            "rog5_routes": [],
        },
        "usb": {"mode": "android", "location": "1-1.2", "serial": DOCTOR.SERIAL},
    }


class HostDoctorTest(unittest.TestCase):
    def test_clean_receipt_and_identical_state_pass(self) -> None:
        value = clean_receipt()
        DOCTOR.validate(value)
        DOCTOR.validate(value, current=deepcopy(value))

    def test_headroom_process_listener_route_and_drift_refuse(self) -> None:
        mutations = (
            ("disk", {"available_bytes": 1, "available_inodes": 2_000_000}),
            ("build_processes", ["1:build-mainline"]),
            ("listeners", ["tcp:00000000:2049"]),
        )
        for name, value in mutations:
            receipt = clean_receipt()
            receipt[name] = value
            with self.assertRaises(DOCTOR.DoctorError):
                DOCTOR.validate(receipt)
        receipt = clean_receipt()
        receipt["network"]["rog5_routes"] = ["169.254.77.0/30 dev stale"]
        with self.assertRaises(DOCTOR.DoctorError):
            DOCTOR.validate(receipt)
        current = clean_receipt()
        current["mount"] = {"target": DOCTOR.MOUNT_TARGET, "root": "/changed", "mount_options": "ro", "source": "/dev/test"}
        with self.assertRaises(DOCTOR.DoctorError):
            DOCTOR.validate(clean_receipt(), current=current)

    def test_build_mode_never_invokes_adb_or_fastboot(self) -> None:
        payload = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('Path("/usr/bin/adb")', payload)
        self.assertNotIn('Path("/usr/bin/fastboot")', payload)

    def test_receipt_verification_rechecks_current_headroom_and_build_processes(self) -> None:
        expected = clean_receipt()
        for key, value in (
            ("disk", {"available_bytes": 1, "available_inodes": 2_000_000}),
            ("disk", {"available_bytes": 100_000_000_000, "available_inodes": 1}),
            ("build_processes", ["123:build-mainline"]),
        ):
            current = clean_receipt()
            current[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(DOCTOR.DoctorError):
                DOCTOR.validate(expected, current=current)


if __name__ == "__main__":
    unittest.main(verbosity=2)
