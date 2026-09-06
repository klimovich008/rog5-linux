# V23 live rejection: devpts storage false positive

Primary question: can the early-initramfs observer keep side-port NCM stable
while reporting battery/UCSI telemetry before NFS?

Result: rejected and consumed; never retry or flash. Exact stock slot-A
fallback, host cleanup, and `FALLBACK_RETURNED` intent resolution passed.

Earliest evidence:

- signed recovery transfer, verification, PREPARE, and COMMIT passed;
- mainline NCM and ACM enumerated at the exact USB path;
- target USB disconnected about 165 ms later, before a stable ACM frame;
- stock Android returned about 24 seconds later;
- UFS remained disabled, so no phone-storage access occurred.

Root cause: proven R2 deployed-runtime fixture gap. The observer rejected any
mountinfo line containing `/dev/`. Its own init mounts devpts at `/dev/pts`, so
the first storage check always classified a required virtual filesystem as a
block-backed phone-storage mount and forced rollback.

Regression: the observer now reuses PID1's major:minor method and reports a
block-backed mount only when its mountinfo device exists in `/sys/dev/block`.
Fixtures accept devtmpfs, devpts, and tmpfs while rejecting an ext4 mount whose
major:minor has a block-device entry.

Successor: V24 changes target initramfs and identity only. Kernel, DTB,
firmware, stable recovery, charging controls, and UFS exclusion remain
unchanged.
