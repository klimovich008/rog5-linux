#!/usr/bin/env python3
"""Read-only userspace or readiness check on an already admitted target."""
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


def ssh_command(key,known_hosts):
    return ['/usr/bin/ssh','-F','/dev/null','-o','BatchMode=yes','-o','IdentitiesOnly=yes',
            '-o','IdentityAgent=none','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no',
            '-o','ConnectionAttempts=1','-o','ConnectTimeout=3','-o','ServerAliveInterval=2',
            '-o','ServerAliveCountMax=2','-o','HostKeyAlias=169.254.77.2',
            '-o','UserKnownHostsFile='+str(known_hosts),'-i',str(key),'root@10.77.0.2']


def collect(identity,key,known_hosts):
    host_gate(identity)  # Before opening credentials or invoking SSH.
    credential(key,True);credential(known_hosts,False)
    request=dict(identity={k:identity[k] for k in ('boot_id','bundle','release')},
                 files={role:target for role,(_,target,_) in FILES.items()})
    script='INPUT='+repr(json.dumps(request))+'\n'+PROBE
    argv=[*ssh_command(key,known_hosts),
          'python3 -I -B -c '+shlex.quote(script)]
    result=subprocess.run(argv,capture_output=True,timeout=15)
    if result.returncode or len(result.stdout)>16384:
        raise ValueError('authenticated probe failed or exceeded output bound')
    host_gate(identity)
    return json.loads(result.stdout)


READINESS_FAMILIES={'fastboot-boot-fallback-only','fastboot-boot-ram-bundle','fastboot-boot-selector-trial'}
READINESS_KEYS=('boot_before','boot_after','kernel','bundle','run_fstype',
                'marker_metadata','ssh_identity_service','marker')
# V11 has no Python. These exact shell/coreutils commands were exercised on its
# retained target filesystem and in a separate authenticated same-boot probe.
READINESS_PROBE=r'''set -eu
export LC_ALL=C
before=$(cat /proc/sys/kernel/random/boot_id)
test "$before" = "$expected_boot"
kernel=$(uname -r)
test "$kernel" = "$expected_release"
bundle=
count=0
set -f
for arg in $(cat /proc/cmdline); do
 case "$arg" in rog5.bundle=*) bundle=${arg#rog5.bundle=}; count=$((count+1));; esac
done
test "$count" = 1
test "$bundle" = "$expected_bundle"
test -d /run; test ! -L /run
file=/run/rog5-p2-ready
test -f "$file"; test ! -L "$file"
test "$(stat -c %s "$file")" -le 16384
identity=$(stat -c '%d:%i:%s:%y:%z:%a:%u:%g:%h:%F' "$file")
metadata=$(stat -c '%u:%g:%a:%F:%h' "$file")
marker=$(cat "$file")
test "$identity" = "$(stat -c '%d:%i:%s:%y:%z:%a:%u:%g:%h:%F' "$file")"
fs=$(findmnt -n -o FSTYPE --target "$file")
service=$(systemctl is-active rog5-persistent-ssh-identity.service)
after=$(cat /proc/sys/kernel/random/boot_id)
printf '%s\0' "$before" "$after" "$kernel" "$bundle" "$fs" "$metadata" "$service" "$marker"
'''


def parse_readiness(payload):
    if len(payload)>20000: raise ValueError('readiness output exceeded bound')
    fields=payload.decode('ascii').split('\0')
    if len(fields)!=len(READINESS_KEYS)+1 or fields[-1]:
        raise ValueError('invalid readiness framing')
    return dict(zip(READINESS_KEYS,fields[:-1]))


def validate_readiness(actual,identity,family):
    if family not in READINESS_FAMILIES: raise ValueError('unsupported readiness family')
    if (actual.get('boot_before')!=identity['boot_id'] or actual.get('boot_after')!=identity['boot_id']
            or actual.get('kernel')!=identity['release'] or actual.get('bundle')!=identity['bundle']):
        raise ValueError('readiness target identity mismatch')
    if (actual.get('run_fstype')!='tmpfs' or actual.get('marker_metadata')!='0:0:444:regular file:1'
            or actual.get('ssh_identity_service')!='active'):
        raise ValueError('readiness marker freshness/metadata or SSH identity service')
    rows=[line.split('=',1) for line in actual['marker'].splitlines()]
    if not rows or any(len(row)!=2 for row in rows) or len({row[0] for row in rows})!=len(rows):
        raise ValueError('malformed or duplicate readiness fields')
    fields=dict(rows)
    if fields.get('status')!='PASS' or fields.get('kernel')!=identity['release'] or fields.get('ssh')!='strict-key-only':
        raise ValueError('readiness core fields failed')
    bound=fields.get('attested_boot_id')
    if bound is not None and bound!=identity['boot_id']:
        raise ValueError('stale boot-bound readiness')
    legacy=bound is None and family=='fastboot-boot-fallback-only'
    if not legacy and bound!=identity['boot_id']:
        raise ValueError('current server requires boot-bound readiness')
    return dict(scope='legacy fallback SSH/readiness component' if legacy else 'boot-bound SSH/readiness component',
                marker_boot_bound=not legacy,release_qualified=False)


def collect_readiness(identity,key,known_hosts):
    host_gate(identity)  # Same exact topology/route and credential gates as composition.
    credential(key,True);credential(known_hosts,False)
    script=''.join('expected_'+name+'='+shlex.quote(identity[field])+'\n'
                   for name,field in [('boot','boot_id'),('release','release'),('bundle','bundle')])+READINESS_PROBE
    result=subprocess.run([*ssh_command(key,known_hosts),'sh -s'],input=script.encode(),capture_output=True,timeout=15)
    if result.returncode: raise ValueError('authenticated readiness probe failed')
    host_gate(identity)
    return parse_readiness(result.stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--manifest',required=True,type=Path)
    parser.add_argument('--boot-id',required=True)
    parser.add_argument('--identity-file',required=True,type=Path)
    parser.add_argument('--known-hosts',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--readiness-only',action='store_true',
                        help='shell-only SSH/readiness component, not six-file or release qualification')
    args=parser.parse_args()
    started=time.monotonic()
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',args.boot_id):
        raise ValueError('invalid exact boot ID')
    record=dict(line.split('=',1) for line in CAPTURE.CLAIMS.expected_record(args.profile).decode().splitlines())
    if args.readiness_only and record['execution'] not in READINESS_FAMILIES:
        raise ValueError('unsupported readiness family')
    if not args.readiness_only and record['execution']!='fastboot-boot-selector-trial':
        raise ValueError('check requires the admitted persistent selector trial family')
    CAPTURE.CLAIMS.verify_entered(args.profile)  # Read-only; never creates authority.
    raw=args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=record['manifest_sha256']:
        raise ValueError('manifest differs from canonical record')
    manifest=dict(line.split('=',1) for line in raw.decode('ascii').splitlines())
    identity=dict(serial=record['serial'],bundle=record['target_bundle'],
                  release=manifest['target_release'],boot_id=args.boot_id)
    expected={} if args.readiness_only else expected_files();source=CAPTURE.ACCEPTANCE.source_identity()
    output=args.output.resolve()
    if not args.output.is_absolute() or output.is_relative_to(REPO) or output.exists():
        raise ValueError('output must be a new private directory outside Git')
    output.mkdir(mode=0o700)
    report=dict(status='FAIL',source=source,identity=identity,expected=expected,
                manifest_sha256=record['manifest_sha256'],canonical_record=record,
                runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='SSH/readiness component' if args.readiness_only else 'six-file deployed userspace component; not full release, power or installed-recovery qualification',
                release_qualified=False,
                mutations='none requested; ordinary filesystem read/atime semantics only')
    try:
        actual=(collect_readiness if args.readiness_only else collect)(identity,args.identity_file,args.known_hosts)
        report['actual']=actual
        if args.readiness_only:
            report.update(validate_readiness(actual,identity,record['execution']))
        else:
            validate_snapshot(actual,identity,expected)
        if source!=CAPTURE.ACCEPTANCE.source_identity() or (not args.readiness_only and expected!=expected_files()):
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
