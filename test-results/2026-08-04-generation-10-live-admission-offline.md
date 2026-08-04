# Generation-10 lifecycle admission — offline result

Date: 2026-08-04

Result: **PASS offline with constrained review and complete local CI;
publication and exact-head GitHub CI remain pending**.
Central temporary-boot policy now admits exactly one Generation-10
PREPARE-progress-instrumented diagnostic lifecycle after connected preflight.
Generation 10 remains unbooted and has no durable boot claim. No phone,
credential, privileged host action, USB discovery, fastboot command, reboot,
network listener, NFS export, or phone-storage access occurred.

## Predecessor checkpoint

The distinct `headless-diagnostic-generation10-live-v1` profile was published
at `adc41239e7d955dca56d8bee7a7c219a5ddde445` and passed exact-head GitHub
Actions run `30869110964`: recovery-core passed in 3m47s and QEMU in 42s.
Central policy still had zero `allow` rows at that checkpoint.

## Exact admission

The single active policy row admits only:

- path
  `build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img`;
- size `100663296` bytes;
- SHA-256
  `b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51`;
  and
- basis `one generation-10 PREPARE-progress-instrumented diagnostic lifecycle
  after connected preflight; remove after any result; never flash`.

Artifact inventory remains separate from boot authority. Its Generation-10
row records issuance `authority=none`, `unbooted`, and no boot claim while
describing the central one-shot admission. The row authorizes neither flashing
nor a second lifecycle.

## Fail-closed evidence

- central policy contains exactly one `allow` row, and its path, status, and
  basis match the Generation-10 live profile exactly;
- consumed Generations 0–9 remain absent from boot policy;
- the immutable offline profile still rejects connected actions before host
  inspection;
- the live profile still requires the lifecycle guard for every connected
  action;
- policy fixtures derive missing, duplicate, and wrong-basis states from the
  admitted policy and reject both preflight and boot before host inspection;
- the early and post-resolution policy checks independently require one exact
  row and exact basis;
- the inventory check rejects a consumed artifact even if policy is altered;
  and
- no connected action is part of this admission checkpoint.

## Integrity chain

The policy-aware inventory role advances the compatibility hash chain to:

- artifact manifest:
  `624689034fb53df179856c6f385afa6b2cdc953546adb90590975d5479c2e643`;
- minimal-headless compatibility profile:
  `62a2a96822bb4a4e1733105adb07b242d294aacd50a79f77a49cef1c51f975e6`;
  and
- source/DT contract checkpoint identity (informational outer digest; no
  tracked consumer pins it):
  `3de523e96fe36946ab9f91eff4dc5c4e45b3186d1bac3083ff03c602ec640e1a`.

## Verification

- shell syntax, JSON parsing, Markdown indentation, and `git diff --check`:
  pass;
- artifact inventory versus boot-policy separation: pass;
- stable-recovery live gate, including exact policy-shape rejection and all
  retained Generation-10 tree/profile artifact checks: pass;
- 64 minimal-headless lifecycle tests: pass;
- 39 compatibility-oracle tests: pass;
- 74 source/DT contract tests: pass with one expected optional-source skip;
- 31 native recovery-fetch tests: pass;
- constrained tool-free Claude Opus re-review after corrections:
  `NO FINDINGS`; and
- complete `scripts/host/test-repository-linux.sh ci`: pass.

The next gate is publication and exact-head GitHub CI. Only this reviewed,
published, exact-head-green admission may proceed to a separate connected
preflight checkpoint.
