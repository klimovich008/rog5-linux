# Generation-11 lifecycle profile — offline transition

Date: 2026-08-04

Result: **PASS offline**. The one-shot diagnostic lifecycle now selects the
exact Generation-11 recovery tuple through a distinct live-capable profile.
Generation 11 remains unbooted, absent from temporary-boot policy, and unable
to reach connected host inspection. No phone or credential interface was
used.

## Prior checkpoint

The immutable `headless-diagnostic-generation11-offline-v1` profile and its
retained-tree evidence were independently reviewed and published. Exact-head
GitHub Actions runs `30904224177` and `30904580002` passed before this separate
transition began.

## Exact transition

`headless-diagnostic-generation11-live-v1` reuses the complete offline tuple
without rebuilding or changing any payload:

| Item | Identity |
| --- | --- |
| AVB image | `8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562` |
| generation record | `4b62b7906ad40f2a36b52a9756a7250364dfe6d9eff4b0c57d25f60713145e49` |
| AVB salt | `00272b827ebb11f198be4758db4008cf534f592f0e63fc82c891cda3b4691c6d` |
| AVB payload digest | `9ccf32a823f5a4685922ed42400bc024d7210412216537cfffb1c128e17febf9` |
| ASUS wrapper Image | `895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae` |
| raw wrapper | `44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2` |
| recovery initramfs | `3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c` |
| NCM-progress responder | `242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7` |
| bundle fetcher | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| bundle verifier | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| signed manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| host verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |

The profile also fixes target `headless-netroot-early-diag`, bundle
`headless-netroot-early-diag-v1`, and bundle profile
`diagnostic-initramfs-v1`. The lifecycle selector changed from consumed
Generation 10 to exact Generation 11.

The future one-shot policy identity is pinned but not admitted:

- image path:
  `build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img`;
- basis: `one generation-11 receive-only NCM-progress diagnostic lifecycle
  after connected preflight; remove after any result; never flash`.

## Fail-closed boundary

- the offline profile rejects connected `preflight` and `boot` before host
  inspection;
- the live profile rejects either direct connected action unless the one-shot
  lifecycle guard is present;
- even with that guard, missing-file, missing-row, malformed-header,
  malformed-artifact-header, missing-artifact-row, duplicate-artifact-row,
  duplicate-policy-row, and wrong-basis fixtures reject before host inspection;
- both profiles pass the exact five-field policy mutation matrix;
- the Generation-11 case has source-scoped pins for all 14 internal and future
  policy assignments;
- both profiles pass artifact preflight against both retained issuer trees and
  matching signed-bundle twins;
- a mutated generation record still fails artifact preflight;
- lifecycle source and tests select only the Generation-11 live profile and do
  not embed the artifact path or AVB digest; and
- `manifests/temporary-boot-images.tsv` remains unchanged with zero `allow`
  rows and no Generation-11 entry.

## Inventory and integrity chain

The inventory records the separate live lifecycle profile while retaining
`authority=none`, `unbooted`, no admission, and no boot claim. Inventory is not
boot authority. The updated fail-closed chain is:

- artifact manifest:
  `900e4f6d97c2fae6b835f63a49979da2c7f1d2009685a0460792907c00118c91`;
- minimal-headless compatibility profile:
  `08233337c32626b7563c8b0e2fd7b29d745f58c1ec71061441500802ec012da5`;
- source/DT contract checkpoint identity (informational outer digest):
  `b5f8b9b9fc8a756ad06eeaa27c236d1d612c6e97ffd569c095f99a29d4457881`;
  and
- unchanged deny-by-default temporary-boot policy:
  `1f3de8269d986c94c0c0c223a059b9953a04a05ae2895c611710b53e5ddfadea`.

## Verification

- shell syntax, Python compilation, and `git diff --check`: pass;
- 69 minimal-headless lifecycle tests: pass;
- stable-recovery gate, including four Generation-11 retained-tree/profile
  combinations: pass; and
- artifact inventory versus boot-policy separation: pass;
- complete `scripts/host/test-repository-linux.sh ci`: pass;
- Claude Opus review found stale test-plan evidence and missing artifact-row
  uniqueness fixtures; both were fixed, and the focused re-review found no
  remaining implementation or test issue after one final citation correction;
  and
- independent Codex review: no actionable correctness findings.

The reviewed implementation was published at commit `2a483ec`; exact-head
GitHub Actions run `30908649494` passed `recovery-core` in 3m49s and
`qemu-system` in 40s. The next gate is a separate central-policy admission
change. No private credential, signing key, privilege, network listener, NFS export, fastboot, ADB, SSH, recovery
transport, phone interface, reboot, boot, flash, wipe, slot operation, or
phone-storage access occurred. A separately reviewed and published central
policy change is still required before any connected preflight or temporary
boot.
