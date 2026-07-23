# Linux 7.1.4 PC cross-build

Result: **PASS** for the compile-only upstream baseline. This is not an ASUS boot candidate.

## Reproduction

- Source: Linux `v7.1.4`, pinned commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
- Builder: Ubuntu 24.04 container pinned to base-image digest `4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90`, on Docker Desktop/WSL2, x86-64 host.
- Compiler: Ubuntu Clang 18.1.3, LLVM ARM64 target.
- Configuration: ARM64 defconfig plus `configs/kernel/rog5-mainline.fragment`.
- Output cache: Docker named volumes; exported products under ignored `dist/linux-7.1.4/`.

## Gates

- Shallow pinned source fetch and commit check: **PASS**.
- ARM64 `Image.gz`: **PASS**; gzip and SHA-256 checks pass.
- Five upstream SM8350 comparison DTBs: **PASS**; nonempty, parseable, and hash-verified.
- ASUS serial skeleton with disabled reviewed UFS contract: **PASS** for preprocessing, compilation, DTB round-trip parsing, exact reset/rail checks, and static enablement guards; **not a boot candidate** because UFS and USB remain disabled and recovery packaging is absent.
- Matching deterministic modules archive: **PASS**; 1,028 modules for `7.1.4-g7a5cef0db479`, dependency metadata, `ath11k`, and `ath11k_pci` verified. Archive order, ownership, timestamps, and gzip metadata are normalized; two complete packaging passes produced the same SHA-256.
- Required UFS, USB NCM, built-in MSM DRM, BPF/BTF, WireGuard, nftables NAT, and policy-routing config checks: **PASS**.
- ELF `.BTF` section and kernel BTF ID generation: **PASS**.
- Host-side export size and SHA-256 verification: **PASS**.
- Isolated privileged-container VPN hotspot test: **PASS**; AP-to-WireGuard forwarding only, drop policy, masquerade, cleanup, sysctl restoration, and invalid-interface rejection verified.

The routing check is reproducible with `scripts/device/test-vpn-hotspot.sh` in the privileged builder container with networking disabled.

The upstream DTBs target Qualcomm, Microsoft, and Sony boards. None is compatible with the ROG Phone 5 and none may be passed to `fastboot boot`. The ASUS serial skeleton is also prohibited from booting. The next bootable milestone requires a reviewed ASUS recovery DTB plus initramfs and Android boot-image packaging.
