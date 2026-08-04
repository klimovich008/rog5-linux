# Generation-10 PREPARE-progress successor — offline

Date: 2026-08-03

Result: **PASS production-key-bound twin build and deterministic Generation-10
issuance; unbooted, unprofiled, and not admitted**.

## Purpose

Generation 9 transferred the complete signed diagnostic bundle but returned no
terminal `PREPARED` response before watchdog fallback. The replacement native
recovery responder emits five request-correlated PREPARE progress boundaries.
This checkpoint binds that responder to the existing production recovery trust
root, rebuilds the complete recovery wrapper twice, and issues a distinct
Generation-10 AVB identity twice without contacting the phone.

## Production build

The guarded deployment launcher consumed the existing external diagnostic
candidate record and recovery signing key. It privately staged the inputs,
scrubbed their paths from the child environment, signed the runtime bundle,
destroyed the private snapshot, and retained only the derived public trust
root. Read-only post-build checks confirmed that the source key and candidate
record metadata and identities did not change.

Two clean ASUS 5.4 wrapper builds produced the same configuration and kernel
Image. The A/B candidate records, signed bundles, recovery initramfses, raw
wrappers, and canonical source AVB wrappers are byte-identical.

| Item | Size | SHA-256 |
| --- | ---: | --- |
| PREPARE-progress responder | 132,896 | `67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167` |
| fixed bundle fetcher | 132,824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| native bundle verifier | 4,467,272 | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| production raw public key | 32 | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| stable-recovery initramfs | 7,595,063 | `99046d30e0910531ebda1163719ae8b5b81489f11329e29e12195fbfd63c6e31` |
| wrapper configuration | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS 5.4 wrapper Image | 50,498,048 | `bb49b4057ce573e3a53366c4663094cf462efb09d496b64b890ed2b0dcb65f98` |
| raw recovery wrapper | 58,101,760 | `27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3` |
| canonical source AVB | 100,663,296 | `b2ada6b8fdc354c2d9676b347a9047fc52e6673d9ac71ad7322c517f68adba83` |
| signed diagnostic manifest | 831 | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |

The retained production base is
`build/prepare-progress-generation10-production-base-20260803`. It is ignored
by Git and contains no private-key snapshot. Its candidate records retain
`status=offline` and `authority=none`.

## Generation-10 issuance

Two independent issuer invocations produced these retained trees:

- `build/stable-recovery-generation10-prepare-progress-20260803-a`; and
- `build/stable-recovery-generation10-prepare-progress-20260803-b`.

| Item | Value |
| --- | --- |
| generation | `10` |
| Generation-10 AVB SHA-256 | `b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51` |
| generation-record SHA-256 | `cb999cd881959055f32fc1b7299cf1dffcf139656ff8c326ea1101d2ffd63b6d` |
| unchanged raw SHA-256 | `27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3` |
| source AVB SHA-256 | `b2ada6b8fdc354c2d9676b347a9047fc52e6673d9ac71ad7322c517f68adba83` |
| AVB salt | `5f62ef87305b45de2d189729a601ac4b143c45e83485272ef5b91c508df5d3ee` |
| AVB payload digest | `32b0de39bd409601da6b8c16bf5039fe9102410d9fb13a8b9f668283d53aee42` |
| partition size | `100663296` |
| authority | `none` |

Each tree has the exact expected 11-file inventory. Every file matches across
the two trees; A/B raw and AVB wrappers also match within each tree. Pinned
`avbtool` verifies the `NONE` footer and the `boot` payload descriptor. A
separate SHA-256 calculation over the generation salt plus all raw-image bytes
reproduces the recorded digest. The Generation-10 AVB differs from every
retained Generation 4–9 AVB; the synthetic issuer regression separately proves
non-reuse through all Generations 1–9.

## Review and verification

- guarded production build and private-snapshot destruction: pass;
- two clean byte-identical ASUS wrapper builds: pass;
- two independent Generation-10 issuances: pass;
- exact 11-file inventories, cross-tree equality, and A/B equality: pass;
- pinned `avbtool` verification and independent salt-plus-raw digest: pass;
- unchanged external signing inputs and no retained private snapshot: pass;
- constrained tool-free Claude Opus re-review after three documentation
  corrections: `NO FINDINGS`; and
- complete `scripts/host/test-repository-linux.sh ci`: pass, including all 41
  tracked Markdown-link checks and the Generation-10 issuer regression.

The checkpoint was published at `d04b804`; exact-head GitHub Actions run
`30865091104` passed recovery-core in 3m35s and QEMU in 40s.

## Boundary and next gate

No fastboot, ADB, SSH, recovery transport, phone interface, reboot, boot,
flash, wipe, slot operation, listener, NFS export, or phone-storage access
occurred. The phone was not inspected or changed.

No Generation-10 lifecycle profile, artifact-inventory row, temporary-boot
policy row, connected admission, or live evidence exists at this checkpoint.
The two ignored trees are not boot authority. Before any phone action, a
separate reviewed change must pin the exact tuple in an immutable offline
profile, pass both retained-tree artifact preflights, publish with green local
and exact-head GitHub CI, and only then consider a distinct live-profile and
one-shot central admission. The eventual temporary lifecycle remains
diagnostic-only and may never be flashed or retried after consumption.
