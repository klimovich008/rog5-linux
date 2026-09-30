#!/usr/bin/env python3
"""Offline tests for scripts/host/rog5-dtb-memory (needs dtc, fdtget, fdtput)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / 'scripts/host/rog5-dtb-memory'
DTS = '''/dts-v1/;
/ {
	#address-cells = <2>;
	#size-cells = <2>;
	memory@80000000 {
		device_type = "memory";
		reg = <0x0 0x80000000 0x0 0x37100000>, <0x2 0x00000000 0x1 0x80000000>,
		      <0x0 0xc0000000 0x1 0x40000000>, <0x0 0xb9500000 0x0 0x00000000>;
	};
	reserved-memory {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;
		low@80000000 { reg = <0x0 0x80000000 0x0 0x600000>; no-map; };
		memx: memory@34a000000 { reg = <0x3 0x4a000000 0x0 0x04000000>; no-map; };
		dynamic { size = <0x0 0x400000>; };
	};
};
'''


def reg_hex(ranges):
    return ''.join('%016x%016x' % r for r in ranges)


REF = [(0x80000000, 0x37100000), (0x200000000, 0x180000000), (0xc0000000, 0x140000000), (0xb9500000, 0)]
GB8 = [(0x80000000, 0x37100000), (0xc0000000, 0x140000000), (0x200000000, 0x80000000)]
GB16 = [(0x80000000, 0x37100000), (0xc0000000, 0x140000000), (0x200000000, 0x280000000)]


@unittest.skipUnless(all(shutil.which(t) for t in ('dtc', 'fdtget', 'fdtput')), 'needs dtc, fdtget, fdtput')
class DtbMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.dtb = self.tmp / 'board.dtb'
        subprocess.run(['dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(self.dtb), '-'],
                       input=DTS, text=True, check=True)

    def tool(self, *args):
        return subprocess.run(['python3', str(TOOL), *map(str, args)], capture_output=True, text=True)

    def test_reference_map_checks_and_memx_is_reported(self):
        result = self.tool('check', self.dtb, '--memory-reg', reg_hex(REF))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        shown = self.tool('show', self.dtb).stdout
        self.assertIn('total 11.86 GiB', shown)
        self.assertIn('memx', shown)

    def test_a_different_phone_map_is_detected(self):
        result = self.tool('check', self.dtb, '--memory-reg', reg_hex(GB16))
        self.assertEqual(result.returncode, 1)
        self.assertIn('differs', result.stdout)

    def test_set_for_16_gb_keeps_memx_inside_ram(self):
        out = self.tmp / 'out.dtb'
        result = self.tool('set', self.dtb, out, '--memory-reg', reg_hex(GB16))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('total 15.86 GiB', self.tool('show', out).stdout)

    def test_set_for_8_gb_refuses_memx_outside_ram(self):
        out = self.tmp / 'out.dtb'
        result = self.tool('set', self.dtb, out, '--memory-reg', reg_hex(GB8))
        self.assertEqual(result.returncode, 1)
        self.assertIn('memory@34a000000', result.stdout)
        self.assertFalse(out.exists())

    def test_malformed_maps_are_refused(self):
        for bad in ('xyz', reg_hex(GB8)[:-2], reg_hex([(0x1000, 0x1000)]),
                    reg_hex([(0x80000000, 0x100000000), (0xc0000000, 0x100000000)]),
                    reg_hex([(0x80000000, 0x40000000)])):
            with self.subTest(bad=bad[:20]):
                result = self.tool('set', self.dtb, self.tmp / 'x.dtb', '--memory-reg', bad)
                self.assertEqual(result.returncode, 1)
                self.assertFalse((self.tmp / 'x.dtb').exists())


if __name__ == '__main__':
    unittest.main()
