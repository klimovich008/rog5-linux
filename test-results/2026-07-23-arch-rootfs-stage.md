# Arch server rootfs staging

This server-only artifact is superseded by
[the minimal Plasma target](2026-07-23-arch-plasma-rootfs-stage.md).

Result: **PASS** for offline userspace staging and metadata round-trip. This is not a boot image and was not installed on the phone.

## Provenance

- Project source: commit `45a007933014ca7cc81605c2e9b6c90ef5d94445`.
- Signed base rootfs SHA-256: `3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a`.
- Matching modules SHA-256: `658f14e300d3896ce68e11e6391df1788efb07637bc7abb73735fb4af972e47e`.
- Target release: `7.1.4-g7a5cef0db479`.
- Output size: `1028140049` bytes.
- Output SHA-256: `d2df10d8b198bc5656de4232b2153786a5e943050d3391277170b512cab6dd2c`.

## Gates

- Package signature policy and initialized Arch Linux ARM trust: **PASS**.
- Full signed package upgrade under ARM64 emulation: **PASS**.
- Generic `linux-aarch64` kernel removal: **PASS**.
- Matching custom module tree and dependency metadata only: **PASS**.
- OpenSSH, nftables, WireGuard tools, hostapd, dnsmasq, `iw`, NetworkManager, and UPower: **PASS**.
- Published root/alarm password access locked; root SSH accepts one external public key only: **PASS**.
- Reusable SSH host keys and machine identity absent: **PASS**.
- VPN private configuration absent and hotspot service not enabled: **PASS**.
- Linux-volume/libarchive ACL, ownership, mode, and xattr archive/re-extraction path: **PASS**.
- Independent verification after re-extraction into a second clean volume: **PASS**.
- Temporary staging volumes removed: **PASS**.

The rootfs contains 191 packages. Relevant versions include OpenSSH 10.4p1-3, nftables 1.1.6-3, WireGuard tools 1.0.20260223-1, NetworkManager 1.56.1-2, hostapd 2.11-4, and dnsmasq 2.93-1.

Systemd reload hooks correctly skipped operations that require a booted target. A first-boot gate must still validate tmpfiles/sysusers, generated SSH host keys and machine ID, package signatures, USB networking, and SSH before the rootfs can be called recovery-grade. The local artifact includes the selected public SSH key and remains outside Git; no private key or network/VPN credential is present.
