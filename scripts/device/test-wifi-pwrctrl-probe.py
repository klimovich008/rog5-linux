#!/usr/bin/env python3
"""Validate the QEMU-only power-control probe and diagnostic pause evidence."""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
PATCH = REPO / 'patches/linux/diagnostic/pci-pwrctrl-pwrseq-observation.patch'
FIXTURE = REPO / 'tools/wifi_pwrctrl_probe/rog5-wifi-pwrctrl-probe.c'
WCN_PATCH = REPO / 'patches/linux/diagnostic/pwrseq-qcom-wcn-serial-observation.patch'


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


def validate_rail_log(text, pause):
    if re.search(r'Kernel panic|Oops:|BUG:', text) or 'ROG5_QEMU_PWRCTRL_END' not in text:
        raise ValueError('QEMU rail fixture did not finish')
    records = re.findall(r'\[\s*([\d.]+)\].*ROG5_WCN_RAIL index=(\d+) supply=(\S+) stage=(enter|return) result=(-?\d+) cached_uv=(-?\d+) voltage_state=(\w+) mode=(-?\d+) mode_state=(\w+) enabled=(-?\d+) enabled_state=(\w+)', text)
    if pause in (0, 1001):
        if 'ROG5_WCN_RAIL index=' in text:
            raise ValueError('disabled/invalid serial observation ran')
    elif pause == 250:
        if len(records) != 20:
            raise ValueError('rail observations are incomplete or unclassified')
        for i, record in enumerate(records):
            timestamp, index, supply, stage, ret, uv, vs, mode, ms, enabled, es = record
            if int(index) != i // 2 or stage != ('enter' if i % 2 == 0 else 'return') or ret != '0':
                raise ValueError('rail order or result changed')
            if i and float(timestamp) - float(records[i-1][0]) < 0.249:
                raise ValueError('rail pause missing')
            if int(mode) > 2147483647:
                raise ValueError('unsigned error presented as a mode')
            if vs != ('error' if int(uv) < 0 else 'present') or es != ('error' if int(enabled) < 0 else 'present'):
                raise ValueError('getter status incorrect')
            if ms != ('error' if int(mode) < 0 else 'absent' if mode == '0' else 'present'):
                raise ValueError('mode status incorrect')
        for stage in ('clock-enter', 'clock-return', 'wlan-gpio-enter', 'wlan-gpio-return'):
            if f'ROG5_WCN_OBSERVE stage={stage} result=0' not in text:
                raise ValueError('later boundary missing')
    else:
        raise ValueError('unsupported rail fixture case')
    expected = -517 if pause == 1001 else 0
    if f'ROG5_PWRCTRL_DUMMY_POWER_ON_RETURN={expected}' not in text:
        raise ValueError('unexpected serial power result')


class PwrctrlProbeTest(unittest.TestCase):
    def test_auto_ack_is_not_a_successful_enable_or_radio_test(self):
        fixture=json.loads((REPO/'tests/fixtures/native-wifi/s12-auto-enable-reset.json').read_text())
        self.assertEqual(fixture['mode_api_return'],0)
        self.assertEqual(fixture['held_cached_mode'],2)
        self.assertIn('addr: 0x40108 data: 0x6',fixture['mode_ack'])
        for key in ('held_api_return_observed','held_voltage_submission_observed',
                    'held_enable_submission_observed','radio_probe_started',
                    'pcie_or_gpio_activation_started','auto_mode_alone_fixes_reset',
                    'safe_to_retry_consumed_target'):
            self.assertFalse(fixture[key])
        self.assertTrue(fixture['trace_tail_may_be_lost'])
        self.assertIsNone(fixture['proven_faulting_instruction'])

    def test_rsc_submission_is_not_completed_voltage_or_power(self):
        fixture = json.loads((REPO / 'tests/fixtures/native-wifi/s12-voltage-submit-reset.json').read_text())
        text = '\n'.join(fixture['kmsg'] + fixture['trace']) + '\nROG5_QEMU_PWRCTRL_END\n'
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            validate_rail_log(text, fixture['pause_ms'])
        self.assertTrue(fixture['voltage_submission_proven'])
        self.assertEqual(int('548', 16), fixture['voltage_request_mv'])
        self.assertIn('msgid: 0x10108', fixture['trace'][-2])
        self.assertIn('result=0', fixture['trace'][-1])
        for key in ('voltage_call_return_observed', 'ack_observed',
                    'enable_request_observed', 'absence_proves_ack_never_happened',
                    'safe_to_retry_consumed_target'):
            self.assertFalse(fixture[key])
        self.assertIsNone(fixture['proven_faulting_rail_or_gpio'])

    def test_live_s12_prefix_is_not_a_completed_power_sequence(self):
        for name in ('s12-entry-reset.json', 's12-ret-entry-reset.json'):
            with self.subTest(name=name):
                fixture = json.loads((REPO / 'tests/fixtures/native-wifi' / name).read_text())
                text = '\n'.join(fixture['kmsg']) + '\nROG5_QEMU_PWRCTRL_END\n'
                with self.assertRaisesRegex(ValueError, 'incomplete'):
                    validate_rail_log(text, fixture['pause_ms'])
                self.assertEqual(sum('stage=return result=0' in line for line in fixture['kmsg']), 2)
                self.assertFalse(fixture['s12_enable_call_entry_proven'])
                entry_time = float(re.match(r'\[([\d.]+)\]', fixture['kmsg'][-1])[1])
                self.assertLess(fixture['last_delivered_trace_time'], entry_time + .250)
                pon = fixture['paired_pon']
                self.assertEqual((pon['push_after'] - pon['push_before']) % pon['ring_bytes'], pon['new_bytes'])
                self.assertEqual(pon['warm_reset_count_after'] - pon['warm_reset_count_before'], 1)
                self.assertFalse(fixture['cached_getters_are_physical_measurements'])
                self.assertFalse(fixture['safe_to_retry_consumed_target'])
                self.assertIsNone(fixture['proven_faulting_rail_or_gpio'])
                if 'initial_mode_property' in fixture:
                    self.assertEqual(fixture['initial_mode_property'], 0)
                    self.assertIn('mode=8 mode_state=present', fixture['kmsg'][-1])
                    self.assertFalse(fixture['mode_vote_alone_fixes_reset'])

    def test_native_probe_loads_software_first_and_checks_pci_before_radio(self):
        source = (REPO / 'scripts/device/probe-native-wifi.sh').read_text()
        start = source.index('# Load software before')
        block = source[start:source.index('for attempt in $(seq 1 60)', start)]
        roots = (REPO / 'configs/kernel/rog5-native-wifi-module-roots').read_text()
        for case in ('exact', 'late-attributes', 'wrong-id', 'never-enumerates'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); (root/'load-roots.txt').write_text(roots)
                (root/'pci').mkdir()
                replay = block.replace('/sys/bus/pci/devices/0000:01:00.0', str(root/'pci'))
                replay = replay.replace('ls -A /sys/bus/pci/devices', 'true')
                replay = replay.replace('timeout -k 2 30 "$root/module-once" "$root/rog5-wifi-activate.ko"', 'activate')
                replay = replay.replace('cat /sys/module/rog5_wifi_activate/parameters/result', 'echo 0')
                setup = f'root={root}\nlog={root}/calls\n'
                setup += 'activate() { :; }\n'
                setup += 'fail() { exit 77; }; sleep() { :; }; guard_count=0\n'
                setup += 'guard() { guard_count=$((guard_count+1));\n'
                if case == 'late-attributes':
                    setup += 'if [ "$guard_count" = 2 ]; then\n'
                    for field, value in {'device':'0x1103','subsystem_vendor':'0x17cb','subsystem_device':'0x0108'}.items():
                        setup += f'printf "%s\\n" {value} >{root}/pci/{field}\n'
                    setup += 'fi\n'
                setup += '}\n'
                setup += 'load_one() { printf "%s\\n" "$1" >>"$log";\n'
                if case != 'never-enumerates':
                    setup += 'if [ "$1" = phy-qcom-qmp-pcie ]; then\n'
                    values = {'vendor': '0xdead' if case == 'wrong-id' else '0x17cb',
                              'device':'0x1103','subsystem_vendor':'0x17cb','subsystem_device':'0x0108'}
                    if case == 'late-attributes':
                        values = {'vendor': '0x17cb'}
                    for field, value in values.items():
                        setup += f'printf "%s\\n" {value} >{root}/pci/{field}\n'
                    setup += 'fi\n'
                setup += '}\n'
                (root/'replay.sh').write_text(setup + replay + f'\nprintf "%s" "$guard_count" >{root}/guards\n')
                result = subprocess.run(['sh', str(root/'replay.sh')], capture_output=True)
                calls = (root/'calls').read_text().splitlines()
                self.assertLess(calls.index('mhi'), calls.index('phy-qcom-qmp-pcie'))
                self.assertEqual(calls.count('phy-qcom-qmp-pcie'), 1)
                if case in ('exact', 'late-attributes'):
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(calls[-1], 'ath11k_pci')
                    self.assertEqual(len(calls), len(roots.splitlines()))
                    if case == 'late-attributes':
                        self.assertGreaterEqual(int((root/'guards').read_text()), 2)
                else:
                    self.assertEqual(result.returncode, 77)
                    self.assertNotIn('ath11k_pci', calls)

    def test_serial_patch_is_default_off_and_never_retunes_supplies(self):
        subprocess.run(['git', 'apply', '--numstat', str(WCN_PATCH)], check=True, stdout=subprocess.PIPE)
        text = WCN_PATCH.read_text()
        added = '\n'.join(line[1:] for line in text.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('static unsigned int serial_observation_ms;', added)
        self.assertIn('module_param(serial_observation_ms, uint, 0400)', added)
        self.assertIn('serial_observation_ms > 1000', added)
        self.assertIn('ctx->pdata != &pwrseq_wcn6855_of_data', added)
        for forbidden in ('regulator_set_voltage', 'regulator_set_mode', 'regulator_set_load'):
            self.assertNotIn(forbidden, added)

    def test_actual_serial_loop_rolls_back_only_completed_enables(self):
        added = '\n'.join(line[1:] for line in WCN_PATCH.read_text().splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        start = added.index('static int pwrseq_qcom_wcn_enable_serial(')
        body = added[start:added.index('\n}', start)+2]
        harness = r'''
#include <assert.h>
#include <stddef.h>
struct regulator { int id; };
struct regulator_bulk_data { struct regulator *consumer; };
struct data { unsigned int num_vregs; };
struct pwrseq_qcom_wcn_ctx { struct data *pdata; struct regulator_bulk_data *regs; };
static int fail_at, attempts, observations, disabled, refs[10];
static int regulator_enable(struct regulator *r) {
 assert(r->id == attempts++);
 if (r->id == fail_at) return -5;
 refs[r->id]++; return 0;
}
static int regulator_bulk_disable(unsigned int n, struct regulator_bulk_data *r) {
 disabled = n;
 while (n) { --n; assert(refs[r[n].consumer->id] == 1); refs[r[n].consumer->id]--; }
 return 0;
}
static void pwrseq_qcom_wcn_observe_rail(struct pwrseq_qcom_wcn_ctx *c, unsigned int i, const char *s, int r) {
 (void)c; (void)i; (void)s; (void)r; observations++;
}
#define pr_info(...) ((void)0)
'''
        # pr_info consumes cleanup in the real kernel; keep that use in this harness.
        harness = harness.replace('#define pr_info(...) ((void)0)', '#define pr_info(...) ((void)cleanup)')
        main = r'''
int main(void) {
 struct regulator r[10]; struct regulator_bulk_data regs[10]; struct data d = {10};
 struct pwrseq_qcom_wcn_ctx c = {&d, regs};
 for (int f=-1; f<10; f++) {
  fail_at=f; attempts=observations=disabled=0;
  for (int i=0; i<10; i++) { r[i].id=i; regs[i].consumer=&r[i]; refs[i]=0; }
  int ret=pwrseq_qcom_wcn_enable_serial(&c);
  assert(ret == (f<0 ? 0 : -5));
  assert(attempts == (f<0 ? 10 : f+1)); assert(observations == attempts*2);
  assert(disabled == (f<0 ? 0 : f));
  for (int i=0; i<10; i++) assert(refs[i] == (f<0 ? 1 : 0));
 }
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'test.c').write_text(harness + body + main)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(root/'test.c'), '-o', str(root/'test')], check=True)
            subprocess.run([str(root/'test')], check=True)

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
        self.assertIn('.probe_type = PROBE_PREFER_ASYNCHRONOUS', text)
        self.assertIn('WRITE_ONCE(fixture_done, true)', text)
        self.assertNotIn('static bool complete;', text)

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
    if len(sys.argv) == 4 and sys.argv[1] in ('--validate-log', '--validate-rails'):
        validator = validate_rail_log if sys.argv[1] == '--validate-rails' else validate_log
        validator(Path(sys.argv[3]).read_text(), int(sys.argv[2]))
        print('PASS exact QEMU power-control observation evidence')
    else:
        unittest.main()
