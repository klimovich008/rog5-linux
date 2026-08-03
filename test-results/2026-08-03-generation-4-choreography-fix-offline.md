# Generation-4 choreography correction — offline

Date: 2026-08-03

Result: **PASS, reviewed and published**. The
Generation-4 failure now has an exact regression, anchored pre-commit failures
restore and prove fallback automatically, recovery `PREPARED` is observable
before the NFS gate, and the host transfer reports artifact-boundary progress.
No phone was contacted and no credential, signing key, or boot authority was
used.

## Evidence boundary

The stable recovery init source arms its independent rollback timer at exactly
180 seconds by default. The privileged host bundle controller uses a separate
205-second hard watchdog. Those values match the live sequence in which the
phone left recovery near the 180-second boundary while the host controller
remained alive until its later watchdog. This explains the cleanup ordering;
it does not by itself identify why the transfer did not complete.

A new integration test compiles the real native fetcher, serves it with the
real descriptor-oriented host server, and transfers artifacts with the exact
Generation-4 large-file sizes:

- `Image`: 40,049,152 bytes;
- `board.dtb`: 102,870 bytes; and
- `initramfs.cpio.gz`: 6,010,870 bytes.

The fetch succeeds over loopback, publishes all five files atomically, and
passes byte-for-byte verification. This rules out a basic framing, EOF, or
large-payload incompatibility between those two implementations. It does not
prove USB/NCM throughput, target-side verifier duration, or phone behavior.

## Test-first lifecycle correction

The new Generation-4 regression models this exact order:

1. the bundle request starts and the transfer service remains alive without
   its independent completion receipt;
2. recovery control reports `PREPARED`, then exits before COMMIT because NFS
   is unavailable;
3. the lifecycle terminates the bundle but keeps the receive-only collector
   through the fallback attempt;
4. it performs one fixed restoration against the captured USB anchor;
5. it performs one strict pinned Alpine SSH proof; and
6. it terminates the collector and performs a continuously clean host-state
   proof.

The test requires exactly one control attempt, one bundle transfer, one
fallback restoration, and one strict-SSH proof. It requires no NFS start, no
durable intent, no intent resolution, and no retry. Separate cases prove that
a failed profile restoration or failed SSH proof still receives one host-only
cleanup proof. Another case injects final host residue and requires that the
dirty state remain explicit. An interrupt during fallback proves the hung
child is reaped, host cleanup checks run afterward, and the interrupt is then
re-raised.

## Observability correction

`stable-recovery-control.py` now flushes the canonical validated `PREPARED`
response before entering the post-PREPARE NFS-readiness callback. Successful
output retains the same canonical record order and does not duplicate the
response. A failed NFS gate can therefore distinguish a completed PREPARE from
a prepare-stage failure without inferring state from the final error line.

The host bundle server now emits monotonic, non-sensitive progress at request
acceptance and after each exact artifact. Progress observers are explicitly
non-authoritative: an observer exception cannot alter transfer correctness.
The privileged controller pins the updated server source hash.

## Verification so far

Passing suites at the reviewed implementation tree include:

- the lifecycle suite, including the new stalled-transfer, cleanup-failure,
  and interrupt cases;
- 21 stable-recovery control tests;
- 12 host bundle-server tests;
- the real-server/real-fetcher Generation-4-scale integration test;
- 25 privileged host-controller tests; and
- the exact timeout-lattice test.

The first constrained Claude Opus response was invalid review evidence because
it emitted a simulated tool transcript despite the tool-free wrapper. Smaller
reviews produced actionable findings. The implementation now keeps the
receive-only collector through fallback, re-raises interrupts after cleanup,
records both fallback and cleanup outcomes, proves child reaping, and prevents
progress reporting from affecting transfer correctness. Final bounded
lifecycle and transport re-reviews both returned `NO FINDINGS` after the
reviewer was given the unchanged `CycleError` context explicitly.

The final implementation tree passes complete
`scripts/host/test-repository-linux.sh ci`, including all 41 documentation
targets, 47 lifecycle tests, 31 native fetch tests, 12 host-server tests, 25
privileged-controller tests, and the recovery protocol, source/DTB, and QEMU
stages. Exact implementation commit
`38b60192a50b94227e63e7286272a56588698fa7` is published on the open PR
branch. GitHub Actions run `30793088424` passed both `recovery-core` and
`qemu-system` at that commit. No Generation-5 artifact is built or admitted by
this result.
