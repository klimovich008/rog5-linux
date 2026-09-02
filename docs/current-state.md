# Current ROG Phone 5 Linux state

Updated: 2026-09-02

This file contains current facts only. Historical generations and incidents are
retained in Git and dated `test-results/` records.

## Objective

Turn the exact ASUS ROG Phone 5 into a reliable standalone Arch Linux server
with persistent storage, continuous safe charging, independent Wi-Fi, key-only
SSH, unattended reboot, and a proven rescue route. Desktop/GPU/audio/sensors
remain deferred; the optional power-key text status screen is frozen.

## Exact device and rescue

- Model: ASUS ROG Phone 5 ZS673KS (`lahaina`).
- Fastboot serial: `M5AIKN00F0353YH`.
- Anchored side-port host USB path: `1-1.2`.
- Bootloader: unlocked.
- Slot A: official ASUS WW33 / Android 13 rescue and charging environment,
  build `33.0210.0210.200`.
- Slot B: canonical signed-bundle recovery `f2a73030…`.
- Active selector-v2: persistent-overlay V10 primary with signed V11 automatic
  fallback. Slot A and V11 must remain available.

## Persistent Linux baseline

- Current live primary: V10 boot `389acb49-2cc0-46da-9997-e67e548a77ee`,
  kernel `7.1.4-g1eea8970e87f`, bundle
  `persistent-native-root-wifi-overlay-v10`, manifest `6c271cfa…e3e8f5`.
  Systemd, native Wi-Fi, NCM, Tailscale, strict key-only SSH and persistent
  service state are healthy.
- V10 first boot `2b9c86b0…` passed with one exact allowed overlay journal
  replay; later V10 boots, including one through the installed `boot_b`
  recovery, pass with clean `0/0` journal evidence. They keep the exact
  163-package inventory `032f6e00…47de1a` and write scope limited to
  `sda,sda23`.
- Slot B now contains bounded-retry recovery `340f6392…`; the prior canonical
  recovery `f2a73030…` remains an exact host restore artifact. Slot A is
  unchanged.
- Stable Ed25519 host fingerprint:
  `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
- V8 health is committed and both 600/900-second rollback timers are inactive.
- Pacman keyring initialization and WKD sync succeeded and persisted across
  reboot. The earlier empty-keyring failure is resolved without a parser hack.
- A signed full update now passes: 163 packages, inventory SHA-256
  `032f6e00…47de1a`, systemd 261.2, OpenSSH 10.5p1, Python 3.14.7, Git 2.55.0
  and tmux 3.7c. See
  `test-results/2026-09-02-persistent-overlay-v8-package-update.md`.
- The first persistent workload, sandboxed `rog5-healthd`, is enabled and
  survived installed-`boot_b` recovery. Its fixed `/healthz` response passes
  over NCM and native Wi-Fi with no credentials or writable service state. See
  `test-results/2026-09-02-healthd-persistent-live.md`.
- The live kernel lacks Landlock, so pacman temporarily disables only its
  filesystem sandbox while retaining the `alpm` user and seccomp sandbox.
  Future persistent-root builds now require `CONFIG_SECURITY_LANDLOCK=y`.
- The repaired package overlay is intact on p23. V9 fixed systemd root mode and
  OpenSSH 10.5 casing; V10 accepts systemd 261's canonical 255-byte
  `systemd-update-done` markers on hardware and across repeat execution. Evidence:
  `test-results/2026-09-02-persistent-overlay-update-reboot-debug.md`.

## Persistent root storage

- P24 (`arch_root_a`) remains the immutable native Arch lower and signed bundle
  store, mounted read-only with `norecovery`.
- P23 remains the only physical Linux write scope. It contains:
  - `rog5/state/server-state-v1.ext4` for SSH/Tailscale/secrets;
  - `rog5/root/root-overlay-v1.ext4`, exact size 16 GiB, UUID
    `f4834541-6e7a-4214-80d5-818fcc5cc252`, label `ROG5_ROOT_RW_V1`.
- The p23 parent mount remains `noexec`; the bounded overlay loop is
  `exec,nodev,nosuid`. Systemd hardens the upper root to `0555` after updates;
  policy also accepts staged `0755`. Work remains `0700`.
- Normal service exposes exactly `sda` and `sda23` writable across 117 UFS
  nodes. P24 and protected firmware/identity/calibration/modem partitions stay
  read-only.
- P23 no longer uses ext4 `orphan_file`. That optional feature left
  `orphan_present` after V10 shutdowns, which ASUS 5.4 could not replay. A
  frozen sparse project backup, restored verification tree, pre/post metadata
  snapshots, mandatory fsck and complete 16-file post-change manifest passed.
- One later PMIC IRQ 118 storm caused transient UFS reads to fail and remounted
  p23/overlay `emergency_ro`. V11 read-only recovery proved p23 clean, repaired
  only the overlay journal, and read the failing physical block consistently in
  20/20 direct probes. A 2,700-second guarded V10 soak reached uptime 3,002.80
  with zero IRQ, UFS or emergency-RO events; no unproven kernel patch was made.
- V8 accepted one exact `EXT4-fs (loopN): recovery complete` for the sealed
  overlay loop and still rejected all other recovery/error shapes. Its first
  pass recorded `journal_recovery_events=1` and
  `allowed_overlay_recovery_events=1`; the current boot records `0/0`.
- Evidence: `test-results/2026-09-02-persistent-root-overlay-v8-live.md`.

## Power and networking

- PMIC GLINK, qcom-battmgr, UCSI, Type-C sink/device mode and NCM pass.
- Side-port USB provides data plus 5 V input while Linux runs.
- Current battery evidence is Full/Good, approximately 8.56 V and 29.9 C,
  with USB online and safe thermal readings.
- Accepted V10 native Wi-Fi has proven carrier, DHCP/default route and strict
  SSH while NCM and Tailscale remain available.
- Historical long-run evidence remains in
  `test-results/2026-08-29-persistent-ncm-two-hour-pass.md`,
  `test-results/2026-08-30-persistent-tailscale-v11-live.md`, and
  `test-results/2026-09-02-persistent-wifi-v3-soak.md`.

## Remaining critical issue

The recovery-selection blocker and first persistent workload checkpoint are
resolved. The next server phase is a credential-isolated automation runtime and
operator-selected workload; GPU, desktop, display, audio and sensor expansion
remain deferred.

## Frozen screen checkpoint

Display V10 proved REFGEN, DSI, DRM, fb0, backlight and status files. The
power-key-toggled text screen remains frozen; do not resume display/GPU work
until the server MVP is stable. See
`test-results/2026-09-01-display60-v10-pre-switch-pass.md`.

## Required boundaries

- Match exact serial, product, topology, slot and signed artifact identity.
- Keep battery/thermal gates, exact write scope, V11 fallback and slot-A rescue.
- Never retry an ambiguous or post-COMMIT target execution.
- Do not expose private keys, credentials, firmware or private evidence.
- Do not rebuild or reflash `super`, alter slot A, modify GPT, or resume unrelated
  subsystem work at this checkpoint.

## Repository state

- Branch: `agent/linux-recovery-host`.
- Resolve publication with `git rev-parse HEAD` and exact-head CI; no embedded
  SHA is release authority.
- Standing GitHub authorization permits normal commits/pushes; never force-push.
