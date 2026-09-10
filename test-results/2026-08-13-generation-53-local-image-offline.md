# Generation 53 local-image offline checkpoint

Status: **built and verified offline with `authority=none`; not admitted,
not booted, and never flash.**

Generation 53 reuses the exact Generation 52 ASUS recovery wrapper, Linux
7.1.4 Image, DTB, and deferred UFS modules. Its target is the bounded
local-image successor: read-only UFS and userdata, one exact 16 GiB ext4
image attached read-only, the minimal deployment-key-bound Arch root, tmpfs
OverlayFS, checked mount handoff, systemd, key-only SSH, stage reporting, and
the existing 600-second rollback.

Exact identities:

- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- clean-twin initramfs SHA-256: `39f1d9a700d8c37cf434ef5d9608d0723571de807a7df0a3957d80be258066e4`
- signed manifest SHA-256: `ae1069eb2f85e1b93c24f831e440a54303ca80934864f7fca07afcf34adfaca1`
- manifest signature SHA-256: `d73ecdfcac1ae30d88cc43a7acfc495da85050a0e14b7436817324c98a95cbcb`
- raw recovery SHA-256: `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`
- Generation 53 AVB SHA-256: `fee441e423675610ee828d13e58db4d1c02b3751a024b3bbf1834257bca55d58`
- AVB salt: `608b5a5694b785d736739ce269d467cf6571575b3520d0e9dc85fd37db5dfe16`
- AVB digest: `fd02fdb7862f6b08eb23a1718d9d42c55ff05ce26f4bd4a2c5d17945a52e2e00`

The two production-key bundle builds took 205.390 and 211.179 ms. Every
bundle file is byte-identical across the twins, and the retained native
verifier produced the same exact execution plan from each. Deterministic AVB
generation took 1.800 seconds and preserved the raw recovery payload.

Generation 52 is now uniquely `revoked` in temporary boot policy and
`consumed` in artifact inventory. Generation 53 has no policy row, claim, or
live profile. No phone contact, phone write, candidate execution, flash, slot
operation, or boot occurred at this checkpoint. Admission remains downstream
of exact cleanup and verified local-image staging.
