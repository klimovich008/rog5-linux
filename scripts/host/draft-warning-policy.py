#!/usr/bin/env python3
"""Draft the warning policy for a new kernel base from one completed build.

A rebase moves upstream code, so the previous base's hash-pinned policy no
longer matches. This keeps every entry of the previous policy that still
matches, then pins each remaining diagnostic only if it is in a file the ROG5
series does not modify: the file's SHA-256 and the exact message with its
count. A diagnostic in a file the series touches, a DT schema (dtb/dtbo/yaml)
message or a depmod line is never drafted and makes the run fail; those need
a real fix or an individual review. The result is re-checked against the same
build logs, so it accepts exactly what the build printed.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('diagnostics', REPO/'scripts/host/check-production-build-diagnostics.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
STAGES = ('kernel-build', 'modules-install', 'depmod', 'dtbs-check')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def need(ok, why):
    if not ok:
        raise ValueError(why)


def touched_files(patch_dir):
    files = set()
    for patch in Path(patch_dir).glob('*.patch'):
        files |= set(re.findall(r'^\+\+\+ b/(\S+)', patch.read_text(errors='replace'), re.M))
    return files


def source_path(line, source):
    """Source-relative file named by a diagnostic line, or None."""
    text = line.replace(str(source)+'/', '')
    text = re.sub(r'^(?:\.\./)+source/', '', text)
    text = re.sub(r'^Warning: ', '', text)
    match = re.match(r'([A-Za-z0-9_./+-]+\.(?:c|h|S|dtsi|dts|dtso|rs)):', text)
    return match.group(1) if match else None


def check(build, policy):
    results = []
    for stage in STAGES:
        log = build/(stage+'.log')
        if log.is_file():
            results += [dict(stage=stage, **r) for r in D.diagnostics(log.read_text(errors='replace'), stage,
                                                                         build/'source', build/'objects', policy)]
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--build-policy', type=Path, required=True, help='build policy of the new base (base_commit, patch_dir)')
    parser.add_argument('--previous', type=Path, required=True, help='warning policy of the previous base')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(not args.output.exists(), 'output exists')
    build = args.build.resolve()
    source = (build/'source').resolve()
    raw = json.loads((build/'result.json').read_text())
    base = json.loads(args.build_policy.read_text())
    need(raw['linux_base'] == base['base_commit'], 'build is not of the new base')
    need(all(raw['stages'].get(s, {}).get('status') == 'PASS' for s in STAGES), 'a build stage did not pass')
    previous = json.loads(args.previous.read_text())
    touched = touched_files(REPO/base['patch_dir'])
    policy = dict(previous, base_commit=base['base_commit'], initializer_overrides=[], reviewed_messages=[])
    # Keep previous entries whose pinned files are byte-identical on the new base.
    for pin in previous['initializer_overrides']:
        root = source if pin['root'] == 'source' else build/'objects'
        if (root/pin['path']).is_file() and sha(root/pin['path']) == pin['sha256'] and all(
                sha((source if d['root'] == 'source' else build/'objects')/d['path']) == d['sha256'] for d in pin['dependencies']):
            policy['initializer_overrides'].append(pin)
    # A reviewed site's reason also rests on its pinned dependencies (headers).
    for pin in previous['reviewed_messages']:
        if (source/pin['path']).is_file() and sha(source/pin['path']) == pin['sha256'] and all(
                (source/d['path']).is_file() and sha(source/d['path']) == d['sha256'] for d in pin['dependencies']):
            policy['reviewed_messages'].append(pin)
    kept = (len(policy['initializer_overrides']), len(policy['reviewed_messages']))
    refused, drafted = [], collections.defaultdict(collections.Counter)
    for entry in check(build, policy):
        if entry['allowed']:
            continue
        line = entry['line']
        path = source_path(line, source)
        if entry['kind'] != 'compiler-or-tool' or entry['stage'] == 'depmod' or path is None or path in touched \
                or not (source/path).is_file():
            refused.append(dict(stage=entry['stage'], line=line[:400], path=path, series_file=path in touched))
            continue
        drafted[path][D.normalize(line, source, build/'objects')] += 1
    need(not refused, 'diagnostics that cannot be drafted:\n'+'\n'.join(json.dumps(r) for r in refused[:40]))
    reason = ('Upstream '+base['base_commit'][:12]+' W=1 diagnostic in a file the ROG5 series does not modify; '
              'exact file hash and message count drafted by draft-warning-policy.py.')
    for path, messages in sorted(drafted.items()):
        policy['reviewed_messages'].append(dict(path=path, sha256=sha(source/path), messages=dict(messages),
                                                dependencies=[], config_guards={}, reason=reason))
    policy['review_evidence'] = dict(method='draft-warning-policy.py', build=str(build),
                                     build_result_sha256=sha(build/'result.json'), previous_policy_sha256=sha(args.previous),
                                     kept_initializer_pins=kept[0], kept_reviewed_files=kept[1], drafted_files=len(drafted),
                                     drafted_messages=sum(sum(c.values()) for c in drafted.values()))
    left = [e['line'] for e in check(build, policy) if not e['allowed']]
    need(not left, 'drafted policy still leaves diagnostics:\n'+'\n'.join(left[:20]))
    args.output.write_text(json.dumps(policy, indent=2)+'\n')
    print(json.dumps(policy['review_evidence']))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
