#!/usr/bin/env python3
"""Focused manifest/config contracts; compilation has its own actual result."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('board',REPO/'scripts/host/build-rog5-production-kernel.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
class BoardBuild(unittest.TestCase):
    def test_build_environment_drops_inherited_release_and_make_overrides(self):
        env=B.build_environment(Path('/owned'),dict(PATH='/usr/bin',LOCALVERSION='-unexpected',MAKEFLAGS='-e LOCALVERSION=bad',GIT_DIR='/foreign',GIT_INDEX_FILE='/foreign-index',MFLAGS='-e',MAKEOVERRIDES='LOCALVERSION=bad'))
        for key in ('LOCALVERSION','MAKEFLAGS','MFLAGS','MAKEOVERRIDES','GIT_DIR','GIT_INDEX_FILE'):
            self.assertNotIn(key,env)
        self.assertEqual(env['GIT_CEILING_DIRECTORIES'],'/owned')
        self.assertEqual(env['PATH'],'/usr/bin')
    def test_compiled_release_rejects_stale_generated_state(self):
        with tempfile.TemporaryDirectory() as directory:
            objects=Path(directory)
            release=objects/'include/config/kernel.release';release.parent.mkdir(parents=True)
            header=objects/'include/generated/utsrelease.h';header.parent.mkdir(parents=True)
            release.write_text('7.1.4-rog5-production\n')
            header.write_text('#define UTS_RELEASE "7.1.4-rog5-production"\n')
            self.assertEqual(B.compiled_release(objects),'7.1.4-rog5-production')
            header.write_text('#define UTS_RELEASE "7.1.4"\n')
            with self.assertRaises(ValueError):B.compiled_release(objects)
            header.unlink()
            with self.assertRaises(OSError):B.compiled_release(objects)
    def test_changed_or_deleted_frozen_input_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input';source.write_text('original')
            inputs={'input':B.digest(source)}
            self.assertTrue(B.inputs_unchanged(inputs,root))
            source.write_text('changed');self.assertFalse(B.inputs_unchanged(inputs,root))
            source.unlink();self.assertFalse(B.inputs_unchanged(inputs,root))
    def test_all_patches_partition_and_known_diagnostics_stay_out(self):
        groups=B.series()
        self.assertEqual(len(groups['production'])+len(groups['diagnostic']),41)
        self.assertTrue(any(x.startswith('0040-') for x in groups['production']))
        self.assertTrue(any(x.startswith('0041-') for x in groups['production']))
        for number in [4,5,6,7,8,9,10,11,13,14,15,16,17,19,20,21,22,23,24,25,27,28,29,30,31,32]:
            self.assertTrue(any(x.startswith(f'{number:04d}-') for x in groups['diagnostic']))
    def test_missing_duplicate_and_overlap_are_rejected(self):
        for mutation in ('missing','duplicate','overlap','path'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
                p=Path(d);(p/'0001-a.patch').touch();(p/'0002-b.patch').touch()
                (p/'series.production').write_text('0001-a.patch\n')
                (p/'series.diagnostic').write_text('0002-b.patch\n')
                if mutation=='missing':(p/'0003-c.patch').touch()
                elif mutation=='duplicate':(p/'series.production').write_text('0001-a.patch\n0001-a.patch\n')
                elif mutation=='overlap':(p/'series.diagnostic').write_text('0001-a.patch\n0002-b.patch\n')
                else:(p/'series.production').write_text('../0001-a.patch\n')
                with self.assertRaises(ValueError):B.series(p)
    def test_mandatory_and_forbidden_after_olddefconfig(self):
        policy=json.loads(B.CONFIG.read_text())
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.config'; valid=''.join(k+'='+v+'\n' for k,v in policy['required'].items())
            p.write_text(valid);B.check_config(p,policy)
            for key in policy['required']:
                changed='\n'.join(x for x in valid.splitlines() if not x.startswith(key+'='))
                if policy['required'][key]=='n':changed+='\n'+key+'=y\n'
                p.write_text(changed)
                with self.assertRaises(ValueError):B.check_config(p,policy)
            for key in policy['forbidden']:
                p.write_text(valid+key+'=y\n')
                with self.assertRaises(ValueError):B.check_config(p,policy)
    def test_iommu_guard_preserves_private_source_fix(self):
        patch=(B.PATCHES/'0040-drm-msm-adreno-defer-until-iommu-attachment.patch').read_text()
        for token in ('136f75ae869afd47a016b1278fae2110cc6d2229','of_property_present(pdev->dev.of_node, "iommus")','!device_iommu_mapped(&pdev->dev)','-EPROBE_DEFER'):
            self.assertIn(token,patch)
    def test_truthful_scope(self):
        policy=json.loads(B.CONFIG.read_text())
        self.assertEqual(policy['physical_validation'],'NOT RUN')
        self.assertIn('FTS3658U',policy['limitations'][0])
        self.assertIn('arbitrary SCSI',policy['limitations'][1])
        self.assertEqual(policy['required']['CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE'],'y')
if __name__=='__main__':unittest.main()
