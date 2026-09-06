# Generation 80 bracketed Type-C role successor

Date: 2026-08-22

Status: **offline built, unbooted, and not admitted.** No phone boot, claim,
flash, or phone-storage access occurred while producing this successor.

The only semantic correction accepts the exact mainline role-switch forms
observed in V26: `host [device]` and `source [sink]`. Bare fixed-role values
`device` and `sink` remain accepted. Inactive selections (`[host] device`,
`[source] sink`) and malformed or trailing values are rejected by focused
fixtures.

Generation 80 reuses the exact Generation 79 kernel, DTB, four UFS modules,
fifteen charging modules, twenty-nine firmware files, local Arch image,
stable recovery raw image, and rollback. No kernel or ASUS wrapper compilation
ran.

Exact outputs:

- twin initramfs size: 23,808,853 bytes;
- twin initramfs SHA-256:
  `7a69e97606d2d4422ba0ead12f5225802cd27d3b036914c0041b7c9da1973c25`;
- bundle/target: `persistent-root-power-usb-v4`;
- manifest: `2240afeecc90e45e4cf51e94365473a8fbe269731cebc7d1dcba86b7bfd84bf2`;
- signature: `34c262e151cf224fc8ce3558002ac0b629f0f2bc028eb2490b2af5e1774f959b`;
- generation: 80;
- AVB salt: `84f9bb7e6320853c262280df13b0dd7c76e643ced6d6157ee6bc59d8c92c4871`;
- AVB digest: `08e51f7e707d373160f1ec176f49ba30c10bf03a458733e8ffb267792cc9a5c4`;
- AVB SHA-256: `f948a480806805b7726e3de5fd2f1def3b457a82219d0e8fa8a3ad7ca94d0ae9`.

Admission remains a separate transition after full local and exact-head CI.
Generation 79 remains consumed and must never be retried.
