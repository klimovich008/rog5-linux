#!/usr/bin/env python3
import copy
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('wifi_dtb', Path(__file__).with_name('verify-native-wifi-dtb.py'))
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)
cell = lambda value: struct.pack('>I', value)

class WifiDeltaTest(unittest.TestCase):
    def setUp(self):
        self.base = {
            wifi.S11: {'regulator-min-microvolt': cell(752000), 'regulator-max-microvolt': cell(1000000)},
            wifi.S1C: {'regulator-min-microvolt': cell(1800000), 'regulator-max-microvolt': cell(1952000)},
            wifi.PCIE: {'status': b'disabled\0', 'iommu-map': b'unchanged-map'},
            wifi.PHY: {'status': b'disabled\0'},
            '/soc@0/ufshc@1d84000': {'status': b'okay\0'},
            '/soc@0/usb@a6f8800': {'status': b'okay\0'},
        }
        self.candidate = copy.deepcopy(self.base)
        self.candidate[wifi.S11].update({'regulator-min-microvolt': cell(1012000), 'regulator-max-microvolt': cell(1016000)})
        self.candidate[wifi.S12] = {'regulator-min-microvolt': cell(1350000), 'regulator-max-microvolt': cell(1352000)}
        self.candidate[wifi.S1C]['regulator-min-microvolt'] = cell(1900000)
        for path in (wifi.PCIE, wifi.PHY): self.candidate[path]['status'] = b'okay\0'
        self.candidate[wifi.TLMM + '/wlan-en-state'] = {}
        self.candidate['/wcn6855-pmu'] = {'compatible': b'qcom,wcn6855-pmu\0'}
        self.candidate[wifi.PCIE + '/pcie@0/wifi@0'] = {'compatible': b'pci17cb,1103\0'}

    def test_exact_delta(self):
        wifi.compare(self.base, self.candidate)

    def test_preserves_storage_usb_and_iommu(self):
        for path, key in (('/soc@0/ufshc@1d84000', 'status'), ('/soc@0/usb@a6f8800', 'status'), (wifi.PCIE, 'iommu-map')):
            with self.subTest(path=path):
                bad = copy.deepcopy(self.candidate); bad[path][key] = b'changed'
                with self.assertRaises(ValueError): wifi.compare(self.base, bad)

    def test_old_voltage_and_forced_wlan_reset_rejected(self):
        self.candidate[wifi.S11]['regulator-min-microvolt'] = cell(952000)
        with self.assertRaises(ValueError): wifi.compare(self.base, self.candidate)
        self.candidate[wifi.S11]['regulator-min-microvolt'] = cell(1012000)
        self.candidate[wifi.TLMM + '/wlan-en-state']['output-low'] = b''
        with self.assertRaises(ValueError): wifi.compare(self.base, self.candidate)

    def test_unrelated_addition_and_removal_rejected(self):
        bad = copy.deepcopy(self.candidate); bad['/unrelated-device'] = {}
        with self.assertRaises(ValueError): wifi.compare(self.base, bad)
        bad = copy.deepcopy(self.candidate); del bad['/soc@0/ufshc@1d84000']
        with self.assertRaises(ValueError): wifi.compare(self.base, bad)

    def test_unrepresentable_literal_vendor_windows_rejected(self):
        for path, value in ((wifi.S11, 1012000), (wifi.S12, 1350000)):
            with self.subTest(path=path):
                bad = copy.deepcopy(self.candidate)
                bad[path]['regulator-max-microvolt'] = cell(value)
                with self.assertRaises(ValueError): wifi.compare(self.base, bad)

    def test_actual_selector_arithmetic(self):
        for value in (1012000, 1350000):
            with self.assertRaises(ValueError): wifi.first_voltage_selector(value, value)
        self.assertEqual(wifi.first_voltage_selector(1012000, 1016000), 1016000)
        self.assertEqual(wifi.first_voltage_selector(1350000, 1352000), 1352000)

if __name__ == '__main__': unittest.main()
