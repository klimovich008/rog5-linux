#!/usr/bin/env python3
"""Pure state checks for the power/USB deployment receipt."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("power-usb-deployment-receipt.py")
SPEC = importlib.util.spec_from_file_location("power_usb_receipt", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load deployment receipt verifier")
RECEIPT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RECEIPT
SPEC.loader.exec_module(RECEIPT)


def base(state: str) -> dict[str, object]:
    value: dict[str, object] = {
        "format": "rog5-power-usb-deployment-receipt-v1",
        "state": state,
        "git_head": "a" * 40,
        "active_lock": {"size": 1, "sha256": "b" * 64},
        "candidate": RECEIPT.POWER_USB.CANDIDATE,
        "candidate_record": {"size": 1, "sha256": "c" * 64},
        "expected_manifest_sha256": RECEIPT.POWER_USB.EXPECTED_MANIFEST_SHA256,
        "output_root": RECEIPT.POWER_USB.OUTPUT_ROOT,
        "mount": {"root": "/source", "options": "ro,relatime", "source": "/dev/test"},
        "served": {
            "bundle": "historical" if state == "planned" else RECEIPT.POWER_USB.BUNDLE,
            "files": {"manifest": {"size": 1, "sha256": RECEIPT.POWER_USB.EXPECTED_MANIFEST_SHA256}},
        },
        "components": {},
        "build": {},
        "policy_sha256": "d" * 64,
        "active_policy_rows": [],
    }
    if state != "planned":
        files = {
            name: {"size": index + 1, "sha256": f"{index + 1:064x}"}
            for index, name in enumerate(RECEIPT.BUILD_FILES)
        }
        files["wrapper/repack/stable-recovery-b.avb.img"] = deepcopy(
            files["wrapper/repack/stable-recovery-a.avb.img"]
        )
        files["wrapper/repack/stable-recovery-b.raw.img"] = deepcopy(
            files["wrapper/repack/stable-recovery-a.raw.img"]
        )
        for first, second in (
            (
                "wrapper/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
                "wrapper/wrapper-b/asus-kexec-stage/arch/arm64/boot/Image",
            ),
            (
                "wrapper/wrapper-a/asus-kexec-stage/.config",
                "wrapper/wrapper-b/asus-kexec-stage/.config",
            ),
            (
                "recovery/initramfs-a/rog5-stable-recovery.cpio.gz",
                "recovery/initramfs-b/rog5-stable-recovery.cpio.gz",
            ),
        ):
            files[second] = deepcopy(files[first])
        value["build"] = files
    if state == "admitted":
        value["active_policy_rows"] = ["exact\tallow\tbasis"]
    return value


class DeploymentReceiptTest(unittest.TestCase):
    def test_planned_built_and_admitted_states_pass(self) -> None:
        for state in ("planned", "built", "admitted"):
            with self.subTest(state=state):
                RECEIPT.validate(base(state))

    def test_planned_authority_and_twin_drift_refuse(self) -> None:
        planned = base("planned")
        planned["active_policy_rows"] = ["unexpected"]
        with self.assertRaises(RECEIPT.ReceiptError):
            RECEIPT.validate(planned)
        built = base("built")
        built["build"]["wrapper/repack/stable-recovery-b.avb.img"] = {
            "size": 9,
            "sha256": "f" * 64,
        }
        with self.assertRaises(RECEIPT.ReceiptError):
            RECEIPT.validate(built)


if __name__ == "__main__":
    unittest.main(verbosity=2)
