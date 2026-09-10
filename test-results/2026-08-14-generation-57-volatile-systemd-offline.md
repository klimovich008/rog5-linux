# Generation 57 volatile-systemd local-image checkpoint

Date: 2026-08-14

Status: **offline checkpoint passed; the sole live cycle is now consumed and
must never be retried or flashed.**

Generation 57 addresses the measured Generation 56 userspace critical path
without changing the accepted kernel, DTB, UFS implementation, local image,
physical mount policy, attestation, or rollback behavior. The v35 initramfs:

- verifies the exact 20,207-byte sealed `/etc/ld.so.cache` before use;
- creates `/etc/.updated` and `/var/.updated` through the tmpfs OverlayFS
  with `/usr`'s exact timestamp;
- verifies the markers exist in the volatile upper and remain absent from
  the read-only lower; and
- masks `systemd-vconsole-setup.service` only in volatile `/run` because
  this target is headless.

The regression failed before the helper existed. Sixteen storage-resolution
tests now cover the exact happy path plus a mutated or symlinked linker cache
and pre-existing lower/upper markers. Existing deterministic initramfs and
rollback tests pass.

Focused verification also passed:

- core compatibility oracle: 39 tests in 0.475 seconds;
- core source/DT contract: 77 tests, one optional retained-source skip, in
  11.497 seconds;
- retention executor contract: 8 tests in 0.089 seconds; and
- retention admission: 27 tests in 3.269 seconds.

The repository checkpoint initially exposed two expected identity cascades:
the artifact manifest changed, then the compatibility profile changed. A later
checkpoint exposed stale exact size/hash records for the claim consumer and
stable recovery gate. Each pin now names the current reviewed bytes; the
focused suites above prove the corrected chain.

Clean initramfs twins completed in 1.135 and 1.158 seconds and are
byte-identical:

- size: 7,509,342 bytes;
- SHA-256:
  `d32482af5c83964e38b3997750a3123ed514baf1976b73968fa204dc7d192ca7`.

Production-key signed bundle twins completed in 0.381 and 0.750 seconds and
are byte-identical:

- bundle: `persistent-root-local-image-volatile-v35`;
- manifest SHA-256:
  `1def5f276c7d07668ccb90a9ca3ed966660e0af359e49e2f847371b058291e30`;
- signature SHA-256:
  `aa434a25776b20a67658a0172e2e4f6ed47265a38559bd29f8caa7ca9cd666a5`;
- unchanged Image SHA-256:
  `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB SHA-256:
  `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 57 AVB derivation completed in 2.107 seconds. The raw recovery
remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the fresh wrapper is
`425346d1fa88586f20b61d333cbff28c6435e6b099e414d2fe2cf58dce6cc04f`,
with salt
`4c2e1b77db4f30ddf17689f6871ee0abebd51544c3e47271ba2bba33c581e690`,
digest
`01b82565207da961c4a4bf84fe472768e413562093d055e0bff2a72dc99f2508`,
and generation-record SHA-256
`2872690a6163d6842249a778b5bbfc3c1257edfa30133980fdf8cf490a363e63`.

Generation 56 is revoked and cannot be consumed again. Generation 57's sole
RAM-only cycle subsequently passed in 305.928 seconds and is now permanently
revoked. See the [live result](2026-08-14-generation-57-volatile-systemd-live.md).
