#!/usr/bin/env python3
"""Actual read-only checkpoint functions against explicit temporary sysfs fixtures."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('display_providers', HERE/'display-providers.py')
P = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(P)
BOOT = '11111111-2222-3333-4444-555555555555'


class Providers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-provider-reader-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sys = self.root/'sys'; self.proc = self.root/'proc'
        for name, value in (('SYS', self.sys), ('PROC', self.proc), ('OWNER_UID', os.getuid())):
            mock = patch.object(P, name, value); mock.start(); self.addCleanup(mock.stop)
        for directory in ('devices', 'bus/platform/devices', 'bus/platform/drivers', 'module',
                          'class/backlight', 'class/graphics', 'class/regulator', 'kernel/iommu_groups'):
            (self.sys/directory).mkdir(parents=True, exist_ok=True)
        self.write(self.proc/'sys/kernel/random/boot_id', BOOT+'\n')
        self.write(self.proc/'sys/kernel/osrelease', P.RELEASE+'\n')
        self.calls = []
        self.value = dict(boot_id=BOOT, release=P.RELEASE, exact_artifact='fixture-only')
        for device, (name, compatible) in P.NODES.items():
            real = self.sys/'devices/platform/soc@0'/device; real.mkdir(parents=True)
            (self.sys/'bus/platform/devices'/device).symlink_to(real)
            dt = self.sys/'firmware/devicetree/base/soc@0'/name; dt.mkdir(parents=True)
            self.write(dt/'compatible', compatible); (real/'of_node').symlink_to(dt)
        self.write(self.dt('3d00000.gpu')/'status', b'okay\0')
        for module in ('qcom_refgen_regulator', 'gpucc_sm8350', 'msm'):
            (self.sys/'module'/module).mkdir()
        for device, driver in (('88e7000.regulator', 'qcom-refgen-regulator'),
                               ('3d90000.clock-controller', 'sm8350-gpucc'),
                               ('3da0000.iommu', 'arm-smmu'), ('3d00000.gpu', 'adreno')):
            self.bind(device, driver)
        regulator = self.device('88e7000.regulator')/'regulator/regulator.4'
        regulator.mkdir(parents=True); self.write(regulator/'name', 'refgen\n')
        (self.sys/'class/regulator/regulator.4').symlink_to(regulator)
        self.write(self.dt('88e7000.regulator')/'phandle', bytes.fromhex('00000081'))
        self.write(self.sys/'firmware/devicetree/base/soc@0/display-subsystem@ae00000/dsi@ae94000/refgen-supply', bytes.fromhex('00000081'))
        self.write(self.sys/'firmware/devicetree/base/soc@0/display-subsystem@ae00000/dsi@ae94000/status', b'okay\0')
        self.write(self.dt('3da0000.iommu')/'phandle', bytes.fromhex('00000059'))
        self.write(self.dt('3da0000.iommu')/'#iommu-cells', bytes.fromhex('00000002'))
        for index, (device, streams) in enumerate(P.STREAMS.items()):
            self.write(self.dt(device)/'iommus', streams)
            group = self.sys/'kernel/iommu_groups'/str(index+37)
            (group/'devices').mkdir(parents=True)
            (group/'devices'/device).symlink_to(self.device(device))
            (self.device(device)/'iommu_group').symlink_to(group)
        for name, value in (('modeset', 'Y\n'), ('skip_gpu', 'N\n'), ('separate_gpu_kms', 'N\n')):
            self.write(self.sys/'module/msm/parameters'/name, value)

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def device(self, name): return self.sys/'devices/platform/soc@0'/name
    def dt(self, name): return self.sys/'firmware/devicetree/base/soc@0'/P.NODES[name][0]

    def bind(self, device, driver):
        directory = self.sys/'bus/platform/drivers'/driver; directory.mkdir(exist_ok=True)
        (self.device(device)/'driver').symlink_to(directory)
        (directory/device).symlink_to(self.device(device))

    def identity(self, boot):
        self.assertEqual(boot, BOOT); self.calls.append(boot); return self.value

    def run_check(self, phase='msm', identity=None):
        return P.checkpoint(phase, BOOT, identity or self.identity)

    def refuses(self, reason, phase='msm'):
        before = set(os.listdir('/proc/self/fd'))
        with self.assertRaises((ValueError, OSError)) as error: self.run_check(phase)
        self.assertIn(reason, str(error.exception))
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_all_phases_read_exact_fixtures(self):
        for phase in ('refgen', 'gpucc', 'msm'):
            self.assertIs(self.run_check(phase), True)
        self.assertEqual(len(self.calls), 6)

    def test_gpucc_does_not_require_msm_or_adreno(self):
        (self.device('3d00000.gpu')/'driver').unlink()
        (self.sys/'module/msm').rename(self.root/'inert-msm')
        self.assertIs(self.run_check('gpucc'), True)
        self.assertFalse((self.device('3d6a000.gmu')/'driver').exists())

    def test_presence_without_gpucc_binding_refuses(self):
        (self.device('3d90000.clock-controller')/'driver').unlink()
        self.refuses('driver not bound', 'gpucc')

    def test_unbound_smmu_refuses_without_reprobe(self):
        (self.device('3da0000.iommu')/'driver').unlink()
        self.refuses('driver not bound', 'gpucc')

    def test_msm_requires_adreno_binding(self):
        (self.device('3d00000.gpu')/'driver').unlink()
        self.refuses('driver not bound')

    def test_wrong_driver_refuses(self):
        path = self.device('3da0000.iommu')/'driver'; path.unlink()
        path.symlink_to(self.sys/'bus/platform/drivers/adreno')
        self.refuses('driver not bound')

    def test_driver_reciprocal_link_required(self):
        (self.sys/'bus/platform/drivers/arm-smmu/3da0000.iommu').unlink()
        self.refuses('reciprocal')

    def test_module_symlink_refuses(self):
        path = self.sys/'module/gpucc_sm8350'; path.rmdir(); path.symlink_to(self.sys/'module/msm')
        self.refuses('module absent')

    def test_wrong_group_reciprocal_device_refuses(self):
        link = self.sys/'kernel/iommu_groups/38/devices/3d6a000.gmu'
        link.unlink(); link.symlink_to(self.device('3d00000.gpu'))
        self.refuses('reciprocal')

    def test_missing_gmu_group_refuses(self):
        (self.device('3d6a000.gmu')/'iommu_group').unlink()
        self.refuses('group absent')

    def test_group_outside_expected_tree_refuses(self):
        link = self.device('3d6a000.gmu')/'iommu_group'; link.unlink()
        foreign = self.root/'38'; foreign.mkdir(); link.symlink_to(foreign)
        self.refuses('group ancestry')

    def test_changed_iommu_streams_refuse(self):
        self.write(self.dt('3d6a000.gmu')/'iommus', bytes.fromhex('000000590000000600000400'))
        self.refuses('streams changed')

    def test_changed_provider_phandle_refuses(self):
        self.write(self.dt('3da0000.iommu')/'phandle', bytes.fromhex('00000058'))
        self.refuses('SMMU DT')

    def test_wrong_compatible_refuses(self):
        self.write(self.dt('3d00000.gpu')/'compatible', b'qcom,adreno-650\0')
        self.refuses('compatible')

    def test_disabled_gpu_refuses(self):
        self.write(self.dt('3d00000.gpu')/'status', b'disabled\0')
        self.refuses('GPU status')

    def test_default_enabled_provider_representation_is_pinned(self):
        for device in ('88e7000.regulator', '3d90000.clock-controller', '3da0000.iommu', '3d6a000.gmu'):
            for value in (b'disabled\0', b'okay\0'):
                with self.subTest(device=device, value=value):
                    path = self.dt(device)/'status'; self.write(path, value)
                    self.refuses('default-enabled status'); path.unlink()

    def test_disabled_dsi_refuses(self):
        self.write(self.sys/'firmware/devicetree/base/soc@0/display-subsystem@ae00000/dsi@ae94000/status', b'disabled\0')
        self.refuses('DSI host status')

    def test_wrong_dt_ancestry_refuses(self):
        link = self.device('3d00000.gpu')/'of_node'; link.unlink(); link.symlink_to(self.dt('3d6a000.gmu'))
        self.refuses('DT ancestry')

    def test_refgen_is_exact_dsi_host_supply(self):
        self.write(self.sys/'firmware/devicetree/base/soc@0/display-subsystem@ae00000/dsi@ae94000/refgen-supply', bytes.fromhex('00000082'))
        self.refuses('REFGEN supply', 'refgen')

    def test_duplicate_refgen_refuses(self):
        duplicate = self.sys/'class/regulator/regulator.5'; duplicate.mkdir(); self.write(duplicate/'name', 'refgen\n')
        self.refuses('regulator count', 'refgen')

    def test_refgen_regulator_cannot_belong_to_other_provider(self):
        path = self.sys/'class/regulator/regulator.4'; path.unlink()
        foreign = self.device('3d90000.clock-controller')/'regulator.4'; foreign.mkdir()
        self.write(foreign/'name', 'refgen\n'); path.symlink_to(foreign)
        self.refuses('provider ancestry', 'refgen')

    def test_wrong_boolean_parameters_refuse(self):
        for name in ('modeset', 'skip_gpu', 'separate_gpu_kms'):
            path = self.sys/'module/msm/parameters'/name; saved = path.read_bytes()
            for value in (b'1\n', b'0\n', b'Y', b'true\n', b'N\n' if name == 'modeset' else b'Y\n'):
                with self.subTest(name=name, value=value):
                    self.write(path, value); self.refuses('MSM parameter')
            self.write(path, saved)

    def test_premature_panel_module_refuses(self):
        (self.sys/'module/panel_asus_rog5_ams678').mkdir(); self.refuses('panel present')

    def test_premature_backlight_refuses(self):
        (self.sys/'class/backlight/ae94000.dsi.0').mkdir(); self.refuses('backlight')

    def test_premature_framebuffer_refuses(self):
        (self.sys/'class/graphics/fb0').mkdir(); self.refuses('framebuffer')

    def test_wrong_kernel_refuses(self):
        self.write(self.proc/'sys/kernel/osrelease', 'historical\n'); self.refuses('release changed')

    def test_changed_boot_refuses(self):
        self.write(self.proc/'sys/kernel/random/boot_id', 'different\n'); self.refuses('boot changed')

    def test_identity_mutation_not_hidden_by_same_dict_object(self):
        def identity(boot):
            value = self.identity(boot)
            if len(self.calls) == 2: value['exact_artifact'] = 'different'
            return value
        with self.assertRaisesRegex(ValueError, 'identity changed'): self.run_check(identity=identity)

    def test_identity_rejection_before_reads(self):
        self.value['release'] = 'historical'
        self.refuses('production identity')

    def test_identity_failure_at_end_propagates(self):
        def identity(boot):
            if self.calls: raise ValueError('outer identity rejected')
            return self.identity(boot)
        with self.assertRaisesRegex(ValueError, 'outer identity rejected'): self.run_check(identity=identity)

    def test_symlink_attribute_refuses(self):
        path = self.sys/'module/msm/parameters/modeset'; path.unlink(); path.symlink_to(path.parent/'skip_gpu')
        self.refuses('Too many levels')

    def test_unknown_phase_refuses(self): self.refuses('unknown provider phase', 'execute')


if __name__ == '__main__': unittest.main(verbosity=2)
