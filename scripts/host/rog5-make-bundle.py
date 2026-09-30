#!/usr/bin/env python3
"""Build one signed production bundle (main or safe) from a clean snapshot of HEAD.

  rog5-make-bundle.py --role main --kernel k111 --dtb d9          # next default
  rog5-make-bundle.py --role safe --kernel k69 --dtb d3 \\
      --boot-modules-from 4980520d                               # a fallback
  rog5-make-bundle.py ... --plan                                 # resolve, build nothing

The name is <role>-k<kernel>-d<dtb>-<YYMMDD><letter> (the first free letter of
the day unless --name-letter). Steps, all offline (no phone, no install):
 1. the kernel build (rog5-kernel-*-build-rNNN for kNNN) must be PASS, its Image
    must match result.json, and a labelled build must report <base>-rog5-kNNN;
 2. the DTB comes from configs/production/dtbs.json (sha256 and features file);
 3. `git archive HEAD` is extracted to <state>/bundle-work-<name>/src (the
    working tree's uncommitted changes are not in the bundle) with artifacts/
    linked; every build step runs that snapshot's scripts;
 4. the module package modules-kNNN is reused while its recorded digest of
    the packager, selection and external module sources matches the snapshot,
    else packaged anew (a legacy modules-<base>-rNNN only for a pruned build);
 5. main: a fresh try-once descriptor <state>/trial-<name>/descriptor; safe: none;
 6. the ramdisk (build-persistent-root-standalone-initramfs.sh with the pinned
    inputs of configs/production/bundle-inputs.json) must carry exactly that
    descriptor (safe: no descriptor) and the current init (restoring-v2);
 7. package-production-ram-trial.py signs the bundle and builds the 128 MiB RAM
    wrapper in <state>/package-<name>; the signing key is only passed on;
 8. configs/production/bundles.json gets the bundle (status built) and the
    kernel if new, and docs/bundles.md is re-rendered. Commit those two files.
"""
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
INPUTS = REPO/'configs/production/bundle-inputs.json'
DESCRIPTOR_MEMBER = 'rog5-production-trial/trial-descriptor'
MIN_FREE = 3 << 30
FILES = ('Image', 'board.dtb', 'initramfs.cpio.gz', 'manifest', 'manifest.sig')
# Inherited variables the build steps read (ramdisk builder, ROG5_TRIAL_HELPER in
# the recovery ramdisk, Python paths); only the pinned values below reach them.
BUILD_VARIABLES = re.compile(r'(PRODUCTION_|EXPECTED_|ROG5_|UFS_CONTAINMENT$|PERSISTENT_ROOT_OVERLAY$|PYTHON)')
MODULE_SOURCES = 'make-bundle-sources.json'


def clean_env():
    return {key: value for key, value in os.environ.items() if not BUILD_VARIABLES.match(key)}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REG = load('rog5_bundle_registry', REPO/'scripts/host/rog5-bundle-registry.py')
need, sha256, expand = REG.need, REG.sha256, REG.expand


def newc_member(archive, wanted):
    """Bytes of one regular member of a gzip newc cpio archive, or None."""
    data = gzip.decompress(archive)
    offset = 0
    while offset + 110 <= len(data):
        need(data[offset:offset+6] in (b'070701', b'070702'), 'initramfs is not newc cpio')
        fields = [int(data[offset+6+8*i:offset+14+8*i], 16) for i in range(13)]
        mode, size, name_size = fields[1], fields[6], fields[11]
        name_end = offset + 110 + name_size
        name = data[offset+110:name_end-1].decode('utf-8', 'replace')
        start = (name_end + 3) & ~3
        if name == 'TRAILER!!!':
            return None
        if name.lstrip('./') == wanted:
            need(mode & 0o170000 == 0o100000, wanted+' is not a regular file')
            return data[start:start+size]
        offset = (start + size + 3) & ~3
    return None


def pinned(entry, state, key='sha256'):
    path = expand(entry['path'], state)
    return path, entry[key]


def kernel_build(kernel, root, copies=()):
    """(build dir, result.json, Image path, release) of a PASS kernel build kNNN.
    A pruned build (objects/ deleted) can still supply its Image from a bundle
    made from it (COPIES), matched by the Image sha256 in result.json."""
    number = REG.KERNEL.fullmatch(kernel)
    need(number is not None, 'kernel must be kNNN (k1 to k9999; k0 is an unlabelled scratch build)')
    found = [p for p in Path(root).glob('rog5-kernel-*-build-r'+number[1]) if p.is_dir()]
    need(len(found) == 1, f'{kernel}: expected one {root}/rog5-kernel-*-build-r{number[1]}, found {len(found)}')
    build = found[0]
    result = json.loads((build/'result.json').read_text())
    need(result.get('status') == 'PASS', f'{kernel}: {build.name} did not PASS ({result.get("status")})')
    need(all(result['stages'].get(s, {}).get('status') == 'PASS' for s in ('kernel-build', 'modules-install')),
         f'{kernel}: kernel or module stage did not pass')
    release = result['release']
    label = result.get('release_label')
    if label is not None:
        need(label == kernel, f'{kernel}: the build is labelled {label}')
        need(release.endswith('-rog5-'+kernel), f'{kernel}: release {release} lacks -rog5-{kernel}')
    expected = result['outputs']['objects/arch/arm64/boot/Image']
    image = build/'objects/arch/arm64/boot/Image'
    if not image.exists():
        image = next((copy for copy in copies if copy.is_file() and sha256(copy) == expected), None)
        need(image is not None, f'{kernel}: {build.name}/objects is gone and no registered bundle has its Image')
    need(sha256(image) == expected, f'{kernel}: Image differs from result.json')
    return build, result, image, release


def kernel_entry(kernel, build, result):
    series = [item['name'][:4] for item in result['ordered_series']['production']]
    return dict(build=build.name, release=result['release'], date=result['started'][:10],
                series=f'{len(series)} patches, {series[0]}-{series[-1]}' if series else 'none',
                image_sha256=result['outputs']['objects/arch/arm64/boot/Image'],
                source_commit=result['repository']['commit'][:12], source_dirty=result['repository']['dirty'],
                changes='')


def kernel_pin(registry, kernel, build, result):
    """The registry entry for KERNEL, which must name exactly this build's bytes."""
    entry = kernel_entry(kernel, build, result)
    known = registry.kernels.get(kernel)
    if known is not None:
        need((known['build'], known['release'], known['image_sha256'])
             == (entry['build'], entry['release'], entry['image_sha256']),
             f'{kernel} in bundles.json names other bytes than {build.name}')
    return entry


def taken(name, registry, state):
    return (any(b['name'] == name for b in registry.bundles)
            or any((state/(prefix+name)).exists() for prefix in ('package-', 'ramdisk-', 'trial-', 'bundle-work-')))


def choose_name(args, registry, state):
    day = args.date or datetime.date.today().strftime('%y%m%d')
    letters = [args.name_letter] if args.name_letter else 'abcdefghijklmnopqrstuvwxyz'
    for letter in letters:
        name = REG.bundle_name(args.role, args.kernel, args.dtb, day, letter)
        if not taken(name, registry, state):
            return name
    raise ValueError('no free bundle name: '+(name if args.name_letter else f'{args.role}-{args.kernel}-{args.dtb}-{day}[a-z]'))


class Steps:
    """Runs the build steps and keeps their output in <work>/<step>.log."""
    def __init__(self, work):
        self.work = work

    def run(self, step, argv, cwd, env=None):
        argv = [str(item) for item in argv]
        started = time.monotonic()
        print(f'  {step} ...', flush=True)
        with (self.work/(step+'.log')).open('wb') as log:
            log.write(('$ '+' '.join(argv)+'\n').encode())
            log.flush()
            result = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT)
        need(result.returncode == 0, f'{step} failed ({result.returncode}); see {self.work/(step+".log")}')
        print(f'  {step} done in {time.monotonic()-started:.0f} s', flush=True)


def snapshot(source_repo, work, boot_modules_from):
    """git archive HEAD of SOURCE_REPO into work/src; returns (src, commit, dirty)."""
    def git(*argv, **kwargs):
        return subprocess.run(['git', '-C', str(source_repo), *argv], check=True, capture_output=True, **kwargs)
    commit = git('rev-parse', 'HEAD').stdout.decode().strip()
    dirty = bool(git('status', '--porcelain', '--untracked-files=no').stdout.strip())
    src = work/'src'
    src.mkdir()
    archive = subprocess.Popen(['git', '-C', str(source_repo), 'archive', commit], stdout=subprocess.PIPE)
    subprocess.run(['tar', '-x', '-C', str(src)], stdin=archive.stdout, check=True)
    archive.stdout.close()
    need(archive.wait() == 0, 'git archive failed')
    artifacts = Path(source_repo)/'artifacts'
    if artifacts.is_dir():
        # Untracked pinned tools (android-boot-tools-v1, trial-state helper) the packager reads.
        (src/'artifacts').symlink_to(artifacts.resolve())
    boot_modules = None
    if boot_modules_from:
        listing = git('show', boot_modules_from+':configs/production/boot-modules.list').stdout
        (src/'configs/production/boot-modules.list').write_bytes(listing)
        boot_modules = dict(revision=git('rev-parse', boot_modules_from+'^{commit}').stdout.decode().strip()[:12],
                            sha256=hashlib.sha256(listing).hexdigest())
    return src, commit, dirty, boot_modules


def module_sources(src):
    """Digest of everything besides the kernel build that goes into a module
    package: the packager, the module selection and each external module's
    source tree (tools/...), as in the snapshot."""
    selection = src/'configs/kernel/rog5-production-modules.json'
    files = [src/'scripts/host/package-production-modules.py', selection]
    for item in json.loads(selection.read_text())['external_modules']:
        root = src/item['source']
        files += sorted(p for p in root.rglob('*') if p.is_file()) if root.is_dir() else [root]
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(src)).encode()+b'\0'+sha256(path).encode()+b'\n')
    return digest.hexdigest()


def usable_package(directory, build, image_sha256, release):
    result = json.loads((directory/'result.json').read_text())
    package = directory/'module-root-complete.tar.gz'
    need(result['status'] == 'PASS_UNSIGNED_MODULE_PACKAGE' and result['release'] == release
         and Path(result['kernel_build']).resolve() == build.resolve()
         and result['kernel_image_sha256'] == image_sha256
         and sha256(package) == result['package_sha256'],
         f'{directory} is not a module package of {build.name}')
    return package, result


def module_package(steps, src, state, kernel, build, image_sha256, release, fresh):
    """(package path, result, how) for this kernel build. A package this tool
    made is reused only when its recorded sources digest matches the snapshot.
    A legacy package (no digest) is reused only when the build's objects are
    gone and nothing else can be packaged (k69)."""
    base = re.fullmatch(r'rog5-kernel-(.+)-build-r[0-9]+', build.name)[1]
    sources = module_sources(src)
    if not fresh:
        for directory in sorted(state.glob(f'modules-{kernel}*')):
            if (re.fullmatch(re.escape('modules-'+kernel)+r'(-[0-9]{12})?', directory.name)
                    and (directory/MODULE_SOURCES).is_file()
                    and json.loads((directory/MODULE_SOURCES).read_text()).get('sources_sha256') == sources):
                return (*usable_package(directory, build, image_sha256, release), 'reused')
    legacy = state/f'modules-{base}-r{kernel[1:]}'
    if not (build/'objects').is_dir():
        need(legacy.is_dir(), f'{build.name}/objects is gone and there is no {legacy.name} to reuse')
        return (*usable_package(legacy, build, image_sha256, release), 'reused-unverified')
    output = state/('modules-'+kernel)
    if output.exists():
        output = state/f'modules-{kernel}-{datetime.datetime.now():%y%m%d%H%M%S}'
    steps.run('modules', [sys.executable, '-B', src/'scripts/host/package-production-modules.py',
                          '--build', build, '--output', output], cwd=src, env=clean_env())
    package, result = usable_package(output, build, image_sha256, release)
    (output/MODULE_SOURCES).write_text(json.dumps(dict(sources_sha256=sources), indent=2)+'\n')
    return package, result, 'new'


def write_descriptor(state, name):
    directory = state/('trial-'+name)
    directory.mkdir(mode=0o755)
    path = directory/'descriptor'
    text = (f'format=rog5-persistent-wifi-health-v1\ntrial_id={secrets.token_hex(32)}\n'
            f'primary_bundle={name}\nmode=try-once\n')
    with open(path, 'x') as stream:
        stream.write(text)
    return path


def ramdisk_env(inputs, state, release, package, descriptor):
    env = clean_env()
    env.update(inputs['ramdisk_env'])
    base_path, base_sha = pinned(inputs['ramdisk_base'], state)
    firmware, firmware_sha = pinned(inputs['extra_firmware'], state, 'sums_sha256')
    wifi, wifi_sha = pinned(inputs['wifi_kit'], state, 'sums_sha256')
    env.update(EXPECTED_RELEASE=release, EXPECTED_STANDALONE_BASE_SHA256=base_sha,
               PRODUCTION_MODULE_PACKAGE=str(package), PRODUCTION_MODULE_PACKAGE_SHA256=sha256(package),
               PRODUCTION_EXTRA_FIRMWARE=str(firmware), PRODUCTION_EXTRA_FIRMWARE_SHA256=firmware_sha,
               PRODUCTION_WIFI_KIT=str(wifi), PRODUCTION_WIFI_KIT_SHA256=wifi_sha)
    if descriptor is not None:
        env.update(PRODUCTION_TRIAL_DESCRIPTOR=str(descriptor), PRODUCTION_TRIAL_DESCRIPTOR_SHA256=sha256(descriptor))
    return env, base_path


def check_ramdisk(ramdisk, descriptor):
    data = ramdisk.read_bytes()
    carried = newc_member(data, DESCRIPTOR_MEMBER)
    if descriptor is None:
        need(carried is None, 'the safe ramdisk carries a trial descriptor')
    else:
        need(carried == descriptor.read_bytes(), 'the ramdisk does not carry the fresh descriptor')
    need(b'restoring-v2' in gzip.decompress(data), 'the ramdisk lacks the current init (restoring-v2)')


def plan(args):
    registry = REG.Registry(args.config, args.doc)
    registry.validate()
    inputs = json.loads(args.inputs.read_text())
    need(inputs.get('format') == 'rog5-bundle-inputs-v1', 'bundle-inputs format')
    state = args.state_dir or expand(inputs['state_dir'])
    need(state.is_dir(), f'state directory {state} missing')
    need(args.role == 'safe' or args.boot_modules_from is None,
         '--boot-modules-from is for a fallback with an older kernel (main bundles use the current list)')
    copies = [state/b['package']/'bundles'/b['name']/'Image' for b in registry.bundles
              if b['kernel'] == args.kernel and b.get('package')]
    build, result, image, release = kernel_build(args.kernel, args.kernel_root or expand(inputs['kernel_builds']), copies)
    kernel_pin(registry, args.kernel, build, result)
    dtb, dtb_entry = registry.verify_dtb(args.dtb)
    name = choose_name(args, registry, state)
    for key in ('ramdisk_base', 'recovery_base', 'asus_template', 'asus_kernel'):
        path, digest = pinned(inputs[key], state)
        need(path.is_file() and sha256(path) == digest, f'{key} {path} missing or changed')
    for key in ('extra_firmware', 'wifi_kit'):
        path, digest = pinned(inputs[key], state, 'sums_sha256')
        need(sha256(path/'SHA256SUMS') == digest, f'{key} {path} missing or changed')
    key = Path(args.private_key or os.environ.get('ROG5_SIGNING_KEY') or expand(inputs['signing_key']))
    need(key.is_absolute() and key.is_file() and not key.is_symlink(), f'signing key {key} missing')
    return dict(registry=registry, inputs=inputs, state=state, build=build, result=result, image=image,
                release=release, dtb=dtb, dtb_entry=dtb_entry, name=name, key=key)


def build_bundle(args, p):
    registry, inputs, state, name = p['registry'], p['inputs'], p['state'], p['name']
    work = state/('bundle-work-'+name)
    work.mkdir(mode=0o700)
    steps = Steps(work)
    print(f'{name}: {args.kernel} ({p["build"].name}, {p["release"]}) + {args.dtb} ({p["dtb_entry"]["path"]})', flush=True)
    src, commit, dirty, boot_modules = snapshot(args.source_repo, work, args.boot_modules_from)
    print(f'  source {commit[:12]}' + (' (uncommitted changes in the working tree are NOT included)' if dirty else ''))
    image_sha256 = sha256(p['image'])
    package, modules, how = module_package(steps, src, state, args.kernel, p['build'], image_sha256,
                                           p['release'], args.fresh_modules)
    print(f'  modules {package.parent.name} ({how})')
    selection = src/'configs/kernel/rog5-production-modules.json'
    selection_current = selection.is_file() and sha256(selection) == modules.get('selection_sha256')
    if how == 'reused-unverified':
        print('  note: a legacy module package of a pruned build: its external modules and selection'
              + ('' if selection_current else ' (which differs from HEAD)') + ' are not checked against HEAD')
    descriptor = write_descriptor(state, name) if args.role == 'main' else None
    ramdisk_dir = state/('ramdisk-'+name)
    ramdisk_dir.mkdir()
    ramdisk = ramdisk_dir/'target.cpio.gz'
    env, base = ramdisk_env(inputs, state, p['release'], package, descriptor)
    steps.run('ramdisk', ['sh', src/'scripts/device/build-persistent-root-standalone-initramfs.sh', base, ramdisk],
              cwd=src, env=env)
    check_ramdisk(ramdisk, descriptor)
    output = state/('package-'+name)
    argv = [sys.executable, '-B', src/'scripts/host/package-production-ram-trial.py']
    for option, path in (('image', p['image']), ('dtb', p['dtb']), ('initramfs', ramdisk)):
        argv += ['--'+option, path, f'--{option}-sha256', sha256(path)]
    for option in ('recovery_base', 'asus_template', 'asus_kernel'):
        path, digest = pinned(inputs[option], state)
        argv += ['--'+option.replace('_', '-'), path, '--'+option.replace('_', '-')+'-sha256', digest]
    argv += ['--private-key', p['key'], '--release', p['release'], '--bundle', name, '--output', output]
    steps.run('package', argv, cwd=src, env=clean_env())
    packaged = json.loads((output/'result.json').read_text())
    need(packaged['status'] == 'PASS_PACKAGED_UNBOOTED' and packaged['bundle'] == name
         and packaged['release'] == p['release'], 'package result')
    need(packaged['inputs']['image']['sha256'] == image_sha256
         and packaged['inputs']['dtb']['sha256'] == p['dtb_entry']['sha256']
         and packaged['inputs']['initramfs']['sha256'] == sha256(ramdisk), 'package inputs differ')
    bundle_dir = output/'bundles'/name
    need(sorted(q.name for q in bundle_dir.iterdir()) == sorted(FILES), 'bundle inventory')

    record = dict(format='rog5-make-bundle-v1', name=name, role=args.role, kernel=args.kernel, dtb=args.dtb,
                  release=p['release'], source_commit=commit, source_tree_dirty=dirty,
                  kernel_build=str(p['build']), image_sha256=image_sha256,
                  dtb_path=str(p['dtb']), dtb_sha256=p['dtb_entry']['sha256'],
                  module_package=str(package), module_package_sha256=sha256(package),
                  module_package_source=how, module_selection_current=selection_current,
                  boot_modules_from=boot_modules,
                  descriptor=str(descriptor) if descriptor else None,
                  ramdisk=str(ramdisk), ramdisk_sha256=sha256(ramdisk),
                  package=str(output), manifest_sha256=packaged['manifest_sha256'],
                  wrapper_sha256=packaged['wrapper']['sha256'], created=datetime.datetime.now().isoformat(timespec='seconds'))
    (output/'make-bundle.json').write_text(json.dumps(record, indent=2)+'\n')
    notes = []
    if how == 'reused-unverified':
        notes.append(f'legacy module package {package.parent.name}')
    if boot_modules:
        notes.append(f'boot-modules.list from {boot_modules["revision"]}')
    if dirty:
        notes.append('built from HEAD while the working tree had uncommitted changes')
    with REG.locked(args.config, args.doc) as current:
        # Reloaded under the lock: status changes made during the build stay.
        need(all(b['name'] != name for b in current.bundles), name+' was registered meanwhile')
        current.kernels.setdefault(args.kernel, kernel_pin(current, args.kernel, p['build'], p['result']))
        current.bundles.append(dict(
            name=name, role=args.role, kernel=args.kernel, dtb=args.dtb, date=datetime.date.today().isoformat(),
            release=p['release'], manifest_sha256=packaged['manifest_sha256'], package=output.name,
            source_commit=commit[:12], changes=args.changes or '', status='built', healthy='unknown',
            installed=None, notes='; '.join(notes) or None))
    shutil.rmtree(src)
    print(f'PASS {name}')
    print(f'  package   {output}')
    print(f'  wrapper   {output}/boot-ram-128m.img {packaged["wrapper"]["sha256"]}')
    if descriptor:
        print(f'  descriptor {descriptor}')
    trust = expand(inputs['trust_key']['path'], state)
    print('Next: RAM-trial the wrapper (production-ram-trial.py to-fastboot, then boot --wrapper ... '
          '--wrapper-sha256 ... --evidence <new dir> --stage-receiver), then install:')
    if args.role == 'main':
        print(f'  python3 scripts/host/install-default-kernel.py --bundle-dir {bundle_dir} --descriptor {descriptor} '
              f'--trust-key {trust} --evidence {state}/install-{name}-preflight --address 10.77.0.2')
    else:
        print(f'  a fallback is installed with a new main bundle: install-default-kernel.py ... '
              f'--fallback-bundle-dir {bundle_dir}')
    print(f'Record the outcome: scripts/host/rog5-bundle-registry.py set {name} --status ... --healthy ...; '
          'commit configs/production/bundles.json and docs/bundles.md.')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('--role', choices=REG.ROLES, required=True)
    parser.add_argument('--kernel', required=True, help='kernel build kNNN')
    parser.add_argument('--dtb', required=True, help='DTB id dN from configs/production/dtbs.json')
    parser.add_argument('--name-letter', help='a-z (default: the first free letter of the day)')
    parser.add_argument('--date', help='YYMMDD (default: today)')
    parser.add_argument('--changes', help='key changes for the registry')
    parser.add_argument('--boot-modules-from', metavar='REV',
                        help='safe only: take configs/production/boot-modules.list from REV (older kernels lack newer modules)')
    parser.add_argument('--fresh-modules', action='store_true', help='package the modules again from the snapshot')
    parser.add_argument('--private-key', help='signing key (default: $ROG5_SIGNING_KEY or bundle-inputs.json)')
    parser.add_argument('--plan', action='store_true', help='resolve and check the inputs, print the name, build nothing')
    parser.add_argument('--state-dir', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--kernel-root', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--source-repo', type=Path, default=REPO, help=argparse.SUPPRESS)
    parser.add_argument('--inputs', type=Path, default=INPUTS, help=argparse.SUPPRESS)
    parser.add_argument('--config', type=Path, default=REG.CONFIG, help=argparse.SUPPRESS)
    parser.add_argument('--doc', type=Path, default=REG.DOC, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.date is not None:
        need(re.fullmatch(r'[0-9]{6}', args.date) is not None, '--date must be YYMMDD')
    p = plan(args)
    if args.plan:
        print(json.dumps(dict(name=p['name'], role=args.role, kernel=args.kernel, build=str(p['build']),
                              image=str(p['image']), release=p['release'], dtb=args.dtb, dtb_path=str(p['dtb']),
                              state=str(p['state'])), indent=2))
        return 0
    need(shutil.disk_usage(p['state']).free >= MIN_FREE, 'keep a 3 GiB free-space reserve')
    build_bundle(args, p)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
