# Generation-11 NCM-progress recovery wrapper — offline

Date: 2026-08-04

Result: **PASS production-trust-root recovery build, clean twin wrapper build,
and deterministic Generation-11 issuance; unbooted, unprofiled, and not
admitted**.

## Purpose

Generation 10 proved correlated `REQUEST_ACCEPTED` and a complete host-side
bundle transfer, but its ACM response transport closed before a later progress
or `PREPARED` response reached the host. The successor adds the independently
captured, receive-only NCM progress stream described by the
[NCM progress contract](../docs/recovery-ncm-progress.md). This checkpoint
binds that responder to the retained production recovery trust root, rebuilds
the complete ASUS 5.4 recovery wrapper twice, and issues the resulting raw
wrapper as Generation 11 twice without contacting the phone.

## Recovery and wrapper build

The recovery initramfs was rebuilt twice under profile
`reconstructed-v18r-v1` with the retained public trust root. Two clean wrapper
builds under `steam-deck-asus-5.4-v1` used the accepted
`accepted-wrapper-v18-v1` configuration. Cache publication was disabled.

| Item | Size | SHA-256 |
| --- | ---: | --- |
| NCM-progress recovery responder | 132,896 | `242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7` |
| fixed bundle fetcher | 132,824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| native bundle verifier | 4,467,272 | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| production raw public key | 32 | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| stable-recovery initramfs | 7,596,411 | `3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c` |
| wrapper source identity | — | `3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8` |
| sealed source-tree inventory | 1,182,067,858 | `592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a` |
| wrapper configuration | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS 5.4 wrapper Image | 50,498,048 | `895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae` |
| raw recovery wrapper | 58,101,760 | `44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2` |
| canonical source AVB | 100,663,296 | `8c0916fec05c8636a10cbdec3e535f0f3bb705fd1115113a3344ca9fc20a61c1` |

The A/B initramfses, Images, raw wrappers, and source AVB wrappers are
byte-identical. The 79,030-entry source-tree seals before and after both builds
compare equal. The NCM responder and recovery initramfs differ from Generation
10 (`67b4f012…f2c167` and `99046d30…c6e31`), and the new raw and canonical AVB
wrappers differ from Generation 10 (`27f4dbcc…d73b3` and
`b2ada6b8…dba83`).

The retained production base is
`build/generation11-ncm-progress-production-base-20260804`. It is ignored by
Git and contains no private signing key.

## Deterministic Generation-11 issuance

Two independent issuer invocations produced these ignored trees:

- `build/stable-recovery-generation11-ncm-progress-20260804-a`; and
- `build/stable-recovery-generation11-ncm-progress-20260804-b`.

| Item | Value |
| --- | --- |
| generation | `11` |
| Generation-11 AVB SHA-256 | `8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562` |
| generation-record SHA-256 | `4b62b7906ad40f2a36b52a9756a7250364dfe6d9eff4b0c57d25f60713145e49` |
| raw SHA-256 | `44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2` |
| source AVB SHA-256 | `8c0916fec05c8636a10cbdec3e535f0f3bb705fd1115113a3344ca9fc20a61c1` |
| AVB salt | `00272b827ebb11f198be4758db4008cf534f592f0e63fc82c891cda3b4691c6d` |
| AVB payload digest | `9ccf32a823f5a4685922ed42400bc024d7210412216537cfffb1c128e17febf9` |
| partition size | `100663296` |
| authority | `none` |

Each output has the exact expected 11-file inventory. Every retained byte
matches across the two trees; A/B raw and AVB wrappers also match within each
tree. Pinned `avbtool` verifies the `NONE` footer and `boot` descriptor. An
independent SHA-256 calculation over the recorded salt plus all issued raw
bytes reproduces the payload digest. The Generation-11 AVB is distinct from
every retained Generation 1–10 AVB, and the issuer rejects the pre-NCM raw
identity before publishing output.

## Verification and review

- recovery initramfs reproducibility under two locales: pass;
- two clean byte-identical ASUS wrapper builds: pass;
- source seal before/after comparison: pass;
- two independent Generation-11 issuances: pass;
- exact inventories, cross-tree equality, and A/B equality: pass;
- pinned `avbtool`, independent salt-plus-raw digest, and trust-root checks:
  pass;
- hostile issuer regression, including fresh-versus-old raw binding: pass;
- recovery progress runtime: 8/8 pass;
- recovery progress collector: 21/21 pass;
- privileged recovery host controller: 34/34 pass;
- minimal-headless lifecycle: 69/69 pass; and
- candidate integration: 2/2 pass; and
- complete `scripts/host/test-repository-linux.sh ci`: pass, including all 42
  tracked Markdown-link checks and the AArch64 QEMU/systemd closure.

A constrained, tool-free Claude review first found missing positive proof of
the fresh NCM raw identity, insufficient cross-generation mutation coverage,
one indirect digest input, and two standing-authorization wording issues.
All were corrected. The post-fix Claude review returned `NO FINDINGS`.

Independent Codex specification review returned `NO FINDINGS`. Standards
review raised only a judgment-call request to abstract the explicit
Generation-10/11 digest blocks. The explicit blocks remain because the exact
per-generation values and negative cross-generation path are evidence under
test, and hiding them behind a helper would not reduce product code or risk.

## Host and phone boundary

The host's ambient AArch64 `binfmt_misc` handler was disabled only for the
sealed ARM64 build, then restored through `systemd-binfmt.service`; its enabled
state and interpreter were verified afterward. No persistent host service,
network profile, firewall rule, listener, or export was changed.

No fastboot, ADB, SSH, recovery transport, phone interface, reboot, boot,
flash, wipe, slot operation, phone-storage access, connected preflight, or
private signing operation occurred. The phone was not inspected or changed.

## Decision and next gate

Generation 11 now exists only as two ignored, byte-identical offline artifact
trees with `authority=none`. There is no lifecycle profile, artifact-inventory
row, temporary-boot policy row, connected admission, or live evidence. These
files cannot authorize a boot.

Before any phone action, a separate reviewed change must pin this exact tuple
in one immutable offline lifecycle profile. First this issuer/evidence
checkpoint must pass complete local and exact-head GitHub CI. The later profile
must verify both retained trees against the complete timeout/rollback/fallback/
private-evidence chain and pass its own publication gates before any distinct
one-shot central-policy admission or connected preflight is considered. The
temporary lifecycle remains diagnostic-only, boot-only, non-retryable after
consumption, and never flashable.
