# Generation 81 userdata-mount discriminator

Date: 2026-08-22

Status: **offline built, unbooted, and not admitted.** No phone boot, claim,
flash, or phone-storage access occurred while producing this successor.

Generation 81 preserves Generation 80's exact kernel, DTB, modules, firmware,
local image, recovery raw image, ext4 mount command, storage guards, and
rollback. It only reports which existing userdata-mount sub-boundary fails:
mount-directory creation, mount syscall, mountpoint, `/proc/mounts`, exact
block-backed mount inventory, physical read-only containment, `/rog5`
directory layout, or selector absence.

Exact outputs:

- twin initramfs size: 23,810,174 bytes;
- twin initramfs SHA-256:
  `6590cc95c9e73fedf24b3b1643d6395514943057b9e2ebb3ba6a05347905033d`;
- bundle/target: `persistent-root-power-usb-v5`;
- manifest: `5320f9cca8582ca7475f06f0a4c3e25e0b961fd1596077c832e9e622667b19bf`;
- signature: `9584c4784c02897e46e86419a6c0643393c7a518a2acc273d24cc71a42b32001`;
- generation: 81;
- AVB salt: `8d3c5b856d83108ae5e39ea5c21692a6ef26f2bfe44deb8125de2a85fd3895e9`;
- AVB digest: `c50ae6210db0433a244a6857da6d4afd0ac710b2adc02b7a72ed04c4bdb48eb7`;
- AVB SHA-256: `6856794c55777c8f473a23a5a2cee55c57c9d652122b57da048e516da2f63ce5`.

Admission remains separate after full local and exact-head CI. Generation 80
is consumed and must never be retried.
