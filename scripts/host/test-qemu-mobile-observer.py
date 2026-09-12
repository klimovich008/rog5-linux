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


if __name__ == '__main__':
    unittest.main()
