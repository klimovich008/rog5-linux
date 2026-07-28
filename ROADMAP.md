# Roadmap

## Goal

Make the ASUS ROG Phone 5 a dependable native Linux ARM device with:

- a maintainable Linux 7.x board port;
- accelerated Adreno 660 graphics;
- modern Arch Linux ARM, with Debian support possible from the same kernel;
- minimal Plasma/KWin on the panel and secure remote GUI while the OLED is
  off;
- stable charging, thermal, refresh-rate, suspend, and idle-power behavior;
- Wi-Fi client/AP and a fail-closed VPN-backed hotspot;
- a confined automation service that can use explicitly delegated tools
  without receiving unrestricted personal credentials.

The goal is complete only when normal operation no longer depends on Android,
an interactive recovery shell, or an attended temporary boot. Until a
persistent boot path is separately designed and approved, development remains
temporary-boot-only.

## Project rules

1. Tests and rollback contracts precede hardware execution.
2. No experimental partition flash.
3. One live diagnostic payload gets at most one execute attempt.
4. Transport loss is `UNKNOWN`; it is never permission to retry.
5. Accepted evidence is immutable and inherited by hash.
6. Storage stays read-only until the persistent-root phase explicitly proves
   a bounded write contract.
7. Credentials, personal data, and private evidence remain outside Git.
8. A kernel version bump does not replace subsystem bring-up. Linux 7.1.4 is
   the current upstream base; work advances driver by driver.

## P0 — Repository and safety stabilization

Status: **in progress**

- [x] Push the complete repository to GitHub.
- [x] Create archive tag
  `archive/pre-stable-recovery-2026-07-28`.
- [x] Inventory tracked source and ignored local artifacts.
- [x] Obtain an independent Claude Opus audit and correct it against live
  evidence.
- [x] Separate artifact inventory from temporary-boot authority.
- [x] Admit only the twice-live-accepted v18 staging AVB image.
- [x] Pin fastboot product `lahaina` in the recovery wrapper.
- [x] Remove the unused `socat` host prerequisite and stale execute guidance.
- [x] Add an offline mock test for boot policy and product rejection.
- [x] Split README orientation, current facts, roadmap, recovery design, and
  archive index into distinct sources of truth.
- [x] Add one canonical Linux quick/rootfs offline-test runner.
- [ ] Add GitHub CI for hardware-free tests.
- [ ] Generate a non-destructive ignored-artifact prune plan.
- [ ] Review that plan before deleting or deduplicating local data.
- [ ] Pin/bootstrap external `mkbootimg` and `avbtool.py` dependencies for a
  fresh clone.

Exit: a fresh clone can run the offline policy suite, and no consumed or
unsafe artifact can pass the generic recovery preflight.

## P1 — Recovery protocol test suite

Status: **complete offline; reference, native PTY, and signed-bundle suites
pass**

Specification:
[docs/recovery-control-plane.md](docs/recovery-control-plane.md)

Build the tests before the responder:

- [x] Canonical frame parser reference model.
- [x] Split/coalesced frame tests at every boundary.
- [x] Malformed length, oversize, duplicate/unknown field, NUL, and non-ASCII
  rejection.
- [x] Device-session and request-ID replay model.
- [x] Same-ID/same-body immutable decision rendered with current state, and
  same-ID/different-body conflict.
- [x] Same-ID `PREPARE` retry, new-ID rejection, and one-bundle-per-session
  model.
- [x] Atomic `COMMIT_EXEC` claim and persisted fingerprint model.
- [x] Fault injection before claim, after claim, after response, and after
  simulated execute.
- [x] Session-keyed host write-ahead ledger, crash consistency, immutable
  outcome, symlink/path replacement, and concurrent-controller tests.
- [x] Pseudo-terminal delayed-open, partial-I/O, dropped-reply, disconnect,
  and responder-restart tests.
- [x] Proof that arbitrary shell input never reaches an execution primitive.
- [x] Signed-manifest, file-size/hash, DTB, path, and command-line policy
  mutation tests.

Exit: the model demonstrates at-most-once execute semantics under every
injected host/device crash and transport loss. There is still no phone action
in this phase.

## P2 — Fixed recovery responder and one re-freeze

Status: **protocol core, fixed fetch/serving, trust verifier, and
same-descriptor load are integrated offline; blocked on initramfs
integration**

- [x] Implement an offline-tested static responder whose production default
  owns `/dev/ttyGS0`.
- [ ] Mint the per-boot device session before USB bind and retain it across
  responder restart under `/run`.
- [x] Implement only `HELLO`, `STATUS`, `PREPARE`, and `COMMIT_EXEC`.
- [x] Invoke the fixed production `kexec -e` path with `execve`; never invoke
  a shell.
- [ ] Integrate the production responder, verifier, fixed kexec-tools, and
  public key into the initramfs before USB bind.
- [ ] Remove `sh -i` from recovery, network-root, and persistent-root
  initramfs variants.
- [x] Implement and independently test fixed-NCM-host binary bundle
  acquisition, an unprivileged chroot/seccomp worker, bounded RAM inventory,
  and atomic no-replace publication.
- [x] Invoke the fixed acquisition helper from `PREPARE` under the watchdog
  before the verifier, with permanent bundle-conflict semantics.
- [x] Add the fixed read-only host-serving command and firewall/controller
  integration for the canonical binary stream.
- [x] Implement and test canonical signed manifests against the fixed
  production key path using ephemeral test keys only.
- [x] Copy the exact kernel, DTB, and initramfs into write-sealed snapshots,
  verify those immutable bytes, transfer their descriptors over a private
  `SOCK_SEQPACKET` channel, and load only those descriptors with bounded,
  watchdog-supervised legacy `kexec_load`.
- [x] Persist `PREPARED` only after load success; cover malformed handoff,
  verifier/loader failure, timeout, watchdog death, path replacement, and
  crash-after-load retry on host and AArch64/QEMU.
- [x] Unload any uncommitted image after loader failure/timeout, returned
  execution, or non-prepared responder restart; bound executor kill/reap.
- [ ] Embed a separately approved production public key in the frozen image.
- [ ] Ask the user before creating or using the production signing key.
- [x] Generate a fixed profiled command line; reject arbitrary `init=`,
  `root=`, and unsafe reserved-memory input.
- [ ] Preserve storage isolation and rollback ordering before UDC bind.
- [ ] Build twice and prove byte-identical responder, initramfs, wrapper, and
  AVB outputs.
- [ ] Update all source, hash, and verifier pins in one change.

Live promotion, separately authorized:

- [ ] Two staging-only RAM-root/storage/USB/rollback cycles.
- [ ] Two protocol-only malformed/replay cycles with no payload load.
- [ ] One signed inert load-only cycle.
- [ ] One execute cycle with host write-ahead intent and out-of-band outcome
  classification.

Exit: one stable recovery image replaces v18 in the temporary-boot allowlist.
The legacy ACM helpers become archive-only.

## P3 — Persistent Arch boot

Status: **offline foundation present; live path blocked on P2**

- [x] Build and verify successor-v3 Arch server/Plasma root.
- [x] Preserve metadata and recursively seal the protected root.
- [x] Use key-only SSH and a distinct target host identity.
- [x] Package screen-off-first and power-button policy.
- [x] Build P2 and early-entry diagnostics.
- [x] Record rejected/consumed P2 and entry-v1 attempts.
- [ ] Re-express the persistent-root payload as a signed runtime bundle.
- [ ] Add exact target/fallback/recovery outcome classification.
- [ ] Prove one temporary read-only persistent-root boot.
- [ ] Prove clean automatic fallback with root state unchanged on failure.
- [ ] Prove a bounded A/B root selector and promotion transaction offline.
- [ ] Ask separately before any persistent selector or boot-partition change.

Exit: Arch reaches systemd, SSH, screen-off service, and clean reboot/fallback
without an ambiguous execute result. Persistence changes remain a separate
approval boundary.

## P4 — Adreno 660 acceleration

Status: **incremental bring-up**

The last live-accepted ancestry is v9 GMU resume entry. V10 GMU/linked-CX
runtime-PM is offline-accepted and remains on HOLD; it has not run on the
phone. The v11 clock-preparation candidate is offline/source-only.

- [ ] Port the current GPU boundary into a signed runtime bundle.
- [ ] Prove GPUCC and linked-CX clock/power preparation with balanced rollback.
- [ ] Bring up GMU resources/HFI without widening storage or remote-processor
  scope.
- [ ] Create `/dev/dri/renderD*` with no SMMU fault.
- [ ] Repeat raw render-node open/close 100 times.
- [ ] Run Mesa Turnip information and a minimal command submission.
- [ ] Run KWin Wayland and Chromium with hardware acceleration.
- [ ] Test suspend/resume and repeated screen off/on.
- [ ] Measure memory, idle CPU, thermals, and battery impact.

Exit: accelerated KWin/Chromium survive reboot, repeated open/close, screen
cycles, and a sustained thermal test without fallback corruption.

## P5 — Wi-Fi and fail-closed VPN hotspot

Status: **offline acceptance; hardware HOLD**

- [x] Identify WCN6855 PCIe endpoint/subsystem and ASUS power graph.
- [x] Validate DTB overlays against pinned schemas.
- [x] Produce reproducible kernel/module and root-overlay packages.
- [x] Keep radio auto-probe disabled for the first gate.
- [x] Pass IPv4/IPv6 and real WireGuard fail-closed tests.
- [x] Pass UDP/TCP DNS and interface/endpoint loss tests.
- [ ] Enumerate PCIe/MHI once with no radio activation.
- [ ] Bring up ath11k client mode.
- [ ] Test AP mode and client/AP coexistence.
- [ ] Use a real provider WireGuard tunnel.
- [ ] Prove DHCP and DNS cannot leave by a non-VPN interface.
- [ ] Test VPN loss/recovery, throughput, thermal behavior, and battery drain.

Exit: no IPv4, IPv6, or DNS client traffic can escape when the VPN is absent,
degraded, or restarting, and the hotspot recovers without stale firewall
state.

## P6 — Desktop, screen, refresh rate, and power

Status: **fallback model proven; mainline pending**

- [x] Keep server services alive with DPMS off and backlight zero.
- [x] Run loopback-only ttyd, noVNC, nested KWin/Plasma, and Chromium CDP over
  a reconnecting SSH tunnel.
- [x] Enforce a singleton phone-side remote GUI supervisor.
- [x] Record screen-off memory and short CPU baselines.
- [ ] Install a minimal Plasma/KWin profile on promoted Arch.
- [ ] Use KRDP/Wayland for the normal remote desktop; keep noVNC as fallback.
- [ ] Map the power button to a confined screen toggle with visible state
  indication.
- [ ] Default to 60 Hz, offer 90 Hz balanced, and keep 120/144 Hz opt-in.
- [ ] Measure wall power and battery drain at each refresh rate, screen-off,
  idle desktop, Chromium automation, and sustained server load.
- [ ] Validate charging, thermal throttling, suspend, wake, and 24-hour
  screen-off reachability.

Exit: the phone remains remotely reachable for 24 hours with the panel off,
does not overheat or unexpectedly drain while powered, and provides a stable
local accelerated desktop on demand.

## P7 — Confined automation server

Status: **packaging foundation only**

- [x] Create a separate locked agent account.
- [x] Apply CPU, memory, swap, task, and scheduling limits.
- [x] Give it private writable state and no broad device access.
- [ ] Choose narrow email/document connectors rather than copying an entire
  personal profile into the image.
- [ ] Store credentials in an encrypted, revocable secret service outside
  Git and rootfs artifacts.
- [ ] Add per-tool allowlists and append-only audit logs.
- [ ] Require explicit user confirmation before sending email, submitting a
  job application, modifying cloud data, or purchasing anything.
- [ ] Add a kill switch and resource/network quotas.
- [ ] Compare local models with remote OpenAI/Anthropic/OpenRouter routing
  based on RAM, thermal, privacy, and cost.

Exit: the agent can read only delegated material, cannot silently submit or
send external actions, and can be revoked without rebuilding the phone.

## P8 — Maintainable kernel and upstream path

Status: **Linux 7.1.4 development base exists**

The project will not create a kernel “from scratch.” It will maintain a small,
reviewable SM8350/ASUS board delta on an upstream kernel and reduce that delta
over time.

- [x] Reproduce Linux 7.1.4 ARM64 builds on the PC.
- [x] Maintain reviewed config, DTS, patch, and module artifacts by hash.
- [ ] Pin the complete container/toolchain/source bootstrap.
- [ ] Consolidate diagnostic patch generations into subsystem-sized commits.
- [ ] Add kernel selftests/KUnit where hardware-independent logic permits.
- [ ] Track upstream SM8350, Adreno, WCN6855, UFS, USB, charger, audio, and
  panel changes.
- [ ] Rebase only after the current recovery and subsystem acceptance suites
  pass on both old and new bases.
- [ ] Prepare upstreamable DTS and driver patches without ASUS private
  firmware or Android-only contracts.

Exit: a fresh PC can reproduce the kernel, modules, DTBs, recovery, and rootfs
from pinned public inputs; the remaining device delta is documented and small
enough to review subsystem by subsystem.

## Definition of done

The project goal is achieved when all of these are true:

- native Linux boots through an approved persistent path with rollback;
- Arch or Debian can be reproduced from pinned inputs;
- display, touch, USB, charging, battery, thermal, Wi-Fi, and audio required
  for the chosen server/desktop role are stable;
- Adreno 660 provides a stable render node and accelerated Plasma/Chromium;
- remote GUI remains available with the physical display off;
- the VPN hotspot is fail-closed for IPv4, IPv6, and DNS;
- refresh-rate and screen-off power profiles are measured and selectable;
- the automation service is confined, auditable, and revocable;
- no normal operation depends on the legacy ACM shell or Android userspace.

The immediate task is P1: build the recovery protocol/state/fault test suite.
