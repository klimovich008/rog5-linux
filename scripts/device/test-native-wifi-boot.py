#!/usr/bin/env python3
"""Production-only USB independence; no real device, mount or network operations."""
import os
import importlib.util
import hashlib
import json
import gzip
from pathlib import Path
import subprocess
import tempfile
import unittest

R = Path(__file__).resolve().parents[2]


def function(source, name):
    start = source.index(name + '() {')
    return source[start:source.index('\n}', start) + 2]


class AutomaticWifi(unittest.TestCase):
    def test_pwrkey_result_publication_is_exact_and_no_replace(self):
        source = (R/'initramfs/native-wifi/load-pwrkey').read_text()
        publisher = function(source, 'record_result')
        for contract in (
            'fail module-load', 'fail input-zero',
            'fail platform-identity', 'record_result pwrkey-pass',
        ):
            self.assertIn(contract, source)
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp)/'pwrkey-result'
            publisher = publisher.replace(
                '/run/rog5-pwrkey-result', str(result)
            )
            script = (
                'set -eu\nresult_path=' + str(result) + '\n' + publisher +
                '\nrecord_result pwrkey-module-load'
            )
            subprocess.run(['sh', '-c', script], check=True)
            self.assertEqual(result.read_text(), 'pwrkey-module-load\n')
            self.assertEqual(result.stat().st_mode & 0o777, 0o444)
            duplicate = subprocess.run(['sh', '-c', script], capture_output=True)
            self.assertNotEqual(duplicate.returncode, 0)

    def test_optional_status_runtime_uses_sealed_applets_and_newroot(self):
        runtime = (R/'initramfs/native-wifi/runtime').read_text()
        body = function(runtime, 'install_status_screen')
        self.assertNotIn('\n\tinstall ', body)
        for command in (
            'mkdir -p', 'cp -p', 'chmod 0755', 'ln -s', 'stat -c', 'cmp'
        ):
            self.assertIn(command, body)
        self.assertIn('/newroot/usr/local/bin/rog5-screen-toggle.sh', body)
        self.assertIn('"$units/multi-user.target.wants"', body)
        self.assertIn('[ "$present" -eq 7 ]', body)
        self.assertIn('qcom-pon.ko', body)
        self.assertIn('load-pwrkey', body)
        self.assertIn('"$root/load-pwrkey" || return 1', body)
        self.assertIn('rog5-p2-ready.service.d/10-screen-off.conf', body)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root/'payload'
            units = root/'run/systemd/system'
            newroot = root/'newroot'
            (payload/'units').mkdir(parents=True)
            units.mkdir(parents=True)
            (units/'rog5-p2-ready.service').write_text('p2-ready')
            for name in (
                'screen-toggle.sh', 'status-screen.sh', 'power-buttond.py',
            ):
                path = payload/name
                path.write_text(name)
                path.chmod(0o755)
            load_log = root/'pwrkey-load.log'
            result = root/'pwrkey-result'
            loader = payload/'load-pwrkey'
            loader.write_text(
                '#!/bin/sh\nprintf loaded >"$PWRKEY_LOAD_LOG"\n'
                'printf "pwrkey-pass\\n" >"$ROG5_PWRKEY_RESULT"\n'
                'chmod 0444 "$ROG5_PWRKEY_RESULT"\n'
            )
            loader.chmod(0o755)
            (payload/'qcom-pon.ko').write_text('module')
            (payload/'qcom-pon.ko').chmod(0o644)
            for name in ('rog5-status-screen.service', 'rog5-power-button.service'):
                path = payload/'units'/name
                path.write_text(name)
                path.chmod(0o644)
            script = body.replace('/newroot', str(newroot)).replace(
                '/run/rog5-pwrkey-result', str(result)
            )
            command = (
                'set -eu\nroot=' + str(payload) + '\nunits=' + str(units) + '\n'
                'PWRKEY_LOAD_LOG=' + str(load_log) + '\nexport PWRKEY_LOAD_LOG\n'
                'stat() { case "$3" in *pwrkey-result) echo 0:0:444:1 ;; '
                '*.service|*.conf|*.ko) echo 0:0:644:1 ;; '
                '*) echo 0:0:755:1 ;; esac; }\n' + script +
                '\ninstall_status_screen "$units"'
            )
            subprocess.run(['sh', '-c', command], check=True)
            self.assertEqual(load_log.read_text(), 'loaded')
            self.assertEqual(result.read_text(), 'pwrkey-pass\n')
            self.assertEqual(
                (newroot/'usr/local/bin/rog5-screen-toggle.sh').read_text(),
                'screen-toggle.sh',
            )
            self.assertEqual(
                (newroot/'usr/local/libexec/rog5-status-screen').read_text(),
                'status-screen.sh',
            )
            self.assertTrue(
                (units/'multi-user.target.wants/rog5-status-screen.service').is_symlink()
            )
            self.assertEqual(
                (units/'rog5-p2-ready.service.d/10-screen-off.conf').read_text(),
                '[Service]\nExecStartPre=/usr/local/bin/rog5-screen-toggle.sh off\n',
            )

            (payload/'power-buttond.py').unlink()
            rejected = subprocess.run(['sh', '-c', command], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_optional_status_runtime_accepts_only_exact_persistent_files(self):
        runtime = (R/'initramfs/native-wifi/runtime').read_text()
        body = function(runtime, 'install_status_screen')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root/'payload'
            source_units = payload/'units'
            newroot = root/'newroot'
            persistent = {
                'screen-toggle.sh': newroot/'usr/local/bin/rog5-screen-toggle.sh',
                'status-screen.sh': newroot/'usr/local/libexec/rog5-status-screen',
                'power-buttond.py': newroot/'usr/local/libexec/rog5-power-buttond',
            }
            source_units.mkdir(parents=True)
            (payload/'load-pwrkey').write_text(
                '#!/bin/sh\nprintf "pwrkey-pass\\n" >"$ROG5_PWRKEY_RESULT"\n'
                'chmod 0444 "$ROG5_PWRKEY_RESULT"\n'
            )
            (payload/'load-pwrkey').chmod(0o755)
            (payload/'qcom-pon.ko').write_text('module')
            (payload/'qcom-pon.ko').chmod(0o644)
            for name, destination in persistent.items():
                source = payload/name
                source.write_text(name)
                source.chmod(0o755)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(name)
                destination.chmod(0o755)
            for name in ('rog5-status-screen.service', 'rog5-power-button.service'):
                path = source_units/name
                path.write_text(name)
                path.chmod(0o644)

            def run(units):
                units.mkdir(parents=True)
                (units/'rog5-p2-ready.service').write_text('p2-ready')
                result = units.parent/'pwrkey-result'
                script = body.replace('/newroot', str(newroot)).replace(
                    '/run/rog5-pwrkey-result', str(result)
                )
                command = (
                    'set -eu\nroot=' + str(payload) + '\nunits=' + str(units) + '\n'
                    'stat() { case "$3" in *pwrkey-result) echo 0:0:444:1 ;; '
                    '*.service|*.conf|*.ko) echo 0:0:644:1 ;; '
                    '*) echo 0:0:755:1 ;; esac; }\n' + script +
                    '\ninstall_status_screen "$units"'
                )
                return subprocess.run(['sh', '-c', command], capture_output=True)

            accepted = run(root/'run-one/systemd')
            self.assertEqual(accepted.returncode, 0, accepted.stderr.decode())
            self.assertTrue(
                (root/'run-one/systemd/multi-user.target.wants/'
                 'rog5-status-screen.service').is_symlink()
            )

            persistent['status-screen.sh'].write_text('changed')
            rejected = run(root/'run-two/systemd')
            self.assertNotEqual(rejected.returncode, 0)

    def test_display_diagnostic_keeps_rollback_and_skips_wifi_units(self):
        runtime = (R/'initramfs/native-wifi/runtime').read_text()
        body = function(runtime, 'install_units')
        self.assertIn('rog5-display-diagnostic-v1', body)
        self.assertIn('[ "$display_diagnostic" -eq 0 ]', body)
        self.assertIn("'unmanaged-devices=interface-name:usb0'", body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root/'payload'
            source_units = payload/'units'
            units = root/'run/systemd/system'
            nm = root/'run/NetworkManager/conf.d'
            source_units.mkdir(parents=True)
            (units/'sysinit.target.wants').mkdir(parents=True)
            nm.mkdir(parents=True)
            for name in (
                'rog5-wifi-failure.service',
                'rog5-wifi-boot-rollback.service',
                'rog5-wifi-boot-rollback.timer',
                'before-ssh.conf',
            ):
                (source_units/name).write_text(name)
            marker = payload/'display-diagnostic'
            marker.write_text('rog5-display-diagnostic-v1\n')
            marker.chmod(0o444)
            script = body.replace('/run/systemd/system', str(units)).replace(
                '/run/NetworkManager/conf.d', str(nm)
            )
            command = (
                'set -eu\nroot=' + str(payload) + '\n'
                'install_status_screen() { :; }\n'
                'stat() { case "${3:-}" in '
                '*/display-post-switch-report) echo 0:0:755:1 ;; '
                '*.service) echo 0:0:644:1 ;; '
                '*) echo 0:0:444:1 ;; esac; }\n' + script + '\ninstall_units'
            )
            subprocess.run(['sh', '-c', command], check=True)
            self.assertTrue(
                (units/'sysinit.target.wants/rog5-wifi-boot-rollback.timer').is_symlink()
            )
            self.assertFalse((units/'rog5-wifi-radio.service').exists())
            self.assertFalse((units/'rog5-persistent-state.service.d').exists())
            self.assertFalse(
                (units/'sysinit.target.wants/'
                 'rog5-display-post-switch.service').exists()
            )
            self.assertEqual(
                (nm/'10-rog5-p2.conf').read_text(),
                '[keyfile]\nunmanaged-devices=interface-name:usb0\n',
            )

            marker.chmod(0o644)
            marker.write_text('wrong\n')
            marker.chmod(0o444)
            rejected = subprocess.run(['sh', '-c', command], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_display_observer_timeout_is_nested_inside_rollback(self):
        timing = dict(
            line.split('=', 1)
            for line in (R/'initramfs/native-wifi/timing').read_text().splitlines()
            if line and not line.startswith('#')
        )
        self.assertLessEqual(int(timing['display_report_seconds']), 90)
        self.assertGreaterEqual(
            int(timing['host_parent_seconds']),
            int(timing['outer_seconds']) + int(timing['cleanup_seconds']) + 30,
        )

    def test_display_observer_runs_before_switch_root_and_persistent_state(self):
        init = (R/'initramfs/persistent-root-init').read_text()
        function_body = function(init, 'run_pre_switch_display_observer')
        self.assertIn('ROG5_OBSERVER_TARGET_ROOT=/newroot', function_body)
        self.assertIn('"$reporter" send', function_body)
        self.assertIn('/bin/busybox reboot -f', function_body)
        self.assertNotIn('/dev/sda', function_body)
        final_storage = init.index('publish_or_rollback final-storage PASS')
        observer = init.index('\nrun_pre_switch_display_observer\n', final_storage)
        switch_root = init.index('publish_or_rollback switch-root ENTER', observer)
        self.assertLess(final_storage, observer)
        self.assertLess(observer, switch_root)

    def test_persistent_trial_selector_and_healthy_commit_are_exact(self):
        spec = importlib.util.spec_from_file_location(
            'wifi_archive', R/'scripts/device/build-native-wifi-boot-initramfs.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        valid = (
            'format=rog5-persistent-wifi-health-v1\n'
            'trial_id=' + '1'*64 + '\n'
            'primary_bundle=persistent-native-root-wifi\n'
            'mode=try-once\n').encode()
        parsed = module.parse_trial_descriptor(valid)
        self.assertEqual(parsed['primary_bundle'], 'persistent-native-root-wifi')
        for bad in (
            valid.replace(b'mode=try-once', b'mode=always'),
            valid.replace(b'trial_id=' + b'1'*64, b'trial_id=' + b'A'*64),
            valid.replace(b'primary_bundle=', b'fallback_bundle=', 1),
        ):
            with self.assertRaises(AssertionError):
                module.parse_trial_descriptor(bad)

        runtime = (R/'initramfs/native-wifi/runtime').read_text()
        self.assertIn('if [ -e "$root/trial-descriptor" ]', runtime)
        self.assertIn('multi-user.target.wants/rog5-wifi-healthy.service', runtime)
        unit = (R/'initramfs/native-wifi-persistent/units/rog5-wifi-healthy.service').read_text()
        for dependency in ('rog5-wifi-dhcp.service', 'rog5-persistent-state.service',
                           'rog5-early-sshd.service', 'rog5-tailscaled.service'):
            self.assertIn(dependency, unit)
        self.assertIn('TimeoutStartSec=180s', unit)
        self.assertIn('Restart=no', unit)
        healthy = (R/'initramfs/native-wifi-persistent/healthy').read_text()
        self.assertIn('helper=$root/trial-state', healthy)
        self.assertIn('record=$root/healthy.record', healthy)
        self.assertNotIn('record=$root/healthy\n', healthy)
        commit = healthy.index('"$helper" healthy')
        stop = healthy.index(
            'systemctl --job-mode=ignore-dependencies stop "$rollback_timer"'
        )
        record = healthy.index("printf 'format=rog5-native-wifi-healthy-v1")
        self.assertLess(commit, stop)
        self.assertLess(stop, record)
        self.assertIn('rog5-wifi-probe-rollback.timer', healthy)
        self.assertIn('rog5-wifi-boot-rollback.timer', healthy)
        for guard in ('primary bundle is not running', 'healthy startup deadline',
                      '117:2', '/sys/class/block/sda/sda24/ro',
                      'qcom-battmgr-usb/online'):
            self.assertIn(guard, healthy)

    def test_persistent_composer_changes_only_trial_members(self):
        spec = importlib.util.spec_from_file_location(
            'persistent_wifi', R/'scripts/device/build-native-wifi-persistent-trial-initramfs.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        archive = module.ARCHIVE
        members = {}
        archive.add(members, 'init', b'qualified-init', 0o100755)
        archive.add(members, 'rog5-native-wifi/automatic',
                    b'rog5-native-wifi-boot-v1\n', 0o100444)
        archive.add(members, 'rog5-native-wifi/runtime', b'old-runtime', 0o100755)
        archive.add(members, 'rog5-native-wifi/radio', b'old-radio', 0o100755)
        archive.add(members, 'rog5-native-wifi/probe-native-wifi.sh', b'old-probe', 0o100755)
        archive.add(members, 'rog5-native-wifi/boot-files.sha256',
                    b'old-checks\n', 0o100444)
        archive.add(
            members,
            'rog5-native-wifi/units/rog5-wifi-radio.service',
            b'[Service]\nTimeoutStartSec=@OUTER_SECONDS@s\n',
            0o100644,
        )
        base = gzip.compress(archive.encode(members), mtime=0)
        descriptor = (
            'format=rog5-persistent-wifi-health-v1\n'
            'trial_id=' + '1'*64 + '\n'
            'primary_bundle=persistent-native-root-wifi\n'
            'mode=try-once\n').encode()
        helper = (R/'artifacts/persistent-trial-state-v1/rog5-persistent-trial-state').read_bytes()
        packed, result = module.compose(base, module.sha(base), descriptor, helper)
        output = archive.entries(gzip.decompress(packed))
        self.assertEqual(output['init'], members['init'])
        self.assertEqual(output['rog5-native-wifi/trial-descriptor'][1], descriptor)
        self.assertEqual(output['rog5-native-wifi/trial-state'][1], helper)
        self.assertNotIn(
            b'@OUTER_SECONDS@',
            output['rog5-native-wifi/units/rog5-wifi-radio.service'][1],
        )
        self.assertIn('rog5-native-wifi/healthy', output)
        self.assertIn('rog5-native-wifi/units/rog5-wifi-healthy.service', output)
        self.assertEqual(set(output)-set(members), {
            'rog5-native-wifi/trial-state',
            'rog5-native-wifi/trial-descriptor', 'rog5-native-wifi/healthy',
            'rog5-native-wifi/units/rog5-wifi-healthy.service',
        })
        self.assertEqual(result['added_members'], 4)
        checks = output['rog5-native-wifi/boot-files.sha256'][1].decode()
        self.assertIn('  healthy\n', checks)
        self.assertIn('  trial-descriptor\n', checks)

        successor_descriptor = (
            'format=rog5-persistent-wifi-health-v1\n'
            'trial_id=' + '2'*64 + '\n'
            'primary_bundle=persistent-native-root-wifi-overlay-v1\n'
            'mode=try-once\n').encode()
        successor, successor_result = module.compose_successor(
            packed, module.sha(packed), successor_descriptor, helper)
        successor_members = archive.entries(gzip.decompress(successor))
        self.assertEqual(
            successor_members['rog5-native-wifi/trial-descriptor'][1],
            successor_descriptor,
        )
        self.assertEqual(successor_result['added_members'], 0)
        self.assertEqual(successor_result['changed_existing_members'], [
            'rog5-native-wifi/boot-files.sha256',
            'rog5-native-wifi/probe-native-wifi.sh',
            'rog5-native-wifi/radio',
            'rog5-native-wifi/trial-descriptor',
        ])
        for name, value in output.items():
            if name not in successor_result['changed_existing_members']:
                self.assertEqual(successor_members[name], value)
        successor_checks = successor_members[
            'rog5-native-wifi/boot-files.sha256'
        ][1].decode()
        self.assertIn(
            hashlib.sha256(successor_descriptor).hexdigest()
            + '  trial-descriptor\n',
            successor_checks,
        )

    def test_failure_diagnostic_composer_changes_only_reporter_members(self):
        spec = importlib.util.spec_from_file_location(
            'failure_wifi', R/'scripts/device/build-native-wifi-failure-diagnostic-initramfs.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        archive = module.ARCHIVE
        members = {}
        archive.add(members, 'init', b'qualified-init', 0o100755)
        for name, data, mode in (
            ('runtime', b'old-runtime', 0o100755),
            ('radio', b'old-radio', 0o100755),
            ('units/rog5-wifi-radio.service', b'old-unit', 0o100644),
            ('boot-files.sha256', b'old-checks\n', 0o100444),
        ):
            archive.add(members, 'rog5-native-wifi/'+name, data, mode)
        base = gzip.compress(archive.encode(members), mtime=0)
        packed, result = module.compose(base, module.sha(base))
        output = archive.entries(gzip.decompress(packed))
        self.assertEqual(output['init'], members['init'])
        self.assertEqual(set(output)-set(members), {
            'rog5-native-wifi/failure',
            'rog5-native-wifi/units/rog5-wifi-failure.service',
        })
        self.assertEqual(result['added_members'], [
            'rog5-native-wifi/failure',
            'rog5-native-wifi/units/rog5-wifi-failure.service',
        ])
        checks = output['rog5-native-wifi/boot-files.sha256'][1].decode()
        self.assertIn('  failure\n', checks)
        self.assertIn('  units/rog5-wifi-failure.service\n', checks)

    def test_watchdog_can_fire_before_basic_or_failed_p2(self):
        fixture = json.loads((R/'tests/fixtures/native-wifi/timer-default-dependencies.json').read_text())
        self.assertIn('basic.target', fixture['original_service_after'])
        self.assertNotIn('basic.target', fixture['fixed_service_after'])
        self.assertEqual(fixture['fixed_timer_after'], [])
        units = R/'initramfs/native-wifi/units'
        for name in ('rog5-wifi-boot-rollback.service', 'rog5-wifi-boot-rollback.timer',
                     'rog5-wifi-radio.service', 'rog5-wifi-wpa.service'):
            source = (units/name).read_text()
            self.assertIn('DefaultDependencies=no', source)
            self.assertIn('Conflicts=shutdown.target', source)
            self.assertIn('Before=shutdown.target', source)
        early = (units/'before-ssh.conf').read_text()
        self.assertIn('Requires=rog5-wifi-boot-rollback.timer', early)
        self.assertIn('After=rog5-wifi-boot-rollback.timer', early)
        rollback = (units/'rog5-wifi-boot-rollback.timer').read_text()
        self.assertNotIn('After=rog5-p2', rollback)
        self.assertIn('OnBootSec=@OUTER_SECONDS@s', rollback)
        probe = (R/'scripts/device/probe-native-wifi.sh').read_text()
        self.assertIn('--property=DefaultDependencies=no', probe)
        self.assertIn('--timer-property=DefaultDependencies=no', probe)

    def test_power_loader_never_turns_carrier_into_a_charging_requirement(self):
        source = (R/'scripts/device/load-persistent-root-power-usb.sh').read_text()
        body = function(source, 'require_ncm_carrier')
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'automatic'
            script = body.replace('/run/rog5-native-wifi/automatic', str(marker))
            for content, expected in [(None, 1), ('bad\n', 1), ('rog5-native-wifi-boot-v1\n', 0)]:
                if content is not None:
                    marker.write_text(content)
                result = subprocess.run(['sh', '-c', 'set -eu\n'
                    + 'stat() { echo 0:0:444:25:1; }; fail() { exit 1; };\n'
                    + script + '\nrequire_ncm_carrier'], capture_output=True)
                self.assertEqual(result.returncode, expected)
        # Missing carrier is bypassed, never power/route/role/storage checks.
        for check in ('wait_for_usb_online\n', 'power_role_is_sink "$power_role"',
                      "fail ncm-route 'NCM route changed'", "fail storage-before-ufs"):
            self.assertIn(check, source)

    def test_foreground_network_commands_do_not_reintroduce_fatal_optional_flags(self):
        source = (R/'initramfs/native-wifi/runtime').read_text()
        for function_name, expected in [('run_wpa', '-Dnl80211 -i wlp1s0 -c'),
                                        ('run_dhcp', '-4 -B -L -m 100')]:
            body = function(source, function_name).replace('\n\texec ', '\n\tprintf \'%s\\n\' ')
            result = subprocess.run(['sh', '-c', 'set -eu\nroot=/payload; state=/private; '
                + 'interface_identity() { interface=wlp1s0; }; fail() { exit 1; };\n'
                + body + '\n' + function_name], capture_output=True, text=True, check=True)
            command = result.stdout.splitlines()
            self.assertIn(expected, ' '.join(command))
            if function_name == 'run_wpa':
                for forbidden in ('-f', '-B', '-P', '-K'):
                    self.assertNotIn(forbidden, command)
                self.assertNotIn('password', result.stdout)
            else:
                self.assertEqual(command[-1], 'wlp1s0')
                self.assertNotIn('-1', command)  # must maintain/reacquire lease

    def test_radio_precedes_writable_state_and_cannot_restart(self):
        units = R/'initramfs/native-wifi/units'
        radio = (units/'rog5-wifi-radio.service').read_text()
        self.assertIn('Before=rog5-persistent-state.service basic.target', radio)
        self.assertIn('OnFailure=rog5-wifi-failure.service', radio)
        self.assertNotIn('OnFailure=reboot.target', radio)
        self.assertIn('Restart=no', radio)
        self.assertIn('Requires=rog5-wifi-radio.service', (units/'before-state.conf').read_text())
        runtime = (R/'initramfs/native-wifi/runtime').read_text()
        self.assertIn('rog5-wifi-dhcp) target=multi-user.target', runtime)
        self.assertNotIn('Before=basic.target', (units/'rog5-wifi-dhcp.service').read_text())
        self.assertIn('systemd-resolved.service', (units/'rog5-wifi-dhcp.service').read_text())
        script = (R/'initramfs/native-wifi/radio').read_text()
        self.assertLess(script.index('rollback.timer'), script.index('for action in query mode held-oem'))
        self.assertIn('mkdir "$root/radio-entered"', script)
        self.assertIn('no', radio)
        self.assertIn('guard\n', script)
        self.assertIn('timeout -k "$kill_seconds" "$limit" "$root/module-once"', script)
        self.assertNotIn('insmod', script)
        self.assertIn('$((outer_seconds - radio_seconds - cleanup_seconds))', script)
        fixture = (
            R/'tests/fixtures/persistent-root/overlay-v2-radio-failure.log'
        ).read_text()
        self.assertIn('rog5-p2-attest: PASS', fixture)
        self.assertIn('FAIL native-wifi-radio: writable UFS', fixture)
        for contract in (
            'overlay_record=/run/rog5-persistent-overlay.runtime',
            'resolve_storage_mode() {',
            'format=rog5-persistent-root-overlay-runtime-v1',
            'rog5/root/root-overlay-v1.ext4',
            '[ "$writable" = 2 ]',
            'fail \'overlay write scope\'',
        ):
            self.assertIn(contract, script)
        probe = (R/'scripts/device/probe-native-wifi.sh').read_text()
        probe_fixture = (
            R/'tests/fixtures/persistent-root/overlay-v3-probe-failure.log'
        ).read_text()
        self.assertIn('rog5-p2-attest: PASS', probe_fixture)
        self.assertIn('WIFI_PROBE_ABORT writable-UFS', probe_fixture)
        for contract in (
            'overlay_record=/run/rog5-persistent-overlay.runtime',
            'resolve_storage_mode() {',
            'format=rog5-persistent-root-overlay-runtime-v1',
            '[ "$writable" = 2 ]',
            "fail 'overlay-write-scope'",
        ):
            self.assertIn(contract, probe)
        timing = (R/'initramfs/native-wifi/timing').read_text()
        result = subprocess.run(['sh', '-c', 'set -eu\n'+timing+
            '\n[ "$outer_seconds" -gt "$((radio_seconds + cleanup_seconds))" ]\n'
            '[ "$((query_seconds + mode_seconds + hold_seconds + 3*kill_seconds))" -lt "$outer_seconds" ]'], check=True)

    def test_radio_failure_is_bounded_and_reported_before_reboot(self):
        radio = (R/'initramfs/native-wifi/radio').read_text()
        body = function(radio, 'fail')
        with tempfile.TemporaryDirectory() as tmp:
            script = body.replace('root=/run/rog5-native-wifi', 'root=' + tmp)
            result = subprocess.run(
                ['sh', '-c', 'set -u\nroot=' + tmp + '\n' + script +
                 '\nfail "hold not qualified"'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual((Path(tmp)/'radio-failure').read_text(),
                             'hold_not_qualified\n')
            self.assertEqual((Path(tmp)/'radio-failure').stat().st_mode & 0o777, 0o444)
        unit = (R/'initramfs/native-wifi/units/rog5-wifi-failure.service').read_text()
        self.assertIn('DefaultDependencies=no', unit)
        self.assertIn('TimeoutStartSec=5s', unit)
        self.assertIn('Restart=no', unit)
        failure = (R/'initramfs/native-wifi/failure').read_text()
        self.assertLess(failure.index('ROG5_WIFI_FAILURE'),
                        failure.index('systemctl --no-block reboot'))
        self.assertIn("timeout -k 1 1 sh -c", failure)
        self.assertIn('stat -c', failure)

    def test_radio_failure_diagnostic_is_signed_bounded_and_does_not_reboot(self):
        failure = (R/'initramfs/native-wifi/failure').read_text()
        self.assertIn('failure-ncm-diagnostic', failure)
        self.assertIn('rog5-wifi-failure-ncm-v1', failure)
        self.assertIn('busybox=/run/initramfs/bin/busybox', failure)
        self.assertIn(
            'busybox_loader=/run/initramfs/lib/ld-musl-aarch64.so.1', failure
        )
        self.assertIn(
            '"$busybox_loader" "$busybox" nc -n -w 2',
            failure,
        )
        self.assertIn('169.254.77.1 8084 <"$record"', failure)
        self.assertIn('[ "$attempt" -lt 2 ]', failure)
        diagnostic = failure.index('if [ "$failure_ncm_diagnostic" -eq 1 ]; then')
        diagnostic_exit = failure.index('\texit 0', diagnostic)
        reboot = failure.index('systemctl --no-block reboot')
        self.assertLess(diagnostic, diagnostic_exit)
        self.assertLess(diagnostic_exit, reboot)

    def test_newc_preserves_existing_entries_and_rejects_unsafe_input(self):
        spec = importlib.util.spec_from_file_location('wifi_archive', R/'scripts/device/build-native-wifi-boot-initramfs.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        members = {}
        module.add(members, 'lib/module.ko', b'ELF-unchanged', 0o100644)
        module.add(members, 'init', b'#!/bin/sh\n', 0o100755)
        module.add(members, 'bin/sh', b'busybox', 0o120777)
        old_module = members['lib/module.ko']
        module.replace(members, 'init', b'#!/bin/sh\necho test\n')
        module.add(members, 'new/regular', b'local-data', 0o100444)
        self.assertEqual(module.entries(module.encode(members)), members)
        self.assertEqual(list(module.entries(module.encode(members))), sorted(members))
        self.assertEqual(members['lib/module.ko'], old_module)
        for name in ('init', '../escape', '/absolute', 'bin/sh/child'):
            with self.assertRaises(AssertionError):
                module.add(members, name, b'bad', 0o100644)
        with self.assertRaises(AssertionError):
            module.compose(b'bad', b'bad', {'files': {'initramfs.cpio.gz': '0'*64}})
        # Execute the real release verifier's newc parser, not just our encoder.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); harness = root/'parser.c'; verifier = root/'parser'
            harness.write_text('#define main full_verifier_main\n#include "'+str(R/'tools/recovery_control/rog5-bundle-verify.c')+'"\n'
                '#undef main\nint main(int argc, char **argv) { if (argc != 2) return 2; '
                'int fd = open(argv[1], O_RDONLY | O_NOFOLLOW); if (fd < 0) return 2; '
                'verify_initramfs_gzip(fd, false, false, false); close(fd); return 0; }\n')
            subprocess.run(['gcc','-O2','-Wall','-Wextra','-Werror',str(harness),'-lcrypto','-lz','-o',str(verifier)], check=True)
            raw = module.encode(members)
            good = root/'good.gz'; good.write_bytes(gzip.compress(raw, mtime=0))
            subprocess.run([str(verifier),str(good)],check=True)
            bad = root/'bad.gz'; bad.write_bytes(gzip.compress(raw.replace(b'bin\0', b'zzz\0', 1), mtime=0))
            rejected = subprocess.run([str(verifier),str(bad)],capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(b'not unique and sorted', rejected.stderr)

    def test_rendezvous_never_waits_for_usb_in_sealed_native_mode(self):
        source = (R / 'initramfs/persistent-root-init').read_text()
        body = function(source, 'wait_for_deferred_ufs_rendezvous')
        for native, expected in [('1', 0), ('0', 1)]:
            result = subprocess.run(['sh', '-c', 'set -eu\nnative_wifi_boot=' + native + '\n'
                + 'cat() { echo 0; }; sleep() { :; };\n' + body
                + '\nwait_for_deferred_ufs_rendezvous'], capture_output=True)
            self.assertEqual(result.returncode, expected)

    def test_only_sealed_readonly_native_mode_can_enable_usb_independence(self):
        source = (R / 'initramfs/persistent-root-init').read_text()
        body = function(source, 'prepare_native_wifi_boot')
        for native, storage, diag, content, expected in [
            ('1', 'read-only', '0', 'rog5-native-wifi-boot-v1\n', 0),
            ('0', 'read-only', '0', 'rog5-native-wifi-boot-v1\n', 1),
            ('1', 'local-write', '0', 'rog5-native-wifi-boot-v1\n', 1),
            ('1', 'read-only', '1', 'rog5-native-wifi-boot-v1\n', 1),
            ('1', 'read-only', '0', 'bad\n', 1),
        ]:
            with self.subTest(native=native, storage=storage, diag=diag, content=content):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp); payload = root/'payload'; payload.mkdir()
                    (payload/'automatic').write_text(content); (payload/'automatic').chmod(0o444)
                    script = body.replace('/rog5-native-wifi', str(payload)).replace(
                        '/run' + str(payload), str(root/'run'))
                    result = subprocess.run(['sh', '-c', 'set -eu\n'
                        + f'expected_native_root_mode={native}\nexpected_ufs_storage_mode={storage}\n'
                        + f'expected_ssh_diagnostic_mode={diag}\nnative_wifi_boot=0\n'
                        + 'stat() { echo 0:0:444:25:1; };\n' + script
                        + '\nprepare_native_wifi_boot'], capture_output=True)
                    self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == '__main__':
    unittest.main()
