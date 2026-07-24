# Arch Linux ARM userspace

The target userspace is the official generic AArch64 Arch Linux ARM root filesystem with this project's kernel, ASUS DTB, modules, firmware, and initramfs. Its UI is a minimal Plasma Desktop Wayland session; GNOME, Plasma Mobile, Discover, and a second display manager are deliberately outside the target. The generic rootfs explicitly expects developers to provide board-specific boot support, so its bundled generic kernel and DTBs are not used for this phone.

## Image contract

- Official input: `ArchLinuxARM-aarch64-latest.tar.gz` plus its detached signature.
- Verify the Arch Linux ARM signing key before extraction.
- Extract as root with ACLs and extended attributes preserved.
- Remove the published default passwords before enabling any network listener.
- Install the matching `modules.tar.gz` under `/lib/modules/` and run `depmod` inside the rootfs.
- Keep firmware local and outside Git; copy only the files required by each accepted hardware tier.
- Use NetworkManager for USB, Wi-Fi, VPN, and hotspot interfaces; do not leave systemd-networkd managing the same interfaces.

Fetch and verify the generic rootfs into the ignored local artifact cache:

```sh
scripts/host/get-arch-rootfs.sh
```

On Windows, the equivalent wrapper is:

```powershell
powershell -NoProfile -File scripts/host/Get-ArchRootfs.ps1
```

The script pins the official Arch Linux ARM keyring repository commit and expected full signing-key fingerprint. It accepts the mutable `latest` download only after its detached signature, archive paths, and required base files pass. The resulting size and SHA-256 become the immutable project input recorded in `manifests/artifacts.tsv`; the rootfs itself remains outside Git.

The current verified snapshot is 818,293,654 bytes with SHA-256 `3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a`. Do not disable pacman signature checking to work around keyring errors; a signed package-update smoke test is a mandatory staging gate.

Stage a server rootfs with an external public SSH key:

```sh
scripts/host/stage-arch-rootfs.sh /path/to/rog5_ed25519.pub
```

On Windows, the equivalent wrapper is:

```powershell
powershell -NoProfile -File scripts/host/Stage-ArchRootfs.ps1 -AuthorizedKey C:\path\to\rog5_ed25519.pub
```

Staging runs the AArch64 userspace under Podman/Docker emulation, keeps pacman
signature enforcement, removes the generic Arch kernel, installs the
server/VPN packages and minimal Plasma target, adds the exact manifest-pinned
network-root modules, locks published password accounts, removes reusable host
identity, and enables key-only SSH. It does not include VPN/Wi-Fi/KRDP
credentials, enable the hotspot, or alter the phone. Extraction, staging,
archival, and verification use Linux volumes plus libarchive ACL/xattr
support; the output is re-extracted and checked so ownership, modes, and
extended attributes survive the round trip.

The earlier staged server-only rootfs is 1,028,140,049 bytes with SHA-256 `d2df10d8b198bc5656de4232b2153786a5e943050d3391277170b512cab6dd2c`. The staged Plasma image is 2,022,113,204 bytes with SHA-256 `31e7d341ec97197e0d315cdb6822a98fe9bf3df6b50bf8606125fc694f62d0f9`. Both pass their historical offline suites, but they contain the previous Linux 7.1.4 module set. Restage the Plasma image with the final reproducible kernel modules before any first boot; neither archive is a current boot candidate.

The current network-root kernel/module bundle is reproducible and
manifest-pinned, and the signed base archive has been reverified on Nobara
Linux. The final Plasma rootfs has not yet been restaged, so the historical
archives remain non-candidates.

`packaging/arch/packages.txt` is the single requested-package list. It contains OpenSSH, nftables, WireGuard tools, dnsmasq, NetworkManager, wpa_supplicant, wireless-regdb, UPower, Plasma Desktop, Plasma-NM, KScreen, greetd, KRDP, PipeWire/WirePlumber, ttyd/tmux, Chromium, Git, Node/npm, Python/pip, Mesa, and Freedreno Vulkan. Mesa/Freedreno is staged for mainline validation but is not accepted as working until the DRM/MSM GPU tier passes.

## Boot and session model

The target defaults to `multi-user.target`: SSH, networking, VPN, hotspot support, ttyd, and headless Chromium can run without a compositor. `greetd` owns the physical login path and starts the packaged Plasma Wayland session only through `graphical.target`.

```sh
systemctl isolate graphical.target   # request the local/remote Plasma session
systemctl isolate multi-user.target  # return to the headless server
```

KRDP shares the active Plasma Wayland session and is reached through an SSH tunnel. Its credentials and any optional unattended-login policy are provisioned on the device after first boot, never embedded in the rootfs. Turning the panel off must leave KWin and the KRDP session running; isolating `multi-user.target` intentionally stops them.

The image does not autologin at the physical console. After the first SSH boot,
set a local-only password with `passwd rog5`, then enter
`graphical.target` and log in once on the phone. SSH password authentication
remains disabled. Unattended graphical login stays opt-in until storage
encryption and the email/CV credential policy are decided.

This is still a staging contract, not a live result. Rejected recovery v6
enumerated ACM/NCM and exposed the SSH port, but it did not pass ACM data,
RAM-only, storage, or rollback gates. The rebuilt recovery must pass first;
then the restaged Arch rootfs, systemd targets, NetworkManager, greetd, Plasma,
KRDP, and Mesa must all pass first-boot tests before being called usable.

## VPN hotspot

NetworkManager owns the AP; do not run hostapd alongside it. Create a manual, non-default, non-autoconnecting AP profile so NetworkManager cannot install ordinary-uplink NAT:

```sh
nmcli connection add type wifi ifname wlan0 con-name rog5-hotspot ssid ROG5-Linux
nmcli connection modify rog5-hotspot \
  802-11-wireless.mode ap 802-11-wireless-security.key-mgmt wpa-psk \
  ipv4.method manual ipv4.addresses 10.42.0.1/24 ipv4.never-default yes \
  ipv6.method disabled connection.autoconnect no
nmcli --ask connection up rog5-hotspot
nmcli connection down rog5-hotspot
```

The one attended `--ask` start records the WPA key in NetworkManager's root-only connection profile instead of the repository or shell command line. Configure dnsmasq as DHCP-only and advertise a DNS resolver reachable through the VPN:

```ini
# /etc/dnsmasq.d/rog5-hotspot.conf
interface=wlan0
bind-dynamic
port=0
dhcp-range=10.42.0.10,10.42.0.200,255.255.255.0,12h
dhcp-option=option:router,10.42.0.1
dhcp-option=option:dns-server,VPN_DNS_ADDRESS
```

`rog5-vpn-hotspot.service` requires NetworkManager and `wg-quick@wg0`. It installs the nftables kill-switch before raising `rog5-hotspot`, then starts dnsmasq. Its AP-scoped chains allow DHCP to the phone, AP traffic only to `wg0`, established VPN replies, and masquerading; unrelated host forwarding keeps its existing policy. If WireGuard disappears, hotspot DNS and data cannot fall back to another uplink.

VPN configuration and keys live only under `/etc/wireguard/` on the device. They are never built into an image or stored in this repository. Override `AP_IF` or `VPN_IF` in `/etc/rog5/vpn-hotspot.env` when interface names differ; a non-default WireGuard unit also needs a matching systemd override. Before using simultaneous Wi-Fi client and AP interfaces, verify the radio's valid interface combinations with `iw phy`.

Run the routing regression test in the builder container before packaging:

```powershell
docker run --rm --privileged --network none --mount "type=bind,source=$PWD,target=/workspace/repo,readonly" rog5-kernel-builder:ubuntu-24.04 sh /workspace/repo/scripts/device/test-vpn-hotspot.sh
```

That test proves rule generation, isolation, cleanup, and service ordering with dummy links. A real client still must pass DHCP, VPN DNS, endpoint reachability, VPN-loss fail-closed, recovery, and AP-to-phone isolation on hardware.
