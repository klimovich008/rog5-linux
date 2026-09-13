#!/usr/bin/env python3
"""Execute the production guest helpers with inert host subprocesses."""
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'tools/qemu-virtio-drm/launcher-apps.sh'


class LauncherApps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rog5-launcher-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.desktops = self.root / 'desktops'
        self.desktops.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.prefix = f'source {shlex.quote(str(HELPER))}; launcher_guest_guard() {{ :; }}; '
        for name, exe in [('org.xfce.mousepad.desktop', 'mousepad %U'), ('foot.desktop', 'foot')]:
            (self.desktops / name).write_text('[Desktop Entry]\nName=Fixture\nExec=' + exe + '\n[Desktop Action preferences]\nExec=untouched\n')

    def command(self, cmd, check=True):
        return subprocess.run(['bash', '-c', self.prefix + cmd], capture_output=True, text=True, timeout=8, check=check)

    def prepare(self):
        return self.command(f'launcher_apps_prepare {self.state} {self.desktops} /run/launcher-apps.sh {self.root}/text; echo "$XDG_DATA_HOME"')

    def run_app(self, app='mousepad', body='echo hello; exit 0'):
        (self.bin / app).write_text('#!/usr/bin/env bash\n' + body + '\n')
        (self.bin / app).chmod(0o700)
        return self.command(f'export WAYLAND_DISPLAY=wayland-1; launcher_app_run {app} {self.state} {self.bin}', check=False)

    def test_prepare_only_replaces_main_exec_and_launches_nothing(self):
        result = self.prepare()
        self.assertIn(str(self.state / 'data'), result.stdout)
        self.assertFalse((self.state / 'mousepad').exists())
        self.assertEqual((self.root / 'text').read_bytes(), b'')
        for name, app in [('org.xfce.mousepad.desktop', 'mousepad'), ('foot.desktop', 'foot')]:
            data = (self.state / 'data/applications' / name).read_text()
            self.assertIn(f'Exec=/usr/bin/bash /run/launcher-apps.sh launch {app}\n', data)
            self.assertIn('[Desktop Action preferences]\nExec=untouched\n', data)
        self.command(f'launcher_apps_cleanup {self.state}')

    def test_duplicate_prepare_refused(self):
        self.prepare()
        result = self.command(f'launcher_apps_prepare {self.state} {self.desktops}', check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_ambiguous_desktop_refused(self):
        (self.desktops / 'foot.desktop').write_text('[Desktop Entry]\nExec=foot\nExec=another\n')
        result = self.command(f'launcher_apps_prepare {self.state} {self.desktops}', check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_cli_guard_and_unknown_app(self):
        result = subprocess.run(['bash', str(HELPER), 'launch', 'mousepad'], capture_output=True, timeout=3)
        self.assertNotEqual(result.returncode, 0)
        self.prepare()
        result = self.run_app('unknown')
        self.assertNotEqual(result.returncode, 0)

    def test_real_app_receives_wayland_environment_and_fixed_file(self):
        self.prepare()
        result = self.run_app(body='printf "%s %s %s %s\\n" "$GDK_BACKEND" "$WAYLAND_DEBUG" "$WAYLAND_DISPLAY" "$1"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('EDITOR_WAYLAND wayland client wayland-1 /tmp/rog5-text-probe.txt', result.stdout)
        self.assertTrue((self.state / 'mousepad/finished').exists())
        self.assertEqual((self.state / 'mousepad/exit-status').read_text(), '0\n')
        self.assertNotEqual(self.run_app().returncode, 0)

    def test_explicit_serial_sink_survives_denial_null_stdio(self):
        self.prepare()
        sink = self.root / 'serial'
        sink.touch()
        (self.bin / 'foot').write_text('#!/usr/bin/env bash\necho native-protocol-event >&2\n')
        (self.bin / 'foot').chmod(0o700)
        cmd = self.prefix + f'export WAYLAND_DISPLAY=wayland-1; launcher_app_run foot {self.state} {self.bin} {sink}'
        result = subprocess.run(['bash', '-c', cmd], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=3)
        self.assertEqual(result.returncode, 0)
        self.assertIn('FOOT_WAYLAND native-protocol-event', sink.read_text())
        self.assertIn('OBSERVE launcher app=foot', sink.read_text())

    def test_original_app_failure_propagated(self):
        self.prepare()
        result = self.run_app('foot', 'echo failure >&2; exit 42')
        self.assertEqual(result.returncode, 42)
        self.assertIn('FOOT_WAYLAND failure', result.stdout)
        self.assertEqual((self.state / 'foot/exit-status').read_text(), '42\n')

    def test_log_is_bounded_without_terminating_writer(self):
        self.prepare()
        result = self.run_app(body="awk 'BEGIN { for(i=0;i<20000;i++) print \"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\" }'; exit 0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('FAIL launcher client log limit', result.stdout)
        self.assertLess(len(result.stdout.encode()), 1049000)

    def test_stale_identity_never_signals_unrelated_process(self):
        self.prepare()
        victim = subprocess.Popen(['sleep', '30'])
        self.addCleanup(lambda: victim.poll() is None and victim.kill())
        (self.state / 'foot').mkdir()
        (self.state / 'foot/owner').write_text(f'{victim.pid} 0\n')
        result = self.command(f'launcher_apps_cleanup {self.state}', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PASS launcher apps cleanup', result.stdout)
        self.assertIsNone(victim.poll())
        self.assertIn('stale launcher owner', result.stderr)
        victim.terminate()
        victim.wait(timeout=2)

    def test_cleanup_owns_separate_session_and_term_ignoring_child(self):
        self.prepare()
        child_pidfile = self.root / 'child'
        (self.bin / 'foot').write_text(f'#!/usr/bin/env bash\ntrap "" TERM\necho $$ > {child_pidfile}\nwhile :; do sleep 1; done\n')
        (self.bin / 'foot').chmod(0o700)
        cmd = self.prefix + f'export WAYLAND_DISPLAY=wayland-1; launcher_app_run foot {self.state} {self.bin}'
        process = subprocess.Popen(['bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        def emergency_cleanup():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
        self.addCleanup(emergency_cleanup)
        until = time.monotonic() + 2
        while not child_pidfile.exists() and time.monotonic() < until:
            time.sleep(.02)
        self.assertTrue(child_pidfile.exists())
        child = int(child_pidfile.read_text())
        result = self.command(f'launcher_apps_cleanup {self.state}')
        self.assertNotIn('deadline', result.stderr)
        process.communicate(timeout=3)
        self.assertTrue((self.state / 'foot/finished').exists())
        # The supervisor reaps timeout; orphaned killed client may briefly be a
        # zombie under container PID 1, but must never still execute.
        proc = Path(f'/proc/{child}/stat')
        self.assertTrue(not proc.exists() or proc.read_text().rsplit(') ', 1)[1].startswith('Z '))
        self.command(f'launcher_apps_cleanup {self.state}')


if __name__ == '__main__':
    unittest.main()
