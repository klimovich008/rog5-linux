#!/usr/bin/env python3
"""Small passive receiver regressions; no phone, credentials or host networking."""
import importlib.util
from pathlib import Path
import socket
import json
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
