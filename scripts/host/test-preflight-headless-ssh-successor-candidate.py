#!/usr/bin/env python3
"""Offline tests for the credential-free real-r2 candidate preflight."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = (
    REPO / "scripts/host/preflight-headless-ssh-successor-candidate.py"
)
FIXTURE_PACKAGE = (
    REPO / "configs/network-roots/headless-ssh-network-root-v3.package"
)
ORIGINAL_OS_OPEN = os.open


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_successor_candidate_preflight_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load successor-candidate preflight")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()


class SuccessorCandidatePreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-successor-candidate-preflight-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.package = self.root / "root.package"
        self.base_candidate = self.root / "base-candidate.json"
        self.candidate = self.root / "candidate.json"
        self.synthetic_repo = self.root / "repository"
        self.artifact_root = self.synthetic_repo / "artifacts" / "synthetic"
        self.candidate_root = (
            self.synthetic_repo / "configs" / "recovery-candidates"
        )
        self.artifact_root.mkdir(parents=True)
        self.candidate_root.mkdir(parents=True)
        self.payloads = {
            "Image": b"I" * 64,
            "board.dtb": b"D" * 40,
            "initramfs.cpio.gz": b"GZ",
        }

        template = TOOL.CANDIDATE.load_candidate(
            TOOL.DEPLOYMENT.CANDIDATE_ID
        )
        for name, payload in self.payloads.items():
            artifact = self.artifact_root / name
            artifact.write_bytes(payload)
            artifact.chmod(0o400)
            template["artifacts"][name] = {
                "path": f"artifacts/synthetic/{name}",
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        template_path = (
            self.candidate_root
            / f"{TOOL.DEPLOYMENT.CANDIDATE_ID}.json"
        )
        template_path.write_bytes(TOOL.DEPLOYMENT.canonical_payload(template))
        template_path.chmod(0o400)

        self.package_fields = (
            TOOL.DEPLOYMENT.HEADLESS.parse_canonical_variant(
                FIXTURE_PACKAGE,
                TOOL.DEPLOYMENT.HEADLESS.PACKAGE_FORMATS,
                owner=FIXTURE_PACKAGE.stat().st_uid,
                mode=stat.S_IMODE(FIXTURE_PACKAGE.stat().st_mode),
            )
        )
        self.package_fields["authorized_key_fingerprint"] = (
            "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        self.package_fields["source_archive_sha256"] = "1" * 64
        self.package_fields["sealed_archive_sha256"] = "2" * 64
        self.package_fields.update(
            TOOL.CANDIDATE.EXTERNAL_SUCCESSOR_ROOT_FIELDS[
                TOOL.DEPLOYMENT.SUCCESSOR_BUNDLE_ID
            ]
        )
        self.write_package()

        self.repo_patch = mock.patch.object(
            TOOL.CANDIDATE,
            "REPO",
            self.synthetic_repo,
        )
        self.root_patch = mock.patch.object(
            TOOL.CANDIDATE,
            "CANDIDATE_ROOT",
            self.candidate_root,
        )
        self.repo_patch.start()
        self.root_patch.start()
        self.addCleanup(self.repo_patch.stop)
        self.addCleanup(self.root_patch.stop)

        self.base_record = TOOL.DEPLOYMENT.candidate_record(
            self.package_fields,
            TOOL.DEPLOYMENT.BASE_BUNDLE_ID,
        )
        self.successor_record = TOOL.DEPLOYMENT.candidate_record(
            self.package_fields,
            TOOL.DEPLOYMENT.SUCCESSOR_BUNDLE_ID,
        )
        self.write_candidate(self.base_candidate, self.base_record)
        self.write_candidate(self.candidate, self.successor_record)
        self.base_candidate_sha256 = hashlib.sha256(
            self.base_candidate.read_bytes()
        ).hexdigest()
        self.candidate_sha256 = hashlib.sha256(
            self.candidate.read_bytes()
        ).hexdigest()
        observed = {
            name: (len(payload), hashlib.sha256(payload).hexdigest())
            for name, payload in self.payloads.items()
        }
        self.manifest_sha256 = TOOL.manifest_identity(
            self.successor_record,
            observed,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_package(self) -> None:
        if self.package.exists():
            self.package.chmod(0o600)
        self.package.write_bytes(
            TOOL.DEPLOYMENT.HEADLESS.canonical_bytes(self.package_fields)
        )
        self.package.chmod(0o444)

    def write_candidate(self, path: Path, record: dict) -> None:
        if path.exists() or path.is_symlink():
            path.unlink()
        path.write_bytes(TOOL.DEPLOYMENT.canonical_payload(record))
        path.chmod(0o444)

    def verify(self) -> tuple[str, str, str, str]:
        def reject_device_open(path, *arguments, **keywords):
            if os.fspath(path).startswith("/dev/"):
                raise AssertionError("device path reached")
            return ORIGINAL_OS_OPEN(path, *arguments, **keywords)

        with (
            mock.patch.object(
                TOOL.STAGER,
                "verify_repository_checkpoint",
                return_value="a" * 40,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_MANIFEST_SHA256",
                self.manifest_sha256,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_BASE_CANDIDATE_SHA256",
                self.base_candidate_sha256,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_SUCCESSOR_CANDIDATE_SHA256",
                self.candidate_sha256,
            ),
            mock.patch.object(
                TOOL.STAGER,
                "derive_ed25519_public",
                side_effect=AssertionError("credential path reached"),
            ),
            mock.patch.object(
                TOOL.PACKAGER,
                "prepare_bundle",
                side_effect=AssertionError("signing path reached"),
            ),
            mock.patch.object(
                TOOL.STAGER.subprocess,
                "run",
                side_effect=AssertionError("process path reached"),
            ),
            mock.patch.object(
                TOOL.os,
                "system",
                side_effect=AssertionError("shell path reached"),
            ),
            mock.patch.object(
                TOOL.os,
                "posix_spawn",
                side_effect=AssertionError("spawn path reached"),
            ),
            mock.patch.object(
                TOOL.os,
                "posix_spawnp",
                side_effect=AssertionError("spawn path reached"),
            ),
            mock.patch.object(
                TOOL.os,
                "open",
                side_effect=reject_device_open,
            ),
            mock.patch(
                "socket.socket",
                side_effect=AssertionError("network path reached"),
            ),
        ):
            return TOOL.verify(
                self.package,
                self.base_candidate,
                self.candidate,
            )

    def test_exact_successor_passes_without_credentials_or_phone(self) -> None:
        (
            checkpoint,
            base_candidate_hash,
            candidate_hash,
            manifest_hash,
        ) = self.verify()
        self.assertEqual(checkpoint, "a" * 40)
        self.assertEqual(
            base_candidate_hash,
            self.base_candidate_sha256,
        )
        self.assertEqual(
            candidate_hash,
            hashlib.sha256(self.candidate.read_bytes()).hexdigest(),
        )
        self.assertEqual(manifest_hash, self.manifest_sha256)

    def test_candidate_mutations_fail_closed(self) -> None:
        cases = {
            "base-bundle": ("bundle", TOOL.DEPLOYMENT.BASE_BUNDLE_ID),
            "root-hash": ("root_tree_sha256", "e" * 64),
            "artifact-hash": (
                "artifacts.Image.sha256",
                "f" * 64,
            ),
        }
        for name, (field, value) in cases.items():
            with self.subTest(name=name):
                record = {
                    key: (
                        dict(item) if isinstance(item, dict) else item
                    )
                    for key, item in self.successor_record.items()
                }
                if field == "artifacts.Image.sha256":
                    record["artifacts"] = {
                        key: dict(item)
                        for key, item in self.successor_record[
                            "artifacts"
                        ].items()
                    }
                    record["artifacts"]["Image"]["sha256"] = value
                else:
                    record[field] = value
                self.write_candidate(self.candidate, record)
                with self.assertRaises(
                    (
                        TOOL.SuccessorPreflightError,
                        TOOL.CANDIDATE.CandidateError,
                    )
                ):
                    self.verify()

    def test_package_mismatch_fails_closed(self) -> None:
        self.package_fields["root_tree_entries"] = "37736"
        self.write_package()
        with self.assertRaises(
            (
                TOOL.SuccessorPreflightError,
                TOOL.CANDIDATE.CandidateError,
            )
        ):
            self.verify()

    def test_actual_base_candidate_mutation_fails_closed(self) -> None:
        record = dict(self.base_record)
        record["root_tree_entries"] = "37736"
        self.write_candidate(self.base_candidate, record)
        with self.assertRaises(
            (
                TOOL.SuccessorPreflightError,
                TOOL.CANDIDATE.CandidateError,
            )
        ):
            self.verify()

    def test_noncanonical_candidate_bytes_fail_closed(self) -> None:
        self.candidate.chmod(0o600)
        self.candidate.write_bytes(
            self.candidate.read_bytes().replace(b"{\n", b"{  \n", 1)
        )
        self.candidate.chmod(0o444)
        with self.assertRaisesRegex(
            TOOL.SuccessorPreflightError,
            "successor candidate",
        ):
            self.verify()

    def test_candidate_metadata_must_be_private_and_read_only(self) -> None:
        self.candidate.chmod(0o644)
        with self.assertRaises(TOOL.STAGER.SigningInputError):
            self.verify()

    def test_candidate_symlink_and_hardlink_are_rejected(self) -> None:
        real = self.root / "candidate.real"
        self.candidate.rename(real)
        self.candidate.symlink_to(real.name)
        with self.assertRaises(TOOL.STAGER.SigningInputError):
            self.verify()
        self.candidate.unlink()
        self.candidate.hardlink_to(real)
        with self.assertRaises(TOOL.STAGER.SigningInputError):
            self.verify()

    def test_base_candidate_metadata_and_bytes_fail_closed(self) -> None:
        self.base_candidate.chmod(0o644)
        with self.assertRaises(TOOL.STAGER.SigningInputError):
            self.verify()
        self.base_candidate.chmod(0o444)

        payload = self.base_candidate.read_bytes()
        self.base_candidate.chmod(0o600)
        self.base_candidate.write_bytes(payload.replace(b"{\n", b"{  \n", 1))
        self.base_candidate.chmod(0o444)
        with self.assertRaisesRegex(
            TOOL.SuccessorPreflightError,
            "base candidate",
        ):
            self.verify()
        self.write_candidate(self.base_candidate, self.base_record)

        real = self.root / "base-candidate.real"
        self.base_candidate.rename(real)
        self.base_candidate.symlink_to(real.name)
        with self.assertRaises(TOOL.STAGER.SigningInputError):
            self.verify()
        self.base_candidate.unlink()
        real.rename(self.base_candidate)
        hardlink = self.root / "base-candidate.hardlink"
        hardlink.hardlink_to(self.base_candidate)
        with self.assertRaises(TOOL.STAGER.SigningInputError):
            self.verify()

    def test_package_metadata_must_be_private_read_only_and_unlinked(self) -> None:
        self.package.chmod(0o666)
        with self.assertRaises(TOOL.DEPLOYMENT.DeploymentCandidateError):
            self.verify()
        self.package.chmod(0o444)

        real = self.root / "package.real"
        self.package.rename(real)
        self.package.symlink_to(real.name)
        with self.assertRaises(TOOL.DEPLOYMENT.DeploymentCandidateError):
            self.verify()
        self.package.unlink()
        real.rename(self.package)

        hardlink = self.root / "package.hardlink"
        hardlink.hardlink_to(self.package)
        with self.assertRaises(TOOL.DEPLOYMENT.DeploymentCandidateError):
            self.verify()
        hardlink.unlink()

    def test_shipped_fixture_package_is_rejected(self) -> None:
        self.package.chmod(0o600)
        self.package.write_bytes(FIXTURE_PACKAGE.read_bytes())
        self.package.chmod(0o444)
        with self.assertRaises(
            TOOL.DEPLOYMENT.DeploymentCandidateError
        ):
            self.verify()

    def test_artifact_change_fails_closed(self) -> None:
        image = self.artifact_root / "Image"
        image.chmod(0o600)
        image.write_bytes(b"X" * 64)
        image.chmod(0o400)
        with self.assertRaises(TOOL.CANDIDATE.CandidateError):
            self.verify()

    def test_artifact_symlink_and_hardlink_fail_closed(self) -> None:
        image = self.artifact_root / "Image"
        real = self.artifact_root / "Image.real"
        image.rename(real)
        image.symlink_to(real.name)
        with self.assertRaises(TOOL.CANDIDATE.CandidateError):
            self.verify()
        image.unlink()
        real.rename(image)

        hardlink = self.artifact_root / "Image.hardlink"
        hardlink.hardlink_to(image)
        with self.assertRaises(TOOL.CANDIDATE.CandidateError):
            self.verify()
        hardlink.unlink()

    def test_base_and_successor_roles_are_not_interchangeable(self) -> None:
        cases = (
            (self.base_record, self.base_record),
            (self.successor_record, self.base_record),
            (self.successor_record, self.successor_record),
        )
        for base, successor in cases:
            with self.subTest(
                base=base["bundle"],
                successor=successor["bundle"],
            ):
                self.write_candidate(self.base_candidate, base)
                self.write_candidate(self.candidate, successor)
                with self.assertRaises(TOOL.SuccessorPreflightError):
                    self.verify()

    def test_unexpected_manifest_identity_fails_closed(self) -> None:
        with (
            mock.patch.object(
                TOOL.STAGER,
                "verify_repository_checkpoint",
                return_value="a" * 40,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_MANIFEST_SHA256",
                "0" * 64,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_BASE_CANDIDATE_SHA256",
                self.base_candidate_sha256,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_SUCCESSOR_CANDIDATE_SHA256",
                self.candidate_sha256,
            ),
        ):
            with self.assertRaisesRegex(
                TOOL.SuccessorPreflightError,
                "pinned prediction",
            ):
                TOOL.verify(
                    self.package,
                    self.base_candidate,
                    self.candidate,
                )

    def test_checkpoint_gate_precedes_external_input_access(self) -> None:
        with (
            mock.patch.object(
                TOOL.STAGER,
                "verify_repository_checkpoint",
                side_effect=TOOL.STAGER.SigningInputError("checkpoint"),
            ),
            mock.patch.object(
                TOOL.DEPLOYMENT,
                "parse_package",
                side_effect=AssertionError("package reached"),
            ),
            mock.patch.object(
                TOOL.STAGER,
                "read_private_input",
                side_effect=AssertionError("candidate reached"),
            ),
        ):
            with self.assertRaises(TOOL.STAGER.SigningInputError):
                TOOL.verify(
                    self.package,
                    self.base_candidate,
                    self.candidate,
                )

    def test_production_identities_rederive_from_tracked_contract(self) -> None:
        with (
            mock.patch.object(TOOL.CANDIDATE, "REPO", REPO),
            mock.patch.object(
                TOOL.CANDIDATE,
                "CANDIDATE_ROOT",
                REPO / "configs/recovery-candidates",
            ),
        ):
            package = dict(
                TOOL.CANDIDATE.EXTERNAL_SUCCESSOR_ROOT_FIELDS[
                    TOOL.DEPLOYMENT.SUCCESSOR_BUNDLE_ID
                ]
            )
            baseline = TOOL.DEPLOYMENT.candidate_record(
                package,
                TOOL.DEPLOYMENT.BASE_BUNDLE_ID,
            )
            successor = TOOL.DEPLOYMENT.candidate_record(
                package,
                TOOL.DEPLOYMENT.SUCCESSOR_BUNDLE_ID,
            )
        observed = {
            name: (artifact["size"], artifact["sha256"])
            for name, artifact in successor["artifacts"].items()
        }
        self.assertEqual(
            TOOL.manifest_identity(successor, observed),
            "9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630",
        )
        self.assertEqual(
            hashlib.sha256(
                TOOL.DEPLOYMENT.canonical_payload(baseline)
            ).hexdigest(),
            "cda35b12db73966fd231ea6889978da5fbf9ab62375177a21084c2ec822f6bcd",
        )
        self.assertEqual(
            hashlib.sha256(
                TOOL.DEPLOYMENT.canonical_payload(successor)
            ).hexdigest(),
            "b26bc73ec6cd0053900044776270ed2c3a7f7bf6424140a59bb74d513b5dd51e",
        )
        self.assertEqual(
            TOOL.EXPECTED_MANIFEST_SHA256,
            TOOL.manifest_identity(successor, observed),
        )
        self.assertEqual(
            TOOL.EXPECTED_BASE_CANDIDATE_SHA256,
            hashlib.sha256(
                TOOL.DEPLOYMENT.canonical_payload(baseline)
            ).hexdigest(),
        )
        self.assertEqual(
            TOOL.EXPECTED_SUCCESSOR_CANDIDATE_SHA256,
            hashlib.sha256(
                TOOL.DEPLOYMENT.canonical_payload(successor)
            ).hexdigest(),
        )

    def test_source_has_no_phone_network_or_privilege_surface(self) -> None:
        source = TOOL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "socket",
            "fastboot",
            "adb",
            "pkexec",
            "sudo",
            "/dev/bus/usb",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_manifest_identity_never_reads_or_depends_on_paths(self) -> None:
        observed = {
            name: (len(payload), hashlib.sha256(payload).hexdigest())
            for name, payload in self.payloads.items()
        }
        paths_a = {
            name: Path("/unavailable/a") / name
            for name in TOOL.CANDIDATE.ARTIFACT_NAMES
        }
        paths_b = {
            name: Path("/unavailable/b") / name
            for name in TOOL.CANDIDATE.ARTIFACT_NAMES
        }
        config_a = TOOL.CANDIDATE.bundle_configuration(
            self.successor_record,
            paths_a,
            Path("/unavailable/key-a"),
            Path("/unavailable/bundles-a"),
        )
        config_b = TOOL.CANDIDATE.bundle_configuration(
            self.successor_record,
            paths_b,
            Path("/unavailable/key-b"),
            Path("/unavailable/bundles-b"),
        )
        with (
            mock.patch.object(
                Path,
                "stat",
                side_effect=AssertionError("path read"),
            ),
            mock.patch.object(
                Path,
                "open",
                side_effect=AssertionError("path opened"),
            ),
            mock.patch(
                "builtins.open",
                side_effect=AssertionError("path opened"),
            ),
            mock.patch.object(
                TOOL.os,
                "open",
                side_effect=AssertionError("path opened"),
            ),
            mock.patch.object(
                TOOL.os,
                "stat",
                side_effect=AssertionError("path read"),
            ),
            mock.patch.object(
                TOOL.os,
                "lstat",
                side_effect=AssertionError("path read"),
            ),
        ):
            TOOL.PACKAGER.validate_configuration(config_a)
            TOOL.PACKAGER.validate_configuration(config_b)
            manifest_a = TOOL.PACKAGER.manifest_bytes(config_a, observed)
            manifest_b = TOOL.PACKAGER.manifest_bytes(config_b, observed)
        self.assertEqual(manifest_a, manifest_b)

    def test_import_failure_is_sanitized(self) -> None:
        isolated = self.root / "isolated" / "scripts" / "host"
        isolated.mkdir(parents=True)
        script = isolated / TOOL_PATH.name
        shutil.copyfile(TOOL_PATH, script)
        script.chmod(0o755)
        result = subprocess.run(
            [sys.executable, str(script)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, f"{TOOL.FAILURE}\n")

    def test_failed_dynamic_import_is_removed_from_module_cache(self) -> None:
        name = "rog5_successor_preflight_broken_dependency"
        broken = self.root / "broken.py"
        broken.write_text("raise RuntimeError('private detail')\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "private detail"):
            TOOL.load_module(name, broken)
        self.assertNotIn(name, sys.modules)

    def test_checkpoint_change_during_preflight_fails_closed(self) -> None:
        with (
            mock.patch.object(
                TOOL.STAGER,
                "verify_repository_checkpoint",
                side_effect=("a" * 40, "b" * 40),
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_MANIFEST_SHA256",
                self.manifest_sha256,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_BASE_CANDIDATE_SHA256",
                self.base_candidate_sha256,
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_SUCCESSOR_CANDIDATE_SHA256",
                self.candidate_sha256,
            ),
        ):
            with self.assertRaisesRegex(
                TOOL.SuccessorPreflightError,
                "checkpoint changed",
            ):
                TOOL.verify(
                    self.package,
                    self.base_candidate,
                    self.candidate,
                )

    def test_cli_is_canonical_and_failures_are_sanitized(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(
                TOOL,
                "verify",
                return_value=(
                    "a" * 40,
                    "b" * 64,
                    "c" * 64,
                    "d" * 64,
                ),
            ),
            redirect_stdout(output),
        ):
            self.assertEqual(
                TOOL.main(
                    [
                        "--package",
                        str(self.package),
                        "--base-candidate-record",
                        str(self.base_candidate),
                        "--candidate-record",
                        str(self.candidate),
                    ]
                ),
                0,
            )
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "format=rog5-headless-ssh-successor-preflight-v1",
                f"checkpoint={'a' * 40}",
                "candidate=headless-ssh-network-root-v3",
                "bundle=headless-ssh-network-root-v3-r2",
                f"base_candidate_sha256={'b' * 64}",
                f"candidate_sha256={'c' * 64}",
                f"manifest_sha256={'d' * 64}",
                "authority=none",
                "credential_access=none",
                "phone_access=none",
            ],
        )

        error = io.StringIO()
        with (
            mock.patch.object(
                TOOL,
                "verify",
                side_effect=TOOL.SuccessorPreflightError("private detail"),
            ),
            redirect_stderr(error),
        ):
            self.assertEqual(
                TOOL.main(
                    [
                        "--package",
                        str(self.package),
                        "--base-candidate-record",
                        str(self.base_candidate),
                        "--candidate-record",
                        str(self.candidate),
                    ]
                ),
                1,
            )
        self.assertEqual(
            error.getvalue(),
            "FAIL successor candidate preflight refused\n",
        )

        error = io.StringIO()
        with (
            mock.patch.object(
                TOOL,
                "verify",
                side_effect=TypeError("private record detail"),
            ),
            redirect_stderr(error),
        ):
            self.assertEqual(
                TOOL.main(
                    [
                        "--package",
                        str(self.package),
                        "--base-candidate-record",
                        str(self.base_candidate),
                        "--candidate-record",
                        str(self.candidate),
                    ]
                ),
                1,
            )
        self.assertEqual(error.getvalue(), f"{TOOL.FAILURE}\n")


if __name__ == "__main__":
    unittest.main()
