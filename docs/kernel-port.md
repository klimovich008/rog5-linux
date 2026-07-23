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
3. Compile a serial-only `sm8350-asus-rog-phone5.dts` skeleton, then add reviewed memory/reserved-memory references, UFS, and one USB controller. The skeleton itself is never booted.
4. Run `dtbs_check`, `make W=1`, and record warnings.
5. Produce `Image.gz`, the recovery-grade ASUS DTB, modules, initramfs, and a header-v3 temporary boot image with hashes.

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

The compile-only GPU tier is deliberately a two-node overlay: enable upstream `&gpu` and select the upstream SM8350 zap-shader path. Linux 7.1 already supplies the A660/GMU/SMMU hardware description and driver. The three matching payloads from `linux-firmware` 20260622 pass pinned hashes and the zap image is valid Qualcomm DSP6 ELF32. They remain outside Git and outside the recovery package until the base recovery boot passes on hardware.

### Phase G — observability and automation

Enable BTF/eBPF and run GodShell as an optional workload. Then add remote AI services under an unprivileged account and an explicit approval boundary for email/job actions.

## Two-stage recovery boot

ROG Phone 5 uses Android boot header v3, and the stock-style boot template has no DTB field. Passing the new ASUS DTB directly through a normal boot image is therefore not available without changing `vendor_boot`, which is outside the recovery safety boundary.

The offline candidate uses a reversible two-stage route:

1. `fastboot boot` starts an ASUS-source-compatible 5.4.210 kernel with only userspace `CONFIG_KEXEC` added. Nothing is flashed.
2. Its RAM-only initramfs contains the Linux 7.1 `Image`, recovery DTB, target initramfs, and signed Alpine ARM64 `kexec` runtime. It does not discover or mount userdata.
3. `rog5-load-mainline-recovery` verifies all three nested hashes and loads the mainline kernel, DTB, and initramfs. Execution remains a separate attended command.
4. Both the staging and target initramfs arm a 180-second forced-reboot timer. USB ACM is the address-free fallback; USB NCM and SSH may use DHCP or an explicitly supplied test address.

The recovery overlay enables only UFS and the reviewed left-side USB1 controller/PHY path. The bottom USB2 controller, display, charging, radios, remote processors, and GPU remain disabled. This package has passed offline tests but has not yet crossed the hardware boot gate.

## Non-goals

- No blind use of a generic SM8350 MTP DTB.
- No port of proprietary Android userspace GPU libraries into the final system.
- No persistent slot change until the full release gate passes.
- No attempt to enable every peripheral simultaneously; each subsystem must have a measurable pass/fail boundary.
- No bulk conversion of the 32k-line vendor DTS into mainline syntax; only reviewed board facts and nodes are carried forward.
