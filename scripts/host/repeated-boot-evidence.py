"""Pinned offline S05 replay. Never imports private producers or contacts a phone."""
import ast
import json
import re
import subprocess
from pathlib import Path

PER_BOOT=('entry','preflight','receiver','receiver_check','root','root_raw','readiness',
          'health','health_raw','health_stderr','close_intent','capture_result','events','reboot',
          'host-before','host-at-entry','host-after-startup','host-after-capture')
ROLES={'run','baseline','baseline_proof','coordinator_source','preflight_source','health_source','manifest'}|{
    f'{n}.{role}' for n in range(1,4) for role in PER_BOOT}

def bind_boot(boot,d,raw,baseline,canonical,producers,probe,B,M,*,kind='S05'):
    require=B.require;c=boot['context'];end=boot['closure'];source=c['source'];identity=c['identity']
    require(kind in ('S05','S06'),'unsupported boot observation')
    operation=('ordinary installed release reboot; no RAM claim retry' if kind=='S05' else
        'installed release power-off and one operator start; no reboot substitution')
    action='reboot' if kind=='S05' else 'poweroff'
    require(c['record']==canonical,'different canonical boot record')
    pre=d['preflight'];entry=d['entry'];receipt=d['receiver'];root=d['root'];health=d['health'];ready=d['readiness']
    require(all(v['source']==source for v in (pre,entry,receipt,root,health,ready)),'mixed producer sources')
    require(pre['status']=='PASS' and pre['source_boot_id']==c['source_boot_id']
        and pre['identity']==dict(identity,boot_id=c['source_boot_id'])
        and pre['installed_boot_b_sha256']==canonical['boot_image_sha256']
        and pre['manifest_sha256']==canonical['manifest_sha256']
        and pre['observer_sha256']==producers['preflight'],'different installed preflight')
    require(entry['operation']==operation
        and entry['source_boot_id']==c['source_boot_id'] and entry['monotonic']==c['entry_monotonic']
        and entry['artifact']==canonical['boot_image_sha256']
        and entry['preflight_sha256']==B.sha(raw['preflight'])
        and entry['receiver_receipt_sha256']==B.sha(raw['receiver'])
        and entry['baseline_sha256']==producers['baseline_proof']
        and entry['supervisor_sha256']==producers['coordinator'],'unbound ordinary entry')
    require(receipt['format']=='rog5-headless-capture-v1' and receipt['canonical_record']==canonical
        and receipt['profile']==canonical['candidate'] and receipt['source_boot_id']==c['source_boot_id']
        and receipt['receiver_sha256']==producers['receiver'],'wrong capture producer/record')
    t=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()['defaults']['rescue_capture']
    required=t['recovery_seconds']+t['target_rollback_seconds']+t['cleanup_seconds']
    check=d['receiver_check']
    require(receipt['required_seconds']==required
        and B.number(receipt['deadline_monotonic'])-B.number(receipt['started_monotonic'])>=required+t['preflight_seconds']
        and receipt['started_monotonic']<entry['monotonic']
        and check['status']=='PASS' and check['test']=='H01-receiver'
        and check['profile']==canonical['candidate'] and check['receipt_sha256']==B.sha(raw['receiver'])
        and B.number(check['remaining_seconds'])>=required,'full failure capture was not armed')
    require(root['status']=='PASS' and root['identity']==identity and root['manifest_sha256']==canonical['manifest_sha256']
        and root['stdout_sha256']==B.sha(raw['root_raw']) and c['root']==d['root_raw'],'root observation changed')
    require(ready['status']=='PASS' and ready['identity']==identity and ready['canonical_record']==canonical
        and ready['runner_sha256']==producers['deployed'] and c['readiness']==ready['actual'],'readiness changed')
    require(health['status']=='PASS' and health['identity']==identity and health['returncode']==0
        and type(health['returncode']) is int and health['root_sha256']==B.sha(raw['root'])
        and health['stdout_sha256']==B.sha(raw['health_raw']) and not raw['health_stderr']
        and health['runner_sha256']==producers['health'] and health['actual']==c['health']
        and health['observed_monotonic']==c['observed_monotonic'],'health observation changed')
    command='expected='+repr(root['identity'])+'\n'+probe
    require(health['script_sha256']==B.sha(command.encode()),'wrong exact healthy command')
    h=d['health_raw'];require(type(h['unit']['returncode']) is int
        and h['unit']['returncode']==0 and not h['unit']['stderr'],'raw unit failure')
    normalized=dict(identity=h['identity'],uptime=h['uptime'],unit=B.READ.unique(
        [line.split('=',1) for line in h['unit']['stdout'].splitlines()]),files={
        'descriptor':h['files']['/run/rog5-native-wifi/trial-descriptor'],
        'healthy':h['files']['/run/rog5-native-wifi/healthy.record'],
        'ssh':h['files']['/run/rog5-persistent-ssh-identity.record']})
    require(normalized==c['health'] and health['healthy']==M.health(normalized,identity),'raw health mismatch')
    intent=d['close_intent']
    require(intent['monotonic']==end['close_requested_monotonic'] and intent['context']==c
        and intent['health_report_sha256']==B.sha(raw['health'])
        and intent['receiver_receipt_sha256']==B.sha(raw['receiver'])
        and intent['decision']==M.eligibility(baseline,c),'unbound early-close decision')
    require(raw['events'].endswith(b'\n'),'truncated capture events')
    events=[B.READ.decode(line) for line in raw['events'].splitlines()]
    require(events==end['events'],'changed closing events')
    ended=[event for event in events if event['event']=='capture-ended']
    require(len(ended)==1 and all(ended[0].get(key)==value for key,value in d['capture_result'].items()),
        'capture result changed')
    require(pre['shutdown_sha256']==producers['shutdown'],'shutdown changed')
    command='set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+c['source_boot_id']+'; test "$(sha256sum /run/initramfs/shutdown | cut -d " " -f 1)" = '+pre['shutdown_sha256']+'; systemctl '+action+' --no-block'
    require(type(d[action]['returncode']) is int
        and d[action]==dict(returncode=0,script_sha256=B.sha(command.encode())),'wrong/ambiguous boot command')
    times=[B.host(d[name]) for name in ('host-before','host-at-entry','host-after-startup','host-after-capture')]
    require(boot['preflight_monotonic']<=times[0]<times[1]<c['entry_monotonic']<times[2]
        <=c['observed_monotonic']<ended[0]['monotonic']<times[3]<=end['finished_monotonic'],
        'host preparation/cleanup ordering')
    require(boot['component']==M.closed(baseline,c,end),'component changed')

def evaluate(args,B):
    require=B.require;payload=B.pinned(args.inputs,args.inputs_sha256);spec=B.READ.decode(payload)
    require(spec['format']=='rog5-repeated-boot-evidence-v1' and set(spec['files'])==ROLES,'S05 evidence roles')
    raw={key:B.pinned(Path(item['path']),item['sha256']) for key,item in spec['files'].items()}
    binary={'manifest','coordinator_source','preflight_source','health_source'}|{
        f'{n}.{role}' for n in range(1,4) for role in ('events','health_stderr')}
    d={key:B.READ.decode(value) for key,value in raw.items() if key not in binary}
    hashes=B.READ.unique([part.split('=',1) for part in args.artifact_hashes.split(',')])
    baseline=B.evaluate(Path(spec['files']['baseline']['path']),B.sha(raw['baseline']),args.candidate,hashes)
    proof=d['baseline_proof'];run=d['run'];source=run['source']
    require(proof['inputs_sha256']==B.sha(raw['baseline'])
        and proof['source']==source,'wrong full-baseline producer')
    B.original_bytes(proof['source'],'scripts/host/check-standalone-boot.py',proof['runner_sha256'])
    require(all(proof[key]==baseline[key] for key in ('status','s01_qualified','identity','candidate',
        'artifact_hashes','original_source','evidence_sha256')),'full baseline changed')
    require(run['status']=='SEQUENCE_COMPONENT_PASS' and 'reason' not in run
        and run['s05_qualified'] is False and run['release_qualified'] is False,'sequence incomplete')
    revision=source['revision'];require(source['clean'] is True and re.fullmatch('[0-9a-f]{40}',revision),'source revision')
    dependencies=('scripts/host/check-deployed-server.py','scripts/host/check-standalone-root.py',
        'scripts/host/headless-stage-receiver.py','scripts/host/ordinary-boot-smoke.py',
        'initramfs/persistent-root-shutdown-standalone')
    for path in dependencies:
        original=B.original_bytes(source,path)
        # Shutdown is an installed release artifact. Authenticate its historical
        # source above, but bind executed bytes to the canonical release below.
        if path not in ('scripts/host/headless-stage-receiver.py','scripts/host/ordinary-boot-smoke.py',
                        'initramfs/persistent-root-shutdown-standalone'):
            require(original==(B.R/path).read_bytes(),'changed observed dependency: '+path)
    old=json.loads(subprocess.check_output(['git','-C',str(B.R),'show',revision+':configs/release-acceptance.json'],timeout=5))
    current=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
    require(all(old['defaults'][key]==current['defaults'][key] for key in ('ordinary_smoke','rescue_capture'))
        and next(t['deadline_seconds'] for t in old['tests'] if t['id']=='S05')==
        next(t['deadline_seconds'] for t in current['tests'] if t['id']=='S05'),'changed observation deadlines')
    canonical=dict(line.split('=',1) for line in B.ROOT.D.CAPTURE.CLAIMS.expected_record(args.candidate).decode().splitlines())
    require(B.sha(raw['manifest'])==canonical['manifest_sha256'],'manifest changed')
    manifest=B.READ.unique([line.split('=',1) for line in raw['manifest'].decode('ascii').splitlines()])
    require(all(manifest[key+'_sha256']==hashes[key] for key in ('kernel','dtb','initramfs')),'different artifacts')
    # Extract a literal only; private adapter code is data, never executed here.
    tree=ast.parse(raw['health_source'])
    probes=[ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='PROBE' for target in node.targets)]
    require(len(probes)==1 and isinstance(probes[0],str),'exact health probe missing')
    producers={key:B.sha(raw[key+'_source']) for key in ('coordinator','preflight','health')}
    producers.update(baseline_proof=B.sha(raw['baseline_proof']),
        receiver=B.sha(B.original_bytes(source,dependencies[2])),deployed=B.sha((B.R/dependencies[0]).read_bytes()),
        shutdown=B.ROOT.D.expected_files(args.candidate)['shutdown']['sha256'])
    M=B.load('repeated_boot_rules',B.R/'scripts/host/ordinary-boot-smoke.py')
    require(len(run['boots'])==3,'three boots required')
    hosts=set()
    for n,boot in enumerate(run['boots'],1):
        prefix=str(n)+'.';local_raw={key[len(prefix):]:value for key,value in raw.items() if key.startswith(prefix)}
        local={key[len(prefix):]:value for key,value in d.items() if key.startswith(prefix)}
        bind_boot(boot,local,local_raw,proof,canonical,producers,probes[0],B,M)
        require(B.ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(local['receiver']['host_boot_id']),'missing host boot identity')
        hosts.add(local['receiver']['host_boot_id'])
    require(len(hosts)==1,'host rebooted during sequence')
    result=M.sequence(proof,run);require(run['sequence']==result,'sequence result changed')
    deadline=next(t['deadline_seconds'] for t in current['tests'] if t['id']=='S05')
    require(result['observed_seconds']<=B.number(run['supervision_seconds'])<=deadline,'supervision exceeded S05 deadline')
    for key,item in spec['files'].items():require(raw[key]==B.pinned(Path(item['path']),item['sha256']),'evidence changed')
    require(payload==B.pinned(args.inputs,args.inputs_sha256),'inputs changed')
    return dict(status='PASS',s05_qualified=True,release_qualified=False,candidate=args.candidate,
        artifact_hashes=hashes,identity=result['identity'],original_source=source,
        observed_seconds=result['observed_seconds'],boot_ids=result['boot_ids'],
        evidence_sha256={key:B.sha(value) for key,value in raw.items()})
