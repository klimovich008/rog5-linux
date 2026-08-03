# Generation-4 timeout-lattice recovery — offline issuance

Date: 2026-08-03

Result: **PASS offline**. Two independent generation-4 issuances produced
byte-identical output trees over the unchanged, verified generation-3 raw
recovery. The exact generation-4 artifact passes the complete phone-free
stable-recovery artifact gate. It is inventory-only, absent from temporary-boot
policy, and has no live or phone authority.

## Reason for a new generation

The sole generation-3 cycle reached correlated and verified `PREPARED` after a
fresh transfer, signature verification, artifact verification, and kexec load.
The former host transfer service expired after 70 seconds, before recovery's
190-second fetch supervisor, so no independent transfer-completion receipt was
available. NFS never started, `COMMIT_EXEC` was never sent, no target ran, and
exact Alpine fallback passed.

The installed and source-matched host path now uses this strict nested deadline
lattice:

| Boundary | Seconds |
|---|---:|
| device fetch worker | 180 |
| recovery fetch supervisor | 190 |
| host transfer service | 195 |
| privileged host watchdog | 205 |
| lifecycle transfer receipt | 220 |
| lifecycle PREPARE | 260 |
| complete control window | 320 |

Generation 4 does not alter the accepted recovery kernel, initramfs, control,
fetcher, verifier, trust root, target payload, or DTB. It gives the corrected
host-side lifecycle a distinct single-use AVB identity.

## Test-first issuance

Before production issuance,
`scripts/host/test-issue-stable-recovery-avb-generation.sh` was extended to:

- issue generation 4 twice;
- compare both AVB twins and both generation records byte-for-byte;
- prove generation 4 differs from generations 1, 2, and 3;
- recompute and verify the canonical generation-4 salt;
- inspect the AVB descriptor's exact salt and digest; and
- require `generation=4` and `authority=none`.

That regression passed before either production output was created.

## Exact identities

| Item | SHA-256 |
|---|---|
| unchanged raw recovery | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| consumed generation-3 source AVB | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| generation-4 AVB | `220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d` |
| generation-4 record | `8e537a2eae12c0d58d6a37a23816031f9a1a4e83b37679c3321c60aa688d3dc4` |
| canonical AVB salt | `82fd20a6c16d7e0387568beb0ada378ea513119fa4480064c6afa5b3dfa567f8` |
| AVB payload digest | `3e8fc9703763bd9572141f909f8e79881dd689ddd3123ec76ce45b13f0708562` |
| recovery kernel | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| recovery initramfs | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |
| recovery control | `f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77` |
| recovery fetcher | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| recovery verifier | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| runtime manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| recovery trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| host verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |

Both AVB images are exactly 100,663,296 bytes. Both raw images are exactly
58,101,760 bytes. The generation record is 483 bytes and mode `0444`.

## Independent production outputs

The issuer published two separate ignored build roots:

- `build/stable-recovery-generation4-timeout-lattice-20260803-a`
- `build/stable-recovery-generation4-timeout-lattice-20260803-b`

`diff -qr` reported no difference, and every relative file was separately
checked with `cmp`. Within each root, the `a` and `b` raw twins match and the
`a` and `b` AVB twins match. The issuer also proved that the raw recovery is
unchanged and that normalized AVB information differs from generation 3 only
by the deterministic generation-bound salt and digest.

## Fail-closed policy

The new `headless-diagnostic-generation4-offline-v1` profile pins every exact
identity above and permits only `policy-preflight` and `artifact-preflight`.
Connected preflight and boot are rejected before host inspection. Mutation
tests replace each recovery, trust, manifest, host-verifier, and bundle identity
and require rejection.

`manifests/artifacts.tsv` records the canonical `a` AVB as an unbooted offline
artifact. `manifests/temporary-boot-images.tsv` remains unchanged and contains
no `allow` row. Artifact inventory is not boot authority.

## Verification

- The focused issuer, recovery-policy, and exact artifact-preflight suites
  pass.
- Complete local `scripts/host/test-repository-linux.sh ci` passes on the final
  implementation tree.
- The constrained Claude review first identified three test-strengthening
  opportunities: connected-preflight denial, generation-4-owned mutation-field
  metadata, and explicit predecessor-generation distinction. All three were
  added; focused tests pass and the follow-up review reports `NO FINDINGS`.
- GitHub Actions run `30786957283` passes both `qemu-system` and
  `recovery-core` at exact implementation commit `e3a47a8`.

## Scope

No ADB, fastboot, ACM, NCM, SSH, signing credential, administrator credential,
phone reboot, phone boot, NFS startup, COMMIT, target execution, or phone
storage access occurred. This result authorizes no phone action. A later live
profile and one-row temporary-boot admission require their own reviewed change
and green local/GitHub CI at the exact commit.
