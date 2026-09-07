"""Read-only eligibility for ending a successful ordinary-boot smoke capture.

This is not S01/S05 qualification or a signal/boot API. The coordinator must
first replay the pinned full S01 baseline, bind these observations to its exact
commands/artifacts, verify the owned receiver is live, and retain complete
cleanup evidence. Failure keeps full capture armed; it never permits retry.
"""
import importlib.util
import re
from pathlib import Path

spec=importlib.util.spec_from_file_location('smoke_full_boot',Path(__file__).with_name('check-standalone-boot.py'))
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
require=B.require

def timing():
    contract=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
    t=contract['defaults']['ordinary_smoke']
    require(set(t)=={'startup_seconds','preflight_seconds','close_seconds',
        'decision_seconds','receiver_stop_seconds'} and all(type(v) is int and v>0 for v in t.values()),
        'invalid ordinary smoke timing')
    total=next(row['deadline_seconds'] for row in contract['tests'] if row['id']=='S05')
    require(t['startup_seconds']<=300 and t['decision_seconds']+t['receiver_stop_seconds']<t['close_seconds']
        and 3*(t['startup_seconds']+t['preflight_seconds']+t['close_seconds'])<=total,
        'ordinary smoke exceeds three-boot deadline')
    return t

def record(value):
    require(value.get('status')=='present','missing healthy-state measurement')
    require(all(type(value.get(k)) is int for k in ('uid','gid','mode','nlink'))
        and (value['uid'],value['gid'],value['mode'],value['nlink'])==(0,0,0o444,1),
        'unsafe healthy-state metadata')
    text=value['text']
    require(type(text) is str and 0<len(text)<=4096 and text.endswith('\n'),'record bound/framing')
    rows=[line.split('=',1) for line in text.splitlines()]
    require(len(rows)==4 and all(len(row)==2 for row in rows),'record fields')
    return B.READ.unique(rows)

def health(value,identity):
    require(value['identity']==identity,'different healthy boot')
    require(set(value['files'])=={'descriptor','healthy','ssh'},'healthy observation fields')
    descriptor,healthy,ssh=(record(value['files'][key]) for key in ('descriptor','healthy','ssh'))
    trial=descriptor.get('trial_id')
    require(type(trial) is str and re.fullmatch('[0-9a-f]{64}',trial),'trial identity')
    require(descriptor==dict(format='rog5-persistent-wifi-health-v1',trial_id=trial,
        primary_bundle=identity['bundle'],mode='try-once'),'wrong trial descriptor')
    require(healthy==dict(format='rog5-native-wifi-healthy-v1',boot_id=identity['boot_id'],
        trial_id=trial,result='PASS'),'missing current-boot healthy commit')
    require(set(ssh)=={'format','mode','fingerprint','identity_boot_id'}
        and ssh['format']=='rog5-persistent-ssh-identity-v1' and ssh['mode'] in ('seed','load')
        and re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',ssh['fingerprint'])
        and ssh['identity_boot_id']==identity['boot_id'],'missing current-boot SSH latch')
    unit=value['unit']
    require(set(unit)=={'ActiveState','SubState','Result','ExecMainStatus',
        'ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic'},'unit fields')
    require((unit['ActiveState'],unit['SubState'],unit['Result'],unit['ExecMainStatus'])==
        ('active','exited','success','0'),'healthy unit did not finish successfully')
    times=[]
    for key in ('ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic'):
        require(type(unit[key]) is str and re.fullmatch('[1-9][0-9]{0,15}',unit[key]),'unit timestamp')
        times.append(int(unit[key])/1000000)
    require(type(value['uptime']) is str,'uptime type')
    uptime=B.number(float(value['uptime']))
    require(0<times[0]<=times[1]<=uptime<=timing()['startup_seconds'],'healthy commit absent, late or stale')
    return dict(trial_id=trial,commit_uptime_seconds=times[1],observed_uptime_seconds=uptime)

def eligibility(baseline,context):
    """Predicate only; no evidence fabrication, mutation or shortened S01 PASS."""
    c=context;identity=c['identity'];record=c['record'];source=c['source']
    require(baseline['status']=='PASS' and baseline['s01_qualified'] is True
        and baseline['release_qualified'] is False,'full S01 prerequisite missing')
    require(baseline['candidate']==record['candidate']
        and baseline['artifact_hashes']==c['artifact_hashes'] and c['artifact_hashes']
        and c['artifact_hashes']['boot_bundle']==record['boot_image_sha256'],
        'different baseline release/artifacts')
    require({k:v for k,v in baseline['identity'].items() if k!='boot_id'}==
        {k:v for k,v in identity.items() if k!='boot_id'},'different baseline device')
    require(identity['serial']==record['serial'] and identity['bundle']==record['target_bundle']
        and record['execution']=='fastboot-boot-selector-trial',
        'not an ordinary installed selector release')
    require(source['clean'] is True and re.fullmatch('[0-9a-f]{40}',source['revision'])
        and re.fullmatch('[0-9a-f]{64}',source['worktree_digest']),'unfrozen source')
    old=c['source_boot_id'];boot=identity['boot_id']
    require(B.ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(old)
        and B.ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(boot) and boot!=old,'no distinct ordinary boot')
    begin=B.number(c['entry_monotonic']);observed=B.number(c['observed_monotonic'])
    require(0<observed-begin<=timing()['startup_seconds'],'ordinary-boot deadline')
    B.ROOT.validate(c['root'],identity)
    require(B.ROOT.D.validate_readiness(c['readiness'],identity,record['execution'])['marker_boot_bound'],
        'missing current-boot readiness')
    committed=health(c['health'],identity)
    events=c['events'];times=[B.number(e['monotonic']) for e in events]
    require(events and times==sorted(times) and times[-1]<=observed,'capture event ordering')
    prepared=[e for e in events if e['event'] in B.READ.PREPARED]
    require(tuple(e['event'] for e in prepared)==B.READ.PREPARED
        and all(e['monotonic']<begin for e in prepared),'prestarted capture missing')
    disconnected=[e for e in events if e['event']=='source-disconnected']
    require(len(disconnected)==1 and disconnected[0]['source_boot_id']==old
        and begin<disconnected[0]['monotonic']<observed,'ordinary source did not disconnect')
    target=False
    for event in events:
        require(event['event'] not in {'transport-check-failed','missing-source-disconnect',
            'invalid-stage','log-bound-exceeded','capture-ended','host-cleanup'},'failed or closed capture')
        if event['event']=='usb-discovery-interrupted':
            require(not target and event.get('target_seen') is False
                and event.get('phase')=='usb-discovery' and event.get('errno') in (2,19)
                and event.get('operation') in {'idVendor','idProduct','product','serial'}
                and event.get('observed_mode')=='absent' and event.get('last_stage') is None
                and event.get('last_startup') is None,'unproven USB read interruption')
        if event['event']=='transport':
            require(not target or event['mode']=='target','post-target transport loss')
            target|=event['mode']=='target'
        if event['event'] in ('stage','startup-observation'):target=True
    stages=[e for e in events if e['event']=='stage']
    require(stages and all(e['stage']['boot_id']==boot and e['stage']['state']!='FAIL'
        and e['monotonic']>disconnected[0]['monotonic'] for e in stages),'wrong/failed target stage')
    require(any(e['stage']['stage']=='switch-root' and e['stage']['state']=='PASS' for e in stages),
        'missing root handover')
    require(all(e['observation']['boot_id']==boot for e in events if e['event']=='startup-observation'),
        'mixed startup observations')
    return dict(eligible=True,status='NOT RUN',s01_qualified=False,release_qualified=False,
        authority='none; coordinator must verify owned live capture and clean closure',
        identity=identity,health=committed,boot_to_health_seconds=observed-begin)

def closed(baseline,context,closure):
    """Validate actual post-decision closure, without synthesizing S01 evidence.

    Hash/command/process binding belongs to the existing coordinator and its
    pinned evidence consumer. This function validates their observed behavior.
    """
    decision=eligibility(baseline,context);c=closure;t=timing()
    require(c['source']==context['source'] and c['identity']==context['identity'],
        'mixed close source/identity')
    require(c['operation']=='ordinary-boot-smoke' and type(c['reboot_returncode']) is int
        and c['reboot_returncode']==0 and type(c['receiver_returncode']) is int
        and c['receiver_returncode']==0,'failed/ambiguous boot or capture')
    requested=B.number(c['close_requested_monotonic']);events=c['events']
    require(context['observed_monotonic']<=requested<=context['observed_monotonic']+t['decision_seconds'],
        'stale healthy-close decision')
    prefix=context['events'];require(events[:len(prefix)]==prefix,'changed observed capture prefix')
    times=[B.number(e['monotonic']) for e in events]
    require(times==sorted(times),'closed event ordering')
    ended=[e for e in events if e['event']=='capture-ended']
    require(len(ended)==1 and ended[0]['status']=='NOT RUN'
        and ended[0]['source_boot_id']==context['source_boot_id']
        and ended[0]['source_disconnected'] is True
        and ended[0]['last_stage']['boot_id']==context['identity']['boot_id']
        and ended[0]['last_stage']['state']!='FAIL'
        and requested<=ended[0]['monotonic']<=requested+t['receiver_stop_seconds'],'capture closure not proven')
    for event in events[len(prefix):]:
        require(event['event'] not in {'transport-check-failed','missing-source-disconnect',
            'invalid-stage','log-bound-exceeded','source-disconnected','usb-discovery-interrupted'},
            'failure after healthy-close decision')
        if event['event']=='transport':require(event['mode']=='target','late target loss')
        if event['event']=='stage':
            require(event['stage']['boot_id']==context['identity']['boot_id']
                and event['stage']['state']!='FAIL','late wrong/failed stage')
        if event['event']=='startup-observation':
            require(event['observation']['boot_id']==context['identity']['boot_id'],'late mixed boot')
    cleanup=[e for e in events if e['event']=='host-cleanup']
    require([e['item'] for e in cleanup]==['route','firewall','profile','address']
        and all(e['status']=='PASS' and ended[0]['monotonic']<e['monotonic']<=requested+t['close_seconds']
                for e in cleanup),'host cleanup incomplete/late')
    finish=B.number(c['finished_monotonic'])
    require(times[-1]<=finish<=context['entry_monotonic']+t['startup_seconds']+t['close_seconds'],
        'ordinary smoke close deadline')
    return dict(status='PASS',smoke_component=True,s01_qualified=False,s05_qualified=False,
        release_qualified=False,identity=context['identity'],source=context['source'],
        source_boot_id=context['source_boot_id'],started_monotonic=context['entry_monotonic'],
        finished_monotonic=finish,boot_to_health_seconds=decision['boot_to_health_seconds'],
        scope='one closed ordinary smoke component; not full watchdog/recovery or three-boot qualification')

def sequence(baseline,run):
    """Three distinct consecutive ordinary boots, with no failed boot discarded."""
    t=timing();start=B.number(run['started_monotonic']);finish=B.number(run['finished_monotonic'])
    deadline=next(row['deadline_seconds'] for row in B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()['tests'] if row['id']=='S05')
    require(0<finish-start<=deadline and len(run['boots'])==3,'incomplete/late three-boot sequence')
    prior=None;previous_end=start;identities=[];results=[]
    for boot in run['boots']:
        context=boot['context'];closure=boot['closure']
        require(context['source']==run['source'],'mixed sequence source')
        before=B.number(boot['preflight_monotonic'])
        require(previous_end<=before<context['entry_monotonic']<=before+t['preflight_seconds'],
            'overlapping or late preflight')
        if prior is not None:require(context['source_boot_id']==prior,'non-consecutive boots')
        else:identities.append(context['source_boot_id'])
        result=closed(baseline,context,closure)
        prior=result['identity']['boot_id'];identities.append(prior);results.append(result)
        previous_end=result['finished_monotonic']
    require(len(set(identities))==4 and previous_end<=finish,'reused boot or unfinished sequence')
    return dict(status='PASS',sequence_component=True,s05_qualified=False,release_qualified=False,
        identity=results[-1]['identity'],source=run['source'],boot_ids=identities[1:],
        observed_seconds=finish-start,boot_to_health_seconds=[r['boot_to_health_seconds'] for r in results],
        scope='three closed ordinary smoke components; pinned producer/artifact replay still required')
