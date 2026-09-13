#!/usr/bin/env python3
"""Pure Python protocol regressions; no VM, compositor or hardware effects."""
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location('caret_protocol', Path(__file__).with_name('qemu-caret-protocol.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CaretProtocol = MODULE.CaretProtocol


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tracker = CaretProtocol()

    def feed(self, record, prefix=b'EDITOR_WAYLAND '):
        self.tracker.feed(prefix + b'[00:03:49.534589] {Default Queue} ' + record.encode() + b'\n')

    def text(self, method, args='', oid=29):
        arrow = '' if method in ('enter', 'leave') else ' -> '
        self.feed(f'{arrow}zwp_text_input_v3#{oid}.{method}({args})')

    def activate(self, oid=29, surface=24, rect='29, 90, 0, 20'):
        self.text('enter', f'wl_surface#{surface}', oid)
        self.text('enable', oid=oid)
        self.text('set_cursor_rectangle', rect, oid)
        self.text('commit', oid=oid)

    def pointer(self, method, args='', oid=15):
        self.feed(f'wl_pointer#{oid}.{method}({args})')

    def geometry(self):
        self.feed(' -> xdg_wm_base#4.get_xdg_surface(new id xdg_surface#26, wl_surface#24)')
        self.feed(' -> xdg_surface#26.set_window_geometry(26, 23, 540, 1176)')

    def test_uncommitted_geometry_ignored_and_zero_width_valid(self):
        self.text('enter', 'wl_surface#24')
        self.text('enable')
        self.text('set_cursor_rectangle', '29, 90, 0, 20')
        self.assertIsNone(self.tracker.caret)
        self.text('commit')
        self.assertEqual(self.tracker.caret, dict(surface=24, x=29, y=90, width=0, height=20,
                                                sequence=4, rectangle_sequence=3))

    def test_pending_update_does_not_change_committed_caret(self):
        self.activate()
        old = dict(self.tracker.caret)
        self.text('set_cursor_rectangle', '30, 800, 1, 20')
        self.assertEqual(self.tracker.caret, old)
        self.text('commit')
        self.assertEqual(self.tracker.caret['y'], 800)

    def test_pending_replacement_and_repeated_commit(self):
        self.activate()
        self.text('set_cursor_rectangle', '30, 800, 0, 20')
        self.text('set_cursor_rectangle', '31, 801, 0, 20')
        self.text('commit')
        self.assertEqual(self.tracker.caret['y'], 801)
        self.text('commit')
        self.assertEqual(self.tracker.caret['sequence'], self.tracker.sequence)

    def test_rect_without_enable_never_publishes(self):
        self.text('enter', 'wl_surface#24')
        self.text('set_cursor_rectangle', '29, 90, 0, 20')
        self.text('commit')
        self.assertIsNone(self.tracker.caret)

    def test_disable_invalidates_before_commit(self):
        self.activate()
        self.text('disable')
        self.assertIsNone(self.tracker.caret)
        self.text('commit')
        self.text('enable')
        self.text('commit')
        self.assertIsNone(self.tracker.caret)

    def test_leave_reenter_requires_fresh_geometry(self):
        self.activate()
        self.text('set_cursor_rectangle', '29, 900, 0, 20')
        self.text('leave', 'wl_surface#24')
        self.text('enter', 'wl_surface#25')
        self.text('enable')
        self.text('commit')
        self.assertIsNone(self.tracker.caret)
        self.text('set_cursor_rectangle', '29, 91, 0, 20')
        self.text('commit')
        self.assertEqual(self.tracker.caret['surface'], 25)

    def test_destroy_then_reuse_refused(self):
        self.activate()
        self.text('destroy')
        self.assertIsNone(self.tracker.caret)
        self.text('enter', 'wl_surface#24')
        self.assertIn('generation', self.tracker.error)

    def test_explicit_creation_and_duplicate_creation(self):
        record = ' -> zwp_text_input_manager_v3#28.get_text_input(new id zwp_text_input_v3#29, wl_seat#16)'
        self.feed(record)
        self.activate()
        self.assertIsNotNone(self.tracker.caret)
        self.feed(record)
        self.assertIsNotNone(self.tracker.error)
        self.assertIsNone(self.tracker.caret)

    def test_duplicate_enter_fails_closed(self):
        self.activate()
        self.text('enter', 'wl_surface#24')
        self.assertIsNotNone(self.tracker.error)
        self.assertIsNone(self.tracker.caret)

    def test_multiple_owners_fail_closed(self):
        self.activate()
        self.activate(oid=30, surface=25)
        self.assertIsNotNone(self.tracker.error)
        self.assertIsNone(self.tracker.caret)

    def test_per_object_pending_geometry(self):
        self.activate()
        self.text('enter', 'wl_surface#25', oid=30)
        self.text('enable', oid=30)
        self.text('set_cursor_rectangle', '1, 700, 0, 20', oid=30)
        self.text('commit', oid=29)
        self.assertEqual(self.tracker.caret['y'], 90)

    def test_invalid_rectangles_fail_closed(self):
        for rect in ('0, 0, -1, 20', '0, 0, 0, 0', '0, 0, 0, -1',
                     '16384, 0, 1, 20', '0, 16384, 0, 20',
                     '99999999999999999, 0, 0, 20', 'NaN, 0, 0, 20',
                     '0.5, 0, 0, 20', '0, 0, 20'):
            with self.subTest(rect=rect):
                self.setUp()
                self.activate()
                self.text('set_cursor_rectangle', rect)
                self.assertIsNotNone(self.tracker.error)
                self.assertIsNone(self.tracker.caret)

    def test_exact_prefix_only(self):
        for prefix in (b'FOOT_WAYLAND ', b'DENIAL_DIAGNOSTIC ', b'xEDITOR_WAYLAND ', b'EDITOR_WAYLAND_EXTRA '):
            self.feed('zwp_text_input_v3#29.enter(wl_surface#24)', prefix)
            self.feed(' -> zwp_text_input_v3#29.enable()', prefix)
            self.feed(' -> zwp_text_input_v3#29.set_cursor_rectangle(0, 900, 0, 20)', prefix)
            self.feed(' -> zwp_text_input_v3#29.commit()', prefix)
        self.assertEqual(self.tracker.sequence, 0)
        self.assertIsNone(self.tracker.caret)

    def test_malformed_and_wrong_direction_fail_closed(self):
        for record in (' -> zwp_text_input_v3#29.enter(wl_surface#24)',
                       'zwp_text_input_v3#29.commit()', 'zwp_text_input_v3#29.enter(bad)',
                       'zwp_text_input_v3#29.enter(wl_surface#24) broken'):
            with self.subTest(record=record):
                self.setUp()
                self.feed(record)
                self.assertIsNotNone(self.tracker.error)

    def test_object_and_line_bounds(self):
        self.tracker.MAX_OBJECTS = 2
        for oid in (29, 30, 31):
            self.text('enter', 'wl_surface#24', oid=oid)
        self.assertEqual(len(self.tracker._objects), 2)
        self.assertIsNotNone(self.tracker.error)
        self.setUp()
        self.tracker.feed(b'EDITOR_WAYLAND ' + b'x' * self.tracker.MAX_LINE)
        self.assertIsNotNone(self.tracker.error)

    def test_record_bound_is_terminal(self):
        self.tracker.MAX_RECORDS = 2
        self.activate()
        self.assertEqual(self.tracker.sequence, 3)
        self.assertIsNone(self.tracker.caret)
        self.assertIsNotNone(self.tracker.error)

    def test_numeric_timestamp_without_queue(self):
        for record in (b'zwp_text_input_v3#29.enter(wl_surface#24)',
                       b' -> zwp_text_input_v3#29.enable()',
                       b' -> zwp_text_input_v3#29.set_cursor_rectangle(-2, 90, 0, 20)',
                       b' -> zwp_text_input_v3#29.commit()'):
            self.tracker.feed(b'EDITOR_WAYLAND [ 345.123] ' + record + b'\n')
        self.assertIsNone(self.tracker.error)
        self.assertEqual(self.tracker.caret['x'], -2)

    def test_object_type_collision_refused(self):
        self.text('enter', 'wl_surface#24')
        self.pointer('enter', '1, wl_surface#24, 1, 2', oid=29)
        self.assertIsNotNone(self.tracker.error)

    def test_text_leave_mismatch_refused(self):
        self.activate()
        self.text('leave', 'wl_surface#25')
        self.assertIsNotNone(self.tracker.error)
        self.assertIsNone(self.tracker.caret)

    def test_same_surface_pointer_press_after_action(self):
        self.activate()
        before = self.tracker.sequence
        self.pointer('enter', '6, wl_surface#24, 77.13671875, 704.59765625')
        self.pointer('motion', '249739, 270.49218750, 152.13671875')
        self.pointer('button', '27, 249842, 272, 1')
        press = self.tracker.presses[-1]
        self.assertEqual(press['surface'], self.tracker.caret['surface'])
        self.assertEqual((press['x'], press['y']), (270.49218750, 152.13671875))
        self.assertGreater(press['sequence'], before)
        self.assertNotIn('PASS', str(self.tracker.result()))

    def test_wrong_surface_press_is_not_relabelled(self):
        self.activate()
        self.pointer('enter', '6, wl_surface#25, 1, 2')
        self.pointer('button', '27, 249842, 272, 1')
        self.assertNotEqual(self.tracker.presses[-1]['surface'], self.tracker.caret['surface'])

    def test_commit_after_press_cannot_refresh_old_rectangle(self):
        self.activate()
        original = self.tracker.caret['rectangle_sequence']
        self.pointer('enter', '6, wl_surface#24, 1, 2')
        self.pointer('button', '27, 249842, 272, 1')
        press_sequence = self.tracker.presses[-1]['sequence']
        self.text('commit')
        self.assertGreater(self.tracker.caret['sequence'], press_sequence)
        self.assertEqual(self.tracker.caret['rectangle_sequence'], original)
        self.assertLess(self.tracker.caret['rectangle_sequence'], press_sequence)
        self.text('set_cursor_rectangle', '29, 120, 0, 20')
        self.assertEqual(self.tracker.caret['rectangle_sequence'], original)
        self.text('commit')
        self.assertGreater(self.tracker.caret['rectangle_sequence'], press_sequence)
        self.assertLess(self.tracker.caret['rectangle_sequence'], self.tracker.caret['sequence'])

    def test_leave_clears_pointer_position(self):
        self.pointer('enter', '6, wl_surface#24, 1, 2')
        self.pointer('leave', '7, wl_surface#24')
        self.pointer('motion', '10, 3, 4')
        self.pointer('button', '8, 20, 272, 1')
        self.assertEqual(self.tracker.presses, [])

    def test_duplicate_pointer_press_fails_closed(self):
        self.pointer('enter', '6, wl_surface#24, 1, 2')
        self.pointer('button', '8, 20, 272, 1')
        self.pointer('button', '9, 21, 272, 1')
        self.assertIsNotNone(self.tracker.error)
        self.assertEqual(self.tracker.presses, [])

    def test_invalid_pointer_records_refused(self):
        for method, args in (('motion', '1, nan, 2'), ('motion', '1, 0, 16385'),
                             ('button', '1, 2, 272, 2'), ('leave', '1, wl_surface#25')):
            with self.subTest(method=method, args=args):
                self.setUp()
                self.pointer('enter', '6, wl_surface#24, 1, 2')
                self.pointer(method, args)
                self.assertIsNotNone(self.tracker.error)

    def test_pointer_release_prevents_generation_reuse(self):
        self.pointer('enter', '6, wl_surface#24, 1, 2')
        self.feed(' -> wl_pointer#15.release()')
        self.pointer('enter', '7, wl_surface#24, 2, 3')
        self.assertIsNotNone(self.tracker.error)

    def test_press_retention_is_bounded(self):
        self.pointer('enter', '6, wl_surface#24, 1, 2')
        for _ in range(self.tracker.MAX_PRESSES + 10):
            self.pointer('button', '8, 20, 272, 1')
            self.pointer('button', '9, 21, 272, 0')
        self.assertIsNone(self.tracker.error)
        self.assertEqual(len(self.tracker.presses), self.tracker.MAX_PRESSES)

    def test_geometry_waits_for_matching_surface_commit(self):
        self.geometry()
        self.assertEqual(self.tracker.geometries, {})
        self.feed(' -> wl_surface#25.commit()')
        self.assertEqual(self.tracker.geometries, {})
        self.feed(' -> wl_surface#24.commit()')
        self.assertEqual(self.tracker.geometries[24], dict(x=26, y=23, width=540, height=1176, sequence=4))
        self.feed(' -> xdg_surface#26.set_window_geometry(26, 23, 540, 900)')
        self.assertEqual(self.tracker.geometries[24]['height'], 1176)
        self.feed(' -> wl_surface#24.commit()')
        self.assertEqual(self.tracker.geometries[24]['height'], 900)

    def test_surface_destroy_invalidates_all_evidence(self):
        self.geometry()
        self.feed(' -> wl_surface#24.commit()')
        self.activate()
        self.pointer('enter', '6, wl_surface#24, 1, 2')
        self.pointer('button', '8, 20, 272, 1')
        self.feed(' -> wl_surface#24.destroy()')
        self.assertIsNone(self.tracker.caret)
        self.assertEqual(self.tracker.geometries, {})
        self.assertEqual(self.tracker.presses, [])
        self.text('enter', 'wl_surface#24')
        self.assertIsNotNone(self.tracker.error)

    def test_xdg_destroy_discards_pending_geometry(self):
        self.geometry()
        self.feed(' -> xdg_surface#26.destroy()')
        self.feed(' -> wl_surface#24.commit()')
        self.assertEqual(self.tracker.geometries, {})
        self.assertIsNone(self.tracker.error)

    def test_geometry_ambiguity_and_bounds_refused(self):
        for record in (' -> xdg_surface#26.set_window_geometry(0, 0, 0, 20)',
                       ' -> xdg_surface#26.set_window_geometry(0, 16380, 20, 20)',
                       ' -> xdg_surface#27.set_window_geometry(0, 0, 20, 20)',
                       ' -> xdg_wm_base#4.get_xdg_surface(new id xdg_surface#27, wl_surface#24)'):
            with self.subTest(record=record):
                self.setUp()
                self.geometry()
                self.feed(' -> wl_surface#24.commit()')
                self.feed(record)
                self.assertIsNotNone(self.tracker.error)
                self.assertEqual(self.tracker.geometries, {})

    def test_actual_retained_log_excerpt(self):
        # Verbatim lines retained from the read-only combined-r1 editor log.
        lines = b'''EDITOR_WAYLAND [00:03:30.024439] {Default Queue}  -> wl_seat#16.get_pointer(new id wl_pointer#15)
EDITOR_WAYLAND [00:03:49.336874] {Default Queue}  -> zwp_text_input_manager_v3#28.get_text_input(new id zwp_text_input_v3#29, wl_seat#16)
EDITOR_WAYLAND [00:03:49.531162] {Default Queue} zwp_text_input_v3#29.enter(wl_surface#24)
EDITOR_WAYLAND [00:03:49.531332] {Default Queue}  -> zwp_text_input_v3#29.enable()
EDITOR_WAYLAND [00:03:49.533702] {Default Queue}  -> zwp_text_input_v3#29.set_surrounding_text("", 0, 0)
EDITOR_WAYLAND [00:03:49.534589] {Default Queue}  -> zwp_text_input_v3#29.set_cursor_rectangle(29, 90, 0, 20)
EDITOR_WAYLAND [00:03:49.534730] {Default Queue}  -> zwp_text_input_v3#29.commit()
EDITOR_WAYLAND [00:03:49.806947] {Default Queue} wl_pointer#15.enter(6, wl_surface#24, 77.13671875, 704.59765625)
EDITOR_WAYLAND [00:03:49.807657] {Default Queue} wl_pointer#15.frame()
EDITOR_WAYLAND [00:03:52.061460] {Default Queue} wl_pointer#15.leave(7, wl_surface#24)
EDITOR_WAYLAND [00:03:58.980942] {Default Queue} zwp_text_input_v3#29.leave(wl_surface#24)
EDITOR_WAYLAND [00:03:58.981209] {Default Queue}  -> zwp_text_input_v3#29.disable()
EDITOR_WAYLAND [00:03:58.981274] {Default Queue}  -> zwp_text_input_v3#29.commit()
'''
        for line in lines.splitlines(keepends=True):
            self.tracker.feed(line)
        self.assertIsNone(self.tracker.error)
        self.assertIsNone(self.tracker.caret)
        self.assertEqual(self.tracker.sequence, 13)


if __name__ == '__main__':
    unittest.main()
