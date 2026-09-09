#!/usr/bin/env python3
"""Small passive receiver regressions; no phone, credentials or host networking."""
import importlib.util
from pathlib import Path
import socket
import json
import hashlib
import errno
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('receiver', Path(__file__).with_name('headless-stage-receiver.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

BOOT = '12345678-1234-4abc-8def-1234567890ab'

def frame(sequence=1, boot=BOOT):
    return (f'format=rog5-persistent-root-stage-v2\ntarget_release=7.1.4-g359318de534f\n'
            f'boot_id={boot}\nsequence={sequence}\nstage=switch-root\nstate=PASS\ndetail=none\n').encode()


class ReceiverTest(unittest.TestCase):
    def test_driver_symlink_disappearance_waits_for_actual_device_removal(self):
        # S04: cdc_ncm's driver link vanished before the USB parent. The
        # original untagged resolve error failed capture; absence followed
        # 100 ms later. Reproduce the actual filesystem operation here.
        fixture=json.loads((M.REPO/'tests/fixtures/persistent-root/s04-usb-driver-teardown.json').read_text())
        self.assertEqual(fixture['original_capture_result'],'FAIL')
        self.assertEqual(fixture['immediate_recheck'],'enumerating')
        self.assertEqual(fixture['errno'],errno.ENOENT)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);device=root/'device';device.mkdir()
            usb=root/'usb';usb.symlink_to(device,target_is_directory=True)
            for name,value in (('idVendor','1d6b'),('idProduct','0104'),
                               ('product','ROG5 persistent root')):
                (device/name).write_text(value)
            interface=device/'1-1.2:1.0';interface.mkdir()
            driver=root/'cdc_ncm';driver.mkdir()
            (interface/'driver').symlink_to(driver,target_is_directory=True)
            net=root/'net'/M.INTERFACE;net.mkdir(parents=True)
            (net/'device').symlink_to(interface,target_is_directory=True)
            original_path=M.Path;original_resolve=Path.resolve;removed=False
            def mapped_path(value):
                return root/'net' if value=='/sys/class/net' else original_path(value)
            def disappearing(path,*args,**kwargs):
                nonlocal removed
                if path==net/'device/driver' and not removed:
                    (interface/'driver').unlink();removed=True
                return original_resolve(path,*args,**kwargs)
            def finish_removal(_seconds):
                if usb.is_symlink():usb.unlink()
            events=[]
            with M.Receiver('fixture',events.append,host='127.0.0.1',port=0,
                            source_boot_id=BOOT) as receiver:
                receiver.transport('source',None)
                route=unittest.mock.Mock(return_value=True)
                with patch.object(M,'USB',usb),patch.object(M,'ANCHOR',str(device)), \
                     patch.object(M,'Path',mapped_path),patch.object(Path,'resolve',disappearing), \
                     patch.object(M.time,'sleep',finish_removal):
                    M.update_transport(receiver,'fixture',route)
                self.assertFalse(receiver.failed)
                self.assertTrue(receiver.source_disconnected)
                self.assertEqual(receiver.mode,'absent')
                event=next(e for e in events if e['event']=='usb-discovery-interrupted')
                self.assertEqual(event['operation'],'net-driver')
                self.assertEqual(event['errno'],errno.ENOENT)
                self.assertEqual(event['removal_rechecks'],1)
                route.assert_not_called()

    def test_link_removal_classification_never_admits_unresolved_or_lost_target(self):
        for operation in ('usb-anchor','net-device','net-driver'):
            for seen,number,following in ((False,errno.ENOENT,'absent'),
                    (False,errno.ENODEV,'absent'),(True,errno.ENOENT,'absent'),
                    (False,errno.EACCES,'absent'),(False,errno.ENOENT,'enumerating'),
                    (False,errno.ENOENT,'mismatch'),(False,errno.ENOENT,'target')):
                with self.subTest(operation=operation,seen=seen,number=number,following=following), \
                     M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0) as receiver:
                    if seen:receiver.transport('target',None)
                    error=M.UsbReadDisappeared(OSError(number,'fixture'),operation)
                    with patch.object(M,'usb_mode',side_effect=[error]+[(following,None)]*5), \
                         patch.object(M.time,'sleep'):
                        M.update_transport(receiver,'fixture',lambda:True)
                    self.assertEqual(receiver.failed,seen or number==errno.EACCES or following!='absent')
                    self.assertFalse(receiver.target_seen and not seen)


    def test_ordinary_reboot_ignores_source_until_observed_disconnect(self):
        events=[]
        with M.Receiver('7.1.4-g359318de534f',events.append,host='127.0.0.1',port=0,
                        peer='127.0.0.1',source_boot_id=BOOT) as receiver:
            route=unittest.mock.Mock(return_value=True)
            with patch.object(M,'usb_mode',return_value=('target',None)):
                M.update_transport(receiver,'fixture',route)
            route.assert_called_once()
            self.assertEqual(receiver.mode,'source')
            self.assertFalse(receiver.target_seen)
            receiver.record(frame(),'127.0.0.1')
            self.assertIsNone(receiver.last)
            with patch.object(M,'usb_mode',return_value=('absent',None)):
                M.update_transport(receiver,'fixture',route)
            self.assertTrue(receiver.source_disconnected)
            with patch.object(M,'usb_mode',return_value=('target',None)):
                M.update_transport(receiver,'fixture',route)
            self.assertEqual(route.call_count,2)
            other='87654321-4321-4abc-8def-1234567890ab'
            receiver.record(frame(1,other),'127.0.0.1')
            self.assertEqual(receiver.last.boot_id,other)
            self.assertFalse(receiver.failed)

    def test_prepared_source_route_is_not_reprobed_during_expected_teardown(self):
        fixture=json.loads((M.REPO/'tests/fixtures/persistent-root/ordinary-source-nmcli-teardown.json').read_text())
        self.assertEqual(fixture['original_capture_result'],'FAIL')
        self.assertEqual(fixture['phase'],'network-setup')
        with M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0,source_boot_id=BOOT) as receiver:
            route=unittest.mock.Mock(return_value=True)
            with patch.object(M,'usb_mode',return_value=('target',None)):
                M.update_transport(receiver,'fixture',route)
            route.assert_called_once()
            # The source is already routed. A later NetworkManager lookup can
            # race its orderly disconnect, so no setup call belongs here.
            route.side_effect=RuntimeError(fixture['reason'])
            with patch.object(M,'usb_mode',return_value=('target',None)):
                for _ in range(20):M.update_transport(receiver,'fixture',route)
            self.assertEqual(route.call_count,1)
            self.assertEqual(receiver.mode,'source')
            self.assertFalse(receiver.failed or receiver.target_seen or receiver.source_disconnected)
            with patch.object(M,'usb_mode',return_value=(fixture['observed_mode'],None)):
                M.update_transport(receiver,'fixture',route)
            self.assertTrue(receiver.source_disconnected)
            self.assertFalse(receiver.failed)
            route.side_effect=None
            with patch.object(M,'usb_mode',return_value=('target',None)):
                M.update_transport(receiver,'fixture',route)
            self.assertEqual(route.call_count,2)
            self.assertTrue(receiver.target_seen)

    def test_ordinary_source_route_pending_never_admits_source_or_disconnect(self):
        with M.Receiver('7.1.4-g359318de534f',lambda e:None,host='127.0.0.1',port=0,
                        peer='127.0.0.1',source_boot_id=BOOT) as receiver:
            route=unittest.mock.Mock(side_effect=[False,True])
            with patch.object(M,'usb_mode',return_value=('target',None)):
                M.update_transport(receiver,'fixture',route)
                self.assertEqual(receiver.mode,'enumerating')
                self.assertFalse(receiver.target_seen or receiver.source_disconnected or receiver.failed)
                M.update_transport(receiver,'fixture',route)
            self.assertEqual(route.call_count,2)
            self.assertEqual(receiver.mode,'source')
            receiver.record(frame(),'127.0.0.1')
            self.assertIsNone(receiver.last)
            self.assertFalse(receiver.target_seen or receiver.source_disconnected or receiver.failed)

    def test_ordinary_source_route_failure_is_permanent_and_single_attempt(self):
        for following in ('target','mismatch'):
            with self.subTest(following=following), M.Receiver('fixture',lambda e:None,
                    host='127.0.0.1',port=0,source_boot_id=BOOT) as receiver:
                route=unittest.mock.Mock(side_effect=RuntimeError('fixture route failure'))
                with patch.object(M,'usb_mode',side_effect=[('target',None),(following,None)]):
                    M.update_transport(receiver,'fixture',route)
                route.assert_called_once()
                self.assertTrue(receiver.failed)
                self.assertFalse(receiver.target_seen or receiver.source_disconnected)
                self.assertEqual(receiver.mode,'enumerating' if following=='target' else 'mismatch')
                if following=='target':
                    with patch.object(M,'usb_mode',return_value=('target',None)):
                        M.update_transport(receiver,'fixture',lambda:True)
                    self.assertEqual(receiver.mode,'source')
                    self.assertTrue(receiver.failed)

    def test_ordinary_reboot_cannot_accept_old_boot_after_disconnect(self):
        with M.Receiver('7.1.4-g359318de534f',lambda e:None,host='127.0.0.1',port=0,
                        peer='127.0.0.1',source_boot_id=BOOT) as receiver:
            receiver.transport('source',None)
            receiver.transport('absent',None)
            receiver.transport('target',None)
            receiver.record(frame(),'127.0.0.1')
            self.assertTrue(receiver.failed)
            self.assertIsNone(receiver.last)

    def test_ordinary_reboot_missing_disconnect_is_not_inferred(self):
        with M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0,source_boot_id=BOOT) as receiver:
            receiver.transport('source',None)
            receiver.transport('recovery',None)
            self.assertTrue(receiver.failed)
            self.assertFalse(receiver.source_disconnected)

    def test_capture_mode_must_be_requested_explicitly(self):
        with self.assertRaisesRegex(ValueError,'capture mode'):
            M.check_capture_mode({'source_boot_id':BOOT},None)
        with self.assertRaisesRegex(ValueError,'capture mode'):
            M.check_capture_mode({},BOOT)
        M.check_capture_mode({},None)
        M.check_capture_mode({'source_boot_id':BOOT},BOOT)

    def test_ordinary_source_removal_read_race_is_pending_not_target_loss(self):
        with M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0,source_boot_id=BOOT) as receiver:
            receiver.transport('source',None)
            error=M.UsbReadDisappeared(OSError(errno.ENODEV,'fixture'),'idVendor')
            with patch.object(M,'usb_mode',side_effect=[error,('absent',None)]):
                M.update_transport(receiver,'fixture',lambda:True)
            self.assertTrue(receiver.source_disconnected)
            self.assertFalse(receiver.target_seen)
            self.assertFalse(receiver.failed)

    def test_ordinary_mode_requires_exact_source_topology_and_selector_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/'manifest'
            raw=b'target_release=fixture\nrollback_timeout=900\n';manifest.write_bytes(raw)
            for family,boot,mode,expected in (
                ('fastboot-boot-selector-trial',BOOT,('target',M.INTERFACE),'absolute output'),
                ('fastboot-boot-selector-trial',BOOT,('mismatch',None),'ordinary capture'),
                ('fastboot-boot-selector-trial','bad-id',('target',M.INTERFACE),'ordinary capture'),
                ('fastboot-boot-fallback-only',BOOT,('target',M.INTERFACE),'ordinary capture')):
                record=f'execution={family}\nmanifest_sha256={hashlib.sha256(raw).hexdigest()}\nserial=fixture\n'.encode()
                with self.subTest(family=family,boot=boot,mode=mode), \
                    patch.object(M.sys,'argv',['receiver','--profile','fixture','--manifest',str(manifest),
                        '--source-boot-id',boot,'--output','relative-capture']), \
                    patch.object(M.os,'geteuid',return_value=0), \
                    patch.object(M.CLAIMS,'expected_record',return_value=record), \
                    patch.object(M,'usb_mode',return_value=mode),self.assertRaisesRegex(ValueError,expected):
                    M.main()

    def test_ordinary_source_listener_remains_probeable_without_target_binding(self):
        with M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0,source_boot_id=BOOT) as receiver:
            with patch.object(M,'usb_mode',return_value=('target',M.INTERFACE)):
                M.update_transport(receiver,'fixture',lambda:True)
            self.assertIsNone(receiver.interface)
            receiver.probe=b'PROBE ordinary\n'
            receiver.probe_response=lambda:dict(ready=receiver.mode=='source' and not receiver.source_disconnected)
            with socket.create_connection(receiver.listener.getsockname()) as client:
                client.sendall(receiver.probe);client.shutdown(socket.SHUT_WR)
                for _ in range(3):receiver.poll(.01)
                self.assertEqual(json.loads(client.recv(1024)),dict(ready=True))


    def test_real_sysfs_read_disappearance_before_target_is_pending(self):
        # Reproduce the read/USB-removal boundary, not a guessed generic error.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); device=root/'device'; device.mkdir()
            usb=root/'usb'; usb.symlink_to(device, target_is_directory=True)
            events=[]; original=Path.read_text
            def removed(path,*args,**kwargs):
                if path==usb/'idVendor':
                    usb.unlink()
                    raise OSError(errno.ENODEV,'No such device')
                return original(path,*args,**kwargs)
            with M.Receiver('fixture',events.append,host='127.0.0.1',port=0) as receiver:
                receiver.transport('recovery',None)
                listener=receiver.listener.fileno()
                with patch.object(M,'USB',usb), patch.object(M,'ANCHOR',str(device)), \
                     patch.object(Path,'read_text',removed):
                    self.assertTrue(M.update_transport(receiver,'fixture',lambda:True))
                self.assertFalse(receiver.failed)
                self.assertEqual(receiver.mode,'absent')
                self.assertEqual(receiver.listener.fileno(),listener)
                self.assertIsNone(receiver.last)
                self.assertEqual(events[-2]['event'],'usb-discovery-interrupted')
                self.assertEqual(events[-2]['operation'],'idVendor')
                self.assertEqual(events[-2]['errno'],errno.ENODEV)

    def test_selector_trial_keeps_exact_manifest_and_fastboot_gates(self):
        # Same supervised fastboot transport, but the target comes from the
        # verified on-device selector, not an embedded RAM bundle.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root/'manifest'
            raw = b'target_release=7.1.4-fixture\nrollback_timeout=900\n'
            manifest.write_bytes(raw)
            for execution, digest, error in (
                ('fastboot-boot-selector-trial', hashlib.sha256(raw).hexdigest(),
                 'receiver must start at exact fastboot'),
                ('fastboot-boot-selector-trial', '0'*64, 'manifest differs'),
                ('fastboot-boot-unreviewed', hashlib.sha256(raw).hexdigest(),
                 'not a supported headless'),
            ):
                record = (f'execution={execution}\nmanifest_sha256={digest}\n'
                          'serial=fixture-device\n').encode()
                with self.subTest(execution=execution, digest=digest), \
                     patch.object(M.sys, 'argv', ['receiver', '--profile', 'fixture',
                         '--manifest', str(manifest), '--output', str(root/'capture')]), \
                     patch.object(M.os, 'geteuid', return_value=0), \
                     patch.object(M.CLAIMS, 'expected_record', return_value=record), \
                     patch.object(M, 'usb_mode', return_value=('mismatch', None)), \
                     self.assertRaisesRegex(ValueError, error):
                    M.main()
                self.assertFalse((root/'capture').exists())

    def test_identified_read_removal_never_hides_other_failures(self):
        for seen, next_mode, number, phase in (
                (True,'absent',errno.ENODEV,'usb'),
                (False,'enumerating',errno.ENODEV,'usb'),
                (False,'mismatch',errno.ENODEV,'usb'),
                (False,'target',errno.ENODEV,'usb'),
                (False,'absent',errno.EACCES,'usb'),
                (False,'absent',errno.ENODEV,'network')):
            with self.subTest(seen=seen,mode=next_mode,number=number,phase=phase):
                events=[]
                with M.Receiver('fixture',events.append,host='127.0.0.1',port=0) as receiver:
                    if seen:
                        receiver.transport('target',None)
                        receiver.transport('absent',None)  # No frame needed to latch observation.
                    error=M.UsbReadDisappeared(OSError(number,'fixture'),'idVendor')
                    discovery=[error]+[(next_mode,None)]*5 if phase=='usb' else [('target',None),(next_mode,None)]
                    def route(): raise error
                    with patch.object(M,'usb_mode',side_effect=discovery):
                        result=M.update_transport(receiver,'fixture',route)
                    self.assertEqual(result,next_mode!='mismatch')
                    self.assertTrue(receiver.failed)
                    failure=next(e for e in events if e['event']=='transport-check-failed')
                    self.assertEqual(failure['phase'],'usb-discovery' if phase=='usb' else 'network-setup')

    def test_teardown_waits_for_positive_absence_before_target(self):
        # Retained S04 trace: product ENODEV, unresolved recheck, then absent
        # 100 ms later. Its unrecorded second exception cannot be inferred;
        # this fixture explicitly supplies classified follow-up observations.
        fixture=json.loads((M.REPO/'tests/fixtures/persistent-root/s04-usb-descriptor-teardown.json').read_text())
        self.assertEqual(fixture['original_capture_result'],'FAIL')
        self.assertEqual(fixture['immediate_recheck_exception'],'not recorded')
        for followup in (fixture['immediate_recheck'], 'tagged-error'):
            events=[]
            with self.subTest(followup=followup), M.Receiver('fixture',events.append,
                    host='127.0.0.1',port=0) as receiver:
                receiver.transport(fixture['previous_mode'],None)
                error=M.UsbReadDisappeared(OSError(fixture['errno'],'No such device'),fixture['operation'])
                unresolved=error if followup=='tagged-error' else ('enumerating',None)
                route=unittest.mock.Mock(return_value=True)
                with patch.object(M,'usb_mode',side_effect=[error,unresolved,unresolved,('absent',None)]), \
                        patch.object(M.time,'sleep') as sleep:
                    M.update_transport(receiver,'fixture',route)
                self.assertFalse(receiver.failed)
                self.assertEqual(receiver.mode,'absent')
                event=next(e for e in events if e['event']=='usb-discovery-interrupted')
                self.assertEqual(event['removal_rechecks'],2)
                self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list),.15)
                route.assert_not_called()

    def test_teardown_resolution_is_bounded_and_never_masks_other_errors(self):
        for followup in ('enumerating','tagged-error','untagged','permission','mismatch','target'):
            events=[]
            with self.subTest(followup=followup), M.Receiver('fixture',events.append,
                    host='127.0.0.1',port=0) as receiver:
                receiver.transport('recovery',None)
                error=M.UsbReadDisappeared(OSError(errno.ENODEV,'fixture'),'product')
                next_read={'tagged-error':error,'untagged':OSError(errno.ENODEV,'fixture'),
                           'permission':PermissionError(errno.EACCES,'fixture')}.get(followup,(followup,None))
                with patch.object(M,'usb_mode',side_effect=[error]+[next_read]*5) as read, \
                        patch.object(M.time,'sleep') as sleep:
                    M.update_transport(receiver,'fixture',lambda:True)
                self.assertTrue(receiver.failed)
                self.assertLessEqual(read.call_count,5)
                self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list),.151)
                if followup not in ('enumerating','tagged-error'):
                    sleep.assert_not_called()
                self.assertTrue(any(e['event']=='transport-check-failed' for e in events))

    def test_teardown_cannot_extend_capture_deadline(self):
        with M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0) as receiver:
            error=M.UsbReadDisappeared(OSError(errno.ENODEV,'fixture'),'product')
            with patch.object(M,'usb_mode',side_effect=[error,('enumerating',None)]), \
                    patch.object(M.time,'monotonic',return_value=100), \
                    patch.object(M.time,'sleep') as sleep:
                M.update_transport(receiver,'fixture',lambda:True,deadline=100)
            self.assertTrue(receiver.failed)
            sleep.assert_not_called()

    def test_benign_enumeration_cannot_clear_an_existing_failure(self):
        with M.Receiver('fixture',lambda e:None,host='127.0.0.1',port=0) as receiver:
            receiver.failed=True
            error=M.UsbReadDisappeared(OSError(errno.ENOENT,'fixture'),'idProduct')
            with patch.object(M,'usb_mode',side_effect=[error,('absent',None)]):
                M.update_transport(receiver,'fixture',lambda:True)
            self.assertTrue(receiver.failed)

    def test_retained_pretarget_enodev_is_not_erased_by_later_readiness(self):
        fixture=json.loads((M.REPO/'tests/fixtures/persistent-root/rescue-pretarget-enodev.json').read_text())
        events=[]
        with M.Receiver('7.1.4-g359318de534f',events.append,host='127.0.0.1',port=0,peer='127.0.0.1') as receiver:
            receiver.transport(fixture['previous_mode'],None)
            with patch.object(M,'usb_mode',side_effect=[
                    OSError(fixture['errno'],fixture['message']),
                    (fixture['next_mode'],None)]):
                self.assertTrue(M.update_transport(receiver,'fixture-serial',lambda:True))
            self.assertEqual(receiver.failed,fixture['expected_capture_failed'])
            self.assertIsNone(receiver.last)
            self.assertEqual(events[-2]['event'],'transport-check-failed')
            with patch.object(M,'usb_mode',return_value=(fixture['later_mode'],None)):
                self.assertTrue(M.update_transport(receiver,'fixture-serial',lambda:True))
            receiver.record(frame(),'127.0.0.1')
            self.assertEqual(receiver.last.boot_id,BOOT)
            self.assertTrue(receiver.failed)  # Preserve the actual FAIL, not a retroactive pass.

    def test_live_disconnect_during_nmcli_preserves_capture_and_last_stage(self):
        fixture=json.loads((M.REPO/'tests/fixtures/persistent-root/rescue-state-host-loss.json').read_text())
        events=[]
        with M.Receiver(fixture['target_release'],events.append,host='127.0.0.1',port=0,peer='127.0.0.1') as receiver:
            receiver.transport('target',None)
            receiver.record(frame(25,fixture['boot_id']),'127.0.0.1')
            with patch.object(M,'usb_mode',side_effect=[('target',None),('absent',None)]):
                def vanished(): raise RuntimeError(fixture['receiver_error'])
                self.assertTrue(M.update_transport(receiver,'fixture-serial',vanished))
            self.assertEqual(receiver.mode,'absent')
            self.assertTrue(receiver.failed)  # Interrupted evidence never becomes green.
            self.assertEqual(receiver.last.boot_id,fixture['boot_id'])
            self.assertEqual(events[-1]['last_stage']['sequence'],25)
            self.assertEqual(events[-2]['event'],'transport-check-failed')
            # The same listener remains alive; no claim, boot or lifetime reset.
            receiver.poll(0)
            with patch.object(M,'usb_mode',return_value=('target',None)):
                self.assertTrue(M.update_transport(receiver,'fixture-serial',lambda:True))
            receiver.record(frame(25,fixture['boot_id']),'127.0.0.1')
            self.assertTrue(receiver.failed)

    def test_network_failure_cannot_admit_target_or_hide_identity_mismatch(self):
        for next_mode in ('target','mismatch'):
            with self.subTest(mode=next_mode), M.Receiver('fixture',lambda event:None,host='127.0.0.1',port=0) as receiver:
                with patch.object(M,'usb_mode',side_effect=[('target',None),(next_mode,None)]):
                    def broken(): raise RuntimeError('host operation failed: nmcli -g')
                    proceed=M.update_transport(receiver,'fixture-serial',broken)
                self.assertEqual(proceed,next_mode!='mismatch')
                self.assertEqual(receiver.mode,'enumerating' if next_mode=='target' else 'mismatch')
                self.assertTrue(receiver.failed)

    def test_live_probe_requires_an_answer_from_the_running_loop(self):
        with M.Receiver('7.1.4-g359318de534f',lambda x:None,host='127.0.0.1',port=0) as receiver:
            receiver.probe=b'PROBE fixture-nonce\n'
            receiver.probe_response=lambda: dict(ready=True,required_seconds=1320)
            with socket.create_connection(receiver.listener.getsockname()) as client:
                client.sendall(receiver.probe); client.shutdown(socket.SHUT_WR)
                for _ in range(3): receiver.poll(.01)
                self.assertEqual(json.loads(client.recv(1024)),dict(ready=True,required_seconds=1320))
                self.assertIsNone(receiver.last)
    def test_preboot_listener_precedes_client_and_disconnect_retains_last_stage(self):
        events=[]
        receiver=M.Receiver('7.1.4-g359318de534f', events.append, host='127.0.0.1', port=0, peer='127.0.0.1')
        with receiver:
            self.assertEqual(receiver.listener.getsockname()[0], '127.0.0.1')
            receiver.transport('absent', None)
            receiver.transport('target', None)
            with socket.create_connection(receiver.listener.getsockname()) as client:
                client.sendall(frame()); client.shutdown(socket.SHUT_WR)
                for _ in range(3): receiver.poll(.02)
            receiver.transport('absent', None)
            self.assertEqual(events[-1]['last_stage']['stage'], 'switch-root')
            self.assertEqual(receiver.last.boot_id, BOOT)
            receiver.transport('target', None)
            self.assertFalse(receiver.failed)

    def test_mixed_boot_regression_and_bad_frames_are_failure_not_new_boot(self):
        for bad in (frame(2,'87654321-4321-4abc-8def-1234567890ab'),frame(1).replace(b'detail=none',b'detail=changed'),b'x'*513):
            events=[]
            with M.Receiver('7.1.4-g359318de534f',events.append,host='127.0.0.1',port=0,peer='127.0.0.1') as receiver:
                receiver.transport('target',None)
                receiver.record(frame(), '127.0.0.1')
                receiver.record(bad, '127.0.0.1')
                self.assertTrue(receiver.failed)
                self.assertEqual(receiver.last.boot_id, BOOT)

    def test_unrelated_transport_never_becomes_target_evidence(self):
        events=[]
        with M.Receiver('7.1.4-g359318de534f',events.append,host='127.0.0.1',port=0,peer='127.0.0.1') as receiver:
            receiver.transport('absent',None)
            receiver.record(frame(),'127.0.0.1')
            self.assertIsNone(receiver.last)
            receiver.transport('target',None)
            receiver.record(frame(),'127.0.0.2')
            self.assertIsNone(receiver.last)

    def test_idle_and_trickle_clients_have_absolute_deadline(self):
        events=[]
        with M.Receiver('7.1.4-g359318de534f',events.append,host='127.0.0.1',port=0,peer='127.0.0.1',client_seconds=.08) as receiver:
            receiver.transport('target',None)
            with socket.create_connection(receiver.listener.getsockname()) as idle, socket.create_connection(receiver.listener.getsockname()) as good:
                idle.sendall(b'f')
                good.sendall(frame()); good.shutdown(socket.SHUT_WR)
                deadline=time.monotonic()+.5
                while time.monotonic()<deadline and (receiver.last is None or receiver.clients):
                    receiver.poll(.01)
                self.assertEqual(receiver.last.boot_id,BOOT)
                self.assertEqual(len(receiver.clients),0)
                self.assertTrue(receiver.failed)  # Partial/lost diagnostic frame is not a green run.

    def test_powered_off_window_preserves_transition_and_full_failure_capture(self):
        contract=M.ACCEPTANCE.load_contract()
        normal=M.capture_lifetime(contract)
        physical=M.capture_lifetime(contract,powered_off_start=True)
        self.assertEqual(normal,1380)
        self.assertEqual(physical,1440)
        # A live check/entry 30 seconds after arming cannot meet S06 with the
        # original lifetime; the scoped allowance retains the full 1380.
        self.assertFalse(M.lifetime_ready(normal,30,1380))
        self.assertTrue(M.lifetime_ready(physical,30,1380))
        self.assertFalse(M.lifetime_ready(physical,61,1380))
        changed=json.loads(json.dumps(contract))
        next(row for row in changed['tests'] if row['id']=='S06')['deadline_seconds']=410
        self.assertEqual(M.capture_lifetime(changed,powered_off_start=True),1430)
        next(row for row in changed['tests'] if row['id']=='S06')['deadline_seconds']=421
        with self.assertRaises(ValueError):M.capture_lifetime(changed,powered_off_start=True)

    def test_powered_off_mode_cannot_be_forged_or_used_for_ram_capture(self):
        M.check_capture_mode({'source_boot_id':BOOT,'powered_off_start':True},BOOT,powered_off_start=True)
        for receipt,boot,requested in (
            ({'source_boot_id':BOOT},BOOT,True),
            ({'source_boot_id':BOOT,'powered_off_start':True},BOOT,False),
            ({'powered_off_start':True},None,True),
            ({'source_boot_id':BOOT,'powered_off_start':1},BOOT,True),
            ({'source_boot_id':BOOT,'powered_off_start':True,'source_teardown_sha256':'a'*64},BOOT,True)):
            with self.subTest(receipt=receipt,requested=requested),self.assertRaisesRegex(ValueError,'capture mode'):
                M.check_capture_mode(receipt,boot,powered_off_start=requested)

    def test_powered_off_cli_rejects_missing_source_and_experimental_intent_before_io(self):
        for extra in ([],['--source-boot-id','invalid'],
                      ['--source-boot-id',BOOT,'--source-teardown-intent','/never-read'],
                      ['--source-boot-id',BOOT,'--source-teardown-sha256','a'*64]):
            with self.subTest(extra=extra),patch.object(M.sys,'argv',[
                'receiver','--profile','fixture','--output','/never-created','--powered-off-start',*extra]), \
                 patch.object(M,'host_ready') as host,self.assertRaisesRegex(ValueError,'capture mode'):
                M.main()
            host.assert_not_called()

    def test_powered_off_start_keeps_installed_selector_and_topology_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/'manifest';raw=b'target_release=fixture\nrollback_timeout=900\n';manifest.write_bytes(raw)
            for family,mode,error in (
                    ('fastboot-boot-selector-trial',('target',M.INTERFACE),'absolute output'),
                    ('fastboot-boot-selector-trial',('mismatch',None),'ordinary capture'),
                    ('fastboot-boot-ram-bundle',('target',M.INTERFACE),'ordinary capture'),
                    ('fastboot-boot-fallback-only',('target',M.INTERFACE),'ordinary capture')):
                record=f'execution={family}\nmanifest_sha256={hashlib.sha256(raw).hexdigest()}\nserial=fixture\n'.encode()
                with self.subTest(family=family,mode=mode),patch.object(M.sys,'argv',[
                    'receiver','--profile','fixture','--manifest',str(manifest),'--source-boot-id',BOOT,
                    '--powered-off-start','--output','relative-capture']),patch.object(M.os,'geteuid',return_value=0), \
                     patch.object(M.CLAIMS,'expected_record',return_value=record), \
                     patch.object(M,'usb_mode',return_value=mode),self.assertRaisesRegex(ValueError,error):
                    M.main()

    def test_powered_off_cli_check_dispatch_binds_mode(self):
        with patch.object(M.sys,'argv',['receiver','--profile','fixture','--output','/fixture',
                '--source-boot-id',BOOT,'--powered-off-start','--check']), \
             patch.object(M,'check_receiver',return_value={}) as check,patch('builtins.print'):
            self.assertEqual(M.main(),0)
            check.assert_called_once_with(Path('/fixture'),'fixture',source_boot_id=BOOT,
                source_teardown_sha256=None,powered_off_start=True)

    def test_live_check_requires_matching_physical_mode_and_original_remaining_gate(self):
        canonical=dict(candidate='fixture',execution='fastboot-boot-selector-trial')
        source={'fixture':'frozen'}
        for mode in (False,True):
            for live_mode,remaining in ((mode,1390),(not mode,1390),(1,1390),(mode,1319)):
                receipt=dict(source_boot_id=BOOT,canonical_record=canonical,profile='fixture',source=source,
                    receiver_sha256=hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),
                    host_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    process_start='fixture',pid=123,probe='PROBE fixture',required_seconds=1320,
                    deadline_monotonic=100+remaining)
                live=dict(ready=True,candidate='fixture',pid=123,required_seconds=1320,
                    source_boot_id=BOOT,remaining_seconds=remaining)
                if mode:receipt['powered_off_start']=True
                if live_mode is not False:live['powered_off_start']=live_mode
                with self.subTest(mode=mode,live_mode=live_mode,remaining=remaining),tempfile.TemporaryDirectory() as tmp:
                    output=Path(tmp);(output/'receipt.json').write_text(json.dumps(receipt))
                    client=unittest.mock.MagicMock();client.__enter__.return_value=client
                    client.recv.side_effect=[json.dumps(live).encode(),b'']
                    with patch.object(M.CLAIMS,'expected_record',return_value=''.join(k+'='+v+'\n' for k,v in canonical.items()).encode()), \
                         patch.object(M.ACCEPTANCE,'source_identity',return_value=source), \
                         patch.object(M,'process_start',return_value='fixture'),patch.object(M,'host_ready'), \
                         patch.object(M.socket,'socket',return_value=client),patch.object(M.time,'monotonic',return_value=100):
                        if live_mode is mode and remaining>=1320:
                            self.assertEqual(M.check_receiver(output,'fixture',source_boot_id=BOOT,
                                powered_off_start=mode)['status'],'PASS')
                        else:
                            with self.assertRaisesRegex(ValueError,'not ready'):
                                M.check_receiver(output,'fixture',source_boot_id=BOOT,powered_off_start=mode)

    def test_remaining_lifetime_is_a_live_gate_not_a_stale_ready_file(self):
        self.assertTrue(M.lifetime_ready(100, 30, 60))
        self.assertFalse(M.lifetime_ready(100, 41, 60))
        self.assertFalse(M.lifetime_ready(100, 100, 1))


class FakeHost:
    def __init__(self, failure='', after=False, shared_single_address=False):
        self.fields=list(M.NETWORK.ORIGINAL)
        self.address=False; self.firewall=False; self.calls=[]; self.label='preexisting'
        self.failure=failure; self.after=after; self.failed=False
        self.shared_single_address=shared_single_address
        self.route=[]; self.ifindex=42; self.up=True; self.zone='nm-shared'

    def __call__(self, args, *, acceptable=(0,)):
        self.calls.append(args)
        if args[0]=='nmcli' and 'show' in args:
            if 'GENERAL.CON-UUID' in args: return 0,M.NETWORK.PROFILE+'\n'
            return 0,'\n'.join(self.fields)+'\n'
        if args[:3]==['ip','-j','address']:
            values=[dict(local=M.ADDRESS,prefixlen=32,label=self.label)] if self.address else []
            return 0,json.dumps([dict(ifname='lo',addr_info=values)])
        if args[:3]==['ip','-j','route']: return 0,json.dumps(self.route)
        if args[:3]==['ip','-j','link']: return 0,json.dumps([dict(ifname=M.INTERFACE,ifindex=self.ifindex,flags=['UP'] if self.up else [])])
        if args[:2]==['firewall-cmd','--get-zone-of-interface='+M.INTERFACE]: return 0,self.zone+'\n'
        if args[0]=='sysctl': return 0,'0\n'*4
        if args[0]=='ss': return 0,''
        if '--state' in args: return 0,'running\n'
        if any(x.startswith('--query-rich-rule=') for x in args): return (0 if self.firewall else 1),''
        operation=None
        if args[:3]==['nmcli','connection','modify']:
            new=args[args.index('connection.zone')+1]
            operation='profile' if new=='nm-shared' else 'restore'
            change=lambda:setattr(self,'fields',list(M.NETWORK.PREPARED if operation=='profile' else M.NETWORK.ORIGINAL))
        elif args[:3]==['ip','address','add']:
            self.label=args[-1]
            operation='address'; change=lambda:setattr(self,'address',True)
        elif args[:3]==['ip','address','del']:
            operation='del-address'; change=lambda:setattr(self,'address',False)
        elif args[:3]==['ip','route','add']:
            operation='route'; change=lambda:setattr(self,'route',[dict(dst=M.NETWORK.PEER,dev=M.INTERFACE,
                prefsrc=M.ADDRESS,protocol='static',metric=8079,scope='link')])
        elif args[:3]==['ip','route','del']:
            operation='del-route'; change=lambda:setattr(self,'route',[])
        elif any(x.startswith('--add-rich-rule=') for x in args):
            operation='firewall'; change=lambda:setattr(self,'firewall',True)
        elif any(x.startswith('--remove-rich-rule=') for x in args):
            operation='del-firewall'; change=lambda:setattr(self,'firewall',False)
        elif args[:3]==['nmcli','device','reapply']:
            return 0,''
        else: raise AssertionError('unexpected host operation: '+repr(args))
        fail=operation==self.failure and not self.failed
        if not fail or self.after:
            change()
            if operation=='profile' and self.shared_single_address:
                self.fields[3]=self.fields[3].split(',')[0]
        if fail:
            self.failed=True
            raise RuntimeError('fixture timeout')
        return 0,''


class NetworkTest(unittest.TestCase):
    def test_discovery_before_link_and_zone_convergence_waits_without_route(self):
        host=FakeHost(); host.up=False; host.zone='no zone'
        with M.NETWORK.prepared(1380,lambda x:None,lambda:False,run=host) as (_,connect):
            self.assertFalse(connect())
            self.assertFalse(host.route)
            host.up=True
            self.assertFalse(connect())
            self.assertFalse(host.route)
            host.zone='nm-shared'
            self.assertTrue(connect())
            self.assertTrue(host.route)

    def test_direct_route_follows_exact_enumeration_and_is_removed(self):
        host=FakeHost()
        with M.NETWORK.prepared(1380,lambda x:None,lambda:False,run=host) as (_,connect):
            self.assertFalse(host.route)
            connect(); connect()
            self.assertTrue(host.route)
            self.assertEqual(sum(c[:3]==['ip','route','add'] for c in host.calls),1)
        self.assertFalse(host.route)

    def test_reenumeration_reacquires_only_a_vanished_owned_route(self):
        host=FakeHost()
        with M.NETWORK.prepared(1380,lambda x:None,lambda:False,run=host) as (_,connect):
            connect()
            host.route=[]; host.ifindex+=1  # Kernel removes link's route on disconnect.
            connect()
        self.assertFalse(host.route)
    def test_real_shared_mode_drops_secondary_address_without_breaking_setup(self):
        host=FakeHost(shared_single_address=True)
        with M.NETWORK.prepared(1380,lambda x:None,lambda:False,run=host):
            self.assertEqual(host.fields[3],'10.77.0.1/30')
            self.assertTrue(host.address)
        self.assertEqual(host.fields,M.NETWORK.ORIGINAL)
    def test_prepared_address_profile_firewall_and_exact_cleanup(self):
        host=FakeHost(); events=[]
        with M.NETWORK.prepared(1380,events.append,lambda:True,run=host):
            self.assertTrue(host.address and host.firewall)
            self.assertEqual(host.fields,M.NETWORK.PREPARED)
        self.assertFalse(host.address or host.firewall)
        self.assertEqual(host.fields,M.NETWORK.ORIGINAL)
        self.assertIn(['nmcli','device','reapply',M.INTERFACE],host.calls)

    def test_failed_or_ambiguous_mutation_is_cleaned_without_boot(self):
        for point in ('profile','address','firewall'):
            for after in (False,True):
                with self.subTest(point=point,after=after):
                    host=FakeHost(point,after)
                    with self.assertRaises(RuntimeError):
                        with M.NETWORK.prepared(1380,lambda x:None,lambda:False,run=host):
                            self.fail('failed setup reached readiness')
                    self.assertFalse(host.address or host.firewall)
                    self.assertEqual(host.fields,M.NETWORK.ORIGINAL)

    def test_preexisting_network_state_is_not_claimed(self):
        for name in ('address','firewall'):
            host=FakeHost(); setattr(host,name,True)
            with self.assertRaises(RuntimeError):
                with M.NETWORK.prepared(1380,lambda x:None,lambda:False,run=host): pass
            self.assertTrue(getattr(host,name))
            self.assertEqual(host.fields,M.NETWORK.ORIGINAL)

    def test_external_profile_change_is_preserved_and_cleanup_failure_visible(self):
        host=FakeHost(); events=[]
        with self.assertRaisesRegex(RuntimeError,'cleanup incomplete'):
            with M.NETWORK.prepared(1380,events.append,lambda:False,run=host):
                host.fields[3]='192.0.2.1/30'
        self.assertEqual(host.fields[3],'192.0.2.1/30')
        self.assertFalse(host.address or host.firewall)
        self.assertTrue(any(x.get('status')=='FAIL' for x in events))


if __name__ == '__main__':
    unittest.main(verbosity=2)
