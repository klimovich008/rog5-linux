#!/usr/bin/env python3
"""Verify an authority-free target/observer retention-cycle review."""

from __future__ import annotations

import ast
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys
import tempfile
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, NamedTuple


REPO = Path(__file__).resolve().parents[2]
PROFILE = (
    REPO
    / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
)
ARTIFACTS = REPO / "manifests/artifacts.tsv"
EXPECTED_SEQUENCE = (
    "diagnostic-target",
    "exact-alpine-fallback",
    "bootloader",
    "observation-recovery",
    "postmortem-status",
)
HISTORICAL_CLAIM_MANIFEST_SHA256 = (
    "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
)


def historical_claim_record(profile: str) -> bytes:
    return (
        "format=rog5-temporary-boot-consumption-v1\n"
        f"recovery_profile={profile}\n"
        "candidate=headless-netroot-early-diag-v1\n"
        f"manifest_sha256={HISTORICAL_CLAIM_MANIFEST_SHA256}\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")


EXPECTED_CLAIMS = {
    profile: historical_claim_record(profile)
    for profile in (
        "headless-diagnostic-generation11-live-v1",
        "headless-diagnostic-generation12-live-v1",
    )
}
EXPECTED_CLAIMS["headless-core-deployment-v1-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-core-deployment-v1-live-v1\n"
    "candidate=headless-core-network-root-v2\n"
    "manifest_sha256="
    "f3884e6554f3d2c1bb437c45484f658817c006185d6c84a5ac4ef452b01bc02f\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-storage-read-v1-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-storage-read-v1-live-v1\n"
    "candidate=persistent-root-storage-read-v1\n"
    "manifest_sha256="
    "f82ea25ffb484668dd56cbd01b33b12062d26d29d40d14000b73afe41c857753\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v2"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v2\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v3"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v3\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v4"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v4\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v5"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v5\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v6"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v6\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v7"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v7\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v8"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v8\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v9"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v9\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-host-rendezvous-v3-live-v10"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v10\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-acceptance-v13-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-acceptance-v13-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-bootstrap-v14-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-bootstrap-v14-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-network-ready-v15-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-network-ready-v15-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-inert-block-v16-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-inert-block-v16-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-gadget-contract-v17-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-gadget-contract-v17-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-configfs-link-v18-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-configfs-link-v18-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["headless-diagnostic-ssh-iproute-whitespace-v19-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=headless-diagnostic-ssh-iproute-whitespace-v19-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS[
    "headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1"
] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile="
    "headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["retention-host-rendezvous-v3-observer-v2"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=retention-host-rendezvous-v3-observer-v2\n"
    "candidate=headless-netroot-early-diag-v2\n"
    "manifest_sha256="
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")


def retention_claim_record(
    role: str,
    identifier: str,
    recovery_sha256: str,
    peer_recovery_sha256: str,
) -> bytes:
    return (
        "format=rog5-retention-boot-consumption-v1\n"
        "retention_profile=host-rendezvous-v3-observer-v1\n"
        "cycle_sha256="
        "d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        f"claim_role={role}\n"
        f"recovery_profile={identifier}\n"
        f"recovery_sha256={recovery_sha256}\n"
        f"peer_recovery_sha256={peer_recovery_sha256}\n"
        "candidate=headless-netroot-early-diag-v2\n"
        "manifest_sha256="
        "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")


EXPECTED_CLAIMS.update(
    {
        "retention-host-rendezvous-v3-execution-v1": retention_claim_record(
            "execution",
            "retention-host-rendezvous-v3-execution-v1",
            "cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d",
            "3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b",
        ),
        "retention-host-rendezvous-v3-observer-v1": retention_claim_record(
            "observer",
            "retention-host-rendezvous-v3-observer-v1",
            "3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b",
            "cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d",
        ),
    }
)
EXPECTED_CLAIMS["persistent-root-storage-read-v2-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-storage-read-v2-live-v1\n"
    "candidate=persistent-root-storage-read-v2\n"
    "manifest_sha256="
    "4b56111b2f40157b5173a24adfedf53341cb243a661fc744410673b1ab7aa567\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-storage-read-v3-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-storage-read-v3-live-v1\n"
    "candidate=persistent-root-storage-read-v3\n"
    "manifest_sha256="
    "3bc4b40f7e230945249db08be19b5791c176e08aeb8b5cfca059f48db5b8ed73\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-storage-read-v4-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-storage-read-v4-live-v1\n"
    "candidate=persistent-root-storage-read-v4\n"
    "manifest_sha256="
    "5d835b0986587c7ce174e66ccf03f82bb8c9e581e83384ce93c0ed455d053baa\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-storage-read-v5-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-storage-read-v5-live-v1\n"
    "candidate=persistent-root-storage-read-v5\n"
    "manifest_sha256="
    "1d64161dd213ced57b6761086629351ba116b30f894aa36afba9480873b4e3ab\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-usb-control-v6-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-usb-control-v6-live-v1\n"
    "candidate=persistent-root-usb-control-v6\n"
    "manifest_sha256="
    "33715e0c566a5fc7e771f6b89ca81fd1fe0bb6325b926995a0ba5c5f81a44a5b\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-dtb-control-v7-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-dtb-control-v7-live-v1\n"
    "candidate=persistent-root-dtb-control-v7\n"
    "manifest_sha256="
    "c4cef9e256708d219c7c77f792dbff43336c5d446d0721048ff471b7c05969ee\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-image-control-v8-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-image-control-v8-live-v1\n"
    "candidate=persistent-root-image-control-v8\n"
    "manifest_sha256="
    "c3cab07c75012941b103a9100e69298ef69de7aa4d73893d6d02ea4602f66f56\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-accepted-image-v9-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-accepted-image-v9-live-v1\n"
    "candidate=persistent-root-accepted-image-v9\n"
    "manifest_sha256="
    "90c3cd03ab749003d46f039b31d6bffd51b98d2ea18e858eaddf59cb64c0efbd\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-deferred-ufs-v10-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-deferred-ufs-v10-live-v1\n"
    "candidate=persistent-root-deferred-ufs-v10\n"
    "manifest_sha256="
    "dc22fde250d88f75859d544737d3703f9a3cf09ca2987eaf213dd744204cd8f7\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-deferred-qmp-ufs-v11-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-deferred-qmp-ufs-v11-live-v1\n"
    "candidate=persistent-root-deferred-qmp-ufs-v11\n"
    "manifest_sha256="
    "e40da74acb705843b0f29c485ca922209e44073f7baab144cbac17c5b285500e\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-ufs-phy-control-v12-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-ufs-phy-control-v12-live-v1\n"
    "candidate=persistent-root-qmp-ufs-phy-control-v12\n"
    "manifest_sha256="
    "330f33a533f8f65e1d32b9e9c90bce10b4301983d7dced88fddfcd8f49e9f294\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-module-load-control-v13-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-module-load-control-v13-live-v1\n"
    "candidate=persistent-root-qmp-module-load-control-v13\n"
    "manifest_sha256="
    "30fb6c355aa8e34097592cf4b33fe7ae4c4193a4c85ae36744c90778f1818cb7\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-regulator-stage-v14-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-regulator-stage-v14-live-v1\n"
    "candidate=persistent-root-qmp-regulator-stage-v14\n"
    "manifest_sha256="
    "03e49b58a082826c1d88ab328c82d6c903c9130e56522fb645eaa3be31eb69a7\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-mmio-stage-v15-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-mmio-stage-v15-live-v1\n"
    "candidate=persistent-root-qmp-mmio-stage-v15\n"
    "manifest_sha256="
    "d81ff27520337a91e556018109173d4d14d9c38d0846639f2d056150fa39886d\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-clock-provider-stage-v16-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-clock-provider-stage-v16-live-v1\n"
    "candidate=persistent-root-qmp-clock-provider-stage-v16\n"
    "manifest_sha256="
    "dd832a7655e4a1130b69f07188907f80853004f5e05c150e827a0aee4e1c6447\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-fixed-clocks-stage-v17-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-fixed-clocks-stage-v17-live-v1\n"
    "candidate=persistent-root-qmp-fixed-clocks-stage-v17\n"
    "manifest_sha256="
    "abd615f73576c798505464c07a3816da470eee5eeb9c26bc2f8f201f85b44ba4\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-first-fixed-clock-stage-v18-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-first-fixed-clock-stage-v18-live-v1\n"
    "candidate=persistent-root-qmp-first-fixed-clock-stage-v18\n"
    "manifest_sha256="
    "f047d1c0ca676afa62a8a4f30d7b68306622b2eee5fc8dfb8b94e9d71450d3c5\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-allocation-stage-v19-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-allocation-stage-v19-live-v1\n"
    "candidate=persistent-root-qmp-allocation-stage-v19\n"
    "manifest_sha256="
    "82f38e524cc9f8c65bd5ae225bbb4d0acf4a7ef20021d61af313880c98731835\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-first-clock-name-stage-v20-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-first-clock-name-stage-v20-live-v1\n"
    "candidate=persistent-root-qmp-first-clock-name-stage-v20\n"
    "manifest_sha256="
    "86c8262c080b0b7254a9175bc8487f464db7a4304ba7879b450a74504a23f713\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1\n"
    "candidate=persistent-root-qmp-first-clock-runtime-pm-stage-v21\n"
    "manifest_sha256="
    "782756493f38d5ea9a634678043214926e9b49ef1ca01ce35e9e41e37169fd4b\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1\n"
    "candidate=persistent-root-qmp-second-clock-runtime-pm-stage-v22\n"
    "manifest_sha256="
    "052d462cbd7820de331c446598f69224128eced8175665acd703428efb75b371\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1\n"
    "candidate=persistent-root-qmp-third-clock-runtime-pm-stage-v23\n"
    "manifest_sha256="
    "6d8195d2e384558b9ff79a42966fd6841837b38d4b41e83dd745bf554be14dc6\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1\n"
    "candidate=persistent-root-qmp-clock-provider-cleanup-stage-v24\n"
    "manifest_sha256="
    "1bc07a9e0b0acf874f542a84f1d7d8c12505504790bc4da433eb22989b76839b\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1\n"
    "candidate=persistent-root-qmp-clock-provider-cleanup-stage-v25\n"
    "manifest_sha256="
    "14f9b93e9951d664e036ef189526bef59a167572dd7a23c052ba56aed9fd44cf\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")
EXPECTED_CLAIMS["persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1"] = (
    "format=rog5-temporary-boot-consumption-v1\n"
    "recovery_profile=persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1\n"
    "candidate=persistent-root-qmp-ufs-phy-creation-stage-v26\n"
    "manifest_sha256="
    "7f05c55c553e057b418f2adc23f284a907dd9ca693d532228372ad9dfe3e57c4\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")


def mainline_udc_claim_record(
    role: str,
    identifier: str,
    recovery_sha256: str,
    peer_recovery_sha256: str,
) -> bytes:
    return (
        "format=rog5-retention-boot-consumption-v1\n"
        "retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        "cycle_sha256="
        "c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        f"claim_role={role}\n"
        f"recovery_profile={identifier}\n"
        f"recovery_sha256={recovery_sha256}\n"
        f"peer_recovery_sha256={peer_recovery_sha256}\n"
        "candidate=headless-netroot-early-diag-v2\n"
        "manifest_sha256="
        "ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")


EXPECTED_CLAIMS.update(
    {
        "retention-host-rendezvous-v11-mainline-udc-execution-v2": (
            mainline_udc_claim_record(
                "execution",
                "retention-host-rendezvous-v11-mainline-udc-execution-v2",
                "2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb",
                "c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e",
            )
        ),
        "retention-host-rendezvous-v11-mainline-udc-observer-v2": (
            mainline_udc_claim_record(
                "observer",
                "retention-host-rendezvous-v11-mainline-udc-observer-v2",
                "c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e",
                "2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb",
            )
        ),
    }
)


def nfs_xattr_claim_record(
    role: str,
    identifier: str,
    recovery_sha256: str,
    peer_recovery_sha256: str,
) -> bytes:
    return (
        "format=rog5-retention-boot-consumption-v1\n"
        "retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        "cycle_sha256="
        "e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        f"claim_role={role}\n"
        f"recovery_profile={identifier}\n"
        f"recovery_sha256={recovery_sha256}\n"
        f"peer_recovery_sha256={peer_recovery_sha256}\n"
        "candidate=headless-netroot-early-diag-v2\n"
        "manifest_sha256="
        "325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")


EXPECTED_CLAIMS.update(
    {
        "retention-host-rendezvous-v12-nfs-xattr-execution-v1": (
            nfs_xattr_claim_record(
                "execution",
                "retention-host-rendezvous-v12-nfs-xattr-execution-v1",
                "f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2",
                "9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69",
            )
        ),
        "retention-host-rendezvous-v12-nfs-xattr-observer-v1": (
            nfs_xattr_claim_record(
                "observer",
                "retention-host-rendezvous-v12-nfs-xattr-observer-v1",
                "9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69",
                "f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2",
            )
        ),
    }
)
EXPECTED_SEQUENCE_REFERENCE = {
    "path": "scripts/host/retention-cycle-sequence-reference.py",
    "size": 11923,
    "sha256": "97075ed7c09cf2c5df5566a971c922d8ea9b1d6b0e53e19f33bed3d220378e44",
    "mode": "0755",
    "implementation": "reference-only",
    "cycle_sha256": "d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078",
    "execution_identifier": "retention-host-rendezvous-v3-execution-v1",
    "execution_record_sha256": "ef0895b7e104a283c44113a67c8f51e826b0088d597b0969ed5ca774e0dc7bbd",
    "observer_identifier": "retention-host-rendezvous-v3-observer-v1",
    "observer_record_sha256": "f0b687163c38fe07c637c6ae863e0244d5cfb2af2d6a97632875473e3c33e345",
}
EXPECTED_TRANSACTION_FIXTURE = {
    "path": "scripts/host/retention-cycle-transaction.py",
    "size": 40185,
    "sha256": "f13fa41bfee58b79eab9ed76650049d0fb160ea578d60071b3199440a8868428",
    "mode": "0644",
    "implementation": "offline-append-only-fixture",
    "event_format": "rog5-retention-cycle-event-v1",
    "cycle_sha256": "d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078",
    "live_entrypoint": "none",
    "claim_registration": "none",
    "policy_allow_rows": 0,
    "ambiguous_reopen": "terminal-only",
}
EXPECTED_ADAPTER_FIXTURE = {
    "path": "scripts/host/retention-cycle-adapter.py",
    "size": 10260,
    "sha256": "c36b4bfa407b4c5d0df6e32f2b69ebbbf411eaad75649465f89161aa84bf6976",
    "mode": "0644",
    "implementation": "callback-only-fixture",
    "journal_sha256": "f13fa41bfee58b79eab9ed76650049d0fb160ea578d60071b3199440a8868428",
    "cycle_sha256": "d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078",
    "invocation_count": 6,
    "live_entrypoint": "none",
    "builtin_executor": "none",
    "claim_registration": "none",
    "policy_allow_rows": 0,
}
EXPECTED_EXECUTOR_CONTRACT = {
    "path": "scripts/host/retention-cycle-executor-contract.py",
    "size": 14562,
    "sha256": "7fdbc6d0bd8ed9a5bbba9018b6049f0983a319e828a0a8e9d15604185cf8ae5d",
    "mode": "0644",
    "implementation": "pure-process-contract-v1",
    "adapter_sha256": "c36b4bfa407b4c5d0df6e32f2b69ebbbf411eaad75649465f89161aa84bf6976",
    "invocation_count": 6,
    "boot_result_protocol": "rog5-retention-boot-result-v1",
    "boot_result_dynamic_inputs": ["fastboot_serial", "usb_location"],
    "inherited_environment": "none",
    "stdin": "devnull",
    "stdout_stderr": "separate-bounded-pipes",
    "timeout_seconds": [15, 300, 240, 15, 300, 90],
    "output_limit_bytes": [4096, 131072, 131072, 4096, 131072, 16384],
    "timeout_cleanup": "process-group",
    "fallback_transport": "nonce-framed-acm",
    "private_key_input": "none",
    "host_pin_access": "unopened-path-contract-only",
    "live_entrypoint": "none",
    "builtin_executor": "none",
    "credential_use": "none",
    "claim_registration": "none",
    "policy_allow_rows": 0,
}
EXPECTED_EXECUTOR_BOUNDARY = {
    "path": "scripts/host/retention-cycle-executor-boundary.py",
    "size": 24548,
    "sha256": "76cd7367e73e1ec8e38d545b2cf387c8700279dca6aba3f337a9a9123b8f1e43",
    "mode": "0644",
    "implementation": "pure-descriptor-output-boundary-v1",
    "executor_contract_sha256": "7fdbc6d0bd8ed9a5bbba9018b6049f0983a319e828a0a8e9d15604185cf8ae5d",
    "boot_result_protocol": "rog5-retention-boot-result-v1",
    "decoded_actions": [
        "execution-claim",
        "execution-boot",
        "fallback-reboot",
        "observer-claim",
        "observer-boot",
        "postmortem-read",
    ],
    "blocked_actions": {
        "execution-boot": "hold-gate-no-current-success",
        "observer-boot": "hold-gate-no-current-success",
    },
    "live_producer_state": {
        "execution-boot": "hold-gate-no-current-success",
        "fallback-reboot": "guarded-producer-defined",
        "observer-boot": "hold-gate-no-current-success",
    },
    "program_open_flags": ["O_CLOEXEC", "O_NOFOLLOW", "O_RDONLY"],
    "directory_open_flags": [
        "O_CLOEXEC",
        "O_DIRECTORY",
        "O_NOFOLLOW",
        "O_RDONLY",
    ],
    "python_interpreter": {
        "logical_path": "/usr/bin/python3",
        "resolved_path": "/usr/bin/python3.13",
        "link_target": "python3.13",
        "size": 14352,
        "sha256": "62cf34d8c76bbde1cceea478800c3b9125a90746dd73f1281614823bdcf1b718",
    },
    "bash_interpreter": {
        "logical_path": "/usr/bin/bash",
        "resolved_path": "/usr/bin/bash",
        "link_target": "none",
        "size": 1162328,
        "sha256": "66bb45cd80c82ea4c352c774c0f1577ad51707f55749e90dd6b787a9fb3022d1",
    },
    "fallback_host_pin": "public-ed25519-snapshot-required",
    "fallback_host_pin_sha256": "not-defined",
    "runtime_closure": "offline-fixture-only-production-descriptor-execution-unproven",
    "live_entrypoint": "none",
    "builtin_executor": "none",
    "credential_use": "none",
    "claim_registration": "none",
    "policy_allow_rows": 0,
}
EXPECTED_EXECUTOR_RUNTIME = {
    "path": "scripts/host/retention-cycle-runtime-closure.py",
    "size": 38531,
    "sha256": "2cce1d450805d4a5f43352b221d35011e43ade5868817cce37b322912f3c765b",
    "mode": "0644",
    "implementation": "offline-fresh-pipe-fixture-v1",
    "executor_boundary_sha256": "76cd7367e73e1ec8e38d545b2cf387c8700279dca6aba3f337a9a9123b8f1e43",
    "transaction_sha256": "f13fa41bfee58b79eab9ed76650049d0fb160ea578d60071b3199440a8868428",
    "intent_binding": "held-fsynced-event-descriptor",
    "pipe_binding": "fresh-empty-cloexec-distinct",
    "process_backend": "forked-fixed-writer-only",
    "runtime_nonce": "getrandom-256-bit",
    "single_use": "in-process-attempt-terminal",
    "timeout_cleanup": "process-group-term-kill",
    "result_type": "offline-wrapper-adapter-ineligible",
    "live_entrypoint": "none",
    "adapter_wiring": "none",
    "production_execution": "none",
    "production_descriptor_execution": "unproven",
    "connected_admission": "none",
    "credential_use": "none",
    "result_authority": "none",
    "claim_registration": "none",
    "policy_allow_rows": 0,
}
EXPECTED_EXECUTOR_DESCRIPTOR_FIXTURE = {
    "runner_path": "scripts/host/retention-cycle-descriptor-execution.py",
    "runner_size": 30039,
    "runner_sha256": "7e82e52ed44343f665f5f03f26b8540c7743415d74145c58db0eb3b935dd1d8a",
    "runner_mode": "0644",
    "probe_path": "scripts/host/retention-cycle-descriptor-probe.py",
    "probe_size": 5288,
    "probe_sha256": "afba8ae9c2bff325eadcae781895aafd7934897b238edcdc72bf73f7f38e20f5",
    "probe_mode": "0644",
    "implementation": "offline-held-fd-exec-v1",
    "executor_runtime_sha256": "2cce1d450805d4a5f43352b221d35011e43ade5868817cce37b322912f3c765b",
    "interpreter_logical_path": "/usr/bin/python3",
    "interpreter_resolved_path": "/usr/bin/python3.13",
    "interpreter_sha256": "62cf34d8c76bbde1cceea478800c3b9125a90746dd73f1281614823bdcf1b718",
    "program_exec_fd": 198,
    "interpreter_exec_fd": 199,
    "interpreter_execution": "fexecve-held-descriptor",
    "program_execution": "proc-self-fd-held-descriptor",
    "repository_cwd": "held-directory-fchdir",
    "environment": "closed-exact",
    "umask": "0077",
    "stdin": "devnull",
    "stdout": "bounded-pipe",
    "stderr": "bounded-pipe",
    "modes": ["success", "timeout", "descendant", "overflow", "exit"],
    "single_use": "in-process-attempt-terminal",
    "timeout_cleanup": "process-group-term-kill",
    "result_type": "offline-evidence-adapter-ineligible",
    "fixture_descriptor_execution": "proven",
    "production_descriptor_execution": "unproven",
    "live_entrypoint": "none",
    "adapter_wiring": "none",
    "production_execution": "none",
    "connected_admission": "none",
    "credential_use": "none",
    "result_authority": "none",
    "claim_registration": "none",
    "policy_allow_rows": 0,
}
SHA256_ZERO = "0" * 64
MAX_INITRAMFS_BYTES = 32 * 1024 * 1024
MAX_BUFFERED_INPUT_BYTES = 32 * 1024 * 1024
BOOT_V3_PAGE_SIZE = 4096
BOOT_V3_HEADER_SIZE = 1580
EXPECTED_RECOVERY_CMDLINE = (
    "init=/init selinux=0 printk.devkmsg=on rog5linux.test=1 "
    "ramoops.mem_address=0x9b800000 ramoops.mem_size=0x400000 "
    "ramoops.record_size=0x100000 ramoops.console_size=0x300000 "
    "ramoops.pmsg_size=0 ramoops.ftrace_size=0 ramoops.dump_oops=1 "
    "rog5.recovery_timeout=180"
)
EXPECTED_RECOVERY_INPUT_PATHS = {
    "init": "initramfs/recovery-init",
    "control_build": "configs/recovery-control/aarch64-build-v1.json",
}
EXPECTED_RECOVERY_CONTROL_SOURCE = (
    "tools/recovery_control/rog5-recovery-control.c"
)
EXPECTED_RECOVERY_CONTROL_BUILDER = (
    "scripts/device/build-recovery-control.sh"
)
EXPECTED_RECOVERY_CONTROL_IMAGE_ID = (
    "a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e"
)
EXPECTED_RECOVERY_CONTROL_IMAGE_DIGEST = (
    "sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa"
)
ACTIVE_ROOT_IDENTITIES: ContextVar[dict[Path, tuple[int, ...]]] = ContextVar(
    "active_retention_review_roots",
    default={},
)


class AdmissionError(RuntimeError):
    """The offline pair is not an exact, authority-free review."""


class NewcEntry(NamedTuple):
    mode: int
    uid: int
    gid: int
    nlink: int
    payload: bytes


def fail(message: str) -> None:
    raise AdmissionError(message)


def require_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"{label} fields are not exact")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label} is not a nonempty string")
    return value


def require_sha256(value: Any, label: str) -> str:
    digest = require_string(value, label)
    if (
        len(digest) != 64
        or digest == SHA256_ZERO
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        fail(f"{label} is not one nonzero lowercase SHA-256")
    return digest


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def read_json(
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    expected_digest: str | None = None,
    expected_mode: int | None = None,
) -> dict[str, Any]:
    payload = read_verified_bytes(
        path,
        label,
        expected_size=expected_size,
        expected_digest=expected_digest,
        expected_mode=expected_mode,
    )
    try:
        value = json.loads(
            payload,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AdmissionError(f"{label} is not canonical JSON") from error
    if not isinstance(value, dict):
        fail(f"{label} is not a JSON object")
    return value


def hash_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while block := os.read(descriptor, 1024 * 1024):
        digest.update(block)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return digest.hexdigest()


def stable_metadata(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def stable_directory_metadata(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
    )


def exact_regular(metadata: os.stat_result) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and metadata.st_nlink == 1
    )


@contextmanager
def path_descriptor(
    path: Path,
    label: str,
    *,
    directory: bool,
) -> Iterator[int]:
    if not path.is_absolute() or path != Path(os.path.normpath(path)):
        fail(f"unsafe or missing {label}")
    directory_flags = (
        os.O_RDONLY
        | os.O_CLOEXEC
        | os.O_DIRECTORY
        | getattr(os, "O_NOFOLLOW", 0)
    )
    final_flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    if directory:
        final_flags |= os.O_DIRECTORY
    descriptors: list[int] = []
    ancestry: list[tuple[int, str, int, tuple[int, ...]]] = []
    try:
        current = os.open("/", directory_flags)
        descriptors.append(current)
        current_path = Path("/")
        for part in path.parts[1:-1]:
            child = os.open(part, directory_flags, dir_fd=current)
            descriptors.append(child)
            opened = os.fstat(child)
            named = os.stat(part, dir_fd=current, follow_symlinks=False)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or stable_directory_metadata(opened)
                != stable_directory_metadata(named)
            ):
                fail(f"unsafe or missing {label}")
            current_path /= part
            pinned = ACTIVE_ROOT_IDENTITIES.get().get(current_path)
            if pinned is not None and stable_directory_metadata(opened) != pinned:
                fail(f"{label} escaped its pinned root")
            ancestry.append(
                (current, part, child, stable_directory_metadata(opened))
            )
            current = child
        leaf = path.parts[-1]
        descriptor = os.open(leaf, final_flags, dir_fd=current)
        descriptors.append(descriptor)
        opened = os.fstat(descriptor)
        named = os.stat(leaf, dir_fd=current, follow_symlinks=False)
        if stable_metadata(opened) != stable_metadata(named):
            fail(f"unsafe or missing {label}")
        final_path = current_path / leaf
        pinned = ACTIVE_ROOT_IDENTITIES.get().get(final_path)
        if pinned is not None and stable_directory_metadata(opened) != pinned:
            fail(f"{label} escaped its pinned root")

        def revalidate_path() -> None:
            for parent, name, child, expected in ancestry:
                if (
                    stable_directory_metadata(os.fstat(child)) != expected
                    or stable_directory_metadata(
                        os.stat(name, dir_fd=parent, follow_symlinks=False)
                    )
                    != expected
                ):
                    fail(f"{label} ancestry changed during verification")
            if (
                stable_metadata(os.fstat(descriptor))
                != stable_metadata(opened)
                or stable_metadata(
                    os.stat(leaf, dir_fd=current, follow_symlinks=False)
                )
                != stable_metadata(opened)
            ):
                fail(f"{label} changed during verification")

        revalidate_path()
        yield descriptor
        revalidate_path()
    except OSError as error:
        raise AdmissionError(f"unsafe or changed {label}") from error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def require_mode(value: Any, label: str) -> int:
    mode = require_string(value, label)
    if len(mode) != 4 or mode[0] != "0" or any(
        character not in "01234567" for character in mode[1:]
    ):
        fail(f"{label} is not an exact file mode")
    return int(mode, 8)


@contextmanager
def verified_descriptor(
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    expected_digest: str | None = None,
    expected_mode: int | None = None,
) -> Iterator[int]:
    with path_descriptor(path, label, directory=False) as descriptor:
        opened = os.fstat(descriptor)
        if not exact_regular(opened):
            fail(f"unsafe or missing {label}")
        if expected_mode is not None and stat.S_IMODE(opened.st_mode) != expected_mode:
            fail(f"{label} mode changed")
        if expected_size is not None and opened.st_size != expected_size:
            fail(f"{label} size changed")
        first_digest = hash_descriptor(descriptor)
        if expected_digest is not None and first_digest != expected_digest:
            fail(f"{label} identity changed")
        after_hash = os.fstat(descriptor)
        if stable_metadata(after_hash) != stable_metadata(opened):
            fail(f"{label} changed during verification")
        yield descriptor
        final_digest = hash_descriptor(descriptor)
        final = os.fstat(descriptor)
        if (
            final_digest != first_digest
            or stable_metadata(final) != stable_metadata(opened)
        ):
            fail(f"{label} changed during verification")


@contextmanager
def verified_directory_descriptor(path: Path, label: str) -> Iterator[int]:
    with path_descriptor(path, label, directory=True) as descriptor:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            fail(f"unsafe or missing {label}")
        yield descriptor


def read_descriptor(
    descriptor: int,
    *,
    maximum: int = MAX_BUFFERED_INPUT_BYTES,
) -> bytes:
    if os.fstat(descriptor).st_size > maximum:
        fail("buffered input exceeds its fixed limit")
    os.lseek(descriptor, 0, os.SEEK_SET)
    blocks: list[bytes] = []
    total = 0
    while block := os.read(descriptor, min(1024 * 1024, maximum + 1 - total)):
        blocks.append(block)
        total += len(block)
        if total > maximum:
            fail("buffered input exceeds its fixed limit")
    os.lseek(descriptor, 0, os.SEEK_SET)
    return b"".join(blocks)


def read_verified_bytes(
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    expected_digest: str | None = None,
    expected_mode: int | None = None,
) -> bytes:
    with verified_descriptor(
        path,
        label,
        expected_size=expected_size,
        expected_digest=expected_digest,
        expected_mode=expected_mode,
    ) as descriptor:
        return read_descriptor(descriptor)


def safe_file_metadata(path: Path, label: str) -> os.stat_result:
    with verified_descriptor(path, label) as descriptor:
        return os.fstat(descriptor)


def read_safe_file(
    path: Path,
    label: str,
    *,
    expected_mode: int | None = None,
) -> bytes:
    with verified_descriptor(
        path,
        label,
        expected_mode=expected_mode,
    ) as descriptor:
        return read_descriptor(descriptor)


def safe_root(path: Path, label: str) -> Path:
    if not path.is_absolute() or path != Path(os.path.normpath(path)):
        fail(f"{label} must be absolute")
    with verified_directory_descriptor(path, label):
        pass
    return path


def directory_inventory(path: Path, label: str) -> tuple[str, ...]:
    entries: list[str] = []
    with verified_directory_descriptor(path, label) as descriptor:
        try:
            iterator = os.scandir(descriptor)
        except OSError as error:
            raise AdmissionError(f"{label} inventory is unavailable") from error
        with iterator:
            for entry in iterator:
                try:
                    metadata = entry.stat(follow_symlinks=False)
                except OSError as error:
                    raise AdmissionError(
                        f"{label} inventory changed during verification"
                    ) from error
                if stat.S_ISREG(metadata.st_mode):
                    kind = "file"
                elif stat.S_ISDIR(metadata.st_mode):
                    kind = "directory"
                else:
                    fail(f"{label} contains an unsafe object")
                entries.append(f"{entry.name}:{kind}")
    return tuple(sorted(entries))


def verify_directory_inventory(
    path: Path,
    expected: Any,
    label: str,
) -> None:
    if (
        not isinstance(expected, list)
        or not expected
        or any(not isinstance(item, str) or not item for item in expected)
        or expected != sorted(set(expected))
    ):
        fail(f"{label} contract is not exact")
    if directory_inventory(path, label) != tuple(expected):
        fail(f"{label} is not exact")


def relative_path(value: Any, label: str) -> PurePosixPath:
    raw = require_string(value, label)
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(
        part in ("", ".", "..") for part in path.parts
    ):
        fail(f"{label} is not a safe relative path")
    return path


def safe_child(root: Path, value: Any, label: str) -> Path:
    relative = relative_path(value, label)
    current = root
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise AdmissionError(f"unsafe or missing {label}") from error
        if not stat.S_ISDIR(metadata.st_mode):
            fail(f"unsafe or missing {label}")
    path = root.joinpath(*relative.parts)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise AdmissionError(f"unsafe or missing {label}") from error
    if resolved != path:
        fail(f"unsafe or missing {label}")
    return path


def require_absent_child(root: Path, value: Any, label: str) -> None:
    relative = relative_path(value, label)
    parent = root.joinpath(*relative.parts[:-1])
    with verified_directory_descriptor(parent, f"{label} parent") as descriptor:
        try:
            os.stat(relative.parts[-1], dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError as error:
            raise AdmissionError(f"unsafe {label}") from error
    fail(f"{label} must be absent")


def verify_file(
    path: Path,
    size: Any,
    digest: Any,
    mode: Any,
    label: str,
) -> None:
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        fail(f"{label} size is invalid")
    expected = require_sha256(digest, f"{label} SHA-256")
    expected_mode = require_mode(mode, f"{label} mode")
    with verified_descriptor(
        path,
        label,
        expected_size=size,
        expected_digest=expected,
        expected_mode=expected_mode,
    ):
        pass


def verify_pair(
    root: Path,
    value: Any,
    label: str,
) -> tuple[Path, Path, str]:
    record = require_keys(
        value,
        {"path_a", "path_b", "size", "sha256", "mode"},
        label,
    )
    first = safe_child(root, record["path_a"], f"{label} A")
    second = safe_child(root, record["path_b"], f"{label} B")
    if first == second:
        fail(f"{label} twins use one pathname")
    verify_file(
        first,
        record["size"],
        record["sha256"],
        record["mode"],
        f"{label} A",
    )
    verify_file(
        second,
        record["size"],
        record["sha256"],
        record["mode"],
        f"{label} B",
    )
    return first, second, require_sha256(record["sha256"], f"{label} SHA-256")


def verify_single(root: Path, value: Any, label: str) -> tuple[Path, str]:
    record = require_keys(value, {"path", "size", "sha256", "mode"}, label)
    path = safe_child(root, record["path"], label)
    verify_file(path, record["size"], record["sha256"], record["mode"], label)
    return path, require_sha256(record["sha256"], f"{label} SHA-256")


def expected_identity(value: Any, label: str, *, pair: bool) -> tuple[int, str]:
    keys = {"path_a", "path_b", "size", "sha256", "mode"} if pair else {
        "path",
        "size",
        "sha256",
        "mode",
    }
    record = require_keys(value, keys, label)
    size = record["size"]
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        fail(f"{label} size is invalid")
    require_mode(record["mode"], f"{label} mode")
    return size, require_sha256(record["sha256"], f"{label} SHA-256")


def verify_recovery_inputs(
    repo: Path,
    value: Any,
) -> tuple[
    bytes,
    tuple[int, str],
    int,
    str,
    str,
    dict[str, Any],
]:
    inputs = require_keys(
        value,
        {"init", "control_build"},
        "recovery input contract",
    )
    init = require_keys(
        inputs["init"],
        {"path", "size", "sha256", "mode"},
        "recovery init source",
    )
    if init["path"] != EXPECTED_RECOVERY_INPUT_PATHS["init"]:
        fail("recovery init source repository path is not exact")
    init_identity = expected_identity(
        init,
        "recovery init source",
        pair=False,
    )
    init_mode = require_mode(init["mode"], "recovery init source mode")
    if init_mode != 0o755:
        fail("recovery init source mode is not exact")
    init_payload = read_verified_bytes(
        safe_child(repo, init["path"], "recovery init source"),
        "recovery init source",
        expected_size=init_identity[0],
        expected_digest=init_identity[1],
        expected_mode=init_mode,
    )

    build_record = require_keys(
        inputs["control_build"],
        {"path", "size", "sha256", "mode"},
        "recovery control build record",
    )
    if build_record["path"] != EXPECTED_RECOVERY_INPUT_PATHS["control_build"]:
        fail("recovery control build record repository path is not exact")
    build_identity = expected_identity(
        build_record,
        "recovery control build record",
        pair=False,
    )
    build_mode = require_mode(
        build_record["mode"],
        "recovery control build record mode",
    )
    if build_mode != 0o644:
        fail("recovery control build record mode is not exact")
    build = require_keys(
        read_json(
            safe_child(
                repo,
                build_record["path"],
                "recovery control build record",
            ),
            "recovery control build record",
            expected_size=build_identity[0],
            expected_digest=build_identity[1],
            expected_mode=build_mode,
        ),
        {"format", "source", "builder", "output"},
        "recovery control build record",
    )
    if build["format"] != "rog5-recovery-control-build-v1":
        fail("recovery control build record format changed")

    source = require_keys(
        build["source"],
        {"path", "size", "sha256", "mode"},
        "recovery control source",
    )
    if source["path"] != EXPECTED_RECOVERY_CONTROL_SOURCE:
        fail("recovery control source repository path is not exact")
    source_identity = expected_identity(
        source,
        "recovery control source",
        pair=False,
    )
    source_mode = require_mode(source["mode"], "recovery control source mode")
    if source_mode != 0o644:
        fail("recovery control source mode is not exact")
    read_verified_bytes(
        safe_child(repo, source["path"], "recovery control source"),
        "recovery control source",
        expected_size=source_identity[0],
        expected_digest=source_identity[1],
        expected_mode=source_mode,
    )

    builder = require_keys(
        build["builder"],
        {
            "script_path",
            "script_size",
            "script_sha256",
            "script_mode",
            "image",
            "image_id",
            "image_digest",
            "architecture",
            "compiler_version",
            "source_date_epoch",
        },
        "recovery control builder",
    )
    if builder["script_path"] != EXPECTED_RECOVERY_CONTROL_BUILDER:
        fail("recovery control builder repository path is not exact")
    script_size = builder["script_size"]
    if (
        not isinstance(script_size, int)
        or isinstance(script_size, bool)
        or script_size <= 0
    ):
        fail("recovery control builder size is invalid")
    script_digest = require_sha256(
        builder["script_sha256"],
        "recovery control builder SHA-256",
    )
    script_mode = require_mode(
        builder["script_mode"],
        "recovery control builder mode",
    )
    if script_mode != 0o755:
        fail("recovery control builder mode is not exact")
    read_verified_bytes(
        safe_child(repo, builder["script_path"], "recovery control builder"),
        "recovery control builder",
        expected_size=script_size,
        expected_digest=script_digest,
        expected_mode=script_mode,
    )
    image_id = require_sha256(
        builder["image_id"],
        "recovery control image ID",
    )
    image_digest = require_string(
        builder["image_digest"],
        "recovery control image digest",
    )
    if image_digest.startswith("sha256:"):
        require_sha256(
            image_digest[len("sha256:") :],
            "recovery control image digest",
        )
    if (
        builder["image"]
        != "localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1"
        or image_id != EXPECTED_RECOVERY_CONTROL_IMAGE_ID
        or image_digest != EXPECTED_RECOVERY_CONTROL_IMAGE_DIGEST
        or builder["architecture"] != "arm64"
        or builder["compiler_version"] != "15.2.0"
        or builder["source_date_epoch"] != 1681862400
    ):
        fail("recovery control builder identity changed")

    binary = require_keys(
        build["output"],
        {"size", "sha256", "mode"},
        "recovery control binary",
    )
    binary_size = binary["size"]
    if (
        not isinstance(binary_size, int)
        or isinstance(binary_size, bool)
        or binary_size <= 0
    ):
        fail("recovery control binary size is invalid")
    binary_identity = (
        binary_size,
        require_sha256(
            binary["sha256"],
            "recovery control binary SHA-256",
        ),
    )
    binary_mode = require_mode(binary["mode"], "recovery control binary mode")
    if binary_mode != 0o755:
        fail("recovery control binary mode is not exact")
    return (
        init_payload,
        binary_identity,
        binary_mode,
        init_identity[1],
        source_identity[1],
        build,
    )


def verify_embedded_recovery_inputs(
    entries: dict[str, NewcEntry],
    init_payload: bytes,
    control_identity: tuple[int, str],
) -> None:
    init = entries.get("init")
    if (
        init is None
        or not stat.S_ISREG(init.mode)
        or stat.S_IMODE(init.mode) != 0o755
        or init.uid != 0
        or init.gid != 0
        or init.nlink != 1
        or init.payload != init_payload
    ):
        fail("embedded recovery init does not match its repository source")
    control = entries.get("usr/libexec/rog5-recovery-control")
    expected_size, expected_digest = control_identity
    if (
        control is None
        or len(control.payload) != expected_size
        or hashlib.sha256(control.payload).hexdigest() != expected_digest
    ):
        fail("embedded recovery control binary identity changed")


def parse_key_values(payload: bytes, label: str) -> dict[str, str]:
    try:
        text = payload.decode("ascii")
    except UnicodeError as error:
        raise AdmissionError(f"{label} is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        fail(f"{label} is not canonical text")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line or "=" not in line:
            fail(f"{label} is not canonical key-value text")
        key, value = line.split("=", 1)
        if not key or not value or key in values:
            fail(f"{label} has an invalid or duplicate field")
        values[key] = value
    return values


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_newc(archive: bytes) -> dict[str, NewcEntry]:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(archive)) as stream:
            payload = stream.read(MAX_INITRAMFS_BYTES + 1)
    except (OSError, EOFError) as error:
        raise AdmissionError("recovery initramfs is not valid gzip") from error
    if len(payload) > MAX_INITRAMFS_BYTES:
        fail("recovery initramfs exceeds the decompression bound")
    entries: dict[str, NewcEntry] = {}
    offset = 0
    trailer = False
    while offset < len(payload):
        if payload[offset : offset + 6] not in (b"070701", b"070702"):
            if not any(memoryview(payload)[offset:]):
                break
            fail("recovery initramfs is not newc")
        if offset + 110 > len(payload):
            fail("recovery initramfs has a truncated newc header")
        header = payload[offset : offset + 110]
        try:
            fields = [
                int(header[6 + index * 8 : 14 + index * 8], 16)
                for index in range(13)
            ]
        except ValueError as error:
            raise AdmissionError("recovery initramfs has an invalid header") from error
        mode, uid, gid, nlink = fields[1:5]
        file_size = fields[6]
        name_size = fields[11]
        if name_size < 2:
            fail("recovery initramfs has an invalid entry name")
        name_start = offset + 110
        name_end = name_start + name_size
        encoded_name = payload[name_start:name_end]
        if (
            name_end > len(payload)
            or encoded_name[-1:] != b"\0"
            or b"\0" in encoded_name[:-1]
        ):
            fail("recovery initramfs has a truncated entry name")
        try:
            name = encoded_name[:-1].decode("utf-8")
        except UnicodeError as error:
            raise AdmissionError("recovery initramfs has a non-UTF-8 path") from error
        data_start = align4(name_end)
        data_end = data_start + file_size
        if data_end > len(payload):
            fail("recovery initramfs has truncated entry data")
        offset = align4(data_end)
        if name == "TRAILER!!!":
            trailer = True
            break
        pure = PurePosixPath(name)
        if (
            not name
            or pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != name
            or name in entries
        ):
            fail("recovery initramfs has an unsafe or duplicate path")
        entries[name] = NewcEntry(
            mode,
            uid,
            gid,
            nlink,
            payload[data_start:data_end],
        )
    if not trailer:
        fail("recovery initramfs lacks its newc trailer")
    if any(memoryview(payload)[offset:]):
        fail("recovery initramfs contains a trailing archive member")
    return entries


def verify_recovery_role(
    path: Path,
    mode: str,
    expected_size: int,
    expected_digest: str,
) -> dict[str, NewcEntry]:
    entries = parse_newc(
        read_verified_bytes(
            path,
            "recovery initramfs",
            expected_size=expected_size,
            expected_digest=expected_digest,
        )
    )
    marker = entries.get("etc/rog5/recovery-mode")
    expected_marker = f"{mode}\n".encode("ascii")
    if (
        marker is None
        or not stat.S_ISREG(marker.mode)
        or stat.S_IMODE(marker.mode) != 0o444
        or marker.uid != 0
        or marker.gid != 0
        or marker.nlink != 1
        or marker.payload != expected_marker
    ):
        fail("recovery initramfs mode is not exact")
    control = entries.get("usr/libexec/rog5-recovery-control")
    if (
        control is None
        or not stat.S_ISREG(control.mode)
        or stat.S_IMODE(control.mode) != 0o755
        or control.uid != 0
        or control.gid != 0
        or control.nlink != 1
    ):
        fail("recovery initramfs lacks its control responder")
    mutating = {
        "usr/libexec/rog5-bundle-fetch",
        "usr/libexec/rog5-bundle-verify",
        "etc/rog5/recovery-bundle-ed25519.pub",
        "usr/sbin/kexec",
    }
    if mode == "full-v1":
        if not mutating.issubset(entries):
            fail("execution recovery lacks its exact payload path")
    elif mode == "observation-only-v1":
        if mutating.intersection(entries) or any(
            PurePosixPath(name).name == "kexec" for name in entries
        ):
            fail("observation recovery retains a payload execution path")
        if any(
            name == "run/rog5-bundles" or name.startswith("run/rog5-bundles/")
            for name in entries
        ):
            fail("observation recovery retains bundle state")
    else:
        fail("unknown recovery role")
    if any(
        stat.S_IFMT(entry.mode)
        not in {stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}
        or entry.uid != 0
        or entry.gid != 0
        or entry.nlink < 1
        or stat.S_IMODE(entry.mode) & 0o6000
        for entry in entries.values()
    ):
        fail("recovery initramfs contains an unsafe object")
    return entries


def verify_recovery_derivation(
    execution: dict[str, NewcEntry],
    observer: dict[str, NewcEntry],
) -> None:
    removed = {
        "usr/libexec/rog5-bundle-fetch",
        "usr/libexec/rog5-bundle-verify",
        "etc/rog5/recovery-bundle-ed25519.pub",
        "usr/sbin/kexec",
    }
    if set(observer) != set(execution) - removed:
        fail("observation recovery is not the exact execution-free derivation")
    marker = "etc/rog5/recovery-mode"
    for name, entry in observer.items():
        if name != marker and entry != execution[name]:
            fail("observation recovery changed a shared base entry")


def compare_prefix(raw_fd: int, avb_fd: int, size: int) -> None:
    offset = 0
    while offset < size:
        length = min(1024 * 1024, size - offset)
        if os.pread(raw_fd, length, offset) != os.pread(avb_fd, length, offset):
            fail("AVB payload differs from its raw boot image")
        offset += length


def zero_region(descriptor: int, start: int, end: int, label: str) -> None:
    if start > end:
        fail(f"{label} geometry is invalid")
    offset = start
    while offset < end:
        length = min(1024 * 1024, end - offset)
        block = os.pread(descriptor, length, offset)
        if len(block) != length or any(block):
            fail(f"{label} padding is not zero")
        offset += length


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def verify_boot_v3(
    raw: Path,
    kernel: Path,
    ramdisk: Path,
    raw_identity: tuple[int, str],
    kernel_identity: tuple[int, str],
    ramdisk_identity: tuple[int, str],
    expected_cmdline: str,
) -> None:
    raw_size, raw_digest = raw_identity
    kernel_size_expected, kernel_digest = kernel_identity
    ramdisk_size_expected, ramdisk_digest = ramdisk_identity
    with (
        verified_descriptor(
            raw,
            "raw boot image",
            expected_size=raw_size,
            expected_digest=raw_digest,
        ) as raw_fd,
        verified_descriptor(
            kernel,
            "wrapper Image",
            expected_size=kernel_size_expected,
            expected_digest=kernel_digest,
        ) as kernel_fd,
        verified_descriptor(
            ramdisk,
            "recovery initramfs",
            expected_size=ramdisk_size_expected,
            expected_digest=ramdisk_digest,
        ) as ramdisk_fd,
    ):
        header = os.pread(raw_fd, BOOT_V3_PAGE_SIZE, 0)
        if len(header) != BOOT_V3_PAGE_SIZE or header[:8] != b"ANDROID!":
            fail("raw wrapper is not Android boot-v3")
        kernel_size, ramdisk_size, _os_version, header_size = struct.unpack_from(
            "<4I", header, 8
        )
        header_version = struct.unpack_from("<I", header, 40)[0]
        if (
            header_version != 3
            or header_size != BOOT_V3_HEADER_SIZE
            or any(header[24:40])
            or any(header[BOOT_V3_HEADER_SIZE:BOOT_V3_PAGE_SIZE])
            or kernel_size != kernel_size_expected
            or ramdisk_size != ramdisk_size_expected
        ):
            fail("raw wrapper boot-v3 header is not exact")
        command_line_field = header[44:BOOT_V3_HEADER_SIZE]
        command_line_bytes, separator, trailing = command_line_field.partition(b"\0")
        try:
            command_line = command_line_bytes.decode("ascii")
        except UnicodeError as error:
            raise AdmissionError("raw wrapper command line is not ASCII") from error
        if (
            not separator
            or any(trailing)
            or command_line != expected_cmdline
        ):
            fail("raw wrapper command line is not exact")
        kernel_offset = BOOT_V3_PAGE_SIZE
        ramdisk_offset = kernel_offset + align(kernel_size, BOOT_V3_PAGE_SIZE)
        expected_size = ramdisk_offset + align(ramdisk_size, BOOT_V3_PAGE_SIZE)
        if raw_size != expected_size:
            fail("raw wrapper boot-v3 geometry is not exact")

        def compare_region(
            source_fd: int,
            source_size: int,
            offset: int,
            label: str,
        ) -> None:
            source_offset = 0
            while source_offset < source_size:
                length = min(1024 * 1024, source_size - source_offset)
                if os.pread(source_fd, length, source_offset) != os.pread(
                    raw_fd,
                    length,
                    offset + source_offset,
                ):
                    fail(f"raw wrapper does not embed the exact {label}")
                source_offset += length

        compare_region(kernel_fd, kernel_size, kernel_offset, "wrapper Image")
        compare_region(
            ramdisk_fd,
            ramdisk_size,
            ramdisk_offset,
            "recovery initramfs",
        )
        zero_region(
            raw_fd,
            kernel_offset + kernel_size,
            ramdisk_offset,
            "boot-v3 kernel",
        )
        zero_region(
            raw_fd,
            ramdisk_offset + ramdisk_size,
            expected_size,
            "boot-v3 ramdisk",
        )


def verify_wrapper_config(
    path: Path,
    identity: tuple[int, str],
) -> None:
    payload = read_verified_bytes(
        path,
        "wrapper config",
        expected_size=identity[0],
        expected_digest=identity[1],
    )
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeError as error:
        raise AdmissionError("wrapper config is not ASCII") from error
    for required in (
        "CONFIG_PSTORE=y",
        "CONFIG_PSTORE_CONSOLE=y",
        "CONFIG_PSTORE_PMSG=y",
        "CONFIG_PSTORE_RAM=y",
    ):
        if lines.count(required) != 1:
            fail(f"wrapper config lacks exact {required}")


def verify_unsigned_avb(
    avb: Path,
    raw: Path,
    algorithm: str,
    avb_identity: tuple[int, str],
    raw_identity: tuple[int, str],
) -> None:
    if algorithm != "NONE":
        fail("offline wrapper AVB algorithm is not NONE")
    avb_size, avb_digest = avb_identity
    raw_size, raw_digest = raw_identity
    try:
        with (
            verified_descriptor(
                avb,
                "unsigned AVB wrapper",
                expected_size=avb_size,
                expected_digest=avb_digest,
            ) as avb_fd,
            verified_descriptor(
                raw,
                "raw boot image",
                expected_size=raw_size,
                expected_digest=raw_digest,
            ) as raw_fd,
        ):
            footer = os.pread(avb_fd, 64, avb_size - 64)
            magic, major, minor, original_size, offset, size = struct.unpack(
                "!4s2I3Q28x", footer
            )
            if (
                magic != b"AVBf"
                or (major, minor) != (1, 0)
                or original_size != raw_size
                or offset != original_size
                or size < 256
                or offset + size > avb_size - 64
            ):
                fail("AVB footer is not exact")
            header = os.pread(avb_fd, 256, offset)
            if len(header) != 256 or header[:4] != b"AVB0":
                fail("AVB metadata header is not exact")
            required_major, required_minor = struct.unpack_from("!2I", header, 4)
            authentication_size, auxiliary_size = struct.unpack_from("!2Q", header, 12)
            hash_offset, hash_size = struct.unpack_from("!2Q", header, 32)
            signature_offset, signature_size = struct.unpack_from("!2Q", header, 48)
            public_key_offset, public_key_size = struct.unpack_from("!2Q", header, 64)
            metadata_offset, metadata_size = struct.unpack_from("!2Q", header, 80)
            descriptors_offset, descriptors_size = struct.unpack_from("!2Q", header, 96)
            rollback_index = struct.unpack_from("!Q", header, 112)[0]
            flags, rollback_location = struct.unpack_from("!2I", header, 120)
            release = header[128:175].split(b"\0", 1)[0]
            if (
                (required_major, required_minor) != (1, 0)
                or authentication_size != 0
                or struct.unpack_from("!I", header, 28)[0] != 0
                or size != 256 + authentication_size + auxiliary_size
                or (hash_offset, hash_size) != (0, 0)
                or (signature_offset, signature_size) != (0, 0)
                or public_key_size != 0
                or metadata_size != 0
                or descriptors_offset != 0
                or descriptors_size != public_key_offset
                or descriptors_size != metadata_offset
                or rollback_index != 0
                or flags != 0
                or rollback_location != 0
                or release != b"avbtool 1.4.0"
                or any(header[175:])
            ):
                fail("offline wrapper AVB algorithm is not NONE")
            auxiliary = os.pread(avb_fd, auxiliary_size, offset + 256)
            if len(auxiliary) != auxiliary_size or descriptors_size != 200:
                fail("AVB hash descriptor geometry is not exact")
            descriptor = auxiliary[:descriptors_size]
            try:
                (
                    tag,
                    following,
                    image_size,
                    hash_algorithm,
                    partition_length,
                    salt_length,
                    digest_length,
                    descriptor_flags,
                    reserved,
                ) = struct.unpack("!QQQ32sLLLL60s", descriptor[:132])
            except struct.error as error:
                raise AdmissionError("AVB hash descriptor is malformed") from error
            variable = descriptor[132:]
            partition = variable[:partition_length]
            salt_start = partition_length
            digest_start = salt_start + salt_length
            salt = variable[salt_start:digest_start]
            recorded_digest = variable[digest_start : digest_start + digest_length]
            expected_following = align(
                116 + partition_length + salt_length + digest_length,
                8,
            )
            if (
                tag != 2
                or following != expected_following
                or 16 + following != descriptors_size
                or image_size != raw_size
                or hash_algorithm.rstrip(b"\0") != b"sha256"
                or any(hash_algorithm[len(b"sha256") :])
                or partition != b"boot"
                or partition_length != 4
                or salt_length != 32
                or digest_length != 32
                or descriptor_flags != 0
                or any(reserved)
                or digest_start + digest_length != len(variable)
                or salt != bytes.fromhex(raw_digest)
                or any(auxiliary[descriptors_size:])
            ):
                fail("AVB hash descriptor is not exact")
            calculated = hashlib.sha256(salt)
            raw_offset = 0
            while raw_offset < raw_size:
                block = os.pread(
                    raw_fd,
                    min(1024 * 1024, raw_size - raw_offset),
                    raw_offset,
                )
                if not block:
                    fail("AVB raw payload is truncated")
                calculated.update(block)
                raw_offset += len(block)
            if calculated.digest() != recorded_digest:
                fail("AVB hash descriptor digest is invalid")
            compare_prefix(raw_fd, avb_fd, raw_size)
            zero_region(
                avb_fd,
                offset + size,
                avb_size - 64,
                "AVB partition",
            )
    except (OSError, struct.error) as error:
        raise AdmissionError("AVB footer is not exact") from error


def verify_signature(
    manifest: Path,
    signature: Path,
    key: Path,
    manifest_identity: tuple[int, str],
    signature_identity: tuple[int, str],
    key_identity: tuple[int, str],
) -> None:
    openssl = Path("/usr/bin/openssl")
    try:
        metadata = openssl.lstat()
    except OSError as error:
        raise AdmissionError("fixed OpenSSL verifier is unavailable") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o022
        or not os.access(openssl, os.X_OK)
    ):
        fail("fixed OpenSSL verifier is unavailable")
    manifest_size, manifest_digest = manifest_identity
    signature_size, signature_digest = signature_identity
    key_size, key_digest = key_identity
    with (
        verified_descriptor(
            manifest,
            "execution runtime manifest",
            expected_size=manifest_size,
            expected_digest=manifest_digest,
        ) as manifest_fd,
        verified_descriptor(
            signature,
            "execution runtime signature",
            expected_size=signature_size,
            expected_digest=signature_digest,
        ) as signature_fd,
        verified_descriptor(
            key,
            "execution recovery trust key",
            expected_size=key_size,
            expected_digest=key_digest,
        ) as key_fd,
    ):
        raw_key = read_descriptor(key_fd)
        if len(raw_key) != 32:
            fail("execution recovery trust key is not raw Ed25519")
        with tempfile.NamedTemporaryFile(prefix="rog5-retention-key-") as der:
            der.write(bytes.fromhex("302a300506032b6570032100") + raw_key)
            der.flush()
            result = subprocess.run(
                [
                    str(openssl),
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-keyform",
                    "DER",
                    "-inkey",
                    der.name,
                    "-rawin",
                    "-in",
                    f"/proc/self/fd/{manifest_fd}",
                    "-sigfile",
                    f"/proc/self/fd/{signature_fd}",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(manifest_fd, signature_fd),
            )
    if result.returncode != 0:
        fail("execution runtime signature is invalid")


def verify_candidate_and_bundle(
    repo: Path,
    root: Path,
    execution: dict[str, Any],
    artifacts_path: Path,
) -> tuple[str, str]:
    candidate_path = safe_child(
        repo,
        execution["candidate_path"],
        "tracked execution candidate",
    )
    candidate_sha256 = require_sha256(
        execution["candidate_sha256"],
        "tracked execution candidate SHA-256",
    )
    candidate_size = execution["candidate_size"]
    if (
        not isinstance(candidate_size, int)
        or isinstance(candidate_size, bool)
        or candidate_size <= 0
    ):
        fail("tracked execution candidate size is invalid")
    candidate = read_json(
        candidate_path,
        "tracked execution candidate",
        expected_size=candidate_size,
        expected_digest=candidate_sha256,
        expected_mode=require_mode(
            execution["candidate_mode"],
            "tracked execution candidate mode",
        ),
    )
    candidate_id = require_string(execution["candidate"], "candidate identity")
    require_keys(
        candidate,
        {
            "format",
            "candidate",
            "status",
            "authority",
            "bundle",
            "profile",
            "target_id",
            "target_release",
            "rollback_timeout",
            "target_timeout",
            "a660_command_manifest_sha256",
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_tree_entries",
            "root_subtree",
            "artifacts",
        },
        "tracked execution candidate",
    )
    if (
        candidate.get("format") != "rog5-recovery-candidate-v1"
        or candidate.get("candidate") != candidate_id
        or candidate.get("status") != "offline"
        or candidate.get("authority") != "none"
        or candidate.get("bundle") != candidate_id
        or candidate.get("target_id") != candidate_id
        or candidate.get("profile") != "diagnostic-initramfs-v1"
    ):
        fail("tracked execution candidate is not authority-free and exact")

    inventory = read_safe_file(
        artifacts_path,
        "artifact inventory",
        expected_mode=require_mode(
            execution["artifact_inventory_mode"],
            "artifact inventory mode",
        ),
    ).decode(
        "utf-8", errors="strict"
    )
    rows = [line.split("\t") for line in inventory.splitlines()]
    if not rows or rows[0] != ["name", "size", "sha256", "role", "tracked"]:
        fail("artifact inventory header is not exact")
    matches = [row for row in rows[1:] if row and row[0] == execution["candidate_path"]]
    if len(matches) != 1 or len(matches[0]) != 5:
        fail("tracked execution candidate inventory is not unique")
    row = matches[0]
    if (
        row[1] != str(candidate_size)
        or row[2] != candidate_sha256
        or not row[3].startswith("tracked ")
        or "consumed" in row[3]
        or row[4] != "yes"
    ):
        fail("tracked execution candidate inventory is not current")

    record_a, _record_b, _record_digest = verify_pair(
        root,
        execution["candidate_record"],
        "execution candidate record",
    )
    manifest_a, manifest_b, manifest_sha256 = verify_pair(
        root,
        execution["runtime_manifest"],
        "execution runtime manifest",
    )
    signature_a, signature_b, _signature_digest = verify_pair(
        root,
        execution["runtime_signature"],
        "execution runtime signature",
    )
    trust_key, trust_sha256 = verify_single(
        root,
        execution["trust_key"],
        "execution recovery trust key",
    )
    require_absent_child(root, execution["private_key_path"], "private signing key")

    record_identity = expected_identity(
        execution["candidate_record"],
        "execution candidate record",
        pair=True,
    )
    manifest_identity = expected_identity(
        execution["runtime_manifest"],
        "execution runtime manifest",
        pair=True,
    )
    signature_identity = expected_identity(
        execution["runtime_signature"],
        "execution runtime signature",
        pair=True,
    )
    trust_identity = expected_identity(
        execution["trust_key"],
        "execution recovery trust key",
        pair=False,
    )
    record = parse_key_values(
        read_verified_bytes(
            record_a,
            "execution candidate record",
            expected_size=record_identity[0],
            expected_digest=record_identity[1],
        ),
        "execution candidate record",
    )
    if set(record) != {
        "format",
        "candidate",
        "status",
        "authority",
        "bundle",
        "manifest_sha256",
        "trust_key_sha256",
    } or record != {
        "format": "rog5-prepared-candidate-v1",
        "candidate": candidate_id,
        "status": "offline",
        "authority": "none",
        "bundle": candidate_id,
        "manifest_sha256": manifest_sha256,
        "trust_key_sha256": trust_sha256,
    }:
        fail("execution candidate record is not exact and authority-free")

    manifest = parse_key_values(
        read_verified_bytes(
            manifest_a,
            "execution runtime manifest",
            expected_size=manifest_identity[0],
            expected_digest=manifest_identity[1],
        ),
        "execution runtime manifest",
    )
    if set(manifest) != {
        "format",
        "bundle",
        "profile",
        "kernel_size",
        "kernel_sha256",
        "dtb_size",
        "dtb_sha256",
        "initramfs_size",
        "initramfs_sha256",
        "target_id",
        "target_release",
        "rollback_timeout",
        "target_timeout",
        "a660_command_manifest_sha256",
        "root_generation",
        "root_tree_sha256",
        "root_seal_sha256",
        "root_tree_entries",
        "root_subtree",
    }:
        fail("execution runtime manifest fields are not exact")
    bound_fields = (
        "profile",
        "target_id",
        "target_release",
        "rollback_timeout",
        "target_timeout",
        "a660_command_manifest_sha256",
        "root_generation",
        "root_tree_sha256",
        "root_seal_sha256",
        "root_tree_entries",
        "root_subtree",
    )
    if any(
        not isinstance(candidate.get(field), str) or not candidate[field]
        for field in bound_fields
    ):
        fail("execution candidate binding fields are incomplete")
    if (
        manifest.get("format") != "rog5-recovery-bundle-v2"
        or manifest.get("bundle") != candidate_id
        or any(manifest.get(field) != candidate[field] for field in bound_fields)
    ):
        fail("execution runtime manifest no longer binds the candidate")

    bundle_roots = tuple(
        safe_root(
            safe_child(root, execution[key], label),
            label,
        )
        for key, label in (
            ("bundle_a", "execution bundle A"),
            ("bundle_b", "execution bundle B"),
        )
    )
    if bundle_roots[0] == bundle_roots[1]:
        fail("execution bundle roots are not distinct")
    if (
        manifest_a != bundle_roots[0] / "manifest"
        or manifest_b != bundle_roots[1] / "manifest"
        or signature_a != bundle_roots[0] / "manifest.sig"
        or signature_b != bundle_roots[1] / "manifest.sig"
    ):
        fail("execution manifest and signature paths are not bundle-owned")
    expected_bundle_inventory = [
        "Image:file",
        "board.dtb:file",
        "initramfs.cpio.gz:file",
        "manifest.sig:file",
        "manifest:file",
    ]
    for bundle_root, label in zip(
        bundle_roots,
        ("execution bundle A", "execution bundle B"),
        strict=True,
    ):
        verify_directory_inventory(
            bundle_root,
            expected_bundle_inventory,
            f"{label} inventory",
        )
    artifacts = candidate.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
        "Image",
        "board.dtb",
        "initramfs.cpio.gz",
    }:
        fail("execution candidate artifact set changed")
    manifest_names = {
        "Image": ("kernel_size", "kernel_sha256"),
        "board.dtb": ("dtb_size", "dtb_sha256"),
        "initramfs.cpio.gz": ("initramfs_size", "initramfs_sha256"),
    }
    for name, fields in manifest_names.items():
        artifact = require_keys(
            artifacts[name],
            {"path", "size", "sha256"},
            f"candidate {name}",
        )
        if (
            manifest.get(fields[0]) != str(artifact["size"])
            or manifest.get(fields[1]) != artifact["sha256"]
        ):
            fail(f"execution manifest does not bind {name}")
        first = safe_child(bundle_roots[0], name, f"bundle A {name}")
        second = safe_child(bundle_roots[1], name, f"bundle B {name}")
        verify_file(
            first,
            artifact["size"],
            artifact["sha256"],
            "0400",
            f"bundle A {name}",
        )
        verify_file(
            second,
            artifact["size"],
            artifact["sha256"],
            "0400",
            f"bundle B {name}",
        )

    verify_signature(
        manifest_a,
        signature_a,
        trust_key,
        manifest_identity,
        signature_identity,
        trust_identity,
    )
    verify_signature(
        manifest_b,
        signature_b,
        trust_key,
        manifest_identity,
        signature_identity,
        trust_identity,
    )
    return candidate_sha256, manifest_sha256


def verify_policy(
    policy_path: Path,
    required_allow_rows: Any,
    expected_mode: int,
) -> int:
    expected_allows = {
        (
            "build/observation-recovery-mainline-udc-v11-generation10-"
            "20260811-r1/repack/stable-recovery-a.avb.img",
            "one exact NFS-xattr retention observation recovery; RAM-only; "
            "externally consumed exact claim required; never flash or retry "
            "after entry",
        ),
        (
            "build/headless-core-v21-generation21-20260812-r1/repack/"
            "stable-recovery-a.avb.img",
            "one exact headless-core Arch SSH recovery with power-key "
            "indicator; RAM-only; externally consumed exact claim required; "
            "never flash or retry after entry",
        ),
        (
            "build/persistent-root-qmp-ufs-phy-creation-stage-v26-generation47-20260813-r1/"
            "repack/stable-recovery-a.avb.img",
            "one exact SM8350 QMP-UFS PHY creation discriminator with bounded "
            "recovery transfer and exact "
            "target-originated post-insmod proof; "
            "RAM-only; externally consumed exact claim required; never flash "
            "or retry after entry",
        ),
    }
    if required_allow_rows != len(expected_allows):
        fail("review must require the exact retention-cycle admissions")
    try:
        text = read_safe_file(
            policy_path,
            "temporary-boot policy",
            expected_mode=expected_mode,
        ).decode("utf-8")
    except UnicodeError as error:
        raise AdmissionError("temporary-boot policy is not UTF-8") from error
    rows = [line.split("\t") for line in text.splitlines()]
    if not rows or rows[0] != ["name", "status", "basis"]:
        fail("temporary-boot policy header is not exact")
    allow_rows: list[tuple[str, str]] = []
    for row in rows[1:]:
        if len(row) != 3 or not all(row):
            fail("temporary-boot policy row is malformed")
        if row[1] == "allow":
            allow_rows.append((row[0], row[2]))
        elif row[1] not in {"deny", "revoked"}:
            fail("temporary-boot policy status is unknown")
    if len(allow_rows) != required_allow_rows or set(allow_rows) != expected_allows:
        fail("temporary-boot policy does not contain exact retention admissions")
    return len(allow_rows)


def verify_observer_evidence(
    path: Path,
    evidence_identity: tuple[int, str],
    initramfs_identity: tuple[int, str],
    config_identity: tuple[int, str],
    image_identity: tuple[int, str],
    raw_identity: tuple[int, str],
    avb_identity: tuple[int, str],
) -> None:
    payload = read_verified_bytes(
        path,
        "observer wrapper evidence",
        expected_size=evidence_identity[0],
        expected_digest=evidence_identity[1],
    )
    try:
        text = payload.decode("ascii")
    except UnicodeError as error:
        raise AdmissionError("observer wrapper evidence is not ASCII") from error
    lines = text.splitlines()
    if not lines or lines[-1] != (
        "PASS observation-only clean-twin wrapper evidence is exact and offline-only"
    ):
        fail("observer wrapper evidence result is not exact")
    values = parse_key_values(
        ("\n".join(lines[:-1]) + "\n").encode("ascii"),
        "observer wrapper evidence",
    )
    required = {
        "format": "rog5-observation-recovery-wrapper-evidence-v1",
        "observer_initramfs_size": str(initramfs_identity[0]),
        "observer_initramfs_sha256": initramfs_identity[1],
        "wrapper_config_size": str(config_identity[0]),
        "wrapper_config_sha256": config_identity[1],
        "wrapper_image_size": str(image_identity[0]),
        "wrapper_image_sha256": image_identity[1],
        "raw_boot_size": str(raw_identity[0]),
        "raw_boot_sha256": raw_identity[1],
        "unsigned_avb_size": str(avb_identity[0]),
        "unsigned_avb_sha256": avb_identity[1],
        "ramoops_mem_address": "0x9b800000",
        "ramoops_mem_size": "0x400000",
        "authority": "none",
        "candidate": "none",
        "boot_authority": "none",
        "retention": "unproven",
    }
    if values != required:
        fail("observer wrapper evidence does not bind the offline role")


def verify(
    profile_path: Path,
    repo: Path,
    execution_root: Path,
    observer_root: Path,
    artifacts_path: Path,
    policy_path: Path,
    *,
    enforce_repository_layout: bool,
) -> str:
    repo = safe_root(repo, "repository root")
    execution_root = safe_root(execution_root, "execution evidence root")
    observer_root = safe_root(observer_root, "observer evidence root")
    with ExitStack() as stack:
        root_descriptors = {
            root: stack.enter_context(verified_directory_descriptor(root, label))
            for root, label in (
                (repo, "repository root"),
                (execution_root, "execution evidence root"),
                (observer_root, "observer evidence root"),
            )
        }
        token = ACTIVE_ROOT_IDENTITIES.set(
            {
                root: stable_directory_metadata(os.fstat(descriptor))
                for root, descriptor in root_descriptors.items()
            }
        )
        try:
            return verify_pinned(
                profile_path,
                repo,
                execution_root,
                observer_root,
                artifacts_path,
                policy_path,
                enforce_repository_layout=enforce_repository_layout,
            )
        finally:
            ACTIVE_ROOT_IDENTITIES.reset(token)


def verify_pinned(
    profile_path: Path,
    repo: Path,
    execution_root: Path,
    observer_root: Path,
    artifacts_path: Path,
    policy_path: Path,
    *,
    enforce_repository_layout: bool,
) -> str:
    if execution_root == observer_root:
        fail("execution and observer evidence roots are not distinct")
    for child, parent in (
        (execution_root, observer_root),
        (observer_root, execution_root),
    ):
        try:
            child.relative_to(parent)
        except ValueError:
            continue
        fail("execution and observer evidence roots overlap")
    if enforce_repository_layout:
        build_root = repo / "build"
        git = Path("/usr/bin/git")
        try:
            git_metadata = git.lstat()
        except OSError as error:
            raise AdmissionError("fixed Git verifier is unavailable") from error
        if (
            not stat.S_ISREG(git_metadata.st_mode)
            or git_metadata.st_uid != 0
            or stat.S_IMODE(git_metadata.st_mode) & 0o022
            or not os.access(git, os.X_OK)
        ):
            fail("fixed Git verifier is unavailable")
        for root, label in (
            (execution_root, "execution evidence root"),
            (observer_root, "observer evidence root"),
        ):
            try:
                root.relative_to(build_root)
            except ValueError:
                fail(f"{label} must remain below the ignored build directory")
            result = subprocess.run(
                [str(git), "-C", str(repo), "check-ignore", "-q", str(root)],
                check=False,
            )
            if result.returncode != 0:
                fail(f"{label} is not ignored by Git")

    profile = read_json(
        profile_path,
        "retention-cycle profile",
        expected_mode=0o644 if enforce_repository_layout else None,
    )
    require_keys(
        profile,
        {
            "format",
            "profile",
            "state",
            "authority",
            "boot_authority",
            "retention",
            "missing_pstore",
            "evidence_owner",
            "recovery_cmdline",
            "recovery_inputs",
            "sequence",
            "root_inventory",
            "execution",
            "observer",
            "claims",
            "policy",
        },
        "retention-cycle profile",
    )
    if (
        profile["format"] != "rog5-retention-cycle-admission-review-v1"
        or profile["profile"] != "host-rendezvous-v3-observer-v1"
        or profile["state"] != "hold"
        or profile["authority"] != "none"
        or profile["boot_authority"] != "none"
        or profile["retention"] != "unproven"
        or profile["missing_pstore"] != "inconclusive"
        or profile["evidence_owner"] != "verifier-euid"
        or profile["recovery_cmdline"] != EXPECTED_RECOVERY_CMDLINE
        or tuple(profile["sequence"]) != EXPECTED_SEQUENCE
    ):
        fail("retention-cycle profile weakens the HOLD boundary")

    (
        recovery_init_payload,
        recovery_control_identity,
        _recovery_control_mode,
        recovery_init_sha256,
        recovery_control_source_sha256,
        _recovery_control_build,
    ) = verify_recovery_inputs(repo, profile["recovery_inputs"])

    execution = require_keys(
        profile["execution"],
        {
            "role",
            "candidate_path",
            "candidate_size",
            "candidate_sha256",
            "candidate_mode",
            "artifact_inventory_mode",
            "candidate",
            "candidate_record",
            "bundle_a",
            "bundle_b",
            "runtime_manifest",
            "runtime_signature",
            "trust_key",
            "private_key_path",
            "trust_class",
            "recovery_mode",
            "avb_algorithm",
            "recovery_initramfs",
            "wrapper_config",
            "wrapper_image",
            "raw_boot",
            "unsigned_avb",
            "claim",
        },
        "execution role",
    )
    observer = require_keys(
        profile["observer"],
        {
            "role",
            "host_action",
            "recovery_mode",
            "avb_algorithm",
            "wrapper_evidence",
            "recovery_initramfs",
            "wrapper_config",
            "wrapper_image",
            "raw_boot",
            "unsigned_avb",
            "claim",
        },
        "observer role",
    )
    if (
        execution["role"] != "target-execution-v1"
        or execution["trust_class"] != "production-project"
        or execution["recovery_mode"] != "full-v1"
        or execution["avb_algorithm"] != "NONE"
        or execution["claim"] != "unissued"
        or observer["role"] != "observation-only-v1"
        or observer["host_action"] != "postmortem-status"
        or observer["recovery_mode"] != "observation-only-v1"
        or observer["avb_algorithm"] != "NONE"
        or observer["claim"] != "unissued"
    ):
        fail("execution and observation roles are not fail-closed")

    root_inventory = require_keys(
        profile["root_inventory"],
        {"execution", "observer"},
        "evidence-root inventory",
    )
    verify_directory_inventory(
        execution_root,
        root_inventory["execution"],
        "execution evidence-root inventory",
    )
    verify_directory_inventory(
        observer_root,
        root_inventory["observer"],
        "observer evidence-root inventory",
    )

    candidate_sha256, manifest_sha256 = verify_candidate_and_bundle(
        repo,
        execution_root,
        execution,
        artifacts_path,
    )
    execution_initramfs_a, _execution_initramfs_b, execution_initramfs = verify_pair(
        execution_root,
        execution["recovery_initramfs"],
        "execution recovery initramfs",
    )
    _execution_config_a, _execution_config_b, execution_config = verify_pair(
        execution_root,
        execution["wrapper_config"],
        "execution wrapper config",
    )
    execution_image_a, _execution_image_b, execution_image = verify_pair(
        execution_root,
        execution["wrapper_image"],
        "execution wrapper Image",
    )
    execution_raw_a, _execution_raw_b, execution_raw = verify_pair(
        execution_root,
        execution["raw_boot"],
        "execution raw boot",
    )
    execution_avb_a, _execution_avb_b, execution_avb = verify_pair(
        execution_root,
        execution["unsigned_avb"],
        "execution unsigned AVB",
    )
    execution_initramfs_identity = expected_identity(
        execution["recovery_initramfs"],
        "execution recovery initramfs",
        pair=True,
    )
    execution_image_identity = expected_identity(
        execution["wrapper_image"],
        "execution wrapper Image",
        pair=True,
    )
    execution_raw_identity = expected_identity(
        execution["raw_boot"],
        "execution raw boot",
        pair=True,
    )
    execution_avb_identity = expected_identity(
        execution["unsigned_avb"],
        "execution unsigned AVB",
        pair=True,
    )
    execution_config_identity = expected_identity(
        execution["wrapper_config"],
        "execution wrapper config",
        pair=True,
    )
    verify_wrapper_config(_execution_config_a, execution_config_identity)
    execution_entries = verify_recovery_role(
        execution_initramfs_a,
        "full-v1",
        *execution_initramfs_identity,
    )
    verify_embedded_recovery_inputs(
        execution_entries,
        recovery_init_payload,
        recovery_control_identity,
    )
    verify_boot_v3(
        execution_raw_a,
        execution_image_a,
        execution_initramfs_a,
        execution_raw_identity,
        execution_image_identity,
        execution_initramfs_identity,
        profile["recovery_cmdline"],
    )
    verify_unsigned_avb(
        execution_avb_a,
        execution_raw_a,
        execution["avb_algorithm"],
        execution_avb_identity,
        execution_raw_identity,
    )

    evidence_path, _evidence_sha256 = verify_single(
        observer_root,
        observer["wrapper_evidence"],
        "observer wrapper evidence",
    )
    observer_initramfs_a, _observer_initramfs_b, observer_initramfs = verify_pair(
        observer_root,
        observer["recovery_initramfs"],
        "observer recovery initramfs",
    )
    _observer_config_a, _observer_config_b, observer_config = verify_pair(
        observer_root,
        observer["wrapper_config"],
        "observer wrapper config",
    )
    observer_image_a, _observer_image_b, observer_image = verify_pair(
        observer_root,
        observer["wrapper_image"],
        "observer wrapper Image",
    )
    observer_raw_a, _observer_raw_b, observer_raw = verify_pair(
        observer_root,
        observer["raw_boot"],
        "observer raw boot",
    )
    observer_avb_a, _observer_avb_b, observer_avb = verify_pair(
        observer_root,
        observer["unsigned_avb"],
        "observer unsigned AVB",
    )
    evidence_identity = expected_identity(
        observer["wrapper_evidence"],
        "observer wrapper evidence",
        pair=False,
    )
    observer_initramfs_identity = expected_identity(
        observer["recovery_initramfs"],
        "observer recovery initramfs",
        pair=True,
    )
    observer_config_identity = expected_identity(
        observer["wrapper_config"],
        "observer wrapper config",
        pair=True,
    )
    observer_image_identity = expected_identity(
        observer["wrapper_image"],
        "observer wrapper Image",
        pair=True,
    )
    observer_raw_identity = expected_identity(
        observer["raw_boot"],
        "observer raw boot",
        pair=True,
    )
    observer_avb_identity = expected_identity(
        observer["unsigned_avb"],
        "observer unsigned AVB",
        pair=True,
    )
    observer_entries = verify_recovery_role(
        observer_initramfs_a,
        "observation-only-v1",
        *observer_initramfs_identity,
    )
    verify_embedded_recovery_inputs(
        observer_entries,
        recovery_init_payload,
        recovery_control_identity,
    )
    verify_boot_v3(
        observer_raw_a,
        observer_image_a,
        observer_initramfs_a,
        observer_raw_identity,
        observer_image_identity,
        observer_initramfs_identity,
        profile["recovery_cmdline"],
    )
    verify_unsigned_avb(
        observer_avb_a,
        observer_raw_a,
        observer["avb_algorithm"],
        observer_avb_identity,
        observer_raw_identity,
    )
    verify_observer_evidence(
        evidence_path,
        evidence_identity,
        observer_initramfs_identity,
        observer_config_identity,
        observer_image_identity,
        observer_raw_identity,
        observer_avb_identity,
    )
    verify_recovery_derivation(execution_entries, observer_entries)

    for label, first, second in (
        ("recovery initramfs", execution_initramfs, observer_initramfs),
        ("wrapper Image", execution_image, observer_image),
        ("raw boot", execution_raw, observer_raw),
        ("AVB wrapper", execution_avb, observer_avb),
    ):
        if first == second:
            fail(f"execution and observer {label} identities are not distinct")
    if execution_config != observer_config:
        fail("execution and observer wrappers do not share the reviewed config")

    claims = require_keys(
        profile["claims"],
        {
            "consumer",
            "consumer_size",
            "consumer_sha256",
            "consumer_mode",
            "execution",
            "observer",
            "sequence_reference",
            "transaction_fixture",
            "adapter_fixture",
            "executor_contract",
            "executor_boundary",
            "executor_runtime",
            "executor_descriptor_fixture",
            "issuance_requirement",
            "reuse",
        },
        "claim policy",
    )
    if (
        claims["consumer"] != "scripts/host/consume-exact-boot-claim.py"
        or claims["execution"] != "not-defined"
        or claims["observer"] != "not-defined"
        or claims["issuance_requirement"] != "distinct-exact-records"
        or claims["reuse"] != "forbidden"
    ):
        fail("one-use claim policy is not exact")
    sequence_reference = require_keys(
        claims["sequence_reference"],
        set(EXPECTED_SEQUENCE_REFERENCE),
        "sequence reference contract",
    )
    if sequence_reference != EXPECTED_SEQUENCE_REFERENCE:
        fail("sequence reference contract is not exact")
    reference_path = safe_child(
        repo,
        sequence_reference["path"],
        "sequence reference path",
    )
    read_verified_bytes(
        reference_path,
        "sequence reference",
        expected_size=sequence_reference["size"],
        expected_digest=require_sha256(
            sequence_reference["sha256"],
            "sequence reference SHA-256",
        ),
        expected_mode=require_mode(
            sequence_reference["mode"],
            "sequence reference mode",
        ),
    )
    transaction_fixture = require_keys(
        claims["transaction_fixture"],
        set(EXPECTED_TRANSACTION_FIXTURE),
        "transaction fixture contract",
    )
    if transaction_fixture != EXPECTED_TRANSACTION_FIXTURE:
        fail("transaction fixture contract is not exact")
    transaction_path = safe_child(
        repo,
        transaction_fixture["path"],
        "transaction fixture path",
    )
    read_verified_bytes(
        transaction_path,
        "transaction fixture",
        expected_size=transaction_fixture["size"],
        expected_digest=require_sha256(
            transaction_fixture["sha256"],
            "transaction fixture SHA-256",
        ),
        expected_mode=require_mode(
            transaction_fixture["mode"],
            "transaction fixture mode",
        ),
    )
    adapter_fixture = require_keys(
        claims["adapter_fixture"],
        set(EXPECTED_ADAPTER_FIXTURE),
        "adapter fixture contract",
    )
    if (
        adapter_fixture != EXPECTED_ADAPTER_FIXTURE
        or adapter_fixture["journal_sha256"]
        != transaction_fixture["sha256"]
        or adapter_fixture["cycle_sha256"]
        != sequence_reference["cycle_sha256"]
    ):
        fail("adapter fixture contract is not exact")
    adapter_path = safe_child(
        repo,
        adapter_fixture["path"],
        "adapter fixture path",
    )
    read_verified_bytes(
        adapter_path,
        "adapter fixture",
        expected_size=adapter_fixture["size"],
        expected_digest=require_sha256(
            adapter_fixture["sha256"],
            "adapter fixture SHA-256",
        ),
        expected_mode=require_mode(
            adapter_fixture["mode"],
            "adapter fixture mode",
        ),
    )
    executor_contract = require_keys(
        claims["executor_contract"],
        set(EXPECTED_EXECUTOR_CONTRACT),
        "executor contract",
    )
    if (
        executor_contract != EXPECTED_EXECUTOR_CONTRACT
        or executor_contract["adapter_sha256"]
        != adapter_fixture["sha256"]
    ):
        fail("executor contract is not exact")
    executor_contract_path = safe_child(
        repo,
        executor_contract["path"],
        "executor contract path",
    )
    read_verified_bytes(
        executor_contract_path,
        "executor contract",
        expected_size=executor_contract["size"],
        expected_digest=require_sha256(
            executor_contract["sha256"],
            "executor contract SHA-256",
        ),
        expected_mode=require_mode(
            executor_contract["mode"],
            "executor contract mode",
        ),
    )
    executor_boundary = require_keys(
        claims["executor_boundary"],
        set(EXPECTED_EXECUTOR_BOUNDARY),
        "executor boundary",
    )
    if (
        executor_boundary != EXPECTED_EXECUTOR_BOUNDARY
        or executor_boundary["executor_contract_sha256"]
        != executor_contract["sha256"]
    ):
        fail("executor boundary is not exact")
    executor_boundary_path = safe_child(
        repo,
        executor_boundary["path"],
        "executor boundary path",
    )
    read_verified_bytes(
        executor_boundary_path,
        "executor boundary",
        expected_size=executor_boundary["size"],
        expected_digest=require_sha256(
            executor_boundary["sha256"],
            "executor boundary SHA-256",
        ),
        expected_mode=require_mode(
            executor_boundary["mode"],
            "executor boundary mode",
        ),
    )
    executor_runtime = require_keys(
        claims["executor_runtime"],
        set(EXPECTED_EXECUTOR_RUNTIME),
        "executor runtime closure",
    )
    if (
        executor_runtime != EXPECTED_EXECUTOR_RUNTIME
        or executor_runtime["executor_boundary_sha256"]
        != executor_boundary["sha256"]
        or executor_runtime["transaction_sha256"]
        != transaction_fixture["sha256"]
    ):
        fail("executor runtime closure is not exact")
    executor_runtime_path = safe_child(
        repo,
        executor_runtime["path"],
        "executor runtime closure path",
    )
    read_verified_bytes(
        executor_runtime_path,
        "executor runtime closure",
        expected_size=executor_runtime["size"],
        expected_digest=require_sha256(
            executor_runtime["sha256"],
            "executor runtime closure SHA-256",
        ),
        expected_mode=require_mode(
            executor_runtime["mode"],
            "executor runtime closure mode",
        ),
    )
    descriptor_fixture = require_keys(
        claims["executor_descriptor_fixture"],
        set(EXPECTED_EXECUTOR_DESCRIPTOR_FIXTURE),
        "executor descriptor fixture",
    )
    if (
        descriptor_fixture != EXPECTED_EXECUTOR_DESCRIPTOR_FIXTURE
        or descriptor_fixture["executor_runtime_sha256"]
        != executor_runtime["sha256"]
    ):
        fail("executor descriptor fixture is not exact")
    descriptor_runner_path = safe_child(
        repo,
        descriptor_fixture["runner_path"],
        "executor descriptor runner path",
    )
    read_verified_bytes(
        descriptor_runner_path,
        "executor descriptor runner",
        expected_size=descriptor_fixture["runner_size"],
        expected_digest=require_sha256(
            descriptor_fixture["runner_sha256"],
            "executor descriptor runner SHA-256",
        ),
        expected_mode=require_mode(
            descriptor_fixture["runner_mode"],
            "executor descriptor runner mode",
        ),
    )
    descriptor_probe_path = safe_child(
        repo,
        descriptor_fixture["probe_path"],
        "executor descriptor probe path",
    )
    read_verified_bytes(
        descriptor_probe_path,
        "executor descriptor probe",
        expected_size=descriptor_fixture["probe_size"],
        expected_digest=require_sha256(
            descriptor_fixture["probe_sha256"],
            "executor descriptor probe SHA-256",
        ),
        expected_mode=require_mode(
            descriptor_fixture["probe_mode"],
            "executor descriptor probe mode",
        ),
    )
    consumer = safe_child(repo, claims["consumer"], "generic claim consumer")
    consumer_size = claims["consumer_size"]
    if (
        not isinstance(consumer_size, int)
        or isinstance(consumer_size, bool)
        or consumer_size <= 0
    ):
        fail("generic claim consumer size is invalid")
    consumer_digest = require_sha256(
        claims["consumer_sha256"],
        "generic claim consumer SHA-256",
    )
    consumer_source = read_verified_bytes(
        consumer,
        "generic claim consumer",
        expected_size=consumer_size,
        expected_digest=consumer_digest,
        expected_mode=require_mode(
            claims["consumer_mode"],
            "generic claim consumer mode",
        ),
    )
    try:
        consumer_tree = ast.parse(consumer_source, filename=str(consumer))
    except (SyntaxError, UnicodeError) as error:
        raise AdmissionError("generic claim consumer cannot be inspected") from error
    claims_assignments = [
        node
        for node in consumer_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CLAIMS"
            for target in node.targets
        )
    ]
    if len(claims_assignments) != 1:
        fail("generic claim consumer registry is not exact")
    claims_expression = claims_assignments[0].value
    if (
        not isinstance(claims_expression, ast.Dict)
        or len(claims_expression.keys) != len(EXPECTED_CLAIMS)
    ):
        fail("generic claim consumer registry is not exact")
    try:
        registered_claims = ast.literal_eval(claims_expression)
        literal_profiles = [ast.literal_eval(key) for key in claims_expression.keys]
    except (ValueError, TypeError) as error:
        raise AdmissionError("generic claim consumer registry is not exact") from error
    if (
        not isinstance(registered_claims, dict)
        or registered_claims != EXPECTED_CLAIMS
        or any(not isinstance(key, str) for key in registered_claims)
        or any(not isinstance(value, bytes) for value in registered_claims.values())
        or any(not isinstance(profile_name, str) for profile_name in literal_profiles)
        or len(set(literal_profiles)) != len(literal_profiles)
    ):
        fail("generic claim consumer registry is not exact")
    canonical_assignments = {claims_assignments[0]}
    for node in consumer_tree.body:
        value = getattr(node, "value", None)
        if (
            node not in canonical_assignments
            and isinstance(value, ast.AST)
            and any(
                isinstance(child, ast.Name)
                and child.id == "CLAIMS"
                for child in ast.walk(value)
            )
            and isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        ):
            fail("generic claim consumer registry is aliased or rebound")
    for node in ast.walk(consumer_tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "CLAIMS"
        ):
            fail("generic claim consumer registry is mutated after definition")
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = list(node.targets)
        for target in targets:
            if (
                (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "CLAIMS"
                )
                or (
                    isinstance(target, ast.Name)
                    and target.id == "CLAIMS"
                    and node not in canonical_assignments
                )
            ):
                fail("generic claim consumer registry is mutated after definition")
    if profile["profile"] in registered_claims:
        fail("HOLD profile already has a consumable boot claim")

    policy = require_keys(
        profile["policy"],
        {"path", "mode", "required_allow_rows"},
        "temporary-boot policy contract",
    )
    expected_policy = safe_child(repo, policy["path"], "profile policy path")
    if expected_policy != policy_path:
        fail("temporary-boot policy path is not repository-owned")
    allow_rows = verify_policy(
        policy_path,
        policy["required_allow_rows"],
        require_mode(policy["mode"], "temporary-boot policy mode"),
    )

    return "\n".join(
        (
            "format=rog5-retention-cycle-admission-review-v1",
            f"profile={profile['profile']}",
            f"execution_candidate_sha256={candidate_sha256}",
            f"execution_runtime_manifest_sha256={manifest_sha256}",
            f"execution_recovery_avb_sha256={execution_avb}",
            f"observer_recovery_avb_sha256={observer_avb}",
            f"recovery_init_sha256={recovery_init_sha256}",
            f"recovery_control_source_sha256={recovery_control_source_sha256}",
            f"recovery_control_binary_sha256={recovery_control_identity[1]}",
            f"sequence_reference_sha256={sequence_reference['sha256']}",
            f"transaction_fixture_sha256={transaction_fixture['sha256']}",
            f"adapter_fixture_sha256={adapter_fixture['sha256']}",
            f"executor_contract_sha256={executor_contract['sha256']}",
            f"executor_boundary_sha256={executor_boundary['sha256']}",
            f"executor_runtime_sha256={executor_runtime['sha256']}",
            "executor_descriptor_runner_sha256="
            f"{descriptor_fixture['runner_sha256']}",
            "executor_descriptor_probe_sha256="
            f"{descriptor_fixture['probe_sha256']}",
            f"cycle_sha256={sequence_reference['cycle_sha256']}",
            "transaction_fixture=offline-only",
            "adapter_fixture=callback-only",
            "executor_contract=pure-offline-only",
            "executor_boundary=six-decodable-two-hold-gates",
            "executor_runtime=offline-fresh-pipe-adapter-ineligible",
            "fixture_descriptor_execution=held-fd-proven-adapter-ineligible",
            "production_descriptor_execution=unproven",
            "fallback_boot_result=guarded-producer-defined",
            "draft_claims=unregistered",
            f"temporary_boot_allow_rows={allow_rows}",
            "execution_claim=not-defined",
            "observer_claim=not-defined",
            "authority=none",
            "boot_authority=none",
            "retention=unproven",
            "missing_pstore=inconclusive",
            "recommendation=HOLD",
            "PASS exact target/observer retention-cycle review remains authority-free",
        )
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: verify-retention-cycle-admission.py "
            "EXECUTION_EVIDENCE_ROOT OBSERVER_EVIDENCE_ROOT",
            file=sys.stderr,
        )
        return 2
    try:
        report = verify(
            PROFILE,
            REPO,
            Path(argv[1]).resolve(strict=True),
            Path(argv[2]).resolve(strict=True),
            ARTIFACTS,
            REPO / "manifests/temporary-boot-images.tsv",
            enforce_repository_layout=True,
        )
    except (AdmissionError, OSError, UnicodeError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
