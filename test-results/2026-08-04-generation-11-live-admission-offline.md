# Generation-11 lifecycle admission — offline result

Date: 2026-08-04

Result: **PASS offline; independent review and complete local CI pass;
publication and exact-head GitHub CI remain pending**. Central temporary-boot policy now
admits exactly one Generation-11 receive-only NCM-progress diagnostic
lifecycle after connected preflight. Generation 11 remains unbooted and has
no durable boot claim. No phone, credential, privileged host action, USB
discovery, fastboot command, reboot, network listener, NFS export, or
phone-storage access occurred.

## Predecessor checkpoint

The distinct `headless-diagnostic-generation11-live-v1` profile was published
at `2a483ecdc174693634941667bffea9b8a18c999c` and passed exact-head GitHub
Actions run `30908649494`: recovery-core passed in 3m49s and QEMU in 40s.
Central policy still had zero `allow` rows at that checkpoint.

## Exact admission

The single active policy row admits only:

- path
  `build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img`;
- size `100663296` bytes;
- SHA-256
  `8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562`;
  and
- basis `one generation-11 receive-only NCM-progress diagnostic lifecycle
  after connected preflight; remove after any result; never flash`.

Artifact inventory remains separate from boot authority. Its Generation-11
row remains `unbooted`, records issuance `authority=none`, and makes no boot
claim while describing the separate central one-shot admission. The row
authorizes neither flashing nor a second lifecycle.

## Fail-closed evidence

- central policy contains exactly one `allow` row, and its path, status, and
  basis match the Generation-11 live profile exactly;
- consumed Generations 0–10 remain absent from boot policy;
- the immutable offline profile still rejects connected actions before host
  inspection;
- the live profile still requires the one-shot lifecycle controller for every
  connected action;
- fixtures derived from the admitted policy reject missing policy files,
  missing rows, malformed policy and artifact headers, missing and duplicate
  artifact rows, duplicate policy rows, wrong-basis rows, denied status,
  artifact-identity mutation, consumed disposition, and trailing policy or
  inventory fields before host inspection for both `preflight` and `boot`;
- the early and post-resolution policy checks independently require one exact
  row, exact basis, artifact identity, and `unbooted` disposition;
- the generic recovery wrapper rejects Generation diagnostic paths and cannot
  bypass the one-shot lifecycle controller;
- the live gate rejects Generation-11 boot before host inspection unless the
  controller has atomically published its exact private durable
  `BOOT_CLAIMED` record; the fixed consumer then irreversibly enters that
  record before host/device inspection, so a failed first attempt cannot be
  reused;
- the consumer proves that the entered path has the same device, inode, and
  exact bytes as the already-validated descriptor, rejects deterministic
  pathname replacement, and leaves mismatched entered state fail-closed;
- inventory disposition still rejects a consumed artifact even if policy is
  altered; and
- no connected action is part of this admission checkpoint.

## Integrity chain

The policy-aware inventory role advances the compatibility hash chain to:

- temporary-boot policy:
  `889ee216f09a788be5c71eb1f70fa4c83224a577bbc441f9333b2a16bd72d4e8`;
- artifact manifest:
  `e993683641972ac43e9082fa07243536bb2a5ae7558d4a0dc8464f0b0c20b291`;
- minimal-headless compatibility profile:
  `b5285a32c6783b52c772d6bca9d8c9340d7d5c114a5571da49afc91d512f58e8`;
  and
- source/DT contract checkpoint identity (informational outer digest; no
  tracked consumer pins it):
  `e9fe1faf25bfa830466dee49a19b7b4ecf0b43aa6d871d409c2d3dd95bb9b55e`.

## Verification

- shell syntax and `git diff --check`: pass;
- artifact inventory versus boot-policy separation: pass;
- seven fixed claim-consumer tests plus the 69 lifecycle tests: pass;
- stable-recovery live gate, including exact admitted-policy shape, thirteen
  hostile Generation-11 policy fixtures for both connected actions, and all
  retained Generation-11 tree/profile artifact checks: pass;
- complete repository Linux CI: pass; and
- independent spec and standards reviews: no findings after the descriptor-to-
  pathname race correction. The earlier Claude Opus review found admission
  bypass, disposition, fixture, and documentation gaps that this checkpoint
  incorporates; a final Claude re-review was unavailable because its session
  limit had not reset.

The next gate is publication and exact-head GitHub CI. Only this reviewed, published,
exact-head-green admission may proceed to a separate connected preflight
checkpoint.
