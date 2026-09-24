# Milestones 2–4: display/GPU at boot, Wi-Fi, touch — September 24

Default kernel `production-7.2.7-r10` (build r7: gpucc/refgen built in; touch
DTB `dd8912f2…` = platform DTB + enabled front-touch overlay + QUP0 GPI DMA;
ramdisk with the platform kit, the production Wi-Fi kit and trial `r10`).
RAM trials t8 (r8) and t10 (r10), then `install-default-kernel.py` and two
ordinary boots that committed healthy. Evidence:
`rog5-production-boot-20260923/trial-727-t{8,10}-session`, `default-7.2.7-r10`.

## Milestone 2: display and GPU at boot, no manual steps — PASS

- The GPU SMMU (`3da0000.iommu`) now probes by itself: gpucc built in removed
  the deferred-probe timeout and the manual `drivers_probe`.
- `rog5-platform-modules` loads msm (`separate_gpu_kms=1`) and the AMS678
  panel at about 22 s: A660 `card0`/`renderD128`, KMS `card1-DSI-1`
  connected and enabled, fbcon `msm-kmsdrmfb`.
- First render-node open: `gpu-initialized: 1`, revision 660 (06060001),
  rbbm-status 0.
- The user saw the four test bands (red, green, blue, white) at brightness 1023
  on r10.
- Remaining WARNs: the two known DSI clock traces during msm load.

## Milestone 3: Wi-Fi — PASS

- `rog5-wifi radio` ran the September sequence on 7.2.7: S12 vote, modules,
  PCIe PHY, activation, `wcn6855 hw1.1`, firmware
  `WLAN.HSP.1.1.c3-00205`, `wlp1s0` at about 38–40 s.
- WPA associated with the private network from `/persist`; dhcpcd leased
  192.168.1.24 (trial) and 192.168.1.138 (default boot 2).
- The old 8.4 V radio floor deferred the radio at 7.96 V / 76 % on t8. It is
  now 7.6 V and 50 % with USB input: the one reset in the September bring-up
  came from the S12/UFS rail request, not battery voltage.

## Milestone 4: touch — PASS

- t8: I2C4 stayed deferred ("Failed to get tx DMA ch"): it runs in GPI mode and
  `gpi_dma0` was disabled. Enabled in the touch overlay for r10.
- r10: `rog5-fts3658u 0-0038: normal firmware ID 5652`, input `event1`.
- The user tapped the four corners; decoded positions (panel 1080×2448):
  top-left (49,150)/(100,86), top-right (962,91), bottom-left (101,2349),
  bottom-right (988,2316). Orientation and scale are correct.

## Also observed

- The RTC counter survived the R1 hard reset (64124 s at t8), and each boot
  restored the clock from RTC + offset before NTP.
- `rog5-package-keyring.service` still fails on some boots; open.
