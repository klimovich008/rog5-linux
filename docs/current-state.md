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
- Active selector-v2: persistent-overlay V8 primary with signed V11 automatic
  fallback. Slot A and V11 must remain available.

## Persistent Linux baseline

- Current candidate: `persistent-native-root-wifi-overlay-v8`, manifest
  `3d4d2bfc5cfc54c44ff434503b5fbd8e6aced4f3f94c482b41d3d158cdf03133`.
- Current boot: `ec8f1d5c-cea0-4f05-965c-8ff36d25f81c`, kernel
  `7.1.4-g1eea8970e87f`.
- Systemd is `running` with zero failed units. Native Wi-Fi, NCM, Tailscale,
  strict key-only SSH, persistent service state and D-Bus are active.
- Stable Ed25519 host fingerprint:
  `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
- V8 health is committed and both 600/900-second rollback timers are inactive.
- Pacman keyring initialization and WKD sync succeeded and persisted across
  reboot. The earlier empty-keyring failure is resolved without a parser hack.

## Persistent root storage

- P24 (`arch_root_a`) remains the immutable native Arch lower and signed bundle
  store, mounted read-only with `norecovery`.
- P23 remains the only physical Linux write scope. It contains:
  - `rog5/state/server-state-v1.ext4` for SSH/Tailscale/secrets;
  - `rog5/root/root-overlay-v1.ext4`, exact size 16 GiB, UUID
    `f4834541-6e7a-4214-80d5-818fcc5cc252`, label `ROG5_ROOT_RW_V1`.
- The p23 parent mount remains `noexec`; the bounded overlay loop is
  `exec,nodev,nosuid`, with root/upper mode `0755` and work mode `0700`.
- Normal service exposes exactly `sda` and `sda23` writable across 117 UFS
  nodes. P24 and protected firmware/identity/calibration/modem partitions stay
  read-only.
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
- Native Wi-Fi has carrier, DHCP/default route and strict SSH; Tailscale keeps
  `100.68.169.83`.
- Historical long-run evidence remains in
  `test-results/2026-08-29-persistent-ncm-two-hour-pass.md`,
  `test-results/2026-08-30-persistent-tailscale-v11-live.md`, and
  `test-results/2026-09-02-persistent-wifi-v3-soak.md`.

## Remaining critical issue

Recovery's selector-v2 p23 admission is intermittently unavailable before the
trial helper runs. It safely chooses V11 and creates no target trial record; a
bounded pre-COMMIT retry then selects the accepted primary. Post-COMMIT behavior
remains one-use. Do not promote to direct selector-v1 until an automatic rescue
design is retained; an experimental direct selector was archived and V11 was
restored before V8 admission.

Next make this recovery boundary observable/reliable, then run a longer V8 soak
and bounded package update before deploying the server workload.

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
