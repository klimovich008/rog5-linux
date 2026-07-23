# ROG Phone 5 native Linux

Reproducible bring-up work for native Arch Linux ARM on the ASUS ROG Phone 5 (`anakin`, Snapdragon 888 / SM8350). The target is a dependable phone-server with a minimal Plasma Desktop Wayland session, remote administration, screen-off operation, charging, Wi-Fi/VPN hotspot support, and upstream-style GPU acceleration. Alpine remains only in the proven vendor-kernel baseline and the small recovery environment. The long-term goal is a maintainable Linux 7.x board port.

This repository contains documentation, test tooling, configuration fragments, and artifact hashes. It intentionally does **not** contain proprietary firmware, credentials, personal data, Android partition dumps, or large boot images.

## Current result

The known-good temporary boot image runs vendor-derived kernel `5.4.210-qgki-perf #20`. Its smoke suite passes DRM/panel, touch, charging, USB networking, Plasma Mobile, power-button screen control, UPower, Wi-Fi client, and hotspot. The display defaults off while the server remains active.

One hard blocker remains: the vendor KGSL driver initializes Adreno 660 on the first `/dev/kgsl-3d0` open, but the second open fails while the GMU handles `PwrLimitsExitIdl`, followed by a CP page fault. This reproduces without Mesa and remains after disabling optional power features and forcing rails/clocks on. GPU acceleration is therefore not an accepted feature yet.

The Linux 7.1 recovery bundle passes its deterministic offline suite. Its
temporary vendor-compatible 5.4 staging kernel boots on the phone with
authenticated SSH, a verified nested payload, rollback, and zero storage
mounts. Linux 7.1 now reaches `/init`, configfs, and an internally configured
USB gadget, but Windows does not enumerate that gadget and target SSH remains
unreachable. Persistent ramoops plus automatic rollback remain the diagnostic
path; storage, the Arch rootfs, the desktop, and the mainline GPU tier have not
passed a live hardware gate.

The panel exposes four fixed modes named 144/120/90/60. Its DRM capability blob says `qsync support=false`, `dfps support=false`, and `dyn bitclk support=false`; this is fixed refresh-rate switching, not VRR.

See [current state](docs/current-state.md), [hardware contract](docs/hardware-contract.md), [builds and artifacts](docs/builds-and-artifacts.md), [subsystem status](docs/port-status.md), [recovery DTS](docs/recovery-dts.md), [remote GUI](docs/remote-gui.md), [Arch userspace](docs/arch-linux.md), [test plan](docs/test-plan.md), and [kernel port plan](docs/kernel-port.md).

## Safety model

- Use `fastboot boot`, never `fastboot flash`, until every mandatory gate passes.
- Keep the untouched Android/recovery slot as the fallback.
- Treat all boot images and extracted firmware as local artifacts.
- Redact serial numbers, full kernel command lines, Wi-Fi credentials, API keys, email, and CV data from reports.
- A newer version number is not success. Storage, USB, charging, thermals, display, input, radio stability, suspend, and GPU must each pass independently.

## Repository layout

```text
configs/kernel/       mainline configuration requirements
containers/           reproducible PC cross-build environment
docs/                 state, architecture, research, and operating guidance
manifests/            artifact identities and provenance (no binaries)
scripts/device/       recovery and Arch device tests, staging, and runtime tools
scripts/host/         PowerShell fastboot/SSH orchestration and validation
test-results/         redacted, reviewable test reports
```

## Quick start

Validate the repository and a local artifact directory:

```powershell
powershell -NoProfile -File scripts/host/Test-Repository.ps1 -ArtifactRoot C:\path\to\RogPhone
```

Temporarily boot an image and run the non-GPU smoke suite:

```powershell
powershell -NoProfile -File scripts/host/Test-Boot.ps1 `
  -BootImage C:\path\to\rog5-alpine-5.4.210-modular.img `
  -SshKey C:\path\to\rog5_ed25519 `
  -SshHost device-debug-address `
  -ExpectedKernel 5.4.210-qgki-perf
```

Validate that the mainline configuration fragment only uses symbols present in a kernel tree:

```powershell
powershell -NoProfile -File scripts/host/Test-KernelFragment.ps1 -KernelSource C:\src\linux-7.1.4
```

Cross-compile the pinned ARM64 kernel in Docker on an x86-64 PC:

```powershell
powershell -NoProfile -File scripts/host/Build-MainlineInDocker.ps1
```

Fetch and authenticate the Arch Linux ARM userspace input:

```powershell
powershell -NoProfile -File scripts/host/Get-ArchRootfs.ps1
```

Fetch and verify the pinned official Google `adb`/`fastboot` package:

```powershell
powershell -NoProfile -File scripts/host/Get-PlatformTools.ps1
```

Fetch and hash-check the pinned upstream A660 firmware set:

```powershell
powershell -NoProfile -File scripts/host/Get-A660Firmware.ps1
```

Fetch and authenticate the three small Alpine ARM64 packages used by the recovery loader:

```powershell
powershell -NoProfile -File scripts/host/Get-RecoveryPackages.ps1
```

Source and object files remain in named Docker volumes for fast incremental builds. Verified `Image.gz`, modules, configuration, metadata, comparison DTBs, and the ASUS recovery-contract skeleton are exported to `dist/linux-7.1.4/`. This compile-only result is not a boot image: neither the upstream DTBs nor the skeleton may be booted on the phone.

The signed Arch input and the earlier locked server rootfs pass their offline staging suites. The minimal Plasma Desktop target is being staged now and has not booted on the phone. The Arch rootfs remains outside the first RAM-only recovery and will not be mounted until USB recovery access and UFS discovery pass on hardware.

The ARM64 device-side compile helpers pin and verify the source before building. The first output is deliberately a compile-only upstream SM8350 comparison build; none of its existing board DTBs is safe to boot on this phone.

On the proven vendor-kernel baseline, the installed profiles are:

```sh
rog5-power-profile.sh server       # 60 Hz, DPMS off
rog5-power-profile.sh battery      # 60 Hz
rog5-power-profile.sh balanced     # 90 Hz
rog5-power-profile.sh performance  # 120 Hz
rog5-power-profile.sh maximum      # 144 Hz
```

All profiles retain `schedutil`; high refresh does not disable thermal management or force CPU clocks.

`scripts/device/install-runtime-tools.sh` installs the tested display and screen-control helpers used by the vendor-kernel baseline after backing up every replaced file under `/root/rog5-backups/`. The Arch target instead uses systemd, greetd, Plasma Wayland, and KRDP; neither path enables a public listener or flashes a boot image.

## Source baselines

- Stable device baseline: local vendor-derived `5.4.210-qgki-perf #20` artifact.
- Mainline research baseline: Linux `v7.1.4`, commit `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
- GodShell evaluation: commit `4530e0fdee0dc98bea20b268273d7a3e438ceb37`.
- postmarketOS audit: pmaports commit `29afb81ed2249d1ca0148a5dc6b4280bf0402af0`; no `anakin` device package was present.

## Definition of done

The project is complete only when a reproducible temporary boot passes the full mandatory matrix, survives repeated cold boots and idle periods, retains the fallback boot path, and has no unexplained kernel faults. Flashing a default kernel and connecting personal automation accounts are separate, explicit release decisions.
