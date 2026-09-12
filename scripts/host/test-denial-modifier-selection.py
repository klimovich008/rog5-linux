#!/usr/bin/env python3
"""Run the actual pinned Denial modifier selectors before/after the local patch.

Data adapters represent only the Format/FormatSet values the functions consume;
this test does not emulate GBM, EGL, DRM or physical hardware.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

BASE = '85b2303e2f09ae7b7b993641f90061a200f03d53'
SOURCE = 'compositor/src/bin/deniald/kms_state.rs'
PATCH = 'patches/denial-85b2303e/0001-preserve-implicit-render-modifier-contract.patch'

ADAPTERS = r"""
#[derive(Clone,Copy,Debug,PartialEq,Eq)] enum Fourcc { Xrgb8888 }
#[derive(Clone,Copy,Debug,PartialEq,Eq)] enum Modifier { Linear, Invalid, Tiled }
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct Format { code: Fourcc, modifier: Modifier }
type FormatSet = Vec<Format>;
"""
TESTS = r"""
fn formats(modifiers: &[Modifier]) -> FormatSet { modifiers.iter().map(|&modifier| Format {code:Fourcc::Xrgb8888,modifier}).collect() }
#[test] fn implicit_everywhere_requests_implicit() {
 let plane=formats(&[Modifier::Invalid]);let render=plane.clone();
 assert_eq!(compatible_xrgb8888_modifiers([&plane],&render),vec![Modifier::Invalid]);
}
#[test] fn explicit_linear_is_not_inferred_from_implicit_renderer() {
 let plane=formats(&[Modifier::Linear,Modifier::Invalid]);let render=formats(&[Modifier::Invalid]);
 assert_eq!(compatible_xrgb8888_modifiers([&plane],&render),vec![Modifier::Invalid]);
}
#[test] fn plane_without_implicit_support_must_refuse_implicit_renderer() {
 let plane=formats(&[Modifier::Linear]);let render=formats(&[Modifier::Invalid]);
 assert!(compatible_xrgb8888_modifiers([&plane],&render).is_empty());
}
#[test] fn explicit_intersection_preserves_preference() {
 let plane=formats(&[Modifier::Tiled,Modifier::Linear,Modifier::Invalid]);let render=plane.clone();
 assert_eq!(compatible_xrgb8888_modifiers([&plane],&render),vec![Modifier::Tiled,Modifier::Linear]);
}
#[test] fn every_plane_must_share_the_selected_mode() {
 let a=formats(&[Modifier::Tiled,Modifier::Invalid]);let b=formats(&[Modifier::Linear]);let render=formats(&[Modifier::Tiled,Modifier::Linear,Modifier::Invalid]);
 assert!(compatible_xrgb8888_modifiers([&a,&b],&render).is_empty());
 assert!(compatible_xrgb8888_modifiers([], &render).is_empty());
}
"""


def extract(source, name):
    start = source.index('fn ' + name)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='retained exact upstream Denial Git repository')
    parser.add_argument('--output', type=Path, required=True,
                        help='fresh disk-backed test output')
    args = parser.parse_args()
    rustc = os.environ.get('RUSTC', 'rustc')
    if not shutil.which(rustc):
        parser.error('BLOCKED: selected Rust compiler unavailable')
    original = subprocess.check_output(
        ['git', '-C', str(args.source), 'show', BASE + ':' + SOURCE],
        timeout=10, text=True)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    stage = output / 'source'
    target = stage / SOURCE
    target.parent.mkdir(parents=True)
    target.write_text(original)
    repo = Path(__file__).resolve().parents[2]
    patch = repo / PATCH
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=stage,
                   check=True, timeout=10)
    subprocess.run(['git', 'apply', str(patch)], cwd=stage,
                   check=True, timeout=10)
    result = {'scope': 'actual extracted selector functions; no GBM/EGL/phone proof',
              'source_commit': BASE, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'physical': 'NOT RUN', 'runs': {}}
    env = dict(os.environ, TMPDIR=str(output))
    for label, source in [('before', original), ('after', target.read_text())]:
        unit = ADAPTERS + '\n'.join(extract(source, name) for name in (
            'common_xrgb8888_modifiers', 'compatible_xrgb8888_modifiers')) + TESTS
        path = output / (label + '.rs')
        path.write_text(unit)
        binary = output / label
        command = [rustc, '--edition=2024', '--test', str(path), '-o', str(binary)]
        start = time.monotonic()
        subprocess.run(command, env=env, check=True, capture_output=True, timeout=30)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
        (output / (label + '.log')).write_text(run.stdout + run.stderr)
        expected = '2 passed; 3 failed' if label == 'before' else '5 passed; 0 failed'
        passed = expected in run.stdout and run.returncode == (101 if label == 'before' else 0)
        result['runs'][label] = {'command': command, 'test_command': [str(binary)],
                                 'exit_status': run.returncode,
                                 'duration_seconds': time.monotonic() - start,
                                 'expected_result_observed': passed,
                                 'source_sha256': hashlib.sha256(unit.encode()).hexdigest()}
    result['status'] = 'PASS' if all(r['expected_result_observed'] for r in result['runs'].values()) else 'FAIL'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
