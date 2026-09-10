# Generation 103 local-write composition result

Date: 2026-08-23

Result: **CONSUMED; READ-ONLY KERNEL CANNOT RUN LOCAL-WRITE POLICY.** Generation
103 must never be retried or flashed.

The exact signed transfer, PREPARE, and COMMIT passed. `ROG5 persistent root`
NCM appeared at 07:48:50, accepted the exact host `/30`, and remained reachable
until 07:49:50. Stock slot A returned at 07:50:08.

V10 changed only target userspace to `local-write/current`, but retained V8's
Image built with `CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y`. That kernel emits the
forced-read-only registration marker, while local-write
`verify_ufs_power_containment()` requires the bounded-write marker set and
explicitly rejects forced-read-only registration. Its `ufs-power` failure
classification delays rollback by 50 seconds, which accounts for the observed
60-second target lifetime including startup.

This is a proven R2 composition defect, not a new kernel failure. The write
window never opened and no probe or target storage write occurred. The next
writer must reuse the exact Generation-64 write-capable Image, DTB, and UFS
modules that already passed the bounded outer/inner write, probe, sync, unmount,
and relock path. Charging-capable read-only Linux remains the production
baseline for the subsequent boot.
