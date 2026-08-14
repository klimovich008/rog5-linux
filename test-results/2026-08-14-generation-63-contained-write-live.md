# Generation 63 contained-write local-image live result

Date: 2026-08-14

Status: **consumed; exact Alpine fallback passed; never retry or flash.**

Generation 63 consumed its sole RAM-only claim for
`persistent-root-local-image-write-contained-v41-live-v1`. Recovery fetched
all 45,794,794 signed bundle bytes and target Linux
`7.1.4-g359318de534f` reported this ordered path:

- `ufs-ready`;
- `storage-locked`;
- `userdata-resolved`;
- `userdata-mount`;
- `image-resolved: PASS`;
- `image-write: ENTER`; and
- `image-fs-rw: FAIL`.

The exact partition-and-parent write window, outer userdata RW mount, and
writable loop attachment therefore passed. Source and initramfs inspection
then identified the immediate defect: `/mnt/probe-root` was never created, so
the inner ext4 mount failed before any inner-filesystem or UFS data write.

Rollback returned exact Alpine, restored the fallback profile, and resolved
the intent as `FALLBACK_RETURNED`. Read-only postcheck verified the 16 GiB
image label `ROG5_ARCH_A`, UUID
`598a876b-a8db-4859-a01a-1b864b0a87f4`, clean `e2fsck -fn` status, mount
count one, absent fixed marker, successful `ro,noload` mount, and no mount
residue.

Retained private evidence is outside Git at
`/home/deck/.local/state/rog5-generation63-contained-write-live-20260814.15rJroja`.
Generation 63 is irrevocably consumed.
