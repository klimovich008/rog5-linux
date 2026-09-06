#!/usr/bin/env python3
"""Offline acceptance bookkeeping regressions; no device or shared state."""
import copy
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name('release-acceptance.py')
SPEC = importlib.util.spec_from_file_location('acceptance', SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class AcceptanceTest(unittest.TestCase):
    def test_overlay_recovery_is_discoverable_without_starting_qemu(self):
        result = subprocess.run([str(M.REPO/'scripts/host/rog5-dev'),
                                 'check-overlay-recovery', '--help'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in ('--kernel', '--target-archive', '--root-image', '--output'):
            self.assertIn(option, result.stdout)

    def test_retained_root_binding_reaches_runner_without_source_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            test = copy.deepcopy(self.contract['tests'][1])
            test['commands'] = [[sys.executable, '-c',
                                'import sys; print(sys.argv[1])', '{rootfs}']]
            release = dict(artifact_paths=dict(kernel='/kernel', initramfs='/archive',
                                              rootfs='/exact-retained-root'))
            row = M.run_one(test, Path(tmp), release)
            self.assertEqual(row['status'], 'PASS', row)
            self.assertEqual((Path(tmp)/'A02.log').read_text().strip(), '/exact-retained-root')

    def test_artifact_arguments_are_not_rehashed_as_repository_test_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root/'root.ext4'
            artifact.write_bytes(b'already bound by the verified artifact receipt')
            test = copy.deepcopy(self.contract['tests'][1])
            test['commands'] = [[sys.executable, '-c', 'pass', str(artifact)]]
            original = M.sha_file
            def source_hash(path):
                self.assertNotEqual(path, artifact, 'duplicate artifact hash consumed test deadline')
                return original(path)
            with mock.patch.object(M, 'sha_file', side_effect=source_hash):
                row = M.run_one(test, root)
            self.assertEqual(row['status'], 'PASS')
            self.assertNotIn(str(artifact), row['test_versions'])

    def test_overlay_missing_runtime_is_blocked_without_launching_commands(self):
        spec = importlib.util.spec_from_file_location(
            'overlay_test', SOURCE.with_name('test-qemu-overlay-recovery.py'))
        overlay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(overlay)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root/'input'
            artifact.write_bytes(b'not executed')
            argv = ['overlay', '--kernel', str(artifact), '--target-archive', str(artifact),
                    '--root-image', str(artifact), '--output', str(root/'result')]
            previous_umask = os.umask(0o022)
            try:
                with mock.patch.object(sys, 'argv', argv), \
                        mock.patch.object(overlay.shutil, 'which', return_value=None), \
                        mock.patch.object(overlay.subprocess, 'run') as run, \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(overlay.main(), 77)
                    run.assert_not_called()
            finally:
                os.umask(previous_umask)
            self.assertEqual(json.loads((root/'result/result.json').read_text())['status'], 'BLOCKED')

    def test_f01_executes_exact_receipt_and_preserves_deadline(self):
        test = next(row for row in self.contract['tests'] if row['id'] == 'F01')
        self.assertEqual(test['commands'], [['python3', 'scripts/host/test-qemu-overlay-recovery.py',
            '--kernel', '{kernel}', '--target-archive', '{initramfs}',
            '--root-image', '{rootfs}', '--output', '{test_output}']])
        self.assertEqual(test['deadline_seconds'], 240)

    def test_wifi_restart_component_is_discoverable_without_starting_units(self):
        result = subprocess.run([str(M.REPO/'scripts/host/rog5-dev'),
                                 'check-wifi-restart', '--help'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output', result.stdout)

    def test_keyring_ordering_component_is_discoverable_without_starting_units(self):
        result = subprocess.run([str(M.REPO/'scripts/host/rog5-dev'),
                                 'check-package-keyring', '--help'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output', result.stdout)

    def test_ssh_rollback_component_is_discoverable_without_running_units(self):
        result = subprocess.run([str(M.REPO/'scripts/host/rog5-dev'),
                                 'check-ssh-rollback', '--help'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--target-archive', result.stdout)
        self.assertIn('--output', result.stdout)

    def setUp(self):
        self.contract = M.load_contract()

    def test_manifest_has_complete_unique_contract_and_no_optional_display_goal(self):
        M.validate_contract(self.contract)
        self.assertEqual(len({x['id'] for x in self.contract['tests']}), 25)
        self.assertIn('display is optional', self.contract['objective'])

    def test_broader_modes_keep_narrow_coverage(self):
        selected = lambda tier: {x['id'] for x in M.select(self.contract, tier)}
        self.assertLess(selected('quick'), selected('offline'))
        self.assertLess(selected('offline'), selected('release'))
        self.assertLess(selected('device-smoke'), selected('release'))

    def test_missing_skipped_or_failed_required_is_not_completion(self):
        rows = [{'status': 'PASS', 'mandatory': True}]
        self.assertTrue(M.all_pass(rows))
        self.assertFalse(M.all_pass([]))
        for status in ('FAIL', 'BLOCKED', 'NOT RUN'):
            self.assertFalse(M.all_pass(rows + [{'status': status, 'mandatory': True}]))

    def test_duplicate_id_unknown_status_and_nonpositive_deadline_rejected(self):
        for mutation in ('duplicate', 'status', 'deadline'):
            contract = copy.deepcopy(self.contract)
            if mutation == 'duplicate':
                contract['tests'].append(contract['tests'][0])
            elif mutation == 'status':
                contract['statuses'].append('SKIP')
            else:
                contract['tests'][0]['deadline_seconds'] = 0
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                M.validate_contract(contract)

    def test_unimplemented_runner_is_blocked_not_a_simulated_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = M.run_one(self.contract['tests'][0], Path(tmp))
            self.assertEqual(row['status'], 'BLOCKED')
            self.assertEqual(row['duration_seconds'], 0)

    def test_a01_exit_zero_without_complete_proof_is_not_success(self):
        test = copy.deepcopy(self.contract['tests'][0])
        test['commands'] = [[sys.executable, '-c', 'print("component PASS")']]
        with tempfile.TemporaryDirectory() as tmp:
            row = M.run_one(test, Path(tmp))
            self.assertEqual(row['status'], 'FAIL')

    def test_a01_has_an_executable_exact_input_command(self):
        test = self.contract['tests'][0]
        self.assertEqual(test['id'], 'A01')
        self.assertTrue(test['commands'])
        for argument in ('{kernel}', '{dtb}', '{initramfs}', '{rootfs}', '{boot_bundle}', '{candidate}'):
            self.assertIn(argument, test['commands'][0])

    def test_a01_fixture_argument_is_explicit_and_not_execution_authority(self):
        test=copy.deepcopy(self.contract['tests'][0])
        original=copy.deepcopy(test['commands'])
        test['commands']=[[sys.executable,'-c','import sys; print(sys.argv); raise SystemExit(77)']]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            row=M.run_one(test,root,activation_fixture_build=Path('relative'))
            self.assertEqual(row['status'],'BLOCKED');self.assertEqual(row['duration_seconds'],0)
            row=M.run_one(test,root,activation_fixture_build=root)
            self.assertEqual(row['status'],'BLOCKED')
            self.assertIn('--activation-fixture-build',(root/'A01.log').read_text())
        self.assertEqual(self.contract['tests'][0]['commands'],original)

    def test_a01_rejects_partial_or_wrong_release_proof(self):
        test = copy.deepcopy(self.contract['tests'][0])
        test['commands'] = [[sys.executable, '-c', 'pass']]
        release = dict(candidate_id='fixture', artifacts={k:dict(sha256='a'*64) for k in M.ARTIFACT_ROLES})
        proof = dict(status='PASS', a01_qualified=True, source=M.source_identity(), candidate='fixture',
                     duration_seconds=1, runner_sha256=M.sha_file(M.REPO/'scripts/host/check-release-composition.py'),
                     checks=dict.fromkeys(test['required_checks'],'PASS'),
                     artifact_hashes=dict.fromkeys(M.ARTIFACT_ROLES,'a'*64))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'A01').mkdir()
            for mutation in ('none','partial','missing-root','wrong-source','false','wrong-hash','late'):
                changed=copy.deepcopy(proof)
                if mutation=='partial': changed['checks']['root_runtime']='NOT RUN'
                if mutation=='missing-root': del changed['artifact_hashes']['rootfs']
                if mutation=='wrong-source': changed['source']['revision']='0'*40
                if mutation=='false': changed['a01_qualified']=False
                if mutation=='wrong-hash': changed['artifact_hashes']['kernel']='b'*64
                if mutation=='late': changed['duration_seconds']=121
                (root/'A01/result.json').write_text(json.dumps(changed))
                with self.subTest(mutation=mutation):
                    row=M.run_one(test,root,release)
                    self.assertEqual(row['status'],'PASS' if mutation=='none' else 'FAIL',row)

    def test_deadline_nonzero_and_missing_executable_are_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            test = copy.deepcopy(self.contract['tests'][1])
            test['deadline_seconds'] = 0.1
            for command, expected in (([sys.executable, '-c', 'import time; time.sleep(10)'], 'FAIL'),
                                      ([sys.executable, '-c', 'raise SystemExit(3)'], 'FAIL'),
                                      ([sys.executable, '-c', 'raise SystemExit(77)'], 'BLOCKED'),
                                      (['rog5-no-such-command'], 'BLOCKED')):
                test['commands'] = [command]
                result = M.run_one(test, Path(tmp))
                self.assertEqual(result['status'], expected)

    def test_release_receipt_requires_every_artifact_and_correct_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root/'artifact'
            artifact.write_bytes(b'exact test artifact')
            record = {'format': 'rog5-release-inputs-v1', 'candidate_id': 'test-only',
                      'source_revision': 'a'*40,
                      'artifacts': {role: {'path': str(artifact), 'sha256': M.sha_file(artifact),
                                          'size': artifact.stat().st_size}
                                    for role in M.ARTIFACT_ROLES}}
            receipt = root/'receipt.json'
            receipt.write_text(json.dumps(record))
            good = M.verify_release(receipt)
            artifact.write_bytes(b'altered')
            with self.assertRaises(ValueError):
                M.verify_release(receipt)
            record['artifacts'].pop('initramfs')
            receipt.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                M.verify_release(receipt)
            self.assertEqual(good['candidate_id'], 'test-only')

    def test_dirty_source_changes_identity_even_when_head_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=test',
                            '-c', 'user.email=test@example.invalid', 'commit',
                            '--allow-empty', '-qm', 'fixture'], check=True)
            before = M.source_identity(root)
            (root/'untracked.py').write_text('one')
            after = M.source_identity(root)
            self.assertEqual(before['revision'], after['revision'])
            self.assertNotEqual(before['worktree_digest'], after['worktree_digest'])
            self.assertFalse(after['clean'])

    def test_no_cross_run_import_or_automatic_evidence_reuse(self):
        help_text = subprocess.run([sys.executable, str(SOURCE), '--help'],
                                   check=True, capture_output=True, text=True).stdout
        self.assertNotIn('--import', help_text)
        self.assertNotIn('--reuse', help_text)

    def test_successful_command_with_skipped_behavior_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            test = copy.deepcopy(self.contract['tests'][1])
            test['commands'] = [[sys.executable, '-c', 'print("OK (skipped=1)")']]
            self.assertEqual(M.run_one(test, Path(tmp))['status'], 'BLOCKED')

    def test_exact_artifact_runner_does_not_fall_back_to_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            test = copy.deepcopy(self.contract['tests'][1])
            test['commands'] = [['python3', 'not-executed.py', '{initramfs}']]
            self.assertEqual(M.run_one(test, Path(tmp))['status'], 'BLOCKED')

    def test_h01_requires_live_matching_capture_not_another_release(self):
        test = next(t for t in self.contract['tests'] if t['id']=='H01')
        release = dict(candidate_id='exact-rescue', artifact_paths=dict(kernel='/kernel',initramfs='/archive'),
                       artifacts=dict(boot_bundle=dict(sha256='a'*64)))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(M.run_one(test,root,release)['status'],'BLOCKED')
            receipt=dict(profile='other',canonical_record=dict(candidate='wrong',boot_image_sha256='a'*64))
            (root/'receipt.json').write_text(json.dumps(receipt))
            self.assertEqual(M.run_one(test,root,release,root)['status'],'FAIL')
            receipt['canonical_record']['candidate']='exact-rescue'
            receipt['canonical_record']['boot_image_sha256']='b'*64
            (root/'receipt.json').write_text(json.dumps(receipt))
            self.assertEqual(M.run_one(test,root,release,root)['status'],'FAIL')

    def test_h02_is_executable_but_missing_cycle_inputs_are_blocked(self):
        test = next(t for t in self.contract['tests'] if t['id']=='H02')
        self.assertTrue(test['commands'])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(M.run_one(test,Path(tmp))['status'],'BLOCKED')

    def test_c02_is_executable_and_missing_exact_release_is_blocked(self):
        test = next(t for t in self.contract['tests'] if t['id'] == 'C02')
        self.assertTrue(test['commands'])
        self.assertIn('--c02', test['commands'][0])
        self.assertEqual(test['deadline_seconds'], 120)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(M.run_one(test, Path(tmp))['status'], 'BLOCKED')

    def test_c02_exit_zero_without_exact_complete_proof_is_not_success(self):
        test = copy.deepcopy(next(t for t in self.contract['tests'] if t['id']=='C02'))
        test['commands'] = [[sys.executable, '-c', 'print("component PASS")']]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = dict(artifacts={role: dict(sha256='a'*64)
                                      for role in ('kernel','initramfs','rootfs')})
            self.assertEqual(M.run_one(test, root, release)['status'], 'FAIL')
            (root/'C02').mkdir()
            proof = dict(status='PASS', c02_qualified=True, root_image_unchanged=True,
                         source_revision=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                         runner_sha256=M.sha_file(M.REPO/'scripts/host/test-qemu-watchdog-handoff.py'),
                         kernel_sha256='a'*64, target_archive_sha256='a'*64,
                         root_image_sha256='a'*64, duration_seconds=119,
                         c02_variant='core-only',
                         cases=[dict(mode=m,passed=True,exit_code=0) for m in
                                ('systemd-ack','systemd-stale-identity')])
            path = root/'C02/result.json'
            for changes in (dict(c02_qualified=False), dict(root_image_unchanged=False),
                            dict(kernel_sha256='b'*64), dict(target_archive_sha256='b'*64),
                            dict(root_image_sha256='b'*64), dict(source_revision='b'*40),
                            dict(runner_sha256='b'*64), dict(duration_seconds=121),
                            dict(cases=[]), dict(c02_variant='unknown')):
                path.write_text(json.dumps(dict(proof,**changes)))
                self.assertEqual(M.run_one(test,root,release)['status'], 'FAIL', changes)
            path.write_text(json.dumps(proof))
            self.assertEqual(M.run_one(test,root,release)['status'], 'PASS')

    def test_h02_exit_zero_without_complete_proof_is_not_success(self):
        test = copy.deepcopy(next(t for t in self.contract['tests'] if t['id']=='H02'))
        test['commands'] = [[sys.executable, '-c', 'print("component PASS")']]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(M.run_one(test,root)['status'],'FAIL')
            (root/'H02').mkdir()
            (root/'H02/result.json').write_text(json.dumps(dict(status='PASS',h02_qualified=False)))
            self.assertEqual(M.run_one(test,root)['status'],'FAIL')

    def test_rescue_inputs_bind_only_known_arguments_to_exact_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'inputs.json'
            values = dict(profile='fixture',cycle='/private/cycle',execution_record='/private/record',
                          manifest='/private/manifest',identity_file='/private/key',known_hosts='/private/hosts')
            path.write_text(json.dumps(values))
            result = M.rescue_bindings(path)
            self.assertEqual(result['{rescue_profile}'], 'fixture')
            self.assertEqual(result['{rescue_cycle}'], '/private/cycle')
            for extra in (dict(command='/bin/sh'), dict(cycle='relative')):
                path.write_text(json.dumps(dict(values,**extra)))
                with self.assertRaises(ValueError): M.rescue_bindings(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
