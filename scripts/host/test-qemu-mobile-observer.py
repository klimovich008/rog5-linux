#!/usr/bin/env python3
"""Bounded real-QMP transport and production mobile-observer host fixtures."""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
import uuid
import zlib
from functools import lru_cache

SPEC = importlib.util.spec_from_file_location(
    'mobile_observer', Path(__file__).with_name('qemu-mobile-observer.py'))
MOBILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOBILE)


def png_chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack(
        '>I', zlib.crc32(kind + payload))


@lru_cache(maxsize=8)
def png_fixture(width=540, height=1224, extra=0):
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    pixels = b'\0' * (height * (width * 3 + 1) + extra)
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header)
            + png_chunk(b'IDAT', zlib.compress(pixels)) + png_chunk(b'IEND', b''))


class FakeQMP:
    """A local AF_UNIX peer; each socket operation and thread join is bounded."""
    def __init__(self, greeting=None, name='owned', reply=None):
        # Abstract AF_UNIX keeps long disk-backed TMPDIR names below sun_path's
        # limit without creating sockets in a shared filesystem directory.
        self.address = '\0rog5-qmp-test-' + str(os.getpid()) + '-' + uuid.uuid4().hex
        self.greeting = {'QMP': {'version': {}}} if greeting is None else greeting
        self.name, self.reply = name, reply
        self.requests, self.errors = [], []
        self.stop = threading.Event()
        self.peer = None
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(self.address)
        self.listener.listen(1)
        self.listener.settimeout(.5)
        self.thread = threading.Thread(target=self.serve, daemon=True)

    @staticmethod
    def send(peer, value):
        peer.sendall(json.dumps(value).encode() + b'\n')

    def serve(self):
        try:
            self.peer, _ = self.listener.accept()
            self.peer.settimeout(.5)
            self.send(self.peer, self.greeting)
            with self.peer.makefile('rb') as stream:
                while not self.stop.is_set():
                    line = stream.readline(65537)
                    if not line:
                        return
                    request = json.loads(line)
                    self.requests.append(request)
                    command = request['execute']
                    if command == 'query-name':
                        result = {'name': self.name}
                    elif command == 'query-status':
                        result = {'running': True}
                    else:
                        result = {}
                    if self.reply and self.reply(self, request):
                        continue
                    self.send(self.peer, {'return': result, 'id': request['id']})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except OSError as error:
            if not self.stop.is_set():
                self.errors.append(error)
        except BaseException as error:
            self.errors.append(error)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        if self.peer:
            with contextlib.suppress(OSError):
                self.peer.shutdown(socket.SHUT_RDWR)
            self.peer.close()
        self.listener.close()
        self.thread.join(1)
        if self.thread.is_alive():
            raise AssertionError('fake QMP peer exceeded cleanup deadline')
        if self.errors:
            raise AssertionError(self.errors)


class QMPTransport(unittest.TestCase):
    def test_greeting_and_exact_owned_name_are_required(self):
        for greeting, name, message in [({}, 'owned', 'greeting'),
                                        ({'QMP': {}}, 'another', 'owned VM')]:
            with self.subTest(message=message), FakeQMP(greeting, name) as server:
                with self.assertRaisesRegex(ValueError, message):
                    MOBILE.QMP(server.address, 'owned', timeout=.15)

    def test_running_status_is_required(self):
        def stopped(server, request):
            if request['execute'] == 'query-status':
                server.send(server.peer, {'return': {'running': False}, 'id': request['id']})
                return True
        with FakeQMP(reply=stopped) as server:
            with self.assertRaisesRegex(ValueError, 'not running'):
                MOBILE.QMP(server.address, 'owned', timeout=.15)

    def test_events_interleave_with_matching_response_ids(self):
        def events(server, request):
            server.send(server.peer, {'event': 'DISPLAY_CHANGED'})
        with FakeQMP(reply=events) as server:
            client = MOBILE.QMP(server.address, 'owned', timeout=.15)
            try:
                self.assertEqual(client.execute('screendump', {'filename': 'capture'}), {})
                self.assertEqual([r['request']['id'] for r in client.records], [1, 2, 3, 4])
                self.assertEqual([r['response']['id'] for r in client.records], [1, 2, 3, 4])
            finally:
                client.close()

    def test_wrong_response_id_is_rejected(self):
        def wrong(server, request):
            server.send(server.peer, {'return': {}, 'id': request['id'] + 1})
            return True
        with FakeQMP(reply=wrong) as server:
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                MOBILE.QMP(server.address, 'owned', timeout=.15)

    def test_error_and_missing_result_are_rejected(self):
        for response, exception in [({'error': {'class': 'GenericError'}}, RuntimeError),
                                     ({}, ValueError)]:
            def respond(server, request):
                server.send(server.peer, dict(response, id=request['id']))
                return True
            with self.subTest(response=response), FakeQMP(reply=respond) as server:
                with self.assertRaises(exception):
                    MOBILE.QMP(server.address, 'owned', timeout=.15)

    def test_disconnect_is_rejected(self):
        def disconnect(server, request):
            server.peer.shutdown(socket.SHUT_RDWR)
            return True
        with FakeQMP(reply=disconnect) as server:
            with self.assertRaises(EOFError):
                MOBILE.QMP(server.address, 'owned', timeout=.15)

    def test_response_size_is_bounded(self):
        def oversized(server, request):
            server.peer.sendall(b'x' * 65537)
            return True
        with FakeQMP(reply=oversized) as server:
            with self.assertRaisesRegex(ValueError, '64 KiB'):
                MOBILE.QMP(server.address, 'owned', timeout=.15)

    def test_silent_peer_has_deadline(self):
        def silent(server, request):
            server.stop.wait(.3)
            return True
        started = time.monotonic()
        with FakeQMP(reply=silent) as server:
            with self.assertRaises(TimeoutError):
                MOBILE.QMP(server.address, 'owned', timeout=.04)
        self.assertLess(time.monotonic() - started, 1)

    def test_combined_qmp_limit_remains_bounded_and_excludes_power(self):
        with FakeQMP() as server:
            client=MOBILE.TextQMP(server.address,'owned',timeout=.15)
            try:
                with self.assertRaisesRegex(ValueError,'outside bounded'):
                    client.execute('system_powerdown')
                for _ in range(93):client.execute('query-status')
                with self.assertRaisesRegex(ValueError,'outside bounded'):
                    client.execute('query-status')
                self.assertEqual(client.sequence,96)
                self.assertEqual(MOBILE.QMP.REQUEST_LIMIT,64)
            finally:client.close()

    def test_event_flood_and_command_budget_are_bounded(self):
        def flood(server, request):
            for _ in range(32):
                server.send(server.peer, {'event': 'NOISE'})
            return True
        with FakeQMP(reply=flood) as server:
            with self.assertRaisesRegex(ValueError, 'event stream'):
                MOBILE.QMP(server.address, 'owned', timeout=.15)
        with FakeQMP() as server:
            client = MOBILE.QMP(server.address, 'owned', timeout=.15)
            try:
                for command in ('quit', 'system_reset', 'human-monitor-command'):
                    with self.assertRaises(ValueError):
                        client.execute(command)
                client.sequence = 64
                with self.assertRaises(ValueError):
                    client.execute('query-status')
                self.assertEqual(len(client.records), 3)
            finally:
                client.close()


class CaptureClient:
    def __init__(self, directory, fail_capture=None, fail_down=False, fail_up=False):
        self.directory = directory
        self.fail_capture, self.fail_down, self.fail_up = fail_capture, fail_down, fail_up
        self.records, self.buttons = [], []
        self.closed = False
        self.capture_count = 0

    def execute(self, command, arguments):
        self.records.append({'command': command, 'arguments': arguments})
        if command == 'screendump':
            self.capture_count += 1
            if self.capture_count == self.fail_capture:
                raise RuntimeError('capture rejected')
            path = self.directory / Path(arguments['filename']).name
            path.write_bytes(png_fixture())
        elif command == 'input-send-event':
            for event in arguments['events']:
                if event['type'] == 'btn':
                    down = event['data']['down']
                    self.buttons.append(down)
                    if (down and self.fail_down) or (not down and self.fail_up):
                        raise RuntimeError('button acknowledgement lost')
        return {}

    def close(self):
        self.closed = True


class MobileObservation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qmp-observer-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'observe'
        self.client = CaptureClient(self.directory)
        self.observer = MOBILE.MobileObserver(self.directory, 'owned',
            client_factory=lambda path, name: self.client)
        (self.directory / 'qmp.sock').touch()

    def advance(self, count=11):
        for _ in range(count):
            self.observer.tick(self.observer.next_at, True)

    def test_fixed_steps_capture_four_images_and_release_every_press(self):
        self.observer.tick(0, False)
        self.assertEqual(self.client.records, [])
        self.advance()
        result = self.observer.finish()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.client.buttons, [True, False] * 3)
        self.assertTrue(result['pointer_released'])
        self.assertTrue(self.client.closed)
        self.assertEqual(len(result['actions']), 3)
        self.assertEqual([Path(row['path']).name for row in result['screenshots']], [
            '00-mobile-locked.png', '01-keyboard-letters.png',
            '02-keyboard-numbers.png', '03-keyboard-letters-restored.png'])
        for row in result['screenshots']:
            self.assertEqual(row['sha256'], hashlib.sha256(png_fixture()).hexdigest())
        self.assertEqual(result['phone_touch'], 'NOT RUN')
        self.assertIn('NOT RUN', result['visual_semantics'])
        moves = [event['data'] for row in self.client.records
                 if row['command'] == 'input-send-event'
                 for event in row['arguments']['events'] if event['type'] == 'abs']
        self.assertEqual(len(moves), 14)
        self.assertTrue(all(0 <= event['value'] <= 32767 for event in moves))
        self.assertEqual(json.loads((self.directory / 'result.json').read_text()), result)

    def test_ticks_respect_ready_socket_and_deadline(self):
        (self.directory / 'qmp.sock').unlink()
        self.observer.tick(0, True)
        self.assertIsNone(self.observer.client)
        (self.directory / 'qmp.sock').touch()
        self.observer.tick(0, True)
        records = len(self.client.records)
        self.observer.tick(.01, True)
        self.assertEqual(len(self.client.records), records)
        self.observer.finish('interrupted')

    def test_interruption_at_every_stage_balances_pointer(self):
        for count in range(12):
            with self.subTest(count=count):
                directory = Path(self.temp.name) / str(count)
                client = CaptureClient(directory)
                observer = MOBILE.MobileObserver(directory, 'owned',
                    client_factory=lambda path, name: client)
                (directory / 'qmp.sock').touch()
                for _ in range(count):
                    observer.tick(observer.next_at, True)
                result = observer.finish('interrupted')
                self.assertEqual(result['status'], 'FAIL')
                self.assertTrue(result['pointer_released'])
                self.assertEqual(client.buttons, [True, False] * (len(client.buttons) // 2))
                if count:
                    self.assertTrue(client.closed)

    def test_lost_press_acknowledgement_still_releases(self):
        self.client.fail_down = True
        with self.assertRaisesRegex(RuntimeError, 'acknowledgement') as caught:
            self.advance(1)
        result = self.observer.finish(caught.exception)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(self.client.buttons, [True, False])
        self.assertTrue(result['pointer_released'])

    def test_failed_release_is_explicit_failure(self):
        self.advance(1)
        self.client.fail_up = True
        result = self.observer.finish('interrupted')
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['pointer_released'])
        self.assertIn('acknowledgement', result['cleanup_error'])
        self.assertTrue(self.client.closed)

    def test_failed_capture_cannot_pass(self):
        for failed in range(1, 5):
            with self.subTest(failed=failed):
                directory = Path(self.temp.name) / ('failure-' + str(failed))
                client = CaptureClient(directory, fail_capture=failed)
                observer = MOBILE.MobileObserver(directory, 'owned',
                    client_factory=lambda path, name: client)
                (directory / 'qmp.sock').touch()
                with self.assertRaisesRegex(RuntimeError, 'capture rejected') as caught:
                    for _ in range(11):
                        observer.tick(observer.next_at, True)
                result = observer.finish(caught.exception)
                self.assertEqual(result['status'], 'FAIL')
                self.assertFalse(observer.complete)
                self.assertEqual(len(result['screenshots']), failed - 1)
                self.assertTrue(result['pointer_released'])

    def test_existing_output_and_capture_are_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            MOBILE.MobileObserver(self.directory, 'owned')
        retained = self.directory / '00-mobile-locked.png'
        retained.write_bytes(b'retained')
        with self.assertRaisesRegex(ValueError, 'overwrite') as caught:
            self.advance(1)
        self.assertEqual(retained.read_bytes(), b'retained')
        self.assertFalse(any(row['command'] == 'screendump' for row in self.client.records))
        self.assertEqual(self.observer.finish(caught.exception)['status'], 'FAIL')

    def test_invalid_dimensions_format_symlinks_and_size_fail(self):
        path = self.directory / 'image.png'
        for content in (b'bad', png_fixture(0, 1224), png_fixture(1224, 540)):
            path.write_bytes(content)
            with self.assertRaises(ValueError):
                MOBILE.png_identity(path)
        path.write_bytes(png_fixture())
        link = self.directory / 'link.png'
        link.symlink_to(path)
        with self.assertRaises(ValueError):
            MOBILE.png_identity(link)
        with path.open('r+b') as stream:
            stream.truncate(4 * 1024 * 1024 + 1)
        with self.assertRaises(ValueError):
            MOBILE.png_identity(path)

    def test_truncated_crc_corrupt_and_oversized_decoding_fail(self):
        path = self.directory / 'broken.png'
        valid = png_fixture()
        for content in (valid[:-1], valid[:33], valid[:30] + bytes([valid[30] ^ 1]) + valid[31:],
                        png_fixture(extra=1), valid + b'trailing'):
            path.write_bytes(content)
            with self.assertRaises(ValueError):
                MOBILE.png_identity(path)

    def test_invalid_pointer_coordinates_emit_no_input(self):
        self.observer.client = self.client
        for x, y in ((-1, 0), (0, -1), (540, 0), (0, 1224)):
            with self.assertRaises(ValueError):
                self.observer.move(x, y)
        self.assertEqual(self.client.records, [])
        self.observer.finish('test complete')


class LauncherObservation(unittest.TestCase):
    def test_discovery_waits_then_captures_without_input_or_launch_claim(self):
        with tempfile.TemporaryDirectory(prefix='qmp-launcher-') as temp:
            directory = Path(temp) / 'observe'
            client = CaptureClient(directory)
            observer = MOBILE.LauncherObserver(directory, 'owned',
                client_factory=lambda path, name: client)
            (directory / 'qmp.sock').touch()
            observer.tick(0, False)
            self.assertEqual(client.records, [])
            observer.tick(0, True)
            observer.tick(4.9, True)
            self.assertFalse(observer.complete)
            observer.tick(5, True)
            result = observer.finish()
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['app_launch_and_switch'], 'NOT RUN')
            self.assertIn('NOT RUN', result['visual_semantics'])
            self.assertEqual([Path(x['path']).name for x in result['screenshots']],
                ['00-launcher-initial.png', '01-launcher-settled.png'])
            self.assertTrue(all(x['command'] == 'screendump' for x in client.records))
            self.assertTrue(client.closed)

    def test_incomplete_or_failed_discovery_cannot_pass(self):
        for failed in (None, 1, 2):
            with tempfile.TemporaryDirectory(prefix='qmp-launcher-') as temp:
                directory = Path(temp) / 'observe'
                client = CaptureClient(directory, fail_capture=failed)
                observer = MOBILE.LauncherObserver(directory, 'owned',
                    client_factory=lambda path, name: client)
                (directory / 'qmp.sock').touch()
                error = None
                try:
                    observer.tick(0, True)
                    if failed:
                        observer.tick(5, True)
                except RuntimeError as caught:
                    error = caught
                self.assertEqual(observer.finish(error)['status'], 'FAIL')
                self.assertEqual(client.buttons, [])
                self.assertTrue(client.closed)


class EditorObservation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='qmp-editor-')
        self.addCleanup(self.temp.cleanup)

    def observer(self, label, **client_options):
        directory = Path(self.temp.name) / label
        client = CaptureClient(directory, **client_options)
        observer = MOBILE.EditorObserver(directory, 'owned',
            client_factory=lambda path, name: client)
        (directory / 'qmp.sock').touch()
        return observer, client

    @staticmethod
    def advance(observer, count):
        for _ in range(count):
            observer.tick(observer.next_at, True)

    def test_editor_pointer_route_and_capture_order_are_bounded(self):
        observer, client = self.observer('complete')
        self.advance(observer, 42)
        self.assertTrue(observer.complete)
        result = observer.finish()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(client.buttons, [True, False] * 9)
        self.assertTrue(result['pointer_released'])
        self.assertTrue(client.closed)
        self.assertEqual(len(result['actions']), 42)
        self.assertEqual([Path(row['path']).name for row in result['screenshots']], [
            '00-editor-empty.png', '01-editor-keyboard.png', '01b-editor-viewport-panned.png', '02-editor-test.png',
            '03-editor-tes.png', '04-editor-test-restored.png'])
        # Decode the emitted QMP stream, independently of the STEPS table.
        # Every press must target the editor, reveal strip or the four intended
        # OSK controls. The fixture never sends a key, text or credential event.
        pointer = {}
        presses = []
        pan_points = []
        for row in client.records:
            self.assertIn(row['command'], ('screendump', 'input-send-event'))
            if row['command'] == 'screendump':
                continue
            for event in row['arguments']['events']:
                self.assertIn(event['type'], ('abs', 'btn'))
                if event['type'] == 'abs':
                    axis, value = event['data']['axis'], event['data']['value']
                    self.assertIn(axis, ('x', 'y'))
                    self.assertGreaterEqual(value, 0)
                    self.assertLessEqual(value, 32767)
                    pointer[axis] = round(value * (539 if axis == 'x' else 1223) / 32767)
                    if axis == 'y' and pointer.get('x') == 531:
                        pan_points.append((531, pointer['y']))
                else:
                    self.assertEqual(set(event['data']), {'button', 'down'})
                    self.assertEqual(event['data']['button'], 'left')
                    if event['data']['down']:
                        presses.append((pointer['x'], pointer['y']))
        self.assertEqual(presses, [(270, 200), (500, 1218), (531, 240), (243, 921),
                                  (137, 921), (111, 1005), (243, 921),
                                  (501, 1089), (243, 921)])
        self.assertEqual(pan_points, [(531, y) for y in (240, 320, 400, 480, 560, 640)])
        self.assertIn('NOT RUN', result['visual_semantics'])
        self.assertEqual(result['phone_touch'], 'NOT RUN')
        self.assertEqual(json.loads((observer.directory / 'result.json').read_text()), result)
        records = len(client.records)
        observer.tick(observer.next_at + 1, True)
        self.assertEqual(len(client.records), records)

    def test_editor_ready_socket_and_clock_gate_all_actions(self):
        observer, client = self.observer('gated')
        observer.tick(0, False)
        self.assertEqual(client.records, [])
        (observer.directory / 'qmp.sock').unlink()
        observer.tick(0, True)
        self.assertEqual(client.records, [])
        (observer.directory / 'qmp.sock').touch()
        observer.tick(0, True)
        self.assertEqual(observer.stage, 1)
        records = len(client.records)
        observer.tick(observer.next_at / 2, True)
        self.assertEqual(observer.stage, 1)
        self.assertEqual(len(client.records), records)
        self.assertEqual(observer.finish()['status'], 'FAIL')

    def test_editor_interruption_at_every_stage_releases_pointer(self):
        for count in range(43):
            with self.subTest(count=count):
                observer, client = self.observer('interrupted-' + str(count))
                self.advance(observer, count)
                result = observer.finish('interrupted')
                self.assertEqual(result['status'], 'FAIL')
                self.assertTrue(result['pointer_released'])
                self.assertEqual(client.buttons, [True, False] * (len(client.buttons) // 2))
                self.assertEqual(client.closed, count > 0)

    def test_editor_incomplete_run_cannot_pass_without_explicit_error(self):
        for count in (0, 3, 6, 14, 19, 33, 37, 41):
            with self.subTest(count=count):
                observer, client = self.observer('incomplete-' + str(count))
                self.advance(observer, count)
                result = observer.finish()
                self.assertEqual(result['status'], 'FAIL')
                self.assertTrue(result['pointer_released'])
                self.assertFalse(observer.complete)

    def test_editor_each_capture_failure_cannot_pass(self):
        for failed in range(1, 7):
            with self.subTest(failed=failed):
                observer, client = self.observer('capture-' + str(failed), fail_capture=failed)
                with self.assertRaisesRegex(RuntimeError, 'capture rejected') as caught:
                    self.advance(observer, 42)
                result = observer.finish(caught.exception)
                self.assertEqual(result['status'], 'FAIL')
                self.assertFalse(observer.complete)
                self.assertEqual(len(result['screenshots']), failed - 1)
                self.assertTrue(result['pointer_released'])
                self.assertTrue(client.closed)

    def test_editor_lost_press_ack_releases_and_failed_release_is_recorded(self):
        for fail_up in (False, True):
            with self.subTest(fail_up=fail_up):
                observer, client = self.observer('lost-ack-' + str(fail_up),
                    fail_down=True, fail_up=fail_up)
                with self.assertRaisesRegex(RuntimeError, 'acknowledgement') as caught:
                    self.advance(observer, 3)
                result = observer.finish(caught.exception)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(client.buttons, [True, False])
                self.assertEqual(result['pointer_released'], not fail_up)
                self.assertEqual('cleanup_error' in result, fail_up)
                self.assertTrue(client.closed)


class VNCCapture(unittest.TestCase):
    class FakeRFB:
        """One real UNIX peer with bounded I/O, explicit wire checks and cleanup."""
        def __init__(self, overrides=None, rectangles=None, eof=None, silent=None,
                     delay=0, initial_width=540, updates=None):
            self.address = '\0rog5-rfb-test-' + uuid.uuid4().hex
            self.overrides = overrides or {}
            self.rectangles = rectangles if rectangles is not None else [
                (0, 612, 540, 612, 0, b'\x91\x62\x33\xee' * (540 * 612)),
                (0, 0, 540, 612, 0, b'\x12\x34\x56\xaa' * (540 * 612))]
            self.eof, self.silent, self.delay = eof, silent, delay
            self.initial_width = initial_width
            self.updates = updates
            self.requests, self.errors = [], []
            self.stop = threading.Event()
            self.peer = None
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.bind(self.address)
            self.listener.listen(1)
            self.listener.settimeout(.75)
            self.thread = threading.Thread(target=self.serve, daemon=True)

        def send(self, stage, payload):
            if self.delay and self.stop.wait(self.delay):
                raise EOFError('fixture stopped')
            if self.silent == stage:
                self.stop.wait(.75)
                raise EOFError('silent fixture finished')
            payload = self.overrides.get(stage, payload)
            if self.eof == stage:
                self.peer.sendall(payload[:-1])
                raise EOFError('intentional truncated frame')
            self.peer.sendall(payload)

        def expect(self, label, expected):
            received = bytearray()
            while len(received) < len(expected):
                block = self.peer.recv(len(expected) - len(received))
                if not block:
                    raise EOFError('client closed')
                received.extend(block)
            if received != expected:
                raise AssertionError((label, bytes(received), expected))
            self.requests.append(label)

        def serve(self):
            try:
                self.peer, _ = self.listener.accept()
                self.peer.settimeout(.75)
                self.send('version', b'RFB 003.008\n')
                self.expect('version', b'RFB 003.008\n')
                self.send('security', b'\x01\x01')
                self.expect('security', b'\x01')
                self.send('security-result', b'\0' * 4)
                self.expect('shared', b'\x01')
                name = b'QEMU (owned)'
                # ServerInit format differs deliberately from the requested one.
                initial = struct.pack('>BBBBHHHBBB3x',
                                      16, 16, 0, 1, 31, 63, 31, 11, 5, 0)
                self.send('init', struct.pack('>HH', self.initial_width, 1224) + initial
                          + struct.pack('>I', len(name)))
                self.send('name', name)
                self.expect('pixel-format', b'\0' * 4 + struct.pack(
                    '>BBBBHHHBBB3x', 32, 24, 1, 1, 255, 255, 255, 24, 16, 8))
                self.expect('raw-encoding-and-size', struct.pack('>BBHii', 2, 0, 2, 0, -223))
                self.expect('full-frame', struct.pack('>BBHHHH', 3, 0, 0, 0, 540, 1224))
                updates = self.updates if self.updates is not None else [self.rectangles]
                for rectangles in updates:
                    self.send('update', struct.pack('>BBH', 0, 0, len(rectangles)))
                    for x, y, width, height, encoding, raw in rectangles:
                        self.send('rectangle', struct.pack('>HHHHi', x, y, width, height, encoding))
                        self.send('pixels', raw)
            except (BrokenPipeError, ConnectionResetError, EOFError):
                pass  # Expected when a deliberately invalid peer is refused.
            except BaseException as error:
                if not self.stop.is_set():
                    self.errors.append(error)
            finally:
                if self.peer:
                    self.peer.close()

        def __enter__(self):
            self.thread.start()
            return self

        def __exit__(self, *_):
            self.stop.set()
            if self.peer:
                with contextlib.suppress(OSError):
                    self.peer.shutdown(socket.SHUT_RDWR)
            self.listener.close()
            self.thread.join(1)
            if self.thread.is_alive():
                raise AssertionError('fake RFB peer exceeded cleanup deadline')
            if self.errors:
                raise AssertionError(self.errors)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='vnc-capture-')
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'capture.png'

    def reject(self, message, **peer_options):
        with self.FakeRFB(**peer_options) as peer:
            with self.assertRaisesRegex(ValueError, message):
                MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.5)
        self.assertFalse(self.path.exists())

    def test_real_handshake_requests_and_captured_rgb_pixels(self):
        with self.FakeRFB() as peer:
            MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.5)
        self.assertEqual(peer.requests, ['version', 'security', 'shared',
                                        'pixel-format', 'raw-encoding-and-size', 'full-frame'])
        self.check_captured_pixels()

    def check_captured_pixels(self):
        identity = MOBILE.png_identity(self.path)
        self.assertEqual((identity['width'], identity['height']), (540, 1224))
        data, offset, compressed = self.path.read_bytes(), 8, bytearray()
        while offset < len(data):
            size = struct.unpack('>I', data[offset:offset + 4])[0]
            if data[offset + 4:offset + 8] == b'IDAT':
                compressed.extend(data[offset + 8:offset + 8 + size])
            offset += size + 12
        self.assertEqual(zlib.decompress(compressed),
                         (b'\0' + b'\x12\x34\x56' * 540) * 612
                         + (b'\0' + b'\x91\x62\x33' * 540) * 612)

    def test_padded_width_requires_exact_resize_before_captured_pixels(self):
        resize = (0, 0, 540, 1224, -223, b'')
        for separate_update in (False, True):
            with self.subTest(separate_update=separate_update):
                with self.FakeRFB(initial_width=544) as peer:
                    peer.updates = ([[resize], peer.rectangles] if separate_update
                                    else [[resize] + peer.rectangles])
                    MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.5)
                self.check_captured_pixels()
                self.path.unlink()
        self.reject('geometry or encoding', initial_width=544)

    def test_invalid_duplicate_and_late_resize_are_rejected(self):
        for x, y, width, height in ((0, 0, 544, 1224), (1, 0, 540, 1224),
                                   (0, 0, 540, 1223), (0, 0, 1, 1)):
            with self.subTest(geometry=(x, y, width, height)):
                self.reject('desktop resize', initial_width=544,
                            rectangles=[(x, y, width, height, -223, b'')])
        resize = (0, 0, 540, 1224, -223, b'')
        self.reject('desktop resize', rectangles=[resize, resize])
        self.reject('desktop resize', rectangles=[(0, 0, 1, 1, 0, bytes(4)), resize])

    def test_unsupported_and_malformed_versions_are_rejected(self):
        for version in (b'RFB 003.003\n', b'RFB 003.009\n', b'BAD 003.008\n'):
            with self.subTest(version=version):
                self.reject('version', overrides={'version': version})

    def test_security_mode_and_failed_handshake_are_rejected(self):
        for security in (b'\0', b'\x01\x02', b'\x02\x01\x02'):
            with self.subTest(security=security):
                self.reject('security mode', overrides={'security': security})
        self.reject('handshake failed', overrides={'security-result': b'\0\0\0\x01'})

    def test_wrong_name_and_oversized_name_are_rejected(self):
        self.reject('owned VM', overrides={'name': b'QEMU (other)'})
        self.reject('owned VM', overrides={
            'init': struct.pack('>HH', 540, 1224) + bytes(16) + struct.pack('>I', 4097)})

    def test_wrong_dimensions_are_rejected(self):
        for width, height in ((0, 1224), (1224, 540), (540, 1223), (65535, 65535)):
            with self.subTest(width=width, height=height):
                self.reject('dimensions', overrides={
                    'init': struct.pack('>HH', width, height) + bytes(16)
                    + struct.pack('>I', len(b'QEMU (owned)'))})

    def test_message_type_and_rectangle_count_are_bounded(self):
        self.reject('server message', overrides={'update': b'\x02\0\0\x01'})
        for count in (0, 129, 65535):
            with self.subTest(count=count):
                self.reject('rectangle count', overrides={
                    'update': struct.pack('>BBH', 0, 0, count)})

    def test_encoding_and_rectangle_geometry_are_rejected(self):
        for geometry in ((0, 0, 1, 1, 1), (0, 0, 1, 1, -224),
                         (0, 0, 0, 1, 0), (0, 0, 1, 0, 0),
                         (540, 0, 1, 1, 0), (0, 1224, 1, 1, 0),
                         (539, 0, 2, 1, 0), (0, 1223, 1, 2, 0)):
            with self.subTest(geometry=geometry):
                self.reject('geometry or encoding', rectangles=[(*geometry, b'')])

    def test_partial_frame_and_overlapping_rectangles_are_rejected(self):
        self.reject('incomplete', updates=[[(x, 0, 1, 1, 0, bytes(4))] for x in range(4)])
        self.reject('overlapping', rectangles=[(0, 0, 1, 1, 0, bytes(4))] * 2)

    def test_truncated_handshake_and_frame_are_rejected_without_output(self):
        for stage in ('version', 'security', 'security-result', 'init', 'name',
                      'update', 'rectangle', 'pixels'):
            with self.subTest(stage=stage), self.FakeRFB(eof=stage) as peer:
                with self.assertRaises(EOFError):
                    MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.5)
                self.assertFalse(self.path.exists())

    def test_silent_peer_is_bounded(self):
        for stage in ('version', 'pixels'):
            started = time.monotonic()
            with self.subTest(stage=stage), self.FakeRFB(silent=stage) as peer:
                with self.assertRaises(TimeoutError):
                    MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.05)
            self.assertLess(time.monotonic() - started, 1)
            self.assertFalse(self.path.exists())

    def test_deadline_is_shared_across_protocol_reads(self):
        started = time.monotonic()
        with self.FakeRFB(delay=.025) as peer:
            with self.assertRaises(TimeoutError):
                MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.09)
        self.assertLess(time.monotonic() - started, .5)
        self.assertFalse(self.path.exists())

    def test_existing_file_and_symlink_are_not_overwritten(self):
        retained = self.path.with_name('retained')
        retained.write_bytes(b'original evidence')
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                if symlink:
                    self.path.symlink_to(retained)
                else:
                    self.path.write_bytes(b'original evidence')
                with self.FakeRFB() as peer:
                    with self.assertRaises(FileExistsError):
                        MOBILE.capture_vnc(peer.address, 'owned', self.path, timeout=.5)
                self.assertEqual(self.path.read_bytes(), b'original evidence')
                self.assertEqual(retained.read_bytes(), b'original evidence')
                self.assertEqual(self.path.is_symlink(), symlink)
                self.path.unlink()

    def test_observer_uses_owned_vnc_backend_and_validates_capture(self):
        for valid in (True, False):
            with self.subTest(valid=valid):
                directory = self.path.parent / ('observe-' + str(valid))
                client = CaptureClient(directory)
                calls = []

                def capture(socket_path, name, output):
                    calls.append((socket_path, name, output))
                    output.write_bytes(png_fixture() if valid else b'invalid PNG')

                observer = MOBILE.MobileObserver(directory, 'owned',
                    client_factory=lambda path, name: client, capture_backend=capture)
                (directory / 'qmp.sock').touch()
                try:
                    if valid:
                        observer.tick(0, True)
                        self.assertEqual(len(observer.result['screenshots']), 1)
                        self.assertEqual(observer.result['screenshots'][0],
                                         MOBILE.png_identity(directory / '00-mobile-locked.png'))
                    else:
                        with self.assertRaisesRegex(ValueError, 'not PNG'):
                            observer.tick(0, True)
                        self.assertEqual(observer.result['screenshots'], [])
                    self.assertEqual(calls, [(directory / 'vnc.sock', 'owned',
                                             directory / '00-mobile-locked.png')])
                    self.assertFalse(any(record['command'] == 'screendump'
                                         for record in client.records))
                finally:
                    observer.finish('fixture complete')


class AppSwitchObservation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='qmp-apps-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.reference = self.root/'reference.png'
        self.reference.write_bytes(png_fixture())

    def observer(self, label='observe', **options):
        class Protocol:
            focus_history = []
            app = None
            mapped = False
            def ready(self, app): return self.mapped and self.app == app
            def focused(self, app): return self.app == app
        protocol = Protocol()
        directory = self.root/label
        observer_class = options.pop('observer_class', MOBILE.AppSwitchObserver)
        client = CaptureClient(directory, **options)
        sleeps = []
        observer = observer_class(directory, 'owned', protocol=protocol,
            reference=self.reference, sleep=sleeps.append,
            client_factory=lambda path, name: client)
        (directory/'qmp.sock').touch()
        return observer, client, protocol, sleeps

    @staticmethod
    def focus(protocol, app):
        protocol.focus_history = [*protocol.focus_history, app]
        protocol.app, protocol.mapped = app, True

    def advance(self, observer, protocol):
        if observer.STEPS[observer.stage][0] == 'client':
            self.focus(protocol, observer.STEPS[observer.stage][1][0])
            stage = observer.stage
            while observer.stage == stage:
                observer.tick(observer.next_at, True)
        else:
            observer.tick(observer.next_at, True)

    def test_combined_flow_reuses_editor_actions_between_return_and_final_switch(self):
        observer, client, protocol, sleeps = self.observer(observer_class=MOBILE.AppTextObserver)
        while not observer.complete:
            self.advance(observer, protocol)
        result=observer.finish()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(protocol.focus_history,['mousepad','foot','mousepad','foot'])
        self.assertEqual(client.buttons,[True,False]*17)
        names=[Path(row['path']).stem for row in result['screenshots']]
        self.assertLess(names.index('04-mousepad-restored'),names.index('02-editor-test'))
        self.assertLess(names.index('04-editor-test-restored'),names.index('05-foot-restored'))
        self.assertEqual(result['qmp_request_limit'],96)
        self.assertLess(len(client.records),96)
        self.assertTrue(result['pointer_released'])
        self.assertIn('NOT RUN',result['visual_semantics'])

    def test_qualified_default_action_sequence_is_unchanged(self):
        expected_editor = [('capture', '00-editor-empty', 0.1),
         ('move', (270, 200), 0.1),
         ('button', True, 0.1),
         ('button', False, 0.3),
         ('move', (500, 1218), 0.1),
         ('button', True, 0.1),
         ('move', (500, 1180), 0.1),
         ('move', (500, 1140), 0.1),
         ('move', (500, 1100), 0.1),
         ('move', (500, 1060), 0.1),
         ('button', False, 1.2),
         ('capture', '01-editor-keyboard', 0.1),
         ('move', (531, 240), 0.1),
         ('button', True, 0.1),
         ('move', (531, 320), 0.1),
         ('move', (531, 400), 0.1),
         ('move', (531, 480), 0.1),
         ('move', (531, 560), 0.1),
         ('move', (531, 640), 0.1),
         ('button', False, 1.2),
         ('capture', '01b-editor-viewport-panned', 0.1),
         ('move', (243, 921), 0.1),
         ('button', True, 0.1),
         ('button', False, 0.3),
         ('move', (137, 921), 0.1),
         ('button', True, 0.1),
         ('button', False, 0.3),
         ('move', (111, 1005), 0.1),
         ('button', True, 0.1),
         ('button', False, 0.3),
         ('move', (243, 921), 0.1),
         ('button', True, 0.1),
         ('button', False, 0.3),
         ('capture', '02-editor-test', 0.1),
         ('move', (501, 1089), 0.1),
         ('button', True, 0.1),
         ('button', False, 1.2),
         ('capture', '03-editor-tes', 0.1),
         ('move', (243, 921), 0.1),
         ('button', True, 0.1),
         ('button', False, 1.2),
         ('capture', '04-editor-test-restored', 0)]
        expected_apps = [('home', '00-home-ready'),
         ('click', (77, 752)),
         ('client', ('mousepad', '01-mousepad-launched')),
         ('home_gesture', ((270, 1194), (270, 1150), (270, 1060), (270, 970), (270, 880))),
         ('capture', '02-overview-or-home'),
         ('click', (25, 1080)),
         ('home', '02-home-returned'),
         ('click', (205, 592)),
         ('client', ('foot', '03-foot-launched')),
         ('gesture', ((270, 1194), (315, 1194), (365, 1194), (415, 1194))),
         ('client', ('mousepad', '04-mousepad-restored')),
         ('editor', 0),
         ('editor', 1),
         ('editor', 2),
         ('editor', 3),
         ('editor', 4),
         ('editor', 5),
         ('editor', 6),
         ('editor', 7),
         ('editor', 8),
         ('editor', 9),
         ('editor', 10),
         ('editor', 11),
         ('editor', 12),
         ('editor', 13),
         ('editor', 14),
         ('editor', 15),
         ('editor', 16),
         ('editor', 17),
         ('editor', 18),
         ('editor', 19),
         ('editor', 20),
         ('editor', 21),
         ('editor', 22),
         ('editor', 23),
         ('editor', 24),
         ('editor', 25),
         ('editor', 26),
         ('editor', 27),
         ('editor', 28),
         ('editor', 29),
         ('editor', 30),
         ('editor', 31),
         ('editor', 32),
         ('editor', 33),
         ('editor', 34),
         ('editor', 35),
         ('editor', 36),
         ('editor', 37),
         ('editor', 38),
         ('editor', 39),
         ('editor', 40),
         ('editor', 41),
         ('home_gesture', ((531, 640), (531, 560), (531, 480), (531, 400), (531, 320), (531, 240))),
         ('home_gesture',
          ((270, 868), (270, 898), (270, 958), (270, 1018), (270, 1078), (270, 1138), (270, 1198))),
         ('capture', '04b-editor-keyboard-dismissed'),
         ('gesture', ((270, 1194), (315, 1194), (365, 1194), (415, 1194))),
         ('client', ('foot', '05-foot-restored'))]
        self.assertEqual(MOBILE.EditorObserver.STEPS, expected_editor)
        self.assertEqual(MOBILE.AppTextObserver.STEPS, expected_apps)

    def test_automatic_caret_flow_omits_only_pan_and_inverse(self):
        default, _, _, _ = self.observer(label='default', observer_class=MOBILE.AppTextObserver)
        automatic, client, protocol, _ = self.observer(observer_class=MOBILE.AutomaticCaretAppTextObserver)
        while not automatic.complete:
            self.advance(automatic, protocol)
        result = automatic.finish()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(protocol.focus_history, ['mousepad', 'foot', 'mousepad', 'foot'])
        self.assertEqual(client.buttons, [True, False]*15)
        self.assertEqual(result['action_policy'], 'automatic caret; no manual viewport pan; manual keyboard reveal')
        self.assertEqual(automatic.EDITOR_STEPS, [
            *MOBILE.EditorObserver.OPENING_STEPS, *MOBILE.EditorObserver.TEXT_STEPS])
        self.assertEqual(default.EDITOR_STEPS, [
            *MOBILE.EditorObserver.OPENING_STEPS, *MOBILE.EditorObserver.VIEWPORT_PAN_STEPS,
            *MOBILE.EditorObserver.TEXT_STEPS])
        self.assertFalse(any(row['operation'] == 'move' and row['value'][0] == 531
                             for row in result['actions']))
        names = [Path(row['path']).stem for row in result['screenshots']]
        self.assertNotIn('01b-editor-viewport-panned', names)
        for name in ('01-editor-keyboard', '02-editor-test', '03-editor-tes',
                     '04-editor-test-restored', '04b-editor-keyboard-dismissed'):
            self.assertIn(name, names)
        self.assertTrue(result['pointer_released'])
        self.assertIn('NOT RUN', result['visual_semantics'])

    def test_combined_editor_refuses_input_after_lost_native_focus(self):
        observer, client, protocol, _ = self.observer(observer_class=MOBILE.AppTextObserver)
        while observer.STEPS[observer.stage][0] != 'editor':
            self.advance(observer,protocol)
        protocol.app='foot';previous=list(client.records)
        with self.assertRaisesRegex(ValueError,'focus lost') as error:
            observer.tick(observer.next_at,True)
        self.assertEqual(client.records,previous)
        self.assertEqual(observer.finish(error.exception)['status'],'FAIL')

    def test_only_matching_tiles_and_fresh_native_focus_advance(self):
        observer, client, protocol, sleeps = self.observer()
        observer.tick(0, False)
        self.assertEqual(client.records, [])
        observer.tick(0, True)
        observer.tick(observer.next_at, True)  # Mousepad tile click
        self.assertEqual(observer.stage, 2)
        observer.tick(observer.next_at, True)
        self.assertEqual(observer.stage, 2)
        self.focus(protocol, 'foot')
        observer.tick(observer.next_at, True)
        self.assertEqual(observer.stage, 2)
        self.focus(protocol, 'mousepad')
        observer.tick(observer.next_at, True)
        self.assertEqual(observer.stage, 2)  # Native focus alone does not skip settling.
        while observer.stage == 2:
            observer.tick(observer.next_at, True)
        self.assertEqual(observer.stage, 3)
        while not observer.complete:
            self.advance(observer, protocol)
        result = observer.finish()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(client.buttons, [True, False]*6)
        self.assertTrue(client.closed)
        self.assertLess(len(client.records), 64)
        self.assertEqual(sleeps.count(.08), 3)
        self.assertEqual(sleeps.count(.025), 8)
        self.assertEqual(sleeps.count(.12), 5)
        gestures = [row['value'] for row in result['actions'] if row['operation'].endswith('gesture')]
        self.assertEqual(gestures[1:], [((270,1194),(315,1194),(365,1194),(415,1194))]*2)
        self.assertEqual(len(result['screenshots']), 7)
        self.assertIn('NOT RUN', result['visual_semantics'])
        self.assertEqual(result['phone_touch'], 'NOT RUN')

    def test_native_wait_retains_one_diagnostic_capture_without_more_input(self):
        observer, client, protocol, _ = self.observer()
        observer.tick(0, True)
        observer.tick(observer.next_at, True)
        observer.tick(observer.next_at, True)
        buttons = list(client.buttons)
        observer.tick(observer.next_at+9, True)
        self.assertEqual(observer.stage, 2)
        self.assertEqual(client.buttons, buttons)
        self.assertTrue((observer.directory/'01-mousepad-launched-waiting.png').exists())
        captures = client.capture_count
        observer.tick(observer.next_at+9, True)
        self.assertEqual(client.capture_count, captures)
        self.assertEqual(observer.finish()['status'], 'FAIL')

    def test_missing_tiles_expires_without_input(self):
        # Change a pixel inside the inspected Foot icon, not the clock/status.
        data = bytearray(1224*(540*3+1))
        data[580*(540*3+1)+1+180*3] = 255
        header = struct.pack('>IIBBBBB', 540, 1224, 8, 2, 0, 0, 0)
        self.reference.write_bytes(b'\x89PNG\r\n\x1a\n'+png_chunk(b'IHDR',header)
            +png_chunk(b'IDAT',zlib.compress(data))+png_chunk(b'IEND',b''))
        observer, client, protocol, _ = self.observer()
        for _ in range(8):
            observer.tick(observer.next_at, True)
            self.assertEqual(observer.stage, 0)
        with self.assertRaisesRegex(TimeoutError, 'tile readiness') as caught:
            observer.tick(observer.next_at, True)
        self.assertEqual(observer.finish(caught.exception)['status'], 'FAIL')
        self.assertEqual(client.buttons, [])

    def test_stale_focus_does_not_prove_switch(self):
        observer, client, protocol, _ = self.observer()
        while observer.stage < 10:
            self.advance(observer, protocol)
        protocol.app = 'mousepad'  # No new focus enter since last capture.
        observer.tick(observer.next_at, True)
        self.assertEqual(observer.stage, 10)
        self.focus(protocol, 'mousepad')
        while observer.stage == 10:
            observer.tick(observer.next_at, True)
        self.assertEqual(observer.stage, 11)
        self.assertEqual(observer.finish('interrupted')['status'], 'FAIL')

    def test_interruption_at_each_stage_is_failure_and_cleans_up(self):
        for stop in range(14):
            with self.subTest(stop=stop):
                observer, client, protocol, _ = self.observer('stage-'+str(stop))
                for _ in range(stop):
                    self.advance(observer, protocol)
                result = observer.finish('interrupted')
                self.assertEqual(result['status'], 'FAIL')
                self.assertTrue(result['pointer_released'])
                if client.records:
                    self.assertTrue(client.closed)

    def test_lost_gesture_ack_releases_pointer_on_abort(self):
        observer, client, protocol, _ = self.observer()
        while observer.stage < 3:
            self.advance(observer, protocol)
        client.fail_down = True
        with self.assertRaises(RuntimeError) as caught:
            observer.tick(observer.next_at, True)
        self.assertTrue(observer.pressed)
        result = observer.finish(caught.exception)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['pointer_released'])
        self.assertEqual(client.buttons[-2:], [True, False])


class BottomCaretEvidence(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        self.tracker = SimpleNamespace(sequence=1, presses=[], caret=None,
            geometries={24:dict(x=26,y=23,width=540,height=1176,sequence=1)}, error=None)
        self.observer = MOBILE.BottomCaretAppTextObserver.__new__(MOBILE.BottomCaretAppTextObserver)
        self.observer.caret_protocol = self.tracker
        self.observer.caret_arm = None
        self.observer.caret_baseline = None
        self.observer.now = 0
        self.observer.advance_stage = True
        self.observer.result = {'bottom_caret':{'status':'NOT RUN'}}

    def press(self, x=296, y=1075, surface=24, caret_surface=24, caret_y=1073):
        sequence = self.tracker.sequence + 1
        self.tracker.presses.append(dict(x=x,y=y,surface=surface,sequence=sequence))
        self.tracker.caret = dict(surface=caret_surface,x=30,y=caret_y,width=0,height=20,
                                  rectangle_sequence=sequence+1,sequence=sequence+2)
        self.tracker.sequence = sequence+2

    def baseline(self):
        self.observer.caret_step('arm-baseline')
        self.press()
        self.observer.caret_step('await-baseline')

    def test_matching_origin_and_translated_pointer_qualify(self):
        self.baseline()
        self.assertEqual(self.observer.result['bottom_caret']['status'],'BASELINE_ONLY')
        self.observer.caret_step('arm-mapping')
        self.press(y=1082.2)
        self.observer.caret_step('await-mapping')
        result=self.observer.result['bottom_caret']
        self.assertEqual(result['status'],'PASS')
        self.assertAlmostEqual(result['translated']['expected_upward_offset'],269.2)

    def test_historical_missing_origin_fails(self):
        self.observer.caret_step('arm-baseline')
        self.press(x=270,y=1052)
        with self.assertRaisesRegex(ValueError,'painted surface mapping'):
            self.observer.caret_step('await-baseline')

    def test_fresh_old_row_waits_for_later_low_rectangle_without_rearming(self):
        self.observer.caret_step('arm-baseline')
        armed = self.observer.caret_arm
        self.press(caret_y=90)
        self.observer.now = .8
        self.assertEqual(self.observer.caret_step('await-baseline'), .1)
        self.assertFalse(self.observer.advance_stage)
        self.assertEqual(self.observer.caret_arm, armed)
        self.assertIsNone(self.observer.caret_baseline)
        self.assertEqual(self.observer.result['bottom_caret']['status'], 'NOT RUN')
        # A later rectangle/commit for the same press, not another injected tap.
        self.tracker.sequence += 2
        self.tracker.caret.update(y=1073, rectangle_sequence=self.tracker.sequence-1,
                                  sequence=self.tracker.sequence)
        self.observer.now = 3.9
        self.observer.advance_stage = True
        self.observer.caret_step('await-baseline')
        self.assertEqual(self.observer.result['bottom_caret']['status'], 'BASELINE_ONLY')
        self.assertEqual(self.observer.caret_baseline['caret']['y'], 1073)
        self.assertEqual(len(self.tracker.presses), 1)
        self.assertIsNone(self.observer.caret_arm)

    def test_old_row_forever_expires_at_original_deadline(self):
        self.observer.caret_step('arm-baseline')
        armed = self.observer.caret_arm
        self.press(caret_y=90)
        for now in (.8, 2.5, 3.9):
            self.observer.now = now
            self.observer.advance_stage = True
            self.observer.caret_step('await-baseline')
            self.assertFalse(self.observer.advance_stage)
            self.assertEqual(self.observer.caret_arm, armed)
        self.observer.now = 4
        with self.assertRaisesRegex(ValueError, 'deadline'):
            self.observer.caret_step('await-baseline')
        self.assertIsNone(self.observer.caret_baseline)
        self.assertEqual(self.observer.result['bottom_caret']['status'], 'NOT RUN')

    def test_fresh_qualifying_rectangle_at_or_after_deadline_is_refused(self):
        for phase in ('baseline', 'mapping'):
            for now in (4, 4.1):
                with self.subTest(phase=phase, now=now):
                    self.setUp()
                    if phase == 'mapping':
                        self.baseline()
                    self.observer.caret_step('arm-'+phase)
                    self.press(y=1075 if phase == 'baseline' else 1082.2)
                    self.observer.now = now
                    with self.assertRaisesRegex(ValueError, 'deadline'):
                        self.observer.caret_step('await-'+phase)
                    self.assertEqual(self.observer.result['bottom_caret']['status'],
                                     'NOT RUN' if phase == 'baseline' else 'BASELINE_ONLY')

    def test_stale_rectangle_recommits_do_not_freshen_selection(self):
        self.observer.caret_step('arm-baseline')
        armed = self.observer.caret_arm
        self.press()
        self.tracker.caret['rectangle_sequence'] = armed[0]
        for now in (.8, 3.9):
            self.tracker.sequence += 1
            self.tracker.caret['sequence'] = self.tracker.sequence
            self.observer.now = now
            self.observer.advance_stage = True
            self.observer.caret_step('await-baseline')
            self.assertFalse(self.observer.advance_stage)
            self.assertEqual(self.observer.caret_arm, armed)
        self.observer.now = 4
        with self.assertRaisesRegex(ValueError, 'fresh pointer'):
            self.observer.caret_step('await-baseline')
        self.assertIsNone(self.observer.caret_baseline)

    def test_wrong_mapping_is_refused_even_with_transient_old_row(self):
        self.observer.caret_step('arm-baseline')
        self.press(x=270, y=1052, caret_y=90)
        with self.assertRaisesRegex(ValueError, 'painted surface mapping'):
            self.observer.caret_step('await-baseline')
        self.assertIsNone(self.observer.caret_baseline)

    def test_commit_without_new_rectangle_cannot_qualify(self):
        self.observer.caret_step('arm-baseline')
        self.press()
        self.tracker.caret['rectangle_sequence']=1
        self.observer.caret_step('await-baseline')
        self.assertFalse(self.observer.advance_stage)
        self.observer.now=4
        with self.assertRaisesRegex(ValueError,'fresh pointer'):
            self.observer.caret_step('await-baseline')

    def test_absent_events_timeout(self):
        self.observer.caret_step('arm-baseline')
        self.observer.now=4
        with self.assertRaisesRegex(ValueError,'fresh pointer'):
            self.observer.caret_step('await-baseline')

    def test_other_surface_cannot_qualify(self):
        self.observer.caret_step('arm-baseline')
        self.press(caret_surface=25)
        with self.assertRaisesRegex(ValueError,'different surfaces'):
            self.observer.caret_step('await-baseline')

    def test_missing_geometry_cannot_qualify(self):
        self.observer.caret_step('arm-baseline')
        self.press();self.tracker.geometries.clear()
        with self.assertRaisesRegex(ValueError,'geometry absent'):
            self.observer.caret_step('await-baseline')

    def test_wrong_size_cannot_qualify(self):
        self.observer.caret_step('arm-baseline')
        self.press();self.tracker.geometries[24]['width']=600
        with self.assertRaisesRegex(ValueError,'exact portrait'):
            self.observer.caret_step('await-baseline')

    def test_changed_geometry_cannot_qualify(self):
        self.baseline();self.observer.caret_step('arm-mapping')
        self.press(y=1082.2);self.tracker.geometries[24]['x']=27
        with self.assertRaisesRegex(ValueError,'geometry changed'):
            self.observer.caret_step('await-mapping')

    def test_normal_geometry_commit_is_allowed(self):
        self.baseline();self.observer.caret_step('arm-mapping')
        self.press(y=1082.2);self.tracker.geometries[24]['sequence']=20
        self.observer.caret_step('await-mapping')
        self.assertEqual(self.observer.result['bottom_caret']['status'],'PASS')

    def test_different_text_row_cannot_qualify(self):
        self.baseline();self.observer.caret_step('arm-mapping')
        self.press(y=1082.2,caret_y=1053)
        with self.assertRaisesRegex(ValueError,'different text row'):
            self.observer.caret_step('await-mapping')

    def test_old_untranslated_second_tap_fails(self):
        self.baseline();self.observer.caret_step('arm-mapping');self.press(y=813)
        with self.assertRaisesRegex(ValueError,'painted surface mapping'):
            self.observer.caret_step('await-mapping')

    def test_sticky_parse_error_aborts_even_after_mapping(self):
        self.baseline();self.observer.caret_step('arm-mapping');self.press(y=1082.2)
        self.observer.caret_step('await-mapping');self.tracker.error='ambiguous identity'
        with self.assertRaisesRegex(ValueError,'ambiguous identity'):
            self.observer.step()

    def test_parse_error_before_arm_is_preserved(self):
        self.tracker.error='malformed record'
        with self.assertRaisesRegex(ValueError,'malformed record'):
            self.observer.caret_step('arm-baseline')


if __name__ == '__main__':
    unittest.main()
