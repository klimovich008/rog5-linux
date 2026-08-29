# Current ROG Phone 5 Linux state

Updated: 2026-08-30

This file contains current facts only. Historical generations and incident
detail are retained in Git and dated `test-results/` records. The complete
pre-compaction state is available at commit `47676f2`.

## Objective

Turn the exact ASUS ROG Phone 5 into a reliable standalone Arch Linux server
with persistent storage, continuous safe charging, networking, key-only SSH,
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

Persistent release v9 is accepted; v8 remains the exact p24 rollback.

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
- V9 adds the live-proven V49 high-speed UFS core. Two persistent boots,
  clean reboot/relock, systemd, NCM, SSH, storage and power checks passed.
- Primary evidence:
  `test-results/2026-08-30-persistent-slotb-v9-pass.md`.

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
- The latest V9 repeat boot showed battery `Full`/`Good`, 8.674 V, 30.0 C,
  side USB online, +181 mA input, and 35.2 C maximum thermal.

## NCM liveness result

Boot `bf9aa234-327f-4b50-acaa-40e98a94c421` completed 7,200 one-second target
samples and 670 ten-second host checks.

- Final target uptime: 7,831.20 seconds.
- UDC: continuously `configured`, high speed.
- DWC runtime: continuously active.
- Host and target RX/TX errors: zero.
- Ping and strict pinned SSH: every check passed.
- Host kernel: no NETDEV watchdog, TX timeout, xHCI, or anchored-USB error in
  the monitored interval.
- Target log SHA-256:
  `32f60ad2bf99e2ecad540f69601d1c444358779c1341e6731c2fd1480c2acb15`.
- Host log SHA-256:
  `d8d24e3b3881f459de62d96283a0b7919c1105ff19d20c0dbb49da5b89cec8d6`.
- Evidence: `test-results/2026-08-29-persistent-ncm-two-hour-pass.md`.

One earlier long-lived boot produced a host `cdc_ncm` NETDEV watchdog after
about 47 minutes. The two-hour pass disproves a deterministic timeout at that
boundary but does not prove the earlier root cause. Preserve the observer for
first-failure capture; do not change kernel or DT without new discriminating
evidence.

## Immediate next gate

V9 p24 deployment and repeated standalone boot pass. Its six sparse chunks
completed in 70.561 seconds; both boots selected the signed V9 bundle, emitted
the V49 high-speed marker once, reported zero UFS errors, loaded stable SSH,
mounted p23 state, and preserved exact write scope and power safety.

Tailscale 1.102.3 is checksum-verified and staged on noexec p23. Same-boot
testing proves the fixed helper, tmpfs executables, TUN, routed `10.77.0.2/30`,
and daemon startup. V10 signed twins add only automatic helper/service startup;
the p24 host image and sparse allocated-byte proof pass offline. Require
exact-head CI before one p24-only transfer. See
`test-results/2026-08-30-persistent-tailscale-v10-offline.md`.

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
- Last pushed commit: `e9d4409db1a55acd7b302eccca40ca39656bbdd0`.
- Standing GitHub authorization covers normal commits and pushes to the active
  branch; never force-push.
