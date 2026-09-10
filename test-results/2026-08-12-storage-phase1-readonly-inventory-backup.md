# Storage Phase-1 read-only inventory and backup — 2026-08-12

## Result

Pass. A temporary RAM boot of the exact backed-up Alpine `boot_b` image
produced a read-only inventory of seven UFS LUNs, 109 GPT partitions, current
mount dependencies, boot slots, AVB images, filesystem signatures, firmware,
identity/calibration stores, and the verified fallback path. No phone
partition was flashed, formatted, erased, repartitioned, or restored.

All primary/backup GPT headers and entry-table CRCs passed, all 109 entries
matched sysfs geometry, and repeated boots demonstrated that Linux `sd*` names
are not stable identities. The current fallback uses slot B and the large
ext4 `userdata` filesystem.

## Backup result

The private host backup contains 14 GPT ranges and all 107 non-`super`,
non-`userdata` partitions. It covers 4,601,434,112 bytes. Every source SHA-256
matches the corresponding host SHA-256. A transient USB stream loss at record
84 left no accepted or partial object; fail-closed resume re-hashed the exact
83-record prefix before completing records 84–107.

The final verifier passed in 5.231 seconds. It re-hashed every accepted file,
reconstructed all seven GPT layouts as sparse host images, and recovered the
exact 109-entry map from the restored metadata.

The private evidence root contains 148 hash-manifested files totaling
4,735,963,709 bytes. Private dumps, per-device GUIDs, filesystem UUIDs,
fastboot identifiers, and partition hashes remain outside Git.

## Dynamic partitions

Read-only first/last 16 MiB captures of `super` recovered valid primary
metadata for Android A/B system, system-ext, product, vendor, ODM, and one B
snapshot COW. Current AOSP `lpdump` required a checksum repair only in a
disposable sparse host copy; source bytes were never changed. `super` and the
separate Android `metadata` partition are evidence-supported Phase-3 reclaim
candidates, not current write targets.

## Next gate

Keep secondary subsystem work frozen. Prove stable repeated mainline UFS reads,
then create one 16 GiB ext4 image inside `userdata` and RAM-boot Arch from that
image read-only with a tmpfs upper. Retain NFS and exact Alpine fallback until
the local-root path repeatedly beats the Generation-20 379.548-second SSH
baseline.

See [the Phase-1 storage contract](../docs/storage-migration-phase1.md).
