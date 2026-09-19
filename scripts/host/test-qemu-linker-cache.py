#!/usr/bin/env python3
"""Semantic cache admission tests; target tool execution is a separate manual test."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('cache', Path(__file__).with_name('prepare-qemu-linker-cache.py'))
CACHE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(CACHE)


class Admission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.runtime = self.root/'runtime'; self.view = self.root/'view'
        self.runtime.mkdir(); self.view.mkdir(); self.out = self.root/'cache'; self.out.mkdir()
        rows = []
        for name, kind, data in [('etc', 'directory', None), ('usr', 'directory', None),
                                 ('usr/lib', 'directory', None), ('usr/lib/liba.so', 'file', b'actual bytes'),
                                 ('usr/lib/liba.so.1', 'symlink', 'liba.so'), ('etc/ld.so.conf', 'file', b'/usr/lib\n')]:
            a, b = self.runtime/name, self.view/name
            if kind == 'directory':
                a.mkdir(); b.mkdir()
            elif kind == 'file':
                a.write_bytes(data); os.link(a,b)
            else:
                a.symlink_to(data); b.write_text(data)
            row = dict(path=name,type=kind,mode=stat.S_IMODE(a.lstat().st_mode))
            if kind == 'file': row.update(size=len(data),sha256=CACHE.digest(a))
            if kind == 'symlink': row['target']=data
            rows.append(row)
            meta=b.parent/'.virtfs_metadata'/b.name;meta.parent.mkdir(exist_ok=True)
            mode = {'directory':stat.S_IFDIR|0o755,'file':stat.S_IFREG|0o644,'symlink':stat.S_IFLNK|0o777}[kind]
            meta.write_text(f'virtfs.uid=0\nvirtfs.gid=0\nvirtfs.mode={mode}\nvirtfs.rdev=0\n')
        (self.view/'.virtfs_metadata_root').write_text('virtfs.uid=0\nvirtfs.gid=0\nvirtfs.mode=16877\nvirtfs.rdev=0\n')
        self.tree = self.root/'tree.json'; self.write(self.tree, rows)
        self.material = self.root/'material.json'; self.write(self.material,dict(status='PASS',installation_scripts_executed=False,archive_audit=dict(status='PASS'),tree_manifest_sha256=CACHE.digest(self.tree)))
        self.receipt = self.root/'view.json'; self.write(self.receipt,dict(status='PASS_VIEW_PREPARED',security_model='mapped-file',readonly_required=True,source_tree_sha256=CACHE.digest(self.tree),receipt_sha256=CACHE.digest(self.material),runtime=str(self.runtime),root=str(self.view)))
        cache=self.out/'ld.so.cache';cache.write_bytes(b'glibc-ld.so.cache1.1'+bytes(64))
        log=self.out/'consumer.log';log.write_text('search cache=/etc/ld.so.cache\n')
        self.record=dict(status='PASS_TARGET_CACHE_PREPARED',authority='none',preparer_sha256=CACHE.digest(Path(CACHE.__file__)),runtime=str(self.runtime),view=str(self.view),view_metadata_sha256=CACHE.verify_tree(self.runtime,self.tree,self.view),tree=CACHE.identity(self.tree),materialization=CACHE.identity(self.material),view_receipt=CACHE.identity(self.receipt),cache=CACHE.identity(cache),consumers={app:dict(cache_searches=1,log=CACHE.identity(log)) for app in ('mousepad','foot')})
        self.write(self.out/'result.json',self.record)

    def write(self,p,x):p.write_text(json.dumps(x))
    def validate(self):return CACHE.validate(self.out,self.view,self.receipt)
    def refuses(self):
        with self.assertRaises((ValueError,FileNotFoundError)):self.validate()

    def test_matching_tree_and_actual_stage(self):
        dest=self.root/'stage';dest.mkdir();CACHE.stage(self.out,self.view,self.receipt,dest)
        self.assertEqual((dest/'linker-cache').read_bytes(),(self.out/'ld.so.cache').read_bytes())
        self.assertEqual((dest/'linker-cache.sha256').read_text(),self.record['cache']['sha256']+'\n')
        self.assertFalse((self.runtime/'etc/ld.so.cache').exists())
        self.assertFalse((self.view/'etc/ld.so.cache').exists())
        with self.assertRaises(FileExistsError):CACHE.stage(self.out,self.view,self.receipt,dest)

    def test_changed_runtime_bytes(self):
        (self.runtime/'usr/lib/liba.so').write_bytes(b'altered bytes');self.refuses()
    def test_changed_link_target(self):
        (self.runtime/'usr/lib/liba.so.1').unlink();(self.runtime/'usr/lib/liba.so.1').symlink_to('elsewhere');self.refuses()
    def test_changed_view_link_description(self):
        (self.view/'usr/lib/liba.so.1').write_text('elsewhere');self.refuses()
    def test_changed_view_metadata(self):
        (self.view/'usr/lib/.virtfs_metadata/liba.so.1').write_text('virtfs.uid=0\nvirtfs.gid=0\nvirtfs.mode=33188\nvirtfs.rdev=0\n');self.refuses()
    def test_changed_guest_executable_permissions(self):
        p=self.view/'usr/lib/.virtfs_metadata/liba.so'
        p.write_text(p.read_text().replace('33188','33261'));self.refuses()
    def test_oversized_encoded_symlink_refuses_before_read(self):
        p=self.view/'usr/lib/liba.so.1'
        with p.open('wb') as stream: stream.truncate(2*1024**2)
        self.refuses()
    def test_added_configuration(self):
        (self.runtime/'etc/unlisted.conf').write_text('/elsewhere');self.refuses()
    def test_missing_runtime_member(self):
        (self.view/'etc/ld.so.conf').unlink();self.refuses()
    def test_truncated_cache(self):
        (self.out/'ld.so.cache').write_bytes(b'glibc-ld.so.cache1.1');self.refuses()
    def test_mutated_cache(self):
        (self.out/'ld.so.cache').write_bytes(b'glibc-ld.so.cache1.1'+b'a'*64);self.refuses()
    def test_symlink_cache(self):
        p=self.out/'ld.so.cache';p.rename(self.out/'elsewhere');p.symlink_to('elsewhere');self.refuses()
    def test_different_view_receipt(self):
        self.receipt.write_text(self.receipt.read_text()+'\n');self.refuses()
    def test_different_preparer(self):
        self.record['preparer_sha256']='0'*64;self.write(self.out/'result.json',self.record);self.refuses()
    def test_changed_consumer_log(self):
        (self.out/'consumer.log').write_text('not found');self.refuses()
    def test_encoded_view_cannot_replace_original(self):
        with self.assertRaises(ValueError):CACHE.verify_tree(self.view,self.tree,self.runtime)
    def test_actual_runner_loads_same_admission_and_boot_calls_after_ram_bind(self):
        spec=importlib.util.spec_from_file_location('runner',Path(__file__).with_name('test-qemu-logind.py'))
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        dest=self.root/'stage';dest.mkdir()
        runner.linker_cache_module().stage(self.out,self.view,self.receipt,dest)
        self.assertEqual(CACHE.digest(dest/'linker-cache'),self.record['cache']['sha256'])
        boot=(Path(__file__).resolve().parents[2]/'tools/qemu-virtio-drm/logind-boot.sh').read_text()
        self.assertLess(boot.index('mount --bind /run/fixture-etc /etc'),boot.index('prepare_linker_cache'))
        self.assertLess(boot.index('prepare_linker_cache'),boot.index('exec /usr/lib/systemd/systemd'))

    def test_unsafe_names(self):
        for name in ('../escape','/absolute','usr//lib','usr/./lib','.virtfs_metadata/x'):
            with self.subTest(name=name),self.assertRaises(ValueError):CACHE.safe_name(name)


if __name__=='__main__':unittest.main()
