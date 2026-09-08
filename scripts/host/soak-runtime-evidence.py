"""Pinned, offline S07 replay. Never executes private producers or contacts a phone."""
import ast
import gzip
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

FIXED={'run','events','coordinator_source','preparation_source','network_source','wifi_source',
       'observer_source','preflight_source','manifest','archive','s02','s04','s05','ci','ci_log','ci_started'}
RAW_LIMIT=128*1024**2
SOURCES=('scripts/device/durability-file-ops.py','scripts/device/durability-target.py',
 'scripts/device/soak-file-window.py','scripts/host/soak-observation.py',
 'scripts/host/network-transfer-stream.py','scripts/host/check-standalone-root.py','scripts/host/check-deployed-server.py')


def literal(raw,name):
    # Literal extraction only; none of the retained private source is imported.
    matches=[ast.literal_eval(node.value) for node in ast.walk(ast.parse(raw))
             if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets)]
    if len(matches)!=1 or not isinstance(matches[0],str):raise ValueError('one exact '+name+' literal required')
    return matches[0]


def endpoint_source(raw,stream,identity,link,action,nonce,size):
    functions=[node for node in ast.parse(raw).body if isinstance(node,ast.FunctionDef) and node.name=='endpoint']
    if len(functions)!=1:raise ValueError('one exact endpoint function required')
    function=functions[0]
    bodies=[node.value.value for node in function.body if isinstance(node,ast.AugAssign)
            and isinstance(node.target,ast.Name) and node.target.id=='body'
            and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)]
    if len(bodies)!=1:raise ValueError('one reviewed transfer monitor literal required')
    return ('expected='+repr(identity)+'\nlink='+repr(link)+'\n'+literal(raw,'GUARD')
        +"\nns={'__name__':'rog5_transfer_endpoint'}\nexec(compile("+repr(stream.decode())+",'reviewed-transfer','exec'),ns)\n"
        +bodies[0]+" ns['endpoint']("+repr(action)+","+repr(nonce)+","+str(size)+")\n gate()\nfinally:\n finished.set();thread.join(timeout=4)\n")


def wifi_contract(entries,names,repo,sha,require):
    prefix='rog5-native-wifi/';units={n+'.service':sha(entries[prefix+'units/'+n+'.service'][1]) for n in names[:3]}
    dropins={name:{} for name in units};cpu='rog5-headless-cpu-policy.service'
    inputs=('cpu-frequency-cap.py','headless-cpu-policy.py','units/'+cpu)
    present=sum(prefix+name in entries for name in inputs);require(present in (0,3),'partial sealed CPU policy')
    if present:
        require(entries[prefix+'runtime'][1]==(repo/'initramfs/native-wifi/runtime').read_bytes(),'different sealed installer')
        units[cpu]=sha(entries[prefix+'units/'+cpu][1]);dropins[cpu]={}
        path='/run/systemd/system/rog5-wifi-radio.service.d/10-cpu-policy.conf'
        dropins['rog5-wifi-radio.service']={path:sha(('[Unit]\nRequires='+cpu+'\nAfter='+cpu+'\n').encode())}
    return units,dropins


def need(ok,reason):
    if not ok:raise ValueError(reason)


def heartbeat_source(preparation,probe,identity,cursor):
    extra=literal(preparation,'EXTRA')
    need(extra.count("value['kmsg']=rows")==1,'changed kernel-log probe assembly')
    extra=extra.replace("value['kmsg']=rows", """value['kmsg_first_available']=int(rows[0].split(';',1)[0].split(',')[1]) if rows else None
value['kmsg']=[row for row in rows if int(row.split(';',1)[0].split(',')[1])>cursor]
value['target_uptime']=float(read('/proc/uptime').split()[0])""")
    need(probe.count('print(json.dumps(value))')==1,'changed root probe assembly')
    return 'request='+repr(identity)+'\ncursor='+str(cursor)+'\n'+probe.replace('print(json.dumps(value))',extra)


def scripts_and_boundaries(run,commands,raw,canonical,archive,B,RUNTIME):
    require=B.require;identity=run['identity'];D=B.ROOT.D
    for suffix in ('before','after'):
        D.validate_snapshot(run['deployed_'+suffix],identity,D.expected_files(identity['bundle']))
        D.validate_readiness(run['readiness_'+suffix],identity,canonical['execution'])
    labels=[entry['label'] for entry,_,_ in commands]
    require(set(labels)=={'installed-inputs','wifi-before','wifi-after','endpoint-guard','heartbeat','storage-window'},'unknown/missing command class')
    require(labels.count('installed-inputs')==labels.count('wifi-before')==labels.count('wifi-after')==1
            and labels.count('endpoint-guard')==2,'extra/missing boundary command')
    by_label={label:[row for row in commands if row[0]['label']==label] for label in set(labels)}
    first_work=min(run['stats'][kind][0]['started'] for kind in ('storage','network'))
    require(all(returned['monotonic']<=first_work for entry,returned,_ in commands
                if entry['label'] in ('installed-inputs','wifi-before','endpoint-guard')),
            'load started before authenticated preflight completed')
    installed=by_label['installed-inputs'][0]
    wanted=dict(status='PASS',identity=identity,boot_b_sha256=canonical['boot_image_sha256'])
    require(installed[2]==run['installed']==wanted,'installed-byte proof changed')
    script='identity='+repr(identity)+'\nrecord='+repr(canonical)+'\n'+literal(raw['coordinator_source'],'installed')
    require(raw[f"{installed[0]['sequence']:04d}.script"]==script.encode(),'changed installed-byte command')
    require(installed[1]['monotonic']<=run['observation_started'],'late installed preflight')
    sealed=B.load('soak_sealed_archive',B.R/'scripts/host/run-sealed-busybox.py')
    entries=sealed.ARCHIVE.entries(gzip.decompress(archive))
    units,dropins=wifi_contract(entries,RUNTIME.F.NAMES,B.R,B.sha,require)
    script='request='+repr(dict(identity=identity,names=RUNTIME.F.NAMES,units=units,dropins=dropins))+'\n'+literal(raw['wifi_source'],'PROBE')
    before=by_label['wifi-before'][0];after=by_label['wifi-after'][0]
    for entry,_,value in (before,after):
        require(raw[f"{entry['sequence']:04d}.script"]==script.encode(),'changed Wi-Fi boundary command')
        RUNTIME.snapshot(value,identity);RUNTIME.ready(value)
    require(all(before[2][key]==after[2][key] for key in ('identity','units','interface','addresses','carrier','default_route')),'service/radio changed under load')
    require(before[1]['monotonic']<=run['observation_started'] and after[0]['monotonic']>=run['observation_finished'],'wrong Wi-Fi boundary timing')
    for link,(entry,returned,value) in zip(run['links'],by_label['endpoint-guard']):
        RUNTIME.link(link,before[2]);require(value==dict(status='GUARD_PASS',boot=identity['boot_id']),'endpoint guard failed')
        script='expected='+repr(identity)+'\nlink='+repr(link)+'\n'+literal(raw['network_source'],'GUARD')+"\nprint(json.dumps(dict(status='GUARD_PASS',boot=expected['boot_id'])))"
        require(raw[f"{entry['sequence']:04d}.script"]==script.encode() and returned['monotonic']<=run['observation_started'],'wrong/late authenticated endpoint guard')
    cursor=-1
    for entry,_,value in by_label['heartbeat']:
        script=heartbeat_source(raw['preparation_source'],B.ROOT.PROBE,identity,cursor)
        require(raw[f"{entry['sequence']:04d}.script"]==script.encode(),'changed exact root/log heartbeat')
        if value['kmsg']:cursor=int(value['kmsg'][-1].split(';',1)[0].split(',')[1])


def evaluate(args,B):
    require=B.require;payload=B.pinned(args.inputs,args.inputs_sha256);spec=B.READ.decode(payload)
    require(spec['format']=='rog5-soak-evidence-v1' and FIXED<=set(spec['files']) and len(spec['files'])<=12000,'S07 evidence roles/bound')
    for name in set(spec['files'])-FIXED:
        require(re.fullmatch(r'[0-9]{4,5}\.(script|stdout|stderr)|transfer-[0-9]{4,5}/(entered\.json|result\.json|stderr\.bin)',name),'unexpected raw evidence role')
    for row in spec['files'].values():require(set(row)=={'path','sha256'},'invalid evidence reference')
    raw={};total_bytes=0
    for name,row in spec['files'].items():
        if name=='archive':continue
        value=B.pinned(Path(row['path']),row['sha256']);total_bytes+=len(value)
        require(total_bytes<=RAW_LIMIT,'combined raw evidence exceeds memory bound')
        raw[name]=value
    run=B.READ.decode(raw['run']);source=run['source'];revision=source['revision']
    require(source['clean'] is True and re.fullmatch('[0-9a-f]{40}',revision)
            and re.fullmatch('[0-9a-f]{64}',source['worktree_digest']),'unfrozen original source')
    hashes=B.READ.unique([part.split('=',1) for part in args.artifact_hashes.split(',')])
    require(run['artifact_hashes']==hashes and run['identity']['bundle']==args.candidate,'different release')
    canonical=dict(line.split('=',1) for line in B.ROOT.D.CAPTURE.CLAIMS.expected_record(args.candidate).decode().splitlines())
    B.ROOT.D.CAPTURE.CLAIMS.verify_entered(args.candidate)
    require(canonical['serial']==run['identity']['serial'] and canonical['boot_image_sha256']==hashes['boot_bundle']
            and B.sha(raw['manifest'])==canonical['manifest_sha256'],'canonical identity mismatch')
    manifest=B.READ.unique([line.split('=',1) for line in raw['manifest'].decode('ascii').splitlines()])
    require(manifest['target_release']==run['identity']['release'] and manifest['bundle']==args.candidate
            and all(manifest[key+'_sha256']==hashes[key] for key in ('kernel','dtb','initramfs')),'different signed artifacts')
    archive_spec=spec['files']['archive'];require(archive_spec['sha256']==hashes['initramfs'],'wrong archive pin')
    archive=B.READ.read_bytes(Path(archive_spec['path']),128*1024**2)
    require(B.sha(archive)==hashes['initramfs'],'changed signed archive')
    for path in (*SOURCES,'initramfs/native-wifi/runtime'):
        require(subprocess.check_output(['git','-C',str(B.R),'show',revision+':'+path],timeout=5)==(B.R/path).read_bytes(),'changed observed dependency: '+path)
    original=json.loads(subprocess.check_output(['git','-C',str(B.R),'show',revision+':configs/release-acceptance.json'],timeout=5))
    contract=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
    O=B.load('soak_observation_rules',B.R/'scripts/host/soak-observation.py')
    # Consumer command additions never change an observed timeout or load profile.
    limits=O.timing(contract);require(original['defaults']['server_soak']==limits,'changed soak timing')
    total=next(row['deadline_seconds'] for row in contract['tests'] if row['id']=='S07')
    require(next(row['deadline_seconds'] for row in original['tests'] if row['id']=='S07')==total,'changed total deadline')
    require(run['runner_sha256']==B.sha(raw['coordinator_source']),'changed coordinator source')
    require(run['sources']=={path:B.sha((B.R/path).read_bytes()) for path in SOURCES},'changed direct runtime source')
    private={Path(spec['files'][role]['path']).name:B.sha(raw[role]) for role in
             ('preparation_source','network_source','wifi_source','observer_source','preflight_source')}
    require(len(private)==5 and run['private_sources']==private,'changed private producer dependency')
    ci=B.READ.decode(raw['ci']);started=B.READ.decode(raw['ci_started']);remote=run['ci']['remote']
    require(ci==run['ci']['local'] and ci['status']=='PASS' and ci['source']==revision and type(ci['returncode']) is int and ci['returncode']==0
            and ci['terminal_completion_marker'] is True and ci['source_unchanged'] is True
            and B.sha(raw['ci_log'])==ci['log_sha256'] and b'PASS repository Linux ci tier' in raw['ci_log'].splitlines(),'incomplete exact local CI')
    require(started['source']==revision and started['umask']=='0022' and started['cwd']==str(B.R)
            and started['command']==ci['command']==['scripts/host/rog5-dev','test','ci'],'wrong original CI invocation')
    require(remote['status']=='completed' and remote['conclusion']=='success' and remote['headSha']==revision
            and {row['name']:row['conclusion'] for row in remote['jobs']}=={name:'success' for name in ('head-exact','merge-compat','candidate-publication','qemu-system')},'incomplete exact remote CI')
    runtime=B.load('soak_prerequisite_replay',B.R/'scripts/host/check-server-runtime-evidence.py')
    prerequisites={}
    for kind in ('S02','S04','S05'):
        role=kind.lower();row=spec['files'][role]
        prerequisites[kind]=runtime.evaluate(SimpleNamespace(kind=kind,inputs=Path(row['path']),inputs_sha256=row['sha256'],candidate=args.candidate,artifact_hashes=args.artifact_hashes))
        require(prerequisites[kind]['status']=='PASS' and prerequisites[kind][role+'_qualified'] is True,'unqualified prerequisite '+kind)
    require(prerequisites==run['prerequisites'] and prerequisites['S05']['identity']==run['identity'],'changed prerequisites or last boot')
    require(raw['events'].endswith(b'\n'),'truncated events')
    events=[B.READ.decode(line) for line in raw['events'].splitlines()]
    rules=B.load('soak_full_evidence_rules',Path(__file__).with_name('soak-evidence-rules.py'))
    rules.timeline(run,events,limits,total)
    commands,transfers,expected=rules.command_pairs(events,raw,B.sha,B.READ.decode)
    scripts_and_boundaries(run,commands,raw,canonical,archive,B,runtime)
    rules.observations(run,commands,B,O)
    sources={name:(B.R/path).read_bytes() for name,path in zip(('ops','guard','window'),SOURCES[:3])}
    nonces=rules.storage(run,commands,events,raw,sources,runtime.T,B.sha)
    endpoint=lambda identity,link,action,nonce,size:endpoint_source(raw['network_source'],(B.R/SOURCES[4]).read_bytes(),identity,link,action,nonce,size)
    expected|=rules.network(run,transfers,raw,runtime.T,B.sha,B.READ.decode,endpoint,B.sha(raw['observer_source']),nonces)
    require(expected|FIXED==set(raw)|{'archive'},'missing/extra raw evidence')
    for name,row in spec['files'].items():
        if name=='archive':require(B.sha(B.READ.read_bytes(Path(row['path']),128*1024**2))==hashes['initramfs'],'archive changed during replay')
        else:require(raw[name]==B.pinned(Path(row['path']),row['sha256']),'evidence changed during replay')
    require(payload==B.pinned(args.inputs,args.inputs_sha256),'inputs changed during replay')
    return dict(status='PASS',s07_qualified=True,release_qualified=False,candidate=args.candidate,
        artifact_hashes=hashes,identity=run['identity'],original_source=source,observed_seconds=run['seconds'],
        load_seconds=run['observation_finished']-run['observation_started'],file_windows=len(run['stats']['storage']),
        network_transfers=len(run['stats']['network']),evidence_sha256={name:row['sha256'] for name,row in spec['files'].items()})
