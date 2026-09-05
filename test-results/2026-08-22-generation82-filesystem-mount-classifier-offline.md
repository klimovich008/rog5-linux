# Generation 82 filesystem/mount classifier

Date: 2026-08-22

Status: **offline built, unbooted, and not admitted.** No phone boot, claim,
flash, or phone-storage access occurred while producing this successor.

Generation 82 preserves Generation 81's exact kernel, DTB, modules, firmware,
local image, recovery raw image, ext4 mount operation, and rollback. Before the
same read-only `ro,noload` mount it performs bounded, read-only classification:

- BusyBox `blkid` type;
- `dumpe2fs -h` feature flags for casefold, encrypt, verity, quota, project,
  needs-recovery, and orphan-file;
- mount exit status;
- bounded ext4/VFS categories including casefold/Unicode, unsupported
  incompat features, non-ext4, suppressed recovery, and generic `EINVAL`.

The combined result remains below the existing 128-character exact stage
detail bound. No raw filesystem data is exported.

Exact outputs:

- twin initramfs size: 23,809,694 bytes;
- twin initramfs SHA-256:
  `1c59a8c7e5c07b643173dd94dabf15190d6ddf7b6164381d7bb43f5dbf208b1f`;
- bundle/target: `persistent-root-power-usb-v6`;
- manifest: `b83d5bacb8b22a7125a33c087b10403cc5e1e9cf35dc5e8ee8d1e48e185e935a`;
- signature: `799d5e64c69b640780d23ef058add08806368196e52f8e05688ad1afedf42eb7`;
- generation: 82;
- AVB salt: `fede27daadd9999ccb1b407a340a305f052c23c03f692de4ee4a4b49292a5637`;
- AVB digest: `5a68ee489f10f25bb18195e771477523e1dc0423f03f212eae04b921b0eac408`;
- AVB SHA-256: `e040c38cbbd311310899f2b4e55cb4bbfbc8c62c12f3c040d06f58469802fb60`.

Admission remains separate after full local and exact-head CI. Generation 81
is consumed and must never be retried.
