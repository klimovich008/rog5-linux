# Steam Deck host setup

The Steam Deck is an x86_64 cross-build and analysis host. It is not the
target, and this host setup performs no phone, signing-key, credential, or raw
storage action.

## First verified state

Use Desktop Mode on a native Linux filesystem with at least 40 GiB free. Git,
Python 3, and rootless Podman are required; unlocking SteamOS or installing
packages with `sudo` is not required.

From the public repository:

```sh
scripts/host/bootstrap-kernel-builder.sh build
```

This builds the accepted Ubuntu 24.04/Clang 18 environment from pinned image
manifests, the Ubuntu `20260728T000000Z` snapshot, and the tracked 247-package
closure. Verify an existing image without network access:

```sh
scripts/host/bootstrap-kernel-builder.sh verify
```

On the qualified Steam Deck host, apply the stronger host profile:

```sh
scripts/host/verify-steam-deck-builder.sh
```

That profile pins the current reproducible rootfs identity and the
byte-identical ASUS 5.4 oracle proof. It does not replace the frozen
historical profile; see the
[qualification result](../test-results/2026-07-30-steam-deck-asus-builder-qualified.md).

If a normalized rootfs identity ever differs, emit the underlying
file-content and metadata stream for a direct diff:

```sh
scripts/host/bootstrap-kernel-builder.sh manifest \
  localhost/rog5-kernel-builder:ubuntu-24.04
```

The manifest action runs offline and does not modify the image. Archive a
manifest alongside each newly qualified builder result; a hash without its
manifest is insufficient for diagnosing a future host-runtime difference.

Do not substitute the older unpinned `rog5-kernel-build:clang18` migration
image. Historical object trees can contain its paths and binaries, but they
are evidence rather than resumable build directories.

## ASUS 5.4 source

The private host workspace may retain ASUS's official
`ASUS_I005_1-33.0210.0210.200-kernel-src.tar.gz` archive. Its required
SHA-256 is:

```text
3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8
```

The pinned ASUS download URL is:

```text
https://dlcdnets.asus.com/pub/ASUS/ZenFone/ZS673KS/ASUS_I005_1-33.0210.0210.200-kernel-src.tar.gz
```

After extraction and the six tracked patches, verify the complete source
directory before use:

```sh
scripts/host/verify-asus-source-tree.py \
  ../kernel-src/msm-5.4
```

The verifier checks the canonical profile and seal-tool identities, exact
patch marker, every tracked patch hash, and all 79,030 source entries by path,
type, permission mode, file content, and symlink target. The accepted result
is:

```text
tree_bytes=1182067858
tree_sha256=592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
```

Ordinary copy tools can preserve file bytes while normalizing `0664/0775`
modes to `0644/0755`; that is not the accepted tree. Never update the expected
seal to accommodate a transfer. Reconstruct from the pinned archive and
patches instead.

Current wrapper scripts consume the source through the rootless Podman volume
`rog5-asus-v12a-source`. Import a verified host directory into a new,
previously absent volume:

```sh
scripts/host/import-asus-source-volume.sh \
  ../kernel-src/msm-5.4
```

The importer refuses an existing volume, requires rootless Podman, resolves
the exact local-volume mountpoint below Podman's graph root, copies source
metadata directly, reseals the copy with the host verifier, and labels the
new volume with a random per-import ownership token. Failure cleanup removes
the volume only while that token still matches, so it cannot remove a
same-named replacement. It deliberately has no kernel-builder image
dependency.

## Regression gate

Run the hardware-free repository suite before selecting any live candidate:

```sh
scripts/host/test-repository-linux.sh ci
```

Large kernel builds should use new ignored output directories. Generated
`wrapper-*-output` trees copied from another host contain stale absolute paths
and host helper binaries; do not resume them.

Phone access, temporary boot, production signing, and private deployment keys
remain separate attended gates. Host readiness never grants authority for
those actions.
