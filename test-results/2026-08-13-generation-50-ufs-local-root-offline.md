# Generation 50 read-only local-root offline checkpoint

Status: **unbooted RAM-only candidate; read-only local root only; never
flash**.

Generation 50 reuses Generation 49's exact clean-twin Linux 7.1.4 Image, DTB,
and four UFS modules. Its sealed initramfs removes only the deliberate
pre-mount proof/rollback terminal. After the same exact topology, power, and
read-only locks, it mounts freshly resolved userdata `ro,noload`, verifies the
181,242-entry Arch tree against its anchored seal, uses it only as a lower
layer with a 2 GiB tmpfs OverlayFS upper, starts Arch systemd, and requires
strict key-only SSH. No physical-write, journal-replay, selector, format,
partition, flash, or orderly-shutdown path is present.

Exact reproducible identities:

- source commit: `ae717d919f87b47ea9ed2173ea96660186b62a66`
- release: `7.1.4-gae717d919f87`
- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- target initramfs SHA-256: `343f73ce4772e80f9e7b3e610454aa6b0d86e83ea2e15c68ca64112f196508c3`
- signed manifest SHA-256: `ae22914906d63accc893157b51c683f24a3a7e933bba84e13661e664764b9cc6`
- manifest signature SHA-256: `bb79aedf1f5fa8ad876c40eac089eb881025f9eac38c509bedee5f55344ab572`
- Generation 50 AVB SHA-256: `26d2d9b7a230268d9bd3e82497aab3e8126aefcf951b2e1fcf0a4c7fc5d6df28`
- AVB salt: `4e9f2860a79b396933e64bd9d5ab4b558267c9c1777b41e4ea37b5901f64ab7e`
- AVB digest: `2f6ce96b8f597b7469f222baf822b08f4068bfc78ad49c8296fda8005df04dc3`

The new initramfs twins were byte-identical and took 2.293 seconds combined;
signed bundle twins took 0.466 seconds, and deterministic AVB generation took
1.848 seconds. Focused target, runner, claim, stable-gate, profile, and
admission tests pass. This checkpoint authorizes neither a persistent write
nor a flash.
