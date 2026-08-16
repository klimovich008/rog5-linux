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
the longer cycle did not show a rising trend. These voltage-only cycles do not
prove net-positive charging or current direction. Do not run another blind
charging boot. The active discriminator is a zero-boot fastboot soak with
read-only voltage and `battery-soc-ok` samples at increasing intervals. If it
remains flat, the next phone transition must provide read-only in-kernel
charger, battery-current, temperature, dual-cell, USB-input, and PMIC-GLINK
telemetry; an output-only 90-second image is prepared but remains unissued.
See the redacted
[live charging-rescue result](../test-results/2026-08-16-low-battery-charging-rescue-live.md).

No currently installed low-battery charging route is proven. Before another
phone transition, identify an already-reviewed RAM-only vendor charging
environment that has measured net-positive current and retains fallback, or
use a hardware/service charging method independent of the installed slots.
Do not discover charging behavior by flashing at low voltage.

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
