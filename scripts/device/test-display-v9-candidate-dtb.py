#!/usr/bin/env python3
"""Focused current-V9 DT preservation tests; requires the retained --base fixture."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'display_v9_builder', Path(__file__).with_name('build-display-v9-candidate-dtb.py'))
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)
V = B.V
REPO = Path(__file__).resolve().parents[2]
OVERLAY = REPO/'dts/qcom/sm8350-asus-rog-phone5-display-60hz.dtso'
BASE = None


class DisplayV9(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = V.read_regular(BASE)
        cls.temp = tempfile.TemporaryDirectory(prefix='rog5-display-v9-test-')
        cls.root = Path(cls.temp.name)
        B.build(BASE, OVERLAY, cls.root/'first.dtb')
        cls.candidate = V.read_regular(cls.root/'first.dtb')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_twins_and_exact_structural_delta(self):
        report = B.build(BASE, OVERLAY, self.root/'second.dtb')
        self.assertEqual(self.candidate, V.read_regular(self.root/'second.dtb'))
        self.assertEqual(report['added_nodes'], 10)
        self.assertEqual(report['changed_existing_properties'], 14)
        self.assertEqual(report['base_sha256'], V.BASE_SHA256)
        self.assertIn('no activation', report['scope'])

    def test_historical_oracle_is_preserved(self):
        self.assertEqual(V.HISTORICAL.BASE_SHA256,
                         '8b1250cefd69870662edb9131190f005f492b4c93c192ee7e2b89b9a121f22da')
        self.assertEqual(V.HISTORICAL.BASE_SIZE, 107194)
        with self.assertRaisesRegex(ValueError, 'base DTB identity changed'):
            V.HISTORICAL.main([str(BASE), str(self.root/'first.dtb')])

    def test_wrong_base_refused_before_tools_and_output(self):
        wrong = self.root/'wrong-base.dtb'
        wrong.write_bytes(self.base[:-1] + bytes([self.base[-1] ^ 1]))
        output = self.root/'wrong-base-output.dtb'
        with patch.object(B.subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'base identity'):
            B.build(wrong, OVERLAY, output)
        run.assert_not_called()
        self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, 'base identity'):
            V.verify(self.base + b'\0', self.candidate)

    def test_wrong_overlay_refused_before_tools_and_output(self):
        wrong = self.root/'wrong-overlay.dts'
        wrong.write_bytes(V.read_regular(OVERLAY) + b'\n')
        output = self.root/'wrong-overlay-output.dtb'
        with patch.object(B.subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'overlay identity'):
            B.build(BASE, wrong, output)
        run.assert_not_called()
        self.assertFalse(output.exists())

    def test_non_display_mutations_and_wrong_panel_refused(self):
        cases = [
            ['-t', 's', '/soc@0/gpu@3d00000', 'status', 'okay'],
            ['-t', 's', '/soc@0/ufshc@1d84000', 'status', 'disabled'],
            ['-t', 's', '/chosen', 'bootargs', 'unapproved'],
            ['-t', 's', '/reserved-memory', 'unapproved', 'drift'],
            ['-t', 'x', '/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey', 'linux,code', '73'],
            ['-t', 's', V.HISTORICAL.PANEL, 'compatible', 'asus,other-panel'],
            ['-c', '/unapproved-node'],
            ['-r', '/chosen'],
        ]
        for index, argv in enumerate(cases):
            path = self.root/('mutant-' + str(index) + '.dtb')
            path.write_bytes(self.candidate)
            command = ['fdtput', *argv[:2], str(path), *argv[2:]] if argv[0] == '-t' else ['fdtput', argv[0], str(path), *argv[1:]]
            subprocess.run(command, check=True, capture_output=True, timeout=3)
            with self.subTest(mutation=argv), self.assertRaises(ValueError):
                V.verify(self.base, V.read_regular(path))

    def test_boot_cpu_reservation_entries_and_origin_are_preserved(self):
        parser = V.HISTORICAL.load_parser()
        original_nodes = parser.parse_dtb(self.candidate, 'original')
        cpu = bytearray(self.candidate)
        struct.pack_into('>I', cpu, 28, 1)
        # Insert a valid reservation before the original terminator. The node
        # tree remains byte-for-byte identical; a nodes-only check misses it.
        added = bytearray(self.candidate[:40] + struct.pack('>QQ', 0x88000000, 0x1000)
                          + self.candidate[40:])
        for index in (1, 2, 3):
            struct.pack_into('>I', added, index * 4,
                             struct.unpack_from('>I', self.candidate, index * 4)[0] + 16)
        # Relocation is also refused even when the empty map is unchanged.
        moved = bytearray(self.candidate[:40] + b'\0' * 8 + self.candidate[40:])
        for index in (1, 2, 3, 4):
            struct.pack_into('>I', moved, index * 4,
                             struct.unpack_from('>I', self.candidate, index * 4)[0] + 8)
        for label, data in (('boot CPU', cpu), ('reservation entry', added), ('origin', moved)):
            with self.subTest(label=label):
                self.assertEqual(parser.parse_dtb(data, label), original_nodes)
                with self.assertRaisesRegex(ValueError, 'boot CPU or reservation map/origin'):
                    V.verify(self.base, data)
        for offset in (0, 41, len(self.candidate) - 8):
            malformed = bytearray(self.candidate)
            struct.pack_into('>I', malformed, 16, offset)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                V.verify(self.base, malformed)
        unterminated = bytearray(self.candidate)
        struct.pack_into('>QQ', unterminated, 40, 1, 1)
        with self.assertRaises(ValueError):
            V.verify(self.base, unterminated)

    def test_input_links_fifo_and_directory_refused_without_tools(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            root = Path(temporary)
            (root/'symlink').symlink_to(BASE)
            os.mkfifo(root/'fifo')
            (root/'directory').mkdir()
            (root/'linked-parent').symlink_to(BASE.parent, target_is_directory=True)
            hard = root/'hard'; hard.write_bytes(self.base); os.link(hard, root/'hard2')
            paths = [root/'symlink', root/'fifo', root/'directory', root/'linked-parent'/BASE.name, hard]
            for path in paths:
                with self.subTest(path=path), patch.object(B.subprocess, 'run') as run:
                    with self.assertRaises((OSError, ValueError)):
                        B.build(path, OVERLAY, root/'uncreated.dtb')
                    run.assert_not_called()
                    self.assertFalse((root/'uncreated.dtb').exists())

    def test_output_overwrite_and_linked_parent_refused(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            root = Path(temporary)
            sentinel = root/'existing'; sentinel.write_bytes(b'preserve')
            (root/'link').symlink_to(sentinel)
            (root/'dangling').symlink_to(root/'absent')
            (root/'dir').mkdir()
            (root/'linked-parent').symlink_to(root/'dir', target_is_directory=True)
            for path in [sentinel, root/'link', root/'dangling', root/'dir', root/'linked-parent'/'new']:
                with self.subTest(path=path), patch.object(B.subprocess, 'run') as run:
                    with self.assertRaises((OSError, ValueError)):
                        B.build(BASE, OVERLAY, path)
                    run.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b'preserve')
            self.assertFalse((root/'absent').exists())
            self.assertFalse((root/'dir'/'new').exists())

    def test_tool_failure_creates_no_candidate(self):
        output = self.root/'failed-tool.dtb'
        with patch.object(B.subprocess, 'run', side_effect=subprocess.TimeoutExpired('dtc', 10)):
            with self.assertRaises(subprocess.TimeoutExpired):
                B.build(BASE, OVERLAY, output)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    args, rest = parser.parse_known_args()
    BASE = args.base
    unittest.main(argv=[__file__, *rest])
