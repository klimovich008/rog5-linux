# Generation 81 mount-call result

Date: 2026-08-22

Result: **consumed; mount syscall identified; fallback passed.** Generation 81
must never be retried or flashed.

The target again passed power/USB, deferred UFS, storage lock, and exact
userdata resolution. It emitted exact stage detail
`userdata-mount-call`, proving `mount -t ext4 -o ro,noload` returned nonzero
before mountpoint, mount-table, inventory, or post-mount containment checks.
Exact stock slot-A fallback, host cleanup, and `FALLBACK_RETURNED` passed. No
phone-storage write occurred.

The next diagnostic must read, not mutate, the current filesystem identity and
superblock features and combine them with mount status and bounded ext4/VFS
dmesg classification. A bounded read-only Opus review recommended this before
any kernel config change. Casefold/`CONFIG_UNICODE` is plausible but remains
unproven.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation81-live-20260822-r1`.
