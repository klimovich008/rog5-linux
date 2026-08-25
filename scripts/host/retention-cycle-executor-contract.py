"""Pure process contract for a future retention-cycle executor."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import re
import sys


REPO = Path(__file__).resolve().parents[2]
ADAPTER_PATH = Path(__file__).with_name("retention-cycle-adapter.py")
_SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_cycle_adapter_for_executor_contract", ADAPTER_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("retention-cycle adapter is unavailable")
ADAPTER = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = ADAPTER
_SPEC.loader.exec_module(ADAPTER)

BUILTIN_EXECUTOR = "none"
LIVE_ENTRYPOINT = "none"
CONNECTED_ADMISSION = "none"
CREDENTIAL_USE = "none"

BASE_ENVIRONMENT = tuple(
    sorted(
        {
            "HOME": "/nonexistent",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "TZ": "UTC",
        }.items()
    )
)

EXECUTION_ENVIRONMENT_NAMES = tuple(
    sorted(
        (
            "ACM_TIMEOUT",
            "ALLOW_HEADLESS_LIVE_GATE",
            "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE",
            "ALLOW_TEMPORARY_BOOT",
            "BUNDLE",
            "BUNDLE_ROOT",
            "FASTBOOT_SERIAL",
            "HOST_VERIFIER_SHA256",
            "LIVE_BUILD_ROOT",
            "MANIFEST_SHA256",
            "RECOVERY_COMPONENT_ROOT",
            "RECOVERY_SHA256",
            "ROG5_EXPECTED_USB_LOCATION",
            "ROG5_RETENTION_BOOT_RESULT",
            "ROG5_STABLE_RECOVERY_PROFILE",
            "TRUST_KEY",
            "TRUST_KEY_SHA256",
        )
    )
)
FALLBACK_ENVIRONMENT_NAMES = tuple(
    sorted(
        (
            "ALLOW_FALLBACK_ACM_CONTROL",
            "ALLOW_FALLBACK_ACM_STORAGE_WRITE",
            "ALLOW_FALLBACK_BOOTLOADER_REBOOT",
            "ALLOW_PHONE_CREDENTIAL_USE",
            "ROG5_EXPECTED_FASTBOOT_SERIAL",
            "ROG5_EXPECTED_USB_LOCATION",
            "ROG5_RETENTION_BOOT_RESULT",
        )
    )
)
OBSERVER_ENVIRONMENT_NAMES = tuple(
    sorted(
        (
            "ALLOW_HEADLESS_LIVE_GATE",
            "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE",
            "ALLOW_TEMPORARY_BOOT",
            "OBSERVER_BUILD_ROOT",
            "OBSERVER_RECOVERY_SHA256",
            "ROG5_EXPECTED_FASTBOOT_SERIAL",
            "ROG5_EXPECTED_USB_LOCATION",
            "ROG5_RETENTION_BOOT_RESULT",
            "ROG5_OBSERVATION_RECOVERY_PROFILE",
        )
    )
)

PROGRAM_IDENTITIES = {
    "scripts/host/consume-exact-boot-claim.py": (
        60567,
        "c362fcd7ed39b2364f9315f03e7ee33246a5d58599f03b7814d0a26496d65c9d",
        "0755",
    ),
    "scripts/host/run-stable-recovery-live-gate.sh": (
        401285,
        "536e6921fca17b10f7ded863b2a63aef34cb555744439d53bfc589fc470830e9",
        "0755",
    ),
    "scripts/host/fallback-acm-control.py": (
        115520,
        "ab507539930648601ffe8b77a425c12d79ba4477a9032328e1061a07e4ffc9ca",
        "0755",
    ),
    "scripts/host/run-observation-recovery-live-gate.sh": (
        21239,
        "ee51680e9871ed788ea846ae4c9887505e8666d44cbf2f1427ad734cc8056f04",
        "0755",
    ),
    "scripts/host/stable-recovery-control.py": (
        39737,
        "54103d48975fa399d6af9209fde4e0fca085a4a6d061e721fa212b9c49da3f51",
        "0755",
    ),
}

BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
SERIAL = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


class ContractError(RuntimeError):
    """A future process request is not the reviewed offline contract."""


@dataclass(frozen=True)
class ExecutorInputs:
    """Dynamic values a future runner must prove before action intent."""

    target_boot_id: str
    fallback_boot_id: str
    usb_location: str
    fastboot_serial: str
    fallback_known_hosts: str


@dataclass(frozen=True)
class ProcessSpec:
    """One immutable process description; this module cannot execute it."""

    name: str
    program: str
    program_size: int
    program_sha256: str
    program_mode: str
    argv: tuple[str, ...]
    cwd: str
    environment: tuple[tuple[str, str], ...]
    stdin: str
    stdout: str
    stderr: str
    timeout_seconds: int
    output_limit_bytes: int
    start_new_session: bool
    kill_process_group_on_timeout: bool
    close_fds: bool
    umask: str
    accepted_exit_codes: tuple[int, ...]
    success_protocol: str


def execution_environment(
    fastboot_serial: str, usb_location: str
) -> dict[str, str]:
    root = REPO / "build/host-rendezvous-v3-haven-production-20260810-r2"
    return {
        "ACM_TIMEOUT": "90",
        "ALLOW_HEADLESS_LIVE_GATE": "1",
        "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE": "1",
        "ALLOW_TEMPORARY_BOOT": "1",
        "BUNDLE": "headless-netroot-early-diag-v2",
        "BUNDLE_ROOT": "/var/lib/rog5-recovery-bundles",
        "FASTBOOT_SERIAL": fastboot_serial,
        "HOST_VERIFIER_SHA256": (
            "03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0"
        ),
        "LIVE_BUILD_ROOT": str(root / "wrapper"),
        "MANIFEST_SHA256": (
            "54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc"
        ),
        "RECOVERY_COMPONENT_ROOT": str(root / "recovery"),
        "RECOVERY_SHA256": (
            "cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d"
        ),
        "ROG5_EXPECTED_USB_LOCATION": usb_location,
        "ROG5_RETENTION_BOOT_RESULT": "1",
        "ROG5_STABLE_RECOVERY_PROFILE": (
            "headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1"
        ),
        "TRUST_KEY": str(root / "recovery/ephemeral-public.raw"),
        "TRUST_KEY_SHA256": (
            "f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b"
        ),
    }


def fallback_environment(
    fastboot_serial: str, usb_location: str
) -> dict[str, str]:
    return {
        "ALLOW_FALLBACK_ACM_CONTROL": "1",
        "ALLOW_FALLBACK_ACM_STORAGE_WRITE": "1",
        "ALLOW_FALLBACK_BOOTLOADER_REBOOT": "1",
        "ALLOW_PHONE_CREDENTIAL_USE": "1",
        "ROG5_EXPECTED_FASTBOOT_SERIAL": fastboot_serial,
        "ROG5_EXPECTED_USB_LOCATION": usb_location,
        "ROG5_RETENTION_BOOT_RESULT": "1",
    }


def observer_environment(
    fastboot_serial: str, usb_location: str
) -> dict[str, str]:
    return {
        "ALLOW_HEADLESS_LIVE_GATE": "1",
        "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE": "1",
        "ALLOW_TEMPORARY_BOOT": "1",
        "OBSERVER_BUILD_ROOT": str(
            REPO / "build/observation-recovery-haven-offline-20260810-r1"
        ),
        "OBSERVER_RECOVERY_SHA256": (
            "3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b"
        ),
        "ROG5_EXPECTED_FASTBOOT_SERIAL": fastboot_serial,
        "ROG5_EXPECTED_USB_LOCATION": usb_location,
        "ROG5_RETENTION_BOOT_RESULT": "1",
        "ROG5_OBSERVATION_RECOVERY_PROFILE": (
            "observation-host-rendezvous-v3-haven-production-hold-v1"
        ),
    }


def _closed_environment(updates: dict[str, str]) -> tuple[tuple[str, str], ...]:
    values = dict(BASE_ENVIRONMENT)
    if set(values) & set(updates):
        raise ContractError("action environment overlaps the fixed baseline")
    values.update(updates)
    if any(
        type(name) is not str
        or type(value) is not str
        or re.fullmatch(r"[A-Z][A-Z0-9_]*", name) is None
        or "\x00" in value
        or "\n" in value
        for name, value in values.items()
    ):
        raise ContractError("process environment is not canonical")
    return tuple(sorted(values.items()))


def _validate_inputs(inputs: ExecutorInputs) -> None:
    if type(inputs) is not ExecutorInputs:
        raise ContractError("executor inputs have the wrong type")
    values = (
        inputs.target_boot_id,
        inputs.fallback_boot_id,
        inputs.usb_location,
        inputs.fastboot_serial,
        inputs.fallback_known_hosts,
    )
    if any(type(value) is not str for value in values):
        raise ContractError("every executor input must be an exact string")
    if (
        BOOT_ID.fullmatch(inputs.target_boot_id) is None
        or BOOT_ID.fullmatch(inputs.fallback_boot_id) is None
        or inputs.target_boot_id == inputs.fallback_boot_id
        or not ADAPTER.JOURNAL.valid_location(inputs.usb_location)
        or inputs.usb_location.startswith("/")
        or ".." in Path(inputs.usb_location).parts
        or SERIAL.fullmatch(inputs.fastboot_serial) is None
    ):
        raise ContractError("executor lineage is not exact")
    pin = Path(inputs.fallback_known_hosts)
    if (
        len(inputs.fallback_known_hosts) > 1024
        or not pin.is_absolute()
        or pin == Path("/")
        or "\x00" in inputs.fallback_known_hosts
        or ".." in pin.parts
        or str(pin) != inputs.fallback_known_hosts
        or inputs.fallback_known_hosts.endswith("/")
        or "//" in inputs.fallback_known_hosts
        or "%" in inputs.fallback_known_hosts
        or re.fullmatch(
            r"/[A-Za-z0-9._/+:-]{1,1023}",
            inputs.fallback_known_hosts,
        )
        is None
        or any(character.isspace() for character in inputs.fallback_known_hosts)
        or pin == REPO
        or pin.is_relative_to(REPO)
    ):
        raise ContractError("fallback host pin path is not canonical")


def _spec(
    name: str,
    program: str,
    argv: tuple[str, ...],
    environment: dict[str, str],
    timeout_seconds: int,
    output_limit_bytes: int,
    success_protocol: str,
) -> ProcessSpec:
    try:
        size, digest, mode = PROGRAM_IDENTITIES[program]
    except KeyError as error:
        raise ContractError("program is not repository-owned") from error
    return ProcessSpec(
        name=name,
        program=program,
        program_size=size,
        program_sha256=digest,
        program_mode=mode,
        argv=argv,
        cwd=str(REPO),
        environment=_closed_environment(environment),
        stdin="devnull",
        stdout="bounded-pipe",
        stderr="bounded-pipe",
        timeout_seconds=timeout_seconds,
        output_limit_bytes=output_limit_bytes,
        start_new_session=True,
        kill_process_group_on_timeout=True,
        close_fds=True,
        umask="0077",
        accepted_exit_codes=(0,),
        success_protocol=success_protocol,
    )


def process_specs(inputs: ExecutorInputs) -> tuple[ProcessSpec, ...]:
    """Return the reviewed process descriptions without running anything."""

    _validate_inputs(inputs)
    invocation_by_name = {item.name: item for item in ADAPTER.INVOCATIONS}
    expected_names = (
        "execution-claim",
        "execution-boot",
        "fallback-reboot",
        "observer-claim",
        "observer-boot",
        "postmortem-read",
    )
    if tuple(item.name for item in ADAPTER.INVOCATIONS) != expected_names:
        raise ContractError("adapter invocation order is not exact")

    def program(name: str) -> tuple[str, str]:
        relative = invocation_by_name[name].program
        if relative not in PROGRAM_IDENTITIES:
            raise ContractError("adapter program is not contract-owned")
        return relative, str(REPO / relative)

    execution_claim, execution_claim_path = program("execution-claim")
    execution_boot, execution_boot_path = program("execution-boot")
    fallback, fallback_path = program("fallback-reboot")
    observer_claim, observer_claim_path = program("observer-claim")
    observer_boot, observer_boot_path = program("observer-boot")
    postmortem, postmortem_path = program("postmortem-read")

    specs = (
        _spec(
            "execution-claim",
            execution_claim,
            (
                "/usr/bin/python3",
                "-B",
                execution_claim_path,
                ADAPTER.JOURNAL.EXECUTION_CLAIM_IDENTIFIER,
            ),
            {},
            15,
            4096,
            "exact-claim-pass-v1",
        ),
        _spec(
            "execution-boot",
            execution_boot,
            (
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                execution_boot_path,
                "boot",
            ),
            execution_environment(inputs.fastboot_serial, inputs.usb_location),
            300,
            131072,
            "retention-boot-result-v1",
        ),
        _spec(
            "fallback-reboot",
            fallback,
            (
                "/usr/bin/python3",
                "-B",
                fallback_path,
                "reboot",
                inputs.fallback_known_hosts,
            ),
            fallback_environment(inputs.fastboot_serial, inputs.usb_location),
            240,
            131072,
            "retention-boot-result-v1",
        ),
        _spec(
            "observer-claim",
            observer_claim,
            (
                "/usr/bin/python3",
                "-B",
                observer_claim_path,
                ADAPTER.JOURNAL.OBSERVER_CLAIM_IDENTIFIER,
            ),
            {},
            15,
            4096,
            "exact-claim-pass-v1",
        ),
        _spec(
            "observer-boot",
            observer_boot,
            (
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                observer_boot_path,
                "boot",
            ),
            observer_environment(inputs.fastboot_serial, inputs.usb_location),
            300,
            131072,
            "retention-boot-result-v1",
        ),
        _spec(
            "postmortem-read",
            postmortem,
            (
                "/usr/bin/python3",
                "-B",
                postmortem_path,
                "postmortem-status",
                ADAPTER.JOURNAL.CANDIDATE,
                inputs.target_boot_id,
            ),
            {},
            90,
            16384,
            "postmortem-lineage-json-v1",
        ),
    )
    for spec, invocation in zip(specs, ADAPTER.INVOCATIONS, strict=True):
        resolved = invocation.resolve_arguments(
            inputs.target_boot_id, inputs.fallback_known_hosts
        )
        if (
            spec.program != invocation.program
            or spec.argv[-len(resolved) :] != resolved
        ):
            raise ContractError("process arguments diverge from the adapter")
    return specs
