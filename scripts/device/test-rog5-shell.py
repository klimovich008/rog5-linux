#!/usr/bin/env python3
"""Offline tests of rog5-shell (shell selector, GNOME Mobile watchdog and
fallback), its unit gates and rog5-gnome-mobile-session, with a fake system
(no systemd, logind, D-Bus or DRM)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TMP = Path(tempfile.mkdtemp(prefix='rog5-shell-test.'))

os.environ.update({
    'ROG5_SHELL_TEST': '1',
    'ROG5_SHELL_MODE_FILE': str(TMP / 'etc/rog5/shell'),
    'ROG5_SHELL_RUN_DIR': str(TMP / 'run/rog5-shell'),
    'ROG5_SHELL_STATE_DIR': str(TMP / 'var/lib/rog5'),
    'ROG5_SHELL_DSI': str(TMP / 'sys/card1-DSI-1'),
    'ROG5_SHELL_SESSION_FILE': str(TMP / 'usr/share/wayland-sessions/gnome-mobile.desktop'),
    'ROG5_SHELL_GDM_CONF': str(TMP / 'etc/gdm/custom.conf'),
    'ROG5_SHELL_GDM_BIN': str(TMP / 'usr/bin/gdm'),
    'ROG5_SHELL_GREETER_MONITORS': str(TMP / 'etc/xdg/monitors.xml'),
    'ROG5_SHELL_KMSG': str(TMP / 'kmsg'),
    'ROG5_SHELL_PHONE_USER': __import__('pwd').getpwuid(os.getuid()).pw_name,
})
loader = importlib.machinery.SourceFileLoader('rog5_shell', str(HERE / 'rog5-shell'))
spec = importlib.util.spec_from_loader('rog5_shell', loader)
rs = importlib.util.module_from_spec(spec)
loader.exec_module(rs)

TOUCH = '/dev/input/event3'
DRM = '/dev/dri/card1'


class FakeSystem:
    """A phone in a scripted state; the clock moves only in sleep()."""

    def __init__(self):
        self.t = 1000.0
        self.calls = []                  # systemctl / loginctl actions, in order
        self.units = {'gdm.service': 'inactive', 'rog5-shell-watchdog.service': 'inactive',
                      'rog5-phosh.service': 'active', 'rog5-desktop-mode.service': 'active',
                      'rog5-gnome.service': 'inactive'}
        self.shells = []                 # [(pid, uid, gid)]
        self.answering = set()           # pids that answer ShellVersion
        self.touch_pids = set()          # pids holding the touchscreen
        self.phosh_procs = []
        self.dsi = {'enabled': 'enabled', 'dpms': 'On'}
        self.drm = []
        self.sess = []
        self.phosh_locks = True          # a started Phosh reports LockedHint=yes
        self.pacman_ok = True
        self.fail_start = set()
        self.kills = []
        self.on_sleep = None
        self.user_runs = []

    # time
    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s
        if self.on_sleep:
            self.on_sleep(self)

    # units
    def unit_state(self, unit):
        return self.units.get(unit, 'inactive')

    def systemctl(self, *args, timeout=90):
        args = [a for a in args if a != '--no-block']
        self.calls.append(('systemctl',) + tuple(args))
        verb, units = args[0], args[1:]
        if verb in ('start', 'restart'):
            for u in units:
                if u in self.fail_start:
                    return False
                self.units[u] = 'active'
                if u == 'rog5-phosh.service':
                    self.sess = [s for s in self.sess if s['Id'] != '9']
                    self.sess.append({'Id': '9', 'Service': 'phosh', 'Class': 'user', 'Desktop': '',
                                      'Leader': '4242', 'Name': 'phone', 'State': 'active',
                                      'LockedHint': 'yes' if self.phosh_locks else 'no'})
                if u == 'gdm.service':
                    pass
        elif verb == 'stop':
            for u in units:
                self.units[u] = 'inactive'
                if u == 'gdm.service':
                    self.shells = []
                    self.drm = [p for p in self.drm if p == 99]   # 99: a stuck holder
        return True

    def run(self, argv, timeout=30, user=None):
        if argv[:2] == ['pacman', '-Q']:
            return (0 if self.pacman_ok else 1), ''
        if argv[:1] == ['systemctl'] and argv[1:3] == ['show', '-p']:
            return 0, '4242\n' if self.units.get('rog5-phosh.service') == 'active' else '0\n'
        if argv[:2] == ['loginctl', 'terminate-session']:
            self.calls.append(('terminate', argv[2]))
            self.sess = [s for s in self.sess if s['Id'] != argv[2]]
            return 0, ''
        if user is not None:
            self.user_runs.append(argv)
            return 0, ''
        return 1, ''

    def processes(self, comm):
        if comm == 'gnome-shell':
            return list(self.shells)
        if comm == 'phosh':
            return list(self.phosh_procs)
        return []

    def proc_env(self, pid, name):
        return f'unix:path=/run/user/{pid}/bus'

    def proc_fds(self, pid):
        return {TOUCH} if int(pid) in self.touch_pids else set()

    def drm_holders(self):
        return list(self.drm)

    def touch_nodes(self):
        return {TOUCH}

    def read(self, path):
        return self.dsi.get(Path(path).name, '')

    def sessions(self):
        return [dict(s) for s in self.sess]

    def kill(self, pid, sig):
        self.kills.append((pid, sig))
        if sig == 9 and pid in self.drm:
            self.drm.remove(pid)


def fake_answers(sysm, pid, uid, gid):
    return pid in sysm.answering


rs.shell_answers = fake_answers


def reset_files(persistent=None, effective=None):
    for p in (rs.MODE_FILE, rs.RUN_DIR / 'effective', rs.STATE_DIR / 'shell-fallback'):
        if p.exists():
            p.unlink()
    if persistent is not None:
        rs.write_atomic(rs.MODE_FILE, persistent + '\n')
    if effective is not None:
        rs.write_atomic(rs.RUN_DIR / 'effective', effective + '\n')


def install_mobile_prereqs():
    for p in (rs.GDM_BIN, rs.SESSION_FILE):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('x\n')
    rs.GDM_CONF.parent.mkdir(parents=True, exist_ok=True)
    rs.GDM_CONF.write_text((REPO / 'configs/gnome-mobile/gdm-custom.conf').read_text())


def mobile_up(f, pid=500, uid=60578):
    """A greeter whose shell answers, holds the touchscreen and lit the panel."""
    f.units['gdm.service'] = 'active'
    f.shells = [(pid, uid, uid)]
    f.answering = {pid}
    f.touch_pids = {pid}


def order(calls, needle):
    for i, c in enumerate(calls):
        if c[:len(needle)] == needle:
            return i
    return -1


class Modes(unittest.TestCase):
    def test_effective_defaults_to_phosh(self):
        reset_files()
        self.assertEqual(rs.effective_mode(), 'phosh')
        reset_files(effective='garbage')
        self.assertEqual(rs.effective_mode(), 'phosh')
        reset_files(effective='gnome-mobile')
        self.assertEqual(rs.effective_mode(), 'gnome-mobile')
        reset_files(persistent='# comment\n\ngnome-mobile')
        self.assertEqual(rs.persistent_mode(), 'gnome-mobile')

    def test_is_command(self):
        reset_files(effective='gnome-mobile')
        self.assertEqual(rs.main(['is', 'gnome-mobile'], FakeSystem()), 0)
        self.assertEqual(rs.main(['is', 'phosh'], FakeSystem()), 1)

    def test_gdm_autologin_parse(self):
        self.assertTrue(rs.gdm_autologin('[daemon]\nAutomaticLoginEnable=True\n'))
        self.assertTrue(rs.gdm_autologin('[daemon]\nTimedLoginEnable = true\n'))
        self.assertFalse(rs.gdm_autologin('[daemon]\n#AutomaticLoginEnable=true\n'))
        self.assertFalse(rs.gdm_autologin('[security]\nAutomaticLoginEnable=true\n'))
        self.assertFalse(rs.gdm_autologin((REPO / 'configs/gnome-mobile/gdm-custom.conf').read_text()))


class Boot(unittest.TestCase):
    def test_phosh_boot_starts_nothing(self):
        reset_files(persistent='phosh')
        f = FakeSystem()
        self.assertEqual(rs.main(['boot'], f), 0)
        self.assertEqual(rs.effective_mode(), 'phosh')
        self.assertEqual(f.calls, [])

    def test_missing_file_is_phosh(self):
        reset_files()
        f = FakeSystem()
        rs.main(['boot'], f)
        self.assertEqual(rs.effective_mode(), 'phosh')
        self.assertEqual(f.calls, [])

    def test_mobile_without_packages_boots_phosh(self):
        reset_files(persistent='gnome-mobile')
        install_mobile_prereqs()
        f = FakeSystem()
        f.pacman_ok = False
        rs.main(['boot'], f)
        self.assertEqual(rs.effective_mode(), 'phosh')
        self.assertEqual(order(f.calls, ('systemctl', 'start', 'gdm.service')), -1)

    def test_mobile_with_autologin_boots_phosh(self):
        reset_files(persistent='gnome-mobile')
        install_mobile_prereqs()
        rs.GDM_CONF.write_text('[daemon]\nAutomaticLoginEnable=true\nAutomaticLogin=phone\n')
        f = FakeSystem()
        rs.main(['boot'], f)
        self.assertEqual(rs.effective_mode(), 'phosh')
        self.assertEqual(f.calls, [])

    def test_mobile_arms_watchdog_before_gdm(self):
        reset_files(persistent='gnome-mobile')
        install_mobile_prereqs()
        f = FakeSystem()
        self.assertEqual(rs.main(['boot'], f), 0)
        self.assertEqual(rs.effective_mode(), 'gnome-mobile')
        w = order(f.calls, ('systemctl', 'start', 'rog5-shell-watchdog.service'))
        g = order(f.calls, ('systemctl', 'start', 'gdm.service'))
        self.assertTrue(0 <= w < g, f.calls)

    def test_watchdog_start_failure_boots_phosh(self):
        reset_files(persistent='gnome-mobile')
        install_mobile_prereqs()
        f = FakeSystem()
        f.fail_start = {'rog5-shell-watchdog.service'}
        self.assertEqual(rs.main(['boot'], f), 1)
        self.assertEqual(rs.effective_mode(), 'phosh')
        self.assertEqual(order(f.calls, ('systemctl', 'start', 'gdm.service')), -1)
        self.assertNotEqual(order(f.calls, ('systemctl', 'start', 'rog5-phosh.service')), -1)


def run_watchdog(f, max_s=2000):
    """Runs cmd_watchdog until it returns, or raises after max_s fake seconds."""
    start = f.t
    prev = f.on_sleep

    def guard(s):
        if prev:
            prev(s)
        if s.t - start > max_s:
            raise TimeoutError('watchdog did not finish')
    f.on_sleep = guard
    return rs.cmd_watchdog(f)


class WatchdogStartup(unittest.TestCase):
    def setUp(self):
        reset_files(persistent='gnome-mobile', effective='gnome-mobile')

    def fell_back(self, f):
        return rs.persistent_mode() == 'phosh' and rs.effective_mode() == 'phosh'

    def test_never_ready_falls_back_to_locked_phosh(self):
        f = FakeSystem()
        f.units['gdm.service'] = 'active'
        f.units['rog5-phosh.service'] = 'inactive'
        rc = run_watchdog(f)
        self.assertEqual(rc, 0)
        self.assertTrue(self.fell_back(f))
        self.assertGreaterEqual(f.t - 1000, rs.ARM_S)
        self.assertLess(f.t - 1000, rs.ARM_S + 60)
        reason = (rs.STATE_DIR / 'shell-fallback').read_text()
        self.assertIn('no answering gnome-shell', reason)
        g = order(f.calls, ('systemctl', 'stop', 'gdm.service'))
        p = order(f.calls, ('systemctl', 'start', 'rog5-phosh.service'))
        self.assertTrue(0 <= g < p, f.calls)

    def test_panel_never_lit(self):
        f = FakeSystem()
        mobile_up(f)
        f.dsi['dpms'] = 'Off'
        run_watchdog(f)
        self.assertIn('panel never lit', (rs.STATE_DIR / 'shell-fallback').read_text())

    def test_touchscreen_not_opened(self):
        f = FakeSystem()
        mobile_up(f)
        f.touch_pids = set()
        run_watchdog(f)
        self.assertIn('touchscreen', (rs.STATE_DIR / 'shell-fallback').read_text())

    def test_ready_then_supervises_quietly(self):
        f = FakeSystem()
        mobile_up(f)
        wd = rs.Watchdog(f)
        for _ in range(400):            # 800 s
            self.assertIsNone(wd.step())
            f.sleep(rs.POLL_S)
        self.assertTrue(wd.ready)

    def test_late_greeter_within_window(self):
        f = FakeSystem()

        def appear(s):
            if s.t - 1000 >= 60 and not s.shells:
                mobile_up(s)
        f.on_sleep = appear
        wd = rs.Watchdog(f)
        for _ in range(60):
            self.assertIsNone(wd.step())
            f.sleep(rs.POLL_S)
        self.assertTrue(wd.ready)


class WatchdogSupervise(unittest.TestCase):
    def setUp(self):
        reset_files(persistent='gnome-mobile', effective='gnome-mobile')
        self.f = FakeSystem()
        mobile_up(self.f)
        self.wd = rs.Watchdog(self.f)
        self.assertIsNone(self.wd.step())
        self.assertTrue(self.wd.ready)

    def steps(self, seconds):
        for _ in range(int(seconds / rs.POLL_S)):
            self.f.sleep(rs.POLL_S)
            r = self.wd.step()
            if r:
                return r
        return None

    def test_hung_shell(self):
        self.f.answering = set()          # e.g. SIGSTOP
        self.assertIsNone(self.steps(rs.DEAD_S - 4))
        self.assertIn('no answering shell', self.steps(10))

    def test_short_hiccup_is_fine(self):
        self.f.answering = set()
        self.assertIsNone(self.steps(30))
        self.f.answering = {500}
        self.assertIsNone(self.steps(120))

    def test_greeter_to_user_session(self):
        self.f.shells = []
        self.f.answering = set()
        self.assertIsNone(self.steps(12))
        self.f.shells = [(501, 1000, 1000)]
        self.f.answering = {501}
        self.assertIsNone(self.steps(60))
        # the user session's shell gets the big-core floor
        self.assertNotEqual(order(self.f.calls, ('systemctl', 'restart',
                                                 'rog5-session-boost.service')), -1)

    def test_gdm_stopped(self):
        self.f.units['gdm.service'] = 'failed'
        self.assertIsNone(self.steps(rs.GDM_GRACE_S - 4))
        self.assertEqual(self.steps(10), 'gdm stopped')

    def test_crash_loop(self):
        pid = [600]

        def respawn(s):
            pid[0] += 1
            s.shells = [(pid[0], 1000, 1000)]
            s.answering = {pid[0]}
        r = None
        for _ in range(rs.CRASH_MAX + 1):
            respawn(self.f)
            r = self.steps(20)
            if r:
                break
        self.assertIsNotNone(r)
        self.assertIn('started', r)

    def test_normal_relogins_are_not_a_loop(self):
        pid = [600]
        for _ in range(rs.CRASH_MAX - 1):
            pid[0] += 1
            self.f.shells = [(pid[0], 1000, 1000)]
            self.f.answering = {pid[0]}
            self.assertIsNone(self.steps(70))

    def test_phosh_from_gdm_counts_as_alive(self):
        self.f.shells = []
        self.f.answering = set()
        self.f.phosh_procs = [(700, 1000, 1000)]
        self.assertIsNone(self.steps(120))


class Fallback(unittest.TestCase):
    def setUp(self):
        reset_files(persistent='gnome-mobile', effective='gnome-mobile')

    def test_unlocked_phosh_fails_closed(self):
        f = FakeSystem()
        f.units['rog5-phosh.service'] = 'inactive'
        f.phosh_locks = False
        self.assertEqual(rs.fallback(f, 'test'), 1)
        last_phosh = max(i for i, c in enumerate(f.calls) if 'rog5-phosh.service' in c)
        self.assertEqual(f.calls[last_phosh][1], 'stop')
        self.assertIn('FAILED CLOSED', (TMP / 'kmsg').read_text())

    def test_gdm_sessions_terminated_and_drm_released(self):
        f = FakeSystem()
        f.units['gdm.service'] = 'active'
        f.sess = [{'Id': '3', 'Service': 'gdm-password', 'Leader': '1', 'State': 'active'},
                  {'Id': '2', 'Service': 'gdm-launch-environment', 'Leader': '2', 'State': 'active'},
                  {'Id': '5', 'Service': 'sshd', 'Leader': '3', 'State': 'active'}]
        f.drm = [99]
        self.assertEqual(rs.fallback(f, 'test'), 0)
        self.assertIn(('terminate', '3'), f.calls)
        self.assertIn(('terminate', '2'), f.calls)
        self.assertNotIn(('terminate', '5'), f.calls)
        self.assertIn((99, 15), f.kills)
        self.assertIn((99, 9), f.kills)
        # the session settings are restored as the phone user
        self.assertIn([rs.SESSION_HELPER, 'stop'], f.user_runs)

    def test_switch_to_mobile_needs_pin_confirmation(self):
        reset_files(persistent='phosh', effective='phosh')
        install_mobile_prereqs()
        f = FakeSystem()
        self.assertEqual(rs.main(['switch', 'gnome-mobile'], f), 2)
        self.assertEqual(rs.persistent_mode(), 'phosh')
        self.assertEqual(f.calls, [])
        self.assertEqual(rs.main(['set', 'gnome-mobile'], f), 2)
        self.assertEqual(rs.persistent_mode(), 'phosh')

    def test_switch_to_mobile_arms_watchdog_first(self):
        reset_files(persistent='phosh', effective='phosh')
        install_mobile_prereqs()
        f = FakeSystem()
        self.assertEqual(rs.main(['switch', 'gnome-mobile', '--pin-is-6-digits'], f), 0)
        w = order(f.calls, ('systemctl', 'restart', 'rog5-shell-watchdog.service'))
        s = order(f.calls, ('systemctl', 'stop', 'rog5-desktop-mode.service'))
        g = order(f.calls, ('systemctl', 'start', 'gdm.service'))
        self.assertTrue(0 <= w < s < g, f.calls)
        self.assertEqual(rs.effective_mode(), 'gnome-mobile')

    def test_switch_to_mobile_without_watchdog_stays(self):
        reset_files(persistent='phosh', effective='phosh')
        install_mobile_prereqs()
        f = FakeSystem()
        f.fail_start = {'rog5-shell-watchdog.service'}
        self.assertEqual(rs.main(['switch', 'gnome-mobile', '--pin-is-6-digits'], f), 1)
        self.assertEqual(rs.effective_mode(), 'phosh')
        self.assertEqual(rs.persistent_mode(), 'phosh')
        self.assertEqual(order(f.calls, ('systemctl', 'stop', 'rog5-phosh.service')), -1)

    def test_switch_to_phosh(self):
        f = FakeSystem()
        f.units['rog5-phosh.service'] = 'inactive'
        f.units['gdm.service'] = 'active'
        self.assertEqual(rs.main(['switch', 'phosh'], f), 0)
        self.assertEqual(rs.effective_mode(), 'phosh')
        w = order(f.calls, ('systemctl', 'stop', 'rog5-shell-watchdog.service'))
        g = order(f.calls, ('systemctl', 'stop', 'gdm.service'))
        self.assertTrue(0 <= w < g)


class GsdPower(unittest.TestCase):
    def me(self):
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name

    def test_cases(self):
        f = FakeSystem()
        f.sess = [{'Id': '1', 'Name': self.me(), 'Desktop': 'gnome-mobile', 'Class': 'user',
                   'State': 'active'}]
        self.assertEqual(rs.cmd_gsd_power_allowed(f), 1)
        f.sess = [{'Id': '1', 'Name': self.me(), 'Desktop': '', 'Class': 'greeter',
                   'State': 'active'}]
        self.assertEqual(rs.cmd_gsd_power_allowed(f), 1)
        f.sess = [{'Id': '1', 'Name': self.me(), 'Desktop': 'phosh', 'Class': 'user',
                   'State': 'active'},
                  {'Id': '2', 'Name': 'someone-else', 'Desktop': 'gnome-mobile', 'Class': 'user',
                   'State': 'active'},
                  {'Id': '3', 'Name': self.me(), 'Desktop': 'gnome-mobile', 'Class': 'user',
                   'State': 'closing'}]
        self.assertEqual(rs.cmd_gsd_power_allowed(f), 0)
        f.sess = []
        self.assertEqual(rs.cmd_gsd_power_allowed(f), 0)


class GreeterMonitors(unittest.TestCase):
    def test_panel_only_configs_copied(self):
        home = TMP / 'home-phone'
        (home / '.config').mkdir(parents=True, exist_ok=True)
        (home / '.config/monitors.xml').write_text('''<monitors version="2">
  <configuration><layoutmode>logical</layoutmode>
    <logicalmonitor><x>0</x><y>0</y><scale>2.6666666666666665</scale><primary>yes</primary>
      <monitor><monitorspec><connector>DSI-1</connector><vendor>unknown</vendor><product>unknown</product><serial>unknown</serial></monitorspec>
        <mode><width>1080</width><height>2448</height><rate>120.000</rate></mode></monitor></logicalmonitor>
  </configuration>
  <configuration><layoutmode>logical</layoutmode>
    <logicalmonitor><x>0</x><y>0</y><scale>1</scale><primary>yes</primary>
      <monitor><monitorspec><connector>DP-1</connector><vendor>MSI</vendor><product>x</product><serial>y</serial></monitorspec>
        <mode><width>5120</width><height>1440</height><rate>60.000</rate></mode></monitor></logicalmonitor>
    <disabled><monitorspec><connector>DSI-1</connector><vendor>unknown</vendor><product>unknown</product><serial>unknown</serial></monitorspec></disabled>
  </configuration>
</monitors>
''')
        old = os.path.expanduser
        os.path.expanduser = lambda p: str(home) if p.startswith('~') else old(p)
        try:
            self.assertEqual(rs.cmd_greeter_monitors(FakeSystem()), 0)
        finally:
            os.path.expanduser = old
        out = rs.GREETER_MONITORS.read_text()
        self.assertIn('2.6666666666666665', out)
        self.assertNotIn('DP-1', out)
        self.assertEqual(out.count('<configuration>'), 1)


def unit_lines(path, key):
    return [l.split('=', 1)[1] for l in Path(path).read_text().splitlines() if l.startswith(key + '=')]


class UnitGates(unittest.TestCase):
    """The ExecCondition lines, run by a real /bin/sh and grep."""

    def gate(self, cmdline, effective):
        eff = TMP / 'gate-effective'
        if effective is None:
            eff.unlink(missing_ok=True)
        else:
            eff.write_text(effective + '\n')
        cmd = cmdline.replace('/run/rog5-shell/effective', str(eff)).replace('/usr/bin/grep', 'grep')
        if cmd.startswith("/bin/sh -c '"):
            argv = ['sh', '-c', cmd[len("/bin/sh -c '"):-1]]
        else:
            argv = cmd.split()
        return subprocess.run(argv).returncode == 0

    def test_exactly_one_side(self):
        sysd = REPO / 'configs/systemd'
        phosh_side = [unit_lines(sysd / f'{u}.service.d/50-rog5-shell.conf', 'ExecCondition')[0]
                      for u in ('rog5-phosh', 'rog5-desktop-mode', 'rog5-gnome')]
        gdm = unit_lines(sysd / 'gdm.service.d/50-rog5-gnome-mobile.conf', 'ExecCondition')[0]
        wd = unit_lines(sysd / 'rog5-shell-watchdog.service', 'ExecCondition')[0]
        for eff, mobile in ((None, False), ('phosh', False), ('garbage', False),
                            ('gnome-mobile', True)):
            for c in phosh_side:
                self.assertEqual(self.gate(c, eff), not mobile, (c, eff))
            self.assertEqual(self.gate(gdm, eff), mobile, eff)
            self.assertEqual(self.gate(wd, eff), mobile, eff)
            # agrees with rog5-shell's own reading
            reset_files(effective=eff) if eff else reset_files()
            self.assertEqual(rs.effective_mode() == 'gnome-mobile', mobile)

    def test_ordering_and_requirements(self):
        sysd = REPO / 'configs/systemd'
        gdm_after = ' '.join(unit_lines(sysd / 'gdm.service.d/50-rog5-gnome-mobile.conf', 'After'))
        gdm_req = ' '.join(unit_lines(sysd / 'gdm.service.d/50-rog5-gnome-mobile.conf', 'Requires'))
        self.assertIn('rog5-shell-watchdog.service', gdm_req)
        for u in ('rog5-phosh', 'rog5-desktop-mode', 'rog5-gnome', 'rog5-shell-watchdog',
                  'rog5-shell-select'):
            self.assertIn(f'{u}.service', gdm_after)
        for u in ('rog5-phosh', 'rog5-desktop-mode', 'rog5-gnome'):
            after = ' '.join(unit_lines(sysd / f'{u}.service.d/50-rog5-shell.conf', 'After'))
            # one direction only: a mutual After= deadlocks two pending start jobs
            self.assertNotIn('gdm.service', after)
            self.assertIn('rog5-shell-select.service', after)
        # the watchdog must not be ordered after the selector, which starts it
        self.assertEqual(unit_lines(sysd / 'rog5-shell-watchdog.service', 'After'), [])
        self.assertNotIn('Conflicts', (sysd / 'gdm.service.d/50-rog5-gnome-mobile.conf').read_text())

    def test_manifest_lists_the_files(self):
        manifest = (REPO / 'configs/rootfs/userspace.tsv').read_text()
        for src in ('scripts/device/rog5-shell', 'configs/systemd/rog5-shell-select.service',
                    'configs/systemd/rog5-shell-watchdog.service',
                    'configs/systemd/gdm.service.d/50-rog5-gnome-mobile.conf',
                    'configs/systemd/rog5-phosh.service.d/50-rog5-shell.conf'):
            self.assertIn(src, manifest)
            self.assertTrue((REPO / src).exists(), src)
        self.assertIn('enable\tsystem\trog5-shell-select.service', manifest)
        # GNOME Mobile itself is opt-in: never built or installed by default
        self.assertNotIn('gnome-mobile', (REPO / 'configs/rootfs/custom-packages.txt').read_text())


class SessionHelper(unittest.TestCase):
    def test_save_set_restore(self):
        home = TMP / 'helper-home'
        binp = TMP / 'helper-bin'
        for d in (home, binp):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
        db = TMP / 'helper-db'
        db.write_text('')
        (binp / 'gsettings').write_text(f'''#!/bin/sh
db={db}
case $1 in
writable) exit 0 ;;
set) grep -v "^/$(echo $2 | tr . /)/$3 " $db >$db.t; echo "/$(echo $2 | tr . /)/$3 '$4'" >>$db.t; mv $db.t $db ;;
reset) grep -v "^/$(echo $2 | tr . /)/$3 " $db >$db.t; mv $db.t $db ;;
esac
''')
        (binp / 'dconf').write_text(f'''#!/bin/sh
db={db}
case $1 in
read) awk -v k="$2" '$1 == k {{print $2}}' $db ;;
write) grep -v "^$2 " $db >$db.t; echo "$2 $3" >>$db.t; mv $db.t $db ;;
esac
''')
        for b in ('gsettings', 'dconf'):
            os.chmod(binp / b, 0o755)
        envh = dict(os.environ, HOME=str(home), PATH=f'{binp}:{os.environ["PATH"]}')
        envh.pop('XDG_STATE_HOME', None)
        helper = str(REPO / 'scripts/device/rog5-gnome-mobile-session')
        key = '/org/gnome/settings-daemon/plugins/power/power-button-action'

        def val():
            for l in db.read_text().splitlines():
                if l.startswith(key + ' '):
                    return l.split(' ', 1)[1]
            return None
        # unset (default) -> nothing -> back to unset
        subprocess.run(['sh', helper, 'start'], env=envh, check=True)
        self.assertEqual(val(), "'nothing'")
        subprocess.run(['sh', helper, 'start'], env=envh, check=True)   # twice: keeps the first save
        subprocess.run(['sh', helper, 'stop'], env=envh, check=True)
        self.assertIsNone(val())
        # a user value survives
        db.write_text(f"{key} 'interactive'\n")
        subprocess.run(['sh', helper, 'start'], env=envh, check=True)
        self.assertEqual(val(), "'nothing'")
        subprocess.run(['sh', helper, 'stop'], env=envh, check=True)
        self.assertEqual(val(), "'interactive'")
        subprocess.run(['sh', helper, 'stop'], env=envh, check=True)    # nothing saved: no-op
        self.assertEqual(val(), "'interactive'")


class Patches(unittest.TestCase):
    """The package directories reference every patch with a matching b2sum."""

    def test_pkgbuild_patch_sums(self):
        import hashlib
        for d in ('mutter-mobile', 'gnome-shell-mobile'):
            pdir = REPO / 'packages/gnome-mobile' / d
            text = (pdir / 'PKGBUILD').read_text()
            src = re.search(r'^source=\((.*?)^\)', text, re.S | re.M).group(1).split()
            sums = re.search(r'^b2sums=\((.*?)\)', text, re.S | re.M).group(1).split()
            self.assertEqual(len(src), len(sums), d)
            patches = sorted(p.name for p in pdir.glob('*.patch'))
            self.assertEqual(sorted(s for s in src if s.endswith('.patch')), patches, d)
            for s, h in zip(src, sums):
                if s.endswith('.patch'):
                    self.assertEqual(hashlib.blake2b((pdir / s).read_bytes()).hexdigest(),
                                     h.strip("'"), f'{d}/{s}')


if __name__ == '__main__':
    try:
        r = unittest.main(exit=False, verbosity=1).result
        ok = r.wasSuccessful()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    print('PASS rog5-shell' if ok else 'FAIL rog5-shell')
    sys.exit(0 if ok else 1)
