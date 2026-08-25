# Local-image direct V48 offline checkpoint

Result: **OFFLINE PASS; ADMITTED ONCE; UNBOOTED.** No V48 phone contact or claim.

V48 keeps the same kernel, DTB, module closure, 37-range map, fixed image path,
storage bounds, and fallback. It replaces 4 KiB direct syscalls with 1 MiB
`ibs`/`obs` plus exact byte-count and byte-seek BusyBox flags. The final partial
block remains 4 KiB aligned. It accepts only a zero-byte or exact 16 GiB
root-owned regular partial before truncating and restarting from zero.

Exact BusyBox execution and the full 1.85 GiB fake-target stream pass. Target
initramfs twins match at SHA-256
`27ea9cda1dfc8b032c78eae06e76d1424ceadcc786c17a3418e125950d6256c9`,
size 23,806,263 bytes. Signed bundle manifest SHA-256 is
`b20c4ae492aecbf000c258456031c30f74847f816af347f40084d6c7569bbba2`.
Generation-157 wrapper SHA-256 is
`a1bf83388dc820764af0735aaa32eddad416b24a97c10e23a6d9e383846316ac`.
