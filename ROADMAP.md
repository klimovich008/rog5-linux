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
- [x] Source-test and reproduce the isolated GPUCC plus Adreno SMMU tier with
  GPU/GMU consumers, A660 firmware, storage, and display still disabled.
- [x] Consume the one-shot attended v18 Adreno SMMU gate safely at its
  read-only baseline; a detector false-positive stopped before watchdog
  disarm, module load, or SMMU bind, and exact fallback/cleanup passed.
- [x] Consume the corrected one-shot v19 gate safely: baseline and GPUCC
  registration passed, the SMMU remained unbound, and watchdog rollback plus
  exact fallback/cleanup passed with zero-storage baseline and no new warning,
  fault, or storage log.
- [x] Source-test and offline-accept a v20 exact-device deferred/supplier
  diagnostic and one narrow platform `drivers_probe` request before any new
  attended cycle.
- [x] Consume the one-shot v20 gate safely at its read-only baseline; the
  kernel exposed the fresh unset `driver_override` as `(null)`, no handoff,
  module load, reprobe, or SMMU bind occurred, and exact fallback/cleanup
  passed.
- [x] Source-test and offline-accept a v21 null-representation correction
  with no `driver_override` write, a new preserved export, and the same
  exact-device/watchdog boundary before deciding on another live cycle.
- [x] Consume the one-shot v21 gate successfully: one exact-device reprobe
  bound `arm-smmu`, reached runtime suspend with zero firmware/render/storage
  activity, and returned through exact fallback and complete host cleanup.
- [x] Consume one A660 registration v3 cycle successfully: seven reviewed
  modules attached GPU/GMU to two IOMMU groups and exposed one unopened
  headless render node with zero firmware/storage/faults before exact fallback.
- [x] Source-prove a first-open seam after exact SQE/GMU requests and before
  ucode, runtime power, hardware initialization, HFI, and ZAP/SCM.
- [x] Build, reproduce, and live-accept the default-off one-shot
  firmware-request failed-open diagnostic; consume v4 after exact fallback
  and complete cleanup.
- [x] Build, reproduce, and live-accept rollback-safe A660 ucode allocation;
  consume v5/v6 after their fail-closed oracle diagnoses and consume passing
  v7 after exact rollback plus equal settled GEM state.
- [x] Source-test and reproduce the default-off v8 GMU resume-entry stop
  before every GMU inner power/clock/MMIO/IRQ/firmware/HFI operation. Keep its
  offline-accepted kernel **HOLD** until a fresh protected root and control
  plane pass separate review.
- [x] Pass two normal-coldplug Arch boots with persistent SSH authorization
  and server identity.
- [x] Fix the normal mainline orderly reboot path with a retained exitrd.
- [x] Reject the near-epoch PMK8350 RTC without writing it, then isolate and
  register the PMK8350 power-key path with RTC still disabled.
- [x] Validate the persistent Alpine fallback's software-rendered KDE/noVNC,
  ttyd, and Chromium endpoints with the physical panel off; enable and
  failure-test a loopback-only reconnecting Linux host tunnel plus a
  singleton phone-side desktop supervisor.
- [x] Build and protect a successor-v2 Arch root with kill-switch-first
  forwarding, partial-failure rollback, exact v1 preservation, real
  WireGuard packet evidence, and four rejected protected-root mutations.
- [x] Build, manifest-pin, and protect a successor-v3 Arch development root
  with a confined, press-only power-button screen-toggle service while
  preserving the complete v2 verifier byte-for-byte. Its separate
  verifier-first NFS, power-input target, and strict no-retry runner controls
  pass offline and remain live HOLD.
- [x] Capture the exact vendor WLAN/PCIe contract, then build and
  schema-validate an isolated WCN6855/PCIe0 board candidate plus two
  byte-identical Linux 7.1.4 kernel/module outputs. Its deterministic runtime
  package, protected root, current fallback preflight, verifier-first server,
  and no-retry runner now also pass while remaining unbooted and radio HOLD.
- [x] Design the
  [non-repartitioning persistent layout](docs/persistent-storage.md) from the
  exact live UFS map. Preserve active Alpine slot B, use versioned Arch roots
  below `userdata:/rog5`, enter Linux 7.x through one-shot kexec, and require
  read-only UFS plus bounded-write gates before persistent promotion. The
  [live preflight](test-results/2026-07-27-persistent-layout-preflight-live.md)
  passes without opening or writing a block device.
- [x] Build and fail-first test the P1 persistent Arch stager. Pin the exact
  successor-v3 archive and signed Alpine libarchive input; reject unsafe
  members and credentials; preserve ACLs/xattrs/capabilities; seal the entire
  extracted tree; and publish `arch-a` atomically while leaving it unbooted.
  The [offline result](test-results/2026-07-27-persistent-arch-staging-offline.md)
  leaves `/rog5` absent on the phone pending a separate write instruction.
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
  redacted pre-kexec state and loader result are recorded. The
  [private capture HOLD](test-results/2026-07-27-alpine-vendor-kernel-boot-log-hold.md)
  adds atomic mode-`0600` storage and rejects incomplete rings. The current
  ring lacks boot origin, so a separately authorized normal Alpine reboot
  and immediate read-only capture remain required.
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
- [x] Document the measured
  [non-repartitioning persistent layout](docs/persistent-storage.md): retain
  Alpine in active slot B and at the `userdata` filesystem root, stage Arch
  generations only below `/rog5`, and use guarded kexec before considering
  any direct-slot change.
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

- [x] Send real packets through isolated client/VPN/uplink namespaces; allow
  only the simulated VPN path, reject one-way IPv4/IPv6 ordinary-uplink
  leakage and unsolicited client ingress, fail closed after VPN-interface
  loss, and restore nftables/sysctls on cleanup.
- [x] Establish a real kernel WireGuard handshake over a network-disabled
  TEST-NET veth underlay, route a hotspot-client packet through the unchanged
  production kill-switch, require nonzero encrypted transfer, erase
  disposable keys, repeat cleanly, and reject a connected container. See the
  [offline WireGuard report](test-results/2026-07-27-vpn-hotspot-wireguard-offline.md).
- [x] Fail-first diagnose and remove the hotspot/dnsmasq/network-online
  systemd ordering cycle, add the hotspot unit to the complete staged-root
  verifier, and retain both packet suites. See the
  [Arch userspace audit](test-results/2026-07-27-arch-userspace-readiness-offline.md).
- [x] Harden the successor-v2 transition boundary so the nftables kill switch
  loads before forwarding, partial failures roll back, existing state is
  refused, forwarding restores before firewall removal, and the AP lowers
  first. Pass isolated IPv4/IPv6, VPN-loss, unsolicited-ingress, and real
  WireGuard tests; then clean-round-trip and separately protect the exact
  [v2 archive](test-results/2026-07-27-arch-successor-v2-rootfs-offline.md).
- [x] Default both isolated packet suites to successor v2, carry valid UDP/TCP
  DNS traffic through real WireGuard, detect one-way DNS leakage, fail closed
  across endpoint/interface loss, and verify recovery plus exact cleanup. See
  the [v2 DNS/recovery report](test-results/2026-07-27-vpn-hotspot-v2-dns-recovery-offline.md).
- [x] Capture the read-only vendor PCI `17cb:1103`/`17cb:0108`, regulator,
  GPIO, firmware, and board-data contract without activating the radio.
- [x] Add the opt-in WCN6855 PMU, PCIe0/QMP PHY, regulator, GPIO, MHI, and
  ath11k candidate. Pass immutable-base mutations, pinned dtschema `2026.6`,
  exact module/alias checks, and two byte-identical clean kernel builds. See
  the [offline WCN6855/PCIe report](test-results/2026-07-27-wcn6855-pcie-offline.md).
- [x] Package the exact candidate into a storage-disabled RAM-only,
  client-only diagnostic with bounded logs, automatic fallback, a protected
  root, watchdog, target oracle, and strict one-shot/no-retry runner. See the
  [runtime package](test-results/2026-07-27-wcn6855-runtime-package-offline.md)
  and [protected-root HOLD](test-results/2026-07-27-wcn6855-v1-prelive-hold.md).
- [x] Pass a post-restart
  [current-state HOLD review](test-results/2026-07-27-wcn6855-v1-current-readiness-hold.md)
  with synchronized Git, complete recursive root verification, exact
  fallback health, and byte-identical unarmed host state.
- [ ] Receive fresh explicit authority for one attended RAM-only enumeration
  probe; do not scan, associate, start AP mode, deploy VPN credentials, retry,
  or flash.
- [ ] Bring up Wi-Fi firmware, calibration, regulatory data, and client mode.
- [ ] Verify the radio advertises and sustains AP mode.
- [ ] Establish an on-phone handshake to the selected VPN provider.
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
- [x] Add a dependency-free `pmic_pwrkey` event handler and confined systemd
  service; reject release/repeat/other-key, truncated-event, failed-toggle,
  unsafe-device, credential, and archive violations offline. See the
  [successor-v3 result](test-results/2026-07-27-arch-successor-v3-power-button-offline.md).
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
- [x] Preserve the consumed v18 root and prepare an independently verified
  v19 copy-on-write export with 1,008 unchanged module files, zero A660
  firmware, preserved credentials, an unchanged accepted base, and an exact
  NFS allowlist that no longer serves v18.
- [x] Test and pin the corrected v19 host/target control plane: five exact tmpfs
  inputs, strict SSH identity, private evidence, baseline under the original
  watchdog, a 120-second transition watchdog overlapping the existing
  75-second probe, one invocation, and immediate fallback reboot.
- [x] Consume v18 safely at the baseline after a false match on the normal
  word `Default`; prove no watchdog disarm, GPUCC load, SMMU bind, firmware,
  render node, storage access, or cleanup failure, and do not retry v18.
- [x] Consume the corrected one-shot attended v19 gate: accept its baseline
  and GPUCC result but reject the no-bind SMMU result, preserve private
  evidence, and prove watchdog fallback plus complete cleanup.
- [x] Capture exact deferred/supplier state and test a v20 exact-device
  platform reprobe control plane; forbid a global timeout extension, broad bus
  rescan, force-bind, unload, retry, firmware, render, and storage path.
- [x] Prepare and independently verify the isolated v20 copy-on-write root
  with all 1,008 modules, zero A660 firmware, preserved credentials, unchanged
  base, exact source/control-plane seal, and an allowlist that rejects v18 and
  v19.
- [x] Consume the single v20 gate at its read-only baseline: reject the
  verifier's empty-line assumption after observing the source-consistent
  `(null)` unset representation; prove the original watchdog stayed armed,
  GPUCC stayed absent, `drivers_probe` was never written, and complete
  fallback/cleanup passed.
- [x] Source-test a v21 correction that pins platform allocation,
  `driver_override` display/match semantics, and kernel NULL-string
  formatting; accept only exact `(null)`, reject every other nonempty value,
  and forbid any write to `driver_override`.
- [x] Prepare and independently verify a new v21 copy-on-write root and
  source/control-plane seal; preserve v20 and remove it from every runnable
  allowlist before deciding whether one v21 cycle is justified.
- [x] Run the sole attended RAM-only v21 SMMU bind/runtime-suspend gate;
  accept one exact bind at runtime suspend with zero firmware/render/storage
  activity, exact fallback, and complete host cleanup; consume v21 and remove
  it from the runnable NFS allowlist.
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
  opens/firmware requests, and source-lock it behind a passing SMMU live result.
- [x] Build and reproduce the module/initramfs stage carrying the accepted
  baseline and probe, then its ASUS wrapper and temporary-boot package before
  any registration attempt; verify the isolated seven-module NFS export,
  duplicate nested stages/wrappers/repacks, and exact fourteen-file manifest.
- [x] Pin the exact v21 live acceptance into the A660 registration-only source
  lock, create and independently verify the isolated v2 export, reject the old
  and consumed roots, and re-run the unchanged binary package's full exact
  verifier.
- [x] Carry the accepted exact-device SMMU reprobe into v3, verify the unset
  override and at-most-one `3da0000.iommu` write before DRM dependencies, and
  replace v2 with a new independently verified export.
- [x] Define and fail-first test an atomic one-shot registration host/target
  control plane with nested watchdogs, private evidence, immediate normal
  fallback, exact persistent-fallback verification, and complete host cleanup.
- [x] Run one registration-only gate, reboot, and review all IOMMU, power,
  interrupt, thermal, and fault evidence before permitting a DRM open.
- [x] Pin the exact registration report and evidence checkpoint in a
  mutation-tested nonsecret acceptance marker, and consume the v3 export.
- [x] Source-test the exact first-open boundary and implement a default-off,
  read-only-armed, atomic one-shot A660.1 diagnostic that requests only SQE
  and GMU, returns `EUCLEAN`, and cannot reach ucode, power, HFI, or ZAP/SCM.
- [x] Build that patch twice in isolated clean environments; require an
  unchanged Image/config/ABI, only one changed MSM module, byte-identical
  archives and metadata, zero embedded firmware, and hard-pinned hashes.
- [x] Prepare and independently verify a new root-owned v4 export with only
  exact SQE/GMU firmware mode `0644`, ZAP absent, the accepted registration-v3
  marker, one tiny open helper, watchdog rollback, and consumed-root lockout.
- [x] Run one attended request-only failed-open gate; require exact
  `EUCLEAN`, bounded success evidence, no surviving DRM descriptor, and zero
  ucode, power, HFI, ZAP/SCM, storage, display, warning, or fault evidence.
- [x] Pin the exact request-only report and evidence checkpoint in a
  mutation-tested nonsecret acceptance marker, and consume the v4 export.
- [x] Source-audit and fail-first test the exact A660.1 ucode-allocation
  boundary. It creates SQE, privileged shadow, and privileged power-up
  reglist objects through three SMMU mappings before GPU/GMU runtime power or
  register access, and requires explicit all-path rollback because the normal
  destroy path does not fully release that state.
- [x] Implement and mutation-test a default-off, exact-A660.1, atomic one-shot
  ucode-allocation diagnostic with balanced three-object rollback.
- [x] Reproduce two isolated builds and require unchanged Image/config/ABI,
  only the reviewed MSM module delta, byte-identical outputs, BTF, and zero
  embedded firmware.
- [x] Prepare a fresh independently verified RAM-only root and watchdog gate
  with PID-filtered exact map/unmap/close and GEM-free evidence, balanced CPU
  vmaps and firmware references, equal pre/post GEM snapshots, nine
  power/HFI/ZAP/SCM zero-event probes, nested fallback watchdogs, and an
  unchanged fully reverified boot package. Keep it absent from the NFS
  allowlist and do not create a live runner at this checkpoint. See the
  [ucode-allocation v5 offline report](test-results/2026-07-26-a660-ucode-allocation-v5-offline.md).
- [x] Fail-first test and accept an exact one-invocation host runner with
  strict SSH identity, private evidence, immutable root/package inputs, and
  no NFS, boot, retry, ADB, fastboot, or flash control. Record a separate
  pre-live **HOLD** while the root remains non-runnable and the phone remains
  untouched. See the
  [pre-live control acceptance](test-results/2026-07-26-a660-ucode-allocation-v5-prelive-hold.md).
- [x] Lift HOLD through a read-only fallback/host/credential preflight and a
  fail-first-tested, verifier-before-state, explicit-opt-in NFS case for only
  v5. Keep NFS inactive and authorize only the one attended RAM-only
  transition described in the
  [pre-live GO review](test-results/2026-07-26-a660-ucode-allocation-v5-prelive-go.md).
- [x] Run the sole attended v5 ucode-allocation gate. The kernel completed
  three mappings and balanced rollback, but the userspace gate safely
  rejected public-wrapper `get=1` against an incorrect expected count of
  four. The snapshot comparison was not reached; exact fallback and complete
  host cleanup passed. V5 is consumed and must not be retried. See the
  [v5 live rejection](test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md).
- [x] Pin the accepted MSM module's symbol and `.rela.text` layout. It proves
  Clang inlined three logical vmap gets and two puts inside
  `msm_gem_kernel_new()`/`put()`, while public wrappers correctly report
  `get=1, put=2`.
- [x] Prepare and mutation-test a fresh v6 root/gate that requires three
  successful `kernel_new` calls, two `kernel_put` calls, logical vmap balance
  `4/4`, and the original equal post-settle GEM snapshot. Keep it default-off
  and non-runnable until a separate GO review. The compiler-pinned generated
  runtime, protected root, tamper test, nested watchdog gate, unchanged boot
  package, and NFS-inactive HOLD boundary pass; see the
  [v6 offline report](test-results/2026-07-26-a660-ucode-allocation-v6-offline.md).
- [x] Fail-first test a v6 one-invocation host runner that requires clean
  synchronized Git, exact root/package/gate inputs, strict SSH identity,
  private evidence, and expected reboot disconnect, while having no NFS,
  boot, retry, or flash control. The
  [v6 pre-live control acceptance](test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md)
  records **HOLD** with inactive NFS and no phone contact.
- [x] Lift v6 HOLD through a fail-first-tested, verifier-before-state,
  explicit-opt-in server case and read-only fallback/credential/host
  preflight. The
  [v6 pre-live GO review](test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md)
  authorizes at most one attended RAM-only cycle with no retry.
- [x] Run at most one attended v6 cycle only after its new offline package,
  root, runner, cleanup, and HOLD-lift requirements pass. The
  [sole v6 cycle](test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md)
  reached successful kernel allocation/rollback but safely rejected raw
  kernel-new sizes `43288`, `4`, and `4096` against page-rounded expectations.
  The snapshot check was not reached; watchdog fallback and cleanup passed.
  V6 is consumed and cannot be retried.
- [x] Build v7 from the unchanged accepted module with a source-pinned raw-size
  oracle, all v6 rollback/storage/watchdog constraints, and the mandatory
  equal post-settle GEM snapshot. Its generated runtime, protected
  consumed-v6-derived root, compiler/source verifiers, exact-delta checks, and
  two seal mutations pass offline. It remains non-runnable **HOLD**; see the
  [v7 offline report](test-results/2026-07-26-a660-ucode-allocation-v7-offline.md).
- [x] Fail-first test an exact one-invocation v7 host runner with strict SSH
  identity, immutable inputs, private evidence, no retry, and no
  NFS/boot/flash authority. Its mock transport, local credential/root checks,
  and actual unarmed refusal pass; the
  [v7 pre-live control acceptance](test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md)
  records the separate non-runnable **HOLD** checkpoint.
- [x] Lift v7 HOLD only in a later verifier-first, explicit-opt-in NFS review
  with clean Git, exact fallback, credentials, inactive services, and an
  actual unarmed-refusal test. The
  [v7 pre-live GO review](test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md)
  passes every check with zero host residue and authorizes at most one
  attended RAM-only cycle with no retry and no flash.
- [x] Run at most one RAM-only v7 cycle, require the raw-size, logical `4/4`,
  complete rollback, and equal settled-snapshot gates, then consume v7
  regardless of result. The
  [sole v7 live cycle](test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md)
  passed every gate with zero power/HFI/ZAP/SCM/storage/fault evidence,
  returned through exact fallback and complete cleanup, and is permanently
  consumed.
- [x] Source-test the GMU resume-entry seam after the initialized guard and
  before `gmu->hung`, inner runtime-PM, clocks, secure setup, bandwidth,
  MMIO, IRQ, GMU firmware, HFI, hardware initialization, or ZAP/SCM.
- [x] Fail-first test, build twice, and offline-accept the default-off,
  read-only, exact-A660.1 v8 entry diagnostic. The two complete builds are
  byte-identical; only `msm.ko` differs from accepted v7. See the
  [v8 offline report](test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md).
- [x] Reproducibly derive and mutation-test the v8 target runtime from
  immutable consumed v7 controls. Pin the compiled call/relocation layout,
  accepted allocation/rollback accounting, one outer and zero inner PM,
  zero resources/HFI/hardware/SCM, exact `EUCLEAN`, and equal GEM snapshots.
  See the
  [v8 runtime report](test-results/2026-07-26-a660-gmu-resume-entry-v8-runtime-offline.md).
- [x] Prepare and independently verify a fresh consumed-v7-derived,
  storage-free v8 root and compound target gate. Whole-tree exact-delta,
  preserved credentials, seven-module/two-firmware payload, compiled
  relocations, five negative mutations, overlapping watchdogs, inactive NFS,
  and non-runnable HOLD all pass; see the
  [v8 protected-root report](test-results/2026-07-26-a660-gmu-resume-entry-v8-root-offline.md).
- [x] Add and independently test a strict one-invocation v8 host runner with
  no NFS/boot/retry authority. Mock one-call transport, private evidence,
  local credential agreement, actual unarmed refusal, synchronized Git,
  protected-root reverification, and inactive NFS/RPC pass; see the
  [v8 pre-live HOLD report](test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md).
- [x] In an attended GO review, reverify the unchanged temporary-boot package,
  fallback, credentials, clean synchronized Git, exact root and controls, and
  add only one verifier-before-state exact-root NFS case. Full package/root
  suites, five hostile mutations, distinct SSH identities, strict read-only
  fallback health, both real unarmed refusals, and final residue-free host
  state pass; see the
  [v8 pre-live GO report](test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md).
- [x] Run exactly one attended RAM-only v8 cycle, require normal fallback and
  complete cleanup, then consume v8 regardless of acceptance or rejection.
  The
  [sole v8 live cycle](test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md)
  reached exact GMU entry and rollback with deliberate `EUCLEAN`, then failed
  closed on a zero-extended signed-return oracle. Its complete trace also
  found 21 process-scoped generic runtime-PM calls instead of the assumed one,
  while every specific inner resource probe stayed zero. Fallback and cleanup
  passed; v8 is permanently consumed, non-runnable, never retried, and never
  flashed.
- [x] Build a separately versioned v9 userspace oracle around the unchanged
  v8 kernel module. Fail-first test signed 32-bit return normalization and
  compare runtime-PM device identity rather than a process-global call count;
  retain every zero-resource, rollback, settle, snapshot, storage, and
  watchdog gate. Duplicate generation and twelve runtime mutations pass,
  including the evidence-derived 21-call fixture; see the
  [v9 offline runtime report](test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md).
  This is runtime-only HOLD with no phone authority.
- [x] Derive a fresh consumed-v8-based v9 protected root and compound target
  gate. The exact-delta verifier preserves every kernel/module, firmware,
  credential, and undeclared rootfs byte; the strengthened umbrella reruns
  the runtime mutation suite and consumed-v8 lockout. Construction and an
  independent final-path audit pass; see the
  [v9 protected-root report](test-results/2026-07-26-a660-gmu-resume-entry-v9-root-offline.md).
  The root remains absent from the bounded NFS server.
- [x] Fail-first test a strict one-invocation v9 host runner, mock its exact
  prepare/copy/remote-verify/gate sequence with no retry, prove actual unarmed
  refusal, and record a separate non-runnable pre-live HOLD checkpoint. The
  mock, local Ed25519 client/server agreement, clean synchronized Git,
  complete protected-root reverification, inactive NFS/RPC, and zero v9
  server tokens pass; see the
  [v9 pre-live HOLD report](test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-hold.md).
- [x] Fail-first test one verifier-before-state, explicit-opt-in exact-v9-root
  NFS case and rerun every local root/package/runner/credential/host gate.
  The case and actual unarmed zero-state refusal pass, but the
  [attended GO review remains HOLD](test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-go-hold.md)
  because the phone is physically absent; NFS never started.
- [x] Connect the phone in exact persistent fallback, rerun the
  identity-pinned read-only health preflight and every local GO gate, then
  authorize at most one attended RAM-only v9 cycle with no retry and no
  flash. Every prerequisite passed from the current fallback.
- [x] Run the sole v9 cycle, require signed/device-scoped runtime-PM evidence,
  exact rollback and equal settled snapshots, prove fallback/host cleanup,
  and consume v9 regardless of result. The
  [v9 live acceptance](test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md)
  passes every gate with one GPU-device outer PM event, zero specific inner
  resource events, no storage or retained DRM descriptors, complete cleanup,
  and permanent server lockout.
- [x] Source-test, mutation-test, and reproduce a separate bounded GMU/CX
  runtime-PM preparation tier. V10 isolates the first
  `pm_runtime_get_sync(gmu->dev)`, balances failed gets, synchronously
  suspends the GMU consumer and linked CX supplier, and stops before GX or
  later resources. Two isolated Linux 7.1.4 builds are byte-identical; only
  `msm.ko` differs from accepted v8. See the
  [v10 offline acceptance](test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md).
- [x] Build and mutation-test a v10 runtime oracle, fresh protected root,
  target gate, nested watchdog, one-shot/no-retry runner, and
  verifier-before-state bounded server case. Require exact GMU/CX-domain
  classification and retain every v9 rollback/snapshot/storage/watchdog
  gate. Keep GX runtime PM, clock rate/enable, secure init, MMIO, IRQ,
  firmware start, HFI, ZAP/SCM, successful open, submit, and rendering out
  of this tier. The complete runtime/root/control suite, exact-root server
  case, actual unarmed zero-state refusal, and connected fallback preflight
  pass; see the
  [v10 protected-root and pre-live HOLD report](test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-hold.md).
- [x] Complete a separate v10 pre-live HOLD review without starting NFS or
  touching the phone. Every offline and recovery prerequisite passes, but
  this checkpoint grants no live authority.
- [x] Source-audit, mutation-test, and reproduce the next GMU
  clock-preparation boundary without making it runnable. The
  [v11 offline acceptance](test-results/2026-07-27-a660-gmu-clock-preparation-v11-offline.md)
  proves that a GX-only tier would add no SM8350 hardware transition, then
  balances GX bookkeeping, both GMU rates, and all seven clocks before secure
  init. Eighteen mutations and two byte-identical isolated builds pass; only
  `msm.ko` differs from v10.
- [x] Revalidate v10 against the current synchronized branch after later
  shared-server changes. The
  [current readiness HOLD](test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-current-readiness-hold.md)
  passes every source/runtime/root/control gate, complete protected-root
  verification, byte-identical unarmed state preservation, strict fallback
  preflight, and v11 live-path exclusion. It grants no live authority.
- [x] Repeat the full technical
  [attended-GO review](test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-go-hold.md)
  after successor-v3 publication. All nine suites, recursive root comparison,
  unarmed zero-state proof, boot-image identity, and fallback preflight pass;
  HOLD remains because the exact fresh user instruction is absent.
- [ ] Keep v11 out of every root, package, export, and server allowlist until
  v10 is live-tested and consumed, then build v11-specific runtime controls,
  protected root, target/watchdog gate, no-retry runner, and separate
  HOLD/GO reviews.
- [ ] Receive the exact fresh user GO before one RAM-only v10 cycle. No retry
  or flash; consume v10 regardless of outcome.
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
- [x] Pass the narrower vendor-Alpine screen-off baseline with nested KWin
  Wayland, noVNC, ttyd, Chromium CDP, and an automatically reconnecting
  loopback-only Linux host tunnel. Prove Chromium recovery and reject a
  duplicate-producing SSH-coupled supervisor before accepting the singleton
  phone-side design.
- [x] Attribute the vendor-Alpine screen-off stack: about 390 MiB PSS for
  KDE, 345 MiB for Chromium, and 66.7 MiB for remote transport, with about
  10.1 GiB available, zero swap, and 0.78% aggregate CPU in the low-overhead
  sample. Keep the desktop and browser on demand; do not remove packages from
  this short baseline alone. See the
  [resource report](test-results/2026-07-27-alpine-screen-off-resource-baseline-live.md).
- [x] Stage and fixture-test a redacted collector for CPU, memory/PSS,
  cgroup, thermal, battery, display, and network-counter comparisons.
- [x] Audit the sealed diagnostic root and current packaging for the normal
  Plasma/KRDP/server stack, headless defaults, loopback exposure, credentials,
  automation isolation, and systemd ordering.
- [x] Build and clean-round-trip a successor normal Arch archive containing
  the current locked `rog5-agent` service and corrected hotspot unit; do not
  mutate the sealed v10 diagnostic root. The
  [successor result](test-results/2026-07-27-arch-successor-rootfs-offline.md)
  passes both full verifiers with 655 current packages.
- [x] Add a separate manifest/protected-export contract for the successor
  archive before any boot or server allowlist change. The
  [protected-export result](test-results/2026-07-27-arch-successor-protected-export-offline.md)
  passes recursive verification and three read-only COW mutation cases while
  NFS remained inactive and unallowlisted at that checkpoint.
- [x] Add a one-token exact-root NFS/runner gate without inferring live
  authority from offline export acceptance. The
  [pre-live HOLD](test-results/2026-07-27-arch-successor-v1-prelive-hold.md)
  passes verifier-first server ordering, first-boot target checks, strict-SSH
  mocked invocation, one normal reboot, and actual unarmed state preservation.
- [x] Build the
  [successor-v2 archive](test-results/2026-07-27-arch-successor-v2-rootfs-offline.md)
  and a wholly separate
  [read-only protected export](test-results/2026-07-27-arch-successor-v2-protected-export-offline.md);
  reject seal, hotspot-control, hotspot-service, and account mutations while
  leaving v1 byte-exact and NFS inactive.
- [x] Add separately versioned successor-v2 target, one-shot runner, and
  explicit-token verifier-first NFS controls. The
  [v2 pre-live HOLD](test-results/2026-07-27-arch-successor-v2-prelive-hold.md)
  passes all mocked controls and an actual unarmed invocation with
  byte-identical normalized host state; it grants no live authority.
- [x] Build and independently verify a successor-v3 development archive that
  enables the confined power-button screen toggle over the exact v2 root
  verifier.
- [x] Create its separate
  [protected pre-live HOLD](test-results/2026-07-27-arch-successor-v3-protected-prelive-hold.md):
  recursively verify the read-only root, reject four COW mutations, add
  exact-root verifier-first NFS plus power-input-aware target/runner
  controls, and prove actual unarmed host-state preservation. Keep it
  unserved and unbooted until a separate physical input/display review.
- [x] Choose v10 GPU diagnosis as the next candidate because GPU acceleration
  is the critical unmet dependency; preserve successor-v2 and protected v3
  as independent server/userspace candidates. The
  [current readiness HOLD](test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-current-readiness-hold.md)
  records the comparison, while the later
  [attended-GO HOLD](test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-go-hold.md)
  repeats every technical prerequisite after v3 publication. A fresh exact
  user GO remains mandatory before NFS or boot.
- [ ] Repeat Plasma, Baloo, browser, and remote-desktop memory/idle
  measurements on the successor Arch image with physical DRM/KWin and KRDP.
- [ ] Disable or remove services only when measurements show a useful saving.
- [ ] Evaluate GNOME only if Plasma fails a concrete requirement.

Exit gate: stable local and remote Plasma sessions with GPU acceleration and
screen-off server operation.

## Phase 9 — AI and browser automation service

Goal: let the phone host automation tools without making personal credentials a
kernel/rootfs build input.

- [x] Stage a locked, unprivileged `rog5-agent` account and its on-demand,
  loopback-only browser service; pass the complete rootfs archive round trip.
- [ ] Run model/API clients under `rog5-agent` only after the runtime secret
  and approval boundaries are implemented.
- [ ] Keep email, CV, browser sessions, API tokens, and provider credentials in
  an encrypted runtime secret store, never in Git or build artifacts.
- [ ] Require confirmation before connecting email or other external accounts.
- [ ] Separate read-only research from actions such as sending mail or applying
  to jobs; require explicit approval for consequential actions.
- [x] Add native CPU, memory, swap, task, I/O-weight, OOM, and restart limits
  to the browser service and pass a clean rootfs archive round trip.
- [ ] Add measured thermal/job-time, provider-rate, and egress limits for each
  model or external-service client.
- [ ] Back up only configuration and encrypted user data, not secrets in logs.

Exit gate: auditable, least-privilege automation with explicit credential and
action boundaries.

## Phase 10 — persistent release and recovery

Goal: turn the tested development system into something recoverable and
maintainable.

- [ ] Freeze accepted kernel, DTB, initramfs, modules, firmware, and rootfs hashes.
- [x] Define a non-repartitioning persistent boot layout with the installed
  Alpine slot-B root as the known-good fallback.
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
- [x] Install Android platform tools, add the development user to `dialout`,
  and verify the refreshed desktop login includes the group.
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
