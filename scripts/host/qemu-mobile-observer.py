#!/usr/bin/env python3
"""Bounded QMP capture/input for one harness-owned portrait mobile VM."""
import hashlib
import json
from pathlib import Path
import socket
import struct
import time
import zlib


class QMP:
    ALLOWED = {'qmp_capabilities', 'query-name', 'query-status', 'screendump', 'input-send-event'}

    def __init__(self, path, name, timeout=2):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.timeout = timeout
        self.buffer = b''
        self.sequence = 0
        self.records = []
        try:
            self.socket.settimeout(timeout)
            self.socket.connect(str(path))
            if 'QMP' not in self.receive(time.monotonic()+timeout):
                raise ValueError('missing QMP greeting')
            self.execute('qmp_capabilities')
            if self.execute('query-name') != {'name': name}:
                raise ValueError('QMP does not identify this owned VM')
            if not self.execute('query-status').get('running'):
                raise ValueError('owned VM is not running')
        except BaseException:
            self.close()
            raise

    def receive(self, deadline):
        while b'\n' not in self.buffer:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('QMP response deadline')
            self.socket.settimeout(remaining)
            block = self.socket.recv(4096)
            if not block:
                raise EOFError('QMP disconnected')
            self.buffer += block
            if len(self.buffer) > 65536:
                raise ValueError('QMP response exceeds 64 KiB')
        line, self.buffer = self.buffer.split(b'\n', 1)
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError('QMP message must be an object')
        return value

    def execute(self, command, arguments=None):
        if command not in self.ALLOWED or self.sequence >= 64:
            raise ValueError('QMP command outside bounded observation')
        self.sequence += 1
        request = {'execute': command, 'id': self.sequence}
        if arguments is not None:
            request['arguments'] = arguments
        deadline = time.monotonic()+self.timeout
        self.socket.settimeout(self.timeout)
        self.socket.sendall(json.dumps(request).encode()+b'\n')
        for _ in range(32):
            response = self.receive(deadline)
            if 'event' in response:
                continue
            self.records.append({'request': request, 'response': response})
            if response.get('id') != self.sequence:
                raise ValueError('QMP response identity mismatch')
            if 'error' in response:
                raise RuntimeError('QMP rejected request: '+str(response['error']))
            if 'return' not in response:
                raise ValueError('QMP reply lacks result')
            return response['return']
        raise ValueError('excessive QMP event stream')

    def close(self):
        self.socket.close()


def png_identity(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4*1024*1024:
        raise ValueError('invalid or oversized screenshot')
    with path.open('rb') as stream:
        data = stream.read(4*1024*1024+1)
        if len(data) > 4*1024*1024:
            raise ValueError('screenshot grew beyond bound')
        header = data[:33]
        if (len(header) != 33 or header[:8] != b'\x89PNG\r\n\x1a\n'
                or header[8:16] != b'\0\0\0\rIHDR'):
            raise ValueError('screenshot is not PNG')
        width, height = struct.unpack('>II', header[16:24])
        if (width, height) != (540, 1224):
            raise ValueError('unexpected portrait screenshot dimensions')
        if header[24] != 8 or header[25] not in (2, 6) or header[26:29] != b'\0\0\0':
            raise ValueError('unsupported screenshot encoding')
        offset, compressed, ended = 8, bytearray(), False
        while offset < len(data):
            if offset+12 > len(data):
                raise ValueError('truncated PNG chunk')
            size = struct.unpack('>I', data[offset:offset+4])[0]
            end = offset+12+size
            if end > len(data):
                raise ValueError('truncated PNG payload')
            kind = data[offset+4:offset+8]
            if kind == b'IHDR' and offset != 8:
                raise ValueError('duplicate PNG header')
            payload = data[offset+8:end-4]
            if zlib.crc32(kind+payload) != struct.unpack('>I', data[end-4:end])[0]:
                raise ValueError('PNG chunk CRC mismatch')
            if kind == b'IDAT':
                compressed.extend(payload)
            if kind == b'IEND':
                if size or end != len(data):
                    raise ValueError('invalid PNG terminator')
                ended = True
            offset = end
        expected = height*(width*(3 if header[25] == 2 else 4)+1)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, expected+1)
        if not ended or len(raw) != expected or not decoder.eof or decoder.unused_data:
            raise ValueError('incomplete or oversized PNG image data')
        if any(raw[index] > 4 for index in range(0, len(raw), expected//height)):
            raise ValueError('invalid PNG scanline filter')
        digest = hashlib.sha256(data).hexdigest()
    return {'path': str(path), 'sha256': digest, 'size': path.stat().st_size,
            'width': width, 'height': height}


class MobileObserver:
    """Fixed OSK-layer probe; no credential input or QMP power commands."""
    def __init__(self, directory, name, client_factory=QMP):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, exist_ok=False)
        self.name = name
        self.client_factory = client_factory
        self.client = None
        self.stage = 0
        self.next_at = 0
        self.pressed = False
        self.complete = False
        self.result = {'status': 'NOT RUN', 'scope': 'QMP captures and synthetic pointer delivery only',
                       'visual_semantics': 'NOT RUN: inspect screenshots separately',
                       'phone_touch': 'NOT RUN', 'profile': 'mobile', 'screenshots': [], 'actions': []}

    def input(self, events):
        self.client.execute('input-send-event', {'events': events})

    def move(self, x, y):
        if not (0 <= x < 540 and 0 <= y < 1224):
            raise ValueError('pointer coordinate outside portrait output')
        self.input([{'type': 'abs', 'data': {'axis': axis, 'value': round(value*32767/maximum)}}
                    for axis, value, maximum in [('x', x, 539), ('y', y, 1223)]])

    def button(self, down):
        # Mark before sending so a lost acknowledgement still attempts release.
        if down:
            self.pressed = True
        self.input([{'type': 'btn', 'data': {'button': 'left', 'down': down}}])
        if not down:
            self.pressed = False

    def capture(self, label):
        path = self.directory/(label+'.png')
        if path.exists():
            raise ValueError('refusing to overwrite screenshot')
        self.client.execute('screendump', {'filename': '/observe/'+path.name, 'format': 'png'})
        self.result['screenshots'].append(png_identity(path))
        if sum(row['size'] for row in self.result['screenshots']) > 8*1024*1024:
            raise ValueError('screenshot aggregate exceeds 8 MiB')

    def tick(self, now, ready):
        if self.complete or now < self.next_at:
            return
        if self.client is None:
            if not ready or not (self.directory/'qmp.sock').exists():
                return
            self.client = self.client_factory(self.directory/'qmp.sock', self.name)
            self.result['status'] = 'RUNNING'
        if self.stage == 0:
            self.capture('00-mobile-locked')
            self.move(500, 1218)
            self.button(True)
            self.result['actions'].append('drag keyboard activation strip upward')
            delay = .08
        elif 1 <= self.stage <= 4:
            self.move(500, [1180, 1140, 1100, 1060][self.stage-1])
            delay = .08
        elif self.stage == 5:
            self.button(False)
            delay = 1.2
        elif self.stage == 6:
            self.capture('01-keyboard-letters')
            self.move(50, 1173)
            self.button(True)
            self.result['actions'].append('click expected ?123 layer control')
            delay = .1
        elif self.stage == 7:
            self.button(False)
            delay = 1.2
        elif self.stage == 8:
            self.capture('02-keyboard-numbers')
            self.move(50, 1173)
            self.button(True)
            self.result['actions'].append('click expected ABC layer control')
            delay = .1
        elif self.stage == 9:
            self.button(False)
            delay = 1.2
        else:
            self.capture('03-keyboard-letters-restored')
            self.complete = True
            self.result['status'] = 'PASS'
            delay = 0
        self.stage += 1
        self.next_at = now+delay

    def finish(self, error=None):
        cleanup_error = None
        if self.client:
            try:
                if self.pressed:
                    self.button(False)
            except Exception as exception:
                cleanup_error = str(exception)
            finally:
                self.client.close()
                self.result['qmp'] = self.client.records
        if error or cleanup_error or not self.complete:
            self.result['status'] = 'FAIL'
            self.result['error'] = str(error or cleanup_error or 'guest ended before observation completed')
        self.result['pointer_released'] = not self.pressed
        if cleanup_error:
            self.result['cleanup_error'] = cleanup_error
        (self.directory/'result.json').write_text(json.dumps(self.result, indent=2)+'\n')
        return self.result
