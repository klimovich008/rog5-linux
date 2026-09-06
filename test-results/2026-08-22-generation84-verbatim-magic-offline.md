# Generation 84 verbatim direct-magic classifier

Date: 2026-08-22

Status: **offline built, unbooted, and not admitted.** No phone boot, claim,
flash, or phone-storage access occurred while producing this successor.

Generation 84 preserves Generation 83's exact kernel, DTB, modules, firmware,
local image, recovery raw image, mount operation, and rollback. The only
semantic change is `od -v`, which disables sealed BusyBox 1.37 duplicate-line
compression. Host execution of the exact embedded BusyBox proved default `od`
emits `*` while `-v` emits the exact 128-character hex record.

Exact outputs:

- twin initramfs size: 23,810,495 bytes;
- twin initramfs SHA-256:
  `4326c052b568a04143befc43c84b177487ccb5b13a1762b22ed178fb1f32ba97`;
- bundle/target: `persistent-root-power-usb-v8`;
- manifest: `c70ed13367192b26225aa3408bf8cdf4dd3a91da1d3a0c0f5fba59c81be36289`;
- signature: `a68d88d8127298aa060d39639f7052758a308a9b29a183dab7d69bdff6770920`;
- generation: 84;
- AVB salt: `7997d52541c01129c6914731b9632b9b22c8a5c0bd310a483ef1fc101a3a507c`;
- AVB digest: `5f0f0e1cc321c4c7409272b10a916ea5c0da458bac75db47360e0927128db50c`;
- AVB SHA-256: `88075dba4a8564fa21d73c69d696b64813dc024389a5d097be345f7cd9f302bb`.

Admission remains separate after full local and exact-head CI. Generation 83
is consumed and must never be retried.
