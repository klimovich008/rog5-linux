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
                      'Unhandled Exception', 'Could not create the embedder backing store'):
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
