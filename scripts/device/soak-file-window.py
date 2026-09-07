#!/usr/bin/env python3
"""One 30-second S07 scratch window using the qualified S04 primitives.

Caller supplies authenticated fixed-scope REQUEST and exact source strings.
No reboot, mount, service changes or retry; failed/partial files stay intact.
"""
import hashlib,json,os,signal,stat,time
WINDOW=30
DEADLINE=50
SIZE=64*1024**2
def require(ok,reason):
 if not ok:raise ValueError(reason)
def load(raw,name):
 result={'__name__':name};exec(compile(raw,name,'exec'),result);return result
def run(request,ops_source,guard_source,*,clock=time.monotonic,pause=time.sleep):
 ops=load(ops_source,'qualified-durability-file-ops')
 guard=load(guard_source,'qualified-durability-target')
 guard['request_valid'](request)
 require(request['phase']=='prepare' and request['size']==SIZE,'fixed scratch preparation')
 require(hasattr(os,'posix_fadvise') and hasattr(os,'POSIX_FADV_DONTNEED'),'cache advice unavailable')
 before=guard['observe']();guard['validate'](before,request);state=before;next_check=0
 def gate(force=False):
  nonlocal state,next_check
  if force or clock()>=next_check:
   state=guard['observe']();guard['validate'](state,request);next_check=clock()+.5
 parent=guard['opened_parent'](request['scope']);started=clock();reads=0
 try:
  free=os.fstatvfs(parent)
  require(free.f_bavail*free.f_frsize>=256*1024**2 and free.f_favail>=32,'scratch headroom')
  gate(True);os.mkdir(guard['NAMESPACE'],0o700,dir_fd=parent);os.fsync(parent)
  fd=guard['open_namespace'](parent);inode=os.fstat(fd).st_ino
  try:
   record=ops['prepare'](fd,'s04-'+request['nonce'][:32],request['nonce'],SIZE,gate)
   while True:
    gate(True)
    child=ops['child'](fd,record['name'])
    try:
     file=os.open('scratch.bin',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=child)
     try:
      st=os.fstat(file)
      require(stat.S_ISREG(st.st_mode) and ops['signature'](st)==record['file'],'cache-advice file changed')
      os.posix_fadvise(file,0,SIZE,os.POSIX_FADV_DONTNEED)
     finally:os.close(file)
    finally:os.close(child)
    require(ops['verify'](fd,record,gate)==record['sha256'],'scratch readback')
    reads+=1
    require(clock()-started<=DEADLINE,'file window deadline')
    if clock()-started>=WINDOW:break
    pause(.5)
   gate(True);ops['cleanup'](fd,record,gate)
   require(os.listdir(fd)==[],'unexpected scratch namespace content')
   current=os.stat(guard['NAMESPACE'],dir_fd=parent,follow_symlinks=False)
   require(current.st_ino==inode and stat.S_ISDIR(current.st_mode),'scratch namespace replaced')
   os.rmdir(guard['NAMESPACE'],dir_fd=parent);os.fsync(parent)
  finally:os.close(fd)
  gate(True)
  return dict(status='PASS',s07_qualified=False,identity=request['identity'],nonce=request['nonce'],
   size=SIZE,readbacks=reads,seconds=clock()-started,file=record,cleanup=True,
   power_before=before['power'],power_after=state['power'],thermal_after=state['thermal'],
   ops_sha256=hashlib.sha256(ops_source.encode()).hexdigest(),guard_sha256=hashlib.sha256(guard_source.encode()).hexdigest())
 finally:os.close(parent)
def main(request,ops_source,guard_source):
 def expired(*unused):raise TimeoutError('bounded scratch worker')
 previous=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,DEADLINE)
 try:return run(request,ops_source,guard_source)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
if __name__=='__main__':print(json.dumps(main(REQUEST,OPS_SOURCE,GUARD_SOURCE)))
