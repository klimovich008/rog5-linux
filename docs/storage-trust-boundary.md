# UFS discovery and writable-runtime trust boundary

Offline audit, 2026-09-12. Repository baseline: `8953632620b8a1a8d5a27d40035b0c825d9d873e`.
The external review examined `4bd1a817618c0dbfdf4b96d391fbf53d50c37dc7`.
This audit makes no kernel change and performs no device I/O.

## Confirmed guarantee and limitation

Patch `0033-ufs-permit-bounded-data-writes-under-discovery-containment.patch`
does **not** confine SCSI writes to a partition, LUN, LBA range, or data-opcode
allowlist. `ufshcd_discovery_scsi_allowed()` immediately returns true when
`CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y`, before inspecting direction or opcode.
Its name and “bounded data writes” title describe intended trusted userspace
operation, not a kernel-enforced write boundary.

The preceding `0001`/`0002` discovery gate, with DATA_WRITE disabled, rejects
host-to-device and bidirectional payloads, restricts opcodes and service actions,
and excludes START STOP UNIT. Patch 0033 bypasses that SCSI gate and the forced
SCSI-disk read-only policy. The separate UFS query gate still restricts query
writes to the mandatory fDeviceInit flag at index/selector zero. Other patches
retain selected management/runtime-PM restrictions. Patch 0034 subsequently
allows high-speed operation for DATA_WRITE; the earlier 0033 help text's absolute
statement that high-speed gear changes remain disabled is historical, not the
complete final patch-stack policy.

The actual compiled successor kernel source is
`136f75ae869afd47a016b1278fae2110cc6d2229` (release `7.1.4-g136f75ae869a`),
under private state `rog5-denial-20260910-r1/gpu-iommu-probe-worktree-r1`.
Its exact `gpu-iommu-kernel-build-r1/build-a/.config`, SHA-256
`889d836fdc2928034d5d2a66062e4fa7d6ca204f82d506acc9fd17bb4a651bef`, has:

```
CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y
CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y
# CONFIG_CHR_DEV_SG is not set
# CONFIG_BLK_DEV_BSG is not set
# CONFIG_SCSI_UFS_BSG is not set
```

The new kernel remains unbooted. These are source/build identities, not evidence
of its installation or physical behavior.

## Ordinary block and pass-through paths

`initramfs/persistent-root-init` first checks all physical nodes read-only.
`open_exact_userdata_write_window()` verifies the resolved userdata partition,
its parent and PARTNAME, then clears read-only on **both** that partition and its
whole parent disk. Its verifier expects exactly those two writable nodes.
Closing relocks the parent first, then the partition, and verifies the set again.
These checks prevent a cooperating tool from selecting an unintended target;
they do not constrain another sufficiently privileged actor.

In the exact kernel, `include/linux/blkdev.h:bdev_read_only()` combines a
partition's own flag with its parent's flag. `block/blk-core.c` checks this for
ordinary write BIOs. Once the parent is writable, its whole-disk node provides
an ordinary raw write path spanning all its sectors. Other partition-node
read-only flags do not restrict writes through that parent node. In addition,
`block/ioctl.c:blkdev_roset()` permits CAP_SYS_ADMIN to change these flags.
The r131 retained source snapshot actually observed `sda=0`, `sda23=0` and the
other 115 nodes read-only; this matches the intended trusted-tool window and
does not strengthen it into kernel range containment.

Disabling `/dev/sg*`, block bsg and UFS bsg removes those interfaces, but does
not remove SG_IO on `/dev/sd*`. In the exact kernel,
`drivers/scsi/sd.c:sd_ioctl()` forwards to `scsi_ioctl()`; its partition check
also allows CAP_SYS_RAWIO. `drivers/scsi/scsi_ioctl.c` handles SG_IO and the
legacy SCSI_IOCTL_SEND_COMMAND. `scsi_cmd_allowed()` returns true for
CAP_SYS_RAWIO before its userspace opcode filtering. This path is not an
ordinary write BIO and does not acquire a partition-relative LBA sandbox from
the read-only flags. The UFS DATA_WRITE predicate supplies no additional SCSI
filter. This is an explicitly privileged trust-boundary observation, not an
unprivileged exploit or a claim that every opcode is supported by the device.

## Executed offline regression

`scripts/device/test-ufs-storage-trust-boundary.py` extracts the actual function
from patch 0001, applies its function hunks from 0002 and 0033, and compiles it
with minimal `scsi_cmnd`/configuration stubs. It enumerates all 256 opcode bytes,
32 low service-action values and four transfer directions for each of three
configuration combinations: 98,304 decisions total. Actual v7.1.4 SCSI opcode
constants are used. The optional `--linux-source` compares both the entire
extracted function and constants against the supplied already-patched source.

The exact 136f75 source comparison and all decisions PASS. Predicate SHA-256:
`4ffad81206514fd2a9c6be13231c636bc5c3ef40c2fbe253a3517c780c99c247`.
The counterexample is precise: with READ_ONLY=1 and DATA_WRITE=1, even opcode
0xff with DMA_TO_DEVICE is accepted at this gate. Repeated testing confirms
the existing broad behavior; it does not claim that the limitation was fixed.
No SCSI command was sent. This small test needs neither a kernel rebuild nor
full-system QEMU. Physical storage effects: **NOT RUN**.

## Separately scoped containment options

A narrower opcode/direction filter could reject format, firmware-download and
management commands while retaining required READ/WRITE variants, discovery,
flush/SYNCHRONIZE CACHE and explicitly justified recovery operations. That is
useful defense in depth, but ordinary WRITE remains capable of reaching an
unintended LBA. UNMAP, WRITE SAME and service-action commands need explicit
payload/range treatment; blindly allowing them defeats a range policy.

Real range confinement must bind the actual UFS LUN and checked start/end LBAs,
reject arithmetic overflow and commands whose affected range cannot be proven,
and cover raw whole-disk and pass-through entry paths consistently. The current
userdata filesystem and recovery tools need an independently enumerated allowed
range/command contract before changing this gate. A device-mapper slice alone
does not hide a still-accessible raw parent. Removing raw-device access and
CAP_SYS_RAWIO/CAP_SYS_ADMIN from ordinary mobile applications, with a narrowly
owned privileged service, reduces userspace exposure but is not containment
of arbitrary privileged I/O.

No filter is enabled by this audit. Preserve current boot, legitimate writes,
flushes, fallback and recovery while a separate storage change is designed and
tested offline. This investigation does not block unrelated panel, touch or
host-side correctness fixes.
