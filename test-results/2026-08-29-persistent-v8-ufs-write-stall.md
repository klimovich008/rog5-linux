# Persistent v8 p23 UFS write stall — R2 composition

- Primary question: can the accepted v8 server obtain routed Internet and
  stage the ARM64 Tailscale userspace payload under the bounded p23 scope?
- Internet routing passed: IP, DNS, HTTPS, strict SSH, charging, and thermals
  remained healthy over the side-port NCM link.
- Official Tailscale 1.102.3 ARM64 archive SHA-256:
  `a0fa1b154af8c61f862a2259f559f7396d96c0225f4a863eae2333e1546bbe25`.
- Extraction wrote about 70 MiB only under `/persist/opt/tailscale/1.102.3`.
  P24 and every protected partition remained read-only.
- `sync -f` then entered uninterruptible sleep at
  `jbd2_log_wait_commit -> ext4_sync_fs -> sync_filesystem`.
- Both `jbd2/sda23-8` and `jbd2/loop0-8` blocked in
  `__wait_on_buffer -> jbd2_journal_commit_transaction`.
- The block layer showed 31 writes in flight. UFS repeatedly timed out WRITE(10)
  commands, skipped aborts, timed out task management, failed device reset with
  `-110`, and entered `eh_fatal` forced host reset.
- NCM and ICMP remained healthy with zero host TX errors, proving this was not
  the earlier USB transport failure.
- The exact restart2 helper reached `kernel_restart` but blocked in
  `sd_shutdown -> sd_sync_cache -> blk_execute_rq`. Emergency SysRq reset then
  returned exact fastboot at serial `M5AIKN00F0353YH`, product `lahaina`, slot
  B, 8.697 V, and `battery-soc-ok=yes`.
- On the next accepted v8 boot, outer p23 journal recovery completed at 334.95
  seconds, the inner state image mounted, both state services passed, the
  stable pinned SSH fingerprint returned, systemd became `running`, and UFS
  in-flight requests drained to zero.

## Proven root cause

Failure class: **R2 deployed composition**.

- Running Image config contains `CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE=y`.
- Persistent v8 packages `ufshcd-core.ko` SHA-256
  `98547f2e54361f86d02085b55516556a1f65504884fa0444559e9843c8ff3e38`.
- That module contains only the low-speed
  `optional device writes and high-speed gear switch disabled` branch.
- The retained clean-twin V49 module SHA-256
  `e3a049d43352fcec6fca6467f6a27b5d827d3d9071a789f782fe26d67f2b777a`
  contains the exact bounded high-speed branch and previously completed all 37
  extents plus fsync/e2fsck/publish/relock in about 92 seconds.

The kernel Image and DTB are not implicated by this discriminator. The next
artifact must replace only the UFS module composition in the target initramfs.

## Regression

- `verify-persistent-ufs-module-profile.sh` now checks exact inventory,
  AArch64 REL format, g359 vermagic, BTF, `struct module` size `0x500`, names,
  dependencies, and mutually exclusive read-only/high-speed markers.
- `test-persistent-ufs-module-profile.sh` proves the tracked persistent-v4
  module is rejected for local-write and the tracked V49 module is accepted.
- Focused regression: PASS in 1.24 seconds.
- Existing persistent-initramfs suite: PASS in 11.56 seconds.

No one-use candidate was involved or consumed. Do not start Tailscale or issue
another persistent write until the module-only successor passes one bounded
RAM-only cycle.
