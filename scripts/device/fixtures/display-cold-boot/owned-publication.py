#!/usr/bin/env python3
"""Focused creator-FD/cancellation tests on actual proposed source definitions.

No private top-level imports, target commands, real claim, credentials or root.
Use the unchanged 28-case base fixture; do not substitute recovery/phase methods.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import sys
import unittest
from unittest.mock import patch

p=argparse.ArgumentParser()
p.add_argument('--base-test',type=Path,required=True)
p.add_argument('--case',action='append',default=[])
args,rest=p.parse_known_args()
if hashlib.sha256(args.base_test.read_bytes()).hexdigest()!='55d3a192fa8425c58f35ecc47825964e1d8c5256cc69e58784b9c8b0e9f0dee6':
    raise ValueError('exact unchanged base fixture required')
sys.argv=[str(args.base_test),*rest]
b=runpy.run_path(str(args.base_test))
BOOT=b['BOOT'];OWNER=b['OWNER'];SOURCE=b['SOURCE_BOOT'];NS=b['NS'];sha=b['sha']


class Owned(b['Integration']):
    def fallback(self):
        def stage(context,results,pin):
            self.ad.authorize('stage_fallback',context,results,pin,contract=self.binding,owner=OWNER)
            proof=results['locate_fallback']
            self.c.same_identity(proof['identity'],self.c.FALLBACK,excluded=(SOURCE,BOOT))
            return dict(status='PASS',identity=proof['identity'],ram_files_verified=True)
        def restore(context,results,pin):
            self.ad.authorize('restore_fallback_state',context,results,pin,contract=self.binding,owner=OWNER)
            return dict(status='PASS',identity=results['locate_fallback']['identity'],completed=True,
                        before_sha256=self.binding.states['pending'],after_sha256=self.binding.states['old'])
        self.inner.bindings['stage_fallback']=stage;self.inner.bindings['restore_fallback_state']=restore

    def root_transport(self,ordinary):
        self.root_calls=[]
        def root(phase,context,results,pin,request,deployed):
            if request['mode']=='linklocal':
                index=f'{len(self.root_calls):03}'
                prefix=phase+'-root-ssh-'+index
                candidate=dict(format='rog5-fallback-route-command-v1',phase=phase,context=context,
                               intent_sha256=pin,command=request)
                path=self.c.OUTPUT/(prefix+'-request.json');self.a.save_transport(path,candidate)
                digest=sha(path.read_bytes())
                self.c.save(self.c.OUTPUT/(prefix+'-entered.json'),dict(intent_sha256=pin,request_sha256=digest))
                envelope=dict(format='rog5-root-fallback-launch-v1',request=dict(
                    phase=phase,context=context,index=index,request_sha256=digest))
                # Actual root entrypoint definitions, UID1000. Only the original
                # fixture's common()/custody/process authentication is inert.
                self.ad.authorize_transport(envelope,{},candidate)
                self.root_calls.append((envelope,candidate))
            return ordinary(phase,context,results,pin,request,deployed)
        return root

    def faults(self,mode,kind=OSError,tamper=None):
        self.hits=[];self.held=None;self.writer_fd=None
        original_open=os.open;original_write=os.write;original_sync=os.fsync
        injected=kind('injected owned publication '+mode)
        self.injected=injected
        def stop():
            self.hits.append(mode);self.only_fallback=True
            if tamper:tamper()
            raise injected
        def opening(path,flags,*a,**kw):
            if str(path)=='production-boot-binding.json' and flags & os.O_EXCL:
                if mode=='before':stop()
                if mode=='signal-open':
                    self.hits.append(mode);self.only_fallback=True
                    signal.raise_signal(signal.SIGINT)
                fd=original_open(path,flags,*a,**kw);self.writer_fd=fd;self.held=os.fstat(fd)
                return fd
            return original_open(path,flags,*a,**kw)
        first=True
        def write(fd,data):
            nonlocal first
            if fd==self.writer_fd and not self.hits:
                if mode in ('partial','signal') and first:
                    first=False;return original_write(fd,data[:17])
                if mode in ('partial','empty'):stop()
                if mode=='zero':
                    self.hits.append(mode);self.only_fallback=True;return 0
                if mode=='signal':
                    self.only_fallback=True;self.hits.append(mode)
                    signal.raise_signal(signal.SIGINT)
                if mode=='complete':
                    original_write(fd,data);stop()
            return original_write(fd,data)
        def sync(fd):
            if self.writer_fd is not None and not self.hits:
                if mode=='file-sync' and fd==self.writer_fd:stop()
                if mode=='parent-sync' and stat.S_ISDIR(os.fstat(fd).st_mode):stop()
            return original_sync(fd)
        return (patch.object(os,'open',opening),patch.object(os,'write',write),patch.object(os,'fsync',sync))

    def exercise(self,mode,kind=OSError,tamper=None):
        controller=self.build_driver();self.fallback()
        root=self.root_transport(self.transport)
        self.inner.health.transport=root;self.inner.fastboot.health.transport=root
        before=set(os.listdir('/proc/self/fd'));mask=signal.pthread_sigmask(signal.SIG_BLOCK,[])
        a,c,d=self.faults(mode,kind,tamper)
        caught=None
        with a,c,d:
            try:result=controller.run()
            except (KeyboardInterrupt,SystemExit) as error:caught=error;result=controller.terminal_result
        self.assertEqual(before,set(os.listdir('/proc/self/fd')))
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK,[]),mask)
        self.assertEqual(len(self.hits),1,result);self.assertEqual(self.binding.selected_boot,BOOT)
        self.assertIsNone(self.binding._contract);self.assertFalse(self.binding._proved)
        self.assertEqual(result['status'],'FAIL');self.assertFalse(result['successor_running'])
        self.assertLessEqual(controller.entered.count('locate_fallback'),1)
        if kind is not OSError:
            self.assertIs(caught,self.binding.publication_cancellation)
            if mode not in ('signal','signal-open'):self.assertIs(caught,self.injected)
        elif self.binding.publication_cancellation is not None:self.assertIs(caught,self.binding.publication_cancellation)
        else:self.assertIsNone(caught)
        return result

    def recovered(self,mode,kind=OSError):
        result=self.exercise(mode,kind)
        self.assertTrue(result['selection_eligibility_restored'],result)
        self.assertEqual(self.controller.entered.count('locate_fallback'),1)
        self.assertTrue(self.root_calls);self.assertEqual(self.ad.selected_boot(),BOOT)
        failed=self.ad.publication_failure()
        self.assertEqual(failed['format'],'rog5-production-boot-publication-failure-v2')
        snapshot=failed['file']
        if mode=='before':self.assertEqual(snapshot,dict(status='absent'))
        else:
            path=self.c.OUTPUT/'production-boot-binding.json'
            self.assertEqual(path.stat().st_ino,self.held.st_ino)
            expected=self.ad.publication_bytes(failed['expectation'])
            self.assertEqual(path.read_bytes(),expected[:path.stat().st_size])
            if mode in ('partial','signal'):self.assertEqual(path.stat().st_size,17)
            if mode in ('empty','zero','signal-open'):self.assertEqual(path.stat().st_size,0)
        for call in (self.binding.session_contract,lambda:self.binding.expected(BOOT,OWNER),
                     lambda:self.binding.script(BOOT),lambda:self.ad.ColdBoot(self.ad,self.g,OWNER),
                     lambda:self.binding.discovery(dict(boot_id=b['FALLBACK_BOOT'],**self.binding.target))):
            with self.assertRaises(ValueError):call()
        self.assertFalse(self.g.OUTPUT.exists())

    def test_before_create_oserror(self):self.recovered('before')
    def test_empty_creator_oserror(self):self.recovered('empty')
    def test_owned_partial_oserror(self):self.recovered('partial')
    def test_complete_write_oserror(self):self.recovered('complete')
    def test_file_sync_oserror(self):self.recovered('file-sync')
    def test_parent_sync_oserror(self):self.recovered('parent-sync')
    def test_before_create_keyboardinterrupt(self):self.recovered('before',KeyboardInterrupt)
    def test_owned_partial_keyboardinterrupt(self):self.recovered('partial',KeyboardInterrupt)
    def test_complete_write_keyboardinterrupt(self):self.recovered('complete',KeyboardInterrupt)
    def test_owned_partial_systemexit(self):self.recovered('partial',SystemExit)
    def test_actual_default_sigint_after_prefix(self):
        self.assertIs(signal.getsignal(signal.SIGINT),signal.default_int_handler)
        self.recovered('signal',KeyboardInterrupt)

    def test_zero_progress_owned_write(self):self.recovered('zero')
    def test_real_sigint_during_exclusive_creation(self):self.recovered('signal-open',KeyboardInterrupt)

    def test_interrupt_after_full_write_and_both_syncs(self):
        original=self.ad.ExpectationWriter.write
        def write(writer):
            original(writer)
            self.hits.append('after-write');self.only_fallback=True;raise self.injected
        with patch.object(self.ad.ExpectationWriter,'write',write):self.recovered('after-write',KeyboardInterrupt)

    def test_interrupt_after_descriptor_closure(self):
        original=self.ad.ExpectationWriter.close
        def close(writer):
            original(writer)
            if not self.hits:
                self.hits.append('after-close');self.only_fallback=True;raise self.injected
        with patch.object(self.ad.ExpectationWriter,'close',close):self.recovered('after-close',KeyboardInterrupt)

    def test_unknown_prefix_replacement_is_not_owned(self):
        foreign=b'foreign unknown file\n'
        def replace():
            path=self.c.OUTPUT/'production-boot-binding.json';other=path.with_suffix('.foreign')
            other.write_bytes(foreign);other.chmod(0o600);os.replace(other,path)
        result=self.exercise('partial',tamper=replace)
        self.assertFalse(result['selection_eligibility_restored'])
        self.assertEqual((self.c.OUTPUT/'production-boot-binding.json').read_bytes(),foreign)
        self.assertFalse((self.c.OUTPUT/'production-boot-publication-failure.json').exists())

    def test_owned_prefix_modified_before_failure_refuses(self):
        def modify():
            path=self.c.OUTPUT/'production-boot-binding.json'
            with path.open('r+b') as f:f.write(b'!')
        result=self.exercise('partial',tamper=modify)
        self.assertFalse(result['selection_eligibility_restored'])
        self.assertFalse((self.c.OUTPUT/'production-boot-publication-failure.json').exists())

    def test_forged_empty_path_without_creator_refuses(self):
        def create():
            path=self.c.OUTPUT/'production-boot-binding.json'
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
        result=self.exercise('before',tamper=create)
        self.assertFalse(result['selection_eligibility_restored'])
        self.assertFalse((self.c.OUTPUT/'production-boot-publication-failure.json').exists())

    def test_partial_changed_after_witness_is_not_recaptured(self):
        self.recovered('partial')
        path=self.c.OUTPUT/'production-boot-binding.json'
        with path.open('ab') as f:f.write(b'!')
        self.assertRaises(ValueError,self.ad.publication_failure)
        self.assertRaises(ValueError,self.binding.check)

    def test_second_cancellation_during_witness_does_not_lose_first(self):
        original=self.c.save
        def save(path,value):
            if Path(path).name=='production-boot-publication-failure.json':raise KeyboardInterrupt('second cancellation')
            return original(path,value)
        with patch.object(self.c,'save',save):result=self.exercise('partial',KeyboardInterrupt)
        self.assertFalse(result['selection_eligibility_restored'])
        self.assertIn('second cancellation',' '.join(self.injected.__notes__))

    def test_cancellation_during_io_failure_recording_is_not_swallowed(self):
        original=self.c.save;cancel=KeyboardInterrupt('cancel while recording io failure')
        def save(path,value):
            if Path(path).name=='production-boot-publication-failure.json':raise cancel
            return original(path,value)
        with patch.object(self.c,'save',save):result=self.exercise('partial')
        self.assertIs(self.binding.publication_cancellation,cancel)
        self.assertFalse(result['selection_eligibility_restored'])
        self.assertEqual(result['errors'][0]['type'],'OSError')

    def test_cancellation_in_consumed_locate_never_retries(self):
        controller=self.build_driver();self.fallback()
        def failed_boot(*a):raise OSError('inert boot ambiguity')
        self.inner.bindings['boot_once']=failed_boot
        a,c,d=self.faults('partial',KeyboardInterrupt)
        with a,c,d:
            with self.assertRaises(KeyboardInterrupt) as caught:controller.run()
        self.assertIs(caught.exception,self.injected)
        result=controller.terminal_result
        self.assertEqual(result['status'],'FAIL');self.assertFalse(result['selection_eligibility_restored'])
        self.assertEqual(controller.entered.count('locate_fallback'),1)
        self.assertEqual(self.ad.selected_boot(),BOOT);self.assertIsNone(self.binding._contract)
        self.assertRaisesRegex(ValueError,'repeated phase',controller.restore_fallback)

    def test_secondary_diagnostic_failure_preserves_cancellation(self):
        original=self.c.save;observer=self.restoration_raw
        def bad_proof(boot,role,purpose='verify-restored'):
            return observer(boot,role,purpose).replace(b'physical_guards_passed=true',b'physical_guards_passed=false')
        def save(path,value):
            if Path(path).name=='restoration-failure.json':raise OSError('injected restoration diagnostic failure')
            return original(path,value)
        with patch.object(self,'restoration_raw',bad_proof),patch.object(self.c,'save',save):
            result=self.exercise('partial',KeyboardInterrupt)
        self.assertFalse(result['selection_eligibility_restored'])
        self.assertIn('restoration diagnostic failure',' '.join(self.injected.__notes__))
        self.assertTrue((self.c.OUTPUT/'result.json').exists())

    def test_entered_only_discovery_is_not_no_selection(self):
        controller=self.build_driver();self.fallback();ordinary=self.transport
        def interrupt(phase,context,results,pin,request,deployed):
            if phase=='observe_target':
                self.only_fallback=True;raise OSError('inert lost discovery result')
            return ordinary(phase,context,results,pin,request,deployed)
        root=self.root_transport(interrupt)
        self.inner.health.transport=root;self.inner.fastboot.health.transport=root
        result=controller.run()
        self.assertEqual(result['status'],'FAIL');self.assertFalse(result['selection_eligibility_restored'])
        self.assertIsNone(self.binding.selected_boot)
        self.assertTrue((self.c.OUTPUT/'observe_target-discovery-000-entered.json').exists())
        self.assertFalse((self.c.OUTPUT/'observe_target-discovery-000-transport.json').exists())
        self.assertRaisesRegex(ValueError,'unfinished target discovery',self.ad.selected_boot)
        self.assertNotIn('stage_fallback',controller.entered)
        # Initial read-only fallback discovery can pass. It is not a mutation.
        self.assertTrue(self.root_calls)

    def test_root_reader_complete_without_witness_is_only_exclusion(self):
        self.recovered('complete',KeyboardInterrupt)
        witness=self.c.OUTPUT/'production-boot-publication-failure.json';witness.unlink()
        self.assertEqual(self.ad.selected_boot(),BOOT)
        self.assertIsNone(self.ad.publication_failure())
        self.assertRaises(ValueError,self.binding.check)
        self.assertRaises(ValueError,self.binding.session_contract)
        envelope,candidate=self.root_calls[0]
        modified=dict(envelope,request=dict(envelope['request'],phase='stage_target_recovery'))
        self.assertRaisesRegex(ValueError,'root transport phase',self.ad.authorize_transport,modified,{},candidate)
        modified=dict(envelope,request=dict(envelope['request'],index='invalid'))
        self.assertRaises(ValueError,self.ad.authorize_transport,modified,{},candidate)

    def test_same_byte_witness_replacement_reader_vs_owner(self):
        self.recovered('partial')
        path=self.c.OUTPUT/'production-boot-publication-failure.json';other=path.with_suffix('.replacement')
        original=self.ad.publication_failure()
        other.write_bytes(path.read_bytes());other.chmod(0o600);os.replace(other,path)
        self.assertEqual(self.ad.publication_failure(),original)
        self.assertEqual(self.ad.selected_boot(),BOOT)
        self.assertRaisesRegex(ValueError,'retained publication failure witness',self.binding.check)
        self.assertRaises(ValueError,self.binding.session_contract)

    def test_launcher_records_failure_cleans_and_reraises_original(self):
        api=self;closed=[];claims=[];controllers=[]
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
            return inner,NS(close=lambda:closed.append('bridge'))
        original_run=self.c.Controller.run
        def run(controller):controllers.append(controller);return original_run(controller)
        a,c,d=self.faults('partial',KeyboardInterrupt)
        with patch.object(self.g,'initialize',b['noop']),patch.object(self.ad,'assemble',assemble), \
             patch.object(self.ad,'qualification',lambda *a:'q'*64),patch.object(self.l,'registered_claim',lambda:dict(inert=True)), \
             patch.object(self.l,'pending_claim',b['noop']),patch.object(self.c.Controller,'run',run),a,c,d:
            with self.assertRaises(KeyboardInterrupt) as caught:self.l._run_once(contract=self.binding,owner=OWNER)
        self.assertIs(caught.exception,self.injected);self.assertEqual(closed,['bridge']);self.assertEqual(claims,[1])
        result=json.loads((self.l.LAUNCH/'result.json').read_bytes())
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['error']['type'],'KeyboardInterrupt')
        self.assertTrue(result['trial']['selection_eligibility_restored'])
        self.assertEqual(len(controllers),1);self.assertIsNone(result['gpu_session'])
        self.assertIsNone(self.binding._contract);self.assertFalse(self.g.OUTPUT.exists())

    def test_unchanged_effectful_save_and_authority_gates(self):
        import ast
        groups={b['C']:('save','same_identity'),b['AD']:('common','claim','authorize_transport','capture_launch_authorize'),
                b['L']:('registered_claim','pending_claim','record','close_owned')}
        for file,names in groups.items():
            old=ast.parse(self.sections[file]);new=ast.parse((self.base/file).read_bytes())
            for name in names:
                def node(tree):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
                self.assertEqual(ast.dump(node(old)),ast.dump(node(new)),(file,name))
        self.assertRaisesRegex(ValueError,'unresolved source dependency',self.g.initialize,self.ad)
        self.assertEqual(set(self.g.PATHS),set(self.ad.PRODUCTION_PATHS))


if __name__=='__main__':
    names=args.case or sorted(n for n in Owned.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Owned(n) for n in names))
    raise SystemExit(not result.wasSuccessful())
