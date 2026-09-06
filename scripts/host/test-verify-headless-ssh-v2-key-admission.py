#!/usr/bin/env python3
"""Hostile offline tests for deployment SSH-key admission."""

from __future__ import annotations

from collections import OrderedDict
import copy
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
RUNNER_PATH = (
    REPO / "scripts/host/verify-headless-ssh-v2-key-admission.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_key_admission_test",
        RUNNER_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load deployment-key admission verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


ADMISSION = load_module()


class KeyAdmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-key-admission-"
        )
        self.root = Path(self.temporary.name)
        self.private_key = self.root / "deployment-key"
        self.package_path = self.root / "package"
        self.candidate_path = self.root / "candidate.json"
        self.manifest_path = self.root / "manifest"
        self.generate_key(self.private_key)
        self.public_key, self.fingerprint = ADMISSION.derive_public_key(
            self.private_key
        )
        self.package = OrderedDict(
            (
                (
                    "format",
                    "rog5-headless-network-root-package-v3",
                ),
                ("profile", ADMISSION.PROFILE),
                ("build_profile", ADMISSION.BUILD_PROFILE),
                ("authorized_key_fingerprint", self.fingerprint),
                ("root_generation", "arch-a"),
                ("root_subtree", "/"),
                ("source_archive_size", "536750378"),
                ("source_archive_sha256", "1" * 64),
                ("sealed_archive_size", "536747283"),
                ("sealed_archive_sha256", "2" * 64),
                ("a660_command_manifest_sha256", "3" * 64),
                ("root_tree_entries", "37736"),
                ("root_tree_sha256", "4" * 64),
                ("root_seal_sha256", "5" * 64),
            )
        )
        self.candidate = {
            "format": "rog5-recovery-candidate-v1",
            "candidate": ADMISSION.CANDIDATE_ID,
            "status": "offline",
            "authority": "none",
            "bundle": ADMISSION.BUNDLE_ID,
            "profile": ADMISSION.PROFILE,
            "target_id": ADMISSION.TARGET_ID,
            "target_release": ADMISSION.TARGET_RELEASE,
            "rollback_timeout": "600",
            "target_timeout": "480",
            **{
                name: self.package[name]
                for name in ADMISSION.ROOT_FIELDS
            },
            "artifacts": copy.deepcopy(ADMISSION.EXPECTED_ARTIFACTS),
        }
        self.manifest = OrderedDict(
            (
                ("format", "rog5-recovery-bundle-v2"),
                ("bundle", ADMISSION.BUNDLE_ID),
                ("profile", ADMISSION.PROFILE),
                (
                    "kernel_size",
                    str(
                        ADMISSION.EXPECTED_ARTIFACTS["Image"]["size"]
                    ),
                ),
                (
                    "kernel_sha256",
                    ADMISSION.EXPECTED_ARTIFACTS["Image"]["sha256"],
                ),
                (
                    "dtb_size",
                    str(
                        ADMISSION.EXPECTED_ARTIFACTS["board.dtb"]["size"]
                    ),
                ),
                (
                    "dtb_sha256",
                    ADMISSION.EXPECTED_ARTIFACTS["board.dtb"]["sha256"],
                ),
                (
                    "initramfs_size",
                    str(
                        ADMISSION.EXPECTED_ARTIFACTS[
                            "initramfs.cpio.gz"
                        ]["size"]
                    ),
                ),
                (
                    "initramfs_sha256",
                    ADMISSION.EXPECTED_ARTIFACTS[
                        "initramfs.cpio.gz"
                    ]["sha256"],
                ),
                ("target_id", ADMISSION.TARGET_ID),
                ("target_release", ADMISSION.TARGET_RELEASE),
                ("rollback_timeout", "600"),
                ("target_timeout", "480"),
                *(
                    (name, self.package[name])
                    for name in ADMISSION.ROOT_FIELDS
                ),
            )
        )
        self.base_package = copy.deepcopy(self.package)
        self.base_candidate = copy.deepcopy(self.candidate)
        self.base_manifest = copy.deepcopy(self.manifest)
        self.write_records()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def generate_key(
        path: Path,
        *,
        algorithm: str = "ed25519",
        passphrase: str = "",
    ) -> None:
        subprocess.run(
            [
                "/usr/bin/ssh-keygen",
                "-q",
                "-t",
                algorithm,
                "-N",
                passphrase,
                "-C",
                "disposable-admission-fixture",
                "-f",
                str(path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=15,
        )
        path.chmod(0o600)

    @staticmethod
    def write_private(path: Path, payload: bytes) -> None:
        if path.exists():
            path.chmod(0o600)
        path.write_bytes(payload)
        path.chmod(0o400)

    def write_records(self) -> str:
        package_payload = ADMISSION.HEADLESS.canonical_bytes(self.package)
        candidate_payload = (
            json.dumps(self.candidate, indent=2) + "\n"
        ).encode("ascii")
        manifest_payload = ADMISSION.HEADLESS.canonical_bytes(self.manifest)
        self.write_private(self.package_path, package_payload)
        self.write_private(self.candidate_path, candidate_payload)
        self.write_private(self.manifest_path, manifest_payload)
        return hashlib.sha256(manifest_payload).hexdigest()

    def reset_records(self) -> None:
        self.package = copy.deepcopy(self.base_package)
        self.candidate = copy.deepcopy(self.base_candidate)
        self.manifest = copy.deepcopy(self.base_manifest)

    def verify(self):
        manifest_sha256 = hashlib.sha256(
            self.manifest_path.read_bytes()
        ).hexdigest()
        return ADMISSION.verify(
            self.private_key,
            self.package_path,
            self.candidate_path,
            self.manifest_path,
            manifest_sha256,
        )

    def assert_refused(self) -> None:
        with self.assertRaises(
            (
                ADMISSION.AdmissionError,
                ADMISSION.HEADLESS.HeadlessRootError,
                ADMISSION.CANDIDATE.CandidateError,
            )
        ):
            self.verify()

    def test_exact_nonfixture_v3_chain_passes(self) -> None:
        result = self.verify()
        self.assertEqual(
            tuple(result),
            (
                "format",
                "candidate",
                "bundle",
                "profile",
                "build_profile",
                "target_id",
                "authorized_key_fingerprint",
                "public_key_sha256",
                "package_sha256",
                "candidate_sha256",
                "manifest_sha256",
                "root_tree_sha256",
                "root_seal_sha256",
                "root_tree_entries",
                "authority",
            ),
        )
        self.assertEqual(
            result["format"],
            "rog5-headless-ssh-v2-key-admission-v1",
        )
        self.assertEqual(
            result["authorized_key_fingerprint"],
            self.fingerprint,
        )
        self.assertEqual(result["authority"], "none")
        output = ADMISSION.HEADLESS.canonical_bytes(result)
        self.assertNotIn(self.public_key.split()[1], output)
        self.assertNotIn(os.fsencode(self.private_key), output)

    def test_exact_early_target_diagnostic_chain_passes(self) -> None:
        profile = ADMISSION.DIAGNOSTIC_ADMISSION_PROFILE
        expected_artifacts = ADMISSION.artifact_map(profile)
        self.candidate.update(
            {
                "candidate": profile.candidate_id,
                "bundle": profile.bundle_id,
                "profile": profile.bundle_profile,
                "target_id": profile.target_id,
                "target_release": profile.target_release,
                "artifacts": copy.deepcopy(expected_artifacts),
            }
        )
        self.manifest.update(
            {
                "bundle": profile.bundle_id,
                "profile": profile.bundle_profile,
                "kernel_size": str(
                    expected_artifacts["Image"]["size"]
                ),
                "kernel_sha256": expected_artifacts["Image"][
                    "sha256"
                ],
                "dtb_size": str(
                    expected_artifacts["board.dtb"]["size"]
                ),
                "dtb_sha256": expected_artifacts["board.dtb"][
                    "sha256"
                ],
                "initramfs_size": str(
                    expected_artifacts["initramfs.cpio.gz"]["size"]
                ),
                "initramfs_sha256": expected_artifacts[
                    "initramfs.cpio.gz"
                ]["sha256"],
                "target_id": profile.target_id,
                "target_release": profile.target_release,
            }
        )
        manifest_sha256 = self.write_records()
        result = ADMISSION.verify(
            self.private_key,
            self.package_path,
            self.candidate_path,
            self.manifest_path,
            manifest_sha256,
            profile.name,
        )
        self.assertEqual(result["candidate"], profile.candidate_id)
        self.assertEqual(result["bundle"], profile.bundle_id)
        self.assertEqual(result["profile"], profile.bundle_profile)
        self.assertEqual(
            result["package_sha256"],
            hashlib.sha256(self.package_path.read_bytes()).hexdigest(),
        )
        self.candidate["artifacts"]["initramfs.cpio.gz"] = copy.deepcopy(
            ADMISSION.EXPECTED_ARTIFACTS["initramfs.cpio.gz"]
        )
        manifest_sha256 = self.write_records()
        with self.assertRaises(ADMISSION.AdmissionError):
            ADMISSION.verify(
                self.private_key,
                self.package_path,
                self.candidate_path,
                self.manifest_path,
                manifest_sha256,
                profile.name,
            )

    def test_exact_headless_core_v3_chain_passes(self) -> None:
        profile = ADMISSION.CORE_ADMISSION_PROFILE
        expected_artifacts = ADMISSION.artifact_map(profile)
        self.package["format"] = "rog5-headless-network-root-package-v4"
        self.package["build_profile"] = profile.build_profile
        self.candidate.update(
            {
                "candidate": profile.candidate_id,
                "bundle": profile.bundle_id,
                "profile": profile.bundle_profile,
                "target_id": profile.target_id,
                "artifacts": copy.deepcopy(expected_artifacts),
            }
        )
        self.manifest.update(
            {
                "bundle": profile.bundle_id,
                "profile": profile.bundle_profile,
                "kernel_size": str(expected_artifacts["Image"]["size"]),
                "kernel_sha256": expected_artifacts["Image"]["sha256"],
                "dtb_size": str(expected_artifacts["board.dtb"]["size"]),
                "dtb_sha256": expected_artifacts["board.dtb"]["sha256"],
                "initramfs_size": str(
                    expected_artifacts["initramfs.cpio.gz"]["size"]
                ),
                "initramfs_sha256": expected_artifacts[
                    "initramfs.cpio.gz"
                ]["sha256"],
                "target_id": profile.target_id,
            }
        )
        manifest_sha256 = self.write_records()
        result = ADMISSION.verify(
            self.private_key,
            self.package_path,
            self.candidate_path,
            self.manifest_path,
            manifest_sha256,
            profile.name,
        )
        self.assertEqual(result["candidate"], profile.candidate_id)
        self.assertEqual(result["bundle"], profile.bundle_id)
        self.assertEqual(result["build_profile"], "headless-core-v3")

    def test_exact_power_usb_observer_chain_passes(self) -> None:
        profile = ADMISSION.POWER_USB_ADMISSION_PROFILE
        expected_artifacts = ADMISSION.artifact_map(profile)
        self.candidate.update(
            {
                "candidate": profile.candidate_id,
                "bundle": profile.bundle_id,
                "profile": profile.bundle_profile,
                "target_id": profile.target_id,
                "rollback_timeout": ADMISSION.POWER_USB.ROLLBACK_TIMEOUT,
                "target_timeout": ADMISSION.POWER_USB.TARGET_TIMEOUT,
                "artifacts": copy.deepcopy(expected_artifacts),
            }
        )
        self.manifest.update(
            {
                "bundle": profile.bundle_id,
                "profile": profile.bundle_profile,
                "kernel_size": str(expected_artifacts["Image"]["size"]),
                "kernel_sha256": expected_artifacts["Image"]["sha256"],
                "dtb_size": str(expected_artifacts["board.dtb"]["size"]),
                "dtb_sha256": expected_artifacts["board.dtb"]["sha256"],
                "initramfs_size": str(
                    expected_artifacts["initramfs.cpio.gz"]["size"]
                ),
                "initramfs_sha256": expected_artifacts[
                    "initramfs.cpio.gz"
                ]["sha256"],
                "target_id": profile.target_id,
                "rollback_timeout": ADMISSION.POWER_USB.ROLLBACK_TIMEOUT,
                "target_timeout": ADMISSION.POWER_USB.TARGET_TIMEOUT,
            }
        )
        manifest_sha256 = self.write_records()
        result = ADMISSION.verify(
            self.private_key,
            self.package_path,
            self.candidate_path,
            self.manifest_path,
            manifest_sha256,
            profile.name,
        )
        self.assertEqual(result["candidate"], profile.candidate_id)
        self.assertEqual(result["bundle"], profile.bundle_id)
        self.assertEqual(result["build_profile"], "headless-ssh-v2")

    def test_admission_policy_cannot_be_supplied_or_mutated(self) -> None:
        custom = ADMISSION.AdmissionProfile(
            name="caller-policy",
            candidate_id="caller-candidate",
            bundle_id="caller-bundle",
            bundle_profile="caller-profile",
            package_profile=ADMISSION.PROFILE,
            build_profile=ADMISSION.BUILD_PROFILE,
            target_id="caller-target",
            target_release=ADMISSION.TARGET_RELEASE,
            expected_artifacts=(),
        )
        manifest_sha256 = hashlib.sha256(
            self.manifest_path.read_bytes()
        ).hexdigest()
        with self.assertRaises(ADMISSION.AdmissionError):
            ADMISSION.verify(
                self.private_key,
                self.package_path,
                self.candidate_path,
                self.manifest_path,
                manifest_sha256,
                custom,
            )
        original = ADMISSION.EXPECTED_ARTIFACTS["Image"]["sha256"]
        try:
            ADMISSION.EXPECTED_ARTIFACTS["Image"]["sha256"] = "f" * 64
            deployment = ADMISSION.artifact_map(
                ADMISSION.DEPLOYMENT_ADMISSION_PROFILE
            )
            diagnostic = ADMISSION.artifact_map(
                ADMISSION.DIAGNOSTIC_ADMISSION_PROFILE
            )
            self.assertEqual(deployment["Image"]["sha256"], original)
            self.assertEqual(diagnostic["Image"]["sha256"], original)
        finally:
            ADMISSION.EXPECTED_ARTIFACTS["Image"]["sha256"] = original

    def test_cli_emits_only_canonical_public_identity(self) -> None:
        manifest_sha256 = hashlib.sha256(
            self.manifest_path.read_bytes()
        ).hexdigest()
        result = subprocess.run(
            [
                str(RUNNER_PATH),
                "--private-key",
                str(self.private_key),
                "--package",
                str(self.package_path),
                "--candidate",
                str(self.candidate_path),
                "--manifest",
                str(self.manifest_path),
                "--manifest-sha256",
                manifest_sha256,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            result.stdout.startswith(
                b"format=rog5-headless-ssh-v2-key-admission-v1\n"
            )
        )
        self.assertNotIn(self.public_key.split()[1], result.stdout)
        self.assertNotIn(os.fsencode(self.private_key), result.stdout)
        self.assertEqual(result.stderr, b"")

    def test_fixture_private_key_is_rejected_explicitly(self) -> None:
        original_path = ADMISSION.FIXTURE_KEY_PATH
        original_fingerprint = ADMISSION.FIXTURE_FINGERPRINT
        try:
            fixture_public = self.root / "fixture.pub"
            self.write_private(fixture_public, self.public_key)
            ADMISSION.FIXTURE_KEY_PATH = fixture_public
            ADMISSION.FIXTURE_FINGERPRINT = self.fingerprint
            with self.assertRaisesRegex(
                ADMISSION.AdmissionError,
                "not a deployment credential",
            ):
                self.verify()
        finally:
            ADMISSION.FIXTURE_KEY_PATH = original_path
            ADMISSION.FIXTURE_FINGERPRINT = original_fingerprint

    def test_private_key_and_package_fingerprint_mismatch_refuses(
        self,
    ) -> None:
        self.package["authorized_key_fingerprint"] = (
            "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        self.write_records()
        self.assert_refused()

    def test_every_tracked_fixture_root_identity_refuses(self) -> None:
        cases = (
            ("source_archive_sha256", ADMISSION.FIXTURE_SOURCE_SHA256),
            ("sealed_archive_sha256", ADMISSION.FIXTURE_SEALED_SHA256),
            ("root_tree_sha256", ADMISSION.FIXTURE_TREE_SHA256),
            ("root_seal_sha256", ADMISSION.FIXTURE_SEAL_SHA256),
        )
        for name, value in cases:
            with self.subTest(name=name):
                self.reset_records()
                self.package[name] = value
                if name in ADMISSION.ROOT_FIELDS:
                    self.candidate[name] = value
                    self.manifest[name] = value
                self.write_records()
                self.assert_refused()

    def test_each_package_candidate_root_mismatch_refuses(self) -> None:
        for name in ADMISSION.ROOT_FIELDS:
            with self.subTest(name=name, case="mismatch"):
                self.reset_records()
                self.candidate[name] = (
                    "6" * 64
                    if name.endswith("sha256")
                    else "arch-b"
                    if name == "root_generation"
                    else "37737"
                    if name == "root_tree_entries"
                    else "/other"
                )
                self.write_records()
                self.assert_refused()
            with self.subTest(name=name, case="missing"):
                self.reset_records()
                del self.candidate[name]
                self.write_records()
                with self.assertRaises(ADMISSION.AdmissionError):
                    self.verify()

    def test_each_candidate_tuple_mutation_refuses(self) -> None:
        mutations = {
            "candidate": "headless-network-root-v1",
            "bundle": "headless-network-root-v1",
            "status": "consumed",
            "authority": "live",
            "profile": "persistent-root-ro-v1",
            "target_id": "headless-network-root",
            "target_release": "7.1.4-other",
            "rollback_timeout": "601",
            "target_timeout": "479",
        }
        for name, value in mutations.items():
            with self.subTest(name=name):
                self.reset_records()
                self.candidate[name] = value
                self.write_records()
                self.assert_refused()

    def test_each_candidate_artifact_mutation_refuses(self) -> None:
        for artifact in ADMISSION.EXPECTED_ARTIFACTS:
            for field in ("path", "size", "sha256"):
                with self.subTest(artifact=artifact, field=field):
                    self.reset_records()
                    value = self.candidate["artifacts"][artifact][field]
                    self.candidate["artifacts"][artifact][field] = (
                        value + ".other"
                        if isinstance(value, str) and field == "path"
                        else "6" * 64
                        if field == "sha256"
                        else value + 1
                    )
                    self.write_records()
                    self.assert_refused()

    def test_each_manifest_mutation_refuses(self) -> None:
        for name in self.manifest:
            with self.subTest(name=name):
                self.reset_records()
                value = self.manifest[name]
                self.manifest[name] = (
                    "6" * 64
                    if name.endswith("sha256")
                    else str(int(value) + 1)
                    if name.endswith("size") or name.endswith("timeout")
                    or name == "root_tree_entries"
                    else value + "-other"
                )
                self.write_records()
                self.assert_refused()

    def test_wrong_expected_or_tracked_manifest_hash_refuses(self) -> None:
        with self.assertRaisesRegex(
            ADMISSION.AdmissionError,
            "manifest identity changed",
        ):
            ADMISSION.verify(
                self.private_key,
                self.package_path,
                self.candidate_path,
                self.manifest_path,
                "6" * 64,
            )
        original = ADMISSION.FIXTURE_MANIFEST_SHA256
        try:
            ADMISSION.FIXTURE_MANIFEST_SHA256 = hashlib.sha256(
                self.manifest_path.read_bytes()
            ).hexdigest()
            with self.assertRaisesRegex(
                ADMISSION.AdmissionError,
                "tracked fixture identity",
            ):
                self.verify()
        finally:
            ADMISSION.FIXTURE_MANIFEST_SHA256 = original

    def test_private_key_metadata_and_path_policy_refuse(self) -> None:
        self.private_key.chmod(0o644)
        self.assert_refused()
        self.private_key.chmod(0o600)

        linked = self.root / "linked-key"
        linked.symlink_to(self.private_key)
        with self.assertRaises(ADMISSION.AdmissionError):
            ADMISSION.verify(
                linked,
                self.package_path,
                self.candidate_path,
                self.manifest_path,
                hashlib.sha256(self.manifest_path.read_bytes()).hexdigest(),
            )

        self.root.chmod(0o755)
        self.assert_refused()
        self.root.chmod(0o700)

    def test_encrypted_and_non_ed25519_private_keys_refuse(self) -> None:
        encrypted = self.root / "encrypted"
        self.generate_key(
            encrypted,
            algorithm="ed25519",
            passphrase="fixture-passphrase",
        )
        with self.assertRaises(ADMISSION.AdmissionError):
            ADMISSION.verify(
                encrypted,
                self.package_path,
                self.candidate_path,
                self.manifest_path,
                hashlib.sha256(
                    self.manifest_path.read_bytes()
                ).hexdigest(),
            )

        rsa = self.root / "rsa"
        self.generate_key(rsa, algorithm="rsa")
        with self.assertRaisesRegex(
            ADMISSION.AdmissionError,
            "not one unencrypted Ed25519 key",
        ):
            ADMISSION.derive_public_key(rsa)

    def test_record_metadata_duplicate_and_link_policy_refuse(self) -> None:
        self.package_path.chmod(0o600)
        self.assert_refused()
        self.package_path.chmod(0o400)

        duplicate = self.root / "package-hardlink"
        duplicate.hardlink_to(self.package_path)
        self.assert_refused()
        duplicate.unlink()

        payload = self.manifest_path.read_bytes()
        self.write_private(
            self.manifest_path,
            payload + b"root_subtree=/\n",
        )
        self.assert_refused()

    def test_source_pins_fixed_keygen_and_excludes_live_transport(
        self,
    ) -> None:
        source = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertIn('SSH_KEYGEN = Path("/usr/bin/ssh-keygen")', source)
        self.assertIn("stdin=subprocess.DEVNULL", source)
        self.assertIn("pass_fds=(descriptor,)", source)
        for token in (
            "fastboot",
            "adb",
            "systemctl",
            "pkexec",
            "sudo",
            "ssh ",
            "scp",
            "/dev/sd",
            "/dev/nvme",
            "/dev/ufs",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
