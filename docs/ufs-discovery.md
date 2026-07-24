# Read-only UFS discovery gate

This gate discovers the ROG Phone 5 UFS topology without mounting a
filesystem or accepting host-originated storage mutation commands. It is a
short, attended hardware test between the proven RAM-only Linux 7.1 recovery
and the first native Arch/Debian root filesystem.

Nothing in this phase is flashed. The Android boot image is used only with
`fastboot boot`, the Linux 7.1 payload is entered through kexec, and both
stages retain independent 180-second forced-reboot watchdogs.

## Current status

Discovery v1 passed two clean mainline builds, two clean ASUS wrapper builds,
two deterministic boot-image repacks, and the complete network-isolated
thirteen-file bundle verifier. Its attended temporary boot then safely
enumerated 7 UFS disks and 109 partitions. All 116 physical nodes were
read-only through independent ioctl and sysfs checks, the root was RAM-backed,
and there were zero block-backed mounts.

The live gate was nevertheless rejected. Runtime PM attempted to enable
auto-BKOPS three times after enumeration. The query guard blocked every
`SET_FLAG`, but upstream UFS recovery entered a fatal state and orderly reboot
stalled in WLUN shutdown. The authorized emergency reset immediately restored
the exact fallback kernel; no UFS filesystem was probed or mounted, no
partition was changed, and nothing was flashed. The full result is in
[`2026-07-24-ufs-discovery-v1-live.md`](../test-results/2026-07-24-ufs-discovery-v1-live.md).

The three-patch replacement at deterministic Linux commit
`cfd385a1c754684dd28b63a4559e04baa5e902b1` and tree
`d2f03d2055227b8b72ab41be949847a066924c5a` pins UFS active for the
short discovery interval and skips shutdown power transitions. Its
patch/config/object verifier passes. Reproducible bundle rebuilds and a new
live gate are pending.

## Build chain

```text
pinned Linux 7.1.4 + read-only patch/config
  -> guarded Image
ASUS base DTB + reviewed UFS/USB2 overlay
  -> discovery DTB
credential-free recovery init + Image + DTB
  -> target initramfs
target payload + dedicated kexec loader
  -> staging initramfs
staging initramfs embedded in reproducible ASUS 5.4 wrapper
  -> Android boot-header-v3 image + unsigned AVB hash footer
```

Every arrow is checked twice from fresh source or output directories where
applicable. The final verifier accepts only the exact SHA-256 manifest and
checks the nested payloads again with container networking disabled.

## Kernel boundary

`CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y` is compile-time and cannot be relaxed
from the command line or userspace.

- Every SCSI disk is marked read-only before registration and remains
  read-only across revalidation.
- Host-to-device and bidirectional SCSI payloads are rejected independently
  of opcode.
- The SCSI whitelist contains only no-data readiness checks and explicit read
  commands. `START STOP UNIT`, writes, discard, cache flush, mode select, and
  security-protocol output are rejected.
- UFS descriptor, attribute, and flag reads are accepted.
- The only accepted UFS write query is the mandatory `fDeviceInit` set-flag
  handshake with index and selector zero.
- WriteBooster, background-operation setup, RTC/timestamp updates,
  exception-event writes, devfreq setup, and the high-speed gear switch are
  skipped.
- The host retains its pre-scan runtime reference, host and WLUN runtime PM
  are forbidden, and auto-hibern8 is disabled.
- WLUN and host power-transition helpers reject discovery-mode calls before
  BKOPS or suspend protocol commands; shutdown leaves the read-only link
  active for platform reset.
- SCSI generic, block BSG, UFS BSG, RPMB, UFS crypto, and UFS hwmon user
  interfaces are disabled in the discovery configuration.

This prevents host-originated data mutation. It cannot prevent autonomous
flash-controller housekeeping that the UFS device may perform when powered or
initialized.

## Userspace boundary

The target starts entirely from initramfs and requires the live kernel config
to attest the compile-time discovery option before waiting for UFS.

- The rollback watchdog is armed before UFS enumeration.
- Any block-backed mount is a hard failure.
- Every physical disk and partition is independently forced and verified
  read-only before USB is exposed.
- No `blkid`, filesystem probe, `fsck`, mount, raw-device read, partitioning,
  or write test is run.
- Topology is collected only from `/sys/class/block` after the read-only gate.
  The report includes disk/partition names, GPT partition names exported by
  the kernel, offsets, sizes, logical block size, read-only state, and sysfs
  path.
- ACM and NCM are configured only after a second storage-isolation check.
- No SSH key, host key, password, credential, or private identifier is
  embedded.

## Live acceptance gate

The candidate may proceed only if all of these conditions hold:

1. The exact manifest-pinned wrapper reaches credential-free staging through
   `fastboot boot`.
2. Staging reports a RAM root, zero block-backed mounts, all fallback-visible
   physical devices read-only, and an armed rollback watchdog.
3. The dedicated loader verifies all nested hashes, disables exactly one
   allowlisted Haven watchdog control, and stops after `kexec -l`.
4. A separate attended `kexec -e` reaches the exact patched Linux release.
5. `/proc/config.gz` contains the compile-time discovery option.
6. At least one UFS physical disk appears; every disk and partition reports
   read-only through both sysfs and the block ioctl.
7. Host and WLUN runtime PM report forbidden, auto-hibern8 is zero, no
   blocked query or SCSI command appears, and no UFS error handler runs.
8. The sysfs-only inventory is complete, the Qualcomm UFS driver is bound,
   USB ACM/NCM works, and no fatal kernel signature appears.
9. The untouched rollback marker performs an orderly forced reboot and
   returns the phone to the exact fallback kernel with a changed boot
   identity.

Any missing attestation, unexpected write command, block-backed mount,
writable device, USB identity mismatch, watchdog failure, or fatal kernel log
ends the test and leaves rollback armed.

## What follows

The inventory determines the safe next boot strategy; it does not authorize a
partition change. The next low-risk native userspace gate is a pure
Arch/Debian root filesystem served from the development PC over USB NCM
(NFS/NBD or an initramfs-carried minimal root). That runs directly on Linux,
not inside Android, while avoiding UFS writes. A persistent on-device root is
a later explicit migration decision after charging, thermals, USB, networking,
display, input, suspend, and recovery have passed.
