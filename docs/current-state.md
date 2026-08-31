# Current ROG Phone 5 Linux state

Updated: 2026-09-01

This file contains current facts only. Historical generations and incident
detail are retained in Git and dated `test-results/` records. The complete
pre-compaction state is available at commit `47676f2`.

## Objective

Turn the exact ASUS ROG Phone 5 into a reliable standalone Arch Linux server
with persistent storage, continuous safe charging, independent Wi-Fi networking, key-only SSH,
unattended reboot, and a proven rescue route. GPU, desktop, display, audio,
sensors, and automation remain deferred.

## Exact device and rescue

- Model: ASUS ROG Phone 5 ZS673KS (`lahaina`).
- Fastboot serial: `M5AIKN00F0353YH`.
- Anchored side-port host USB path: `1-1.2`.
- Bootloader: unlocked.
- Slot A: official ASUS WW33 / Android 13 rescue and charging environment,
  build `33.0210.0210.200`.
- Slot B: persistent signed Linux recovery/loader.
- Slot A must remain the independently verified rescue route.

## Persistent Linux baseline

Persistent release v11 boots successfully; V10, V9 and V8 remain p24 rollbacks.

- The slot-B loader verifies a signed bundle from read-only `arch_root_a` and
  kexecs Linux `7.1.4-g359318de534f`.
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
- Primary evidence:
  `test-results/2026-08-30-persistent-tailscale-v11-live.md`.

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
- The latest V11 boots showed battery `Full`/`Good`, 100%, 8.659 V, 29.9 C,
  side USB online and +272 mA input in the first V11 sample.

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

V11's six p24 sparse chunks completed in 72.816 seconds. Two boots, including
a normal unattended systemd reboot, selected the signed V11 bundle, preserved
the SSH/Tailscale identities, and passed power, UFS and exact write-scope checks.
The installed conntrack-mark config and standalone shutdown helper are proven.
Slot A and the stable slot-B loader were not changed.

V21 passed native-root/Wi-Fi startup with USB data removed before the root mount.
The cutoff bound was5.615–5.786s of target uptime, before mount entry11.432s.
USB stayed off84.504s through authenticated endpoint discovery and strict WLAN
SSH proof. V19's prior180s isolation/reassociation/64MiB runtime pass remains
valid. Preserve the qualified target artifacts; all trials through V21 are
consumed. V20's host namespace defect is fixed and retained as a regression.
V11`cec1225b-e998-4d97-8728-c56faddbee5c` is restored with state/Tailscale;
normal recovery took64.532s. Battery is Full/Good,8.593V/30.2°C.
Charger-only physical startup, longer power proof and permanent healthy-startup
policy remain before changing the persistent selector. Wi-Fi is not yet the
default. V19's sampled battery current averaged−22mA; net-positive charging
has not been established. See `test-results/2026-08-31-wifi-early-cut.md`.
The private network configuration persists only in the existing p23 state image.
See `test-results/2026-08-31-wifi-usb-isolation.md`.
The clean kernel/module/initramfs twins, baseline DT and readback evidence are
retained; see `test-results/2026-08-31-rpmh-readback-development.md`.
The WCN6851/hw1.1 backport and exact-keyed ASUS board data now pass the RAM test.
The deployed V11 baseline still requires USB carrier. Early software data
isolation passed for the RAM target; actual charger-only power-on is untested.
Its two rollback timers remain qualification-only, not permanent service policy.
An early SPMI SID5 probe warning is shared with V18, not a new Wi-Fi failure.
The installed loader cannot export its pstore snapshot before kexec; crash
capture remains incomplete. Missing evidence never proves no crash.
Preserve USB rescue. Tailscale UDP discovery identified the verified WLAN
address while USB data was off; it can locate the next target without guessing
DHCP. Managed Tailscale SSH still needs its account check; no gate was bypassed.
Keep the existing
observer for longer loaded-network tests; prior two-hour evidence is a baseline,
not a V11 soak result.

Rollback-safe selector-v2 and healthy-commit support now pass offline full CI;
they are not deployed. V11 remains selected. See
`test-results/2026-09-01-persistent-wifi-rollback-offline.md`.

The preexisting empty runtime package keyring causes a background refresh parser
failure. Initial zero-failed-unit checks do not cover that later failure. Fix
package-keyring initialization separately; do not mask it or redesign the kernel.

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
