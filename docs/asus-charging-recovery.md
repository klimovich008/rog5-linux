# ROG Phone 5 low-battery recovery hold

Use this runbook when the bootloader reports `battery-soc-ok: no`. Keep every
storage candidate unbooted and every one-use claim unconsumed until the gate
passes.

## Proven limits

Neither installed slot is an accepted charging environment:

- Slot B boots the Alpine fallback. Its ASUS/Qualcomm charging stack is
  incomplete, and external power has allowed pack voltage to fall while it
  runs.
- A 2026-08-16 attempt to enter the preserved slot-A recovery transitioned
  the exact phone from fastboot to `05c6:900e` Qualcomm crashdump, with the
  display waiting for a full RAM dump. It did not enter recovery or prove
  charging. That slot-A recovery path must not be repeated.

The retained AVB metadata explains why slot A is not a coherent recovery
chain: `boot_a` reports `18.0840.2103.26-0`, while `vendor_boot_a` reports
`18.1220.2202.206-0`. The two slot-A components are from different ASUS
releases. This mismatch is evidence against using the installed slot, not a
reason to flash either component while the battery is low.

The presence of the backed-up ASUS `boot_a` image does not prove that the
installed slot-A companion firmware and recovery chain are complete or
charging-capable. `off-mode-charge: 1` and `charger-screen-enabled: 1` also do
not prove that the current installed operating systems can charge the pack.

## Recover crashdump to fastboot

If the phone displays the full-RAM-dump wait screen:

1. Hold Volume Down + Power for at least 8 seconds; use 12 seconds if needed.
2. Immediately hold Volume Up + Power.
3. At vibration, release Power but keep holding Volume Up until fastboot is
   visible.
4. Do not select Recovery.

After exact serial, product, and USB-topology verification, restore only the
verified fallback slot B as the active-slot metadata. Keep the phone in
fastboot; do not boot Alpine merely to inspect the battery.

## Battery gate

Read only the bootloader telemetry from the exact device:

```sh
fastboot devices -l
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar serialno
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar product
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-voltage
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-soc-ok
```

Refuse Stage 1 unless `battery-soc-ok` is exactly `yes` and voltage has risen
substantially from the recorded low value. A flat or falling voltage remains a
refusal even if external power is attached. Do not leave the phone in Alpine
or fastboot under the assumption that either state will charge it.

## 2026-08-16 bounded charging evidence

The phone uses the side USB-C port for the anchored PC data connection and the
bottom USB-C port for the ASUS wall charger during these measurements. Two
distinct RAM-only ASUS-derived 5.4.210 recovery images preserved slot B and
returned directly to exact fastboot without accessing phone storage:

- `charging-rescue-fastboot-v1-live-v1` is consumed and never reusable. Its
  30-second window moved the bootloader reading from 6.801 V to 6.933 V, which
  then remained near 6.933 V.
- `charging-rescue-fastboot-v2-live-v1` is consumed and never reusable. Its
  five-minute window moved the reading from 6.934 V to 6.931 V.

The first step is too large to represent stored charge over that interval and
the longer cycle did not show a rising trend. A later fastboot soak fell from
6.931 V to 6.925 V over 30 minutes. These voltage-only cycles do not prove
net-positive charging or current direction.

`charging-telemetry-v1-live-v1` is now consumed and never reusable. Its
90-second output-only cycle returned to exact fastboot after 35 complete ACM
frames. Every
frame reported `PSY_COUNT value=0`: the side Type-C controller reached
`Attached.SNK`, but no battery or USB power-supply service registered. The
exact kernel has `QTI_BATTERY_CHARGER` and `QTI_PMIC_GLINK` built in, so adding
modules is not the fix. The downstream source requires the
`PMIC_RTR_ADSP_APPS` RPMsg channel and `msm/adsp/charger_pd` service.

One hybrid ASUS charger experiment followed. Version 1 was canceled before
claim entry when offline review found no charger-class trigger or rollback.
Version 2 paired the exact slot-B 5.4.134 kernel and matching installed
vendor-boot with the preserved ASUS recovery ramdisk, added a charger-only
class and 15-minute bootloader rollback, and was consumed once. It disconnected
USB and returned to exact fastboot about eight seconds later without ADB,
power-supply evidence, or Qualcomm crashdump. It is not a charging route and
must not be retried.

With the side PC cable and bottom ASUS wall charger attached together, voltage
remained flat or falling. Before another phone boot, physically disconnect the
side cable so its low-current VBUS cannot win input selection, leave only the
bottom wall charger for at least 15 minutes, reconnect the side cable, and read
the exact fastboot voltage and `battery-soc-ok`. The host hub's class power bit
did not remove physical VBUS and cannot substitute for unplugging the cable.
See the redacted
[live charging-rescue result](../test-results/2026-08-16-low-battery-charging-rescue-live.md).

No currently installed low-battery charging route is proven. If physical
side-port isolation also fails, identify an exact late-Android-11 slot-B ASUS
charger/recovery ramdisk or build a complete RAM-only environment that starts
the ADSP charger protection domain. Do not discover charging behavior by
flashing at low voltage.

Do not flash `boot_a`, `boot_b`, `vendor_boot`, `misc`, or any other partition
to solve charging. Do not erase, format, repartition, or consume a temporary-
boot claim while the battery gate is closed.

## Return to Stage 1

The current private Stage-1 execution record binds the verified fallback slot
B. Once an independently proven charging method has restored the battery,
re-enter fastboot and verify that exact slot plus every original precondition:

```sh
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-voltage
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-soc-ok
```

Then revalidate device and USB identity, repository head, candidate size and
hash, private execution record, backup manifests, unconsumed claim, and all
Stage-1 geometry. A slot selection never substitutes for those checks.

## Long-term boundary

Retain the verified Alpine recovery route until native Linux charging or an
independent charging/recovery route is physically accepted. Native charging
requires the complete SM8350/ASUS path: PMIC GLINK charger service, battery
telemetry, USB Type-C/PD role and input-current negotiation, thermal
protection, dual-cell handling, and verified shutdown charging. Read-only
telemetry alone is insufficient. Charging-control writes remain disabled
until voltage, current direction, temperature, and dual-cell behavior pass
hardware validation.
