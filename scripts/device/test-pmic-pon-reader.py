#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('pon_decoder', REPO/'tools/pmic_pon_reader/decode.py')
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)


def snapshot(push, records):
    fifo = bytearray(117)
    start = (push - 0x4b - 116) % 117
    for index, entry in enumerate(records, 29-len(records)):
        for offset, byte in enumerate(entry):
            fifo[(start + index*4 + offset) % 117] = byte
    return b'RPON\x01' + bytes([push,push,117]) + fifo


class PonReaderTest(unittest.TestCase):
    def test_all_push_positions_and_wraps(self):
        for push in range(0x4b,0xc0):
            result=decoder.decode(snapshot(push,[(4,6,0,0x84),(4,7,0,7)]))
            self.assertEqual(result['records'][0]['reset_trigger'],'PS_HOLD')
            self.assertEqual(result['records'][1]['reset_type'],'HARD_RESET')

    def test_empty_unknown_and_faults_remain_explicit(self):
        result=decoder.decode(snapshot(0x4b,[]))
        self.assertEqual(result['records'],[])
        self.assertTrue(result['empty_is_inconclusive'])
        result=decoder.decode(snapshot(0x90,[(0,9,0x10,0x40),(4,6,0x12,0x34)]))
        self.assertEqual(result['records'][0]['faults'],['UVLO','FAULT_WATCHDOG'])
        self.assertEqual(result['records'][1]['reset_trigger'],'UNKNOWN_1234')
        self.assertEqual(decoder.decode(snapshot(0x7f,[(7,8,0,3)]))['records'][0]['warm_reset_count'],3)

    def test_partial_or_changing_snapshot_rejected(self):
        valid=snapshot(0x4b,[])
        for bad in (valid[:-1],b'x'+valid[1:],valid[:6]+bytes([0x50])+valid[7:]):
            with self.assertRaises(ValueError): decoder.decode(bad)

    def test_reader_has_fixed_identity_and_no_write_surface(self):
        source=(REPO/'tools/pmic_pon_reader/rog5-pmic-pon-readonly.c').read_text()
        self.assertIn('of_machine_is_compatible("asus,rog-phone5")',source)
        self.assertIn('/soc@0/spmi@c440000/pmic@0/nvram@7400',source)
        self.assertIn('count != 1',source)
        self.assertIn('snapshot[5] != snapshot[6]',source)
        self.assertIn('"snapshot", 0400',source)
        for forbidden in ('nvmem_device_write(', 'regmap_write(', 'writel(', 'module_param(', '0xE5', '0xE6'):
            self.assertNotIn(forbidden,source)

    def test_resolve_full_path_before_comparing_node_identity(self):
        source=(REPO/'tools/pmic_pon_reader/rog5-pmic-pon-readonly.c').read_text()
        self.assertIn('of_find_node_by_path(PON_NODE)',source)
        self.assertIn('np != lookup->node',source)
        self.assertNotIn('strcmp(np->full_name',source)


if __name__=='__main__': unittest.main()
