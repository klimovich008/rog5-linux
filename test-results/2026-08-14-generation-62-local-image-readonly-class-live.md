# Generation 62 effective-readonly discriminator live result

Date: 2026-08-14

Status: **consumed; exact Alpine fallback passed; never retry or flash.**

Generation 62 consumed its sole RAM-only claim for
`persistent-root-local-image-write-roclass-v40-live-v1`. Recovery accepted
exactly one signed bundle and target Linux `7.1.4-gae717d919f87` reported the
following ordered stages:

- `ufs-ready`;
- `storage-locked`;
- `userdata-resolved`;
- `userdata-mount`;
- `image-write`; and
- `write-window-selected-disk-blockdev: FAIL`.

Both selected-partition and parent-disk `BLKROSET` calls returned success, but
the parent disk remained effectively read-only. The failure occurred before
any outer userdata RW mount, loop attachment, inner ext4 RW mount, marker
creation, or persistent write. The first and terminal target stage records
were received 9.057 seconds apart.

The recovery progress channel closed cleanly after five records. The normal
rollback returned the exact pinned Alpine fallback, strict SSH identity proof
passed, the fallback NetworkManager profile was restored, and the host intent
was resolved as `FALLBACK_RETURNED`.

Read-only post-cycle inspection verified
`/rog5/images/arch-local-a.ext4` as a 16 GiB ext4 filesystem with label
`ROG5_ARCH_A` and UUID `598a876b-a8db-4859-a01a-1b864b0a87f4`. `e2fsck -fn`
reported it clean and the fixed write-probe marker remained absent.

The retained private cycle evidence is outside Git at
`/home/deck/.local/state/rog5-generation62-local-image-write-live-20260814.NJsMPQe2`.
Generation 62 is irrevocably consumed and must never be retried.
