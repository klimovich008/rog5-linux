#!/usr/bin/env python3
"""Bounded local capture and QMP input for one owned portrait mobile VM."""
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


def capture_vnc(socket_path, name, path, timeout=3):
    """Read one full raw frame from the owned UNIX-only QEMU VNC listener."""
    deadline = time.monotonic()+timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        def receive(count):
            if not 0 <= count <= 540*1224*4:
                raise ValueError('VNC read exceeds frame bound')
            result = bytearray()
            while len(result) < count:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('VNC capture deadline')
                client.settimeout(remaining)
                block = client.recv(min(65536, count-len(result)))
                if not block:
                    raise EOFError('VNC disconnected')
                result.extend(block)
            return bytes(result)

        def send(data):
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('VNC capture deadline')
            client.settimeout(remaining)
            client.sendall(data)

        client.settimeout(timeout)
        client.connect(str(socket_path))
        if receive(12) != b'RFB 003.008\n':
            raise ValueError('unsupported VNC version')
        send(b'RFB 003.008\n')
        count = receive(1)[0]
        if count != 1 or receive(count) != b'\x01':
            raise ValueError('unexpected private VNC security mode')
        send(b'\x01')
        if receive(4) != b'\0\0\0\0':
            raise ValueError('VNC security handshake failed')
        send(b'\x01')  # Shared observer, no input through VNC.
        header = receive(24)
        width, height = struct.unpack('>HH', header[:4])
        size = struct.unpack('>I', header[20:24])[0]
        if size > 4096 or receive(size) != ('QEMU ('+name+')').encode():
            raise ValueError('VNC does not identify the owned VM')
        if width not in (540, 544) or height != 1224:
            raise ValueError('unexpected VNC portrait dimensions')
        # QEMU pads its initial RFB width to16 pixels. DesktopSize reports
        # the true scanout extent; require it before accepting a padded frame.
        size_ready = width == 540
        width = 540
        # Request RGBx in wire order; only raw encoding, no clipboard or keys.
        pixel_format = struct.pack('>BBBBHHHBBB3x', 32, 24, 1, 1, 255, 255, 255, 24, 16, 8)
        send(b'\0\0\0\0'+pixel_format)
        send(struct.pack('>BBHii', 2, 0, 2, 0, -223))
        send(struct.pack('>BBHHHH', 3, 0, 0, 0, width, height))
        pixels = bytearray(width*height*4)
        covered = bytearray(width*height)
        resized = False
        for _ in range(4):
            if receive(1) != b'\0':
                raise ValueError('unexpected VNC server message')
            count = struct.unpack('>xH', receive(3))[0]
            if not 1 <= count <= 128:
                raise ValueError('VNC rectangle count outside bound')
            for _ in range(count):
                x, y, w, h, encoding = struct.unpack('>HHHHi', receive(12))
                if encoding == -223:
                    if resized or any(covered) or (x, y, w, h) != (0, 0, width, height):
                        raise ValueError('unexpected VNC desktop resize')
                    size_ready = resized = True
                    continue
                if (not size_ready or encoding != 0 or not w or not h
                        or x+w > width or y+h > height):
                    raise ValueError('unexpected VNC rectangle geometry or encoding')
                raw = receive(w*h*4)
                for row in range(h):
                    start = (y+row)*width+x
                    if any(covered[start:start+w]):
                        raise ValueError('overlapping VNC rectangles')
                    covered[start:start+w] = b'\x01'*w
                    pixels[start*4:(start+w)*4] = raw[row*w*4:(row+1)*w*4]
            if all(covered):
                break
        if not all(covered):
            raise ValueError('incomplete nonincremental VNC frame')
    # Encode the captured RGB pixels losslessly; no scaling or visual edits.
    rows = bytearray(height*(width*3+1))
    for y in range(height):
        start = y*(width*3+1)+1
        row = pixels[y*width*4:(y+1)*width*4]
        rows[start:start+width*3:3] = row[0::4]
        rows[start+1:start+width*3:3] = row[1::4]
        rows[start+2:start+width*3:3] = row[2::4]
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    png = (b'\x89PNG\r\n\x1a\n'
           +chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           +chunk(b'IDAT', zlib.compress(rows))+chunk(b'IEND', b''))
    with path.open('xb') as output:
        output.write(png)


class MobileObserver:
    """Fixed OSK-layer probe; no credential input or QMP power commands."""
    def __init__(self, directory, name, client_factory=QMP, capture_backend=None):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, exist_ok=False)
        self.name = name
        self.client_factory = client_factory
        self.capture_backend = capture_backend
        self.client = None
        self.stage = 0
        self.next_at = 0
        self.pressed = False
        self.complete = False
        self.result = {'status': 'NOT RUN', 'scope': 'Local VM captures and synthetic pointer delivery only',
                       'visual_semantics': 'NOT RUN: inspect screenshots separately',
                       'phone_touch': 'NOT RUN', 'profile': 'mobile',
                       'capture_backend': 'UNIX VNC raw' if capture_backend else 'QMP screendump', 'screenshots': [], 'actions': []}

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
        if self.capture_backend:
            self.capture_backend(self.directory/'vnc.sock', self.name, path)
        else:
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
        self.advance_stage = True
        delay = self.step()
        self.stage += int(self.advance_stage)
        self.next_at = now+delay

    def step(self):
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
        return delay

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


class LauncherObserver(MobileObserver):
    """Discover the unlocked launcher without guessing tile coordinates."""

    def step(self):
        self.result['probe'] = 'unlocked launcher discovery; no app input'
        self.result['app_launch_and_switch'] = 'NOT RUN'
        if self.stage == 0:
            self.capture('00-launcher-initial')
            return 5.0
        self.capture('01-launcher-settled')
        self.complete = True
        self.result['status'] = 'PASS'
        return 0


class EditorObserver(MobileObserver):
    """Fixed native-client text probe; only OSK pointer presses type text."""
    STEPS = [
        ('capture', '00-editor-empty', .1),
        ('move', (270, 200), .1), ('button', True, .1), ('button', False, .3),
        ('move', (500, 1218), .1), ('button', True, .1),
        *[('move', (500, y), .1) for y in (1180, 1140, 1100, 1060)],
        ('button', False, 1.2), ('capture', '01-editor-keyboard', .1),
        # The pinned mobile shell translates the app upward by the OSK height.
        # Pan its stationary18px right-edge strip to reveal the editor's top
        # line; preserve the unpanned capture as a separate observation.
        ('move', (531, 240), .1), ('button', True, .1),
        *[('move', (531, y), .1) for y in (320, 400, 480, 560, 640)],
        ('button', False, 1.2), ('capture', '01b-editor-viewport-panned', .1),
        *[step for point in ((243, 921), (137, 921), (111, 1005), (243, 921))
          for step in (('move', point, .1), ('button', True, .1), ('button', False, .3))],
        ('capture', '02-editor-test', .1),
        ('move', (501, 1089), .1), ('button', True, .1), ('button', False, 1.2),
        ('capture', '03-editor-tes', .1),
        ('move', (243, 921), .1), ('button', True, .1), ('button', False, 1.2),
        ('capture', '04-editor-test-restored', 0),
    ]

    def step(self):
        operation, value, delay = self.STEPS[self.stage]
        if operation == 'capture':
            self.capture(value)
        elif operation == 'move':
            self.move(*value)
        elif operation == 'button':
            self.button(value)
        else:
            raise ValueError('unknown fixed editor action')
        self.result['actions'].append({'operation': operation,
                                       'value': list(value) if isinstance(value, tuple) else value})
        self.result['probe'] = 'native Mousepad OSK text entry; normal unlocked VM startup'
        if self.stage == len(self.STEPS)-1:
            self.complete = True
            self.result['status'] = 'PASS'
        return delay


def launcher_tile_signatures(path):
    """Match inspected fixed tile regions in our own unfiltered RGB captures.

    This only recognizes the retained layout; it does not infer arbitrary app
    names or claim broader visual semantics from image equality.
    """
    png_identity(path)  # Validate CRC, dimensions, size and decompression bound.
    data = path.read_bytes()
    if data[25] != 2:
        raise ValueError('launcher reference must be capture-backend RGB')
    chunks = []
    offset = 8
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset+4])[0]
        if data[offset+4:offset+8] == b'IDAT':
            chunks.append(data[offset+8:offset+8+size])
        offset += 12+size
    raw = zlib.decompress(b''.join(chunks))
    stride = 540*3+1
    if any(raw[y*stride] != 0 for y in range(1224)):
        raise ValueError('launcher reference must use our unfiltered capture encoding')
    result = {}
    for app, rect in {'foot': (174, 562, 237, 622),
                      'mousepad': (45, 722, 107, 782)}.items():
        x0, y0, x1, y1 = rect
        tile = b''.join(raw[y*stride+1+x0*3:y*stride+1+x1*3] for y in range(y0, y1))
        result[app] = hashlib.sha256(tile).hexdigest()
    return result


class AppSwitchObserver(MobileObserver):
    """One owned native launch/switch sequence using inspected launcher tiles."""
    STEPS = [
        ('home', '00-home-ready'),
        ('click', (77, 752)),
        ('client', ('mousepad', '01-mousepad-launched')),
        ('gesture', ((270, 1194), (270, 1150), (270, 1060), (270, 970), (270, 880))),
        ('home', '02-home-returned'),
        ('click', (205, 592)),
        ('client', ('foot', '03-foot-launched')),
        ('gesture', ((270, 1194), (315, 1194), (365, 1194), (415, 1194))),
        ('client', ('mousepad', '04-mousepad-restored')),
        # Activation raises each app to the end of the snapshot's stacking
        # order. Both switches go to the preceding window with a right drag.
        ('gesture', ((270, 1194), (315, 1194), (365, 1194), (415, 1194))),
        ('client', ('foot', '05-foot-restored')),
    ]

    def __init__(self, *args, protocol, reference, sleep=time.sleep, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol = protocol
        self.reference = launcher_tile_signatures(reference)
        self.sleep = sleep
        self.probes = {}
        self.focus_count = 0
        self.result.update(probe='UI launch and switch native Mousepad and Foot',
                           launcher_reference=png_identity(reference),
                           launcher_tiles=self.reference)

    def step(self):
        operation, value = self.STEPS[self.stage]
        self.result['waiting_for'] = {'operation': operation, 'value': value}
        if operation == 'home':
            attempt = self.probes.get(self.stage, 0)+1
            if attempt > 8:
                raise TimeoutError('launcher tile readiness not observed')
            self.probes[self.stage] = attempt
            label = value+'-probe-'+str(attempt)
            self.capture(label)
            match = launcher_tile_signatures(self.directory/(label+'.png')) == self.reference
            self.result.setdefault('tile_checks', []).append({'capture': label, 'matched': match})
            if not match:
                self.advance_stage = False
                return 1.0
        elif operation == 'client':
            app, label = value
            if not (self.protocol.ready(app) and self.protocol.focused(app)
                    and len(self.protocol.focus_history) > self.focus_count):
                self.advance_stage = False
                return .2
            self.focus_count = len(self.protocol.focus_history)
            self.capture(label)
        elif operation == 'click':
            self.move(*value)
            self.button(True)
            self.sleep(.08)
            self.button(False)
        elif operation == 'gesture':
            self.move(*value[0])
            self.button(True)
            # Keep consecutive gesture samples inside the Flutter velocity
            # tracker's history. Ordinary 200ms host polling is too sparse.
            for point in value[1:]:
                self.sleep(.025)
                self.move(*point)
            self.sleep(.025)
            self.button(False)
        else:
            raise ValueError('unknown fixed application action')
        self.result['actions'].append({'operation': operation, 'value': value})
        if self.stage == len(self.STEPS)-1:
            self.complete = True
            self.result['status'] = 'PASS'
            self.result.pop('waiting_for', None)
        return .8
