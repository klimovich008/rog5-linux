# Kernel build cache integration — 2026-07-29

Status: **accepted for development builds; release builds remain clean twins**

The rootless, network-disabled kernel-builder container compiled a real
minimal ARM64 Linux kernel three ways:

1. a fresh output tree with compiler caching disabled;
2. a distinct fresh output tree with ccache enabled;
3. a second incremental invocation against the cached output tree.

All three produced the same configuration and raw Image.

| Property | Value |
|---|---|
| Linux source commit | `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` |
| Config SHA-256 | `24e70400094f99d4a56d9cc5f629681a3d9552c7a79c630d23c6bcc27aec95d9` |
| Fresh uncached Image SHA-256 | `346b620bbe40e2d82097e2234d4ccaeedc88b8902cb4c346211fca420bf4dd9c` |
| Fresh cached Image SHA-256 | `346b620bbe40e2d82097e2234d4ccaeedc88b8902cb4c346211fca420bf4dd9c` |
| Repeated incremental Image SHA-256 | `346b620bbe40e2d82097e2234d4ccaeedc88b8902cb4c346211fca420bf4dd9c` |
| Image size | 3,354,632 bytes |
| ccache version | 4.9.1 |
| Final cacheable calls | 972 |
| Final direct hits | 301 |
| Final misses | 671 |
| Final uncacheable calls | 458 |

The integration gate machine-parses `ccache --print-stats` and requires a
nonzero direct-hit count before publishing `PASS`; printed statistics alone
are not acceptance.

The first real cached build also rejected an invalid
`CCACHE_DEPEND=0` setting that the fake-tool contract could not detect. The
implementation was corrected to ccache's supported
`CCACHE_NODEPEND=true`, the fixture now pins that environment, and the real
comparison then passed.

The output contract is deliberately development-only:

- clean/uncached remains the default;
- reuse requires an exact mode-`0600`, current-owner input record;
- canonical source/output paths, source and config identity, build scripts,
  selected tool binaries, Kbuild identity, and cache mode are bound;
- output must stay outside the source tree;
- `flock` excludes concurrent builders and is released on process death;
- a matching interrupted Kbuild tree may resume, but its input record does
  not assert completion;
- a mismatch is never cleaned automatically.

The proof used the generic QEMU `virt` profile and did not contact, boot, or
write the phone. It does not validate ASUS hardware, the full board config,
modules, or BTF. Those release products still require two fresh output trees
and the existing byte-comparison gates.

The local container used the pinned Ubuntu base digest from the Dockerfile,
but its apt package closure is not yet snapshot-pinned. Complete source,
package, and container identity pinning remains the next offline task.
