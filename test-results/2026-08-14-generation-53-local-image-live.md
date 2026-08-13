# Generation 53 local-image live result

Date: 2026-08-14

Result: **PASS at the device objective; consumed and revoked. The 16 GiB local
Arch image reached strict key-only SSH with both ext4 layers read-only, then a
normal systemd reboot returned exact Alpine. Never retry or flash Generation
53.**

The sole `persistent-root-local-image-v32` RAM-only cycle used AVB image
SHA-256
`fee441e423675610ee828d13e58db4d1c02b3751a024b3bbf1834257bca55d58`
from reviewed repository head
`fb4e7319c3103f8c771308467a22d9c914f7c2df`. The exact one-use claim entered
before the temporary fastboot boot. Recovery transferred all 45,806,325
bundle bytes and committed one target execution.

Mainline boot ID `17bcfcba-a80b-423b-a57c-2474c2c15d40` reported this target
timeline:

| Target uptime | State |
|---:|---|
| 2.895 s | kernel identity passed |
| 2.906 s | UFS discovery entered |
| 11.725 s | UFS discovery passed |
| 12.284 s | 116-node storage lock passed |
| 13.763 s | exact userdata resolved as `/dev/sda23` |
| 14.763 s | userdata mounted `ro,noload` |
| 14.843 s | exact 16 GiB image resolved |
| 15.917 s | image mounted `ro,noload` through `loop0` |
| 22.592 s | boot-critical local root verification passed |
| 22.634 s | UFS-health check passed |
| 22.659 s | tmpfs OverlayFS creation passed |
| 23.235 s | final storage invariants passed |
| 23.247 s | `switch_root` entered |
| 25.494 s | `switch_root` passed |
| 57.870 s | systemd 260.2 entered system mode |
| 282.122 s | boot-critical root attestation passed |
| 298.620 s | strict key-only SSH runtime record completed |

The runtime record proved:

```text
kernel=7.1.4-gae717d919f87
physical_blocks=116
block_backed_mounts=2
userdata_mount=ro-noload
local_image_mount=ro-noload
root=local-ext4-overlay-tmpfs
blocked_device_queries=0
blocked_scsi_commands=0
journal_recovery_events=0
ufs_error_events=0
backlights=0
ssh=strict-key-only
userdata_device=/dev/sda23
result=PASS
```

The host pinned the target Ed25519 key approximately 332.186 seconds after
the one-use claim record was created. The complete runtime record was present
approximately 352.991 seconds after that record. On the target-uptime basis,
strict SSH completed 80.928 seconds sooner than Generation 20's 379.548-second
NFS-root result.

## Host parser defect and recovery

The sealed target correctly reported `root=local-ext4-overlay-tmpfs`, while
the Generation 53 host parser still required the older generic
`root=overlay-tmpfs` marker. The parser therefore rejected the already
successful runtime record before writing its timing record or running the
normal diagnostic/reboot tail. This was a host evidence-classification defect,
not a target boot, UFS, mount, systemd, or SSH failure.

The skipped read-only diagnostics were captured through the already pinned
target key. They showed both filesystems read-only, the expected tmpfs upper,
zero UFS errors, and the complete stage sequence. A normal
`systemctl reboot` then returned status zero. The original lifecycle process
subsequently proved exact Alpine fallback and clean host-network restoration,
while retaining its expected nonzero parser result. The parser regression now
requires the exact local-image marker and has a focused hostile test.

## Independent fallback evidence

Fallback boot ID `3bba77cf-87cd-498b-ade8-2213315c66ab` differed from the
target boot ID. The bounded signed postmortem reported:

- PMIC trigger `PS_HOLD` and reset type `HARD_RESET`, consistent with the
  requested systemd reboot;
- no watchdog signal and zero fatal tokens;
- `pstore_state=UNAVAILABLE`, zero records, and unavailable lineage.

The pstore absence remains inconclusive and is not proof that no crash
occurred. In this cycle, the live target diagnostics, successful SSH command,
zero-status reboot request, PMIC result, and exact fallback provide the
independent positive evidence.

Private evidence remains outside Git. Selected file identities are:

- stages: `54f83a191f98da11a873672a68d5036068f38b4a14afbeb5ca415f01e289c9d6`;
- runtime: `b1472ec8ca18db44ab05ca1008e24020c41c78d9718e85bd4905539b86222e0c`;
- manual read-only diagnostics:
  `c6da54400f2444110197a6086badc593c581b23ae24b5a7fe2eca9ec40554877`;
- signed fallback postmortem:
  `2ab131523d8b3cb6c5ceaec47da04a09d8b0d5768f2c34fb98cf0508ad653068`.

No partition, GPT, slot, bootloader, or raw block-device operation occurred.
The temporary target kept phone storage read-only. Generation 53 is uniquely
revoked and retained only as offline evidence. Its served bundle was removed
from `/var/lib/rog5-recovery-bundles` after an exact byte comparison and is
archived privately under the deployment state directory, outside Git.

## Publication validation

The focused 12-test lifecycle parser suite passed in 0.073 seconds; the
consumed-profile check passed in 11.212 seconds; the exact live-gate suite
passed in 6.041 seconds; and the 27-test retention admission suite passed in
3.098 seconds after its expected allow-row count was corrected from three to
two. Final `scripts/host/test-repository-linux.sh ci` passed in 469.657
seconds. The previous coherent checkpoint took 456.155 seconds, a 13.502
second increase.
