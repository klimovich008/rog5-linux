#!/usr/bin/env python3
"""Executable checks of the board gate's actual log/metadata validators."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('diagnostics',HERE/'check-production-build-diagnostics.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

class Diagnostics(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source';self.objects=self.root/'objects'
        self.source.mkdir();self.objects.mkdir()
        (self.source/'table.c').write_text('default range followed by designated overrides\n')
        (self.objects/'table.h').write_text('exact generated entries\n')
        self.policy={'initializer_overrides':[{'root':'objects','path':'table.h','sha256':checker.sha(self.objects/'table.h'),'maximum_count':2,'dependencies':[{'root':'source','path':'table.c','sha256':checker.sha(self.source/'table.c')}]}]}
        self.warning=str(self.objects/'table.h')+':1:2: '+checker.INITIALIZER
    def check(self,text,stage='kernel-build'):
        return checker.diagnostics(text,stage,self.source,self.objects,self.policy)
    def test_depmod_diagnostics_do_not_depend_on_exit_status(self):
        for message in ('depmod: WARNING: module foo needs unknown symbol bar','unexpected output'):
            with self.subTest(message=message):self.assertFalse(self.check(message,'depmod')[0]['allowed'])
        self.assertEqual(self.check('\n','depmod'),[])
    def test_zero_exit_schema_diagnostics_fail(self):
        for message in ('/build/board.dtb: panel: unevaluated property','board.dtbo: node: missing required property','panel.yaml: required property missing'):
            with self.subTest(message=message):self.assertEqual(self.check(message,'dtbs-check')[0]['allowed'],False)
    def test_only_exact_pinned_initializer_is_allowed(self):
        self.assertTrue(self.check(self.warning)[0]['allowed'])
        self.assertFalse(self.check(self.warning.replace('table.h','other.h'))[0]['allowed'])
        self.assertFalse(self.check(self.warning.replace('initializer overrides','unexpected initializer overrides'))[0]['allowed'])
        (self.objects/'table.h').write_text('different bytes')
        self.assertFalse(self.check(self.warning)[0]['allowed'])
    def test_dependency_identity_and_count_are_required(self):
        self.assertEqual([x['allowed'] for x in self.check('\n'.join([self.warning]*3))],[True,True,False])
        (self.source/'table.c').write_text('different initializer semantics')
        self.assertFalse(self.check(self.warning)[0]['allowed'])
    def test_unrelated_missing_pin_does_not_mask_diagnostics(self):
        self.policy['initializer_overrides'].insert(0,{'root':'objects','path':'absent.h'})
        self.assertTrue(self.check(self.warning)[0]['allowed'])
    def test_clean_build_progress_is_not_a_diagnostic(self):
        self.assertEqual(self.check('  CC [M] drivers/gpu/panel.o\n  MODPOST Module.symvers\n  CC net/9p/error.o\n1 warning generated.\n'),[])
    def reviewed(self):
        (self.objects/'.config').write_text('CONFIG_ARM64=y\n# CONFIG_DEBUG_LABEL is not set\n')
        (self.source/'support.h').write_text('reviewed type definition\n')
        message="table.c:12:3: warning: variable 'label' set but not used [-Wunused-but-set-variable]"
        self.policy['reviewed_messages']=[{'path':'table.c','sha256':checker.sha(self.source/'table.c'),'messages':{message:1},'config_guards':{'CONFIG_ARM64':'y','CONFIG_DEBUG_LABEL':'n'},'dependencies':[{'path':'support.h','sha256':checker.sha(self.source/'support.h')}]}]
        return str(self.source)+'/'+message
    def test_reviewed_site_message_ceiling_and_config_guards(self):
        message=self.reviewed()
        self.assertEqual([x['allowed'] for x in self.check(message+'\n'+message)],[True,False])
        self.assertFalse(self.check(message.replace(':12:3:',':13:3:'))[0]['allowed'])
        self.assertFalse(self.check(message.replace("'label'","'packet'"))[0]['allowed'])
        (self.objects/'.config').write_text('CONFIG_ARM64=y\nCONFIG_DEBUG_LABEL=y\n')
        self.assertFalse(self.check(message)[0]['allowed'])
    def test_changed_reviewed_source_or_supporting_header_rejected(self):
        for name in ('table.c','support.h'):
            with self.subTest(name=name):
                message=self.reviewed();before=(self.source/name).read_text()
                (self.source/name).write_text('new semantics')
                self.assertFalse(self.check(message)[0]['allowed'])
                (self.source/name).write_text(before)
    def test_schema_error_cannot_be_allowed_as_reviewed_warning(self):
        self.reviewed();self.policy['reviewed_messages'][0]['messages']={'board.dtb: missing required property':1}
        self.assertFalse(self.check('board.dtb: missing required property','dtbs-check')[0]['allowed'])
    def test_generated_table_site_and_occurrence_are_pinned(self):
        self.policy['initializer_overrides'][0]['sites']={'1:2':1}
        self.assertTrue(self.check(self.warning)[0]['allowed'])
        self.assertFalse(self.check(self.warning.replace(':1:2:',':2:2:'))[0]['allowed'])
        self.assertEqual([x['allowed'] for x in self.check(self.warning+'\n'+self.warning)],[True,False])

class ModuleClosure(unittest.TestCase):
    def setUp(self):
        self.entries=[{'name':name,'path':'modules/lib/modules/7.1.4/kernel/'+name+'.ko','depends':deps,'vermagic':'7.1.4 SMP preempt mod_unload aarch64'} for name,deps in [('panel','drm,backlight'),('drm','')]]
        self.builtin='kernel/backlight.ko\n';self.dep='kernel/panel.ko: kernel/drm.ko\nkernel/drm.ko:\n'
    def check(self):return checker.module_closure(self.entries,self.builtin,self.dep,'7.1.4')
    def test_clean_dependency_closure(self):self.assertEqual(self.check(),[])
    def test_kmod_hyphen_and_underscore_names_are_equivalent(self):
        self.entries[0]['depends']='gpu-sched,backlight'
        self.entries[1]['name']='gpu_sched'
        self.assertEqual(self.check(),[])
        self.entries[0]['depends']='gpu-other,backlight'
        self.assertTrue(self.check())
    def test_missing_declared_dependency(self):
        self.entries[0]['depends']+=',missing';self.assertTrue(any('missing dependencies' in x for x in self.check()))
    def test_depmod_omission_and_unknown_paths(self):
        for dep in ('kernel/panel.ko:\nkernel/drm.ko:\n','kernel/panel.ko: kernel/absent.ko\nkernel/drm.ko:\n','kernel/drm.ko:\n'):
            with self.subTest(dep=dep):self.dep=dep;self.assertTrue(self.check())
    def test_vermagic_duplicate_and_malformed_metadata(self):
        for magic in ('','6.1.0 SMP'):
            self.entries[0]['vermagic']=magic;self.assertTrue(self.check())
        self.entries[0]['vermagic']='7.1.4 SMP';self.entries.append(copy.deepcopy(self.entries[0]));self.assertTrue(self.check())
        self.entries.pop();self.dep='missing colon';self.assertTrue(self.check())
    def test_closed_dependency_cycle_is_rejected(self):
        self.entries[1]['depends']='panel'
        self.dep='kernel/panel.ko: kernel/drm.ko\nkernel/drm.ko: kernel/panel.ko\n'
        self.assertIn('modules.dep cycle or unresolved dependency',self.check())

class EvidenceBinding(unittest.TestCase):
    def test_changed_zero_exit_log_is_not_requalified(self):
        with tempfile.TemporaryDirectory() as directory:
            build=Path(directory);(build/'source').mkdir();(build/'objects').mkdir()
            modules=build/'modules/lib/modules/7.1.4';modules.mkdir(parents=True)
            (modules/'modules.builtin').write_text('');(modules/'modules.dep').write_text('')
            provenance=build/'module-provenance.json';provenance.write_text('[]')
            raw={'linux_base':json.loads(checker.POLICY.read_text())['base_commit'],'release':'7.1.4','stages':{},'outputs':{'module-provenance.json':checker.sha(provenance)}}
            for stage in ('kernel-build','modules-install','depmod','dtbs-check'):
                log=build/(stage+'.log');log.write_text('')
                raw['stages'][stage]={'status':'PASS','log_sha256':checker.sha(log)}
            (build/'result.json').write_text(json.dumps(raw))
            cmd=[sys.executable,str(HERE/'check-production-build-diagnostics.py'),'--build',str(build),'--output']
            subprocess.run(cmd+[str(build/'clean.json')],check=True,capture_output=True)
            (build/'depmod.log').write_text('depmod: WARNING: unknown symbol\n')
            failed=subprocess.run(cmd+[str(build/'changed.json')],capture_output=True)
            self.assertNotEqual(failed.returncode,0)
            errors=json.loads((build/'changed.json').read_text())['errors']
            self.assertIn('recorded log changed depmod.log',errors)
            self.assertIn('unreviewed diagnostic output',errors)

if __name__=='__main__':unittest.main()
