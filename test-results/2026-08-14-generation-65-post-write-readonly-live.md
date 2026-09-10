# Generation 65 post-write read-only live result

Date: 2026-08-14

Result: **UFS discovery failed because the sealed initramfs omitted all four
deferred UFS modules; exact Alpine fallback passed. Generation 65 is consumed
and must never be retried.**

The sole RAM-only cycle transferred all 44,423,703 runtime-bundle bytes,
accepted `COMMIT_EXEC`, and executed target release
`7.1.4-gae717d919f87` with boot ID
`b97fb696-a71b-44a0-a4db-e3a747c4e791`. Mainline USB NCM appeared and remained
available. The target entered `ufs-ready` at host monotonic 209883.712712 and
reported failure at 209940.005034, an interval of 56.292322 seconds. It never
reached storage locking, `userdata`, the local image, either ext4 mount,
OverlayFS, systemd, or SSH. This read-only profile exposed no storage-write
path.

Inspection of the exact candidate initramfs found no `/rog5-ufs-modules`
directory. Its size was 6,127,628 bytes, while the accepted v36 initramfs
contains the four release-matched deferred modules. Consequently the module
loader had nothing to load and the 45-second UFS discovery wait could not
succeed. This is the direct cause of the Generation 65 failure.

Fallback boot ID `4871e7c8-2fd6-494b-8f26-79214255ef50` passed strict identity
proof and host cleanup. PMIC evidence recorded `PS_HOLD / HARD_RESET`, no
watchdog signal, and no retained fatal token. Pstore was unavailable, so its
absence remains inconclusive. The durable lifecycle intent resolved as
`FALLBACK_RETURNED`.
