#!/usr/bin/env python3
"""Offline FTS3658U -> pinned Linux input.c -> handler-callback regressions.

Additive to test-rog5-touch-lifecycle.py: no previous tests or driver changes.
A packet or a locally retained exact Linux source is REQUIRED (never fetched).
See fixtures/fts3658u-input-core/README.md for the intentionally substituted
hardware, object allocation, registration, locking, list, RCU and timer APIs.
"""
# repository-test-report.py invokes python3 -O SCRIPT with no extra arguments.
# Re-exec in place BEFORE workload imports/limits; keep PID, argv and -O.
import os
import sys
if __name__ == '__main__' and not sys.flags.no_site:
    os.execv(sys.executable, [sys.executable, '-S', '-B', *sys.orig_argv[1:]])
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import resource
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'scripts/device/fixtures/fts3658u'
HERE = ROOT / 'scripts/device/fixtures/fts3658u-input-core'
DRIVER = ROOT / 'tools/rog5-fts3658u/rog5_fts3658u.c'
sys.path.insert(0, str(HERE))
from owned_process import OwnedCommands
CASES = (
    'down-move-up', 'unchanged-empty', 'delayed-slot', 'multiple', 'missing',
    'short-transfer', 'io-error', 'invalid-frame', 'suspend', 'wrap-oldest',
    'ten-contacts', 'capacity', 'handler-closed',
)
# Definitions, not declarations: extraction stops at the unindented closing
# brace, exactly as in the original harness. Whole-source hashes constrain
# this extractor to these particular, reviewed source files.
OLD_FUNCS = {
    'kernel/irq/manage.c#disable_irq': ('void disable_irq(',),
    'include/linux/input/mt.h': (
        'static inline void input_mt_set_value(',
        'static inline int input_mt_get_value(',
        'static inline bool input_mt_is_active(',
        'static inline bool input_mt_is_used(',
        'static inline int input_mt_new_trkid(',
        'static inline void input_mt_slot('),
    'drivers/input/input-mt.c': (
        'static void copy_abs(', 'int input_mt_init_slots(',
        'void input_mt_report_finger_count(',
        'void input_mt_report_pointer_emulation(',
        'bool input_mt_report_slot_state(',
        'static void __input_mt_drop_unused(', 'void input_mt_sync_frame('),
}
CORE_FUNCS = (
    'static inline int is_event_supported(', 'static int input_defuzz_abs_event(',
    'static void input_start_autorepeat(', 'static void input_stop_autorepeat(',
    'static void input_pass_values(', 'static int input_handle_abs_event(',
    'static int input_get_disposition(', 'static void input_event_dispose(',
    'void input_handle_event(', 'void input_event(', 'void input_set_abs_params(',
    'static unsigned int input_handle_events_default(',
    'static unsigned int input_handle_events_filter(',
    'static unsigned int input_handle_events_null(',
    'static void input_handle_setup_event_handler(',
)
CORE_MUTANTS = (
    ('no-abs-suppression', 'core', 'if (*pold == *pval)',
     'if (false && *pold == *pval)', 'unchanged-empty'),
    ('no-key-suppression', 'core', 'if (!!test_bit(code, dev->key) != !!value)',
     'if (true)', 'unchanged-empty'),
    ('eager-slot', 'core', '\t\treturn INPUT_IGNORE_EVENT;\n\t}\n\n\tis_mt_event',
     '\t\treturn INPUT_PASS_TO_HANDLERS;\n\t}\n\n\tis_mt_event', 'delayed-slot'),
    ('no-delayed-slot', 'core', 'return INPUT_PASS_TO_HANDLERS | INPUT_SLOT;',
     'return INPUT_PASS_TO_HANDLERS;', 'down-move-up'),
    ('deliver-empty-syn', 'core', 'if (dev->num_vals >= 2)',
     'if (dev->num_vals >= 1)', 'unchanged-empty'),
    ('no-report-flush', 'core',
     'disposition = INPUT_PASS_TO_HANDLERS | INPUT_FLUSH;',
     'disposition = INPUT_PASS_TO_HANDLERS;', 'down-move-up'),
    ('premature-flush', 'core', 'if (disposition & INPUT_FLUSH) {',
     'if ((disposition & INPUT_FLUSH) || dev->num_vals >= 2) {', 'delayed-slot'),
    ('no-handler-delivery', 'core',
     'count = handle->handle_events(handle, vals,\n\t\t\t\t\t\t\t      count);',
     'count = count - 0;', 'down-move-up'),
    ('ignore-handle-open', 'core', 'if (handle->open) {',
     'if (true) {', 'handler-closed'),
    ('late-capacity-flush', 'core', 'dev->num_vals >= dev->max_vals - 2',
     'dev->num_vals > dev->max_vals - 2', 'capacity'),
    ('wrong-synthetic-syn', 'core',
     'input_value_sync = { EV_SYN, SYN_REPORT, 1 };',
     'input_value_sync = { EV_SYN, SYN_REPORT, 0 };', 'capacity'),
)
DRIVER_MT_MUTANTS = (
    ('no-drop-unused', 'driver', 'INPUT_MT_DIRECT | INPUT_MT_DROP_UNUSED',
     'INPUT_MT_DIRECT', 'missing'),
    ('no-error-release', 'driver',
     '\t\trog5_fts_release(ts);\n\t\tdev_warn_ratelimited',
     '\t\tdev_warn_ratelimited', 'invalid-frame'),
    ('no-stop-release', 'driver',
     '\trog5_fts_release(ts);\n}\n\nstatic int rog5_fts_probe',
     '}\n\nstatic int rog5_fts_probe', 'suspend'),
    ('unmasked-tracking-id', 'mt', 'return mt->trkid++ & TRKID_MAX;',
     'return mt->trkid++;', 'wrap-oldest'),
    ('preincrement-tracking-id', 'mt', 'return mt->trkid++ & TRKID_MAX;',
     'return ++mt->trkid & TRKID_MAX;', 'wrap-oldest'),
    ('numeric-oldest', 'mt', 'if ((id - oldid) & TRKID_SGN)',
     'if (id < oldid)', 'wrap-oldest'),
    ('no-pointer-emulation', 'mt',
     '\tinput_mt_report_pointer_emulation(dev, use_count);',
     '\t(void)use_count;', 'down-move-up'),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cut(source, signature):
    require(source.count(signature) == 1, 'definition not unique: ' + signature)
    begin = source.index(signature)
    return source[begin:source.index('\n}', begin) + 2]


def once(source, old, new):
    require(source.count(old) == 1, 'splice/mutation target not unique: ' + repr(old))
    return source.replace(old, new, 1)


def section(data, entry):
    start = data.index(('## ' + entry['label'] + '\n').encode())
    start = data.index(b'```text\n', start) + len(b'```text\n')
    end = data.index(b'\n```\n', start) + 1
    body = data[start:end]
    candidates = [v for v in (body, body[:-1])
                  if len(v) == entry['bytes'] and sha(v) == entry['sha256']]
    require(len(candidates) == 1, 'packet section differs: ' + entry['label'])
    return candidates[0]


def sources(args, pins):
    entries = {e['label']: e for e in pins['sources']}
    originals = {}
    if args.packet:
        data = args.packet.read_bytes()
        require(len(data) == pins['packet_bytes'] and sha(data) == pins['packet_sha256'],
                'packet hash/length differs')
        if args.packet_manifest:
            supplied = json.loads(args.packet_manifest.read_text())
            for k in ('repo_head', 'kernel_base', 'packet_bytes', 'packet_sha256'):
                require(supplied[k] == pins[k], 'packet manifest differs: ' + k)
            got = [{k: e[k] for k in ('label', 'bytes', 'sha256')}
                   for e in supplied['sources']]
            require(got == pins['sources'], 'packet manifest section pins differ')
        originals = {label: section(data, e) for label, e in entries.items()}
        print(f'PASS packet and all {len(originals)} section hashes', flush=True)
    else:
        require(not args.packet_manifest, '--packet-manifest requires --packet')
        for label, entry in entries.items():
            if not label.startswith('linux/'):
                continue
            rel = label[len('linux/'):]
            if '#' in rel:
                raw = (args.linux_source / rel.split('#')[0]).read_bytes()
                # Only disable_irq was supplied as a function. Authenticate
                # that precise function; do not claim a whole manage.c check.
                data = cut(raw.decode(), 'void disable_irq(').encode()
            else:
                data = (args.linux_source / rel).read_bytes()
            require(len(data) == entry['bytes'] and sha(data) == entry['sha256'],
                    'Linux source differs: ' + label)
            originals[label] = data
        print('PASS 9 complete Linux files and exact disable_irq source hashes', flush=True)
    # Existing production and lifecycle files are not changed or rerun. All
    # compiled/reused files must still be the supplied baseline, also under -O.
    for label, entry in entries.items():
        if label.startswith('repo/'):
            file = ROOT / label[len('repo/'):]
            data = file.read_bytes()
            require(len(data) == entry['bytes'] and sha(data) == entry['sha256'],
                    'baseline repository input differs: ' + str(file))
    return {k[len('linux/'):]: v.decode() for k, v in originals.items()
            if k.startswith('linux/')}


def compose(linux):
    audit = []
    mt = (OLD / 'kernel-v7.1.4.c').read_text()
    for rel, names in OLD_FUNCS.items():
        for name in names:
            body = cut(linux[rel], name)
            require(mt.count(body) == 1, 'existing Linux extract differs: ' + name)
            audit.append({'source': rel, 'signature': name,
                          'sha256': sha(body.encode()), 'body': body})
    ic = linux['drivers/input/input.c']
    ih = linux['include/linux/input.h']
    mh = linux['include/linux/input/mt.h']
    uh = linux['include/uapi/linux/input.h']
    exact = []
    for rel, names in (
        ('include/linux/input.h', ('static inline void input_report_abs(',
                                  'static inline void input_sync(')),
        ('include/linux/input/mt.h', ('static inline bool input_is_mt_value(',)),
        ('drivers/input/input.c', CORE_FUNCS),
    ):
        for name in names:
            body = cut(linux[rel], name)
            exact.append(body)
            audit.append({'source': rel, 'signature': name,
                          'sha256': sha(body.encode()), 'body': body})
    # The macro itself, rather than a remembered expansion of the accessor.
    accessors = ih[ih.index('#define INPUT_GENERATE_ABS_ACCESSORS('):
                   ih.index('INPUT_GENERATE_ABS_ACCESSORS(val, value)') +
                   len('INPUT_GENERATE_ABS_ACCESSORS(val, value)')]
    dispositions = ic[ic.index('#define INPUT_IGNORE_EVENT'):
                      ic.index('\n\n', ic.index('#define INPUT_IGNORE_EVENT'))]
    sync = re.search(r'^static const struct input_value input_value_sync = .*;$',
                     ic, re.M).group(0)
    attribution = ic[:ic.index('#define pr_fmt')]
    core = '\n\n'.join((attribution, accessors, dispositions, sync, *exact)) + '\n'
    types = (HERE / 'types.h.in').read_text()
    for marker, text, signature in (
        ('INPUT_VALUE', ih, 'struct input_value {'),
        ('INPUT_CLOCK', ih, 'enum input_clock_type {'),
        ('INPUT_ABSINFO', uh, 'struct input_absinfo {'),
        ('INPUT_MT_SLOT', mh, 'struct input_mt_slot {'),
        ('INPUT_HANDLER', ih, 'struct input_handler {'),
        ('INPUT_HANDLE', ih, 'struct input_handle {'),
    ):
        types = once(types, '@' + marker + '@', cut(text, signature) + ';')
    stub = (OLD / 'stubs.h').read_text()
    stub = once(stub, '#include <linux/input-event-codes.h>',
                '#include "input-event-codes.h"')
    # Pin input constants to the supplied headers, not /usr/include.
    for name, text in [(n, mh) for n in ('INPUT_MT_POINTER', 'INPUT_MT_DIRECT',
                         'INPUT_MT_DROP_UNUSED', 'INPUT_MT_TRACK', 'INPUT_MT_SEMI_MT',
                         'INPUT_MT_TOTAL_FORCE', 'TRKID_MAX')] + [
        ('TRKID_SGN', linux['drivers/input/input-mt.c']),
        ('ABS_MT_FIRST', ih), ('ABS_MT_LAST', ih),
        ('MT_TOOL_FINGER', uh), ('BUS_I2C', uh),
    ]:
        pattern = r'^#define ' + name + r'\s+[^\n]+'
        original = re.search(pattern, stub, re.M).group(0)
        replacement = re.search(pattern, text, re.M).group(0)
        stub = once(stub, original, replacement)
    begin, end = stub.index('struct input_mt_slot {'), stub.index('struct action {')
    stub = stub[:begin] + types + '\n' + stub[end:]
    begin = stub.index('static int input_abs_get_val(')
    end = stub.index('static struct input_mt *fixture_alloc_mt(', begin)
    stub = stub[:begin] + '/* API sink removed: exact input.c is compiled below. */\n' + stub[end:]
    stub = once(stub, '\tinput.valid = true;',
                '\tinput.valid = true;\n\tfixture_input_allocate(&input);')
    stub = once(stub, '\tdev->registered = true;',
                '\tfixture_input_register(dev);\n\tdev->registered = true;')
    require('#define input_handle_event' not in stub, 'input_handle_event must not be aliased')
    full_driver = DRIVER.read_text()
    driver = full_driver[full_driver.index('enum rog5_fts_vote {'):
                         full_driver.index('static const struct of_device_id ')]
    parts = {
        'stub': stub + '\n' + (HERE / 'boundary.h').read_text(),
        'core': core, 'mt': mt, 'driver': driver,
        'cases': '\n#define main unused_lifecycle_main\n' + (OLD / 'cases.c').read_text() +
                 '\n#undef main\n' + (HERE / 'cases.c').read_text(),
    }
    whole = '\n'.join(parts.values())
    for row in audit:
        require(whole.count(row['body']) == 1,
                'compiled definition differs/duplicated: ' + row['signature'])
        row.pop('body')
    print(f'PASS applicability: {len(audit)} exact function bodies (14 retained + 18 new); '
          '6 declarations, accessor macro and input constants extracted', flush=True)
    return parts, audit


def disk_backed(path):
    # Linux mountinfo provides filesystem type without needing root or stat(1).
    # Follow the most specific enclosing mount; reject in-memory filesystems.
    resolved = path.resolve()
    mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        point = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), left.split()[4])
        mount = Path(point)
        if resolved == mount or mount in resolved.parents:
            mounts.append((len(mount.parts), right.split()[0]))
    require(mounts, 'cannot establish scratch filesystem')
    fs = max(mounts)[1]
    require(fs not in ('tmpfs', 'ramfs', 'hugetlbfs'), 'scratch must be disk-backed: ' + fs)
    return fs


def main(owner):
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group()
    src.add_argument('--packet', type=Path)
    src.add_argument('--linux-source', type=Path)
    p.add_argument('--packet-manifest', type=Path)
    p.add_argument('--batch', choices=('all', 'cases', 'core-mutants', 'driver-mt-mutants'),
                   default='all')
    p.add_argument('--report-dir', type=Path,
                   help='new directory for source comparison, unit, and per-command disk logs')
    args = p.parse_args()
    if args.packet is None and args.linux_source is None:
        source = os.environ.get('ROG5_LINUX_SOURCE')
        args.linux_source = Path(source) if source else None
    if args.packet is None and (args.linux_source is None or not args.linux_source.is_dir()):
        print('BLOCKED exact kernel source: use --linux-source or ROG5_LINUX_SOURCE', flush=True)
        return 2
    require(os.geteuid() != 0, 'run unprivileged, not as root')
    require(platform.machine() == 'x86_64', 'this fixture is reviewed for x86_64 hosts only')
    # Some host site hooks reserve hundreds of MiB before this script starts.
    # Do not silently impose a limit below the interpreter's existing mappings.
    status = Path('/proc/self/status').read_text()
    virtual = int(re.search(r'^VmSize:\s+(\d+) kB$', status, re.M)[1]) * 1024
    require(virtual + 64 * 1024**2 < 384 * 1024**2,
            'interpreter virtual footprint too large; run python3 -S -O ' + str(Path(__file__)))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (384 * 1024**2, 384 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    started = time.monotonic()
    deadline = started + 85
    pins = json.loads((HERE / 'source-pins.json').read_text())
    watched = [DRIVER, DRIVER.with_name('rog5_fts_protocol.h'),
               ROOT / 'scripts/device/test-rog5-touch-lifecycle.py',
               *sorted(OLD.glob('*')), *sorted(HERE.glob('*')),
               Path(__file__).resolve()]
    before = {str(f): sha(f.read_bytes()) for f in watched if f.is_file()}
    print('repo_base=' + pins['repo_head'] + ' linux_base=' + pins['kernel_base'], flush=True)
    linux = sources(args, pins)
    parts, audit = compose(linux)
    scratch = ROOT / 'build'
    scratch.mkdir(exist_ok=True)
    fs = disk_backed(scratch)
    if args.report_dir:
        args.report_dir.parent.mkdir(parents=True, exist_ok=True)
        disk_backed(args.report_dir.parent)
        args.report_dir.mkdir(exist_ok=False)
    mutations = ()
    if args.batch in ('all', 'core-mutants'):
        mutations += CORE_MUTANTS
    if args.batch in ('all', 'driver-mt-mutants'):
        mutations += DRIVER_MT_MUTANTS
    cases = CASES if args.batch in ('all', 'cases') else tuple(
        c for c in CASES if c in {m[4] for m in mutations})
    print(f'host={platform.machine()} python={platform.python_version()} uid={os.geteuid()} '
          f'python_no_site={sys.flags.no_site} scratch_fs={fs} batch={args.batch}', flush=True)
    compiler = shutil.which(os.environ.get('CC', 'cc'))
    require(compiler, 'CC executable not found (use a path, not a shell command)')
    compiler = str(Path(compiler).resolve())
    toolchain = {'path': compiler, 'sha256': sha(Path(compiler).read_bytes())}
    results = []
    with owner.scratch(scratch) as tmp:
        (tmp / 'input-event-codes.h').write_text(linux['include/uapi/linux/input-event-codes.h'])
        env = dict(os.environ, TMPDIR=str(tmp), LC_ALL='C')
        for name in ('CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'GCC_EXEC_PREFIX',
                     'COMPILER_PATH', 'LIBRARY_PATH'):
            env.pop(name, None)

        def run(argv, label, limit):
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'focused batch exhausted 85-second deadline')
            log = tmp / (label + '.log')
            with log.open('wb') as stream:
                try:
                    rc = owner.run(argv, stream, env, min(limit, remaining))
                except BaseException:
                    # This runs only AFTER the ownership drain attempt. Preserve
                    # diagnostics even on cancellation; never report a mutant kill.
                    stream.flush()
                    if args.report_dir:
                        shutil.copyfile(log, args.report_dir / log.name)
                    raise
            raw = log.read_bytes()
            if args.report_dir:
                (args.report_dir / log.name).write_bytes(raw)
            results.append({'label': label, 'argv': list(map(str, argv)), 'exit': rc,
                            'log_sha256': sha(raw)})
            return rc, raw.decode(errors='replace')

        def compile_unit(label, components):
            text = '\n'.join(components.values())
            unit, binary = tmp / (label + '.c'), tmp / label
            unit.write_text(text)
            argv = [compiler, '-std=gnu11', '-O1', '-Wall', '-Wextra',
                    '-Werror', '-Wno-unused-parameter', '-Wno-unused-function', '-pthread',
                    '-fsanitize=undefined', '-fno-sanitize-recover=all',
                    '-I', str(DRIVER.parent), '-I', str(tmp), str(unit), '-o', str(binary)]
            rc, log = run(argv, 'compile-' + label, 30)
            require(rc == 0, 'compile failed (not a mutation kill): ' + label + '\n' + log)
            print('PASS compilation: ' + label, flush=True)
            if label == 'baseline':
                print('compiled_unit_sha256=' + sha(unit.read_bytes()), flush=True)
                if args.report_dir:
                    (args.report_dir / 'compiled-unit.c').write_bytes(unit.read_bytes())
            return binary

        rc, version = run([compiler, '--version'], 'compiler-version', 5)
        require(rc == 0, 'compiler version command failed')
        toolchain['version'] = version.splitlines()[0]
        print('compiler=' + toolchain['version'] + ' sha256=' + toolchain['sha256'], flush=True)
        baseline = compile_unit('baseline', parts)
        for case in cases:
            rc, log = run([str(baseline), case], 'case-' + case, 5)
            require(rc == 0, 'semantic case failed: ' + case + '\n' + log)
            print('PASS behavioral: delivered ' + case, flush=True)
        for label, component, old, new, case in mutations:
            mutated = dict(parts)
            mutated[component] = once(mutated[component], old, new)
            binary = compile_unit(label, mutated)
            rc, log = run([str(binary), case], 'mutant-' + label, 5)
            require(rc == 1 and 'FAIL ' in log and 'runtime error:' not in log,
                    'mutation did not fail a semantic CHECK: ' + label + '\n' + log)
            print('PASS behavioral: rejects ' + label + ': ' + log.strip(), flush=True)
    after = {str(f): sha(f.read_bytes()) for f in watched if f.is_file()}
    require(before == after, 'test/source input changed during batch')
    summary = {'repo_base': pins['repo_head'], 'linux_base': pins['kernel_base'],
               'source_comparisons': audit, 'inputs': before, 'commands': results,
               'source_mode': 'packet' if args.packet else 'local-files',
               'source_pins': pins, 'status': 'PASS offline handler-boundary semantics',
               'cases': list(cases), 'mutants': [m[0] for m in mutations],
               'elapsed_seconds': time.monotonic() - started,
               'python': sys.version, 'python_no_site': sys.flags.no_site,
               'host': platform.machine(), 'toolchain': toolchain,
               'physical': 'NOT RUN', 'evdev_libinput': 'NOT RUN'}
    if args.report_dir:
        (args.report_dir / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'PASS behavioral: delivered: {len(cases)} cases; {len(mutations)} semantic mutation controls; '
          f'{len(audit)} exact function comparisons; elapsed={summary["elapsed_seconds"]:.3f}s')
    print('PASS applicability: preserved production driver and existing lifecycle sources byte-for-byte')
    print('NOT RUN existing 27/8 lifecycle execution (unchanged; historical evidence retained)')
    print('NOT RUN kernel locking/RCU/timers, evdev/libinput, ARM64 build, physical touch/rails/PM')


def entrypoint():
    try:
        with OwnedCommands() as owner:
            return main(owner) or 0
    except (Exception, KeyboardInterrupt) as exc:
        print('FAIL harness: ' + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(entrypoint())
