# Generation 84 encrypted-userdata result

Date: 2026-08-22

Result: **consumed; raw userdata architecture resolved; fallback passed.**

Generation 84 retained exact detail
`userdata-mount-call-s255-tunknown-bunknown-cx-ex-vx-qx-px-rx-ox-einval`
after a verbatim 64-byte read. Therefore raw partition 23 contains neither
plaintext ext4 nor F2FS magic and ext4 mount returns status 255/`EINVAL`.

The official WW33 fstab independently specifies `/data` as F2FS with
`metadata_encryption=aes-256-xts:wrappedkey_v0`, keys under
`/metadata/vold/metadata_encryption`, and `dm-default-key`. Mainline cannot
mount that decrypted filesystem by reading raw `sda23`; the old pre-restoration
ext4 local-image plan is no longer applicable.

Exact stock slot-A fallback, host cleanup, and `FALLBACK_RETURNED` passed. No
phone-storage write occurred. Generation 84 must never be retried or flashed.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation84-live-20260822-r1`.
