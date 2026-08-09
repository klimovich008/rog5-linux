#!/usr/bin/env python3
"""Hostile tests for the ROG Phone 5 VCNL36866 port contract."""

from __future__ import annotations

import importlib.util
from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-vcnl36866-port-contract.py"
CONTRACT = REPO / "configs/compatibility/rog5-vcnl36866-v1.json"
CANONICAL_VENDOR = REPO.parent / "kernel-src/msm-5.4"
CANONICAL_UPSTREAM = REPO / "build/linux-stable-v7.1.4-source"


def load_verifier():
    specification = importlib.util.spec_from_file_location(
        "vcnl36866_port_contract", VERIFIER
    )
    if specification is None or specification.loader is None:
        raise AssertionError("cannot load VCNL36866 verifier")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class Vcnl36866PortContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = load_verifier()
        cls.contract = cls.verifier.load_contract(CONTRACT)

    def expect_error(self, expected: str, action) -> None:
        with self.assertRaises(self.verifier.ContractError) as caught:
            action()
        self.assertIn(expected, str(caught.exception))

    def vendor_fixture(self) -> dict[str, str]:
        return {
            entry["path"]: "\n".join(entry["required_markers"])
            for entry in self.contract["vendor_sources"]
        }

    def candidate_fixture(self) -> dict[str, str]:
        return {
            entry["path"]: "\n".join(entry["required_markers"])
            for entry in self.contract["candidate_sources"]
        }

    def runtime_fixture(self) -> dict[str, object]:
        return {
            "format": "rog5-vcnl36866-readonly-runtime-v1",
            "status": "observed-not-hardware-accepted",
            "controller": "/soc@0/geniqup@9c0000/i2c@980000",
            "address": "0x60",
            "compatible": "vishay,vcnl36866",
            "driver": "vcnl36866",
            "iio_name": "vcnl36866",
            "illuminance_raw": 1234,
            "proximity_raw": 321,
            "data_surface_modes": {
                "in_illuminance_raw": "0444",
                "in_proximity_raw": "0444",
            },
            "control_surfaces": [],
            "phone_storage_access": "none",
            "authority": "none",
        }

    def test_contract_definition_is_exact(self) -> None:
        self.verifier.validate_contract(self.contract)
        self.assertEqual(self.contract["state"], "port-required")
        self.assertEqual(
            self.contract["board"]["revision_chain"][-1],
            "ZS673KS-MP5-overlay.dts",
        )

    def test_contract_source_path_sets_are_fixed(self) -> None:
        for field, expected in (
            ("vendor_sources", "vendor source path set is wrong"),
            ("upstream_gap_sources", "upstream gap source path set is wrong"),
            ("candidate_sources", "candidate source path set is wrong"),
        ):
            mutant = deepcopy(self.contract)
            mutant[field][0]["path"] = "hostile/redirected-source"
            with self.subTest(field=field):
                self.expect_error(
                    expected,
                    lambda mutant=mutant: self.verifier.validate_contract(mutant),
                )

    def test_synthetic_vendor_oracle_passes(self) -> None:
        facts = self.verifier.verify_vendor_texts(
            self.vendor_fixture(), self.contract
        )
        self.assertEqual(facts["controller_address"], "0x980000")
        self.assertEqual(facts["i2c_address"], "0x60")
        self.assertEqual(facts["chip_id"], "0x62")
        self.assertEqual(facts["irq_gpio"], 89)

    def test_every_vendor_marker_is_mandatory(self) -> None:
        fixture = self.vendor_fixture()
        for entry in self.contract["vendor_sources"]:
            for marker in entry["required_markers"]:
                mutant = dict(fixture)
                mutant[entry["path"]] = mutant[entry["path"]].replace(
                    marker, "HOSTILE_MARKER_REMOVED", 1
                )
                with self.subTest(path=entry["path"], marker=marker):
                    self.expect_error(
                        "vendor source marker is missing",
                        lambda mutant=mutant: self.verifier.verify_vendor_texts(
                            mutant, self.contract
                        ),
                    )

    def test_successor_overlay_cannot_override_sensor(self) -> None:
        fixture = self.vendor_fixture()
        successor = self.contract["board"]["revision_chain"][1]
        path = f"arch/arm64/boot/dts/vendor/qcom/{successor}"
        fixture[path] += '\nvcnl36866@60 { status = "disabled"; };\n'
        self.expect_error(
            "successor overlay overrides VCNL36866",
            lambda: self.verifier.verify_vendor_texts(fixture, self.contract),
        )

    def test_current_upstream_is_classified_as_port_required(self) -> None:
        gap = {
            entry["path"]: "\n".join(entry["required_gap_markers"])
            for entry in self.contract["upstream_gap_sources"]
        }
        self.assertEqual(
            self.verifier.classify_upstream_texts(gap, self.contract),
            "port-required",
        )
        first = self.contract["upstream_gap_sources"][0]
        gap[first["path"]] += "\nvishay,vcnl36866\n"
        self.expect_error(
            "partial or unreviewed VCNL36866 support",
            lambda: self.verifier.classify_upstream_texts(gap, self.contract),
        )

    def test_complete_candidate_source_contract_passes(self) -> None:
        self.assertEqual(
            self.verifier.classify_upstream_texts(
                self.candidate_fixture(), self.contract
            ),
            "candidate-ready-not-hardware-accepted",
        )

    def test_every_candidate_marker_is_mandatory(self) -> None:
        fixture = self.candidate_fixture()
        for entry in self.contract["candidate_sources"]:
            for marker in entry["required_markers"]:
                mutant = dict(fixture)
                mutant[entry["path"]] = mutant[entry["path"]].replace(
                    marker, "HOSTILE_MARKER_REMOVED", 1
                )
                with self.subTest(path=entry["path"], marker=marker):
                    self.expect_error(
                        "partial or unreviewed VCNL36866 support",
                        lambda mutant=mutant: self.verifier.classify_upstream_texts(
                            mutant, self.contract
                        ),
                    )

    def test_candidate_forbidden_surfaces_are_rejected(self) -> None:
        fixture = self.candidate_fixture()
        driver = "drivers/iio/light/vcnl36866.c"
        for marker in self.contract["candidate_forbidden_markers"]:
            mutant = dict(fixture)
            mutant[driver] += f"\n{marker}\n"
            with self.subTest(marker=marker):
                self.expect_error(
                    "partial or unreviewed VCNL36866 support",
                    lambda mutant=mutant: self.verifier.classify_upstream_texts(
                        mutant, self.contract
                    ),
                )

    def test_runtime_readonly_record_passes(self) -> None:
        result = self.verifier.verify_runtime_record(
            self.runtime_fixture(), self.contract
        )
        self.assertEqual(result, "observed-not-hardware-accepted")

    def test_runtime_identity_and_topology_are_exact(self) -> None:
        mutations = {
            "controller": "/soc@0/i2c@984000",
            "address": "0x61",
            "compatible": "vishay,vcnl4040",
            "driver": "vcnl4000",
            "iio_name": "vcnl4040",
            "phone_storage_access": "read-only",
            "authority": "boot",
        }
        for field, value in mutations.items():
            record = self.runtime_fixture()
            record[field] = value
            with self.subTest(field=field):
                self.expect_error(
                    f"runtime field is wrong: {field}",
                    lambda record=record: self.verifier.verify_runtime_record(
                        record, self.contract
                    ),
                )

    def test_runtime_values_and_surfaces_are_bounded(self) -> None:
        for field, value in (
            ("illuminance_raw", -1),
            ("illuminance_raw", 65536),
            ("proximity_raw", -1),
            ("proximity_raw", 65536),
        ):
            record = self.runtime_fixture()
            record[field] = value
            with self.subTest(field=field, value=value):
                self.expect_error(
                    f"runtime reading is out of range: {field}",
                    lambda record=record: self.verifier.verify_runtime_record(
                        record, self.contract
                    ),
                )

        writable = self.runtime_fixture()
        writable["data_surface_modes"]["in_proximity_raw"] = "0644"
        self.expect_error(
            "runtime data surface is writable",
            lambda: self.verifier.verify_runtime_record(writable, self.contract),
        )

        control = self.runtime_fixture()
        control["control_surfaces"] = ["in_proximity_thresh_rising_value"]
        self.expect_error(
            "runtime control surface is present",
            lambda: self.verifier.verify_runtime_record(control, self.contract),
        )

    def test_runtime_record_rejects_missing_or_extra_fields(self) -> None:
        missing = self.runtime_fixture()
        del missing["driver"]
        self.expect_error(
            "runtime record fields are not exact",
            lambda: self.verifier.verify_runtime_record(missing, self.contract),
        )
        extra = self.runtime_fixture()
        extra["accepted"] = True
        self.expect_error(
            "runtime record fields are not exact",
            lambda: self.verifier.verify_runtime_record(extra, self.contract),
        )

    def test_real_vendor_source_integration(self) -> None:
        source = Path(
            os.environ.get("ROG5_ASUS_5_4_SOURCE", str(CANONICAL_VENDOR))
        )
        if not source.exists():
            self.skipTest("retained ASUS 5.4 source is optional in CI")
        facts = self.verifier.verify_vendor_source(source, self.contract)
        self.assertEqual(facts["compatible"], "qcom,vcnl36866")

    def test_real_upstream_gap_integration(self) -> None:
        source = Path(
            os.environ.get(
                "ROG5_ACCEPTED_KERNEL_SOURCE", str(CANONICAL_UPSTREAM)
            )
        )
        if not source.exists():
            self.skipTest("retained Linux 7.1.4 source is optional in CI")
        self.assertEqual(
            self.verifier.verify_upstream_source(source, self.contract),
            "port-required",
        )

    def test_source_root_and_files_fail_closed(self) -> None:
        self.expect_error(
            "source root must be an absolute non-linked directory",
            lambda: self.verifier.verify_vendor_source(
                Path("relative-vendor-source"), self.contract
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            linked = root / "vendor-link"
            linked.symlink_to(CANONICAL_VENDOR)
            self.expect_error(
                "source root must be an absolute non-linked directory",
                lambda: self.verifier.verify_vendor_source(
                    linked, self.contract
                ),
            )

            if CANONICAL_VENDOR.is_dir():
                copied = root / "vendor"
                copied.mkdir()
                entry = self.contract["vendor_sources"][0]
                target = copied / entry["path"]
                target.parent.mkdir(parents=True)
                target.symlink_to(CANONICAL_VENDOR / entry["path"])
                self.expect_error(
                    "unsafe source file",
                    lambda: self.verifier.verify_vendor_source(
                        copied, self.contract
                    ),
                )

    def test_cli_reports_both_current_oracles(self) -> None:
        vendor = Path(
            os.environ.get("ROG5_ASUS_5_4_SOURCE", str(CANONICAL_VENDOR))
        )
        upstream = Path(
            os.environ.get(
                "ROG5_ACCEPTED_KERNEL_SOURCE", str(CANONICAL_UPSTREAM)
            )
        )
        if not vendor.is_dir() or not upstream.is_dir():
            self.skipTest("retained source trees are optional in CI")
        completed = subprocess.run(
            [
                str(VERIFIER),
                "--contract",
                str(CONTRACT),
                "--vendor-source",
                str(vendor),
                "--upstream-source",
                str(upstream),
            ],
            cwd=REPO,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("vendor_oracle=verified", completed.stdout)
        self.assertIn("upstream_state=port-required", completed.stdout)
        self.assertIn("authority=none", completed.stdout)


if __name__ == "__main__":
    unittest.main()
