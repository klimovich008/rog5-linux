#!/usr/bin/env python3
"""Production endpoint on temporary sysfs: no real device or privilege operation."""
import ast
import copy
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('production_endpoint', HERE/'display-endpoint.py')
E = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(E)
BOOT = '11111111-2222-3333-4444-555555555555'


class EndpointFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-production-endpoint-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sys = self.root/'sys'; self.proc = self.root/'proc'; self.descriptor = self.root/'trial-descriptor'
        for key, value in (('SYS', self.sys), ('PROC', self.proc), ('DESCRIPTOR', self.descriptor)):
            p = patch.object(E, key, value); p.start(); self.addCleanup(p.stop)
        # Ownership and effective UID are explicit fixtures. All actual reads,
        # pathname checks, held descriptors and zero writes use temporary files.
        self.owner_uid = 0; self.owner_gid = 0
        for key in ('fstat', 'stat'):
            original = getattr(os, key)
            def owned(*args, _call=original, **kwargs):
                result = _call(*args, **kwargs)
                fields = {name: getattr(result, name) for name in dir(result) if name.startswith('st_')}
                fields.update(st_uid=self.owner_uid, st_gid=self.owner_gid)
                return types.SimpleNamespace(**fields)
            p = patch.object(E.os, key, side_effect=owned); p.start(); self.addCleanup(p.stop)
        p = patch.object(E.os, 'geteuid', return_value=0); p.start(); self.addCleanup(p.stop)
        self.write(self.descriptor, b'inert fixture descriptor\n')
        self.identity_record = dict(boot_id=BOOT, release=E.RELEASE, bundle='fixture-production',
                                    descriptor_sha256=hashlib.sha256(self.descriptor.read_bytes()).hexdigest(),
                                    board_dtb_sha256=E.BOARD, owner='a'*32)
        self.calls = 0
        self.endpoint = E.Endpoint(self.identity_check)
        self.write(self.proc/'sys/kernel/random/boot_id', BOOT+'\n')
        self.write(self.proc/'sys/kernel/osrelease', E.RELEASE+'\n')
        self.write(self.proc/'cmdline', 'console=tty0 rog5.bundle=fixture-production quiet\n')
        self.display = self.sys/'devices/platform/soc@0/ae00000.display-subsystem'
        self.panel = self.display/'ae94000.dsi'/E.NAME
        self.backlight = self.panel/'backlight'/E.NAME
        self.backlight.mkdir(parents=True)
        self.master = self.display/'ae01000.display-controller'
        self.fb = self.master/'graphics/fb0'; self.fb.mkdir(parents=True)
        for directory in ('class/backlight', 'class/graphics', 'bus/platform/devices',
                          'bus/platform/drivers/msm_dpu', 'bus/mipi-dsi/drivers/'+E.DRIVER):
            (self.sys/directory).mkdir(parents=True)
        self.symlink(self.sys/'class/backlight'/E.NAME, self.backlight)
        self.symlink(self.backlight/'device', self.panel)
        self.symlink(self.panel/'driver', self.sys/'bus/mipi-dsi/drivers'/E.DRIVER)
        self.symlink(self.sys/'bus/mipi-dsi/drivers'/E.DRIVER/E.NAME, self.panel)
        panel_dt = self.sys/'firmware/devicetree/base'/E.PANEL_DT
        self.write(panel_dt/'compatible', b'asus,rog5-ams678-er2\0')
        self.symlink(self.panel/'of_node', panel_dt)
        self.write(self.backlight/'max_brightness', '1023\n'); self.write(self.backlight/'type', 'raw\n')
        self.write(self.backlight/'brightness', '0\n')
        self.symlink(self.sys/'class/graphics/fb0', self.fb)
        self.symlink(self.fb/'device', self.master)
        self.symlink(self.sys/'bus/platform/devices/ae01000.display-controller', self.master)
        self.symlink(self.master/'driver', self.sys/'bus/platform/drivers/msm_dpu')
        self.symlink(self.sys/'bus/platform/drivers/msm_dpu/ae01000.display-controller', self.master)
        master_dt = self.sys/'firmware/devicetree/base'/E.DPU_DT; master_dt.mkdir(parents=True)
        self.symlink(self.master/'of_node', master_dt)
        for name, value in (('name', 'msmdrmfb\n'), ('virtual_size', '1080,2448\n'),
                            ('modes', 'U:1080x2448p-60\n'), ('bits_per_pixel', '32\n')):
            self.write(self.fb/name, value)
        for name in ('qcom_refgen_regulator', 'gpucc_sm8350', 'msm', 'panel_asus_rog5_ams678'):
            (self.sys/'module'/name).mkdir(parents=True)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.encode() if isinstance(value, str) else value)

    def symlink(self, path, target):
        path.parent.mkdir(parents=True, exist_ok=True); path.symlink_to(target)

    def identity_check(self, boot):
        self.assertEqual(boot, BOOT); self.calls += 1; return self.identity_record

    def check(self, method='identity'):
        if method == 'blank': return self.endpoint.blank(BOOT, lambda: True)
        return getattr(self.endpoint, method)(BOOT)

    def refuses(self, reason, method='identity'):
        before = set(os.listdir('/proc/self/fd'))
        with self.assertRaises((ValueError, OSError)) as error: self.check(method)
        self.assertIn(reason, str(error.exception))
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def mutant(self, reason):
        # Mutate one production guard, never a rewritten endpoint model. The
        # normal refusal tests must reject the same input this control admits.
        tree = ast.parse((HERE/'display-endpoint.py').read_text()); matches = 0
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'need' and len(node.args) == 2
                    and isinstance(node.args[1], ast.Constant) and node.args[1].value == reason):
                node.args[0] = ast.Constant(True); matches += 1
        self.assertEqual(matches, 1)
        module = types.ModuleType('guard_removed_endpoint')
        exec(compile(ast.fix_missing_locations(tree), 'guard-removed-endpoint', 'exec'), module.__dict__)
        module.SYS = self.sys; module.PROC = self.proc; module.DESCRIPTOR = self.descriptor
        return module.Endpoint(self.identity_check)

    def test_success_metadata_zero_and_identity(self):
        self.assertEqual(self.check(), self.identity_record)
        self.assertEqual(self.check('backlight')['brightness'], 0)
        result = self.check('blank')
        self.assertEqual(result['status'], 'PASS_ZERO_BRIGHTNESS_COMMAND')
        self.assertFalse(result['physical_darkness_verified'])
        result = self.check('framebuffer')
        self.assertEqual(result['status'], 'PASS_FRAMEBUFFER_SYSFS')
        self.assertFalse(result['device_opened']); self.assertFalse(result['physical_scanout_verified'])

    def test_bundle_exactly_one_correct_token(self):
        for value in ('quiet', 'rog5.bundle=other', 'rog5.bundle=fixture-production rog5.bundle=fixture-production',
                      'rog5.bundle=fixture-production rog5.bundle=other', 'rog5.bundle=fixture-productionx'):
            with self.subTest(value=value):
                self.write(self.proc/'cmdline', value); self.refuses('bundle command line')

    def test_mutation_missing_bundle_check_admits_duplicate(self):
        self.write(self.proc/'cmdline', 'rog5.bundle=fixture-production rog5.bundle=fixture-production')
        self.refuses('bundle command line')
        self.assertEqual(self.mutant('bundle command line mismatch').identity(BOOT), self.identity_record)

    def test_invalid_identity_schema_and_values(self):
        original = copy.deepcopy(self.identity_record)
        for key, value in (('owner', 'a'*31), ('owner', 'G'*32), ('bundle', 'with space'),
                           ('bundle', 'a'*97), ('bundle', 'é'), ('descriptor_sha256', 'a'*63),
                           ('board_dtb_sha256', 'a'*64), ('release', 'historical'), ('boot_id', 'wrong')):
            with self.subTest(key=key, value=value):
                self.identity_record = dict(original, **{key:value})
                with self.assertRaises(ValueError): self.check()
        self.identity_record = dict(original, extra='unadmitted'); self.refuses('schema')

    def test_nonroot_refuses_before_callback(self):
        with patch.object(E.os, 'geteuid', return_value=1000): self.refuses('requires root')
        self.assertEqual(self.calls, 0)

    def test_wrong_boot_and_kernel(self):
        self.write(self.proc/'sys/kernel/random/boot_id', 'different\n'); self.refuses('boot changed')
        self.write(self.proc/'sys/kernel/random/boot_id', BOOT+'\n')
        self.write(self.proc/'sys/kernel/osrelease', 'old\n'); self.refuses('kernel changed')

    def test_descriptor_wrong_owner_or_group_refuses(self):
        self.owner_uid = 1000; self.refuses('type/owner')
        self.owner_uid = 0; self.owner_gid = 1000; self.refuses('descriptor metadata')

    def test_descriptor_writable_or_oversize_refuses(self):
        self.descriptor.chmod(0o666); self.refuses('descriptor metadata')
        self.descriptor.chmod(0o644); self.write(self.descriptor, b'x'*1025); self.refuses('descriptor metadata')

    def test_descriptor_hash_mismatch_refuses(self):
        self.write(self.descriptor, b'changed'); self.refuses('descriptor changed')

    def test_descriptor_symlink_refuses(self):
        original = self.root/'descriptor-data'; self.descriptor.rename(original)
        self.descriptor.symlink_to(original); self.refuses('Too many levels')

    def test_descriptor_replacement_during_read_refuses(self):
        original = os.read; replaced = False
        def raced(fd, size):
            nonlocal replaced
            data = original(fd, size)
            if not replaced and os.readlink('/proc/self/fd/'+str(fd)) == str(self.descriptor):
                replaced = True; self.descriptor.rename(self.root/'old-descriptor')
                self.descriptor.write_bytes(data)
            return data
        with patch.object(E.os, 'read', side_effect=raced): self.refuses('replaced/changed')

    def test_callback_mutation_sticky_binding(self):
        result = self.check(); result['owner'] = 'c'*32
        self.assertEqual(self.check()['owner'], 'a'*32)
        self.identity_record['owner'] = 'b'*32; self.refuses('admitted identity changed')

    def test_failed_initial_check_does_not_bind(self):
        self.write(self.proc/'cmdline', 'wrong'); self.refuses('bundle')
        self.identity_record['owner'] = 'b'*32
        self.write(self.proc/'cmdline', 'rog5.bundle=fixture-production')
        self.assertEqual(self.check()['owner'], 'b'*32)

    def test_callback_refusal_propagates(self):
        self.endpoint.identity_check = lambda boot: (_ for _ in ()).throw(ValueError('outer denied'))
        self.refuses('outer denied')

    def test_backlight_range_type_and_value(self):
        for name, value, reason in (('max_brightness','4095\n','range/type'), ('type','platform\n','range/type'),
                                    ('brightness','1024\n','brightness value'), ('brightness','00\n','brightness value')):
            path = self.backlight/name; original = path.read_bytes()
            with self.subTest(name=name, value=value):
                self.write(path,value); self.refuses(reason,'backlight')
            self.write(path,original)

    def test_missing_current_modules(self):
        for name in ('gpucc_sm8350','msm','qcom_refgen_regulator','panel_asus_rog5_ams678'):
            path = self.sys/'module'/name; path.rmdir()
            self.refuses('module absent','backlight'); path.mkdir()

    def test_wrong_panel_driver_or_reciprocal(self):
        path = self.panel/'driver'; path.unlink(); path.symlink_to(self.sys/'bus/platform/drivers/msm_dpu')
        self.refuses('link changed','backlight')

    def test_wrong_panel_dt(self):
        path=self.panel/'of_node'; path.unlink(); path.symlink_to(self.sys/'firmware/devicetree/base'/E.DPU_DT)
        self.refuses('link changed','backlight')

    def test_additional_backlight_refuses(self):
        (self.sys/'class/backlight/unexpected').mkdir(); self.refuses('inventory','backlight')

    def test_same_mdss_but_wrong_framebuffer_parent_refuses(self):
        foreign=self.display/'wrong-controller/graphics/fb0'; foreign.mkdir(parents=True)
        for child in self.fb.iterdir():
            if child.is_file(): self.write(foreign/child.name, child.read_bytes())
        path=self.sys/'class/graphics/fb0'; path.unlink(); path.symlink_to(foreign)
        self.refuses('exact DPU parent','framebuffer')

    def test_mutation_missing_exact_parent_admits_same_mdss_sibling(self):
        foreign = self.display/'wrong-controller/graphics/fb0'; foreign.mkdir(parents=True)
        for child in self.fb.iterdir():
            if child.is_file(): self.write(foreign/child.name, child.read_bytes())
        self.symlink(foreign/'device', self.master)
        path = self.sys/'class/graphics/fb0'; path.unlink(); path.symlink_to(foreign)
        self.refuses('exact DPU parent','framebuffer')
        self.assertEqual(self.mutant('framebuffer exact DPU parent').framebuffer(BOOT)['status'],
                         'PASS_FRAMEBUFFER_SYSFS')

    def test_wrong_framebuffer_device_link(self):
        path=self.fb/'device'; path.unlink(); path.symlink_to(self.panel)
        self.refuses('link changed','framebuffer')

    def test_wrong_dpu_driver_or_dt(self):
        path=self.master/'driver'; path.unlink(); path.symlink_to(self.sys/'bus/mipi-dsi/drivers'/E.DRIVER)
        self.refuses('link changed','framebuffer')

    def test_framebuffer_metadata_refusals(self):
        for name,value in (('name','msm-kmsdrmfb\n'),('virtual_size','1080,4896\n'),
                           ('modes','U:1080x2448p-90\n'),('bits_per_pixel','16\n')):
            path=self.fb/name; saved=path.read_bytes()
            with self.subTest(name=name):
                self.write(path,value); self.refuses('framebuffer','framebuffer')
            self.write(path,saved)

    def test_framebuffer_requires_zero_property(self):
        self.write(self.backlight/'brightness','1\n'); self.refuses('default-zero','framebuffer')

    def test_blank_writes_only_zero_and_never_opens_fb(self):
        original_write=os.write; original_open=os.open; calls=[]
        def write(fd,data):
            calls.append((os.readlink('/proc/self/fd/'+str(fd)),data)); return original_write(fd,data)
        def opened(path,flags,*args,**kwargs):
            self.assertFalse(str(path).startswith('/dev/')); return original_open(path,flags,*args,**kwargs)
        with patch.object(E.os,'write',side_effect=write), patch.object(E.os,'open',side_effect=opened): self.check('blank')
        self.assertEqual(calls,[(str(self.backlight/'brightness'),b'0\n')])

    def test_failed_write_zero_readback_stays_failure(self):
        with patch.object(E.os,'write',side_effect=PermissionError(errno.EPERM,'fixture unprepared')):
            self.refuses('fixture unprepared','blank')
        self.assertEqual((self.backlight/'brightness').read_bytes(),b'0\n')

    def test_short_write_stays_failure(self):
        with patch.object(E.os,'write',return_value=1): self.refuses('short brightness write','blank')

    def test_replaced_attribute_before_write_refuses(self):
        calls=0; path=self.backlight/'brightness'
        def authorize():
            nonlocal calls
            calls+=1
            if calls==2:
                path.rename(self.root/'old-brightness'); self.write(path,'0\n')
            return True
        with patch.object(E.os,'write',side_effect=AssertionError('unexpected write')):
            with self.assertRaisesRegex(ValueError,'endpoint replaced'): self.endpoint.blank(BOOT,authorize)

    def test_replaced_attribute_after_write_refuses(self):
        original=os.write; path=self.backlight/'brightness'
        def write(fd,data):
            count=original(fd,data); path.rename(self.root/'old-brightness'); self.write(path,data); return count
        with patch.object(E.os,'write',side_effect=write): self.refuses('endpoint replaced','blank')

    def test_class_link_switch_after_write_refuses(self):
        original=os.write
        def write(fd,data):
            count=original(fd,data)
            path=self.sys/'class/backlight'/E.NAME; path.unlink(); path.symlink_to(self.master)
            return count
        with patch.object(E.os,'write',side_effect=write): self.refuses('backlight ancestry','blank')

    def test_identity_changes_during_blank_refuse(self):
        calls=0
        def authorize():
            nonlocal calls
            calls+=1
            if calls==2:self.identity_record['owner']='b'*32
            return True
        with self.assertRaisesRegex(ValueError,'admitted identity changed'):self.endpoint.blank(BOOT,authorize)

    def test_identity_changes_during_framebuffer_refuse(self):
        original=E.read
        def read(path,*args,**kwargs):
            data=original(path,*args,**kwargs)
            if path==self.fb/'modes':self.identity_record['owner']='b'*32
            return data
        with patch.object(E,'read',side_effect=read):self.refuses('admitted identity changed','framebuffer')

    def test_authorization_failure_at_each_boundary(self):
        for failed in (1,2,3):
            calls=0
            def authorize():
                nonlocal calls
                calls+=1;return calls!=failed
            with self.subTest(failed=failed):
                with self.assertRaisesRegex(ValueError,'authorization'):self.endpoint.blank(BOOT,authorize)


if __name__ == '__main__': unittest.main(verbosity=2)
