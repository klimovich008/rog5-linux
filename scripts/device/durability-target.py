#!/usr/bin/env python3
"""S04 target adapter. Fixed service-state namespace; no raw block writes."""
import hashlib,json,os,re,signal,stat,time
from pathlib import Path

NAMESPACE='rog5-release-acceptance'
SIZE=64*1024*1024
def require(ok,reason):
    if not ok:raise ValueError(reason)
def request_valid(request):
    require(request['phase'] in ('probe','prepare','verify','cleanup'),'unknown phase')
    require(re.fullmatch('[0-9a-f]{64}',request['nonce']) and type(request['size']) is int and request['size']==SIZE,'scratch scope')
    require(request['origin_boot_id']==request['identity']['boot_id'] if request['phase'] in ('probe','prepare')
            else request['origin_boot_id']!=request['identity']['boot_id'],'wrong boot phase')
    require(request['scope']['path']=='/persist' and type(request['scope']['dev']) is int
            and type(request['scope']['inode']) is int,'fixed parent scope')
def read(path):return Path(path).read_text().strip()
def observe():
    return dict(boot=read('/proc/sys/kernel/random/boot_id'),kernel=os.uname().release,
        bundles=[x.split('=',1)[1] for x in read('/proc/cmdline').split() if x.startswith('rog5.bundle=')],
        mountinfo=read('/proc/self/mountinfo'),
        blocks={p.parent.name:p.read_text().strip() for p in Path('/sys/class/block').glob('sd*/ro')},
        backing=read('/sys/class/block/loop1/loop/backing_file'),
        power={key:read('/sys/class/power_supply/qcom-battmgr-bat/'+key) for key in ('health','temp','voltage_now')},
        online=read('/sys/class/power_supply/qcom-battmgr-usb/online'),
        thermal={p.parent.name:p.read_text().strip() for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')})
def validate(value,request):
    identity=request['identity']
    require(value['boot']==identity['boot_id'] and value['kernel']==identity['release']
            and value['bundles']==[identity['bundle']],'wrong boot/kernel/bundle')
    require(len(value['blocks'])==117 and set(value['blocks'].values())<={'0','1'}
            and {k for k,v in value['blocks'].items() if v=='0'}=={'sda','sda23'},'unexpected block-write scope')
    require(value['backing']=='/.rog5/userdata-rw/rog5/state/server-state-v1.ext4','wrong service-state image')
    mounts={}
    for line in value['mountinfo'].splitlines():
        fields=line.split();require(fields.count('-')==1,'malformed mount');cut=fields.index('-')
        require(cut>=6 and len(fields)==cut+4 and fields[4] not in mounts,'ambiguous mount')
        mounts[fields[4]]=(fields[cut+1],fields[cut+2],set(fields[5].split(',')),set(fields[cut+3].split(',')))
        if fields[4]=='/persist':
            require(fields[2]==f"{os.major(request['scope']['dev'])}:{os.minor(request['scope']['dev'])}"
                    and fields[3]=='/','wrong service-state mount identity')
    for path,source,mode in (('/persist','/dev/loop1','rw'),('/.rog5/root-ro','/dev/sda24','ro'),
                              ('/.rog5/userdata-rw','/dev/sda23','rw')):
        fs,device,options,super_options=mounts[path]
        require(fs=='ext4' and device==source and mode in options and ({'ro','rw'}-{mode}).isdisjoint(options),'wrong mount '+path)
        if mode=='ro':require('norecovery' in super_options,'lower journal replay')
    p=value['power']
    require(p['health']=='Good' and 0<=int(p['temp'])<400 and 8400000<=int(p['voltage_now'])<=8800000
            and value['online']=='1','unsafe power')
    require(bool(value['thermal']) and all(int(v)<60000 for v in value['thermal'].values()),'unsafe or absent thermal')
def opened_parent(scope):
    fd=os.open('/persist',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        require(stat.S_ISDIR(s.st_mode) and s.st_uid==0 and s.st_gid==0 and not s.st_mode&0o022
                and s.st_dev==scope['dev'] and s.st_ino==scope['inode'],'wrong authorized parent')
        return fd
    except BaseException:os.close(fd);raise
def open_namespace(parent,expected=None):
    fd=os.open(NAMESPACE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    try:
        s=os.fstat(fd)
        require(s.st_uid==0 and s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o700
                and s.st_dev==os.fstat(parent).st_dev and (expected is None or s.st_ino==expected),'namespace mismatch')
        return fd
    except BaseException:os.close(fd);raise
def _run(request,ops_source):
    start=time.monotonic()
    ops={};exec(compile(ops_source,'sealed-durability-file-ops','exec'),ops)
    state=observe();validate(state,request);before=state;next_check=0
    def guard(force=False):
        nonlocal next_check,state
        if force or time.monotonic()>=next_check:
            state=observe();validate(state,request);next_check=time.monotonic()+.5
    parent=opened_parent(request['scope'])
    try:
        if request['phase']=='probe':
            try:os.stat(NAMESPACE,dir_fd=parent,follow_symlinks=False)
            except FileNotFoundError:pass
            else:raise ValueError('test namespace already exists')
            result={}
        elif request['phase']=='prepare':
            v=os.fstatvfs(parent)
            require(v.f_bavail*v.f_frsize>=256*1024**2 and v.f_favail>=32,'scratch headroom')
            guard(True);os.mkdir(NAMESPACE,0o700,dir_fd=parent);os.fsync(parent)
            fd=open_namespace(parent)
            try:
                result=ops['prepare'](fd,'s04-'+request['nonce'][:32],request['nonce'],SIZE,guard)
                require(ops['verify'](fd,result,guard)==result['sha256'],'initial readback')
                result=dict(file=result,namespace_inode=os.fstat(fd).st_ino)
            finally:os.close(fd)
        else:
            result=request['prepared'];file=result['file']
            require(file['nonce']==request['nonce'] and file['name']=='s04-'+request['nonce'][:32]
                    and file['file']['size']==SIZE,'prepared record scope')
            fd=open_namespace(parent,result['namespace_inode'])
            try:
                require(ops['verify'](fd,file,guard)==file['sha256'],'post-reboot readback')
                if request['phase']=='cleanup':
                    guard(True);ops['cleanup'](fd,file,guard)
                    require(os.listdir(fd)==[],'unexpected namespace content')
                    current=os.stat(NAMESPACE,dir_fd=parent,follow_symlinks=False)
                    require(current.st_ino==result['namespace_inode'] and stat.S_ISDIR(current.st_mode),'namespace changed')
                    os.rmdir(NAMESPACE,dir_fd=parent);os.fsync(parent)
            finally:os.close(fd)
        guard(True)
        return dict(status='PASS',phase=request['phase'],identity=request['identity'],
            origin_boot_id=request['origin_boot_id'],nonce=request['nonce'],size=SIZE,prepared=result,
            power_before=before['power'],power_after=state['power'],thermal_after=state['thermal'],
            seconds=time.monotonic()-start,ops_sha256=hashlib.sha256(ops_source.encode()).hexdigest())
    finally:os.close(parent)
def main(request,ops_source):
    request_valid(request)
    def alarm(*unused):raise TimeoutError('target file-operation deadline')
    previous=signal.signal(signal.SIGALRM,alarm)
    signal.setitimer(signal.ITIMER_REAL,60)
    try:return _run(request,ops_source)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)
if __name__=='__main__':print(json.dumps(main(REQUEST,OPS_SOURCE)))
