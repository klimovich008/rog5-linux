#!/usr/bin/env python3
"""Hardware-free tests for the generic exact-record boot-claim consumer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ast
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
GATE = REPO / "scripts/host/run-stable-recovery-live-gate.sh"
OBSERVER_GATE = REPO / "scripts/host/run-observation-recovery-live-gate.sh"
REFERENCE_PATH = REPO / "scripts/host/retention-cycle-sequence-reference.py"
CURRENT_REFERENCE_PATH = (
    REPO / "scripts/host/retention-cycle-mainline-udc-v11.py"
)
CURRENT_XATTR_REFERENCE_PATH = (
    REPO / "scripts/host/retention-cycle-nfs-xattr-v12.py"
)
HISTORICAL_MANIFESTS = {
    "headless-diagnostic-generation11-live-v1": (
        "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
    ),
    "headless-diagnostic-generation12-live-v1": (
        "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
    ),
}

SPEC = importlib.util.spec_from_file_location("consume_exact_boot_claim", CONSUMER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load generic exact-record claim consumer")
CLAIMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLAIMS)
REFERENCE_SPEC = importlib.util.spec_from_file_location(
    "retention_sequence_for_claim_test", REFERENCE_PATH
)
if REFERENCE_SPEC is None or REFERENCE_SPEC.loader is None:
    raise RuntimeError("cannot load retention-cycle claim reference")
REFERENCE = importlib.util.module_from_spec(REFERENCE_SPEC)
sys.modules[REFERENCE_SPEC.name] = REFERENCE
REFERENCE_SPEC.loader.exec_module(REFERENCE)
CURRENT_REFERENCE_SPEC = importlib.util.spec_from_file_location(
    "current_retention_sequence_for_claim_test", CURRENT_REFERENCE_PATH
)
if CURRENT_REFERENCE_SPEC is None or CURRENT_REFERENCE_SPEC.loader is None:
    raise RuntimeError("cannot load current retention-cycle claim reference")
CURRENT_REFERENCE = importlib.util.module_from_spec(CURRENT_REFERENCE_SPEC)
sys.modules[CURRENT_REFERENCE_SPEC.name] = CURRENT_REFERENCE
CURRENT_REFERENCE_SPEC.loader.exec_module(CURRENT_REFERENCE)
CURRENT_XATTR_REFERENCE_SPEC = importlib.util.spec_from_file_location(
    "current_xattr_retention_sequence_for_claim_test",
    CURRENT_XATTR_REFERENCE_PATH,
)
if (
    CURRENT_XATTR_REFERENCE_SPEC is None
    or CURRENT_XATTR_REFERENCE_SPEC.loader is None
):
    raise RuntimeError("cannot load current xattr retention-cycle claim reference")
CURRENT_XATTR_REFERENCE = importlib.util.module_from_spec(
    CURRENT_XATTR_REFERENCE_SPEC
)
sys.modules[CURRENT_XATTR_REFERENCE_SPEC.name] = CURRENT_XATTR_REFERENCE
CURRENT_XATTR_REFERENCE_SPEC.loader.exec_module(CURRENT_XATTR_REFERENCE)
PROFILES = {
    profile: (
        "format=rog5-temporary-boot-consumption-v1\n"
        f"recovery_profile={profile}\n"
        "candidate=headless-netroot-early-diag-v1\n"
        f"manifest_sha256={manifest}\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")
    for profile, manifest in HISTORICAL_MANIFESTS.items()
}
PROFILES.update(
    {
        "persistent-root-dtb-control-v7-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-dtb-control-v7-live-v1\n"
            b"candidate=persistent-root-dtb-control-v7\n"
            b"manifest_sha256="
            b"c4cef9e256708d219c7c77f792dbff43336c5d446d0721048ff471b7c05969ee\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-usb-control-v6-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-usb-control-v6-live-v1\n"
            b"candidate=persistent-root-usb-control-v6\n"
            b"manifest_sha256="
            b"33715e0c566a5fc7e771f6b89ca81fd1fe0bb6325b926995a0ba5c5f81a44a5b\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-storage-read-v5-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-storage-read-v5-live-v1\n"
            b"candidate=persistent-root-storage-read-v5\n"
            b"manifest_sha256="
            b"1d64161dd213ced57b6761086629351ba116b30f894aa36afba9480873b4e3ab\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-storage-read-v4-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-storage-read-v4-live-v1\n"
            b"candidate=persistent-root-storage-read-v4\n"
            b"manifest_sha256="
            b"5d835b0986587c7ce174e66ccf03f82bb8c9e581e83384ce93c0ed455d053baa\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-storage-read-v3-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-storage-read-v3-live-v1\n"
            b"candidate=persistent-root-storage-read-v3\n"
            b"manifest_sha256="
            b"3bc4b40f7e230945249db08be19b5791c176e08aeb8b5cfca059f48db5b8ed73\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-storage-read-v2-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-storage-read-v2-live-v1\n"
            b"candidate=persistent-root-storage-read-v2\n"
            b"manifest_sha256="
            b"4b56111b2f40157b5173a24adfedf53341cb243a661fc744410673b1ab7aa567\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-storage-read-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-storage-read-v1-live-v1\n"
            b"candidate=persistent-root-storage-read-v1\n"
            b"manifest_sha256="
            b"f82ea25ffb484668dd56cbd01b33b12062d26d29d40d14000b73afe41c857753\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-core-deployment-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=headless-core-deployment-v1-live-v1\n"
            b"candidate=headless-core-network-root-v2\n"
            b"manifest_sha256="
            b"f3884e6554f3d2c1bb437c45484f658817c006185d6c84a5ac4ef452b01bc02f\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-iproute-whitespace-v19-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-iproute-whitespace-v19-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-configfs-link-v18-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-configfs-link-v18-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-gadget-contract-v17-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-gadget-contract-v17-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-inert-block-v16-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-inert-block-v16-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-network-ready-v15-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-network-ready-v15-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-bootstrap-v14-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-bootstrap-v14-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-ssh-acceptance-v13-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-ssh-acceptance-v13-live-v1\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v2": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v2\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v3": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v3\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v4": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v4\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v5": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v5\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v6": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v6\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v7": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v7\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v8": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v8\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v9": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v9\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "headless-diagnostic-host-rendezvous-v3-live-v10": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"headless-diagnostic-host-rendezvous-v3-live-v10\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "retention-host-rendezvous-v3-observer-v2": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=retention-host-rendezvous-v3-observer-v2\n"
            b"candidate=headless-netroot-early-diag-v2\n"
            b"manifest_sha256="
            b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
            b"state=BOOT_CLAIMED\n"
        ),
        REFERENCE.EXECUTION_CLAIM.identifier: REFERENCE.EXECUTION_CLAIM.record,
        REFERENCE.OBSERVER_CLAIM.identifier: REFERENCE.OBSERVER_CLAIM.record,
        CURRENT_REFERENCE.EXECUTION_CLAIM.identifier: (
            CURRENT_REFERENCE.EXECUTION_CLAIM.record
        ),
        CURRENT_REFERENCE.OBSERVER_CLAIM.identifier: (
            CURRENT_REFERENCE.OBSERVER_CLAIM.record
        ),
        CURRENT_XATTR_REFERENCE.EXECUTION_CLAIM.identifier: (
            CURRENT_XATTR_REFERENCE.EXECUTION_CLAIM.record
        ),
        CURRENT_XATTR_REFERENCE.OBSERVER_CLAIM.identifier: (
            CURRENT_XATTR_REFERENCE.OBSERVER_CLAIM.record
        ),
    }
)
REAL_ANCHOR_PARENT_IS_REPLACE_PROTECTED = (
    CLAIMS.anchor_parent_is_replace_protected
)


class ExactClaimConsumerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        self.root = self.state / "rog5-temporary-boot-consumption"
        self.root.mkdir(parents=True, mode=0o700)
        anchor_protection = mock.patch.object(
            CLAIMS,
            "anchor_parent_is_replace_protected",
            return_value=True,
        )
        anchor_protection.start()
        self.addCleanup(anchor_protection.stop)

    def expected(self, profile: str) -> bytes:
        return PROFILES[profile]

    def paths(self, profile: str) -> tuple[Path, Path]:
        record = self.root / f"{profile}.record"
        return record, record.with_name(record.name + ".entered")

    def guard(self, profile: str) -> Path:
        return self.state / (
            f".rog5-temporary-boot-consumption.{profile}.entered"
        )

    def write_record(self, profile: str, payload: bytes | None = None) -> Path:
        record, _entered = self.paths(profile)
        record.write_bytes(payload if payload is not None else self.expected(profile))
        record.chmod(0o600)
        return record

    def test_repository_lookup_admits_only_reviewed_exact_records(self) -> None:
        self.assertEqual(set(CLAIMS.CLAIMS), set(PROFILES))
        self.assertNotIn("generation13", CONSUMER.read_text(encoding="utf-8"))
        for profile in PROFILES:
            with self.subTest(profile=profile):
                self.write_record(profile)
                CLAIMS.consume(profile, self.root)
                record, entered = self.paths(profile)
                self.assertFalse(record.exists())
                self.assertEqual(entered.read_bytes(), self.expected(profile))
                entered.unlink()
        with self.assertRaisesRegex(CLAIMS.ClaimError, "not repository-owned"):
            CLAIMS.consume("headless-diagnostic-generation13-live-v1", self.root)

    def test_repository_lookup_is_a_literal_exact_record_registry(self) -> None:
        tree = ast.parse(CONSUMER.read_bytes(), filename=str(CONSUMER))
        assignments = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "CLAIMS"
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1)
        self.assertIsInstance(assignments[0].value, ast.Dict)
        self.assertNotIn("CLAIM_PROFILES", CONSUMER.read_text(encoding="utf-8"))

    def test_wrong_content_owner_mode_link_and_symlink_fail_closed(self) -> None:
        profile = next(iter(PROFILES))
        cases = ("content", "mode", "hardlink", "symlink")
        for case in cases:
            with self.subTest(case=case):
                record, entered = self.paths(profile)
                record.unlink(missing_ok=True)
                entered.unlink(missing_ok=True)
                record = self.write_record(profile)
                if case == "content":
                    record.write_bytes(self.expected(profile) + b"extra=1\n")
                elif case == "mode":
                    record.chmod(0o644)
                elif case == "hardlink":
                    os.link(record, record.with_suffix(".copy"))
                else:
                    target = self.state / "outside-record"
                    record.replace(target)
                    record.symlink_to(target)
                with self.assertRaises(CLAIMS.ClaimError):
                    CLAIMS.consume(profile, self.root)
                self.assertFalse(entered.exists())

    def test_root_metadata_and_symlink_fail_closed(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(CLAIMS.ClaimError, "root is unsafe"):
            CLAIMS.consume(profile, self.root)
        self.root.chmod(0o700)
        moved = self.state / "moved"
        self.root.rename(moved)
        self.root.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(CLAIMS.ClaimError, "root is unsafe"):
            CLAIMS.consume(profile, self.root)

    def test_replaceable_anchor_parent_fails_before_entry(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        with (
            mock.patch.object(
                CLAIMS,
                "anchor_parent_is_replace_protected",
                return_value=False,
            ),
            self.assertRaisesRegex(
                CLAIMS.ClaimError,
                "anchor parent is replaceable",
            ),
        ):
            CLAIMS.consume(profile, self.root)
        self.assertFalse(self.guard(profile).exists())
        _record, entered = self.paths(profile)
        self.assertFalse(entered.exists())

    def test_lifecycle_owned_readonly_anchor_parent_fails_before_entry(
        self,
    ) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        anchor_parent = self.state.parent
        anchor_parent.chmod(0o555)
        self.addCleanup(anchor_parent.chmod, 0o700)
        with (
            mock.patch.object(
                CLAIMS,
                "anchor_parent_is_replace_protected",
                REAL_ANCHOR_PARENT_IS_REPLACE_PROTECTED,
            ),
            self.assertRaisesRegex(
                CLAIMS.ClaimError,
                "anchor parent is replaceable",
            ),
        ):
            CLAIMS.consume(profile, self.root)
        self.assertFalse(self.guard(profile).exists())
        _record, entered = self.paths(profile)
        self.assertFalse(entered.exists())

    def test_global_guard_requires_exact_content_and_metadata(self) -> None:
        profile = next(iter(PROFILES))
        _record, entered = self.paths(profile)
        guard = self.guard(profile)
        for case in ("content", "mode", "hardlink", "symlink"):
            with self.subTest(case=case):
                guard.unlink(missing_ok=True)
                entered.unlink(missing_ok=True)
                copy = guard.with_suffix(".copy")
                copy.unlink(missing_ok=True)
                target = guard.with_suffix(".target")
                target.unlink(missing_ok=True)
                guard.write_bytes(self.expected(profile))
                guard.chmod(0o600)
                if case == "content":
                    guard.write_bytes(self.expected(profile) + b"extra=1\n")
                elif case == "mode":
                    guard.chmod(0o644)
                elif case == "hardlink":
                    os.link(guard, copy)
                else:
                    guard.replace(target)
                    guard.symlink_to(target)
                self.write_record(profile)
                with self.assertRaisesRegex(
                    CLAIMS.ClaimError,
                    "global BOOT_CLAIMED guard is unsafe",
                ):
                    CLAIMS.consume(profile, self.root)
                self.assertFalse(entered.exists())
    def test_wrong_record_owner_fails_before_entry(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        _record, entered = self.paths(profile)
        original_fstat = os.fstat

        def wrong_regular_owner(descriptor: int) -> os.stat_result:
            metadata = original_fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                return metadata
            fields = list(metadata)
            fields[stat.ST_UID] = metadata.st_uid + 1
            return os.stat_result(fields)

        with mock.patch.object(
            CLAIMS.os,
            "fstat",
            side_effect=wrong_regular_owner,
        ):
            with self.assertRaisesRegex(CLAIMS.ClaimError, "record is unsafe"):
                CLAIMS.consume(profile, self.root)
        self.assertFalse(entered.exists())

    def test_pathname_replacement_cannot_poison_irreversible_entry(
        self,
    ) -> None:
        profile = next(iter(PROFILES))
        record = self.write_record(profile)
        _record, entered = self.paths(profile)
        original_create = CLAIMS.create_entered_record

        create_calls = 0

        def replace_then_create(*args: object, **kwargs: object) -> int:
            nonlocal create_calls
            create_calls += 1
            if create_calls == 2:
                record.unlink()
                self.write_record(
                    profile,
                    self.expected(profile).replace(
                        b"BOOT_CLAIMED", b"UNVALIDATED"
                    ),
                )
            return original_create(*args, **kwargs)

        with mock.patch.object(
            CLAIMS,
            "create_entered_record",
            side_effect=replace_then_create,
        ):
            with self.assertRaisesRegex(
                CLAIMS.ClaimError,
                "source BOOT_CLAIMED record changed during entry",
            ):
                CLAIMS.consume(profile, self.root)
        self.assertTrue(entered.exists())
        self.assertEqual(entered.read_bytes(), self.expected(profile))
        with self.assertRaisesRegex(CLAIMS.ClaimError, "already entered"):
            CLAIMS.consume(profile, self.root)

    def test_fsync_and_final_root_revalidation_preserve_at_most_once(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        original_fsync = os.fsync
        calls = 0

        def replace_after_final_fsync(descriptor: int) -> None:
            nonlocal calls
            original_fsync(descriptor)
            calls += 1
            if calls == 5:
                moved = self.state / "entered-root"
                self.root.rename(moved)
                self.root.mkdir(mode=0o700)

        with mock.patch.object(CLAIMS.os, "fsync", side_effect=replace_after_final_fsync):
            with self.assertRaisesRegex(CLAIMS.ClaimError, "changed during entry"):
                CLAIMS.consume(profile, self.root)
        self.assertEqual(calls, 5)
        self.assertTrue(
            (self.state / "entered-root" / f"{profile}.record.entered").exists()
        )

    def test_root_replacement_after_global_entry_cannot_be_consumed_twice(
        self,
    ) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        moved = self.state / "detached-root"
        original_create = CLAIMS.create_entered_record
        create_calls = 0

        def replace_root_before_inner_entry(
            *args: object,
            **kwargs: object,
        ) -> int:
            nonlocal create_calls
            create_calls += 1
            if create_calls == 2:
                self.root.rename(moved)
                self.root.mkdir(mode=0o700)
                self.write_record(profile)
            return original_create(*args, **kwargs)

        with mock.patch.object(
            CLAIMS,
            "create_entered_record",
            side_effect=replace_root_before_inner_entry,
        ):
            with self.assertRaisesRegex(
                CLAIMS.ClaimError,
                "claim root changed during entry",
            ):
                CLAIMS.consume(profile, self.root)

        self.assertEqual(self.guard(profile).read_bytes(), self.expected(profile))
        self.assertEqual(
            (moved / f"{profile}.record.entered").read_bytes(),
            self.expected(profile),
        )
        with self.assertRaisesRegex(CLAIMS.ClaimError, "already entered"):
            CLAIMS.consume(profile, self.root)
        _record, replacement_entered = self.paths(profile)
        self.assertFalse(replacement_entered.exists())

    def test_concurrent_consumers_admit_exactly_one(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)

        def attempt() -> bool:
            try:
                CLAIMS.consume(profile, self.root)
            except (CLAIMS.ClaimError, OSError):
                return False
            return True

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: attempt(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        _record, entered = self.paths(profile)
        self.assertEqual(entered.read_bytes(), self.expected(profile))

    def test_entered_verifier_requires_source_absent_and_two_exact_records(
        self,
    ) -> None:
        profile = REFERENCE.OBSERVER_CLAIM.identifier
        self.write_record(profile)
        with self.assertRaisesRegex(CLAIMS.ClaimError, "source.*exists"):
            CLAIMS.verify_entered(profile, self.root)
        CLAIMS.consume(profile, self.root)
        CLAIMS.verify_entered(profile, self.root)
        _record, entered = self.paths(profile)
        for path in (entered, self.guard(profile)):
            with self.subTest(path=path.name):
                exact = path.read_bytes()
                path.write_bytes(exact + b"x")
                with self.assertRaises(CLAIMS.ClaimError):
                    CLAIMS.verify_entered(profile, self.root)
                path.write_bytes(exact)
                path.chmod(0o600)

    def test_generic_consumer_replaces_future_copying_and_retains_history(
        self,
    ) -> None:
        source = GATE.read_text(encoding="utf-8")
        observer_source = OBSERVER_GATE.read_text(encoding="utf-8")
        self.assertNotIn("consume-exact-boot-claim.py", source)
        self.assertIn("consume-exact-boot-claim.py", observer_source)
        self.assertIn("--verify-entered", observer_source)
        self.assertNotIn("claim_consumer=$repo/scripts/host/consume-generation12", source)
        self.assertTrue(CONSUMER.is_file())
        self.assertTrue(os.access(CONSUMER, os.X_OK))
        for generation in (11, 12):
            historical = REPO / f"scripts/host/consume-generation{generation}-boot-claim.py"
            self.assertTrue(historical.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
