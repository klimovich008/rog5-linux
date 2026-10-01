#!/usr/bin/env python3
"""Offline tests of rog5-session-carry (apps carried across a Phosh <-> GNOME
desktop-mode switch) and its units, with a fake session (no systemd, D-Bus or
compositor)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TMP = Path(tempfile.mkdtemp(prefix='rog5-session-carry-test.'))
(TMP / 'boot_id').write_text('boot-a\n')
os.environ.update({
    'ROG5_SESSION_CARRY_STATE': str(TMP / 'state.json'),
    'ROG5_SESSION_CARRY_SYS_CONF': str(TMP / 'sys.conf'),
    'ROG5_SESSION_CARRY_USER_CONF': str(TMP / 'user.conf'),
    'ROG5_SESSION_CARRY_BOOT_ID_FILE': str(TMP / 'boot_id'),
    'XDG_CURRENT_DESKTOP': 'GNOME',
})
loader = importlib.machinery.SourceFileLoader('rog5_session_carry', str(HERE / 'rog5-session-carry'))
spec = importlib.util.spec_from_loader('rog5_session_carry', loader)
sc = importlib.util.module_from_spec(spec)
loader.exec_module(sc)

STATE = TMP / 'state.json'


class FakeSystem:
    def __init__(self):
        self.scope_list = []
        self.names = []
        self.windows = {}
        self.apps = {'steam-arm64', 'firefox', 'org.gnome.Console', 'org.gnome.Settings',
                     'org.gnome.clocks', 'rog5-phone-mode', 'mobi.phosh.MobileSettings'}
        self.quit_actions = set()
        self.calls = []
        self.exit_on_signal = True
        self.launch_ok = True
        self.switch = True
        self.locked = ['no']
        self.slow = 0.0

    def switch_pending(self):
        return self.switch

    def session_locked(self):
        return self.locked.pop(0) if len(self.locked) > 1 else self.locked[0]

    def scopes(self):
        return list(self.scope_list)

    def bus_names(self):
        return list(self.names)

    def window_count(self, name):
        if self.slow:
            time.sleep(self.slow)
        self.calls.append(('windows', name))
        return self.windows.get(name, 0)

    def name_pid(self, name):
        return 4242

    def quit_app(self, name):
        if name in self.quit_actions:
            self.calls.append(('quit', name))
            if self.exit_on_signal:
                self.names.remove(name)
            return True
        return False

    def visible_app(self, app_id):
        return app_id in self.apps

    def kill_scope(self, unit):
        self.calls.append(('kill', unit))
        if self.exit_on_signal:
            self.scope_list.remove(unit)

    def kill_pid(self, pid):
        self.calls.append(('kill_pid', pid))
        if self.exit_on_signal:
            self.names = [n for n in self.names if n != 'org.gnome.Settings']

    def launch(self, app_id):
        self.calls.append(('launch', app_id))
        return self.launch_ok

    def sleep(self, s):
        self.calls.append(('sleep', s))


def reset():
    for p in (STATE, TMP / 'sys.conf', TMP / 'user.conf'):
        if p.exists():
            p.unlink()
    (TMP / 'boot_id').write_text('boot-a\n')


class Collect(unittest.TestCase):
    def setUp(self):
        reset()

    def test_scopes_and_windowed_dbus_apps(self):
        f = FakeSystem()
        f.scope_list = ['app-gnome-steam\\x2darm64-1234.scope', 'app-gnome-firefox-99.scope',
                        'app-gnome-rog5\\x2dphone\\x2dmode-5.scope', 'app-gnome-unknown-7.scope',
                        'other.scope']
        f.names = ['org.gnome.Console', 'org.gnome.clocks', 'org.gnome.Settings',
                   'mobi.phosh.MobileSettings', 'org.freedesktop.Notifications']
        f.windows = {'org.gnome.Console': 1, 'org.gnome.clocks': 0, 'org.gnome.Settings': 2,
                     'mobi.phosh.MobileSettings': 1}
        _, globs = sc.read_config()
        apps = sc.collect(f, globs)
        self.assertEqual(sorted(apps), ['firefox', 'org.gnome.Console', 'org.gnome.Settings', 'steam-arm64'])
        # excluded or invisible names are never queried
        self.assertNotIn(('windows', 'mobi.phosh.MobileSettings'), f.calls)
        self.assertNotIn(('windows', 'org.freedesktop.Notifications'), f.calls)

    def test_config_exclude_and_off(self):
        (TMP / 'user.conf').write_text('exclude steam-*  # not on the phone\n')
        f = FakeSystem()
        f.scope_list = ['app-gnome-steam\\x2darm64-1.scope', 'app-gnome-firefox-2.scope']
        enabled, globs = sc.read_config()
        self.assertTrue(enabled)
        self.assertEqual(sorted(sc.collect(f, globs)), ['firefox'])
        (TMP / 'sys.conf').write_text('off\n')
        self.assertEqual(sc.main(['save', '--close'], f), 0)
        self.assertFalse(STATE.exists())
        self.assertEqual(f.calls, [])


class SaveRestore(unittest.TestCase):
    def setUp(self):
        reset()

    def saved(self):
        f = FakeSystem()
        f.scope_list = ['app-gnome-firefox-2.scope', 'app-gnome-steam\\x2darm64-3.scope']
        f.names = ['org.gnome.Console', 'org.gnome.Settings']
        f.windows = {'org.gnome.Console': 1, 'org.gnome.Settings': 1}
        f.quit_actions = {'org.gnome.Console'}
        self.assertEqual(sc.main(['save', '--close', '--timeout', '2'], f), 0)
        return f

    def test_save_closes_cleanly_and_records(self):
        f = self.saved()
        rec = json.loads(STATE.read_text())
        self.assertEqual(rec['apps'], ['firefox', 'org.gnome.Console', 'org.gnome.Settings', 'steam-arm64'])
        self.assertEqual(rec['boot_id'], 'boot-a')
        self.assertEqual(rec['from'], 'GNOME')
        self.assertIn(('quit', 'org.gnome.Console'), f.calls)          # app.quit first
        self.assertIn(('kill', 'app-gnome-firefox-2.scope'), f.calls)    # SIGTERM to scopes
        self.assertIn(('kill_pid', 4242), f.calls)                       # no quit action: its PID
        self.assertEqual(f.scope_list, [])

    def test_close_gives_up_after_the_timeout(self):
        f = FakeSystem()
        f.exit_on_signal = False
        f.scope_list = ['app-gnome-firefox-2.scope']
        t = time.monotonic()
        self.assertEqual(sc.main(['save', '--close', '--timeout', '0.3'], f), 0)
        self.assertLess(time.monotonic() - t, 3)
        self.assertTrue(STATE.exists())

    def test_timeout_covers_collection_too(self):
        f = FakeSystem()
        f.slow = 0.2
        f.exit_on_signal = False
        f.names = ['org.gnome.Console', 'org.gnome.Settings', 'org.gnome.clocks'] * 5
        f.windows = {'org.gnome.Console': 1}
        t = time.monotonic()
        self.assertEqual(sc.main(['save', '--close', '--timeout', '0.5'], f), 0)
        self.assertLess(time.monotonic() - t, 1.2)

    def test_not_a_switch_records_nothing(self):
        STATE.write_text('{"old": 1}')
        f = FakeSystem()
        f.switch = False
        f.scope_list = ['app-gnome-firefox-2.scope']
        self.assertEqual(sc.main(['save', '--close'], f), 0)
        self.assertFalse(STATE.exists())
        self.assertEqual([c for c in f.calls if c[0] == 'kill'], [])

    def test_restore_once_in_the_same_boot(self):
        self.saved()
        g = FakeSystem()
        self.assertEqual(sc.main(['restore', '--delay', '0'], g), 0)
        self.assertEqual([c[1] for c in g.calls if c[0] == 'launch'],
                         ['firefox', 'org.gnome.Console', 'org.gnome.Settings', 'steam-arm64'])
        self.assertFalse(STATE.exists())
        h = FakeSystem()
        self.assertEqual(sc.main(['restore', '--delay', '0'], h), 0)   # record used up
        self.assertEqual(h.calls, [])

    def test_no_restore_after_reboot_or_when_old(self):
        self.saved()
        (TMP / 'boot_id').write_text('boot-b\n')
        g = FakeSystem()
        sc.main(['restore', '--delay', '0'], g)
        self.assertEqual(g.calls, [])
        self.assertFalse(STATE.exists())
        (TMP / 'boot_id').write_text('boot-a\n')
        self.saved()
        rec = json.loads(STATE.read_text())
        rec['saved'] -= 1000
        STATE.write_text(json.dumps(rec))
        g = FakeSystem()
        sc.main(['restore', '--delay', '0', '--max-age', '300'], g)
        self.assertEqual(g.calls, [])

    def test_restore_skips_apps_no_longer_installed_or_excluded(self):
        self.saved()
        (TMP / 'user.conf').write_text('exclude org.gnome.Settings\n')
        g = FakeSystem()
        g.apps.discard('firefox')
        sc.main(['restore', '--delay', '0'], g)
        self.assertEqual([c[1] for c in g.calls if c[0] == 'launch'], ['org.gnome.Console', 'steam-arm64'])

    def test_restore_waits_for_unlock(self):
        self.saved()
        g = FakeSystem()
        g.locked = ['yes', 'yes', 'no']
        sc.main(['restore', '--delay', '0'], g)
        sleeps = [c for c in g.calls if c[0] == 'sleep']
        launches = [c for c in g.calls if c[0] == 'launch']
        self.assertEqual(len(launches), 4)
        self.assertLess(g.calls.index(sleeps[1]), g.calls.index(launches[0]))

    def test_restore_gives_up_while_locked(self):
        self.saved()
        g = FakeSystem()
        g.locked = ['yes']
        sc.main(['restore', '--delay', '0', '--unlock-wait', '0.01'], g)
        self.assertEqual([c for c in g.calls if c[0] == 'launch'], [])
        self.assertFalse(STATE.exists())

    def test_malformed_shapes_are_ignored(self):
        bad = ['[]', '{"format": "rog5-session-carry-v1"}',
               '{"format": "rog5-session-carry-v1", "boot_id": "boot-a", "saved": "x", "apps": []}',
               '{"format": "rog5-session-carry-v1", "boot_id": "boot-a", "saved": NaN, "apps": []}',
               '{"format": "rog5-session-carry-v1", "boot_id": "boot-a", "saved": %f, "apps": [1]}' % time.time(),
               '{"format": "rog5-session-carry-v1", "boot_id": "boot-a", "saved": %f, "apps": ["../x y"]}' % time.time()]
        for text in bad:
            STATE.write_text(text)
            g = FakeSystem()
            self.assertEqual(sc.main(['restore', '--delay', '0'], g), 0, text)
            self.assertEqual(g.calls, [], text)
            self.assertFalse(STATE.exists())

    def test_symlinked_record_is_refused(self):
        self.saved()
        real = TMP / 'elsewhere.json'
        STATE.rename(real)
        STATE.symlink_to(real)
        g = FakeSystem()
        sc.main(['restore', '--delay', '0'], g)
        self.assertEqual(g.calls, [])
        real.unlink()

    def test_corrupt_record_is_ignored(self):
        STATE.write_text('{not json')
        g = FakeSystem()
        self.assertEqual(sc.main(['restore'], g), 0)
        self.assertEqual(g.calls, [])


class Units(unittest.TestCase):
    def test_dropins_and_user_unit(self):
        for u in ('phosh', 'gnome'):
            text = (REPO / f'configs/systemd/rog5-{u}.service.d/60-rog5-session-carry.conf').read_text()
            self.assertIn('ExecStop=-/usr/local/bin/rog5-session-carry save --close', text)
        unit = (REPO / 'configs/systemd-user/rog5-session-restore.service').read_text()
        self.assertIn('WantedBy=graphical-session.target', unit)
        self.assertIn('ExecStart=/usr/local/bin/rog5-session-carry restore', unit)
        manifest = (REPO / 'configs/rootfs/userspace.tsv').read_text()
        for needle in ('60-rog5-session-carry.conf\t/etc/systemd/system/rog5-phosh.service.d/',
                       '60-rog5-session-carry.conf\t/etc/systemd/system/rog5-gnome.service.d/',
                       'scripts/device/rog5-session-carry\t/usr/local/bin/rog5-session-carry\t0755',
                       'rog5-session-restore.service\t/etc/systemd/user/',
                       'enable\tuser\trog5-session-restore.service'):
            self.assertIn(needle, manifest)

    def test_scope_names(self):
        m = sc.SCOPE_RE.match('app-gnome-org.gnome.Console-123.scope')
        self.assertEqual(m.group('id'), 'org.gnome.Console')
        self.assertEqual(sc.unescape_unit('steam\\x2darm64'), 'steam-arm64')
        self.assertIsNone(sc.SCOPE_RE.match('app-gnome-firefox.scope'))

    def test_background_services_are_excluded(self):
        # GNOME Software runs as a service with a hidden window
        _, globs = sc.read_config()
        self.assertTrue(sc.excluded('org.gnome.Software', globs))


if __name__ == '__main__':
    result = unittest.main(exit=False, verbosity=1).result
    ok = result.wasSuccessful()
    print('PASS rog5-session-carry' if ok else 'FAIL rog5-session-carry')
    raise SystemExit(0 if ok else 1)
