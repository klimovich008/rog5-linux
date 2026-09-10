"""Pure evidence parser for a separately admitted ROG5 physical-key reader.

No device access, execution authority, fixture backend or LED writes live here.
The controller must bind the stream to a freshly opened, validated input device
on the exact admitted boot. Parsed bytes alone do not prove a physical press.
"""

import re
import struct


KEYS = {'power': (116, 'pmic_pwrkey'),
        'volume-down': (114, 'pmic_resin'),
        'volume-up': (115, 'volume_up')}
# The admitted phone uses the little-endian AArch64 input_event ABI. Do not use
# the host's native long size, endianness or alignment to interpret its records.
EVENT = struct.Struct('<qqHHi')
MAX_RECORDS = 4096
MAX_IRQ_BYTES = 65536


class EvidenceError(ValueError):
    """Malformed, incomplete or contradictory key evidence."""


class KeyStream:
    """Incrementally check one press/release, retaining only a partial record.

    The caller enforces a monotonic wall-clock deadline, reads bounded chunks,
    and calls finish only once the reader has closed. SYN_DROPPED makes the
    entire observation fail; it cannot be repaired from this evidence stream.
    """

    def __init__(self, key):
        if key not in KEYS:
            raise EvidenceError('unsupported key')
        self.key = key
        self.code = KEYS[key][0]
        self.pending = b''
        self.records = 0
        self.phase = 'waiting'
        self.error = False
        self.closed = False
        self.previous_time = None

    @property
    def complete(self):
        return self.phase == 'released' and not self.error

    def feed(self, data):
        if self.closed or self.error:
            raise EvidenceError('stream already closed or failed')
        try:
            if not isinstance(data, bytes):
                raise EvidenceError('event chunk must be bytes')
            if len(data) + len(self.pending) > (
                    MAX_RECORDS - self.records) * EVENT.size:
                raise EvidenceError('event stream exceeds record bound')
            data = self.pending + data
            count = len(data) // EVENT.size
            for offset in range(0, count * EVENT.size, EVENT.size):
                sec, usec, kind, code, value = EVENT.unpack_from(data, offset)
                self.records += 1
                timestamp = (sec, usec)
                if sec < 0 or not 0 <= usec < 1000000:
                    raise EvidenceError('invalid event timestamp')
                if self.previous_time is not None and timestamp < self.previous_time:
                    raise EvidenceError('event time moved backwards')
                self.previous_time = timestamp
                if kind == 0 and code == 3:
                    raise EvidenceError('SYN_DROPPED loses physical event evidence')
                if kind != 1:
                    continue
                if code != self.code:
                    raise EvidenceError('unexpected key code')
                if value == 2:
                    raise EvidenceError('autorepeat is forbidden')
                if value == 1 and self.phase == 'waiting':
                    self.phase = 'pressed'
                elif value == 0 and self.phase == 'pressed':
                    self.phase = 'released'
                else:
                    raise EvidenceError('invalid press/release order or value')
            self.pending = data[count * EVENT.size:]
        except EvidenceError:
            self.error = True
            raise

    def finish(self):
        if self.closed or self.error:
            raise EvidenceError('stream already closed or failed')
        self.closed = True
        if self.pending:
            self.error = True
            raise EvidenceError('truncated input_event')
        if not self.complete:
            self.error = True
            raise EvidenceError('missing physical press and release')
        return {'key': self.key, 'code': self.code, 'presses': 1,
                'releases': 1, 'records': self.records}


def _irq_record(text, key):
    """Sum only CPU count columns for exactly one expected IRQ action.

    Numeric hardware IRQ IDs after the CPU columns are metadata, not counters.
    This deliberately refuses shared action names and duplicate matching rows.
    """
    if key not in KEYS:
        raise EvidenceError('unsupported key')
    if not isinstance(text, str) or len(text) > MAX_IRQ_BYTES:
        raise EvidenceError('interrupt snapshot is absent or oversized')
    lines = text.splitlines()
    if not lines:
        raise EvidenceError('missing interrupt CPU header')
    cpus = lines[0].split()
    if (not cpus or len(cpus) > 256 or len(set(cpus)) != len(cpus) or
            any(re.fullmatch(r'CPU[0-9]+', cpu) is None for cpu in cpus)):
        raise EvidenceError('invalid interrupt CPU header')
    label = KEYS[key][1]
    matches = []
    for line in lines[1:]:
        fields = line.split()
        if label not in fields:
            continue
        if (len(fields) < len(cpus) + 3 or fields[-1] != label or
                re.fullmatch(r'[0-9]+:', fields[0]) is None):
            raise EvidenceError('unexpected IRQ identity')
        counts = fields[1:1 + len(cpus)]
        if any(re.fullmatch(r'[0-9]{1,20}', value) is None for value in counts):
            raise EvidenceError('invalid IRQ CPU count')
        matches.append((sum(int(value) for value in counts), tuple(cpus),
                        (fields[0], *fields[1 + len(cpus):])))
    if len(matches) != 1:
        raise EvidenceError('expected exactly one IRQ action')
    return matches[0]


def irq_count(text, key):
    return _irq_record(text, key)[0]


def irq_delta(before, after, key):
    first = _irq_record(before, key)
    last = _irq_record(after, key)
    if first[1:] != last[1:]:
        raise EvidenceError('IRQ identity or CPU topology changed')
    delta = last[0] - first[0]
    if not 2 <= delta <= 16:
        raise EvidenceError('IRQ delta outside physical press/release bounce bound')
    return delta
