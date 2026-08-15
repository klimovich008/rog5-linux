# Storage migration Phase 1

## Current decision

The phone is becoming a dedicated Arch Linux server. Preserving Android is no
longer an objective. Development remains RAM-booted while storage is proved,
but the end state is a persistent, standalone Linux installation that no
longer depends on the Steam Deck or NFS.

Buttons, the indicator, sensors, audio, and suspend are frozen at the
Generation-21 checkpoint. Generation 21 is preserved, unbooted, and is not a
storage candidate. Storage and local-root boot are the current critical path.

No raw partition is expendable merely because Android is no longer required.
Phase 1 distinguishes Android payload from boot firmware, calibration,
identity, security state, and the Alpine recovery route. Phase 2 uses one
bounded image in the existing `userdata` filesystem. Repartitioning remains a
separate Phase-3 action requiring the operator's final confirmation of the
exact commands.

The bounded local-image experiment is complete. Generation 70 reached strict
key-only SSH in 326.300 seconds and retained Alpine/NFS recovery. Current work
has moved to the first dedicated-layout boundary; no secondary button,
indicator, sensor, audio, or suspend expansion is active.

Stage 1 is currently paused at the battery gate. Slot B boots Alpine, whose
ASUS/Qualcomm charging path is not accepted; using it as an off-mode charging
environment caused the pack voltage to fall. Active-slot metadata is
temporarily A so the preserved ASUS recovery can charge the phone. The
one-use Stage-1 claim remains unconsumed, and GPT, `userdata`, and partition
payloads are unchanged. Follow the
[ASUS low-battery charging recovery runbook](asus-charging-recovery.md), then
restore slot B only after fastboot reports `battery-soc-ok: yes` and the
current private Stage-1 record is revalidated.

## Read-only inventory result

The 2026-08-12 collector ran from a temporary RAM boot of the exact backed-up
Alpine `boot_b` image. It opens block devices with `O_RDONLY | O_CLOEXEC |
O_NOFOLLOW`, disables the `blkid` cache, and performs no mount, format,
partition, flash, erase, or block write.

The canonical private JSON records every per-device disk/partition GUID,
filesystem UUID, offset, and dependency. Those identifiers and raw images are
not committed to this public repository. The redacted hardware result is:

| UFS LUN | Bytes | Logical block | GPT entries | Principal role |
|---|---:|---:|---:|---|
| LUN 0 | 253,403,070,464 | 4,096 | 23 | OEM data, Android `super`, metadata, Linux/Alpine `userdata` |
| LUN 1 | 33,554,432 | 4,096 | 6 | modem/EFS state |
| LUN 2 | 8,388,608 | 4,096 | 2 | XBL A |
| LUN 3 | 8,388,608 | 4,096 | 2 | XBL B |
| LUN 4 | 33,554,432 | 4,096 | 7 | ASUS keys and system configuration |
| LUN 5 | 8,388,608 | 4,096 | 3 | DDR/CDT calibration |
| LUN 6 | 2,415,919,104 | 4,096 | 66 | A/B bootloader, firmware, boot, AVB, diagnostics |

All seven primary and backup GPT headers pass CRC validation. All seven entry
tables pass CRC validation, all primary/backup header pairs cross-check, and
all 109 GPT entries match their sysfs offsets and sizes. The device exposes 13
ext4 and seven FAT filesystem signatures. No normal RPMB device is exposed;
the boot command line also reports `androidboot.fused.norpmb=1`. This absence
does not prove that the platform has no inaccessible secure state.

UFS `sd*` names changed between consecutive boots. For example, `boot_b`
moved between different LUN letters while its GPT label, unique GUID, offset,
and size remained stable. Every future reader or writer must resolve the exact
disk and partition from freshly validated GPT identity and geometry. A fixed
`/dev/sdX` path is never an identity.

The development fallback contract is:

- bootloader slot `b`, with both A and B reported successful and bootable;
- unlocked bootloader with secure bootloader mode still reported;
- Alpine root on the 243,766,472,704-byte ext4 `userdata` partition;
- 195,854,397,440 bytes available at the final read-only checkpoint; and
- a sealed Arch tree at `/rog5/roots/arch-a`, occupying 5,969,854,464 bytes.

As of 2026-08-16, the active-slot selector is temporarily A for ASUS charging;
this does not change the slot-B development contract or reclaimability.

Both boot slots, both vendor-boot images, both top-level vbmeta images, both
system vbmeta images, and both DTBO images were inventoried and backed up.
Private `avbtool info_image` output records the algorithms, rollback indexes,
footers, and original image sizes. The known-good Alpine recovery route is
slot-B firmware plus `boot_b` and the current `userdata` filesystem; it is not
reclaimable during Phase 2.

## Android dynamic partitions

Only the first and last 16 MiB of `super` were copied read-only. The source and
host hashes match. Current AOSP `lpdump` rejects the vendor geometry checksum;
the raw bytes are retained unchanged, and only a disposable sparse host copy
had its two geometry checksums recomputed for parsing. The primary metadata
headers and tables for all three metadata slots independently pass SHA-256.
Vendor backup metadata reports a non-AOSP major/minor version, so its rejection
is not treated as proof of corruption.

The valid primary metadata describes:

| Metadata view | Logical payload |
|---|---|
| A | `system_a` 3,702,759,424; `system_ext_a` 240,635,904; `product_a` 1,600,753,664; `vendor_a` 1,305,767,936; `odm_a` 1,105,920 bytes |
| B | `system_b` 3,668,914,176; `system_ext_b` 240,930,816; `product_b` 1,979,990,016; `vendor_b` 1,344,622,592; `odm_b` 1,110,016; `system_b-cow` 278,429,696 bytes |

The third primary metadata slot matches the A view. `super` is therefore an
Android OS container, not a firmware store. It and the separate 16 MiB
`metadata` partition are Phase-3 reclaim candidates after local Linux and the
recovery route no longer depend on Android metadata. They are not needed for
the first local-image experiment and are not authorized for modification now.

## Preservation classification

| Class | Partitions | Current disposition |
|---|---|---|
| Boot chain and firmware | XBL/XBL-config, AOP, TZ, HYP, ABL, devcfg, qupfw, keymaster, UEFI apps/image, SHRM, VM boot system, CPUCP, modem, Bluetooth, DSP, and associated A/B firmware | Preserve both slots |
| Identity, radio, security, calibration | `modemst1/2`, `fsg`, `fsgCA`, `fsc`, `persist`, `factory`, `batinfo`, DDR/CDT, ASUS keys, `sysconf`, `devinfo`, security stores and OEM calibration/data | Preserve; no reclaim claim |
| Verified recovery | Slot-B boot/DTBO/vendor-boot/vbmeta plus the Alpine files in `userdata` | Preserve through Phase 2 and Phase 3 layout review |
| Inactive slot | Slot-A boot/DTBO/vendor-boot/vbmeta and firmware | Backed up but still preserve; “inactive” is not “expendable” |
| Android payload | `super` logical system/system_ext/product/vendor/odm/COW and separate `metadata` | Evidence-supported future reclaim candidates |
| Linux data | `userdata`, ext4 label `rog5-linux` | Keep; host the bounded Phase-2 image |
| OEM/diagnostic unknowns | `ftm`, `rtice`, `logfs`, `logdump`, `vm-data`, `mdcompress`, `APD`, `ADF`, `asusfw_*`, `xrom_*`, and similar small stores | Preserve until a role/dependency review makes their small capacity worth reclaiming |

This classification intentionally favors reclaiming the large proven Android
payload and avoids risking small device-specific partitions whose storage
benefit is negligible.

## Backup and restoration checkpoint

The private backup contains:

- 14 exact primary/backup GPT metadata ranges;
- all 107 GPT partitions except the large `super` and `userdata` payloads;
- 4,601,434,112 backed-up bytes;
- the exact active `boot_b` image and read-only storage inventory;
- both 16 MiB `super` metadata edges;
- fastboot slot variables and offline AVB reports; and
- one private 148-file evidence manifest covering 4,735,963,709 bytes.

Every partition was hashed on the phone before transfer and again on the host.
Every pair matches. An interrupted transfer after record 83 was resumed only
after all 83 accepted images and all 14 GPT ranges were revalidated as the
exact contiguous manifest prefix. The completed offline verifier re-hashed all
121 backup objects in 5.231 seconds.

The restoration rehearsal created seven sparse host disks at their exact UFS
LUN sizes, placed each backed-up primary and backup GPT range at its recorded
offset, and re-parsed all headers, CRCs, GUIDs, and 109 entries. All seven
passed. This proves backup consistency and GPT placement logic; it is not a
phone restore and does not authorize one.

The authoritative v3 inventory and all retained backup objects were
re-verified again before Generation 26 work: 14 GPT ranges, 107 partition
images, and 4,601,434,112 bytes passed in 6.600 seconds, including all seven
offline GPT restoration rehearsals.

After Generation 49 proved mainline enumeration of all 116 physical disk and
partition nodes, the same authoritative v3 backup was re-verified again. All
14 GPT ranges, 107 partition images, 4,601,434,112 bytes, and seven sparse GPT
restoration rehearsals passed in 8.045 seconds. The separate 148-file private
evidence manifest passed in 4.080 seconds.

A future restore must:

1. enter the verified recovery path and collect a fresh read-only inventory;
2. match each LUN by disk GUID and exact size, then each partition by unique
   GUID, label, offset, and size—never by `sd*` name;
3. re-run `verify-readonly-storage-backup.py` and require a complete manifest;
4. produce an exact dry-run map from each image to one current partition;
5. preserve both GPT copies and the known-good recovery route; and
6. present the exact write commands for final operator confirmation.

No raw restore command is implemented or authorized at this checkpoint.

## First local-image experiment

The first Phase-2 writable object is one 16 GiB preallocated ext4 image:

```text
/rog5/images/arch-local-a.ext4.partial
  -> verify filesystem and copied root
  -> atomic rename to /rog5/images/arch-local-a.ext4
```

The bounded experiment is:

1. first prove repeated mainline UFS enumeration and read-only reads without
   UFS error recovery, USB loss, or rollback loss; Generation 49 supplies the
   first exact enumeration, consumed Generation 50 proved a stable target
   gadget but did not reach SSH, and consumed Generation 51 proved exact
   dynamic userdata resolution plus the `ro,noload` outer mount before the
   legacy full-tree rehash exceeded its rollback window;
2. create and format only the image file from Alpine, with a unique filesystem
   UUID and `ROG5_ARCH_A` label;
3. copy the sealed deployment-key-bound headless Arch archive into the
   loop-mounted image with ownership, hard links, ACLs, xattrs, capabilities,
   and timestamps; this intentionally replaces the historical Plasma tree for
   the server path;
4. verify the complete 37,735-entry tree seal, unmount, run read-only `e2fsck`,
   hash the image, and atomically publish it;
5. RAM-boot the mainline kernel, resolve `userdata` by fresh GPT identity,
   mount the outer ext4 read-only, attach the image read-only, and use a tmpfs
   OverlayFS upper for the first local-root boots;
6. retain NFS and Alpine as independent recovery paths; and
7. timestamp UFS discovery, outer mount, image verification, inner mount,
   systemd, sshd, and strict key-only SSH acceptance.

The [local-image v32 offline checkpoint](../test-results/2026-08-13-local-image-v32-offline.md)
proves two independent ext4 materializations produce the same canonical tree
and seal, and pins a self-contained volatile AArch64 extraction runtime. The
[phone staging result](../test-results/2026-08-13-generation-53-local-image-staged.md)
then created the exact 16 GiB image in 34.718 seconds and independently
reverified its full hash, ext4 identity, complete seal, and read-only mount
behavior with no loop or mount residue.

The [Generation 53 live result](../test-results/2026-08-14-generation-53-local-image-live.md)
then proved the staged image on hardware. Mainline resolved and locked UFS,
mounted both userdata and the image `ro,noload`, passed the local-image seal
and UFS-health checks, switched into the tmpfs-overlay Arch root at target
uptime 25.494 seconds, and completed strict key-only SSH/runtime acceptance at
target uptime 298.62 seconds. The host pinned the SSH key approximately
332.186 seconds after the one-use claim record was created. Exact Alpine
fallback followed a normal systemd reboot. Generation 53 is consumed and
revoked.

The baseline to beat is Generation 20: NFS mounted at 4.930 seconds, sealed
root verification completed at 350.038 seconds, systemd began at 359.043
seconds, sshd began at 372.046 seconds, and strict SSH passed at 379.548
seconds. No raw partition layout change is needed for this experiment.
On the directly comparable target-uptime acceptance marker, Generation 53 was
80.928 seconds faster than Generation 20. The next optimization target is the
approximately 256.6 seconds between successful `switch_root` and completion
of the boot-critical root attestation, not UFS discovery or image mounting.

After the one controlled Generation-64 write, a 2026-08-15 read-only fallback
refresh proved the image clean and unattached, recomputed its full SHA-256 as
`a51ee69000bcdf56b87ef0045d517fa60cffe92a21fba728e80fc37c4380b3ce`,
and produced the current 37,738-entry tree SHA-256
`c804445418eea694667f6529086d7eeaa8e4a82293c86c692e0ebc379fd28e38`.
The read-only loop exposed `norecovery`, and cleanup left no mount or loop
residue. These values replace the original Generation-53 image/tree identity
for native-partition cloning.

The Stage-1 dedicated-layout executor and collector are now implemented but
unissued. They require exact UFS/GPT/ext4 identities, a fresh host-fsynced GPT
backup ACK, and exact rollback-watchdog disarm before the first write; then
they shrink ext4 before changing GPT, verify the result, and relock all block
nodes. A real-size disposable rehearsal and deterministic sealed twin builds
pass. Phone execution still requires final confirmation of this exact
destructive stage.

The separate Stage-2 implementation is also ready offline. It does not format
or alter GPT: it clones the exact refreshed image into only the future native
partition, verifies the full 16-GiB target prefix, changes its filesystem UUID,
grows ext4, publishes the current-tree seal, then relocks and verifies the root
read-only. It remains ineligible until Stage 1 has run and the unchanged Alpine
fallback has proved the intermediate layout. The
[offline result](../test-results/2026-08-15-storage-layout-stage2-offline.md)
records its deterministic twins and AArch64 runtime checks.
The [Generation 54 live cycle](../test-results/2026-08-14-generation-54-fast-attestation-live.md)
proved that UFS and local-root handoff remain fast, but also proved the
retained BusyBox is musl-dynamic rather than static. Direct execution after
`switch_root` failed because its interpreter was retained below
`/run/initramfs`, not the Arch `/lib`. The
[Generation 55 live cycle](../test-results/2026-08-14-generation-55-retained-loader-live.md)
proved the corrected retained-loader execution: attestation passed at target
uptime 274.44 seconds and strict key-only SSH accepted at uptime 291.33
seconds, or 344.676 seconds after lifecycle start. This is 35.324 seconds
(9.3%) faster than the approximately 380-second Generation 20 NFS baseline.
Both ext4 layers remained `ro,noload`, OverlayFS remained tmpfs-backed, and
exact Alpine fallback passed after a normal reboot. Generation 55 is consumed.
The [Generation 56 repeat checkpoint](../test-results/2026-08-14-generation-56-repeat-systemd-timing-offline.md)
keeps the target byte-identical and adds bounded read-only `systemd-analyze`
capture. Its [live cycle](../test-results/2026-08-14-generation-56-repeat-systemd-timing-live.md)
again passed exact UFS, local-image Arch, strict key-only SSH, and Alpine
fallback in 362.241 seconds. It identified `ldconfig.service` (148.089
seconds) and the unused headless virtual-console setup (76.694 seconds) as
the next critical-path targets. Generation 57 changes only volatile boot
state to skip those two costs while leaving both physical ext4 layers
`ro,noload`. Its
[live cycle](../test-results/2026-08-14-generation-57-volatile-systemd-live.md)
passed strict SSH in 305.928 seconds. Userspace fell by 54.862 seconds, and
neither `ldconfig` nor vconsole remained in the timing report. The next
measured targets are early userspace/udev and SSH key generation; device-unit
blame must be separated from the actual critical chain before another change.
Generation 58 targets only the measured 38.212-second SSH host-key step. Its
initramfs leaves both ext4 layers `ro,noload`, masks the stock three-algorithm
generator in tmpfs, and requires one per-boot volatile Ed25519 key before sshd.
The [offline checkpoint](../test-results/2026-08-14-generation-58-ed25519-only-offline.md)
passed clean-twin and exact one-use admission checks. The
[live cycle](../test-results/2026-08-14-generation-58-ed25519-only-live.md)
proved the intended key path: the replacement service took 28 ms, stock
`sshdgenkeys.service` was masked, only Ed25519 private/public key paths existed,
and sshd began about 18 seconds earlier. End-to-end acceptance was 333.446
seconds, 27.518 seconds slower than Generation 57 because other measured work
grew; therefore the key optimization is accepted, but the run is not evidence
of an overall speedup. Generation 58 is consumed and revoked.

Generation 59 is the first mainline-controlled write inside that existing
image. It does not create, resize, format, or repartition storage. The v37
initramfs resolves `userdata` from fresh GPT identity, begins with all 116
physical UFS disk/partition nodes read-only, and temporarily clears only the
exact `userdata` partition and its parent LUN. It verifies every sibling stays
read-only, mounts the outer filesystem and exact UUID/label/size image
read-write, and creates only:

```text
/var/lib/rog5/local-image-write-probe-v1
```

The 132-byte, mode-0444 marker contains an exact format, image UUID, and
current target boot ID. Existing files, directories, or symlinks at the
marker location fail closed. After one sync, both mounts and the loop are
closed, the parent LUN is relocked before `userdata`, and all 116 nodes must
again prove read-only before the familiar two-`ro,noload` tmpfs-overlay Arch
runtime can start. The same marker is then verified from the read-only lower
root and by retained-loader attestation.

This deliberately changes the image after its historical 37,735-entry tree
seal. That seal still identifies the materialized source tree, but it no
longer claims the entire current image is byte-for-byte unchanged. Generation
59 instead admits exactly one independently attested mutation while retaining
exact boot-critical-file checks. A later persistent-root design must define a
new mutable-state/seal boundary; it must not silently reuse the old full-tree
claim.

Generation 59 consumed its sole RAM-only cycle. It reached UFS, exact
`userdata`, the initial `ro,noload` mount, and exact image resolution, then
reported `image-write: FAIL`. Read-only fallback inspection proved that the
image filesystem was never mounted read-write: its mount count did not
advance and `/var/lib/rog5`, the marker, and the temporary marker were all
absent. Exact Alpine fallback and host cleanup passed. Generation 59 is
revoked and must never be retried.

Generation 60 also consumed its sole RAM-only cycle. It reached exact UFS,
`userdata`, and read-only image resolution, then reported
`image-write-window: FAIL` before the outer userdata RW mount. Read-only
fallback inspection found a clean image with mount count one and no marker
ancestry. Exact PS_HOLD Alpine fallback and host cleanup passed. Generation 60
is revoked and must never be retried.

Generation 61 consumed its sole RAM-only cycle. It passed userdata unmount,
the all-node read-only precheck, and both selected-partition and parent-disk
`BLKROSET` calls, then failed effective `blockdev --getro` verification before
sysfs/count verification, any RW mount, loop attachment, marker, or persistent
write. Read-only fallback inspection found the image clean, at mount count
one, and without marker ancestry. Generation 61 is revoked and must never be
retried.

Generation 62 consumed its sole RAM-only cycle. It reported
`write-window-selected-disk-blockdev: FAIL` after both reviewed `BLKROSET`
calls returned success: the selected parent disk still reported effective
read-only state. No RW mount, loop attachment, marker, or persistent write
occurred. Read-only fallback inspection found the 16 GiB ext4 image clean and
marker-free, and exact Alpine fallback passed. Generation 62 is revoked and
must never be retried.

The failure is a kernel-profile mismatch, not another userspace window bug.
`CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y` sets the SCSI disk's hardware
read-only state and independently blocks SCSI data writes. The first local
write successor therefore adds `CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y` while
retaining the discovery option. Device-query writes, optional UFS management
writes, high-speed gear switching, link-power changes, and runtime PM remain
contained. Its sealed initramfs still locks every physical block node
read-only before opening the exact two-node userdata window. The read-only
discovery build remains available and unchanged; GPT, partition geometry,
firmware, calibration, device identity, and Alpine recovery remain outside the
write surface.

Generation 63 consumed its sole RAM-only cycle. Its kernel kept
`CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y` and adds the separate
`CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y` policy. Clean-twin builds verified an
identical kernel, compat vDSO, and four deferred UFS modules. The sealed
initramfs records `local-write`, requires the retained containment markers,
locks all 116 physical block nodes before opening the exact userdata
partition-and-parent window, and relocks every node before the read-only Arch
runtime. Hardware passed that window, the outer userdata RW mount, and writable
loop attachment. The inner ext4 mount then failed before any inner-filesystem
or UFS data write because the initramfs had not created `/mnt/probe-root`.
Exact Alpine fallback and read-only postcheck found the image clean,
marker-free, and without mount residue. Generation 63 must never be retried.

Generation 64 consumed its sole RAM-only cycle. It completed the exact
contained write, persisted the 132-byte marker, relocked storage, remounted the
image read-only, and verified the root. The aggregate UFS-health gate then
failed and triggered the bounded rollback. Read-only fallback inspection
proved the image clean, the exact marker durable, and no loop, mount, or
temporary-file residue. Generation 64 must never be retried.

Generation 65 consumed its sole RAM-only cycle. Its accepted read-only kernel
executed, but the sealed initramfs contained no `/rog5-ufs-modules` directory.
It entered `ufs-ready`, could not load the four deferred UFS modules, and
failed after 56.292 seconds before storage enumeration, mounts, image access,
or writes. Exact Alpine fallback and cleanup passed. Generation 65 must never
be retried.

Generation 66 consumed its sole RAM-only cycle and restored the four accepted
v36 UFS modules. UFS passed in 5.029 seconds, exact `/dev/sda23` and the 16 GiB
local image mounted `ro,noload`, the persisted Generation 64 marker verified,
and local Arch reached strict key-only SSH in 328.363 seconds. A normal reboot
returned exact Alpine fallback; host cleanup and `TARGET_ACCEPTED` intent
resolution passed. The production builder now fails closed when a
module-required build omits the UFS modules, and the stage protocol retains
bounded UFS failure detail. Generation 66 must never be retried or flashed.

This completes the read-only local-image boot milestone and removes NFS from
the successful target path. The next reversible work is local-root startup
reduction and a separately bounded persistent-write experiment inside the
existing image; no partition-table change is authorized by this result.

Generation 67 consumed its sole RAM-only cycle and proved the startup reduction.
The exact read-only UFS/local-image path passed, early strict SSH was active at
approximately 94.147 seconds target uptime, and full storage attestation passed
at 130.057 seconds. Recovery returned canonical `CLAIMED`, then ACM closed
before the follow-up STATUS response; a transient `inspect-error` sample made
the formal lifecycle refuse
the target; the same running boot was salvaged without retry, then normal
reboot, exact Alpine fallback, and host restoration passed. Generation 67 is
revoked and must never be retried or flashed. The narrow host fix now retries
only that indeterminate departure observation for two seconds while preserving
immediate rejection of an exact present responder. See
the [offline checkpoint](../test-results/2026-08-14-generation-67-early-ssh-offline.md)
and [live result](../test-results/2026-08-14-generation-67-early-ssh-live.md).

Generation 68 consumed its sole RAM-only cycle and proved the corrected
post-`CLAIMED` recovery departure, exact UFS/local-image boot, tmpfs OverlayFS,
P2 storage attestation, and early key-only `sshd`. Its first cold authenticated
SSH session exceeded the runner's 10-second host deadline; `sshd` remained
active with zero restarts and the same boot later passed exact runtime and
diagnostics at 474.59 seconds uptime. Normal reboot, exact Alpine fallback, and
host restoration passed. Generation 68 is revoked and must never be retried or
flashed. See the [offline checkpoint](../test-results/2026-08-14-generation-68-host-departure-offline.md)
and [live result](../test-results/2026-08-14-generation-68-host-departure-live.md).

Generation 69 consumed its sole RAM-only cycle. It passed exact UFS, the local
image, tmpfs OverlayFS, P2 storage attestation, and key-only `sshd`. The bounded
rendezvous reached a status-zero SSH response within its deadline, but the host
required marker-only output and rejected unretained extra startup output before
running the runtime command. The same boot later passed exact runtime at
378.07 seconds and diagnostics, then normal reboot, exact Alpine fallback, and
host restoration passed. Generation 69 is revoked and must never be retried or
flashed. See the [offline checkpoint](../test-results/2026-08-14-generation-69-authenticated-ssh-rendezvous-offline.md)
and [live result](../test-results/2026-08-14-generation-69-authenticated-ssh-rendezvous-live.md).

Generation 70 consumed its sole RAM-only cycle and formally passed the complete
local-image path. Exact UFS, both `ro,noload` ext4 layers, tmpfs OverlayFS, P2
storage attestation, stable NCM, and key-only SSH passed. Attempt seven returned
175 bounded startup bytes containing exactly one marker; the corrected host
accepted it and the exact runtime command passed at target uptime 243.46
seconds. End-to-end accepted SSH took 326.300 seconds versus Generation 20's
380-second reference. Normal reboot, exact Alpine fallback, PS_HOLD/HARD_RESET
lineage, intent resolution, and host restoration passed. Generation 70 is
revoked and must never be retried or flashed. See the
[offline checkpoint](../test-results/2026-08-14-generation-70-bounded-startup-output-offline.md)
and [live result](../test-results/2026-08-14-generation-70-bounded-startup-output-live.md).

This completes reversible Phase 2: Generation 64 proved a write constrained to
the existing 16-GiB image, Generations 66–70 repeatedly booted that image
read-only, and the successful target root path no longer uses NFS. No new
local-image candidate is admitted. The next step is a dedicated-Linux layout
proposal and exact destructive-operation review; partitioning still requires
final operator confirmation.

The first [dedicated Linux layout proposal](dedicated-linux-layout-v1.md) now
keeps partitions 1–22 unchanged, shrinks only the tail of `userdata` from about
228 GiB to about 195 GiB, and assigns the aligned final 32 GiB to one native
`arch_root_a` ext4 partition. A fresh strict-SSH checkpoint measured more than
150 GiB of ext4 headroom at the proposed pre-shrink size. The proposal and its
offline geometry verifier do not perform any phone write; a tool-bearing
RAM-only recovery and disposable 4-KiB-sector GPT rehearsal now pass offline.
One read-only physical preflight comes before the required final confirmation.

## Reproduction commands

```sh
scripts/device/test-collect-readonly-storage-inventory.py
scripts/host/test-backup-readonly-storage-inventory.py
scripts/host/verify-readonly-storage-backup.py \
  --inventory "$PRIVATE_INVENTORY" \
  --backup "$PRIVATE_BACKUP"
```

The collector output and backup arguments are deliberately private and
outside Git.
