#!/usr/bin/env python3
"""Draft loader patch against real panel/core callbacks; no device access.

Extract actual Loader/insert functions; identity, payload ownership, module
insertion effects and sysfs are explicit fixtures. Insertion children are real;
brightness returns come from compiled current driver and exact core extracts.
The patch does not update/admit the historical controller's payload pins.
"""
import ast
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'scripts/device/fixtures/display-loader/load-display-before.py'
PATCH = ROOT/'patches/display-controller/0001-default-dark-probe-ordering.patch'
BASE_SHA = '5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d'
OLD = '--before' in sys.argv
if OLD:
    sys.argv.remove('--before')


def module(path):
    spec = importlib.util.spec_from_file_location('panel_test_extract', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def build_driver(directory):
    life = module(ROOT/'scripts/device/test-ams678-lifecycle.py')
    fixture = life.FIXTURES
    driver = life.driver_source(life.DEFAULT)
    setup = (fixture/'cases.c').read_text().split('static void start(void)', 1)[0]
    locks = '\n'.join(re.findall(r'mutex_init\(&ctx->\w+\);', driver)).replace('ctx->', 'ctx.')
    # Only transport is new. The actual driver/create_backlight, DRM core and
    # backlight setter decide initialization, error and property behavior.
    bridge = r'''
int main(void)
{
 char line[32]; int ret; (void)off_finished;
 setup(); ctx.panel.backlight = ams678_er2_plus_dsc_create_backlight(&dsi);
 while (fgets(line, sizeof(line), stdin)) {
  ret = 0;
  if (!strcmp(line, "prepare\n") || !strcmp(line, "prepare-fail\n")) {
   fail_init = !strcmp(line, "prepare-fail\n");
   drm_panel_prepare(&ctx.panel); drm_panel_enable(&ctx.panel);
  } else if (!strcmp(line, "zero\n")) {
   ret = backlight_device_set_brightness(ctx.panel.backlight, 0);
  } else if (!strcmp(line, "zero-fail\n")) {
   fail_brightness = 1;
   ret = backlight_device_set_brightness(ctx.panel.backlight, 0);
  } else if (strcmp(line, "read\n")) { return 42; }
  printf("{\"ret\":%d,\"brightness\":%d,\"initialized\":%s,\"dbv_count\":%u}\n",
   ret, ctx.panel.backlight->props.brightness, ctx.initialized ? "true" : "false", dbv_count);
  fflush(stdout);
 }
 return 0;
}
'''
    source = '\n'.join((fixture/name).read_text() for name in
                       ('stubs.h', 'drm-brightness-v7.1.4.c', 'backlight-v7.1.4.c'))
    source += '\n'+life.extract(driver)+'\n'+(fixture/'drm-panel-v7.1.4.c').read_text()
    source += '\n'+setup.replace('DRIVER_MUTEX_INIT', locks)+bridge
    unit = directory/'panel.c'; unit.write_text(source)
    binary = directory/'panel'
    subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-Wno-unused-function', '-pthread', str(unit),
                    '-o', str(binary)], check=True, timeout=30)
    return binary


def patched_source(directory):
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('historical loader fixture differs')
    path = directory/'load-display.py'; path.write_bytes(raw)
    subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=directory, check=True, timeout=5)
    subprocess.run(['git', 'apply', str(PATCH)], cwd=directory, check=True, timeout=5)
    return raw.decode() if OLD else path.read_text()


class Ordering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory(prefix='rog5-loader-build-')
        cls.addClassCleanup(cls.shared.cleanup)
        root = Path(cls.shared.name)
        cls.binary = build_driver(root)
        cls.source = patched_source(root)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-loader-order-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sys = self.root/'sys'
        for path in ('class/backlight', 'class/graphics', 'module'):
            (self.sys/path).mkdir(parents=True)
        self.payload = self.root/'payload'
        (self.payload/'display-trial').mkdir(parents=True)
        self.driver = subprocess.Popen([str(self.binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self.stop_driver)
        self.mode = 'normal'
        self.events = []; self.zeros = []; self.entered = []; self.insertions = []
        self.identity_ok = self.health_ok = self.cleanup_ok = True
        self.property_override = None
        self.children = []; self.interrupted = False
        self.e = types.SimpleNamespace(SYS=self.sys, NAME='fixture-panel', identity=self.identity,
                                       backlight=self.backlight, blank=self.blank,
                                       framebuffer=self.framebuffer)
        self.m = types.ModuleType('loader_functions_under_test')
        self.m.__dict__.update(os=os, Path=Path, time=time, subprocess=subprocess,
                               selectors=selectors, clock=time.monotonic, pause=time.sleep,
                               E=self.e, PAYLOAD=self.payload, INSERT_SECONDS=2.0, DISCOVERY_SECONDS=.15)
        names = {'need', 'stamp', 'command', 'insert', 'LoadError', 'Loader'}
        selected = [node for node in ast.parse(self.source).body
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
        self.assertEqual({node.name for node in selected}, names)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(BASE), 'exec'), self.m.__dict__)
        helper = self.payload/'helper'; helper.write_bytes(b'not executable fixture')
        self.m.HELPER = ('helper', helper.stat().st_size, 'fixture', 0o644)
        self.m.MODULES = tuple((name, name+'.ko', 1, 'fixture') for name in ('refgen', 'panel'))
        for name, filename, *_ in self.m.MODULES:
            (self.payload/'display-trial'/filename).write_bytes(b'x')
        self.m.open_directory = lambda path: os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        def exact_file(directory, name, *_):
            # Explicit metadata fixture: production ownership/digest primitives
            # are unchanged by the patch and not qualified by this suite.
            fd = os.open(name, os.O_RDONLY, dir_fd=directory)
            return fd, self.m.stamp(os.fstat(fd))
        self.m.exact_file = exact_file
        self.m.refgen = lambda boot: {'fixture': True}
        self.m.command = self.command
        def child(*args, **kwargs):
            proc = subprocess.Popen(*args, **kwargs)
            self.children.append(proc)
            return proc
        self.m.subprocess = types.SimpleNamespace(Popen=child, PIPE=subprocess.PIPE,
                                                  DEVNULL=subprocess.DEVNULL)
        actual_insert = self.m.insert
        def insert(*args):
            result = actual_insert(*args)
            self.insertions.append(result)
            self.events.append(('reaped', result['filename'], result['reaped']))
            if result['filename'] == 'panel.ko' and result['status'] == 'PASS_INSERTION':
                if self.mode not in ('deferred', 'no-fb'):
                    self.rpc('prepare-fail' if self.mode == 'prepare-fail' else 'prepare')
                if self.mode == 'lost-health': self.health_ok = False
                if self.mode == 'lost-boot': self.identity_ok = False
                if self.mode == 'lost-cleanup': self.cleanup_ok = False
            return result
        self.m.insert = insert
        self.loader = self.m.Loader()

    def stop_driver(self):
        if self.driver.poll() is None:
            self.driver.stdin.close()
            try: self.driver.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.driver.kill(); self.driver.wait(timeout=2)
        self.driver.stdout.close(); self.driver.stderr.close()

    def rpc(self, command):
        self.driver.stdin.write(command+'\n'); self.driver.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(self.driver.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(2), 'panel fixture response deadline')
            return json.loads(self.driver.stdout.readline())

    def identity(self, boot):
        if not self.identity_ok: raise ValueError('fixture boot changed')
        return {'boot': boot}

    def backlight(self, boot):
        self.identity(boot)
        if not (self.sys/'class/backlight'/self.e.NAME).exists():
            raise FileNotFoundError('fixture backlight absent')
        if self.mode == 'interrupt' and not self.interrupted:
            self.interrupted = True
            raise KeyboardInterrupt('fixture process interruption')
        (self.root/'registration-observed').touch()
        value = self.rpc('read')['brightness']
        return {'brightness': value if self.property_override is None else self.property_override}

    def blank(self, boot, authorize):
        self.identity(boot)
        if authorize() is not True: raise ValueError('fixture cleanup ownership lost')
        self.backlight(boot)
        value = self.rpc('zero-fail' if self.mode == 'write-fail' else 'zero')
        self.zeros.append(value); self.events.append(('zero', value['ret']))
        if value['ret']: raise OSError(-value['ret'], 'actual panel/core rejected zero')
        if self.mode == 'post-zero-health': self.health_ok = False
        if self.mode == 'post-zero-boot':
            self.identity_ok = False
        self.identity(boot)
        return {'status': 'PASS_ZERO_BRIGHTNESS_COMMAND', 'brightness_readback': value['brightness']}

    def framebuffer(self, boot):
        self.identity(boot)
        if not (self.sys/'class/graphics/fb0').exists(): raise FileNotFoundError('fixture fb0 absent')
        self.assertEqual(self.backlight(boot)['brightness'], 0)
        self.events.append(('framebuffer', self.rpc('read')['initialized']))
        return {'status': 'PASS_FRAMEBUFFER_SYSFS'}

    def command(self, helper, directory, filename):
        # Only subprocess substitution. Actual insert/select/output/deadline/
        # kill/reap behavior runs on an owned inert Python child.
        script = 'import pathlib,time\n'
        script += f'pathlib.Path({str(self.sys/"module"/filename[:-3])!r}).mkdir()\n'
        if filename == 'panel.ko':
            script += f'pathlib.Path({str(self.sys/"class/backlight"/self.e.NAME)!r}).touch()\n'
            if self.mode != 'no-fb':
                script += f'pathlib.Path({str(self.sys/"class/graphics/fb0")!r}).touch()\n'
            # Keep registration visible until the parent actually observes it;
            # a sleep-based window is flaky under host CPU pressure.
            script += f'ack=pathlib.Path({str(self.root/"registration-observed")!r})\n'
            script += 'end=time.monotonic()+5\nwhile not ack.exists():\n if time.monotonic()>end: raise SystemExit(43)\n time.sleep(.005)\n'
            if self.mode == 'panel-fail': script += 'raise SystemExit(42)\n'
            if self.mode == 'timeout': script += 'time.sleep(10)\n'
        return [sys.executable, '-I', '-B', '-c', script]

    def enter(self, intent):
        self.entered.append(intent)
        return True

    def run_load(self):
        return self.loader.load_once('fixture-boot', lambda: self.health_ok,
                                     self.enter, lambda: self.cleanup_ok)

    def fail_load(self):
        with self.assertRaises(self.m.LoadError) as error:
            self.run_load()
        return error.exception.evidence

    def test_preparation_finishes_before_insertion_returns(self):
        result = self.run_load()
        self.assertEqual(result['status'], 'PASS_MODULES_AND_BLANK')
        self.assertEqual(len(self.zeros), 1)
        self.assertTrue(self.zeros[0]['initialized'])
        self.assertLess(self.events.index(('reaped', 'panel.ko', True)), self.events.index(('zero', 0)))
        self.assertTrue(all(row['reaped'] for row in result['insertions']))
        self.assertFalse(result['physical_darkness_verified'])
        self.assertFalse(result['physical_scanout_verified'])
        self.fail_load()
        self.assertEqual(len(self.insertions), 2)
        self.assertEqual(len(self.entered), 1)

    def test_fb_exists_but_deferred_preparation_remains_failure(self):
        self.mode = 'deferred'
        result = self.fail_load()
        self.assertEqual(len(self.zeros), 2)  # startup plus separate cleanup
        self.assertTrue(all(row['ret'] == -errno.EPERM and row['brightness'] == 0 for row in self.zeros))
        self.assertTrue(result['cleanup_errors'])
        self.assertIsNone(result['blank'])
        self.assertIn(('framebuffer', False), self.events)

    def test_initialization_failure_is_not_zero_property_success(self):
        self.mode = 'prepare-fail'
        result = self.fail_load()
        self.assertEqual(result['error']['type'], 'PermissionError')
        self.assertEqual(self.zeros[0]['ret'], -errno.EPERM)
        self.assertEqual(self.zeros[0]['brightness'], 0)
        self.assertFalse(result['retry_allowed'])

    def test_actual_dsi_zero_write_failure_propagates(self):
        self.mode = 'write-fail'
        result = self.fail_load()
        self.assertEqual(self.zeros[0]['ret'], -errno.EIO)
        self.assertEqual(self.zeros[0]['brightness'], 0)
        self.assertIsNone(result['blank'])

    def test_insertion_failure_still_attempts_independent_cleanup(self):
        self.mode = 'panel-fail'
        result = self.fail_load()
        self.assertEqual(result['insertions'][-1]['returncode'], 42)
        self.assertEqual(len(self.zeros), 1)
        self.assertTrue(result['cleanup_errors'])
        self.assertIsNone(result['blank'])

    def test_missing_fb_has_no_startup_write_but_attempts_cleanup(self):
        self.mode = 'no-fb'
        result = self.fail_load()
        self.assertIsNone(result['endpoint'])
        self.assertEqual(len(self.zeros), 1)
        self.assertTrue(result['cleanup_errors'])

    def test_lost_health_still_allows_independent_cleanup(self):
        self.mode = 'lost-health'
        result = self.fail_load()
        self.assertIsNone(result['blank'])
        self.assertEqual(result['cleanup_blank']['status'], 'PASS_ZERO_BRIGHTNESS_COMMAND')
        self.assertEqual(len(self.zeros), 1)

    def test_health_loss_after_zero_preserves_successful_cleanup_but_fails(self):
        self.mode = 'post-zero-health'
        result = self.fail_load()
        self.assertIsNotNone(result['blank'])
        self.assertIsNotNone(result['cleanup_blank'])
        self.assertEqual(len(self.zeros), 2)
        self.assertFalse(result['cleanup_errors'])

    def test_lost_boot_refuses_stale_cleanup(self):
        self.mode = 'lost-boot'
        result = self.fail_load()
        self.assertFalse(self.zeros)
        self.assertTrue(result['cleanup_errors'])

    def test_lost_cleanup_owner_refuses_write(self):
        self.mode = 'lost-cleanup'
        result = self.fail_load()
        self.assertFalse(self.zeros)
        self.assertTrue(result['cleanup_errors'])

    def test_boot_loss_after_zero_does_not_pass(self):
        self.mode = 'post-zero-boot'
        result = self.fail_load()
        self.assertIsNone(result['blank'])
        self.assertEqual(len(self.zeros), 1)
        self.assertTrue(result['cleanup_errors'])

    def test_bright_registration_is_rejected(self):
        self.property_override = 1023
        result = self.fail_load()
        self.assertIn('default-dark', result['insertions'][-1]['error']['reason'])
        self.assertTrue(result['insertions'][-1]['reaped'])
        self.assertIsNone(result['blank'])

    def test_deadline_reaps_child_and_preserves_cleanup_failure(self):
        self.mode = 'timeout'; self.m.INSERT_SECONDS = .15
        result = self.fail_load()
        self.assertEqual(result['insertions'][-1]['returncode'], -9)
        self.assertTrue(result['insertions'][-1]['reaped'])
        self.assertEqual(len(self.zeros), 1)
        self.assertTrue(result['cleanup_errors'])

    def test_interruption_reaps_insertion_and_closes_held_files(self):
        self.mode = 'interrupt'
        before = set(os.listdir('/proc/self/fd'))
        with self.assertRaises(KeyboardInterrupt): self.run_load()
        self.assertEqual(len(self.children), 2)
        self.assertTrue(all(child.poll() is not None for child in self.children))
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)
        self.assertEqual(len(self.zeros), 1)
        self.assertEqual(self.zeros[0]['ret'], -errno.EPERM)
        self.fail_load()
        self.assertEqual(len(self.children), 2)

    def test_uncertain_entry_cannot_be_repeated(self):
        self.enter = lambda intent: 1
        self.fail_load(); self.fail_load()
        self.assertFalse(self.children)
        self.assertFalse(self.zeros)

    def test_missing_cleanup_owner_prevents_entry(self):
        self.cleanup_ok = False
        result = self.fail_load()
        self.assertFalse(result['entered'])
        self.assertFalse(self.insertions)
        self.assertFalse(self.zeros)


class HistoricalRegression(unittest.TestCase):
    def test_previous_ordering_fails_with_actual_unprepared_driver(self):
        result = subprocess.run([sys.executable, '-O', str(Path(__file__).resolve()), '--before',
                                 'Ordering.test_preparation_finishes_before_insertion_returns'],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('actual panel/core rejected zero', result.stderr)
        self.assertIn("'reaped': True", result.stderr)
        self.assertIn('FAILED (errors=1)', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
