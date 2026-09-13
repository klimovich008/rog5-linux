#!/usr/bin/env python3
"""Execute the production launcher stream parser with attributed protocol fixtures."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('launcher_protocol', Path(__file__).with_name('qemu-launcher-protocol.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LauncherProtocolTests(unittest.TestCase):
    def parser(self):
        return MODULE.LauncherProtocol()

    @staticmethod
    def owner(app):
        return f'OBSERVE launcher app={app} owner={100 if app == "mousepad" else 200} start=999\n'

    @staticmethod
    def wire(app, *lines):
        prefix = 'EDITOR_WAYLAND' if app == 'mousepad' else 'FOOT_WAYLAND'
        return ''.join(f'{prefix} [00:01:02.500000] {{Default Queue}} {line}\n' for line in lines)

    @staticmethod
    def lifecycle(app):
        title = '/tmp/rog5-text-probe.txt - Mousepad' if app == 'mousepad' else 'foot'
        app_id = 'org.xfce.mousepad' if app == 'mousepad' else 'foot'
        return [
            '-> xdg_wm_base#2.get_xdg_surface(new id xdg_surface#3, wl_surface#4)',
            '-> xdg_surface#3.get_toplevel(new id xdg_toplevel#5)',
            f'-> xdg_toplevel#5.set_title("{title}")',
            f'-> xdg_toplevel#5.set_app_id("{app_id}")',
            'xdg_toplevel#5.configure(540, 1200, array[4])',
            'xdg_surface#3.configure(71)',
            '-> xdg_surface#3.ack_configure(71)',
            '-> wl_surface#4.attach(wl_buffer#8, 0, 0)',
            '-> wl_surface#4.commit()',
        ]

    @staticmethod
    def audits(count=2):
        return f'Denial/Volition output scheduler audit presentations={count}\n' * 2

    def launch(self, app):
        return self.owner(app)+self.wire(app, *self.lifecycle(app))

    def enter(self, app):
        return self.wire(app, 'wl_keyboard#6.enter(80, wl_surface#4, array[0])')

    def leave(self, app):
        return self.wire(app, 'wl_keyboard#6.leave(81, wl_surface#4)')

    def success_log(self):
        return (self.launch('mousepad')+self.enter('mousepad')+self.audits()
                +self.leave('mousepad')+self.launch('foot')+self.enter('foot')+self.audits()
                +self.leave('foot')+self.enter('mousepad')+self.audits()
                +self.leave('mousepad')+self.enter('foot')+self.audits())

    def test_complete_sequence_and_separate_client_object_namespaces(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        self.assertEqual(parser.result()['status'], 'PASS')
        self.assertEqual(parser.focus_history, ['mousepad', 'foot', 'mousepad', 'foot'])
        self.assertTrue(parser.focused('foot'))
        self.assertFalse(parser.focused('mousepad'))
        self.assertTrue(parser.ready('mousepad'))
        self.assertEqual(parser.result()['phone'], 'NOT RUN')

    def test_split_stream_and_ansi_and_legacy_object_syntax(self):
        for text in (self.success_log(), self.success_log().replace('#', '@'),
                     '\x1b[32m'+self.success_log().replace('\n', '\x1b[0m\r\n\x1b[32m')):
            parser = self.parser()
            for byte in text.encode():
                parser.feed(bytes([byte]))
            self.assertEqual(parser.result()['status'], 'PASS')

    def test_static_native_clients_need_no_later_audit_to_allow_capture(self):
        parser = self.parser()
        # OutputSchedulerAudit reports only on activity after its one-second
        # interval; a mapped scene can settle before any later report exists.
        parser.feed(self.success_log().replace(self.audits(), '').encode())
        self.assertTrue(parser.ready('mousepad'))
        self.assertTrue(parser.ready('foot'))
        self.assertTrue(parser.focused('foot'))
        self.assertEqual(parser.focus_generation, 4)
        self.assertEqual(parser.result()['status'], 'PASS')

    def test_each_missing_lifecycle_event_blocks_that_client(self):
        for app in ('mousepad', 'foot'):
            for index in range(len(self.lifecycle(app))):
                with self.subTest(app=app, index=index):
                    line = self.wire(app, self.lifecycle(app)[index])
                    parser = self.parser()
                    parser.feed(self.success_log().replace(line, '', 1).encode())
                    self.assertEqual(parser.result()['status'], 'FAIL')
                    self.assertFalse(parser.ready(app))

    def test_unowned_or_mismatched_prefix_does_not_count(self):
        for text in (self.success_log().replace(self.owner('foot'), ''),
                     self.success_log().replace('FOOT_WAYLAND ', 'UNOWNED_WAYLAND '),
                     self.success_log().replace('FOOT_WAYLAND ', 'EDITOR_WAYLAND ')):
            parser = self.parser()
            parser.feed(text.encode())
            self.assertEqual(parser.result()['status'], 'FAIL')

    def test_duplicate_and_shared_supervisor_identity_rejected(self):
        for text in (self.owner('foot')+self.success_log(),
                     self.success_log().replace('app=foot owner=200', 'app=foot owner=100')):
            parser = self.parser()
            parser.feed(text.encode())
            self.assertIn('duplicate launcher owner', parser.errors)
            self.assertEqual(parser.result()['status'], 'FAIL')

    def test_exact_app_identity_and_title_required(self):
        variants = [('"org.xfce.mousepad"', '"fake.org.xfce.mousepad"'),
                    ('set_app_id("foot")', 'set_app_id("footclient")'),
                    ('set_title("foot")', 'set_title("")'),
                    ('/tmp/rog5-text-probe.txt - Mousepad', '/else/rog5-text-probe.txt - Mousepad')]
        for before, after in variants:
            parser = self.parser()
            parser.feed(self.success_log().replace(before, after).encode())
            self.assertEqual(parser.result()['status'], 'FAIL')

    def test_valid_dynamic_titles_keep_identity(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        parser.feed((self.wire('foot', '-> xdg_toplevel#5.set_title("deck@vm: ~")')+
                     self.wire('mousepad', '-> xdg_toplevel#5.set_title("*/tmp/rog5-text-probe.txt - Mousepad")')).encode())
        self.assertEqual(parser.result()['status'], 'PASS')

    def test_bad_serial_surface_toplevel_direction_and_attach_order(self):
        changes = [('ack_configure(71)', 'ack_configure(70)'),
                   ('wl_surface#4.attach', 'wl_surface#9.attach'),
                   ('wl_buffer#8, 0, 0', 'nil, 0, 0'),
                   ('xdg_toplevel#5.configure', 'xdg_toplevel#9.configure'),
                   ('-> xdg_surface#3.ack_configure', 'xdg_surface#3.ack_configure')]
        for before, after in changes:
            parser = self.parser()
            parser.feed(self.success_log().replace(before, after).encode())
            self.assertEqual(parser.result()['status'], 'FAIL')
        lines = self.lifecycle('foot')
        lines[6], lines[7] = lines[7], lines[6]
        parser = self.parser()
        parser.feed((self.owner('foot')+self.wire('foot', *lines)+self.enter('foot')+self.audits()).encode())
        self.assertFalse(parser.ready('foot'))

    def test_zero_or_first_interval_is_not_presentation_proof(self):
        parser = self.parser()
        parser.feed(self.audits().encode())  # Global output alone cannot map a client.
        self.assertFalse(parser.ready('mousepad'))
        parser.feed((self.launch('mousepad')+self.enter('mousepad')).encode())
        self.assertTrue(parser.focused('mousepad'))
        parser.feed(b'Denial/Volition output scheduler audit presentations=2\n')
        self.assertFalse(parser.focus_visits[-1]['presented_interval'])
        parser.feed(self.audits(0).encode())
        self.assertFalse(parser.focus_visits[-1]['presented_interval'])
        parser.feed(b'Denial/Volition output scheduler audit presentations=1\n')
        self.assertTrue(parser.focus_visits[-1]['presented_interval'])
        observation = parser.result()['focus_visits'][-1]['presentation_observation']
        self.assertEqual(observation['status'], 'PASS')
        self.assertEqual(observation['client_presentation'], 'NOT RUN')
        self.assertIn('global output', observation['scope'])

    def test_each_focus_visit_reports_optional_global_interval_separately(self):
        parser = self.parser()
        text = self.success_log()
        parser.feed(text[:-len(self.audits())].encode())
        self.assertTrue(parser.focused('foot'))
        result = parser.result()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['focus_visits'][-1]['presentation_observation']['status'], 'NOT RUN')
        parser.feed(self.audits().encode())
        result = parser.result()
        self.assertEqual(result['focus_visits'][-1]['presentation_observation']['status'], 'PASS')
        self.assertEqual(result['focus_visits'][-1]['presentation_observation']['client_presentation'], 'NOT RUN')
        self.assertIn('no attributed client presentation', result['presentation'])
        self.assertIn('mapping and focus sequence only', result['scope'])

    def test_wrong_keyboard_or_surface_leave_rejected(self):
        for before, after in [('wl_keyboard#6.leave', 'wl_keyboard#7.leave'),
                              ('leave(81, wl_surface#4)', 'leave(81, wl_surface#9)'),
                              ('enter(80, wl_surface#4', 'enter(80, wl_surface#9')]:
            parser = self.parser()
            parser.feed(self.success_log().replace(before, after).encode())
            self.assertEqual(parser.result()['status'], 'FAIL')

    def test_missing_leave_and_duplicate_enter_do_not_manufacture_switch(self):
        parser = self.parser()
        parser.feed(self.success_log().replace(self.leave('mousepad'), '', 1).encode())
        self.assertEqual(parser.result()['status'], 'FAIL')
        parser = self.parser()
        parser.feed(self.success_log().encode())
        parser.feed((self.enter('foot')+self.audits()).encode())
        self.assertEqual(len(parser.focus_history), 4)
        self.assertEqual(parser.result()['status'], 'PASS')

    def test_cross_client_enter_before_matching_leave_is_pending(self):
        parser = self.parser()
        parser.feed((self.launch('mousepad')+self.enter('mousepad')+self.launch('foot')).encode())
        generation = parser.focus_generation
        parser.feed(self.wire('foot', 'wl_keyboard#6.enter(23, wl_surface#4, array[0])').encode())
        self.assertEqual(parser.errors, [])
        self.assertFalse(parser.focused('foot'))
        self.assertFalse(parser.focused('mousepad'))
        self.assertEqual(parser.focus_generation, generation)
        self.assertEqual(parser.result(('mousepad',))['status'], 'FAIL')
        parser.feed(self.wire('mousepad', 'wl_keyboard#6.leave(23, wl_surface#4)').encode())
        self.assertEqual(parser.errors, [])
        self.assertTrue(parser.focused('foot'))
        self.assertEqual(parser.focus_history, ['mousepad', 'foot'])
        self.assertEqual(parser.result(('mousepad', 'foot'))['status'], 'PASS')

    def test_reordered_complete_sequence_byte_at_a_time(self):
        parser = self.parser()
        text = self.launch('mousepad')+self.enter('mousepad')+self.launch('foot')
        for old, new, serial in [('mousepad', 'foot', 23), ('foot', 'mousepad', 24),
                                 ('mousepad', 'foot', 25)]:
            text += self.wire(new, f'wl_keyboard#6.enter({serial}, wl_surface#4, array[0])')
            text += self.wire(old, f'wl_keyboard#6.leave({serial}, wl_surface#4)')
        for byte in text.encode():
            parser.feed(bytes([byte]))
        self.assertEqual(parser.result()['status'], 'PASS')
        self.assertEqual(parser.focus_generation, 4)
        self.assertTrue(parser.focused('foot'))
        self.assertIsNone(parser.pending_focus)

    def test_reordered_transition_rejects_wrong_serial_or_endpoint(self):
        for leave in ['wl_keyboard#6.leave(24, wl_surface#4)',
                      'wl_keyboard#7.leave(23, wl_surface#4)',
                      'wl_keyboard#6.leave(23, wl_surface#9)']:
            with self.subTest(leave=leave):
                parser = self.parser()
                parser.feed((self.launch('mousepad')+self.enter('mousepad')+self.launch('foot')
                             +self.wire('foot', 'wl_keyboard#6.enter(23, wl_surface#4, array[0])')
                             +self.wire('mousepad', leave)).encode())
                self.assertEqual(parser.result(('mousepad', 'foot'))['status'], 'FAIL')
                self.assertFalse(parser.focused('foot'))
                self.assertEqual(parser.focus_generation, 1)

    def test_pending_duplicate_enter_does_not_complete_or_duplicate_switch(self):
        parser = self.parser()
        enter = self.wire('foot', 'wl_keyboard#6.enter(23, wl_surface#4, array[0])')
        parser.feed((self.launch('mousepad')+self.enter('mousepad')+self.launch('foot')+enter+enter).encode())
        self.assertEqual(parser.errors, [])
        self.assertEqual(parser.focus_generation, 1)
        self.assertFalse(parser.focused('foot'))
        parser.feed(self.wire('mousepad', 'wl_keyboard#6.leave(23, wl_surface#4)').encode())
        self.assertEqual(parser.focus_generation, 2)
        self.assertTrue(parser.focused('foot'))

    def test_focus_before_initial_commit_is_recorded_only_after_mapping(self):
        parser = self.parser()
        lines = self.lifecycle('mousepad')
        parser.feed((self.owner('mousepad')+self.wire('mousepad', *lines[:4])+self.enter('mousepad')).encode())
        self.assertEqual(parser.focus_history, [])
        parser.feed((self.wire('mousepad', *lines[4:])+self.audits()).encode())
        self.assertEqual(parser.focus_history, ['mousepad'])
        self.assertTrue(parser.focused('mousepad'))

    def test_commit_without_attach_retains_buffer_and_mapping(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        parser.feed(self.wire('foot', 'xdg_toplevel#5.configure(540, 1200, array[4])',
                             'xdg_surface#3.configure(90)', '-> xdg_surface#3.ack_configure(90)',
                             '-> wl_surface#4.commit()', '-> wl_surface#4.commit()').encode())
        self.assertEqual(parser.result()['status'], 'PASS')

    def test_null_attach_takes_effect_only_on_commit(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        parser.feed(self.wire('foot', '-> wl_surface#4.attach(nil, 0, 0)').encode())
        self.assertEqual(parser.result()['status'], 'PASS')
        parser.feed(self.wire('foot', '-> wl_surface#4.commit()').encode())
        self.assertFalse(parser.ready('foot'))
        self.assertEqual(parser.result()['status'], 'FAIL')

    def test_destroy_revokes_completed_result_permanently(self):
        for event in ('-> xdg_toplevel#5.destroy()', '-> xdg_surface#3.destroy()', '-> wl_surface#4.destroy()'):
            parser = self.parser()
            parser.feed(self.success_log().encode())
            parser.feed(self.wire('foot', event).encode())
            parser.feed(self.audits().encode())
            self.assertEqual(parser.result()['status'], 'FAIL')
            self.assertFalse(parser.ready('mousepad'))  # Overall trial invalidated.

    def test_early_zero_and_nonzero_exit_and_limit_revoke_success(self):
        for marker in ('OBSERVE launcher app=foot exit=0\n', 'OBSERVE launcher app=mousepad exit=42\n',
                       'FAIL launcher client log limit\n', 'FAIL launcher cleanup deadline: foot\n'):
            parser = self.parser()
            parser.feed(self.success_log().encode())
            parser.feed(marker.encode())
            self.assertEqual(parser.result()['status'], 'FAIL')

    def test_terminal_teardown_preserves_observation_but_fail_marker_does_not(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        parser.feed(b'independently clocked Flutter KMS session complete raster_frames=20 output_page_flips=20\n')
        parser.feed((self.wire('foot', '-> wl_surface#4.destroy()')+'OBSERVE launcher app=foot exit=1\n').encode())
        self.assertEqual(parser.result()['status'], 'PASS')
        self.assertEqual(len(parser.result()['post_terminal_exits']), 1)
        parser.feed(b'FAIL launcher cleanup deadline: foot\n')
        self.assertEqual(parser.result()['status'], 'FAIL')

    def test_client_cannot_spoof_supervisor_or_terminal(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        parser.feed(b'FOOT_WAYLAND independently clocked Flutter KMS session complete\n')
        parser.feed(b'OBSERVE launcher app=foot exit=1\n')
        self.assertFalse(parser.terminal)
        self.assertEqual(parser.result()['status'], 'FAIL')

    def test_custom_sequence_is_exact_not_subsequence(self):
        parser = self.parser()
        parser.feed(self.success_log().encode())
        self.assertEqual(parser.result(('mousepad', 'foot'))['status'], 'FAIL')
        self.assertEqual(parser.result(())['status'], 'FAIL')

    def test_log_bounds_and_file_truncation(self):
        parser = self.parser()
        with self.assertRaises(ValueError):
            parser.feed(b'x' * 16385)
        parser = self.parser()
        parser.LOG_LIMIT = 8
        with self.assertRaises(ValueError):
            parser.feed(b'123456789')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'serial.log'
            path.write_text(self.success_log())
            parser = self.parser()
            parser.read_available(path)
            self.assertEqual(parser.result()['status'], 'PASS')
            before = parser.offset
            parser.read_available(path)
            self.assertEqual(parser.offset, before)
            path.write_text('')
            with self.assertRaises(ValueError):
                parser.read_available(path)


if __name__ == '__main__':
    unittest.main()
