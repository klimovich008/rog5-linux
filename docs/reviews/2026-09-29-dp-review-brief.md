# Review request: SM8350 DP alt mode trains but the monitor never locks

Read-only analysis. Do not run anything against the phone, do not modify
files. Answer in text. Challenge the reasoning below; look from angles not
covered yet.

## Setup
- ASUS ROG Phone 5 (SM8350), mainline Linux 7.2.7 + our patches, side USB-C
  port (primary USB, combo QMP PHY 0x88e8000, DP controller ae90000, DPU 7.0).
- USB-C hub with HDMI out -> MSI MPG 491C OLED. The same hub + monitor work
  from a Steam Deck (amdgpu).
- Orientation: pmic_glink_altmode -> gpio-sbu-mux (TLMM167 enable active-low,
  PM8350C GPIO1 select) and QMP combo PHY orientation-switch (our DT overlay
  dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso). The stock ASUS DT
  uses the same GPIOs (qcom,aux-en-gpio = TLMM167, aux-sel = PM8350C GPIO1,
  pcie-mux-en = TLMM173 which is already high).

## Observations (see modeset-dmesg.txt in this directory, drm.debug=0x106)
- DPCD 0x000: 14 14 c2 01 00 15 01 81 00 01 00 01 08 (rev 1.4, HBR2, 2 lanes,
  TPS3, enhanced framing, downspread supported, branch with 1 HDMI port).
  0x080: 0b f0 02 1f (HDMI, HPD aware, 600 MHz TMDS, 12 bpc max).
- Source writes: 0x100=14 (HBR2), 0x101=82 (2 lanes + EF), 0x107=10 01
  (0.5% downspread claimed, 8b/10b), TPS1 then TPS3, then 0x102=00.
- Link training: passes first try at vswing 1 / pre-emph 0; lane status
  77 00 81 (CR/EQ/symbol lock on both lanes, interlane aligned). Trained
  twice per enable (on_link, then again in on_stream with force_link_train).
- dp_video_ready interrupt fires, "mainlink READY".
- MVID/NVID for 1080p60: mvid=0x4641 nvid=0xff78 (148.5/540 correct).
- About 18.5 s after video_ready the branch drops HPD for ~1.1 s (long
  pulse, not IRQ_HPD), then replugs; the cycle repeats forever. Monitor
  "tries to receive an image but shows nothing" (it detects activity but
  never locks).
- SINK_STATUS (0x205) is only read during training (00); never read while
  streaming. No DPCD reads happen after video starts.

## Ruled out by experiment (each one tested live on the monitor)
1. Mode/bandwidth: 3840x1080@60 (30 bpp, 2 LM 3D merge) and 1920x1080@60.
2. Colour depth: 10 bpc and forced 8 bpc (msm.dp_max_bpc=8; MISC0 0x21).
3. PCON output mode: 0094 writes DPCD 0x3050=1 (HDMI) before link bring-up;
   readback 0x01. No change.
4. Wide bus: msm.dp_widebus=0 (DPU INTF and DP ctrl both off). No change.
5. DPU pipeline: msm.dp_tpg=1 (DP controller's own checkered test pattern,
   widebus off, 1080p60) -> still no image. So the fault is after the DPU:
   DP controller stream config / MSA / timing, PHY analog levels or lane
   data mapping, SSC, scrambler, or something the converter needs.
6. No DPU underruns or IRQ timeouts.

## Code
- Patched source: ~/.local/state/rog5-kernel-7.2.7-build-r75/source
  (drivers/gpu/drm/msm/dp/, drivers/phy/qualcomm/phy-qcom-qmp-combo.c,
  drivers/soc/qcom/pmic_glink_altmode.c, drivers/usb/typec/mux/gpio-sbu-mux.c)
- Our patches: ~/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/
  (0080, 0091, 0093, 0094, 0095 touch DP/DPU)
- Stock ASUS 5.4 downstream (working DP on this phone):
  ~/.local/state/rog5-kernel-compare-20260927/stock
  techpack/display/msm/dp/ (dp_catalog_v420.c, dp_ctrl.c, dp_link.c,
  dp_panel.c, dp_pll_5nm.c or similar), and
  arch/arm64/boot/dts/vendor/qcom/display/lahaina-sde.dtsi (sde_dp node),
  stock DTBO decompiled: ~/.local/state/rog5-stock-payload-20260927/dtbo/dtbo0.dts
- Earlier research: earlier-research-COMBINED.md, earlier-fable-opinion.md.

## Questions
1. With TPG also failing, rank the remaining causes with evidence (file:line
   in mainline vs stock). Compare especially: DP PHY/PLL programming for
   5nm/v4-v5 QMP combo at HBR2 (SSC, TX drive/emphasis tables, lane
   polarity/swap for SM8350 in both orientations, DP_PHY_MODE, SPARE0),
   DP controller mainlink/config (scrambler, enhanced framing, MISC/MSA
   fields, sync polarity, TU/valid boundary), link clock vs pixel clock
   source (dispcc DP pixel clock parent, stream clock rate actually
   achieved), and anything the stock driver does after link training
   that mainline skips.
2. Is "lane data swapped within the pair" plausible given training passes
   with interlane alignment? How would it show? How to test cheaply?
3. What does a ~18.5 s HPD drop from an HDMI PCON usually indicate?
4. Propose the 3 most informative next experiments, ideally runtime knobs
   or DPCD reads we can add in one kernel build (e.g. read 0x200-0x205,
   0x2003/0x2004 ESI, 0x3036+ PCON status, CRC via 0x246/0x240 TEST_SINK,
   PHY test pattern). Predict outcomes under each hypothesis.
5. If you find a concrete bug, give the minimal patch.
