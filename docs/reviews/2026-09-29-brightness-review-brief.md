# Review request: why does ROG Phone 5 panel brightness only take coarse steps?

Read-only task: do not run anything against the phone, do not modify files.
Answer in text. Look at the problem from a different angle than the earlier
analysis; challenge its assumptions.

## Hardware and software
- ASUS ROG Phone 5 (SM8350), Samsung AMS678 (ER2) AMOLED, DSI0 command mode,
  with a Pixelworks **Iris6** bridge between the SoC DSI host and the panel.
  Mainline 7.2.7 runs the Iris in analog bypass (ABYP); stock Android runs it
  in passthrough (PT) with Iris firmware and sends brightness through the
  Iris's own DSI TX.
- Brightness = DCS 0x51 with a 10-bit DBV (stock: 1..1023, inverted bytes
  hh ll).

## Symptoms (history)
- Only DBV[9:8] takes effect: `51 FF` (one-byte short write) = full,
  `51 03 FF` = the 768 block, `51 00 FF` dark; the level is flat within each
  256 block. So effectively 4 levels (3 visible).
- DCS long writes in HS mode were ignored entirely; LP long writes appear to
  lose the last payload byte. Multi-byte init writes (F0 5A 5A unlock,
  44 09 80 TE line, 2A/2B window, EC/E4 vendor settings) may be truncated the
  same way, but their effect is masked by DDIC defaults.
- With 0074 (stock DSI DMA_FIFO_CTRL watermark) + 0075 (send the full 10-bit
  DBV) on trial r125: every value below 256 was black; above, still coarse.
  The later re-analysis retracted the FIFO-watermark root cause.
- Hazard: a 0x51 write with a padded/3-byte payload hard-hung the phone once
  (stock-shape `51 hh ll` is allowed).

## Where to look
- Repo: /home/deck/.local/state/rog5-prod-boot-20260923
  - Patches: patches/linux-7.2.7/0037 (panel driver), 0043 (brightness in LP),
    0045 (map to DBV high levels = current production), 0061, 0074, 0075
    (diagnostic series).
  - Earlier analysis with ranked hypotheses and experiments E0-E6 (never
    run): test-results/2026-09-27-brightness-reanalysis.md
  - Lessons: docs/development-lessons.md (search 0x51 / brightness / padded).
- Patched kernel source: /home/deck/.local/state/rog5-kernel-7.2.7-build-r71/source
  (drivers/gpu/drm/panel/panel-asus-rog5-ams678.c, drivers/gpu/drm/msm/dsi/).
- Lab module (planned, unused):
  /tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/brightness-investigation/rog5_dsi_lab/
  and phone state snapshot .../brightness-investigation/phone/state.txt
- Stock ASUS 5.4 kernel (techpack display incl. Iris6 driver):
  /home/deck/.local/state/rog5-kernel-compare-20260927/stock
  (techpack/display/msm/dsi/, iris sources), stock DT:
  /home/deck/.local/state/rog5-stock-payload-20260927/dtbo/dtbo0.dts,
  vendor files under /home/deck/.local/state/rog5-stock-payload-20260927/.

## Questions
1. What alternative explanations did the earlier analysis miss or dismiss too
   quickly? Consider e.g. DSI packet formation (header/ECC/WC, DMA length
   rounding, the MSM "last packet" / batching bit, `MIPI_DSI_MSG_USE_LPM`
   handling, `mipi_dsi_dcs_write` vs `_buffer`, the panel driver building the
   payload), DDIC-side behaviour (register/level-key state, 0x53 control bits,
   dimming/BCTRL, DBV bit order/inversion, write-protect of the lower DBV
   byte), and Iris ABYP behaviour (does ABYP forward LP long packets
   verbatim? packet-length limits? does the Iris itself answer or filter DCS
   0x51/0x53?).
2. Why would "below 256 = black" happen with 0075 on r125, and what does that
   imply about which byte the DDIC uses?
3. Rank the hypotheses, with evidence (file:line) and what would falsify each.
4. Propose the single most informative safe experiment (only `51 hh ll`,
   one-byte short writes, and DCS reads; no padded 0x51; no msm reload) and
   predict its outcome under each hypothesis. Also say whether the lab
   module's design is sound or could itself mislead.
5. If you find a concrete driver bug, describe the minimal patch.
