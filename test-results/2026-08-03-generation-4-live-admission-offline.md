# Generation-4 live admission — offline

Date: 2026-08-03

Result: **PASS reviewed offline**. One exact Generation-4 recovery is admitted
for one connected-preflight-gated, RAM-only diagnostic lifecycle. Focused and
complete local CI pass. No phone interface, credential, reboot, connected
preflight, or boot was used.

## Exact authority

`manifests/temporary-boot-images.tsv` contains one `allow` row:

- image: `build/stable-recovery-generation4-timeout-lattice-20260803-a/repack/stable-recovery-a.avb.img`
- size: `100663296`
- SHA-256: `220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d`
- basis: one Generation-4 timeout-lattice diagnostic lifecycle after connected
  preflight; remove after any result; never flash

The artifact's issuance record remains `authority=none`; that record did not
silently acquire authority. The reviewed central policy row is the sole boot
authority. The immutable offline profile still rejects connected actions, and
the live profile still rejects direct boot outside the one-shot lifecycle
controller.

## Test-first evidence

Before the policy changed, both the generic recovery-policy test and the
stable-recovery live-gate test failed because the exact one-shot row was
absent. After the single row was added, both pass. They enforce:

- at most one active `allow` row and exactly one manifest-backed identity;
- exact Generation-4 path, status, one-shot basis, size, and SHA-256;
- absence of every consumed diagnostic generation from boot policy;
- offline-profile refusal before host inspection;
- direct live-profile boot refusal outside the lifecycle controller; and
- no flash, erase, format, slot-selection, ADB, or SSH path in the live gate.

The complete `scripts/host/test-repository-linux.sh ci` tier passes with the
admission present, including documentation links, all 42 lifecycle tests, the
recovery policy, stable-recovery gate, and compatibility oracle.

## Review

The first constrained, credential-free Claude Opus review found two real
consistency gaps: tests did not match the connected-preflight phrase exactly,
and the artifact inventory role still said `not admitted`. The basis is now
matched as one exact string, and the inventory distinguishes its offline
`authority=none` issuance record from the separate central-policy admission.
That inventory correction changed the sealed artifact-manifest metadata hash
to `86dafd0dda38cf5ebcc279c3013e4473fdc4f184f0ef6db923f5645e95040910`;
the compatibility profile was updated and its 39 hostile tests pass.
The first complete rerun then correctly rejected the changed compatibility
profile at the separate source/DT contract boundary. Its downstream pin is now
`079b244353d982a62a00da12e050050364931fd20b34134004fb8f8fcd1f3875`;
the 74 source/DT tests pass after that explicit update.

The review also questioned the global one-row rule, but the existing policy
parser already rejects `allow_count > 1`, while the exact Generation-4 test
requires one row. The follow-up review evaluated those checks together and
returned `NO FINDINGS`.

## Consumption rule

After any lifecycle result, including a failed or ambiguous boot, consume the
admission in one versioned change:

1. remove the Generation-4 `allow` row from
   `manifests/temporary-boot-images.tsv`;
2. retain the artifact but rewrite its inventory role as consumed,
   offline-only, and never-retry-or-flash;
3. invert both recovery-policy tests back to absence from boot policy plus the
   exact consumed inventory identity;
4. recompute `artifact_manifest_sha256` in the compatibility profile and then
   repin that profile's SHA-256 in the source/DT contract; and
5. run complete local review/CI and publish the consumed checkpoint.

Do not retry the admitted image and never flash it. The live gate does not
edit Git, so this versioned transition is part of lifecycle resolution rather
than an automatic device-side action.

## Next gate

Run complete local CI and constrained read-only review, publish the exact
checkpoint, and require green GitHub CI. Only then run connected preflight;
the phone must not boot during that preflight.
