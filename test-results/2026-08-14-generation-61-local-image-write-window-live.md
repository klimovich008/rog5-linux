# Generation 61 write-window live result

Date: 2026-08-14

Result: **consumed failure; no image mutation; exact fallback passed; never
retry.**

Generation 61 ran from exact repository SHA
`d6d38a3919be79e7e692de83a348bc6906378a91` after local CI and exact-head
GitHub Actions run `31778601128` passed. Recovery transferred the exact
`persistent-root-local-image-write-window-v39` bundle, completed PREPARE, and
accepted one COMMIT. Mainline Linux `7.1.4-gae717d919f87`, boot ID
`06f63c65-3d61-4297-865b-59121bc0f952`, reported:

| Host monotonic receive time | Exact stage |
|---:|---|
| 192216.294406 | `ufs-ready: ENTER` |
| 192222.331829 | `userdata-resolved: ENTER` |
| 192224.343417 | `userdata-mount: ENTER` |
| 192225.350801 | `image-write: ENTER` |
| 192226.357535 | `write-window-blockdev: FAIL` |

The fixed v39 boundaries prove that userdata unmount, the exact all-node
read-only precheck, selected-partition `BLKROSET`, and parent-disk `BLKROSET`
all returned successfully. Effective `blockdev --getro` verification then
failed before sysfs/count verification, the outer userdata RW mount, loop
attachment, image RW mount, marker creation, or final relock. The retained
record does not identify which physical node mismatched and does not justify
assuming it was `/dev/sda`.

The storage-quiescent rollback returned exact Alpine fallback, boot ID
`a95e42f0-5d80-482b-af09-1f2ed3ee6c1e`. Strict fallback identity, profile
restoration, intent resolution as `FALLBACK_RETURNED`, host cleanup, and Steam
socket restoration passed. No formal fallback postmortem record was retained
for this cycle, so no reset-cause claim is made.

Read-only fallback inspection attached the 16 GiB image through a read-only
loop, passed `e2fsck -fn`, and mounted it
`ro,noload,nodev,nosuid,noexec,noatime`. Label `ROG5_ARCH_A`, UUID
`598a876b-a8db-4859-a01a-1b864b0a87f4`, size 16 GiB, clean state, and mount
count one were unchanged. `/var/lib/rog5`, the marker, and its `.next` path
were absent. Generation 61 therefore performed no persistent marker mutation
and must never be retried or flashed.

The minimal successor retains the exact operation count and write surface and
classifies the existing effective-state check as selected or unrelated,
disk or partition, and blockdev or sysfs.
