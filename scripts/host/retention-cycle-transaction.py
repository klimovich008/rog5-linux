"""Crash-conservative offline journal for one reviewed retention cycle."""

from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, NoReturn


REFERENCE_SELECTOR = os.environ.get(
    "ROG5_RETENTION_SEQUENCE", "host-rendezvous-v3-observer-v1"
)
REFERENCE_FILES = {
    "host-rendezvous-v3-observer-v1": (
        "retention-cycle-sequence-reference.py"
    ),
    "host-rendezvous-v11-mainline-udc-observer-v2": (
        "retention-cycle-mainline-udc-v11.py"
    ),
}
try:
    reference_file = REFERENCE_FILES[REFERENCE_SELECTOR]
except KeyError as error:
    raise RuntimeError(
        "retention sequence selector is not repository-owned"
    ) from error
REFERENCE_PATH = Path(__file__).with_name(reference_file)
_SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_cycle_sequence_for_transaction", REFERENCE_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("retention sequence reference is unavailable")
REFERENCE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = REFERENCE
_SPEC.loader.exec_module(REFERENCE)

CYCLE_SHA256 = REFERENCE.CYCLE_SHA256
PROFILE = REFERENCE.RETENTION_PROFILE
CANDIDATE = REFERENCE.CANDIDATE
MANIFEST_SHA256 = REFERENCE.MANIFEST_SHA256
EXECUTION_RECOVERY_SHA256 = REFERENCE.EXECUTION_RECOVERY_SHA256
OBSERVER_RECOVERY_SHA256 = REFERENCE.OBSERVER_RECOVERY_SHA256
EXECUTION_CLAIM_IDENTIFIER = REFERENCE.EXECUTION_CLAIM.identifier
EXECUTION_CLAIM_SHA256 = REFERENCE.EXECUTION_CLAIM.sha256
OBSERVER_CLAIM_IDENTIFIER = REFERENCE.OBSERVER_CLAIM.identifier
OBSERVER_CLAIM_SHA256 = REFERENCE.OBSERVER_CLAIM.sha256
POSTMORTEM_CLASSIFICATIONS = REFERENCE.POSTMORTEM_CLASSIFICATIONS

CYCLE_DIRECTORY = f"retention-{CYCLE_SHA256}"
ZERO_SHA256 = "0" * 64
MAX_EVENT_BYTES = 4096
BOOT_ID = REFERENCE.BOOT_ID
SERIAL = REFERENCE.SERIAL
USB_LOCATION = re.compile(r"[A-Za-z0-9._:/-]{1,512}\Z")
REASON = re.compile(r"[a-z0-9][a-z0-9-]{0,95}\Z")

EVENT_NAMES = (
    "cycle-opened",
    "execution-claim-intent",
    "execution-claim-entered",
    "execution-boot-intent",
    "execution-recovery-observed",
    "target-observed",
    "fallback-observed",
    "retention-preflight",
    "bootloader-transition-intent",
    "bootloader-observed",
    "observer-claim-intent",
    "observer-claim-entered",
    "observer-boot-intent",
    "observer-recovery-observed",
    "postmortem-read-intent",
    "postmortem-result",
    "complete",
)
EVENT_FILES = tuple(
    f"{index:02d}-{name}.json"
    for index, name in enumerate(EVENT_NAMES)
)
TERMINAL_FILE = "99-terminal.json"
REOPEN_BLOCKED = frozenset(
    {
        "execution-claim-intent",
        "execution-claim-entered",
        "execution-boot-intent",
        "bootloader-transition-intent",
        "observer-claim-intent",
        "observer-claim-entered",
        "observer-boot-intent",
        "postmortem-read-intent",
    }
)


class TransactionError(RuntimeError):
    """The durable cycle state cannot prove one exact safe continuation."""


def fail(message: str) -> NoReturn:
    raise TransactionError(message)


def canonical_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        + b"\n"
    )


def reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"event has duplicate field: {key}")
        value[key] = item
    return value


def same_object(first: os.stat_result, second: os.stat_result) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


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


def exact_keys(
    value: dict[str, Any], keys: set[str], label: str
) -> None:
    if set(value) != keys:
        fail(f"{label} fields are not exact")


def valid_location(value: object) -> bool:
    return (
        isinstance(value, str)
        and USB_LOCATION.fullmatch(value) is not None
        and not value.startswith("/")
        and not value.endswith("/")
        and "//" not in value
        and ".." not in Path(value).parts
    )


class CycleJournal:
    """One append-only transaction, with no device or command surface."""

    def __init__(
        self,
        root: Path,
        root_descriptor: int,
        cycle_descriptor: int,
        *,
        reopened: bool,
    ) -> None:
        self.root = root
        self.root_descriptor = root_descriptor
        self.cycle_descriptor = cycle_descriptor
        self.cycle_path = root / CYCLE_DIRECTORY
        self._closed = False
        self._reopened = reopened
        self._events: list[tuple[str, bytes]] = []
        self._state = self._initial_state()
        self._load()

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        return {
            "authority": "none",
            "boot_authority": "none",
            "host_boot_id": None,
            "usb_location": None,
            "execution_claim": "absent",
            "observer_claim": "absent",
            "target_boot_id": None,
            "fallback_boot_id": None,
            "fastboot_serial": None,
            "postmortem_reads": 0,
            "postmortem_classification": None,
            "lineage_result": "INCONCLUSIVE",
            "terminal": False,
        }

    @classmethod
    def _open_root(cls, root: Path) -> int:
        if (
            not root.is_absolute()
            or root != Path(os.path.normpath(root))
        ):
            fail("transaction root is not canonical and absolute")
        flags = (
            os.O_RDONLY
            | os.O_CLOEXEC
            | os.O_DIRECTORY
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(root, flags)
        except OSError as error:
            raise TransactionError(
                "transaction root is unsafe or absent"
            ) from error
        try:
            opened = os.fstat(descriptor)
            named = root.stat(follow_symlinks=False)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or not same_object(opened, named)
                or opened.st_uid != os.geteuid()
                or opened.st_gid != os.getegid()
                or stat.S_IMODE(opened.st_mode) != 0o700
            ):
                fail("transaction root metadata is unsafe")
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    @classmethod
    def _open_cycle(cls, root_descriptor: int) -> int:
        flags = (
            os.O_RDONLY
            | os.O_CLOEXEC
            | os.O_DIRECTORY
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(
                CYCLE_DIRECTORY, flags, dir_fd=root_descriptor
            )
        except OSError as error:
            raise TransactionError(
                "transaction directory is unsafe or absent"
            ) from error
        try:
            opened = os.fstat(descriptor)
            named = os.stat(
                CYCLE_DIRECTORY,
                dir_fd=root_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISDIR(opened.st_mode)
                or not same_object(opened, named)
                or opened.st_uid != os.geteuid()
                or opened.st_gid != os.getegid()
                or stat.S_IMODE(opened.st_mode) != 0o700
            ):
                fail("transaction directory metadata is unsafe")
            try:
                fcntl.flock(
                    descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB
                )
            except BlockingIOError as error:
                raise TransactionError(
                    "transaction is already open"
                ) from error
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    @classmethod
    def create(
        cls, root: Path, host_boot_id: str, usb_location: str
    ) -> "CycleJournal":
        root_descriptor = cls._open_root(root)
        cycle_descriptor = -1
        try:
            try:
                os.mkdir(
                    CYCLE_DIRECTORY,
                    mode=0o700,
                    dir_fd=root_descriptor,
                )
            except FileExistsError as error:
                raise TransactionError(
                    "retention cycle already exists"
                ) from error
            os.fsync(root_descriptor)
            cycle_descriptor = cls._open_cycle(root_descriptor)
            journal = cls(
                root,
                root_descriptor,
                cycle_descriptor,
                reopened=False,
            )
            journal._append(
                "cycle-opened",
                {
                    "authority": "none",
                    "boot_authority": "none",
                    "claims_registered": False,
                    "host_boot_id": host_boot_id,
                    "policy_allow_rows": 0,
                    "usb_location": usb_location,
                },
            )
            return journal
        except BaseException:
            if cycle_descriptor >= 0:
                os.close(cycle_descriptor)
            os.close(root_descriptor)
            raise

    @classmethod
    def open(cls, root: Path) -> "CycleJournal":
        root_descriptor = cls._open_root(root)
        try:
            cycle_descriptor = cls._open_cycle(root_descriptor)
        except BaseException:
            os.close(root_descriptor)
            raise
        try:
            return cls(
                root,
                root_descriptor,
                cycle_descriptor,
                reopened=True,
            )
        except BaseException:
            os.close(cycle_descriptor)
            os.close(root_descriptor)
            raise

    def __enter__(self) -> "CycleJournal":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        os.close(self.cycle_descriptor)
        os.close(self.root_descriptor)

    def _require_open(self) -> None:
        if self._closed:
            fail("transaction journal is closed")

    def _revalidate(self) -> None:
        self._require_open()
        try:
            root_opened = os.fstat(self.root_descriptor)
            root_named = self.root.stat(follow_symlinks=False)
        except OSError as error:
            raise TransactionError("transaction root changed") from error
        if (
            not same_object(root_opened, root_named)
            or root_opened.st_uid != os.geteuid()
            or root_opened.st_gid != os.getegid()
            or stat.S_IMODE(root_opened.st_mode) != 0o700
        ):
            fail("transaction root changed")
        try:
            cycle_opened = os.fstat(self.cycle_descriptor)
            cycle_named = os.stat(
                CYCLE_DIRECTORY,
                dir_fd=self.root_descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            raise TransactionError(
                "transaction directory changed"
            ) from error
        if (
            not same_object(cycle_opened, cycle_named)
            or cycle_opened.st_uid != os.geteuid()
            or cycle_opened.st_gid != os.getegid()
            or stat.S_IMODE(cycle_opened.st_mode) != 0o700
        ):
            fail("transaction directory changed")

    def _inventory(self) -> list[str]:
        self._revalidate()
        try:
            names = sorted(os.listdir(self.cycle_descriptor))
        except OSError as error:
            raise TransactionError(
                "transaction inventory is unavailable"
            ) from error
        allowed = set(EVENT_FILES) | {TERMINAL_FILE}
        if any(name not in allowed for name in names):
            fail("transaction directory contains an unknown entry")
        prefix: list[str] = []
        for expected in EVENT_FILES:
            if expected not in names:
                break
            prefix.append(expected)
        if any(name not in prefix and name != TERMINAL_FILE for name in names):
            fail("transaction event sequence has a gap or reordering")
        if TERMINAL_FILE in names:
            prefix.append(TERMINAL_FILE)
        return prefix

    def _read_event(self, name: str) -> tuple[dict[str, Any], bytes]:
        flags = os.O_RDONLY | os.O_CLOEXEC | getattr(
            os, "O_NOFOLLOW", 0
        )
        try:
            descriptor = os.open(
                name, flags, dir_fd=self.cycle_descriptor
            )
        except OSError as error:
            raise TransactionError("transaction event is unsafe") from error
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.geteuid()
                or before.st_gid != os.getegid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o600
                or not 1 <= before.st_size <= MAX_EVENT_BYTES
            ):
                fail("transaction event metadata is unsafe")
            payload = bytearray()
            while len(payload) <= MAX_EVENT_BYTES:
                block = os.read(
                    descriptor,
                    min(65536, MAX_EVENT_BYTES + 1 - len(payload)),
                )
                if not block:
                    break
                payload.extend(block)
            after = os.fstat(descriptor)
            named = os.stat(
                name,
                dir_fd=self.cycle_descriptor,
                follow_symlinks=False,
            )
            if (
                len(payload) != before.st_size
                or stable_metadata(before) != stable_metadata(after)
                or stable_metadata(before) != stable_metadata(named)
            ):
                fail("transaction event changed while being read")
        finally:
            os.close(descriptor)
        raw = bytes(payload)
        if (
            not raw.endswith(b"\n")
            or raw.count(b"\n") != 1
            or b"\r" in raw
            or b"\0" in raw
        ):
            fail("transaction event encoding is not canonical")
        try:
            value = json.loads(
                raw,
                object_pairs_hook=reject_duplicate_keys,
            )
        except (UnicodeError, json.JSONDecodeError) as error:
            raise TransactionError(
                "transaction event is not canonical JSON"
            ) from error
        if not isinstance(value, dict) or canonical_json(value) != raw:
            fail("transaction event is not canonical JSON")
        return value, raw

    def _load(self) -> None:
        inventory = self._inventory()
        previous = ZERO_SHA256
        for index, filename in enumerate(inventory):
            value, payload = self._read_event(filename)
            exact_keys(
                value,
                {
                    "cycle_sha256",
                    "data",
                    "format",
                    "index",
                    "name",
                    "previous_sha256",
                },
                "transaction event",
            )
            expected_name = (
                "terminal"
                if filename == TERMINAL_FILE
                else EVENT_NAMES[index]
            )
            if (
                value["format"] != "rog5-retention-cycle-event-v1"
                or value["cycle_sha256"] != CYCLE_SHA256
                or value["index"] != index
                or value["name"] != expected_name
                or value["previous_sha256"] != previous
                or not isinstance(value["data"], dict)
            ):
                fail("transaction event identity or hash chain changed")
            self._state = self._transition(
                expected_name, value["data"], self._state
            )
            self._events.append((expected_name, payload))
            previous = hashlib.sha256(payload).hexdigest()
        if not self._events:
            return
        if self._events[0][0] != "cycle-opened":
            fail("transaction does not begin with its exact anchor")
        if self._inventory() != inventory:
            fail("transaction inventory changed while being read")

    def _known_inventory(self) -> list[str]:
        inventory: list[str] = []
        for index, (name, _) in enumerate(self._events):
            inventory.append(
                TERMINAL_FILE if name == "terminal" else EVENT_FILES[index]
            )
        return inventory

    def _transition(
        self,
        name: str,
        data: dict[str, Any],
        original: dict[str, Any],
    ) -> dict[str, Any]:
        state = dict(original)
        if state["terminal"]:
            fail("transaction is already terminal")
        expected_index = len(self._events)
        expected_name = (
            EVENT_NAMES[expected_index]
            if expected_index < len(EVENT_NAMES)
            else None
        )
        if name != "terminal" and name != expected_name:
            fail(f"expected {expected_name}")

        location = state["usb_location"]
        if name == "cycle-opened":
            exact_keys(
                data,
                {
                    "authority",
                    "boot_authority",
                    "claims_registered",
                    "host_boot_id",
                    "policy_allow_rows",
                    "usb_location",
                },
                name,
            )
            if (
                data["authority"] != "none"
                or data["boot_authority"] != "none"
                or data["claims_registered"] is not False
                or data["policy_allow_rows"] != 0
                or not isinstance(data["host_boot_id"], str)
                or BOOT_ID.fullmatch(data["host_boot_id"]) is None
                or not valid_location(data["usb_location"])
            ):
                fail("cycle anchor is not exact and authority-free")
            state["host_boot_id"] = data["host_boot_id"]
            state["usb_location"] = data["usb_location"]
        elif name in {
            "execution-claim-intent",
            "observer-claim-intent",
        }:
            exact_keys(data, {"identifier", "record_sha256"}, name)
            execution = name.startswith("execution")
            expected_identifier = (
                EXECUTION_CLAIM_IDENTIFIER
                if execution
                else OBSERVER_CLAIM_IDENTIFIER
            )
            expected_digest = (
                EXECUTION_CLAIM_SHA256
                if execution
                else OBSERVER_CLAIM_SHA256
            )
            if (
                data["identifier"] != expected_identifier
                or data["record_sha256"] != expected_digest
            ):
                fail(f"{name} does not bind the exact draft")
            state[
                "execution_claim" if execution else "observer_claim"
            ] = "unknown"
        elif name in {
            "execution-claim-entered",
            "observer-claim-entered",
        }:
            exact_keys(
                data,
                {"identifier", "record_sha256", "state"},
                name,
            )
            execution = name.startswith("execution")
            expected_identifier = (
                EXECUTION_CLAIM_IDENTIFIER
                if execution
                else OBSERVER_CLAIM_IDENTIFIER
            )
            expected_digest = (
                EXECUTION_CLAIM_SHA256
                if execution
                else OBSERVER_CLAIM_SHA256
            )
            if (
                data["identifier"] != expected_identifier
                or data["record_sha256"] != expected_digest
                or data["state"] != "consumed"
            ):
                fail(f"{name} is not exact")
            state[
                "execution_claim" if execution else "observer_claim"
            ] = "consumed"
        elif name in {
            "execution-boot-intent",
            "execution-recovery-observed",
        }:
            exact_keys(
                data,
                {"recovery_sha256", "rollback_armed", "usb_location"},
                name,
            )
            if (
                data["recovery_sha256"] != EXECUTION_RECOVERY_SHA256
                or data["rollback_armed"] is not True
                or data["usb_location"] != location
            ):
                fail("execution recovery lineage or rollback changed")
        elif name == "target-observed":
            exact_keys(
                data, {"candidate", "target_boot_id", "usb_location"}, name
            )
            if (
                data["candidate"] != CANDIDATE
                or not isinstance(data["target_boot_id"], str)
                or BOOT_ID.fullmatch(data["target_boot_id"]) is None
                or data["usb_location"] != location
            ):
                fail("target lineage is not exact")
            state["target_boot_id"] = data["target_boot_id"]
        elif name == "fallback-observed":
            exact_keys(
                data,
                {
                    "candidate",
                    "fallback_boot_id",
                    "intent_resolved",
                    "product",
                    "rollback_armed",
                    "serial",
                    "target_boot_id",
                    "usb_location",
                },
                name,
            )
            if (
                data["candidate"] != CANDIDATE
                or data["target_boot_id"] != state["target_boot_id"]
                or not isinstance(data["fallback_boot_id"], str)
                or BOOT_ID.fullmatch(data["fallback_boot_id"]) is None
                or data["fallback_boot_id"] == state["target_boot_id"]
                or data["usb_location"] != location
                or data["product"] != "1d6b:0104"
                or data["serial"] != "ROG5LINUX"
                or data["intent_resolved"] is not True
                or data["rollback_armed"] is not True
            ):
                fail("fallback identity or target correlation changed")
            state["fallback_boot_id"] = data["fallback_boot_id"]
        elif name == "retention-preflight":
            exact_keys(
                data,
                {
                    "fallback_boot_id",
                    "pstore_empty",
                    "ramoops_exact",
                    "usb_location",
                },
                name,
            )
            if (
                data["fallback_boot_id"] != state["fallback_boot_id"]
                or data["usb_location"] != location
                or data["ramoops_exact"] is not True
                or data["pstore_empty"] is not True
            ):
                fail("retention preflight is not exact")
        elif name == "bootloader-transition-intent":
            exact_keys(
                data, {"fallback_boot_id", "usb_location"}, name
            )
            if (
                data["fallback_boot_id"] != state["fallback_boot_id"]
                or data["usb_location"] != location
            ):
                fail("bootloader transition anchor changed")
        elif name == "bootloader-observed":
            exact_keys(
                data,
                {"fastboot_serial", "product", "usb_location"},
                name,
            )
            if (
                data["usb_location"] != location
                or data["product"] != "0b05:4daf"
                or not isinstance(data["fastboot_serial"], str)
                or SERIAL.fullmatch(data["fastboot_serial"]) is None
            ):
                fail("bootloader port, product, or serial changed")
            state["fastboot_serial"] = data["fastboot_serial"]
        elif name in {
            "observer-boot-intent",
            "observer-recovery-observed",
        }:
            exact_keys(
                data,
                {
                    "fastboot_serial",
                    "recovery_sha256",
                    "rollback_armed",
                    "usb_location",
                },
                name,
            )
            if (
                data["recovery_sha256"] != OBSERVER_RECOVERY_SHA256
                or data["usb_location"] != location
                or data["fastboot_serial"] != state["fastboot_serial"]
                or data["rollback_armed"] is not True
            ):
                fail("observer recovery lineage or rollback changed")
        elif name == "postmortem-read-intent":
            exact_keys(
                data,
                {"action", "candidate", "read_budget", "target_boot_id"},
                name,
            )
            if (
                data["action"] != "postmortem-status"
                or data["candidate"] != CANDIDATE
                or data["target_boot_id"] != state["target_boot_id"]
                or data["read_budget"] != 1
            ):
                fail("postmortem read intent is not exact")
            state["postmortem_reads"] = "unknown"
        elif name == "postmortem-result":
            exact_keys(
                data,
                {
                    "candidate",
                    "classification",
                    "reads",
                    "target_boot_id",
                },
                name,
            )
            if (
                data["candidate"] != CANDIDATE
                or data["target_boot_id"] != state["target_boot_id"]
                or data["classification"]
                not in POSTMORTEM_CLASSIFICATIONS
                or data["reads"] != 1
            ):
                fail("postmortem result is not exact and single-read")
            state["postmortem_reads"] = 1
            state["postmortem_classification"] = data["classification"]
            state["lineage_result"] = (
                "LINEAGE_RETAINED"
                if data["classification"] in {"MATCH", "MATCH_REPEATED"}
                else "INCONCLUSIVE"
            )
        elif name == "complete":
            expected = {
                "execution_claim": "consumed",
                "lineage_result": state["lineage_result"],
                "observer_claim": "consumed",
                "postmortem_classification": state[
                    "postmortem_classification"
                ],
                "postmortem_reads": 1,
                "retry": "forbidden",
            }
            if data != expected:
                fail("complete transaction result is not exact")
            state["terminal"] = True
        elif name == "terminal":
            expected = self._terminal_data(data.get("reason"), state)
            if data != expected:
                fail("terminal transaction result is not exact")
            state["terminal"] = True
        else:
            fail("transaction event name is unknown")
        return state

    def _append(self, name: str, data: dict[str, Any]) -> None:
        self._revalidate()
        if self._inventory() != self._known_inventory():
            fail("transaction inventory changed before append")
        if self._state["terminal"]:
            fail("transaction is already terminal")
        if (
            self._reopened
            and self._events
            and self._events[-1][0] in REOPEN_BLOCKED
            and name != "terminal"
        ):
            fail("reopened ambiguous action intent cannot be retried")
        candidate = self._transition(name, data, self._state)
        index = len(self._events)
        filename = (
            TERMINAL_FILE
            if name == "terminal"
            else EVENT_FILES[index]
        )
        previous = (
            hashlib.sha256(self._events[-1][1]).hexdigest()
            if self._events
            else ZERO_SHA256
        )
        payload = canonical_json(
            {
                "cycle_sha256": CYCLE_SHA256,
                "data": data,
                "format": "rog5-retention-cycle-event-v1",
                "index": index,
                "name": name,
                "previous_sha256": previous,
            }
        )
        if len(payload) > MAX_EVENT_BYTES:
            fail("transaction event is oversized")
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = -1
        try:
            descriptor = os.open(
                filename,
                flags,
                0o600,
                dir_fd=self.cycle_descriptor,
            )
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written < 1:
                    fail("transaction event write made no progress")
                view = view[written:]
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_gid != os.getegid()
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_size != len(payload)
            ):
                fail("published transaction event metadata is unsafe")
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        os.fsync(self.cycle_descriptor)
        self._revalidate()
        if self._inventory() != self._known_inventory() + [filename]:
            fail("transaction inventory changed during append")
        value, observed = self._read_event(filename)
        if observed != payload or value["name"] != name:
            fail("published transaction event changed")
        self._events.append((name, payload))
        self._state = candidate
        self._reopened = False

    def execution_claim_intent(self) -> None:
        self._append(
            "execution-claim-intent",
            {
                "identifier": EXECUTION_CLAIM_IDENTIFIER,
                "record_sha256": EXECUTION_CLAIM_SHA256,
            },
        )

    def execution_claim_entered(
        self, identifier: str, record_sha256: str
    ) -> None:
        self._append(
            "execution-claim-entered",
            {
                "identifier": identifier,
                "record_sha256": record_sha256,
                "state": "consumed",
            },
        )

    def execution_boot_intent(
        self,
        recovery_sha256: str,
        usb_location: str,
        rollback_armed: bool,
    ) -> None:
        self._append(
            "execution-boot-intent",
            {
                "recovery_sha256": recovery_sha256,
                "rollback_armed": rollback_armed,
                "usb_location": usb_location,
            },
        )

    def execution_recovery_observed(
        self,
        recovery_sha256: str,
        usb_location: str,
        rollback_armed: bool,
    ) -> None:
        self._append(
            "execution-recovery-observed",
            {
                "recovery_sha256": recovery_sha256,
                "rollback_armed": rollback_armed,
                "usb_location": usb_location,
            },
        )

    def target_observed(
        self, candidate: str, target_boot_id: str, usb_location: str
    ) -> None:
        self._append(
            "target-observed",
            {
                "candidate": candidate,
                "target_boot_id": target_boot_id,
                "usb_location": usb_location,
            },
        )

    def fallback_observed(
        self,
        candidate: str,
        target_boot_id: str,
        fallback_boot_id: str,
        usb_location: str,
        product: str,
        serial: str,
        intent_resolved: bool,
        rollback_armed: bool,
    ) -> None:
        self._append(
            "fallback-observed",
            {
                "candidate": candidate,
                "fallback_boot_id": fallback_boot_id,
                "intent_resolved": intent_resolved,
                "product": product,
                "rollback_armed": rollback_armed,
                "serial": serial,
                "target_boot_id": target_boot_id,
                "usb_location": usb_location,
            },
        )

    def retention_preflight(
        self,
        fallback_boot_id: str,
        usb_location: str,
        ramoops_exact: bool,
        pstore_empty: bool,
    ) -> None:
        self._append(
            "retention-preflight",
            {
                "fallback_boot_id": fallback_boot_id,
                "pstore_empty": pstore_empty,
                "ramoops_exact": ramoops_exact,
                "usb_location": usb_location,
            },
        )

    def bootloader_transition_intent(
        self, fallback_boot_id: str, usb_location: str
    ) -> None:
        self._append(
            "bootloader-transition-intent",
            {
                "fallback_boot_id": fallback_boot_id,
                "usb_location": usb_location,
            },
        )

    def bootloader_observed(
        self, usb_location: str, product: str, fastboot_serial: str
    ) -> None:
        self._append(
            "bootloader-observed",
            {
                "fastboot_serial": fastboot_serial,
                "product": product,
                "usb_location": usb_location,
            },
        )

    def observer_claim_intent(self) -> None:
        self._append(
            "observer-claim-intent",
            {
                "identifier": OBSERVER_CLAIM_IDENTIFIER,
                "record_sha256": OBSERVER_CLAIM_SHA256,
            },
        )

    def observer_claim_entered(
        self, identifier: str, record_sha256: str
    ) -> None:
        self._append(
            "observer-claim-entered",
            {
                "identifier": identifier,
                "record_sha256": record_sha256,
                "state": "consumed",
            },
        )

    def observer_boot_intent(
        self,
        recovery_sha256: str,
        usb_location: str,
        fastboot_serial: str,
        rollback_armed: bool,
    ) -> None:
        self._append(
            "observer-boot-intent",
            {
                "fastboot_serial": fastboot_serial,
                "recovery_sha256": recovery_sha256,
                "rollback_armed": rollback_armed,
                "usb_location": usb_location,
            },
        )

    def observer_recovery_observed(
        self,
        recovery_sha256: str,
        usb_location: str,
        fastboot_serial: str,
        rollback_armed: bool,
    ) -> None:
        self._append(
            "observer-recovery-observed",
            {
                "fastboot_serial": fastboot_serial,
                "recovery_sha256": recovery_sha256,
                "rollback_armed": rollback_armed,
                "usb_location": usb_location,
            },
        )

    def postmortem_read_intent(
        self, candidate: str, target_boot_id: str
    ) -> None:
        self._append(
            "postmortem-read-intent",
            {
                "action": "postmortem-status",
                "candidate": candidate,
                "read_budget": 1,
                "target_boot_id": target_boot_id,
            },
        )

    def postmortem_result(
        self,
        candidate: str,
        target_boot_id: str,
        classification: str,
        reads: int,
    ) -> None:
        self._append(
            "postmortem-result",
            {
                "candidate": candidate,
                "classification": classification,
                "reads": reads,
                "target_boot_id": target_boot_id,
            },
        )

    def finish(self) -> dict[str, Any]:
        if self._state["terminal"]:
            fail("transaction is already terminal")
        data = {
            "execution_claim": "consumed",
            "lineage_result": self._state["lineage_result"],
            "observer_claim": "consumed",
            "postmortem_classification": self._state[
                "postmortem_classification"
            ],
            "postmortem_reads": 1,
            "retry": "forbidden",
        }
        self._append("complete", data)
        return self.snapshot()

    def _terminal_data(
        self, reason: object, state: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(reason, str) or REASON.fullmatch(reason) is None:
            fail("terminal reason is not canonical")
        execution = state["execution_claim"]
        return {
            "execution_claim": execution,
            "failed_after": self._events[-1][0] if self._events else "none",
            "lineage_result": "INCONCLUSIVE",
            "observer_claim": state["observer_claim"],
            "postmortem_reads": state["postmortem_reads"],
            "reason": reason,
            "result": (
                "NO_BOOT" if execution == "absent" else "UNKNOWN"
            ),
            "retry": (
                "not-applicable"
                if execution == "absent"
                else "forbidden"
            ),
        }

    def terminate(self, reason: str) -> dict[str, Any]:
        if self._state["terminal"]:
            fail("transaction is already terminal")
        self._append("terminal", self._terminal_data(reason, self._state))
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        self._require_open()
        last = self._events[-1][0] if self._events else "none"
        phase = (
            "complete"
            if last == "complete"
            else "terminated" if last == "terminal" else last
        )
        next_event = "none"
        if not self._state["terminal"]:
            next_event = EVENT_NAMES[len(self._events)]
        execution = self._state["execution_claim"]
        return {
            "authority": "none",
            "boot_authority": "none",
            "cycle_sha256": CYCLE_SHA256,
            "execution_claim": execution,
            "fallback_boot_id": self._state["fallback_boot_id"],
            "fastboot_serial": self._state["fastboot_serial"],
            "host_boot_id": self._state["host_boot_id"],
            "lineage_result": self._state["lineage_result"],
            "next_event": next_event,
            "observer_claim": self._state["observer_claim"],
            "phase": phase,
            "postmortem_classification": self._state[
                "postmortem_classification"
            ],
            "postmortem_reads": self._state["postmortem_reads"],
            "profile": PROFILE,
            "result": (
                "NO_BOOT" if execution == "absent" else "UNKNOWN"
            ),
            "retry": (
                "not-applicable"
                if execution == "absent"
                else "forbidden"
            ),
            "target_boot_id": self._state["target_boot_id"],
            "usb_location": self._state["usb_location"],
        }

    def event_paths(self) -> tuple[Path, ...]:
        self._revalidate()
        names = self._inventory()
        return tuple(self.cycle_path / name for name in names)
