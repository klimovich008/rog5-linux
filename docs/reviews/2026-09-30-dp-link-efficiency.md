# DP link efficiency on the side port: 4 vs 2 lanes, rate, refresh (2026-09-30)

Question (user): do 4 DP lanes cost more power or heat than 2, and how do
other drivers choose link rate, lanes, resolution and refresh for the best
efficiency? Scope: kernel 7.2.7 msm DP with 0136-0139 (4 lanes on pin
assignment C), MSI MPG 491C OLED over USB-C, GNOME desktop mode with the
DSI panel off. Research and design only; nothing was changed on the phone.
Result: kernel patch 0145 (`msm.dp_link_policy`), measurement script
[`scripts/device/rog5-dp-power-measure`](../../scripts/device/rog5-dp-power-measure).

## Short answer

- **Lanes cost little.** The PLL and the common serdes block are shared; a
  second lane pair adds its serialisers and drivers (in 2-lane mode
  `qmp_v4_configure_dp_phy` only lowers the bias of the unused TX block,
  `TRANSCEIVER_BIAS_EN` 0x15 instead of 0x3f). Estimate for 4 x HBR2 vs
  2 x HBR2: +10 to +25 mW, under 1 % of the desktop-mode input power and
  well under 0.5 °C at the skin.
- **The rate costs more, through the voltage corner.** `sm8350.dtsi`
  `dp_opp_table` votes MMCX SVS_L1 for the 540 MHz link clock (HBR2) and SVS
  for 270 MHz (HBR). At 3840x1080@60 the DPU votes ~280 MHz (0099 floor,
  300 MHz OPP = SVS), so HBR2 alone lifts the whole MMCX rail (DPU + DP
  controller) one corner. Estimated cost of that corner: 20-50 mW.
- **Cheapest link for the current mode: 4 x HBR** (8.64 Gbit/s payload, the
  mode fills 92.5 %). Estimate vs today's 4 x HBR2: -30 to -80 mW; vs
  2 x HBR2: -20 to -60 mW. That is 1-3 % of a ~2.5-3.5 W desktop session:
  worth taking, but no heat problem either way. Every estimate has about
  ±50 % uncertainty until measured.
- Bigger levers than the link: keep the DPU pin off (`ROG5_DPU_PIN=0`, the
  460 MHz pin holds MMCX at NOM and raises the DDR votes), 100 % scale, and
  letting the monitor blank when idle.

## Link arithmetic (8b/10b)

Payload per lane = rate x 0.8: RBR 1.296, HBR 2.16, HBR2 4.32, HBR3
6.48 Gbit/s. The mode GNOME uses (journal, 2026-09-30): 3840x1080@60,
pclk 266.5 MHz, 30 bpp = 7.995 Gbit/s (24 bpp: 6.40).

| link | payload Gbit/s | fill at 30 bpp | link clock, MMCX vote | seen on the phone |
|---|---|---|---|---|
| 4 x HBR2 | 17.28 | 46.3 % | 540 MHz, SVS_L1 | yes (0136-0139, default until 0145) |
| 2 x HBR2 | 8.64 | 92.5 % | 540 MHz, SVS_L1 | yes, 35 enables (pin D / before 0136) |
| 4 x HBR | 8.64 | 92.5 % | 270 MHz, SVS | not yet (0145 default) |
| 2 x HBR | 4.32 | no | | |
| 4 x RBR | 5.18 | no (81 % at 24 bpp is no either: 6.40 > 5.18) | | |

The EDID's own 60 Hz timing (285 MHz, seen over the HDMI hub) needs
8.55 Gbit/s at 30 bpp: 99 % of 4 x HBR, above 0145's 95 % margin, so it
would stay at 4 x HBR2 unless `msm.dp_max_bpc=8` (6.84 Gbit/s, 79 %).

## What others do

| stack | policy | where |
|---|---|---|
| i915 (SST DP) | max bpp first, then the **lowest rate**, then the fewest lanes at that rate ("slow and wide") | `intel_dp_compute_link_config_wide()` in `drivers/gpu/drm/i915/display/intel_dp.c` ("Optimize link config in order: max bpp, min clock, min lanes") |
| i915 (MST, eDP < 1.4) | max rate and lanes; eDP 1.4+ tries the optimal link first and retrains at max on failure (`use_max_params`) | `intel_dp_compute_config_limits()`, `intel_dp_get_link_train_fallback_values()` in `intel_dp_link_training.c` |
| amdgpu DC | lowest rate first, lanes ascending within a rate, over the caps verified by a max-link training at detection; eDP 1.4 rate tables with ILR optimisation; `preferred_link_setting` debugfs override | `decide_dp_link_settings()`, `edp_decide_link_settings()`, `link_decide_link_settings()` in `dc/link/protocols/link_dp_capability.c` |
| nouveau | max lanes, highest rate that carries the mode first; lower configs only as training fallbacks | `nouveau_dp_train()` in `nouveau_dp.c` (rates sorted descending) |
| msm mainline, Qualcomm msm-5.4 (stock ROG5) | max rate and lanes, downshift only on training failure; stock caps multi-function (pin D) partners at 2 lanes and votes `vdd_mx` TURBO while the DP PLL is on (`lahaina-sde.dtsi` `qcom,pll-supply-entries`); mainline has no MX vote | `msm_dp_ctrl_on_link()`; stock `dp_ctrl_on()`/`dp_ctrl_link_setup()` |
| ChromeOS | no separate link policy found: the kernel driver decides (i915/amdgpu slow-and-wide, msm on trogdor/herobrine max) | |
| Android, Apple | no public documentation of the link choice; Qualcomm Android uses the downstream driver (max). Android's refresh-rate switching (SurfaceFlinger `RefreshRateSelector`, idle timer, per-app frame-rate votes) targets the built-in panel; external displays get the preferred mode (unverified for current releases) | |

Power features beyond the link:

- **PSR / PSR2**: eDP only (msm supports it for eDP panels). External DP sinks
  do not implement it.
- **Panel Replay** (DP 2.1, also for external sinks; i915 implements it in
  `intel_psr.c`): the MSI is a DP 1.4 sink (DPCD rev 0x12, extended 0x14),
  and msm has no support. Not available.
- **ALPM** (AUX-less ALPM with Panel Replay / eDP 1.5): not applicable.
- **Adaptive-Sync / VRR**: the monitor supports it (DPCD 0x0007 =
  0x40, MSA_TIMING_PAR_IGNORED; EDID range 48-144 Hz), but msm has no
  `vrr_capable` property or DPU support for a stretched vertical front porch,
  so GNOME's experimental VRR switch has nothing to enable. With VRR an idle
  desktop could fall to 48 Hz (-20 % scanout); a large DPU job for a small gain.
- **DSC**: no DSC on msm DP; not needed (every mode the DPU can drive at
  460 MHz fits 4 x HBR2 uncompressed).
- **bpc**: 10 -> 8 bpc cuts the payload by 20 %, but the lanes carry
  scrambled fill symbols anyway, so it only saves power when it moves the mode
  to a lower rate (see above; 1920x1080@120: 8.9 Gbit/s at 30 bpp needs HBR2,
  7.1 at 24 bpp fits 4 x HBR). msm has no `max bpc` connector property, so
  mutter can't choose; `msm.dp_max_bpc=8` is the knob.
- **Refresh**: the DPU core clock follows the pixel clock (0099: pclk x 1.05)
  and scanout reads 3840 x 1080 x 4 B per frame (1.0 GB/s at 60 Hz). The
  DPU's lowest OPP (200 MHz) also needs SVS in `sm8350.dtsi`, so a lower
  refresh can't lower the MMCX corner below SVS; it saves DDR bandwidth and
  GPU work for animated content. The monitor offers 3840x1080 only at 60, 100
  and 128 Hz (100 and 128 exceed the 460 MHz core clock, 0114).

## Power model and uncertainty

- **PHY**: stock `lahaina-sde.dtsi` sizes the DP PHY supplies at 115 mA on
  vdda-0p9 (L1B, 0.912 V) and 21.7 mA on vdda-1p2 (L6B): about 130 mW, an
  upper bound for 4 x HBR3 with margin. The VCO runs at 8.1 GHz for RBR, HBR
  and HBR3 and 10.8 GHz for HBR2 (stock `dp_pll_5nm.c` hsclk dividers 5, 3,
  1, 2), so the PLL costs about the same at every rate. Estimates:
  4 x HBR2 40-70 mW, 2 x HBR2 30-50 mW, 4 x HBR 30-55 mW.
- **MMCX corner**: SVS_L1 vs SVS is roughly +10 % voltage, +20 % rail power.
  With the DPU scanning out 3840x1080@60 the rail carries an estimated
  100-250 mW, so +20-50 mW at HBR2.
- **DP controller link clock domain**: 540 vs 270 MHz, a few mW.

| link | est. vs 4 x HBR2 |
|---|---|
| 4 x HBR2 | 0 |
| 2 x HBR2 | -10 to -25 mW |
| 4 x HBR | -30 to -80 mW |

Why "lowest rate, then fewest lanes" and not "fewest lanes first": the rate
decides the corner, and the corner outweighs a lane pair's static current.
Once both rates sit at the same corner (RBR vs HBR: the DPU already holds
SVS), the difference is a few mW either way. The policy follows i915 and
amdgpu for that reason, and policy 2 (fewest lanes) remains for the A/B.

## Kernel patch 0145

`patches/linux-7.2.7/0145-drm-msm-dp-ROG5-train-the-lowest-link-rate-that-carries-the-mode-dp_link_policy.patch`

- `msm.dp_link_policy` (default 1): 0 = max (old), 1 = lowest rate that
  carries the mode, then the fewest lanes (never below 2 unless the link has
  1), 2 = fewest lanes first (2 x HBR2 here, for A/B tests without a replug).
- `msm.dp_link_fill_pct` (default 95): margin for SSC downspread and
  reference clock (0.6 %, DP 2.1 2.6.4.1) and transfer unit rounding.
- Read at every link enable, i.e. every modeset. A reduced link that fails
  training, or that msm's downshifts leave too small for the mode, is
  retrained at the maximum. Mode validation and bpp still use the maximum
  link (0110, 0137, 0138 caps and `msm.dp_max_rate` unchanged). eDP and eDP
  rate tables are left alone.
- Kernel log after each enable: `DP: link policy 1: 4 lanes x 270000 kHz for
  7995000 kbit/s (max 4 x 540000)`, then the usual `DP: 3840x1080@60 ...`.
- Back to the old link at runtime: `echo 0 >
  /sys/module/msm/parameters/dp_link_policy`, then any modeset (change the
  mode, DPMS off/on, or replug).

Before it becomes the default bundle: first enable at 4 x HBR on the MSI
(picture, no underrun, no fallback line), a replug, a suspend/resume with the
monitor attached, and the USB-C HDMI hub (pin D: 2 lanes; its PCON cap
0110 keeps HBR, so 1080p60 24 bpp becomes 2 x HBR as before).

## Measurement plan (with the user and the monitor)

Needs a kernel with 0145, the monitor on the side port and GNOME desktop
mode. Copy the script to the phone (`/usr/local/bin`).

1. Fixed conditions: brightness and the monitor's own settings unchanged,
   Wi-Fi as usual, no USB devices added or removed, rog5-perf-mode noted
   (the script records cpufreq limits), 10 min warm-up in desktop mode.
2. Power source: the phone normally runs in bypass (inhibit-charge) or Full
   on the adapter, so the battery reads ~0 and the script sums V x I of the
   charger inputs (`qcom-battmgr-usb`, `-wls`). Better resolution:
   `--power=battery` (force-discharge, the fuel gauge measures; needs
   >= 30 %, restores the charger and rog5-charge-policy at the end; note
   that rog5-perf-mode "auto" sees an unplug meanwhile).
3. Noise floor: `sudo rog5-dp-power-measure sample --seconds=300` twice.
4. Idle desktop: `sudo rog5-dp-power-measure matrix` (max, narrow,
   efficient; 3 rounds in rotated order; 45 s settle + 120 s each, ~25 min).
   Each retrain is a mutter DPMS off/on, which re-enables the CRTC and
   retrains with the policy just set; the script checks the kernel's link
   line. Expected: MMCX perf_state 192 (SVS_L1) for max/narrow, 128 (SVS) for
   efficient; power efficient < narrow <= max.
5. Video: the same with `--load='mpv --fs --loop=inf <file>'`.
6. Refresh/resolution: select a mode in GNOME Settings, then `sample
   --label=<mode>` (3840x1080@60 vs 1920x1080@60 vs 2560x1440@60).
7. bpc: `echo 8 > /sys/module/msm/parameters/dp_max_bpc`, DPMS cycle,
   `sample --label=8bpc`; back to 0.
8. On a kernel without 0145: `--retrain=manual` with `msm.dp_max_lanes=2`
   and a replug for 2 x HBR2.

Read the summary's per-round paired deltas: a difference under ~2 sd is not
resolved. Record results in `test-results/`.

## Desktop-side settings

| setting | recommendation | expected effect |
|---|---|---|
| mode | 3840x1080@60 (the widest mode the DPU drives; 5120x1440@60 and @100 exceed 460 MHz) | - |
| scale | 100 % (81 ppi on the 49" panel). Fractional scaling makes mutter render at the next integer scale and scale down: an extra full-screen GPU pass and larger buffers per frame | tens to hundreds of mW while content changes |
| VRR | not offered on msm DP; leave the experimental feature off | - |
| 10 vs 8 bpc | keep 10 at 3840x1080@60 (same link); `msm.dp_max_bpc=8` only where it drops a rate (e.g. 1080p120) | ~0 here |
| DPU pin | keep `ROG5_DPU_PIN=0` | pinning costs far more than any link choice |
| idle | GNOME blanks after 10 min (DPMS off turns the link and PHY off); shorter if acceptable | full DP + DPU power while blanked |
| fullscreen video/games | fullscreen lets mutter scan the client buffer out directly (no composition pass) | GPU work per frame |

## Review (GPT-6.1-Sol, read-only)

[2026-09-30-gpt-6.1-sol-dp-link-policy.md](2026-09-30-gpt-6.1-sol-dp-link-policy.md): no P1
(no clock/PHY imbalance or unclocked access on the fallback paths; TU, MSA,
audio and link maintenance use the trained `link_params`; RBR's 810 MHz
pixel parent is supported). Fixed in v2:

- msm's training loop reports success when its retries run out (the last
  reinitialisation's 0). For a reduced link this now counts as a failure, so
  0145 falls back to the maximum; the maximum link keeps the old flow
  (on_stream retrains once more).
- A reduced link that msm downshifted is kept only within
  `dp_link_fill_pct`, not at 100 %.
- Script: every restore step runs on its own and the record stays until all
  succeeded; a failed `systemctl stop rog5-charge-policy` aborts before
  force-discharge; a lock keeps runs and `restore` apart; the DPMS off/on has
  a marker and `restore` powers the monitors on and applies the restored
  policy with a modeset; the workload's process group is killed (TERM, then
  KILL); `/dev/kmsg` retries only EPIPE; windows where 0145 fell back are
  marked (FB) and listed apart from the ones that kept the reduced link.

Not changed (inherited, stated in 0145): the maximum link's own downshifts
can end below the mode's bandwidth, and DP CTS link-training requests change
`link_params` without retraining the PHY (only reachable with compliance
equipment). Sol would ship with `dp_link_policy=0` until 4 x HBR has been
checked on the monitor (picture, underruns, replug, resume). 0145 keeps 1 as
the default as asked; that check belongs to the RAM trial before the kernel
becomes the default bundle, and `dp_link_policy=0` plus a modeset is the
runtime way back.
