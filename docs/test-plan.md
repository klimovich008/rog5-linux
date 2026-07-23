# Test plan

Tests are ordered so a failure never hides whether the phone can be recovered. A tier is attempted only after every mandatory test in the previous tier passes.

## Tier 0 — static build checks

- Kernel source revision is pinned and recorded.
- Board DTS compiles with `dtbs_check` warnings reviewed.
- Configuration fragment contains only real symbols.
- `Image`, DTB, modules, initramfs, and boot image hashes are recorded.
- Boot image contains no credentials or host-specific SSH private keys.
- Build logs contain no errors and are retained outside Git if large.
- `verify-mainline-build.sh` validates the compressed Image, artifact hashes, final boot/BTF config, and parseability of every comparison DTB.
- `verify-kexec-recovery-stage.sh` validates the staging kernel config, recovery DTB allowlist, both initramfs layers, nested payload hashes, boot header, AVB footer, and absence of private-key blocks.
- `build-gpu-recovery-initramfs.sh` preserves the recovery init, adds exactly the three hash-pinned A660 payloads, and reproduces the same archive byte-for-byte.

## Tier 1 — boot and recovery

- `fastboot boot` reaches the 5.4 kexec staging initramfs without flashing or mounting storage.
- USB ACM works even if USB networking has no address; SSH is optional in this first sub-tier.
- The staging rollback timer returns to the installed fallback kernel.
- The mainline payload loads, then starts only after a separate attended `kexec -e`.
- The Linux 7.1 target reports the expected release and its independent rollback timer works.
- UFS is discovered without errors while no filesystem is mounted.
- Watchdog/reset counters do not increase.
- A normal reboot still reaches the fallback slot.

## Tier 2 — core hardware

- USB NCM remains stable during sustained traffic.
- Battery capacity, voltage, current, temperature, and charging status are real.
- Thermal zones and CPU frequency policies are present.
- DRM connector, backlight, touch, and power button work.
- Screen-off state does not stop SSH, networking, or scheduled work.
- At least 30 minutes of idle and load operation produce no fatal kernel warnings.

## Tier 3 — networking and services

- Wi-Fi client associates and routes to the internet.
- Hotspot DHCP, DNS, NAT, and source-policy routing pass.
- Radio startup produces no modem watchdog, fatal interrupt, or WLAN RDDM.
- SSH is key-only and remote access is not exposed directly to the public internet.

## Tier 4 — display and desktop

- Plasma Mobile and Plasma Desktop can each start on physical DRM.
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
- The observability daemon runs under OpenRC or a supervised foreground service, not its upstream systemd unit.
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
