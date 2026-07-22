# Linux 7.1.4 PC cross-build

Result: **PASS** for the compile-only upstream baseline. This is not an ASUS boot candidate.

## Reproduction

- Source: Linux `v7.1.4`, pinned commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
- Builder: Ubuntu 24.04 container on Docker Desktop/WSL2, x86-64 host.
- Compiler: Ubuntu Clang 18.1.3, LLVM ARM64 target.
- Configuration: ARM64 defconfig plus `configs/kernel/rog5-mainline.fragment`.
- Output cache: Docker named volumes; exported products under ignored `dist/linux-7.1.4/`.

## Gates

- Shallow pinned source fetch and commit check: **PASS**.
- ARM64 `Image.gz`: **PASS**; gzip and SHA-256 checks pass.
- Five upstream SM8350 comparison DTBs: **PASS**; nonempty, parseable, and hash-verified.
- Required UFS, USB NCM, built-in MSM DRM, BPF, and BTF config checks: **PASS**.
- ELF `.BTF` section and kernel BTF ID generation: **PASS**.
- Host-side export size and SHA-256 verification: **PASS**.

The upstream DTBs target Qualcomm, Microsoft, and Sony boards. None is compatible with the ROG Phone 5 and none may be passed to `fastboot boot`. The next bootable milestone requires an reviewed ASUS recovery DTB plus initramfs and Android boot-image packaging.
