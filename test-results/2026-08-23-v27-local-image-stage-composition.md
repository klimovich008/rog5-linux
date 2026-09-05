# V27 staging composition rejection

Date: 2026-08-23

Result: **R2, revoked before claim or phone contact.**

V27 reused the V20 network-root target to obtain NFS and key-only SSH. That
composition intentionally disables UFS in its DTB and `network-root-init`
rejects every physical block device before USB handoff. It therefore cannot
access the newly formatted userdata filesystem and cannot answer the cycle's
primary local-image staging question. Exact-head, merge, and QEMU CI passed,
but those tests did not assert the new storage requirement.

The regression test `scripts/device/test-local-image-stage-initramfs.sh` now
requires the live-proven `7.1.4-gae717d919f87` Image, UFS-capable power/USB
DTB, four deferred UFS modules, strict `a600000.usb` gadget identity, and the
absence of the network-root physical-storage exclusion.

The corrected target-only successor receives one exact 649,960,943-byte gzip
file in RAM, opens a write window only for the userdata disk and partition,
publishes one 17,179,869,184-byte image beneath `rog5/images`, unmounts,
relocks every block node, and requests bootloader restart. Its pinned hashes
are:

- compressed transfer: `41f75ab6c9c74e3f511fcac4a85b1c4da93695bc56bf85ab954a42f70d83ba88`;
- local image: `533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153`;
- target initramfs: `968e2ce5573f539bd329827babe184627bc26ae0bcd94386cc7d04a7edba4fda`.

No kernel or recovery source change is required. V27 remains unbooted and
must never be used.
