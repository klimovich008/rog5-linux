#!/usr/bin/env python3
"""Explicit completed rescue replay; no connection, credential use or boot."""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

H=load('retained_rescue_startup',Path(__file__).with_name('check-rescue-startup.py'))
R=H.D.REPO
G=load('retained_rescue_charging',R/'scripts/host/check-charging-regulation.py')
require=H.require
FIXED={'composition','c02','manifest','h02','h03','execution','capture_receipt',
       'capture_events','capture_result','first_ssh','readiness','ssh_attempts',
       'smoke','boot_log','h02_log','samples'}
ROLES=FIXED|{f'sample-{i:02d}.raw' for i in range(61)}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def pinned(path,pin):
    require(type(pin) is str and re.fullmatch('[0-9a-f]{64}',pin),'invalid evidence pin')
    raw=H.read_bytes(path,4*H.LIMIT)
    require(sha(raw)==pin,'changed pinned rescue evidence')
    return raw

def historical_source(source):
    require(type(source) is dict and source.get('clean') is True
            and type(source.get('revision')) is str and re.fullmatch('[0-9a-f]{40}',source['revision'])
            and source.get('worktree_digest')==sha(source['revision'].encode()),'unbound clean historical source')
    return source['revision']

def original_bytes(source,path,pin=None):
    raw=subprocess.check_output(['git','-C',str(R),'show',historical_source(source)+':'+path],timeout=5)
    require(pin is None or sha(raw)==pin,'original producer hash mismatch')
    return raw

def functions(raw):
    return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(raw).body
            if isinstance(node,ast.FunctionDef)}

def observation_compatibility(h02,h03,receipt,readiness):
    source=h02['source']
    require(source==h03['source']==receipt['source']==readiness['source'],'different historical sources')
    for name,pin in [('check-charging-regulation.py',h03['runner_sha256']),
                     ('h03-regulation.py',h03['criteria_sha256'])]:
        require(original_bytes(source,'scripts/host/'+name,pin)==(R/'scripts/host'/name).read_bytes(),
                'changed charging collector or criteria')
    original=functions(original_bytes(source,'scripts/host/check-rescue-startup.py',h02['runner_sha256']))
    current=functions(Path(H.__file__).read_bytes())
    for name in ('sealed_runtime','current_script','collect_current','validate_current'):
        require(original[name]==current[name],'changed runtime observation implementation')
    versions={}
    for role,name,pin in [('receiver','headless-stage-receiver.py',receipt['receiver_sha256']),
                          ('readiness','check-deployed-server.py',readiness['runner_sha256'])]:
        versions[role]=sha(original_bytes(source,'scripts/host/'+name,pin))
    # The latest predicates independently check all captured boot, timing and
    # transport data. Original versions are authenticated, never relabeled.
    return versions

def paired_composition(composition,c02,candidate,hashes):
    require(set(hashes)=={'kernel','dtb','initramfs','rootfs','boot_bundle'}
            and all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in hashes.values()),'rescue artifact roles')
    require(composition['status']=='PASS' and composition['a01_qualified'] is True
            and composition['candidate']==candidate and composition['artifact_hashes']==hashes
            and composition['root_unchanged'] is True,'incompatible rescue composition')
    contract=H.D.CAPTURE.ACCEPTANCE.load_contract()
    a01=next(test for test in contract['tests'] if test['id']=='A01')
    require(composition['checks']==dict.fromkeys(a01['required_checks'],'PASS')
            and 0<H.number(composition['duration_seconds'])<=a01['deadline_seconds'],
            'incomplete rescue composition or deadline')
    require(c02['status']=='PASS' and c02['c02_qualified'] is True
            and c02['release_qualified'] is False and c02['root_image_unchanged'] is True
            and c02['kernel_sha256']==hashes['kernel'] and c02['target_archive_sha256']==hashes['initramfs']
            and c02['root_image_sha256']==hashes['rootfs'],'incompatible rescue SSH/watchdog proof')
    require(c02['c02_variant']=='core-only' and c02['root_scope']=='retained-base-only'
            and [case['mode'] for case in c02['cases']]==['systemd-ack','systemd-stale-identity']
            and all(case['passed'] is True and type(case['exit_code']) is int and case['exit_code']==0
                    and 0<H.number(case['seconds'])<=50 for case in c02['cases']),
            'incomplete rescue SSH/watchdog cases')
    require(type(c02['duration_seconds']) in (int,float) and math.isfinite(c02['duration_seconds'])
            and 0<c02['duration_seconds']<=120,'rescue C02 deadline')
    for proof,name in [(composition,'check-release-composition.py'),(c02,'test-qemu-watchdog-handoff.py')]:
        require(original_bytes(proof['source'],'scripts/host/'+name,proof['runner_sha256'])
                ==(R/'scripts/host'/name).read_bytes(),'changed composition producer')
    for name in ('check-rescue-root-composition.py','run-sealed-busybox.py'):
        for proof in (composition,c02):
            require(original_bytes(proof['source'],'scripts/host/'+name)==(R/'scripts/host'/name).read_bytes(),
                    'changed composition dependency')

def capture_closed(receipt,result,events):
    timing=H.D.CAPTURE.ACCEPTANCE.load_contract()['defaults']['rescue_capture']
    required=sum(timing[key] for key in ('recovery_seconds','target_rollback_seconds','cleanup_seconds'))
    require(receipt['timing']==timing and H.number(receipt['required_seconds'])==required
            and H.number(receipt['deadline_monotonic'])-H.number(receipt['started_monotonic'])
                >=required+timing['preflight_seconds'],'original capture budget differs from contract')
    ended=[event for event in events if event['event']=='capture-ended']
    require(len(ended)==1 and result['status']==ended[0]['status']=='NOT RUN'
            and result['duration_seconds']==ended[0]['duration_seconds']
            and H.number(result['duration_seconds'])>=H.number(receipt['required_seconds'])
            and H.number(ended[0]['monotonic'])>=H.number(receipt['deadline_monotonic']),
            'incomplete original capture')
    cleanup=[event for event in events if event['event']=='host-cleanup']
    require([event['item'] for event in cleanup]==['route','firewall','profile','address']
            and all(event['status']=='PASS' and H.number(event['monotonic'])>ended[0]['monotonic'] for event in cleanup),
            'original capture cleanup incomplete')

def charging_rows(h03,rows,raw,identity,rollback):
    require(type(h03['samples']) is int and h03['samples']==61 and len(rows)==61
            and type(h03['raw_replies']) is int and h03['raw_replies']==61
            and h03['branch']=='firmware-full-v1','incomplete charging method')
    require(type(h03['duration_seconds']) in (int,float) and math.isfinite(h03['duration_seconds'])
            and 600<=h03['duration_seconds']<=660,'original H03 deadline')
    for index,row in enumerate(rows):
        sample=G.parse_frame(raw[f'sample-{index:02d}.raw'],identity,rollback)
        require(set(row)==set(sample)|{'read_seconds'} and
                all(type(row[key]) is type(value) and row[key]==value
                    for key,value in sample.items() if key!='elapsed_s'),'raw sample disagrees with series')
        require(type(row['read_seconds']) in (int,float) and math.isfinite(row['read_seconds'])
                and 0<=row['read_seconds']<=2,'sample read freshness')
        if index:
            host=H.number(row['elapsed_s'])-H.number(rows[index-1]['elapsed_s'])
            target=row['target_uptime_after']-rows[index-1]['target_uptime_after']
            require(8<=host<=12 and target>0 and abs(host-target)<=2,'charging sample timing gap')
    outcome=G.REGULATION.evaluate_full(rows)
    require(outcome==h03['outcome'] and H.number(rows[-1]['elapsed_s'])<=h03['duration_seconds'],
            'different charging outcome or enclosing duration')
    return outcome

def evaluate(args):
    input_raw=pinned(args.inputs,args.inputs_sha256);inputs=H.decode(input_raw)
    require(inputs['format']=='rog5-rescue-runtime-evidence-v1' and set(inputs['files'])==ROLES,'rescue evidence roles')
    raw={};total=0
    for name,item in inputs['files'].items():
        value=pinned(Path(item['path']),item['sha256']);total+=len(value)
        require(total<=16*H.LIMIT,'aggregate rescue evidence bound')
        raw[name]=value
    data={name:H.decode(value) for name,value in raw.items()
          if name in FIXED-{'manifest','capture_events','ssh_attempts','boot_log','h02_log','samples'}}
    hashes=H.unique([item.split('=',1) for item in args.artifact_hashes.split(',')])
    paired_composition(data['composition'],data['c02'],args.candidate,hashes)
    canonical=dict(line.split('=',1) for line in H.D.CAPTURE.CLAIMS.expected_record(args.candidate).decode().splitlines())
    H.D.CAPTURE.CLAIMS.verify_entered(args.candidate)
    require(canonical['execution']=='fastboot-boot-ram-bundle'
            and canonical['manifest_sha256']==sha(raw['manifest'])
            and canonical['boot_image_sha256']==hashes['boot_bundle'],'wrong consumed rescue family or manifest')
    manifest=H.unique([line.split('=',1) for line in raw['manifest'].decode('ascii').splitlines()])
    for name in ('kernel','dtb','initramfs'):require(manifest[name+'_sha256']==hashes[name],'rescue target mismatch')
    h02,h03=data['h02'],data['h03'];identity=h02['identity'];receipt=data['capture_receipt'];ready=data['readiness']
    require(h02['status']==h03['status']=='PASS' and h02['h02_qualified'] is True
            and h03['h03_qualified'] is True and h02['release_qualified'] is False and h03['release_qualified'] is False
            and h03['candidate']==args.candidate and h02['canonical_record']==canonical
            and h03['identity']==identity==dict(serial=canonical['serial'],bundle=canonical['target_bundle'],
                release=manifest['target_release'],boot_id=identity['boot_id']), 'incoherent historical rescue identity')
    require(h02['artifact_hashes']==h03['artifact_hashes']==dict(initramfs=hashes['initramfs'],boot_image=hashes['boot_bundle'])
            and h03['h02_sha256']==sha(raw['h02']),'unpaired H02/H03 artifacts')
    historical_roles=('manifest','capture_receipt','first_ssh','readiness','execution',
                      'capture_events','ssh_attempts','smoke','boot_log')
    require(h02['evidence']=={inputs['files'][name]['path']:sha(raw[name]) for name in historical_roles},
            'original H02 raw dependencies changed')
    require(data['first_ssh']['status']=='PASS' and data['first_ssh']['seconds']==ready['seconds']
            and str(Path(data['first_ssh']['output'])/'result.json')==inputs['files']['readiness']['path'],'wrong first authenticated readiness')
    versions=observation_compatibility(h02,h03,receipt,ready)
    events=[H.decode(line) for line in raw['capture_events'].splitlines()]
    attempts=[H.decode(line) for line in raw['ssh_attempts'].splitlines()]
    startup=H.validate(canonical,identity,data['execution'],receipt,sha(raw['capture_receipt']),events,attempts,
                       data['smoke'],ready,300,observed_producers=versions)
    capture_closed(receipt,data['capture_result'],events)
    for name in ('device','last_fastboot'):
        device=data['execution'][name]
        require(device['product']==canonical['product'] and device['current-slot']==canonical['expected_slot']
                and device['battery-soc-ok']=='yes' and 8400<=int(device['battery-voltage'])<=9000,'original boot/power gate')
    log=raw['boot_log']
    require(log.count(b'CLAIM_CONSUMED:')==log.count(b'FASTBOOT_ACCEPTED:')==1
            and len(re.findall(rb'^Booting\s+OKAY',log,re.M))==1
            and b'FAILED' not in log and b'AMBIGUOUS' not in log,'ambiguous original boot')
    expected,archive=H.sealed_runtime(args.target_archive,manifest)
    boot=H.read_bytes(args.boot_image,256*H.LIMIT)
    require(sha(boot)==hashes['boot_bundle'] and expected==h02['expected_runtime']
            and sha(H.current_script(identity,expected).encode())==h02['probe_sha256'],'observed runtime script mismatch')
    require(set(h02['current'])==set(H.CURRENT_KEYS) and 0<H.number(h02['seconds'])<=300,'H02 runtime framing or deadline')
    require(H.validate_current(h02['current'],identity,int(manifest['rollback_timeout']))==h02['current_validation'],
            'changed watchdog observation')
    require(H.D.validate_readiness(h02['current_readiness'],identity,canonical['execution'])['marker_boot_bound'],
            'historical readiness is not boot bound')
    script,firmware=G.firmware_probe(args.target_archive,identity,manifest)
    require(firmware==h03['firmware'] and sha(script.encode())==h03['runtime_probe_sha256']
            and sha(G.sample_script().encode())==h03['probe_sha256'],'observed firmware or sample script mismatch')
    for key in ('current_before','current_after'):
        require(set(h03[key])==set(H.CURRENT_KEYS),'H03 runtime framing')
        H.validate_current(h03[key],identity,int(manifest['rollback_timeout']))
    expected_files={'h02.log':'h02_log','samples.jsonl':'samples'}|{name:name for name in ROLES-FIXED}
    require(set(h03['evidence'])==set(expected_files)
            and all(h03['evidence'][name]==sha(raw[role]) for name,role in expected_files.items()),'incomplete H03 raw evidence')
    rows=[H.decode(line) for line in raw['samples'].splitlines()]
    outcome=charging_rows(h03,rows,raw,identity,int(manifest['rollback_timeout']))
    require(H.read_bytes(args.target_archive,256*H.LIMIT)==archive and H.read_bytes(args.boot_image,256*H.LIMIT)==boot,
            'rescue artifacts changed')
    require(all(pinned(Path(item['path']),item['sha256'])==raw[name] for name,item in inputs['files'].items())
            and pinned(args.inputs,args.inputs_sha256)==input_raw,'rescue evidence changed')
    return dict(status='PASS',candidate=args.candidate,identity=identity,artifact_hashes=hashes,
                h01_qualified=True,h02_qualified=True,h03_qualified=True,original_source=h03['source'],
                startup_seconds=startup['startup_seconds'],observed_seconds=h03['duration_seconds'],
                observation=outcome,evidence_sha256={name:sha(value) for name,value in raw.items()},
                scope='Completed radio-inactive rescue, original boot and source preserved; no current phone observation')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=('H01','H02','H03'),required=True)
    for name in ('inputs','target-archive','boot-image','output'):parser.add_argument('--'+name,type=Path,required=True)
    for name in ('inputs-sha256','candidate','artifact-hashes'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();require(args.output.is_absolute() and not args.output.resolve().is_relative_to(R),'private output required')
    os.umask(0o077);args.output.mkdir(mode=0o700);start=time.monotonic();A=H.D.CAPTURE.ACCEPTANCE
    report=dict(status='FAIL',release_qualified=False,h01_qualified=False,h02_qualified=False,h03_qualified=False,
                evidence_reused=True,source=A.source_identity(),
                inputs_sha256=args.inputs_sha256,runner_sha256=sha(Path(__file__).read_bytes()))
    try:report.update(evaluate(args))
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:report['error']=str(error)
    if report['source']!=A.source_identity():
        report.update(status='FAIL',h01_qualified=False,h02_qualified=False,h03_qualified=False,error='source changed')
    report['duration_seconds']=time.monotonic()-start
    (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report.get(key) for key in ('status','duration_seconds','error')}))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
