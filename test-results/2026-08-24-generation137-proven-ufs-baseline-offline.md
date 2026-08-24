# Generation 137 live-proven UFS baseline

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

This candidate restores the exact g359 Image `7c89d9a0…`, DTB `40fb477a…`,
and four UFS module hashes that previously produced 116 devices. The new target
contains only NCM/stage reporting, UFS module load/count, and bounded fallback.
It has no power loader, SSH, userdata resolver, installer invocation, block
locking, filesystem mount, or storage-write path.

Target twins are `474a0bab...f83986a`; manifest is
`914681f8...1b555c2`; Generation-137 recovery is
`68e3a667...f81ce4`. Raw stable recovery is unchanged.
