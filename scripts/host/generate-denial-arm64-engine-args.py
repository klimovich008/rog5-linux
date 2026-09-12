#!/usr/bin/env python3
"""Generate exact-source ARM64 engine arguments; never run GN, Ninja or hooks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
FLAGS = ['--runtime-mode=release', '--enable-fontconfig', '--target-os=linux',
         '--linux-cpu=arm64', '--embedder-for-target', '--no-prebuilt-dart-sdk']
REQUIRED = {'host_os': 'linux', 'host_cpu': 'x64', 'target_os': 'linux',
            'target_cpu': 'arm64', 'dart_target_arch': 'arm64',
            'embedder_for_target': True, 'flutter_runtime_mode': 'release',
            'flutter_use_fontconfig': True, 'concurrent_toolchain_jobs': 1}


def require_profile(args):
    for key, value in REQUIRED.items():
        if type(args.get(key)) is not type(value) or args[key] != value:
            raise ValueError(f'wrong ARM64 engine argument: {key}')
    if args.get('flutter_prebuilt_dart_sdk', False) is not False:
        raise ValueError('unqualified prebuilt Dart SDK refused')


def generate(gn):
    args = gn['to_gn_args'](gn['parse_args'](['gn', *FLAGS]))
    # Upstream sizes this from host RAM, outside our build resource budget.
    args['concurrent_toolchain_jobs'] = 1
    require_profile(args)
    return args, '\n'.join(gn['to_command_line'](args)) + '\n'


def verify_source(source, lock):
    entries = [(source, lock['engine_sources']['flutter']['revision']),
               (source / 'engine/src/flutter/third_party/skia', lock['engine_sources']['skia']['revision'])]
    deps = (source / 'DEPS').read_text()
    matches = re.findall(r"^\s*'dart_revision': '([0-9a-f]{40})',?$", deps, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError('missing or ambiguous pinned Dart revision')
    entries.append((source / 'engine/src/flutter/third_party/dart', matches[0]))
    for path, wanted in entries:
        actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True, timeout=15).strip()
        if actual != wanted:
            raise ValueError(f'wrong source revision: {path.name}')
        changed = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no'], text=True, timeout=30)
        if changed:
            raise ValueError(f'tracked source changes: {path.name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='locked Flutter checkout root')
    parser.add_argument('--output', type=Path, required=True, help='new external GN output directory')
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    # No writes to the frozen source or an existing configuration.
    if output.is_relative_to(source):
        raise ValueError('output must be outside the source checkout')
    output.mkdir()
    started = time.monotonic()
    record = {'argument_status': 'NOT RUN', 'graph_status': 'NOT RUN', 'build_status': 'NOT RUN',
              'physical_status': 'NOT RUN', 'authority': 'none', 'flags': FLAGS}
    try:
        lock_path = ROOT / 'configs/denial/source-lock-v1.json'
        lock = json.loads(lock_path.read_text())
        verify_source(source, lock)
        script = source / 'engine/src/flutter/tools/gn'
        sys.dont_write_bytecode = True
        gn = runpy.run_path(str(script))
        values, text = generate(gn)
        # Dart is verified against pinned DEPS. Complete gclient/hooks closure
        # and real GN/Ninja execution still require separate evidence.
        record.update(source_revision=lock['engine_sources']['flutter']['revision'],
                      source_lock_sha256=hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                      generator_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                      versions={k: values[k] for k in ('engine_version', 'skia_version', 'dart_version', 'content_hash')})
        path = output / 'args.gn'
        path.write_text(text)
        record.update(argument_status='PASS', args_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        command = [str(source / 'engine/src/flutter/third_party/gn/gn'), 'gen', '--check', str(output)]
        record['graph_command'] = command
    except Exception as error:
        record['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        record['duration_seconds'] = time.monotonic() - started
        (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS ARM64 arguments; graph=' + record['graph_status'] + '; compilation and physical validation NOT RUN')


if __name__ == '__main__':
    main()
