#!/usr/bin/env python3
"""Replay appeared-but-offline charging telemetry through the actual shell gate."""
import os
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'scripts/device/load-persistent-root-power-usb.sh'

def function(text,name):
    begin=text.index(name+'() {')
    return text[begin:text.index('\n}',begin)+2]

class ReadinessTest(unittest.TestCase):
    def test_captured_failure_is_not_an_s12_probe_or_automatic_fallback(self):
        fixture=json.loads((REPO/'tests/fixtures/native-wifi/s12-mode-v8-usb-offline.json').read_text())
        path=REPO/'scripts/host/run-persistent-root-storage-live-cycle.py'
        sys.path.insert(0,str(path.parent))
        spec=importlib.util.spec_from_file_location('s12_readiness_stages',path)
        parser=importlib.util.module_from_spec(spec); sys.modules[spec.name]=parser
        spec.loader.exec_module(parser)
        record=parser.parse_stage_record(fixture['target_record'].encode())
        self.assertEqual((record.stage,record.state,record.detail),
                         ('ufs-ready','FAIL','power-usb-usb-offline'))
        for key in ('target_ssh_seen','s12_probe_started','radio_probe_started',
                    'automatic_v11_fallback','safe_to_retry_consumed_target'):
            self.assertFalse(fixture[key])
        self.assertIsNone(fixture['usb_online_later_in_same_target_boot'])

    def run_gate(self,case,deadline=20,attempt=0):
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
        payload=(stub+f'case={case}\ntelemetry_deadline={deadline}\nattempt={attempt}\n'+
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

if __name__=='__main__': unittest.main()
