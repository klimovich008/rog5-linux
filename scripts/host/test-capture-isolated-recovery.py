#!/usr/bin/env python3
"""R01 capture boundaries on loopback and synthetic USB; no device access."""
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

SPEC=importlib.util.spec_from_file_location('isolated_capture',Path(__file__).with_name('capture-isolated-recovery.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
BOOT='12345678-1234-4abc-8def-1234567890ab'
RETURN_BOOT='87654321-4321-4abc-8def-1234567890ab'
INITIAL='7.1.4-negative'
RETURN=dict(bundle='fixture-rescue',release='7.1.4-rescue',manifest_sha256='a'*64)


def frame(boot=BOOT,release=INITIAL,sequence=1,stage='switch-root',state='PASS'):
    return (f'format=rog5-persistent-root-stage-v2\ntarget_release={release}\nboot_id={boot}\n'
            f'sequence={sequence}\nstage={stage}\nstate={state}\ndetail=none\n').encode()


def startup(boot=BOOT,release=INITIAL,sequence=1):
    return (f'format=rog5-startup-observation-v1\ntarget_release={release}\nboot_id={boot}\n'
            f'sequence={sequence}\nunit=sshd\nobservation=present\nactive=active\nsub=running\n'
            'result=success\nexit=0\njournal=present\nfailure_hex=none\n').encode()


class CaptureTest(unittest.TestCase):
    def receiver(self,events=None,**kwargs):
        return M.Receiver(INITIAL,(events if events is not None else []).append,
                          host='127.0.0.1',port=0,peer='127.0.0.1',return_identity=RETURN,**kwargs)

    def initial(self,receiver):
        receiver.transport('target',None)
        receiver.record(frame(),'127.0.0.1')

    def returning(self,receiver):
        self.initial(receiver)
        receiver.transport('absent',None)
        receiver.transport('recovery',None)
        receiver.transport('absent',None)
        receiver.transport('target',None)

    def test_two_boots_with_explicit_absence_and_fixed_return_identity(self):
        for first in (frame,startup):
            events=[]
            with self.subTest(first=first.__name__),self.receiver(events) as receiver:
                self.returning(receiver)
                receiver.record(first(RETURN_BOOT,RETURN['release']),'127.0.0.1')
                receiver.record(frame(RETURN_BOOT,RETURN['release'],2),'127.0.0.1')
                self.assertFalse(receiver.failed)
                self.assertTrue(receiver.return_seen)
                self.assertEqual(receiver.initial_boot,BOOT)
                self.assertEqual(receiver.last.boot_id,RETURN_BOOT)
                self.assertEqual(sum(e['event']=='recovery-disconnected' for e in events),1)
                observed=[e for e in events if e['event']=='recovery-boot-observed']
                self.assertEqual(len(observed),1)
                self.assertIs(observed[0]['authenticated'],False)

    def test_startup_first_preserves_initial_boot(self):
        with self.receiver() as receiver:
            receiver.transport('target',None)
            receiver.record(startup(),'127.0.0.1')
            self.assertEqual(receiver.initial_boot,BOOT)
            self.assertFalse(receiver.return_read_allowed())
            receiver.record(frame(),'127.0.0.1')
            self.assertTrue(receiver.return_read_allowed())

    def test_return_requires_positive_absence(self):
        for mode in ('target','enumerating','recovery','fastboot'):
            with self.subTest(mode=mode),self.receiver() as receiver:
                self.initial(receiver)
                receiver.transport(mode,None)
                receiver.transport('target',None)
                receiver.record(frame(RETURN_BOOT,RETURN['release']),'127.0.0.1')
                self.assertTrue(receiver.failed)
                self.assertFalse(receiver.return_seen)

    def test_early_disconnect_cannot_arm_return(self):
        for payload in (None,startup(),frame(stage='overlay'),frame(state='FAIL')):
            with self.subTest(payload=payload),self.receiver() as receiver:
                receiver.transport('target',None)
                if payload:receiver.record(payload,'127.0.0.1')
                receiver.transport('absent',None)
                self.assertTrue(receiver.failed)
                self.assertFalse(receiver.return_pending)

    def test_same_boot_wrong_kernel_and_malformed_return_refused(self):
        for payload in (frame(BOOT,RETURN['release']),frame(RETURN_BOOT,INITIAL),b'bad\n'):
            with self.subTest(payload=payload),self.receiver() as receiver:
                self.returning(receiver)
                receiver.record(payload,'127.0.0.1')
                self.assertTrue(receiver.failed)
                self.assertFalse(receiver.return_seen)
                self.assertEqual(receiver.release,INITIAL)

    def test_untrusted_peer_does_not_transition(self):
        with self.receiver() as receiver:
            self.returning(receiver)
            receiver.record(frame(RETURN_BOOT,RETURN['release']),'127.0.0.2')
            self.assertFalse(receiver.return_seen)
            self.assertFalse(receiver.failed)
            receiver.record(frame(RETURN_BOOT,RETURN['release']),'127.0.0.1')
            self.assertTrue(receiver.return_seen)

    def test_earlier_failure_is_never_cleared(self):
        with self.receiver() as receiver:
            self.returning(receiver)
            receiver.record(b'invalid\n','127.0.0.1')
            receiver.record(frame(RETURN_BOOT,RETURN['release']),'127.0.0.1')
            self.assertTrue(receiver.failed)

    def test_return_boot_stays_single_and_ordered(self):
        for failure in ('boot','sequence','disconnect','enumerating-disconnect'):
            with self.subTest(failure=failure),self.receiver() as receiver:
                self.returning(receiver)
                receiver.record(frame(RETURN_BOOT,RETURN['release'],2),'127.0.0.1')
                if failure=='boot':receiver.record(frame(BOOT,RETURN['release'],3),'127.0.0.1')
                elif failure=='sequence':receiver.record(frame(RETURN_BOOT,RETURN['release'],1),'127.0.0.1')
                else:
                    if failure=='enumerating-disconnect':receiver.transport('enumerating',None)
                    receiver.transport('absent',None)
                self.assertTrue(receiver.failed)

    def test_transport_switch_closes_old_accepted_connections(self):
        with self.receiver() as receiver:
            self.initial(receiver)
            with socket.create_connection(receiver.listener.getsockname()) as client:
                receiver.poll(.01)
                old=list(receiver.clients)
                self.assertEqual(len(old),1)
                receiver.transport('absent',None)
                self.assertFalse(receiver.clients)
                self.assertEqual(old[0].fileno(),-1)

    def test_tagged_teardown_only_after_completed_initial_root(self):
        for operation in sorted(M.USB_READ_OPERATIONS):
            events=[]
            with self.subTest(operation=operation),self.receiver(events) as receiver:
                self.initial(receiver)
                error=M.UsbReadDisappeared(OSError(errno.ENODEV,'fixture'),operation)
                route=Mock(return_value=True)
                with patch.object(M,'usb_mode',side_effect=[error,('enumerating',None),('absent',None)]), \
                     patch.object(M.time,'sleep') as sleep:
                    M.update_transport(receiver,'fixture',route,deadline=time.monotonic()+1)
                self.assertFalse(receiver.failed)
                self.assertTrue(receiver.return_pending)
                self.assertEqual(receiver.mode,'absent')
                event=next(e for e in events if e['event']=='recovery-discovery-interrupted')
                self.assertEqual(event['removal_rechecks'],1)
                self.assertLessEqual(sum(call.args[0] for call in sleep.call_args_list),.15)
                route.assert_not_called()

    def test_teardown_never_masks_other_failures_or_extends_deadline(self):
        for case in ('permission','untagged','unknown-operation','unresolved','mismatch','network',
                     'bind','expired','prior-failure','returned'):
            events=[]
            with self.subTest(case=case),self.receiver(events) as receiver:
                self.initial(receiver)
                error=M.UsbReadDisappeared(OSError(errno.ENOENT,'fixture'),'net-driver')
                if case=='permission':error=M.UsbReadDisappeared(OSError(errno.EACCES,'fixture'),'net-driver')
                if case=='untagged':error=OSError(errno.ENODEV,'fixture')
                if case=='unknown-operation':error=M.UsbReadDisappeared(OSError(errno.ENOENT,'fixture'),'unknown')
                if case=='prior-failure':receiver.failed=True
                if case=='returned':
                    receiver.transport('absent',None);receiver.transport('target',None)
                    receiver.record(frame(RETURN_BOOT,RETURN['release']),'127.0.0.1')
                following='enumerating' if case=='unresolved' else 'mismatch' if case=='mismatch' else 'absent'
                discovery=[error]+[(following,None)]*5
                route=Mock(return_value=True)
                bind=receiver.transport
                if case=='network':
                    discovery=[('target',None),('absent',None)];route.side_effect=error
                if case=='bind':
                    discovery=[('target',None),('absent',None)]
                    def bind(mode,interface):
                        if mode=='target':raise error
                        return type(receiver).transport(receiver,mode,interface)
                deadline=time.monotonic()+(-1 if case=='expired' else 1)
                with patch.object(M,'usb_mode',side_effect=discovery),patch.object(M.time,'sleep'), \
                     patch.object(receiver,'transport',side_effect=bind):
                    M.update_transport(receiver,'fixture',route,deadline=deadline)
                self.assertTrue(receiver.failed)
                self.assertTrue(any(e['event']=='transport-check-failed' for e in events))

    def test_identity_and_mode_are_explicit(self):
        for identity in (None,{},dict(RETURN,release=INITIAL),dict(RETURN,bundle=1),
                         dict(RETURN,manifest_sha256='0'*64),dict(RETURN,extra='value')):
            with self.subTest(identity=identity),self.assertRaises(ValueError):
                M.Receiver(INITIAL,lambda e:None,return_identity=identity,host='127.0.0.1',port=0)
        with self.assertRaises(ValueError):self.receiver(source_boot_id=BOOT)
        M.check_capture_mode(dict(return_identity=RETURN),None,RETURN)
        for receipt,source,identity in (({},None,RETURN),({},None,None),
                (dict(return_identity=RETURN,source_boot_id=BOOT),BOOT,RETURN)):
            with self.assertRaises(ValueError):M.check_capture_mode(receipt,source,identity)

    def test_manifest_is_bounded_regular_and_canonical(self):
        raw=b'bundle=fixture-rescue\ntarget_release=7.1.4-rescue\n'
        canonical=dict(qualification='isolated-failure-r01',execution='fastboot-boot-ram-bundle',
                       fallback_bundle='fixture-rescue',fallback_manifest_sha256=hashlib.sha256(raw).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/'manifest';manifest.write_bytes(raw)
            self.assertEqual(M.return_manifest(manifest,canonical),dict(RETURN,manifest_sha256=hashlib.sha256(raw).hexdigest()))
            for key,value in (('qualification','other'),('execution','fastboot-boot-selector-trial'),
                              ('fallback_manifest_sha256','0'*64),('fallback_bundle','other')):
                with self.subTest(key=key),self.assertRaises(ValueError):
                    M.return_manifest(manifest,dict(canonical,**{key:value}))
            link=Path(tmp)/'link';link.symlink_to(manifest)
            with self.assertRaises(OSError):M.return_manifest(link,canonical)
            for changed in (b'',b'x'*4097,raw+b'bundle=fixture-rescue\n',b'not-a-field\n',
                            b'bundle=fixture-rescue\ntarget_release=bad release\n'):
                manifest.write_bytes(changed)
                with self.subTest(changed=changed[:80]),self.assertRaises(ValueError):
                    M.return_manifest(manifest,dict(canonical,fallback_manifest_sha256=hashlib.sha256(changed).hexdigest()))

    def test_main_refuses_wrong_topology_before_network_or_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);primary=root/'primary';fallback=root/'fallback'
            primary.write_bytes(b'target_release=7.1.4-negative\nrollback_timeout=900\n')
            fallback.write_bytes(b'bundle=fixture-rescue\ntarget_release=7.1.4-rescue\n')
            record=dict(qualification='isolated-failure-r01',execution='fastboot-boot-ram-bundle',
                        fallback_bundle='fixture-rescue',serial='fixture',
                        fallback_manifest_sha256=hashlib.sha256(fallback.read_bytes()).hexdigest(),
                        manifest_sha256=hashlib.sha256(primary.read_bytes()).hexdigest())
            for mode in ('mismatch','target','absent','recovery'):
                with self.subTest(mode=mode),patch.object(sys,'argv',['capture','--profile','fixture',
                    '--manifest',str(primary),'--return-manifest',str(fallback),'--output',str(root/'capture')]), \
                    patch.object(M.os,'geteuid',return_value=0),patch.object(M.CLAIMS,'expected_record',
                    return_value=''.join(f'{k}={v}\n' for k,v in record.items()).encode()), \
                    patch.object(M,'usb_mode',return_value=(mode,None)),patch.object(M.NETWORK,'prepared') as network, \
                    self.assertRaisesRegex(ValueError,'exact fastboot'):
                    M.main()
                network.assert_not_called()
                self.assertFalse((root/'capture').exists())

    def test_live_readiness_binds_both_producers_return_and_time_budget(self):
        canonical=dict(qualification='isolated-failure-r01',execution='fastboot-boot-ram-bundle',
                       candidate='fixture-negative',fallback_bundle=RETURN['bundle'],
                       fallback_manifest_sha256=RETURN['manifest_sha256'])
        raw=''.join(f'{key}={value}\n' for key,value in canonical.items()).encode()
        timing=json.loads((M.REPO/'configs/release-acceptance.json').read_text())['defaults']['rescue_capture']
        required=timing['target_rollback_seconds']+timing['recovery_seconds']+timing['cleanup_seconds']
        with tempfile.TemporaryDirectory() as tmp,self.receiver() as receiver:
            output=Path(tmp)
            receipt=dict(profile='fixture',canonical_record=canonical,source={'fixture':True},
                         receiver_sha256=hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),
                         framework_sha256=hashlib.sha256(Path(M.BASE.__file__).read_bytes()).hexdigest(),
                         host_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                         pid=os.getpid(),process_start=M.process_start(os.getpid()),probe='PROBE test\n',
                         return_identity=RETURN,required_seconds=required,timing=timing,
                         deadline_monotonic=time.monotonic()+required+30)
            def write(value):
                (output/'receipt.json').write_text(json.dumps(value))
            write(receipt)
            with patch.object(M.CLAIMS,'expected_record',return_value=raw), \
                 patch.object(M.ACCEPTANCE,'source_identity',return_value={'fixture':True}), \
                 patch.object(M,'host_ready'),patch.object(M,'ADDRESS','127.0.0.1'), \
                 patch.object(M,'PORT',receiver.listener.getsockname()[1]):
                # A real loopback challenge proves this is a live process reply.
                receiver.probe=receipt['probe'].encode()
                live=dict(ready=True,candidate=canonical['candidate'],pid=os.getpid(),
                          required_seconds=required,remaining_seconds=required+20,
                          source_boot_id=None,return_identity=RETURN)
                receiver.probe_response=lambda:live
                stop=threading.Event()
                def poll():
                    while not stop.is_set():receiver.poll(.01)
                worker=threading.Thread(target=poll);worker.start()
                try:
                    result=M.check_receiver(output,'fixture',return_identity=RETURN)
                    self.assertEqual(result['status'],'PASS')
                    self.assertEqual(result['authority'],'none')
                    for key,value in (('ready',False),('return_identity',dict(RETURN,bundle='other')),
                                      ('candidate','other'),('pid',-1),('required_seconds',1)):
                        previous=live[key];live[key]=value
                        with self.subTest(live=key),self.assertRaisesRegex(ValueError,'not ready'):
                            M.check_receiver(output,'fixture',return_identity=RETURN)
                        live[key]=previous
                finally:stop.set();worker.join(2)
                self.assertFalse(worker.is_alive())
                # Corrupted receipts must fail before a socket is opened.
                for key,value in (('receiver_sha256','0'*64),('framework_sha256','0'*64),
                    ('process_start','wrong'),('host_boot_id',BOOT),('source',{}),
                    ('canonical_record',{}),('required_seconds',1),('timing',{}),
                    ('return_identity',dict(RETURN,bundle='other'))):
                    write(dict(receipt,**{key:value}))
                    with self.subTest(receipt=key),patch.object(M.socket,'socket') as client, \
                         self.assertRaises(ValueError):
                        M.check_receiver(output,'fixture',return_identity=RETURN)
                    client.assert_not_called()
                changed=dict(RETURN,manifest_sha256='b'*64)
                write(dict(receipt,return_identity=changed))
                with self.assertRaisesRegex(ValueError,'canonical fallback'):
                    M.check_receiver(output,'fixture',return_identity=changed)


if __name__=='__main__':unittest.main()
