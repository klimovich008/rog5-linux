#!/usr/bin/env python3
"""Replay exact source observer with sealed BusyBox and synthetic kernel inputs.

Explicit artifact paths are required. This fixture cannot prove shutdown, USB
availability, UFS quiescence or receipt delivery on a physical phone.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import time

R=Path(__file__).resolve().parents[2]
S=importlib.util.spec_from_file_location('sealed_teardown',R/'scripts/host/source-teardown-observation.py')
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
BOOT='12345678-1234-4abc-8def-1234567890ab'
MOUNTS=('1 0 0:1 / / rw - tmpfs tmpfs rw\n'
 '2 1 0:2 / /oldsys/proc rw - proc proc rw\n'
 '3 1 0:3 / /oldsys/sys rw - sysfs sysfs rw\n'
 '4 1 0:4 / /oldsys/dev rw - devtmpfs devtmpfs rw\n')
STATEFUL=('stateful-clean','stateful-stopped-state','stateful-move-fail','stateful-root-busy',
          'stateful-detach-fail','stateful-detach-lies','stateful-wrong-backing','stateful-relock-fail',
          'stateful-order-loop0','stateful-order-loop1','stateful-order-relock','stateful-order-root',
          'stateful-order-state','stateful-order-userdata','stateful-journal-entry',
          'stateful-order-overlay-reference')
ORDER_REFUSALS={
    'stateful-order-loop0':['losetup','-d','/oldsys/dev/loop0'],
    'stateful-order-loop1':['losetup','-d','/oldsys/dev/loop1'],
    'stateful-order-relock':['blockdev','--setro','/oldsys/dev/sda23'],
    'stateful-order-root':['umount','/oldroot'],
    'stateful-order-state':['umount','/oldroot/.rog5/state'],
    'stateful-order-userdata':['umount','/oldroot/.rog5/userdata-rw'],
    'stateful-order-overlay-reference':['losetup','-d','/oldsys/dev/loop0'],
}
JOURNAL_ENTRY=('stateful-journal-entry','stateful-order-overlay-reference')

def stateful_inputs(root,case):
    for path in ('.rog5/root-ro','.rog5/userdata-ro','.rog5/userdata-rw','.rog5/state',
                 'sys','proc','run','dev','persist'):(root/'oldroot'/path).mkdir(parents=True,exist_ok=True)
    run=root/'oldsys/run';run.mkdir()
    record=('format=rog5-persistent-root-overlay-runtime-v1\n'+f'boot_id={BOOT}\n'+
            'disk=/dev/sda\nuserdata=/dev/sda23\nloop=/dev/loop0\n'+
            'image=rog5/root/root-overlay-v1.ext4\nmount=/mnt/state\nuserdata_mount=/mnt/userdata\n')
    (run/'rog5-persistent-overlay.runtime').write_text(record)
    state_stopped=case=='stateful-stopped-state' or case in JOURNAL_ENTRY
    if not state_stopped:
        (run/'rog5-persistent-state.runtime').write_text(
            'format=rog5-persistent-service-state-runtime-v1\n'+f'boot_id={BOOT}\n'+
            'disk=/dev/sda\nuserdata=/dev/sda23\nloop=/dev/loop1\n'+
            'image=rog5/state/server-state-v1.ext4\nmount=/persist\nuserdata_owner=overlay\n')
    for p in run.iterdir():p.chmod(0o400)
    nodes=[]
    for i in range(2):
        (root/f'oldsys/dev/loop{i}').touch();nodes.append(f'/oldsys/dev/loop{i}')
        if i==1 and state_stopped:continue
        p=root/f'oldsys/sys/class/block/loop{i}/loop';p.mkdir(parents=True)
        name='root/root-overlay-v1.ext4' if i==0 else 'state/server-state-v1.ext4'
        backing='/.rog5/userdata-rw/rog5/'+name
        if i==0 and case=='stateful-wrong-backing':backing='/.rog5/userdata-rw/unrelated.ext4'
        (p/'backing_file').write_text(backing+'\n')
    for i in range(117):
        node='sda'+(str(i) if i else '');nodes.append('/oldsys/dev/'+node)
        (root/f'oldsys/sys/class/block/{node}/ro').write_text('0\n' if i in (0,23) else '1\n')
    return nodes

def stateful_result(root,case,diagnostics):
    operations=(root/'operations').read_text().splitlines()
    final=struct.unpack('20i',(root/'mount-state').read_bytes())
    clean=case in ('stateful-clean','stateful-stopped-state','stateful-journal-entry')
    valid=True
    if case in ORDER_REFUSALS:
        initial=([0,0,1,0,1,1,1,1]+[0]*8+[1,0,1,0]) if case in JOURNAL_ENTRY else [1]*8+[0]*8+[1]*4
        valid=list(final)==initial and operations==[' '.join(ORDER_REFUSALS[case])]
    elif clean:
        ordered=['umount /oldroot','umount /oldsys/state','losetup -d /oldsys/dev/loop0',
                 'umount /oldsys/userdata-rw','blockdev --setro /oldsys/dev/sda']
        if case=='stateful-journal-entry':ordered[1]='mountpoint -q /oldsys/state'
        if case=='stateful-clean':
            ordered=['umount /oldroot/persist','losetup -d /oldsys/dev/loop1']+ordered
        positions=[operations.index(v) for v in ordered]
        relocks=[line for line in operations if line.startswith('blockdev --setro ')]
        expected={'blockdev --setro /oldsys/dev/sda'+(str(i) if i else '') for i in range(117)}
        valid=positions==sorted(positions) and len(relocks)==117 and set(relocks)==expected
        moved=[0,0,1,0,1,1,1,1] if case in JOURNAL_ENTRY else [1]*8
        valid &= not any(final[:8]+final[16:]) and list(final[8:16])==moved
        if case in JOURNAL_ENTRY:
            valid &= not any(v in operations for v in ('umount /oldsys/state','umount /oldsys/root-ro',
                                                      'losetup -d /oldsys/dev/loop1'))
    else:
        reached={
            'stateful-move-fail':'mount --move /oldroot/.rog5/userdata-rw /oldsys/userdata-rw',
            'stateful-root-busy':'umount /oldroot',
            'stateful-detach-fail':'losetup -d /oldsys/dev/loop0',
            'stateful-detach-lies':'losetup -d /oldsys/dev/loop0',
            'stateful-relock-fail':'blockdev --setro /oldsys/dev/sda23',
            'stateful-wrong-backing':'umount /oldsys/state',
        }
        valid=reached[case] in operations
        if case=='stateful-wrong-backing':valid &= 'losetup -d /oldsys/dev/loop0' not in operations
        if case=='stateful-relock-fail':valid &= (root/'oldsys/sys/class/block/sda23/ro').read_text()=='0\n'
    if case not in ORDER_REFUSALS:
        # Observe the actual shutdown argument, not merely the missing receipt.
        wanted=f'timeout -s KILL 5 /bin/busybox sh /rog5-source-teardown {int(clean)} reboot'
        if diagnostics:wanted+=' --diagnostics'
        valid &= [v for v in operations if v.startswith('timeout ')]==[wanted]
    return dict(valid=bool(valid),operation_count=len(operations),
                operations_sha256=M.sha((root/'operations').read_bytes()),
                final_mount_state=list(final),scope='synthetic mount/loop/ioctl state; unchanged shell')

def run(args):
    out=args.output;out.mkdir(mode=0o700);started=time.monotonic()
    if not all(p.is_absolute() and p.is_file() for p in (args.busybox,args.loader,args.qemu)):
        raise ValueError('absolute sealed artifact paths required')
    shim=out/'shim'
    subprocess.run(['cc','-static','-O2','-Wall','-Wextra','-Werror',str(R/'tests/fixtures/source-teardown/shim.c'),'-o',str(shim)],check=True,timeout=30)
    original=(R/'initramfs/persistent-root-shutdown-standalone').read_bytes()
    expected,files=M.prepare(original,M.sha(original),dict(boot_id=BOOT,serial='FIXTURE123',
                            bundle='headless-server-fixture',release='7.1.4-fixture'),'a'*64,
                            diagnostics=args.diagnostics)
    cases=('clean','unclean-flag','wrong-action','wrong-boot','wrong-release','wrong-hash','file-writable',
       'file-symlink','checksum-extra','intent-extra','physical-mount','unknown-mount','missing-proc',
       'bad-mount-device','attached-loop','dangling-loop','sysfs-writable','ioctl-writable','wrong-node',
       'missing-node','missing-physical','extra-physical','network-fail','assembled-clean',
       'assembled-unclean-shutdown','assembled-network-fail','assembled-network-hang','real-netcat',
       'hugetlbfs','hugetlbfs-physical-device','hugetlbfs-with-physical-mount','assembled-hugetlbfs',
       'assembled-receiver-poll')
    if args.diagnostics:cases+=('assembled-diagnostic-hang',)
    if args.inert_block_node:
        node=args.inert_block_node
        metadata=node.lstat()
        if not node.is_absolute() or not stat.S_ISBLK(metadata.st_mode) or metadata.st_rdev!=0:
            raise ValueError('only an inert major/minor 0:0 block node is allowed')
        cases+=STATEFUL
    if args.case:
        if any(case not in cases for case in args.case):raise ValueError('unknown replay case')
        cases=tuple(args.case)
    results=[]
    for case in cases:
        root=out/case;root.mkdir()
        for name,raw in files.items():
            p=root/name;p.write_bytes(raw);p.chmod(0o755 if name=='shutdown' else 0o444)
        for directory in ('bin','lib','sealed','oldsys/proc/self','oldsys/proc/sys/kernel/random',
                          'oldsys/sys/class/block','oldsys/dev','usr/libexec'):(root/directory).mkdir(parents=True,exist_ok=True)
        (root/'oldsys/proc/sys/kernel/random/boot_id').write_text(BOOT+'\n')
        (root/'oldsys/proc/self/mountinfo').write_text(MOUNTS)
        if 'hugetlbfs' in case:
            p=root/'oldsys/proc/self/mountinfo'
            raw=(R/'tests/fixtures/source-teardown/hugetlbfs.mountinfo').read_text()
            if case=='hugetlbfs-physical-device':raw=raw.replace('0:35','259:58')
            if case=='hugetlbfs-with-physical-mount':
                raw+='90 1 259:58 / /residual rw - ext4 /dev/sda23 rw\n'
            p.write_text(MOUNTS+raw)
        (root/'scenario').write_text(case.removeprefix('assembled-'))
        for i in range(117):
            node='sda'+(str(i) if i else '')
            p=root/'oldsys/sys/class/block'/node;p.mkdir();(p/'dev').write_text(f'259:{i}\n');(p/'ro').write_text('1\n')
            (root/'oldsys/dev'/node).touch()
        if case=='wrong-boot':(root/'oldsys/proc/sys/kernel/random/boot_id').write_text('different\n')
        if case in ('wrong-release','intent-extra'):
            p=root/'rog5-source-teardown.intent';p.chmod(0o644)
            p.write_bytes(p.read_bytes().replace(b'7.1.4-fixture',b'7.1.4-other') if case=='wrong-release' else p.read_bytes()+b'nonce='+b'a'*64+b'\n');p.chmod(0o444)
            # Exercise the intent parser after valid checksum verification.
            p=root/'rog5-source-teardown.sha256';p.chmod(0o644)
            p.write_bytes(b''.join(M.sha((root/n).read_bytes()).encode()+b'  '+n.encode()+b'\n' for n in ('shutdown','rog5-source-teardown','rog5-source-teardown.intent')));p.chmod(0o444)
        if case=='wrong-hash':
            p=root/'shutdown';p.write_bytes(p.read_bytes()+b'\n')
        if case=='file-writable':(root/'rog5-source-teardown.intent').chmod(0o644)
        if case=='file-symlink':
            p=root/'rog5-source-teardown.intent';p.rename(root/'linked-intent');p.symlink_to('linked-intent')
        if case=='checksum-extra':
            p=root/'rog5-source-teardown.sha256';p.chmod(0o644);p.write_bytes(p.read_bytes()+b'extra\n');p.chmod(0o444)
        if case in ('physical-mount','unknown-mount','bad-mount-device','missing-proc'):
            p=root/'oldsys/proc/self/mountinfo';raw=p.read_text()
            if case=='physical-mount':raw+='5 1 259:58 / /residual rw - ext4 /dev/sda23 rw\n'
            if case=='unknown-mount':raw+='5 1 0:8 / /residual rw - overlay overlay rw\n'
            if case=='bad-mount-device':raw=raw.replace('0:4','259:58')
            if case=='missing-proc':raw=''.join(line+'\n' for line in raw.splitlines() if '/oldsys/proc ' not in line)
            p.write_text(raw)
        if case in ('attached-loop','dangling-loop'):
            p=root/'oldsys/sys/class/block/loop0';p.mkdir()
            if case=='attached-loop':(p/'loop').mkdir()
            else:(p/'loop').symlink_to('missing')
        if case=='sysfs-writable':(root/'oldsys/sys/class/block/sda23/ro').write_text('0\n')
        if case=='missing-node':(root/'oldsys/dev/sda23').unlink()
        if case=='missing-physical':shutil.rmtree(root/'oldsys/sys/class/block/sda23')
        if case=='extra-physical':
            p=root/'oldsys/sys/class/block/sda117';p.mkdir();(p/'dev').write_text('259:117\n');(p/'ro').write_text('1\n');(root/'oldsys/dev/sda117').touch()
        stateful=case in STATEFUL
        nodes=stateful_inputs(root,case) if stateful else []
        command=['bwrap','--unshare-all','--die-with-parent','--new-session','--uid','0','--gid','0',
          '--cap-add','CAP_NET_ADMIN','--bind',str(root),'/',
          '--dev','/dev','--ro-bind',str(args.busybox),'/sealed/busybox','--ro-bind',str(args.loader),'/lib/ld-musl-aarch64.so.1',
          '--ro-bind',str(args.qemu),'/qemu','--ro-bind',str(shim),'/bin/busybox','--ro-bind',str(shim),'/usr/libexec/rog5-reboot-bootloader',
          '--clearenv']
        for node in nodes:command+=['--ro-bind',str(args.inert_block_node),node]
        assembled=case.startswith('assembled-') or (stateful and case not in ORDER_REFUSALS)
        if case=='assembled-receiver-poll':
            (root/'expected.json').write_text(json.dumps(expected))
            command+=['--ro-bind','/usr','/usr','--ro-bind','/usr/lib','/lib64',
                      '--tmpfs','/usr/libexec','--ro-bind',str(shim),'/usr/libexec/rog5-reboot-bootloader',
                      '--ro-bind',str(R),'/repo','/usr/bin/python3','-B',
                      '/repo/tests/fixtures/source-teardown/receiver-poll.py']
        elif case in ORDER_REFUSALS:command+=['/bin/busybox',*ORDER_REFUSALS[case]]
        else:
            command+=['/qemu','/lib/ld-musl-aarch64.so.1','/sealed/busybox','sh']
            command+=['/shutdown','reboot'] if assembled else ['/rog5-source-teardown','0' if case=='unclean-flag' else '1','poweroff' if case=='wrong-action' else 'reboot']
            if args.diagnostics and not assembled:command+=['--diagnostics']
        begin=time.monotonic()
        done=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        seconds=time.monotonic()-begin;(root/'stdout').write_bytes(done.stdout);(root/'stderr').write_bytes(done.stderr)
        receipt=(root/'receipt').read_bytes() if (root/'receipt').exists() else None
        wants_receipt=case in ('clean','assembled-clean','real-netcat','hugetlbfs','assembled-hugetlbfs',
                              'stateful-clean','stateful-stopped-state','stateful-journal-entry')
        wants_receipt |= case=='assembled-receiver-poll'
        valid=(receipt is not None)==wants_receipt
        if receipt is not None:M.parse(receipt,expected)
        if not assembled:valid &= (done.returncode==0)==wants_receipt
        else:valid &= (root/'fallback').is_file() and (root/'fallback').read_text()=='requested\n' and seconds<8
        if case in ORDER_REFUSALS:valid &= done.returncode==1
        observations=[]
        if args.diagnostics:
            observation=M.Observation(expected,BOOT,0)
            for i,p in enumerate(sorted(root.glob('diagnostic-*'))):
                observations.append(observation.diagnose(p.read_bytes(),i+1))
            if receipt is not None:observation.observe(receipt,len(observations)+1)
            phase=None
            if case in ('unclean-flag','assembled-unclean-shutdown') or (stateful and
                case not in ORDER_REFUSALS and case not in ('stateful-clean','stateful-stopped-state','stateful-journal-entry')):
                phase='teardown'
            elif case in ('physical-mount','unknown-mount','missing-proc','bad-mount-device',
                          'hugetlbfs-physical-device','hugetlbfs-with-physical-mount'):phase='mounts'
            elif case in ('attached-loop','dangling-loop'):phase='loops'
            elif case in ('sysfs-writable','ioctl-writable','wrong-node','missing-node',
                          'missing-physical','extra-physical'):phase='physical'
            if phase:
                valid &= bool(observations) and observations[-1]['record']['phase']==phase
                valid &= bool(observations) and observations[-1]['record']['state']=='fail' and observation.failed
            elif case=='assembled-diagnostic-hang':
                valid &= len(observations)==1 and observations[0]['record']['phase']=='teardown'
                valid &= not observation.failed and 5<=seconds<8
            elif not wants_receipt:valid &= not observations
        else:valid &= not list(root.glob('diagnostic-*'))
        attempts=len((root/'nc-attempts').read_text().splitlines()) if (root/'nc-attempts').exists() else 0
        if case in ('network-fail','assembled-network-fail'):valid &= attempts==(2 if args.diagnostics else 1)
        if case=='assembled-network-hang':valid &= attempts==1
        if case=='assembled-diagnostic-hang':valid &= attempts==2
        if case=='assembled-receiver-poll':
            p=root/'receiver-poll.json'
            integrated=json.loads(p.read_text()) if p.is_file() else {}
            valid &= done.returncode==0 and integrated.get('status')=='PASS' and integrated.get('seconds',99)<8
        state=stateful_result(root,case,args.diagnostics) if stateful else None
        if state:valid &= state['valid']
        results.append(dict(case=case,status='PASS' if valid else 'FAIL',returncode=done.returncode,
                            receipt=receipt is not None,seconds=seconds,stateful=state,
                            diagnostic_records=[v['record'] for v in observations],send_attempts=attempts))
        print(json.dumps(results[-1]),flush=True)
        if not valid:break
    result=dict(status='PASS' if len(results)==len(cases) and all(v['status']=='PASS' for v in results) else 'FAIL',
       seconds=time.monotonic()-started,cases=results,source_shutdown_sha256=M.sha(original),observer_sha256=expected['observer_sha256'],
       generated_shutdown_sha256=expected['shutdown_sha256'],busybox_sha256=M.sha(args.busybox.read_bytes()),
       replay_sha256=M.sha(Path(__file__).read_bytes()),shim_source_sha256=M.sha((R/'tests/fixtures/source-teardown/shim.c').read_bytes()),
       hugetlbfs_fixture_sha256=M.sha((R/'tests/fixtures/source-teardown/hugetlbfs.mountinfo').read_bytes()),
       stateful_source_sha256=M.sha((R/'tests/fixtures/source-teardown/stateful.h').read_bytes()),
       receiver_fixture_sha256=M.sha((R/'tests/fixtures/source-teardown/receiver-poll.py').read_bytes()),
       loader_sha256=M.sha(args.loader.read_bytes()),qemu_sha256=M.sha(args.qemu.read_bytes()),
       synthetic=['kernel identity','mountinfo','sysfs','device metadata','blockdev ioctl','network sender','mount operations','reboot helper'],
       phone_action=False,qualification_authority='none')
    result['diagnostics']=args.diagnostics
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result['status']!='PASS'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('busybox','loader','qemu','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--case',action='append',help='run only named changed/new scenarios')
    p.add_argument('--inert-block-node',type=Path,help='optional existing inert 0:0 node for stateful shell cases; never opened')
    p.add_argument('--diagnostics',action='store_true',help='exercise opt-in bounded phase diagnostics')
    raise SystemExit(run(p.parse_args()))
