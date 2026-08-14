# Generation 60 bounded-write discriminator checkpoint

Date: 2026-08-14

Status: **offline candidate checkpoint; unbooted and one-use.**

Starting repository SHA:
`497b06229bd8d8bbf1857e893307491c9680d5ea`.

Generation 59 proved UFS and exact read-only image resolution but returned
only `image-write: FAIL`. The v38 initramfs preserves the exact kernel, DTB,
UFS identities, two-node write window, one fixed 132-byte marker, all-116-node
relock, read-only Arch runtime, key-only SSH, and rollback. It changes only
the terminal failure record. A failure is now classified as exactly one of:

- `image-write-window`;
- `userdata-rw`;
- `image-loop-rw`;
- `image-fs-rw`;
- `image-probe`; or
- `storage-relock`.

Fail-first tests completed in 0.893 and 0.131 seconds and failed because the
target classifier and host allow-list did not exist. After implementation,
18 storage tests passed in 0.873 seconds, 13 runner tests passed in 0.133
seconds, and the deterministic initramfs contract passed in 2.847 seconds.

Clean initramfs twins completed in 1.147 and 1.140 seconds and are
byte-identical:

- SHA-256:
  `2daf7e5ddd3226a3662826156b9a8a25c444e2cd7be3bc09bdcb4c5d21565e6a`.

Production-key signed bundle twins completed in 0.262 and 0.265 seconds and
are byte-identical:

- bundle: `persistent-root-local-image-write-diag-v38`;
- manifest SHA-256:
  `a12844274c1bc707cee9ae1f3e464e73ffed57adcd477af8f21fbb678173c444`;
- signature SHA-256:
  `02c67550384212bc19f0ac5a793817bb4168697b213c802fa89235cb4ac35a90`;
- unchanged Image SHA-256:
  `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB SHA-256:
  `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 60 AVB issuance from the canonical generation-zero wrapper took
1.991 seconds. The raw wrapper remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the generation-tagged AVB image is
`b4cbabb688f513db7939670fa1f6068065b6e6130c3418350c78421ee64ff18e`,
with salt
`51a7c37619ca333a55ac8d79195dc356a981820f476c1a0d8c2348494d598bad`,
digest
`bc5b43c21d392b7ca29934915358fd1e0c4b1daf7c1f486570ae50ca442b2d2b`,
and generation-record SHA-256
`391a94a0fd4009edfd6f5165f88a8337db2a6d724a94dfa542aa22d278dfbad5`.

Focused exact-claim, current-profile/artifact, stable-gate, and retention
admission suites all pass. The first full repository CI run reached a stale
retention executor identity after 246.602 seconds; that exact size/hash pin was
updated for the already-reviewed Generation 60 claim consumer and live gate.
The focused executor and admission regressions then passed in 0.088 and 3.280
seconds. Final `scripts/host/test-repository-linux.sh ci` passed in 459 seconds.
No Generation 60 claim was created and no phone boot occurred while building
this checkpoint.
