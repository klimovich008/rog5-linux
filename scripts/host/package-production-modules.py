#!/usr/bin/env python3
"""Package the production ramdisk module tree from one completed kernel build.

Offline only. Takes the modules installed by build-rog5-production-kernel.py,
builds the ROG5 external modules (tools/) against the same object tree, lays
out lib/modules/<release> with the board's modules.order, runs depmod against
the exact System.map and writes the deterministic module-root-complete.tar.gz
that build-persistent-root-standalone-initramfs.sh consumes as
PRODUCTION_MODULE_PACKAGE: regular files only, sorted names, mode 0644,
uid/gid/mtime 0, gzip level 1 with mtime 0. Every member is read back and
checked after packing.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import time

REPO = Path(__file__).resolve().parents[2]
SELECTION = REPO/'configs/kernel/rog5-production-modules.json'


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def modinfo(path, field):
    return subprocess.run(['modinfo', '-F', field, str(path)], capture_output=True, text=True, check=True).stdout.strip()


def build_external(objects, source, stage, jobs, env, extra_symbols):
    shutil.copytree(source, stage, ignore=shutil.ignore_patterns('*.o', '*.ko', '*.mod*', '.*.cmd', 'modules.order', '__pycache__'))
    # Externals may use symbols exported by externals built before them (wifi-activate uses s12).
    make = ['make', '-C', str(objects), 'M='+str(stage), 'ARCH=arm64', 'LLVM=1', '-j'+str(jobs)]
    if extra_symbols:
        make.append('KBUILD_EXTRA_SYMBOLS='+' '.join(str(p) for p in extra_symbols))
    result = subprocess.run(make+['modules'],
                            env=env, capture_output=True, text=True)
    (stage.parent/(stage.name+'.log')).write_text(result.stdout+result.stderr)
    need(result.returncode == 0, 'external module build failed: '+str(source))
    built = sorted(stage.glob('*.ko'))
    need(len(built) == 1, 'expected one module from '+str(source))
    subprocess.run(['llvm-strip', '--strip-debug', str(built[0])], check=True)
    return built[0]


def pack(tree, package):
    entries = {str(p.relative_to(tree)): sha(p) for p in sorted(tree.rglob('*')) if p.is_file()}
    total = 0
    with package.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0, compresslevel=1) as compressed, \
            tarfile.open(fileobj=compressed, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
        for name in sorted(entries):
            path = tree/name
            st = path.lstat()
            need(stat.S_ISREG(st.st_mode) and 0 < st.st_size <= 64*1024**2, 'input type/size: '+name)
            total += st.st_size
            info = tarfile.TarInfo(name)
            info.size, info.mode = st.st_size, 0o644
            info.uid = info.gid = info.mtime = 0
            with path.open('rb') as source:
                archive.addfile(info, source)
    seen = set()
    with tarfile.open(package, mode='r|gz') as archive:
        for item in archive:
            need(item.name in entries and item.name not in seen and item.isfile() and item.mode == 0o644
                 and item.uid == item.gid == item.mtime == 0, 'package member identity: '+item.name)
            seen.add(item.name)
            with archive.extractfile(item) as source:
                need(hashlib.sha256(source.read()).hexdigest() == entries[item.name], 'round trip: '+item.name)
    need(seen == set(entries), 'package inventory changed')
    return entries, total


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--build', type=Path, required=True, help='completed build-rog5-production-kernel.py output')
    parser.add_argument('--selection', type=Path, default=SELECTION)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    started = time.monotonic()
    build = args.build.resolve()
    built = json.loads((build/'result.json').read_text())
    # Only the compile and module-install stages feed this package; build-r2 (7.1.4)
    # recorded FAIL at its own later depmod stage with an old release derivation.
    stages = built['stages']
    need(all(stages.get(n, {}).get('status') == 'PASS' for n in ('kernel-build', 'modules-install')),
         'kernel build or module install did not pass')
    objects = build/'objects'
    release = (objects/'include/config/kernel.release').read_text().strip()
    installed = build/'modules/lib/modules'/release
    need((installed/'modules.builtin').is_file(), 'installed modules missing')
    selection = json.loads(args.selection.read_text())
    out = args.output.resolve()
    need(not out.exists(), 'output must be new')
    out.mkdir(parents=True, mode=0o700)
    tree = out/'tree'
    root = tree/'lib/modules'/release
    (root/'kernel').mkdir(parents=True)
    # A base may build a selected module in (7.2.7 defconfig: crypto aes, cmac, sha256).
    builtin_names = set((installed/'modules.builtin').read_text().splitlines())
    built_in = [m for m in selection['board_modules'] if not (installed/'kernel'/m).is_file() and 'kernel/'+m in builtin_names]
    missing = [m for m in selection['board_modules'] if not (installed/'kernel'/m).is_file() and m not in built_in]
    need(not missing, 'selected modules missing from this build: '+', '.join(missing))
    for canonical in selection['board_modules']:
        if canonical in built_in:
            continue
        dst = root/'kernel'/canonical
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(installed/'kernel'/canonical, dst)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('KBUILD', 'KCFLAGS', 'CC', 'MAKEFLAGS'))}
    env.update(LC_ALL='C', KBUILD_BUILD_USER='rog5-linux', KBUILD_BUILD_HOST='rog5-builder', KBUILD_BUILD_VERSION='1')
    externals, symvers = [], []
    for item in selection['external_modules']:
        ko = build_external(objects, REPO/item['source'], out/'external'/item['name'], args.jobs, env, symvers)
        symvers.append(out/'external'/item['name']/'Module.symvers')
        need(modinfo(ko, 'name') == item['name'].replace('-', '_'), 'external module name: '+item['name'])
        shutil.copyfile(ko, root/'kernel'/(item['name']+'.ko'))
        externals.append(item['name']+'.ko')
    for name in ('modules.builtin', 'modules.builtin.modinfo'):
        shutil.copyfile(installed/name, root/name)
    builtin = (root/'modules.builtin').read_text().splitlines()
    need(all(b in builtin for b in selection['required_builtin']), 'required built-in modules missing')
    board_order = [line[:-2]+'.ko' for line in (objects/'modules.order').read_text().splitlines()]
    selected = set(selection['board_modules'])-set(built_in)
    order = [c for c in board_order if c in selected]
    need(sorted(order) == sorted(selected), 'modules.order lacks selected modules')
    (root/'modules.order').write_text(''.join('kernel/'+c+'\n' for c in order+sorted(externals)))
    depmod = subprocess.run(['depmod', '-a', '-e', '-F', str(objects/'System.map'), '-b', str(tree), release],
                            capture_output=True, text=True, timeout=60)
    need(depmod.returncode == 0 and not depmod.stderr.strip(), 'depmod: '+depmod.stderr[-2000:])
    for ko in root.rglob('*.ko'):
        need(modinfo(ko, 'vermagic').split()[0] == release, 'vermagic: '+str(ko))
    package = out/'module-root-complete.tar.gz'
    entries, total = pack(tree, package)
    result = dict(status='PASS_UNSIGNED_MODULE_PACKAGE', release=release, kernel_build=str(build), kernel_build_status=built['status'],
                  kernel_image_sha256=sha(objects/'arch/arm64/boot/Image'),
                  selection_sha256=sha(args.selection), package_sha256=sha(package), package_bytes=package.stat().st_size,
                  files=len(entries), modules=sum(n.endswith('.ko') for n in entries), uncompressed_bytes=total,
                  external_modules=externals, selected_built_in=built_in, files_sha256=entries, duration_seconds=round(time.monotonic()-started, 2),
                  physical='NOT RUN', signed=False)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'release', 'package_sha256', 'files', 'modules', 'duration_seconds')}))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
