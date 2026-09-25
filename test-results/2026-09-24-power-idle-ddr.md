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

### r30: votes in place, DDR still held

t30 (kernel r13, `gpubw` + `bwmon`, P2 ordering fix) passed:
- P2 at 23.20 s, then the platform modules; system `running`.
- GPU: 300 wake cycles (worst 7.8 ms), fault recovered in 0.1 s.
- 300 s idle soak with 0 SSH misses; Wi-Fi 100 MB in 1.6 s; Bluetooth on its
  own.
- Both bwmons bound. Consumers on EBI: bwmon 0.8 GB/s, GPU 10.94 GB/s while
  busy, UFS 2.9 GB/s, display, USB. The aggregate stayed INT_MAX because crypto
  still held `sync_state`, and the RPMh DDR/CX sleep counters stayed at 0.

One `HFI_H2F_MSG_GX_BW_PERF_VOTE ... timed out` (the GMU answered after more
than 1 s) happened when glmark2 exited and Denial restarted. There were none in
5 more glmark2/Denial cycles, in a further smooth run, or anywhere on r31/r32.
It is left for the step-8 soaks.

### r31: DDR scaling

With the crypto node disabled, mc_virt, aggre2 and gem_noc reached
`sync_state`. The idle EBI vote is now 1.8 GB/s peak (451 MHz DDR) instead of
INT_MAX.

| `rog5-bench.py perf` | r30 (DDR max) | r31 (scaling) |
|---|---:|---:|
| glmark2 (9 scenes, 1080x2448) | 1669 | 1642 |
| SHA-256 A55 / A78 / X1, MB/s | 749 / 1484 / 1747 | 748 / 1479 / 1748 |
| SHA-256, 8 cores | 8948 | 8944 |
| memcpy X1 / A55, GB/s | 16.9 / 4.3 | 17.9 / 4.2 |
| EBI peak vote during memcpy | INT_MAX | 12.78 GB/s (bwmon top) |

Throughput holds. Smoothness (3 gestures per scenario) stays within the goal:
quick settings 4, keyboard 5 and home pages 6 dropped frames. But
input-to-first-frame latency grew from about 26 ms to about 38 ms (quick
settings 28 to 41 ms, keyboard 24 to 37 ms).

Two experiments on the same boot narrowed it down:
- A 443 MHz GPU floor (6.22 GB/s GPU vote) did not help (37/35 ms).
- An experiment module flooring CPU to LLCC and LLCC to DDR helped only at the
  top levels. At 7.46/6.22 GB/s latency was 40/31 ms; at 16/12.78 GB/s it was
  27.6/26.1 ms.

bwmon only follows measured traffic, and the first frames of a gesture are
latency-bound. Stock Android covers this with memory-latency governors and
input boost. `tools/input_boost` (r32) holds both paths at the top level from
the first touch, key or power-key event until 250 ms after the last one.

### r32: input boost, installed as the default

t32 passed the full session (GPU worst wake 8.9 ms, 300 s soak with 0 misses,
Wi-Fi 100 MB in 1.6 s, Bluetooth), and `rog5-input-boost` is bound to the
touchscreen. During a swipe the EBI vote goes to 12.78 GB/s; between gestures it
falls back to 0.8-2.9 GB/s. A/B on the same boot, 5 repeats each (median
input-to-first-frame, dropped frames):

| scenario | boost | no boost (rmmod) |
|---|---:|---:|
| quick settings | 33.9 ms, 15 | 46.1 ms, 11 |
| keyboard | 26.2 ms, 10 | 29.1 ms, 9 |
| home pages | 31.5 ms, 10 | 28.9 ms, 10 |

`install-default-kernel.py` installed r32 at 19:55Z; two ordinary reboots
committed healthy. No GMU HFI timeouts on r31 or r32.

## GMU sync_state (step 6, r33)

The A660 GMU platform device never bound a driver: msm drives it through
`of_find_device_by_node()`. fw_devlink therefore kept GCC and GPUCC waiting
(`sync_state() pending due to 3d6a000.gmu`), and their unused boot-time clocks
stayed on. `tools/gmu_bind` is an empty platform driver (`driver_managed_dma`,
no clocks or registers). It loads before msm, because the driver core refuses
to probe a device that already has devm resources.

On t33:
- `3d6a000.gmu` is bound to `rog5-gmu-bind`.
- GCC, GPUCC, mc_virt and aggre2 all report `state_synced=1`.
- The GPU passes: 300 wake cycles (worst 9.0 ms), fault recovered in 0.1 s.
- 300 s idle soak with 0 misses; Bluetooth came up.
- Wi-Fi was 100 MB in 1.63-1.78 s over three repeats. The session's single
  8 s timeout did not recur.

r33 was installed as the default at 20:10Z; two ordinary reboots committed
healthy.

A known warning remains at msm load: the DSI PLL lock fails during the
bootloader handoff, followed by a `dsi0_phy_pll_out_dsiclk already disabled`
clock-reparent WARN. It predates this work, and the display works; it is left
for step 12.

## Slow-drag dropped frames: what they were (step 7)

Each slow-drag gesture showed one 130-166 ms gap, which accounted for
essentially all of its 8-11 "dropped frames". The gap started 1010-1035 ms
after touch-down: the scripted drag moves for 1.0 s, rests the finger for
150 ms, then lifts. Nothing on screen changes while the finger rests, so
Denial correctly renders nothing. The bench now reports gaps inside that rest
as `finger_rest_gap_ms` and does not count them as dropped. It also locates
the worst remaining gap and lists the kernel trace events inside it.

With that correction (r33, 20 gestures per scenario, profiled run):

| scenario | dropped frames | per gesture | gestures dropping 0-1 |
|---|---:|---:|---:|
| quick settings (fling) | 21 | 1.05 | 18 / 20 |
| quick settings slow drag | 56 | 2.8 | 14 / 20 |
| keyboard | 17 | 0.85 | 17 / 20 |

The remaining outliers (6-10 frames in 6 of 20 slow drags, and one quick
settings fling) share one pattern. A 120-185 ms gap comes just before the
final frame of the settle animation, 370-500 ms after the lift. In that gap
the GPU suspends and resumes, and a 1999 Hz call-graph profile of deniald
shows 3 samples in 138 ms, all threads waiting in epoll or poll. Nothing is
blocked or rendering, so this is a late repaint requested by the shell after
its animations end, not a GPU, DDR or allocation stall. The shade's settle
path (`endQuickSettingsDrag` -> `open/closeQuickSettings`, implicit
animations) has no timer in it; the next step is to trace which widget
schedules that frame.

## Haptics, light/proximity sensor, logo LED (step 11, r34-r36)

On the r33 default, a development module enabled QUP wrapper 0 SE0 and SE6
I2C at run time; all three stock parts answered:

| part | bus / addr | identity | driver | result |
|---|---|---|---|---|
| AW8697 LRA haptics | SE6 0x5a | ID 0x97 | tools/aw8697 (input FF_RUMBLE, CONT mode) | a 1 s effect: GLB_STATE 0x06 (CONT playing), SYSCTRL 0x48, back to standby after |
| VCNL36866 light/proximity | SE0 0x60 | ID 0x62 | tools/vcnl36866 (IIO) | room light 37-39 counts (about 23 lx at the default calibration), proximity about 152-155 with nothing near; switched off 2 s after the last read |
| MS51 Aura logo MCU | SE0 0x16 | firmware 0x0105 | tools/aura (multicolor LED `rgb:logo`) | powered through PM8350C GPIO 2; static colour written and applied |

r34 (both buses, the three devices and PM8350C LDO7 declared at 3.3 V, the
sensor's `vcc_psensor`) reset within the first second of kernel boot. It left
no panic record and never reached the USB gadget. The bisect:
- r35 (SE6 + AW8697 only) booted, and haptics bound from DT.
- r36 (SE0 + VCNL36866 + MS51, no LDO7) booted: sensor 37-39 lx counts /
  proximity 155, logo firmware 0105, the LED lit for 3 s.

So LDO7 stays undeclared; the boot chain leaves it on. Whether the user feels
the vibration and sees the logo is still to be confirmed.

r35 also produced a second GMU `HFI_H2F_MSG_GX_BW_PERF_VOTE` timeout (worst
GPU wake 1036 ms in the 300-cycle test). GMU-side DDR voting (patch 0046) is
therefore dropped in kernel r14. The GPU's OPP bandwidths are still voted from
the CPU side on every frequency change.

### r37/r38: installed

- r37 (kernel r14 without 0046, both buses, no LDO7) booted; the Aura LED
  needed a DT color/function to be named.
- r38 passed the full trial:
  - GPU: 300 wake cycles (worst 11.4 ms), no GMU HFI timeouts.
  - 300 s soak; Wi-Fi 100 MB in 1.75 s; Bluetooth.
  - Peripherals: haptics played, `rgb:logo` lit and turned off, proximity
    153-155.
- r38 was installed as the default at 21:38Z; two ordinary reboots committed
  healthy.
- `rog5-bench.py hw` now passes vibration (`aw8697-haptics`), leds
  (`rgb:logo`) and sensors (`vcnl36866`). Audio, cameras, fingerprint and NFC
  remain.

## Audio (step 10, r39-r42)

The earpiece ("RCV", 0x30) and speaker ("SPK", 0x31) CS35L45 amplifiers on
SE17 I2C answered on the r38 default: DEVID 0x35a450, rev A0, with resets on
TLMM 104/105. The ADSP's APR services (q6core/q6afe/q6asm/q6adm) register when
the stack is loaded.

Changes:
- Kernel r15:
  - `CONFIG_SND_SOC_CS35L45_I2C=m`.
  - Patch 0046: the sm8250 machine driver sets the SENARY MI2S bit clock and
    I2S format, for every codec DAI on the link.
- Kernel r16: patch 0047, a q6routing `SEN_MI2S_RX Audio Mixer`.
- `sm8350-asus-rog-phone5-audio.dtso`:
  - q6afe SENARY_MI2S_RX on SD1 and LPI GPIO10-13 `i2s2`;
  - the sound card (MultiMedia1/2 plus a Speakers back end with both amps);
  - the amps on i2c17, whose QUP wrapper 2 stays disabled at boot.

Trials:
- r39: the audio modules loaded with the boot modules. The q6asm DAIs took an
  apps SMMU context ahead of PCIe, and ath11k MHI failed (-110), the same
  failure mode as wrapper 2 at boot. Fix: `rog5-audio.service` loads
  `audio-modules` after Wi-Fi and Bluetooth.
- r40: Wi-Fi, Bluetooth and both amplifiers were fine, but the card failed
  -ENODEV. fdtoverlay had reversed the DAI link order, so q6routing's routes
  to q6asm widgets failed, and in 7.2 component route errors are fatal. Fix:
  links ordered mm1, mm2, speaker, checked by the composer.
- r41: the card registers: `ASUSROGPhone5`, MultiMedia1/2 PCMs, and the RCV/SPK
  controls (DACPCM Source, AMP Enable, volumes, DSP1). q6routing had no
  SENARY mixer, which r42 adds.

The ADSP accepts the LPASS core HW vote but rejects the devote (AFE 0x100f6),
so LPASS stays voted after first use.

### r42-r46: playback start resets the phone (open)

With patch 0047 (r42) MultiMedia1 can be routed to SEN_MI2S_RX, and the card,
controls and amplifiers are all present. Starting a stream resets the whole
phone. No panic record is left; the next boot is the r38 default.

The resets were staged down to one step:
- r43: the reset happens in the DSP path alone. Both amplifiers were disabled
  (AMP Enable 0, DACPCM Source Zero) and fed a -40 dBFS tone.
- r44: holding the LPASS core/dcodec votes (LPI pinctrl runtime PM forced on)
  did not change it.
- r46: a kernel log streamed to the userdata filesystem with a global sync per
  line shows `open`, `hw_params` and `prepare` succeeding, so the AFE port
  configuration is accepted. The reset comes at the first write, when the
  stream runs. There are no SMMU fault or remoteproc messages in between.

A hard reset at stream run, without the amplifiers, points to a fatal ADSP
error when LPASS starts clocking data out of SENARY MI2S (LPI i2s2). The ASUS
firmware turns that into a device reset. Next steps: compare the stock
SENARY/LPI clock setup (IBIT vs EBIT, LPI clock root, `msm-mi2s-master`,
ext-mclk) with upstream q6afe; test an unconnected MI2S port to tell a
SENARY-specific problem from a general AFE-run one; recover the ADSP crash
reason from SMEM if the reset can be delayed. Audio is not in the default
image: r38 carries none of the audio changes.

### r47: the amplifiers are ruled out

r47 replaced both CS35L45 in the Speakers link with the `linux,spdif-dit`
dummy codec. The phone still reset at the first write, after a successful open,
`hw_params` and prepare (which starts the AFE port). The reset therefore comes
from the DSP data path itself once the ASM stream runs into SENARY MI2S.
The upstream q6afe clock range does cover SEN_MI2S_IBIT (0x10D within
0x100-0x116). The q6asm buffer SID matches stock (0x1801, mask 0xf in the
IOVA). Still open: LPI island clocking for i2s2, the ADM/ASM topology, and the
ADSP crash reason (SMEM), which needs a way to keep the phone alive long
enough to read it.

### r48/r49: not port- or IOVA-specific (open)

- r48 used the unwired PRIMARY MI2S port with the dummy codec (no pins, no
  LPI). It reset at stream run in the same way, so the fault is in the general
  ASM/ADM/AFE streaming path, not SENARY or LPI.
- r49 (kernel r17, patch 0048) limited the q6asm stream-buffer IOVAs to
  29 bits (`qcom,iova-bits`), the stock driver's 0x10000000-0x1fffffff
  window. It still reset at stream run. That the limit took effect is not
  verified: the reset leaves no log.

The phone resets without a Linux panic and without a remoteproc crash report.
That points to a secure-side reset (an XPU or hypervisor stage-2 violation by
the ADSP on first buffer access) rather than a recoverable ADSP crash. Audio
remains open; the default (r38) carries none of these changes.

## GPU soak on the r38 default (step 8)

On a fresh r38 boot, back to back:
- 3000 GPU suspend/wake cycles: worst wake 11.84 ms, 0 over 50 ms, no
  failure.
- Three glmark2 runs: 1662, 1656 and 1675.
- Five rounds of the smooth bench (10 gestures per scenario): quick settings 20,
  slow drag 34, keyboard 12 and home pages 4 dropped frames. That is 2.0, 3.4,
  1.2 and 0.4 per gesture.

The kernel log after the soak has no GMU HFI timeout, GPU fault or hangcheck.
With CPU-side GPU DDR votes (0046 dropped), no GMU stall has recurred since r35.

## Cleanup (step 13)

- The phone's persistent root had
  `/etc/systemd/journald.conf.d/rog5-hang-debug.conf` (persistent storage,
  1 s sync, no rate limit), a debugging aid from the hang hunt. It is removed,
  and journald was restarted with the stock settings.
- The DCS probe module is not loaded and the brightness-UI transient unit is
  gone. The repo no longer carries either tool (git history does).
- The laptop's USB profile is unchanged; `rog5-bench.py hw` passes (earlier
  run, this boot).

## Wake from screen-off (step 12)

On r38, after Denial blanked the screen (48-58 s idle), a virtual key press
brought up the display pipe and the first frame in 119-135 ms (3 wakes). The
earlier multi-second wakes came from synchronous console printk, which the
platform kit has lowered to warnings since r16. A watchdog panic restarting the
phone was verified in milestone 1 (self-recovery in 35 s). Whether the lock
screen really needs a double tap on wake needs the user's eyes.

### r50: how the phone dies at stream run

A heartbeat script appended uptime, the remoteproc states and the last kernel
line to userdata every 50 ms, with a sync each time. It ran normally up to
454.93 s, with the ADSP `running`. The first `writei` (stream run, first
ASM buffer) started about 455.0 s, and the heartbeat stopped there: the phone
reset within about 80 ms. No kernel message, no ADSP state change, no panic.
That is the signature of a secure-side reset (an access violation) when the
ADSP first touches the stream buffer, not of an ADSP software crash (Linux
would see and log that).

Compared with stock and found identical:
- the ASM memory-map pool (SHMEM8_4K, property flag 0);
- the SID bits in the buffer address (0x1801, mask 0xf);
- the MI2S clock setup;
- master mode.

Stock confined the buffers to IOVA 0x10000000-0x1fffffff; r49's 29-bit limit
did not help, although whether it took effect is unverified. No SM8350 board in
the upstream tree has working APR audio, so there is no reference to follow;
this needs lower-level work (e.g. reading the reset reason from the PMIC/TZ
restart registers, or testing buffers from a hypervisor-shared region like the
stock audio CMA pool).
