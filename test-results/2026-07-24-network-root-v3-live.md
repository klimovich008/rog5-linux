# Network-root v3 offline and live result

Status: **PASS**. The reproducible v3 bundle retains a minimal shutdown
initramfs, boots Arch Linux ARM as PID 1 on Linux 7.1.4, and returns through a
normal systemd reboot to the persistent Alpine fallback. Nothing was flashed.

## Root cause and fix

The earlier v2 target had no `/run/initramfs`. Its read-only NFS lower and
tmpfs writable layer remained backing filesystems for OverlayFS `/`, while the
generated mounts conflicted with `umount.target`. A normal
`systemctl reboot --no-block` removed the USB gadget but did not reach the
kernel restart path.

V3 prepares `/run/initramfs` before `switch_root` and retains:

- the exact reviewed `network-root-shutdown` script;
- BusyBox and its AArch64 musl loader; and
- the directories needed by systemd's shutdown pivot.

During shutdown, the exitrd moves the NFS lower and tmpfs state mounts out of
the old OverlayFS root, unmounts the old root first, then unmounts its backing
filesystems. A lazy detach is only a fallback before the forced reboot syscall
and final emergency SysRq reset.

## Reproducible candidate

Two target initramfs builds, two nested staging initramfs builds, two clean
ASUS 5.4 wrapper builds, and two Android header-v3/AVB repacks matched
byte-for-byte. The fourteen-file semantic verifier and manifest check passed
offline.

| Artifact | Size | SHA-256 |
|---|---:|---|
| target initramfs | 5,840,728 | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | 27,036,728 | `13d0171a45794f7e81cbf1052ea456acbed5402ffcfa018dd74504c24bc16c5e` |
| ASUS wrapper Image | 69,372,416 | `d886d6b27902c2dab1c9d006e84842d76c7933513c9c245a516cb67850e83a6a` |
| raw boot image | 96,415,744 | `61bbea54474196b00cf1c047ca0459a2665854d85fdb4c204e4e7f98230b777d` |
| temporary-boot AVB image | 100,663,296 | `c21325ed75f935e52da58524f8efa6e99d550d0b753116a8abde00678ae25d8a` |

The Linux 7.1.4 Image, modules, config, metadata, and isolated recovery DTB are
unchanged from the accepted v2 hardware candidate. Exact identities for all
fourteen files are in `manifests/artifacts.tsv`.

## Attended RAM-only boot

The host first reverified the prepared Arch export and proved there was no
existing NFS listener, export, mount, or kernel NFS thread. The foreground
server then exposed one NFSv4.2/TCP listener on the USB-only address and one
exact-peer, read-only export in the drop-by-default runtime firewall boundary.

The phone entered Fastboot through the reviewed restart syscall helper. The
host issued only:

```text
fastboot boot boot-5.4.210-network-root-stage.avb.img
```

The ASUS recovery verified the embedded Image, DTB, and target initramfs
before kexec load. Kexec execution remained a separate attended command.

The resulting normal, unmasked Arch boot passed:

| Gate | Result |
|---|---|
| kernel / PID 1 | exact `7.1.4-g7a5cef0db479` / systemd |
| system state | running; multi-user, SSH, udev, and NetworkManager active |
| coldplug | udev-trigger and modules-load unmasked, result `success` |
| failed units | 0 |
| root | OverlayFS |
| lower | exact NFSv4.2 source, read-only |
| writable state | 2 GiB tmpfs, `nodev,nosuid` |
| physical block devices | 0 |
| block-backed mounts | 0 |
| USB | exact point-to-point address and carrier |
| retained exitrd | executable source hash matched; AArch64 chroot checks passed |
| kernel fatal signatures | 0 |
| thermals | 33 zones, 32–37 C |
| available memory | 10,693 MiB |
| NFS stability | all 1,008 module-tree files read |
| rollback | watchdog stayed armed through every gate, then was safely disarmed |

Client authorization and the prepared root's pinned server host identity both
passed strict key-only SSH. No private key, public-key body, fingerprint,
device serial, boot identity, or NetworkManager identity is recorded here.

## Normal reboot result

After the acceptance gate and watchdog disarm, the target ran:

```text
systemctl reboot --no-block
```

The network-root gadget departed after about six seconds. The persistent
Alpine fallback gadget returned after about 25 seconds on the exact installed
5.4 kernel. Strict key-only fallback SSH passed, including the persistent
client authorization and fallback server identity.

The attended host process then reported target departure and removed all
runtime state. Final checks found:

- zero NFS listeners, exports, bind mounts, and kernel NFS threads;
- zero matching runtime firewall rules and no interface in the temporary drop
  zone;
- the temporary nonlocal-bind sysctl restored;
- the network-root `/30` address absent and the fallback `/16` restored;
- Fastboot and ADB absent; and
- the host ModemManager service restored after the ACM handoff.

This closes the v2 orderly-reboot defect. It does not accept persistent
storage, display, battery/charging, Wi-Fi, audio, suspend, or GPU. Those remain
separate hardware tiers, and the v3 image remains an attended
`fastboot boot`/RAM-kexec development artifact that must never be flashed.
