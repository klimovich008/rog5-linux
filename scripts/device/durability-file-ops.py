#!/usr/bin/env python3
"""Bounded S04 file operations; caller must verify the exact target filesystem.

No device lookup, mount, reboot or arbitrary path CLI. All paths are relative
 to a caller-verified directory FD. Partial/failed work is preserved.
"""
import hashlib,os,re,stat,time
SIZE=64*1024*1024
BLOCK=65536
def require(ok,reason):
 if not ok:raise ValueError(reason)
def directory(fd):
 s=os.fstat(fd)
 require(stat.S_ISDIR(s.st_mode) and s.st_uid==os.geteuid() and not s.st_mode & 0o022,'unsafe directory')
 return s
def child(parent,name):
 require(re.fullmatch('s04-[0-9a-f]{32}',name),'invalid owned directory name')
 fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
 try:
  directory(fd);require(os.fstat(fd).st_dev==os.fstat(parent).st_dev,'different filesystem')
 except BaseException:os.close(fd);raise
 return fd
def chunks(nonce,size):
 require(re.fullmatch('[0-9a-f]{64}',nonce) and type(size) is int and 0<size<=SIZE,'invalid bounded payload')
 for offset in range(0,size,BLOCK):
  yield hashlib.shake_256(bytes.fromhex(nonce)+offset.to_bytes(8,'big')).digest(min(BLOCK,size-offset))
def signature(s):
 return dict(inode=s.st_ino,size=s.st_size,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink)
def prepare(parent,name,nonce,size=SIZE,guard=lambda:None):
 base=directory(parent);payload=chunks(nonce,size);first=next(payload)
 # Validate before any mutation. Never reuse an existing name, even empty.
 require(re.fullmatch('s04-[0-9a-f]{32}',name),'invalid owned directory name')
 guard()
 os.mkdir(name,0o700,dir_fd=parent);os.fsync(parent)
 fd=child(parent,name)
 try:
  file=os.open('scratch.bin',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
  digest=hashlib.sha256();start=time.monotonic()
  try:
   block=first
   while True:
    digest.update(block);pending=memoryview(block)
    while pending:
     require(time.monotonic()-start<30,'bounded write deadline')
     guard()
     count=os.write(file,pending);require(count>0,'short write');pending=pending[count:]
    block=next(payload,None)
    if block is None:break
   guard();os.fsync(file);os.fchmod(file,0o400);os.fsync(file)
   observed=signature(os.fstat(file))
  finally:os.close(file)
  os.fsync(fd);os.fsync(parent)
  return dict(name=name,nonce=nonce,sha256=digest.hexdigest(),file=observed,
   directory_inode=os.fstat(fd).st_ino,parent_inode=base.st_ino)
 finally:os.close(fd)
def verify(parent,record,guard=lambda:None):
 base=directory(parent);require(base.st_ino==record['parent_inode'],'wrong parent')
 fd=child(parent,record['name'])
 try:
  require(os.fstat(fd).st_ino==record['directory_inode'] and os.listdir(fd)==['scratch.bin'],'directory replaced or unexpected entry')
  file=os.open('scratch.bin',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
  try:
   before=os.fstat(file);s=signature(before)
   require(stat.S_ISREG(before.st_mode) and before.st_dev==os.fstat(fd).st_dev
    and s==record['file'] and s['mode']==0o400
    and s['nlink']==1 and 0<s['size']<=SIZE,'file metadata mismatch')
   actual=hashlib.sha256();expected=hashlib.sha256();start=time.monotonic()
   for wanted in chunks(record['nonce'],s['size']):
    guard()
    require(time.monotonic()-start<30,'bounded read deadline')
    data=b''
    while len(data)<len(wanted):
     part=os.read(file,len(wanted)-len(data));require(part,'truncated payload');data+=part
    require(data==wanted,'payload changed');actual.update(data);expected.update(wanted)
   require(not os.read(file,1) and actual.hexdigest()==expected.hexdigest()==record['sha256'],'hash/size changed')
   current=os.stat('scratch.bin',dir_fd=fd,follow_symlinks=False)
   require(signature(os.fstat(file))==s==signature(current) and
    (before.st_mtime_ns,before.st_ctime_ns)==(current.st_mtime_ns,current.st_ctime_ns),'file changed during read')
   return actual.hexdigest()
  finally:os.close(file)
 finally:os.close(fd)

def cleanup(parent,record,guard=lambda:None):
 # Never recursively delete, and never clean up a failed/partial write.
 verify(parent,record,guard)
 fd=child(parent,record['name'])
 try:
  require(os.fstat(fd).st_ino==record['directory_inode'] and os.listdir(fd)==['scratch.bin'],'cleanup directory changed')
  current=os.stat('scratch.bin',dir_fd=fd,follow_symlinks=False)
  require(signature(current)==record['file'] and stat.S_ISREG(current.st_mode),'cleanup file changed')
  guard()
  os.unlink('scratch.bin',dir_fd=fd);os.fsync(fd)
  current=os.stat(record['name'],dir_fd=parent,follow_symlinks=False)
  require(current.st_ino==record['directory_inode'] and stat.S_ISDIR(current.st_mode),'cleanup pathname changed')
  os.rmdir(record['name'],dir_fd=parent);os.fsync(parent)
 finally:os.close(fd)

