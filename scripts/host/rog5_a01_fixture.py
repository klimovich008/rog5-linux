"""Bind an existing local QEMU-only module build to A01's exact kernel.

This consumes the retained build result, not boot authority or a production
provider. It never builds, inserts modules on the host, or modifies artifacts.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import subprocess
import tempfile

SOURCE=Path(__file__).resolve().parents[2]/'tests/fixtures/rog5-a01-s12-shim.c'


class FixtureUnavailable(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signature(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,
            info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def exact_file(path, limit):
    for ancestor in (path,*path.parents):
        if ancestor.is_symlink():raise ValueError('symlink in fixture build input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.geteuid()
                or before.st_nlink!=1 or before.st_mode&0o022 or before.st_size>limit):
            raise ValueError('unsafe fixture build input')
        data=stream.read(limit+1)
        if signature(before)!=signature(os.fstat(stream.fileno())) or len(data)!=before.st_size:
            raise ValueError('fixture build input changed')
    if signature(before)!=signature(path.lstat()):raise ValueError('fixture pathname changed')
    return data


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate fixture build key')
        result[key]=value
    return result


REFERENCE_FORMAT='rog5-a01-fixture-reference-v1'


def require(value, message):
    if not value:raise ValueError(message)


def receipt_references(record):
    refs=record['references']
    require(set(refs)=={'shim','kernel','module','derived','completed'},'fixture receipt inventory')
    loaded={};raws={}
    for role,pin in refs.items():
        require(set(pin)=={'path','sha256'} and Path(pin['path']).is_absolute(),'fixture receipt locator')
        raw=exact_file(Path(pin['path']),2*1024*1024)
        require(digest(raw)==pin['sha256'],'fixture receipt hash: '+role)
        loaded[role]=json.loads(raw,object_pairs_hook=unique);raws[role]=raw
        require(isinstance(loaded[role],dict),'fixture receipt object')
    return loaded,raws


def completed_twins(record, removed=False):
    rows=record.get('stages',[])
    require([r.get('label') for r in rows]==['a','b'],'fixture twin labels')
    for row in rows:
        state=row.get('container_state',{})
        require(row.get('status')=='PASS' and row.get('returncode')==0
                and row.get('cleanup_errors')==[] and state.get('Running') is False
                and state.get('OOMKilled') is False and state.get('ExitCode')==0
                and (not removed or row.get('container_removed') is True),'fixture twin completion')


def reference_inputs(record, kernel_sha256, vermagic):
    require(set(record)=={'format','status','source_commit','kernel_sha256','vermagic',
                         'references','source_path','kit_path'},'fixture reference fields')
    require(record['format']==REFERENCE_FORMAT and record['status']=='REFERENCES_EXISTING_TEST_ONLY_SHIM_TWINS',
            'fixture reference format/status')
    commit=record['source_commit']
    require(isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit)
            and record['kernel_sha256']==kernel_sha256 and record['vermagic']==vermagic
            and isinstance(vermagic,str) and vermagic.split()
            and vermagic.split()[0].endswith('-g'+commit[:12]),'fixture source/kernel identity')
    records,raws=receipt_references(record);refs=record['references']
    shim,kernel,modules,derived,completed=[records[r] for r in ('shim','kernel','module','derived','completed')]
    for row,status,key in ((shim,'PASS_TEST_ONLY_SHIM_TWINS','source'),(kernel,'PASS','source'),
                          (modules,'PASS_RAW_MODULE_TWINS','source'),(derived,'PASS_DERIVED_KIT_BYTES','kernel_source'),
                          (completed,'PASS_COMPLETED_KIT_BYTES','kernel_source')):
        require(row.get('status')==status and row.get(key)==commit,'fixture prerequisite status/source')
    for row in (shim,kernel,modules):completed_twins(row,removed=row is shim)
    require(shim.get('production_module') is False and modules.get('twins_identical') is True,
            'fixture test-only twin scope')
    require(shim['kernel_receipt_sha256']==refs['kernel']['sha256']
            and shim['module_receipt_sha256']==refs['module']['sha256'],'fixture shim provenance')
    for role in ('kernel','derived','completed'):
        require(modules['receipts_sha256'][role]==refs[role]['sha256']
                and modules['receipt_paths'][role]==refs[role]['path'],'fixture module-kit provenance')
    require(derived['source_build_receipt_sha256']==refs['kernel']['sha256'],'fixture derived provenance')
    for role in ('kernel','derived'):
        require(completed['prerequisites_sha256'][refs[role]['path']]==refs[role]['sha256'],
                'fixture completed-kit provenance')
    require(kernel['artifacts']['arch/arm64/boot/Image']==kernel_sha256,'fixture kernel Image receipt')
    require(shim['release']==derived['release']==completed['release']==vermagic.split()[0],
            'fixture prerequisite release')
    source_path=Path(record['source_path']);kit=Path(record['kit_path'])
    require(source_path.is_absolute() and kit.is_absolute(),'fixture source/kit paths')
    source=exact_file(source_path,65536)
    require(source==exact_file(SOURCE,65536) and shim['inputs_sha256'][str(source_path)]==digest(source),
            'fixture source changed since build')
    module=None
    for side,row in zip(('a','b'),shim['stages']):
        base=Path(refs['shim']['path']).parent/side
        require(str(kit)+':/kit:ro' in row['command'] and str(base)+':/out:rw' in row['command'],
                'fixture original build paths')
        candidate=exact_file(base/'module/rog5_a01_s12_shim.ko',8*1024*1024)
        require(len(candidate)==row['size']==shim['size'] and digest(candidate)==row['sha256']==shim['sha256']
                and (module is None or candidate==module),'fixture exact module twins')
        module=candidate
    require(module[:6]==b'\x7fELF\x02\x01' and module[16:20]==b'\x01\x00\xb7\x00','fixture module ELF')
    hashes={}
    for name in ('.config','Module.symvers','vmlinux'):
        expected=kernel['artifacts'][name]
        require(derived['kit_file_sha256'][name]==completed['complete_inventory'][name]['sha256']==expected,
                'fixture exact kit byte provenance')
        hashes[name]=expected
    return module,source,kit,hashes,raws


def verified_copy(source, destination, expected, limit):
    """Bounded snapshot for objcopy; do not buffer an entire debug vmlinux."""
    for ancestor in (source,*source.parents):
        require(not ancestor.is_symlink(),'symlink in fixture kit')
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream,destination.open('xb') as output:
        before=os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid==os.geteuid()
                and before.st_nlink==1 and not before.st_mode&0o022
                and 0<before.st_size<=limit,'unsafe fixture kit input')
        h=hashlib.sha256();left=before.st_size
        while left:
            chunk=stream.read(min(left,1024*1024));require(chunk,'short fixture kit')
            left-=len(chunk);h.update(chunk);output.write(chunk)
        require(not stream.read(1) and signature(os.fstat(stream.fileno()))==signature(before)
                and signature(source.lstat())==signature(before),'fixture kit changed')
        require(h.hexdigest()==expected,'fixture kit hash mismatch')


def load_reference_fixture(directory, raw, record, kernel_sha256, vermagic):
    module,source,kit,hashes,raws=reference_inputs(record,kernel_sha256,vermagic)
    for name,limit in (('.config',1024*1024),('Module.symvers',8*1024*1024)):
        data=exact_file(kit/name,limit)
        require(digest(data)==hashes[name],'fixture kit hash mismatch: '+name)
        if name=='.config':
            require(data.splitlines().count(b'CONFIG_DEBUG_INFO_BTF_MODULES=y')==1
                    and data.splitlines().count(b'# CONFIG_MODULE_ALLOW_BTF_MISMATCH is not set')==1,
                    'fixture kernel must enforce module BTF')
    with tempfile.TemporaryDirectory(prefix='rog5-a01-fixture-reference-',dir=directory) as temp:
        root=Path(temp);elf=root/'vmlinux';image=root/'Image';ko=root/'fixture.ko'
        verified_copy(kit/'vmlinux',elf,hashes['vmlinux'],512*1024*1024);ko.write_bytes(module)
        subprocess.run(['llvm-objcopy','-O','binary','-R','.note','-R','.note.gnu.build-id',
                        '-R','.comment','-S',str(elf),str(image)],check=True,capture_output=True,timeout=10,
                       preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024*1024,256*1024*1024)))
        require(digest(exact_file(image,256*1024*1024))==kernel_sha256,
                'fixture vmlinux does not produce accepted kernel')
        for name,value in (('vermagic',vermagic),('name','rog5_a01_s12_shim'),('depends','')):
            require(subprocess.check_output(['modinfo','-F',name,str(ko)],text=True,timeout=5).strip()==value,
                    'fixture module metadata mismatch: '+name)
    for role,old in raws.items():
        require(exact_file(Path(record['references'][role]['path']),2*1024*1024)==old,'fixture prerequisite changed')
    require(exact_file(directory/'result.json',16384)==raw,'fixture reference changed')
    return module,dict(status='PASS',format=REFERENCE_FORMAT,source_commit=record['source_commit'],
        kernel_sha256=kernel_sha256,module_sha256=digest(module),fixture_source_sha256=digest(source),
        build_result_sha256=digest(raw),kit_hashes=hashes,
        reference_receipts_sha256={role:digest(value) for role,value in raws.items()},
        production_provider=False,scope='retained test-only twins; exact vmlinux-to-Image binding; not signed phone content')


def load_fixture(directory, kernel_sha256, vermagic):
    if directory is None:raise FixtureUnavailable('supply existing --activation-fixture-build for exact consumer BTF/refusal')
    if directory.is_absolute() and not directory.exists() and not directory.is_symlink():
        raise FixtureUnavailable('missing exact-kernel QEMU-only fixture build')
    if not directory.is_absolute() or not directory.is_dir():
        raise ValueError('fixture build directory must be absolute and present')
    if any(not shutil.which(x) for x in ('llvm-objcopy','modinfo')):
        raise FixtureUnavailable('fixture binding requires llvm-objcopy and modinfo')
    raw=exact_file(directory/'result.json',16384)
    record=json.loads(raw,object_pairs_hook=unique)
    if isinstance(record,dict) and record.get('format')==REFERENCE_FORMAT:
        try:return load_reference_fixture(directory,raw,record,kernel_sha256,vermagic)
        except (KeyError,TypeError,IndexError,AttributeError) as error:
            raise ValueError('malformed fixture reference evidence') from error
    if not isinstance(record,dict) or not isinstance(record.get('kit_hashes'),dict):
        raise ValueError('invalid fixture build record')
    commit=record.get('source_commit','')
    if (record.get('status')!='PASS' or not isinstance(commit,str)
            or not re.fullmatch('[0-9a-f]{40}',commit)
            or record.get('vermagic')!=vermagic
            or not isinstance(vermagic,str) or not vermagic.split()
            or not vermagic.split()[0].endswith('-g'+commit[:12])):
        raise ValueError('fixture source/kernel build identity mismatch')
    source=exact_file(directory/'module/rog5_a01_s12_shim.c',65536)
    if source!=SOURCE.read_bytes() or digest(source)!=record.get('fixture_source_sha256'):
        raise ValueError('fixture source changed since build')
    module=exact_file(directory/'module/rog5_a01_s12_shim.ko',8*1024*1024)
    if (digest(module)!=record.get('module_sha256') or module[:6]!=b'\x7fELF\x02\x01'
            or module[16:20]!=b'\x01\x00\xb7\x00'):
        raise ValueError('fixture module identity mismatch')
    for name,limit in (('.config',1024*1024),('Module.symvers',8*1024*1024),('vmlinux',512*1024*1024)):
        data=exact_file(directory/'clean-b'/name,limit)
        if digest(data)!=record.get('kit_hashes',{}).get(name):
            raise ValueError('fixture kit hash mismatch: '+name)
        if name=='.config':
            lines=data.splitlines()
            if (lines.count(b'CONFIG_DEBUG_INFO_BTF_MODULES=y')!=1
                    or lines.count(b'# CONFIG_MODULE_ALLOW_BTF_MISMATCH is not set')!=1):
                raise ValueError('fixture kernel must enforce module BTF')
        if name=='vmlinux':vmlinux=data
    # The accepted arm64 boot Makefile produces Image with these exact flags.
    # Compare actual bytes, not the short release suffix or a copied Image hash.
    with tempfile.TemporaryDirectory(prefix='rog5-a01-fixture-binding-') as temp:
        root=Path(temp);elf=root/'vmlinux';elf.write_bytes(vmlinux)
        image=root/'Image';ko=root/'fixture.ko';ko.write_bytes(module)
        subprocess.run(['llvm-objcopy','-O','binary','-R','.note','-R','.note.gnu.build-id',
                        '-R','.comment','-S',str(elf),str(image)],check=True,capture_output=True,timeout=10,
                       preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024*1024,256*1024*1024)))
        if digest(image.read_bytes())!=kernel_sha256:
            raise ValueError('fixture vmlinux does not produce accepted kernel')
        for name,value in (('vermagic',vermagic),('name','rog5_a01_s12_shim'),('depends','')):
            actual=subprocess.check_output(['modinfo','-F',name,str(ko)],text=True,timeout=5).strip()
            if actual!=value:raise ValueError('fixture module metadata mismatch: '+name)
    if exact_file(directory/'result.json',16384)!=raw:
        raise ValueError('fixture build result changed')
    return module,dict(status='PASS',source_commit=commit,kernel_sha256=kernel_sha256,
        module_sha256=digest(module),fixture_source_sha256=digest(source),
        build_result_sha256=digest(raw),kit_hashes=record['kit_hashes'],
        production_provider=False,scope='local test build; exact vmlinux-to-Image binding; not signed phone content')
