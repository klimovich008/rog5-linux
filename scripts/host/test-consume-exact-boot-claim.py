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
        "storage-layout-stage1-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-v1-live-v1\n"
            b"candidate=storage-layout-stage1-v1\n"
            b"manifest_sha256="
            b"dda7a22e8473b5cbab07f765e7eb1b6bfb3f5f3868a22398781fe6804a3664a2\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-preflight-v4-generation74-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-preflight-v4-generation74-live-v1\n"
            b"candidate=storage-preflight-v4\n"
            b"manifest_sha256="
            b"4ab1ad92b75b975c887bca9b1f4d2617f0d9267dd1b179bb36a0f37c791bff64\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-preflight-v3-generation73-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-preflight-v3-generation73-live-v1\n"
            b"candidate=storage-preflight-v3\n"
            b"manifest_sha256="
            b"1721186c050eb2c2130492217cb1838782d0c63936183968fef716b62bcce4b6\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-preflight-v2-generation72-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-preflight-v2-generation72-live-v1\n"
            b"candidate=storage-preflight-v2\n"
            b"manifest_sha256="
            b"7a436a3716d56536326040fd626c3dc8b760c2ef94ee2d0695e536d2ee779935\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-preflight-v1-generation71-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-preflight-v1-generation71-live-v1\n"
            b"candidate=storage-preflight-v1\n"
            b"manifest_sha256="
            b"a14872f8ca4db705015586f4e199e5bdf607f947f96949eecd35e42a137d19c5\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-early-ssh-v45-generation70-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-early-ssh-v45-generation70-live-v1\n"
            b"candidate=persistent-root-local-image-early-ssh-v45\n"
            b"manifest_sha256="
            b"f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-early-ssh-v45-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-early-ssh-v45-live-v1\n"
            b"candidate=persistent-root-local-image-early-ssh-v45\n"
            b"manifest_sha256="
            b"f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-ufs-detail-v44-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-ufs-detail-v44-live-v1\n"
            b"candidate=persistent-root-local-image-ufs-detail-v44\n"
            b"manifest_sha256="
            b"07e7f72c7c88ea4c081d77e3e561c36278ef0a0273dee6b831ca691f6518ee2e\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-post-write-v43-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-post-write-v43-live-v1\n"
            b"candidate=persistent-root-local-image-post-write-v43\n"
            b"manifest_sha256="
            b"9a57ef7dab71d782bce1893525129e24bd350ee74f24aeabe4ed033af6500d07\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-write-mountpoint-v42-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-write-mountpoint-v42-live-v1\n"
            b"candidate=persistent-root-local-image-write-mountpoint-v42\n"
            b"manifest_sha256="
            b"8b2e95268be4e5e0c65eb9367514bb93ab2c20f38a3848a0986de4fe4336d221\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-write-contained-v41-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-write-contained-v41-live-v1\n"
            b"candidate=persistent-root-local-image-write-contained-v41\n"
            b"manifest_sha256="
            b"5125eddd0aeeb394eea7f24b427b04c1c001276c5b8b2e9dbf544a49c4af0646\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-write-roclass-v40-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-write-roclass-v40-live-v1\n"
            b"candidate=persistent-root-local-image-write-roclass-v40\n"
            b"manifest_sha256="
            b"c284330d2e37cda85d125c098c6acece877ae5e5b69be66edcae326e57ee0f4b\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-write-window-v39-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-write-window-v39-live-v1\n"
            b"candidate=persistent-root-local-image-write-window-v39\n"
            b"manifest_sha256="
            b"35cdc621f44873e42b1b8f2619e383d1a6ed2236f49790fdf36c7435e7883824\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-write-diag-v38-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-write-diag-v38-live-v1\n"
            b"candidate=persistent-root-local-image-write-diag-v38\n"
            b"manifest_sha256="
            b"a12844274c1bc707cee9ae1f3e464e73ffed57adcd477af8f21fbb678173c444\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-write-v37-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-write-v37-live-v1\n"
            b"candidate=persistent-root-local-image-write-v37\n"
            b"manifest_sha256="
            b"5033263fbdb28f795fe92b74a850d3e33119f2d440f9e3999b3ebff3804ef259\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-ed25519-v36-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-ed25519-v36-live-v1\n"
            b"candidate=persistent-root-local-image-ed25519-v36\n"
            b"manifest_sha256="
            b"cc41176df74def7a8953dfcd8621e1d1ad2457eb98a7822a0d40ce50ab8c2be0\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-volatile-v35-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-volatile-v35-live-v1\n"
            b"candidate=persistent-root-local-image-volatile-v35\n"
            b"manifest_sha256="
            b"1def5f276c7d07668ccb90a9ca3ed966660e0af359e49e2f847371b058291e30\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-loader-v34-repeat-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-loader-v34-repeat-live-v1\n"
            b"candidate=persistent-root-local-image-loader-v34\n"
            b"manifest_sha256="
            b"8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-loader-v34-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-loader-v34-live-v1\n"
            b"candidate=persistent-root-local-image-loader-v34\n"
            b"manifest_sha256="
            b"8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-fast-attest-v33-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-fast-attest-v33-live-v1\n"
            b"candidate=persistent-root-local-image-fast-attest-v33\n"
            b"manifest_sha256="
            b"40b5573a4d03f4571ead025083a7989e6ac9288a89b8fe64e4b8439b64aaa42e\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-local-image-v32-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-local-image-v32-live-v1\n"
            b"candidate=persistent-root-local-image-v32\n"
            b"manifest_sha256="
            b"ae1069eb2f85e1b93c24f831e440a54303ca80934864f7fca07afcf34adfaca1\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-ufs-fast-admission-v31-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-ufs-fast-admission-v31-live-v1\n"
            b"candidate=persistent-root-ufs-fast-admission-v31\n"
            b"manifest_sha256="
            b"3cee4b788a2005e90b4c901955a3b1df392cad8b332ea7252580fe1621af1f89\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-ufs-local-root-stage-v30-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-ufs-local-root-stage-v30-live-v1\n"
            b"candidate=persistent-root-ufs-local-root-stage-v30\n"
            b"manifest_sha256="
            b"53afa65bb7134e7d5acccc2126aa8764fd3918c7cab02c61417f4be1572aad27\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-ufs-local-root-v29-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-ufs-local-root-v29-live-v1\n"
            b"candidate=persistent-root-ufs-local-root-v29\n"
            b"manifest_sha256="
            b"ae22914906d63accc893157b51c683f24a3a7e933bba84e13661e664764b9cc6\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-ufs-readonly-enumeration-v28-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-ufs-readonly-enumeration-v28-live-v1\n"
            b"candidate=persistent-root-ufs-readonly-enumeration-v28\n"
            b"manifest_sha256="
            b"9ea343f70b9dfa3658a13d4b1e4dfd2cb841881ec21ce0444cd4422899434045\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1\n"
            b"candidate=persistent-root-qmp-ufs-phy-provider-stage-v27\n"
            b"manifest_sha256="
            b"734bd5af4c2f7db1af87e08d0a6c1de0e6d0b013be4901110b892fd065e7656c\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1\n"
            b"candidate=persistent-root-qmp-ufs-phy-creation-stage-v26\n"
            b"manifest_sha256="
            b"7f05c55c553e057b418f2adc23f284a907dd9ca693d532228372ad9dfe3e57c4\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1\n"
            b"candidate=persistent-root-qmp-clock-provider-cleanup-stage-v25\n"
            b"manifest_sha256="
            b"14f9b93e9951d664e036ef189526bef59a167572dd7a23c052ba56aed9fd44cf\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1\n"
            b"candidate=persistent-root-qmp-clock-provider-cleanup-stage-v24\n"
            b"manifest_sha256="
            b"1bc07a9e0b0acf874f542a84f1d7d8c12505504790bc4da433eb22989b76839b\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1\n"
            b"candidate=persistent-root-qmp-third-clock-runtime-pm-stage-v23\n"
            b"manifest_sha256="
            b"6d8195d2e384558b9ff79a42966fd6841837b38d4b41e83dd745bf554be14dc6\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1\n"
            b"candidate=persistent-root-qmp-second-clock-runtime-pm-stage-v22\n"
            b"manifest_sha256="
            b"052d462cbd7820de331c446598f69224128eced8175665acd703428efb75b371\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1\n"
            b"candidate=persistent-root-qmp-first-clock-runtime-pm-stage-v21\n"
            b"manifest_sha256="
            b"782756493f38d5ea9a634678043214926e9b49ef1ca01ce35e9e41e37169fd4b\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-first-clock-name-stage-v20-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-first-clock-name-stage-v20-live-v1\n"
            b"candidate=persistent-root-qmp-first-clock-name-stage-v20\n"
            b"manifest_sha256="
            b"86c8262c080b0b7254a9175bc8487f464db7a4304ba7879b450a74504a23f713\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-allocation-stage-v19-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-allocation-stage-v19-live-v1\n"
            b"candidate=persistent-root-qmp-allocation-stage-v19\n"
            b"manifest_sha256="
            b"82f38e524cc9f8c65bd5ae225bbb4d0acf4a7ef20021d61af313880c98731835\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-first-fixed-clock-stage-v18-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-first-fixed-clock-stage-v18-live-v1\n"
            b"candidate=persistent-root-qmp-first-fixed-clock-stage-v18\n"
            b"manifest_sha256="
            b"f047d1c0ca676afa62a8a4f30d7b68306622b2eee5fc8dfb8b94e9d71450d3c5\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-fixed-clocks-stage-v17-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-fixed-clocks-stage-v17-live-v1\n"
            b"candidate=persistent-root-qmp-fixed-clocks-stage-v17\n"
            b"manifest_sha256="
            b"abd615f73576c798505464c07a3816da470eee5eeb9c26bc2f8f201f85b44ba4\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-clock-provider-stage-v16-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-clock-provider-stage-v16-live-v1\n"
            b"candidate=persistent-root-qmp-clock-provider-stage-v16\n"
            b"manifest_sha256="
            b"dd832a7655e4a1130b69f07188907f80853004f5e05c150e827a0aee4e1c6447\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-mmio-stage-v15-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-mmio-stage-v15-live-v1\n"
            b"candidate=persistent-root-qmp-mmio-stage-v15\n"
            b"manifest_sha256="
            b"d81ff27520337a91e556018109173d4d14d9c38d0846639f2d056150fa39886d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-regulator-stage-v14-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-regulator-stage-v14-live-v1\n"
            b"candidate=persistent-root-qmp-regulator-stage-v14\n"
            b"manifest_sha256="
            b"03e49b58a082826c1d88ab328c82d6c903c9130e56522fb645eaa3be31eb69a7\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-module-load-control-v13-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-module-load-control-v13-live-v1\n"
            b"candidate=persistent-root-qmp-module-load-control-v13\n"
            b"manifest_sha256="
            b"30fb6c355aa8e34097592cf4b33fe7ae4c4193a4c85ae36744c90778f1818cb7\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-qmp-ufs-phy-control-v12-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-qmp-ufs-phy-control-v12-live-v1\n"
            b"candidate=persistent-root-qmp-ufs-phy-control-v12\n"
            b"manifest_sha256="
            b"330f33a533f8f65e1d32b9e9c90bce10b4301983d7dced88fddfcd8f49e9f294\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-deferred-qmp-ufs-v11-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-deferred-qmp-ufs-v11-live-v1\n"
            b"candidate=persistent-root-deferred-qmp-ufs-v11\n"
            b"manifest_sha256="
            b"e40da74acb705843b0f29c485ca922209e44073f7baab144cbac17c5b285500e\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-deferred-ufs-v10-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-deferred-ufs-v10-live-v1\n"
            b"candidate=persistent-root-deferred-ufs-v10\n"
            b"manifest_sha256="
            b"dc22fde250d88f75859d544737d3703f9a3cf09ca2987eaf213dd744204cd8f7\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-accepted-image-v9-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-accepted-image-v9-live-v1\n"
            b"candidate=persistent-root-accepted-image-v9\n"
            b"manifest_sha256="
            b"90c3cd03ab749003d46f039b31d6bffd51b98d2ea18e858eaddf59cb64c0efbd\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-image-control-v8-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-image-control-v8-live-v1\n"
            b"candidate=persistent-root-image-control-v8\n"
            b"manifest_sha256="
            b"c3cab07c75012941b103a9100e69298ef69de7aa4d73893d6d02ea4602f66f56\n"
            b"state=BOOT_CLAIMED\n"
        ),
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
