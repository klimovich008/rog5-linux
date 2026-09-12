#!/usr/bin/env python3
"""Actual FTS power callbacks + Linux7.1.4 regulator accounting under faults."""
import argparse
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'scripts/device/fixtures/fts3658u-regulator'
FUNCTIONS = ('_regulator_handle_consumer_disable', '_regulator_disable',
             '_regulator_handle_consumer_enable', '_regulator_enable')
CASES = ('cycles', 'child-disable', 'parent-disable', 'enable-failure', 'enable-unwind', 'unknown-other-held')


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]


def driver_code(source):
    start = source.index('struct rog5_fts {')
    structure = source[start:source.index('\n};', start) + 3]
    enum_start = source.find('enum rog5_fts_')
    if enum_start >= 0 and enum_start < start:
        enum = source[enum_start:source.index('\n};', enum_start) + 3]
    else:
        # Old bool-based sources must compile then fail behavior, not compilation.
        enum = 'enum { ROG5_FTS_VOTE_NONE, ROG5_FTS_VOTE_HELD, ROG5_FTS_VOTE_UNKNOWN };'
    return enum + '\n' + structure + '\n' + '\n'.join(function(source, 'static int ' + name + '(')
                   for name in ('rog5_fts_power_off', 'rog5_fts_power_on'))


BOUNDARIES = r'''
static int disable_calls, enable_calls;
static int regulator_disable(struct regulator *reg) { disable_calls++; return _regulator_disable(reg); }
static int regulator_enable(struct regulator *reg) { enable_calls++; return _regulator_enable(reg); }
struct device { int unused; };
struct i2c_client { struct device dev; };
struct gpio_desc { int unused; };
struct input_dev;
static int gpiod_set_value_cansleep(struct gpio_desc *gpio, int level) { return 0; }
static void usleep_range(int low, int high) {}
static void msleep(int ms) {}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver', type=Path, default=ROOT / 'tools/rog5-fts3658u/rog5_fts3658u.c')
    parser.add_argument('--linux-source', type=Path, default=os.environ.get('ROG5_LINUX_SOURCE'))
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    inputs = [args.driver, *sorted(FIXTURE.iterdir())]
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    core = (FIXTURE / 'regulator-core-v7.1.4.c').read_text()
    if args.linux_source:
        source = (args.linux_source / 'drivers/regulator/core.c').read_text()
        for name in FUNCTIONS:
            signature = 'static int ' + name + '(struct regulator *regulator)\n'
            if function(source, signature) != function(core, signature):
                raise ValueError('exact core extract differs: ' + name)
        print('PASS behavioral: four exact kernel regulator accounting functions compared')
    else:
        print('NOT RUN external source comparison; pinned actual accounting functions compiled')
    prefix = (FIXTURE / 'stubs.h').read_text() + '\n' + core + '\n' + BOUNDARIES + '\n'
    suffix = '\n' + (FIXTURE / 'cases.c').read_text()
    driver = args.driver.read_text()
    unit = prefix + driver_code(driver) + suffix
    scratch = ROOT / 'build'; scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fts-regulator-errors-', dir=scratch) as directory:
        tmp = Path(directory); source = tmp / 'unit.c'; binary = tmp / 'unit'
        def compile_unit(text):
            source.write_text(text)
            subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            str(source), '-o', str(binary)], check=True, timeout=20)
        compile_unit(unit)
        failures = []
        for case in CASES:
            result = subprocess.run([str(binary), case], capture_output=True, text=True, timeout=5)
            print((result.stdout + result.stderr).strip(), flush=True)
            if result.returncode:
                failures.append(case)
        if failures:
            raise RuntimeError('behavioral cases failed: ' + ', '.join(failures))
        mutations = (
            ('assume-retained', 'ts->vdd_vote = ROG5_FTS_VOTE_UNKNOWN;',
             'ts->vdd_vote = ROG5_FTS_VOTE_HELD;', 'parent-disable'),
            ('skip-other-held', 'if (ts->vdd_vote == ROG5_FTS_VOTE_UNKNOWN) {',
             'if (ts->vdd_vote == ROG5_FTS_VOTE_UNKNOWN) { return -EUCLEAN;', 'enable-unwind'),
        )
        for name, before, after, case in mutations:
            if before not in driver:
                raise ValueError('mutation target missing: ' + name)
            compile_unit(prefix + driver_code(driver.replace(before, after, 1)) + suffix)
            result = subprocess.run([str(binary), case], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 or 'FAIL ' not in result.stderr:
                raise ValueError('behavioral mutation escaped: ' + name)
            print('PASS rejected mutation ' + name + ': ' + result.stderr.strip())
    if pins != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}:
        raise ValueError('test inputs changed')
    print('driver_sha256=' + pins[str(args.driver)])
    print('compiled_unit_sha256=' + hashlib.sha256(unit.encode()).hexdigest())
    print(f'PASS behavioral: six actual-core/actual-driver regulator cases + two mutations; elapsed={time.monotonic() - started:.6f}s')
    print('NOT RUN physical RPMh/GPIO, terminal devres restoration or hardware recovery')


if __name__ == '__main__':
    main()
