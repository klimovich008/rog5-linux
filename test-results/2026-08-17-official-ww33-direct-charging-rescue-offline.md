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
`rog5.charging_route=fastboot-direct-v1`.

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
| rescue initramfs | `22bccf4d3a138cc09c1120d787a0a67a5079c6d7c78dd579468498077c58f639` |
| direct raw boot image | `40a6bf5d500c3ba0a228f45dcbdded57356d99831540d53398aded54425403a7` |
| 100,663,296-byte direct AVB image | `d9584575a91d42b3b763034800b0e3d94aeab5af11d21b413ca2d0293051b7b6` |
| candidate record | `02169fccb158df2e5486f63e8fd19e372c7d50065daf59608430ef582d536e30` |

The two production builds completed in 2.023 and 2.215 seconds and were
byte-identical. The focused deterministic/hostile test completed in 2.227
seconds. It proves header-v3 composition, exact kernel and ramdisk retention,
bare kernel-flag support, safe collapse of byte-identical duplicate keys, the
one direct-route token, slot-A binding, refusal of an existing output, and
refusal of a wrong manifest identity.

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
