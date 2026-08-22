#!/usr/bin/env python3
"""Hardware-free tests for the stage-1 GPT backup/ACK protocol."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/collect-storage-layout-stage1.py"
SPEC = importlib.util.spec_from_file_location("collect_storage_layout_stage1", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load stage-1 collector")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

OPERATION = "0123456789abcdef0123456789abcdef"
NONCE = "abcdef0123456789abcdef0123456789"
READY = (
    "ROG5_LAYOUT_STAGE1_V1 status=HOST_READY "
    f"operation_id={OPERATION}\n"
).encode("ascii")


class FakeTransport:
    def __init__(self, incoming: bytes) -> None:
        self.incoming = bytearray(incoming)
        self.outgoing = bytearray()

    def readline(self, maximum: int, _timeout: float) -> bytes:
        newline = self.incoming.find(b"\n")
        if newline < 0 or newline + 1 > maximum:
            raise MODULE.LayoutProtocolError("line framing is not exact")
        result = bytes(self.incoming[: newline + 1])
        del self.incoming[: newline + 1]
        return result

    def read_exact(self, size: int, _timeout: float) -> bytes:
        if len(self.incoming) < size:
            raise MODULE.LayoutProtocolError("backup payload ended early")
        result = bytes(self.incoming[:size])
        del self.incoming[:size]
        return result

    def write_all(self, payload: bytes, _timeout: float) -> None:
        self.outgoing.extend(payload)


def backups() -> dict[str, bytes]:
    primary = bytearray(24_576)
    primary[510:512] = b"\x55\xaa"
    primary[4096:4104] = b"EFI PART"
    secondary = bytearray(20_480)
    secondary[-4096:-4088] = b"EFI PART"
    return {
        "sgdisk.gpt": b"sealed-sgdisk-backup" * 1024,
        "primary.raw": bytes(primary),
        "secondary.raw": bytes(secondary),
    }


def backup_set_sha(files: dict[str, bytes]) -> str:
    records = "".join(
        f"{name}:{hashlib.sha256(files[name]).hexdigest()}:{len(files[name])}\n"
        for name in MODULE.FILE_ORDER
    ).encode("ascii")
    return hashlib.sha256(records).hexdigest()


def protocol(files: dict[str, bytes], *, operation: str = OPERATION) -> bytes:
    seal = backup_set_sha(files)
    parts = [
        b"ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S10_TOPOLOGY reason=none\n",
        (
            "ROG5_LAYOUT_STAGE1_V1 status=BACKUP_BEGIN "
            f"operation_id={operation} nonce={NONCE} files=3 "
            f"backup_set_sha256={seal}\n"
        ).encode("ascii"),
    ]
    for name in MODULE.FILE_ORDER:
        payload = files[name]
        digest = hashlib.sha256(payload).hexdigest()
        parts.extend(
            (
                (
                    "ROG5_LAYOUT_STAGE1_V1 status=BACKUP_FILE "
                    f"name={name} size={len(payload)} sha256={digest}\n"
                ).encode("ascii"),
                payload,
                b"\n",
                (
                    "ROG5_LAYOUT_STAGE1_V1 status=BACKUP_FILE_END "
                    f"name={name}\n"
                ).encode("ascii"),
            )
        )
    parts.append(
        (
            "ROG5_LAYOUT_STAGE1_V1 status=BACKUP_END "
            f"operation_id={operation} nonce={NONCE} "
            f"backup_set_sha256={seal}\n"
        ).encode("ascii")
    )
    return b"".join(parts)


class CollectorTests(unittest.TestCase):
    def test_host_ready_precedes_target_read(self) -> None:
        class ReadyRequiredTransport(FakeTransport):
            def readline(self, maximum: int, timeout: float) -> bytes:
                if self.outgoing != READY:
                    raise AssertionError("target bytes read before host-ready")
                return super().readline(maximum, timeout)

        transport = ReadyRequiredTransport(protocol(backups()))
        with tempfile.TemporaryDirectory() as directory:
            MODULE.receive_backup_set(
                transport, Path(directory) / "generation-stage1", OPERATION, 2
            )
        self.assertTrue(transport.outgoing.startswith(READY))

    def test_execution_record_is_finalized_before_ack(self) -> None:
        files = backups()
        transport = FakeTransport(protocol(files))
        template = {
            "format": "rog5-storage-layout-stage1-execution-v1",
            "status": "authorized_waiting_fresh_backup",
            "operation_id": OPERATION,
            "device_identity": {"usb_location": "1-1.2"},
            "old_geometry": {"userdata_last_lba": 61865978},
            "new_geometry": {"userdata_last_lba": 53477375},
            "backup_hashes": {"inventory_sha256": "a" * 64},
            "commands": ["resize2fs EXACT_USERDATA 51124000"],
            "abort_conditions": ["identity mismatch"],
            "rollback_limitations": ["filesystem growth is not automatic"],
        }
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            template_path = parent / "execution-template.json"
            template_path.write_text(
                json.dumps(template, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="ascii",
            )
            template_path.chmod(0o600)
            loaded, template_sha256 = MODULE.load_execution_record_template(
                template_path, OPERATION, "1-1.2"
            )
            output = parent / "generation-stage1"

            def before_ack(manifest: dict[str, object]) -> None:
                self.assertEqual(transport.outgoing, READY)
                MODULE.finalize_execution_record(
                    output, loaded, template_sha256, manifest
                )
                record_path = output / "execution-record.json"
                self.assertTrue(record_path.is_file())
                self.assertEqual(os.stat(record_path).st_mode & 0o777, 0o600)

            manifest = MODULE.receive_backup_set(
                transport, output, OPERATION, 2, before_ack=before_ack
            )
            record = json.loads(
                (output / "execution-record.json").read_text(encoding="ascii")
            )
            self.assertEqual(
                record["status"], "fresh_backup_durable_mutation_ack_ready"
            )
            self.assertEqual(record["fresh_backup"], manifest)
            self.assertEqual(record["template_sha256"], template_sha256)

    def test_exact_backup_is_durable_before_ack(self) -> None:
        files = backups()
        transport = FakeTransport(protocol(files))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generation-stage1"
            evidence = MODULE.receive_backup_set(transport, output, OPERATION, 2)
            self.assertEqual(evidence["backup_set_sha256"], backup_set_sha(files))
            self.assertFalse((output / ".incomplete").exists())
            self.assertTrue((output / "ack-sent.txt").is_file())
            manifest = json.loads((output / "manifest.json").read_text(encoding="ascii"))
            self.assertTrue(manifest["ack_prepared"])
            self.assertNotIn("acknowledged", manifest)
            for name, payload in files.items():
                self.assertEqual((output / name).read_bytes(), payload)
                self.assertEqual(manifest["files"][name]["sha256"], hashlib.sha256(payload).hexdigest())
        expected_ack = (
            "ROG5_LAYOUT_STAGE1_V1 status=BACKUP_ACK "
            f"operation_id={OPERATION} nonce={NONCE} "
            f"backup_set_sha256={backup_set_sha(files)}\n"
        ).encode("ascii")
        self.assertEqual(bytes(transport.outgoing), READY + expected_ack)

    def test_payload_hash_mismatch_never_acks(self) -> None:
        files = backups()
        payload = protocol(files).replace(b"sealed-sgdisk", b"sealed-Sgdisk", 1)
        transport = FakeTransport(payload)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(MODULE.LayoutProtocolError, "hash"):
                MODULE.receive_backup_set(transport, Path(directory) / "bad", OPERATION, 2)
        self.assertEqual(transport.outgoing, READY)

    def test_execution_record_failure_never_acks(self) -> None:
        transport = FakeTransport(protocol(backups()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bad-record"

            def fail_record(_manifest: dict[str, object]) -> None:
                raise MODULE.LayoutProtocolError("record finalization failed")

            with self.assertRaisesRegex(
                MODULE.LayoutProtocolError, "record finalization failed"
            ):
                MODULE.receive_backup_set(
                    transport, output, OPERATION, 2, before_ack=fail_record
                )
            self.assertTrue((output / ".incomplete").is_file())
        self.assertEqual(transport.outgoing, READY)

    def test_terminal_pass_requires_every_exact_field(self) -> None:
        seal = "a" * 64
        valid = (
            "ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S32_WATCHDOG_DISARM reason=none\n"
            "ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S40_FILESYSTEM_CHECK reason=none\n"
            "ROG5_LAYOUT_STAGE1_V1 status=PASS stage=S99_COMPLETE reason=none "
            f"operation_id={OPERATION} userdata_last_lba=53477375 "
            "arch_root_first_lba=53477376 arch_root_last_lba=61865978 "
            f"filesystem_blocks=51124000 backup_set_sha256={seal} "
            "all_read_only=1 block_mounts=0\n"
        ).encode("ascii")
        transport = FakeTransport(valid)
        terminal = MODULE.capture_terminal(transport, OPERATION, seal, 2)
        self.assertIn(b"status=PASS", terminal)

        duplicate = valid.replace(
            f"operation_id={OPERATION}".encode("ascii"),
            f"operation_id={OPERATION} operation_id={OPERATION}".encode("ascii"),
        )
        with self.assertRaisesRegex(MODULE.LayoutProtocolError, "field count"):
            MODULE.capture_terminal(FakeTransport(duplicate), OPERATION, seal, 2)

    def test_userdata_reset_terminal_is_exact(self) -> None:
        seal = "b" * 64
        valid = (
            "ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S40_FORMAT reason=none\n"
            "ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S70_POSTVERIFY reason=none\n"
            "ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S80_LOCK reason=none\n"
            "ROG5_LAYOUT_STAGE1_V1 status=PASS stage=S99_COMPLETE reason=none "
            f"operation_id={OPERATION} operation=userdata_ext4_reset "
            "gpt_changed=0 userdata_last_lba=61865978 "
            "filesystem_blocks=59513299 "
            "filesystem_uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5 "
            f"filesystem_label=rog5-linux backup_set_sha256={seal} "
            "all_read_only=1 block_mounts=0\n"
        ).encode("ascii")
        terminal = MODULE.capture_terminal(
            FakeTransport(valid), OPERATION, seal, 2, "userdata-ext4-reset-v1"
        )
        self.assertIn(b"gpt_changed=0", terminal)

        wrong = valid.replace(b"gpt_changed=0", b"gpt_changed=1")
        with self.assertRaisesRegex(MODULE.LayoutProtocolError, "PASS identity"):
            MODULE.capture_terminal(
                FakeTransport(wrong), OPERATION, seal, 2, "userdata-ext4-reset-v1"
            )

    def test_wrong_operation_never_acks(self) -> None:
        transport = FakeTransport(protocol(backups(), operation="f" * 32))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(MODULE.LayoutProtocolError, "operation"):
                MODULE.receive_backup_set(transport, Path(directory) / "bad", OPERATION, 2)
        self.assertEqual(transport.outgoing, READY)

    def test_exact_prebackup_failure_is_terminal_and_never_acks(self) -> None:
        payload = (
            "ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage=S10_TOPOLOGY reason=none\n"
            "ROG5_LAYOUT_STAGE1_V1 status=FAIL stage=S10_TOPOLOGY "
            "reason=userdata_content_changed gpt_restored=not_needed\n"
        ).encode("ascii")
        transport = FakeTransport(payload)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "must-not-exist"
            with self.assertRaisesRegex(
                MODULE.LayoutProtocolError,
                "pre-backup target failure: stage=S10_TOPOLOGY "
                "reason=userdata_content_changed gpt_restored=not_needed",
            ):
                MODULE.receive_backup_set(transport, output, OPERATION, 2)
            self.assertFalse(output.exists())
        self.assertEqual(transport.outgoing, READY)

    def test_wrong_file_order_never_acks(self) -> None:
        payload = protocol(backups()).replace(b"name=sgdisk.gpt", b"name=primary.raw", 1)
        transport = FakeTransport(payload)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(MODULE.LayoutProtocolError, "file header"):
                MODULE.receive_backup_set(transport, Path(directory) / "bad", OPERATION, 2)
        self.assertEqual(transport.outgoing, READY)

    def test_invalid_raw_gpt_signature_never_acks(self) -> None:
        files = backups()
        primary = bytearray(files["primary.raw"])
        primary[4096:4104] = b"NOT GPT!"
        files["primary.raw"] = bytes(primary)
        transport = FakeTransport(protocol(files))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(MODULE.LayoutProtocolError, "primary GPT"):
                MODULE.receive_backup_set(transport, Path(directory) / "bad", OPERATION, 2)
        self.assertEqual(transport.outgoing, READY)

    def test_existing_output_refuses_before_read_or_ack(self) -> None:
        transport = FakeTransport(protocol(backups()))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing"
            output.mkdir()
            with self.assertRaisesRegex(MODULE.LayoutProtocolError, "already exists"):
                MODULE.receive_backup_set(transport, output, OPERATION, 2)
        self.assertEqual(transport.outgoing, b"")


if __name__ == "__main__":
    unittest.main(verbosity=2)
