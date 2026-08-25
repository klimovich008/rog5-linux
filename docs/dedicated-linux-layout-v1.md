# Dedicated Linux storage layout v1

> Reactivated as a geometry proposal after Generation 99 converted unchanged
> `userdata` to ext4 and Generations 162–163 repeatedly booted the staged local
> Arch image. Do not execute the historical Stage-1/2 artifacts: their fallback
> and source-image assumptions predate the current slot-A rescue and staged-seal
> image. A refreshed executor, read-only preflight, and exact final confirmation
> are still required.

## Recommendation

Use the tail of the existing large `userdata` partition for one aligned
32-GiB native Arch root. Keep every partition before `userdata` unchanged,
including Android `super` and `metadata`, keep slot A as the ASUS charging and
recovery route, and retain the remaining approximately 195 GiB of `userdata`
for persistent server data and signed recovery bundles.

This is the smallest Phase-3 layout change that gives Arch a native block
filesystem. It avoids both boot-slot changes and unnecessary reclamation of
the 7-GiB `super` partition. The latter is too small for a comfortable Arch
root after the current sealed tree, package updates, and rollback space.

Status: **geometry reverified; execution HOLD.** The historical executor is not
eligible for reuse. The current battery and slot-A charging route are healthy,
but a successor must bind the current userdata filesystem, staged image, backup
set, slot-A rescue, and exact Generation-163 local-root baseline.

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
| measured offline minimum | 11,698,467 blocks (47,916,920,832 bytes) |
| proposed offline pre-shrink | 51,124,000 blocks |
| measured headroom at pre-shrink | 39,425,533 blocks (161,486,983,168 bytes) |

Generation 74 repeated the estimate from an independent RAM-only recovery
after exact fallback remount-to-read-only, read-only UFS/GPT validation, and
`e2fsck -fn`. The exact PASS frame also reported zero block-backed mounts and
all physical block nodes read-only. This measurement is still not permission
to resize. The actual operation must run a forced offline `e2fsck` and repeat
the minimum-size estimate immediately before shrinking.

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
key, and kexec; it contains no partition/filesystem mutation command.
Generation 74 completed the RAM-only physical gate; see its
[live result](../test-results/2026-08-15-generation-74-storage-preflight-live.md).

The complete offline checkpoint is recorded in
[the 2026-08-14 result](../test-results/2026-08-14-dedicated-linux-layout-v1-offline.md).

The Stage-1 successor streams a fresh `sgdisk` backup and exact raw GPT ends
over framed ACM, waits for the host to validate and durably fsync all three
objects, and accepts only the matching operation/nonce/set-hash ACK. It then
proves and disarms the exact 900-second recovery rollback process before the
first write. This avoids an intentional reboot interrupting `resize2fs` or the
GPT transaction. The helper rejects stale process identities and ambiguous
timer children and resumes a frozen watchdog on a pre-disarm failure.

Two final Stage-1 initramfs builds are byte-identical at SHA-256
`74f4ecc24de5686eea059d83d9a455cd83e8cca6ecd5bd406bd2d07c2a781bd4`
(5,934,933 bytes) and took 3.489 seconds together. The sealed AArch64 tools
execute under QEMU. An exact-size disposable disk then completed the forced
check, ext4 shrink, GPT split, post-check, fresh-GPT restoration, and restored
filesystem check. See the
[Stage-1 offline result](../test-results/2026-08-15-storage-layout-stage1-offline.md).

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

Stage 1 leaves the `userdata` ext4 filesystem at exactly 51,124,000 4-KiB
blocks. The new partition contains 51,124,696 blocks, leaving 696 blocks
(2,850,816 bytes) of deliberate tail slack. Stage 1 does not grow the
filesystem after changing GPT.

## Destructive operation boundary

The eventual operation is deliberately limited to these mutations:

1. boot the sealed tool recovery entirely from RAM, require the exact
   900-second pre-mutation rollback window, and verify the fresh LUN/GPT/ext4
   identity against the private inventory with zero block-backed mounts;
2. capture a fresh `sgdisk` backup and raw primary/secondary GPT ends, stream
   them to a new private host directory, and refuse to continue until the host
   has validated and durably fsynced them and returned the exact nonce-bound
   ACK;
3. prove and disarm that exact userspace rollback process before making the
   selected disk and partition writable;
4. run forced ext4 checking, repeat the minimum-size estimate, and shrink ext4
   to exactly 51,124,000 4-KiB blocks;
5. in one GPT transaction, force `sgdisk --set-alignment=1`, preserve
   partition 23's first LBA, type, unique GUID, name, and attributes while
   changing only its last LBA to 53,477,375, then create partition 24 over
   LBAs 53,477,376–61,865,978;
6. reread and revalidate both GPT copies, partitions 1–22, the 51,124,000-block
   clean filesystem, and all physical read-only locks;
7. prove the unchanged slot-A ASUS charging/recovery route still works before
   any partition-24 write;
8. in a separately gated Stage 2, raw-clone the freshly attested 16-GiB local
   image into partition 24, verify the clone prefix, change only its filesystem
   UUID, grow it to the partition, and create a fresh native-root tree seal;
   and
9. keep the kernel/recovery RAM-only until native-root SSH and rollback pass
   repeatedly.

The execution environment must contain pinned `e2fsck`, `resize2fs`, `sgdisk`,
`partprobe`, and `mkfs.ext4`. It must create a fresh in-RAM GPT backup and copy
that backup to the host before step 3. A power loss between ext4 shrink and GPT
resize remains recoverable because the smaller filesystem still fits in the
old larger partition; the reverse order is forbidden.

The repository contains the sealed Stage-1 executor and host backup/ACK
collector. The private prepared candidate, execution record, and one-use claim
remain unconsumed and cannot run until the battery, slot-B, identity, artifact,
backup, and claim checks all pass again. The exact tool-bearing recovery and
disposable 4-KiB-sector transaction have passed offline. A command-level
rehearsal first proved that
omitting `--set-alignment=1` silently moves the recreated `userdata` start,
then proved that the corrected option preserves the exact start, GUID, type,
name, and attributes. The result is recorded in the
[2026-08-15 command rehearsal](../test-results/2026-08-15-dedicated-linux-command-rehearsal.md).
The final phone command, private identity bindings, generated partition UUID,
and fresh pre-write backup hash are kept together in a private execution
record for the required final confirmation.

The current staged image is clean, 17,179,869,184 bytes, and hashes to
`533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153`.
Its active tree seal is
`4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167`.
Any refreshed Stage 2 must bind these exact identities rather than either
historical image lineage below.

That Stage-2 path is now implemented offline as a distinct sealed executor.
It verifies the source hash and tree before disarming the recovery timer,
opens only the parent-disk/partition-24 write window, hashes the complete clone
prefix before changing its UUID, grows ext4, and atomically publishes the
fresh 37,738-entry seal. Final initramfs twins are byte-identical at
`36202033676f8d5217e3426ba05a5818e9b8787b3bae4145e050eb78a3ad0ba2`
(6,075,358 bytes). The AArch64 verifier and storage tools pass their runtime
closures. This is preparation only: Stage 2 cannot be issued before Stage 1
and the intermediate Alpine fallback proof. See the
[Stage-2 offline result](../test-results/2026-08-15-storage-layout-stage2-offline.md).

The machine-readable public geometry is
[`configs/storage/rog5-dedicated-linux-v1.json`](../configs/storage/rog5-dedicated-linux-v1.json)
and its focused verifier is
[`scripts/host/verify-dedicated-linux-layout.py`](../scripts/host/verify-dedicated-linux-layout.py).
