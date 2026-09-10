# Generation 137 live-proven UFS baseline

Result: **CONSUMED; UFS COUNT ZERO.** Never retry or flash.

This candidate restores the exact g359 Image `7c89d9a0…`, DTB `40fb477a…`,
and four UFS module hashes that previously produced 116 devices. The new target
contains only NCM/stage reporting, UFS module load/count, and bounded fallback.
It has no power loader, SSH, userdata resolver, installer invocation, block
locking, filesystem mount, or storage-write path.

Target twins are `474a0bab...f83986a`; manifest is
`914681f8...1b555c2`; Generation-137 recovery is
`68e3a667...f81ce4`. Raw stable recovery is unchanged.

The sole RAM-only cycle passed exact device, topology, slot-A, battery, signed
wrapper, transfer, PREPARE/COMMIT, target NCM, release, command line, and all
four module-load checks. It then emitted exact terminal sequence 2:
`stage=ufs-ready state=FAIL detail=ufs-count-0` after a bounded 20-second wait.
No block device, mount, installer, or storage write existed.

The exact serial returned at the anchored USB path as stock slot-A recovery
with `18d1:d001`, product `ASUS_I005D`, and one `ff/42/01` ADB interface. The
fallback verifier expected the older `0b05:7770` Android descriptor and
therefore could not complete proof initially. A targeted host correction now
accepts each complete exact tuple while rejecting mixed identities. It passed
against this live `18d1:d001` USB and the retained slot-A preboot record,
proving the stock recovery fallback without another phone boot. Physical
fastboot entry is still required for the next RAM-only cycle.

Generation 64 used the same target Image, DTB, and module bytes but a retained
ASUS wrapper kernel `71b48a03...d309455`; Generation 137 used
`838425a8...9c7783`. Opus initially ranked wrapper residual state highest.
Independent review then found a stronger live control that supersedes another
wrapper-only cycle: Generation 109 used the current wrapper plus ae717 Image
`1a1958fe...f9ce22`, passed UFS/userdata, and returned exact fastboot through
built-in PMK8350 reboot mode. Generation 138 therefore restores that complete
working target lineage rather than testing the historical wrapper first.
