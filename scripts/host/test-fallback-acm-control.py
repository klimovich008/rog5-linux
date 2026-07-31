#!/usr/bin/env python3
"""Hardware-free tests for the pinned Alpine fallback ACM controller."""

from __future__ import annotations

import ast
import base64
from collections import OrderedDict
import ctypes
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import pty
import shlex
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


sys.dont_write_bytecode = True
SOURCE = Path(__file__).with_name("fallback-acm-control.py")
SPEC = importlib.util.spec_from_file_location("fallback_acm_control", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record(
    nonce: str,
    action: str = "preflight",
    **updates: str,
) -> tuple[OrderedDict[str, str], bytes]:
    values = OrderedDict(
        (
            ("format", MODULE.FORMAT),
            ("nonce", nonce),
            ("action", action),
            ("kernel_release", MODULE.FALLBACK_KERNEL),
            ("init", "/bin/busybox"),
            ("compatible", "qcom,lahaina-mtp"),
            ("root_fstype", "ext4"),
            ("modules_checked", "1"),
            ("project_modules", "0"),
            ("pstore_checked", "1"),
            ("pstore_records", "0"),
            ("dmesg_checked", "1"),
            ("fatal_lines", "0"),
            ("thermal_samples", "3"),
            ("thermal_zones", "70"),
            ("thermal_max", "38800"),
            ("python_major", "3"),
            ("boot_id", "11111111-2222-4333-8444-555555555555"),
            ("result", "PASS"),
        )
    )
    values.update(updates)
    payload = "".join(
        f"{key}={value}\n" for key, value in values.items()
    ).encode("ascii")
    return values, payload


def frame(nonce: str, action: str = "preflight") -> bytes:
    _, payload = record(nonce, action)
    output = (
        b"\x1b[6nnoisy prompt\r\n"
        + f"ROG5_FALLBACK_ACM_BEGIN {nonce}\r\n".encode()
        + base64.b64encode(payload)
        + b"\r\n"
        + base64.b64encode(b"synthetic-signature")
        + b"\r\n"
        + f"ROG5_FALLBACK_ACM_END {nonce} PREPARED\r\n".encode()
    )
    if action != "reboot":
        output += b"~ # \x1b[6n"
    return output


def read_line(descriptor: int) -> bytes:
    output = bytearray()
    while not output.endswith(b"\n"):
        output.extend(os.read(descriptor, 1))
    return bytes(output)


class FrameTest(unittest.TestCase):
    def test_exact_correlated_frame_passes(self) -> None:
        nonce = "a" * 32
        values, payload, signature = MODULE.parse_frame(
            frame(nonce),
            nonce,
            "preflight",
        )
        self.assertEqual(values["result"], "PASS")
        self.assertEqual(payload, record(nonce)[1])
        self.assertEqual(signature, b"synthetic-signature")

    def test_echo_cannot_satisfy_a_frame(self) -> None:
        nonce = "b" * 32
        launcher, chunks = MODULE.remote_transport(nonce, "preflight")
        wire = launcher + b"".join(chunks)
        self.assertNotIn(b"ROG5_FALLBACK_LOADER_READY", launcher)
        self.assertNotIn(b"ROG5_FALLBACK_ACM_BEGIN", wire)
        self.assertNotIn(b"ROG5_FALLBACK_ACM_END", wire)
        with self.assertRaises(MODULE.FallbackError):
            MODULE.parse_frame(wire, nonce, "preflight")

    def test_truncated_duplicate_and_wrong_nonce_frames_fail(self) -> None:
        nonce = "c" * 32
        valid = frame(nonce)
        cases = (
            valid.split(b"ROG5_FALLBACK_ACM_END", 1)[0],
            valid + valid,
            valid.replace(nonce.encode(), b"d" * 32),
            valid.replace(b"PREPARED", b"PASS"),
        )
        for candidate in cases:
            with self.subTest(candidate=candidate[-80:]):
                with self.assertRaises(MODULE.FallbackError):
                    MODULE.parse_frame(candidate, nonce, "preflight")

    def test_every_signed_health_mutation_fails(self) -> None:
        nonce = "e" * 32
        mutations = {
            "kernel_release": "wrong",
            "init": "/sbin/init",
            "compatible": "qcom,lahaina",
            "root_fstype": "tmpfs",
            "modules_checked": "0",
            "project_modules": "1",
            "pstore_checked": "0",
            "pstore_records": "1",
            "dmesg_checked": "0",
            "fatal_lines": "1",
            "thermal_samples": "2",
            "thermal_zones": "0",
            "thermal_max": "60001",
            "python_major": "2",
            "boot_id": "not-a-boot-id",
            "result": "FAIL",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                _, payload = record(nonce, **{field: value})
                with self.assertRaises(MODULE.FallbackError):
                    MODULE.parse_record(payload, nonce, "preflight")

    def test_record_rejects_reordering_and_trailing_fields(self) -> None:
        nonce = "f" * 32
        _, payload = record(nonce)
        lines = payload.splitlines(keepends=True)
        for candidate in (
            b"".join((lines[1], lines[0], *lines[2:])),
            payload + b"unexpected=value\n",
            payload[:-1],
        ):
            with self.assertRaises(MODULE.FallbackError):
                MODULE.parse_record(candidate, nonce, "preflight")

    def test_return_classification_has_a_separate_hard_thermal_ceiling(
        self,
    ) -> None:
        nonce = "f" * 32
        _, warm_return = record(
            nonce,
            "classify",
            thermal_max="61400",
        )
        values = MODULE.parse_record(warm_return, nonce, "classify")
        self.assertEqual(values["thermal_max"], "61400")
        _, warm_preflight = record(
            nonce,
            "preflight",
            thermal_max="61400",
        )
        with self.assertRaises(MODULE.FallbackError):
            MODULE.parse_record(warm_preflight, nonce, "preflight")
        _, unsafe_return = record(
            nonce,
            "classify",
            thermal_max="80001",
        )
        with self.assertRaises(MODULE.FallbackError):
            MODULE.parse_record(unsafe_return, nonce, "classify")


class SignatureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-fallback-signature-"
        )
        self.root = Path(self.temporary.name)
        self.key = self.root / "host-key"
        subprocess.run(
            [
                str(MODULE.SSH_KEYGEN),
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(self.key),
            ],
            check=True,
        )
        fields = self.key.with_suffix(".pub").read_text().split()
        self.known_hosts = self.root / "known-hosts"
        self.known_hosts.write_text(
            f"{MODULE.HOST_ALIAS} {fields[0]} {fields[1]}\n",
            encoding="ascii",
        )
        self.known_hosts.chmod(0o600)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def signature(self, payload: bytes) -> bytes:
        result = subprocess.run(
            [
                str(MODULE.SSH_KEYGEN),
                "-Y",
                "sign",
                "-f",
                str(self.key),
                "-n",
                MODULE.SIGN_NAMESPACE,
                "-",
            ],
            input=payload,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return result.stdout

    def test_real_host_key_signature_passes(self) -> None:
        payload = record("1" * 32)[1]
        MODULE.verify_signature(
            MODULE.verify_known_hosts(self.known_hosts),
            payload,
            self.signature(payload),
        )

    def test_payload_signature_and_pin_mutations_fail(self) -> None:
        payload = record("2" * 32)[1]
        signature = self.signature(payload)
        pin = MODULE.verify_known_hosts(self.known_hosts)
        with self.assertRaises(MODULE.FallbackError):
            MODULE.verify_signature(
                pin,
                payload + b"x",
                signature,
            )
        other = self.root / "other"
        subprocess.run(
            [
                str(MODULE.SSH_KEYGEN),
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(other),
            ],
            check=True,
        )
        fields = other.with_suffix(".pub").read_text().split()
        wrong_pin = self.root / "wrong-pin"
        wrong_pin.write_text(
            f"{MODULE.HOST_ALIAS} {fields[0]} {fields[1]}\n",
            encoding="ascii",
        )
        wrong_pin.chmod(0o600)
        with self.assertRaises(MODULE.FallbackError):
            MODULE.verify_signature(
                MODULE.verify_known_hosts(wrong_pin),
                payload,
                signature,
            )

    def test_pin_requires_one_exact_private_record(self) -> None:
        self.assertEqual(
            MODULE.verify_known_hosts(self.known_hosts),
            self.known_hosts.read_bytes(),
        )
        for payload in (
            "",
            "wrong ssh-ed25519 AAAA\n",
            self.known_hosts.read_text() * 2,
        ):
            path = self.root / hashlib_name(payload)
            path.write_text(payload, encoding="ascii")
            path.chmod(0o600)
            with self.subTest(payload=payload):
                with self.assertRaises(MODULE.FallbackError):
                    MODULE.verify_known_hosts(path)
        loose = self.root / "loose"
        loose.mkdir(mode=0o755)
        loose_pin = loose / "pin"
        loose_pin.write_bytes(self.known_hosts.read_bytes())
        loose_pin.chmod(0o600)
        with self.assertRaises(MODULE.FallbackError):
            MODULE.verify_known_hosts(loose_pin)
        with (
            mock.patch.object(MODULE, "REPO", self.root),
            self.assertRaises(MODULE.FallbackError),
        ):
            MODULE.verify_known_hosts(self.known_hosts)

    def test_verification_uses_the_inspected_pin_snapshot(self) -> None:
        payload = record("4" * 32)[1]
        pin = MODULE.verify_known_hosts(self.known_hosts)
        self.known_hosts.unlink()
        self.known_hosts.write_text(
            (
                f"{MODULE.HOST_ALIAS} ssh-ed25519 "
                "AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAA\n"
            ),
            encoding="ascii",
        )
        self.known_hosts.chmod(0o600)
        MODULE.verify_signature(pin, payload, self.signature(payload))


def hashlib_name(value: str) -> str:
    return "pin-" + hashlib.sha256(value.encode()).hexdigest()


class UsbFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-fallback-usb-"
        )
        self.root = Path(self.temporary.name)
        self.devices = self.root / "devices"
        self.bus = self.root / "bus"
        self.tty = self.root / "tty"
        self.raw = self.devices / "pci/usb1/1-1/1-1.2"
        self.interface = self.raw / "1-1.2:1.2"
        (self.interface / "tty/ttyACM7").mkdir(parents=True)
        self.bus.mkdir()
        self.tty.mkdir()
        (self.raw / "idVendor").write_text(MODULE.USB_VENDOR)
        (self.raw / "idProduct").write_text(MODULE.USB_PRODUCT)
        (self.raw / "product").write_text(MODULE.USB_PRODUCT_NAME)
        (self.bus / "1-1.2").symlink_to(self.raw)
        (self.tty / "ttyACM7").symlink_to(
            self.interface / "tty/ttyACM7"
        )
        self.location = self.raw.relative_to(self.devices).as_posix()

    def close(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def properties() -> dict[str, str]:
        return {
            "ID_VENDOR_ID": MODULE.USB_VENDOR,
            "ID_MODEL_ID": MODULE.USB_PRODUCT,
            "ID_MODEL": MODULE.USB_MODEL,
            "ID_USB_DRIVER": MODULE.USB_DRIVER,
            "ID_USB_INTERFACE_NUM": MODULE.USB_INTERFACE,
        }


class UsbIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = UsbFixture()
        self.patches = (
            mock.patch.object(MODULE, "SYS_DEVICES", self.fixture.devices),
            mock.patch.object(MODULE, "SYS_BUS_USB", self.fixture.bus),
            mock.patch.object(MODULE, "SYS_CLASS_TTY", self.fixture.tty),
            mock.patch.object(
                MODULE.glob,
                "glob",
                return_value=["/dev/ttyACM7"],
            ),
            mock.patch.object(
                MODULE,
                "udev_properties",
                return_value=self.fixture.properties(),
            ),
            mock.patch.object(MODULE.os, "access", return_value=True),
        )
        for patch in self.patches:
            patch.start()
        real_stat = os.stat

        def fake_stat(path: object, *, follow_symlinks: bool = True):
            if str(path) in {"/dev/ttyACM7", "/dev/ttyACM8"}:
                return mock.Mock(st_mode=stat.S_IFCHR | 0o660, st_rdev=16647)
            return real_stat(path, follow_symlinks=follow_symlinks)

        self.stat = mock.patch.object(MODULE.os, "stat", side_effect=fake_stat)
        self.stat.start()

    def tearDown(self) -> None:
        self.stat.stop()
        for patch in reversed(self.patches):
            patch.stop()
        self.fixture.close()

    def test_exact_usb_product_interface_and_location_pass(self) -> None:
        self.assertEqual(
            MODULE.find_fallback_acm(self.fixture.location),
            ("/dev/ttyACM7", self.fixture.location, 16647),
        )
        MODULE.udev_properties.reset_mock()
        MODULE.revalidate_fallback_acm(
            "/dev/ttyACM7",
            self.fixture.location,
            16647,
        )
        MODULE.udev_properties.assert_called_once_with("/dev/ttyACM7")

    def test_wrong_expected_port_and_wrong_interface_fail(self) -> None:
        with self.assertRaises(MODULE.FallbackError):
            MODULE.find_fallback_acm("pci/usb1/1-1/1-1.9")
        with (
            mock.patch.object(
                MODULE,
                "udev_properties",
                return_value={
                    **self.fixture.properties(),
                    "ID_USB_INTERFACE_NUM": "03",
                },
            ),
            self.assertRaises(MODULE.FallbackError),
        ):
            MODULE.find_fallback_acm()

    def test_duplicate_product_and_duplicate_acm_fail(self) -> None:
        duplicate = self.fixture.devices / "pci/usb1/1-1/1-1.3"
        duplicate.mkdir(parents=True)
        (duplicate / "idVendor").write_text(MODULE.USB_VENDOR)
        (duplicate / "idProduct").write_text(MODULE.USB_PRODUCT)
        (duplicate / "product").write_text(MODULE.USB_PRODUCT_NAME)
        (self.fixture.bus / "1-1.3").symlink_to(duplicate)
        with self.assertRaises(MODULE.FallbackError):
            MODULE.find_fallback_acm()
        (self.fixture.bus / "1-1.3").unlink()
        (self.fixture.tty / "ttyACM8").symlink_to(
            self.fixture.interface / "tty/ttyACM7"
        )
        with (
            mock.patch.object(
                MODULE.glob,
                "glob",
                return_value=["/dev/ttyACM7", "/dev/ttyACM8"],
            ),
            self.assertRaises(MODULE.FallbackError),
        ):
            MODULE.find_fallback_acm()


class SerialTest(unittest.TestCase):
    def run_probe(
        self,
        action: str,
        *,
        duplicate_shell_ready: bool = False,
    ) -> tuple[OrderedDict[str, str] | None, bytes]:
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        device_number = os.stat(path).st_rdev
        nonce = "3" * 32
        observed = bytearray()
        commit_consumed = threading.Event()
        read_until = MODULE.FallbackSerial.read_until

        def emulate() -> None:
            reset, sync_command, shell_ready = MODULE.shell_sync_transport(
                nonce
            )
            actual_reset = read_line(master)
            self.assertEqual(actual_reset, reset)
            observed.extend(actual_reset)
            actual_sync = read_line(master)
            self.assertEqual(actual_sync, sync_command)
            observed.extend(actual_sync)
            os.write(master, f"{shell_ready}\r\n".encode())
            launcher = read_line(master)
            observed.extend(launcher)
            if duplicate_shell_ready:
                os.write(master, f"{shell_ready}\r\n".encode())
            os.write(
                master,
                f"ROG5_FALLBACK_LOADER_READY {nonce}\r\n".encode(),
            )
            _, source_chunks = MODULE.remote_transport(nonce, action)
            for expected_chunk in source_chunks:
                actual_chunk = read_line(master)
                self.assertEqual(actual_chunk, expected_chunk)
                observed.extend(actual_chunk)
            os.write(master, frame(nonce, action))
            if action == "reboot":
                acknowledgement = read_line(master)
                expected = (
                    "ROG5_FALLBACK_REBOOT_ACK "
                    f"{nonce} 11111111-2222-4333-8444-555555555555\n"
                ).encode()
                self.assertEqual(acknowledgement, expected)
                os.write(
                    master,
                    (
                        "ROG5_FALLBACK_ACM_COMMIT "
                        f"{nonce} 11111111-2222-4333-8444-555555555555\r\n"
                    ).encode(),
                )
                self.assertTrue(commit_consumed.wait(timeout=5))
                os.close(master)

        def tracked_read(
            serial: MODULE.FallbackSerial,
            expected_line: str,
            timeout_seconds: float,
            remote_nonce: str | None = None,
        ) -> None:
            read_until(
                serial,
                expected_line,
                timeout_seconds,
                remote_nonce,
            )
            if expected_line.startswith("ROG5_FALLBACK_ACM_COMMIT"):
                commit_consumed.set()

        thread = threading.Thread(target=emulate)
        thread.start()
        try:
            with (
                mock.patch.object(
                    MODULE,
                    "wait_fallback_acm",
                    return_value=(
                        path,
                        "pci/usb1/1-1/1-1.2",
                        device_number,
                    ),
                ),
                mock.patch.object(
                    MODULE,
                    "revalidate_fallback_acm",
                ),
                mock.patch.object(MODULE.os, "urandom", return_value=b"3" * 16),
                mock.patch.object(MODULE, "verify_signature") as verify,
                mock.patch.object(
                    MODULE.FallbackSerial,
                    "read_until",
                    tracked_read,
                ),
            ):
                if duplicate_shell_ready:
                    with self.assertRaisesRegex(
                        MODULE.FallbackError,
                        "shell readiness marker is absent or ambiguous",
                    ):
                        MODULE.probe(
                            b"synthetic-allowed-signers\n",
                            action=action,
                        )
                    values = None
                else:
                    values, _, _ = MODULE.probe(
                        b"synthetic-allowed-signers\n",
                        action=action,
                    )
            if duplicate_shell_ready:
                verify.assert_not_called()
            else:
                verify.assert_called_once()
        finally:
            os.close(slave)
            if action != "reboot":
                os.close(master)
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        return values, bytes(observed)

    def test_preflight_is_one_bounded_nonce_framed_exchange(self) -> None:
        values, wire = self.run_probe("preflight")
        assert values is not None
        self.assertEqual(values["result"], "PASS")
        reset, sync_command, marker = MODULE.shell_sync_transport("3" * 32)
        launcher, chunks = MODULE.remote_transport("3" * 32, "preflight")
        self.assertEqual(
            wire,
            reset + sync_command + launcher + b"".join(chunks),
        )
        self.assertNotIn(marker.encode(), reset + sync_command)
        self.assertNotIn(b"ROG5_FALLBACK_ACM_BEGIN", wire)
        self.assertNotIn(b"ROG5_FALLBACK_LOADER_READY", launcher)
        self.assertLessEqual(
            len(launcher),
            MODULE.MAX_LAUNCHER_LINE_BYTES,
        )
        self.assertLess(
            MODULE.MAX_LAUNCHER_LINE_BYTES,
            MODULE.BUSYBOX_EDITING_MAX_LEN,
        )
        self.assertTrue(
            all(
                len(chunk) <= MODULE.SOURCE_CHUNK_BYTES + 1
                for chunk in chunks
            )
        )
        self.assertLessEqual(len(chunks), MODULE.MAX_SOURCE_CHUNKS)
        self.assertIn(b"/usr/bin/python3 -I -S -B -c", launcher)
        synthetic_source = (
            "import sys\n"
            "print('SYNTHETIC_LOADER_EXECUTED', *sys.argv[1:])\n"
        )
        with mock.patch.object(
            MODULE,
            "REMOTE_SOURCE",
            synthetic_source,
        ):
            synthetic_launcher, synthetic_chunks = MODULE.remote_transport(
                "4" * 32,
                "preflight",
            )
        arguments = shlex.split(synthetic_launcher.decode("ascii"))
        python_index = arguments.index("/usr/bin/python3")
        result = subprocess.run(
            [sys.executable, *arguments[python_index + 1 :]],
            input=b"".join(synthetic_chunks),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.decode("ascii").splitlines(),
            [
                f"ROG5_FALLBACK_LOADER_READY {'4' * 32}",
                f"SYNTHETIC_LOADER_EXECUTED {'4' * 32} preflight",
            ],
        )
        with (
            mock.patch.object(
                MODULE,
                "REMOTE_SOURCE",
                synthetic_source,
            ),
            mock.patch.object(
                MODULE,
                "LOADER_RECEIVE_TIMEOUT_SECONDS",
                1,
            ),
        ):
            stalled_launcher, stalled_chunks = MODULE.remote_transport(
                "5" * 32,
                "preflight",
            )
        stalled_arguments = shlex.split(stalled_launcher.decode("ascii"))
        stalled_python = stalled_arguments.index("/usr/bin/python3")
        for partial in (b"", stalled_chunks[0][:-1]):
            process = subprocess.Popen(
                [
                    sys.executable,
                    *stalled_arguments[stalled_python + 1 :],
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            ready = process.stdout.readline().decode("ascii").strip()
            self.assertEqual(
                ready,
                f"ROG5_FALLBACK_LOADER_READY {'5' * 32}",
            )
            if partial:
                process.stdin.write(partial)
                process.stdin.flush()
            self.assertNotEqual(process.wait(timeout=3), 0)
            process.stdin.close()
            self.assertNotIn(
                b"SYNTHETIC_LOADER_EXECUTED",
                process.stdout.read(),
            )
            process.stdout.close()
            process.stderr.close()

    def test_delayed_duplicate_shell_ready_fails_before_signature(self) -> None:
        values, _ = self.run_probe(
            "preflight",
            duplicate_shell_ready=True,
        )
        self.assertIsNone(values)

    def test_classify_is_read_only_and_returns_without_reboot_ack(self) -> None:
        values, _ = self.run_probe("classify")
        assert values is not None
        self.assertEqual(values["action"], "classify")

    def test_reboot_waits_for_verified_ack_then_disconnects(self) -> None:
        values, _ = self.run_probe("reboot")
        assert values is not None
        self.assertEqual(values["action"], "reboot")

    def test_exclusive_tty_refuses_a_second_controller(self) -> None:
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        device_number = os.stat(path).st_rdev
        try:
            with MODULE.FallbackSerial(path, "location", device_number):
                with self.assertRaises(OSError):
                    with MODULE.FallbackSerial(
                        path,
                        "location",
                        device_number,
                    ):
                        pass
        finally:
            os.close(master)
            os.close(slave)

    def test_opened_tty_must_match_discovered_device_number(self) -> None:
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        try:
            with self.assertRaises(MODULE.FallbackError):
                with MODULE.FallbackSerial(
                    path,
                    "location",
                    os.stat(path).st_rdev + 1,
                ):
                    pass
        finally:
            os.close(master)
            os.close(slave)

    def test_preexisting_tty_holder_is_rejected(self) -> None:
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        device_number = os.stat(path).st_rdev
        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import os,sys,time;"
                    "fd=os.open(sys.argv[1],os.O_RDWR|os.O_NOCTTY);"
                    "print('ready',flush=True);time.sleep(10)"
                ),
                path,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(holder.stdout.readline().strip(), "ready")
            with self.assertRaises(MODULE.FallbackError):
                with MODULE.FallbackSerial(
                    path,
                    "location",
                    device_number,
                ):
                    pass
        finally:
            holder.terminate()
            holder.wait(timeout=5)
            holder.stdout.close()
            holder.stderr.close()
            os.close(master)
            os.close(slave)

    def test_serial_output_bound_and_timeout_fail_closed(self) -> None:
        serial = MODULE.FallbackSerial("/unused", "location", 1)
        serial.fd = 17
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([17], [], []),
            ),
            mock.patch.object(
                MODULE.os,
                "read",
                return_value=b"x" * (MODULE.MAX_SERIAL_OUTPUT + 1),
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "output exceeds",
            ),
        ):
            serial.read_until("never", 1)
        nonce = "a" * 32
        serial.output = bytearray(
            f"ROG5_FALLBACK_ACM_ERROR {nonce} host-key-sign\r\n".encode()
        )
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "remote probe failed: host-key-sign",
            ),
        ):
            serial.read_until("never", 1, remote_nonce=nonce)
        serial.output.clear()
        final_error = (
            f"ROG5_FALLBACK_ACM_ERROR {nonce} health\r\n".encode()
        )
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0, 2.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([17], [], []),
            ),
            mock.patch.object(
                MODULE.os,
                "read",
                return_value=final_error,
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "remote probe failed: health",
            ),
        ):
            serial.read_until("never", 1, remote_nonce=nonce)
        serial.output.clear()
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0, 2.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([17], [], []),
            ),
            mock.patch.object(
                MODULE.os,
                "read",
                return_value=final_error,
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "remote probe failed: health",
            ),
        ):
            serial.wait_disconnect(1, remote_nonce=nonce)
        serial.output = bytearray(
            f"ROG5_FALLBACK_ACM_ERROR {nonce} post-ack-timeout\r\n".encode()
        )
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "remote probe failed: post-ack-timeout",
            ),
        ):
            serial.wait_disconnect(1, remote_nonce=nonce)
        serial.output = bytearray(
            f"ROG5_FALLBACK_ACM_ERROR {nonce} unknown\r\n".encode()
        )
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "malformed or ambiguous",
            ),
        ):
            serial.read_until("never", 1, remote_nonce=nonce)
        serial.output.clear()
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0, 2.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([], [], []),
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "result timed out",
            ),
        ):
            serial.read_until("never", 1)

    def test_serial_write_timeout_fails_closed(self) -> None:
        serial = MODULE.FallbackSerial("/unused", "location", 1)
        serial.fd = 17
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([], [], []),
            ),
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "payload write timed out after 0/1 bytes",
            ),
        ):
            serial.write(b"x", timeout_seconds=1)
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0, 0.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([], [17], []),
            ),
            mock.patch.object(
                MODULE.os,
                "write",
                side_effect=[
                    BlockingIOError(errno.EAGAIN, "retry"),
                    1,
                ],
            ) as write,
        ):
            serial.write(b"x", timeout_seconds=1)
        self.assertEqual(write.call_count, 2)

    def test_serial_write_drains_echo_backpressure(self) -> None:
        serial = MODULE.FallbackSerial("/unused", "location", 1)
        serial.fd = 17
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([17], [17], []),
            ) as selected,
            mock.patch.object(
                MODULE.os,
                "read",
                return_value=b"echoed launcher",
            ) as read,
            mock.patch.object(
                MODULE.os,
                "write",
                return_value=1,
            ) as write,
        ):
            serial.write(b"x", timeout_seconds=1)
        selected.assert_called_once_with([17], [17], [], 1.0)
        read.assert_called_once_with(17, 4096)
        write.assert_called_once()
        self.assertEqual(serial.output, b"echoed launcher")

    def test_serial_write_bounds_drained_echo(self) -> None:
        serial = MODULE.FallbackSerial("/unused", "location", 1)
        serial.fd = 17
        serial.output.extend(b"x" * MODULE.MAX_SERIAL_OUTPUT)
        with (
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0],
            ),
            mock.patch.object(
                MODULE.select,
                "select",
                return_value=([17], [17], []),
            ),
            mock.patch.object(
                MODULE.os,
                "read",
                return_value=b"x",
            ),
            mock.patch.object(MODULE.os, "write") as write,
            self.assertRaisesRegex(
                MODULE.FallbackError,
                "output exceeds its bound",
            ),
        ):
            serial.write(b"x", timeout_seconds=1)
        write.assert_not_called()

    def test_serial_write_stage_is_canonical(self) -> None:
        serial = MODULE.FallbackSerial("/unused", "location", 1)
        serial.fd = 17
        for stage in ("", "UPPER", "space value", "x" * 33):
            with (
                self.subTest(stage=stage),
                self.assertRaisesRegex(
                    MODULE.FallbackError,
                    "write stage is invalid",
                ),
            ):
                serial.write(b"x", stage=stage)


class PolicyTest(unittest.TestCase):
    def test_guards_fail_before_pin_or_device_access(self) -> None:
        environment = os.environ.copy()
        environment.pop("ALLOW_FALLBACK_ACM_CONTROL", None)
        environment.pop("ALLOW_PHONE_CREDENTIAL_USE", None)
        environment.pop("ALLOW_FALLBACK_ACM_STORAGE_WRITE", None)
        environment.pop("ALLOW_FALLBACK_BOOTLOADER_REBOOT", None)
        result = subprocess.run(
            [sys.executable, SOURCE, "reboot", "/absent/pin"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_FALLBACK_ACM_CONTROL", result.stderr)
        environment["ALLOW_FALLBACK_ACM_CONTROL"] = "1"
        result = subprocess.run(
            [sys.executable, SOURCE, "reboot", "/absent/pin"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_PHONE_CREDENTIAL_USE", result.stderr)
        self.assertNotIn("pin", result.stderr.lower())
        environment["ALLOW_PHONE_CREDENTIAL_USE"] = "1"
        result = subprocess.run(
            [sys.executable, SOURCE, "reboot", "/absent/pin"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_FALLBACK_ACM_STORAGE_WRITE", result.stderr)
        self.assertNotIn("pin", result.stderr.lower())
        environment["ALLOW_FALLBACK_ACM_STORAGE_WRITE"] = "1"
        result = subprocess.run(
            [sys.executable, SOURCE, "reboot", "/absent/pin"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_FALLBACK_BOOTLOADER_REBOOT", result.stderr)
        self.assertNotIn("pin", result.stderr.lower())
        with mock.patch.dict(
            MODULE.os.environ,
            {
                "ALLOW_FALLBACK_ACM_CONTROL": "1",
                "ALLOW_PHONE_CREDENTIAL_USE": "1",
            },
            clear=True,
        ):
            MODULE.require_guards("host-preflight")

    def test_remote_payload_is_fixed_read_only_except_restart2(self) -> None:
        source = MODULE.REMOTE_SOURCE
        compile(source, "fallback-remote.py", "exec")
        for required in (
            "ssh_host_ed25519_key",
            '"-Y"',
            '"sign"',
            "ROG5_FALLBACK_REBOOT_ACK",
            "REBOOT_ACK_TIMEOUT_SECONDS = 30",
            "POST_ACK_DEADLINE_SECONDS = 25",
            "ctypes.c_uint(0xFEE1DEAD)",
            "ctypes.c_uint(0xA1B2C3D4)",
            'ctypes.c_char_p(b"bootloader")',
            "range(3)",
            "pstore_checked",
            "dmesg_checked",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "fastboot boot",
            "fastboot flash",
            "authorized_keys",
            "open(\"/dev/",
            "sysrq-trigger",
            "mount(",
            "os.sync()",
            "os.open(",
            ".write_text(",
            ".write_bytes(",
        ):
            self.assertNotIn(forbidden, source)
        launcher, chunks = MODULE.remote_transport(
            "9" * 32,
            "preflight",
        )
        self.assertIn(b"/bin/busybox env -i", launcher)
        self.assertNotIn(b"exec /bin/busybox env -i", launcher)
        self.assertNotIn(b"HISTFILE=", launcher)
        self.assertIn(b"PYTHONDONTWRITEBYTECODE=1", launcher)
        self.assertIn(b"/usr/bin/python3 -I -S -B -c", launcher)
        self.assertNotIn(b" env python3 ", launcher)
        self.assertTrue(chunks)

    def test_frame_and_commit_waits_cover_remote_health_and_signing_bounds(
        self,
    ) -> None:
        tree = ast.parse(MODULE.REMOTE_SOURCE)
        timeouts: dict[str, int] = {}
        constants: dict[str, int] = {}
        thermal_sleep_total = 0.0
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)
            ):
                constants[node.targets[0].id] = node.value.value
            if not isinstance(node, ast.Call):
                continue
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
            ):
                command = next(
                    (
                        argument
                        for argument in node.args
                        if isinstance(argument, ast.List)
                    ),
                    None,
                )
                timeout = next(
                    (
                        keyword.value.value
                        for keyword in node.keywords
                        if keyword.arg == "timeout"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, int)
                    ),
                    None,
                )
                if command is not None and timeout is not None:
                    literals = {
                        item.value
                        for item in command.elts
                        if isinstance(item, ast.Constant)
                        and isinstance(item.value, str)
                    }
                    if "/bin/dmesg" in literals:
                        timeouts["dmesg"] = timeout
                    if "/usr/bin/ssh-keygen" in literals:
                        timeouts["ssh-keygen"] = timeout
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "sleep"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, (int, float))
            ):
                thermal_sleep_total += float(node.args[0].value)
        self.assertEqual(timeouts, {"dmesg": 10, "ssh-keygen": 10})
        self.assertEqual(thermal_sleep_total, 0.5)
        remote_bound = (
            timeouts["dmesg"]
            + 2 * thermal_sleep_total
            + timeouts["ssh-keygen"]
        )
        self.assertGreater(
            MODULE.REBOOT_COMMIT_TIMEOUT_SECONDS,
            remote_bound,
        )
        self.assertGreater(
            MODULE.PREPARED_FRAME_TIMEOUT_SECONDS,
            remote_bound,
        )
        self.assertGreater(
            constants["REBOOT_ACK_TIMEOUT_SECONDS"],
            timeouts["ssh-keygen"] + 5,
        )
        self.assertLess(
            constants["POST_ACK_DEADLINE_SECONDS"],
            MODULE.REBOOT_COMMIT_TIMEOUT_SECONDS,
        )

    def test_embedded_restart2_marshalling_preserves_unsigned_magics(
        self,
    ) -> None:
        tree = ast.parse(MODULE.REMOTE_SOURCE)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "restart_bootloader"
        )
        namespace = {"ctypes": ctypes}
        exec(
            compile(
                ast.Module(body=[function], type_ignores=[]),
                "embedded-restart2.py",
                "exec",
            ),
            namespace,
        )
        captured: list[object] = []

        def syscall(*arguments: object) -> int:
            captured.extend(arguments)
            return -1

        libc = mock.Mock()
        libc.syscall = syscall
        with (
            mock.patch.object(ctypes, "CDLL", return_value=libc),
            mock.patch.object(ctypes, "get_errno", return_value=22),
            self.assertRaisesRegex(
                RuntimeError,
                "reboot-returned--1-22",
            ),
        ):
            namespace["restart_bootloader"]()
        self.assertEqual(
            [argument.value for argument in captured[:4]],
            [142, 0xFEE1DEAD, 672274793, 0xA1B2C3D4],
        )
        self.assertEqual(captured[4].value, b"bootloader")

    def test_embedded_reboot_ack_wait_is_bounded(self) -> None:
        tree = ast.parse(MODULE.REMOTE_SOURCE)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "main"
        )
        nonce = "a" * 32
        values, payload = record(nonce, "reboot")
        restart = mock.Mock()

        def stop(_nonce: str, code: str) -> None:
            raise RuntimeError(code)

        namespace = {
            "sys": mock.Mock(argv=["probe", nonce, "reboot"]),
            "re": __import__("re"),
            "collect": mock.Mock(return_value=list(values.items())),
            "encode": mock.Mock(return_value=payload),
            "sign": mock.Mock(return_value=b"signature"),
            "base64": base64,
            "select": mock.Mock(),
            "print": mock.Mock(),
            "stop": stop,
            "restart_bootloader": restart,
            "REBOOT_ACK_TIMEOUT_SECONDS": 30,
            "POST_ACK_DEADLINE_SECONDS": 25,
            "time": mock.Mock(),
        }
        namespace["select"].select.return_value = ([], [], [])
        exec(
            compile(
                ast.Module(body=[function], type_ignores=[]),
                "embedded-ack-timeout.py",
                "exec",
            ),
            namespace,
        )
        with self.assertRaisesRegex(RuntimeError, "ack-timeout"):
            namespace["main"]()
        restart.assert_not_called()

        current = list(values.items())
        namespace["collect"].reset_mock()
        namespace["collect"].side_effect = [
            list(values.items()),
            current,
        ]
        namespace["select"].select.return_value = ([object()], [], [])
        namespace["sys"].stdin.readline.return_value = (
            f"ROG5_FALLBACK_REBOOT_ACK {nonce} {values['boot_id']}\n"
        )
        namespace["time"].monotonic.side_effect = [0.0, 30.0]
        with self.assertRaisesRegex(RuntimeError, "post-ack-timeout"):
            namespace["main"]()
        restart.assert_not_called()

        namespace["collect"].reset_mock()
        namespace["collect"].side_effect = [
            list(values.items()),
            current,
        ]
        namespace["time"].monotonic.side_effect = [0.0, 1.0, 30.0]
        with self.assertRaisesRegex(RuntimeError, "post-ack-timeout"):
            namespace["main"]()
        restart.assert_not_called()

    def test_modem_manager_requires_exact_inactive_status(self) -> None:
        cases = (
            (
                0,
                "LoadState=loaded\nActiveState=inactive\nSubState=dead\n",
                True,
            ),
            (
                0,
                "LoadState=loaded\nActiveState=failed\nSubState=failed\n",
                False,
            ),
            (
                0,
                "LoadState=not-found\nActiveState=inactive\nSubState=dead\n",
                True,
            ),
            (1, "", False),
        )
        for status, output, accepted in cases:
            result = subprocess.CompletedProcess([], status, output, "")
            with (
                self.subTest(status=status, output=output),
                mock.patch.object(
                    MODULE.subprocess,
                    "run",
                    return_value=result,
                ),
            ):
                if accepted:
                    MODULE.require_modem_manager_inactive()
                else:
                    with self.assertRaises(MODULE.FallbackError):
                        MODULE.require_modem_manager_inactive()

    def test_embedded_thermal_sampling_requires_all_exact_zones(self) -> None:
        tree = ast.parse(MODULE.REMOTE_SOURCE)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "temperatures"
        )
        readings = {
            f"/sys/class/thermal/thermal_zone{index}/temp": "40000"
            for index in range(MODULE.EXPECTED_THERMAL_ZONES)
        }

        class FakePath:
            def __init__(self, value: str):
                self.value = value

            def read_text(self) -> str:
                value = readings[self.value]
                if value == "error":
                    raise OSError("injected")
                return value

            def glob(self, _pattern: str) -> list["FakePath"]:
                return [FakePath(name) for name in readings]

            def __str__(self) -> str:
                return self.value

        namespace = {
            "EXPECTED_THERMAL_ZONES": MODULE.EXPECTED_THERMAL_ZONES,
            "Path": FakePath,
            "time": mock.Mock(),
        }
        exec(
            compile(
                ast.Module(body=[function], type_ignores=[]),
                "embedded-thermals.py",
                "exec",
            ),
            namespace,
        )
        self.assertEqual(
            namespace["temperatures"](),
            (3, MODULE.EXPECTED_THERMAL_ZONES, 40000),
        )
        readings["/sys/class/thermal/thermal_zone69/temp"] = "90000"
        self.assertEqual(
            namespace["temperatures"](),
            (3, MODULE.EXPECTED_THERMAL_ZONES, 90000),
        )
        readings["/sys/class/thermal/thermal_zone70/temp"] = "190000"
        self.assertEqual(namespace["temperatures"](), (0, 0, 0))
        del readings["/sys/class/thermal/thermal_zone70/temp"]
        readings["/sys/class/thermal/thermal_zone69/temp"] = "error"
        self.assertEqual(namespace["temperatures"](), (0, 0, 0))

    def test_embedded_pstore_inspection_never_hides_entry_errors(self) -> None:
        tree = ast.parse(MODULE.REMOTE_SOURCE)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "pstore_count"
        )

        class BrokenEntry:
            def is_file(self) -> bool:
                raise OSError("injected")

        class FakeRoot:
            def __init__(self, value: str):
                self.value = value

            def is_dir(self) -> bool:
                return self.value == "/sys/fs/pstore"

            def iterdir(self) -> list[BrokenEntry]:
                return [BrokenEntry()]

        namespace = {"Path": FakeRoot}
        exec(
            compile(
                ast.Module(body=[function], type_ignores=[]),
                "embedded-pstore.py",
                "exec",
            ),
            namespace,
        )
        self.assertEqual(namespace["pstore_count"](), (0, 0))

    def test_reboot_requires_empty_initial_fastboot_inventory(self) -> None:
        cases = (
            (0, "", True),
            (0, "device\tfastboot\n", False),
            (0, "malformed\n", False),
            (1, "", False),
        )
        for status, output, accepted in cases:
            result = subprocess.CompletedProcess([], status, output, "")
            with (
                self.subTest(status=status, output=output),
                mock.patch.object(MODULE, "fixed_binary"),
                mock.patch.object(
                    MODULE.subprocess,
                    "run",
                    return_value=result,
                ),
            ):
                if accepted:
                    MODULE.require_fastboot_absent()
                else:
                    with self.assertRaises(MODULE.FallbackError):
                        MODULE.require_fastboot_absent()

    def test_anchor_time_is_canonical_and_bounded(self) -> None:
        producer_path = SOURCE.with_name(
            "pin-minimal-headless-host-key.py"
        )
        producer_spec = importlib.util.spec_from_file_location(
            "pin_minimal_headless_host_key_contract",
            producer_path,
        )
        assert producer_spec is not None and producer_spec.loader is not None
        producer = importlib.util.module_from_spec(producer_spec)
        producer_spec.loader.exec_module(producer)
        self.assertEqual(tuple(producer.ANCHOR_KEYS), MODULE.ANCHOR_FIELDS)
        self.assertEqual(
            producer.FORMAT,
            "rog5-minimal-headless-usb-anchor-v1",
        )
        self.assertEqual(
            producer.RECOVERY_PRODUCT,
            MODULE.RECOVERY_PRODUCT_NAME,
        )
        with tempfile.TemporaryDirectory(
            prefix="rog5-fallback-anchor-"
        ) as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            anchor = root / "anchor"
            now = 2000000000

            def write(created: str) -> None:
                anchor.write_text(
                    "\n".join(
                        (
                            "format=rog5-minimal-headless-usb-anchor-v1",
                            (
                                "host_boot_id="
                                "11111111-2222-4333-8444-555555555555"
                            ),
                            f"created_unix={created}",
                            "usb_location=pci/usb1/1-1/1-1.2",
                            f"recovery_vendor={MODULE.USB_VENDOR}",
                            f"recovery_product_id={MODULE.USB_PRODUCT}",
                            (
                                "recovery_product="
                                f"{MODULE.RECOVERY_PRODUCT_NAME}"
                            ),
                            "",
                        )
                    ),
                    encoding="ascii",
                )
                anchor.chmod(0o600)

            with (
                mock.patch.object(
                    MODULE,
                    "host_boot_id",
                    return_value=(
                        "11111111-2222-4333-8444-555555555555"
                    ),
                ),
                mock.patch.object(MODULE.time, "time", return_value=now),
            ):
                write(str(now))
                self.assertEqual(
                    MODULE.read_anchor(anchor),
                    "pci/usb1/1-1/1-1.2",
                )
                for created in (
                    "0",
                    str(now + 6),
                    str(now - MODULE.ANCHOR_MAX_AGE_SECONDS - 1),
                ):
                    write(created)
                    with self.subTest(created=created):
                        with self.assertRaises(MODULE.FallbackError):
                            MODULE.read_anchor(anchor)
            write(str(now))
            with (
                mock.patch.object(
                    MODULE,
                    "host_boot_id",
                    return_value=(
                        "11111111-2222-4333-8444-555555555555"
                    ),
                ),
                mock.patch.object(
                    MODULE.time,
                    "time",
                    side_effect=[
                        now,
                        now + MODULE.ANCHOR_MAX_AGE_SECONDS + 1,
                    ],
                ),
            ):
                self.assertEqual(
                    MODULE.read_anchor(anchor),
                    "pci/usb1/1-1/1-1.2",
                )
                with self.assertRaises(MODULE.FallbackError):
                    MODULE.read_anchor(anchor)
            with (
                mock.patch.object(
                    MODULE,
                    "wait_fallback_acm",
                    return_value=(
                        "/dev/ttyACM0",
                        "pci/usb1/1-1/1-1.2",
                        1,
                    ),
                ),
                mock.patch.object(
                    MODULE,
                    "read_anchor",
                    side_effect=MODULE.FallbackError("stale anchor"),
                ),
                mock.patch.object(MODULE, "FallbackSerial") as serial,
                self.assertRaisesRegex(MODULE.FallbackError, "stale anchor"),
            ):
                MODULE.probe(
                    b"pin\n",
                    action="classify",
                    expected_location="pci/usb1/1-1/1-1.2",
                    anchor_path=anchor,
                )
            serial.assert_not_called()

    def test_identity_evidence_retains_signed_proof_metadata(self) -> None:
        nonce = "7" * 32
        values, _ = record(nonce, "classify")
        proof = OrderedDict(
            (
                ("nonce", nonce),
                ("usb_location", "pci/usb1/1-1/1-1.2"),
                ("thermal_max", "61400"),
                ("record_sha256", "8" * 64),
                ("signature_sha256", "9" * 64),
                ("host_pin_sha256", "a" * 64),
            )
        )
        with tempfile.TemporaryDirectory(
            prefix="rog5-fallback-identity-"
        ) as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            output = root / "identity"
            MODULE.write_identity(output, values, proof)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertEqual(
                output.read_text(encoding="ascii").splitlines(),
                [
                    f"format={MODULE.IDENTITY_FORMAT}",
                    f"kernel_release={MODULE.FALLBACK_KERNEL}",
                    (
                        "boot_id="
                        "11111111-2222-4333-8444-555555555555"
                    ),
                    "usb_location=pci/usb1/1-1/1-1.2",
                    f"nonce={nonce}",
                    "thermal_max=61400",
                    f"record_sha256={'8' * 64}",
                    f"signature_sha256={'9' * 64}",
                    f"host_pin_sha256={'a' * 64}",
                    "result=PASS",
                ],
            )
            preflight_output = root / "preflight.record"
            with (
                mock.patch.object(MODULE, "require_guards"),
                mock.patch.object(MODULE, "fixed_binary"),
                mock.patch.object(MODULE, "require_modem_manager_inactive"),
                mock.patch.object(
                    MODULE,
                    "verify_known_hosts",
                    return_value=b"pin\n",
                ),
                mock.patch.object(
                    MODULE,
                    "probe",
                    return_value=(values, "location", proof),
                ),
            ):
                self.assertEqual(
                    MODULE.main(
                        [
                            "preflight",
                            str(root / "known-hosts"),
                            str(preflight_output),
                        ]
                    ),
                    0,
                )
            self.assertEqual(
                preflight_output.read_bytes(),
                output.read_bytes(),
            )
            with (
                mock.patch.object(MODULE, "require_guards"),
                mock.patch.object(MODULE, "fixed_binary"),
                mock.patch.object(MODULE, "require_modem_manager_inactive"),
                mock.patch.object(
                    MODULE,
                    "verify_known_hosts",
                    return_value=b"pin\n",
                ),
                mock.patch.object(
                    MODULE,
                    "remote_transport",
                    return_value=(b"launcher", (b"chunk",)),
                ) as transport,
            ):
                self.assertEqual(
                    MODULE.main(
                        [
                            "host-preflight",
                            str(root / "known-hosts"),
                            "750",
                            "3600",
                        ]
                    ),
                    0,
                )
            transport.assert_called_once_with("1" * 32, "classify")

    def test_fastboot_must_return_on_same_port_with_exact_product(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="rog5-fallback-fastboot-"
        ) as temporary:
            root = Path(temporary)
            location = "pci/usb1/1-1/1-1.2"
            raw = root / location
            raw.mkdir(parents=True)
            (raw / "serial").write_text("test-device")
            (raw / "idVendor").write_text(MODULE.FASTBOOT_VENDOR)
            (raw / "idProduct").write_text(MODULE.FASTBOOT_PRODUCT)
            (raw / "product").write_text("Android Bootloader Interface")
            bus = root / "bus"
            bus.mkdir()
            (bus / "1-1.2").symlink_to(raw)
            devices = subprocess.CompletedProcess(
                [], 0, "test-device\tfastboot\n", ""
            )
            product = subprocess.CompletedProcess(
                [], 0, "product: lahaina\n", ""
            )
            with (
                mock.patch.object(MODULE, "SYS_DEVICES", root),
                mock.patch.object(MODULE, "SYS_BUS_USB", bus),
                mock.patch.object(MODULE, "fixed_binary"),
                mock.patch.object(
                    MODULE.subprocess,
                    "run",
                    side_effect=[devices, product],
                ),
            ):
                MODULE.wait_fastboot(location, timeout_seconds=1)

    def test_fastboot_rejects_wrong_port_product_state_and_inventory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="rog5-fallback-fastboot-negative-"
        ) as temporary:
            root = Path(temporary)
            location = "pci/usb1/1-1/1-1.2"
            raw = root / location
            raw.mkdir(parents=True)
            (raw / "serial").write_text("test-device")
            (raw / "idVendor").write_text(MODULE.FASTBOOT_VENDOR)
            (raw / "idProduct").write_text(MODULE.FASTBOOT_PRODUCT)
            (raw / "product").write_text("Android Bootloader Interface")
            bus = root / "bus"
            bus.mkdir()
            (bus / "1-1.2").symlink_to(raw)
            cases = (
                (
                    "other-device\tfastboot\n",
                    (),
                ),
                (
                    "test-device\tbootloader\n",
                    (),
                ),
                (
                    "test-device\tfastboot\n",
                    ("product: taro\n",),
                ),
                (
                    "test-device\tfastboot\nother\tfastboot\n",
                    (),
                ),
                (
                    "test-device fastboot trailing\n",
                    (),
                ),
            )
            for inventory, products in cases:
                side_effect = [
                    subprocess.CompletedProcess([], 0, inventory, ""),
                    *(
                        subprocess.CompletedProcess([], 0, product, "")
                        for product in products
                    ),
                ]
                with (
                    self.subTest(inventory=inventory, products=products),
                    mock.patch.object(MODULE, "SYS_DEVICES", root),
                    mock.patch.object(MODULE, "SYS_BUS_USB", bus),
                    mock.patch.object(MODULE, "fixed_binary"),
                    mock.patch.object(
                        MODULE.subprocess,
                        "run",
                        side_effect=side_effect,
                    ),
                    self.assertRaises(MODULE.FallbackError),
                ):
                    MODULE.wait_fastboot(location, timeout_seconds=1)
            duplicate = root / "pci/usb1/1-1/1-1.3"
            duplicate.mkdir(parents=True)
            for name in ("idVendor", "idProduct", "product", "serial"):
                (duplicate / name).write_bytes((raw / name).read_bytes())
            (bus / "1-1.3").symlink_to(duplicate)
            devices = subprocess.CompletedProcess(
                [], 0, "test-device\tfastboot\n", ""
            )
            with (
                mock.patch.object(MODULE, "SYS_DEVICES", root),
                mock.patch.object(MODULE, "SYS_BUS_USB", bus),
                mock.patch.object(MODULE, "fixed_binary"),
                mock.patch.object(
                    MODULE.subprocess,
                    "run",
                    return_value=devices,
                ),
                self.assertRaises(MODULE.FallbackError),
            ):
                MODULE.wait_fastboot(location, timeout_seconds=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
