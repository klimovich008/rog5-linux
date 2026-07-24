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

1. Cross-compile upstream `Image.gz` and known SM8350 DTBs on the PC to prove the pinned source and toolchain. These comparison DTBs must never be booted on the ASUS device.
2. Start the board port from `arm64 defconfig` plus `configs/kernel/rog5-mainline.fragment`.
3. Compile a serial-only `sm8350-asus-rog-phone5.dts` skeleton, then add reviewed memory/reserved-memory references, UFS, and one USB controller. The skeleton itself is never booted.
4. Run `dtbs_check`, `make W=1`, and record warnings.
5. Produce `Image.gz`, the recovery-grade ASUS DTB, modules, initramfs, and a header-v3 temporary boot image with hashes.

### Phase B — recovery-grade boot

Only console, a RAM-only initramfs, USB NCM/ACM, SSH, watchdog visibility, and reboot are required. UFS remains disabled until host-visible remote recovery works. Display, radio, charging, audio, cameras, and GPU remain disabled. The image is used only with `fastboot boot`.

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

Enable BTF/eBPF and run GodShell as an optional systemd-managed workload. Then add remote AI services under an unprivileged account and an explicit approval boundary for email/job actions.

## Two-stage recovery boot

ROG Phone 5 uses Android boot header v3, and the stock-style boot template has no DTB field. Passing the new ASUS DTB directly through a normal boot image is therefore not available without changing `vendor_boot`, which is outside the recovery safety boundary.

The v18 candidate uses this intended reversible two-stage route:

1. `fastboot boot` starts an ASUS-source-compatible 5.4.210 kernel with the staging initramfs built into the kernel. Nothing is flashed.
2. The built-in initramfs contains the Linux 7.1 `Image`, USB2-only recovery DTB, target initramfs, and signed Alpine ARM64 `kexec` runtime. Its offline contract contains no storage-mount logic.
3. `rog5-load-mainline-recovery` verifies all three nested hashes, disables and verifies the single Haven hypervisor watchdog, and loads the mainline kernel, DTB, and initramfs. Execution remains a separate attended command.
4. Both the staging and target initramfs arm a 180-second forced-reboot timer,
   reject block-backed mounts, apply and verify `BLKROSET` on every enumerated
   physical disk and partition, and expose USB only after that gate passes.
   Volatile loop, RAM, and zram objects remain writable. USB ACM is the
   credential-free fallback; USB NCM may use an explicitly supplied test
   address.

The recovery overlay enables only the reviewed `usb_1` wrapper and its
high-speed FEMTO PHY. The DWC3 child uses one `usb2-phy`; UFS, QMP/SuperSpeed,
the secondary `usb_2` controller, display, charging, radios, remote processors,
and GPU remain disabled. The overlay passes static inspection. The v6 bundle
passed its then-current offline verifier but failed live ACM data and rollback;
recovery v12 rebuilt the dependency chain but remained unbooted because it
lacked the pre-USB block-device lock. V13 added an all-block-device gate and
v14 narrowed it to physical storage, but both returned to fallback after 21
seconds without exact recovery USB. V15 reproduced the chain with bounded
failure delays; its exact 31-second live return identified the unnecessary
wake-lock gate before storage isolation. V16 removes that gate and all timing
delays while retaining the watchdog and physical-storage boundary. It reached
exact USB, NCM, and rollback but lacked `/dev/ttyGS0`. A local keyed v17
diagnostic proved the RAM-backed root, zero block mounts, all 116 physical
nodes read-only, and the live `mdev -s` ACM fix. V18 makes that rescan and a
second storage gate mandatory before USB binding. Its duplicate builds and
offline verifier pass. V18 staging and rollback now also pass twice with RAM
root, zero block mounts, 116 read-only physical nodes, ACM/NCM, and changed
fallback boot identities. One separately attended Linux 7.1 kexec attempt is
now eligible.

The historical v2 image produced staging and Linux 7.1.4 logs, including
target `/init`, NCM/ACM configuration, the `a600000` UDC, and `usb0`. It did
not, however, satisfy the claimed recovery boundary: its staging `/` was
writable physical UFS, and its target DTB enabled UFS and QMP/SuperSpeed.
Nothing was flashed, but v2 is superseded and must not be booted. Its logs
remain diagnostic evidence for the TLMM GPIO 52 reservation and built-in FEMTO
PHY work, not proof that the corrected RAM-only path passes. The raw ramoops
and bootloader restart-reason module sources are under `tools/diagnostics/`.

## Non-goals

- No blind use of a generic SM8350 MTP DTB.
- No port of proprietary Android userspace GPU libraries into the final system.
- No persistent slot change until the full release gate passes.
- No attempt to enable every peripheral simultaneously; each subsystem must have a measurable pass/fail boundary.
- No bulk conversion of the 32k-line vendor DTS into mainline syntax; only reviewed board facts and nodes are carried forward.
