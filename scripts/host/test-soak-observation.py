"""Offline tests for a proposed soak monitor, never physical S07 PASS."""
import copy,importlib.util,json,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('observe',Path(__file__).with_name('soak-observation.py'))
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class Tests(unittest.TestCase):
 def test_timing_contract_rejects_shortening_or_overcommit(self):
  c=json.loads((Path(__file__).resolve().parents[2]/'configs/release-acceptance.json').read_text());M.timing(c)
  for key,value in (('observation_seconds',3599),('warmup_seconds',61),('heartbeat_seconds',True),('max_file_windows',129),('cleanup_seconds',100)):
   changed=copy.deepcopy(c);changed['defaults']['server_soak'][key]=value
   with self.assertRaises(ValueError):M.timing(changed)
 def test_continuous_records_and_cmdline_not_panic(self):
  self.assertEqual(M.kmsg(['5,726,1000,-;Kernel command line: panic=10 oops=panic\n','6,727,2000,-;ordinary progress\n'],725),727)
 def test_new_error_classes(self):
  for text in ('WARNING: drivers/spmi/spmi-pmic-arb.c:340','BUG: sleeping function','Oops: test',
   'Kernel panic - not syncing','sda: I/O error','EXT4-fs error (device loop1)',
   'EXT4-fs (sda23): Remounting filesystem read-only','ufshcd: command failed','UFS fatal error',
   'watchdog: soft lockup','task blocked for more than 120 seconds'):
   with self.subTest(text=text),self.assertRaises(ValueError):M.kmsg(['4,726,1000,-;'+text+'\n'],725)
 def test_log_loss_replay_or_truncation(self):
  for raw in ('6,727,1,-;gap\n','6,725,1,-;replay\n','6,726,1,-;truncated','6,726,1,-;'+('x'*8193)+'\n'):
   with self.assertRaises(ValueError):M.kmsg([raw],725)
  with self.assertRaises(ValueError):M.kmsg([],False)
 def test_error_counter_missing_changed_or_reset(self):
  before={name:dict(status='present',value='0') for name in ('loop1','sda23','sda24')}
  M.ext4(before,before)
  for changed in ({'status':'absent'},{'value':'1'},{'value':0}):
   after=copy.deepcopy(before);after['loop1'].update(changed)
   with self.assertRaises(ValueError):M.ext4(before,after)
  older=copy.deepcopy(before);older['loop1']['value']='1'
  with self.assertRaises(ValueError):M.ext4(older,before)
 def test_heartbeat_identity_gap_and_finite_time(self):
  before=dict(identity={'boot':'exact'},host_monotonic=10,target_uptime=20)
  after=dict(before,host_monotonic=20,target_uptime=30);M.progress(before,after,before['identity'])
  for change in ({'identity':{}},{'host_monotonic':40},{'target_uptime':20},{'target_uptime':float('nan')},{'host_monotonic':True}):
   bad=dict(after,**change)
   with self.assertRaises(ValueError):M.progress(before,bad,before['identity'])
 def test_real_backing_activity_not_just_successful_cached_calls(self):
  before={name:' '.join(['0']*17) for name in ('loop1','sda23')}
  fields=['0']*17;fields[2]=fields[6]=str(2*64*1024**2//512)
  after={name:' '.join(fields) for name in before};M.io_progress(before,after,2)
  for change in ({'loop1':before['loop1']},{'sda23':'malformed'}):
   with self.assertRaises(ValueError):M.io_progress(before,dict(after,**change),2)
  with self.assertRaises(ValueError):M.io_progress(after,before,2)
  with self.assertRaises(ValueError):M.io_progress(before,after,True)
 def test_captured_buffered_loop_discrepancy_is_not_storage_read_proof(self):
  # Stopped live S07: loop1 reads were real block I/O but its buffered backing
  # file satisfied them without corresponding UFS reads (loop/dio=0).
  before={name:' '.join(['0']*17) for name in ('loop1','sda23')};after={}
  for name,reads,writes in (('loop1',34493964288,1280344064),('sda23',8192,1369858048)):
   fields=['0']*17;fields[2]=str(reads//512);fields[6]=str(writes//512);after[name]=' '.join(fields)
  with self.assertRaisesRegex(ValueError,'backing-device'):M.io_progress(before,after,19)
if __name__=='__main__':unittest.main()
