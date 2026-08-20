# Active ROG Phone 5 Linux context

Updated: 2026-08-20

This file contains only the current handoff. Historical cycles remain in Git
history, `test-results/`, and `docs/archive-index.md`.

## Device baseline

- Device: ASUS ROG Phone 5 ZS673KS (`lahaina`)
- Serial: `M5AIKN00F0353YH`
- Active slot: A
- Bootloader: unlocked
- Rescue OS: official ASUS WW33 / Android 13
- Build: `33.0210.0210.200`
- Known-good rescue functions: Android boot, stock recovery, powered-off
  charging, RNDIS/ADB

Slot A is the permanent charging and recovery route. Future Linux work uses
RAM-only `fastboot boot` until a persistent design explicitly preserves it.

## Completed charging repair

The August charging loop is resolved. Reconstructed dynamic-partition metadata
incorrectly marked the one physical, unsuffixed `super` device as
slot-suffixed. Android first-stage init therefore waited for nonexistent
`super_b`, `/vendor` never mounted, charger services did not start, and the
phone returned to fastboot.

The corrected explicit-A/B `super` image was flashed once and verified. It
contains explicit `*_a` and factory-empty `*_b` logical partitions backed by
physical `super`. The official WW33 AVB chain passes, stock charger mode raised
the battery from about 3% to 47%, and Android booted with
`sys.boot_completed=1`.

Authoritative private evidence:

- `/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/SUCCESS-EVIDENCE.md`
- `/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/BUILD-RECORD.md`
- `/home/deck/.local/state/rog5-super-explicit-ab-20260819-r1/corrected-super-live.log`

Do not rebuild or reflash `super`, attempt a WW18 rollback, or write GPT,
`persist`, `factory`, `batinfo`, modem/EFS, calibration, RPMB/devinfo, or
per-unit key material.

## Current objective

Build a reliable standalone Arch Linux server while preserving slot A.
Immediate work is Linux power over the side data port:

1. keep side controller `a600000` in peripheral mode for NCM/ACM data;
2. reproduce side-port sink charging while NCM/SSH remains active;
3. bring up ADSP, PMIC GLINK, `qcom_battmgr`, and UCSI;
4. expose aggregate and dual-cell battery telemetry;
5. prove net-positive charging and safe temperature under sustained load;
6. keep NCM, key-only SSH, and rollback stable throughout;
7. return to persistent local-root Arch only after this foundation passes.

## Current physical evidence

Stock WW33 establishes the physical UCSI mapping:

- `port1`: with only the PC cable attached, connected as UFP/sink/device while
  RNDIS/ADB uses `a600000.dwc3`; this is the side data/charging port.
- `port0`: disconnected in that side-only state and connected only when the
  bottom cable is attached; this is the bottom port.

With only the side PC connection, Android reports UFP/sink/device, charging,
5 V / 500 mA input, `side usb status: 1`, and `asus charger: 0`. The immediate
Linux gate is the same side-only combination; bottom-port arbitration is
deferred.

Android names the controller `a600000.dwc3`; the proven Linux 7.1 UDC is
`a600000.usb`. Do not rename the Linux contract based only on Android's name.

## Current implementation

Authoritative clean repository:

- path: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`
- branch: `agent/linux-recovery-host`
- starting published head: `ac7689f3e8307f024b229cb10809e7f4f972eafd`

The separate workspace at
`/home/deck/Projects/rog-phone-linux-migration/repo` preserves unfinished
VCNL36866 work and must not be cleaned, stashed, or overwritten implicitly.

The power/USB successor is `headless-power-usb-observer-v3`. It reuses the
proven Linux 7.1 Image and PMIC-GLINK/UCSI DTB, embeds the reviewed probe source
directly in the normal network-root initramfs, reports every UCSI port and
aggregate USB voltage/current limit, and revalidates the exact side UDC,
gadget binding, address, route, and carrier after UCSI starts.

The first cycle intentionally performs no charge-control or role-control
writes. Kernel and firmware observations decide the next patch. Its complete
disposable-key twin build passed with manifest
`872fe9feb04c9da3a69b605e36927218c8bd9c2c80e7bcc03dcb9e00af920381`
and wrapper AVB
`fe4f2c5581dfb56d452d1cfd0780ade6c0b109f0635733ff7e80d55b2a88a726`.

## Next execution sequence

1. Run coherent repository CI for the completed disposable-key twin build.
2. Commit and publish the checkpoint.
3. Admit the disposable-key twin wrapper and matching bundle for one RAM-only
   cycle; its private key is destroyed after construction.
4. Verify serial, USB topology, slot A, battery, candidate, and one-use claim.
5. Temporarily boot once with only the side port connected.
6. Reach systemd and key-only SSH, then run the power/USB probe.
7. Record UCSI port1, power role, USB limits, battery current/temperature,
   NCM continuity, and rollback result.
8. Patch only the earliest demonstrated failure.

## Boundaries

- Never reuse a consumed or ambiguous candidate.
- Never flash an experimental kernel or recovery image.
- Keep slot A and the official WW33 charging route intact.
- Stop on identity/topology mismatch, unsafe temperature/power, unexpected
  phone-storage writes, or loss of the rescue route.
- Keep private keys, firmware, phone dumps, and live evidence outside Git.
