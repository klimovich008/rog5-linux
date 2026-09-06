#!/usr/bin/env python3
"""Read-only exact userspace check on an already admitted persistent server."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('deployed_capture',Path(__file__).with_name('headless-stage-receiver.py'))
CAPTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(CAPTURE)
# One repository-owned inventory; hashes and sizes are derived, never copied.
FILES={
    'runtime':('initramfs/native-wifi/runtime','/run/rog5-native-wifi/runtime',0o755),
    'healthy':('initramfs/native-wifi-persistent/healthy','/run/rog5-native-wifi/healthy',0o755),
    'trial':('artifacts/persistent-trial-state-v2/rog5-persistent-trial-state','/run/rog5-native-wifi/trial-state',0o755),
    'healthd':('scripts/device/rog5-healthd.py','/usr/local/libexec/rog5-healthd',0o755),
    'healthd_unit':('packaging/arch/rog5-healthd.service','/etc/systemd/system/rog5-healthd.service',0o644),
    'shutdown':('initramfs/persistent-root-shutdown-standalone','/run/initramfs/shutdown',0o755),
}


def expected_files():
    result={}
    for role,(source,target,mode) in FILES.items():
        payload=(REPO/source).read_bytes()
        result[role]=dict(status='present',path=target,size=len(payload),
                          sha256=hashlib.sha256(payload).hexdigest(),mode=mode,uid=0,gid=0,nlink=1)
    return result


def validate_snapshot(actual,identity,expected):
    for key in ('boot_id','bundle','release'):
        if actual.get(key)!=identity[key]: raise ValueError('target identity mismatch: '+key)
    files=actual.get('files')
    if not isinstance(files,dict) or set(files)!=set(expected):
        raise ValueError('deployed file inventory mismatch')
    for role in expected:
        if (not isinstance(files[role],dict) or files[role]!=expected[role]
                or any(type(files[role].get(key)) is not int
                       for key in ('size','mode','uid','gid','nlink'))):
            raise ValueError('deployed userspace mismatch: '+role)


def host_gate(identity):
    if CAPTURE.usb_mode(identity['serial'])!=('target',CAPTURE.INTERFACE):
        raise ValueError('wrong USB identity/topology/driver')
    route=json.loads(CAPTURE.run('ip','-j','route','get','10.77.0.2'))
    if (len(route)!=1 or route[0].get('dev')!=CAPTURE.INTERFACE
            or route[0].get('prefsrc')!='10.77.0.1'):
        raise ValueError('wrong pinned USB route')


def credential(path,private):
    if not path.is_absolute(): raise ValueError('credential path must be absolute')
    metadata=path.lstat()
    modes={0o400,0o600} if private else {0o400,0o600,0o644}
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid!=os.geteuid()
            or metadata.st_nlink!=1 or stat.S_IMODE(metadata.st_mode) not in modes):
        raise ValueError('credential metadata mismatch')


PROBE=r'''
import hashlib,json,os,stat
request=json.loads(INPUT)
def identity():
    with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
    with open('/proc/cmdline') as f: args=f.read().split()
    bundles=[x.split('=',1)[1] for x in args if x.startswith('rog5.bundle=')]
    if len(bundles)!=1: raise ValueError('bundle identity is ambiguous')
    return dict(boot_id=boot,bundle=bundles[0],release=os.uname().release)
actual=identity()
if actual!=request['identity']: raise ValueError('wrong target; no userspace reads')
def read_file(path):
    def signature(s):
        return (s.st_ino,s.st_dev,s.st_size,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_mtime_ns,s.st_ctime_ns)
    parts=path.split('/')[1:]
    directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=child
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        with os.fdopen(fd,'rb') as f:
            before=os.fstat(f.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size>1048576:
                raise ValueError('not a bounded regular file')
            data=f.read(1048577);after=os.fstat(f.fileno())
            if signature(before)!=signature(after):
                raise ValueError('file changed during read')
            current=os.stat(parts[-1],dir_fd=directory,follow_symlinks=False)
            if signature(current)!=signature(after):
                raise ValueError('pathname changed during read')
            return dict(status='present',path=path,size=len(data),sha256=hashlib.sha256(data).hexdigest(),
                        mode=stat.S_IMODE(after.st_mode),uid=after.st_uid,gid=after.st_gid,nlink=after.st_nlink)
    finally: os.close(directory)
files={}
for role,path in request['files'].items():
    try: files[role]=read_file(path)
    except (OSError,ValueError) as error: files[role]=dict(status='error',reason=type(error).__name__)
if identity()!=actual: raise ValueError('boot changed during read')
actual['files']=files
print(json.dumps(actual))
'''


def collect(identity,key,known_hosts):
    host_gate(identity)  # Before opening credentials or invoking SSH.
    credential(key,True);credential(known_hosts,False)
    request=dict(identity={k:identity[k] for k in ('boot_id','bundle','release')},
                 files={role:target for role,(_,target,_) in FILES.items()})
    script='INPUT='+repr(json.dumps(request))+'\n'+PROBE
    argv=['/usr/bin/ssh','-F','/dev/null','-o','BatchMode=yes','-o','IdentitiesOnly=yes',
          '-o','IdentityAgent=none','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no',
          '-o','ConnectionAttempts=1','-o','ConnectTimeout=3','-o','ServerAliveInterval=2',
          '-o','ServerAliveCountMax=2','-o','HostKeyAlias=169.254.77.2',
          '-o','UserKnownHostsFile='+str(known_hosts),'-i',str(key),'root@10.77.0.2',
          'python3 -I -B -c '+shlex.quote(script)]
    result=subprocess.run(argv,capture_output=True,timeout=15)
    if result.returncode or len(result.stdout)>16384:
        raise ValueError('authenticated probe failed or exceeded output bound')
    host_gate(identity)
    return json.loads(result.stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--boot-id',required=True)
    parser.add_argument('--identity-file',required=True,type=Path)
    parser.add_argument('--known-hosts',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    started=time.monotonic()
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',args.boot_id):
        raise ValueError('invalid exact boot ID')
    record=dict(line.split('=',1) for line in CAPTURE.CLAIMS.expected_record(args.profile).decode().splitlines())
    if record['execution']!='fastboot-boot-selector-trial':
        raise ValueError('check requires the admitted persistent selector trial family')
    CAPTURE.CLAIMS.verify_entered(args.profile)  # Read-only; never creates authority.
    raw=args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=record['manifest_sha256']:
        raise ValueError('manifest differs from canonical record')
    manifest=dict(line.split('=',1) for line in raw.decode('ascii').splitlines())
    identity=dict(serial=record['serial'],bundle=record['target_bundle'],
                  release=manifest['target_release'],boot_id=args.boot_id)
    expected=expected_files();source=CAPTURE.ACCEPTANCE.source_identity()
    output=args.output.resolve()
    if not args.output.is_absolute() or output.is_relative_to(REPO) or output.exists():
        raise ValueError('output must be a new private directory outside Git')
    output.mkdir(mode=0o700)
    report=dict(status='FAIL',source=source,identity=identity,expected=expected,
                manifest_sha256=record['manifest_sha256'],canonical_record=record,
                runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='six-file deployed userspace component; not full release, power or installed-recovery qualification',
                mutations='none requested; ordinary filesystem read/atime semantics only')
    try:
        actual=collect(identity,args.identity_file,args.known_hosts)
        report['actual']=actual
        validate_snapshot(actual,identity,expected)
        if source!=CAPTURE.ACCEPTANCE.source_identity() or expected!=expected_files():
            raise ValueError('source changed during check')
        report['status']='PASS'
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        report['reason']=str(error)
    report['seconds']=time.monotonic()-started
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],seconds=report['seconds'],output=str(output))))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,KeyError,ValueError,subprocess.SubprocessError) as error:
        print('FAIL '+str(error),file=sys.stderr);sys.exit(1)
