"""Callback-only adapter for the offline retention-cycle transaction."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Callable


JOURNAL_PATH = Path(__file__).with_name("retention-cycle-transaction.py")
_SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_cycle_transaction_for_adapter", JOURNAL_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("retention transaction journal is unavailable")
JOURNAL = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = JOURNAL
_SPEC.loader.exec_module(JOURNAL)

TARGET_TOKEN = "$TARGET_BOOT_ID"
FALLBACK_PIN_TOKEN = "$FALLBACK_HOST_PIN"


class AdapterError(RuntimeError):
    """The fixture cannot preserve an exact action boundary."""


@dataclass(frozen=True)
class Invocation:
    """One exact helper descriptor; this module never executes it."""

    name: str
    program: str
    arguments: tuple[str, ...]
    required_intent: str

    def resolve_arguments(
        self,
        target_boot_id: str,
        fallback_known_hosts: str = FALLBACK_PIN_TOKEN,
    ) -> tuple[str, ...]:
        return tuple(
            target_boot_id
            if value == TARGET_TOKEN
            else fallback_known_hosts
            if value == FALLBACK_PIN_TOKEN
            else value
            for value in self.arguments
        )


@dataclass(frozen=True)
class CycleEvidence:
    """Exact dynamic evidence supplied by a hardware-free fixture."""

    target_boot_id: str
    fallback_boot_id: str
    usb_location: str
    fastboot_serial: str
    postmortem_classification: str


INVOCATIONS = (
    Invocation(
        "execution-claim",
        "scripts/host/consume-exact-boot-claim.py",
        (JOURNAL.EXECUTION_CLAIM_IDENTIFIER,),
        "execution-claim-intent",
    ),
    Invocation(
        "execution-boot",
        "scripts/host/run-stable-recovery-live-gate.sh",
        ("boot",),
        "execution-boot-intent",
    ),
    Invocation(
        "fallback-reboot",
        "scripts/host/fallback-acm-control.py",
        ("reboot", FALLBACK_PIN_TOKEN),
        "bootloader-transition-intent",
    ),
    Invocation(
        "observer-claim",
        "scripts/host/consume-exact-boot-claim.py",
        (JOURNAL.OBSERVER_CLAIM_IDENTIFIER,),
        "observer-claim-intent",
    ),
    Invocation(
        "observer-boot",
        "scripts/host/run-observation-recovery-live-gate.sh",
        ("boot",),
        "observer-boot-intent",
    ),
    Invocation(
        "postmortem-read",
        "scripts/host/stable-recovery-control.py",
        ("postmortem-status", JOURNAL.CANDIDATE, TARGET_TOKEN),
        "postmortem-read-intent",
    ),
)

FixtureExecutor = Callable[[Invocation], dict[str, object]]


class CycleAdapter:
    """Drive one fresh journal using injected fixture callbacks only."""

    def __init__(self, journal: object, executor: FixtureExecutor) -> None:
        self.journal = journal
        self.executor = executor

    def _validate_evidence(self, evidence: CycleEvidence) -> None:
        snapshot = self.journal.snapshot()
        if (
            not isinstance(evidence.target_boot_id, str)
            or JOURNAL.BOOT_ID.fullmatch(evidence.target_boot_id) is None
            or not isinstance(evidence.fallback_boot_id, str)
            or JOURNAL.BOOT_ID.fullmatch(evidence.fallback_boot_id) is None
            or evidence.fallback_boot_id == evidence.target_boot_id
            or evidence.usb_location != snapshot["usb_location"]
            or not JOURNAL.valid_location(evidence.usb_location)
            or not isinstance(evidence.fastboot_serial, str)
            or JOURNAL.SERIAL.fullmatch(evidence.fastboot_serial) is None
            or evidence.postmortem_classification
            not in JOURNAL.POSTMORTEM_CLASSIFICATIONS
        ):
            raise AdapterError("fixture evidence is not exact")

    @staticmethod
    def _expected_result(
        invocation: Invocation, evidence: CycleEvidence
    ) -> dict[str, object]:
        results: dict[str, dict[str, object]] = {
            "execution-claim": {
                "identifier": JOURNAL.EXECUTION_CLAIM_IDENTIFIER,
                "record_sha256": JOURNAL.EXECUTION_CLAIM_SHA256,
                "state": "consumed",
            },
            "execution-boot": {
                "recovery_sha256": JOURNAL.EXECUTION_RECOVERY_SHA256,
                "rollback_armed": True,
                "usb_location": evidence.usb_location,
            },
            "fallback-reboot": {
                "fastboot_serial": evidence.fastboot_serial,
                "product": "0b05:4daf",
                "usb_location": evidence.usb_location,
            },
            "observer-claim": {
                "identifier": JOURNAL.OBSERVER_CLAIM_IDENTIFIER,
                "record_sha256": JOURNAL.OBSERVER_CLAIM_SHA256,
                "state": "consumed",
            },
            "observer-boot": {
                "fastboot_serial": evidence.fastboot_serial,
                "recovery_sha256": JOURNAL.OBSERVER_RECOVERY_SHA256,
                "rollback_armed": True,
                "usb_location": evidence.usb_location,
            },
            "postmortem-read": {
                "candidate": JOURNAL.CANDIDATE,
                "classification": evidence.postmortem_classification,
                "reads": 1,
                "target_boot_id": evidence.target_boot_id,
            },
        }
        return results[invocation.name]

    def _invoke(
        self, index: int, evidence: CycleEvidence
    ) -> dict[str, object]:
        invocation = INVOCATIONS[index]
        before = self.journal.snapshot()
        if before["phase"] != invocation.required_intent:
            raise AdapterError(
                f"{invocation.name} lacks its durable intent"
            )
        resolved = Invocation(
            invocation.name,
            invocation.program,
            invocation.resolve_arguments(evidence.target_boot_id),
            invocation.required_intent,
        )
        try:
            result = self.executor(resolved)
        except Exception as error:
            raise AdapterError(
                f"fixture callback failed: {invocation.name}"
            ) from error
        after = self.journal.snapshot()
        if after != before:
            raise AdapterError("fixture callback changed transaction state")
        expected = self._expected_result(invocation, evidence)
        if (
            type(result) is not dict
            or set(result) != set(expected)
            or any(
                type(result[key]) is not type(expected[key])
                or result[key] != expected[key]
                for key in expected
            )
        ):
            raise AdapterError(
                f"fixture callback result is not exact: {invocation.name}"
            )
        return result

    def run(self, evidence: CycleEvidence) -> dict[str, object]:
        initial = self.journal.snapshot()
        if (
            initial["phase"] != "cycle-opened"
            or initial["next_event"] != "execution-claim-intent"
            or initial["authority"] != "none"
            or initial["boot_authority"] != "none"
            or initial["execution_claim"] != "absent"
            or initial["observer_claim"] != "absent"
        ):
            raise AdapterError(
                "adapter requires one fresh cycle-opened HOLD journal"
            )
        self._validate_evidence(evidence)

        self.journal.execution_claim_intent()
        claim = self._invoke(0, evidence)
        self.journal.execution_claim_entered(
            str(claim["identifier"]), str(claim["record_sha256"])
        )

        self.journal.execution_boot_intent(
            JOURNAL.EXECUTION_RECOVERY_SHA256,
            evidence.usb_location,
            True,
        )
        execution = self._invoke(1, evidence)
        self.journal.execution_recovery_observed(
            str(execution["recovery_sha256"]),
            str(execution["usb_location"]),
            execution["rollback_armed"] is True,
        )
        self.journal.target_observed(
            JOURNAL.CANDIDATE,
            evidence.target_boot_id,
            evidence.usb_location,
        )
        self.journal.fallback_observed(
            JOURNAL.CANDIDATE,
            evidence.target_boot_id,
            evidence.fallback_boot_id,
            evidence.usb_location,
            "1d6b:0104",
            "ROG5LINUX",
            True,
            True,
        )
        self.journal.retention_preflight(
            evidence.fallback_boot_id,
            evidence.usb_location,
            True,
            True,
        )

        self.journal.bootloader_transition_intent(
            evidence.fallback_boot_id, evidence.usb_location
        )
        bootloader = self._invoke(2, evidence)
        self.journal.bootloader_observed(
            str(bootloader["usb_location"]),
            str(bootloader["product"]),
            str(bootloader["fastboot_serial"]),
        )

        self.journal.observer_claim_intent()
        observer_claim = self._invoke(3, evidence)
        self.journal.observer_claim_entered(
            str(observer_claim["identifier"]),
            str(observer_claim["record_sha256"]),
        )
        self.journal.observer_boot_intent(
            JOURNAL.OBSERVER_RECOVERY_SHA256,
            evidence.usb_location,
            evidence.fastboot_serial,
            True,
        )
        observer = self._invoke(4, evidence)
        self.journal.observer_recovery_observed(
            str(observer["recovery_sha256"]),
            str(observer["usb_location"]),
            str(observer["fastboot_serial"]),
            observer["rollback_armed"] is True,
        )

        self.journal.postmortem_read_intent(
            JOURNAL.CANDIDATE, evidence.target_boot_id
        )
        postmortem = self._invoke(5, evidence)
        self.journal.postmortem_result(
            str(postmortem["candidate"]),
            str(postmortem["target_boot_id"]),
            str(postmortem["classification"]),
            int(postmortem["reads"]),
        )
        return self.journal.finish()
