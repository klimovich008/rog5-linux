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

Registry correction `bf5f2e31` passed full local CI (470.670 s) and exact-head,
merge, publication and QEMU (33935980881). Acceptance checkpoint `21b2375c`
also passed GitHub run 33937660322. Its local full run failed on two controller
response timeouts; focused replay and all 95 controller tests passed afterward.
The failed full run is not relabeled green.

The executable acceptance contract exists. The latest source-only matrix at
`0daad254` is seven PASS, seven BLOCKED, eleven NOT RUN—not a qualified release.
It does not import the earlier rescue's physical results. The corrected unsigned
headless archive reuses the retained kernel and all 19 modules. Exact-archive
watchdog QEMU cases pass. Real sealed runtime preparation against the retained
read-only Arch image now passes systemd, key-only SSH policy and unit checks.
The reconstructed image is a verified sparse-derived inspection input, not
byte-identical to the pre-sparse original or a new restoration authorization.

**Do not execute the old prepared fallback-only rescue:** it selects unchanged
signed V11, whose watchdog disarms before handover and lacks the early health
predicate. Preserve its unused twins and claim. A narrow RAM-embedded signed
bundle branch is now implemented in the shared loader and passes focused
normal/sealed-BusyBox tests. It avoids selector/mount/trial writes and retains
geometry, all-storage RO, signature, Haven and single-execute checks.
The corrected target is now signed and exact sealed ARM verification passes.
The RAM wrapper twins are byte-identical (`dd96e3aa…`), built without a kernel
recompile. Its canonical registry row is `headless-acceptance-rescue-v1`;
packaging/registry inclusion grants no execution. It was subsequently consumed
for one RAM-only trial: UFS/root handover passed, but the expected pinned SSH
identity did not appear within 300 seconds. **Never retry this candidate.**

Recovery correction `0afbc63e` passed full local CI (478.334 s) and GitHub
33940190642 exact-head/merge/publication/QEMU. The current host capture and
RAM-family closure changes require their own frozen checkpoint checks.
`rog5-dev capture-rescue` now establishes the diagnostic address, firewall and
listener before boot, verifies a live readiness response, and preserves the
last stage through disconnect. A real 2.699 s host rehearsal cleaned up all
owned changes; a disposable veth test proved the ARP/direct-route receive path.
These are host tests, not a phone or final-release H01 PASS.

Capture/closure checkpoint `eef710f7` passed full local CI (485.693 s) and
GitHub 33942832456 (exact-head, merge, publication, QEMU). Its RAM-only trial
reached `switch-root PASS` and an SSH listener. The listener continued offering
a different key; strict verification was never bypassed. No authenticated
health/charging result exists. The target remained enumerated beyond the
900-second target watchdog interval: this does not distinguish readiness-based
disarm from watchdog failure. The full 1380.783-second capture completed and
owned route/firewall/profile/address cleanup passed. The phone remained in the
target gadget mode, without pinned SSH. Physical fastboot re-entry is requested;
do not issue another execution against this consumed record.

Independent offline regressions now expose valid Ed25519 key comments rejected
by fixed 399/92-byte metadata checks, and slow health clients starving other
requests. Source fixes pass focused tests; the key fix also passes exact sealed
BusyBox plus retained Arch ARM ssh-keygen. Neither is deployed. The retained
Arch hostname is `alarm`, so key-length rejection is **not proven** to explain
the live mismatch. Do not issue a blind key-only successor: obtain the exact
post-handover P2/state/identity failure through the next scoped diagnostic path.
Display remains optional; no kernel defect is established.

Follow-up source checkpoint `0daad254` passed the active tier (11.087 s),
offline acceptance dispatch (19.122 s, correctly BLOCKED overall), and one full
local CI (479.828 s). GitHub 33944557168 exact-head, merge, publication and QEMU
all passed. Do not rerun unchanged full local CI.

The next source-only diagnostic now observes P2, service-state, SSH identity
and early SSH through the existing prestarted NCM receiver after handover.
It reports service properties and bounded helper failure text, not key contents.
Journal absence/error is explicit and never proof of no failure. Kernel-transport
journal queries are required because the helpers log through `/dev/kmsg`.
Its lifetime uses the unchanged target rollback budget; no core service depends
on it, and it neither changes acceptance nor forces reboot. Focused producer,
receiver and archive-composition tests pass; exact sealed ARM replay also passes.
This diagnostic is not deployed or issued. Physical fastboot re-entry remains
necessary because pinned SSH is unavailable. Complete its frozen checks and
exact assembled runtime verification before preparing a successor.

Observer checkpoint `42c729d8` passed full local CI (479.663 s) and all GitHub
33945569616 jobs. All seven watchdog/handover cases passed against its unsigned
archive; all 19 modules are unchanged. Exact archive/retained-Arch preparation
then exposed a host checker omission: its synthetic environment lacked the
observer lifetime variable. The checker now supplies an explicitly labeled
unit-generation fixture, checks observer bytes and verifies its generated unit.
Two fail-first regressions pass; exact ARM/root replay passes (31.786 s), using
unchanged archive bytes. This does not verify deployed timeout binding or
complete A01. Read-only host loop mounts were cleaned up. No successor is signed
or issued, and no further phone boot has occurred.

Host composition fix `df871166` passed all GitHub 33946155200 jobs. The next
acceptance-driven source fix addresses WPA restart preparation: repeated
ExecStartPre previously failed on its existing directory. Exact unchanged
runtime credentials can now be reused, with real owner/mode/link/content checks;
changed secrets and partial state are refused without overwrite. Only the same
interface link-up is reasserted, not hardware activation. Real-file and sealed
BusyBox regressions pass. Full F02 remains BLOCKED on the actual systemd
WPA/DHCP/address/SSH restart transaction; this source fix is not deployed.
