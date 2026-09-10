#!/usr/bin/env python3
"""Stage the reviewed Wi-Fi DT with PMU/PHY/PCIe disabled until S12 qualifies."""
import copy
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

spec = importlib.util.spec_from_file_location('wifi_dtb', Path(__file__).with_name('verify-native-wifi-dtb.py'))
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)
CONSUMER = '/rog5-s12-revote'
PMU = '/wcn6855-pmu'
cell = lambda value: struct.pack('>I', value)

def compose(base, radio):
    wifi.compare(base, radio)
    if CONSUMER in radio:
        raise ValueError('consumer already exists')
    staged = copy.deepcopy(radio)
    for node in (PMU, wifi.PHY, wifi.PCIE):
        staged[node]['status'] = b'disabled\0'
    staged[wifi.S12]['regulator-min-microvolt'] = cell(1224000)
    staged[wifi.S12]['regulator-max-microvolt'] = cell(1360000)
    supply = staged[PMU]['vddpmu-supply']
    if supply != staged[wifi.S12].get('phandle'):
        raise ValueError('wrong shared S12 supply')
    staged[CONSUMER] = {'compatible': b'rog5,s12-revote-diagnostic\0', 'vddpmu-supply': supply}
    return staged

def verify(base, radio, staged):
    if staged != compose(base, radio):
        raise ValueError('staged Wi-Fi delta mismatch')

def main():
    if len(sys.argv) != 4:
        raise SystemExit('usage: stage-native-wifi-dtb.py BASE RADIO NEW_OUTPUT')
    base, radio, output = map(Path, sys.argv[1:])
    if output.exists() or output.is_symlink():
        raise ValueError('output already exists')
    original = wifi.dtb.read_dtb(base)
    live = wifi.dtb.read_dtb(radio)
    expected = compose(original, live)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        candidate = Path(tmp) / 'staged.dtb'
        shutil.copyfile(radio, candidate)
        subprocess.run(['fdtput', '-c', str(candidate), CONSUMER], check=True)
        for node in (PMU, wifi.PHY, wifi.PCIE, wifi.S12, CONSUMER):
            for key, value in expected[node].items():
                if value == live.get(node, {}).get(key):
                    continue
                if key in ('status', 'compatible'):
                    args = ['s', value.rstrip(b'\0').decode()]
                else:
                    args = ['x', *[f'{v:x}' for v in struct.unpack('>' + str(len(value)//4) + 'I', value)]]
                subprocess.run(['fdtput', '-t', args[0], str(candidate), node, key, *args[1:]], check=True)
        verify(original, live, wifi.dtb.read_dtb(candidate))
        with output.open('xb') as target:
            target.write(candidate.read_bytes())
    print('PASS staged Wi-Fi: constraints present at boot, radio nodes disabled')

if __name__ == '__main__':
    main()
