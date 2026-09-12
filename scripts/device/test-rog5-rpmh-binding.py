#!/usr/bin/env python3
"""Validate the ASUS RSC binding against real DTs and exact driver PM code.

All writes stay in a new output directory. The supplied kernel source is read
only. Domain-restoring DTs are negative/positive schema fixtures, never boot
artifacts. This does not qualify CPU idle, system suspend, or physical hardware.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'patches/linux-7.1.4/0042-dt-bindings-soc-qcom-document-ASUS-ROG5-RSC-firmware.patch'
BOARD = ROOT / 'dts/qcom/sm8350-asus-rog-phone5.dts'
BINDING = 'Documentation/devicetree/bindings/soc/qcom/qcom,rpmh-rsc.yaml'
BASE_SCHEMA_SHA = '894c22ae16e15b9c32f7269cd8607986c0c2fa86af1d62903c918d6c1e1f69d9'
ASUS_SCHEMA_SHA = '99f5978a4e902b8df1d7450f9fc49de1d3147822d45ab8797e8cf9b89f453e79'
BASE_BOARD_SHA = '51bfb90a66d06eec89ff08a85bcfe7e1e0850d458e0df6792d91beba6ef3edc2'
PAIR = '\tcompatible = "asus,rog-phone5-rpmh-apps-rsc", "qcom,rpmh-rsc";\n'
RSC_PATH = '/soc@0/rsc@18200000'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def domain_provider_disabled(text):
    """Require one disabled assignment, rejecting contradictory duplicates."""
    symbol = 'CONFIG_ARM_PSCI_CPUIDLE_DOMAIN'
    values = []
    for line in text.splitlines():
        line = line.strip()
        if line == '# ' + symbol + ' is not set':
            values.append('n')
        elif re.match(symbol + r'\s*=', line):
            values.append(line.split('=', 1)[1].strip())
    return values == ['n']


def decoded(path):
    import libfdt
    tree = libfdt.Fdt(path.read_bytes())
    result = {}

    def visit(offset, parent):
        name = tree.get_name(offset)
        node = parent + '/' + name if name else '/'
        properties = {}
        prop_offset = tree.first_property_offset(offset, quiet=(libfdt.NOTFOUND,))
        while prop_offset >= 0:
            prop = tree.get_property_by_offset(prop_offset)
            properties[prop.name] = bytes(prop).hex()
            prop_offset = tree.next_property_offset(prop_offset, quiet=(libfdt.NOTFOUND,))
        result[node] = properties
        child = tree.first_subnode(offset, quiet=(libfdt.NOTFOUND,))
        while child >= 0:
            visit(child, '' if node == '/' else node)
            child = tree.next_subnode(child, quiet=(libfdt.NOTFOUND,))

    visit(0, '')
    return result


def driver_harness(driver):
    """Extract the actual probe decision and match table, never a PM model."""
    start = driver.index('\tsolver_config = readl_relaxed(')
    end = driver.index('\n\t/* Enable the active TCS', start)
    block = driver[start:end]
    start = driver.index('static const struct of_device_id rpmh_drv_match[] = {')
    end = driver.index('\n};', start) + 3
    table = driver[start:end]
    defines = '\n'.join(re.findall(r'^#define DRV_HW_SOLVER_(?:MASK|SHIFT)\s+\d+$', driver, re.M))
    require(len(defines.splitlines()) == 2, 'solver definitions changed')
    require(re.findall(r'\.compatible = "([^"]+)"', table) == ['qcom,rpmh-rsc'],
            'actual RSC match table changed; review matching before extending fixture')
    source = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct of_device_id { const char *compatible; };
struct notifier { int (*notifier_call)(void); };
struct device { void *pm_domain; };
struct platform_device { struct device dev; };
struct rsc_drv { uintptr_t base; unsigned regs[1]; struct notifier rsc_pm; };
enum { DRV_SOLVER_CONFIG };
static unsigned hardware, genpd_calls, cpu_calls;
static int attach_error;
static unsigned readl_relaxed(uintptr_t address) { (void)address; return hardware; }
static int rpmh_rsc_cpu_pm_callback(void) { return 0; }
static int cpu_pm_register_notifier(struct notifier *n) {
    if (n->notifier_call != rpmh_rsc_cpu_pm_callback) return -99;
    cpu_calls++; return 0;
}
static int rpmh_rsc_pd_attach(struct rsc_drv *d, struct device *v) {
    (void)d; (void)v; genpd_calls++; return attach_error;
}
'''
    source += defines + '\n' + table + '\n'
    source += 'static int probe(struct rsc_drv *drv, struct platform_device *pdev) {\nunsigned solver_config; int ret;\n'
    source += block + '\nreturn 0;\n}\n'
    source += r'''
static int check(unsigned solver, int domain, int error,
                 unsigned want_genpd, unsigned want_cpu, int want_return) {
    struct rsc_drv drv = {0};
    struct platform_device pdev = {{domain ? &drv : NULL}};
    hardware = solver << DRV_HW_SOLVER_SHIFT;
    attach_error = error; genpd_calls = cpu_calls = 0;
    int ret = probe(&drv, &pdev);
    return ret != want_return || genpd_calls != want_genpd || cpu_calls != want_cpu;
}
int main(void) {
    if (strcmp(rpmh_drv_match[0].compatible, "qcom,rpmh-rsc") ||
        rpmh_drv_match[1].compatible) return 1;
    if (check(0, 0, 0, 0, 1, 0)) return 2;
    if (check(0, 1, 0, 1, 0, 0)) return 3;
    if (check(0, 1, -42, 1, 0, -42)) return 4;
    if (check(1, 0, 0, 0, 0, 0)) return 5;
    if (check(1, 1, -42, 0, 0, 0)) return 6;
    puts("PASS actual PM selection: CPU_PM, genpd, attach failure, two HW-solver cases");
    return 0;
}
'''
    return source, block, table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-source', type=Path, default=os.environ.get('ROG5_LINUX_SOURCE'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    missing = [tool for tool in ['cpp', 'dtc', 'dt-validate', 'dt-doc-validate', 'dt-mk-schema', 'cc', 'git']
               if not shutil.which(tool)]
    try:
        import libfdt  # Mandatory; absence must not turn this into a static PASS.
    except ImportError:
        missing.append('Python libfdt')
    if args.linux_source is None or not args.linux_source.is_dir():
        missing.append('exact kernel source (--linux-source or ROG5_LINUX_SOURCE)')
    else:
        for relative in [BINDING, 'drivers/soc/qcom/rpmh-rsc.c',
                         'arch/arm64/boot/dts/qcom/sm8350.dtsi']:
            if not (args.linux_source / relative).is_file():
                missing.append('kernel source file: ' + relative)
    if missing:
        print('BLOCKED missing prerequisites: ' + ', '.join(missing))
        return 2
    source = args.linux_source.resolve()
    if args.output is None:
        scratch = Path(os.environ.get('ROG5_TEST_TMPDIR') or os.environ.get('TMPDIR') or ROOT / 'build')
        scratch.mkdir(parents=True, exist_ok=True)
        args.output = Path(tempfile.mkdtemp(prefix='rpmh-binding-', dir=scratch)) / 'evidence'
    out = args.output.resolve()
    require(not out.exists(), 'output already exists; preserve earlier evidence')
    require(not out.is_relative_to(source), 'output must be outside read-only kernel source')
    out.mkdir(parents=True)
    print('Evidence: ' + str(out), flush=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env['GIT_CEILING_DIRECTORIES'] = str(out)
    started = time.monotonic()
    result = {'status': 'RUNNING', 'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'physical_validation': 'NOT RUN', 'schema_fixture_DTs': 'NEVER FOR BOOT',
              'kernel_compilation': 'NOT RUN', 'stages': {}, 'inputs': {
                  str(p): digest(p) for p in [PATCH, BOARD, Path(__file__), source / BINDING,
                                            ROOT / 'configs/kernel/rog5-mainline.fragment',
                                            source / 'drivers/soc/qcom/rpmh-rsc.c']}}

    def save():
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    def run(name, command):
        begin = time.monotonic()
        log = out / (name + '.log')
        with log.open('wb') as stream:
            child = subprocess.Popen(list(map(str, command)), env=env, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    require(time.monotonic() - begin < 180, name + ': deadline exceeded')
                    require(log.stat().st_size <= 8 * 1024 * 1024, name + ': output exceeds 8 MiB')
                    require(shutil.disk_usage(out).free >= 256 * 1024 * 1024, 'disk reserve exhausted')
                    time.sleep(.1)
            finally:
                # Kill the whole owned process group, including a grandchild
                # remaining after its direct parent exited or was interrupted.
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
        require(log.stat().st_size <= 8 * 1024 * 1024, name + ': output exceeds 8 MiB')
        output = log.read_text(errors='replace')
        result['stages'][name] = {'command': list(map(str, command)), 'exit_status': child.returncode,
                                 'seconds': round(time.monotonic() - begin, 3), 'log_sha256': digest(log)}
        save()
        require(child.returncode == 0, name + ' failed: ' + output[-2000:])
        return output

    try:
        schema_hash = digest(source / BINDING)
        require(schema_hash in (BASE_SCHEMA_SHA, ASUS_SCHEMA_SHA), 'supplied RSC binding differs from reviewed source')
        board = BOARD.read_text()
        require(board.count(PAIR) == 1, 'ASUS compatible assignment absent or duplicated')
        before = board.replace(PAIR, '')
        require(hashlib.sha256(before.encode()).hexdigest() == BASE_BOARD_SHA,
                'board changed beyond reviewed compatible addition; update baseline deliberately')
        require('&apps_rsc {\n' + PAIR + '\t/delete-property/ power-domains;' in board,
                'retained RSC domain deletion changed')
        require(domain_provider_disabled((ROOT / 'configs/kernel/rog5-mainline.fragment').read_text()),
                'PSCI domain config changed')

        # Link read-only schema inputs; only the one owned binding copy is patched.
        bindings = source / 'Documentation/devicetree/bindings'
        for original in bindings.rglob('*'):
            target = out / 'source/Documentation/devicetree/bindings' / original.relative_to(bindings)
            if original.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif original.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(original)
        owned_schema = out / 'source' / BINDING
        owned_schema.unlink()
        shutil.copyfile(source / BINDING, owned_schema)
        if schema_hash == ASUS_SCHEMA_SHA:
            run('reverse-owned-patch', ['git', '-C', out / 'source', 'apply', '-R', PATCH])
            require(digest(owned_schema) == BASE_SCHEMA_SHA, 'owned reverse patch does not recover exact base')
        run('apply-check', ['git', '-C', out / 'source', 'apply', '--check', PATCH])
        run('apply', ['git', '-C', out / 'source', 'apply', PATCH])
        require(not run('meta-schema', ['dt-doc-validate', owned_schema]).strip(), 'binding meta-schema diagnostics')
        run('schema-cache', ['dt-mk-schema', '-j', '-o', out / 'schema.json',
                             out / 'source/Documentation/devicetree/bindings'])
        variants = {'before': before, 'asus': board,
                    'asus-domain': board.replace('\t/delete-property/ power-domains;\n\n\tregulators-0',
                                               '\t/delete-property/ power-domains;\n\tpower-domains = <&cluster_pd>;\n\n\tregulators-0'),
                    'malformed-pair': board.replace(PAIR, '\tcompatible = "asus,rog-phone5-rpmh-apps-rsc";\n'),
                    'malformed-domain': board.replace('\t/delete-property/ power-domains;\n\n\tregulators-0',
                                               '\t/delete-property/ power-domains;\n\tpower-domains = <&cluster_pd>, <&cluster_pd>;\n\n\tregulators-0')}
        result['cases'] = {}
        for name, text in variants.items():
            dts = out / (name + '.dts')
            dts.write_text(text)
            cpp = run(name + '-cpp', ['cpp', '-nostdinc', '-undef', '-D__DTS__', '-x', 'assembler-with-cpp',
                                     '-I', source / 'scripts/dtc/include-prefixes',
                                     '-I', source / 'arch/arm64/boot/dts/qcom', dts])
            preprocessed = out / (name + '.preprocessed.dts')
            preprocessed.write_text(cpp)
            dtb = out / (name + '.dtb')
            # Match the production base-DTB flags: symbol generation is for
            # overlays, not this base target. Never add artificial phandles.
            run(name + '-dtc', ['dtc', '-I', 'dts', '-O', 'dtb', '-o', dtb, preprocessed])
            log = run(name + '-schema', ['dt-validate', '-s', out / 'schema.json',
                                        '-l', 'qcom,rpmh-rsc', dtb])
            expected = {'before': "'power-domains' is a required property",
                        'malformed-pair': 'compatible:', 'malformed-domain': 'power-domains:'}.get(name)
            require(expected in log if expected else not log.strip(), name + ': unexpected schema diagnostics')
            result['cases'][name] = {'status': 'PASS', 'expected_schema_rejection': bool(expected),
                                     'dtb_sha256': digest(dtb)}
        require(not run('whole-board-schema', ['dt-validate', '-m', '-s', out / 'schema.json',
                                               out / 'asus.dtb']).strip(), 'whole-board schema diagnostics')
        result['whole_board_schema'] = 'PASS'
        old, new = decoded(out / 'before.dtb'), decoded(out / 'asus.dtb')
        require(old[RSC_PATH]['compatible'] == b'qcom,rpmh-rsc\0'.hex(), 'old generic match changed')
        require(new[RSC_PATH]['compatible'] == b'asus,rog-phone5-rpmh-apps-rsc\0qcom,rpmh-rsc\0'.hex(),
                'new fallback match changed')
        require('power-domains' not in old[RSC_PATH] and 'power-domains' not in new[RSC_PATH],
                'runtime domain property changed')
        delta = {'path': RSC_PATH, 'property': 'compatible', 'before': old[RSC_PATH]['compatible'],
                 'after': new[RSC_PATH]['compatible']}
        new[RSC_PATH]['compatible'] = old[RSC_PATH]['compatible']
        require(new == old, 'decoded DT differs beyond new compatible string')
        result['decoded_delta'] = delta
        driver = (source / 'drivers/soc/qcom/rpmh-rsc.c').read_text()
        harness, block, table = driver_harness(driver)
        unit = out / 'actual-pm.c'
        unit.write_text(harness)
        result['pm_extract_sha256'] = hashlib.sha256(block.encode()).hexdigest()
        result['match_extract_sha256'] = hashlib.sha256(table.encode()).hexdigest()
        run('actual-pm-compile', ['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', unit, '-o', out / 'actual-pm'])
        run('actual-pm', [out / 'actual-pm'])
        result['status'] = 'PASS'
    except BaseException as error:
        result.update(status='FAIL', error=str(error))
    finally:
        for path, expected in result['inputs'].items():
            if not Path(path).is_file() or digest(Path(path)) != expected:
                result.update(status='FAIL', error='input changed during test: ' + path)
        result.update(ended=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      seconds=round(time.monotonic() - started, 3))
        save()
    print(json.dumps({k: v for k, v in result.items() if k in ['status', 'seconds', 'error', 'cases']}, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    def interrupt(signum, frame):
        raise InterruptedError('interrupted by signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    raise SystemExit(main())
