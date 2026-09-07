"""Offline S04 extension for the existing runtime-evidence runner.

No phone contact, private-source execution, storage write, reboot or retry.
"""
import hashlib,json,re,subprocess
from pathlib import Path

PHASES=('prepare','verify','cleanup')
ROLES={'plan','scope','s01-before','s01-after','cycle','started','entry'}|{
    phase+suffix for phase in PHASES for suffix in ('','.stdout','.root')}

def check_phases(d,raw,before,after,source_hashes,source_payloads,B,P,ops):
    require=B.require;source=after['original_source'];plan=d['plan'];scope=d['scope']
    origin=before['identity'];identity=after['identity']
    require({k:v for k,v in origin.items() if k!='boot_id'}==
            {k:v for k,v in identity.items() if k!='boot_id'} and origin['boot_id']!=identity['boot_id'],
            'different release/device or no reboot')
    previous=None;seconds=0
    for phase in PHASES:
        report=d[phase];target=d[phase+'.stdout']
        require(report['status']=='PASS' and report['phase']==phase and report['source']==source
                and report['target_started'] is True and report['s04_qualified'] is False
                and report['release_qualified'] is False and report['script_hashes']==source_hashes
                and report['inputs_sha256']==B.sha(raw['plan']) and report['target']==target
                and report['stdout_sha256']==B.sha(raw[phase+'.stdout']),'phase producer/content mismatch')
        expected_previous=None if previous is None else B.sha(raw[PHASES[PHASES.index(phase)-1]])
        require(report['previous_sha256']==expected_previous,'phase order/input changed')
        boot=origin['boot_id'] if phase=='prepare' else identity['boot_id']
        request=P.phase_request(plan,origin,scope,phase,boot,previous,source_hashes,B.sha(raw['plan']))
        P.validate_result(target,request,source_hashes[P.SOURCES[0]])
        require(report['identity']==request['identity'],'phase host identity')
        B.ROOT.validate(d[phase+'.root'],request['identity'])
        script='REQUEST='+repr(request)+'\nOPS_SOURCE='+repr(source_payloads[P.SOURCES[0]].decode())+'\n'+source_payloads[P.SOURCES[1]].decode()
        require(report['script_sha256']==B.sha(script.encode()),'wrong assembled target command')
        elapsed=B.number(report['seconds']);require(elapsed<=100,'phase exceeds coordinator deadline')
        seconds+=elapsed;previous=report
    prepared=d['prepare.stdout']['prepared'];file=prepared['file'];metadata=file['file']
    require(set(metadata)=={'inode','size','mode','uid','gid','nlink'} and
            all(type(v) is int for v in metadata.values()) and metadata['inode']>0
            and metadata['size']==64*1024**2 and metadata['mode']==0o400
            and metadata['uid']==metadata['gid']==0 and metadata['nlink']==1,'file metadata/scope')
    require(type(prepared['namespace_inode']) is int and prepared['namespace_inode']>0
            and file['parent_inode']==prepared['namespace_inode']
            and type(file['directory_inode']) is int and file['directory_inode']>0,'file directory identity')
    digest=hashlib.sha256()
    for block in ops.chunks(plan['nonce'],64*1024**2):digest.update(block)
    require(digest.hexdigest()==file['sha256'],'wrong independent payload hash')
    cycle=d['cycle'];started=d['started'];entry=d['entry'];elapsed=B.number(cycle['seconds'])
    require(cycle['status']=='PASS' and cycle['source']==source and cycle['origin_boot_id']==origin['boot_id']
            and cycle['identity']==identity and elapsed<=660 and elapsed>=seconds+after['boot_to_ssh_seconds'],
            'file cycle identity/deadline')
    require(type(started['deadline_seconds']) is int and started['deadline_seconds']==660
            and started['result_sha256']==B.sha(raw['prepare'])
            and B.number(started['monotonic'])+d['prepare']['seconds']<=B.number(entry['monotonic']),
            'preparation was not completed before reboot')
    require(after['evidence_sha256']['entry']==B.sha(raw['entry'])
            and entry['source_boot_id']==origin['boot_id'],'unbound ordinary reboot')
    for phase in PHASES:
        field={'prepare':'prepared_sha256','verify':'verified_sha256','cleanup':'cleanup_sha256'}[phase]
        require(cycle[field]==B.sha(raw[phase]),'changed final phase record')
    return dict(status='PASS',s04_qualified=True,identity=identity,original_source=source,
                observed_seconds=elapsed,scratch_bytes=metadata['size'],scratch_sha256=file['sha256'],
                scope='one 64 MiB file survived one ordinary reboot; verified exact cleanup; not crash/power-cut durability')

def evaluate(args,B):
    require=B.require
    payload=B.pinned(args.inputs,args.inputs_sha256);spec=B.READ.decode(payload)
    require(spec['format']=='rog5-storage-durability-evidence-v1' and set(spec['files'])==ROLES,'S04 evidence roles')
    raw={name:B.pinned(Path(item['path']),item['sha256']) for name,item in spec['files'].items()}
    d={name:B.READ.decode(value) for name,value in raw.items()}
    hashes=B.READ.unique([x.split('=',1) for x in args.artifact_hashes.split(',')])
    plan=d['plan'];require(plan['format']=='rog5-s04-file-plan-v1' and plan['candidate']==args.candidate
            and plan['artifact_hashes']==hashes,'different S04 plan/release')
    require(plan['s01']['sha256']==B.sha(raw['s01-before']) and plan['scope']['sha256']==B.sha(raw['scope']),
            'plan does not bind original S01/scope')
    before=B.evaluate(Path(spec['files']['s01-before']['path']),B.sha(raw['s01-before']),args.candidate,hashes)
    after=B.evaluate(Path(spec['files']['s01-after']['path']),B.sha(raw['s01-after']),args.candidate,hashes)
    require(all(x['status']=='PASS' and x['s01_qualified'] is True for x in (before,after)),
            'complete compatible ordinary-boot evidence required')
    P=B.load('durability_phase_evidence',B.R/'scripts/host/run-durability-phase.py')
    ops=B.load('durability_ops_evidence',B.R/'scripts/device/durability-file-ops.py')
    source=after['original_source']['revision'];require(re.fullmatch('[0-9a-f]{40}',source),'source revision')
    source_payloads=P.sources();source_hashes=P.hashes(source_payloads)
    for path,value in source_payloads.items():
        old=subprocess.check_output(['git','-C',str(B.R),'show',source+':'+path],timeout=5)
        require(old==value,'changed observed file-operation dependency')
    old_contract=json.loads(subprocess.check_output(['git','-C',str(B.R),'show',source+':configs/release-acceptance.json'],timeout=5))
    current=B.ROOT.D.CAPTURE.ACCEPTANCE.load_contract()
    require(all(next(t for t in c['tests'] if t['id']=='S04')['deadline_seconds']==660 for c in (old_contract,current)),
            'S04 deadline changed')
    result=check_phases(d,raw,before,after,source_hashes,source_payloads,B,P,ops)
    for name,item in spec['files'].items():require(raw[name]==B.pinned(Path(item['path']),item['sha256']),'evidence changed')
    require(payload==B.pinned(args.inputs,args.inputs_sha256),'inputs changed')
    result.update(candidate=args.candidate,artifact_hashes=hashes,evidence_sha256={k:B.sha(v) for k,v in raw.items()})
    return result
