# ROG5 current state

Updated: 2026-09-05. This is the single current-state entry point.
Facts below are accepted evidence, not a claim of freshly measured live health.

## Objective and checkpoint

The standalone Arch server migration passed. Repository/development-loop
consolidation passed local and published exact-head/merge CI at `a2e3efb4`.
The active goal is continued standalone-server reliability and validation of
the next display build; first restore fresh transport/health evidence.
See [transport checks](../test-results/2026-09-04-server-resume-transport.md) and
[boot-code review/fix](../test-results/2026-09-04-native-boot-review.md).
The physical button trial is waiting for a usable connection.
V15 preparation stopped before signing, claim consumption or execution.
There is no authorized storage mutation in this checkpoint.

## Accepted architecture

- Exact phone: ASUS ROG Phone 5 ZS673KS, product `lahaina`, serial
  `M5AIKN00F0353YH`, anchored side USB path `1-1.2`.
- Slot A: matched official ASUS WW33 `33.0210.0210.200`, rescue/charging.
  Charging restoration is complete; see [repair runbook](asus-charging-recovery.md).
- Installed slot B: recovery `340f6392…` with bounded pre-COMMIT preparation
  retries (not a proven bound on subsequent target boot failures). The superseded
  `f2a73030…` image is retained as a host restore artifact, not installed state.
- Selector v2: `persistent-native-root-wifi-overlay-v10` primary
  (manifest `6c271cfa…e3e8f5`), signed `persistent-native-root-v11` fallback.
  Abbreviated hashes here are navigation aids, never verification inputs.
- Accepted server kernel: `7.1.4-g1eea8970e87f`. Last recorded accepted boot:
  `d746db04-06f2-4f1e-af3a-015439de7746`.
- P24 `arch_root_a`: immutable Arch lower/bundle store, read-only `norecovery`.
  P23: bounded 16 GiB root OverlayFS image plus separate service-state image.
  Exactly `sda,sda23` writable across 117 UFS nodes; protected nodes stay RO.
- P23 omits ext4 `orphan_file` for ASUS 5.4 replay compatibility.
  Normal parent mount is `noexec`; overlay loop is `exec,nodev,nosuid`.
- Side-port sink charging, NCM, native Wi-Fi, systemd, key-only early SSH,
  Tailscale and sandboxed `rog5-healthd` passed; normal boot needs no host NFS.
- Pinned SSH host fingerprint:
  `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
  Host alias remains `169.254.77.2` even for the normal `10.77.0.2` address.
  Credentials and complete deployment records remain private.

## Evidence and practical limits

- [Installed reboot/start](../test-results/2026-09-03-unattended-reboot-v10.md):
  101.273 s ordinary reboot; 96.697 s powered-off start under connected power.
  These are two recorded timings, not a boot-time distribution.
- [Persistent overlay](../test-results/2026-09-02-persistent-root-overlay-v8-live.md)
  and [update/reboot fixes](../test-results/2026-09-02-persistent-overlay-update-reboot-debug.md).
- [Package update](../test-results/2026-09-02-persistent-overlay-v8-package-update.md):
  163-package signed update, persistent keyring. Live baseline lacks Landlock;
  only pacman's filesystem sandbox is disabled. Future builds require Landlock.
- [Health service](../test-results/2026-09-02-healthd-persistent-live.md),
  [Wi-Fi soak](../test-results/2026-09-02-persistent-wifi-v3-soak.md),
  [NCM soak](../test-results/2026-08-29-persistent-ncm-two-hour-pass.md),
  [Tailscale](../test-results/2026-08-30-persistent-tailscale-v11-live.md).
- A PMIC IRQ storm once caused transient UFS errors/emergency RO. Subsequent
  20/20 block reads and 2,700-second soak passed; root cause remains unproven.
- [Display V14](../test-results/2026-09-03-display-power-button-v14.md) proved
  rendering and power-key input setup. Physical toggle remains unobserved.
  Display V11–V14 are consumed; never retry them. Headless V10 is the baseline.
- On September 4 the anchored USB descriptor still identified persistent Linux,
  but pinned SSH at `10.77.0.2` returned “No route to host”. Fresh server health
  remains unverified. Host logs show repeated NCM transmit-queue watchdog
  timeouts, unchanged RX counters and rising TX errors. Reactivating only the
  existing phone network profile did not recover SSH; the last Wi-Fi address
  was also unreachable. This does not establish a target crash or its cause.
  A fresh reconnect then failed USB enumeration (`-110`/`-71`). After exact
  fastboot identity/slot-B and safe voltage (7671 mV, SOC gate yes) were verified,
  one ordinary reboot at 22:52:42 local produced alternating recovery/target
  descriptors. Target windows lasted about 22 seconds, without SSH or stages.
  Descriptor identity cannot distinguish primary V10 from signed fallback V11.
  Live recovery attempts are paused for the requested code-first investigation.
- Offline review reproduced accepted-primary non-demotion and crash-recovery
  validation defects. It also found software UFS clock-gating still enabled
  despite the keep-active containment. None proves today's first failure.
  Source-only fixes now accept independent systemd update markers and re-arm
  accepted primary boots before selection. Helper v2 passes offline tests;
  the installed v1 helper is unchanged. Neither fix is deployed. UFS, workdir
  and journal behavior remain unchanged and under investigation.
- The follow-up source checkpoint guards late rollback timer activation with
  exact current-boot acceptance, bounds idle health connections, and repairs
  probe-tier coverage. The runtime and rollback unit are refreshed together
  in fresh persistent compositions; identity-only successors still preserve
  their qualified runtime. These corrections are offline-tested, not deployed.
- The pending loader correction now selects the verified signed fallback when
  primary copy/verification fails; fallback verification, unmount and storage
  relock failures remain fatal. No trial write window is opened for a broken
  primary. This is source-only, not installed recovery behavior.
- Exact target BusyBox plus the accepted kernel passed a diskless ARM64 QEMU
  handover test using the corrected production watchdog. It now survives root
  deletion and requires current-boot P2 readiness at its unchanged deadline.
  Missing/stale acknowledgment resets via the retained static helper; helper
  failure reaches SysRq. Failed init remains a separate panic path. Seven QEMU
  cases pass; this source-only correction is not deployed or physical reset proof.
- September 5 passive early-stage capture reached sequence 25 `switch-root
  PASS` before USB disconnected 7.66 s later. This narrows the observed failure
  to handover or later startup, not the earlier storage/overlay gates. The
  record precedes exec and does not prove systemd started. Primary versus
  fallback remains unidentified. Early stages require the distinct
  `169.254.77.1:8079` host endpoint; the normal shared `10.77.0.1` profile alone
  neither supplied that address nor allowed that port. Temporary host capture
  changes were cleaned up; raw records remain private. No boot was issued.
- Latest exact fastboot read: slot B, 7701 mV, `battery-soc-ok=yes`; serial,
  product and anchored path matched. This is not a current/temperature or
  sustained-charging measurement. No reboot or phone-storage access followed.
- The retained V10 archive requires at least 8.4 V before radio activation;
  its radio failure service explicitly requests reboot. Its failure reporter
  uses ACM, but V10 configures NCM only. This is a strong post-handoff reboot
  hypothesis, not proof of the live voltage or failure reason. Do not lower
  the radio gate; prioritize bounded failure capture and qualified headless
  charging/recovery before another display/radio trial.

## Working authority and next action

Routine repository edits, tests, local packaging, normal commits/pushes and
scoped diagnostics already have standing authorization. Existing authorization
is not revoked by a historical checklist; do not ask repeatedly.

Preserve exact device/product/topology/slot and boot-chain checks; safe battery
and temperature; signed artifact verification; storage scope and backups;
slot-A rescue and V11 fallback; permanent non-retry after COMMIT or ambiguous
execution. No experimental flash, GPT change or protected-data write belongs
to this consolidation. Destructive storage requires a separately reviewed
exact operation and explicit approval. Never publish private material.

Read [development workflow](development.md) for commands and validation tiers.
Read only relevant R1–R10 entries in [lessons](development-lessons.md) during
routine edits; use its complete pre-build/live checklists before a successor.
Source fallback checkpoint `87eea4ae` passed full local CI in 476.297 s and
was pushed; physical deployment is unchanged. Prioritize the now-observed
switch-root boundary before changing unrelated subsystems. Obtain stable exact
fastboot for a reviewed RAM-only diagnostic when required, and fresh transport/
health evidence before the attended screen test.
Watchdog source checkpoint `5c406e19` passed full local CI in 473.624 s;
its exact-head, merge and QEMU publication checks passed. It still needs an
exact paired init/attestation deployment.
The next recovery preparation adds an exact-selector fallback-only option to
the shared loader: no primary copy/execute or p23 trial writes. The historical
rescue image expects obsolete V6 selector bytes and must not be reused.
Fresh composition, publication, admission and live power/identity gates remain
required. Crash-recovery validation, WPA restartability and display isolation
remain open; no kernel change explains the current loss yet.
Rescue checkpoint `c005ddff` preserves the exact-selector fallback-only change;
its frozen tree passed full CI in 470.865 s. Fresh twin rescue archives/images
were verified offline, but remain unissued and unbooted. The following source
checkpoint pairs current init with current parameterized attestation in the
Wi-Fi composer and renders the diagnostic radio timeout. Focused composition
and active checks pass. Checkpoint `8cb0f65f` passed full local CI in 491.913 s
and exact-head, merge, candidate-publication and QEMU checks in run 33933475707.
The next data-only registration binds `headless-selector-rescue-v1` to the
verified private twins and current selector. All 17 generic claim tests pass;
consumer statements and every historical record are unchanged. No actual
claim has been created/consumed. The pinned V11 SSH host identity and matching
deployment key are located. Exact-head run 33934354059 failed because the
historical admission verifier omitted the canonical fallback-only claim family.
The focused correction imports that family from the same fixed registry;
30 admission and 17 consumer tests pass, including two fail-first regressions.
Connected preflight refused before consumption; slot B, 7702 mV and SOC yes
were observed. No boot or host networking change occurred.

Do not execute the prepared rescue yet: exact V11 archive review found no early
battery-health predicate and its old init disarms the watchdog before
switch_root. The source watchdog correction is not in that signed fallback.
The 1320-second collector is only an observation lifetime, not proof of
continuous target rollback; it also stops on the first disconnect and lacks
an admission check for remaining lifetime. It has not been started.
Next: finish the registry CI checkpoint, then compose a coherent headless
rescue with paired watchdog/attestation and early power gates using the retained
kernel. Preserve the existing signed V11 and stock slot-A rescue unchanged.
Any new composition needs fresh exact validation/admission; no consumed retry
or experimental flash. Do not rebuild the already verified rescue twins.
The [roadmap](../ROADMAP.md) holds later work.
