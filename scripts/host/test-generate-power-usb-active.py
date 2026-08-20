#!/usr/bin/env python3
"""Fast checks for canonical active power/USB generation and timing."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


SOURCE = Path(__file__).with_name("generate-power-usb-active.py")
SPEC = importlib.util.spec_from_file_location("power_usb_generator", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load power/USB generator")
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)


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

    def test_candidate_bundle_target_mismatch_refuses(self) -> None:
        mutated = deepcopy(self.source)
        mutated["record"]["bundle"] = "wrong"
        with self.assertRaises(GENERATOR.GenerationError):
            GENERATOR.validate(mutated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
