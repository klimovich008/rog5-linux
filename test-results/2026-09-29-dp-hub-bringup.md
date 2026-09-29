# DP alt mode through a USB-C HDMI hub, 2026-09-29 (r171-r175)

Hub: USB-C multiport with HDMI (DP 1.4 branch, HDMI PCON: DPCD 0x80 =
0b f0 02 1f, 600 MHz TMDS, 12 bpc; 2 DP lanes, pin assignment D). Monitor
MSI MPG 491C OLED (32:9). The same hub + monitor work from a Steam Deck.

## Results
| Build | Change | Monitor |
|---|---|---|
| r170 | orientation to SBU mux/PHY (DT) | trains, dark, HPD drops every ~20 s |
| r171 (0093) | cap bpp at branch max bpc | no change (PCON reports 12 bpc) |
| r172 (0094) | PCON HDMI mode (0x3050=1), dp_max_bpc knob | no change at 8/10 bpc |
| r173 (0095) | dp_widebus=0, dp_tpg=1 knobs | no change at HBR2 |
| r174 (0096) | sink status log + polarity/SSC/safe-exit/lane-map/rate knobs | see below |
| r175 (0097) | dpu_rm_top_down, dp_min_v/plevel, qmp dp_pol_inv knobs | test pending |

r174 sink log (0x200-0x207, 0x210-0x213, ESI, 0x3036):
- HBR2: lane status 77 00 81 but ~25k symbol errors/s on lane 1 (0x212/0x213
  valid bit set); second training pass settles at swing 0 / pre-emph 0.
- HBR (dp_max_rate=270000): zero symbol errors. SINK_STATUS 0x205 stays 00
  in every configuration; this PCON does not seem to report it. No CRC
  support (0x246 = 0).
- HBR + TPG: the monitor shows the DP controller's checkered test pattern.
  The link, PHY, converter and HDMI side work.
- HBR + DPU stream at 1920x1080: the monitor locks and shows solid blue, the
  DPU INTF underflow colour (dpu_encoder_phys_vid underflow_clr = 0xff), and
  HPD stops cycling. The DPU path feeding DP starves.
- HPD cycle: kprobes on pmic_glink_altmode_callback show the ADSP reporting
  hpd_state 1 for ~19-20 s then 0 for ~1.1 s; hpd_irq is never set (the lost
  IRQ_HPD theory is refuted). The cycle stops once the monitor locks.
- 1024x768 (single mixer): no lock, HPD cycles (the monitor rejects the mode).
- Clock readback: dp pixel 74.25 MHz (1080p, widebus), link 540/135 MHz.

## Next
- r175: msm.dpu_rm_top_down=0 (DP on mainline LM_2/3 -> PP_2/3 instead of
  0080's LM_4/5 -> PP_4/5 -> MERGE_3D_2, CTL_5) at HBR 1080p.
- HBR2 margin: msm.dp_min_vlevel=1..2, then phy_qcom_qmp_combo.dp_pol_inv.
- Mode validation ignores dp_max_rate (3840x1080 accepted at HBR).
- Phosh 0.57 segfaults in a GObject notify handler on output removal
  (phosh+0x6c39c); phoc segfaults in a wl request handler when wlr-randr
  hits a vanished output (test-induced).

Reviews: docs/reviews/2026-09-29-gpt-6-astra-dp-review.md; Fable review and
the Steam Frame research in the session scratchpad (Valve publishes no Frame
kernel source; no DP work there).

## Result (r175, 13:13)
- **Picture works at HBR.** The user sees browser windows on the external monitor: 1920x1080@60, 2 lanes x 2.7 Gbit/s, 24 bpp, widebus on, mainline DPU block order. The display core runs at the normal 345 MHz; a fixed 460 MHz was not needed.
- The earlier "blue square" was the empty extended Phosh desktop (32:9 monitor, 16:9 mode, centred), not DPU underflow.
- Persistent setting: /etc/tmpfiles.d/rog5-dp.conf (configs/tmpfiles/rog5-dp.conf) writes msm.dp_max_rate=270000 at boot. msm loads from the ramdisk, so modprobe.d does not apply.
- Open:
  - HBR2 lane-1 errors, needed for 3840x1080. Floor tests were inconclusive because phoc fell back to 3840x1080 on mode switches.
  - Mode validation ignores the rate cap.
  - Whether 0080 top-down is safe to keep; the picture works with dpu_rm_top_down=0.
  - The Phosh launch splash outlives Chromium's startup.

## GNOME desktop mode on DP (14:00-14:10)
- rog5-kms-reset before GNOME fixed "switching CRTC directly" (plane-0 left on
  the panel CRTC by Phosh): 0 failed flips, and the scanout captured with
  rog5-kms-grab shows a correct GNOME frame.
- **But the monitor shows solid underflow blue:** DPU INTF_0 underrun IRQ
  [0,24] fires on every frame (+198 underruns for +198 vsyncs while the
  pointer moved). mutter renders 10-bit XR30 (linear) buffers; Phosh/phoc
  (XR24) gave a picture on DP at 13:13, and the first GNOME test (13:36)
  worked before the KMS reset put DP on crtc-0.
- Next test: modetest on DP XR24 vs XR30, counting [0,24]/[0,25]. `-M msm`
  opens card0 (GPU only; GetResources fails) and `-D /dev/dri/card1` is
  taken as a bus id; find the right device argument. Then force mutter to
  8 bpc or fix the DPU 2101010 fetch.
- GNOME session: the power key tried to suspend, and the rog5-server
  inhibitor made polkit ask for a password; power-button-action is now
  'nothing' in GNOME. GNOME idle-delay is 600 s, and a GNOME lock hands over
  to the Phosh lock screen.
