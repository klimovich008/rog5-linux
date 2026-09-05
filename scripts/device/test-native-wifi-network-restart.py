#!/usr/bin/env python3
"""Real file-state restart regression; hardware/mount/service endpoints are fixtures.

This does not replace the actual systemd/network transaction required by F02.
"""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
import gzip
import importlib.util
import sys

REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'initramfs/native-wifi/runtime'
SEALED_ARCHIVE=None


class NetworkRestart(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rog5-network-restart-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.secret=self.root/'persist/secrets/wifi/network.conf'
        self.secret.parent.mkdir(parents=True)
        for path in (self.secret.parent.parent,self.secret.parent): path.chmod(0o700)
        self.secret.write_text('network={\n ssid="disposable-fixture"\n}\n')
        self.secret.chmod(0o600)
        self.state=self.root/'association'

    def prepare(self, count=1, *, owner='0:0'):
        source=SOURCE.read_text()
        start='verify_prepared_network() {' if 'verify_prepared_network() {' in source else 'prepare_network() {'
        functions=source[source.index(start):source.index('run_wpa() {')]
        functions=functions.replace('/persist/secrets',str(self.root/'persist/secrets'))
        script='''set -eu
umask 077
fail() { printf '%s\\n' "$*" >&2; exit 1; }
interface_identity() { interface=wlp1s0; }
systemctl() { test "$*" = 'is-active --quiet rog5-persistent-state.service'; }
findmnt() { case "$3" in TARGET) echo /persist ;; FSTYPE) echo ext4 ;; *) exit 9 ;; esac; }
stat() { command stat "$@" | sed '''+shlex.quote('s/^'+str(os.getuid())+':'+str(os.getgid())+':/'+owner+':/')+'''; }
ip() { test "$*" = 'link set dev wlp1s0 up'; printf '%s\\n' "$*" >>'''+shlex.quote(str(self.root/'ip.log'))+'''; }
'''+f'state={shlex.quote(str(self.state))}\nsecret={shlex.quote(str(self.secret))}\n'+functions+'\n'+('prepare_network\n'*count)
        if SEALED_ARCHIVE:
            spec=importlib.util.spec_from_file_location('sealed',REPO/'scripts/host/run-sealed-busybox.py')
            sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
            with tempfile.TemporaryDirectory(prefix='rog5-network-sealed-') as temp:
                archive_root=Path(temp)
                sealed.extract(sealed.ARCHIVE.entries(gzip.decompress(SEALED_ARCHIVE.read_bytes())),archive_root)
                (archive_root/'rog5-qemu').touch()
                return subprocess.run(['bwrap','--unshare-all','--die-with-parent','--new-session',
                    '--uid','0','--gid','0','--ro-bind',str(archive_root),'/', '--dev','/dev',
                    '--tmpfs','/tmp','--bind',str(self.root),str(self.root),
                    '--ro-bind','/usr/bin/qemu-aarch64-static','/rog5-qemu','--clearenv',
                    '--setenv','PATH','/bin:/sbin:/usr/bin:/usr/sbin', '--setenv','LC_ALL','C',
                    '/rog5-qemu','/bin/busybox','sh','-c',script],capture_output=True,text=True,timeout=10)
        return subprocess.run(['sh','-c',script],capture_output=True,text=True,timeout=3)

    def test_repeated_prepare_keeps_exact_files_and_only_reasserts_same_link(self):
        first=self.prepare()
        self.assertEqual(first.returncode,0,first.stderr)
        config=self.state/'private-network.conf'
        before=(config.stat().st_ino,config.read_bytes(),config.stat().st_mtime_ns)
        again=self.prepare(count=2)
        self.assertEqual(again.returncode,0,again.stderr)
        self.assertEqual(before,(config.stat().st_ino,config.read_bytes(),config.stat().st_mtime_ns))
        self.assertEqual((self.root/'ip.log').read_text(),'link set dev wlp1s0 up\n'*3)

    def test_changed_secret_is_not_silently_copied_over_live_state(self):
        self.assertEqual(self.prepare().returncode,0)
        original=(self.state/'private-network.conf').read_bytes()
        self.secret.write_text('changed fixture\n')
        self.assertNotEqual(self.prepare().returncode,0)
        self.assertEqual((self.state/'private-network.conf').read_bytes(),original)

    def test_partial_unsafe_or_aliased_existing_state_is_refused(self):
        for mutation in ('missing-config','directory-mode','config-mode','dhcp-mode','dhcp-content','extra-file','symlink','hardlink'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.assertEqual(self.prepare().returncode,0)
                config=self.state/'private-network.conf'; dhcp=self.state/'dhcpcd.conf'
                if mutation=='missing-config': config.unlink()
                elif mutation=='directory-mode': self.state.chmod(0o755)
                elif mutation=='config-mode': config.chmod(0o644)
                elif mutation=='dhcp-mode': dhcp.chmod(0o644)
                elif mutation=='dhcp-content': dhcp.write_text('unexpected hook\n')
                elif mutation=='extra-file': (self.state/'unexpected').touch()
                elif mutation=='symlink': config.unlink();config.symlink_to(self.secret)
                elif mutation=='hardlink': os.link(config,self.root/'alias')
                self.assertNotEqual(self.prepare().returncode,0)


if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--sealed-archive':
        SEALED_ARCHIVE=Path(sys.argv[2]).resolve(strict=True)
        del sys.argv[1:3]
    unittest.main(verbosity=2)
