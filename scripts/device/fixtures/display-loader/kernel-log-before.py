"""Bounded authenticated SSH kernel log; no module, reboot or network setup."""
import base64,hashlib,importlib.util,json,os,re,select,signal,stat,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
LIVE=HERE.parent/'oled-startup-live-driver-r1'
SOURCE_BOOT='946acb59-744e-4bbc-b291-ac6b2e05f3fe'
TARGET=dict(release='7.1.4-g136f75ae869a',bundle='gpu-136f7-a9b1bc89566205b6')
MAX_OUTPUT=4*1024*1024
REMOTE=r'''
import base64,json,os,re,select,time
from pathlib import Path
def identity():
 words=Path('/proc/cmdline').read_text().split();bundles=[w.split('=',1)[1] for w in words if w.startswith('rog5.bundle=')]
 if len(bundles)!=1:raise ValueError('bundle identity')
 return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),release=os.uname().release,bundle=bundles[0])
def guard():
 if identity()!=EXPECTED:raise ValueError('target identity changed')
seq=records=0;start=time.monotonic()
def emit(event,**fields):
 global seq
 data=(json.dumps(dict(event=event,sequence=seq,identity=EXPECTED,elapsed=time.monotonic()-start,**fields))+'\n').encode()
 if len(data)>65536:raise ValueError('frame bound')
 os.write(1,data);seq+=1
guard();fd=os.open('/dev/kmsg',os.O_RDONLY|os.O_NONBLOCK|os.O_CLOEXEC)
try:
 os.lseek(fd,0,os.SEEK_END);emit('ready',read_only=True);next_beat=start+1
 while time.monotonic()<start+DURATION:
  ready,_,_=select.select([fd],[],[],min(.2,max(0,start+DURATION-time.monotonic())))
  if ready:
   data=os.read(fd,16384)
   if not data:raise ValueError('kernel EOF')
   records+=1
   if records>128:raise ValueError('kernel record limit')
   emit('kernel',data=base64.b64encode(data).decode())
  if time.monotonic()>=next_beat:
   guard();emit('heartbeat');next_beat=time.monotonic()+1
 guard();emit('terminal',status='PASS',records=records,read_only=True)
finally:os.close(fd)
'''
def need(value,message):
 if not value:raise ValueError(message)
def save(path,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def command():
 path=LIVE/'ssh-worker.py'
 need(hashlib.sha256(path.read_bytes()).hexdigest()=='250647044223f7aa91ef174487e2c7318cf3c435b62f3154d0f4568f04afbefb','SSH worker changed')
 s=importlib.util.spec_from_file_location('module_log_ssh',path);W=importlib.util.module_from_spec(s);s.loader.exec_module(W)
 deployed=W.load_deployed();source=deployed.CAPTURE.ACCEPTANCE.source_identity()
 need(source==dict(revision='f02083f40d999bf095670b4c1a937058c7b035f0',worktree_digest='642669b91ba7db4188e039d92d420b25cd666f1b8f7ae4e76dcd35bcb7409e71',clean=True),'logger source identity')
 W.credentials();deployed.host_gate(dict(serial=W.SERIAL))
 return ['/usr/bin/prlimit','--core=0:0',f'--fsize={MAX_OUTPUT}:{MAX_OUTPUT}','--',*deployed.ssh_command(W.KEY,W.HOSTS),'python3 -I -B -']
class KernelLog:
 def __init__(self,output,boot,duration=120):
  need(type(boot)is str and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot) and boot!=SOURCE_BOOT,'new GPU logger boot required')
  self.identity=dict(TARGET,boot_id=boot)
  need(type(duration)is int and 1<=duration<=300,'logger duration')
  need(os.getuid()==os.geteuid()==1000,'logger owner')
  self.output=Path(output);need(self.output.is_absolute() and self.output.resolve()==self.output,'logger path')
  self.duration=duration;self.process=None;self.pidfd=None;self.files={};self.offset=0;self.buffer=b'';self.sequence=0;self.ready=None;self.terminal=None;self.records=0;self.closed=False;self.started=None;self.last_event=None
 def start(self):
  argv=command();self.output.mkdir(mode=0o700)
  st=self.output.stat();need(st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o700,'logger output metadata')
  save(self.output/'entered.json',dict(identity=self.identity,duration=self.duration,read_only=True,argv=argv,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
  try:
   for name in ('stdout','stderr'):
    fd=os.open(self.output/name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600);self.files[name]=os.fdopen(fd,'w+b',buffering=0)
   self.started=time.monotonic();self.process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=self.files['stdout'],stderr=self.files['stderr'],start_new_session=True,bufsize=0)
   self.pidfd=os.pidfd_open(self.process.pid,0)
   script=('EXPECTED='+repr(self.identity)+'\nDURATION='+str(self.duration)+'\n'+REMOTE).encode();need(len(script)<=4096,'logger input bound')
   need(self.process.stdin.write(script)==len(script),'logger input write');self.process.stdin.close()
   while time.monotonic()<self.started+8:
    self.check()
    if self.ready is not None:return self.ready
    need(self.process.poll() is None,'logger exited before ready');time.sleep(.05)
   raise ValueError('logger readiness deadline')
  except Exception:self.close(cancel=True);raise
 def check(self):
  need(not self.closed,'logger closed')
  for name,f in self.files.items():
   st=os.fstat(f.fileno());named=(self.output/name).lstat()
   need((st.st_dev,st.st_ino)==(named.st_dev,named.st_ino) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and st.st_size<=MAX_OUTPUT,'logger file changed/bound')
  need(os.fstat(self.files['stderr'].fileno()).st_size==0,'logger stderr')
  while raw:=os.pread(self.files['stdout'].fileno(),65536,self.offset):
   self.offset+=len(raw);self.buffer+=raw
   while b'\n' in self.buffer:
    line,self.buffer=self.buffer.split(b'\n',1);need(len(line)<=65536,'logger line bound');value=json.loads(line)
    need(self.terminal is None and value.get('identity')==self.identity and type(value.get('sequence'))is int and value['sequence']==self.sequence,'logger identity/order')
    self.sequence+=1;self.last_event=time.monotonic();event=value.get('event')
    if event=='ready':
     need(self.ready is None and self.sequence==1 and value.get('read_only')is True,'logger readiness');self.ready=value
    else:
     need(self.ready is not None,'logger event before ready')
     if event=='kernel':
      need(0<len(base64.b64decode(value['data'],validate=True))<=16384,'kernel record bound');self.records+=1;need(self.records<=128,'kernel record count')
     elif event=='heartbeat':pass
     elif event=='terminal':
      need(value.get('status')=='PASS' and type(value.get('records'))is int and value['records']==self.records and value.get('read_only')is True and type(value.get('elapsed'))in(int,float) and self.duration<=value['elapsed']<=self.duration+5,'logger terminal');self.terminal=value
     else:raise ValueError('logger event')
   need(len(self.buffer)<=65536,'logger incomplete frame bound')
  return self.ready
 def live(self,remaining=0):
  self.check()
  need(self.ready is not None and self.terminal is None and self.process.poll() is None
       and self.last_event is not None and time.monotonic()-self.last_event<3
       and time.monotonic()+remaining<=self.started+self.duration,'logger is not live')
  return True
 def close(self,cancel=False):
  if self.closed:return
  error=None;forced=False
  try:
   if self.process is not None:
    if not cancel:
     while self.process.poll() is None and time.monotonic()<self.started+self.duration+12:self.check();time.sleep(.1)
    if self.process.poll() is None:
     forced=True
     if self.pidfd is not None:signal.pidfd_send_signal(self.pidfd,signal.SIGTERM)
     else:self.process.terminate()
     try:self.process.wait(timeout=2)
     except subprocess.TimeoutExpired:
      if self.pidfd is not None:signal.pidfd_send_signal(self.pidfd,signal.SIGKILL)
      else:self.process.kill()
      self.process.wait(timeout=2)
    self.check();need(not cancel and not forced and self.process.returncode==0 and self.terminal is not None and not self.buffer,'logger incomplete closure')
  except Exception as exc:error=str(exc)
  finally:
   if self.process is not None and self.process.poll() is None:
    forced=True
    if self.pidfd is not None:signal.pidfd_send_signal(self.pidfd,signal.SIGKILL)
    else:self.process.kill()
    self.process.wait(timeout=2)
   if self.process is not None and self.process.stdin is not None:self.process.stdin.close()
   if self.pidfd is not None:os.close(self.pidfd)
   for f in self.files.values():f.flush();os.fsync(f.fileno());f.close()
   self.closed=True
  result=dict(status='PASS' if error is None and self.terminal is not None else 'FAIL',error=error,forced=forced,child_reaped=self.process is None or self.process.poll() is not None,records=self.records,identity=self.identity,duration=self.duration,read_only=True,module_actions=0)
  save(self.output/'result.json',result);return result
if __name__=='__main__':raise SystemExit('Import-only; read-only observation, not module admission')
