#!/usr/bin/env python3
"""Focused first-cancellation finalization regressions; reuse the exact Owned fixture.

Actual publisher/controller/launcher/phase code; all external effects remain the
existing explicit inert fixtures. No private imports, device commands or signals.
"""
import argparse
import ast
from contextlib import nullcontext, contextmanager
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

p=argparse.ArgumentParser()
p.add_argument('--owned-test',type=Path,required=True)
p.add_argument('--case',action='append',default=[])
p.add_argument('--negative-control',action='store_true')
args,rest=p.parse_known_args()
if hashlib.sha256(args.owned_test.read_bytes()).hexdigest()!='12165e7bb9735aa4a29a48e1b2f8066bb7ce2008dfa236807b732c3b91db191a':
    raise ValueError('exact unchanged Owned fixture required')
sys.argv=[str(args.owned_test),*rest]
loaded=runpy.run_path(str(args.owned_test))
Owned=loaded['Owned'];b=loaded['b'];BOOT=loaded['BOOT'];OWNER=loaded['OWNER'];NS=loaded['NS']


class Finalization(Owned):
    def fault(self,kind,where='before-second',tamper=None,primary=False):
        self.injected=kind('first cancellation at publisher '+where)
        self.hits=[];self.close_calls=[];self.held_writer=None
        original=self.ad.ExpectationWriter.close
        assign=self.ad.ColdBoot.__setattr__
        primary_error=OSError('earlier non-cancellation publication error')
        def stop(writer):
            self.assertTrue(writer.closed);self.assertFalse(writer.bad)
            self.assertIsNone(writer.fd);self.assertIsNone(writer.parent)
            self.assertIsNotNone(writer.frozen)
            self.held_writer=writer;self.hits.append(where);self.only_fallback=True
            if tamper:tamper(writer)
            raise self.injected
        def close(writer):
            self.held_writer=writer
            self.close_calls.append((writer.closed,writer.bad))
            index=len(self.close_calls)
            if index==2 and where=='before-second':stop(writer)
            result=original(writer)
            if index==1 and primary:raise primary_error
            if index==2 and where=='after-second':stop(writer)
            return result
        def setting(obj,name,value):
            if obj is self.binding and name=='_publication' and value=='committed' and not self.hits:
                if where=='commit-after':assign(obj,name,value)
                if where in ('commit-before','commit-after'):stop(self.held_writer)
            return assign(obj,name,value)
        @contextmanager
        def before_finalizer():
            text=(self.base/b['AD']).read_text().splitlines()
            line,=[i for i,s in enumerate(text,1) if s.strip()=='if writer is not None:writer.close()']
            code=self.ad.ColdBoot.publish_expectation.__code__;previous=sys.gettrace()
            def trace(frame,event,arg):
                if frame.f_code is not code:return None
                if event=='line' and frame.f_lineno==line and not self.hits:stop(self.held_writer)
                return trace
            sys.settrace(trace)
            try:yield
            finally:sys.settrace(previous)
        return (patch.object(self.ad.ExpectationWriter,'close',close),
                patch.object(self.ad.ColdBoot,'__setattr__',setting),
                before_finalizer() if where=='finally-entry' else nullcontext())

    def check_failure(self,result,restored=True,primary=False):
        self.assertIsNotNone(result)
        self.assertEqual(result['status'],'FAIL')
        self.assertIs(result['selection_eligibility_restored'],restored)
        self.assertFalse(result['successor_running']);self.assertFalse(result['retry_permitted'])
        self.assertEqual(self.binding.selected_boot,BOOT)
        self.assertIsNone(self.binding._contract);self.assertFalse(self.binding._proved)
        self.assertIs(self.binding.publication_cancellation,self.injected)
        self.assertEqual(self.binding._publication,'failed')
        self.assertEqual(len(self.hits),1)
        self.assertTrue((self.c.OUTPUT/'result.json').exists())
        if restored:
            self.assertEqual([r['phase'] for r in result['errors']],['observe_target'])
            self.assertEqual(result['entered'].count('locate_fallback'),1)
            self.assertTrue(self.root_calls)
            failed=self.ad.publication_failure()
            self.assertEqual(failed['file'],self.held_writer.frozen)
            self.assertEqual(failed['file']['status'],'present')
            self.assertEqual(self.ad.selected_boot(),BOOT)
            self.assertTrue(self.binding.check())
        first=result['errors'][0]
        self.assertEqual(first['type'],'OSError' if primary else type(self.injected).__name__)
        if primary:self.assertIn('earlier non-cancellation',first['reason'])
        else:self.assertEqual(first['reason'],str(self.injected))
        for call in (self.binding.session_contract,lambda:self.binding.expected(BOOT,OWNER),
                     lambda:self.binding.script(BOOT),lambda:self.ad.ColdBoot(self.ad,self.g,OWNER),
                     lambda:self.binding.discovery(dict(boot_id=b['FALLBACK_BOOT'],**self.binding.target))):
            with self.assertRaises(ValueError):call()
        self.assertFalse(self.g.OUTPUT.exists())

    def exercise(self,kind,where='before-second',restored=True,tamper=None,primary=False,consumed=False):
        controller=self.build_driver();self.fallback()
        root=self.root_transport(self.transport)
        self.inner.health.transport=root;self.inner.fastboot.health.transport=root
        if consumed:
            def fail_boot(*a):raise OSError('inert boot ambiguity')
            self.inner.bindings['boot_once']=fail_boot
        before=set(os.listdir('/proc/self/fd'))
        a,c,d=self.fault(kind,where,tamper,primary)
        with a,c,d:
            with self.assertRaises(kind) as caught:controller.run()
        self.assertIs(caught.exception,self.injected)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))
        self.assertIn('close_capture',controller.results)
        result=controller.terminal_result
        if args.negative_control:
            self.assertEqual(self.close_calls,[(False,False),(True,False)])
            self.assertIsNone(result);self.assertIsNone(self.binding.publication_cancellation)
            self.assertFalse(controller.selection_restored)
            self.assertFalse((self.c.OUTPUT/'result.json').exists())
            self.assertFalse((self.c.OUTPUT/'production-boot-publication-failure.json').exists())
            return
        if consumed:
            self.assertEqual(result['status'],'FAIL');self.assertFalse(controller.selection_restored)
            self.assertEqual(result['entered'].count('locate_fallback'),1)
            self.assertIs(self.binding.publication_cancellation,self.injected)
            self.assertIsNone(self.binding._contract);self.assertEqual(self.ad.selected_boot(),BOOT)
            self.assertRaisesRegex(ValueError,'repeated phase',controller.restore_fallback)
        else:self.check_failure(result,restored,primary)
        return result

    def test_second_close_first_keyboardinterrupt(self):self.exercise(KeyboardInterrupt)
    def test_second_close_first_systemexit(self):self.exercise(SystemExit)
    def test_after_second_close_first_keyboardinterrupt(self):self.exercise(KeyboardInterrupt,'after-second')
    def test_first_cancellation_before_finalizer_call(self):self.exercise(KeyboardInterrupt,'finally-entry')
    def test_first_cancellation_before_commit(self):self.exercise(KeyboardInterrupt,'commit-before')
    def test_first_systemexit_after_commit_assignment(self):self.exercise(SystemExit,'commit-after')
    def test_original_io_failure_then_first_finalizer_cancellation(self):
        self.exercise(SystemExit,primary=True)

    def test_tampered_closed_snapshot_does_not_gain_witness(self):
        def tamper(writer):
            path=writer.path;other=path.with_suffix('.replacement')
            other.write_bytes(path.read_bytes());other.chmod(0o600);os.replace(other,path)
        self.exercise(KeyboardInterrupt,restored=False,tamper=tamper)
        self.assertFalse((self.c.OUTPUT/'production-boot-publication-failure.json').exists())
        self.assertRaises(ValueError,self.binding.check)

    def test_writer_closure_uncertainty_stays_refused(self):
        self.exercise(KeyboardInterrupt,restored=False,tamper=lambda writer:setattr(writer,'bad',True))
        self.assertFalse((self.c.OUTPUT/'production-boot-publication-failure.json').exists())

    def test_retention_without_witness_still_refuses_recovery(self):
        original=self.c.save
        def save(path,value):
            if Path(path).name=='production-boot-publication-failure.json':raise OSError('inert witness write failure')
            return original(path,value)
        with patch.object(self.c,'save',save):self.exercise(SystemExit,restored=False)
        self.assertIsNone(self.binding._failure_record)
        self.assertRaisesRegex(ValueError,'no committed fallback witness',self.binding.check)
        self.assertIn('witness write failure',' '.join(self.injected.__notes__))

    def test_cancelled_consumed_locate_is_not_retried(self):
        self.exercise(KeyboardInterrupt,restored=False,consumed=True)

    def launcher(self,kind):
        closed=[];claims=[];controllers=[]
        class Credentials:
            def __init__(self,path):self.started=b['time'].monotonic()
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def check(self):pass
        self.l.K=NS(Credentials=Credentials);self.l.ADMISSION_SHA='e'*64
        self.l.B=NS(PROFILE_ID='inert-not-a-claim',SERIAL='inert',CLAIMS=NS(consume=lambda *a:claims.append(1)),canonical=b['noop'])
        self.ad.PREP=NS(prior_and_staging=b['noop'],observe_fresh=lambda *a:'a'*64,verify_ready=b['noop'])
        self.ad.S=NS(process_identity=lambda pid:dict(uids=[1000]*4,start='inert'))
        def assemble(source,*,contract,owner):
            self.assertIs(contract,self.binding)
            inner=self.build_driver(create_controller=False);self.fallback()
            root=self.root_transport(self.transport)
            inner.health.transport=root;inner.fastboot.health.transport=root
            return inner,NS(close=lambda:closed.append('bridge'))
        original=self.c.Controller.run
        def run(controller):controllers.append(controller);return original(controller)
        a,c,d=self.fault(kind)
        before=set(os.listdir('/proc/self/fd'))
        with patch.object(self.g,'initialize',b['noop']),patch.object(self.ad,'assemble',assemble), \
             patch.object(self.ad,'qualification',lambda *a:'q'*64),patch.object(self.l,'registered_claim',lambda:dict(inert=True)), \
             patch.object(self.l,'pending_claim',b['noop']),patch.object(self.c.Controller,'run',run),a,c,d:
            with self.assertRaises(kind) as caught:self.l._run_once(contract=self.binding,owner=OWNER)
        self.assertIs(caught.exception,self.injected)
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))
        self.assertEqual(closed,['bridge']);self.assertEqual(claims,[1]);self.assertEqual(len(controllers),1)
        result=json.loads((self.l.LAUNCH/'result.json').read_bytes())
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['error']['type'],kind.__name__)
        self.assertIsNone(result['gpu_session']);self.check_failure(result['trial'])

    def test_launcher_second_close_keyboardinterrupt(self):self.launcher(KeyboardInterrupt)
    def test_launcher_second_close_systemexit(self):self.launcher(SystemExit)

    def test_changed_scope_is_only_publisher(self):
        tree=ast.parse((self.base/b['AD']).read_bytes())
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='publish_expectation')
        # Successful commitment must follow finalization inside the same handler.
        outer=next(n for n in method.body if isinstance(n,ast.Try))
        inner=next(n for n in outer.body if isinstance(n,ast.Try))
        self.assertTrue(inner.finalbody)
        self.assertIn("self._publication = 'committed'",ast.unparse(outer.body[-1]))
        self.assertFalse(outer.finalbody)
        self.assertRaisesRegex(ValueError,'unresolved source dependency',self.g.initialize,self.ad)


if __name__=='__main__':
    names=(['test_second_close_first_keyboardinterrupt','test_second_close_first_systemexit']
           if args.negative_control else args.case or sorted(n for n in Finalization.__dict__ if n.startswith('test_')))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Finalization(n) for n in names))
    raise SystemExit(not result.wasSuccessful())
