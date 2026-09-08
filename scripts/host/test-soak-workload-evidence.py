"""Offline workload scope, payload and child-completion regressions."""
import functools,hashlib,importlib.util,json,os,unittest
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent;REPO=Path(os.environ.get('ROG5_TEST_REPO',str(HERE.parents[1])))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('soak_workload_rules',HERE/'soak-evidence-rules.py')
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  stream=load('soak_stream_fixture',REPO/'scripts/host/network-transfer-stream.py')
  cls.T=SimpleNamespace(validate=stream.validate,expected_digest=functools.lru_cache(maxsize=8)(stream.expected_digest))
  cls.sha=staticmethod(lambda raw:hashlib.sha256(raw).hexdigest())
 def storage_fixture(self):
  identity=dict(boot_id='fixture');scope=dict(namespace_inode=8194);nonce='1'*64
  sources=dict(ops=b'ops fixture',guard=b'guard fixture',window=b'window fixture')
  request=dict(phase='prepare',origin_boot_id=identity['boot_id'],identity=identity,scope=scope,nonce=nonce,size=M.SIZE)
  value=dict(status='PASS',s07_qualified=False,identity=identity,nonce=nonce,size=M.SIZE,cleanup=True,seconds=30,readbacks=2,
   ops_sha256=self.sha(sources['ops']),guard_sha256=self.sha(sources['guard']),
   file=dict(name='s04-'+nonce[:32],nonce=nonce,sha256=self.T.expected_digest(nonce,M.SIZE),parent_inode=8194,directory_inode=9000,
    file=dict(inode=9001,size=M.SIZE,mode=0o400,uid=0,gid=0,nlink=1)),
   power_before=dict(health='Good',temp='300',voltage_now='8500000'),power_after=dict(health='Good',temp='305',voltage_now='8500000'),thermal_after={'zone0':'32000'})
  entry=dict(sequence=1,label='storage-window',monotonic=20.1,request=request)
  returned=dict(monotonic=50.5);row=dict(started=20,finished=51,result=value)
  script=chr(10).join(('REQUEST='+repr(request),'OPS_SOURCE='+repr(sources['ops'].decode()),'GUARD_SOURCE='+repr(sources['guard'].decode()),sources['window'].decode())).encode()
  run=dict(identity=identity,baseline=dict(scratch_scope=scope),stats=dict(storage=[row]))
  return run,[(entry,returned,value)],[dict(event='storage-completed',index=0,monotonic=51.1)],{'0001.script':script},sources
 def test_scoped_storage_success(self):
  self.assertEqual(M.storage(*self.storage_fixture(),self.T,self.sha),{'1'*64})
 def test_storage_failure_scope_and_false_summary(self):
  for mutation in ('cleanup','short','readback','size','parent','hash','power','script','producer','summary'):
   run,commands,events,raw,sources=self.storage_fixture();value=commands[0][2]
   if mutation=='cleanup':value['cleanup']=False
   elif mutation=='short':value['seconds']=29
   elif mutation=='readback':value['readbacks']=0
   elif mutation=='size':value['file']['file']['size']=1
   elif mutation=='parent':value['file']['parent_inode']=1
   elif mutation=='hash':value['file']['sha256']='f'*64
   elif mutation=='power':value['power_after']['temp']='401'
   elif mutation=='script':raw['0001.script']+=b'changed'
   elif mutation=='producer':value['guard_sha256']='f'*64
   else:run['stats']['storage'][0]['result']=dict(value,cleanup=False)
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):M.storage(run,commands,events,raw,sources,self.T,self.sha)
 def network_fixture(self):
  links=[dict(name='usb'),dict(name='wifi')];identity=dict(boot_id='fixture');rows=[];pairs=[];raw={};observer=self.sha(b'reviewed observer')
  endpoint=lambda identity,link,action,nonce,size:repr((identity,link,action,nonce,size))
  for index in range(4):
   seq=2*index+1;nonce=str(index+2)*64;link=links[index//2];direction,action=(('upload','receive'),('download','send'))[index%2]
   start=100+index*20;value=dict(bytes=M.SIZE,sha256=self.T.expected_digest(nonce,M.SIZE),returncode=0,s02_qualified=False,duration_seconds=10)
   rows.append(dict(started=start,finished=start+10.1,link=link,direction=direction,nonce=nonce,result=value))
   command_hash=self.sha(nonce.encode());entry=dict(sequence=seq,monotonic=start-.5,link=link,direction=direction,nonce=nonce,command_sha256=command_hash)
   pairs.append((entry,dict(monotonic=start+10.2,result=value)))
   raw[f'{seq:04d}.script']=endpoint(identity,link,action,nonce,M.SIZE).encode()
   before=dict(status='ENTERED',started_monotonic=start+.3,command_sha256=command_hash,limit_bytes=4096,observer_sha256=observer)
   after=dict(before,status='TERMINAL',returncode=0,overflow=False,seconds=9,stderr_bytes=0,stderr_sha256=self.sha(b''))
   prefix=f'transfer-{seq:04d}/';raw[prefix+'entered.json']=json.dumps(before).encode();raw[prefix+'result.json']=json.dumps(after).encode();raw[prefix+'stderr.bin']=b''
  return dict(identity=identity,links=links,stats=dict(network=rows)),pairs,raw,endpoint,observer
 def check_network(self,run,pairs,raw,endpoint,observer):
  return M.network(run,pairs,raw,self.T,self.sha,json.loads,endpoint,observer,set())
 def test_four_hash_verified_transport_directions(self):self.assertEqual(len(self.check_network(*self.network_fixture())),12)
 def test_network_errors_wrong_endpoint_and_incomplete_child_cannot_pass(self):
  for mutation in ('missing-direction','hash','bytes','direction','deadline','returncode','stderr','overflow','command','script','child-deadline'):
   run,pairs,raw,endpoint,observer=self.network_fixture();value=run['stats']['network'][0]['result']
   if mutation=='missing-direction':run['stats']['network'].pop();pairs.pop()
   elif mutation=='hash':value['sha256']='f'*64
   elif mutation=='bytes':value['bytes']=1
   elif mutation=='direction':pairs[0][0]['direction']='download';run['stats']['network'][0]['direction']='download'
   elif mutation=='deadline':value['duration_seconds']=91
   elif mutation=='returncode':value['returncode']=False
   elif mutation=='stderr':raw['transfer-0001/stderr.bin']=b'guard failed'
   elif mutation=='script':raw['0001.script']+=b'changed'
   else:
    child=json.loads(raw['transfer-0001/result.json']);child.update({'overflow':True} if mutation=='overflow' else {'command_sha256':'f'*64} if mutation=='command' else {'seconds':91})
    raw['transfer-0001/result.json']=json.dumps(child).encode()
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.check_network(run,pairs,raw,endpoint,observer)
if __name__=='__main__':unittest.main()
