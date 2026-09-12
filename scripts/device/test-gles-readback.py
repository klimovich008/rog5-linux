#!/usr/bin/env python3
"""Actual Rust executable, ABI faults and real Mesa software pixels; no DRI."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'tools/a660/rog5-gles-readback.rs'


class ReadbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in (os.environ.get('RUSTC', 'rustc'), 'cc', 'bwrap'):
            if not shutil.which(tool):
                raise RuntimeError(f'BLOCKED mandatory tool missing: {tool}')
        cls.tmp = tempfile.TemporaryDirectory(prefix='gles-readback-')
        cls.root = Path(cls.tmp.name)
        cls.binary = cls.root / 'probe'
        cls.unit = cls.root / 'unit'
        cls.fake = cls.root / 'fake'
        cls.fake.mkdir()
        for extra, output in (([], cls.binary), (['--test'], cls.unit)):
            subprocess.run([os.environ.get('RUSTC', 'rustc'), '--edition=2021',
                            '-Dwarnings', '-O', *extra, str(SOURCE), '-o', str(output)],
                           check=True, timeout=60)
        subprocess.run(['cc', '-shared', '-fPIC', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(REPO / 'tools/a660/test-fake-gles.c'), '-o', str(cls.fake / 'fixture.so')],
                       check=True, timeout=30)
        for name in ('libEGL.so.1', 'libGLESv2.so.2', 'libgbm.so.1'):
            (cls.fake / name).symlink_to('fixture.so')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def invoke(self, mode='--software-fixture', fault='', renderer=None, real=False, binary=None, timeout=10, native_fence=False, fence_import=False, dma_buf=False, gbm=False):
        env = os.environ.copy()
        for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
                     'EGL_PLATFORM', 'MESA_LOADER_DRIVER_OVERRIDE', 'GALLIUM_DRIVER',
                     '__EGL_VENDOR_LIBRARY_FILENAMES', '__EGL_VENDOR_LIBRARY_DIRS'):
            env.pop(name, None)
        env.update(LIBGL_ALWAYS_SOFTWARE='1', MESA_SHADER_CACHE_DISABLE='true',
                   LP_NUM_THREADS='1', ROG5_FAKE_GLES_FAIL=fault)
        env.pop('ROG5_FAKE_GLES_RENDERER', None)
        if renderer is not None:
            env['ROG5_FAKE_GLES_RENDERER'] = renderer
        if not real:
            env['LD_LIBRARY_PATH'] = str(self.fake)
            env['LD_PRELOAD'] = str(self.fake / 'fixture.so')
        # Private device namespace has no /dev/dri; no network/display sockets.
        command = ['bwrap', '--unshare-all', '--die-with-parent', '--ro-bind', '/', '/',
                   '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp',
                   '--', str(binary or self.binary)]
        if mode:
            command.append(mode)
        if gbm:
            command.append('--gbm-fd=0')
        elif dma_buf:
            command.append('--dma-buf')
        elif fence_import:
            command.append('--native-fence-import')
        elif native_fence:
            command.append('--native-fence')
        return subprocess.run(command, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)

    def test_rust_semantics(self):
        subprocess.run([str(self.unit)], check=True, timeout=10)

    def test_requires_explicit_mode_before_library_loading(self):
        result = self.invoke(mode=None)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn('CALL ', result.stderr)

    def test_actual_executable_faults_never_publish_pass(self):
        faults = ('extensions', 'display', 'initialize', 'version', 'bind', 'no_config',
                  'config', 'surface', 'context', 'current', 'identity_null',
                  'vertex_create', 'fragment_create', 'vertex_compile', 'fragment_compile',
                  'program_create', 'link', 'draw_error', 'read_error', 'read',
                  'cleanup_error', 'unbind', 'destroy_context', 'destroy_surface', 'terminate')
        for fault in faults:
            with self.subTest(fault=fault):
                result = self.invoke(fault=fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('FAIL ', result.stderr)
                self.assertEqual(result.stdout, '')
                if fault not in ('extensions', 'display', 'initialize'):
                    self.assertIn('CALL terminate', result.stderr)
                if fault in ('context', 'current', 'vertex_compile', 'cleanup_error', 'unbind', 'destroy_context'):
                    self.assertIn('CALL destroy_surface', result.stderr)
                if fault == 'current':
                    self.assertNotIn('CALL identity_null', result.stderr)

    def test_strict_renderer_scope_and_cleanup(self):
        for renderer, mode, status in (
            ('FD660', '--require-a660', 0),
            ('Adreno (TM) 660', '--require-a660', 0),
            ('llvmpipe (ABI fixture)', '--require-a660', 1),
            ('FD660 software', '--require-a660', 1),
            ('FD660', '--software-fixture', 1),
            ('llvmpipe (ABI fixture)', '--software-fixture', 0),
        ):
            with self.subTest(renderer=renderer, mode=mode):
                result = self.invoke(mode=mode, renderer=renderer)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertIn('CALL destroy_context', result.stderr)
                if status == 0:
                    self.assertIn('physical_acceptance=NOT RUN', result.stdout)
                    self.assertIn('render_readback=PASS', result.stdout)
                else:
                    self.assertNotIn('CALL vertex_create', result.stderr)

    def test_real_mesa_software_pixels_and_hardware_mode_refusal(self):
        result = self.invoke(real=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('scope=software-fixture-only', result.stdout)
        self.assertIn('channels_checked=64', result.stdout)
        self.assertIn('render_readback=PASS', result.stdout)
        result = self.invoke(real=True, mode='--require-a660')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('renderer refused', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_denial_gles_versions_and_refusal_before_drawing(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('REQUEST_CONTEXT 3.2', result.stderr)
        self.assertIn('REQUEST_CONFIG_ES 64', result.stderr)
        self.assertNotIn('REQUEST_CONTEXT 3.0', result.stderr)
        self.assertIn('gles_requested=3.2', result.stdout)
        self.assertIn('gles_actual=3.2', result.stdout)
        result = self.invoke(fault='context32')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(result.stderr.index('REQUEST_CONTEXT 3.2'),
                        result.stderr.index('REQUEST_CONTEXT 3.0'))
        self.assertIn('gles_requested=3.0', result.stdout)
        self.assertIn('gles32_error=0x3009', result.stdout)
        for fault in ('gles2', 'below_requested', 'negative_version', 'version_query'):
            with self.subTest(fault=fault):
                result = self.invoke(fault=fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('CALL vertex_create', result.stderr)
                self.assertIn('CALL destroy_context', result.stderr)
                self.assertIn('CALL terminate', result.stderr)

    def test_native_fence_export_wait_and_faults(self):
        result = self.invoke(native_fence=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('native_fence=PASS', result.stdout)
        stages = ['CALL draw', 'CALL fence_create', 'CALL flush',
                  'CALL fence_export', 'CALL fence_info', 'CALL fence_destroy', 'CALL read']
        offsets = [result.stderr.index(stage) for stage in stages]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn('FENCE_FD_CLOSED', result.stderr)
        for fault in ('native_extension', 'fence_symbol', 'fence_create', 'flush',
                      'fence_export', 'fence_timeout', 'fence_poll_error',
                      'fence_info', 'fence_pending', 'fence_negative', 'fence_destroy'):
            with self.subTest(fault=fault):
                result = self.invoke(native_fence=True, fault=fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('CALL read\n', result.stderr)
                self.assertIn('CALL terminate', result.stderr)
                if fault not in ('native_extension', 'fence_symbol', 'fence_create'):
                    self.assertIn('CALL fence_destroy', result.stderr)
                if fault in ('fence_timeout', 'fence_poll_error', 'fence_info',
                             'fence_pending', 'fence_negative', 'fence_destroy'):
                    self.assertIn('FENCE_FD_CLOSED', result.stderr)
        result = self.invoke(native_fence=True, fault='fence_eintr')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('native_fence=PASS', result.stdout)

    def test_native_fence_import_consumer_and_cleanup(self):
        result = self.invoke(fence_import=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('native_fence_import=PASS', result.stdout)
        self.assertIn('buffer_sharing=NOT RUN', result.stdout)
        stages = ['CALL fence_export', 'CALL consumer_context',
                  'CALL consumer_current', 'CALL fence_import', 'CALL server_wait',
                  'CALL consumer_fence_create', 'CALL consumer_flush',
                  'CALL consumer_export', 'CALL consumer_info',
                  'CALL consumer_fence_destroy', 'CALL import_destroy',
                  'CALL restore_current', 'CALL consumer_destroy',
                  'CALL fence_info', 'CALL fence_destroy', 'CALL read\n']
        offsets = [result.stderr.index(stage) for stage in stages]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn('IMPORT_FD_CLOSED', result.stderr)
        for fault in ('consumer_context', 'consumer_surface', 'consumer_current',
                      'duplicate_fd', 'fence_import', 'server_wait', 'consumer_fence_create',
                      'consumer_flush', 'consumer_export', 'consumer_info',
                      'consumer_timeout', 'consumer_pending', 'consumer_negative',
                      'consumer_fence_destroy', 'import_destroy',
                      'restore_current', 'consumer_destroy', 'consumer_surface_destroy'):
            with self.subTest(fault=fault):
                result = self.invoke(fence_import=True, fault=fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertNotIn('CALL read\n', result.stderr)
                self.assertIn('CALL fence_destroy', result.stderr)
                self.assertIn('CALL terminate', result.stderr)
                self.assertIn('FENCE_FD_CLOSED', result.stderr)
                if fault == 'restore_current':
                    self.assertNotIn('CALL delete_program', result.stderr)
                if fault == 'import_destroy':
                    self.assertIn('IMPORT_FD_CLOSED_AT_TERMINATE', result.stderr)
                if fault == 'fence_import':
                    self.assertIn('IMPORT_FD_CLOSED', result.stderr)
        result = self.invoke(fence_import=True, fault='context32')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('gles_requested=3.0', result.stdout)
        self.assertIn('native_fence_import=PASS', result.stdout)
        for mode in (None, '--native-fence', '--native-fence-import'):
            result = self.invoke(mode=mode, fence_import=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn('CALL ', result.stderr)
        # A blocked server call is covered by the external process deadline.
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.invoke(fence_import=True, fault='server_stall', timeout=0.5)
        self.assertFalse(caught.exception.stdout)

    def test_dma_buf_roundtrip_and_faults(self):
        result = self.invoke(dma_buf=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dma_buf=PASS', result.stdout)
        self.assertIn('buffer_sharing=PASS: same-context linear DMA-BUF', result.stdout)
        self.assertIn('DMA_FD_CLOSED', result.stderr)
        stages = ['CALL texture_allocate', 'CALL draw', 'CALL dma_finish',
                  'CALL source_image', 'CALL dma_query', 'CALL dma_export',
                  'CALL dma_import', 'CALL image_texture', 'CALL read\n']
        offsets = [result.stderr.index(stage) for stage in stages]
        self.assertEqual(offsets, sorted(offsets))
        for fault in ('dma_extension', 'dma_symbol', 'texture_create', 'texture_allocate',
                      'framebuffer_create', 'framebuffer_incomplete', 'source_image',
                      'dma_finish', 'dma_query', 'dma_planes', 'dma_format', 'dma_modifier',
                      'dma_export', 'dma_export_partial', 'dma_fd', 'dma_stride',
                      'dma_offset', 'dma_import', 'image_texture', 'dma_corrupt',
                      'dma_destroy', 'texture_delete', 'framebuffer_delete'):
            with self.subTest(fault=fault):
                result = self.invoke(dma_buf=True, fault=fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertIn('CALL terminate', result.stderr)
                if fault in ('dma_export_partial', 'dma_stride', 'dma_offset',
                             'dma_import', 'image_texture', 'dma_corrupt', 'dma_destroy'):
                    self.assertIn('DMA_FD_CLOSED', result.stderr)
        result = self.invoke(dma_buf=True, fault='context32')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dma_buf=PASS', result.stdout)

    def test_gbm_allocation_import_and_cleanup(self):
        result = self.invoke(gbm=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('dma_allocation=GBM explicit linear', result.stdout)
        self.assertIn('dma_buf=PASS', result.stdout)
        self.assertNotIn('CALL dma_export', result.stderr)
        self.assertNotIn('CALL texture_allocate', result.stderr)
        self.assertIn('GBM_FD_ALIVE', result.stderr)
        self.assertIn('GBM_FD_CLOSED', result.stderr)
        self.assertLess(result.stderr.index('CALL terminate'), result.stderr.index('CALL gbm_bo_destroy'))
        self.assertLess(result.stderr.index('CALL gbm_bo_destroy'), result.stderr.index('CALL gbm_destroy'))
        for fault in ('gbm_device', 'gbm_context_extension', 'gbm_allocate',
                      'gbm_planes', 'gbm_format', 'gbm_modifier', 'gbm_stride',
                      'gbm_offset', 'gbm_export', 'dma_import', 'image_texture',
                      'dma_corrupt', 'dma_destroy', 'texture_delete', 'terminate'):
            with self.subTest(fault=fault):
                result = self.invoke(gbm=True, fault=fault)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, '')
                if fault != 'gbm_device': self.assertIn('CALL gbm_destroy', result.stderr)
                if fault not in ('gbm_device', 'gbm_context_extension', 'gbm_allocate'):
                    self.assertIn('CALL gbm_bo_destroy', result.stderr)

    def test_stalled_readback_is_killed_without_success(self):
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.invoke(fault='stall', timeout=0.5)
        self.assertFalse(caught.exception.stdout)
        self.assertIn(b'CALL stall', caught.exception.stderr)
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_draw_mutation_fails_against_real_mesa(self):
        source = SOURCE.read_text()
        marker = '(a.glDrawArrays)(0x0004, 0, 3);'
        self.assertEqual(source.count(marker), 1)
        mutated = self.root / 'no-draw.rs'
        mutated.write_text(source.replace(marker, 'let _ = a.glDrawArrays;'))
        binary = self.root / 'no-draw'
        subprocess.run([os.environ.get('RUSTC', 'rustc'), '--edition=2021', '-Dwarnings',
                        '-O', str(mutated), '-o', str(binary)], check=True, timeout=60)
        result = self.invoke(real=True, binary=binary)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('pixel mismatch', result.stderr)
        self.assertEqual(result.stdout, '')
        # The same mutation must also fail after a real FD-backed fixture transfer.
        result = self.invoke(dma_buf=True, binary=binary)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('pixel mismatch', result.stderr)
        self.assertEqual(result.stdout, '')
        result = self.invoke(gbm=True, binary=binary)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('pixel mismatch', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_dma_import_binding_mutation_and_real_texture_pixels(self):
        source = SOURCE.read_text()
        for name, marker, replacement, real, wanted in (
            ('no-import-binding', 'target(0x0de1, imported);',
             'let _ = target;', False, 1),
            ('texture-only', 'self.dma_extensions(true)?;',
             'let _ = self.dma_extensions(true);', True, 0),
        ):
            changed = source.replace(marker, replacement)
            self.assertNotEqual(source, changed)
            if real:
                changed = changed.replace('if dma_buf { self.dma_roundtrip()?; }',
                                          'if false { self.dma_roundtrip()?; }')
                changed = changed.replace('if dma_buf { "PASS" } else { "NOT RUN" }',
                                          '"NOT RUN: texture-only test mutation"')
                changed = changed.replace('PASS: same-context linear DMA-BUF',
                                          'NOT RUN: texture-only test mutation')
            path = self.root / (name + '.rs')
            path.write_text(changed)
            binary = self.root / name
            subprocess.run([os.environ.get('RUSTC', 'rustc'), '--edition=2021', '-Dwarnings',
                            '-O', str(path), '-o', str(binary)], check=True, timeout=60)
            result = self.invoke(dma_buf=True, binary=binary, real=real)
            self.assertEqual(result.returncode, wanted, result.stderr)
            if real:
                self.assertIn('render_readback=PASS', result.stdout)
                self.assertIn('dma_buf=NOT RUN: texture-only test mutation', result.stdout)
                # This intentionally bypasses the DMA-BUF operations. Only the
                # actual texture/FBO/shader/readback is evidence, not its labels.
            else:
                self.assertIn('framebuffer incomplete', result.stderr)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
