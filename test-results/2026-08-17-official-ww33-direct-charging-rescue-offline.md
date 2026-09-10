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
`rog5.charging_route=fastboot-direct-v3`.

The first offline composition passed CI but was rejected before claim or phone
contact: it required active slot A for the matching `vendor_boot_a`, while its
reused kexec initramfs still required `androidboot.slot_suffix=_b`. V2 performs
one bounded, length-preserving rewrite of the exact `_b` token to `_a` and its
matching diagnostic text before recompression. The builder fails unless both
source strings occur exactly once, both destination strings occur exactly
once, no source string remains, and the uncompressed archive length is
unchanged. The original slot-B kexec bundle is not modified.

V2 was then rejected before issuance because its inherited
`echo b >/proc/sysrq-trigger` rollback would normally boot the still-active,
known-bad slot A. V3 removes that one direct-init line and embeds a freestanding
static AArch64 helper that performs Linux `RESTART2("bootloader")`. The helper
has no interpreter or dynamic segment. Success cannot return; any returned
syscall exits with status 111 and the invoking `fail` path leaves PID 1 in its
fail-closed loop rather than attempting a normal reboot. The existing
host lifecycle restores slot B only after exact fastboot identity returns.

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
| slot-A direct initramfs | `69ed47cec0bf58268fea04382ab1f68d6bf0363d5d9b70b21f8949ac78ed893f` |
| restart2 helper | `68d6a69e597e9fa86ee956ee9fadc15f4283e7dd2a6032b924449330bb3e4785` |
| direct raw boot image | `785cc50f52ec9efd9d6d4376772db3bcf96a8ddb2295669414b54b7b79b33443` |
| 100,663,296-byte direct AVB image | `17380c1b362e1f41f2c9c9a231d976ad58f8d09cfaad50a39f7f5205ad94e8ae` |
| candidate record | `4f1535bca3722551214abd952ae2b23020ead2b3bcf37080167b8519df9d7f11` |

The two corrected production builds completed in 3.858 and 4.069 seconds and
were byte-identical. The focused deterministic/hostile test completed in 3.058
seconds. It proves header-v3 composition, exact kernel retention, deterministic
slot-patched ramdisk composition, the static AArch64 bootloader rollback,
bare kernel-flag support, safe collapse of byte-identical duplicate keys, the
one direct-route token, end-to-end slot-A binding, refusal of an existing
output, and refusal of a wrong manifest identity.

## Live disposition

The exact-head checkpoint was subsequently issued once and is consumed. ABL
accepted the image at 6.893 V with slot A active. Fastboot departed, but no
target USB or 30-second userspace rollback appeared. About 115 seconds after
boot acceptance, the anchored port enumerated Qualcomm `05c6:900e`
full-RAM-dump mode. Physical fastboot recovery restored slot B at 6.888 V;
`battery-soc-ok` remained `no`.

This rejects the direct slot-A composition and proves that PID 1 did not reach
the embedded rollback helper. It does not identify the earlier kernel or
firmware failure. The image and claim must never be retried or flashed.
Subsequent work switched to the exact stock slot-B lineage and is recorded in
the [stock live result](2026-08-17-stock-slotb-charger-live.md). Stage 1 remains
paused until fastboot reports `battery-soc-ok: yes`.
