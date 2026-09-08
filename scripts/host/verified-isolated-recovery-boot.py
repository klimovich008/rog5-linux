#!/usr/bin/env python3
"""One canonical R01-only 128 MiB RAM image; existing boot helpers stay unchanged.

This helper has no CLI and cannot flash. Size is an exact candidate property,
not a partition resize or a general relaxation of the existing 96 MiB helper.
"""
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import subprocess

HERE=Path(__file__).resolve().parent
PROFILE='headless-recovery-negative-v1'
SERIAL='M5AIKN00F0353YH'
IMAGE_SIZE=134217728


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


BASE=load('isolated_existing_fastboot',HERE/'verified-fastboot-boot.py')
CLAIMS=load('isolated_existing_claims',HERE/'consume-exact-boot-claim.py')


def need(value,message):
    if not value:raise ValueError(message)


def capacity(result):
    """A single successful getvar response; contradictory duplicates refuse."""
    need(type(result.returncode) is int and result.returncode==0 and
         type(result.stdout) is bytes and type(result.stderr) is bytes and
         len(result.stdout)+len(result.stderr)<=4096,'failed or oversized download-capacity query')
    values=[]
    for line in (result.stdout+b'\n'+result.stderr).decode('ascii').splitlines():
        if not line:continue
        match=re.fullmatch(r'(?:\(bootloader\) )?max-download-size:\s*(0x[0-9a-fA-F]{1,8}|[0-9]{1,10})',line)
        if match:
            text=match[1];values.append(int(text,16 if text.startswith('0x') else 10));continue
        need(re.fullmatch(r'(?:Finished\. Total time:|total time:) [0-9]+\.[0-9]+s',line),
             'unexpected download-capacity response')
    need(len(values)==1 and IMAGE_SIZE<=values[0]<=1073741824,
         'ambiguous or insufficient reviewed RAM download capacity')
    return values[0]


def download_capacity(serial):
    need(serial==SERIAL,'wrong isolated recovery serial')
    BASE.validate_fastboot()
    result=subprocess.run([str(BASE.FASTBOOT),'-s',serial,'getvar','max-download-size'],
                          stdin=subprocess.DEVNULL,capture_output=True,timeout=10)
    maximum=capacity(result)
    return dict(max_download_size=maximum,returncode=result.returncode,
                stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex())


def replay_capacity(value):
    need(set(value)=={'max_download_size','returncode','stdout_hex','stderr_hex'}
         and type(value['max_download_size']) is int,'download-capacity evidence fields')
    raw=[]
    for name in ('stdout_hex','stderr_hex'):
        text=value[name];need(type(text) is str and len(text)<=8192 and len(text)%2==0
                             and re.fullmatch('[0-9a-f]*',text),'capacity response encoding')
        raw.append(bytes.fromhex(text))
    actual=capacity(subprocess.CompletedProcess([],value['returncode'],*raw))
    need(actual==value['max_download_size'],'capacity summary differs from raw response')
    return actual


def canonical(expected_sha256,serial):
    need(serial==SERIAL and BASE.SHA256.fullmatch(expected_sha256)
         and expected_sha256!='0'*64,'invalid isolated image identity')
    rows=[line.split('=',1) for line in CLAIMS.expected_record(PROFILE).decode('ascii').splitlines()]
    need(all(len(row)==2 for row in rows) and len({row[0] for row in rows})==len(rows),'ambiguous canonical R01 record')
    record=dict(rows)
    required=dict(candidate=PROFILE,target_bundle=PROFILE,qualification='isolated-failure-r01',
                  execution='fastboot-boot-ram-bundle',ram_boot_image_size=str(IMAGE_SIZE),
                  serial=SERIAL,product='lahaina',usb_path='1-1.2',expected_slot='b',
                  flash='forbidden',attempt_limit='1',boot_image_sha256=expected_sha256)
    need(all(record.get(key)==value for key,value in required.items()),'not the exact canonical isolated RAM image')
    CLAIMS.verify_entered(PROFILE)
    return record


def sealed_snapshot(image,expected_sha256):
    """Snapshot one exact-size owner-controlled image, then irreversibly seal it."""
    image=Path(image)
    need(image.is_absolute() and image.resolve()==image and BASE.SHA256.fullmatch(expected_sha256),
         'canonical isolated image path/hash required')
    source=os.open(image,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC);snapshot=-1
    try:
        before=os.fstat(source)
        need(stat.S_ISREG(before.st_mode) and before.st_uid==os.geteuid() and before.st_nlink==1
             and not stat.S_IMODE(before.st_mode)&0o022 and before.st_size==IMAGE_SIZE,
             'isolated RAM image metadata is unsafe')
        snapshot=os.memfd_create('rog5-isolated-recovery-boot',os.MFD_ALLOW_SEALING|os.MFD_CLOEXEC)
        digest=hashlib.sha256();observed=0
        while block:=os.read(source,1048576):
            digest.update(block);observed+=len(block);view=memoryview(block)
            while view:
                written=os.write(snapshot,view);need(written>0,'isolated snapshot write made no progress');view=view[written:]
        need(observed==IMAGE_SIZE and BASE.file_identity(before)==BASE.file_identity(os.fstat(source))
             and BASE.file_identity(before)==BASE.file_identity(image.lstat())
             and digest.hexdigest()==expected_sha256,'isolated RAM image changed or has the wrong hash')
        os.fchmod(snapshot,0o400)
        seals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
        fcntl.fcntl(snapshot,fcntl.F_ADD_SEALS,seals)
        need(fcntl.fcntl(snapshot,fcntl.F_GET_SEALS)==seals,'isolated snapshot is not fully sealed')
        os.lseek(snapshot,0,os.SEEK_SET);return snapshot
    except BaseException:
        if snapshot>=0:os.close(snapshot)
        raise
    finally:os.close(source)


def boot(image,expected_sha256,serial):
    need(os.environ.get('ALLOW_TEMPORARY_BOOT')=='1' and os.environ.get('ALLOW_HEADLESS_LIVE_GATE')=='1',
         'explicit isolated execution environment required')
    canonical(expected_sha256,serial)
    BASE.validate_fastboot()
    snapshot=sealed_snapshot(image,expected_sha256)
    try:
        subprocess.run([str(BASE.FASTBOOT),'-s',serial,'boot',f'/proc/self/fd/{snapshot}'],
                       check=True,stdin=subprocess.DEVNULL,pass_fds=(snapshot,))
    finally:os.close(snapshot)


if __name__=='__main__':raise SystemExit('Import-only exact R01 helper; the admitted one-use controller is required')
