#!/usr/bin/env python3
"""Pure reference model for one future two-claim retention cycle."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sys


RETENTION_PROFILE = "host-rendezvous-v3-observer-v1"
CANDIDATE = "headless-netroot-early-diag-v2"
MANIFEST_SHA256 = (
    "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc"
)
EXECUTION_RECOVERY_PROFILE = "retention-host-rendezvous-v3-execution-v1"
OBSERVER_RECOVERY_PROFILE = "retention-host-rendezvous-v3-observer-v1"
EXECUTION_RECOVERY_SHA256 = (
    "cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d"
)
OBSERVER_RECOVERY_SHA256 = (
    "3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b"
)
PHYSICAL_SEQUENCE = (
    "diagnostic-target",
    "exact-alpine-fallback",
    "bootloader",
    "observation-recovery",
    "postmortem-status",
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
    b"format=rog5-retention-cycle-identity-v1\n"
    b"profile=host-rendezvous-v3-observer-v1\n"
    b"candidate=headless-netroot-early-diag-v2\n"
    b"manifest_sha256="
    b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
    b"execution_recovery_profile=retention-host-rendezvous-v3-execution-v1\n"
    b"execution_recovery_sha256="
    b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
    b"observer_recovery_profile=retention-host-rendezvous-v3-observer-v1\n"
    b"observer_recovery_sha256="
    b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
    b"sequence=diagnostic-target>exact-alpine-fallback>bootloader>"
    b"observation-recovery>postmortem-status\n"
)
CYCLE_SHA256 = hashlib.sha256(CYCLE_DESCRIPTOR).hexdigest()


@dataclass(frozen=True)
class DraftClaim:
    """One exact, deliberately unregistered future claim body."""

    identifier: str
    role: str
    record: bytes
    sha256: str


def draft_claim(
    identifier: str,
    role: str,
    recovery_sha256: str,
    peer_recovery_sha256: str,
) -> DraftClaim:
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
    return DraftClaim(
        identifier=identifier,
        role=role,
        record=record,
        sha256=hashlib.sha256(record).hexdigest(),
    )


EXECUTION_CLAIM = draft_claim(
    EXECUTION_RECOVERY_PROFILE,
    "execution",
    EXECUTION_RECOVERY_SHA256,
    OBSERVER_RECOVERY_SHA256,
)
OBSERVER_CLAIM = draft_claim(
    OBSERVER_RECOVERY_PROFILE,
    "observer",
    OBSERVER_RECOVERY_SHA256,
    EXECUTION_RECOVERY_SHA256,
)


class SequenceError(RuntimeError):
    """The reference transaction cannot preserve its exact ordering."""


class RetentionSequence:
    """No-I/O state machine for one future, non-retryable physical cycle."""

    def __init__(self) -> None:
        self.phase = "hold"
        self.next_step = "preflight"
        self.execution_claimed = False
        self.observer_claimed = False
        self.target_boot_id: str | None = None
        self.fastboot_serial: str | None = None
        self.postmortem_classification: str | None = None
        self.postmortem_reads = 0
        self._terminal = False

    def _expect(self, step: str) -> None:
        if self._terminal:
            raise SequenceError("sequence is already terminal")
        if self.next_step != step:
            raise SequenceError(f"expected {self.next_step}")

    def _advance(self, phase: str, next_step: str) -> None:
        self.phase = phase
        self.next_step = next_step

    def preflight(
        self,
        execution_exact: bool,
        observer_exact: bool,
        policy_allow_rows: int,
        claims_registered: bool,
    ) -> None:
        self._expect("preflight")
        if (
            not execution_exact
            or not observer_exact
            or policy_allow_rows != 0
            or claims_registered
        ):
            raise SequenceError("offline HOLD preflight is not exact")
        self._advance("preflighted", "execution-claim")

    def enter_execution_claim(self, identifier: str, record: bytes) -> None:
        self._expect("execution-claim")
        if (
            identifier != EXECUTION_CLAIM.identifier
            or record != EXECUTION_CLAIM.record
        ):
            raise SequenceError("execution claim is not the exact draft")
        self.execution_claimed = True
        self._advance("execution-claimed", "execution-recovery")

    def boot_execution_recovery(
        self, recovery_sha256: str, rollback_armed: bool
    ) -> None:
        self._expect("execution-recovery")
        if (
            recovery_sha256 != EXECUTION_RECOVERY_SHA256
            or not rollback_armed
        ):
            raise SequenceError(
                "execution recovery identity or rollback changed"
            )
        self._advance("execution-recovery-booted", "target-observation")

    def observe_target(self, candidate: str, boot_id: str) -> None:
        self._expect("target-observation")
        if candidate != CANDIDATE or not BOOT_ID.fullmatch(boot_id):
            raise SequenceError("target lineage is not exact")
        self.target_boot_id = boot_id
        self._advance("target-observed", "fallback-proof")

    def prove_fallback(
        self,
        candidate: str,
        boot_id: str,
        exact_identity: bool,
        intent_resolved: bool,
    ) -> None:
        self._expect("fallback-proof")
        if (
            candidate != CANDIDATE
            or boot_id != self.target_boot_id
            or not exact_identity
            or not intent_resolved
        ):
            raise SequenceError("fallback proof is not exact or correlated")
        self._advance("fallback-proved", "retention-preflight")

    def retention_preflight(
        self, ramoops_exact: bool, pstore_empty: bool
    ) -> None:
        self._expect("retention-preflight")
        if not ramoops_exact or not pstore_empty:
            raise SequenceError("fallback retention preflight is not exact")
        self._advance("retention-preflighted", "bootloader-proof")

    def prove_bootloader(
        self,
        same_port: bool,
        product: str,
        anchored_serial: str,
        observed_serial: str,
    ) -> None:
        self._expect("bootloader-proof")
        if (
            not same_port
            or product != "0b05:4daf"
            or not SERIAL.fullmatch(anchored_serial)
            or observed_serial != anchored_serial
        ):
            raise SequenceError("bootloader identity or port lineage changed")
        self.fastboot_serial = anchored_serial
        self._advance("bootloader-proved", "observer-claim")

    def enter_observer_claim(self, identifier: str, record: bytes) -> None:
        self._expect("observer-claim")
        if (
            identifier != OBSERVER_CLAIM.identifier
            or record != OBSERVER_CLAIM.record
        ):
            raise SequenceError("observer claim is not the exact draft")
        self.observer_claimed = True
        self._advance("observer-claimed", "observer-recovery")

    def boot_observer_recovery(
        self,
        recovery_sha256: str,
        same_port: bool,
        observed_serial: str,
        rollback_armed: bool,
    ) -> None:
        self._expect("observer-recovery")
        if (
            recovery_sha256 != OBSERVER_RECOVERY_SHA256
            or not same_port
            or observed_serial != self.fastboot_serial
            or not rollback_armed
        ):
            raise SequenceError(
                "observer recovery identity, port lineage, or rollback changed"
            )
        self._advance("observer-recovery-booted", "postmortem-status")

    def read_postmortem(
        self, candidate: str, boot_id: str, classification: str
    ) -> None:
        self._expect("postmortem-status")
        if candidate != CANDIDATE or boot_id != self.target_boot_id:
            raise SequenceError("postmortem lineage input changed")
        if classification not in POSTMORTEM_CLASSIFICATIONS:
            raise SequenceError("postmortem classification is not canonical")
        self.postmortem_classification = classification
        self.postmortem_reads = 1
        self._advance("postmortem-read", "finish")

    def finish(self) -> dict[str, object]:
        self._expect("finish")
        lineage_result = (
            "LINEAGE_RETAINED"
            if self.postmortem_classification in {"MATCH", "MATCH_REPEATED"}
            else "INCONCLUSIVE"
        )
        self.phase = "complete"
        self.next_step = "none"
        self._terminal = True
        return {
            "format": "rog5-retention-sequence-result-v1",
            "phase": self.phase,
            "execution_claim": "consumed",
            "observer_claim": "consumed",
            "postmortem_classification": self.postmortem_classification,
            "postmortem_reads": self.postmortem_reads,
            "lineage_result": lineage_result,
            "retry": "forbidden",
        }

    def terminate(self, reason: str) -> dict[str, str]:
        if self._terminal:
            raise SequenceError("sequence is already terminal")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", reason):
            raise SequenceError("terminal reason is not canonical")
        failed_phase = self.phase
        physical_result = "UNKNOWN" if self.execution_claimed else "NO_BOOT"
        retry = "forbidden" if self.execution_claimed else "not-applicable"
        self.phase = "terminated"
        self.next_step = "none"
        self._terminal = True
        return {
            "format": "rog5-retention-sequence-terminal-v1",
            "failed_phase": failed_phase,
            "reason": reason,
            "execution_claim": (
                "consumed" if self.execution_claimed else "absent"
            ),
            "observer_claim": (
                "consumed" if self.observer_claimed else "absent"
            ),
            "result": physical_result,
            "retry": retry,
        }


def plan() -> dict[str, object]:
    return {
        "format": "rog5-retention-sequence-reference-v1",
        "profile": RETENTION_PROFILE,
        "cycle_sha256": CYCLE_SHA256,
        "candidate": CANDIDATE,
        "manifest_sha256": MANIFEST_SHA256,
        "execution_claim_sha256": EXECUTION_CLAIM.sha256,
        "observer_claim_sha256": OBSERVER_CLAIM.sha256,
        "sequence": list(PHYSICAL_SEQUENCE),
        "implementation": "reference-only",
        "claims_registered": False,
        "policy_allow_rows": 0,
        "authority": "none",
        "boot_authority": "none",
        "retry": "forbidden",
        "missing_pstore": "inconclusive",
        "recommendation": "HOLD",
    }


def main(arguments: list[str]) -> int:
    if arguments != ["plan"]:
        raise SequenceError(
            "usage: retention-cycle-sequence-reference.py plan"
        )
    print(json.dumps(plan(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SequenceError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
