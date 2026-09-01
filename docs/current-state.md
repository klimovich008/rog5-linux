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
- The corrected local pre-stop transaction now quiesces service state before
  RAM kexec. V29 reached the qualified Wi-Fi target, systemd, and
  `switch-root PASS`, then returned to a fresh V11 fallback.
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
- V29 reported battery `Full`/`Good`, 100%, 8.573 V, 29.9 C, side USB online,
  and a 500 mA input-current limit while native Arch and Wi-Fi were running.

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

V29 proved the repaired source-to-target lifecycle and the current native Wi-Fi
stack. Source exitrd emitted `native-kexec enter`; target boot
`54a5e437-9a04-402a-b14e-01dbcb8a3b5d` reached `switch-root PASS`; systemd was
running; `wlp1s0` had carrier and DHCP; radio, WPA, and DHCP units were active;
and fallback boot `f70ba888-af07-492c-920d-75fef09313b5` restored V11. V29 is
consumed and must never be retried. See
`test-results/2026-09-01-native-wifi-v29.md`.

The optional initial screen userspace now has one compact path: the existing
power-button toggle plus a `tty1` renderer for time, Wi-Fi interface/IP, and
battery/charging status. It sleeps for 30 seconds while off and refreshes once
per second while visible. It deliberately exposes no SSID or MAC and starts no
desktop or GPU process.

Physical pixels remain a separate live gate. The offline display baseline now
builds Linux `7.1.4-rog5-display60-v1` with a minimal AMS678 ER2 DSC panel
driver, fail-closed Pixelworks Iris6 analog-bypass transaction, and one 60 Hz
mode. Its exact DT delta enables only the required display blocks, L12/L13
rails, panel GPIOs, and DSI0 graph. Focused driver, binding, DT, and status
userspace tests pass. The first RAM-only display candidate entered that kernel,
passed UFS/read-only storage, then failed optional status installation at the
initramfs `runtime` stage before switch-root. The sealed BusyBox binary contains
an `install` applet but exposes no `/bin/install` link; the injected runtime also
targeted `/usr/local` instead of `/newroot/usr/local`. The consumed candidate
returned to exact fastboot and a normal reboot restored fresh V11. This is R3,
not panel evidence. See `test-results/2026-09-01-display-60hz-offline.md` and
`test-results/2026-09-01-display60-runtime-r3.md`.

Display60 V2 fixed the initramfs runtime boundary and reached `switch-root PASS`,
then returned before target SSH. Display60 V3 removed Wi-Fi startup and reached
SSH, proving the post-switch reboot was not a display crash. It found no fb0 or
backlight: DSI PHY `vdds` and DSI host `vdda` used dummy regulators, REFGEN was
unavailable, DSI stayed deferred, and the PLL could not lock. V1-V3 are consumed.
V4 proved `vdda`/`vdds` wiring, but module timing left REFGEN unavailable. A
no-reboot V11 probe proved the driver/DT creates `refgen`; V5 builds this DSI
dependency in. See `test-results/2026-09-01-display60-refgen-timing.md`.

Higher refresh rates, Pixelworks PQ, desktop, and GPU work remain out of scope.

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
