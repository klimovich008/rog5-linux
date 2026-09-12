#!/usr/bin/env python3
"""Offline production DT/overlay composition, with exact semantic boundaries.

Uses the existing bounded DT parser and display verifier without changing their
historical CLI identity pins. Generated DTs are qualification fixtures, not boot
candidates. Touch controller, bus, and its rails must remain disabled.
"""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import signal
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


PARSER = module('mobile_dtb_parser', 'verify-recovery-dtb-delta.py')
DISPLAY = module('mobile_display_delta', 'verify-display-60hz-dtb-delta.py')
cell, cells, string = DISPLAY.cell, DISPLAY.cells, DISPLAY.string
SYMBOLS = '/__symbols__'
GPU = '/soc@0/gpu@3d00000'
REGULATORS = '/soc@0/rsc@18200000/regulators-1'
L3, L8 = REGULATORS + '/ldo3', REGULATORS + '/ldo8'
TLMM = '/soc@0/pinctrl@f100000'
TOUCH_PINS = TLMM + '/rog5-front-touch-active-state'
I2C = '/soc@0/geniqup@9c0000/i2c@990000'
SPI = '/soc@0/geniqup@9c0000/spi@990000'
TOUCH = I2C + '/touchscreen@38'
DT_DIR = ROOT / 'dts/qcom'
BOARD = DT_DIR / 'sm8350-asus-rog-phone5.dts'
OVERLAYS = [DT_DIR / name for name in (
    'sm8350-asus-rog-phone5-display-60hz-reviewed.dtso',
    'sm8350-asus-rog-phone5-gpu.dtso',
    'sm8350-rog5-mp2-front-touch-disabled.dtso')]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def metadata(data):
    """Keep reservations and boot CPU separate from mutable DT block layout."""
    PARSER.parse_dtb(data, 'metadata input')
    offset = struct.unpack_from('>I', data, 16)[0]
    start = offset
    while struct.unpack_from('>QQ', data, offset) != (0, 0):
        offset += 16
    return data[start:offset + 16], struct.unpack_from('>I', data, 28)[0]


def phandles(nodes):
    owners = {}
    for path, props in nodes.items():
        values = [props[k] for k in ('phandle', 'linux,phandle') if k in props]
        if not values:
            continue
        require(all(v == values[0] and len(v) == 4 for v in values), 'invalid phandle aliases: ' + path)
        number = int.from_bytes(values[0], 'big')
        require(number not in (0, 0xffffffff) and number not in owners, 'duplicate/reserved phandle: ' + path)
        owners[number] = path
    return owners


def compare_symbols(base, symbolic):
    PARSER.require_board_identity(base, 'base')
    PARSER.require_board_identity(symbolic, 'symbolic base')
    require(SYMBOLS not in base, 'reference base already has symbols')
    require(set(symbolic) == set(base) | {SYMBOLS}, 'symbols build added/removed non-symbol nodes')
    phandles(base)
    phandles(symbolic)
    added = 0
    for path, original in base.items():
        props = dict(symbolic[path])
        for key in ('phandle', 'linux,phandle'):
            if key not in original and key in props:
                del props[key]
                added += 1
        require(props == original, 'symbols build altered hardware property: ' + path)
    require(symbolic[SYMBOLS], 'symbols table empty')
    for label, encoded in symbolic[SYMBOLS].items():
        require(encoded.endswith(b'\0') and b'\0' not in encoded[:-1], 'invalid symbol: ' + label)
        target = encoded[:-1].decode('ascii')
        require(target in base, 'symbol target absent: ' + label)
    return {'added_symbol_count': len(symbolic[SYMBOLS]), 'added_phandle_count': added}


def compare_gpu(base, candidate):
    expected = copy.deepcopy(base)
    require(GPU in expected and GPU + '/zap-shader' in expected, 'GPU topology absent')
    expected[GPU]['status'] = string('okay')
    expected[GPU + '/zap-shader']['firmware-name'] = string('qcom/sm8350/a660_zap.mbn')
    require(candidate == expected, 'GPU overlay changed unapproved properties/nodes')
    phandles(candidate)


def compare_display(base, candidate):
    # Kernel /plugin/ compilation emits fixups without necessarily exporting
    # overlay labels. The historical display verifier expects four exports.
    # Normalize ONLY those known metadata entries in a private comparison view;
    # every real property, phandle, and pre-existing symbol is still compared.
    view = copy.deepcopy(candidate)
    for label, path in {'rog5_panel_default': DISPLAY.PINCTRL, 'rog5_panel_in': DISPLAY.PANEL_IN,
                        'vreg_l12c_1p8': DISPLAY.L12, 'vreg_l13c_3p0': DISPLAY.L13}.items():
        require(label not in base[SYMBOLS], 'display symbol already present')
        if label in view[SYMBOLS]:
            require(view[SYMBOLS][label] == string(path), 'incorrect display export: ' + label)
        view[SYMBOLS][label] = string(path)
    return DISPLAY.compare(base, view, PARSER, input_direction='output-disable')


def compare_inert_touch(base, candidate):
    require(not {L3, L8, TOUCH_PINS, TOUCH} & set(base), 'touch additions already present')
    expected = copy.deepcopy(base)
    handle = lambda path: DISPLAY.phandle(candidate, path)
    for path in (I2C, SPI):
        require(base[path].get('status') == string('disabled'), 'touch bus baseline not disabled')
    for label, path in {'rog5_touch_l3c': L3, 'rog5_touch_l8c': L8,
                        'rog5_front_touch_active': TOUCH_PINS}.items():
        require(label not in base[SYMBOLS], 'touch symbol already present')
        if label in candidate[SYMBOLS]:
            require(candidate[SYMBOLS][label] == string(path), 'incorrect touch export: ' + label)
            expected[SYMBOLS][label] = string(path)
    expected[L3] = {'phandle': handle(L3), 'regulator-name': string('rog5_touch_l3c_3p008'),
                    'regulator-min-microvolt': cell(3008000), 'regulator-max-microvolt': cell(3008000),
                    'status': string('disabled')}
    expected[L8] = {'phandle': handle(L8), 'regulator-name': string('rog5_touch_l8c_1p8'),
                    'regulator-min-microvolt': cell(1800000), 'regulator-max-microvolt': cell(1800000),
                    'regulator-always-on': b'', 'status': string('disabled')}
    expected[TOUCH_PINS] = {'phandle': handle(TOUCH_PINS), 'pins': b'gpio22\0gpio23\0',
                            'function': string('gpio'), 'drive-strength': cell(8), 'bias-pull-up': b''}
    expected[TOUCH] = {'compatible': string('asus,rog5-mp2-fts3658u'), 'reg': cell(0x38),
                       'interrupt-parent': handle(TLMM), 'interrupts': cells(23, 2),
                       'reset-gpios': handle(TLMM) + cells(22, 1),
                       'io-enable-gpios': handle(TLMM) + cells(131, 0),
                       'vdd-supply': handle(L3), 'vcc_i2c-supply': handle(L8),
                       'pinctrl-names': string('default'), 'pinctrl-0': handle(TOUCH_PINS),
                       'touchscreen-size-x': cell(17280), 'touchscreen-size-y': cell(39168),
                       'status': string('disabled')}
    require(candidate == expected, 'inert touch overlay changed unapproved properties/nodes')
    phandles(candidate)


def rejected_mutation(check, before, after, path, prop, value):
    changed = copy.deepcopy(after)
    changed[path][prop] = value
    try:
        check(before, changed)
    except ValueError:
        return
    raise ValueError('semantic guard accepted mutation: ' + path + ':' + prop)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--linux-source', required=True, type=Path)
    ap.add_argument('--base-dtb', required=True, type=Path, help='production reference, with or without symbols')
    ap.add_argument('--schema', required=True, type=Path, help='complete processed exact-source schema JSON')
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    missing = [x for x in ('cpp', 'dtc', 'fdtoverlay', 'dt-validate') if not shutil.which(x)]
    for p in (args.base_dtb, args.schema, args.linux_source / 'arch/arm64/boot/dts/qcom/sm8350.dtsi'):
        if not p.is_file():
            missing.append(str(p))
    if missing:
        print('BLOCKED missing prerequisites: ' + ', '.join(missing))
        return 2
    out, source = args.output.resolve(), args.linux_source.resolve()
    require(not out.exists() and not out.is_relative_to(source), 'output must be new and outside kernel source')
    out.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    inputs = [Path(__file__), HERE / 'verify-recovery-dtb-delta.py', HERE / 'verify-display-60hz-dtb-delta.py',
              BOARD, *OVERLAYS, args.base_dtb, args.schema]
    result = {'status': 'RUNNING', 'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'physical_validation': 'NOT RUN', 'boot_candidate': 'NOT CREATED',
              'inputs': {str(p.resolve()): digest(p) for p in inputs}, 'source_inputs': {}, 'stages': {}}
    started = time.monotonic()

    def save():
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    def run(name, command, expected_failure=False):
        begin = time.monotonic()
        log = out / (name + '.log')
        with log.open('wb') as stream:
            child = subprocess.Popen(list(map(str, command)), env=env, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    require(time.monotonic() - begin < 60, name + ': timeout')
                    require(log.stat().st_size < 8 * 1024 * 1024, name + ': excessive output')
                    require(shutil.disk_usage(out).free > 256 * 1024 * 1024, 'disk reserve')
                    time.sleep(.1)
            finally:
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(child.pid, sig)
                    except ProcessLookupError:
                        pass
                    if sig == signal.SIGTERM:
                        try:
                            child.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            pass
                child.wait()
        require(log.stat().st_size <= 8 * 1024 * 1024, name + ': excessive output')
        text = log.read_text(errors='replace')
        result['stages'][name] = {'command': list(map(str, command)), 'exit_status': child.returncode,
                                 'seconds': round(time.monotonic() - begin, 3), 'log_sha256': digest(log)}
        save()
        require(bool(child.returncode) if expected_failure else child.returncode == 0, name + ': unexpected exit status')
        return text

    def compile_dt(name, dts, symbols):
        pre = out / (name + '.preprocessed.dts')
        dependencies = out / (name + '.dependencies')
        pre.write_text(run(name + '-cpp', ['cpp', '-nostdinc', '-undef', '-D__DTS__', '-x', 'assembler-with-cpp',
                                           '-MD', '-MF', dependencies, '-MT', 'mobile-dt',
                                           '-I', source / 'scripts/dtc/include-prefixes',
                                           '-I', source / 'arch/arm64/boot/dts/qcom', dts]))
        names = shlex.split(dependencies.read_text().replace('\\\n', ' '))
        require(names and names[0] == 'mobile-dt:', 'unexpected CPP dependency format')
        for dependency_name in names[1:]:
            dependency = Path(dependency_name)
            require(dependency.is_absolute() and dependency.is_file(), 'invalid CPP dependency: ' + dependency_name)
            require(dependency.stat().st_size <= 2 * 1024 * 1024, 'oversized CPP dependency: ' + dependency_name)
            binding = {'resolved': str(dependency.resolve()), 'sha256': digest(dependency)}
            require(dependency_name not in result['source_inputs'] or result['source_inputs'][dependency_name] == binding,
                    'CPP dependency changed between stages: ' + dependency_name)
            result['source_inputs'][dependency_name] = binding
        output = out / (name + ('.dtbo' if dts.suffix == '.dtso' else '.dtb'))
        require(output.parent == out, 'compiled DT output escaped owned directory')
        run(name + '-dtc', ['dtc', *(['-@'] if symbols else []), '-I', 'dts', '-O', 'dtb', '-o', output, pre])
        return output

    try:
        result['tools'] = {}
        for name in ('cpp', 'dtc', 'fdtoverlay', 'dt-validate'):
            path = Path(shutil.which(name)).resolve()
            version = run('version-' + name, [path, '--version'])
            result['tools'][name] = {'path': str(path), 'sha256': digest(path), 'version': version.splitlines()[:2]}
        plain = compile_dt('base-no-symbols', BOARD, False)
        symbolic = compile_dt('base-symbols', BOARD, True)
        repeated = compile_dt('base-symbols-repeat', BOARD, True)
        require(digest(symbolic) == digest(repeated), 'base symbols build is not reproducible')
        require(digest(args.base_dtb) in (digest(plain), digest(symbolic)), 'reference differs from both exact compiled base variants')
        require(metadata(plain.read_bytes()) == metadata(symbolic.read_bytes()), 'symbols changed DT boot/reservation metadata')
        base = PARSER.read_dtb(plain)
        nodes = PARSER.read_dtb(symbolic)
        result['symbols_delta'] = compare_symbols(base, nodes)
        # Match production's plugin targets: external/local fixups are emitted
        # by /plugin/ itself; exported symbols are not needed by these overlays.
        overlays = [compile_dt('overlay-' + str(i), dt, False) for i, dt in enumerate(OVERLAYS)]
        require(PARSER.read_dtb(overlays[0]).get('/__fixups__'), 'display overlay has no external fixups')
        # The exact diagnostic wording differs between dtc releases. The
        # parsed absence of symbols, real external fixups, failed application,
        # and success after the isolated symbols delta establish the cause.
        run('missing-symbols-regression', ['fdtoverlay', '-i', plain, '-o', out / 'failed-no-symbols.dtb',
                                          overlays[0]], expected_failure=True)
        checks = [compare_display, compare_gpu, compare_inert_touch]
        previous = symbolic
        result['composition'] = []
        result['mutation_regressions'] = []
        for i, overlay in enumerate(overlays):
            current = out / ('composed-' + str(i) + '.dtb')
            run('compose-' + str(i), ['fdtoverlay', '-i', previous, '-o', current, overlay])
            candidate = PARSER.read_dtb(current)
            checks[i](nodes, candidate)
            phandles(candidate)
            mutations = [[(DISPLAY.PANEL, 'vdd-supply', cell(0))],
                         [(GPU, 'memory-region', cell(0))],
                         [(TOUCH, 'status', string('okay')), (L8, 'status', string('okay')),
                          (L3, 'regulator-min-microvolt', cell(3100000)),
                          (REGULATORS, 'vdd-l3-l4-l5-l7-l13-supply', cell(0)),
                          (TOUCH, 'reset-gpios', DISPLAY.phandle(candidate, TLMM) + cells(131, 1))]][i]
            for path, prop, value in mutations:
                rejected_mutation(checks[i], nodes, candidate, path, prop, value)
                result['mutation_regressions'].append(path + ':' + prop)
            require(metadata(previous.read_bytes()) == metadata(current.read_bytes()), 'overlay changed DT boot/reservation metadata')
            result['composition'].append({'stage': ('display', 'gpu', 'inert-touch')[i], 'semantic_delta': 'PASS',
                                          'dtb_sha256': digest(current)})
            previous, nodes = current, candidate
        repeated = out / 'composed-repeat.dtb'
        run('compose-repeat', ['fdtoverlay', '-i', symbolic, '-o', repeated, *overlays])
        require(digest(previous) == digest(repeated), 'composition is not byte-reproducible')
        result['semantic_validation'] = 'PASS'
        result['outputs'] = {p.name: digest(p) for p in [plain, symbolic, previous, *overlays]}
        schema_log = run('composed-schema', ['dt-validate', '-m', '-s', args.schema, previous])
        result['schema_validation'] = 'FAIL' if schema_log.strip() else 'PASS'
        result['schema_diagnostics'] = schema_log.splitlines()
        result['status'] = 'FAIL' if schema_log.strip() else 'PASS'
    except BaseException as error:
        result.update(status='FAIL', error=str(error))
    finally:
        for p, h in result['inputs'].items():
            if not Path(p).is_file() or digest(Path(p)) != h:
                result.update(status='FAIL', error='input changed: ' + p)
        for p, binding in result['source_inputs'].items():
            dependency = Path(p)
            if (not dependency.is_file() or str(dependency.resolve()) != binding['resolved'] or
                    digest(dependency) != binding['sha256']):
                result.update(status='FAIL', error='CPP source input changed: ' + p)
        result['seconds'] = round(time.monotonic() - started, 3)
        result['ended'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(json.dumps({k: result[k] for k in ('status', 'semantic_validation', 'schema_validation', 'error', 'seconds') if k in result}, indent=2))
    print('Evidence: ' + str(out))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    def interrupt(signum, frame):
        raise InterruptedError('signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(main())
