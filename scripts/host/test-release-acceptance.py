#!/usr/bin/env python3
"""Offline acceptance bookkeeping regressions; no device or shared state."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).with_name('release-acceptance.py')
SPEC = importlib.util.spec_from_file_location('acceptance', SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class AcceptanceTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
