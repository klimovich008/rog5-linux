# Dedicated Linux layout v1 offline checkpoint

Date: 2026-08-14

Starting commit: `04b7506f27ba8ad22241c26ff47f9e94aca74fe9`

Phone storage mutation: none

## Result

The proposed 32-GiB native Arch-root layout passed its public geometry tests,
an exact disposable GPT transaction/restoration rehearsal, and a deterministic
read-only recovery-tool build. This checkpoint does not authorize or contain a
phone partitioning command.

The proposal preserves partitions 1–22, changes only partition 23's tail, and
creates aligned entry 24. The verifier reports:

```text
userdata_bytes=209406754816
arch_root_bytes=34359717888
ext4_headroom_bytes=161499561984
```

All eight hostile geometry tests passed. A fresh verification of the private
Phase-1 backup also passed 14 GPT ranges, 107 protected partition images,
4,601,434,112 bytes, and all seven restoration rehearsals in 5.636 seconds.

## Disposable GPT rehearsal

A sparse host file reproduced the exact 253,403,070,464-byte LUN and its
4,096-byte logical-sector geometry. The host initially exposed the loop device
read-only; the rehearsal detected that state and changed only the disposable
loop device to writable before proceeding.

The exact transaction then passed:

```text
SGDISK_TRANSACTION_PASS entry_count=32 proposed_userdata_last=53477375 root_first=53477376 root_last=61865978
GPT_RESTORE_PASS restored_userdata_last=61865978
```

The transaction preserved the existing partition 23 type and unique identity,
created entry 24 with the standard Linux filesystem-data type, passed
`sgdisk -v`, and restored the original primary/backup GPT bytes afterward. No
phone interface was used.

## Sealed read-only recovery tools

The recovery builder pins the reconstructed v18r base and these signed Alpine
v3.24 AArch64 packages by SHA-256:

| Package | SHA-256 |
|---|---|
| `sgdisk-1.0.10-r1.apk` | `b37f3d8ce629ee38132e308ef0c7e6e6d661e308c02975718a69ceb94136dcb5` |
| `popt-1.19-r4.apk` | `5eb2037c453c870f31a1db4f1235f8ac2a27f8d401421cb5662f2ff6f1bea94b` |
| `libgcc-15.2.0-r5.apk` | `369aaa6e9d099a737bad6dd3e6c2fe7bb1547ca26d22b94ee0411228f709b403` |
| `libstdc++-15.2.0-r5.apk` | `2302e766d4e4926038ec166ecb85837ee884576115236ddb565e3a5fca4a11d7` |
| `musl-1.2.6-r2.apk` | `5e9674b7f41152fe2119093b5cb4c13eaaadb19c2d5422b2d7267913e663ee6e` |
| `libuuid-2.42.1-r0.apk` | `d2f69552b05184ba205dbc8aa0e79f8a080fcf746ec5e5e25eb89d66fbbe6db6` |

All package signatures verified offline against the pinned Alpine verifier
image. The assembled AArch64 `sgdisk`, `e2fsck`, `resize2fs`, `mkfs.ext4`, and
BusyBox `partprobe` binaries executed under QEMU with the staged musl loader.

Two independent initramfs builds completed in 2.052 seconds and matched:

```text
recovery-init c1b83c2bf72b722629ddbe0ed76ea6a743aaab0784f9b0495fd55073421ef53c
storage-preflight 46e81f34900905ac82bd3ad8749e5332a571e50e3ceb388c5c8b5c825a13ddfb
```

The mode runs one exact-LUN/GPT/ext4 inspection while block nodes are locked
read-only. It removes SSH, shell-access credentials, bundle fetch/control,
kexec, and the recovery trust key. It has no `sgdisk` mutation, `resize2fs`
resize, `mkfs.ext4` device, or writable-block command.

## Tests

- storage-preflight initramfs contract: 4 tests passed;
- recovery init policy: 14 tests passed;
- dedicated-layout verifier: 8 tests passed;
- existing full and observation-only recovery integration: passed in 107.699
  seconds using the reconstructed-v18r profile;
- repository runner contract and Markdown link checks: passed.

The next action is a temporary RAM-only boot of the sealed read-only preflight,
followed by exact ACM report capture and verified Alpine fallback. Any ext4
resize or GPT write still requires the separately presented exact destructive
operation and final operator confirmation.
