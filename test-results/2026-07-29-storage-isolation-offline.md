# Minimal-headless storage isolation — offline

Date: 2026-07-29

Result: **PASS hardware-free; corrected-target runtime observation pending;
authority=none**

## Outcome

The minimal headless target still uses the accepted storage-free Linux 7.1.4
configuration and corrected DTB: UFS, its PHY, SCSI disk support, and RPMB
remain disabled while the root stays on read-only NFS plus volatile tmpfs.
This increment closes runtime proof gaps without enabling a storage driver,
mounting a disk, or changing the persistent-root plan.

The canonical runtime record grows from 55 to 68 fields. It now requires:

- three distinct positive mount IDs for OverlayFS `/`, the NFS lower, and the
  tmpfs state mount;
- exact equality between those live IDs and the immutable initramfs
  `rog5-network-root-identity-v1` handoff record;
- exact OverlayFS `lowerdir=/mnt/root-ro`,
  `upperdir=/mnt/state/upper`, and `workdir=/mnt/state/work`, preventing an
  unrelated overlay from passing beside the attested mounts;
- `nfs4`, `vers=4.2`, and `proto=tcp` for the exact read-only
  `169.254.77.1:/` lower;
- zero entries in the complete block class, not only zero devices exposing a
  physical `device` link;
- zero SCSI hosts, RPMB devices, and exact-board
  `1d84000.ufshc` platform devices; and
- zero mounts whose major/minor identity resolves through `/sys/dev/block`.

These are fail-closed conditions for the current network-root profile. They
do not accept persistent storage, prove UFS reliability, or authorize a
write. A later persistent-root profile must replace—not weaken—this
zero-storage boundary under its separately approved read-only and write
gates.

## Mutation coverage

The target fixture emits one canonical 68-line record and rejects 27
mutations. The added storage cases reject:

1. a non-`nfs4` lower;
2. NFS version other than 4.2;
3. transport other than TCP;
4. live mount IDs that disagree with the initramfs attestation;
5. each changed OverlayFS backing path independently, including a hostile
   second-`=` suffix that must not be truncated;
6. any block-class entry;
7. an absent or linked block-class root;
8. a block-backed mount;
9. a SCSI host or dangling SCSI-class root;
10. an RPMB device; and
11. the board UFS platform device.

The host verifier has 21 test groups. Its new semantic check rejects
noncanonical, zero, or duplicate mount IDs, while the exact-value mutation
loop covers every new NFS and storage-isolation field.

## Verification

| Gate | Result |
|---|---:|
| target runtime fixture | golden record plus 27 rejected mutations |
| host runtime verifier | 21 tests passed |
| strict-SSH one-collection runner | passed |
| shell syntax and ShellCheck | passed |
| Python compile and diff check | passed |
| complete hardware-free repository `ci` tier | passed |

Current implementation identities:

```text
bd06c2451af9afd117b0ca4ad95e9870f94d9ff43ece7f3653e6d80b22665b93  scripts/device/collect-minimal-headless-runtime.sh
829d96afda6f0228ee39ccb2e6e426091ced75fd06d5b1668bffd6379a6cfead  scripts/device/test-collect-minimal-headless-runtime.sh
04a4627de626f3e816aca5c6f854fde93b8d065b19be4569f10155dadf6ec7ef  scripts/host/verify-minimal-headless-runtime.py
67ae400e6674249a35d58bc126ea8b8f72db55949de5b9d976765ea5973dae06  scripts/host/test-verify-minimal-headless-runtime.py
15ea75e65ad44347ea0cd1431d1e438f2fc8b2af234aba55c088d1d0e0f11dd9  scripts/host/test-run-minimal-headless-runtime-acceptance.sh
223436c93ff22f38efdf54dbb4829f48163de35da067a5306ac2b7132e82b11f  configs/compatibility/rog5-minimal-headless-v1.json
630cefe56a3cac3c76d4822a23bf0ef905d2afb8dccb67c65fd3c9c7af6a7c5d  configs/compatibility/rog5-core-source-dtb-v1.json
```

## Safety boundary

- No phone, USB device, fastboot, ADB, target SSH, or credential was used.
- No phone or host storage was mounted, written, removed, or reclaimed.
- No kernel, DTB, initramfs, bundle, or boot image was rebuilt or modified.
- No UFS/SCSI/RPMB code or DT node was enabled.
- The accepted fallback and temporary-boot-only model are unchanged.
- Runtime acceptance on the corrected phone remains unproven and requires
  fresh explicit live authorization.

See the
[minimal-headless runtime contract](../docs/minimal-headless-runtime-acceptance.md),
[source/DT contract](../docs/core-source-dtb-contract.md), and
[persistent-storage design](../docs/persistent-storage.md).
