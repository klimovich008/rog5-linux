"""One-shot headless boot policy; no daemon, files, charging or display controls.

The authenticated initramfs and current-boot P2 service own device/storage trust.
Keep lowered maxima on success; restore partial application on failure. Normal
shutdown retains the conservative limits until the kernel exits.
"""
import importlib.util,json,os,re,signal,stat
from pathlib import Path

CORE=Path('/run/rog5-native-wifi/cpu-frequency-cap.py')
def require(ok,why):
 if not ok:raise ValueError(why)
def record(path):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  s=os.fstat(fd)
  require(stat.S_ISREG(s.st_mode) and s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o444 and s.st_nlink==1,'P2 record metadata')
  raw=os.read(fd,4097);require(0<len(raw)<=4096,'P2 record bound')
 finally:os.close(fd)
 lines=raw.decode('ascii').splitlines();value={}
 for line in lines:
  k,sep,v=line.partition('=');require(sep and k not in value,'P2 record fields');value[k]=v
 return value
def guard():
 def read(path):return Path(path).read_text().strip()
 require(os.geteuid()==0,'root required')
 require(Path('/proc/device-tree/compatible').read_bytes()==b'asus,rog-phone5\0qcom,sm8350\0','wrong device tree')
 boot=read('/proc/sys/kernel/random/boot_id');require(re.fullmatch('[0-9a-f-]{36}',boot),'boot identity')
 p2=record('/run/rog5-p2-ready')
 require(p2.get('status')=='PASS' and p2.get('attested_boot_id')==boot and p2.get('kernel')==os.uname().release,'current P2 required')
 require(p2.get('physical_blocks')=='117' and p2.get('root_mount')=='native-root-ro-noload','native root attestation')
 root='/sys/class/power_supply/qcom-battmgr-bat/'
 require(read(root+'health')=='Good' and 0<=int(read(root+'temp'))<400
  and 7500000<=int(read(root+'voltage_now'))<=8800000,'unsafe battery')
 require(read('/sys/class/power_supply/qcom-battmgr-usb/online')=='1','input power absent')
 zones=list(Path('/sys/class/thermal').glob('thermal_zone*/temp'))
 require(zones and all(int(p.read_text())<60000 for p in zones),'unsafe or unavailable thermal state')
 blocks={p.parent.name:p.read_text().strip() for p in Path('/sys/class/block').glob('sd*/ro')}
 require(len(blocks)==117 and all(v in ('0','1') for v in blocks.values())
  and {k for k,v in blocks.items() if v=='0'}<={'sda','sda23'},'storage write scope')
 return boot
def apply(core,backend,check):
 require(signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'existing timer')
 def interrupted(signum,unused):raise InterruptedError('CPU boot policy interrupted: '+str(signum))
 signals=(signal.SIGALRM,signal.SIGTERM,signal.SIGHUP,signal.SIGINT)
 previous={n:signal.getsignal(n) for n in signals}
 try:
  for n in signals:signal.signal(n,interrupted)
  signal.setitimer(signal.ITIMER_REAL,10)
  return core.run(backend,check,lambda:None,retain_on_success=True)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  for n,handler in previous.items():signal.signal(n,handler)
def main():
 guard()
 s=CORE.lstat();require(stat.S_ISREG(s.st_mode) and s.st_uid==s.st_gid==0 and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o644,'core metadata')
 spec=importlib.util.spec_from_file_location('sealed_cpu_cap',CORE);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
 b=core.Sysfs()
 try:result=apply(core,b,guard)
 finally:b.close()
 print(json.dumps(dict(status='APPLIED',boot_id=guard(),**result)))
if __name__=='__main__':main()
