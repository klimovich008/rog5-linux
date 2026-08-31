# Persistent Wi-Fi try-once rollback — offline PASS

Primary question: can a future persistent Wi-Fi bundle fail back to the signed
V11 bundle automatically without writing p24? Yes, offline. No phone contact,
boot, selector change, partition write, signing or admission occurred.

## Defect fixed

The RAM qualification timer reboots into V11 because p24 still selects V11. If
the same Wi-Fi bundle were made persistent, that timer would reboot into the
same failing bundle. This was an R8 rollback-ownership defect, not a kernel
defect. A first design also embedded the primary manifest hash in its own
initramfs, creating a circular hash dependency; focused integration exposed and
removed it before candidate construction.

## Implementation

- Selector v1 behavior remains supported. Selector v2 names one primary and one
  fallback signed bundle plus a 256-bit trial ID.
- The loader copies and verifies both bundles before changing state.
- Only exact `sda` and `sda23` become writable while p23 is mounted. P24 and all
  other UFS nodes stay read-only; all 117 nodes must relock before kexec.
- The static AArch64 helper uses fixed paths, descriptor-relative no-follow
  access, exact owner/mode/link/content validation, file and directory fsync,
  no-replace pending publication, pathname revalidation and nonblocking
  concurrency refusal.
- First entry durably publishes `pending` and selects the primary. Pending on a
  later entry selects V11. A target proves its non-circular trial ID and bundle
  name, then atomically commits `healthy` while preserving the loader-written
  manifest and fallback hashes.
- The target healthy gate requires WLAN association/address/default route,
  radio/WPA/DHCP/state/SSH/Tailscale services, charger online, Good battery,
  safe temperature, exactly two expected writable UFS nodes and read-only p24
  before stopping the 900-second rollback timer.
- The persistent target is a 3.3-second overlay composition on the already
  qualified Wi-Fi initramfs; no kernel, module, firmware or DT rebuild occurs.

## Evidence and timing

- Focused hostile gate: PASS, 22.910s.
- Reproducible AArch64 helper: 67,520 bytes,
  `ff6ede42d089a6a651db320a007947091029aca504500227e0c51bed6792f3ca`.
- Reproducible loader-initramfs twins: 7,634,650 bytes,
  `8adfa1642a7f7281efb1e5603b6505ae72c5c7f75944f447fc197d159ebb7e2e`.
- Representative persistent-target twins:
  `d1a60fa4b9fe9dfc1a6d591baadec67bf88f3b2f1113500ce5015eb5389f583e`.
- First full CI attempt stopped at 144.873s because a legacy test treated its
  own `/dev/shm` scratch as device access. The narrowed fixture still rejects
  every other `/dev/*` path and passes under both `/dev/shm` and `/tmp`.
- Final exact-tree `scripts/host/test-repository-linux.sh ci`: PASS, 454.453s.

## Remaining gates

V22 charger-runtime and a separate charger-only startup trial remain physical
requirements. The new loader and persistent selector are not authorized by
this offline result. Keep V11 and ASUS slot A unchanged until those pass and an
exact deployment is separately reviewed.
