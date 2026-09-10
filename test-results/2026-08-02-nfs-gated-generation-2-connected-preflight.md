# NFS-gated generation-2 connected preflight

Date: 2026-08-02

Result: **PASS connected preflight — the exact generation-2 diagnostic
recovery, signed bundle, deployment key chain, host state, and one physical
ASUS fastboot device passed. No phone boot, payload transfer, SSH connection,
privileged server, flash, mount, wipe, or phone-storage write occurred.**

The preflight ran from clean pushed commit `32ce8b1` after local CI and GitHub
Actions run `30747098571` passed. The connected device exposed exact USB
identity `0b05:4daf` at physical path `1-1.2`, one canonical fastboot state,
and exact product `lahaina`.

The admitted recovery identity was generation-2 AVB
`70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1`
over unchanged raw recovery
`2f460aa01ee1b97c495d0857b3207bf74920487c56f30c5e155e199967628a01`.
The runtime manifest was
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
for bundle `headless-netroot-early-diag-v1` under the canonical installed
no-replace root `/var/lib/rog5-recovery-bundles`.

The first invocation supplied the ignored offline build bundle root and failed
closed before phone discovery with `FAIL unexpected recovery bundle root`.
The corrected invocation changed only `BUNDLE_ROOT` to the canonical installed
root. Its terminal marker was:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the deployment key was admitted locally, and no phone boot, payload transfer, SSH connection, or privileged server was started
```

Generation 2 remains unbooted and unconsumed. This result proves readiness for
an attended, RAM-only diagnostic lifecycle evaluation; it is not itself
runtime evidence and does not authorize flash, persistence, or a retry after
an ambiguous execute.
