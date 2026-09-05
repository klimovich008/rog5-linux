#!/usr/bin/env python3
"""Real key encodings/metadata; only uid/gid are mapped to the target root."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]/'initramfs/persistent-ssh-identity'


class KeyFilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = SOURCE.read_text()
        self.function = source[source.index('verify_key_pair() {'):source.index('verify_sshd_listener() {')]

    def key(self, name, comment, kind='ed25519'):
        path = self.root/name
        subprocess.run(['ssh-keygen', '-q', '-t', kind, '-N', '', '-C', comment, '-f', str(path)], check=True)
        path.chmod(0o600); path.with_suffix('.pub').chmod(0o644)
        return path

    def verify(self, private, public=None):
        # Preserve real modes, sizes and link counts. Do not manufacture the
        # old hardcoded 399/92-byte metadata as the historical test did.
        shell = '''bb() {
  if [ "$1" = stat ]; then
    shift
    command stat "$@" | sed 's/^'''+str(os.getuid())+':'+str(os.getgid())+''':/0:0:/'
  else command "$@"; fi
}
'''+self.function+'\nverify_key_pair "$1" "$2"\n'
        return subprocess.run(['sh','-c',shell,'key-fixture',str(private),str(public or private.with_suffix('.pub'))],
                              capture_output=True,text=True,timeout=3).returncode

    def test_valid_ed25519_comments_do_not_change_identity_acceptance(self):
        for index, comment in enumerate(('root@alarm','root@rog5-persistent-root','','host-'+'x'*100)):
            with self.subTest(comment=comment):
                path=self.key('key'+str(index),comment)
                self.assertEqual(self.verify(path),0)

    def test_wrong_pair_and_other_algorithm_are_rejected(self):
        first=self.key('first','root@alarm');other=self.key('other','root@alarm')
        self.assertNotEqual(self.verify(first,other.with_suffix('.pub')),0)
        self.assertNotEqual(self.verify(self.key('ecdsa','root@alarm','ecdsa')),0)

    def test_unsafe_modes_links_and_corrupt_public_are_rejected(self):
        path=self.key('key','root@alarm');public=path.with_suffix('.pub')
        for mode in (0o644,0o660,0o666):
            path.chmod(mode);self.assertNotEqual(self.verify(path),0)
        path.chmod(0o600)
        alias=self.root/'alias';alias.symlink_to(path)
        self.assertNotEqual(self.verify(alias,public),0)
        alias.unlink();os.link(path,alias)
        self.assertNotEqual(self.verify(path),0)
        alias.unlink()
        good=public.read_bytes()
        for content in (good+good,b'not a key\n',b'x'*2048):
            public.write_bytes(content);self.assertNotEqual(self.verify(path),0)


if __name__=='__main__': unittest.main(verbosity=2)
