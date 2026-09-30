#!/usr/bin/env python3
"""Tests for initramfs/production-audio-route: the ALSA state sanitizer and the
per-amplifier choice between the direct path and the speaker-protection DSP.

The mixer is a fake (no libasound); sysfs, firmware and state paths point into
a temporary directory.
"""
import importlib.machinery
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
ROUTE = REPO/'initramfs/production-audio-route'


def load_route():
    loader = importlib.machinery.SourceFileLoader('production_audio_route', str(ROUTE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def control(numid, name, value, extra=''):
    return (f"\tcontrol.{numid} {{\n\t\tiface MIXER\n\t\tname '{name}'\n\t\tvalue {value}\n"
            f"\t\tcomment {{\n\t\t\taccess 'read write'\n\t\t\ttype ENUMERATED\n{extra}\t\t}}\n\t}}\n")


STATE = ('state.ASUSROGPhone5 {\n'
         + control(1, 'RCV DSP1 Preload Switch', 'true')
         + control(2, 'RCV DSP1 Firmware', 'Protection', "\t\t\titem.0 'MBC/VSS'\n")
         + control(3, 'SPK Digital PCM Volume', '361')
         + control(4, 'SPK DACPCM Source', 'DSP_TX1', "\t\t\titem.0 Zero\n")
         + control(5, 'RCV DSP_RX5 Source', 'VDD_BATTMON')
         + control(6, 'SPK DSP1 Protection cd CAL_R', "'000020c8'")
         + control(7, 'SEN_MI2S_RX Audio Mixer MultiMedia1', 'true')
         + '}\n'
         + 'state.Other {\n' + control(1, 'SPK DACPCM Source', 'ASP_RX1') + '}\n')


class Sanitize(unittest.TestCase):
    def setUp(self):
        self.route = load_route()
        self.route.log = lambda message: None
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-audio-route-'))
        self.state = self.dir/'asound.state'

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_drops_dsp_entries_of_this_card_only(self):
        self.state.write_text(STATE)
        self.state.chmod(0o640)
        self.assertEqual(self.route.sanitize_alsa_state(str(self.state)), 0)
        text = self.state.read_text()
        for gone in ('RCV DSP1 Preload Switch', 'RCV DSP1 Firmware', "'SPK DACPCM Source'\n\t\tvalue DSP_TX1",
                     'RCV DSP_RX5 Source', 'SPK DSP1 Protection cd CAL_R'):
            self.assertNotIn(gone, text)
        self.assertIn('SPK Digital PCM Volume', text)
        self.assertIn('SEN_MI2S_RX Audio Mixer MultiMedia1', text)
        self.assertIn("state.Other {\n\tcontrol.1 {\n\t\tiface MIXER\n\t\tname 'SPK DACPCM Source'", text)
        self.assertEqual(text.count('{'), text.count('}'))
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o640)
        again = text
        self.route.sanitize_alsa_state(str(self.state))
        self.assertEqual(self.state.read_text(), again)

    def test_missing_and_unparsable_files_are_left_alone(self):
        self.assertEqual(self.route.sanitize_alsa_state(str(self.dir/'none')), 0)
        broken = STATE[:-40]
        self.state.write_text(broken)
        self.route.sanitize_alsa_state(str(self.state))
        self.assertEqual(self.state.read_text(), broken)


class FakeMixer:
    """Controls of one amplifier pair; Preload 1 'boots' the DSP."""

    def __init__(self, cal=None, state=0, error=0, boots=True):
        self.values = {}
        self.writes = []
        self.running = set()
        self.cal = cal or {}
        self.state, self.error, self.boots = state, error, boots
        self.params = {}

    def set(self, name, value):
        self.writes.append((name, value))
        prefix = name.split()[0]
        if name.endswith('DSP1 Preload Switch'):
            if value == '1' and self.boots:
                self.running.add(prefix)
            elif value == '0':
                self.running.discard(prefix)
        self.values[name] = value
        return 0

    def get_int(self, name):
        value = self.values.get(name, '0')
        return int(value) if value.isdigit() else None

    def _coeff(self, name):
        prefix = name.split()[0]
        if prefix not in self.running:
            return None
        field = name.rsplit(' ', 1)[1]
        cal_r = self.cal.get(prefix, 0)
        return {'CAL_R': cal_r, 'CAL_STATUS': 1, 'CAL_CHECKSUM': cal_r + 1,
                'CSPL_STATE': self.state, 'CSPL_ERRORNO': self.error}.get(field)

    def get_be32(self, name):
        return self._coeff(name)

    def get_bytes(self, name):
        if name.split()[0] not in self.running:
            return -1, None
        return 0, self.params.get(name, bytes(400))

    def set_bytes(self, name, data):
        self.writes.append((name, data))
        self.params[name] = data
        return 0


class AmpBase(unittest.TestCase):
    def setUp(self):
        self.route = load_route()
        self.logs = []
        self.route.log = self.logs.append
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-audio-route-'))
        fw = self.dir/'firmware'
        fw.mkdir()
        for part in ('rcv', 'spk'):
            for suffix in ('wmfw', 'bin'):
                (fw/f'cs35l45-{part}-dsp1-spk-prot.{suffix}').write_bytes(b'x')
        (self.dir/'cs35l45-rcv-music.be32').write_bytes((68).to_bytes(4, 'big') + bytes(268))
        self.route.FIRMWARE_DIR = str(fw)
        self.route.SPEAKER_DIR = str(self.dir)
        self.route.amp_device = lambda prefix: f'/sys/fake/{prefix}'
        self.route.dt_string = lambda device, prop: 'cs35l45-' + device.rsplit('/', 1)[1].lower()
        self.pm = {}

        def runtime_control(device, value=None):
            if value is not None:
                self.pm[device] = value
            return self.pm.get(device, 'auto')
        self.route.runtime_control = runtime_control
        self.route.runtime_status = lambda device: 'active' if self.pm.get(device) == 'on' else 'suspended'
        self.route.DSP_BOOT_SECONDS = 0.3
        self.calibration = {'rcv_cal_r': '8996', 'spk_cal_r': '9096',
                            'rcv_cal_source': 'persist', 'spk_cal_source': 'persist'}
        self.on = {'amps': 'rcv spk'}

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_amp(self, mixer, config=None, calibration=None):
        return self.route.route_amp(mixer, 'RCV', 'rcv', 'ASP_RX1', dict(self.on, **(config or {})),
                                    self.calibration if calibration is None else calibration)


class Amp(AmpBase):
    def test_protection_path(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        names = [name for name, value in mixer.writes]
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')
        self.assertEqual(mixer.values['RCV DSP_RX1 Source'], 'ASP_RX1')
        self.assertEqual(mixer.values['RCV DSP_RX2 Source'], 'ASP_RX1')
        self.assertEqual(mixer.values['RCV DSP_RX5 Source'], 'VDD_BATTMON')
        self.assertEqual(mixer.values['RCV DSP_RX6 Source'], 'VDD_BSTMON')
        self.assertEqual(mixer.values['RCV DSP_RX7 Source'], 'CLASSH_TGT')
        # inputs and firmware before the preload, DACPCM last
        self.assertLess(names.index('RCV DSP_RX7 Source'), names.index('RCV DSP1 Preload Switch'))
        self.assertLess(names.index('RCV DSP1 Firmware'), names.index('RCV DSP1 Preload Switch'))
        # DACPCM, then (only now) the full level
        self.assertEqual(mixer.writes[-2:], [('RCV DACPCM Source', 'DSP_TX1'), ('RCV Digital PCM Volume', '409')])
        self.assertNotIn('RCV DSP1 Protection cd CSPL_COMMAND', names)
        # stock never hibernated this firmware: the amplifier stays awake
        self.assertEqual(self.pm['/sys/fake/RCV'], 'on')

    def test_hibernate_option_returns_to_autosuspend(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer, config={'hibernate': '1'}))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')
        self.assertEqual(self.pm['/sys/fake/RCV'], 'auto')

    def test_rerun_does_not_restart_a_running_dsp(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.set('RCV DSP1 Preload Switch', '1')
        mixer.writes.clear()
        self.assertIsNone(self.run_amp(mixer))
        self.assertNotIn('RCV DSP1 Preload Switch', [name for name, value in mixer.writes])
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')

    def test_no_firmware_or_disabled_keeps_direct_path(self):
        for name in ('cs35l45-rcv-dsp1-spk-prot.bin',):
            (Path(self.route.FIRMWARE_DIR)/name).unlink()
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertNotIn('RCV DSP1 Preload Switch', mixer.values)
        self.assertEqual(self.logs, [])

    def test_disabling_stops_a_running_dsp_after_the_direct_path(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.set('RCV DSP1 Preload Switch', '1')
        mixer.writes.clear()
        self.assertIsNone(self.run_amp(mixer, config={'amps': ''}))
        self.assertEqual(mixer.writes, [('RCV Digital PCM Volume', '361'), ('RCV DACPCM Source', 'ASP_RX1'),
                                        ('RCV DSP1 Preload Switch', '0')])
        self.assertEqual(self.pm['/sys/fake/RCV'], 'auto')

    def test_core_kept_running_by_another_path_is_reported(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.set('RCV DSP1 Preload Switch', '1')
        orig = mixer.set

        def set_keep_core(name, value):
            rc = orig(name, value)
            mixer.running.add('RCV')  # e.g. a capture path through DSP_TX1
            return rc
        mixer.set = set_keep_core
        failure = self.run_amp(mixer, config={'amps': ''})
        self.assertIn('DSP stop', failure)
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')

    def test_calibration_mismatch_falls_back(self):
        mixer = FakeMixer(cal={'RCV': 8392})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertEqual(mixer.values['RCV DSP1 Preload Switch'], '0')
        self.assertTrue(any('FAIL RCV speaker protection: calibration' in line for line in self.logs))

    def test_cspl_error_or_boot_failure_falls_back(self):
        for mixer in (FakeMixer(cal={'RCV': 8996}, state=1), FakeMixer(cal={'RCV': 8996}, error=5),
                      FakeMixer(cal={'RCV': 8996}, boots=False)):
            self.assertIsNone(self.run_amp(mixer))
            self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
            self.assertEqual(mixer.values['RCV DSP1 Preload Switch'], '0')
            self.assertNotIn(('RCV DACPCM Source', 'DSP_TX1'), mixer.writes)
            self.assertEqual(self.pm['/sys/fake/RCV'], 'auto')

    def test_out_of_range_calibration_is_refused(self):
        mixer = FakeMixer(cal={'RCV': 12000})
        self.assertIsNone(self.run_amp(mixer, calibration={'rcv_cal_r': '12000', 'rcv_cal_source': 'persist'}))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertNotIn('RCV DSP1 Preload Switch', mixer.values)

    def test_missing_config_or_default_calibration_keeps_direct_path(self):
        mixer = FakeMixer(cal={'RCV': 8392})
        self.assertIsNone(self.route.route_amp(mixer, 'RCV', 'rcv', 'ASP_RX1', {}, self.calibration))
        self.assertNotIn('RCV DSP1 Preload Switch', mixer.values)
        default = {'rcv_cal_r': '8392', 'rcv_cal_source': 'default (persist value missing)'}
        self.assertIsNone(self.run_amp(mixer, calibration=default))
        self.assertNotIn('RCV DSP1 Preload Switch', mixer.values)
        self.assertIsNone(self.run_amp(mixer, config={'allow_default_calibration': '1'}, calibration=default))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')

    def test_music_delta_needs_running_state(self):
        mixer = FakeMixer(cal={'RCV': 8996}, state=2)
        self.assertIsNone(self.run_amp(mixer, config={'music_delta': '1'}))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertTrue(any('music delta: CSPL_STATE 2' in line for line in self.logs))

    def test_music_delta(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer, config={'music_delta': '1'}))
        params = mixer.params['RCV DSP1 Protection cd UPDATE_PARAMS_CONFIG']
        self.assertEqual(len(params), 400)
        self.assertEqual(params[:4], (68).to_bytes(4, 'big'))
        self.assertEqual(mixer.params['RCV DSP1 Protection cd CSPL_COMMAND'], (8).to_bytes(4, 'big'))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')


class NoDspMixer(FakeMixer):
    """A kernel without the protection support (e.g. the r69 fallback): the
    amplifier has no DSP1 or DSP_RXn controls."""

    def set(self, name, value):
        if ' DSP' in name:
            self.writes.append((name, value))
            return -2
        return super().set(name, value)

    def get_int(self, name):
        return None if ' DSP' in name else super().get_int(name)


class Level(AmpBase):
    """0 dB only behind a verified protection DSP, -12 dB on every direct path."""

    def volumes(self, mixer):
        return [value for name, value in mixer.writes if name == 'RCV Digital PCM Volume']

    def test_route_starts_every_amplifier_at_the_direct_level(self):
        levels = {name: value for name, value in self.route.ROUTE if name.endswith('Digital PCM Volume')}
        self.assertEqual(levels, {'SPK Digital PCM Volume': '361', 'RCV Digital PCM Volume': '361'})
        self.assertNotIn('409', [value for name, value in self.route.ROUTE])

    def test_kernel_without_protection_controls_stays_at_minus_12_db(self):
        mixer = NoDspMixer(cal={'RCV': 8996})
        mixer.values['RCV Digital PCM Volume'] = '409'  # e.g. restored by alsactl
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
        self.assertNotIn('409', self.volumes(mixer))
        self.assertTrue(any('FAIL RCV speaker protection' in line for line in self.logs))

    def test_every_failed_start_lowers_the_level_before_the_direct_path(self):
        for mixer in (FakeMixer(cal={'RCV': 8996}, state=1), FakeMixer(cal={'RCV': 8392}),
                      FakeMixer(cal={'RCV': 8996}, boots=False)):
            mixer.values['RCV Digital PCM Volume'] = '409'  # left by an earlier protected run
            self.assertIsNone(self.run_amp(mixer))
            self.assertNotIn('409', self.volumes(mixer))
            self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
            names = [name for name, value in mixer.writes]
            self.assertLess(names.index('RCV Digital PCM Volume'), names.index('RCV DACPCM Source'))

    def test_disabled_or_missing_firmware_is_direct_at_minus_12_db(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer, config={'amps': ''}))
        self.assertEqual(self.volumes(mixer), ['361'])
        (Path(self.route.FIRMWARE_DIR)/'cs35l45-rcv-dsp1-spk-prot.wmfw').unlink()
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(self.volumes(mixer), ['361'])

    def test_protected_amplifier_gets_0_db_after_dacpcm(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(self.volumes(mixer), ['409'])
        names = [name for name, value in mixer.writes]
        self.assertLess(names.index('RCV DACPCM Source'), names.index('RCV Digital PCM Volume'))


if __name__ == '__main__':
    unittest.main()
