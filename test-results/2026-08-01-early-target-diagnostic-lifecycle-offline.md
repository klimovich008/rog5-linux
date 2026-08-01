# Early-target diagnostic lifecycle integration

Date: 2026-08-01

Result: **PASS — the diagnostic collector is supervisor-ready before the
non-retryable recovery commit, and the normal r2 lifecycle remains unchanged.**

This run was hardware-free. It contacted no phone or external service, used no
credential, loaded no production signing key, and created no boot authority.

## Exact admission

The deployment-key verifier now has two explicit, fail-closed profiles. The
historical `headless-ssh-r2` default retains its exact candidate, bundle,
network-root initramfs, and target identities. The new
`early-target-diagnostic-v1` profile accepts only:

- candidate and bundle `headless-netroot-early-diag-v1`;
- bundle profile `diagnostic-initramfs-v1`;
- target `headless-netroot-early-diag`;
- the accepted 40,049,152-byte Linux 7.1.4 Image;
- the corrected 102,870-byte ROG Phone 5 DTB; and
- the 6,010,870-byte diagnostic initramfs with SHA-256
  `10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c`.

Both profiles still derive the public half from one caller-owned private key,
reject the tracked fixture key, and require the key-bound v3 Arch package to
match the candidate and signed manifest root identities. Substituting the
normal reporter-free initramfs into the diagnostic candidate is rejected.

## Supervisor ordering

The one-shot lifecycle exposes separate `diagnostic-key-preflight`,
`diagnostic-preflight`, and `diagnostic-run` actions. Diagnostic execution:

1. captures the signed recovery USB anchor and exact recovery NCM state;
2. starts the receive-only collector and waits for its flushed readiness line;
3. refuses before the bundle server or recovery control starts if readiness is
   absent, and refuses before the NFS/COMMIT handoff if the ready collector
   exits;
4. transfers the exact signed diagnostic bundle and performs one existing
   prepare/commit transaction;
5. starts the unchanged read-only NFS handoff;
6. waits for one canonical mode-`0600` diagnostic evidence record;
7. never attempts target host-key pinning, target SSH, or normal runtime
   acceptance;
8. verifies the exact Alpine fallback and continuously clean host state; and
9. resolves the durable intent as `FALLBACK_RETURNED`, never
   `TARGET_ACCEPTED`.

A collector rejection remains a failed diagnostic cycle, but its bounded
evidence is preserved, the commit is not retried, and fallback/cleanup/intent
resolution still run exactly once. The normal lifecycle continues to resolve
`TARGET_ACCEPTED` only after its strict-SSH runtime record and verified
fallback.

## Verification

- 16 deployment-key admission tests pass, including the exact diagnostic
  chain, normal-initramfs substitution rejection, fixed-name policy
  resolution, and immutable non-aliased artifact pins.
- 34 lifecycle methods pass. Diagnostic-specific cases cover phone-free
  preflight, ready-before-commit ordering, accepted capture, rejected capture,
  retained mode-`0600` evidence, no target SSH/runtime path, one commit, exact
  fallback resolution, exact-line readiness, post-readiness liveness,
  independently bound canonical evidence, distinct target/fallback boot IDs,
  and refusal before commit when collector startup fails.
- Python syntax compilation and `git diff --check` pass.

The first independent review found post-readiness liveness, evidence binding,
and mutable admission-policy gaps; each now has a hostile regression. The
independent closure review reports no remaining actionable findings, and the
complete repository `ci` tier passes the corrected diff. Production signing,
GitHub publication and CI, host installation, and every phone action remain
separate future gates.
