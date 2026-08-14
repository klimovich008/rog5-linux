#!/usr/bin/env python3
"""Irreversibly enter one repository-owned exact temporary-boot claim."""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import sys


# This is the repository-owned lookup. A caller selects a reviewed identifier;
# it cannot supply a pathname, candidate, manifest, or expected record bytes.
CLAIMS = {
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
    "headless-diagnostic-generation11-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-generation11-live-v1\n"
        b"candidate=headless-netroot-early-diag-v1\n"
        b"manifest_sha256="
        b"4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-generation12-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-generation12-live-v1\n"
        b"candidate=headless-netroot-early-diag-v1\n"
        b"manifest_sha256="
        b"4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v2": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v3": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v3\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v4": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v4\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v5": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v5\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v6": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v6\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v7": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v7\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v8": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v8\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v9": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v9\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v10": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v10\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-execution-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v3-observer-v1\n"
        b"cycle_sha256="
        b"d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        b"claim_role=execution\n"
        b"recovery_profile=retention-host-rendezvous-v3-execution-v1\n"
        b"recovery_sha256="
        b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
        b"peer_recovery_sha256="
        b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v3-observer-v1\n"
        b"cycle_sha256="
        b"d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        b"claim_role=observer\n"
        b"recovery_profile=retention-host-rendezvous-v3-observer-v1\n"
        b"recovery_sha256="
        b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
        b"peer_recovery_sha256="
        b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
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
    "retention-host-rendezvous-v11-mainline-udc-execution-v2": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"cycle_sha256="
        b"c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        b"claim_role=execution\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v11-mainline-udc-execution-v2\n"
        b"recovery_sha256="
        b"2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb\n"
        b"peer_recovery_sha256="
        b"c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v11-mainline-udc-observer-v2": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"cycle_sha256="
        b"c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"recovery_sha256="
        b"c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e\n"
        b"peer_recovery_sha256="
        b"2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v12-nfs-xattr-execution-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"cycle_sha256="
        b"e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        b"claim_role=execution\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v12-nfs-xattr-execution-v1\n"
        b"recovery_sha256="
        b"f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2\n"
        b"peer_recovery_sha256="
        b"9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v12-nfs-xattr-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"cycle_sha256="
        b"e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"recovery_sha256="
        b"9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69\n"
        b"peer_recovery_sha256="
        b"f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        b"state=BOOT_CLAIMED\n"
    ),
}


class ClaimError(RuntimeError):
    """The durable claim cannot be safely entered."""


def fail(message: str) -> None:
    raise ClaimError(message)


def expected_record(profile: str) -> bytes:
    try:
        return CLAIMS[profile]
    except KeyError as error:
        raise ClaimError("claim profile is not repository-owned") from error


def canonical_claim_root() -> Path:
    account_home = Path(pwd.getpwuid(os.geteuid()).pw_dir)
    if not account_home.is_absolute():
        fail("lifecycle account home must be absolute")
    try:
        account_home = account_home.resolve(strict=True)
    except OSError as error:
        raise ClaimError("lifecycle account home is unsafe or absent") from error
    return account_home / ".local/state/rog5-temporary-boot-consumption"


def canonical_claim_anchor() -> Path:
    try:
        return Path(pwd.getpwuid(os.geteuid()).pw_dir).resolve(strict=True)
    except OSError as error:
        raise ClaimError("lifecycle claim anchor is unsafe or absent") from error


def anchor_parent_is_replace_protected(
    parent_fd: int,
    metadata: os.stat_result,
) -> bool:
    if metadata.st_uid == os.geteuid():
        return False
    mode = stat.S_IMODE(metadata.st_mode)
    groups = {os.getegid(), *os.getgroups()}
    if metadata.st_gid in groups:
        mode_protected = not mode & stat.S_IWGRP
    else:
        mode_protected = not mode & stat.S_IWOTH
    return mode_protected and not os.access(
        f"/proc/self/fd/{parent_fd}",
        os.W_OK,
        effective_ids=True,
    )


def open_claim_anchor(anchor: Path) -> tuple[int, int]:
    if not anchor.is_absolute():
        fail("lifecycle claim anchor must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    parent = anchor.parent
    if parent == anchor:
        fail("lifecycle claim anchor parent is unsafe")
    try:
        parent_fd = os.open(parent, flags | nofollow)
    except OSError as error:
        raise ClaimError("lifecycle claim anchor parent is unsafe") from error
    try:
        parent_metadata = os.fstat(parent_fd)
        opened_parent = Path(f"/proc/self/fd/{parent_fd}").resolve(strict=True)
        if (
            opened_parent != parent
            or not stat.S_ISDIR(parent_metadata.st_mode)
            or not anchor_parent_is_replace_protected(
                parent_fd,
                parent_metadata,
            )
        ):
            fail("lifecycle claim anchor parent is replaceable")
        anchor_fd = os.open(anchor.name, flags | nofollow, dir_fd=parent_fd)
        metadata = os.fstat(anchor_fd)
        opened_path = Path(f"/proc/self/fd/{anchor_fd}").resolve(strict=True)
        if (
            opened_path != anchor
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            fail("lifecycle claim anchor is unsafe or absent")
    except (ClaimError, OSError):
        if "anchor_fd" in locals():
            os.close(anchor_fd)
        os.close(parent_fd)
        raise
    return anchor_fd, parent_fd


def open_claim_root(root: Path) -> int:
    if not root.is_absolute():
        fail("lifecycle claim state root must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(root, flags | nofollow)
    except OSError as error:
        raise ClaimError("lifecycle claim root is unsafe or absent") from error
    try:
        metadata = os.fstat(directory_fd)
        opened_path = Path(f"/proc/self/fd/{directory_fd}").resolve(strict=True)
        if (
            opened_path != root
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            fail("lifecycle claim root is unsafe or absent")
    except (ClaimError, OSError):
        os.close(directory_fd)
        raise
    return directory_fd


def verify_claim_root_path(root: Path, directory_fd: int) -> None:
    opened = os.fstat(directory_fd)
    try:
        current = os.stat(root, follow_symlinks=False)
    except OSError as error:
        raise ClaimError("lifecycle claim root changed during entry") from error
    if (
        current.st_dev != opened.st_dev
        or current.st_ino != opened.st_ino
        or not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.geteuid()
        or stat.S_IMODE(current.st_mode) != 0o700
    ):
        fail("lifecycle claim root changed during entry")


def verify_claim_anchor_path(
    anchor: Path,
    anchor_fd: int,
    parent_fd: int,
) -> None:
    opened = os.fstat(anchor_fd)
    opened_parent = os.fstat(parent_fd)
    try:
        current_parent = os.stat(anchor.parent, follow_symlinks=False)
        current = os.stat(
            anchor.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ClaimError("lifecycle claim anchor changed during entry") from error
    if (
        current_parent.st_dev != opened_parent.st_dev
        or current_parent.st_ino != opened_parent.st_ino
        or not stat.S_ISDIR(current_parent.st_mode)
        or not anchor_parent_is_replace_protected(parent_fd, current_parent)
        or current.st_dev != opened.st_dev
        or current.st_ino != opened.st_ino
        or not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.geteuid()
        or stat.S_IMODE(current.st_mode) & 0o022
    ):
        fail("lifecycle claim anchor changed during entry")


def verify_source_path(
    record_name: str,
    directory_fd: int,
    source_fd: int,
    expected: bytes,
) -> None:
    try:
        named = os.stat(
            record_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ClaimError(
            "source BOOT_CLAIMED record changed during entry"
        ) from error
    opened = os.fstat(source_fd)
    if (
        named.st_dev != opened.st_dev
        or named.st_ino != opened.st_ino
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.geteuid()
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
    ):
        fail("source BOOT_CLAIMED record changed during entry")
    os.lseek(source_fd, 0, os.SEEK_SET)
    content = os.read(source_fd, len(expected) + 1)
    if content != expected or os.read(source_fd, 1):
        fail("source BOOT_CLAIMED record changed during entry")


def existing_guard_is_exact(
    guard_name: str,
    anchor_fd: int,
    expected: bytes,
) -> bool:
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        guard_fd = os.open(guard_name, flags | nofollow, dir_fd=anchor_fd)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ClaimError("global BOOT_CLAIMED guard is unsafe") from error
    try:
        opened = os.fstat(guard_fd)
        named = os.stat(guard_name, dir_fd=anchor_fd, follow_symlinks=False)
        content = os.read(guard_fd, len(expected) + 1)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or content != expected
            or os.read(guard_fd, 1)
        ):
            fail("global BOOT_CLAIMED guard is unsafe")
    finally:
        os.close(guard_fd)
    return True


def create_entered_record(
    entered_name: str,
    directory_fd: int,
    expected: bytes,
) -> int:
    flags = os.O_RDWR | os.O_CLOEXEC | os.O_CREAT | os.O_EXCL
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        entered_fd = os.open(
            entered_name,
            flags | nofollow,
            0o600,
            dir_fd=directory_fd,
        )
    except FileExistsError as error:
        raise ClaimError(
            "durable BOOT_CLAIMED record is already entered"
        ) from error
    except OSError as error:
        raise ClaimError("cannot enter durable BOOT_CLAIMED record") from error
    try:
        os.fchmod(entered_fd, 0o600)
        remaining = memoryview(expected)
        while remaining:
            written = os.write(entered_fd, remaining)
            if written <= 0:
                fail("cannot write entered BOOT_CLAIMED record")
            remaining = remaining[written:]
        os.fsync(entered_fd)
        os.lseek(entered_fd, 0, os.SEEK_SET)
        metadata = os.fstat(entered_fd)
        content = os.read(entered_fd, len(expected) + 1)
        named = os.stat(
            entered_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or named.st_dev != metadata.st_dev
            or named.st_ino != metadata.st_ino
            or content != expected
            or os.read(entered_fd, 1)
        ):
            fail("entered BOOT_CLAIMED record is not exact")
    except Exception:
        os.close(entered_fd)
        raise
    return entered_fd


def verify_entered_file(
    name: str,
    directory_fd: int,
    expected: bytes,
    label: str,
) -> None:
    flags = os.O_RDONLY | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ClaimError(f"{label} is unsafe or absent") from error
    try:
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        content = os.read(descriptor, len(expected) + 1)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or content != expected
            or os.read(descriptor, 1)
        ):
            fail(f"{label} is not exact")
    finally:
        os.close(descriptor)


def verify_entered(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
        anchor = canonical_claim_anchor()
    else:
        anchor = root.parent
    guard_name = f".rog5-temporary-boot-consumption.{profile}.entered"
    anchor_fd, anchor_parent_fd = open_claim_anchor(anchor)
    try:
        directory_fd = open_claim_root(root)
    except Exception:
        os.close(anchor_fd)
        os.close(anchor_parent_fd)
        raise
    try:
        try:
            os.stat(record_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ClaimError("source BOOT_CLAIMED record is unsafe") from error
        else:
            fail("source BOOT_CLAIMED record still exists")
        verify_entered_file(
            entered_name,
            directory_fd,
            expected,
            "entered BOOT_CLAIMED record",
        )
        if not existing_guard_is_exact(guard_name, anchor_fd, expected):
            fail("global BOOT_CLAIMED guard is absent")
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
    finally:
        os.close(directory_fd)
        os.close(anchor_fd)
        os.close(anchor_parent_fd)


def consume(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
        anchor = canonical_claim_anchor()
    else:
        anchor = root.parent
    guard_name = f".rog5-temporary-boot-consumption.{profile}.entered"
    anchor_fd, anchor_parent_fd = open_claim_anchor(anchor)
    try:
        directory_fd = open_claim_root(root)
    except Exception:
        os.close(anchor_fd)
        os.close(anchor_parent_fd)
        raise
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    source_fd = -1
    entered_fd = -1
    guard_fd = -1
    try:
        if existing_guard_is_exact(guard_name, anchor_fd, expected):
            fail("durable BOOT_CLAIMED record is already entered")

        try:
            os.stat(entered_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ClaimError("entered BOOT_CLAIMED record is unsafe") from error
        else:
            fail("durable BOOT_CLAIMED record is already entered")

        try:
            source_fd = os.open(
                record_name,
                flags | nofollow,
                dir_fd=directory_fd,
            )
        except OSError as error:
            raise ClaimError(
                "durable BOOT_CLAIMED record is unsafe or absent"
            ) from error
        metadata = os.fstat(source_fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            fail("durable BOOT_CLAIMED record is unsafe or absent")
        content = os.read(source_fd, len(expected) + 1)
        if content != expected or os.read(source_fd, 1):
            fail("durable BOOT_CLAIMED record is not exact")

        verify_source_path(record_name, directory_fd, source_fd, expected)
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
        guard_fd = create_entered_record(
            guard_name,
            anchor_fd,
            expected,
        )
        os.fsync(anchor_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
        entered_fd = create_entered_record(
            entered_name,
            directory_fd,
            expected,
        )
        os.fsync(directory_fd)

        verify_source_path(
            record_name,
            directory_fd,
            source_fd,
            expected,
        )
        try:
            os.unlink(record_name, dir_fd=directory_fd)
        except OSError as error:
            raise ClaimError(
                "durable BOOT_CLAIMED record entered but source cleanup failed"
            ) from error
        if os.fstat(source_fd).st_nlink != 0:
            fail("source BOOT_CLAIMED record changed during entry")
        os.fsync(directory_fd)
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
    finally:
        if entered_fd >= 0:
            os.close(entered_fd)
        if guard_fd >= 0:
            os.close(guard_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)
        os.close(anchor_fd)
        os.close(anchor_parent_fd)


def main() -> int:
    if len(sys.argv) == 2:
        profile = sys.argv[1]
        consume(profile)
        print(f"PASS exact durable BOOT_CLAIMED record entered: {profile}")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-entered":
        profile = sys.argv[2]
        verify_entered(profile)
        print(f"PASS exact durable BOOT_CLAIMED record verified: {profile}")
        return 0
    fail(
        "exact-record claim consumer requires a repository-owned profile "
        "or --verify-entered PROFILE"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClaimError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
