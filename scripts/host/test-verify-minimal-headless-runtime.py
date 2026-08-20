#!/usr/bin/env python3
"""Mutation tests for the minimal-headless runtime record verifier."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/host/verify-minimal-headless-runtime.py"
PROBE = REPO / "scripts/device/collect-minimal-headless-runtime.sh"
BOOT_ID = "7d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8"
SPEC = importlib.util.spec_from_file_location(
    "verify_minimal_headless_runtime",
    SCRIPT,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the runtime acceptance verifier")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def golden_values() -> dict[str, str]:
    values = dict(VERIFIER.EXACT_VALUES)
    values.update(
        VERIFIER.USB_GADGET_CONTRACTS[VERIFIER.HISTORICAL_PROFILE]
    )
    values.update(
        {
            "probe_sha256": hashlib.sha256(PROBE.read_bytes()).hexdigest(),
            "candidate": VERIFIER.HISTORICAL_CANDIDATE,
            "boot_id": BOOT_ID,
            "kernel_release": "7.1.4-g7a5cef0db479",
            "cpu_online_count": "8",
            "memory_total_kib": "11900000",
            "memory_available_kib": "10949632",
            "overlay_mount_id": "101",
            "overlay_lower_mount_id": "102",
            "state_mount_id": "103",
            "thermal_zone_count": "33",
            "thermal_min_millidegree_c": "32000",
            "thermal_max_millidegree_c": "37000",
            "watchdog_timeout_seconds": "600",
            "watchdog_remaining_seconds": "300",
            "root_generation": "arch-a",
            "root_tree_sha256": (
                "7c35d2b75f09722afd4fa59135f4327a"
                "29c4d612441b1e165908f4777b458afb"
            ),
            "root_seal_sha256": (
                "6cd986cae4918effc236d28ee5034403"
                "2795853b546296a94e9431508fa32896"
            ),
            "root_seal_file_sha256": (
                "6cd986cae4918effc236d28ee5034403"
                "2795853b546296a94e9431508fa32896"
            ),
            "root_tree_entries": "37669",
            "root_subtree": "/",
            "command_manifest_sha256": (
                "99f194b32171c9c9f09d28636e351bb"
                "a4cb34751997e1aa174e3466bd758a1d2"
            ),
        }
    )
    if set(values) != set(VERIFIER.FIELDS):
        raise AssertionError("golden runtime record does not cover the schema")
    return values


def render(values: dict[str, str]) -> bytes:
    return "".join(
        f"{field}={values[field]}\n" for field in VERIFIER.FIELDS
    ).encode("ascii")


class MinimalHeadlessRuntimeVerifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-runtime-acceptance-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.record = self.directory / "runtime.record"
        self.candidate_record = self.directory / "candidate.json"
        candidate = json.loads(
            (
                REPO
                / "configs/recovery-candidates/"
                "headless-ssh-network-root-v3.json"
            ).read_text(encoding="ascii")
        )
        candidate["bundle"] = VERIFIER.DEPLOYMENT_BUNDLE
        candidate["root_tree_sha256"] = "4" * 64
        candidate["root_seal_sha256"] = "5" * 64
        candidate["root_tree_entries"] = "37736"
        self.candidate_record.write_text(
            json.dumps(candidate, indent=2) + "\n",
            encoding="ascii",
        )
        self.candidate_record.chmod(0o400)
        self.candidate = candidate
        self.candidate_sha256 = hashlib.sha256(
            self.candidate_record.read_bytes()
        ).hexdigest()
        self.values = golden_values()
        self.write(self.values)

    def write(self, values: dict[str, str], data: bytes | None = None) -> None:
        self.record.write_bytes(render(values) if data is None else data)
        self.record.chmod(0o600)

    def verify(
        self,
        values: dict[str, str] | None = None,
        *,
        expected_boot_id: str = BOOT_ID,
        deployment: bool = False,
        candidate_record: Path | None = None,
        candidate_sha256: str | None = None,
    ) -> tuple[str, dict[str, str]]:
        if values is not None:
            self.write(values)
        return VERIFIER.verify_record(
            REPO,
            self.record,
            expected_boot_id,
            (
                VERIFIER.DEPLOYMENT_PROFILE
                if deployment
                else VERIFIER.HISTORICAL_PROFILE
            ),
            (
                self.candidate_record
                if deployment and candidate_record is None
                else candidate_record
            ),
            (
                self.candidate_sha256
                if deployment and candidate_sha256 is None
                else (candidate_sha256 or "")
            ),
        )

    def deployment_values(self) -> dict[str, str]:
        values = deepcopy(self.values)
        values.update(
            {
                "candidate": VERIFIER.DEPLOYMENT_CANDIDATE,
                "kernel_release": self.candidate["target_release"],
                "watchdog_timeout_seconds": self.candidate[
                    "rollback_timeout"
                ],
                "root_generation": self.candidate["root_generation"],
                "root_tree_sha256": self.candidate["root_tree_sha256"],
                "root_seal_sha256": self.candidate["root_seal_sha256"],
                "root_seal_file_sha256": self.candidate[
                    "root_seal_sha256"
                ],
                "root_tree_entries": self.candidate["root_tree_entries"],
                "root_subtree": self.candidate["root_subtree"],
                "command_manifest_sha256": self.candidate[
                    "a660_command_manifest_sha256"
                ],
            }
        )
        return values

    def assert_mutation_fails(
        self,
        field: str,
        value: str,
        message: str,
    ) -> None:
        mutated = deepcopy(self.values)
        mutated[field] = value
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            message,
        ):
            self.verify(mutated)

    def test_golden_record_passes(self) -> None:
        digest, values = self.verify()
        self.assertEqual(digest, hashlib.sha256(render(self.values)).hexdigest())
        self.assertEqual(values["result"], "PASS")

    def test_deployment_record_is_bound_to_external_candidate(self) -> None:
        values = self.deployment_values()
        digest, verified = self.verify(values, deployment=True)
        self.assertEqual(digest, hashlib.sha256(render(values)).hexdigest())
        self.assertEqual(
            verified["candidate"],
            VERIFIER.DEPLOYMENT_CANDIDATE,
        )

    def test_core_record_is_bound_to_exact_external_candidate(self) -> None:
        path = self.directory / "core-candidate.json"
        candidate = json.loads(
            (REPO / "configs/recovery-candidates/headless-core-network-root-v2.json").read_text(encoding="ascii")
        )
        candidate["bundle"] = VERIFIER.CORE_BUNDLE
        candidate["root_tree_sha256"] = "7" * 64
        candidate["root_seal_sha256"] = "8" * 64
        candidate["root_tree_entries"] = "37740"
        path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="ascii")
        path.chmod(0o400)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        values = self.deployment_values()
        values["candidate"] = VERIFIER.CORE_CANDIDATE
        for name in (
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_tree_entries",
            "root_subtree",
        ):
            values[name] = candidate[name]
        values["root_seal_file_sha256"] = candidate["root_seal_sha256"]
        self.write(values)
        verified_digest, verified = VERIFIER.verify_record(
            REPO,
            self.record,
            BOOT_ID,
            VERIFIER.CORE_PROFILE,
            path,
            digest,
        )
        self.assertEqual(verified_digest, hashlib.sha256(render(values)).hexdigest())
        self.assertEqual(verified["candidate"], VERIFIER.CORE_CANDIDATE)

    def test_power_usb_record_is_bound_to_exact_external_candidate(self) -> None:
        path = self.directory / "power-usb-candidate.json"
        candidate = json.loads(
            (REPO / "configs/recovery-candidates/headless-power-usb-observer-v3.json").read_text(encoding="ascii")
        )
        candidate["root_tree_sha256"] = "9" * 64
        candidate["root_seal_sha256"] = "a" * 64
        candidate["root_tree_entries"] = "37741"
        path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="ascii")
        path.chmod(0o400)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        values = self.deployment_values()
        values.update(VERIFIER.USB_GADGET_CONTRACTS[VERIFIER.POWER_USB_PROFILE])
        values["candidate"] = VERIFIER.POWER_USB_CANDIDATE
        for name in (
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_tree_entries",
            "root_subtree",
        ):
            values[name] = candidate[name]
        values["root_seal_file_sha256"] = candidate["root_seal_sha256"]
        values["kernel_release"] = candidate["target_release"]
        values["watchdog_timeout_seconds"] = candidate["rollback_timeout"]
        values["command_manifest_sha256"] = candidate[
            "a660_command_manifest_sha256"
        ]
        self.write(values)
        verified_digest, verified = VERIFIER.verify_record(
            REPO,
            self.record,
            BOOT_ID,
            VERIFIER.POWER_USB_PROFILE,
            path,
            digest,
        )
        self.assertEqual(verified_digest, hashlib.sha256(render(values)).hexdigest())
        self.assertEqual(verified["candidate"], VERIFIER.POWER_USB_CANDIDATE)

    def test_diagnostic_record_requires_exact_ncm_acm_gadget(self) -> None:
        candidate_path = self.directory / "diagnostic-candidate.json"
        candidate = json.loads(
            (
                REPO
                / "configs/recovery-candidates/"
                "headless-netroot-early-diag-v2.json"
            ).read_text(encoding="ascii")
        )
        candidate["root_tree_sha256"] = "4" * 64
        candidate["root_seal_sha256"] = "5" * 64
        candidate["root_tree_entries"] = "37736"
        candidate_path.write_text(
            json.dumps(candidate, indent=2) + "\n",
            encoding="ascii",
        )
        candidate_path.chmod(0o400)
        candidate_sha256 = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        values = deepcopy(self.values)
        values.update(
            {
                "candidate": VERIFIER.DIAGNOSTIC_CANDIDATE,
                "kernel_release": candidate["target_release"],
                "watchdog_timeout_seconds": candidate["rollback_timeout"],
                "root_generation": candidate["root_generation"],
                "root_tree_sha256": candidate["root_tree_sha256"],
                "root_seal_sha256": candidate["root_seal_sha256"],
                "root_seal_file_sha256": candidate["root_seal_sha256"],
                "root_tree_entries": candidate["root_tree_entries"],
                "root_subtree": candidate["root_subtree"],
                "command_manifest_sha256": candidate[
                    "a660_command_manifest_sha256"
                ],
            }
        )
        values.update(
            VERIFIER.USB_GADGET_CONTRACTS[VERIFIER.DIAGNOSTIC_PROFILE]
        )
        self.write(values)
        digest, verified = VERIFIER.verify_record(
            REPO,
            self.record,
            BOOT_ID,
            VERIFIER.DIAGNOSTIC_PROFILE,
            candidate_path,
            candidate_sha256,
        )
        self.assertEqual(digest, hashlib.sha256(render(values)).hexdigest())
        self.assertEqual(
            verified["usb_function"],
            "acm.usb0,ncm.usb0",
        )

        values["usb_function"] = "ncm.usb0"
        self.write(values)
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "runtime USB gadget value changed: usb_function",
        ):
            VERIFIER.verify_record(
                REPO,
                self.record,
                BOOT_ID,
                VERIFIER.DIAGNOSTIC_PROFILE,
                candidate_path,
                candidate_sha256,
            )

    def test_deployment_profile_never_falls_back_to_historical(self) -> None:
        self.write(self.deployment_values())
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "deployment candidate record is required",
        ):
            VERIFIER.verify_record(
                REPO,
                self.record,
                BOOT_ID,
                VERIFIER.DEPLOYMENT_PROFILE,
                None,
                self.candidate_sha256,
            )

    def test_deployment_candidate_hash_is_exact(self) -> None:
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "deployment candidate identity changed",
        ):
            self.verify(
                self.deployment_values(),
                deployment=True,
                candidate_sha256="6" * 64,
            )

    def test_tracked_fixture_candidate_cannot_be_promoted(self) -> None:
        fixture = (
            REPO
            / "configs/recovery-candidates/"
            "headless-ssh-network-root-v3.json"
        )
        fixture_copy = self.directory / "fixture-candidate.json"
        fixture_candidate = json.loads(fixture.read_text(encoding="ascii"))
        fixture_candidate["bundle"] = VERIFIER.DEPLOYMENT_BUNDLE
        fixture_copy.write_text(
            json.dumps(fixture_candidate, indent=2) + "\n",
            encoding="ascii",
        )
        fixture_copy.chmod(0o400)
        fixture_hash = hashlib.sha256(fixture_copy.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "still carries fixture root identity",
        ):
            self.verify(
                self.deployment_values(),
                deployment=True,
                candidate_record=fixture_copy,
                candidate_sha256=fixture_hash,
            )

    def test_candidate_inside_repository_is_rejected(self) -> None:
        fixture = (
            REPO
            / "configs/recovery-candidates/"
            "headless-ssh-network-root-v3.json"
        )
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "must remain outside the repository",
        ):
            self.verify(
                self.deployment_values(),
                deployment=True,
                candidate_record=fixture,
                candidate_sha256=hashlib.sha256(
                    fixture.read_bytes()
                ).hexdigest(),
            )

    def test_historical_profile_rejects_dynamic_candidate(self) -> None:
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "historical profile does not accept a dynamic candidate",
        ):
            VERIFIER.verify_record(
                REPO,
                self.record,
                BOOT_ID,
                VERIFIER.HISTORICAL_PROFILE,
                self.candidate_record,
                self.candidate_sha256,
            )

    def test_cli_passes_and_reports_bounded_summary(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(REPO),
                "--record",
                str(self.record),
                "--expected-boot-id",
                BOOT_ID,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS minimal headless runtime acceptance", result.stdout)
        self.assertIn("active_capabilities=6", result.stdout)
        self.assertIn("boot_id=verified", result.stdout)
        self.assertNotIn(BOOT_ID, result.stdout)

    def test_every_exact_acceptance_value_is_fail_closed(self) -> None:
        for field in VERIFIER.EXACT_VALUES:
            with self.subTest(field=field):
                replacement = "changed"
                if field == "probe_sha256":
                    replacement = "1" * 64
                self.assert_mutation_fails(
                    field,
                    replacement,
                    "runtime acceptance value changed"
                    if field != "probe_sha256"
                    else "runtime acceptance value changed",
                )

    def test_every_standard_usb_gadget_value_is_fail_closed(self) -> None:
        for field in VERIFIER.USB_GADGET_CONTRACTS[
            VERIFIER.HISTORICAL_PROFILE
        ]:
            with self.subTest(field=field):
                self.assert_mutation_fails(
                    field,
                    "changed",
                    f"runtime USB gadget value changed: {field}",
                )

    def test_test_fixture_record_cannot_be_promoted(self) -> None:
        self.assert_mutation_fails(
            "execution_mode",
            "test",
            "runtime acceptance value changed: execution_mode",
        )

    def test_probe_hash_is_bound_to_current_source(self) -> None:
        self.assert_mutation_fails(
            "probe_sha256",
            "1" * 64,
            "runtime probe identity changed",
        )

    def test_stale_boot_identity_fails(self) -> None:
        self.assert_mutation_fails(
            "boot_id",
            "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            "runtime record boot identity is stale",
        )

    def test_invalid_expected_boot_identity_fails(self) -> None:
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "expected boot identity is invalid",
        ):
            self.verify(expected_boot_id="not-a-boot-id")

    def test_kernel_is_bound_to_candidate(self) -> None:
        self.assert_mutation_fails(
            "kernel_release",
            "7.2.0-unreviewed",
            "runtime kernel does not match the candidate",
        )

    def test_exact_cpu_count_is_enforced(self) -> None:
        for count in ("7", "9"):
            with self.subTest(count=count):
                self.assert_mutation_fails(
                    "cpu_online_count",
                    count,
                    "does not have exactly eight online CPUs",
                )

    def test_cpu_policy_topology_is_fail_closed(self) -> None:
        mutations = (
            ("cpu_online_set", "0-6"),
            ("cpu_present_set", "0-8"),
            ("cpufreq_policy_count", "2"),
            ("cpufreq_policy_names", "policy0;policy4"),
            ("cpufreq_policy_cpu_sets", "0 1 2 3;4 5 6 7"),
            ("cpufreq_policy_drivers", "qcom-cpufreq-hw"),
            ("cpufreq_policy_governors", "performance;performance;performance"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                self.assert_mutation_fails(
                    field,
                    value,
                    f"runtime acceptance value changed: {field}",
                )

    def test_memory_envelope_is_enforced(self) -> None:
        mutations = (
            ("memory_total_kib", str(10 * 1024 * 1024 - 1)),
            ("memory_available_kib", str(8 * 1024 * 1024 - 1)),
            ("memory_available_kib", "12000000"),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                message = (
                    "total memory is below"
                    if field == "memory_total_kib"
                    else "available memory is outside"
                )
                self.assert_mutation_fails(field, value, message)

    def test_storage_mount_identity_is_canonical_and_distinct(self) -> None:
        mutations = (
            (
                "overlay_mount_id",
                "0101",
                "overlay_mount_id storage mount ID is not a canonical decimal",
            ),
            (
                "overlay_mount_id",
                "0",
                "storage mount identities are zero or duplicated",
            ),
            (
                "overlay_lower_mount_id",
                "101",
                "storage mount identities are zero or duplicated",
            ),
        )
        for field, value, message in mutations:
            with self.subTest(field=field, value=value):
                self.assert_mutation_fails(field, value, message)

    def test_decimal_encoding_is_canonical(self) -> None:
        self.assert_mutation_fails(
            "cpu_online_count",
            "08",
            "online CPU count is not a canonical decimal",
        )
        self.assert_mutation_fails(
            "thermal_min_millidegree_c",
            "-0",
            "minimum thermal value is not a canonical signed decimal",
        )

    def test_thermal_envelope_is_enforced(self) -> None:
        mutations = (
            ("thermal_zone_count", "29"),
            ("thermal_zone_count", "129"),
            ("thermal_min_millidegree_c", "-20001"),
            ("thermal_max_millidegree_c", "120001"),
            ("thermal_min_millidegree_c", "38000"),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                message = (
                    "thermal-zone count"
                    if field == "thermal_zone_count"
                    else "thermal values"
                )
                self.assert_mutation_fails(field, value, message)

    def test_watchdog_window_is_bound_to_candidate(self) -> None:
        mutations = (
            ("watchdog_timeout_seconds", "599", "does not match"),
            ("watchdog_remaining_seconds", "59", "outside the live gate"),
            ("watchdog_remaining_seconds", "601", "outside the live gate"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field, value=value):
                self.assert_mutation_fails(field, value, message)

    def test_every_candidate_root_identity_is_bound(self) -> None:
        for field in (
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_seal_file_sha256",
            "root_tree_entries",
            "root_subtree",
            "command_manifest_sha256",
        ):
            with self.subTest(field=field):
                replacement = "changed"
                if field.endswith("sha256"):
                    replacement = "1" * 64
                self.assert_mutation_fails(
                    field,
                    replacement,
                    f"runtime root identity does not match candidate: {field}",
                )

    def test_field_order_missing_duplicate_and_extra_are_rejected(self) -> None:
        lines = render(self.values).decode("ascii").splitlines()
        malformed = (
            "\n".join((lines[1], lines[0], *lines[2:])) + "\n",
            "\n".join(lines[:-1]) + "\n",
            "\n".join((*lines, lines[-1])) + "\n",
            "\n".join((*lines, "extra=value")) + "\n",
        )
        for index, text in enumerate(malformed):
            with self.subTest(index=index):
                self.write(self.values, text.encode("ascii"))
                with self.assertRaisesRegex(
                    VERIFIER.RuntimeAcceptanceError,
                    "field",
                ):
                    self.verify()

    def test_non_ascii_crlf_and_missing_final_lf_are_rejected(self) -> None:
        payload = render(self.values)
        malformed = (
            payload[:-1],
            payload.replace(b"\n", b"\r\n", 1),
            payload.replace(b"PASS", b"P\xffSS"),
        )
        for index, data in enumerate(malformed):
            with self.subTest(index=index):
                self.write(self.values, data)
                with self.assertRaisesRegex(
                    VERIFIER.RuntimeAcceptanceError,
                    "runtime record",
                ):
                    self.verify()

    def test_symlink_and_open_mode_are_rejected(self) -> None:
        target = self.directory / "target.record"
        target.write_bytes(render(self.values))
        target.chmod(0o600)
        self.record.unlink()
        self.record.symlink_to(target)
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "runtime record is linked",
        ):
            self.verify()
        self.record.unlink()
        self.record.write_bytes(render(self.values))
        self.record.chmod(0o644)
        with self.assertRaisesRegex(
            VERIFIER.RuntimeAcceptanceError,
            "runtime record metadata is unsafe",
        ):
            self.verify()

    def test_cli_translates_rejection_to_nonzero(self) -> None:
        values = deepcopy(self.values)
        values["watchdog_remaining_seconds"] = "0"
        self.write(values)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--record",
                str(self.record),
                "--expected-boot-id",
                BOOT_ID,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL runtime watchdog remaining time", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_record_must_be_owned_by_the_verifier_caller(self) -> None:
        self.assertEqual(self.record.stat().st_uid, os.geteuid())


if __name__ == "__main__":
    unittest.main()
