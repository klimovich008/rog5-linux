# ASUS low-battery charging recovery

Use this runbook when the bootloader reports `battery-soc-ok: no`. The
dedicated-layout Stage-1 candidate must remain unbooted and its one-use claim
must remain unconsumed until this runbook completes.

## Why slot B cannot be the charging environment

Slot B boots the persistent Alpine fallback. That fallback is a useful Linux
recovery system, but it does not have an accepted ASUS/Qualcomm charging
stack. External power can therefore wake the phone into Alpine, where the
phone consumes more power than the PC data connection supplies. Enabling
`off-mode-charge` or the charger screen does not correct the missing Linux
charger path.

The short-term recovery is to preserve slot A as the ASUS charging-capable
environment. Do not use Alpine, mainline Linux, or repeated fastboot waiting
as a low-battery charger.

## Enter the ASUS charging environment

1. Keep every storage candidate and claim untouched. Record the current
   voltage, `battery-soc-ok`, and active slot.
2. Require one exact fastboot device at the retained physical USB location,
   the private expected serial, and product `lahaina`. Refuse an ambiguous
   inventory.
3. Verify from the private backup manifest that slot A still has the preserved
   ASUS `boot_a` recovery image and matching companion firmware. Do not infer
   this from the slot letter alone.
4. Confirm slot A is bootable, then change only active-slot metadata:

   ```sh
   fastboot -s "$ROG5_FASTBOOT_SERIAL" set_active a
   fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
   fastboot -s "$ROG5_FASTBOOT_SERIAL" reboot recovery
   ```

5. Verify that fastboot and the Alpine USB identity remain absent. USB
   disappearance is consistent with ASUS recovery or powered-off charging;
   it is not by itself proof that charging succeeded.
6. Leave the phone on a known-good ASUS-compatible wall charger. Do not attach
   the low-current PC data cable while recovering a deeply discharged pack.

Do not flash `boot_a`, `boot_b`, `vendor_boot`, `misc`, or any other
partition to solve charging. Do not erase, format, repartition, or consume a
temporary-boot claim in this procedure.

## Return to Stage 1

After charging, re-enter fastboot and repeat exact identity and topology
checks before trusting telemetry:

```sh
fastboot devices
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar serialno
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar product
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-voltage
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-soc-ok
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
```

Refuse Stage 1 unless `battery-soc-ok` is exactly `yes` and voltage has risen
substantially from the recorded low-battery value. The project does not invent
a numeric voltage threshold: the bootloader gate is mandatory, and a flat or
falling voltage remains a refusal.

The current private Stage-1 execution record binds slot B. Once the battery
gate passes, restore and verify that exact slot before any claim consumption:

```sh
fastboot -s "$ROG5_FASTBOOT_SERIAL" set_active b
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
```

Then revalidate the exact device and USB location, repository head, candidate
size and hash, private execution record, backup manifests, unconsumed claim,
and every Stage-1 precondition. A slot change never substitutes for those
checks.

## Long-term boundary

Keep one ASUS charging-capable slot/recovery until native Linux charging is
physically accepted. Linux charging requires the complete SM8350/ASUS path:
PMIC GLINK charger service, battery telemetry, USB Type-C/PD role and input
current negotiation, thermal protection, dual-cell handling, and verified
shutdown charging. Read-only telemetry alone is insufficient. Charging-control
writes remain disabled until voltage, current direction, temperature, and
dual-cell behavior pass hardware validation.
