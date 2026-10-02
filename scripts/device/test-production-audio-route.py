#!/usr/bin/env python3
"""Tests for initramfs/production-audio-route: the ALSA state sanitizer and the
per-amplifier choice between the direct path and the speaker-protection DSP.

The mixer is a fake (no libasound); sysfs, firmware and state paths point into
a temporary directory.
"""
import fnmatch
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import shutil
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
ROUTE = REPO/'initramfs/production-audio-route'
RULES = REPO/'configs/udev'


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
         + control(8, 'RCV Digital PCM Volume', '409')
         + control(9, 'RCV AMP Enable Switch', 'true')
         + control(10, 'SPK AMP Enable Switch', 'false')
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
        self.assertIn("'SPK Digital PCM Volume'\n\t\tvalue 361\n", text)
        # a shutdown behind a running DSP saved 0 dB: restored at -12 dB
        self.assertIn("'RCV Digital PCM Volume'\n\t\tvalue 361\n", text)
        self.assertNotIn('409', text)
        # amplifiers restored off: the route enables them after -12 dB
        self.assertIn("'RCV AMP Enable Switch'\n\t\tvalue false\n", text)
        self.assertIn("'SPK AMP Enable Switch'\n\t\tvalue false\n", text)
        self.assertIn('SEN_MI2S_RX Audio Mixer MultiMedia1', text)
        self.assertIn("state.Other {\n\tcontrol.1 {\n\t\tiface MIXER\n\t\tname 'SPK DACPCM Source'", text)
        self.assertEqual(text.count('{'), text.count('}'))
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o640)
        again = text
        self.route.sanitize_alsa_state(str(self.state))
        self.assertEqual(self.state.read_text(), again)

    def test_only_a_safe_state_is_left_unchanged(self):
        safe = ('state.ASUSROGPhone5 {\n' + control(1, 'SPK Digital PCM Volume', '361')
                + control(2, 'SPK AMP Enable Switch', 'false') + '}\n')
        self.state.write_text(safe)
        before = self.state.stat().st_mtime_ns
        self.assertEqual(self.route.sanitize_alsa_state(str(self.state)), 0)
        self.assertEqual(self.state.read_text(), safe)
        self.assertEqual(self.state.stat().st_mtime_ns, before)

    def test_multi_value_and_other_card_entries(self):
        text = ('state.ASUSROGPhone5 {\n'
                + "\tcontrol.1 {\n\t\tiface MIXER\n\t\tname 'RCV Digital PCM Volume'\n"
                  "\t\tvalue.0 409\n\t\tvalue.1 457\n\t\tcomment {\n\t\t\ttype INTEGER\n"
                  "\t\t\tdbvalue.0 0\n\t\t}\n\t}\n"
                + '}\nstate.Other {\n' + control(1, 'RCV Digital PCM Volume', '409') + '}\n')
        self.state.write_text(text)
        self.route.sanitize_alsa_state(str(self.state))
        out = self.state.read_text()
        self.assertIn('\t\tvalue.0 361\n\t\tvalue.1 361\n', out)
        self.assertIn('\t\t\tdbvalue.0 0\n', out)  # comments untouched
        self.assertIn("state.Other {\n\tcontrol.1 {\n\t\tiface MIXER\n\t\tname 'RCV Digital PCM Volume'\n"
                      "\t\tvalue 409\n", out)

    def test_missing_file_is_fine_and_unparsable_is_moved_aside(self):
        self.assertEqual(self.route.sanitize_alsa_state(str(self.dir/'none')), 0)
        self.assertEqual(list(self.dir.iterdir()), [])
        broken = STATE[:-40]
        self.state.write_text(broken)
        self.assertEqual(self.route.sanitize_alsa_state(str(self.state)), 0)
        # alsactl must not restore an unchecked 0 dB / amplifier-on state
        self.assertFalse(self.state.exists())
        self.assertEqual((self.dir/'asound.state.rog5-unsafe').read_text(), broken)

    def test_unwritable_state_is_moved_aside(self):
        self.state.write_text(STATE)
        real_open = open

        def failing_open(path, mode='r', *args, **kwargs):
            if str(path).endswith('.rog5-tmp'):
                raise OSError(28, 'No space left on device')
            return real_open(path, mode, *args, **kwargs)
        self.route.open = failing_open
        try:
            self.assertEqual(self.route.sanitize_alsa_state(str(self.state)), 0)
        finally:
            del self.route.open
        self.assertFalse(self.state.exists())
        self.assertTrue((self.dir/'asound.state.rog5-unsafe').exists())
        self.assertFalse((self.dir/'asound.state.rog5-tmp').exists())

    def test_inline_comment_is_rewritten(self):
        self.state.write_text('state.ASUSROGPhone5 {\n' + control(1, 'RCV Digital PCM Volume', '409 # saved gain')
                              + control(2, 'RCV AMP Enable Switch', 'true # on') + '}\n')
        self.route.sanitize_alsa_state(str(self.state))
        text = self.state.read_text()
        self.assertIn("'RCV Digital PCM Volume'\n\t\tvalue 361\n", text)
        self.assertIn("'RCV AMP Enable Switch'\n\t\tvalue false\n", text)
        self.assertNotIn('409', text)

    def assert_moved_aside(self, text):
        self.state.write_text(text)
        self.assertEqual(self.route.sanitize_alsa_state(str(self.state)), 0)
        self.assertFalse(self.state.exists(), text)
        self.assertEqual((self.dir/'asound.state.rog5-unsafe').read_text(), text)
        (self.dir/'asound.state.rog5-unsafe').unlink()

    def test_layouts_other_than_alsactls_are_moved_aside(self):
        volume = "\t\tiface MIXER\n\t\tname 'RCV Digital PCM Volume'\n"
        for text in (
                # compact: the whole control on one line
                "state.ASUSROGPhone5 {\n\tcontrol.1 { name 'RCV Digital PCM Volume' value 409 }\n}\n",
                # name and value on one line inside the block
                "state.ASUSROGPhone5 {\n\tcontrol.1 {\n\t\tname 'RCV Digital PCM Volume' value 409\n\t}\n}\n",
                # a compound value
                "state.ASUSROGPhone5 {\n\tcontrol.1 {\n" + volume + "\t\tvalue [ 409 409 ]\n\t}\n}\n",
                # no value line at all
                "state.ASUSROGPhone5 {\n\tcontrol.1 {\n" + volume + "\t}\n}\n",
                # libasound reads an escaped name as RCV Digital PCM Volume
                "state.ASUSROGPhone5 {\n" + control(1, 'RCV Digital PCM Volum\\e', '409') + "}\n",
                # a quoted key: libasound takes the last value, 409
                "state.ASUSROGPhone5 {\n\tcontrol.1 {\n" + volume + "\t\tvalue 361\n\t\t'value' 409\n\t}\n}\n",
                # an escaped card id
                "state.ASUSROGPhone\\5 {\n" + control(1, 'RCV Digital PCM Volume', '409') + "}\n",
                # two keys on one line, a brace inside the comment block
                "state.ASUSROGPhone5 {\n\tcontrol.1 {\n\t\tiface MIXER name 'RCV Digital PCM Volume'\n"
                "\t\tvalue 409\n\t}\n}\n",
                "state.ASUSROGPhone5 {\n\tcontrol.1 {\n" + volume + "\t\tvalue 361\n\t\tcomment {\n"
                "\t\t\ttype INTEGER } value 409\n\t\t}\n\t}\n}\n",
                # the card in another notation
                "state {\n\tASUSROGPhone5 {\n\t\tcontrol.1 {\n" + volume + "\t\t\tvalue 409\n\t\t}\n\t}\n}\n",
                # dotted keys at card level
                "state.ASUSROGPhone5 {\n\tcontrol.1.value 409\n}\n"):
            self.assert_moved_aside(text)

    def test_quoted_values_with_spaces_are_alsactl_layout(self):
        text = ('state.ASUSROGPhone5 {\n' + control(1, 'RCV DSP1 Firmware', "'Tx Speaker'", "\t\t\titem.0 'MBC/VSS'\n")
                + control(2, 'VA DEC0 MUX', "'VA DMIC'") + control(3, 'RCV Digital PCM Volume', "'4 09'") + '}\n')
        self.state.write_text(text)
        self.route.sanitize_alsa_state(str(self.state))
        out = self.state.read_text()
        self.assertNotIn('DSP1 Firmware', out)
        self.assertIn("value 'VA DMIC'", out)
        self.assertIn("'RCV Digital PCM Volume'\n\t\tvalue 361\n", out)

    def test_quoted_card_id_is_handled(self):
        self.state.write_text("state.'ASUSROGPhone5' {\n" + control(1, 'RCV Digital PCM Volume', '409') + '}\n')
        self.route.sanitize_alsa_state(str(self.state))
        self.assertIn('value 361', self.state.read_text())

    def test_unwritable_and_immovable_state_is_reported(self):
        # e.g. a read-only /var/lib/alsa: nothing can be done here; the route
        # attenuates (and confirms) right after the restore
        self.state.write_text(STATE)
        real_open, real_replace = open, self.route.os.replace

        def failing_open(path, mode='r', *args, **kwargs):
            if str(path).endswith('.rog5-tmp'):
                raise OSError(30, 'Read-only file system')
            return real_open(path, mode, *args, **kwargs)

        def failing_replace(src, dst):
            raise OSError(30, 'Read-only file system')
        logs = []
        self.route.log = logs.append
        self.route.open = failing_open
        self.route.os.replace = failing_replace
        try:
            self.assertEqual(self.route.sanitize_alsa_state(str(self.state)), 0)
        finally:
            del self.route.open
            self.route.os.replace = real_replace
        self.assertTrue(any('FAIL' in line and 'could not be moved aside' in line for line in logs))

    def test_main_moves_an_unreadable_state_aside(self):
        self.state.write_bytes(b'state.ASUSROGPhone5 {\n\xff\xfe\n}\n')
        self.route.STATE_FILE = str(self.state)
        argv = self.route.sys.argv
        self.route.sys.argv = ['audio-route', '--sanitize-alsa-state']
        try:
            self.assertEqual(self.route.main(), 0)
        finally:
            self.route.sys.argv = argv
        self.assertFalse(self.state.exists())
        self.assertTrue((self.dir/'asound.state.rog5-unsafe').exists())


class FakeMixer:
    """Controls of one amplifier pair; Preload 1 'boots' the DSP."""

    def __init__(self, cal=None, state=0, error=0, boots=True, fail=(), ignore=()):
        self.values = {}
        self.writes = []
        # fail: the write returns an error, nothing changes; ignore: the
        # write "succeeds", but the control keeps its value
        self.fail, self.ignore = set(fail), set(ignore)
        self.running = set()
        self.cal = cal or {}
        self.state, self.error, self.boots = state, error, boots
        self.params = {}

    def set(self, name, value):
        self.writes.append((name, value))
        if name in self.fail:
            return -5
        if name in self.ignore:
            return 0
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

        def log(message):
            # as on the phone: this script's reports land in the kernel log
            self.logs.append(message)
            if isinstance(self.kmsg, list):
                self.kmsg.append(f'rog5-audio-route: {message}')
        self.route.log = log
        self.kmsg = []
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
        self.route.DSP_STOP_SECONDS = 0.3
        self.route.PCM_IDLE_SECONDS = 0.3
        self.kmsg = []
        self.route.kernel_messages = lambda: list(self.kmsg)
        self.idle = True
        self.route.playback_idle = lambda card: self.idle
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
        # DACPCM, then (only now) the full level, then the amplifier
        self.assertEqual(mixer.writes[-3:], [('RCV DACPCM Source', 'DSP_TX1'), ('RCV Digital PCM Volume', '409'),
                                             ('RCV AMP Enable Switch', '1')])
        self.assertEqual(mixer.writes[:2], [('RCV Digital PCM Volume', '360'), ('RCV Digital PCM Volume', '361')])
        self.assertNotIn('RCV DSP1 Protection cd CSPL_COMMAND', names)
        # stock never hibernated this firmware: the amplifier stays awake
        self.assertEqual(self.pm['/sys/fake/RCV'], 'on')

    def test_hibernate_option_returns_to_autosuspend(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer, config={'hibernate': '1'}))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')
        self.assertEqual(self.pm['/sys/fake/RCV'], 'auto')

    def test_rerun_does_not_restart_a_running_dsp(self):
        self.kmsg = ['cs35l45 RCV: Protection firmware calibration CAL_R 8996']
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
        self.assertEqual(mixer.writes, [('RCV Digital PCM Volume', '360'), ('RCV Digital PCM Volume', '361')] * 2
                         + [('RCV DACPCM Source', 'ASP_RX1'), ('RCV DSP1 Preload Switch', '0'),
                            ('RCV AMP Enable Switch', '1')])
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


# The amplifier device of the fake sysfs is /sys/fake/RCV.
START = 'cs35l45 RCV: Protection firmware calibration CAL_R 8996'
PAUSE_FAILED = 'cs35l45 RCV: Failed to set mailbox cmd 1 (status 0)'


class Wedge(AmpBase):
    """A protection DSP whose firmware missed a pause after its last start
    is power cycled, once playback is idle."""

    def running_mixer(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.set('RCV DSP1 Preload Switch', '1')
        mixer.writes.clear()
        return mixer

    def preloads(self, mixer):
        return [value for name, value in mixer.writes if name == 'RCV DSP1 Preload Switch']

    def test_wedge_reason(self):
        reason = self.route.wedge_reason
        # no start in the history (overwritten) or no history: unknown, restart
        self.assertIn('no longer in the kernel log', reason([], '5-0030', 'RCV'))
        self.assertEqual(reason(None, '5-0030', 'RCV'), 'kernel log unreadable')
        log = ['cs35l45 5-0030: Protection firmware calibration CAL_R 8996',
               'cs35l45 5-0031: Failed to set mailbox cmd 1 (status 0)',
               'snd-sm8250 sound: ASoC: PRE_PMD: SPK DSP1 event failed: -42']
        self.assertIsNone(reason(log, '5-0030', 'RCV'))
        self.assertIn('5-0031: Failed', reason(log[:2], '5-0031', 'SPK'))
        self.assertIn('SPK DSP1', reason(log, '5-0031', 'SPK'))
        # a later start (a reload) clears it
        self.assertIsNone(reason(log + ['cs35l45 5-0031: Protection firmware calibration CAL_R 9096'],
                                 '5-0031', 'SPK'))
        # this script's own report quotes the failure
        self.assertIsNone(reason(log[:1] + ['rog5-audio-route: RCV protection DSP wedged after its last start '
                                            '(cs35l45 5-0030: Failed to set mailbox cmd 1 (status 0)); restarting it'],
                                 '5-0030', 'RCV'))
        # the hibernation exit retries are not failures
        self.assertIsNone(reason(log[:1] + ['cs35l45 5-0030: Failed to set mailbox cmd 6 (status 1)'],
                                 '5-0030', 'RCV'))
        self.assertIsNotNone(reason(['cs35l45 5-0030: Protection firmware did not pause: stopping it'],
                                    '5-0030', 'RCV'))
        # a resume that could not be written
        for line in ('cs35l45 5-0030: Failed to write MBOX: -5',
                     'snd-sm8250 sound: ASoC: POST_PMU: RCV DSP1 event failed: -5'):
            self.assertEqual(reason(log[:1] + [line], '5-0030', 'RCV'), line)

    def test_kernel_messages_reads_records(self):
        path = self.dir/'kmsg'
        path.write_bytes(b'6,1,5,-;cs35l45 5-0030: Failed to set mailbox cmd 1 (status 0)\n SUBSYSTEM=i2c\n')
        # a regular file returns everything in one read, then EOF
        self.assertEqual(self.route_module_messages(path), ['cs35l45 5-0030: Failed to set mailbox cmd 1 (status 0)'])
        self.assertIsNone(self.route_module_messages(self.dir/'missing'))

    def test_kernel_messages_overwritten_while_reading_is_unknown(self):
        route = load_route()
        reads = iter([b'6,1,5,-;cs35l45 RCV: Protection firmware calibration CAL_R 8996\n', BrokenPipeError()])

        def read(fd, size):
            item = next(reads)
            if isinstance(item, Exception):
                raise item
            return item
        route.os = type('os', (), dict(open=lambda *a: 3, read=read, close=lambda fd: None,
                                       O_RDONLY=0, O_NONBLOCK=0))
        self.assertIsNone(route.kernel_messages('/dev/kmsg'))

    def route_module_messages(self, path):
        return load_route().kernel_messages(str(path))

    def test_healthy_running_dsp_is_kept(self):
        self.kmsg = [PAUSE_FAILED, START]
        mixer = self.running_mixer()
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(self.preloads(mixer), [])
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')

    def test_unknown_history_restarts_the_dsp(self):
        for history in ([], None, [PAUSE_FAILED]):
            self.kmsg = history
            self.route.kernel_messages = lambda: None if self.kmsg is None else list(self.kmsg)
            mixer = self.running_mixer()
            self.assertIsNone(self.run_amp(mixer))
            self.assertEqual(self.preloads(mixer)[:2], ['0', '1'])
            if history is None:
                # without a kernel log DACPCM = DSP_TX1 cannot be confirmed: direct path
                self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
                self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
            else:
                self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')

    def test_wedged_dsp_is_power_cycled(self):
        self.kmsg = [START, PAUSE_FAILED]
        mixer = self.running_mixer()
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(self.preloads(mixer), ['0', '1'])
        self.assertTrue(any('RCV protection DSP wedged' in line for line in self.logs))
        self.assertTrue(any('started' in line for line in self.logs))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'DSP_TX1')
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '409')

    def test_wedged_dsp_with_playback_running_goes_direct(self):
        self.kmsg = [START, PAUSE_FAILED]
        self.idle = False
        mixer = self.running_mixer()
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
        self.assertNotIn('409', [value for name, value in mixer.writes if name == 'RCV Digital PCM Volume'])
        self.assertTrue(any('wedged' in line and 'playback did not stop' in line for line in self.logs))

    def test_dsp_that_does_not_stop_goes_direct(self):
        self.kmsg = [START, PAUSE_FAILED]
        mixer = self.running_mixer()
        orig = mixer.set

        def set_keep_core(name, value):
            rc = orig(name, value)
            mixer.running.add('RCV')
            return rc
        mixer.set = set_keep_core
        failure = self.run_amp(mixer)
        self.assertTrue(any('DSP did not stop' in line for line in self.logs))
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertIn('DSP stop', failure)


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

    def test_route_leaves_levels_and_enables_to_route_amp(self):
        names = [name for name, value in self.route.ROUTE]
        self.assertFalse([name for name in names if 'Digital PCM Volume' in name or 'AMP Enable' in name
                          or name == self.route.PLAYBACK_MIXER])
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
        # first, and again right before DACPCM; each 361 preceded by 360 so it reaches the amplifier
        self.assertEqual(self.volumes(mixer), ['360', '361', '360', '361'])
        (Path(self.route.FIRMWARE_DIR)/'cs35l45-rcv-dsp1-spk-prot.wmfw').unlink()
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(self.volumes(mixer), ['360', '361', '360', '361'])

    def test_protected_amplifier_gets_0_db_after_dacpcm(self):
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(self.volumes(mixer), ['360', '361', '409'])
        self.assertLess(mixer.writes.index(('RCV DACPCM Source', 'DSP_TX1')),
                        mixer.writes.index(('RCV Digital PCM Volume', '409')))


class CachedMixer(FakeMixer):
    """The driver's view as regmap gives it: a write updates the register
    cache first and then the amplifier; the write is skipped when the cache
    already holds the value; reads come from the cache. hw_fail: writes of
    these controls fail at the amplifier (the cache keeps the new value)."""

    def __init__(self, hw_fail=(), hw_fail_count=None, **kwargs):
        super().__init__(**kwargs)
        self.hw = {}
        self.hw_fail, self.hw_fail_count = set(hw_fail), hw_fail_count

    def set(self, name, value):
        if name not in self.hw_fail:
            rc = super().set(name, value)
            self.hw[name] = self.values.get(name)
            return rc
        self.writes.append((name, value))
        if self.values.get(name) == value:
            return 0  # cache already matches: no bus write, success
        self.values[name] = value
        if self.hw_fail_count is not None:
            if self.hw_fail_count == 0:
                self.hw[name] = value
                return 0
            self.hw_fail_count -= 1
        return -5


class FailClosed(AmpBase):
    """-12 dB must be confirmed before DACPCM Source, the DSP or the AMP
    Enable Switch change (GPT-6.1-Sol audit 2026-10-02: a failed volume write
    still switched to the direct path, leaving 409 with ASP_RX1)."""

    def setUp(self):
        super().setUp()
        self.route.CONFIRM_RETRY_SECONDS = 0

    def earlier_protected_run(self, cls=FakeMixer, **kwargs):
        mixer = cls(cal={'RCV': 8996}, **kwargs)
        mixer.values.update({'RCV Digital PCM Volume': '409', 'RCV DACPCM Source': 'DSP_TX1',
                             'RCV AMP Enable Switch': '1', 'RCV DSP1 Preload Switch': '1'})
        if cls is CachedMixer:
            mixer.hw.update(mixer.values)
        mixer.running.add('RCV')
        return mixer

    def assert_muted(self, mixer, failure):
        self.assertIn('not confirmed at 361', failure)
        self.assertIn('amplifier muted', failure)
        self.assertNotIsInstance(failure, self.route.NotIsolated)
        self.assertEqual(mixer.values['RCV AMP Enable Switch'], '0')
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'Zero')
        self.assertNotIn(('RCV DACPCM Source', 'ASP_RX1'), mixer.writes)
        # Zero is written through DSP_TX1 (so it is a register change) after the amplifier is off
        self.assertEqual([w for w in mixer.writes if w[0] in ('RCV DACPCM Source', 'RCV AMP Enable Switch')],
                         [('RCV AMP Enable Switch', '0'), ('RCV DACPCM Source', 'DSP_TX1'),
                          ('RCV DACPCM Source', 'Zero')])
        # the (protecting) DSP is not stopped or restarted
        self.assertNotIn('RCV DSP1 Preload Switch', [name for name, value in mixer.writes])
        self.assertTrue(any(line.startswith('FAIL RCV Digital PCM Volume not confirmed') for line in self.logs))

    def test_failed_volume_write_never_selects_the_direct_path(self):
        for config in ({'amps': ''}, {}):  # disabled, and protection that would fail (no kmsg start)
            mixer = self.earlier_protected_run(fail={'RCV Digital PCM Volume'})
            self.assert_muted(mixer, self.run_amp(mixer, config=config))
            self.assertEqual(mixer.values['RCV Digital PCM Volume'], '409')

    def test_volume_write_that_does_not_take_is_not_trusted(self):
        mixer = self.earlier_protected_run(ignore={'RCV Digital PCM Volume'})
        self.assert_muted(mixer, self.run_amp(mixer, config={'amps': ''}))
        # retried before giving up
        self.assertEqual([value for name, value in mixer.writes if name == 'RCV Digital PCM Volume'],
                         ['360', '361'] * 3)

    def test_cached_read_back_of_a_failed_write_is_not_trusted(self):
        # regmap: the cache says 361 after the failed I2C write, the amplifier is at 409
        mixer = self.earlier_protected_run(cls=CachedMixer, hw_fail={'RCV Digital PCM Volume'})
        self.assert_muted(mixer, self.run_amp(mixer, config={'amps': ''}))
        self.assertEqual(mixer.hw['RCV Digital PCM Volume'], '409')
        self.assertEqual(mixer.hw['RCV DACPCM Source'], 'Zero')
        self.assertEqual(mixer.hw['RCV AMP Enable Switch'], '0')

    def test_transient_failure_reaches_the_amplifier_on_retry(self):
        # the first bus write fails (cache already updated); the retry still
        # reaches the amplifier because 360 -> 361 changes the cached value
        for fails in (1, 2):
            mixer = self.earlier_protected_run(cls=CachedMixer, hw_fail={'RCV Digital PCM Volume'},
                                               hw_fail_count=fails)
            self.assertIsNone(self.run_amp(mixer, config={'amps': ''}))
            self.assertEqual(mixer.hw['RCV Digital PCM Volume'], '361')
            self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
            self.assertEqual(mixer.values['RCV AMP Enable Switch'], '1')

    def test_mute_failure_is_reported_as_not_isolated(self):
        mixer = self.earlier_protected_run(fail={'RCV Digital PCM Volume', 'RCV AMP Enable Switch',
                                                 'RCV DACPCM Source'})
        failure = self.run_amp(mixer, config={'amps': ''})
        self.assertIsInstance(failure, self.route.NotIsolated)
        self.assertIn('NOT isolated', failure)
        self.assertTrue(any('NOT confirmed off' in line and 'could not set DACPCM Source' in line
                            for line in self.logs))
        self.assertNotIn(('RCV DACPCM Source', 'ASP_RX1'), mixer.writes)

    def test_dacpcm_zero_that_fails_in_the_kernel_is_not_isolation(self):
        mixer = self.earlier_protected_run(fail={'RCV Digital PCM Volume'})
        orig = mixer.set

        def set_logging_dapm_failure(name, value):
            rc = orig(name, value)
            if name == 'RCV DACPCM Source':
                self.kmsg.append('snd-sm8250 sound: ASoC: RCV DACPCM Source DAPM update failed: -5')
            return rc
        mixer.set = set_logging_dapm_failure
        self.assertIsInstance(self.run_amp(mixer, config={'amps': ''}), self.route.NotIsolated)

    def test_dacpcm_dsp_tx1_that_fails_in_the_kernel_keeps_minus_12_db(self):
        # the DAPM mux put succeeds although the register write failed: only
        # the kernel log shows it, and 409 must not follow
        self.kmsg = [START]
        mixer = FakeMixer(cal={'RCV': 8996})
        orig = mixer.set

        def set_logging_dapm_failure(name, value):
            rc = orig(name, value)
            if (name, value) == ('RCV DACPCM Source', 'DSP_TX1'):
                self.kmsg.append('snd-sm8250 sound: ASoC: RCV DACPCM Source DAPM update failed: -5')
            return rc
        mixer.set = set_logging_dapm_failure
        self.assertIsNone(self.run_amp(mixer))
        self.assertNotIn(('RCV Digital PCM Volume', '409'), mixer.writes)
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertTrue(any('DACPCM Source DSP_TX1 not confirmed' in line for line in self.logs))

    def dapm_mixer(self, hw_fail_writes):
        """DACPCM Source as a DAPM mux over regmap: the put succeeds, the cache
        takes the value, a register write happens only when the cached value
        changes, and a failed one is only logged."""
        mixer = FakeMixer(cal={'RCV': 8996})
        hw, orig, count = {}, mixer.set, {'writes': 0}

        def set_dapm(name, value):
            if name != 'RCV DACPCM Source':
                return orig(name, value)
            mixer.writes.append((name, value))
            if mixer.values.get(name) == value:
                return 0  # no register change: no write, no error
            mixer.values[name] = value
            count['writes'] += 1
            if count['writes'] in hw_fail_writes:
                self.kmsg.append('snd-sm8250 sound: ASoC: RCV DACPCM Source DAPM update failed: -5')
            else:
                hw[name] = value
            return 0
        mixer.set = set_dapm
        return mixer, hw

    def test_rerun_after_a_failed_dsp_tx1_write_writes_it_again(self):
        # an earlier run's DSP_TX1 write failed (cache DSP_TX1, chip ASP_RX1)
        # and was interrupted before its fallback; the rerun must not take
        # the unchanged cache as confirmation
        self.kmsg = [START]
        mixer, hw = self.dapm_mixer(hw_fail_writes=())
        mixer.values['RCV DACPCM Source'] = 'DSP_TX1'
        hw['RCV DACPCM Source'] = 'ASP_RX1'
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(hw['RCV DACPCM Source'], 'DSP_TX1')
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '409')

    def test_failed_zero_write_is_retried_through_dsp_tx1(self):
        mixer, hw = self.dapm_mixer(hw_fail_writes=())
        mixer.fail = {'RCV Digital PCM Volume'}
        mixer.values.update({'RCV Digital PCM Volume': '409', 'RCV DACPCM Source': 'Zero', 'RCV AMP Enable Switch': '1'})
        hw['RCV DACPCM Source'] = 'ASP_RX1'  # an earlier Zero write failed
        failure = self.run_amp(mixer, config={'amps': ''})
        self.assertIn('amplifier muted', failure)
        self.assertEqual(hw['RCV DACPCM Source'], 'Zero')

    def test_resume_failed_by_the_forced_mux_change_goes_direct(self):
        # a rerun during protected playback: DSP_TX1 -> Zero -> DSP_TX1 pauses
        # and resumes the DSP; a resume it missed leaves it silent or wedged
        self.kmsg = [START]
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.set('RCV DSP1 Preload Switch', '1')
        mixer.values['RCV DACPCM Source'] = 'DSP_TX1'
        orig = mixer.set

        def set_failing_resume(name, value):
            rc = orig(name, value)
            if (name, value) == ('RCV DACPCM Source', 'DSP_TX1'):
                self.kmsg.append('snd-sm8250 sound: ASoC: POST_PMU: RCV DSP1 event failed: -5')
            return rc
        mixer.set = set_failing_resume
        self.assertIsNone(self.run_amp(mixer))
        self.assertNotIn(('RCV Digital PCM Volume', '409'), mixer.writes)
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')
        self.assertTrue(any('DSP_TX1 not confirmed' in line and 'POST_PMU' in line for line in self.logs))

    def test_an_older_dapm_failure_does_not_count(self):
        self.kmsg = ['snd-sm8250 sound: ASoC: RCV DACPCM Source DAPM update failed: -5', START]
        mixer = FakeMixer(cal={'RCV': 8996})
        self.assertIsNone(self.run_amp(mixer))
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '409')

    def test_restored_409_is_lowered_before_the_direct_path(self):
        # alsactl restored 0 dB and the amplifier on (an old sanitizer)
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.values.update({'RCV Digital PCM Volume': '409', 'RCV AMP Enable Switch': '1'})
        self.assertIsNone(self.run_amp(mixer, config={'amps': ''}))
        names = [name for name, value in mixer.writes]
        self.assertEqual(mixer.writes[:2], [('RCV Digital PCM Volume', '360'), ('RCV Digital PCM Volume', '361')])
        self.assertLess(names.index('RCV Digital PCM Volume'), names.index('RCV DACPCM Source'))
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '361')
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'ASP_RX1')

    def test_restored_409_with_protection_is_lowered_until_dacpcm_dsp(self):
        self.kmsg = [START]
        mixer = FakeMixer(cal={'RCV': 8996})
        mixer.values.update({'RCV Digital PCM Volume': '409', 'RCV AMP Enable Switch': '1'})
        self.assertIsNone(self.run_amp(mixer))
        volumes = [(i, value) for i, (name, value) in enumerate(mixer.writes) if name == 'RCV Digital PCM Volume']
        dacpcm = mixer.writes.index(('RCV DACPCM Source', 'DSP_TX1'))
        self.assertEqual(volumes[:2], [(0, '360'), (1, '361')])
        self.assertEqual([value for i, value in volumes if i < dacpcm], ['360', '361'])
        self.assertEqual(mixer.values['RCV Digital PCM Volume'], '409')


class Card(AmpBase):
    """route_card(): both amplifiers confirmed at -12 dB before the shared
    route, each enabled only after its path, the playback mixer last."""

    def setUp(self):
        super().setUp()
        self.route.CONFIRM_RETRY_SECONDS = 0

    def test_order(self):
        mixer = FakeMixer(cal={'RCV': 8996, 'SPK': 9096})
        self.assertEqual(self.route.route_card(mixer, {'amps': ''}, self.calibration), [])
        names = [name for name, value in mixer.writes]
        first_route = min(names.index(name) for name, value in self.route.ROUTE)
        for prefix in ('RCV', 'SPK'):
            self.assertLess(names.index(f'{prefix} Digital PCM Volume'), first_route)
            self.assertLess(names.index(f'{prefix} DACPCM Source'), names.index(f'{prefix} AMP Enable Switch'))
            self.assertEqual(mixer.values[f'{prefix} AMP Enable Switch'], '1')
            self.assertEqual(mixer.values[f'{prefix} Digital PCM Volume'], '361')
        self.assertEqual(mixer.writes[-1], (self.route.PLAYBACK_MIXER, '1'))

    def test_one_unconfirmed_amplifier_is_muted_the_other_plays(self):
        mixer = FakeMixer(cal={'RCV': 8996, 'SPK': 9096}, fail={'RCV Digital PCM Volume'})
        mixer.values['RCV Digital PCM Volume'] = '409'
        failed = self.route.route_card(mixer, {'amps': ''}, self.calibration)
        self.assertEqual(len(failed), 1)
        self.assertIn('RCV Digital PCM Volume not confirmed', failed[0])
        self.assertEqual(mixer.values['RCV AMP Enable Switch'], '0')
        self.assertEqual(mixer.values['RCV DACPCM Source'], 'Zero')
        self.assertNotIn(('RCV AMP Enable Switch', '1'), mixer.writes)
        self.assertEqual(mixer.values['SPK AMP Enable Switch'], '1')
        self.assertEqual(mixer.values['SPK DACPCM Source'], 'ASP_RX2')
        self.assertEqual(mixer.values[self.route.PLAYBACK_MIXER], '1')

    def test_an_amplifier_that_cannot_be_muted_stops_the_whole_route(self):
        # earlier boot: 409 behind a DSP, amplifier and mixer on; now its I2C writes fail
        mixer = FakeMixer(cal={'RCV': 8996, 'SPK': 9096},
                          fail={'RCV Digital PCM Volume', 'RCV AMP Enable Switch', 'RCV DACPCM Source'})
        mixer.values.update({'RCV Digital PCM Volume': '409', 'RCV DACPCM Source': 'ASP_RX1',
                             'RCV AMP Enable Switch': '1', self.route.PLAYBACK_MIXER: '1'})
        failed = self.route.route_card(mixer, {'amps': ''}, self.calibration)
        self.assertTrue(any('NOT isolated' in failure for failure in failed))
        self.assertEqual(mixer.values[self.route.PLAYBACK_MIXER], '0')
        self.assertNotIn((self.route.PLAYBACK_MIXER, '1'), mixer.writes)
        for name, value in self.route.ROUTE:
            self.assertNotIn(name, [n for n, v in mixer.writes])
        self.assertNotIn(('SPK AMP Enable Switch', '1'), mixer.writes)
        self.assertTrue(any('MultiMedia1 disconnected' in line for line in self.logs))

    def test_mixer_that_cannot_be_cut_is_reported(self):
        mixer = FakeMixer(cal={'RCV': 8996, 'SPK': 9096},
                          fail={'RCV Digital PCM Volume', 'RCV AMP Enable Switch', 'RCV DACPCM Source',
                                self.route.PLAYBACK_MIXER})
        mixer.values[self.route.PLAYBACK_MIXER] = '1'
        failed = self.route.route_card(mixer, {'amps': ''}, self.calibration)
        self.assertIn(self.route.PLAYBACK_MIXER, failed)
        self.assertTrue(any('could NOT be disconnected' in line for line in self.logs))


# The Linux 7.2.7 (k113) sysfs chain of the card's control device, from
# sound/core/init.c: snd_device_alloc() parents controlC0 to card0, whose
# attribute group (id, number) is the only one with "id"; card0's parent is
# the DT "sound" platform device (snd-sm8250).
K113_CONTROL_CHAIN = (
    dict(kernel='controlC0', subsystem='sound', driver='', attrs={'dev': '116:0'}),
    dict(kernel='card0', subsystem='sound', driver='', attrs={'id': 'ASUSROGPhone5', 'number': '0'}),
    dict(kernel='sound', subsystem='platform', driver='snd-sm8250', attrs={'driver_override': '(null)'}),
    dict(kernel='platform', subsystem='', driver='', attrs={}),
)
PARENT_KEYS = ('KERNELS', 'SUBSYSTEMS', 'DRIVERS', 'ATTRS')
TOKEN = re.compile(r'\s*([A-Z_]+)(?:\{([^}]*)\})?\s*(==|!=|\+=|:=|=)\s*"([^"]*)"\s*,?')


def udev_match(value, pattern):
    return any(fnmatch.fnmatchcase(value, alt) for alt in pattern.split('|'))


def run_udev_rules(text, chain, action='add', existing=()):
    """A small model of systemd-udevd rule matching for the keys these rules
    use; parent keys (KERNELS, SUBSYSTEMS, DRIVERS, ATTRS) must all match on
    one device of the chain, starting with the device itself. Returns the
    IMPORT{program} and RUN commands, in order."""
    lines, programs, skip_to = [], [], None
    for line in text.replace('\\\n', '').splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            lines.append(line)
    dev = chain[0]
    for line in lines:
        tokens = []
        pos = 0
        while pos < len(line):
            match = TOKEN.match(line, pos)
            assert match, f'cannot parse {line[pos:]!r}'
            tokens.append(match.groups())
            pos = match.end()
        if skip_to is not None:
            if ('LABEL', None, '=', skip_to) in tokens:
                skip_to = None
            continue
        own = {'ACTION': action, 'SUBSYSTEM': dev['subsystem'], 'KERNEL': dev['kernel']}
        ok = True
        for key, attr, op, value in tokens:
            if op in ('==', '!=') and key in own:
                ok &= udev_match(own[key], value) == (op == '==')
            elif op in ('==', '!=') and key == 'TEST':
                ok &= (value in existing) == (op == '==')
        parent = [(key, attr, op, value) for key, attr, op, value in tokens if key in PARENT_KEYS]
        if ok and parent:
            def device_matches(device):
                for key, attr, op, value in parent:
                    if key == 'ATTRS':
                        if attr not in device['attrs']:
                            return False
                        have = device['attrs'][attr]
                    else:
                        have = device[{'KERNELS': 'kernel', 'SUBSYSTEMS': 'subsystem', 'DRIVERS': 'driver'}[key]]
                    if udev_match(have, value) != (op == '=='):
                        return False
                return True
            ok = any(device_matches(device) for device in chain)
        if not ok:
            continue
        for key, attr, op, value in tokens:
            if key == 'IMPORT' and attr == 'program' or key == 'RUN':
                programs.append(value)
            elif key == 'GOTO':
                skip_to = value
    return programs


class UdevRules(unittest.TestCase):
    """89-rog5-alsa-state.rules must match the real k113 control device
    (GPT-6.1-Sol audit 2026-10-02: KERNELS!="card*" with ATTRS{id} never
    matched one ancestor, so the sanitizer never ran)."""

    ROOT_COPY = '/usr/local/libexec/rog5-audio-route'
    KIT_COPY = '/run/rog5-platform/audio-route'

    def rules(self, name='89-rog5-alsa-state.rules'):
        return (RULES/name).read_text()

    def test_sanitizer_runs_for_the_rog5_card(self):
        both = (self.ROOT_COPY, self.KIT_COPY)
        self.assertEqual(run_udev_rules(self.rules(), K113_CONTROL_CHAIN, existing=both),
                         [f'{self.ROOT_COPY} --sanitize-alsa-state'])
        self.assertEqual(run_udev_rules(self.rules(), K113_CONTROL_CHAIN, existing=(self.KIT_COPY,)),
                         [f'{self.KIT_COPY} --sanitize-alsa-state'])
        self.assertEqual(run_udev_rules(self.rules(), K113_CONTROL_CHAIN, existing=()), [])

    def test_not_for_other_cards_events_or_devices(self):
        both = (self.ROOT_COPY, self.KIT_COPY)
        other = list(K113_CONTROL_CHAIN)
        other[1] = dict(other[1], attrs={'id': 'Headset', 'number': '1'})
        self.assertEqual(run_udev_rules(self.rules(), other, existing=both), [])
        self.assertEqual(run_udev_rules(self.rules(), K113_CONTROL_CHAIN, action='change', existing=both), [])
        pcm = [dict(K113_CONTROL_CHAIN[0], kernel='pcmC0D0p')] + list(K113_CONTROL_CHAIN[1:])
        self.assertEqual(run_udev_rules(self.rules(), pcm, existing=both), [])
        self.assertEqual(run_udev_rules(self.rules(), K113_CONTROL_CHAIN[1:], existing=both), [])

    def test_model_reproduces_the_old_rule_and_the_route_rule(self):
        old = ('ACTION=="add", SUBSYSTEM=="sound", KERNEL=="controlC*", KERNELS!="card*", '
               'ATTRS{id}=="ASUSROGPhone5", TEST=="/run/rog5-platform/audio-route", '
               'IMPORT{program}="/run/rog5-platform/audio-route --sanitize-alsa-state"\n')
        self.assertEqual(run_udev_rules(old, K113_CONTROL_CHAIN, existing=(self.KIT_COPY,)), [])
        # 91-rog5-audio-route.rules (same match) is known to fire on the phone
        route = self.rules('91-rog5-audio-route.rules').replace('ENV{SYSTEMD_WANTS}+=', 'RUN+=')
        self.assertEqual(run_udev_rules(route, K113_CONTROL_CHAIN), ['rog5-audio-route.service'])

    def test_runs_before_alsa_restore(self):
        self.assertLess('89-rog5-alsa-state.rules', '90-alsa-restore.rules')
        self.assertIn('IMPORT{program}=', self.rules())

    def test_root_copy_is_installed(self):
        rows = [line.split() for line in (REPO/'configs/rootfs/userspace.tsv').read_text().splitlines()
                if line and not line.startswith('#')]
        self.assertIn(['file', 'initramfs/production-audio-route', self.ROOT_COPY, '0755'], rows)


if __name__ == '__main__':
    unittest.main()
