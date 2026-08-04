# Stage-75 transport and fallback postmortem integration — offline

Date: 2026-08-05

Result: **PASS — the unissued diagnostic successor now distinguishes a
returned NFS mount call from a still-blocked call, records same-port target
transport activity, and captures a bounded signed fallback pstore summary
correlated to the just-finished target boot. The complete repository CI tier
and an independent tool-free Claude Opus review pass. This checkpoint is
host-only and creates no candidate, signature, policy row, or phone boot
authority.**

## Starting boundary

The sole Generation-12 lifecycle emitted stage 70 `nfs-mount-begin`, then lost
the target USB gadget before stage 80 `nfs-mount-ok`. That evidence proved the
mount call was entered but could not distinguish a blocked call from a mount
that returned into a later kernel/userspace failure. The fallback pstore
snapshot available to recovery predated target execution and therefore could
not establish current-cycle crash lineage.

Generation 12 remains consumed and must never be retried. The implementation
here is a host-only successor contract, not a Generation-13 issuance.

## Implemented evidence boundary

- The target initramfs emits monotonic stage 75 `nfs-mount-returned`
  immediately after the NFS mount command returns and before it evaluates the
  command status. Stage 80 remains reserved for verified mount success.
- The target writes one `/dev/kmsg` lineage record carrying the fixed format,
  candidate, and current target boot ID.
- Private evidence v2 records change-only snapshots of the exact physical USB
  port's `cdc_ncm` interface, link counters, and host kernel NFS RPC counters.
- After the independent watchdog returns the phone to Alpine and the exact
  fallback profile is restored, a separate strict-SSH action reads pstore
  without clearing or modifying it. It examines at most 64 deduplicated
  records and 4 MiB, exports no raw bytes, and signs only canonical counts,
  hashes, candidate/boot identities, and correlation classifications.
- The lifecycle verifies that the signed postmortem and unchanged strict
  fallback-health records report the same fallback boot ID.

The postmortem collector accepts `EMPTY` only while an exact pstore filesystem
remains mounted throughout the snapshot. Unknown pstore mount locations,
directory-probe failures, mount appearance or removal, symlinks, type/inode
changes, malformed names, bounds, and incomplete evidence all fail closed.
Duplicate known mount aliases sharing one filesystem or record inode are
deduplicated.

Fatal signatures are counted across the complete snapshot and, separately,
after lineage inside each marker-bearing record. Cross-record signatures are
reported as present with unknown order. Multiple exact lineage-bearing
records remain explicit as `MATCH_MULTIPLE`; no `UNAVAILABLE`, `NO_RECORDS`,
`NO_LINEAGE`, or no-token classification is presented as proof that no panic
occurred.

## Reproducible artifact identities

The host-only qualified twins produce:

| Artifact | Size | SHA-256 |
|---|---:|---|
| Static early-target reporter | 67,288 bytes | `dc53932d6275180fa71972ceed0ae409bd4ae1604fca8befd9f030d476583a10` |
| Diagnostic initramfs | 6,011,337 bytes | `8324083480a4266bc9dd73d4974d20491979c5d5b11919c9a3ad8f09def8a31d` |

The corresponding C source is 20,939 bytes at SHA-256
`2f8a3bc21a43b415f08a341d01179603401842df25da0b3ce17a67f5cdbd8a65`.
No signed bundle, ASUS wrapper, AVB image, candidate record, or policy entry
was created from these bytes.

## Verification

- `test-fallback-acm-control.py`: **63/63 pass**, including canonical signed
  states, adjacent token boundaries, cross-record ordering, zero-byte records,
  duplicate aliases, unknown pstore locations, probe failures, mount races,
  hostile framing, credential identity checks, and read-only source policy.
- `test-run-minimal-headless-live-cycle.py`: **80/80 pass**, including exact
  postmortem schema, target/fallback boot-ID separation, capture failure,
  cross-response mutation, fallback-health ordering, cleanup, and no-retry
  behavior.
- Early-target state/reporter suite: **25/25 pass**.
- Complete repository Linux `ci` tier: **PASS**, ending with
  `PASS repository Linux ci tier`. This includes source/DT compatibility,
  reproducible builders, QEMU contracts, deployment/runtime admission,
  recovery responder/fetcher/controller/socket suites, and rollback policy.
- Independent Claude Opus review ran through the repository's stdin-only,
  safe-mode, tool-free, nonpersistent wrapper. Supported findings were fixed:
  pstore mount completeness, probe-error and late-mount handling, exact
  non-consuming fatal-token boundaries, cross-record classification,
  zero-length records, strict JSON integer typing, and broader read-only
  source guards. Its final targeted re-review reported **NO FINDINGS**.

The review suggestions to classify `Call trace:` or watchdog bark as fatal
were not adopted because the existing project-wide 5.4 behavioral oracle
treats those as warning/pre-fatal evidence rather than fatal signatures. A
suggested additional anchor-budget gate was also unnecessary: the lifecycle
already owns one shared fallback deadline and the strict-SSH collector
revalidates the exact anchor both before and after its bounded probe.

## Effects and remaining gates

No phone, fastboot, ADB, ACM, NCM, SSH credential, signing key, administrator
credential, reboot, temporary boot, flash, erase, wipe, slot, persistent
installation, or phone-storage operation was used in this checkpoint.

Local implementation, tests, reproducible builds, documentation, and review
are complete. Commit review, branch publication, and exact-head GitHub Actions
remain required before the host-only checkpoint is considered published.
Even after those gates pass, issuance remains a separate HOLD: a fresh
successor would still require an exact signed artifact tuple and one central
temporary-boot policy row before any RAM-only phone execution.
