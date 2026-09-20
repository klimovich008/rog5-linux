"""Fresh boot-bound health for the successor, including after full capture.

Target-only GPU health. Expected runtime includes all three sealed A660 firmware
files. No reboot, DRM open, unit change or state write.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shlex
import sys

HERE=Path(__file__).resolve().parent
STATE=HERE.parent
REPO=STATE/'oled-startup-controller-worktree-r1'
INPUTS=HERE/'health-inputs.json'
INPUT_SHA='02e007b553ba4a5e3d5bf5d1545ea3a5ee62860cc09ffb748135e7bc9d8b3425'
RECEIPT_SHA='94aa13ff7ec74d5ece82f94c1b627601d7b7e23e85898cfc25dfc6e9fb311f2b'
FINGERPRINT='SHA256:'+'f'*43
STARTUP_SECONDS=300
MARKERS={'descriptor':'/run/rog5-native-wifi/trial-descriptor','healthy':'/run/rog5-native-wifi/healthy.record',
         'ssh':'/run/rog5-persistent-ssh-identity.record','ready':'/run/rog5-p2-ready',
         'selection':'/.rog5/userdata-rw/rog5/boot/wifi-trial-state'}
PROPERTIES=('ActiveState','SubState','Result','ExecMainStatus','ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic')


def need(ok,why):
    if not ok:raise ValueError(why)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def inputs():
    need(INPUTS.resolve()==INPUTS and INPUTS.stat().st_size<=16384,'health inputs path/bound')
    raw=INPUTS.read_bytes();need(sha(raw)==INPUT_SHA,'health input seal changed');value=json.loads(raw)
    for name,digest in value['producers'].items():
        path=REPO/name
        need(path.resolve()==path and path.stat().st_size<=131072 and sha(path.read_bytes())==digest,'health producer changed')
    return value


SEAL=inputs()
sys.path.insert(0,str(REPO/'scripts/host'))
try:
    ROOT=load('successor_health_root',REPO/'scripts/host/check-standalone-root.py')
    OBS=load('successor_health_readers',REPO/'scripts/host/isolated-recovery-observation.py')
finally:sys.path.pop(0)
need(sha((STATE/'gpu-capture-r1/capture-common.py').read_bytes())=='cd51574835b3c8e397382d577aad76d168ffa280a922dda0f81ac844d6824f14','action common changed')
A=load('successor_health_action_common',STATE/'gpu-capture-r1/capture-common.py')
D=ROOT.D


def configuration(role,boot):
    need(role == 'target','target-only health role; V11 uses the sealed-shell source observer')
    A.C.boot_id(boot)
    need(boot not in (A.SOURCE_BOOT,SEAL['source_boot_id']),'source boot cannot qualify successor')
    identity=dict(SEAL['target'],boot_id=boot);trial=SEAL['trial_id'];state=SEAL['healthy_state_sha256']
    files={key:{k:v for k,v in row.items() if k!='origin'} for key,row in SEAL['files'].items()}
    return dict(role=role,identity=identity,trial_id=trial,state_sha256=state,files=files)


def physical_guard(cfg):
    # Reuse the qualified physical prefix only. Never include helper execution.
    identity=cfg['identity']
    if cfg['role']=='baseline':
        full=A.G.build('stage',identity['boot_id'],A.SOURCE_BOOT,A.OWNER,RECEIPT_SHA)
    else:
        full=A.G.build('restore-v11',identity['boot_id'],A.SOURCE_BOOT,A.OWNER,RECEIPT_SHA)
        for key,old,new in [('expected_bundle',A.C.FALLBACK['bundle'],identity['bundle']),
                            ('expected_release',A.C.FALLBACK['release'],identity['release'])]:
            before=key+'='+shlex.quote(old)+'\n';after=key+'='+shlex.quote(new)+'\n'
            need(full.count(before)==1,'physical identity substitution boundary');full=full.replace(before,after)
    need(full.count('run_helper() {')==1,'physical guard boundary')
    return full.split('run_helper() {')[0]+"guard\nprintf 'PASS-physical-guard\\n'\n"


SEALED_READER='"""Collector source for exact-size sealed binaries; offline candidate only.\n\nExecuted alongside the retained observation reader (need/signature/imports).\nText markers retain their existing 16 KiB limit and reader.\n"""\n\ndef observed_sealed(row):\n    path = row[\'path\']\n    expected_size = row[\'size\']\n    need(type(expected_size) is int and 0 < expected_size <= 2097152,\n         \'sealed file expected size bound: \' + path)\n    need(Path(path).is_absolute() and \'..\' not in Path(path).parts,\n         \'sealed file absolute path\')\n    directory = os.open(\'/\', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)\n    fd = None\n    try:\n        parts = Path(path).parts[1:]\n        for name in parts[:-1]:\n            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,\n                            dir_fd=directory)\n            os.close(directory)\n            directory = child\n        try:\n            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,\n                         dir_fd=directory)\n        except FileNotFoundError:\n            need(not os.path.lexists(path), \'dangling sealed observation link: \' + path)\n            return dict(status=\'absent\')\n        before = os.fstat(fd)\n        need(stat.S_ISREG(before.st_mode) and before.st_size == expected_size,\n             \'sealed file type/exact size: \' + path)\n        digest = hashlib.sha256()\n        remaining = expected_size\n        while remaining:\n            chunk = os.read(fd, min(65536, remaining))\n            need(bool(chunk), \'sealed file short read: \' + path)\n            digest.update(chunk)\n            remaining -= len(chunk)\n        need(not os.read(fd, 1), \'sealed file grew: \' + path)\n        need(signature(before) == signature(os.fstat(fd)) ==\n             signature(os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)),\n             \'sealed file changed: \' + path)\n        return dict(status=\'present\', uid=before.st_uid, gid=before.st_gid,\n                    mode=stat.S_IMODE(before.st_mode), nlink=before.st_nlink,\n                    dev=before.st_dev, sha256=digest.hexdigest())\n    finally:\n        if fd is not None:\n            os.close(fd)\n        os.close(directory)\n'


COLLECT=r'''
import json,subprocess

def command(argv,data=None):
    result=subprocess.run(argv,input=data,stdin=None if data is not None else subprocess.DEVNULL,
        capture_output=True,timeout=8,env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'})
    if result.returncode or result.stderr or len(result.stdout)>65536:raise ValueError('health command failed/bound')
    return result.stdout

def guard():
    actual=command(['/run/initramfs/lib/ld-musl-aarch64.so.1','/run/initramfs/bin/busybox','sh','-s'],GUARD.encode())
    if actual!=b'PASS-physical-guard\n':raise ValueError('physical health guard failed')

guard()
root_space={'request':CFG['identity']}
exec(ROOT_PROBE,root_space)
space={'request':{'identity':CFG['identity']}}
exec(READERS,space)
identity=space['identity'];observed=space['observed'];observed_sealed=space['observed_sealed']
identity()
value={'identity':identity(),'root':root_space['value'],
       'files':{name:observed(path,True) for name,path in MARKERS.items()},
       'sealed':{name:observed_sealed(row) for name,row in CFG['files'].items()}}
raw=command(['systemctl','show','rog5-wifi-healthy.service',*[part for key in PROPERTIES for part in ('-p',key)]]).decode()
rows=[line.split('=',1) for line in raw.splitlines()]
if any(len(row)!=2 for row in rows) or len({row[0] for row in rows})!=len(rows):raise ValueError('health unit framing')
value['unit']=dict(rows)
value['timers']={name:command(['systemctl','show',name,'-p','ActiveState','--value']).decode()
    for name in ('rog5-wifi-boot-rollback.timer','rog5-wifi-probe-rollback.timer')}
value['services']={name:command(['systemctl','show',name,'-p','ActiveState','--value']).decode()
    for name in ('rog5-wifi-radio.service','rog5-wifi-wpa.service','rog5-wifi-dhcp.service','rog5-tailscaled.service')}
value['marker_fstype']=command(['findmnt','-n','-o','FSTYPE','--target','/run/rog5-p2-ready']).decode()
value['uptime']=space['small']('/proc/uptime',128).split()[0]
guard()
value['boot_after']=identity()
value['physical_guard_passed']=True
print(json.dumps(value,sort_keys=True))
'''


def script(role,boot):
    inputs();A.pinned_sources();cfg=configuration(role,boot)
    need(ROOT.PROBE.count('print(json.dumps(value))')==1,'root probe result boundary')
    root=ROOT.PROBE.replace('print(json.dumps(value))','')
    need(OBS.PROBE.count('actual=dict(identity=identity(),files={},sealed={},units={})')==1,'reader prefix boundary')
    readers=OBS.PROBE.split('actual=dict(identity=identity(),files={},sealed={},units={})')[0]+SEALED_READER
    source='CFG='+repr(cfg)+'\nGUARD='+repr(physical_guard(cfg))+'\nROOT_PROBE='+repr(root)+'\nREADERS='+repr(readers)+'\nMARKERS='+repr(MARKERS)+'\nPROPERTIES='+repr(PROPERTIES)+'\n'+COLLECT
    compile(source,'<successor-health>','exec');return source


def record(item,mode):
    return OBS.record(item,mode)


def latch(value,cfg):
    identity=cfg['identity'];trial=cfg['trial_id'];files=value['files']
    need(record(files['descriptor'],0o444)==dict(format='rog5-persistent-wifi-health-v1',trial_id=trial,
        primary_bundle=identity['bundle'],mode='try-once'),'health descriptor identity')
    need(record(files['healthy'],0o444)==dict(format='rog5-native-wifi-healthy-v1',boot_id=identity['boot_id'],
        trial_id=trial,result='PASS'),'current-boot healthy commit absent')
    ssh=record(files['ssh'],0o444)
    need(set(ssh)=={'format','mode','fingerprint','identity_boot_id'} and ssh['format']=='rog5-persistent-ssh-identity-v1'
         and ssh['mode'] in ('seed','load') and ssh['fingerprint']==FINGERPRINT
         and ssh['identity_boot_id']==identity['boot_id'],'SSH identity latch')
    unit=value['unit']
    need(type(unit) is dict and set(unit)==set(PROPERTIES)
         and tuple(unit[k] for k in PROPERTIES[:4])==('active','exited','success','0'),'healthy unit did not finish')
    times=[]
    for key in PROPERTIES[-2:]:
        need(type(unit[key]) is str and re.fullmatch('[1-9][0-9]{0,15}',unit[key]),'health timestamp framing')
        times.append(int(unit[key])/1000000)
    need(type(value['uptime']) is str and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',value['uptime']),'uptime framing')
    uptime=float(value['uptime'])
    need(math.isfinite(uptime) and 0<times[0]<=times[1]<=STARTUP_SECONDS and times[1]<=uptime,
         'healthy commit late, absent or newer than observation')
    return dict(commit_uptime_seconds=times[1],observed_uptime_seconds=uptime)


def validate(value,role,boot):
    inputs();cfg=configuration(role,boot);identity=cfg['identity']
    need(set(value)=={'identity','root','files','sealed','unit','timers','services','marker_fstype','uptime',
         'boot_after','physical_guard_passed'},'health snapshot schema')
    need(A.exact_json(value['identity'],identity) and A.exact_json(value['boot_after'],identity)
         and value['physical_guard_passed'] is True,'health boot changed or guard absent')
    ROOT.validate(value['root'],identity)
    need(set(value['files'])==set(MARKERS) and set(value['sealed'])==set(cfg['files']),'health file inventory')
    for role_name,row in cfg['files'].items():
        observed=value['sealed'][role_name]
        expected=dict(status='present',**{k:row[k] for k in ('uid','gid','mode','nlink','sha256')})
        need(set(observed)==set(expected)|{'dev'} and type(observed['dev']) is int
             and A.exact_json({k:v for k,v in observed.items() if k!='dev'},expected),'health runtime differs: '+role_name)
    for name,expected_names,expected_value in [('timers',('rog5-wifi-boot-rollback.timer','rog5-wifi-probe-rollback.timer'),'inactive\n'),
        ('services',('rog5-wifi-radio.service','rog5-wifi-wpa.service','rog5-wifi-dhcp.service','rog5-tailscaled.service'),'active\n')]:
        need(A.exact_json(value[name],dict.fromkeys(expected_names,expected_value)),'health service/timer state')
    selection=value['files']['selection'];record(selection,0o600)
    need(sha(selection['text'].encode())==cfg['state_sha256'],'selection not exact current healthy')
    ready=value['files']['ready'];record(ready,0o444)
    actual=dict(boot_before=boot,boot_after=boot,kernel=identity['release'],bundle=identity['bundle'],
        run_fstype=value['marker_fstype'].strip(),marker_metadata='0:0:444:regular file:1',
        ssh_identity_service=value['root']['units']['rog5-persistent-ssh-identity.service'],marker=ready['text'])
    proof=D.validate_readiness(actual,identity,'fastboot-boot-ram-bundle')
    need(proof['marker_boot_bound'] is True,'health readiness not boot-bound')
    stamps=latch(value,cfg)
    return dict(status='PASS',identity=identity,state_sha256=cfg['state_sha256'],current_boot_healthy=True,
                readiness_boot_bound=True,physical_guards_passed=True,role=role,**stamps,release_qualified=False)


if __name__=='__main__':raise SystemExit('Import-only health component; no phone admission or execution')
