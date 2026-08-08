#!/usr/bin/env python3
"""Hostile tests for the receive-only early-target diagnostic collector."""

from __future__ import annotations

from collections import OrderedDict
import errno
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import pty
import stat
import sys
import tempfile
import termios
import threading
import time
import unittest
from unittest import mock


SOURCE = Path(__file__).with_name("collect-early-target-diagnostics.py")
if not SOURCE.is_file():
    raise SystemExit(f"FAIL missing early-target collector: {SOURCE}")
SPEC = importlib.util.spec_from_file_location(
    "collect_early_target_diagnostics", SOURCE
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PARSER_SOURCE = Path(__file__).with_name("early-target-diagnostics.py")
PARSER_SPEC = importlib.util.spec_from_file_location(
    "early_target_diagnostics_test_oracle", PARSER_SOURCE
)
assert PARSER_SPEC is not None and PARSER_SPEC.loader is not None
PARSER = importlib.util.module_from_spec(PARSER_SPEC)
sys.modules[PARSER_SPEC.name] = PARSER
PARSER_SPEC.loader.exec_module(PARSER)

CANDIDATE = "headless-netroot-early-diag-v2"
BOOT = "12345678-1234-4abc-8def-1234567890ab"
HOST_BOOT = "87654321-4321-4abc-8def-1234567890ab"
LOCATION = "pci0000:00/0000:00:08.1/usb3/3-2"


def diagnostic_record(sequence: int, stage: int):
    return PARSER.DiagnosticRecord(
        candidate=CANDIDATE,
        boot_id=BOOT,
        sequence=sequence,
        boottime_ms=sequence * 250,
        stage_code=stage,
        stage=PARSER.STAGES[stage],
        last_good_code=stage,
        fault="none",
        watchdog_deadline_ms=600_000,
        dropped_updates=0,
    )


def anchor_payload(location: str = LOCATION) -> bytes:
    return (
        "format=rog5-minimal-headless-usb-anchor-v1\n"
        f"host_boot_id={HOST_BOOT}\n"
        "created_unix=2000000000\n"
        f"usb_location={location}\n"
        "recovery_vendor=1d6b\n"
        "recovery_product_id=0104\n"
        "recovery_product=ROG5 recovery\n"
    ).encode("ascii")


def transport_snapshot() -> MODULE.TransportSnapshot:
    return MODULE.TransportSnapshot(
        host_unix_ns=100,
        host_monotonic_ns=10,
        state="present",
        interface="usb7",
        usb_location=LOCATION,
        carrier=1,
        operstate="up",
        rx_bytes=100,
        rx_packets=2,
        rx_errors=0,
        rx_dropped=0,
        tx_bytes=200,
        tx_packets=3,
        tx_errors=0,
        tx_dropped=0,
        nfs_rpc_calls=1,
        nfs_rpc_badcalls=0,
        nfs_rpc_badauth=0,
        nfs_rpc_badclnt=0,
        nfs_rpc_xdrcall=0,
        nfs_tcp_listener=1,
        nfs_tcp_accept_backlog=0,
        nfs_tcp_connections=1,
        nfs_tcp_states="established",
        nfs_tcp_tx_queue=16,
        nfs_tcp_rx_queue=32,
        nfs_tcp_unrecovered_retransmits=0,
    )


class CollectorPolicyTest(unittest.TestCase):
    def private_directory(self, root: Path) -> Path:
        directory = root / "private"
        directory.mkdir(mode=0o700)
        os.chmod(directory, 0o700)
        return directory

    def write_anchor(self, directory: Path, payload: bytes) -> Path:
        path = directory / "anchor"
        path.write_bytes(payload)
        os.chmod(path, 0o600)
        return path

    def test_anchor_is_canonical_private_fresh_and_host_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self.private_directory(Path(temporary))
            anchor = self.write_anchor(directory, anchor_payload())
            with (
                mock.patch.object(MODULE, "host_boot_id", return_value=HOST_BOOT),
                mock.patch.object(MODULE.time, "time", return_value=2_000_000_001),
            ):
                values = MODULE.read_anchor(anchor)
            self.assertEqual(values["usb_location"], LOCATION)

            mutations = (
                anchor_payload().replace(b"created_unix=", b"created_unix=0"),
                anchor_payload().replace(HOST_BOOT.encode(), BOOT.encode()),
                anchor_payload().replace(b"ROG5 recovery", b"other product"),
                anchor_payload().replace(b"usb3/3-2", b"../3-2"),
                anchor_payload() + b"extra=1\n",
            )
            for index, payload in enumerate(mutations):
                mutated = self.write_anchor(
                    directory, payload
                ) if index == 0 else directory / f"anchor-{index}"
                if index != 0:
                    mutated.write_bytes(payload)
                    os.chmod(mutated, 0o600)
                with self.subTest(index=index), self.assertRaises(MODULE.CollectorError), (
                    mock.patch.object(MODULE, "host_boot_id", return_value=HOST_BOOT)
                ), mock.patch.object(MODULE.time, "time", return_value=2_000_000_001):
                    MODULE.read_anchor(mutated)

    def test_output_must_be_new_outside_repo_in_private_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self.private_directory(Path(temporary))
            output = directory / "evidence.json"
            self.assertEqual(MODULE.safe_new_output(output), output)
            output.write_text("occupied", encoding="ascii")
            with self.assertRaises(MODULE.CollectorError):
                MODULE.safe_new_output(output)
            os.chmod(directory, 0o755)
            with self.assertRaises(MODULE.CollectorError):
                MODULE.safe_new_output(directory / "other.json")
        with self.assertRaises(MODULE.CollectorError):
            MODULE.safe_new_output(MODULE.REPO / "forbidden-evidence.json")

    def test_exact_product_and_acm_identity_are_unique_and_port_bound(self):
        identity = MODULE.AcmIdentity(
            path="/dev/ttyACM7",
            location=LOCATION,
            device_number=123,
        )
        with (
            mock.patch.object(MODULE, "diagnostic_product_locations", return_value={LOCATION}),
            mock.patch.object(MODULE, "diagnostic_acm_identities", return_value=[identity]),
        ):
            self.assertEqual(MODULE.find_diagnostic_acm(LOCATION), identity)
        hostile = (
            (set(), [identity]),
            ({LOCATION, "pci/usb4/4-1"}, [identity]),
            ({LOCATION}, []),
            ({LOCATION}, [identity, identity]),
            ({"pci/usb4/4-1"}, [identity]),
        )
        for products, acms in hostile:
            with self.subTest(products=products, acms=acms), (
                mock.patch.object(MODULE, "diagnostic_product_locations", return_value=products)
            ), mock.patch.object(MODULE, "diagnostic_acm_identities", return_value=acms), self.assertRaises(MODULE.CollectorError):
                MODULE.find_diagnostic_acm(LOCATION)

    def test_revalidation_rejects_device_or_port_replacement(self):
        identity = MODULE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        with mock.patch.object(MODULE, "find_diagnostic_acm", return_value=identity):
            MODULE.revalidate_diagnostic_acm(identity)
        replacement = MODULE.AcmIdentity("/dev/ttyACM7", LOCATION, 124)
        with mock.patch.object(MODULE, "find_diagnostic_acm", return_value=replacement), self.assertRaises(MODULE.CollectorError):
            MODULE.revalidate_diagnostic_acm(identity)

    def test_usb_interface_identity_pins_number_and_driver(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "3-2"
            interface = raw / "3-2:1.2"
            tty_root = interface / "tty" / "ttyACM7"
            driver = root / "drivers" / "cdc_acm"
            tty_root.mkdir(parents=True)
            driver.mkdir(parents=True)
            (interface / "bInterfaceNumber").write_text("02\n", encoding="ascii")
            (interface / "driver").symlink_to(driver, target_is_directory=True)
            self.assertEqual(
                MODULE.usb_interface_identity(tty_root, raw),
                ("02", "cdc_acm"),
            )


class TransportObserverTest(unittest.TestCase):
    def test_nfs_rpc_parser_is_bounded_and_canonical(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nfsd"
            path.write_text(
                "net 12 0 12 4\nrpc 10 1 2 3 4\nproc4 2 0 10\n",
                encoding="ascii",
            )
            with mock.patch.object(MODULE, "NFSD_STATS", path):
                self.assertEqual(MODULE.nfs_rpc_state(), (10, 1, 2, 3, 4))
            for payload in (
                "rpc 10 1 2 3\n",
                "rpc 10 1 2 3 4\nrpc 11 0 0 0 0\n",
                "rpc 01 0 0 0 0\n",
                "rpc x 0 0 0 0\n",
            ):
                path.write_text(payload, encoding="ascii")
                with (
                    self.subTest(payload=payload),
                    mock.patch.object(MODULE, "NFSD_STATS", path),
                    self.assertRaises(MODULE.CollectorError),
                ):
                    MODULE.nfs_rpc_state()
            path.unlink()
            with mock.patch.object(MODULE, "NFSD_STATS", path):
                self.assertIsNone(MODULE.nfs_rpc_state())

    def test_nfs_tcp_parser_is_exact_bounded_and_target_specific(self):
        header = (
            "sl local_address rem_address st tx_queue rx_queue tr "
            "tm->when retrnsmt uid timeout inode\n"
        )
        listener = (
            "0: 014DFEA9:0801 00000000:0000 0A "
            "00000000:00000005 00:00000000 00000000 0 0 1\n"
        )
        established = (
            "1: 014DFEA9:0801 024DFEA9:C001 01 "
            "00000010:00000020 00:00000000 00000003 0 0 2\n"
        )
        time_wait = (
            "2: 014DFEA9:0801 024DFEA9:C002 06 "
            "00000001:00000002 00:00000000 00000000 0 0 0\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            table = Path(temporary) / "tcp"
            table.write_text(
                header + listener + established + time_wait,
                encoding="ascii",
            )
            with mock.patch.object(MODULE, "TCP_STATS", table):
                self.assertEqual(
                    MODULE.nfs_tcp_state(),
                    MODULE.NfsTcpState(
                        listener=1,
                        accept_backlog=5,
                        connections=2,
                        states="established,time-wait",
                        tx_queue=17,
                        rx_queue=34,
                        unrecovered_retransmits=3,
                    ),
                )

            table.write_text(
                header
                + listener
                + listener.replace("0:", "9:", 1)
                + established
                + established.replace("1:", "8:", 1)
                + time_wait,
                encoding="ascii",
            )
            with mock.patch.object(MODULE, "TCP_STATS", table):
                self.assertEqual(
                    MODULE.nfs_tcp_state(),
                    MODULE.NfsTcpState(
                        listener=1,
                        accept_backlog=5,
                        connections=2,
                        states="established,time-wait",
                        tx_queue=17,
                        rx_queue=34,
                        unrecovered_retransmits=3,
                    ),
                )

            hostile = (
                header.replace("local_address", "local"),
                header
                + listener.replace("014DFEA9:0801", "00000000:0801"),
                header
                + established.replace("024DFEA9:C001", "034DFEA9:C001"),
                header
                + established.replace(
                    "00000010:00000020", "00000010:xyz"
                ),
                header
                + listener
                + listener.replace("0:", "1:", 1).replace(
                    " 0 0 1\n", " 0 0 3\n"
                ),
                header
                + established
                + established.replace("00000003 0 0 2", "00000004 0 0 2"),
                header
                + time_wait.replace(
                    "00:00000000 00000000 0 0 0",
                    "00:00000000 00000001 0 0 0",
                ),
                header + established.replace(" 01 ", " FF "),
            )
            for index, payload in enumerate(hostile):
                table.write_text(payload, encoding="ascii")
                with (
                    self.subTest(index=index),
                    mock.patch.object(MODULE, "TCP_STATS", table),
                    self.assertRaises(MODULE.CollectorError),
                ):
                    MODULE.nfs_tcp_state()
            table.write_text(
                header + established + time_wait,
                encoding="ascii",
            )
            with (
                mock.patch.object(MODULE, "TCP_STATS", table),
                mock.patch.object(MODULE, "MAX_NFS_TCP_CONNECTIONS", 1),
                self.assertRaises(MODULE.CollectorError),
            ):
                MODULE.nfs_tcp_state()

    def test_observer_records_only_changes_and_departure(self):
        clock = mock.Mock()
        clock.monotonic.side_effect = [0.0, 1.0, 2.0, 3.0]
        clock.time_ns.side_effect = [100, 200, 300]
        clock.monotonic_ns.side_effect = [10, 20, 30]
        identity = MODULE.NcmIdentity("usb7", LOCATION)
        first = (1, "up", (100, 2, 0, 0, 200, 3, 0, 0))
        changed = (1, "up", (140, 3, 0, 0, 260, 4, 0, 0))
        tcp = MODULE.NfsTcpState(1, 0, 1, "established", 0, 0, 0)
        with (
            mock.patch.object(
                MODULE,
                "diagnostic_ncm_identities",
                side_effect=[[identity], [identity], [identity], []],
            ),
            mock.patch.object(
                MODULE, "ncm_state", side_effect=[first, first, changed]
            ),
            mock.patch.object(
                MODULE,
                "nfs_rpc_state",
                side_effect=[
                    (0, 0, 0, 0, 0),
                    (0, 0, 0, 0, 0),
                    (2, 0, 0, 0, 0),
                    (2, 0, 0, 0, 0),
                ],
            ),
            mock.patch.object(MODULE, "nfs_tcp_state", return_value=tcp),
        ):
            observer = MODULE.TransportObserver(LOCATION, clock=clock)
            for _ in range(4):
                observer.poll(force=True)
        self.assertEqual(len(observer.snapshots), 3)
        self.assertEqual(
            [item.state for item in observer.snapshots],
            ["present", "present", "absent"],
        )
        self.assertEqual(observer.snapshots[1].nfs_rpc_calls, 2)
        self.assertIsNone(observer.snapshots[-1].rx_bytes)
        self.assertEqual(observer.dropped, 0)

    def test_observer_rejects_wrong_port_and_bounds_changes(self):
        wrong = MODULE.NcmIdentity("usb7", "pci/usb4/4-1")
        observer = MODULE.TransportObserver(LOCATION, clock=mock.Mock(monotonic=lambda: 0.0))
        with (
            mock.patch.object(MODULE, "diagnostic_ncm_identities", return_value=[wrong]),
            self.assertRaises(MODULE.CollectorError),
        ):
            observer.poll(force=True)

        clock = mock.Mock()
        clock.monotonic.side_effect = [0.0, 1.0]
        clock.time_ns.return_value = 1
        clock.monotonic_ns.return_value = 1
        with (
            mock.patch.object(MODULE, "MAX_TRANSPORT_SNAPSHOTS", 1),
            mock.patch.object(MODULE, "diagnostic_ncm_identities", side_effect=[[], []]),
            mock.patch.object(
                MODULE,
                "nfs_rpc_state",
                side_effect=[(0, 0, 0, 0, 0), (1, 0, 0, 0, 0)],
            ),
            mock.patch.object(
                MODULE,
                "nfs_tcp_state",
                return_value=MODULE.NfsTcpState(
                    0, 0, 0, "absent", 0, 0, 0
                ),
            ),
        ):
            observer = MODULE.TransportObserver(LOCATION, clock=clock)
            observer.poll(force=True)
            observer.poll(force=True)
        self.assertEqual(len(observer.snapshots), 1)
        self.assertEqual(observer.dropped, 1)


class ReceiveOnlySerialTest(unittest.TestCase):
    def test_serial_open_and_setup_races_become_collector_errors(self):
        identity = MODULE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        with (
            mock.patch.object(MODULE.os, "open", side_effect=FileNotFoundError()),
            self.assertRaises(MODULE.CollectorError),
        ):
            MODULE.ReceiveOnlySerial(identity).__enter__()

        master, slave = pty.openpty()
        path = os.ttyname(slave)
        identity = MODULE.AcmIdentity(path, LOCATION, os.fstat(slave).st_rdev)
        os.close(slave)
        try:
            with (
                mock.patch.object(MODULE.fcntl, "flock", side_effect=OSError()),
                self.assertRaises(MODULE.CollectorError),
            ):
                MODULE.ReceiveOnlySerial(identity).__enter__()
        finally:
            os.close(master)

    def test_serial_descriptor_is_read_only_raw_exclusive_and_no_hupcl(self):
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        device_number = os.fstat(slave).st_rdev
        os.close(slave)
        try:
            identity = MODULE.AcmIdentity(path, LOCATION, device_number)
            with MODULE.ReceiveOnlySerial(identity) as serial:
                flags = fcntl.fcntl(serial.fileno(), fcntl.F_GETFL)
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
                attributes = termios.tcgetattr(serial.fileno())
                self.assertFalse(attributes[2] & termios.HUPCL)
                self.assertFalse(attributes[3] & termios.ECHO)
                with self.assertRaises(OSError) as failure:
                    os.write(serial.fileno(), b"forbidden")
                self.assertEqual(failure.exception.errno, errno.EBADF)

                os.write(master, b"target-only")
                self.assertEqual(serial.read(1.0), b"target-only")
        finally:
            os.close(master)

    def test_disconnect_is_distinct_from_timeout(self):
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        identity = MODULE.AcmIdentity(path, LOCATION, os.fstat(slave).st_rdev)
        os.close(slave)
        serial = MODULE.ReceiveOnlySerial(identity)
        serial.__enter__()
        try:
            self.assertIsNone(serial.read(0.01))
            os.close(master)
            master = -1
            self.assertEqual(serial.read(1.0), b"")
        finally:
            serial.__exit__(None, None, None)
            if master >= 0:
                os.close(master)


class EvidenceAndCaptureTest(unittest.TestCase):
    def test_capture_timestamps_only_validated_frames(self):
        stream = b"".join(
            PARSER.frame_for(diagnostic_record(index, stage))
            for index, stage in ((1, 10), (2, 20), (3, 30))
        )
        reader = mock.Mock()
        reader.read.side_effect = [stream[:7], stream[7:], b""]
        clock = mock.Mock()
        clock.time_ns.side_effect = [100, 200, 300, 400, 500]
        clock.monotonic_ns.side_effect = [10, 20, 30, 40, 50]
        clock.monotonic.return_value = 0.0
        result = MODULE.capture_stream(
            reader,
            CANDIDATE,
            deadline_monotonic=100.0,
            clock=clock,
            revalidate=lambda: None,
            poll_events=lambda: [],
        )
        self.assertEqual(result.end_reason, "disconnected")
        self.assertEqual([frame.record.stage_code for frame in result.frames], [10, 20, 30])
        self.assertEqual([frame.host_unix_ns for frame in result.frames], [100, 200, 300])

    def test_capture_rejects_malformed_or_truncated_stream_without_raw_bytes(self):
        for chunks in ([b"01:x,"], [PARSER.frame_for(diagnostic_record(1, 10))[:-1], b""]):
            reader = mock.Mock()
            reader.read.side_effect = chunks
            clock = mock.Mock()
            clock.time_ns.return_value = 1
            clock.monotonic_ns.return_value = 1
            clock.monotonic.return_value = 0.0
            with self.subTest(chunks=chunks), self.assertRaises(MODULE.CollectorError) as failure:
                MODULE.capture_stream(
                    reader,
                    CANDIDATE,
                    deadline_monotonic=100.0,
                    clock=clock,
                    revalidate=lambda: None,
                    poll_events=lambda: [],
                )
            self.assertNotIn("01:x", str(failure.exception))

    def test_valid_prefix_survives_coalesced_and_split_invalid_frame(self):
        valid = PARSER.frame_for(diagnostic_record(1, 10))
        for chunks in ([valid + b"01:x,"], [valid, b"01:x,"]):
            reader = mock.Mock()
            reader.read.side_effect = chunks
            clock = mock.Mock()
            clock.time_ns.return_value = 1
            clock.monotonic_ns.return_value = 1
            clock.monotonic.return_value = 0.0
            with self.subTest(chunks=len(chunks)), self.assertRaises(MODULE.CaptureRejected) as failure:
                MODULE.capture_stream(
                    reader,
                    CANDIDATE,
                    deadline_monotonic=100.0,
                    clock=clock,
                    revalidate=lambda: None,
                    poll_events=lambda: [],
                )
            self.assertEqual(
                [frame.record.stage_code for frame in failure.exception.partial.frames],
                [10],
            )

    def test_kernel_event_filter_is_bounded_and_redacts_serial_lines(self):
        monitor = MODULE.KernelEventFilter("3-2")
        lines = [
            b"usb 3-2: new SuperSpeed USB device number 9",
            b"cdc_acm 3-2:1.2: ttyACM0: USB ACM device",
            b"usb 4-1: unrelated",
            b"usb 3-2: SerialNumber: private",
        ]
        events = []
        for line in lines:
            events.extend(monitor.accept(line, 123))
        self.assertEqual(len(events), 2)
        self.assertTrue(all(len(event.message) <= MODULE.MAX_EVENT_BYTES for event in events))
        for index in range(MODULE.MAX_USB_EVENTS + 2):
            monitor.accept(f"usb 3-2: event {index}".encode(), index)
        self.assertEqual(len(monitor.events), MODULE.MAX_USB_EVENTS)
        self.assertGreater(monitor.dropped, 0)

    def test_journal_bounds_one_unterminated_line_not_aggregate_bursts(self):
        journal = MODULE.KernelJournal(LOCATION)
        journal.consume(b"x" * 7000)
        burst = b"\n" + (b"usb 3-2: bounded event\n" * 100)
        journal.consume(burst)
        self.assertLessEqual(len(journal.buffer), MODULE.MAX_JOURNAL_BUFFER)
        journal = MODULE.KernelJournal(LOCATION)
        with self.assertRaises(MODULE.CollectorError):
            journal.consume(b"x" * (MODULE.MAX_JOURNAL_BUFFER + 1))

    def test_kernel_journal_subprocess_lifecycle_and_buffering(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "journal-fixture"
            executable.write_text(
                "#!/usr/bin/python3\n"
                "import sys, time\n"
                "sys.stdout.write('[ 1.0] usb 3-2: fixture connected\\n')\n"
                "sys.stdout.flush()\n"
                "time.sleep(30)\n",
                encoding="ascii",
            )
            executable.chmod(0o755)
            with (
                mock.patch.object(MODULE, "JOURNALCTL", executable),
                mock.patch.object(MODULE, "require_fixed_executable"),
            ):
                journal = MODULE.KernelJournal(LOCATION)
                with journal:
                    deadline = time.monotonic() + 2
                    while not journal.filter.events and time.monotonic() < deadline:
                        journal.poll()
                        time.sleep(0.01)
                    self.assertEqual(
                        journal.filter.events[0].message,
                        "[ 1.0] usb 3-2: fixture connected",
                    )
                self.assertIsNone(journal.process)

    def test_kernel_journal_immediate_exit_fails_startup(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "journal-fixture"
            executable.write_text("#!/bin/sh\nexit 7\n", encoding="ascii")
            executable.chmod(0o755)
            with (
                mock.patch.object(MODULE, "JOURNALCTL", executable),
                mock.patch.object(MODULE, "require_fixed_executable"),
                self.assertRaisesRegex(
                    MODULE.CollectorError,
                    "kernel event reader exited during startup",
                ),
            ):
                journal = MODULE.KernelJournal(LOCATION)
                with journal:
                    self.fail("an exited journal reader was admitted")
            self.assertIsNone(journal.process)

    def test_evidence_is_canonical_private_and_contains_no_raw_stream(self):
        captured = MODULE.CaptureResult(
            frames=(
                MODULE.TimestampedRecord(
                    host_unix_ns=100,
                    host_monotonic_ns=10,
                    record=diagnostic_record(1, 10),
                ),
            ),
            usb_events=(MODULE.UsbEvent(90, "usb 3-2: connected"),),
            dropped_usb_events=0,
            end_reason="disconnected",
            transport_snapshots=(transport_snapshot(),),
        )
        evidence = MODULE.evidence_document(
            anchor=OrderedDict(
                host_boot_id=HOST_BOOT,
                usb_location=LOCATION,
            ),
            started_unix_ns=1,
            ended_unix_ns=200,
            result=captured,
        )
        encoded = MODULE.encode_evidence(evidence)
        self.assertEqual(encoded, json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n")
        self.assertNotIn(b"raw", encoded)
        self.assertEqual(evidence["transport_snapshot_count"], 1)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "private"
            directory.mkdir(mode=0o700)
            os.chmod(directory, 0o700)
            output = directory / "evidence.json"
            MODULE.write_evidence(output, encoded)
            metadata = output.stat()
            self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o600)
            self.assertEqual(output.read_bytes(), encoded)
            with self.assertRaises(MODULE.CollectorError):
                MODULE.write_evidence(output, encoded)

    def test_source_has_no_serial_write_or_shell_execution_surface(self):
        source = SOURCE.read_text(encoding="utf-8")
        serial = source[source.index("class ReceiveOnlySerial"):source.index("class KernelEventFilter")]
        self.assertIn("os.O_RDONLY", serial)
        self.assertNotIn("os.O_RDWR", serial)
        self.assertNotIn("os.write", serial)
        self.assertNotIn("shell=True", source)

    def test_existing_foreign_serial_holder_is_rejected(self):
        result = mock.Mock(returncode=0, stdout=f"{os.getpid()} 999999")
        with (
            mock.patch.object(MODULE, "require_fixed_executable"),
            mock.patch.object(MODULE.subprocess, "run", return_value=result),
            self.assertRaises(MODULE.CollectorError),
        ):
            MODULE.require_exclusive_holder("/dev/ttyACM7")

    def test_main_starts_kernel_capture_before_enumeration_and_writes_once(self):
        calls = []
        identity = MODULE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        captured = MODULE.CaptureResult(
            frames=(
                MODULE.TimestampedRecord(100, 10, diagnostic_record(1, 10)),
            ),
            usb_events=(),
            dropped_usb_events=0,
            end_reason="disconnected",
        )

        class Journal:
            def __init__(self, location):
                self.location = location
                self.filter = mock.Mock(events=[], dropped=0)
                self.poll_count = 0

            def __enter__(self):
                calls.append("journal-enter")
                return self

            def __exit__(self, *_):
                calls.append("journal-exit")

            def poll(self):
                self.poll_count += 1
                if self.poll_count == 2:
                    self.filter.events.append(
                        MODULE.UsbEvent(101, "usb 3-2: final disconnect")
                    )
                return []

        class Serial:
            def __init__(self, observed):
                self.observed = observed

            def __enter__(self):
                calls.append("serial-enter")
                return self

            def __exit__(self, *_):
                calls.append("serial-exit")

        def capture(*_, **__):
            calls.append("capture")
            return captured

        written = []
        anchor = OrderedDict(host_boot_id=HOST_BOOT, usb_location=LOCATION)
        class FlushWitness(io.StringIO):
            def __init__(self):
                super().__init__()
                self.flush_count = 0

            def flush(self):
                self.flush_count += 1
                return super().flush()

        stdout = FlushWitness()

        def enumerate_after_ready(*_):
            calls.append("enumerate")
            self.assertEqual(
                stdout.getvalue().splitlines(),
                [MODULE.COLLECTOR_READY],
            )
            self.assertEqual(stdout.flush_count, 1)
            return identity

        with (
            mock.patch.object(MODULE, "read_anchor", return_value=anchor),
            mock.patch.object(MODULE, "safe_new_output"),
            mock.patch.object(MODULE, "KernelJournal", Journal),
            mock.patch.object(
                MODULE,
                "wait_diagnostic_acm",
                side_effect=enumerate_after_ready,
            ),
            mock.patch.object(MODULE, "ReceiveOnlySerial", Serial),
            mock.patch.object(MODULE, "capture_stream", side_effect=capture),
            mock.patch.object(MODULE, "write_evidence", side_effect=lambda path, payload: written.append((path, payload))),
            mock.patch.object(MODULE.time, "sleep"),
            mock.patch.object(MODULE.sys, "stdout", stdout),
        ):
            self.assertEqual(
                MODULE.main(["/private/anchor", "/private/evidence"]),
                0,
            )
        self.assertLess(calls.index("journal-enter"), calls.index("enumerate"))
        self.assertLess(calls.index("enumerate"), calls.index("serial-enter"))
        self.assertEqual(
            stdout.getvalue().splitlines().count(MODULE.COLLECTOR_READY), 1
        )
        self.assertEqual(stdout.flush_count, 1)
        self.assertEqual(len(written), 1)
        document = json.loads(written[0][1])
        self.assertEqual(document["capture_status"], "valid")
        self.assertEqual(
            document["usb_events"][0]["message"],
            "usb 3-2: final disconnect",
        )

    def test_main_does_not_claim_ready_when_journal_startup_fails(self):
        class Journal:
            def __init__(self, _):
                pass

            def __enter__(self):
                raise MODULE.CollectorError("journal startup failed")

            def __exit__(self, *_):
                return None

        anchor = OrderedDict(host_boot_id=HOST_BOOT, usb_location=LOCATION)
        written = []
        stdout = io.StringIO()
        with (
            mock.patch.object(MODULE, "read_anchor", return_value=anchor),
            mock.patch.object(MODULE, "safe_new_output"),
            mock.patch.object(MODULE, "KernelJournal", Journal),
            mock.patch.object(
                MODULE,
                "write_evidence",
                side_effect=lambda path, payload: written.append(payload),
            ),
            mock.patch.object(MODULE.sys, "stdout", stdout),
        ):
            self.assertEqual(
                MODULE.main(["/private/anchor", "/private/evidence"]),
                1,
            )
        self.assertNotIn(MODULE.COLLECTOR_READY, stdout.getvalue())
        self.assertEqual(len(written), 1)

    def test_main_preserves_kernel_events_when_enumeration_fails(self):
        event = MODULE.UsbEvent(90, "usb 3-2: device departed")

        class Journal:
            def __init__(self, _):
                self.filter = mock.Mock(events=[event], dropped=2)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def poll(self):
                return []

        anchor = OrderedDict(host_boot_id=HOST_BOOT, usb_location=LOCATION)
        written = []
        with (
            mock.patch.object(MODULE, "read_anchor", return_value=anchor),
            mock.patch.object(MODULE, "safe_new_output"),
            mock.patch.object(MODULE, "KernelJournal", Journal),
            mock.patch.object(
                MODULE,
                "wait_diagnostic_acm",
                side_effect=MODULE.CollectorError("enumeration failed"),
            ),
            mock.patch.object(
                MODULE,
                "write_evidence",
                side_effect=lambda path, payload: written.append(payload),
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            self.assertEqual(
                MODULE.main(["/private/anchor", "/private/evidence"]),
                1,
            )
        document = json.loads(written[0])
        self.assertEqual(document["usb_events"][0]["message"], event.message)
        self.assertEqual(document["dropped_usb_events"], 2)

    def test_final_drain_failure_cannot_mask_rejected_valid_prefix(self):
        identity = MODULE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        partial = MODULE.CaptureResult(
            frames=(
                MODULE.TimestampedRecord(100, 10, diagnostic_record(1, 10)),
            ),
            usb_events=(),
            dropped_usb_events=0,
            end_reason="rejected",
        )

        class Journal:
            def __init__(self, _):
                self.filter = mock.Mock(events=[], dropped=0)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def poll(self):
                raise MODULE.CollectorError("journal departed")

        class Serial:
            def __init__(self, _):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

        written = []
        anchor = OrderedDict(host_boot_id=HOST_BOOT, usb_location=LOCATION)
        rejection = MODULE.CaptureRejected(
            "invalid-stream", "invalid stream", partial
        )
        with (
            mock.patch.object(MODULE, "read_anchor", return_value=anchor),
            mock.patch.object(MODULE, "safe_new_output"),
            mock.patch.object(MODULE, "KernelJournal", Journal),
            mock.patch.object(MODULE, "wait_diagnostic_acm", return_value=identity),
            mock.patch.object(MODULE, "ReceiveOnlySerial", Serial),
            mock.patch.object(MODULE, "capture_stream", side_effect=rejection),
            mock.patch.object(
                MODULE,
                "write_evidence",
                side_effect=lambda path, payload: written.append(payload),
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            self.assertEqual(
                MODULE.main(["/private/anchor", "/private/evidence"]),
                1,
            )
        document = json.loads(written[0])
        self.assertEqual(document["rejection_code"], "invalid-stream")
        self.assertEqual(document["frame_count"], 1)

    def test_final_drain_failure_retains_successful_capture_frames(self):
        identity = MODULE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        captured = MODULE.CaptureResult(
            frames=(
                MODULE.TimestampedRecord(100, 10, diagnostic_record(1, 10)),
            ),
            usb_events=(),
            dropped_usb_events=0,
            end_reason="disconnected",
        )

        class Journal:
            def __init__(self, _):
                self.filter = mock.Mock(events=[], dropped=0)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def poll(self):
                raise MODULE.CollectorError("journal departed")

        class Serial:
            def __init__(self, _):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

        written = []
        anchor = OrderedDict(host_boot_id=HOST_BOOT, usb_location=LOCATION)
        with (
            mock.patch.object(MODULE, "read_anchor", return_value=anchor),
            mock.patch.object(MODULE, "safe_new_output"),
            mock.patch.object(MODULE, "KernelJournal", Journal),
            mock.patch.object(MODULE, "wait_diagnostic_acm", return_value=identity),
            mock.patch.object(MODULE, "ReceiveOnlySerial", Serial),
            mock.patch.object(MODULE, "capture_stream", return_value=captured),
            mock.patch.object(
                MODULE,
                "write_evidence",
                side_effect=lambda path, payload: written.append(payload),
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            self.assertEqual(
                MODULE.main(["/private/anchor", "/private/evidence"]),
                1,
            )
        document = json.loads(written[0])
        self.assertEqual(
            document["rejection_code"], "collector-finalization"
        )
        self.assertEqual(document["frame_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
