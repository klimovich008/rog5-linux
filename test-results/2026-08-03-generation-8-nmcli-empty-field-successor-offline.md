# Generation-8 NetworkManager-empty-field successor — offline

Date: 2026-08-03

Result: **PASS offline issuance and immutable profile; unbooted and not
admitted**. Two separate issuer invocations on this host produced byte-identical
Generation-8 wrapper trees with the same new outer AVB identity over the
unchanged recovery payload. The successor exists
only to consume a fresh one-shot identity after correcting the host parser for
NetworkManager 1.52.1's canonical empty `GENERAL.CON-UUID` rendering.

## Exact identities

| Item | SHA-256 |
| --- | --- |
| Generation-8 AVB image | `f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415` |
| AVB-generation record | `9805809c27e1fe47efcbc7561fe5289e81d789beba231acbac59c32a67ae59d5` |
| AVB salt | `a8563ded9a34767ed97ed4f9130361a1b4efadc91ee7294d9a212caf59e53899` |
| AVB payload digest | `b297100d269798d4eaf46b37899c3cf9196f7c076df3a31d39fe3d2db5915dbc` |
| Canonical generation-zero source AVB | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| Unchanged raw recovery | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| Unchanged recovery kernel | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| Unchanged recovery initramfs | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |

The A and B trees are byte-identical for every retained file, as are the A/B
twins within each tree. The wrapper is distinct from Generations 1–7. Pinned
`avbtool` independently verifies the exact `NONE` descriptor, `boot`
partition, image geometry, salt, and digest. The raw prefix is byte-identical
to the audited source. Both generation records retain `authority=none`.

## Offline profile and authority boundary

`headless-diagnostic-generation8-offline-v1` pins the complete recovery,
component, signed-bundle, trust-root, manifest, host-verifier, generation
record, salt, and digest tuple. It permits only `policy-preflight` and
`artifact-preflight`. Connected `preflight` and `boot` reject before host or
phone inspection even if every live guard is supplied.

The prospective `headless-diagnostic-generation8-live-v1` remains unsupported.
The lifecycle selector still names consumed Generation 7. The artifact
inventory contains one exact `unbooted`, `authority=none`, `never flash` row;
temporary-boot policy contains no Generation-8 row and zero active `allow`
rows. The compatibility oracle pins the resulting complete inventory as
`695f565017aecc6f5ce739e1dce266a4d99ac4a538fc99a9e162b909db45fcc4`.
The source/DT contract in turn pins the resulting compatibility profile as
`e5c0e00f1ca51d687965dcd7086c856fd52fc19664a0cf1ad75512e40828c993`.
This checkpoint cannot boot the phone.

## Verification

- deterministic issuer regression through Generation 8: pass;
- two separate host-local production issuer invocations: pass;
- host-local cross-tree and within-tree twin equality: pass;
- non-reuse of every predecessor generation: pass;
- exact five-field policy mutation matrix: pass;
- offline connected-action rejection: pass;
- unissued live-profile rejection: pass;
- host-local artifact preflight against both retained trees: pass;
- host-local generation-record mutation rejection: pass; and
- focused stable-recovery live-gate suite: pass;
- 39 compatibility-oracle tests: pass;
- 74 source/DT contract tests: pass with one expected optional-source skip;
  and
- complete repository Linux `ci` tier: pass.

The test-first issuer checkpoint was published at exact commit `dac27b0`, and
GitHub Actions [run `30823148903`](https://github.com/klimovich008/rog5-linux/actions/runs/30823148903)
passed `qemu-system` in 47 seconds and `recovery-core` in 3 minutes 22 seconds
before production issuance.

The first constrained Claude Opus review found six issues without finding a
boot-authority break: two documentation regressions, incomplete prospective
live-profile action coverage, an implicit lifecycle-selector claim, missing
within-tree comparisons, and inconsistent roadmap status. All were corrected.
The follow-up confirmed five fixes and requested that same-host twin
reproduction not be described as independent-host reproduction; every such
claim now says host-local. The focused gate and complete CI pass after those
changes.

Adding the inventory row intentionally tripped two chained integrity pins.
The compatibility profile now pins artifact manifest
`695f565017aecc6f5ce739e1dce266a4d99ac4a538fc99a9e162b909db45fcc4`,
and the source/DT contract pins resulting compatibility profile
`e5c0e00f1ca51d687965dcd7086c856fd52fc19664a0cf1ad75512e40828c993`.
Each layer failed closed before its pin was updated and then passed its full
hostile suite.

No signing credential, privilege, fastboot command, phone interface, reboot,
network listener, NFS export, or phone storage was used. A separate reviewed
change is required to create a live lifecycle profile; a still-separate
central-policy change is required to admit one temporary boot.
