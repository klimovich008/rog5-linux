#!/usr/bin/env python3
"""Select the cheapest repository tier that covers a changed-path set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]
PROBE_ONLY = frozenset(
    {
        "scripts/device/observe-early-mainline-power.sh",
        "scripts/device/probe-network-root-battery-telemetry.sh",
        "scripts/device/test-observe-early-mainline-power.sh",
        "scripts/device/test-probe-network-root-battery-telemetry.sh",
        "scripts/host/collect-early-target-diagnostics.py",
        "scripts/host/early-target-diagnostics.py",
        "scripts/host/test-collect-early-target-diagnostics.py",
        "scripts/host/test-early-target-diagnostics.py",
        "tools/early_target_diag/rog5-early-target-diag.c",
    }
)
PROBE_QEMU = "tools/early_target_diag/rog5-early-target-diag.c"
# This current narrative has no runtime/builder consumers (reviewed with
# git grep). Do not generalize to other test-results: many are sealed inputs.
NARRATIVE_REPORT = 'test-results/2026-09-05-headless-acceptance.md'

# A development-only scope, NOT a release/admission allowlist. Any changed
# dependency outside these reviewed leaves broadens the decision. In particular
# the deployed verifier, units, power gates and runner itself are not leaves.
DEVELOPMENT_LEAVES = {
    'scripts/host/check-standalone-root.py': (
        'read-only-observer', 'scripts/host/test-check-standalone-root.py'),
    'scripts/device/rog5-healthd.py': (
        'isolated-userspace', 'scripts/device/test-rog5-healthd.py'),
}


def impact_categories(paths: list[str]) -> list[str]:
    categories=set()
    for path in paths:
        if documentation(path) or path==NARRATIVE_REPORT:
            categories.add('documentation')
        elif path in DEVELOPMENT_LEAVES:
            categories.add(DEVELOPMENT_LEAVES[path][0])
        elif any(word in path for word in ('admission','signing','claim','registry')):
            categories.add('trust-admission')
        elif path.startswith('initramfs/'):
            categories.add('initramfs')
        elif path.startswith('dts/') or path.endswith(('.dts','.dtso','.dtb')):
            categories.add('device-tree')
        elif any(word in path for word in ('charging','shutdown','watchdog','storage','recovery',
                                           'cpu-frequency-cap','power-profile')):
            categories.add('critical-runtime')
        elif '/module' in path or path.endswith('.ko'):
            categories.add('kernel-module')
        elif path.startswith(('patches/','configs/kernel/')) or 'kernel' in path:
            categories.add('kernel-or-ABI')
        else:
            categories.add('unknown-dependency')
    return sorted(categories)


def development_decision(paths: list[str]) -> dict:
    changed=sorted(set(paths))
    leaves={path:value for source,value in DEVELOPMENT_LEAVES.items()
            for path in (source,value[1])}
    runtime=[path for path in changed if not documentation(path) and path!=NARRATIVE_REPORT]
    covered=bool(changed) and all(path in leaves for path in runtime)
    impacts={leaves[path][0] for path in runtime if path in leaves}
    service='isolated-userspace' in impacts
    impact=('isolated-userspace' if service else 'read-only-observer') if runtime else 'documentation'
    if not covered:
        impact='critical-or-unknown-dependency'
    focused=sorted({leaves[path][1] for path in runtime if path in leaves})
    categories=impact_categories(changed)
    if 'trust-admission' in categories:
        focused=sorted(set(focused)|{'scripts/host/test-consume-exact-boot-claim.py',
            'scripts/host/test-verify-retention-cycle-admission.py'})
    return dict(format='rog5-development-selection-v1',status='NOT RUN',
        changed_paths=changed,impact=impact,impact_categories=categories,eligible=covered,
        tier='active' if covered else 'ci',focused_tests=focused,
        optimized_tests=focused,remote_ci_before_experiment=not covered,
        exact_target_required=bool(runtime),service_experiment_required=service,
        final_composition_required=bool(runtime),release_qualified=False,
        module_ABI_BTF_closure_required='kernel-module' in categories or 'kernel-or-ABI' in categories,
        all_admission_consumers_required='trust-admission' in categories,
        authority='none; selection is not a test result or boot admission',
        experiment_scope=('none' if not covered else
            'dedicated /run/rog5-dev-experiments directory; no accepted service/config replacement; '
            'read-only observation or isolated loopback service only; no boot/power/storage/recovery changes'),
        required_evidence=['frozen source and selected tests/results',
            'exact artifact/dependency/toolchain/configuration/environment identities',
            'exact-device and power/thermal checks before device access',
            'assembled payload and exact-target compatibility; bounded cleanup'],
        reason=('reviewed leaves only; all other changed dependencies fail broad' if covered else
                'empty changes or dependency outside demonstrated isolated coverage'))


def documentation(path: str) -> bool:
    # Markdown elsewhere can be a sealed artifact/runtime input, not prose.
    # In particular, test-results includes hash-pinned runtime-builder evidence
    # and compatibility-oracle inputs: do not exempt that whole namespace.
    return path in {"README.md", "ROADMAP.md", "AGENTS.md"} or (
        path.startswith(("docs/", ".agents/skills/")) and path.endswith(".md")
    )


def classify(paths: list[str]) -> tuple[str, str]:
    normalized = sorted({path for path in paths if path})
    if not normalized:
        return "ci", "yes"
    runtime = [path for path in normalized
               if not documentation(path) and path != NARRATIVE_REPORT]
    if not runtime:
        return "active", "no"
    if all(path in PROBE_ONLY for path in runtime):
        return "probe", "yes" if PROBE_QEMU in runtime else "no"
    # Only demonstrated narrow coverage may opt out of full CI and QEMU.
    return "ci", "yes"


def git(*arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def changed_paths(base: str, head: str, *, merge_base: bool = False) -> list[str]:
    revisions = []
    for revision in (base, head):
        if not revision or not revision.strip("0"):
            raise ValueError("missing or zero revision")
        revisions.append(git("rev-parse", "--verify", "--end-of-options",
                             f"{revision}^{{commit}}").decode().strip())
    base, head = revisions
    if merge_base:
        bases = git("merge-base", "--all", base, head).decode().splitlines()
        if len(bases) != 1:
            raise ValueError("no unique merge base")
        base = bases[0]
    # Disable rename detection so a runtime -> docs rename includes BOTH paths.
    result = git("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                 "--name-only", "-z", base, head, "--")
    return [
        item.decode("utf-8", errors="surrogateescape")
        for item in result.split(b"\0")
        if item
    ]


def select(base: str, head: str, event: str) -> tuple[str, str]:
    if event in {"schedule", "workflow_dispatch"}:
        return "nightly", "yes"
    if event not in {"push", "pull_request", "merge"}:
        return "ci", "yes"
    try:
        # PR head: branch contribution, excluding unrelated base advancement.
        # Push: before -> head, including force pushes. Merge: base -> actual merge.
        return classify(changed_paths(base, head, merge_base=event == "pull_request"))
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f"selection unavailable; using full CI/QEMU: {error}", file=sys.stderr)
        return "ci", "yes"


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default="push")
    parser.add_argument("--development", action="store_true",
                        help="JSON development-only eligibility; does not change release CI/admission")
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args(arguments)
    if args.development:
        # Use exact committed objects, never claim that a dirty checkout was
        # tested. The caller freezes/checks the checkout before executing tests.
        try:
            paths=changed_paths(args.base,args.head,merge_base=args.event=='pull_request')
            result=development_decision(paths)
            result['base_revision']=git('rev-parse','--verify','--end-of-options',args.base+'^{commit}').decode().strip()
            result['head_revision']=git('rev-parse','--verify','--end-of-options',args.head+'^{commit}').decode().strip()
            result['head_tree']=git('rev-parse',result['head_revision']+'^{tree}').decode().strip()
            result['selector_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            if args.event not in {'push','pull_request','merge'}:
                result.update(eligible=False,tier='ci',remote_ci_before_experiment=True,
                              experiment_scope='none',reason='unsupported development event')
        except (OSError,ValueError,subprocess.CalledProcessError) as error:
            result=development_decision([])
            result['reason']='revision resolution failed: '+type(error).__name__
        print(json.dumps(result,sort_keys=True))
        return 0
    tier, qemu = select(args.base, args.head, args.event)
    print(f"tier={tier}")
    print(f"qemu={qemu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
