# Current stage-75 v2 disposable twin-build validation

Date: 2026-08-08

Repository checkpoint under test:
`afc0e9e94bbc6edea1aa0c2ace17b2b5d00cef83`.

## Purpose

Validate the active, single-attempt `headless-netroot-early-diag-v2`
candidate through the complete credential-free recovery composition path after
the diagnostic NFS/UDC corrections. This is hardware-free validation only. It
does not issue a generation, add a policy row, use a production credential, or
authorize a boot.

## Result

The complete disposable-key build passed in 2,332.019 seconds. It produced two
clean ASUS 5.4 wrapper builds and proved their kernel, raw boot image, and
unsigned AVB test image byte-identical. The builder destroyed its temporary
Ed25519 private key and returned `authority=none`.

Exact identities:

- active target Image: `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`;
- accepted DTB: `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`;
- single-attempt target initramfs: `71537ca0cfdfcf8f7dbf26cc2eb6585bac025bea08526a7e22d62df60fa0c58e`;
- signed bundle manifest: `2ca802ee37d444dca71629064ccadfb81c3e8db2b83a6a4e040c1d5d5469cbe7`;
- disposable recovery initramfs: `756210bd0901322a636125ea314289a8d2fea5230b10ac325a548d92fc793066`;
- wrapper kernel: `2110f1c4a12c1e964d77c7e247e37b572667279986549525360a8d21eddc593d`;
- raw recovery image: `925917037d56a414421c52ef68ce0079f2eb5d99a645123d52fe512b5dd42673`;
- unsigned AVB test image: `a28af4cd899e5d8fbd2870a8833b761e54c3b1f904d80640889acca5963bab3a`.

The generated validation tree occupied 10,094,547,047 bytes. Its identities
were recorded above, then the tree was removed to avoid retaining duplicate
build products. No private key, image, or candidate authority was retained.

## Timing context

The complete repository CI at the preceding implementation checkpoint passed
in 634.242 seconds (`user=181.660`, `sys=182.374`), versus 657.683 seconds for
the prior exact-head checkpoint. The focused stale-origin regression failed on
the old behavior in 0.828 seconds and passed after the fix in 1.140 seconds.
The 38m52s clean twin build shows that release wrapper compilation, not phone
interaction, is currently the dominant unattended validation cost. Incremental
builds remain appropriate for development, while clean twins remain mandatory
for issuance.

No phone interface, phone storage, production signing key, persistent install,
flash, wipe, erase, slot operation, or temporary boot was used.
