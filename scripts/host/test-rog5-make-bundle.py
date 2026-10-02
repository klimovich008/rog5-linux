#!/usr/bin/env python3
"""Offline tests of the bundle naming, the registries and rog5-make-bundle.py.

The build runs end to end against a throwaway git repository whose three build
scripts are fakes (module packager, ramdisk builder, signer/packager) that
record what they were given; nothing is signed and no phone is involved.
"""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REG = load('rog5_bundle_registry_test', REPO/'scripts/host/rog5-bundle-registry.py')
MB = load('rog5_make_bundle_test', REPO/'scripts/host/rog5-make-bundle.py')
MB.MIN_FREE = 0  # the fixture is a few bytes in a small TMPDIR
KEY_TEXT = 'FAKE SIGNING KEY CONTENT 7f3a'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def newc(members):
    out = b''
    for index, (name, data) in enumerate(members + [('TRAILER!!!', b'')]):
        raw = name.encode()+b'\0'
        mode = 0o100644 if name != 'TRAILER!!!' else 0
        fields = [index+1, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(raw), 0]
        header = b'070701'+b''.join(b'%08x' % f for f in fields)
        out += header+raw
        out += b'\0'*((-len(out)) % 4)+data
        out += b'\0'*((-len(out)) % 4)
    return gzip.compress(out, mtime=0)


FAKE_MODULES = r'''#!/usr/bin/env python3
import argparse, hashlib, io, json, os, sys, tarfile
from pathlib import Path
p = argparse.ArgumentParser(); p.add_argument('--build'); p.add_argument('--output'); a = p.parse_args()
build = Path(a.build); out = Path(a.output); out.mkdir()
r = json.loads((build/'result.json').read_text())
installed = build/'modules/lib/modules'/r['release']
pkg = out/'module-root-complete.tar.gz'
members = {'lib/modules/%s/kernel/%s' % (r['release'], q.relative_to(installed/'kernel')): q.read_bytes()
           for q in sorted((installed/'kernel').rglob('*.ko'))}
members['lib/modules/%s/kernel/fake-ext.ko' % r['release']] = os.environ.get('FAKE_EXTERNAL', 'external').encode()
members['lib/modules/%s/modules.dep' % r['release']] = b'dep'
with tarfile.open(pkg, 'w:gz') as t:
    for name, data in members.items():
        info = tarfile.TarInfo(name); info.size = len(data); t.addfile(info, io.BytesIO(data))
h = lambda b: hashlib.sha256(b).hexdigest()
repo = Path(__file__).resolve().parents[2]
json.dump(dict(status='PASS_UNSIGNED_MODULE_PACKAGE', release=r['release'], kernel_build=str(build),
    kernel_image_sha256=h((build/'objects/arch/arm64/boot/Image').read_bytes()), package_sha256=h(pkg.read_bytes()),
    external_modules=['fake-ext.ko'],
    selection_sha256=h((repo/'configs/kernel/rog5-production-modules.json').read_bytes())), open(out/'result.json', 'w'))
'''


def module_tar(release, members):
    import tarfile
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(f'lib/modules/{release}/kernel/{name}')
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()

FAKE_RAMDISK = r'''#!/bin/sh
exec python3 - "$@" <<'EOF'
import gzip, hashlib, json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ['FAKE_HELPERS'])
from fakehelpers import newc
base, output = sys.argv[1], Path(sys.argv[2])
assert not output.exists()
env = {k: v for k, v in os.environ.items() if k.startswith(('PRODUCTION_', 'EXPECTED_', 'UFS_', 'PERSISTENT_'))}
repo = Path.cwd()
env['boot_modules'] = (repo/'configs/production/boot-modules.list').read_text()
Path(os.environ['FAKE_LOG']).write_text(json.dumps(env))
members = [('init', b'#!/bin/sh\nexpected_kernel_release=' + env['EXPECTED_RELEASE'].encode() + b'\nrestoring-v2\n')]
descriptor = env.get('PRODUCTION_TRIAL_DESCRIPTOR')
if descriptor and not os.environ.get('FAKE_DROP_DESCRIPTOR'):
    data = Path(descriptor).read_bytes()
    assert hashlib.sha256(data).hexdigest() == env['PRODUCTION_TRIAL_DESCRIPTOR_SHA256']
    members.append(('rog5-production-trial/trial-descriptor', data))
output.write_bytes(newc(members))
EOF
'''

FAKE_PACKAGE = r'''#!/usr/bin/env python3
import argparse, hashlib, json, os
from pathlib import Path
p = argparse.ArgumentParser()
for n in ('image', 'dtb', 'initramfs', 'recovery-base', 'asus-template', 'asus-kernel'):
    p.add_argument('--'+n); p.add_argument('--'+n+'-sha256')
for n in ('private-key', 'release', 'bundle', 'output'):
    p.add_argument('--'+n)
a = p.parse_args()
if os.environ.get('FAKE_SET_DURING'):
    import subprocess
    subprocess.run(os.environ['FAKE_SET_DURING'].split('|'), check=True)
h = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
for n in ('image', 'dtb', 'initramfs', 'recovery_base', 'asus_template', 'asus_kernel'):
    assert h(getattr(a, n)) == getattr(a, n+'_sha256'), n
out = Path(a.output); out.mkdir(); b = out/'bundles'/a.bundle; b.mkdir(parents=True)
for n, src in (('Image', a.image), ('board.dtb', a.dtb), ('initramfs.cpio.gz', a.initramfs)):
    (b/n).write_bytes(Path(src).read_bytes())
(b/'manifest').write_text('bundle='+a.bundle+'\ntarget_release='+a.release+'\n'); (b/'manifest.sig').write_bytes(b'sig')
(out/'boot-ram-128m.img').write_bytes(b'wrapper')
(out/'commands.log').write_text('--private-key '+a.private_key+'\n')
(out/'environment.json').write_text(json.dumps(sorted(os.environ)))
json.dump(dict(status='PASS_PACKAGED_UNBOOTED', bundle=a.bundle, release=a.release, manifest_sha256=h(b/'manifest'),
    wrapper=dict(sha256=h(out/'boot-ram-128m.img')),
    inputs={n: dict(path=getattr(a, n), sha256=h(getattr(a, n))) for n in ('image', 'dtb', 'initramfs')}),
    open(out/'result.json', 'w'))
'''


class Fixture:
    def __init__(self, root):
        self.root = root
        self.state = root/'state'
        self.kernels = root/'kernels'
        self.source = root/'source'
        self.config = root/'config'
        self.doc = root/'bundles.md'
        self.log = root/'ramdisk-env.json'
        for d in (self.state, self.kernels, self.source, self.config):
            d.mkdir()
        helpers = root/'helpers'
        helpers.mkdir()
        (helpers/'fakehelpers.py').write_text(
            'import gzip\n' + ''.join(__import__('inspect').getsource(f) for f in (newc,)))
        self.env = dict(FAKE_HELPERS=str(helpers), FAKE_LOG=str(self.log))
        # Source repository with the fake build scripts.
        for rel, text in (('scripts/host/package-production-modules.py', FAKE_MODULES),
                          ('scripts/device/build-persistent-root-standalone-initramfs.sh', FAKE_RAMDISK),
                          ('scripts/host/package-production-ram-trial.py', FAKE_PACKAGE),
                          ('configs/kernel/rog5-production-modules.json',
                           '{"board_modules": ["drivers/board.ko"], "external_modules": [{"name": "fake-ext", "source": "tools/fake"}]}\n'),
                          ('tools/fake/fake.c', 'int x;\n'),
                          ('configs/production/boot-modules.list', 'old_module\n')):
            path = self.source/rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git = ['git', '-C', str(self.source), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git[:3]+['init', '-q'], check=True)
        subprocess.run(git+['add', '-A'], check=True)
        subprocess.run(git+['commit', '-qm', 'old list'], check=True)
        self.old_rev = subprocess.run(git[:3]+['rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        (self.source/'configs/production/boot-modules.list').write_text('old_module\ntcpci_rt1711h\n')
        subprocess.run(git+['commit', '-qam', 'new list'], check=True)
        (self.source/'artifacts').mkdir()
        # Kernel builds: k111 labelled, k69 legacy.
        self.kernel(111, '7.2.7-rog5-k111', 'k111')
        self.kernel(69, '7.2.7-rog5-production', None)
        # DTB registry pointing at the state directory.
        dtb_dir = self.state/'platform-test-dtb-r9'
        dtb_dir.mkdir()
        (dtb_dir/'board.dtb').write_bytes(b'dtb nine')
        registry = json.loads((REPO/'configs/production/dtbs.json').read_text())
        registry['root'] = str(self.state)
        registry['dtbs'] = {'d9': dict(path='platform-test-dtb-r9/board.dtb', sha256=sha(b'dtb nine'),
                                       features='touch,memx', base=None, created='2026-09-30',
                                       kernel_requires='', requires={}, notes='test')}
        (self.config/'dtbs.json').write_text(json.dumps(registry))
        bundles = dict(format='rog5-bundle-registry-v1', kernels={}, bundles=[])
        (self.config/'bundles.json').write_text(json.dumps(bundles))
        reg = REG.Registry(self.config, self.doc)
        REG.write_features(reg, 'd9')
        # Pinned inputs.
        files = {}
        for name in ('ramdisk_base', 'recovery_base', 'asus_template', 'asus_kernel'):
            path = root/'pins'/name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(name.encode())
            files[name] = dict(path=str(path), sha256=sha(name.encode()))
        for name in ('extra_firmware', 'wifi_kit'):
            path = self.state/name
            path.mkdir()
            (path/'SHA256SUMS').write_text(name)
            files[name] = dict(path='{state}/'+name, sums_sha256=sha(name.encode()))
        self.key = root/'key.pem'
        self.key.write_text(KEY_TEXT)
        self.inputs = root/'inputs.json'
        self.inputs.write_text(json.dumps(dict(format='rog5-bundle-inputs-v1', state_dir=str(self.state),
            kernel_builds=str(self.kernels), trust_key=dict(path='{state}/trust-key.raw', sha256='0'*64),
            signing_key=str(self.key), ramdisk_env=dict(UFS_CONTAINMENT='off', PERSISTENT_ROOT_OVERLAY='1',
                                                          PRODUCTION_UPDATE_KIT='1'), **files)))

    def kernel(self, number, release, label, status='PASS', provenance=True, patches=('0001-a.patch', '0148-b.patch'),
               config='CONFIG_X=y\n'):
        build = self.kernels/f'rog5-kernel-7.2.7-build-r{number}'
        image = build/'objects/arch/arm64/boot/Image'
        image.parent.mkdir(parents=True)
        image.write_bytes(b'Image '+release.encode())
        (build/'objects/.config').write_text(config)
        outputs = {'objects/arch/arm64/boot/Image': sha(image.read_bytes()),
                   'objects/.config': sha(config.encode())}
        if provenance:
            module = build/'modules/lib/modules'/release/'kernel/drivers/board.ko'
            module.parent.mkdir(parents=True)
            module.write_bytes(b'board module of '+release.encode())
            entries = [dict(path=f'modules/lib/modules/{release}/kernel/drivers/board.ko',
                            sha256=sha(module.read_bytes()), name='board', vermagic=release+' SMP')]
            (build/'module-provenance.json').write_text(json.dumps(entries))
            outputs['module-provenance.json'] = sha((build/'module-provenance.json').read_bytes())
        result = dict(status=status, release=release, started='2026-10-01T09:00:00',
                      stages={'kernel-build': dict(status='PASS'), 'modules-install': dict(status='PASS')},
                      outputs=outputs,
                      ordered_series=dict(production=[dict(name=name) for name in patches]),
                      repository=dict(commit='abcdef1234567890', dirty=False))
        if label:
            result['release_label'] = label
        (build/'result.json').write_text(json.dumps(result))
        return build

    def args(self, *extra):
        return ['--state-dir', str(self.state), '--kernel-root', str(self.kernels), '--source-repo', str(self.source),
                '--inputs', str(self.inputs), '--config', str(self.config), '--doc', str(self.doc),
                '--date', '261001', *extra]

    def run(self, *extra, env=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        saved = dict(os.environ)
        os.environ.update(self.env, **(env or {}))
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                MB.main(self.args(*extra))
        finally:
            os.environ.clear()
            os.environ.update(saved)
        return stdout.getvalue()


class Naming(unittest.TestCase):
    def test_names_fit_the_loader_and_the_scheme(self):
        self.assertEqual(REG.bundle_name('main', 'k110', 'd9', '260930', 'a'), 'main-k110-d9-260930a')
        self.assertEqual(REG.bundle_name('safe', 'k69', 'd3', '260930', 'z'), 'safe-k69-d3-260930z')
        longest = REG.bundle_name('main', 'k9999', 'd9999', '991231', 'z')
        self.assertTrue(REG.loader_name_ok(longest))
        for bad in (('trial', 'k1', 'd1', '260930', 'a'), ('main', 'k0', 'd9', '260930', 'a'),
                    ('main', 'k110', 'd09', '260930', 'a'), ('main', 'k110', 'd9', '2609301', 'a'),
                    ('main', 'k110', 'd9', '260930', 'A'), ('main', '110', 'd9', '260930', 'a'),
                    ('main', 'k10000', 'd9', '260930', 'a')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                REG.bundle_name(*bad)
        for bad in ('Main-k1', '-a', 'a..b', 'a/b', 'x'*65):
            self.assertFalse(REG.loader_name_ok(bad))


class Registries(unittest.TestCase):
    def test_committed_registries_validate_and_the_document_is_current(self):
        registry = REG.Registry()
        self.assertTrue(registry.validate())
        self.assertEqual(registry.doc.read_text(), REG.render(registry),
                         'docs/bundles.md is stale: python3 scripts/host/rog5-bundle-registry.py render')
        main = [b for b in registry.bundles if b['status'] == 'installed-main']
        self.assertEqual(len(main), 1)
        for entry in registry.dtbs['dtbs'].values():
            self.assertEqual(Path(entry['path']).name, 'board.dtb')

    def test_private_dtb_files_match_the_registry_when_present(self):
        registry = REG.Registry()
        checked = 0
        for ident in registry.dtbs['dtbs']:
            if registry.dtb(ident)[0].exists():
                registry.verify_dtb(ident)
                checked += 1
        if not checked:
            self.skipTest('private DTB directory not present')

    def test_validation_rejects_inconsistent_entries(self):
        base = REG.Registry()
        cases = {
            'duplicate': lambda r: r.bundles.append(dict(r.bundles[-1])),
            'unknown kernel': lambda r: r.bundles[-1].update(kernel='k999'),
            'unknown dtb': lambda r: r.bundles[-1].update(dtb='d999'),
            'status': lambda r: r.bundles[-1].update(status='fine'),
            'two mains': lambda r: [b.update(status='installed-main') for b in r.bundles[-2:]],
            'scheme mismatch': lambda r: r.bundles[-1].update(name='main-k110-d8-260930a'),
            'loader name': lambda r: r.bundles[-1].update(name='Main..x'),
            'release': lambda r: r.bundles[-1].update(release='7.2.7-rog5-k1'),
            'dtb path': lambda r: r.dtbs['dtbs']['d9'].update(path='../x/board.dtb'),
            'requires missing': lambda r: r.dtbs['dtbs']['d9'].pop('requires'),
            'unknown patch': lambda r: r.dtbs['dtbs']['d9'].update(requires=dict(patches=['0999-none.patch'])),
            'patch name': lambda r: r.dtbs['dtbs']['d9'].update(requires=dict(patches=['0136'])),
            'config value': lambda r: r.dtbs['dtbs']['d15']['requires']['config'].update(CONFIG_SM_VIDEOCC_8350='n'),
            'requires key': lambda r: r.dtbs['dtbs']['d9'].update(requires=dict(modules=['iris'])),
            'base cycle': lambda r: r.dtbs['dtbs']['d7'].update(base='d9'),
        }
        for label, mutate in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                registry = REG.Registry()
                registry.data = json.loads(json.dumps(base.data))
                registry.dtbs = json.loads(json.dumps(base.dtbs))
                mutate(registry)
                with self.assertRaises(ValueError):
                    registry.validate()

    def test_committed_dtb_requirements_reject_an_incompatible_kernel(self):
        # d13 inherits 0136-0139, 0144 and 0146 from d8 through d10/d9 (its own
        # entry is empty): a kernel without them is refused, k113's series passes.
        registry = REG.Registry()
        patches, config = registry.requirements('d13')
        self.assertEqual([name[:4] for name in patches],
                         ['0089', '0121', '0122', '0123', '0124', '0136', '0137', '0138', '0139', '0144', '0146'])
        self.assertEqual(config, {})
        series = sorted(path.name for path in (REPO/'patches/linux-7.2.7').glob('0*.patch')
                        if path.name[:4] <= '0153')
        full = dict(ordered_series=dict(production=[dict(name=name) for name in series]))
        registry.check_kernel('d13', 'k113', full, None)
        lacking = dict(ordered_series=dict(production=[dict(name=name) for name in series
                                                       if name[:4] not in ('0136', '0144', '0146')]))
        with self.assertRaisesRegex(ValueError, 'd13 needs kernel patches kX does not carry: 0136-.*0144-.*0146-'):
            registry.check_kernel('d13', 'kX', lacking, None)
        # d15 also needs the video config; a pruned build (no .config) cannot show it.
        with self.assertRaisesRegex(ValueError, 'needs .config symbols'):
            registry.check_kernel('d15', 'kX', dict(ordered_series=dict(production=[
                dict(name=name) for name in sorted(p.name for p in (REPO/'patches/linux-7.2.7').glob('0*.patch'))])),
                None)

    def test_set_retires_the_previous_installed_bundle_and_add_dtb_numbers_from_10(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Fixture(Path(tmp))
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
            cli = ['--config', str(f.config), '--doc', str(f.doc)]
            with contextlib.redirect_stdout(io.StringIO()):
                REG.main(cli+['set', 'main-k111-d9-261001a', '--status', 'installed-main', '--healthy', 'yes'])
                REG.main(cli+['set', 'main-k111-d9-261001b', '--status', 'installed-main', '--healthy', 'yes'])
            registry = REG.Registry(f.config, f.doc)
            self.assertEqual([b['status'] for b in registry.bundles], ['retired', 'installed-main'])
            new = f.state/'platform-test-dtb-r10'
            new.mkdir()
            (new/'board.dtb').write_bytes(b'dtb ten')
            with contextlib.redirect_stdout(io.StringIO()):
                REG.main(cli+['add-dtb', '--dtb', str(new/'board.dtb'), '--features', 'touch,memx,l11off', '--base', 'd9'])
            registry = REG.Registry(f.config, f.doc)
            self.assertEqual(registry.dtbs['dtbs']['d10']['sha256'], sha(b'dtb ten'))
            registry.verify_dtb('d10')
            self.assertIn('id=d10\n', (new/'features').read_text())
            with self.assertRaises(ValueError), contextlib.redirect_stdout(io.StringIO()):
                REG.main(cli+['add-dtb', '--dtb', str(new/'board.dtb'), '--features', 'touch'])
            self.assertEqual(f.doc.read_text(), REG.render(registry))


class MakeBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Fixture(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_main_bundle_end_to_end(self):
        f = self.f
        # An inherited descriptor or release must never reach the ramdisk builder.
        out = f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', '--changes', '0148 test',
                    env=dict(EXPECTED_RELEASE='7.2.7-rog5-production', PRODUCTION_WIFI_KIT='/elsewhere'))
        name = 'main-k111-d9-261001a'
        self.assertIn('PASS '+name, out)
        package = f.state/('package-'+name)
        record = json.loads((package/'make-bundle.json').read_text())
        env = json.loads(f.log.read_text())
        self.assertEqual(env['EXPECTED_RELEASE'], '7.2.7-rog5-k111')
        self.assertEqual(env['PRODUCTION_WIFI_KIT'], str(f.state/'wifi_kit'))
        self.assertEqual(env['UFS_CONTAINMENT'], 'off')
        descriptor = f.state/('trial-'+name)/'descriptor'
        rows = descriptor.read_text().splitlines()
        self.assertEqual(rows[0], 'format=rog5-persistent-wifi-health-v1')
        self.assertRegex(rows[1], r'^trial_id=[0-9a-f]{64}$')
        self.assertEqual(rows[2:], ['primary_bundle='+name, 'mode=try-once'])
        self.assertEqual(env['PRODUCTION_TRIAL_DESCRIPTOR'], str(descriptor))
        self.assertEqual(env['boot_modules'], 'old_module\ntcpci_rt1711h\n')
        self.assertEqual(MB.newc_member((package/'bundles'/name/'initramfs.cpio.gz').read_bytes(),
                                        MB.DESCRIPTOR_MEMBER), descriptor.read_bytes())
        self.assertEqual(record['release'], '7.2.7-rog5-k111')
        self.assertEqual(record['module_package_source'], 'new')
        self.assertTrue((f.state/'modules-k111/module-root-complete.tar.gz').is_file())
        self.assertFalse((f.state/('bundle-work-'+name)/'src').exists())
        registry = REG.Registry(f.config, f.doc)
        entry = registry.bundle(name)
        self.assertEqual((entry['status'], entry['healthy'], entry['kernel'], entry['dtb'], entry['changes']),
                         ('built', 'unknown', 'k111', 'd9', '0148 test'))
        self.assertEqual(registry.kernels['k111']['release'], '7.2.7-rog5-k111')
        self.assertEqual(f.doc.read_text(), REG.render(registry))
        # The key is passed as a path; its bytes appear in no output or log.
        for path in list(f.state.rglob('*'))+[f.config/'bundles.json', f.doc]:
            if path.is_file():
                self.assertNotIn(KEY_TEXT.encode(), path.read_bytes(), path)
        self.assertNotIn(KEY_TEXT, out)
        # Same day, same inputs: the next free letter, a fresh trial id, the module package reused.
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        second = f.state/'trial-main-k111-d9-261001b'/'descriptor'
        self.assertNotEqual(second.read_text().splitlines()[1], rows[1])
        self.assertEqual(json.loads((f.state/'package-main-k111-d9-261001b/make-bundle.json').read_text())
                         ['module_package_source'], 'reused')

    def test_a_status_change_during_a_build_is_kept(self):
        f = self.f
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        during = ['python3', str(REPO/'scripts/host/rog5-bundle-registry.py'), '--config', str(f.config),
                  '--doc', str(f.doc), 'set', 'main-k111-d9-261001a', '--status', 'installed-main', '--healthy', 'yes']
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', env=dict(FAKE_SET_DURING='|'.join(during)))
        registry = REG.Registry(f.config, f.doc)
        self.assertEqual([(b['name'], b['status']) for b in registry.bundles],
                         [('main-k111-d9-261001a', 'installed-main'), ('main-k111-d9-261001b', 'built')])
        self.assertEqual(f.doc.read_text(), REG.render(registry))

    def test_safe_bundle_has_no_descriptor_and_the_older_module_list(self):
        f = self.f
        f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--boot-modules-from', f.old_rev,
              env=dict(PRODUCTION_TRIAL_DESCRIPTOR='/tmp/leak', PRODUCTION_TRIAL_DESCRIPTOR_SHA256='0'*64))
        name = 'safe-k69-d9-261001a'
        env = json.loads(f.log.read_text())
        self.assertNotIn('PRODUCTION_TRIAL_DESCRIPTOR', env)
        self.assertEqual(env['EXPECTED_RELEASE'], '7.2.7-rog5-production')
        self.assertEqual(env['boot_modules'], 'old_module\n')
        self.assertFalse((f.state/('trial-'+name)).exists())
        self.assertIsNone(MB.newc_member((f.state/('package-'+name)/'bundles'/name/'initramfs.cpio.gz').read_bytes(),
                                         MB.DESCRIPTOR_MEMBER))
        entry = REG.Registry(f.config, f.doc).bundle(name)
        self.assertEqual((entry['role'], entry['status']), ('safe', 'built'))
        self.assertIn('boot-modules.list from '+f.old_rev[:12], entry['notes'])

    def prune_k69_with_a_registered_copy(self):
        f = self.f
        build = f.kernels/'rog5-kernel-7.2.7-build-r69'
        image = (build/'objects/arch/arm64/boot/Image').read_bytes()
        shutil.rmtree(build/'objects')
        copy = f.state/'package-7.2.7-safe-r8/bundles/production-7.2.7-safe-r8/Image'
        copy.parent.mkdir(parents=True)
        copy.write_bytes(image)
        data = json.loads((f.config/'bundles.json').read_text())
        data['kernels']['k69'] = dict(build=build.name, release='7.2.7-rog5-production', image_sha256=sha(image))
        data['bundles'].append(dict(name='production-7.2.7-safe-r8', role='safe', kernel='k69', dtb='d9',
                                    release='7.2.7-rog5-production', manifest_sha256='2'*64,
                                    package='package-7.2.7-safe-r8', status='installed-fallback', healthy='yes'))
        (f.config/'bundles.json').write_text(json.dumps(data))
        return build, image, copy

    def test_legacy_module_package_is_reused_only_for_a_pruned_build(self):
        f = self.f
        legacy = f.state/'modules-7.2.7-r69'
        build = f.kernels/'rog5-kernel-7.2.7-build-r69'
        legacy.mkdir()
        (legacy/'module-root-complete.tar.gz').write_bytes(b'legacy')
        result = dict(status='PASS_UNSIGNED_MODULE_PACKAGE', release='7.2.7-rog5-production', kernel_build=str(build),
                      kernel_image_sha256=sha((build/'objects/arch/arm64/boot/Image').read_bytes()),
                      package_sha256=sha(b'legacy'), selection_sha256='1'*64)
        (legacy/'result.json').write_text(json.dumps(result))
        # The build can still be packaged: an unverified legacy package is not used.
        self.assertIn('modules modules-k69 (new)', f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9',
                                                         '--boot-modules-from', f.old_rev))
        # A package this tool made would still win after pruning; drop it to reach the legacy one.
        shutil.rmtree(f.state/'modules-k69')
        self.prune_k69_with_a_registered_copy()
        # An old build that recorded no module provenance: the legacy package
        # stays usable, explicitly unverified.
        built = json.loads((build/'result.json').read_text())
        del built['outputs']['module-provenance.json']
        (build/'result.json').write_text(json.dumps(built))
        out = f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--boot-modules-from', f.old_rev)
        self.assertIn('modules modules-7.2.7-r69 (reused-unverified)', out)
        self.assertIn('differs from HEAD', out)
        record = json.loads((f.state/'package-safe-k69-d9-261001b/make-bundle.json').read_text())
        self.assertEqual((record['module_package_sha256'], record['module_package_source']),
                         (sha(b'legacy'), 'reused-unverified'))
        self.assertFalse(record['module_selection_current'])
        self.assertIn('legacy module package modules-7.2.7-r69 (module provenance not verified)',
                      REG.Registry(f.config, f.doc).bundle('safe-k69-d9-261001b')['notes'])
        self.assertEqual(record['module_provenance']['status'], 'unverified')
        result['kernel_build'] = str(f.kernels/'rog5-kernel-7.2.7-build-r111')
        (legacy/'result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'not a module package'):
            f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--boot-modules-from', f.old_rev)

    def test_legacy_package_of_a_pruned_build_is_checked_against_its_provenance(self):
        # The real safe-r8 recipe: k69's objects are gone, modules-7.2.7-r69 is
        # reused, and k69 still records module provenance.
        f = self.f
        build = f.kernels/'rog5-kernel-7.2.7-build-r69'
        release = '7.2.7-rog5-production'
        board = (build/'modules/lib/modules'/release/'kernel/drivers/board.ko').read_bytes()
        legacy = f.state/'modules-7.2.7-r69'
        legacy.mkdir()
        image_sha = sha((build/'objects/arch/arm64/boot/Image').read_bytes())
        self.prune_k69_with_a_registered_copy()

        def legacy_package(members):
            data = module_tar(release, members)
            (legacy/'module-root-complete.tar.gz').write_bytes(data)
            (legacy/'result.json').write_text(json.dumps(dict(
                status='PASS_UNSIGNED_MODULE_PACKAGE', release=release, kernel_build=str(build),
                kernel_image_sha256=image_sha, package_sha256=sha(data), selection_sha256='1'*64,
                external_modules=['fake-ext.ko'])))
        legacy_package({'drivers/board.ko': board, 'fake-ext.ko': b'ext'})
        out = f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--boot-modules-from', f.old_rev)
        self.assertIn('module provenance verified (1 board modules)', out)
        record = json.loads((f.state/'package-safe-k69-d9-261001a/make-bundle.json').read_text())
        self.assertEqual(record['module_provenance']['status'], 'verified')
        self.assertNotIn('not verified', REG.Registry(f.config, f.doc).bundle('safe-k69-d9-261001a')['notes'])
        for members, message in (({'drivers/board.ko': b'rebuilt', 'fake-ext.ko': b'ext'}, 'differs from'),
                                 ({'drivers/board.ko': board, 'drivers/extra.ko': b'x', 'fake-ext.ko': b'ext'},
                                  'no provenance record'),
                                 ({'drivers/board.ko': board}, 'external modules differ')):
            with self.subTest(message=message):
                legacy_package(members)
                with self.assertRaisesRegex(ValueError, message):
                    f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--boot-modules-from', f.old_rev)

    def test_module_provenance_is_enforced_for_new_and_reused_packages(self):
        f = self.f
        build = f.kernels/'rog5-kernel-7.2.7-build-r111'
        self.assertIn('module provenance verified', f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9'))
        # Provenance edited to match a replaced module: result.json binds the file.
        provenance = build/'module-provenance.json'
        original = provenance.read_bytes()
        entries = json.loads(original)
        entries[0]['sha256'] = sha(b'replaced module')
        provenance.write_text(json.dumps(entries))
        with self.assertRaisesRegex(ValueError, 'module-provenance.json differs from result.json'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        provenance.write_bytes(original)
        # A reused package whose board module differs from the provenance.
        package_dir = f.state/'modules-k111'
        result = json.loads((package_dir/'result.json').read_text())
        data = module_tar('7.2.7-rog5-k111', {'drivers/board.ko': b'tampered', 'fake-ext.ko': b'external'})
        (package_dir/'module-root-complete.tar.gz').write_bytes(data)
        result['package_sha256'] = sha(data)
        (package_dir/'result.json').write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'drivers/board.ko differs from'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        # A build without recorded provenance cannot get a new package.
        built = json.loads((build/'result.json').read_text())
        del built['outputs']['module-provenance.json']
        (build/'result.json').write_text(json.dumps(built))
        with self.assertRaisesRegex(ValueError, 'records no module provenance'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', '--fresh-modules')

    def test_package_inventory_externals_and_required_modules(self):
        f = self.f
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        package_dir = f.state/'modules-k111'
        original = (package_dir/'module-root-complete.tar.gz').read_bytes(), (package_dir/'result.json').read_text()
        build = f.kernels/'rog5-kernel-7.2.7-build-r111'
        board = (build/'modules/lib/modules/7.2.7-rog5-k111/kernel/drivers/board.ko').read_bytes()

        def repackage(members, externals=('fake-ext.ko',)):
            data = module_tar('7.2.7-rog5-k111', members)
            (package_dir/'module-root-complete.tar.gz').write_bytes(data)
            result = json.loads(original[1])
            result.update(package_sha256=sha(data), external_modules=list(externals))
            (package_dir/'result.json').write_text(json.dumps(result))
        cases = [
            # a board module declared "external" to dodge provenance
            (dict({'drivers/board.ko': board, 'fake-ext.ko': b'e', 'extra.ko': board}), ('fake-ext.ko', 'extra.ko'),
             'external modules outside the selection'),
            # no board module at all
            (dict({'fake-ext.ko': b'e'}), ('fake-ext.ko',), 'carries no board module'),
            # the selection's external module left out
            (dict({'drivers/board.ko': board}), (), 'lacks external modules of the selection'),
        ]
        for members, externals, message in cases:
            with self.subTest(message=message):
                repackage(members, externals)
                with self.assertRaisesRegex(ValueError, message):
                    f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        # A verified module of the build that the selection does not name.
        second = build/'modules/lib/modules/7.2.7-rog5-k111/kernel/drivers/second.ko'
        second.write_bytes(b'second')
        entries = json.loads((build/'module-provenance.json').read_text())
        entries.append(dict(path='modules/lib/modules/7.2.7-rog5-k111/kernel/drivers/second.ko', sha256=sha(b'second'),
                            name='second', vermagic='7.2.7-rog5-k111 SMP'))
        (build/'module-provenance.json').write_text(json.dumps(entries))
        built = json.loads((build/'result.json').read_text())
        built['outputs']['module-provenance.json'] = sha((build/'module-provenance.json').read_bytes())
        (build/'result.json').write_text(json.dumps(built))
        repackage({'drivers/board.ko': board, 'drivers/second.ko': b'second', 'fake-ext.ko': b'e'})
        with self.assertRaisesRegex(ValueError, 'board modules differ from the selection: missing ; extra drivers/second.ko'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        # The private copy is what the ramdisk builder gets.
        (package_dir/'module-root-complete.tar.gz').write_bytes(original[0])
        (package_dir/'result.json').write_text(original[1])
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        env = json.loads(f.log.read_text())
        self.assertRegex(Path(env['PRODUCTION_MODULE_PACKAGE']).parent.name, r'^bundle-work-main-k111-d9-261001[a-z]$')
        # A DTB that needs a module the package lacks.
        registry = json.loads((f.config/'dtbs.json').read_text())
        registry['dtbs']['d9']['requires'] = dict(modules=['drivers/media/iris.ko'])
        (f.config/'dtbs.json').write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, 'the DTB needs modules the package does not carry: drivers/media/iris.ko'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')

    def test_bundle_inputs_symlink_in_the_repository_is_refused(self):
        f = self.f
        inside = f.source/'configs/production/bundle-inputs.json'
        inside.write_text(f.inputs.read_text())
        git = ['git', '-C', str(f.source), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git+['add', '-A'], check=True)
        subprocess.run(git+['commit', '-qm', 'inputs'], check=True)
        inside.unlink()
        inside.symlink_to(f.inputs)
        f.inputs = inside
        with self.assertRaisesRegex(ValueError, 'must not be a symlink'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')

    def test_dtb_kernel_requirements_are_inherited_and_enforced(self):
        f = self.f
        registry = json.loads((f.config/'dtbs.json').read_text())
        patch = '0089-power-supply-qcom_battmgr-ROG5-bottom-port-5V-source-regulator.patch'
        registry['dtbs']['d9']['requires'] = dict(patches=[patch], config={'CONFIG_X': 'y|m'})
        new = f.state/'platform-test-dtb-d10'
        new.mkdir()
        (new/'board.dtb').write_bytes(b'dtb ten')
        registry['dtbs']['d10'] = dict(path='platform-test-dtb-d10/board.dtb', sha256=sha(b'dtb ten'),
                                       features='touch,memx', base='d9', created='2026-10-01',
                                       kernel_requires='', requires={}, notes='derived')
        (f.config/'dtbs.json').write_text(json.dumps(registry))
        REG.write_features(REG.Registry(f.config, f.doc), 'd10')
        reg = REG.Registry(f.config, f.doc)
        self.assertEqual(reg.requirements('d10'), ([patch], {'CONFIG_X': 'y|m'}))
        # k111 lacks 0089: d10 inherits d9's requirement and is refused, at --plan already.
        with self.assertRaisesRegex(ValueError, 'd10 needs kernel patches k111 does not carry: '+patch):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd10', '--plan')
        f.kernel(113, '7.2.7-rog5-k113', 'k113', patches=('0001-a.patch', patch), config='CONFIG_X=m\n')
        self.assertEqual(json.loads(f.run('--role', 'main', '--kernel', 'k113', '--dtb', 'd10', '--plan'))['name'],
                         'main-k113-d10-261001a')
        f.kernel(114, '7.2.7-rog5-k114', 'k114', patches=('0001-a.patch', patch), config='# CONFIG_X is not set\n')
        with self.assertRaisesRegex(ValueError, 'needs kernel config k114 does not have: CONFIG_X=y\\|m \\(has unset\\)'):
            f.run('--role', 'main', '--kernel', 'k114', '--dtb', 'd10', '--plan')
        # A .config that differs from result.json is not trusted.
        (f.kernels/'rog5-kernel-7.2.7-build-r113/objects/.config').write_text('CONFIG_X=y\n')
        with self.assertRaisesRegex(ValueError, 'objects/.config differs from result.json'):
            f.run('--role', 'main', '--kernel', 'k113', '--dtb', 'd10', '--plan')

    def test_bundle_inputs_in_the_repository_must_be_committed(self):
        f = self.f
        inside = f.source/'configs/production/bundle-inputs.json'
        inside.write_text(f.inputs.read_text())
        git = ['git', '-C', str(f.source), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git+['add', '-A'], check=True)
        subprocess.run(git+['commit', '-qm', 'inputs'], check=True)
        f.inputs = inside
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        record = json.loads((f.state/'package-main-k111-d9-261001a/make-bundle.json').read_text())
        self.assertEqual(record['bundle_inputs_sha256'], sha(inside.read_bytes()))
        data = json.loads(inside.read_text())
        data['ramdisk_env']['UFS_CONTAINMENT'] = 'on'
        inside.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'bundle-inputs.json differs from HEAD'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')

    def test_registries_in_the_repository_must_be_committed(self):
        f = self.f
        inside = f.source/'configs/production'
        for name in ('dtbs.json', 'bundles.json'):
            shutil.copyfile(f.config/name, inside/name)
        f.config = inside
        git = ['git', '-C', str(f.source), '-c', 'user.name=t', '-c', 'user.email=t@t']
        subprocess.run(git+['add', '-A'], check=True)
        subprocess.run(git+['commit', '-qm', 'registries'], check=True)
        for name in ('dtbs.json', 'bundles.json'):
            path = inside/name
            original = path.read_bytes()
            path.write_bytes(original+b'\n')
            with self.assertRaisesRegex(ValueError, name.replace('.', r'\.')+' differs from HEAD'):
                f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
            self.assertFalse(list(f.state.glob('package-*')))
            path.write_bytes(original)
        expected = {str(inside/name): sha((inside/name).read_bytes()) for name in ('dtbs.json', 'bundles.json')}
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        record = json.loads(next(f.state.glob('package-*/make-bundle.json')).read_text())
        self.assertEqual(record['registry_inputs_sha256'], expected)

    def test_changed_external_module_sources_give_a_new_module_package(self):
        f = self.f
        self.assertIn('modules modules-k111 (new)', f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9'))
        self.assertIn('modules modules-k111 (reused)', f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9'))
        (f.source/'tools/fake/fake.c').write_text('int x = 1;\n')
        subprocess.run(['git', '-C', str(f.source), '-c', 'user.name=t', '-c', 'user.email=t@t',
                        'commit', '-qam', 'external module fix'], check=True)
        out = f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        self.assertRegex(out, r'modules modules-k111-[0-9]{12} \(new\)')
        newer = out.split('modules modules-k111-')[1][:12]
        self.assertIn(f'modules modules-k111-{newer} (reused)',
                      f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9'))

    def test_build_steps_get_no_inherited_overrides(self):
        f = self.f
        f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9',
              env=dict(ROG5_TRIAL_HELPER='artifacts/persistent-trial-state-v1/x', PYTHONPATH='/elsewhere',
                       ROG5_SIGNING_KEY=str(f.key)))
        seen = json.loads((f.state/'package-main-k111-d9-261001a/environment.json').read_text())
        for key in ('ROG5_TRIAL_HELPER', 'PYTHONPATH', 'ROG5_SIGNING_KEY', 'PRODUCTION_TRIAL_DESCRIPTOR'):
            self.assertNotIn(key, seen)

    def test_a_registered_kernel_must_keep_its_bytes(self):
        f = self.f
        data = json.loads((f.config/'bundles.json').read_text())
        data['kernels']['k111'] = dict(build='rog5-kernel-7.2.7-build-r111', release='7.2.7-rog5-k111',
                                       image_sha256='3'*64)
        (f.config/'bundles.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'names other bytes'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', '--plan')

    def test_pruned_build_takes_its_image_from_a_registered_bundle(self):
        f = self.f
        with self.assertRaisesRegex(ValueError, 'no registered bundle has its Image'):
            build = f.kernels/'rog5-kernel-7.2.7-build-r69'
            shutil.copytree(build/'objects', f.root/'objects-k69')
            shutil.rmtree(build/'objects')
            f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--plan')
        shutil.copytree(f.root/'objects-k69', build/'objects')
        _, _, copy = self.prune_k69_with_a_registered_copy()
        self.assertEqual(json.loads(f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--plan'))['image'],
                         str(copy))
        copy.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'no registered bundle has its Image'):
            f.run('--role', 'safe', '--kernel', 'k69', '--dtb', 'd9', '--plan')

    def test_refusals_leave_the_registry_unchanged(self):
        f = self.f
        f.kernel(112, '7.2.7-rog5-k112', 'k112', status='FAIL')
        f.kernel(113, '7.2.7-rog5-k114', 'k113')
        f.kernel(115, '7.2.7-rog5-k115', 'k116')
        before = (f.config/'bundles.json').read_text()
        cases = [
            (('--role', 'main', '--kernel', 'k112', '--dtb', 'd9'), 'did not PASS'),
            (('--role', 'main', '--kernel', 'k113', '--dtb', 'd9'), 'lacks -rog5-k113'),
            (('--role', 'main', '--kernel', 'k115', '--dtb', 'd9'), 'labelled k116'),
            (('--role', 'main', '--kernel', 'k0', '--dtb', 'd9'), 'kNNN'),
            (('--role', 'main', '--kernel', 'k120', '--dtb', 'd9'), 'expected one'),
            (('--role', 'main', '--kernel', 'k111', '--dtb', 'd8'), 'unknown DTB'),
            (('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', '--boot-modules-from', f.old_rev), 'fallback'),
            (('--role', 'trial', '--kernel', 'k111', '--dtb', 'd9'), None),
        ]
        for argv, message in cases:
            with self.subTest(argv=argv):
                with self.assertRaises((ValueError, SystemExit)) as caught:
                    f.run(*argv)
                if message:
                    self.assertIn(message, str(caught.exception))
        (f.state/'platform-test-dtb-r9/board.dtb').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'does not match its sha256'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9')
        (f.state/'platform-test-dtb-r9/board.dtb').write_bytes(b'dtb nine')
        with self.assertRaisesRegex(ValueError, 'does not carry the fresh descriptor'):
            f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', env=dict(FAKE_DROP_DESCRIPTOR='1'))
        self.assertEqual((f.config/'bundles.json').read_text(), before)
        # A failed attempt burns its name: the next run takes the next letter.
        self.assertIn('main-k111-d9-261001b', f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', '--plan'))

    def test_plan_builds_nothing(self):
        f = self.f
        out = f.run('--role', 'main', '--kernel', 'k111', '--dtb', 'd9', '--plan')
        self.assertEqual(json.loads(out)['name'], 'main-k111-d9-261001a')
        self.assertEqual(sorted(p.name for p in f.state.iterdir()),
                         ['extra_firmware', 'platform-test-dtb-r9', 'wifi_kit'])


if __name__ == '__main__':
    unittest.main()
