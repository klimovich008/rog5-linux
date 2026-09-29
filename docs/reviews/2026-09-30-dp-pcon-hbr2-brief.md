# Review request: why the USB-C HDMI hub shows nothing at HBR2 (and gets stuck)

Read-only analysis. Do not modify files and do not run anything against the
phone. Read as much of the code below as you need; pinpoint concrete causes
in our driver/patches, rank them, and give the smallest decisive experiments
and exact code changes (as diffs against the files named) that would make
the phone drive this hub at HBR2. Challenge our reasoning.

## Setup

- Phone: ASUS ROG Phone 5 (SM8350), mainline Linux 7.2.7 + our patches
  (`patches/linux-7.2.7/series.production` in this repository; the patched
  source tree is `/home/deck/.local/state/rog5-kernel-7.2.7-build-r93/source`).
  Side USB-C port in DP alt mode (2 DP lanes + USB 2.0) -> USB-C hub with
  an HDMI protocol converter (PCON) -> MSI MPG 491C OLED (EDID decoded in
  `docs/reviews/2026-09-30-msi-mpg491c-edid.txt`: 3840x1080@60 285 MHz,
  3840x1080@100 453 MHz, 1920x1080@120 297 MHz, HDMI max TMDS 340 MHz,
  HF-VSDB max TMDS character rate 600 MHz, SCDC present).
- Branch DPCD (from our logs): 0x000 = 14 14 c2 01 00 15 01 81 00 01 00 01 08
  (DPCD 1.4, max HBR2, 2 lanes, TPS3, downspread, 1 downstream port);
  0x080 = 0b f0 02 1f (HDMI, HPD aware, max TMDS 600 MHz, max 12 bpc).
- The same hub + monitor work from a Steam Deck (amdgpu, SteamOS); the
  negotiated link settings there are not captured yet.

## What we observe

1. **HBR (2.7 Gb/s x 2 lanes), 1920x1080@60, 8 bpc**: picture, user-confirmed,
   stable. Kernel line: `DP: 1920x1080@60 pclk 148500 kHz, 2 lanes x 270000 kHz, bpp 24, widebus 1`.
2. **HBR2 (5.4 Gb/s x 2 lanes)** with a DTB whose DP endpoint
   `link-frequencies` includes 5.4 GHz (`dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso`
   has the HBR-only production value):
   - Training passes first time; lane status `200:41 00 77 00 01 00 00 00`,
     `200c:77 00 01 00` (CR/EQ/symbol lock both lanes, interlane aligned);
     symbol-error counters (0x210..) show a burst in the first second after
     training, then 0 at the 5 s and 15 s snapshots (read-to-clear).
   - Modes: 1920x1080@60 at 30 bpp and 24 bpp, 3840x1080@60 at 30 and 24 bpp.
     DPU scanout verified (framebuffer grab of the plane shows the desktop),
     no DPU underruns after the switch.
   - **Monitor shows nothing** in every case.
3. **After the HBR2 attempts, HBR 1080p60 8 bpc also shows nothing**, even
   with the DP controller's own test pattern (msm `dp_tpg`), until the hub was
   physically reconnected and the phone rebooted. So the PCON ended up in a
   state our driver does not recover from.
4. The PCON setup we do: patch 0094 writes DPCD 0x3050 = 1 (HDMI mode)
   before link bring-up and reads it back; bpc capped by 0x080 max bpc
   (0093); nothing else is written to the PCON (no 0x305A/0x305B HDMI link
   config, no FRL, no SCDC/scrambling handling, no DP_PROTOCOL_CONVERTER_CONTROL
   beyond that one write). DPCD snapshots after training at HBR and HBR2 are
   byte-identical (`2002:41 00 00 00`, `3036:00 00 00 00 00 00`).

Hypotheses to test and rank (add your own):
- HBR2 as such is fine, but with the higher link rate the PCON is expected
  to run HDMI 2.0 (TMDS > 340 MHz needs scrambling; even at 285 MHz the PCON
  may default differently) and needs source-side configuration: PCON
  HDMI link config (DP_PCON_HDMI_LINK_CONFIG_1/2), "source control mode",
  TMDS/FRL mode select, max TMDS character rate, HDMI SCDC scrambling via the
  PCON's I2C-over-AUX, colorspace/BPC conversion settings
  (DP_PROTOCOL_CONVERTER_CONTROL_0/1/2), or a sink (HDMI) HPD/EDID refresh.
  Compare with how i915 (`drivers/gpu/drm/i915/display/intel_dp.c`:
  intel_dp_*pcon*, intel_dp_configure_protocol_converter,
  intel_dp_hdmi_*), the DRM helpers (`drivers/gpu/drm/display/drm_dp_helper.c`:
  drm_dp_pcon_*, drm_dp_downstream_*), and amdgpu DC
  (`drivers/gpu/drm/amd/display/dc/link/**`, e.g. link_dp_capability.c,
  dp_set_hdmi*/pcon/dongle handling, dc/core/dc_link*.c) drive a PCON; list
  every write they do that we don't.
- Our 0094 write of 0x3050=1 itself (DP_PROTOCOL_CONVERTER_CONTROL_0 = HDMI
  mode enable?) might be wrong/insufficient or put the PCON into a mode that
  only works up to a certain TMDS clock; check the exact DPCD semantics.
- Link-rate/lane-count or downspread (0x107) or MSA/misc (bpc/colorimetry)
  values we program at HBR2 that the PCON rejects silently.
- Our DP driver not doing a proper sink power state / link-off sequence
  (DP_SET_POWER D3 -> D0, link training restart) so the PCON stays stuck
  after a failed attempt; what recovery sequence would reset it without
  unplugging?

Code to read (all local, read-only):
- Our msm DP/DPU code: `.../build-r93/source/drivers/gpu/drm/msm/dp/*`,
  `.../msm/disp/dpu1/*`, `drivers/phy/qualcomm/phy-qcom-qmp-combo.c`,
  `drivers/usb/typec/*` altmode/`drivers/soc/qcom/pmic_glink_altmode.c`,
  `drivers/gpu/drm/display/drm_dp_helper.c`, `include/drm/display/drm_dp.h`
  (DPCD register names).
- Our patches (explain what each DP one does and whether any is harmful):
  `patches/linux-7.2.7/0092`..`0101`, `0106`, `0109` and the DT overlays
  `dts/qcom/sm8350-asus-rog-phone5-displayport-side.dtso`.
- Reference drivers in the same tree: i915 (`drivers/gpu/drm/i915/display/intel_dp.c`,
  `intel_dp_link_training.c`), amdgpu DC (`drivers/gpu/drm/amd/display/**`).
- Stock ASUS/Qualcomm kernel (msm-5.4, read-only):
  `/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/display/msm/dp/*`
  (dp_display.c, dp_link.c, dp_panel.c, dp_ctrl.c, dp_aux.c, dp_catalog*.c).
- Notes: `test-results/2026-09-29-dp-hub-bringup.md`,
  `test-results/2026-09-29-hbr2-and-server-checks.md`,
  `docs/reviews/2026-09-29-gpt-6-astra-dp-review.md`,
  `docs/reviews/2026-09-29-gpt-6-astra-dp-followup.md`.

Output: ranked causes with file:line evidence; the exact DPCD write sequence
you would add (register, value, when, why), as a diff against our msm DP
files; a PCON recovery sequence; a 5-step test plan with pass/fail criteria;
and anything else you find wrong in our DP path.
