#!/usr/bin/env python3
"""Move the production patch series to a new signed kernel tag.

  start     fetch the tag if asked, verify its signature against pinned kernel
            release keys, extract it into a new work tree and apply the series
            one commit per patch. A patch that does not apply stops the run
            with its rejected hunks (*.rej) listed.
  continue  after resolving the current patch in the work tree (and deleting
            the .rej/.orig files), commit it and apply the remaining patches.
  export    write patches/linux-<version>/ (original headers, fresh full-index
            diffs, series files), prove the new set reproduces the work tree
            on a fresh extract, and write the matching build policy with the
            new base commit and base-archive hash.

The build and phone trials of the new base are separate steps (see "Upgrading
the kernel base" in docs/development.md). Nothing here touches the phone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
STABLE = 'https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git'
GNUPG = Path.home()/'.local/state/rog5-host-tools/gnupg'
# Kernel release signers: Greg Kroah-Hartman (stable) and Linus Torvalds (mainline).
TRUSTED = {'647F28654894E3BD457199BE38DBBDC86092693E', 'ABAF11C65A2970B130ABE3C479BE3E4300411886'}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def git(*args, cwd=None, check=True, env=None):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=check, env=env)


def verify_tag(linux_git, tag):
    env = dict(os.environ, GNUPGHOME=str(GNUPG))
    result = subprocess.run(['git', '-C', str(linux_git), 'verify-tag', '--raw', tag], capture_output=True, text=True, env=env)
    signers = {line.split()[2] for line in result.stderr.splitlines() if line.startswith('[GNUPG:] VALIDSIG')}
    need(result.returncode == 0 and signers & TRUSTED, 'tag signature is not from a pinned kernel release key: '+tag)
    return sorted(signers & TRUSTED)[0]


def series(directory):
    return [line for line in (directory/'series.production').read_text().splitlines() if line and not line.startswith('#')]


def commit(tree, message):
    git('add', '-A', cwd=tree)
    git('-c', 'user.name=rog5-rebase', '-c', 'user.email=rog5-rebase@localhost', 'commit', '-q', '--allow-empty', '-m', message, cwd=tree)


def apply_from(state, work):
    tree, source = work/'tree', Path(state['from'])
    names = series(source)
    while state['next'] < len(names):
        name = names[state['next']]
        patch = source/name
        if git('apply', '--check', str(patch), cwd=tree, check=False).returncode == 0:
            git('apply', str(patch), cwd=tree)
            commit(tree, name)
            state['clean'].append(name)
            state['next'] += 1
            continue
        git('apply', '--reject', str(patch), cwd=tree, check=False)
        state['conflict'] = dict(patch=name, rejects=sorted(str(p.relative_to(tree)) for p in tree.rglob('*.rej')))
        (work/'state.json').write_text(json.dumps(state, indent=2)+'\n')
        print(json.dumps(dict(status='CONFLICT', patch=name, rejects=state['conflict']['rejects'],
                              resolve_in=str(tree), then='rebase-kernel-series.py continue --work '+str(work))))
        return 2
    state['conflict'] = None
    (work/'state.json').write_text(json.dumps(state, indent=2)+'\n')
    print(json.dumps(dict(status='APPLIED', tag=state['tag'], clean=len(state['clean']), resolved=state['resolved'],
                          then='rebase-kernel-series.py export --work '+str(work))))
    return 0


def start(args):
    linux_git, work = Path(args.linux_git).resolve(), Path(args.work).resolve()
    need(not work.exists(), 'work must be a new directory')
    if args.fetch and git('-C', str(linux_git), 'rev-parse', '-q', '--verify', 'refs/tags/'+args.tag, check=False).returncode:
        git('-C', str(linux_git), 'fetch', '-q', '--depth', '1', STABLE, 'tag', args.tag)
    signer = 'NOT VERIFIED (--no-verify)' if args.no_verify else verify_tag(linux_git, args.tag)
    base = git('-C', str(linux_git), 'rev-parse', args.tag+'^{commit}').stdout.strip()
    tree = work/'tree'
    tree.mkdir(parents=True)
    archive = subprocess.run(['git', '-C', str(linux_git), 'archive', base], capture_output=True, check=True, env=dict(os.environ, LC_ALL='C')).stdout
    subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
    git('init', '-q', cwd=tree)
    commit(tree, args.tag+' '+base)
    state = dict(tag=args.tag, base_commit=base, base_archive_sha256=hashlib.sha256(archive).hexdigest(), signer=signer,
                 linux_git=str(linux_git), **{'from': str(Path(args.series_from).resolve())}, next=0, clean=[], resolved=[], conflict=None)
    return apply_from(state, work)


def resume(args):
    work = Path(args.work).resolve()
    state = json.loads((work/'state.json').read_text())
    need(state.get('conflict'), 'nothing to continue')
    tree = work/'tree'
    left = [str(p.relative_to(tree)) for p in list(tree.rglob('*.rej'))+list(tree.rglob('*.orig'))]
    need(not left, 'remove resolved .rej/.orig files first: '+', '.join(left))
    name = state['conflict']['patch']
    commit(tree, name)
    state['resolved'].append(name)
    state['next'] += 1
    return apply_from(state, work)


def export(args):
    work = Path(args.work).resolve()
    state = json.loads((work/'state.json').read_text())
    need(state.get('conflict') is None and state['next'] == len(series(Path(state['from']))), 'the series is not fully applied')
    tree, source = work/'tree', Path(state['from'])
    version = state['tag'].lstrip('v')
    out = Path(args.output).resolve() if args.output else REPO/'patches'/('linux-'+version)
    need(not out.exists(), 'output patch directory exists: '+str(out))
    out.mkdir(parents=True)
    commits = git('log', '--reverse', '--format=%H %s', cwd=tree).stdout.splitlines()[1:]
    names = []
    for line in commits:
        sha, name = line.split(' ', 1)
        text = (source/name).read_text()
        header = '' if text.startswith('diff --git ') else text[:text.find('\ndiff --git ')+1]
        diff = git('diff', '--full-index', '--binary', sha+'~1', sha, cwd=tree).stdout
        (out/name).write_text(header+diff)
        names.append(name)
    (out/'series.production').write_text('# Ordered production build inputs on '+state['tag']+' ('+state['base_commit'][:8]+'); no hardware qualification implied.\n'+''.join(n+'\n' for n in names))
    (out/'series.diagnostic').write_text('# No diagnostic patches are carried on this base.\n')
    with tempfile.TemporaryDirectory(prefix='rog5-rebase-verify-') as scratch:
        check = Path(scratch)
        archive = subprocess.run(['git', '-C', state['linux_git'], 'archive', state['base_commit']], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(check)], input=archive, check=True)
        git('init', '-q', cwd=check)
        for name in names:
            git('apply', str(out/name), cwd=check)
        git('add', '-A', cwd=check)
        rebuilt = git('write-tree', cwd=check).stdout.strip()
    expected = git('rev-parse', 'HEAD^{tree}', cwd=tree).stdout.strip()
    need(rebuilt == expected, 'exported patches do not reproduce the work tree')
    policy = json.loads(Path(args.policy_from).read_text())
    policy.update(base_commit=state['base_commit'], base_archive_sha256=state['base_archive_sha256'],
                  patch_dir=str(out.relative_to(REPO)) if out.is_relative_to(REPO) else str(out), base_description='stable '+state['tag']+', signed by '+state['signer'])
    policy_out = Path(args.policy_output).resolve() if args.policy_output else REPO/'configs/kernel'/('rog5-production-build-'+version+'.json')
    need(not policy_out.exists(), 'policy exists: '+str(policy_out))
    policy_out.write_text(json.dumps(policy, indent=2)+'\n')
    print(json.dumps(dict(status='EXPORTED', patches=str(out), policy=str(policy_out), tree=expected,
                          clean=len(state['clean']), resolved=state['resolved'])))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='action', required=True)
    s = sub.add_parser('start')
    s.add_argument('--linux-git', required=True)
    s.add_argument('--tag', required=True)
    s.add_argument('--from', dest='series_from', required=True, help='current patch directory, e.g. patches/linux-7.2.7')
    s.add_argument('--work', required=True)
    s.add_argument('--fetch', action='store_true', help='shallow-fetch the tag from the stable tree if missing')
    s.add_argument('--no-verify', action='store_true', help='skip the tag signature check (local test tags only)')
    c = sub.add_parser('continue')
    c.add_argument('--work', required=True)
    e = sub.add_parser('export')
    e.add_argument('--work', required=True)
    e.add_argument('--output')
    e.add_argument('--policy-from', required=True, help='build policy of the current base')
    e.add_argument('--policy-output')
    args = parser.parse_args()
    return dict(start=start, export=export)[args.action](args) if args.action != 'continue' else resume(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
