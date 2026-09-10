#!/usr/bin/env python3
"""E01: shipped radio/runtime with fake hardware; no physical activation."""
import gzip
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

R = Path(__file__).resolve().parents[2]
BOOT = '11111111-2222-3333-4444-555555555555'
BUNDLE = 'fixture-radio'
SEALED_ARCHIVE = None

class RadioRefusal(unittest.TestCase):
    archive_root = None

    @classmethod
    def setUpClass(cls):
        if SEALED_ARCHIVE:
            spec=importlib.util.spec_from_file_location('sealed',R/'scripts/host/run-sealed-busybox.py')
            sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
            extraction=tempfile.TemporaryDirectory(prefix='rog5-e01-sealed-')
            cls.addClassCleanup(extraction.cleanup)
            cls.archive_root=Path(extraction.name)
            data=SEALED_ARCHIVE.read_bytes()
            sealed.extract(sealed.ARCHIVE.entries(gzip.decompress(data)),cls.archive_root)
            (cls.archive_root/'rog5-qemu').touch()
            print('sealed_archive_sha256='+hashlib.sha256(data).hexdigest(),flush=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-radio-refusal-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root/'run/rog5-native-wifi'
        self.payload.mkdir(parents=True)
        for name, data in {
            'proc/sys/kernel/random/boot_id': BOOT,
            'proc/cmdline': 'rog5.bundle='+BUNDLE,
            'sys/firmware/devicetree/base/model': 'ASUS ROG Phone 5',
            'sys/class/power_supply/qcom-battmgr-bat/health': 'Good',
            'sys/class/power_supply/qcom-battmgr-bat/temp': '300',
            'sys/class/power_supply/qcom-battmgr-bat/voltage_now': '8000000',
            'sys/class/power_supply/qcom-battmgr-usb/online': '1',
            'sys/class/thermal/thermal_zone0/temp': '30000',
        }.items():
            path = self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data)
        for index in range(117):
            path = self.root/f'sys/class/block/sd{index}/ro'
            path.parent.mkdir(parents=True)
            path.write_text('1')
        (self.payload/'kernel-release').write_text('7.1.4-test')
        (self.payload/'timing').write_bytes((R/'initramfs/native-wifi/timing').read_bytes())
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            entry = tarfile.TarInfo('fixture.ko'); entry.size=7
            archive.addfile(entry,io.BytesIO(b'fixture'))
        (self.payload/'module-root-complete.tar.gz').write_bytes(stream.getvalue())
        (self.payload/'module-files.sha256').write_text(
            hashlib.sha256(b'fixture').hexdigest()+'  fixture.ko\n')
        self.seal()
        self.armed = True

    def seal(self):
        (self.payload/'boot-files.sha256').write_text(''.join(
            hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'
            for p in sorted(self.payload.iterdir()) if p.is_file() and p.name!='boot-files.sha256'))

    def mapped(self, source):
        return re.sub(r'(?<![A-Za-z0-9_/])/(sys|proc|run|dev)/',
                      lambda match: str(self.root/match[1])+'/', source)

    def script(self, path, radio=False):
        source = path.read_text()
        if radio:
            # Discriminating boundary: all real preflight code executes, but
            # the physical trace/power/module sequence must never run offline.
            source = source.replace('started=0\n','echo HARDWARE_BOUNDARY; exit 42\nstarted=0\n',1)
        prelude = (
            'id() { echo 0; }; uname() { echo 7.1.4-test; }\n'
            'stat() { command stat "$@" | sed ' + shlex.quote(
                f's/^{os.getuid()}:{os.getgid()}:/0:0:/') + '; }\n'
            'systemctl() { case "$*" in '
            '"--no-block reboot") echo REBOOT ;; '
            '*rog5-wifi-boot-rollback.timer) return '+('0' if self.armed else '1')+' ;; '
            '*) return 0 ;; esac; }\n'
        )
        return prelude+self.mapped(source)

    def run_script(self, path, action=None, radio=False):
        command=['sh']
        if self.archive_root:
            command=['bwrap','--unshare-all','--die-with-parent','--new-session',
                '--uid','0','--gid','0','--ro-bind',str(self.archive_root),'/',
                '--dev','/dev','--tmpfs','/tmp','--bind',str(self.root),str(self.root),
                '--ro-bind','/usr/bin/qemu-aarch64-static','/rog5-qemu',
                '--clearenv','--setenv','PATH','/bin:/sbin:/usr/bin:/usr/sbin',
                '--setenv','LC_ALL','C','/rog5-qemu','/bin/busybox','sh']
        return subprocess.run([*command,'-c',self.script(path,radio),'fixture',*([action] if action else [])],
                              capture_output=True,text=True,timeout=10)

    def radio(self):
        return self.run_script(R/'initramfs/native-wifi/radio',radio=True)

    def runtime(self, action):
        return self.run_script(R/'initramfs/native-wifi/runtime',action)

    def test_safe_low_radio_voltage_refuses_without_hardware_or_retry(self):
        result=self.radio()
        self.assertEqual(result.returncode,77,result.stdout+result.stderr)
        self.assertNotIn('HARDWARE_BOUNDARY',result.stdout)
        self.assertTrue((self.payload/'radio-refused').is_file())
        self.assertFalse((self.payload/'radio-activation-entered').exists())
        self.assertEqual(self.runtime('radio-enabled').returncode,1)
        self.assertNotEqual(self.radio().returncode,77)

    def test_radio_threshold_stays_exact_and_activation_never_becomes_refusal(self):
        (self.root/'sys/class/power_supply/qcom-battmgr-bat/voltage_now').write_text('8400000')
        result=self.radio()
        self.assertEqual(result.returncode,42,result.stdout+result.stderr)
        self.assertIn('HARDWARE_BOUNDARY',result.stdout)
        self.assertFalse((self.payload/'radio-refused').exists())
        self.assertTrue((self.payload/'radio-activation-entered').is_dir())

    def test_unsafe_power_storage_artifact_and_rollback_remain_fatal(self):
        for case in ('low','high','hot','thermal','health','offline','write','hash','rollback'):
            with self.subTest(case=case):
                self.setUp()
                updates = {
                    'low': ('sys/class/power_supply/qcom-battmgr-bat/voltage_now','7499999'),
                    'high': ('sys/class/power_supply/qcom-battmgr-bat/voltage_now','8800001'),
                    'hot': ('sys/class/power_supply/qcom-battmgr-bat/temp','400'),
                    'thermal': ('sys/class/thermal/thermal_zone0/temp','60000'),
                    'health': ('sys/class/power_supply/qcom-battmgr-bat/health','Overheat'),
                    'offline': ('sys/class/power_supply/qcom-battmgr-usb/online','0'),
                    'write': ('sys/class/block/sd0/ro','0'),
                }
                if case in updates:
                    name,value=updates[case]; (self.root/name).write_text(value)
                elif case=='hash': (self.payload/'module-files.sha256').write_text('corrupt')
                else: self.armed=False
                result=self.radio()
                self.assertNotIn(result.returncode,(0,77))
                self.assertFalse((self.payload/'radio-refused').exists())
                self.assertNotIn('HARDWARE_BOUNDARY',result.stdout)

    def accepted_core(self):
        for name,content in {
            'rog5-p2-ready': f'status=PASS\nattested_boot_id={BOOT}\n',
            'rog5-persistent-ssh-identity.record':
                'format=rog5-persistent-ssh-identity-v1\nmode=load\nfingerprint=SHA256:'+
                'A'*43+f'\nidentity_boot_id={BOOT}\n',
        }.items():
            path=self.root/'run'/name
            path.write_text(content);path.chmod(0o444)

    def test_only_current_refusal_and_qualified_core_suppress_rollback(self):
        self.assertEqual(self.radio().returncode,77)
        self.assertIn('REBOOT',self.runtime('rollback').stdout)
        self.accepted_core()
        self.assertNotIn('REBOOT',self.runtime('rollback').stdout)
        for case in ('stale','mode','symlink','extra','partial-activation','missing-core',
                     'stale-core','missing-identity','unsafe-temperature','unsafe-thermal'):
            with self.subTest(case=case):
                self.setUp();self.assertEqual(self.radio().returncode,77)
                self.accepted_core()
                path=self.payload/'radio-refused'
                if case=='stale':
                    path.chmod(0o644);path.write_text(path.read_text().replace(BOOT,'0'*36));path.chmod(0o444)
                elif case=='mode': path.chmod(0o644)
                elif case=='symlink':
                    path.rename(self.payload/'old');path.symlink_to('old')
                elif case=='extra':
                    path.chmod(0o644);path.write_bytes(path.read_bytes()+b'junk');path.chmod(0o444)
                elif case=='partial-activation': (self.payload/'radio-activation-entered').mkdir()
                elif case=='missing-core': (self.root/'run/rog5-p2-ready').unlink()
                elif case=='stale-core':
                    core=self.root/'run/rog5-p2-ready'
                    core.chmod(0o644);core.write_text(core.read_text().replace(BOOT,'0'*36));core.chmod(0o444)
                elif case=='missing-identity': (self.root/'run/rog5-persistent-ssh-identity.record').unlink()
                elif case=='unsafe-temperature': (self.root/'sys/class/power_supply/qcom-battmgr-bat/temp').write_text('400')
                else: (self.root/'sys/class/thermal/thermal_zone0/temp').write_text('60000')
                self.assertIn('REBOOT',self.runtime('rollback').stdout)
                if case not in ('missing-core','stale-core','missing-identity','unsafe-temperature','unsafe-thermal'):
                    self.assertEqual(self.runtime('radio-enabled').returncode,255)

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--sealed-archive':
        for executable in ('bwrap','qemu-aarch64-static'):
            if not shutil.which(executable):
                print('BLOCKED: missing '+executable)
                raise SystemExit(77)
        SEALED_ARCHIVE=Path(sys.argv[2]).resolve(strict=True)
        del sys.argv[1:3]
    unittest.main(verbosity=2)
