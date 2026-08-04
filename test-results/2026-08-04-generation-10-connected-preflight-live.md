# Generation-10 connected preflight — live result

Date: 2026-08-04

Result: **PASS connected preflight — the exact Generation-10 diagnostic
recovery, signed bundle, deployment-key chain, installed host surfaces, and
one physical ASUS fastboot device passed. No phone boot, payload transfer, SSH
connection, privileged server, flash, mount, wipe, or phone-storage write
occurred.**

## Published prerequisite

The preflight ran from clean pushed commit
`70d2f3606c7e4f6e8e234b2c3d3920331c4508e6`. Its complete local CI and
constrained tool-free Opus review passed, and exact-head GitHub Actions run
`30871533747` passed `recovery-core` in 3m32s and QEMU in 41s.
That run covers the clean prerequisite checkpoint before this live result; the
new connected-preflight evidence itself must be committed and pass a later
exact-head run before the lifecycle may execute.

Central policy admits exactly one RAM-only lifecycle for AVB
`b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51`.
Generation 10 remained `unbooted`, retained issuance `authority=none`, and had
no boot claim throughout this preflight.

## Connected result

The local admission first matched the dedicated Ed25519 key to one
non-fixture v3 package, the exact `headless-netroot-early-diag-v1` candidate,
and runtime manifest
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.
The connected gate then verified the pinned A/B recovery artifacts, production
trust root, host verifier, installed no-replace bundle, root-owned host
components, rollback prerequisites, isolated USB profile, and exactly one
fastboot device reporting product `lahaina`.

Fastboot appeared later on the same physical connection after the prior
bounded Alpine-to-bootloader transition observation had ended. This result
supersedes the earlier operational requirement for manual fastboot entry; it
does not infer why enumeration was delayed or rewrite the historical
transition result.

The first invocation accidentally supplied the ignored build-tree bundle root
and failed closed before connected phone discovery with:

```text
FAIL unexpected recovery bundle root
```

The corrected invocation changed `BUNDLE_ROOT` only to the canonical installed
root `/var/lib/rog5-recovery-bundles`. Its terminal marker was:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the deployment key was admitted locally, and no phone boot, payload transfer, SSH connection, or privileged server was started
```

Private serial, credential, and invocation-state paths remain outside Git.
This pass establishes the connected-preflight precondition for the sole
attended Generation-10 diagnostic lifecycle after this evidence checkpoint is
reviewed, published, and green at exact-head CI. It is not runtime evidence,
does not consume the artifact, and does not authorize flashing or a retry
after any later ambiguous execute.
