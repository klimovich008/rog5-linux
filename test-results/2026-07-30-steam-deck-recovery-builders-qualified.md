# Steam Deck ARM64 recovery-builder qualification — 2026-07-30

> Historical identity note (2026-08-01): the runner and profile hashes below
> describe this original qualification. Later private-runner hardening changed
> the runner to
> `4437422db78d196d6992fa53b006ebde68efb6d6dc8700ee91ccb46af2a3b621`.
> The repaired current profile is
> `780d564013d30c278b709939db6402347243eb2866065c6cbbe1788a946b842f`
> and now cross-checks the live runner in both the verifier and hostile
> contract. The current qualification and reconstruction evidence is recorded
> in the [diagnostic candidate result](2026-08-01-early-target-diagnostic-candidate-offline.md).

## Result

**PASS — both Alpine ARM64 recovery builders run rootlessly on the x86_64
host, reproduce their pinned filesystem/package identities, and emit the
accepted recovery binaries.**

This was a PC-only, network-disabled qualification. It used no root password,
phone, ADB, fastboot, SSH credential, signing key, private input, or external
service. It grants no boot, flash, signing, storage, or deployment authority.

## Why this was needed

The post-cleanup host no longer had a privileged `binfmt_misc` registration.
The recovery components are built in ARM64 Alpine images, while the
development PC is x86_64. A fixed `qemu-aarch64-static` is now extracted from
the already qualified historical builder and invoked through a private
rootless runner. The runner does not alter host kernel state and therefore
survives reboots without requiring `sudo`.

## Pinned emulation

```text
source image:  localhost/rog5-kernel-builder:historical-20260724
QEMU size:     6,245,816 bytes
QEMU SHA-256:  bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec
runner SHA-256:
972831d9c4bde3c440e905bdb7beac6b3e74a0a02dc04d0eeb1060c6bfaeb50d
sealed-memfd runner SHA-256:
354ea9b62a7ec9f19501858e3e0d2c4f848faa93e639dccc36bb23f5a016c301
extractor SHA-256:
5b0e991cb1112b21f5c40c8e1504020d8638ac6bff611964c96059d658cd6ecd
profile SHA-256:
18fc6f392d4a84cf15eab867de89b7a8760c54568793d5fe07f5a50725402278
```

`scripts/host/extract-qualified-qemu-aarch64-static.sh` refuses a changed
source image, linked input, path traversal, symlink-parent escape, wrong size,
wrong digest, or conflicting output. `scripts/host/run-private-arm64-binfmt.sh`
requires a rootless user namespace with private mount propagation, pins the
emulator bytes in a write/grow/shrink/seal-protected `memfd`, and registers
that same verified descriptor on a private `binfmt_misc` mount. The runner
refuses to operate if a host AArch64 handler exists, making successful ARM64
execution evidence for the private handler rather than a host fallback. It
does not register a system-wide binary handler.

## Qualified builders

| Role | Image ID | Image digest |
|---|---|---|
| responder/fetcher/indicator | `a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e` | `sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa` |
| signed-bundle verifier | `13d758cd4c708ddb798dd539d1b6c4e3546ea5ef9129ed309c74bd8f4e620689` | `sha256:75f5179fe0164ffefa2f9bc5dba5a47eac47674d347311602256476aa2ee7a01` |

The profile pins the ARM64 base-image digest, recipes, complete normalized
root filesystem inventories, package inventories, and expected binary
outputs. Independent live inspection reproduced:

```text
responder rootfs:
89fde8f4651efe47ce5b2e78d44307520547f7e693ec8e2b2672e1a979119fcd
responder packages:
a0b976c4df8050064f88664f97c1762a11a32321a282b34c523c9e829d75334c
verifier rootfs:
e6ab755c445f3388ccc04717346337f65c8d24ee892e078977b6bbe99f0b26b3
verifier packages:
6b52a32d2720a6e9e391601f483f7f37c625667eb65e465a58a989350590c8ae
```

The accepted output identities are:

| Component | SHA-256 |
|---|---|
| `rog5-recovery-control` | `c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0` |
| `rog5-bundle-fetch` | `becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c` |
| `rog5-key-indicatord` | `3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8` |
| `rog5-bundle-verify` | `374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b` |

## Reproduction

```sh
scripts/host/extract-qualified-qemu-aarch64-static.sh
scripts/host/verify-steam-deck-recovery-builders.sh
```

The first command is idempotent and no-replace. The second requires both
images to exist locally, disables container networking, recomputes the live
root filesystem and package identities, and fails before accepting changed
images or manifests.

After the namespace/path hardening, the complete stable-recovery integration
was rebuilt through the updated runner with the finalized candidate's public
trust root. Both independent builds were byte-identical to the retained
candidate archive:

```text
stable recovery SHA-256:
ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04
public trust-root SHA-256:
ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb
```

Hostile contracts cover changed QEMU identity, traversal and symlink output
escapes, direct internal-branch invocation, missing private runner, profile
drift, wrong image architecture/identity, changed compressed or uncompressed
manifests, symlinked inputs, and missing success evidence.

## Limits

This proves the build environment and exact recovery-component bytes. It does
not prove USB enumeration, NCM, button/indicator behavior, storage safety,
Linux target boot, SSH, charging, thermal control, suspend, sensors, audio,
display, radio, or GPU behavior on the ROG Phone 5. Those remain separate
attended live gates behind fresh authorization.
