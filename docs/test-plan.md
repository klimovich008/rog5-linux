# Test plan

Tests are ordered so a failure never hides whether the phone can be recovered. A tier is attempted only after every mandatory test in the previous tier passes.

## Tier 0 — static build checks

- Kernel source revision is pinned and recorded.
- Board DTS compiles with `dtbs_check` warnings reviewed.
- Configuration fragment contains only real symbols.
- `Image`, DTB, modules, initramfs, and boot image hashes are recorded.
- The first recovery candidate is `acm-only` and contains no
  `authorized_keys`, credentials, or host-specific SSH private keys.
- Build logs contain no errors and are retained outside Git if large.
- `verify-mainline-build.sh` validates the pinned Python hash seed, raw and
  compressed Images, artifact hashes, final boot/BTF config, and parseability
  of every comparison DTB.
- `compare-mainline-builds.sh` rejects the same directory through aliases and
  requires byte-identical configuration, raw and compressed kernels, module
  archive, metadata, and all reviewed DTBs from two fresh output directories.
- `verify-kexec-recovery-stage.sh` requires an explicit `acm-only` or `ssh`
  access mode and a separately recorded artifact SHA-256 manifest, then
  validates the staging kernel config, recovery DTB allowlist, both initramfs
  layers, nested payload hashes, boot header, AVB footer, and access material.
- The base board-DTB check requires the TLMM 52-59 reservation and all eight translated ASUS HS-PHY tuning properties.
- The recovery DTB check requires USB2 high-speed operation, a built-in FEMTO PHY, exactly one USB PHY reference, and disabled UFS, QMP/SuperSpeed, and secondary USB.
- `build-gpu-recovery-initramfs.sh` preserves the recovery init, adds exactly the three hash-pinned A660 payloads, and reproduces the same archive byte-for-byte.
- `verify-staged-arch-rootfs.sh` checks the requested packages, modules, firmware, locked accounts, key-only SSH, NetworkManager ownership, headless/no-autologin default, on-demand ttyd/Chromium, Plasma/KRDP tools, and absence of baked network or remote-desktop credentials.
- `test-screen-toggle.sh` and `test-vpn-hotspot.sh` exercise idempotent display state and AP-scoped fail-closed nftables rules without phone hardware.
- `test-load-mainline-recovery.sh` rejects non-Haven watchdog controls and rollback timeouts outside 30-900 seconds before loading kexec.
- `verify-ufs-discovery-patch.sh` applies the three-patch discovery series to
  the pinned tree, enforces exact query/SCSI whitelists, rejects
  data-to-device and bidirectional payloads, proves discovery returns before
  runtime-PM/BKOPS and shutdown transitions, and compiles the guarded
  SCSI/UFS objects.
- `verify-ufs-discovery-bundle.sh` requires exactly thirteen manifest-pinned
  products, rebuilds the reviewed UFS/USB2 DTB, verifies both nested
  credential-free initramfs layers, and checks the wrapper, boot header,
  command line, and AVB footer.
- `verify-network-root-bundle.sh` requires exactly fourteen manifest-pinned
  products, delegates the dedicated kernel and target-initramfs checks,
  rejects an enabled UFS path or UFS module, verifies both credential-free
  initramfs layers and nested hashes, and checks the wrapper, boot header,
  command line, and AVB footer.
- `test-linux-rootfs-tools.sh` checks the pinned signed-Arch input path,
  metadata-preserving rootfs stage path, exact network-root module input, and
  absence of broad container privilege or phone-write commands.
- `recovery-linux.sh preflight` requires an explicit manifest-pinned image and
  exactly one fastboot target; no candidate is selected by default and `boot`
  remains inert unless `ALLOW_TEMPORARY_BOOT=1` is explicit. Recovery ACM detection requires exact
  normalized product `ROG5_recovery`; the fallback gadget sharing
  `1d6b:0104` is a hard failure.
- `network-root-acm.py` replaces terminal attachment with three fixed staging
  actions, `O_NOCTTY`, exact recovery-gadget discovery, a separate attended
  kexec guard, and sanitized console output. Its pseudoterminal regression
  proves cursor-position queries are never returned as shell input.
- Build diagnostic modules under `tools/diagnostics/` only against the exact fallback kernel, and record their local hashes before use.

## Tier 1 — boot and recovery

- `fastboot boot` reaches the 5.4 kexec staging initramfs without flashing or mounting storage.
- The first candidate exposes supervised USB ACM without credentials or SSH;
  USB networking may remain unaddressed in this sub-tier.
- The staging rollback timer returns to the installed fallback kernel.
- The v15 diagnostic maps approximately 21/31/51/71-second fallback intervals
  to pre-`/init`, wake-lock, block-backed-mount, and physical-lock paths; it
  stopped after the 31-second wake-lock result and never ran kexec.
- V16 exposed exact `ROG5_recovery`, NCM, and automatic rollback but lacked an
  ACM device node. V17 proved the RAM/storage gates and live rescan fix.
- V18 exposed credential-free ACM, proved a RAM-backed root and read-only
  physical storage, and returned through its 180-second watchdog twice. The
  separate attended kexec then passed Linux 7.1 RAM-root, zero-storage,
  ACM/NCM, watchdog, fatal-log, and automatic rollback checks.
- Before exposing USB, both stages reject any block-backed mount and use
  `BLKROSET` through `blockdev --setro`; every physical disk and partition
  must report read-only. Volatile loop, RAM, and zram devices are excluded.
- After creating the ACM function, both stages must rescan device nodes,
  require `/dev/ttyGS0`, and repeat the storage gate before ACM or UDC binding.
- The mainline payload loads, then starts only after a separate attended `kexec -e`.
- Before kexec, exactly one Haven hypervisor watchdog control is disabled and verified; a secure-watchdog deactivation failure aborts the test.
- The Linux 7.1 target reports the expected release, starts `/init`, mounts configfs, configures NCM/ACM, binds the expected UDC, creates `usb0`, and runs its independent rollback timer.
- The host enumerates the target NCM or ACM function and target SSH becomes reachable.
- If host enumeration fails, record UDC state and `usb0` carrier, allow the rollback timer to recover the phone, then capture the reserved region with `tools/diagnostics/ramoops-raw` before changing hardware enablement.
- UFS remains disabled and the target has zero block-device mounts.
- Watchdog/reset counters do not increase unexpectedly.
- A normal reboot still reaches the fallback slot.

## Tier 1.5 — read-only UFS discovery

Status: **passed by discovery v2**. Exact `7.1.4-gcfd385a1c754` exposed all
116 physical nodes read-only with zero blocked commands and no UFS
error-handler signature, then the untouched watchdog chain automatically
restored the exact fallback kernel.

- Use only the dedicated compile-time discovery kernel and its exact
  UFS/USB2 DTB; no normal mainline image is interchangeable.
- Arm rollback before enumeration and attest
  `CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y` from `/proc/config.gz`.
- Require at least one physical UFS disk while retaining zero block-backed
  mounts.
- Require every disk and partition to report read-only through sysfs and the
  block ioctl before ACM/NCM is exposed.
- Collect only the sysfs topology inventory; do not run `blkid`, mount, fsck,
  partitioning tools, raw-device reads, or write tests.
- Require the Qualcomm UFS driver, forbidden host/WLUN runtime PM,
  auto-hibern8 disabled, zero blocked commands, exact compiled guard markers,
  working ACM/NCM, no UFS error handler or fatal log signature, and orderly
  automatic return to the exact fallback kernel.
- Require rollback to arm an independent delayed SysRq reset before starting
  `reboot -f` in the background, so shutdown cannot block the fallback path.
- Treat the resulting topology as design input only. Persistent rootfs or
  partition changes require a later explicit authorization.

## Tier 1.75 — UFS-disabled network root

Status: **offline, privileged host, normal-coldplug, and retained-exitrd reboot
gates passed**. Persistent storage and hardware bring-up remain isolated.

- Use only the fourteen-file manifest-pinned network-root bundle.
- Require built-in NFSv4.2, TCP, OverlayFS, tmpfs xattrs, USB ACM/NCM, and
  `/proc/config.gz`.
- Require SCSI/UFS, SCSI disk/BSG/RPMB, and UFS/combo/PCIe/SuperSpeed QMP PHY
  paths to be absent from the final kernel config and module archive.
- Keep the accepted USB2 recovery DTB with UFS and its PHY disabled.
- Restrict the host NFSv4 export to `169.254.77.2` on the dedicated USB
  interface, export it read-only, and remove the runtime export/firewall rule
  after the attended test.
- Run `test-network-root-host.sh` before privilege; require a fixed
  NFSv4.2-only listener address, exact gadget identity, read-only bind mount,
  dedicated drop-by-default zone, pre-zone drops for broad host zones, and
  cleanup traps.
- Require read-only NFS lower, 2 GiB `nodev,nosuid` tmpfs upper, OverlayFS
  `/`, zero physical block devices, and zero block-backed mounts before
  accepting userspace.
- Boot `multi-user.target`, leave `usb0` unmanaged, and require key-only SSH.
- Verify exact kernel release, systemd state, nested mounts, watchdog, stable
  USB traffic, no fatal log signature, and automatic return to fallback.
- Require the default loader path to carry no systemd mask. Diagnostic mode
  may mask only the two named coldplug/module units and must fail before kexec
  for any other value.
- The diagnostic target must reach running systemd, active
  `multi-user.target`, key-only root and unprivileged SSH, zero failed units,
  and a controlled watchdog disarm. **Passed twice.**
- Replay coldplug candidates only through the explicit allowlisted probe with
  an independent process-group watchdog. **Passed; `gpucc_sm8350` isolated as
  the live stall, and overlapping `rmtfs_mem` rejected by DT review.**
- Require the recovery DT contract to disable RMTFS, GPUCC, GPU, GMU, and the
  Adreno SMMU. **Passed reproducibly and in two normal-coldplug boots.**
- Require persistent client authorization plus one pinned server host
  identity to pass strict verification across two boots. **Passed.**
- Require `/run/initramfs/shutdown` to match the reviewed source and execute
  with its retained AArch64 BusyBox/musl runtime. Unmount OverlayFS before its
  tmpfs and NFS backing filesystems, then prove normal `systemctl reboot`
  returns to the exact fallback and removes all host runtime state.
  **Passed once with v3; repeated clean cycles remain a Phase 4 gate.**
- Keep v4 as rejected RTC evidence only: the raw PMK8350 clock was near the
  Unix epoch and set Linux about 56 years behind the host. Require no RTC,
  system-clock, offset-storage, or phone-storage write in this tier.
- For v5 diagnostic input isolation, require RTC disabled, `qcom_pon` absent
  and zero power-key events before the guarded probe, then require the
  watchdog safely disarmed, `qcom_pon` loaded, exactly one
  `pmic_pwrkey`/`pm8941-pwrkey` event, `KEY_POWER`, wakeup enabled, unchanged
  NFS/USB/storage boundaries, and a clean systemd reboot to fallback.
  **Dependency plus diagnostic and normal registration/reboot passed. The
  fail-resumable disarm helper passed live; physical press remains pending
  after a protected 120-second window received no confirmed event.**
- Run `monitor-network-root-pwrkey.sh` only after the full normal-mode gate and
  watchdog disarm. Require its explicit guard, exact storage/NFS/RTC/input
  state, low-level logind inhibitor, and both `KEY_POWER` press and release
  records before accepting the physical switch/IRQ path.
- Before TLS, package, or automation tests, run
  `sync-network-root-time.sh` while the rollback watchdog is still armed.
  Require an NTP-synchronized host, strict dedicated SSH identity, normal
  unmasked Linux, read-only NFS/OverlayFS, zero storage, RTC disabled and
  absent, exact USB state, and no failed/fatal state before and after changing
  only the volatile Linux system clock. **Offline fake-SSH contract and live
  `changed=1` correction of a 2,378,466-second drift passed; independent host
  interval, normal reboot, and cleanup passed.**
- Require the board DTS to reserve the exact three stock-owned RAM spans
  before enabling any remote processor. For the ADSP-only gate, keep every
  other remote processor and PMIC GLINK disabled, stage exact stock firmware
  only in tmpfs, arm an independent SysRq watchdog, and require PAS/SCM
  success, ADSP `running`, only the reviewed PAS/GLINK plus `qrtr` module set,
  zero power supplies/storage, stable USB/NFS, clean logs, and fallback
  restoration. **Passed twice at the hardware boundary; the second run
  passed the complete corrected harness.**
- Treat display, battery values, charging, radio, physical input actuation,
  and GPU as untested despite the normal headless coldplug, input
  registration, and accepted ADSP prerequisite.

## Tier 2 — core hardware

- USB NCM remains stable during sustained traffic.
- Battery capacity, voltage, current, temperature, and charging status are real.
- Thermal zones and CPU frequency policies are present.
- DRM connector, backlight, and touch work; a physically observed short
  power-button press traverses the switch/IRQ/input path. Driver registration
  alone does not satisfy this gate.
- Screen-off state does not stop SSH, networking, or scheduled work.
- At least 30 minutes of idle and load operation produce no fatal kernel warnings.

## Tier 3 — networking and services

- Wi-Fi client associates and routes to the internet.
- Hotspot DHCP, DNS, NAT, and source-policy routing pass.
- Radio startup produces no modem watchdog, fatal interrupt, or WLAN RDDM.
- SSH is key-only and remote access is not exposed directly to the public internet.

## Tier 4 — display and desktop

- Plasma Desktop Wayland starts on physical DRM and KRDP shares that session.
- Screen wakes on power-button press and returns to the configured blank timeout.
- Fixed 60/90/120/144 mode selection is verified visually and from the active DRM/KScreen state.
- 60 Hz idle is the default; mode changes do not blank permanently or reset the panel.
- Remote admin UI remains available independently of the physical compositor.

## Tier 5 — GPU (opt-in, run last)

- Raw KGSL or DRM render-node open/close/open cycle succeeds repeatedly.
- `vulkaninfo --summary` succeeds at least ten consecutive times.
- A headless Vulkan submit and a rendered Wayland workload pass.
- KWin runs with hardware acceleration and without llvmpipe.
- Suspend/idle/wake cycles do not produce GMU HFI errors or IOMMU faults.
- Power use with GPU idle remains acceptable.

The script `scripts/device/kgsl-open-cycle.sh` requires `ALLOW_GPU_FAULT_TEST=1` because the current vendor driver is known to fail this tier.

## Tier 6 — observability and automation

- BPF syscall/JIT, BTF, tracepoints, kprobes, and uprobes are enabled.
- GodShell can load its ARM64 programs without verifier errors.
- The observability daemon runs as a restricted systemd service on the Arch target.
- AI/email/CV automation runs as an unprivileged account with scoped tokens and an approval queue for external actions.

## Release gates

Before any persistent flash:

- three cold boots
- three warm reboots
- one four-hour idle run with screen off
- one sustained CPU/network load run
- charging from low battery through a meaningful interval
- complete redacted report with all mandatory tiers
- verified recovery/fallback procedure
