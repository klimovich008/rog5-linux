# Generation 63 contained-write local-image offline checkpoint

Date: 2026-08-14

Status: **unbooted; no claim created; RAM-only candidate only.**

Generation 62 proved that the discovery kernel's SCSI disk hardware-read-only
state prevented a userspace `BLKROSET` write window. The successor does not
disable discovery containment. Linux source commit
`359318de534f196c1281de7195fbf5868c6f7333` adds
`CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE`, which lifts only the SCSI data-command
and SCSI disk hardware-read-only gates. UFS query writes, optional management
writes, WriteBooster, RTC updates, high-speed gear switching, auto-hibernation,
link-power transitions, and runtime PM remain contained.

The sealed initramfs selects `local-write`, verifies the retained containment
markers, locks all 116 physical block nodes read-only, opens only the exact
userdata partition and parent-disk window for the existing fixed 132-byte
marker operation, and relocks all nodes before read-only Arch SSH.

## Reproducible outputs

- source commit: `359318de534f196c1281de7195fbf5868c6f7333`;
- source tree: `8528fcd29e4ad19cf944f79c2ebb3438feee5e0b`;
- release: `7.1.4-g359318de534f`;
- clean-twin `Image`: `7c89d9a0a7ace2b0057b6cf2b535e134da596d3f3c3c3774c5b64014e32bf234`;
- clean-twin `Image.gz`: `b4c8583ef75eb7cf778fa434d14f41918bda0d7c710cb73ca16d941e56acc7a3`;
- clean-twin initramfs: `3f084169531ac644d51b3687fd454bba84a51cabdda0378a200f2c382842d6e2`;
- signed runtime manifest: `5125eddd0aeeb394eea7f24b427b04c1c001276c5b8b2e9dbf544a49c4af0646`;
- Generation 63 recovery AVB image: `159bf683100ad25aa9512a21ed2d24f91625b25597563eebe4d13bc42223b55a`;
- unchanged raw recovery: `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt: `1db67bc08d7b9685512178f3233c9ff47c50e30c2eb5f53b944a62c507625eb9`;
- AVB digest: `b70134efcd6bb79d78c09b5b362bf36a1e9d609b12d1a7c080cd827c25927c83`.

The first contained build ran from 11:42:43.326 to 11:57:33.740
(890.413 seconds). Its warm-cache peer took 109.672 seconds but exposed a
40-byte clean-build mismatch: the compat 32-bit vDSO ignored `KCFLAGS`, so its
SHA-1 build ID and the final kernel build ID depended on the output directory.
After passing the same normalized debug-path flags through `CC_COMPAT`, fresh
builds C and D took 109.223 and 112.806 seconds and matched byte-for-byte,
including the compat vDSO and all four UFS modules.

Focused checks passed:

- persistent-root kernel build and clean-twin comparison;
- read-only and local-write initramfs tests;
- stable-recovery live-gate regression;
- generic exact-record claim-consumer regression;
- persistent-root live-cycle regression;
- retention-cycle admission regression;
- exact current-profile artifact preflight.

The temporary-boot policy revokes consumed Generation 62 and admits only the
unbooted Generation 63 contained-write successor for the current storage
cycle. No phone contact, claim creation, or boot occurred during this offline
checkpoint.
