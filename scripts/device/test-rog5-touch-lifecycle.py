#!/usr/bin/env python3
"""Exercise actual FTS3658U driver/probe code with faulted hardware APIs.

Exact Linux7.1.4 IRQ-disable and multitouch functions are compiled too; the
remaining input/devres/GPIO/I2C/regulator boundaries are fixtures. Regulator
failure preserves votes in this controlled fixture; actual-core error effects
are covered separately by test-rog5-touch-regulator-errors.py. Never loads a module,
uses a phone, changes DT, or establishes physical touch/power qualification.
"""
import argparse
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / 'tools/rog5-fts3658u/rog5_fts3658u.c'
FIXTURES = ROOT / 'scripts/device/fixtures/fts3658u'
CASES = ('probe-unwind', 'vote-vdd-unknown', 'vote-io-unknown', 'off-reset-error',
         'off-io-error', 'normal-id-refusal', 'irq-short-transfer', 'irq-io-error',
         'irq-invalid-frame', 'irq-drop-unused', 'shutdown-idempotent',
         'shutdown-drains-irq', 'suspend-refused', 'prepare-cleanup-unknown',
         'irq-at-registration', 'normal-power-cycles')


def driver_unit(source):
    # Compile all actual callbacks, the power/ID/parser paths and full probe.
    # Omit only kernel includes and static registration/PM metadata.
    begin = source.index('enum rog5_fts_vote {')
    end = source.index('static DEFINE_SIMPLE_DEV_PM_OPS(')
    return source[begin:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-source', type=Path,
                        default=os.environ.get('ROG5_LINUX_SOURCE'))
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    kernel = (FIXTURES / 'kernel-v7.1.4.c').read_text()
    if args.linux_source:
        for relative, names in (
                ('kernel/irq/manage.c', ('void disable_irq(',)),
                ('drivers/input/input-mt.c', ('bool input_mt_report_slot_state(',
                 'static void __input_mt_drop_unused(', 'void input_mt_sync_frame('))):
            original = (args.linux_source / relative).read_text()
            for signature in names:
                begin = original.index(signature)
                if original[begin:original.index('\n}', begin) + 2] not in kernel:
                    raise ValueError('kernel fixture differs: ' + signature)
        print('PASS behavioral: exact-kernel extracted IRQ and input functions compared')
    else:
        print('NOT RUN external kernel-source comparison; pinned extract is compiled')
    inputs = [DRIVER, DRIVER.with_name('rog5_fts_protocol.h'),
              *sorted(FIXTURES.glob('*'))]
    pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    source = DRIVER.read_text()
    prefix = (FIXTURES / 'stubs.h').read_text() + '\n' + kernel + '\n'
    suffix = '\n' + (FIXTURES / 'cases.c').read_text()
    started = time.monotonic()
    scratch = ROOT / 'build'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fts3658u-lifecycle-', dir=scratch) as tmp:
        tmp = Path(tmp)

        def compile_source(label, body):
            unit = tmp / (label + '.c')
            binary = tmp / label
            unit.write_text(prefix + driver_unit(body) + suffix)
            subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1',
                            '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                            '-Wno-unused-function', '-pthread', '-fsanitize=undefined',
                            '-fno-sanitize-recover=all', '-I', str(DRIVER.parent),
                            str(unit), '-o', str(binary)], check=True, timeout=30)
            if label == 'driver':
                print('compiled_unit_sha256=' + hashlib.sha256(unit.read_bytes()).hexdigest())
            return binary

        binary = compile_source('driver', source)
        for case in CASES:
            start = time.monotonic()
            subprocess.run([str(binary), case], check=True, timeout=5)
            print(f'PASS {case} elapsed={time.monotonic() - start:.6f}s', flush=True)
        mutations = (
            ('irq-drain', '\t\tdisable_irq(ts->client->irq);', '', 'shutdown-drains-irq'),
            ('vote-tracking', '\t\t\tts->vdd_vote = ROG5_FTS_VOTE_UNKNOWN;\n'
             '\t\t\tdev_err(dev, "VDD vote release failed:',
             '\t\t\tts->vdd_vote = ROG5_FTS_VOTE_HELD;\n'
             '\t\t\tdev_err(dev, "VDD vote release failed:', 'vote-vdd-unknown'),
            ('bad-frame-release', '\t\trog5_fts_release(ts);\n\t\tdev_warn_ratelimited',
             '\t\tdev_warn_ratelimited', 'irq-invalid-frame'),
        )
        for label, old, new, case in mutations:
            if source.count(old) != 1:
                raise ValueError('mutation target changed: ' + label)
            mutant = compile_source(label, source.replace(old, new, 1))
            result = subprocess.run([str(mutant), case], capture_output=True,
                                    text=True, timeout=5)
            if result.returncode == 0 or 'FAIL ' not in result.stderr:
                raise ValueError('mutation was not rejected by behavior: ' + label)
            print(f'PASS rejects mutation {label}: ' + result.stderr.strip())
    if pins != {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}:
        raise ValueError('source input changed during tests')
    print('driver_sha256=' + pins[DRIVER])
    print(f'PASS behavioral: {len(CASES)} actual-driver cases (13 probe failure stages), '
          f'3 mutation controls; elapsed={time.monotonic() - started:.6f}s')
    print('NOT RUN module loading, physical IRQ/input, rail behavior or suspend qualification')


if __name__ == '__main__':
    main()
