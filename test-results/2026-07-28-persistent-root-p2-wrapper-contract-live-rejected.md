# Persistent Arch P2 wrapper-contract live attempt

Date: 2026-07-28

Result: **REJECTED BEFORE STAGING; FALLBACK PASS; NO FLASH.**

The attended command temporarily booted the manifest-pinned ASUS wrapper.
Fastboot accepted the image, but the phone returned to the exact Alpine
fallback before the recovery ACM appeared. No P2 load command, kexec, target
probe, storage mount, selector change, or flash operation occurred.

## Rejected input

| Input | Identity |
|---|---|
| temporary AVB wrapper | `439a945babb5af1af83b7f6ad07ec6a8c0bf3e74fe416925b2e1a416e3b39ae0` |
| raw header-v3 wrapper | `deaa9c047cd2251c4981f1c41ba5d144118b6ba1fceb216e58c310d6e6491bdf` |
| ASUS wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| target kernel | `7.1.4-gcfd385a1c754` |
| fallback kernel | `5.4.134-qgki-perf-00001-g6c308144c23e` |

The image was used only with `fastboot boot`. The bootloader still reported
unlocked `lahaina`, active slot B, and secure metadata before the attempt.

## Observed sequence

1. The clean synchronized branch and manifest/image preflight passed.
2. Fastboot transferred and accepted the 100,663,296-byte image.
3. The exact fallback USB gadget appeared instead of `ROG5_recovery`.
4. The guarded runner stopped before ACM staging and before kexec.
5. Strict fallback preflight passed exact kernel, BusyBox init, compatible,
   ext4 root, empty pstore, zero project modules, and safe thermals.
6. The staged Arch seal remained unchanged and `UNBOOTED`; `state/good`,
   `state/next`, and `arch-a.partial` remained absent; the backlight was off.
7. ModemManager was restored.

The private fallback attestation is caller-owned mode 0600 outside the
repository and has SHA-256
`f1fc6ad010e95929e573c45d5d63fb893f4803b483dd07ca5e2401eb3e646e77`.
It contains no committed serial or credential material.

## Root cause

The rejected boot-v3 command line enabled `rog5.ufs_discovery=1`. The ASUS
5.4 wrapper config does not define
`CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y`. Recovery `/init` correctly treats
that mismatch as a failed dedicated-kernel attestation and forces rollback
before configuring USB.

The flag was added after the first P2 run because its staging transcript
lacked the two custom UFS counter files. That inference crossed two kernel
contracts:

- the ASUS staging wrapper uses its accepted vendor UFS path, locks all 116
  physical block nodes read-only, and mounts no physical storage; and
- the Linux 7.1.4 target has the custom read-only UFS policy and receives
  exactly one `rog5.ufs_discovery=1` from its kexec loader.

The wrapper cannot truthfully produce the target-only custom counters. Its
preflight must attest its real boundary instead of enabling an unsupported
mode.

## Fail-first correction

Two new assertions failed before implementation:

- the boot-v3 contract rejected the wrapper's target-only UFS token; and
- the ACM contract required a fresh enumeration of all 116 physical nodes,
  zero writable nodes, and absence of target-only counter files.

The fixed staging preflight independently counts every physical disk and
partition, requires all 116 sysfs `ro` states to equal one, cross-checks the
initramfs lock count, requires zero block-backed mounts, verifies the nested
payload, and accepts only a loaded kexec image. The complete success marker
still exists only in successful output, not in the echoed command.

The boot-v3 parser now requires the exact staging tokens, rejects every
wrapper `rog5.ufs_discovery` token, and confirms that the wrapper config does
not claim the target-only option. The separate loader regression continues to
require exactly one `rog5.ufs_discovery=1` in the Linux 7.1.4 target command
line.

Two independent repacks are byte-identical:

| Corrected product | Size | SHA-256 |
|---|---:|---|
| raw header-v3 image | 96,067,584 | `5c9e0391f1be68f1257c3402eea4105508066b2b6afd26c450c4725e3ae1aba9` |
| unsigned AVB image | 100,663,296 | `f4f33bae1e69c8499527be159d409b53cea424e09eefc7e25c73157516d54249` |

The target Image, DTB, timing-diagnostic initramfs, nested stage, ASUS
wrapper Image, watchdog, root seal, and target read-only UFS policy were
unchanged in that correction.

## Decision

The rejected wrapper image is superseded and must not be retried or flashed.
P2 remains HOLD and P3 remains prohibited. After the corrected source,
manifest, tests, and report were committed and pushed, one attended
non-flashing run proceeded to the original target timing classification. It
reached recovery, executed the target exactly once, and
[safely selected the runtime kernel-config branch](2026-07-28-persistent-root-p2-config-timing-live-rejected.md).
