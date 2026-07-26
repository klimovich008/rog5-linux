# A660 registration kernel — offline build and reproducibility

Date: 2026-07-26

Result: **the storage-disabled, headless A660 registration kernel and module
set pass their complete offline build contract and reproduce byte-for-byte**.
The phone was not contacted. This is not a bootable bundle, a live registration
result, a render-node result, or GPU acceleration.

## Boundary

The candidate is based on the pinned Linux 7.1.4 source:

- source commit `d9ac316489f4258d389d6298659d5e9c22183400`;
- source tree `c796deb1cc54e942f8bb46a2c76a7199e19e5c92`;
- release `7.1.4-rog5-a660reg1`;
- DRM/MSM and SM8350 GPUCC built as manually loaded modules;
- MSM display/KMS backends, SCSI, UFS, block SCSI disks, and RPMB disabled;
- A660 SQE, GMU, and ZAP firmware absent from both the build tree and module
  archive;
- the accepted consumer-disabled v18 SMMU config retained as the dependency
  baseline.

The build applies
`0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch`, whose SHA-256 is
`0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637`.
It makes `a6xx_gmu_init()` return an `a6xx_gmu_pwrlevels_probe()` failure before
ACD, HFI, or RPMh initialization can continue. The patched `a6xx_gmu.c`
SHA-256 is
`126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace`.

## Fail-first and build results

The fail-first contract initially rejected the missing fragment, builder, and
verifier. After implementation it passes and requires the pinned source and
patch, unique ABI, modular DRM/MSM and GPUCC, disabled display KMS, exact
module identities, BTF, archive membership, zero A660 firmware, and the
existing storage-disabled network-root verifier.

The first builder attempt stopped before compilation because
`merge_config.sh` was invoked from the read-only archived source location.
That failed output was moved intact to
`artifacts/failed-a660-registration-build-merge-config`; no source file or
phone state changed. The builder now invokes the merge helper from the
writable output directory while keeping the repository and pinned source
read-only.

Build A and Build B then completed in independent empty output directories
under rootless Podman, with networking disabled, a read-only container root,
read-only source and repository mounts, and only the selected build directory
writable persistently. Each complete verifier run reported:

```text
PASS final network-root config, Image, modules, and recorded hashes
PASS modular headless A660 registration Image/modules; exact source patch, unique ABI, zero UFS, and zero firmware
```

The following nine Build A/Build B outputs are byte-identical:

| Output | SHA-256 |
|---|---|
| `.config` | `d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0` |
| `arch/arm64/boot/Image` | `52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db` |
| `arch/arm64/boot/Image.gz` | `9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307` |
| `modules.tar.gz` | `e3cb1ef31b6c1c803bee98748660f92b3b192d460cb41d5d4691f9953a91a42b` |
| `Module.symvers` | `a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477` |
| `drivers/gpu/drm/msm/msm.ko` | `f7c69c399dea567ad8a1f0ecc10c61259dd76052230f61ae69165c711e24ac24` |
| `drivers/clk/qcom/gpucc-sm8350.ko` | `c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563` |
| `drivers/soc/qcom/mdt_loader.ko` | `001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3` |
| `build-meta.txt` | `6b7e0cd2d93b9671a11b19039e7df7426b86fea0b5e56dbd9267ebda1d6a5bfc` |

## Resolved verifier assumptions

With `CONFIG_DRM_MSM=m`, upstream Kconfig resolves
`CONFIG_QCOM_MDT_LOADER=m`, and `msm.ko` records an `mdt_loader` dependency.
The verifier therefore requires the exact loader module name, release,
dependency, BTF section, and matching archive payload instead of incorrectly
requiring a built-in loader.

Upstream's module parameter is correctly exported as
`separate_gpu_kms: (bool)`, although its nearby source description is attached
to the differently named `separate_gpu_drm` parameter. The verifier checks the
actual exported parameter needed by this candidate. No cosmetic source patch
was added.

## DT candidate

The registration overlay and builder now also pass offline. The builder
accepts only the exact v18 SMMU DTB with SHA-256
`da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f`.
The overlay contains exactly five references and changes only four statuses
plus the ZAP firmware name:

- GPUCC, Adreno SMMU, A660 GPU, and GMU are `okay`;
- the ZAP child names `qcom/sm8350/a660_zap.mbn`;
- all register, IRQ, IOMMU, clock, power-domain, OPP, reserved-memory, and
  cooling properties remain byte-for-byte derived from the pinned base;
- UFS, QMP/SuperSpeed, the second USB controller, RMTFS, display, remote
  processors, RTC, and the power key remain disabled;
- recovery USB2 high-speed and the accepted RAM map remain unchanged.

Mutation tests reject a missing GMU or ZAP node, a disabled dependency, a
different firmware path, a GPU register override, an added display consumer,
a modified v18 base, and an output that aliases an input. Two independent
builds produced byte-identical 102,908-byte DTBs:

```text
b96f4350b35ff3bfc987ce97828e22bd7136100323752c2ac68c537580bd35d6
```

## Guarded runtime contracts

The read-only baseline and one-shot registration probe now pass their offline
source and artifact contracts. The baseline requires the exact kernel, four
enabled DT nodes, armed original watchdog, masked coldplug/module loading,
unbound devices, unloaded modules, no render node or DRM descriptor, no A660
firmware or request, zero physical storage and block mounts, safe thermals,
and a quiet kernel log.

The probe pins and verifies the exact GPUCC, DRM exec/GPUVM/scheduler,
MDT-loader, UBWC, and MSM modules before arming an independent 90-second SysRq
watchdog. It loads all seven modules explicitly, with GPUCC first and MSM last
using `separate_gpu_kms=1`. Acceptance requires the exact GPUCC, SMMU, A660,
and GMU registration graph; two IOMMU attachments; one headless render node;
zero display connectors; zero DRM file descriptors; zero firmware requests;
runtime-suspended SMMU/GMU state; stable systemd, USB/NFS, storage, thermal,
and kernel-log state; and watchdog disarm only after every check passes.

The probe is deliberately not runnable yet:
`smmu_acceptance_sha=NOT_ACCEPTED` is a source lock. After the independent v18
SMMU live gate passes, that lock must be replaced with the SHA-256 of a
root-owned, mode-0400 acceptance marker included in the reviewed runtime
stage. This prevents the later registration gate from overtaking its required
predecessor.

## What remains

The next offline artifacts are the initramfs/module stage, nested wrapper,
temporary-boot package, and duplicate-build contracts. The v18 SMMU live gate
must then supply the pinned acceptance marker. Only after all of those steps
pass can an attended, RAM-only registration test be considered.

The independent v18 SMMU bind/runtime-suspend gate remains pending and must run
first. A registration-only test must not open a DRM node; firmware loading,
GMU resume/HFI, ZAP/SCM authentication, GPU initialization, and rendering
remain a separate later gate.
