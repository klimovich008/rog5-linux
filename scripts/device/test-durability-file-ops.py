#!/usr/bin/env python3
"""Host filesystem API fixtures only; not reboot or UFS durability evidence."""
import copy,importlib.util,os,tempfile,unittest
from pathlib import Path
from unittest import mock
s=importlib.util.spec_from_file_location('scratch',Path(__file__).with_name('durability-file-ops.py'))
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY);self.name='s04-'+'a'*32
 def tearDown(self):os.close(self.fd);self.tmp.cleanup()
 def prepare(self):return M.prepare(self.fd,self.name,'b'*64,1024*1024)
 def test_exact_payload_and_metadata(self):
  record=self.prepare();self.assertEqual(M.verify(self.fd,record),record['sha256'])
  self.assertEqual(record['file']['mode'],0o400);self.assertEqual(record['file']['size'],1024*1024)
 def test_full_authorized_size_on_disposable_host_filesystem(self):
  record=M.prepare(self.fd,self.name,'b'*64,M.SIZE)
  self.assertEqual(record['file']['size'],64*1024*1024)
  self.assertEqual(M.verify(self.fd,record),record['sha256'])
 def test_existing_directory_never_reused(self):
  (self.root/self.name).mkdir()
  with self.assertRaises(FileExistsError):self.prepare()
  self.assertEqual(list((self.root/self.name).iterdir()),[])
 def test_invalid_bounds_before_mutation(self):
  for size in (0,True,M.SIZE+1):
   with self.subTest(size=size),self.assertRaises(ValueError):M.prepare(self.fd,self.name,'b'*64,size)
  self.assertEqual(list(self.root.iterdir()),[])
 def test_parent_and_child_symlink_refused(self):
  (self.root/self.name).symlink_to(self.root,target_is_directory=True)
  with self.assertRaises(OSError):M.child(self.fd,self.name)
 def test_altered_content_and_hardlink_refused(self):
  record=self.prepare();p=self.root/self.name/'scratch.bin';p.chmod(0o600)
  p.write_bytes(b'x'*record['file']['size']);p.chmod(0o400)
  with self.assertRaises(ValueError):M.verify(self.fd,record)
  os.link(p,self.root/'extra')
  with self.assertRaises(ValueError):M.verify(self.fd,record)
 def test_mismatched_record_cannot_access_other_directory(self):
  record=self.prepare();record['name']='../other'
  with self.assertRaises(ValueError):M.verify(self.fd,record)
 def test_wrong_inode_and_extra_entry_refused(self):
  record=self.prepare();changed=copy.deepcopy(record);changed['directory_inode']+=1
  with self.assertRaises(ValueError):M.verify(self.fd,changed)
  (self.root/self.name/'extra').touch()
  with self.assertRaises(ValueError):M.verify(self.fd,record)
 def test_short_writes_are_completed(self):
  write=os.write
  with mock.patch.object(M.os,'write',side_effect=lambda fd,data:write(fd,data[:1024])):
   record=self.prepare()
  self.assertEqual(M.verify(self.fd,record),record['sha256'])
 def test_cleanup_only_exact_owned_complete_file(self):
  record=self.prepare();(self.root/'unrelated').write_text('keep')
  M.cleanup(self.fd,record)
  self.assertFalse((self.root/self.name).exists())
  self.assertEqual((self.root/'unrelated').read_text(),'keep')
 def test_cleanup_refuses_altered_file_without_deleting(self):
  record=self.prepare();record['sha256']='0'*64
  with self.assertRaises(ValueError):M.cleanup(self.fd,record)
  self.assertTrue((self.root/self.name/'scratch.bin').is_file())
 def test_guard_refusal_before_mutation(self):
  guard=mock.Mock(side_effect=ValueError('unsafe power'))
  with self.assertRaises(ValueError):M.prepare(self.fd,self.name,'b'*64,guard=guard)
  self.assertEqual(list(self.root.iterdir()),[])
 def test_guard_failure_leaves_partial_evidence(self):
  calls=iter([None,ValueError('unsafe')])
  def guard():
   value=next(calls)
   if value:raise value
  with self.assertRaises(ValueError):M.prepare(self.fd,self.name,'b'*64,1024,guard)
  self.assertTrue((self.root/self.name/'scratch.bin').exists())
if __name__=='__main__':unittest.main()
