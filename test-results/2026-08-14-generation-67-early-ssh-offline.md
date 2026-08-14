# Generation 67 early-SSH offline checkpoint

Date: 2026-08-14

Result: **PASS offline. Generation 67 is built but unbooted.**

Generation 66 proved the exact read-only local-image path but reached strict
SSH in 328.363 seconds. Its systemd report attributed 53.485 seconds to
`dbus-broker`, 21.119 seconds to `systemd-resolved`, 42.800 seconds to the P2
ready unit, and 10.070 seconds to stock sshd. Generation 67 tests the narrow
hypothesis that strict SSH need not wait for that unrelated general userspace
transaction.

## Exact change

The v45 initramfs preserves the accepted Linux 7.1.4 Image, DTB, four deferred
UFS modules, exact userdata and 16 GiB image identity, both `ro,noload` ext4
mounts, persisted Generation 64 marker, tmpfs OverlayFS, and bounded rollback.
It changes only volatile startup ordering:

- mask stock `sshdgenkeys.service` and `sshd.service` under `/run`;
- generate exactly one volatile Ed25519 host key from `sysinit.target`;
- run strict `sshd -D` from a dedicated unit before `basic.target`;
- run the unchanged storage attestation after that SSH unit and before
  `basic.target`.

No phone contact, flash, partition operation, or persistent phone-storage
access occurred while preparing this successor.

## Clean-twin identities

- target: `persistent-root-local-image-early-ssh-v45`;
- profile: `persistent-root-ro-v1`;
- target Image: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- target DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`;
- both initramfs twins: `f647e6e32f313078b1557fdb6116750d3865c65e2d42426ebc414cbf1c9fbb64`,
  7,514,752 bytes;
- initramfs clean-twin build times: 1.200 and 1.178 seconds;
- both signed bundle manifests:
  `f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949`;
- Generation 67 AVB:
  `0bd1b6b8fddc27a5b4860036a13406f5cf4897c0ae84761a835868c0db086953`;
- AVB generation record:
  `5c6c01703f5d84dd95697c5d9e7318dedd40546fa3f530ca1220dc8193b6cdbd`;
- authority: `none`.

The accepted module hashes are unchanged: `phy-qcom-qmp-ufs.ko`
`73fef6fa...51ddb`, `ufs-qcom.ko` `b55d7641...8a26c`, `ufshcd-core.ko`
`a3e26e00...6562`, and `ufshcd-pltfrm.ko` `ef0a566c...b74d`.

## Focused verification

- storage resolution: 20 tests, 1.039 seconds;
- deterministic initramfs contract: PASS, 2.306 seconds;
- live-runner contract: 13 tests, 0.140 seconds;
- current exact profile and artifact preflight: PASS, 11.085 seconds;
- stable recovery gate: PASS, 4.705 seconds;
- exact generic claim consumer: 14 tests, 0.182 seconds;
- retention admission: 27 tests, 3.286 seconds;
- retention executor contract: 8 tests, 0.087 seconds;
- core compatibility: 39 tests, 0.479 seconds;
- core source/DTB contract: 77 tests, 11.540 seconds, one optional retained-input
  test skipped.

## Boundary and next action

Generation 67 remains unbooted and one-use. It may receive one RAM-only cycle
only after the coherent repository checkpoint and exact-head CI pass. The
cycle must measure time to accepted strict SSH, preserve the exact read-only
storage checks, capture diagnostics, reboot normally, and prove exact Alpine
fallback. It must never be flashed or retried after claim entry.
