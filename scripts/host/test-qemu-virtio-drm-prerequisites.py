#!/usr/bin/env python3
"""Exercise the actual guest prerequisite selection with bounded file fixtures."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    'guest', Path(__file__).with_name('test-qemu-virtio-drm.py'))
GUEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUEST)


class RuntimePrerequisites(unittest.TestCase):
    def test_shell_requires_xwayland_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'usr/bin').mkdir(parents=True)
            for name in ('bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout',
                         'modetest', 'seatd', 'seatd-launch', 'sleep'):
                (root/'usr/bin'/name).touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), ['usr/bin/Xwayland'])
            self.assertEqual(GUEST.missing_runtime_inputs(root, False), [])
            (root/'usr/bin/Xwayland').touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), [])
            (root/'usr/bin/modetest').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), ['usr/bin/modetest'])


if __name__ == '__main__':
    unittest.main()
