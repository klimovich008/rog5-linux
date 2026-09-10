# Headless-core successor candidate — offline

Date: 2026-07-30

Result: **PASS hardware-free; unbooted; authority=none**

## Outcome

The sealed `headless-core-v2` Arch root is now a complete recovery candidate
without changing the accepted SSH-only root or the `network-root-v1` wire
protocol. The host package format advances to v2 so it explicitly binds
`build_profile=headless-core-v2`; the candidate has a distinct ID and target
and selects the buttons/default-off status-LED DTB.

No phone, fastboot, ADB, SSH credential, production signing key, reboot,
mount, flash, or physical storage action occurred.

## Root and package identities

```text
source_root_size=535163814
source_root_sha256=f52bd75f023ab6209a04f842881356e5a224e1e1845f1d5732ab71da7d36e66b
dense_network_source_size=536070124
dense_network_source_sha256=86e2b3bfdd057e9b7bb98963eb419c839641b63d8d21ec8d3bd84c5c1b8d18f1
sealed_archive_size=534347412
sealed_archive_sha256=f8ec3bd739ab96b8559f20da4e971e4c01fadaec86f8610036c084cd78019f64
package_manifest_size=654
package_manifest_sha256=c0cca453edf7ccd5c0cc61c1ff5d9087e3f70df4eb02defcb92c34da2e49abd0
root_tree_entries=37675
root_tree_sha256=c00fbf419f64b41690aa66c9c5b627e78990b367be320f13b04ff1cf5e7af17d
root_seal_sha256=96c9ff3584d65e21c0307cd065ca28babf8f9c3ad708034965c85e3788de1e22
```

The original root archive encoded the static indicator with a GNU sparse
member. The generic persistent-root validator correctly refused it. The
normalizer sealed and archived the exact pinned source root before creating
any verifier mountpoints, generated two byte-identical dense archives with
libarchive `--no-read-sparse`, and rejected sparse members with the existing
validator. A separate comparator proved that all 37,674 source members,
hard-link groups, and both `nocow` inode flags were preserved. Re-extraction
and complete tree-seal comparison bound content, mode, owner, link, mtime,
and xattr after canonicalizing only the extraction-volume root mtime. Gzip,
archive comparison, and archive validation ran inside the digest-pinned
builder.

## Candidate identities

```text
candidate=headless-core-network-root-v2
profile=network-root-v1
target_id=headless-core-network-root
target_release=7.1.4-g7a5cef0db479
board_dtb_size=103554
board_dtb_sha256=57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d
runtime_manifest_sha256=f7316f6a02c041f345c4e079d93bccb8b1b566a6ecf3a9c16d16cc46a4affa32
ephemeral_trust_key_sha256=fb20058030351188f316928d8dceef633b380a50a4c30956bdcd91e4fb7cd872
authority=none
```

The runtime manifest is independent of the signing key. The listed trust key
was generated only for this offline gate. Its private half was mode-restricted
inside a temporary directory and destroyed before the gate returned success.

## Reproducibility and verification

| Gate | Result |
|---|---:|
| dense source archive twin build | byte-identical |
| source/normalized paths, hard links, and inode flags | identical |
| extracted source/normalized whole-tree seal | identical |
| v2 network-root prepare/package/clean-extract verify | passed |
| candidate/package/hash adapter tests | 7 passed |
| successor root hostile tests | 6 passed |
| archive semantic comparator hostile tests | 5 passed |
| signed runtime bundles A/B | byte-identical |
| native bundle verifier plans A/B | identical |
| shell-free recovery initramfs A/B | byte-identical |
| clean ASUS kexec-wrapper kernels A/B | byte-identical |
| header-v3 raw wrappers A/B | byte-identical |
| test-only AVB wrappers A/B | byte-identical and verified |
| disposable private key cleanup | passed |

Key wrapper identities:

```text
stable_recovery_initramfs_sha256=05e19c6cc15da83a83dc39e5a1a5c3f5bb293e23d710b6d585fe1c102828bb13
wrapper_config_sha256=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
wrapper_image_sha256=934f95b029e8274be71a0a99b76ead05d59051085fbf5603c134fa93f541af41
raw_wrapper_sha256=e9d68e2740b0c3ef4d14cf9376eaf82901c5bf9ec30716b6725552f7749d9323
test_avb_wrapper_sha256=f1e90936b4def0a3289c2270389cd88b41288d28c4323cda77b1c3f423f26918
```

## Claude advisory review

The final constrained Opus review returned `BLOCKERS: NONE`. It confirmed
that the corrected implementation excludes verifier mountpoints from the
archives, preserves hard links and inode flags, runs archive tooling inside
the pinned builder, validates the complete candidate tuple, scans the shared
builder for transport, publishes without replacement, and tests hostile v1/v2
package substitutions. Its two non-blocking least-privilege and clarity
suggestions were also applied: tree sealing no longer receives an unused
writable output mount, and the structural comparator documents the separate
whole-tree seal coverage.

## Remaining boundary

This result does not authorize a live signing key or a phone boot. The next
live step, if separately approved, is one attended temporary-boot cycle with
strict storage isolation, rollback, host-key pinning, SSH/runtime collection,
physical power-key/LED observation, exact fallback proof, and no retry after
an unknown transport outcome.
