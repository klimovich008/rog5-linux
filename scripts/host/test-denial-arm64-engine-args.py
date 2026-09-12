#!/usr/bin/env python3
"""Exercise the argument producer and reject wrong-architecture configurations."""
import argparse
import copy
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

SCRIPT=Path(__file__).with_name('generate-denial-arm64-engine-args.py')
M=runpy.run_path(str(SCRIPT))

class Arguments(unittest.TestCase):
    def test_required_target_host_and_limits(self):
        values=copy.deepcopy(M['REQUIRED']); values['concurrent_toolchain_jobs']=32
        parser=Mock(return_value=object()); generator=Mock(return_value=values)
        renderer=Mock(return_value=['target_cpu="arm64"'])
        result,text=M['generate']({'parse_args':parser,'to_gn_args':generator,'to_command_line':renderer})
        parser.assert_called_once_with(['gn', *M['FLAGS']])
        generator.assert_called_once_with(parser.return_value)
        self.assertEqual(result['concurrent_toolchain_jobs'],1)
        renderer.assert_called_once_with(result)
        self.assertEqual(text,'target_cpu="arm64"\n')
        for option in ('--target-os=linux','--linux-cpu=arm64','--embedder-for-target','--no-prebuilt-dart-sdk'):
            self.assertIn(option,parser.call_args.args[0])

    def test_upstream_parser_receives_program_name(self):
        parser=argparse.ArgumentParser()
        parser.add_argument('--runtime-mode',default='debug')
        def parse(argv):
            return parser.parse_known_args(argv[1:])[0]
        def convert(args):
            values=copy.deepcopy(M['REQUIRED'])
            values['flutter_runtime_mode']=args.runtime_mode
            return values
        values,_=M['generate']({'parse_args':parse,'to_gn_args':convert,'to_command_line':lambda values:[]})
        self.assertEqual(values['flutter_runtime_mode'],'release')

    def test_wrong_profile_fields_refused(self):
        for key in M['REQUIRED']:
            with self.subTest(key=key):
                values=copy.deepcopy(M['REQUIRED']);values[key]=None
                with self.assertRaises(ValueError):M['require_profile'](values)

    def test_host_defaults_do_not_qualify_as_arm64(self):
        values=copy.deepcopy(M['REQUIRED']);values.update(target_cpu='x64',dart_target_arch='x64',embedder_for_target=False)
        with self.assertRaises(ValueError):M['require_profile'](values)

    def test_implicit_prebuilt_sdk_refused(self):
        values=copy.deepcopy(M['REQUIRED']);values['flutter_prebuilt_dart_sdk']=True
        with self.assertRaises(ValueError):M['require_profile'](values)

    def test_missing_source_records_no_argument_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'out'
            r=subprocess.run([sys.executable,'-O',str(SCRIPT),'--source',str(root/'missing'),'--output',str(out)],capture_output=True,timeout=10)
            self.assertNotEqual(r.returncode,0)
            d=json.loads((out/'result.json').read_text())
            self.assertEqual(d['argument_status'],'NOT RUN')
            self.assertFalse((out/'args.gn').exists())

    def test_existing_output_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'out';out.mkdir();receipt=out/'result.json';receipt.write_text('preserved')
            r=subprocess.run([sys.executable,'-O',str(SCRIPT),'--source',str(root/'missing'),'--output',str(out)],capture_output=True,timeout=10)
            self.assertNotEqual(r.returncode,0);self.assertEqual(receipt.read_text(),'preserved')

    def test_output_alias_into_source_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();alias=root/'alias';alias.symlink_to(source,target_is_directory=True)
            r=subprocess.run([sys.executable,'-O',str(SCRIPT),'--source',str(source),'--output',str(alias/'out')],capture_output=True,timeout=10)
            self.assertNotEqual(r.returncode,0);self.assertFalse((source/'out').exists())

    def test_output_within_source_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            r=subprocess.run([sys.executable,'-O',str(SCRIPT),'--source',str(root),'--output',str(root/'out')],capture_output=True,timeout=10)
            self.assertNotEqual(r.returncode,0);self.assertFalse((root/'out').exists())

if __name__=='__main__':unittest.main(verbosity=2)
