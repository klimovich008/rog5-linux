#!/usr/bin/env python3
"""Mutation tests for the ROG5 minimal-headless compatibility oracle."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/host/verify-core-compatibility-oracle.py"
PROFILE_PATH = (
    REPO / "configs/compatibility/rog5-minimal-headless-v1.json"
)
GOLDEN_CONFIG = (
    REPO / "configs/compatibility/rog5-minimal-headless-v1.config"
)
ACCEPTED_CONFIG = (
    REPO / "artifacts/network-root-v3/config-7.1.4-network-root"
)

SPEC = importlib.util.spec_from_file_location(
    "verify_core_compatibility_oracle",
    SCRIPT,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the compatibility oracle")
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


def load_profile() -> dict[str, object]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def capability(
    profile: dict[str, object],
    identity: str,
) -> dict[str, object]:
    rows = profile["capabilities"]
    if not isinstance(rows, list):
        raise AssertionError("profile capabilities are not a list")
    for row in rows:
        if isinstance(row, dict) and row.get("id") == identity:
            return row
    raise AssertionError(f"missing capability: {identity}")


def active_config(profile: dict[str, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    rows = profile["capabilities"]
    if not isinstance(rows, list):
        raise AssertionError("profile capabilities are not a list")
    for row in rows:
        if not isinstance(row, dict) or row.get("phase") != "active":
            continue
        required = row["required_config"]
        minimum = row["minimum_integer_config"]
        maximum = row["maximum_integer_config"]
        forbidden = row["forbidden_config"]
        if (
            not isinstance(required, dict)
            or not isinstance(minimum, dict)
            or not isinstance(maximum, dict)
        ):
            raise AssertionError("profile config contract is malformed")
        if not isinstance(forbidden, list):
            raise AssertionError("profile forbidden config is malformed")
        for symbol, value in required.items():
            previous = result.setdefault(symbol, value)
            if previous != value:
                raise AssertionError(f"conflicting fixture symbol: {symbol}")
        for symbol, value in minimum.items():
            try:
                old = int(result.get(symbol, "0"))
            except ValueError as error:
                raise AssertionError(
                    f"nonnumeric minimum fixture symbol: {symbol}"
                ) from error
            result[symbol] = str(max(old, value))
        for symbol, value in maximum.items():
            try:
                old = int(result.get(symbol, str(value)))
            except ValueError as error:
                raise AssertionError(
                    f"nonnumeric maximum fixture symbol: {symbol}"
                ) from error
            result[symbol] = str(min(old, value))
        for symbol in forbidden:
            previous = result.setdefault(symbol, "n")
            if previous != "n":
                raise AssertionError(f"forbidden fixture symbol: {symbol}")
    return result


def complete_config(profile: dict[str, object]) -> dict[str, str]:
    result = active_config(profile)
    rows = profile["capabilities"]
    if not isinstance(rows, list):
        raise AssertionError("profile capabilities are not a list")
    for row in rows:
        if not isinstance(row, dict):
            raise AssertionError("profile capability is not an object")
        required = row["required_config"]
        minimum = row["minimum_integer_config"]
        maximum = row["maximum_integer_config"]
        forbidden = row["forbidden_config"]
        if (
            not isinstance(required, dict)
            or not isinstance(minimum, dict)
            or not isinstance(maximum, dict)
        ):
            raise AssertionError("profile config contract is malformed")
        if not isinstance(forbidden, list):
            raise AssertionError("profile forbidden config is malformed")
        result.update(required)
        for symbol, value in minimum.items():
            try:
                old = int(result.get(symbol, "0"))
            except ValueError as error:
                raise AssertionError(
                    f"nonnumeric minimum fixture symbol: {symbol}"
                ) from error
            result[symbol] = str(max(old, value))
        for symbol, value in maximum.items():
            try:
                old = int(result.get(symbol, str(value)))
            except ValueError as error:
                raise AssertionError(
                    f"nonnumeric maximum fixture symbol: {symbol}"
                ) from error
            result[symbol] = str(min(old, value))
        for symbol in forbidden:
            result.setdefault(symbol, "n")
    return result


def render_config(config: dict[str, str]) -> str:
    lines = []
    for symbol, value in sorted(config.items()):
        if value == "n":
            lines.append(f"# {symbol} is not set")
        else:
            lines.append(f"{symbol}={value}")
    return "\n".join(lines) + "\n"


class CoreCompatibilityOracleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_profile()
        self.config = active_config(self.profile)
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-core-oracle-test-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.config_path = Path(self.temporary.name) / "active.config"
        self.config_path.write_text(
            render_config(self.config),
            encoding="utf-8",
        )

    def validate(
        self,
        profile: dict[str, object] | None = None,
        *,
        include_future: bool = False,
    ) -> tuple[int, int, str]:
        return ORACLE.validate_profile(
            REPO,
            deepcopy(profile if profile is not None else self.profile),
            self.config_path,
            include_future,
        )

    def assert_profile_fails(
        self,
        profile: dict[str, object],
        message: str,
    ) -> None:
        with self.assertRaisesRegex(ValueError, message):
            self.validate(profile)

    def test_real_profile_passes_in_explicit_metadata_mode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(REPO),
                "--profile",
                str(PROFILE_PATH),
                "--metadata-only",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("active_capabilities=6", result.stdout)
        self.assertIn("future_capabilities=8", result.stdout)
        self.assertIn("kernel_config=metadata-only", result.stdout)
        self.assertIn("new_root_state=live-pending", result.stdout)
        self.assertIn("authority=none", result.stdout)
        self.assertIn("status=metadata-only", result.stdout)

    def test_cli_requires_an_explicit_verification_mode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(REPO),
                "--profile",
                str(PROFILE_PATH),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("one of the arguments", result.stderr)

    def test_cli_translates_verifier_failure_to_nonzero_exit(self) -> None:
        bad_config = Path(self.temporary.name) / "bad.config"
        bad_config.write_text("CONFIG_ARM64=y\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(REPO),
                "--profile",
                str(PROFILE_PATH),
                "--kernel-config",
                str(bad_config),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "FAIL kernel config violates oracle: CONFIG_ARM_PSCI_FW=y",
            result.stderr,
        )

    def test_synthetic_active_config_passes(self) -> None:
        self.assertEqual(self.validate(), (6, 8, "verified"))

    def test_committed_golden_active_config_passes(self) -> None:
        self.assertEqual(
            ORACLE.validate_profile(
                REPO,
                deepcopy(self.profile),
                GOLDEN_CONFIG,
                False,
            ),
            (6, 8, "verified"),
        )

    def test_retained_accepted_config_passes_when_available(self) -> None:
        if not ACCEPTED_CONFIG.exists():
            self.skipTest("large accepted config is intentionally not in Git")
        self.assertEqual(
            ORACLE.validate_profile(
                REPO,
                deepcopy(self.profile),
                ACCEPTED_CONFIG,
                False,
            ),
            (6, 8, "verified"),
        )

    def test_missing_required_symbol_fails(self) -> None:
        config = dict(self.config)
        config.pop("CONFIG_USB_GADGET")
        with self.assertRaisesRegex(
            ValueError,
            "kernel config violates oracle: CONFIG_USB_GADGET=y",
        ):
            ORACLE.validate_kernel_config(
                config,
                deepcopy(self.profile["capabilities"]),
                False,
            )

    def test_cpu_frequency_stack_cannot_be_disabled(self) -> None:
        for symbol in (
            "CONFIG_ARM_QCOM_CPUFREQ_HW",
            "CONFIG_CPU_FREQ",
            "CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL",
            "CONFIG_CPU_FREQ_GOV_SCHEDUTIL",
        ):
            with self.subTest(symbol=symbol):
                config = dict(self.config)
                config[symbol] = "n"
                with self.assertRaisesRegex(
                    ValueError,
                    f"kernel config violates oracle: {symbol}=y",
                ):
                    ORACLE.validate_kernel_config(
                        config,
                        deepcopy(self.profile["capabilities"]),
                        False,
                    )

    def test_forbidden_symbol_enabled_fails(self) -> None:
        config = dict(self.config)
        config["CONFIG_SCSI"] = "y"
        with self.assertRaisesRegex(
            ValueError,
            "enables forbidden oracle symbol: CONFIG_SCSI",
        ):
            ORACLE.validate_kernel_config(
                config,
                deepcopy(self.profile["capabilities"]),
                False,
            )

    def test_integer_below_minimum_fails(self) -> None:
        config = dict(self.config)
        config["CONFIG_NR_CPUS"] = "7"
        with self.assertRaisesRegex(
            ValueError,
            "kernel config is below oracle minimum: CONFIG_NR_CPUS>=8",
        ):
            ORACLE.validate_kernel_config(
                config,
                deepcopy(self.profile["capabilities"]),
                False,
            )

    def test_evidence_hash_mutation_fails(self) -> None:
        profile = deepcopy(self.profile)
        profile["evidence"][0]["sha256"] = "0" * 64
        self.assert_profile_fails(profile, "evidence hash changed")

    def test_evidence_marker_mutation_fails(self) -> None:
        profile = deepcopy(self.profile)
        profile["evidence"][0]["markers"][0] = "absent evidence marker"
        self.assert_profile_fails(
            profile,
            "evidence marker is invalid or absent",
        )

    def test_duplicate_evidence_marker_fails(self) -> None:
        profile = deepcopy(self.profile)
        profile["evidence"][0]["markers"][1] = profile["evidence"][0][
            "markers"
        ][0]
        self.assert_profile_fails(
            profile,
            "evidence marker is duplicate",
        )

    def test_artifact_manifest_identity_mutation_fails(self) -> None:
        profile = deepcopy(self.profile)
        profile["artifacts"][0]["size"] += 1
        self.assert_profile_fails(
            profile,
            "artifact manifest identity changed",
        )

    def test_artifact_manifest_is_validated_by_rows_not_recursive_source_hash(self) -> None:
        self.assertNotIn("artifact_manifest_sha256", self.profile)
        manifest = ORACLE.load_artifact_manifest(
            REPO / self.profile["artifact_manifest"]
        )
        self.assertGreater(len(manifest), len(self.profile["artifacts"]))

    def test_artifact_equivalence_mutation_fails(self) -> None:
        profile = deepcopy(self.profile)
        profile["equivalence_sets"][0][1] = "accepted-7.1-config"
        self.assert_profile_fails(
            profile,
            "artifact equivalence set 0 differs",
        )

    def test_nonstring_equivalence_member_fails_cleanly(self) -> None:
        profile = deepcopy(self.profile)
        profile["equivalence_sets"][0][1] = {"not": "an identity"}
        self.assert_profile_fails(
            profile,
            "artifact equivalence set 0 is not a canonical nonempty string",
        )

    def test_candidate_identity_cannot_be_weakened(self) -> None:
        profile = deepcopy(self.profile)
        del profile["candidate"]["identity"]["authority"]
        self.assert_profile_fails(
            profile,
            "candidate identity contract is not canonical",
        )

    def test_candidate_artifact_link_mutation_fails(self) -> None:
        profile = deepcopy(self.profile)
        profile["candidate"]["artifact_links"][
            "Image"
        ] = "accepted-7.1-config"
        self.assert_profile_fails(
            profile,
            "candidate artifact ancestry changed: Image",
        )

    def test_capability_inventory_cannot_be_narrowed(self) -> None:
        profile = deepcopy(self.profile)
        profile["capabilities"].pop()
        self.assert_profile_fails(
            profile,
            "capability inventory does not cover the complete core roadmap",
        )

    def test_nonstring_capability_lists_fail_cleanly(self) -> None:
        mutations = (
            (
                "baseline_evidence",
                {"not": "evidence"},
                r"capability\[cpu-ram\]\.baseline_evidence",
            ),
            (
                "forbidden_config",
                {"not": "a symbol"},
                r"capability\[cpu-ram\]\.forbidden_config",
            ),
            (
                "ci_gates",
                {"not": "a gate"},
                r"capability\[cpu-ram\]\.ci_gates",
            ),
        )
        for field, replacement, expected in mutations:
            with self.subTest(field=field):
                profile = deepcopy(self.profile)
                capability(profile, "cpu-ram")[field] = [replacement]
                with self.assertRaisesRegex(ValueError, expected):
                    self.validate(profile)

    def test_active_gate_must_be_wired_into_ci(self) -> None:
        profile = deepcopy(self.profile)
        capability(profile, "thermal-readonly")["ci_gates"] = [
            "scripts/host/verify-core-compatibility-oracle.py"
        ]
        self.assert_profile_fails(
            profile,
            "active capability gate is absent from CI",
        )

    def test_integration_identity_cannot_be_rewired(self) -> None:
        profile = deepcopy(self.profile)
        profile["integration"][
            "build_verifier"
        ] = "scripts/host/test-repository-linux.sh"
        self.assert_profile_fails(
            profile,
            "integration identity is not canonical",
        )

    def test_future_contract_is_not_claimed_by_active_config(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "CONFIG_BATTERY_QCOM_BATTMGR=m",
        ):
            self.validate(include_future=True)

    def test_thermal_emergency_fallback_remains_future(self) -> None:
        profile = deepcopy(self.profile)
        rows = profile["capabilities"]
        profile["capabilities"] = [
            row
            for row in rows
            if row["id"] != "thermal-emergency-fallback"
        ]
        self.assert_profile_fails(
            profile,
            "capability inventory does not cover the complete core roadmap",
        )

    def test_zero_thermal_emergency_delay_is_not_claimed(self) -> None:
        config = complete_config(self.profile)
        config["CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS"] = "0"
        ORACLE.validate_kernel_config(
            config,
            deepcopy(self.profile["capabilities"]),
            False,
        )
        with self.assertRaisesRegex(
            ValueError,
            "CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS>=10000",
        ):
            ORACLE.validate_kernel_config(
                config,
                deepcopy(self.profile["capabilities"]),
                True,
            )

    def test_nonzero_thermal_emergency_delay_satisfies_future_contract(
        self,
    ) -> None:
        config = complete_config(self.profile)
        self.assertEqual(
            config["CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS"],
            "10000",
        )
        ORACLE.validate_kernel_config(
            config,
            deepcopy(self.profile["capabilities"]),
            True,
        )

    def test_excessive_thermal_emergency_delay_fails(self) -> None:
        config = complete_config(self.profile)
        config["CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS"] = "30001"
        with self.assertRaisesRegex(
            ValueError,
            "CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS<=30000",
        ):
            ORACLE.validate_kernel_config(
                config,
                deepcopy(self.profile["capabilities"]),
                True,
            )

    def test_pmic_critical_path_requires_built_in_driver(self) -> None:
        config = complete_config(self.profile)
        config["CONFIG_QCOM_SPMI_TEMP_ALARM"] = "m"
        with self.assertRaisesRegex(
            ValueError,
            "CONFIG_QCOM_SPMI_TEMP_ALARM=y",
        ):
            ORACLE.validate_kernel_config(
                config,
                deepcopy(self.profile["capabilities"]),
                True,
            )

    def test_cross_capability_config_conflict_fails_at_profile(self) -> None:
        profile = deepcopy(self.profile)
        capability(profile, "cpu-ram")[
            "minimum_integer_config"
        ]["CONFIG_PM"] = 1
        self.assert_profile_fails(
            profile,
            "capability config requirements conflict: CONFIG_PM",
        )

    def test_required_config_cannot_encode_disabled_symbol(self) -> None:
        profile = deepcopy(self.profile)
        capability(profile, "thermal-readonly")[
            "required_config"
        ]["CONFIG_UNUSED_TEST"] = "n"
        self.assert_profile_fails(
            profile,
            "capability required config is invalid",
        )

    def test_duplicate_json_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON field: value"):
            ORACLE.unique_object(
                [
                    ("value", 1),
                    ("value", 2),
                ]
            )

    def test_duplicate_json_fields_fail_through_loader(self) -> None:
        duplicate = Path(self.temporary.name) / "duplicate.json"
        duplicate.write_text(
            '{"value": 1, "value": 2}\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON field: value"):
            ORACLE.read_json(duplicate, "duplicate fixture")

    def test_symlinked_inputs_are_rejected(self) -> None:
        target = Path(self.temporary.name) / "target"
        target.write_text("CONFIG_ARM64=y\n", encoding="utf-8")
        linked = Path(self.temporary.name) / "linked"
        try:
            linked.symlink_to(target)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"symlinks unavailable: {error}")
        with self.assertRaisesRegex(ValueError, "kernel config is linked"):
            ORACLE.safe_input_file(linked, "kernel config")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(REPO),
                "--profile",
                str(PROFILE_PATH),
                "--kernel-config",
                str(linked),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL kernel config is linked", result.stderr)

    def test_duplicate_kernel_config_symbol_is_rejected(self) -> None:
        self.config_path.write_text(
            "CONFIG_ARM64=y\nCONFIG_ARM64=y\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            ValueError,
            "kernel config contains duplicate symbol: CONFIG_ARM64",
        ):
            ORACLE.parse_kernel_config(self.config_path)

    def test_non_lf_config_separator_cannot_create_symbols(self) -> None:
        self.config_path.write_text(
            "CONFIG_ARM64=y\u2028CONFIG_USB_GADGET=y\n",
            encoding="utf-8",
        )
        parsed = ORACLE.parse_kernel_config(self.config_path)
        self.assertEqual(
            parsed,
            {
                "CONFIG_ARM64": (
                    "y\u2028CONFIG_USB_GADGET=y"
                )
            },
        )

    def test_duplicate_equivalence_identity_is_rejected(self) -> None:
        profile = deepcopy(self.profile)
        profile["equivalence_sets"][0][1] = profile[
            "equivalence_sets"
        ][0][0]
        self.assert_profile_fails(
            profile,
            "artifact equivalence set 0 is invalid",
        )

    def test_unknown_candidate_artifact_identity_is_rejected(self) -> None:
        profile = deepcopy(self.profile)
        profile["candidate"]["artifact_links"]["Image"] = "unknown-artifact"
        self.assert_profile_fails(
            profile,
            "candidate references unknown artifact oracle",
        )

    def test_future_gate_need_not_be_in_current_ci(self) -> None:
        profile = deepcopy(self.profile)
        capability(profile, "sensors")["ci_gates"] = [
            "scripts/host/verify-core-compatibility-oracle.py"
        ]
        self.assertEqual(self.validate(profile), (6, 8, "verified"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
