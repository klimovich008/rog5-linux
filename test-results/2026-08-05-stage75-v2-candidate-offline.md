# Stage-75 v2 pre-single-attempt composition — superseded offline evidence

Date: 2026-08-05
Result: HISTORICAL PASS offline; superseded; `authority=none`; not boot-authorized

## Purpose

Record the first stage-75/postmortem v2 composition without changing or
relabeling the immutable v1 bundles used by consumed diagnostic Generations
0–12. This tuple predates the exact-one-attempt NFS and exact-UDC corrections;
it is not the current write-side candidate.

No production credential was used. No phone was inspected, rebooted, or
booted. No boot-policy row was added. The generated private Ed25519 key was
disposable and the builder destroyed it after completing the twin proof.

## Candidate contract

- candidate, bundle, and target ID:
  `headless-netroot-early-diag-v2`
- wire/runtime profile: `diagnostic-initramfs-v1`
- historical candidate record: 1,411 bytes,
  `80b7c3aa1892526e97da40c47de6503a931c4e3de6ed096a9a4b62fd177feba3`
- Linux 7.1.4 Image: 40,049,152 bytes,
  `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`
- corrected accepted DTB: 102,870 bytes,
  `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`
- superseded pre-single-attempt initramfs: 6,011,332 bytes,
  `4bfc16ae341d4e186dfdb86fbe4b4ab7fb7646b966f9e99a0a2db52d3dc37e04`
- signed manifest: 834 bytes,
  `2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156`

The superseded reporter is 67,288 bytes at
`dc53932d6275180fa71972ceed0ae409bd4ae1604fca8befd9f030d476583a10`.
The archive identity changes because the admitted bundle/target identity is
now v2. Recovery retains v1 read compatibility only for historical evidence;
current production and offline builders emit v2.

## Deterministic twin build

Command:

```sh
scripts/host/build-corrected-headless-candidate-offline.sh \
  --candidate headless-netroot-early-diag-v2 \
  --expected-target headless-netroot-early-diag-v2 \
  build/stage75-v2-offline-20260805-a
```

Both clean ASUS-wrapper builds were byte-identical. The exact retained
offline identities are:

- disposable raw Ed25519 public key: 32 bytes,
  `58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268`
- stable-recovery initramfs: 7,596,405 bytes,
  `a38b61462468272c8d8409461d7318cfc442c3a4707a624e9f8ab1751ef047a4`
- ASUS 5.4 wrapper Image: 50,498,048 bytes,
  `7a6c2a19c7a00a2699fd598b4fc3ad5fed680bf2cd9cb7cfa7bafa783d9fe563`
- raw boot wrapper: 58,101,760 bytes,
  `406b2497bff8174b01119e4bcfa4dddb544df3de8fdb9168d80e88708f20a995`
- unsigned AVB wrapper: 100,663,296 bytes,
  `833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de`
- AVB salt: raw-wrapper SHA-256 above
- AVB digest:
  `a1d19575dd21b6da3fd3cbb6c0f4ea33e312cc59ddc860889f1f54ef976e7b49`

Recovery components are pinned at control `242ac7fc…149e7`, fetcher
`77eff28d…fe800`, target verifier `5f3a47bb…4a6e0`, and host verifier
`0a570805…b621`.

## Gate result

Historical profile
`headless-diagnostic-stage75-v2-superseded-offline-v1` pins the complete old
tuple and accepts only `policy-preflight` and `artifact-preflight`. Both pass
against the retained ignored build tree. Connected `preflight` and `boot`
reject before host or phone inspection. The profile name makes it impossible
to confuse this evidence with the current corrected candidate.

The artifact preflight independently verifies:

- both recovery initramfses, wrapper kernels, raw images, and AVB images are
  byte-identical;
- every component, config, trust root, manifest, and wrapper identity;
- the shell-free stable-recovery archive contract;
- native signed-bundle verification and exact v2 target plan;
- AVB footer/hash descriptor and raw boot-image structure; and
- the pinned qualified `cpio`, `avbtool`, and unpacker inputs.

## Disposition

HISTORICAL PASS for the superseded offline composition only. This artifact is
intentionally absent from `manifests/temporary-boot-images.tsv`, has no
production trust root, and must not be booted or flashed. The active corrected
candidate uses the 6,011,687-byte initramfs
`71537ca0cfdfcf8f7dbf26cc2eb6585bac025bea08526a7e22d62df60fa0c58e`,
the reporter `0b5d318e…7bc1`, and candidate record `f7752e30…9157`; it remains
unissued and has no signed wrapper or boot authority.
