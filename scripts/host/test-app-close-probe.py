#!/usr/bin/env python3
"""Compile and execute the actual read-only VM sampler tests; no VM access."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/qemu-virtio-drm/app-close-probe.rs'


class AppCloseProbe(unittest.TestCase):
    def test_actual_rust_parser_sampler_and_release_refusal(self):
        with tempfile.TemporaryDirectory(prefix='rog5-app-close-probe-') as temp:
            target = Path(temp)
            for kind, flags in [('tests', ['--test']), ('release', [])]:
                subprocess.run(['rustc', '--edition=2024', '-D', 'warnings', *flags,
                                str(SOURCE), '-o', str(target / kind)], check=True, timeout=30)
            subprocess.run([str(target / 'tests'), '--nocapture'], check=True, timeout=10)
            result = subprocess.run([str(target / 'release'), '1', '1', '2', '1'],
                                    capture_output=True, timeout=3)
            self.assertEqual(result.returncode, 125)
            self.assertEqual(result.stdout, b'')
            self.assertIn(b'requires non-root isolated VM', result.stderr)


if __name__ == '__main__':
    unittest.main()
