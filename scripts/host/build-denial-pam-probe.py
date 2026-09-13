#!/usr/bin/env python3
"""Compile the pinned, actual Denial PAM backend for an isolated ARM64 guest.

No PAM adapter or duplicate authentication model: the backend, conversation,
secret erasure and result mapping are copied without edits from the Git object.
Only the entry point supplies synthetic answers. This is not a target package.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import re
import resource
import uuid

BASE = '85b2303e2f09ae7b7b993641f90061a200f03d53'
SOURCE = 'compositor/src/bin/deniald/authentication.rs'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--toolchain-image', required=True,
                        help='retained full immutable Podman image ID, no pull')
    parser.add_argument('--libc', type=Path, required=True)
    parser.add_argument('--libloading', type=Path, required=True)
    parser.add_argument('--tracing', type=Path, required=True)
    parser.add_argument('--host-deps', type=Path, required=True,
                        help='matching retained host proc-macro dependency directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.toolchain_image):
        parser.error('BLOCKED: expected full immutable toolchain image ID')
    output = args.output.absolute()
    if output.exists():
        parser.error('output must be fresh')
    if shutil.disk_usage(output.parent).free < 3 * 1024**3 + 16 * 1024**2:
        parser.error('BLOCKED: insufficient space above 3 GiB reserve')
    try:
        source = subprocess.check_output(
            ['git', '-C', str(args.source), 'show', f'{BASE}:{SOURCE}'],
            timeout=10, stderr=subprocess.PIPE).decode()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        parser.error('BLOCKED: source must be a Git checkout containing the pinned Denial object')
    if (args.source / SOURCE).read_text() != source:
        parser.error('working authentication source differs from pinned Git object')
    start, end = 'struct SecureString {', 'fn default_backend()'
    if source.count(start) != 1 or source.count(end) != 1:
        parser.error('unexpected authentication source boundaries')
    fragment = source[source.index(start):source.index(end)]
    imports = ('use std::ffi::{CStr, CString, c_char, c_int, c_void};\n'
               'use std::ptr;\nuse std::sync::atomic::{Ordering, compiler_fence};\n'
               'use libloading::Library;\nuse tracing::warn;\n')
    entry = Path(__file__).resolve().parents[2] / 'tools/denial-modifier-tests/pam-guest-main.rs'
    output.mkdir()
    unit = output / 'pam-probe.rs'
    unit.write_text(imports + fragment + entry.read_text())
    rust_command = ['/opt/denial-rust/bin/rustc', '--edition=2024', '--target=aarch64-unknown-linux-gnu',
               '--crate-name=denial_pam_probe', '--remap-path-prefix', f'{output}=/rog5-pam-probe',
               '-C', 'linker=/usr/bin/aarch64-linux-gnu-gcc', '-C', 'opt-level=2',
               '-C', 'lto=thin', '-C', 'codegen-units=1',
               '-C', 'strip=debuginfo', str(unit), '-o', str(output/'pam-probe')]
    for name in ('libc', 'libloading', 'tracing'):
        path = getattr(args, name).resolve(strict=True)
        rust_command += ['--extern', f'{name}={path}', '-L', f'dependency={path.parent}']
    rust_command += ['-L', f'dependency={args.host_deps.resolve(strict=True)}']
    name = 'rog5-pam-build-' + uuid.uuid4().hex
    command = ['podman', 'run', '--rm', '--pull=never', '--name', name,
               '--network=none', '--read-only', '--memory=512m', '--memory-swap=512m',
               '--cpus=1', '--pids-limit=128',
               '-v', f'{Path.home()}:{Path.home()}:ro', '-v', f'{output}:{output}:rw',
               '--env', f'TMPDIR={output}', args.toolchain_image, *rust_command]
    started = time.monotonic()
    exit_status = 124
    try:
        with (output/'build.log').open('xb') as log:
            build = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=60,
                                   preexec_fn=lambda: resource.setrlimit(
                                       resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2)))
            exit_status = build.returncode
    except subprocess.TimeoutExpired:
        pass
    finally:
        cleanup = subprocess.run(['podman', 'rm', '--force', '--ignore', name],
                                 capture_output=True, timeout=15)
    result = {'status': 'PASS' if exit_status == 0 and cleanup.returncode == 0 else 'FAIL',
              'scope': 'actual ARM64 Denial PAM backend compilation only; execution NOT RUN',
              'denial_commit': BASE, 'command': command, 'exit_status': exit_status,
              'cleanup_exit_status': cleanup.returncode,
              'toolchain_image': args.toolchain_image,
              'duration_seconds': time.monotonic()-started,
              'authentication_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'fragment_sha256': hashlib.sha256(fragment.encode()).hexdigest(),
              'inputs': {str(p): sha(p) for p in [Path(__file__), entry,
                                                args.libc, args.libloading, args.tracing]},
              'outputs': {p.name: sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
