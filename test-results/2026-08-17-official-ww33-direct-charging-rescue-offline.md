# Official WW33 direct charging rescue — offline checkpoint

## Outcome

The corrected WW33 charging payload now has a distinct, deterministic
RAM-only `fastboot boot` composition. It bypasses the failed
ASUS-5.4-to-ASUS-5.4 kexec transition while preserving the payload's exact
kernel, matching ADSP modules, read-only `modem_b` firmware mount, battery/USB
telemetry, and 30-second rollback. No phone boot, claim consumption, slot
change, or phone-storage write occurred at this checkpoint.

This is not the retired direct-v5 probe. Direct-v5 replaced Android PID 1,
disabled every fstab entry, and therefore skipped the modem/ADSP sequence that
provides the charger service. The new composition uses the already-tested
official-WW33 rescue initramfs and adds the unique command-line identity
`rog5.charging_route=fastboot-direct-v2`.

The first offline composition passed CI but was rejected before claim or phone
contact: it required active slot A for the matching `vendor_boot_a`, while its
reused kexec initramfs still required `androidboot.slot_suffix=_b`. V2 performs
one bounded, length-preserving rewrite of the exact `_b` token to `_a` and its
matching diagnostic text before recompression. The builder fails unless both
source strings occur exactly once, both destination strings occur exactly
once, no source string remains, and the uncompressed archive length is
unchanged. The original slot-B kexec bundle is not modified.

## Why direct entry is the next discriminator

The official WW33 recovery/kexec cycle transferred and claimed its payload,
but the target disappeared before reporting. Historical results separately
show that ASUS 5.4 self-kexec is unreliable on this device while ASUS 5.4 can
kexec the mainline target. Direct ABL entry removes that transition from the
experiment.

Android boot header v3 obtains its DTB and vendor ramdisk from the active
`vendor_boot` partition. The backed-up slot-A `vendor_boot_a` is not
byte-identical to the official WW33 image: its module set has different local
version identities. Those modules do not supply the new target's five
charger/ADSP modules; the exact
`5.4.210-qgki-perf-gc89cd02a7dfe` modules remain embedded in the generic rescue
initramfs and are loaded explicitly by `/init`.

The DTB comparison is narrower and favorable. Both slot-A and official WW33
vendor-boot images contain four concatenated FDTs. The first three are
byte-identical; selected index zero is
`edc923c729fb06d748dbcf4d567df021c73f4047d12f0be31120006c61c321e3`.
Only the final 173-byte FDT differs. This supports using slot A for one direct
candidate, but it remains a live hypothesis until ABL actually boots it.

The v3 composition follows the AOSP rule that the generic ramdisk is loaded
after, and overlays, the vendor ramdisk. See the
[AOSP vendor-boot documentation](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions).

## Exact inputs and outputs

| Artifact | SHA-256 |
|---|---|
| official WW33 boot template | `fb9866b37b8ad92049057415347e0be18f46a4bd3f63e5cae1a0bfb8b2d575c8` |
| rescue bundle manifest | `037a1fac2dde71b0a8a887612fcbd6bad5df59e998ab35f802137b9095b96630` |
| official WW33 Image | `54b8d9d23ace1126bf1059f1ab483c027b50865695c7b305a15311e30a217b33` |
| source rescue initramfs | `22bccf4d3a138cc09c1120d787a0a67a5079c6d7c78dd579468498077c58f639` |
| slot-A direct initramfs | `bbd31b29fea2b7fbc252a0d32fc25959349061d315ce8e15dcbfa796b790e7d3` |
| direct raw boot image | `ec94f3fd923f93e27c0a016711d341b60ea921a51649ff2ae70a3adfb6785fee` |
| 100,663,296-byte direct AVB image | `902212c20873ff105123a8406d9bc0ce180a3f0461abb7eef6fcf6a168cec6a6` |
| candidate record | `42bf129431d4ba471ae55c0d6f2fa4932d8bf347d18a29df103735c12c43640b` |

The two corrected production builds completed in 3.333 and 2.862 seconds and
were byte-identical. The focused deterministic/hostile test completed in 2.260
seconds. It proves header-v3 composition, exact kernel retention, deterministic
slot-patched ramdisk composition, bare kernel-flag support, safe collapse of
byte-identical duplicate keys, the one direct-route token, end-to-end slot-A
binding, refusal of an existing
output, and refusal of a wrong manifest identity.

## Remaining live gate

Publish this source checkpoint and require successful exact-head CI before
creating the private one-use claim. Then transition the exact Alpine fallback
to fastboot once, read `battery-voltage` and `battery-soc-ok`, set active slot
A only for this candidate, and boot the exact direct image once. A successful
cycle must produce target telemetry and return through the 30-second rollback.
Positive charging requires measured rising pack voltage; a visible icon or
stable voltage alone is insufficient.

Stage-1 storage work remains paused until fastboot reports
`battery-soc-ok: yes`.
