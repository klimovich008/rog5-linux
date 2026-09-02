# Active ROG Phone 5 Linux context

Updated: 2026-09-02

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
accepted V9 facts. Historical generations remain in Git and dated
`test-results/` records.

## One current question

Can initramfs-only V10 accept canonical systemd 261 update-done markers and
repeat-boot the 163-package persistent overlay while retaining exact V11
fallback?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B contains bounded-retry recovery `340f6392…` and selector-v2 primary
  `persistent-native-root-wifi-overlay-v9`, manifest `3f353b9b…`, with signed
  V11 as automatic fallback. Exact old recovery `f2a73030…` remains restorable.
- Current boot: healthy V11 `5fbe39c4-1024-4514-8078-26c7b85a3faa` with NCM,
  Tailscale, strict SSH and persistent service state. V9's p23 overlay is not
  mounted by V11.
- V9 uses p24 read-only as the Arch lower and the exact 16 GiB
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
- V9 first boot passed with the 163-package overlay and healthy trial. Repeat
  reached `runtime` and exposed systemd's canonical timestamped update markers;
  V10 parser fixtures now pass.

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

1. Run full local/exact-head CI for the update-marker parser.
2. Build/sign/stage V10 with unchanged V9 kernel/DTB, then require first and
   repeat boots with 163 packages, P2/systemd/Wi-Fi/SSH and exact write scope.
3. Deploy the first server workload after the V10 repeat-boot checkpoint.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24 read-only scope, V11 and slot-A rescue, and non-retry after ambiguous target
execution. Do not flash, alter slot A, modify GPT, or resume GPU/display/audio
work during this milestone. The frozen power-key status-screen checkpoint stays
deferred until the server MVP is stable.
