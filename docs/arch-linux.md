# Arch Linux ARM userspace

The target userspace is the official generic AArch64 Arch Linux ARM root filesystem with this project's kernel, ASUS DTB, modules, firmware, and initramfs. The generic rootfs explicitly expects developers to provide board-specific boot support, so its bundled generic kernel and DTBs are not used for this phone.

## Image contract

- Official input: `ArchLinuxARM-aarch64-latest.tar.gz` plus its detached signature.
- Verify the Arch Linux ARM signing key before extraction.
- Extract as root with ACLs and extended attributes preserved.
- Remove the published default passwords before enabling any network listener.
- Install the matching `modules.tar.gz` under `/lib/modules/` and run `depmod` inside the rootfs.
- Keep firmware local and outside Git; copy only the files required by each accepted hardware tier.
- Use systemd-networkd or NetworkManager, not both for the same interface.

Fetch and verify the generic rootfs into the ignored local artifact cache:

```powershell
powershell -NoProfile -File scripts/host/Get-ArchRootfs.ps1
```

The script pins the official Arch Linux ARM keyring repository commit and expected full signing-key fingerprint. It accepts the mutable `latest` download only after its detached signature, archive paths, and required base files pass. The resulting size and SHA-256 become the immutable project input recorded in `manifests/artifacts.tsv`; the rootfs itself remains outside Git.

The current verified snapshot is 818,293,654 bytes with SHA-256 `3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a`. Do not disable pacman signature checking to work around keyring errors; a signed package-update smoke test is a mandatory staging gate.

Required server packages include OpenSSH, nftables, WireGuard tools, hostapd, dnsmasq, NetworkManager, UPower, and the selected KDE/Plasma session. Mesa/Freedreno becomes the default only after the mainline DRM/MSM GPU test tier passes.

## VPN hotspot

`rog5-vpn-hotspot.service` starts after `wg-quick@wg0`, hostapd, and dnsmasq. Its nftables table has a drop policy and permits forwarding only from `ap0` to `wg0`, with established replies and masquerading. If the VPN disappears, hotspot clients cannot fall back to the ordinary uplink.

VPN configuration and keys live only under `/etc/wireguard/` on the device. They are never built into an image or stored in this repository. Override `AP_IF` or `VPN_IF` in `/etc/rog5/vpn-hotspot.env` when interface names differ; a non-default WireGuard unit also needs a matching systemd override.

Run the routing regression test in the builder container before packaging:

```powershell
docker run --rm --privileged --network none --mount "type=bind,source=$PWD,target=/workspace/repo,readonly" rog5-kernel-builder:ubuntu-24.04 sh /workspace/repo/scripts/device/test-vpn-hotspot.sh
```
