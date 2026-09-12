#!/usr/bin/env python3
"""Actual patch panel power helpers + exact Linux regulator accounting faults."""
import argparse
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / 'scripts/device/fixtures/fts3658u-regulator'
CASES_FILE = ROOT / 'scripts/device/fixtures/ams678-regulator/cases.c'
PATCH = ROOT / 'patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch'
CASES = ('cycles', 'vdd-child-disable', 'vdd-parent-disable', 'io-parent-disable',
         'vdd-enable-unwind', 'io-enable-unwind', 'unknown-vdd-other-held', 'unknown-io-other-held')
FUNCTIONS = ('_regulator_handle_consumer_disable', '_regulator_disable',
             '_regulator_handle_consumer_enable', '_regulator_enable')


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]


def driver_source(patch):
    tail = patch.read_text().split('+++ b/drivers/gpu/drm/panel/panel-asus-rog5-ams678.c\n', 1)[1]
    return '\n'.join(line[1:] for line in tail.splitlines() if line.startswith('+')) + '\n'


def extract(driver):
    start = driver.index('struct ams678_er2_plus_dsc {')
    enum = driver.find('enum ams678_supply_vote {')
    if enum >= 0:
        start = enum
        alias = ''
    else:
        alias = '\nenum { AMS678_VOTE_NONE, AMS678_VOTE_HELD, AMS678_VOTE_UNKNOWN };\n#define supply_vote supply_enabled\n'
    end = driver.index('static inline', start)
    body = driver[start:end] + '\n' + '\n'.join(function(driver, 'static int ams678_er2_plus_dsc_' + name + '(')
                                             for name in ('power_off', 'power_on'))
    # Historical field alias applies only to test expectations, after callbacks.
    return driver[:driver.index('#include')] + body + alias


BOUNDARIES = r'''
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
struct device { int unused; };
struct mipi_dsi_device { struct device dev; };
struct mutex { int unused; };
struct drm_panel { int unused; };
struct drm_dsc_config { int unused; };
struct regulator_bulk_data { const char *supply; struct regulator *consumer; };
static int disable_calls, enable_calls;
static int regulator_disable(struct regulator *reg) { disable_calls++; return _regulator_disable(reg); }
static int regulator_enable(struct regulator *reg) { enable_calls++; return _regulator_enable(reg); }
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', type=Path, default=PATCH)
    parser.add_argument('--linux-source', type=Path, default=os.environ.get('ROG5_LINUX_SOURCE'))
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    inputs = [args.patch, SHARED / 'stubs.h', SHARED / 'regulator-core-v7.1.4.c', CASES_FILE]
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    core = inputs[2].read_text()
    if args.linux_source:
        original = (args.linux_source / 'drivers/regulator/core.c').read_text()
        for name in FUNCTIONS:
            signature = 'static int ' + name + '(struct regulator *regulator)\n'
            if function(original, signature) != function(core, signature):
                raise ValueError('exact regulator extract differs: ' + name)
        print('PASS behavioral: four exact kernel regulator accounting functions compared')
    else:
        print('NOT RUN external regulator-source comparison; pinned accounting functions compiled')
    driver = driver_source(args.patch)
    prefix = inputs[1].read_text() + '\n' + core + '\n' + BOUNDARIES + '\n'
    unit = prefix + extract(driver) + '\n' + CASES_FILE.read_text()
    scratch = ROOT / 'build'; scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ams678-regulator-', dir=scratch) as directory:
        tmp = Path(directory); source = tmp / 'unit.c'; binary = tmp / 'unit'
        def compile_unit(text):
            source.write_text(text)
            subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-Wno-sign-compare', '-fsanitize=undefined',
                            '-fno-sanitize-recover=all', str(source), '-o', str(binary)], check=True, timeout=20)
        compile_unit(unit)
        failed = []
        for case in CASES:
            result = subprocess.run([str(binary), case], capture_output=True, text=True, timeout=5)
            print((result.stdout + result.stderr).strip(), flush=True)
            if result.returncode:
                failed.append(case)
        if failed:
            raise RuntimeError('behavioral cases failed: ' + ', '.join(failed))
        mutations = (
            ('assume-retained', 'ctx->supply_vote[i] = AMS678_VOTE_UNKNOWN;',
             'ctx->supply_vote[i] = AMS678_VOTE_HELD;', 'vdd-parent-disable'),
            ('blind-retry', 'if (ctx->supply_vote[i] == AMS678_VOTE_UNKNOWN)',
             'if (false && ctx->supply_vote[i] == AMS678_VOTE_UNKNOWN)', 'vdd-parent-disable'),
            ('skip-other-held', 'ret = -EUCLEAN;\n\t\t\tcontinue;',
             'ret = -EUCLEAN;\n\t\t\treturn ret;', 'unknown-vdd-other-held'),
        )
        for name, before, after, case in mutations:
            if before not in driver:
                raise ValueError('mutation target missing: ' + name)
            compile_unit(prefix + extract(driver.replace(before, after, 1)) + '\n' + CASES_FILE.read_text())
            result = subprocess.run([str(binary), case], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 or 'FAIL ' not in result.stderr:
                raise ValueError('behavioral mutation escaped: ' + name)
            print('PASS behavioral: rejected mutation ' + name + ': ' + result.stderr.strip())
    if pins != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}:
        raise ValueError('test inputs changed')
    print('panel_driver_sha256=' + hashlib.sha256(driver.encode()).hexdigest())
    print('compiled_unit_sha256=' + hashlib.sha256(unit.encode()).hexdigest())
    print(f'PASS behavioral: eight actual panel/core regulator cases + three mutations; elapsed={time.monotonic() - started:.6f}s')
    print('NOT RUN full DRM/DSI callbacks, physical power, devres restoration or recovery across reprobe')


if __name__ == '__main__':
    main()
