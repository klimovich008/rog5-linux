# Native Arch/Debian network-root gate

This is the first full-distribution boot after accepted read-only UFS
discovery. It runs a normal ARM64 distribution as PID 1 directly on Linux,
not inside Android, while keeping phone storage absent from the kernel.

Status: **complete offline bundle and rootfs stage pass; host export and live
boot remain pending**. No network-root image has been transferred to or booted
on the phone.

## Chosen design

The development PC exports one prepared rootfs over NFSv4.2 on the dedicated
USB NCM link. The phone mounts that export read-only, places a size-limited
tmpfs above it with OverlayFS, and executes `switch_root` into the merged tree.

```text
PC rootfs directory -- NFSv4.2 read-only --> phone lower layer
                                             + 2 GiB tmpfs upper
                                             = writable overlay root
                                             -> systemd multi-user.target
```

This gives systemd, SSH, package files, and ordinary Arch/Debian userspace
without writing UFS or mutating the host copy of the rootfs. A reboot discards
the tmpfs upper layer.

NFS is preferred over NBD for this gate because the phone receives no remote
block device. The only new mount is the exact read-only network export.

## Independent safety boundaries

- The Android wrapper remains temporary `fastboot boot`; no image is flashed.
- Kexec load and execution remain separate attended actions.
- The target reuses the accepted USB2 recovery DTB, where UFS, its PHY,
  SuperSpeed QMP, and the secondary USB controller are disabled.
- The dedicated kernel also compiles out SCSI, UFS host drivers, UFS/QMP PHY
  drivers, BSG, RPMB, and SCSI disk support.
- Initramfs rejects any physical block device or block-backed mount before USB
  exposure and checks again immediately before `switch_root`.
- Device and host addresses are fixed at `169.254.77.2/30` and
  `169.254.77.1`; no command-line network/export parser is present.
- The NFS lower mount is fixed to NFSv4.2 over TCP, port 2049, read-only.
- The tmpfs upper is capped at 2 GiB and mounted `nodev,nosuid`.
- A 60-900 second watchdog opens `/proc/sysrq-trigger` before `switch_root`,
  so it can reset the phone even if the network root or new userspace stalls.
- No private key, SSH host key, machine identity, VPN secret, email data, CV,
  API token, or browser profile enters the kernel/initramfs bundle.

## Kernel and initramfs contract

`configs/kernel/rog5-network-root.fragment` is layered after the normal
mainline requirements. NFSv4.2, its dependencies, OverlayFS, tmpfs xattrs,
USB ACM/NCM, and `/proc/config.gz` are built in. Every UFS/SCSI path is
disabled in the final configuration, not merely left unused by the DTB.

`initramfs/network-root-init`:

1. mounts only proc, sysfs, devtmpfs, devpts, and tmpfs;
2. requires exactly one `rog5.netroot=1`;
3. proves zero physical storage and zero block-backed mounts;
4. arms the independent reset watchdog;
5. creates credential-free ACM diagnostics plus USB NCM;
6. configures the fixed point-to-point address;
7. mounts the exact NFS export read-only;
8. creates the tmpfs/OverlayFS merged root;
9. repeats the no-phone-storage check;
10. moves `/dev`, `/proc`, `/sys`, and `/run`; and
11. executes the distribution's `/sbin/init`.

The target watchdog PID remains in `/run/rog5-network-root-watchdog.pid`.
During the first attended test it is disarmed only after the host verifies the
kernel, mounts, zero-storage state, network path, systemd target, and SSH.

## Offline result

The v1 bundle passes its fourteen-file verifier:

- two fresh Linux 7.1.4 output volumes produced byte-identical config, raw and
  compressed Images, modules, and metadata;
- NFSv4.2, OverlayFS, tmpfs xattrs, ACM, and NCM are built in;
- SCSI, UFS, SCSI disk/BSG/RPMB, and the UFS/combo/PCIe/SuperSpeed QMP PHY
  paths are absent from the final config, with no UFS module in the archive;
- target and nested staging initramfs builds are byte-identical and contain no
  authorization key, host key, machine identity, or private key;
- two clean ASUS wrapper builds and two header-v3/AVB repacks are
  byte-identical; and
- nested hashes, wrapper metadata, boot command line, accepted recovery-DTB
  identity, and unsigned AVB footer all pass.

The signed 818,293,654-byte Arch Linux ARM input also re-verifies under the
pinned Arch Linux ARM key, and the Linux-native rootfs path preserves metadata
and executes the extracted userspace as `aarch64`. The final
2,007,208,337-byte archive was staged from a fresh volume with the exact
`7.1.4-g7a5cef0db479` modules, pinned A660 firmware, key-only SSH, and the
headless-first Plasma/server package set. Its SHA-256 is
`e0de832fadc4005dc46aca17c3b9ecb4b4b5c107e1e35472e2971172d2a2861b`.
Re-extraction into a second clean volume passed the complete architecture,
ownership/mode/xattr, module, firmware, identity, networking, SSH, and desktop
contract.

## Rootfs policy

Arch Linux ARM remains the primary target because the existing signed staging
workflow already covers the server, VPN/hotspot, and Plasma package set.
Debian is the fallback if an Arch-specific userspace blocker appears; the
kernel and initramfs transport are distribution-independent.

The first boot is deliberately headless:

- `multi-user.target`;
- key-only SSH;
- no Wi-Fi, hotspot, VPN, browser, KDE, GNOME, or GPU test;
- NetworkManager must leave `usb0` unmanaged so it cannot remove the address
  carrying its own NFS root;
- no `/etc/fstab` entry may name a block device, UUID, or PARTUUID; and
- SSH host keys and machine identity are generated only in the tmpfs overlay.

KDE Plasma is preferred over GNOME for the eventual GUI because the repository
already has a minimal Plasma/KRDP path and measured baseline. It is enabled
only after the headless boot, display, input, and GPU gates pass.

## Host boundary

The host export must be:

- read-only;
- restricted to the exact phone address;
- reachable only through the dedicated USB interface/firewall zone;
- absent from `/etc/exports`;
- enabled only for an attended test; and
- removed when the phone returns to fallback.

Installing `nfs-utils`, starting `nfs-server`, or changing the runtime firewall
is an external service setup and requires user confirmation. Offline kernel,
initramfs, rootfs, and preflight work does not.

The offline host implementation now passes
`scripts/host/test-network-root-host.sh`. After confirmation,
`prepare-network-root-export.sh` authenticates the exact archive, extracts it
with ACL/xattr support into `/var/lib/rog5-network-root-v1`, seals its artifact
identity, and runs the independent path-based verifier.
`serve-network-root.sh` then:

1. refuses an existing NFS service, export, kernel server, firewall zone, or
   unexpected root;
2. creates only runtime firewalld rules and blocks the NFS and fixed mountd
   ports in every previously active zone;
3. binds NFSv4.2/TCP only to `169.254.77.1`;
4. exports a read-only bind mount only to `169.254.77.2`, using
   `no_root_squash` because PID 1 and root-owned key files must remain
   readable;
5. recognizes only the `ROG5_network_root` CDC-NCM gadget and gives it the
   `/30` host address in a temporary drop-by-default zone; and
6. unexports, stops its private server processes, unmounts, restores the
   temporary sysctl, and removes all runtime firewall state on exit.

The privileged path has not been run. The current host still lacks
`nfs-utils`, and its default workstation zone broadly allows high ports; that
is why the dedicated zone and pre-zone drop rules are mandatory.

## Acceptance gate

Before any live attempt:

1. two clean kernel builds must be byte-identical — **passed**;
2. two initramfs builds must be byte-identical and credential-free — **passed**;
3. the final kernel config must prove built-in NFS/OverlayFS and absent UFS —
   **passed**;
4. the reused recovery DTB hash and disabled-node contract must pass —
   **passed**;
5. the staged rootfs must pass architecture, systemd, module, SSH, network,
   fstab, identity, secret, and archive round-trip checks — **passed**; and
6. host NFS/firewall preflight must pass without broad network exposure —
   **offline contract passed; privileged runtime test pending**.

Live acceptance requires exact kernel release, OverlayFS `/`, read-only NFS
lower, tmpfs upper, zero physical block devices, zero block-backed mounts,
`multi-user.target`, key-only SSH, stable USB traffic, no fatal kernel log,
and automatic return to the exact fallback kernel. Failure leaves the
watchdog armed.
