#!/usr/bin/env python3
"""Offline plan checks tied to the real pre-MHI PCIe reset observation."""
import json
import re
from pathlib import Path
import subprocess
import unittest

REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / 'scripts/device/trace-native-wifi-pcie.sh'


class PcieTracePlan(unittest.TestCase):
    def test_reader_outlives_radio_rollback_and_fallback_margin(self):
        fixture = json.loads((REPO / 'tests/fixtures/native-wifi/pcie-reset-before-mhi.json').read_text())
        deadline = int(re.search(r'exec timeout (\d+) cat', HELPER.read_text())[1])
        self.assertGreaterEqual(deadline, fixture['rollback_timer_seconds'] + 120)

    def test_plan_covers_observed_boundary_without_activating_hardware(self):
        fixture = json.loads((REPO / 'tests/fixtures/native-wifi/pcie-reset-before-mhi.json').read_text())
        self.assertFalse(fixture['wifi_phy_ready'])
        self.assertIsNone(fixture['later_module_entry'])
        self.assertIn('WIFI_MODULE_RETURN phy-qcom-qmp-pcie', fixture['records'])
        self.assertEqual(fixture['reset_mechanism'], 'unknown')
        plan = subprocess.check_output(['sh', str(HELPER), 'plan'], text=True).splitlines()
        self.assertEqual(len(plan), 20)
        self.assertEqual(len(set(plan)), 20)
        for line in plan:
            self.assertRegex(line, r'^(p|r64):rog5_native_wifi/(enter|return)_[a-z0-9_]+ [a-z0-9_]+( result=\$retval:s32)?$')
        for symbol in ('qcom_pcie_host_init', 'qcom_pcie_init_2_7_0', 'phy_power_on',
                       'clk_bulk_prepare', 'clk_bulk_enable', 'reset_control_assert',
                       'reset_control_deassert', 'pci_pwrctrl_power_on_devices'):
            self.assertIn(f'p:rog5_native_wifi/enter_{symbol} {symbol}', plan)
        self.assertFalse(any('ath11k' in line or 'mhi' in line for line in plan))

    def test_cleanup_is_selective_and_ownership_precedes_changes(self):
        source = HELPER.read_text()
        subprocess.run(['sh', '-n', str(HELPER)], check=True)
        self.assertNotRegex(source, r'(?<!>)>"\$trace/kprobe_events"')
        self.assertIn('owns_instance || return 1', source)
        self.assertIn('>>"$trace/kprobe_events"', source)
        self.assertRegex(source, r'exec timeout \d+ cat "\$instance/trace_pipe"')
        self.assertLess(source.index('missing or ambiguous symbol'), source.index('mkdir "$owner"'))
        for forbidden in ('modprobe ', 'insmod ', 'kexec ', 'fastboot ', 'blockdev ',
                          'systemctl ', 'rm -rf', '/dev/mem', 'current_tracer"'):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
