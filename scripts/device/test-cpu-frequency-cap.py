"""Bounded CPU-cap transaction tests; no real sysfs/device writes."""
import copy,importlib.util,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('cap',Path(__file__).with_name('cpu-frequency-cap.py'))
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
def fixture():
 return {name:dict(cpus=cpus,driver='qcom-cpufreq-hw',governor='schedutil',minimum=minimum,
  maximum=maximum,frequencies=[minimum,cap,maximum]) for name,cpus,minimum,maximum,cap in
  (('policy0','0 1 2 3',300000,1804800,1209600),('policy4','4 5 6',710400,2419200,1555200),
   ('policy7','7',844800,2841600,1555200))}
class Backend:
 def __init__(self):self.value=fixture();self.writes=[];self.failure=None
 def snapshot(self):return copy.deepcopy(self.value)
 def set_maximum(self,name,value):
  self.writes.append((name,value))
  if self.failure and len(self.writes)==self.failure:raise OSError('injected write failure')
  self.value[name]['maximum']=value
class Tests(unittest.TestCase):
 def test_async_qos_apply_and_restore(self):
  class Delayed(Backend):
   def __init__(self):super().__init__();self.pending={}
   def set_maximum(self,name,value):
    self.writes.append((name,value));self.pending[name]=[value,2]
   def snapshot(self):
    for name,(value,remaining) in list(self.pending.items()):
     if remaining==0:self.value[name]['maximum']=value;del self.pending[name]
     else:self.pending[name][1]-=1
    return super().snapshot()
  b=Delayed();original=b.snapshot()
  result=M.run(b,lambda:None,b.snapshot)
  self.assertEqual({n:p['maximum'] for n,p in result['action'].items()},M.CAPS)
  self.assertEqual(b.snapshot(),original);self.assertEqual(len(b.writes),6)
 def test_failed_write_cancels_pending_qos_even_when_readback_is_old(self):
  class Pending(Backend):
   def set_maximum(self,name,value):
    self.writes.append((name,value));self.pending=(name,value)
    if len(self.writes)==1:raise OSError('request accepted before interrupted return')
  b=Pending();original=b.snapshot()
  with self.assertRaises(OSError):M.run(b,lambda:None,lambda:self.fail('action ran'))
  self.assertEqual(b.pending,('policy0',original['policy0']['maximum']))
  self.assertEqual(b.writes,[('policy0',M.CAPS['policy0']),('policy0',original['policy0']['maximum'])])
 def test_action_sees_caps_and_exact_restoration(self):
  b=Backend();original=b.snapshot();seen=[]
  result=M.run(b,lambda:seen.append('gate'),lambda: b.snapshot())
  self.assertEqual({n:v['maximum'] for n,v in result['action'].items()},M.CAPS)
  self.assertEqual(b.snapshot(),original);self.assertEqual(result['restoration'],'PASS')
  self.assertGreater(len(seen),3);self.assertEqual(len(b.writes),6)
 def test_all_policies_validated_before_any_write(self):
  for key,value in (('cpus','4 5 6 7'),('driver','other'),('governor','performance'),
   ('minimum',1600000),('maximum',1400000),('frequencies',[710400,2419200])):
   b=Backend();b.value['policy4'][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):M.run(b,lambda:None,lambda:None)
   self.assertEqual(b.writes,[])
 def test_unknown_missing_and_boolean_values(self):
  for change in ('extra','missing','bool'):
   b=Backend()
   if change=='extra':b.value['policy8']=b.value['policy7']
   if change=='missing':del b.value['policy7']
   if change=='bool':b.value['policy7']['maximum']=True
   with self.subTest(change=change),self.assertRaises(ValueError):M.run(b,lambda:None,lambda:None)
   self.assertEqual(b.writes,[])
 def test_partial_apply_restores_only_entered_operations(self):
  b=Backend();original=b.snapshot();b.failure=2
  with self.assertRaises(OSError):M.run(b,lambda:None,lambda:None)
  self.assertEqual(b.snapshot(),original)
  self.assertNotIn(('policy7',M.CAPS['policy7']),b.writes)
 def test_action_error_and_interrupt_restore(self):
  for error in (ValueError('load failed'),KeyboardInterrupt()):
   b=Backend();original=b.snapshot()
   def action():raise error
   with self.subTest(error=type(error)),self.assertRaises(type(error)):M.run(b,lambda:None,action)
   self.assertEqual(b.snapshot(),original)
 def test_guard_failure_after_first_write_restores(self):
  b=Backend();original=b.snapshot()
  def guard():
   if b.writes:raise ValueError('unsafe power')
  with self.assertRaises(ValueError):M.run(b,guard,lambda:None)
  self.assertEqual(b.snapshot(),original)
 def test_external_policy_change_is_not_overwritten(self):
  b=Backend()
  def action():b.value['policy4']['maximum']=1324800
  with self.assertRaisesRegex(ValueError,'restoration'):M.run(b,lambda:None,action)
  self.assertEqual(b.value['policy4']['maximum'],1324800)
  self.assertEqual(b.value['policy0']['maximum'],1804800)
  self.assertEqual(b.value['policy7']['maximum'],2841600)
 def test_noop_readback_never_runs_action(self):
  b=Backend();b.set_maximum=lambda *args:b.writes.append(args);called=[]
  with patch.object(M,'SETTLE_SECONDS',.02),self.assertRaisesRegex(ValueError,'deadline'):M.run(b,lambda:None,lambda:called.append(True))
  self.assertEqual(called,[])
  self.assertEqual(b.writes,[('policy0',M.CAPS['policy0']),('policy0',fixture()['policy0']['maximum'])])
 def test_unexpected_intermediate_policy_refuses_without_retry(self):
  b=Backend()
  def write(name,value):b.writes.append((name,value));b.value[name]['maximum']=998400
  b.set_maximum=write
  with self.assertRaisesRegex(ValueError,'restoration'):M.run(b,lambda:None,lambda:self.fail('action ran'))
  self.assertEqual(b.writes,[('policy0',M.CAPS['policy0'])])
 def disk(self,root):
  root.chmod(0o755)
  for name,p in fixture().items():
   d=root/name;d.mkdir(mode=0o755);(d/'stats').mkdir(mode=0o755)
   fields={'related_cpus':p['cpus'],'scaling_driver':p['driver'],'scaling_governor':p['governor'],
    'scaling_min_freq':str(p['minimum']),'scaling_max_freq':str(p['maximum']),
    'stats/time_in_state':'\n'.join(str(v)+' 1' for v in p['frequencies'])}
   for field,value in fields.items():(d/field).write_text(value+'\n');(d/field).chmod(0o644)
 def owned(self):
  original=os.fstat
  def fstat(fd):
   v=list(original(fd));v[4]=v[5]=0;return os.stat_result(v)
  return patch.object(M.os,'fstat',side_effect=fstat)
 def test_real_descriptor_io_restores_fixture_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.disk(root);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with self.owned():
     b=M.Sysfs(fd)
     try:
      original=b.snapshot();M.run(b,lambda:None,lambda:None);self.assertEqual(b.snapshot(),original)
     finally:b.close()
   finally:os.close(fd)
 def test_symlink_policy_stats_or_attribute_refused(self):
  for relative in ('policy4','policy4/stats','policy4/scaling_max_freq'):
   with self.subTest(relative=relative),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);self.disk(root);path=root/relative;retained=path.with_name('retained')
    path.rename(retained);path.symlink_to(retained.name);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    try:
     with self.owned(),self.assertRaises((OSError,ValueError)):
      b=M.Sysfs(fd)
      try:b.snapshot()
      finally:b.close()
    finally:os.close(fd)
 def test_policy_path_replacement_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.disk(root);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with self.owned():
     b=M.Sysfs(fd)
     try:
      (root/'policy4').rename(root/'retained');(root/'policy4').mkdir()
      with self.assertRaisesRegex(ValueError,'pathname changed'):b.snapshot()
     finally:b.close()
   finally:os.close(fd)
 def test_lease_is_bounded_and_restores_handlers_and_limits(self):
  b=Backend();original=b.snapshot();clock=[0];observed=[]
  prior={n:M.signal.getsignal(n) for n in (M.signal.SIGALRM,M.signal.SIGTERM,M.signal.SIGHUP,M.signal.SIGINT)}
  result=M.lease(b,lambda:None,observed.append,3,clock=lambda:clock[0],pause=lambda n:clock.__setitem__(0,clock[0]+n))
  self.assertEqual(clock,[3]);self.assertEqual(len(observed),3);self.assertEqual(b.snapshot(),original)
  self.assertEqual(result['restoration'],'PASS');self.assertEqual(M.signal.getitimer(M.signal.ITIMER_REAL),(0.0,0.0))
  self.assertEqual(prior,{n:M.signal.getsignal(n) for n in prior})
 def test_term_hup_and_alarm_restore_but_do_not_pass(self):
  for sig in (M.signal.SIGTERM,M.signal.SIGHUP,M.signal.SIGALRM):
   b=Backend();original=b.snapshot()
   def observed(unused):M.signal.getsignal(sig)(sig,None)
   with self.subTest(signal=sig),self.assertRaises(InterruptedError):M.lease(b,lambda:None,observed,3)
   self.assertEqual(b.snapshot(),original)
 def test_invalid_lease_refuses_before_writes(self):
  for duration in (True,0,-1,721):
   b=Backend()
   with self.assertRaises(ValueError):M.lease(b,lambda:None,lambda _:None,duration)
   self.assertEqual(b.writes,[])
 def test_existing_alarm_is_not_replaced(self):
  b=Backend()
  with patch.object(M.signal,'getitimer',return_value=(1.0,0.0)),patch.object(M.signal,'setitimer') as timer:
   with self.assertRaisesRegex(ValueError,'existing alarm'):M.lease(b,lambda:None,lambda _:None,3)
   timer.assert_not_called()
  self.assertEqual(b.writes,[])
 def test_world_writable_sysfs_fixture_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.disk(root);(root/'policy4/scaling_max_freq').chmod(0o666)
   fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with self.owned():
     b=M.Sysfs(fd)
     try:
      with self.assertRaisesRegex(ValueError,'unsafe CPU attribute'):b.snapshot()
     finally:b.close()
   finally:os.close(fd)
if __name__=='__main__':unittest.main()
