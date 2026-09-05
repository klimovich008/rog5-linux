# Generation 58 Ed25519-only local-image checkpoint

Date: 2026-08-14

Status: **offline checkpoint passed; Generation 58 is unbooted and has one
RAM-only use available.**

The later one-use hardware result is recorded separately in the
[Generation 58 live report](2026-08-14-generation-58-ed25519-only-live.md).

Generation 57 proved that the local Arch image, read-only UFS, tmpfs
OverlayFS, systemd, NCM, and strict key-only SSH work together, but its
critical-path evidence showed that stock `sshdgenkeys.service` spent 38.212
seconds generating RSA, ECDSA, and Ed25519 host keys even though the exact
sshd configuration permits only the Ed25519 key. Generation 58 removes that
measured waste without modifying the sealed image or either physical ext4
filesystem.

The v36 initramfs now verifies the exact sealed `/usr/bin/ssh-keygen`, stock
`sshdgenkeys.service`, Ed25519-only sshd setting, and absence of all six host
key files. Before `switch_root`, it then creates only in the tmpfs-backed
systemd state:

- a mask for the stock all-key generator;
- an exact oneshot that generates one volatile Ed25519 host key; and
- an exact sshd dependency on that oneshot.

The defect was fixed fail-first. The new hostile regression rejected the old
initramfs because it lacked the replacement service, then proved that existing
or symlinked keygen masks, service files, sshd drop-ins, or host keys all fail
closed. No private host key is present in the repository, bundle, or local
image.

Clean initramfs twins completed in 1.169 and 1.158 seconds and are
byte-identical:

- size: 7,511,699 bytes;
- SHA-256:
  `9f97b88ab6be2155b842ddeb65ce2d87fd5a7f091853251aa2a7af58d516dd5a`.

Production-key signed bundle twins completed in 0.255 and 0.307 seconds and
are byte-identical:

- bundle: `persistent-root-local-image-ed25519-v36`;
- manifest SHA-256:
  `cc41176df74def7a8953dfcd8621e1d1ad2457eb98a7822a0d40ce50ab8c2be0`;
- signature SHA-256:
  `59fb68fd7983152fe9b87592747785dc971a9dff46f5c26829dff431439be5b3`;
- unchanged Image SHA-256:
  `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB SHA-256:
  `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 58 AVB derivation completed in 2.069 seconds. An initial invocation
against Generation 57's already salted wrapper failed closed before producing
an output. The successful invocation used the exact canonical generation-zero
parent. The raw recovery remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the fresh wrapper is
`38bc065959a88f4f51f13cc3443a8bd02dda61d8813150821d561239bd02a4f0`,
with salt
`c3f2b88d54e3a4260d28e69d7796643cc50e3df8b3c37c55690ac92acb5b553d`,
digest
`22328e06887d643547fa04153d868eb1ec78428210d4b637b6066c8a956d0de7`,
and generation-record SHA-256
`1fa76a89ca2f0952be3a401ded4bc53bf0044c42b94577f4a8c74b7675d9390a`.

Focused verification passed:

- storage-resolution and hostile volatile-state suite: 16 tests in 0.853 s;
- deterministic initramfs contract: 23.140 s;
- generic exact-record consumer: 14 tests in 0.214 s;
- retention admission: 27 tests in 3.344 s;
- persistent live-cycle runner: 13 tests in 0.131 s;
- exact current artifact/profile preflight: 10.631 s;
- core compatibility oracle: 39 tests in 0.463 s;
- stable recovery gate: 4.550 s;
- recovery boot policy: 0.486 s; and
- current production, core, and observer profiles: 13.103 s, 10.800 s, and
  8.955 s.

The checkpoint started from
`50c9a50f8b7e181bdf3e063494d74efe1685f835`. Generation 57 remains consumed
and permanently non-retryable. Generation 58 has not contacted the phone,
entered its claim, or used its single boot authority at this checkpoint.
