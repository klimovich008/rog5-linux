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
