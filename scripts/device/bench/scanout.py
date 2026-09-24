#!/usr/bin/env python3
"""Screenshot of what the panel is showing: the scanout framebuffer of DSI-1.

Root only (GETFB2 hands out buffer handles to CAP_SYS_ADMIN). Reads the
framebuffer attached to the primary plane of the active CRTC, exports it as a
dma-buf and writes a PNG (downscaled by --scale). Works whatever compositor
is running. Linear 32-bit RGB is read directly; compressed (UBWC) buffers go
through scanout-read.c (EGL import + glReadPixels, built with gcc on first use).
  scanout.py info            print the plane/framebuffer/modifier
  scanout.py png OUT [--scale N]
"""
import ctypes, fcntl, mmap, os, struct, subprocess, sys, zlib

CARD = '/dev/dri/card1'
SET_CLIENT_CAP = 0x4010640d
CAP_UNIVERSAL_PLANES = 2
GETPLANERESOURCES = 0xc01064b5
GETPLANE = 0xc02064b6
GETFB2 = 0xc06864ce
PRIME_HANDLE_TO_FD = 0xc00c642d
DMA_BUF_SYNC = 0x40086200
DMA_BUF_SYNC_READ, DMA_BUF_SYNC_START, DMA_BUF_SYNC_END = 1, 0, 4
LINEAR = 0
FOURCC = {0x34325258: 'XR24', 0x34325241: 'AR24', 0x34324258: 'XB24', 0x34324241: 'AB24'}


def ioctl(fd, req, fmt, *values):
    buf = bytearray(struct.pack(fmt, *values))
    fcntl.ioctl(fd, req, buf, True)
    return struct.unpack(fmt, buf)


def planes(fd):
    n = ioctl(fd, GETPLANERESOURCES, '<QI4x', 0, 0)[1]
    arr = (ctypes.c_uint32 * n)()
    ioctl(fd, GETPLANERESOURCES, '<QI4x', ctypes.addressof(arr), n)
    return list(arr)


def active_fb(fd):
    # without universal planes the primary plane is not listed
    fcntl.ioctl(fd, SET_CLIENT_CAP, struct.pack('<QQ', CAP_UNIVERSAL_PLANES, 1))
    for pid in planes(fd):
        plane_id, crtc_id, fb_id = ioctl(fd, GETPLANE, '<6IQ', pid, 0, 0, 0, 0, 0, 0)[:3]
        if crtc_id and fb_id:
            return pid, fb_id
    raise RuntimeError('no plane is scanning out (display off?)')


def fb_info(fd, fb_id):
    v = ioctl(fd, GETFB2, '<5I4I4I4I4x4Q', fb_id, *([0] * 16), *([0] * 4))
    return dict(fb=fb_id, width=v[1], height=v[2], format=FOURCC.get(v[3], hex(v[3])), flags=v[4],
                handle=v[5], pitch=v[9], offset=v[13], modifier=v[17])


HERE = os.path.dirname(os.path.abspath(__file__))


def grab_gpu(info, scale):
    helper = os.path.join(HERE, 'scanout-read')
    source = helper + '.c'
    if not os.path.exists(helper) or os.path.getmtime(helper) < os.path.getmtime(source):
        subprocess.run(['gcc', '-O2', '-o', helper, source, '-lEGL', '-lGLESv2'], check=True)
    raw_path = '/run/rog5-scanout.rgba'
    out = subprocess.run([helper, raw_path], capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr.strip())
    w, h = map(int, out.stdout.split())
    with open(raw_path, 'rb') as f:
        data = f.read()
    os.unlink(raw_path)
    rows = []
    for y in range(0, h, scale):
        line = data[y * w * 4:(y + 1) * w * 4]
        px = bytearray()
        for x in range(0, w * 4, 4 * scale):
            px += line[x:x + 3]
        rows.append(b'\0' + bytes(px))
    return info, (w + scale - 1) // scale, len(rows), b''.join(rows)


def grab(scale=4):
    fd = os.open(CARD, os.O_RDWR | os.O_CLOEXEC)
    try:
        plane, fb_id = active_fb(fd)
        info = fb_info(fd, fb_id)
        if info['modifier'] != LINEAR:
            return grab_gpu(info, scale)
        if info['format'] not in FOURCC.values():
            raise RuntimeError(f'cannot decode scanout buffer: {info}')
        dfd = ioctl(fd, PRIME_HANDLE_TO_FD, '<IIi', info['handle'], os.O_CLOEXEC, -1)[2]
    finally:
        os.close(fd)
    try:
        size = info['offset'] + info['pitch'] * info['height']
        m = mmap.mmap(dfd, size, mmap.MAP_SHARED, mmap.PROT_READ)
        fcntl.ioctl(dfd, DMA_BUF_SYNC, struct.pack('<Q', DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ))
        data = bytes(m[:size])
        fcntl.ioctl(dfd, DMA_BUF_SYNC, struct.pack('<Q', DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ))
        m.close()
    finally:
        os.close(dfd)
    w, h, pitch, off = info['width'], info['height'], info['pitch'], info['offset']
    bgr = info['format'] in ('XR24', 'AR24')  # little-endian B,G,R,X in memory
    rows = []
    for y in range(0, h, scale):
        line = data[off + y * pitch: off + y * pitch + w * 4]
        px = bytearray()
        for x in range(0, w * 4, 4 * scale):
            b0, b1, b2 = line[x], line[x + 1], line[x + 2]
            px += bytes((b2, b1, b0)) if bgr else bytes((b0, b1, b2))
        rows.append(b'\0' + bytes(px))
    return info, (w + scale - 1) // scale, len(rows), b''.join(rows)


def png(path, w, h, raw):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'png':
        if '--no-wake' not in sys.argv:
            sys.path.insert(0, HERE)
            from vtouch import wake_display
            wake_display()
        scale = int(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 4
        info, w, h, raw = grab(scale)
        png(sys.argv[2], w, h, raw)
        print(dict(info, png=sys.argv[2], size=(w, h)))
    else:
        fd = os.open(CARD, os.O_RDWR | os.O_CLOEXEC)
        plane, fb_id = active_fb(fd)
        print(dict(fb_info(fd, fb_id), plane=plane))


if __name__ == '__main__':
    main()
