#!/usr/bin/env python3
"""Actual duplex transport and supervisor, with explicit inert target fixtures.

AST selection excludes all historical staging/import/SSH construction entrypoints.
The selected protocol functions themselves execute unchanged (or patched).
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'scripts/device/fixtures/display-loader/transport-before.py'
OLD_SHA='3d6f76bb421bf8f40967ac354d49e152248636b2272a1cf2653f8702e2a1a573'
PATCH=ROOT/'patches/display-controller/0003-production-transport.patch'
BOOT='11111111-2222-3333-4444-555555555555'
OWNER='a'*32
WHO=dict(boot_id=BOOT,owner=OWNER,release='7.1.4-rog5-production',bundle='fixture-production',
         descriptor_sha256=hashlib.sha256(b'inert fixture descriptor\n').hexdigest(),
         board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57')


def load(path,name):
    m=types.ModuleType(name);m.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m


def transport(path,backend):
    tree=ast.parse(path.read_text())
    names={'need','identity','expected_intent','terminal','exchange'}
    constants={'NORMAL_SECONDS','CLOSURE_SECONDS','RENEW_SECONDS','OUTPUT_LIMIT'}
    nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or
           isinstance(n,ast.FunctionDef) and n.name in names or
           isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
    m=types.ModuleType('actual_transport');m.__file__=str(path)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),m.__dict__)
    m.B=backend;m.save=backend.save
    return m


class Owner:
    def __init__(self,root):
        self.phase=root/'phase';self.phase.mkdir()
        self.admission=dict(boot_id=BOOT,owner=OWNER)
        self.receipt_sha='2'*64;self.calls=[];self.fail_after=None
    def check(self,seconds=35):
        self.calls.append(seconds)
        if self.fail_after is not None and len(self.calls)>self.fail_after:
            raise ValueError('fixture owner health lost')
        return True


def peer(directory,scenario,backend_path):
    """CLI used only as the local pipe peer; no SSH or device entrypoints."""
    b=load(backend_path,'peer_backend')
    spec=json.loads((directory/'peer.json').read_text());who=spec['identity']
    value=dict(phase='gpu-iommu-display',boot_id=who['boot_id'],owner=who['owner'],
               monitor_receipt_sha256=spec.get('monitor_receipt_sha256','2'*64))
    (directory/'boot').write_text(who['boot_id'])
    b.ENTRY=directory/'target-entered.json';b.INITIALIZER_ENTRY=directory/'legacy-entered.json';b.LOCK=directory/'lock'
    b.LIFETIME=100.;b.LEASE=3.;b.REAP=.5;b.CLEANUP=.5
    s=load(ROOT/'scripts/device/test-production-display-supervisor.py','peer_fixture')
    s.BOOT=who['boot_id'];s.OWNER=who['owner'];s.WHO=who
    case=s.Supervisor();case.b=b
    if scenario=='assembled':
        a=load(ROOT/'scripts/device/test-display-component.py','assembled_peer')
        a.Assembly.setUpClass();case.addCleanup(a.Assembly.doClassCleanups)
        component,_,_,_=a.pipeline(case,execute=False)
    else:
        mapping={'action-fail':'action-fail','hang':'hang','bad-zero':'bad-zero','wrong-intent':'wrong-scope'}
        component=case.component(directory,mapping.get(scenario,'pass'))
    b.load_component=lambda _,binding:component
    real_stat=os.fstat
    class Owned:
        def __init__(self,st):self.st=st;self.st_uid=self.st_gid=0
        def __getattr__(self,key):return getattr(self.st,key)
    # Lock metadata only needs substituted root ownership in this inert peer.
    old_emit=b.Supervisor.emit
    def emit(self,event,payload=None):
        if event=='transport-ready' and scenario=='wrong-ready':payload=dict(lease_seconds=3.,maximum_seconds=60.)
        if event=='terminal' and scenario in ('hang','delayed-terminal'):time.sleep(.08)
        if event=='terminal' and scenario=='bad-terminal':payload=dict(payload,remote_reaped=False)
        if scenario=='fragmented':
            raw=b.encoded(dict(self.identity,event=event,payload=payload))
            for part in (raw[:3],raw[3:11],raw[11:]):os.write(self.output,part);time.sleep(.005)
            self.out_count+=1
            return
        answer=old_emit(self,event,payload)
        if event=='terminal' and scenario=='extra-output':os.write(self.output,b'garbage after terminal\n')
        return answer
    b.Supervisor.emit=emit
    if scenario=='stderr':os.write(2,b'fixture stderr\n')
    try:
        with patch.object(b.os,'fstat',side_effect=lambda fd:Owned(real_stat(fd))):
            result=b.Supervisor(directory,value).run()
    finally:case.doCleanups()
    return 0 if result['status']=='PASS_PRODUCTION_DISPLAY_AND_CLEANUP' else 1


class Duplex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='production-transport-',dir=os.environ.get('TMPDIR',str(Path.home()/'.local/state')))
        cls.addClassCleanup(cls.temp.cleanup);cls.base=Path(cls.temp.name)
        if hashlib.sha256(OLD.read_bytes()).hexdigest()!=OLD_SHA:raise ValueError('historical transport changed')
        cls.source=cls.base/'transport.py';cls.source.write_bytes(OLD.read_bytes())
        cls.before='--before' in sys.argv
        if not cls.before:
            subprocess.run(['git','apply',str(PATCH)],cwd=cls.base,check=True,capture_output=True)
            subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0008-production-staging.patch')],cwd=cls.base,check=True,capture_output=True)
        cls.backend=cls.base/'backend.py'
        cls.backend.write_bytes((ROOT/'scripts/device/fixtures/display-loader/backend-before.py').read_bytes())
        subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0002-production-supervisor.patch')],cwd=cls.base,check=True,capture_output=True)
        subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0007-production-context.patch')],cwd=cls.base,check=True,capture_output=True)

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=self.base));self.out=self.root/'output';self.out.mkdir()
        self.owner=Owner(self.root)
        self.b=load(self.backend,'host_backend')
        self.t=transport(self.source,self.b)
        self.c=load(ROOT/'scripts/device/display-component.py','host_contract')
        self.contract=self.c.HostContract(WHO)

    def argv(self,scenario):
        d=self.root/'peer';d.mkdir()
        (d/'peer.json').write_text(json.dumps(dict(identity=WHO)))
        return [sys.executable,'-I','-B',str(Path(__file__).resolve()),'--peer',str(d),scenario,str(self.backend)]

    def run_peer(self,scenario='pass'):
        argv=self.argv(scenario)
        if self.before:
            old_b=load(ROOT/'scripts/device/fixtures/display-loader/backend-before.py','historical_host_protocol')
            self.t.B=old_b;self.t.save=old_b.save
            return self.t.exchange(self.owner,argv,self.out)
        return self.t.exchange(self.owner,argv,self.out,self.contract)

    def test_production_ready_and_terminal(self):
        result=self.run_peer()
        self.assertEqual(result['status'],'COMPONENT_PASS',result.get('transport_error'))
        self.assertTrue(result['remote_reaped']);self.assertTrue(result['ssh_reaped'])
        self.assertTrue(result['ssh_group_absent'])
        self.assertEqual(len(result['target']['component']['insertions']),14)
        self.assertFalse(result['physical_scanout_verified'])
        self.assertTrue((self.out/'entry-ack.json').exists())
        prior=(self.owner.phase/'entered.json').read_bytes()
        with self.assertRaises(FileExistsError):self.t.exchange(self.owner,[],self.out,self.contract)
        self.assertEqual((self.owner.phase/'entered.json').read_bytes(),prior)

    def test_unproven_local_group_refuses_positive_target(self):
        original=self.b.stop
        def uncertain(pid,force):
            # Actual child is safely closed; withhold only its group proof.
            return dict(original(pid,force),group_absent=False)
        with patch.object(self.b,'stop',side_effect=uncertain):r=self.run_peer()
        self.assertEqual(r['target']['status'],'PASS_PRODUCTION_DISPLAY_AND_CLEANUP')
        self.assertEqual(r['status'],'FAIL');self.assertFalse(r['ssh_group_absent'])
        self.assertIn('group closure unproven',r['transport_error'])

    def test_local_child_remains_owned_until_group_cleanup(self):
        original=self.b.stop;seen=[]
        def stop(pid,force):
            held=os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
            seen.append(pid)
            self.assertIsNotNone(held)
            return original(pid,force)
        with patch.object(self.b,'stop',side_effect=stop):r=self.run_peer()
        self.assertEqual(r['status'],'COMPONENT_PASS');self.assertEqual(len(seen),1)
        self.assertTrue(r['ssh_group_absent'])

    def test_failed_action_and_cleanup_preserve_failure(self):
        r=self.run_peer('action-fail');self.assertEqual(r['status'],'FAIL')
        self.assertTrue(r['remote_reaped']);self.assertIsNotNone(r['blank'])
        self.assertIn('fixture action failure',r['target']['error']['reason'])

    def test_normal_timeout_collects_independent_terminal(self):
        self.t.NORMAL_SECONDS=.45;self.t.CLOSURE_SECONDS=1.5
        r=self.run_peer('hang')
        self.assertEqual(r['status'],'FAIL');self.assertIsNotNone(r['transport_error'])
        self.assertIsNotNone(r['target']);self.assertTrue(r['remote_reaped'])
        self.assertIsNotNone(r['blank']);self.assertLess(r['ended_monotonic']-r['started_monotonic'],2.5)

    def test_wrong_intent_never_acknowledged(self):
        r=self.run_peer('wrong-intent');self.assertEqual(r['status'],'FAIL')
        self.assertFalse((self.out/'entry-ack.json').exists())
        self.assertFalse((self.root/'peer/action-started').exists())

    def test_wrong_ready_never_starts(self):
        r=self.run_peer('wrong-ready');self.assertEqual(r['status'],'FAIL')
        self.assertFalse((self.root/'peer/target-entered.json').exists())

    def test_fragmented_records(self):
        self.assertEqual(self.run_peer('fragmented')['status'],'COMPONENT_PASS')

    def test_failed_zero_cannot_pass(self):
        r=self.run_peer('bad-zero');self.assertEqual(r['status'],'FAIL');self.assertTrue(r['cleanup_errors'])

    def test_stderr_never_passes(self):
        r=self.run_peer('stderr');self.assertEqual(r['status'],'FAIL');self.assertIn('stderr',r['transport_error'])

    def test_corrupted_terminal_refused(self):
        r=self.run_peer('bad-terminal');self.assertEqual(r['status'],'FAIL');self.assertFalse(r['remote_reaped'])

    def test_missing_transport_consumes_host_attempt_only(self):
        r=self.t.exchange(self.owner,['/no/such/inert-peer'],self.out,self.contract)
        self.assertEqual(r['status'],'FAIL');self.assertTrue((self.owner.phase/'entered.json').exists())
        self.assertFalse((self.out/'entry-ack.json').exists())

    def test_owner_failure_before_entry(self):
        self.owner.fail_after=0
        with self.assertRaisesRegex(ValueError,'health lost'):
            self.t.exchange(self.owner,[],self.out,self.contract)
        self.assertFalse((self.owner.phase/'entered.json').exists())

    def test_mismatched_contract_before_entry(self):
        self.owner.admission['owner']='b'*32
        with self.assertRaises(ValueError):self.t.exchange(self.owner,[],self.out,self.contract)
        self.assertFalse((self.owner.phase/'entered.json').exists())

    def test_host_contract_does_not_read_target(self):
        value=copy.deepcopy(WHO);contract=self.c.HostContract(value);value['owner']='b'*32
        intent=contract.entry_intent(BOOT,OWNER);intent['identity']['owner']='b'*32
        self.assertEqual(contract.entry_intent(BOOT,OWNER)['identity'],WHO)
        self.assertEqual(len(intent['modules']),14)
        for changes in ({'descriptor_sha256':'bad'},{'board_dtb_sha256':'0'*64},{'release':'old'},{'extra':'unknown'}):
            with self.assertRaises(ValueError):self.c.HostContract(dict(WHO,**changes))

    def test_complete_host_supervisor_loader_endpoint_chain(self):
        # Explicit module bytes/hash and per-child timing fixtures match the
        # actual loader test. Production default pins are exercised separately.
        self.contract.modules.MODULES=tuple((n,p,1,'fixture') for n,p,_,_ in self.contract.modules.MODULES)
        self.contract.modules.HELPER=('helper',1,'fixture',0o644)
        self.contract.modules.INSERT_SECONDS=2
        r=self.run_peer('assembled')
        self.assertEqual(r['status'],'COMPONENT_PASS',r.get('transport_error'))
        self.assertEqual(len(r['target']['component']['insertions']),14)
        self.assertEqual(r['blank']['write_bytes'],2);self.assertTrue(r['remote_reaped'])


    def test_owner_loss_after_ack_collects_cleanup(self):
        self.owner.fail_after=4
        r=self.run_peer('hang')
        self.assertEqual(r['status'],'FAIL');self.assertIn('health lost',r['transport_error'])
        self.assertTrue(r['remote_reaped']);self.assertIsNotNone(r['blank'])

    def test_interruption_retains_failure_even_with_positive_terminal(self):
        real_read=os.read;interrupted=False
        def read(fd,size):
            nonlocal interrupted
            if not interrupted and (self.root/'peer/action-started').exists():
                interrupted=True;raise KeyboardInterrupt('fixture transport interruption')
            return real_read(fd,size)
        with patch.object(self.t.os,'read',side_effect=read):r=self.run_peer('delayed-terminal')
        self.assertTrue(interrupted);self.assertEqual(r['status'],'FAIL')
        self.assertIn('fixture transport interruption',r['transport_error'])
        self.assertEqual(r['target']['status'],'PASS_PRODUCTION_DISPLAY_AND_CLEANUP')
        self.assertTrue(r['remote_reaped']);self.assertTrue(r['ssh_reaped'])

    def test_extra_output_after_terminal_is_failure(self):
        r=self.run_peer('extra-output');self.assertEqual(r['status'],'FAIL')
        self.assertIsNotNone(r['target']);self.assertTrue(r['remote_reaped'])

    def jump_past_historical_deadline(self):
        jumped=False
        def clock():
            nonlocal jumped
            if (self.root/'peer/action-started').exists():jumped=True
            return time.monotonic()+(79 if jumped else 0)
        self.t.time=types.SimpleNamespace(monotonic=clock)
        r=self.run_peer('delayed-terminal')
        self.assertTrue(jumped)
        return r

    def test_action_after_second_78_remains_within_new_budget(self):
        r=self.jump_past_historical_deadline()
        self.assertEqual(r['status'],'COMPONENT_PASS',r['transport_error'])
        self.assertGreater(r['ended_monotonic']-r['started_monotonic'],79)

    def test_old_78_second_budget_rejects_same_action(self):
        self.t.NORMAL_SECONDS=78
        r=self.jump_past_historical_deadline()
        self.assertEqual(r['status'],'FAIL');self.assertIn('deadline',r['transport_error'])

    def test_old_min_deadline_discards_delayed_cleanup(self):
        source=self.source.read_text()
        before='deadline=min(deadline,time.monotonic()+CLOSURE_SECONDS)'
        self.assertIn(before,OLD.read_text())
        self.assertEqual(source.count('deadline=time.monotonic()+CLOSURE_SECONDS'),1)
        mutant=self.root/'old-drain.py';mutant.write_text(source.replace('deadline=time.monotonic()+CLOSURE_SECONDS',before))
        self.t=transport(mutant,self.b);self.t.NORMAL_SECONDS=.45;self.t.CLOSURE_SECONDS=1.5
        r=self.run_peer('hang')
        self.assertEqual(r['status'],'FAIL');self.assertIsNone(r['target']);self.assertFalse(r['remote_reaped'])

    def test_production_bounds_and_sealed_entrypoints(self):
        self.assertEqual((self.t.NORMAL_SECONDS,self.t.CLOSURE_SECONDS),(120,18))
        self.assertGreaterEqual(self.t.NORMAL_SECONDS,self.b.LIFETIME+2*self.b.REAP+self.b.CLEANUP+2*self.b.REAP+1+5+2)
        self.assertGreaterEqual(self.t.CLOSURE_SECONDS,self.b.LEASE+2*self.b.REAP+self.b.CLEANUP+2*self.b.REAP+1+2)
        r=self.run_peer();self.assertEqual(r['status'],'COMPONENT_PASS')
        self.assertEqual(self.owner.calls[:2],[143,143])
        original=ast.parse(OLD.read_text());successor=ast.parse(self.source.read_text())
        for name in ('raw','load','ssh_argv','identity'):
            def definition(tree):return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
            self.assertEqual(definition(original),definition(successor),name)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--peer':
        raise SystemExit(peer(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4])))
    if '--before' in sys.argv:
        # unittest must not parse the fixture switch; preserve it for setup.
        suite=unittest.TestSuite([Duplex('test_production_ready_and_terminal')])
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    unittest.main(verbosity=2)
