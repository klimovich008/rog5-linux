#!/usr/bin/env python3
"""A01 exact wrapper, target, firmware and Arch runtime composition.

Offline only. No claim consumption, signing, phone access or prerequisite setup.
Incomplete dynamic composition remains BLOCKED, never an imported component PASS.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import resource
import shlex
import shutil
import stat
import subprocess
import tempfile
import time

SPEC = importlib.util.spec_from_file_location('final_composition', Path(__file__).with_name('check-rescue-root-composition.py'))
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)
CLAIMS = C.load('composition_claim_records', 'scripts/host/consume-exact-boot-claim.py')
RECEIVER = C.load('composition_receiver', 'scripts/host/headless-stage-receiver.py')


class Blocked(Exception):
    pass


def root_identity(path):
    s=path.lstat()
    return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,
            s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def local_selector_identity(root_image, expected_hash):
    """Read only the fixed loader selector; never mount, repair or stage a root.

    This is an early stale-input refusal, not full selector/bundle qualification.
    debugfs defaults to read-only; no command or filesystem path comes from metadata.
    """
    if (not root_image.is_absolute() or root_image.is_symlink() or not root_image.is_file()
            or not re.fullmatch(r'[0-9a-f]{64}',expected_hash)):
        raise ValueError('invalid retained root/selector identity')
    tool=shutil.which('debugfs')
    if not tool:
        raise Blocked('read-only ext4 inspection requires debugfs')
    signature=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,
                        s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    before=signature(root_image.lstat())
    path='/boot/rog5-linux/selector'
    info=subprocess.run([tool,'-R','stat '+path,str(root_image)],capture_output=True,timeout=5)
    size=re.findall(rb'(?m)^User:\s+0\s+Group:\s+0\s+Project:\s+0\s+Size:\s+([0-9]+)$',info.stdout)
    if (info.returncode or b'Type: regular' not in info.stdout or len(size)!=1
            or not 1<=int(size[0])<=4096 or not re.search(rb'(?m)^Links: 1(?:\s|$)',info.stdout)):
        raise ValueError('missing or unsafe retained root selector')
    result=subprocess.run([tool,'-R','cat '+path,str(root_image)],capture_output=True,timeout=5)
    if result.returncode or len(result.stdout)!=int(size[0]) or signature(root_image.lstat())!=before:
        raise ValueError('retained root selector read changed or failed')
    actual=hashlib.sha256(result.stdout).hexdigest()
    if actual!=expected_hash:
        raise ValueError('retained root selector mismatch: expected '+expected_hash+' observed '+actual)
    return dict(path=path,size=len(result.stdout),sha256=actual,scope='selector identity only')


def root_member(root_image, path, limit, *, directory=False):
    """Bounded read-only debugfs access to the fixed bundle store, not host paths."""
    if (not re.fullmatch(r'/boot/rog5-linux/bundles/[a-z0-9][a-z0-9._-]{0,127}'
                         r'(?:/(?:manifest|manifest[.]sig|Image|board[.]dtb|initramfs[.]cpio[.]gz))?',path)
            or not root_image.is_absolute() or root_image.is_symlink() or not root_image.is_file()
            or not 1 <= limit <= 256*1024*1024):
        raise ValueError('invalid retained bundle read')
    tool=shutil.which('debugfs')
    if not tool: raise Blocked('read-only ext4 inspection requires debugfs')
    before=root_identity(root_image)
    def query(command, bound):
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            result=subprocess.run([tool,'-R',command,str(root_image)],stdout=output,stderr=errors,
                timeout=5,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_FSIZE,(bound,bound)))
            output.seek(0); data=output.read(bound+1)
        if result.returncode or len(data)>bound:
            raise ValueError('bounded retained bundle read failed')
        return data
    parts=path.split('/')[1:]
    for index in range(1,len(parts)+1):
        current='/'+'/'.join(parts[:index])
        info=query('stat '+current,16384)
        kind=re.findall(rb'Type: (\w+)\s+Mode:\s+([0-7]+)',info)
        size=re.findall(rb'(?m)^User:\s+0\s+Group:\s+0\s+Project:\s+0\s+Size:\s+(\d+)$',info)
        want_dir=index<len(parts) or directory
        if (len(kind)!=1 or len(size)!=1 or kind[0][0]!=(b'directory' if want_dir else b'regular')
                or int(kind[0][1],8)&0o7022):
            raise ValueError('unsafe retained bundle metadata: '+current)
        if not want_dir and (not re.search(rb'(?m)^Links: 1(?:\s|$)',info)
                             or not 1<=int(size[0])<=limit):
            raise ValueError('unsafe retained bundle size/links: '+current)
    data=query(('ls -p ' if directory else 'cat ')+path,limit)
    if (root_identity(root_image)!=before
            or (not directory and len(data)!=int(size[0]))):
        raise ValueError('retained bundle source changed or truncated')
    return data


def external_bundle_plan(root_image, record, recovery_members):
    """Verify both selector bundles from the paired root with the sealed verifier.

    This never accepts an unrelated host bundle directory or substitutes the
    repository verifier for the bytes authenticated in the recovery image.
    """
    if record.get('execution')!='fastboot-boot-selector-trial':
        raise Blocked('unsupported external bundle composition family')
    bundles=[(record['target_bundle'],record['manifest_sha256']),
             (record['fallback_bundle'],record['fallback_manifest_sha256'])]
    if (bundles[0][0]==bundles[1][0] or any(
            not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}',name)
            or not re.fullmatch(r'[0-9a-f]{64}',digest) for name,digest in bundles)):
        raise ValueError('invalid canonical external bundle selection')
    before=root_identity(root_image)
    selector=local_selector_identity(root_image,record['selector_sha256'])
    members=dict(recovery_members); plans=[]
    filenames={'manifest':4096,'manifest.sig':64,'Image':256*1024*1024,
               'board.dtb':2*1024*1024,'initramfs.cpio.gz':256*1024*1024}
    for bundle,digest in bundles:
        path='/boot/rog5-linux/bundles/'+bundle
        listing=root_member(root_image,path,16384,directory=True)
        names=[]
        for line in listing.splitlines():
            if not line: continue
            fields=line.split(b'/')
            if len(fields)!=8 or fields[0] or fields[-1]:
                raise ValueError('invalid retained bundle inventory')
            if fields[5] not in (b'.',b'..'): names.append(fields[5].decode('ascii'))
        if sorted(names)!=sorted(filenames):
            raise ValueError('unexpected retained bundle inventory')
        prefix='usr/share/rog5/ram-bundles/'+bundle
        if any(name==prefix or name.startswith(prefix+'/') for name in members):
            raise ValueError('mixed embedded and external bundle members')
        for name,bound in filenames.items():
            data=root_member(root_image,path+'/'+name,bound)
            if name=='manifest' and hashlib.sha256(data).hexdigest()!=digest:
                raise ValueError('retained bundle manifest mismatch')
            C.SEALED.ARCHIVE.add(members,prefix+'/'+name,data,stat.S_IFREG|0o644)
        plans.append(C.sealed_bundle_plan(members,bundle,digest))
    if root_identity(root_image)!=before:
        raise ValueError('retained root changed across bundle verification')
    return members,plans[0],dict(source='retained-root-only',selector=selector,
                                 primary=plans[0],fallback=plans[1])


def timing_contract(manifest, plan, wrapper, members):
    def options(line):
        values={}
        for word in shlex.split(line):
            if not word.startswith('rog5.'):
                continue
            key,value=word.split('=',1)
            if key in values:
                raise ValueError('duplicate signed timing/identity argument')
            values[key]=value
        return values
    target=options(plan['cmdline']); recovery=options(wrapper['cmdline'])
    timing=C.ACCEPTANCE.load_contract()['defaults']['rescue_capture']
    rollback=int(manifest['rollback_timeout']); timeout=int(manifest['target_timeout'])
    expected={'rog5.bundle':manifest['bundle'], 'rog5.target_timeout':str(timeout),
              'rog5.recovery_timeout':str(rollback)}
    if (any(target.get(k)!=v for k,v in expected.items())
            or plan['target_timeout']!=str(timeout) or plan['target_id']!=manifest['target_id']
            or not 30<=timeout<=600 or not 300<=rollback<=900 or timeout>rollback-30
            or rollback!=timing['target_rollback_seconds']
            or recovery.get('rog5.recovery_timeout')!=str(timing['recovery_seconds'])):
        raise ValueError('signed target/wrapper/capture timing mismatch')
    source=members['init'][1].decode()
    endpoint=re.findall(r'nc -n -w 1 -s ([0-9.]+) \\\n\s*([0-9.]+) ([0-9]+) >',source)
    if endpoint != [(RECEIVER.PEER,RECEIVER.ADDRESS,str(RECEIVER.PORT))]:
        raise ValueError('sealed diagnostic sender/host receiver mismatch')
    return dict(rollback_seconds=rollback,target_seconds=timeout,
                recovery_seconds=timing['recovery_seconds'],capture_seconds=sum(timing.values()),
                peer=RECEIVER.PEER,host=RECEIVER.ADDRESS,port=RECEIVER.PORT,
                scope='signed budgets, generated units and stage framing; physical USB is separate')


def read_artifact(path, limit=256*1024*1024):
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('not an exact regular artifact: '+str(path))
    with path.open('rb') as stream:
        data = stream.read(limit+1)
    if len(data)>limit:
        raise ValueError('artifact exceeds bound')
    return data


def inspect(args, checks):
    try:
        record = dict(line.split('=',1) for line in CLAIMS.expected_record(args.candidate).decode().splitlines())
    except CLAIMS.ClaimError as error:
        raise Blocked('missing repository-owned wrapper identity: '+str(error)) from error
    boot = read_artifact(args.boot_image)
    if hashlib.sha256(boot).hexdigest() != record.get('boot_image_sha256'):
        raise ValueError('canonical boot image mismatch')
    # Authenticated whole-image identity precedes parsing or running sealed code.
    kernel_size = int.from_bytes(boot[8:12], 'little')
    recovery_size = int.from_bytes(boot[12:16], 'little')
    recovery_offset = 4096 + ((kernel_size+4095)//4096)*4096
    kernel = boot[4096:4096+kernel_size]
    recovery = boot[recovery_offset:recovery_offset+recovery_size]
    if hashlib.sha256(recovery).hexdigest() != record.get('recovery_initramfs_sha256'):
        raise ValueError('canonical recovery archive mismatch')
    cmdline = boot[44:1580].split(b'\0',1)[0].decode('ascii')
    wrapper = C.wrapper_composition(boot,kernel,recovery,cmdline)
    avb = C.REPO/'artifacts/android-boot-tools-v1/avbtool.py'
    if avb.is_symlink() or C.ACCEPTANCE.sha_file(avb) != '6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff':
        raise ValueError('AVB verifier changed')
    with tempfile.TemporaryDirectory(prefix='avb-',dir=args.output) as tmp:
        image=Path(tmp)/'boot.img'; image.write_bytes(boot)
        run=subprocess.run(['python3',str(avb),'verify_image','--image',str(image)],capture_output=True,timeout=15)
        (args.output/'avb.log').write_bytes(run.stdout+run.stderr)
        if run.returncode: raise ValueError('AVB image integrity verification failed')
    checks['wrapper']='PASS'
    wrapper['avb_integrity_verified']=True
    with gzip.GzipFile(fileobj=io.BytesIO(recovery)) as stream:
        payload=stream.read(512*1024*1024+1)
    if len(payload)>512*1024*1024: raise ValueError('recovery archive too large')
    members=C.SEALED.ARCHIVE.entries(payload)
    bundle=record['target_bundle']; prefix='usr/share/rog5/ram-bundles/'+bundle
    external=None
    if prefix+'/manifest' not in members:
        members,plan,external=external_bundle_plan(args.root_image,record,members)
    else:
        plan=C.sealed_bundle_plan(members,bundle,record['manifest_sha256'])
    hashes={'boot_bundle':hashlib.sha256(boot).hexdigest()}
    for role, filename, path in (('kernel','Image',args.kernel),('dtb','board.dtb',args.dtb),
                                  ('initramfs','initramfs.cpio.gz',args.target_archive)):
        data=read_artifact(path)
        if data != members[prefix+'/'+filename][1]:
            raise ValueError('signed target/release artifact mismatch: '+role)
        hashes[role]=hashlib.sha256(data).hexdigest()
    checks['signed_target']='PASS'
    target=target_members(members[prefix+'/initramfs.cpio.gz'][1])
    profile='server-runtime' if b'expected_persistent_overlay_mode=1\n' in target['init'][1] else 'rescue'
    values=C.archive_parameters(target,profile=profile)
    if values['KERNEL_RELEASE']!=plan['target_release']:
        raise ValueError('target archive/verified-plan release mismatch')
    checks['archive']='PASS'
    manifest=dict(line.split('=',1) for line in members[prefix+'/manifest'][1].decode().splitlines())
    timing=timing_contract(manifest,plan,wrapper,target)
    return dict(wrapper=wrapper,plan=plan,artifact_hashes=hashes,profile=profile,timing=timing,
                external_bundles=external)


def target_members(blob):
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
        payload=stream.read(512*1024*1024+1)
    if len(payload)>512*1024*1024:
        raise ValueError('target archive too large')
    return C.SEALED.ARCHIVE.entries(payload)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ('kernel','dtb','target-archive','root-image','boot-image','output'):
        parser.add_argument('--'+option,type=Path,required=True)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--activation-fixture-build',type=Path,
                        help='existing private QEMU-only link fixture build; never a phone artifact')
    args=parser.parse_args()
    if not args.output.is_absolute() or args.output.resolve().is_relative_to(C.REPO) or args.output.exists():
        parser.error('output must be new and private outside Git')
    os.umask(0o077); args.output.mkdir(mode=0o700)
    source=C.ACCEPTANCE.source_identity(); start=time.monotonic()
    contract=next(t for t in C.ACCEPTANCE.load_contract()['tests'] if t['id']=='A01')
    checks={name:'NOT RUN' for name in contract['required_checks']}
    report=dict(status='BLOCKED',a01_qualified=False,release_qualified=False,checks=checks,
                source=source,candidate=args.candidate,runner_sha256=C.ACCEPTANCE.sha_file(Path(__file__)))
    try:
        if any(not shutil.which(tool) for tool in ('bwrap','python3','qemu-aarch64-static')):
            raise Blocked('missing isolated verification prerequisites')
        if args.root_image.is_symlink() or not args.root_image.is_absolute() or not args.root_image.is_file():
            raise Blocked('missing exact retained root image')
        root_before=root_identity(args.root_image)
        report.update(inspect(args,checks))
        if not shutil.which('podman') or not shutil.which('modinfo'):
            raise Blocked('missing exact-kernel VM/module prerequisites')
        target=target_members(read_artifact(args.target_archive))
        builder=(C.REPO/'scripts/device/build-persistent-root-initramfs.sh').read_text()
        digests=re.findall(r'\[ "\$firmware_tree_sha" = \\\n\s*([0-9a-f]{64}) \]',builder)
        loader=target['sbin/rog5-load-persistent-power-usb'][1].decode()
        counts=re.findall(r'find "\$firmware_runtime"[^\n]+\)" -eq ([0-9]+) \]',loader)
        if len(digests)!=1 or len(counts)!=1:
            raise ValueError('ambiguous accepted firmware build contract')
        report['firmware']=C.firmware_composition(target,digests[0],int(counts[0]))
        if report['profile']=='server-runtime':
            report['radio_firmware']=C.radio_firmware_composition(target)
        core,pending=C.core_module_members(target,report['profile'])
        modules=C.module_closure(core,report['plan']['target_release'])
        refusals=[];activation_fixture=None
        if pending:
            target,modules,report['radio_modules']=C.radio_module_composition(target,modules,report['plan']['target_release'])
            refusals=C.board_helper_refusals(target,modules[0]['vermagic'])
            pending=[row for row in pending if row['path'].endswith('.ko')]
            edge=C.load('a01_edge','scripts/host/rog5_module_edge.py')
            fixture=C.load('a01_fixture','scripts/host/rog5_a01_fixture.py')
            try:
                report['activation_static_edge']=edge.inspect_edge(target,modules[0]['vermagic'])
                activation_fixture,report['activation_fixture']=fixture.load_fixture(
                    args.activation_fixture_build,report['artifact_hashes']['kernel'],modules[0]['vermagic'])
            except (edge.EdgeUnavailable,fixture.FixtureUnavailable) as error:
                raise Blocked(str(error)) from error
        root_hash=C.ACCEPTANCE.sha_file(args.root_image)
        report['artifact_hashes']['rootfs']=root_hash
        report['runtime']=C.vm_runtime(target,modules,args.kernel,args.root_image,
                                     args.output,profile=report['profile'],firmware=True,
                                     recovery_timeout=report['timing']['rollback_seconds'],
                                     command_line=report['plan']['cmdline'],refusals=refusals,
                                     activation_fixture=activation_fixture)
        if C.ACCEPTANCE.sha_file(args.root_image)!=root_hash or root_identity(args.root_image)!=root_before:
            raise ValueError('retained root image changed')
        for role,path in (('kernel',args.kernel),('dtb',args.dtb),
                          ('initramfs',args.target_archive),('boot_bundle',args.boot_image)):
            if C.ACCEPTANCE.sha_file(path)!=report['artifact_hashes'][role]:
                raise ValueError('artifact changed during runtime check: '+role)
        report['root_unchanged']=True
        if report['runtime']['status']!='PASS':
            raise ValueError('exact-kernel runtime composition failed; see runtime.log')
        checks['root_runtime']='PASS'
        try:
            stage=RECEIVER.STAGES.parse_stage_record(report['runtime']['stage_frame'].encode(),
                        expected_release=report['plan']['target_release'])
        except (AttributeError, RECEIVER.STAGES.PersistentCycleError) as error:
            raise ValueError('sealed producer/host stage consumer mismatch') from error
        if (stage.stage,stage.state,stage.detail,stage.sequence)!=('runtime','PASS','composition',1):
            raise ValueError('unexpected exact-shell stage proof')
        report['timing']['virtual_boot_id']=stage.boot_id
        checks['timing_transport']='PASS'
        checks['firmware']='PASS'  # Core and (when present) radio inventories + exact VM readback.
        proven={row['path'] for row in refusals}
        if activation_fixture is not None:
            if report['runtime']['activation_split']!='PASS':
                raise ValueError('missing exact consumer BTF/refusal evidence')
            proven.add('rog5-native-wifi/rog5-wifi-activate.ko')
            report['activation_scope']={
                'offline_dependency_and_safe_refusal':'PASS',
                'real_pair_hardware_initialization':'NOT RUN',
                'limitations':['static real-provider edge plus separate exact-kernel refusals',
                    'consumer relocation/BTF with inert test-only provider; no validator call',
                    'not dynamic binding to initialized real provider, hold lifetime or changeset probes']}
        pending=[row for row in pending if row['path'] not in proven]
        report['board_helper_refusals']=dict(status='PASS' if refusals else 'NOT RUN',
            modules=refusals,scope='exact-kernel ABI and wrong-board ENODEV; not hardware activation')
        if not pending:
            checks['module_load']='PASS'
        report['radio_module_tests']=pending
        remaining=[k for k,v in checks.items() if v!='PASS']
        report['reason']='Remaining integrated checks: '+', '.join(remaining) if remaining else 'Complete offline composition proof'
        if not remaining:
            report.update(status='PASS',a01_qualified=True)
    except Blocked as error:
        report['reason']=str(error)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        report.update(status='FAIL',reason=str(error))
    report['duration_seconds']=time.monotonic()-start
    if source!=C.ACCEPTANCE.source_identity() or report['duration_seconds']>contract['deadline_seconds']:
        report.update(status='FAIL',reason='source changed or composition deadline exceeded')
    if report['status']!='PASS':
        report['a01_qualified']=False
    (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return {'FAIL':1,'BLOCKED':77,'PASS':0}[report['status']]


if __name__=='__main__':
    raise SystemExit(main())
