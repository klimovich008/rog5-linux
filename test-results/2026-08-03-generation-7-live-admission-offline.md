# Generation-7 lifecycle admission — offline

Date: 2026-08-03

Result: **PASS reviewed offline**. One exact Generation-7 recovery image is
admitted for at most one connected-preflight-gated, RAM-only diagnostic
lifecycle. No connected preflight, credential use, privileged host mutation,
fastboot command, phone action, or artifact consumption occurred.

## Exact one-shot authority

`manifests/temporary-boot-images.tsv` contains exactly one `allow` row:

- path:
  `build/stable-recovery-generation7-deferred-profile-fix-20260803-a/repack/stable-recovery-a.avb.img`
- size: `100663296` bytes
- SHA-256: `d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901`
- basis: `one generation-7 deferred-profile-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash`

The image remains the independently twin-reproduced deterministic AVB
successor over unchanged raw recovery
`f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`.
Its issuance record intentionally retains `authority=none`: issuance creates
an artifact but grants no boot authority. The central temporary-boot policy
separately grants this one lifecycle.

## Fail-closed evidence

The executable checks require:

- exactly one global `allow` row;
- the exact Generation-7 path, basis, size, and SHA-256;
- the exact complete inventory role preserving the offline issuance boundary
  and separately admitted central policy;
- lifecycle-only boot, with direct boot rejected before host inspection;
- `diagnostic-run` executing the complete connected preflight before its boot
  call, with the ordering asserted by the lifecycle fixture;
- offline-profile refusal of connected preflight and boot; and
- unique manifest backing for the sole policy row.

The production live gate reads both central policy files for `preflight` and
`boot`, requires one unique matching `allow` row, joins it to the unique
100663296-byte artifact-manifest identity, and hashes the image before device
discovery. The lifecycle's `diagnostic-run` invokes its complete preflight in
the same process immediately before `run`; it does not trust a stale earlier
preflight receipt.

These are admitted-state checks. Removal after every result is the mandatory
state transition. That transition must replace admitted-state assertions with
consumed-state assertions in the same evidence commit. Until then, leaving the
row present describes an unconsumed candidate, not permission to retry it.

The compatibility seals propagate the admitted inventory identity:

- artifact manifest SHA-256:
  `4180b8e6f2eb385a3f81de5f6defa28c3c32b511e9bb0a1aba50526d26dbcd13`
- minimal-headless compatibility profile SHA-256:
  `6cf25a9e7d632a85702e219468605a86dbe6ac577dcb8f3a3a1847b01a32361b`

Focused verification passes:

- recovery inventory and boot-authority separation;
- exact stable-recovery live gate against both production issuer trees;
- all 56 lifecycle tests, including explicit diagnostic preflight-before-boot
  ordering;
- all 39 compatibility-oracle tests;
- all 74 source/DTB tests with one expected optional retained-source skip;
- the complete repository Linux `ci` tier; and
- `git diff --check`.

The first broad constrained Claude response was invalid: it emitted impossible
tool-call text despite the tool-free wrapper and fabricated content for the
untracked result file, so it was discarded. A smaller self-contained code
review confirmed the exact global allow count, policy-to-manifest size/hash
join before discovery, diagnostic preflight-before-boot ordering, and direct-
boot lifecycle guard. Its one alleged shell defect came from an excerpt that
began in the middle of an earlier assertion and is disproved by the passing
shell test. A separate documentation-only review explicitly found all
Generation-7 statements mutually consistent; its unrelated objection confused
two different historical recovery boots with target execution. No supported
review finding remains.

The first complete-CI attempt hit two unrelated `RawFetchServer.recv` local
socket timeouts. The exact 31-test native-fetch suite immediately passed in
isolation, and the complete CI tier then passed from the start with
`PASS repository Linux ci tier`; no code was changed to hide the transient.

Exact GitHub publication remains required before connected preflight. A
temporary boot may occur only if that connected preflight passes. After any
lifecycle result, including an ambiguous failure, the policy row must be
removed and the artifact marked consumed; it must never be retried or flashed.
