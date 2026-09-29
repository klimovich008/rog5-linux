# Review request (follow-up): SM8350 DP alt mode -> HDMI, remaining issues

Read-only analysis and discussion. Do not run anything against the phone and
do not modify files. Answer in text. Challenge our reasoning, rank causes,
and propose the smallest decisive experiments. Earlier today's review of the
"no picture" problem is `docs/reviews/2026-09-29-gpt-6-astra-dp-review.md`
(brief: `2026-09-29-dp-review-brief.md`); read both first.

## Where we are now (kernel bundle r188 = kernel r91-splash)

Setup: ASUS ROG Phone 5 (SM8350, DPU 7.0), mainline 7.2.7 + our patches
(`patches/linux-7.2.7/series.production`), side USB-C DP alt mode -> USB-C
hub with an HDMI PCON (DPCD 0x80 = 0b f0 02 1f, 12 bpc, 600 MHz TMDS) ->
monitor. GNOME "desktop mode" (mutter, XR30 linear buffers) or Phosh/phoc
drive it. Findings log: `test-results/2026-09-29-dp-hub-bringup.md`.

What fixed the picture (all in series.production):
- 0093 cap bpp at the branch's downstream max bpc; 0094 PCON HDMI mode
  (DPCD 0x3050=1) before link bring-up, DVI 8-bit cap, `msm.dp_max_bpc`;
  0095-0097 debug knobs (widebus, TPG, polarity, SSC, lane map, max rate,
  top-down RM, vlevel/plevel, PHY polarity) and sink-status snapshots;
  0098 mode_valid uses link_pclk_khz (only YUV420 halves it); 0099 DPU core
  clock floor = mode clock for video-mode encoders; 0100
  `dpu_video_min_bw_kbps` (default 4 GB/s ab+ib floor for video CRTCs);
  0101 vote bandwidth in dpu_crtc_enable before the encoder enables;
  0106 (new, untested with a monitor) NoC QoS urgency forwarding for
  qxm_mdp0/1 (mmss_noc 0x16000/0x16080) and qnm_mnoc_hf (gem_noc
  0x23000/0x63000), stock lahaina values, programmed by icc-rpmh at probe.
- DT: `dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso` caps the link
  at HBR (`link-frequencies = <1620000000 2700000000>`), data-lanes <0 1>;
  tmpfiles `configs/tmpfiles/rog5-dp.conf` sets msm.dp_max_rate=270000.

## Open issues

1. **DP-only first-enable underrun latch.** When DP is the only output
   (GNOME desktop mode; the DSI panel off), the first enable latches a DPU
   underrun (INTF_0 underrun IRQ [0,24] counts up in debugfs core_irq; the
   monitor shows the underflow colour, blue, 0xff) in normal perf mode. It
   stays latched until a full disable. A pinned core_perf avoids it:
   `configs/systemd/rog5-gnome.service` ExecStartPre writes
   fix_core_clk_rate 460000000, fix_core_ab_vote / fix_core_ib_vote 15500000,
   perf_mode 2 before mutter starts (and perf_mode 0 afterwards). Trace
   (0101) shows the bandwidth votes now precede the encoder enable, but that
   alone did not fix it. Stock (msm-5.4 SDE) uses a 2.5 GB/s static ib floor
   plus NoC QoS urgency forwarding (now 0106) and a different creq LUT
   (stock 0x0011223344556677). Questions: which of 0106 / creq/danger/safe
   LUTs / VBIF QoS remap / OT limits / CDP / prefill-lines / rotator-less
   fetch timing at first enable explains a *latched* underrun that a high
   clock+bandwidth pin prevents? What minimal experiment separates clock
   from bandwidth from QoS? Is the latch itself (never recovering) a driver
   bug (e.g. missing INTF/CTL reset or underrun recovery on SM8350)?
2. **HBR2 lane-1 symbol errors.** At HBR2 (5.4 Gb/s) training passes but
   lane 1 shows symbol errors, so we cap at HBR (1080p60 fits; 3840x1080 and
   4K don't). Same hub/monitor fine from other hosts at HBR2. Candidates:
   QMP combo PHY DP swing/pre-emphasis tables for SM8350 vs stock
   (`kernel-src/msm-5.4` in the archive checkout at
   /home/deck/Projects/rog-phone-linux-migration, read-only), SSC, lane
   mapping with the flipped orientation, AUX/SBU mux, PHY PLL settings at
   HBR2. What would you compare first and how would you test it cheaply?
3. **Hub audible noise** (coil whine) while DP runs. Anything on the phone
   side (e.g. link rate/SSC/refresh) worth trying, or purely the hub?
4. **Phosh/phoc side:** `/etc/phosh/phoc.ini` pins `[output:DP-1] mode =
   1920x1080@60Hz`; phosh 0.57 segfaults on monitor unplug (being fixed
   separately). Any kernel-side hotplug behaviour (HPD long-pulse handling,
   connector state on unplug) that could provoke compositor crashes?

Files to read: the patches above, `drivers/gpu/drm/msm/disp/dpu1/*` and
`drivers/gpu/drm/msm/dp/*` in the r91 build tree
(`/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source`),
`drivers/interconnect/qcom/sm8350.c`, `drivers/phy/qualcomm/phy-qcom-qmp-combo.c`,
the stock SDE/DP code in the archive's msm-5.4 tree, the DT overlays, and the
test-results notes. Output: ranked hypotheses with evidence, a concrete test
plan (each step: what to change, what to observe, pass/fail), and any bug you
see in our DP/DPU patches.
