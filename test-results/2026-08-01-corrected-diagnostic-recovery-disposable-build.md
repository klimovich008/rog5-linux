# Corrected diagnostic-recovery disposable twin build

Date: 2026-08-01

Result: **PASS offline — the recovery fetch-policy correction completed the
full diagnostic deployment path with a disposable Ed25519 trust root, two
byte-identical ASUS 5.4 wrapper builds, native verification, and the real
artifact-preflight logic.**

The run started from clean, origin-synchronized checkpoint
`2653e6195e7e1ea33e1b23ed955494ec507fccac`. It did not open the production
recovery signing key, contact fastboot or any other phone interface, mutate
host networking, or create boot authority. The retained candidate records
`authority=none` and is not eligible for a phone boot.

## Full-path execution

With `ROG5_RUN_FULL_DISPOSABLE_DIAGNOSTIC=1`,
`scripts/host/test-full-diagnostic-deployment-path.sh` created an external
mode-`0600` disposable Ed25519 private key and executed the production
diagnostic wrapper, shared twin builder, signing-input stager, bundle
packager, stable-recovery initramfs builder, two clean ASUS 5.4 kernel builds,
header-v3 image packer, test-only AVB wrapper, native artifact verifier, and a
disposable copy of the production artifact preflight. The private-key
snapshot was destroyed before success.

The fixture preserved the production gate's exact consumed-recovery refusal.
It changed only the candidate-specific identity pins in its ignored disposable
copy, so the historical consumed wrapper
`9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef`
remained denied throughout the test.

The terminal verdict was:

```text
image_sha256=2a44a9087b677342698b1e1e3fb63cd0276b8251ba2af75d48362a534ae62c53
trust_key_sha256=f76b061d024358c060d1113232e64c213ce983096f26ad64fccaf40d16519350
authority=none
PASS full disposable-key diagnostic wrapper, twin build, native verification, and artifact-preflight fixture
```

## Reproduced identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Test-only AVB recovery wrapper | 100,663,296 | `2a44a9087b677342698b1e1e3fb63cd0276b8251ba2af75d48362a534ae62c53` |
| Raw recovery wrapper | 58,101,760 | `79ea621c4ba6a11bfb84722c5bd59f9a76661d56de74316959eca4fcc1e29ded` |
| ASUS 5.4 recovery `Image` | 50,498,048 | `c6a7a4a65b2c837c2a01fc16ac836600f181ec11cef170c013f395575e11ca87` |
| Accepted wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| Stable-recovery initramfs | 7,594,697 | `3d4ac0cbe41d5f92aa7e0e6411e0d0c61288b4e0429ed4f70a0d6d02e982b5ae` |
| Disposable public trust root | 32 | `f76b061d024358c060d1113232e64c213ce983096f26ad64fccaf40d16519350` |
| Recovery fetcher | 132,824 | `f410ca875031dcf9c41cf2c8a67e5a9fba862cf50b53e1d8c51453f4e0b5d13d` |
| Recovery control | 132,896 | `f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77` |
| Target bundle verifier | 4,467,272 | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| Host verifier | 48,144 | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |
| Diagnostic Linux `Image` | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| Corrected board DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| Diagnostic target initramfs | 6,010,870 | `10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c` |
| Diagnostic manifest | 831 | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| Disposable manifest signature | 64 | `82f3f82403a299b2c474cdafe94b866b4d0d0a043cb03ff53227f4b326353595` |

Every A/B identity above is byte-identical. Both kernel build records also
match source SHA-256
`3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`,
accepted config profile `accepted-wrapper-v18-v1`, Clang 18.1.3, and the
qualified builder/rootfs/package-lock/recipe tuple. The source seals before
and after both builds match at 79,030 entries and tree SHA-256
`592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a`.

## Warning boundary

The inherited ASUS/Qualcomm 5.4 source emits compiler warnings for old-style
prototypes, pointer-to-smaller-integer casts, enum conversions, malformed
vendor Kconfig declarations, static exported symbols, deprecated OpenSSL
builder APIs, and three functions whose stack frames exceed the 2,048-byte
warning threshold. Both clean builds reproduced the same warning classes and
completed successfully. These warnings are kernel-hardening debt; they are
not silently treated as evidence that the corresponding runtime paths work.

## Decision

The fetch-policy repair is now proven through the complete hardware-free
deployment composition, not only unit and QEMU tests. The disposable wrapper
must not be booted. The next recovery candidate must be built twice with the
existing production recovery trust root, pass the same exact verification and
repository CI gates, and then replace—never re-admit—the consumed wrapper in
the deny-by-default temporary-boot policy. The separate bounded fallback
NetworkManager cleanup design remains a prerequisite for another phone
lifecycle.
