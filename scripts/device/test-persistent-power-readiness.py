#!/usr/bin/env python3
"""Replay appeared-but-offline charging telemetry through the actual shell gate."""
import os
from pathlib import Path
import subprocess
import unittest

REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'scripts/device/load-persistent-root-power-usb.sh'

def function(text,name):
    begin=text.index(name+'() {')
    return text[begin:text.index('\n}',begin)+2]

class ReadinessTest(unittest.TestCase):
    def test_production_boot_continues_on_battery(self):
        p=self.run_gate('never',production=1)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('OBS battery',p.stdout)
        self.assertNotIn('FAIL',p.stdout)
        # the battery checks still apply in production
        p=self.run_gate('unsafe-later',production=1)
        self.assertIn('FAIL battery-temperature-unsafe',p.stdout)

    def run_gate(self,case,deadline=20,attempt=0,production=0):
        text=SOURCE.read_text()
        if 'wait_for_usb_online() {' in text:
            gate=function(text,'wait_for_usb_online')+'\nwait_for_usb_online\n'
        else:
            # Before the fix this is a single sample after node appearance.
            begin=text.index('battery_voltage=$(read_integer')
            end=text.index('[ "$usb_voltage" -ge',begin)
            gate=text[begin:end]
        stub=r'''
set -eu
battery=/fake/battery
usb=/fake/usb
step=0
fail() { printf 'FAIL %s step=%s\n' "$1" "$step"; exit 1; }
telemetry_seconds() { printf '%s\n' "$step"; }
power_observation() { printf 'OBS %s step=%s\n' "$1" "$step"; }
sleep() { step=$((step+1)); }
cat() {
 case $1 in
 */battery/voltage_now) if [ "$case" = unsafe-voltage ]; then echo 9300000; else echo 8627000; fi ;;
 */battery/temp)
  if [ "$case" = unsafe-temp ] || { [ "$case" = unsafe-later ] && [ "$step" -gt 0 ]; }; then echo 600; else echo 299; fi ;;
 */battery/health)
  case $case in bad-health) echo Overheat ;; missing-health) return 1 ;;
   health-lost) if [ "$step" -gt 0 ]; then echo Unknown; else echo Good; fi ;;
   *) echo Good ;; esac ;;
 */usb/online)
  case $case in
   missing) return 1 ;;
   invalid) echo 2 ;;
   never|unsafe-later|health-lost) echo 0 ;;
   delayed) if [ "$step" -lt 2 ]; then echo 0; else echo 1; fi ;;
   late) if [ "$step" -lt "$telemetry_deadline" ]; then echo 0; else echo 1; fi ;;
   *) echo 1 ;;
  esac ;;
 */usb/voltage_now) echo 5000000 ;;
 */usb/current_max) echo 500000 ;;
 *) return 1 ;;
 esac
}
'''
        payload=(stub+f'case={case}\ntelemetry_deadline={deadline}\nattempt={attempt}\nproduction={production}\n'+
                 function(text,'read_integer')+'\n'+gate+
                 'printf "PASS step=%s online=%s\\n" "$step" "$usb_online"\n')
        command=['sh']
        if os.environ.get('ROG5_TEST_BUSYBOX'):
            command=[os.environ['ROG5_TEST_QEMU'],os.environ['ROG5_TEST_BUSYBOX'],'sh']
        return subprocess.run(command,input=payload,text=True,capture_output=True,timeout=4)

    def test_appeared_but_offline_waits_for_valid_online_value(self):
        p=self.run_gate('delayed')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('PASS step=2 online=1',p.stdout)
        self.assertEqual(p.stdout.count('OBS waiting'),1)
        self.assertIn('OBS ready step=2',p.stdout)

    def test_immediate_ready_never_sleeps(self):
        p=self.run_gate('ready'); self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('PASS step=0 online=1',p.stdout)

    def test_deadline_and_node_wait_share_one_budget(self):
        for case,deadline,attempt,step in [('never',20,0,20),('late',20,0,20),
                                         ('delayed',1,0,1),('delayed',20,199,1)]:
            with self.subTest(case=case,deadline=deadline,attempt=attempt):
                p=self.run_gate(case,deadline,attempt)
                self.assertNotEqual(p.returncode,0)
                self.assertIn(f'FAIL usb-offline step={step}',p.stdout)

    def test_invalid_or_unsafe_telemetry_is_immediate_failure(self):
        for case,detail in [('unsafe-voltage','battery-voltage-unsafe'),
                            ('unsafe-temp','battery-temperature-unsafe'),
                            ('missing','usb-online-unavailable'),('invalid','usb-online-unavailable')]:
            with self.subTest(case=case):
                p=self.run_gate(case)
                self.assertNotEqual(p.returncode,0)
                self.assertIn(f'FAIL {detail} step=0',p.stdout)

    def test_battery_is_rechecked_while_waiting(self):
        p=self.run_gate('unsafe-later')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('FAIL battery-temperature-unsafe step=1',p.stdout)

    def test_health_must_be_good_before_ufs_and_throughout_wait(self):
        for case, detail, step in [('bad-health', 'battery-health-unsafe', 0),
                                  ('missing-health', 'battery-health-unavailable', 0),
                                  ('health-lost', 'battery-health-unsafe', 1)]:
            with self.subTest(case=case):
                result = self.run_gate(case)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'FAIL {detail} step={step}', result.stdout)

class StandbyBisectTest(unittest.TestCase):
    """The noadsp standby-bisect DTB (compose-standby-bisect-dtb.sh) is the only
    way past the battery/UCSI checks, and only in a production ramdisk."""

    def gate(self, production, props):
        import tempfile
        with tempfile.TemporaryDirectory() as tree:
            for path, value in props.items():
                Path(tree, path).parent.mkdir(parents=True, exist_ok=True)
                Path(tree, path).write_bytes(value.encode() + b'\0')
            body = function(SOURCE.read_text(), 'adsp_bisect_off').replace('/proc/device-tree', tree)
            command = ['sh']
            if os.environ.get('ROG5_TEST_BUSYBOX'):
                command = [os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX'], 'sh']
            return subprocess.run(command, input=f'production={production}\n' + body + '\n' +
                                  'adsp_bisect_off && echo SKIP || echo CHECK\n',
                                  text=True, capture_output=True, timeout=4).stdout.strip()

    ADSP = 'soc@0/remoteproc@3000000/'
    BISECT = {ADSP + 'status': 'disabled', ADSP + 'rog5,standby-bisect': 'noadsp',
              'pmic-glink/status': 'disabled'}

    def test_only_the_marked_noadsp_dtb_skips_the_checks(self):
        self.assertEqual(self.gate(1, self.BISECT), 'SKIP')
        for label, props, production in (
                ('development ramdisk', self.BISECT, 0),
                ('production DTB', {self.ADSP + 'status': 'okay'}, 1),
                ('ADSP disabled without marker', {self.ADSP + 'status': 'disabled',
                                                  'pmic-glink/status': 'disabled'}, 1),
                ('marker but ADSP enabled', dict(self.BISECT, **{self.ADSP + 'status': 'okay'}), 1),
                ('pmic-glink still enabled', dict(self.BISECT, **{'pmic-glink/status': 'okay'}), 1),
                ('other marker', dict(self.BISECT, **{self.ADSP + 'rog5,standby-bisect': 'noslpi'}), 1)):
            with self.subTest(label):
                self.assertEqual(self.gate(production, props), 'CHECK')

    def test_the_telemetry_checks_run_unless_bisecting(self):
        text = SOURCE.read_text()
        tail = text[text.index('\nif adsp_bisect_off; then'):]
        self.assertIn('\nelse\n\tcheck_power_telemetry\nfi\n', tail)
        self.assertLess(tail.index('check_power_telemetry'), tail.index('physical_count=0'))


if __name__=='__main__': unittest.main()
