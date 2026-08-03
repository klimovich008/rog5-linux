# Generation-6 lifecycle profile — offline transition

Date: 2026-08-03

Result: **PASS reviewed offline**. The diagnostic lifecycle now selects the
exact Generation-6 recovery through a distinct live-capable profile, while
Generation 6 remains absent from temporary-boot policy. No connected preflight,
credential use, privileged host mutation, or phone action occurred.

## Exact transition

The immutable `headless-diagnostic-generation6-offline-v1` profile continues
to permit only `policy-preflight` and `artifact-preflight`. The new
`headless-diagnostic-generation6-live-v1` profile pins the identical recovery,
kernel, raw wrapper, initramfs, control, fetcher, verifier, runtime manifest,
trust root, host verifier, AVB-generation record, AVB salt, and AVB digest.

The diagnostic lifecycle selector changed from consumed
`headless-diagnostic-generation5-live-v1` to
`headless-diagnostic-generation6-live-v1`. No payload or artifact identity
changed.

## Fail-closed evidence

- both Generation-6 profiles pass the exact five-field policy mutation matrix;
- both pass the complete retained-artifact preflight;
- the offline profile rejects connected preflight and boot before host
  inspection;
- the live profile rejects direct boot before host inspection unless the
  one-shot lifecycle guard is present;
- lifecycle tests select Generation 6; and
- `manifests/temporary-boot-images.tsv` remains unchanged and contains no
  Generation-6 row or any `allow` row.

This profile wiring does not admit connected preflight or boot. A separate
reviewed one-row temporary-boot policy change with green local and GitHub CI
remains mandatory before one RAM-only lifecycle. No phone or credential action
is part of this transition.
