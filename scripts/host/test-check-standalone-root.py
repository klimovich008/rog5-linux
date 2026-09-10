#!/usr/bin/env python3
"""Local-root observations: fail closed without confusing a component with S01."""
import copy
import contextlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('root_check',Path(__file__).with_name('check-standalone-root.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

# Sanitized exact mount records from the retained V4 server snapshot.
MOUNTS='''32 37 259:8 / /.rog5/root-ro ro,nosuid,nodev,noatime shared:3 - ext4 /dev/sda24 ro,norecovery
33 37 259:7 / /.rog5/userdata-rw rw,nosuid,nodev,noexec,noatime shared:2 - ext4 /dev/sda23 rw,stripe=128
34 37 7:0 / /.rog5/state rw,nosuid,nodev,noatime shared:4 - ext4 /dev/loop0 rw
37 2 0:28 / / rw,relatime shared:1 - overlay overlay rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/state/work
59 37 7:1 / /persist rw,nosuid,nodev,noexec,noatime shared:168 - ext4 /dev/loop1 rw
'''

class Tests(unittest.TestCase):
    def setUp(self):
        self.identity=dict(serial='fixture',boot_id='11111111-1111-4111-8111-111111111111',bundle='fixture',release='fixture')
        self.value=dict(identity=self.identity.copy(),mountinfo=MOUNTS,
            root_device='/dev/sda24',geometry=dict(partition='24',start='427819008',size='67108824',ro='1',uevent='PARTNAME=arch_root_a\n'),
            loops={'loop0':'/.rog5/userdata-rw/rog5/root/root-overlay-v1.ext4'},
            blocks={'sda':'0','sda23':'0',**{f'readonly{x}':'1' for x in range(115)}},
            units={x:'active' for x in ('rog5-persistent-state.service','rog5-persistent-ssh-identity.service','rog5-early-sshd.service','rog5-healthd.service')},
            power=dict(health='Good',temp='299',voltage_now='8500000'),usb_online='1')

    def test_exact_local_root(self):M.validate(self.value,self.identity)

    def test_missing_and_duplicate_mounts(self):
        for raw in ('',MOUNTS+MOUNTS.splitlines()[0]+'\n','bad record'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):M.mounts(raw)
        self.value['mountinfo']='\n'.join(MOUNTS.splitlines()[1:])
        with self.assertRaisesRegex(ValueError,'missing mount'):M.validate(self.value,self.identity)

    def test_network_mount_anywhere(self):
        for fs in ('nfs','nfs4','cifs','smb3','9p'):
            self.value['mountinfo']=MOUNTS+f'90 37 0:90 / /hidden rw - {fs} host:/root rw\n'
            with self.subTest(fs=fs),self.assertRaisesRegex(ValueError,'network filesystem'):M.validate(self.value,self.identity)

    def test_wrong_geometry_source_or_write_scope(self):
        for field,value in [('root_device','/dev/sda23'),('geometry',{**self.value['geometry'],'size':'1'}),
            ('blocks',{**self.value['blocks'],'sda24':'0'}),('loops',{'loop0':'/tmp/root.ext4'})]:
            changed=copy.deepcopy(self.value);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):M.validate(changed,self.identity)

    def test_overlay_and_lower_options(self):
        for old,new in [('ro,norecovery','ro'),('lowerdir=/mnt/root-ro','lowerdir=/tmp/root'),
            ('upperdir=/mnt/state/upper','upperdir=/tmp/upper'),('ext4 /dev/sda24','ext4 /dev/loop9'),
            ('/.rog5/state rw','/.rog5/state ro')]:
            changed=copy.deepcopy(self.value);changed['mountinfo']=MOUNTS.replace(old,new)
            with self.subTest(old=old),self.assertRaises(ValueError):M.validate(changed,self.identity)

    def test_identity_power_and_services(self):
        for field,value in [('identity',{}),('usb_online','0'),('units',{}),
            ('power',dict(health='Good',temp='400',voltage_now='8500000'))]:
            changed=copy.deepcopy(self.value);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):M.validate(changed,self.identity)

    def test_probe_is_compilable_and_is_not_a_boot_or_write_command(self):
        compile('request={}\n'+M.PROBE,'sealed-observer','exec')
        for token in ('reboot','fastboot','systemctl restart','modprobe','write_text','write_bytes'):
            self.assertNotIn(token,M.PROBE)

    def test_entry_point_has_no_boot_action(self):
        p=subprocess.run([str(M.D.REPO/'scripts/host/rog5-dev'),'check-standalone-root','--help'],capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('--boot-id',p.stdout)
        self.assertNotIn('--reboot',p.stdout)

    def collect_fixture(self,missing,error):
        class FixturePath(PurePosixPath):
            def glob(self,pattern):return []
            def resolve(self,strict=False):return PurePosixPath('/dev/sda24')
        def opened(path,*args,**kwargs):
            path=str(path)
            if path.endswith('/'+missing):raise error('fixture unsupported field')
            value={'/proc/sys/kernel/random/boot_id':self.identity['boot_id'],
                '/proc/cmdline':'rog5.bundle=fixture'}.get(path,'fixture')
            return io.StringIO(value)
        output=io.StringIO()
        with mock.patch('pathlib.Path',FixturePath),mock.patch('builtins.open',opened), \
             mock.patch('os.uname',return_value=SimpleNamespace(release='fixture')), \
             mock.patch('subprocess.check_output',return_value='active\n'),contextlib.redirect_stdout(output):
            exec('request='+repr(self.identity)+'\n'+M.PROBE,{})
        return json.loads(output.getvalue())

    def test_optional_field_absence_and_error_are_observations(self):
        for field in ('capacity','status','current_now'):
            for error,status in ((FileNotFoundError,'absent'),(PermissionError,'error')):
                with self.subTest(field=field,error=error):
                    value=self.collect_fixture(field,error)
                    self.assertEqual(value['power_optional'][field],{'status':status})

    def test_missing_required_power_is_not_swallowed(self):
        for field in ('health','temp','voltage_now','online'):
            with self.subTest(field=field),self.assertRaises(FileNotFoundError):
                self.collect_fixture(field,FileNotFoundError)

if __name__=='__main__':unittest.main()
