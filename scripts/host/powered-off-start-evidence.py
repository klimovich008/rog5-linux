"""Offline S06 replay. Operator attestation is required; USB absence is not off proof."""
import ast
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
import importlib.util

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

HERE=Path(__file__).resolve().parent
M=load('off_start_smoke',HERE/'ordinary-boot-smoke.py')
E=load('off_start_bindings',HERE/'repeated-boot-evidence.py')
B=M.B;require=B.require
ROLES=({'run','baseline','baseline_proof','s05','coordinator_source','preflight_source',
        'health_source','manifest','operator','off_samples'}|set(E.PER_BOOT)) - {'reboot'} | {'poweroff'}

def timing():
    contract=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract();t=contract['defaults']['powered_off_start']
    require(set(t)=={'minimum_off_seconds','maximum_sample_gap_seconds'},'off-start timing fields')
    require(all(type(v) is int and v>0 for v in t.values()),'off-start timing values')
    total=next(row['deadline_seconds'] for row in contract['tests'] if row['id']=='S06')
    startup=M.timing()['startup_seconds'];close=M.timing()['close_seconds']
    transition=total-M.timing()['preflight_seconds']-startup-close
    require(t['maximum_sample_gap_seconds']<t['minimum_off_seconds']<transition
        and startup<=300 and total<=420,'off-start timing lattice')
    return dict(t,total_seconds=total,startup_seconds=startup,transition_seconds=transition,close_seconds=close)

def physical(context):
    """Require direct operator statements plus continuous same-host observation."""
    c=context;t=timing();p=c['physical'];identity=c['identity'];old=c['source_boot_id']
    require(set(p)=={'format','nonce','host_boot_id','source_boot_id','serial','usb_anchor',
        'conditions','operator','samples'},'physical evidence fields')
    require(p['format']=='rog5-powered-off-conditions-v1' and re.fullmatch('[0-9a-f]{64}',p['nonce']),
        'physical session identity')
    require(B.ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(p['host_boot_id'])
        and p['source_boot_id']==old and p['serial']==identity['serial']
        and p['usb_anchor']==B.ROOT.D.CAPTURE.ANCHOR,'physical device or host mismatch')
    require(p['conditions']==dict(side_usb='connected throughout',external_power='host USB throughout',
        other_cables='none',start_method='one physical power-button press'),
        'unsupported or changed cable/power conditions')
    messages=p['operator'];require(len(messages)==4,'operator handoff incomplete')
    expected=(('ready','READY'),('off-confirmed','OFF'),('start-requested','PRESS POWER ONCE'),('started','STARTED'))
    times=[]
    for row,(event,text) in zip(messages,expected):
        require(set(row)=={'event','text','monotonic','nonce','host_boot_id','origin'}
            and row['event']==event and row['text']==text+' '+p['nonce']
            and row['nonce']==p['nonce'] and row['host_boot_id']==p['host_boot_id']
            and row['origin']==('coordinator' if event=='start-requested' else 'operator'),
            'missing, stale or indirect operator statement')
        times.append(B.number(row['monotonic']))
    ready,off,start,pressed=times;begin=B.number(c['entry_monotonic']);observed=B.number(c['observed_monotonic'])
    require(ready<begin<off<start<=pressed<observed and begin-ready<=M.timing()['preflight_seconds']
        and start-off>=t['minimum_off_seconds']
        and pressed-begin<=t['transition_seconds'] and observed-start<=t['startup_seconds'],
        'off interval, operator transition or startup deadline')
    samples=p['samples'];require(2<=len(samples)<=1000,'missing/unbounded off observation')
    sample_times=[]
    for n,row in enumerate(samples,1):
        require(set(row)=={'sequence','monotonic','host_boot_id','serial','usb_anchor','mode','interface'}
            and type(row['sequence']) is int and row['sequence']==n
            and row['host_boot_id']==p['host_boot_id'] and row['serial']==p['serial']
            and row['usb_anchor']==p['usb_anchor'] and row['mode']=='absent' and row['interface'] is None,
            'off observation interrupted, wrong device or unknown USB state')
        sample_times.append(B.number(row['monotonic']))
    require(begin<sample_times[0]<=off and start<=sample_times[-1]<=pressed
        and all(0<b-a<=t['maximum_sample_gap_seconds'] for a,b in zip(sample_times,sample_times[1:])),
        'off observation gap or incomplete interval')
    return dict(start_monotonic=start,off_confirmed_monotonic=off,pressed_monotonic=pressed,
        off_seconds=start-off,boot_to_health_seconds=observed-start)

def eligibility(baseline,c):
    """A healthy close predicate only; no power-off, start, signal or qualification."""
    p=physical(c);identity=c['identity'];record=c['record'];source=c['source'];begin=B.number(c['entry_monotonic'])
    require(baseline['status']=='PASS' and baseline['s01_qualified'] is True
        and baseline['release_qualified'] is False and baseline['candidate']==record['candidate']
        and baseline['artifact_hashes']==c['artifact_hashes'] and c['artifact_hashes']
        and c['artifact_hashes']['boot_bundle']==record['boot_image_sha256'],'missing compatible full S01')
    require({k:v for k,v in baseline['identity'].items() if k!='boot_id'}==
        {k:v for k,v in identity.items() if k!='boot_id'} and identity['serial']==record['serial']
        and identity['bundle']==record['target_bundle'] and record['execution']=='fastboot-boot-selector-trial',
        'different installed release/device')
    require(source['clean'] is True and re.fullmatch('[0-9a-f]{40}',source['revision'])
        and re.fullmatch('[0-9a-f]{64}',source['worktree_digest']),'unfrozen source')
    boot=identity['boot_id'];old=c['source_boot_id']
    require(B.ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(old)
        and B.ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(boot) and boot!=old,'no distinct start')
    B.ROOT.validate(c['root'],identity)
    require(B.ROOT.D.validate_readiness(c['readiness'],identity,record['execution'])['marker_boot_bound'],
        'missing current-boot readiness')
    committed=M.health(c['health'],identity)
    events=c['events'];times=[B.number(e['monotonic']) for e in events]
    require(events and times==sorted(times) and times[-1]<=c['observed_monotonic'],'capture ordering')
    prepared=[e for e in events if e['event'] in B.READ.PREPARED]
    require(tuple(e['event'] for e in prepared)==B.READ.PREPARED
        and all(e['monotonic']<begin for e in prepared),'capture not prestarted')
    disconnect=[e for e in events if e['event']=='source-disconnected']
    require(len(disconnect)==1 and disconnect[0]['source_boot_id']==old
        and begin<disconnect[0]['monotonic']<=c['physical']['samples'][0]['monotonic'],
        'source disconnect absent or after off observation')
    target=False
    for event in events:
        require(event['event'] not in {'transport-check-failed','missing-source-disconnect','invalid-stage',
            'log-bound-exceeded','capture-ended','host-cleanup','usb-discovery-interrupted'},'failed or ambiguous capture')
        if event['event']=='transport':
            mode=event['mode'];when=event['monotonic']
            require(not target or mode=='target','post-start transport loss')
            if when>=disconnect[0]['monotonic'] and when<p['start_monotonic']:
                require(mode=='absent','device returned before requested start')
            if mode=='target':
                require(when>=p['start_monotonic'],'automatic start instead of powered-off interval');target=True
        if event['event'] in ('stage','startup-observation'):
            value=event['stage'] if event['event']=='stage' else event['observation']
            require(value['boot_id']==boot and event['monotonic']>=p['start_monotonic']
                and value.get('state')!='FAIL','failed, early or different boot');target=True
    require(any(e['event']=='stage' and e['stage']['stage']=='switch-root' and e['stage']['state']=='PASS'
        for e in events),'missing root handover')
    return dict(eligible=True,status='NOT RUN',s06_qualified=False,release_qualified=False,
        authority='none; coordinator must verify owned live capture and clean closure',identity=identity,
        health=committed,physical=p,boot_to_health_seconds=p['boot_to_health_seconds'])

# Shared receiver closure checks take original observations plus the explicit
# power-off operation and clock. No ordinary reboot evidence is fabricated.
def closed(baseline,context,closure):
    decision=eligibility(baseline,context)
    result=M.close_capture(context,closure,decision,operation='powered-off-start-smoke',
        action_key='poweroff_returncode',finish_deadline=context['entry_monotonic']+timing()['total_seconds'],
        scope='one powered-off start component; pinned evidence replay still required')
    return dict(result,s06_qualified=False)

health=M.health

def evaluate(args,base):
    require=base.require;payload=base.pinned(args.inputs,args.inputs_sha256);spec=base.READ.decode(payload)
    require(spec['format']=='rog5-powered-off-start-evidence-v1' and set(spec['files'])==ROLES,'S06 evidence roles')
    raw={key:base.pinned(Path(item['path']),item['sha256']) for key,item in spec['files'].items()}
    binary={'manifest','coordinator_source','preflight_source','health_source','events','health_stderr'}
    d={key:base.READ.decode(value) for key,value in raw.items() if key not in binary}
    hashes=base.READ.unique([part.split('=',1) for part in args.artifact_hashes.split(',')])
    baseline=base.evaluate(Path(spec['files']['baseline']['path']),base.sha(raw['baseline']),args.candidate,hashes)
    proof=d['baseline_proof'];run=d['run'];source=run['source']
    require(proof['inputs_sha256']==base.sha(raw['baseline']) and proof['source']==source
        and proof['runner_sha256']==base.sha(Path(base.__file__).read_bytes()),'wrong full baseline producer')
    require(all(proof[key]==baseline[key] for key in ('status','s01_qualified','identity','candidate',
        'artifact_hashes','original_source','evidence_sha256')),'full baseline changed')
    runtime=base.load('off_start_prerequisite',HERE/'check-server-runtime-evidence.py')
    item=spec['files']['s05'];s05=runtime.evaluate(SimpleNamespace(kind='S05',inputs=Path(item['path']),
        inputs_sha256=item['sha256'],candidate=args.candidate,artifact_hashes=args.artifact_hashes))
    require(s05['status']=='PASS' and s05['s05_qualified'] is True and run['s05']==s05,'missing replayed S05')
    require(run['status']=='POWERED_OFF_COMPONENT_PASS' and 'reason' not in run and 'error' not in run
        and run['s06_qualified'] is False and run['release_qualified'] is False,'incomplete off-start run')
    revision=source['revision'];require(source['clean'] is True and re.fullmatch('[0-9a-f]{40}',revision),'source revision')
    dependencies=('scripts/host/check-deployed-server.py','scripts/host/check-standalone-root.py',
        'scripts/host/headless-stage-receiver.py','scripts/host/ordinary-boot-smoke.py',
        'initramfs/persistent-root-shutdown-standalone','scripts/host/powered-off-start-evidence.py',
        'scripts/host/repeated-boot-evidence.py')
    for path in dependencies:
        require(subprocess.check_output(['git','-C',str(base.R),'show',revision+':'+path],timeout=5)==
            (base.R/path).read_bytes(),'changed observed dependency: '+path)
    old=json.loads(subprocess.check_output(['git','-C',str(base.R),'show',revision+':configs/release-acceptance.json'],timeout=5))
    current=base.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
    require(all(old['defaults'][key]==current['defaults'][key] for key in ('ordinary_smoke','rescue_capture','powered_off_start'))
        and next(t['deadline_seconds'] for t in old['tests'] if t['id']=='S06')==timing()['total_seconds'],
        'changed observation deadlines')
    canonical=dict(line.split('=',1) for line in base.ROOT.D.CAPTURE.CLAIMS.expected_record(args.candidate).decode().splitlines())
    require(base.sha(raw['manifest'])==canonical['manifest_sha256'],'manifest changed')
    manifest=base.READ.unique([line.split('=',1) for line in raw['manifest'].decode('ascii').splitlines()])
    require(all(manifest[key+'_sha256']==hashes[key] for key in ('kernel','dtb','initramfs')),'different artifacts')
    tree=ast.parse(raw['health_source'])
    probes=[ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='PROBE' for target in node.targets)]
    require(len(probes)==1 and isinstance(probes[0],str),'exact health probe missing')
    producers={key:base.sha(raw[key+'_source']) for key in ('coordinator','preflight','health')}
    producers.update(baseline_proof=base.sha(raw['baseline_proof']),receiver=base.sha((base.R/dependencies[2]).read_bytes()),
        deployed=base.sha((base.R/dependencies[0]).read_bytes()),shutdown=base.sha((base.R/dependencies[4]).read_bytes()))
    boot=run['boot'];c=boot['context'];physical_data=c['physical']
    require(c['source']==source and physical_data['operator']==d['operator'] and physical_data['samples']==d['off_samples']
        and physical_data['host_boot_id']==d['receiver']['host_boot_id'],'unbound physical observations')
    capture=current['defaults']['rescue_capture']
    full_window=sum(capture[key] for key in ('recovery_seconds','target_rollback_seconds','cleanup_seconds'))
    require(base.number(d['receiver']['deadline_monotonic'])>=
        c['entry_monotonic']+timing()['transition_seconds']+full_window
        and base.number(d['receiver_check']['remaining_seconds'])>=full_window+timing()['transition_seconds'],
        'failure capture does not cover the operator transition and full recovery window')
    require({k:v for k,v in s05['identity'].items() if k!='boot_id'}==
        {k:v for k,v in c['identity'].items() if k!='boot_id'},'different S05 release/device')
    rules=SimpleNamespace(health=health,eligibility=eligibility,closed=closed)
    E.bind_boot(boot,d,raw,proof,canonical,producers,probes[0],base,rules,kind='S06')
    start=base.number(run['started_monotonic']);finish=base.number(run['finished_monotonic'])
    require(start<=boot['preflight_monotonic']<c['entry_monotonic']
        and c['entry_monotonic']-boot['preflight_monotonic']<=M.timing()['preflight_seconds']
        and boot['closure']['finished_monotonic']<=finish
        and 0<finish-start<=timing()['total_seconds'],'incomplete or late overall supervision')
    for key,item in spec['files'].items():require(raw[key]==base.pinned(Path(item['path']),item['sha256']),'evidence changed')
    require(payload==base.pinned(args.inputs,args.inputs_sha256),'inputs changed')
    return dict(status='PASS',s06_qualified=True,release_qualified=False,candidate=args.candidate,
        artifact_hashes=hashes,identity=c['identity'],original_source=source,observed_seconds=finish-start,
        physical=physical(c),evidence_sha256={key:base.sha(value) for key,value in raw.items()})
