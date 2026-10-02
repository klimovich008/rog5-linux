#!/usr/bin/env python3
"""Exercise the real privileged Phosh lock probe with fake processes/bus.
No phone, real bus, or real /proc files are accessed by the probe.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SWITCHER = REPO / 'scripts/device/rog5-desktop-mode'
PATCH = REPO / 'packages/phosh/0003-export-real-lock-state.patch'

STUB = '''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
s = json.loads(Path(os.environ['PROBE_STATE']).read_text())
a = sys.argv[1:]
n = Path(sys.argv[0]).name
with open(os.environ['PROBE_CALLS'], 'a') as f:
    f.write(json.dumps([n, *a]) + '\\n')
if n == 'id': print('1000')
elif n == 'systemctl': print(s['unit'])
elif n == 'readlink': print(s['exe'])
elif n == 'cat': print(s['cgroup'])
elif n == 'busctl':
    if 'GetNameOwner' in a: print(s['owner'])
    elif 'GetConnectionUnixProcessID' in a: print(s['pid'])
    elif 'get-property' in a:
        if s.get('property_error'): sys.exit(1)
        print(s['locked'])
    else: sys.exit(2)
if s.get('fail') == n: sys.exit(1)
'''


class Probe(unittest.TestCase):
    def run_probe(self, **values):
        with tempfile.TemporaryDirectory(prefix='rog5-phosh-probe.') as d:
            root = Path(d)
            b = root / 'bin'
            b.mkdir()
            state = dict(unit='/system.slice/rog5-phosh.service', exe='/usr/bin/phosh',
                         cgroup='0::/system.slice/rog5-phosh.service', owner='s ":1.8"',
                         pid='u 1234', locked='b false')
            state.update(values)
            (root / 'state').write_text(json.dumps(state))
            for name in ('id', 'systemctl', 'busctl', 'readlink', 'cat'):
                p = b / name
                p.write_text(STUB)
                p.chmod(0o755)
            env = dict(os.environ, ROG5_DM_LIB='1', PROBE_STATE=str(root / 'state'),
                       PROBE_CALLS=str(root / 'calls'), PATH=str(b) + ':' + os.environ['PATH'])
            r = subprocess.run(['bash', '-c', '. "$1"; phosh_locked', 'test', str(SWITCHER)],
                               env=env, capture_output=True, text=True, timeout=10)
            calls = [json.loads(l) for l in (root / 'calls').read_text().splitlines()]
            return r, calls

    def test_actual_lock_state_and_unique_destination(self):
        for value, answer in [('b false', 'no'), ('b true', 'yes')]:
            r, calls = self.run_probe(locked=value)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, answer), r.stderr)
            get = [c for c in calls if 'get-property' in c]
            self.assertEqual(get[0][-4:], [':1.8', '/org/gnome/Shell', 'org.gnome.Shell', 'Locked'])
            self.assertIn('--address=unix:path=/run/user/1000/bus', get[0])
        # Children in the unit cgroup are allowed (Phosh is not the PAM leader).
        r, _ = self.run_probe(cgroup='0::/system.slice/rog5-phosh.service/child')
        self.assertEqual(r.returncode, 0)

    def test_packaged_user_service_layout(self):
        r, _ = self.run_probe(exe='/usr/lib/phosh/phosh',
                             cgroup='0::/user.slice/user-1000.slice/user@1000.service/session.slice/mobi.phosh.Shell.service')
        self.assertEqual((r.returncode, r.stdout.strip()), (0, 'no'), r.stderr)
        r, _ = self.run_probe(exe='/usr/lib/phosh/phosh',
                             cgroup='0::/user.slice/user-1001.slice/user@1001.service/session.slice/mobi.phosh.Shell.service')
        self.assertNotEqual(r.returncode, 0)

    def test_replacement_owner_and_unknown_state_fail_closed(self):
        for values in [dict(exe='/usr/bin/python3'), dict(exe='/usr/bin/phosh (deleted)'),
                       dict(cgroup='0::/user.slice/phone-app.scope'),
                       dict(cgroup='0::/system.slice/rog5-phosh.service-spoof'),
                       dict(unit=''), dict(unit='/'), dict(owner='s "org.gnome.Shell"'),
                       dict(pid='u 0'), dict(pid='u broken'), dict(locked=''),
                       dict(locked='b false junk'), dict(property_error=True)]:
            with self.subTest(values=values):
                r, _ = self.run_probe(**values)
                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(r.stdout, '')
        for cmd in ('id', 'systemctl', 'busctl', 'readlink', 'cat'):
            with self.subTest(cmd=cmd):
                self.assertNotEqual(self.run_probe(fail=cmd)[0].returncode, 0)

    def test_phosh_package_pins_and_applies_property_patch(self):
        text = (REPO / 'packages/phosh/PKGBUILD').read_text()
        self.assertIn('pkgrel=1.4', text)
        self.assertIn('patch -d $pkgname -p1 < ' + PATCH.name, text)
        self.assertIn(hashlib.blake2b(PATCH.read_bytes()).hexdigest(), text)
        patch = PATCH.read_text()
        self.assertIn('+    <property name="Locked" type="b" access="read"/>', patch)
        self.assertIn('+  g_object_bind_property (shell, "locked", object, "locked", G_BINDING_SYNC_CREATE);', patch)
    def test_switcher_watchdog_binds_gnome_lifetime(self):
        unit = (REPO / 'configs/systemd/rog5-desktop-mode.service').read_text()
        for setting in ('Type=notify', 'NotifyAccess=all', 'WatchdogSec=30', 'TimeoutStopSec=5'):
            self.assertIn(setting, unit)
        gnome = (REPO / 'configs/systemd/rog5-gnome.service').read_text()
        self.assertIn('BindsTo=rog5-desktop-mode.service', gnome)
        self.assertRegex(gnome, r'(?m)^After=.*rog5-desktop-mode.service')

    @unittest.skipUnless(shutil.which('gdbus-codegen') and subprocess.run(
        ['pkg-config', '--exists', 'gio-2.0'], capture_output=True).returncode == 0,
        'needs gdbus-codegen and gio-2.0 development files')
    def test_property_skeleton(self):
        patch = PATCH.read_text()
        # Generate/compile the actual property skeleton from the patched XML
        # excerpt. This catches unsupported gdbus property definitions.
        added = re.search(r'^\+    <property.*Locked.*$', patch, re.M).group()[1:]
        with tempfile.TemporaryDirectory(prefix='rog5-lock-property.') as d:
            root = Path(d)
            (root / 'lock.xml').write_text('<node><interface name="org.gnome.Shell">' + added + '</interface></node>')
            subprocess.run(['gdbus-codegen', '--generate-c-code', str(root / 'lock'), str(root / 'lock.xml')], check=True)
            (root / 'test.c').write_text('''#include "lock.h"
int main(void) {
  OrgGnomeShell *s = org_gnome_shell_skeleton_new();
  GObject *real = g_object_new(G_TYPE_SIMPLE_ACTION, "name", "locked", "enabled", TRUE, NULL);
  g_object_bind_property(real, "enabled", s, "locked", G_BINDING_SYNC_CREATE);
  if (!org_gnome_shell_get_locked(s)) return 1;
  g_object_set(real, "enabled", FALSE, NULL);
  if (org_gnome_shell_get_locked(s)) return 2;
  g_object_unref(real); g_object_unref(s); return 0;
}
''')
            flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'gio-2.0'], text=True).split()
            subprocess.run(['cc', '-o', str(root / 'test'), str(root / 'test.c'), str(root / 'lock.c'), *flags], check=True)
            subprocess.run([str(root / 'test')], check=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
