# ROG Phone 5 native Linux

Reproducible bring-up work for native Arch Linux ARM on the ASUS ROG Phone 5 (`anakin`, Snapdragon 888 / SM8350). The target is a dependable phone-server with a minimal Plasma Desktop Wayland session, remote administration, screen-off operation, charging, Wi-Fi/VPN hotspot support, and upstream-style GPU acceleration. Alpine remains only in the proven vendor-kernel baseline and the small recovery environment. The long-term goal is a maintainable Linux 7.x board port.

This repository contains documentation, test tooling, configuration fragments, and artifact hashes. It intentionally does **not** contain proprietary firmware, credentials, personal data, Android partition dumps, or large boot images.

## Current result

The known-good temporary boot image runs vendor-derived kernel `5.4.210-qgki-perf #20`. Its smoke suite passes DRM/panel, touch, charging, USB networking, Plasma Mobile, power-button screen control, UPower, Wi-Fi client, and hotspot. The display defaults off while the server remains active.

For the mainline userspace path, the fail-closed hotspot policy now passes a
real packet regression in isolated, network-disabled namespaces: only the
simulated VPN path works; IPv4/IPv6 ordinary-uplink leakage, unsolicited
client ingress, and VPN-loss fallback are blocked; cleanup is exact. Radio,
real WireGuard, DHCP/DNS, throughput, thermal, and battery acceptance remain
hardware gates.

The newer Arch development root now also passes its full stage and clean
archive round trip with a locked `rog5-agent` account. Its on-demand Chromium
service is loopback-only, cannot reuse the Plasma user's home or credentials,
has no device access or capabilities, and can write only its private
`/var/lib/rog5-agent` state. No email, CV, browser session, API token, or
provider account is present. This artifact is verified offline but has not
replaced the live-tested network root or run on the phone.

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
read-only, ACM/NCM, no SSH, and changed fallback boot identities. The separate
attended kexec gate now also passes: Linux `7.1.4-g7a5cef0db479` reached its
RAM-only recovery with zero physical block devices, working ACM/NCM and
watchdog, no fatal log signatures, and automatic return to a changed fallback
boot identity. The corrected read-only UFS discovery v2 gate also passes:
Linux `7.1.4-gcfd385a1c754` enumerated all 116 UFS disks and partitions
read-only with zero blocked commands, disabled auto-hibern8, pinned-active
runtime PM, no UFS error handler, and automatic fallback recovery. Arch/Debian
network root now also passes its complete offline reproducibility gate: two
Linux 7.1.4 builds, two target/staging initramfs builds, two ASUS wrappers, and
two header-v3/AVB repacks are byte-identical. The dedicated kernel has
NFSv4.2/OverlayFS built in and compiles SCSI/UFS/QMP storage paths out. The
signed Arch input and the final 2,007,186,653-byte headless-first Plasma
rootfs pass Linux-native staging and archive round-trip verification with the
exact network-root modules and pinned A660 firmware. The restricted host
NFS harness now also passes its privileged runtime gate on Nobara: one
NFSv4.2/TCP listener on the USB address, one exact-peer read-only export, a
successful isolated client mount, no persistent firewall state, and complete
cleanup. Four early normal boots localized a deterministic reset to hardware
coldplug. Attended, rollback-guarded module isolation then proved
`gpucc_sm8350` stalls and showed that `rmtfs_mem` overlaps the recovery
ramoops reservation. Network-root v2 disables RMTFS, GPUCC, GPU, GMU, and the
Adreno SMMU in the recovery DTB. Two normal, unmasked boots now pass exact
Linux 7.1.4, running systemd, successful udev coldplug, `multi-user.target`,
key-only SSH, OverlayFS with read-only NFS lower, zero physical storage,
stable USB/NFS, zero failed units, sane thermals, and safe watchdog disarm.
Client authorization and a single pinned server host identity also persist
across boots. Network-root v3 now retains a minimal shutdown initramfs that
unmounts OverlayFS before its tmpfs and NFS backing filesystems. Its attended
normal `systemctl reboot` test returned to the persistent fallback in about
25 seconds, with strict fallback SSH and complete NFS/firewall cleanup.
Network-root v7 also passes the isolated ADSP prerequisite after adding the
exact stock-owned ASUS RAM spans. Network-root v8 then passes one guarded
read-only SM8350 battery snapshot through the audited QRTR/PDR and
battery-only PMIC GLINK path. Charging, Type-C control, sustained
current-direction validation, display, and GPU remain isolated.
Network-root v9 independently reproduced a GPUCC-only diagnostic with every
GPU consumer disabled. V10 then added a default-off, exact-compatible trace to
the built-in Qualcomm common-clock path. Duplicate clean kernels, matching
module archives, wrappers, and packages were byte-identical. The guarded live
trace completed mapping, both PLL configurations, reset registration, and both
GDSC steps, then stopped while registering clock index 0
(`gpu_cc_ahb_clk`). Its independent watchdog restored the exact fallback and
complete host cleanup passed. Source analysis does not prove an access to the
branch register: this clock is non-critical and should enter CCF as an orphan.
Network-root v11 passed its offline gate and the attended RAM-only probe. The
trace completed allocation, prepare-lock/runtime-PM, parent lookup, orphan
insertion, phase/duty/rate, and the non-critical branch for
`gpu_cc_ahb_clk`, then stopped inside
`clk_core_reparent_orphans_nolock()`. Its independent watchdog restored the
exact fallback and complete cleanup passed. The result does not prove GPUCC
MMIO: the generic scan can inspect or reparent any existing orphan clock.
Network-root v12 passed its complete offline gate and one attended RAM-only
probe. The global scan completed the no-parent entry for newly registered
`gpu_cc_ahb_clk`, advanced to the existing
`disp_cc_mdss_pclk0_clk_src` orphan, and stopped inside that clock's
`__clk_init_parent()` call. Source order places its display RCG
`get_parent()` callback before CCF's cached-parent lookup, but v12 does not yet
distinguish those operations or prove a register access. The independent
watchdog restored the exact fallback and complete host cleanup passed. GPUCC
remains rejected. Network-root v13 passed its complete offline gate and one
attended RAM-only probe. It recorded the display orphan as a three-parent
clock whose runtime-PM-enabled provider was suspended, then entered
`disp_cc_mdss_pclk0_clk_src`'s `get_parent()` callback without reaching the
callback-complete or later parent-cache markers. Source maps that callback to
`clk_rcg2_get_parent()`, whose first substantive operation is a regmap read,
but v13 does not instrument inside the callback and therefore does not prove
that read began or identify a register access as the cause. The independent
watchdog restored the exact fallback and complete host cleanup passed. A
runtime resume must not simply be added while CCF's global `prepare_lock` is
held because provider callbacks may need the same lock. Network-root v14
passed the complete offline successor gate and one attended RAM-only
diagnostic. Its exact-clock markers reached `parent-read-begin` immediately
before the display RCG's existing `regmap_read()` but never reached
`parent-read-complete`. This localizes the non-returning boundary to that
existing call without proving whether MMIO, interconnect, regmap locking, or
runtime-suspended provider state is responsible. The independent watchdog
restored the exact fallback; zero retained pstore/fatal records and complete
host cleanup passed. V14 must not be rerun and is not a GPU fix. Network-root
v15 now passes the complete offline gate for an experimental partial backport
of the March 2025 CCF runtime-PM RFC. Its exhaustive lock model, red/green
source and mutation tests, clock KUnit suite, two mainline builds, and two
nested wrapper/package paths pass; exported symbols, modules, and the RCG2
object remain byte-identical to v14. It acquires generic all-provider
runtime-PM references before `prepare_lock`, preserves the orphan scan, and
releases them after unlocking. Its one attended RAM-only probe made DISPCC
active, completed all seven observed parent reads, and advanced GPUCC clock
registration through completed index 6 and into index 7. The 75-second
watchdog reset while 100 ms markers were still arriving continuously: a
73.901-second trace span with no gap over 0.116 seconds. This supports the
ordering hypothesis but does not prove complete GPUCC registration. V15 must
not be rerun; the next gate is an offline-verified trace-free confirmation.
See the
[v14 offline report](test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-offline.md)
and
[v14 live report](test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-live.md),
then the
[v15 offline report](test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md)
and
[v15 live report](test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-live.md).
Network-root v16 now passes its complete offline gate without changing any
kernel/package bit: its explicit confirmation transport omits all three core
trace flags, its fail-closed probe requires each parameter at count zero and
mode-`0400` state `N`, and only the delay-free outer GPUCC trace remains. A
hash-pinned read-only target baseline proves those conditions, zero storage,
consumer isolation, and the still-armed initial watchdog before any disarm.
See the
[v16 offline report](test-results/2026-07-25-network-root-gpucc-confirmation-offline.md).
The attended v16 cycle never entered the Linux 7.1 target: a 284-second
operator gap after load exceeded the staging watchdog, both later execute
invocations failed before serial transmission, and exact fallback/cleanup
passed. V16 is consumed. V17 now passes an offline gate that runs the same
trace-free load and execute actions in one guarded process, while preserving
bounded identical-load replay and non-retryable execute. See the
[v16 staging-only report](test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
and
[v17 offline report](test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md).
The one permitted live v17 cycle now passes. The atomic transport transmitted
one execute, the trace-free GPUCC driver reached
`registration-complete ret=0`, bound exactly one device, and stayed stable for
30 seconds with every GPU/GMU/SMMU consumer, render node, and storage path
absent. Normal systemd reboot restored the exact fallback with zero retained
pstore/fatal evidence and complete host cleanup. This accepts only the
GPUCC/CCF foundation, not acceleration; the next gate is an offline-tested,
reproducible Adreno power/SMMU/GMU/firmware dependency tier. See the
[v17 live report](test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md).
V18 now passes the first, deliberately smaller offline slice: the exact v17
GPUCC bits plus the built-in Adreno SMMU, with GPU, GMU, A660 firmware,
DRM/render nodes, and storage still disabled. The dependency contract, DTB,
nested staging archive, two clean ASUS wrapper builds, two repacks, baseline,
guarded probe, mutation suite, and exact bundle verifier pass. The phone was
not contacted. The host now also has an independently verified copy-on-write
v18 export with the complete 1,008-file module tree and zero A660 firmware;
the accepted fallback export remains unchanged. An exact NFS allowlist,
five-file tmpfs launcher, 120-second transition watchdog overlapping the
existing 75-second probe watchdog, immediate-reboot path, negative tests, and
complete bundle re-verification pass offline. This is not acceleration; one
attended RAM-only SMMU probe remains pending. See the
[v18 offline report](test-results/2026-07-26-network-root-adreno-smmu-offline.md).
The complete pinned A660/GMU source graph and its first guarded kernel build
now pass offline. Registration is a real hardware boundary: it attaches three
IOMMU contexts and programs GMU RSCC/PDC registers, while firmware, GPU
power-up, ZAP/SCM authentication, and hardware initialization wait for the
first DRM open. The new Linux `7.1.4-rog5-a660reg1` candidate makes DRM/MSM and
GPUCC manually loaded modules, disables display KMS and UFS, exports
`separate_gpu_kms`, and propagates the previously unchecked GMU power-level
error. Two isolated rootless builds and all nine acceptance outputs are
byte-identical; no firmware is embedded and the phone was not contacted. The
exact four-node DT also passes mutation tests and duplicate byte-identical
builds. Its read-only baseline and no-open registration probe pass offline but
remain source-locked until the earlier v18 SMMU live gate succeeds; the
isolated seven-module NFS export, nested stage, two clean ASUS wrappers, two
header-v3/AVB repacks, and exact fourteen-file bundle now also reproduce and
pass their complete offline verifier. The package is intentionally not
authorized for live use; the v18 SMMU gate and both later GPU live gates remain
pending. See the
[A660 full dependency audit](test-results/2026-07-26-a660-full-dependency-audit.md)
and
[A660 registration build report](test-results/2026-07-26-a660-registration-build.md).

The panel exposes four fixed modes named 144/120/90/60. Its DRM capability blob says `qsync support=false`, `dfps support=false`, and `dyn bitclk support=false`; this is fixed refresh-rate switching, not VRR.

See the [project roadmap](ROADMAP.md), [current state](docs/current-state.md),
[hardware contract](docs/hardware-contract.md),
[builds and artifacts](docs/builds-and-artifacts.md),
[subsystem status](docs/port-status.md), [recovery DTS](docs/recovery-dts.md),
[read-only UFS discovery](docs/ufs-discovery.md),
[native network root](docs/network-root.md),
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

After ACM enumerates, use the fixed-action helper rather than attaching a
terminal. It opens ACM with no controlling terminal, strips cursor-position
queries, accepts no arbitrary command, and keeps rollback armed:

```sh
ALLOW_NETWORK_ROOT_ACM=1 \
  scripts/host/network-root-acm.py load-normal

# Only with the reviewed GPUCC generic-CCF diagnostic bundle:
ALLOW_NETWORK_ROOT_ACM=1 \
  scripts/host/network-root-acm.py load-gpucc-diagnostic

ALLOW_NETWORK_ROOT_ACM=1 \
ALLOW_ATTENDED_KEXEC=1 \
  scripts/host/network-root-acm.py execute
```

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

```sh
scripts/host/get-arch-rootfs.sh
```

After an offline bundle is accepted and the repository is clean, stage the
matching headless-first Plasma rootfs with an external public SSH key:

```sh
scripts/host/stage-arch-rootfs.sh /path/to/rog5_ed25519.pub
```

After the separate host-service confirmation, prepare the manifest-pinned
archive as a root-owned export source and run the attended foreground server:

```sh
pkexec dnf install nfs-utils
pkexec env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  "$PWD/scripts/host/prepare-network-root-export.sh"
pkexec env PATH=/usr/sbin:/usr/bin:/sbin:/bin \
  "$PWD/scripts/host/serve-network-root.sh"
```

The server uses no permanent export or firewall configuration. It binds
NFSv4.2 to `169.254.77.1`, exports a read-only bind mount only to
`169.254.77.2`, moves only the exact network-root gadget into the verified
unused built-in `drop` zone, and restores runtime state on exit. Do not run
these commands until the external-service gate is explicitly approved.
Its default attended window is 900 seconds. For a deliberately bounded
long-running diagnostic, set `ROG5_NFS_TIMEOUT=86400`; return the phone to
fallback with the validated attended procedure before that deadline because
this temporary root depends on the host export. The v3 retained-exitrd path
has one passing normal systemd reboot, but the bundle remains an attended
temporary-boot transport and must never be flashed.

The equivalent Windows workflow remains available:

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

The signed Arch input and the current locked minimal Plasma Desktop rootfs
pass their offline suites. The current archive contains the exact
`7.1.4-g7a5cef0db479` network-root modules, verified Qualcomm firmware,
key-only SSH, and no VPN/Wi-Fi/KRDP secret. Root preparation generates one
deployment-local server host key outside Git and pins `sshd` to it. Arch has
now passed two native boots with normal hardware coldplug through the
attended, read-only USB NFS gate; nothing was flashed.

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
