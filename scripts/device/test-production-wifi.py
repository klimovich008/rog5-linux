#!/usr/bin/env python3
"""Tests for the production Wi-Fi script and its init publisher.

The radio sequence runs against a temporary sysfs: stub modprobe/rmmod create
and remove /sys/module entries, rog5_wifi_activate makes the PCI endpoint
appear and ath11k_pci creates phy0 and its interface, so the exact order of
the S12 vote, module loads and waits is observable. Set
ROG5_TEST_BUSYBOX/ROG5_TEST_QEMU to run the init publisher under the target
ARM64 busybox.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
WIFI = REPO/'initramfs/production-wifi'
INIT = REPO/'initramfs/persistent-root-init'
UNITS = ('rog5-wifi-radio.service', 'rog5-wifi-wpa.service', 'rog5-wifi-dhcp.service', 'rog5-bluetooth.service')
SOFTWARE = ['sha256', 'aes', 'ctr', 'ccm', 'gcm', 'cmac', 'pwrseq-qcom-wcn', 'pci-pwrctrl-pwrseq', 'mhi', 'qrtr-mhi',
            'rfkill', 'libarc4', 'cfg80211', 'mac80211', 'ath11k']


def unshare_ok():
    return subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0


class Radio(unittest.TestCase):
    def setUp(self):
        self.dir = d = Path(tempfile.mkdtemp(prefix='rog5-wifi-'))
        self.sys = d/'sys'
        self.bin = d/'bin'
        self.bin.mkdir()
        release = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip()
        (d/'tree/lib/modules'/release).mkdir(parents=True)
        power = self.sys/'class/power_supply'
        for name, value in (('qcom-battmgr-bat/health', 'Good'), ('qcom-battmgr-bat/temp', '300'),
                            ('qcom-battmgr-bat/voltage_now', '8000000'), ('qcom-battmgr-bat/capacity', '76'),
                            ('qcom-battmgr-usb/online', '1')):
            (power/name).parent.mkdir(parents=True, exist_ok=True)
            (power/name).write_text(value+'\n')
        (self.sys/'class/thermal/thermal_zone0').mkdir(parents=True)
        (self.sys/'class/thermal/thermal_zone0/temp').write_text('38000\n')
        for disk, ro in (('sda', 0), ('sda23', 0), ('sda24', 1)):
            (self.sys/'class/block'/disk).mkdir(parents=True)
            (self.sys/'class/block'/disk/'ro').write_text(f'{ro}\n')
        (self.sys/'module/firmware_class/parameters').mkdir(parents=True)
        self.firmware = d/'run-firmware'
        self.firmware.mkdir()
        (self.sys/'module/firmware_class/parameters/path').write_text(f'{self.firmware}\n')
        (self.sys/'bus/pci/devices').mkdir(parents=True)
        for path in ('class/net', 'class/ieee80211', 'devices'):
            (self.sys/path).mkdir(parents=True, exist_ok=True)
        (self.sys/'class/net/usb0').mkdir()
        self.kit = d/'kit'
        (self.kit/'firmware/ath11k/WCN6855/hw1.1').mkdir(parents=True)
        (self.kit/'firmware/ath11k/WCN6855/hw1.1/amss.bin').write_bytes(b'amss')
        (self.kit/'firmware/regulatory.db').write_bytes(b'db')
        S = self.sys
        self.stub('modprobe', f'''shift 2; name=$1; shift
echo "modprobe $name $*" >>$D/calls
case $name in
	rog5_s12_ufs_vote) mkdir -p {S}/module/$name; echo 1 >{S}/module/$name/refcnt ;;
	rog5_wifi_activate)
		mkdir -p {S}/module/$name/parameters; cat $D/activate-result 2>/dev/null >{S}/module/$name/parameters/result || echo 0 >{S}/module/$name/parameters/result
		dev={S}/devices/pci0000:00/0000:01:00.0; mkdir -p $dev
		echo 0x17cb >$dev/vendor; echo 0x1103 >$dev/device; echo 0x17cb >$dev/subsystem_vendor
		cat $D/subsystem 2>/dev/null >$dev/subsystem_device || echo 0x0108 >$dev/subsystem_device
		ln -s ../../../devices/pci0000:00/0000:01:00.0 {S}/bus/pci/devices/0000:01:00.0 ;;
	ath11k_pci)
		dev={S}/devices/pci0000:00/0000:01:00.0
		mkdir -p $dev/ieee80211/phy0 $dev/net/wlan0
		ln -s $dev/ieee80211/phy0 {S}/class/ieee80211/phy0
		ln -s $dev/ieee80211/phy0 $dev/net/wlan0/phy80211
		ln -s $dev $dev/net/wlan0/device
		ln -s $dev/net/wlan0 {S}/class/net/wlan0 ;;
esac''')
        self.stub('rmmod', f'echo "rmmod $*" >>$D/calls; rm -r {S}/module/$1')
        self.stub('sleep', 'exit 0')

    def tearDown(self):
        shutil.rmtree(self.dir)

    def stub(self, name, body):
        (self.bin/name).write_text(f'#!/bin/sh\nD={self.dir}\n{body}\n')
        (self.bin/name).chmod(0o755)

    def wifi(self, action):
        # production-wifi resets PATH to the system directories; run it through
        # a copy whose PATH line puts the stubs first.
        script = self.dir/'wifi'
        script.write_text(WIFI.read_text().replace('PATH=/usr/sbin:/usr/bin:/sbin:/bin\n',
                                                   f'PATH={self.bin}:/usr/sbin:/usr/bin:/sbin:/bin\n', 1))
        env = dict(os.environ, ROG5_WIFI_KIT=str(self.kit), ROG5_WIFI_MODULES=str(self.dir/'tree'),
                   ROG5_WIFI_SYS=str(self.sys), ROG5_WIFI_KMSG=str(self.dir/'kmsg'), ROG5_WIFI_RUN=str(self.dir),
                   ROG5_WIFI_COOL_WAIT=getattr(self, 'cool_wait', '0'))
        result = subprocess.run(['unshare', '-r', 'sh', str(script), action], capture_output=True, text=True,
                                env=env, timeout=60)
        kmsg = self.dir/'kmsg'
        return result.returncode, kmsg.read_text() if kmsg.exists() else ''

    def calls(self):
        path = self.dir/'calls'
        return path.read_text().splitlines() if path.exists() else []

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_the_qualified_sequence_brings_up_wlan0(self):
        code, kmsg = self.wifi('radio')
        self.assertEqual(code, 0, kmsg)
        self.assertIn('PASS radio ready on wlan0', kmsg)
        expected = ['modprobe rog5_s12_ufs_vote action=query', 'rmmod rog5_s12_ufs_vote',
                    'modprobe rog5_s12_ufs_vote action=mode', 'rmmod rog5_s12_ufs_vote',
                    'modprobe rog5_s12_ufs_vote action=held-oem']
        expected += [f'modprobe {m} ' for m in SOFTWARE]
        expected += ['modprobe phy-qcom-qmp-pcie ', 'modprobe rog5_wifi_activate ', 'modprobe ath11k_pci ']
        self.assertEqual(self.calls(), expected)
        self.assertEqual((self.firmware/'ath11k/WCN6855/hw1.1/amss.bin').read_bytes(), b'amss')
        self.assertEqual((self.firmware/'regulatory.db').read_bytes(), b'db')
        self.assertTrue((self.kit/'radio-ready').exists())
        self.assertEqual(self.wifi('ready')[0], 0)
        # A second run in the same boot refuses.
        code, kmsg = self.wifi('radio')
        self.assertEqual(code, 1)
        self.assertIn('radio already entered', kmsg)

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_low_battery_without_usb_defers_without_touching_power(self):
        power = self.sys/'class/power_supply'
        (power/'qcom-battmgr-usb/online').write_text('0\n')
        for name, value in (('qcom-battmgr-bat/voltage_now', '6999999'), ('qcom-battmgr-bat/capacity', '14')):
            with self.subTest(name):
                path = power/name
                old = path.read_text()
                path.write_text(value+'\n')
                code, kmsg = self.wifi('radio')
                self.assertEqual(code, 0, kmsg)
                self.assertIn('DEFER on battery', kmsg)
                self.assertIn('below 7.0 V / 15 %', kmsg)
                self.assertEqual(self.calls(), [])
                self.assertNotEqual(self.wifi('ready')[0], 0)
                path.write_text(old)

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_battery_alone_is_enough_when_charged(self):
        (self.sys/'class/power_supply/qcom-battmgr-usb/online').write_text('0\n')
        code, kmsg = self.wifi('radio')
        self.assertEqual(code, 0, kmsg)
        self.assertNotIn('DEFER', kmsg)
        self.assertIn('modprobe ath11k_pci ', self.calls())

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_usb_power_starts_the_radio_even_on_a_low_battery(self):
        (self.sys/'class/power_supply/qcom-battmgr-bat/capacity').write_text('5\n')
        code, kmsg = self.wifi('radio')
        self.assertEqual(code, 0, kmsg)
        self.assertNotIn('DEFER', kmsg)
        self.assertIn('modprobe ath11k_pci ', self.calls())

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_bluetooth_needs_a_ready_radio_then_activates_in_order(self):
        code, kmsg = self.wifi('bluetooth')
        self.assertEqual(code, 1, kmsg)
        self.assertIn('Wi-Fi radio is not ready', kmsg)
        self.assertEqual(self.calls(), [])
        (self.dir/'rog5-wifi').mkdir(exist_ok=True)
        (self.kit/'radio-ready').write_text('')
        S = self.sys
        self.stub('modprobe', f'''shift 2; name=$1; shift
echo "modprobe $name $*" >>$D/calls
case $name in
	rog5_bt_activate) mkdir -p {S}/module/$name/parameters; echo 0 >{S}/module/$name/parameters/result ;;
	hci_uart) mkdir -p {S}/class/bluetooth/hci0 ;;
esac''')
        code, kmsg = self.wifi('bluetooth')
        self.assertEqual(code, 0, kmsg)
        self.assertEqual(self.calls(), ['modprobe rog5_bt_activate ', 'modprobe hci_uart ', 'modprobe hidp ',
                                        'modprobe uhid ', 'modprobe rfcomm ', 'modprobe bnep '])
        self.assertIn('PASS bluetooth hci0', kmsg)
        code, kmsg = self.wifi('bluetooth')
        self.assertEqual(code, 1, kmsg)
        self.assertIn('bluetooth already entered this boot', kmsg)

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_a_boot_heat_spike_waits_for_the_zones_to_cool(self):
        zone = self.sys/'class/thermal/thermal_zone0/temp'
        zone.write_text('62700\n')
        # the kit's sleep cools the zone, standing in for time passing
        self.stub('sleep', f'echo 45000 >{zone}')
        self.cool_wait = '90'
        code, kmsg = self.wifi('radio')
        self.assertEqual(code, 0, kmsg)
        self.assertIn('WAIT thermal zone', kmsg)
        self.assertIn('cooled below 60 C after 2s', kmsg)
        self.assertIn('modprobe ath11k_pci ', self.calls())

    @unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
    def test_failures_stop_before_the_radio_binds(self):
        cases = [
            ('write scope is sda sda23 sda24', lambda: (self.sys/'class/block/sda24/ro').write_text('0\n'), 0),
            ('thermal zone', lambda: (self.sys/'class/thermal/thermal_zone0/temp').write_text('61000\n'), 0),
            ('radio activation result', lambda: (self.dir/'activate-result').write_text('-1\n'), None),
            ('PCI endpoint identity', lambda: (self.dir/'subsystem').write_text('0x0000\n'), None),
            ('already holds Wi-Fi files', lambda: (self.firmware/'regulatory.db').write_text('x'), 0),
        ]
        for why, breakit, calls in cases:
            with self.subTest(why):
                self.tearDown()
                self.setUp()
                breakit()
                code, kmsg = self.wifi('radio')
                self.assertEqual(code, 1, kmsg)
                self.assertIn(why, kmsg)
                self.assertNotIn('modprobe ath11k_pci ', self.calls())
                if calls is not None:
                    self.assertEqual(len(self.calls()), calls)


def publish_function(kit, run):
    body = re.search(r'^prepare_wifi_services\(\) \{\n.*?^\}\n', INIT.read_text(), re.M | re.S).group(0)
    assert body.count('\tkit=/rog5-wifi\n') == 1 and body.count('\trun=/run\n') == 1
    return body.replace('\tkit=/rog5-wifi\n', f'\tkit={kit}\n').replace('\trun=/run\n', f'\trun={run}\n')


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Publish(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-wifi-publish-'))
        self.kit, self.run = self.dir/'kit', self.dir/'run'
        self.run.mkdir()
        self.kit.mkdir(mode=0o700)
        (self.kit/'firmware/ath11k').mkdir(parents=True)
        (self.kit/'firmware/ath11k/amss.bin').write_bytes(b'amss')
        (self.kit/'wifi').write_bytes(WIFI.read_bytes())
        (self.kit/'wifi').chmod(0o755)
        for unit in UNITS:
            (self.kit/unit).write_bytes((REPO/'configs/systemd'/unit).read_bytes())
            (self.kit/unit).chmod(0o644)

    def tearDown(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.dir)])
        shutil.rmtree(self.dir)

    def publish(self):
        shell, env = ['sh'], dict(os.environ)
        if os.environ.get('ROG5_TEST_BUSYBOX'):
            qemu, busybox = os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX']
            tools = self.dir/'applets'
            tools.mkdir(exist_ok=True)
            for name in ('cp', 'find', 'ln', 'mkdir', 'stat'):
                (tools/name).write_text(f'#!/bin/sh\nexec {qemu} {busybox} {name} "$@"\n')
                (tools/name).chmod(0o755)
            shell, env['PATH'] = [qemu, busybox, 'sh'], f'{tools}:{env["PATH"]}'
        script = publish_function(self.kit, self.run)+'prepare_wifi_services\n'
        return subprocess.run(['unshare', '-r', *shell, '-c', script], capture_output=True, text=True,
                              env=env, timeout=120).returncode

    def test_kit_is_published_and_units_enabled(self):
        self.assertEqual(self.publish(), 0)
        self.assertEqual((self.run/'rog5-wifi/firmware/ath11k/amss.bin').read_bytes(), b'amss')
        self.assertEqual(oct((self.run/'rog5-wifi').stat().st_mode & 0o777), '0o700')
        for unit in UNITS:
            self.assertEqual(os.readlink(self.run/'systemd/system/multi-user.target.wants'/unit), '../'+unit)

    def test_absent_kit_is_a_no_op(self):
        shutil.rmtree(self.kit)
        self.assertEqual(self.publish(), 0)
        self.assertEqual(list(self.run.iterdir()), [])

    def test_writable_or_linked_payload_is_refused(self):
        (self.kit/'firmware/ath11k/amss.bin').chmod(0o666)
        self.assertEqual(self.publish(), 1)
        (self.kit/'firmware/ath11k/amss.bin').chmod(0o644)
        (self.kit/'firmware/link').symlink_to('/etc/shadow')
        self.assertEqual(self.publish(), 1)
        self.assertFalse((self.run/'rog5-wifi').exists())


class Units(unittest.TestCase):
    def test_wpa_dhcp_and_bluetooth_run_only_after_a_ready_radio(self):
        bt = (REPO/'configs/systemd/rog5-bluetooth.service').read_text()
        self.assertIn('rog5-wifi-radio.service', re.search(r'^After=(.*)$', bt, re.M).group(1))
        for unit in ('rog5-wifi-wpa.service', 'rog5-wifi-dhcp.service', 'rog5-bluetooth.service'):
            self.assertIn('ExecCondition=/run/rog5-wifi/wifi ready', (REPO/'configs/systemd'/unit).read_text())
        radio = (REPO/'configs/systemd/rog5-wifi-radio.service').read_text()
        self.assertIn('rog5-platform-modules.service', re.search(r'^After=(.*)$', radio, re.M).group(1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
