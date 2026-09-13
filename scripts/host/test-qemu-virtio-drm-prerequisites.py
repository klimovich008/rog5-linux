#!/usr/bin/env python3
"""Exercise the actual guest prerequisite selection with bounded file fixtures."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import os
import stat
import re
import subprocess

SPEC = importlib.util.spec_from_file_location(
    'guest', Path(__file__).with_name('test-qemu-virtio-drm.py'))
GUEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUEST)


class RuntimePrerequisites(unittest.TestCase):
    @staticmethod
    def editor_lines():
        return [
            '-> xdg_wm_base#2.get_xdg_surface(new id xdg_surface#3, wl_surface#4)',
            '-> xdg_surface#3.get_toplevel(new id xdg_toplevel#5)',
            '-> xdg_toplevel#5.set_title("rog5-text-probe.txt - Mousepad")',
            'xdg_toplevel#5.configure(540, 1200, array[4])',
            'xdg_surface#3.configure(71)',
            '-> xdg_surface#3.ack_configure(71)',
            '-> wl_surface#4.attach(wl_buffer#8, 0, 0)',
            '-> wl_surface#4.commit()',
        ]

    @classmethod
    def editor_log(cls):
        lines = cls.editor_lines() + [
            'wl_keyboard#6.enter(72, wl_surface#4, array[0])',
            *[f'wl_keyboard#6.key({index}, 1000, {key}, {state})'
              for index, (key, state) in enumerate([
                  (20, 1), (20, 0), (18, 1), (18, 0), (31, 1), (31, 0),
                  (20, 1), (20, 0), (14, 1), (14, 0), (20, 1), (20, 0)])],
        ]
        return ''.join('EDITOR_WAYLAND [100.01] {Default Queue} '+line+'\n' for line in lines)

    @staticmethod
    def audit(count):
        return f'Denial/Volition output scheduler audit presentations={count}\n'

    def test_app_channel_writer_required_and_excluded_elsewhere(self):
        base=['python3',str(Path(__file__).with_name('test-qemu-virtio-drm.py')),
              '--runtime','/missing','--kernel','/missing','--deniald','/missing',
              '--image','0'*64,'--output','/missing-output']
        for options in [ ['--observe-mobile','--observe-mobile-apps','--launcher-reference','/missing','--flutter-bundle','/missing','--render-node','/missing'],
                         ['--evidence-writer','/missing'] ]:
            run=subprocess.run(base+options,capture_output=True,text=True,timeout=3)
            self.assertNotEqual(run.returncode,0)
            self.assertIn('app interaction requires --evidence-writer',run.stderr)

    def test_editor_protocol_accepts_exact_native_key_lifecycles_and_ansi(self):
        log = self.editor_log()
        for text in (log, log.replace('#', '@'), log.replace('xdg_', '\x1b[32mxdg_').replace('(', '\x1b[0m(')):
            with self.subTest(text=text[:40]):
                result = GUEST.editor_result(text)
                self.assertEqual(result['status'], 'PASS')
                self.assertTrue(result['native_toplevel_observed'])
                self.assertEqual(result['keys'], [
                    (20, 1), (20, 0), (18, 1), (18, 0), (31, 1), (31, 0),
                    (20, 1), (20, 0), (14, 1), (14, 0), (20, 1), (20, 0)])
                self.assertIn('visual text checked separately', result['scope'])

    def test_editor_protocol_accepts_observed_exact_tmp_title_only(self):
        for title in ('/tmp/rog5-text-probe.txt - Mousepad',
                      '*/tmp/rog5-text-probe.txt - Mousepad',
                      '*rog5-text-probe.txt - Mousepad'):
            with self.subTest(title=title):
                log = self.editor_log().replace('rog5-text-probe.txt - Mousepad', title)
                self.assertEqual(GUEST.editor_result(log)['status'], 'PASS')
        for title in ('/other/rog5-text-probe.txt - Mousepad',
                      '/tmp/fake-rog5-text-probe.txt - Mousepad',
                      'rog5-text-probe.txt.backup - Mousepad',
                      '/tmp/rog5-text-probe.txt - Other'):
            with self.subTest(title=title):
                log = self.editor_log().replace('rog5-text-probe.txt - Mousepad', title)
                self.assertEqual(GUEST.editor_result(log)['status'], 'FAIL')

    def test_editor_protocol_requires_linked_toplevel_and_exact_probe_title(self):
        log = self.editor_log()
        invalid = ['', log.replace('rog5-text-probe.txt', 'unrelated.txt'),
                   log.replace('rog5-text-probe.txt', 'fake-rog5-text-probe.txt'),
                   log.replace('EDITOR_WAYLAND ', ''),
                   log.replace('get_toplevel(new id xdg_toplevel#5)', 'get_toplevel(new id xdg_toplevel#9)'),
                   log.replace('enter(72, wl_surface#4', 'enter(72, wl_surface#9')]
        for index in range(9):
            lines = log.splitlines(keepends=True)
            invalid.append(''.join(lines[:index]+lines[index+1:]))
        for text in invalid:
            with self.subTest(text=text[:70]):
                self.assertEqual(GUEST.editor_result(text)['status'], 'FAIL')

    def test_editor_protocol_rejects_extra_missing_wrong_and_unbalanced_keys(self):
        log = self.editor_log()
        lines = log.splitlines(keepends=True)
        invalid = [log+lines[-1], ''.join(lines[:-1]),
                   log.replace('1000, 18,', '1000, 19,'),
                   log.replace('1000, 14, 0)', '1000, 14, 1)'),
                   log.replace('wl_keyboard#6.key', 'wl_keyboard#9.key')]
        for text in invalid:
            with self.subTest(text=text[-90:]):
                self.assertEqual(GUEST.editor_result(text)['status'], 'FAIL')

    def test_editor_readiness_requires_commit_and_later_complete_interval(self):
        parser = GUEST.EditorProtocol()
        parser.feed(self.audit(9).encode())
        self.assertFalse(parser.ready)
        for line in self.editor_lines():
            parser.feed(('EDITOR_WAYLAND '+line+'\n').encode())
            self.assertFalse(parser.ready)
        parser.feed(self.audit(9).encode())  # May overlap the commit.
        self.assertFalse(parser.ready)
        parser.feed(self.audit(0).encode())
        self.assertFalse(parser.ready)
        parser.feed(self.audit(2).encode())  # Counts are per interval, not cumulative.
        self.assertTrue(parser.ready)

    def test_editor_readiness_rejects_wrong_order_ids_serial_and_null_attach(self):
        lines = self.editor_lines()
        variants = [lines[:i]+lines[i+1:] for i in range(len(lines))]
        variants += [lines[:5]+[lines[5].replace('(71)', '(72)')]+lines[6:],
                     lines[:6]+[lines[6].replace('wl_buffer#8', 'nil')]+lines[7:],
                     lines[:6]+[lines[6].replace('wl_surface#4', 'wl_surface#9')]+lines[7:],
                     lines[:5]+[lines[6], lines[5], lines[7]],
                     lines[:3]+[lines[4], lines[3]]+lines[5:]]
        for variant in variants:
            with self.subTest(variant=variant):
                parser = GUEST.EditorProtocol()
                parser.feed((''.join('EDITOR_WAYLAND '+line+'\n' for line in variant)+self.audit(1)*2).encode())
                self.assertFalse(parser.ready)

    def test_editor_stream_latches_across_chunks_without_tail_loss(self):
        parser = GUEST.EditorProtocol()
        log = self.editor_log().encode()
        for value in log:
            parser.feed(bytes([value]))
        for _ in range(150):
            parser.feed(b'unrelated log ' + b'x'*1000+b'\n')
        parser.feed((self.audit(1)*2).encode())
        self.assertTrue(parser.ready)
        self.assertEqual(parser.result()['status'], 'PASS')
        self.assertEqual(parser.pending, b'')

    def test_editor_cleanup_preserves_completed_evidence_but_revokes_readiness(self):
        for event in ('-> xdg_toplevel#5.destroy()', '-> xdg_surface#3.destroy()',
                      '-> wl_surface#4.destroy()',
                      '-> wl_surface#4.attach(nil, 0, 0)\nEDITOR_WAYLAND -> wl_surface#4.commit()'):
            with self.subTest(event=event):
                parser = GUEST.EditorProtocol()
                parser.feed((self.editor_log()+self.audit(1)*2).encode())
                self.assertTrue(parser.ready)
                parser.feed(('EDITOR_WAYLAND '+event+'\n'+self.audit(1)*2).encode())
                self.assertFalse(parser.ready)
                self.assertEqual(parser.result()['status'], 'PASS')
                parser.feed(b'EDITOR_WAYLAND wl_keyboard#6.key(80, 1000, 20, 1)\n')
                self.assertTrue(parser.bad_keys)
                self.assertEqual(parser.result()['status'], 'FAIL')

    def test_editor_destroyed_before_ready_never_arms(self):
        parser = GUEST.EditorProtocol()
        parser.feed((self.editor_log()+'EDITOR_WAYLAND -> xdg_toplevel#5.destroy()\n'+self.audit(1)*3).encode())
        self.assertFalse(parser.ready)

    def test_editor_commit_without_attach_retains_current_buffer(self):
        parser = GUEST.EditorProtocol()
        parser.feed((self.editor_log()+self.audit(1)*2).encode())
        self.assertTrue(parser.ready)
        for line in ('xdg_toplevel#5.configure(540, 1200, array[4])',
                     'xdg_surface#3.configure(73)',
                     '-> xdg_surface#3.ack_configure(73)',
                     '-> wl_surface#4.commit()',
                     '-> wl_surface#4.commit()'):
            parser.feed(('EDITOR_WAYLAND '+line+'\n').encode())
            self.assertTrue(parser.mapped)
            self.assertTrue(parser.ready)
        parser.feed(b'EDITOR_WAYLAND -> wl_surface#4.attach(nil, 0, 0)\n')
        self.assertTrue(parser.mapped)  # Pending NULL does not alter current content.
        parser.feed(b'EDITOR_WAYLAND -> wl_surface#4.commit()\n')
        self.assertFalse(parser.mapped)
        self.assertFalse(parser.ready)
        parser.feed(b'EDITOR_WAYLAND -> wl_surface#4.commit()\n')
        self.assertFalse(parser.mapped)

    def test_editor_stream_bounds_and_truncation_fail_closed(self):
        parser = GUEST.EditorProtocol()
        with self.assertRaises(ValueError):
            parser.feed(b'x' * 16385)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'serial.log'
            path.write_bytes(self.editor_log().encode())
            parser = GUEST.EditorProtocol()
            parser.read_available(path)
            offset = parser.offset
            parser.read_available(path)
            self.assertEqual(parser.offset, offset)
            self.assertEqual(parser.result()['status'], 'PASS')
            path.write_bytes(b'')
            with self.assertRaises(ValueError):
                parser.read_available(path)

    @staticmethod
    def runtime_function():
        script = Path(__file__).resolve().parents[2]/'tools/qemu-virtio-drm/guest.sh'
        return re.search(r'^prepare_editor_runtime\(\) \{\n.*?^\}', script.read_text(), re.M | re.S)[0]

    def prepare_cache_fixture(self, directory, failure=''):
        root = Path(directory)
        tools = root/'bin'
        tools.mkdir()
        schemas, mime, cache = (root/name for name in ('schemas', 'mime', 'cache'))
        schemas.mkdir()
        mime.mkdir()
        (schemas/'fixture.gschema.xml').write_text('<schema/>')
        (mime/'fixture.xml').write_text('<mime/>')
        for name, script in {
            'glib-compile-schemas': '[[ $1 == --strict && $2 == --targetdir=* ]]\nprintf schema > "${2#--targetdir=}/gschemas.compiled"',
            'update-mime-database': 'test -s "$1/packages/fixture.xml"\nprintf mime > "$1/mime.cache"',
        }.items():
            if failure == name:
                script = 'exit 42'
            elif failure == name+'-empty':
                script = ':'
            tool = tools/name
            tool.write_text('#!/bin/bash\nset -euo pipefail\n'+script+'\n')
            tool.chmod(0o700)
        command = ['bash', '-c', 'set -euo pipefail\n'+self.runtime_function()+
                   '\nprepare_editor_runtime "$1" "$2" "$3"\n'
                   'printf "ENV %s %s\\n" "$GSETTINGS_SCHEMA_DIR" "$XDG_DATA_DIRS"',
                   'fixture', str(schemas), str(mime), str(cache)]
        env = dict(os.environ, PATH=str(tools)+':'+os.environ['PATH'])
        env.pop('GSETTINGS_SCHEMA_DIR', None)
        return root, cache, command, env

    def test_editor_derived_runtime_caches_and_exports_are_guest_local(self):
        with tempfile.TemporaryDirectory() as directory:
            root, cache, command, env = self.prepare_cache_fixture(directory)
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('PASS guest RAM GSettings and MIME caches prepared', result.stdout)
            self.assertIn(f'ENV {cache}/schemas {cache}:/usr/local/share:/usr/share', result.stdout)
            self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o700)
            self.assertEqual((root/'schemas/fixture.gschema.xml').read_text(), '<schema/>')
            self.assertEqual((root/'mime/fixture.xml').read_text(), '<mime/>')
            self.assertFalse((root/'schemas/gschemas.compiled').exists())
            self.assertFalse((root/'mime/mime.cache').exists())
            repeat = subprocess.run(command, env=env, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(repeat.returncode, 0)
            self.assertNotIn('PASS', repeat.stdout)

    def test_editor_derived_runtime_cache_failures_never_export_success(self):
        for failure in ('glib-compile-schemas', 'update-mime-database',
                        'glib-compile-schemas-empty', 'update-mime-database-empty'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                _, _, command, env = self.prepare_cache_fixture(directory, failure)
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('PASS', result.stdout)
                self.assertNotIn('ENV', result.stdout)

    def test_egl_comparison_requires_all_modes_and_observations(self):
        lines = []
        for mode in ('exit', 'unbind', 'release'):
            lines += [f'EGL_THREAD mode={mode} stage=live-collision ok=0 error=0x3002',
                      f'EGL_THREAD mode={mode} stage=after-join ok=1 error=0x3000',
                      f'PASS EGL thread probe mode={mode}']
        log = '\n'.join(lines)
        self.assertEqual(GUEST.egl_thread_result(log)['status'], 'PASS')
        exit_failed = log.replace('mode=exit stage=after-join ok=1 error=0x3000',
                                 'mode=exit stage=after-join ok=0 error=0x3002')
        result = GUEST.egl_thread_result(exit_failed)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['after_join']['exit']['acquired'])
        for bad in ('', log+'\n'+lines[-1], log.replace(lines[0], ''),
                    log.replace('mode=unbind stage=after-join ok=1 error=0x3000',
                                'mode=unbind stage=after-join ok=0 error=0x3002'),
                    log.replace('stage=live-collision ok=0 error=0x3002',
                                'stage=live-collision ok=1 error=0x3000'),
                    log+'\nFAIL EGL thread probe: cleanup'):
            self.assertEqual(GUEST.egl_thread_result(bad)['status'], 'FAIL')

    def test_mobile_readiness_requires_real_presentation(self):
        for text in ('', 'Flutter per-output render audit presented_outputs=0',
                     'Flutter per-output render audit presented_outputs=1',
                     'Denial/Volition output scheduler audit presentations=0',
                     'unrelated presentations=1',
                     'Denial/Volition output scheduler audit presentations=1 presentations=0'):
            self.assertFalse(GUEST.mobile_ready(text.encode()))
        text = 'Denial/Volition output scheduler audit \x1b[3mpresentations\x1b[0m=2 ready_with_fence=2'
        self.assertTrue(GUEST.mobile_ready(text.encode()))

    def test_shell_requires_xwayland_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'usr/bin').mkdir(parents=True)
            for name in ('bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout',
                         'modetest', 'seatd', 'seatd-launch', 'sleep', 'dbus-daemon'):
                (root/'usr/bin'/name).touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), ['usr/bin/Xwayland'])
            self.assertEqual(GUEST.missing_runtime_inputs(root, False), [])
            (root/'usr/bin/Xwayland').touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), [])
            (root/'usr/bin/modetest').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), ['usr/bin/modetest'])

    def test_mobile_requires_udev_tools_and_input_identification_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'usr/bin').mkdir(parents=True)
            for name in ('bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout',
                         'modetest', 'seatd', 'sleep', 'Xwayland', 'dbus-daemon'):
                (root / 'usr/bin' / name).touch()
            mandatory = ['usr/bin/udevadm', 'usr/lib/systemd/systemd-udevd',
                         'usr/lib/udev/rules.d/60-input-id.rules']
            self.assertEqual(GUEST.missing_runtime_inputs(root, True), [])
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=False), [])
            self.assertCountEqual(GUEST.missing_runtime_inputs(root, True, mobile=True),
                                  mandatory)
            for relative in mandatory:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True), [])
            for relative in mandatory:
                with self.subTest(missing=relative):
                    path = root / relative
                    path.unlink()
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True),
                                     [relative])
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=False), [])
                    path.touch()
            (root / 'usr/bin/Xwayland').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True),
                             ['usr/bin/Xwayland'])

    def test_native_editor_requires_mousepad_without_changing_default_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            required = ('usr/bin/' + name for name in (
                'bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout', 'modetest',
                'seatd', 'sleep', 'Xwayland', 'dbus-daemon', 'udevadm'))
            for relative in (*required, 'usr/lib/systemd/systemd-udevd',
                             'usr/lib/udev/rules.d/60-input-id.rules'):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            cache_inputs = [
                'usr/bin/'+name for name in ('mkfifo', 'sed', 'cp', 'sha256sum',
                                             'glib-compile-schemas', 'update-mime-database')]
            cache_inputs += ['usr/share/glib-2.0/schemas/org.xfce.mousepad.gschema.xml',
                             'usr/share/mime/packages/freedesktop.org.xml']
            for relative in cache_inputs:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            for mobile in (False, True):
                with self.subTest(mobile=mobile):
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=mobile), [])
                    self.assertEqual(GUEST.missing_runtime_inputs(
                        root, True, mobile=mobile, editor=False), [])
                    self.assertEqual(GUEST.missing_runtime_inputs(
                        root, True, mobile=mobile, editor=True), ['usr/bin/mousepad'])
            editor = root / 'usr/bin/mousepad'
            editor.mkdir()
            self.assertEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), ['usr/bin/mousepad'])
            editor.rmdir()
            editor.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), [])
            for relative in cache_inputs:
                path = root / relative
                path.unlink()
                self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True, editor=True), [relative])
                self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True), [])
                path.touch()

            (root / 'usr/bin/Xwayland').unlink()
            self.assertEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), ['usr/bin/Xwayland'])
            editor.unlink()
            self.assertCountEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, editor=True), ['usr/bin/Xwayland', 'usr/bin/mousepad'])
            self.assertEqual(GUEST.missing_runtime_inputs(root, False), [])

    def test_focus_trace_guest_opt_in_is_explicit_and_validated(self):
        guest = (Path(__file__).resolve().parents[2]/'tools/qemu-virtio-drm/guest.sh').read_text()
        setup = guest[guest.index('unset DENIA_FOCUS_TRACE'):guest.index('# End focus trace setup.')]
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td)/'focus-trace'
            program = setup.replace('/run/focus-trace', str(marker)) + '\nprintf "%s" "${DENIA_FOCUS_TRACE-unset}"'
            for contents, expected, code in [(None, 'unset', 0), ('1\n', '1', 0), ('wrong\n', '', 1)]:
                if contents is None:
                    marker.unlink(missing_ok=True)
                else:
                    marker.write_text(contents)
                run = subprocess.run(['bash', '-c', program], env=dict(os.environ, DENIA_FOCUS_TRACE='1'), capture_output=True, text=True, timeout=5)
                self.assertEqual(run.returncode, code)
                if code == 0:
                    self.assertEqual(run.stdout.splitlines()[-1], expected)
                else:
                    self.assertIn('invalid focus trace marker', run.stderr)

    def test_focus_trace_requires_app_observation_before_io(self):
        run = subprocess.run(['python3', str(Path(__file__).with_name('test-qemu-virtio-drm.py')),
            '--trace-focus', '--runtime', '/not-used', '--kernel', '/not-used',
            '--deniald', '/not-used', '--image', 'not-used', '--output', '/not-used'],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(run.returncode, 2)
        self.assertIn('focus tracing requires --observe-mobile-apps', run.stderr)

    def test_launcher_requires_both_apps_desktops_and_cache_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = GUEST.missing_runtime_inputs(root, True, mobile=True, editor=True)
            additional = ['usr/bin/foot', 'usr/bin/awk', 'usr/bin/env',
                          'usr/share/applications/foot.desktop',
                          'usr/share/applications/org.xfce.mousepad.desktop']
            self.assertCountEqual(GUEST.missing_runtime_inputs(
                root, True, mobile=True, launcher=True), baseline+additional)
            for relative in baseline+additional:
                path = root/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True, launcher=True), [])
            for relative in baseline+additional:
                path = root/relative
                path.unlink()
                self.assertEqual(GUEST.missing_runtime_inputs(
                    root, True, mobile=True, launcher=True), [relative])
                if relative in additional:
                    self.assertEqual(GUEST.missing_runtime_inputs(root, True, mobile=True, editor=True), [])
                path.touch()

    def test_launcher_discovery_requires_unique_cleanup_and_no_app_launch(self):
        prepare = 'PASS launcher desktop overrides prepared; apps NOT STARTED\n'
        cleanup = 'PASS launcher apps cleanup\n'
        good = prepare+cleanup
        result = GUEST.launcher_discovery_result(good)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['app_launch_and_switch'], 'NOT RUN')
        for bad in ('', prepare, cleanup, good+cleanup, prepare+good,
                    good+'OBSERVE launcher app=foot owner=12 start=34\n',
                    good+'FAIL launcher client log limit\n',
                    good.replace(cleanup, 'FOOT_WAYLAND '+cleanup)):
            self.assertEqual(GUEST.launcher_discovery_result(bad)['status'], 'FAIL', bad)

    def test_native_capture_requires_move_and_client_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout', 'modetest'):
                path = root/'usr/bin'/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, False), [])
            required = ['usr/bin/mv', 'usr/lib/libwayland-client.so.0']
            self.assertEqual(GUEST.missing_runtime_inputs(root, False, native=True), required)
            for relative in required:
                path = root/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(GUEST.missing_runtime_inputs(root, False, native=True), [])

    def test_actual_zero_frame_summary_is_failure(self):
        line = ('independently clocked Flutter KMS session complete '
                '\x1b[3mraster_frames\x1b[0m\x1b[2m=\x1b[0m0 '
                'output_page_flips=0 delivered_vsyncs=1\n'
                'PASS actual deniald shell bounded exit\n')
        result = GUEST.session_result(line)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['raster_frames'], 0)
        self.assertEqual(result['output_page_flips'], 0)

    def test_positive_counters_require_no_render_errors(self):
        line = ('independently clocked Flutter KMS session complete '
                'raster_frames=3 output_page_flips=2')
        self.assertEqual(GUEST.session_result(line)['status'], 'PASS')
        for error in ('required Flutter native fence export failed',
                      'Unhandled Exception', 'Could not create the embedder backing store',
                      'Could not make the context current to destroy Impeller surface resources.',
                      'Could not clear the context after Impeller surface cleanup.',
                      'Could not clear the Impeller IO resource context.'):
            self.assertEqual(GUEST.session_result(line+'\n'+error)['status'], 'FAIL')

    def test_missing_duplicate_and_incomplete_counters_fail(self):
        line = ('independently clocked Flutter KMS session complete '
                'raster_frames=3 output_page_flips=2')
        for log in ('', line+'\n'+line, line.replace('output_page_flips=2', ''),
                    line+' raster_frames=4'):
            self.assertEqual(GUEST.session_result(log)['status'], 'FAIL')

    def test_virgl_rejects_primary_block_regular_and_symlink_nodes(self):
        for path in ('/dev/dri/card0', '/dev/sda', '/tmp/renderD128'):
            with self.assertRaises(ValueError):
                GUEST.render_node_identity(Path(path))
        for mode, major, minor in ((stat.S_IFREG, 226, 128), (stat.S_IFLNK, 226, 128),
                                   (stat.S_IFCHR, 8, 128), (stat.S_IFCHR, 226, 0)):
            with patch.object(Path, 'lstat', return_value=SimpleNamespace(
                    st_mode=mode, st_rdev=os.makedev(major, minor))):
                with self.assertRaises(ValueError):
                    GUEST.render_node_identity(Path('/dev/dri/renderD128'))
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(
                st_mode=stat.S_IFCHR, st_rdev=os.makedev(226, 128))):
            self.assertEqual(GUEST.render_node_identity(Path('/dev/dri/renderD128'))['minor'], 128)


if __name__ == '__main__':
    unittest.main()
