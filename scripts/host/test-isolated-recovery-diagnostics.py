#!/usr/bin/env python3
"""Reset observation protocol; no phone or filesystem changes."""
import copy
import importlib.util
from pathlib import Path
import unittest
S=importlib.util.spec_from_file_location('r01_reset',Path(__file__).with_name('isolated-recovery-diagnostics.py'))
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
IDENTITY=dict(boot_id='11111111-1111-4111-8111-111111111111',release='7.1.4-fixture',bundle='fixture')

def fixture(records=()):
    rows=[['format','rog5-r01-reset-observation-v1'],['identity',IDENTITY['boot_id'],IDENTITY['release'],IDENTITY['bundle']],
          ['cmdline',b'rog5.bundle=fixture androidboot.bootreason=reboot'.hex()],['directory','/sys/fs/pstore','present']]
    rows.extend(records)
    return rows+[['directory','/mnt/pstore','absent'],['boot_after',IDENTITY['boot_id']]]

def raw(rows):return ('\n'.join('|'.join(row) for row in rows)+'\n').encode()

class Tests(unittest.TestCase):
    def test_empty_and_available_records_never_infer_reset_cause(self):
        for rows in (fixture(),fixture([['record','/sys/fs/pstore',b'dmesg-ramoops-0'.hex(),'present',b'actual bytes\0\n'.hex()]])):
            result=M.replay(raw(rows),IDENTITY)
            self.assertTrue(result['empty_pstore_inconclusive']);self.assertFalse(result['reset_cause_proven'])
    def test_optional_absence_unsupported_and_error_are_observations(self):
        for state in ('absent','unsupported','error'):
            rows=fixture();rows[3][2]=state
            self.assertEqual(M.replay(raw(rows),IDENTITY)['directories']['/sys/fs/pstore'],state)
    def test_truncation_overflow_and_unreadable_record_are_explicit(self):
        rows=fixture([['record','/sys/fs/pstore',b'log'.hex(),'truncated',(b'x'*4097).hex()],
                      ['record','/sys/fs/pstore',b'unreadable'.hex(),'error',''],['overflow','/sys/fs/pstore']])
        result=M.replay(raw(rows),IDENTITY)
        self.assertEqual(result['records'][0]['status'],'truncated');self.assertEqual(result['overflow'],['/sys/fs/pstore'])
    def test_wrong_boot_malformed_duplicate_or_unbound_records_refuse(self):
        for case in ('wrong-boot','wrong-bundle','partial','duplicate-directory','duplicate-record','unsupported-record',
                     'oversize','slash-name','nul-name','wrong-truncation','error-data','unknown'):
            rows=fixture([['record','/sys/fs/pstore',b'log'.hex(),'present','78']]);data=None
            if case=='wrong-boot':rows[-1][1]='22222222-2222-4222-8222-222222222222'
            if case=='wrong-bundle':rows[2][1]=b'rog5.bundle=other'.hex()
            if case=='partial':data=raw(rows)[:-1]
            if case=='duplicate-directory':rows.insert(4,rows[3].copy())
            if case=='duplicate-record':rows.insert(5,rows[4].copy())
            if case=='unsupported-record':rows[3][2]='unsupported'
            if case=='oversize':rows[4][4]=(b'x'*4098).hex()
            if case=='slash-name':rows[4][2]=b'../log'.hex()
            if case=='nul-name':rows[4][2]=b'log\0'.hex()
            if case=='wrong-truncation':rows[4][3]='truncated'
            if case=='error-data':rows[4][3]='error'
            if case=='unknown':rows.insert(4,['other'])
            with self.subTest(case=case),self.assertRaises(ValueError):M.replay(data or raw(rows),IDENTITY)
    def test_generator_rejects_injected_identity_and_unpinned_tools(self):
        for identity in (dict(IDENTITY,bundle='$(reboot)'),dict(IDENTITY,boot_id='bad'),dict(IDENTITY,extra='value')):
            with self.assertRaises(ValueError):M.script(identity,'a'*64,'b'*64)
        with self.assertRaises(ValueError):M.script(IDENTITY,'not-a-pin','b'*64)
        source=M.script(IDENTITY,'a'*64,'b'*64)
        self.assertIn('set -o pipefail',source);self.assertIn('head -c 4097',source)

if __name__=='__main__':unittest.main()
