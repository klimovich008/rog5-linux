#!/usr/bin/env python3
"""Only private filesystem fixtures; no host sysfs or device access."""
import json,os,signal,struct,subprocess,sys,tempfile,time,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[2]
# Observed LED-core fwnode layout: the leaf has uevent identity, no of_node link.
DIAG={
 'trigger':'[none] timer heartbeat',
 'uevent':'OF_NAME=led\nOF_FULLNAME=/soc@0/spmi@c440000/pmic@2/pwm/led@2\nOF_COMPATIBLE_N=0',
 'device/uevent':'DRIVER=qcom-spmi-lpg\nOF_NAME=pwm\nOF_FULLNAME=/soc@0/spmi@c440000/pmic@2/pwm\nOF_COMPATIBLE_0=qcom,pm8350c-pwm\nOF_COMPATIBLE_N=1',
}
RUNNER=[os.environ['ROG5_INDICATOR_TEST_RUNNER']] if os.environ.get('ROG5_INDICATOR_TEST_RUNNER') else []
FIXTURE=Path(os.environ['ROG5_INDICATOR_FIXTURE_BINARY'])
RACE=Path(os.environ['ROG5_INDICATOR_FD_FIXTURE_BINARY'])
def fixture(root):
    sysfs=root/'sys';led=sysfs/'devices/platform/soc@0/c440000.spmi/spmi-0/0-02/c440000.spmi:pmic@2:pwm/leds/green:status'
    parent=led.parent.parent;dt=sysfs/'firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/pwm';driver=sysfs/'bus/platform/drivers/qcom-spmi-lpg'
    for directory in (led,dt/'led@2',driver,sysfs/'class/leds',sysfs/'class/input'):directory.mkdir(parents=True,exist_ok=True)
    def link(path,target):path.symlink_to(os.path.relpath(target,path.parent))
    link(sysfs/'class/leds/green:status',led);link(led/'device',parent);link(parent/'of_node',dt);link(parent/'driver',driver)
    for name,value in (('brightness','0000000031'),('max_brightness','511'),('trigger',DIAG['trigger']),('uevent',DIAG['uevent'])):(led/name).write_text(value+'\n')
    (parent/'uevent').write_text(DIAG['device/uevent']+'\n')
    return sysfs/'class/leds/green:status'
class Contract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="rog5-led-contract-");self.root=Path(self.tmp.name);self.led=fixture(self.root)
    def tearDown(self):self.tmp.cleanup()
    def off(self):return subprocess.run([*RUNNER,str(FIXTURE),'--fixture-off',str(self.led)],capture_output=True,text=True,timeout=3)
    def refusal(self):
        before=(self.led/'brightness').read_text();r=self.off();self.assertNotEqual(r.returncode,0);self.assertEqual((self.led/'brightness').read_text(),before)
    def test_actual_missing_leaf_link_off_without_input(self):
        self.assertFalse((self.led/'of_node').exists());self.assertEqual(list((self.root/'sys/class/input').iterdir()),[])
        result=self.off();self.assertEqual(result.returncode,0,result.stderr);self.assertEqual((self.led/'brightness').read_text(),'0000000000\n')
    def test_wrong_leaf_fullname(self):
        p=self.led/'uevent';p.write_text(p.read_text().replace('led@2','led@3'));self.refusal()
    def test_missing_leaf_identity(self):(self.led/'uevent').write_text('OF_NAME=led\n');self.refusal()
    def test_duplicate_leaf_identity(self):
        p=self.led/'uevent';p.write_text(p.read_text()+'OF_NAME=led\n');self.refusal()
    def test_wrong_parent_fullname(self):
        p=self.led/'device/uevent';p.write_text(p.read_text().replace('pmic@2','pmic@3'));self.refusal()
    def test_wrong_parent_compatible(self):
        p=self.led/'device/uevent';p.write_text(p.read_text().replace('pm8350c','pm8350'));self.refusal()
    def test_duplicate_parent_driver(self):
        p=self.led/'device/uevent';p.write_text(p.read_text()+'DRIVER=qcom-spmi-lpg\n');self.refusal()
    def test_parent_of_node_wrong(self):
        p=self.led/'device/of_node';p.unlink();p.symlink_to(self.root);self.refusal()
    def test_leaf_dt_node_missing(self):(self.led/'device/of_node/led@2').rmdir();self.refusal()
    def test_leaf_dt_node_redirected(self):
        p=self.led/'device/of_node/led@2';p.rmdir();p.symlink_to(self.root);self.refusal()
    def test_wrong_driver(self):
        p=self.led/'device/driver';p.unlink();p.symlink_to(self.root);self.refusal()
    def test_wrong_maximum(self):(self.led/'max_brightness').write_text('255\n');self.refusal()
    def test_active_trigger(self):(self.led/'trigger').write_text('none [timer]\n');self.refusal()
    def test_symlink_brightness(self):
        p=self.led/'brightness';old=self.root/'other';p.rename(old);p.symlink_to(old);self.refusal()
    def test_uevent_symlink(self):
        p=self.led/'uevent';old=self.root/'other';p.rename(old);p.symlink_to(old);self.refusal()
    def test_brightness_replaced_after_validation(self):
        r=subprocess.run([*RUNNER,str(RACE),str(self.led)],capture_output=True,text=True,timeout=3)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('led.brightness_identity',r.stderr);self.assertEqual((self.led/'brightness').read_text(),'0000000031\n')
    def events(self,values):
        path=self.root/'events';path.write_bytes(b''.join(struct.pack('@llHHi',0,0,*v) for v in values));(self.led/'brightness').write_text('0000000000\n');return path
    def test_single_press_repeat_ignored_and_off(self):
        events=self.events([(1,116,0),(1,116,2),(1,114,1),(1,116,1),(1,116,1),(1,116,0)])
        r=subprocess.run([*RUNNER,str(FIXTURE),'--fixture',str(events),str(self.led),'1','180'],capture_output=True,text=True,timeout=3)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.count('state=on brightness=31'),1);self.assertIn('state=off brightness=0',r.stdout);self.assertEqual((self.led/'brightness').read_text(),'0000000000\n')
    def test_timer_failure_cleanup(self):
        events=self.events([(1,116,1)])
        r=subprocess.run([*RUNNER,str(FIXTURE),'--fixture',str(events),str(self.led),'0','180','timer-failure'],capture_output=True,text=True,timeout=3)
        self.assertNotEqual(r.returncode,0);self.assertIn('state=off brightness=0',r.stdout);self.assertEqual((self.led/'brightness').read_text(),'0000000000\n')
    def test_truncated_event_refused(self):
        events=self.events([]);events.write_bytes(b'bad')
        r=subprocess.run([*RUNNER,str(FIXTURE),'--fixture',str(events),str(self.led),'0','180'],capture_output=True,text=True,timeout=3)
        self.assertNotEqual(r.returncode,0);self.assertIn('input.event_alignment',r.stderr);self.assertEqual((self.led/'brightness').read_text(),'0000000000\n')
    def test_sigterm_turns_off(self):
        events=self.events([(1,116,1)])
        with (self.root/'stdout').open('w') as out,(self.root/'stderr').open('w') as err:
            p=subprocess.Popen([*RUNNER,str(FIXTURE),'--fixture',str(events),str(self.led),'1','5000'],stdout=out,stderr=err)
            try:
                deadline=time.monotonic()+2
                while 'state=on' not in (self.root/'stdout').read_text() and time.monotonic()<deadline:time.sleep(.01)
                self.assertIn('state=on',(self.root/'stdout').read_text());p.send_signal(signal.SIGTERM);self.assertEqual(p.wait(timeout=2),0)
            finally:
                if p.poll() is None:p.kill();p.wait()
        self.assertEqual((self.led/'brightness').read_text(),'0000000000\n')
if __name__=='__main__':unittest.main()
