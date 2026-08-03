# Generation-8 lifecycle profile — offline transition

Date: 2026-08-03

Result: **PASS offline**. The diagnostic lifecycle now selects exact
Generation-8 recovery through a distinct live-capable profile. Generation 8
remains absent from temporary-boot policy. No connected preflight, credential
use, privileged host mutation, fastboot command, reboot, or phone action
occurred.

## Exact transition

The immutable `headless-diagnostic-generation8-offline-v1` profile continues
to permit only `policy-preflight` and `artifact-preflight`. The new
`headless-diagnostic-generation8-live-v1` profile pins the identical:

- AVB image `f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415`;
- raw recovery `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`;
- generation record `9805809c27e1fe47efcbc7561fe5289e81d789beba231acbac59c32a67ae59d5`;
- AVB salt `a8563ded9a34767ed97ed4f9130361a1b4efadc91ee7294d9a212caf59e53899`;
- AVB digest `b297100d269798d4eaf46b37899c3cf9196f7c076df3a31d39fe3d2db5915dbc`;
  and
- recovery kernel, initramfs, config, control, fetcher, verifier, signed
  bundle, runtime manifest, trust root, and host verifier.

The lifecycle selector changed from consumed
`headless-diagnostic-generation7-live-v1` to
`headless-diagnostic-generation8-live-v1`. No payload, artifact, inventory,
credential, or central-policy identity changed.

## Fail-closed evidence

- both Generation-8 profiles pass the exact five-field policy mutation
  matrix;
- both profiles pass complete artifact preflight against both host-local
  issuer trees;
- the offline profile rejects connected preflight and boot before host
  inspection;
- the live profile rejects direct connected preflight and boot before host
  inspection unless the one-shot lifecycle guard is present;
- even with that guard, both actions reject on the absent exact central-policy
  row before host inspection;
- all 61 lifecycle tests select exact Generation 8;
- the generation-record mutation still fails exact artifact preflight; and
- `manifests/temporary-boot-images.tsv` remains unchanged with no Generation-8
  row and zero active `allow` rows.

This profile wiring itself does not admit connected preflight or boot. A
separate reviewed central-policy change is required before any connected or
phone-side action.

## Verification

- `scripts/host/test-run-minimal-headless-live-cycle.py`: 61 tests passed;
- `scripts/host/test-run-stable-recovery-live-gate.sh`: passed;
- shell syntax and `git diff --check`: passed; and
- central temporary-boot allow count: zero; and
- complete repository Linux `ci` tier: pass.

The first constrained Claude Opus review confirmed the shared tuple and
authority separation, then identified missing guarded-action coverage, an
unguarded connected-preflight path, a negative test pointed at the real bundle
store, and a missing offline-profile leak assertion. Gen-8 connected
`preflight` and `boot` now both require the lifecycle guard and then verify the
exact central-policy row before host inspection; tests cover both unguarded
and guarded zero-policy rejection using only sandbox paths. The offline-name
leak check and formatting/documentation corrections were also added. The
focused gate passed again and the follow-up Opus review returned `PASS`.

No private credential, recovery signing key, privilege, USB interface, phone,
network listener, NFS export, or phone storage was used.

## CI follow-up

The first pushed run later exposed a timing-dependent failure in the final
fallback reboot *test fixture*. The Generation-8 gate and all recovery suites
had already passed. The [offline race correction](2026-08-03-fallback-reboot-fixture-race.md)
removes the fixture's orphaned wall-clock writer, makes the mock USB return
poll-driven, and adds case-labelled failures without changing production
reboot behavior or any Generation-8 artifact.

The subsequent
[one-shot admission](2026-08-03-generation-8-live-admission-offline.md)
adds the separate exact central-policy row after local credential, artifact,
fallback, and rollback checks. The profile tuple and all recovery bytes remain
unchanged.
