"""Real scratch I/O with fixture identity; no phone, block writes or services."""
import copy,importlib.util,os,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('soak_window',HERE/'soak-file-window.py');F=load('soak_fixture',HERE/'test-durability-target.py')
OPS=(HERE/'durability-file-ops.py').read_text();GUARD=(HERE/'durability-target.py').read_text()
class Tests(unittest.TestCase):
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
  with patch.object(M,'load',side_effect=namespaces):
   return M.run(F.request('prepare'),OPS,GUARD,clock=lambda:time[0],pause=pause)
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
