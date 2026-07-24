# ROG Phone 5 native Linux

Reproducible bring-up work for native Arch Linux ARM on the ASUS ROG Phone 5 (`anakin`, Snapdragon 888 / SM8350). The target is a dependable phone-server with a minimal Plasma Desktop Wayland session, remote administration, screen-off operation, charging, Wi-Fi/VPN hotspot support, and upstream-style GPU acceleration. Alpine remains only in the proven vendor-kernel baseline and the small recovery environment. The long-term goal is a maintainable Linux 7.x board port.

This repository contains documentation, test tooling, configuration fragments, and artifact hashes. It intentionally does **not** contain proprietary firmware, credentials, personal data, Android partition dumps, or large boot images.

## Current result

The known-good temporary boot image runs vendor-derived kernel `5.4.210-qgki-perf #20`. Its smoke suite passes DRM/panel, touch, charging, USB networking, Plasma Mobile, power-button screen control, UPower, Wi-Fi client, and hotspot. The display defaults off while the server remains active.

One hard blocker remains: the vendor KGSL driver initializes Adreno 660 on the first `/dev/kgsl-3d0` open, but the second open fails while the GMU handles `PwrLimitsExitIdl`, followed by a CP page fault. This reproduces without Mesa and remains after disabling optional power features and forcing rails/clocks on. GPU acceleration is therefore not an accepted feature yet.

The historical v2 recovery image temporarily booted and produced logs showing
Linux 7.1 reaching `/init`, configfs, and an internally configured USB gadget.
A later audit invalidated its safety classification: the v2 staging `/` was a
writable physical UFS filesystem, and its target DTB enabled UFS and the
QMP/SuperSpeed PHY. Nothing was flashed, but v2 is superseded and must not be
booted again.

The later v6 candidate embedded the staging initramfs in the 5.4 kernel and
used a USB2-only target DTB with UFS and QMP disabled. It passed its then-current
offline suite, but live ACM data and automatic rollback failed, so v6 is also
rejected. Source fixes for both failures and a fresh Linux 7.1 build exist;
two clean Linux 7.1 kernel/module/DTB builds are now byte-identical. The
credential-free v12 target/staging initramfs, ASUS wrapper, and temporary boot
image were each rebuilt twice and are byte-identical. The complete offline
verifier passes in explicit `acm-only` mode, including the PM wake-lock,
USB2-only DTB, nested hashes, boot-header, AVB, and no-authorized-key checks.
V12 was not booted: a final audit found that it did not force block devices
read-only before exposing USB, so it is superseded. Recovery v13 adds a
fail-closed pre-USB storage gate to both initramfs layers: it rejects any
block-backed mount, applies and verifies `BLKROSET` on every enumerated block
device, and forces rollback on any failure. Its complete credential-free
dependency chain and temporary boot image were independently reproduced and
pass the expanded offline verifier. Its first temporary boot returned to the
fallback system before the exact recovery USB identity appeared, so v13 is
rejected. The host workflow also exposed and fixed an identity bug: recovery
and fallback share `1d6b:0104`, so the exact product string is now mandatory.

Recovery v14 keeps the block-backed-mount rejection but applies `BLKROSET`
only to physical disks and their partitions, excluding volatile loop, RAM,
and zram objects. Two complete clean builds and two repacks are byte-identical,
and the expanded offline verifier passes. Its live attempt nevertheless
returned to fallback in the same 21-second interval without recovery USB, so
v14 is also rejected.

Recovery v15 was a diagnostic-only timing image. Its temporary boot returned
to fallback in exactly 31 seconds, selecting the 10-second wake-lock failure
branch and proving `/init` ran before storage isolation. The wrapper has
`CONFIG_PM_AUTOSLEEP` disabled and recovery has no userspace power manager, so
that wake-lock gate was unnecessary. Recovery v16 removed it and reached exact
recovery USB, working NCM, and automatic rollback, but ACM returned no shell
data. An authorized local v17 SSH diagnostic proved the root was RAM-backed,
there were zero block-backed mounts, all 116 physical devices were read-only,
and the watchdog worked. It isolated ACM to a missing `/dev/ttyGS0` node; a
live `mdev -s` rescan immediately restored the shell. Recovery v18 makes that
rescan fail-closed, requires the node, and repeats storage isolation before
binding USB. Two complete v18 builds and repacks are byte-identical, and the
network-isolated verifier passes. Two credential-free live staging/rollback
cycles now pass with RAM root, zero block mounts, all 116 physical devices
read-only, ACM/NCM, no SSH, and changed fallback boot identities. The nested
Linux 7.1 recovery is eligible for one separate attended kexec attempt. Arch
rootfs, desktop, and mainline GPU gates remain pending.

The panel exposes four fixed modes named 144/120/90/60. Its DRM capability blob says `qsync support=false`, `dfps support=false`, and `dyn bitclk support=false`; this is fixed refresh-rate switching, not VRR.

See the [project roadmap](ROADMAP.md), [current state](docs/current-state.md),
[hardware contract](docs/hardware-contract.md),
[builds and artifacts](docs/builds-and-artifacts.md),
[subsystem status](docs/port-status.md), [recovery DTS](docs/recovery-dts.md),
[remote GUI](docs/remote-gui.md), [Arch userspace](docs/arch-linux.md),
[test plan](docs/test-plan.md), and [kernel port plan](docs/kernel-port.md).

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
scripts/host/         Linux/PowerShell fastboot, SSH, and build orchestration
test-results/         redacted, reviewable test reports
```

## Quick start

On the current Nobara Linux development host, install the native Android tools
and grant serial access once, then log out and back in:

```sh
sudo dnf install android-tools
sudo usermod -aG dialout "$(id -un)"
```

The Linux recovery workflow is read-only by default. It validates the exact
manifest-pinned image and requires exactly one fastboot device. Rejected
candidates are never selected by default:

```sh
BOOT_IMAGE="$PWD/artifacts/recovery-stage-vNN/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" \
  scripts/host/recovery-linux.sh preflight
```

The attended temporary boot has a separate explicit guard and invokes only
`fastboot boot`. It never flashes:

```sh
ALLOW_TEMPORARY_BOOT=1 \
BOOT_IMAGE="$PWD/artifacts/recovery-stage-vNN/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" \
  scripts/host/recovery-linux.sh boot
```

After ACM enumerates, the script prints the `socat` command for the
credential-free recovery shell. Its 180-second rollback remains armed.

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

Source files remain in a named Docker volume. Each default PC build uses a
fresh object volume so stale objects cannot contaminate a release candidate;
the retained volume name is printed for audit. Verified `Image`, `Image.gz`,
modules, configuration, metadata, comparison DTBs, and the ASUS
recovery-contract skeleton plus USB2 recovery DTB are exported to
`dist/linux-7.1.4/`. This compile-only result is not a boot image: neither the
upstream DTBs nor the standalone ASUS DTBs may be booted directly on the phone.

The signed Arch input and the locked minimal Plasma Desktop rootfs pass their
historical offline staging suites, but the archive contains the previous
kernel modules and must be restaged after the final kernel is accepted. No
Arch image has booted on the phone. It remains outside the first RAM-only
recovery and will not be mounted until USB recovery access and UFS discovery
pass on hardware.

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
