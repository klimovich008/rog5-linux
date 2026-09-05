#!/usr/bin/env python3
"""Exact identities for one NFS-xattr execution/observer cycle."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


RETENTION_PROFILE = "host-rendezvous-v12-nfs-xattr-observer-v1"
CANDIDATE = "headless-netroot-early-diag-v2"
MANIFEST_SHA256 = (
    "325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854"
)
EXECUTION_RECOVERY_PROFILE = (
    "retention-host-rendezvous-v12-nfs-xattr-execution-v1"
)
OBSERVER_RECOVERY_PROFILE = (
    "retention-host-rendezvous-v12-nfs-xattr-observer-v1"
)
EXECUTION_RECOVERY_SHA256 = (
    "f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2"
)
OBSERVER_RECOVERY_SHA256 = (
    "9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69"
)
POSTMORTEM_CLASSIFICATIONS = frozenset(
    {
        "UNAVAILABLE",
        "NO_RECORDS",
        "NO_MARKER",
        "AMBIGUOUS",
        "DIFFERENT_MARKER",
        "MATCH",
        "MATCH_REPEATED",
    }
)
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
SERIAL = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")

CYCLE_DESCRIPTOR = (
    "format=rog5-retention-cycle-identity-v1\n"
    f"profile={RETENTION_PROFILE}\n"
    f"candidate={CANDIDATE}\n"
    f"manifest_sha256={MANIFEST_SHA256}\n"
    f"execution_recovery_profile={EXECUTION_RECOVERY_PROFILE}\n"
    f"execution_recovery_sha256={EXECUTION_RECOVERY_SHA256}\n"
    f"observer_recovery_profile={OBSERVER_RECOVERY_PROFILE}\n"
    f"observer_recovery_sha256={OBSERVER_RECOVERY_SHA256}\n"
    "sequence=diagnostic-target>exact-alpine-fallback>bootloader>"
    "observation-recovery>postmortem-status\n"
).encode("ascii")
CYCLE_SHA256 = hashlib.sha256(CYCLE_DESCRIPTOR).hexdigest()


@dataclass(frozen=True)
class ExactClaim:
    """One repository-owned exact claim record."""

    identifier: str
    role: str
    record: bytes
    sha256: str


def exact_claim(
    identifier: str,
    role: str,
    recovery_sha256: str,
    peer_recovery_sha256: str,
) -> ExactClaim:
    record = (
        "format=rog5-retention-boot-consumption-v1\n"
        f"retention_profile={RETENTION_PROFILE}\n"
        f"cycle_sha256={CYCLE_SHA256}\n"
        f"claim_role={role}\n"
        f"recovery_profile={identifier}\n"
        f"recovery_sha256={recovery_sha256}\n"
        f"peer_recovery_sha256={peer_recovery_sha256}\n"
        f"candidate={CANDIDATE}\n"
        f"manifest_sha256={MANIFEST_SHA256}\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")
    return ExactClaim(
        identifier=identifier,
        role=role,
        record=record,
        sha256=hashlib.sha256(record).hexdigest(),
    )


EXECUTION_CLAIM = exact_claim(
    EXECUTION_RECOVERY_PROFILE,
    "execution",
    EXECUTION_RECOVERY_SHA256,
    OBSERVER_RECOVERY_SHA256,
)
OBSERVER_CLAIM = exact_claim(
    OBSERVER_RECOVERY_PROFILE,
    "observer",
    OBSERVER_RECOVERY_SHA256,
    EXECUTION_RECOVERY_SHA256,
)
