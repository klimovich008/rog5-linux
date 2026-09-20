#!/usr/bin/env python3
"""Actual execute() finalization, not a duplicate lifecycle implementation.

Most cases use inert process/socket/signal adapters with real owned temporary
files and /dev/null descriptors. Two targeted cases use harmless local children
and the existing pidfd starter. No private import, credential, network or device.
"""
import argparse
import array
import ast
import base64
from collections import Counter
import errno
import hashlib
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest

P=argparse.ArgumentParser()
P.add_argument('--before',type=Path,required=True)
P.add_argument('--after',type=Path,required=True)
P.add_argument('--negative-control',action='store_true')
P.add_argument('--case',action='append',default=[])
ARGS=P.parse_args()
OLD_SHA='44382acd27a4a5da05d933dd4779496d8a49b7e135900202d8931bb20998ea69'
NS=types.SimpleNamespace

def need(ok,why):
    if not ok:raise ValueError(why)

def fdset():return set(os.listdir('/proc/self/fd'))

def actual(path,root,**overrides):
    tree=ast.parse(path.read_bytes())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute'
           or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in
           ('_PIDFD_START','PIDFD_SIGNAL_PROCESS_GROUP') for t in n.targets)]
    ns=dict(array=array,base64=base64,hashlib=hashlib,os=os,signal=signal,socket=socket,
            subprocess=subprocess,sys=sys,tempfile=tempfile,time=time,HERE=root,
            MAX_INPUT=3*1024**2,MAX_OUTPUT=1024**2,need=need)
    ns.update(overrides)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns['execute']


class Inert:
    """Faults surround actual close/read calls; raw fd numbers are never signals."""
    def __init__(self,root,mode='success',faults=None,body=None,extras=0,reuse=False):
        self.root=root;self.mode=mode;self.body=body;self.faults=faults or {};self.reuse=reuse
        self.before=fdset();self.events=[];self.calls=Counter();self.files=[]
        self.raw=[os.open('/dev/null',os.O_RDONLY|os.O_CLOEXEC) for _ in range(1+extras)]
        self.owned=set(self.raw);self.replacements=[];self.reaped=False;self.released=False
        self.timeout=subprocess.TimeoutExpired(['inert-no-command'],5)
        self.parent=self.Endpoint(self,'parent');self.child=self.Endpoint(self,'child')
        self.stdin=self.Endpoint(self,'stdin');self.proc=self.Process(self)

    def operation(self,label,operation):
        self.calls[label]+=1;index=self.calls[label];self.events.append((label,index))
        fault=self.faults.get((label,index))
        if fault is not None and not fault[1]:raise fault[0]
        result=operation()
        if fault is not None and fault[1]:raise fault[0]
        return result

    class Endpoint:
        def __init__(self,f,name):self.f=f;self.name=name;self.closed=False
        def fileno(self):return 23456
        def settimeout(self,*a):pass
        def close(self):return self.f.operation(self.name+'.close',lambda:setattr(self,'closed',True))
        def recvmsg(self,*a):
            return b'P',[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',self.f.raw).tobytes())],0,None
        def send(self,raw):
            need(raw==b'G','inert release byte');self.f.released=True;return 1

    class Output:
        def __init__(self,f,name):
            self.f=f;self.name=name;self.stream=tempfile.TemporaryFile(dir=f.root)
        def __enter__(self):return self
        def __exit__(self,*a):self.close()
        def close(self):return self.f.operation(self.name+'.close',self.stream.close)
        def seek(self,*a):return self.f.operation(self.name+'.seek',lambda:self.stream.seek(*a))
        def read(self,*a):return self.f.operation(self.name+'.read',lambda:self.stream.read(*a))

    class Process:
        pid=12345
        def __init__(self,f):self.f=f;self.stdin=f.stdin;self.returncode=None
        def communicate(self,*a,**kw):
            self.stdin.close()
            self.f.files[0].stream.write(b'out');self.f.files[1].stream.write(b'err')
            if self.f.mode=='timeout':raise self.f.timeout
            if self.f.body is not None:raise self.f.body
            self.returncode=0;self.f.reaped=True
        def wait(self,*a,**kw):
            def waited():self.returncode=0;self.f.reaped=True;return 0
            return self.f.operation('group.wait',waited)

    def output(self,**kw):
        name='stdout' if not self.files else 'stderr'
        def opened():
            value=self.Output(self,name);self.files.append(value);return value
        return self.operation(name+'.open',opened)

    def popen(self,*a,**kw):
        need(kw['start_new_session'] is True and 'preexec_fn' not in kw,'child lifetime interface')
        need(kw['stdout'] is self.files[0] and kw['stderr'] is self.files[1],'output ownership')
        return self.operation('spawn',lambda:self.proc)

    def signaling(self,fd,sig,info,flags):
        need(fd==self.raw[0] and fd in self.owned,'signal after raw descriptor release')
        os.fstat(fd);self.events.append(('group.signal',int(sig)))
        if sig==0 and self.reaped:raise ProcessLookupError()

    def raw_close(self,fd):
        need(fd in self.raw,'unexpected raw descriptor close')
        def closed():
            need(fd in self.owned,'raw close was retried')
            os.close(fd);self.owned.remove(fd)
            if self.reuse and fd==self.raw[0]:
                replacement=os.open('/dev/null',os.O_RDONLY|os.O_CLOEXEC)
                need(replacement==fd,'fixture requires immediate fd reuse')
                self.replacements.append(replacement)
        return self.operation('pidfd.close',closed)

    def invoke(self,path):
        function=actual(path,self.root,
            os=NS(pidfd_open=lambda *a:None,close=self.raw_close),
            signal=NS(SIGKILL=signal.SIGKILL,pidfd_send_signal=self.signaling),
            subprocess=NS(Popen=self.popen,PIPE=subprocess.PIPE,TimeoutExpired=subprocess.TimeoutExpired),
            tempfile=NS(TemporaryFile=self.output),
            socket=NS(socketpair=lambda:(self.parent,self.child),CMSG_SPACE=socket.CMSG_SPACE,
                MSG_CMSG_CLOEXEC=socket.MSG_CMSG_CLOEXEC,SOL_SOCKET=socket.SOL_SOCKET,SCM_RIGHTS=socket.SCM_RIGHTS,
                MSG_CTRUNC=socket.MSG_CTRUNC,MSG_TRUNC=socket.MSG_TRUNC))
        self.result=self.caught=None
        try:
            try:self.result=function(['inert-no-command'],'',5)
            except BaseException as error:self.caught=error
            self.after=fdset();self.raw_left=set(self.owned)
            self.replacement_open=all(os.fstat(fd) for fd in self.replacements)
            return self
        finally:
            # Only the fixture's own uncertain/leaked descriptors are repaired.
            for fd in self.owned|set(self.replacements):os.close(fd)
            for value in self.files:
                if not value.stream.closed:value.stream.close()
            need(fdset()==self.before,'fixture final descriptor imbalance')


class Finalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 required; do not run as root')
        need(hashlib.sha256(ARGS.before.read_bytes()).hexdigest()==OLD_SHA,'exact preceding worker required')
        cls.temp=tempfile.TemporaryDirectory(prefix='worker-finalization-',dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)

    def run_case(self,mode='success',faults=None,body=None,**kw):
        return Inert(self.root,mode,faults,body,**kw).invoke(ARGS.after)

    def complete(self,f):
        self.assertTrue(f.reaped)
        for name in ('parent','child','stdin','stderr','stdout'):
            self.assertGreaterEqual(f.calls[name+'.close'],1,name)
        self.assertEqual(f.calls['pidfd.close'],len(f.raw));self.assertFalse(f.raw_left)
        self.assertEqual(f.after,f.before)
        first=next(i for i,row in enumerate(f.events) if row[0]=='pidfd.close')
        self.assertFalse(any(row[0]=='group.signal' for row in f.events[first:]))

    def test_negative_control_success_final_close_leaks(self):
        error=KeyboardInterrupt('old-success-close')
        f=Inert(self.root,faults={('parent.close',1):(error,True)}).invoke(ARGS.before)
        self.assertIs(f.caught,error);self.assertIsNone(f.result)
        self.assertEqual(f.calls['pidfd.close'],0);self.assertEqual(f.raw_left,set(f.raw))

    def test_negative_control_handled_timeout_swallows_cancellation(self):
        error=KeyboardInterrupt('old-timeout-close')
        f=Inert(self.root,'timeout',{('parent.close',1):(error,True)}).invoke(ARGS.before)
        self.assertIsNone(f.caught);self.assertTrue(f.result['timed_out']);self.assertFalse(f.raw_left)
        self.assertIn('old-timeout-close',' '.join(f.timeout.__notes__))

    def test_baseline_success_and_handled_timeout(self):
        for mode in ('success','timeout'):
            with self.subTest(mode=mode):
                f=self.run_case(mode);self.complete(f);self.assertIsNone(f.caught)
                self.assertIs(f.result['timed_out'],mode=='timeout')
                self.assertEqual(base64.b64decode(f.result['stdout_base64']),b'out')
                self.assertEqual(base64.b64decode(f.result['stderr_base64']),b'err')
                self.assertEqual(f.result['stdout_sha256'],hashlib.sha256(b'out').hexdigest())

    def test_each_final_closer_after_success_or_handled_timeout(self):
        for mode in ('success','timeout'):
            for label,index in (('parent',1),('child',2),('stdin',2),('pidfd',1),('stderr',1),('stdout',1)):
                for kind in (KeyboardInterrupt,SystemExit,OSError):
                    with self.subTest(mode=mode,closer=label,kind=kind.__name__):
                        error=kind('first-'+label)
                        f=self.run_case(mode,{(label+'.close',index):(error,True)})
                        self.complete(f);self.assertIs(f.caught,error);self.assertIsNone(f.result)
                        if mode=='timeout':self.assertIn('Handled command timeout',' '.join(error.__notes__))

    def test_propagating_error_precedes_all_later_closer_errors(self):
        for original_kind in (KeyboardInterrupt,SystemExit,OSError):
            for closer_kind in (KeyboardInterrupt,SystemExit,OSError):
                for label,index in (('parent',1),('child',2),('stdin',2),('pidfd',1),('stderr',1),('stdout',1)):
                    with self.subTest(original=original_kind.__name__,closer=label,kind=closer_kind.__name__):
                        original=original_kind('body-original');late=closer_kind('late-'+label)
                        faults={(label+'.close',index):(late,True)}
                        if label!='stdout':faults[('stdout.close',1)]=(OSError('late-output'),True)
                        f=self.run_case(faults=faults,body=original)
                        self.complete(f);self.assertIs(f.caught,original);self.assertIsNone(f.result)
                        notes=' '.join(original.__notes__)
                        self.assertIn(type(late).__name__+': late-'+label,notes)
                        if label!='stdout':self.assertIn('late-output',notes)

    def test_first_finalizer_error_wins_over_all_later_errors(self):
        for mode in ('success','timeout'):
            for kind in (KeyboardInterrupt,SystemExit,OSError):
                first=kind('first-parent');second=KeyboardInterrupt('second-child');third=SystemExit('third-pidfd')
                faults={('parent.close',1):(first,True),('child.close',2):(second,True),
                        ('stdin.close',2):(OSError('stdin-late'),True),('pidfd.close',1):(third,True),
                        ('stderr.close',1):(OSError('stderr-late'),True),('stdout.close',1):(OSError('stdout-late'),True)}
                with self.subTest(mode=mode,kind=kind.__name__):
                    f=self.run_case(mode,faults);self.complete(f);self.assertIs(f.caught,first)
                    notes=' '.join(first.__notes__)
                    for text in ('second-child','third-pidfd','stdin-late','stderr-late','stdout-late'):self.assertIn(text,notes)

    def test_timeout_output_read_or_seek_error_is_the_actual_failure(self):
        for mode in ('success','timeout'):
            for name in ('stdout.seek','stderr.seek','stdout.read','stderr.read'):
                for kind in (KeyboardInterrupt,SystemExit,OSError):
                    with self.subTest(mode=mode,operation=name,kind=kind.__name__):
                        error=kind('output-original');late=OSError('final-late')
                        f=self.run_case(mode,{(name,1):(error,False),('parent.close',1):(late,True)})
                        self.complete(f);self.assertIs(f.caught,error);self.assertIsNone(f.result)
                        self.assertIn('final-late',' '.join(error.__notes__))
                        if mode=='timeout':self.assertIn('Handled command timeout',' '.join(error.__notes__))

    def test_timeout_cleanup_failure_does_not_become_successful_timeout(self):
        for kind in (KeyboardInterrupt,SystemExit,OSError):
            with self.subTest(kind=kind.__name__):
                first=kind('cleanup-original');second=OSError('later-wait')
                f=self.run_case('timeout',{('group.wait',1):(first,True),('group.wait',2):(second,True),
                                           ('parent.close',1):(OSError('later-close'),True)})
                self.complete(f);self.assertIs(f.caught,first);self.assertIsNone(f.result)
                notes=' '.join(first.__notes__)
                for text in ('later-wait','later-close','Handled command timeout'):self.assertIn(text,notes)

    def test_output_allocation_failure_still_attempts_owned_output_close(self):
        for kind in (KeyboardInterrupt,SystemExit,OSError):
            error=kind('second-output-open');late=SystemExit('first-output-close')
            f=self.run_case(faults={('stderr.open',1):(error,False),('stdout.close',1):(late,True)})
            self.assertIs(f.caught,error);self.assertEqual(f.calls['stdout.close'],1)
            self.assertEqual(f.calls['spawn'],0);self.assertIn('first-output-close',' '.join(error.__notes__))
            # No handoff occurred: this raw descriptor still belongs to the fixture.
            self.assertEqual(f.raw_left,set(f.raw))

    def test_raw_after_close_exception_does_not_close_reused_descriptor(self):
        for kind in (KeyboardInterrupt,SystemExit,OSError):
            error=kind('after-raw-close')
            f=self.run_case(faults={('pidfd.close',1):(error,True)},reuse=True)
            self.assertIs(f.caught,error);self.assertEqual(f.calls['pidfd.close'],1)
            self.assertFalse(f.raw_left);self.assertTrue(f.replacement_open)
            self.assertEqual(f.calls['stderr.close'],1);self.assertEqual(f.calls['stdout.close'],1)

    def test_raw_before_close_exception_is_not_retried_or_reported_success(self):
        for kind in (KeyboardInterrupt,SystemExit,OSError):
            error=kind('uncertain-raw-close')
            f=self.run_case(faults={('pidfd.close',1):(error,False),('stderr.close',1):(OSError('later-file'),True)})
            self.assertIs(f.caught,error);self.assertIsNone(f.result);self.assertEqual(f.calls['pidfd.close'],1)
            self.assertEqual(f.raw_left,set(f.raw));self.assertEqual(f.calls['stdout.close'],1)
            self.assertIn('later-file',' '.join(error.__notes__))

    def test_unexpected_received_descriptors_are_all_attempted(self):
        error=KeyboardInterrupt('first-raw-extra-handoff')
        f=self.run_case(faults={('pidfd.close',1):(error,True)},extras=1)
        self.assertIsInstance(f.caught,ValueError);self.assertIn('handoff',str(f.caught))
        self.assertFalse(f.released);self.complete(f)
        self.assertIn('first-raw-extra-handoff',' '.join(f.caught.__notes__))

    def test_output_closure_does_not_replace_already_propagating_output_error(self):
        original=OSError('output-read-original');first=KeyboardInterrupt('stderr-final');last=SystemExit('stdout-final')
        f=self.run_case('timeout',{('stdout.read',1):(original,False),('stderr.close',1):(first,True),('stdout.close',1):(last,True)})
        self.complete(f);self.assertIs(f.caught,original);self.assertIsNone(f.result)
        for text in ('stderr-final','stdout-final','Handled command timeout'):self.assertIn(text,' '.join(original.__notes__))

    def test_only_execute_changes_and_group_lifecycle_stays_exact(self):
        old=ast.parse(ARGS.before.read_bytes());new=ast.parse(ARGS.after.read_bytes())
        get=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
        left,right=get(old),get(new)
        for name in ('left','group','close_group'):
            find=lambda tree:next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(find(left)),ast.dump(find(right)),name)
        old.body.remove(left);new.body.remove(right)
        self.assertEqual(ast.dump(old),ast.dump(new))
        self.assertNotIn('killpg',ast.unparse(right).split('"""')[-1])

    def real_case(self,timed_out):
        baseline=fdset();error=KeyboardInterrupt('real-parent-final-close');processes=[];raw_closes=[]
        pair=socket.socketpair;popen=subprocess.Popen
        class Parent:
            def __init__(self,s):self.s=s;self.fired=False
            def __getattr__(self,key):return getattr(self.s,key)
            def close(self):
                self.s.close()
                if not self.fired:self.fired=True;raise error
        def sockets():
            a,b=pair();return Parent(a),b
        def spawn(*a,**kw):
            need('preexec_fn' not in kw and kw['start_new_session'] is True,'threaded spawn invariant')
            value=popen(*a,**kw);processes.append(value);return value
        def close(fd):raw_closes.append(fd);os.close(fd)
        def proxy(module,**overrides):
            values=dict(vars(module));values.update(overrides);return NS(**values)
        fn=actual(ARGS.after,self.root,os=proxy(os,close=close),socket=proxy(socket,socketpair=sockets),
                  subprocess=proxy(subprocess,Popen=spawn))
        code='import time;time.sleep(5)' if timed_out else 'pass'
        with self.assertRaises(KeyboardInterrupt) as caught:fn([sys.executable,'-I','-S','-c',code],'',1 if timed_out else 5)
        self.assertIs(caught.exception,error);self.assertEqual(len(processes),1)
        self.assertIsNotNone(processes[0].returncode);self.assertEqual(len(raw_closes),1)
        self.assertEqual(fdset(),baseline)
        with self.assertRaises(ChildProcessError):os.waitpid(processes[0].pid,os.WNOHANG)
        if timed_out:self.assertIn('Handled command timeout',' '.join(error.__notes__))

    def test_real_inert_success_then_final_parent_cancellation(self):self.real_case(False)
    def test_real_inert_timeout_then_final_parent_cancellation(self):self.real_case(True)


if __name__=='__main__':
    names=ARGS.case or unittest.defaultTestLoader.getTestCaseNames(Finalization)
    if ARGS.negative_control:names=[n for n in names if n.startswith('test_negative_control_')]
    outcome=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Finalization(n) for n in names))
    raise SystemExit(not outcome.wasSuccessful())
