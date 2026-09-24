#!/usr/bin/env python3
"""Adreno recovery probe: inject one GPU fault or hang, then prove the GPU still works.

Uses the msm render node directly (no Mesa), so the result isolates the kernel
recovery path from any userspace driver:
  nop    submit a CP_NOP stream and wait for its fence (health check only)
  fault  CP_INDIRECT_BUFFER at iova 0: an SMMU translation fault from the CP,
         the same signature the compositor hit on 2026-09-24
  hang   CP_WAIT_REG_MEM on a value that never arrives: a hangcheck timeout
  cycle  N x (NOP, sleep past the 66 ms autosuspend): stresses GMU slumber and
         cold boot without any userspace driver; any fault or GMU error fails it
After a fault/hang it submits NOPs until one completes and reports how long
recovery took, plus the kernel lines logged meanwhile. Exit 0 only if the GPU
recovered. Never run it while the GPU is already unhealthy.
"""
import ctypes, fcntl, json, mmap, os, struct, subprocess, sys, time

RENDER = '/dev/dri/renderD128'
MSM_PIPE_3D0 = 0x10
MSM_BO_WC = 0x00020000
MSM_SUBMIT_CMD_BUF = 1
MSM_SUBMIT_BO_READ = 1
MSM_INFO_GET_OFFSET = 0
MSM_INFO_GET_IOVA = 1
CP_NOP = 0x10
CP_WAIT_REG_MEM = 0x3c
CP_INDIRECT_BUFFER = 0x3f


def _iowr(nr, size):
    return (3 << 30) | (size << 16) | (ord('d') << 8) | (0x40 + nr)


def _iow(nr, size):
    return (1 << 30) | (size << 16) | (ord('d') << 8) | (0x40 + nr)


GEM_NEW = _iowr(0x02, 16)
GEM_INFO = _iowr(0x03, 24)
GEM_SUBMIT = _iowr(0x06, 72)
WAIT_FENCE = _iow(0x07, 32)


def parity(v):
    x = (v ^ (v >> 4) ^ (v >> 8) ^ (v >> 12) ^ (v >> 16) ^ (v >> 20) ^ (v >> 24) ^ (v >> 28)) & 0xf
    return (0x9669 >> x) & 1


def pkt7(op, payload):
    n = len(payload)
    hdr = 0x70000000 | n | (parity(n) << 15) | ((op & 0x7f) << 16) | (parity(op) << 23)
    return [hdr] + payload


class Gpu:
    def __init__(self):
        self.fd = os.open(RENDER, os.O_RDWR | os.O_CLOEXEC)

    def ioctl(self, req, buf):
        fcntl.ioctl(self.fd, req, buf, True)
        return buf

    def bo(self, size=4096):
        b = self.ioctl(GEM_NEW, bytearray(struct.pack('<QII', size, MSM_BO_WC, 0)))
        handle = struct.unpack_from('<I', b, 12)[0]
        info = self.ioctl(GEM_INFO, bytearray(struct.pack('<IIQII', handle, MSM_INFO_GET_OFFSET, 0, 0, 0)))
        off = struct.unpack_from('<Q', info, 8)[0]
        m = mmap.mmap(self.fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=off)
        info = self.ioctl(GEM_INFO, bytearray(struct.pack('<IIQII', handle, MSM_INFO_GET_IOVA, 0, 0, 0)))
        return handle, m, struct.unpack_from('<Q', info, 8)[0]

    def submit(self, words, extra=()):
        """Submit one command buffer; extra BO handles are attached so the CP may read them."""
        handle, m, _ = self.bo()
        data = struct.pack('<%dI' % len(words), *words)
        m[:len(data)] = data
        handles = [handle] + list(extra)
        bos = (ctypes.c_uint8 * (16 * len(handles))).from_buffer_copy(
            b''.join(struct.pack('<IIQ', MSM_SUBMIT_BO_READ, h, 0) for h in handles))
        cmds = (ctypes.c_uint8 * 32).from_buffer_copy(struct.pack('<IIIIIIQ', MSM_SUBMIT_CMD_BUF, 0, 0, len(data), 0, 0, 0))
        req = bytearray(struct.pack('<IIIIQQiIQQIIII', MSM_PIPE_3D0, 0, len(handles), 1, ctypes.addressof(bos),
                                    ctypes.addressof(cmds), -1, 0, 0, 0, 0, 0, 0, 0))
        self.ioctl(GEM_SUBMIT, req)
        return struct.unpack_from('<I', req, 4)[0]

    def wait(self, fence, seconds):
        deadline = time.clock_gettime(time.CLOCK_MONOTONIC) + seconds
        sec, nsec = int(deadline), int((deadline % 1) * 1e9)
        try:
            self.ioctl(WAIT_FENCE, bytearray(struct.pack('<IIqqII', fence, 0, sec, nsec, 0, 0)))
            return True
        except OSError:
            return False


def kmsg_since(cursor):
    out = subprocess.run(['journalctl', '-k', '-o', 'short-monotonic', '--no-pager', '--after-cursor', cursor],
                         capture_output=True, text=True).stdout
    keys = ('gmu', 'gpu', 'adreno', 'a6xx', 'smmu', 'hangcheck', 'recover', 'gdsc')
    return [l for l in out.splitlines() if any(k in l.lower() for k in keys) and 'drm:dpu' not in l]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'nop'
    assert mode in ('nop', 'fault', 'hang', 'cycle')
    cursor = subprocess.run(['journalctl', '-k', '-n', '0', '--show-cursor', '-q', '--no-pager'],
                            capture_output=True, text=True).stdout.strip().split('cursor: ')[-1]
    gpu = Gpu()
    result = {'mode': mode}
    t0 = time.monotonic()
    if not gpu.wait(gpu.submit(pkt7(CP_NOP, [0] * 4)), 5):
        result.update(status='FAIL', reason='GPU unhealthy before injection')
        print(json.dumps(result, indent=2)); return 1
    result['baseline_nop_ms'] = round((time.monotonic() - t0) * 1000, 2)
    if mode == 'cycle':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        slow, worst, failed = 0, 0.0, None
        for i in range(count):
            time.sleep(0.12)
            t = time.monotonic()
            if not gpu.wait(gpu.submit(pkt7(CP_NOP, [0] * 4)), 5):
                failed = i
                break
            dt = (time.monotonic() - t) * 1000
            worst = max(worst, dt)
            slow += dt > 50
        time.sleep(1)
        result.update(cycles=count if failed is None else failed, first_failure=failed,
                      worst_wake_ms=round(worst, 2), wakes_over_50ms=slow, kernel=kmsg_since(cursor)[-25:])
        result['status'] = 'PASS' if failed is None and not any(
            'ERROR' in l or 'fault' in l for l in result['kernel']) else 'FAIL'
    elif mode != 'nop':
        extra = ()
        if mode == 'fault':
            bad = pkt7(CP_INDIRECT_BUFFER, [0, 0, 16])
        else:
            poll, _, iova = gpu.bo()
            extra = (poll,)
            # wait until *iova == 0xdeadbeef (never written): function EQ, poll interval 16
            bad = pkt7(CP_WAIT_REG_MEM, [0x13, iova & 0xffffffff, iova >> 32, 0xdeadbeef, 0xffffffff, 16])
        t1 = time.monotonic()
        bad_fence = gpu.submit(bad + pkt7(CP_NOP, [0]), extra)
        gpu.wait(bad_fence, 30)
        recovered = None
        while time.monotonic() - t1 < 40:
            try:
                if gpu.wait(gpu.submit(pkt7(CP_NOP, [0] * 4)), 5):
                    recovered = round(time.monotonic() - t1, 2)
                    break
            except OSError as e:
                result.setdefault('submit_errors', []).append(str(e))
                time.sleep(1)
        result['recovered_after_s'] = recovered
        time.sleep(1)
        result['kernel'] = kmsg_since(cursor)[-25:]
        result['status'] = 'PASS' if recovered is not None and not any(
            'timed out' in l or "didn't collapse" in l for l in result['kernel']) else 'FAIL'
    else:
        result['status'] = 'PASS'
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
