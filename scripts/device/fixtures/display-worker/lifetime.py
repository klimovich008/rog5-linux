#!/usr/bin/env python3
"""Actual acceptance and execution; no device/credential/claim/root operations.

Reuse the preceding binding fixture with its documented actual-acceptance update.
Only real local Git repositories and inert Python children are executed. The
checked source loader and request expectations remain test inputs, not admission.
"""
import argparse
import base64
import concurrent.futures
import errno
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

P=argparse.ArgumentParser()
P.add_argument('--binding-test',type=Path,required=True)
P.add_argument('--case',action='append',default=[])
args,rest=P.parse_known_args()
sys.argv=[str(args.binding_test),*rest]
B=runpy.run_path(str(args.binding_test))
WORKER=B['WORKER'];PREFIX=B['PREFIX'];source_module=B['source_module']


class Focused(B['Binding']):
    def executor(self):return source_module(self.root/WORKER,'real_executor')
    def python(self,code):return [sys.executable,'-I','-S','-c',code]

    def reference(self):
        with patch.dict(os.environ,self.git_env,clear=True):
            return self.original_acceptance.source_identity(self.repo)

    def test_actual_acceptance_unbound_import_is_inert(self):
        with patch.object(subprocess,'Popen',side_effect=AssertionError('import invoked child')):
            fresh=source_module(self.root/(PREFIX+'release-acceptance.py'),'unbound_acceptance')
            self.assertRaisesRegex(ValueError,'reader absent',fresh.source_identity)
        self.assertEqual(fresh.source_identity.__defaults__,(self.repo,))
        self.assertFalse((self.repo/'configs/release-acceptance.json').exists())

    def test_actual_clean_dirty_staged_untracked_and_symlink_recipe(self):
        tracked=self.repo/'fixture.txt';tracked.write_bytes(b'one\n')
        self.git('add','fixture.txt')
        self.git('-c','user.name=Fixture','-c','user.email=fixture.invalid','commit','--quiet','--no-gpg-sign','-m','fixture')
        self.bind()
        self.assertEqual(self.a.source_identity(),self.reference())
        tracked.write_bytes(b'two\n')
        self.assertEqual(self.a.source_identity(),self.reference());self.assertFalse(self.a.source_identity()['clean'])
        self.git('add','fixture.txt');self.assertEqual(self.a.source_identity(),self.reference())
        (self.repo/'untracked space\nname').write_bytes(b'untracked\0bytes')
        (self.repo/'link').symlink_to('missing-target')
        self.assertEqual(self.a.source_identity(),self.reference())
        tracked.unlink();self.assertEqual(self.a.source_identity(),self.reference())
        self.assertEqual(self.events,[])

    def test_repository_default_and_reader_mutation_are_rejected(self):
        self.bind();original=self.a.source_identity.__defaults__
        self.a.source_identity.__defaults__=(self.root,)
        try:self.assertRaisesRegex(ValueError,'function changed',self.w.load_deployed)
        finally:self.a.source_identity.__defaults__=original
        with patch.object(self.a,'_SOURCE_READER',tuple([*self.a._SOURCE_READER])):
            self.assertRaisesRegex(ValueError,'reader changed',self.w.load_deployed)
        with patch.object(self.a,'REPO',self.root):self.assertRaisesRegex(ValueError,'repository binding',self.a.source_identity)
        self.assertRaisesRegex(ValueError,'cannot be rebound',self.a.bind_source_reader,lambda *a:None,self.loader)
        with patch.object(self.w,'_PIDFD_START','changed'):
            self.assertRaisesRegex(ValueError,'execution binding',self.w.load_deployed)

    def test_observable_change_between_actual_git_passes_is_refused(self):
        f=self.repo/'fixture';f.write_bytes(b'first')
        self.git('add','fixture');self.git('-c','user.name=Fixture','-c','user.email=fixture.invalid','commit','--quiet','--no-gpg-sign','-m','fixture')
        self.bind();calls=[]
        def change(argv,result):
            calls.append(argv)
            if len(calls)==4:f.write_bytes(b'changed')
        self.git_observer=change
        self.assertRaisesRegex(ValueError,'source changed during observation',self.a.source_identity)
        self.assertEqual(len(calls),8);self.assertEqual(self.events,[])

    def test_untracked_size_and_special_file_refusal(self):
        self.bind();f=self.repo/'large'
        with f.open('wb') as stream:stream.truncate(self.a._SOURCE_BYTES+1)
        self.assertRaisesRegex(ValueError,'byte bound',self.a.source_identity)
        f.unlink();os.mkfifo(f)
        # Git itself omits a FIFO; exercise the actual reader for a reported
        # path that has become special. Do not broaden Git's source inventory.
        self.assertRaisesRegex(ValueError,'regular file',self.a._source_untracked,self.repo,b'large',
                              [self.a._SOURCE_BYTES],time.monotonic()+3)

    def test_git_failure_and_output_hash_refusal(self):
        self.bind()
        def corrupt(argv,result):result['stdout_sha256']='0'*64
        self.git_observer=corrupt
        self.assertRaisesRegex(ValueError,'output bound/hash',self.a.source_identity)
        self.git_observer=lambda *args:None
        self.git('update-ref','-d','HEAD')
        self.assertRaisesRegex(ValueError,'Git command failed',self.a.source_identity)

    def test_git_output_bound_and_environment_are_explicit(self):
        self.bind();expected=self.a.source_identity()
        with patch.dict(os.environ,GIT_DIR=str(self.root/'foreign'),GIT_EXTERNAL_DIFF='/never-executed'):
            self.assertEqual(self.a.source_identity(),expected)
        p=self.repo/'large-diff';p.write_bytes(b'first\n');self.git('add','large-diff')
        self.git('-c','user.name=Fixture','-c','user.email=fixture.invalid','commit','--quiet','--no-gpg-sign','-m','fixture')
        p.write_bytes(b'x'*(2*1024**2)+b'\n')
        self.assertRaisesRegex(ValueError,'Git command failed',self.a.source_identity)

    def test_source_deadline_after_real_query(self):
        self.bind();clock=time.monotonic;expired=False
        def tick():return clock()+100 if expired else clock()
        def expire(*args):
            nonlocal expired
            expired=True
        self.git_observer=expire
        with patch.object(self.a.time,'monotonic',tick):
            self.assertRaisesRegex(ValueError,'source observation deadline',self.a.source_identity)

    def test_live_identity_changes_do_not_become_request_authority(self):
        self.bind();expected=self.request()
        (self.repo/'untracked-after-request').write_bytes(b'new input')
        result=self.w.perform(expected,self.d)
        self.assertEqual(result['status'],'FAIL');self.assertIn('host source changed',result['reason'])
        self.assertFalse(result['command_invoked']);self.assertEqual(self.events,[])

    def test_original_stale_numeric_signal_counterexample(self):
        old=source_module(self.before/'ssh-worker.py.txt','old_worker');old.HERE=self.root
        real=subprocess.Popen;children=[];attempts=[];interrupt=KeyboardInterrupt('after original reap')
        class Child(real):
            def communicate(child,*a,**kw):
                result=super().communicate(*a,**kw)
                if not children:
                    children.append(child)
                    self.assertEqual(child.returncode,0)
                    with self.assertRaises(ChildProcessError):os.waitpid(child.pid,os.WNOHANG)
                    raise interrupt
                return result
        def record(pgid,sig):attempts.append((pgid,sig,children[0].returncode))
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(subprocess,'Popen',Child),patch.object(os,'killpg',record):
            with self.assertRaises(KeyboardInterrupt) as caught:old.execute(self.python('pass'),'',3)
        self.assertIs(caught.exception,interrupt)
        self.assertEqual(attempts,[(children[0].pid,signal.SIGKILL,0)])
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def after_reap(self,kind):
        w=self.executor();real=subprocess.Popen;send=signal.pidfd_send_signal
        children=[];events=[];interrupt=kind('first cancellation after confirmed reap')
        class Child(real):
            def communicate(child,*a,**kw):
                result=super().communicate(*a,**kw);children.append(child)
                self.assertEqual(child.returncode,0)
                with self.assertRaises(ChildProcessError):os.waitpid(child.pid,os.WNOHANG)
                raise interrupt
        def signal_fd(fd,sig,info=None,flags=0):
            events.append((sig,flags,bool(children)))
            return send(fd,sig,info,flags)
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(subprocess,'Popen',Child),patch.object(signal,'pidfd_send_signal',signal_fd), \
             patch.object(os,'killpg',side_effect=AssertionError('numeric signal forbidden')):
            with self.assertRaises(kind) as caught:w.execute(self.python('pass'),'',3)
        self.assertIs(caught.exception,interrupt)
        self.assertIn((signal.SIGKILL,4,True),events)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_first_keyboardinterrupt_after_real_reap(self):self.after_reap(KeyboardInterrupt)
    def test_first_systemexit_after_real_reap(self):self.after_reap(SystemExit)

    def test_first_cancellation_after_cleanup_wait_is_safe(self):
        w=self.executor();real=subprocess.Popen;interrupt=KeyboardInterrupt('first cancellation after cleanup wait')
        calls=[]
        class Child(real):
            def wait(child,*a,**kw):
                result=super().wait(*a,**kw);calls.append(result)
                if len(calls)==2:raise interrupt
                return result
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(subprocess,'Popen',Child),patch.object(os,'killpg',side_effect=AssertionError('numeric signal')):
            with self.assertRaises(KeyboardInterrupt) as caught:w.execute(self.python('pass'),'',3)
        self.assertIs(caught.exception,interrupt);self.assertGreaterEqual(len(calls),3)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_unsupported_group_feature_refuses_before_payload_and_reaps_starter(self):
        w=self.executor();send=signal.pidfd_send_signal;created=[];real=subprocess.Popen
        path=self.root/'MUST_NOT_EXIST'
        def spawn(*a,**kw):
            child=real(*a,**kw);created.append(child);return child
        def unsupported(fd,sig,info=None,flags=0):
            if flags==4:raise OSError(errno.EINVAL,'inert unsupported group scope')
            return send(fd,sig,info,flags)
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(subprocess,'Popen',spawn),patch.object(signal,'pidfd_send_signal',unsupported):
            self.assertRaises(OSError,w.execute,self.python(f'open({str(path)!r},"w").write("bad")'),'',3)
        self.assertFalse(path.exists());self.assertIsNotNone(created[0].returncode)
        with self.assertRaises(ChildProcessError):os.waitpid(created[0].pid,os.WNOHANG)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_first_cancellation_before_payload_release_closes_inert_starter(self):
        w=self.executor();send=signal.pidfd_send_signal;cancel=KeyboardInterrupt('pidfd received; no GO yet')
        fired=[];target=self.root/'payload-marker'
        def inject(fd,sig,info=None,flags=0):
            if flags==4 and sig==0 and not fired:
                fired.append(True);raise cancel
            return send(fd,sig,info,flags)
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(signal,'pidfd_send_signal',inject):
            with self.assertRaises(KeyboardInterrupt) as caught:
                w.execute(self.python(f'open({str(target)!r},"w").write("bad")'),'',3)
        self.assertIs(caught.exception,cancel);self.assertFalse(target.exists())
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_original_cancellation_is_not_replaced_by_cleanup_error(self):
        w=self.executor();real=subprocess.Popen;send=signal.pidfd_send_signal
        cancel=KeyboardInterrupt('original after reap');done=[]
        class Child(real):
            def communicate(child,*a,**kw):
                super().communicate(*a,**kw);done.append(True);raise cancel
        def broken(fd,sig,info=None,flags=0):
            if sig==signal.SIGKILL and done:raise PermissionError('inert cleanup signal failure')
            return send(fd,sig,info,flags)
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(subprocess,'Popen',Child),patch.object(signal,'pidfd_send_signal',broken):
            with self.assertRaises(KeyboardInterrupt) as caught:w.execute(self.python('pass'),'',3)
        self.assertIs(caught.exception,cancel)
        self.assertIn('cleanup signal failure',' '.join(cancel.__notes__))
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_output_and_input_bounds_with_real_local_children(self):
        w=self.executor();before=set(os.listdir('/proc/self/fd'))
        result=w.execute(self.python('import os; os.write(1,b"x"*(1024*1024+1))'),'',3)
        self.assertLessEqual(len(base64.b64decode(result['stdout_base64'])),w.MAX_OUTPUT)
        payload='x'*w.MAX_INPUT
        result=w.execute(self.python('import sys; print(len(sys.stdin.buffer.read()))'),payload,3)
        self.assertEqual(base64.b64decode(result['stdout_base64']),str(len(payload)).encode()+b'\n')
        self.assertRaises(ValueError,w.execute,self.python('pass'),payload+'x',3)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))

    def test_monitoring_threads_do_not_use_python_preexec_or_signal_policy(self):
        w=self.executor();real=subprocess.Popen;calls=[]
        def spawn(*a,**kw):
            self.assertNotIn('preexec_fn',kw);calls.append(threading.get_ident());return real(*a,**kw)
        before={s:signal.getsignal(s) for s in (signal.SIGCHLD,signal.SIGINT,signal.SIGTERM)}
        with patch.object(subprocess,'Popen',spawn),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda n:w.execute(self.python(f'print({n})'),'',3),[1,2]))
        self.assertEqual([base64.b64decode(r['stdout_base64']) for r in results],[b'1\n',b'2\n'])
        self.assertTrue(all(t!=threading.get_ident() for t in calls))
        self.assertEqual(before,{s:signal.getsignal(s) for s in before})

    def descendants(self,cancel):
        # Only this separate inert test process becomes a subreaper, so orphan
        # grandchildren can be observed/reaped without relying on container PID1.
        # Production execute does not alter subreaper/SIGCHLD/process policy.
        script=r'''
import ctypes,os,sys,time,threading,json,types,subprocess,signal
from pathlib import Path
p=Path(sys.argv[1]);cancel=sys.argv[2]=='1';root=Path(sys.argv[3]);pidfile=root/'grandchild'
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(36,1,0,0,0):raise OSError(ctypes.get_errno(),'test subreaper')
w=types.ModuleType('worker');w.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),w.__dict__)
done=[];errors=[]
def reap():
    until=time.monotonic()+12
    while time.monotonic()<until:
        if pidfile.exists():
            try:pid=int(pidfile.read_text());got,status=os.waitpid(pid,os.WNOHANG)
            except (ChildProcessError,ValueError):pass
            else:
                if got:done.append(os.waitstatus_to_exitcode(status));return
        time.sleep(.005)
    errors.append('descendant not reaped')
t=threading.Thread(target=reap);t.start()
real=subprocess.Popen;interrupt=KeyboardInterrupt('after leader reap with descendant');reaped=[]
class Child(real):
    def communicate(self,*a,**kw):
        result=super().communicate(*a,**kw)
        try:os.waitpid(self.pid,os.WNOHANG)
        except ChildProcessError:reaped.append(True)
        if cancel:raise interrupt
        return result
subprocess.Popen=Child
code="import os,time\nfrom pathlib import Path\np=Path("+repr(str(pidfile))+")\npid=os.fork()\nif pid==0:\n p.write_text(str(os.getpid()))\n time.sleep(8)\nelse:\n while not p.exists():time.sleep(.005)\n os._exit(0)\n"
caught=None;result=None
try:result=w.execute([sys.executable,'-I','-S','-c',code],'',3)
except KeyboardInterrupt as e:caught=e
finally:t.join(13)
if errors or done!=[-signal.SIGKILL] or not reaped:raise ValueError((errors,done,reaped))
if cancel and caught is not interrupt:raise ValueError('original cancellation lost')
if not cancel and (result is None or result['returncode']!=0):raise ValueError('normal return absent')
print(json.dumps(dict(reaped=done,first_cancellation_preserved=caught is interrupt if cancel else None)))
'''
        reply=subprocess.run([sys.executable,'-I','-S','-c',script,str(self.root/WORKER),'1' if cancel else '0',str(self.root)],
                             capture_output=True,timeout=18)
        self.assertEqual(reply.returncode,0,reply.stderr.decode())
        self.assertEqual(json.loads(reply.stdout)['reaped'],[-signal.SIGKILL])

    def test_leader_exit_still_closes_remaining_descendant(self):self.descendants(False)
    def test_after_reap_cancellation_still_closes_remaining_descendant(self):self.descendants(True)


if __name__=='__main__':
    names=args.case or sorted(n for n in Focused.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Focused(n) for n in names))
    raise SystemExit(not result.wasSuccessful())
