#!/usr/bin/env python3
"""Build an unsigned touch prototype against the read-only Q6 kernel kit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
Q6_RESULT = 'b4e9b22be52dda512416ba4313cb8ee78e458c99685bea67ee4ab76e2fc7a999'
Q6_BINDING = 'e61c8bef682fb5367351fdb6b58abb7f98652e3fcb60878ced52a5a2a819f5f4'
MIN_FREE = 3 * 1024**3
MODULE_FILES = ('rog5_fts3658u.c', 'rog5_fts_protocol.h', 'Makefile')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_kit(kit, qualification, result_pin=Q6_RESULT, binding_pin=Q6_BINDING):
    need(digest(qualification/'result.json') == result_pin, 'Q6 result identity')
    need(digest(qualification/'final-source-binding.json') == binding_pin, 'Q6 binding identity')
    result = json.loads((qualification/'result.json').read_text())
    binding = json.loads((qualification/'final-source-binding.json').read_text())
    need(binding['qualification_sha256'] == result_pin, 'qualification binding')
    need(result['status'] == 'FAIL' and result['physical_validation'] == 'NOT RUN', 'Q6 qualification scope')
    need(digest(qualification/'module-provenance.json') == result['module_metadata_sha256'], 'module metadata identity')
    modules = json.loads((qualification/'module-provenance.json').read_text())
    need(len(modules) == result['module_count'], 'module count')
    for name, expected in result['outputs'].items():
        path = (kit/name).resolve()
        need(path.is_relative_to(kit.resolve()), 'kit path escape')
        need(digest(path) == expected, 'kit output changed: '+name)
    release = (kit/'objects/include/config/kernel.release').read_text().strip()
    need(release == result['release'], 'compiled release mismatch')
    need((kit/'objects/include/generated/utsrelease.h').read_text().strip() ==
         '#define UTS_RELEASE "'+release+'"', 'generated release mismatch')
    config = dict(line.split('=', 1) for line in (kit/'objects/.config').read_text().splitlines() if line.startswith('CONFIG_'))
    for key in ('CONFIG_ARM64', 'CONFIG_MODULES', 'CONFIG_I2C', 'CONFIG_INPUT'):
        need(config.get(key) == 'y', 'required kit configuration: '+key)
    for name, expected in result['panel_source'].items():
        need(digest(kit/'source'/name) == expected, 'kit source binding: '+name)
    need(all(m['vermagic'].split()[0] == release for m in modules), 'retained module release')
    return result, binding, modules


def run_owned(command, log, env, deadline, minimum_free=MIN_FREE, stage=None):
    """Own the process group; interruption and timeout always kill/reap it."""
    begin = time.monotonic()
    old = {}
    cleaning = False
    def interrupted(signum, frame):
        if not cleaning:
            raise RuntimeError('interrupted: '+str(signum))
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        old[sig] = signal.signal(sig, interrupted)
    process = None
    try:
        need(shutil.disk_usage(log.parent).free >= minimum_free, 'disk reserve below3GiB')
        with log.open('wb') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
            while process.poll() is None:
                need(time.monotonic() < deadline, 'build deadline expired')
                need(shutil.disk_usage(log.parent).free >= minimum_free, 'disk reserve reached')
                time.sleep(.05)
            need(process.returncode == 0, 'command failed: '+str(process.returncode))
    except BaseException as error:
        if stage is not None: stage['error'] = str(error)
        raise
    finally:
        cleaning = True
        if process is not None:
            # Kill same-group descendants even when their leader already exited.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
        if stage is not None:
            stage.update(seconds=round(time.monotonic()-begin, 3),
                         exit_code=process.returncode if process is not None else None,
                         status='FAIL' if 'error' in stage else 'PASS')
        for sig, handler in old.items(): signal.signal(sig, handler)
    return round(time.monotonic()-begin, 3)


def check_module(metadata, retained, builtin):
    need(metadata['name'] == 'rog5_fts3658u', 'unexpected module name')
    vermagics = {m['vermagic'] for m in retained}
    need(metadata['vermagic'] in vermagics, 'vermagic mismatch')
    names = {m['name'] for m in retained} | {Path(p).stem.replace('-', '_') for p in builtin.splitlines() if p}
    dependencies = set(filter(None, metadata['depends'].split(',')))
    need(dependencies <= names, 'missing module dependency: '+','.join(sorted(dependencies-names)))
    return sorted(dependencies)


def sandbox(command, output):
    return ['bwrap', '--die-with-parent', '--unshare-user', '--unshare-pid', '--unshare-net',
            '--ro-bind', '/', '/', '--proc', '/proc', '--dev', '/dev', '--bind', str(output), str(output),
            '--chdir', str(output), '--'] + command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, choices=(1, 2), default=2)
    parser.add_argument('--timeout', type=int, default=120, choices=range(1, 601))
    args = parser.parse_args()
    kit = args.kit.resolve(); qualification = args.qualification.resolve(); output = args.output.resolve()
    need(not output.exists(), 'output must be fresh')
    need(not output.is_relative_to(kit) and not kit.is_relative_to(output), 'output overlaps retained kit')
    need(not output.is_relative_to(qualification) and not qualification.is_relative_to(output), 'output overlaps evidence')
    output.mkdir(parents=True)
    started = time.monotonic(); deadline = started + args.timeout
    report = dict(format='rog5-touch-module-prototype-build-v1', status='FAIL', scope='software prototype',
                  physical_validation='NOT RUN', candidate='NOT CREATED', admission='BLOCKED: prototype; no hardware qualification',
                  retained_qualification='FAIL: RPMh RSC schema', stages={}, limits=dict(jobs=args.jobs,seconds=args.timeout,min_free=MIN_FREE))
    env = {'PATH':'/usr/bin:/bin', 'LC_ALL':'C', 'HOME':str(output), 'TMPDIR':str(output),
           'KBUILD_BUILD_USER':'rog5-linux', 'KBUILD_BUILD_HOST':'rog5-builder', 'KBUILD_BUILD_VERSION':'1',
           'KBUILD_BUILD_TIMESTAMP':'Sat, 18 Jul 2026 14:55:52 +0000', 'SOURCE_DATE_EPOCH':'1784386552'}
    try:
        need(shutil.which('bwrap', path=env['PATH']), 'read-only sandbox unavailable')
        receipt, binding, retained = verify_kit(kit, qualification)
        report['kit'] = dict(path=str(kit), qualification=str(qualification), result_sha256=Q6_RESULT,
                             binding_sha256=Q6_BINDING, source_binding=binding['repository_commit'],
                             linux_base=receipt['source_kernel_base'], config_sha256=receipt['config_sha256'],
                             outputs=receipt['outputs'], module_metadata_sha256=receipt['module_metadata_sha256'])
        report['tools'] = {}
        for name in ('make','clang','ld.lld','llvm-ar','llvm-nm','llvm-objcopy','modinfo'):
            path = shutil.which(name, path=env['PATH']); need(path, 'missing tool '+name)
            need(digest(path) == receipt['tools'][name]['sha256'], 'kit tool identity: '+name)
            report['tools'][name] = dict(path=path, sha256=digest(path))
        capture = lambda argv: subprocess.check_output(argv, text=True, env=env, timeout=5).strip()
        report['repository'] = dict(commit=capture(['git','-C',str(REPO),'rev-parse','HEAD']),
            tree=capture(['git','-C',str(REPO),'rev-parse','HEAD^{tree}']),
            dirty=bool(capture(['git','-C',str(REPO),'status','--porcelain'])))
        module = output/'module'; module.mkdir()
        report['inputs'] = {}
        for name in MODULE_FILES:
            source = REPO/'tools/rog5-fts3658u'/name
            report['inputs'][str(source.relative_to(REPO))] = digest(source)
            shutil.copyfile(source, module/name)
            need(digest(module/name) == digest(source), 'copy changed')
        report['builder_sha256'] = digest(Path(__file__))
        command = sandbox(['make','-C',str(kit/'source'),'O='+str(kit/'objects'),'ARCH=arm64','LLVM=1',
                           '-j'+str(args.jobs),'W=1','M='+str(module), 'modules'], output)
        report['stages']['build'] = dict(command=command, status='RUNNING')
        (output/'result.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
        run_owned(command, output/'build.log', env, deadline, stage=report['stages']['build'])
        text = (output/'build.log').read_text()
        need(not re.search(r'\b(?:warning|error):', text, re.I), 'module compilation diagnostic')
        artifact = module/'rog5_fts3658u.ko'; need(artifact.is_file(), 'module missing')
        metadata = {key:capture(['modinfo','-F',key,str(artifact)]) for key in ('name','vermagic','depends')}
        dependencies = check_module(metadata, retained, (kit/'objects/modules.builtin').read_text())
        report['module'] = dict(metadata, dependencies=dependencies, path=str(artifact), sha256=digest(artifact), size=artifact.stat().st_size)
        # Record the actual source/header dependency closure emitted by kbuild.
        dependencies_used = set()
        for command_file in module.glob('.*.cmd'):
            dependencies_used.update(re.findall(re.escape(str(kit))+r'/[^\s\\()]+', command_file.read_text()))
        # Build control and generated configuration are inputs too, not just the
        # C dependency list; distinguish them in the receipt for origin review.
        for name in ('source/Makefile', 'source/scripts/Makefile.build',
                     'source/scripts/Makefile.modpost', 'source/scripts/Makefile.modfinal',
                     'objects/Makefile', 'objects/include/generated/autoconf.h',
                     'objects/include/generated/compile.h', 'objects/include/config/auto.conf',
                     'objects/include/config/kernel.release', 'objects/Module.symvers'):
            dependencies_used.add(str(kit/name))
        report['consumed_kit_files'] = {p:digest(Path(p)) for p in sorted(dependencies_used) if Path(p).is_file()}
        report['consumed_kit_file_roots'] = {'source':str(kit/'source'), 'generated_or_built':str(kit/'objects')}
        need(report['consumed_kit_files'], 'missing kbuild source dependency receipt')
        verify_kit(kit, qualification)
        need(all(digest(REPO/p)==h for p,h in report['inputs'].items()), 'module source changed during build')
        report['status'] = 'PASS'
        report['limitations'] = ['Q6 kit remains schema FAIL and unqualified on hardware.',
            'Q6 recorded outputs/panel source and compiler verified; consumed header hashes are newly recorded, not independently matched to a full historical source-tree manifest.',
            'Existing production module bytes are represented by the verified Q6 metadata receipt; no loading, signing, depmod mutation or installation performed.',
            'Cleanup covers owned process group and sandbox PID namespace.']
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    finally:
        report['seconds'] = round(time.monotonic()-started, 3)
        if (output/'build.log').exists(): report['build_log_sha256'] = digest(output/'build.log')
        (output/'result.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(report['status']+': '+str(output/'result.json'))
    return 0 if report['status']=='PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
