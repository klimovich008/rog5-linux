# Active ROG Phone 5 Linux context

Updated: 2026-09-02

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
accepted V8 facts. Historical generations remain in Git and dated
`test-results/` records.

## One current question

Can the slot-B recovery eliminate its intermittent pre-COMMIT p23 admission
fallback while preserving the accepted persistent-overlay V8 primary and exact
V11 fallback?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B contains canonical recovery `f2a73030…` and selector-v2 primary
  `persistent-native-root-wifi-overlay-v8`, manifest `3d4d2bfc…`, with signed
  V11 as automatic fallback.
- Current boot: V8 `5cec9d09-2491-4ca7-a72e-3c276727667b`, kernel
  `7.1.4-g1eea8970e87f`; systemd, native Wi-Fi, NCM, Tailscale and strict SSH
  are active with zero failed units.
- V8 uses p24 read-only as the Arch lower and the exact 16 GiB
  `rog5/root/root-overlay-v1.ext4` image on p23 as persistent OverlayFS state.
  P23 remains `noexec`; the bounded loop filesystem is `exec,nodev,nosuid`.
- Exactly `sda` and `sda23` are writable; p24 and every protected UFS node are
  read-only. Battery is Full/Good and side-port USB power is online.
- Pacman keyring initialization and WKD sync succeeded and survived reboot.
- The signed full package update passed with 163 packages and zero pending
  updates. Python, Git and tmux are installed; a 60-sample post-update soak
  passed. The exact result is
  `test-results/2026-09-02-persistent-overlay-v8-package-update.md`.
- The package hook exposed and now tests an `already-healthy` rerun bug. The
  corrected health script is live in `/run` and source-fixed; it enters the
  signed bundle only on a future target rebuild. Future kernels also require
  Landlock so pacman can remove its filesystem-sandbox compatibility exception.

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

1. Make recovery's pre-COMMIT p23 trial-state admission observable and reliable;
   do not weaken post-COMMIT one-use behavior.
2. Validate the updated userspace and persistent overlay across that clean
   reboot.
3. Deploy the first server workload after the reboot checkpoint.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24 read-only scope, V11 and slot-A rescue, and non-retry after ambiguous target
execution. Do not flash, alter slot A, modify GPT, or resume GPU/display/audio
work during this milestone. The frozen power-key status-screen checkpoint stays
deferred until the server MVP is stable.
