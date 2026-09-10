# Generation-5 lifecycle profile — offline transition

Date: 2026-08-03

Result: **PASS reviewed offline**. The diagnostic lifecycle now selects the
exact Generation-5 recovery through a distinct live-capable profile, while
Generation 5 remained absent from temporary-boot policy at this transition.
No connected preflight, credential use, host mutation, or phone action
occurred.

## Exact transition

The immutable `headless-diagnostic-generation5-offline-v1` profile continues
to permit only `policy-preflight` and `artifact-preflight`. The new
`headless-diagnostic-generation5-live-v1` profile pins the identical recovery,
kernel, raw wrapper, initramfs, control, fetcher, verifier, runtime manifest,
trust root, host verifier, AVB-generation record, AVB salt, and AVB digest.

The diagnostic lifecycle selector changed from consumed
`headless-diagnostic-generation4-live-v1` to
`headless-diagnostic-generation5-live-v1`. No payload or artifact identity
changed.

## Fail-closed evidence

- both Generation-5 profiles pass the exact five-field policy mutation matrix;
- both pass the complete retained-artifact preflight;
- the offline profile rejects connected preflight and boot before host
  inspection;
- the live profile rejects direct boot before host inspection unless the
  one-shot lifecycle guard is present;
- all 47 lifecycle tests pass with Generation 5 selected; and
- `manifests/temporary-boot-images.tsv` remains unchanged and contains no
  Generation-5 row.

The complete `scripts/host/test-repository-linux.sh ci` tier passes on the
implementation tree. A bounded, tool-free, non-persistent Claude Opus review
checked for authority leaks, stale Generation-4 selection, missing mutation or
artifact coverage, and shell/Python inconsistencies and returned
`NO FINDINGS`.

The later
[one-shot admission](2026-08-03-generation-5-live-admission-offline.md) adds
the separate reviewed policy row. This report remains the phone-free profile
transition and does not itself grant boot authority.
