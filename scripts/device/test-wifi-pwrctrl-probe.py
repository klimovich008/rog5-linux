#!/usr/bin/env python3
"""Validate the QEMU-only power-control probe and diagnostic pause evidence."""
from pathlib import Path
import json
import re
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[2]
PATCH = REPO / 'patches/linux/diagnostic/pci-pwrctrl-pwrseq-observation.patch'
FIXTURE = REPO / 'tools/wifi_pwrctrl_probe/rog5-wifi-pwrctrl-probe.c'


def validate_log(text, pause):
    if re.search(r'Kernel panic|Oops:|BUG:', text) or 'ROG5_QEMU_PWRCTRL_END' not in text:
        raise ValueError('QEMU fixture did not finish cleanly')
    records = re.findall(r'\[\s*([\d.]+)\].*ROG5_PWRCTRL_OBSERVE stage=([a-z-]+) result=(-?\d+) pause_ms=(\d+)', text)
    if pause in (0, 1001):
        if records:
            raise ValueError('disabled/invalid pause produced observation actions')
    elif pause == 250:
        expected = ['probe-enter', 'probe-ready', 'power-on-enter', 'power-on-return']
        if [r[1] for r in records] != expected or any(r[2:] != ('0', '250') for r in records):
            raise ValueError('diagnostic boundaries are incomplete')
        for earlier, later in zip(records, records[1:]):
            if float(later[0]) - float(earlier[0]) < 0.249:
                raise ValueError('observation pause did not drain the prior boundary')
        final = re.search(r'\[\s*([\d.]+)\].*ROG5_PWRCTRL_DUMMY_POWER_ON_RETURN=0', text)
        if not final or float(final[1]) - float(records[-1][0]) < 0.249:
            raise ValueError('final observation pause missing')
    else:
        raise ValueError('unsupported fixture case')
    result = -517 if pause == 1001 else 0
    if f'ROG5_PWRCTRL_DUMMY_POWER_ON_RETURN={result}' not in text:
        raise ValueError('unexpected power-control result')


class PwrctrlProbeTest(unittest.TestCase):
    def test_patch_is_parseable_and_disabled_by_default(self):
        subprocess.run(['git', 'apply', '--numstat', str(PATCH)], check=True, stdout=subprocess.PIPE)
        text = PATCH.read_text()
        self.assertIn('static unsigned int observation_ms;', text)
        self.assertIn('module_param(observation_ms, uint, 0400)', text)
        self.assertIn('if (observation_ms > 1000)', text)
        self.assertIn('msleep(observation_ms)', text)
        self.assertLess(text.index('if (observation_ms > 1000)'), text.index('"probe-enter"'))

    def test_fixture_cannot_activate_a_phone(self):
        text = FIXTURE.read_text()
        self.assertLess(text.index('of_machine_is_compatible("linux,dummy-virt")'), text.index('ret = pci_pwrctrl_create_devices'))
        for forbidden in ('ioremap', 'readl(', 'writel(', '/dev/', 'kexec', 'reboot'):
            self.assertNotIn(forbidden, text)

    def test_trace_loss_is_not_a_proven_failure_location(self):
        fixture = json.loads((REPO / 'tests/fixtures/native-wifi/pcie-after-phy-trace.json').read_text())
        self.assertEqual(fixture['completed_calls'][-1]['name'], 'phy_power_on')
        self.assertEqual(fixture['completed_calls'][-1]['result'], 0)
        self.assertTrue(fixture['lost_final_trace_records_possible'])
        self.assertIsNone(fixture['proven_fault_site'])

    def test_missing_completion_or_pause_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_log('ROG5_PWRCTRL_DUMMY_POWER_ON_RETURN=0', 0)
        text = '\n'.join(f'[{i / 10}] ROG5_PWRCTRL_OBSERVE stage={s} result=0 pause_ms=250'
                         for i, s in enumerate(['probe-enter', 'probe-ready', 'power-on-enter', 'power-on-return']))
        with self.assertRaises(ValueError):
            validate_log(text + '\n[1] ROG5_PWRCTRL_DUMMY_POWER_ON_RETURN=0\nROG5_QEMU_PWRCTRL_END', 250)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--validate-log':
        validate_log(Path(sys.argv[3]).read_text(), int(sys.argv[2]))
        print('PASS exact QEMU power-control observation evidence')
    else:
        unittest.main()
