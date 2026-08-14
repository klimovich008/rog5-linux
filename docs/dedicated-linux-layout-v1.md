# Dedicated Linux storage layout v1

## Recommendation

Use the tail of the existing large `userdata` partition for one aligned
32-GiB native Arch root. Keep every partition before `userdata` unchanged,
including Android `super` and `metadata`, and keep the remaining approximately
195 GiB of `userdata` as the Alpine recovery root and persistent server-data
filesystem.

This is the smallest Phase-3 layout change that gives Arch a native block
filesystem. It avoids both boot-slot changes and unnecessary reclamation of
the 7-GiB `super` partition. The latter is too small for a comfortable Arch
root after the current sealed tree, package updates, and rollback space.

Status: **offline-rehearsed proposal only; no phone partition or filesystem
mutation has run.** The exact destructive operation still requires final
operator confirmation.

## Verified input

The authoritative private Phase-1 inventory was re-verified on 2026-08-14.
All 14 GPT ranges, 107 protected partition images, 4,601,434,112 backed-up
bytes, and seven sparse GPT restoration rehearsals passed in 5.636 seconds.

Strict pinned SSH then measured the current mounted fallback filesystem:

| Field | Value |
|---|---:|
| ext4 state | clean |
| block size | 4,096 bytes |
| current block count | 59,513,299 |
| free blocks | 47,320,908 |
| estimated minimum | 11,695,396 blocks (47,904,342,016 bytes) |
| proposed offline pre-shrink | 51,124,000 blocks |
| measured headroom at pre-shrink | 39,428,604 blocks (161,499,561,984 bytes) |

The estimate was taken while the fallback was mounted and is not permission to
resize it. The actual operation must first boot an independent RAM-only
recovery, unmount `userdata`, and pass a forced `e2fsck` before repeating the
minimum-size estimate.

## Offline gates passed

The exact primary and backup GPT bytes were placed in a disposable sparse disk
with the phone's 4,096-byte logical-sector geometry. The proposed `userdata`
tail change and entry 24 creation passed `sgdisk -v`, preserved the 32-entry
table and partition 23 identities, and produced the exact public LBAs below.
Restoring the retained GPT ranges then recovered the original partition 23 end
and removed entry 24. The first loop attachment exposed the host device as
read-only; the rehearsal detected that state and made the disposable loop
writable before running the transaction. It did not contact the phone.

A separate sealed `storage-preflight-v1` initramfs now contains only the pinned
AArch64 read-only inspection closure: `sgdisk` 1.0.10, e2fsprogs 1.47.4,
BusyBox `partprobe`, musl, and their exact libraries. Two independent builds
were byte-identical at SHA-256
`46e81f34900905ac82bd3ad8749e5332a571e50e3ceb388c5c8b5c825a13ddfb`
in 2.052 seconds. The image removes SSH, recovery bundle control, the trust
key, and kexec; it contains no partition/filesystem mutation command. Its next
gate is one RAM-only physical boot that reports GPT and ext4 preflight results
over fixed ACM while every physical block node remains read-only.

The complete offline checkpoint is recorded in
[the 2026-08-14 result](../test-results/2026-08-14-dedicated-linux-layout-v1-offline.md).

## Exact public geometry

All LBAs below are 4,096-byte logical blocks on the 253,403,070,464-byte main
UFS LUN. Per-device disk, partition, and filesystem GUIDs remain in the private
inventory and execution plan.

| Partition | Number | First LBA | Last LBA | Blocks | Bytes | Disposition |
|---|---:|---:|---:|---:|---:|---|
| existing prefix | 1–22 | unchanged | 2,352,679 | unchanged | unchanged | preserve byte-for-byte |
| `userdata` now | 23 | 2,352,680 | 61,865,978 | 59,513,299 | 243,766,472,704 | current Alpine/data ext4 |
| `userdata` proposed | 23 | 2,352,680 | 53,477,375 | 51,124,696 | 209,406,754,816 | preserve GUID/type/name; shrink tail only |
| `arch_root_a` proposed | 24 | 53,477,376 | 61,865,978 | 8,388,603 | 34,359,717,888 | new ext4 `ROG5_ARCH_A` |

`arch_root_a` starts on an exact 1-MiB boundary. It ends at the current last
usable LBA, so the backup GPT entries and header remain at LBAs 61,865,979–
61,865,983. There is no overlap or unallocated gap. GPT has 32 entries, so
entry 24 is available. The new type is the standard Linux filesystem-data GUID
`0fc63daf-8483-4772-8e79-3d69d8477de4`.

No storage-backed swap partition is proposed. Use zram first; this avoids UFS
write amplification and leaves the layout simpler.

## Destructive operation boundary

The eventual operation is deliberately limited to these mutations:

1. boot a tool-bearing recovery entirely from RAM and verify the fresh LUN/GPT
   identity against the private inventory;
2. unmount `userdata`, run forced ext4 checking, and repeat the minimum-size
   estimate;
3. shrink ext4 to exactly 51,124,000 4-KiB blocks;
4. in one GPT transaction, preserve partition 23's first LBA, type, unique
   GUID, name, and attributes while changing only its last LBA to 53,477,375,
   then create partition 24 over LBAs 53,477,376–61,865,978;
5. reread and revalidate both GPT copies before opening either filesystem;
6. grow ext4 partition 23 to its new boundary, check it again, and prove the
   Alpine recovery still boots;
7. format only partition 24 as ext4 label `ROG5_ARCH_A`, copy the already
   sealed Arch tree, verify it, and initially mount it read-only; and
8. keep the kernel/recovery RAM-only until native-root SSH and rollback pass
   repeatedly.

The execution environment must contain pinned `e2fsck`, `resize2fs`, `sgdisk`,
`partprobe`, and `mkfs.ext4`. It must create a fresh in-RAM GPT backup and copy
that backup to the host before step 3. A power loss between ext4 shrink and GPT
resize remains recoverable because the smaller filesystem still fits in the
old larger partition; the reverse order is forbidden.

No command in the current repository performs these mutations yet. The exact
tool-bearing read-only recovery and disposable 4-KiB-sector GPT transaction
have passed offline. After the read-only phone preflight, the final phone
command, private identity bindings, generated partition UUID, and fresh backup
hash will be presented together for the required final confirmation.

The machine-readable public geometry is
[`configs/storage/rog5-dedicated-linux-v1.json`](../configs/storage/rog5-dedicated-linux-v1.json)
and its focused verifier is
[`scripts/host/verify-dedicated-linux-layout.py`](../scripts/host/verify-dedicated-linux-layout.py).
