#!/usr/bin/env python3
"""Validate one fresh authenticated Tailscale discovery result, not SSH access.

The caller performs a bounded single ping and immediately reads status/routes.
This never reads USB paths or changes authentication. An endpoint is only a
candidate: strict project SSH host-key and expected new boot identity checks
remain mandatory before using it for target operations.
"""
import ipaddress
import re


class NotReady(RuntimeError):
    """The known peer has not supplied a fresh usable direct endpoint yet."""


def unicast(value):
    if not isinstance(value,str) or '%' in value:
        raise ValueError('invalid unscoped IP address')
    address=ipaddress.ip_address(value)
    if address.is_unspecified or address.is_loopback or address.is_multicast or address.is_link_local:
        raise ValueError('endpoint is not an eligible LAN unicast address')
    return address


def parse_endpoint(value):
    if not isinstance(value,str) or len(value)>96:
        raise ValueError('invalid endpoint')
    match=re.fullmatch(r'\[([^\]]+)\]:([0-9]+)|([^:]+):([0-9]+)',value)
    if not match:raise ValueError('endpoint framing changed')
    address=unicast(match[1] or match[3]);port=int(match[2] or match[4])
    if not 1<=port<=65535:raise ValueError('invalid UDP endpoint port')
    return {'address':str(address),'port':port}


def peer_endpoint(status,pong,overlay_ip,hostname):
    wanted=ipaddress.ip_address(overlay_ip)
    if status.get('BackendState')!='Running':raise NotReady('client-not-running')
    peers=status.get('Peer') or {}
    if not isinstance(peers,dict):raise ValueError('invalid peer table')
    selected=[peer for peer in peers.values() if str(wanted) in (peer.get('TailscaleIPs') or [])]
    if not selected:raise NotReady('peer-not-present')
    if len(selected)!=1:raise ValueError('ambiguous peer identity')
    peer=selected[0]
    if peer.get('HostName')!=hostname:raise ValueError('peer identity changed')
    if peer.get('Online') is not True:raise NotReady('peer-offline')
    if not peer.get('CurAddr'):raise NotReady('no-direct-endpoint')
    endpoint=parse_endpoint(peer['CurAddr'])
    if endpoint['address']==str(wanted):raise ValueError('overlay address is not a LAN endpoint')
    if not isinstance(pong,str) or len(pong)>4096:raise ValueError('invalid ping output')
    lines=pong.splitlines()
    if len(lines)!=1:raise ValueError('ambiguous ping response')
    match=re.fullmatch(r'pong from \S+ \(([^)]+)\) via (\S+) in [0-9]+(?:\.[0-9]+)?(?:ns|µs|us|ms|s)',lines[0])
    if not match:raise ValueError('unrecognized ping output')
    if ipaddress.ip_address(match[1])!=wanted:raise ValueError('ping answered by another peer')
    if match[2].startswith('DERP('):raise NotReady('relay-only')
    if parse_endpoint(match[2])!=endpoint:raise NotReady('endpoint-changed-during-discovery')
    return endpoint


def lan_source(routes,address,interface='wlan0'):
    endpoint=unicast(address)
    if not isinstance(routes,list) or len(routes)!=1:raise ValueError('ambiguous route')
    route=routes[0]
    if route.get('dev')!=interface or route.get('gateway'):
        raise NotReady('endpoint is not directly routed over the expected WLAN')
    if ipaddress.ip_address(route.get('dst',''))!=endpoint:raise ValueError('route destination changed')
    sources={str(unicast(route[key])) for key in ('prefsrc','src') if route.get(key)}
    if len(sources)!=1:raise ValueError('missing or ambiguous WLAN source')
    source=sources.pop()
    if ipaddress.ip_address(source).version!=endpoint.version:raise ValueError('source address family changed')
    return source
