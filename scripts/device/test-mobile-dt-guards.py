#!/usr/bin/env python3
"""Small semantic guard regressions; hardware/schema checks are separate."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('mobile_dt', Path(__file__).with_name('test-mobile-dt-composition.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class Symbols(unittest.TestCase):
    def setUp(self):
        self.base = {'/': {'compatible': b'asus,rog-phone5\0qcom,sm8350\0'},
                     '/clock': {'phandle': M.cell(1), 'clock-frequency': M.cell(100)}, '/device': {}}
        self.symbolic = copy.deepcopy(self.base)
        self.symbolic['/device']['phandle'] = M.cell(2)
        self.symbolic[M.SYMBOLS] = {'clock': M.string('/clock'), 'device': M.string('/device')}

    def test_symbols_only(self):
        self.assertEqual(M.compare_symbols(self.base, self.symbolic),
                         {'added_symbol_count': 2, 'added_phandle_count': 1})

    def test_existing_property_cannot_change(self):
        self.symbolic['/clock']['clock-frequency'] = M.cell(200)
        with self.assertRaises(ValueError):
            M.compare_symbols(self.base, self.symbolic)

    def test_existing_phandle_cannot_change(self):
        self.symbolic['/clock']['phandle'] = M.cell(3)
        with self.assertRaises(ValueError):
            M.compare_symbols(self.base, self.symbolic)

    def test_phandle_collision(self):
        self.symbolic['/device']['phandle'] = M.cell(1)
        with self.assertRaises(ValueError):
            M.compare_symbols(self.base, self.symbolic)

    def test_extra_hardware_node(self):
        self.symbolic['/surprise'] = {}
        with self.assertRaises(ValueError):
            M.compare_symbols(self.base, self.symbolic)

    def test_dangling_symbol(self):
        self.symbolic[M.SYMBOLS]['missing'] = M.string('/missing')
        with self.assertRaises(ValueError):
            M.compare_symbols(self.base, self.symbolic)

    def test_existing_node_cannot_disappear(self):
        del self.symbolic['/device']
        with self.assertRaises(ValueError):
            M.compare_symbols(self.base, self.symbolic)


if __name__ == '__main__':
    unittest.main()
