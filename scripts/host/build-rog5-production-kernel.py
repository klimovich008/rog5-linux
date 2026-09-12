#!/usr/bin/env python3
"""Unsigned exact-base ROG5 source build. No device, signing, admission or install."""
import argparse
import importlib.util
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO/'configs/kernel/rog5-production-build.json'
PATCHES = REPO/'patches/linux-7.1.4'
MIN_FREE = 3 * 1024**3
DIAGNOSTIC_SOURCE = REPO/'scripts/host/check-production-build-diagnostics.py'
WARNING_POLICY = REPO/'configs/kernel/rog5-production-warning-policy.json'
DT_COMPOSITION = REPO/'scripts/device/test-mobile-dt-composition.py'
TOUCH_PROVIDERS = REPO/'scripts/device/verify-mobile-touch-providers.py'


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): value.update(block)
    return value.hexdigest()


def inputs_unchanged(inputs, root=REPO):
    try: return all(digest(root/name)==expected for name,expected in inputs.items())
    except OSError: return False


def compiled_release(objects):
    # These two generated files are consumed by the completed kernel/module build.
    # A pre-syncconfig `make kernelrelease` can omit CONFIG_LOCALVERSION.
    release=(objects/'include/config/kernel.release').read_text().strip()
    header=(objects/'include/generated/utsrelease.h').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,127}',release):
        raise ValueError('invalid compiled kernel release')
    if header != '#define UTS_RELEASE "'+release+'"':
        raise ValueError('compiled kernel release/header mismatch')
    return release


def series(root=PATCHES):
    groups = {}
    for role in ('production', 'diagnostic'):
        lines = (root/('series.'+role)).read_text().splitlines()
        names = [x for x in lines if x and not x.startswith('#')]
        if names != sorted(set(names)): raise ValueError('unordered/duplicate '+role+' series')
        if any(not re.fullmatch(r'[0-9]{4}-[a-zA-Z0-9_-]+\.patch', x) for x in names):
            raise ValueError('invalid patch name')
        groups[role] = names
    all_names = groups['production'] + groups['diagnostic']
    if len(set(all_names)) != len(all_names) or set(all_names) != {p.name for p in root.glob('*.patch')}:
        raise ValueError('series must be disjoint and cover every patch')
    return groups


def check_config(path, policy):
    fields = dict(line.split('=', 1) for line in path.read_text().splitlines() if line.startswith('CONFIG_'))
    errors = [key+' expected '+value+' got '+fields.get(key, 'n')
              for key, value in policy['required'].items() if fields.get(key, 'n') != value]
    errors += [key+' forbidden' for key in policy['forbidden'] if fields.get(key, 'n') != 'n']
    if errors: raise ValueError('; '.join(errors))
    return fields


def build_environment(output, environ=None):
    env = dict({key:value for key,value in (os.environ if environ is None else environ).items() if not key.startswith('GIT_')}, LC_ALL='C', KBUILD_BUILD_USER='rog5-linux', KBUILD_BUILD_HOST='rog5-builder',
               KBUILD_BUILD_VERSION='1', KBUILD_BUILD_TIMESTAMP='Sat, 18 Jul 2026 14:55:52 +0000',
               SOURCE_DATE_EPOCH='1784386552', PYTHONHASHSEED='0',
               GIT_CEILING_DIRECTORIES=str(output), KCONFIG_NOTIMESTAMP='1')
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'KCONFIG_CONFIG', 'KBUILD_OUTPUT', 'KCFLAGS', 'KAFLAGS', 'CC', 'HOSTCC', 'LOCALVERSION', 'MAKEFLAGS', 'MFLAGS', 'MAKEOVERRIDES'):
        env.pop(key, None)
    env['KCFLAGS'] = '-fdebug-prefix-map='+str(output)+'/source=/usr/src/rog5-linux -fdebug-compilation-dir=/usr/src/rog5-build'
    env['KAFLAGS'] = env['KCFLAGS']
    env['CC_COMPAT'] = 'clang '+env['KCFLAGS']
    return env


def stage_dt_sources(source, names, repo=REPO):
    dtdir = source/'arch/arm64/boot/dts/qcom'
    targets = []
    with (dtdir/'Makefile').open('a') as makefile:
        for relative in names:
            path=repo/relative; shutil.copyfile(path,dtdir/path.name)
            suffix='.dtbo' if path.suffix=='.dtso' else '.dtb'
            target=path.stem+suffix; targets.append('qcom/'+target)
            makefile.write('\ndtb-$(CONFIG_ARCH_QCOM) += '+target+'\n')
            # Linux Makefile.dtbs uses this per-target flag. The board's
            # overlays need its exported labels; other DT targets stay scoped.
            if path.name == 'sm8350-asus-rog-phone5.dts':
                makefile.write('DTC_FLAGS_'+path.stem+' += -@\n')
    return targets


def stage_dt_bindings(source, bindings, repo=REPO):
    for item in bindings:
        relative=Path(item['target'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[:3] != ('Documentation','devicetree','bindings'):
            raise ValueError('binding target must be inside kernel bindings')
        target=source/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        # An external prototype binding must not replace an upstream contract.
        with target.open('xb') as output, (repo/item['source']).open('rb') as input_file:
            shutil.copyfileobj(input_file,output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-git', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, choices=(1, 2), default=2)
    parser.add_argument('--firmware-root', type=Path)
    parser.add_argument('--base-archive', type=Path, help='reuse only the exact hash-pinned immutable-base tar')
    parser.add_argument('--prepare-only', action='store_true', help='apply/resolve config only; compile remains NOT RUN')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists(): parser.error('output must be new; never reuse an unknown build')
    output.mkdir(parents=True)
    started = time.monotonic()
    result = dict(format='rog5-production-kernel-build-result-v1', status='RUNNING',
                  started=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  stages={name:dict(status='NOT RUN') for name in ('defconfig','merge-config','olddefconfig','kernel-build','modules-install','depmod','dtbs-check','dt-composition','touch-providers')}, physical_validation='NOT RUN', signed_candidate='NOT CREATED',
                  installed_bytes='UNCHANGED')
    env = build_environment(output)
    def interrupted(signum, _frame): raise RuntimeError('interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    def save(): (output/'result.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    def capture(argv): return subprocess.check_output(argv, text=True, env=env).strip()
    def run(name, argv, cwd=None):
        if not inputs_unchanged(result.get('inputs',{})):
            raise RuntimeError('frozen build input changed')
        if shutil.disk_usage(output).free < MIN_FREE: raise RuntimeError('less than 3 GiB disk free')
        begin = time.monotonic()
        result['stages'][name] = dict(status='RUNNING', command=argv, started=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        with (output/(name+'.log')).open('wb') as log:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            result['stages'][name]['pid'] = process.pid
            save()
            try:
                while process.poll() is None:
                    if shutil.disk_usage(output).free < MIN_FREE:
                        raise RuntimeError('disk reserve reached; owned build stopped')
                    time.sleep(0.2)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait()
                result['stages'][name].update(status='FAIL', exit_code=process.returncode,
                    seconds=round(time.monotonic()-begin, 3), log_sha256=digest(output/(name+'.log')))
                save()
                raise
        result['stages'][name] = dict(status='PASS' if process.returncode == 0 else 'FAIL',
                                     exit_code=process.returncode, seconds=round(time.monotonic()-begin, 3),
                                     log_sha256=digest(output/(name+'.log')), command=argv)
        save()
        if process.returncode: raise RuntimeError(name+' failed; see '+str(output/(name+'.log')))
    try:
        policy = json.loads(CONFIG.read_text()); groups = series()
        result['repository'] = dict(commit=capture(['git','-C',str(REPO),'rev-parse','HEAD']),
            tree=capture(['git','-C',str(REPO),'rev-parse','HEAD^{tree}']),
            dirty=bool(capture(['git','-C',str(REPO),'status','--porcelain'])))
        inputs = [CONFIG, Path(__file__).resolve(), DIAGNOSTIC_SOURCE, WARNING_POLICY, PATCHES/'series.production', PATCHES/'series.diagnostic']
        inputs += [PATCHES/name for name in groups['production']+groups['diagnostic']]
        inputs += [REPO/name for name in policy['fragments']+policy['dt_sources']]
        inputs += [REPO/item['source'] for item in policy['dt_bindings']]
        inputs += [DT_COMPOSITION, REPO/'scripts/device/verify-recovery-dtb-delta.py',
                   REPO/'scripts/device/verify-display-60hz-dtb-delta.py', TOUCH_PROVIDERS]
        result['inputs'] = {str(p.relative_to(REPO)): digest(p) for p in inputs}
        result['ordered_series']={role:[dict(name=name,sha256=digest(PATCHES/name)) for name in groups[role]] for role in groups}
        result['production_series_binding_sha256']=hashlib.sha256(json.dumps(result['ordered_series']['production'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result['build_limits']=dict(jobs=args.jobs,min_free_disk_bytes=MIN_FREE)
        result['policy'] = policy
        result['linux_base'] = capture(['git','-C',str(args.linux_git),'rev-parse',policy['base_commit']+'^{commit}'])
        if result['linux_base'] != policy['base_commit']: raise ValueError('exact kernel base missing')
        result['linux_base_tree'] = capture(['git','-C',str(args.linux_git),'rev-parse',policy['base_commit']+'^{tree}'])
        result['tools'] = {}
        for name in ('git','make','clang','ld.lld','llvm-ar','llvm-nm','llvm-objcopy','llvm-strip','llvm-readelf','bc','bison','flex','depmod','modinfo','cpp','dtc','fdtoverlay','python3','openssl','perl'):
            path = shutil.which(name)
            if not path: raise RuntimeError('missing build tool '+name)
            version = subprocess.run([path, '--version'], env=env, capture_output=True, text=True)
            result['tools'][name] = dict(path=str(Path(path).resolve()), sha256=digest(path),
                                        version=(version.stdout or version.stderr).splitlines()[:2])
        result['schema_tools'] = {}
        for name in ('dt-validate','dt-doc-validate','dt-mk-schema'):
            path = shutil.which(name)
            if path:
                version = subprocess.run([path,'--version'],env=env,capture_output=True,text=True)
                result['schema_tools'][name] = dict(path=path,sha256=digest(path),version=(version.stdout or version.stderr).strip())
            else: result['schema_tools'][name] = dict(status='MISSING')
        source = output/'source'; source.mkdir()
        archive = args.base_archive.resolve() if args.base_archive else output/'base.tar'
        if args.base_archive:
            if args.base_archive.is_symlink() or not archive.is_file(): raise ValueError('unsafe base archive')
        else:
            with archive.open('wb') as stream:
                subprocess.run(['git','-C',str(args.linux_git),'archive',policy['base_commit']], stdout=stream, check=True, env=env)
        result['base_archive_sha256'] = digest(archive)
        if result['base_archive_sha256'] != policy['base_archive_sha256']:
            raise ValueError('exact-base archive bytes changed')
        run('extract', ['tar','-xf',str(archive),'-C',str(source)])
        if not args.base_archive: archive.unlink()
        for name in groups['production']:
            run('apply-'+name[:4], ['git','apply','--check',str(PATCHES/name)], cwd=source)
            subprocess.run(['git','apply',str(PATCHES/name)], cwd=source, env=env, check=True)
        targets = stage_dt_sources(source, policy['dt_sources'])
        stage_dt_bindings(source, policy['dt_bindings'])
        objects = output/'objects'
        make = ['make','-C',str(source),'O='+str(objects),'ARCH=arm64','LLVM=1']
        run('defconfig', make+['defconfig'])
        run('merge-config', [str(source/'scripts/kconfig/merge_config.sh'),'-m','-O',str(objects),str(objects/'.config')]+[str(REPO/p) for p in policy['fragments']])
        run('olddefconfig', make+['olddefconfig'])
        check_config(objects/'.config',policy)
        result['config_sha256']=digest(objects/'.config')
        result['btf'] = dict(status='DISABLED', resolved_config_debug_info_btf='n', pahole='NOT REQUIRED: CONFIG_DEBUG_INFO_NONE=y')
        spec=importlib.util.spec_from_file_location('board_diagnostics',DIAGNOSTIC_SOURCE)
        diagnostics=importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostics)
        warning_policy=json.loads(WARNING_POLICY.read_text())
        if args.prepare_only:
            result['status']='PREPARED'; result['compilation']='NOT RUN'
        else:
            run('kernel-build',make+['-j'+str(args.jobs),'W=1','Image','modules',*targets])
            result['release']=compiled_release(objects)
            result['outputs']={str(p.relative_to(output)):digest(p) for p in
                [objects/'arch/arm64/boot/Image',objects/'Module.symvers',objects/'System.map',objects/'.config']+
                [objects/'arch/arm64/boot/dts'/target for target in targets]}
            save()
            # modules target includes real modpost. Install solely into disposable output.
            run('modules-install',make+['INSTALL_MOD_PATH='+str(output/'modules'),'INSTALL_MOD_STRIP=1','modules_install'])
            run('depmod', ['depmod','-a','-e','-F',str(objects/'System.map'),'-b',str(output/'modules'),result['release']])
            module_data=[]; names=set()
            for module in sorted((output/'modules').rglob('*.ko')):
                name=capture(['modinfo','-F','name',str(module)]); names.add(name)
                vermagic=capture(['modinfo','-F','vermagic',str(module)])
                if vermagic.split()[0]!=result['release']: raise ValueError('module vermagic mismatch '+str(module))
                firmware=capture(['modinfo','-F','firmware',str(module)]).splitlines()
                module_data.append(dict(path=str(module.relative_to(output)), sha256=digest(module), name=name,
                    vermagic=vermagic,depends=capture(['modinfo','-F','depends',str(module)]), firmware=firmware))
            modroot=output/'modules/lib/modules'/result['release']
            result['module_dependency_errors']=diagnostics.module_closure(module_data,
                (modroot/'modules.builtin').read_text(), (modroot/'modules.dep').read_text(), result['release'])
            missing=set(policy['required_modules'])-names
            if missing: raise ValueError('required modules missing: '+','.join(sorted(missing)))
            (output/'module-provenance.json').write_text(json.dumps(module_data,indent=2)+'\n')
            firmware=sorted({f for entry in module_data for f in entry['firmware']})
            result['firmware']={name:dict(status='NOT RUN' if args.firmware_root is None else 'MISSING') for name in firmware}
            if args.firmware_root:
                for name in firmware:
                    path=args.firmware_root/name
                    if path.is_file(): result['firmware'][name]=dict(status='PRESENT',sha256=digest(path))
            result['outputs']={str(p.relative_to(output)):digest(p) for p in
                [objects/'arch/arm64/boot/Image',objects/'Module.symvers',objects/'System.map',objects/'.config',output/'module-provenance.json']+
                [objects/'arch/arm64/boot/dts'/target for target in targets]}
            missing_schema=[name for name in ('dt-validate','dt-doc-validate','dt-mk-schema') if not shutil.which(name)]
            if missing_schema:
                result['stages']['dtbs-check']=dict(status='BLOCKED',reason='missing schema tools: '+', '.join(missing_schema))
                result['stages']['dt-composition']=dict(status='BLOCKED',reason='missing schema tools')
                result['stages']['touch-providers']=dict(status='BLOCKED',reason='composition unavailable without schema tools')
            else:
                run('dtbs-check',make+['-j'+str(args.jobs),'W=1','CHECK_DTBS=y',*targets])
                run('dt-composition',[sys.executable,str(DT_COMPOSITION),
                    '--linux-source',str(source),'--base-dtb',str(objects/'arch/arm64/boot/dts/qcom/sm8350-asus-rog-phone5.dtb'),
                    '--schema',str(objects/'Documentation/devicetree/bindings/processed-schema.json'),
                    '--output',str(output/'dt-composition')])
                composition=json.loads((output/'dt-composition/result.json').read_text())
                if composition['status']!='PASS': raise RuntimeError('composed DT qualification failed')
                result['dt_composition']=dict(status='PASS',physical_validation='NOT RUN',
                    result_sha256=digest(output/'dt-composition/result.json'),outputs=composition['outputs'])
                run('touch-providers',[sys.executable,str(TOUCH_PROVIDERS),
                    '--dtb',str(output/'dt-composition/composed-2.dtb'),
                    '--config',str(objects/'.config'),
                    '--module-metadata',str(output/'module-provenance.json')])
                result['touch_providers']=json.loads((output/'touch-providers.log').read_text())
            result['diagnostics']=[]
            for stage in ('kernel-build','modules-install','depmod','dtbs-check'):
                log=output/(stage+'.log')
                if log.is_file():
                    result['diagnostics'] += [dict(stage=stage, **entry) for entry in
                        diagnostics.diagnostics(log.read_text(errors='replace'),stage,source,objects,warning_policy)]
            result['unreviewed_diagnostics']=sum(not entry['allowed'] for entry in result['diagnostics'])
            if result['module_dependency_errors']: raise RuntimeError('module dependency closure failed')
            if result['unreviewed_diagnostics']:
                raise RuntimeError('unreviewed compiler/DT/tool diagnostics: '+str(result['unreviewed_diagnostics']))
            if result['stages']['dtbs-check']['status']!='PASS': result['status']='BLOCKED'
            else: result['status']='PASS'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        result['status']='FAIL'; result['error']=str(error)
    finally:
        result['ended']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        result['duration_seconds']=round(time.monotonic()-started,3)
        if not inputs_unchanged(result.get('inputs',{})):
            result['status']='FAIL'; result['error']='build input changed during execution'
        result['exit_status']=0 if result['status'] in ('PASS','PREPARED') else 1
        save()
    return result['exit_status']

if __name__=='__main__': sys.exit(main())
