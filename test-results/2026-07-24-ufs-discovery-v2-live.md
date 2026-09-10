# Read-only UFS discovery v2 live result

Status: **PASS live; automatic fallback restored**. The corrected discovery
kernel enumerated the complete UFS topology without a blocked command, power
transition, error-handler entry, writable block node, or block-backed mount.
The untouched rollback chain returned the phone to the exact fallback kernel.
Nothing was flashed.

## Candidate and staging

The manifest-pinned unsigned AVB image with SHA-256
`d22790e5b8aebba0dc78a6704b7d2845b0e4637e1256acd379e7dd6170f1540b`
was used only with `fastboot boot`. Fastboot accepted the temporary image; no
flash command was issued.

The credential-free staging environment reached exact kernel
`5.4.210-qgki-perf-kexec-stage-builtin-recovery` and passed these checks before
kexec:

- `/` was RAM-backed `rootfs` and the block-backed mount count was zero.
- All 116 physical disks and partitions reported read-only through an
  independent `BLKROGET` check; failures were zero.
- Recovery ACM and watchdog supervisor processes were alive, USB carrier was
  present, and the rollback marker remained armed.
- No authorized key or SSH daemon was present.
- The nested Image, DTB, and initramfs hashes passed, and the compressed
  initramfs passed its integrity check.
- `/sys/kernel/kexec_loaded` changed from zero to one only after the dedicated
  loader passed. Execution remained a separate attended `kexec -e`.

## Linux 7.1.4 result

The target reached exact kernel `7.1.4-gcfd385a1c754`. The command line
contained exactly one `rog5.ufs_discovery=1`, and `/proc/config.gz` attested
all required built-in paths:

```text
CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y
CONFIG_SCSI_UFSHCD=y
CONFIG_SCSI_UFS_QCOM=y
CONFIG_PHY_QCOM_QMP=y
CONFIG_PHY_QCOM_QMP_UFS=y
```

The live storage boundary passed:

- `/` was RAM-backed `rootfs`; block-backed mount count was zero.
- The kernel exposed 7 UFS disks and 109 partitions.
- All 116 physical nodes independently reported read-only; failures were
  zero.
- The sysfs-only inventory contained one header plus all 116 nodes.
- Blocked UFS query count and blocked SCSI command count were both zero in
  the attestation files and kernel log.
- SCSI host 0 reported `ufshcd`, and `1d84000.ufshc` was bound to
  `ufshcd-qcom`.

The corrected power containment also passed:

```text
auto_hibern8=0
host power/control=on
host power/runtime_status=active
```

The auto-hibern8-disabled, retained host-runtime-reference, and forbidden-WLUN
runtime-PM markers each appeared. Both userspace containment checks reported
`blocked queries=0 blocked SCSI=0`. There was no BKOPS, UFS error-handler,
fatal-error, blocked-query, or blocked-SCSI signature.

Recovery ACM, NCM, both supervisor processes, and the rollback marker remained
live. No credential or SSH service was present.

No filesystem probe, `blkid`, mount, fsck, raw-device read, partition command,
or storage write test was run. The complete inventory remains local; this
public report contains only aggregate topology.

## Automatic rollback

The rollback marker was deliberately left untouched. At the expected
180-second boundary the recovery USB gadget disconnected, and the known
fallback USB gadget returned without manual reboot, SysRq, or bootloader
interaction. The host-only USB network profile was restored and SSH verified:

- exact fallback kernel
  `5.4.134-qgki-perf-00001-g6c308144c23e`;
- a new boot identity;
- the expected normal ext4 root; and
- low fallback uptime consistent with a fresh boot.

The fallback pstore contained no retained record, including when mounted
read-only for inspection. It is therefore not possible to distinguish from
retained evidence whether `reboot -f` completed directly or the independently
armed five-second SysRq fallback completed the reset. The proven acceptance
claim is the important one: the untouched automatic rollback chain recovered
the phone, and no manual emergency action was needed.

## Decision

The read-only UFS discovery tier is accepted. Its result authorizes topology
design work only; it does not authorize mounting, modifying, repartitioning,
formatting, or flashing UFS.

The next native-userspace gate should keep UFS unmounted and boot a minimal
Arch Linux ARM or Debian root over the already proven USB NCM transport. A
persistent on-device root remains a separate, explicitly authorized migration
after charging, thermals, USB, networking, display, input, suspend, and
recovery are validated.
