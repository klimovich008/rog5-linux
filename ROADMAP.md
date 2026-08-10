# Roadmap

## Goal

Build a stable, observable, maintainable native Linux system for the ASUS ROG
Phone 5 (`anakin`), headless-first.

Long-term success means the phone can run unattended as a minimal native-Linux
ARM server with repeatable builds, bounded recovery, key-only remote access,
screen-off operation, and measured power and thermal behavior. A newer kernel,
GPU, desktop, or persistent install is not a substitute for that foundation.

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
3. Keep the installed fallback configuration and authorization untouched.
   The standing operator authorization covers only the already-bounded
   fallback ACM shell-history and read-induced atime effects.
4. One live diagnostic payload gets at most one execute attempt.
5. Transport loss is `UNKNOWN`; it never authorizes a retry.
6. Accepted evidence is immutable and inherited by hash.
7. Outside the standing-authorized fallback history/atime effects, physical
   storage stays read-only until a bounded persistent-root write contract is
   explicitly added to project scope.
8. Credentials, personal data, and private evidence remain outside Git.
9. A kernel version bump does not replace subsystem bring-up.
10. No desktop, GPU, or automation dependency may enter the active headless
    profile before its gate.

## A0 — Shorten the development loop

Status: **offline speed-amplifier boundary complete; live promotion pending**

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
- [x] Build a distinct observation-only recovery initramfs that can report
  postmortem status but has no fetcher, verifier, kexec binary, bundle root,
  or protocol path capable of preparing or committing a payload.
- [x] Build that observation identity through two clean ASUS 5.4 wrapper,
  boot-v3, and unsigned-AVB compositions and verify its exact pstore/ramoops
  contract without issuing a candidate.
- [x] Add a distinct read-only fallback transition preflight that verifies the
  exact `0x9b800000 + 0x400000` DT reservation and command-line tuple, no
  overlapping fixed reservation, no bound ramoops consumer, and empty pstore
  before a later observation-recovery boot.
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
- [ ] Embed an independently reviewed production public key.
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
- [x] Package `headless-core-v2` as a separately identified, whole-tree-sealed
  network root and assemble its buttons DTB into a twin-built,
  ephemeral-signed recovery candidate without phone or production-key access.
- [x] Cache the verified stable-recovery wrapper by exact source, config,
  initramfs, builder, and output hashes so ordinary candidate iterations do
  not repeat two broad vendor-kernel builds.
- [x] Add a separate wrapper-config slimming audit; do not mix that change
  with a live headless-core candidate.
- [x] Replace the hosted `defconfig` build with a reproducible, QEMU-only
  `tinyconfig` kernel after the first run exceeded its 35-minute bound.
- [x] Cache only the content-keyed kernel Image and avoid duplicate
  feature-branch push/PR runs.
- [x] Keep QEMU tests board-neutral; never claim that QEMU proves ROG Phone
  hardware.
- [x] Exercise the exact network-root NFSv4.2 client options under Linux 7.1.4
  against a userspace server, with the production `/30`, TCP-only forwarding,
  server-enforced read-only behavior, and hostile drift tests. The private
  tmpfs VFS export carries the sealed ARM64 systemd/OpenSSH runtime with exact
  numeric ownership. The test guest continues through the
  `mount_network_root()` function extracted verbatim from the current
  production init, proving one diagnostic attempt, stages 70, 75, 80, 90,
  and 100, production shutdown-root handoff and `switch_root`, real systemd
  PID 1, and real key-only OpenSSH. Its terminal proof revalidates exact
  OverlayFS, NFS, and tmpfs topology after handoff. This closes the
  hardware-free path through minimal userspace service; it does not prove
  USB/NCM continuity on the phone.
- [x] Convert the ASUS 5.4 and accepted Linux 7.1 behavioral ancestry into a
  fail-closed core compatibility profile, committed golden Kconfig, build
  gate, and 39-case mutation/CLI suite.
- [x] Bind all six active capabilities to 43 source-integration checks and 23
  corrected-DTB topology checks, with separate exact-baseline and
  compatible-but-unaccepted candidate modes.
- [x] Pin the accepted static thermal topology: both TSENS critical IRQs
  through PDC/GIC, all 12 CPU zones and cooling maps, five PMIC alarms and
  zones, the kernel critical-shutdown call chain, and hostile mutations.
  Keep PMIC built-in enforcement and a bounded forced fallback future-only.
- [x] Add one canonical 68-field runtime observation, candidate-bound host
  verifier, 27 target mutations, 21 host test groups, and a strict-SSH
  one-collection runner test for all six active capabilities, including
  mount/path-attested NFSv4.2 and zero block/SCSI/RPMB/UFS exposure.
- [x] Add a credential-free volatile host-key bootstrap that binds the signed
  recovery and target NCM gadgets to one physical USB port, requires an exact
  direct `/30` route, pins one nonzero Ed25519 key, and rechecks continuity
  before strict SSH can use a client credential.

Exit: parser, initramfs, recovery, root handoff, and policy regressions fail
before a phone cycle.

### A0.4 Reduce candidate overhead

- [x] Replace version-per-candidate prepare/serve/verify/run glue with one
  manifest-driven runner and prove real packager/server/fetcher/verifier/
  responder composition with the consumed P2 fixture.
- [x] Extract only the already-proven CPU/RAM, network-root/storage, USB/SSH,
  thermal, fatal-signature, and watchdog checks into one read-only probe and
  fail-closed verifier; keep boot/sign/reboot/fallback orchestration separate.
- [x] Port the consumed persistent-root P2 payload into the manifest adapter
  and prove exact artifact/profile parity offline without restoring live
  authority.
- [x] Add an explicit, fail-closed compiler-cache option and preserve
  exact-identity incremental kernel output trees for the active baseline
  builder; clean release twins remain mandatory.
- [x] Create a minimal SSH-only root profile with no display, desktop,
  browser, Vulkan, hotspot, or agent packages.
- [x] Seal that root as a byte-reproducible read-only network lower, bind its
  explicit no-workload manifest and complete tree into an authority-free v2
  candidate, and verify an ephemeral-signed bundle natively.
- [x] Audit the pruned root reconstruction, reject the generated Pacman
  private signing key/revocation state, and make minimal-root staging
  network-disabled and credential-clean.
- [x] Build the corrected minimal root twice from fresh volumes and require
  byte-identical output before assigning a new successor identity.
- [x] Add `headless-ssh-v2` plus v3 identity/package records that bind one
  canonical Ed25519 fingerprint across the root, complete seal, and package;
  hostile key, metadata, mismatch, and downgrade tests pass with a public-only
  fixture.
- [x] Bind the v3 package to a distinct corrected-DTB recovery candidate and
  pass twin signed-bundle, native-verifier, shell-free recovery, clean ASUS
  wrapper, boot-v3, and test-only AVB gates with a destroyed disposable key.
- [x] At the live gate, derive the public half from the caller's private key,
  reject the fixture fingerprint, and require exact v3/profile pairing before
  any connected preflight.
- [x] Carry the admitted package and candidate identities through the fixed
  v3 NFS handoff, recovery COMMIT rendezvous, target probe, and runtime
  verifier while preserving the historical no-argument path.
- [x] Add a fixed root-owned v3 export installer and unprivileged launcher
  that rerun key admission, reject fixture identities and unsafe archives,
  privately snapshot caller-owned bytes, verify and durably sync the extracted
  root, and publish once without replacing an existing export.
- [x] Rebuild the root/package/candidate/runtime-manifest chain around a
  separately authorized non-fixture key, pin its stable-recovery
  wrapper/trust/manifest profile, and pass every host-only artifact gate.
- [x] Install the remediated fixed read-only NFS export on SteamOS's large
  `/home` filesystem after the original `/var` publication stopped safely;
  pass sealed-root, fixed-NFS, artifact, and connected-fastboot
  preflights.
- [x] Remove fallback client-key authorization from the lifecycle with a
  fixed nonce-framed USB ACM verifier. Bind its canonical health record to the
  existing pinned Alpine Ed25519 host key, exact physical USB path, bounded
  thermal/log checks, a sub-2,048-byte isolated loader with ready-before-data
  framing, one-contact lifecycle semantics, and a separately guarded
  ACK-before-`RESTART2` path.
- [x] Separately authorize the bounded BusyBox-history and possible ext4-atime
  effects of one fallback ACM action and pass one live cryptographic
  preflight with a private no-replace signed proof.
- [x] Preserve fallback proof through the attended minimal-headless lifecycle
  over strict SSH without entering the interactive Alpine ACM shell. The
  target rejection returned to the same port and resolved its durable intent.
- [x] Permanently reject the consumed deployment manifest before private-key
  inspection and stage an r2 signed-bundle identity that keeps every target
  artifact and root identity unchanged.
- [x] Sign, twin-build, install, and preflight r2; execute it exactly once.
  Recovery transfer, PREPARE, COMMIT, watchdog rollback, and signed fallback
  proof passed. The target USB gadget disconnected after 23 seconds before
  SSH acceptance, so r2 is consumed and a distinct diagnostic successor is
  required.

Exit: a new hardware candidate changes a manifest, DT/kernel delta, and its
specific assertion—not five copied scripts and a full userspace image.

### A0.5 Artifact retention

The current read-only snapshot records 234,216,853,504 allocated bytes and
234,452,626,574 apparent bytes across 99 top-level units, with six nested
recovery temporary units classified separately. No data is deleted merely
because it looks reproducible.

- [x] Preserve the tracked pre-reduction checkpoint at
  `archive/pre-stable-recovery-2026-07-28`.
- [x] Recompute the current top-level footprint.
- [x] Generate a
  [machine-readable prune plan](test-results/2026-07-29-artifact-prune-plan.json)
  with size, identity, references, role, and reproduction status for every
  candidate.
- [x] Review and execute the exact 87-volume detached Podman delete set with
  candidate-set, plan, repository-state, mount, and reference guards.
- [x] Preserve the 11 accepted source/build/cache volumes and verify zero
  remaining Podman prune candidates.
- [ ] Review the separate external development/cache candidates before any
  additional deletion.

Exit: active inputs and irreplaceable evidence are obvious; failed and
duplicate builds can be removed safely.

## H1 — Recovery, logging, and rollback

- [x] Admit the exact corrected successor through the phone-free production
  recovery-artifact gate and reject the consumed historical profile before
  credentials.
- [x] Restore the missing NFS-root dependency with a credential-clean,
  byte-reproducible successor identity; recovery admission alone is not a
  complete runnable candidate.
- [x] Promote the framed recovery candidate through the approved live gate;
  its transfer, PREPARE, and one COMMIT passed on hardware.
- [ ] Prove deterministic target, recovery, fallback, and watchdog outcomes.
- [ ] Prove postmortem retention or select the tested UART fallback.
- [x] Retire legacy ACM execution helpers from active operation. Their
  transport/parser bodies remain historical evidence, but all three Python
  entry points and both old live-gate runners now refuse before authority,
  credential, host, USB, or phone inspection; the framed stable-recovery
  lifecycle is the only active execution path.
- [x] Build the
  [early-target diagnostic successor](docs/early-target-diagnostics.md) with a
  one-way framed stage stream, bounded failure dwell, switch-root continuity,
  hostile parser/emitter tests, and a distinct consumed-once identity before
  another phone cycle.
- [x] Integrate its receive-only collector into the one-shot lifecycle before
  recovery control, require explicit readiness before COMMIT, preserve
  rejected evidence, and keep normal target SSH acceptance unchanged.
- [x] Add a credential-free no-replace diagnostic candidate preparer, fixed-ID
  signing-input admission before key access, a guarded twin-build wrapper,
  and a distinct production recovery-artifact profile. Keep both consumed
  normal manifests denied by the lifecycle and direct boot gate.

Exit: failed boots are diagnosable and recover automatically.

## H2 — Minimal headless boot

- [x] Preserve the historical ephemeral-signed minimal-root bundle evidence;
  the pruned root identity is not reusable.
- [x] Package and verify the credential-clean reproducible root successor.
- [x] Production-sign and twin-build the exact diagnostic successor; pin its
  diagnostic-only artifact tuple and pass the complete native artifact gate.
- [ ] Boot kernel → initramfs → read-only root.
- [ ] Verify storage discovery, USB NCM, init, key-only SSH, time sync, and
  clean reboot.
- [x] Remove desktop/browser/GPU packages from the active image. The three
  requested packages remain `attr`, `diffutils`, and `openssh`; the complete
  152-package dependency closure is now byte-pinned and checked against both
  the recorded inventory and a fresh `pacman -Q` result during every stage.
- [ ] Prove the fallback root remains unchanged after failure.

Exit: a repeatable native Linux shell is reachable without Android or a GUI.

## H3 — Power and lifecycle

- [x] Define and hostile-test a read-only 10-minute battery-series record for
  unplugged, USB-online, and wireless-online phases plus a same-boot
  unplugged/USB comparison that derives current sign instead of guessing it;
  hardware execution remains pending.
- [x] Add a compile-only, DT-opt-in ASUS dual-cell voltage read to upstream
  qcom_battmgr without importing vendor charging controls. Exact protocol,
  DT-delta, sysfs framing, and hostile fixture gates pass. Two clean complete
  uncached builds now reproduce the kernel, symbol table, module archive,
  metadata, linked driver, and exact candidate DTB; all phone observations
  remain pending and the local candidate has no boot authority.
- [x] Freeze the accepted Linux 7.1.4 static thermal source/DTB topology and
  reject disabled/rewired TSENS, CPU cooling, trip, PMIC, and shutdown paths.
  This is an offline regression gate, not runtime thermal acceptance.
- [x] Add an offline minimal-server display-isolation DTB that explicitly
  disables the otherwise implicit DISPCC provider, changes no other DT
  property, and hostile-tests zero display platform/class/device exposure.
  This is not live OLED-off or power acceptance.
- [x] Add a compile-only suspend-debug candidate and at-most-once target gate
  for exactly one `pm_test=devices` callback pass. The pinned-source oracle
  proves that level returns before platform, CPU, or PSCI entry; hostile tests
  classify post-return UDC, interface, carrier, address, and route loss. No
  phone execution or real suspend has occurred.
- [ ] Verify charger detection and safe charging states.
- [ ] Verify battery capacity, voltage, current, and temperature telemetry.
- [ ] Prove CPU cooling response and PMIC alarm registration on the corrected
  target, with `qcom-spmi-temp-alarm` built in.
- [ ] Profile and enable a 10–30 second forced thermal shutdown fallback;
  never test critical temperature by deliberately overheating the phone.
- [ ] Verify power-off, reboot, watchdog reboot, and bootloader reboot.
- [ ] Run the devices-level `pm_test` on a separately authorized temporary
  target, then verify attended wake sources before any real suspend; true
  panel-off behavior and SSH continuity remain pending.
- [ ] Measure idle, screen-off, charging, and sustained-load power.

Exit: the phone can run unattended without overheating, silently discharging,
or losing remote reachability.

## H4 — Input and sensors

- [x] Encode and hostile-test the stock-evidenced power, volume-down,
  volume-up, and default-off green indicator DT/kernel contract.
- [x] Replace the Python-only power-key monitor gap with a dependency-free,
  hostile-tested three-key runtime gate that verifies exact input identity,
  press/release pairs, bounded IRQ movement, wake policy, and unchanged
  minimal-server isolation. Hardware execution remains pending.
- [ ] Verify all three physical keys with IRQ behavior and a bounded
  userspace health indication.
- [ ] Verify wake behavior and idle-power impact separately under the H3
  suspend gate.
- [ ] Verify touchscreen input independently of the desktop.
- [x] Freeze the exact ASUS 5.4 VCNL36866 ambient-light/proximity board and
  wire-protocol oracle, prove the device is inherited unchanged through the
  EVB-to-MP5 overlay chain, and classify accepted Linux 7.1.4 as
  `port-required`. The future driver/DT/runtime boundary is hostile-tested;
  no driver has been implemented or run on hardware yet.
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
- [x] Pin the complete Linux source/toolchain bootstrap for a fresh clone.
- [x] Reconstruct the historical no-local-tag Git state and builder closure;
  recover all five frozen `network-root-v1` kernel artifacts in two
  byte-identical, network-disabled builds.
- [x] Reconstruct the pruned v18r/network-root/headless recovery chain,
  qualify reboot-safe rootless ARM64 builders, bootstrap Android image tools
  from immutable AOSP blobs, and replace the missing broad boot template with
  a compact reproducible metadata template.
- [x] Add a fail-closed source/DT integration oracle for the accepted
  baseline and future candidate comparisons.
- [ ] Add KUnit/selftests where hardware-independent logic exists.
- [ ] Track upstream SM8350, UFS, USB, charger, input, sensor, audio, WCN6855,
  display, and Adreno changes.
- [ ] Rebase only when old and new bases pass the same recovery and subsystem
  gates.

## Current next action

The hardware-free recovery, corrected-DTB, non-fixture key-bound root, NFS,
runtime, rollback, thermal, fallback, and CI gates are complete. Diagnostic
generations 0–12 are consumed and absent from temporary-boot policy.
Generation 7 transferred the complete signed bundle but the host rejected its
post-transfer deferred-profile observation before receiving `PREPARED`; no
intent, NFS handoff, or target execution occurred. Exact fallback and strict
SSH passed.

Both host cleanup defects exposed by that cycle are now reproduced and fixed
offline without extending deadlines or weakening identity checks. Firewalld
state uses three coherent snapshots instead of roughly 23 subprocesses, and
the NetworkManager verifier now handles the exact one-empty-field rendering
of a NULL `GENERAL.CON-UUID`. Generation 8 was host-locally twin-issued and
passed connected preflight. Its sole RAM-only boot transferred the complete
signed bundle, but recovery returned no PREPARED record. The terminal
identity-stability rejection did not label whether it sampled initial recovery
or replay discovery after transport loss; Generation-9 timing makes replay of
watchdog fallback plausible but does not retroactively prove it. No COMMIT
intent or target execution existed. Exact Alpine fallback returned. The final
host proof separately
exposed an empty root-owned mode-`0600` NFS export-table inspection defect;
independent checks found no host residue.

Generation 9 then passed its reviewed one-shot admission and connected
preflight. Its sole RAM-only lifecycle reached exact recovery ACM/NCM and
transferred all 46,163,787 signed-bundle bytes, but no `PREPARED` response
reached the host before recovery USB disconnected and watchdog fallback began.
The final 216-sample product-mismatch trace is best explained by fallback-only
replay discovery, but that generation did not label the phase directly. No
COMMIT intent existed, no target ran, and exact Alpine fallback plus final host
cleanup passed. Generation 9 is consumed, absent from policy, and never
reusable. Its ambiguity motivated the labeled replay and correlated progress
instrumentation used by Generation 10.

Generation 10 then passed exact key and connected preflight at the reviewed,
published, exact-head-green checkpoint. Its sole RAM-only lifecycle reached
exact recovery ACM/NCM, emitted correlated `REQUEST_ACCEPTED`, and caused the
host to send all 46,163,787 signed-bundle bytes. The response transport then
closed before any later progress or `PREPARED` response reached the host; the
exact device-side fetch/verify/load boundary remains unknown. Replay was
explicitly classified as `prepare-replay` with 216 stable
fallback/product-mismatch samples. The pre-COMMIT NFS export became ready, but
no COMMIT intent existed and no target ran. Exact Alpine fallback, strict SSH,
profile restoration, and final host cleanup passed. Generation 10 is
permanently `BOOT_CLAIMED`, absent from boot policy, consumed in inventory, and
never reusable. The next correction must make post-acceptance progress
independently observable across ACM loss. Generation 11 implemented that
channel but was consumed by the later host listener-confinement failure; the
Generation-12 host correction reproduced the real scoped TCP 8081 endpoint and
implemented exact endpoint/sole-owner verification offline. Its sole cycle
then reached target stage 70 `nfs-mount-begin` before USB disconnected. Exact
fallback passed; Generation 12 is consumed. The current host-only work repairs
the outer response parser and defines stronger NFS/USB/postmortem evidence
before a distinct successor may be issued; no phone boot is implied.

Current execution order:

1. **Complete:** pass the focused and complete local suite, constrained
   read-only review, publication, and GitHub CI for the exact NetworkManager
   parser correction at `61c6ddd`.
2. **Complete:** revalidate installed host components, the sealed deployment
   root, credential admission, and exact connected Alpine fallback without
   issuing or booting a candidate.
3. **Complete:** publish the pre-issuance checkpoint and the test-first
   deterministic Generation-8 issuer/non-reuse regression after auditing
   every retained source and Generation-7 input.
4. **Complete:** publish the host-locally twin-reproduced Generation-8
   identity and immutable offline-only profile; keep central boot policy at
   zero `allow` rows.
5. **Complete:** add a separate live lifecycle profile while keeping central
   policy at zero `allow` rows.
6. **Complete:** add one-shot central admission after artifact,
   credential, rollback, host-cleanup, and fallback host-only preflights pass;
   publish it at `c667718`, and pass exact-head GitHub run `30832269180`.
7. **Complete:** pass connected preflight, run the sole Generation-8 RAM-only
   diagnostic lifecycle, preserve private evidence, consume it for the safe
   pre-COMMIT rejection, and restore exact Alpine fallback without retry.
8. **Complete:** the mode-`0600` export table is now inspected read-only
   through the fixed privileged broker with no permission mutation; exact
   empty, metadata, hard-link, symlink, missing, and nonempty cases are covered
   offline, and the exact reviewed bytes pass two real-host proofs without
   changing table identity or metadata. The bounded non-sensitive recovery-ACM
   classifier and test-first Generation-9 issuer regression are published and
   green.
9. **Complete:** offline issuance of two byte-identical host-local
   Generation-9 successors passed exact-head GitHub run `30841980164` at
   `6193056`; the separate live-profile transition passed exact-head run
   `30843398402` at `4979581` while central policy remained empty.
10. **Complete:** publish the exact Generation-9 central-policy admission at
    `eea0989`; complete local CI and exact-head GitHub run `30847253087` pass.
11. **Complete:** pass key and connected preflight, run the sole Generation-9
    RAM-only lifecycle, preserve its permanent `BOOT_CLAIMED` record, remove
    admission after the safe pre-COMMIT rejection, and prove exact Alpine
    fallback plus final host cleanup. The complete bundle transferred, but
    recovery returned no `PREPARED` response before watchdog fallback; see the
    [live result](test-results/2026-08-03-generation-9-prepared-response-gap-live.md).
12. **Complete:** initial/replay ACM discovery is labeled separately; the
    native responder emits five canonical PREPARE boundaries; the host enforces
    one correlated contiguous prefix per attempt and retains both prefixes on
    transport failure. Progress remains advisory, a send failure suppresses
    later phases without changing safe PREPARE state, and watchdog exit remains
    independently observed out of band. No Generation 10 was issued at that
    checkpoint.
13. **Complete:** the
    changed responder is byte-verified inside two identical
    recovery initramfses and two clean, byte-identical ASUS 5.4 wrapper/raw/AVB
    builds. The disposable signing key was destroyed, `authority=none`, and no
    Generation 10 artifact or phone action was created at that checkpoint.
    Full local CI,
    constrained re-review, publication at `6b9f00e`, and exact-head GitHub run
    `30860916085` pass. See the
    [offline integration result](test-results/2026-08-03-prepare-progress-wrapper-integration-offline.md).
14. **Complete:** the guarded
    production signing-input preflight and deterministic synthetic issuer
    regression through Generation 10 passed without creating an artifact and
    were published at `d6d20b0`; exact-head GitHub run `30861861026` is green.
    The subsequent guarded production build retained identical A/B signed
    bundles, initramfses, wrapper Images, raw wrappers, and canonical AVB
    wrappers under the existing production trust root. Two independent
    Generation-10 issuances now retain exact matching 11-file trees at AVB
    `b983e89b…8b51` over unchanged raw recovery `27f4dbcc…73b3`. The key
    snapshot was destroyed, external inputs remained unchanged, no phone was
    contacted, and every record retains `authority=none`. See the
    [issuer-readiness result](test-results/2026-08-03-generation-10-issuer-readiness-offline.md)
    and
    [offline successor result](test-results/2026-08-03-generation-10-prepare-progress-successor-offline.md).
    The production issuance was independently reviewed, published at
    `d04b804`, and passed exact-head GitHub Actions run `30865091104`.
15. **Complete:** the immutable
    `headless-diagnostic-generation10-offline-v1` profile pins the full tuple,
    rejects connected actions before host inspection, and passes both retained
    host-local 11-file trees plus generation-record mutation rejection. Clean
    CI skips those ignored trees. Artifact inventory
    records `unbooted` and `authority=none`; boot policy remains unchanged with
    zero `allow` rows. See the
    [offline profile result](test-results/2026-08-03-generation-10-offline-profile.md).
    Constrained review and full local CI passed; publication at `edae5d1` and
    exact-head GitHub Actions run `30867110893` are green.
16. **Complete:** the distinct
    `headless-diagnostic-generation10-live-v1` profile and lifecycle selector
    reuse the exact tuple. Direct connected actions require the lifecycle
    controller; missing, duplicate, and wrong-basis policy states reject before
    host inspection. This profile transition was published at `adc4123` and
    passed exact-head GitHub Actions run `30869110964` while central policy
    still had zero `allow` rows.
    See the
    [live-profile result](test-results/2026-08-04-generation-10-live-profile-offline.md).
17. **Complete:**
    central policy admitted exactly one Generation-10 image and basis
    for one connected-preflight-gated RAM-only lifecycle. Missing, duplicate,
    and wrong-basis policy fixtures reject before host inspection; inventory
    retains issuance `authority=none`, `unbooted`, and no boot claim. See the
    [admission result](test-results/2026-08-04-generation-10-live-admission-offline.md).
    The instrumentation does not locate the post-transfer gap, so this
    admission remains diagnostic-only. Commit `a9c012c` and exact-head GitHub
    Actions run `30870594823` are green.
18. **Complete (preflight passed; transition failed):** the first
    connected-preflight transition began from exact
    Alpine fallback. Fallback health and authenticated `RESTART2("bootloader")`
    passed, but the anchored USB port did not re-enumerate during the fixed
    45-second window or an additional 30-second read-only check. No boot or
    payload action occurred. Exact fastboot appeared later on the same
    connection, and the fresh Generation-10 connected preflight then passed
    the deployment-key chain, artifacts, installed host state, rollback
    prerequisites, isolated USB profile, and one `lahaina` device without
    booting. See the
    [transition result](test-results/2026-08-04-generation-10-connected-preflight-transition-live.md)
    and
    [connected-preflight result](test-results/2026-08-04-generation-10-connected-preflight-live.md).
19. **Complete:** the connected-preflight result was reviewed and published at
    `f4b9e1c`; exact-head GitHub Actions run `30872608193` passed. The sole
    Generation-10 lifecycle then emitted `REQUEST_ACCEPTED`, transferred all
    signed-bundle bytes, and lost ACM before any later progress or `PREPARED`
    response reached the host. The exact device-side boundary remains unknown.
    No COMMIT intent or target execution occurred. Exact fallback and host
    cleanup passed; the permanent boot claim is retained, policy admission is
    removed, and inventory is consumed. See the
    [live result](test-results/2026-08-04-generation-10-request-accepted-transport-gap-live.md).
20. **Complete:** the independent receive-only NCM progress path now spans
    the device responder, exact production namespace, privileged broker and
    firewall controller, irreversible root-to-user collector, and private
    post-COMMIT lifecycle assessment. Every wire truncation, torn record,
    absent/stalled collector, identity/order mismatch, and fabricated authority
    remains partial, unavailable, or rejected; a complete trace still creates
    no COMMIT claim. Focused suites and the complete local Linux `ci` and
    provisioned `quick` tiers pass. See the
    [contract](docs/recovery-ncm-progress.md) and
    [offline result](test-results/2026-08-04-generation-11-ncm-progress-host-integration-offline.md).
    Generation 11 was then clean-built twice, issued twice, pinned through an
    immutable offline profile, and selected by the one-shot controller through
    a separate live-capable profile without changing central boot policy. See
    the [offline transition](test-results/2026-08-04-generation-11-live-profile-offline.md).
21. **Complete:** focused and complete local CI, Claude Opus review, and
    independent Codex review pass for the Generation-11 live-profile
    transition. Commit `2a483ec` passed exact-head GitHub Actions run
    `30908649494`.
22. **Complete live preflight:** central policy admits exactly one Generation-11
    receive-only NCM-progress lifecycle after connected preflight. The
    admitted-policy and hostile-fixture gates pass; independent spec and
    standards reviews, complete local CI, commit `8e22bc5`, and exact-head
    GitHub Actions run `30916646825` are green. Exact key and connected
    preflight then passed after an anchored Alpine-to-fastboot transition. At
    that preflight checkpoint the artifact remained unbooted with
    `authority=none`, and no boot claim existed.
    See the
    [admission result](test-results/2026-08-04-generation-11-live-admission-offline.md)
    and [connected result](test-results/2026-08-04-generation-11-connected-preflight-live.md).
23. **Complete:** independent spec and standards review, complete local CI,
    commit `7b76733`, and exact-head GitHub Actions run `30921019231` publish
    the Generation-11 connected-preflight evidence. At that publication
    checkpoint the artifact remained unbooted and had no boot claim.
24. **Complete and consumed:** the sole Generation-11 RAM-only boot reached
    exact recovery ACM/NCM. The privileged host path then rejected its started
    TCP 8081 collector as not uniquely confined before the bundle-server ready
    marker. Progress remained `PARTIAL/NO_ADMISSION` with zero records; no
    PREPARE, transfer, COMMIT intent, NFS, or target occurred. Exact Alpine
    fallback, strict SSH, host cleanup, and Steam socket restoration passed.
    The policy row is removed and exact-basis readmission rejects. Independent
    spec and standards review plus complete local CI passed. Commit `3cee3f1`
    published the transition, and exact-head GitHub Actions run `30926911113`
    passed recovery-core in 3m59s and QEMU in 35s. See the
    [live result](test-results/2026-08-04-generation-11-progress-listener-confinement-live.md).
25. **Complete:** a production-faithful
    host-only run captured the `SO_BINDTODEVICE` listener as
    `169.254.77.1%interface:8081`. The controller now parses one exact `ss`
    record and requires the scoped endpoint, sole launched `python3` PID/fd
    owner, live process, and empty IPv6 inventory. Thirty-eight controller
    cases cover SteamOS races and hostile lookalikes. Complete local CI and
    installed-host verification pass. Implementation commit `1f3cc66` passed
    exact-head GitHub Actions run `30931511061` (recovery-core 4m02s; QEMU
    37s).
26. **Complete:** deterministic
    Generation-12 twins preserve the exact Generation-11 raw recovery, kernel,
    config, and NCM-capable initramfs while deriving distinct AVB
    `615d7498…d72cf6`. Immutable offline profile
    `headless-diagnostic-generation12-offline-v1` passes both retained local
    trees; direct connected actions and the then-unsupported live profile
    reject before host inspection. The reviewed checkpoint was published at
    commit `52ce322`; exact-head GitHub Actions run `30935842119` passed
    recovery-core in 4m11s and QEMU in 35s. See the [offline
    result](test-results/2026-08-04-generation-12-host-confinement-successor-offline.md).
27. **Complete:** add
    `headless-diagnostic-generation12-live-v1`, make the one-shot controller
    select it, admit exactly one central-policy row, and require an exact
    irreversible Generation-12 `BOOT_CLAIMED` record before `boot` can inspect
    the host. Hardware-free tests cover direct-action bypass, claim reuse and
    filesystem races, policy/header/inventory mutations, and both retained
    twins under offline and live profiles. Commit `328b33c` and exact-head run
    `30942517411` passed; the connected preflight then passed after an anchored
    Alpine-to-fastboot transition and exact Steam TCP-8081 socket restoration.
    This host-only admission checkpoint preceded the sole Generation-12
    lifecycle recorded in step 28. See the [host-only
    admission](test-results/2026-08-04-generation-12-live-admission-offline.md)
    and [connected-preflight
    result](test-results/2026-08-04-generation-12-connected-preflight-live.md).
28. **Complete and consumed:** commit `1ee5508` and exact-head GitHub Actions
    run `30944062957` published the connected-preflight evidence. The sole
    Generation-12 RAM-only lifecycle then transferred the exact 46,163,787-byte
    bundle, accepted correlated PREPARE/COMMIT, and captured 40 lossless target
    frames through stage 70 `nfs-mount-begin`; USB disconnected before stage
    80 `nfs-mount-ok`. The watchdog returned exact Alpine fallback, strict SSH,
    cleanup, Steam socket restoration, and `FALLBACK_RETURNED` intent
    resolution passed. Generation 12 is removed from boot policy, recorded
    consumed, and never reusable. See the [live
    result](test-results/2026-08-04-generation-12-nfs-mount-disconnect-live.md).
29. **Complete:** the outer lifecycle now requires all 18 PREPARE/COMMIT
    fields, recomputes the canonical COMMIT request fingerprint, binds the
    immutable postmortem tuple across both responses, and rejects hostile
    missing/extra/cross-phase mutations. Native and exact claim-gate
    regressions pass. Commits `5ce677e`, `baf57cf`, and `606303a` publish the
    correction; exact-head GitHub Actions run `30952333022` passed QEMU in 35s
    and recovery-core in 11m40s.
30. **In progress, offline candidate complete and production issuance HOLD:**
    the distinct successor
    inserts stage 75 `nfs-mount-returned` between begin and verified success,
    emits one candidate/boot-ID kernel-log lineage marker, and extends private
    evidence with change-only same-port NCM, kernel NFS-RPC, and exact
    `169.254.77.1:2049`-to-target TCP state/queue/current-unrecovered-RTO
    snapshots. The
    historical 67,288-byte reporter was sealed at `dc53932d…a10`. The active
    single-attempt host-port-classifying reporter is `26249252…bafa`. Hostile
    parser, collector,
    lifecycle, and build-contract tests pass. The fallback now captures a
    signed, read-only, 64-record/4-MiB pstore summary before strict health,
    binds it to the expected candidate/target boot ID, separates lineage and
    fatal-token classifications, and cross-checks the fallback boot ID across
    both probes. Sixty-four fallback, 27 collector, and 80 lifecycle tests,
    complete local
    CI, and independent review pass in the [host-only
    checkpoint](test-results/2026-08-05-stage75-postmortem-host-integration-offline.md).
    Implementation commit `eeb157b` is published with green exact-head GitHub
    Actions run `30988099391` (`qemu-system` 37s; `recovery-core` 4m03s). This
    closes the host-only publication gate. The write-side
    `headless-netroot-early-diag-v2` wire identity now binds the corrected
    6,013,458-byte bounded-rendezvous v3 initramfs `94edd625…cffc`, accepted
    Image, corrected DTB, and sealed Arch root. Its canonical candidate record
    is `41c23330…b9cf`, and the exact runtime-manifest body is
    `54f53420…6efc`. The prior authority-free disposable-key wrapper tuple and
    v2 component row are retained as superseded offline evidence only. The
    active candidate has no policy row, production credential, or boot
    authority; central policy remains empty. The preceding candidate
    checkpoint was reviewed and published at
    `9088c8ff70e24c1c71c3b3b806f7161848dd7320` with green exact-head CI. The
    corrected disposable twins and distinct target/observer identities now
    pass a joint [offline retention review](test-results/2026-08-09-retention-cycle-two-identity-review-offline.md)
    with zero policy rows and no new claim records. This remains composition
    evidence, not candidate admission. Only a later fresh authorization may
    bind production credentials or issue one new one-shot generation. Promote
    a normal SSH candidate only after physical evidence locates and the
    implementation fixes the failing boundary. The
    authority-free [v3 rebind proof](test-results/2026-08-09-host-rendezvous-v3-candidate-rebind-offline.md)
    is retained locally with candidate admission still on hold. The shell-free
    Haven-watchdog correction is now source/builder/output-bound into a new
    [execution/observer refreeze](test-results/2026-08-10-haven-retention-observer-refreeze-offline.md).
    Both roles have distinct clean-twin ASUS wrappers and pass the joint
    authority-free verifier; no physical retention result, claim, policy row,
    production signature, or boot authority exists. Admission remains
    **HOLD**.
31. If H2 passes, continue physical keys/indicator, then H3
    power/charging/thermal/suspend and H4 sensors.

Use [active-context.md](docs/active-context.md) as the resume point. Detailed
completed chronology remains in the dated evidence and Git archive.
