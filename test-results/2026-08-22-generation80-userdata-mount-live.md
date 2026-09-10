# Generation 80 userdata-mount result

Date: 2026-08-22

Result: **consumed; power/UFS advanced; fallback passed.** Generation 80 must
never be retried or flashed.

The target passed the bracketed data and power role checks, complete power/USB
loader, deferred UFS discovery, UFS power containment, physical storage lock,
exact userdata resolution, inventory publication, and post-rescan read-only
containment. It then emitted exact stage sequence 9:

`stage=userdata-mount`, `state=FAIL`, `detail=none`.

The failure occurred before local-image resolution or SSH. Exact stock slot-A
fallback, host cleanup, and `FALLBACK_RETURNED` passed. No phone-storage write
occurred.

The successor preserves the exact `mount -t ext4 -o ro,noload` operation and
adds only a bounded discriminator for directory creation, mount syscall,
mountpoint verification, mount-table verification, block-backed mount
inventory, physical read-only containment, expected `/rog5` directories, and
selector absence.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation80-live-20260822-r1`.
