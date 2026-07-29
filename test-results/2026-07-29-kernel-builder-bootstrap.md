# Pinned kernel-builder bootstrap acceptance — 2026-07-29

## Result

**PASS — the Linux v7.1.4 source identity and x86_64 kernel-builder
environment are reproducible from pinned public inputs on rootless Podman.**

This is a PC-only infrastructure result. No phone was contacted, no
credential was used, no signing authority was created, and no boot, flash,
wipe, storage, or recovery action was performed.

## Accepted inputs

- Linux tag: `v7.1.4`
- annotated tag object:
  `114456a9c542d933387517bb22561668c25a5b59`
- peeled commit: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
- source tree: `2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9`
- Ubuntu 24.04 amd64 base:
  `sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90`
- Fedora 44 amd64 CA-bootstrap image:
  `sha256:89f61a124414261868224666aa7fb8df1b78397a53623774bdfb105d1612b48b`
- bootstrap CA bundle:
  `00411c197b16f659945fba3c2f970a26030f56eef5d445c913cb59a089c813b9`
- Ubuntu snapshot: `20260728T000000Z`
- historical snapshot expiry handling: `Check-Valid-Until: no`
- complete 247-package closure:
  `9dce7979f2b55e0f56c6dd803986d127107e5a7ead15cd69e780aebaccacc101`

## Test-first contract

`scripts/host/test-kernel-builder-bootstrap-contract.sh` first failed on the
missing Linux bootstrap. Its accepted form checks the exact image/snapshot/
lock inputs, sorted unique package closure, rootless/no-sudo/no-phone host
boundary, offline final-image verification, and normalized rootfs comparison.

The source fixture creates an annotated local Git tag, verifies a valid
tag-object/commit/tree tuple, then changes the expected tag object. The
changed identity is rejected before the target source obtains a checked-out
`HEAD`.

## Independent build evidence

Host:

```text
Podman 5.8.4
rootless=true
Nobara 44 amd64
```

The first snapshot fetch transferred about 32 MiB of indexes and 218 MiB of
packages. Canonical's snapshot service was the dominant cold-bootstrap cost.
Normal builds reuse a verified download cache. The accepted reproduction
path instead assigns separate initially empty cache namespaces to its two
builds.

Two no-layer-cache builds with independently fetched snapshot caches produced
the same complete root filesystem:

```text
first_image_id=c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec
second_image_id=9c97545be6ee9eb76979eb6475ef527e8c19a6124ab277212c8622f3a5482aa1
rootfs_identity=2eb07c8a9a4895530ab092ed43e8a953b428f7cd2315c63fa08cf1f9a83f13af
builder_recipe_sha256=28dca69fd5c7f0fb1cf3418fd5a8bc5d2d8d04cdd1cf09919667e32faefb54bd
```

Podman records each cache namespace value in OCI build history, so the image
IDs and digests intentionally differ. They are diagnostic metadata, not the
acceptance identity. The normalized rootfs identity covers file contents,
modes, owners, symlinks, and paths while excluding only runtime-injected
container filesystems and host-name/resolver files.

The final verifier ran with container networking disabled and reproduced the
entire installed package lock. Selected tools were:

```text
Ubuntu clang 18.1.3
Ubuntu LLD 18.1.3
ccache 4.9.1
pahole 1.25
```

The accepted image then compiled a real minimal ARM64 Linux kernel with
container networking disabled:

```text
config_sha256=24e70400094f99d4a56d9cc5f629681a3d9552c7a79c630d23c6bcc27aec95d9
image_sha256=346b620bbe40e2d82097e2234d4ccaeedc88b8902cb4c346211fca420bf4dd9c
```

The Image matches the previously accepted clean/cached/incremental toolchain
proof. The host does not currently provide `qemu-system-aarch64`; the hosted
CI QEMU job remains the full-system kernel-to-initramfs boot gate.

## Claude advisory review

Claude Code `2.1.220` passed separate Haiku and Opus connectivity prompts.
The original broad 37 KiB Opus review reached its fixed timeout without
output; authentication remained healthy, and the timeout produced no
security or authorization diagnostic. A targeted core review completed and
identified the snapshot-expiry, cache-independence, source-rejection, and
package-state issues corrected above. A second targeted Opus review of the
corrected patch returned `NO_BLOCKERS`.

The wrapper remained safe-mode, tool-free, nonpersistent, stdin-only, and
time-bounded throughout. It now reports timeout status explicitly and
instructs future reviews to use smaller self-contained slices. Claude's
output was advisory and made no repository changes.

An initial same-cache diagnostic localized its only content difference to
generated `/var/cache/apt/pkgcache.bin`. Removing that non-runtime APT cache
made the rootfs deterministic. The later separate-cache proof above confirms
that result without sharing downloaded indexes or packages; package logs and
`ldconfig`'s generated auxiliary cache are also excluded from the final
image.

## Meaning and limits

This accepts the public Linux source and PC toolchain bootstrap. It does not
claim that an upstream SM8350 DTB is safe for the ASUS phone, that the
corrected ASUS DTB has passed live hardware, or that Android boot-image tools
are fully pinned. `mkbootimg`, `avbtool.py`, the disposable test trust root,
and the corrected candidate's duplicate build remain separate gates.
