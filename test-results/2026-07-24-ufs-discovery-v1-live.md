# Read-only UFS discovery v1 live result

Status: **REJECTED safely; exact fallback restored**. The storage boundary
worked, but runtime power management attempted a forbidden auto-BKOPS query
after enumeration and orderly reboot then hung in the UFS shutdown path.
Nothing was flashed.

## Candidate and transport

- The exact manifest-pinned v1 unsigned AVB image was used only with
  `fastboot boot`.
- The ASUS 5.4 staging kernel booted entirely from initramfs with zero
  block-backed mounts.
- All 116 fallback-visible physical block nodes were independently read-only
  through both the block ioctl and sysfs.
- Recovery ACM, USB NCM, and the forced-reboot watchdog were live.
- Both initramfs layers contained no authorized key, SSH host key, password,
  or SSH daemon.

The first staging cycle passed every safety check but its watchdog expired
before the dedicated loader returned, so it rolled back without executing
kexec. The second cycle passed the same checks, verified every nested payload
hash, loaded the discovery payload with legacy kexec, and reported
`kexec_loaded=1`. Execution remained a separate attended command.

## Mainline discovery result

The target reached exact kernel `7.1.4-g44fd886a77b8` with the compile-time
discovery guard and built-in Qualcomm QMP UFS PHY and host driver attested
through `/proc/config.gz`.

- Root was RAM-backed `rootfs`; block-backed mount count was zero.
- Exactly 116 physical block nodes appeared: 7 disks and 109 partitions.
- Every node was read-only through both independent checks; failures were
  zero.
- The inventory contained one header plus all 116 nodes and was generated
  only from sysfs.
- SCSI host 0 reported `ufshcd`, and `1d84000.ufshc` was bound to the Qualcomm
  UFS driver.
- The device reported a SK hynix UFS product, and the primary LUN exposed
  approximately 253 GB decimal capacity.
- ACM, NCM, the target watchdog, and the rollback marker were live.
- No credential or SSH service was present, and no fatal log signature was
  present at initial attestation.

No filesystem probe, `blkid`, mount, fsck, raw-device read, partition command,
or storage write test was run. The full topology was retained locally; this
public report intentionally summarizes it.

## Rejection reason

After successful enumeration, runtime PM reached
`ufshcd_enable_auto_bkops()` and attempted three copies of:

```text
UPIU_QUERY_OPCODE_SET_FLAG / QUERY_FLAG_IDN_BKOPS_EN
```

The compile-time query gate rejected all three with `-EROFS`. The blocked
command count was therefore three, proving that no forbidden query reached
the device, but the upstream error path then:

1. failed `ufshcd_bkops_ctrl()`;
2. returned `-EBUSY` from WLUN runtime suspend;
3. entered the UFS fatal error handler with forced reset requested; and
4. later stalled orderly reboot while shutting the UFS WLUN down.

This violates the live gate even though the storage mutation boundary held.

## Recovery

The independent target watchdog expired and requested forced reboot, but that
process remained stuck in the UFS shutdown path. Because the target had a RAM
root, zero block-backed mounts, and all UFS nodes independently read-only, the
already-authorized emergency SysRq reboot was used. The phone immediately
returned to the exact fallback `5.4.134-qgki-perf-00001-g6c308144c23e`
kernel with a changed boot identity, and SSH recovery was verified.

No partition was mounted, modified, resized, formatted, or flashed during the
test.

## Remediation gate

Patch
`0003-ufs-pin-discovery-link-active-across-pm-and-shutdown.patch` keeps the
short-lived discovery link active:

- retain the runtime reference acquired before asynchronous scan;
- forbid runtime PM on both the UFS host and device WLUN;
- disable auto-hibern8;
- return before WLUN or host power-transition helpers can issue protocol
  commands; and
- skip WLUN shutdown state changes so platform reset can occur with the
  read-only link still active.

The source verifier requires those branches to occur before BKOPS, suspend,
quiesce, or shutdown calls and compiles the guarded objects. A replacement
bundle must also reproduce twice, pass the complete network-off verifier,
show zero blocked queries during an attended temporary boot, and roll back
orderly before discovery can be accepted.
