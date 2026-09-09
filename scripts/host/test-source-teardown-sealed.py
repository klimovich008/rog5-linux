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

def run(args):
    out=args.output;out.mkdir(mode=0o700);started=time.monotonic()
    if not all(p.is_absolute() and p.is_file() for p in (args.busybox,args.loader,args.qemu)):
        raise ValueError('absolute sealed artifact paths required')
    shim=out/'shim'
    subprocess.run(['cc','-static','-O2','-Wall','-Wextra','-Werror',str(R/'tests/fixtures/source-teardown/shim.c'),'-o',str(shim)],check=True,timeout=30)
    original=(R/'initramfs/persistent-root-shutdown-standalone').read_bytes()
    expected,files=M.prepare(original,M.sha(original),dict(boot_id=BOOT,serial='FIXTURE123',
                            bundle='headless-server-fixture',release='7.1.4-fixture'),'a'*64)
    cases=('clean','unclean-flag','wrong-action','wrong-boot','wrong-release','wrong-hash','file-writable',
       'file-symlink','checksum-extra','intent-extra','physical-mount','unknown-mount','missing-proc',
       'bad-mount-device','attached-loop','dangling-loop','sysfs-writable','ioctl-writable','wrong-node',
       'missing-node','missing-physical','extra-physical','network-fail','assembled-clean',
       'assembled-unclean-shutdown','assembled-network-fail','assembled-network-hang','real-netcat',
       'hugetlbfs','hugetlbfs-physical-device','hugetlbfs-with-physical-mount','assembled-hugetlbfs')
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
        command=['bwrap','--unshare-all','--die-with-parent','--new-session','--uid','0','--gid','0',
          '--cap-add','CAP_NET_ADMIN','--bind',str(root),'/',
          '--dev','/dev','--ro-bind',str(args.busybox),'/sealed/busybox','--ro-bind',str(args.loader),'/lib/ld-musl-aarch64.so.1',
          '--ro-bind',str(args.qemu),'/qemu','--ro-bind',str(shim),'/bin/busybox','--ro-bind',str(shim),'/usr/libexec/rog5-reboot-bootloader',
          '--clearenv','/qemu','/lib/ld-musl-aarch64.so.1','/sealed/busybox','sh']
        assembled=case.startswith('assembled-')
        command+=['/shutdown','reboot'] if assembled else ['/rog5-source-teardown','0' if case=='unclean-flag' else '1','poweroff' if case=='wrong-action' else 'reboot']
        begin=time.monotonic()
        done=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        seconds=time.monotonic()-begin;(root/'stdout').write_bytes(done.stdout);(root/'stderr').write_bytes(done.stderr)
        receipt=(root/'receipt').read_bytes() if (root/'receipt').exists() else None
        wants_receipt=case in ('clean','assembled-clean','real-netcat','hugetlbfs','assembled-hugetlbfs')
        valid=(receipt is not None)==wants_receipt
        if receipt is not None:M.parse(receipt,expected)
        if not assembled:valid &= (done.returncode==0)==wants_receipt
        else:valid &= (root/'fallback').read_text()=='requested\n' and seconds<8
        results.append(dict(case=case,status='PASS' if valid else 'FAIL',returncode=done.returncode,
                            receipt=receipt is not None,seconds=seconds))
        print(json.dumps(results[-1]),flush=True)
        if not valid:break
    result=dict(status='PASS' if len(results)==len(cases) and all(v['status']=='PASS' for v in results) else 'FAIL',
       seconds=time.monotonic()-started,cases=results,source_shutdown_sha256=M.sha(original),observer_sha256=expected['observer_sha256'],
       generated_shutdown_sha256=expected['shutdown_sha256'],busybox_sha256=M.sha(args.busybox.read_bytes()),
       replay_sha256=M.sha(Path(__file__).read_bytes()),shim_source_sha256=M.sha((R/'tests/fixtures/source-teardown/shim.c').read_bytes()),
       hugetlbfs_fixture_sha256=M.sha((R/'tests/fixtures/source-teardown/hugetlbfs.mountinfo').read_bytes()),
       loader_sha256=M.sha(args.loader.read_bytes()),qemu_sha256=M.sha(args.qemu.read_bytes()),
       synthetic=['kernel identity','mountinfo','sysfs','device metadata','blockdev ioctl','network sender','mount operations','reboot helper'],
       phone_action=False,qualification_authority='none')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result['status']!='PASS'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('busybox','loader','qemu','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--case',action='append',help='run only named changed/new scenarios')
    raise SystemExit(run(p.parse_args()))
