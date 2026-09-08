#!/usr/bin/env python3
"""Synthetic completed-rescue regressions; no private data or phone access."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

M=load('rescue_runtime_tested',Path(__file__).with_name('rescue-runtime-evidence.py'))
FRAMES=load('rescue_sample_fixtures',M.R/'scripts/host/test-check-charging-regulation.py')
STARTUP=load('rescue_startup_fixtures',M.R/'scripts/host/test-check-rescue-startup.py')

class Tests(unittest.TestCase):
    def series(self):
        raw={};rows=[]
        for index in range(61):
            reply=FRAMES.frame(uptime_before=str(1000+index*10),uptime_after=str(1000.1+index*10))
            raw[f'sample-{index:02d}.raw']=reply
            row=M.G.parse_frame(reply,FRAMES.IDENTITY,900)
            row.update(elapsed_s=.1+index*10,read_seconds=.1);rows.append(row)
        proof=dict(samples=61,raw_replies=61,branch='firmware-full-v1',duration_seconds=604,
                   outcome=M.G.REGULATION.evaluate_full(rows))
        return proof,rows,raw

    def test_raw_observation_replay_and_mutations(self):
        proof,rows,raw=self.series()
        self.assertEqual(M.charging_rows(proof,rows,raw,FRAMES.IDENTITY,900),proof['outcome'])
        for mutation in ('missing','stale','cadence','boolean','raw','duration','outcome'):
            with self.subTest(mutation=mutation):
                p=copy.deepcopy(proof);data=copy.deepcopy(rows);frames=raw.copy()
                if mutation=='missing':data.pop()
                if mutation=='stale':data[30]['target_uptime_after']=data[29]['target_uptime_after']
                if mutation=='cadence':data[30]['elapsed_s']+=4
                if mutation=='boolean':data[0]['current_ua']=False
                if mutation=='raw':frames['sample-30.raw']=frames['sample-29.raw']
                if mutation=='duration':p['duration_seconds']=661
                if mutation=='outcome':p['outcome']={}
                with self.assertRaises(ValueError):M.charging_rows(p,data,frames,FRAMES.IDENTITY,900)

    def test_original_versions_never_disable_startup_validation(self):
        fixture=STARTUP.Tests();fixture.setUp()
        args=[fixture.record,fixture.identity,fixture.execution,fixture.receipt,'c'*64,
              fixture.events,fixture.attempts,fixture.smoke,fixture.readiness,300]
        M.H.validate(*args)
        versions=dict(receiver='a'*64,readiness='b'*64)
        fixture.receipt['receiver_sha256']=versions['receiver'];fixture.readiness['runner_sha256']=versions['readiness']
        with self.assertRaisesRegex(ValueError,'changed evidence producer'):M.H.validate(*args)
        result=M.H.validate(*args,observed_producers=versions)
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['h02_qualified'])
        for changed in ({},dict(versions,receiver=True),dict(versions,extra='c'*64)):
            with self.assertRaises(ValueError):M.H.validate(*args,observed_producers=changed)
        fixture.execution['flash']=True
        with self.assertRaises(ValueError):M.H.validate(*args,observed_producers=versions)

    def test_original_capture_must_end_and_restore_host(self):
        receipt=dict(required_seconds=1320,deadline_monotonic=1480,started_monotonic=100,
                     timing=dict(M.H.D.CAPTURE.ACCEPTANCE.load_contract()['defaults']['rescue_capture']))
        result=dict(status='NOT RUN',duration_seconds=1380.1)
        events=[dict(event='capture-ended',monotonic=1480.1,**result)]
        events += [dict(event='host-cleanup',item=name,status='PASS',monotonic=1481+i)
                   for i,name in enumerate(('route','firewall','profile','address'))]
        M.capture_closed(receipt,result,events)
        for modified in (events[:-1],events[1:],events+[events[0]]):
            with self.assertRaises(ValueError):M.capture_closed(receipt,result,modified)
        with self.assertRaises(ValueError):M.capture_closed(receipt,dict(result,status='FAIL'),events)
        with self.assertRaises(ValueError):M.capture_closed(dict(receipt,deadline_monotonic=2000),result,events)
        with self.assertRaises(ValueError):M.capture_closed(dict(receipt,required_seconds=1),result,events)

    def test_original_source_must_bind_clean_revision(self):
        source=dict(clean=True,revision='a'*40,worktree_digest=M.sha(('a'*40).encode()))
        self.assertEqual(M.historical_source(source),'a'*40)
        for changed in (dict(source,clean=1),dict(source,clean=False),dict(source,revision='b'*40)):
            with self.assertRaises(ValueError):M.historical_source(changed)

    def test_composition_and_ssh_proofs_must_be_complete_and_paired(self):
        hashes=dict.fromkeys(('kernel','dtb','initramfs','rootfs','boot_bundle'),'a'*64)
        a01=next(t for t in M.H.D.CAPTURE.ACCEPTANCE.load_contract()['tests'] if t['id']=='A01')
        source=dict(clean=True,revision='a'*40,worktree_digest=M.sha(('a'*40).encode()))
        composition=dict(status='PASS',a01_qualified=True,candidate='rescue',artifact_hashes=hashes,
                         root_unchanged=True,checks=dict.fromkeys(a01['required_checks'],'PASS'),duration_seconds=60,
                         source=source,runner_sha256='b'*64)
        c02=dict(status='PASS',c02_qualified=True,release_qualified=False,root_image_unchanged=True,
                 kernel_sha256=hashes['kernel'],target_archive_sha256=hashes['initramfs'],root_image_sha256=hashes['rootfs'],
                 c02_variant='core-only',root_scope='retained-base-only',duration_seconds=90,source=source,runner_sha256='b'*64,
                 cases=[dict(mode=mode,passed=True,exit_code=0,seconds=20) for mode in ('systemd-ack','systemd-stale-identity')])
        with patch.object(M,'original_bytes',side_effect=lambda source,path,pin=None:(M.R/path).read_bytes()):
            M.paired_composition(composition,c02,'rescue',hashes)
            for mutation in ('candidate','root','archive','missing-case','case-failed','checks','late','overlay'):
                with self.subTest(mutation=mutation):
                    a=copy.deepcopy(composition);c=copy.deepcopy(c02)
                    if mutation=='candidate':a['candidate']='server'
                    if mutation=='root':c['root_image_sha256']='c'*64
                    if mutation=='archive':c['target_archive_sha256']='c'*64
                    if mutation=='missing-case':c['cases'].pop()
                    if mutation=='case-failed':c['cases'][0]['passed']=False
                    if mutation=='checks':a['checks'].pop('root_runtime')
                    if mutation=='late':c['duration_seconds']=121
                    if mutation=='overlay':c['root_scope']='retained-base-and-upper'
                    with self.assertRaises(ValueError):M.paired_composition(a,c,'rescue',hashes)

    def test_changed_or_aliased_evidence_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'proof';path.write_bytes(b'fixture');path.chmod(0o600)
            self.assertEqual(M.pinned(path,M.sha(b'fixture')),b'fixture')
            with self.assertRaises(ValueError):M.pinned(path,'a'*64)
            link=Path(tmp)/'link';link.symlink_to(path)
            with self.assertRaises(OSError):M.pinned(link,M.sha(b'fixture'))

    def test_aggregate_bound_precedes_decoding_or_full_collection(self):
        args=SimpleNamespace(inputs=Path('/fixture/input'),inputs_sha256='a'*64)
        inputs=json.dumps(dict(format='rog5-rescue-runtime-evidence-v1',files={name:dict(path='/fixture/'+name,sha256='b'*64) for name in M.ROLES})).encode()
        calls=[];payload=b'x'*(4*M.H.LIMIT)
        def read(path,pin):
            calls.append(path);return inputs if path==args.inputs else payload
        with patch.object(M,'pinned',side_effect=read),self.assertRaisesRegex(ValueError,'aggregate rescue'):
            M.evaluate(args)
        self.assertEqual(len(calls),6)

if __name__=='__main__':unittest.main()
