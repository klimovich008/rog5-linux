# ROG5 current state

Updated: 2026-09-05. This is the single current-state entry point.
Facts below are accepted evidence, not a claim of freshly measured live health.

## Objective and checkpoint

The standalone Arch server migration passed. Repository/development-loop
consolidation passed local and published exact-head/merge CI at `a2e3efb4`.
The existing active goal now ends at test-defined qualification of one reliable
standalone headless server release. Display is optional, not a completion gate.
The [release acceptance contract](release-acceptance.md) and
[machine-readable tests](../configs/release-acceptance.json) define mandatory
offline, rescue, server and physical-recovery outcomes. Run `rog5-dev accept`
to produce one current results matrix; missing or mixed-build evidence cannot pass.
See [transport checks](../test-results/2026-09-04-server-resume-transport.md) and
[boot-code review/fix](../test-results/2026-09-04-native-boot-review.md).
The physical button trial is deferred outside headless qualification.
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
Use relevant R1–R10 [lessons](development-lessons.md) during routine edits and
the complete pre-build/live checklists before a successor. Historical checkpoint
details remain in Git and the [acceptance incident](../test-results/2026-09-05-headless-acceptance.md);
the [roadmap](../ROADMAP.md) holds later work.

## Active recovery checkpoint

Registry closure is corrected; all four GitHub jobs passed for `17d7fbb6`
(run 33948165386). See the [acceptance incident](../test-results/2026-09-05-headless-acceptance.md)
for historical fixes and exact test timings. Current acceptance is incomplete:
the latest standalone offline matrix has seven PASS, seven BLOCKED and eleven
NOT RUN. No physical results are merged into that source-only matrix.

**Consumed:** `headless-acceptance-rescue-v1` reached root handover and an SSH
listener, but it offered the wrong host key and failed the 300-second pinned
SSH gate. Strict verification was never bypassed. No authenticated charging
result exists. The target remained enumerated past the watchdog interval; this
does not distinguish readiness-based disarm from watchdog failure. Full capture
and owned host-network cleanup completed. Never retry this candidate.

**Prepared, not executed:** `headless-acceptance-rescue-v2` contains the verified
startup observer and SSH-identity size correction. Its one question is which
post-handover P2/state/identity service prevents pinned SSH acceptance. The
observer is optional, sends bounded service/failure evidence through the existing
prestarted NCM receiver, and changes neither watchdog nor acceptance behavior.
Its output is unauthenticated diagnostics, never an SSH or health PASS.

Signed target and RAM-wrapper twins match; packaging took 28.690 s without
recompiling either kernel. The final wrapper's sealed ARM verifier passed in
3.767 s, including embedded bytes, signature, artifact hashes and target plan:
600-second target, 900-second rollback. The canonical registry binds wrapper
`b0cb5a31…`, recovery archive `13ba0b6f…`, and manifest `a49507e8…`.
Full hashes live in the single repository-owned claim record. Registry inclusion
does not consume a claim or replace connected admission.

Evidence explicitly reused because relevant bytes are unchanged: the unsigned
target archive's seven QEMU watchdog/handover cases; exact retained-Arch runtime
preparation/unit checks (31.786 s); all 19 module identities and load-order
metadata. BTF/symbol/hardware-load proof and final complete A01 remain separate.
The retained root is a verified sparse-derived inspection input, not a new
restoration image. No root/kernel/module rewrite was needed for this packaging.

Full local CI passed in 480.918 s on the frozen registry checkpoint.
Next: complete exact-head publication checks, then
verify fresh fastboot identity/slot/power, establish capture, and admit at most
one v2 RAM-only execution. The last host descriptor still identifies persistent
Linux, not fastboot; pinned SSH is unavailable. Physical fastboot re-entry is
required. Do not interpret cached descriptors or old voltage as current health.
No live claim is created or consumed and no storage/flash operation is planned.

Preserve the old unused fallback-only rescue as evidence, but do not execute it:
its unchanged signed V11 watchdog predates the corrected handover predicate.
The installed stock-A rescue and signed V11 fallback remain untouched. Wi-Fi
restart preparation and healthy late-SSH timer guards are source-tested, not
deployed; C02/F02 await exact target restart qualification. Display stays optional.
