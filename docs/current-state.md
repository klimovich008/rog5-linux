# Current ROG Phone 5 Linux state

Updated: 2026-09-01

This file contains current facts only. Historical generations and incident
detail are retained in Git and dated `test-results/` records. The complete
pre-compaction state is available at commit `47676f2`.

## Objective

Turn the exact ASUS ROG Phone 5 into a reliable standalone Arch Linux server
with persistent storage, continuous safe charging, independent Wi-Fi, key-only
SSH, unattended reboot, and a proven rescue route. The current optional UI
scope is one power-key-toggled text status screen; desktop, GPU acceleration,
audio, sensors, and automation remain deferred.

## Exact device and rescue

- Model: ASUS ROG Phone 5 ZS673KS (`lahaina`).
- Fastboot serial: `M5AIKN00F0353YH`.
- Anchored side-port host USB path: `1-1.2`.
- Bootloader: unlocked.
- Slot A: official ASUS WW33 / Android 13 rescue and charging environment,
  build `33.0210.0210.200`.
- Slot B: canonical selector-v2 recovery `f2a73030…`, selecting the signed
  Wi-Fi V3 primary under live soak with signed V11 retained as fallback.
- Slot A must remain the independently verified rescue route.

## Persistent Linux baseline

Persistent Wi-Fi V3 boots successfully; V11, V10, V9 and V8 remain p24
fallback/rollback bundles.

- The slot-B loader verifies signed bundles from read-only `arch_root_a`; the
  active primary runs Linux `7.1.4-g1eea8970e87f`.
- Native Arch root reaches systemd `running`, zero failed units, high-speed NCM
  at `169.254.77.2/30`, and key-only SSH.
- Stable Ed25519 host fingerprint:
  `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
- Persistent service state is stored only through the bounded p23 state image.
- Normal service exposes exactly `/dev/sda` and `/dev/sda23` writable; p24 and
  every other UFS block node remain read-only.
- Marker `23fd76f779d41f79322ff5e6b0fec69816a281e0c3f37524323c23c2b4192f35`
  survives reboot and clean state-service teardown relocks all 117 nodes.
- V9 adds the live-proven V49 high-speed UFS core. Two persistent V9 boots,
  clean reboot/relock, systemd, NCM, SSH, storage and power checks passed.
- V11 adds exact conntrack-mark support and the standalone shutdown helper.
  Enrolled Tailscale has no health warnings and survives normal systemd reboot.
  V11 evidence: `test-results/2026-08-30-persistent-tailscale-v11-live.md`.
- The corrected local pre-stop transaction now quiesces service state before
  RAM kexec. V29 reached the qualified Wi-Fi target, systemd, and
  `switch-root PASS`, then returned to a fresh V11 fallback.
- Wi-Fi V2 passed functional boot but reset when its separate 600-second probe
  timer survived health. Wi-Fi V3 disarms both rollback timers and passed two
  clean boots; its multi-hour soak is in progress. See
  `test-results/2026-09-02-persistent-wifi-v2-live.md`.

## Storage state

- The GPT has 117 visible disk/partition nodes under the proven mainline path.
- P23 is the bounded persistent state container and is the only intended Linux
  service-state write scope.
- P24 (`arch_root_a`) contains the verified native Arch root and signed bundle
  store; it remains read-only during normal service.
- Protected bootloader, firmware, modem/EFS-equivalent, calibration, persist,
  identity, security, GPT-backup, and slot-A rescue data are preserved.
- No further GPT or filesystem transaction is currently needed for the MVP.

## Power and USB

- PMIC GLINK, qcom-battmgr, UCSI, Type-C sink/device mode, NCM, and the required
  module closure pass on the current kernel.
- Side-port USB provides data plus 5 V input while Linux is running.
- Accepted tests showed net-positive charging, safe battery temperature, and
  safe thermal-zone values.
- V29 reported battery `Full`/`Good`, 100%, 8.573 V, 29.9 C, side USB online,
  and a 500 mA input-current limit while native Arch and Wi-Fi were running.
- Wi-Fi V3 repeats those safety properties while serving SSH over both NCM
  and native Wi-Fi; its repeat boot reported 30.0 C battery and safe maximum
  thermal-zone temperature.

## NCM liveness result

Boot `bf9aa234-327f-4b50-acaa-40e98a94c421` completed 7,200 target samples
and 670 host checks: configured/high-speed USB, active DWC, zero RX/TX errors,
all ping/strict-SSH checks passing, no host USB/xHCI/NETDEV failure. Final uptime
was 7,831.20s. Exact logs/hashes are retained in
`test-results/2026-08-29-persistent-ncm-two-hour-pass.md`.

One earlier long-lived boot produced a host `cdc_ncm` NETDEV watchdog after
about 47 minutes. The two-hour pass disproves a deterministic timeout at that
boundary but does not prove the earlier root cause. Preserve the observer for
first-failure capture; do not change kernel or DT without new discriminating
evidence.

## Immediate next gate

The active primary is `persistent-native-root-wifi-v3`, manifest `3848a474…`,
selector `47fe38b7…`. Boots `f57790ad-90e1-4917-b89f-27e7e918a2ad` and
`e4424825-a7b0-4d33-8a4f-fcad3f9e479b` both committed the same healthy trial,
disarmed both rollback timers, kept p24 read-only and exposed only
`sda`/`sda23` writable. GitHub run `33568444295` is fully green.

Next prove multi-hour Wi-Fi/Tailscale/charging liveness and unattended rescue,
then proceed to server service deployment. The frozen minimal screen checkpoint
already proved REFGEN, DSI, DRM, fb0, backlight and status files in Display V10;
do not merge it or resume broader display/GPU work until the server MVP is
stable. See `test-results/2026-09-01-display60-v10-pre-switch-pass.md`.

The preexisting runtime package-keyring WKD parser failure is unrelated to
Wi-Fi, charging, or display and remains a separate userspace repair.

## Required boundaries

- Match exact serial, product, topology, slot, and signed artifact identity.
- Keep battery and thermal gates, exact write scope, fallback, and integrity
  checks.
- Never retry consumed or ambiguous target execution.
- Do not expose private keys, credentials, firmware, or private evidence.
- Do not rebuild or reflash `super`; do not modify slot A for Linux work.
- Stop on identity ambiguity, unsafe power/temperature, unexpected storage
  writes, transport ambiguity during a write, or loss of rescue.

## Repository state

- Branch: `agent/linux-recovery-host`.
- Resolve the current publication with `git rev-parse HEAD` and the exact-head
  GitHub check; do not use an embedded last-pushed SHA as release authority.
- Standing GitHub authorization covers normal commits and pushes to the active
  branch; never force-push.
