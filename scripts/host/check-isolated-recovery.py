#!/usr/bin/env python3
"""Offline R01 evidence replay. This module never connects to or boots a phone.

The physical recovery deadline, complete receiver lifetime and subsequent
ordinary restoration are separate intervals. Component flags alone are never
accepted in place of the pinned commands, journal and capture events.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat

R=Path(__file__).resolve().parents[2]


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,R/'scripts/host'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


CAP=load('r01_replay_capture','capture-isolated-recovery.py')
OBS=load('r01_replay_negative','isolated-recovery-observation.py')
SMOKE=load('r01_replay_ordinary','ordinary-boot-smoke.py')
ROOT=SMOKE.B.ROOT
need=OBS.need
PRIMARY='headless-server-selector-v8'
FALLBACK='persistent-native-root-v11'
PHASES=('preflight','arm','transition','capture','execute','observe','close_capture',
        'rescue_guard','restore','ordinary_verify')
HASH=re.compile('[0-9a-f]{64}')
JOB_START='7d4958e842da4a758f6c1cdc7b36dcc5'
JOB_SUCCESS='39f53479d3a045ac8e11786248231fbf'
JOB_FAILED='be02cf6855d2428ba40df7e9d022f03d'


def number(value):
    need(type(value) in (int,float) and math.isfinite(value) and value>=0,'invalid monotonic time')
    return value


def digest(raw):return hashlib.sha256(raw).hexdigest()


def pinned(path,pin=None,limit=10*1024**2):
    path=Path(path)
    need(path.is_absolute() and path.resolve()==path,'canonical evidence path required')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    def signature(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,
                             s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    with os.fdopen(fd,'rb') as file:
        before=os.fstat(file.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=limit,
             'unsafe or oversized evidence')
        raw=file.read(limit+1);after=os.fstat(file.fileno())
    need(len(raw)<=limit and signature(before)==signature(after)==signature(path.lstat()),
         'evidence changed during read')
    if pin is not None:need(type(pin) is str and HASH.fullmatch(pin) and digest(raw)==pin,'evidence hash mismatch')
    return raw


def read(path,pin=None):
    return json.loads(pinned(path,pin),object_pairs_hook=OBS.unique)


def canonical(profile):
    return OBS.unique(line.split('=',1) for line in CAP.CLAIMS.expected_record(profile).decode().splitlines())


def journal(raw,identity):
    """Require complete PID 1 job records, with no ignored trailing bytes."""
    need(0<len(raw)<=2*1024**2 and raw.endswith(b'\n'),'incomplete rollback journal')
    lines=raw.splitlines();need(all(0<len(line)<=65536 for line in lines),'journal framing')
    rows=[OBS.decode(line) for line in lines];header=rows.pop(0)
    need(header==dict(event='stream-started',format='rog5-r01-journal-stream-v1',**identity,
                     uptime_seconds=header.get('uptime_seconds'),maximum_uptime_seconds=915)
         and type(header['uptime_seconds']) is int and 0<header['uptime_seconds']<900,'journal stream identity')
    start=None;done=None;previous=0
    for row in rows:
        need(row.get('_BOOT_ID')==identity['boot_id'].replace('-',''),'different journal boot')
        stamp=row.get('__MONOTONIC_TIMESTAMP')
        need(type(stamp) is str and re.fullmatch('[1-9][0-9]{0,15}',stamp),'journal monotonic timestamp')
        stamp=int(stamp);need(previous<=stamp<=915000000,'journal ordering/deadline');previous=stamp
        unit=row.get('UNIT',row.get('_SYSTEMD_UNIT'))
        need(unit in (OBS.UNITS['health'],OBS.UNITS['rollback']),'unexpected journal unit')
        if unit!=OBS.UNITS['rollback']:continue
        need(row.get('MESSAGE_ID')!=JOB_FAILED,'rollback job failed')
        if row.get('MESSAGE_ID') not in (JOB_START,JOB_SUCCESS):continue
        job=row.get('JOB_ID')
        need(row.get('_PID')=='1' and row.get('_UID')=='0' and row.get('UNIT')==OBS.UNITS['rollback']
             and type(job) is str and re.fullmatch('[1-9][0-9]{0,11}',job),'untrusted rollback job record')
        if row['MESSAGE_ID']==JOB_START:
            need(start is None and 900000000<=stamp<=905000000,'early, late or repeated rollback')
            start=(job,stamp)
        else:
            need(start is not None and done is None and job==start[0]
                 and start[1]<=stamp<=start[1]+10000000,'unmatched rollback completion')
            done=(job,stamp)
    need(start is not None and done is not None,'autonomous callback not observed')
    return dict(job_id=start[0],started_uptime_seconds=start[1]/1000000,
                completed_uptime_seconds=done[1]/1000000)


def timeline(receipt,events,entry,returned,negative,rescue,samples,callback):
    """Replay the two-boot capture and independently bound physical return."""
    entry=number(entry);returned=number(returned)
    timing=CAP.ACCEPTANCE.load_contract()['defaults']['rescue_capture']
    need(timing==dict(recovery_seconds=300,target_rollback_seconds=900,cleanup_seconds=120,preflight_seconds=60),
         'review changed R01 timing lattice')
    start=number(receipt['started_monotonic']);deadline=number(receipt['deadline_monotonic'])
    need(receipt['timing']==timing and receipt['required_seconds']==1320 and start<entry
         and deadline-start>=1380 and deadline-entry>=1320,'insufficient prestarted full capture')
    need(0<returned-entry<=1200,'physical recovery exceeded deployed rollback plus recovery budget')
    need(negative['boot_id']!=rescue['boot_id'],'rescue reused negative boot')
    times=[number(event['monotonic']) for event in events]
    need(times and times==sorted(times),'capture event ordering')
    prepared=[event for event in events if event['event'] in SMOKE.B.READ.PREPARED]
    need(tuple(event['event'] for event in prepared)==SMOKE.B.READ.PREPARED
         and all(start<=event['monotonic']<entry for event in prepared),'capture was not ready before execution')
    failed={'transport-check-failed','invalid-stage','log-bound-exceeded','premature-target-disconnect',
            'missing-recovery-disconnect','unexpected-post-return-disconnect','missing-source-disconnect',
            'rejected-peer-or-transport','rejected-unbound-client','client-capacity-exceeded'}
    need(not any(event['event'] in failed for event in events),'failed or ambiguous diagnostic channel')
    losses=[event for event in events if event['event']=='recovery-disconnected']
    returns=[event for event in events if event['event']=='recovery-boot-observed']
    need(len(losses)==len(returns)==1,'missing or repeated physical return')
    loss=losses[0];back=returns[0]
    need(loss['source_boot_id']==back['source_boot_id']==negative['boot_id']
         and back['boot_id']==rescue['boot_id'] and back['return_identity']==receipt['return_identity']
         and entry<loss['monotonic']<back['monotonic']<returned,'return identity/order mismatch')
    need(loss['last_stage']['boot_id']==negative['boot_id']
         and (loss['last_stage']['stage'],loss['last_stage']['state'])==('switch-root','PASS'),
         'negative target never handed over to userspace')
    stages=[event for event in events if event['event']=='stage']
    for boot,before,after in ((negative['boot_id'],entry,loss['monotonic']),
                              (rescue['boot_id'],back['monotonic'],deadline+120)):
        group=[event for event in stages if event['stage']['boot_id']==boot]
        need(group and all(before<=event['monotonic']<=after and event['stage']['state']!='FAIL' for event in group)
             and any((event['stage']['stage'],event['stage']['state'])==('switch-root','PASS') for event in group),
             'missing, failed or out-of-order userspace handover')
    need(all(event['stage']['boot_id'] in (negative['boot_id'],rescue['boot_id']) for event in stages),'third boot in capture')
    for event in events:
        if event['event']=='startup-observation':
            boot=event['observation']['boot_id']
            need(boot==(negative['boot_id'] if event['monotonic']<loss['monotonic'] else rescue['boot_id']),
                 'mixed startup observation')
        if event['event']=='transport' and event['monotonic']>=back['monotonic']:
            need(event['mode']=='target','post-return transport loss')
        if event['event'] in ('usb-discovery-interrupted','recovery-discovery-interrupted'):
            need(event.get('phase')=='usb-discovery' and event.get('errno') in (2,19)
                 and event.get('operation') in CAP.USB_READ_OPERATIONS and event.get('observed_mode')=='absent',
                 'unproven discovery interruption')
            if event['event']=='usb-discovery-interrupted':
                need(event.get('target_seen') is False and event.get('last_stage') is None
                     and event.get('last_startup') is None,'post-target startup interruption')
            else:
                # The producer emits the bounded read interruption immediately
                # before reporting the positively observed absence to Receiver.
                need(loss['monotonic']-.2<=event['monotonic']<back['monotonic']
                     and event.get('target_seen') is True
                     and event.get('last_stage',{}).get('boot_id')==negative['boot_id'],
                     'discovery interruption outside recovery')
    ended=[event for event in events if event['event']=='capture-ended']
    cleanup=[event for event in events if event['event']=='host-cleanup']
    need(len(ended)==1 and ended[0]['status']=='NOT RUN' and ended[0]['return_seen'] is True
         and ended[0]['initial_boot']==negative['boot_id'] and deadline<=ended[0]['monotonic']<=deadline+40,
         'receiver failed, ended early or did not complete')
    need([event['item'] for event in cleanup]==['route','firewall','profile','address']
         and all(event['status']=='PASS' and ended[0]['monotonic']<event['monotonic']<=deadline+120 for event in cleanup),
         'owned host cleanup failed or incomplete')
    need(samples and samples[0]['uptime']<=300 and samples[-1]['uptime']>=860,'negative monitoring coverage')
    lower=entry;upper=entry+300;previous=entry
    for sample in samples:
        begin=number(sample['started_monotonic']);end=number(sample['finished_monotonic']);uptime=number(sample['uptime'])
        need(previous<=begin<=end<loss['monotonic'] and end-begin<=20,'overlapping, late or unbounded negative sample')
        if previous!=entry:need(begin-previous<=15,'negative observation gap')
        lower=max(lower,begin-uptime-1);upper=min(upper,end-uptime+1);previous=end
    need(lower<=upper,'host and target clocks do not describe one boot')
    need(lower+callback['completed_uptime_seconds']-1<=loss['monotonic']<=upper+920,
         'disconnect does not follow autonomous callback')
    return dict(physical_recovery_seconds=returned-entry,capture_seconds=ended[0]['monotonic']-start,
                boot_monotonic_bounds=[lower,upper])


def command(directory,name,*,startup_pending=False):
    need(re.fullmatch('[a-z0-9-]+',name),'invalid command evidence name')
    report=read(directory/(name+'-command.json'))
    stdout=pinned(directory/(name+'.stdout'),report['stdout_sha256'])
    stderr=pinned(directory/(name+'.stderr'),report['stderr_sha256'])
    pinned(directory/(name+'.script'),report['script_sha256'])
    need(report['timeout'] is False and type(report['returncode']) is int,'failed command: '+name)
    number(report['retained_monotonic'])
    if startup_pending:
        need(report['returncode']==255 and not stdout and re.fullmatch(rb'ssh: connect to host 10\.77\.0\.2 port 22: Connection refused\r?\n',stderr),
             'ambiguous startup transport failure')
    else:need(report['returncode']==0 and not stderr,'failed authenticated command: '+name)
    return stdout


def numbered(directory,prefix):
    names=[path.name.removesuffix('-command.json') for path in directory.glob(prefix+'-*-command.json')]
    need(names and all(re.fullmatch(re.escape(prefix)+r'-[1-9][0-9]*',name) for name in names),
         'missing/malformed numbered command sequence')
    names.sort(key=lambda name:int(name.rsplit('-',1)[1]))
    need(names==[prefix+'-'+str(index) for index in range(1,len(names)+1)],'discarded or repeated command')
    return names


def ordinary_health(raw):
    value=OBS.decode(raw);unit=value['unit']
    need(unit['returncode']==0 and not unit['stderr'],'failed ordinary health read')
    fields=OBS.unique(line.split('=',1) for line in unit['stdout'].splitlines())
    return dict(identity=value['identity'],uptime=value['uptime'],unit=fields,
                files={role:value['files'][OBS.MARKERS[role]] for role in ('descriptor','healthy','ssh')})


def check_controller(admission_path,admission_sha256,directory):
    """Validate retained raw results while the sole driver's qualify phase runs."""
    directory=Path(directory);admission_path=Path(admission_path)
    c=read(admission_path,admission_sha256);profile=c['candidate'];record=canonical(profile);primary=canonical(PRIMARY)
    need(c['format']=='rog5-r01-live-admission-v1' and record.get('qualification')=='isolated-failure-r01'
         and record['execution']=='fastboot-boot-ram-bundle','not the admitted isolated failure candidate')
    need(c['source']==CAP.ACCEPTANCE.source_identity() and c['source']['clean'],'changed/unfrozen R01 source')
    need(c['checker']['path']==str(Path(__file__).resolve())
         and c['checker']['sha256']==digest(pinned(Path(__file__).resolve())),'changed R01 consumer')
    for name,pin in c['private_sources'].items():
        need(Path(name).name==name and name.endswith('.py'),'private producer name')
        pinned(admission_path.parent/name,pin)
    checked=read(c['controller_checks']['path'],c['controller_checks']['sha256'])
    need(checked['status']=='PASS' and checked.get('complete_driver_bindings') is True
         and checked['private_sources']==c['private_sources'],
         'untested complete controller bindings')
    need(not list(directory.glob('*-failure.json')) and not list(directory.glob('*-timeout.json')),
         'failed or ambiguous controller phase cannot qualify')
    context=read(directory/'context.json')['context'];results={};previous=0
    for index,phase in enumerate(PHASES):
        intent=read(directory/(phase+'-entered.json'));result=read(directory/(phase+'-result.json'))
        need(intent['phase']==phase and intent['prior']==list(PHASES[:index])
             and number(intent['monotonic'])>=previous and result['status'] in ('PASS','COMPONENT_PASS'),
             'missing, repeated or out-of-order controller phase')
        previous=intent['monotonic'];results[phase]=result
    expected={'source-deployed','source-ready','source-root','source-state','source-installed','arm-state',
              'source-fastboot','execute','negative-root','return-guard','rescue-fresh-ready',
              'rescue-fresh-guard','restore-fresh-guard','restore-directory','restore-helper','restore-state',
              'restore-cleanup','ordinary-source-guard','ordinary-reboot','ordinary-root',
              'ordinary-state','ordinary-installed'}
    for name in expected:command(directory,name)
    sequences={prefix:numbered(directory,prefix) for prefix in
               ('negative-ready','return-ready','ordinary-ready','negative-health-wait','negative-sample','ordinary-health')}
    for prefix,names in sequences.items():
        for index,name in enumerate(names):
            command(directory,name,startup_pending=prefix.endswith('-ready') and index<len(names)-1)
        expected.update(names)
    need({path.name.removesuffix('-command.json') for path in directory.glob('*-command.json')}==expected,
         'unexpected or missing controller command')
    negative=results['observe']['negative_identity'];rescue=results['observe']['identity']
    source=c['source_identity'];ordinary=results['ordinary_verify']['identity']
    need(context['source']==source and source['bundle']==ordinary['bundle']==PRIMARY
         and source['release']==ordinary['release']==negative['release']
         and negative['bundle']==profile and rescue['bundle']==FALLBACK
         and rescue['release']=='7.1.4-g359318de534f','mixed release/return identities')
    boots=[identity['boot_id'] for identity in (source,negative,rescue,ordinary)]
    need(len(set(boots))==4 and all(CAP.STAGES.BOOT_ID.fullmatch(boot) for boot in boots),'fresh boot identities missing')
    installed={key:primary[key] for key in ('trial_id','fallback_bundle','fallback_manifest_sha256')}
    installed.update(primary_bundle=PRIMARY,primary_manifest_sha256=primary['manifest_sha256'])
    def state_pin(state):
        rows=dict(format='rog5-persistent-wifi-trial-v1',**installed,state=state)
        # The accepted record order is part of the durable helper protocol.
        return digest(''.join(key+'='+rows[key]+'\n' for key in ('format','trial_id','primary_bundle',
          'primary_manifest_sha256','fallback_bundle','fallback_manifest_sha256','state')).encode())
    need(context['pending_sha256']==state_pin('pending') and context['healthy_sha256']==state_pin('healthy'),
         'different installed fallback state')
    ROOT.D.validate_snapshot(OBS.decode(command(directory,'source-deployed')),source,ROOT.D.expected_files(PRIMARY))
    ROOT.validate(OBS.decode(command(directory,'source-root')),source)
    ROOT.D.validate_readiness(ROOT.D.parse_readiness(command(directory,'source-ready')),source,primary['execution'])
    source_state=OBS.decode(command(directory,'source-state'))
    need(source_state['status']=='PASS' and source_state['identity']==source
         and source_state['healthy_sha256']==context['healthy_sha256']
         and command(directory,'source-installed')==b'PASS-installed\n','source installed baseline differs')
    armed=OBS.decode(command(directory,'arm-state'))
    need(armed['identity']==source and armed['before_sha256']==context['healthy_sha256']
         and armed['after_sha256']==context['pending_sha256'],'arming did not preserve exact prior state')
    need(command(directory,'execute').splitlines()==[b'CLAIM_CONSUMED',b'FASTBOOT_ACCEPTED'],
         'experimental command not acknowledged once')
    need(results['execute']['canonical_record']==record,'different executed image claim')
    transition=[OBS.decode(line) for line in command(directory,'source-fastboot').splitlines()]
    need(len(transition)==2 and transition[0]['event']=='transition-ready'
         and transition[0]['pending_sha256']==context['pending_sha256']
         and transition[1]['event']=='reboot-request-returned' and transition[1]['returncode']==0,
         'source transition was failed or ambiguous')
    samples=[]
    for index,name in enumerate(sequences['negative-health-wait']):
        actual=OBS.decode(command(directory,name))
        if index<len(sequences['negative-health-wait'])-1:
            need(OBS.pending(actual,negative,c['negative_trial_id'],installed,c['negative_sealed']),
                 'discarded completed negative health observation')
        else:OBS.negative(actual,negative,c['negative_trial_id'],installed,c['negative_sealed'])
    for index,sample in enumerate(results['observe']['samples'],1):
        name='negative-sample-'+str(index);need(sample['command']==name,'discarded or reordered negative sample')
        actual=OBS.decode(command(directory,name))
        proof=OBS.negative(actual,negative,c['negative_trial_id'],installed,c['negative_sealed'])
        need(sample['proof']==proof,'negative sample result mismatch')
        samples.append(dict(started_monotonic=sample['started_monotonic'],finished_monotonic=sample['finished_monotonic'],uptime=actual['uptime']))
    ROOT.validate(OBS.decode(command(directory,'negative-root')),negative)
    for key,identity,family in (('negative_ready',negative,'fastboot-boot-ram-bundle'),
                                ('return_ready',rescue,'fastboot-boot-fallback-only')):
        value=results['observe'][key]
        prefix='negative-ready' if key=='negative_ready' else 'return-ready'
        need(value['command']==sequences[prefix][-1],'unbound successful readiness command')
        actual=ROOT.D.parse_readiness(command(directory,value['command']))
        need(actual==value['actual'],'readiness flags differ from authenticated raw output')
        ROOT.D.validate_readiness(actual,identity,family)
    stream=read(directory/'rollback-stream-result.json')
    callback=journal(pinned(directory/'rollback-stream.stdout',stream['stdout_sha256']),negative)
    pinned(directory/'rollback-stream.stderr',stream['stderr_sha256'])
    need(type(stream['returncode']) is int and stream['returncode'] in (0,255), 'journal observer failure')
    started=read(directory/'rollback-stream-started.json')
    pinned(directory/'rollback-stream.script',started['script_sha256'])
    need(started['identity']==negative and samples[0]['finished_monotonic']<=started['monotonic']
         <=samples[0]['finished_monotonic']+15,'rollback stream not started with the negative observation')
    receipt=read(directory/'capture/receipt.json')
    need(receipt['canonical_record']==record and receipt['source']==c['source']
         and receipt['receiver_sha256']==digest(pinned(R/'scripts/host/capture-isolated-recovery.py'))
         and receipt['framework_sha256']==digest(pinned(R/'scripts/host/headless-stage-receiver.py')),
         'capture producer or candidate changed')
    returning=CAP.return_manifest(Path(c['fallback_manifest']),record)
    need(receipt['return_identity']==returning,'different signed fallback')
    raw=pinned(directory/'capture/events.jsonl',results['close_capture']['events_sha256'])
    need(raw.endswith(b'\n'),'partial final capture')
    events=[OBS.decode(line) for line in raw.splitlines()]
    evidence=timeline(receipt,events,results['execute']['entry_monotonic'],
        results['observe']['physical_return_monotonic'],negative,rescue,samples,callback)
    returned=results['observe']['physical_return_monotonic']
    retained=number(read(directory/'return-guard-command.json')['retained_monotonic'])
    need(retained<=returned<=retained+5,'unbound physical return timestamp')
    cleanup=max(event['monotonic'] for event in events if event['event']=='host-cleanup')
    need(read(directory/'rescue_guard-entered.json')['monotonic']>=cleanup,
         'restoration guard began before full capture cleanup')
    need(results['close_capture']['receiver_returncode']==0 and results['close_capture']['full_lifetime'] is True,
         'receiver not fully closed')
    for name in ('return-guard','rescue-fresh-guard','restore-fresh-guard','ordinary-source-guard'):
        need(command(directory,name)==b'PASS-V11-guard\n','fallback or installed byte guard failed')
    restored=OBS.unique(line.split('=',1) for line in command(directory,'restore-state').decode().splitlines())
    need(restored==dict(format='rog5-r01-selection-restoration-v1',entered='true',boot_id=rescue['boot_id'],
         before_sha256=context['pending_sha256'],completed='true',after_sha256=context['healthy_sha256'],
         selection_eligibility_restored='true',release_qualified='false'),'unproven prior selection restoration')
    need(command(directory,'restore-cleanup')==b'PASS-helper-cleaned\n'
         and command(directory,'ordinary-state')==b'PASS-ordinary-state\n'
         and command(directory,'ordinary-installed')==b'PASS-installed\n','restoration cleanup or current health failed')
    smoke=read(directory/'ordinary-smoke.json');baseline=read(c['ordinary_baseline']['path'],c['ordinary_baseline']['sha256'])
    need({key:smoke['context']['identity'][key] for key in ordinary}==ordinary
         and smoke['context']['source_boot_id']==rescue['boot_id'] and smoke['context']['source']==c['source'],
         'different ordinary restoration boot')
    need(smoke['context']['entry_monotonic']>=read(directory/'ordinary_verify-entered.json')['monotonic']
         >=cleanup,'ordinary restoration overlapped physical recovery capture')
    need(OBS.decode(command(directory,'ordinary-root'))==smoke['context']['root']
         and ROOT.D.parse_readiness(command(directory,sequences['ordinary-ready'][-1]))==smoke['context']['readiness']
         and ordinary_health(command(directory,sequences['ordinary-health'][-1]))==smoke['context']['health'],
         'ordinary health/root/readiness flags differ from raw authenticated output')
    for name in sequences['ordinary-health'][:-1]:
        pending=ordinary_health(command(directory,name))
        need(pending['identity']==smoke['context']['identity'] and pending['unit']['Result']=='success'
             and pending['unit']['ExecMainStatus']=='0'
             and all(item['status'] in ('present','absent') for item in pending['files'].values()),
             'discarded failed ordinary health observation')
    original=pinned(directory/'ordinary-capture/events.jsonl')
    need(original.endswith(b'\n') and [OBS.decode(line) for line in original.splitlines()]==smoke['closure']['events'],
         'ordinary closure differs from original capture')
    need(SMOKE.closed(baseline,smoke['context'],smoke['closure'])==smoke['proof'],'ordinary closure replay differs')
    return dict(status='COMPONENT_PASS',r01_qualified=True,release_qualified=False,candidate=PRIMARY,
                negative_candidate=profile,source=c['source'],admission_sha256=admission_sha256,
                identity=ordinary,negative_identity=negative,rescue_identity=rescue,**evidence)


if __name__=='__main__':
    raise SystemExit('Offline library; completed R01 input-envelope/dispatcher integration is required')
