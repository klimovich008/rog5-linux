# Generation 55 retained-loader local-image checkpoint

Date: 2026-08-14

Status: **offline checks pass; one Generation 55 RAM-only admission is
prepared. The successor has not been booted and must never be flashed.**

Generation 55 changes only the post-handoff attestor proven defective by the
[Generation 54 live cycle](2026-08-14-generation-54-fast-attestation-live.md).
It invokes the retained musl BusyBox through the retained musl loader. The
builder now pins both files and verifies BusyBox's exact ELF interpreter and
`libc.musl-aarch64.so.1` dependency. A fail-first regression prevents direct
post-`switch_root` BusyBox execution from returning.

`qemu-aarch64-static` executed both `true` and the `blockdev` applet through
the retained loader successfully. Clean initramfs twins completed in 1.192 and
1.208 seconds and are byte-identical:

- size: 7,510,399 bytes;
- SHA-256: `6d183c056484b8279a8d0aef1ebff1affa2a7be1b3d2e15ddad61c8794a59ab3`.

Production-key signed twins completed in 0.211 and 0.239 seconds and are
byte-identical. The native verifier accepted both exact plans:

- bundle: `persistent-root-local-image-loader-v34`;
- manifest SHA-256:
  `8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79`;
- signature SHA-256:
  `b634a2609c81d7fb2615aaacdaccabf19e6232603d4d03acbab362e6afdd61b2`;
- unchanged Image SHA-256:
  `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB SHA-256:
  `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 55 AVB derivation took 1.891 seconds. The raw recovery remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the generated wrapper is
`c3cd5d584c959b8d78eab54e4b1547a6c24e06677d8c9a827275bc7cfc5b06da`,
with salt
`9f018a2ccd39be1535084cb01f42c6036602c33f1ea392e9257b6f0708d021d7`,
digest
`eb411a0b837ac84193267a18ddcc92c3798a1e945d6c9e2d30217e1e2b332b81`,
and generation-record SHA-256
`2cfd74db7da6f7aa9f782489ad87a83d04565186b1ddb817d24b0dcce3d674d9`.

Focused tests pass for the 14 storage-resolution cases, 12 live-runner cases,
14 generic claim-consumer cases, 27 retention-admission cases, the current
persistent-root artifact/profile gate, and the stable recovery gate. Full local
CI passed in 458.655 seconds. Exact-head GitHub CI remains the publication
checkpoint before a live cycle.
