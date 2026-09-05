# Persistent Tailscale V10 — offline and same-boot PASS

- Official stable Tailscale ARM64 1.102.3 archive was downloaded from
  `pkgs.tailscale.com`; archive SHA-256 matches the official sidecar at
  `a0fa1b15…be25`.
- P23 stores the noexec archive, exact extracted binaries, and daemon state.
  Executable copies are hash-verified into tmpfs on each boot.
- Same-boot helper test passed cleanup and prepare against the real V9 target:
  exact p23 mount, archive/binary hashes, TUN, fixed `169.254.77.2/30`, added
  standalone `10.77.0.2/30`, default route, tmpfs copies, and daemon startup.
- Dedicated host shared mode at `10.77.0.1/30` provides routed IPv4 while the
  separate recovery profile remains `169.254.77.1/30`.
- V10 target initramfs twins built in 7.0 seconds and match at SHA-256
  `db249f8c…02fb`. Image, DTB, V49 UFS modules, power modules, native p24 root,
  slot-B loader, recovery and slot A are unchanged.
- Signed bundle twins verify at manifest SHA-256 `307883f5…2970`, signature
  `a022215b…e4e`, and project trust key `cc1bca69…6054`.
- V10 p24 host image is clean ext4 with unchanged UUID/label/geometry. Sparse
  SHA-256 is `915b4a32…899e`; 3,032,543,232 allocated bytes independently match
  the source at exact offsets, with only ext4 free blocks DONT_CARE.
- Focused helper test: 0.03 seconds. Persistent initramfs test: 11.43 seconds.
  Active tier: 1 minute 19.694 seconds.

No V10 phone write or boot has occurred. The next gate is exact-head GitHub CI,
then one p24-only transfer from slot A and one standalone boot proving automatic
Tailscale service startup plus slot-A rescue.
