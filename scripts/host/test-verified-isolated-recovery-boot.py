#!/usr/bin/env python3
"""Exact R01 RAM image and capacity gates; no fastboot/device invocation."""
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
S=importlib.util.spec_from_file_location('isolated_boot_test',Path(__file__).with_name('verified-isolated-recovery-boot.py'))
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
PIN='a'*64

def record():
    return dict(candidate=M.PROFILE,target_bundle=M.PROFILE,qualification='isolated-failure-r01',
                execution='fastboot-boot-ram-bundle',ram_boot_image_size=str(M.IMAGE_SIZE),serial=M.SERIAL,
                product='lahaina',usb_path='1-1.2',expected_slot='b',flash='forbidden',attempt_limit='1',boot_image_sha256=PIN)

def encode(value):return ''.join(k+'='+v+'\n' for k,v in value.items()).encode()

class Tests(unittest.TestCase):
    def test_capacity_requires_one_successful_bounded_response(self):
        for stdout,stderr in ((b'',b'(bootloader) max-download-size: 536870912\nFinished. Total time: 0.002s\n'),
                              (b'max-download-size: 0x30000000\n',b'total time: 0.001s\n')):
            value=M.capacity(subprocess.CompletedProcess([],0,stdout,stderr));self.assertGreaterEqual(value,M.IMAGE_SIZE)
        for result in (subprocess.CompletedProcess([],1,b'',b'failed'),
                       subprocess.CompletedProcess([],0,b'',b'max-download-size: 100663296\n'),
                       subprocess.CompletedProcess([],0,b'',b'max-download-size: 536870912\n'*2),
                       subprocess.CompletedProcess([],0,b'',b'max-download-size: 536870912\nmax-download-size: 805306368\n'),
                       subprocess.CompletedProcess([],0,b'',b'max-download-size: 4294967295\n'),
                       subprocess.CompletedProcess([],0,b'',b'max-download-size: 536870912\nunknown error\n')):
            with self.subTest(result=result),self.assertRaises(ValueError):M.capacity(result)
    def test_capacity_query_and_replay_bind_fixed_serial_and_raw_bytes(self):
        result=subprocess.CompletedProcess([],0,b'',b'(bootloader) max-download-size: 536870912\n')
        with patch.object(M.BASE,'validate_fastboot'),patch.object(M.subprocess,'run',return_value=result) as run:
            proof=M.download_capacity(M.SERIAL)
            self.assertEqual(run.call_args.args[0],[str(M.BASE.FASTBOOT),'-s',M.SERIAL,'getvar','max-download-size'])
            self.assertEqual(M.replay_capacity(proof),536870912)
            with self.assertRaises(ValueError):M.download_capacity('another-phone')
            self.assertEqual(run.call_count,1)
        proof['max_download_size']=805306368
        with self.assertRaises(ValueError):M.replay_capacity(proof)
    def test_canonical_image_requires_consumed_exact_ram_only_profile(self):
        with patch.object(M.CLAIMS,'expected_record',return_value=encode(record())),patch.object(M.CLAIMS,'verify_entered') as verify:
            self.assertEqual(M.canonical(PIN,M.SERIAL),record());verify.assert_called_once_with(M.PROFILE)
        for key,changed in (('ram_boot_image_size','100663296'),('execution','flash'),('flash','allowed'),
                             ('qualification','other'),('serial','other'),('expected_slot','a'),('boot_image_sha256','b'*64)):
            value=record();value[key]=changed
            with self.subTest(key=key),patch.object(M.CLAIMS,'expected_record',return_value=encode(value)),patch.object(M.CLAIMS,'verify_entered') as verify:
                with self.assertRaises(ValueError):M.canonical(PIN,M.SERIAL)
                verify.assert_not_called()
        with patch.object(M.CLAIMS,'expected_record',return_value=encode(record())),patch.object(M.CLAIMS,'verify_entered',side_effect=ValueError('unconsumed')):
            with self.assertRaises(ValueError):M.canonical(PIN,M.SERIAL)
    def test_exact_real_snapshot_is_fully_sealed_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            image=Path(temporary)/'image';image.write_bytes(b'fixture')
            with image.open('r+b') as f:f.truncate(M.IMAGE_SIZE)
            image.chmod(0o600)
            with image.open('rb') as f:pin=hashlib.file_digest(f,'sha256').hexdigest()
            fd=M.sealed_snapshot(image,pin)
            try:
                self.assertEqual(os.fstat(fd).st_size,M.IMAGE_SIZE)
                seals=fcntl.F_SEAL_SEAL|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_GROW|fcntl.F_SEAL_WRITE
                self.assertEqual(fcntl.fcntl(fd,fcntl.F_GET_SEALS),seals)
                with self.assertRaises(OSError):os.write(fd,b'changed')
            finally:os.close(fd)
            with self.assertRaises(ValueError):M.sealed_snapshot(image,'b'*64)
    def test_wrong_size_links_or_writable_metadata_refuse_before_memory_allocation(self):
        for case in ('old-size','symlink','hardlink','writable'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temporary:
                image=Path(temporary)/'image';image.touch();image.chmod(0o600)
                with image.open('r+b') as f:f.truncate(M.BASE.PARTITION_SIZE if case=='old-size' else M.IMAGE_SIZE)
                if case=='symlink':
                    link=image.with_name('link');link.symlink_to(image);image=link
                if case=='hardlink':image.with_name('link').hardlink_to(image)
                if case=='writable':image.chmod(0o666)
                with patch.object(M.os,'memfd_create') as create:
                    with self.assertRaises((ValueError,OSError)):M.sealed_snapshot(image,PIN)
                    create.assert_not_called()
    def test_boot_dispatches_once_with_sealed_fd_and_closes_it_on_failure(self):
        for fail in (False,True):
            with self.subTest(fail=fail):
                fd=os.memfd_create('fixture');seen=[]
                def run(argv,**kwargs):
                    seen.append(argv);self.assertEqual(kwargs['pass_fds'],(fd,));self.assertTrue(kwargs['check'])
                    if fail:raise subprocess.CalledProcessError(1,argv)
                with patch.dict(M.os.environ,ALLOW_TEMPORARY_BOOT='1',ALLOW_HEADLESS_LIVE_GATE='1'),\
                     patch.object(M,'canonical') as canonical,patch.object(M.BASE,'validate_fastboot'),\
                     patch.object(M,'sealed_snapshot',return_value=fd),patch.object(M.subprocess,'run',side_effect=run):
                    if fail:
                        with self.assertRaises(subprocess.CalledProcessError):M.boot(Path('/fixture'),PIN,M.SERIAL)
                    else:M.boot(Path('/fixture'),PIN,M.SERIAL)
                    canonical.assert_called_once_with(PIN,M.SERIAL)
                self.assertEqual(seen,[[str(M.BASE.FASTBOOT),'-s',M.SERIAL,'boot',f'/proc/self/fd/{fd}']])
                with self.assertRaises(OSError):os.fstat(fd)
    def test_no_implicit_boot_or_change_to_legacy_size(self):
        with patch.dict(M.os.environ,{},clear=True),patch.object(M.subprocess,'run') as run:
            with self.assertRaises(ValueError):M.boot(Path('/fixture'),PIN,M.SERIAL)
            run.assert_not_called()
        self.assertEqual(M.BASE.PARTITION_SIZE,100663296)

if __name__=='__main__':unittest.main()
