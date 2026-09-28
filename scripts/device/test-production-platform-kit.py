#!/usr/bin/env python3
"""Tests for the production platform kit: boot modules, RTC time and publishing.

The scripts run against temporary sysfs, state and module trees; modprobe and
date are stubs that log their calls. The init function runs under
`unshare -r`, so the temporary kit is owned by uid 0 as in the ramdisk.
Set ROG5_TEST_BUSYBOX/ROG5_TEST_QEMU to run the init function under the
target ARM64 busybox.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
MODULES = REPO/'initramfs/production-platform-modules'
RTC = REPO/'initramfs/production-rtc-time'
INIT = REPO/'initramfs/persistent-root-init'
LIST = REPO/'configs/production/boot-modules.list'
AUDIO_LIST = REPO/'configs/production/audio-modules.list'
SENSOR_LIST = REPO/'configs/production/sensor-modules.list'
AUDIO = ['apr', 'q6core', 'q6afe_dai', 'q6afe_clocks', 'q6asm_dai', 'q6routing', 'pinctrl_sc7280_lpass_lpi',
         'snd_soc_cs35l45_i2c', 'snd_soc_sm8250']
UNITS = ('rog5-platform-modules.service', 'rog5-rtc-time.service', 'rog5-rtc-time-save.service',
         'rog5-rtc-time-save.path', 'rog5-audio.service', 'rog5-sensors.service')
NOW = 1790200000  # 2026-09-23
RAW = 1234567


def unshare_ok():
    return subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-platform-'))
        self.bin = self.dir/'bin'
        self.bin.mkdir()

    def tearDown(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.dir)])
        shutil.rmtree(self.dir)

    def stub(self, name, body):
        (self.bin/name).write_text(f'#!/bin/sh\nD={self.dir}\n{body}\n')
        (self.bin/name).chmod(0o755)

    def run_script(self, script, *args, **env):
        environment = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', **env)
        result = subprocess.run(['sh', str(script), *args], capture_output=True, text=True, env=environment, timeout=30)
        kmsg = self.dir/'kmsg'
        return result.returncode, kmsg.read_text() if kmsg.exists() else ''

    def calls(self):
        path = self.dir/'calls'
        return path.read_text().splitlines() if path.exists() else []


class BootModules(Base):
    def setUp(self):
        super().setUp()
        self.kit = self.dir/'kit'
        self.kit.mkdir()
        shutil.copy(LIST, self.kit/'boot-modules')
        release = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip()
        (self.dir/'tree/lib/modules'/release).mkdir(parents=True)
        self.stub('modprobe', 'echo "modprobe $*" >>$D/calls; [ ! -e "$D/fail-$3" ]')

    def load(self, *args):
        (self.dir/'ignore_loglevel').write_text('Y\n')
        (self.dir/'shmem_enabled').write_text('never\n')
        return self.run_script(MODULES, *args, ROG5_PLATFORM_KIT=str(self.kit), ROG5_PLATFORM_MODULES=str(self.dir/'tree'),
                               ROG5_PLATFORM_KMSG=str(self.dir/'kmsg'),
                               ROG5_PLATFORM_PRINTK=str(self.dir/'ignore_loglevel'),
                               ROG5_PLATFORM_SHMEM_THP=str(self.dir/'shmem_enabled'))

    def test_console_logging_is_quieted_first(self):
        code, kmsg = self.load()
        self.assertEqual(code, 0, kmsg)
        self.assertEqual((self.dir/'ignore_loglevel').read_text(), 'N\n')
        self.assertEqual((self.dir/'shmem_enabled').read_text(), 'within_size\n')

    def test_the_listed_modules_load_in_order_with_parameters(self):
        code, kmsg = self.load()
        self.assertEqual(code, 0, kmsg)
        tree = self.dir/'tree'
        self.assertEqual(self.calls(), [f'modprobe -d {tree} rtc_pm8xxx', f'modprobe -d {tree} softdog soft_panic=1', f'modprobe -d {tree} rog5_gmu_bind',
                                        f'modprobe -d {tree} drm_client_lib active=', f'modprobe -d {tree} phy_qcom_qmp_combo', f'modprobe -d {tree} gpio_sbu_mux',
                                        f'modprobe -d {tree} aux_bridge', f'modprobe -d {tree} aux_hpd_bridge', f'modprobe -d {tree} pmic_glink_altmode',
                                        f'modprobe -d {tree} msm separate_gpu_kms=1', f'modprobe -d {tree} panel_asus_rog5_ams678',
                                        f'modprobe -d {tree} gpi', f'modprobe -d {tree} rog5_fts3658u', f'modprobe -d {tree} rog5_aw8697',
                                        f'modprobe -d {tree} rog5_vcnl36866', f'modprobe -d {tree} rog5_aura', f'modprobe -d {tree} leds_qcom_flash',
                                        f'modprobe -d {tree} qcom_pon', f'modprobe -d {tree} qcom_spmi_adc5', f'modprobe -d {tree} qcom_spmi_adc_tm5', f'modprobe -d {tree} icc_bwmon', f'modprobe -d {tree} rog5_input_boost',
                                        f'modprobe -d {tree} qcom_stats'])
        self.assertIn('loaded rtc_pm8xxx softdog rog5_gmu_bind drm_client_lib phy_qcom_qmp_combo gpio_sbu_mux aux_bridge aux_hpd_bridge pmic_glink_altmode msm panel_asus_rog5_ams678 gpi rog5_fts3658u rog5_aw8697 rog5_vcnl36866 rog5_aura leds_qcom_flash qcom_pon qcom_spmi_adc5 qcom_spmi_adc_tm5 icc_bwmon rog5_input_boost qcom_stats', kmsg)

    def test_one_failure_still_loads_the_rest_and_fails_the_unit(self):
        (self.dir/'fail-rtc_pm8xxx').touch()
        code, kmsg = self.load()
        self.assertEqual(code, 1)
        self.assertIn('FAIL modprobe rtc_pm8xxx', kmsg)
        self.assertEqual(len(self.calls()), 23)

    def test_audio_list_loads_without_boot_settings(self):
        shutil.copy(AUDIO_LIST, self.kit/'audio-modules')
        code, kmsg = self.load('audio-modules')
        self.assertEqual(code, 0, kmsg)
        tree = self.dir/'tree'
        self.assertEqual(self.calls(), [f'modprobe -d {tree} {m}' for m in AUDIO])
        self.assertIn('audio-modules loaded ' + ' '.join(AUDIO), kmsg)
        self.assertFalse((self.dir/'shmem_enabled').read_text().startswith('within_size'))

    def test_sensor_list_loads(self):
        shutil.copy(SENSOR_LIST, self.kit/'sensor-modules')
        code, kmsg = self.load('sensor-modules')
        self.assertEqual(code, 0, kmsg)
        tree = self.dir/'tree'
        self.assertEqual(self.calls(), [f'modprobe -d {tree} {m}' for m in ('fastrpc', 'socinfo')])
        self.assertIn('sensor-modules loaded fastrpc socinfo', kmsg)

    def test_unknown_list_is_refused(self):
        code, kmsg = self.load('../boot-modules')
        self.assertEqual(code, 1)
        self.assertIn('FAIL unknown module list', kmsg)

    def test_bad_names_are_refused(self):
        (self.kit/'boot-modules').write_text('softdog\n../evil\n')
        code, kmsg = self.load()
        self.assertEqual(code, 1)
        self.assertIn('FAIL bad module name ../evil', kmsg)
        self.assertEqual(len(self.calls()), 1)


class RtcTime(Base):
    def setUp(self):
        super().setUp()
        self.rtc = self.dir/'sys/rtc0'
        self.rtc.mkdir(parents=True)
        (self.rtc/'name').write_text('rtc-pm8xxx c440000.spmi:pmic@0:rtc@6100\n')
        (self.rtc/'since_epoch').write_text(f'{RAW}\n')
        self.state = self.dir/'state'
        self.now = NOW
        self.stub('date', f'''case "$*" in
	+%s) cat $D/now ;;
	"-u -s @"*) echo "date $*" >>$D/calls; echo "${{3#@}}" >$D/now ;;
	*) /usr/bin/date -u -d "@$(cat $D/now)" "${{@:2}}" 2>/dev/null || echo T ;;
esac''')
        self.set_now(NOW)

    def set_now(self, value):
        (self.dir/'now').write_text(f'{value}\n')

    def rtc_time(self, action, synced=True):
        if synced:
            (self.dir/'synced').touch()
        return self.run_script(RTC, action, ROG5_RTC_SYS=str(self.dir/'sys'), ROG5_RTC_STATE=str(self.state),
                               ROG5_RTC_SYNCED=str(self.dir/'synced'), ROG5_RTC_KMSG=str(self.dir/'kmsg'),
                               ROG5_RTC_TRUSTED=str(self.dir/'trusted'))

    def test_save_then_restore_after_a_reboot(self):
        code, kmsg = self.rtc_time('save')
        self.assertEqual(code, 0, kmsg)
        self.assertEqual((self.state/'rtc-offset').read_text(), f'rog5-rtc-offset-v1 {NOW - RAW}\n')
        # Reboot 1 hour later: the RTC advanced, the clock restarted in the past.
        (self.rtc/'since_epoch').write_text(f'{RAW + 3600}\n')
        self.set_now(1780000000)
        (self.dir/'synced').unlink()
        (self.dir/'kmsg').unlink()
        code, kmsg = self.rtc_time('restore', synced=False)
        self.assertEqual(code, 0, kmsg)
        self.assertEqual(self.calls(), [f'date -u -s @{NOW + 3600}'])
        self.assertIn('restored', kmsg)
        self.assertTrue((self.dir/'trusted').exists())

    def test_restore_never_moves_the_clock_back(self):
        self.state.mkdir()
        (self.state/'rtc-offset').write_text(f'rog5-rtc-offset-v1 {NOW - RAW - 600}\n')
        code, kmsg = self.rtc_time('restore', synced=False)
        self.assertEqual(code, 0, kmsg)
        self.assertEqual(self.calls(), [])
        self.assertIn('unchanged', kmsg)

    def test_save_needs_ntp_and_a_sane_clock(self):
        code, kmsg = self.rtc_time('save', synced=False)
        self.assertEqual(code, 0)
        self.assertIn('SKIP clock not NTP-synchronized', kmsg)
        self.assertFalse((self.state/'rtc-offset').exists())
        self.set_now(RAW + 10)
        code, kmsg = self.rtc_time('save')
        self.assertEqual(code, 1)
        self.assertIn('outside the sane range', kmsg)

    def test_restore_refuses_malformed_or_insane_offsets(self):
        self.state.mkdir()
        for text, why in (('rog5-rtc-offset-v1 -5\n', 'malformed'), ('offset 5\n', 'malformed'),
                          ('rog5-rtc-offset-v1 99999999999\n', 'sane range'), ('rog5-rtc-offset-v1 1\n', 'sane range')):
            with self.subTest(text):
                (self.state/'rtc-offset').write_text(text)
                code, kmsg = self.rtc_time('restore', synced=False)
                self.assertEqual(code, 1, kmsg)
                self.assertIn(why, kmsg)
                self.assertEqual(self.calls(), [])
                self.assertFalse((self.dir/'trusted').exists())

    def test_missing_rtc_is_a_skip(self):
        (self.rtc/'name').write_text('some-other-rtc\n')
        code, kmsg = self.rtc_time('restore')
        self.assertEqual(code, 0)
        self.assertIn('SKIP no PMK8350 RTC', kmsg)


def prepare_function(kit, run):
    text = INIT.read_text()
    body = re.search(r'^prepare_platform_services\(\) \{\n.*?^\}\n', text, re.M | re.S).group(0)
    assert body.count('\tkit=/rog5-platform\n') == 1 and body.count('\trun=/run\n') == 1
    return body.replace('\tkit=/rog5-platform\n', f'\tkit={kit}\n').replace('\trun=/run\n', f'\trun={run}\n')


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Publish(Base):
    FILES = (('boot-modules', 0o444, LIST), ('audio-modules', 0o444, AUDIO_LIST), ('sensor-modules', 0o444, SENSOR_LIST), ('modules', 0o755, MODULES), ('rtc-time', 0o755, RTC),
             ('audio-route', 0o755, REPO/'initramfs/production-audio-route'),
             ('rog5-watchdog.conf', 0o644, REPO/'configs/systemd/rog5-watchdog.conf')) + tuple(
                 (unit, 0o644, REPO/'configs/systemd'/unit) for unit in UNITS)

    def setUp(self):
        super().setUp()
        self.kit, self.run = self.dir/'kit', self.dir/'run'
        self.run.mkdir()
        self.kit.mkdir(mode=0o700)
        for name, mode, source in self.FILES:
            (self.kit/name).write_bytes(source.read_bytes())
            (self.kit/name).chmod(mode)

    def prepare(self):
        shell = ['sh']
        env = dict(os.environ)
        if os.environ.get('ROG5_TEST_BUSYBOX'):
            qemu, busybox = os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX']
            for name in ('cp', 'ln', 'mkdir', 'stat'):
                self.stub(name, f'exec {qemu} {busybox} {name} "$@"')
            shell = [qemu, busybox, 'sh']
            env['PATH'] = f'{self.bin}:{env["PATH"]}'
        script = prepare_function(self.kit, self.run)+'prepare_platform_services\n'
        return subprocess.run(['unshare', '-r', *shell, '-c', script], capture_output=True, text=True,
                              env=env, timeout=120).returncode

    def test_kit_is_published(self):
        self.assertEqual(self.prepare(), 0)
        target = self.run/'rog5-platform'
        self.assertEqual(sorted(p.name for p in target.iterdir()), ['audio-modules', 'audio-route', 'boot-modules', 'modules', 'rtc-time', 'sensor-modules'])
        self.assertEqual(oct(target.stat().st_mode & 0o777), '0o700')
        system = self.run/'systemd/system'
        for unit in UNITS:
            self.assertEqual((system/unit).read_bytes(), (REPO/'configs/systemd'/unit).read_bytes())
        self.assertEqual(os.readlink(system/'sysinit.target.wants/rog5-platform-modules.service'),
                         '../rog5-platform-modules.service')
        self.assertEqual(os.readlink(system/'sysinit.target.wants/rog5-rtc-time.service'), '../rog5-rtc-time.service')
        self.assertEqual(os.readlink(system/'multi-user.target.wants/rog5-rtc-time-save.path'),
                         '../rog5-rtc-time-save.path')
        self.assertEqual(os.readlink(system/'multi-user.target.wants/rog5-audio.service'), '../rog5-audio.service')
        self.assertEqual(os.readlink(system/'multi-user.target.wants/rog5-sensors.service'), '../rog5-sensors.service')
        self.assertIn('RuntimeWatchdogSec=2min', (self.run/'systemd/system.conf.d/rog5-watchdog.conf').read_text())

    def test_absent_kit_is_a_no_op(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.kit)])
        shutil.rmtree(self.kit)
        self.assertEqual(self.prepare(), 0)
        self.assertEqual(list(self.run.iterdir()), [])

    def test_wrong_mode_extra_link_or_existing_target_is_refused(self):
        (self.kit/'rtc-time').chmod(0o775)
        self.assertEqual(self.prepare(), 1)
        self.assertEqual(list(self.run.iterdir()), [])
        (self.kit/'rtc-time').chmod(0o755)
        os.link(self.kit/'modules', self.dir/'extra')
        self.assertEqual(self.prepare(), 1)
        (self.dir/'extra').unlink()
        (self.run/'systemd/system').mkdir(parents=True)
        (self.run/'systemd/system/rog5-rtc-time.service').write_text('other\n')
        self.assertEqual(self.prepare(), 1)
        self.assertFalse((self.run/'rog5-platform').exists())


class Units(unittest.TestCase):
    def test_rtc_restore_runs_after_persistent_state_and_saves_on_stop(self):
        text = (REPO/'configs/systemd/rog5-rtc-time.service').read_text()
        after = re.search(r'^After=(.*)$', text, re.M).group(1).split()
        self.assertIn('rog5-persistent-state.service', after)
        self.assertIn('rog5-platform-modules.service', after)
        self.assertIn('ExecStop=/run/rog5-platform/rtc-time save', text)
        self.assertIn('/persist/var/lib/rog5-clock', RTC.read_text())

    def test_the_save_unit_stays_active_so_its_path_unit_cannot_loop(self):
        self.assertIn('RemainAfterExit=yes', (REPO/'configs/systemd/rog5-rtc-time-save.service').read_text())

    def test_every_listed_module_is_in_the_production_selection(self):
        import json
        selection = json.loads((REPO/'configs/kernel/rog5-production-modules.json').read_text())
        names = {Path(path).name[:-3].replace('-', '_') for path in selection['board_modules']}
        names |= {external['name'].replace('-', '_') for external in selection['external_modules']}
        for line in LIST.read_text().splitlines():
            line = line.split('#')[0].strip()
            if line:
                self.assertIn(line.split()[0].replace('-', '_'), names)


if __name__ == '__main__':
    unittest.main(verbosity=2)
