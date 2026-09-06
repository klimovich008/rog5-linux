# Stable-recovery wrapper cache

The stable-recovery cache removes the slowest repeated host-only step without
weakening the release gate. It stores a wrapper only after two clean ASUS 5.4
kernel builds, two raw boot repacks, and two unsigned AVB test repacks match
byte-for-byte and pass the existing structural checks.

The cache is an optimization, not evidence of phone compatibility. It never
uses `fastboot`, ADB, SSH, a signing credential, elevated privilege, phone
storage, or a network client.

## Identity

The input key binds:

- the canonical cache profile;
- the ASUS source archive and marker identities;
- a portable seal of every source path, type, permission mode, file size and
  content, and symlink target;
- the source-seal implementation;
- reference and resulting wrapper configurations;
- the exact recovery initramfs;
- kernel build and boot repack scripts;
- boot-v3 template, `mkbootimg`, `unpack_bootimg`, and `avbtool`;
- builder image ID, digest, compiler, partition size, and command-line policy.

`kernel-source-seal.py` deliberately excludes host UID, GID, timestamps, link
count, and xattrs. Those are reconstruction-host properties and are not kernel
build inputs. Modes, content, paths, and symlink targets remain identity
inputs. It detects source changes during traversal and rejects special files,
linked roots, cross-filesystem traversal, and symlink-following file opens.

The output entry ID is the SHA-256 of a canonical manifest that adds the exact
configuration, kernel Image, build metadata, initramfs, raw boot image, and AVB
image sizes and hashes.

## Publication contract

`test-stable-recovery-wrapper-offline.sh` performs these operations in order:

1. seal the source and derive the exact input key;
2. build the vendor wrapper twice in separate output roots;
3. require byte-identical configs, Images, metadata, and embedded initramfses;
4. repack and structurally inspect both raw boot-v3 images;
5. verify both fixed-size unsigned AVB test images;
6. reseal the source and require the seal to be unchanged;
7. atomically publish one immutable content-addressed entry.

One exact input key can bind to only one output entry. A concurrent or later
attempt to publish different output bytes for the same inputs fails closed.
Entries and bindings are owned by the invoking user, private, single-link,
read-only files. Publication and binding use `renameat2(RENAME_NOREPLACE)` and
directory `fsync`.

The complete twin build remains mandatory for a new cache entry. A cache hit
must never be used to claim that changed source, tooling, configuration, or
initramfs output is reproducible.

## Materialization

Materialization is intentionally explicit:

```sh
scripts/host/materialize-stable-recovery-wrapper-cache.sh \
  path/to/rog5-stable-recovery.cpio.gz \
  build/stable-recovery-wrapper-cache \
  EXPECTED_64_HEX_ENTRY_ID \
  build/materialized-stable-recovery
```

The wrapper:

- recomputes the portable ASUS source seal in the pinned, network-disabled
  builder;
- validates all input hashes and the builder ID/digest;
- requires the caller-supplied entry ID and its exact input-key binding;
- rehashes the manifest and every cached file;
- requires an absent ignored output directory below `build/`;
- publishes the materialized directory atomically without replacement.

The result contains `wrapper.Image`, `wrapper.config`,
`wrapper.build-meta`, `recovery.cpio.gz`, `stable-recovery.raw.img`, and
`stable-recovery.avb.img`. It does not compile a kernel.

## Trust and retention

The first retained entry proves the mechanism with the already accepted
corrected-headless twin build. Its initramfs embeds a public key whose
disposable private counterpart was destroyed after that build. The entry can
therefore reproduce and inspect the historical wrapper but cannot sign a new
runtime bundle.

A future operational stable-recovery entry needs an admitted production trust
root. The central standing authorization covers credential use and an admitted
temporary boot, but they remain distinct technical gates. The cache itself
grants neither action.

Keep the compact cache entry, profile, source volume, builder image, tracked
tools, and redacted proof. Materialized copies and broad kernel object trees
may be removed after their exact entry and reconstruction proof are recorded.

See the
[offline cache proof](../test-results/2026-07-30-stable-recovery-wrapper-cache.md)
and the
[original twin-build proof](../test-results/2026-07-29-corrected-headless-candidate-offline.md).
