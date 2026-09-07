"""Fixed ROG5 CPU-cap experiment primitive; never installs policy or runs on import.

Caller owns exact boot/device/power gates, a bounded action and SIGTERM cleanup.
Only scaling_max_freq is written. No governor, voltage, charging or thermal-trip
changes. A successful experiment is not release acceptance. Unexpected concurrent
policy changes are reported, not overwritten. SIGKILL cannot run Python cleanup;
the coordinator must independently verify restoration (or ordinary reboot).
"""
import os,re,signal,stat,time

CAPS={'policy0':1209600,'policy4':1555200,'policy7':1555200}
CPUS={'policy0':'0 1 2 3','policy4':'4 5 6','policy7':'7'}
ROOT='/sys/devices/system/cpu/cpufreq'
SETTLE_SECONDS=1.0
def require(ok,why):
 if not ok:raise ValueError(why)
def settled(read,before,after):
 """cpufreq QoS schedules policy->update; a successful store is not readback.

Only the exact pre-write or requested snapshot is valid while waiting. Never
repeat the write to make it converge or accept unrelated concurrent changes.
"""
 deadline=time.monotonic()+SETTLE_SECONDS
 while True:
  current=read()
  require(time.monotonic()<=deadline,'CPU policy update deadline')
  if current==after:return
  require(current==before,'unexpected CPU policy during update')
  time.sleep(min(.02,max(0,deadline-time.monotonic())))
def validate(value):
 require(set(value)==set(CAPS),'unexpected CPU policy set')
 for name,p in value.items():
  require(p['cpus']==CPUS[name] and p['driver']=='qcom-cpufreq-hw' and p['governor']=='schedutil','policy identity')
  require(type(p['minimum']) is int and type(p['maximum']) is int and
   0<p['minimum']<=CAPS[name]<=p['maximum'],'cap must only lower maximum above minimum')
  require(type(p['frequencies']) is list and all(type(v) is int and v>0 for v in p['frequencies'])
   and CAPS[name] in p['frequencies'],'cap absent from hardware frequency table')
def run(backend,guard,action,*,retain_on_success=False):
 """Apply fixed caps; experiments restore, explicit boot setup may retain them.

Retention changes only successful completion, never failed/partial application.
It is kernel state for this boot, not permission to install persistent files.
"""
 require(type(retain_on_success) is bool,'retention must be explicit boolean')
 guard();original=backend.snapshot();validate(original);entered=[];during=None;result=None;retained=False
 try:
  for name,limit in CAPS.items():
   guard();current=backend.snapshot()
   expected={n:dict(p,maximum=CAPS[n] if n in entered else p['maximum']) for n,p in original.items()}
   require(current==expected,'policy changed before apply')
   entered.append(name)  # A failed write may already have reached the kernel.
   backend.set_maximum(name,limit)
   expected[name]['maximum']=limit
   settled(backend.snapshot,current,expected)
  guard();during=backend.snapshot();result=action()
  if retain_on_success:
   guard();require(backend.snapshot()==during,'policy changed before retention')
   retained=True
 finally:
  errors=[]
  for name in ([] if retained else reversed(entered)):
   try:
    current=backend.snapshot()[name];prior=original[name]
    require({k:v for k,v in current.items() if k!='maximum'}=={k:v for k,v in prior.items() if k!='maximum'},'policy identity changed')
    require(current['maximum'] in (CAPS[name],prior['maximum']),'external maximum change')
    # Even an old visible maximum can hide our pending QoS request. Replace
    # that request unconditionally after entry, including failed write returns.
    backend.set_maximum(name,prior['maximum'])
    settled(lambda:backend.snapshot()[name],current,prior)
   except (OSError,ValueError,KeyError,TypeError) as error:errors.append(name+': '+str(error))
  if errors:raise ValueError('restoration incomplete: '+'; '.join(errors))
 after=backend.snapshot();require(after==(during if retained else original),'post-transaction policy changed')
 return dict(before=original,during=during,after=after,action=result,
  restoration='NOT REQUESTED' if retained else 'PASS',policy_retained=retained,release_qualified=False)

def lease(backend,guard,observe,seconds,*,clock=time.monotonic,pause=time.sleep):
 """Bounded main-thread lease. Caller streams observations, never changes scope.

SIGTERM/SIGHUP/SIGINT and the independent alarm unwind through run() restoration.
An expired alarm is failure, not a successful shortened experiment. The caller
must stop load before normal lease expiry and verify restoration independently.
"""
 require(type(seconds) is int and 1<=seconds<=720,'invalid cap lease duration')
 require(signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'existing alarm cannot be replaced')
 def interrupted(signum,unused):raise InterruptedError('CPU cap lease interrupted: '+str(signum))
 signals=(signal.SIGALRM,signal.SIGTERM,signal.SIGHUP,signal.SIGINT)
 previous={signum:signal.getsignal(signum) for signum in signals}
 def action():
  start=clock();deadline=start+seconds;count=0
  while clock()<deadline:
   guard();current=backend.snapshot()
   require({n:p['maximum'] for n,p in current.items()}==CAPS,'cap changed during lease')
   observe(dict(elapsed=clock()-start,policies=current));count+=1
   pause(min(1,max(0,deadline-clock())))
  return dict(seconds=clock()-start,samples=count)
 try:
  for signum in signals:signal.signal(signum,interrupted)
  signal.setitimer(signal.ITIMER_REAL,seconds+15)
  return run(backend,guard,action)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  for signum,handler in previous.items():signal.signal(signum,handler)

class Sysfs:
 """Descriptor-relative fixed policy access; root fd injection is for fixtures."""
 def __init__(self,root_fd=None):
  self.root=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW) if root_fd is None else os.dup(root_fd)
  self.policies={}
  try:
   self.directory(self.root)
   require({n for n in os.listdir(self.root) if n.startswith('policy')}==set(CAPS),'sysfs policy set')
   for name in CAPS:
    fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.root)
    self.policies[name]=fd;self.directory(fd)
  except BaseException:self.close();raise
 @staticmethod
 def directory(fd):
  s=os.fstat(fd);require(stat.S_ISDIR(s.st_mode) and s.st_uid==s.st_gid==0 and not s.st_mode&0o022,'unsafe CPU directory')
 def same(self,name):
  fd=self.policies[name];old=os.fstat(fd);now=os.stat(name,dir_fd=self.root,follow_symlinks=False)
  require(stat.S_ISDIR(now.st_mode) and (old.st_dev,old.st_ino)==(now.st_dev,now.st_ino),'CPU policy pathname changed')
  self.directory(fd);return fd
 def opened(self,name,field,flags):
  parent=self.same(name);stats_fd=None
  if field=='stats/time_in_state':
   stats_fd=os.open('stats',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
   try:self.directory(stats_fd)
   except BaseException:os.close(stats_fd);raise
   parent=stats_fd;field='time_in_state'
  try:fd=os.open(field,flags|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
  finally:
   if stats_fd is not None:os.close(stats_fd)
  try:
   s=os.fstat(fd);require(stat.S_ISREG(s.st_mode) and s.st_uid==s.st_gid==0 and not s.st_mode&0o022,'unsafe CPU attribute')
   return fd
  except BaseException:os.close(fd);raise
 def read(self,name,field):
  fd=self.opened(name,field,os.O_RDONLY)
  try:
   raw=os.read(fd,65537);require(len(raw)<=65536,'CPU attribute read bound');self.same(name)
   return raw.decode('ascii').strip()
  finally:os.close(fd)
 def snapshot(self):
  require({n for n in os.listdir(self.root) if n.startswith('policy')}==set(CAPS),'CPU policy set changed')
  rows={}
  for name in CAPS:
   def integer(field):
    value=self.read(name,field);require(re.fullmatch('[0-9]+',value),'CPU frequency integer');return int(value)
   pairs=[line.split() for line in self.read(name,'stats/time_in_state').splitlines()]
   require(pairs and all(len(p)==2 and all(re.fullmatch('[0-9]+',x) for x in p) for p in pairs),'hardware frequency table')
   rows[name]=dict(cpus=self.read(name,'related_cpus'),driver=self.read(name,'scaling_driver'),
    governor=self.read(name,'scaling_governor'),minimum=integer('scaling_min_freq'),maximum=integer('scaling_max_freq'),
    frequencies=[int(p[0]) for p in pairs])
  return rows
 def set_maximum(self,name,value):
  require(name in CAPS and type(value) is int and 0<value<=3000000,'invalid maximum write')
  fd=self.opened(name,'scaling_max_freq',os.O_WRONLY)
  try:
   raw=(str(value)+'\n').encode('ascii');require(os.write(fd,raw)==len(raw),'short CPU maximum write')
   self.same(name)
  finally:os.close(fd)
 def close(self):
  for fd in self.policies.values():os.close(fd)
  self.policies.clear()
  if self.root is not None:os.close(self.root);self.root=None
