#!/usr/bin/env python3
"""Run the shipped screen helper against temporary hardware and process peers."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(__file__).with_name('screen-toggle.sh')


class Screen(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='rog5-screen-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.panel = self.root / 'panel'
        self.panel.mkdir()
        (self.panel / 'brightness').write_text('500\n')
        (self.panel / 'max_brightness').write_text('1000\n')
        self.state = self.root / 'state'
        self.helper = self.root / 'helper'
        self.log = self.root / 'calls'
        self.env = dict(os.environ, STATE_FILE=str(self.state),
                        BRIGHTNESS_FILE=str(self.root / 'saved'),
                        BACKLIGHT_DIR=str(self.panel), DISPLAY_PROFILE=str(self.helper),
                        STATUS_SCREEN=str(self.root / 'absent-status'),
                        DPMS_STATE_FILE=str(self.root / 'dpms'),
                        DISPLAY_POWER_MODE='auto')
        self.peer()

    def peer(self, code=0, delay=0, report=True):
        self.helper.write_text(
            '#!/bin/sh\n'
            f'printf "%s\\n" "$1" >>"{self.log}"\n'
            f'sleep {delay}\n'
            + (f'printf "%s\\n" "${{1#dpms-}}" >"{self.root / "dpms"}"\n'
               if report and not code else '')
            + f'exit {code}\n')
        self.helper.chmod(0o700)

    def run_action(self, action='toggle'):
        return subprocess.run(['sh', str(SCRIPT), action], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def test_requested_off_helper_failure_is_not_success(self):
        self.peer(42)
        result = self.run_action('off')
        self.assertEqual(result.returncode, 42, result)
        self.assertNotIn('Screen off', result.stdout)
        self.assertNotEqual(self.state.read_text().strip(), 'off')

    def test_requested_on_helper_failure_is_not_success(self):
        (self.panel / 'brightness').write_text('0\n')
        self.peer(42)
        result = self.run_action('on')
        self.assertEqual(result.returncode, 42, result)
        self.assertEqual((self.panel / 'brightness').read_text().strip(), '0')
        self.assertNotEqual(self.state.read_text().strip(), 'on')

    def test_missing_optional_helper_is_explicit_backlight_only(self):
        self.helper.unlink()
        result = self.run_action('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('backlight-only', result.stdout)
        self.assertIn('display-power=NOT_RUN', result.stdout)

    def test_required_helper_absence_refuses_before_backlight_change(self):
        self.helper.unlink()
        self.env['DISPLAY_POWER_MODE'] = 'required'
        result = self.run_action('off')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.panel / 'brightness').read_text().strip(), '500')

    def test_explicit_backlight_mode_does_not_invoke_installed_helper(self):
        self.env['DISPLAY_POWER_MODE'] = 'backlight-only'
        self.peer(42)
        result = self.run_action('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())
        self.assertIn('backlight-only', result.stdout)

    def test_backlight_only_toggle_ignores_uncontrolled_dpms(self):
        for optional_helper_absent in (False, True):
            with self.subTest(optional_helper_absent=optional_helper_absent):
                self.env['DISPLAY_POWER_MODE'] = ('auto' if optional_helper_absent
                                                  else 'backlight-only')
                if optional_helper_absent:
                    self.helper.unlink()
                (self.root / 'dpms').write_text('Off\n')
                (self.panel / 'brightness').write_text('500\n')
                result = self.run_action()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.panel / 'brightness').read_text().strip(), '0')
                self.assertIn('backlight=off scope=backlight-only', result.stdout)
                result = self.run_action()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.panel / 'brightness').read_text().strip(), '500')
                self.assertFalse(self.log.exists())

    def test_stale_cache_is_reconciled_to_brightness(self):
        self.helper.unlink()
        self.state.write_text('off\n')
        result = self.run_action()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.panel / 'brightness').read_text().strip(), '0')

    def test_reported_dpms_off_is_used_when_brightness_is_stale(self):
        (self.root / 'dpms').write_text('Off\n')
        result = self.run_action()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text(), 'dpms-on\n')

    def test_helper_acknowledgment_is_not_verified_power(self):
        self.peer(report=False)
        result = self.run_action('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('display-power=UNVERIFIED', result.stdout)

    def test_matching_reported_power_is_distinguished(self):
        result = self.run_action('off')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('display-power=reported-off', result.stdout)

    def test_wrong_reported_power_refuses(self):
        (self.root / 'dpms').write_text('On\n')
        self.peer(report=False)
        result = self.run_action('off')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state.read_text().strip(), 'unknown')

    def test_concurrent_toggles_serialize_read_and_write(self):
        self.peer(delay=.2)
        children = [subprocess.Popen(['sh', str(SCRIPT), 'toggle'], env=self.env,
                                    text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE) for _ in range(2)]
        for child in children:
            out, err = child.communicate(timeout=10)
            self.assertEqual(child.returncode, 0, (out, err))
        self.assertEqual(self.log.read_text(), 'dpms-off\ndpms-on\n')
        self.assertEqual((self.panel / 'brightness').read_text().strip(), '500')

    def test_interrupted_transition_leaves_unknown_and_next_run_reconciles(self):
        self.peer(delay=5)
        child = subprocess.Popen(['sh', str(SCRIPT), 'off'], env=self.env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        try:
            until = time.monotonic() + 3
            while not self.log.exists() and time.monotonic() < until:
                time.sleep(.01)
            self.assertTrue(self.log.exists())
            os.killpg(child.pid, signal.SIGKILL)
            child.communicate(timeout=3)
            self.assertEqual(self.state.read_text().strip(), 'unknown')
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate(timeout=3)
        self.peer()
        result = self.run_action()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state.read_text().strip(), 'on')


if __name__ == '__main__':
    unittest.main(verbosity=2)
