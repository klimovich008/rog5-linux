#!/usr/bin/env python3
"""Receipt/transport regressions. No phone, claim or global network changes."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

# The receipt parser for initramfs/persistent-root-shutdown-standalone. The
# socket receiver that armed it (headless-stage-receiver.py) is retired.
SPEC=importlib.util.spec_from_file_location('teardown_observation_tests',Path(__file__).with_name('source-teardown-observation.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
BOOT='12345678-1234-4abc-8def-1234567890ab'
IDENTITY=dict(boot_id=BOOT,serial='FIXTURE123',bundle='headless-server-fixture',release='7.2.7-fixture')

def prepared(*,diagnostics=False):
    raw=(M.REPO/'initramfs/persistent-root-shutdown-standalone').read_bytes()
    return M.prepare(raw,M.sha(raw),IDENTITY,'a'*64,diagnostics=diagnostics)

def frame(spec):
    values=dict(format=M.FORMAT,boot_id=BOOT,nonce=spec['nonce'],shutdown_sha256=spec['shutdown_sha256'],
        observer_sha256=spec['observer_sha256'],physical_nodes='117',mounts='clear',loops='clear',physical_ro='all',result='PASS')
    return ''.join(k+'='+v+'\n' for k,v in values.items()).encode()

def diagnostic(spec,phase='teardown',clean='1',state='begin',reason=None):
    values=dict(format=M.DIAGNOSTIC_FORMAT,boot_id=BOOT,nonce=spec['nonce'],
        shutdown_sha256=spec['shutdown_sha256'],observer_sha256=spec['observer_sha256'],
        phase=phase,clean=clean,state=state,
        reason=reason if reason is not None else ('none' if state=='begin' else 'check-failed'))
    return ''.join(k+'='+v+'\n' for k,v in values.items()).encode()

class TeardownTest(unittest.TestCase):
    def test_failure_categories_are_bounded_phase_specific_and_never_clean(self):
        spec,_=prepared(diagnostics=True)
        reasons=('mount-read','mount-command','mount-command:1','mount-command:2',
            'mount-row:5','mount-filesystem:ext4:259:58','mount-filesystem:overlay:0:8',
            'mount-filesystem:unknown:invalid','mount-device:259:58','mount-device:invalid',
            'mount-missing:root','mount-missing:proc','mount-missing:sys','mount-missing:dev')
        for reason in reasons:
            raw=diagnostic(spec,'mounts',state='fail',reason=reason)
            with self.subTest(reason=reason):
                self.assertLessEqual(len(raw),512)
                self.assertEqual(M.parse_diagnostic(raw,spec)['reason'],reason)
                obs=M.Observation(spec,BOOT,100)
                obs.diagnose(diagnostic(spec),101);obs.diagnose(diagnostic(spec,'mounts'),102)
                obs.diagnose(raw,103)
                with self.assertRaises(ValueError):obs.observe(frame(spec),104)
                with self.assertRaises(ValueError):M.parse_diagnostic(diagnostic(spec,'loops',state='fail',reason=reason),spec)
        for reason in ('none','mount-row:0','mount-command:0','mount-missing:other',
                       'mount-filesystem:/private/path:259:58','mount-device:259:58\nextra=secret',
                       'mount-filesystem:'+('x'*33)+':0:1'):
            with self.subTest(reason=reason),self.assertRaises(ValueError):
                M.parse_diagnostic(diagnostic(spec,'mounts',state='fail',reason=reason),spec)
        with self.assertRaises(ValueError):M.parse_diagnostic(diagnostic(spec,'mounts',reason='mount-read'),spec)

    def test_diagnostics_are_opt_in_bound_and_do_not_change_timeout(self):
        plain,base=prepared();spec,files=prepared(diagnostics=True)
        self.assertNotIn('diagnostics',plain);self.assertIs(spec['diagnostics'],True)
        self.assertNotEqual(spec['shutdown_sha256'],plain['shutdown_sha256'])
        self.assertEqual(files['shutdown'].replace(b' --diagnostics',b''),base['shutdown'])
        self.assertIn(b'timeout -s KILL 5',files['shutdown'])
        self.assertEqual((spec,files),prepared(diagnostics=True))
        for bad in (False,1,'true',None):
            changed=copy.deepcopy(spec);changed['diagnostics']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):M.intent(changed)
        with self.assertRaises(ValueError):M.parse_diagnostic(diagnostic(spec),plain)

    def test_diagnostic_parser_requires_exact_identity_order_and_values(self):
        spec,_=prepared(diagnostics=True);raw=diagnostic(spec)
        self.assertEqual(M.parse_diagnostic(raw,spec)['phase'],'teardown')
        for row in raw.splitlines(keepends=True):
            with self.subTest(row=row),self.assertRaises(ValueError):
                M.parse_diagnostic(raw.replace(row,row[:-1]+b'x\n'),spec)
        for bad in (raw[:-1],raw+b'\n',raw.replace(b'\n',b'\r\n'),raw+b'x'*513,
                    raw.replace(b'state=begin',b'state=PASS'),diagnostic(spec,'physical','0'),
                    b'\n'.join(reversed(raw.splitlines()))+b'\n'):
            with self.subTest(bad=bad[:40]),self.assertRaises(ValueError):M.parse_diagnostic(bad,spec)

    def test_diagnostics_require_order_and_never_substitute_for_receipt(self):
        spec,_=prepared(diagnostics=True);obs=M.Observation(spec,BOOT,100)
        for i,phase in enumerate(M.PHASES):
            record=obs.diagnose(diagnostic(spec,phase),101+i)
            self.assertEqual(record['payload_sha256'],M.sha(diagnostic(spec,phase)))
            self.assertIsNone(obs.receipt)
        self.assertEqual(obs.observe(frame(spec),106)['record']['result'],'PASS')
        with self.assertRaises(ValueError):obs.diagnose(diagnostic(spec,'receipt','1','fail'),107)
        for case in ('missing','reordered','duplicate','fail-first','backwards','expired','nan','bool','early-receipt'):
            obs=M.Observation(spec,BOOT,100)
            with self.subTest(case=case),self.assertRaises(ValueError):
                if case=='missing':obs.observe(frame(spec),101)
                elif case=='reordered':obs.diagnose(diagnostic(spec,'physical'),101)
                elif case=='fail-first':obs.diagnose(diagnostic(spec,state='fail'),101)
                elif case in ('expired','nan','bool'):
                    obs.diagnose(diagnostic(spec),{'expired':161,'nan':float('nan'),'bool':True}[case])
                elif case=='early-receipt':
                    for i,phase in enumerate(M.PHASES):obs.diagnose(diagnostic(spec,phase),101+i)
                    obs.observe(frame(spec),104)
                else:
                    obs.diagnose(diagnostic(spec),102)
                    obs.diagnose(diagnostic(spec,'teardown' if case=='duplicate' else 'mounts'),101 if case=='backwards' else 103)

    def test_diagnostic_failure_is_permanent_and_keeps_clean_receipt_absent(self):
        spec,_=prepared(diagnostics=True)
        for phase in M.PHASES:
            obs=M.Observation(spec,BOOT,100)
            for current in M.PHASES[:M.PHASES.index(phase)+1]:obs.diagnose(diagnostic(spec,current),101)
            self.assertEqual(obs.diagnose(diagnostic(spec,phase,state='fail'),102)['record']['state'],'fail')
            self.assertTrue(obs.failed);self.assertIsNone(obs.receipt)
            with self.assertRaises(ValueError):obs.observe(frame(spec),103)
        obs=M.Observation(spec,BOOT,100)
        obs.diagnose(diagnostic(spec,clean='0'),101)
        obs.diagnose(diagnostic(spec,clean='0',state='fail'),102)
        self.assertTrue(obs.failed)

    def test_preparation_is_deterministic_and_preserves_accepted_teardown(self):
        spec,files=prepared();self.assertEqual((spec,files),prepared())
        original=(M.REPO/'initramfs/persistent-root-shutdown-standalone').read_bytes()
        hook=(b'if [ -f /rog5-source-teardown ] && [ ! -L /rog5-source-teardown ]; then\n'
            b'\t"$bb" timeout -s KILL 5 "$bb" sh /rog5-source-teardown "$clean" "${1:-reboot}" || true\nfi\n')
        self.assertEqual(files['shutdown'].count(hook),1)
        restored=files['shutdown'].replace(hook,b'').replace(b'/usr/libexec/rog5-reboot-bootloader || true',b'"$bb" reboot -f 2>/dev/null || true')
        self.assertEqual(restored,original)
        self.assertLess(files['shutdown'].index(hook),files['shutdown'].index(b'for api in run dev sys proc; do'))
        self.assertEqual(spec['shutdown_sha256'],M.sha(files['shutdown']))
        for row in files['rog5-source-teardown.sha256'].decode().splitlines():
            digest,path=row.split('  ');self.assertEqual(digest,M.sha(files[path]))
        with self.assertRaises(ValueError):M.prepare(original+b'\n',M.sha(original+b'\n'),IDENTITY,'a'*64)
        with self.assertRaises(ValueError):M.prepare(original,'b'*64,IDENTITY,'a'*64)

    def test_receipt_requires_every_exact_field_and_lf_framing(self):
        spec,_=prepared();raw=frame(spec);self.assertLessEqual(len(raw),512)
        self.assertEqual(M.parse(raw,spec)['result'],'PASS')
        for row in raw.splitlines(keepends=True):
            with self.subTest(row=row),self.assertRaises(ValueError):M.parse(raw.replace(row,row.rstrip(b'\n')+b'x\n'),spec)
        for bad in (raw[:-1],raw+b'\n',raw.replace(b'\n',b'\r\n'),raw.replace(b'\n',b'\v'),
                    raw.replace(b'\n',b'\x1c'),raw+b'x'*513,raw+b'\xff\n',raw.replace(b'result=PASS',b'result=FAIL'),
                    b'\n'.join(reversed(raw.splitlines()))+b'\n'):
            with self.subTest(bad=bad[:30]),self.assertRaises(ValueError):M.parse(bad,spec)

    def test_intent_rejects_ambiguous_shapes_and_owns_immutable_copy(self):
        spec,_=prepared()
        for key,value in (('physical_nodes',True),('physical_nodes','117'),('nonce','a'*63),('extra',1)):
            bad=copy.deepcopy(spec);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.intent(bad)
        obs=M.Observation(spec,BOOT,100);spec['identity']['boot_id']='wrong'
        self.assertEqual(obs.expected['identity']['boot_id'],BOOT)
        with self.assertRaises(ValueError):M.Observation(obs.expected,'different',100)

    def test_one_receipt_has_absolute_finite_deadline(self):
        for now in (99.999,160.001,float('nan'),float('inf'),True):
            spec,_=prepared()
            with self.subTest(now=now),self.assertRaises(ValueError):M.Observation(spec,BOOT,100).observe(frame(spec),now)
        for now in (100,160):
            spec,_=prepared();obs=M.Observation(spec,BOOT,100);result=obs.observe(frame(spec),now)
            self.assertEqual(result['payload_sha256'],M.sha(frame(spec)))
            with self.assertRaises(ValueError):obs.observe(frame(spec),now)

    def test_pinned_intent_reader_refuses_links_writable_oversize_or_duplicate_json(self):
        spec,_=prepared()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'intent';raw=json.dumps(spec).encode();path.write_bytes(raw);path.chmod(0o600)
            self.assertEqual(M.read_intent(path,M.sha(raw)),spec)
            with self.assertRaises(ValueError):M.read_intent(path,'0'*64)
            link=Path(tmp)/'link';link.symlink_to(path)
            with self.assertRaises(OSError):M.read_intent(link,M.sha(raw))
            path.chmod(0o666)
            with self.assertRaises(ValueError):M.read_intent(path,M.sha(raw))
            path.chmod(0o600)
            for bad in (b' '*2049,raw[:-1]+b',"format":"rog5-source-teardown-intent-v1"}'):
                path.write_bytes(bad)
                with self.assertRaises(ValueError):M.read_intent(path,M.sha(bad))

if __name__=='__main__':unittest.main(verbosity=2)
