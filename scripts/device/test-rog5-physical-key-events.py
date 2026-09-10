#!/usr/bin/env python3
"""Focused hostile-stream checks; no device or privileged backend exists."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    'key_events', Path(__file__).with_name('rog5_physical_key_events.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def event(code=116, value=1, kind=1, sec=5, usec=10):
    return M.EVENT.pack(sec, usec, kind, code, value)


def interrupts(count=10, hardware=291, label='pmic_pwrkey'):
    return f'           CPU0       CPU1\n 45: {count} 2 GICv3 {hardware} Edge {label}\n'


class Events(unittest.TestCase):
    def test_all_keys_split_at_every_byte_boundary(self):
        for key, (code, _) in M.KEYS.items():
            payload = event(code) + event(0, 0, 0) + event(code, 0)
            for split in range(len(payload) + 1):
                with self.subTest(key=key, split=split):
                    parser = M.KeyStream(key)
                    parser.feed(payload[:split]); parser.feed(payload[split:])
                    self.assertEqual(parser.finish(), {'key': key, 'code': code,
                        'presses': 1, 'releases': 1, 'records': 3})

    def test_bytewise_read(self):
        parser = M.KeyStream('power')
        for byte in event() + event(value=0):
            parser.feed(bytes([byte]))
        self.assertTrue(parser.complete)
        parser.finish()

    def test_wrong_order_values_and_code(self):
        cases = [event(value=0), event()+event(), event(value=2),
                 event(value=-1), event(value=65536), event(code=114),
                 event()+event(value=0)+event(),
                 event()+event(value=0)+event(value=0)]
        for payload in cases:
            with self.subTest(payload=payload.hex()):
                parser = M.KeyStream('power')
                with self.assertRaises(M.EvidenceError):
                    parser.feed(payload)
                self.assertFalse(parser.complete)
                with self.assertRaises(M.EvidenceError):
                    parser.finish()

    def test_dropped_syn_fails_before_or_after_release(self):
        dropped = event(code=3, value=0, kind=0)
        for payload in (dropped, event()+dropped,
                        event()+event(value=0)+dropped):
            with self.assertRaisesRegex(M.EvidenceError, 'SYN_DROPPED'):
                M.KeyStream('power').feed(payload)

    def test_incomplete_and_truncated(self):
        for payload in (b'', event(), event()+event(value=0)[:-1],
                        event()+event(value=0)+b'x'):
            parser = M.KeyStream('power'); parser.feed(payload)
            with self.assertRaises(M.EvidenceError):
                parser.finish()

    def test_timestamp_validation(self):
        for payload in (event(sec=-1), event(usec=-1), event(usec=1000000),
                        event(sec=6)+event(value=0, sec=5)):
            with self.assertRaises(M.EvidenceError):
                M.KeyStream('power').feed(payload)

    def test_record_bound_and_closed_stream(self):
        parser = M.KeyStream('power')
        parser.feed(event()+event(value=0)); parser.finish()
        for operation in (parser.finish, lambda: parser.feed(b'')):
            with self.assertRaises(M.EvidenceError): operation()
        with self.assertRaisesRegex(M.EvidenceError, 'record bound'):
            M.KeyStream('power').feed(event() * (M.MAX_RECORDS + 1))

    def test_types_and_unknown_key(self):
        with self.assertRaises(M.EvidenceError): M.KeyStream('home')
        with self.assertRaises(M.EvidenceError): M.KeyStream('power').feed('bytes')


class Interrupts(unittest.TestCase):
    def test_counter_columns_exclude_hardware_irq_number(self):
        self.assertEqual(M.irq_count(interrupts(), 'power'), 12)
        self.assertEqual(M.irq_count(interrupts(hardware=987), 'power'), 12)
        self.assertEqual(M.irq_delta(interrupts(), interrupts(12), 'power'), 2)

    def test_identity_and_cpu_topology_must_remain_exact(self):
        for snapshot in (interrupts(12, 987),
                         interrupts(12).replace('CPU1', 'CPU2'),
                         interrupts(12).replace('45:', '46:')):
            with self.assertRaisesRegex(M.EvidenceError, 'identity or CPU'):
                M.irq_delta(interrupts(), snapshot, 'power')

    def test_all_key_labels(self):
        for key, (_, label) in M.KEYS.items():
            self.assertEqual(M.irq_count(interrupts(label=label), key), 12)

    def test_bad_headers_rows_and_identity(self):
        cases = ['', 'CPU0 CPU0\n', interrupts().replace('CPU1', 'notCPU'),
                 interrupts().replace('10 2', '10 -2'),
                 interrupts().replace('45:', 'IPI:'),
                 interrupts(label='other'), interrupts()+interrupts().splitlines()[1],
                 interrupts().replace('pmic_pwrkey', 'pmic_pwrkey shared')]
        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                with self.assertRaises(M.EvidenceError):
                    M.irq_count(snapshot, 'power')

    def test_delta_bounds(self):
        for count in (0, 10, 11, 27):
            with self.assertRaises(M.EvidenceError):
                M.irq_delta(interrupts(), interrupts(count), 'power')
        self.assertEqual(M.irq_delta(interrupts(), interrupts(26), 'power'), 16)


if __name__ == '__main__':
    unittest.main()
