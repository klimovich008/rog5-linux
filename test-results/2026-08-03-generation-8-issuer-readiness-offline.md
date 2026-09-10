# Generation-8 issuer readiness — offline

Date: 2026-08-03

Result: **PASS test-first readiness; no production output**. The generic
AVB-generation issuer is now regression-tested through Generation 8 before it
is allowed to create either retained successor twin.

## Trusted input audit

The retained production source remains present below the ignored build tree.
Its canonical generation-zero AVB image is
`eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6`,
and its raw recovery is
`f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`.
Both retained Generation-7 issuer twins are present and their generation
record identifies that exact source/raw pair. Generation 7 remains consumed.

The pre-issuance host/fallback checkpoint is pushed at `684a209`. GitHub
Actions
[run `30822205991`](https://github.com/klimovich008/rog5-linux/actions/runs/30822205991)
passed `qemu-system` in 32 seconds and `recovery-core` in 3 minutes 26 seconds.

## Generation-8 regression

The hardware-free issuer test now creates two disposable synthetic
Generation-8 outputs and proves:

- byte-identical A outputs across both runs;
- byte-identical B outputs across both runs;
- byte-identical A/B AVB wrappers and raw images within one run;
- unchanged raw payloads;
- non-reuse of every Generation 1–7 A and B AVB wrapper;
- exact `rog5-stable-recovery-avb-generation-v1` salt derivation for
  `generation=8`;
- descriptor salt and digest agreement with the immutable generation record;
  and
- `authority=none`.

The focused issuer suite passes. The first constrained Claude Opus review
found that the new block proved cross-run outputs but did not independently
pin same-run A/B equality. Both AVB and raw comparisons were added; the suite
passed again and the final self-contained review returned `PASS`.

## Boundary

No retained Generation-8 directory, AVB image, generation record, artifact
inventory row, lifecycle profile, temporary-boot policy row, signing action,
credential use, phone contact, or host privilege occurred. Production
issuance remains a separate next step after this exact test-first checkpoint
is committed, pushed, and green.
