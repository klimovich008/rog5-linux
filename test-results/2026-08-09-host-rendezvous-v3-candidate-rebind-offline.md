# Host-rendezvous v3 diagnostic candidate rebind — offline

Date: 2026-08-09

Result: **PASS offline composition; HOLD candidate admission.** The existing
authority-free `headless-netroot-early-diag-v2` wire identity now binds the
reviewed host-rendezvous v3 diagnostic initramfs. This corrects stale candidate
composition; it does not prove that the host-readiness race caused Generation
12 and creates no phone boot authority.

The initial implementation range is
`12ed3bcbbfc3ad51b72175883c5810ad9ebb87ab..765be2ef8293636ddb1cdec39edef11dd200293c`.
No phone interface, phone storage, production credential, production signing
key, policy row, issuance record, flash, wipe, erase, slot operation,
persistent installation, or phone boot was used.

## Concrete defect and patch

The critical readiness review produced and clean-twin verified a 6,013,458-byte
v3 diagnostic initramfs with bounded source-bound TCP/2049 rendezvous and exact
host-port terminal reporting. The tracked current candidate and its active
consumers still referenced the superseded 6,011,687-byte v2 initramfs. A future
offline composition would therefore have silently omitted the reviewed fix.

The patch:

- changes only the candidate's `initramfs.cpio.gz` path, size, and SHA-256;
- updates every active exact candidate and runtime-manifest pin;
- retains the `headless-netroot-early-diag-v2` target/bundle identity so the
  fixed target, collector, and recovery-control lineage vocabulary does not
  change;
- preserves the historical v2 component inventory row and all consumed
  Generation-12 evidence;
- adds a two-package exact-twin regression and hostile refusal of an external
  candidate that substitutes the stale v2 initramfs;
- leaves `manifests/temporary-boot-images.tsv` at zero `allow` rows and creates
  no Generation-13 implementation or claim.

The fail-first candidate contract rejected the old state in 0.062 seconds:

```text
FAIL diagnostic candidate omits fixed token: "path":
"artifacts/early-target-diagnostic-v3/rog5-early-target-diagnostic-initramfs.cpio.gz"
```

## Exact identities

| Item | Size | SHA-256 |
|---|---:|---|
| candidate record | 1,411 | `41c23330fd95d7c7426434ae3c19f948208f221ddc4f502859137f22b7eab9cf` |
| target Image | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| target DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| v3 target initramfs | 6,013,458 | `94edd6254403759db423970e8cd313e4edde2e744f042f87f9f59815f8bbcffc` |
| canonical runtime manifest | 834 | `54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc` |
| stable-recovery initramfs | 7,603,769 | `dd224fb964d4d19c87d8107945ea835c62b97bc34c4faf50cfcc47a5255947c1` |
| observation-only initramfs | 5,371,780 | `613d6e3e61d7818693c0d26b0b7c252479941cc25c98e897ef6aa30469e770db` |
| wrapper kernel Image | 50,498,048 | `05f702c7f9ed4ebb7f416377b769a80b7f17c8443d7c8d75b374995509899e80` |
| raw boot-v3 wrapper | 58,109,952 | `e8c010ff723a45eb17cbdf4acb9510f2cc4783caaefa70eca6d8137ee7f92e23` |
| unsigned AVB wrapper | 100,663,296 | `142f44f461ab82c586bf06136358370356162826433d11639237299c107706ba` |

The complete builder used two clean, separate ASUS 5.4 output trees. Kernel,
raw wrapper, unsigned AVB wrapper, candidate record, runtime manifest, bundle
inventory, file modes, and source seals were byte-identical. The output passed
embedded-key AVB footer/hash verification. Its generated Ed25519 trust key was
disposable (`26f50bab…f4b`), the private half was destroyed, and the final
record says `authority=none`.

The retained validation tree is
`build/host-rendezvous-v3-offline-20260809-r1` and occupies 9.4 GiB. It was not
deleted because it is the clean-twin evidence for this checkpoint. No broader
retention deletion was performed.

## Tests and timing

Focused tests were run before the complete repository tier:

- candidate offline contract: PASS, 0.215 s after the 0.062 s fail-first run;
- candidate packager: initial artifact-resident 14/14 PASS in 0.791 s; after
  review, the exact-current-manifest check, self-contained byte/mode twin, and
  current-template stale-v2 refusal pass 14/14 in 0.421 s and also pass from a
  clean Git archive with all ignored production artifacts absent in 0.400 s;
- deployment-candidate adapter: 3/3 PASS, 0.157 s;
- signing-input staging: 15/15 PASS, 2.813 s;
- exact diagnostic admission verifier: 16/16 PASS, 1.235 s;
- deployment-builder contract: PASS, 1.374 s;
- stable-recovery lifecycle/zero-admission gate: PASS, 177.383 s
  (`user=37.595`, `sys=52.880`).

The first complete `ci` attempt correctly failed after 39.131 seconds because
the changed artifact inventory had not been propagated to the core
compatibility profile's exact manifest hash. Before the fix, 19 hostile cases
failed and four errored at that earlier fail-closed boundary. After updating
the canonical pin to `30e6db9b…8fd4`, the focused core oracle passes 39/39 in
0.499 seconds. This was a real active-pin defect found by the required final
gate, not an expected failure fixture.

The clean disposable twin composition passed in 2,465.364 seconds
(`user=53.083`, `sys=59.629`). The preceding comparable v2 clean twin took
2,332.019 seconds, so this run was 133.345 seconds (5.7%) slower. That is one
pair of host measurements, not a performance regression conclusion; clean
kernel LTO dominates both runs and the wrapper/recovery inputs differ.

The final repository `ci` result is recorded below after it completes.

## Independent review

Two independent fixed-range reviews ran in parallel. Both initially found that
the new runtime twin test depended on ignored production artifacts and that
the PR candidate-publication job still pinned the superseded candidate hash.
The specification review also found three active-documentation passages that
still described v2 as current. The standards closure then caught two
historical v2 checkpoints whose wording could misattribute their CI/build
evidence to the current v3 payload.

The fixes make the twin test self-contained while separately checking the exact
current manifest and real-template stale-v2 refusal, bind both workflow and
workflow-contract tests to `41c23330…b9cf`, and distinguish current v3 evidence
from immutable historical v2 evidence. Final reviewer counts are:

- Standards: P0 0, P1 0, P2 0, P3 0;
- Specification: P0 0, P1 0, P2 0, P3 0.

## Recommendation

**HOLD candidate admission.** This checkpoint proves exact, reproducible,
authority-free composition of the already-reviewed offline fix. It still lacks
physical USB-NCM timing and lineage-safe independent target failure evidence.
Do not issue, production-sign, authorize, or boot a successor from this result.
