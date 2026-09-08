#!/usr/bin/env python3
"""S01 offline replay of a reviewed ordinary boot; never contacts or reboots a device."""
import argparse,hashlib,importlib.util,json,math,os,re,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts/host'))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ROOT=load('ordinary_root',R/'scripts/host/check-standalone-root.py')
READ=load('ordinary_reader',R/'scripts/host/check-rescue-startup.py')
require=ROOT.require
def number(v):
 require(type(v) in (int,float) and math.isfinite(v) and v>=0,'invalid timing')
 return v
def host(value):
 require(value['nfs_listening'] is False,'NFS listener present or unknown')
 for line in value['listeners'].splitlines():
  fields=line.split();require(len(fields)>=5 and fields[0]=='LISTEN','invalid listener row')
  port=fields[3].rsplit(':',1)[-1]
  require(port!='2049','raw NFS listener present')
  if port=='8080':require(fields[3]=='127.0.0.1:8080' and '"steamwebhelper"' in line,'unknown boot-port listener')
  if port=='8081':require('"systemd"' in line and 'pid=1,' in line,'unknown bundle-port listener')
 require(set(value['cef_socket'].splitlines())=={
  'FragmentPath=/usr/lib/systemd/system/steam-web-debug-portforward.socket','DropInPaths='},'CEF override')
 return number(value['monotonic'])
def qualify(d,record,hashes,producers,deadline=300):
 receipt=d['receipt'];entry=d['entry'];root=d['root'];identity=root['identity']
 source=receipt['source'];boot=identity['boot_id'];old=entry['source_boot_id']
 require(hashes['manifest']==record['manifest_sha256'] and d['manifest']['bundle']==identity['bundle']
  and d['manifest']['target_release']==identity['release'],'manifest/kernel mismatch')
 require(receipt['format']=='rog5-headless-capture-v1' and receipt['canonical_record']==record
  and receipt['profile']==record['candidate'],'canonical capture mismatch')
 require(source['clean'] is True and re.fullmatch('[0-9a-f]{40}',source['revision'])
  and re.fullmatch('[0-9a-f]{64}',source['worktree_digest']),'source identity')
 require(all(x['source']==source for x in (root,entry,d['preflight'],d['startup'],d['supervision'],d['readiness'])),
  'mixed source evidence')
 require(ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(boot) and ROOT.D.CAPTURE.STAGES.BOOT_ID.fullmatch(old)
  and boot!=old and receipt['source_boot_id']==old,'old or invalid boot identity')
 require(identity['serial']==record['serial'] and identity['bundle']==record['target_bundle'],'wrong device/bundle')
 require(entry['artifact']==record['boot_image_sha256']
  and entry['preflight_sha256']==hashes['preflight']
  and entry['receiver_receipt_sha256']==hashes['receipt'],'unbound entry or artifact')
 require(entry['operation']=='ordinary installed release reboot; no RAM claim retry','not an ordinary reboot')
 require(entry['supervisor_sha256']==producers['supervisor']
  and d['preflight']['observer_sha256']==producers['preflight']
  and receipt['receiver_sha256']==producers['receiver']
  and d['readiness']['runner_sha256']==producers['deployed'],'changed evidence producer')
 require(d['preflight']['status']=='PASS' and d['preflight']['source_boot_id']==old
  and d['preflight']['identity']['boot_id']==old
  and d['preflight']['installed_boot_b_sha256']==entry['artifact']
  and d['preflight']['manifest_sha256']==record['manifest_sha256'],'source preflight mismatch')
 check=d['receiver_check'];require(check['status']=='PASS' and check['test']=='H01-receiver'
  and check['profile']==record['candidate'] and check['receipt_sha256']==hashes['receipt'],'missing prestarted capture proof')
 required=number(receipt['required_seconds']);remaining=number(check['remaining_seconds'])
 timing=ROOT.D.CAPTURE.ACCEPTANCE.load_contract()['defaults']['rescue_capture']
 expected=timing['recovery_seconds']+timing['target_rollback_seconds']+timing['cleanup_seconds']
 window=number(receipt['deadline_monotonic'])-number(receipt['started_monotonic'])
 require(required==expected and remaining>=required
  and window>=max(remaining,expected+timing['preflight_seconds']),'insufficient receiver lifetime')
 begin=number(entry['monotonic']);elapsed=number(d['startup']['boot_to_ssh_seconds'])
 require(0<elapsed<=deadline,'startup deadline')
 for report in (d['startup'],d['supervision']):
  require(report['status']=='LOCAL_ROOT_PASS_CAPTURE_PENDING' and report['identity']==identity
   and report['boot_requested'] is True and type(report['reboot_returncode']) is int
   and report['reboot_returncode']==0 and report['boot_to_ssh_seconds']==elapsed,'failed/ambiguous startup')
 require(type(d['supervision']['receiver_returncode']) is int
  and d['supervision']['receiver_returncode']==0,'capture still running or failed')
 require(root['status']=='PASS' and root['manifest_sha256']==record['manifest_sha256']
  and root['stdout_sha256']==hashes['root_raw'],'root proof changed')
 ROOT.validate(d['root_raw'],identity)
 readiness=d['readiness'];require(readiness['status']=='PASS' and readiness['identity']==identity
  and readiness['canonical_record']==record,'readiness mismatch')
 require(ROOT.D.validate_readiness(readiness['actual'],identity,record['execution'])['marker_boot_bound'],
  'unbound readiness marker')
 events=d['events'];require(events,'missing capture events')
 times=[number(e['monotonic']) for e in events];require(times==sorted(times),'event ordering')
 prepared=[e for e in events if e['event'] in READ.PREPARED]
 require(tuple(e['event'] for e in prepared)==READ.PREPARED
  and all(e['monotonic']<begin for e in prepared),'capture prepared late/incomplete')
 failures={'transport-check-failed','missing-source-disconnect','invalid-stage','log-bound-exceeded'}
 require(not any(e['event'] in failures for e in events),'failed diagnostic channel')
 target_seen=False
 for event in events:
  target_seen |= event['event'] in {'stage','startup-observation'}
  if event['event']=='transport':
   require(not target_seen or event['mode']=='target','post-target transport loss')
   target_seen|=event['mode']=='target'
  if event['event']=='usb-discovery-interrupted':
   require(not target_seen and event.get('target_seen') is False
    and event.get('phase')=='usb-discovery' and event.get('errno') in (2,19)
    and event.get('operation') in ROOT.D.CAPTURE.USB_READ_OPERATIONS
    and event.get('observed_mode')=='absent' and event.get('last_stage') is None
    and event.get('last_startup') is None,'unproven USB read interruption')
 disconnect=[e for e in events if e['event']=='source-disconnected']
 require(len(disconnect)==1 and disconnect[0]['source_boot_id']==old
  and begin<disconnect[0]['monotonic']<begin+elapsed,'missing source disconnect')
 stages=[e for e in events if e['event']=='stage']
 require(stages and all(e['stage']['boot_id']==boot and e['stage']['state']!='FAIL'
  and e['monotonic']>disconnect[0]['monotonic'] for e in stages),'wrong or failed target stage')
 require(any(e['stage']['stage']=='switch-root' and e['stage']['state']=='PASS'
  and e['monotonic']<=begin+elapsed for e in stages),'missing handover before SSH')
 starts=[e for e in events if e['event']=='startup-observation']
 require(all(e['observation']['boot_id']==boot for e in starts),'mixed startup boot')
 finished=d['capture_result'];ended=[e for e in events if e['event']=='capture-ended']
 require(len(ended)==1 and finished['status']=='NOT RUN' and ended[0]['status']=='NOT RUN'
  and ended[0]['source_disconnected'] is True
  and ended[0]['source_boot_id']==old and ended[0]['monotonic']>=number(receipt['deadline_monotonic'])
  and number(finished['duration_seconds'])>=required and finished['source_disconnected'] is True
  and finished['source_boot_id']==old and finished['last_stage']==ended[0]['last_stage']
  and finished['last_stage']['boot_id']==boot,'capture missing/shortened/mixed')
 cleanup=[e for e in events if e['event']=='host-cleanup']
 require([e['item'] for e in cleanup]==['route','firewall','profile','address']
  and all(e['status']=='PASS' and e['monotonic']>ended[0]['monotonic'] for e in cleanup),'cleanup incomplete')
 before,at_entry,after,closed=[host(x) for x in d['hosts']]
 require(before<at_entry<begin<after<=begin+elapsed<ended[0]['monotonic']<closed,'host evidence ordering')
 return dict(status='PASS',s01_qualified=True,release_qualified=False,identity=identity,
  original_source=source,evidence_reused=True,boot_to_ssh_seconds=elapsed,
  scope='one ordinary local-root boot with prestarted capture and cleanup; not repeated boots, endurance or recovery')

# One pinned input receipt, using existing F02 evidence semantics. Private
# coordinator sources are reviewed data only, never imported/executed here.
ROLES={'entry','receipt','preflight','receiver_check','startup','supervision',
 'root','root_raw','capture_result','events','readiness','manifest','composition',
 'host-0','host-1','host-2','host-3','supervisor_source','preflight_source'}
HEX=re.compile('[0-9a-f]{64}')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pinned(path,pin):
 require(isinstance(pin,str) and HEX.fullmatch(pin),'invalid evidence pin')
 raw=READ.read_bytes(path,9*1024**2)
 require(sha(raw)==pin,'evidence hash mismatch')
 return raw

def evaluate(inputs,pin,candidate,artifact_hashes):
 raw=pinned(inputs,pin);spec=READ.decode(raw)
 require(spec['format']=='rog5-standalone-boot-evidence-v1' and set(spec['files'])==ROLES,'evidence roles')
 payload={}
 for name,entry in spec['files'].items():
  require(set(entry)=={'path','sha256'},'invalid evidence entry')
  payload[name]=pinned(Path(entry['path']),entry['sha256'])
 require(payload['supervisor_source'] and payload['preflight_source'],'missing reviewed producer source')
 require(payload['events'].endswith(b'\n'),'truncated events')
 binary={'events','manifest','supervisor_source','preflight_source'}
 d={name:READ.decode(value) for name,value in payload.items() if name not in binary}
 d['events']=[READ.decode(line) for line in payload['events'].splitlines()]
 d['hosts']=[d.pop('host-'+str(i)) for i in range(4)]
 d['manifest']=READ.unique([line.split('=',1) for line in payload['manifest'].decode('ascii').splitlines()])
 F02=load('ordinary_composition',R/'scripts/host/check-wifi-restart-evidence.py')
 F02.composition_matches(d['composition'],candidate,artifact_hashes)
 record=dict(line.split('=',1) for line in ROOT.D.CAPTURE.CLAIMS.expected_record(candidate).decode().splitlines())
 ROOT.D.CAPTURE.CLAIMS.verify_entered(candidate) # No new claim or retry.
 require(record['boot_image_sha256']==artifact_hashes['boot_bundle'],'different installed release')
 for name in ('kernel','dtb','initramfs'):
  require(d['manifest'][name+'_sha256']==artifact_hashes[name],'different target artifact')
 source=d['receipt']['source']['revision']
 require(re.fullmatch('[0-9a-f]{40}',source),'source revision')
 dependencies=('scripts/host/check-standalone-root.py','scripts/host/check-deployed-server.py',
  'scripts/host/headless-stage-receiver.py','configs/storage/rog5-dedicated-linux-v1.json')
 for path in dependencies:
  historical=subprocess.check_output(['git','-C',str(R),'show',source+':'+path],timeout=5)
  require(historical==(R/path).read_bytes(),'changed qualification dependency: '+path)
 producers=dict(supervisor=sha(payload['supervisor_source']),preflight=sha(payload['preflight_source']),
  receiver=sha((R/'scripts/host/headless-stage-receiver.py').read_bytes()),
  deployed=sha((R/'scripts/host/check-deployed-server.py').read_bytes()))
 result=qualify(d,record,{k:sha(v) for k,v in payload.items()},producers)
 # Revalidate every pinned input after evaluation, not just the outer receipt.
 for name,entry in spec['files'].items():
  require(pinned(Path(entry['path']),entry['sha256'])==payload[name],'evidence changed')
 require(pinned(inputs,pin)==raw,'inputs changed')
 result.update(candidate=candidate,artifact_hashes=artifact_hashes,
  evidence_sha256={k:sha(v) for k,v in payload.items()})
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--inputs',type=Path,required=True);p.add_argument('--inputs-sha256',required=True)
 p.add_argument('--candidate',required=True);p.add_argument('--artifact-hashes',required=True)
 p.add_argument('--output',type=Path,required=True);a=p.parse_args();start=time.monotonic()
 require(a.output.is_absolute() and not a.output.resolve().is_relative_to(R),'private new output required')
 os.umask(0o077);a.output.mkdir(mode=0o700)
 A=ROOT.D.CAPTURE.ACCEPTANCE
 result=dict(status='FAIL',s01_qualified=False,release_qualified=False,evidence_reused=True,
  source=A.source_identity(),inputs_sha256=a.inputs_sha256,runner_sha256=sha(Path(__file__).read_bytes()))
 try:
  hashes=READ.unique([item.split('=',1) for item in a.artifact_hashes.split(',')])
  result.update(evaluate(a.inputs,a.inputs_sha256,a.candidate,hashes))
 except FileNotFoundError as error:
  result.update(status='BLOCKED',error='missing completed evidence: '+str(error))
 except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
  result.update(status='FAIL',error=str(error))
 if A.source_identity()!=result['source']:
  result.update(status='FAIL',s01_qualified=False,error='assessment source changed')
 result.update(duration_seconds=time.monotonic()-start,assessment_python=sys.version)
 (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(status=result['status'],seconds=result['duration_seconds'],error=result.get('error'))))
 return {'PASS':0,'FAIL':1,'BLOCKED':3}[result['status']]
if __name__=='__main__':raise SystemExit(main())
