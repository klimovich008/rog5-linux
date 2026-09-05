#!/usr/bin/env python3
"""Owned temporary host networking for the passive rescue receiver, not a boot."""
from contextlib import contextmanager
import json
import os
import subprocess
import time

INTERFACE = 'enp4s0f3u1u2'
PROFILE = 'ca8e4b9d-b5e4-44e9-a77a-4bd989e5bfe9'
ADDRESS = '169.254.77.1'
RULE = 'rule family="ipv4" source address="169.254.77.2" destination address="169.254.77.1" port port="8079" protocol="tcp" accept'
FIELDS = 'connection.interface-name,connection.autoconnect,ipv4.method,ipv4.addresses,connection.zone'
ORIGINAL = [INTERFACE, 'yes', 'shared', '10.77.0.1/30', '']
PREPARED = [INTERFACE, 'yes', 'shared', '10.77.0.1/30', 'nm-shared']
PEER = '169.254.77.2'


def command(args, *, acceptable=(0,)):
    result = subprocess.run(args, capture_output=True, text=True, timeout=5)
    if result.returncode not in acceptable:
        raise RuntimeError('host operation failed: '+args[0]+' '+args[1])
    return result.returncode, result.stdout


def profile(run=command):
    fields = run(['nmcli', '-g', FIELDS, 'connection', 'show', PROFILE])[1].splitlines()
    if len(fields) != 5:
        raise RuntimeError('unexpected NetworkManager profile fields')
    fields[3] = fields[3].replace(' ', '')
    return fields


def addresses(run=command):
    return json.loads(run(['ip', '-j', 'address', 'show'])[1])


@contextmanager
def prepared(lifetime, emit, target_connected, run=command):
    label = f'lo:rg{os.getpid():x}'
    if profile(run) != ORIGINAL:
        raise RuntimeError('original project network profile changed')
    if any(a.get('local') == ADDRESS for interface in addresses(run) for a in interface.get('addr_info', [])):
        raise RuntimeError('diagnostic address already exists; ownership refused')
    if run(['ss', '-H', '-ltn', 'sport = :8079'])[1].strip():
        raise RuntimeError('diagnostic listener already exists')
    if run(['firewall-cmd', '--state'])[1].strip() != 'running':
        raise RuntimeError('firewalld unavailable')
    query = ['firewall-cmd', '--zone=nm-shared', '--query-rich-rule='+RULE]
    if run(query, acceptable=(0,1))[0] != 1:
        raise RuntimeError('diagnostic firewall rule already exists')
    owned_address = owned_profile = owned_firewall = False
    route_index = None
    cleanup_errors = []
    deadline = time.monotonic()+lifetime
    def route_rows():
        return json.loads(run(['ip','-j','route','show','exact',PEER+'/32'])[1])
    def exact_route(rows):
        return (len(rows)==1 and rows[0].get('dst') in {PEER,PEER+'/32'}
                and rows[0].get('dev')==INTERFACE and rows[0].get('prefsrc')==ADDRESS
                and rows[0].get('protocol')=='static' and rows[0].get('metric')==8079
                and rows[0].get('scope')=='link')
    def interface_state():
        rows=json.loads(run(['ip','-j','link','show','dev',INTERFACE])[1])
        if len(rows)!=1 or rows[0]['ifname']!=INTERFACE:
            raise RuntimeError('ambiguous USB link')
        return rows[0]
    def ensure_route():
        nonlocal route_index
        link=interface_state()
        index=link['ifindex']
        # sysfs discovery precedes NetworkManager/firewalld convergence.
        # These bounded pending states are not transport readiness or failure.
        if 'UP' not in link.get('flags', []): return False
        zone=run(['firewall-cmd','--get-zone-of-interface='+INTERFACE],acceptable=(0,1))[1].strip()
        if zone in {'','no zone'}: return False
        if zone!='nm-shared': raise RuntimeError('USB firewall zone changed')
        if run(['nmcli','-g','GENERAL.CON-UUID','device','show',INTERFACE])[1].strip()!=PROFILE:
            return False
        rows=route_rows()
        if rows:
            if route_index==index and exact_route(rows): return True
            raise RuntimeError('direct diagnostic route already owned/changed')
        values=run(['sysctl','-n', 'net.ipv4.conf.all.arp_ignore',
                    'net.ipv4.conf.'+INTERFACE+'.arp_ignore', 'net.ipv4.conf.all.arp_filter',
                    'net.ipv4.conf.'+INTERFACE+'.arp_filter'])[1].splitlines()
        if values!=['0']*4:
            raise RuntimeError('loopback diagnostic address requires reviewed ARP policy')
        route_index=index
        run(['ip','route','add',PEER+'/32','dev',INTERFACE,'src',ADDRESS,
             'proto','static','scope','link','metric','8079'])
        if not exact_route(route_rows()): raise RuntimeError('diagnostic route did not converge')
        emit(dict(event='host-usb-route-ready',ifindex=index))
        return True
    if route_rows():
        raise RuntimeError('preexisting diagnostic route; ownership refused')
    try:
        # Mark an attempted narrow mutation as owned before invoking it: a
        # timeout may occur after D-Bus/ip already applied the requested state.
        owned_profile = True
        run(['nmcli','connection','modify','--temporary',PROFILE,
             'connection.zone','nm-shared'])
        if profile(run) != PREPARED:
            raise RuntimeError('temporary profile did not converge')
        emit(dict(event='host-profile-prepared'))
        owned_address = True
        run(['ip','address','add',ADDRESS+'/32','dev','lo','label',label])
        emit(dict(event='host-address-prepared'))
        owned_firewall = True
        run(['firewall-cmd','--zone=nm-shared','--add-rich-rule='+RULE,'--timeout='+str(lifetime)])
        if run(query, acceptable=(0,1))[0] != 0:
            raise RuntimeError('temporary firewall rule not present')
        emit(dict(event='host-firewall-prepared', deadline_monotonic=deadline))
        yield deadline, ensure_route
    finally:
        def cleanup(label, action):
            try:
                action()
                emit(dict(event='host-cleanup', item=label, status='PASS'))
            except Exception as error:
                cleanup_errors.append(label)
                emit(dict(event='host-cleanup', item=label, status='FAIL', reason=str(error)))
        def restore_profile():
            current = profile(run)
            if current == ORIGINAL:
                return
            if current != PREPARED:
                raise RuntimeError('profile changed externally; refusing overwrite')
            run(['nmcli','connection','modify','--temporary',PROFILE,
                 'connection.zone',''])
            if profile(run) != ORIGINAL:
                raise RuntimeError('profile restoration did not converge')
            if target_connected():
                if run(['nmcli','-g','GENERAL.CON-UUID','device','show',INTERFACE])[1].strip() != PROFILE:
                    raise RuntimeError('active interface owner changed')
                run(['nmcli','device','reapply',INTERFACE])
        def remove_address():
            matches = [(i,a) for i in addresses(run) for a in i.get('addr_info',[]) if a.get('local') == ADDRESS]
            if not matches:
                return
            if len(matches)!=1 or matches[0][0]['ifname']!='lo' or matches[0][1].get('label')!=label or matches[0][1]['prefixlen']!=32:
                raise RuntimeError('diagnostic address ownership changed')
            run(['ip','address','del',ADDRESS+'/32','dev','lo'])
        def remove_firewall():
            if run(query, acceptable=(0,1))[0] == 0:
                run(['firewall-cmd','--zone=nm-shared','--remove-rich-rule='+RULE])
        def remove_route():
            rows=route_rows()
            if not rows: return
            if interface_state()['ifindex']!=route_index or not exact_route(rows):
                raise RuntimeError('route/interface ownership changed')
            run(['ip','route','del',PEER+'/32','dev',INTERFACE,'proto','static','metric','8079'])
        if route_index is not None: cleanup('route',remove_route)
        if owned_firewall: cleanup('firewall',remove_firewall)
        if owned_profile: cleanup('profile',restore_profile)
        if owned_address: cleanup('address',remove_address)
        if cleanup_errors:
            raise RuntimeError('host cleanup incomplete: '+','.join(cleanup_errors))
