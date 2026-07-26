# Network-root v18 GPUCC plus Adreno SMMU — offline acceptance

Date: 2026-07-26

Result: **offline acceptance passed; one attended RAM-only probe is eligible
after review; no GPU, GMU, firmware, DRM/render, or acceleration claim**. The
phone was not contacted, booted, or modified. Nothing was flashed.

V17 accepted only trace-free GPUCC registration and a stable one-device bind
with every consumer disabled. V18 takes the smallest next dependency step:
the same external GPUCC module plus the built-in Adreno SMMU driver. GPU and
GMU remain disabled, so this tier cannot request A660 firmware, create a DRM
master or render node, or submit a GPU workload.

## Exact source and dependency boundary

The source audit is pinned to Linux commit
`d9ac316489f4258d389d6298659d5e9c22183400` and tree
`c796deb1cc54e942f8bb46a2c76a7199e19e5c92`.

| Pinned source | SHA-256 |
|---|---|
| `arch/arm64/boot/dts/qcom/sm8350.dtsi` | `58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c` |
| `drivers/iommu/arm/arm-smmu/arm-smmu.c` | `580bcc9326837da0607e45843f4906694c28a0a5b68ca9297bc516747704d55f` |
| `drivers/iommu/arm/arm-smmu/arm-smmu-qcom.c` | `a8ba34c18e75740495d64a15ad6ff94fec4265814f96d7068b9f4c5e45eb3663` |
| `Documentation/devicetree/bindings/iommu/arm,smmu.yaml` | `9c3282286063d71ef9865fd276de5de48f924c8b1dd3404de5b4e21dda62bdb1` |
| `drivers/clk/qcom/gpucc-sm8350.c` | `39efbb61d7cc9a59e13f7e1ee9ebab6357d6fc4cbc981e8a89a28aa976b33755` |

The exact Adreno SMMU node has:

- compatible chain `qcom,sm8350-smmu-500`, `qcom,adreno-smmu`,
  `qcom,smmu-500`, and `arm,mmu-500`;
- register window `0x03da0000` with size `0x20000`;
- two IOMMU cells, two global interrupts, and twelve interrupt entries;
- seven clocks named `bus`, `iface`, `ahb`, `hlos1_vote_gpu_smmu`,
  `cx_gmu`, `hub_cx_int`, and `hub_aon`;
- one GPUCC CX GDSC power domain; and
- no firmware, reserved-memory, supply, regulator, or interconnect property.

The pinned ARM SMMU driver selects the SM8350 Qualcomm implementation,
acquires and enables the node clocks, configures and registers the SMMU and
its IRQs, enables runtime PM, and applies a 20 ms autosuspend delay. Neither
the generic nor Qualcomm ARM SMMU source requests firmware.

The upstream GPU and GMU nodes reference this SMMU, but both remain disabled
in the candidate DTB. The existing network-root kernel already has
`CONFIG_ARM_SMMU=y` and `CONFIG_ARM_SMMU_QCOM=y`, so no mainline Image or
module rebuild was required.

## Candidate construction

The diagnostic overlay changes exactly two statuses to `okay`: GPUCC and the
Adreno SMMU. It cannot alter registers, clocks, resets, power domains,
interconnects, supplies, memory, firmware, boot arguments, or another device.

The resulting DTB preserves the accepted recovery boundary:

- GPU and GMU are disabled;
- UFS, its PHY, SuperSpeed USB/QMP, and physical block access are disabled;
- display, remote processors, RMTFS, RTC, and the power key are disabled;
- only USB2 high-speed recovery transport remains enabled; and
- no A660 firmware exists in either initramfs or the module archive.

The derivative staging archive changes only its nested `board.dtb` and
`SHA256SUMS`. The accepted Linux 7.1.4 Image, module archive, target initramfs,
and external GPUCC module remain byte-identical to v15/v17. The ASUS
5.4.210 wrapper was rebuilt from the accepted config solely to embed the new
credential-free staging archive. The Android package uses AVB algorithm
`NONE` and is eligible only for temporary `fastboot boot`; it must never be
flashed.

## Test-first and static safety evidence

The fail-first commits preceded every production implementation:

- `f608359` defined the source, DT, baseline, probe, and exact-bundle
  expectations;
- `b9aa036` added the nested staging-payload boundary; and
- `520beb2` required clean ASUS wrapper rebuilds.

The tests initially failed because the verifier, overlay, builders, baseline,
probe, and bundle did not exist. After implementation:

- the dependency verifier rejects source drift, missing clocks, reordered
  probe operations, new firmware paths, or an altered GPU/GMU relationship;
- DT mutations that omit the SMMU, enable GPU/GMU, or add firmware are
  rejected;
- the staging builder proves only the DTB and nested manifest changed;
- the base network-root verifier independently checks GPUCC and SMMU status
  while retaining the historical five-argument contract;
- the pre-disarm baseline is read-only and requires the original target
  watchdog armed, read-only NFS, exact USB, zero block devices/mounts,
  trace-free parameters, no firmware/render/fault evidence, safe thermals,
  GPUCC absent, and the exact SMMU device still unbound;
- the guarded probe requires an explicit one-shot opt-in, exact module hash,
  mode, and ABI, and arms an independent 75-second SysRq watchdog before
  loading GPUCC;
- post-load acceptance requires one GPUCC bind, one exact ARM SMMU bind,
  runtime-suspended SMMU state, no GPU/GMU IOMMU client, no firmware or render
  node, zero storage, stable systemd/NFS/USB, safe thermals, and no new warning
  or IOMMU fault; and
- any post-load failure leaves the independent watchdog armed for automatic
  hardware reset. No unload, retry, flash, mount, or storage-write path exists.

Pinned ShellCheck found that standalone negative `grep` assertions could
bypass `set -e` in some shells. Those assertions were converted to explicit
fail-closed branches before acceptance. All new production scripts are
warning-free under the pinned ShellCheck image.

## Reproducibility

Two clean ASUS source copies were built in separate rootless Podman containers
with no network, a read-only container root, and different parallelism
(`JOBS=4` and `JOBS=6`). The builder image digest was:

`sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c`

The source comparison covered 73,717 regular files, 41 symlink targets, and
all modes without following the intentionally broken vendor audio symlinks.

| Source comparison record | SHA-256 |
|---|---|
| regular-file manifest | `cc0d941b8ea06d443adc329ca5315b639e848bc81f28953dc23a43b91f981351` |
| mode manifest | `322403b60fa73c401920fd0d6fc5dfccf65222f40294cee9f471302d368fe16f` |
| symlink-target manifest | `046d934da016cd35279d1d80a50f31d3843af860996204e82943461607cb27c6` |

Both clean wrapper Images and metadata matched byte-for-byte. Two independently
prepared staging archives also matched, and two separate header-v3/AVB
repacks produced identical raw and AVB images.

## Exact candidate identities

The fourteen-file manifest SHA-256 is
`e433a95b3cfeeeabd8dd97b4321da3082f934e5bbbca5cb0bfd4f71074355d73`.
The inherited accepted v15 manifest remains
`a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc`.

| Artifact | SHA-256 |
|---|---|
| ASUS 5.4.210 staging Image | `9b953088c3da1a757f07b219572cd3409dc8bba3698207833259822ef8bc0aac` |
| ASUS staging config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| embedded/staging initramfs | `85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4` |
| ASUS wrapper metadata | `9378a4687f433aed63f3cc57f33772526fd186126e7c0825f8bdaf618bcb10cd` |
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| Linux 7.1.4 Image.gz | `a620dd40df6d495e00a8f7f84e707c9ceb7483f0828afb2372792985e69f008e` |
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| Linux 7.1.4 metadata | `21deef91a5fc0864b9c43389cec6ea0f326e1f68e47265f2514986f2f13712f1` |
| GPUCC plus Adreno SMMU DTB | `da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| raw header-v3 boot image | `ce730ff01f76b455a751c9f5d7204e722cc62ee56e77dcd632fd9aaa2d692613` |
| temporary-boot AVB image | `37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |

The external GPUCC module is pinned separately and is not one of the
fourteen package-manifest entries.

The exact verifier also pins `mkbootimg.py`,
`unpack_bootimg.py`, and `avbtool` to
`d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a`,
`7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef`,
and
`6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff`,
respectively.

The complete exact-bundle verifier returns:

`PASS exact v18 GPUCC plus Adreno SMMU bundle; consumer-disabled, firmware-free, zero-storage, reproducible, and offline-only`

No binary artifact, credential, private identifier, or personal data is
committed.

## One-shot live gate

This offline result does not prove that the SMMU registers safely on this ASUS
board. One attended cycle may be reviewed separately. It must:

1. use only the exact temporary AVB image with `fastboot boot`, never flash;
2. preserve the atomic staging load-to-execute route and its initial fallback
   watchdog;
3. run the read-only baseline before disarming that initial watchdog;
4. place only the exact hash-pinned GPUCC module, disarm helper, and probe
   helper in target tmpfs;
5. atomically replace the initial watchdog with the independent 75-second
   SysRq watchdog before the one external GPUCC load;
6. accept only one GPUCC bind, one exact Adreno SMMU bind, runtime-suspended
   SMMU state, no GPU/GMU clients, firmware, render node, storage, warning,
   fault, or unsafe thermal state; and
7. normally reboot to the exact fallback after PASS, or allow the watchdog to
   force fallback after any non-returning operation.

There is no live retry. A PASS would accept only the idle SMMU prerequisite.
GPU/GX power, regulators, interconnects, GMU, reserved memory, firmware,
DRM/MSM, Mesa/Freedreno, display, suspend, and accelerated desktop remain
separate tiers.
