# Recovery v18 Linux 7.1 kexec result

Status: **PASS** for one attended Linux 7.1 recovery boot and automatic
rollback. Nothing was flashed, no physical storage was exposed to the target,
and no persistent phone state was intentionally written.

## Staging and load

- The manifest-pinned v18 image passed a fresh real fastboot preflight.
- Credential-free staging ACM appeared at 07:31:34.
- Immediately before load, staging reported:
  - expected 5.4.210 wrapper release;
  - RAM-backed `rootfs`;
  - zero block-backed mounts;
  - 116 physical disks/partitions read-only with zero failures;
  - rollback marker still armed.
- The loader verified `Image`, `board.dtb`, and `initramfs.cpio.gz`.
- Exactly one allowlisted `qcom,hh-watchdog` control was disabled and verified.
- The loader stopped after `kexec -l`; `/sys/kernel/kexec_loaded` reported `1`.
- Execution remained a separate attended `kexec -e` command at 07:33:42.

Kexec-tools warned that `/proc/kcore` was unavailable and used its ARM64
fallback path for VA-bit discovery. The wrapper configuration is 39-bit VA,
the load syscall succeeded, and the kernel reported the image loaded before
execution. The fallback behavior is documented in the
[upstream kexec-tools patch discussion](https://lists.infradead.org/pipermail/kexec/2021-December/023766.html).

## Linux 7.1 target

The exact recovery gadget re-enumerated after kexec. Credential-free ACM
reported:

| Gate | Result |
|---|---|
| kernel | `7.1.4-g7a5cef0db479` |
| root | RAM-backed `rootfs` |
| block-backed mounts | 0 |
| physical block devices | 0 |
| rollback marker/watchdog | armed/alive |
| ACM supervisor and `/dev/ttyGS0` | alive/present |
| authorization/SSH | absent/stopped |
| UDC/NCM carrier | configured/1 |
| host NCM ICMP | pass |
| fatal log signatures | 0 |

Zero physical block devices is expected because the recovery DTB disables the
UFS controller and PHY.

## Rollback

The target rollback marker was never removed. Its independent 180-second timer
returned the phone to exact fallback product at 07:37:19. The fallback boot
identity changed from the pre-test baseline and SSH became reachable again.

## Promotion

The RAM-only Linux 7.1 recovery gate passes. The next phase is a separately
built read-only UFS discovery candidate: enable only the reviewed controller,
PHY, regulators, and reset; prohibit filesystem mounts; force every discovered
device read-only; and retain the same ACM/NCM and automatic rollback boundary.
