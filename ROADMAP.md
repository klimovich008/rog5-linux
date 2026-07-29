# Roadmap

## Goal

Build a stable, observable, maintainable native Linux system for the ASUS ROG
Phone 5 (`anakin`), headless-first.

The active target is a minimal server that boots repeatably, preserves
postmortem evidence, exposes key-only SSH, keeps physical storage safe during
development, and has correct power, charging, thermal, input, sensor, audio,
and wireless behavior. Basic display, GPU acceleration, Plasma/GNOME, remote
GUI, refresh-rate tuning, VPN hotspot, and AI workloads resume only after the
headless core passes its reliability gate.

Normal operation must eventually stop depending on Android, an interactive
recovery shell, or an attended temporary boot. Development remains
temporary-boot-only until a persistent path is separately designed, tested,
and approved.

## What “incremental” means

Incremental bring-up does **not** restart or redo accepted work. Existing
hashes, sealed roots, live evidence, recovery design, WCN6855 analysis, GPU
ancestry, and fallback services remain immutable baselines.

Incremental means changing one unproven hardware boundary at a time and
requiring an observable pass/fail result before widening the next boundary.
Only integration glue is replaced when the stable framed recovery supersedes
legacy ACM transport.

## Active and frozen profiles

The active build profile contains only:

- kernel, initramfs, and a minimal root filesystem;
- systemd or an equivalently small init;
- USB networking and key-only SSH;
- logging, watchdog, rollback, and health telemetry;
- tools required by the current hardware acceptance gate.

The following are frozen, not deleted:

- Plasma, KWin, GNOME, KRDP, noVNC, ttyd, Chromium, and browser automation;
- Vulkan userspace, Turnip helpers, and A660 v9/v10/v11 candidate work;
- fail-closed hotspot and automation-agent packaging;
- superseded live-gate scripts still required to prove accepted ancestry.

The Alpine fallback GUI remains an operator lifeline. It is not part of the
active mainline target.

## Safety rules

1. Tests and rollback contracts precede hardware execution.
2. No experimental partition flash; use only an explicitly allowed attended
   `fastboot boot`.
3. Keep the installed fallback slot untouched.
4. One live diagnostic payload gets at most one execute attempt.
5. Transport loss is `UNKNOWN`; it never authorizes a retry.
6. Accepted evidence is immutable and inherited by hash.
7. Physical storage stays read-only until a bounded persistent-root write
   contract is separately approved.
8. Credentials, personal data, and private evidence remain outside Git.
9. A kernel version bump does not replace subsystem bring-up.
10. No desktop, GPU, or automation dependency may enter the active headless
    profile before its gate.

## A0 — Shorten the development loop

Status: **in progress**

### A0.1 Postmortem outcome oracle

- [x] Confirm the accepted 5.4 recovery wrapper has built-in `PSTORE_RAM` and
  the exact 4 MiB ramoops command-line reservation.
- [x] Snapshot pstore into RAM without deleting records.
- [x] Export state, record count, byte count, SHA-256, and a bounded log tail
  through framed `HELLO`/`STATUS` responses.
- [x] Cover empty, present, unavailable, malformed, crash/restart, partial-I/O,
  and watchdog cases offline.
- [x] Rebuild the postmortem-enabled initramfs, wrapper kernel, raw boot
  image, and test-only AVB image twice and prove byte identity.
- [ ] Prove experimentally whether ramoops survives target → bootloader →
  recovery on this phone.
- [ ] If DRAM does not survive, test the Qualcomm USB-C debug UART before
  designing another oracle.

Exit: every attended target execution yields `PASS`, `FAIL`, or bounded
`UNKNOWN` evidence without relying on timing guesses.

### A0.2 Stable recovery platform

- [x] Replace the interactive ACM shell with the fixed framed responder.
- [x] Keep signed runtime payloads separate from the recovery image.
- [x] Implement at-most-once prepare/commit state and a host write-ahead
  ledger.
- [x] Build the shell-free initramfs and wrapper reproducibly with ephemeral
  keys.
- [ ] Embed a separately approved production public key.
- [ ] Update all source, hash, verifier, and wrapper pins in one release
  change.
- [ ] Pass staging-only promotion cycles before replacing v18 authority.

Exit: one frozen recovery handles future kernel, DTB, initramfs, and
postmortem operations without per-candidate recovery rebuilds.

### A0.3 Hardware-free automation

- [x] Add one `ci` repository-test tier with no phone, Vulkan, desktop, or
  delegated-cgroup dependency.
- [x] Add a GitHub Actions workflow for the recovery protocol, native
  responder, bundle verifier/fetcher, host controller, boot policy, and
  repository policy.
- [x] Observe the first green GitHub run.
- [x] Add a full-system `qemu-system-aarch64 -M virt` boot harness for generic
  initramfs/root handoff, pinned to an exact upstream Linux commit.
- [x] Replace the hosted `defconfig` build with a reproducible, QEMU-only
  `tinyconfig` kernel after the first run exceeded its 35-minute bound.
- [x] Cache only the content-keyed kernel Image and avoid duplicate
  feature-branch push/PR runs.
- [x] Keep QEMU tests board-neutral; never claim that QEMU proves ROG Phone
  hardware.

Exit: parser, initramfs, recovery, root handoff, and policy regressions fail
before a phone cycle.

### A0.4 Reduce candidate overhead

- [ ] Replace version-per-candidate prepare/serve/verify/run glue with one
  manifest-driven runner. The strict offline manifest-to-bundle preparation
  adapter is complete; fixed serve/verify/execute integration remains.
- [ ] Extract only the already-proven generic safety checks needed by that
  runner; do not create a new framework.
- [x] Port the consumed persistent-root P2 payload into the manifest adapter
  and prove exact artifact/profile parity offline without restoring live
  authority.
- [ ] Add compiler caching and preserve incremental kernel output trees.
- [x] Create a minimal SSH-only root profile with no display, desktop,
  browser, Vulkan, hotspot, or agent packages.

Exit: a new hardware candidate changes a manifest, DT/kernel delta, and its
specific assertion—not five copied scripts and a full userspace image.

### A0.5 Artifact retention

The current ignored footprint is approximately 166 GiB: 113 GiB under
`artifacts/` and 53 GiB under `build/`. No data is deleted merely because it
looks reproducible.

- [x] Preserve the tracked pre-reduction checkpoint at
  `archive/pre-stable-recovery-2026-07-28`.
- [x] Recompute the current top-level footprint.
- [ ] Generate a machine-readable prune plan with size, identity, references,
  role, and reproduction command for every candidate.
- [ ] Review the plan before deleting or deduplicating anything.

Exit: active inputs and irreplaceable evidence are obvious; failed and
duplicate builds can be removed safely.

## H1 — Recovery, logging, and rollback

- [ ] Promote the framed recovery candidate through the approved live gate.
- [ ] Prove deterministic target, recovery, fallback, and watchdog outcomes.
- [ ] Prove postmortem retention or select the tested UART fallback.
- [ ] Retire legacy ACM execution helpers from active operation.

Exit: failed boots are diagnosable and recover automatically.

## H2 — Minimal headless boot

- [ ] Package one signed minimal root bundle.
- [ ] Boot kernel → initramfs → read-only root.
- [ ] Verify storage discovery, USB NCM, init, key-only SSH, time sync, and
  clean reboot.
- [ ] Remove desktop/browser/GPU packages from the active image.
- [ ] Prove the fallback root remains unchanged after failure.

Exit: a repeatable native Linux shell is reachable without Android or a GUI.

## H3 — Power and lifecycle

- [ ] Verify charger detection and safe charging states.
- [ ] Verify battery capacity, voltage, current, and temperature telemetry.
- [ ] Bound thermal zones and emergency shutdown behavior.
- [ ] Verify power-off, reboot, watchdog reboot, and bootloader reboot.
- [ ] Verify suspend, wake, true panel-off behavior, and SSH continuity.
- [ ] Measure idle, screen-off, charging, and sustained-load power.

Exit: the phone can run unattended without overheating, silently discharging,
or losing remote reachability.

## H4 — Input and sensors

- [ ] Verify power and volume keys with IRQ/wakeup behavior.
- [ ] Verify touchscreen input independently of the desktop.
- [ ] Bring up IMU, compass, ambient-light, and proximity sensors one at a
  time.
- [ ] Add calibration controls only where physical measurements require them.
- [ ] Treat fingerprint, NFC, and cameras as separate later scopes.

Exit: each required input/sensor has a stable kernel interface, bounded test,
and suspend/resume result.

## H5 — Audio and connectivity

- [ ] Bring up playback, capture, routing, and headset detection.
- [ ] Enumerate WCN6855/PCIe/MHI without radio activation.
- [ ] Bring up Wi-Fi client mode, then Bluetooth.
- [ ] Bring up GPS and modem only where firmware, legality, and upstream
  support make them feasible.
- [ ] Keep hotspot/VPN policy frozen until Wi-Fi client reliability passes.

Exit: selected server peripherals survive repeated init, shutdown, and
suspend cycles.

## H6 — Persistent headless reliability

- [ ] Design and test a bounded A/B read-only root selector offline.
- [ ] Ask separately before any persistent selector or boot-partition change.
- [ ] Promote only after rollback and root integrity are proven.
- [ ] Pass reboot stress, suspend stress, network recovery, and 24-hour
  screen-off SSH reachability.

Exit: the phone is a dependable native Linux server.

## H7 — Basic local display

The Samsung AMS678 panel sits behind the Pixelworks Iris/i6 bridge. Linux
7.1.4 has no matching upstream bridge/panel path, so this is a driver-porting
project rather than a configuration switch.

- [ ] Document the smallest bridge/panel command and power sequence from
  stock evidence.
- [ ] Implement and test bridge, panel, backlight, DPMS, and mode setting.
- [ ] Start at 60 Hz; measure before enabling 90/120/144 Hz.
- [ ] Keep display failure independent from headless boot and SSH.

Exit: a basic unaccelerated console/Wayland scanout survives screen cycles.

## H8 — Headless GPU acceleration

Accepted A660 ancestry remains frozen through v9; v10 is offline/HOLD and v11
is source-only.

- [ ] Remove the current KWin requirement from preflight-only GPU acceptance.
- [ ] Port the accepted GPU boundary into a signed runtime bundle.
- [ ] Bring up GPUCC, GMU/HFI, SMMU, firmware, and `/dev/dri/renderD*`.
- [ ] Pass render-node open/close, real Vulkan submission, fault, thermal, and
  suspend/resume gates without requiring a display server.

Exit: compute/render-node acceleration is stable on the headless system.

## H9 — Desktop and remote GUI

- [ ] Select Plasma or GNOME only after measuring the stable headless baseline.
- [ ] Add accelerated local Wayland.
- [ ] Prefer KRDP/Wayland for normal remote GUI; retain noVNC only as fallback.
- [ ] Validate power-button indication, panel off/on, refresh rates, Chromium,
  memory pressure, thermal behavior, and battery drain.

Exit: the optional desktop does not reduce server reliability.

## H10 — Network appliance and automation

- [ ] Restore the already-tested fail-closed WireGuard hotspot policy after
  Wi-Fi/AP reliability passes.
- [ ] Keep automation under a separate locked, resource-limited account.
- [ ] Use narrow, revocable connectors instead of copying email, CV, browser
  profiles, or credentials into the image.
- [ ] Require explicit confirmation before sending messages, applying to a
  job, modifying cloud data, or making a purchase.
- [ ] Compare local and remote AI models only after thermal and power budgets
  are measured.

Exit: optional services are confined, auditable, revocable, and do not weaken
the core system.

## Kernel maintenance

The project will not create a kernel “from scratch.” It maintains a small,
reviewable SM8350/ASUS delta on an upstream kernel and reduces that delta over
time.

- [x] Reproduce Linux 7.1.4 ARM64 builds on the PC.
- [x] Maintain reviewed config, DTS, patch, module, and evidence identities.
- [ ] Pin the complete source/toolchain bootstrap for a fresh clone.
- [ ] Add KUnit/selftests where hardware-independent logic exists.
- [ ] Track upstream SM8350, UFS, USB, charger, input, sensor, audio, WCN6855,
  display, and Adreno changes.
- [ ] Rebase only when old and new bases pass the same recovery and subsystem
  gates.

## Current next action

The A0 feedback-loop work is green. Continue in this order:

1. package the verified SSH-only root into a signed runtime bundle;
2. complete fixed serve/verify/execute integration for the manifest runner;
3. generate, but do not execute, the artifact prune plan;
4. obtain explicit approval for a production recovery trust root;
5. promote the stable recovery through staging-only tests and measure pstore
   retention.
