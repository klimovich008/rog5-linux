#!/usr/bin/env python3
"""Create an inert, deterministic display/GPU module archive from the active board.

No module loading, initramfs replacement, signing, admission or device access.
Symbol dependency closure is not hardware activation order or firmware readiness.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ROOTS = ('qcom_refgen_regulator', 'gpucc_sm8350', 'panel_asus_rog5_ams678', 'msm')
RELEASE = '7.1.4-rog5-production'
PREFIX = 'modules/lib/modules/' + RELEASE + '/'
MAX_MODULE = 64 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}\Z')
NAME = re.compile(r'[A-Za-z0-9_-]+\Z')


def need(value, reason):
    if not value: raise ValueError(reason)


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def checked_file(path, limit, digest=None):
    """Bounded no-final-symlink read, including mutation detection while reading."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit, 'input type/size')
        h = hashlib.sha256(); data = bytearray()
        while chunk := os.read(fd, min(65536, limit + 1 - len(data))):
            data.extend(chunk); h.update(chunk)
            need(len(data) <= limit, 'input grew')
        after = os.fstat(fd)
        def stamp(s): return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
        need(stamp(before) == stamp(after) == stamp(path.lstat()), 'input changed during read')
        need(len(data) == before.st_size, 'short input')
        if digest is not None:
            need(type(digest) is str and HEX.fullmatch(digest) and h.hexdigest() == digest, 'input digest mismatch: ' + path.name)
        return bytes(data)
    finally:
        os.close(fd)


def beneath(root, relative):
    need(type(relative) is str and str(PurePosixPath(relative)) == relative
         and not relative.startswith('/') and '..' not in PurePosixPath(relative).parts,
         'unsafe relative path')
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        need(not path.is_symlink(), 'input symlink')
    return path


def parse_json(raw):
    return json.loads(raw, object_pairs_hook=unique)


def inspect_module(path):
    # modinfo reads ELF metadata; it does not insert a module.
    result = {}
    for field in ('name', 'vermagic', 'depends', 'firmware', 'softdep', 'weakdep'):
        call = subprocess.run(['modinfo', '-F', field, str(path)], capture_output=True,
                              text=True, timeout=5)
        need(call.returncode == 0 and not call.stderr and len(call.stdout) < 16384, 'modinfo failed: ' + field)
        result[field] = call.stdout.strip()
    return result


def select(entries, builtin, dependencies, softdep, release=RELEASE):
    """Validate full metadata, then take only the explicit roots' symbol closure."""
    spec = importlib.util.spec_from_file_location('module_closure_checker', ROOT/'scripts/host/check-production-build-diagnostics.py')
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    need(not checker.module_closure(entries, builtin, dependencies, release), 'module dependency closure invalid')
    paths = {}; names = {}
    for row in entries:
        need(row['path'].startswith(PREFIX + 'kernel/') and row['path'].endswith('.ko'), 'module path outside production tree')
        relative = row['path'][len(PREFIX):]
        need(str(PurePosixPath(relative)) == relative and '..' not in PurePosixPath(relative).parts, 'unsafe module path')
        need(NAME.fullmatch(row['name']), 'invalid module name')
        paths[relative] = row; names[row['name'].replace('-', '_')] = relative
    need(all(name in names for name in ROOTS), 'required display/GPU root missing')
    graph = {line.split(':')[0]: line.split(':')[1].split() for line in dependencies.splitlines()}
    # depmod includes transitive edges. Select from declared ELF dependencies,
    # then require every index edge to belong to that transitive closure.
    direct = {path: [names[dep.replace('-', '_')] for dep in row['depends'].split(',')
                     if dep and dep.replace('-', '_') in names] for path, row in paths.items()}
    selected = []; seen = set()
    def visit(path):
        if path in seen: return
        seen.add(path)
        for dep in sorted(direct[path]): visit(dep)
        selected.append(path)
    for name in ROOTS: visit(names[name])
    def descendants(path):
        found = set(); pending = list(direct[path])
        while pending:
            dep = pending.pop()
            if dep not in found:
                found.add(dep); pending.extend(direct[dep])
        return found
    for path in selected:
        need(set(graph[path]) <= descendants(path), 'depmod edge outside declared transitive closure')
    need(len(selected) <= 64, 'display module closure exceeds reviewed bound')
    selected_names = {paths[path]['name'].replace('-', '_') for path in selected}
    for line in softdep.splitlines():
        fields = line.split()
        if not fields or fields[0].startswith('#'): continue
        need(len(fields) >= 3 and fields[0] == 'softdep', 'invalid softdep index')
        need(fields[1].replace('-', '_') not in selected_names, 'selected module softdep requires separate review')
    return [(paths[path], graph[path]) for path in selected]


def prepare(pointer_path):
    pointer_raw = checked_file(pointer_path, 2 * 1024 * 1024)
    board = parse_json(pointer_raw)['current_board_qualification']
    need(board['status'] == 'PASS: offline incremental software qualification'
         and board['candidate'] is None and board['release'] == RELEASE, 'active unsigned board qualification required')
    for name in ('production_series_sha256', 'config_sha256'):
        need(HEX.fullmatch(board[name]), 'invalid board binding')
    cohort = Path(board['module_artifact_root'])
    need(cohort.is_absolute() and cohort.resolve(strict=True) == cohort, 'unsafe cohort root')
    meta = board['module_metadata']
    metadata_path = beneath(cohort, 'module-provenance.json')
    need(str(metadata_path) == meta['path'], 'metadata outside current cohort')
    metadata = checked_file(metadata_path, 2 * 1024 * 1024, meta['sha256'])
    need(len(metadata) == meta['size'], 'module metadata size')
    entries = parse_json(metadata)
    proof = board['evidence']
    proof_raw = checked_file(beneath(ROOT, proof['path']), 2 * 1024 * 1024, proof['sha256'])
    need(len(proof_raw) == proof['size'], 'qualification size')
    evidence = parse_json(proof_raw)
    need(evidence['cohort']['status'] == 'PASS'
         and evidence['cohort']['module_metadata_sha256'] == meta['sha256'], 'cohort qualification mismatch')
    for pointer_key, evidence_key in (('source_commit', 'source_commit'), ('source_tree', 'source_tree'),
                                    ('linux_base', 'linux_commit'), ('release', 'release'),
                                    ('production_series_sha256', 'production_series_sha256'), ('config_sha256', 'config_sha256')):
        need(board[pointer_key] == evidence[evidence_key], 'board qualification binding mismatch: ' + pointer_key)
    indexes = {}
    for name in ('modules.dep', 'modules.builtin', 'modules.softdep'):
        indexes[name] = checked_file(beneath(cohort, PREFIX + name), 2 * 1024 * 1024,
                                     evidence['cohort']['indexes'][name]).decode()
    selected = select(entries, indexes['modules.builtin'], indexes['modules.dep'], indexes['modules.softdep'])
    return board, selected, cohort, hashlib.sha256(pointer_raw).hexdigest()


def assemble(pointer, output):
    need(not os.path.lexists(output), 'output already exists')
    need(output.parent.resolve(strict=True) == output.parent and not output.is_symlink(), 'unsafe output parent')
    board, selected, cohort, pointer_sha = prepare(pointer)
    manifest = dict(format='rog5-production-display-modules-v1', authority='none', release=RELEASE,
                    builder_sha256=hashlib.sha256(checked_file(Path(__file__).resolve(), 65536)).hexdigest(),
                    closure_checker_sha256=hashlib.sha256(checked_file(ROOT/'scripts/host/check-production-build-diagnostics.py', 65536)).hexdigest(),
                    board_source_commit=board['source_commit'], linux_commit=board['linux_base'],
                    production_series_sha256=board['production_series_sha256'], config_sha256=board['config_sha256'],
                    artifact_pointer_sha256=pointer_sha, module_metadata_sha256=board['module_metadata']['sha256'],
                    qualification_sha256=board['evidence']['sha256'], roots=list(ROOTS), modules=[],
                    order_scope='symbol dependencies only; hardware activation order NOT QUALIFIED',
                    firmware_status='NOT PACKAGED; modinfo does not enumerate every runtime firmware request',
                    activation='none; no helper, service, autoload, boot image or claim', physical='NOT RUN')
    temporary = None
    total_bytes = 0
    try:
        with tempfile.NamedTemporaryFile(prefix='.' + output.name + '.', dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                def add(name, data):
                    entry = tarfile.TarInfo(name); entry.size = len(data); entry.mode = 0o644
                    archive.addfile(entry, io.BytesIO(data))
                for row, deps in selected:
                    path = beneath(cohort, row['path'])
                    data = checked_file(path, MAX_MODULE, row['sha256'])
                    need(data[:6] == b'\x7fELF\x02\x01' and data[16:20] == b'\x01\x00\xb7\x00', 'module must be ARM64 relocatable ELF')
                    total_bytes += len(data)
                    need(total_bytes <= 128 * 1024 * 1024, 'display module payload exceeds bound')
                    actual = inspect_module(path)
                    firmware = [] if type(row['firmware']) is str and row['firmware'] == '' else row['firmware']
                    need(type(firmware) is list and all(type(x) is str for x in firmware), 'firmware metadata schema')
                    need(actual['name'] == row['name'] and actual['depends'] == row['depends']
                         and actual['vermagic'] == row['vermagic'] == board['panel_module']['vermagic']
                         and actual['firmware'].splitlines() == firmware, 'ELF metadata mismatch')
                    need(not actual['softdep'] and not actual['weakdep'], 'selected ELF soft/weak dependency requires review')
                    # Detect mutation between reading bytes and modinfo reopening.
                    need(checked_file(path, MAX_MODULE, row['sha256']) == data, 'module changed during inspection')
                    if row['name'] == 'panel_asus_rog5_ams678':
                        need(row['sha256'] == board['panel_module']['sha256'], 'qualified default-dark panel mismatch')
                    add(row['path'], data)
                    manifest['modules'].append(dict(row, firmware=firmware, bytes=len(data), dependencies=[PREFIX + p for p in deps]))
                add('manifest.json', (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode())
            stream.flush(); os.fsync(stream.fileno())
        # Link publishes the complete single-file archive without replacing a
        # concurrent writer or existing artifact. Temp and output share a disk.
        os.link(temporary, output, follow_symlinks=False)
        temporary.unlink(); temporary = None
        fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = assemble(ROOT/'manifests/current-artifact.json', args.output.absolute())
    print('PASS inert module archive:', len(result['modules']), 'modules; firmware/activation/physical NOT RUN')


if __name__ == '__main__': main()
