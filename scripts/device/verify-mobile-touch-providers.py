#!/usr/bin/env python3
"""Verify the inert ROG5 touch provider contract; no hardware readiness claim."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('touch_dtb_parser', HERE / 'verify-recovery-dtb-delta.py')
PARSER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PARSER)
QUP = '/soc@0/geniqup@9c0000'
I2C, SPI = QUP + '/i2c@990000', QUP + '/spi@990000'
TOUCH = I2C + '/touchscreen@38'
GPI = '/soc@0/dma-controller@900000'
GCC = '/soc@0/clock-controller@100000'
SMMU = '/soc@0/iommu@15000000'
TLMM = '/soc@0/pinctrl@f100000'
GIC = '/soc@0/interrupt-controller@17a00000'
RSC = '/soc@0/rsc@18200000'
REG = RSC + '/regulators-1'
L3, L8, BOB = REG + '/ldo3', REG + '/ldo8', REG + '/bob'
BUS_PINS, TOUCH_PINS = TLMM + '/qup-i2c4-default-state', TLMM + '/rog5-front-touch-active-state'
BUILTINS = ('I2C', 'I2C_QCOM_GENI', 'QCOM_GENI_SE', 'SM_GCC_8350', 'PINCTRL_SM8350',
            'ARM_SMMU', 'ARM_SMMU_QCOM', 'REGULATOR_QCOM_RPMH', 'QCOM_RPMH',
            'QCOM_COMMAND_DB', 'DMA_ENGINE', 'DMA_VIRTUAL_CHANNELS')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cell(*values):
    return struct.pack('>' + 'I' * len(values), *values)


def config_values(text):
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r'(CONFIG_\w+)=(.*)|# (CONFIG_\w+) is not set', line)
        if match:
            key, value = (match[1], match[2]) if match[1] else (match[3], 'n')
            require(key not in values, 'duplicate config assignment: ' + key)
            values[key] = value
    return values


def verify(nodes, config, modules=None):
    PARSER.require_board_identity(nodes, 'touch provider DT')
    owners = {}
    for path, props in nodes.items():
        handles = [props[k] for k in ('phandle', 'linux,phandle') if k in props]
        if handles:
            require(len(handles[0]) == 4 and all(h == handles[0] for h in handles), 'invalid phandle: ' + path)
            handle = struct.unpack('>I', handles[0])[0]
            require(handle not in (0, 0xffffffff) and handle not in owners, 'duplicate/reserved phandle: ' + path)
            owners[handle] = path

    def prop(path, key, expected):
        require(nodes.get(path, {}).get(key) == expected, path + ': incorrect ' + key)

    def handle(path):
        found = [key for key, owner in owners.items() if owner == path]
        require(len(found) == 1, 'missing provider phandle: ' + path)
        return found[0]

    def refs(path, key, *targets):
        prop(path, key, cell(*(value for target, args in targets for value in (handle(target), *args))))

    def available(path):
        while path:
            require(path in nodes and nodes[path].get('status', b'okay\0') in (b'okay\0', b'ok\0'), 'unavailable ancestor/provider: ' + path)
            path = (path.rsplit('/', 1)[0] or '/') if path != '/' else ''

    for path in (TOUCH, I2C, SPI, GPI, L3, L8):
        prop(path, 'status', b'disabled\0')
    for path in (QUP, GCC, SMMU, TLMM, GIC, RSC, REG, BOB):
        available(path)
    for path, compatible in ((QUP, b'qcom,geni-se-qup\0'), (I2C, b'qcom,geni-i2c\0'),
                            (GPI, b'qcom,sm8350-gpi-dma\0qcom,sm6350-gpi-dma\0'),
                            (GCC, b'qcom,gcc-sm8350\0'), (SMMU, b'qcom,sm8350-smmu-500\0arm,mmu-500\0'),
                            (TLMM, b'qcom,sm8350-tlmm\0'), (GIC, b'arm,gic-v3\0'),
                            (TOUCH, b'asus,rog5-mp2-fts3658u\0'), (REG, b'qcom,pm8350c-rpmh-regulators\0'),
                            (RSC, b'asus,rog-phone5-rpmh-apps-rsc\0qcom,rpmh-rsc\0')):
        prop(path, 'compatible', compatible)
    for path, key, count in ((GCC, '#clock-cells', 1), (SMMU, '#iommu-cells', 2),
                             (GPI, '#dma-cells', 3), (TLMM, '#gpio-cells', 2),
                             (TLMM, '#interrupt-cells', 2), (GIC, '#interrupt-cells', 3),
                             (I2C, '#address-cells', 1), (I2C, '#size-cells', 0)):
        prop(path, key, cell(count))
    refs(QUP, 'clocks', (GCC, (121,)), (GCC, (122,)))
    prop(QUP, 'clock-names', b'm-ahb\0s-ahb\0')
    refs(I2C, 'clocks', (GCC, (85,)))
    prop(I2C, 'clock-names', b'se\0')
    refs(I2C, 'pinctrl-0', (BUS_PINS, ()))
    prop(I2C, 'pinctrl-names', b'default\0')
    prop(BUS_PINS, 'pins', b'gpio20\0gpio21\0')
    prop(BUS_PINS, 'function', b'qup4\0')
    prop(I2C, 'interrupts', cell(0, 605, 4))
    for path in (I2C, GPI):
        owner = path
        while 'interrupt-parent' not in nodes[owner] and owner != '/':
            owner = owner.rsplit('/', 1)[0] or '/'
        refs(owner, 'interrupt-parent', (GIC, ()))
    refs(I2C, 'dmas', (GPI, (0, 4, 3)), (GPI, (1, 4, 3)))
    prop(I2C, 'dma-names', b'tx\0rx\0')
    refs(GPI, 'iommus', (SMMU, (0x5b6, 0)))
    refs(QUP, 'iommus', (SMMU, (0x5a3, 0)))
    prop(GPI, 'dma-channels', cell(12))
    prop(GPI, 'dma-channel-mask', cell(0x7e))
    prop(GPI, 'interrupts', cell(*(v for irq in range(244, 256) for v in (0, irq, 4))))
    prop(TOUCH, 'reg', cell(0x38))
    refs(TOUCH, 'interrupt-parent', (TLMM, ()))
    prop(TOUCH, 'interrupts', cell(23, 2))
    refs(TOUCH, 'reset-gpios', (TLMM, (22, 1)))
    refs(TOUCH, 'io-enable-gpios', (TLMM, (131, 0)))
    refs(TOUCH, 'pinctrl-0', (TOUCH_PINS, ()))
    prop(TOUCH_PINS, 'pins', b'gpio22\0gpio23\0')
    prop(TOUCH_PINS, 'function', b'gpio\0')
    refs(TOUCH, 'vdd-supply', (L3, ()))
    refs(TOUCH, 'vcc_i2c-supply', (L8, ()))
    for rail, voltage in ((L3, 3008000), (L8, 1800000)):
        for key in ('regulator-min-microvolt', 'regulator-max-microvolt'):
            prop(rail, key, cell(voltage))
    prop(L8, 'regulator-always-on', b'')
    prop(REG, 'qcom,pmic-id', b'c\0')
    refs(REG, 'vdd-l3-l4-l5-l7-l13-supply', (BOB, ()))
    require('vdd-l2-l8-supply' not in nodes[REG], 'L8 parent differs from reviewed unresolved mapping')
    values = config_values(config)
    for name in BUILTINS:
        require(values.get('CONFIG_' + name) == 'y', 'required built-in missing: CONFIG_' + name)
    require(values.get('CONFIG_QCOM_GPI_DMA') in ('y', 'm'), 'GPI driver unconfigured')
    module_status = 'NOT RUN metadata check'
    if modules is not None and values['CONFIG_QCOM_GPI_DMA'] == 'm':
        require(isinstance(modules, list), 'module metadata must be a list')
        entries = [m for m in modules if isinstance(m, dict) and m.get('name') == 'gpi']
        require(len(entries) == 1, 'expected one GPI module metadata entry')
        entry = entries[0]
        require(entry.get('path', '').endswith('/drivers/dma/qcom/gpi.ko') and
                re.fullmatch('[0-9a-f]{64}', entry.get('sha256', '')) and
                entry.get('depends') == '' and entry.get('firmware') == [], 'GPI metadata contract differs')
        module_status = 'PASS metadata shape/dependencies; module bytes and ABI NOT checked here'
    return {'status': 'PASS_INERT_PROVIDER_CONTRACT', 'configured_drivers': {key: values[key] for key in
            ['CONFIG_' + n for n in BUILTINS] + ['CONFIG_QCOM_GPI_DMA']},
            'gpi_module_metadata': module_status,
            'supply_mapping': {'L3C': 'BOB phandle present; physical power UNKNOWN', 'L8C': 'upstream parent absent; UNKNOWN'},
            'runtime': {'status': 'UNKNOWN; physical NOT RUN',
                        'blockers': ['I2C4/touch/L3C/L8C/GPI0 remain disabled by design',
                                     'Runtime I2C protocol/FIFO/depth unknown; invalid protocol needs wrapper firmware-name and firmware',
                                     'GPI required only when FIFO_IF_DISABLE; channel ownership/IRQ/SMMU attachment unknown',
                                     'FIFO one-byte ID uses FIFO; 62-byte event read may use wrapper SE-DMA, not qualified by ID',
                                     'RPMh CMD-DB ldoc3/ldoc8, upstream rail power and terminal cleanup unknown']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dtb', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--module-metadata', type=Path)
    args = parser.parse_args()
    raw = {'dtb': PARSER.read_dtb_bytes(args.dtb)}
    for name, limit in (('config', 1024 * 1024), ('module_metadata', 8 * 1024 * 1024)):
        path = getattr(args, name)
        if path is not None:
            with path.open('rb') as stream:
                raw[name] = stream.read(limit + 1)
            require(len(raw[name]) <= limit, name + ' exceeds input limit')
    modules = json.loads(raw['module_metadata']) if 'module_metadata' in raw else None
    result = verify(PARSER.parse_dtb(raw['dtb'], str(args.dtb)), raw['config'].decode(), modules)
    result['inputs'] = {name: {'path': str(getattr(args, name)), 'sha256': hashlib.sha256(data).hexdigest()}
                        for name, data in raw.items()}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
