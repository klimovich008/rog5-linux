# Network-root v2 live result

Status: **PASS twice with normal systemd coldplug**. Arch Linux ARM runs
natively as PID 1 on Linux 7.1.4 from a read-only PC-backed NFS lower and a
tmpfs/OverlayFS writable layer. The phone exposed no physical block device and
nothing was flashed.

## Reproducible candidate

The v2 candidate replaces the earlier diagnostic workaround with a recovery
DTB that disables the two proven coldplug hazards and the GPU clients that
depend on them:

- `rmtfs_mem`, because its reserved-memory node overlaps the recovery ramoops
  reservation;
- `gpucc`, because a live `gpucc_sm8350` probe stalled and the attended
  watchdog reset the phone; and
- GPU, GMU, and the Adreno SMMU, which cannot be enabled safely without GPUCC.

The recovery DTB was built twice byte-identically. Two clean, network-disabled
ASUS wrapper builds and two Android header-v3/unsigned-AVB repacks also
matched. The complete fourteen-file bundle passes its manifest and semantic
verifier.

| Artifact | SHA-256 |
|---|---|
| recovery DTB | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| nested kexec-stage initramfs | `73f6616acec1080236fe98fe994c99b3a3c28f998305571beb2ad67814f2e3ff` |
| ASUS wrapper Image | `877bb79263d29942b629a0ab3c713d935ef1619801fdb10fd7d33a47aababf13` |
| raw boot image | `b86c6aaf977176b992e48d9aa3bdc6a5e010c3105f0dc4114e06eb3d65860f2d` |
| temporary-boot AVB image | `8174287fa5f599e39adcc34dbf31ed6be4c020abf770dbbbe0c12de489710327` |

## Normal-coldplug acceptance

Both attended boots used `ROG5_SYSTEMD_DIAGNOSTIC=0`; the kernel command line
contained no `systemd.mask=` argument. Each boot passed:

| Gate | Result |
|---|---|
| kernel / PID 1 | exact `7.1.4-g7a5cef0db479` / systemd |
| system state | running; multi-user, SSH, and udev active |
| coldplug | udev-trigger and modules-load unmasked, result `success` |
| failed units | 0 |
| root | OverlayFS |
| lower | exact NFSv4.2 export, read-only |
| writable state | tmpfs, `nodev,nosuid` |
| physical block devices | 0 |
| block-backed mounts | 0 |
| USB | exact point-to-point NCM address and carrier |
| isolated hazards | five DT nodes disabled; `gpucc_sm8350` and `rmtfs_mem` absent |
| kernel fatal signatures | 0 |
| thermals | 33 readable zones in the accepted range |
| available memory | about 10.4 GiB |
| NFS stability | full module-tree read passed |
| rollback | watchdog validated while armed, then safely disarmed |

Normal coldplug loaded the reviewed non-hazardous Qualcomm support modules,
including NVMEM, LPASS pinctrl, PON, reference regulator, RNG, ADC/thermal,
stats, TEE, crypto, and SoC-info drivers. The phone remained stable beyond
the old deterministic 16-second reset boundary and through repeated
30/60-second gates.

An early ad-hoc log check used case-insensitive matching and falsely matched
ordinary `debug:` and `ramoops:` text. The exact case-sensitive fatal filter
reported zero panic, Oops, BUG, external-abort, or watchdog-bite signatures.

ICMP to the host is intentionally dropped because the exact USB interface is
placed in the drop-by-default firewall zone and only the phone-to-host NFS
flow is allowed. This is not a transport failure: SSH worked in both
directions required by the test, NFS remained mounted, and a sustained full
module-tree read passed.

## SSH persistence

Client authorization and server identity are separate:

- the dedicated client private key remains outside the repository at
  `~/.ssh/rog5_linux`, mode 0600;
- its public half remains installed in both the persistent Alpine fallback
  and the prepared Arch root;
- the prepared PC-backed Arch root now owns one deployment-local Ed25519
  server host key, with the private half root-owned and mode 0600; and
- `sshd` is pinned to that one host-key path.

Strict key-only fallback login passed after each reset. The Arch client key
authenticated on two separate native-Linux boots. On the second boot an
unqualified SSH scan advertised exactly one host identity, and it matched the
first boot byte-for-byte. No private key, public-key body, fingerprint, device
serial, or boot identity is committed or recorded in this report.

A later unchanged RAM-only boot also accepted the same pinned Arch host
identity immediately. After returning to fallback, strict key-only login
passed again and both the persistent authorization file and fallback server
host key remained present.

## Reboot and remaining boundary

The earlier normal `systemctl reboot --no-block` test removed the network-root
gadget but did not return fallback, fastboot, or ADB within 120 seconds; the
phone was electrically absent from USB. That orderly mainline reboot path is
therefore still a defect.

The kernel reset path itself is healthy. On an unchanged v2 boot,
`systemctl reboot --force --force` bypassed the systemd manager and invoked
the reboot syscall: the USB gadget departed after about seven seconds and the
installed fallback returned after about 21 seconds. Strict fallback SSH then
passed and the attended NFS listener, export, bind mount, runtime firewall
state, and host interface state were removed. This narrows the remaining
defect to normal userspace shutdown rather than the arm64 PSCI/Qualcomm kernel
restart path.

Live inspection also found no retained `/run/initramfs`. The NFS lower and
tmpfs upper are separate generated mount units that conflict with
`umount.target`, while both remain backing filesystems for OverlayFS `/`.
This is the leading shutdown-teardown hypothesis; it still requires a
retained shutdown-initramfs implementation and an attended normal-reboot
test.

For these two persistence cycles, after all gates and watchdog disarm, the
read-only root was synced and the already validated emergency SysRq reset was
used. Fallback returned, strict SSH checks passed, and the attended NFS export,
listener, mount, temporary sysctl, interface address, and firewall rules were
all removed.

The phone is back in the persistent Alpine fallback with the host NFS service
and temporary firewall state absent. Network-root v2 is a
safe, reversible native-Linux bring-up transport, not yet an independent
daily-driver installation: UFS, GPU/display, battery/charging, Wi-Fi, audio,
and suspend remain separate hardware tiers.
