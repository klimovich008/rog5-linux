# Generation 83 direct filesystem-magic classifier

Date: 2026-08-22

Status: **offline built, unbooted, and not admitted.** No phone boot, claim,
flash, or phone-storage access occurred while producing this successor.

Generation 83 preserves Generation 82's exact kernel, DTB, modules, firmware,
local image, recovery raw image, mount operation, and rollback. It adds a
64-byte read at offset 1024 and accepts only exact ext4 (`0xef53`) or F2FS
(`0xf2f52010`) magic at their defined positions. `blkid` is retained only as an
independent agreement signal. Exact ext4 magic always triggers bounded
`dumpe2fs -h` feature classification.

Fixtures cover real-output-shaped ext4/F2FS blkid records, labels containing
type lookalikes, unquoted/suffixed values, missing types, valid magic, malformed
length, non-hex bytes, and misplaced magic.

Exact outputs:

- twin initramfs size: 23,810,499 bytes;
- twin initramfs SHA-256:
  `aad0c9fd71f852ad378ac2a21864652bee35cc59b26ae7781bc2f4204b419647`;
- bundle/target: `persistent-root-power-usb-v7`;
- manifest: `ed43083b35d7f1e4d3c7aa6aa8dacb4ec4e22a2d1e57cd818c4efa20f78080cd`;
- signature: `0e596a9d77445a08c2b3872afb65ace91e6bd0b3c042d6378fa59ada15d88aa7`;
- generation: 83;
- AVB salt: `c77ba861db5befabb583be8234e8af887f2b24ebd357f0badfab73bb92126666`;
- AVB digest: `f5a2172714203144a2d93fb8841fa6d26df764c9e5b446c6be9a43736eb982f0`;
- AVB SHA-256: `b1e69cbdb2a379d763a65c2841182b2e3f163ad7648da5fc470b75bba4092517`.

Admission remains separate after full local and exact-head CI. Generation 82
is consumed and must never be retried.
