#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

R=Path(__file__).resolve().parents[2]
SCRIPT=R/'scripts/device/start-native-wifi-wpa.sh'

class WpaStartup(unittest.TestCase):
    def test_exact_launcher_uses_supervision_not_unavailable_logging(self):
        source=SCRIPT.read_text()
        function=source[source.index('start_wpa() {'):source.index('\nstart_wpa\n')]
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'args'
            shell=f'''set -eu
root=/run/rog5-native-wifi
state=/run/rog5-wifi-association
interface=wlp1s0
seconds=400
systemd-run() {{ printf '%s\\n' "$@" >{output}; }}
'''+function+'\nstart_wpa\n'
            subprocess.run(['sh','-c',shell],check=True)
            args=output.read_text().splitlines()
        self.assertIn('--property=Type=exec',args)
        self.assertIn('--property=Restart=no',args)
        self.assertIn('--property=RuntimeMaxSec=400s',args)
        index=args.index('/run/rog5-native-wifi/wpa-userspace/sbin/wpa_supplicant')
        self.assertEqual(args[index+1:],['-Dnl80211','-i','wlp1s0','-c','/run/rog5-wifi-association/private-network.conf'])
        for forbidden in ('-f','-B','-P','-K'):self.assertNotIn(forbidden,args[index+1:])
    def test_live_usage_exit_zero_is_not_startup_proof(self):
        fixture=json.loads((R/'tests/fixtures/native-wifi/wpa-no-debug-file.json').read_text())
        self.assertEqual(fixture['program_exit_code'],0)
        self.assertNotIn('f',fixture['observed_synopsis'].split('[')[1].split(']')[0])
        self.assertFalse(fixture['association_occurred'])
        source=SCRIPT.read_text()
        self.assertTrue(source.rstrip().endswith('systemctl is-active --quiet rog5-wifi-wpa.service'))
        self.assertLess(source.index('boot_id'),source.index('\nstart_wpa\n'))
        self.assertIn('0:600:1',source)
        subprocess.run(['sh','-n',str(SCRIPT)],check=True)

if __name__=='__main__':unittest.main()
