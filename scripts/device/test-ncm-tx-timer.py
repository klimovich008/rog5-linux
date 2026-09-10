#!/usr/bin/env python3
"""Compile the real NCM timer callback and reproduce an exhausted TX pool."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / 'scripts/device/fixtures/ncm-tx-timer.c'
PATCH = REPO / 'patches/linux-7.1.4/0039-usb-gadget-ncm-restart-busy-tx-timer.patch'
DRIVER = Path('drivers/usb/gadget/function/f_ncm.c')
FRAGMENT = re.compile(r'/\* source: ncm_tx_timeout \*/\n(.*?)/\* end: ncm_tx_timeout \*/', re.S)


def patched(directory, source):
    target = directory / DRIVER
    target.parent.mkdir(parents=True)
    target.write_text(source)
    subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=directory, check=True)
    subprocess.run(['git', 'apply', str(PATCH)], cwd=directory, check=True)
    return target.read_text()


class NcmTimer(unittest.TestCase):
    def compile_run(self, directory, source):
        c = directory / 'test.c'; exe = directory / 'test'
        c.write_text(source)
        subprocess.run(['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                        str(c), '-o', str(exe)], check=True)
        return subprocess.run([str(exe)], capture_output=True, text=True, timeout=5)

    def test_unfixed_callback_strands_pending_reply(self):
        with tempfile.TemporaryDirectory(prefix='rog5-ncm-timer-') as tmp:
            result = self.compile_run(Path(tmp), FIXTURE.read_text())
        self.assertEqual(result.returncode, 1)
        self.assertIn('pending NTB stranded: calls=1 busy=1', result.stderr)

    def test_fixed_callback_retries_without_new_traffic_and_stops_correctly(self):
        with tempfile.TemporaryDirectory(prefix='rog5-ncm-timer-') as tmp:
            directory = Path(tmp)
            result = self.compile_run(directory, patched(directory, FIXTURE.read_text()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('success stops, absent device stops', result.stdout)

    def test_patch_changes_only_busy_callback_handling(self):
        lines = PATCH.read_text().splitlines()
        self.assertEqual([line for line in lines if line.startswith('+++ ')],
                         ['+++ b/' + str(DRIVER)])
        removed = [line for line in lines if line.startswith('-') and not line.startswith('--- ')]
        self.assertEqual(removed, ['-\t\tnetdev->netdev_ops->ndo_start_xmit(NULL, netdev);'])
        added = [line[1:] for line in lines if line.startswith('+') and not line.startswith('+++ ')]
        self.assertEqual(added, ['\tnetdev_tx_t ret;',
            '\t\tret = netdev->netdev_ops->ndo_start_xmit(NULL, netdev);',
            '\t\tif (ret == NETDEV_TX_BUSY) {',
            '\t\t\thrtimer_forward_now(data, TX_TIMEOUT_NSECS);',
            '\t\t\treturn HRTIMER_RESTART;', '\t\t}'])


def check_source(path):
    source = path.read_text(); fixture = FIXTURE.read_text()
    fragment = FRAGMENT.search(fixture).group(1)
    if source.count(fragment) != 1:
        raise ValueError('retained callback differs from compiled regression')
    with tempfile.TemporaryDirectory(prefix='rog5-ncm-source-') as tmp:
        original_patch = patched(Path(tmp) / 'source', source)
        fixture_patch = patched(Path(tmp) / 'fixture', fixture)
        if original_patch.count(FRAGMENT.search(fixture_patch).group(1)) != 1:
            raise ValueError('patched callback differs from regression')
    print('PASS exact retained callback and read-only patch-application check')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    args, remaining = parser.parse_known_args()
    if args.source: check_source(args.source)
    unittest.main(argv=[__file__, *remaining])
