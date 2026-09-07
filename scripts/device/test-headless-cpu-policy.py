"""Boot policy API, exact archive members and optional runtime installation."""
import copy,importlib.util,json,os,signal,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('policy',R/'scripts/device/headless-cpu-policy.py')
F=load('policy_fixtures',R/'scripts/device/test-cpu-frequency-cap.py')
A=load('policy_archive',R/'scripts/device/build-native-wifi-boot-initramfs.py')
class Tests(unittest.TestCase):
 def test_boot_apply_and_restart_retain_caps_without_daemon(self):
  b=F.Backend();v=M.apply(F.M,b,lambda:None)
  self.assertTrue(v['policy_retained']);self.assertEqual(v['restoration'],'NOT REQUESTED')
  self.assertEqual({n:p['maximum'] for n,p in b.snapshot().items()},F.M.CAPS)
  self.assertEqual(M.apply(F.M,b,lambda:None)['after'],v['after'])
  self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
 def test_interrupted_boot_application_restores_prior_values(self):
  for sig in (signal.SIGTERM,signal.SIGALRM):
   b=F.Backend();original=b.snapshot()
   def gate():
    if b.writes:signal.getsignal(sig)(sig,None)
   with self.subTest(signal=sig),self.assertRaises(InterruptedError):M.apply(F.M,b,gate)
   self.assertEqual(b.snapshot(),original)
 def test_existing_timer_refuses_before_entry(self):
  b=F.Backend()
  with patch.object(signal,'getitimer',return_value=(1.,0.)),self.assertRaises(ValueError):M.apply(F.M,b,lambda:None)
  self.assertEqual(b.writes,[])
 def test_composition_is_optional_complete_and_exact(self):
  A.verify_headless_cpu_composition({});members={};changed=A.install_headless_cpu_policy(members)
  self.assertEqual(len(changed),3);A.verify_headless_cpu_composition(members)
  for name in changed:
   bad=copy.deepcopy(members);del bad[name]
   with self.assertRaises(ValueError):A.verify_headless_cpu_composition(bad)
   bad=copy.deepcopy(members);fields,data=bad[name];bad[name]=(fields,data+b'altered')
   with self.assertRaises(ValueError):A.verify_headless_cpu_composition(bad)
   bad=copy.deepcopy(members);bad[name][0][4]=2
   with self.assertRaises(ValueError):A.verify_headless_cpu_composition(bad)
 def test_unit_orders_policy_before_radio_without_display_or_restart(self):
  unit=(R/'packaging/arch/rog5-headless-cpu-policy.service').read_text()
  for line in ('Requires=rog5-p2-ready.service','After=rog5-p2-ready.service',
   'Before=rog5-wifi-radio.service basic.target shutdown.target','Restart=no','RemainAfterExit=yes'):
   self.assertIn(line,unit)
  self.assertNotIn('display',unit);self.assertNotIn('ExecStop=',unit)
  self.assertIn('ProtectKernelTunables=yes',unit)
  self.assertEqual([v for v in unit.splitlines() if v.startswith('ReadWritePaths=')],
   ['ReadWritePaths=/sys/devices/system/cpu/cpufreq/'+name+'/scaling_max_freq' for name in F.M.CAPS])
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'rog5-headless-cpu-policy.service';path.write_text(unit)
   for name in ('rog5-p2-ready','rog5-wifi-radio','rog5-wifi-failure'):
    (root/(name+'.service')).write_text('[Unit]\nDefaultDependencies=no\n[Service]\nType=oneshot\nExecStart=/bin/true\n')
   subprocess.run(['systemd-analyze','verify',str(path)],check=True,capture_output=True,timeout=10)
 def test_guard_rejects_wrong_boot_device_power_and_scope(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);boot='96b722da-4ddc-4611-b813-a62149df541f'
   def put(path,value):
    p=root/path.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
   put('/proc/device-tree/compatible','asus,rog-phone5\0qcom,sm8350\0')
   put('/proc/sys/kernel/random/boot_id',boot)
   for key,value in dict(health='Good',temp='303',voltage_now='8500000').items():put('/sys/class/power_supply/qcom-battmgr-bat/'+key,value)
   put('/sys/class/power_supply/qcom-battmgr-usb/online','1')
   put('/sys/class/thermal/thermal_zone0/temp','47100')
   for i in range(117):put('/sys/class/block/sdz'+str(i)+'/ro','1')
   p2=dict(status='PASS',attested_boot_id=boot,kernel=os.uname().release,physical_blocks='117',root_mount='native-root-ro-noload')
   with patch.object(M,'Path',side_effect=lambda p:root/str(p).lstrip('/')),patch.object(M.os,'geteuid',return_value=0),patch.object(M,'record',return_value=p2):
    self.assertEqual(M.guard(),boot)
    for path,bad in (('/proc/device-tree/compatible','other\0'),('/proc/sys/kernel/random/boot_id','bad'),
     ('/sys/class/power_supply/qcom-battmgr-bat/health','Overheat'),('/sys/class/power_supply/qcom-battmgr-bat/temp','400'),
     ('/sys/class/power_supply/qcom-battmgr-bat/voltage_now','6900000'),('/sys/class/power_supply/qcom-battmgr-usb/online','0'),
     ('/sys/class/thermal/thermal_zone0/temp','60000'),('/sys/class/block/sdz0/ro','0')):
     before=(root/path.lstrip('/')).read_text();put(path,bad)
     with self.subTest(path=path),self.assertRaises(ValueError) as failure:M.guard()
     if path=='/sys/class/thermal/thermal_zone0/temp':
      # V6's retained journal proved thermal refusal but lost the sensor/value.
      self.assertIn('thermal_zone0=60000 mC; required <60000 mC',str(failure.exception))
     put(path,before)
    thermal='/sys/class/thermal/thermal_zone0/temp'
    put(thermal,'59999');self.assertEqual(M.guard(),boot)
    put(thermal,'unsupported')
    with self.assertRaisesRegex(ValueError,'thermal_zone0 read error: ValueError'):M.guard()
    (root/thermal.lstrip('/')).unlink()
    (root/thermal.lstrip('/')).mkdir()
    with self.assertRaisesRegex(ValueError,'thermal_zone0 read error: IsADirectoryError'):M.guard()
    (root/thermal.lstrip('/')).rmdir()
    with self.assertRaisesRegex(ValueError,'no thermal zones'):M.guard()
    p2['attested_boot_id']='stale'
    with self.assertRaises(ValueError):M.guard()
 def test_p2_record_has_no_symlink_or_duplicate_field_escape(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'p2';p.write_text('status=PASS\n');p.chmod(0o444)
   with F.Tests().owned():
    self.assertEqual(M.record(p),dict(status='PASS'))
    p.chmod(0o644);p.write_text('status=PASS\nstatus=FAIL\n');p.chmod(0o444)
    with self.assertRaises(ValueError):M.record(p)
    p.chmod(0o644);p.write_text('status=PASS\n')
    with self.assertRaises(ValueError):M.record(p)
    p.chmod(0o444);link=p.with_name('link');link.symlink_to(p.name)
    with self.assertRaises(OSError):M.record(link)
 def test_runtime_installs_only_complete_opt_in(self):
  runtime=(R/'initramfs/native-wifi/runtime').read_text();start=runtime.index('install_headless_cpu_policy() {')
  body=runtime[start:runtime.index('\n}',start)+2]
  for scenario in ('absent','complete','partial','symlink','display','existing'):
   with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)/'payload';units=Path(tmp)/'units'
    (root/'units').mkdir(parents=True);(units/'sysinit.target.wants').mkdir(parents=True)
    if scenario!='absent':
     for name,path in A.headless_cpu_files().items():(root/name).write_bytes(path.read_bytes());(root/name).chmod(0o644)
    if scenario=='partial':(root/'cpu-frequency-cap.py').unlink()
    if scenario=='symlink':(root/'cpu-frequency-cap.py').rename(root/'real');(root/'cpu-frequency-cap.py').symlink_to('real')
    if scenario=='existing':(units/'rog5-wifi-radio.service.d').mkdir()
    script='set -eu\nroot='+str(root)+'\ndisplay_diagnostic='+('1' if scenario=='display' else '0')+'\n'
    script+='stat() { command stat "$@" | sed "s/^[0-9]*:[0-9]*:/0:0:/"; }\n'+body+'\ninstall_headless_cpu_policy '+str(units)
    p=subprocess.run(['sh','-c',script],capture_output=True)
    self.assertEqual(p.returncode==0,scenario in ('absent','complete'),p.stderr)
    if scenario=='complete':
     self.assertEqual((units/'rog5-headless-cpu-policy.service').read_bytes(),(R/'packaging/arch/rog5-headless-cpu-policy.service').read_bytes())
     self.assertEqual(os.readlink(units/'sysinit.target.wants/rog5-headless-cpu-policy.service'),'../rog5-headless-cpu-policy.service')
     self.assertEqual((units/'rog5-wifi-radio.service.d/10-cpu-policy.conf').read_text(),'[Unit]\nRequires=rog5-headless-cpu-policy.service\nAfter=rog5-headless-cpu-policy.service\n')
if __name__=='__main__':unittest.main()
