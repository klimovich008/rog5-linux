# Recovery postmortem refreeze — offline

Date: 2026-08-09
Starting repository SHA: `6e767616985d11c9292bcbd5d2f201c3c4db7363`
Recommendation: **HOLD**

## Outcome

The pstore-aware stable-recovery responder is now integrated into two
byte-identical shell-free initramfses and two genuinely clean ASUS 5.4 wrapper
builds. The complete config, kernel Image, initramfs, boot-v3 image, unsigned
AVB wrapper, and sealed source state reproduce exactly. This closes the
offline composition gap recorded by the preceding
[lineage checkpoint](2026-08-09-recovery-postmortem-lineage-offline.md).

It does **not** prove that the Snapdragon ramoops reservation survives a real
target → fallback → bootloader → recovery sequence. The products are ignored
test artifacts, use a disposable public trust input, have AVB
`Algorithm: NONE`, are absent from temporary-boot policy, and have no candidate
record or boot authority. No phone or production credential was used.

The earlier critical-path result is unchanged: the readiness race is
structurally reproducible in the hardware-free model but is not established as
the cause of Generation 12. Exact host timings, patches, hostile tests, NFS
timeout calculation, watchdog audit, VCNL isolation, and retention inventory
remain in the
[critical network-root review](2026-08-09-critical-network-root-readiness-review-offline.md).

## Complete refrozen identity

The shell-free initramfs integration used reconstructed base profile
`reconstructed-v18r-v1` and produced:

| Component | Size | SHA-256 |
|---|---:|---|
| recovery init source | — | `23791f8e22924773baf6aa223a13bfa4bdd65ae3e51187ea221e61874ee7b7ab` |
| native recovery responder | 132,896 | `897a521c94557152a466f33c295f008100e3a183d84f94bf767c65bf49f91fea` |
| fixed bundle fetcher | 132,824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| native bundle verifier | 4,467,272 | `33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef` |
| disposable public trust input | 32 | `c6e613ffcbb4513805ee2947f017a6f1e16c267df0b3d654143d80a67e2358b9` |
| stable-recovery initramfs A/B | 7,601,886 | `c778588a5620ca0270fa7859861c78386edeaaef3f13e2403aebbd8dc2b7a380` |

The network-disabled clean wrapper builds used the sealed ASUS source volume,
qualified Steam Deck builder profile `steam-deck-asus-5.4-v1`, Clang 18.1.3,
accepted wrapper profile `accepted-wrapper-v18-v1`, and source identity
`3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`.
Their complete source seals were identical before and after both builds at
`4c4958385b9d0f270c368642c484c84e4c60ea23d18f68c00e37ca67a8637344`.

| Wrapper product | Size | SHA-256 |
|---|---:|---|
| config A/B | — | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| kernel Image A/B | 50,498,048 | `4b30cfff3aedb6ac04bb57d981df920314d830adcbcbed9a3da033db7cec9495` |
| raw boot-v3 image A/B | 58,105,856 | `5141f0d037f8ca8dc5a2367a476b2730d4cdac8cd61d6d29a95bbf3ca477deab` |
| unsigned AVB image A/B | 100,663,296 | `b004e500a7e77840568ec6e8aee8092e16a9e6a4089f954d140d68c8c2b0c218` |

The built config contains `CONFIG_PSTORE=y`, `CONFIG_PSTORE_CONSOLE=y`,
`CONFIG_PSTORE_PMSG=y`, and `CONFIG_PSTORE_RAM=y`. The inspected boot image
contains the exact 4 MiB reservation at `0x9b800000`, split into a 1 MiB record
and 3 MiB console region, with pmsg/ftrace disabled and `dump_oops=1`. The
wrapper also retains one 180-second recovery rollback token. The AVB footer
verifies its sole 58,105,856-byte `boot` descriptor, but `Algorithm: NONE` and
rollback index zero make this explicitly an unsigned test product, not a
release or admission artifact.

## Physical retention experiment boundary

A future physical test must preserve the existing one-use model. It requires
two separately reviewed temporary-boot admissions, not reuse of one image:

1. one execution recovery identity may load exactly one new diagnostic target
   whose early log emits the exact candidate/boot-ID lineage marker;
2. the unchanged rollback must return exact Alpine and complete its normal
   health and host cleanup proof;
3. a guarded, separately authorized transition may return that fallback to
   fastboot;
4. a distinct observation-only recovery identity, built from the same reviewed
   recovery internals but with its own outer identity and irreversible claim,
   may boot once and must not prepare or commit a payload;
5. the host may run only `postmortem-status CANDIDATE BOOT_ID` and retain its
   redacted result.

Only `MATCH` or `MATCH_REPEATED` proves that the exact marker survived this
sequence. `DIFFERENT_MARKER` proves stale/different lineage. `UNAVAILABLE`,
`NO_RECORDS`, `NO_MARKER`, or `AMBIGUOUS` is an inconclusive observation and
never proof that no crash occurred. A matching marker also does not by itself
prove a panic; fatal/crash interpretation remains separate. No transport loss
or ambiguous result authorizes replay of either one-use identity.

This proposal deliberately keeps candidate issuance, both physical boots,
credential use, and execution authority outside this checkpoint.

## Timing, retention, and remaining uncertainty

- clean-twin responder/initramfs integration: PASS in 91.35 seconds;
- two clean ASUS 5.4 wrappers plus repack, AVB inspection, source reseal, and
  full twin comparison: PASS in 2,088.42 seconds (34m48s);
- complete exact-tree repository Linux `ci` tier after this documentation
  checkpoint: PASS in 465.06 seconds (the preceding critical code checkpoint
  recorded 456.488 seconds);
- retained ignored evidence: 9.3 GiB below
  `build/postmortem-refreeze-offline-20260809/`;
- free space after the build: approximately 422 GiB;
- no wrapper build process or output lock remained after completion.

The source and complete product now reproduce, but offline tests cannot
establish whether boot firmware, the Alpine fallback, or a later recovery boot
clears or overwrites the reserved DRAM. Stable recovery still has no proven
independent UART. The only honest recommendation remains **HOLD** until a
separately admitted physical retention experiment returns lineage-safe
evidence.

No signing key, production trust key, SSH credential, administrator
credential, fastboot/ADB/ACM/NCM device, phone storage, candidate issuance,
policy row, flash, wipe, erase, slot operation, persistent installation, or
phone boot was used.
