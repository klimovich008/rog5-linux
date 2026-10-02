#!/usr/bin/env python3
"""Kernel, DTB and bundle registries and the generated docs/bundles.md.

Names (docs/development.md, "Bundle names"):
  kernel build  kNNN   the build directory rog5-kernel-<base>-build-rNNN;
                       from k111 on uname -r is <base>-rog5-kNNN
  DTB           dN     configs/production/dtbs.json, with a 'features' file
                       next to each board.dtb
  bundle        <role>-k<kernel>-d<dtb>-<YYMMDD><letter>, role main|safe,
                e.g. main-k111-d9-261001a; bundles made before the scheme keep
                their names (production-7.2.7-r208, production-7.2.7-safe-r8)

  rog5-bundle-registry.py check                     validate the registries, the DTB
                                                    files (if present) and docs/bundles.md
  rog5-bundle-registry.py render                    rewrite docs/bundles.md
  rog5-bundle-registry.py set NAME [--status S] [--healthy H] [--installed TEXT]
                                   [--changes TEXT] [--notes TEXT]
  rog5-bundle-registry.py describe kNNN|dN TEXT     set a kernel's changes or a DTB's notes
  rog5-bundle-registry.py add-dtb --dtb PATH --features LIST [--base dN]
                                  [--kernel-requires TEXT] [--notes TEXT]
                                  [--require-patch NAME ...] [--require-config SYM=y|m|y|m ...]

A DTB's "requires" (production-series patch file names and .config symbols)
plus those of its base chain must be carried by the kernel build a bundle pairs
it with; rog5-make-bundle.py enforces that (check_kernel). "kernel_requires"
is free text for the table.

Offline only: nothing here touches the phone.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO/'configs/production'
DOC = REPO/'docs/bundles.md'
ROLES = ('main', 'safe')
STATUSES = ('built', 'ram-trial-pass', 'ram-trial-fail', 'installed-main', 'installed-fallback',
            'retired', 'not-installed', 'install-failed', 'rejected')
HEALTHY = ('yes', 'no', 'unknown', 'n/a')
SHA = re.compile(r'[0-9a-f]{64}')
KERNEL = re.compile(r'k([1-9][0-9]{0,3})')
DTB = re.compile(r'd([1-9][0-9]{0,3})')
# The slot-B loader's valid_bundle_name (initramfs/persistent-slotb-loader-init).
LOADER_NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')
NEW_NAME = re.compile(r'(main|safe)-k([1-9][0-9]{0,3})-d([1-9][0-9]{0,3})-([0-9]{6})([a-z])')
FEATURE = re.compile(r'[a-z0-9]+')
PATCH_NAME = re.compile(r'[0-9]{4}-[A-Za-z0-9._+-]+\.patch')
CONFIG_SYMBOL = re.compile(r'CONFIG_[A-Z0-9_]+')
CONFIG_VALUES = {'y': ('y',), 'm': ('m',), 'y|m': ('y', 'm')}
FIRST_NEW_DTB = 10


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def expand(text, state=None):
    """~ and {state} in a registry or input path."""
    if state is not None:
        text = text.replace('{state}', str(state))
    return Path(os.path.expanduser(text))


def loader_name_ok(name):
    return LOADER_NAME.fullmatch(name) is not None and '..' not in name


def bundle_name(role, kernel, dtb, day, letter):
    """<role>-k<kernel>-d<dtb>-<YYMMDD><letter>."""
    need(role in ROLES, 'role must be main or safe')
    need(KERNEL.fullmatch(kernel) is not None, 'kernel must be kNNN (k1 to k9999)')
    need(DTB.fullmatch(dtb) is not None, 'DTB must be dN (d1 to d9999)')
    need(re.fullmatch(r'[0-9]{6}', day) is not None, 'date must be YYMMDD')
    need(re.fullmatch(r'[a-z]', letter) is not None, 'letter must be a-z')
    name = f'{role}-{kernel}-{dtb}-{day}{letter}'
    need(NEW_NAME.fullmatch(name) is not None and loader_name_ok(name), 'invalid bundle name '+name)
    return name


def write_json(path, data):
    """Replace PATH atomically (same directory)."""
    path = Path(path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.'+path.name+'.')
    try:
        with os.fdopen(handle, 'w') as stream:
            stream.write(json.dumps(data, indent=2)+'\n')
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class Registry:
    def __init__(self, config=CONFIG, doc=DOC):
        self.config = Path(config)
        self.doc = Path(doc)
        self.dtbs_path = self.config/'dtbs.json'
        self.bundles_path = self.config/'bundles.json'
        self.dtbs = json.loads(self.dtbs_path.read_text())
        self.data = json.loads(self.bundles_path.read_text())

    @property
    def bundles(self):
        return self.data['bundles']

    @property
    def kernels(self):
        return self.data['kernels']

    def dtb_root(self):
        return expand(self.dtbs['root'])

    def bundle(self, name):
        found = [entry for entry in self.bundles if entry['name'] == name]
        need(len(found) == 1, 'unknown bundle '+name)
        return found[0]

    def dtb(self, ident):
        need(ident in self.dtbs['dtbs'], 'unknown DTB '+ident+' (configs/production/dtbs.json)')
        entry = self.dtbs['dtbs'][ident]
        return self.dtb_root()/entry['path'], entry

    def validate(self):
        """Structural checks of both registries (no private files needed)."""
        need(self.dtbs.get('format') == 'rog5-dtb-registry-v1', 'dtbs.json format')
        need(self.data.get('format') == 'rog5-bundle-registry-v1', 'bundles.json format')
        paths = set()
        for ident, entry in self.dtbs['dtbs'].items():
            need(DTB.fullmatch(ident) is not None, 'DTB id '+ident)
            need(SHA.fullmatch(entry['sha256']) is not None, ident+' sha256')
            relative = Path(entry['path'])
            need(not relative.is_absolute() and '..' not in relative.parts and relative.name == 'board.dtb',
                 ident+' path must be <dir>/board.dtb under root')
            need(entry['path'] not in paths, ident+' path registered twice')
            paths.add(entry['path'])
            need(all(FEATURE.fullmatch(f) for f in entry['features'].split(',')), ident+' features')
            need(entry.get('base') is None or entry['base'] in self.dtbs['dtbs'], ident+' base')
            requires = entry.get('requires')
            need(isinstance(requires, dict) and set(requires) <= {'patches', 'config'},
                 ident+' requires must be an object with patches and/or config')
            patches = requires.get('patches', [])
            need(isinstance(patches, list) and len(set(patches)) == len(patches)
                 and all(isinstance(n, str) and PATCH_NAME.fullmatch(n) for n in patches),
                 ident+' requires.patches must be distinct patch file names')
            for name in patches:
                need(any((series/name).is_file() for series in (REPO/'patches').glob('linux-*')),
                     ident+' requires an unknown patch '+name)
            config = requires.get('config', {})
            need(isinstance(config, dict) and all(CONFIG_SYMBOL.fullmatch(k) and v in CONFIG_VALUES
                                                  for k, v in config.items()),
                 ident+' requires.config must map CONFIG_ symbols to y, m or y|m')
        for ident in self.dtbs['dtbs']:
            self.requirements(ident)  # no base cycle, no conflicting inherited config
        for ident, entry in self.kernels.items():
            need(KERNEL.fullmatch(ident) is not None, 'kernel id '+ident)
            need(entry['build'].endswith('-build-r'+ident[1:]), ident+' build directory must end in -build-r'+ident[1:])
            need(SHA.fullmatch(entry['image_sha256']) is not None, ident+' image sha256')
            need(LOADER_NAME.fullmatch(entry['release']) is not None, ident+' release')
        names = set()
        for entry in self.bundles:
            name = entry['name']
            need(loader_name_ok(name), 'bundle name not accepted by the loader: '+name)
            need(name not in names, 'bundle listed twice: '+name)
            names.add(name)
            need(entry['role'] in ROLES, name+' role')
            need(entry['kernel'] in self.kernels, name+' kernel '+entry['kernel']+' not in kernels')
            need(entry['dtb'] in self.dtbs['dtbs'], name+' DTB '+entry['dtb']+' not in dtbs.json')
            need(entry['status'] in STATUSES, name+' status')
            need(entry['healthy'] in HEALTHY, name+' healthy')
            need(SHA.fullmatch(entry['manifest_sha256']) is not None, name+' manifest sha256')
            need(entry['release'] == self.kernels[entry['kernel']]['release'], name+' release differs from its kernel')
            parts = NEW_NAME.fullmatch(name)
            if parts:
                need((parts[1], 'k'+parts[2], 'd'+parts[3]) == (entry['role'], entry['kernel'], entry['dtb']),
                     name+' does not match its role/kernel/DTB')
            else:
                need(name.startswith('production-'), name+' is neither a scheme name nor a legacy name')
        for status in ('installed-main', 'installed-fallback'):
            need(sum(entry['status'] == status for entry in self.bundles) <= 1, 'more than one bundle is '+status)
        return True

    def requirements(self, ident):
        """(patches, config) a kernel needs for DTB IDENT: its own 'requires'
        and those of every base it was derived from."""
        patches, config, seen, current = set(), {}, [], ident
        while current is not None:
            need(current in self.dtbs['dtbs'], f'{ident}: unknown base {current}')
            need(current not in seen, f'{ident}: base cycle through {current}')
            seen.append(current)
            entry = self.dtbs['dtbs'][current]
            requires = entry.get('requires') or {}
            patches.update(requires.get('patches', []))
            for symbol, value in requires.get('config', {}).items():
                need(config.get(symbol, value) == value, f'{ident}: {current} and a derived DTB disagree on {symbol}')
                config[symbol] = value
            current = entry.get('base')
        return sorted(patches), dict(sorted(config.items()))

    def check_kernel(self, ident, kernel, result, config_text):
        """Refuse a kernel build that lacks a patch or .config symbol DTB IDENT
        (with its bases) needs. RESULT is the build's result.json; CONFIG_TEXT
        its .config (None when the object tree is pruned)."""
        patches, config = self.requirements(ident)
        applied = {item['name'] for item in result.get('ordered_series', {}).get('production', [])}
        need(applied or not patches, f'{kernel}: result.json records no production series')
        missing = [name for name in patches if name not in applied]
        need(not missing, f'{ident} needs kernel patches {kernel} does not carry: '+', '.join(missing))
        if config:
            need(config_text is not None, f'{ident} needs .config symbols but the {kernel} build has no .config')
            values = {}
            for line in config_text.splitlines():
                match = re.fullmatch(r'(CONFIG_[A-Z0-9_]+)=(.*)', line)
                if match:
                    values[match[1]] = match[2]
            wrong = [f'{symbol}={value} (has {values.get(symbol, "unset")})' for symbol, value in config.items()
                     if values.get(symbol) not in CONFIG_VALUES[value]]
            need(not wrong, f'{ident} needs kernel config {kernel} does not have: '+', '.join(wrong))
        return patches, config

    def verify_dtb(self, ident):
        """The DTB file and its features file match the registry."""
        path, entry = self.dtb(ident)
        need(path.is_file() and not path.is_symlink(), f'{ident}: {path} missing')
        need(sha256(path) == entry['sha256'], f'{ident}: {path} does not match its sha256')
        features = path.parent/'features'
        need(features.is_file(), f'{ident}: no features file next to {path}')
        need(features.read_text() == features_text(ident, entry), f'{ident}: {features} differs from dtbs.json')
        return path, entry

    def save(self):
        self.validate()
        write_json(self.dtbs_path, self.dtbs)
        write_json(self.bundles_path, self.data)
        self.doc.write_text(render(self))

    def next_dtb_id(self):
        used = [int(DTB.fullmatch(ident)[1]) for ident in self.dtbs['dtbs']]
        return 'd'+str(max([FIRST_NEW_DTB-1]+used)+1)


@contextlib.contextmanager
def locked(config=CONFIG, doc=DOC):
    """The registry loaded fresh under an exclusive lock (flock on the config
    directory) and saved when the block succeeds, so a bundle build that ran
    for minutes cannot overwrite a status change made meanwhile."""
    descriptor = os.open(config, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        registry = Registry(config, doc)
        registry.validate()
        yield registry
        registry.save()
    finally:
        os.close(descriptor)


def features_text(ident, entry):
    return (f"id={ident}\nsha256={entry['sha256']}\nfeatures={entry['features']}\n"
            f"base={entry.get('base') or 'none'}\n")


def write_features(registry, ident):
    path, entry = registry.dtb(ident)
    target = path.parent/'features'
    text = features_text(ident, entry)
    if target.exists():
        need(target.read_text() == text, f'{target} exists with other content')
        return target
    target.write_text(text)
    return target


def cell(value):
    text = '' if value is None else str(value)
    return text.replace('|', '\\|').replace('\n', ' ')


def needs_text(registry, ident):
    """The table's Needs cell: the enforced requirement (inherited ones
    included), then the free text."""
    patches, config = registry.requirements(ident)
    runs = []
    for number in sorted(int(name[:4]) for name in patches):
        if runs and number == runs[-1][1]+1:
            runs[-1][1] = number
        else:
            runs.append([number, number])
    numbers = [f'{a:04d}' if a == b else f'{a:04d}-{b:04d}' for a, b in runs]
    enforced = ', '.join(numbers + [f'{k}={v}' for k, v in config.items()])
    text = registry.dtbs['dtbs'][ident].get('kernel_requires') or ''
    return enforced + (f' ({text})' if text else '') if enforced else text


def render(registry):
    lines = ['# Bundles, kernels and DTBs', '',
             '<!-- Generated by scripts/host/rog5-bundle-registry.py from configs/production/bundles.json',
             '     and configs/production/dtbs.json. Edit those files (or use the tools), then render. -->', '',
             'Naming: kernel builds are `kNNN` (build directory `rog5-kernel-<base>-build-rNNN`), DTBs are',
             '`dN` (`configs/production/dtbs.json`) and bundles are `<role>-k<kernel>-d<dtb>-<YYMMDD><letter>`',
             'with role `main` (the try-once default, built with a trial descriptor) or `safe` (the',
             'fallback, no descriptor). From k111 on `uname -r` is `<base>-rog5-kNNN`; k110 and older',
             'report `7.2.7-rog5-production`. Bundles made before the scheme keep their names.',
             'Build one with `scripts/host/rog5-make-bundle.py --role main|safe --kernel kNNN --dtb dN`',
             '(see "Bundle names and the bundle tool" in [development.md](development.md)).', '']
    main = [b['name'] for b in registry.bundles if b['status'] == 'installed-main']
    safe = [b['name'] for b in registry.bundles if b['status'] == 'installed-fallback']
    lines += [f"Installed: default `{main[0] if main else 'none recorded'}`, "
              f"fallback `{safe[0] if safe else 'none recorded'}`.", '', '## Bundles', '',
              '| Bundle | Role | Kernel | DTB | Status | Healthy | Installed | Key changes | Notes |',
              '|---|---|---|---|---|---|---|---|---|']
    for b in reversed(registry.bundles):
        lines.append('| ' + ' | '.join(cell(v) for v in (
            '`'+b['name']+'`', b['role'], b['kernel'], b['dtb'], b['status'], b['healthy'],
            b.get('installed') or '', b.get('changes'), b.get('notes'))) + ' |')
    lines += ['', '## Kernel builds', '',
              '| Kernel | Build directory | uname -r | Series | Date | Changes |', '|---|---|---|---|---|---|']
    for ident in sorted(registry.kernels, key=lambda k: -int(k[1:])):
        k = registry.kernels[ident]
        lines.append('| ' + ' | '.join(cell(v) for v in (
            ident, '`'+k['build']+'`', '`'+k['release']+'`', k.get('series'), k.get('date'), k.get('changes'))) + ' |')
    lines += ['', '## DTBs', '',
              f"Paths are under `{registry.dtbs['root']}`; each directory holds `board.dtb` and `features`.", '',
              '| DTB | Path | SHA-256 | Base | Features | Needs | Notes |', '|---|---|---|---|---|---|---|']
    for ident in sorted(registry.dtbs['dtbs'], key=lambda d: -int(d[1:])):
        d = registry.dtbs['dtbs'][ident]
        lines.append('| ' + ' | '.join(cell(v) for v in (
            ident, '`'+d['path']+'`', '`'+d['sha256'][:8]+'`', d.get('base') or '', d['features'].replace(',', ', '),
            needs_text(registry, ident), d.get('notes'))) + ' |')
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument('--config', type=Path, default=CONFIG, help=argparse.SUPPRESS)
    parser.add_argument('--doc', type=Path, default=DOC, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('check')
    check.add_argument('--files', action='store_true', help='also require every DTB file and features file')
    sub.add_parser('render')
    setting = sub.add_parser('set')
    setting.add_argument('name')
    setting.add_argument('--status', choices=STATUSES)
    setting.add_argument('--healthy', choices=HEALTHY)
    setting.add_argument('--installed')
    setting.add_argument('--changes')
    setting.add_argument('--notes')
    describe = sub.add_parser('describe')
    describe.add_argument('ident')
    describe.add_argument('text')
    add = sub.add_parser('add-dtb')
    add.add_argument('--dtb', type=Path, required=True, help='<dir>/board.dtb under the registry root')
    add.add_argument('--features', required=True, help='compose feature list, comma separated')
    add.add_argument('--base', help='the dN it was derived from')
    add.add_argument('--kernel-requires', default='')
    add.add_argument('--notes', default='')
    add.add_argument('--require-patch', action='append', default=[], metavar='NAME',
                     help='production-series patch file the kernel must carry (repeatable; the base chain is inherited)')
    add.add_argument('--require-config', action='append', default=[], metavar='SYM=y|m|y|m',
                     help='.config symbol the kernel must have (repeatable)')
    args = parser.parse_args(argv)
    if args.action != 'check':
        with locked(args.config, args.doc) as registry:
            change(args, registry)
        return 0
    registry = Registry(args.config, args.doc)
    registry.validate()
    if args.action == 'check':
        problems = []
        if registry.doc.read_text() != render(registry):
            problems.append(f'{registry.doc} is stale: run rog5-bundle-registry.py render')
        for ident in registry.dtbs['dtbs']:
            path, _ = registry.dtb(ident)
            if args.files or path.exists():
                try:
                    registry.verify_dtb(ident)
                except ValueError as error:
                    problems.append(str(error))
        for problem in problems:
            print('FAIL '+problem, file=sys.stderr)
        if problems:
            return 1
        print(f'PASS {len(registry.bundles)} bundles, {len(registry.kernels)} kernels, '
              f'{len(registry.dtbs["dtbs"])} DTBs')
        return 0


def requires_argument(args):
    requires = {}
    if args.require_patch:
        requires['patches'] = list(args.require_patch)
    if args.require_config:
        config = {}
        for item in args.require_config:
            symbol, _, value = item.partition('=')
            need(symbol not in config, 'config symbol given twice: '+symbol)
            config[symbol] = value
        requires['config'] = config
    return requires


def change(args, registry):
    """Apply one set/describe/add-dtb/render to REGISTRY (saved by the caller)."""
    if args.action == 'set':
        entry = registry.bundle(args.name)
        if args.status == 'installed-main' or args.status == 'installed-fallback':
            for other in registry.bundles:
                if other is not entry and other['status'] == args.status:
                    other['status'] = 'retired'
                    print(f'{other["name"]}: {args.status} -> retired')
        for key in ('status', 'healthy', 'installed', 'changes', 'notes'):
            if getattr(args, key) is not None:
                entry[key] = getattr(args, key)
    elif args.action == 'describe':
        if KERNEL.fullmatch(args.ident):
            need(args.ident in registry.kernels, 'unknown kernel '+args.ident)
            registry.kernels[args.ident]['changes'] = args.text
        else:
            registry.dtb(args.ident)[1]['notes'] = args.text
    elif args.action == 'add-dtb':
        root = registry.dtb_root().resolve()
        path = args.dtb.resolve()
        need(path.name == 'board.dtb' and path.parent.parent == root,
             f'the DTB must be {root}/<dir>/board.dtb')
        relative = str(path.relative_to(root))
        digest = sha256(path)
        for ident, entry in registry.dtbs['dtbs'].items():
            need(entry['path'] != relative and entry['sha256'] != digest, 'already registered as '+ident)
        need(args.base is None or args.base in registry.dtbs['dtbs'], 'unknown base '+str(args.base))
        ident = registry.next_dtb_id()
        registry.dtbs['dtbs'][ident] = dict(
            path=relative, sha256=digest, features=args.features, base=args.base,
            created=datetime.date.today().isoformat(), kernel_requires=args.kernel_requires,
            requires=requires_argument(args), notes=args.notes)
        registry.validate()
        write_features(registry, ident)
        print(f'{ident} = {relative} ({digest[:8]})')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
