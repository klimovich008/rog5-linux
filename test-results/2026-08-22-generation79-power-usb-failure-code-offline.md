# Generation 79 power/USB failure-code successor

Date: 2026-08-22

Status: **offline built, unbooted, and not admitted.** No phone boot, claim,
flash, or phone-storage access occurred while producing this checkpoint.

Primary question for one future RAM-only cycle: which exact boundary inside
`/sbin/rog5-load-persistent-power-usb` failed during Generation 78?

The successor reuses exact Generation 78 bytes for:

- Linux Image: `a4648dd425616adff2dfb07590be4f85d17d5305e1f72830eb85e668490046d6`;
- board DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- stable recovery raw image: `09c497ef23718cf74c94f3dc11085575b46982232d9e690df48c52637e5d9616`;
- four deferred UFS modules, fifteen power/USB modules, twenty-nine firmware
  files, local Arch image, stock slot-A fallback, and rollback behavior.

Two clean target initramfs builds took 3.183 and 3.126 seconds and reproduced:

- size: 23,809,223 bytes;
- SHA-256: `9cbfeb5dce268d611b5f05d1715c91d2d2470c087636ceeeccc15cd2d0723c9c`.

Comparing all 174 regular archive files with Generation 78 found exactly two
changed paths: `/init` and `/sbin/rog5-load-persistent-power-usb`. The new
loader emits one validated reason such as
`power-usb-module-pdr-interface-load`; malformed output becomes
`power-usb-invalid-failure-record`. The existing stage channel and two-second
fail-closed rollback are unchanged.

The twin signed bundle identity is:

- bundle/target: `persistent-root-power-usb-v3`;
- manifest: `d0a1e7b2d9a2fce6d934fc560af466c476f66c1b5ee700dd6efdc6134b6e68eb`;
- signature: `4a188ade428cc49f03a19f092082767a00fa3774ec841b6c7397a9f060e36e4c`;
- trust root: `cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054`.

The stable recovery transport required no rebuild. A fresh deterministic AVB
generation over the unchanged raw image produced:

- generation: 79;
- salt: `f4facf8b1bbb988669bc291d3e0bf05e1bb7d0f1d3efae094d0f35261d586fa4`;
- digest: `02457303674d04b449cce7cdda94148b78160e1e1ecd68ece31ba072b96cce00`;
- AVB SHA-256: `2e49097855eaee747d5935e2d1a6dfe28a42a99396bcafc670db47e3bf388623`.

Admission remains a separate transition after focused, full local, and exact-
head CI pass. Generation 78 remains consumed and must never be retried.
