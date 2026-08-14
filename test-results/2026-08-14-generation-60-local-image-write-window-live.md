# Generation 60 local-image write-window live result

Date: 2026-08-14

Result: **consumed failure; exact fallback passed; never retry.**

Generation 60 ran from exact repository SHA
`204efb12ac37d72a751525f0c9fd677f9002a4b1` after local CI, exact-head
GitHub CI, candidate publication, installed-bundle preflight, and a read-only
marker-absence check passed. Recovery transferred the exact
`persistent-root-local-image-write-diag-v38` bundle, completed PREPARE, and
accepted one irreversible COMMIT. Mainline Linux
`7.1.4-gae717d919f87`, boot ID
`55c8c145-b065-4590-9b27-e2e61ef9cd92`, then reported:

| Host monotonic receive time | Exact stage |
|---:|---|
| 189374.985583 | `ufs-ready: ENTER` |
| 189380.015589 | `storage-locked: ENTER` |
| 189381.021741 | `userdata-resolved: ENTER` |
| 189382.027428 | `userdata-mount: ENTER` |
| 189383.033265 | `image-write: ENTER` |
| 189384.040801 | `image-write-window: FAIL` |

These receive times are not syscall timestamps. The v38 discriminator proves
that the failure occurred before the outer userdata RW mount, loop setup,
inner image RW mount, marker creation, and final storage relock. Its current
classification still combines the initial userdata unmount, exact read-only
precheck, partition `BLKROSET`, parent-disk `BLKROSET`, and final write-window
verification.

The deliberate storage-quiescent SysRq reset returned exact Alpine fallback,
boot ID `42038eab-1ae5-4b8d-82c7-d21a7fa750fd`. Strict fallback identity,
profile restoration, and host cleanup passed; the execution intent resolved
`FALLBACK_RETURNED`. Maximum fallback temperature was 40.5 C. The bounded
postmortem found exact PMIC `PS_HOLD`/`HARD_RESET`, no PMIC watchdog signal,
and no fatal token. Pstore was unavailable and lineage was uncorrelated, so
that absence is not evidence that no kernel failure occurred.

Read-only fallback inspection attached the 16 GiB image through a read-only
loop and mounted it `ro,noload,nodev,nosuid,noexec,noatime`. The filesystem
remained clean with mount count one. `/var/lib/rog5`, the final marker, and
the temporary marker were absent. Generation 60 therefore made no marker
mutation and did not complete an inner image RW mount.

Two offline controls passed after fallback:

- the phone's retained BusyBox 1.37 `blockdev --setro`, `--setrw`, and
  `--getro` dialect worked on a tmpfs-backed loop device; and
- a disposable host loop disk proved partition-first `BLKROSET` semantics:
  clearing the partition flag while the parent remained read-only kept the
  effective partition state read-only, then clearing the parent made exactly
  the parent and selected partition writable.

The host-loop result does not prove Qualcomm UFS/SCSI behavior on Linux 7.1,
and the fallback BusyBox result does not prove the mainline parent/partition
path. A requested Claude Opus review returned HTTP 529 overloaded before
producing advice; this was a server-side availability failure, not a security
or authorization verdict.

The minimal successor should keep the same write surface and separately
classify userdata unmount, precheck, partition `BLKROSET`, parent
`BLKROSET`, and final blockdev/sysfs window verification. Generation 60 is
consumed and must never be retried or flashed.
