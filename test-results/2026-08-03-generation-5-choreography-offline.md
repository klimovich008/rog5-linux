# Generation-5 host-choreography recovery — offline issuance

Date: 2026-08-03

Result: **PASS offline**. Two independent Generation-5 issuances produced
byte-identical output trees over the unchanged verified recovery payload. The
exact artifact passes the complete phone-free stable-recovery gate under an
offline-only profile. It is inventory-only, absent from temporary-boot policy,
and has no live or phone authority.

## Purpose

Generation 4 was consumed after its sole RAM-only cycle. The subsequent
host-side correction now covers the exact PREPARED/control-exits-first stall,
automatically restores and proves fallback on anchored pre-intent failure,
keeps the collector alive until that proof, flushes PREPARED before the NFS
gate, and emits non-authoritative artifact progress. The corrected source and
installed host paths pass hardware-free and real host preflights.

Generation 5 changes only the deterministic AVB generation identity. It does
not alter the recovery kernel, raw wrapper, initramfs, control responder,
fetcher, verifier, trust root, runtime bundle, target kernel, DTB, or target
initramfs.

## Exact identities

| Item | SHA-256 |
|---|---|
| unchanged raw recovery | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| canonical source AVB | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| Generation-5 AVB | `abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a` |
| Generation-5 record | `7d1a1071df1dcc4172c9f1e28ab5b62d6c44670b21f075f775de587f789cf98f` |
| canonical AVB salt | `818427845bc55deb8167fbb205fb672f2edfb3b465160109dacc0f4d65a9f306` |
| AVB payload digest | `b1a6bb43d26230e3c623332703998459d51b37fc8244c051287c8291f9e213b0` |
| recovery kernel | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| recovery initramfs | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |
| runtime manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| recovery trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| host verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |

Both AVB images are 100,663,296 bytes, and both raw images are 58,101,760
bytes. The generation record says `generation=5` and `authority=none`.

## Independent production outputs

The issuer atomically published two separate ignored roots:

- `build/stable-recovery-generation5-choreography-20260803-a`
- `build/stable-recovery-generation5-choreography-20260803-b`

`diff -qr` reported no difference. The issuer separately proved that both raw
twins remain unchanged, both AVB twins match, the output differs from
Generations 1–4, and the descriptor digest binds the canonical salt plus the
raw image.

## Fail-closed policy and tests

The new `headless-diagnostic-generation5-offline-v1` profile permits only
`policy-preflight` and `artifact-preflight`. Both connected preflight and boot
fail with the offline-only reason before host inspection. The mutation matrix
replaces each recovery, trust, manifest, host-verifier, and bundle identity and
requires rejection. `manifests/artifacts.tsv` records one exact inventory row;
`manifests/temporary-boot-images.tsv` remains unchanged and contains no
Generation-5 row.

The changed artifact-manifest identity is explicitly repinned through the
minimal-headless compatibility profile and its source/DT contract. All 39
compatibility-oracle tests and all 74 source/DT tests pass.

Focused issuer, recovery-policy, stable-recovery-gate, compatibility, and
source/DT tests pass. Complete local
`scripts/host/test-repository-linux.sh ci` passes on the implementation tree.
A bounded, tool-free, non-persistent Claude Opus review checked the offline
authority separation, exact pins, predecessor distinction, compatibility
propagation, refusal ordering, mutation coverage, and shell behavior and
returned `NO FINDINGS`.

Publication and GitHub Actions evidence remain to be added. No ADB, fastboot,
ACM, NCM, SSH, signing key, administrator credential, phone reboot, phone
boot, NFS startup, payload transfer, COMMIT, target execution, or phone-storage
access occurred. A separate one-row temporary-boot admission remains required
before connected preflight or a single temporary boot.

The separate
[live-profile transition](2026-08-03-generation-5-live-profile-offline.md)
now wires the lifecycle to the same exact tuple without adding boot authority.
Only the one-row temporary-boot admission remains before connected preflight.
