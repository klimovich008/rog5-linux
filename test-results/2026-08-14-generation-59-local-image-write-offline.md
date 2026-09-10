# Generation 59 bounded local-image write checkpoint

Date: 2026-08-14

Status: **offline checkpoint passed; Generation 59 is unbooted and its one
RAM-only use remains available.**

## Defect and bounded correction

Generations 53–58 proved that mainline Linux can resolve all seven UFS LUNs,
mount the existing `userdata` filesystem and 16 GiB Arch image `ro,noload`,
start systemd with a tmpfs OverlayFS upper, reach strict key-only SSH, and
return to exact Alpine fallback. They did not prove that mainline can perform
a controlled persistent write. Generation 59 adds the smallest discriminating
experiment: one fixed marker inside the existing image.

The v37 initramfs starts with all 116 physical UFS disk/partition nodes
read-only. After dynamically resolving exact `userdata`, it clears read-only
only on that partition and its parent LUN, verifies that these are the only two
effective writable nodes, mounts `userdata` and the exact image read-write,
and creates one 132-byte mode-0444 marker containing the image UUID and target
boot ID. It refuses an existing directory, file, or symlink and therefore
cannot repeat the mutation. It then syncs, unmounts both ext4 filesystems,
detaches the loop, relocks the parent before the partition, and proves all 116
nodes read-only before resuming the established two-`ro,noload` Arch runtime.

The Linux 7.1.4 block-layer source was checked at exact source commit
`cfd385a1c754684dd28b63a4559e04baa5e902b1`: `bdev_read_only()` combines the
per-block-device read-only bit with the whole-disk bit. Clearing the parent
last therefore preserves a closed window until exact `userdata` is ready,
while sibling partition read-only bits remain effective. Closing the parent
first immediately blocks the LUN again.

The correction is fail-first. Before implementation, the new storage suite
failed because the exact write/verification functions were absent, and the
host stage suite rejected `image-write`; the two failures completed in 0.210
seconds. Hostile cases now cover a repeated marker, symlinked marker ancestry,
an inexact write surface, wrong image backing path, size, UUID, label or
filesystem type, incomplete relock, missing marker attestation, and an
unrecognized live stage.

## Artifact identities and timing

The final clean initramfs twins completed in 1.146 and 1.144 seconds and are
byte-identical:

- SHA-256:
  `56bf0b9e9a34ae1c32a542ed15244bafe0d6b9a96a9e8e5621dd30a57f19ea21`.

Production-key signed bundle twins completed in 0.262 and 0.270 seconds and
are byte-identical:

- bundle: `persistent-root-local-image-write-v37`;
- manifest SHA-256:
  `5033263fbdb28f795fe92b74a850d3e33119f2d440f9e3999b3ebff3804ef259`;
- signature SHA-256:
  `98ee112a7c30eeb52b2b81dc485a3414dc415ef4c7f43ceda8c1506c08edeecc`;
- unchanged Image SHA-256:
  `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB SHA-256:
  `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`.

Generation 59 AVB derivation from the canonical generation-zero parent took
1.875 seconds. The raw recovery remains
`5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
the fresh generation-59 wrapper is
`b349d27e41ba2ad1bda9e06e681e3eb8faae9d1f8b32a13943476e63eb997578`,
with salt
`9189a8941f35c91242b0ca4a3544792a078916c854ca0b33506d7410a91df371`,
digest
`1b0894de77d910e3d9d9c4658c68ea71399993b8c447ca1a5a95fd35ddd7505f`,
and generation-record SHA-256
`803f15dfbb71fb93182ce0b6e565e63c7471ee9bb6f30c16b5eaabcba2f2568a`.

## Safety boundary

Generation 59 does not flash, erase, format, resize, repartition, change a
slot, or write any raw partition payload. Normal ext4 data/journal changes are
expected in the image and in its containing `userdata` filesystem. The prior
full-tree seal remains provenance for the original materialization but, after
this marker, is not represented as a seal of the complete current image.
Exact boot-critical files and the new marker remain independently verified.

## Verification

Focused verification passed:

- storage resolution, one-shot marker, exact write-window and hostile cases:
  18 tests in 1.01 seconds;
- persistent live-cycle parsing and cleanup: 13 tests in 0.17 seconds;
- deterministic initramfs rebuild contract: 2.89 seconds;
- generic exact-record consumer: 14 tests in 0.27 seconds;
- retention admission: 27 tests in 3.25 seconds;
- retained executor contract: eight tests in 0.10 seconds;
- current Generation 59 artifact/profile preflight: 11.12 seconds;
- stable recovery gate: 4.69 seconds;
- recovery boot policy: 0.53 seconds;
- current production, core and observer profiles: 15.67, 13.52 and 9.84
  seconds; and
- core compatibility oracle: 39 tests in 0.65 seconds.

The first full repository run exposed stale exact identities after the policy
gained its third allow row: the retention admission profile still pinned the
previous executor digest and two-row policy set. It failed after 358.52
seconds. Those publication dependencies were updated, their focused 27-test
suite passed, and the complete `scripts/host/test-repository-linux.sh ci`
checkpoint then passed in 473.81 seconds. This was a host-policy identity
failure; no phone claim, candidate entry, or storage write occurred.

The checkpoint started at repository SHA
`18c863737502c6ee0ae3aa184672143bf107bb83`. Generation 58 remains consumed
and permanently non-retryable. Generation 59 has not entered its claim or
executed on the phone. Host USB enumeration showed that the connected phone
was in the known-good Alpine fallback rather than fastboot while the offline
tests ran.
