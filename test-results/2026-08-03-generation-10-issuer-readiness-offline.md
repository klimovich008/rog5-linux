# Generation-10 issuer readiness — offline

Date: 2026-08-03

Result: **PASS hardware-free test-first readiness; signing inputs preflighted;
no Generation 10 artifact issued or booted**.

## Purpose

The next recovery wrapper must carry the bounded PREPARE progress responder.
Before any production signing operation, the generic AVB-generation issuer
was exercised twice at Generation 10 on synthetic wrapper inputs and required
to remain distinct from every Generation 1–9 result.

## Credential preflight

The guarded diagnostic deployment launcher ran in
`--signing-input-preflight` mode against the existing external recovery key
and immutable diagnostic candidate record. The preflight validated and
privately staged both inputs, scrubbed their paths from the child environment,
destroyed the temporary snapshot, and exited before signing or creating an
output root:

```text
PASS guarded deployment signing inputs staged, validated, scrubbed from the child environment, and destroyed without signing
```

The external inputs remained:

| Input | Mode | Size | SHA-256/derived identity |
|---|---:|---:|---|
| production recovery private key | `0600` | 119 | derived raw public key `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| diagnostic candidate record | `0444` | 1408 | `7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8` |

The PASS line is emitted by the guarded launcher. The table is separately
transcribed from read-only post-preflight `stat`, candidate SHA-256, and
derived-public-key SHA-256 checks on this host; it is evidence for this run,
not output claimed from the launcher itself.

No private key bytes, path-bearing build record, or credential snapshot were
written to Git.

## Issuer regression

`test-issue-stable-recovery-avb-generation.sh` now creates two Generation-10
trees on synthetic canonical inputs and proves:

- A/B AVB and raw twins match within each invocation;
- both independent invocations match byte-for-byte;
- raw payloads remain identical to the canonical source;
- the generation record and command output are deterministic;
- the canonical salt binds `raw_sha256` plus `generation=10`;
- the descriptor digest is independently recomputed from the salt plus raw
  bytes, and the generation record matches it exactly;
- both complete 11-file output inventories are exact, contain no extra file,
  and match across invocations;
- the `authority=none` field is exact; and
- neither twin reproduces any synthetic Generation 1–9 AVB wrapper.

The focused shell syntax check and complete issuer regression pass:

```text
PASS stable-recovery AVB generation issuance is deterministic, legacy-reproducing, descriptor-bound, and fail-closed
```

`scripts/host/test-repository-linux.sh ci` also passes the complete
hardware-free repository tier. A constrained Claude Opus review identified
and drove the independent digest, exact inventory, both-successor,
non-vacuous predecessor, and evidence-wording corrections; its targeted
re-review returned `NO FINDINGS`.

## Boundary and next gate

This checkpoint used no production signing operation, phone interface,
fastboot, ADB, recovery transport, reboot, boot, flash, wipe, slot change, or
phone-storage access. No Generation-10 image, generation record, lifecycle
profile, inventory row, or temporary-boot admission was created.

After review, publication, and exact-head CI, the next separate operation may
twin-build the progress-enabled recovery with the existing production trust
root. The resulting fresh raw wrapper must then be issued twice as an exact
Generation-10 AVB successor and retained offline with `authority=none` before
any live profile or central admission exists.
