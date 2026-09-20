#!/usr/bin/env python3
"""Actual logger with real local children; no SSH or kernel-device access.

Protocol peers are inert; remote identity is tested separately through the actual
read-only endpoint code. Short fixtures do not prove a 300-second observation.
"""
import ast
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
BEFORE='--before' in sys.argv
if BEFORE:sys.argv.remove('--before')


def load(path,name):
    module=types.ModuleType(name);module.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


D=load(ROOT/'scripts/device/test-production-display-transport.py','logger_transport_fixture')
PEER=r'''
import ast,base64,json,os,sys,time
from pathlib import Path
script=sys.stdin.buffer.read()
values={}
for node in ast.parse(script).body:
 if isinstance(node,ast.Assign):
  for target in node.targets:
   if isinstance(target,ast.Name) and target.id in ('EXPECTED','DURATION'):
    values[target.id]=ast.literal_eval(node.value)
identity=values['EXPECTED'];duration=values['DURATION'];seq=0
start=time.monotonic()
def emit(event,**fields):
 global seq
 value=dict(event=event,sequence=seq,identity=identity,elapsed=time.monotonic()-start);value.update(fields)
 print(json.dumps(value),flush=True);seq+=1
if CASE=='wrong-identity':identity=dict(identity,bundle='wrong')
if CASE=='stderr':sys.stderr.write('fixture failure\n');sys.stderr.flush()
emit('ready',read_only=True)
if CASE=='early':raise SystemExit(0)
if CASE=='hang':time.sleep(30)
if CASE=='malformed':print('bad json',flush=True);raise SystemExit(1)
count=100 if CASE=='burst' else 0
for _ in range(count):emit('kernel',data=base64.b64encode(b'x'*8000).decode())
time.sleep(.12)
if CASE=='descendant':
 child=os.fork()
 if child==0:time.sleep(30);os._exit(0)
 Path(DESCENDANT).write_text(str(child))
if CASE=='partial':sys.stdout.write('{');sys.stdout.flush();raise SystemExit(0)
emit('terminal',status='PASS',records=count,read_only=True,elapsed=duration+.1)
if CASE=='after-terminal':emit('heartbeat')
'''


class Logs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        D.Duplex.setUpClass();cls.addClassCleanup(D.Duplex.doClassCleanups)
        cls.base=D.Duplex.base
        cls.source=cls.base/'kernel-log.py'
        cls.old=ROOT/'scripts/device/fixtures/display-loader/kernel-log-before.py'
        if hashlib.sha256(cls.old.read_bytes()).hexdigest()!='b690ae15bfced9c5cc3c9ab905209dc12dccb909678c31975fe6a32282a18d14':
            raise ValueError('historical logger changed')
        cls.source.write_bytes(cls.old.read_bytes())
        if not BEFORE:subprocess.run(['git','apply',str(ROOT/'patches/display-controller/0005-production-kernel-log.patch')],cwd=cls.base,check=True,capture_output=True)

    def setUp(self):
        self.root=Path(tempfile.mkdtemp(dir=self.base));self.m=load(self.source,'actual_logger')
        self.b=load(D.Duplex.backend,'actual_process_stop')
        self.c=load(ROOT/'scripts/device/display-component.py','actual_logger_contract')
        self.contract=self.c.HostContract(D.WHO)
        self.obj=None

    def create(self,duration=1):
        args={} if BEFORE else dict(contract=self.contract,owner=D.OWNER,stop=self.b.stop)
        self.obj=self.m.KernelLog(self.root/'output',D.BOOT,duration,**args)
        self.addCleanup(self.clean)
        return self.obj

    def clean(self):
        obj=self.obj
        if obj is None:return
        if obj.process is not None and obj.process.returncode is None:
            try:
                receipt=self.b.stop(obj.process.pid,True)
                if receipt['reaped']:obj.process.returncode=receipt['exitcode']
            except ChildProcessError:pass
        if obj.process is not None and obj.process.stdin is not None:obj.process.stdin.close()
        if obj.pidfd is not None:
            try:os.close(obj.pidfd)
            except OSError:pass
            obj.pidfd=None
        for stream in obj.files.values():
            if not stream.closed:stream.close()

    def start(self,scenario='normal',duration=1):
        obj=self.create(duration)
        code='CASE='+repr(scenario)+'\nDESCENDANT='+repr(str(self.root/'descendant'))+'\n'+PEER
        with patch.object(self.m,'command',return_value=[sys.executable,'-I','-B','-c',code]):obj.start()
        return obj

    def test_production_identity_and_terminal(self):
        obj=self.start();self.assertTrue(obj.live())
        result=obj.close();self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['identity'],D.WHO);self.assertTrue(result['child_reaped'])
        self.assertTrue(result['group_absent']);self.assertTrue(obj.closed)

    def test_start_interruption_cleans_owned_resources(self):
        obj=self.create();code='import sys,time;sys.stdin.buffer.read();time.sleep(30)'
        held=[]
        def interrupt(*args):
            held.extend(obj.files.values());raise KeyboardInterrupt('fixture start interrupt')
        with patch.object(self.m,'command',return_value=[sys.executable,'-I','-B','-c',code]), \
             patch.object(self.m.os,'pidfd_open',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):obj.start()
        self.assertIsNotNone(obj.process.returncode,'partial start left child alive')
        self.assertEqual(len(held),2)
        self.assertTrue(all(f.closed for f in held),'partial start left files open')
        self.assertTrue(obj.closed)

    def test_fsync_failure_closes_all_files_without_stale_fd_retry(self):
        obj=self.start('hang');pidfd=obj.pidfd;streams=list(obj.files.values());fd=streams[0].fileno()
        fsync=os.fsync
        def fail(number):
            if number==fd:raise OSError(5,'fixture output fsync failure')
            return fsync(number)
        try:
            with patch.object(self.m.os,'fsync',side_effect=fail):result=obj.close(cancel=True)
        except OSError:result=None
        self.assertTrue(all(f.closed for f in streams),'one stream error skipped remaining cleanup')
        self.assertIsNone(obj.pidfd,'released pidfd ownership was retained')
        self.assertIsNotNone(obj.process.returncode)
        with patch.object(self.m.os,'close',wraps=os.close) as close:
            obj.close(cancel=True)
        self.assertNotIn(pidfd,[call.args[0] for call in close.call_args_list])
        self.assertEqual(result['status'],'FAIL')

    def test_exited_leader_cannot_leave_live_descendant(self):
        libc=ctypes.CDLL(None,use_errno=True);previous=ctypes.c_int()
        self.assertEqual(libc.prctl(37,ctypes.byref(previous),0,0,0),0)
        self.assertEqual(libc.prctl(36,1,0,0,0),0)
        descendant=None;reaped=False;real_killpg=os.killpg
        try:
            obj=self.start('descendant');deadline=time.monotonic()+2
            while not (self.root/'descendant').exists():
                self.assertLess(time.monotonic(),deadline);time.sleep(.005)
            descendant=int((self.root/'descendant').read_text())
            # PID1's orphan-reaping role is provided explicitly by this fixture.
            def group(group,sig):
                nonlocal reaped
                if not sig and not reaped:
                    try:got,_=os.waitpid(descendant,os.WNOHANG);reaped=got==descendant
                    except ChildProcessError:pass
                return real_killpg(group,sig)
            with patch.object(self.b.os,'killpg',side_effect=group):result=obj.close()
            self.assertTrue(reaped,'logger leader exited but its descendant survived')
            self.assertTrue(result['group_absent']);self.assertTrue(result['child_reaped'])
        finally:
            self.clean()
            if descendant is not None and not reaped:
                try:
                    os.waitid(os.P_PID,descendant,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                    os.kill(descendant,signal.SIGKILL);os.waitpid(descendant,0)
                except ChildProcessError:pass
            self.assertEqual(libc.prctl(36,previous.value,0,0,0),0)

    def test_wrong_identity_refused(self):
        with self.assertRaisesRegex(ValueError,'identity'):self.start('wrong-identity')

    def test_missing_terminal_refused(self):
        obj=self.start('early');r=obj.close();self.assertEqual(r['status'],'FAIL');self.assertTrue(r['child_reaped'])

    def test_stderr_refused(self):
        with self.assertRaisesRegex(ValueError,'stderr'):self.start('stderr')

    def test_partial_record_refused(self):
        obj=self.start('partial');r=obj.close();self.assertEqual(r['status'],'FAIL');self.assertTrue(r['child_reaped'])

    def test_record_after_terminal_refused(self):
        obj=self.start('after-terminal');r=obj.close();self.assertEqual(r['status'],'FAIL')

    def test_cancel_reaps_child_and_never_passes(self):
        obj=self.start('hang');r=obj.close(cancel=True)
        self.assertEqual(r['status'],'FAIL');self.assertTrue(r['child_reaped']);self.assertTrue(r['group_absent'])

    def test_large_burst_with_bounded_files(self):
        obj=self.start('burst');r=obj.close()
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['records'],100)
        self.assertGreater((obj.output/'stdout').stat().st_size,1024*1024)

    def test_300_second_terminal_uses_virtual_remote_elapsed(self):
        obj=self.start(duration=300);r=obj.close()
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['duration'],300)

    def test_duration_bounds(self):
        for value in (0,301,True,1.5):
            with self.subTest(value=value),self.assertRaises(ValueError):self.create(value)

    def test_source_boot_refused(self):
        args={} if BEFORE else dict(contract=self.contract,owner=D.OWNER,stop=self.b.stop)
        with self.assertRaises(ValueError):self.m.KernelLog(self.root/'unused',self.m.SOURCE_BOOT,1,**args)

    def test_contract_snapshot_and_source_digest(self):
        obj=self.create();self.contract._binding['bundle']='changed'
        self.assertEqual(obj.identity,D.WHO)
        self.contract=self.c.HostContract(D.WHO);self.contract.identity_source+=b'\n'
        with self.assertRaises(ValueError):self.create()

    def test_closed_logger_cannot_be_live(self):
        obj=self.start();obj.close()
        with self.assertRaises(ValueError):obj.live()

    def remote(self,changes=None,short_write=False,after_heartbeat=False):
        obj=self.create();tree=ast.parse(obj.script());scope={}
        split=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign)
                   and any(isinstance(t,ast.Name) and t.id=='seq' for t in n.targets))
        exec(compile(ast.Module(body=tree.body[:split],type_ignores=[]),'logger-prefix','exec'),scope)
        endpoint=scope['namespace'];now=[0.0];events=[];opened=[];closed=[]
        readings={str(endpoint['PROC']/'sys/kernel/random/boot_id'):(D.BOOT+'\n').encode(),
                  str(endpoint['PROC']/'sys/kernel/osrelease'):(D.WHO['release']+'\n').encode(),
                  str(endpoint['PROC']/'cmdline'):('rog5.bundle='+D.WHO['bundle']).encode(),
                  str(endpoint['DESCRIPTOR']):b'inert fixture descriptor\n'}
        readings.update(changes or {})
        endpoint['read']=lambda path,*args,**kwargs:readings[str(path)]
        endpoint['os']=types.SimpleNamespace(geteuid=lambda:0)
        def open_device(path,flags):
            self.assertEqual(path,'/dev/kmsg');self.assertEqual(flags & os.O_ACCMODE,os.O_RDONLY)
            opened.append(path);return 123
        def write(fd,data):
            self.assertEqual(fd,1);event=json.loads(data);events.append(event)
            if after_heartbeat and event['event']=='heartbeat':readings[str(endpoint['DESCRIPTOR'])]=b'changed'
            return len(data)-1 if short_write else len(data)
        fake=types.SimpleNamespace(O_RDONLY=os.O_RDONLY,O_NONBLOCK=os.O_NONBLOCK,O_CLOEXEC=os.O_CLOEXEC,
            SEEK_END=os.SEEK_END,open=open_device,lseek=lambda *args:0,write=write,close=closed.append,
            read=lambda *args:b'inert kernel record')
        def select(read,write,error,timeout):
            now[0]+=timeout;return [],[],[]
        scope['os']=fake;scope['time']=types.SimpleNamespace(monotonic=lambda:now[0]);scope['select']=types.SimpleNamespace(select=select)
        try:exec(compile(ast.Module(body=tree.body[split:],type_ignores=[]),'logger-loop','exec'),scope)
        finally:self.remote_observed=(events,opened,closed)
        return events,opened,closed

    def test_actual_remote_reads_identity_and_only_kmsg(self):
        events,opened,closed=self.remote()
        self.assertEqual(opened,['/dev/kmsg']);self.assertEqual(closed,[123])
        self.assertEqual(events[0]['event'],'ready');self.assertEqual(events[-1]['event'],'terminal')
        self.assertTrue(all(e['identity']==D.WHO for e in events))

    def test_remote_duplicate_bundle_refused_before_kmsg(self):
        with self.assertRaisesRegex(ValueError,'bundle command line'):
            self.remote({'/proc/cmdline':b'rog5.bundle=fixture-production rog5.bundle=fixture-production'})
        self.assertEqual(self.remote_observed[1],[])

    def test_remote_descriptor_change_refused_before_kmsg(self):
        with self.assertRaisesRegex(ValueError,'descriptor changed'):
            self.remote({'/run/rog5-native-wifi/trial-descriptor':b'changed'})
        self.assertEqual(self.remote_observed[1],[])

    def test_remote_change_after_heartbeat_stops_without_terminal(self):
        with self.assertRaisesRegex(ValueError,'descriptor changed'):self.remote(after_heartbeat=True)
        events,_,closed=self.remote_observed
        self.assertFalse(any(e['event']=='terminal' for e in events));self.assertEqual(closed,[123])

    def test_remote_short_frame_fails_and_closes(self):
        with self.assertRaisesRegex(ValueError,'short logger frame'):self.remote(short_write=True)
        self.assertEqual(self.remote_observed[2],[123])

    def test_input_peer_not_reading_has_deadline(self):
        obj=self.create();clock=time.monotonic;offset=[0.0]
        obj_time=types.SimpleNamespace(monotonic=lambda:clock()+offset[0],sleep=time.sleep)
        original_write=os.write
        def blocked(fd,data):
            if obj.process is not None and obj.process.stdin is not None and fd==obj.process.stdin.fileno():
                offset[0]=9.0;raise BlockingIOError()
            return original_write(fd,data)
        with patch.object(self.m,'command',return_value=[sys.executable,'-I','-B','-c','import time;time.sleep(30)']), \
             patch.object(self.m,'time',obj_time),patch.object(self.m.os,'write',side_effect=blocked):
            with self.assertRaisesRegex(ValueError,'input deadline'):obj.start()
        self.assertTrue(obj.closed);self.assertIsNotNone(obj.process.returncode)

    def test_result_publication_failure_is_not_pass(self):
        obj=self.start();save=self.m.save
        def fail(path,value):
            if path.name=='result.json':raise OSError(28,'fixture disk full')
            return save(path,value)
        with patch.object(self.m,'save',side_effect=fail):result=obj.close()
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['child_reaped'])
        self.assertTrue(any(e['stage']=='result-publication' for e in result['cleanup_errors']))

    def test_unproven_group_cannot_pass(self):
        obj=self.create();stop=self.b.stop
        obj.stop=lambda pid,force:dict(stop(pid,force),group_absent=False)
        code="CASE='normal'\nDESCENDANT=''\n"+PEER
        with patch.object(self.m,'command',return_value=[sys.executable,'-I','-B','-c',code]):obj.start()
        result=obj.close();self.assertEqual(result['status'],'FAIL');self.assertFalse(result['group_absent'])

    def test_command_authority_unchanged(self):
        def command(path):return ast.dump(next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='command'))
        self.assertEqual(command(self.old),command(self.source))


if __name__=='__main__':unittest.main()
