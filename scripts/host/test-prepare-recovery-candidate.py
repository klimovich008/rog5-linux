#!/usr/bin/env python3
"""Offline tests for the strict candidate-to-bundle adapter."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO / "scripts" / "host" / "prepare-recovery-candidate.py"


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_candidate_runner_test",
        RUNNER_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load candidate runner")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


RUNNER = load_module()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class RecoveryCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("openssl") is None:
            raise RuntimeError("openssl is required")
        cls.original_repo = RUNNER.REPO
        cls.original_candidate_root = RUNNER.CANDIDATE_ROOT

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.candidates = self.repo / "configs" / "recovery-candidates"
        self.artifacts = self.repo / "artifacts" / "fixture"
        self.candidates.mkdir(parents=True)
        self.artifacts.mkdir(parents=True)
        self.payloads = {
            "Image": bytes(range(64)),
            "board.dtb": b"D" * 40,
            "initramfs.cpio.gz": b"\x1f\x8b",
        }
        self.paths = {
            "Image": "artifacts/fixture/Image",
            "board.dtb": "artifacts/fixture/board.dtb",
            "initramfs.cpio.gz": "artifacts/fixture/initramfs.cpio.gz",
        }
        for name, payload in self.payloads.items():
            destination = self.repo / self.paths[name]
            destination.write_bytes(payload)
            destination.chmod(0o444)
        self.record = {
            "format": "rog5-recovery-candidate-v1",
            "candidate": "fixture",
            "status": "consumed",
            "authority": "none",
            "bundle": "fixture",
            "profile": "persistent-root-ro-v1",
            "target_id": "fixture",
            "target_release": "7.1.4-test",
            "rollback_timeout": "600",
            "target_timeout": "480",
            "a660_command_manifest_sha256": "0" * 64,
            "root_generation": "none",
            "root_tree_sha256": "0" * 64,
            "root_seal_sha256": "0" * 64,
            "root_tree_entries": "0",
            "root_subtree": "none",
            "artifacts": {
                name: {
                    "path": self.paths[name],
                    "size": len(self.payloads[name]),
                    "sha256": sha256(self.payloads[name]),
                }
                for name in RUNNER.ARTIFACT_NAMES
            },
        }
        self.write_record(self.record)
        self.private_key = self.root / "test-ed25519.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(self.private_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.private_key.chmod(0o600)
        self.bundle_root = self.root / "bundles"
        self.bundle_root.mkdir(mode=0o700)
        RUNNER.REPO = self.repo
        RUNNER.CANDIDATE_ROOT = self.candidates

    def tearDown(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        self.temporary.cleanup()

    def write_record(self, record: dict) -> None:
        path = self.candidates / f"{record['candidate']}.json"
        path.write_text(
            json.dumps(record, indent=2) + "\n",
            encoding="ascii",
        )
        path.chmod(0o644)

    def test_consumed_candidate_packages_offline(self) -> None:
        record, manifest_hash, trust_hash = RUNNER.prepare(
            "fixture",
            self.private_key,
            self.bundle_root,
        )
        self.assertEqual(record["authority"], "none")
        self.assertRegex(manifest_hash, r"^[0-9a-f]{64}$")
        self.assertRegex(trust_hash, r"^[0-9a-f]{64}$")
        bundle = self.bundle_root / "fixture"
        self.assertEqual(
            {path.name for path in bundle.iterdir()},
            {
                "Image",
                "board.dtb",
                "initramfs.cpio.gz",
                "manifest",
                "manifest.sig",
            },
        )
        manifest = (bundle / "manifest").read_text(encoding="ascii")
        self.assertIn("profile=persistent-root-ro-v1\n", manifest)
        self.assertIn("target_id=fixture\n", manifest)
        self.assertEqual((bundle / "manifest.sig").stat().st_size, 64)

    def test_live_authority_status_and_unknown_fields_refuse(self) -> None:
        for mutation in ("authority", "status", "unknown"):
            record = copy.deepcopy(self.record)
            if mutation == "authority":
                record["authority"] = "live"
            elif mutation == "status":
                record["status"] = "ready"
            else:
                record["extra"] = "no"
            self.write_record(record)
            with self.assertRaises(RUNNER.CandidateError):
                RUNNER.load_candidate("fixture")

    def test_offline_persistent_root_profile_packages(self) -> None:
        record = copy.deepcopy(self.record)
        record["status"] = "offline"
        self.write_record(record)
        loaded = RUNNER.load_candidate("fixture")
        self.assertEqual(loaded["profile"], "persistent-root-ro-v1")

    def test_offline_unknown_profile_refuses(self) -> None:
        record = copy.deepcopy(self.record)
        record["status"] = "offline"
        record["profile"] = "unknown-v1"
        self.write_record(record)
        with self.assertRaises(RUNNER.CandidateError):
            RUNNER.load_candidate("fixture")

    def test_invalid_identifier_refuses_before_any_file_read(self) -> None:
        with mock.patch.object(RUNNER, "regular_bytes") as reader:
            with self.assertRaisesRegex(
                RUNNER.CandidateError,
                "identifier is invalid",
            ):
                RUNNER.load_candidate_path(
                    self.root / "untrusted-record",
                    "../untrusted",
                )
        reader.assert_not_called()

    def test_artifact_identity_change_refuses(self) -> None:
        (self.repo / self.paths["Image"]).chmod(0o644)
        (self.repo / self.paths["Image"]).write_bytes(b"X" * 64)
        (self.repo / self.paths["Image"]).chmod(0o444)
        with self.assertRaises(RUNNER.CandidateError):
            RUNNER.prepare("fixture", self.private_key, self.bundle_root)

    def test_explicit_authority_free_candidate_record_packages(self) -> None:
        external = self.root / "external-candidate.json"
        external.write_text(
            json.dumps(self.record, indent=2) + "\n",
            encoding="ascii",
        )
        external.chmod(0o444)
        external_hash = hashlib.sha256(external.read_bytes()).hexdigest()
        record, manifest_hash, _trust_hash = RUNNER.prepare(
            "fixture",
            self.private_key,
            self.bundle_root,
            external,
            external_hash,
        )
        self.assertEqual(record, self.record)
        self.assertEqual(
            hashlib.sha256(
                (self.bundle_root / "fixture/manifest").read_bytes()
            ).hexdigest(),
            manifest_hash,
        )

        external.chmod(0o600)
        external.write_text(
            json.dumps({**self.record, "authority": "live"}, indent=2)
            + "\n",
            encoding="ascii",
        )
        external.chmod(0o444)
        other_root = self.root / "other-bundles"
        other_root.mkdir(mode=0o700)
        with self.assertRaises(RUNNER.CandidateError):
            RUNNER.prepare(
                "fixture",
                self.private_key,
                other_root,
                external,
                hashlib.sha256(external.read_bytes()).hexdigest(),
            )

    def test_external_candidate_is_hash_and_template_bound(self) -> None:
        external = self.root / "external-candidate.json"
        cases = ("hash", "target", "bundle", "artifact")
        for case in cases:
            with self.subTest(case=case):
                record = copy.deepcopy(self.record)
                if case == "target":
                    record["target_id"] = "different"
                elif case == "bundle":
                    record["bundle"] = "different"
                elif case == "artifact":
                    record["artifacts"]["Image"]["sha256"] = "f" * 64
                if external.exists():
                    external.chmod(0o600)
                external.write_text(
                    json.dumps(record, indent=2) + "\n",
                    encoding="ascii",
                )
                external.chmod(0o444)
                expected = hashlib.sha256(external.read_bytes()).hexdigest()
                if case == "hash":
                    expected = "f" * 64
                output = self.root / f"external-{case}-bundles"
                output.mkdir(mode=0o700)
                with self.assertRaisesRegex(
                    RUNNER.CandidateError,
                    "hash changed|fixed template field|bundle is unsupported",
                ):
                    RUNNER.prepare(
                        "fixture",
                        self.private_key,
                        output,
                        external,
                        expected,
                    )

        with self.assertRaisesRegex(
            RUNNER.CandidateError,
            "path and hash must be provided together",
        ):
            RUNNER.prepare(
                "fixture",
                self.private_key,
                self.root / "missing-hash-bundles",
                external,
            )

    def test_deployment_successor_pins_every_predecessor_root_field(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        record = copy.deepcopy(
            RUNNER.load_candidate("headless-ssh-network-root-v3")
        )
        bundle = "headless-ssh-network-root-v3-r2"
        record["bundle"] = bundle
        record.update(RUNNER.EXTERNAL_SUCCESSOR_ROOT_FIELDS[bundle])
        RUNNER.validate_external_candidate_record(
            record,
            "headless-ssh-network-root-v3",
        )
        for field in RUNNER.EXTERNAL_MUTABLE_FIELDS:
            with self.subTest(field=field):
                mutated = copy.deepcopy(record)
                mutated[field] = (
                    "arch-b"
                    if field == "root_generation"
                    else "/changed"
                    if field == "root_subtree"
                    else "37736"
                    if field == "root_tree_entries"
                    else "f" * 64
                )
                with self.assertRaisesRegex(
                    RUNNER.CandidateError,
                    "accepted predecessor root",
                ):
                    RUNNER.validate_external_candidate_record(
                        mutated,
                        "headless-ssh-network-root-v3",
                    )

    def test_tracked_parity_record_matches_inventory(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        record = RUNNER.load_candidate("persistent-root-p2-parity")
        inventory = {}
        for line in (REPO / "manifests" / "artifacts.tsv").read_text().splitlines():
            fields = line.split("\t")
            if len(fields) >= 3 and fields[1].isdecimal():
                inventory[fields[0]] = (int(fields[1]), fields[2])
        for artifact in record["artifacts"].values():
            self.assertEqual(
                (artifact["size"], artifact["sha256"]),
                inventory[artifact["path"]],
            )

    def test_tracked_early_target_diagnostic_is_fixed_and_offline(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        record = RUNNER.load_candidate("headless-netroot-early-diag-v1")
        candidate_path = (
            self.original_candidate_root / "headless-netroot-early-diag-v1.json"
        )
        self.assertEqual(
            hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            "7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8",
        )
        self.assertEqual(record["status"], "offline")
        self.assertEqual(record["authority"], "none")
        self.assertEqual(record["bundle"], "headless-netroot-early-diag-v1")
        self.assertEqual(record["profile"], "diagnostic-initramfs-v1")
        self.assertEqual(record["target_id"], "headless-netroot-early-diag")
        self.assertEqual(record["target_release"], "7.1.4-g7a5cef0db479")
        self.assertEqual(record["rollback_timeout"], "600")
        self.assertEqual(record["target_timeout"], "480")
        self.assertEqual(
            record["a660_command_manifest_sha256"],
            "99f194b32171c9c9f09d28636e351bba4cb34751997e1aa174e3466bd758a1d2",
        )
        self.assertEqual(
            record["artifacts"]["initramfs.cpio.gz"],
            {
                "path": (
                    "artifacts/early-target-diagnostic-v1/"
                    "rog5-early-target-diagnostic-initramfs.cpio.gz"
                ),
                "size": 6010870,
                "sha256": (
                    "10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c"
                ),
            },
        )
        artifacts = {
            name: REPO / record["artifacts"][name]["path"]
            for name in RUNNER.ARTIFACT_NAMES
        }
        observed = {
            name: (
                record["artifacts"][name]["size"],
                record["artifacts"][name]["sha256"],
            )
            for name in RUNNER.ARTIFACT_NAMES
        }

        def manifest_hash(candidate: dict) -> str:
            configuration = RUNNER.bundle_configuration(
                candidate,
                artifacts,
                self.private_key,
                self.bundle_root,
            )
            return hashlib.sha256(
                RUNNER.PACKAGER.manifest_bytes(configuration, observed)
            ).hexdigest()

        expected_manifest = (
            "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
        )
        self.assertEqual(manifest_hash(record), expected_manifest)
        for field, changed in (
            ("rollback_timeout", "601"),
            ("a660_command_manifest_sha256", "f" * 64),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(record)
                mutated[field] = changed
                self.assertNotEqual(manifest_hash(mutated), expected_manifest)

    def test_stage75_diagnostic_successor_is_distinct_and_offline(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        candidate = "headless-netroot-early-diag-v2"
        record = RUNNER.load_candidate(candidate)
        candidate_path = self.original_candidate_root / f"{candidate}.json"
        self.assertEqual(
            hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
            "f23626d6ad0b15a660835bd8419cde40a8f8c3c79f83b6feca5cb57952f7b1ab",
        )
        self.assertEqual(record["status"], "offline")
        self.assertEqual(record["authority"], "none")
        self.assertEqual(record["bundle"], candidate)
        self.assertEqual(record["profile"], "diagnostic-initramfs-v1")
        self.assertEqual(record["target_id"], candidate)
        self.assertEqual(
            record["artifacts"]["initramfs.cpio.gz"],
            {
                "path": (
                    "artifacts/early-target-diagnostic-v7/"
                    "rog5-early-target-diagnostic-initramfs.cpio.gz"
                ),
                "size": 6014751,
                "sha256": (
                    "635e641c62f894d4bc150cd3fec9ae965f0f9a769ff7b856ad5ca2432530ed2b"
                ),
            },
        )
        artifacts = {
            name: REPO / record["artifacts"][name]["path"]
            for name in RUNNER.ARTIFACT_NAMES
        }
        observed = {
            name: (
                record["artifacts"][name]["size"],
                record["artifacts"][name]["sha256"],
            )
            for name in RUNNER.ARTIFACT_NAMES
        }
        configuration = RUNNER.bundle_configuration(
            record,
            artifacts,
            self.private_key,
            self.bundle_root,
        )
        self.assertEqual(
            hashlib.sha256(
                RUNNER.PACKAGER.manifest_bytes(configuration, observed)
            ).hexdigest(),
            "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d",
        )

    def test_exact_twins_and_current_template_refuses_stale_v2(self) -> None:
        second_root = self.root / "diagnostic-twin-b"
        second_root.mkdir(mode=0o700)

        record_a, manifest_a, trust_a = RUNNER.prepare(
            "fixture",
            self.private_key,
            self.bundle_root,
        )
        record_b, manifest_b, trust_b = RUNNER.prepare(
            "fixture",
            self.private_key,
            second_root,
        )
        self.assertEqual(record_a, record_b)
        self.assertEqual(manifest_a, manifest_b)
        self.assertEqual(trust_a, trust_b)

        first = self.bundle_root / "fixture"
        second = second_root / "fixture"
        self.assertEqual(
            tuple(sorted(path.name for path in first.iterdir())),
            tuple(sorted(RUNNER.PACKAGER.FINAL_INVENTORY)),
        )
        for name in RUNNER.PACKAGER.FINAL_INVENTORY:
            with self.subTest(name=name):
                left = first / name
                right = second / name
                self.assertEqual(left.read_bytes(), right.read_bytes())
                self.assertEqual(
                    left.stat().st_mode,
                    right.stat().st_mode,
                )

        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        candidate = "headless-netroot-early-diag-v2"
        stale = copy.deepcopy(RUNNER.load_candidate(candidate))
        stale["artifacts"]["initramfs.cpio.gz"] = {
            "path": (
                "artifacts/early-target-diagnostic-v2/"
                "rog5-early-target-diagnostic-initramfs.cpio.gz"
            ),
            "size": 6011687,
            "sha256": (
                "71537ca0cfdfcf8f7dbf26cc2eb6585bac025bea08526a7e22d62df60fa0c58e"
            ),
        }
        with self.assertRaisesRegex(
            RUNNER.CandidateError,
            "external candidate changed a fixed template field",
        ):
            RUNNER.validate_external_candidate_record(stale, candidate)

    def test_headless_network_candidate_matches_root_package(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        shared_image = {
            "path": "artifacts/network-root-v1/Image-7.1.4-network-root",
            "size": 40049152,
            "sha256": (
                "349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf"
            ),
        }
        shared_network_root_loader = {
            "path": (
                "artifacts/headless-network-root-v1/"
                "rog5-headless-network-root-initramfs.cpio.gz"
            ),
            "size": 5978369,
            "sha256": (
                "819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5"
            ),
        }
        cases = (
            (
                "headless-network-root-v1",
                "headless-network-root-v1.package",
                "artifacts/network-root-v3/"
                "sm8350-asus-rog-phone5-recovery.dtb",
                102870,
                "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46",
            ),
            (
                "headless-core-network-root-v2",
                "headless-core-network-root-v2.package",
                "artifacts/buttons-indicator-v1/"
                "sm8350-asus-rog-phone5-buttons-indicator.dtb",
                103554,
                "57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d",
            ),
            (
                "headless-ssh-network-root-v3",
                "headless-ssh-network-root-v3.package",
                "artifacts/network-root-v3/"
                "sm8350-asus-rog-phone5-recovery.dtb",
                102870,
                "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46",
            ),
        )
        for candidate, package_name, dtb_path, dtb_size, dtb_hash in cases:
            with self.subTest(candidate=candidate):
                record = RUNNER.load_candidate(candidate)
                package = {}
                package_path = (
                    REPO / "configs/network-roots" / package_name
                )
                for line in package_path.read_text(
                    encoding="ascii"
                ).splitlines():
                    name, separator, value = line.partition("=")
                    self.assertEqual(separator, "=")
                    self.assertNotIn(name, package)
                    package[name] = value
                self.assertEqual(record["status"], "offline")
                self.assertEqual(record["authority"], "none")
                self.assertEqual(record["profile"], package["profile"])
                self.assertEqual(record["artifacts"]["Image"], shared_image)
                self.assertEqual(
                    record["artifacts"]["board.dtb"],
                    {
                        "path": dtb_path,
                        "size": dtb_size,
                        "sha256": dtb_hash,
                    },
                )
                self.assertEqual(
                    record["artifacts"]["initramfs.cpio.gz"],
                    shared_network_root_loader,
                )
                for name in (
                    "a660_command_manifest_sha256",
                    "root_generation",
                    "root_tree_sha256",
                    "root_seal_sha256",
                    "root_tree_entries",
                    "root_subtree",
                ):
                    self.assertEqual(str(record[name]), package[name])

    def test_adapter_has_no_live_transport(self) -> None:
        source = RUNNER_PATH.read_text(encoding="utf-8")
        for token in (
            "fastboot",
            "adb",
            "rog5-recovery-bundle-controller",
            "run-recovery-bundle-server",
            "systemctl",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
