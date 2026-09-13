#!/usr/bin/env python3
"""Compile actual caret encoders and generated FlatBuffers readers for ARM64.

Uses an explicit matching flatbuffers rlib/dependency directory and ARM64
runner. Only WireState storage is an adapter; encoding, validation, sequence,
schema and old/new readers are production source. No compositor/VM/phone proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time


def block(text, marker):
    start = text.index(marker)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--source-before', type=Path, required=True)
    p.add_argument('--flatbuffers-rlib', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    rel = 'compositor/src/bin/deniald/'
    inputs = {}

    def read(root, name):
        path = root / name
        data = path.read_text()
        inputs[str(path)] = hashlib.sha256(data.encode()).hexdigest()
        return data

    encoder = read(args.source, rel + 'wire/encode.rs')
    wire = read(args.source, rel + 'wire.rs')
    text_input = read(args.source, rel + 'wayland_frontend/text_input.rs')
    old_encoder = read(args.source_before, rel + 'wire/encode.rs')
    for root, name in ((args.source, 'generated.rs'), (args.source_before, 'old_generated.rs')):
        (out / name).write_text(read(root, 'protocol/generated/rust/denial_generated.rs'))
    common = '\n'.join(line for line in wire.splitlines()
                       if line.startswith(('const PROTOCOL_VERSION:', 'const MAX_MESSAGE_BYTES:')))
    common += '\n#[derive(Debug)]\n' + block(wire, 'pub enum WireError')
    common += '\n' + block(wire, 'fn validate_finished_message')
    caret = block(text_input, 'pub(crate) struct TextInputCaret')
    unit = '''#![allow(dead_code,unused_imports,non_camel_case_types,non_snake_case,
        non_upper_case_globals,mismatched_lifetime_syntaxes,unsafe_op_in_unsafe_fn)]
use flatbuffers::FlatBufferBuilder;
mod generated { include!("generated.rs"); }
use generated::denial::wire as fb;
mod old_generated { include!("old_generated.rs"); }
'''
    unit += 'mod wayland_frontend { #[derive(Clone,Copy,Debug)]\n' + caret + '\n}\n'
    unit += common + '\n' + block(encoder, '\nfn encode_text_input_state')
    unit += '\nstruct WireState { outbound_builder: FlatBufferBuilder<\'static>, next_sequence:u64 }\nimpl WireState {\n'
    unit += block(wire, 'fn take_sequence') + '\n' + block(encoder, 'pub fn encode_text_input_state') + '\n}\n'
    unit += '\nmod old { use super::{FlatBufferBuilder,WireError,PROTOCOL_VERSION,validate_finished_message}; use super::old_generated::denial::wire as fb;\n'
    unit += block(old_encoder, '\nfn encode_text_input_state').replace('\nfn ', '\npub(super) fn ', 1) + '\n}\n'
    unit += encoder[encoder.index('#[cfg(test)]\nmod caret_wire_tests'):]
    unit += r'''
#[test] fn old_reader_accepts_new_optional_fields() {
    let mut b=FlatBufferBuilder::new();
    encode_text_input_state(&mut b,3,true,true,false,4,5,6,Some(caret())).unwrap();
    let e=old_generated::denial::wire::root_as_envelope(b.finished_data()).unwrap();
    let s=e.payload_as_text_input_state().unwrap();
    assert!(s.active()); assert!(s.input_panel_visible()); assert_eq!(s.content_purpose(),5);
}
#[test] fn new_reader_accepts_old_message_without_caret() {
    let mut b=FlatBufferBuilder::new(); old::encode_text_input_state(&mut b,3,true,true,false,4,5).unwrap();
    let e=fb::root_as_envelope(b.finished_data()).unwrap(); let s=e.payload_as_text_input_state().unwrap();
    assert_eq!(s.activation_serial(),0); assert!(s.caret().is_none()); assert!(s.active());
}
fn caret()->wayland_frontend::TextInputCaret { wayland_frontend::TextInputCaret {window_id:11,surface_id:12,x:2,y:90,width:0,height:20} }
fn state()->WireState { WireState {outbound_builder:FlatBufferBuilder::new(),next_sequence:1} }
#[test] fn public_encoder_refuses_inactive_and_legacy_carets() {
    let mut s=state();
    for (active,visible,legacy) in [(false,false,false),(true,true,true),(false,true,false)] {
        assert!(matches!(s.encode_text_input_state(active,visible,legacy,0,0,1,Some(caret())),Err(WireError::Payload)));
    }
    assert_eq!(s.next_sequence,1);
}
#[test] fn public_encoder_refuses_negative_dimensions() {
    let mut s=state(); let mut c=caret();c.width=-1;
    assert!(s.encode_text_input_state(true,true,false,0,0,1,Some(c)).is_err());
    c.width=0;c.height=-1;assert!(s.encode_text_input_state(true,true,false,0,0,1,Some(c)).is_err());
}
#[test] fn public_encoder_resets_optional_geometry_between_updates() {
    let mut s=state();
    let b=s.encode_text_input_state(true,true,false,0,0,1,Some(caret())).unwrap();
    assert!(fb::root_as_envelope(b).unwrap().payload_as_text_input_state().unwrap().caret().is_some());
    let b=s.encode_text_input_state(false,false,false,0,0,2,None).unwrap();
    let e=fb::root_as_envelope(b).unwrap();assert_eq!(e.sequence(),2);
    assert!(e.payload_as_text_input_state().unwrap().caret().is_none());
}
'''
    path = out / 'wire-tests.rs'
    path.write_text(unit)
    rustc = os.environ.get('RUSTC', 'rustc')
    runner = shlex.split(os.environ['ROG5_ARM64_RUNNER'])
    binary = out / 'wire-tests'
    commands = [[rustc, '--edition=2024', '--target=aarch64-unknown-linux-gnu',
                 '-C', 'linker=aarch64-linux-gnu-gcc', '-C', 'lto=thin',
                 '-C', 'codegen-units=1', '--test', str(path),
                 '--extern', 'flatbuffers=' + str(args.flatbuffers_rlib),
                 '-L', 'dependency=' + str(args.flatbuffers_rlib.parent), '-o', str(binary)],
                [*runner, str(binary), '--test-threads=1']]
    result = {'scope': __doc__, 'inputs': inputs, 'unit_sha256': hashlib.sha256(unit.encode()).hexdigest(),
              'status': 'FAIL', 'physical': 'NOT RUN', 'runs': []}
    with args.flatbuffers_rlib.open('rb') as f:
        result['flatbuffers_rlib_sha256'] = hashlib.file_digest(f, 'sha256').hexdigest()
    for command in commands:
        start = time.monotonic()
        run = subprocess.run(command, capture_output=True, text=True, timeout=45,
                             env=dict(os.environ, TMPDIR=str(out)))
        (out / f'run-{len(result["runs"])}.log').write_text(run.stdout + run.stderr)
        result['runs'].append({'command': command, 'seconds': time.monotonic()-start, 'exit_status': run.returncode})
        if run.returncode:
            break
    else:
        if '7 passed; 0 failed' in run.stdout:
            result['status'] = 'PASS'
    (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
