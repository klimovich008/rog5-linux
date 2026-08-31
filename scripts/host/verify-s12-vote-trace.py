#!/usr/bin/env python3
"""Correlate S12 responses with read/write origins, within one captured phase."""
import json
from pathlib import Path
import re
import sys

ADDRESSES=(0x40100,0x40104,0x40108)
SEND=re.compile(r'rpmh_send_msg: apps_rsc: tcs\(m\): (\d+) \[(\w+)\] cmd\(n\): (\d+) msgid: (0x[0-9a-f]+) addr: (0x[0-9a-f]+) data: (0x[0-9a-f]+)')
DONE=re.compile(r'rpmh_tx_done: apps_rsc: ack: tcs-m: (\d+) addr: (0x[0-9a-f]+) data: (0x[0-9a-f]+)')

def transactions(text):
    if len(text)>4*1024*1024 or re.search(r'LOST.*EVENTS|lost events',text,re.I):
        raise ValueError('incomplete or oversized trace')
    pending={};completed=[];control=[]
    for line in text.splitlines():
        send=SEND.search(line)
        if send:
            slot,state,index,msg,address,data=send.groups()
            slot,index=int(slot),int(index);msg,address,data=(int(v,16) for v in (msg,address,data))
            if state!='active':
                if address in ADDRESSES:
                    if not msg & 0x10000:raise ValueError('non-active S12 read')
                    control.append((address,data))
                continue
            if index:
                if address in ADDRESSES:raise ValueError('unexpected multi-command S12 request')
                continue
            if slot in pending:raise ValueError('slot reused before observed S12 completion')
            if address in ADDRESSES:
                if msg not in (0x108,0x10108):raise ValueError('unexpected S12 message/response policy')
                pending[slot]=('write' if msg==0x10108 else 'read',address,data)
            continue
        done=DONE.search(line)
        if done:
            slot,address,data=int(done[1]),int(done[2],16),int(done[3],16)
            if address not in ADDRESSES:
                if slot in pending:raise ValueError('mismatched S12 completion')
                continue
            if slot not in pending:raise ValueError('S12 response has no request origin')
            kind,expected,sent=pending.pop(slot)
            if address!=expected or (kind=='write' and sent!=data):
                raise ValueError('S12 response disagrees with its originating request')
            completed.append((kind,address,data))
        elif ('rpmh_send_msg:' in line or 'rpmh_tx_done:' in line) and re.search(r'addr: 0x4010[048]\b',line):
            raise ValueError('unrecognized S12 controller or framing')
    if pending:raise ValueError('uncompleted S12 request')
    return completed,control

def verify(text,action):
    if action not in ('query','mode','held-enable','held-oem'):raise ValueError('unknown action')
    completed,control=transactions(text)
    before=6 if action in ('held-enable','held-oem') else 3
    reads=lambda mode,mv=1224:[('read',0x40100,mv),('read',0x40104,1),('read',0x40108,mode)]
    expected=reads(before)
    writes=[]
    if action=='mode':writes=[(0x40108,6)]
    if action in ('held-enable','held-oem'):writes=[(0x40100,1224),(0x40104,1)]
    expected += [('write',address,data) for address,data in writes]
    if action!='query':expected+=reads(6)
    if action=='held-oem':expected+=[('write',0x40100,1350),*reads(6,1350)]
    normalized=[]
    for kind,address,data in completed:
        if kind=='read':
            mask={0x40100:0x1fff,0x40104:1,0x40108:7}[address]
            if data & ~(0x80000000|mask):raise ValueError('unreviewed read bits')
            data &= mask
        normalized.append((kind,address,data))
    if normalized!=expected:raise ValueError('wrong or missing ordered read/write sequence')
    # Mirroring the declared initial mode into sleep/wake buffers is not a
    # voltage/enable operation. Keep every such write visible in the result.
    allowed_control={(0x40108,before),*writes}
    if action in ('held-enable','held-oem'):allowed_control.add((0x40108,6))
    if action=='held-oem':allowed_control.add((0x40100,1350))
    if any(item not in allowed_control for item in control):
        raise ValueError('unexpected S12 sleep/wake programming')
    return {'action':action,'completed':completed,'control_writes':control,'result':'PASS'}

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('usage: verify-s12-vote-trace.py TRACE ACTION')
    print(json.dumps(verify(Path(sys.argv[1]).read_text(),sys.argv[2]),indent=2))
