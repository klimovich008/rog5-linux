# Corrected headless successor offline candidate — 2026-07-30

## Result

**PASS — the corrected-DTB target, signed runtime bundle, shell-free recovery,
accepted-config ASUS wrapper successor, boot-v3 image, and unsigned AVB image
pass the complete hardware-free gate.**

This was PC-only work. No phone, ADB, fastboot, SSH credential, root password,
production signing key, private workload input, or external service was used.
The result remains `authority=none`; it grants no boot, flash, signing,
storage, or deployment authority.

## Candidate identity

```text
candidate:        headless-network-root-v1
manifest SHA-256:
d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d
public trust-root SHA-256:
ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb
authority:        none
```

The runtime bundle carries the accepted GPU/RMTFS-isolated DTB:

```text
bytes:   102,870
sha256:  86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
```

The exact Linux target remains release
`7.1.4-g7a5cef0db479`. Its kernel, headless initramfs, manifest, signature,
and DTB match across the A/B bundles.

## Reproduced recovery and wrapper

The successor ARM64 recovery builders reproduced the accepted production
components. Two stable-recovery compositions with the same explicitly
supplied public test key were byte-identical:

| Product | Bytes | SHA-256 |
|---|---:|---|
| public trust root | 32 | `ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb` |
| shell-free stable-recovery initramfs | 7,593,284 | `ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04` |
| runtime manifest | 811 | `d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d` |
| accepted DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| ASUS 5.4 wrapper Image | 50,498,048 | `bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da` |
| raw header-v3 image | 58,097,664 | `157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c` |
| unsigned AVB test image | 100,663,296 | `416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430` |

The two clean wrapper builds used:

```text
builder profile:          steam-deck-asus-5.4-v1
reference config profile: accepted-wrapper-v18-v1
config SHA-256:
df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
source SHA-256:
3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8
source tree SHA-256:
592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
compiler: Ubuntu clang version 18.1.3 (1ubuntu1)
```

Both Images, configs, metadata, raw images, and AVB images match
byte-for-byte. The source seal is unchanged before and after both builds.
The historical builder remains frozen; this result uses the separate
accepted-config successor described in the
[dependency-closure report](2026-07-30-headless-recovery-dependency-closure.md).

## Verification

The retained output passed:

- independent A/B ARM64 recovery-component builds and malicious fixtures;
- independent A/B shell-free stable-recovery composition;
- A/B signed runtime-bundle byte and metadata comparison;
- native signature verification and equal immutable execution plans;
- exact accepted-DTB, target ID, and target release checks;
- two clean source-sealed ASUS 5.4 wrapper builds;
- wrapper config, embedded-initramfs, and output comparison;
- two boot-header-v3 repacks and literal-glob command-line mutation;
- exclusion of legacy recovery CIDR and target-only UFS tokens;
- twin raw/AVB byte comparison and exact partition size;
- independent unpacked kernel/ramdisk comparison;
- AVB footer, `NONE` vbmeta, and `boot` SHA-256 descriptor verification;
- seven candidate-packaging unit tests and two integration tests;
- stable-recovery composition fixture integration; and
- retained-output scans rejecting private-key headers and private-key-shaped
  files.

Legacy compiler and linker warnings from the accepted ASUS 5.4 source remain
non-fatal and reproduced in both builds. Acceptance is based on the pinned
configuration, exact output identities, source seals, independent A/B
comparison, and post-build inspection.

## Disposable-key boundary

One test-only Ed25519 private key was created under a mode-`0700` temporary
directory and used only to produce the two offline runtime bundles. The build
trap deleted it when the original orchestration exited. Final inspection
found no PEM/private-key header and no `.pem` or `.key` file anywhere in the
candidate. Only the raw public key and 64-byte detached signatures remain.

No production key was created or used. The output cannot authorize or sign a
different runtime bundle.

## Recovered dispatch failure

The first orchestration attempt failed closed before wrapper compilation
because it selected the successor builder for hashing but dispatched the
frozen historical script. The partial directory retained only the selected
profile, builder qualification, and pre-build source seal.

After the dispatch was fixed, the wrapper gate was run independently against
the exact already-built A/B recovery initramfs inputs. It completed the full
twin compile/repack/inspection gate. Those outputs were then attached to the
existing signed candidate after byte-comparing both embedded initramfs inputs.
The three small pre-compile records are preserved under
`wrapper-dispatch-failure`; no partial kernel product was reused.

## Next gate

This result proves offline construction and packaging, not phone behavior.
Any temporary boot still requires fresh, separate user authorization and an
attended rollback window. The first live acceptance target remains minimal
key-only SSH with clean automatic fallback; buttons/indicator, charging,
thermal control, suspend, sensors, audio, display, radio, and GPU follow as
separate measured gates.
