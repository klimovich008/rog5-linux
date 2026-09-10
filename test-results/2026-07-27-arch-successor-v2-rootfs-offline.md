# Arch Plasma/server successor v2 rootfs — offline result

Date: 2026-07-27

Result: **PASS OFFLINE. A fresh Arch Linux ARM Plasma/server archive with
fail-closed VPN-hotspot transitions was built from committed packaging,
verified inside the AArch64 staging root, archived with metadata preservation,
extracted into a second clean volume, and verified again. It remains unbooted
and is not promoted.**

No phone command ran. No boot, kexec, flash, module load, NFS export, host
firewall, interface, or service changed. The build embedded only the
already-approved SSH public key; it did not read or embed a private key.

## Exact result

| Property | Value |
|---|---|
| local artifact | `artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v2.tar.gz` |
| size | `2,007,001,876` bytes |
| SHA-256 | `0da5f1dbc05588fcda444b6ba6d8a66db8fa9749691b1f7e37132de9e8a88078` |
| project commit embedded in root | `ed7fa5e12e888c90edfe6e89a45beb30a7b222f6` |
| kernel release | `7.1.4-g7a5cef0db479` |
| package count | `655` |
| builder image ID | `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941` |
| builder image digest | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |
| promotion state | `UNBOOTED_HOLD` |

The immutable input identities embedded in `/etc/rog5/build` are:

```text
rootfs_sha256=3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a
modules_sha256=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9
```

The signed Arch Linux ARM rootfs, matching Linux 7.1.4 module archive, and
three A660 firmware files passed their manifest size/hash gates before
staging. Pacman retained `PackageRequired` and `PackageTrustedOnly`.

## Hardened hotspot delta

The accepted successor-v1 control, service, and full staged-root verifier
remain byte-exact. Successor v2 installs separately versioned sources at the
same runtime paths and adds these fail-closed properties:

- the nftables kill switch loads before either IPv4 or IPv6 forwarding is
  enabled;
- an existing production nftables table or stale runtime state is refused
  instead of replaced;
- a failed nftables load or partial forwarding change rolls back;
- normal shutdown restores forwarding before removing the kill switch;
- failed forwarding restoration retains the kill switch and state for
  recovery; and
- systemd lowers the access-point connection before removing the firewall,
  including after a partial service-start failure.

The phone-side dnsmasq design remains DHCP-only (`port=0`). It advertises the
configured VPN DNS address instead of opening a local DNS path around the VPN.

Exact v2 control identities:

| Input | SHA-256 |
|---|---|
| hotspot control | `5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d` |
| hotspot systemd service | `8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814` |
| transition/rollback test | `9d129081d44d2328000fbf9960ace61ebfea9a293fc8f85ffbc85f8a76a9fb91` |
| successor-v2 staged-root verifier | `5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e` |

The v2 verifier first checks the complete accepted v1 verifier against
SHA-256
`e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f`
and runs it. It then compares the installed v2 control and service byte for
byte with repository sources and runs the transition test.

## Test evidence

The non-root transition suite passed normal up/check/down ordering, nftables
load failure, partial IPv6-forwarding failure, stale-table refusal, cleanup,
and systemd stop-order assertions:

```text
PASS v2 VPN-hotspot installs the kill-switch before forwarding, rejects replacement, rolls back partial failure, and lowers AP before firewall cleanup
```

Two disposable privileged containers with no external network passed the
packet-level suites:

```text
PASS isolated VPN path, IPv4/IPv6 leak blocking, unsolicited isolation, VPN-loss fail-close, and cleanup
PASS real WireGuard handshake, encrypted hotspot packet, and cleanup
```

The staging workflow then passed the full verifier before archiving and after
clean extraction:

```text
PASS staged Arch successor v2 rootfs kernel=7.1.4-g7a5cef0db479 hotspot=fail-closed-transition-v2
PASS staged Arch successor v2 rootfs kernel=7.1.4-g7a5cef0db479 hotspot=fail-closed-transition-v2
PASS staged Arch rootfs kernel=7.1.4-g7a5cef0db479 size=2007001876 sha256=0da5f1dbc05588fcda444b6ba6d8a66db8fa9749691b1f7e37132de9e8a88078
```

Package hooks that need a booted service manager or unrestricted host
devices reported expected chroot skips. They did not bypass either complete
verifier. The workflow left no running container or transient Arch
stage/verify volume.

## Modern userspace

| Package | Version |
|---|---|
| Plasma Desktop | `6.7.3-1` |
| KWin | `6.7.3-1` |
| KRDP | `6.7.3-1` |
| Chromium | `150.0.7871.46-1` |
| Node.js / npm | `26.5.0-1` / `12.0.1-1` |
| Python | `3.14.6-1` |
| Mesa / Freedreno Vulkan | `26.1.5-1` |
| NetworkManager | `1.58.0-1` |
| systemd | `261.2-1` |
| WireGuard tools | `1.0.20260223-1` |
| dnsmasq | `2.93-1` |

The default remains `multi-user.target`. NetworkManager, key-only SSH, and
the sleep inhibitor are enabled. Plasma/greetd is available through
`graphical.target`; headless Chromium, ttyd, and the VPN hotspot remain
disabled until explicitly configured and requested.

## Independent archive checks

After the builder completed, a separate host pass:

- reran size, SHA-256, and `gzip -t`;
- inspected every archive name and rejected absolute or parent-traversal
  paths;
- required build, package, module, firmware, and v2 control entries;
- confirmed the machine ID is empty;
- found no SSH host key, WireGuard configuration, NetworkManager connection,
  KRDP setting, or KWallet path;
- confirmed the embedded project commit contains the hardened packaging;
- counted exactly 655 installed packages; and
- matched the installed hotspot script and service to the reviewed v2 source
  hashes.

The manifest-backed archive contract and aggregate Linux rootfs tool suite
both passed.

Important build-control identities:

| Input | SHA-256 |
|---|---|
| host staging wrapper | `fb046dc1f53d087dcb83550a567d71f3a2bf489f8d478afe5f9533cf9cdef93c` |
| AArch64 stage runner | `2f99e7ff4afdaec51dd1b1bff9db4626c5f0e49a4542e9c6b72c4a0d9be2070a` |
| in-root stage | `8234c09b646143288c1e58ca52d0c3c4253f4c2b0e0ee07d8cc6cdcc6c0749d9` |
| complete accepted v1 verifier | `e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f` |
| successor-v2 verifier | `5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e` |
| requested package list | `83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2` |
| isolated Chromium service | `6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb` |

## Promotion boundary

This artifact supersedes successor v1 for offline userspace development only.
It does not modify or supersede the accepted v1 protected export or any live
GPU generation. It remains ignored local build output under an immutable
manifest identity.

Before any boot:

1. create a separate root-owned read-only Btrfs successor-v2 export;
2. recursively verify and mutation-test that export without changing v1;
3. create separately versioned NFS and one-shot target gates;
4. conduct a new HOLD/GO review; and
5. require normal first-boot tmpfiles/sysusers, coldplug, SSH, screen-off,
   resource, thermal, VPN-loss, hotspot, and clean-reboot evidence.

Physical Plasma/KRDP and accelerated Mesa remain behind the display/GPU
hardware gates.
