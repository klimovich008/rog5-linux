# Two-stage mainline recovery package - 2026-07-23

Result: **PASS** for deterministic v2 construction and offline validation.
The ASUS 5.4 staging half has also passed live boot; see
`2026-07-23-kexec-live.md` for the target-handoff blocker.

## Design

Android boot header v3 does not provide this boot template with a DTB field. The package therefore temporarily boots an ASUS-compatible 5.4.210 staging kernel with `CONFIG_KEXEC=y`, then loads Linux 7.1.4 with the reviewed ASUS recovery DTB and a separate target initramfs. The complete second stage is embedded in the first initramfs; no storage mount or network transfer is required.

Both initramfs stages provide USB ACM, USB NCM, key-only SSH, and a default 180-second reboot timer. The target initramfs never mounts UFS. Loading the mainline payload and executing it are deliberately separate commands.

## Reproducible inputs

- ASUS 5.4.210 source archive SHA-256: `3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`.
- Reference config SHA-256: `e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4`.
- Alpine 3.24 base initramfs SHA-256: `100e33ea4bc7e2d568450418bba3617f24394e8bb122a39fd5db334555d3bdca`.
- Signed Alpine aarch64 packages: `kexec-tools 2.0.32-r2`, `xz-libs 5.8.3-r0`, and `zstd-libs 1.5.7-r2`; package signatures and pinned SHA-256 values pass.
- Linux 7.1.4 uncompressed `Image` SHA-256: `f010217f70eb6c8022b6af0d937c7ad33498b2c65913a448ef342a72f0148909`.

## Products

- 5.4.210 kexec-stage `Image`: 42,109,440 bytes, SHA-256 `5655a45839340cb68e4cf5fe497f1e2790db293d4a8e234fb4d12dd54d98c9d7`.
- Staging config: 185,609 bytes, SHA-256 `8c7fabbf879d2bce652d8b44d8ac1d982126015732b1176f63cedeb53064d571`.
- Recovery DTB: SHA-256 `c9af02720703471425bbf5a9086869754031d7dced1ec7ec53cbf4c487f3a351`.
- Target initramfs: 5,838,346 bytes, SHA-256 `8bd91d390cf3d65e55c7d1e7e581800edfbede30f8d3f5e51e0d53cf5a495226`.
- Self-contained staging initramfs: 26,281,211 bytes, SHA-256 `940df2d403dcf02dd03b3dc428747a25bcc4290bfd9d31bd7c2f00876bb821f0`.
- Header-v3 raw boot image: 68,399,104 bytes, SHA-256 `5be6a072aaff93df210cf0a86511789f995e3ec8499d1b6728e7c4a8739185f0`.
- Unsigned AVB test image: 100,663,296 bytes, algorithm `NONE`, SHA-256 `88777b3c32fbe6fa29964dd9d1865447c9109d07593e5d4ab910a6bdf1f27aa0`.

Boot images and the stock-derived template remain ignored local artifacts.

## Gates

- ASUS-source compile with only userspace kexec enabled: **PASS**.
- Staging kernel release/config/hash checks: **PASS**.
- Exact memory map and UFS/USB1-only recovery overlay: **PASS**; USB2 remains disabled.
- Target and staging initramfs deterministic double builds: **PASS**.
- Storage-mount prohibition and private-key-block scan: **PASS**.
- Signed ARM64 loader dependency closure: **PASS**.
- ARM64 `kexec-tools 2.0.32` execution and required DTB/initrd/command-line options under PC emulation: **PASS**.
- Nested Linux 7.1 `Image`, DTB, and target-initramfs hashes: **PASS**.
- Runtime payload `SHA256SUMS` manifest construction and offline verification: **PASS**.
- Header-v3 kernel and ramdisk round-trip: **PASS**.
- AVB partition size, partition name, and algorithm: **PASS**.

The offline suite first rejected reuse of the earlier ramdisk because it did not contain `kexec`. The final package embeds the authenticated loader and all runtime libraries, removing dependence on the installed userdata rootfs.
