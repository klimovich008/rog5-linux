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
use std::{error::Error,cell::Cell,rc::Rc};
#[derive(Clone,Copy)] struct PixelSize { width:u32, height:u32 }
macro_rules! warn { ($($tokens:tt)*) => {{}} }
struct ScanoutBuffer { live:Rc<Cell<usize>> }
impl Drop for ScanoutBuffer { fn drop(&mut self) { self.live.set(self.live.get()-1); } }
struct ScanoutAllocator { calls:Vec<Vec<Modifier>>, live:Rc<Cell<usize>>, fail_on:Option<usize> }
impl ScanoutAllocator {
 fn new(fail_on:Option<usize>) -> Self { Self {calls:vec![],live:Rc::new(Cell::new(0)),fail_on} }
 fn allocate(&mut self, _size:PixelSize, modifiers:&[Modifier], _linear:bool) -> Result<ScanoutBuffer,Box<dyn Error>> {
  self.calls.push(modifiers.to_vec());
  if self.fail_on==Some(self.calls.len()) {return Err("injected allocation failure".into());}
  self.live.set(self.live.get()+1);Ok(ScanoutBuffer {live:self.live.clone()})
 }
}
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
#[test] fn implicit_pool_reaches_allocator_without_relabelling() {
 let mut a=ScanoutAllocator::new(None);
 let buffers=allocate_scanout_pool(&mut a,PixelSize{width:640,height:480},2,&[Modifier::Invalid],false).expect("implicit allocation");
 assert_eq!(a.calls,vec![vec![Modifier::Invalid];2]);assert_eq!(a.live.get(),2);drop(buffers);assert_eq!(a.live.get(),0);
}
#[test] fn implicit_pool_failure_releases_partial_allocations() {
 let mut a=ScanoutAllocator::new(Some(2));
 assert!(allocate_scanout_pool(&mut a,PixelSize{width:640,height:480},3,&[Modifier::Invalid],false).is_err());
 assert_eq!(a.calls.len(),2);assert_eq!(a.live.get(),0);
}
#[test] fn invalid_pool_dimensions_still_refuse_before_allocation() {
 let mut a=ScanoutAllocator::new(None);
 assert!(allocate_scanout_pool(&mut a,PixelSize{width:0,height:480},2,&[Modifier::Invalid],false).is_err());
 assert!(allocate_scanout_pool(&mut a,PixelSize{width:640,height:480},1,&[Modifier::Invalid],false).is_err());
 assert!(a.calls.is_empty());
}
#[test] fn optimized_failure_retains_existing_linear_fallback() {
 let mut a=ScanoutAllocator::new(Some(1));
 let buffers=allocate_scanout_pool(&mut a,PixelSize{width:640,height:480},2,&[Modifier::Tiled,Modifier::Linear],false).expect("linear fallback");
 assert_eq!(a.calls,vec![vec![Modifier::Tiled],vec![Modifier::Linear],vec![Modifier::Linear]]);
 drop(buffers);assert_eq!(a.live.get(),0);
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
        constants = '\n'.join(line for line in source.splitlines() if line.startswith(('const SCANOUT_BYTES_PER_PIXEL:', 'const MAX_SCANOUT_')))
        unit = ADAPTERS + constants + '\n'.join(extract(source, name) for name in (
            'common_xrgb8888_modifiers', 'compatible_xrgb8888_modifiers',
            'allocate_scanout_pool', 'validate_scanout_pool_allocation')) + TESTS
        path = output / (label + '.rs')
        path.write_text(unit)
        binary = output / label
        command = [rustc, '--edition=2024', '--test', str(path), '-o', str(binary)]
        start = time.monotonic()
        subprocess.run(command, env=env, check=True, capture_output=True, timeout=30)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
        (output / (label + '.log')).write_text(run.stdout + run.stderr)
        expected = '4 passed; 5 failed' if label == 'before' else '9 passed; 0 failed'
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
