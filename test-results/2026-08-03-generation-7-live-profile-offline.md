# Generation-7 lifecycle profile — offline transition

Date: 2026-08-03

Result: **PASS offline**. The diagnostic lifecycle now selects the
exact Generation-7 recovery through a distinct live-capable profile. Generation
7 remains absent from temporary-boot policy. No connected preflight,
credential use, privileged host mutation, fastboot command, or phone action
occurred.

## Exact transition

The immutable `headless-diagnostic-generation7-offline-v1` profile continues
to permit only `policy-preflight` and `artifact-preflight`. The new
`headless-diagnostic-generation7-live-v1` profile pins the identical:

- AVB image `d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901`;
- raw recovery `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`;
- generation record `8127197dcf0704bf7bee81a7b25a604fb9e7c9b752ba6d9523e073de2bf9799e`;
- recovery kernel, initramfs, config, control, fetcher, verifier, signed bundle,
  runtime manifest, trust root, host verifier, AVB salt, and AVB digest.

The lifecycle selector changed from consumed
`headless-diagnostic-generation6-live-v1` to
`headless-diagnostic-generation7-live-v1`. No payload or artifact identity
changed.

## Fail-closed evidence

- both Generation-7 profiles pass the exact five-field policy mutation matrix;
- both profiles pass complete artifact preflight against both independent
  production issuer trees;
- the offline profile rejects connected preflight and boot before host
  inspection;
- the live profile rejects direct boot before host inspection unless the
  one-shot lifecycle guard is present;
- all 56 lifecycle tests select Generation 7;
- the in-place generation-record mutation still fails exact artifact
  preflight; and
- `manifests/temporary-boot-images.tsv` remains unchanged and contains no
  Generation-7 row or any `allow` row.

This profile wiring itself does not admit connected preflight or boot. A
separate reviewed central-policy change is required before any connected
action. No phone or credential action is part of this transition.

## Verification

- `scripts/host/test-run-minimal-headless-live-cycle.py`: 56 tests passed;
- `scripts/host/test-run-stable-recovery-live-gate.sh`: passed;
- shell syntax, Python compilation, and `git diff --check`: passed; and
- `scripts/host/test-repository-linux.sh ci`: passed in full with
  `PASS repository Linux ci tier`.

The constrained, read-only Claude review raised three questions: whether an
allowed lifecycle boot is exercised, whether the controller exports the new
lifecycle guard, and whether other live-profile actions bypass that guard.
The existing lifecycle fixture proves the first two by accepting its boot call
only when Generation 7 and all three authorization guards are exact; all 56
tests passed after the selector change. The live gate's top-level action
allowlist rejects every verb except `policy-preflight`, `artifact-preflight`,
`preflight`, and `boot`, while the Generation-7 live profile applies its extra
guard to `boot`. No review finding required a code change.
