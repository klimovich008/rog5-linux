# 2026-09-27: remote desktop, AI automation, wake on connection

## Remote screen and virtual desktop
- Mirror of the phone screen: `rog5-wayvnc-phone.service` (user unit, Phosh
  session), wayvnc on DSI-1, 127.0.0.1:5900. It renders only while the panel is
  on. Verified from the Deck through an SSH tunnel (lock screen 1080x2448).
- Virtual desktop: `rog5-desktop.service` (user unit, `phone` user,
  lingering), headless sway 1920x1080 with its own wayvnc on 127.0.0.1:5901.
  It runs from boot, independently of Phosh and the panel.
  `WLR_RENDERER=pixman`: with GLES, wayvnc found "No supported buffer formats"
  (ext-image-copy-capture) on this split msm_dpu/adreno setup.
- A headless output inside phoc was tried first and dropped: Phosh's screen
  saver blanks every output, including HEADLESS-1.
- `rog5-desktop` (on the phone): status, screenshot, type, key, run, click,
  move, scroll, windows, sway, wake. Each wtype call starts with a 150 ms
  pause, because the first key of a new virtual keyboard was dropped.
  Verified: launch foot, type and run commands, screenshot; over VNC from the
  Deck: typing, Enter, capture.
- Access is localhost-only; use an SSH tunnel (`ssh -L 5901:127.0.0.1:5901`).

## Stay awake with remote clients, wake on connection
- `rog5-sleep-policy`: stays awake while a remote client is connected. That
  means an established inbound TCP connection to a listening port from a
  non-loopback peer, on an interface with carrier. The carrier check was
  added after a dead USB SSH session (cable pulled) kept the phone awake for
  an hour.
- sshd: ClientAliveInterval 30 / CountMax 4
  (`packaging/arch/20-rog5-sshd-keepalive.conf` →
  `/etc/ssh/sshd_config.d/20-rog5-keepalive.conf`). The daemon is
  `rog5-early-sshd.service` (sshd.service is masked).
- Before each suspend the policy arms WoWLAN: magic packet + IPv4 TCP dport 22
  + UDP dport 41641 (Tailscale). The WCN6855 supports 22 patterns of up to
  134 bytes.
- With WoWLAN armed on r124, suspend still stopped the PCIe link and deinit
  asserted PERST# ("mhi mhi0: Resuming from non M3 state (RESET)", qrtr_mhi
  resume -22). 0076 makes a wakeup-enabled endpoint block D3cold. r126 =
  r44 = r42 + 0076: with WoWLAN armed there is no link down, the resume is
  clean and Wi-Fi reconnects.

## Brightness (see the two brightness reports)
- r125 = r43 = r42 + 0074 (DSI DMA FIFO watermark) + 0075 (10-bit DBV): still
  4 levels. Values below 256 are black, so the lower slider range went black.
  Auto-brightness was switched off: vcnl36866 reads 1.8-23 lux indoors.
  0074/0075 moved to series.diagnostic.
- `scripts/host/rog5-brightness-lab.py`: host web page with a live slider
  (0-1023, about 50 ms per change), dma_fifo_ctrl/bl_hs switches and an
  observation log (~/.local/state/rog5-brightness-lab/observations.jsonl).

## WoWLAN is off by default; Wi-Fi power save and "reachable" mode instead
- r126 (0076) with WoWLAN armed: the first suspends woke within 1 s via the
  root-port PME (IRQ 195). The third failed to enter WoW ("htc suspend not
  complete", "failed to start wow: -110"), then the firmware crashed
  (MHI_CB_EE_RDDM) and Wi-Fi stayed dead. While asleep the phone answered no
  ARP and ignored a magic packet. WCN6855 hw1.1 with the ASUS 2021 firmware.
  WoWLAN stays available with ROG5_SLEEP_WAKE_PORTS; it is off by default.
- 802.11 power save (was disabled because it "stalled TCP setup" in early
  bring-up), re-tested on r127 from the Deck over Wi-Fi:
  off: ping avg 14.5 ms (max 102), SSH connect 0.25 s; on: ping avg 83 ms
  (max 250), SSH connect 0.21-0.32 s; no loss, no stalls.
- rog5-sleep-policy now turns power save on while the screen is off and no
  remote client is connected (off otherwise), and it has a mode:
  /etc/rog5/sleep-mode (or ROG5_SLEEP_MODE) = suspend (default) or reachable
  (never suspends on battery; CPU idle + Wi-Fi PS, reachable over the
  network).
