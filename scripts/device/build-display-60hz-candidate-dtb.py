#!/usr/bin/env python3
"""Build an offline DTB/provenance bundle; never stage or sign a phone image.

OUTPUT is a directory containing candidate.dtb and provenance.json, published
with one atomic rename. --replace atomically exchanges an existing valid bundle.
ROG5_LINUX_SOURCE supplies matching GPIO/regulator headers and panel bindings.
Missing schema tooling or validation diagnostics refuse publication.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'rog5-display-60hz-offline-bundle-v1'
BASE_CONTRACT = '7a5cef0db4795d9d453a12e0f61b5b7634fc4d40'
HEADER_PINS = {
    'include/dt-bindings/gpio/gpio.h': '5423b3866877ead0920ec978b5b072f06087443033a72445b39faed8f288ddc1',
    'include/dt-bindings/regulator/qcom,rpmh-regulator.h': '9024ec736a8bca4cc31d414ea2978b237ac6c4ff0409988f8434147a29ecd622',
}



def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('unsafe or missing input: ' + str(path))
    return path


def sha(path):
    with regular(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bindings_identity(root):
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob('*.yaml')):
        digest.update((str(path.relative_to(root)) + '\0' + sha(path) + '\n').encode())
        count += 1
    if not count:
        raise ValueError('empty binding tree')
    return {'yaml_files': count, 'sha256': digest.hexdigest()}


def verify_source_contract(source, schema):
    for relative, expected in HEADER_PINS.items():
        if sha(source / relative) != expected:
            raise ValueError('exact base header mismatch: ' + relative)
    patch = ROOT / 'patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch'
    body = regular(patch).read_text().split(
        '+++ b/Documentation/devicetree/bindings/display/panel/asus,rog5-ams678.yaml\n', 1)[1].split('diff --git', 1)[0]
    expected = ('\n'.join(line[1:] for line in body.splitlines() if line.startswith('+')) + '\n').encode()
    if regular(schema).read_bytes() != expected:
        raise ValueError('panel binding differs from current patch')
    return patch


def tools_identity():
    result = {}
    for name in ('cpp', 'dtc', 'fdtoverlay', 'dt-doc-validate', 'dt-validate'):
        path = Path(shutil.which(name)).resolve()
        version = subprocess.run([str(path), '--version'], capture_output=True,
                                 text=True, timeout=10)
        result[name] = {'path': str(path), 'sha256': sha(path),
                        'version': (version.stdout + version.stderr).strip(),
                        'version_returncode': version.returncode}
    return result


def run(argv, *, strict=False):
    completed = subprocess.run([str(v) for v in argv], capture_output=True,
                               text=True, timeout=120)
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    if completed.returncode or (strict and completed.stderr.strip()):
        raise ValueError('validation failed: ' + str(argv[0]))
    return completed.stdout + completed.stderr


def existing_bundle(path):
    if path.is_symlink() or not path.is_dir():
        raise ValueError('replacement is not a bundle directory')
    if {p.name for p in path.iterdir()} != {'candidate.dtb', 'provenance.json'}:
        raise ValueError('replacement contains unowned files')
    record = json.loads(regular(path / 'provenance.json').read_text())
    if record.get('format') != FORMAT or record.get('dtb_sha256') != sha(path / 'candidate.dtb'):
        raise ValueError('replacement bundle identity mismatch')


def publish(stage, output, replace):
    existing_bundle(stage)
    # NOREPLACE closes the check/rename race; EXCHANGE keeps the old complete
    # bundle until commit. Both entries are on the same filesystem.
    present = output.exists() or output.is_symlink()
    if present:
        if not replace:
            raise ValueError('output exists; explicit --replace is required')
        existing_bundle(output)
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = libc.renameat2
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                         ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    flag = 2 if present else 1  # RENAME_EXCHANGE / RENAME_NOREPLACE
    if renameat2(-100, os.fsencode(stage), -100, os.fsencode(output), flag):
        raise OSError(ctypes.get_errno(), 'atomic bundle publication failed')
    fd = os.open(output.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    # Interruption after exchange may retain the old bundle in owned staging;
    # output still names the complete new pair.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('overlay', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    for command in ('cpp', 'dtc', 'fdtoverlay', 'dt-doc-validate', 'dt-validate'):
        if not shutil.which(command):
            raise ValueError('BLOCKED missing required command: ' + command)
    source = os.environ.get('ROG5_LINUX_SOURCE')
    if not source:
        raise ValueError('BLOCKED ROG5_LINUX_SOURCE is required for headers/bindings')
    source = Path(source).resolve()
    schema = source / 'Documentation/devicetree/bindings/display/panel/asus,rog5-ams678.yaml'
    patch = verify_source_contract(source, schema)
    bindings_root = source / 'Documentation/devicetree/bindings'
    bindings = bindings_identity(bindings_root)
    tool_pins = tools_identity()
    headers = [source / relative for relative in HEADER_PINS]
    inputs = [args.base, args.overlay, schema, patch, *headers,
              ROOT / 'scripts/device/verify-display-60hz-dtb-delta.py']
    pins = {str(p.resolve()): sha(p) for p in inputs}
    output = args.output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / ('.' + output.name + '.lock')
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if output.exists() or output.is_symlink():
            if not args.replace:
                raise ValueError('output exists; explicit --replace is required')
            existing_bundle(output)
        with tempfile.TemporaryDirectory(prefix='.rog5-display-60hz-', dir=output.parent) as tmp:
            work = Path(tmp)
            stage = work / 'bundle'
            stage.mkdir()
            preprocessed = work / 'display.dts'
            with preprocessed.open('w') as stream:
                subprocess.run(['cpp', '-nostdinc', '-undef', '-D__DTS__',
                                '-x', 'assembler-with-cpp', '-I', str(source / 'include'),
                                str(args.overlay)], stdout=stream, check=True, timeout=30)
            warnings = run(['dtc', '-@', '-I', 'dts', '-O', 'dtb',
                            '-o', work / 'display.dtbo', preprocessed])
            run(['fdtoverlay', '-i', args.base, '-o', stage / 'candidate.dtb', work / 'display.dtbo'])
            warnings += run(['dtc', '-I', 'dtb', '-O', 'dts', '-o', '/dev/null', stage / 'candidate.dtb'])
            run([inputs[-1], args.base, stage / 'candidate.dtb',
                 '--input-direction', 'output-disable'])
            run(['dt-doc-validate', schema], strict=True)
            run(['dt-validate', '-s', source / 'Documentation/devicetree/bindings',
                 '-l', 'asus,rog5-ams678', stage / 'candidate.dtb'], strict=True)
            run(['dt-validate', '-s', source / 'Documentation/devicetree/bindings',
                 '-l', 'qcom,sm8350-tlmm', stage / 'candidate.dtb'], strict=True)
            if (bindings != bindings_identity(bindings_root) or
                    tool_pins != tools_identity()):
                raise ValueError('binding tree or tools changed during validation')
            if pins != {str(p.resolve()): sha(p) for p in inputs}:
                raise ValueError('input changed during construction')
            record = {'format': FORMAT, 'authority': 'offline only', 'inputs': pins,
                      'dtb_sha256': sha(stage / 'candidate.dtb'),
                      'kernel_base_contract': BASE_CONTRACT,
                      'source_verification': 'selected exact-base headers and current panel binding; not full kernel checkout',
                      'binding_tree': bindings, 'tools': tool_pins,
                      'dtc_version': run(['dtc', '--version']).strip(),
                      'dtc_diagnostics': warnings, 'panel_binding_validation': 'PASS',
                      'tlmm_binding_validation': 'PASS',
                      'all_board_bindings_validation': 'NOT RUN (separate production composition gate)',
                      'physical_validation': 'NOT RUN',
                      'memory_zero_length_tuple': 'preserved from exact base; unresolved'}
            (stage / 'provenance.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            for item in stage.iterdir():
                with item.open('rb') as stream:
                    os.fsync(stream.fileno())
            directory = os.open(stage, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            publish(stage, output, args.replace)
        print('PASS atomic offline DTB/provenance bundle: ' + str(output))
        print('NOT RUN physical validation; zero-length base memory tuple remains unresolved')
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL ' + str(error), file=sys.stderr)
        raise SystemExit(1)
