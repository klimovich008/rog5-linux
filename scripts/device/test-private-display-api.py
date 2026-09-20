#!/usr/bin/env python3
"""Actual caller definitions and unchanged 0009 sources, ordinary-user fixtures.

No private module top-level is executed. The external admission inputs, custody,
private health producers, identity comparator, credentials and transports are
explicit fixtures, not authenticated artifacts. Production cohort/contract code
is real. Tests never issue a lock, claim, or remote command.
"""
import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import shutil
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
P = argparse.ArgumentParser()
P.add_argument('--callers', type=Path, default=None)
P.add_argument('--before', type=Path, default=None)
P.add_argument('--sources', type=Path, default=None)
ARGS, REST = P.parse_known_args()
NS = types.SimpleNamespace
BOOT = '11111111-2222-3333-4444-555555555555'
OWNER = 'a'*32
OLD_BOOT = '00000000-1111-2222-3333-444444444444'
SCOPE = 'gpu-iommu-display-r1/'
ORIGINAL_CALLERS = {
    'live-admission.py.txt': '7c076f7812ed11b694e4c827c4bbc25fe6f7a370c860cb2c3d8ce4804b92580f',
    'trial-launcher.py.txt': 'f8894e240bd32ca7c2081994c1a933df6825e69d0ad82bf5a66b8427af6c1aa1',
}
UNCHANGED = {
    'session.py': '44868048b5ef3d220c039fa0dc601380533e423fd8d507ab8b5c4aff552e4483',
    'health.py': 'f88f6cf1e418a3c90ab59b18c796cbff57188996229a0b8e4fd98ba9ccc62892',
    'display-component.py': 'd2d80309c27ad525945c077e6170b95bbfca93ce347edd7ba5a831e86a6313f6',
}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def exact(a, b): return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)
def noop(*args, **kwargs): return None


def definitions(path, namespace, constants=()):
    """No private imports, top-level loads, or module-main entrypoints."""
    tree = ast.parse(path.read_bytes())
    for name in constants:
        node, = [n for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def source_module(path):
    value = types.ModuleType('fixture_source'); value.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), value.__dict__)
    return value


def globals_for(path):
    return dict(__file__=str(path), __name__='fixture_definitions', base64=base64,
                hashlib=hashlib, json=json, math=math, os=os, Path=Path,
                re=re, stat=stat, time=time)


class StopEffect(Exception): pass


class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        supplied = (ARGS.callers, ARGS.before, ARGS.sources)
        if any(value is not None for value in supplied):
            if not all(value is not None for value in supplied):
                raise ValueError('supply all three fixture directories or none')
            return
        temp = tempfile.TemporaryDirectory(prefix='private-api-assembly-', dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(temp.cleanup)
        base = Path(temp.name)
        ARGS.before, ARGS.callers, ARGS.sources = (base/name for name in ('before', 'after', 'sources'))
        for directory in (ARGS.before, ARGS.callers, ARGS.sources):
            directory.mkdir()
        for stem in ('live-admission', 'trial-launcher'):
            retained = ROOT/'scripts/device/fixtures/display-loader'/(stem+'-before.py.txt')
            for directory in (ARGS.before, ARGS.callers):
                shutil.copyfile(retained, directory/(stem+'.py.txt'))
        # Reuse the actual strict production-source composition, not a second
        # copy of its patch-order or hash-pinning implementation.
        cohort = source_module(ROOT/'scripts/device/test-production-display-cohort.py')
        cohort.assemble(ARGS.sources)
        patch_path = ROOT/'patches/display-controller/0010-private-display-api.patch'
        for options in (['--check'], []):
            subprocess.run(['git', 'apply', *options, str(patch_path)], cwd=ARGS.callers,
                           check=True, capture_output=True, timeout=10)

    def setUp(self):
        if os.getuid() != 1000 or os.geteuid() != 1000:
            raise ValueError('ordinary UID1000 required; do not run as root')
        temp = tempfile.TemporaryDirectory(prefix='private-display-api-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(temp.cleanup); self.root = Path(temp.name)
        for filename, digest in ORIGINAL_CALLERS.items():
            self.assertEqual(sha((ARGS.before/filename).read_bytes()), digest)
        for filename, digest in UNCHANGED.items():
            self.assertEqual(sha((ARGS.sources/filename).read_bytes()), digest)
        for source in ARGS.sources.glob('*.py'):
            directory = ('gpu-iommu-session-r1' if source.name in ('session.py', 'kernel-log.py') else
                         'gpu-iommu-health-r1' if source.name == 'health.py' else 'gpu-iommu-display-r1')
            name = 'successor-health.py' if source.name == 'health.py' else source.name
            target = self.root/directory/name; target.parent.mkdir(exist_ok=True)
            target.write_bytes(source.read_bytes()); target.chmod(0o644)
        self.g = source_module(self.root/'gpu-iommu-session-r1/session.py')
        self.value = dict(format='rog5-live-admission-inputs-v1', files={},
                          production_display_sources=list(self.g.PATHS))
        for name in self.g.PATHS:
            path = self.root/name; st = path.stat()
            self.value['files'][name] = dict(size=st.st_size, uid=st.st_uid,
                                           mode=stat.S_IMODE(st.st_mode), sha256=sha(path.read_bytes()))
        self.ad = types.ModuleType('fixture_admission')
        ad_path = self.root/'gpu-iommu-live-driver-r1/live-admission.py'
        ad_path.parent.mkdir(); ad_path.write_bytes((ARGS.callers/'live-admission.py.txt').read_bytes())
        self.ad.__dict__.update(globals_for(ad_path))
        definitions(ARGS.callers/'live-admission.py.txt', self.ad.__dict__,
                    ('PRODUCTION_PATHS', 'DISCOVERY_FIELDS', 'ARTIFACT_FIELDS'))
        self.source = dict(clean=True, revision='fixture', worktree_digest='f'*64)
        fallback = dict(bundle='fixture-fallback', release='fixture-fallback-release')
        self.c = NS(TARGET=dict(bundle='fixture-production', release='7.1.4-rog5-production'),
                    FALLBACK=fallback, HEALTHY='healthy-fixture', OLD='old-fixture', PENDING='pending-fixture',
                    PHASES=('observe_target',), same_identity=self.same_identity)
        custody = self.root/'custody-fixture'; custody.mkdir()
        for name in ('preparation.json', 'stage-receipt.json'):
            (custody/name).write_bytes(b'inert private custody fixture\n')
        self.a = NS(OWNER=OWNER, SOURCE_BOOT=OLD_BOOT, sha=sha, exact_json=exact,
                    decode=json.loads, fields=lambda raw:dict(line.split('=', 1) for line in raw.decode().splitlines()),
                    PHASES=('arm_state',), SHELL='fixture-shell', W=NS(request=json.loads),
                    STAGING=custody, RECEIPT_SHA='c'*64, CUSTODY_SHA=sha(b'custody'), pinned_sources=noop,
                    C=NS(boot_id=lambda boot:self.assertRegex(boot, r'^[0-9a-f-]{36}$'), FALLBACK=fallback),
                    G=NS(custody=lambda *args:b'custody', build=lambda *args:
                         "expected_bundle=fixture-fallback\nexpected_release=fixture-fallback-release\nrun_helper() {\n"))
        self.wrapper = NS(pins=noop, PHASES=('observe_target', 'post_capture_health', 'locate_fallback',
                            'verify_target_restoration', 'verify_fallback_restoration'),
                          discovery=lambda role:'fixture-discovery-'+role,
                          F=NS(build=lambda *args:'fixture-fallback-health'))
        self.ad.__dict__.update(A=self.a, C=self.c, H=self.wrapper, STATE=self.root,
            OUTPUT=self.root/'gpu-iommu-controller-r1/execution', INPUTS=ad_path.parent/'fixture-inputs', _CACHE={},
            D=NS(BOOT=NS(expected_kernel_relay=noop, pins=noop), pins=noop),
            W=NS(pins=noop, source_identity=lambda:dict(self.source)))
        self.ad.R = NS(receipt=lambda path, limit: self.raw if path == self.ad.INPUTS else path.read_bytes())
        real_digest = self.ad.digest_file
        # These two historical private custody artifacts are intentionally not
        # supplied/qualified. All display-source digest checks are the actual code.
        self.ad.digest_file = lambda path, *args: None if path.parent == custody else real_digest(path, *args)
        self.lock_bytes(json.dumps(self.value).encode())
        self.component = self.g.bind_sources(self.ad)
        self.identity = dict(boot_id=BOOT, owner=OWNER, **self.c.TARGET,
            descriptor_sha256='1'*64, board_dtb_sha256='deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57')
        self.contract = self.g.host_contract(self.ad, self.identity)
        self.h = self.g.H; self.wrapper.H = self.h; self.h.A = self.a
        self.h.SEAL = dict(source_boot_id=OLD_BOOT, owner=OWNER, ssh_fingerprint='SHA256:'+'f'*43,
            target={k:v for k,v in self.identity.items() if k not in ('owner', 'boot_id')},
            trial_id='2'*64, healthy_state_sha256='3'*64, files={})
        self.h.inputs = lambda:copy.deepcopy(self.h.SEAL)
        self.h.ROOT = NS(PROBE='print(json.dumps(value))')
        self.h.OBS = NS(PROBE='actual=dict(identity=identity(),files={},sealed={},units={})')
        self.l = types.ModuleType('fixture_launcher')
        self.l.__dict__.update(globals_for(ARGS.callers/'trial-launcher.py.txt'), AD=self.ad,
            A=self.a, C=self.c, B=NS(), G=self.g, need=self.ad.need,
            LAUNCH=self.root/'launch', AUTH_ROOT=self.root/'auth', LOCK=self.root/'launch.lock')
        definitions(ARGS.callers/'trial-launcher.py.txt', self.l.__dict__)
        self.effects = []
        def forbidden(*args, **kwargs):
            self.effects.append('forbidden'); raise AssertionError('effect must not run')
        self.l.K = NS(Credentials=forbidden); self.l.P = NS(authenticate=forbidden)
        self.ad.PREP = NS(prior_and_staging=forbidden)
        self.c.save = forbidden
        env = patch.dict(os.environ, ALLOW_TEMPORARY_BOOT='1', ALLOW_HEADLESS_LIVE_GATE='1')
        env.start(); self.addCleanup(env.stop)

    def lock_bytes(self, raw, pin=None):
        # Synthetic authentication boundary, in memory only; not a lock issuer.
        self.raw = raw; self.ad.INPUTS_SHA = sha(raw) if pin is None else pin

    def same_identity(self, identity, expected, excluded=()):
        # Omitted private C.same_identity is an explicit fixture, not a claim
        # about its implementation. Verify that callers hand it only identity3.
        self.assertEqual(set(identity), {'boot_id', 'bundle', 'release'})
        self.ad.need(identity['boot_id'] not in excluded and
                     all(identity[k] == v for k,v in expected.items()), 'fixture identity mismatch')

    def rejected(self, fn, text=None):
        with self.assertRaises(ValueError) as error: fn()
        if text: self.assertIn(text, str(error.exception))
        self.assertEqual(self.effects, [])
        self.assertFalse(self.l.LAUNCH.exists()); self.assertFalse(self.l.LOCK.exists())

    def discover(self, role='target', fields=None):
        self.ad.OUTPUT.mkdir(parents=True, exist_ok=True)
        (self.ad.OUTPUT/'admission.json').write_text(json.dumps(dict(host_source=self.source)))
        fields = fields or dict(self.identity if role == 'target' else dict(boot_id='22222222-2222-3333-4444-555555555555', **self.c.FALLBACK))
        out = ''.join(k+'='+fields[k]+'\n' for k in self.ad.DISCOVERY_FIELDS).encode()+b'ready=ready\n'
        raw = dict(status='PASS_TRANSPORT_COMPLETED', command_invoked=True, source=self.source,
            mode='normal' if role == 'target' else 'linklocal', command=dict(returncode=0, timed_out=False, reaped=True,
            stdout_base64=base64.b64encode(out).decode(), stderr_base64='', stdout_sha256=sha(out), stderr_sha256=sha(b'')))
        path = self.ad.OUTPUT/('locate_fallback-discovery-000-'+role+'-transport.json')
        path.write_text(json.dumps(raw)); return path

    def test_actual_inputs_accept_exact_authenticated_scope(self):
        self.assertEqual(self.ad.inputs(), self.value)
        self.assertEqual(tuple(self.ad.PRODUCTION_PATHS), self.g.PATHS)

    def test_input_schema_rejects_legacy_extra_missing_duplicate_unknown(self):
        variants = []
        v=copy.deepcopy(self.value); del v['production_display_sources']; variants.append(v)
        v=copy.deepcopy(self.value); v['extra']=True; variants.append(v)
        v=copy.deepcopy(self.value); v['files']=[]; variants.append(v)
        for names in ([], list(self.g.PATHS)+[self.g.PATHS[0]], list(self.g.PATHS[:-1])+[self.g.PATHS[0]],
                      list(self.g.PATHS[:-1])+['gpu-query-arm64-r1/a/rog5-gpu-query.deploy']):
            v=copy.deepcopy(self.value); v['production_display_sources']=names; variants.append(v)
        v=copy.deepcopy(self.value); del v['files'][self.g.PATHS[0]]; variants.append(v)
        for value in variants:
            with self.subTest(value=value.get('production_display_sources')):
                self.lock_bytes(json.dumps(value).encode()); self.rejected(self.ad.inputs)

    def test_scope_cannot_be_added_without_matching_authenticated_bytes(self):
        old = dict(format=self.value['format'], files=self.value['files'])
        self.lock_bytes(json.dumps(self.value).encode(), sha(json.dumps(old).encode()))
        self.rejected(self.ad.inputs, 'input lock changed')

    def test_actual_0009_retains_private_refusal(self):
        self.rejected(lambda:self.g.initialize(self.ad), 'unresolved source dependency')
        self.assertIsNone(self.g.T.W)

    def test_launcher_missing_foreign_contract_or_owner_precedes_effects(self):
        for function in (self.l.run, self.l._run_once):
            for contract, owner in ((None, OWNER), (self.contract, None), (self.contract, 'b'*32), (object(), OWNER)):
                with self.subTest(function=function.__name__, owner=owner):
                    self.rejected(lambda:function(authenticate=True, contract=contract, owner=owner))

    def test_launcher_actual_preflight_calls_actual_initialize_before_effects(self):
        for function in (self.l.run, self.l._run_once):
            self.rejected(lambda:function(authenticate=True, contract=self.contract, owner=OWNER),
                          'unresolved source dependency')

    def test_launcher_rejects_historical_session_interface(self):
        with patch.object(self.l, 'G', NS()):
            self.rejected(lambda:self.l.production_preflight(self.contract, OWNER), 'historical session')

    def test_preflight_health_consistency_after_explicit_private_readiness_fixture(self):
        # Test ONLY the next API checks; production initialize is never changed.
        with patch.object(self.g, 'initialize', noop):
            self.assertEqual(self.l.production_preflight(self.contract, OWNER), self.identity)
            with patch.object(self.wrapper, 'H', NS()):
                self.rejected(lambda:self.l.production_preflight(self.contract, OWNER), 'health module')
            with patch.object(self.h, 'inputs', lambda:dict(self.h.SEAL, owner='b'*32)):
                self.rejected(lambda:self.l.production_preflight(self.contract, OWNER), 'bound health seal')

    def test_actual_configuration_and_validate_keep_legacy_seal_refusal(self):
        self.h.SEAL = dict(source_boot_id=OLD_BOOT,
            target=dict(bundle='gpu-136f7-a9b1bc89566205b6', release='7.1.4-g136f75ae869a'))
        for function in (lambda:self.h.configuration('target',BOOT,self.contract,OWNER),
                         lambda:self.h.validate({},'target',BOOT,self.contract,OWNER)):
            self.rejected(function, 'health seal differs from production contract')

    def test_actual_target_discovery_accepts_same_six_field_prior_without_promoting_it(self):
        self.discover(); prior = dict(observe_target=dict(identity=copy.deepcopy(self.identity)))
        before = copy.deepcopy(prior)
        self.assertEqual(self.ad.discovered_boot('locate_fallback','target',prior,contract=self.contract,owner=OWNER), BOOT)
        self.assertEqual(prior, before)

    def test_discovery_rejects_every_changed_or_missing_artifact_field(self):
        self.discover()
        for field in self.identity:
            value = dict(self.identity); value[field] = 'x'
            with self.subTest(field=field):
                self.rejected(lambda:self.ad.discovered_boot('locate_fallback','target',
                    dict(observe_target=dict(identity=value)),contract=self.contract,owner=OWNER))
        value = {k:self.identity[k] for k in self.ad.DISCOVERY_FIELDS}
        self.rejected(lambda:self.ad.discovered_boot('locate_fallback','target',
            dict(observe_target=dict(identity=value)),contract=self.contract,owner=OWNER), 'identity6')

    def test_discovery_rejects_wrong_common_fields_owner_contract_and_route(self):
        for field in self.ad.DISCOVERY_FIELDS:
            changed = dict(self.identity); changed[field]='changed'
            path=self.discover(fields=changed)
            self.rejected(lambda:self.ad.discovered_boot('locate_fallback','target',{},contract=self.contract,owner=OWNER))
            path.unlink()
        self.discover()
        for contract,owner in ((None,OWNER),(self.contract,'b'*32)):
            self.rejected(lambda:self.ad.discovered_boot('locate_fallback','target',{},contract=contract,owner=owner))
        self.rejected(lambda:self.ad.discovered_boot('locate_fallback','fallback',{}), 'route differs')

    def test_fallback_discovery_keeps_three_field_route(self):
        self.discover('fallback')
        self.assertEqual(self.ad.discovered_boot('locate_fallback','fallback',{}), '22222222-2222-3333-4444-555555555555')

    def test_recovery_policy_requires_full_contract_and_all_existing_health_flags(self):
        proof = dict(identity=dict(self.identity), mode='target', state_sha256=self.c.HEALTHY,
                     authenticated=True, physical_guards_passed=True, current_boot_healthy=True, readiness_boot_bound=True)
        results = dict(locate_fallback=proof, observe_target=dict(identity=dict(self.identity)))
        call=lambda:self.ad.policy('stage_target_recovery',results,{'request_source_reboot'},contract=self.contract,owner=OWNER)
        call()
        for field in ('authenticated','physical_guards_passed','current_boot_healthy','readiness_boot_bound'):
            proof[field]=False; self.rejected(call); proof[field]=True
        for field in self.identity:
            old=proof['identity'][field]; proof['identity'][field]='x'; self.rejected(call); proof['identity'][field]=old
        results['observe_target']['identity']['descriptor_sha256']='f'*64
        self.rejected(call, 'target recovery boot changed')

    def test_early_health_and_restoration_boot_paths_require_identity6(self):
        for phase, prior in (('post_capture_health','observe_target'),('verify_target_restoration','restore_target_state')):
            results={prior:dict(identity=dict(self.identity))}
            self.assertEqual(self.ad.discovered_boot(phase,'target',results,contract=self.contract,owner=OWNER),BOOT)
            results[prior]['identity'].pop('owner')
            self.rejected(lambda:self.ad.discovered_boot(phase,'target',results,contract=self.contract,owner=OWNER))

    def test_actual_session_health_script_matches_actual_command_policy(self):
        requests=[]
        def stop_transport(request, deployed): requests.append(request); raise StopEffect()
        self.g.T.W=NS(request=json.loads,load_deployed=noop,perform=stop_transport)
        self.g.T.SOURCE=self.source; self.g.save=lambda *args:None
        self.g.OUTPUT.mkdir()
        owner=NS(base=noop,target=dict(self.identity),admission=dict(owner=OWNER),contract=self.contract)
        with self.assertRaises(StopEffect):self.g.collect_health(owner,'api-health')
        req,=requests
        self.ad.OUTPUT.mkdir(parents=True,exist_ok=True)
        pin='4'*64
        (self.ad.OUTPUT/'post_capture_health-health-entered.json').write_text(json.dumps(
            dict(intent_sha256=pin,script_sha256=sha(req['script'].encode()),read_only=True,mode='normal')))
        results=dict(observe_target=dict(identity=dict(self.identity)))
        call=lambda:self.ad.command_policy('post_capture_health',dict(owner=OWNER),results,pin,req,self.source,
                                          contract=self.contract,owner=OWNER)
        self.assertTrue(call())
        req['script']+='\n# changed\n'; self.rejected(call, 'health command differs')
        req['script']=req['script'].removesuffix('\n# changed\n')
        for contract, owner in ((None,OWNER),(self.contract,None),(self.contract,'b'*32)):
            self.rejected(lambda:self.ad.command_policy('post_capture_health',dict(owner=OWNER),results,pin,req,self.source,
                                                       contract=contract,owner=owner))

    def test_phase_and_transport_forward_the_same_object(self):
        seen=[]
        with patch.object(self.ad,'common',lambda *args:dict(host_source=self.source)), \
             patch.object(self.ad,'history',lambda *args,**kwargs:seen.append(kwargs)):
            self.ad.phase('observe_target',dict(owner=OWNER),{},contract=self.contract,owner=OWNER)
        self.assertIs(seen[0]['contract'],self.contract); self.assertEqual(seen[0]['owner'],OWNER)
        with patch.object(self.ad,'phase',lambda *args,**kwargs:(seen.append(kwargs) or dict(host_source=self.source))), \
             patch.object(self.ad,'command_policy',lambda *args,**kwargs:seen.append(kwargs)):
            self.ad.transport_authorize('observe_target',dict(owner=OWNER),{},'pin',{},contract=self.contract,owner=OWNER)
        for kwargs in seen:self.assertIs(kwargs['contract'],self.contract)
        with patch.object(self.ad,'common',lambda *args:self.effects.append('common')):
            self.rejected(lambda:self.ad.phase('observe_target',dict(owner='b'*32),{},contract=self.contract,owner=OWNER))

    def test_actual_launcher_session_call_reaches_unchanged_initialization_not_typeerror(self):
        tree=ast.parse((ARGS.callers/'trial-launcher.py.txt').read_bytes())
        call,=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
               and isinstance(n.func.value,ast.Name) and n.func.value.id=='G' and n.func.attr=='run']
        namespace=dict(G=self.g,AD=self.ad,controller=None,credentials=None,trial=None,contract=self.contract)
        self.rejected(lambda:eval(compile(ast.Expression(body=call),'<actual-session-call>','eval'),namespace),
                      'unresolved source dependency')

    def test_actual_status_gate_new_success_legacy_and_failures(self):
        tree=ast.parse((ARGS.callers/'trial-launcher.py.txt').read_bytes())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_run_once')
        node=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='result' for t in n.targets))
        expression=next(k.value for k in node.value.keywords if k.arg=='status')
        code=compile(ast.Expression(body=expression),'<actual-status>','eval')
        base=dict(trial=dict(status='COMPONENT_PASS'),gpu=dict(status='PASS_PRODUCTION_DISPLAY_SESSION'),error=None,cleanup=[])
        self.assertEqual(eval(code,base),'COMPONENT_PASS')
        original = ast.parse((ARGS.before/'trial-launcher.py.txt').read_bytes())
        old_fn = next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='_run_once')
        old_result = next(n for n in old_fn.body if isinstance(n,ast.Assign)
                          and any(isinstance(t,ast.Name) and t.id=='result' for t in n.targets))
        old_status = next(k.value for k in old_result.value.keywords if k.arg=='status')
        self.assertEqual(eval(compile(ast.Expression(body=old_status), '<actual-old-status>', 'eval'), base), 'FAIL')
        for change in (dict(gpu=dict(status='PASS_GPU_INITIALIZATION_SESSION')),dict(trial=None),dict(gpu=None),dict(error={}),dict(cleanup=['failure'])):
            self.assertEqual(eval(code,dict(base,**change)),'FAIL')

    def test_actual_assembly_captures_contract_in_all_ordinary_callbacks(self):
        loaded={}; seen=[]
        class Transport:
            def __init__(self, gate): self.perform=gate
        class Bridge:
            def __init__(self, gate): self.gate=gate
        def driver(source, before, enter, bridge, *, transport):
            return NS(before=before, enter=enter, transport=transport)
        for name in ('capture-bridge.py','fallback-transport.py'):
            directory=self.root/'gpu-iommu-capture-r1' if name=='capture-bridge.py' else Path(self.ad.__file__).parent
            directory.mkdir(exist_ok=True); path=directory/name; path.write_bytes(b'inert import fixture\n')
            loaded[str(path)]=NS(Transport=Transport,Bridge=Bridge,OUTPUT=self.ad.OUTPUT)
            self.value['files'][str(path.relative_to(self.root))]=dict(size=path.stat().st_size,uid=1000,mode=0o644,sha256=sha(path.read_bytes()))
        self.lock_bytes(json.dumps(self.value).encode())
        util=NS(spec_from_file_location=lambda name,path:NS(path=str(path),loader=NS(exec_module=noop)),
                module_from_spec=lambda spec:loaded[spec.path])
        self.ad.importlib=NS(util=util); self.ad.HERE=Path(self.ad.__file__).parent
        self.ad.B=NS(expected_fields=lambda:{'fixture':'claim'})
        self.ad.D.OUTPUT=self.ad.OUTPUT; self.ad.D.Driver=driver
        with patch.object(self.ad,'claim',lambda:{'fixture':'claim'}), \
             patch.object(self.ad,'qualification',lambda source:'fixture-qualification'), \
             patch.object(self.ad,'before_phase',lambda *a,**kw:seen.append(kw)), \
             patch.object(self.ad,'authorize',lambda *a,**kw:seen.append(kw)), \
             patch.object(self.ad,'transport_authorize',lambda *a,**kw:seen.append(kw)):
            actual, bridge=self.ad.assemble(self.source,contract=self.contract,owner=OWNER)
            actual.before(); actual.enter(); actual.transport()
        self.assertEqual(len(seen),3)
        for kwargs in seen:
            self.assertIs(kwargs['contract'],self.contract); self.assertEqual(kwargs['owner'],OWNER)
        with patch.object(self.ad,'inputs',lambda:self.effects.append('inputs')):
            self.rejected(lambda:self.ad.assemble(self.source), 'binding required')

    def test_actual_run_once_rechecks_after_authentication_before_claim(self):
        saved=[]
        api=self
        class Credentials:
            def __init__(self, path): self.started=time.monotonic()
            def __enter__(self):
                api.contract._binding['descriptor_sha256']='f'*64
                return self
            def __exit__(self,*args):return False
        self.l.K=NS(Credentials=Credentials)
        self.c.save=lambda path,value:(saved.append(path.name) or sha(json.dumps(value).encode()))
        self.ad.PREP.prior_and_staging=noop
        with patch.object(self.g,'initialize',noop), \
             patch.object(self.ad,'qualification',lambda source:'fixture-qualification'), \
             patch.object(self.l,'registered_claim',lambda:{'fixture':'claim'}), \
             patch.object(self.l,'pending_claim',noop):
            result=self.l._run_once(contract=self.contract,owner=OWNER)
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('health seal differs',result['error']['reason'])
        self.assertFalse(result['claim_consumption_entered'])
        self.assertNotIn('claim-consumption-entered.json',saved)
        self.assertEqual(self.effects,[])

    def test_original_signature_counterexamples_still_detect_old_callers(self):
        for filename, root, attr, namespace in (
            ('trial-launcher.py.txt','G','run',dict(G=self.g,AD=self.ad,controller=None,credentials=None,trial=None)),
            ('live-admission.py.txt','H.H','script',dict(H=NS(H=self.h),boot=BOOT)),
        ):
            tree=ast.parse((ARGS.before/filename).read_bytes())
            call,=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                   and ast.unparse(n.func.value)==root and n.func.attr==attr]
            with self.assertRaisesRegex(TypeError,'contract'):
                eval(compile(ast.Expression(body=call),'<actual-old-call>','eval'),namespace)

    def old_admission_function(self, name):
        path = ARGS.before/'live-admission.py.txt'
        node, = [n for n in ast.parse(path.read_bytes()).body
                 if isinstance(n, ast.FunctionDef) and n.name == name]
        namespace = dict(self.ad.__dict__)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        return namespace[name]

    def test_original_authenticated_scope_schema_fails_before_repair(self):
        original = self.old_admission_function('inputs')
        self.rejected(original, 'input lock schema')
        self.assertEqual(self.ad.inputs(), self.value)

    def test_original_full_discovery_fails_with_successor_identity(self):
        self.discover()
        original = self.old_admission_function('discovered_boot')
        prior = dict(observe_target=dict(identity=copy.deepcopy(self.identity)))
        self.rejected(lambda:original('locate_fallback', 'target', prior), 'target recovery boot changed')
        self.assertEqual(self.ad.discovered_boot('locate_fallback', 'target', prior,
                         contract=self.contract, owner=OWNER), BOOT)

    def test_unchanged_private_guards_and_decoder_delegation(self):
        groups={
            'live-admission.py.txt':('common','claim','qualification','digest_file','stamp','results_for',
                                    'authorize_transport','capture_launch_authorize','authorize_capture'),
            'trial-launcher.py.txt':('load','registered_claim','pending_claim','record','Driver','close_owned','closed_authentication_attempts'),
        }
        for filename,names in groups.items():
            old=ast.parse((ARGS.before/filename).read_bytes()); new=ast.parse((ARGS.callers/filename).read_bytes())
            for name in names:
                def node(tree):return next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
                self.assertEqual(ast.dump(node(old)),ast.dump(node(new)),name)
        tree=ast.parse((ARGS.callers/'live-admission.py.txt').read_bytes())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='inputs')
        self.assertIn('input_schema(A.decode(raw))',ast.unparse(fn))
        self.assertLess(ast.unparse(fn).index('A.sha(raw) == INPUTS_SHA'),ast.unparse(fn).index('input_schema(A.decode(raw))'))
        # All original literal hash assignments remain unchanged in both callers.
        for filename in groups:
            def pins(path):
                return {t.id:ast.literal_eval(n.value) for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.Assign)
                        for t in n.targets if isinstance(t,ast.Name) and t.id.endswith('_SHA')}
            self.assertEqual(pins(ARGS.before/filename),pins(ARGS.callers/filename))


if __name__ == '__main__':
    unittest.main(argv=[__file__,*REST],verbosity=2)
