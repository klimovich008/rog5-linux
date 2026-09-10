# A660 versioned runtime-root offline evidence

Status: **PASS offline**

Date: 2026-07-28

Scope: build the three target AArch64 runtime tools reproducibly, install the
guarded A660 command surface into versioned roots, preserve accepted v10 GPU
ancestry, and bind each complete root to an independently verified persistent
seal. No phone boot, reboot, flash, selector, production key, or external
credential was used.

## Runtime tools

The accepted Arch Linux ARM builder is preserved in the immutable 931,880,960
byte OCI archive
`artifacts/a660-runtime-builder/rog5-a660-runtime-builder-arch-2026.07.24.oci.tar`,
whose SHA-256 is
`c38d64ea0642d659c66022a638167284876b804e8120a83304284a0d2b7af3a2`.
`scripts/host/get-a660-runtime-builder-image.sh` retrieves that exact
GitHub release asset into the ignored artifact cache and rejects any metadata,
size, or hash mismatch.
Its image ID is
`8c84a3b902803fafcc2d9ab4671e6ff9b3ca1b9297cee55cdc4caad34b895e91`.
The base layer is
`622a01d66d32793ccf4a4198a7f76bd145b66558605171d51b4c15ff661ae715`.
The builder layer is
`88a5a305621e113fb7ee16a53dda1d0a477eb0aacd3d28216738e01d35e053b1`.
The static Alpine builder image is
`d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495`.
Both report `arm64`.

The Arch builder package inventory hashes to
`125cb2f6fb2af2c473f319d91c23da47d62e3abc84ed6ca8b8f30525cf4eed3e`.
Two independent OCI-directory exports normalized to byte-identical archives.
Loading the accepted archive into a new isolated Podman store reproduced the
exact image, architecture, and two layer identities without a package mirror.
Two complete runtime-tool builds were byte-identical. The published ignored
artifact directory is `artifacts/a660-runtime-tools-v1`:

| File | Size | SHA-256 |
|---|---:|---|
| `manifest` | 699 | `356ec71e4f8fff5cdc0c371c49225df1f387f4157f8f850a5eeed9ecc8c51e4f` |
| `persistent-root-verify` | 326920 | `bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58` |
| `rog5-cgroup-exec` | 300416 | `0558728dbc82f651b7a36a8a618ed84e510e103646420d523fd17f1837ed2508` |
| `rog5-vulkan-submit` | 71688 | `715ab6e341c389f287bb2c1794cb552e820efb25f57643e46c48ccdf839c4f30` |

The verifier and cgroup executor are static AArch64 ELF files. The Vulkan
helper has the exact AArch64 interpreter `/lib/ld-linux-aarch64.so.1` and
loader dependency `libvulkan.so.1`. A QEMU smoke run reached the target Vulkan
loader and returned `VK_ERROR_INCOMPATIBLE_DRIVER`, as expected on the x86
host without an A660.

## Published roots

Each publication is one root-owned mode-`0700` directory created by atomic
`renameat2(RENAME_NOREPLACE)`. It contains a root-owned mode-`0555` Btrfs
subvolume with `ro=true` and a root-owned mode-`0444` identity. The root and
identity therefore become canonical together.

| Property | Generic acceptance root | Accepted-v10 runtime root |
|---|---|---|
| Root path | `/var/lib/rog5-network-root-a660-acceptance-v1/root` | `/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10-runtime-v1/root` |
| Kernel release | `7.1.4-g7a5cef0db479` | `7.1.4-rog5-a660reg1` |
| Base generation | `arch-successor-v3` | `a660-gmu-cx-runtime-pm-v10` |
| Identity SHA-256 | `7f177499035f16b772d4055482710aa2b4892e622d7c2388ba5d71eb2bc1e4a9` | `01228bd733a3fab30ec836c489d1c0bea6bde2c5c78fe03c481c02bce0ff7fe6` |
| Base tree entries | `181245` | `181264` |
| Base tree SHA-256 | `dfa48252cdcc5cfb45d9b3994dd8171bb5f63552eaf1e0d6dea2152e9564628d` | `fead9c0ef533685bb7653ca43ad0340ba495996ce8457a3504d34d95f2ea388c` |
| Command manifest | `1d6e6a61be06c71d68cbf4098e7f9ac9375550071acc5d1328d6db168f226521` | `84d60606d63497e80e60bb3143b24bcb0ed4924d876906c43e042130c6cfa93f` |
| Tree entries | `181252` | `181272` |
| Tree SHA-256 | `f0949286eda91af2fb597caaa9d0a8db5c37b6c8173ece03316aea9cf099eda8` | `253dc2c1cf975290d6f8c2b4cd1d90cbf1762a75b1c559958d1b422ebd93fa73` |
| Seal SHA-256 | `65011e3245ced700386b2d074d5b469671f79f17537edb84bc9077e5faffc7cf` | `c38b08e2f689c5008d305dc2710e4fc57beff65d982fa33654ff3b953fb202e8` |

Both root transactions require the external approved runtime-tools manifest
SHA-256
`356ec71e4f8fff5cdc0c371c49225df1f387f4157f8f850a5eeed9ecc8c51e4f`;
the manifest cannot approve a replacement of itself. The generic identity
binds successor-v3 verifier
`ee301696a22565bb338781b455e5510dbb7102b1e11e1653baba9538a3282e1e`.
The v10 identity binds the accepted-v10 verifier
`f26d67a3267f34153fb672b30bcc9cede8bc4b5bef4f011fa2a3028473601743`.
The v10 `msm.ko` remains
`c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d`.

For v10, the protected source and private clone passed the legacy verifier
before integration. A private read-only snapshot then anchored the complete
base tree. Post-integration verification requires the final inventory to equal
that exact base plus only the approved runtime paths, and byte-checks every
pre-existing file, symlink, xattr, owner, mode, link count, and non-directory
metadata. The accepted `msm.ko` receives an additional fixed-hash check. The
integrated successor then received a new complete tree seal and passed both
the Python verifier and the independently implemented static AArch64 verifier
before and after atomic publication. The legacy verifier is intentionally not
applied after integration because its policy rejects every added
diagnostic/runtime file.

## Fault and repository checks

- Fourteen focused Python tests pass, including deterministic identities,
  exact base-delta enforcement, real no-replace publication collision tests,
  post-rename symlink replacement, and rejection of command, tool, identity,
  tool-manifest, unapproved self-consistent tool builds, and base-verifier
  substitution.
- Python compilation, Bash parsing, ShellCheck, and `git diff --check` pass.
- The complete repository Linux `quick` tier passes with the new runtime-root
  tests included.
- Both root-publication scripts completed their final published-path
  verification.

These roots are not cryptographically signed artifacts. The next gate is to
bind the selected root identity into the incompatible signed runtime-bundle
v2 manifest, package the matching kernel/DTB/initramfs, and add the exact host
serving profile. Production-key use and any phone boot remain separate
authorization boundaries.
