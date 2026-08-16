# Alpine 5.4.210 charging rescue — first live routes

Date: 2026-08-16

Result: **FAIL before charging telemetry; all three exact routes are consumed and
must never be retried. No phone storage was accessed.**

The first route staged the exact payload only in fallback `/run` tmpfs. Every
target-side payload hash passed and the single `qcom,hh-watchdog` control was
disabled, but `kexec -c -l` returned `ENOSYS` before execution. Read-only
configuration then proved `CONFIG_KEXEC=n`, `CONFIG_KEXEC_FILE=n`, and
`CONFIG_CRASH_DUMP=n` in the installed 5.4.134 fallback. The source boot ID
remained unchanged.

The second route used an exact boot-v3 direct wrapper. The historical
build-21 image was first reproduced byte-for-byte at
`b5805cc29cea05ed13f0e4695ba8ffa50a2893223ff2fc06b6b9c60decf88d86`.
Clean direct-wrapper twins then matched at raw SHA-256
`88b3d0514449ba5bb365b11d4f2c556c9c25b12ae7527f3b791c624de6bf1e89`
and AVB SHA-256
`81537c14ec164c27e7752a4baec5362e4c4b5ba3b86ef0c917b31a681c29434e`.

Exact fastboot accepted the RAM-only image at 10:03:57. Host kernel capture
recorded fastboot departure at 10:03:59, no intervening USB enumeration, and
exact `ROG5LINUX` fallback enumeration at 10:05:05. The 66-second blackout is
earlier than the target's 180-second userspace rollback. No `ROG5CHARGING`
product, ACM, NCM, or SSH appeared. Fallback pstore was empty, which remains
inconclusive. Bootloader voltage was 6.900 V before and 6.901 V afterward;
this is measurement noise and does not prove charging.

The demonstrated pre-USB defects were an unbounded first `mdev -s` before
rollback arm and unconditional base-module `insmod` under `set -e`, unlike the
historically working dependency-aware loader. A fail-first contract reproduced
the ordering failure. The offline successor arms rollback before the first
device scan, provides an exact-release module dependency link, restores
`modprobe`-first loading, retains optional base-module failures for later USB
inspection, and keeps charger-module failures strict. Clean successor twins
took 1,544 ms and 1,543 ms before the final timeout discriminator and matched
at initramfs SHA-256
`9ac3e31c11600b3ac4d2db8acc685edcd4c44e0d7f9fa6a09376ecff204f40ba`.
The final successor uses a 30-second rollback, shorter than the observed
66-second blackout, so its fallback time can prove whether PID 1 reached the
arm point. Final clean twins took 1,573 ms and 1,552 ms and match at
`7366600f925587613629a2336036dd75321c67a5e51ffa470b43de40fdec74fb`.

That discriminator was executed once after exact-head CI run `31936511077`
passed commit `beeccb9a0ce2f4453c2b04f8763447a4e2e5849e`. Direct-wrapper twins
matched at raw SHA-256
`9cdd035fde41351dd0fc4572c4bddad8db012f4d44253f6ffc3e1428a8e2de69`
and AVB SHA-256
`0b8eb2f24bca5faab89bb5772a0fa836dbd27577c4de876ee2458ed3277e8ecd`.
Fastboot accepted the image at 10:34:11, the anchored device departed at
10:34:13, and no USB device appeared until exact fallback enumerated at
10:35:20. Strict SSH proved fallback at 10:35:21. The unchanged 67-second
boundary, despite the 30-second rollback being armed before `mdev` or module
loading, proves that userspace rollback did not control the return and strongly
indicates that the rescue PID 1 never reached its arm point. Empty pstore is
still inconclusive. Voltage was 6.896 V both before and after the cycle.

The historical qualification is therefore corrected: byte-reproducing the
build-21 `rtcharger` artifact proves provenance, not function. Its original
manifest called it only a charger-calibration experiment and retained no
successful boot evidence. The separately documented build/image #20 is the
actual known-good charging baseline. Build #21 also has an external initramfs
and `CONFIG_INITRAMFS_SOURCE=""`; the proven later 5.4.210 recovery wrappers
compile their initramfs into the kernel and kexec targets with an explicit DTB.
The direct build-21 route is retired rather than debugged with more module
changes.

The exact phone serial, `lahaina` product, anchored USB topology, slot B,
fallback boot identity, and 39.5 C maximum pre-cycle readable thermal value
were verified. No flash, erase, format, repartition, slot change, or persistent
phone-storage write occurred.
