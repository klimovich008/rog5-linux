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
| Linux 7.1.4 `Image.gz` and modules | current-stable compile/toolchain baseline | reproducible PC build; recovery Image passes one attended kexec |
| upstream SM8350 comparison DTBs | schema and subsystem reference | five build/parse/hash checks pass; never boot on ASUS hardware |
| ASUS serial skeleton DTB | verify board source and DTB toolchain | memory, TLMM, disabled UFS, and left-side USB contracts compile and pass static checks; never boot |
| ASUS minimal recovery DTB | USB2 high-speed NCM/ACM recovery with storage disabled | passes offline, two staging cycles, and Linux 7.1 target recovery |
| ASUS A660 tier DTB | upstream Freedreno/GMU bring-up after recovery | isolated two-node overlay and pinned upstream firmware pass offline guards; hardware tests pending |
| ASUS hardware DTB and modules | incremental subsystem bring-up | planned behind tier gates |
| locked Arch server rootfs | signed packages, SSH, VPN/hotspot tools | historical suite passes; contains the previous module set and is not a current boot candidate |
| locked Arch Plasma rootfs | headless-first target with Plasma/KRDP and browser/network tools | current 2,007,186,653-byte network-root archive has exact modules/firmware, persistent client authorization, and passes clean round-trip plus two diagnostic phone boots |
| target initramfs | RAM-only recovery shell, USB NCM/ACM, optional SSH, rollback | v18 passes staging twice and one Linux 7.1 target/rollback cycle |
| GPU target initramfs | isolated A660 probe after base recovery passes | historical archive is derived from the unsafe v2 base; do not boot |
| kexec staging initramfs | carry mainline kernel/DTB/initramfs through header-v3 boot | v18 passes nested load, separate execute, Linux 7.1 target, and rollback |
| read-only UFS discovery bundle | enumerate the UFS topology without mounts or host-originated writes | v1 was rejected safely; reproducible v2 passes offline and live with 116/116 nodes read-only, zero blocked commands, contained power state, and automatic rollback; never flash |
| UFS-disabled network-root bundle | boot an ordinary distro from read-only NFS plus a volatile OverlayFS upper | fourteen-file v1 bundle passes offline and twice in diagnostic live boot; normal udev coldplug reset remains; never flash |
| temporary Android boot image | reversible two-stage `fastboot boot` testing | v18 passes two attended live cycles; never flash |
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

Normal development uses the PC cross-builder. The current v18 recovery,
read-only UFS discovery, and UFS-disabled network-root bundles were built on
Nobara Linux with rootless Podman and container networking disabled. The
network-root Linux 7.1.4 config, Images, module archive, target/staging
initramfs, ASUS wrapper, and header-v3/AVB package each reproduce
byte-for-byte. The existing Windows wrapper remains available:

```powershell
powershell -NoProfile -File scripts/host/Build-MainlineInDocker.ps1
```

It runs the same pinned source, fragment, module, DTB, and verification scripts
as the native experiment. Docker retains the source volume, but the wrapper
creates a fresh object volume by default and prints its name for audit. Only
verified artifacts are copied to `dist/linux-7.1.4/`. The phone receives
nothing until a recovery image passes offline gates; copying `Image`/`Image.gz`
or the current skeleton cannot boot the device because initramfs, command line,
and Android boot-image packaging are still required.

The ASUS staging builder defaults to the smaller legacy loader. Set
`KEXEC_FILE=1` with a separate output directory to reproduce the tested
file-syscall variant; source patches 0005 and 0006 supply the libfdt address
helpers missing from the ASUS source drop.

The archived v2 recovery products retain their hashes for provenance only.
Their live staging root was writable physical UFS, and their target DTB enabled
UFS and QMP/SuperSpeed despite the former zero-storage and USB2-only claims.
Nothing was flashed. Do not boot v2, the rejected v6 candidate, or the
superseded unbooted v12 candidate. V13 and v14 are also rejected because their
exact recovery USB identity never appeared during live temporary boot. V15
identified the unnecessary wake-lock gate through its 31-second timing result
and is retained only as diagnostic evidence. V16 reached exact USB, NCM, and
rollback but not an ACM shell. The local v17 keyed diagnostic proved the
RAM/storage boundary and identified the missing `/dev/ttyGS0` node. V18 is the
reproducible credential-free candidate; both required staging/rollback cycles
and the separate attended Linux 7.1 kexec/target/rollback gate now pass.

## Reproduction records

The build log and private DTS stay out of Git if they contain identifiers. A
redacted summary belongs in `test-results/`; exact nonsecret output hashes
belong in `manifests/`. The
[network-root v1 offline report](../test-results/2026-07-24-network-root-v1-offline.md)
records the reproducible UFS-disabled NFS/OverlayFS kernel, both initramfs
layers, ASUS wrapper, Android package, signed Arch input, verified exact-module
Plasma rootfs, and offline host isolation harness. The
[network-root v1 live report](../test-results/2026-07-24-network-root-v1-live.md)
records the privileged export, four bounded coldplug resets, two passing
diagnostic Arch boots, persistent client authorization, and next isolation
gate. The
[UFS discovery offline report](../test-results/2026-07-24-ufs-discovery-offline.md)
records the guarded Linux 7.1.4 build, corrected built-in UFS PHY dependency,
reproducible nested bundle, and exact candidate hashes. The
[v2 offline report](../test-results/2026-07-24-ufs-discovery-v2-offline.md)
records the corrected power-containment build, and the
[v2 live report](../test-results/2026-07-24-ufs-discovery-v2-live.md) records
the passing 116-node read-only enumeration and automatic rollback. The
[current clean-build report](../test-results/2026-07-23-mainline-reproducibility.md)
records the rejected comparisons and the combined Python hash-seed/BTF
serialization fix. The
[recovery v18 report](../test-results/2026-07-24-recovery-v18-offline.md)
records the current reproducible candidate and artifact set. The
[v18 live report](../test-results/2026-07-24-recovery-v18-live.md) records its
two passing credential-free staging and rollback cycles. The
[Linux 7.1 live report](../test-results/2026-07-24-recovery-v18-mainline-live.md)
records the passing load, kexec, zero-storage target, and rollback. The
[v17 diagnostic](../test-results/2026-07-24-recovery-v17-ssh-diagnostic.md)
records the live storage proof and ACM root cause. The
[v16 live report](../test-results/2026-07-24-recovery-v16-live.md) records
exact recovery USB, NCM, and rollback with the missing ACM shell. The
[recovery v15 report](../test-results/2026-07-24-recovery-v15-diagnostic.md)
records the completed timing diagnosis. The
[v14 live report](../test-results/2026-07-24-recovery-v14-live.md) records its
matching early return. The
[v13 live report](../test-results/2026-07-24-recovery-v13-live.md) records its
early return and the corrected host USB identity check. The earlier
[v12 report](../test-results/2026-07-24-recovery-v12-offline.md) is retained
as superseded provenance.
