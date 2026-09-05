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
        self.assertEqual(len(plan), 26)
        self.assertEqual(len(set(plan)), 26)
        for line in plan:
            self.assertRegex(line, r'^(p|r64):rog5_native_wifi/(enter|return)_[a-z0-9_]+ [a-z0-9_]+( [a-z_]+=[^ ]+)*$')
        for symbol in ('qcom_pcie_host_init', 'qcom_pcie_init_2_7_0', 'phy_power_on',
                       'clk_bulk_prepare', 'clk_bulk_enable', 'reset_control_assert',
                       'reset_control_deassert', 'pci_pwrctrl_power_on_devices'):
            self.assertIn(f'p:rog5_native_wifi/enter_{symbol} {symbol}', plan)
        self.assertFalse(any('ath11k' in line or 'mhi' in line for line in plan))

    def test_rpmh_plan_captures_command_and_completion_boundary(self):
        plan = subprocess.check_output(['sh', str(HELPER), 'plan'], text=True).splitlines()
        for symbol in ('rpmh_write', 'rpmh_write_async'):
            self.assertIn(
                f'p:rog5_native_wifi/enter_{symbol} {symbol}'
                ' state=$arg2:u32 count=$arg4:u32 address=+0($arg3):x32'
                ' value=+4($arg3):x32 command_wait=+8($arg3):u32', plan)
            self.assertIn(f'r64:rog5_native_wifi/return_{symbol} {symbol} result=$retval:s32', plan)
        self.assertIn('p:rog5_native_wifi/enter_rpmh_rsc_send_data rpmh_rsc_send_data', plan)
        self.assertIn('r64:rog5_native_wifi/return_rpmh_rsc_send_data rpmh_rsc_send_data result=$retval:s32', plan)
        # Per-command wait is a u32, not the request's wait_for_compl flag.
        self.assertFalse(any('complete=' in line or 'command_wait=+8($arg3):u8' in line for line in plan))

    def test_private_rpmh_events_checked_before_arming_and_disabled_on_cleanup(self):
        source = HELPER.read_text()
        self.assertIn('for event in rpmh_send_msg rpmh_tx_done', source)
        self.assertLess(source.index('RPMh event unavailable'), source.index('mkdir "$owner"'))
        self.assertIn('printf \'1\\n\' >"$instance/events/rpmh/enable"', source)
        self.assertIn('printf \'0\\n\' >"$instance/events/rpmh/enable"', source)
        self.assertNotIn('>"$trace/events/rpmh/enable"', source)

    def test_real_sync_and_async_frames_require_call_and_ack_evidence(self):
        fixture = json.loads((REPO / 'tests/fixtures/native-wifi/rpmh-passive-v11.json').read_text())
        plan = subprocess.check_output(['sh', str(HELPER), 'plan'], text=True)
        for kind, symbol in (('sync', 'rpmh_write'), ('async', 'rpmh_write_async')):
            frames = fixture[kind]
            self.assertIn(f'enter_{symbol}', plan)
            self.assertIn(f'return_{symbol}', plan)
            for field in ('state', 'count', 'address', 'value', 'command_wait'):
                self.assertIn(f'{field}=', frames[0])
                self.assertIn(f'{field}=', plan)
            self.assertIn('complete: 0', frames[1])
            self.assertTrue(any('rpmh_tx_done:' in line for line in frames))
        # The same printed complete=0 has different request-response bits.
        self.assertIn('msgid: 0x10108', fixture['sync'][1])
        self.assertIn('msgid: 0x10008', fixture['async'][1])
        self.assertFalse(fixture['radio_activated'])
        self.assertFalse(fixture['previous_trace_loss_explained'])

    def test_polling_consumers_do_not_require_half_full_buffer(self):
        source = HELPER.read_text()
        self.assertIn('printf \'0\\n\' >"$instance/buffer_percent"', source)
        self.assertLess(source.index('>"$instance/buffer_percent"'),
                        source.index('printf \'1\\n\' >"$instance/tracing_on"'))

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
