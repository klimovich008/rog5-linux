# Generation-6 lifecycle admission — offline

Date: 2026-08-03

Result: **PASS reviewed offline**. One exact Generation-6 recovery image is
admitted for at most one connected-preflight-gated, RAM-only diagnostic
lifecycle. No connected preflight, credential use, privileged host mutation,
fastboot command, phone action, or artifact consumption occurred.

## Exact one-shot authority

`manifests/temporary-boot-images.tsv` contains exactly one `allow` row:

- path:
  `build/stable-recovery-generation6-signal-fix-20260803-a/repack/stable-recovery-a.avb.img`
- size: `100663296` bytes
- SHA-256: `6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398`
- basis: `one generation-6 signal-mask-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash`

The image remains the independently twin-reproduced deterministic AVB
successor over unchanged raw recovery
`f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`.
Its issuance record intentionally retains `authority=none`: issuance creates
an artifact but grants no boot authority. The central temporary-boot policy
separately grants this one lifecycle.

## Fail-closed evidence

The executable checks require:

- exactly one global `allow` row, not merely one matching Generation-6 row;
- the exact path, basis, size, and SHA-256 through the live gate;
- the exact complete Generation-6 inventory role, preserving the offline
  issuance boundary and separately admitted central policy;
- lifecycle-only boot, with direct boot rejected before host inspection;
- offline-profile refusal of connected preflight and boot; and
- exact admitted-state refusal when the one row is absent, duplicated,
  redirected, or changed.

These are admitted-state checks: accepting zero rows before the cycle would
silently turn a missing admission into a passing release. Removal after every
result is instead the required state transition. That transition must replace
the admitted-state assertions with consumed-state assertions in the same
evidence commit; until then, leaving this row present means the repository
still describes an unconsumed candidate and is not a valid post-run state.

The compatibility seals propagate the admitted inventory identity:

- artifact manifest SHA-256:
  `9b0e945bb6f7c2761d5725414c38260fc8f10f6b355164be908801a053794082`
- minimal-headless compatibility profile SHA-256:
  `bfa988c14bd762d353e5e451448e2566d9dbeb90c1524ed79daacf801cf71303`

Focused recovery/live-gate tests, all 39 compatibility tests, all 74
source/DTB tests (one optional retained-source skip), all 47 lifecycle tests,
and the complete `scripts/host/test-repository-linux.sh ci` tier pass. The
bounded review is resolved below. Exact GitHub publication is the remaining
offline gate.

A bounded tool-free Claude Opus review usefully challenged the distinction
between admitted-state tests and post-result revocation. Its proposal to let
the current tests accept zero rows was rejected because that would weaken the
pre-boot snapshot. The wording above now makes the required atomic consumed-
state transition explicit. The review's path-only concern does not apply:
the live gate joins the unique policy path to the unique artifact-manifest
size/SHA-256 tuple and then hashes the image bytes before any device discovery.
No superseded compatibility hashes remain in current documentation.

After those pass, the next phone interaction is read-only device discovery
followed by one fresh `diagnostic-preflight`. A temporary boot may occur only
if that connected preflight passes. After any lifecycle result, including an
ambiguous failure, the policy row must be removed and the artifact marked
consumed; it must never be retried or flashed.
