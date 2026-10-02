#!/usr/bin/env python3
"""Offline test of scripts/host/backup-readonly-storage-inventory.py: a
stream that times out (or is interrupted) terminates and reaps its SSH child
before the partial file is removed (audit 2026-10-02, 04-host-rest). A local
shell stands in for SSH; no phone is contacted."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
loader = importlib.machinery.SourceFileLoader(
    'backup_inventory', str(REPO / 'scripts/host/backup-readonly-storage-inventory.py'))
TOOL = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(TOOL)

RECORD = {'node': 'sda1', 'label': 'modemst1', 'size_512_sectors': 8, 'start_512_sectors': 8,
          'size_bytes': 4096, 'disk': 'sda', 'role': 'primary', 'logical_block_bytes': 4096,
          'offset_bytes': 0, 'disk_size_512_sectors': 16}


class StreamTimeout(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pidfile = self.tmp / 'child.pid'
        # "ssh" that records its pid and never finishes
        self.base = ['sh', '-c', f'echo $$ > {self.pidfile}; exec sleep 300', 'fake-ssh']
        self.real_popen = subprocess.Popen
        self.addCleanup(setattr, subprocess, 'Popen', self.real_popen)

    def short_communicate(self):
        real = self.real_popen

        class Short(real):
            def communicate(self, input=None, timeout=None):
                return super().communicate(input, timeout=0.5)
        subprocess.Popen = Short

    def child_gone(self):
        pid = int(self.pidfile.read_text())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        return False

    def check(self, fn):
        self.short_communicate()
        out = self.tmp / 'out.img'
        with self.assertRaises(subprocess.TimeoutExpired):
            fn(self.base, 'boot', RECORD, out)
        for _ in range(20):
            if self.pidfile.exists():
                break
            time.sleep(0.05)
        self.assertTrue(self.child_gone(), 'the SSH child still runs after the timeout')
        self.assertFalse((self.tmp / 'out.img.partial').exists())
        self.assertFalse(out.exists())

    def test_partition_stream_reaps_its_child(self):
        self.check(TOOL.stream_partition)

    def test_gpt_stream_reaps_its_child(self):
        self.check(TOOL.stream_gpt)


if __name__ == '__main__':
    unittest.main()
