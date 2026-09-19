#!/usr/bin/env python3
"""Exercise the production icon preparation with real files and GTK cache tool."""
from pathlib import Path
import os
import signal
import time
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT/'tools/qemu-virtio-drm/logind-icon-cache.sh'

class IconCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-icon-cache-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'source'; self.source.mkdir()
        self.output = self.root/'output'; self.output.mkdir()
        self.theme = self.source/'Test'; (self.theme/'scalable/apps').mkdir(parents=True)
        (self.theme/'index.theme').write_text('[Icon Theme]\nName=Test\nDirectories=scalable/apps\n[scalable/apps]\nSize=48\nType=Scalable\nContext=Applications\n')
        (self.theme/'scalable/apps/test.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"/>')
        (self.theme/'scalable/apps/alias.svg').symlink_to('test.svg')
        self.cmd = ['bash', '-c', 'source "$1"; prepare_icon_tree "$2" "$3"',
                    'icon-test', str(HELPER), str(self.source), str(self.output)]
        self.env = dict(os.environ, LC_ALL='C')

    def run_helper(self):
        return subprocess.run(self.cmd, env=self.env, capture_output=True, text=True, timeout=15)

    def test_real_cache_is_valid_and_original_is_unchanged(self):
        before = (self.theme/'index.theme').stat()
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        new = self.output/'icons/Test'
        self.assertFalse((self.theme/'icon-theme.cache').exists())
        self.assertEqual((self.theme/'index.theme').stat(), before)
        self.assertEqual((new/'scalable/apps/test.svg').read_bytes(), (self.theme/'scalable/apps/test.svg').read_bytes())
        self.assertEqual(os.readlink(new/'scalable/apps/alias.svg'), 'test.svg')
        self.assertGreaterEqual((new/'icon-theme.cache').stat().st_mtime_ns, new.stat().st_mtime_ns)
        subprocess.run(['gtk-update-icon-cache', '--validate', str(new)], check=True, capture_output=True)
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), ['icons'])

    def test_existing_destination_is_preserved(self):
        (self.output/'icons').mkdir(); (self.output/'icons/keep').write_text('keep')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual((self.output/'icons/keep').read_text(), 'keep')

    def test_destination_symlink_is_refused(self):
        (self.output/'icons').symlink_to(self.root/'absent')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse((self.root/'absent').exists())

    def test_no_theme_is_failure_with_cleanup(self):
        (self.theme/'index.theme').unlink()
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_old_cache_link_cannot_modify_original(self):
        retained = self.root/'retained'; retained.write_text('retained')
        (self.theme/'icon-theme.cache').symlink_to(retained)
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(retained.read_text(), 'retained')
        self.assertFalse((self.output/'icons/Test/icon-theme.cache').is_symlink())

    def test_tool_failure_propagates_and_cleans_partial_tree(self):
        binary = self.root/'bin'; binary.mkdir()
        tool = binary/'gtk-update-icon-cache'
        tool.write_text('#!/bin/sh\nexit 42\n'); tool.chmod(0o755)
        self.env['PATH'] = str(binary)+':'+self.env['PATH']
        r = self.run_helper(); self.assertEqual(r.returncode, 42, r.stderr)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_success_without_cache_is_rejected(self):
        binary = self.root/'bin'; binary.mkdir()
        tool = binary/'gtk-update-icon-cache'
        tool.write_text('#!/bin/sh\nexit 0\n'); tool.chmod(0o755)
        self.env['PATH'] = str(binary)+':'+self.env['PATH']
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_interruption_cleans_partial_preparation(self):
        binary = self.root/'bin'; binary.mkdir()
        marker = self.root/'started'
        tool = binary/'gtk-update-icon-cache'
        tool.write_text('#!/bin/sh\ntouch "$MARKER"\nsleep 10\n'); tool.chmod(0o755)
        self.env.update(PATH=str(binary)+':'+self.env['PATH'], MARKER=str(marker))
        p = subprocess.Popen(self.cmd, env=self.env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
        try:
            deadline = time.monotonic()+3
            while not marker.exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(marker.exists())
            os.killpg(p.pid, signal.SIGTERM); p.communicate(timeout=3)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(list(self.output.iterdir()), [])
        finally:
            if p.poll() is None: os.killpg(p.pid, signal.SIGKILL); p.wait()

    def test_concurrent_preparers_cannot_overwrite(self):
        ps = [subprocess.Popen(self.cmd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for p in ps: p.communicate(timeout=15)
        self.assertEqual(sum(p.returncode == 0 for p in ps), 1)
        self.assertEqual(sorted(p.name for p in self.output.iterdir()), ['icons'])

if __name__ == '__main__': unittest.main()
