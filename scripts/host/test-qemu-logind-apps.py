#!/usr/bin/env python3
"""Production launcher/editor oracles and actions over bounded real UNIX sockets."""
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest


def sibling(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

APPS = sibling('apps', 'qemu-logind-apps.py')
FIX = sibling('launcher_fixtures', 'test-qemu-launcher-protocol.py')
MOBILE_FIX = sibling('mobile_fixtures', 'test-qemu-mobile-observer.py')
TOKEN = 'ROG5_APPS_DONE_' + 'a' * 32
READY = b'OBSERVE authenticated launcher flow-ready\n'
TEARDOWN = b'OBSERVE authenticated launcher teardown\n'
EXITS = b'OBSERVE launcher app=mousepad exit=0\nOBSERVE launcher app=foot exit=0\n'
F = FIX.LauncherProtocolTests()
KEYS = F.wire('mousepad', *(f'wl_keyboard#6.key(82, 100, {key}, {state})'
                           for key in (20, 18, 31, 20, 14, 20) for state in (1, 0))).encode()


class LiveAppsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='apps-test-')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        reference = root/'reference.png'
        reference.write_bytes(MOBILE_FIX.png_fixture())
        self.client = MOBILE_FIX.CaptureClient(root/'observe')
        self.apps = APPS.LiveApps(root/'observe', 'fixture', TOKEN, reference,
            client_factory=lambda *_: self.client,
            capture_backend=lambda socket, name, path: path.write_bytes(MOBILE_FIX.png_fixture()))
        self.addCleanup(self.apps.finish)
        self.apps.observer.sleep = lambda _: None
        (self.apps.directory/'qmp.sock').touch()
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.settimeout(.2)
        self.listener.bind(str(self.apps.directory/'apps.sock'))
        self.listener.listen(1)
        self.apps.tick(0)
        self.peer, _ = self.listener.accept()
        self.addCleanup(self.peer.close)
        self.peer.settimeout(.2)
        self.keys_sent = False
        self.focused_stages = set()

    def send(self, data):
        self.peer.sendall(data if isinstance(data, bytes) else data.encode())

    def no_ack(self):
        self.peer.setblocking(False)
        try:
            with self.assertRaises(BlockingIOError):
                self.peer.recv(256)
        finally:
            self.peer.settimeout(.2)

    def advance(self, keys=True):
        observer = self.apps.observer
        operation, value = observer.STEPS[observer.stage]
        if operation == 'client' and observer.stage not in self.focused_stages:
            self.focused_stages.add(observer.stage)
            app = value[0]
            previous = self.apps.parser.launcher.active_app
            if previous:
                self.send(F.leave(previous))
            if app not in self.apps.parser.launcher.owners:
                self.send(F.launch(app))
            self.send(F.enter(app))
        if operation == 'editor' and not self.keys_sent:
            self.keys_sent = True
            if keys:
                self.send(KEYS)
        self.apps.tick(observer.next_at)

    def actions(self, keys=True):
        if not self.apps.ready:
            self.send(READY)
            self.apps.tick(0)
        for _ in range(150):
            if self.apps.observer.complete:
                return
            self.advance(keys)
        self.fail('fixed application flow did not complete within fixture bound')

    def approved_finish(self, exits=EXITS):
        self.send(TEARDOWN+exits)
        self.apps.tick(self.apps.observer.next_at)
        self.peer.shutdown(socket.SHUT_WR)
        return self.apps.finish()

    def test_complete_real_socket_handshake_exact_once_and_both_clean_exits(self):
        self.actions()
        self.assertTrue(self.apps.complete)
        self.assertEqual(self.peer.recv(256), (TOKEN+'\n').encode())
        self.apps.tick(self.apps.observer.next_at)
        self.no_ack()
        result = self.approved_finish()
        self.assertEqual(result['status'], 'PASS', result)
        self.assertTrue(result['acknowledgement_sent'])
        self.assertTrue(result['approved_teardown'])
        self.assertTrue(result['clean_client_exits'])
        self.assertEqual(result['launcher_protocol']['focus_history'], ['mousepad','foot','mousepad','foot'])
        self.assertEqual(len(result['editor_protocol']['keys']), 12)
        self.assertEqual(result['phone'], 'NOT RUN')
        self.assertIn('NOT RUN', result['observation']['visual_semantics'])
        self.assertEqual(self.client.buttons, [True, False]*17)
        self.assertLess(len(self.client.records), 96)
        self.assertTrue(self.client.closed)
        self.assertIs(self.apps.finish(), result)

    def test_action_completion_cannot_ack_missing_editor_keys(self):
        self.actions(keys=False)
        self.assertEqual(self.apps.parser.launcher.result()['status'], 'PASS')
        self.assertFalse(self.apps.ack_sent)
        self.no_ack()
        self.assertEqual(self.apps.finish()['status'], 'FAIL')

    def test_both_protocol_oracles_cannot_ack_without_ui_actions(self):
        text = F.success_log().replace(F.leave('mousepad'), KEYS.decode()+F.leave('mousepad'), 1)
        self.send(READY+text.encode())
        self.apps.tick(0)
        self.assertEqual(self.apps.parser.result()['status'], 'PASS')
        self.assertFalse(self.apps.observer.complete)
        self.no_ack()
        self.assertEqual(self.apps.finish()['status'], 'FAIL')

    def test_partial_ready_line_waits_and_incomplete_finish_fails(self):
        self.send(READY[:-1])
        self.apps.tick(0)
        self.assertFalse(self.apps.ready)
        self.assertIsNone(self.apps.observer.client)
        self.no_ack()
        result = self.apps.finish()
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('incomplete line', result['error'])

    def test_partial_ready_line_can_complete(self):
        self.send(READY[:-1])
        self.apps.tick(0)
        self.send(b'\n')
        self.apps.tick(1)
        self.assertTrue(self.apps.ready)
        self.assertIsNotNone(self.apps.observer.client)

    def test_wrong_readiness_token_never_arms(self):
        self.send(READY.replace(b'flow-ready', b'flow-ready-wrong'))
        self.apps.tick(0)
        self.assertFalse(self.apps.ready)
        self.assertIsNone(self.apps.observer.client)
        self.no_ack()

    def test_duplicate_ready_is_error(self):
        self.send(READY+READY)
        with self.assertRaisesRegex(ValueError, 'duplicate or late'):
            self.apps.tick(0)
        self.no_ack()

    def test_owner_before_ready_rejects_late_ready(self):
        self.send(F.owner('mousepad').encode()+READY)
        with self.assertRaisesRegex(ValueError, 'duplicate or late'):
            self.apps.tick(0)
        self.no_ack()

    def test_early_teardown_is_rejected(self):
        self.send(READY+TEARDOWN+EXITS)
        with self.assertRaisesRegex(ValueError, 'unapproved'):
            self.apps.tick(0)
        self.no_ack()

    def test_early_client_exit_is_rejected(self):
        self.send(READY+EXITS)
        with self.assertRaisesRegex(ValueError, 'before terminal'):
            self.apps.tick(0)
        self.no_ack()

    def test_forged_compositor_terminal_cannot_authorize_teardown(self):
        self.send(b'independently clocked Flutter KMS session complete raster_frames=9\n')
        with self.assertRaisesRegex(ValueError, 'separate serial oracle'):
            self.apps.tick(0)
        self.no_ack()

    def test_eof_before_approved_teardown_is_failure(self):
        self.peer.shutdown(socket.SHUT_WR)
        with self.assertRaisesRegex(ValueError, 'before approved teardown'):
            self.apps.tick(0)
        self.assertEqual(self.apps.finish()['status'], 'FAIL')

    def test_duplicate_teardown_is_failure_even_after_exact_ack(self):
        self.actions()
        self.assertEqual(self.peer.recv(256), (TOKEN+'\n').encode())
        self.send(TEARDOWN+TEARDOWN+EXITS)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.apps.tick(self.apps.observer.next_at)
        self.assertEqual(self.apps.finish()['status'], 'FAIL')

    def test_both_exit_records_are_required_once_and_zero(self):
        self.actions()
        self.peer.recv(256)
        result = self.approved_finish(EXITS.replace(b'app=foot exit=0', b'app=foot exit=1'))
        self.assertFalse(result['clean_client_exits'])
        self.assertEqual(result['status'], 'FAIL')

    def test_missing_foot_exit_cannot_pass(self):
        self.actions(); self.peer.recv(256)
        result = self.approved_finish(b'OBSERVE launcher app=mousepad exit=0\n')
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['clean_client_exits'])

    def test_duplicate_exit_cannot_pass(self):
        self.actions(); self.peer.recv(256)
        result = self.approved_finish(EXITS+EXITS.splitlines(keepends=True)[0])
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['clean_client_exits'])

    def test_transient_editor_focus_loss_is_error_before_more_actions(self):
        self.send(READY); self.apps.tick(0)
        while self.apps.observer.STEPS[self.apps.observer.stage][0] != 'editor':
            self.advance()
        self.advance()  # Initial editor capture.
        self.advance()  # Move into editor.
        self.advance()  # Hold pointer button.
        self.assertTrue(self.apps.observer.pressed)
        previous = list(self.client.records)
        self.send(F.leave('mousepad')+F.enter('mousepad'))
        with self.assertRaisesRegex(ValueError, 'focus lost'):
            self.apps.tick(self.apps.observer.next_at)
        self.assertEqual(self.client.records, previous)
        self.no_ack()
        result = self.apps.finish()
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['observation']['pointer_released'])
        self.assertTrue(self.client.closed)
        self.assertEqual(self.client.buttons[-1], False)

    def test_editor_key_bound_is_enforced_through_application_stream(self):
        self.send(READY+F.launch('mousepad').encode()+F.enter('mousepad').encode())
        self.apps.tick(0)
        keys = F.wire('mousepad', *('wl_keyboard#6.key(90, 100, 20, 1)' for _ in range(65)))
        self.send(keys)
        with self.assertRaisesRegex(ValueError, 'key event bound'):
            self.apps.tick(1)
        self.assertEqual(len(self.apps.parser.editor.keys), 64)
        self.no_ack()

    def test_capture_failure_never_acknowledges_completed_protocol(self):
        self.send(READY); self.apps.tick(0)
        while self.apps.observer.stage < len(self.apps.observer.STEPS)-1:
            self.advance()
        self.advance()  # Final focus is present; final screenshot has not run.
        self.assertEqual(self.apps.parser.result()['status'], 'PASS')
        def failed_capture(*_):
            raise RuntimeError('capture failed')
        self.apps.observer.capture_backend = failed_capture
        with self.assertRaisesRegex(RuntimeError, 'capture failed'):
            self.apps.tick(self.apps.observer.next_at+2)
        self.no_ack()
        self.assertEqual(self.apps.finish()['status'], 'FAIL')

    def test_partial_terminal_line_cannot_finalize_clean_exit(self):
        self.actions(); self.peer.recv(256)
        self.send(TEARDOWN+EXITS[:-1])
        result = self.apps.finish()
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('incomplete line', result['error'])

    def test_failed_observation_cannot_resume_and_send_completion_ack(self):
        self.send(READY); self.apps.tick(0)
        while self.apps.observer.stage < len(self.apps.observer.STEPS)-1:
            self.advance()
        # Final client mapping/focus is real, while its capture is still waiting.
        self.advance()
        self.send(READY)
        with self.assertRaisesRegex(ValueError, 'duplicate or late'):
            self.apps.tick(self.apps.observer.next_at)
        with self.assertRaisesRegex(ValueError, 'duplicate or late'):
            self.apps.tick(self.apps.observer.next_at+2)
        self.no_ack()

    def test_partial_ack_retries_send_only_unsent_bytes_once(self):
        self.send(READY); self.apps.tick(0)
        while self.apps.observer.stage < len(self.apps.observer.STEPS)-1:
            self.advance()
        transport = self.apps.transport
        class PartialSender:
            calls = 0
            def recv(self, size): return transport.recv(size)
            def close(self): transport.close()
            def send(self, data):
                self.calls += 1
                if self.calls == 1:
                    raise BlockingIOError()
                return transport.send(data[:7])
        self.apps.transport = PartialSender()
        self.actions()
        self.assertFalse(self.apps.ack_sent)
        self.no_ack()
        for _ in range(16):
            if self.apps.ack_sent:
                break
            self.apps.tick(self.apps.observer.next_at)
        self.assertTrue(self.apps.ack_sent)
        self.assertEqual(self.peer.recv(256), (TOKEN+'\n').encode())
        self.apps.tick(self.apps.observer.next_at)
        self.no_ack()
        self.assertEqual(self.approved_finish()['status'], 'PASS')

    def test_exact_token_format_is_required_before_output_creation(self):
        for token in ('ROG5_APPS_DONE_fixture', TOKEN+'\n', TOKEN.upper(), TOKEN+'0'):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, 'exact observation token'):
                APPS.LiveApps(self.apps.directory/'unused', 'fixture', token,
                              self.apps.directory.parent/'reference.png')
        self.assertFalse((self.apps.directory/'unused').exists())


if __name__ == '__main__':
    unittest.main()
