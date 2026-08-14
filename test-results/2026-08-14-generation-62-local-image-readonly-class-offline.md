# Generation 62 effective-readonly discriminator checkpoint

Date: 2026-08-14

Status: **offline candidate checkpoint; unbooted and one-use.**

Starting repository SHA:
`d6d38a3919be79e7e692de83a348bc6906378a91`.

Generation 61 proved that both reviewed `BLKROSET` calls return success but
effective `blockdev --getro` verification does not match the intended
two-node write window. Generation 62 preserves the exact Image, DTB, UFS
modules, two-node write surface, fixed 132-byte marker, all-116-node relock,
read-only Arch runtime, key-only SSH, and rollback. It changes no operation
and adds only eight fixed terminal classes: selected or unrelated, disk or
partition, and blockdev or sysfs.

The fail-first storage test rejected the old coarse classification in 0.922
seconds. After the correction, 19 storage tests passed in 0.912 seconds and
13 host-runner tests passed in 0.154 seconds.

Clean initramfs twins completed in 1.154 and 1.141 seconds and are identical
at SHA-256
`4a19c8bc88f45d4c638d6bbff673d2cc28490883dc43989b8609e1156616ea4c`.
Production-key signed bundle twins completed in 0.202 and 0.188 seconds and
are byte-identical:

- bundle: `persistent-root-local-image-write-roclass-v40`;
- manifest: `c284330d2e37cda85d125c098c6acece877ae5e5b69be66edcae326e57ee0f4b`;
- signature: `914baa346956c3849d25a6e571708ac44addeca0eccec59b9316665cea684310`;
- unchanged Image: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 62 issuance from the canonical generation-zero wrapper took 1.850
seconds. The raw wrapper remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the generation-tagged AVB image is
`1e19474e2536305f4845346d800e054959408a8ecd5e7dd0ba4cb43272a96ef8`,
with salt
`065c8bbf741c20313eb78464e922370fd1a2da1a6063925f8f1f3cfc4af8e4df`,
digest
`57d19cf69690e2e2ded485408ae7349b2d3c3aa09a091cd2569e9f3f59e29144`,
and generation-record SHA-256
`7bebeb697cd04caa9336648fb2811cbf301e24521f38ff6bb5db7c2ae0cb5398`.

Full local repository CI passed in 461.033 seconds. The candidate remains
authority-free until the exact-head publication checkpoint passes and the
one-use claim is created immediately before the physical cycle. No Generation
62 claim has been created and no Generation 62 phone boot has occurred at
this checkpoint.
