# Generation 82 unknown-type result

Date: 2026-08-22

Result: **consumed; classifier gap identified; fallback passed.** Generation 82
must never be retried or flashed.

The target emitted
`userdata-mount-call-s255-tunknown-cx-ex-vx-qx-px-rx-ox-einval`.
Mount status 255 and `EINVAL` were retained. BusyBox `blkid` did not expose a
recognized ext4/F2FS token, so the type-gated classifier did not invoke
`dumpe2fs`; current filesystem features remain unproven.

The successor reads only 64 bytes at the standard superblock offset to classify
exact ext4/F2FS magic, records blkid agreement separately, and runs
`dumpe2fs -h` whenever ext4 magic is present. Fixtures cover real-output-shaped
records and hostile type/magic lookalikes. Exact stock slot-A fallback, host
cleanup, and `FALLBACK_RETURNED` passed. No phone-storage write occurred.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation82-live-20260822-r1`.
