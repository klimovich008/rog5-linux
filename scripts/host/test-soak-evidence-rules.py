"""Adversarial offline S07 evidence tests; synthetic time is never hardware proof."""
import copy,hashlib,importlib.util,json,os,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=Path(os.environ.get('ROG5_TEST_REPO',str(HERE.parents[1])))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('soak_rules',HERE/'soak-evidence-rules.py')
LIMITS=dict(observation_seconds=3600,heartbeat_seconds=10,preflight_seconds=60,warmup_seconds=60,
 cleanup_seconds=180,max_file_windows=128,network_bytes=M.SIZE,network_deadline_seconds=90)
def fixture():
 run=dict(status='COMPONENT_PASS',s07_qualified=False,release_qualified=False,workers_stopped=True,
  deadline_seconds=3900,observation_seconds=3600,heartbeat_seconds=10,max_file_windows=128,
  file_bytes=M.SIZE,network_bytes=M.SIZE,started_monotonic=10,seconds=3700,
  observation_started=50,observation_finished=3650,
  stats=dict(storage=[dict(started=20+i*30,finished=50+i*30) for i in range(122)],
             network=[dict(started=20+i*60,finished=80+i*60) for i in range(61)],samples=[{}]*364))
 return run,[dict(sequence=1,event='soak-started',monotonic=50)]
class TimelineTests(unittest.TestCase):
 def test_complete_hour_and_workers(self):M.timeline(*fixture(),LIMITS,3900)
 def test_short_incomplete_or_overrun_never_passes(self):
  for change in ({'status':'PASS'},{'workers_stopped':False},{'reason':'late failure'},
   {'s07_qualified':True},{'file_bytes':True},{'seconds':3901},{'observation_finished':3649},
   {'observation_started':131},{'observation_finished':float('nan')},{'started_monotonic':True}):
   run,events=fixture();run.update(change)
   with self.subTest(change=change),self.assertRaises(ValueError):M.timeline(run,events,LIMITS,3900)
 def test_event_failures_reordering_and_clock_drift(self):
  for change in ({'sequence':2},{'event':'worker-failed'},{'monotonic':51.1},{'monotonic':4000}):
   run,events=fixture();events[0].update(change)
   with self.assertRaises(ValueError):M.timeline(run,events,LIMITS,3900)
 def test_workload_must_span_hour_and_stay_bounded(self):
  for key in ('storage','network'):
   for mutation in ('short','gap','overlap','deadline','late_start','empty'):
    run,events=fixture();rows=run['stats'][key]
    if mutation=='short':del rows[-2:]
    elif mutation=='gap':rows[2]['started']+=6
    elif mutation=='overlap':rows[2]['started']-=1
    elif mutation=='deadline':rows[-1]['finished']+=91
    elif mutation=='late_start':rows[0]['started']=51
    else:rows.clear()
    with self.subTest(key=key,mutation=mutation),self.assertRaises(ValueError):M.timeline(run,events,LIMITS,3900)
 def test_maximum_write_volume_and_heartbeat_count(self):
  for key,value in (('storage',[dict(started=20+i*30,finished=50+i*30) for i in range(129)]),('samples',[{}]*359)):
   run,events=fixture();run['stats'][key]=value
   with self.assertRaises(ValueError):M.timeline(run,events,LIMITS,3900)
 def test_raw_command_requires_one_successful_terminal_record(self):
  sha=lambda raw:hashlib.sha256(raw).hexdigest()
  raw={'0001.script':b'exact probe','0001.stdout':b'{"raw":true}','0001.stderr':b''}
  begin=dict(sequence=1,event='command-entered',monotonic=10,label='heartbeat',timeout=20,script_sha256=sha(raw['0001.script']))
  end=dict(sequence=2,event='command-returned',monotonic=11,command=1,returncode=0,stdout_sha256=sha(raw['0001.stdout']))
  commands,transfers,_=M.command_pairs([begin,end],raw,sha,json.loads)
  self.assertEqual(commands[0][2],{'raw':True});self.assertEqual(transfers,[])
  for events,data in (([begin],raw),([begin,end,end],raw),([begin,dict(end,returncode=False)],raw),
   ([begin,dict(end,monotonic=31)],raw),([begin,end],dict(raw,**{'0001.stderr':b'error'})),
   ([begin,end],dict(raw,**{'0001.script':b'changed probe'}))):
   with self.assertRaises(ValueError):M.command_pairs(events,data,sha,json.loads)
class ObservationTests(unittest.TestCase):
 def fixture(self):
  B=load('soak_fixture_boot',REPO/'scripts/host/check-standalone-boot.py')
  F=load('soak_fixture_root',REPO/'scripts/host/test-check-standalone-root.py').Tests();F.setUp()
  O=load('soak_fixture_observation',REPO/'scripts/host/soak-observation.py')
  root=F.value;identity=root['identity'];commands=[];raws=[]
  scope=dict(path='/persist',dev=1793,inode=2,mode=0o755,uid=0,gid=0,test_directory_exists=True,namespace_inode=8194)
  run,_=fixture();run['identity']=identity
  for index,stamp in enumerate([10,*range(20,3660,10),3690]):
   value=copy.deepcopy(root);fields=['0']*17
   completed=sum(row['finished']<=stamp for row in run['stats']['storage'])
   fields[2]=fields[6]=str(completed*M.SIZE//512)
   value.update(thermal={'zone0':'32000'},disk_stats={name:' '.join(fields) for name in ('loop1','sda23')},
    ext4={name:dict(status='present',value='0') for name in ('loop1','sda23','sda24')},
    kmsg=['6,10,1,-;baseline record'+chr(10)] if index==0 else [],kmsg_first_available=10,advice_available=True,
    target_uptime=float(stamp),scratch_scope=scope)
   commands.append((dict(label='heartbeat',monotonic=stamp-1),dict(monotonic=stamp-.1),value))
   raws.append(dict(value,host_monotonic=stamp))
  run['baseline']=raws[0];run['final']=raws[-1]
  run['stats']['samples']=[{**{k:v[k] for k in ('host_monotonic','target_uptime','power','disk_stats','ext4')},'cursor':10} for v in raws[1:-1]]
  return run,commands,B,O
 def test_raw_samples_cover_hour_with_real_root_rules(self):M.observations(*self.fixture())
 def test_loss_unsafe_state_or_summary_forgery_is_rejected(self):
  for mutation in ('log-gap','new-warning','missing-counter','io-regression','unsafe-power','namespace','forged-summary'):
   run,commands,B,O=self.fixture();raw=commands[10][2]
   if mutation=='log-gap':raw['kmsg']=['6,12,1,-;lost record'+chr(10)]
   elif mutation=='new-warning':raw['kmsg']=['4,11,1,-;WARNING: fixture'+chr(10)]
   elif mutation=='missing-counter':raw['ext4']['loop1']={'status':'absent'}
   elif mutation=='io-regression':raw['disk_stats']['sda23']=' '.join(['0']*17)
   elif mutation=='unsafe-power':raw['power']['temp']='401'
   elif mutation=='namespace':run['final']['scratch_scope']=dict(run['final']['scratch_scope'],namespace_inode=999)
   else:run['stats']['samples'][9]['target_uptime']+=10
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):M.observations(run,commands,B,O)
if __name__=='__main__':unittest.main()
