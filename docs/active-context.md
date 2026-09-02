# Active ROG Phone 5 Linux context

Updated: 2026-09-02

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
accepted V9 facts. Historical generations remain in Git and dated
`test-results/` records.

## One current question

Why did one healthy V10 selector cycle choose V11, and can the existing
recovery expose and eliminate that transient decision failure before the first
unattended server workload?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B contains bounded-retry recovery `340f6392…` and selector-v2 primary
  `persistent-native-root-wifi-overlay-v10`, manifest `6c271cfa…`, with signed
  V11 as automatic fallback. Exact old recovery `f2a73030…` remains restorable.
- Current boot: accepted V10 `43c91566-b125-4da9-a933-af8f3601ea2a` with
  systemd, native Wi-Fi, NCM, Tailscale, strict SSH and persistent service
  state.
- V10 uses p24 read-only as the Arch lower and the exact 16 GiB
  `rog5/root/root-overlay-v1.ext4` image on p23 as persistent OverlayFS state.
  P23 remains `noexec`; the bounded loop filesystem is `exec,nodev,nosuid`.
- Exactly `sda` and `sda23` are writable; p24 and every protected UFS node are
  read-only. Battery is Full/Good and side-port USB power is online.
- Pacman keyring initialization and WKD sync succeeded and survived reboot.
- The signed full package update passed with 163 packages and zero pending
  updates. Python, Git and tmux are installed in V8's persistent overlay; a
  60-sample hot post-update soak passed. The exact result is
  `test-results/2026-09-02-persistent-overlay-v8-package-update.md`.
- Reboot debugging proved two additional source-only issues: systemd 261's
  intentional root mode `0555` and OpenSSH 10.5's mixed-case `sshd -T` names.
  The overlay is repaired; fail-first regressions and source fixes pass. See
  `test-results/2026-09-02-persistent-overlay-update-reboot-debug.md`.
- V10 first boot passed with the 163-package overlay, one exact allowed journal
  replay and a healthy trial. A later clean V10 boot passed `runtime`,
  `switch-root`, systemd, Wi-Fi, Tailscale, strict SSH, storage and power with
  `0/0` journal evidence.
- One intervening recovery cycle selected healthy V11. Selector bytes, trial
  bytes and the exact AArch64 decision helper independently select V10, and the
  following cycle selected V10. S65 decision detail is currently not observable
  in the installed recovery because it is overwritten before the 250 ms
  reporter can emit it. Source now retains S65 for 300 ms; focused recovery and
  active-tier tests plus one full local CI pass, but those bytes are not
  installed.

## Newly proven milestone

V8 booted with one exact owned-overlay journal replay, reported
`journal_recovery_events=1` and `allowed_overlay_recovery_events=1`, committed
healthy, and disarmed both rollback timers. A later clean boot reported zero
recovery events and the same healthy services. See
`test-results/2026-09-02-persistent-root-overlay-v8-live.md`.

The earlier V1–V6 failures are now regression fixtures: stale tmpfs-only
attestation, duplicate writable-UFS guards, non-executable/0700 upper, retained
empty `/persist`, and global rejection of the owned overlay's successful ext4
journal replay.

## Next actions

1. Build the CI-approved S65 observability correction from cached wrapper
   inputs and validate it RAM-only before any persistent update.
2. Reproduce or clear the transient V11 selection with exact S65 evidence.
3. Require consecutive V10 boots before claiming unattended reboot reliability.
4. Deploy the first persistent server workload after that recovery checkpoint.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24 read-only scope, V11 and slot-A rescue, and non-retry after ambiguous target
execution. Do not flash, alter slot A, modify GPT, or resume GPU/display/audio
work during this milestone. The frozen power-key status-screen checkpoint stays
deferred until the server MVP is stable.
