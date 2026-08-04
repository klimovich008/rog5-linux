# Generation-11 immutable offline profile

Date: 2026-08-04

Result: **PASS immutable offline-only profile and both retained-tree artifact
preflights; unbooted and not admitted**.

## Profile boundary

`headless-diagnostic-generation11-offline-v1` pins the complete receive-only
NCM-progress recovery tuple:

| Item | SHA-256 |
| --- | --- |
| Generation-11 AVB | `8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562` |
| recovery trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| signed diagnostic manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| native host verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |
| AVB-generation record | `4b62b7906ad40f2a36b52a9756a7250364dfe6d9eff4b0c57d25f60713145e49` |
| AVB salt | `00272b827ebb11f198be4758db4008cf534f592f0e63fc82c891cda3b4691c6d` |
| AVB payload digest | `9ccf32a823f5a4685922ed42400bc024d7210412216537cfffb1c128e17febf9` |
| ASUS wrapper Image | `895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae` |
| raw wrapper | `44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2` |
| stable-recovery initramfs | `3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c` |
| NCM-progress recovery responder | `242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7` |
| bundle fetcher | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| bundle verifier | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |

The profile also fixes bundle `headless-netroot-early-diag-v1`, bundle profile
`diagnostic-initramfs-v1`, and target ID `headless-netroot-early-diag`. The
signed target bundle and manifest are intentionally reused from Generation 10:
the target tuple did not change, while Generation 11 changes only the recovery
wrapper and its receive-only NCM observability. `policy-preflight` emits the
canonical tuple plus `authority=none`.

Only `policy-preflight` and `artifact-preflight` are supported. Connected
`preflight` and `boot` reject with the Generation-11 offline-only error before
command, credential, host-service, fastboot, or phone inspection, even when
all live authorization guards are supplied. No Generation-11 live profile is
supported, and the one-shot lifecycle selector remains on the consumed
Generation-10 history rather than selecting this artifact.

This artifact profile binds recovery and signed target identities for offline
verification. It deliberately does not claim that the installed NCM collector,
broker, controller, timeout lattice, rollback path, or private-evidence path
has been admitted for a Generation-11 lifecycle. Those host/lifecycle bindings
belong to a separate reviewed live-profile transition.

## Retained artifact verification

Both ignored issuer trees pass the exact artifact gate against the unchanged
matching signed diagnostic bundle twins:

- `build/stable-recovery-generation11-ncm-progress-20260804-a` with the
  Generation-10 production `bundle-a`; and
- `build/stable-recovery-generation11-ncm-progress-20260804-b` with the
  Generation-10 production `bundle-b`.

The gate independently verifies both A/B AVB and raw images, both wrapper
Images/configurations/initramfses, the extracted recovery components, the
production trust root, the signed bundle manifest, the AVB descriptor, exact
salt and digest, wrapper command line, and embedded initramfs composition. All
11 retained files match across the issuer trees. A copied tree with
`generation=11` changed to `generation=10` fails on the generation-record
identity before artifact acceptance.

The exact native host-verifier binary was copied from the unchanged
Generation-10 production base into the ignored Generation-11 production base
solely so host-local artifact preflight can verify the reused target bundle.
It is not embedded in the recovery initramfs and is not a tracked artifact.

## Inventory and integrity chain

`manifests/artifacts.tsv` contains one exact Generation-11 row marked
`unbooted`, offline-only, `authority=none`, untracked, and never flash. The
inventory is not boot authority. `manifests/temporary-boot-images.tsv` remains
unchanged with zero `allow` rows and no Generation-11 entry.

Adding the inventory row advances the fail-closed integrity chain:

- artifact manifest:
  `37425d48b4869b182ea247d13dc7023e912a403f1677da1f77e83b912d4cc514`;
- minimal-headless compatibility profile:
  `b8ad8d4b8155c81aac78f710bad821146f64097e3278c75c3c04eff01408c01e`;
- source/DT contract file checkpoint identity (informational outer digest; no
  tracked consumer pins it):
  `a9c1e2a43fa2dcbbafe9a652f4b7948d5074dbf5b4e731469fda80d28fafd26c`;
  and
- unchanged temporary-boot policy:
  `1f3de8269d986c94c0c0c223a059b9953a04a05ae2895c611710b53e5ddfadea`.

## Verification

- exact five-field profile mutation matrix: pass;
- exact source-level pins for all 12 internal Generation-11 assignments: pass;
- connected-action rejection before host inspection: pass;
- prospective Generation-11 live-profile and lifecycle-selector absence:
  pass;
- host-local exact cross-tree 11-file equality: pass;
- host-local artifact preflight against both retained trees and both unchanged
  signed bundle twins: pass;
- host-local mutated generation-record rejection: pass;
- artifact inventory/boot-policy separation: pass;
- focused stable-recovery gate: pass;
- 39 compatibility-oracle tests: pass; and
- 74 source/DT contract tests: pass with one expected optional-source skip;
- independent Codex specification review: no findings;
- independent Codex standards review: no documented-standard violations and
  one judgment-call duplication note retained because explicit
  per-generation tuples are deliberate evidence; and
- constrained tool-free Claude Opus review: one initial lifecycle-leak oracle
  gap corrected by rejecting the Generation-11 profile name, artifact path,
  and AVB hash in both lifecycle sources; post-fix re-review: `NO FINDINGS`.
- complete `scripts/host/test-repository-linux.sh ci`: pass, including all 42
  tracked Markdown-link checks and the AArch64 QEMU/systemd closure.

No credential, privilege, network listener, NFS export, fastboot, ADB, SSH,
phone interface, reboot, boot, flash, wipe, slot operation, or phone-storage
access occurred. A separate reviewed live-profile change must bind the complete
installed-host, timeout, rollback, fallback, one-shot consumption, and
private-evidence paths before connected preflight can be considered. A still
separate central-policy admission is required before any temporary boot.

The retained issuer trees, production recovery base, and signed target bundle
twins are ignored local build outputs. Repository CI therefore exercises the
profile, policy, mutation, inventory, and source-level pinning checks but
reports the retained-tree and generation-record artifact checks as `SKIP`
when those local trees are absent. The host-local passes above are preserved by
this evidence record; they are not presented as GitHub CI executions.
