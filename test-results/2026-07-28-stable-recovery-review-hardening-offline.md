# Stable recovery review hardening — 2026-07-28

Result: **PASS offline; independently reviewed implementation; ephemeral
trust root; not boot-authorized**

## Scope

This checkpoint closes the actionable findings from the separately
authorized, read-only Claude Opus review of the shell-free stable recovery
platform. It repeats the cross-architecture initramfs integration and the
complete two-clean-build ASUS wrapper, Android boot-v3, and AVB gate.

No production signing key was created or used. No temporary-boot allowlist,
manifest pin, host network state, phone state, or Git-tracked credential was
changed. Every retained image uses an ephemeral public key whose private half
was never written to disk.

## Review disposition

The review findings were resolved as follows:

1. The initramfs builder now exports `LC_ALL=C` and `TZ=UTC`. The integration
   test proves byte identity between a C/UTC build and an
   `en_US.utf8`/`Pacific/Kiritimati` build.
2. The review correctly identified that accepting zero block nodes was too
   weak, but its proposed late-UFS-enumeration race does not apply to this
   pinned wrapper. Vendor `ufshcd.c` schedules `ufshcd_async_scan`, while
   `kernel_init()` calls `async_synchronize_full()` before
   `run_init_process()` starts `/init`. The pinned wrapper also has
   `CONFIG_SCSI_SCAN_ASYNC` unset, which keeps SCSI disk/partition scanning
   synchronous inside the UFS async task; the integration gate asserts this
   config fact. The fail-closed fix therefore requires the repeatedly
   measured ASUS topology of exactly 116 physical disk and partition nodes
   both before gadget configuration and after the `mdev` rescan.
3. Nine negative integration fixtures now prove rejection of an interactive
   shell, DHCP, a missing responder, a missing fixed address, an authorized
   key, a set-ID binary, an unlocked root account, a relocated login binary,
   and unsafe shadow metadata.
4. Ordering verification requires exactly two storage-isolation calls and
   proves the complete lease, isolation, topology, responder, session, and
   USB-bind chain using the unique post-rescan topology check.
5. The native responder opens and validates the watchdog lease before loading
   state can mint or reconstruct a session. Invalid and stale watchdog tests
   assert that no session file is created.
6. The legacy `rog5.recovery_cidr` boot token is removed, not replaced. The
   fixed `169.254.77.2/30` address exists only in recovery `/init`.
7. The builder locks root and removes login/password and DHCP entry points;
   the verifier checks that boundary.
8. Configfs mount failure now immediately invokes the rollback path.
9. Builder/verifier command prerequisites and the operator documentation were
   corrected.

The final read-only Opus follow-up reported no high-severity finding. Its
low-severity observations were also addressed: the gates now require both
storage-isolation calls and their ordering, prerequisite lists are exact,
boot-command-line token loops have pathname expansion disabled, login/DHCP
scrubbing is path-independent, and the verifier checks shadow file type,
mode, and link count. A second scoped read-only recheck of the resulting diff
reported no actionable findings.

## Cross-locale initramfs proof

The retained test-only public key is under the ignored
`build/stable-recovery-review-fixes-initramfs/` directory. The final
fixed-key rebuild is under `build/stable-recovery-final-rebuild/`:

```text
recovery init source  233319f9e9a4ffc6bc48bc85fee86012f39e0428a86a03f4e31a17a3ce0baa00
responder source      4a2a270b1ecd6a4eef8e20ea9f18327609703da90170764b4e253a9f83b7a218
responder binary      2b8be1ddbbc98e7d80c9bbcec82dd14f2ccb11effbf55bcce6fa5838fba0f7f9
fetcher binary        920c9bb3ccb4ab4b3fc3ad783532c5620ed31b3bd52377c8fe3e340fd865702f
verifier binary       ce0f2d997c0243b43e417a41fb5daadd89dfde7b2738ce3bb2e33783ba403b4c
kexec binary          5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015
ephemeral public key  dd15f779b42a7dd1cf98b6127de2af70307fffa58b85c373be4f23ba4b3c11a6
initramfs A           31aa52acea3dac91fd23108bd05e7681597cfd1d082a06782f1315aad3c12108
initramfs B           31aa52acea3dac91fd23108bd05e7681597cfd1d082a06782f1315aad3c12108
```

The private key existed only inside the OpenSSL pipeline. The public key and
derived archive identities are test-only and must not enter production pins.
Relative to the preceding fixed-key archive, the only removed entry is the
obsolete `etc/udhcpc/udhcpc.conf`.

## Two-build wrapper and AVB proof

The full gate used network-disabled containers, distinct empty build trees,
and the retained byte-identical initramfs pair:

```sh
JOBS=16 scripts/host/test-stable-recovery-wrapper-offline.sh \
  build/stable-recovery-final-rebuild/a/rog5-stable-recovery.cpio.gz \
  build/stable-recovery-final-rebuild/b/rog5-stable-recovery.cpio.gz \
  build/stable-recovery-final-wrapper-v3
```

Both clean builds produced:

```text
wrapper config  df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
kernel Image    491195f7f0e5205f3e6a4d4e52da79f03f5a4ae3ad3b92854cf41f6ed5240eea
raw boot-v3     28b4fec683fd8d7bfa7305700faa837bfa14aef1608da591fb3b42bc515f5fe0
AVB boot        64537159174c8aea99d52d87a7eefc1c363b82acf61bbe664cfc69bed23eb21d
```

The raw image is 58,097,664 bytes and the AVB image is exactly 100,663,296
bytes. Unpacking recovered the exact kernel and initramfs. The command line
contains exactly one each of `init=/init`, `selinux=0`,
`rog5linux.test=1`, and `rog5.recovery_timeout=180`; it contains neither
`rog5.recovery_cidr` nor target-only `rog5.ufs_discovery`.

The wrapper gate also asserts that the repacker disables pathname expansion.
Its committed adversarial case creates matching host filenames and proves a
literal `rog5.glob=[ab]*` command-line value survives unchanged while the
obsolete CIDR token is removed.

`avbtool verify_image` verified the complete image. Its unsigned test-only
descriptor has partition name `boot`, original image size 58,097,664 bytes,
and digest:

```text
fc7e8e261548fd5150bab12e8089687634cd297063e9da5f0ec3c9ffe57fe1d5
```

## Promotion boundary

This checkpoint independently reviews and proves the offline implementation,
not a production artifact or live device behavior. A production candidate
still requires explicit confirmation before creating or using its signing
key, two release builds with that public key, atomic source/artifact/allowlist
pin updates, and the attended staging-only promotion sequence.
