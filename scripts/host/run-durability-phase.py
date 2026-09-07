#!/usr/bin/env python3
"""One scoped S04 file phase, never a reboot or automatic retry.

The coordinator owns CI qualification and ordinary-reboot capture. This runner
cannot issue a candidate, mount, format, or write raw storage. Its PASS is only
one phase, never S04 or release qualification.
"""
import argparse,hashlib,importlib.util,json,os,re,shlex,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts/host'))
spec=importlib.util.spec_from_file_location('durability_boot',R/'scripts/host/check-standalone-boot.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
ROOT=B.ROOT;D=ROOT.D;require=ROOT.require
TARGET=B.load('durability_namespace_policy',R/'scripts/device/durability-target.py')
SOURCES=('scripts/device/durability-file-ops.py','scripts/device/durability-target.py',
         'scripts/host/run-durability-phase.py')
def sources():return {p:(R/p).read_bytes() for p in SOURCES}
def hashes(payload):return {p:hashlib.sha256(raw).hexdigest() for p,raw in payload.items()}
def pinned(entry):return B.pinned(Path(entry['path']),entry['sha256'])
def decode(raw):return B.READ.decode(raw)

def phase_request(plan,origin,scope,phase,boot_id,previous,source_hashes,plan_hash):
    require(phase in ('probe','prepare','verify','cleanup'),'unknown phase')
    require(D.CAPTURE.STAGES.BOOT_ID.fullmatch(boot_id),'invalid current boot')
    require(re.fullmatch('[0-9a-f]{64}',plan['nonce']),'invalid nonce')
    require(scope['status']=='PASS' and scope['mutation']=='none' and scope['identity']==origin,
            'scope observation identity or mutation')
    parent=scope['scope']
    require(parent['path']=='/persist' and parent['uid']==parent['gid']==0 and parent['mode']==0o755
            and type(parent['test_directory_exists']) is bool and type(parent['dev']) is int
            and type(parent['inode']) is int,'authorized scratch parent')
    TARGET.namespace_policy(parent)
    identity=dict(origin,boot_id=boot_id)
    if phase in ('probe','prepare'):
        require(previous is None and identity==origin,'prepare must use qualified source boot')
    else:
        expected='prepare' if phase=='verify' else 'verify'
        require(previous is not None and previous['status']=='PASS' and previous['phase']==expected
                and previous['inputs_sha256']==plan_hash and previous['script_hashes']==source_hashes,
                'missing/changed previous phase')
        old=previous['target']
        require(old['status']=='PASS' and old['phase']==expected and old['origin_boot_id']==origin['boot_id']
                and old['nonce']==plan['nonce'] and old['size']==64*1024**2,'unbound previous target phase')
        require(identity['boot_id']!=origin['boot_id'] and
                (old['identity']==origin if phase=='verify' else old['identity']==identity),
                'wrong post-reboot identity')
    result=dict(phase=phase,origin_boot_id=origin['boot_id'],identity=identity,scope=parent,
                nonce=plan['nonce'],size=64*1024**2)
    if previous is not None:result['prepared']=previous['target']['prepared']
    return result

def validate_result(value,request,ops_hash):
    require(value['status']=='PASS' and value['phase']==request['phase']
            and all(value[k]==request[k] for k in ('identity','origin_boot_id','nonce','size'))
            and value['ops_sha256']==ops_hash and 0<=B.number(value['seconds'])<=60,
            'target phase result mismatch')
    expected=TARGET.namespace_policy(request['scope'])
    if expected is not None and request['phase']!='probe':
        require(type(value['prepared']['namespace_inode']) is int and
                value['prepared']['namespace_inode']==expected,'changed existing namespace result')
    if request['phase'] in ('verify','cleanup'):
        require(value['prepared']==request['prepared'],'file record changed after preparation')
    elif request['phase']=='prepare':
        record=value['prepared']['file']
        require(record['nonce']==request['nonce'] and record['name']=='s04-'+request['nonce'][:32]
                and record['file']['size']==request['size'] and record['file']['mode']==0o400
                and re.fullmatch('[0-9a-f]{64}',record['sha256']),'prepared record scope')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('inputs','manifest','identity-file','known-hosts','output'):
        p.add_argument('--'+key,type=Path,required=True)
    for key in ('inputs-sha256','phase','boot-id'):p.add_argument('--'+key,required=True)
    p.add_argument('--previous',type=Path);p.add_argument('--previous-sha256')
    args=p.parse_args();os.umask(0o077);start=time.monotonic()
    raw=B.pinned(args.inputs,args.inputs_sha256);plan=decode(raw)
    require(plan['format']=='rog5-s04-file-plan-v1','unknown file plan')
    payload=sources();source_hashes=hashes(payload);source=D.CAPTURE.ACCEPTANCE.source_identity()
    require(source['clean'],'frozen clean source required')
    s01=B.evaluate(Path(plan['s01']['path']),plan['s01']['sha256'],plan['candidate'],plan['artifact_hashes'])
    require(s01['status']=='PASS' and s01['s01_qualified'] is True,'qualified unchanged S01 required')
    scope_raw=pinned(plan['scope']);scope=decode(scope_raw)
    previous=decode(B.pinned(args.previous,args.previous_sha256)) if args.previous is not None else None
    request=phase_request(plan,s01['identity'],scope,args.phase,args.boot_id,previous,source_hashes,args.inputs_sha256)
    record=dict(x.split('=',1) for x in D.CAPTURE.CLAIMS.expected_record(plan['candidate']).decode().splitlines())
    require(hashlib.sha256(args.manifest.read_bytes()).hexdigest()==record['manifest_sha256'],'exact manifest required')
    require(args.output.is_absolute() and not args.output.resolve().is_relative_to(R),'private new output required')
    args.output.mkdir(mode=0o700)
    report=dict(status='FAIL',phase=args.phase,source=source,inputs_sha256=args.inputs_sha256,
                script_hashes=source_hashes,s04_qualified=False,release_qualified=False,
                previous_sha256=args.previous_sha256,identity=request['identity'],
                operation='single file phase; no reboot, mount, raw storage write or automatic retry')
    try:
        identity=request['identity']
        expected=D.expected_files(plan['candidate'])
        D.validate_snapshot(D.collect(identity,args.identity_file,args.known_hosts),identity,expected)
        D.validate_readiness(D.collect_readiness(identity,args.identity_file,args.known_hosts),identity,record['execution'])
        D.host_gate(identity)
        root_script='request='+repr(identity)+'\n'+ROOT.PROBE
        result=subprocess.run([*D.ssh_command(args.identity_file,args.known_hosts),'python3 -I -B -c '+shlex.quote(root_script)],
                              capture_output=True,timeout=20)
        (args.output/'root.stdout').write_bytes(result.stdout);(args.output/'root.stderr').write_bytes(result.stderr)
        require(result.returncode==0 and len(result.stdout)<=1048576,'root preflight failed')
        ROOT.validate(decode(result.stdout),identity)
        D.host_gate(identity)
        require(source==D.CAPTURE.ACCEPTANCE.source_identity() and sources()==payload,'source changed before operation')
        script='REQUEST='+repr(request)+'\nOPS_SOURCE='+repr(payload[SOURCES[0]].decode())+'\n'+payload[SOURCES[1]].decode()
        # Retain intent before the single SSH action. Any timeout/disconnect is
        # ambiguous: preserve target partial data, do not repeat this phase.
        report.update(target_started=True,script_sha256=hashlib.sha256(script.encode()).hexdigest())
        (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        result=subprocess.run([*D.ssh_command(args.identity_file,args.known_hosts),'python3 -I -B -c '+shlex.quote(script)],
                              capture_output=True,timeout=70)
        (args.output/'target.stdout').write_bytes(result.stdout);(args.output/'target.stderr').write_bytes(result.stderr)
        require(result.returncode==0 and len(result.stdout)<=1048576,'target phase failed or ambiguous; no retry')
        target=decode(result.stdout);validate_result(target,request,source_hashes[SOURCES[0]])
        D.host_gate(identity)
        require(source==D.CAPTURE.ACCEPTANCE.source_identity() and sources()==payload
                and B.pinned(args.inputs,args.inputs_sha256)==raw and pinned(plan['scope'])==scope_raw,'inputs changed')
        report.update(status='PASS',target=target,stdout_sha256=hashlib.sha256(result.stdout).hexdigest())
    except Exception as error:report['reason']=str(error)
    report['seconds']=time.monotonic()-start
    (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
