# A660 registration v2 — v21 acceptance re-lock and export

Date: 2026-07-26

Result: **PASS offline. The exact accepted v21 idle-SMMU result is now
hash-pinned into the A660 registration probe, a new independently verified
root-owned v2 export replaces the old `NOT_ACCEPTED` runtime path, and the
unchanged kernel/DT/module/wrapper/AVB package passes its complete exact
verifier. The phone was not contacted, NFS remained inactive, and nothing was
booted or flashed.**

This is not a live A660 registration result and does not accept firmware,
first DRM open, rendering, display, suspend, or acceleration.

## Fail-first boundary

Tests were changed before implementation. They rejected the old control plane
at four independent boundaries:

```text
FAIL attended A660 registration probe omits: smmu_acceptance_sha=c5c97d...
FAIL A660 export path omits: /var/lib/rog5-network-root-a660-registration-v2
FAIL A660 registration bundle verifier omits: verify-adreno-smmu-v21-live-acceptance.sh
FAIL network-root host contract missing: /var/lib/rog5-network-root-a660-registration-v2)
```

The new acceptance verifier itself first failed because it did not yet exist:

```text
FAIL missing v21 live-acceptance verifier
```

After implementation, the positive and mutation suites pass. They reject a
modified live report, modified marker, linked marker, old `NOT_ACCEPTED`
probe, old export root, and every consumed v20/v21 server path.

## Exact predecessor acceptance

The committed live report is:

`test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md`

SHA-256:

`0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc`

The new nonsecret acceptance marker is:

`manifests/acceptance/adreno-smmu-v21-live.accepted`

SHA-256:

`c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875`

It pins:

- candidate checkpoint
  `327dfb12142fabb616ffa91fdcf84dc74654e4ba`;
- evidence checkpoint
  `8b4bad817686a690a5aeb6ca27b043aee119a14c`;
- exact temporary-boot image
  `37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf`;
- one GPUCC bind and one exact-device SMMU reprobe/bind;
- `arm-smmu` at runtime suspend;
- exact unset-null override representation;
- zero firmware, render, storage, mounts, and failed units;
- passed fallback and host cleanup;
- v21 reuse forbidden; and
- no flash.

The verifier result is:

```text
PASS exact v21 live acceptance report=0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc marker=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875 scope=idle-smmu consumed=yes flash=none
```

## Registration probe lock

The probe no longer contains `NOT_ACCEPTED` or references the obsolete v18
boundary. It requires the exact marker at:

`/.rog5/root-ro/etc/rog5/adreno-smmu-v21-live.accepted`

This is the immutable read-only NFS lower, not the writable OverlayFS view or
a mutable `/run` file. The probe requires a regular non-link file owned by
root with mode `0444` and the exact marker SHA-256 before arming or loading
any module.

Probe SHA-256:

`5439c8c431432ecd3c7c50e9d0124e71f986f09f844518bde0ec1d01b0692dca`

Probe-test SHA-256:

`2c4ba542a45388743f2532f38e34b4c16be55e1684216a9712a2fabbde6809ee`

The remaining registration boundary is unchanged: seven manually ordered
modules, GPUCC first, MSM last with `separate_gpu_kms=1`, no DRM file
descriptor, no firmware file/request, zero physical storage and block-backed
mounts, independent SysRq watchdog, and fail-closed thermal/kernel-log checks.

## Unchanged binary package

No kernel, config, DT, module, target initramfs, nested stage, ASUS wrapper, or
Android boot-image input changed. Recompiling would therefore create no new
reviewable behavior. Instead, the full exact verifier rechecked the existing
independently reproduced build and all fourteen package files against their
accepted hashes, then added the v21 report/marker and new probe/export
contracts.

It returned:

```text
PASS exact v21-accepted A660 registration bundle; four nodes, seven modules, zero firmware/storage/display, reproducible and offline-only
```

Key unchanged identities:

| Output | SHA-256 |
|---|---|
| Linux Image | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| module archive | `e3cb1ef31b6c1c803bee98748660f92b3b192d460cb41d5d4691f9953a91a42b` |
| registration DTB | `b96f4350b35ff3bfc987ce97828e22bd7136100323752c2ac68c537580bd35d6` |
| nested stage | `8275e22dc5e2894c5bb73bcf25c989c475b6a7e28a6da13b5aa0741e5eb75722` |
| ASUS wrapper | `763aae44f04840d6c151baa068bb83e874f9d32aea0023fc6a7eb8c89f975276` |
| raw boot image | `1f98e136913a924e6338c6b7bfc3fb925146f00efd3c77e1192f4e25c0be26bb` |
| temporary-boot AVB image | `c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c` |
| fourteen-file manifest | `c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0` |

## New isolated export

PolicyKit created:

`/var/lib/rog5-network-root-a660-registration-v2`

The old source-locked
`/var/lib/rog5-network-root-a660-registration` remains preserved but is not
server-allowlisted.

Two independent verifier invocations, including one through the full host
test with actual root paths, returned:

```text
PASS v21-accepted A660 registration v2 export modules=7 firmware=0 credentials=preserved base=unchanged
```

The v2 root and seal state is:

- export root: root-owned mode `0555`;
- seal: root-owned mode `0444`, SHA-256
  `62fef7c7adeb9463e8c3a4edc76af44bcdd8aadf6458df1a25bac140987b6b7a`;
- acceptance marker: root-owned mode `0444`, exact SHA-256
  `c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875`;
- exactly seven matching modules;
- zero A660 firmware;
- existing SSH authorization and host identity preserved byte-for-byte;
- unchanged accepted v1 base; and
- v2 registration generation plus accepted-idle-v21 seal fields.

The generic NFS server now accepts only the persistent v1 root and the new
A660 registration v2 root. It rejects consumed v20/v21 SMMU roots and the old
A660 registration root. NFS remained inactive with no export.

## Next gate

The binary/control-plane/export tier is eligible for a new offline
one-shot-runner review, not yet for an immediate device action. Before one
registration-only RAM boot, the project still needs:

1. an atomic host/target launcher with exact artifact, export, SSH, watchdog,
   evidence-directory, and one-invocation contracts;
2. a transition watchdog that remains rollback authority through normal
   reboot;
3. exact persistent-fallback and complete host cleanup verification; and
4. a final clean synchronized Git and inactive-NFS preflight.

The eventual registration cycle must never be retried. It may register a
headless render node but must not open it. Firmware loading, GMU resume/HFI,
ZAP/SCM authentication, first DRM open, rendering, display, suspend, and
accelerated desktop remain later gates.
