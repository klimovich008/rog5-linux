#!/usr/bin/env python3
"""Preserve the native-root DT outside the reviewed WCN6855 addition."""
import importlib.util
from pathlib import Path
import struct
import sys

spec = importlib.util.spec_from_file_location('dtb', Path(__file__).with_name('verify-recovery-dtb-delta.py'))
dtb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dtb)
RSC = '/soc@0/rsc@18200000'
TLMM = '/soc@0/pinctrl@f100000'
PCIE = '/soc@0/pcie@1c00000'
PHY = '/soc@0/phy@1c06000'
S11 = RSC + '/regulators-0/smps11'
S12 = RSC + '/regulators-0/smps12'
S1C = RSC + '/regulators-1/smps1'
ADDITIONS = (
    '/wcn6855-pmu', PCIE + '/pcie@0/wifi@0',
    RSC + '/regulators-0/smps10', RSC + '/regulators-0/smps12',
    RSC + '/regulators-2', TLMM + '/wlan-en-state',
    TLMM + '/bt-en-state', TLMM + '/wlan-antenna-state',
    TLMM + '/pcie0-default-state',
)
CHANGES = {
    S11: {'regulator-min-microvolt', 'regulator-max-microvolt'},
    S1C: {'regulator-min-microvolt'},
    RSC + '/regulators-0': {'vdd-s10-supply', 'vdd-s12-supply'},
    PCIE: {'status', 'perst-gpios', 'wake-gpios', 'pinctrl-0', 'pinctrl-names'},
    PHY: {'status', 'vdda-phy-supply', 'vdda-pll-supply'},
}

def first_voltage_selector(minimum, maximum, base=320000, step=8000, last=215):
    selector = max(0, (minimum - base + step - 1) // step)
    value = base + selector * step
    if selector > last or value > maximum:
        raise ValueError('voltage window has no mainline regulator selector')
    return value

def compare(base, candidate):
    for path, props in base.items():
        if path not in candidate:
            raise ValueError(f'removed native node: {path}')
        for key in props.keys() | candidate[path].keys():
            if props.get(key) == candidate[path].get(key):
                continue
            if path == '/__symbols__' and key not in props:
                destination = candidate[path][key].rstrip(b'\0').decode('ascii')
                if destination not in candidate or not any(destination == root or destination.startswith(root + '/') for root in ADDITIONS):
                    raise ValueError('new symbol escaped Wi-Fi additions')
                continue
            if key not in CHANGES.get(path, set()):
                raise ValueError(f'changed native property: {path}:{key}')
    for path in candidate.keys() - base.keys():
        if not any(path == root or path.startswith(root + '/') for root in ADDITIONS):
            raise ValueError(f'unrelated added node: {path}')
    for path, key, value in (
        (S11, 'regulator-min-microvolt', 1012000),
        (S11, 'regulator-max-microvolt', 1016000),
        (S12, 'regulator-min-microvolt', 1350000),
        (S12, 'regulator-max-microvolt', 1352000),
        (S12, 'regulator-initial-mode', 0),
        (S1C, 'regulator-min-microvolt', 1900000),
        (S1C, 'regulator-max-microvolt', 1952000),
    ):
        if candidate[path].get(key) != struct.pack('>I', value):
            raise ValueError(f'wrong WW33 rail request: {path}:{key}')
    for path in (PCIE, PHY):
        if candidate[path].get('status') != b'okay\0':
            raise ValueError(f'Wi-Fi path disabled: {path}')
    # PM8350 smps11 uses pmic5_hfsmps510 in the exact kernel: 320 mV + 8 mV*n.
    # A literal vendor request can fall between selectors in the mainline API.
    for path in (S11, S12):
        minimum = struct.unpack('>I', candidate[path]['regulator-min-microvolt'])[0]
        maximum = struct.unpack('>I', candidate[path]['regulator-max-microvolt'])[0]
        first_voltage_selector(minimum, maximum)
    if 'output-low' in candidate[TLMM + '/wlan-en-state']:
        raise ValueError('WLAN_EN would be forced low before sequencing')
    if candidate['/wcn6855-pmu'].get('compatible') != b'qcom,wcn6855-pmu\0':
        raise ValueError('wrong PMU')
    if candidate[PCIE + '/pcie@0/wifi@0'].get('compatible') != b'pci17cb,1103\0':
        raise ValueError('wrong PCI endpoint')

if __name__ == '__main__':
    try:
        compare(dtb.read_dtb(Path(sys.argv[1])), dtb.read_dtb(Path(sys.argv[2])))
        print('PASS native Wi-Fi delta preserves unrelated DT state and uses stock-derived selector-valid rails')
    except (ValueError, KeyError, IndexError) as error:
        raise SystemExit(f'FAIL {error}')
