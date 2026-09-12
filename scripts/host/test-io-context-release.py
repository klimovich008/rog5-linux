#!/usr/bin/env python3
"""Run actual pinned engine IO and Denial clear callback bodies before/after fixes.

The adapters do not prove EGL, engine ABI, VM or phone behavior. Exact ARM64
compilation and runtime qualification are separate checks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ENGINE = 'd728e61e7d835e02c453c70ae9523a40f6c03215'
DENIAL = '85b2303e2f09ae7b7b993641f90061a200f03d53'
EP = 'engine/src/flutter/shell/platform/embedder/'
DP = 'compositor/src/bin/deniald/flutter_runtime/renderer/'


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-source', type=Path, required=True)
    parser.add_argument('--denial-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    cxx, rustc = os.environ.get('CXX', 'c++'), os.environ.get('RUSTC', 'rustc')
    if not all(shutil.which(c) for c in (cxx, rustc)):
        parser.error('BLOCKED: C++ and Rust compilers are required')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source'
    inputs = {}

    def load(checkout, revision, path):
        content = subprocess.check_output(
            ['git', '-C', str(checkout), 'show', revision + ':' + path], timeout=10)
        file = source / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)
        inputs[path] = hashlib.sha256(content).hexdigest()
        return content.decode()

    for name in ('embedder_surface.h', 'platform_view_embedder.h',
                 'platform_view_embedder.cc', 'embedder_surface_gl_impeller.h',
                 'embedder_surface_gl_impeller.cc'):
        load(args.engine_source, ENGINE, EP + name)
    base_release = load(args.engine_source, ENGINE,
                        'engine/src/flutter/shell/common/platform_view.cc')
    for name in ('gl.rs', 'handler.rs', 'handler/open_gl.rs'):
        load(args.denial_source, DENIAL, DP + name)

    def apply(name):
        patch = repo / name
        for flags in (['--check'], []):
            subprocess.run(['git', 'apply', *flags, str(patch)],
                           cwd=source, check=True, timeout=10)
        return hashlib.sha256(patch.read_bytes()).hexdigest()

    patches = {}
    trace = 'patches/denial-85b2303e/0004-trace-egl-context-ownership.patch'
    patches[trace] = apply(trace)
    before = {p: (source / p).read_text() for p in inputs}
    for patch in ('patches/flutter-engine-d728e61e/0002-release-impeller-io-context.patch',
                  'patches/denial-85b2303e/0005-clear-current-io-resource-context.patch'):
        patches[patch] = apply(patch)
    after = {p: (source / p).read_text() for p in inputs}
    result = {'scope': __doc__, 'engine_base': ENGINE, 'denial_base': DENIAL,
              'input_hashes': inputs, 'patch_hashes': patches, 'runs': []}
    cpp_fixture = (repo / 'tools/denial-engine-tests/io-release.cc').read_text()
    rust_fixture = (repo / 'tools/denial-modifier-tests/io-clear.rs').read_text()
    for label, files in [('before', before), ('after', after)]:
        surface = files[EP + 'embedder_surface_gl_impeller.cc']
        methods = 'sk_sp<GrDirectContext>\n' + function(
            surface, 'EmbedderSurfaceGLImpeller::CreateResourceContext()')
        if label == 'after':
            methods += '\nvoid ' + function(surface,
                'EmbedderSurfaceGLImpeller::ReleaseResourceContext()')
            methods += '\nvoid ' + function(files[EP + 'platform_view_embedder.cc'],
                'PlatformViewEmbedder::ReleaseResourceContext()')
        else:
            methods += '\nvoid ' + function(base_release,
                'PlatformView::ReleaseResourceContext()').replace(
                    'PlatformView::', 'PlatformViewEmbedder::', 1)
        cpp = cpp_fixture.replace('// @METHODS@', methods).replace(
            '// @SURFACE_DECL@', 'void ReleaseResourceContext() const override;'
            if label == 'after' else '')
        binding = function(files[DP + 'gl.rs'], 'pub(super) fn clear_current(').replace(
            'pub(super) ', '', 1)  # The fixture places the same method at crate root.
        callback = function(files[DP + 'handler/open_gl.rs'], 'fn clear_current(')
        rust = rust_fixture.replace('// @BINDING@', binding).replace('// @CALLBACK@', callback)
        for language, code, compiler, flags, modes, old_failures in (
                ('cpp', cpp, cxx, ['-std=c++17', '-pthread', '-Wall', '-Wextra', '-Werror'],
                 ['normal', 'repeated-bind', 'clear-failure', 'bind-failure', 'null-surface'],
                 {'normal', 'repeated-bind', 'clear-failure'}),
                ('rs', rust, rustc, ['--edition=2024'],
                 ['resource', 'resource-failure', 'wrong-owner', 'render'],
                 {'resource', 'resource-failure'})):
            unit = output / (label + '.' + language)
            unit.write_text(code)
            binary = output / (label + '-' + language)
            command = [compiler, *flags, str(unit), '-o', str(binary)]
            started = time.monotonic()
            build = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                   env=dict(os.environ, TMPDIR=str(output)))
            (output / (label + '-' + language + '-build.log')).write_text(build.stdout + build.stderr)
            build.check_returncode()
            result['runs'].append({'kind': 'build', 'command': command,
                                   'duration_seconds': time.monotonic() - started,
                                   'exit_status': build.returncode, 'expected_observed': True})
            for mode in modes:
                command = [str(binary), mode]
                started = time.monotonic()
                run = subprocess.run(command, capture_output=True, text=True, timeout=5)
                (output / (label + '-' + language + '-' + mode + '.log')).write_text(run.stdout + run.stderr)
                expected = 1 if label == 'before' and mode in old_failures else 0
                result['runs'].append({'kind': 'test', 'label': label, 'language': language,
                    'mode': mode, 'command': command, 'exit_status': run.returncode,
                    'expected_exit_status': expected, 'expected_observed': run.returncode == expected,
                    'duration_seconds': time.monotonic() - started})
    result['status'] = 'PASS' if all(r['expected_observed'] for r in result['runs']) else 'FAIL'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'runs': len(result['runs']),
                      'result': str(output / 'result.json')}))
    return result['status'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
