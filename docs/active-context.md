# Active ROG Phone 5 Linux context

Updated: 2026-08-21

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
- starting published head: `9a86c94bf2357f8128ef42301f19283e226d82a3`

The separate workspace at
`/home/deck/Projects/rog-phone-linux-migration/repo` preserves unfinished
VCNL36866 work and must not be cleaned, stashed, or overwritten implicitly.

The active power/USB identity is defined only by
`configs/recovery-candidates/power-usb-active.json`; generated identities are
recorded in `manifests/power-usb-active.lock.json`. V7 is consumed after
passing NFS, systemd, the corrected 29-zone acceptance, key-only SSH, watchdog
fallback, and exact stock slot-A return. It exposed an R1 target selector that
recognized only three historical charging candidates, so no charging probe
ran. V8 generated the target identity but was revoked unbooted when review
showed its early PID1 probe had no SSH observation channel. V9 deferred the
probe; retained pstore later proved its rebuilt initramfs omitted the private
ADSP firmware source and failed `prepare_shutdown_root`. V10 was aborted before
COMMIT after exposing that evidence. V11 embeds the exact hash-pinned WW33
firmware and passed SSH, but the probe refused inherited runtime-mask/disarmed-
watchdog preconditions before hardware. V12 composed those preconditions but
exposed obsolete reserved-memory paths before ADSP. V13 bound the accepted
geometry but had two noncanonical channel-size strings. V14 corrected them,
then found systemd had already coldplugged `qcom_q6v5_pas`. V15 masked whole
services before switch-root and prevented systemd readiness. V16 used a narrow
volatile pre-switch modprobe blacklist and reached the hardware probe, where
PAS returned `-EINVAL`; the deployed full-UCSI DTB had regressed by omitting
the three stock-owned RAM exclusions previously required for successful ADSP
startup. V17 restored those nodes and reached runtime acceptance, but its
reused initramfs still selected V16 exactly, skipped deferred charging mode,
and omitted the retained probe. V18 replaced that identity copy, reached ADSP
`running`, and then found `pdr_interface.ko` had incompatible build-specific
BTF. V19 passed PDR/PMIC GLINK/UCSI and found `port_type` is source-validly
optional. V20 classified that absence, then was revoked unbooted before phone
contact. V21 is consumed after its diagnostic-profile token was rejected
before target USB. V22 reached target NCM/ACM, then its first transport check
used unsupported BusyBox `find -printf` and rolled back. Exact stock fallback
passed. V23 reached target NCM/ACM, then its textual mountinfo guard
misclassified required `/dev/pts` as phone storage. V24 is the target-only
successor. See
`test-results/2026-08-20-power-usb-v7-r1-target-selector.md`.

## Current loop optimization

- The observer runs before NFS/systemd/SSH and reports optional telemetry
  non-fatally over typed ACM netstrings.
- Its real module closure is 16 files rather than the 844 MB module tree.
- Twin offline initramfs builds match at
  `64c0e4be67f39817c7d86c31ee4d07fd0c9e7a076a971fd3fb8b1b9934c1b2d3`.
- `test-repository-linux.sh probe` takes about 5.6 seconds.
- The ASUS wrapper path checks a recovery-only content-addressed cache before
  compiling; target bundles and documentation do not invalidate it.
- Persistent stock-Android ADB is no longer a project objective. Linux cycles
  use fastboot, ACM/NCM, and later key-only SSH.

## Next execution sequence

V24's sole acceptance test is stable side-port NCM/ACM plus complete typed
battery/UCSI evidence and net-positive current at a safe temperature.

1. Record V23 as consumed with R2 classification.
2. Pass every mandatory pre-build item in `docs/development-lessons.md`.
3. Generate one V24 early-probe bundle from a clean-twin initramfs and reuse
   the stable recovery wrapper cache; do not rebuild an unchanged kernel.
4. Verify serial, USB topology, slot A, battery, candidate, and one-use claim.
5. Temporarily boot V24 once with only the side port connected.
6. Run the observer immediately after NCM carrier, before NFS/systemd/SSH.
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
