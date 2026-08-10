# Deployment checkpoint ignored-input staging — offline

Date: 2026-08-10

Starting repository SHA:
`24845b5a6d6d6be5209ef28dca849a0b4a4e56e3`

Recommendation: **HOLD**

No phone, USB device, fastboot, ADB, ACM/NCM session, phone storage, boot
claim, temporary-boot policy row, flash, wipe, slot operation, persistent
installation, or phone boot was used. The project signing key was read only
by the already-reviewed signing-input preflight and failed build launchers;
no production bundle, signature, wrapper, claim, or boot authority was
published.

## Concrete defect

The credential-bound deployment launcher correctly created a detached Git
worktree for the exact reviewed commit and executed a sealed implementation
from that checkpoint. The release builder also needs fixed Git-ignored inputs:
the target kernel/initramfs, recovery base and APK inputs, static QEMU,
Android boot tools, and canonical boot-v3 template. The launcher did not copy
those inputs into the detached worktree.

As a result, a valid synchronized checkout with all exact release inputs
failed inside the sealed checkpoint with:

```text
FAIL missing qualified QEMU artifact; run extract-qualified-qemu-aarch64-static.sh
```

This was reproduced twice in six seconds per launch. The second reproduction
occurred after the qualified QEMU file had been staged and hash-verified in
the launching checkout, proving that the detached worktree boundary—not a
missing host artifact—caused the failure. Both attempts destroyed their
private signing snapshots and left no output root or reviewed-checkpoint
worktree.

## Correction

Both fixed deployment launchers now carry a candidate-specific, literal
allowlist of every required ignored input. Before any credential reaches the
sealed builder, a non-preflight launch:

1. requires canonical repository-owned source paths and safe owned parents;
2. validates fixed path, size, mode, and SHA-256 contracts;
3. opens sources without following the final component;
4. creates destination files with `O_EXCL` and no-follow semantics;
5. streams and hashes the already-open source while bounding the exact size;
6. rejects source metadata change during the copy;
7. fsyncs and revalidates the named destination; and
8. proves that the ignored copies did not change reviewed Git state.

Signing-input preflight deliberately skips these expensive release inputs,
because it exits after key/candidate validation and creates no build output.
The stage still occurs before the private key is read by the child builder.

## Fail-first and tests

The new hostile test failed against the old launchers in 69 ms because they
exposed no checkpoint-input staging path. After the correction, five cases
pass in 0.158 seconds, covering:

- exact independent copy and mode preservation;
- missing input, wrong mode, wrong hash, and occupied destination;
- final and parent symlinks on both sides;
- absolute, parent-traversing, and duplicate contracts; and
- a source modified during streaming, including removal of the partial
  destination.

Focused results:

- checkpoint-input hostile suite: PASS, 5 cases, 0.158 s;
- guarded deployment contract: PASS, 1.204 s;
- deployment signing-input staging: PASS, 15 cases, 2.387 s;
- early diagnostic candidate preparation: PASS, 3 cases, 0.010 s;
- retention-cycle admission: PASS, 19 cases, 2.595 s; and
- repository-runner contract: PASS, 5.965 s.

The complete `scripts/host/test-repository-linux.sh ci` checkpoint passed in
299 seconds and includes the new suite. The exact ending commit and GitHub
exact-head run are recorded in the handoff after this report is committed.

## Boundary and next action

The external project key remains mode `0600`, size 119, and derives the
unchanged public trust root
`f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`.
The exact-head signing-input preflight passed in 2.873 seconds before the
build-path defect was exercised.

Minimal next action: commit this isolated launcher correction, push it, and
require successful GitHub exact-head CI. Only then may a fresh offline
credential-bound clean twin build create the final execution identity. The
observer, claims, policy, lifecycle admission, and physical cycle remain
separate. Recommendation remains **HOLD**.
