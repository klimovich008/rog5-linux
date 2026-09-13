#!/usr/bin/env python3
"""Two bounded native/VNC VM capture pairs; no physical-device access."""
import hashlib
import json
from pathlib import Path
import struct
import time
import zlib


def ppm_to_png(data):
    header = b'P6\n540 1224\n255\n'
    if not data.startswith(header) or len(data) != len(header) + 540 * 1224 * 3:
        raise ValueError('native capture must be exact 540x1224 RGB PPM')
    pixels = memoryview(data)[len(header):]
    raw = b''.join(b'\0' + pixels[y*1620:(y+1)*1620].tobytes() for y in range(1224))
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind+value))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 540, 1224, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


class NativeCapture:
    LABELS = {'00-editor-empty.png': 'initial', '04-editor-test-restored.png': 'final'}

    def __init__(self, directory, vnc_capture, png_identity, timeout=8):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700)
        self.vnc_capture, self.png_identity = vnc_capture, png_identity
        self.timeout = timeout
        self.records = []

    def check_bound(self):
        size = 0
        for path in self.directory.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError('unexpected native capture file type')
            size += path.stat().st_size
        if size > 8 * 1024 * 1024:
            raise ValueError('native capture exceeds 8 MiB aggregate')

    def __call__(self, socket, name, path):
        self.vnc_capture(socket, name, path)
        label = self.LABELS.get(path.name)
        if label is None:
            return
        start = time.monotonic()
        request = self.directory / (label + '.request')
        with request.open('x') as stream:
            stream.write(label + '\n')
        done = self.directory / (label + '.done')
        while True:
            self.check_bound()
            if done.exists():
                if done.read_bytes() != b'0\n':
                    raise ValueError('native screencopy client failed')
                break
            if time.monotonic() - start >= self.timeout:
                raise TimeoutError('native screencopy deadline')
            time.sleep(0.02)
        ppm = self.directory / (label + '.ppm')
        self.check_bound()
        with ppm.open('rb') as stream:
            data = stream.read(2 * 1024 * 1024 + 1)
        encoded = ppm_to_png(data)
        png = path.with_name(path.stem + '-native.png')
        with png.open('xb') as stream:
            stream.write(encoded)
        metadata_path = self.directory / (label + '.json')
        if metadata_path.stat().st_size > 16384:
            raise ValueError('oversized native capture metadata')
        metadata = json.loads(metadata_path.read_text())
        self.records.append({'label': label, 'vnc': self.png_identity(path),
                             'native': self.png_identity(png), 'metadata': metadata,
                             'ppm_sha256': hashlib.sha256(data).hexdigest(),
                             'duration_seconds': time.monotonic()-start,
                             'scope': 'sequential VNC/native output capture; not exact same frame'})
