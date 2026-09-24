# 2026-09-24: battery boot, idle power, CPU idle, DDR voting (plan steps 1-5)

Kernel 7.2.7, bundles r24-r30. Every change was RAM-trialled first
(`production-ram-trial.py`, one boot per wrapper image); sessions and logs are
under `~/.local/state/rog5-production-boot-20260923/trial-727-tNN*`.

## CPU capacity and EAS (r24-r26, step 1)

r24/r25 added `capacity-dmips-mhz` and `dynamic-power-coefficient` for the
A55/A78/X1 cores (sm8250 and sc8280xp values); `cpu_capacity` read about
284/836/1024 and EAS switched on. With EAS, Denial's raster and UI threads ran on
the A55s, and the bench regressed. Quick settings went from 5 to 60 dropped
frames, keyboard from 7 to 77 and slow drag from 74 to 188. With
`sched_energy_aware=0` they were still 50/33/95. r26 removed the capacities
again; they are kept in `sm8350-asus-rog-phone5-cpu-capacity.dtso` for a later
test with uclamp (`CONFIG_UCLAMP_TASK[_GROUP]`, kernel r12).

## Booting without USB (r26-r29, step 2)

Two unplugged reboots fell back to fastboot and then to V11:
- r26: the deferred-UFS rendezvous waited 15 s for a USB host carrier and then
  failed the boot. Since r27, a production archive (platform kit, read-only UFS)
  continues if no carrier appears within 2 s.
- r27: the power/USB loader required USB power, a device/sink Type-C role and
  an NCM carrier (`power-usb-usb-offline`). Since r29, a production archive
  continues on battery after 1.5 s offline. On USB it still validates the
  charging input (voltage, current limit) and records the role and NCM as seen.
  Battery health, voltage and temperature checks stay strict.

On battery, Wi-Fi starts at 7.0 V and 15 % charge or more (2S pack); on USB it
always starts. Hotspot and Bluetooth are unchanged.

After a replug during the r28 trial, the phone saw a data port (SDP, Type-C
partner present) but its UDC stayed in `default` and the Deck never saw an
enumeration attempt. Soft reconnect and a gadget rebind did not help; an
ordinary reboot to fastboot did. Log: `r28-usb-replug-failure.log`. This is
still open (step 12).

## Idle power (steps 3-4)

`rog5-bench.py power`: battery only, screen blanked by Denial, 120 s at 1 Hz
from `qcom-battmgr-bat`.

| boot | CPU idle | mean current | power | CPU busy | top wakeups/s |
|------|----------|-------------:|------:|---------:|---------------|
| r26 | WFI only | 190.7 mA | 1.60 W | 1.11 % | arch_timer 612, IPI call 252 |
| r28 | per-core PC (`cpu-sleep-0-0`/`1-0`) | 136.2 mA | 1.14 W | 0.47 % | arch_timer 170, mem_timer 95, IPI call 93, broadcast 78 |

The per-core power-collapse states run in PSCI platform-coordinated mode (the
stock regime). `ARM_PSCI_CPUIDLE_DOMAIN` stays off, so no OSI mode and no
cluster or RPMh states. Result: 29 % less idle power. t29 (r29 with cpuidle)
passed a 300 s idle soak (0 SSH misses, worst RTT 0.19 s), 300 GPU wake cycles
(worst 7 ms) and fault recovery (0.1 s). DDR still sits at the boot maximum
(next section), which is most of what is left.

## Smoothness changes in r28

- `shmem_enabled=within_size`: GPU buffers are shmem-backed, and huge pages cut
  the per-frame allocation cost. Quick settings went from 37 to 8 dropped frames
  over 6 gestures (p95 31.8 to 17.3 ms), with 2911 THP file allocations and 0
  fallbacks.
- `rog5-denial.service` `CPUAffinity=4-7`: keyboard went from 25 to 6 dropped.
- Slow drag is still 54 dropped (about 9 per gesture); that is step 7.

## P2 backlight race (t29)

t29 failed its P2 gate with `a physical backlight is on`. msm and the panel
driver light the panel as they bind (about 24.2 s), and the P2 backlight check
ran at 24.40 s. Wi-Fi depends on P2, so it was skipped and the trial failed. The
t24 failure previously blamed on Denial was most likely the same race.
`rog5-platform-modules.service` now runs `After=rog5-p2-ready.service`. On t30,
P2 passed at 23.20 s and the modules loaded at 23.74 s.

## DDR voting (step 5)

Before: the A660 catalog had no BCM list, so `a660_build_bw_table` sent a
single "off" DDR vote. The GPU OPPs had no bandwidth, and the CPUs had no
memory-bandwidth governor. DDR/LLCC stayed at the boot-time maximum because the
driverless crypto engine held the mc_virt/aggre2 `sync_state`.

- Patch 0046 (kernel r13): the stock KGSL SM8350 BCMs for a660 (SH0/16, MC0/4,
  ACV fixed perfmode 0x08). The GMU now builds per-level votes from the OPP
  bandwidths.
- `sm8350-asus-rog-phone5-gpu-bw.dtso` (`gpubw`): the gfx-mem path, plus peak
  bandwidth per GPU OPP from the stock LPDDR5 nominal bus levels. 840/778/738 MHz
  get 12.78 GB/s, 676 MHz 10.94, 608-443 MHz 6.22, 379 MHz 4.07 and
  315 MHz 1.80 GB/s.
- `sm8350-asus-rog-phone5-bwmon.dtso` (`bwmon`): the stock bw_hwmon pairs as
  upstream icc-bwmon nodes. CPU to LLCC is v4 at 0x90b6400 (SPI 581); LLCC to
  DDR is v5 at 0x9091000 (SPI 81). OPP tables are the stock LLCC and LPDDR5 DDR
  levels. Boot modules gain `icc_bwmon`, and `qcom_stats` for the RPMh sleep
  counters.
- `ddrscale`: the crypto node is disabled, which the composer only allows
  together with `gpubw` and `bwmon`. That is trial r31.
