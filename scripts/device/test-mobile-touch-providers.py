#!/usr/bin/env python3
"""Hostile mutations of the fixed inert-touch contract; optional actual DT input."""
import copy
import importlib.util
import os
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('touch_providers', Path(__file__).with_name('verify-mobile-touch-providers.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def fixture():
    # Minimal semantic projection of composition/run-r2; this is not a boot DT.
    n = {'/': {'compatible': b'asus,rog-phone5\0qcom,sm8350\0'}, '/soc@0': {}}
    paths = [M.QUP, M.I2C, M.SPI, M.TOUCH, M.GPI, M.GCC, M.SMMU, M.TLMM,
             M.GIC, M.RSC, M.REG, M.L3, M.L8, M.BOB, M.BUS_PINS, M.TOUCH_PINS]
    for index, path in enumerate(paths, 1):
        n[path] = {'phandle': M.cell(index)}
    def put(p, **props): n[p].update({k.replace('_', '-'): v for k, v in props.items()})
    def ref(p, key, *args): n[p][key] = b''.join(n[t]['phandle'] + M.cell(*cells) for t, cells in args)
    for p in (M.TOUCH, M.I2C, M.SPI, M.GPI, M.L3, M.L8): put(p, status=b'disabled\0')
    compatibles = ['qcom,geni-se-qup', 'qcom,geni-i2c', 'qcom,geni-spi', 'asus,rog5-mp2-fts3658u',
                   'qcom,sm8350-gpi-dma\0qcom,sm6350-gpi-dma', 'qcom,gcc-sm8350',
                   'qcom,sm8350-smmu-500\0arm,mmu-500', 'qcom,sm8350-tlmm', 'arm,gic-v3',
                   'asus,rog-phone5-rpmh-apps-rsc\0qcom,rpmh-rsc', 'qcom,pm8350c-rpmh-regulators']
    for p, compatible in zip(paths, compatibles): put(p, compatible=(compatible + '\0').encode())
    for p, key, count in ((M.GCC, '#clock-cells', 1), (M.SMMU, '#iommu-cells', 2), (M.GPI, '#dma-cells', 3),
                          (M.TLMM, '#gpio-cells', 2), (M.TLMM, '#interrupt-cells', 2), (M.GIC, '#interrupt-cells', 3),
                          (M.I2C, '#address-cells', 1), (M.I2C, '#size-cells', 0)):
        n[p][key] = M.cell(count)
    ref(M.QUP, 'clocks', (M.GCC, (121,)), (M.GCC, (122,)))
    put(M.QUP, clock_names=b'm-ahb\0s-ahb\0')
    ref(M.I2C, 'clocks', (M.GCC, (85,)))
    put(M.I2C, clock_names=b'se\0', pinctrl_names=b'default\0', interrupts=M.cell(0,605,4), dma_names=b'tx\0rx\0')
    ref(M.I2C, 'pinctrl-0', (M.BUS_PINS, ()))
    put(M.BUS_PINS, pins=b'gpio20\0gpio21\0', function=b'qup4\0')
    ref('/', 'interrupt-parent', (M.GIC, ()))
    ref(M.I2C, 'dmas', (M.GPI,(0,4,3)), (M.GPI,(1,4,3)))
    ref(M.GPI, 'iommus', (M.SMMU,(0x5b6,0)))
    ref(M.QUP, 'iommus', (M.SMMU,(0x5a3,0)))
    put(M.GPI, dma_channels=M.cell(12), dma_channel_mask=M.cell(0x7e),
        interrupts=M.cell(*(v for irq in range(244,256) for v in (0,irq,4))))
    put(M.TOUCH, reg=M.cell(0x38), interrupts=M.cell(23,2))
    for key, target, cells in [('interrupt-parent',M.TLMM,()), ('reset-gpios',M.TLMM,(22,1)),
                              ('io-enable-gpios',M.TLMM,(131,0)), ('pinctrl-0',M.TOUCH_PINS,()),
                              ('vdd-supply',M.L3,()), ('vcc_i2c-supply',M.L8,())]: ref(M.TOUCH,key,(target,cells))
    put(M.TOUCH_PINS, pins=b'gpio22\0gpio23\0', function=b'gpio\0')
    for p, voltage in ((M.L3,3008000),(M.L8,1800000)):
        put(p, regulator_min_microvolt=M.cell(voltage), regulator_max_microvolt=M.cell(voltage))
    put(M.L8, regulator_always_on=b'')
    n[M.REG]['qcom,pmic-id'] = b'c\0'
    ref(M.REG, 'vdd-l3-l4-l5-l7-l13-supply', (M.BOB,()))
    return n


class Providers(unittest.TestCase):
    def setUp(self):
        self.nodes = M.PARSER.read_dtb(Path(os.environ['ROG5_MOBILE_DTB'])) if os.environ.get('ROG5_MOBILE_DTB') else fixture()
        self.config = '\n'.join('CONFIG_' + key + '=y' for key in M.BUILTINS) + '\nCONFIG_QCOM_GPI_DMA=m\n'

    def test_inert_valid_is_not_runtime_pass(self):
        report = M.verify(self.nodes, self.config)
        self.assertEqual(report['status'], 'PASS_INERT_PROVIDER_CONTRACT')
        self.assertIn('UNKNOWN', report['runtime']['status'])
        self.assertIn('NOT RUN', report['gpi_module_metadata'])
        self.assertIn('absent', report['supply_mapping']['L8C'])

    def test_hostile_properties(self):
        cases = [(M.I2C,'clocks',M.cell(0xffffffff,85)), (M.GCC,'#clock-cells',M.cell(2)),
                 (M.QUP,'clocks',self.nodes[M.GCC]['phandle'] + M.cell(121)),
                 (M.I2C,'dmas',self.nodes[M.GPI]['phandle'] + M.cell(0,5,3)),
                 (M.I2C,'interrupts',M.cell(0,605,1)), (M.BUS_PINS,'function',b'gpio\0'),
                 (M.BUS_PINS,'pins',b'gpio20\0gpio22\0'), (M.GPI,'dma-channel-mask',M.cell(0x10)),
                 (M.GPI,'iommus',self.nodes[M.SMMU]['phandle'] + M.cell(0x5a3,0)),
                 (M.QUP,'iommus',self.nodes[M.SMMU]['phandle'] + M.cell(0x5b6,0)),
                 (M.GPI,'interrupts',M.cell(0,244,4)), (M.SMMU,'status',b'disabled\0'),
                 (M.TOUCH,'reset-gpios',self.nodes[M.TLMM]['phandle'] + M.cell(22,0)),
                 (M.REG,'vdd-l3-l4-l5-l7-l13-supply',self.nodes[M.L8]['phandle']),
                 (M.REG,'vdd-l2-l8-supply',self.nodes[M.BOB]['phandle']),
                 (M.TLMM,'phandle',self.nodes[M.GCC]['phandle']),
                 ('/','status',b'disabled\0'), (M.RSC,'compatible',b'qcom,rpmh-rsc\0'),
                 (M.REG,'qcom,pmic-id',b'b\0')]
        cases += [(p,'status',b'okay\0') for p in (M.TOUCH,M.I2C,M.SPI,M.GPI,M.L3,M.L8)]
        for path,key,value in cases:
            with self.subTest(path=path,key=key):
                nodes = copy.deepcopy(self.nodes); nodes[path][key] = value
                with self.assertRaises(ValueError): M.verify(nodes,self.config)

    def test_config_missing_and_duplicate(self):
        for config in [self.config.replace('CONFIG_I2C_QCOM_GENI=y','CONFIG_I2C_QCOM_GENI=m'),
                       self.config.replace('CONFIG_QCOM_GPI_DMA=m','CONFIG_QCOM_GPI_DMA=n'),
                       self.config + '# CONFIG_I2C_QCOM_GENI is not set\n',
                       '# CONFIG_I2C_QCOM_GENI is not set\n' + self.config]:
            with self.assertRaises(ValueError): M.verify(self.nodes,config)

    def test_module_metadata_truth(self):
        good = {'name':'gpi','path':'modules/kernel/drivers/dma/qcom/gpi.ko','sha256':'a'*64,'depends':'','firmware':[]}
        self.assertIn('bytes and ABI NOT',M.verify(self.nodes,self.config,[good])['gpi_module_metadata'])
        for bad in ([], [good,good], [{**good,'firmware':['unknown']}], [{**good,'sha256':'bad'}]):
            with self.assertRaises(ValueError): M.verify(self.nodes,self.config,bad)


if __name__ == '__main__':
    unittest.main()
