# Generation-8 lifecycle admission — offline

Date: 2026-08-03

Result: **PASS offline at commit `c667718`; now consumed**. One exact Generation-8 recovery
image was admitted for at most one connected-preflight-gated, RAM-only
diagnostic lifecycle. At this checkpoint the phone remained in exact Alpine
fallback and Generation 8 was unbooted. No fastboot command, reboot, payload
transfer, privileged host mutation, or phone-storage access occurred.

## Exact one-shot admission

`manifests/temporary-boot-images.tsv` contains exactly one active `allow` row:

- path:
  `build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-a/repack/stable-recovery-a.avb.img`
- size: `100663296` bytes;
- SHA-256:
  `f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415`;
  and
- basis: `one generation-8 NetworkManager-empty-field-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash`.

The two retained issuer trees remain byte-identical. The artifact inventory
continues to describe the offline issuance record as `authority=none`; central
policy is the separate one-shot execution authority. Direct connected actions
still require the Generation-8 live profile and lifecycle guard.

Repository tests require exactly one policy row with the Generation-8 image
path, as well as exactly one global `allow` row and the exact one-shot basis.
This rejects a duplicate or conflicting row even when the valid row remains.

## Fail-closed evidence

The executable policy checks require:

- exactly one global active row, one Generation-8 path row, and one exact
  Generation-8 path/basis row;
- one unique `100663296`-byte artifact-manifest entry with the exact SHA-256;
- lifecycle-only connected preflight and boot, while direct invocations reject
  before host inspection;
- lifecycle preflight passes its explicit lifecycle guard to the Generation-8
  live gate, and tests require direct unguarded actions to reject for that
  exact reason;
- guarded connected preflight and boot both re-check central policy at action
  time and reject missing or duplicate Generation-8 rows before host
  inspection;
- the immutable Generation-8 offline profile continuing to reject connected
  actions;
- both issuer trees, every pinned recovery component, the generation record,
  AVB salt/digest, trust root, runtime manifest, and host verifier passing
  exact artifact preflight; and
- one diagnostic `run` process performing complete connected preflight before
  its single temporary-boot call.

Local diagnostic key admission also passed against the dedicated non-fixture
Ed25519 client identity, 37,735-entry sealed v3 package, exact diagnostic
candidate record, and installed signed runtime bundle. That action used no
phone, privilege, network listener, or external service.

Focused recovery, live-gate, and 61-case lifecycle suites pass after review.
Claude's tool-free advisory review first identified the policy-name uniqueness
gap, then exposed the lifecycle-preflight guard wiring and action-time policy
mutation coverage gaps; all were corrected. The complete local
`scripts/host/test-repository-linux.sh ci` tier passes after those changes.

The compatibility chain now pins:

- artifact manifest SHA-256:
  `08ddb967328c6d80a7beebcafc3602b91117d3694616c09221ce3bdd0cc6ed2b`;
  and
- minimal-headless compatibility profile SHA-256:
  `3e2ce5b19e3d84c4ee2c8b554b56a0beeb6d4b5699b15196906daae8b63838da`.

## Required transition

This checkpoint grants no retry. After any lifecycle result—including a
pre-commit rejection, ambiguous transport loss, target acceptance, or failed
fallback proof—the Generation-8 policy row must be removed and the artifact
recorded as consumed in the same evidence/publication update. It must never be
flashed.

Connected preflight and temporary boot remained prohibited until this exact
checkpoint is reviewed, committed, pushed, and green in GitHub Actions.

That transition completed in GitHub Actions run `30832269180`. The sole
admitted lifecycle was subsequently rejected safely and consumed; see the
[Generation-8 live result](2026-08-03-generation-8-recovery-acm-stability-live.md).
