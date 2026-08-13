# Generation 51 local-root stage checkpoint

Status: **offline checkpoint superseded by the sole consumed live cycle; never retry or flash**.

Generation 51 preserves Generation 50's exact Linux Image, DTB, four deferred
UFS modules, physical read-only locks, exact userdata `ro,noload` mount,
complete root-seal verification, tmpfs OverlayFS, systemd, key-only SSH, and
bounded rollback. It adds a fixed outbound-only TCP heartbeat from
`169.254.77.2` to the host's `169.254.77.1:8079`. The six-line ASCII record is
bounded, release- and boot-ID-bound, monotonically sequenced, stored only on
tmpfs, and exposes no listener, shell, command, or evaluation surface.

Exact identities:

- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- clean-twin initramfs SHA-256: `2f8fb42078cc9c827953cd0ad5a67042aae8a8989f60b4056319c25f3dccc280`
- signed manifest SHA-256: `53afa65bb7134e7d5acccc2126aa8764fd3918c7cab02c61417f4be1572aad27`
- Generation 51 AVB SHA-256: `3fbcf296b054460a4a5a48092e55e4df080c6e308430177cf999d42ff6ef39cc`

The initramfs twins built in 1.111 and 1.126 seconds; deterministic AVB
generation took 1.836 seconds. Focused target, runner, claim, current-profile,
admission, and stable-gate tests pass. This checkpoint authorizes no flash or
persistent phone write.

The later sole live cycle is recorded separately in
[Generation 51 local-root stage live result](2026-08-13-generation-51-local-root-stage-live.md).
