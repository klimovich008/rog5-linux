"""Read-only R01 negative-health component. This is not physical recovery proof.

The sole outer coordinator supplies admitted identities and sealed-file hashes,
retains raw authenticated output, and independently proves autonomous return.
No helper execution, service action, acknowledgment or rollback change occurs.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess

SPEC=importlib.util.spec_from_file_location('negative_deployed',Path(__file__).with_name('check-deployed-server.py'))
D=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(D)
ROOT='/run/rog5-native-wifi/'
# Accepted userdata partition; sysfs geometry uses 512-byte sectors. Linux may
# allocate an extended device minor, independently of partition number 23.
USERDATA_GEOMETRY=dict(partition='23',start='18821440',size='408997568')
USERDATA_PARTUUID='8d82ef11-4d42-60e9-24e8-4d6ebf20491b'
MARKERS={
    'descriptor':ROOT+'trial-descriptor',
    'healthy':ROOT+'healthy.record',
    'radio_refused':ROOT+'radio-refused',
    'pending':'/.rog5/userdata-rw/rog5/boot/wifi-trial-state',
    'ready':'/run/rog5-p2-ready',
    'ssh':'/run/rog5-persistent-ssh-identity.record',
}
SEALED={
    'runtime':(ROOT+'runtime',0o755),
    'healthy':(ROOT+'healthy',0o755),
    'helper':(ROOT+'trial-state',0o755),
    'health_unit':('/run/systemd/system/rog5-wifi-healthy.service',0o644),
    'timer_unit':('/run/systemd/system/rog5-wifi-boot-rollback.timer',0o644),
    'rollback_unit':('/run/systemd/system/rog5-wifi-boot-rollback.service',0o644),
}
UNITS={role:'rog5-wifi-'+name for role,name in (
    ('health','healthy.service'),('timer','boot-rollback.timer'),('rollback','boot-rollback.service'))}
SERVICE_PROPERTIES=('LoadState','ActiveState','SubState','Result','ExecMainStatus',
                    'ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic')
TIMER_PROPERTIES=('LoadState','ActiveState','SubState','Result','Unit')
MESSAGES=('FAIL persistent trial state: running trial identity does not match pending state',
          'FAIL native-wifi-healthy: trial commit')


def need(ok,why):
    if not ok:raise ValueError(why)


def unique(rows):
    result={}
    for key,value in rows:
        need(key not in result,'duplicate observation field')
        result[key]=value
    return result


def decode(raw):
    need(type(raw) is bytes and 0<len(raw)<=262144,'observation output bound')
    return json.loads(raw,object_pairs_hook=unique)


def record(item,mode):
    need(type(item) is dict and item.get('status')=='present','missing observed record')
    need(all(type(item.get(k)) is int for k in ('uid','gid','mode','nlink','dev'))
         and (item['uid'],item['gid'],item['mode'],item['nlink'])==(0,0,mode,1),'record metadata')
    raw=item.get('text')
    need(type(raw) is str and 0<len(raw)<=16384 and raw.endswith('\n') and '\r' not in raw
         and '\0' not in raw,'record framing')
    return unique(line.split('=',1) for line in raw.splitlines())


def command(value):
    need(type(value) is dict and type(value.get('returncode')) is int and value['returncode']==0
         and value.get('stderr')=='','failed observation command')
    need(type(value.get('stdout')) is str and len(value['stdout'])<=131072,'command output bound')
    return value['stdout']



def userdata_device(actual):
    device=actual.get('userdata_device')
    need(type(device) is str,'missing userdata device')
    match=re.fullmatch(r'([1-9][0-9]{0,3}):(0|[1-9][0-9]{0,6})',device)
    need(match is not None,'userdata device framing')
    major,minor=map(int,match.groups())
    need(major<=4095 and minor<=1048575,'userdata device bounds')
    partition=actual.get('userdata_partition')
    need(type(partition) is dict and set(partition)=={*USERDATA_GEOMETRY,'uevent'},
         'userdata partition observation fields')
    need(all(partition[name]==value for name,value in USERDATA_GEOMETRY.items()),
         'userdata geometry differs')
    raw=partition['uevent']
    need(type(raw) is str and len(raw)<=4096,'userdata partition identity bound')
    events=unique(line.split('=',1) for line in raw.splitlines())
    expected=dict(MAJOR=str(major),MINOR=str(minor),DEVNAME='sda23',DEVTYPE='partition',
                  PARTN='23',PARTNAME='userdata',PARTUUID=USERDATA_PARTUUID)
    need(all(events.get(name)==value for name,value in expected.items()),
         'userdata partition identity differs')
    return os.makedev(major,minor)


def environment(actual,identity,trial,installed,sealed,rollback_seconds=900):
    """Validate actual identity, sealed state, power and storage before classifying health."""
    need(type(trial) is str and re.fullmatch('[0-9a-f]{64}',trial),'negative trial identity')
    need(set(installed)=={'trial_id','primary_bundle','primary_manifest_sha256','fallback_bundle',
                         'fallback_manifest_sha256'},'installed trial fields')
    need(trial!=installed['trial_id'] and identity['bundle']!=installed['primary_bundle'],
         'negative trial must differ from accepted primary')
    need(actual['identity']==identity and D.CAPTURE.STAGES.BOOT_ID.fullmatch(identity['boot_id']),
         'wrong negative boot identity')
    need(type(rollback_seconds) is int and rollback_seconds==900,'review different rollback lattice')
    uptime=actual['uptime']
    need(type(uptime) in (int,float) and math.isfinite(uptime) and 0<uptime<rollback_seconds,
         'negative observation outside timer window')
    need(set(actual['files'])==set(MARKERS),'marker inventory')
    files=actual['files']
    descriptor=record(files['descriptor'],0o444)
    need(descriptor==dict(format='rog5-persistent-wifi-health-v1',trial_id=trial,
                         primary_bundle=identity['bundle'],mode='try-once'),'negative descriptor differs')
    for role in ('healthy','radio_refused'):
        need(files[role]=={'status':'absent'},'healthy or radio-refusal branch is not this failure')
    device_number=userdata_device(actual)
    pending=record(files['pending'],0o600)
    need(pending==dict(format='rog5-persistent-wifi-trial-v1',**installed,state='pending')
         and files['pending']['dev']==device_number,'pending installed fallback changed')
    ready=record(files['ready'],0o444)
    need(ready.get('status')=='PASS' and ready.get('attested_boot_id')==identity['boot_id']
         and ready.get('kernel')==identity['release'] and ready.get('ssh')=='strict-key-only',
         'core readiness missing or stale')
    ssh=record(files['ssh'],0o444)
    need(set(ssh)=={'format','mode','fingerprint','identity_boot_id'}
         and ssh['format']=='rog5-persistent-ssh-identity-v1' and ssh['mode'] in ('seed','load')
         and ssh['identity_boot_id']==identity['boot_id']
         and re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',ssh['fingerprint']),'SSH identity latch')
    need(set(sealed)==set(SEALED) and set(actual['sealed'])==set(SEALED),'sealed observation inventory')
    for role,(path,mode) in SEALED.items():
        item=actual['sealed'][role]
        need(type(sealed[role]) is str and re.fullmatch('[0-9a-f]{64}',sealed[role]),'sealed hash pin')
        need(item.get('status')=='present' and item.get('sha256')==sealed[role]
             and all(type(item.get(k)) is int for k in ('uid','gid','mode','nlink'))
             and (item['uid'],item['gid'],item['mode'],item['nlink'])==(0,0,mode,1),
             'deployed rollback/health bytes differ: '+role)
    need(set(actual['units'])==set(UNITS),'unit inventory')
    units={role:unique(line.split('=',1) for line in command(value).splitlines())
           for role,value in actual['units'].items()}
    health=units['health'];timer=units['timer'];rollback=units['rollback']
    need(set(health)==set(SERVICE_PROPERTIES) and set(rollback)==set(SERVICE_PROPERTIES)
         and set(timer)==set(TIMER_PROPERTIES),'unit observation fields')
    need(timer==dict(LoadState='loaded',ActiveState='active',SubState='waiting',Result='success',
                     Unit=UNITS['rollback']),'rollback timer is not armed')
    need(tuple(rollback[k] for k in SERVICE_PROPERTIES)==('loaded','inactive','dead','success','0','0','0'),
         'rollback already executed or failed')
    power=actual['power']
    need(power['health']=='Good' and power['usb_online']=='1'
         and 0<=int(power['temp'])<400 and 8400000<=int(power['voltage_now'])<=8800000,'unsafe power')
    thermal=actual['thermal']
    need(thermal and all(type(value) is int and 0<=value<60000 for value in thermal.values()),'unsafe thermal')
    blocks=actual['blocks']
    need(len(blocks)==117 and set(blocks.values())<={'0','1'}
         and {key for key,value in blocks.items() if value=='0'}=={'sda','sda23'},'storage scope')
    rows=[line.split() for line in actual['mountinfo'].splitlines()]
    mounted=[row for row in rows if len(row)>6 and row[4]=='/.rog5/userdata-rw']
    need(len(mounted)==1,'missing or stacked userdata mount')
    row=mounted[0];need(row.count('-')==1,'mount framing');cut=row.index('-')
    need(row[2:4]==[actual['userdata_device'],'/'] and 'rw' in row[5].split(',') and 'ro' not in row[5].split(',')
         and row[cut+1:cut+3]==['ext4','/dev/sda23'],'userdata mount differs')
    return units


def pending(actual,identity,trial,installed,sealed):
    """Allow a bounded read-only wait only for a still-running healthy unit."""
    health=environment(actual,identity,trial,installed,sealed)['health']
    if health['ActiveState']=='failed':return False
    need((health['LoadState'],health['ActiveState'],health['SubState'],health['Result'],health['ExecMainStatus'])
         in {('loaded','inactive','dead','success','0'),('loaded','activating','start','success','0'),
             ('loaded','activating','start-post','success','0')},'unexpected pending health state')
    for key in SERVICE_PROPERTIES[-2:]:
        value=health[key]
        need(type(value) is str and re.fullmatch('0|[1-9][0-9]{0,15}',value)
             and int(value)<=actual['uptime']*1000000,'pending health timestamp')
    rows=[decode(line.encode()) for line in command(actual['journal']).splitlines()]
    need(len(rows)<=80 and all(row.get('_BOOT_ID')==identity['boot_id'].replace('-','') for row in rows),
         'pending health journal identity/bound')
    return True


def negative(actual,identity,trial,installed,sealed,rollback_seconds=900):
    """Validate the completed specific refusal; never qualify physical return."""
    health=environment(actual,identity,trial,installed,sealed,rollback_seconds)['health']
    uptime=actual['uptime']
    need(tuple(health[k] for k in SERVICE_PROPERTIES[:5])==('loaded','failed','failed','exit-code','1'),
         'health did not fail with the expected exit')
    health_times=[]
    for key in SERVICE_PROPERTIES[-2:]:
        value=health[key]
        need(re.fullmatch('[1-9][0-9]{0,15}',value),'health execution timestamp')
        health_times.append(int(value))
    start,end=health_times
    need(0<start<=end<=uptime*1000000,'health execution outside this observation')
    journal=[decode(line.encode()) for line in command(actual['journal']).splitlines()]
    need(0<len(journal)<=80,'health journal missing or truncated beyond bound')
    matches=[]
    for entry in journal:
        need(type(entry) is dict and entry.get('_BOOT_ID')==identity['boot_id'].replace('-',''),
             'journal belongs to another boot')
        if entry.get('MESSAGE') in MESSAGES:
            need(entry.get('_SYSTEMD_UNIT')==UNITS['health'],'refusal came from another unit')
            stamp=entry.get('__MONOTONIC_TIMESTAMP')
            need(type(stamp) is str and re.fullmatch('[1-9][0-9]{0,15}',stamp),'journal timestamp')
            need(start<=int(stamp)<=end,'refusal outside health execution')
            matches.append((entry['MESSAGE'],int(stamp)))
    need([message for message,_ in matches]==list(MESSAGES)
         and matches[0][1]<=matches[1][1],'specific helper refusal sequence absent or ambiguous')
    return dict(status='COMPONENT_PASS',identity=identity,negative_trial_id=trial,
                health_refusal_uptime_seconds=end/1000000,observed_uptime_seconds=uptime,
                timer_armed=True,autonomous_recovery_proven=False,release_qualified=False)


PROBE=r'''
import hashlib,json,os,stat,subprocess,time
from pathlib import Path
def need(ok,why):
    if not ok:raise ValueError(why)
def small(path,limit=4096):
    with open(path) as f:value=f.read(limit+1)
    need(len(value)<=limit,'telemetry bound');return value.strip()
def identity():
    need(os.getuid()==os.geteuid()==os.getgid()==0,'root required')
    actual=dict(boot_id=small('/proc/sys/kernel/random/boot_id'),release=os.uname().release,
                bundle=[v.split('=',1)[1] for v in small('/proc/cmdline').split() if v.startswith('rog5.bundle=')])
    need(actual.pop('bundle')==[request['identity']['bundle']],'bundle identity')
    actual['bundle']=request['identity']['bundle']
    need(actual==request['identity'],'negative boot identity')
    return actual
def signature(m):return (m.st_dev,m.st_ino,m.st_mode,m.st_uid,m.st_gid,m.st_nlink,m.st_size,m.st_mtime_ns,m.st_ctime_ns)
def observed(path,text):
    directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    fd=None
    try:
        parts=Path(path).parts[1:]
        for name in parts[:-1]:
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
            os.close(directory);directory=child
        try:fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=directory)
        except FileNotFoundError:
            need(not os.path.lexists(path),'dangling observation link')
            return dict(status='absent')
        before=os.fstat(fd);limit=16384 if text else 131072
        need(stat.S_ISREG(before.st_mode) and 0<before.st_size<=limit,'file type/size')
        raw=os.read(fd,limit+1)
        need(len(raw)==before.st_size and not os.read(fd,1),'bounded file read')
        need(signature(before)==signature(os.fstat(fd))==signature(os.stat(parts[-1],dir_fd=directory,follow_symlinks=False)),'file changed')
        result=dict(status='present',uid=before.st_uid,gid=before.st_gid,mode=stat.S_IMODE(before.st_mode),nlink=before.st_nlink,dev=before.st_dev)
        result.update({'text':raw.decode('ascii')} if text else {'sha256':hashlib.sha256(raw).hexdigest()})
        return result
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)
def command(argv):
    value=subprocess.run(argv,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=3,
                         env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C','SYSTEMD_COLORS':'0'})
    need(len(value.stdout)<=131072 and len(value.stderr)<=4096,'command output bound')
    return dict(returncode=value.returncode,stdout=value.stdout,stderr=value.stderr)
actual=dict(identity=identity(),files={},sealed={},units={})
for role,path in request['markers'].items():actual['files'][role]=observed(path,True)
for role,path in request['sealed'].items():actual['sealed'][role]=observed(path,False)
for role,unit in request['units'].items():
    properties=request['timer_properties'] if role=='timer' else request['service_properties']
    actual['units'][role]=command(['systemctl','show',unit,*[flag for key in properties for flag in ('-p',key)]])
actual['journal']=command(['journalctl','-b',request['identity']['boot_id'],'-u',request['units']['health'],'-n','80','--no-pager','-o','json'])
battery='/sys/class/power_supply/qcom-battmgr-bat/'
actual['power']={key:small(battery+key,128) for key in ('health','temp','voltage_now')}
actual['power']['usb_online']=small('/sys/class/power_supply/qcom-battmgr-usb/online',32)
actual['thermal']={p.parent.name:int(small(p,32)) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
actual['blocks']={p.parent.name:small(p,16) for p in Path('/sys/class/block').glob('sd*/ro')}
actual['userdata_device']=small('/sys/class/block/sda23/dev',32)
actual['userdata_partition']={name:small('/sys/class/block/sda23/'+name,4096 if name=='uevent' else 64)
                              for name in ('partition','start','size','uevent')}
actual['mountinfo']=small('/proc/self/mountinfo',65536)
actual['uptime']=float(small('/proc/uptime',128).split()[0])
identity()
print(json.dumps(actual))
'''


def script(identity):
    need(set(identity)=={'boot_id','bundle','release'},'explicit boot identity required')
    need(D.CAPTURE.STAGES.BOOT_ID.fullmatch(identity['boot_id'])
         and re.fullmatch('[a-z0-9][a-z0-9._-]{0,63}',identity['bundle'])
         and re.fullmatch('[A-Za-z0-9_.+-]{1,96}',identity['release']),'invalid boot identity')
    request=dict(identity=identity,markers=MARKERS,sealed={role:path for role,(path,_) in SEALED.items()},
                 units=UNITS,service_properties=SERVICE_PROPERTIES,timer_properties=TIMER_PROPERTIES)
    return 'request='+repr(request)+'\n'+PROBE


def collect(identity,serial,key,known_hosts,retain):
    """One authenticated read; retain receives CompletedProcess or TimeoutExpired."""
    source=script(identity)
    digest=hashlib.sha256(source.encode()).hexdigest()
    gate=dict(identity,serial=serial)
    D.host_gate(gate);D.credential(key,True);D.credential(known_hosts,False)
    try:
        result=subprocess.run([*D.ssh_command(key,known_hosts),'python3 -I -B -c '+shlex.quote(source)],
                              capture_output=True,timeout=20)
    except subprocess.TimeoutExpired as error:
        retain(error,digest)
        raise
    retain(result,digest)  # Preserve the reply before any post-read gate can fail.
    D.host_gate(gate)
    return result,digest
