# Arch Plasma rootfs offline stage - 2026-07-23

Result: **PASS OFFLINE**; no phone hardware was accessed.

## Artifact

- Project commit: `700c45c3025169e53cb7dc9821ada207993b6245`
- File: `artifacts/arch/rog5-arch-plasma-rootfs-7.1.4.tar.gz`
- Size: 2,022,113,204 bytes
- SHA-256: `31e7d341ec97197e0d315cdb6822a98fe9bf3df6b50bf8606125fc694f62d0f9`

## Passing gates

- The signed Arch Linux ARM input, matching Linux 7.1.4 modules, and three
  pinned A660 firmware files matched the repository manifest.
- Pacman signature enforcement remained active during the full upgrade and
  installation of all 42 requested packages.
- The generic Arch kernel was removed; exactly one matching custom module
  tree and generated dependency metadata remain.
- Plasma Wayland, greetd, KRDP, Mesa/Freedreno, Chromium, NetworkManager,
  WireGuard/nftables, Git, Node/npm, Python/pip, ttyd/tmux, and PipeWire tools
  are present.
- The image defaults to `multi-user.target`. Key-only SSH, NetworkManager, and
  the server sleep inhibitor are enabled; Chromium, ttyd, and the VPN hotspot
  remain on-demand.
- Root and `rog5` passwords are locked, physical autologin is absent, remote
  services bind to loopback where applicable, and no Wi-Fi, VPN, KRDP, email,
  or API credentials are embedded.
- The archive was re-extracted into a fresh volume and passed the same package,
  ownership, mode, xattr, firmware, service-state, and credential-absence
  checks.
- The embedded source commit matches the commit above, gzip integrity passes,
  temporary build volumes were removed, and the transient ARM emulator
  registration was cleaned up.

## Remaining live gates

The artifact has not booted on the phone. UFS, display, touch, charging,
Wi-Fi, Plasma/KRDP, screen-off operation, suspend, hotspot routing, and GPU
acceleration remain unaccepted until the Linux 7.1 recovery USB path is
host-visible and each hardware tier passes.
