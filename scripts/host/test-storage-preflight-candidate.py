#!/usr/bin/env python3
"""Exact-source and optional local-artifact checks for Generations 71-74."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import importlib.util
from pathlib import Path
import stat
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests/storage-preflight-v1-generation71.manifest"
MANIFEST_V2 = REPO / "manifests/storage-preflight-v2-generation72.manifest"
MANIFEST_V3 = REPO / "manifests/storage-preflight-v3-generation73.manifest"
MANIFEST_V4 = REPO / "manifests/storage-preflight-v4-generation74.manifest"
CURRENT = REPO / "manifests/storage-preflight-current-generation164.manifest"
POLICY = REPO / "manifests/storage-preflight-temporary-boot-v1.tsv"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
PROFILE = "storage-preflight-v1-generation71-live-v1"
MANIFEST_SHA256 = "a14872f8ca4db705015586f4e199e5bdf607f947f96949eecd35e42a137d19c5"
PROFILE_V2 = "storage-preflight-v2-generation72-live-v1"
MANIFEST_V2_SHA256 = (
    "7a436a3716d56536326040fd626c3dc8b760c2ef94ee2d0695e536d2ee779935"
)
PROFILE_V3 = "storage-preflight-v3-generation73-live-v1"
MANIFEST_V3_SHA256 = (
    "1721186c050eb2c2130492217cb1838782d0c63936183968fef716b62bcce4b6"
)
PROFILE_V4 = "storage-preflight-v4-generation74-live-v1"
MANIFEST_V4_SHA256 = (
    "4ab1ad92b75b975c887bca9b1f4d2617f0d9267dd1b179bb36a0f37c791bff64"
)
CURRENT_PROFILE = "storage-preflight-current-generation164-live-v1"
CURRENT_MANIFEST_SHA256 = (
    "8f0f1f5c22231e7c2090299c1b0878b38e09b1839ecaf9cf8cdaf2643e365f6a"
)

EXPECTED = OrderedDict(
    (
        ("format", "rog5-storage-preflight-candidate-v1"),
        ("profile", PROFILE),
        ("candidate", "storage-preflight-v1"),
        ("source_checkpoint", "54af0d90147e97c8f9133b1690b8a39f02ca417f"),
        (
            "image_path",
            "build/storage-preflight-wrapper-v1-20260814-r1/"
            "repack/stable-recovery-a.avb.img",
        ),
        ("image_size", "100663296"),
        (
            "image_sha256",
            "69a1139c13a0cb1b025ee85719d319f42431e07bde6c044c828c95c2ad120b1f",
        ),
        (
            "raw_sha256",
            "21aaf13c9a9fbec3fe42cb75af0a2fda1abf24ed2e36800d7b6927b9201b9bd9",
        ),
        (
            "kernel_sha256",
            "8dc38de4063d4b6d83f7f5cadd1c2d138bfc33677287fa054c9735939bd802ae",
        ),
        (
            "wrapper_config_sha256",
            "df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f",
        ),
        (
            "initramfs_sha256",
            "46e81f34900905ac82bd3ad8749e5332a571e50e3ceb388c5c8b5c825a13ddfb",
        ),
        (
            "recovery_init_sha256",
            "c1b83c2bf72b722629ddbe0ed76ea6a743aaab0784f9b0495fd55073421ef53c",
        ),
        (
            "collector_sha256",
            "c09bdf60bdd12c5b2b1ad158c6121e003c77b4bbe97ea8d0c2dfd54947d3b940",
        ),
        (
            "layout_sha256",
            "0a12212eefdf2594b8ee74757eeacb168c825ffff481cb6044b8871e19382fb1",
        ),
        ("boot_mode", "temporary-ram-only"),
        ("storage_mode", "read-only-no-mounts"),
        ("fallback", "verified-alpine"),
        ("reuse", "forbidden-after-claim-entry"),
    )
)

EXPECTED_V2 = OrderedDict(
    (
        ("format", "rog5-storage-preflight-candidate-v2"),
        ("profile", PROFILE_V2),
        ("candidate", "storage-preflight-v2"),
        ("source_checkpoint", "81b7b7c9f67e8303487cac6ad014b5345086df26"),
        (
            "image_path",
            "build/storage-preflight-wrapper-v2-generation72-20260814-r1/"
            "repack/stable-recovery-a.avb.img",
        ),
        ("image_size", "100663296"),
        (
            "image_sha256",
            "5e55d2fd6ad6e838e99aadd62398027a6eab5667efa8fe5a58d76562d31e4497",
        ),
        (
            "raw_sha256",
            "d834309806ff3406fd11614513914694b3af60c5728dcabda2c7a4ced30cdfea",
        ),
        (
            "kernel_sha256",
            "8dc38de4063d4b6d83f7f5cadd1c2d138bfc33677287fa054c9735939bd802ae",
        ),
        (
            "wrapper_config_sha256",
            "df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f",
        ),
        (
            "initramfs_sha256",
            "fddeb2a6eae0712d53c7fdd5c024f4c0ba0795e76de9a3ab63f82dd996ee91be",
        ),
        (
            "recovery_init_sha256",
            "c82704a691adb71c8b653d09789115973dcedf94802e4c66f642103fd397e083",
        ),
        (
            "collector_sha256",
            "883b0f6c495059edc00f74b5857e6cecd270fb70a3416e2a1fff1ba47aa664e4",
        ),
        (
            "runtime_verifier_sha256",
            "f4c0b7b06910a0e4aa9dd08d2a8c4951b8b3e655e8379af1937a5266e66c174a",
        ),
        (
            "layout_sha256",
            "0a12212eefdf2594b8ee74757eeacb168c825ffff481cb6044b8871e19382fb1",
        ),
        ("boot_mode", "temporary-ram-only"),
        ("storage_mode", "read-only-no-mounts"),
        ("report_mode", "receive-only-acm-terminal-v2"),
        ("failure_visibility_seconds", "10"),
        ("fallback", "verified-alpine"),
        ("reuse", "forbidden-after-claim-entry"),
    )
)

EXPECTED_V3 = OrderedDict(
    (
        ("format", "rog5-storage-preflight-candidate-v3"),
        ("profile", PROFILE_V3),
        ("candidate", "storage-preflight-v3"),
        ("source_checkpoint", "dcb1e4b630804826038cbf1179d76c459a7473a8"),
        (
            "image_path",
            "build/storage-preflight-wrapper-v3-generation73-20260815-r2/"
            "repack/stable-recovery-a.avb.img",
        ),
        ("image_size", "100663296"),
        (
            "image_sha256",
            "ce86da71c7593579e9eae28e265dc3c91483f0fa4a924701d704cabfe5fbff58",
        ),
        (
            "raw_sha256",
            "0d72ebbe28abadaa2b910803343571c580d8c1d620e5aa8b045a112ccc4d9365",
        ),
        (
            "kernel_sha256",
            "8dc38de4063d4b6d83f7f5cadd1c2d138bfc33677287fa054c9735939bd802ae",
        ),
        (
            "wrapper_config_sha256",
            "df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f",
        ),
        (
            "initramfs_sha256",
            "549ec5d58b8070a3784a652f64ce1ef6e9011ce2578c65f29d57d0c1eefd0f8d",
        ),
        (
            "recovery_init_sha256",
            "94ca78bd7736615746089ba8ad63f1eca4592f29efcef55a00d556f46ea8c345",
        ),
        (
            "collector_sha256",
            "4513e805f6532824cb54c13e6542485dccca5050641741bb64c450ca8b0a25ab",
        ),
        (
            "runtime_verifier_sha256",
            "7ef621deccc1cad89c8825ca2476f04905e19ff382cee429a9f6b2e4a849d798",
        ),
        (
            "layout_sha256",
            "0a12212eefdf2594b8ee74757eeacb168c825ffff481cb6044b8871e19382fb1",
        ),
        ("wrapper_kernel_provenance", "retained-generation72-byte-exact"),
        ("boot_mode", "temporary-ram-only"),
        ("storage_mode", "read-only-no-mounts"),
        ("report_mode", "receive-only-acm-raw-persistent-terminal-v3"),
        ("rejected_evidence", "bounded-fail-closed-v1"),
        ("failure_visibility_seconds", "10"),
        ("fallback", "verified-alpine"),
        ("reuse", "forbidden-after-claim-entry"),
    )
)

EXPECTED_V4 = OrderedDict(
    (
        ("format", "rog5-storage-preflight-candidate-v4"),
        ("profile", PROFILE_V4),
        ("candidate", "storage-preflight-v4"),
        ("source_checkpoint", "b8f6e9f39f55d7741c0b9122e1ef59b6148836f4"),
        (
            "image_path",
            "build/storage-preflight-wrapper-v4-generation74-20260815-r2/"
            "repack/stable-recovery-a.avb.img",
        ),
        ("image_size", "100663296"),
        (
            "image_sha256",
            "4f7343b1701002dfeab327e6d1110c2d77ea9671cfa033e786f7aa591439d9ca",
        ),
        (
            "raw_sha256",
            "cd9c345101bb203c833123ff3766beefca6381b11fca4eb8eeaaa3881dbf59d0",
        ),
        (
            "kernel_sha256",
            "8dc38de4063d4b6d83f7f5cadd1c2d138bfc33677287fa054c9735939bd802ae",
        ),
        (
            "wrapper_config_sha256",
            "df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f",
        ),
        (
            "initramfs_sha256",
            "ae7ba9045045e1ac7048dc7061bf9f8c780fa53c43bfd43aebbecb29b03fa9f4",
        ),
        (
            "recovery_init_sha256",
            "4e07f4d5f4a88b80a102edfb454ed2cf507bb7e9d513f0ff20b21a7e5999b431",
        ),
        (
            "collector_sha256",
            "eeb7a615bbbec3372c48d88ecdb9347f3ca9682cc281df4e8af438857498b190",
        ),
        (
            "runtime_verifier_sha256",
            "4e57f6d0d17bfddf90aa385bbd5ed07a6485de9104216c533dba3f8f7f850ec2",
        ),
        (
            "layout_sha256",
            "189b158c08943e46b1dae455e203db3e556a6c9f2b7880b058684950eef2df62",
        ),
        ("wrapper_kernel_provenance", "retained-generation73-byte-exact"),
        ("boot_mode", "temporary-ram-only"),
        ("storage_mode", "read-only-no-mounts"),
        ("report_mode", "receive-only-acm-raw-persistent-terminal-v4"),
        ("rejected_evidence", "bounded-fail-closed-v1"),
        ("failure_visibility_seconds", "10"),
        ("fallback", "verified-alpine"),
        ("reuse", "forbidden-after-claim-entry"),
    )
)

SPEC = importlib.util.spec_from_file_location("storage_claim_consumer", CONSUMER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load generic claim consumer")
CLAIMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLAIMS)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def canonical_manifest(path: Path = MANIFEST) -> OrderedDict[str, str]:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o022:
        raise AssertionError("candidate manifest metadata is unsafe")
    payload = path.read_bytes()
    if not payload.endswith(b"\n"):
        raise AssertionError("candidate manifest lacks canonical newline")
    values: OrderedDict[str, str] = OrderedDict()
    for line in payload.decode("ascii").splitlines():
        name, separator, value = line.partition("=")
        if separator != "=" or not name or not value or name in values:
            raise AssertionError("candidate manifest is not canonical")
        values[name] = value
    return values


class CandidateTests(unittest.TestCase):
    def test_generation164_is_current_bound_and_has_no_authority(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT.read_text(encoding="ascii").splitlines()
        )
        self.assertEqual(fields["profile"], CURRENT_PROFILE)
        self.assertEqual(fields["status"], "offline")
        self.assertEqual(fields["authority"], "none")
        self.assertEqual(fields["phone_boot"], "forbidden")
        self.assertEqual(fields["rescue_slot"], "a")
        self.assertEqual(fields["accepted_generation"], "163")
        self.assertEqual(
            fields["layout_sha256"],
            "6b64b3ca5e58a270c1afd358b5a6fd59793e2b331c73a7fe62b58ef5bbe3440f",
        )
        self.assertEqual(
            fields["image_sha256"],
            "d9a500dd7285b6f7789df89c8da0735f75bb04ee893808bb4f59de1e9e46fdf1",
        )

    def test_generation164_admission_and_claim_are_exact(self) -> None:
        self.assertEqual(digest(CURRENT), CURRENT_MANIFEST_SHA256)
        lines = POLICY.read_text(encoding="ascii").splitlines()
        self.assertEqual(len(lines), 6)
        fields = next(
            line.split("\t")
            for line in lines[1:]
            if line.startswith(CURRENT_PROFILE + "\t")
        )
        self.assertEqual(
            fields[:6],
            [
                CURRENT_PROFILE,
                "allow",
                CURRENT_MANIFEST_SHA256,
                "build/storage-preflight-current-generation164-20260825-r1/"
                "repack/stable-recovery-a.avb.img",
                "100663296",
                "d9a500dd7285b6f7789df89c8da0735f75bb04ee893808bb4f59de1e9e46fdf1",
            ],
        )
        self.assertIn("no mounts, writes, GPT operations", fields[6])
        self.assertIn("never flash or retry after entry", fields[6])
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={CURRENT_PROFILE}\n"
            "candidate=storage-preflight-current\n"
            f"manifest_sha256={CURRENT_MANIFEST_SHA256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        self.assertEqual(CLAIMS.expected_record(CURRENT_PROFILE), expected_claim)

    def test_consumed_manifest_remains_exact(self) -> None:
        values = canonical_manifest()
        self.assertEqual(values, EXPECTED)
        self.assertEqual(digest(MANIFEST), MANIFEST_SHA256)

    def test_narrow_policy_and_one_use_claim_are_exact(self) -> None:
        lines = POLICY.read_text(encoding="ascii").splitlines()
        self.assertEqual(
            lines[0],
            "profile\tstatus\tcandidate_manifest_sha256\timage_path\t"
            "image_size\timage_sha256\tbasis",
        )
        self.assertEqual(len(lines), 6)
        fields = next(
            line.split("\t") for line in lines[1:] if line.startswith(PROFILE + "\t")
        )
        self.assertEqual(fields[:6], [
            PROFILE,
            "revoked",
            MANIFEST_SHA256,
            EXPECTED["image_path"],
            EXPECTED["image_size"],
            EXPECTED["image_sha256"],
        ])
        self.assertEqual(
            fields[6],
            "consumed 2026-08-14; failed before recovery USB with intentional "
            "PS_HOLD hard-reset rollback; no storage write observed; never retry",
        )
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={PROFILE}\n"
            "candidate=storage-preflight-v1\n"
            f"manifest_sha256={MANIFEST_SHA256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        self.assertEqual(CLAIMS.expected_record(PROFILE), expected_claim)

    def test_generation72_candidate_policy_sources_and_claim_are_exact(self) -> None:
        values = canonical_manifest(MANIFEST_V2)
        self.assertEqual(values, EXPECTED_V2)
        self.assertEqual(digest(MANIFEST_V2), MANIFEST_V2_SHA256)
        lines = POLICY.read_text(encoding="ascii").splitlines()
        fields = next(
            line.split("\t")
            for line in lines[1:]
            if line.startswith(PROFILE_V2 + "\t")
        )
        self.assertEqual(
            fields[:6],
            [
                PROFILE_V2,
                "revoked",
                MANIFEST_V2_SHA256,
                values["image_path"],
                values["image_size"],
                values["image_sha256"],
            ],
        )
        self.assertEqual(
            fields[6],
            "consumed 2026-08-15; recovery ACM enumerated but its first frame "
            "was rejected as malformed; exact Alpine fallback and PS_HOLD "
            "hard-reset rollback returned with no watchdog or fatal signature; "
            "no storage write observed; never retry",
        )
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={PROFILE_V2}\n"
            "candidate=storage-preflight-v2\n"
            f"manifest_sha256={MANIFEST_V2_SHA256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        self.assertEqual(CLAIMS.expected_record(PROFILE_V2), expected_claim)

    def test_generation72_local_twin_artifact_when_present(self) -> None:
        values = canonical_manifest(MANIFEST_V2)
        image = REPO / values["image_path"]
        if not image.exists():
            self.skipTest("ignored Generation 72 twin artifact is not present")
        root = image.parents[1]
        paths = {
            "image_sha256": image,
            "raw_sha256": root / "repack/stable-recovery-a.raw.img",
            "kernel_sha256": root
            / "wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
            "wrapper_config_sha256": root / "wrapper-a/asus-kexec-stage/.config",
            "initramfs_sha256": root
            / "wrapper-a/rog5-kexec-stage-initramfs.cpio.gz",
        }
        self.assertEqual(image.stat().st_size, int(values["image_size"]))
        for name, path in paths.items():
            with self.subTest(name=name):
                self.assertEqual(digest(path), values[name])
        self.assertEqual(
            image.read_bytes(),
            (root / "repack/stable-recovery-b.avb.img").read_bytes(),
        )

    def test_generation73_candidate_policy_sources_and_claim_are_exact(self) -> None:
        values = canonical_manifest(MANIFEST_V3)
        self.assertEqual(values, EXPECTED_V3)
        self.assertEqual(digest(MANIFEST_V3), MANIFEST_V3_SHA256)
        fields = next(
            line.split("\t")
            for line in POLICY.read_text(encoding="ascii").splitlines()[1:]
            if line.startswith(PROFILE_V3 + "\t")
        )
        self.assertEqual(
            fields[:6],
            [
                PROFILE_V3,
                "revoked",
                MANIFEST_V3_SHA256,
                values["image_path"],
                values["image_size"],
                values["image_sha256"],
            ],
        )
        self.assertIn("consumed 2026-08-15", fields[6])
        self.assertIn("journal-pending userdata", fields[6])
        self.assertIn("no storage mount or write", fields[6])
        self.assertIn("never retry", fields[6])
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={PROFILE_V3}\n"
            "candidate=storage-preflight-v3\n"
            f"manifest_sha256={MANIFEST_V3_SHA256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        self.assertEqual(CLAIMS.expected_record(PROFILE_V3), expected_claim)

    def test_generation73_local_twin_artifact_when_present(self) -> None:
        values = canonical_manifest(MANIFEST_V3)
        image = REPO / values["image_path"]
        if not image.exists():
            self.skipTest("ignored Generation 73 twin artifact is not present")
        root = image.parents[1]
        paths = {
            "image_sha256": image,
            "raw_sha256": root / "repack/stable-recovery-a.raw.img",
            "kernel_sha256": root
            / "wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
            "wrapper_config_sha256": root / "wrapper-a/asus-kexec-stage/.config",
            "initramfs_sha256": root
            / "wrapper-a/rog5-kexec-stage-initramfs.cpio.gz",
        }
        self.assertEqual(image.stat().st_size, int(values["image_size"]))
        for name, path in paths.items():
            with self.subTest(name=name):
                self.assertEqual(digest(path), values[name])
        self.assertEqual(
            image.read_bytes(),
            (root / "repack/stable-recovery-b.avb.img").read_bytes(),
        )

    def test_generation74_candidate_policy_sources_and_claim_are_exact(self) -> None:
        values = canonical_manifest(MANIFEST_V4)
        self.assertEqual(values, EXPECTED_V4)
        self.assertEqual(digest(MANIFEST_V4), MANIFEST_V4_SHA256)
        fields = next(
            line.split("\t")
            for line in POLICY.read_text(encoding="ascii").splitlines()[1:]
            if line.startswith(PROFILE_V4 + "\t")
        )
        self.assertEqual(
            fields[:6],
            [
                PROFILE_V4,
                "revoked",
                MANIFEST_V4_SHA256,
                values["image_path"],
                values["image_size"],
                values["image_sha256"],
            ],
        )
        self.assertEqual(
            fields[6],
            "consumed 2026-08-15; target repeatedly emitted exact PASS with "
            "UFS, GPT, ext4, minimum 11698467 blocks, and no mounts or writes; "
            "admitted collector rejected the aggregate persistent-frame burst "
            "before line splitting; exact Alpine fallback and PS_HOLD "
            "hard-reset returned without watchdog signal; never retry",
        )
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={PROFILE_V4}\n"
            "candidate=storage-preflight-v4\n"
            f"manifest_sha256={MANIFEST_V4_SHA256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        self.assertEqual(CLAIMS.expected_record(PROFILE_V4), expected_claim)

    def test_generation74_local_twin_artifact_when_present(self) -> None:
        values = canonical_manifest(MANIFEST_V4)
        image = REPO / values["image_path"]
        if not image.exists():
            self.skipTest("ignored Generation 74 twin artifact is not present")
        root = image.parents[1]
        paths = {
            "image_sha256": image,
            "raw_sha256": root / "repack/stable-recovery-a.raw.img",
            "kernel_sha256": root
            / "wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
            "wrapper_config_sha256": root / "wrapper-a/asus-kexec-stage/.config",
            "initramfs_sha256": root
            / "wrapper-a/rog5-kexec-stage-initramfs.cpio.gz",
        }
        self.assertEqual(image.stat().st_size, int(values["image_size"]))
        for name, path in paths.items():
            with self.subTest(name=name):
                self.assertEqual(digest(path), values[name])
        self.assertEqual(
            image.read_bytes(),
            (root / "repack/stable-recovery-b.avb.img").read_bytes(),
        )

    def test_local_clean_twin_artifact_when_present(self) -> None:
        values = canonical_manifest()
        image = REPO / values["image_path"]
        if not image.exists():
            self.skipTest("ignored clean-twin artifact is not present")
        root = image.parents[1]
        paths = {
            "image_sha256": image,
            "raw_sha256": root / "repack/stable-recovery-a.raw.img",
            "kernel_sha256": root
            / "wrapper-a/asus-kexec-stage/arch/arm64/boot/Image",
            "wrapper_config_sha256": root
            / "wrapper-a/asus-kexec-stage/.config",
            "initramfs_sha256": root
            / "wrapper-a/rog5-kexec-stage-initramfs.cpio.gz",
        }
        self.assertEqual(image.stat().st_size, int(values["image_size"]))
        for name, path in paths.items():
            with self.subTest(name=name):
                self.assertEqual(digest(path), values[name])
        self.assertEqual(
            image.read_bytes(),
            (root / "repack/stable-recovery-b.avb.img").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
