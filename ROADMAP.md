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
- [ ] Prove the corrected recovery bundle twice from clean inputs.
- [ ] Pass live RAM-only, storage-isolation, USB, SSH, and rollback gates.
- [ ] Kexec from the temporary vendor kernel into Linux 7.1.4.
- [ ] Discover UFS read-only, then design the persistent storage layout.
- [ ] Boot Arch headlessly.
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
- [x] Add the required USB ACM/NCM and PM wake-lock kernel configuration.
- [x] Keep a supervised ACM shell open so host writes cannot be left unqueued.
- [x] Make rollback retry a forced reboot and emergency SysRq reboot.
- [x] Prevent suspend from consuming the rollback window.
- [x] Reject non-empty kernel output directories.
- [x] Verify the final kernel configuration and recovery-init markers.
- [x] Finish two clean Linux 7.1.4 builds and compare all outputs byte-for-byte.
- [ ] Rebuild and compare the ASUS recovery DTB from both clean builds.
- [ ] With approval to use the recovery public key, build the target and staging
  initramfs twice and compare them.
- [ ] Build the ASUS 5.4 kexec wrapper twice from clean source/output pairs.
- [ ] Repack and verify a new unsigned AVB temporary-boot image.
- [ ] Record every input/output hash in the artifact manifest and test report.

Exit gate: two identical offline builds and a complete verifier pass.

## Phase 1 — live RAM-only recovery

Goal: prove that the recovery mechanism is usable and cannot silently touch UFS.

- [ ] Boot the candidate with `fastboot boot`; do not flash it.
- [ ] Verify ACM and NCM enumerate on the host.
- [ ] Verify the rollback wake lock and supervised ACM process.
- [ ] Authenticate only after separate approval to use the recovery key.
- [ ] Prove the live root and writable paths are tmpfs/ramfs.
- [ ] Prove no physical storage block device is mounted or writable.
- [ ] Run the storage-isolation and USB gadget smoke suites.
- [ ] Let the short rollback timer expire and prove return to the fallback OS.
- [ ] Repeat the boot and rollback test to exclude a one-off success.

Exit gate: RAM-only, USB, authentication, storage-isolation, and automatic
rollback tests all pass twice.

## Phase 2 — Linux 7.1 recovery

Goal: kexec from the temporary ASUS wrapper into a current mainline-derived
kernel without relying on phone storage.

- [ ] Load the verified Linux `Image`, recovery DTB, and target initramfs.
- [ ] Capture the final vendor-kernel log before kexec.
- [ ] Execute kexec and verify the new kernel release and boot identity.
- [ ] Re-run ACM/NCM, SSH, RAM-only, storage-isolation, and rollback gates.
- [ ] Record boot logs and all observed regressions.

Exit gate: Linux 7.1 runs the recovery userspace and retains the safe rollback
path.

## Phase 3 — read-only UFS discovery

Goal: learn the phone storage topology without mounting or modifying it.

- [ ] Enable only the UFS controller and required PHY/IOMMU dependencies.
- [ ] Retain the proven USB2 recovery channel and RAM-only root.
- [ ] Confirm block enumeration and collect redacted topology/size data.
- [ ] Confirm zero block-backed mounts and zero write tests.
- [ ] Check UFS, IOMMU, watchdog, and USB logs for faults.
- [ ] Prove rollback and fallback boot again.
- [ ] Document candidate persistent layouts and Android coexistence choices.
- [ ] Request confirmation before provisioning or changing any partition.

Exit gate: stable read-only UFS enumeration with working recovery and rollback.

## Phase 4 — headless Arch Linux first boot

Goal: boot a normal modern distro before adding desktop complexity.

- [ ] Restage the Arch rootfs with the exact accepted kernel modules.
- [ ] Verify package signatures, firmware hashes, ownership, symlinks, and modes.
- [ ] Define the rootfs deployment and `switch_root` path.
- [ ] Provision storage only after explicit confirmation and a recovery check.
- [ ] Boot to `multi-user.target`.
- [ ] Verify console, SSH, time, entropy, logs, clean reboot, and clean shutdown.
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

- [ ] Rebuild the GPU DTB from the corrected, storage-safe base.
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

The low-risk migration is dual boot or a separate SSD first. Keep Windows until
Linux can build the repository, detect fastboot/ADB and `/dev/ttyACM*`, and
access all backups. Do not erase the existing PC installation as part of the
kernel bring-up.

Suggested host migration:

- [ ] Back up the repository, ignored artifact store, hashes, and recovery
  material without placing private keys in Git.
- [ ] Install a supported Ubuntu LTS release on a separate SSD or dual-boot
  partition.
- [ ] Install Git, Android platform tools, Docker Engine, and the Android udev
  rules; keep the kernel compiler inside the pinned builder container.
- [ ] Clone this repository and restore ignored artifacts, then verify every
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
