# Arch Plasma/server successor rootfs — offline result

Date: 2026-07-27

Result: **PASS OFFLINE. A fresh normal Arch Linux ARM Plasma/server archive
was built from current packaging, verified in the AArch64 staging root,
archived with metadata preservation, extracted into a second clean volume,
and verified again. It is not promoted or boot-authorized.**

No phone command ran. No sealed diagnostic root, NFS export, firewall,
interface, or host service changed. The build used only the already-approved
SSH public key; no private key was copied, printed, or embedded.

## Exact result

| Property | Value |
|---|---|
| local artifact | `artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor.tar.gz` |
| size | `2,006,999,039` bytes |
| SHA-256 | `88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a` |
| project commit embedded in root | `22f5429fd5497ce1a37addb4ff9ab3cb9027af78` |
| kernel release | `7.1.4-g7a5cef0db479` |
| package count | `655` |
| builder image | `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941` |

The immutable input identities embedded in `/etc/rog5/build` are:

```text
rootfs_sha256=3cf5764fb6fec7bffdff98787e52ccd15d5d6390a2496c7028d7c4950404c56a
modules_sha256=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9
```

The source rootfs, module archive, and three A660 firmware files first passed
their manifest size/hash gates. The official Arch package signature policy
remained `PackageRequired` and `PackageTrustedOnly`.

## Build and verification sequence

The non-overwriting host workflow:

1. created PID-unique staging and verification volumes;
2. extracted the signed generic AArch64 root with ACLs, xattrs, and flags;
3. proved the chroot executes as AArch64;
4. removed the generic kernel and installed the current requested package set;
5. installed the exact project module tree and pinned A660 firmware;
6. installed current server, screen, metrics, VPN, browser-isolation, SSH,
   NetworkManager, greetd, Plasma, and KRDP policy;
7. ran the complete staged-root verifier;
8. archived with metadata preservation and deterministic gzip headers;
9. extracted the archive into a second clean volume; and
10. ran the complete verifier again before moving the `.part` file to the
    final name.

The terminal result was:

```text
PASS pinned A660 SQE, GMU, and SM8350 zap-shader firmware
PASS staged Arch rootfs kernel=7.1.4-g7a5cef0db479
PASS pinned A660 SQE, GMU, and SM8350 zap-shader firmware
PASS staged Arch rootfs kernel=7.1.4-g7a5cef0db479
PASS staged Arch rootfs kernel=7.1.4-g7a5cef0db479 size=2006999039 sha256=88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a
```

Package post-install hooks that require a booted system or unrestricted host
`/dev` reported expected chroot skips. They did not bypass the final
in-root or clean-extraction verifiers. First-boot tmpfiles/sysusers and normal
systemd coldplug remain live gates.

## Modern userspace

Selected package versions in the exact archive are:

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

The archive also includes XWayland, KScreen, Plasma-NM, greetd, PipeWire,
WirePlumber, OpenSSH, nftables, ttyd, tmux, Git, and pip.

The default remains `multi-user.target`. NetworkManager, key-only SSH, and
the sleep inhibitor are enabled. Plasma/greetd is reached only through
`graphical.target`; headless Chromium, ttyd, and the VPN hotspot remain
disabled until explicitly requested.

## Isolation and service identities

The locked `rog5-agent` system account has no login shell, SSH directory,
supplementary groups, device access, or desktop-user home access. Its private
state directory is mode `0700`. The loopback-only Chromium service has:

- two-CPU quota;
- 1.5/2 GiB memory high/max;
- 512 MiB swap and 256-task caps;
- reduced CPU and I/O weights;
- no capabilities or device access;
- strict home/system/kernel protection; and
- restart throttling.

Installed service hashes exactly match current packaging:

| Service | SHA-256 |
|---|---|
| isolated Chromium | `6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb` |
| corrected VPN hotspot | `4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525` |

The full verifier runs `systemd-analyze verify` on both. The hotspot unit
contains no dnsmasq/network-online ordering cycle.

## Independent archive checks

After the staging workflow completed:

- `gzip -t`, size, and SHA-256 passed independently;
- one complete listing rejected absolute or parent-traversal paths;
- all required Plasma/KRDP/server/agent entries were present;
- machine ID was empty;
- no SSH host private key was embedded;
- WireGuard configuration, NetworkManager profiles, KRDP settings, and
  KWallet data were absent;
- installed Chromium and hotspot unit hashes matched repository sources;
- no transient stage/verify volume or running container remained; and
- Git remained clean and synchronized.

Important build-control identities are:

| Input | SHA-256 |
|---|---|
| host staging wrapper | `7b1c782192718e7d54cadbfb2dbba667c962d5d90bb11267b3b558c64351792b` |
| AArch64 stage runner | `2f99e7ff4afdaec51dd1b1bff9db4626c5f0e49a4542e9c6b72c4a0d9be2070a` |
| in-root stage | `b9bde0627b86e08fb4bab1e2d6b3ea22199f132bb170719aabd285b749215038` |
| complete staged-root verifier | `e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f` |
| requested package list | `83328a5ca9d4b516888439037762829c0aa388292352810bc375b61114716bc2` |
| redacted runtime collector | `2726ffda517aa13d97da4c9b04712524ccded2ba6ac25f2021f337a10523b946` |

## Promotion boundary

This artifact supersedes the earlier development archive for offline
userspace work, but it does not supersede any live-accepted root or GPU
diagnostic generation. It remains under ignored local artifacts.

Before any boot:

1. add an explicit successor artifact/manifest contract;
2. create a new protected export and recursive verifier without modifying the
   sealed v10 root;
3. rerun key agreement and exact server/host isolation checks;
4. conduct a separate HOLD/GO review; and
5. require normal first-boot tmpfiles/sysusers, coldplug, SSH, screen-off,
   resource, thermal, and clean-reboot evidence.

Physical Plasma/KRDP and accelerated Mesa remain behind the display/GPU
hardware gates.
