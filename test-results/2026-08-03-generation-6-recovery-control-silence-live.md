# Generation-6 recovery-control silence — live

Date: 2026-08-03

Result: **REJECTED safely and consumed before COMMIT**. The sole admitted
Generation-6 RAM-only recovery boot reached verified recovery ACM/NCM and the
one-transfer service sent the complete 46,163,787-byte signed diagnostic
bundle. Recovery control produced no output and no authenticated `PREPARED`
record. Independently, the diagnostic collector's fixed 120-second target-ACM
preflight expired with zero frames. No durable commit intent existed,
`COMMIT_EXEC` was never sent, and no target ran.

## Exact candidate

- profile: `headless-diagnostic-generation6-live-v1`
- AVB image SHA-256:
  `6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398`
- unchanged raw recovery SHA-256:
  `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`
- signed diagnostic manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
- recovery trust-root SHA-256:
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`
- host verifier SHA-256:
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`
- connected checkpoint:
  `40ad052fd0f64669e8028f20ebdfec575c9aa19a`, GitHub Actions run
  [`30807236352`](https://github.com/klimovich008/rog5-linux/actions/runs/30807236352)
- fastboot serial and private evidence directory: retained outside Git

## Live sequence

1. The central policy contained one exact Generation-6 row. The connected
   preflight passed after the reviewed fallback helper returned the phone to
   exact `lahaina` fastboot.
2. The AVB footer, `NONE` vbmeta structure, and exact 58,101,760-byte raw boot
   descriptor passed verification. Fastboot accepted the 100,663,296-byte
   image for temporary RAM-only boot.
3. Recovery exposed the pinned ACM and NCM identities with rollback armed.
   The host anchored the physical USB location and started the receive-only
   diagnostic collector before any possible commit.
4. Recovery requested the signed bundle. The one-transfer server sent the
   831-byte manifest, 64-byte signature, Image, DTB, and initramfs, reporting
   exactly 46,163,787 bytes and successful network cleanup.
5. No canonical recovery-control output was received; its private log is the
   zero-byte SHA-256 empty-file identity. The collector never observed the
   distinct target diagnostic ACM and rejected at its fixed 120-second
   preflight deadline with `frame_count=0` and `target_boot_id=None`.
6. Because no `PREPARED`/COMMIT boundary was established, the lifecycle had
   no durable intent to resolve. It did not start NFS and did not execute the
   target.

## Rollback and host state

The anchored fallback-profile restoration passed, followed by strict-key SSH
to exact Alpine on the same USB port. The automated final controller cleanup
proof returned **FAIL** on the restored `169.254.77.1/30` address. Clean host
state therefore rests on the independent read-only residue checks below, not
on the intended automated proof. The failure is a verifier defect: production
udev reports `ID_MODEL=ROG_Phone_5_Linux_Server`, while
`rog5_ncm_interfaces()` currently
accepts only models beginning `ROG5_`. Consequently its exact-interface set
was empty even though NetworkManager showed the canonical
`rog5-fallback-usb-ssh` profile active on `enp4s0f3u1u2` with only the expected
address.

Independent read-only checks after controller exit found an empty NFS export
table, no lifecycle marker/export/mount, no project listener on the bundle,
NFS, or rpcbind ports, and only the pre-existing loopback browser listener on
TCP 8080. The phone remained on exact Alpine fallback. No image was flashed;
no partition was erased, formatted, mounted by the host, or selected for a
new slot. Strict-SSH and reboot handling may have caused only the bounded
fallback atime/sync effects covered by standing authorization.

## Private evidence seals

| Record | SHA-256 |
| --- | --- |
| stable-recovery boot | `21ec4b4cad177892971ab1b2817277844d9be561d1b4e6d5ed0558197be20947` |
| recovery USB anchor | `fcf65acde7107ca2d2e5cdbc769e5ab0d4516de82fc6f81e3fd2432fb4745e15` |
| bundle server | `9bdc6eb5732ad074b8aef5facbfe4c6c8baef8e48b59a09561213f2f1910edb7` |
| recovery control | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| diagnostic collector log | `970a479aed1fdd0484a0dfb540f567c36766918c294ddd37cddb2b598a1a3429` |
| diagnostic collector record | `9768e2e58879fd14683b2999c9ea5c1c5a145636984a5254bce719d9ee8ad381` |
| fallback restoration | `8608f0478541424f17bca20c9ab7adb85ba3cbe7da7fb986457fb4c358a99658` |
| fallback strict-SSH proof | `c6432c9b31f985030290e137d4f9b3be42e32cb2636c4ef8960aa7f06e9bbe15` |
| fallback identity | `a27fe3e82f3feeee90715ff731cf33d254df03fc5389c80efcfd0d31f1ed717f` |

## Disposition and next correction

Generation 6 is single-use and consumed. Its central-policy row is removed,
its inventory role is consumed/offline-only/never-retry-or-flash, and tests
require its absence.

Before issuing a distinct successor:

1. reproduce the real fallback udev model in hardware-free lifecycle tests
   and accept only the explicit recovery, target, and fallback model set;
2. explain why a complete bundle transfer yielded no `PREPARED` response
   before the fixed collector deadline, preserving the no-retry and timeout
   lattice; and
3. verify clean fallback classification without weakening physical-port,
   driver, address, NetworkManager, or firewall checks.

Increasing a timeout or reusing Generation 6 is not an acceptable correction.

The first correction item subsequently passed offline in the
[fallback udev-model classification result](2026-08-03-fallback-udev-model-classification-fix-offline.md).
The complete-transfer/control-silence boundary was unresolved when this live
result was first published; this does not change Generation 6's consumed
status or repair the failed live cleanup proof retroactively.

Subsequent timestamp and NetworkManager-journal reconstruction showed the host
entered its fallback path after the 10-second deferred-profile cleanup failure
and before it waited for recovery control. See the
[offline deferred-profile correction](2026-08-03-generation-6-deferred-profile-association-fix-offline.md).
The empty control log therefore does not prove recovery-side silence. It also
does not supply the missing live `PREPARED` record.
