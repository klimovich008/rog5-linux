# Generation 61 write-window discriminator checkpoint

Date: 2026-08-14

Status: **offline candidate checkpoint; unbooted and one-use.**

Starting repository SHA:
`204efb12ac37d72a751525f0c9fd677f9002a4b1`.

Generation 60 proved that the bounded write path fails before the outer
userdata RW mount, but its `image-write-window` terminal record still grouped
five operations. Generation 61 preserves the exact Image, DTB, two-node write
surface, fixed 132-byte marker, all-116-node relock, read-only Arch runtime,
key-only SSH, and rollback. It adds fixed terminal boundaries for:

- userdata unmount;
- exact read-only precheck;
- userdata-partition `BLKROSET`;
- parent-disk `BLKROSET`;
- blockdev and sysfs effective-state verification;
- exact writable-node count;
- outer userdata RW mount;
- loop and inner image RW mounts;
- marker creation; and
- storage relock.

Fail-first storage and host-runner tests completed in approximately 1 and 0
seconds and rejected the missing sub-boundaries before implementation. After
the change, 18 storage tests passed in 1.079 seconds, 13 runner tests passed in
0.232 seconds, and the deterministic initramfs contract passed in 3 seconds.

Clean initramfs twins completed in 1.144 and 1.152 seconds and are
byte-identical at SHA-256
`9b0bb0929ff05a828209ea9f3ccf2ff95c8f7bb595c042a76b24fecec84bbdcd`.
Production-key signed bundle twins completed in 0.185 and 0.205 seconds and
are byte-identical:

- bundle: `persistent-root-local-image-write-window-v39`;
- manifest: `35cdc621f44873e42b1b8f2619e383d1a6ed2236f49790fdf36c7435e7883824`;
- signature: `c22039ea4c6ce51ba2d1663e309cb6664ccd0552835e7098b6e21692e06e69cc`;
- unchanged Image: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 61 AVB issuance from the canonical generation-zero wrapper took
1.836 seconds. The raw wrapper remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the generation-tagged AVB image is
`8215928fc9c68414e90f50401238a4539b3f0f101c7834f3fce242b71ee3606d`,
with salt
`0f4c13f39636781d936c4b3b832c62294dfce2f84bea0f3311655c9798bb6500`,
digest
`47661db4eba88e4f49336156b7b08098d6d7e4a5c50c0d1a0b52d26f2e9a74f1`,
and generation-record SHA-256
`d66774da20ae34e0b645b326d0b204ecabc35c002355b29f0dfe04675b0e51e5`.

Focused storage, host-runner, exact-claim, current-profile/artifact,
stable-gate, retention admission, executor-contract/runtime, compatibility,
and core-source/DTB regressions pass. No Generation 61 claim has been created
and no Generation 61 phone boot has occurred at this checkpoint.
Final `scripts/host/test-repository-linux.sh ci` passed in 476.367 seconds.
