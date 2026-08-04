# Generation-10 lifecycle profile — offline transition

Date: 2026-08-04

Result: **PASS offline**. The diagnostic lifecycle now selects exact
Generation-10 recovery through a distinct live-capable profile. Generation 10
remains unbooted, absent from temporary-boot policy, and unable to reach a
connected preflight or boot. No phone or credential interface was used.

## Prior checkpoint

The immutable `headless-diagnostic-generation10-offline-v1` profile was
independently reviewed, published at `edae5d1`, and passed exact-head GitHub
Actions run `30867110893` before this separate transition began. Recovery-core
passed in 3m16s and QEMU in 32s.

## Exact transition

The new `headless-diagnostic-generation10-live-v1` profile reuses the complete
offline-profile tuple without rebuilding or changing any payload:

| Item | Identity |
| --- | --- |
| AVB image | `b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51` |
| generation record | `cb999cd881959055f32fc1b7299cf1dffcf139656ff8c326ea1101d2ffd63b6d` |
| AVB salt | `5f62ef87305b45de2d189729a601ac4b143c45e83485272ef5b91c508df5d3ee` |
| AVB payload digest | `32b0de39bd409601da6b8c16bf5039fe9102410d9fb13a8b9f668283d53aee42` |
| ASUS wrapper Image | `bb49b4057ce573e3a53366c4663094cf462efb09d496b64b890ed2b0dcb65f98` |
| raw wrapper | `27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3` |
| recovery initramfs | `99046d30e0910531ebda1163719ae8b5b81489f11329e29e12195fbfd63c6e31` |
| PREPARE-progress responder | `67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167` |
| bundle fetcher | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| bundle verifier | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| signed manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| host verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |

The profile also fixes target `headless-netroot-early-diag`, bundle
`headless-netroot-early-diag-v1`, and bundle profile
`diagnostic-initramfs-v1`. The lifecycle selector changed from consumed
`headless-diagnostic-generation9-live-v1` to the Generation-10 live profile.

The future one-shot policy identity is pinned but not admitted:

- image path:
  `build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img`;
- basis: `one generation-10 PREPARE-progress-instrumented diagnostic lifecycle
  after connected preflight; remove after any result; never flash`.

## Fail-closed boundary

- the offline profile still rejects connected `preflight` and `boot` before
  host inspection;
- the live profile rejects either direct connected action unless the one-shot
  lifecycle guard is present;
- even with that guard, missing, duplicate, and wrong-basis Generation-10
  policy fixtures reject before host inspection;
- both profiles pass the exact five-field policy mutation matrix;
- the Generation-10 case has source-scoped pins for all 14 internal and
  future-policy assignments;
- both profiles pass artifact preflight against both retained issuer trees and
  matching signed-bundle twins on this host;
- a mutated generation record still fails artifact preflight;
- the lifecycle test suite selects only the Generation-10 live profile; and
- `manifests/temporary-boot-images.tsv` remains unchanged with zero `allow`
  rows and no Generation-10 entry.

The retained issuer trees and production bundle base are ignored local build
outputs. Clean repository CI therefore skips those retained-tree artifact
checks while continuing to exercise profile selection, policy rejection,
mutation, source pinning, inventory, and lifecycle tests.

## Inventory and integrity chain

The Generation-10 inventory row now records the separate live lifecycle
profile but explicitly retains `authority=none`, `unbooted`, no admission, and
no boot claim. Inventory is not boot authority. The updated fail-closed chain
is:

- artifact manifest:
  `3746038f7002c320791f5b1b4fb53ab6f0f2fda32f8f314f8038508cb2c19b26`;
- minimal-headless compatibility profile:
  `d8ef50162eab745812327113500d6ec4cd321115a7eb2a1ab1d95c4650be4eed`;
  and
- source/DT contract checkpoint identity (informational outer digest; no
  tracked consumer pins it):
  `d806e4681a8cf7e1ad107fbde2cee6a1873fa5ea48889b23e4c36604c676cfaa`.

The outer-digest terminus was checked with a repository-wide exact search over
tracked source, configuration, scripts, documentation, tests, and workflow
files after recomputation; only this evidence record contains that digest.

## Focused verification

- shell syntax, Python compilation, and `git diff --check`: pass;
- 64 minimal-headless lifecycle tests: pass;
- stable-recovery gate, including four Generation-10 retained-tree/profile
  combinations: pass;
- artifact inventory versus boot-policy separation: pass;
- 39 compatibility-oracle tests: pass;
- 74 source/DT contract tests: pass with one expected optional-source skip;
  and
- constrained tool-free Claude Opus re-review after corrections:
  `NO FINDINGS`; and
- complete `scripts/host/test-repository-linux.sh ci`: pass.

No private credential, signing key, privilege, network listener, NFS export,
fastboot, ADB, SSH, recovery transport, phone interface, reboot, boot, flash,
wipe, slot operation, or phone-storage access occurred. A separately reviewed,
published, and exact-head-green central-policy change is required before any
connected preflight or temporary boot.
