# Builds and required artifacts

## Version strategy

Development follows current stable Linux 7.1.4 so board work is written against the newest upstream Qualcomm, DRM/MSM, and A660 code. Linux 6.18.39 is the deployment/LTS comparison target: kernel.org projects 6.18 maintenance through December 2028. Board changes should be kept small enough to compile on both where APIs permit.

Linux version numbers are not capability grades. A 7.x build is accepted only if it passes more hardware gates than the stable 5.4 baseline.

## Inputs kept in Git

- source revision manifest and URLs
- kernel configuration requirements fragment
- reviewed ASUS board DTS and any new bindings/drivers, once developed
- Arch/systemd service definitions and small BusyBox-compatible recovery scripts
- build, packaging, smoke, hardware, and regression tests
- redacted reports and artifact SHA-256 identities

## Inputs kept private

- stock/vendor boot, vendor-boot, DTBO, and partition images
- decompiled running vendor DTB/DTS
- Qualcomm, ASUS, Pixelworks, Wi-Fi, modem, DSP, and GPU firmware
- SSH private keys, Wi-Fi credentials, API tokens, email, CV, and account data
- complete boot command line and device identifiers

Private inputs live outside the repository and are referenced only by path or hash. They must never be bundled into a public source archive.

## Build products

| Product | Purpose | Current status |
|---|---|---|
| vendor-derived 5.4.210 image #20 | recoverable working server baseline | passes core suite; GPU rejected |
| Linux 7.1.4 `Image.gz` and modules | current-stable compile/toolchain baseline | PC cross-build and verification pass; never boot alone |
| upstream SM8350 comparison DTBs | schema and subsystem reference | five build/parse/hash checks pass; never boot on ASUS hardware |
| ASUS serial skeleton DTB | verify board source and DTB toolchain | memory, TLMM, disabled UFS, and left-side USB contracts compile and pass static checks; never boot |
| ASUS minimal recovery DTB | USB2 high-speed NCM/ACM recovery with storage disabled | built-in FEMTO PHY reaches the gadget and `usb0` internally; host enumeration is pending |
| ASUS A660 tier DTB | upstream Freedreno/GMU bring-up after recovery | isolated two-node overlay and pinned upstream firmware pass offline guards; hardware tests pending |
| ASUS hardware DTB and modules | incremental subsystem bring-up | planned behind tier gates |
| locked Arch server rootfs | signed packages, SSH, VPN/hotspot tools, matching modules | offline staging and metadata round-trip pass; not booted |
| locked Arch Plasma rootfs | current headless-first target with Plasma/KRDP, browser automation, VPN/hotspot tools, and matching modules | staging plus archive re-extraction suite pass; not booted |
| target initramfs | RAM-only recovery shell, USB NCM/ACM, SSH, rollback | Linux 7.1 starts it, configures the gadget, creates `usb0`, and returns through rollback; host SSH is pending |
| GPU target initramfs | isolated A660 probe after base recovery passes | deterministic firmware-bearing archive passes; deliberately absent from boot package |
| kexec staging initramfs | carry mainline kernel/DTB/initramfs through header-v3 boot | boots with authenticated SSH; manifest and zero-storage gates pass |
| temporary Android boot image | reversible two-stage `fastboot boot` testing | staging and Linux 7.1 execution pass; target host enumeration remains under diagnosis |
| diagnostic module sources | read raw ramoops and arm bootloader recovery without storage access | maintained under `tools/diagnostics/`; built privately against the exact fallback kernel |
| release boot image | possible persistent deployment | prohibited until every release gate passes |

Large products go under ignored `build/`, `dist/`, or `artifacts/` directories. Every candidate receives a source commit, config hash, compiler version, file sizes, and SHA-256 manifest.

## Build order

1. Validate scripts, known artifacts, and kernel config symbols.
2. Compile current stable Linux plus known upstream SM8350 DTBs to prove the native ARM64 toolchain.
3. Translate only the minimal ASUS boot contract: reserved memory, regulators, disabled UFS, one USB controller, serial/reboot.
4. Compile and run `dtbs_check`; package and verify the RAM-only two-stage recovery image.
5. Use temporary boot, keep UFS disabled until host-visible recovery works, and stop immediately on watchdog, reset, thermal, or USB regression.
6. Add charging, input/display, radios/remotes, then GPU in separate commits and test tiers.
7. Cross-compile-test the board series on 6.18 LTS and current stable.
8. Add BTF/eBPF and GodShell only after the hardware platform is stable.

Native phone builds default to one parallel job. Four jobs heated rapidly; even two jobs eventually approached 45 C at the battery sensor during the first compile. Each build was stopped cleanly and resumed from the object cache at a lower job count. The fragment also disables unrelated ARM64 SoC families, ACPI, Xen, KVM, and NFS so the final image is a DT-based Qualcomm server kernel rather than a distribution-wide ARM64 build.

When a native build is unavoidable, run `guard-kernel-build.sh BUILD_PID` alongside it. The default 45.0 C battery-sensor ceiling terminates the active `make` child and build wrapper while preserving the object cache.

Normal development uses the PC cross-builder:

```powershell
powershell -NoProfile -File scripts/host/Build-MainlineInDocker.ps1
```

It runs the same pinned source, fragment, module, DTB, and verification scripts as the native experiment. Docker named volumes retain the source and object cache, while only verified artifacts are copied to `dist/linux-7.1.4/`. The phone receives nothing until a recovery image passes offline gates; copying `Image.gz` or the current skeleton cannot boot the device because UFS/USB remain disabled and initramfs, command line, and Android boot-image packaging are still required.

The ASUS staging builder defaults to the smaller legacy loader. Set
`KEXEC_FILE=1` with a separate output directory to reproduce the tested
file-syscall variant; source patches 0005 and 0006 supply the libfdt address
helpers missing from the ASUS source drop.

## Reproduction records

The build log and private DTS stay out of Git if they contain identifiers. A redacted summary belongs in `test-results/`; exact nonsecret output hashes belong in `manifests/`.
