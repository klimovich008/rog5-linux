#!/usr/bin/env python3
"""Exercise the actual guest prerequisite selection with bounded file fixtures."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import os
import stat

SPEC = importlib.util.spec_from_file_location(
    'guest', Path(__file__).with_name('test-qemu-virtio-drm.py'))
GUEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUEST)


class RuntimePrerequisites(unittest.TestCase):
    @staticmethod
    def editor_log():
        return '\n'.join([
            '[100.01] -> xdg_wm_base#2.get_xdg_surface(new id xdg_surface#3, wl_surface#4)',
            '[100.02] -> xdg_surface#3.get_toplevel(new id xdg_toplevel#5)',
            '[100.03] -> xdg_toplevel#5.set_title("rog5-text-probe.txt - Mousepad")',
            *[f'[101.00] wl_keyboard#6.key({index}, 1000, {key}, {state})'
              for index, (key, state) in enumerate([
                  (20, 1), (20, 0), (18, 1), (18, 0), (31, 1), (31, 0),
                  (20, 1), (20, 0), (14, 1), (14, 0), (20, 1), (20, 0)])],
        ])

    def test_editor_protocol_accepts_exact_native_key_lifecycles_and_ansi(self):
        log = self.editor_log()
        for text in (log, log.replace('#', '@'), '\x1b[32m' + log + '\x1b[0m'):
            with self.subTest(text=text[:40]):
                result = GUEST.editor_result(text)
                self.assertEqual(result['status'], 'PASS')
                self.assertTrue(result['native_toplevel_observed'])
                self.assertEqual(result['keys'], [
                    (20, 1), (20, 0), (18, 1), (18, 0), (31, 1), (31, 0),
                    (20, 1), (20, 0), (14, 1), (14, 0), (20, 1), (20, 0)])
                self.assertIn('visual text checked separately', result['scope'])

    def test_editor_protocol_requires_toplevel_and_exact_probe_title(self):
        lines = self.editor_log().splitlines()
        invalid = ['', '\n'.join(lines[3:]), '\n'.join(lines[:3]),
                   self.editor_log().replace('rog5-text-probe.txt', 'unrelated.txt')]
        invalid += ['\n'.join(lines[:index] + lines[index + 1:]) for index in range(3)]
        for text in invalid:
            with self.subTest(text=text[:70]):
                self.assertEqual(GUEST.editor_result(text)['status'], 'FAIL')

    def test_editor_protocol_rejects_extra_missing_wrong_and_unbalanced_keys(self):
        lines = self.editor_log().splitlines()
        invalid = [
            '\n'.join(lines + [lines[-1]]),
            '\n'.join(lines[:-1]),
            '\n'.join(lines[:3] + lines[5:7] + lines[3:5] + lines[7:]),
            self.editor_log().replace('1000, 18,', '1000, 19,'),
            self.editor_log().replace('1000, 14, 0)', '1000, 14, 1)'),
        ]
        for text in invalid:
            with self.subTest(text=text[-90:]):
                self.assertEqual(GUEST.editor_result(text)['status'], 'FAIL')

    def test_egl_comparison_requires_all_modes_and_observations(self):
        lines = []
        for mode in ('exit', 'unbind', 'release'):
            lines += [f'EGL_THREAD mode={mode} stage=live-collision ok=0 error=0x3002',
                      f'EGL_THREAD mode={mode} stage=after-join ok=1 error=0x3000',
                      f'PASS EGL thread probe mode={mode}']
        log = '\n'.join(lines)
        self.assertEqual(GUEST.egl_thread_result(log)['status'], 'PASS')
        exit_failed = log.replace('mode=exit stage=after-join ok=1 error=0x3000',
                                 'mode=exit stage=after-join ok=0 error=0x3002')
        result = GUEST.egl_thread_result(exit_failed)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['after_join']['exit']['acquired'])
        for bad in ('', log+'\n'+lines[-1], log.replace(lines[0], ''),
                    log.replace('mode=unbind stage=after-join ok=1 error=0x3000',
                                'mode=unbind stage=after-join ok=0 error=0x3002'),
                    log.replace('stage=live-collision ok=0 error=0x3002',
                                'stage=live-collision ok=1 error=0x3000'),
                    log+'\nFAIL EGL thread probe: cleanup'):
            self.assertEqual(GUEST.egl_thread_result(bad)['status'], 'FAIL')

    def test_mobile_readiness_requires_real_presentation(self):
        for text in ('', 'Flutter per-output render audit presented_outputs=0',
                     'Flutter per-output render audit presented_outputs=1',
                     'Denial/Volition output scheduler audit presentations=0',
                     'unrelated presentations=1',
                     'Denial/Volition output scheduler audit presentations=1 presentations=0'):
            self.assertFalse(GUEST.mobile_ready(text.encode()))
        text = 'Denial/Volition output scheduler audit \x1b[3mpresentations\x1b[0m=2 ready_with_fence=2'
        self.assertTrue(GUEST.mobile_ready(text.encode()))

    def test_shell_requires_xwayland_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'usr/bin').mkdir(parents=True)
            for name in ('bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout',
                         'modetest', 'seatd', 'seatd-launch', 'sleep', 'dbus-daemon'):
                (root/'usr/bin'/name).touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), ['usr/bin/Xwayland'])
            self.assertEqual(GUEST.missing_runtime_inputs(root, False), [])
            (root/'usr/bin/Xwayland').touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), [])
            (root/'usr/bin/modetest').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), ['usr/bin/modetest'])

    def test_mobile_requires_udev_tools_and_input_identification_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'usr/bin').mkdir(parents=True)
            for name in ('bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout',
                         'modetest', 'seatd', 'sleep', 'Xwayland', 'dbus-daemon'):
                (root / 'usr/bin' / name).touch()
            mandatory = ['usr/bin/udevadm', 'usr/lib/systemd/systemd-udevd',
                         'usr/lib/udev/rules.d/60-input-id.rules']
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), [])
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=False), [])
            self.assertCountEqual(GUEST.missing_runtime_inputs(root, True, mobile=True),
                                  mandatory)
            for relative in mandatory:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True), [])
            for relative in mandatory:
                with self.subTest(missing=relative):
                    path = root / relative
                    path.unlink()
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True),
                                     [relative])
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=False), [])
                    path.touch()
            (root / 'usr/bin/Xwayland').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True),
                             ['usr/bin/Xwayland'])

    def test_native_editor_requires_mousepad_without_changing_default_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            required = ('usr/bin/' + name for name in (
                'bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout', 'modetest',
                'seatd', 'sleep', 'Xwayland', 'dbus-daemon', 'udevadm'))
            for relative in (*required, 'usr/lib/systemd/systemd-udevd',
                             'usr/lib/udev/rules.d/60-input-id.rules'):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            for mobile in (False, True):
                with self.subTest(mobile=mobile):
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=mobile), [])
                    self.assertEqual(GUEST.missing_runtime_inputs(
                        root, True, mobile=mobile, editor=False), [])
                    self.assertEqual(GUEST.missing_runtime_inputs(
                        root, True, mobile=mobile, editor=True), ['usr/bin/mousepad'])
            editor = root / 'usr/bin/mousepad'
            editor.mkdir()
            self.assertEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), ['usr/bin/mousepad'])
            editor.rmdir()
            editor.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), [])
            (root / 'usr/bin/Xwayland').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), ['usr/bin/Xwayland'])
            editor.unlink()
            self.assertCountEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), ['usr/bin/Xwayland', 'usr/bin/mousepad'])
            self.assertEqual(GUEST.missing_runtime_inputs(root, False), [])

    def test_actual_zero_frame_summary_is_failure(self):
        line = ('independently clocked Flutter KMS session complete '
                '\x1b[3mraster_frames\x1b[0m\x1b[2m=\x1b[0m0 '
                'output_page_flips=0 delivered_vsyncs=1\n'
                'PASS actual deniald shell bounded exit\n')
        result = GUEST.session_result(line)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['raster_frames'], 0)
        self.assertEqual(result['output_page_flips'], 0)

    def test_positive_counters_require_no_render_errors(self):
        line = ('independently clocked Flutter KMS session complete '
                'raster_frames=3 output_page_flips=2')
        self.assertEqual(GUEST.session_result(line)['status'], 'PASS')
        for error in ('required Flutter native fence export failed',
                      'Unhandled Exception', 'Could not create the embedder backing store',
                      'Could not make the context current to destroy Impeller surface resources.',
                      'Could not clear the context after Impeller surface cleanup.',
                      'Could not clear the Impeller IO resource context.'):
            self.assertEqual(GUEST.session_result(line+'\n'+error)['status'], 'FAIL')

    def test_missing_duplicate_and_incomplete_counters_fail(self):
        line = ('independently clocked Flutter KMS session complete '
                'raster_frames=3 output_page_flips=2')
        for log in ('', line+'\n'+line, line.replace('output_page_flips=2', ''),
                    line+' raster_frames=4'):
            self.assertEqual(GUEST.session_result(log)['status'], 'FAIL')

    def test_virgl_rejects_primary_block_regular_and_symlink_nodes(self):
        for path in ('/dev/dri/card0', '/dev/sda', '/tmp/renderD128'):
            with self.assertRaises(ValueError):
                GUEST.render_node_identity(Path(path))
        for mode, major, minor in ((stat.S_IFREG, 226, 128), (stat.S_IFLNK, 226, 128),
                                   (stat.S_IFCHR, 8, 128), (stat.S_IFCHR, 226, 0)):
            with patch.object(Path, 'lstat', return_value=SimpleNamespace(
                    st_mode=mode, st_rdev=os.makedev(major, minor))):
                with self.assertRaises(ValueError):
                    GUEST.render_node_identity(Path('/dev/dri/renderD128'))
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(
                st_mode=stat.S_IFCHR, st_rdev=os.makedev(226, 128))):
            self.assertEqual(GUEST.render_node_identity(Path('/dev/dri/renderD128'))['minor'], 128)


if __name__ == '__main__':
    unittest.main()
