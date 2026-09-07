#!/usr/bin/env python3
"""Offline S02/S03/S04 replay: no phone connection, mutation or execution claim."""
import argparse
import ast
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import time

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

B=load('runtime_boot',Path(__file__).with_name('check-standalone-boot.py'))
F=load('runtime_wifi',Path(__file__).with_name('check-wifi-restart-evidence.py'))
T=load('runtime_stream',Path(__file__).with_name('network-transfer-stream.py'))
R=B.R;require=B.require
ACTIONS=('rog5-healthd','rog5-early-sshd','rog5-wifi-wpa','rog5-wifi-dhcp')
REFUSED=b'ssh: connect to host 10.77.0.2 port 22: Connection refused'

def snapshot(value,identity):
    require(value['identity']==identity and set(value['units'])==set(F.NAMES),'snapshot identity/units')
    for unit in value['units'].values():
        require(unit['ActiveState']=='active' and re.fullmatch('[0-9a-f]{32}',unit['InvocationID']),'inactive service')
    p=value['power']
    require(all(type(p[k]) is str and re.fullmatch('-?[0-9]+',p[k]) for k in ('temp','voltage_now')),'invalid telemetry type')
    require(p['health']=='Good' and 0<=int(p['temp'])<400
            and 8400000<=int(p['voltage_now'])<=8800000,'unsafe power')
    require(re.fullmatch('[A-Za-z0-9_.:-]{1,32}',value['interface']),'invalid radio interface')

def ready(value):
    require(value['carrier']=='1' and value['default_route'] is True and len(value['addresses'])==1,'lease missing')
    address=ipaddress.IPv4Address(value['addresses'][0])
    require(not address.is_loopback and not address.is_unspecified and not address.is_multicast,'invalid lease')

def link(value,base):
    require(set(value)=={'name','host_interface','target_interface','source','address'},'link fields')
    if value['name']=='usb':
        require(value==dict(name='usb',host_interface=B.ROOT.D.CAPTURE.INTERFACE,
            target_interface='usb0',source='10.77.0.1',address='10.77.0.2'),'wrong USB link')
    else:
        require(value['name']=='wifi' and value['host_interface']=='wlan0'
                and value['target_interface']==base['interface']
                and value['address']==base['addresses'][0],'wrong Wi-Fi link')
        source=ipaddress.IPv4Address(value['source'])
        require(not source.is_loopback and not source.is_unspecified and not source.is_multicast
                and value['source'] not in (value['address'],'10.77.0.1'),'wrong Wi-Fi source')

def validate(kind,record,logs,identity,hashes,expected_digest=T.expected_digest):
    require(kind in ('S02','S03'),'unsupported outcome')
    require(record['status']=='PASS' and record[kind.lower()+'_qualified'] is True
            and record['release_qualified'] is False,'incomplete observation')
    require(record['source']['clean'] is True and re.fullmatch('[0-9a-f]{40}',record['source']['revision'])
            and re.fullmatch('[0-9a-f]{64}',record['source']['worktree_digest']),'unbound original source')
    require(record['identity']==identity and record['artifact_hashes']==hashes,'different release')
    limit=720 if kind=='S02' else 300
    require(type(record['deadline_seconds']) is int and record['deadline_seconds']==limit,'changed deadline')
    F.elapsed(record['seconds'],limit)
    base=record['before'];snapshot(base,identity);ready(base)
    cases=record['cases'];require(len(cases)==4,'incomplete cases')
    if kind=='S02':
        require(record['per_direction_seconds']==180 and len(record['links'])==2,'transfer bounds/links')
        require([x['name'] for x in record['links']]==['usb','wifi'],'missing transport')
        for item in record['links']:link(item,base)
        require([(c['link'],c['direction']) for c in cases]==
                [(item,d) for item in record['links'] for d in ('upload','download')],'transfer ordering/scope')
        require(len({c['nonce'] for c in cases})==4,'reused transfer nonce')
        for case in cases:
            require(case['status']=='PASS' and type(case['returncode']) is int and case['returncode']==0
                    and type(case['bytes']) is int and case['bytes']==T.LIMIT
                    and case['s02_qualified'] is False and F.HEX.fullmatch(case['script_sha256']),'incomplete transfer')
            T.validate(case['nonce'],case['bytes']);F.elapsed(case['duration_seconds'],180)
            require(case['sha256']==expected_digest(case['nonce'],T.LIMIT),'wrong stream digest')
        require(sum(c['duration_seconds'] for c in cases)<=record['seconds'],'inconsistent transfer timing')
    else:
        require(record['per_restart_seconds']==40 and [c['action'] for c in cases]==list(ACTIONS),'restart scope/bounds')
        prior=base;end=0
        for case in cases:
            require(case['status']=='PASS','incomplete restart')
            F.elapsed(case['seconds'],40);F.elapsed(case['started_seconds'],300)
            require(case['started_seconds']>=end,'overlapping restart actions')
            end=case['started_seconds']+case['seconds'];require(end<=record['seconds'],'restart exceeds observation')
            after=case['after'];snapshot(after,identity);ready(after)
            require(after['interface']==base['interface'],'radio changed')
            changed={case['action']}
            if case['action']=='rog5-wifi-wpa':changed.add('rog5-wifi-dhcp')
            for name,unit in prior['units'].items():
                if name in changed:
                    require(unit['InvocationID']!=after['units'][name]['InvocationID'],'restart absent')
                else:require(unit==after['units'][name],'unexpected restart: '+name)
            prior=after
    commands=record['commands'];require(9<=len(commands)<=200,'command count')
    expected_logs=set();observed=[];wifi_count=0;refused_count=0
    for n,command in enumerate(commands,1):
        require(type(command['sequence']) is int and command['sequence']==n,'command order')
        output=f'{n:02d}.stdout';error=f'{n:02d}.stderr';expected_logs.update((output,error))
        code=command['returncode'];require(type(code) is int,'invalid command result')
        script_key='sha256' if kind=='S02' else 'script_sha256'
        require(F.HEX.fullmatch(command[script_key]),'missing exact command')
        if code:
            # Captured restart race: only the same read-only observer can wait.
            # No changed key, partial output, action failure or Wi-Fi error is a retry.
            require(kind=='S03' and code==255 and command['link'] is None and not logs[output]
                    and logs[error].strip()==REFUSED and n>1
                    and command[script_key]==commands[0][script_key],'failed action or unexpected reconnect')
            refused_count+=1;require(refused_count<=24,'unbounded reconnect')
            continue
        refused_count=0;require(not logs[error],'unexpected stderr')
        value=B.READ.decode(logs[output])
        if kind=='S03' and command['link'] is not None:
            require(wifi_count<4 and value=={'boot':identity['boot_id']},'wrong Wi-Fi confirmation')
            boundary=cases[wifi_count]['after'];link(command['link'],boundary)
            require(observed and observed[-1]==boundary,'missing post-restart USB confirmation')
            wifi_count+=1
        else:
            snapshot(value,identity);observed.append(value)
            require(value['interface']==base['interface'],'radio interface changed')
            if kind=='S02':
                ready(value);require(value['units']==base['units'] and value['addresses']==base['addresses'],'server changed during transfer')
    require(expected_logs==set(logs) and observed and observed[0]==base,'incomplete/extra raw evidence')
    if kind=='S02':require(len(observed)==9 and len(commands)==9,'missing transfer boundary snapshots')
    else:
        require(wifi_count==4 and commands[-1]['link'] is not None,'missing final reconnect')
        require(all(c['after'] in observed for c in cases),'missing raw post-restart evidence')

def evaluate(args):
    if args.kind=='S04':
        return load('storage_durability_evidence',Path(__file__).with_name('storage-durability-evidence.py')).evaluate(args,B)
    raw=B.pinned(args.inputs,args.inputs_sha256);inputs=B.READ.decode(raw)
    fixed={'result','adapter','snapshot','stream','s01','composition','manifest'}
    if args.kind=='S03':fixed.update(('transfer_adapter','transfer_result'))
    require(inputs['format']=='rog5-server-runtime-evidence-v1' and inputs['kind']==args.kind,'input format')
    roles=set(inputs['files'])
    require(fixed<=roles and len(roles)<=407 and
            all(x in fixed or re.fullmatch(r'[0-9]{2,3}\.(stdout|stderr)',x) for x in roles),'input roles')
    data={name:B.pinned(Path(item['path']),item['sha256']) for name,item in inputs['files'].items()}
    hashes=B.READ.unique([x.split('=',1) for x in args.artifact_hashes.split(',')])
    record=B.READ.decode(data['result']);s01=B.READ.decode(data['s01'])
    F.composition_matches(B.READ.decode(data['composition']),args.candidate,hashes)
    require(s01['status']=='PASS' and s01['s01_qualified'] is True and s01['candidate']==args.candidate
            and s01['artifact_hashes']==hashes
            and s01['runner_sha256']==B.sha(Path(B.__file__).read_bytes()),'missing compatible S01')
    identity=s01['identity']
    canonical=dict(x.split('=',1) for x in B.ROOT.D.CAPTURE.CLAIMS.expected_record(args.candidate).decode().splitlines())
    B.ROOT.D.CAPTURE.CLAIMS.verify_entered(args.candidate)
    require(canonical['serial']==identity['serial'] and canonical['target_bundle']==identity['bundle']
            and canonical['boot_image_sha256']==hashes['boot_bundle']
            and canonical['manifest_sha256']==B.sha(data['manifest']),'canonical mismatch')
    manifest=B.READ.unique([x.split('=',1) for x in data['manifest'].decode('ascii').splitlines()])
    require(manifest['target_release']==identity['release'],'kernel mismatch')
    for name in ('kernel','dtb','initramfs'):require(manifest[name+'_sha256']==hashes[name],'target mismatch')
    require(record['runner_sha256']==B.sha(data['adapter']) and data['adapter'],'changed reviewed coordinator')
    snapshot_key='snapshot_source_sha256' if args.kind=='S02' else 'snapshot_sha256'
    require(record[snapshot_key]==B.sha(data['snapshot']) and data['snapshot'],'changed snapshot producer')
    require(data['stream']==Path(T.__file__).read_bytes(),'changed stream implementation')
    if args.kind=='S02':
        require(record['stream_sha256']==B.sha(data['stream']) and record['s01_sha256']==B.sha(data['s01']),'changed stream/S01')
    else:
        transfer=B.READ.decode(data['transfer_result'])
        require(transfer['status']=='PASS' and transfer['s02_qualified'] is True and
                transfer['identity']==identity and transfer['artifact_hashes']==hashes and
                transfer['runner_sha256']==B.sha(data['transfer_adapter']),'different transport helper')
        # Literal extraction only: private operator sources are never executed.
        tree=ast.parse(data['transfer_adapter'])
        values=[ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='GUARD' for t in node.targets)]
        require(len(values)==1 and isinstance(values[0],str),'missing reviewed transport guard')
        for command in record['commands']:
            if command['link'] is not None:
                script='expected='+repr(identity)+'\nlink='+repr(command['link'])+'\n'+values[0]+"\nprint(json.dumps({'boot':expected['boot_id']}))"
                require(command['script_sha256']==B.sha(script.encode()),'changed authenticated endpoint command')
    # Check direct producer dependencies against the original run, not a new label.
    source=record['source']['revision'];require(re.fullmatch('[0-9a-f]{40}',source),'source revision')
    for name in ('check-deployed-server.py','network-transfer-stream.py'):
        relative='scripts/host/'+name
        previous=subprocess.check_output(['git','-C',str(R),'show',source+':'+relative],timeout=5)
        require(previous==(R/relative).read_bytes(),'changed observed dependency')
    validate(args.kind,record,{k:v for k,v in data.items() if k not in fixed},identity,hashes)
    for name,item in inputs['files'].items():require(data[name]==B.pinned(Path(item['path']),item['sha256']),'evidence changed')
    require(raw==B.pinned(args.inputs,args.inputs_sha256),'inputs changed')
    return dict(status='PASS',**{args.kind.lower()+'_qualified':True},candidate=args.candidate,
        identity=identity,artifact_hashes=hashes,original_source=record['source'],
        observed_seconds=record['seconds'],evidence_sha256={k:B.sha(v) for k,v in data.items()})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=('S02','S03','S04'),required=True)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--inputs-sha256',required=True)
    p.add_argument('--candidate',required=True);p.add_argument('--artifact-hashes',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(a.output.is_absolute() and not a.output.resolve().is_relative_to(R),'new private output required')
    os.umask(0o077);a.output.mkdir(mode=0o700);start=time.monotonic();A=B.ROOT.D.CAPTURE.ACCEPTANCE
    result=dict(status='FAIL',**{a.kind.lower()+'_qualified':False},release_qualified=False,evidence_reused=True,
        source=A.source_identity(),runner_sha256=B.sha(Path(__file__).read_bytes()),inputs_sha256=a.inputs_sha256)
    try:result.update(evaluate(a))
    except FileNotFoundError as error:result.update(status='BLOCKED',error=str(error))
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:result['error']=str(error)
    if result['source']!=A.source_identity():result.update(status='FAIL',**{a.kind.lower()+'_qualified':False},error='source changed')
    result['duration_seconds']=time.monotonic()-start
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],seconds=result['duration_seconds'],error=result.get('error'))))
    return {'PASS':0,'FAIL':1,'BLOCKED':3}[result['status']]
if __name__=='__main__':raise SystemExit(main())
