#!/usr/bin/env python3
"""Compile the patch's actual callbacks with fault-injected hardware APIs.

The DRM core fixture is an exact extract from pinned Linux v7.1.4. The scoped
kernel compile check compares that extract to the actual base again. This test
does not load a module or establish physical panel behavior.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'scripts/device/fixtures/ams678'
DEFAULT = ROOT / 'patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch'


def driver_source(patch):
    text = patch.read_text()
    tail = text.split('+++ b/drivers/gpu/drm/panel/panel-asus-rog5-ams678.c\n', 1)[1]
    return '\n'.join(line[1:] for line in tail.splitlines() if line.startswith('+')) + '\n'


def extract(source):
    # Compile the whole lifecycle implementation, including real command
    # sequences and Iris polling. Exclude only kernel registration/mode code.
    start = source.index('enum ams678_supply_vote {')
    end = source.index('static const struct drm_display_mode ')
    lifecycle = source[start:end]
    start = source.index('static int ams678_er2_plus_dsc_bl_update_status(')
    end = source.index('\n}', start) + 2
    return lifecycle + '\n' + source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', type=Path, default=DEFAULT)
    parser.add_argument('--linux-source', type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    inputs = [args.patch, *sorted(FIXTURES.iterdir())]
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    core = (FIXTURES / 'drm-panel-v7.1.4.c').read_text()
    brightness = (FIXTURES / 'drm-brightness-v7.1.4.c').read_text()
    if args.linux_source:
        exact = (args.linux_source / 'drivers/gpu/drm/drm_panel.c').read_text()
        for name in ('prepare', 'unprepare', 'enable', 'disable'):
            needle = 'void drm_panel_' + name + '('
            begin = exact.index(needle)
            function = exact[begin:exact.index('\n}', begin) + 2]
            if function not in core:
                raise ValueError('DRM core fixture differs: ' + name)
        exact = (args.linux_source / 'drivers/gpu/drm/drm_mipi_dsi.c').read_text()
        begin = exact.index('int mipi_dsi_dcs_set_display_brightness_large(')
        if exact[begin:exact.index('\n}', begin) + 2] not in brightness:
            raise ValueError('DRM brightness fixture differs')
        print('PASS behavioral: exact Linux DRM lifecycle and brightness source comparison')
    else:
        print('NOT RUN external kernel-source comparison; pinned extracts compiled')
    driver = driver_source(args.patch)
    lock_init = '\n'.join(re.findall(r'mutex_init\(&ctx->\w+\);', driver)).replace('ctx->', 'ctx.')
    source = ((FIXTURES / 'stubs.h').read_text() + '\n' + brightness + '\n' +
              extract(driver) + '\n' + core + '\n' +
              (FIXTURES / 'cases.c').read_text().replace('DRIVER_MUTEX_INIT', lock_init))
    cases = ('iris-timeout', 'iris-gpio-error', 'init-error', 'pps-error',
             'compression-error', 'off-error-reprepare', 'disable-error',
             'prepare-cleanup-error', 'normal-cycles', 'brightness-order',
             'enable-error', 'serialized-backlight', 'enable-supply-error',
             'disable-second-supply-error', 'brightness-error-flags',
             'enable-first-supply-error')
    with tempfile.TemporaryDirectory(prefix='ams678-lifecycle-',
                                     dir=os.environ.get('TMPDIR')) as tmp:
        unit = Path(tmp) / 'unit.c'
        unit.write_text(source)
        binary = Path(tmp) / 'test'
        command = [os.environ.get('CC', 'cc'), '-std=gnu11', '-Wall',
                        '-Wextra', '-Werror', '-Wno-unused-parameter',
                        '-Wno-unused-function', '-pthread', str(unit),
                        '-o', str(binary)]
        subprocess.run(command, check=True, timeout=30)
        failed = []
        for case in cases:
            result = subprocess.run([str(binary), case], timeout=5)
            print(('PASS' if result.returncode == 0 else 'FAIL') + ' ' + case,
                  flush=True)
            if result.returncode:
                failed.append(case)
        if failed:
            raise SystemExit('FAIL lifecycle cases: ' + ', '.join(failed))
        target = ('\t\t\tctx->supply_vote[i] = AMS678_VOTE_UNKNOWN;\n'
                  '\t\t\tdev_err')
        if source.count(target) != 1:
            raise ValueError('uncertain vote mutation target changed')
        unit.write_text(source.replace(target, target.replace('AMS678_VOTE_UNKNOWN',
                                                               'AMS678_VOTE_HELD'), 1))
        subprocess.run(command, check=True, timeout=30)
        result = subprocess.run([str(binary), 'disable-error'], capture_output=True,
                                text=True, timeout=5)
        if result.returncode == 0 or 'Assertion' not in result.stderr:
            raise ValueError('unsafe regulator retry mutation escaped behavioral checks')
        print('PASS behavioral: rejects HELD ownership after regulator-disable error')
    if pins != {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}:
        raise ValueError('lifecycle inputs changed during tests')
    print('driver_sha256=' + hashlib.sha256(driver.encode()).hexdigest())
    print(f'PASS behavioral: {len(cases)} actual-driver/core fault-injection cases, 1 mutation; '
          f'elapsed={time.monotonic() - started:.6f}s')
    print('NOT RUN physical panel validation')


if __name__ == '__main__':
    main()
