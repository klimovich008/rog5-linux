#!/usr/bin/env python3
"""Exact-source and optional local-artifact checks for Generation 71."""

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
POLICY = REPO / "manifests/storage-preflight-temporary-boot-v1.tsv"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
PROFILE = "storage-preflight-v1-generation71-live-v1"
MANIFEST_SHA256 = "a14872f8ca4db705015586f4e199e5bdf607f947f96949eecd35e42a137d19c5"

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


def canonical_manifest() -> OrderedDict[str, str]:
    metadata = MANIFEST.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o022:
        raise AssertionError("candidate manifest metadata is unsafe")
    payload = MANIFEST.read_bytes()
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
    def test_manifest_and_repository_sources_are_exact(self) -> None:
        values = canonical_manifest()
        self.assertEqual(values, EXPECTED)
        self.assertEqual(digest(MANIFEST), MANIFEST_SHA256)
        self.assertEqual(
            digest(REPO / "initramfs/recovery-init"),
            values["recovery_init_sha256"],
        )
        self.assertEqual(
            digest(REPO / "scripts/host/collect-storage-preflight-report.py"),
            values["collector_sha256"],
        )
        self.assertEqual(
            digest(REPO / "configs/storage/rog5-dedicated-linux-v1.json"),
            values["layout_sha256"],
        )

    def test_narrow_policy_and_one_use_claim_are_exact(self) -> None:
        lines = POLICY.read_text(encoding="ascii").splitlines()
        self.assertEqual(
            lines[0],
            "profile\tstatus\tcandidate_manifest_sha256\timage_path\t"
            "image_size\timage_sha256\tbasis",
        )
        self.assertEqual(len(lines), 2)
        fields = lines[1].split("\t")
        self.assertEqual(fields[:6], [
            PROFILE,
            "allow",
            MANIFEST_SHA256,
            EXPECTED["image_path"],
            EXPECTED["image_size"],
            EXPECTED["image_sha256"],
        ])
        self.assertEqual(
            fields[6],
            "one exact read-only UFS/GPT/ext4 preflight over receive-only ACM; "
            "temporary RAM-only recovery; externally consumed exact claim "
            "required; never flash or retry after entry",
        )
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={PROFILE}\n"
            "candidate=storage-preflight-v1\n"
            f"manifest_sha256={MANIFEST_SHA256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        self.assertEqual(CLAIMS.expected_record(PROFILE), expected_claim)

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
