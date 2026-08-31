#!/usr/bin/env python3
import copy
import importlib.util
from pathlib import Path
import unittest

R=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('discovery',R/'scripts/host/native-wifi-discovery.py')
discovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(discovery)


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.status={'BackendState':'Running','Peer':{'node':{'HostName':'rog5-server','Online':True,
            'TailscaleIPs':['100.64.0.10'],'CurAddr':'192.0.2.10:58636'}}}
        self.pong='pong from rog5-server (100.64.0.10) via 192.0.2.10:58636 in 33ms\n'
        self.route=[{'dst':'192.0.2.10','dev':'wlan0','prefsrc':'192.0.2.1'}]

    def select(self,status=None,pong=None):
        return discovery.peer_endpoint(self.status if status is None else status,self.pong if pong is None else pong,'100.64.0.10','rog5-server')

    def test_captured_direct_shape_needs_fresh_pong_and_direct_wlan_route(self):
        endpoint=self.select()
        self.assertEqual(endpoint,{'address':'192.0.2.10','port':58636})
        self.assertEqual(discovery.lan_source(self.route,endpoint['address']),'192.0.2.1')

    def test_ipv6_and_microsecond_duration(self):
        data=copy.deepcopy(self.status);data['Peer']['node']['CurAddr']='[2001:db8::10]:41641'
        pong=self.pong.replace('192.0.2.10:58636','[2001:db8::10]:41641').replace('33ms','981.2µs')
        endpoint=self.select(data,pong)
        self.assertEqual(endpoint['address'],'2001:db8::10')
        self.assertEqual(discovery.lan_source([{'dst':'2001:db8::10','dev':'wlan0','src':'2001:db8::1'}],endpoint['address']),'2001:db8::1')

    def test_absent_offline_relay_and_stale_endpoint_are_not_ready(self):
        for mutation in ('not-running','no-peer','offline','blank','stale'):
            data=copy.deepcopy(self.status)
            if mutation=='not-running':data['BackendState']='NeedsLogin'
            elif mutation=='no-peer':data['Peer']={}
            elif mutation=='offline':data['Peer']['node']['Online']=False
            elif mutation=='blank':data['Peer']['node']['CurAddr']=''
            else:data['Peer']['node']['CurAddr']='192.0.2.11:58636'
            with self.subTest(mutation=mutation),self.assertRaises(discovery.NotReady):self.select(data)
        with self.assertRaises(discovery.NotReady):self.select(pong='pong from rog5-server (100.64.0.10) via DERP(waw) in 23ms\n')

    def test_identity_ambiguity_and_malformed_endpoints_fail(self):
        duplicate=copy.deepcopy(self.status);duplicate['Peer']['duplicate']=copy.deepcopy(duplicate['Peer']['node'])
        with self.assertRaises(ValueError):self.select(duplicate)
        wrong=copy.deepcopy(self.status);wrong['Peer']['node']['HostName']='another-device'
        with self.assertRaises(ValueError):self.select(wrong)
        with self.assertRaises(ValueError):self.select(pong=self.pong.replace('(100.64.0.10)','(100.64.0.11)'))
        with self.assertRaises(ValueError):self.select(pong=self.pong+self.pong)
        for bad in ('127.0.0.1:22','169.254.77.2:22','224.0.0.1:22','0.0.0.0:22','example.com:22','192.0.2.10:0','192.0.2.10:65536','[fe80::1%wlan0]:22','192.0.2.10;true:22'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):discovery.parse_endpoint(bad)

    def test_wrong_source_interface_gateway_or_ambiguous_route_fails(self):
        for route in ([dict(self.route[0],dev='enp4s0f3u1u2')],
                      [dict(self.route[0],gateway='192.0.2.254')],
                      [dict(self.route[0],dst='192.0.2.11')],
                      [dict(self.route[0],src='192.0.2.9')],
                      [dict(self.route[0],prefsrc='127.0.0.1')],self.route*2,[]):
            with self.subTest(route=route),self.assertRaises((ValueError,discovery.NotReady)):discovery.lan_source(route,'192.0.2.10')


if __name__=='__main__':unittest.main()
