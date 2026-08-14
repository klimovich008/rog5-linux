# Generation 66 UFS-module restoration checkpoint

Date: 2026-08-14

Status: **unbooted; no claim created; RAM-only candidate only.**

Generation 66 fixes the concrete Generation 65 packaging defect without
changing UFS probing, storage policy, mount options, rollback, Image, or DTB.
The initramfs restores exactly the four deferred modules accepted in v36 and
the production builder now refuses a module-required build if any are absent.
Stage protocol v2 also carries one bounded `detail` field so a later UFS
failure preserves module status and compact physical/host/WLUN/error counts.

## Reproducible outputs

- target: `persistent-root-local-image-ufs-detail-v44`;
- release: `7.1.4-gae717d919f87`;
- unchanged read-only `Image`: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`;
- twin initramfs: `01c87e43d949d2d0eae7a459ca9304ab28409beb31908bbf411c66ff4799f8fe`;
- signed runtime manifest: `07e7f72c7c88ea4c081d77e3e561c36278ef0a0273dee6b831ca691f6518ee2e`;
- manifest signature: `1cad4fffd08cf01da192360322e09066d4f6c46893b95cf9edae907b6c575150`;
- Generation 66 recovery AVB image: `d4d95e010810e09a209f0cde8f82e3d36e28c20dfa1b5aa899b5873c1ee36412`;
- unchanged raw recovery: `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt: `f537b31e935551de1f80f047f6d35262c2c925bc02533b5e005d965ad6e8ce4d`;
- AVB digest: `b1ceb0949211677269294b9da6f710bbe331e9aa903b7c52b61059af18d4ea3e`;
- generation record: `e9d3d2add267da9145e8efc713bc68e3fe2ffa2380274d62575c6dd3a19eb70a`.

The two initramfs builds completed in 1.174 and 1.188 seconds and matched
byte-for-byte. The focused runner (0.164 seconds), exact-claim consumer (0.202
seconds), retention admission (3.302 seconds), stable gate (4.726 seconds),
and current-profile/module inventory (10.985 seconds) checks pass. The module
inventory test extracts the sealed runtime initramfs and pins the exact four
accepted module hashes. Full `scripts/host/test-repository-linux.sh ci` passed
in 466.640 seconds. No phone contact, claim creation, installation, or boot
occurred at this checkpoint.
