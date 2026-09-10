# Generation 64 contained-write live result

Date: 2026-08-14

Result: **bounded local-image write passed; later UFS-health gate failed; exact
Alpine fallback passed. Generation 64 is consumed and must never be retried.**

The sole RAM-only cycle booted target release `7.1.4-g359318de534f` with boot
ID `7c3afb64-8e84-4f4b-87f4-88d19c2646de`. It passed exact UFS discovery,
userdata resolution and mount, image resolution, the contained partition and
parent-disk write window, outer userdata RW mount, writable loop attachment,
inner ext4 RW mount, exact marker write and sync, unmount, storage relock,
read-only userdata and image remount, and root verification. The subsequent
aggregate `ufs-health` stage failed and the target deliberately entered the
bounded rollback; this was not an observed target crash.

Fallback inspection mounted the image only through a read-only loop and
proved:

- ext4 UUID `598a876b-a8db-4859-a01a-1b864b0a87f4`, label `ROG5_ARCH_A`, and
  clean `e2fsck -fn` status;
- exact marker metadata `0:0:0444:132:1` and SHA-256
  `9581532937a6791a74d55f61fb23b324769a8f0baff576066dae21d6dd5abac3`;
- marker producer boot ID equal to the Generation 64 target boot ID;
- exactly one marker, no `.next`, loop, or mount residue.

The transport did not retain the four individual UFS-health counters, so the
specific aggregate predicate that failed is unknown. The controlled write
experiment itself is complete. Generation 65 therefore returns to the
previously accepted read-only kernel and uses the persisted marker as fixed
writer-lineage evidence rather than rewriting it.
