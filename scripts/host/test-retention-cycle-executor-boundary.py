#!/usr/bin/env python3
"""Hostile tests for the pure retention-cycle executor boundary."""

from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/retention-cycle-executor-boundary.py"
CONTRACT_SOURCE = REPO / "scripts/host/retention-cycle-executor-contract.py"
PROFILE = REPO / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
POLICY = REPO / "manifests/temporary-boot-images.tsv"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BOUNDARY = load_module("rog5_retention_executor_boundary", SOURCE)
CONTRACT = BOUNDARY.CONTRACT

TARGET_BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
FALLBACK_BOOT_ID = "fedcba98-7654-3210-fedc-ba9876543210"
USB_LOCATION = "pci0000:00/0000:00:14.0/usb1/1-3"
FASTBOOT_SERIAL = "M1AIB760D093XYZ"
FALLBACK_KNOWN_HOSTS = "/private/rog5/fallback-known-hosts"
REPOSITORY_UID = 1000
REPOSITORY_GID = 1000
OPEN_FLAGS = ("O_CLOEXEC", "O_NOFOLLOW", "O_RDONLY")
DIRECTORY_OPEN_FLAGS = (
    "O_CLOEXEC",
    "O_DIRECTORY",
    "O_NOFOLLOW",
    "O_RDONLY",
)
SSH_PREFIX = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
PIN_PAYLOAD = (
    "rog5-fallback ssh-ed25519 "
    + base64.b64encode(SSH_PREFIX + b"\x01" * 32).decode("ascii")
    + "\n"
).encode("ascii")
PIN_SHA256 = hashlib.sha256(PIN_PAYLOAD).hexdigest()


class RetentionCycleExecutorBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = CONTRACT.ExecutorInputs(
            target_boot_id=TARGET_BOOT_ID,
            fallback_boot_id=FALLBACK_BOOT_ID,
            usb_location=USB_LOCATION,
            fastboot_serial=FASTBOOT_SERIAL,
            fallback_known_hosts=FALLBACK_KNOWN_HOSTS,
        )
        self.specs = {
            item.name: item for item in CONTRACT.process_specs(self.inputs)
        }

    def file_evidence(
        self,
        name: str,
        *,
        device: int = 27,
        inode: int = 100,
    ):
        spec = self.specs[name]
        path = str(REPO / spec.program)
        return BOUNDARY.FileDescriptorEvidence(
            logical_path=path,
            resolved_path=path,
            link_target="none",
            revalidated_link_target="none",
            file_type="regular",
            uid=REPOSITORY_UID,
            gid=REPOSITORY_GID,
            mode=spec.program_mode,
            nlink=1,
            size=spec.program_size,
            sha256=spec.program_sha256,
            opened_device=device,
            opened_inode=inode,
            path_device=device,
            path_inode=inode,
            open_flags=OPEN_FLAGS,
        )

    def interpreter_evidence(
        self,
        name: str,
        *,
        device: int = 27,
        inode: int = 200,
    ):
        identity = BOUNDARY.INTERPRETERS[self.specs[name].argv[0]]
        return BOUNDARY.FileDescriptorEvidence(
            logical_path=identity.logical_path,
            resolved_path=identity.resolved_path,
            link_target=identity.link_target,
            revalidated_link_target=identity.link_target,
            file_type="regular",
            uid=0,
            gid=0,
            mode="0755",
            nlink=1,
            size=identity.size,
            sha256=identity.sha256,
            opened_device=device,
            opened_inode=inode,
            path_device=device,
            path_inode=inode,
            open_flags=OPEN_FLAGS,
        )

    def host_pin_evidence(self):
        return BOUNDARY.HostPinEvidence(
            file=BOUNDARY.FileDescriptorEvidence(
                logical_path=FALLBACK_KNOWN_HOSTS,
                resolved_path=FALLBACK_KNOWN_HOSTS,
                link_target="none",
                revalidated_link_target="none",
                file_type="regular",
                uid=REPOSITORY_UID,
                gid=REPOSITORY_GID,
                mode="0600",
                nlink=1,
                size=len(PIN_PAYLOAD),
                sha256=PIN_SHA256,
                opened_device=27,
                opened_inode=300,
                path_device=27,
                path_inode=300,
                open_flags=OPEN_FLAGS,
            ),
            parent=BOUNDARY.DirectoryDescriptorEvidence(
                logical_path=str(Path(FALLBACK_KNOWN_HOSTS).parent),
                resolved_path=str(Path(FALLBACK_KNOWN_HOSTS).parent),
                uid=REPOSITORY_UID,
                gid=REPOSITORY_GID,
                mode="0700",
                opened_device=27,
                opened_inode=301,
                path_device=27,
                path_inode=301,
                open_flags=DIRECTORY_OPEN_FLAGS,
            ),
            payload=PIN_PAYLOAD,
        )

    def attest(self, name: str, **updates):
        values = {
            "spec": self.specs[name],
            "inputs": self.inputs,
            "program": self.file_evidence(name),
            "interpreter": self.interpreter_evidence(name),
            "repository_uid": REPOSITORY_UID,
            "repository_gid": REPOSITORY_GID,
            "host_pin": self.host_pin_evidence()
            if name == "fallback-reboot"
            else None,
            "expected_host_pin_sha256": PIN_SHA256
            if name == "fallback-reboot"
            else "none",
        }
        values.update(updates)
        return BOUNDARY.attest_descriptors(**values)

    def outcome(self, name: str, stdout: bytes):
        return BOUNDARY.ProcessOutcome(
            name=name,
            exit_code=0,
            term_signal=None,
            timed_out=False,
            output_overflow=False,
            stdout=stdout,
            stderr=b"",
        )

    def boot_marker(self, name: str, *, pin_sha256: str = PIN_SHA256) -> bytes:
        records = {
            "execution-boot": (
                "ROG5_RETENTION_BOOT_RESULT_V1 action=execution-boot "
                f"recovery_sha256={BOUNDARY.ADAPTER.JOURNAL.EXECUTION_RECOVERY_SHA256} "
                f"rollback_armed=1 usb_location={USB_LOCATION}\n"
            ),
            "fallback-reboot": (
                "ROG5_RETENTION_BOOT_RESULT_V1 action=fallback-reboot "
                f"fastboot_serial={FASTBOOT_SERIAL} "
                f"host_pin_sha256={pin_sha256} product=0b05:4daf "
                f"usb_location={USB_LOCATION}\n"
            ),
            "observer-boot": (
                "ROG5_RETENTION_BOOT_RESULT_V1 action=observer-boot "
                f"fastboot_serial={FASTBOOT_SERIAL} "
                f"recovery_sha256={BOUNDARY.ADAPTER.JOURNAL.OBSERVER_RECOVERY_SHA256} "
                f"rollback_armed=1 usb_location={USB_LOCATION}\n"
            ),
        }
        return records[name].encode("ascii")

    def postmortem_record(self) -> dict[str, str]:
        expected = hashlib.sha256(
            (
                "rog5-network-root: lineage "
                "format=rog5-target-lineage-v1 candidate="
                f"headless-netroot-early-diag-v2 boot_id={TARGET_BOOT_ID}"
            ).encode("ascii")
        ).hexdigest()
        return {
            "classification": "MATCH",
            "expected_boot_id": TARGET_BOOT_ID,
            "expected_candidate": "headless-netroot-early-diag-v2",
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

    def test_exact_program_and_interpreter_descriptors_attest(self) -> None:
        for name in self.specs:
            with self.subTest(name=name):
                attestation = self.attest(name)
                self.assertEqual(attestation.name, name)
                self.assertEqual(
                    attestation.program_sha256,
                    self.specs[name].program_sha256,
                )
                self.assertEqual(
                    attestation.interpreter_sha256,
                    BOUNDARY.INTERPRETERS[
                        self.specs[name].argv[0]
                    ].sha256,
                )
                self.assertEqual(
                    attestation.host_pin_sha256,
                    PIN_SHA256 if name == "fallback-reboot" else "none",
                )

    def test_program_descriptor_mutations_fail_closed(self) -> None:
        baseline = self.file_evidence("execution-claim")
        mutations = (
            {"logical_path": "/tmp/consumer.py"},
            {"resolved_path": "/tmp/consumer.py"},
            {"link_target": "consumer.py"},
            {"revalidated_link_target": "consumer.py"},
            {"file_type": "directory"},
            {"uid": 0},
            {"gid": 0},
            {"mode": "0775"},
            {"nlink": 2},
            {"size": baseline.size + 1},
            {"sha256": "f" * 64},
            {"path_device": baseline.opened_device + 1},
            {"path_inode": baseline.opened_inode + 1},
            {"open_flags": ("O_RDONLY",)},
            {"uid": True},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    self.attest(
                        "execution-claim",
                        program=replace(baseline, **mutation),
                    )

    def test_interpreter_identity_and_symlink_are_exact(self) -> None:
        self.assertEqual(
            BOUNDARY.INTERPRETERS["/usr/bin/python3"].resolved_path,
            "/usr/bin/python3.13",
        )
        self.assertEqual(
            BOUNDARY.INTERPRETERS["/usr/bin/python3"].link_target,
            "python3.13",
        )
        self.assertEqual(
            BOUNDARY.INTERPRETERS["/usr/bin/bash"].link_target,
            "none",
        )
        baseline = self.interpreter_evidence("execution-claim")
        for mutation in (
            {"resolved_path": "/usr/bin/python3.12"},
            {"link_target": "python3.12"},
            {"revalidated_link_target": "python3.12"},
            {"uid": REPOSITORY_UID},
            {"mode": "0775"},
            {"sha256": "f" * 64},
            {"path_inode": baseline.opened_inode + 1},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    self.attest(
                        "execution-claim",
                        interpreter=replace(baseline, **mutation),
                    )

    def test_host_pin_requires_exact_snapshot_and_public_key(self) -> None:
        self.attest("fallback-reboot")
        pin = self.host_pin_evidence()
        with self.assertRaises(BOUNDARY.BoundaryError):
            self.attest("fallback-reboot", host_pin=None)
        with self.assertRaises(BOUNDARY.BoundaryError):
            self.attest(
                "execution-claim",
                host_pin=pin,
                expected_host_pin_sha256=PIN_SHA256,
            )
        hostile_files = (
            replace(pin.file, logical_path="/private/rog5/other"),
            replace(pin.file, resolved_path="/private/rog5/other"),
            replace(pin.file, mode="0644"),
            replace(pin.file, uid=0),
            replace(pin.file, nlink=2),
            replace(pin.file, sha256="f" * 64),
            replace(pin.file, path_inode=999),
        )
        for hostile in hostile_files:
            with self.subTest(hostile=hostile):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    self.attest(
                        "fallback-reboot",
                        host_pin=replace(pin, file=hostile),
                    )
        for hostile_parent in (
            replace(pin.parent, mode="0755"),
            replace(pin.parent, uid=0),
            replace(pin.parent, resolved_path="/tmp"),
            replace(pin.parent, path_device=999),
        ):
            with self.subTest(hostile_parent=hostile_parent):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    self.attest(
                        "fallback-reboot",
                        host_pin=replace(pin, parent=hostile_parent),
                    )
        malformed = (
            PIN_PAYLOAD + PIN_PAYLOAD,
            PIN_PAYLOAD.rstrip(b"\n"),
            PIN_PAYLOAD.replace(b"ssh-ed25519", b"ssh-rsa"),
            b"rog5-fallback ssh-ed25519 !!!\n",
            (
                "rog5-fallback ssh-ed25519 "
                + base64.b64encode(SSH_PREFIX + b"\x00" * 32).decode()
                + "\n"
            ).encode(),
        )
        for payload in malformed:
            digest = hashlib.sha256(payload).hexdigest()
            hostile_file = replace(
                pin.file,
                size=len(payload),
                sha256=digest,
            )
            with self.subTest(payload=payload):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    self.attest(
                        "fallback-reboot",
                        host_pin=replace(
                            pin, file=hostile_file, payload=payload
                        ),
                        expected_host_pin_sha256=digest,
                    )

    def test_claim_outputs_decode_exactly(self) -> None:
        for name, identifier, digest in (
            (
                "execution-claim",
                BOUNDARY.ADAPTER.JOURNAL.EXECUTION_CLAIM_IDENTIFIER,
                BOUNDARY.ADAPTER.JOURNAL.EXECUTION_CLAIM_SHA256,
            ),
            (
                "observer-claim",
                BOUNDARY.ADAPTER.JOURNAL.OBSERVER_CLAIM_IDENTIFIER,
                BOUNDARY.ADAPTER.JOURNAL.OBSERVER_CLAIM_SHA256,
            ),
        ):
            stdout = (
                f"PASS exact durable BOOT_CLAIMED record entered: "
                f"{identifier}\n"
            ).encode("ascii")
            result = BOUNDARY.decode_process_outcome(
                self.specs[name], self.inputs, self.outcome(name, stdout)
            )
            self.assertEqual(
                result,
                {
                    "identifier": identifier,
                    "record_sha256": digest,
                    "state": "consumed",
                },
            )

    def test_postmortem_json_decodes_exactly(self) -> None:
        record = self.postmortem_record()
        stdout = (
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")
        result = BOUNDARY.decode_process_outcome(
            self.specs["postmortem-read"],
            self.inputs,
            self.outcome("postmortem-read", stdout),
        )
        self.assertEqual(
            result,
            {
                "candidate": "headless-netroot-early-diag-v2",
                "classification": "MATCH",
                "reads": 1,
                "target_boot_id": TARGET_BOOT_ID,
            },
        )
        hostile = (
            {**record, "classification": "PASS"},
            {**record, "expected_boot_id": FALLBACK_BOOT_ID},
            {**record, "expected_candidate": "other"},
            {**record, "expected_lineage_sha256": "f" * 64},
            {**record, "observed_lineage_matches": "01"},
            {**record, "extra": "field"},
            {**record, "postmortem_records": 1},
        )
        for mutation in hostile:
            payload = (
                json.dumps(mutation, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("ascii")
            with self.subTest(mutation=mutation):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    BOUNDARY.decode_process_outcome(
                        self.specs["postmortem-read"],
                        self.inputs,
                        self.outcome("postmortem-read", payload),
                    )
        noncanonical = (
            (json.dumps(record) + "\n").encode("ascii"),
            (
                '{"classification":"MATCH","classification":"MATCH"}\n'
            ).encode("ascii"),
            (json.dumps(record, sort_keys=True) + "\n\n").encode("ascii"),
        )
        for payload in noncanonical:
            with self.subTest(payload=payload):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    BOUNDARY.decode_process_outcome(
                        self.specs["postmortem-read"],
                        self.inputs,
                        self.outcome("postmortem-read", payload),
                    )

    def test_common_process_failures_and_aliases_fail_closed(self) -> None:
        name = "execution-claim"
        stdout = (
            "PASS exact durable BOOT_CLAIMED record entered: "
            f"{BOUNDARY.ADAPTER.JOURNAL.EXECUTION_CLAIM_IDENTIFIER}\n"
        ).encode()
        baseline = self.outcome(name, stdout)
        hostile = (
            {"exit_code": 1},
            {"exit_code": False},
            {"term_signal": 9},
            {"timed_out": True},
            {"timed_out": 1},
            {"output_overflow": True},
            {"stderr": b"warning\n"},
            {"stdout": stdout.rstrip(b"\n")},
            {"stdout": stdout.replace(b"\n", b"\r\n")},
            {"stdout": stdout + b"extra\n"},
            {"stdout": stdout.replace(b"PASS", b"PASS\x00")},
            {"stdout": b"x" * (self.specs[name].output_limit_bytes + 1)},
        )
        for mutation in hostile:
            with self.subTest(mutation=mutation):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    BOUNDARY.decode_process_outcome(
                        self.specs[name],
                        self.inputs,
                        replace(baseline, **mutation),
                    )

    def test_boot_results_decode_one_exact_terminal_record(self) -> None:
        expected = {
            "execution-boot": {
                "recovery_sha256": (
                    BOUNDARY.ADAPTER.JOURNAL.EXECUTION_RECOVERY_SHA256
                ),
                "rollback_armed": True,
                "usb_location": USB_LOCATION,
            },
            "fallback-reboot": {
                "fastboot_serial": FASTBOOT_SERIAL,
                "product": "0b05:4daf",
                "usb_location": USB_LOCATION,
            },
            "observer-boot": {
                "fastboot_serial": FASTBOOT_SERIAL,
                "recovery_sha256": (
                    BOUNDARY.ADAPTER.JOURNAL.OBSERVER_RECOVERY_SHA256
                ),
                "rollback_armed": True,
                "usb_location": USB_LOCATION,
            },
        }
        self.assertEqual(
            BOUNDARY.LIVE_PRODUCER_STATE,
            {
                "execution-boot": "hold-gate-no-current-success",
                "fallback-reboot": "guarded-producer-defined",
                "observer-boot": "hold-gate-no-current-success",
            },
        )
        for name in expected:
            with self.subTest(name=name):
                outcome = replace(
                    self.outcome(
                        name,
                        b"bounded helper diagnostic\n" + self.boot_marker(name),
                    ),
                    stderr=b"bounded child diagnostic\n",
                )
                result = BOUNDARY.decode_process_outcome(
                    self.specs[name],
                    self.inputs,
                    outcome,
                    attestation=self.attest(name),
                )
                self.assertEqual(result, expected[name])

    def test_boot_result_records_fail_closed(self) -> None:
        old_markers = {
            "execution-boot": (
                b"PASS temporary stable recovery ready at /dev/ttyACM0\n"
            ),
            "fallback-reboot": (
                b"PASS pinned Alpine fallback reached exact fastboot device\n"
            ),
            "observer-boot": (
                b"PASS temporary observation recovery ready at /dev/ttyACM0\n"
            ),
        }
        for name, stdout in old_markers.items():
            with self.subTest(name=name, case="old-marker"):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    BOUNDARY.decode_process_outcome(
                        self.specs[name],
                        self.inputs,
                        self.outcome(name, stdout),
                        attestation=self.attest(name),
                    )

        baseline = self.boot_marker("fallback-reboot")
        hostile = (
            baseline.replace(b"fallback-reboot", b"execution-boot"),
            baseline.replace(USB_LOCATION.encode(), b"pci/usb1/other"),
            baseline.replace(FASTBOOT_SERIAL.encode(), b"OTHER"),
            baseline.replace(PIN_SHA256.encode(), b"f" * 64),
            baseline.replace(b"product=0b05:4daf", b"product=18d1:4ee0"),
            baseline.rstrip(b"\n"),
            baseline.replace(b"\n", b"\r\n"),
            baseline.replace(b" usb_location=", b" extra=1 usb_location="),
            baseline + baseline,
            baseline + b"trailing\n",
            b"echo " + baseline + baseline,
            baseline.replace(b"ROG5_", b"ROG5_\x00"),
        )
        for stdout in hostile:
            with self.subTest(stdout=stdout):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    BOUNDARY.decode_process_outcome(
                        self.specs["fallback-reboot"],
                        self.inputs,
                        self.outcome("fallback-reboot", stdout),
                        attestation=self.attest("fallback-reboot"),
                    )
        with self.assertRaises(BOUNDARY.BoundaryError):
            BOUNDARY.decode_process_outcome(
                self.specs["fallback-reboot"],
                self.inputs,
                replace(
                    self.outcome("fallback-reboot", baseline),
                    stderr=baseline,
                ),
                attestation=self.attest("fallback-reboot"),
            )
        for attestation in (None, self.attest("execution-claim")):
            with self.subTest(attestation=attestation):
                with self.assertRaises(BOUNDARY.BoundaryError):
                    BOUNDARY.decode_process_outcome(
                        self.specs["fallback-reboot"],
                        self.inputs,
                        self.outcome("fallback-reboot", baseline),
                        attestation=attestation,
                    )

    def test_source_has_no_executor_or_io_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for token in (
            "subprocess",
            "socket",
            "Popen",
            "os.open",
            "os.stat",
            "os.environ",
            "pathlib.Path.open",
            "SSH_KEY",
            "GITHUB_TOKEN",
        ):
            self.assertNotIn(token, source)
        self.assertNotIn("if __name__ ==", source)
        self.assertEqual(BOUNDARY.BUILTIN_EXECUTOR, "none")
        self.assertEqual(BOUNDARY.LIVE_ENTRYPOINT, "none")
        self.assertEqual(BOUNDARY.CREDENTIAL_USE, "none")
        self.assertEqual(BOUNDARY.CONNECTED_ADMISSION, "none")

    def test_hold_claim_and_policy_state_remains_closed(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(profile["state"], "hold")
        self.assertEqual(profile["authority"], "none")
        self.assertEqual(profile["boot_authority"], "none")
        self.assertEqual(profile["claims"]["execution"], "not-defined")
        self.assertEqual(profile["claims"]["observer"], "not-defined")
        rows = [
            line.split("\t")
            for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
            if line
        ]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn(
            "retention-host-rendezvous-v3-execution-v1", consumer
        )
        self.assertIn(
            "retention-host-rendezvous-v3-observer-v1", consumer
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
