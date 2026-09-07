"""Real scratch I/O with fixture identity; no phone, block writes or services."""
import contextlib,copy,importlib.util,io,json,os,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('soak_window',HERE/'soak-file-window.py');F=load('soak_fixture',HERE/'test-durability-target.py')
OPS=(HERE/'durability-file-ops.py').read_text();GUARD=(HERE/'durability-target.py').read_text()
class Tests(unittest.TestCase):
 def test_failed_guard_preserves_exact_rejected_sample_without_reread(self):
  for thermal in ({'thermal_zone11':'60000'},{}):
   state=dict(thermal=thermal,power={'temp':'300'},unrelated_private_value='do not log')
   error=ValueError('unsafe or absent thermal');output=io.StringIO()
   observe=unittest.mock.Mock(return_value=state)
   guard=dict(observe=observe,validate=unittest.mock.Mock(side_effect=error))
   with patch.object(M.os,'open') as opened,contextlib.redirect_stderr(output):
    with self.assertRaises(ValueError) as raised:M.backing_advice(guard,{})
    self.assertIs(raised.exception,error);opened.assert_not_called()
   observe.assert_called_once_with()
   line=output.getvalue().splitlines();self.assertEqual(len(line),1)
   self.assertTrue(line[0].startswith('soak-guard-evidence '))
   self.assertEqual(json.loads(line[0].split(' ',1)[1]),dict(thermal=thermal,power={'temp':'300'}))
 def test_diagnostic_failure_never_masks_original_refusal(self):
  error=ValueError('unsafe power')
  guard=dict(observe=lambda:dict(thermal={},power={}),validate=unittest.mock.Mock(side_effect=error))
  with patch.object(M,'print',side_effect=OSError('stderr unavailable'),create=True):
   with self.assertRaises(ValueError) as raised:M.checked_observation(guard,{})
  self.assertIs(raised.exception,error)
 def test_backing_cache_advice_is_fixed_read_only_and_rejects_bad_files(self):
  for wrong in (None,'symlink','mode','size','device'):
   with self.subTest(wrong=wrong),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);parent=root/'.rog5/userdata-rw/rog5/state';parent.mkdir(parents=True)
    path=parent/'server-state-v1.ext4'
    with path.open('wb') as f:f.truncate(4*1024**3 if wrong!='size' else 4096)
    path.chmod(0o600 if wrong!='mode' else 0o666)
    if wrong=='symlink':
     path.rename(parent/'retained');path.symlink_to('retained')
    opened=os.open;fstat=os.fstat;calls=[]
    def fixture_open(name,flags,*args,**kwargs):
     calls.append((name,flags));return opened(tmp if name=='/' else name,flags,*args,**kwargs)
    def root_owner(fd):
     s=list(fstat(fd));s[4]=s[5]=0;return os.stat_result(s)
    dev=path.stat().st_dev;device=f'{os.major(dev)}:{os.minor(dev)}'
    guard=dict(read=lambda name:device if wrong!='device' else '999:999',observe=lambda:{},validate=lambda *unused:None)
    with patch.object(M.os,'open',side_effect=fixture_open),patch.object(M.os,'fstat',side_effect=root_owner), \
         patch.object(M.os,'posix_fadvise') as advise:
     if wrong:
      with self.assertRaises((ValueError,OSError)):M.backing_advice(guard,{})
      advise.assert_not_called()
     else:
      M.backing_advice(guard,{})
      self.assertEqual(advise.call_count,1)
      self.assertEqual(advise.call_args.args[1:],(0,4*1024**3,os.POSIX_FADV_DONTNEED))
     self.assertTrue(all(not flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC) for _,flags in calls))
     self.assertTrue(all(flags&os.O_NOFOLLOW for _,flags in calls))
 def exercise(self,parent,*,failure=None):
  g=M.load(GUARD,'fixture_guard');state=F.snapshot();time=[0];base_load=M.load;fstat=os.fstat
  g['observe']=lambda:copy.deepcopy(state);g['opened_parent']=lambda scope:os.dup(parent)
  original=g['open_namespace']
  def namespace(fd,expected=None):
   def root_owner(fd):
    s=list(fstat(fd));s[4]=s[5]=0;return os.stat_result(s)
   with patch.object(os,'fstat',side_effect=root_owner):return original(fd,expected)
  g['open_namespace']=namespace
  def pause(unused):
   time[0]+=10
   if failure=='power':state['power']['temp']='400'
   if failure=='scope':state['blocks']['fixture0']='0'
   if failure=='boot':state['boot']='different'
  def namespaces(raw,name):return g if name=='qualified-durability-target' else base_load(raw,name)
  with patch.object(M,'load',side_effect=namespaces),patch.object(M,'backing_advice') as backing:
   result=M.run(F.request('prepare'),OPS,GUARD,clock=lambda:time[0],pause=pause)
   self.assertEqual(backing.call_count,result['readbacks'])
   return result
 def test_real_write_fsync_uncached_readback_and_cleanup(self):
  with tempfile.TemporaryDirectory() as tmp:
   fd=os.open(tmp,os.O_RDONLY|os.O_DIRECTORY)
   try:
    r=self.exercise(fd)
    self.assertEqual(r['status'],'PASS');self.assertFalse(r['s07_qualified'])
    self.assertTrue(r['cleanup']);self.assertEqual(r['size'],64*1024**2)
    self.assertEqual(r['readbacks'],4);self.assertEqual(r['seconds'],30)
    self.assertEqual(os.listdir(fd),[])
   finally:os.close(fd)
 def test_power_scope_or_boot_failure_preserves_owned_file(self):
  for failure in ('power','scope','boot'):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
    fd=os.open(tmp,os.O_RDONLY|os.O_DIRECTORY)
    try:
     with self.assertRaises(ValueError):self.exercise(fd,failure=failure)
     file=Path(tmp)/'rog5-release-acceptance'/('s04-'+'a'*32)/'scratch.bin'
     self.assertEqual(file.stat().st_size,64*1024**2)
    finally:os.close(fd)
 def test_existing_namespace_is_not_reused_or_removed(self):
  with tempfile.TemporaryDirectory() as tmp:
   (Path(tmp)/'rog5-release-acceptance').mkdir();fd=os.open(tmp,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with self.assertRaises(FileExistsError):self.exercise(fd)
    self.assertTrue((Path(tmp)/'rog5-release-acceptance').is_dir())
   finally:os.close(fd)
 def test_invalid_request_or_missing_advice_cannot_write(self):
  with patch.object(M.os,'mkdir') as mkdir:
   for change in ({'phase':'cleanup'},{'size':True},{'nonce':'../bad'}):
    request=F.request('prepare');request.update(change)
    with self.assertRaises(ValueError):M.run(request,OPS,GUARD)
   mkdir.assert_not_called()
 def test_deadline_is_always_disarmed(self):
  with patch.object(M,'run',side_effect=ValueError('stop')),patch.object(M.signal,'signal'),patch.object(M.signal,'setitimer') as timer:
   with self.assertRaises(ValueError):M.main({},OPS,GUARD)
   self.assertEqual(timer.call_args.args,(M.signal.ITIMER_REAL,0))
if __name__=='__main__':unittest.main()
