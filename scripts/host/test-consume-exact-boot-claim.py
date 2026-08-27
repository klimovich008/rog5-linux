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
        "stock-charging-memory-fixed-v4-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=stock-charging-memory-fixed-v4-live-v1\n"
            b"candidate=stock-charging-memory-fixed-v4\n"
            b"manifest_sha256="
            b"5b3323d2259160e37c74d2f5b9e972ca6aa5a62d0b596d604b592e7c720313a1\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "stock-charging-memory-fixed-v3-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=stock-charging-memory-fixed-v3-live-v1\n"
            b"candidate=stock-charging-memory-fixed-v3\n"
            b"manifest_sha256="
            b"67ec60a2acf4b600491dfd58d86bea1bf1efeeb3e14914fe0c0452cb1d4caa06\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "stock-charging-explicit-dtb-v2-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=stock-charging-explicit-dtb-v2-live-v1\n"
            b"candidate=stock-charging-explicit-dtb-v2\n"
            b"manifest_sha256="
            b"1df5c41b2a7687bbfd66c201ef9ab164bb77767df41b5cc7c1c05f0b6de03fdf\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "charging-direct-stock-storage-isolated-v3-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=charging-direct-stock-storage-isolated-v3-live-v1\n"
            b"candidate=charging-direct-stock-storage-isolated-v3\n"
            b"manifest_sha256="
            b"713314d66035b37ae4111c1270a39bf2def66afbe41a93029c088856eafdfedb\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "stock-charging-recovery-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=stock-charging-recovery-v1-live-v1\n"
            b"candidate=stock-charging-recovery-v1\n"
            b"manifest_sha256="
            b"3e15b8a23b440d1e58bf05592df7d4e40fb8401d6c80c74ae47e7c93043233b5\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "official-ww33-charging-rescue-v2-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=official-ww33-charging-rescue-v2-live-v1\n"
            b"candidate=official-ww33-charging-rescue-v2\n"
            b"manifest_sha256="
            b"0d3cca84453b17409fefbbda650f5a46836bb0d3b9e105b0581b37f9d7e2011f\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "charging-hybrid-asus-recovery-v2-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=charging-hybrid-asus-recovery-v2-live-v1\n"
            b"candidate=charging-hybrid-asus-recovery-v2\n"
            b"manifest_sha256="
            b"5b1297a25bb7d42cfb2bcafd27c6cc82524fc90401b76d20eef1a48654c58a9f\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "charging-hybrid-asus-recovery-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=charging-hybrid-asus-recovery-v1-live-v1\n"
            b"candidate=charging-hybrid-asus-recovery-v1\n"
            b"manifest_sha256="
            b"07b7754c20f80e573d007f909543a8bd4e61262b89f937f4a39e85624b02638e\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "charging-telemetry-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=charging-telemetry-v1-live-v1\n"
            b"candidate=charging-telemetry-v1\n"
            b"manifest_sha256="
            b"1cfffb18008c07099e2950689043572806bec9318700e95375adc97e2792a800\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "charging-rescue-fastboot-v2-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=charging-rescue-fastboot-v2-live-v1\n"
            b"candidate=charging-rescue-fastboot-v2\n"
            b"manifest_sha256="
            b"95d80165ebf94d6ec6db3a812d8438bb88215254b4292d6f0a8b031f5785fa6f\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "charging-rescue-fastboot-v1-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=charging-rescue-fastboot-v1-live-v1\n"
            b"candidate=charging-rescue-fastboot-v1\n"
            b"manifest_sha256="
            b"1b770a941fa8f4fa11dc7100ddd2313795c5256bab1269db4b7520cc87b62e0d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "userdata-ext4-reset-generation99-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=userdata-ext4-reset-generation99-live-v1\n"
            b"candidate=userdata-ext4-reset-generation99\n"
            b"manifest_sha256="
            b"121adc0df0d2a395685983c573fe37ca25da8a31497c2cf9843e9372ab40a3c5\n"
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
        "storage-preflight-current-generation164-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-preflight-current-generation164-live-v1\n"
            b"candidate=storage-preflight-current\n"
            b"manifest_sha256="
            b"8f0f1f5c22231e7c2090299c1b0878b38e09b1839ecaf9cf8cdaf2643e365f6a\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-current-generation165-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-current-generation165-live-v1\n"
            b"candidate=storage-layout-stage1-current\n"
            b"manifest_sha256="
            b"7e3bb797375f5b3a38a4bf76bb57f2a51e344b36a9613e0f25cf2e6c97862215\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-current-generation166-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-current-generation166-live-v1\n"
            b"candidate=storage-layout-stage1-current\n"
            b"manifest_sha256="
            b"cc348a62688135492e36e02604b7a197b081cc671e0c65f48969015414963d88\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-load-backup-generation167-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-load-backup-generation167-live-v1\n"
            b"candidate=storage-layout-stage1-load-backup\n"
            b"manifest_sha256="
            b"f9df41fb58858b9eeed9528650f1461d0a71bd2bb0bd8dd926f740ad65954ccf\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-load-backup-generation168-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-load-backup-generation168-live-v1\n"
            b"candidate=storage-layout-stage1-load-backup\n"
            b"manifest_sha256="
            b"902890bd36b067fd7a262fd71334f418766777b3c8beb47711776b251878c9ea\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-prewrite-observer-generation169-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-prewrite-observer-generation169-live-v1\n"
            b"candidate=storage-layout-stage1-prewrite-observer\n"
            b"manifest_sha256="
            b"c129243271b42c6efb38e3248d5a2ba58b11346720f8c188250efa5f8482e207\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-prewrite-observer-generation170-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-prewrite-observer-generation170-live-v1\n"
            b"candidate=storage-layout-stage1-prewrite-observer\n"
            b"manifest_sha256="
            b"74aaa7c64929f33d1758853c0a191d6e9104f97f7f81e3d13c32095c319c9553\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-config-diag-generation171-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-config-diag-generation171-live-v1\n"
            b"candidate=storage-layout-stage1-config-diag\n"
            b"manifest_sha256="
            b"acee0a4e68fdc3e5e0dd60618719bb25e6a28f2afff602d1f329fead3a6d0b64\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-production-generation172-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-production-generation172-live-v1\n"
            b"candidate=storage-layout-stage1-production\n"
            b"manifest_sha256="
            b"8df8f0152e66180f368c55f31e9b788ea3d120ce87117d3386ef2cd7f46fead0\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-production-generation173-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-production-generation173-live-v1\n"
            b"candidate=storage-layout-stage1-production\n"
            b"manifest_sha256="
            b"09895a561a5086542463ba3fce4ecd4daf632fd8bb311e425ac385060cea3754\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-production-generation174-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-production-generation174-live-v1\n"
            b"candidate=storage-layout-stage1-production\n"
            b"manifest_sha256="
            b"e259fda8dcba14b5cfd1e53adc1dfa2e1782b548f6c7980fde994d9d1412d780\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage1-production-generation175-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage1-production-generation175-live-v1\n"
            b"candidate=storage-layout-stage1-production\n"
            b"manifest_sha256="
            b"7dc95a58248ba2613f09da8a032449e8a8e2f0b635aee66445fd518f4494ae4f\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation176-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation176-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"3ee8244a6ccef26f594cf4aceecb2efc1e27b731fa7bdfc03917602def1b9f8d\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation177-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation177-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"8764447295144136ef58f759ca2f118da36025a49bdc2e13c918cd2a97a48381\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation178-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation178-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"5d2a7541fc708a76e19afa2252460f12c9cceb5d766a9f35af07b172b9379d85\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation179-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation179-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"707cae20d3ed363599fbae4174a0081485f26ca213decd4b52a39f24b61dbaaa\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation180-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation180-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"827e5b67f6e2c876af21fbc01c79ee79025f03a59d21639e25df3d8cf0b305a4\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation181-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation181-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"ba2fa54f3e343e3e0a7921281ab5f0f7219723deb6c0b49f687e86f51e272bb8\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation182-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation182-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"35590291bdacb3a8dc198c27a38b8a41333d49d6f72f5c6bb74b6d81bcd65747\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation183-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation183-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"ab476c8cca14aff156943ff72e6fd2bf702df02b2069f191cedc2c93f757d2ba\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation184-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation184-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"c11a8e0ce53f29188b845fdaa471163319e3c02c2771488f06c3f4ddd25548e6\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation185-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation185-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"39ac9cde4c24d0aefca63ff231113bc4b7a6ab72eaa243d83895ccdb934d2659\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation186-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation186-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"faecb6ded2dea36099195dbb0e611e39a47dfef733ba3f94d9f17bd127a2e345\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation187-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation187-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"b9f01bbc792cc41c054fb3c00e39bf8703ab122f74262a3efae83c444e9b987b\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation188-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation188-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"110480d6a5e39cb887f5b707c09931c0b116206433457e420a5085f60e50dd0c\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation189-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation189-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"995836aa417803d584485bc9f996a1162e97446dab29c3d20b41eb0297475c04\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-preflight-generation190-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-preflight-generation190-live-v1\n"
            b"candidate=storage-layout-stage2-preflight\n"
            b"manifest_sha256="
            b"4d23f203add015b888289c915c8defdf2ed0fb34b39adaa9dcb77fe2e5aa9ed7\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-readonly-v1-generation191-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-readonly-v1-generation191-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-readonly-v1\n"
            b"manifest_sha256="
            b"75c44d8d069dd79e448fd546aaa3cabb60fa9fada04e8f4310f9d2d04f490e65\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-readonly-v2-generation192-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-readonly-v2-generation192-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-readonly-v2\n"
            b"manifest_sha256="
            b"c2b05bfbebb23a8936a54678ce68954a4634d4d966dbc02afe08f253a13058af\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-readonly-v3-generation193-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-readonly-v3-generation193-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-readonly-v3\n"
            b"manifest_sha256="
            b"1384d198998f3a055487c747b38f59f0abcfb452049d7b77879f9e0cf1e0380a\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-clone-v1-generation194-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-clone-v1-generation194-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-clone-v1\n"
            b"manifest_sha256="
            b"115fc705b9e3eb396ba75760ca0db4bae663ccc95fadc1ead21b84b874d97f06\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-native-postmortem-v1-generation195-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-native-postmortem-v1-generation195-live-v1\n"
            b"candidate=storage-layout-stage2-native-postmortem-v1\n"
            b"manifest_sha256="
            b"307188a2c6d6630e8f5732d7d0b84e297a6dd171cc687100a4714a565b4303f1\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-clone-v2-generation196-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-clone-v2-generation196-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-clone-v2\n"
            b"manifest_sha256="
            b"cea60920ad773c05cf85ec396461ecdaa49b14d7ea481bf1f5d5e64ef9233cf3\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-clone-v3-generation197-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-clone-v3-generation197-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-clone-v3\n"
            b"manifest_sha256="
            b"dd3455a16c59c61d56d78636c3de94a9230e9d25aa895f36834d9e041dfcd6a3\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-probe-v1-generation198-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-watchdog-probe-v1-generation198-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-probe-v1\n"
            b"manifest_sha256="
            b"a289b401846593d0a6c49250da810c2b2f602596b878f2eb51dcf88ac85afb56\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-mainline-clone-v4-generation199-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-mainline-clone-v4-generation199-live-v1\n"
            b"candidate=storage-layout-stage2-mainline-clone-v4\n"
            b"manifest_sha256="
            b"d941385ab07dfa59142a3ff25eed6329a209b57f58d86157171ed6829e5ce5a3\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-lifetime-v1-generation200-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-watchdog-lifetime-v1-generation200-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-lifetime-v1\n"
            b"manifest_sha256="
            b"8544f57d85d0a75af067fa02ec2747f01a6c0fa6c666b94a5ea0931b61444452\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-lifetime-v2-generation201-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-watchdog-lifetime-v2-generation201-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-lifetime-v2\n"
            b"manifest_sha256="
            b"eaadc07583a675edf398e8d74c73658e3e0783a839fceee3d3510f1a403fe741\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-observer-v1-generation202-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-watchdog-observer-v1-generation202-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-observer-v1\n"
            b"manifest_sha256="
            b"57359d0f1e3a3471c733d79985edca7f271e352fb92cfa81d9fa94b65b76e4d2\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-observer-v2-generation203-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile="
            b"storage-layout-stage2-watchdog-observer-v2-generation203-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-observer-v2\n"
            b"manifest_sha256="
            b"e984aa8be8b6d3ce24071035edfbd63e73b8fc08a32a2b5c31b9e63a9562cdb1\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-mmio-v1-generation204-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-watchdog-mmio-v1-generation204-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-mmio-v1\n"
            b"manifest_sha256=596df1af9bc9a3cc3710be7802559983849f2ef381a38f105414d2df7e0dcaf8\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-mmio-v2-generation205-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-watchdog-mmio-v2-generation205-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-mmio-v2\n"
            b"manifest_sha256=436f32b67473360af215486d275966cc9b3504dfaf9b6e3a704f5ce8a188dcd0\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-watchdog-mmap-v1-generation206-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-watchdog-mmap-v1-generation206-live-v1\n"
            b"candidate=storage-layout-stage2-watchdog-mmap-v1\n"
            b"manifest_sha256=840e40b59cd266f9545773c971f38e85ded0165349b3b61997dcb1f6f5ee7d97\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-softdog-probe-v1-generation207-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-softdog-probe-v1-generation207-live-v1\n"
            b"candidate=storage-layout-stage2-softdog-probe-v1\n"
            b"manifest_sha256=ec5d0890e83589c9b564908a511d266c873e9d7f5a76d7c16b4024e0c5dd8344\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-softdog-clone-v1-generation208-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-softdog-clone-v1-generation208-live-v1\n"
            b"candidate=storage-layout-stage2-softdog-clone-v1\n"
            b"manifest_sha256=8aab1a2c3eb96fc275caf05f7ea1e99f58197f1c13ecd024bac4ed68d2b277c4\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "storage-layout-stage2-softdog-clone-v2-generation209-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=storage-layout-stage2-softdog-clone-v2-generation209-live-v1\n"
            b"candidate=storage-layout-stage2-softdog-clone-v2\n"
            b"manifest_sha256=dd9a427854d7ad9a1b762774b3a7ac859c2710bc0b077a0959a819ade274afd1\n"
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
        "persistent-root-power-usb-v1-generation77-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v1-generation77-live-v1\n"
            b"candidate=persistent-root-power-usb-v1\n"
            b"manifest_sha256="
            b"def5a06936e84c20e8609ae47b3fd8955500bf9c97de724897e52c6b7596d184\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v2-generation78-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v2-generation78-live-v1\n"
            b"candidate=persistent-root-power-usb-v2\n"
            b"manifest_sha256="
            b"ffbdb39dc4c5c959c4214c7987b954f70c63e33ba78305f821ccd07c32fb17a6\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v3-generation79-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v3-generation79-live-v1\n"
            b"candidate=persistent-root-power-usb-v3\n"
            b"manifest_sha256="
            b"d0a1e7b2d9a2fce6d934fc560af466c476f66c1b5ee700dd6efdc6134b6e68eb\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v4-generation80-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v4-generation80-live-v1\n"
            b"candidate=persistent-root-power-usb-v4\n"
            b"manifest_sha256="
            b"2240afeecc90e45e4cf51e94365473a8fbe269731cebc7d1dcba86b7bfd84bf2\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v5-generation81-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v5-generation81-live-v1\n"
            b"candidate=persistent-root-power-usb-v5\n"
            b"manifest_sha256="
            b"5320f9cca8582ca7475f06f0a4c3e25e0b961fd1596077c832e9e622667b19bf\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v6-generation82-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v6-generation82-live-v1\n"
            b"candidate=persistent-root-power-usb-v6\n"
            b"manifest_sha256="
            b"b83d5bacb8b22a7125a33c087b10403cc5e1e9cf35dc5e8ee8d1e48e185e935a\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v7-generation83-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v7-generation83-live-v1\n"
            b"candidate=persistent-root-power-usb-v7\n"
            b"manifest_sha256="
            b"ed43083b35d7f1e4d3c7aa6aa8dacb4ec4e22a2d1e57cd818c4efa20f78080cd\n"
            b"state=BOOT_CLAIMED\n"
        ),
        "persistent-root-power-usb-v8-generation84-live-v1": (
            b"format=rog5-temporary-boot-consumption-v1\n"
            b"recovery_profile=persistent-root-power-usb-v8-generation84-live-v1\n"
            b"candidate=persistent-root-power-usb-v8\n"
            b"manifest_sha256="
            b"c70ed13367192b26225aa3408bf8cdf4dd3a91da1d3a0c0f5fba59c81be36289\n"
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
        "local-image-stage-ncm-v9-generation118-observer-v1": (
            b"format=rog5-retention-boot-consumption-v1\n"
            b"retention_profile=local-image-stage-ncm-v9-generation118-postmortem-v1\n"
            b"cycle_sha256="
            b"5b49c45578d578df82422dba92f21d2adc283e526ce16d00c295dbd21364c8c7\n"
            b"claim_role=observer\n"
            b"recovery_profile="
            b"local-image-stage-ncm-v9-generation118-observer-v1\n"
            b"recovery_sha256="
            b"4fef0b9acd38bf06009db1c26314e6ec910b32a06f251012b4efc2910c13325c\n"
            b"peer_recovery_sha256="
            b"6e1fc8bf8e2c5f65d0e391c6b5275c8dceaf9f1c236d9feee23367a27e4ae1dc\n"
            b"candidate=local-image-stage-ncm-v9\n"
            b"manifest_sha256="
            b"ec657d94aea6a71aa7efab80bcddba7794256209609ddc7031bd37764c17a4b5\n"
            b"state=BOOT_CLAIMED\n"
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
