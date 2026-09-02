# Active ROG Phone 5 Linux context

Updated: 2026-09-02

Read `docs/current-state.md` for durable device, rescue, storage, charging, and
accepted V10 facts. Historical generations remain in Git and dated
`test-results/` records.

## One current question

Can one physical PMK8350 power-button press toggle the proven minimal status
screen without affecting server, recovery, storage, power or SSH health?
After that bounded proof, the next phase remains the credential-isolated automation runtime.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, side-port host path `1-1.2`.
- Slot A remains the ASUS WW33 rescue/charging route.
- Slot B contains bounded-retry recovery `340f6392…` and selector-v2 primary
  `persistent-native-root-wifi-overlay-v10`, manifest `6c271cfa…`, with signed
  V11 as automatic fallback. Exact old recovery `f2a73030…` remains restorable.
- Current boot: accepted V10 `9a4dce86-229f-4193-a216-aedb06dbd5ff` with
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
- Instrumented recovery classified the intermittent fallback as
  `mount-recovery-orphan-incompat`: p23's modern ext4 `orphan_file` left
  `orphan_present`, which ASUS 5.4 cannot replay. The backed-up, fsck-clean p23
  now omits only that feature. Recovery selected V10 after the change, after an
  old-shutdown stress cycle, and through the installed `boot_b` path.
- Repository source also accepts only an exact attached loop or a proven-gone
  stale loop node during exitrd teardown; wrong or ambiguous backing fails.
- A transient PMIC IRQ 118 storm forced p23 and the overlay `emergency_ro`.
  Fresh V11 recovery found p23 clean, repaired only the overlay journal and
  proved the failing physical block in 20/20 direct reads. A guarded
  2,700-second V10 soak then passed with zero IRQ/UFS/RO trigger; the event was
  not reproducible, so kernel/DT source remains unchanged.
- `rog5-healthd` is the first persistent workload. It is credential-free,
  dynamic-user sandboxed, enabled at boot, and survived installed recovery.
  `/healthz` passes over NCM and Wi-Fi; full V10 acceptance remains green. A
  RAM-only action-aware shutdown also proved powered-off auto-start under
  connected power. Repository exitrd source now preserves that poweroff action.
- Display V9 passed persistent systemd, native Wi-Fi, Tailscale, healthd,
  DRM/fb0/backlight and text status rendering. V10 plus the exact RAM-loaded
  `qcom-pon.ko` created one `pmic_pwrkey` input; the durable loader is committed.
  No physical press occurred before the scheduled rollback.

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

1. Package the exact PON module in one successor and observe one physical
   power-button press/release toggling the screen.
2. Define one unprivileged automation service account with secrets kept only in
   the existing p23 service-state image.
3. Deploy the operator-selected AI/automation workload and validate resource,
   thermal, network and reboot behavior before enabling unattended actions.

## Boundaries

Preserve exact device/topology, safe battery/temperature, signed artifacts,
p24 read-only scope, V11 and slot-A rescue, and non-retry after ambiguous target
execution. Do not flash, alter slot A, modify GPT, or resume GPU/desktop/audio
work during this milestone.
