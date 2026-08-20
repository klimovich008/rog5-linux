#!/usr/bin/env python3
"""Fast checks for canonical active power/USB generation and timing."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).with_name("generate-power-usb-active.py")
SPEC = importlib.util.spec_from_file_location("power_usb_generator", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load power/USB generator")
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)

CLOSURE_SOURCE = Path(__file__).with_name("check-power-usb-active-closure.py")
CLOSURE_SPEC = importlib.util.spec_from_file_location(
    "power_usb_closure", CLOSURE_SOURCE
)
if CLOSURE_SPEC is None or CLOSURE_SPEC.loader is None:
    raise RuntimeError("cannot load power/USB closure")
CLOSURE = importlib.util.module_from_spec(CLOSURE_SPEC)
CLOSURE_SPEC.loader.exec_module(CLOSURE)


class PowerUsbGenerationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = GENERATOR.load_json(GENERATOR.SOURCE)
        self.record, self.integration = GENERATOR.validate(self.source)

    def test_regeneration_and_consumer_closure_are_clean(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SOURCE)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        GENERATOR.verify_consumer_closure(self.source)
        self.assertTrue(
            GENERATOR.SHELL_LOCK.read_bytes().startswith(b"#!/bin/sh\n")
        )
        shell = GENERATOR.SHELL_LOCK.read_text(encoding="ascii")
        self.assertIn("readonly POWER_USB_TARGET_RELEASE=", shell)
        self.assertIn("readonly POWER_USB_TARGET_TIMEOUT=", shell)
        self.assertEqual(
            GENERATOR.TARGET_LOCK.read_text(encoding="ascii").splitlines()[-1],
            f"power_usb_candidate={self.record['candidate']}",
        )

    def test_timing_lattice_is_central_and_exact(self) -> None:
        timing = GENERATOR.validate_timing(self.source, self.record)
        self.assertEqual(timing["rollback_timeout_seconds"], 600)
        mutated = deepcopy(self.source)
        mutated["timing"]["rollback_timeout_seconds"] = 599
        with self.assertRaises(GENERATOR.GenerationError):
            GENERATOR.validate_timing(mutated, mutated["record"])

    def test_generation_cannot_grant_boot_authority(self) -> None:
        mutated = deepcopy(self.source)
        mutated["integration"]["boot_policy_status"] = "allow"
        with self.assertRaises(GENERATOR.GenerationError):
            GENERATOR.validate(mutated)

    def test_generation_preserves_but_never_creates_exact_admission(self) -> None:
        record, integration = GENERATOR.validate(self.source)
        name = (
            f"{integration['output_root']}/wrapper/repack/"
            "stable-recovery-a.avb.img"
        )
        exact = f"{name}\tallow\t{integration['boot_policy_basis']}"
        with tempfile.TemporaryDirectory() as raw:
            policy = Path(raw) / "policy.tsv"
            with mock.patch.object(GENERATOR, "POLICY", policy):
                policy.write_text("name\tstatus\tbasis\n", encoding="utf-8")
                self.assertNotIn(
                    "\tallow\t",
                    GENERATOR.policy_payload(record, integration).decode(),
                )
                policy.write_text(
                    "name\tstatus\tbasis\n" + exact + "\n",
                    encoding="utf-8",
                )
                self.assertIn(
                    exact,
                    GENERATOR.policy_payload(record, integration).decode(),
                )
                policy.write_text(
                    "name\tstatus\tbasis\n"
                    "build/power-usb-observer-v3/x\tallow\tstale\n",
                    encoding="utf-8",
                )
                with self.assertRaises(GENERATOR.GenerationError):
                    GENERATOR.policy_payload(record, integration)

    def test_candidate_bundle_target_mismatch_refuses(self) -> None:
        mutated = deepcopy(self.source)
        mutated["record"]["bundle"] = "wrong"
        with self.assertRaises(GENERATOR.GenerationError):
            GENERATOR.validate(mutated)

    def test_built_receipt_verification_includes_canonical_build_root(self) -> None:
        receipt = Path("/private/built-receipt.json")
        built = CLOSURE.receipt_verify_command(receipt, "built")
        self.assertEqual(
            built[-2:],
            ["--build-root", str(CLOSURE.REPO / CLOSURE.POWER_USB.OUTPUT_ROOT)],
        )
        self.assertNotIn(
            "--build-root",
            CLOSURE.receipt_verify_command(receipt, "planned"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
