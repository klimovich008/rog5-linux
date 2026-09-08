#!/usr/bin/env python3
"""R01 raw replay boundaries; loopback receiver frames, no phone operations."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('r01_checker_tests',Path(__file__).with_name('check-isolated-recovery.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
NEG=dict(boot_id='12345678-1234-4abc-8def-1234567890ab',bundle='fixture-negative',release='7.1.4-negative')
BACK=dict(boot_id='87654321-4321-4abc-8def-1234567890ab',bundle='fixture-rescue',release='7.1.4-rescue')
RETURN=dict(bundle=BACK['bundle'],release=BACK['release'],manifest_sha256='a'*64)


def stream():
    rows=[dict(event='stream-started',format='rog5-r01-journal-stream-v1',**NEG,
               uptime_seconds=100,maximum_uptime_seconds=915)]
    for message,stamp in ((M.JOB_START,900000000),(M.JOB_SUCCESS,901000000)):
        rows.append(dict(_BOOT_ID=NEG['boot_id'].replace('-',''),_PID='1',_UID='0',
                         UNIT=M.OBS.UNITS['rollback'],MESSAGE_ID=message,JOB_ID='42',
                         __MONOTONIC_TIMESTAMP=str(stamp)))
    return rows


def raw(rows):return b''.join(json.dumps(row).encode()+b'\n' for row in rows)


def frame(identity):
    return ('format=rog5-persistent-root-stage-v2\ntarget_release='+identity['release']+
            '\nboot_id='+identity['boot_id']+'\nsequence=1\nstage=switch-root\nstate=PASS\ndetail=none\n').encode()


def fixture():
    events=[];now=1000
    def emit(event):
        nonlocal now
        now+=.001;events.append(dict(event,monotonic=now))
    for name in M.SMOKE.B.READ.PREPARED:emit(dict(event=name))
    with M.CAP.Receiver(NEG['release'],emit,return_identity=RETURN,host='127.0.0.1',port=0,peer='127.0.0.1') as receiver:
        now=1100;receiver.transport('target',None);receiver.record(frame(NEG),'127.0.0.1')
        now=1913;receiver.transport('absent',None)
        now=2000;receiver.transport('target',None);receiver.record(frame(BACK),'127.0.0.1')
        assert not receiver.failed
        now=2380.1;emit(dict(event='capture-ended',status='NOT RUN',return_seen=True,initial_boot=NEG['boot_id']))
    for item in ('route','firewall','profile','address'):emit(dict(event='host-cleanup',item=item,status='PASS'))
    samples=[dict(started_monotonic=1012+uptime,finished_monotonic=1012.25+uptime,uptime=uptime)
             for uptime in [*range(100,871,10),875]]
    return dict(receipt=dict(started_monotonic=1000,deadline_monotonic=2380,required_seconds=1320,
                             timing=M.CAP.ACCEPTANCE.load_contract()['defaults']['rescue_capture'],return_identity=RETURN),
                events=events,entry=1010,returned=2012,negative=NEG,rescue=BACK,samples=samples,
                callback=M.journal(raw(stream()),NEG))


class ReplayTest(unittest.TestCase):
    def test_real_receiver_frames_have_no_release_field(self):
        value=fixture()
        self.assertTrue(all('release' not in event['stage'] for event in value['events'] if event['event']=='stage'))
        result=M.timeline(**value)
        self.assertEqual(result['physical_recovery_seconds'],1002)
        self.assertGreater(result['capture_seconds'],1380)

    def test_deadlines_are_distinct_and_cannot_extend_each_other(self):
        for change in ('late-return','short-capture','late-entry','wrong-budget'):
            with self.subTest(change=change):
                value=fixture()
                if change=='late-return':value['returned']=2210.001
                if change=='short-capture':value['receipt']['deadline_monotonic']=2379
                if change=='late-entry':value['entry']=1061
                if change=='wrong-budget':value['receipt']['required_seconds']=1200
                with self.assertRaises(ValueError):M.timeline(**value)

    def test_capture_failures_cannot_be_restored_into_pass(self):
        for change in ('early-end','cleanup-failed','capture-failed','late-disconnect','third-boot','wrong-return'):
            with self.subTest(change=change):
                value=fixture();events=value['events']
                ended=next(e for e in events if e['event']=='capture-ended')
                if change=='early-end':ended['monotonic']=2379
                if change=='cleanup-failed':events[-1]['status']='FAIL'
                if change=='capture-failed':ended['status']='FAIL'
                if change=='late-disconnect':events.insert(-1,dict(event='unexpected-post-return-disconnect',monotonic=events[-1]['monotonic']))
                if change=='third-boot':next(e for e in events if e['event']=='stage')['stage']['boot_id']='aaaaaaaa-1234-4abc-8def-1234567890ab'
                if change=='wrong-return':next(e for e in events if e['event']=='recovery-boot-observed')['return_identity']['manifest_sha256']='b'*64
                with self.assertRaises(ValueError):M.timeline(**value)

    def test_sampling_gaps_and_clock_mismatch_fail(self):
        for change in ('gap','clock','early-stop','negative-missing'):
            with self.subTest(change=change):
                value=fixture()
                if change=='gap':del value['samples'][20:23]
                if change=='clock':value['samples'][20]['uptime']+=30
                if change=='early-stop':value['samples']=value['samples'][:-3]
                if change=='negative-missing':value['samples']=[]
                with self.assertRaises(ValueError):M.timeline(**value)

    def test_expected_removal_read_precedes_loss_but_arbitrary_failure_does_not(self):
        value=fixture();events=value['events'];index=next(i for i,e in enumerate(events) if e['event']=='recovery-disconnected')
        event=dict(event='recovery-discovery-interrupted',monotonic=events[index]['monotonic']-.01,
                   target_seen=True,phase='usb-discovery',errno=19,observed_mode='absent',
                   operation=next(iter(M.CAP.USB_READ_OPERATIONS)),last_stage=events[index]['last_stage'])
        events.insert(index,event);M.timeline(**value)
        for key,bad in (('errno',13),('observed_mode','enumerating'),('monotonic',1800),('target_seen',False)):
            with self.subTest(key=key):
                changed=copy.deepcopy(value);changed['events'][index][key]=bad
                with self.assertRaises(ValueError):M.timeline(**changed)

    def test_journal_requires_complete_matching_pid_one_job(self):
        self.assertEqual(M.journal(raw(stream()),NEG)['job_id'],'42')
        for change in ('partial','wrong-job','wrong-pid','failed','early','late','duplicate','other-boot'):
            with self.subTest(change=change):
                rows=stream()
                if change=='wrong-job':rows[-1]['JOB_ID']='43'
                if change=='wrong-pid':rows[-1]['_PID']='2'
                if change=='failed':rows[-1]['MESSAGE_ID']=M.JOB_FAILED
                if change=='early':rows[1]['__MONOTONIC_TIMESTAMP']='899999999'
                if change=='late':rows[-1]['__MONOTONIC_TIMESTAMP']='914000000'
                if change=='duplicate':rows.append(rows[-1])
                if change=='other-boot':rows[-1]['_BOOT_ID']=BACK['boot_id'].replace('-','')
                data=raw(rows)+(b'{' if change=='partial' else b'')
                with self.assertRaises(ValueError):M.journal(data,NEG)

    def test_pinned_reader_rejects_symlinks_hardlinks_and_changed_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);file=directory/'evidence';file.write_bytes(b'evidence')
            self.assertEqual(M.pinned(file,M.digest(b'evidence')),b'evidence')
            with self.assertRaises(ValueError):M.pinned(file,'a'*64)
            link=directory/'link';link.symlink_to(file)
            with self.assertRaises(ValueError):M.pinned(link)
            hard=directory/'hard';hard.hardlink_to(file)
            with self.assertRaises(ValueError):M.pinned(file)


if __name__=='__main__':unittest.main()
