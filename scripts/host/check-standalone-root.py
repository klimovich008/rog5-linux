#!/usr/bin/env python3
"""Read-only local-root component for S01; not ordinary-boot qualification."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

spec=importlib.util.spec_from_file_location('standalone_deployed',Path(__file__).with_name('check-deployed-server.py'))
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)

PROBE=r'''
import json,os,subprocess
from pathlib import Path
def read(path,limit=1048576):
 with open(path) as f: value=f.read(limit+1)
 if len(value)>limit: raise ValueError('observation bound')
 return value.strip()
def identity():
 return dict(boot_id=read('/proc/sys/kernel/random/boot_id'),release=os.uname().release,
  bundles=[x.split('=',1)[1] for x in read('/proc/cmdline').split() if x.startswith('rog5.bundle=')])
expected=dict(boot_id=request['boot_id'],release=request['release'],bundles=[request['bundle']])
if identity()!=expected: raise ValueError('wrong boot; no storage reads')
blocks={p.parent.name:read(p) for p in Path('/sys/class/block').glob('sd*/ro')}
root=Path('/sys/class/block/sda24')
geometry={name:read(root/name) for name in ('partition','start','size','ro','uevent')}
loops={p.parent.parent.name:read(p) for p in Path('/sys/class/block').glob('loop*/loop/backing_file')}
units={name:subprocess.check_output(['systemctl','show',name,'-p','ActiveState','--value'],text=True,timeout=2).strip()
 for name in ('rog5-persistent-state.service','rog5-persistent-ssh-identity.service','rog5-early-sshd.service','rog5-healthd.service')}
power={name:read('/sys/class/power_supply/qcom-battmgr-bat/'+name,128)
 for name in ('health','temp','voltage_now')}
def optional_power(name):
 try: return dict(status='present',value=read('/sys/class/power_supply/qcom-battmgr-bat/'+name,128))
 except FileNotFoundError: return dict(status='absent')
 except OSError: return dict(status='error')
power_optional={name:optional_power(name) for name in ('current_now','status','capacity')}
value=dict(identity=request,mountinfo=read('/proc/self/mountinfo'),blocks=blocks,geometry=geometry,
 loops=loops,units=units,power=power,power_optional=power_optional,
 usb_online=read('/sys/class/power_supply/qcom-battmgr-usb/online'),
 root_device=str(Path('/dev/disk/by-partlabel/arch_root_a').resolve(strict=True)))
if identity()!=expected: raise ValueError('boot changed')
print(json.dumps(value))
'''

def require(ok,reason):
    if not ok: raise ValueError(reason)

def mounts(raw):
    require(isinstance(raw,str) and len(raw)<=1048576,'mount inventory bound')
    result={}
    for line in raw.splitlines():
        words=line.split();require(words.count('-')==1,'malformed mount record')
        cut=words.index('-');require(cut>=6 and len(words)==cut+4,'malformed mount fields')
        target=words[4]
        require(target not in result,'stacked/ambiguous mount')
        # Required mount paths are space-free. Preserve all unknown escapes;
        # do not normalize malformed input into an accepted path.
        result[target]=dict(device=words[2],options=set(words[5].split(',')),
            fstype=words[cut+1],source=words[cut+2],super_options=set(words[cut+3].split(',')))
    require(result,'empty mount inventory')
    return result

def validate(value,identity):
    require(value['identity']==identity,'boot identity mismatch')
    table=mounts(value['mountinfo'])
    require(not any(m['fstype'] in {'nfs','nfs4','cifs','smb3','9p'} for m in table.values()),'network filesystem present')
    def mount(path,kind,source,mode):
        require(path in table,'missing mount '+path);m=table[path]
        require(m['fstype']==kind and (source is None or m['source']==source)
                and mode in m['options'] and ({'ro','rw'}-{mode}).isdisjoint(m['options']),
                'wrong mount '+path)
        return m
    lower=mount('/.rog5/root-ro','ext4','/dev/sda24','ro')
    require('norecovery' in lower['super_options'],'native lower permits journal replay')
    mount('/.rog5/userdata-rw','ext4','/dev/sda23','rw')
    state=mount('/.rog5/state','ext4',None,'rw')
    require(re.fullmatch('/dev/loop[0-9]+',state['source']),'overlay is not loop-backed')
    loop=state['source'].removeprefix('/dev/')
    require(value['loops'].get(loop) in {'/mnt/userdata/rog5/root/root-overlay-v1.ext4',
        '/.rog5/userdata-rw/rog5/root/root-overlay-v1.ext4'},'wrong persistent upper backing')
    root=mount('/','overlay','overlay','rw')
    require({'lowerdir=/mnt/root-ro','upperdir=/mnt/state/upper','workdir=/mnt/state/work'}<=root['super_options'],
            'wrong root overlay composition')
    require(value['root_device']=='/dev/sda24','wrong native partition label')
    layout=json.loads((D.REPO/'configs/storage/rog5-dedicated-linux-v1.json').read_text())['proposal']['arch_root_a']
    geometry=value['geometry']
    require(geometry['partition']==str(layout['number']) and geometry['start']==str(layout['first_lba']*8)
        and geometry['size']==str(layout['size_lba']*8) and geometry['ro']=='1'
        and 'PARTNAME='+layout['name'] in geometry['uevent'].splitlines(),'native geometry changed')
    blocks=value['blocks']
    require(len(blocks)==117 and set(blocks.values())<={'0','1'}
        and {k for k,v in blocks.items() if v=='0'}=={'sda','sda23'},'unexpected writable storage')
    require(set(value['units'])=={'rog5-persistent-state.service','rog5-persistent-ssh-identity.service',
        'rog5-early-sshd.service','rog5-healthd.service'} and set(value['units'].values())=={'active'},'core services unavailable')
    power=value['power']
    require(power['health']=='Good' and 0<=int(power['temp'])<400 and
        8400000<=int(power['voltage_now'])<=9000000 and value['usb_online']=='1','unsafe or missing power')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('profile','boot-id'):p.add_argument('--'+key,required=True)
    for key in ('manifest','identity-file','known-hosts','output'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args();os.umask(0o077);started=time.monotonic()
    require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',args.boot_id),'invalid boot identity')
    record=dict(x.split('=',1) for x in D.CAPTURE.CLAIMS.expected_record(args.profile).decode().splitlines())
    require(record['execution']=='fastboot-boot-selector-trial','unsupported persistent family')
    D.CAPTURE.CLAIMS.verify_entered(args.profile)  # No new entry/claim or target execution.
    raw=args.manifest.read_bytes();require(hashlib.sha256(raw).hexdigest()==record['manifest_sha256'],'manifest mismatch')
    manifest=dict(x.split('=',1) for x in raw.decode().splitlines())
    identity=dict(serial=record['serial'],bundle=record['target_bundle'],release=manifest['target_release'],boot_id=args.boot_id)
    require(args.output.is_absolute() and not args.output.resolve().is_relative_to(D.REPO),'private output required')
    args.output.mkdir(mode=0o700)
    report=dict(status='FAIL',identity=identity,source=D.CAPTURE.ACCEPTANCE.source_identity(),
        manifest_sha256=record['manifest_sha256'],s01_qualified=False,release_qualified=False,
        scope='current local-root/readiness component only; no historical boot-service absence or ordinary reboot proof')
    try:
        expected=D.expected_files(args.profile)
        actual=D.collect(identity,args.identity_file,args.known_hosts)
        report.update(expected_userspace=expected,userspace=actual)
        D.validate_snapshot(actual,identity,expected)
        readiness=D.collect_readiness(identity,args.identity_file,args.known_hosts)
        D.validate_readiness(readiness,identity,record['execution'])
        D.host_gate(identity)
        script='request='+repr(identity)+'\n'+PROBE
        command=[*D.ssh_command(args.identity_file,args.known_hosts),'python3 -I -B -c '+shlex.quote(script)]
        actual=subprocess.run(command,capture_output=True,timeout=20)
        (args.output/'stdout.json').write_bytes(actual.stdout);(args.output/'stderr.log').write_bytes(actual.stderr)
        require(actual.returncode==0 and len(actual.stdout)<=1048576,'target observation failed/bound')
        value=json.loads(actual.stdout);validate(value,identity);D.host_gate(identity)
        require(report['source']==D.CAPTURE.ACCEPTANCE.source_identity(),'source changed')
        report.update(status='PASS',power=value['power'],power_optional=value['power_optional'],
            stdout_sha256=hashlib.sha256(actual.stdout).hexdigest())
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:report['reason']=str(error)
    report['seconds']=time.monotonic()-started
    (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
