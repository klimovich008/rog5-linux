#!/usr/bin/env python3
"""H03 supervised firmware-Full observation. Read-only; never boot or admit."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def load(name, filename):
    spec=importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


STARTUP=load('charging_startup', 'check-rescue-startup.py')
REGULATION=load('charging_math', 'h03-regulation.py')
D=STARTUP.D
WINDOW=600
CADENCE=10
COUNT=WINDOW//CADENCE+1
DEADLINE=660
READ_BOUND=2
ATTRIBUTES={
    'capacity':'qcom-battmgr-bat/capacity', 'current_ua':'qcom-battmgr-bat/current_now',
    'counter_uah':'qcom-battmgr-bat/charge_counter', 'voltage_uv':'qcom-battmgr-bat/voltage_now',
    'voltage_max_uv':'qcom-battmgr-bat/voltage_max', 'temp_dc':'qcom-battmgr-bat/temp',
    'usb_online':'qcom-battmgr-usb/online', 'usb_voltage_uv':'qcom-battmgr-usb/voltage_now',
    'usb_current_ua':'qcom-battmgr-usb/current_now', 'input_limit_ua':'qcom-battmgr-usb/input_current_limit',
    'status':'qcom-battmgr-bat/status', 'health':'qcom-battmgr-bat/health',
}
FIELD_NAMES=('boot_before','kernel','cmdline','wifi','uptime_before',*ATTRIBUTES,
             'data_role','power_role','uptime_after','boot_after')
require=STARTUP.require


class TelemetryError(ValueError):
    """A failed read still carries bounded private evidence, never a retry."""
    def __init__(self, reason, stdout=b'', stderr=b''):
        super().__init__(reason)
        self.stdout=(stdout or b'')[:32768]
        self.stderr=(stderr or b'')[:8192]


def sample_script():
    """Fixed sysfs reads; present/absent/error is retained, never forward-filled."""
    script='''set -eu
export LC_ALL=C PATH=/usr/sbin:/usr/bin:/sbin:/bin
emit() { printf '%s\\0%s\\0%s\\0' "$1" "$2" "$3"; }
field() {
 if [ ! -e "$2" ]; then emit "$1" absent ''; return; fi
 if value=$(timeout -k 1 2 head -c 512 "$2"); then
  emit "$1" present "$value"
 else emit "$1" error ''; fi
}
field boot_before /proc/sys/kernel/random/boot_id
emit kernel present "$(uname -r)"
emit cmdline present "$(head -c 4096 /proc/cmdline)"
wifi=inactive
for phy in /sys/class/ieee80211/*; do
 if [ -e "$phy" ] || [ -L "$phy" ]; then wifi=active; fi
done
[ ! -d /sys/module/ath11k ] || wifi=active
emit wifi present "$wifi"
emit uptime_before present "$(cut -d ' ' -f 1 /proc/uptime)"
'''
    for name, path in ATTRIBUTES.items():
        script+='field '+name+' /sys/class/power_supply/'+path+'\n'
    return script+'''field data_role /sys/class/typec/port0/data_role
field power_role /sys/class/typec/port0/power_role
emit uptime_after present "$(cut -d ' ' -f 1 /proc/uptime)"
field boot_after /proc/sys/kernel/random/boot_id
'''


def parse_frame(raw, identity, rollback):
    require(type(raw) is bytes and len(raw)<=32768, 'sample output bound')
    fields=raw.decode('ascii').split('\0')
    require(len(fields)==len(FIELD_NAMES)*3+1 and fields[-1]=='', 'sample framing')
    values={}
    for index, name in enumerate(FIELD_NAMES):
        key,state,value=fields[index*3:index*3+3]
        require(key==name and state=='present', 'missing/error/duplicate field: '+name)
        values[name]=value
    require(values['boot_before']==values['boot_after']==identity['boot_id']
            and values['kernel']==identity['release'] and values['wifi']=='inactive', 'boot/kernel/radio changed')
    for key,want in (('rog5.bundle',identity['bundle']),('rog5.recovery_timeout',str(rollback))):
        require([v for v in values['cmdline'].split() if v.startswith(key+'=')]==[key+'='+want], 'ambiguous sample cmdline')
    for field, want, allowed in (('data_role','[device]',{'host','device','[host]','[device]'}),
                                  ('power_role','[sink]',{'source','sink','[source]','[sink]'})):
        tokens=values[field].split()
        require(tokens.count(want)==1 and len(tokens)==len(set(tokens))
                and set(tokens)<=allowed and sum(t.startswith('[') for t in tokens)==1, 'USB role changed')
    row={'status':values['status'],'health':values['health'],'role':'device/sink','elapsed_s':0}
    for name in ATTRIBUTES:
        if name in ('status','health'): continue
        require(re.fullmatch(r'-?(?:0|[1-9][0-9]*)',values[name]) is not None, 'noninteger telemetry: '+name)
        row[name]=int(values[name])
    before,after=(float(values[name]) for name in ('uptime_before','uptime_after'))
    require(math.isfinite(before) and math.isfinite(after) and 0<=before<=after<=before+READ_BOUND, 'stale/unbounded target reading')
    row.update(target_uptime_before=before,target_uptime_after=after)
    REGULATION.validate_full_sample(row)
    return row


def collect(identity, key, known_hosts, script):
    D.host_gate(identity)  # Exact physical topology/addressing before credentials.
    D.credential(key,True); D.credential(known_hosts,False)
    try:
        result=subprocess.run([*D.ssh_command(key,known_hosts),'timeout -k 1 6 sh -s'],
                              input=script.encode(),capture_output=True,timeout=8)
    except subprocess.TimeoutExpired as error:
        raise TelemetryError('telemetry transport timeout',error.stdout,error.stderr) from error
    try:
        D.host_gate(identity)
        require(result.returncode==0, 'authenticated telemetry transport failed')
        require(len(result.stdout)<=32768 and len(result.stderr)<=8192, 'telemetry output bound')
        require(not result.stderr, 'telemetry read error; see private sample stderr')
    except (ValueError,OSError) as error:
        raise TelemetryError(str(error),result.stdout,result.stderr) from error
    return result.stdout


def observe(identity, rollback, fetch, output, deadline, *, clock=time.monotonic, sleep=time.sleep):
    start=clock()
    require(deadline-start>=WINDOW+2*READ_BOUND, 'insufficient observation deadline')
    samples=[]; anchor=None
    for index in range(COUNT):
        if anchor is not None:
            delay=anchor+index*CADENCE-clock()
            require(delay>=-READ_BOUND, 'sample schedule missed')
            if delay>0: sleep(delay)
        require(clock()+8<=deadline, 'observation deadline')
        begin=clock()
        try:
            raw=fetch()
        except TelemetryError as error:
            for suffix,payload in (('raw',error.stdout),('stderr',error.stderr)):
                with (output/f'sample-{index:02d}.{suffix}').open('xb') as stream:
                    stream.write(payload)
            raise
        finish=clock()
        # Retain even a malformed or unsafe reply. Never retry its measurement.
        with (output/f'sample-{index:02d}.raw').open('xb') as stream: stream.write(raw)
        row=parse_frame(raw,identity,rollback)
        require(0<=finish-begin<=READ_BOUND, 'sample read exceeded freshness bound')
        row.update(elapsed_s=finish-start,read_seconds=finish-begin)
        if samples:
            host_delta=row['elapsed_s']-samples[-1]['elapsed_s']
            target_delta=row['target_uptime_after']-samples[-1]['target_uptime_after']
            require(8<=host_delta<=12 and target_delta>0 and abs(target_delta-host_delta)<=READ_BOUND, 'stale or missing sample')
        else: anchor=finish
        samples.append(row)
        with (output/'samples.jsonl').open('a') as stream: stream.write(json.dumps(row)+'\n')
    REGULATION.evaluate_full(samples)
    return samples


def firmware_probe(archive, identity, manifest):
    expected,_=STARTUP.sealed_runtime(archive,manifest)
    composition=D.CAPTURE.load('charging_composition','scripts/host/check-rescue-root-composition.py')
    import gzip
    members=composition.SEALED.ARCHIVE.entries(gzip.decompress(STARTUP.read_bytes(archive,256*STARTUP.LIMIT)))
    builder=(D.REPO/'scripts/device/build-persistent-root-initramfs.sh').read_text()
    hashes=re.findall(r'\[ "\$firmware_tree_sha" = \\\n\s*([0-9a-f]{64}) \]',builder)
    loader=members['sbin/rog5-load-persistent-power-usb'][1].decode()
    counts=re.findall(r'find "\$firmware_runtime"[^\n]+\)" -eq ([0-9]+) \]',loader)
    require(len(hashes)==len(counts)==1, 'ambiguous firmware contract')
    firmware=composition.firmware_composition(members,hashes[0],int(counts[0]))
    for row in firmware['files']:
        expected['/run/rog5-charge-firmware/'+row['name']]=dict(row,mode='644')
    script=STARTUP.current_script(identity,expected)
    script='set -eu\ntest "$(cat /sys/module/firmware_class/parameters/path)" = /run/rog5-charge-firmware\n'+script
    return script,firmware


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('cycle','execution-record','manifest','archive','boot-image','identity-file','known-hosts','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--profile',required=True)
    parser.add_argument('--expected-candidate',required=True)
    args=parser.parse_args()
    require(args.output.is_absolute() and not args.output.resolve().is_relative_to(D.REPO)
            and not args.output.exists(), 'new private output required')
    os.umask(0o077);args.output.mkdir(mode=0o700)
    source=D.CAPTURE.ACCEPTANCE.source_identity();started=time.monotonic();deadline=started+DEADLINE
    result=dict(status='FAIL',h03_qualified=False,release_qualified=False,source=source,
                candidate=args.expected_candidate,branch='firmware-full-v1',samples=0,
                runner_sha256=STARTUP.digest(__file__),criteria_sha256=STARTUP.digest(Path(__file__).with_name('h03-regulation.py')))
    try:
        required=(args.cycle,args.execution_record,args.manifest,args.archive,args.boot_image,args.identity_file,args.known_hosts)
        if any(not p.exists() for p in required):
            result['status']='BLOCKED';raise ValueError('missing H02 inputs; no collection attempted')
        # Reuse the complete H02 replay/current check, not a supplied PASS boolean.
        command=[sys.executable,'-B',str(Path(__file__).with_name('check-rescue-startup.py')),'--qualify-current']
        for name in ('cycle','execution_record','profile','manifest','archive','boot_image','identity_file','known_hosts','expected_candidate'):
            command+=['--'+name.replace('_','-'),str(getattr(args,name))]
        command+=['--output',str(args.output/'h02')]
        with (args.output/'h02.log').open('xb') as log:
            check=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=35)
        require(check.returncode==0,'H02 prerequisite revalidation failed; see h02.log')
        h02_raw=STARTUP.read_bytes(args.output/'h02/result.json');h02=STARTUP.decode(h02_raw)
        require(h02['status']=='PASS' and h02['h02_qualified'] is True
                and h02['canonical_record']['candidate']==args.expected_candidate, 'incomplete H02 qualification')
        identity=h02['identity']; result.update(identity=identity,artifact_hashes=h02['artifact_hashes'],h02_sha256=hashlib.sha256(h02_raw).hexdigest())
        manifest_raw=STARTUP.read_bytes(args.manifest)
        manifest=dict(line.split('=',1) for line in manifest_raw.decode('ascii').splitlines())
        rollback=int(manifest['rollback_timeout'])
        script,firmware=firmware_probe(args.archive,identity,manifest)
        current=STARTUP.collect_current(identity,args.identity_file,args.known_hosts,script)
        result['current_before']=current
        STARTUP.validate_current(current,identity,rollback)
        require(deadline-time.monotonic()>=620,'not enough time for complete observation and final validation')
        sample=sample_script();result.update(firmware=firmware,probe_sha256=hashlib.sha256(sample.encode()).hexdigest(),
                                           runtime_probe_sha256=hashlib.sha256(script.encode()).hexdigest())
        rows=observe(identity,rollback,lambda:collect(identity,args.identity_file,args.known_hosts,sample),args.output,deadline)
        result['samples']=len(rows);result['outcome']=REGULATION.evaluate_full(rows)
        current=STARTUP.collect_current(identity,args.identity_file,args.known_hosts,script)
        result['current_after']=current
        STARTUP.validate_current(current,identity,rollback)
        require(STARTUP.read_bytes(args.manifest)==manifest_raw and STARTUP.read_bytes(args.output/'h02/result.json')==h02_raw,'prerequisite evidence changed')
        require(STARTUP.digest(args.archive)==h02['artifact_hashes']['initramfs']
                and STARTUP.digest(args.boot_image)==h02['artifact_hashes']['boot_image'],'artifact changed')
        require(time.monotonic()<=deadline and source==D.CAPTURE.ACCEPTANCE.source_identity(),'deadline/source drift')
        result.update(status='PASS',h03_qualified=True,scope='same-boot firmware Full maintenance; not programmable limits or sub-full qualification')
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result['reason']=str(error)
    series=args.output/'samples.jsonl'
    result['samples']=len(series.read_text().splitlines()) if series.exists() else 0
    result['raw_replies']=len(list(args.output.glob('sample-*.raw')))
    result['duration_seconds']=time.monotonic()-started
    result['evidence']={p.name:STARTUP.digest(p) for p in args.output.iterdir() if p.is_file()}
    with (args.output/'result.json').open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({key:result[key] for key in ('status','h03_qualified','duration_seconds')}))
    return 0 if result['status']=='PASS' else (77 if result['status']=='BLOCKED' else 1)


if __name__=='__main__':raise SystemExit(main())
