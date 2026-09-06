# Generation-9 recovery-ACM-classifier successor — offline

Date: 2026-08-03

Result: **PASS offline issuance and immutable profile; unbooted and not
admitted**. Two separate issuer invocations on this host produced
byte-identical Generation-9 wrapper trees. Only the outer AVB generation
identity changed; the audited raw recovery and every recovery component remain
unchanged.

## Exact identities

| Item | SHA-256 |
| --- | --- |
| Generation-9 AVB image | `b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008` |
| AVB-generation record | `29beac5ec4ef88194927283a45427fcc89b95f94c4afa4fda9d6b24301fc9961` |
| AVB salt | `4ddc34b9dace6d11338be71dba16797ff38e8f8e9e572cd61a6b1434c18b59df` |
| AVB payload digest | `8c97c36eed4dab241bc3353b8f70dc0ece8301fb795362cb129fe331af6c8dc0` |
| Canonical generation-zero source AVB | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| Unchanged raw recovery | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| Unchanged recovery kernel | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| Unchanged recovery initramfs | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |

The retained trees are:

- `build/stable-recovery-generation9-acm-classifier-20260803-a`; and
- `build/stable-recovery-generation9-acm-classifier-20260803-b`.

All 11 retained files are byte-identical across the two trees. The A/B AVB
wrappers and raw images are also identical within each tree. Pinned `avbtool`
verifies the exact `NONE` descriptor, `boot` partition, image geometry, salt,
and digest. Both generation records retain `authority=none`.

## Offline profile and authority boundary

`headless-diagnostic-generation9-offline-v1` pins the complete recovery,
component, signed-bundle, trust-root, manifest, host-verifier, generation
record, salt, and digest tuple. It permits only `policy-preflight` and
`artifact-preflight`. Connected `preflight` and `boot` reject before host or
phone inspection even if every live guard is supplied. The prospective
`headless-diagnostic-generation9-live-v1` name is also rejected as unsupported.

The artifact inventory contains one exact `unbooted`, `authority=none`,
`never flash` row. `manifests/temporary-boot-images.tsv` remains header-only,
with no Generation-9 row and zero active `allow` rows. No Generation-9 live
profile or lifecycle selection exists. This checkpoint cannot boot the phone.

Adding the inventory row intentionally advanced the integrity chain:

- artifact manifest: `38c0b9b5fa9a14a46590939c468f598fa2cbd52680e71be33e2a16dba81068bc`;
- minimal-headless compatibility profile:
  `1e24f71e5b3bbce32585fcad4c287b691ece9b054d0c0b09fbc9fa85e7745b17`;
  and
- source/DT contract profile:
  `1c1b6b4839336eadbfc1b16a45d22560560b2229d2993845cb1155f475383977`.

## Verification

- deterministic issuer regression through Generation 9: pass;
- two separate host-local production issuer invocations: pass;
- exact 11-file cross-tree and within-tree twin equality: pass;
- unchanged raw recovery and non-reuse of Generations 1–8: pass;
- exact five-field policy mutation matrix: pass;
- offline connected-action rejection before host inspection: pass;
- artifact preflight against both retained trees: pass;
- mutated generation-record rejection: pass;
- unissued Generation-9 live-profile rejection: pass;
- stable-recovery live-gate suite: pass;
- 39 compatibility-oracle tests: pass;
- 74 source/DT contract tests: pass with one expected optional-source skip;
  and
- recovery inventory and issuer suites: pass.

No phone command, reboot, connected-device inspection, privilege, network
listener, NFS export, or phone-storage access occurred. The project recovery
signing operation produced only the two retained host-local wrappers. Private
key material remains outside Git.

Exact-head GitHub CI must pass this offline issuance first. A subsequent
reviewed change may create a live lifecycle profile while keeping central boot
policy empty. A still-separate change must admit one exact temporary lifecycle
before any connected preflight or RAM-only boot.

That exact-head gate passed in GitHub Actions run `30841980164` at commit
`6193056`. The subsequent
[live-profile transition](2026-08-03-generation-9-live-profile-offline.md)
selects the identical tuple without adding central boot authority.
