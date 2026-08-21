#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("select-repository-test-tier.py")
SPEC = importlib.util.spec_from_file_location("tier_selector", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TierSelectorTest(unittest.TestCase):
    def test_probe_only_changes_use_fast_tier(self) -> None:
        self.assertEqual(
            MODULE.classify(
                [
                    "scripts/device/observe-early-mainline-power.sh",
                    "scripts/host/early-target-diagnostics.py",
                ]
            ),
            ("probe", "no"),
        )

    def test_docs_only_use_active_tier(self) -> None:
        self.assertEqual(
            MODULE.classify(["docs/current-state.md", "README.md"]),
            ("active", "no"),
        )

    def test_shared_lifecycle_uses_full_ci(self) -> None:
        self.assertEqual(
            MODULE.classify(
                ["scripts/host/run-minimal-headless-live-cycle.py"]
            ),
            ("ci", "no"),
        )

    def test_kernel_dtb_recovery_or_storage_changes_require_qemu(self) -> None:
        for path in (
            "initramfs/network-root-init",
            "dts/qcom/sm8350-asus.dts",
            "patches/linux/ufs.patch",
            "tools/early_target_diag/rog5-early-target-diag.c",
        ):
            with self.subTest(path=path):
                self.assertEqual(MODULE.classify([path])[1], "yes")

    def test_empty_or_unknown_change_fails_to_full_ci(self) -> None:
        self.assertEqual(MODULE.classify([]), ("ci", "yes"))
        self.assertEqual(
            MODULE.classify(["scripts/host/unknown.py"]), ("ci", "no")
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
