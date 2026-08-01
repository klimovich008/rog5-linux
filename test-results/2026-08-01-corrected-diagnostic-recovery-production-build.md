# Corrected diagnostic-recovery production twin build

Date: 2026-08-01

Result: **PASS offline — the fetch-policy-corrected diagnostic recovery was
twin-built with the existing production trust root, signed, independently
verified, and admitted by the exact artifact gate.**

The guarded build started from clean, origin-synchronized checkpoint
`84a9cc845c8f3250a68dc09326b05c40314de77d`. It used the existing external
recovery signing key without copying private material into the repository or
retaining its private build snapshot. The external mode-`0444` candidate
record remained SHA-256
`7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8`
after the operation, the signing key retained mode `0600`, and the ASUS source
seals before and after both builds were byte-identical. No phone interface or
host network state was touched.

## Production identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Production AVB recovery wrapper | 100,663,296 | `f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef` |
| Raw recovery wrapper | 58,101,760 | `2f460aa01ee1b97c495d0857b3207bf74920487c56f30c5e155e199967628a01` |
| ASUS 5.4 recovery `Image` | 50,498,048 | `7fac4dda6a7133e7d3a6589da4fb5d0bdad3802705da5edf52701a20133728ed` |
| Accepted wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| Stable-recovery initramfs | 7,594,700 | `fec72c4dba62a24ced899af4d4fc3d0af3b7b691ea6f6c1bcf90c7aaf181c57a` |
| Production public trust root | 32 | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| Recovery fetcher | 132,824 | `f410ca875031dcf9c41cf2c8a67e5a9fba862cf50b53e1d8c51453f4e0b5d13d` |
| Recovery control | 132,896 | `f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77` |
| Target bundle verifier | 4,467,272 | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| Host verifier | 48,144 | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |
| Diagnostic Linux `Image` | 40,049,152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| Corrected board DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| Diagnostic target initramfs | 6,010,870 | `10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c` |
| Diagnostic manifest | 831 | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| Production manifest signature | 64 | `44123a0817816295fc8a8359ddd78b36c59c9f7c6d9e88373e4ed37191235f6b` |

Every A/B wrapper, raw image, kernel, configuration, and initramfs is
byte-identical. Both kernels also reproduce source SHA-256
`3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`,
the accepted `accepted-wrapper-v18-v1` profile, and Clang 18.1.3.

## Gate result

The production profile now pins the corrected fetcher and exact wrapper
identities. The phone-free live-gate replay verified the stable-recovery
archive, signed bundle, diagnostic profile and target, embedded trust root,
AVB footer and boot descriptor, raw-image prefix, unpacked kernel and
initramfs, wrapper command line, and twin equality:

```text
PASS stable-recovery artifact preflight profile=headless-diagnostic-deployment-v1 image_sha256=f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef
```

The old production wrapper
`9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef`
remains consumed, absent from temporary-boot admission, and explicitly
refused by the live gate.

## Decision

The new wrapper is eligible for one RAM-only temporary boot after the
remaining bounded fallback-profile cleanup correction, installed-host
identity checks, connected preflight, and repository CI pass. It must be
consumed regardless of that lifecycle's result and must never be flashed.
