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
