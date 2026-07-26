# ROG Phone 5 native Linux roadmap

This is the execution plan for turning the ASUS ROG Phone 5 (`anakin`,
Snapdragon 888 / SM8350) into a maintainable native-Linux phone-server.

The intended end state is:

- a modern, reproducibly built Linux kernel;
- a normal Arch Linux ARM desktop installation, with Debian kept as a fallback;
- KDE Plasma Desktop on Wayland, not an Android-hosted Linux container;
- working Adreno 660 acceleration through DRM/MSM and Mesa/Freedreno;
- reliable charging, thermal management, Wi-Fi, USB networking, audio, input,
  power-button handling, and screen-off server operation;
- remote shell and remote desktop access;
- a Wi-Fi hotspot whose client traffic is forced through a VPN and fails closed;
- documented recovery and rollback paths that do not depend on a working rootfs.

This is a bring-up project, not yet an installable Linux distribution. Every
phase below has a stop/go gate so that an unproved subsystem is not mistaken
for a working feature.

## Current position

- [x] Record the hardware and vendor-kernel baseline.
- [x] Create reproducible build, verification, and artifact-manifest tooling.
- [x] Build a normal Arch Plasma rootfs offline.
- [x] Implement Linux 7.1.4 USB gadget/rollback source and offline build tooling.
- [x] Prove the corrected recovery bundle twice from clean inputs.
- [x] Pass live RAM-only, storage-isolation, USB, and rollback gates.
- [x] Kexec from the temporary vendor kernel into Linux 7.1.4.
- [x] Discover the complete UFS topology read-only with zero blocked commands.
- [x] Reproduce the UFS-disabled Linux 7.1.4 USB network-root bundle offline.
- [x] Boot Arch over USB NCM with UFS absent and reach systemd/SSH twice in
  diagnostic mode.
- [x] Isolate the normal-coldplug reset to GPUCC and an overlapping RMTFS
  reservation; reproduce and boot the guarded v2 DTB.
- [x] Reproduce GPUCC with every consumer disabled and narrow its first
  non-returning operation to CCF registration of clock index 0, with
  independent watchdog rollback and complete cleanup.
- [x] Build and offline-accept the exact-device v11 generic CCF trace with 72
  new registration boundaries, bounded idempotent ACM load recovery, and two
  byte-identical kernel/wrapper/package paths.
- [x] Run the attended v11 probe once and localize the stall to
  `clk_core_reparent_orphans_nolock()` after orphan insertion and all earlier
  index-0 CCF phases, with independent rollback and complete cleanup.
- [x] Build and offline-accept a source-tested v12 per-orphan trace that
  brackets parent lookup and each reparent callback without changing normal
  CCF behavior; reproduce both kernel/wrapper/package paths byte-for-byte.
- [x] Run one attended RAM-only v12 probe with the independent 75-second
  watchdog; localize the stall to `__clk_init_parent()` for the second,
  DISPCC-owned orphan, then verify exact fallback and complete host cleanup.
- [x] Build, source-test, and reproduce a default-off v13 trace that separately
  brackets the display orphan's `get_parent()` callback and cached-parent
  lookup; pass two kernel, wrapper, and package paths byte-for-byte.
- [x] Run one attended RAM-only v13 probe with the independent 75-second
  watchdog; prove the runtime-suspended DISPCC orphan enters its
  `get_parent()` callback without returning, then verify exact fallback and
  complete host cleanup.
- [x] Design, source-test, reproduce, and offline-accept a default-off v14
  trace around the exact display RCG's existing regmap read, with no
  runtime-PM or hardware behavior change; pass two mainline, wrapper, and
  package paths byte-for-byte.
- [x] Run one attended RAM-only v14 probe with the independent 75-second
  watchdog; localize the boundary to the display RCG's existing regmap read,
  then verify exact fallback and complete host cleanup.
- [x] Model CCF prepare-lock, orphan-list, DISPCC runtime-PM, and regmap lock
  ordering; write failing source, mutation, and concurrency tests before
  implementing a behavioral candidate.
- [x] Reproduce the v15 behavioral candidate through two clean kernel, wrapper,
  and package paths before considering one new attended zero-storage probe.
- [x] Run at most one attended RAM-only v15 probe with independent rollback;
  accept only the first non-returning boundary, exact fallback, and complete
  host cleanup.
- [x] Offline-accept a v16 confirmation using the exact v15 behavior with all
  high-volume core traces absent and only the bounded outer GPUCC trace.
- [x] Consume one attended v16 cycle safely at the staging boundary: no
  `kexec -e` reached the target, the staging watchdog restored exact fallback,
  and complete host cleanup passed.
- [x] Offline-accept a v17 atomic load-to-execute transport using the exact
  v15 artifacts and v16 target gates, with guard-first ordering, bounded
  identical-load replay, and non-retryable execute.
- [x] Run at most one attended RAM-only v17 confirmation; require complete
  GPUCC bind/stability, disabled consumers, zero storage, exact rollback, and
  complete host cleanup.
- [ ] Source-test and reproduce the next isolated Adreno dependency tier
  before enabling the SMMU, GPU power path, GMU, firmware, or DRM consumers.
- [x] Pass two normal-coldplug Arch boots with persistent SSH authorization
  and server identity.
- [x] Fix the normal mainline orderly reboot path with a retained exitrd.
- [x] Reject the near-epoch PMK8350 RTC without writing it, then isolate and
  register the PMK8350 power-key path with RTC still disabled.
- [ ] Design the persistent storage layout from measured hardware results.
- [ ] Bring up the phone hardware and accelerated desktop.
- [ ] Produce a recoverable persistent release.

The historical v2 recovery image and the GPU image derived from it are unsafe
and must not be booted. Later v4-v6 recovery candidates are rejected test
artifacts, not releases. See [current state](docs/current-state.md) and
[test results](test-results/).

## Non-negotiable safety rules

1. Never flash during recovery development. Use reversible `fastboot boot`.
2. Never enable storage in a recovery DTB before the RAM-only and USB rollback
   gates pass.
3. Treat an unmounted block device as sensitive. Discovery starts read-only.
4. A temporary boot must have an independent, wall-clock-tested fallback path.
5. Build from clean, pinned inputs and reproduce release artifacts twice.
6. Never commit private keys, account tokens, CVs, email data, VPN profiles,
   partition dumps, proprietary firmware, or other personal data.
7. Require explicit confirmation before credential use, account integration,
   persistent device writes, partition changes, or flashing.

## Phase 0 — reproducible recovery bundle

Goal: produce a small recovery environment that can be trusted before touching
storage or desktop userspace.

- [x] Pin the Linux source revision and offline builder image.
- [x] Add the required USB ACM/NCM kernel configuration and verify that PM
  autosleep is disabled in the staging wrapper.
- [x] Keep a supervised ACM shell open so host writes cannot be left unqueued.
- [x] Make rollback retry a forced reboot and emergency SysRq reboot.
- [x] Prevent suspend from consuming the rollback window without a
  capability-dependent wake-lock gate.
- [x] Reject any block-backed mount and force every physical block device and
  partition read-only before exposing USB recovery.
- [x] Rescan configfs-created device nodes, require `/dev/ttyGS0`, and repeat
  storage isolation before starting ACM or binding USB.
- [x] Reject non-empty kernel output directories.
- [x] Verify the final kernel configuration and recovery-init markers.
- [x] Finish two clean Linux 7.1.4 builds and compare all outputs byte-for-byte.
- [x] Rebuild and compare the ASUS recovery DTB from both clean builds.
- [x] Build credential-free ACM-only target and staging initramfs twice and
  compare them.
- [x] Build the ASUS 5.4 kexec wrapper twice from clean source/output pairs.
- [x] Repack and verify a new unsigned AVB temporary-boot image.
- [x] Record every input/output hash in the artifact manifest and test report.

Exit gate: **reproducible offline tooling passes through v18**. Recovery v12
remained unbooted; v13 and v14 both returned to fallback before their exact
recovery USB identity appeared. V15 identified the unnecessary wake-lock gate;
v16 reached USB/NCM/rollback but not ACM; v17 identified the missing device
node; v18 is the current credential-free candidate.

## Phase 1 — live RAM-only recovery

Goal: prove that the recovery mechanism is usable and cannot silently touch UFS.

- [x] Boot the candidate with `fastboot boot`; do not flash it.
- [x] Verify ACM and NCM enumerate on the host.
- [x] Verify the rollback watchdog and supervised ACM process.
- [x] Complete the first rollback test through credential-free ACM.
- [x] Authenticate only after separate approval to build an SSH-enabled
  candidate with the recovery public key.
- [x] Prove the live root and writable paths are tmpfs/ramfs.
- [x] Prove no physical storage block device is mounted and every enumerated
  block device reports read-only.
- [x] Run the storage-isolation and USB gadget smoke suites.
- [x] Let the short rollback timer expire and prove return to the fallback OS.
- [x] Repeat the boot and rollback test to exclude a one-off success.

Recovery v13 and v14 completed non-flashing fastboot transfers but each
returned to fallback 21 seconds after fastboot disconnected, without
enumerating the exact recovery USB product. Neither satisfies a Phase 1 gate.
V15's 31-second live interval identified the wake-lock gate as the shared
early-return path. V16 removed that gate and reached exact USB, NCM, and
rollback, but ACM lacked `/dev/ttyGS0`. V17 proved the RAM/storage boundary and
confirmed a live `mdev -s` rescan fixes ACM. V18 implements the fail-closed
rescan and second storage check. Kexec was prohibited until two complete
RAM-only staging and rollback cycles passed. Both cycles passed, followed by a
passing attended Linux 7.1 target and rollback.

Exit gate: RAM-only, USB, authentication, storage-isolation, and automatic
rollback tests all pass twice.

## Phase 2 — Linux 7.1 recovery

Goal: kexec from the temporary ASUS wrapper into a current mainline-derived
kernel without relying on phone storage.

- [x] Load the verified Linux `Image`, recovery DTB, and target initramfs.
- [ ] Capture a complete final vendor-kernel log before a future kexec; the
  redacted pre-kexec state and loader result are recorded.
- [x] Execute kexec and verify the new kernel release and boot identity.
- [x] Re-run ACM/NCM, RAM-only, storage-isolation, and rollback gates; the
  accepted credential-free target intentionally keeps SSH disabled.
- [x] Record redacted target logs and all observed regressions.

Exit gate: **passed**. Linux 7.1 runs the recovery userspace and retains the
safe rollback path.

## Phase 3 — read-only UFS discovery

Goal: learn the phone storage topology without mounting or modifying it.

- [x] Enable only the UFS controller and required PHY/IOMMU dependencies.
- [x] Retain the proven USB2 recovery channel and RAM-only root.
- [x] Confirm block enumeration and collect redacted topology/size data.
- [x] Confirm zero block-backed mounts and zero write tests.
- [x] Check UFS, IOMMU, watchdog, and USB logs for faults.
- [x] Prove rollback and fallback boot again.
- [ ] Document candidate persistent layouts and Android coexistence choices.
- [ ] Request confirmation before provisioning or changing any partition.

Exit gate: **passed by v2**. Exact Linux `7.1.4-gcfd385a1c754`
enumerated all 116 physical nodes read-only with zero blocked commands, kept
the UFS host active without a power transition, and automatically returned to
the exact fallback kernel.

## Phase 4 — headless Arch Linux first boot

Goal: boot a normal modern distro before adding desktop complexity.

- [x] Restage the Arch rootfs with the exact accepted kernel modules.
- [x] Verify package signatures, firmware hashes, ownership, symlinks, modes,
  ACLs, xattrs, and a clean archive round trip.
- [x] Add a fail-closed initramfs path that creates USB NCM, mounts a
  host-exported root read-only, adds a tmpfs overlay, and then `switch_root`s.
- [x] Build the dedicated NFSv4.2/OverlayFS kernel twice with SCSI/UFS and its
  QMP PHY paths compiled out; reproduce both initramfs layers, wrapper, and
  Android temporary-boot package.
- [x] Implement and offline-test a runtime-only, exact-peer host NFS/firewall
  harness with automatic cleanup.
- [x] Run the privileged host export gate on the dedicated USB address and
  keep it enabled only during attended tests.
- [x] Boot twice with UFS disabled before combining normal userspace with any
  on-device storage driver.
- [x] Reach running systemd, `multi-user.target`, and key-only SSH for root and
  the unprivileged account.
- [x] Prove OverlayFS, read-only NFS lower, stable USB traffic, no physical
  block devices, no block-backed mounts, and zero failed units.
- [x] Return to fallback through the validated attended reset after two normal
  v2 boots.
- [x] Isolate and fix the normal udev coldplug reset in the recovery tier.
- [x] Fix normal orderly reboot with a retained shutdown initramfs; one
  attended v3 `systemctl reboot` returned to fallback with complete host
  cleanup.
- [x] Verify runtime timekeeping, entropy, and two additional clean
  mainline-to-fallback reboot cycles while adding only isolated PMIC nodes.
- [x] Implement and offline-test a strict-SSH, host-authoritative volatile
  time bootstrap that leaves RTC disabled and the rollback watchdog armed.
- [x] Pass the live host-time bootstrap with RTC/storage absent and rollback
  armed; correct the measured 2,378,466-second drift and reboot cleanly.
- [ ] Hand off to authenticated network time after Wi-Fi acceptance; the raw
  PMK8350 RTC remains rejected as a server-time source.
- [ ] Provision storage only after explicit confirmation and a recovery check.
- [ ] Measure baseline RAM, idle CPU, temperature, and power.
- [ ] Add zram only if measurements justify it.

Exit gate: repeatable headless Arch boot, remote administration, and clean power
cycles. Debian is evaluated only if an Arch-specific blocker appears.

## Phase 5 — Wi-Fi, VPN, and hotspot

Goal: make the phone useful as a network appliance without leaking client
traffic outside the VPN.

- [ ] Bring up Wi-Fi firmware, calibration, regulatory data, and client mode.
- [ ] Verify the radio advertises and sustains AP mode.
- [ ] Establish a real WireGuard or supported VPN handshake.
- [ ] Add DHCP, DNS, forwarding, and nftables rules.
- [ ] Force hotspot-client traffic through the VPN interface.
- [ ] Drop forwarded client traffic when the VPN is down.
- [ ] Test packets, DNS, IPv4/IPv6 policy, reconnects, and VPN loss.
- [ ] Test sustained throughput, thermals, charging, and battery depletion.

Exit gate: a hardware-tested hotspot with a real VPN handshake and demonstrated
fail-closed behavior.

## Phase 6 — display, input, power, and charging

Goal: make the phone locally usable while remaining an efficient screen-off
server.

- [ ] Port panel, DSI, Pixelworks bridge, backlight, touch, and buttons.
- [x] Isolate the PMK8350 power-key DT node and register one `KEY_POWER`
  device through the guarded `qcom_pon` parent-module probe.
- [x] Repeat v5 in normal unmasked mode, live-test the fail-resumable watchdog
  disarm, and return through a clean systemd reboot.
- [ ] Observe a real short press through the switch/IRQ/input path; driver
  registration alone is not acceptance.
- [ ] Validate 60 Hz first, then 90/120/144 Hz one mode at a time.
- [ ] Use 60 Hz and panel-off as server defaults; expose higher rates on demand.
- [ ] Make a short power-button press toggle panel/DPMS state without suspending
  or stopping network/server workloads.
- [ ] Define a clear on-device working indicator that does not keep the display
  lit continuously.
- [ ] Validate USB charging, current limits, battery reporting, thermal zones,
  throttling, and safe shutdown.
- [ ] Measure panel-off idle draw and each refresh-rate profile.

Exit gate: reliable local input/display, real screen-off operation, charging,
thermal safety, and measured power profiles.

## Phase 7 — Adreno 660 GPU acceleration

Goal: run Plasma through DRM/MSM and Mesa/Freedreno instead of software rendering.

- [x] Complete trace-free GPUCC registration, one-device bind, 30-second
  stability, normal reboot, and cleanup with every consumer disabled.
- [x] Source-test the exact consumer-disabled Adreno SMMU node and driver
  boundary: seven clocks, one CX domain, twelve IRQs, runtime PM, and no
  firmware path.
- [x] Rebuild and reproduce the smallest GPUCC plus Adreno SMMU DTB, nested
  stage, ASUS wrapper, and temporary-boot package from the storage-safe base.
- [ ] Run the one-shot attended RAM-only SMMU bind/runtime-suspend gate.
- [x] Source-test the remaining GPU/GX, regulator, interconnect, GMU,
  reserved-memory, firmware, and complete consumer dependency graph; separate
  probe-time IOMMU/RSCC/PDC setup from first-open firmware and power-up.
- [x] Define fail-first kernel contracts for a storage-disabled candidate with
  DRM/MSM and GPUCC loaded manually, headless GPU KMS, no automatic DRM opens,
  and checked GMU power-level probe errors.
- [x] Build and independently reproduce Linux `7.1.4-rog5-a660reg1`; require
  exact config, Image, compressed Image, module archive, symbols, MSM, GPUCC,
  MDT-loader, and metadata outputs, with zero UFS and zero embedded firmware.
- [x] Build and reproduce the exact v18-derived four-node DT; mutation-test
  every changed status and the pinned ZAP name while retaining storage,
  display, remote-processor, RTC, and USB containment.
- [x] Define and artifact-test the read-only registration baseline and
  independent-watchdog probe; pin the seven-module load order, forbid DRM
  opens/firmware requests, and source-lock it behind the v18 SMMU live result.
- [x] Build and reproduce the module/initramfs stage carrying the accepted
  baseline and probe, then its ASUS wrapper and temporary-boot package before
  any registration attempt; verify the isolated seven-module NFS export,
  duplicate nested stages/wrappers/repacks, and exact fourteen-file manifest.
- [ ] Run one registration-only gate, reboot, and review all IOMMU, power,
  interrupt, thermal, and fault evidence before permitting a DRM open.
- [ ] Run a separate first-open gate for SQE/GMU firmware, GMU resume,
  ZAP/SCM authentication, and GPU hardware initialization.
- [ ] Bring up GPU power domains, clocks, regulators, IOMMU, GMU, and firmware.
- [ ] Verify `/dev/dri/card*` and `/dev/dri/renderD*`.
- [ ] Repeatedly open the render node and submit simple workloads.
- [ ] Run EGL/OpenGL ES and Vulkan smoke tests.
- [ ] Verify Mesa reports Freedreno/Turnip, not llvmpipe.
- [ ] Run suspend/idle, thermal, fault-recovery, and repeated-boot tests.
- [ ] Keep vendor KGSL experiments separate from the mainline acceptance path.

Exit gate: stable accelerated rendering across repeated boots and idle/power
transitions, with no IOMMU, GMU, or page faults.

## Phase 8 — normal KDE Plasma and remote GUI

Goal: provide a familiar desktop locally and remotely without wasting resources
when no desktop is needed.

- [ ] Boot the existing Plasma Desktop image on the accepted kernel/modules.
- [ ] Validate KWin Wayland, XWayland, KScreen, audio, clipboard, and input.
- [ ] Keep graphical startup optional; default to headless server mode until
  desktop stability and memory use are measured.
- [ ] Enable KRDP or another maintained remote-desktop service only after
  credentials and exposure policy are explicitly configured.
- [ ] Test remote use with the physical panel off.
- [ ] Measure Plasma, Baloo, browser, and remote-desktop memory/idle cost.
- [ ] Disable or remove services only when measurements show a useful saving.
- [ ] Evaluate GNOME only if Plasma fails a concrete requirement.

Exit gate: stable local and remote Plasma sessions with GPU acceleration and
screen-off server operation.

## Phase 9 — AI and browser automation service

Goal: let the phone host automation tools without making personal credentials a
kernel/rootfs build input.

- [ ] Run model/API clients as an unprivileged, isolated service account.
- [ ] Keep email, CV, browser sessions, API tokens, and provider credentials in
  an encrypted runtime secret store, never in Git or build artifacts.
- [ ] Require confirmation before connecting email or other external accounts.
- [ ] Separate read-only research from actions such as sending mail or applying
  to jobs; require explicit approval for consequential actions.
- [ ] Add resource, thermal, network, and rate limits.
- [ ] Back up only configuration and encrypted user data, not secrets in logs.

Exit gate: auditable, least-privilege automation with explicit credential and
action boundaries.

## Phase 10 — persistent release and recovery

Goal: turn the tested development system into something recoverable and
maintainable.

- [ ] Freeze accepted kernel, DTB, initramfs, modules, firmware, and rootfs hashes.
- [ ] Define a persistent boot layout with a known-good fallback.
- [ ] Add an atomic update or A/B rollback strategy where the storage layout
  allows it.
- [ ] Document backup, restore, recovery entry, and unbrick procedures.
- [ ] Run cold-boot, reboot-loop, power-loss, low-battery, charging, thermal,
  networking, and multi-day server tests.
- [ ] Request explicit confirmation before the first persistent flash/install.
- [ ] Tag and publish source, manifests, build instructions, and checksums.

Exit gate: an independently reproducible release that survives failure and has
a documented recovery path.

## Development-host recommendation

A native Linux workstation is the preferred long-term host for this project.
Kernel builds, device-tree tooling, initramfs ownership/modes/symlinks, serial
devices, USB permissions, and containerized offline builds all match their
target environment more directly. Raw compile time will still be governed
mostly by CPU, RAM, cooling, storage, and parallel-job count.

The project now runs from a native Nobara Linux Btrfs workspace with rootless
Podman. Keep the previous Windows environment available until Linux can detect
fastboot/ADB and `/dev/ttyACM*` and all restored backups are verified.

Suggested host migration:

- [ ] Back up the repository, ignored artifact store, hashes, and recovery
  material without placing private keys in Git.
- [x] Install a native Linux workstation on a separate partition.
- [x] Install Android platform tools and add the development user to `dialout`;
  the current desktop login still needs a group refresh.
- [x] Clone this repository and restore ignored artifacts, then verify every
  restored file against `manifests/artifacts.tsv`.
- [ ] Run the repository policy suite and two clean kernel builds.
- [ ] Compare Linux-produced hashes and build times with the Windows baseline.
- [ ] Verify `fastboot`, `adb`, USB NCM, and `/dev/ttyACM*`; capture `usbmon`
  traces if ACM still fails.
- [ ] Keep Windows bootable until all of those checks pass.

Primary references: [AOSP workstation requirements][aosp-host],
[Docker Engine on Ubuntu][docker-ubuntu], [Android USB setup][android-usb],
[Kbuild with LLVM][kbuild-llvm], [Linux gadget serial][gadget-serial], and
[usbmon][usbmon].

[aosp-host]: https://source.android.com/docs/setup/start/requirements
[docker-ubuntu]: https://docs.docker.com/engine/install/ubuntu/
[android-usb]: https://developer.android.com/studio/run/device
[kbuild-llvm]: https://docs.kernel.org/kbuild/llvm.html
[gadget-serial]: https://docs.kernel.org/usb/gadget_serial.html
[usbmon]: https://docs.kernel.org/usb/usbmon.html

## Artifact and release policy

Git tracks source, configuration, scripts, documentation, tests, manifests, and
small redistributable inputs. Large rootfs/kernel/boot artifacts stay in the
ignored artifact store or a separately approved release store; Git records
their hashes and provenance. Private keys and personal or third-party
credentials never enter either location.

Every release candidate must identify:

- source revisions and patch hashes;
- builder image digest and toolchain versions;
- configuration, kernel, DTB, initramfs, module, rootfs, and boot-image hashes;
- clean-build A/B comparison results;
- live gate results and known failures;
- exact recovery and rollback procedure.
