# Low-battery charging-rescue result — 2026-08-16

Result: **battery gate remains closed; physical side-port isolation did not
establish charging**.

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
| `charging-direct-stock-storage-isolated-v3-live-v1` | `713314d6…edb` | about 9 s | 6.883 V | 6.880 V | direct ASUS-derived charger path returned to exact fastboot; no ADB or crashdump; consumed |

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

## Side-port isolation result

After crashdump recovery, exact fastboot reported 6.836 V. The side PC cable
was physically removed and only the bottom ASUS wall charger remained attached
for about 30 minutes. The next exact reading was 6.839 V with
`battery-soc-ok: no`; this 3 mV change is within measurement and thermal noise
and does not establish net-positive charging. With side USB reconnected, the
reading fell to 6.833 V. Physical side-port isolation is therefore no longer
the next discriminator.

The direct candidate above was followed by one normal slot-A boot. It entered
`05c6:900e` Qualcomm crashdump, matching the rejected recovery result. The
hardware-key sequence returned exact fastboot and active-slot metadata was
restored to B without booting Alpine.

## Offline firmware result

The official ASUS WW-33.0210.0210.200 package was downloaded from ASUS and
verified as a complete 3,859,425,958-byte ZIP at SHA-256
`7d53b6cc78486598e1913ca5a9a48c7292b90527bd9c9ac80dabd5324be14eb4`.
Its CRC check passes. The full A/B payload contains a single signed
charging-relevant closure: `boot`, `vendor_boot`, `dtbo`, `dsp`, `aop`, `tz`,
`xbl`, and `vendor`. The extracted `boot`, `vendor_boot`, and `dtbo` AVB
properties all identify `18.1220.2202.206-0`; the kernel reports
`5.4.210-qgki-perf-gc89cd02a7dfe`. This closes the offline source-availability
gap but does not make the currently installed slot coherent and does not
authorize a low-voltage boot or write.

## Next action

No additional RAM-only charger candidate is admitted until that hardware
closure has been reduced to one independently reviewed, fully RAM-contained
design and the battery risk is acceptable. The immediate zero-write
discriminator is an inline USB-C power meter on the bottom port; qualified
hardware service is the fallback if the port supplies negligible power or the
pack falls further. All five issued candidates above are single-use and must
never be retried.

Stage 1 remains unbooted and its separate one-use claim remains unconsumed.
