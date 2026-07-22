# Linux 7.x board-port plan

## Why 7.1.4

As of 2026-07-22, Linux 7.1.4 is the current stable kernel. It is a better research baseline than an unmaintained 6.7 SM8350 fork because upstream already contains SM8350 SoC support, the MSM DPU/DSI display stack, A660 GPU support, Qualcomm remoteproc, PMIC GLINK, UFS, and DWC3 infrastructure.

The missing piece is board support. Linux 7.1.4 has SM8350 DTS files for the Qualcomm HDK/MTP, Microsoft Surface Duo 2, and Sony Sagami devices, but no ASUS `anakin` DTS. postmarketOS pmaports at commit `29afb81e…` likewise has no ROG Phone 5 package; its generic SM8350 kernel package is archived and based on an old 6.7 fork.

This project therefore creates a new board DTS and minimal supporting drivers/quirks on top of upstream. It does not rewrite the Linux kernel from nothing.

Linux 6.18 is also retained as the LTS comparison branch because kernel.org projects maintenance through December 2028. Current-stable 7.1 is the development baseline; 6.18 is the eventual long-lived deployment candidate if it passes the same hardware matrix.

## Inputs

- Linux stable v7.1.4 source, pinned by commit.
- Running vendor device tree exported from `/sys/firmware/fdt` or `/proc/device-tree` for comparison only.
- ASUS-released kernel source and the working 5.4.210 configuration as behavioral references.
- Stock Android DTBO/vendor boot metadata and partition backups.
- Upstream SM8350 HDK, MTP, Surface Duo 2, and Sony Sagami DTS files.
- Locally extracted firmware, never committed.

## Bring-up phases

### Phase A — reproducible compile

1. Compile upstream `Image.gz` and known SM8350 DTBs natively on the phone to prove the pinned source and toolchain. These comparison DTBs must never be booted on the ASUS device.
2. Start the board port from `arm64 defconfig` plus `configs/kernel/rog5-mainline.fragment`.
3. Add a minimal `sm8350-asus-rog-phone5.dts` with model/compatible, chosen console, memory/reserved-memory references, UFS, and one USB controller.
4. Run `dtbs_check`, `make W=1`, and record warnings.
5. Produce `Image.gz`, the ASUS DTB, modules, initramfs, and a header-v3 temporary boot image with hashes.

### Phase B — recovery-grade boot

Only console, UFS root, USB NCM, SSH, watchdog visibility, and reboot are required. Display, radio, charging, audio, cameras, and GPU remain disabled. The image is used only with `fastboot boot`.

### Phase C — power and charging

Port PMIC GLINK/battery telemetry, Type-C role detection, charging, thermal zones, and CPU/GPU cooling. Validate current direction and battery temperature before enabling performance modes.

### Phase D — input and display

Add the exact AMS678 ER2 panel description, DSI DSC timings, FocalTech touch, backlight, and power button. The vendor display chain also contains a Pixelworks Iris/i6 processor and per-mode light-up configuration; Linux 7.1.4 has no matching upstream bridge driver. Determine whether a safe pass-through mode exists or port the minimal bridge initialization before treating display as available. Implement fixed 60/90/120/144 modes; do not claim VRR because the panel advertises no qsync/DFPS support.

### Phase E — radio and remote processors

Bring up ADSP/CDSP/modem/SLPI one at a time with correct reserved memory and firmware paths. Add Wi-Fi only after remoteproc and power stability. Preserve the known radio startup delay until measurement proves it unnecessary.

### Phase F — mainline GPU

Use upstream DRM/MSM Freedreno rather than vendor KGSL. Validate A660 firmware, IOMMU mappings, GMU idle transitions, repeated render-node opens, Turnip, and KWin. This is expected to remove the current vendor KGSL second-open failure, but it is not assumed until tested.

### Phase G — observability and automation

Enable BTF/eBPF and run GodShell as an optional workload. Then add remote AI services under an unprivileged account and an explicit approval boundary for email/job actions.

## Boot-image constraint

ROG Phone 5 uses Android boot header v3; the current boot image does not carry a DTB field. The mainline board DTB must therefore be supplied using a tested bootloader-compatible method (commonly an appended DTB or the appropriate vendor-boot path). This is a Phase A artifact test, not something to guess during a live flash.

## Non-goals

- No blind use of a generic SM8350 MTP DTB.
- No port of proprietary Android userspace GPU libraries into the final system.
- No persistent slot change until the full release gate passes.
- No attempt to enable every peripheral simultaneously; each subsystem must have a measurable pass/fail boundary.
- No bulk conversion of the 32k-line vendor DTS into mainline syntax; only reviewed board facts and nodes are carried forward.
