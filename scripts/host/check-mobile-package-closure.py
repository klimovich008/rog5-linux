#!/usr/bin/env python3
"""Check recorded native-mobile dependency metadata; does not install packages."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

def need(condition, message):
    if not condition:
        raise ValueError(message)

def validate(root, database_dir=None):
    lock = json.loads((root / 'packaging/arch/mobile-package-closure.json').read_text())
    need(hashlib.sha256((root / lock['source_lock']['path']).read_bytes()).hexdigest() == lock['source_lock']['sha256'], 'invalid recorded metadata')
    packages = {p['name']: p for p in lock['packages']}
    need(len(packages) == len(lock['packages']) == lock['counts']['packages'], 'invalid recorded metadata')
    need(set(lock['roots']) <= packages.keys(), 'invalid recorded metadata')
    need({'mesa', 'vulkan-freedreno', 'wayland', 'libinput', 'seatd', 'fontconfig', 'foot', 'mousepad'} <= packages.keys(), 'invalid recorded metadata')
    need(not {'plasma-desktop', 'kwin', 'krdp'} & packages.keys(), 'invalid recorded metadata')
    requests = {('root', p) for p in lock['roots']}
    requests |= {(p['name'], d) for p in packages.values() for d in p['depends']}
    edges = {(e['from'], e['dependency']): e['provider'] for e in lock['dependency_edges']}
    need(requests == edges.keys(), 'missing or surplus dependency edge')
    for package in packages.values():
        need(package['architecture'] in ('aarch64', 'any'), 'invalid recorded metadata')
        need(re.fullmatch('[0-9a-f]{64}', package['sha256']), 'invalid recorded metadata')
        need(package['archive'].endswith(('.pkg.tar.xz', '.pkg.tar.zst')), 'invalid recorded metadata')
        need(package['signature_verified'] is False, 'invalid recorded metadata')
    for (_, dependency), provider in edges.items():
        p = packages[provider]
        name, *rest = re.split('([<>=]+)', dependency, maxsplit=1)
        provided = {re.split('[<>=]', v, maxsplit=1)[0]: v for v in p['provides']}
        need(name == provider or name in provided, dependency)
        if rest:
            operator, wanted = rest
            actual = p['version'] if name == provider else provided[name].split('=', 1)[1]
            comparison = int(subprocess.check_output(['vercmp', actual, wanted], text=True))
            need({'=': comparison == 0, '>=': comparison >= 0, '<=': comparison <= 0, '>': comparison > 0, '<': comparison < 0}[operator], dependency)
    if database_dir:
        for database in lock['repository_snapshots']:
            digest = hashlib.sha256()
            path = database_dir / (database['repository'] + '.db')
            need(path.stat().st_size == database['size'], 'invalid recorded metadata')
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            need(digest.hexdigest() == database['sha256'], 'invalid recorded metadata')
    need(lock['status'] == 'BLOCKED' and lock['blockers'], 'invalid recorded metadata')
    need(lock['denial_runtime_artifacts']['flutter_engine_archive'] is None, 'invalid recorded metadata')
    need(not any(lock['authority'].values()), 'invalid recorded metadata')
    print(f'PASS metadata graph: {len(packages)} packages, {len(edges)} dependency edges')
    print('PASS retained database hashes' if database_dir else 'NOT RUN retained database hashes')
    print('BLOCKED runtime closure: archive/signature verification, valid repository snapshot and engine/AOT remain missing')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-dir', type=Path)
    args = parser.parse_args()
    validate(Path(__file__).resolve().parents[2], args.database_dir)
if __name__ == '__main__':
    main()
