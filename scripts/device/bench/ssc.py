"""Minimal Snapdragon Sensor Core (SLPI) client: QMI service 400 over QRTR.

The SLPI's sensors are reached as on Android, through the SNS client service:
sns_client_request_msg protobufs (encoded by hand here) in QMI request 0x20,
events back in report indications. Needs the SLPI running and hexagonrpcd
serving its registry (rog5-sensors.service); without the registry every
lookup comes back empty.

  ssc.py lookup [type ...]          SUIDs per data type
  ssc.py stream TYPE HZ SECONDS     stream one sensor, print samples
"""
import socket, struct, sys, time

AF_QIPCRTR = 42
SNS_SERVICE = 400
LOOKUP_SUID = (0xabababababababab, 0xabababababababab)


# ---- protobuf helpers -------------------------------------------------------
def varint(n):
    out = b''
    while True:
        b = n & 0x7f
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def field(num, wt, value):
    key = varint(num << 3 | wt)
    if wt == 0:
        return key + varint(value)
    if wt == 1:
        return key + struct.pack('<Q', value)
    if wt == 5:
        return key + (struct.pack('<f', value) if isinstance(value, float) else struct.pack('<I', value))
    return key + varint(len(value)) + value  # wt 2


def parse(buf):
    out, i = [], 0
    while i < len(buf):
        key, i = read_varint(buf, i)
        num, wt = key >> 3, key & 7
        if wt == 0:
            v, i = read_varint(buf, i)
        elif wt == 1:
            v = buf[i:i + 8]; i += 8
        elif wt == 5:
            v = buf[i:i + 4]; i += 4
        elif wt == 2:
            n, i = read_varint(buf, i)
            v = buf[i:i + n]; i += n
        else:
            raise ValueError(f'wire type {wt}')
        out.append((num, wt, v))
    return out


def read_varint(buf, i):
    n = shift = 0
    while True:
        b = buf[i]; i += 1
        n |= (b & 0x7f) << shift
        shift += 7
        if not b & 0x80:
            return n, i


def suid_msg(suid):
    return field(1, 1, suid[0]) + field(2, 1, suid[1])


def client_request(suid, msg_id, payload, batch=None):
    susp = field(1, 0, 1) + field(2, 0, 1)          # APSS, no wakeup
    req = field(2, 2, payload)
    return (field(1, 2, suid_msg(suid)) + field(2, 5, msg_id) + field(3, 2, susp) + field(4, 2, req))


# ---- QMI over QRTR ------------------------------------------------------------
class Client:
    def __init__(self):
        self.s = socket.socket(AF_QIPCRTR, socket.SOCK_DGRAM)
        self.s.settimeout(3)
        node, _ = self.s.getsockname()
        self.s.sendto(struct.pack('<IIIII', 10, SNS_SERVICE, 0, 0, 0), (node, 0xfffffffe))
        self.addr = None
        while True:
            d = self.s.recv(64)
            cmd, svc, ins, nd, pt = struct.unpack('<IIIII', d[:20])
            if cmd == 4 and svc == SNS_SERVICE:
                self.addr = (nd, pt)
            if cmd == 4 and svc == 0:
                break
        if not self.addr:
            raise SystemExit('no SNS service')
        self.txn = 1

    def request(self, pb):
        tlv = struct.pack('<BHH', 1, len(pb) + 2, len(pb)) + pb + struct.pack('<BHB', 0x10, 1, 0)
        hdr = struct.pack('<BHHH', 0, self.txn, 0x20, len(tlv))
        self.txn += 1
        self.s.sendto(hdr + tlv, self.addr)

    def messages(self, until):
        while time.monotonic() < until:
            try:
                d, _ = self.s.recvfrom(65536)
            except socket.timeout:
                continue
            typ, txn, msg_id, ln = struct.unpack('<BHHH', d[:7])
            tlvs, i = {}, 7
            while i < 7 + ln:
                t, l = struct.unpack('<BH', d[i:i + 3])
                tlvs[t] = d[i + 3:i + 3 + l]
                i += 3 + l
            yield typ, msg_id, tlvs


def events(tlvs):
    raw = tlvs.get(2, b'')
    pb = raw[2:2 + struct.unpack('<H', raw[:2])[0]] if len(raw) >= 2 else b''
    suid = None
    for num, wt, v in parse(pb):
        if num == 1:
            f = {n: x for n, _, x in parse(v)}
            suid = (struct.unpack('<Q', f[1])[0], struct.unpack('<Q', f[2])[0])
        elif num == 2:
            ev = {n: x for n, _, x in parse(v)}
            yield suid, struct.unpack('<I', ev[1])[0], ev.get(3, b'')


def lookup(c, types, wait=4):
    for t in types:
        c.request(client_request(LOOKUP_SUID, 512, field(1, 2, t.encode()) + field(2, 0, 0) + field(3, 0, 0)))
    found = {}
    for typ, msg_id, tlvs in c.messages(time.monotonic() + wait):
        if typ == 2:
            continue
        for suid, mid, payload in events(tlvs):
            if mid != 768:
                continue
            name, suids = '', []
            for num, wt, v in parse(payload):
                if num == 1:
                    name = v.decode()
                elif num == 2:
                    f = {n: x for n, _, x in parse(v)}
                    suids.append((struct.unpack('<Q', f[1])[0], struct.unpack('<Q', f[2])[0]))
            found[name] = suids
    return found


def read(data_type, hz=25.0, seconds=2.0):
    """Samples ([floats], status) of the first sensor of data_type; [] if none."""
    c = Client()
    suids = lookup(c, [data_type]).get(data_type)
    if not suids:
        return []
    c.request(client_request(suids[0], 513, field(1, 5, float(hz))))
    samples = []
    for typ, msg_id, tlvs in c.messages(time.monotonic() + seconds):
        if typ == 2:
            continue
        for suid, mid, payload in events(tlvs):
            if mid != 1025:
                continue
            data, status = [], None
            for num, wt, v in parse(payload):
                if num == 1 and wt == 2:
                    data += list(struct.unpack(f'<{len(v) // 4}f', v))
                elif num == 1 and wt == 5:
                    data.append(struct.unpack('<f', v)[0])
                elif num == 2:
                    status = v
            samples.append((data, status))
    return samples


def main():
    c = Client()
    if sys.argv[1] == 'lookup':
        types = sys.argv[2:] or ['accel', 'gyro', 'mag', 'proximity', 'ambient_light', 'pressure',
                                 'sensor_temperature', 'gravity', 'game_rv', 'rotv', 'sig_motion', 'step_detect',
                                 'hinge_angle', 'device_orient']
        for name, suids in sorted(lookup(c, types).items()):
            print(f'{name:20s} {len(suids)} ' + ' '.join(f'{lo:016x}:{hi:016x}' for lo, hi in suids))
        return
    if sys.argv[1] == 'stream':
        t, hz, secs = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
        suids = lookup(c, [t]).get(t)
        if not suids:
            raise SystemExit(f'no {t} sensor')
        c.request(client_request(suids[0], 513, field(1, 5, hz)))
        n = 0
        for typ, msg_id, tlvs in c.messages(time.monotonic() + secs):
            if typ == 2:
                continue
            for suid, mid, payload in events(tlvs):
                if mid == 1025:
                    data, status = [], None
                    for num, wt, v in parse(payload):
                        if num == 1 and wt == 2:
                            data += list(struct.unpack(f'<{len(v) // 4}f', v))
                        elif num == 1 and wt == 5:
                            data.append(struct.unpack('<f', v)[0])
                        elif num == 2:
                            status = v
                    n += 1
                    if n <= 5 or n % 25 == 0:
                        print(f'{t} #{n} status={status} ' + ' '.join(f'{x:.3f}' for x in data), flush=True)
                elif n == 0:
                    print(f'event msg_id {mid} len {len(payload)}', flush=True)
        print(f'{t}: {n} samples in {secs}s')


if __name__ == '__main__':
    main()
