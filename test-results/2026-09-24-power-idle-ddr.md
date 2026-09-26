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

## Sensor DSP (SLPI) for the IMU (step 11, r51)

r51 was the r38 set plus the `slpi` overlay, which enables remoteproc@5c00000
with `firmware-name = "qcom/sm8350/slpi.mdt"`. The stock NON-HLOS
`image/slpi.*` (25 files, sizes verified against the FAT listing) went into
firmware kit r3; the kernel was r17. Everything else passed: GPU, 300 s soak,
Wi-Fi 100 MB in 1.88 s, Bluetooth, peripherals.

The SLPI does not boot: `qcom_q6v5_pas 5c00000.remoteproc: error -22
initializing firmware`. The secure monitor rejects `pas_init_image` with an
invalid-argument or invalid-address error, both at boot and on a later manual
start, so it is not an ADSP/SLPI race.
- The metadata is well formed: header 0x354 plus hash 0x1dc0 equals the
  8468-byte `.mdt`; entry 0x88200000 lies in the reserved 0x88200000+0x1500000
  region, the same as stock.
- The upstream definition matches stock: PAS ID 12, LCX/LMX proxy domains,
  AOP load state.
- The ASUS wrapper does not start the SLPI (its PIL only tries `ipa_fws`), so
  it is not a second init.

The QRTR service list stays ADSP (node 5) and Wi-Fi (node 7) only. Like the
audio stream reset, this now needs insight into the TZ/hypervisor side (the
stock kernel runs a Qualcomm trusted VM, `qcom,trustedvm@d0800000`). The
default image does not enable the SLPI.

### SLPI follow-up checks on the r51 trial

- **Firmware provenance.** The phone's `modem_a` and `modem_b` (read-only
  copies) are byte-identical to the WW33 stock `modem.img`, SLPI files
  included. The production charge-kit ADSP is an older build
  (ADSP.HT.5.5-00933-LAHAINA-2, 2021-10-21), but TZ also accepts the WW33
  ADSP: stopping the ADSP and starting it with WW33 `adsp.mdt` ran, and it
  switched back. So a firmware version or era mismatch does not explain the
  SLPI rejection.
- **Stale state.** `qcom_scm_pas_shutdown(12)` before a new start changed
  nothing (`-22` at init).
- **PAS support query.** `qcom_scm_pas_supported()` is false for every ID
  0-31, the ADSP's included, so that query is not answered on this firmware
  and says nothing about the SLPI.

TZ refuses the SLPI image at `pas_init_image` with a generic error, while
the same path loads the ADSP. The upstream definition and the stock PIL node
agree (PAS 12, LPI CX/MX proxy votes at max, XO, AOP load state, region
0x88200000/0x1500000).

## r38 on battery: unplugged boot and idle power (2026-09-25)

With the USB cable removed, an ordinary reboot (from the r51 trial) came up on
the r38 default:
- committed healthy at 28.3 s;
- Wi-Fi radio ready at 39.8 s, Bluetooth `hci0` at 42.3 s;
- Denial active, systemd `running`;
- found over Wi-Fi at 192.168.1.111 (the random MAC gives a new lease each
  boot).

`rog5-bench.py power --seconds 180` (Denial blanked the screen; Wi-Fi
associated; one SSH session open):

| boot | mean current | median | power | CPU busy |
|---|---:|---:|---:|---:|
| r26 (WFI only) | 190.7 mA | 188 mA | 1.60 W | 1.11 % |
| r28 (per-core CPU idle) | 136.2 mA | 135 mA | 1.14 W | 0.47 % |
| r38 (CPU idle, DDR scaling, GCC/GPUCC sync_state) | 114.1 mA | 109 mA | 0.98 W | 1.29 % |

That is 40 % below r26. Top wakeups: arch_timer 286/s, IPI function call
143/s, arch_mem_timer 90/s, timer broadcast 75/s, ath11k CE2 13/s.

The RPMh sleep counters (`qcom_stats` cxsd, ddr) are still 0: the SoC never
collapses CX or puts DDR into self-refresh. Only per-core power collapse runs.
The next idle step is cluster and system low-power states (OSI domains or RPMh
sleep), which were deliberately kept off (ASUS reset after kexec in OSI mode).

Haptics (three 400 ms effects) and the logo LED (red, green, blue) were run
for the user to confirm by eye.

## Stock ASUS 5.4 capture (2026-09-25, RAM only)

A full stock Android boot is off the table: its fstab mounts `/data` from
userdata as encrypted f2fs with `formattable`, and userdata is now the Linux
ext4 partition. Instead, the slot-B wrapper's ASUS 5.4 kernel (our build of
the ASUS source, `5.4.210-qgki-...-builtin-recovery`) ran a capture
executor in RAM:
- `initramfs/stock-capture-5.4` runs as the slot-B loader executor, never
  kexecs, and only mounts modem_a read-only;
- `scripts/host/package-stock-capture-wrapper.py` packages it (the
  wrapper-image steps were split out of package-production-ram-trial.py as
  `build_wrapper()`; r51 still rebuilds byte-identical);
- the output streams over the loader's USB ACM.

Evidence: `~/.local/state/rog5-production-boot-20260923/trial-stockcap-c{1,2,3}-session/`
(capture.txt, and the stock flattened DT as stock-fdt.dtb/.dts in c1).

Findings:
- **SLPI and CDSP are rejected by TZ for the stock kernel too.** With the stock
  PIL (proxy votes, crypto bandwidth, AOP load state, all before init), c2/c3
  log `slpi: Initializing image failed(rc:-22)`, and c3 `cdsp: ... (rc:-22)`.
  The ADSP from the same WW33 image set boots (`adsp: Brought out of reset`).
  The TZ log records each failure as event `0x30001f` (PAS ID, metadata PA),
  then SMC 0x42000201 returns `0xffcfffe1` (-0x30001f). The hypervisor logs
  `pil_init_image_to_tz [300045]`, and at boot `HYPX NOT ENABLED Reason:
  0xfa11`.
- The difference between the images: the ADSP (sw_id 0x4) is bound to this
  OEM (hw_id 0x29, oem_id 0x28, flags 0x0002) and chains to root
  `2c8bc18e…`, the root that also signs `multiimgoem`. The CDSP (sw_id 0x17)
  and SLPI (0x18) carry hw_id/oem_id 0, flags 0x0102, and chain to a different
  root `959b8d05…`. The `multiimgoem` MULT table lists sw_ids including 0x4,
  0x17 and 0x18. Its SHA-384 entries match no image, hash segment,
  sub-range or certificate from the WW33 modem image, so how TZ authenticates
  these two images is still unknown.
- Slot A and slot B hold identical secure firmware, all equal to stock WW33:
  multiimgoem, tz, hyp, xbl, xbl_config, aop, devcfg, keymaster, featenabler,
  qupfw, cpucp, shrm, uefisecapp, abl, dsp, bluetooth.
- So the missing piece is runtime state that stock Android sets up before its
  `on early-boot` writes `boot_adsp`, `boot_cdsp`, `boot_slpi` (vendor
  `init.qti.kernel.rc`). Neither kernel is at fault.
- The PMIC PON history records every reset as `Reset Trigger: PS_HOLD`,
  `HARD_RESET`: software dropped PS_HOLD. That fits the audio stream resets
  being secure-side resets.
- Stock brightness for the AMS678 ER2: `bl_ctrl_dcs`, 1..1023, inverted DBV,
  panel through the Iris6 (`pxlw,iris-lightup-config`). Stock sends `51 hi lo`
  as a DCS long write in HS mode: `iris_pt_send_panel_cmd` in Iris
  passthrough (PT) mode, `mipi_dsi_dcs_set_display_brightness` in bypass. Our
  driver runs the Iris in analog bypass, where only the first 0x51 byte lands
  (3 visible levels, patch 0045) and HS writes were ignored (patch 0043).
  Full-range brightness likely needs the Iris PT path.

Boot-chain incident: after capture c1, the next r38 boot (08:27Z) stalled
before its persistent root (USB NCM up, then TX timeouts at about 2.5 min, no
Wi-Fi, no journal). It never committed, and the target timer put it in
fastboot. The next boot took the V11 fallback because the r38 record was left
`pending`. The r38 boot before the capture had committed healthy at 27.4 s.
After c2 and c3, V11 came back normally. The default is restored through a
fresh bundle, r52 (below).

### r52: default restored (2026-09-25)

r52 is r51 without the SLPI overlay: kernel/modules r17, DTB
`platform-periph-dtb-r3` (r38's), display-firmware-r3 and the current
platform kit, with a fresh descriptor. The audio service stays inactive
because there is no `sound` node. r38 itself could not be rebuilt, because
the kit now needs the audio-module list that modules r14-b lacks.

- RAM trial t52: GPU 300 wake cycles (worst 11.17 ms) and fault recovery,
  a 300 s idle soak with no SSH misses, Wi-Fi 100 MB in 2.78 s, Bluetooth,
  GCC/GPUCC/interconnect `sync_state`, light/proximity, logo LED. The two
  call traces are the known DSI PHY clock reparent warnings, as in r51.
- `install-default-kernel.py --stage` passed at 09:31Z; both ordinary reboots
  committed healthy (`PASS production-7.2.7-r52 committed healthy`, 26 s).

### r52 default: bench verification (2026-09-25, USB attached)

- `rog5-bench.py hw` (20260925T094252Z-hw.json): pass battery_charger,
  bluetooth, buttons, display, dsp_remoteprocs, gpu, leds, rtc, sensors
  (vcnl36866), storage, thermal_cpufreq, touch, usb, vibration. Wi-Fi is
  partial only because hwcheck reads no `wpa` state; wlp1s0 is up at
  192.168.1.15. Suspend is partial by design. Audio, cameras, fingerprint
  and NFC are missing.
- Smooth bench, `--repeat 10`. Each run is an open and a close, so 20
  gestures per scenario (the r38 baseline used 10):

  | scenario | dropped frames | per gesture | r38 per gesture |
  |---|---:|---:|---:|
  | quick_settings | 21 | 1.05 | 2.0 |
  | quick_settings_slow_drag | 37 | 1.85 | 3.4 |
  | keyboard (two runs) | 40, 34 | 2.0, 1.7 | 1.2 |
  | home_pages | 13 | 0.65 | 0.4 |

  Everything is under 5 per gesture; p50 is 16.7 ms; no glitches and no GPU
  errors.
- Throughput (20260925T094924Z-perf.json):
  - SHA-256: A55 750, A78 1484, X1 1739, all 8 cores 8944 MB/s.
  - glmark2: 1639 (r38 1656-1675).
  - The EBI vote reaches its 12.78 GB/s ceiling during the memory tests and
    drops back afterwards.
- Idle power on r52 still needs an unplugged run. The DTB and idle
  configuration match r38, which measured 114 mA / 0.98 W.

## Audio: stock stack plays; upstream hangs at the first kernel buffer write (2026-09-25)

### Stock ASUS 5.4 audio in RAM (captures a1-a12)

- The ASUS 5.4 source was rebuilt with its techpack audio modules (32 `.ko`) in
  the `localhost/rog5-kernel-builder:ubuntu-24.04` container. The clang 18.1.3
  build boots; a host clang 20 build did not (a1). The build is in
  `~/.local/state/rog5-asus54-audio-build-r2`; the writable debug source is in
  `~/.local/state/rog5-asus54-src-debug`.
- `initramfs/stock-audio-5.4` loads the stock module set, boots the ADSP
  through `adsp_loader` and drives `tools/alsa_probe` (a freestanding raw
  ALSA ioctl client).
- Three changes, test build only, were needed to get a card without Android:
  - `audio_notifier` starts on SSR: the service locator is on the modem, and
    its LOCATOR_DOWN reply arrives before the notifier listens;
  - the machine driver skips the WCN BT SLIMbus links: that codec only exists
    once Android's BT stack powers the chip;
  - `mdev -s` after the card registers.
- **Result (a11, a12): `lahaina-mtp-snd-card` registers, and MultiMedia1 ->
  SEN_MI2S_RX (amplifiers off) opens, prepares, runs and plays for 3 s. The
  ADSP returned 150 write-done events, end of stream and a clean close, with
  no reset.**
- The stock command stream, from an `apr_send_pkt` hex dump:
  - AFE clock set (`0x100f3`): SEN_MI2S_IBIT at 3.072 MHz;
  - LPASS votes: `0x100f4` "LPASS_HW", devote `0x100f6` with the client
    handle;
  - AFE `DEVICE_HW_DELAY` and I2S config: 24-bit, SD1, stereo, internal WS,
    48 kHz; then `DEVICE_START`;
  - ASM map: one 0x4000 region, IOVA 0x1fff4000, msw 1;
  - ASM `OPEN_WRITE_V3`: POPP 0x10be4, PCM 0x13222;
  - ADM `DEVICE_OPEN_V8`: topology 0x10312, 24-bit;
  - matrix map, then media format (PCM v4 block);
  - `RUN_V2`, then `WRITE_V2` at 0x1fff4000/0x1fff4f00 (msw 1).

### Upstream 7.2.7 with a packet-dumping `apr.ko` (RAM trials r53-r63)

- r54: upstream sends the same kind of sequence. It differs in a 1.536 MHz
  clock, 16-bit I2S and COPP, NULL POPP (0x10c68) with PCM v2 (0x10da5), and
  ADM `DEVICE_OPEN_V5`. All of these are acknowledged.
- r55, r56: stock's 3.072 MHz clock, a 24-bit back end and the default POPP
  still reset. So none of them is the cause.
- r57: ADSP coredump was already disabled; disabling recovery changed
  nothing.
- r58: with `ASM_SESSION_CMD_RUN_V2` withheld in `apr.ko`, the phone still
  reset. So no DSP command at stream start is needed for the reset.
- r59 (`alsa_probe fill`): prepare, then `sw_params` with a start threshold
  that is never reached, then the first `writei`. The phone reset with no
  stream start.
- r60 (`alsa_probe mmaptest`): writing the same buffer through an mmap of the
  PCM, before and after prepare (after the ASM map), did not reset. The
  following `writei` did.
- r61: with `kernel.panic_on_oops=0 kernel.panic=0` the phone still went down,
  and USB dropped 10 s after play started. The reboot is a PS_HOLD hard reset:
  a ramoops region moved to 0x85c00000 (r62, r63; the stock wrapper leaves it
  alone) came back empty, so DDR is not retained.

So the upstream failure is a Linux-side hang on the first `writei` into the
q6asm PCM buffer, followed by a hard reset about 10 s later. It is not an ADSP
command, not the SENARY port, not the amplifiers, and not a CPU store through
the user mapping. The next step is to check what `writei` touches that mmap
does not in the upstream `q6asm-dai` (fixed buffer from
`snd_pcm_set_fixed_buffer_all`) plus ALSA core path, for example by switching
the buffer type or logging `dma_area`/`dma_addr` before the copy.

### r64-r71: the ADSP's DMA read of the stream buffer is the trigger

- r64: with `ASM_DATA_CMD_WRITE_V2` withheld, both `fill` and `play` survive.
  Upstream's `q6asm_dai_prepare` marks the stream RUNNING, so the first
  `writei` makes `.ack` queue WRITEs, before RUN. The dumped payload matches
  stock's layout: `1ff80000 00000001 <handle> 00000f00 seq 0 0 0`.
- r65: queuing WRITEs only after RUN (`tools/audio_debug`): `fill` survives
  (no writes), but `play` still froze on the first write after RUN.
- r66: re-enabling the crypto node leaves most providers synced, including
  lpass_ag_noc. Upstream lpass_ag_noc has no BCMs, and stock votes nothing on
  it; the stock ADSP TBU (0x1800-0x1bff) has no interconnect vote either.
  Still froze.
- r67: a live `dmesg -W` over SSH carried nothing past the pause. The freeze
  happens right after the WRITE is sent and takes USB and UFS I/O with it.
- r68: the q6asm DAI device is in SMMU group 10 (DMA domain, apps SMMU).
- **r69: WRITE_V2 with `buf_size` forced to 0 does not freeze, and `play`
  completes.** So the trigger is the ADSP DMA-reading the upstream buffer
  (IOVA 0x1ff8xxxx, SID 0x1801). It is not the command, RUN, or the
  ADM/AFE/ASM configuration.
- r70 (q6asm DAIs `dma-coherent`) and r71 (SMR mask 0x3f0 around 0x1801) both
  still froze.

Open: why the ADSP's read through the apps SMMU works on stock 5.4 (vendor
arm-smmu with `qcom,skip-init`, no reset of the boot SMMU state; ION buffers
through `msm-audio-ion`) and wedges the system on upstream. Candidates:
- SMMU global state reset by upstream (sCR0, unidentified-stream handling);
- context-bank attributes;
- a fault handler that touches TBU registers.

### r72-r85: root cause is an SMMU stream route the hypervisor refuses

- r72-r76 (buffer variants: zero-size write, low CMA, a separate alias
  mapping, physical-address buffers): only the zero-size write survived. So
  the buffer allocation path is not the difference.
- r77 (`tools/audio_debug` SMR/S2CR dump module): **SID 0x1801, the ADSP's
  stream for the q6asm buffers, sits at S2CR 0x000200ff = FAULT**, although
  Linux attached it to a DMA domain (group 10, context bank 9). 0x180f and
  0x1803 are on bank 74, upstream's bypass-quirk bank. The ADSP's first read
  of the stream buffer therefore faults, and on SM8350 that fault wedges the
  SoC until the PS_HOLD reset about 10 s later.
- r78: a full dump of the apps SMMU. Linux's own routes (display, GPU, UFS,
  USB) all took effect, on banks 2-13.
- r79-r82 (kprobes on `arm_smmu_attach_dev` by `/proc/kallsyms` address, since
  SMMUv2 and v3 are both built in): the attach succeeds and writes S2CR for
  bank 9. Re-attaching the group after the ADSP booted left it at FAULT too.
  The hypervisor (which traps the SMMU's stream-mapping registers) silently
  drops that write.
- r83 (`rog5-smmu-poke`): copying bank 9's context into bank 52 and routing
  0x1801 there (stock's layout: 0x1801 on CB52, 0x180f on CB40, 0x1803 on
  CB27) was accepted, and **`play` completed with the phone still
  reachable**.
- r84: acceptance scan for 0x1801. Banks 9 and 10 are ignored; 20, 27, 30,
  40, 50, 52, 60, 70 and 73 are accepted.
- Fix: `patches/linux-7.2.7/0049` gives the SM8350 SMMU-500 an
  `alloc_context_bank` hook. For LPASS SIDs (0x1800-0x1bff) it starts the
  search at bank 20, and every other master keeps the lowest free bank.
- **r85 (kernel r18 with 0049, `platform-audio-dtb-r4`, no debug modules):**
  - 0x1801 came up on CB20 (s2cr 0x14) with no poke.
  - `play` with the amplifiers off completed.
  - With both CS35L45 amps enabled in RCV mode, a quiet 100 Hz tone for 2 s
    also completed.
  - The phone stayed reachable throughout, and afterwards it returned to the
    installed r52 chain.

Open: `SNDRV_PCM_IOCTL_DRAIN` returns -EIO after the last period (the data is
consumed). Audible output has not yet been confirmed by ear. The audio DTB is
not in the default yet: a new bundle with kernel r18 needs the full RAM trial
and hw matrix before `install-default-kernel.py`.

### r86-r87: audio in the default (2026-09-25)

- **0050** (`q6asm_dai_pointer`): the pointer is `hw_ptr * period_size`
  modulo the buffer. The former `- 1` left one frame of every period
  pending, so `SNDRV_PCM_IOCTL_DRAIN` never saw an empty buffer and timed out
  with -EIO. With the fix, r86 and r87 return `drain rc=0`.
- **Boot route:** `rog5-audio.service` runs `ExecStartPost=audio-route`
  (`initramfs/production-audio-route`, libasound through ctypes). The card
  has no UCM profile, so this routes MultiMedia1 to SENARY MI2S. It sets
  both CS35L45 to speaker mode with left ASP_RX1 on the bottom amp and right
  ASP_RX2 on the top, both at -12 dB digital (361). The speaker-protection
  DSP is not loaded. DAPM powers the amps only while a stream runs.
- **Output check without a listener** (r85 boot, USB input current, screen
  on, 1 kHz at -6 dBFS against digital silence through the same path, three
  rounds each):
  - bottom amp: +36 to +47 mA;
  - top amp: +21 to +70 mA.

  So both amps drive a load with the signal. Nobody has confirmed the sound
  by ear yet.
- **r86 (kernel r19, DTB r4):**
  - The full trial passed: health, display, Wi-Fi, BT, GPU recovery, a 300 s
    idle soak with 0 misses, and peripherals.
  - hwcheck passes 16 blocks, including audio and Wi-Fi.
  - hwcheck's Wi-Fi check now asks `iw dev link`. The kit's wpa_supplicant
    has no `wpa_cli` socket, so the check had shown "partial".
  - Smooth: QS 0.97, slow drag 1.10, keyboard 1.15 and home 0.60 dropped
    frames per gesture (n=40).
- **CS35L45 IRQ storm** (r86): A55 memcpy fell to 2.85 GB/s (4.2 on r52) and
  A55 memset to 16.8 (20.7), and unloading the audio modules restored both.
  - Cause: GPIO 2 and 90, the amplifiers' open-drain active-low IRQs, were
    left at the TLMM reset pull-down. Both level IRQs fired about 73 times a
    second with no source, and I2C17 took about 7900 interrupts a second of
    status reads.
  - Stock uses `bias-pull-up` (`rcv_irq_default`/`spk_irq_default`). Setting
    the pull-up live through /dev/mem stopped it at once (0/s) and gave
    4.21 GB/s.
  - The audio overlay now carries both pin states (DTB r5).
- **r87 (kernel r19, DTB r5):**
  - The full trial passed. Both amp IRQs stay at 0, and I2C17 is idle at
    0/s. SID 0x1801 is on CB20. Probe `play` drains with rc 0, the alsa-lib
    tone plays, and the phone stays reachable.
  - hwcheck: 16 blocks pass (audio, battery, BT, buttons, display, DSPs,
    GPU, LEDs, RTC, sensors, storage, thermal, touch, USB, vibration, Wi-Fi).
    Suspend is partial. Cameras, fingerprint and NFC are missing.
  - perf: SHA-256 747/1483/1742 MB/s (A55/A78/X1), 8956 MB/s on all 8 cores.
    memcpy: A55 4.21 GB/s, X1 16.6 GB/s. glmark2 1644.
  - Smooth (n=40 per scenario): QS 1.00, slow drag 2.12, keyboard 1.93 and
    home 1.10 dropped frames per gesture. As on r52, a few gestures spike to
    10-15 frames.
- **Default:** `install-default-kernel.py --stage` installed
  production-7.2.7-r87. Two ordinary reboots each ran r87 and committed
  healthy. On the installed default the route applies at 46 s, and the amp
  IRQs stay at 0.
- **Audio idle cost** (r85, screen off, battery full, USB input): loaded vs
  unloaded was 235/231 and 251/229 mA. That run still had the IRQ storm. The
  unplugged idle-power bench on r87 is still to do.

### r88: the SLPI boots with the vendor-partition firmware (2026-09-25)

- The vendor partition (`super` → `vendor_a`, ext4, read-only loop) ships its
  own `firmware/slpi.*`, `cdsp.*` and `adsp.*`. They have the same sizes as the
  modem_a (`firmware_mnt/image`) copies but different contents: `slpi.mdt`
  is 83c528c5… on vendor and 08183cfd… on modem, and there are 26 files
  against 25.
  - Every SLPI attempt so far, on the stock 5.4 wrapper and on 7.2.7, used
    the modem_a images.
  - Android's ueventd presumably searches `/vendor/firmware` first.
- r88 was r87 plus the `slpi` overlay (compose features
  `...,periph,audio,slpi`, DTB `platform-audio-slpi-dtb-r1`).
  - At boot the kit's modem_a image failed as before (`-22`).
  - With the vendor images and a manual `start`, **"remote processor slpi is
    now up"**. Its glink edge came up (IPCRTR, fastrpcglink-apps-dsp,
    LOOPBACK_CTL_DSPS).
  - QRTR lists SNS client service 400 and service 4100 on node 9.
- A QMI SUID lookup (hand-encoded `sns_client_request_msg`) returned no
  sensors for accel, gyro, mag, proximity, ambient_light and the rest. The SSC
  needs its registry and config (`/vendor/etc/sensors/config` holds 63 JSON
  files including `lahaina_icm4x6xx_0.json`, plus `sns_reg_config` and
  persist `sensors/registry`). It reads them over fastrpc (`sdsp`) from a
  host listener, which is hexagonrpcd in postmarketOS. Installing that is
  waiting for the user's decision.
- Firmware kit `display-firmware-r4` (outside git) is r3 with the vendor
  `slpi.*` (SHA256SUMS 390cf505…).
- Side note: overwriting `firmware_class.path` (production value
  `/run/rog5-charge-firmware`) broke the GPU's SQE reload until restored.
  Put new firmware into the charge-firmware tree instead.
- The r88 boot was later found in fastboot with no kernel log of a failure.
  The cause is unknown (possibly a user reboot); to recheck before the SLPI
  enters a default.

### r89-r91: motion sensors work, default r91 (2026-09-26)

- **r89** (the SLPI auto-boots with the vendor firmware from kit
  `display-firmware-r4`):
  - Loading `fastrpc` created `/dev/fastrpc-sdsp`. When hexagonrpcd
    attached, `sensor_process` crashed (`frpck_0_0`, exception 0x3d).
  - The SMMU dump showed the SLPI compute SIDs 0x541 and 0x542 at FAULT (the
    hypervisor refuses banks 9 and 10), with 0x543 accepted on CB11. This is
    the same refusal as the LPASS streams.
  - Routing them live to CB60/61 stopped the crash. The registry task then
    asserted on the missing `sns_reg_version`
    (`sns_registry_sensor.c:154`), and the SLPI recovery re-created the
    compute banks on 9 and 10. The next access wedged the SoC.
  - After the hard reset, one r87 boot stalled (USB NCM up, no userspace),
    so the selector fell back to V11.
- **0051** widens 0049 into a table of SM8350 DSP stream ranges that start
  at bank 20: SLPI compute 0x540-0x55f, LPASS 0x1800-0x1bff, and the CDSP
  compute ranges 0x1180-0x119f and 0x2160-0x217f. The module selection adds
  `fastrpc` and `socinfo` (121 modules).
- **hexagonrpc** (user-approved) is pinned at `third_party/hexagonrpc`
  (upstream 598b591 plus our `sns_reg_version` patch).
  `scripts/device/install-rog5-sensors.sh` builds it on the phone
  (reproducible, sha256 5668f659…). It also stages the stock sensor data
  read-only: 63 vendor configs, 159 persist registry entries plus
  `sns_reg_version`, and dsp_a. `rog5-sensors.service` loads the
  `sensor-modules` list and runs hexagonrpcd.
- **r90** (kernel r20, manual start): 0x541-0x543 came up on CB20-22 with no
  crash.
  - SUID lookup finds accel, gyro, mag, gravity, game_rv, rotv,
    device_orient, sig_motion, step_detect and sensor_temperature.
  - At rest, flat: accel (0.01, -0.02, 10.01) m/s², gyro about 0.01 rad/s,
    mag (-31.6, -54.3, 49.3) µT. The stream runs at about 24 Hz when 25 Hz is
    requested.
  - Proximity and light stay on the VCNL36866 (IIO).
  - Restarting hexagonrpcd does not disturb the SLPI.
- hwcheck `sensors` now needs IIO plus SSC accel, gyro and mag, with the
  accel magnitude plausible. It passes.
- **r91** (r90 plus the kit's `rog5-sensors.service`):
  - The full trial passed: health, GPU, 300 s idle soak with 0 misses,
    Wi-Fi, BT and audio. The sensors came up by themselves with
    NRestarts=0.
  - hwcheck: 16 blocks pass, including sensors and audio.
  - perf: SHA-256 751/1486/1742 MB/s, A55 memcpy 4.15 GB/s, glmark2 1645.
  - Smooth (n=40): QS 1.30, slow drag 1.60, keyboard 1.45 and home 0.97
    dropped frames per gesture.
- **Default:** production-7.2.7-r91 was installed. Two ordinary reboots each
  committed healthy, with `rog5-audio` and `rog5-sensors` active
  automatically (NRestarts=0).

### New fallback: production-7.2.7-safe-r2 replaces V11 (2026-09-26)

The user asked for a newer safe kernel ("V11 is no longer stable"). Once,
after the r89 hang, a fallback to V11 showed only a black screen, because
V11 is a headless volatile root.
- **safe-r2:**
  - kernel/modules r20 and the r52 DTB (`platform-periph-dtb-r4`,
    byte-identical to r3), so no audio or SLPI overlays, which are the parts
    that hung the phone this week;
  - the persistent root (Denial), firmware kit r4 and the Wi-Fi kit;
  - no trial descriptor.
  - `rog5-audio` and `rog5-sensors` skip themselves. The sensor unit gained an
    `ExecCondition` on the SLPI node's `status`: the safe-r1 RAM trial
    restarted it forever, because the disabled node still exists.
- **Tools:**
  - `install-default-kernel.py` now takes the fallback from the phone's
    current selector (verified with the trust key) and
    `--fallback-bundle-dir` to install a new one in the same p24 write window.
  - The target script checks that the new fallback is new on p24 and carries
    no descriptor.
  - 12 installer tests pass.
- **Trials:** safe-r1 and safe-r2 in RAM (Denial, Wi-Fi, BT, touch, a 180 s
  soak with 0 misses), and r92 in RAM.
- **Install:** r92 as the default with safe-r2 as the fallback. Two reboots
  committed healthy, and the selector names safe-r2. V11's files remain on
  p24.
- **Forced fallback:**
  - With the commit unit masked, boot A ran r92 and stayed pending.
  - Boot B ran **production-7.2.7-safe-r2**: `running`, Denial on the panel,
    Wi-Fi up, audio and sensors off.
  - Then the mask was removed, r93 was RAM-trialed, and r93 was installed
    keeping safe-r2. Two reboots committed healthy.
- **Default now:** production-7.2.7-r93 (the same content as r91/r92), with
  fallback production-7.2.7-safe-r2.

### r93 default: speakers by ear, idle power on battery (2026-09-26)

- **Speakers by ear:** the user held the phone over Wi-Fi SSH, USB unplugged.
  Three 1 kHz beeps at -10 dBFS on the left channel, a pause, then three on
  the right. The user heard the bottom speaker, then the top one. Both
  CS35L45 speaker paths are confirmed audible.
- **Idle power** (`rog5-bench.py power --seconds 240`, USB unplugged, over
  Wi-Fi, display blanked after 48 s):
  - **106.2 mA mean / 105 median** (p10-p90 101-114 mA), 0.91 W at 8.58 V,
    CPU busy 0.61 %.
  - That is with Wi-Fi associated, audio loaded, the SLPI and hexagonrpcd
    running, and deep CPU idle and DDR scaling on.
  - For comparison: r38 measured 114 mA / 0.98 W with none of audio or
    sensors; r26 (WFI only) measured 191 mA.
  - Top wakeups: arch_timer 157/s, IPI function calls 90/s, mem_timer 89/s,
    timer broadcast 84/s, Wi-Fi CE 11/s, glink 9/s.

### Denial and userspace fixes on the r93 default (2026-09-26)

- **Quick-settings glitch (colour band):**
  - The band shows at the physical top edge during quick-settings and keyboard overlay animations, never during page swipes. The user watched remote-triggered gestures.
  - The scanned-out framebuffer is always clean: 2103 GPU-read samples.
  - It persists with each of these changed: the MSAA engine patch reverted, backdrop blur off, UBWC off (linear), DPU pinned at 460 MHz with a 4 GB/s vote.
  - The panel is DSC with 48-row slices, and TE uses scanline 0x980 (the same as stock).
  - Suspect: command-mode tear check. Late kickoffs overlap the panel's read of slice 0. Next: DPU tear-check variants, with the user watching.
- **Quick-settings inner scroll:**
  - Denial shell patch 0001 makes the panel as tall as its contents, sliding by its own height. `libapp.so` is rebuilt (1 min, `pub get --offline`) and deployed.
  - The bench handle moved to y=1350.
  - Smooth: QS 1.05, slow drag 1.02 dropped frames per gesture (n=40).
- **Wi-Fi on NetworkManager:**
  - NM 1.58.1 with the glibc wpa_supplicant 2.12 backend. `rog5-wifi-wpa`/`-dhcp` are masked in /etc; `rog5-wifi-radio` still powers the radio.
  - `scripts/device/rog5-wifi-networkmanager.sh apply|revert` imports the /persist network as a 0600 keyfile without printing the key.
  - The raw 64-hex PSK needs `pmf=1`. Otherwise NM also offers SAE, which cannot use a derived PSK, and fails with CONN_FAILED (reported as "ssid-not-found").
  - iwd was rejected: the kernel lacks CRYPTO_USER_API_HASH/SKCIPHER and KEY_DH_OPERATIONS.
  - Result: connected at the same IP, DNS through resolved, HTTPS works.
  - Denial's Wi-Fi tile and detail list now work: networks with signal and security, connected state, forget/disconnect, radio toggle.
- **USB re-plug:**
  - After an unplug/replug the dwc3 link stayed Suspend, the UDC "default", and the host saw nothing. Cause: `dr_mode=peripheral` with no role switch and forced VBUS, so no detach is ever signalled.
  - A dwc3 unbind/bind (core and PHY re-init) recovers it.
  - `rog5-usb-reconnect` (udev on qcom-battmgr-usb change → oneshot service) re-initialises only when an SDP/CDP attach is not configured after 6 s.
  - Verified with a real replug: "gadget still default 6s after attach; re-initialising" → "PASS gadget configured", and the host enumerated.
  - A proper kernel fix (a usb-c connector under pmic-glink, a role switch, and a UDC vbus handler in drd.c) is drafted but not built.

### Overlay colour band: DSI link rate; default r98 (2026-09-26)

- **Root cause:** the AMS678 command-mode DSC link ran at 362 Mb/s per lane
  (byte clock 45.2 MHz) with the port's 48-pixel horizontal blanking. Stock
  uses 829 Mb/s for 60 Hz.
  - Sending a frame took about 15 ms of the 16.7 ms refresh, so a late
    kickoff (overlay animations) let the panel's scan overtake the write. It
    then decoded a half-written 48-row DSC slice as colour noise at the top.
  - The scanned-out framebuffer was always clean.
- **User-observed tests** (r94/r95/r97, RAM):
  - TE scanline 2304 moved the band lower and made it worse; 2460 brought the
    full band back; 2432 (stock) is best.
  - 0053 (front porch 557 → htotal 1655, clock 244.6 MHz, still 60.0 Hz;
    byte clock 103.6 MHz, 829 Mb/s): the band became a line about 8× smaller.
  - Adding 0054 (tear-check continue threshold 0): "a really small line,
    almost perfect".
- **Password and boot:** the password lock set with chpasswd failed both
  `prepare_volatile_root_account` (init) and `rog5-p2-attest`. The init now
  accepts a user hash on the persistent overlay (882c81e9); the attestor
  does not yet. At the user's request the password was dropped (root back
  to `x`).
- **NetworkManager:** the Wi-Fi interface came up as `wlan0` on one boot, so
  NM now manages Wi-Fi by device type.
- **Default:** production-7.2.7-r98 (kernel r23 = r20 + 0052 test parameters
  + 0053 + 0054), with fallback safe-r2 kept.
  - RAM trial: `running`, 16/16 hwcheck blocks pass.
  - `install-default-kernel.py --stage`, then two reboots, each committed
    healthy.

### r99-r102: side-port USB host, audio seek fix; default r102 (2026-09-26)

- **Kernel r24-r26:**
  - 0055: the dwc3 drd gates the pull-up on the role for the legacy glue.
  - 0057: q6asm resets the queue pointer and DSP buffer index on prepare. Playback no longer freezes after a seek.
  - 0058: UCSI re-fetches the role switch and retries.
  - USB Ethernet modules added: cdc_ether, cdc_ncm, r8152, ax88179_178a.
  - DTB `platform-usbotg-dtb-r1`: a usb-c connector under pmic-glink; usb_1 is OTG with a role switch, defaulting to peripheral.
- **Side-port host mode:** since 0058, UCSI switches usb_1 to host by itself when a hub is attached.
  - After a gadget session, every device then failed at full speed: `device descriptor read/64, error -71`.
  - A dwc3 unbind/bind plus a switch to host fixed it: the hub (4 ports) and its card reader came up at high speed.
  - `rog5-usb-reconnect` now also runs on usb_role changes. In host mode it waits 4 s. If nothing enumerated, it re-initialises once (at most every 30 s) and restores host. It never re-initialises the gadget while in host mode.
  - Verified on two real replugs: -71, then re-init, then the hub and card reader at high speed.
- **The bottom port (usb_2)** is still disabled. It needs the RT1715 Type-C controller and an OTG VBUS regulator (drafted, not built).
- **r101 install:** the first try stopped at inspection with `write scope is sda sda23 sdh`, the hub's card reader.
  - The installer now leaves USB disks out of the UFS write scope (13 tests pass).
  - The install then passed, but the first boot ended in the ASUS bootloader. The phone was the hub's USB host at boot.
  - Cause: not the slot-B wrapper. The r101 record was left `pending`, which only the loader's decision writes, after the wrapper and loader checks passed.
    - The 7.2.7 production ramdisk starts pmic_glink/UCSI and the ADSP. Since 0058, the side port then turns host, and the hub's card reader (USB_STORAGE=y) appears as an extra sd disk.
    - The init's `wait_for_ufs_discovery` needs a stable 117 physical nodes. It timed out, then `force_rollback` rebooted into the bootloader.
    - `fastboot reboot` then ran the fallback safe-r2, as designed after an uncommitted try.
  - Fix: the production ramdisk's exact-117 checks skip USB disks. It goes through a RAM trial and install; no flash.
    - The same skip for the boot_b wrapper is built but not flashed: `slotb-wrapper-usbdisk-r1`, flash candidate `f1069935…`, reproduces the installed `dcc487f1` from old sources. It only matters for a disk on the bottom port, which 5.4 can host through the RT1715.
  - Until the fix is installed, don't reboot with USB storage on the side port.
- **Default:** production-7.2.7-r102 is r101's content with a new descriptor. It was installed with the Deck as USB host; two reboots each committed healthy (62 s and 59 s to SSH). The fallback is still safe-r2.

### Suspend works; default r113; boot display (2026-09-26)

- **Suspend bring-up**, found with pm_test levels, pm_print_times and a raw ramoops read:
  - The production kernel's UFS discovery containment rejected every UFS power transition, so suspend aborted with `ufshcd_wl_suspend failed: -16`.
    - 0059 allows **system** suspend on bounded-write kernels: START STOP UNIT to spm_lvl 5, link off. Runtime PM and shutdown stay rejected.
    - No query write is needed, because auto-BKOPS and WriteBooster are never enabled. A runtime switch `ufshcd_core.rog5_ufs_system_pm` selects 0 reject, 1 no-op, 2 real.
  - The next reset (a warm reset, no panic dump) came on resume: `pcie_0_gdsc status stuck at 'off'`. 0060 declares the gcc-sm8350 PCIe GDSCs `PWRSTS_RET_ON`, as sm8450 and sm8550 do.
  - `CONFIG_PM_DEBUG`/`PM_SLEEP_DEBUG` are now on, for `/sys/power/pm_test`.
  - Logging method: unbind the debug UART console (98c000.serial), set `ignore_loglevel=Y` (production-platform-modules clears it), pad the log past the wrapper's ~160 KB overwrite, then read the raw region after the reset with an out-of-tree debugfs module that vmaps 0x9b800000 write-combined. The cached linear map returns stale data.
- **Result (r109, all services up):** s2idle and deep suspend both pass (5/5 with RTC wake). After each resume, Wi-Fi is associated, the USB gadget configured, Denial active and UFS readable.
- **Standby power, on battery:**
  - Awake idle with the screen off: 92–106 mA (current_now).
  - A deep-suspend loop: about 79 mA. This is the charge counter divided by 2: the counter runs 2x the 2S pack current, as calibrated by awake idle at 200 000 µAh/h against 106 mA.
  - The phone wakes about every 60 s from a wake-capable interrupt; PMIC RTC events match the suspend count.
  - The RPMh counters `cxsd`, `ddr` and `aosd` stay 0: the SoC never collapses CX or DDR. That needs the cluster/system low-power states (OSI domain idle), which were kept off after the ASUS reset under OSI.
  - Suspend is therefore reliable but saves only about 25 % for now.
- **r110 install, first boot:** at 206 s, UFS `hibern8 exit failed -110`, PHY re-init timed out, the root filesystem got I/O errors, and an SPMI PMIC-arbiter IRQ storm followed (IRQ 130, from 217 s).
  - The stage reports looked like a hang at `runtime`, but the Deck's NetworkManager had moved the link from 169.254.77.1 to 10.77.0.1.
  - Recovery: a forced restart ran the fallback safe-r2.
  - Not reproduced since: the r109 RAM trial ran 50 min including suspends, and an r111 UFS idle/active soak ran 216 cycles in 15 min without error. Treated as sporadic and kept under watch.
- **Boot display:**
  - The kernel fbdev/fbcon client is gone (`drm_client_lib active=`), so the ASUS splash now stays up until Denial's first commit.
  - 0061: the panel keeps a brightness written while it's off. systemd-backlight's boot restore had failed with EPERM, and without it the panel came up at brightness 0.
  - The remaining colour noise (user photo) is Denial's first modeset (28.6 s) scanning out a raster target Flutter hasn't drawn yet. A deniald boot animation is in progress (Denial agent).
- **Default:** production-7.2.7-r113 = kernel r30 (0059, 0060, 0061, PM debug) plus the ramdisk with the USB-disk scope fix and no fbdev. Two reboots, each committed healthy (60 s to SSH). The fallback is still safe-r2.
- **Host:** superseded kernel build trees r1–r19, r21, r22, r24 and r25 were deleted (the disk was full; they can be rebuilt from git).
