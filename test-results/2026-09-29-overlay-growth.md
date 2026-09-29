# Persistent overlay grown from 16 GiB to 128 GiB (2026-09-29, user approved)

- init + attest accept 16-160 GiB overlay images (whole MiB, loop size = file
  size, all other identity checks unchanged; the manifest keeps the creation
  size). Commit ab6a2ee3; source tests pass; edge cases checked.
- New default production-7.2.7-r169 = kernel r71 (r70 + 0091 DP guard) +
  platform-cpucap-dtb-r1 + the new ramdisk. New fallback
  production-7.2.7-safe-r6 = r165 content (kernel r69 + platform-usbbtm-dtb-r2,
  no descriptor) with the new ramdisk; safe-r2 could not be rebuilt from
  today's sources (kernel r20 lacks modules on the current boot list).
- RAM trials: r169 and safe-r6 boot on the 16 GiB image (p2-attest PASS).
  Installed together with install-default-kernel.py --fallback-bundle-dir;
  two ordinary boots committed healthy.
- Growth, online on r169: fallocate -l 128GiB (allocated, not sparse),
  losetup -c, resize2fs: / 126 GB, 117 GB free; userdata 61 GB free.
- Reboot on the grown image: p2-attest PASS, r169 committed healthy. A copy
  of the fallback (safe-r6t, same content) RAM-booted on the grown image:
  p2-attest PASS.
