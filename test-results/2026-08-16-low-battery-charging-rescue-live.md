# Low-battery charging-rescue result — 2026-08-16

Result: **battery gate remains closed; physical side-port isolation is the
next discriminator**.

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
| `charging-telemetry-v1-live-v1` | `1cfffb18…800` | 90 s | 6.924 V | 6.922 V | 35 complete ACM frames; zero power-supply devices; consumed |
| `charging-hybrid-asus-recovery-v2-live-v1` | `5b1297a2…a9f` | bounded 900 s | 6.922 V | 6.923 V | USB disconnected and exact fastboot returned after about eight seconds; no ADB or crashdump; consumed |

The first voltage step persisted, but it is too large to represent stored
energy added during the short interval. The five-minute cycle showed no rising
trend. These voltage-only observations do not determine battery-current
direction and therefore do not accept charging. Neither candidate is reusable.

An independent read-only Claude Opus review identified the missing
in-recovery ADSP/PMIC-GLINK telemetry as the principal diagnostic gap. Its
claims were checked against the retained initramfs, downstream 5.4 source,
exact kernel config, and live evidence. The config has the Qualcomm battery
and PMIC-GLINK drivers built in. The downstream source requires the
`PMIC_RTR_ADSP_APPS` channel and `msm/adsp/charger_pd`; live Type-C reached
`Attached.SNK`, but all 35 telemetry frames had `PSY_COUNT value=0`.

The hybrid's first version was canceled intact before claim entry after
offline review found that charger mode lacked a charger-class trigger and
bounded rollback. Version 2 added only that trigger, recovery ADB setup, and a
15-minute bootloader rollback. It used the exact slot-B 5.4.134 kernel whose
version matches the installed slot-B vendor modules. Its early return means
the preserved older recovery userspace did not establish a usable charger
environment; it does not establish why second-stage recovery exited.

## Next action

The zero-boot fastboot soak fell from 6.931 V to 6.925 V over its first 30
minutes. With both phone ports attached, the side data port may be winning
input selection with the PC's low-current VBUS while the bottom wall charger
is ignored. The host hub accepted `CLEAR_FEATURE(PORT_POWER)` logically but
fastboot remained usable, proving that it did not electrically remove side
VBUS. The next bounded experiment therefore requires physically unplugging
only the side cable, leaving the bottom ASUS charger attached, then
reconnecting side USB and reading bootloader voltage and `battery-soc-ok`.

No additional RAM-only charger candidate is admitted until that hardware
isolation result is known or an exact matching ASUS charger userspace is
available. All four issued candidates above are single-use and must never be
retried.

Stage 1 remains unbooted and its separate one-use claim remains unconsumed.
