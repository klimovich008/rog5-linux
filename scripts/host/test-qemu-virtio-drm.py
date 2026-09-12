#!/usr/bin/env python3
"""Bounded, offline generic ARM64 DRM guest. Does not qualify phone hardware."""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import time
import uuid


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def missing_runtime_inputs(runtime, shell):
    commands = ['bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout', 'modetest']
    commands += ['seatd', 'sleep', 'Xwayland', 'dbus-daemon'] if shell else []
    return ['usr/bin/' + name for name in commands
            if not (runtime/'usr/bin'/name).is_file()]


def session_result(log):
    """Interpret actual Denial terminal counters; exit 0 is insufficient."""
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log)
    summaries = [line for line in text.splitlines()
                 if 'independently clocked Flutter KMS session complete' in line]
    result = {'status': 'FAIL', 'scope': 'Denial terminal counters; not visual or phone proof'}
    if len(summaries) != 1:
        return dict(result, reason='missing or duplicate terminal session counters')
    counts = {}
    for name in ('raster_frames', 'output_page_flips'):
        values = re.findall(r'\b' + name + r'=(\d+)\b', summaries[0])
        if len(values) != 1:
            return dict(result, reason='missing or duplicate frame count')
        counts[name] = int(values[0])
    errors = [message for message in (
        'required Flutter native fence export failed',
        'Could not create the embedder backing store',
        'Unhandled Exception', 'deniald: fatal error:',
        'could not bind Flutter context for output-target cleanup',
    ) if message in text]
    result.update(counts, render_errors=errors)
    if all(counts.values()) and not errors:
        result['status'] = 'PASS'
    else:
        result['reason'] = 'zero frames/page flips or observed rendering errors'
    return result


def render_node_identity(path):
    if path.parent != Path('/dev/dri') or not re.fullmatch(r'renderD\d+', path.name):
        raise ValueError('VirGL requires an explicit /dev/dri/renderD* node')
    info = path.lstat()
    if (not stat.S_ISCHR(info.st_mode) or os.major(info.st_rdev) != 226
            or not 128 <= os.minor(info.st_rdev) <= 255):
        raise ValueError('VirGL input is not a DRM render node')
    return {'path': str(path), 'major': os.major(info.st_rdev),
            'minor': os.minor(info.st_rdev), 'scope': 'host rendering only; no phone device'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--kernel', required=True, type=Path)
    parser.add_argument('--deniald', required=True, type=Path)
    parser.add_argument('--flutter-bundle', type=Path)
    parser.add_argument('--render-node', type=Path,
                        help='explicit host DRM render node for virtual VirGL; default uses software')
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--deadline', type=int, default=120)
    args = parser.parse_args()
    render_node = render_node_identity(args.render_node) if args.render_node else None
    if not 30 <= args.deadline <= 300:
        parser.error('deadline must be between 30 and 300 seconds')
    if len(args.image) != 64 or any(c not in '0123456789abcdef' for c in args.image):
        parser.error('image must be a retained immutable container ID')
    for tool in ('clang', 'cpio', 'gzip', 'podman'):
        if not shutil.which(tool):
            parser.error(f'BLOCKED missing {tool}')
    runtime = args.runtime.resolve(strict=True)
    kernel = args.kernel.resolve(strict=True)
    deniald = args.deniald.resolve(strict=True)
    if not (runtime/'usr/bin/bash').is_file() or runtime == Path('/'):
        parser.error('expected an explicitly materialized guest runtime')
    if not kernel.is_file() or not deniald.is_file():
        parser.error('kernel and deniald must be regular files')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[2]
    missing = missing_runtime_inputs(runtime, bool(args.flutter_bundle))
    if missing:
        report = {'status': 'BLOCKED', 'scope': 'offline guest prerequisites',
                  'missing_runtime_inputs': missing, 'vm_started': False,
                  'phone_hardware': 'NOT RUN', 'runtime': str(runtime)}
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
        return 2
    stage = output/'initramfs'
    for directory in ('dev', 'sysroot', 'stage/payload'):
        (stage/directory).mkdir(parents=True, exist_ok=True)
    payload = output/'payload'
    payload.mkdir()
    shutil.copy2(deniald, payload/'deniald')
    if args.flutter_bundle:
        bundle = args.flutter_bundle.resolve(strict=True)
        for required in ('lib/libflutter_engine.so', 'lib/libapp.so', 'data/icudtl.dat'):
            if not (bundle/required).is_file():
                parser.error(f'missing Flutter bundle input: {required}')
        shutil.copytree(bundle, payload/'flutter')
    shutil.copy2(repo/'tools/qemu-virtio-drm/guest.sh', stage/'stage/guest.sh')
    (stage/'stage/graphics-mode').write_text('virgl\n' if render_node else 'software\n')
    compile_command = ['clang', '--target=aarch64-none-elf', '-fuse-ld=lld',
                       '-nostdlib', '-static', '-fno-pic', '-fno-stack-protector',
                       '-Werror', '-Wall', '-Wextra',
                       '-Wl,--build-id=none,--entry=_start',
                       str(repo/'tools/qemu-virtio-drm/init.c'), '-o', str(stage/'init')]
    start = time.monotonic()
    report = {'scope': 'generic ARM64 virtual DRM; phone hardware NOT RUN',
              'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'kernel_sha256': digest(kernel), 'deniald_sha256': digest(deniald),
              'container': args.image, 'runtime': str(runtime),
              'runtime_inventory_verified_by_this_runner': False,
              'flutter_bundle': str(args.flutter_bundle) if args.flutter_bundle else None,
              'graphics_mode': 'virgl' if render_node else 'software',
              'host_render_node': render_node,
              'harness_sha256': digest(Path(__file__)),
              'init_source_sha256': digest(repo/'tools/qemu-virtio-drm/init.c'),
              'compile_command': compile_command, 'status': 'FAIL'}
    name = 'rog5-virtual-drm-' + uuid.uuid4().hex[:12]
    launched = False
    try:
        subprocess.run(compile_command, check=True, timeout=30,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        members = sorted(str(p.relative_to(stage)) for p in stage.rglob('*'))
        archive = subprocess.run(['cpio', '--null', '-o', '--quiet', '--format=newc',
                                  '--owner=0:0'], input=('\0'.join(members)+'\0').encode(),
                                 cwd=stage, capture_output=True, check=True, timeout=10)
        with (output/'initramfs.cpio.gz').open('xb') as packed:
            subprocess.run(['gzip', '-n'], input=archive.stdout, stdout=packed,
                           check=True, timeout=10)
        command = ['podman', 'run', '--rm', '--name', name, '--network', 'none',
                   '--read-only', '--memory', '1536m', '--memory-swap', '1536m',
                   '--cpus', '2', '--pids-limit', '64', '--security-opt', 'no-new-privileges',
                   '-v', str(runtime)+':/runtime:ro',
                   '-v', str(kernel)+':/Image:ro',
                   '-v', str(output/'initramfs.cpio.gz')+':/initramfs.gz:ro',
                   '-v', str(payload)+':/payload:ro', args.image,
                   'qemu-system-aarch64', '-M', 'virt', '-cpu', 'max', '-smp', '2',
                   '-m', '1024M', '-accel', 'tcg,thread=multi',
                   '-global', 'virtio-mmio.force-legacy=false', '-display', 'none',
                   '-monitor', 'none', '-nic', 'none', '-serial', 'stdio', '-no-reboot',
                   '-kernel', '/Image', '-initrd', '/initramfs.gz',
                   '-append', 'console=ttyAMA0 rdinit=/init panic=-1 rog5.virtual_drm=1',
                   '-device', 'virtio-gpu-device,xres=640,yres=480',
                   '-device', 'virtio-keyboard-device', '-device', 'virtio-tablet-device',
                   '-device', 'virtio-rng-device',
                   '-fsdev', 'local,id=rootfs,path=/runtime,security_model=none,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=rootfs,mount_tag=rootfs',
                   '-fsdev', 'local,id=payload,path=/payload,security_model=none,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=payload,mount_tag=payload']
        if render_node:
            index = command.index(args.image)
            command[index:index] = ['--device', str(args.render_node)+':'+str(args.render_node)+':rw']
            command[command.index('-display')+1] = 'egl-headless,rendernode='+str(args.render_node)
            index = command.index('virtio-gpu-device,xres=640,yres=480')
            command[index] = 'virtio-gpu-gl-device,xres=640,yres=480'
        report['command'] = command
        logpath = output/'serial.log'
        with logpath.open('xb') as log:
            launched = True
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    end = time.monotonic() + args.deadline
                    while process.poll() is None:
                        if time.monotonic() >= end or logpath.stat().st_size > 8*1024*1024:
                            raise TimeoutError('guest deadline or 8 MiB log bound exceeded')
                        time.sleep(0.2)
                finally:
                    if process.poll() is None:
                        subprocess.run(['podman', 'stop', '--time', '2', name],
                                       capture_output=True, timeout=10)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                report['qemu_exit_status'] = process.returncode
        log = logpath.read_text(errors='replace')
        report['drm_discovery'] = 'PASS' if 'PASS virtual DRM discovery' in log else 'FAIL'
        report['deniald_kms'] = 'NOT RUN: discovery/CLI are separate from frames'
        report['deniald_cli'] = 'PASS' if 'PASS actual deniald guest CLI' in log else 'NOT RUN'
        if args.flutter_bundle:
            report['deniald_kms'] = 'NOT RUN'
            report['shell_exit'] = 'PASS' if 'PASS actual deniald shell bounded exit' in log else 'FAIL'
            report['shell_rendering'] = session_result(log)
        if (process.returncode == 0 and
                report['drm_discovery'] == 'PASS' and
                ((report.get('shell_exit') == 'PASS' and
                  report['shell_rendering']['status'] == 'PASS') or report['deniald_cli'] == 'PASS')
                and 'PASS guest-script exited cleanly' in log and 'FAIL guest-' not in log):
            report['status'] = 'PASS'
    except Exception as error:
        report['error'] = str(error)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            report['stderr'] = error.stderr.decode(errors='replace')[-4000:]
    finally:
        if launched:
            check = subprocess.run(['podman', 'container', 'exists', name], timeout=10)
            report['container_removed'] = check.returncode == 1
            if not report['container_removed']:
                report['status'] = 'FAIL'
        report['duration_seconds'] = time.monotonic() - start
        for path in (stage/'init', stage/'stage/guest.sh', output/'initramfs.cpio.gz',
                     stage/'stage/graphics-mode', output/'serial.log'):
            if path.is_file():
                report.setdefault('hashes', {})[str(path.relative_to(output))] = digest(path)
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
