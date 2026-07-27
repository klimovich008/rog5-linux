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

To build the separately versioned power-button development root without
changing the v2 default:

```sh
scripts/host/stage-arch-successor-v3-rootfs.sh /path/to/rog5_ed25519.pub
```

On Windows, the equivalent wrapper is:

```powershell
powershell -NoProfile -File scripts/host/Stage-ArchRootfs.ps1 -AuthorizedKey C:\path\to\rog5_ed25519.pub
```

Staging runs the AArch64 userspace under Podman/Docker emulation, keeps pacman
signature enforcement, removes the generic Arch kernel, installs the
server/VPN packages and minimal Plasma target, adds the exact manifest-pinned
network-root modules, locks published password accounts, removes reusable host
identity, enables key-only SSH, and creates the locked `rog5-agent` automation
account. It does not include VPN/Wi-Fi/KRDP/model/email credentials, enable
the hotspot, connect an external account, or alter the phone. Extraction,
staging, archival, and verification use Linux volumes plus libarchive
ACL/xattr support; the output is re-extracted and checked so ownership, modes,
and extended attributes survive the round trip.

The earlier staged server-only rootfs is 1,028,140,049 bytes with SHA-256
`d2df10d8b198bc5656de4232b2153786a5e943050d3391277170b512cab6dd2c`.
The historical Plasma image is 2,022,113,204 bytes with SHA-256
`31e7d341ec97197e0d315cdb6822a98fe9bf3df6b50bf8606125fc694f62d0f9`.
Both contain the previous Linux 7.1.4 module set and remain non-candidates.

The current network-root Plasma archive is 2,007,186,653 bytes with SHA-256
`8711b34cf454a3f3eef04f12650ef0622ee575d80942e418e1c61f45679aa717`.
It was staged from the authenticated base on Nobara Linux, contains only the
exact `7.1.4-g7a5cef0db479` module tree, and passed a clean archive
re-extraction plus the complete rootfs verifier. It contains the selected
public SSH key but no private key, reusable host identity, network secret,
remote-desktop credential, or user data. Preparing the PC-backed export
creates one deployment-local Ed25519 server host key outside Git and pins
`sshd` to it. The restricted NFS host gate and two normal-coldplug phone boots
now pass, including persistent client authorization and server identity.

A newer resource-bounded, agent-isolated development archive is
2,007,027,068 bytes with
SHA-256
`5863cacf23a9c0cb972b37e3c71f801df77ccb708a277c0f2787d3afd9ac51e4`.
It was staged from source commit
`5292f3caf4acba7e548505a004f55e6c3276661e`, passed the complete verifier
before archival and again after extraction into a clean volume, and passed an
independent gzip/hash check. It adds a locked `rog5-agent` account, an empty
mode-`0700` private-data boundary, and a hardened loopback-only Chromium
service without changing the desktop user. The service is capped at two CPUs,
1.5/2 GiB memory high/max, 512 MiB swap, and 256 tasks, and its restarts are
rate-limited. It also stages `rog5-collect-baseline.sh`, a redacted one-shot
runtime metrics helper. This development artifact remains outside Git and has
not replaced the manifest-pinned live root, been exported over NFS, or booted
on the phone.

The later
[userspace readiness audit](../test-results/2026-07-27-arch-userspace-readiness-offline.md)
keeps every sealed diagnostic root unchanged, confirms its full
Plasma/KRDP/server package set and secret-free headless policy, and
fail-first fixes a systemd ordering cycle in future hotspot packaging.
Current staging now verifies both the hardened Chromium and hotspot units.
The resulting
[successor archive](../test-results/2026-07-27-arch-successor-rootfs-offline.md)
is 2,006,999,039 bytes with SHA-256
`88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a`.
It contains 655 current packages and passes the complete verifier before
archival and after clean extraction. The later
[protected-export result](../test-results/2026-07-27-arch-successor-protected-export-offline.md)
pins that identity in the manifest and verifies a 181,239-entry,
root-owned, read-only Btrfs subvolume plus three tamper cases. The
[pre-live HOLD](../test-results/2026-07-27-arch-successor-v1-prelive-hold.md)
adds one explicit-token, verifier-first NFS case and a strict-SSH first-boot
runner covering coldplug, sysusers/tmpfiles, agent isolation, headless
screen-off state, volatile machine identity, watchdog handoff, and normal
reboot. It has not been booted and no live cycle is authorized.

The newer
[successor-v2 archive](../test-results/2026-07-27-arch-successor-v2-rootfs-offline.md)
is 2,007,001,876 bytes with SHA-256
`0da5f1dbc05588fcda444b6ba6d8a66db8fa9749691b1f7e37132de9e8a88078`.
It retains all 655 packages and accepted v1 evidence while adding
kill-switch-first hotspot transitions, partial-failure rollback, and
AP-before-firewall cleanup. Its separate
[protected export](../test-results/2026-07-27-arch-successor-v2-protected-export-offline.md)
passes complete recursive verification and four mutation cases. Its
[pre-live HOLD](../test-results/2026-07-27-arch-successor-v2-prelive-hold.md)
adds dedicated verifier-first NFS, screen-off first-boot, strict-SSH,
watchdog-handoff, and one-reboot controls. The unarmed host check passed; no
NFS window or boot ran, and the root remains HOLD.

The later
[successor-v3 development archive](../test-results/2026-07-27-arch-successor-v3-power-button-offline.md)
is 2,007,033,670 bytes with SHA-256
`a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7`.
It keeps all 655 packages, reruns the byte-exact v2 verifier, then installs
and enables a confined `pmic_pwrkey` press handler for the existing
DPMS/backlight toggle. Both staged and clean-extracted roots pass the v3
verifier, and an independent archive contract rejects unsafe paths and
runtime credentials. Its separate
[protected pre-live HOLD](../test-results/2026-07-27-arch-successor-v3-protected-prelive-hold.md)
adds a root-owned read-only Btrfs export, four rejected COW mutations, an
exact-root verifier-first NFS control, a power-input-aware first-boot gate,
and a strict no-retry runner. The unarmed server preserves byte-identical
host state. V3 remains unserved and unbooted with no physical-button/display
acceptance; GPU diagnostic v10 remains the selected next live candidate.

`packaging/arch/packages.txt` is the single requested-package list. It contains OpenSSH, nftables, WireGuard tools, dnsmasq, NetworkManager, wpa_supplicant, wireless-regdb, UPower, Plasma Desktop, Plasma-NM, KScreen, greetd, KRDP, PipeWire/WirePlumber, ttyd/tmux, Chromium, Git, Node/npm, Python/pip, Mesa, and Freedreno Vulkan. Mesa/Freedreno is staged for mainline validation but is not accepted as working until the DRM/MSM GPU tier passes.

## Boot and session model

The target defaults to `multi-user.target`: SSH, networking, VPN, hotspot
support, ttyd, and on-demand headless Chromium can run without a compositor.
Chromium runs as `rog5-agent`, not the interactive desktop user. `greetd` owns
the physical login path and starts the packaged Plasma Wayland session only
through `graphical.target`.

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

This rootfs is now a live native-Arch result for the headless tier:
credential-free recovery, attended Linux 7.1 kexec, read-only UFS discovery,
host NFS isolation, normal systemd coldplug, key-only SSH, and zero-storage
boots pass. NetworkManager's USB exclusion is accepted, but Wi-Fi, greetd,
Plasma, KRDP, and Mesa still require their separate hardware gates before the
device is called usable. The
[read-only vendor Wi-Fi contract](../test-results/2026-07-27-arch-wifi-vendor-contract-hold.md)
proves the exact `17cb:1103`/`17cb:0108` PCI endpoint and matching staged
ath11k inputs, but remains HOLD pending a schema-checked PCIe/WCN6855 PMU
board description and a separately authorized client-only probe.

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

Run both routing regressions in a privileged, network-disabled builder
container before packaging:

```sh
podman run --rm --privileged --network none \
  --mount "type=bind,source=$PWD,target=/workspace/repo,readonly" \
  rog5-kernel-builder:ubuntu-24.04 \
  sh /workspace/repo/scripts/device/test-vpn-hotspot.sh
podman run --rm --privileged --network none \
  --mount "type=bind,source=$PWD,target=/workspace/repo,readonly" \
  rog5-kernel-builder:ubuntu-24.04 \
  sh /workspace/repo/scripts/device/test-vpn-hotspot-wireguard.sh
```

The first test sends IPv4/IPv6 and UDP/TCP DNS-port traffic across isolated
client, simulated-VPN, and ordinary-uplink namespaces. It proves the VPN path
works, packets never reach the ordinary uplink, unsolicited VPN-side traffic
cannot enter the AP client, VPN-interface loss stays closed, recreating it
restores DNS traffic, and teardown restores nftables and forwarding sysctls.
Receipt-marker mutation testing detects one-way UDP datagrams and TCP SYNs
even when replies are dropped. See the historical
[offline packet report](../test-results/2026-07-26-vpn-hotspot-packet-offline.md).
The
[real-WireGuard offline gate](../test-results/2026-07-27-vpn-hotspot-wireguard-offline.md)
adds a credential-free kernel handshake over a local TEST-NET veth underlay
and sends one hotspot-client packet through the unchanged production
kill-switch. It requires nonzero handshake and encrypted transfer counters,
refuses a network-connected container, erases its disposable mode-`0600`
keys, and repeats with exact cleanup. The
[v2 DNS/recovery gate](../test-results/2026-07-27-vpn-hotspot-v2-dns-recovery-offline.md)
then makes v2 the default, carries valid DNS framing over UDP and TCP,
requires endpoint loss to remain closed, restores both protocols after
recovery, and mutation-tests one-way DNS leakage. A real client still must
pass ath11k AP capability, DHCP/provider DNS, an on-phone/provider handshake,
radio coexistence, throughput, thermals, charging, and battery tests.
The vendor-contract checkpoint above does not authorize radio activation:
its live tree has one stale WLAN I/O-regulator phandle, and the mainline board
DTS does not yet encode the WCN6855 PMU supply graph.
