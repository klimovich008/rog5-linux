I found **a definite sync-polarity bug, a misleading bpp log, and several useful stock/mainline differences—but no proven explanation for the black screen**. The best next step is to observe the receiver during streaming and read back the actual clock/controller configuration.

Everything was read-only. `modeset.b64` decompresses byte-for-byte to `modeset-dmesg.txt`.

**First, three corrections to the evidence**

- The supplied log captures `widebus 1, tpg 0`. I accept the brief’s separate TPG result, but this file does not validate that experiment. Verify the TPG register enables, not just the module parameter.
- `bpp 36` in the summary is misleading. [dp_panel.c:775](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/gpu/drm/msm/dp/dp_panel.c:775) clamps the panel’s bpp to 24; the controller uses that value. Patch 0095 logs the unclamped display-mode copy.
- The second training pass actually succeeds at **voltage 0 / emphasis 0**. The first pass needed voltage 1. Also, the two complete intervals from video-ready to disconnect are approximately **17.51 s and 19.09 s**, rather than a fixed 18.5-second timer.

**1. Ranked remaining causes**

These rankings assume the separate TPG test really enabled the generator with widebus disabled.

| Rank | Cause | Assessment |
|---|---|---|
| 1 | Stream timing/clock inconsistency | TPG still depends on the stream clock, MSA and packetizer. Correct calculated M/N does not prove the actual clock. There is also a definite polarity-copy bug. |
| 2 | Controller initialization/transition difference | Stock programs a lane-dependent mainlink threshold that mainline omits. Scrambler and framing register readback are missing. |
| 3 | SSC declaration versus actual PHY state | Mainline requests/advertises SSC, but this QMP implementation never acts on the SSC option. Stock requests no downspread. |
| 4 | Logical lane ordering | Training does not eliminate this, but inspected stock and mainline mappings agree, reducing its probability. |
| 5 | Marginal analog link or converter/HDMI-side recovery | Still possible because no streaming receiver status or error counters were collected. The HBR2 programming comparison provides little evidence for a gross PHY-table error. |

The important comparisons follow.

**PHY/PLL: substantially closer to stock than the “v4/v5 versus 5nm” names suggest.**

Mainline selects the v4 DP PLL tables, v5 TX table and v4 configuration routines for SM8350 in [phy-qcom-qmp-combo.c:2794](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/phy/qualcomm/phy-qcom-qmp-combo.c:2794). That mixture is consistent with the stock register programming; replacing it wholesale with a differently named “5nm” table would be unjustified.

- HBR2 PLL values match: `HSCLK_SEL=01`, `DEC_START=8c`, fractional bytes `00/00/0a`, lock compare `1f/1c`, lock enable `08`, VCO divider `02`. Compare [mainline:1248](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/phy/qualcomm/phy-qcom-qmp-combo.c:1248) with [stock dp_pll_5nm.c:214](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_pll_5nm.c:214).
- The mainline v5 TX initialization matches stock’s 5nm TX initialization, including interface select `3b`, resistance offsets `11/11`, and band `04`: [mainline:1311](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/phy/qualcomm/phy-qcom-qmp-combo.c:1311), [stock:284](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_pll_5nm.c:284).
- HBR2 drive/emphasis tables match stock. At voltage 1/emphasis 0, both produce **DRV `29`, EMP `22`**, including mux-enable bits. At 0/0, both produce `22/20`. Mainline’s temporary default drive `27` differs from stock’s update routine default `2a`, but the selected table values overwrite it.
- Orientation programming also matches:

| Two-lane configuration | Normal / CC1 | Reverse / CC2 |
|---|---:|---:|
| `DP_PHY_MODE` | `5c` | `4c` |
| `DP_PHY_PD_CTL` | `75` | `6d` |
| TX0/TX1-block bias enables | `15 / 3f` | `3f / 15` |
| Both high-Z driver controls | `10` | `10` |
| Default polarity inversion registers | `0a / 0a` | `0a / 0a` |

Compare [mainline mode configuration:3155](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/phy/qualcomm/phy-qcom-qmp-combo.c:3155) and its PHY setup at 3471 with [stock PLL:333](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_pll_5nm.c:333) and [stock late PHY initialization:471](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_catalog.c:471). I found no DP P/N-swap override in the supplied stock DTS/DTBO.

**SPARE0 is not an obvious missing hardware requirement.** Stock writes lane count/orientation there, then its separately implemented PLL driver reads it into software variables: [writer:206](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_catalog_v420.c:206), [reader:170](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_pll_5nm.c:170). Mainline already holds those variables in the combined driver. This evidence supports treating SPARE0 as a software handoff, not blindly adding its write.

**SSC is a real inconsistency.**

[Mainline dp_ctrl.c:1801](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/gpu/drm/msm/dp/dp_ctrl.c:1801) requests SSC, and line 1639 advertises downspread at DPCD `107`. The combo PHY copies the options but never consumes `dp_opts.ssc`; its selected DP tables do not program SSC.

Stock instead writes `DOWNSPREAD_CTRL=0` at [dp_ctrl.c:536](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_ctrl.c:536). Its optional PLL SSC programming uses period `0136` and HBR2 step `085c`, gated by `qcom,ssc-feature-enable`; that property was absent from the inspected stock DTS/DTBO.

Therefore, **neither “SSC is enabled” nor its actual hardware state is established by the log**. Read the SSC registers. A coherent no-SSC configuration is a cheap stock-equivalence test, although this discrepancy alone is not strong proof of the failure.

**Controller/MSA: several checks pass; two differences deserve attention.**

- `CONFIGURATION_CTRL=4157` and `MISC0=21` agree with stock’s RGB, 8-bpc, two-lane, enhanced-framing, synchronous/static-MVID setup: [stock dp_panel.c:2721](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_panel.c:2721). ASSR is clear.
- The logged TU allocation is correct in aggregate: TU size 32; one TU with 14 valid symbols and four with 13 gives **13.2 symbols/TU**, exactly `32 × 148.5 × 3 / (540 × 2)`. This lowers suspicion of a gross bpp/TU arithmetic error; it does not validate every FIFO timing parameter.
- **Sync polarity is lost.** [dp_display.c:1500](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/gpu/drm/msm/dp/dp_display.c:1500) computes `h_active_low`/`v_active_low`, but [the copy at line 597](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/gpu/drm/msm/dp/dp_display.c:597) omits them. [dp_panel.c:710](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/gpu/drm/msm/dp/dp_panel.c:710) subsequently programs the panel’s zero-initialized fields. The logged mode flags are `0xa`, requesting negative H/V sync. Expected width/polarity is therefore `8005802c`, whereas this path constructs `0005002c`. Stock preserves the requested polarities. This is a definite bug, but polarity alone does not necessarily prevent a converter locking.
- **Stock sets `MAINLINK_LEVELS`’ safe-to-exit threshold to 8 for two lanes**: [dp_catalog.c:2204](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_catalog.c:2204). Mainline only writes this register in PHY-test paths. Its normal path also explicitly sets `FB_BOUNDARY_SEL`, unlike stock’s mainlink enable. Read both registers and test these differences individually.
- Mainline’s normal enable preserves the scrambler-bypass bit rather than explicitly clearing it. That is a reason to **read back bit 4**, not evidence that it is currently set.

**Clock source: intended wiring is correct; achieved rate is unproven.**

The DTS assigns the link clock to the PHY link output and both pixel sources to the PHY VCO-divider output. At HBR2, the intended rates are **540 MHz link**, **1.35 GHz pixel parent**, and **148.5 MHz stream pixel with widebus off**.

The critical distinction is that [mainline MSA generation:2398](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/gpu/drm/msm/dp/dp_ctrl.c:2398) computes M/N from requested rates. [Stock:168](~/.local/state/rog5-kernel-compare-20260927/stock/techpack/display/msm/dp/dp_catalog_v420.c:168) reads the DISPCC pixel M/N registers.

Moreover, [clk_rcg2_dp_set_rate():1780](~/.local/state/rog5-kernel-7.2.7-build-r75/source/drivers/clk/qcom/clk-rcg2.c:1780) preserves the existing HID divider. A non-unity divider is worth checking. PHY clock `recalc_rate` itself returns values from software options, not frequency measurements.

Read the SM8350-adjusted pixel RCG at **`af021a8`**, its CFG/M/N/D registers, the selected parent and `clk_get_rate()`. Correct printed MVID/NVID cannot replace that check.

Stock’s post-training extras include conditional FEC/DSC setup and VSC colourimetry packets. Neither is inherently required for this ordinary RGB SST mode. I found no universal missing “enable HDMI video” operation after training.

**2. Can the two logical lanes be swapped despite successful training?**

**Yes.** Deskew/alignment does not prove correct logical byte ordering. A permutation can preserve decodable training symbols yet corrupt striped MSA and pixel data during video. It could produce clean physical status with no stream synchronization, or corrupted colours/pixels if sufficient framing survives. This follows from the separation between link training and stream reconstruction in the [DisplayPort specification](https://glenwing.github.io/docs/DP-1.2.pdf).

However, the inspected mapping is identity in both implementations: stock writes `e4`; mainline’s `<0 1>` is completed to `<0 1 2 3>`. Thus it remains plausible, not the leading source-backed discrepancy.

Cheap test: add a next-modeset logical-map override and compare **`e4` against `e1`**, swapping lanes 0/1 while leaving 2/3 unchanged. Apply it before training and retain it through streaming; mainline’s source-parameter setup otherwise overwrites it. Repeat both plug orientations.

Keep this distinct from swapping **P/N within a differential lane**, which is a polarity/receiver-compensation question.

**3. Meaning of the recurring HPD drop**

There is no standard “18.5-second PCON failure code.” A roughly one-second low interval is a disconnect/reconnect-class event; ordinary DP link-loss recovery normally uses IRQ_HPD. [DisplayPort specification, link maintenance and HPD](https://glenwing.github.io/docs/DP-1.2.pdf).

My inference is **a recovery loop somewhere in the converter/monitor/Type-C chain**: stream-acquisition timeout, downstream HDMI HPD cycling, converter reset, or power/PD disturbance. The log establishes that Linux received disconnect notifications; it does not prove which device originated them.

Correlate the first failure with raw GLINK HPD/IRQ notifications, sink status, USB disconnects and PD events. The absence of AUX reads while streaming is a diagnostic blind spot, not itself proof of broken maintenance when no IRQ was delivered.

**4. Three most informative next experiments**

**Experiment 1 — Observe the receiver across the training-to-video transition.**

Add bounded delayed snapshots at roughly 20 ms, 100 ms, 1 s, 5 s and 15 s, serialized with teardown:

- `200–207`: sink count, service flags, link status, sink synchronization, adjustment requests.
- `210–213`: lane 0/1 symbol-error counts, including validity bits.
- `2002–2005` and `200c–200f`: ESI events and mirrored link/sink status. **Include `2005`**; `2003/2004` alone miss stream/HDMI-link event bits.
- `3036–303b` only with capability-aware interpretation. `303b` is HDMI-link-active; `3036` is post-FRL status, not a universal TMDS-lock register. A legacy converter’s zero/NACK is inconclusive.
- CRC: check support at `246`; start through **`270`**, then read `240–246` and verify the count advances. `246` is not the start register. These addresses are defined in [drm_dp.h](~/.local/state/rog5-kernel-7.2.7-build-r75/source/include/drm/display/drm_dp.h:932).

Predictions:

| Observation | Strongest implication |
|---|---|
| Link status degrades or valid symbol-error counts rise | PHY integrity, power, or transition problem |
| Physical link stays good; `205` never synchronizes | Clock/MSA/framing/scrambler/lane-order problem |
| Sink synchronizes and changing test images produce repeatable corresponding CRCs | DP stream reception works; concentrate on converter output/HDMI |
| AUX becomes unavailable alongside USB/PD events | Reset or power-path problem |

`205`’s receive-port bit describes stream regeneration/synchronization, not merely physical training. [DisplayPort specification, SINK_STATUS](https://glenwing.github.io/docs/DP-1.2.pdf).

**Experiment 2 — Verified TPG plus controlled stock-equivalence tests.**

Use 1080p, effective 24 bpp, widebus off. Read back TPG control, BIST enable, timing-engine enable, interface configuration, MSA registers, mainlink control/levels, and actual pixel RCG configuration.

Then vary **one item per modeset**:

1. Correct the polarity-copy bug.
2. Program the stock two-lane safe-to-exit threshold, 8.
3. Select coherent SSC-off operation: PHY SSC demonstrably disabled and DPCD `107=00`.

If pixel clock readback is wrong, fix that before interpreting the other trials. A clock/threshold fix should allow `205` and CRC progress without necessarily changing training status. An SSC-only improvement isolates a converter/clock-tolerance interaction. If scrambler bypass reads set, clear it for normal video and repeat.

**Experiment 3 — Lane-map/rate matrix.**

At a fixed **720p60 RGB8** mode, compare two lanes at HBR2 versus HBR, then identity versus swapped logical lanes, in both orientations. This mode avoids a bandwidth-edge explanation.

- A specific map consistently restoring video supports lane ordering.
- HBR curing valid symbol errors supports signal integrity or rate-dependent PHY behaviour.
- HBR curing video with clean error counters at both rates points more toward clock/TU/rate-specific controller configuration.
- Orientation-specific failure implicates lane-group routing or electrical asymmetry.
- No changes, with stable sink synchronization/CRCs, moves suspicion downstream.

A coordinated scrambled symbol-error test can follow if error counters implicate the PHY. Simply transmitting PRBS7 and observing a black monitor proves nothing; the receiver must be configured to measure that pattern.

**5. Minimal patches for the concrete bugs**

The polarity fix belongs in `msm_dp_display_set_mode()`:

```diff
--- a/drivers/gpu/drm/msm/dp/dp_display.c
+++ b/drivers/gpu/drm/msm/dp/dp_display.c
@@
 	drm_mode_copy(&dp->panel->msm_dp_mode.drm_mode, &mode->drm_mode);
 	dp->panel->msm_dp_mode.bpp = mode->bpp;
+	dp->panel->msm_dp_mode.h_active_low = mode->h_active_low;
+	dp->panel->msm_dp_mode.v_active_low = mode->v_active_low;
 	dp->panel->msm_dp_mode.out_fmt_is_yuv_420 = mode->out_fmt_is_yuv_420;
```

Correct patch 0095’s summary to report the effective depth:

```diff
-		 msm_dp_display->msm_dp_mode.bpp,
+		 msm_dp_display->panel->msm_dp_mode.bpp,
```

These are source-supported fixes, **not a claim that the display failure is solved**. The decisive missing evidence is receiver synchronization and clock/register readback during the interval when the screen remains black.