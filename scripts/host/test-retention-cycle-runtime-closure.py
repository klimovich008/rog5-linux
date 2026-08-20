#!/usr/bin/env python3
"""Hostile tests for the disconnected retention runtime closure fixture."""

from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
from unittest import mock
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/retention-cycle-runtime-closure.py"
PROFILE = REPO / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
POLICY = REPO / "manifests/temporary-boot-images.tsv"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNTIME = load_module("rog5_retention_runtime_closure", SOURCE)
BOUNDARY = RUNTIME.BOUNDARY
CONTRACT = BOUNDARY.CONTRACT
JOURNAL = CONTRACT.ADAPTER.JOURNAL

HOST_BOOT_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_HOST_BOOT_ID = "11111111-2222-4333-8444-555555555555"
TARGET_BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
FALLBACK_BOOT_ID = "fedcba98-7654-3210-fedc-ba9876543210"
USB_LOCATION = "pci0000:00/0000:00:14.0/usb1/1-3"
FASTBOOT_SERIAL = "M1AIB760D093XYZ"
SSH_PREFIX = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
PIN_PAYLOAD = (
    "rog5-fallback ssh-ed25519 "
    + base64.b64encode(SSH_PREFIX + b"\x01" * 32).decode("ascii")
    + "\n"
).encode("ascii")
PIN_SHA256 = hashlib.sha256(PIN_PAYLOAD).hexdigest()


def pinned_interpreters_available() -> bool:
    """Return true only on the exact deployment host runtime."""

    try:
        for identity in BOUNDARY.INTERPRETERS.values():
            logical = Path(identity.logical_path)
            resolved = Path(identity.resolved_path)
            logical_metadata = logical.lstat()
            if identity.link_target == "none":
                if logical != resolved or not stat.S_ISREG(
                    logical_metadata.st_mode
                ):
                    return False
            elif (
                not stat.S_ISLNK(logical_metadata.st_mode)
                or logical_metadata.st_uid != 0
                or logical_metadata.st_gid != 0
                or os.readlink(logical) != identity.link_target
            ):
                return False
            resolved_metadata = resolved.stat(follow_symlinks=False)
            if (
                not stat.S_ISREG(resolved_metadata.st_mode)
                or resolved_metadata.st_uid != 0
                or resolved_metadata.st_gid != 0
                or resolved_metadata.st_nlink != 1
                or stat.S_IMODE(resolved_metadata.st_mode) != 0o755
                or resolved_metadata.st_size != identity.size
                or hashlib.sha256(resolved.read_bytes()).hexdigest()
                != identity.sha256
            ):
                return False
    except OSError:
        return False
    return True


@unittest.skipUnless(
    pinned_interpreters_available(),
    "requires the exact pinned deployment-host interpreters",
)
class RetentionCycleRuntimeClosureTest(unittest.TestCase):
    @staticmethod
    def current_specs(inputs):
        specs = {item.name: item for item in CONTRACT.process_specs(inputs)}
        for name, item in tuple(specs.items()):
            program = REPO / item.program
            metadata = program.lstat()
            if not stat.S_ISREG(metadata.st_mode) or program.is_symlink():
                raise AssertionError("runtime fixture program is not repository-owned")
            specs[name] = replace(
                item,
                program_size=metadata.st_size,
                program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(),
                program_mode=f"{stat.S_IMODE(metadata.st_mode):04o}",
            )
        return specs

    def make_journal(self, host_boot_id: str = HOST_BOOT_ID):
        temporary = tempfile.TemporaryDirectory(prefix="rog5-runtime-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "state"
        root.mkdir(mode=0o700)
        journal = JOURNAL.CycleJournal.create(
            root, host_boot_id, USB_LOCATION
        )
        self.addCleanup(journal.close)
        pin_parent = Path(temporary.name) / "pin"
        pin_parent.mkdir(mode=0o700)
        pin = pin_parent / "fallback-known-hosts"
        inputs = CONTRACT.ExecutorInputs(
            target_boot_id=TARGET_BOOT_ID,
            fallback_boot_id=FALLBACK_BOOT_ID,
            usb_location=USB_LOCATION,
            fastboot_serial=FASTBOOT_SERIAL,
            fallback_known_hosts=str(pin),
        )
        specs = self.current_specs(inputs)
        return root, journal, pin, inputs, specs

    @staticmethod
    def claim_stdout() -> bytes:
        return (
            "PASS exact durable BOOT_CLAIMED record entered: "
            f"{JOURNAL.EXECUTION_CLAIM_IDENTIFIER}\n"
        ).encode("ascii")

    @staticmethod
    def observer_claim_stdout() -> bytes:
        return (
            "PASS exact durable BOOT_CLAIMED record entered: "
            f"{JOURNAL.OBSERVER_CLAIM_IDENTIFIER}\n"
        ).encode("ascii")

    @staticmethod
    def boot_stdout(name: str) -> bytes:
        records = {
            "execution-boot": (
                "ROG5_RETENTION_BOOT_RESULT_V1 action=execution-boot "
                f"recovery_sha256={JOURNAL.EXECUTION_RECOVERY_SHA256} "
                f"rollback_armed=1 usb_location={USB_LOCATION}\n"
            ),
            "fallback-reboot": (
                "ROG5_RETENTION_BOOT_RESULT_V1 action=fallback-reboot "
                f"fastboot_serial={FASTBOOT_SERIAL} "
                f"host_pin_sha256={PIN_SHA256} product=0b05:4daf "
                f"usb_location={USB_LOCATION}\n"
            ),
            "observer-boot": (
                "ROG5_RETENTION_BOOT_RESULT_V1 action=observer-boot "
                f"fastboot_serial={FASTBOOT_SERIAL} "
                f"recovery_sha256={JOURNAL.OBSERVER_RECOVERY_SHA256} "
                f"rollback_armed=1 usb_location={USB_LOCATION}\n"
            ),
        }
        return records[name].encode("ascii")

    @staticmethod
    def postmortem_stdout() -> bytes:
        expected = hashlib.sha256(
            (
                "rog5-network-root: lineage "
                f"format=rog5-target-lineage-v1 candidate={JOURNAL.CANDIDATE} "
                f"boot_id={TARGET_BOOT_ID}"
            ).encode("ascii")
        ).hexdigest()
        record = {
            "classification": "MATCH",
            "expected_boot_id": TARGET_BOOT_ID,
            "expected_candidate": JOURNAL.CANDIDATE,
            "expected_lineage_sha256": expected,
            "observed_lineage_matches": "1",
            "observed_lineage_sha256": expected,
            "postmortem_bytes": "100",
            "postmortem_records": "1",
            "postmortem_sha256": "a" * 64,
            "postmortem_state": "PRESENT",
            "recovery_session": "1" * 32,
            "status_request": "2" * 32,
        }
        return (
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")

    def run_action(
        self,
        journal,
        spec,
        inputs,
        stdout: bytes,
        *,
        pin_sha256: str = "none",
    ):
        current = tuple(self.current_specs(inputs).values())
        with mock.patch.object(CONTRACT, "process_specs", return_value=current):
            prepared = RUNTIME.prepare_action(
                journal=journal,
                spec=spec,
                inputs=inputs,
                expected_host_pin_sha256=pin_sha256,
            )
            proof = RUNTIME.run_offline_fixture(
                prepared,
                RUNTIME.OfflineChildPlan(stdout, b"", 0, 0, False),
                deadline_milliseconds=500,
            )
            decoded = RUNTIME.decode_offline_fixture(prepared, proof)
        return prepared, decoded.result

    def prepare_claim(self, host_boot_id: str = HOST_BOOT_ID):
        root, journal, pin, inputs, specs = self.make_journal(host_boot_id)
        journal.execution_claim_intent()
        prepared = RUNTIME.prepare_action(
            journal=journal,
            spec=specs["execution-claim"],
            inputs=inputs,
            expected_host_pin_sha256="none",
        )
        self.addCleanup(prepared.close)
        return root, journal, pin, inputs, specs, prepared

    @staticmethod
    def advance_to_fallback_intent(journal) -> None:
        journal.execution_claim_intent()
        journal.execution_claim_entered(
            JOURNAL.EXECUTION_CLAIM_IDENTIFIER,
            JOURNAL.EXECUTION_CLAIM_SHA256,
        )
        journal.execution_boot_intent(
            JOURNAL.EXECUTION_RECOVERY_SHA256,
            USB_LOCATION,
            True,
        )
        journal.execution_recovery_observed(
            JOURNAL.EXECUTION_RECOVERY_SHA256,
            USB_LOCATION,
            True,
        )
        journal.target_observed(
            JOURNAL.CANDIDATE, TARGET_BOOT_ID, USB_LOCATION
        )
        journal.fallback_observed(
            JOURNAL.CANDIDATE,
            TARGET_BOOT_ID,
            FALLBACK_BOOT_ID,
            USB_LOCATION,
            "1d6b:0104",
            "ROG5LINUX",
            True,
            True,
        )
        journal.retention_preflight(
            FALLBACK_BOOT_ID, USB_LOCATION, True, True
        )
        journal.bootloader_transition_intent(
            FALLBACK_BOOT_ID, USB_LOCATION
        )

    @classmethod
    def advance_to_postmortem_intent(cls, journal) -> None:
        cls.advance_to_fallback_intent(journal)
        journal.bootloader_observed(
            USB_LOCATION, "0b05:4daf", FASTBOOT_SERIAL
        )
        journal.observer_claim_intent()
        journal.observer_claim_entered(
            JOURNAL.OBSERVER_CLAIM_IDENTIFIER,
            JOURNAL.OBSERVER_CLAIM_SHA256,
        )
        journal.observer_boot_intent(
            JOURNAL.OBSERVER_RECOVERY_SHA256,
            USB_LOCATION,
            FASTBOOT_SERIAL,
            True,
        )
        journal.observer_recovery_observed(
            JOURNAL.OBSERVER_RECOVERY_SHA256,
            USB_LOCATION,
            FASTBOOT_SERIAL,
            True,
        )
        journal.postmortem_read_intent(JOURNAL.CANDIDATE, TARGET_BOOT_ID)

    def test_real_descriptors_and_fsynced_intent_are_held(self) -> None:
        _, journal, _, _, specs, prepared = self.prepare_claim()
        self.assertEqual(prepared.action, "execution-claim")
        self.assertEqual(
            prepared.intent.required_intent, "execution-claim-intent"
        )
        self.assertEqual(prepared.intent.cycle_sha256, JOURNAL.CYCLE_SHA256)
        self.assertRegex(prepared.intent.event_sha256, r"^[0-9a-f]{64}$")
        self.assertGreater(prepared.intent.opened_inode, 0)
        self.assertEqual(
            prepared.descriptors.program_sha256,
            specs["execution-claim"].program_sha256,
        )
        self.assertEqual(
            prepared.descriptors.interpreter_sha256,
            BOUNDARY.INTERPRETERS["/usr/bin/python3"].sha256,
        )
        self.assertEqual(prepared.descriptors.host_pin_sha256, "none")
        self.assertEqual(journal.snapshot()["phase"], prepared.intent.required_intent)
        for descriptor in prepared.held_descriptors:
            self.assertGreaterEqual(os.fstat(descriptor).st_ino, 1)

    def test_fresh_private_pipes_bind_one_decodable_fixture(self) -> None:
        _, _, _, _, _, prepared = self.prepare_claim()
        proof = RUNTIME.run_offline_fixture(
            prepared,
            RUNTIME.OfflineChildPlan(
                stdout=self.claim_stdout(),
                stderr=b"",
                exit_code=0,
                delay_milliseconds=0,
                descendant_holds_pipes=False,
            ),
            deadline_milliseconds=500,
        )
        self.assertTrue(proof.stdout_eof)
        self.assertTrue(proof.stderr_eof)
        self.assertNotEqual(proof.stdout_pipe_inode, proof.stderr_pipe_inode)
        self.assertLess(proof.intent.checked_ns, proof.pipe_created_ns)
        self.assertLess(proof.pipe_created_ns, proof.spawned_ns)
        self.assertLessEqual(proof.spawned_ns, proof.finished_ns)
        self.assertRegex(proof.runtime_nonce, r"^[0-9a-f]{64}$")
        decoded = RUNTIME.decode_offline_fixture(prepared, proof)
        self.assertEqual(
            decoded.result,
            {
                "identifier": JOURNAL.EXECUTION_CLAIM_IDENTIFIER,
                "record_sha256": JOURNAL.EXECUTION_CLAIM_SHA256,
                "state": "consumed",
            },
        )
        self.assertEqual(decoded.authority, "none")
        self.assertFalse(decoded.adapter_eligible)
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "already decoded"
        ):
            RUNTIME.decode_offline_fixture(prepared, proof)
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "already attempted"
        ):
            RUNTIME.run_offline_fixture(
                prepared,
                RUNTIME.OfflineChildPlan(
                    self.claim_stdout(), b"", 0, 0, False
                ),
                deadline_milliseconds=500,
            )

    def test_all_six_actions_release_only_after_exact_result_events(self) -> None:
        _, journal, pin, inputs, specs = self.make_journal()
        pin.write_bytes(PIN_PAYLOAD)
        pin.chmod(0o600)

        journal.execution_claim_intent()
        prepared, result = self.run_action(
            journal,
            specs["execution-claim"],
            inputs,
            self.claim_stdout(),
        )
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "did not advance"
        ):
            RUNTIME.finalize_offline_fixture(prepared)
        journal.execution_claim_entered(
            str(result["identifier"]), str(result["record_sha256"])
        )
        RUNTIME.finalize_offline_fixture(prepared)

        journal.execution_boot_intent(
            JOURNAL.EXECUTION_RECOVERY_SHA256, USB_LOCATION, True
        )
        prepared, result = self.run_action(
            journal,
            specs["execution-boot"],
            inputs,
            self.boot_stdout("execution-boot"),
        )
        journal.execution_recovery_observed(
            str(result["recovery_sha256"]),
            str(result["usb_location"]),
            result["rollback_armed"] is True,
        )
        RUNTIME.finalize_offline_fixture(prepared)

        journal.target_observed(
            JOURNAL.CANDIDATE, TARGET_BOOT_ID, USB_LOCATION
        )
        journal.fallback_observed(
            JOURNAL.CANDIDATE,
            TARGET_BOOT_ID,
            FALLBACK_BOOT_ID,
            USB_LOCATION,
            "1d6b:0104",
            "ROG5LINUX",
            True,
            True,
        )
        journal.retention_preflight(
            FALLBACK_BOOT_ID, USB_LOCATION, True, True
        )
        journal.bootloader_transition_intent(
            FALLBACK_BOOT_ID, USB_LOCATION
        )
        prepared, result = self.run_action(
            journal,
            specs["fallback-reboot"],
            inputs,
            self.boot_stdout("fallback-reboot"),
            pin_sha256=PIN_SHA256,
        )
        journal.bootloader_observed(
            str(result["usb_location"]),
            str(result["product"]),
            str(result["fastboot_serial"]),
        )
        RUNTIME.finalize_offline_fixture(prepared)

        journal.observer_claim_intent()
        prepared, result = self.run_action(
            journal,
            specs["observer-claim"],
            inputs,
            self.observer_claim_stdout(),
        )
        journal.observer_claim_entered(
            str(result["identifier"]), str(result["record_sha256"])
        )
        RUNTIME.finalize_offline_fixture(prepared)

        journal.observer_boot_intent(
            JOURNAL.OBSERVER_RECOVERY_SHA256,
            USB_LOCATION,
            FASTBOOT_SERIAL,
            True,
        )
        prepared, result = self.run_action(
            journal,
            specs["observer-boot"],
            inputs,
            self.boot_stdout("observer-boot"),
        )
        journal.observer_recovery_observed(
            str(result["recovery_sha256"]),
            str(result["usb_location"]),
            str(result["fastboot_serial"]),
            result["rollback_armed"] is True,
        )
        RUNTIME.finalize_offline_fixture(prepared)

        journal.postmortem_read_intent(JOURNAL.CANDIDATE, TARGET_BOOT_ID)
        prepared, result = self.run_action(
            journal,
            specs["postmortem-read"],
            inputs,
            self.postmortem_stdout(),
        )
        journal.postmortem_result(
            str(result["candidate"]),
            str(result["target_boot_id"]),
            str(result["classification"]),
            int(result["reads"]),
        )
        RUNTIME.finalize_offline_fixture(prepared)
        final = journal.finish()
        self.assertEqual(final["phase"], "complete")
        self.assertEqual(final["execution_claim"], "consumed")
        self.assertEqual(final["observer_claim"], "consumed")
        self.assertEqual(final["postmortem_reads"], 1)
        self.assertEqual(final["retry"], "forbidden")

    def test_valid_but_different_result_event_is_refused(self) -> None:
        _, journal, _, inputs, specs = self.make_journal()
        self.advance_to_postmortem_intent(journal)
        prepared, result = self.run_action(
            journal,
            specs["postmortem-read"],
            inputs,
            self.postmortem_stdout(),
        )
        self.assertEqual(result["classification"], "MATCH")
        journal.postmortem_result(
            JOURNAL.CANDIDATE,
            TARGET_BOOT_ID,
            "NO_MARKER",
            1,
        )
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "differs from decoded child"
        ):
            RUNTIME.finalize_offline_fixture(prepared)

    def test_result_event_path_replacement_before_release_is_refused(self) -> None:
        _, journal, _, inputs, specs = self.make_journal()
        journal.execution_claim_intent()
        prepared, result = self.run_action(
            journal,
            specs["execution-claim"],
            inputs,
            self.claim_stdout(),
        )
        journal.execution_claim_entered(
            str(result["identifier"]), str(result["record_sha256"])
        )
        result_path = journal.event_paths()[-1]
        displaced_path = result_path.with_name(result_path.name + ".displaced")
        real_open = RUNTIME._open_journal_event

        def open_then_replace(*args, **kwargs):
            opened = real_open(*args, **kwargs)
            payload = result_path.read_bytes()
            result_path.rename(displaced_path)
            result_path.write_bytes(payload)
            result_path.chmod(0o600)
            return opened

        with mock.patch.object(
            RUNTIME,
            "_open_journal_event",
            side_effect=open_then_replace,
        ), self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "action result event changed"
        ):
            RUNTIME.finalize_offline_fixture(prepared)
        self.assertTrue(hasattr(journal, RUNTIME.JOURNAL_MARKER))
        self.assertFalse(prepared._finalized)

    def test_cross_cycle_proof_and_reopened_intent_are_rejected(self) -> None:
        root1, journal1, _, _, _, prepared1 = self.prepare_claim(HOST_BOOT_ID)
        _, _, _, _, _, prepared2 = self.prepare_claim(OTHER_HOST_BOOT_ID)
        proof1 = RUNTIME.run_offline_fixture(
            prepared1,
            RUNTIME.OfflineChildPlan(
                self.claim_stdout(), b"", 0, 0, False
            ),
            deadline_milliseconds=500,
        )
        self.assertNotEqual(
            prepared1.intent.event_sha256, prepared2.intent.event_sha256
        )
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "different prepared action"
        ):
            RUNTIME.decode_offline_fixture(prepared2, proof1)

        prepared2.close()
        journal1.close()
        reopened = JOURNAL.CycleJournal.open(root1)
        self.addCleanup(reopened.close)
        inputs = prepared1.inputs
        spec = {
            item.name: item for item in CONTRACT.process_specs(inputs)
        }["execution-claim"]
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "reopened action intent"
        ):
            RUNTIME.prepare_action(
                journal=reopened,
                spec=spec,
                inputs=inputs,
                expected_host_pin_sha256="none",
            )

    def test_concurrent_prepare_and_path_replacement_fail_closed(self) -> None:
        _, journal, _, inputs, specs, prepared = self.prepare_claim()
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "already prepared"
        ):
            RUNTIME.prepare_action(
                journal=journal,
                spec=specs["execution-claim"],
                inputs=inputs,
                expected_host_pin_sha256="none",
            )

        intent_path = prepared.intent.path
        original = intent_path.read_bytes()
        moved = intent_path.with_suffix(".moved")
        intent_path.rename(moved)
        intent_path.write_bytes(original)
        intent_path.chmod(0o600)
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "intent record changed"
        ):
            RUNTIME.run_offline_fixture(
                prepared,
                RUNTIME.OfflineChildPlan(
                    self.claim_stdout(), b"", 0, 0, False
                ),
                deadline_milliseconds=500,
            )
        self.assertTrue(prepared.attempted)

    def test_journal_change_while_child_runs_invalidates_result(self) -> None:
        _, journal, _, _, _, prepared = self.prepare_claim()
        real_revalidate = RUNTIME._revalidate_prepared
        calls = 0

        def advance_before_final_revalidation(selected) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                journal.execution_claim_entered(
                    JOURNAL.EXECUTION_CLAIM_IDENTIFIER,
                    JOURNAL.EXECUTION_CLAIM_SHA256,
                )
            real_revalidate(selected)

        with mock.patch.object(
            RUNTIME,
            "_revalidate_prepared",
            side_effect=advance_before_final_revalidation,
        ):
            with self.assertRaisesRegex(
                RUNTIME.RuntimeClosureError, "journal changed during action"
            ):
                RUNTIME.run_offline_fixture(
                    prepared,
                    RUNTIME.OfflineChildPlan(
                        self.claim_stdout(), b"", 0, 100, False
                    ),
                    deadline_milliseconds=500,
                )
        self.assertEqual(journal.snapshot()["phase"], "execution-claim-entered")

    def test_preloaded_pipe_is_refused_before_fork(self) -> None:
        _, _, _, _, _, prepared = self.prepare_claim()
        real_new_pipe = RUNTIME._new_pipe

        def preloaded_pipe():
            read_descriptor, write_descriptor = real_new_pipe()
            os.write(write_descriptor, b"stale")
            return read_descriptor, write_descriptor

        with mock.patch.object(
            RUNTIME, "_new_pipe", side_effect=preloaded_pipe
        ), self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "fresh pipe was not empty"
        ):
            RUNTIME.run_offline_fixture(
                prepared,
                RUNTIME.OfflineChildPlan(
                    self.claim_stdout(), b"", 0, 0, False
                ),
                deadline_milliseconds=500,
            )
        self.assertTrue(prepared.attempted)

    def test_timeout_descendant_and_output_overflow_are_bounded(self) -> None:
        _, _, _, _, _, timeout_prepared = self.prepare_claim(HOST_BOOT_ID)
        started = time.monotonic()
        timeout_proof = RUNTIME.run_offline_fixture(
            timeout_prepared,
            RUNTIME.OfflineChildPlan(
                self.claim_stdout(), b"", 0, 500, True
            ),
            deadline_milliseconds=40,
        )
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertTrue(timeout_proof.outcome.timed_out)
        with self.assertRaises(BOUNDARY.BoundaryError):
            RUNTIME.decode_offline_fixture(timeout_prepared, timeout_proof)

        _, _, _, _, specs, overflow_prepared = self.prepare_claim(
            OTHER_HOST_BOOT_ID
        )
        overflow_proof = RUNTIME.run_offline_fixture(
            overflow_prepared,
            RUNTIME.OfflineChildPlan(
                b"x" * (specs["execution-claim"].output_limit_bytes + 1),
                b"",
                0,
                0,
                False,
            ),
            deadline_milliseconds=500,
        )
        self.assertTrue(overflow_proof.outcome.output_overflow)
        self.assertLessEqual(
            len(overflow_proof.outcome.stdout),
            specs["execution-claim"].output_limit_bytes + 1,
        )
        with self.assertRaises(BOUNDARY.BoundaryError):
            RUNTIME.decode_offline_fixture(overflow_prepared, overflow_proof)

    def test_actual_host_pin_is_held_and_symlinks_fail(self) -> None:
        _, journal, pin, inputs, specs = self.make_journal()
        pin.write_bytes(PIN_PAYLOAD)
        pin.chmod(0o600)
        self.advance_to_fallback_intent(journal)
        prepared = RUNTIME.prepare_action(
            journal=journal,
            spec=specs["fallback-reboot"],
            inputs=inputs,
            expected_host_pin_sha256=PIN_SHA256,
        )
        self.addCleanup(prepared.close)
        self.assertEqual(
            prepared.descriptors.host_pin_sha256, PIN_SHA256
        )
        self.assertEqual(prepared.host_pin_payload, PIN_PAYLOAD)
        prepared.close()

        real_pin = pin.with_name("real-pin")
        pin.rename(real_pin)
        pin.symlink_to(real_pin.name)
        with self.assertRaises((RUNTIME.RuntimeClosureError, OSError)):
            RUNTIME.prepare_action(
                journal=journal,
                spec=specs["fallback-reboot"],
                inputs=inputs,
                expected_host_pin_sha256=PIN_SHA256,
            )

    def test_wrong_spec_and_host_pin_digest_fail_before_attempt(self) -> None:
        _, journal, _, inputs, specs = self.make_journal()
        journal.execution_claim_intent()
        wrong = RUNTIME.dataclass_replace(
            specs["execution-claim"], timeout_seconds=16
        )
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "reviewed contract"
        ):
            RUNTIME.prepare_action(
                journal=journal,
                spec=wrong,
                inputs=inputs,
                expected_host_pin_sha256="none",
            )
        with self.assertRaisesRegex(
            RUNTIME.RuntimeClosureError, "host pin digest"
        ):
            RUNTIME.prepare_action(
                journal=journal,
                spec=specs["execution-claim"],
                inputs=inputs,
                expected_host_pin_sha256="f" * 64,
            )

    def test_fixture_has_no_live_or_adapter_execution_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for token in (
            "subprocess",
            "execve",
            "execv",
            "socket",
            "os.environ",
            "getpass",
            "GITHUB_TOKEN",
            "SSH_KEY",
            "if __name__ ==",
        ):
            self.assertNotIn(token, source)
        self.assertEqual(RUNTIME.LIVE_ENTRYPOINT, "none")
        self.assertEqual(RUNTIME.ADAPTER_WIRING, "none")
        self.assertEqual(RUNTIME.PRODUCTION_EXECUTION, "none")
        self.assertEqual(RUNTIME.CONNECTED_ADMISSION, "none")
        self.assertEqual(RUNTIME.CREDENTIAL_USE, "none")
        self.assertEqual(RUNTIME.RESULT_AUTHORITY, "none")

        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        runtime = profile["claims"]["executor_runtime"]
        self.assertEqual(runtime["path"], SOURCE.relative_to(REPO).as_posix())
        self.assertEqual(runtime["implementation"], "offline-fresh-pipe-fixture-v1")
        self.assertEqual(runtime["live_entrypoint"], "none")
        self.assertEqual(runtime["adapter_wiring"], "none")
        self.assertEqual(runtime["production_execution"], "none")
        self.assertEqual(runtime["production_descriptor_execution"], "unproven")
        self.assertEqual(runtime["credential_use"], "none")
        self.assertEqual(runtime["result_authority"], "none")
        self.assertEqual(profile["state"], "hold")
        self.assertEqual(profile["authority"], "none")
        self.assertEqual(profile["boot_authority"], "none")
        self.assertEqual(profile["claims"]["execution"], "not-defined")
        self.assertEqual(profile["claims"]["observer"], "not-defined")
        self.assertEqual(
            profile["claims"]["executor_boundary"]["runtime_closure"],
            "offline-fixture-only-production-descriptor-execution-unproven",
        )
        rows = [
            line.split("\t")
            for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
            if line
        ]
        self.assertEqual(
            sum(
                row[0]
                == "build/observation-recovery-mainline-udc-v11-generation10-20260811-r1/repack/stable-recovery-a.avb.img"
                and row[1] == "allow"
                for row in rows
            ),
            1,
        )
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn(
            "retention-host-rendezvous-v3-execution-v1", consumer
        )
        self.assertIn(
            "retention-host-rendezvous-v3-observer-v1", consumer
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
