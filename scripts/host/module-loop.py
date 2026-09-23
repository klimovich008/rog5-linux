#!/usr/bin/env python3
"""Fast module loop for the running ROG5 production kernel: build, deliver, test.

  build    Compile one module directory of a dev source tree as an external
           (M=) module against the exact, read-only object tree of the running
           kernel. Kernel headers come from that pristine tree, so a module
           build cannot change the ABI the running vmlinux was built with.
           Edits outside the module directory under include/ or arch/, or to
           any header outside it, are refused: they need a full kernel build.
  deliver  Check that the phone runs that exact vmlinux (GNU build ID and
           release), stream the modules into RAM (/run/rog5-dev-modules),
           load or replace them, run an optional test command and collect the
           kernel log written since a marker. An oops, BUG, WARNING or lost
           SSH fails the run.

Nothing is written to phone storage and nothing is flashed. Every run keeps
its inputs, commands and outputs in a new evidence directory.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('production_ram_trial', HERE/'production-ram-trial.py')
TRIAL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TRIAL)

STATE = Path(os.environ.get('ROG5_MODULE_LOOP_STATE', Path.home()/'.local/state/rog5-module-loop'))
REMOTE_DIR = '/run/rog5-dev-modules'
PROBLEMS = re.compile(r'Internal error|Oops|BUG:|WARNING:|Call trace:|Kernel panic|Unable to handle kernel')
SHARED = ('include/', 'arch/')


def need(ok, why):
    if not ok:
        raise ValueError(why)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def new_dir(path, prefix):
    path = Path(path) if path else STATE/(stamp()+'-'+prefix)
    need(path.is_absolute(), 'output must be an absolute path')
    need(not path.exists(), 'output must be a new directory: '+str(path))
    path.mkdir(mode=0o700, parents=True)
    return path


def gnu_build_id(notes):
    """GNU build ID from an ELF note blob (/sys/kernel/notes or a .notes section)."""
    offset = 0
    while offset + 12 <= len(notes):
        namesz, descsz, kind = struct.unpack_from('<III', notes, offset)
        offset += 12
        name = notes[offset:offset+namesz]
        offset += (namesz + 3) & ~3
        desc = notes[offset:offset+descsz]
        offset += (descsz + 3) & ~3
        if kind == 3 and name.rstrip(b'\0') == b'GNU':
            return desc.hex()
    return None


def vmlinux_build_id(objects):
    readelf = shutil.which('llvm-readelf') or shutil.which('readelf')
    need(readelf, 'readelf is required')
    out = subprocess.run([readelf, '-n', str(objects/'vmlinux')], capture_output=True, text=True, check=True).stdout
    match = re.search(r'Build ID: ([0-9a-f]{40})', out)
    need(match, 'vmlinux has no GNU build ID')
    return match.group(1)


def outside_changes(source, directory):
    """Changed files of a git dev tree that a module-only build cannot carry."""
    if not (source/'.git').exists():
        return []
    status = subprocess.run(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'],
                            capture_output=True, text=True, check=True).stdout
    prefix = directory.rstrip('/')+'/'
    bad = []
    for line in status.splitlines():
        path = line[3:].split(' -> ')[-1]
        if path.startswith(prefix):
            continue
        if path.startswith(SHARED) or path.endswith('.h'):
            bad.append(path)
    return bad


def build(args):
    objects = Path(args.objects).resolve()
    source = Path(args.source).resolve()
    directory = args.dir.strip('/')
    need((objects/'Module.symvers').is_file() and (objects/'vmlinux').is_file(), 'objects is not a complete kernel build')
    need((source/directory/'Makefile').is_file(), 'no Makefile in '+str(source/directory))
    bad = outside_changes(source, directory)
    need(not bad or args.allow_outside, 'shared kernel files changed (need a full kernel build): '+', '.join(bad))
    release = (objects/'include/config/kernel.release').read_text().strip()
    out = new_dir(args.output, 'build-'+Path(directory).name)
    stage = out/'src'
    shutil.copytree(source/directory, stage, ignore=shutil.ignore_patterns('*.o', '*.ko', '*.mod*', '.*.cmd', 'modules.order'))
    env = {k: v for k, v in os.environ.items() if not k.startswith(('KBUILD', 'KCFLAGS', 'CC', 'MAKEFLAGS'))}
    env.update(LC_ALL='C')
    make = ['make', '-C', str(objects), 'M='+str(stage), 'ARCH=arm64', 'LLVM=1', '-j'+str(args.jobs)]
    if args.ccache:
        env.update(CCACHE_DIR=str(STATE/'ccache'), CCACHE_BASEDIR=str(out))
        make.append('CC='+args.ccache+' clang')
    began = time.monotonic()
    with (out/'make.log').open('wb') as log:
        rc = subprocess.run(make+['modules'], env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    seconds = round(time.monotonic()-began, 2)
    need(rc == 0, 'module build failed; see '+str(out/'make.log'))
    modules = []
    (out/'modules').mkdir()
    strip = shutil.which('llvm-strip')
    for ko in sorted(stage.rglob('*.ko')):
        info = lambda field: subprocess.run(['modinfo', '-F', field, str(ko)], capture_output=True, text=True, check=True).stdout.strip()
        name, vermagic = info('name'), info('vermagic')
        need(vermagic.split()[0] == release, name+' vermagic does not match '+release)
        target = out/'modules'/(name+'.ko')
        shutil.copyfile(ko, target)
        if strip:
            subprocess.run([strip, '--strip-debug', str(target)], check=True)
        modules.append(dict(name=name, file=str(target.relative_to(out)), sha256=digest(target.read_bytes()),
                            vermagic=vermagic, depends=[d for d in info('depends').split(',') if d]))
    need(modules, 'the build produced no modules')
    head = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(['git', '-C', str(source), 'diff', 'HEAD', '--', directory], capture_output=True).stdout
    result = dict(format='rog5-module-loop-build-v1', objects=str(objects), release=release,
                  build_id=vmlinux_build_id(objects), source=str(source), dir=directory,
                  source_head=head or None, source_diff_sha256=digest(diff), outside_changes=bad,
                  command=make+['modules'], seconds=seconds, modules=modules)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(build=str(out), seconds=seconds, modules=[m['name'] for m in modules])))
    return 0


def remote(address, command, timeout=60, data=None):
    result = TRIAL.ssh(address, command, timeout, data)
    return result.returncode, result.stdout.decode(errors='replace'), result.stderr.decode(errors='replace')


def running_identity(address):
    rc, out, err = remote(address, 'uname -r; od -An -v -tx1 /sys/kernel/notes | tr -d " \\n"', 20)
    need(rc == 0, 'SSH identity probe failed: '+err[-300:])
    release, _, notes = out.partition('\n')
    return release.strip(), gnu_build_id(bytes.fromhex(notes.strip()))


def deliver(args):
    build_dir = Path(args.build).resolve()
    built = json.loads((build_dir/'result.json').read_text())
    modules = [m for m in built['modules'] if not args.only or m['name'] in args.only]
    need(modules, 'no module selected')
    params = {}
    for item in args.param:
        name, _, value = item.partition(':')
        params.setdefault(name, []).append(value)
    need(TRIAL.usb_state() == 'target', 'no running target on the approved port')
    release, build_id = running_identity(args.address)
    need(release == built['release'], 'phone runs '+release+', modules are for '+built['release'])
    need(build_id == built['build_id'], 'phone vmlinux build ID '+str(build_id)+' is not '+built['build_id'])
    out = new_dir(args.evidence or build_dir/('deliver-'+stamp()), 'deliver')
    record = dict(format='rog5-module-loop-deliver-v1', build=str(build_dir), release=release, build_id=build_id,
                  mode=args.mode, started=TRIAL.now(), steps=[])

    def step(name, command, timeout=60, data=None):
        rc, stdout, stderr = remote(args.address, command, timeout, data)
        record['steps'].append(dict(name=name, command=command, returncode=rc, stdout=stdout[-4000:], stderr=stderr[-2000:]))
        return rc, stdout

    marker = 'rog5-module-loop begin '+secrets.token_hex(6)
    step('mark', 'mkdir -p '+REMOTE_DIR+' && echo '+shlex.quote(marker)+' > /dev/kmsg')
    ok = True
    for module in modules:
        path = REMOTE_DIR+'/'+module['name']+'.ko'
        data = (build_dir/module['file']).read_bytes()
        rc, stdout = step('push '+module['name'], 'cat > '+path+' && sha256sum '+path, data=data)
        ok = ok and rc == 0 and stdout.split()[:1] == [module['sha256']]
    loaded = []
    for module in modules if ok else []:
        name, path = module['name'], REMOTE_DIR+'/'+module['name']+'.ko'
        for dep in module['depends']:
            step('dependency '+dep, 'grep -q "^'+dep+' " /proc/modules || modprobe -d /run/rog5-modules '+dep)
        if args.mode == 'replace':
            rc, _ = step('remove '+name, 'if grep -q "^'+name+' " /proc/modules; then rmmod '+name+'; fi')
            if rc:
                ok = False
                break
        rc, _ = step('insmod '+name, 'insmod '+path+' '+' '.join(shlex.quote(p) for p in params.get(name, [])))
        if args.mode == 'oneshot':
            continue
        if rc:
            ok = False
            break
        loaded.append(name)
    if ok and args.test:
        rc, _ = step('test', args.test, timeout=args.test_timeout)
        ok = rc == 0
    rc, log = step('kernel log', 'dmesg | sed -n "/'+marker+'/,\\$p"')
    problems = [line for line in log.splitlines() if PROBLEMS.search(line)]
    alive, _ = step('health', 'uname -r', 20)
    record.update(ended=TRIAL.now(), loaded=loaded, kernel_problems=problems[:40], ssh_after=alive == 0,
                  usb_after=TRIAL.usb_state(), status='PASS' if ok and not problems and alive == 0 else 'FAIL')
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    (out/'kernel.log').write_text(log)
    print(json.dumps(dict(deliver=str(out), status=record['status'], loaded=loaded, kernel_problems=len(problems))))
    return 0 if record['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build', help='build one module directory against the running kernel objects')
    b.add_argument('--objects', default=os.environ.get('ROG5_KDEV_OBJECTS'), required='ROG5_KDEV_OBJECTS' not in os.environ)
    b.add_argument('--source', default=os.environ.get('ROG5_KDEV_SOURCE'), required='ROG5_KDEV_SOURCE' not in os.environ)
    b.add_argument('--dir', required=True, help='module directory relative to the source, e.g. drivers/gpu/drm/panel')
    b.add_argument('--output')
    b.add_argument('--jobs', type=int, default=min(6, os.cpu_count() or 1))
    b.add_argument('--ccache', help='ccache executable to wrap clang with')
    b.add_argument('--allow-outside', action='store_true', help='accept shared-file edits (the module may not match the running kernel)')
    d = sub.add_parser('deliver', help='identity-check the phone, load the built modules, test and collect the log')
    d.add_argument('--build', required=True)
    d.add_argument('--only', nargs='*', default=[])
    d.add_argument('--mode', choices=('load', 'replace', 'oneshot'), default='replace')
    d.add_argument('--param', action='append', default=[], help='MODULE:key=value (repeatable)')
    d.add_argument('--test', help='shell command run on the phone after loading')
    d.add_argument('--test-timeout', type=int, default=60)
    d.add_argument('--address', default='169.254.77.2', choices=sorted(TRIAL.PROFILES))
    d.add_argument('--evidence')
    args = parser.parse_args()
    return build(args) if args.action == 'build' else deliver(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
