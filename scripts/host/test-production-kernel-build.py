#!/usr/bin/env python3
"""Focused manifest/config contracts; compilation has its own actual result."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('board',REPO/'scripts/host/build-rog5-production-kernel.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
class BoardBuild(unittest.TestCase):
    def test_generated_board_flags_make_labels_available_to_real_overlay(self):
        # Evaluate Linux Makefile.dtbs' per-target expression with GNU make
        # and use the resulting flags in actual dtc/fdtoverlay invocations.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=root/'source';repo=root/'repo';repo.mkdir()
            dt=src/'arch/arm64/boot/dts/qcom';dt.mkdir(parents=True)
            (dt/'Makefile').write_text('# retained kernel rules\n')
            board='sm8350-asus-rog-phone5.dts'
            tree='/dts-v1/; / { target: target-node { status = "disabled"; }; };\n'
            (repo/board).write_text(tree);(repo/'unrelated.dts').write_text(tree)
            targets=B.stage_dt_sources(src,[board,'unrelated.dts'],repo)
            self.assertEqual(targets,['qcom/sm8350-asus-rog-phone5.dtb','qcom/unrelated.dtb'])
            harness=dt/'flags.mk'
            harness.write_text('include Makefile\nDTC_FLAGS += $(DTC_FLAGS_$(target-stem))\n'
                               'all:\n\t@echo $(DTC_FLAGS)\n')
            def flags(stem):
                return subprocess.check_output(['make','-s','-f','flags.mk','target-stem='+stem],
                                               cwd=dt,text=True,timeout=5).split()
            self.assertEqual(flags('unrelated'),[])
            overlay=root/'overlay.dts'
            overlay.write_text('/dts-v1/; /plugin/; &target { test-value = <42>; };\n')
            def compile_dts(path,output,extra):
                subprocess.run(['dtc',*extra,'-I','dts','-O','dtb','-o',str(output),str(path)],
                               check=True,capture_output=True,timeout=5)
            compile_dts(overlay,root/'overlay.dtbo',['-@'])
            compile_dts(dt/board,root/'board.dtb',flags(Path(board).stem))
            command=['fdtoverlay','-i',str(root/'board.dtb'),'-o',str(root/'composed.dtb'),str(root/'overlay.dtbo')]
            subprocess.run(command,check=True,capture_output=True,timeout=5)
            self.assertEqual(subprocess.check_output(['fdtget','-t','u',str(root/'composed.dtb'),'/target-node','test-value'],text=True,timeout=5).strip(),'42')
            # The previous flag omission must fail the same real composition.
            rules=(dt/'Makefile').read_text();self.assertEqual(rules.count(' += -@'),1)
            (dt/'Makefile').write_text(rules.replace(' += -@',' += '))
            compile_dts(dt/board,root/'board.dtb',flags(Path(board).stem))
            result=subprocess.run(command,capture_output=True,text=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertNotEqual(subprocess.run(['fdtget', '-p', str(root/'board.dtb'), '/__symbols__'], capture_output=True, timeout=5).returncode, 0)
    def test_external_binding_cannot_replace_upstream_or_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);src=root/'source';src.mkdir()
            (root/'prototype.yaml').write_text('specific prototype contract\n')
            target='Documentation/devicetree/bindings/input/touchscreen/prototype.yaml'
            binding=[dict(source='prototype.yaml',target=target)]
            B.stage_dt_bindings(src,binding,root)
            self.assertEqual((src/target).read_text(),'specific prototype contract\n')
            with self.assertRaises(FileExistsError): B.stage_dt_bindings(src,binding,root)
            for path in ('/escape.yaml','Documentation/devicetree/bindings/../../escape.yaml','drivers/escape.yaml'):
                with self.assertRaises(ValueError): B.stage_dt_bindings(src,[dict(source='prototype.yaml',target=path)],root)

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
            release.write_text('7.2.7-rog5-production\n')
            header.write_text('#define UTS_RELEASE "7.2.7-rog5-production"\n')
            self.assertEqual(B.compiled_release(objects),'7.2.7-rog5-production')
            header.write_text('#define UTS_RELEASE "7.2.7"\n')
            with self.assertRaises(ValueError):B.compiled_release(objects)
            header.unlink()
            with self.assertRaises(OSError):B.compiled_release(objects)
    def test_release_label_from_output_or_argument(self):
        self.assertEqual(B.release_label(Path('/s/rog5-kernel-7.2.7-build-r111')),'k111')
        self.assertEqual(B.release_label(Path('/s/rog5-kernel-7.2.7-build-r111'),'k111'),'k111')
        self.assertEqual(B.release_label(Path('/w/build/board-production')),'k0')
        self.assertEqual(B.release_label(Path('/w/scratch'),'k7'),'k7')
        for output,label in (('/s/x-build-r111','k112'),('/s/x','k0'),('/s/x','k01'),('/s/x','111'),('/s/x','k12345'),('/s/x','k1\n')):
            with self.subTest(label=label),self.assertRaises(ValueError):B.release_label(Path(output),label)
    def test_policy_release_carries_the_label(self):
        policy=json.loads(B.CONFIG.read_text())
        self.assertNotIn('CONFIG_LOCALVERSION',policy['required'])
        self.assertEqual(policy['required']['CONFIG_LOCALVERSION_AUTO'],'n')
        fragments=''.join((B.REPO/f).read_text() for f in policy['fragments'])
        self.assertNotRegex(fragments,r'(?m)^CONFIG_LOCALVERSION=')
        labelled,localversion=B.labelled_policy(policy,'k111')
        self.assertEqual(localversion,'-rog5-k111')
        self.assertEqual(labelled['required']['CONFIG_LOCALVERSION'],'"-rog5-k111"')
        self.assertNotIn('CONFIG_LOCALVERSION',policy['required'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.config'
            valid=''.join(k+'='+v+'\n' for k,v in labelled['required'].items())
            p.write_text(valid);B.check_config(p,labelled)
            p.write_text(valid.replace('"-rog5-k111"','"-rog5-k110"'))
            with self.assertRaises(ValueError):B.check_config(p,labelled)
        self.assertEqual(B.labelled_release('7.2.7-rog5-k111','-rog5-k111'),'7.2.7-rog5-k111')
        for release in ('7.2.7-rog5-production','7.2.7-rog5-k1111','7.2.7-rog5-k111-dirty','x7.2.7-rog5-k111'):
            with self.subTest(release=release),self.assertRaises(ValueError):B.labelled_release(release,'-rog5-k111')
        pinned=dict(policy,required=dict(policy['required'],CONFIG_LOCALVERSION='"-rog5-production"'))
        with self.assertRaises(ValueError):B.labelled_policy(pinned,'k111')
        legacy={k:v for k,v in pinned.items() if k!='release_localversion'}
        self.assertEqual(B.labelled_policy(legacy,'k111'),(legacy,None))
        self.assertEqual(B.labelled_release('7.2.7-rog5-production',None),'7.2.7-rog5-production')
    def test_changed_or_deleted_frozen_input_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input';source.write_text('original')
            inputs={'input':B.digest(source)}
            self.assertTrue(B.inputs_unchanged(inputs,root))
            source.write_text('changed');self.assertFalse(B.inputs_unchanged(inputs,root))
            source.unlink();self.assertFalse(B.inputs_unchanged(inputs,root))
    def test_all_patches_partition_and_known_diagnostics_stay_out(self):
        groups=B.series()
        production=set(groups['production'])
        self.assertGreaterEqual(len(production),70)
        for number in (1,2,3,35,36,37,40,41,42,43,44,99):
            self.assertTrue(any(x.startswith(f'{number:04d}-') for x in production),number)
        # Carried but out of production (see series.diagnostic for the reasons).
        for number in (74,75,84,85,86,87):
            self.assertTrue(any(x.startswith(f'{number:04d}-') for x in groups['diagnostic']),number)
        self.assertFalse(production&set(groups['diagnostic']))
    def test_defaults_are_the_7_2_7_production_policy(self):
        policy=json.loads(B.CONFIG.read_text())
        self.assertEqual(B.CONFIG,B.REPO/'configs/kernel/rog5-production-build-7.2.7.json')
        self.assertEqual(policy['patch_dir'],'patches/linux-7.2.7')
        self.assertEqual(B.PATCHES,B.REPO/policy['patch_dir'])
        self.assertEqual(B.WARNING_POLICY,B.REPO/policy['warning_policy_file'])
        self.assertEqual(policy['base_commit'],'f42acb3678424d1e08f6ed27c0d8ba8a125e14d6')
        self.assertEqual(B.series(B.REPO/policy['patch_dir']),B.series())
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
        # 7.2.7 production mounts UFS read-write through the stock driver.
        self.assertEqual(policy['required']['CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE'],'n')
        self.assertEqual(policy['required']['CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY'],'n')
if __name__=='__main__':unittest.main()
