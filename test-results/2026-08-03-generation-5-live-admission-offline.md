# Generation-5 lifecycle admission — offline

Date: 2026-08-03

Result: **PASS reviewed offline**. One exact Generation-5 recovery image is
admitted for at most one connected-preflight-gated, RAM-only diagnostic
lifecycle. No connected preflight, credential use, host mutation, fastboot
command, phone action, or artifact consumption occurred.

## Exact one-shot authority

`manifests/temporary-boot-images.tsv` contains exactly one `allow` row:

- path:
  `build/stable-recovery-generation5-choreography-20260803-a/repack/stable-recovery-a.avb.img`
- size: `100663296` bytes
- SHA-256: `abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a`
- basis: `one generation-5 host-choreography diagnostic lifecycle after connected preflight; remove after any result; never flash`

The image remains the independently twin-reproduced deterministic AVB
successor over unchanged raw recovery
`f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`.
Its issuance record intentionally retains `authority=none`: issuance creates
an artifact but grants no boot authority. The central temporary-boot policy
separately grants this one lifecycle.

## Fail-closed evidence

The tests were changed before the policy and inventory implementation. They
first failed with `generation-5 temporary-boot admission is not exact and
one-shot`, proving the new assertions exercised the missing authority. The
implemented checks now require:

- exactly one global `allow` row, not merely one matching Generation-5 row;
- the exact path, basis, size, and SHA-256 through the live gate;
- the exact complete Generation-5 artifact inventory role, including the
  offline issuance boundary and separately admitted central policy;
- lifecycle-only boot, with direct boot rejected before host inspection;
- offline-profile refusal of connected preflight and boot; and
- removal of the allow row after every result, with no retry or flash.

The compatibility seals propagate the admitted inventory identity:

- artifact manifest SHA-256:
  `7820475c0424e2b76f0b642497eab502e198919571f30054fe0a84ff224695fc`
- minimal-headless compatibility profile SHA-256:
  `0574770c291b0d2ae977501a3066de28a04848ffce75388908692c6650010ca6`

Focused recovery/live-gate tests, all 39 compatibility tests, all 74
source/DTB tests (one optional retained-source skip), and the complete
`scripts/host/test-repository-linux.sh ci` tier pass.

A bounded, tool-free, non-persistent Claude review first identified that the
tests should state the global one-row invariant and compare the full inventory
role; both findings were implemented. Its follow-up suggestion to hash the
temporary-boot policy inside another tracked compatibility JSON was rejected:
the boot consumer opens and validates the current exact policy on every
preflight and boot, while the reviewed Git commit binds that policy. Adding
the same mutable indirection would not add authenticity and would blur the
intentional separation between artifact issuance and one-shot authority.

Publication and GitHub Actions evidence remain to be added. After those pass,
the next permitted phone interaction is read-only device discovery followed
by one fresh `diagnostic-preflight`. A temporary boot may occur only if that
connected preflight passes. After any lifecycle result, including ambiguous
failure, the policy row must be removed and the artifact marked consumed; it
must never be retried or flashed.
