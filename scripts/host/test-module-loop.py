#!/usr/bin/env python3
"""Exercise module-loop.py against fake make, modinfo, readelf and SSH.
No phone, USB device, network or kernel tree is touched."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/module-loop.py'
RELEASE = '7.1.4-rog5-production'
BUILD_ID = 'b194e02f908034fe050e105250382c24271fd734'

FAKE_MAKE = r'''#!/bin/sh
for arg; do case "$arg" in M=*) m=${arg#M=} ;; esac; done
printf 'ko\n' > "$m/qcom_battmgr.ko"
'''
FAKE_MODINFO = r'''#!/bin/sh
case "$2" in
	name) echo qcom_battmgr ;;
	vermagic) echo "${FAKE_VERMAGIC:-7.1.4-rog5-production SMP preempt mod_unload aarch64}" ;;
	depends) echo pmic_glink ;;
esac
'''
FAKE_READELF = '#!/bin/sh\necho "    Build ID: b194e02f908034fe050e105250382c24271fd734"\n'


def notes(build_id):
    desc = bytes.fromhex(build_id)
    return struct.pack('<III', 4, len(desc), 3) + b'GNU\0' + desc


def load():
    spec = importlib.util.spec_from_file_location('module_loop', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePhone:
    def __init__(self, build_id=BUILD_ID, log_extra=''):
        self.build_id, self.log_extra, self.calls, self.marker = build_id, log_extra, [], None

    def __call__(self, address, command, timeout, data=None):
        self.calls.append(command)
        out, rc = '', 0
        if command.startswith('uname -r; od'):
            out = RELEASE+'\n'+notes(self.build_id).hex()
        elif command.startswith('mkdir -p'):
            self.marker = command.split("echo '", 1)[1].split("'")[0]
        elif command.startswith('cat > '):
            import hashlib
            out = hashlib.sha256(data).hexdigest()+'  '+command.split()[2]
        elif command.startswith('dmesg'):
            out = '[ 1.0] '+self.marker+'\n[ 1.1] probe\n'+self.log_extra
        elif command == 'uname -r':
            out = RELEASE
        return subprocess.CompletedProcess(command, rc, out.encode(), b'')


class ModuleLoop(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        os.environ['ROG5_MODULE_LOOP_STATE'] = str(self.root/'state')
        self.loop = load()

    def run_main(self, argv, phone=None):
        patches = [mock.patch.object(sys, 'argv', ['module-loop.py']+argv),
                   mock.patch.object(self.loop.TRIAL, 'usb_state', return_value='target')]
        if phone:
            patches.append(mock.patch.object(self.loop.TRIAL, 'ssh', phone))
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            return self.loop.main()

    def fake_build(self):
        build = self.root/'build'
        (build/'modules').mkdir(parents=True)
        ko = build/'modules/qcom_battmgr.ko'
        ko.write_bytes(b'module bytes')
        import hashlib
        (build/'result.json').write_text(json.dumps(dict(release=RELEASE, build_id=BUILD_ID, modules=[dict(
            name='qcom_battmgr', file='modules/qcom_battmgr.ko', sha256=hashlib.sha256(b'module bytes').hexdigest(),
            depends=['pmic_glink'])])))
        return build

    def test_build_id_parser_skips_other_notes(self):
        blob = struct.pack('<III', 6, 4, 1) + b'Linux\0\0\0' + b'abcd' + notes(BUILD_ID)
        self.assertEqual(self.loop.gnu_build_id(blob), BUILD_ID)
        self.assertIsNone(self.loop.gnu_build_id(b''))

    def test_shared_header_edits_are_refused(self):
        tree = self.root/'tree'
        for path in ('drivers/x/a.c', 'drivers/x/a.h', 'drivers/y/b.h', 'include/linux/c.h', 'drivers/y/d.c'):
            (tree/path).parent.mkdir(parents=True, exist_ok=True)
            (tree/path).write_text('0\n')
        git = ['git', '-C', str(tree)]
        subprocess.run(git+['init', '-q'], check=True)
        subprocess.run(git+['add', '-A'], check=True)
        subprocess.run(git+['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base'], check=True)
        for path in ('drivers/x/a.c', 'drivers/x/a.h', 'drivers/y/d.c'):
            (tree/path).write_text('1\n')
        self.assertEqual(self.loop.outside_changes(tree, 'drivers/x'), [])
        (tree/'drivers/y/b.h').write_text('1\n')
        (tree/'include/linux/c.h').write_text('1\n')
        self.assertEqual(sorted(self.loop.outside_changes(tree, 'drivers/x')), ['drivers/y/b.h', 'include/linux/c.h'])

    def test_build_with_fake_toolchain(self):
        bin_dir = self.root/'bin'
        bin_dir.mkdir()
        for name, text in (('make', FAKE_MAKE), ('modinfo', FAKE_MODINFO), ('readelf', FAKE_READELF), ('llvm-readelf', FAKE_READELF)):
            (bin_dir/name).write_text(text)
            (bin_dir/name).chmod(0o755)
        objects = self.root/'objects'
        (objects/'include/config').mkdir(parents=True)
        (objects/'include/config/kernel.release').write_text(RELEASE+'\n')
        (objects/'Module.symvers').write_text('')
        (objects/'vmlinux').write_text('')
        source = self.root/'source'
        (source/'drivers/power/supply').mkdir(parents=True)
        (source/'drivers/power/supply/Makefile').write_text('obj-m += qcom_battmgr.o\n')
        path = str(bin_dir)+os.pathsep+os.environ['PATH']
        with mock.patch.dict(os.environ, PATH=path), mock.patch.object(self.loop.shutil, 'which', side_effect=lambda n: str(bin_dir/n) if (bin_dir/n).exists() else None):
            self.assertEqual(self.run_main(['build', '--objects', str(objects), '--source', str(source),
                                            '--dir', 'drivers/power/supply', '--output', str(self.root/'out')]), 0)
        result = json.loads((self.root/'out/result.json').read_text())
        self.assertEqual((result['release'], result['build_id'], result['modules'][0]['name']), (RELEASE, BUILD_ID, 'qcom_battmgr'))
        with mock.patch.dict(os.environ, PATH=path, FAKE_VERMAGIC='7.2.7 SMP'), \
                mock.patch.object(self.loop.shutil, 'which', side_effect=lambda n: str(bin_dir/n) if (bin_dir/n).exists() else None):
            with self.assertRaisesRegex(ValueError, 'vermagic'):
                self.run_main(['build', '--objects', str(objects), '--source', str(source),
                               '--dir', 'drivers/power/supply', '--output', str(self.root/'out2')])

    def test_deliver_replaces_tests_and_passes(self):
        phone = FakePhone()
        self.assertEqual(self.run_main(['deliver', '--build', str(self.fake_build()), '--test', 'true'], phone), 0)
        names = [c.split()[0] for c in phone.calls]
        self.assertEqual(names[:3], ['uname', 'mkdir', 'cat'])
        self.assertTrue(any(c.startswith('grep -q "^pmic_glink "') for c in phone.calls))
        order = [i for i, c in enumerate(phone.calls) if 'rmmod qcom_battmgr' in c or c.startswith('insmod ')]
        self.assertTrue('rmmod' in phone.calls[order[0]] and phone.calls[order[1]].startswith('insmod'))
        record = json.loads(next((self.root/'build').glob('deliver-*/result.json')).read_text())
        self.assertEqual((record['status'], record['loaded']), ('PASS', ['qcom_battmgr']))

    def test_wrong_vmlinux_is_refused_before_any_write(self):
        phone = FakePhone(build_id='00'*20)
        with self.assertRaisesRegex(ValueError, 'build ID'):
            self.run_main(['deliver', '--build', str(self.fake_build())], phone)
        self.assertEqual(len(phone.calls), 1)

    def test_oops_in_kernel_log_fails(self):
        phone = FakePhone(log_extra='[ 1.2] Unable to handle kernel NULL pointer dereference\n')
        self.assertEqual(self.run_main(['deliver', '--build', str(self.fake_build())], phone), 1)
        record = json.loads(next((self.root/'build').glob('deliver-*/result.json')).read_text())
        self.assertEqual(record['status'], 'FAIL')
        self.assertTrue(record['kernel_problems'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
