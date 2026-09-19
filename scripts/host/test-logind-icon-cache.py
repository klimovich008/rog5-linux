#!/usr/bin/env python3
"""Actual cache generation plus syscall-boundary failure injection; no device."""
from pathlib import Path
import os
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT/'tools/qemu-virtio-drm/logind-icon-cache.sh'

class Fixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-icon-cache-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'source'; self.source.mkdir()
        self.output = self.root/'output'; self.output.mkdir()
        self.bin = self.root/'bin'; self.bin.mkdir()
        self.theme = self.source/'Test'; (self.theme/'scalable/apps').mkdir(parents=True)
        (self.theme/'index.theme').write_text('[Icon Theme]\nName=Test\nDirectories=scalable/apps\n[scalable/apps]\nSize=48\nType=Scalable\nContext=Applications\n')
        (self.theme/'scalable/apps/test.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"/>')
        (self.theme/'scalable/apps/alias.svg').symlink_to('test.svg')
        self.cmd = ['bash', '-c', 'source "$1"; generate_icon_caches "$2"',
                    'icon-test', str(HELPER), str(self.source)]
        self.env = dict(os.environ, LC_ALL='C', PATH=str(self.bin)+':'+os.environ['PATH'])

    def command(self, name, code):
        tool = self.bin/name
        tool.write_text('#!/bin/bash\nset -eu\n'+code); tool.chmod(0o755)

    def run_helper(self):
        return subprocess.run(self.cmd, env=self.env, capture_output=True, text=True, timeout=15)

class IconCache(Fixture, unittest.TestCase):
    def test_real_cache_is_valid_and_assets_unchanged(self):
        before = (self.theme/'index.theme').stat()
        icon = (self.theme/'scalable/apps/test.svg').read_bytes()
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertEqual((self.theme/'index.theme').stat(), before)
        self.assertEqual((self.theme/'scalable/apps/test.svg').read_bytes(), icon)
        self.assertEqual(os.readlink(self.theme/'scalable/apps/alias.svg'), 'test.svg')
        self.assertGreaterEqual((self.theme/'icon-theme.cache').stat().st_mtime_ns, self.theme.stat().st_mtime_ns)
        subprocess.run(['gtk-update-icon-cache', '--validate', str(self.theme)], check=True, capture_output=True)

    def test_inheritance_only_default_needs_no_cache(self):
        alias = self.source/'default'; alias.mkdir()
        (alias/'index.theme').write_text('[Icon Theme]\nInherits=Test\n')
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertFalse((alias/'icon-theme.cache').exists())
        self.assertTrue((self.theme/'icon-theme.cache').is_file())

    def test_no_theme_is_failure(self):
        (self.theme/'index.theme').unlink()
        self.assertNotEqual(self.run_helper().returncode, 0)

    def test_old_cache_link_cannot_modify_original(self):
        retained = self.root/'retained'; retained.write_text('retained')
        (self.theme/'icon-theme.cache').symlink_to(retained)
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(retained.read_text(), 'retained')
        self.assertFalse((self.theme/'icon-theme.cache').is_symlink())

    def test_tool_failure_propagates(self):
        self.command('gtk-update-icon-cache', 'exit 42\n')
        self.assertEqual(self.run_helper().returncode, 42)

    def test_success_without_cache_is_rejected(self):
        self.command('gtk-update-icon-cache', 'exit 0\n')
        self.assertNotEqual(self.run_helper().returncode, 0)

    def test_invalid_cache_is_rejected(self):
        self.command('gtk-update-icon-cache', 'if [[ $1 == -q ]]; then echo invalid > "$2/icon-theme.cache"; else exec /usr/bin/gtk-update-icon-cache "$@"; fi\n')
        self.assertNotEqual(self.run_helper().returncode, 0)

    def test_interruption_stops_query(self):
        marker = self.root/'started'
        self.command('gtk-update-icon-cache', 'echo $$ > "$MARKER"\nsleep 10\n')
        self.env['MARKER'] = str(marker)
        p = subprocess.Popen(self.cmd, env=self.env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
        try:
            deadline = time.monotonic()+3
            while not marker.exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(marker.exists())
            os.killpg(p.pid, signal.SIGTERM); p.communicate(timeout=3)
            self.assertNotEqual(p.returncode, 0)
            with self.assertRaises(ProcessLookupError): os.kill(int(marker.read_text()), 0)
        finally:
            if p.poll() is None: os.killpg(p.pid, signal.SIGKILL); p.wait()

class IconMount(Fixture, unittest.TestCase):
    """Production ownership/rollback; fake only mount syscalls, never GTK."""
    def setUp(self):
        super().setUp()
        self.env.update(STATE=str(self.root/'mounted'), SOURCE=str(self.source),
                        MODE='success', CALLS=str(self.root/'calls'))
        self.cmd = ['bash', '-c', 'source "$1"; prepare_icon_mount "$2" "$3"',
                    'mount-test', str(HELPER), str(self.source), str(self.output)]
        self.command('mountpoint', 'if [[ ${@: -1} == \"$SOURCE\" ]]; then [[ -f $STATE ]]; else [[ -f $STATE.overlay ]]; fi && exit 0 || exit 32\n')
        self.command('mount', '''echo "$*" >> "$CALLS"
if [[ $1 == -t ]]; then
 [[ $MODE != overlay-fail ]] || exit 41
 cp -a "$SOURCE/." "${@: -1}/"
 touch "$STATE.overlay"
elif [[ $1 == --bind ]]; then
 [[ $MODE != bind-fail ]] || exit 42
 touch "$STATE"
else
 [[ $MODE != remount-fail ]] || exit 43
fi
''')
        self.command('findmnt', '[[ $MODE != writable ]] && echo ro,nodev,nosuid,noexec || echo rw\n')
        self.command('umount', '[[ $MODE != unmount-fail ]] || exit 44\necho "umount $*" >> "$CALLS"\nif [[ ${@: -1} == "$SOURCE" ]]; then rm "$STATE"; else rm "$STATE.overlay"; fi\n')

    def test_mount_success_only_cache_outputs_change(self):
        r=self.run_helper(); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertFalse((self.theme/'icon-theme.cache').exists())
        self.assertTrue((self.root/'mounted').exists())
        self.assertFalse((self.output/'.icons.lock').exists())
        self.assertIn('remount,bind,ro,nodev,nosuid,noexec',(self.root/'calls').read_text())

    def test_failures_clean_owned_mounts_and_scratch(self):
        for mode,code in [('overlay-fail',41),('bind-fail',42),('remount-fail',43),('writable',1)]:
            with self.subTest(mode=mode):
                self.env['MODE']=mode
                r=self.run_helper();self.assertEqual(r.returncode,code,r.stdout+r.stderr)
                self.assertFalse((self.root/'mounted').exists())
                self.assertEqual(list(self.output.iterdir()),[])
                self.assertFalse((self.theme/'icon-theme.cache').exists())

    def test_unmount_failure_retains_backing_scratch(self):
        self.env['MODE']='unmount-fail'
        r=self.run_helper(); self.assertEqual(r.returncode,44,r.stdout+r.stderr)
        self.assertTrue((self.root/'mounted').exists())
        self.assertTrue((self.root/'mounted.overlay').exists())
        scratch=list(self.output.glob('.icons.*'))
        self.assertEqual(len(scratch),1)
        self.assertTrue((scratch[0]/'merged/Test/icon-theme.cache').is_file())
        self.assertIn('FAIL icon overlay cleanup',r.stderr)

    def test_existing_mount_is_preserved(self):
        (self.root/'mounted').touch()
        self.assertNotEqual(self.run_helper().returncode,0)
        self.assertTrue((self.root/'mounted').exists())
        self.assertFalse((self.root/'calls').exists())

    def test_generation_error_never_binds(self):
        self.command('gtk-update-icon-cache','exit 42\n')
        self.assertEqual(self.run_helper().returncode,42)
        self.assertNotIn('--bind',(self.root/'calls').read_text())
        self.assertEqual(list(self.output.iterdir()),[])

if __name__ == '__main__': unittest.main()
