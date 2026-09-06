# Generation-10 immutable offline profile

Date: 2026-08-03

Result: **PASS immutable offline-only profile and both retained-tree artifact
preflights; unbooted and not admitted**.

## Profile boundary

`headless-diagnostic-generation10-offline-v1` pins the complete
PREPARE-progress recovery tuple:

| Item | SHA-256 |
| --- | --- |
| Generation-10 AVB | `b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51` |
| recovery trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| signed diagnostic manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| native host verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |
| AVB-generation record | `cb999cd881959055f32fc1b7299cf1dffcf139656ff8c326ea1101d2ffd63b6d` |
| AVB salt | `5f62ef87305b45de2d189729a601ac4b143c45e83485272ef5b91c508df5d3ee` |
| AVB payload digest | `32b0de39bd409601da6b8c16bf5039fe9102410d9fb13a8b9f668283d53aee42` |
| ASUS wrapper Image | `bb49b4057ce573e3a53366c4663094cf462efb09d496b64b890ed2b0dcb65f98` |
| raw wrapper | `27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3` |
| stable-recovery initramfs | `99046d30e0910531ebda1163719ae8b5b81489f11329e29e12195fbfd63c6e31` |
| PREPARE-progress responder | `67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167` |
| bundle fetcher | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| bundle verifier | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |

The profile also fixes bundle `headless-netroot-early-diag-v1`, bundle profile
`diagnostic-initramfs-v1`, and target ID `headless-netroot-early-diag`.
`policy-preflight` emits only the canonical tuple plus `authority=none`.

Only `policy-preflight` and `artifact-preflight` are supported. Connected
`preflight` and `boot` reject with the offline-only error before command,
credential, host-service, fastboot, or phone inspection, even when every live
guard is supplied. `headless-diagnostic-generation10-live-v1` remains
unsupported and is absent from the lifecycle selector.

## Retained artifact verification

Both ignored issuer trees pass the exact artifact gate against their matching
production bundle twin:

- `build/stable-recovery-generation10-prepare-progress-20260803-a`; and
- `build/stable-recovery-generation10-prepare-progress-20260803-b`.

The gate independently verifies both A/B AVB and raw images, both wrapper
Images/configurations/initramfses, the extracted recovery components, the
production trust root, the signed bundle manifest, the AVB descriptor, exact
salt and digest, wrapper command line, and the embedded initramfs composition.
All 11 retained files match across the issuer trees. A copied tree with
`generation=10` changed to `generation=9` fails on the generation-record
identity before artifact acceptance.

## Inventory and integrity chain

`manifests/artifacts.tsv` now contains one exact Generation-10 row marked
`unbooted`, `authority=none`, offline-only, untracked, and never flash. The
inventory is not boot authority. `manifests/temporary-boot-images.tsv` remains
unchanged with zero `allow` rows and no Generation-10 entry.

Adding the inventory row advanced the fail-closed integrity chain:

- artifact manifest: `e7bb1aa789765f989bcf349f8d021018af1b312aab86652b074061103b30d76e`;
- minimal-headless compatibility profile:
  `52b197ab7372a0d7462e2ca24ef8f4e0881a8f44a85ace0ccfdfa811b3f244de`;
  and
- source/DT contract file checkpoint identity (informational outer digest; no
  tracked consumer pins it):
  `30ee279d1c5a4c26bc0d914f6a91e53e72eb3d562b49fa2f767b7ce78037f430`.

## Verification

- exact five-field profile mutation matrix: pass;
- exact source-level pins for all 12 internal Generation-10 assignments: pass;
- connected-action rejection before host inspection: pass;
- prospective live-profile absence: pass;
- host-local exact cross-tree 11-file equality: pass;
- host-local artifact preflight against both retained trees and both signed
  bundle twins: pass;
- host-local mutated generation-record rejection: pass;
- artifact inventory/boot-policy separation: pass;
- focused stable-recovery gate: pass;
- 39 compatibility-oracle tests: pass;
- 74 source/DT contract tests: pass with one expected optional-source skip;
- constrained tool-free Claude Opus re-review after corrections: `NO FINDINGS`;
  and
- complete `scripts/host/test-repository-linux.sh ci`: pass.

No credential, privilege, network listener, NFS export, fastboot, ADB, SSH,
phone interface, reboot, boot, flash, wipe, slot operation, or phone-storage
access occurred. A separate reviewed and exact-head-green change is required
before a live lifecycle profile may exist. A still-separate central-policy
change is required before any connected preflight or temporary boot.

The retained issuer trees and production bundle base are ignored local build
outputs. Repository CI therefore exercises the profile, policy, mutation,
inventory, and source-level pinning checks but reports the retained-tree and
generation-record artifact checks as `SKIP` when those local trees are absent.
The host-local passes above are preserved by this evidence record; they are
not presented as GitHub CI executions.
