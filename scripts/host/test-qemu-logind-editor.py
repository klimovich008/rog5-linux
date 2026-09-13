#!/usr/bin/env python3
"""Real editor parser/action fixtures; transports do not claim GUI execution."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SPEC = importlib.util.spec_from_file_location(
    'logind_editor', Path(__file__).with_name('qemu-logind-editor.py'))
EDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EDITOR)


def protocol(*lines):
    return ''.join('EDITOR_WAYLAND [1.000] ' + line + '\n' for line in lines).encode()


MAPPED = protocol(
    '-> xdg_wm_base#1.get_xdg_surface(new id xdg_surface#2, wl_surface#3)',
    '-> xdg_surface#2.get_toplevel(new id xdg_toplevel#4)',
    '-> xdg_toplevel#4.set_title("rog5-text-probe.txt - Mousepad")',
    'xdg_toplevel#4.configure(540, 1224, array[4])',
    'xdg_surface#2.configure(42)',
    '-> xdg_surface#2.ack_configure(42)',
    '-> wl_surface#3.attach(wl_buffer#8, 0, 0)',
    '-> wl_surface#3.commit()')
ENTER = protocol('wl_keyboard#7.enter(43, wl_surface#3, array[0])')
LEAVE = protocol('wl_keyboard#7.leave(44, wl_surface#3)')
KEYS = protocol(*(f'wl_keyboard#7.key(45, 100, {key}, {state})'
                  for key in (20, 18, 31, 20, 14, 20) for state in (1, 0)))


def png_chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload)))


PNG = (b'\x89PNG\r\n\x1a\n'
       + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 540, 1224, 8, 2, 0, 0, 0))
       + png_chunk(b'IDAT', zlib.compress(b'\0' * (1224 * (540 * 3 + 1))))
       + png_chunk(b'IEND', b''))


class Transport:
    """Only QMP/capture transport is substituted, not observer or parser."""
    def __init__(self, path, name):
        self.records = []
        self.closed = False

    def execute(self, command, arguments):
        self.records.append({'execute': command, 'arguments': arguments})

    def close(self):
        self.closed = True


def capture(socket, name, path):
    path.write_bytes(PNG)


class LiveEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-editor-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.editor = EDITOR.LiveEditor(Path(self.temp.name) / 'observe', 'fixture',
                                        client_factory=Transport, capture_backend=capture)
        self.addCleanup(self.editor.finish)
        (self.editor.directory / 'qmp.sock').touch()  # Fake transport endpoint only.

    def append(self, data):
        with self.editor.log_path.open('ab') as target:
            target.write(data)

    def start(self):
        self.append(MAPPED + ENTER)
        self.editor.tick(0)
        self.editor.tick(1.5)
        self.assertIsNotNone(self.editor.observer.client)

    def actions(self):
        for _ in EDITOR.MOBILE.EditorObserver.STEPS:
            if self.editor.observer.complete:
                break
            self.editor.tick(self.editor.observer.next_at)
        self.assertTrue(self.editor.observer.complete)

    def test_requires_stable_focused_committed_editor_without_scheduler_audits(self):
        self.assertFalse(self.editor.tick(0))  # File may not exist before QEMU.
        self.append(MAPPED)
        self.editor.tick(1)
        self.editor.tick(100)
        self.assertIsNone(self.editor.observer.client)
        self.append(ENTER)
        self.editor.tick(101)
        self.editor.tick(102.49)
        self.assertIsNone(self.editor.observer.client)
        self.editor.tick(102.5)
        self.assertIsNotNone(self.editor.observer.client)
        self.assertFalse(self.editor.parser.ready)  # No scheduler-cadence dependency.

    def test_focus_instability_restarts_full_settle_interval(self):
        self.append(MAPPED + ENTER)
        self.editor.tick(0)
        self.append(LEAVE + ENTER)
        self.editor.tick(1)
        self.editor.tick(2)
        self.assertIsNone(self.editor.observer.client)
        self.editor.tick(2.5)
        self.assertIsNotNone(self.editor.observer.client)

    def test_wrong_title_is_not_ready(self):
        self.append(MAPPED.replace(b'rog5-text-probe.txt', b'text.txt') + ENTER)
        self.editor.tick(0)
        self.editor.tick(100)
        self.assertIsNone(self.editor.observer.client)
        self.assertEqual(self.editor.finish()['status'], 'FAIL')

    def test_invalid_configure_ack_is_not_ready(self):
        self.append(MAPPED.replace(b'ack_configure(42)', b'ack_configure(41)') + ENTER)
        self.editor.tick(0)
        self.editor.tick(100)
        self.assertFalse(self.editor.parser.mapped)
        self.assertIsNone(self.editor.observer.client)

    def test_focus_loss_and_reentry_within_one_read_fails_and_releases_pointer(self):
        self.start()
        self.editor.tick(self.editor.observer.next_at)  # move
        self.editor.tick(self.editor.observer.next_at)  # press
        self.assertTrue(self.editor.observer.pressed)
        self.append(LEAVE + ENTER)
        with self.assertRaisesRegex(ValueError, 'focus lost'):
            self.editor.tick(2)
        result = self.editor.finish()
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('focus lost', result['error'])
        self.assertTrue(result['observation']['pointer_released'])
        self.assertTrue(self.editor.observer.client.closed)
        final = self.editor.observer.client.records[-1]['arguments']['events']
        self.assertEqual(final, [{'type': 'btn', 'data': {'button': 'left', 'down': False}}])

    def test_unmap_during_actions_is_failure(self):
        self.start()
        self.append(protocol('-> wl_surface#3.attach(nil, 0, 0)', '-> wl_surface#3.commit()'))
        with self.assertRaisesRegex(ValueError, 'focus lost'):
            self.editor.tick(2)

    def test_wrong_focus_surface_does_not_start(self):
        self.append(MAPPED + ENTER.replace(b'wl_surface#3', b'wl_surface#99'))
        self.editor.tick(0)
        self.editor.tick(100)
        self.assertIsNone(self.editor.observer.client)

    def test_one_mib_bound(self):
        self.append(b'\n' * (self.editor.LOG_LIMIT + 1))
        with self.assertRaisesRegex(ValueError, '1 MiB'):
            self.editor.tick(0)
        self.assertEqual(self.editor.offset, 0)

    def test_truncated_stream(self):
        self.append(MAPPED)
        self.editor.tick(0)
        self.editor.log_path.write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'truncated'):
            self.editor.tick(1)

    def test_replaced_stream(self):
        self.append(MAPPED)
        self.editor.tick(0)
        replacement = self.editor.directory / 'replacement'
        replacement.write_bytes(MAPPED)
        replacement.replace(self.editor.log_path)
        with self.assertRaisesRegex(ValueError, 'replaced'):
            self.editor.tick(1)

    def test_symlink_stream_refused(self):
        outside = Path(self.temp.name) / 'outside'
        outside.write_bytes(MAPPED + ENTER)
        self.editor.log_path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            self.editor.tick(0)
        self.assertEqual(outside.read_bytes(), MAPPED + ENTER)

    def test_existing_observation_directory_refused(self):
        marker = self.editor.directory / 'retained'
        marker.write_text('keep')
        with self.assertRaises(FileExistsError):
            EDITOR.LiveEditor(self.editor.directory, 'fixture')
        self.assertEqual(marker.read_text(), 'keep')

    def test_partial_lines_wait_and_unterminated_finish_fails(self):
        self.append(MAPPED + ENTER[:-1])
        self.editor.tick(0)
        self.editor.tick(100)
        self.assertIsNone(self.editor.observer.client)
        self.append(b'\n')
        self.editor.tick(101)
        self.editor.tick(102.5)
        self.assertIsNotNone(self.editor.observer.client)
        self.append(b'EDITOR_WAYLAND unfinished')
        result = self.editor.finish()
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('incomplete line', result['error'])

    def test_oversized_line(self):
        self.append(b'x' * (self.editor.parser.LINE_LIMIT + 1))
        with self.assertRaisesRegex(ValueError, '16 KiB'):
            self.editor.tick(0)

    def test_protocol_pass_alone_cannot_complete_observation(self):
        self.append(MAPPED + ENTER + KEYS)
        self.editor.tick(0)
        self.assertEqual(self.editor.parser.result()['status'], 'PASS')
        self.assertFalse(self.editor.complete)
        self.assertEqual(self.editor.finish()['status'], 'FAIL')

    def test_action_completion_alone_cannot_pass_missing_protocol(self):
        self.start()
        self.actions()
        self.assertFalse(self.editor.complete)
        result = self.editor.finish()
        self.assertEqual(result['observation']['status'], 'PASS')
        self.assertEqual(result['protocol']['status'], 'FAIL')
        self.assertEqual(result['status'], 'FAIL')

    def test_unfocused_key_records_cannot_pass_completed_actions(self):
        self.start()
        self.actions()
        self.append(LEAVE + KEYS)
        self.editor.tick(20)
        result = self.editor.finish()
        self.assertTrue(result['protocol']['unfocused_keys'])
        self.assertEqual(result['status'], 'FAIL')

    def test_complete_combines_oracles_and_only_pointer_events_are_injected(self):
        self.start()
        self.actions()
        # These are transport-fixture incoming events, not asserted GUI output.
        self.append(KEYS + LEAVE)  # Normal app teardown after actions is allowed.
        self.assertTrue(self.editor.tick(20))
        result = self.editor.finish()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['phone_touch'], 'NOT RUN')
        self.assertTrue(result['observation']['visual_semantics'].startswith('NOT RUN'))
        self.assertEqual(len(result['observation']['screenshots']), 6)
        events = [event for record in self.editor.observer.client.records
                  for event in record['arguments']['events']]
        self.assertEqual({event['type'] for event in events}, {'abs', 'btn'})
        self.assertTrue(result['observation']['pointer_released'])
        self.assertTrue(self.editor.observer.client.closed)
        self.assertIs(self.editor.finish(), result)
        self.assertEqual(json.loads((self.editor.directory / 'editor-result.json').read_text())['status'], 'PASS')

    def test_external_error_preserved_after_both_oracles_complete(self):
        self.start()
        self.actions()
        self.append(KEYS)
        self.editor.tick(20)
        result = self.editor.finish('VM deadline exceeded')
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['error'], 'VM deadline exceeded')


if __name__ == '__main__':
    unittest.main()
