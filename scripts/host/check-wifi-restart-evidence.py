#!/usr/bin/env python3
"""F02 offline replay of explicitly pinned, reviewed live evidence. No SSH/boot."""
import argparse
import gzip
import hashlib
import importlib.util
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import stat
import time

NAMES=('rog5-wifi-radio','rog5-wifi-wpa','rog5-wifi-dhcp','rog5-early-sshd',
       'rog5-healthd','rog5-persistent-state','rog5-persistent-ssh-identity','rog5-tailscaled')
HEX=re.compile('[0-9a-f]{64}')

def require(ok,reason):
    if not ok: raise ValueError(reason)

def digest(raw): return hashlib.sha256(raw).hexdigest()

def decode(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'duplicate metadata')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=unique)

def pinned(path,expected,limit=524288):
    require(path.is_absolute() and isinstance(expected,str) and HEX.fullmatch(expected),'invalid input pin')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid==os.getuid() and
                before.st_nlink==1 and not before.st_mode & 0o022 and before.st_size<=limit,'unsafe evidence file')
        raw=stream.read(limit+1);after=os.fstat(stream.fileno())
        signature=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        require(signature(before)==signature(after)==signature(path.lstat()) and len(raw)<=limit,'evidence changed')
    require(digest(raw)==expected,'evidence hash mismatch')
    return raw

def elapsed(value,limit):
    require(type(value) in (int,float) and math.isfinite(value) and 0<value<=limit,'invalid duration/deadline')

def composition_matches(composition,candidate,hashes):
    require(set(hashes)=={'kernel','dtb','initramfs','rootfs','boot_bundle'} and
            all(isinstance(v,str) and HEX.fullmatch(v) for v in hashes.values()),'artifact roles')
    require(composition['status']=='PASS' and composition['a01_qualified'] is True and
            composition['candidate']==candidate and composition['artifact_hashes']==hashes,'incompatible composition')

def validate(record,logs,identity,archive_sha):
    require(record['status']=='PASS' and record['release_qualified'] is False,'not completed component')
    require(record['source']['clean'] is True and re.fullmatch('[0-9a-f]{40}',record['source']['revision']),'unbound original source')
    require(record['identity']==identity and record['artifact_sha256']==archive_sha,'release identity mismatch')
    require(record['deadline_seconds']==120 and record['per_restart_seconds']==40,'observation limits changed')
    elapsed(record['seconds'],120)
    cases=record['cases']
    require(len(cases)==2 and [c['action'] for c in cases]==['rog5-wifi-wpa','rog5-wifi-dhcp'],'restart scope')
    base=record['before']
    def snapshot(value):
        require(value['identity']==identity and set(value['units'])==set(NAMES),'snapshot identity')
        for name,unit in value['units'].items():
            require(unit['ActiveState']=='active' and re.fullmatch('[0-9a-f]{32}',unit['InvocationID']),'inactive unit')
            if name not in ('rog5-wifi-wpa','rog5-wifi-dhcp'):
                require(unit==base['units'][name],'radio/core changed')
        require(value['interface']==base['interface'],'interface changed')
        power=value['power']
        require(power['health']=='Good' and 0<=int(power['temp'])<400 and
                8400000<=int(power['voltage_now'])<=8800000,'unsafe power')
    snapshot(base);previous=base;end=0
    for case in cases:
        require(case['status']=='PASS','restart not complete');elapsed(case['seconds'],40)
        elapsed(case['started_seconds'],120)
        require(case['started_seconds']>=end,'overlapping/reordered restarts')
        end=case['started_seconds']+case['seconds']
        require(end<=record['seconds'],'restart exceeds observation')
        after=case['after'];snapshot(after)
        for name in ('rog5-wifi-wpa','rog5-wifi-dhcp'):
            changed=previous['units'][name]['InvocationID']!=after['units'][name]['InvocationID']
            require(changed==(name=='rog5-wifi-dhcp' or case['action']=='rog5-wifi-wpa'),'wrong restart propagation')
        previous=after
    expected_logs=set();wifi_count=0;last_usb=None
    require(6<=len(record['commands'])<=100,'command count')
    for index,command in enumerate(record['commands'],1):
        require(type(command['sequence']) is int and command['sequence']==index and
                type(command['returncode']) is int and command['returncode']==0 and
                HEX.fullmatch(command['script_sha256']),'command failed or sequence changed')
        output=f'{index:02d}.stdout';error=f'{index:02d}.stderr'
        expected_logs.update((output,error))
        require(not logs[error],'unexpected command stderr')
        value=decode(logs[output])
        if command['transport']=='usb':
            snapshot(value);last_usb=value
        else:
            require(command['transport']=='wifi' and wifi_count<3 and last_usb is not None,'transport sequence')
            expected=base if wifi_count==0 else cases[wifi_count-1]['after']
            require(last_usb==expected,'missing exact boundary snapshot')
            require(last_usb['carrier']=='1' and last_usb['default_route'] is True and
                    len(last_usb['addresses'])==1,'lease not recovered')
            connection=value['connection'].split()
            require(value['boot']==identity['boot_id'] and len(connection)==4 and
                    connection[2]==last_usb['addresses'][0] and connection[3]=='22','wrong SSH endpoint')
            client=ipaddress.IPv4Address(connection[0]);server=ipaddress.IPv4Address(connection[2])
            require(client!=server and not server.is_loopback and not server.is_unspecified,'invalid endpoint')
            wifi_count+=1
    require(wifi_count==3 and record['commands'][-1]['transport']=='wifi' and
            set(logs)==expected_logs,'incomplete or extra evidence')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--inputs-sha256',required=True)
    p.add_argument('--candidate',required=True)
    p.add_argument('--target-archive',type=Path,required=True)
    p.add_argument('--artifact-hashes',required=True,help='JSON from the verified release receipt')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();start=time.monotonic()
    spec=importlib.util.spec_from_file_location('wifi_acceptance',Path(__file__).with_name('release-acceptance.py'))
    A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
    require(args.output.is_absolute() and not args.output.resolve().is_relative_to(A.REPO),'private output required')
    args.output.mkdir(mode=0o700)
    report=dict(status='FAIL',f02_qualified=False,evidence_reused=True,source=A.source_identity(),
                runner_sha256=digest(Path(__file__).read_bytes()),inputs_sha256=args.inputs_sha256)
    try:
        raw=pinned(args.inputs,args.inputs_sha256)
        inputs=decode(raw)
        require(inputs['format']=='rog5-wifi-restart-evidence-v1' and 10<=len(inputs['files'])<=204,'input format/count')
        data={}
        for name,entry in inputs['files'].items():
            require(name in ('result','composition','adapter','manifest') or
                    re.fullmatch(r'[0-9]{2,3}\.(stdout|stderr)',name),'unknown evidence role')
            data[name]=pinned(Path(entry['path']),entry['sha256'])
        record=decode(data.pop('result'));composition=decode(data.pop('composition'))
        adapter=data.pop('adapter');manifest_raw=data.pop('manifest')
        # Adapter is reviewed/hash-bound data, never imported or executed here.
        require(bool(adapter),'missing reviewed observation adapter')
        hashes=decode(args.artifact_hashes)
        composition_matches(composition,args.candidate,hashes)
        # Read-only canonical lookup; this does not admit, execute or use credentials.
        spec=importlib.util.spec_from_file_location('wifi_claims',Path(__file__).with_name('consume-exact-boot-claim.py'))
        claims=importlib.util.module_from_spec(spec);spec.loader.exec_module(claims)
        canonical=dict(line.split('=',1) for line in claims.expected_record(args.candidate).decode().splitlines())
        claims.verify_entered(args.candidate)
        require(canonical['manifest_sha256']==digest(manifest_raw) and
                canonical['boot_image_sha256']==hashes['boot_bundle'],'canonical release mismatch')
        manifest=dict(line.split('=',1) for line in manifest_raw.decode('ascii').splitlines())
        for name in ('kernel','dtb','initramfs'):
            require(manifest[name+'_sha256']==hashes[name],'manifest artifact mismatch')
        identity=dict(serial=canonical['serial'],bundle=canonical['target_bundle'],
                      release=manifest['target_release'],boot_id=record['identity']['boot_id'])
        require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',identity['boot_id']),'invalid boot ID')
        archive=args.target_archive.read_bytes()
        require(digest(archive)==hashes['initramfs'],'archive bytes changed')
        spec=importlib.util.spec_from_file_location('wifi_sealed',Path(__file__).with_name('run-sealed-busybox.py'))
        sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
        entries=sealed.ARCHIVE.entries(gzip.decompress(archive))
        expected_units={name+'.service':digest(entries['rog5-native-wifi/units/'+name+'.service'][1]) for name in NAMES[:3]}
        require(record['units']==expected_units,'deployed unit/archive mismatch')
        validate(record,data,identity,hashes['initramfs'])
        require(raw==pinned(args.inputs,args.inputs_sha256),'inputs changed')
        report.update(status='PASS',f02_qualified=True,candidate=args.candidate,artifact_hashes=hashes,
                      original_source=record['source'],identity=identity,
                      observed_seconds=record['seconds'],evidence={k:v['sha256'] for k,v in inputs['files'].items()})
    except (ValueError,KeyError,TypeError,OSError) as error:
        report['error']=str(error)
    report['duration_seconds']=time.monotonic()-start
    (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],seconds=report['duration_seconds'],error=report.get('error'))))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
