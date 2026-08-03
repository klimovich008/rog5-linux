# Generation-9 issuer readiness — offline

Date: 2026-08-03

Result: **PASS test-first readiness; no retained Generation-9 output or boot
authority exists.**

## Scope

Generation 8 is consumed and absent from temporary-boot policy. The bounded
recovery ACM classifier is published and green, but a consumed wrapper can
never be retried. Before creating a successor, the generic AVB-generation test
now issues two disposable synthetic Generation-9 trees.

The regression proves:

- byte-identical A and B outputs across two separate issuer invocations;
- byte-identical A/B AVB wrappers and raw images within one invocation;
- unchanged raw recovery bytes;
- non-reuse of every Generation 1–8 A and B AVB wrapper;
- exact `generation=9` salt derivation, AVB descriptor salt, and digest; and
- `authority=none` in the immutable generation record.

## Verification

- `scripts/host/test-issue-stable-recovery-avb-generation.sh` — PASS.
- `scripts/host/test-recovery-linux.sh` — PASS; inventory remains separated
  from boot authority.
- `scripts/host/test-run-stable-recovery-live-gate.sh` — PASS; retained
  profiles stay exact, guarded, twin-built, and boot-only.
- no Generation-9 path, profile, artifact row, or allow row existed before or
  after the disposable test.

The constrained Claude invocation returned a fabricated tool transcript rather
than a review verdict and is not used as evidence. Direct source review and the
three real suites above cover the claimed checks.

No retained wrapper, signing credential, privilege, host network mutation,
phone command, reboot, fastboot/ADB/SSH connection, or phone storage access was
used. Retained twin issuance remains a separate next step after this readiness
change is reviewed, committed, pushed, and green at exact head.
