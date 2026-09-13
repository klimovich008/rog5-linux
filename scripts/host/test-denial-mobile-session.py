#!/usr/bin/env python3
"""Execute the mobile entry's decisions with bounded, read-only fact fixtures.

No login session, PAM authentication, device, service or phone is operated.
Real ARM64 PAM behavior is a separate VM qualification.
"""
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ENTRY = Path(__file__).resolve().parents[2] / 'packaging/arch/mobile/denial-mobile-session'
LOGIN = 'Active=yes\nRemote=no\nUser=1000\nClass=user\nType=tty\nSeat=seat0'


class MobileSession(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = self.root / 'delegated.json'
        self.delegate = self.root / 'delegate.py'
        self.delegate.write_text('''import json, os, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'argv':sys.argv[2:], 'env':dict(os.environ)}))
raise SystemExit(42)
''')

    def invoke(self, *, identity='1000 1000 1000 1000 mobile\n1000',
               status='NoNewPrivs:\t0', login=LOGIN, login_failure=False,
               metadata=None, config=None, character=True, output=True,
               env=None, args=()):
        facts = {'/usr/bin/unix_chkpwd': '0 0 6755 regular file',
                 '/run/user/1000': '1000 1000 700 directory',
                 '/etc': '0 0 755 directory', '/etc/denial': '0 0 755 directory',
                 '/etc/denial/session.conf': '0 0 644 regular file',
                 '/home/mobile/.config/denial/outputs.conf': '1000 1000 600 regular file'}
        facts.update(metadata or {})
        config = config if config is not None else '''
DENIAL_DRM_DEVICE=/dev/dri/by-path/fixture-card
DENIAL_RENDER_DEVICE=/dev/dri/by-path/fixture-render
DENIAL_OUTPUT_CONFIG=/home/mobile/.config/denial/outputs.conf
'''
        lines = [f'source {shlex.quote(str(ENTRY))}',
                 f'mobile_identity() {{ printf %s {shlex.quote(identity)}; }}',
                 f'mobile_status() {{ printf %s {shlex.quote(status)}; }}',
                 ('mobile_login() { return 1; }' if login_failure else
                  f'mobile_login() {{ printf %s {shlex.quote(login)}; }}'),
                 'mobile_metadata() { case "$1" in']
        for path, value in facts.items():
            lines.append(f'{shlex.quote(path)}) printf %s {shlex.quote(value)};;')
        lines += ['*) return 1;; esac; }', 'mobile_load_config() {', config, '}',
                  'mobile_character_device() { [[ "$1" == /dev/dri/by-path/fixture-* ]] && '
                  + ('true' if character else 'false') + '; }',
                  'mobile_output_access() { [[ "$1" == /home/mobile/.config/denial/outputs.conf ]] && '
                  + ('true' if output else 'false') + '; }',
                  f'mobile_delegate() {{ exec /usr/bin/python3 {shlex.quote(str(self.delegate))} '
                  f'{shlex.quote(str(self.record))} "$@"; }}', 'mobile_main "$@"']
        environment = {'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': '/run/user/1000',
                       'XDG_SESSION_ID': 'wrong-inherited-session'}
        environment.update(env or {})
        return subprocess.run(['bash', '-c', '\n'.join(lines), 'fixture', *args],
                              env=environment, text=True, capture_output=True, timeout=5)

    def refuse(self, message, **kwargs):
        result = self.invoke(**kwargs)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertFalse(self.record.exists())

    def test_delegates_exact_check_and_environment_and_preserves_exit(self):
        result = self.invoke(args=('--check',), env={'LIBSEAT_BACKEND':'seatd', 'DENIA_SHELL_PROFILE':'desktop', 'DENIAL_PAM_SERVICE':'other'})
        self.assertEqual(result.returncode, 42, result.stderr)
        record = json.loads(self.record.read_text())
        self.assertEqual(record['argv'], ['--check'])
        self.assertEqual(record['env']['LIBSEAT_BACKEND'], 'logind')
        self.assertEqual(record['env']['DENIA_SHELL_PROFILE'], 'mobile')
        self.assertEqual(record['env']['DENIAL_PAM_SERVICE'], 'login')
        self.assertEqual(record['env']['DENIAL_DRM_DEVICE'], '/dev/dri/by-path/fixture-card')
        self.assertEqual(record['env']['DENIAL_RENDER_DEVICE'], '/dev/dri/by-path/fixture-render')
        self.assertNotIn('XDG_SESSION_ID', record['env'])

    def test_normal_start_and_empty_supplementary_groups(self):
        result = self.invoke(identity='1000 1000 1000 1000 mobile\n')
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertEqual(json.loads(self.record.read_text())['argv'], [])

    def test_wayland_logind_type_without_inherited_display(self):
        result = self.invoke(login=LOGIN.replace('Type=tty', 'Type=wayland'))
        self.assertEqual(result.returncode, 42, result.stderr)

    def test_identity_and_device_groups(self):
        for identity in ('0 0 0 0 root\n0', '1000 0 1000 1000 mobile\n1000',
                         '1000 1000 1000 1000 deck\n1000'):
            with self.subTest(identity=identity):
                self.refuse('requires real/effective', identity=identity)
        self.refuse('supplementary groups', identity='1000 1000 1000 1000 mobile\n1000 107')

    def test_refuses_nested_display(self):
        self.refuse('inherited Wayland', env={'WAYLAND_DISPLAY': 'wayland-0'})

    def test_refuses_argument_device_override(self):
        self.refuse('only --check', args=('--device', '/dev/other'))

    def test_no_new_privileges_and_missing_privilege_data(self):
        for status in ('NoNewPrivs:\t1', '', 'NoNewPrivs:\t0\nNoNewPrivs:\t0'):
            with self.subTest(status=status):
                self.refuse('NoNewPrivs', status=status)

    def test_stripped_wrong_owner_and_wrong_privileged_helper(self):
        for value in ('0 0 755 regular file', '1000 1000 6755 regular file',
                      '0 0 4755 regular file', '0 0 6777 regular file', '0 0 6755 symbolic link'):
            with self.subTest(value=value):
                self.refuse('authenticated PAM package', metadata={'/usr/bin/unix_chkpwd': value})

    def test_runtime_path_and_ownership(self):
        self.refuse('XDG_RUNTIME_DIR', env={'XDG_RUNTIME_DIR': '/tmp/runtime'})
        for value in ('0 0 700 directory', '1000 1000 755 directory', '1000 1000 700 symbolic link'):
            with self.subTest(value=value):
                self.refuse('runtime directory must', metadata={'/run/user/1000':value})

    def test_logind_fail_closed(self):
        self.refuse('cannot verify', login_failure=True)
        for original, replacement in (('Active=yes', 'Active=no'), ('Remote=no', 'Remote=yes'),
                                      ('User=1000', 'User=0'), ('Class=user', 'Class=greeter'),
                                      ('Type=tty', 'Type=x11'), ('Seat=seat0', 'Seat=')):
            with self.subTest(property=original):
                self.refuse('active local', login=LOGIN.replace(original, replacement))
        self.refuse('duplicate logind', login=LOGIN+'\nActive=yes')
        self.refuse('unexpected logind', login=LOGIN+'\nUnexpected=yes')
        self.refuse('active local', login=LOGIN.replace('User=1000\n', ''))

    def test_root_configuration_trust(self):
        for path in ('/etc', '/etc/denial', '/etc/denial/session.conf'):
            with self.subTest(path=path):
                kind = 'regular file' if path.endswith('.conf') else 'directory'
                self.refuse('root-controlled', metadata={path: f'1000 1000 755 {kind}'})
                self.refuse('writable by other', metadata={path: f'0 0 777 {kind}'})

    def test_config_cannot_switch_back_to_fixture_seat(self):
        self.refuse('preserve logind', config='LIBSEAT_BACKEND=seatd')
        self.refuse('preserve logind', config='DENIA_SHELL_PROFILE=desktop')
        self.refuse('login PAM service', config='DENIAL_PAM_SERVICE=other')

    def test_inherited_devices_do_not_substitute_missing_configuration(self):
        self.refuse('explicit DRM', config=':', env={
            'DENIAL_DRM_DEVICE':'/dev/dri/by-path/fixture-card',
            'DENIAL_RENDER_DEVICE':'/dev/dri/by-path/fixture-render'})
        self.refuse('explicit render', config='DENIAL_DRM_DEVICE=/dev/dri/by-path/fixture-card')

    def test_requires_character_devices(self):
        self.refuse('explicit DRM', character=False)

    def test_requires_existing_private_output_config(self):
        self.refuse('existing writable', output=False)
        self.refuse('mobile-owned mode 0600', metadata={
            '/home/mobile/.config/denial/outputs.conf':'1000 1000 644 regular file'})

    def test_actual_metadata_provider_rejects_symlinks(self):
        regular = self.root/'regular'; regular.write_text('fixture'); regular.chmod(0o600)
        link = self.root/'link'; link.symlink_to(regular)
        for path, expected in ((regular, 0), (link, 1)):
            result = subprocess.run(['bash', '-c', 'source "$1"; mobile_metadata "$2"',
                                     'fixture', str(ENTRY), str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, expected, result.stderr)
        self.assertEqual(regular.read_text(), 'fixture')

    def test_actual_logind_provider_selects_self_with_deadline(self):
        # Interpose only the command invocation, not the production function.
        result = subprocess.run(['bash', '-c', '''source "$1"
function /usr/bin/timeout() { printf '%s\\n' "$@"; }
mobile_login''', 'fixture', str(ENTRY)], text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = result.stdout.splitlines()
        self.assertEqual(argv[:6], ['--signal=TERM', '--kill-after=1s', '5s',
                                   '/usr/bin/loginctl', 'show-session', 'self'])
        self.assertNotIn('auto', argv)
        self.assertIn('--all', argv)

    def test_actual_output_provider_refuses_symlink_and_missing_file(self):
        regular = self.root/'outputs.conf'; regular.write_text('# fixture\n')
        link = self.root/'linked.conf'; link.symlink_to(regular)
        for path, expected in ((regular, 0), (link, 1), (self.root/'absent', 1)):
            result = subprocess.run(['bash', '-c', 'source "$1"; mobile_output_access "$2"',
                                     'fixture', str(ENTRY), str(path)],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == '__main__':
    unittest.main()
