# Low-battery charging-rescue result — 2026-08-16

Result: **battery gate remains closed; passive soak in progress**.

The exact pinned ROG Phone 5 was recovered from Qualcomm crashdump to
fastboot, active-slot metadata was restored to the verified fallback slot B,
and no partition image, GPT entry, filesystem, or phone-storage byte was
written. Fastboot continued to report `battery-soc-ok: no`.

Retained AVB metadata proves the installed slot-A chain is inconsistent:
`boot_a` identifies ASUS `18.0840.2103.26-0`, while `vendor_boot_a` identifies
`18.1220.2202.206-0`. The installed slot-A recovery path is rejected after it
entered `05c6:900e` Qualcomm crashdump and displayed the full-RAM-dump wait.

## Bounded RAM-only cycles

Both candidates used the retained ASUS-derived 5.4.210 kernel, a storage-
isolating recovery initramfs, and a fixed AArch64
`RESTART2("bootloader")` rollback helper. The side USB-C port carried the
anchored host data connection; the bottom USB-C port was connected to the ASUS
wall charger.

| Cycle | Candidate SHA-256 | Window | Preboot | Postboot | Result |
|---|---|---:|---:|---:|---|
| `charging-rescue-fastboot-v1-live-v1` | `1b770a94…62e0d` | 30 s | 6.801 V | 6.933 V | exact recovery gadget and direct fastboot return; consumed |
| `charging-rescue-fastboot-v2-live-v1` | `95d80165…5fa6f` | 300 s | 6.934 V | 6.931 V | recovery gadget remained stable and returned directly to exact fastboot; consumed |

The first voltage step persisted, but it is too large to represent stored
energy added during the short interval. The five-minute cycle showed no rising
trend. These voltage-only observations do not determine battery-current
direction and therefore do not accept charging. Neither candidate is reusable.

An independent read-only Claude Opus review reached the same evidentiary
conclusion and identified the missing in-recovery ADSP/PMIC-GLINK telemetry as
the principal diagnostic gap. Its claims were checked against the retained
initramfs, downstream 5.4 source, exact kernel config, and live evidence.

## Next action

A host user service now records exact read-only fastboot voltage and
`battery-soc-ok` samples at 0, 5, 10, 20, 30, 60, 120, 240, and 360 minutes.
It stops on device-identity or slot mismatch. No additional boot is admitted
during this soak.

If the soak stays flat, the next possible transition is a prepared but
unissued 90-second output-only ACM diagnostic. It reads downstream
`power_supply` and ASUS charger attributes, samples current/voltage/
temperature/USB-input state, reports PMIC-GLINK and ADSP probe messages, keeps
storage isolation, and returns directly to fastboot. It performs no charger-
control or storage write.

Stage 1 remains unbooted and its separate one-use claim remains unconsumed.
