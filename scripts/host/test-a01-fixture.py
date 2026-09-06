#!/usr/bin/env python3
"""Test-only fixture provenance; no phone or production module insertion."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('composition',Path(__file__).with_name('check-rescue-root-composition.py'))
C=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(C)


class FixtureTest(unittest.TestCase):
    def test_fixture_must_bind_exact_kernel_source_config_and_module(self):
        F=C.load('fixture','scripts/host/rog5_a01_fixture.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'clean-b').mkdir();(root/'module').mkdir()
            magic='7.1.4-g'+12*'a'+' SMP preempt mod_unload aarch64'
            config=b'CONFIG_DEBUG_INFO_BTF_MODULES=y\n# CONFIG_MODULE_ALLOW_BTF_MISMATCH is not set\n'
            elf=bytearray(64);elf[:6]=b'\x7fELF\x02\x01';elf[16:20]=b'\x01\x00\xb7\x00'
            inputs={'clean-b/.config':config,'clean-b/vmlinux':b'vmlinux',
                    'clean-b/Module.symvers':b'symbols','module/rog5_a01_s12_shim.ko':bytes(elf),
                    'module/rog5_a01_s12_shim.c':F.SOURCE.read_bytes()}
            for name,data in inputs.items():(root/name).write_bytes(data)
            record=dict(status='PASS',source_commit='a'*40,vermagic=magic,
                        fixture_source_sha256=F.digest(F.SOURCE.read_bytes()),
                        module_sha256=F.digest(bytes(elf)),
                        kit_hashes={name:F.digest(inputs['clean-b/'+name]) for name in ('.config','vmlinux','Module.symvers')})
            receipt=root/'result.json';receipt.write_text(json.dumps(record))
            calls=[]
            def run(args,**kwargs):
                calls.append(args)
                self.assertLessEqual(kwargs['timeout'],10)
                if args[0]=='modinfo':
                    return dict(vermagic=magic,name='rog5_a01_s12_shim',depends='')[args[2]]+'\n'
                Path(args[-1]).write_bytes(b'Image')
                return subprocess.CompletedProcess(args,0)
            with patch.object(F.subprocess,'check_output',side_effect=run),patch.object(F.subprocess,'run',side_effect=run),patch.object(F.shutil,'which',side_effect=lambda x:x):
                for absent in (None,root/'absent'):
                    with self.assertRaises(F.FixtureUnavailable):F.load_fixture(absent,F.digest(b'Image'),magic)
                data,proof=F.load_fixture(root,F.digest(b'Image'),magic)
                self.assertEqual(data,bytes(elf));self.assertEqual(proof['kernel_sha256'],F.digest(b'Image'))
                self.assertFalse(proof['production_provider'])
                for key,value in [('status','FAIL'),('module_sha256','0'*64),('fixture_source_sha256','0'*64),('source_commit','b'*40),('vermagic','wrong')]:
                    bad=copy.deepcopy(record);bad[key]=value;receipt.write_text(json.dumps(bad))
                    with self.subTest(key=key),self.assertRaises(ValueError):F.load_fixture(root,F.digest(b'Image'),magic)
                receipt.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'kernel'):F.load_fixture(root,F.digest(b'wrong'),magic)
                for bad in ('[]','null','{"status":"PASS","status":"PASS"}'):
                    receipt.write_text(bad)
                    with self.assertRaises(ValueError):F.load_fixture(root,F.digest(b'Image'),magic)
                receipt.write_text(json.dumps(record))
                module=root/'module/rog5_a01_s12_shim.ko';module.unlink();module.symlink_to(root/'clean-b/vmlinux')
                with self.assertRaises(ValueError):F.load_fixture(root,F.digest(b'Image'),magic)
            self.assertTrue(any(x[0]=='llvm-objcopy' for x in calls))

    def test_split_markers_do_not_substitute_for_real_provider_or_hide_missing_btf(self):
        base='\n'.join('COMPOSITION_'+name+'_PASS' for name in C.MARKERS)+'\nCOMPOSITION_VM_COMPLETE\n'
        rows=[{'name':'rog5_s12_ufs_vote'}]
        real='COMPOSITION_HELPER_rog5_s12_ufs_vote_REFUSED_ENODEV\n'
        split='COMPOSITION_CONSUMER_rog5_wifi_activate_REFUSED_ENODEV\nCOMPOSITION_ACTIVATION_SPLIT_PASS\n'
        self.assertTrue(C.vm_runtime_passed(base+real+split,0,[],refusals=rows,activation=True))
        for fault in (base+split,base+real,base+real+split+split,base+real+split.replace('CONSUMER','HELPER')):
            self.assertFalse(C.vm_runtime_passed(fault,0,[],refusals=rows,activation=True))
        self.assertFalse(C.vm_runtime_passed(base+real+split,0,[],refusals=rows))
        script=C.activation_refusal_driver()
        self.assertEqual(script.count('/rog5-native-wifi/module-once '),1)
        for check in ('btf_coming)" = 1','consumer_live)" = 0','validator_calls)" = 0','rmmod rog5_a01_s12_shim'):
            self.assertIn(check,script)

    def test_split_driver_rejects_wrong_counters_refusal_and_failed_cleanup(self):
        for fault in ('','missing-btf','called','no-coming','duplicate-coming','live','errno','cleanup','real-provider'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'run').mkdir();(root/'btf').mkdir()
                modules=root/'modules';params=modules/'rog5_a01_s12_shim/parameters';params.mkdir(parents=True)
                for name,value in (('validator_calls','1' if fault=='called' else '0'),
                                   ('consumer_live','1' if fault=='live' else '0'),
                                   ('btf_coming','0' if fault=='no-coming' else '2' if fault=='duplicate-coming' else '1')):
                    (params/name).write_text(value+'\n')
                (root/'btf/rog5_a01_s12_shim').write_text('' if fault=='missing-btf' else 'BTF')
                if fault=='real-provider':(modules/'rog5_s12_ufs_vote').mkdir()
                loader=root/'loader';loader.write_text('#!/bin/sh\necho "module-once finit_module errno='+
                    ('22' if fault=='errno' else '19')+' (No such device); no retry"\nexit 1\n');loader.chmod(0o755)
                prefix='set -eu\ninsmod() { :; }\nrmmod() { '+(':' if fault=='cleanup' else
                    'mv '+str(modules/'rog5_a01_s12_shim')+' '+str(modules/'removed'))+'; }\n'
                script=C.activation_refusal_driver().replace('/rog5-native-wifi/module-once',str(loader)).replace(
                    '/run/',str(root/'run')+'/').replace('/sys/module/',str(modules)+'/').replace('/sys/kernel/btf/',str(root/'btf')+'/')
                result=subprocess.run(['sh','-c',prefix+script],capture_output=True,timeout=3)
                self.assertEqual(result.returncode==0,not fault,(fault,result.stderr))
                self.assertEqual(b'COMPOSITION_ACTIVATION_SPLIT_PASS' in result.stdout,not fault)


if __name__=='__main__':unittest.main()
